"""Author-side world generation jobs for the web UI (one job at a time, every heavy step is a child process).

Chain: skeleton -> frozen islands + bounded 1km plans -> explicit island TD (or CPU pending) -> final fast 2km world -> optional TD coarse
ridge field on the GPU + comparison with the fast layer -> atlas render -> summary / map_source check.
Skeleton, fast layer and TD need numba / torch, so they run with the Terragenesis interpreter (imported read-only, nothing there
is written). The atlas render runs with this server's own interpreter. Products go to new directories named web-<job id>;
an existing directory is never reused or overwritten. No D8 anywhere: the fast layer routes on the irregular Delaunay graph.
"""
from __future__ import annotations

import json
import math
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from . import config as wc, estimates as est
from .sysmem import available_memory_bytes, command_lines

ROOT = Path(__file__).resolve().parents[2]
TG_PYTHON = ROOT.parent / '山川形意Terragenesis' / 'runtime' / 'venv' / 'Scripts' / 'python.exe'
SIZES_KM = (1600, 5000, 10000)
SIZE_LABELS = {1600: '1600 km', 5000: '5000 km', 10000: '10000 km（需显卡 / 较慢）'}
QUALITIES = ('speed', 'balanced', 'precise')
QUALITY_LABELS = {'speed': '速度（粗格距·默认）', 'balanced': '均衡', 'precise': '精细（细格距）'}
PIPELINES = ('playable', 'full')
PIPELINE_LABELS = {'playable': '游玩草稿（默认·更快）', 'full': '作者完整链'}
# size_km → quality → spacing_m (must divide size and skeleton cell)
QUALITY_SPACING_M = {
    1600: {'speed': 4000.0, 'balanced': 2000.0, 'precise': 1000.0},
    5000: {'speed': 8000.0, 'balanced': 4000.0, 'precise': 2000.0},
    10000: {'speed': 12000.0, 'balanced': 8000.0, 'precise': 4000.0},
}
MIN_FREE_BYTES = 2 * 2 ** 30
SOFT_MIN_FREE_GIB = 0.25  # when memory is tight: still start freeze, do not hard-refuse
MIN_SIDE_KM, MAX_SIDE_KM = 100, 10000  # independent width_km / height_km bounds of the author API
# Island candidate density selector of web_island_stage prepare (frozen reader limits are never relaxed).
ISLAND_DENSITIES = ('none', 'low', 'medium', 'high')
DEFAULT_ISLAND_DENSITY = 'medium'
# Island candidate *layout* selector of web_island_stage prepare. 'old' is the historical absolute-slot v5
# geometry and passes no new keyword; 'clustered' declares the clustered-provinces preset explicitly. Neither
# a quality nor a size ever selects a layout. CLUSTERED_LAYOUT_POLICY is the policy string that preset records
# (see web_island_stage.CLUSTERED_LAYOUT_POLICY); it is only read back to report what a frozen product declares.
ISLAND_LAYOUTS = ('old', 'clustered')
DEFAULT_ISLAND_LAYOUT = 'old'
CLUSTERED_LAYOUT_POLICY = 'clustered-provinces-v1'
ISLAND_LAYOUT_LABELS = {'old': '历史绝对槽位（默认）', 'clustered': '岛群聚类（少数岛群世界）'}
# Fast-layer node cap of an explicit-rectangle job: ocean_island_consumers.rasterize() defaults to
# max_cells = 1e6 cells. Only the explicit width/height path is pre-checked (the square legacy path
# keeps its old behaviour), and no budget is raised anywhere.
FAST_NODE_BUDGET = 1_000_000
GPU_MIN_FREE_MIB = est.TD_GPU_MIN_FREE_MIB
TD_SKIP_OCEAN_KM = 120
TD_STEPS = 15
GPU_CACHE_SECONDS = 60
JOB_ID_RE = re.compile(r'^\d{8}-\d{6}-[0-9a-f]{4}$')
GPU_JOB_PATTERNS = ('web_island_stage', 'td_coarse_ridges', 'web_td_stage', 'build_td_world', 'build_td_fast_world', 'freeze_td_world', 'eval_td_speedup')
FINISHED = ('succeeded', 'failed', 'cancelled', 'interrupted')
PREVIEWS = {'overview': ('atlas_dir', 'simple-atlas.png'), 'relief': ('atlas_dir', 'relief-only.png'),
            'final-overview': ('final_atlas_dir', 'simple-atlas.png'), 'final-relief': ('final_atlas_dir', 'relief-only.png'),
            'td': ('job_dir', 'td-preview.png')}


def spacing_m(size_km, quality='speed'):
    """Legacy square table: size_km -> quality -> spacing_m (1600/5000/10000 only)."""
    table = QUALITY_SPACING_M.get(int(size_km))
    if table is None:
        raise ValueError(f'unsupported size_km {size_km}')
    if quality not in table:
        raise ValueError(f'unsupported quality {quality!r}')
    return float(table[quality])


def size_class(width_km, height_km):
    """Existing spacing table band chosen by the **longest** side: <=2000 / <=6000 / rest.

    Never a dict lookup of the raw size, so a 10000x8000 or a 1200x900 world cannot raise KeyError.
    """
    longest = max(int(width_km), int(height_km))
    return 1600 if longest <= 2000 else 5000 if longest <= 6000 else 10000


def _divisors(n):
    out, i = set(), 1
    while i * i <= n:
        if n % i == 0:
            out.update((i, n // i))
        i += 1
    return out


def _gcd(a, b):
    while b:
        a, b = b, a % b
    return a


def rectangular_spacing_m(width_km, height_km, quality='speed'):
    """Fast spacing for an arbitrary rectangle: same band table, but a spacing that actually divides.

    ``fast_relief.grid_of`` rejects a skeleton extent that is not a whole number of grid cells, so the
    spacing must divide both extents (width_km * 1000 and height_km * 1000). We start from the band's
    target spacing and fall back to the largest whole-metre divisor of gcd(w, h) * 1000 that is <= it:
    10000x8000 km at speed (target 12000 m) -> 10000 m, i.e. 1000 x 800 = 800000 nodes.
    """
    if quality not in QUALITIES:
        raise ValueError(f'unsupported quality {quality!r}')
    w, h = int(width_km), int(height_km)
    target = QUALITY_SPACING_M[size_class(w, h)][quality]
    limit = _gcd(w, h) * 1000                       # metres that divide both extents
    if limit % int(target) == 0:
        return float(target)
    return float(max(d for d in _divisors(limit) if d <= target))


def requested_spacing_m(width_km, height_km, quality='speed', *, explicit=None):
    """Pick the fast spacing. Legacy square sizes keep the exact table value; every other world is rectangular.

    ``explicit`` says whether the caller passed width_km/height_km on purpose (None = infer: a square that is in
    the legacy table is treated as legacy). The table values themselves are never changed.
    """
    w, h = int(width_km), int(height_km)
    legacy = w == h and w in QUALITY_SPACING_M
    if explicit is None:
        explicit = not legacy
    if legacy and not explicit:
        return spacing_m(w, quality)
    return rectangular_spacing_m(w, h, quality)


def job_dims(params):
    """Real (width_km, height_km) of a job. Jobs saved before rectangles only carry size_km (square)."""
    w, h = params.get('width_km'), params.get('height_km')
    if w and h:
        return int(w), int(h)
    side = int(params.get('size_km') or 1600)
    return side, side


def explicit_rect(params):
    """True when the job was submitted with width_km **and** height_km (jobs saved before rectangles have neither)."""
    return params.get('width_km') is not None and params.get('height_km') is not None


def defer_island_analysis(params):
    """Speed CPU drafts of an explicit rectangle defer the 1 km island qualification analysis.

    An explicit width_km/height_km world has to rasterize the whole domain at 1 km just for island qualification.
    Only ``quality=speed`` + ``pipeline=playable`` + ``use_gpu=False`` passes ``--defer-mountain-analysis`` to the
    island prepare stage; every other request (and every legacy square job) keeps the old argv, and the GPU path is
    never affected. Island TD qualification is then reported as pending-analysis, never as computed.
    """
    return (explicit_rect(params) and (params.get('quality') or 'speed') == 'speed'
            and (params.get('pipeline') or 'playable') == 'playable' and not params.get('use_gpu'))


def saved_island_density(*records):
    """Density of an already frozen island product; never re-derived from a new quality or size.

    Upgrade / resume reuse the source islands exactly as they were prepared, so the recorded density (prepared.json
    record → fast manifest ``island_mountains.record``) wins over anything a new request might ask for. Islands
    prepared before the selector existed carry nothing and count as 'medium' (the stage default they were built with).
    """
    for rec in records:
        value = (rec or {}).get('island_density') if isinstance(rec, dict) else None
        if value in ISLAND_DENSITIES:
            return value
    return 'medium'


def saved_island_analysis(record):
    """(status, deferred) of the saved island qualification record; 'pending-analysis' means it was not computed."""
    analysis = (record or {}).get('analysis') or {}
    status = analysis.get('status')
    if status is None:
        return None, None
    return status, status == 'pending-analysis'


def saved_island_layout(*records):
    """Layout actually frozen with this world's islands; never re-derived from a new quality or size.

    Upgrade / resume reuse the source islands exactly as they were prepared, so the declared layout of the saved
    record (``island_layout``, else a clustered ``island_config.layout_policy``) wins over anything a new request
    might ask for. Islands prepared before the selector existed carry nothing and count as the historical 'old'.
    """
    for rec in records:
        if not isinstance(rec, dict):
            continue
        value = rec.get('island_layout')
        if value in ISLAND_LAYOUTS:
            return value
        if (rec.get('island_config') or {}).get('layout_policy') == CLUSTERED_LAYOUT_POLICY:
            return 'clustered'
    return DEFAULT_ISLAND_LAYOUT


def island_layout(params):
    """Layout a *new* prepare stage asks for ('clustered', otherwise None = the historical 'old').

    Only an explicit ``island_layout=clustered`` request changes the prepare argv; a job saved before the
    selector existed (no field) and an explicit 'old' both keep the historical call byte-identical. use_gpu,
    quality and pipeline never select a layout, so the existing defer / density rules stay untouched.
    """
    return 'clustered' if (params or {}).get('island_layout') == 'clustered' else None


def island_density(params):
    """Island candidate density a *new* prepare stage would ask for ('low', otherwise None = default 'medium').

    Big explicit rectangles (max side > 6000 km) at speed + playable + CPU would exceed the frozen island manifest
    encoding limit (16 MiB) with the default candidate density. Only that combination asks for
    ``--island-density low``: it lowers the number of island *candidates* over the coarse map, never the geometry
    of a single island. Every other request returns None and the stage keeps its default 'medium'.
    """
    width_km, height_km = job_dims(params)
    if (max(width_km, height_km) > 6000 and explicit_rect(params) and (params.get('quality') or 'speed') == 'speed'
            and (params.get('pipeline') or 'playable') == 'playable' and not params.get('use_gpu')):
        return 'low'
    return None


def render_policy(params):
    """One place for the render argv policy, so estimate and stages cannot drift apart.

    Only the default pair (quality=speed + pipeline=playable) gets the quick overview: one page at
    1200 px, no detail / reserved pages. Everything else renders the full atlas as before, and
    nothing here touches the physical rounds, the spacing table or the stage sequence.
    """
    quick = est.quick_overview(params.get('quality', 'speed'), params.get('pipeline') or 'playable')
    return dict(quick_overview=quick, width_px=est.OVERVIEW_WIDTH_PX if quick else None,
                extra_argv=['--overview-only', '--width', str(est.OVERVIEW_WIDTH_PX)] if quick else [],
                note=('速度档 + 游玩草稿：概览图 %d px，无局部/预留附页' % est.OVERVIEW_WIDTH_PX) if quick
                     else '完整图册（局部页 + 预留演示）')


def memory_advice(available_bytes, recommended_bytes):
    """Soft memory schedule: never a hard refuse; low free RAM → slower / fewer threads."""
    avail = int(available_bytes) if available_bytes is not None else None
    need = int(recommended_bytes)
    if avail is None:
        return dict(constrained=False, hard_limit=False, available_bytes=None, recommended_bytes=need,
                    thread_cap=None, memory_wait_s=60.0, min_free_gib=None, time_scale=1.0,
                    note='未能读取可用内存，按常速调度')
    if avail >= need:
        return dict(constrained=False, hard_limit=False, available_bytes=avail, recommended_bytes=need,
                    thread_cap=None, memory_wait_s=60.0, min_free_gib=None, time_scale=1.0,
                    note='内存充裕，按常速调度')
    time_scale = min(4.0, max(1.25, need / max(avail, 1)))
    return dict(constrained=True, hard_limit=False, available_bytes=avail, recommended_bytes=need,
                thread_cap=1, memory_wait_s=min(3600.0, 300.0 * time_scale),
                min_free_gib=SOFT_MIN_FREE_GIB, time_scale=float(time_scale),
                note=f'可用内存低于建议值，将放慢并拉长等待（约 ×{time_scale:.1f}），不硬拦')


class WorldGenRequest(BaseModel):
    """Author submit body. Rectangles: give width_km **and** height_km (integers 100-10000); size_km stays
    the legacy square shortcut (1600 / 5000 / 10000) and is ignored when both dims are present."""

    model_config = ConfigDict(extra='forbid')
    world_type: Literal['multi-continent', 'pangaea', 'archipelago', 'two-continents', 'inland-sea'] = 'multi-continent'
    size_km: Literal[1600, 5000, 10000] = 1600
    width_km: int | None = Field(None, ge=MIN_SIDE_KM, le=MAX_SIDE_KM)
    height_km: int | None = Field(None, ge=MIN_SIDE_KM, le=MAX_SIDE_KM)
    ocean_fraction: float = Field(0.6, ge=wc.OCEAN_RANGE[0], le=wc.OCEAN_RANGE[1], allow_inf_nan=False)
    mountain_area: float = Field(0.25, ge=0.20, le=0.30, allow_inf_nan=False)
    seed: int = Field(wc.DEFAULT_WORLD_SEED, ge=0, lt=2 ** 63, strict=True)
    use_gpu: bool = Field(False, strict=True)
    quality: Literal['speed', 'balanced', 'precise'] = 'speed'
    pipeline: Literal['playable', 'full'] = 'playable'
    # Optional island candidate layout. Omitting it keeps the historical 'old' geometry, so every stored job and
    # every replay of it stays byte-identical; 'clustered' explicitly asks for the clustered-provinces preset.
    island_layout: Literal['old', 'clustered'] = 'old'
    geography_features: list[dict] = Field(default_factory=list, max_length=32)

    @field_validator('width_km', 'height_km', mode='before')
    @classmethod
    def _integer_side(cls, v):
        """Reject bool / NaN / inf / fractional / string sides with a 422 instead of coercing them."""
        if v is None:
            return None
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError('width_km / height_km must be an integer number of km (100-10000)')
        if isinstance(v, float) and (not math.isfinite(v) or v != int(v)):
            raise ValueError('width_km / height_km must be a finite whole number of km')
        return int(v)

    @model_validator(mode='after')
    def _both_or_none(self):
        if (self.width_km is None) != (self.height_km is None):
            raise ValueError('width_km and height_km must be given together (or omit both for size_km)')
        return self

    @property
    def dims(self):
        """(width_km, height_km) actually requested; without width/height this is the square size_km."""
        if self.width_km is not None:
            return int(self.width_km), int(self.height_km)
        return int(self.size_km), int(self.size_km)

    @property
    def explicit_rect(self):
        return self.width_km is not None


class WorldGenUpgradeRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    quality: Literal['speed', 'balanced', 'precise']
    pipeline: Literal['playable', 'full'] | None = None


class WorldGenRefused(Exception):
    """A request that is valid but cannot start now (busy, memory, GPU). status is the HTTP status for the route."""

    def __init__(self, status, detail):
        super().__init__(detail)
        self.status, self.detail = status, detail


@dataclass
class Stage:
    name: str
    label: str
    argv: list | None = None
    fn: Callable | None = None
    gpu: bool = False            # True: CUDA stays visible and device memory is sampled while it runs


# ------------------------------------------------------------------------------------------------------------- probes
def nvidia_smi_used_mib():
    """Whole-device memory.used (MiB, all processes) or None when nvidia-smi is missing."""
    try:
        out = subprocess.run(['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits'], capture_output=True,
                             text=True, timeout=10, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        return int(out.stdout.strip().splitlines()[0]) if out.returncode == 0 and out.stdout.strip() else None
    except (OSError, ValueError, subprocess.SubprocessError, IndexError):
        return None


def other_gpu_jobs():
    """Running TD / torch jobs of this project (by command line) and python processes nvidia-smi lists as compute apps."""
    me, hits = os.getpid(), []
    try:
        for pid, cmd in command_lines():
            low = (cmd or '').lower()
            if pid != me and 'python' in low and 'get-ciminstance' not in low and any(p in low for p in GPU_JOB_PATTERNS):
                hits.append(f'pid {pid}: {cmd[:160]}')
    except Exception as e:  # listing failed: report it instead of pretending the GPU is free
        hits.append(f'无法列出进程（{type(e).__name__}: {e}），为安全起见视为占用')
    try:
        out = subprocess.run(['nvidia-smi', '--query-compute-apps=pid,process_name', '--format=csv,noheader'], capture_output=True,
                             text=True, timeout=10, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        for line in out.stdout.splitlines():
            if 'python' in line.lower():
                hits.append('nvidia-smi: ' + line.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return hits


def gpu_reason(ok, info, min_mib=GPU_MIN_FREE_MIB):
    if ok:
        return ''
    if info.get('error'):
        return '显卡检测失败：' + str(info['error'])
    if not info.get('cuda_available'):
        r = str(info.get('reason', ''))
        if 'torch not importable' in r:
            return 'Terragenesis 环境里导入不了 PyTorch（' + r + '）'
        cvd = info.get('cuda_visible_devices')
        extra = f'；本服务环境变量 CUDA_VISIBLE_DEVICES={cvd!r}' if cvd is not None else ''
        return '未检测到可用的 CUDA 显卡（torch.cuda.is_available() 为 False）' + extra
    return f"显存空闲 {info.get('cuda_free_mib')} MiB，低于所需 {min_mib} MiB（{info.get('name', '')}）"


# ------------------------------------------------------------------------------------------------------------- manager
def _now():
    return time.strftime('%Y-%m-%dT%H:%M:%S')


def _kill_tree(proc):
    if proc is None or proc.poll() is not None:
        return
    if sys.platform == 'win32':
        subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'], capture_output=True,
                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    else:
        proc.kill()


def _jsonable(v):
    """JSON-safe copy: numpy scalars -> python, NaN / inf -> None (the web response encoder rejects NaN)."""
    def clean(x):
        if isinstance(x, float) and (x != x or x in (float('inf'), float('-inf'))):
            return None
        if isinstance(x, dict):
            return {k: clean(y) for k, y in x.items()}
        if isinstance(x, list):
            return [clean(y) for y in x]
        return x
    return clean(json.loads(json.dumps(v, default=lambda o: o.item() if hasattr(o, 'item') else str(o), allow_nan=True)))


class WorldGenManager:
    def __init__(self, root=ROOT, *, artifacts=None, tg_python=None, web_python=None, gpu_probe=None, memory=None,
                 gpu_jobs=None, stage_builder=None, gpu_sampler=None):
        self.root = Path(root)
        self.artifacts = Path(artifacts) if artifacts else self.root / 'artifacts'
        self.jobs_dir = self.artifacts / 'worldgen-jobs'
        self.tg_python = Path(tg_python or TG_PYTHON)
        self.web_python = Path(web_python or sys.executable)
        self.gpu_probe = gpu_probe or self._probe_gpu_subprocess
        self.memory = memory or available_memory_bytes
        self.gpu_jobs = gpu_jobs or other_gpu_jobs
        self.stage_builder = stage_builder or self.default_stages
        self.gpu_sampler = gpu_sampler or nvidia_smi_used_mib
        self._lock = threading.RLock()
        self._jobs, self._busy, self._active, self._proc, self._cancel = {}, False, None, None, set()
        self._gpu_cache = None
        self._load_existing()

    # ---------------------------------------------------------------- persistence
    def _load_existing(self):
        if not self.jobs_dir.is_dir():
            return
        for f in self.jobs_dir.glob('web-*/job.json'):
            try:
                job = json.loads(f.read_text(encoding='utf-8'))
            except (OSError, ValueError):
                continue
            if job.get('status') not in FINISHED and not _pid_alive(job.get('owner_pid')):
                job.update(status='interrupted', error='服务重启时任务未结束（子进程已不受管理），产物可能不完整')
                self._jobs[job['id']] = job
                self._save(job)
            self._jobs[job['id']] = job

    def _foreign_active(self):
        """Unfinished jobs owned by another live server process (same artifacts folder)."""
        me, hits = os.getpid(), []
        if not self.jobs_dir.is_dir():
            return hits
        for f in self.jobs_dir.glob('web-*/job.json'):
            job = _read_json(f) or {}
            pid = job.get('owner_pid')
            if job.get('status') not in FINISHED and pid not in (None, me) and _pid_alive(pid):
                hits.append(f"{job.get('id')}（进程 {pid}）")
        return hits

    def _save(self, job):
        d = Path(job['paths']['job_dir'])
        d.mkdir(parents=True, exist_ok=True)
        tmp = d / 'job.json.tmp'
        tmp.write_text(json.dumps(job, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
        os.replace(tmp, d / 'job.json')

    # ---------------------------------------------------------------- GPU / memory / options
    def _probe_gpu_subprocess(self):
        if not self.tg_python.is_file():
            return False, dict(cuda_available=False, error=f'Terragenesis 解释器不存在：{self.tg_python}')
        code = ('import json,sys;sys.path.insert(0,sys.argv[1]);from app.world_gen import td_coarse as tc;'
                'ok,info=tc.gpu_status(int(sys.argv[2]));print(json.dumps({"ok":bool(ok),"info":info},default=str))')
        try:
            out = subprocess.run([str(self.tg_python), '-c', code, str(self.root), str(GPU_MIN_FREE_MIB)], capture_output=True,
                                 text=True, timeout=120, cwd=str(self.root), encoding='utf-8', errors='replace',
                                 creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            line = [x for x in out.stdout.splitlines() if x.startswith('{')][-1]
            r = json.loads(line)
            return bool(r['ok']), r['info']
        except Exception as e:
            return False, dict(cuda_available=False, error=f'{type(e).__name__}: {e}'[:300])

    def gpu_status(self, refresh=False):
        with self._lock:
            c = self._gpu_cache
            if c and not refresh and time.time() - c['_t'] < GPU_CACHE_SECONDS:
                return {k: v for k, v in c.items() if k != '_t'}
        ok, info = self.gpu_probe()
        info = dict(info or {})
        if os.environ.get('CUDA_VISIBLE_DEVICES') is not None:
            info.setdefault('cuda_visible_devices', os.environ['CUDA_VISIBLE_DEVICES'])
        status = dict(usable=bool(ok), reason=gpu_reason(ok, info), info=info, min_free_mib=GPU_MIN_FREE_MIB, checked_at=_now(),
                      used_for='TD island interiors and coarse ridge comparison; final world layer is CPU')
        with self._lock:
            self._gpu_cache = dict(status, _t=time.time())
        return status

    @staticmethod
    def memory_gate_bytes(size_km, spacing=None, quality='speed', *, height_km=None):
        """Recommended free RAM (not a hard refuse threshold). ``height_km`` keeps squares backwards compatible."""
        sp = float(spacing if spacing is not None else
                   requested_spacing_m(size_km, size_km if height_km is None else height_km, quality))
        return max(MIN_FREE_BYTES, int(est.world_process_peak_mb(size_km, sp, height_km=height_km) * 2 ** 20))

    def disk_free_bytes(self):
        for path in (self.artifacts, self.root):
            try:
                target = path if path.exists() else path.parent
                if target.exists():
                    return int(shutil.disk_usage(target).free)
            except Exception:
                continue
        return None

    def options(self, refresh_gpu=False):
        try:
            avail = int(self.memory())
        except Exception:
            avail = None
        with self._lock:
            active = self._active
        estimates, recommended, advice = {}, {}, {}
        for s in SIZES_KM:
            estimates[str(s)] = {}
            recommended[str(s)] = {}
            advice[str(s)] = {}
            for q in QUALITIES:
                sp = spacing_m(s, q)
                need = self.memory_gate_bytes(s, sp)
                adv = memory_advice(avail, need)
                pipelines = {}
                for pipe in PIPELINES:
                    quick = est.quick_overview(q, pipe)
                    cpu = est.scale_chain_time(est.chain(s, False, sp, pipeline=pipe, quick_render=quick), adv['time_scale'])
                    gpu = est.scale_chain_time(est.chain(s, True, sp, pipeline=pipe, quick_render=quick), adv['time_scale'])
                    pipelines[pipe] = dict(cpu=cpu, gpu=gpu, disk_bytes=cpu['disk_bytes'], disk=cpu['disk'])
                # Top-level cpu/gpu mirror playable for older clients / default UI path.
                estimates[str(s)][q] = dict(cpu=pipelines['playable']['cpu'], gpu=pipelines['playable']['gpu'],
                                            spacing_m=sp, disk_bytes=pipelines['playable']['disk_bytes'],
                                            disk=pipelines['playable']['disk'], pipelines=pipelines)
                recommended[str(s)][q] = need
                advice[str(s)][q] = adv
        free = self.disk_free_bytes()
        return dict(
            world_types=[dict(id=t, label=wc.WORLD_TYPE_LABELS[t]) for t in wc.WORLD_TYPES],
            sizes=[dict(km=s, label=SIZE_LABELS[s], slow=s == 10000) for s in SIZES_KM],
            qualities=[dict(id=q, label=QUALITY_LABELS[q],
                            spacings_m={str(s): QUALITY_SPACING_M[s][q] for s in SIZES_KM}) for q in QUALITIES],
            pipelines=[dict(id=p, label=PIPELINE_LABELS[p]) for p in PIPELINES],
            rectangles=dict(width_km=[MIN_SIDE_KM, MAX_SIDE_KM], height_km=[MIN_SIDE_KM, MAX_SIDE_KM],
                            together=True, size_class_by='longest', node_budget=FAST_NODE_BUDGET,
                            note='矩形：同时给 width_km 与 height_km（整数 %d-%d）；格距按最长边选档，必要时取能整除两边的最大整米值，'
                                 '提交后 params 里的实际 spacing_m / 网格节点数才是准；显式矩形受 fast 节点上限 %d 预检'
                                 % (MIN_SIDE_KM, MAX_SIDE_KM, FAST_NODE_BUDGET)),
            island_layouts=[dict(id=l, label=ISLAND_LAYOUT_LABELS[l], default=l == DEFAULT_ISLAND_LAYOUT)
                            for l in ISLAND_LAYOUTS],
            defaults=dict(world_type='multi-continent', size_km=1600, ocean_fraction=0.6, mountain_area=0.25,
                          seed=wc.DEFAULT_WORLD_SEED, use_gpu=False, quality='speed', pipeline='playable'),
            ranges=dict(ocean_fraction=list(wc.OCEAN_RANGE), mountain_area=[0.20, 0.30], seed=[0, 2 ** 63 - 1]),
            gpu=self.gpu_status(refresh_gpu),
            estimates=estimates,
            memory=dict(available_bytes=avail, recommended_bytes=recommended,
                        min_free_bytes=recommended, hard_limit=False, advice=advice),
            disk=dict(free_bytes=free, path=str(self.artifacts),
                      note='产物写入 artifacts；占用为推算值（游玩草稿单份成图，完整链含细节与双份成图）'),
            active_job=active,
            td=dict(skip_ocean_km=TD_SKIP_OCEAN_KM, steps=TD_STEPS, spec='docs/td-coarse-ridges-spec.md §6'),
            tg_python=dict(path=str(self.tg_python), present=self.tg_python.is_file()),
            terragenesis=__import__('app.world_gen.terragenesis_bridge', fromlist=['probe']).probe(),
            notes=['estimates 标 measured 的是本机实测，extrapolated 是推算',
                   '默认 pipeline=playable（游玩草稿）：跳过 world-processes / details / 双份成图，尽快得到可关联的 fast 层',
                   '默认精度为速度档（粗格距）；精度档只改 fast 采样格距，不改种子；可对已成功任务 upgrade',
                   '万公里骨架单元格 40 km（与 5000 km@20 km 同格数）；玩家开局区域可再做更细局部骨架，不必重跑全域',
                   '概览快档只给默认组合（速度档 + 游玩草稿）：成图只出 1200 px 概览图，无局部/预留附页；'
                   '均衡/精细或完整链仍是完整图册',
                   'use_gpu=true 的游玩草稿仍会跑完整岛内 TD，引擎预热/模型加载占大头，可能较慢；完整链不承诺分钟级',
                   '内存为软建议：低于建议值仍可启动，会限线程、拉长等待并放慢；不设硬上限',
                   '提交前估算含磁盘占用推算与当前可用磁盘',
                   '骨架/岛/岛山/fast/details 子进程使用 Terragenesis runtime/venv；缺解释器时 submit 返回 503',
                   '岛布局 island_layout 是可选新增项，不写就仍是 old（历史绝对槽位几何）：旧任务与其 upgrade 按原样回放，'
                   '不因档位/尺寸重选布局',
                   '显式 clustered 只用于少数岛群世界（province 5×6 + 3 个孤岛、age 300、链长 600 km、stages 8、'
                   '边界 150 km、ridge false）；不传该字段即保持 old 默认',
                   '地图生成核：Terragenesis；成功后可导入到游玩世界地图（mechanics.map = world_map_product）'])
    # ---------------------------------------------------------------- jobs
    def _paths(self, jid):
        name = 'web-' + jid
        world = self.artifacts / 'worlds' / name
        fast = self.artifacts / 'fast-world' / name
        return dict(world_dir=str(world), skeleton=str(world / 'skeleton.npz'), td_dir=str(world / 'td-coarse-ridges'),
                    fast_dir=str(fast), detail_dir=str(fast.parent/(name+'-detailed')), atlas_dir=str(fast / 'atlas'),
                    final_atlas_dir=str(fast.parent/(name+'-detailed')/'atlas'), job_dir=str(self.jobs_dir / name),
                    log=str(self.jobs_dir / name / 'log.txt'))

    def submit(self, req: WorldGenRequest):
        with self._lock:
            if self._busy:
                raise WorldGenRefused(409, f'已有生成任务（{self._active or "正在启动"}）在运行，同一时间只允许一个')
            self._busy = True
        try:
            foreign = self._foreign_active()
            if foreign:
                raise WorldGenRefused(409, '另一个织梦服务进程有生成任务在运行：' + '；'.join(foreign[:3]))
            if not self.tg_python.is_file():
                raise WorldGenRefused(503, f'Terragenesis 解释器不存在：{self.tg_python}（作者生成需 ../山川形意Terragenesis/runtime/venv）')
            width_km, height_km = req.dims
            try:
                geography_features = wc.normalize_geography_features(req.geography_features,
                    dict(width_km=width_km, height_km=height_km, origin_km=[-width_km / 2, -height_km / 2]),
                    est.skeleton_cell_km(width_km, height_km))
            except wc.ConfigError as exc:
                raise WorldGenRefused(422, str(exc)) from exc
            sp = requested_spacing_m(width_km, height_km, req.quality, explicit=req.explicit_rect)
            if req.explicit_rect:
                nodes = est.fast_layer(width_km, height_km, sp)['nodes']
                if nodes > FAST_NODE_BUDGET:
                    raise WorldGenRefused(422, f'{width_km}x{height_km} km 在 {sp:g} m 格距下有 {nodes} 个网格节点，'
                                               f'超过 fast 岛栅格预算 {FAST_NODE_BUDGET}（岛消费方 rasterize 的默认上限）；'
                                               f'请用速度档（粗格距）或缩小尺寸')
            avail, gate = int(self.memory()), self.memory_gate_bytes(width_km, sp, height_km=height_km)
            advice = memory_advice(avail, gate)
            gpu = None
            if req.use_gpu:
                gpu = self.gpu_status(refresh=True)
                if not gpu['usable']:
                    raise WorldGenRefused(409, '不能使用显卡：' + gpu['reason'])
                others = self.gpu_jobs()
                if others:
                    raise WorldGenRefused(409, '已有别的显卡任务在运行：' + '；'.join(others[:3]))
            for _ in range(20):
                jid = time.strftime('%Y%m%d-%H%M%S') + '-' + secrets.token_hex(2)
                paths = self._paths(jid)
                if jid not in self._jobs and not any(Path(paths[k]).exists() for k in ('world_dir', 'fast_dir', 'job_dir')):
                    break
            else:
                raise WorldGenRefused(500, '无法分配新的任务目录')
            params = req.model_dump()
            if geography_features:
                params['geography_features'] = geography_features
            else:
                params.pop('geography_features', None)
            params['spacing_m'] = sp
            params['memory_schedule'] = advice
            params['skeleton_cell_km'] = est.skeleton_cell_km(width_km, height_km)
            params['fast_nodes'] = est.fast_layer(width_km, height_km, sp)['nodes']
            params['island_density'] = island_density(params) or 'medium'
            pipe = params.get('pipeline') or 'playable'
            quick = est.quick_overview(params.get('quality'), pipe)
            params['quick_render'] = quick
            job = dict(id=jid, name='web-' + jid, status='queued', created=_now(), owner_pid=os.getpid(), started=None, finished=None, stage=None,
                       params=params, paths=paths, stages=[], error=None, result=None, gpu_check=gpu,
                       memory_check=dict(available_bytes=avail, recommended_bytes=gate, required_bytes=gate,
                                         hard_limit=False, **{k: advice[k] for k in
                                                              ('constrained', 'time_scale', 'thread_cap',
                                                               'memory_wait_s', 'min_free_gib', 'note')}),
                       disk_check=dict(free_bytes=self.disk_free_bytes(),
                                       estimated_bytes=est.disk_product_bytes(width_km, sp, pipeline=pipe,
                                                                             quick_render=quick, height_km=height_km)['bytes']),
                       estimate=est.scale_chain_time(
                           est.chain(width_km, req.use_gpu, sp, pipeline=pipe, quick_render=quick, height_km=height_km),
                           advice['time_scale']))
            with self._lock:
                self._jobs[jid] = job
                self._active = jid
                self._save(job)
        except BaseException:
            with self._lock:
                self._busy = False
            raise
        threading.Thread(target=self._run, args=(jid,), daemon=True, name='worldgen-' + jid).start()
        return self.view(jid)

    def _schedule_flags(self, params):
        sched = params.get('memory_schedule') or {}
        fast_extra, details_extra = [], []
        if sched.get('min_free_gib') is not None:
            fast_extra += ['--min-free-gib', str(sched['min_free_gib'])]
        if sched.get('memory_wait_s') is not None:
            details_extra += ['--memory-wait-s', str(sched['memory_wait_s'])]
        return fast_extra, details_extra

    def default_stages(self, job):
        p, P, r = job['params'], job['paths'], self.root
        tg, py = str(self.tg_python), str(self.web_python)
        width_km, height_km = job_dims(p)
        skeleton_cell = int(p.get('skeleton_cell_km') or est.skeleton_cell_km(width_km, height_km))
        square_side = int(p.get('size_km') or (width_km if width_km == height_km else 0))
        sp = float(p.get('spacing_m') or requested_spacing_m(width_km, height_km, p.get('quality', 'speed'),
                                                             explicit=explicit_rect(p)))
        pipe = p.get('pipeline') or 'playable'
        full = pipe == 'full'
        fast_extra, details_extra = self._schedule_flags(p)
        policy = render_policy(p)
        fast_argv = [tg, str(r / 'app/world_gen/web_island_stage.py'), 'fast',
                     '--input', str(Path(P['world_dir'])/'island-mountains'/'world-input.json'), '--out', P['fast_dir'],
                     '--spacing-m', str(sp)]
        if full:
            fast_argv.append('--world-processes')
        fast_argv += fast_extra
        stages = [
            Stage('skeleton', '板块骨架 (orogen)',
                  [tg, str(r / 'tools/generate_world_skeleton.py'), '--preset', p['world_type']]
                  + (['--width-km', str(width_km), '--height-km', str(height_km)]
                     if (width_km, height_km) != (square_side, square_side) else ['--size-km', str(square_side)])
                  + ['--name', job['name'], '--seed', str(p['seed']), '--ocean', repr(float(p['ocean_fraction'])), '--ridges', 'orogen',
                     '--mountain-area', repr(float(p['mountain_area'])), '--cell-km', str(skeleton_cell),
                     '--out-root', str(Path(P['world_dir']).parent), '--record-history']),
            Stage('islands', 'Frozen islands and fixed 1km mountain plans (CPU)'
                  + ('（矩形·延后 1km 资格分析）' if defer_island_analysis(p) else '')
                  + ('（候选密度 low）' if island_density(p) else '')
                  + ('（岛群聚类布局）' if island_layout(p) else ''),
                  [tg, str(r / 'app/world_gen/web_island_stage.py'), 'prepare', '--skeleton', P['skeleton'],
                   '--run', str(Path(P['world_dir'])/'skeleton-run.json'), '--out', str(Path(P['world_dir'])/'ocean-islands'),
                   '--world-type', p['world_type'], '--seed', str(p['seed'])]
                  + (['--defer-mountain-analysis'] if defer_island_analysis(p) else [])
                   + (['--island-density', island_density(p)] if island_density(p) else [])
                   + (['--island-layout', island_layout(p)] if island_layout(p) else [])),
            Stage('island-mountains', 'Island TD interiors' if p['use_gpu'] else 'Island mountain pending state (CPU)',
                  [tg, str(r / 'app/world_gen/web_island_stage.py'), 'schedule',
                   '--input', str(Path(P['world_dir'])/'ocean-islands'/'prepared.json'),
                   '--out', str(Path(P['world_dir'])/'island-mountains')] + (['--use-gpu'] if p['use_gpu'] else []), gpu=p['use_gpu']),
            Stage('fast', 'Final world layer with frozen islands (CPU)', fast_argv)]
        if p.get('geography_features'):
            stages[0].argv += ['--geography-json', wc.canonical(p['geography_features'])]
        stages.append(Stage('render', '发布粗世界预览' + ('（1200 px 概览）' if policy['quick_overview'] else ''),
                     [py, str(r/'tools/render_world_relief_atlas.py'), '--product', P['fast_dir'], '--out', P['atlas_dir']]
                     + policy['extra_argv']))
        if full:
            stages.append(Stage('details', '重点河段、湖口与河口续算',
                         [tg, str(r/'app/world_gen/world_process_details.py'), '--preview', P['fast_dir'],
                          '--out', P['detail_dir']] + (['--use-gpu'] if p['use_gpu'] else []) + details_extra, gpu=p['use_gpu']))
            stages.append(Stage('final-render', '详细版本成图',
                         [py, str(r/'tools/render_world_relief_atlas.py'), '--product', P['detail_dir'], '--out', P['final_atlas_dir']]))
            if p['use_gpu']:
                stages += [
                    Stage('td', 'TD 粗模型山脉走向 (GPU)',
                          [tg, str(r / 'app/world_gen/web_td_stage.py'), '--skeleton', P['skeleton'], '--out', P['td_dir'], '--device', 'cuda',
                           '--skip-ocean-km', str(TD_SKIP_OCEAN_KM), '--steps', str(TD_STEPS),
                           '--preview', str(Path(P['job_dir']) / 'td-preview.png')], gpu=True),
                    Stage('compare', 'TD 与快速层走向对比',
                          [py, str(r / 'app/world_gen/td_fast_compare.py'), '--td', P['td_dir'], '--fast', P['fast_dir'],
                           '--json', str(Path(P['job_dir']) / 'td-vs-fast.json')])]
        stages += [Stage('summary', '汇总与产品校验', fn=summarize)]
        return stages

    def upgrade_stages(self, job):
        """Reuse skeleton/islands/mountains; rebuild fast (+ optional details) at a new spacing."""
        p, P, r = job['params'], job['paths'], self.root
        tg, py = str(self.tg_python), str(self.web_python)
        sp = float(p['spacing_m'])
        pipe = p.get('pipeline') or 'playable'
        full = pipe == 'full'
        fast_extra, details_extra = self._schedule_flags(p)
        policy = render_policy(p)
        fast_argv = [tg, str(r / 'app/world_gen/web_island_stage.py'), 'fast',
                     '--input', str(Path(P['world_dir'])/'island-mountains'/'world-input.json'), '--out', P['fast_dir'],
                     '--spacing-m', str(sp)]
        if full:
            fast_argv.append('--world-processes')
        fast_argv += fast_extra
        stages = [
            Stage('fast', 'Final world layer with frozen islands (CPU)', fast_argv),
            Stage('render', '发布粗世界预览' + ('（1200 px 概览）' if policy['quick_overview'] else ''),
                  [py, str(r/'tools/render_world_relief_atlas.py'), '--product', P['fast_dir'], '--out', P['atlas_dir']]
                  + policy['extra_argv']),
        ]
        if full:
            stages.append(Stage('details', '重点河段、湖口与河口续算',
                          [tg, str(r/'app/world_gen/world_process_details.py'), '--preview', P['fast_dir'],
                           '--out', P['detail_dir']] + (['--use-gpu'] if p['use_gpu'] else []) + details_extra, gpu=p['use_gpu']))
            stages.append(Stage('final-render', '详细版本成图',
                          [py, str(r/'tools/render_world_relief_atlas.py'), '--product', P['detail_dir'], '--out', P['final_atlas_dir']]))
            if p['use_gpu'] and Path(P['td_dir']).is_dir():
                stages.append(Stage('compare', 'TD 与快速层走向对比',
                                    [py, str(r / 'app/world_gen/td_fast_compare.py'), '--td', P['td_dir'], '--fast', P['fast_dir'],
                                     '--json', str(Path(P['job_dir']) / 'td-vs-fast.json')]))
        stages.append(Stage('summary', '汇总与产品校验', fn=summarize))
        return stages

    def upgrade(self, jid, req: WorldGenUpgradeRequest):
        src = self._jobs.get(jid)
        if src is None:
            path = self.jobs_dir / ('web-' + jid) / 'job.json'
            if path.is_file():
                src = json.loads(path.read_text(encoding='utf-8'))
                with self._lock:
                    self._jobs[jid] = src
            else:
                raise WorldGenRefused(404, f'找不到任务 {jid}')
        if src.get('status') != 'succeeded':
            raise WorldGenRefused(409, '只能对已成功的任务提高/更换采样精度')
        parent_fast = Path(src['paths']['fast_dir']) / 'manifest.json'
        if not parent_fast.is_file():
            raise WorldGenRefused(409, '源任务缺少 fast 层 manifest，无法升级')
        parent_man = json.loads(parent_fast.read_text(encoding='utf-8'))
        parent_spacing = float(parent_man.get('grid', {}).get('spacing_m')
                               or parent_man.get('parameters', {}).get('spacing_m')
                               or src['params'].get('spacing_m') or est.FAST_SPACING_M)
        parent_identity = parent_man.get('identity')
        width_km, height_km = job_dims(src['params'])
        new_spacing = requested_spacing_m(width_km, height_km, req.quality, explicit=explicit_rect(src['params']))
        if abs(new_spacing - parent_spacing) < 1e-9:
            raise WorldGenRefused(409, f'目标精度与源产物相同（{new_spacing:g} m），未启动')
        world_input = Path(src['paths']['world_dir']) / 'island-mountains' / 'world-input.json'
        if not world_input.is_file():
            raise WorldGenRefused(409, '源任务缺少 island-mountains/world-input.json，无法复用')
        with self._lock:
            if self._busy:
                raise WorldGenRefused(409, f'已有生成任务（{self._active or "正在启动"}）在运行，同一时间只允许一个')
            self._busy = True
        try:
            if not self.tg_python.is_file():
                raise WorldGenRefused(503, f'Terragenesis 解释器不存在：{self.tg_python}')
            avail, gate = int(self.memory()), self.memory_gate_bytes(width_km, new_spacing, height_km=height_km)
            advice = memory_advice(avail, gate)
            use_gpu = bool(src['params'].get('use_gpu'))
            gpu = None
            if use_gpu:
                gpu = self.gpu_status(refresh=True)
                if not gpu['usable']:
                    raise WorldGenRefused(409, '不能使用显卡：' + gpu['reason'])
            for _ in range(20):
                nid = time.strftime('%Y%m%d-%H%M%S') + '-' + secrets.token_hex(2)
                paths = self._paths(nid)
                # reuse skeleton / islands / mountains from the source job
                paths['world_dir'] = src['paths']['world_dir']
                paths['skeleton'] = src['paths']['skeleton']
                paths['td_dir'] = src['paths']['td_dir']
                if nid not in self._jobs and not any(Path(paths[k]).exists() for k in ('fast_dir', 'job_dir')):
                    break
            else:
                raise WorldGenRefused(500, '无法分配新的任务目录')
            params = dict(src['params'])
            pipe = req.pipeline or params.get('pipeline') or 'playable'
            # The islands are reused as prepared: keep the density and the layout they were actually built with
            # (the recorded param, else the frozen record, else the historical defaults 'medium' / 'old'). Never
            # re-derive either from the new quality/size — an upgrade does not re-run prepare.
            frozen_record = saved_island_record(src)[0]
            frozen_density = island_record_density(params, frozen_record)
            frozen_layout = island_record_layout(params, frozen_record)
            params.update(quality=req.quality, spacing_m=new_spacing, upgrade_of=jid,
                          parent_fast_identity=parent_identity, parent_spacing_m=parent_spacing,
                          memory_schedule=advice, pipeline=pipe, island_density=frozen_density,
                          island_layout=frozen_layout)
            quick = est.quick_overview(req.quality, pipe)
            params['quick_render'] = quick
            job = dict(id=nid, name='web-' + nid, status='queued', created=_now(), owner_pid=os.getpid(),
                       started=None, finished=None, stage=None, params=params, paths=paths, stages=[],
                       error=None, result=None, gpu_check=gpu,
                       memory_check=dict(available_bytes=avail, recommended_bytes=gate, required_bytes=gate,
                                         hard_limit=False, **{k: advice[k] for k in
                                                              ('constrained', 'time_scale', 'thread_cap',
                                                               'memory_wait_s', 'min_free_gib', 'note')}),
                       disk_check=dict(free_bytes=self.disk_free_bytes(),
                                       estimated_bytes=est.disk_product_bytes(width_km, new_spacing, pipeline=pipe,
                                                                             quick_render=quick, height_km=height_km)['bytes']),
                       estimate=est.scale_chain_time(
                           est.chain(width_km, use_gpu, new_spacing, pipeline=pipe, quick_render=quick,
                                     height_km=height_km), advice['time_scale']),
                       upgrade_of=jid)
            with self._lock:
                self._jobs[nid] = job
                self._active = nid
                self._save(job)
            stages = self.upgrade_stages(job)
        except BaseException:
            with self._lock:
                self._busy = False
            raise
        threading.Thread(target=self._run, args=(nid, stages), daemon=True, name='worldgen-upgrade-' + nid).start()
        return self.view(nid)

    def _env(self, gpu, schedule=None):
        env = dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
        if not gpu:
            env['CUDA_VISIBLE_DEVICES'] = '-1'   # '' does not hide the GPU; only the TD stage may see it
        cap = (schedule or {}).get('thread_cap')
        if cap:
            for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
                        'NUMBA_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
                env[key] = str(int(cap))
        return env

    def _run_proc(self, jid, stage, log, rec):
        log.write(f'\n===== {stage.name} {_now()} =====\n$ {" ".join(stage.argv)}\n')
        log.flush()
        flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0) | getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
        with self._lock:
            schedule = (self._jobs.get(jid) or {}).get('params', {}).get('memory_schedule')
        proc = subprocess.Popen(stage.argv, cwd=str(self.root), stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                env=self._env(stage.gpu, schedule), creationflags=flags)
        with self._lock:
            self._proc = proc
            cancelled = jid in self._cancel
        if cancelled:
            _kill_tree(proc)
        mon = None
        if stage.gpu:
            mon = dict(baseline_mib=self.gpu_sampler(), peak_mib=None, samples=0,
                       note='nvidia-smi memory.used of the whole device (all processes), sampled every 1 s')

            def watch():
                while proc.poll() is None:
                    v = self.gpu_sampler()
                    if v is not None:
                        mon['peak_mib'] = v if mon['peak_mib'] is None else max(mon['peak_mib'], v)
                        mon['samples'] += 1
                    time.sleep(1.0)
            th = threading.Thread(target=watch, daemon=True)
            th.start()
        rc = proc.wait()
        if mon is not None:
            th.join(timeout=5)
            if mon['peak_mib'] is not None and mon['baseline_mib'] is not None:
                mon['delta_mib'] = mon['peak_mib'] - mon['baseline_mib']
            rec['gpu_monitor'] = mon
        with self._lock:
            self._proc = None
        return rc

    def _run(self, jid, resumed_stages=None):
        job = self._jobs[jid]
        log = None
        try:
            stages = resumed_stages if resumed_stages is not None else self.stage_builder(job)
            with self._lock:
                job['stages'] = [dict(name=s.name, label=s.label, status='pending') for s in stages]
                job.update(status='running', started=_now())
                self._save(job)
            Path(job['paths']['log']).parent.mkdir(parents=True, exist_ok=True)
            log = open(job['paths']['log'], 'a', encoding='utf-8')
            t_job = time.perf_counter()
            outcome = 'succeeded'
            for i, s in enumerate(stages):
                rec = job['stages'][i]
                with self._lock:
                    if jid in self._cancel:
                        outcome = 'cancelled'
                        break
                    rec.update(status='running', started=_now())
                    job['stage'] = s.name
                    self._save(job)
                t0 = time.perf_counter()
                if s.argv:
                    rc = self._run_proc(jid, s, log, rec)
                else:
                    log.write(f'\n===== {s.name} {_now()} (in-process) =====\n')
                    log.flush()
                    try:
                        out = s.fn(job)
                        with self._lock:
                            job['result'] = _jsonable(out)
                        rc = 0
                    except Exception as e:
                        log.write(traceback.format_exc())
                        rec['error'] = f'{type(e).__name__}: {e}'[:500]
                        rc = 1
                with self._lock:
                    rec.update(finished=_now(), seconds=round(time.perf_counter() - t0, 2), returncode=rc)
                    if jid in self._cancel:
                        rec['status'], outcome = 'cancelled', 'cancelled'
                    elif rc != 0:
                        rec['status'], outcome = 'failed', 'failed'
                        job['error'] = f'{s.label} 失败（退出码 {rc}），见日志尾部'
                    else:
                        rec['status'] = 'succeeded'
                    self._save(job)
                if outcome != 'succeeded':
                    break
            with self._lock:
                for rec in job['stages']:
                    if rec['status'] == 'pending':
                        rec['status'] = 'skipped'
                if outcome == 'cancelled':
                    job['error'] = '已取消；已写出的部分产物保留在原目录，未删除'
                job.update(status=outcome, seconds_total=round(time.perf_counter() - t_job, 2),
                           finished=_now(), stage=None)
        except Exception as e:
            with self._lock:
                job.update(status='failed', error=f'{type(e).__name__}: {e}'[:500],
                           finished=_now(), stage=None)
            if log:
                log.write(traceback.format_exc())
        finally:
            if log:
                log.close()
            with self._lock:
                job.setdefault('finished', _now())
                job['stage'] = None
                self._cancel.discard(jid)
                self._active, self._proc, self._busy = None, None, False
                self._save(job)

    def cancel(self, jid):
        with self._lock:
            job = self._get(jid)
            if job['status'] in FINISHED:
                raise WorldGenRefused(409, f'任务已结束（{job["status"]}），不能取消')
            self._cancel.add(jid)
            proc = self._proc if self._active == jid else None
        _kill_tree(proc)
        return self.view(jid)

    def _get(self, jid):
        if not isinstance(jid, str) or not JOB_ID_RE.match(jid) or jid not in self._jobs:
            raise WorldGenRefused(404, '没有这个生成任务')
        return self._jobs[jid]

    def view(self, jid, tail_lines=60):
        with self._lock:
            job = json.loads(json.dumps(self._get(jid), default=str))
        log = Path(job['paths']['log'])
        tail = []
        if log.is_file():
            with open(log, 'rb') as f:
                f.seek(0, 2)
                size = f.tell()
                f.seek(max(0, size - 65536))
                tail = f.read().decode('utf-8', errors='replace').splitlines()[-tail_lines:]
        job['log_tail'] = tail
        job['previews'] = [k for k, (base, fn) in PREVIEWS.items() if base in job['paths'] and (Path(job['paths'][base]) / fn).is_file()]
        job['paths_relative'] = {k: _rel(v, self.root) for k, v in job['paths'].items()}
        return job

    def list(self):
        with self._lock:
            jobs = sorted(self._jobs.values(), key=lambda j: j['created'], reverse=True)
            return [dict(id=j['id'], status=j['status'], created=j['created'], finished=j.get('finished'), params=j['params'],
                         stage=j.get('stage'), seconds_total=j.get('seconds_total')) for j in jobs]

    def preview_path(self, jid, name):
        with self._lock:
            job = self._get(jid)
        if name not in PREVIEWS:
            raise WorldGenRefused(404, '没有这种预览图')
        base, fn = PREVIEWS[name]
        if base not in job['paths']:
            raise WorldGenRefused(404, '旧任务未登记该版本')
        f = Path(job['paths'][base]) / fn
        if not f.is_file():
            raise WorldGenRefused(404, '预览图还没有生成')
        return f

    def continue_job(self, jid):
        """Explicitly resume saved author work; completed stages stay frozen."""
        with self._lock:
            job = self._get(jid)
            if self._busy:
                raise WorldGenRefused(409, '已有世界任务运行中')
            if job['status'] not in FINISHED:
                raise WorldGenRefused(409, '任务尚未停止')
            if job['status'] == 'succeeded':
                raise WorldGenRefused(409, '任务已完成；后续版本应通过显式续算入口准备')
            foreign = self._foreign_active()
            if foreign:
                raise WorldGenRefused(409, '另一个服务进程有世界任务运行中')
            width_km, height_km = job_dims(job['params'])
            sp = job['params'].get('spacing_m') or requested_spacing_m(width_km, height_km, job['params'].get('quality', 'speed'),
                                                                      explicit=explicit_rect(job['params']))
            avail, gate = int(self.memory()), self.memory_gate_bytes(width_km, sp, height_km=height_km)
            advice = memory_advice(avail, gate)
            job['params']['memory_schedule'] = advice
            job['memory_check'] = dict(available_bytes=avail, recommended_bytes=gate, required_bytes=gate,
                                       hard_limit=False, **{k: advice[k] for k in
                                                            ('constrained', 'time_scale', 'thread_cap',
                                                             'memory_wait_s', 'min_free_gib', 'note')})
            if job['params'].get('use_gpu'):
                gpu = self.gpu_status(refresh=True)
                if not gpu['usable'] or self.gpu_jobs():
                    raise WorldGenRefused(409, '当前显卡状态不允许恢复此 GPU 任务')
            completed = {row['name'] for row in job.get('stages', []) if row.get('status') == 'succeeded'}
            stages = self.stage_builder(job)
            for stage in stages:
                if stage.name in completed:
                    stage.argv = None
                    stage.fn = lambda current, name=stage.name: dict(reused_completed_stage=name)
                elif stage.name == 'fast':
                    checkpoint = Path(job['paths']['fast_dir'])/'world-processes'/'checkpoint.json'
                    if checkpoint.exists():
                        stage.argv.append('--resume-processes')
            job.update(status='queued', finished=None, error=None)
            self._busy, self._active = True, jid
            self._save(job)
        threading.Thread(target=self._run, args=(jid, stages), daemon=True, name='worldgen-resume-'+jid).start()
        return self.view(jid)


def _rel(p, root):
    try:
        return Path(p).resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return str(p)


def _pid_alive(pid):
    """True when a process with this pid exists. Never signals it (os.kill(pid, 0) would terminate it on Windows)."""
    if not isinstance(pid, int) or pid <= 0:
        return False
    if sys.platform == 'win32':
        import ctypes
        k32 = ctypes.windll.kernel32
        h = k32.OpenProcess(0x1000, False, pid)        # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        try:
            code = ctypes.c_ulong()
            return bool(k32.GetExitCodeProcess(h, ctypes.byref(code))) and code.value == 259   # STILL_ACTIVE
        finally:
            k32.CloseHandle(h)
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def island_record_density(params, record=None):
    """Density actually frozen with this world's islands (record first, else the recorded job param, else medium).

    Never derived from the current request's quality/size: an upgrade reuses the source islands and must not claim
    a density that was never prepared.
    """
    if record:
        return saved_island_density(record)
    return saved_island_density({'island_density': (params or {}).get('island_density')})


def island_record_layout(params, record=None):
    """Layout actually frozen with this world's islands (record first, else the recorded job param, else 'old').

    Never derived from the current request's quality/size: an upgrade reuses the source islands and must not claim
    a layout that was never prepared.
    """
    if record:
        return saved_island_layout(record)
    return saved_island_layout({'island_layout': (params or {}).get('island_layout')})


def island_record_analysis(record):
    """(status, deferred) from the saved island record; 'pending-analysis' is never reported as a completed analysis."""
    return saved_island_analysis(record)


def saved_island_record(job):
    """The island preparation actually frozen for this job's world, and where it came from.

    ``upgrade`` shares ``world_dir`` with the source job, so this reads the *real* prepared record (density,
    analysis status) instead of guessing from the current request's quality/size. The job's own paths are searched
    first, then the upgrade source's world directory.
    """
    prepared = _read_json(Path(job['paths']['world_dir']) / 'ocean-islands' / 'prepared.json')
    if prepared:
        return prepared, 'ocean-islands/prepared.json'
    fm = _read_json(Path(job['paths']['fast_dir']) / 'manifest.json') or {}
    record = (fm.get('island_mountains') or {}).get('record')
    if record:
        return record, 'fast manifest island_mountains.record'
    return {}, None


# ------------------------------------------------------------------------------------------------------------- summary
def summarize(job):
    """Key numbers from the frozen products; the fast layer is loaded through app.map_source (identity verified)."""
    import numpy as np
    from app.map_source import load_source
    P = job['paths']
    out = dict(params=job['params'])
    pol = render_policy(job['params'])
    out['render_policy'] = dict(quick_overview=pol['quick_overview'], width_px=pol['width_px'], note=pol['note'],
                                overview_only=pol['quick_overview'], extra_pages=not pol['quick_overview'])
    sk = _read_json(Path(P['world_dir']) / 'skeleton-run.json') or {}
    a, t = sk.get('actual', {}), sk.get('targets', {})
    width_km, height_km = job_dims(job['params'])
    sk_cfg = (sk.get('product') or {})
    record, record_source = saved_island_record(job)
    density = island_record_density(job['params'], record)
    layout = island_record_layout(job['params'], record)
    layout_policy = (record.get('island_config') or {}).get('layout_policy') if isinstance(record, dict) else None
    analysis_status, analysis_deferred = island_record_analysis(record)
    requirement = island_density(job['params'])
    out['world'] = dict(width_km=width_km, height_km=height_km, area_km2=width_km * height_km,
                        rectangular=width_km != height_km,
                        skeleton_cells=list(sk_cfg.get('shape_zx') or []) or None,
                        skeleton_cell_km=job['params'].get('skeleton_cell_km'),
                        spacing_m=job['params'].get('spacing_m'),
                        spacing_source=('rectangular: largest whole-metre divisor of both sides <= band target'
                                        if explicit_rect(job['params'])
                                        else 'square table (1600 / 5000 / 10000)'),
                        fast_nodes=job['params'].get('fast_nodes'),
                        island_density=density,
                        island_density_requested=requirement or DEFAULT_ISLAND_DENSITY,
                        island_density_source=record_source,
                        island_density_note=(None if density != 'low' else
                                             '已保存的岛产品是低候选密度：只减少全域岛候选数量（把冻结 manifest '
                                             '压回编码上限内），单岛几何/峰高/TD 口径不变；不宣称完成了高密度岛链'),
                        island_layout=layout,
                        island_layout_policy=layout_policy,
                        island_layout_requested=(job['params'].get('island_layout') or DEFAULT_ISLAND_LAYOUT),
                        island_layout_source=record_source,
                        island_analysis_deferred=analysis_deferred,
                        island_analysis_status=analysis_status)
    out['skeleton'] = dict(algorithm=sk.get('algorithm'), identity=sk.get('identity'),
                           plate_identity=(sk.get('product') or {}).get('plate_identity'),
                           ocean_fraction=a.get('ocean_fraction'), ocean_target=t.get('ocean_fraction'),
                           mountain_area_land_fraction=a.get('mountain_area_land_fraction'),
                           mountain_area_target=t.get('mountain_area_target'), mountain_area_band=t.get('mountain_area_land_fraction_band'),
                           mountain_area_within_band=a.get('mountain_area_within_band'),
                           high_mountain_land_fraction=a.get('high_mountain_land_fraction'),
                           seconds=sk.get('seconds'), peak_rss_bytes=sk.get('peak_rss_bytes'))
    if sk.get('geography'):
        out['skeleton']['geography'] = sk['geography']
    fdir = Path(P['fast_dir'])
    fm = _read_json(fdir / 'manifest.json')
    if fm is None:
        raise FileNotFoundError(f'fast layer manifest missing: {fdir}')
    rs = _read_json(fdir / 'runtime-stats.json') or {}
    src = load_source('world-map-product', fdir, expected_identity=fm['identity'])
    pilot = load_source('world-relief-pilot', fdir, expected_identity=fm['identity'])
    elev = np.load(fdir / 'elevation_m.npy', mmap_mode='r')
    land = np.load(fdir / 'status.npy', mmap_mode='r') == 5
    st = fm.get('statistics', {})
    out['island_mountains'] = fm.get('island_mountains', {}).get('record', {}).get('mountains')
    out['island_analysis'] = fm.get('island_mountains', {}).get('record', {}).get('analysis')
    out['world_processes'] = dict(coarse=fm.get('world_processes'),
        continuation=_read_json(Path(P.get('detail_dir', fdir.parent/(fdir.name+'-detailed')))/'continuation.json'))
    from .world_process_adapter import environment_status
    if fm.get('world_processes'):
        out['world_processes']['environment_status'] = environment_status(fm['world_processes']['metadata'])
    final_dir = Path(P.get('detail_dir', fdir.parent/(fdir.name+'-detailed')))
    final_manifest = _read_json(final_dir/'manifest.json')
    if final_manifest:
        final_source = load_source('world-map-product', final_dir, expected_identity=final_manifest['identity'])
        continuation = out['world_processes']['continuation'] or {}
        out['world_processes']['published'] = dict(identity=final_source.info.identity,
            parent_preview_identity=final_manifest.get('parent_preview_identity'),
            detailed_regions=continuation.get('detailed_regions', []),
            pending_regions=continuation.get('pending_regions', []),
            status=continuation.get('status'),
            process_stages=final_manifest.get('world_processes', {}).get('metadata', {}).get('stages'))
        out['world_processes']['published']['environment_status'] = environment_status(
            final_manifest.get('world_processes', {}).get('metadata', {}))
    out['fast'] = dict(
        schema=fm['schema'], algorithm_version=fm.get('algorithm_version'), identity=fm['identity'], routing=fm.get('routing'),
        map_source=dict(kind=src.info.kind, schema=src.info.schema, identity=src.info.identity, world_seed=src.info.world_seed,
                        shape_zx=list(src.info.shape_zx), spacing_m=src.info.spacing_m, atlas_alias_identity=pilot.info.identity,
                        identity_matches=src.info.identity == fm['identity'] == pilot.info.identity),
        ocean_fraction=1.0 - float(st['land_fraction']) if 'land_fraction' in st else None,
        high_mountain_land_fraction_gt1500m=float((np.asarray(elev)[land] > 1500).mean()) if land.any() else None,
        max_elevation_m=st.get('elevation_max_m'), river_segments=st.get('river_segments'), kept_lakes=st.get('kept_lakes'),
        seconds=rs.get('total_seconds'), peak_working_set_mb=rs.get('peak_working_set_mb'))
    if job['params'].get('use_gpu'):
        tdir = Path(P['td_dir'])
        tm, trs = _read_json(tdir / 'manifest.json') or {}, _read_json(tdir / 'runtime-stats.json') or {}
        peak = _read_json(tdir.parent / 'td-gpu-peak.json') or {}
        mon = next((s.get('gpu_monitor') for s in job['stages'] if s['name'] == 'td'), None)
        out['td'] = dict(identity=tm.get('identity'), algorithm=tm.get('algorithm'), device=trs.get('device'),
                         device_name=(trs.get('device_info') or {}).get('name') or peak.get('device_name'),
                         tiles=trs.get('tiles'), tiles_total=trs.get('tiles_total'), tiles_skipped=trs.get('tiles_skipped'),
                         model_load_seconds=trs.get('model_load_seconds'), generate_seconds=trs.get('generate_seconds'),
                         seconds_per_tile=trs.get('seconds_per_tile'), peak_working_set_bytes=trs.get('peak_working_set_bytes'),
                         torch_cuda_max_allocated_mib=peak.get('max_memory_allocated_mib'),
                         torch_cuda_max_reserved_mib=peak.get('max_memory_reserved_mib'), nvidia_smi=mon,
                         compare_with_fast=_read_json(Path(P['job_dir']) / 'td-vs-fast.json'))
    adir = Path(P['atlas_dir'])
    out['atlas'] = dict(files=sorted(f.name for f in adir.glob('*.png')) if adir.is_dir() else [],
                        source=(_read_json(adir / 'atlas-source.json') or {}).get('identity'))
    final_atlas = Path(P.get('final_atlas_dir', final_dir/'atlas'))
    out['final_atlas'] = dict(files=sorted(f.name for f in final_atlas.glob('*.png')) if final_atlas.is_dir() else [],
                              source=(_read_json(final_atlas/'atlas-source.json') or {}).get('identity'))
    return out
