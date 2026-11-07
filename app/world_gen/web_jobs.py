"""Author-side world generation jobs for the web UI (one job at a time, every heavy step is a child process).

Chain: skeleton -> frozen islands + bounded 1km plans -> explicit island TD (or CPU pending) -> final fast 2km world -> optional TD coarse
ridge field on the GPU + comparison with the fast layer -> atlas render -> summary / map_source check.
Skeleton, fast layer and TD need numba / torch, so they run with the Terragenesis interpreter (imported read-only, nothing there
is written). The atlas render runs with this server's own interpreter. Products go to new directories named web-<job id>;
an existing directory is never reused or overwritten. No D8 anywhere: the fast layer routes on the irregular Delaunay graph.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import subprocess
import sys
import threading
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

from pydantic import BaseModel, ConfigDict, Field

from . import config as wc, estimates as est
from .sysmem import available_memory_bytes, command_lines

ROOT = Path(__file__).resolve().parents[2]
TG_PYTHON = ROOT.parent / '山川形意Terragenesis' / 'runtime' / 'venv' / 'Scripts' / 'python.exe'
SIZES_KM = (1600, 5000, 10000)
SIZE_LABELS = {1600: '1600 km', 5000: '5000 km', 10000: '10000 km（需显卡 / 较慢）'}
MIN_FREE_BYTES = 2 * 2 ** 30
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


class WorldGenRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    world_type: Literal['multi-continent', 'pangaea', 'archipelago', 'two-continents', 'inland-sea'] = 'multi-continent'
    size_km: Literal[1600, 5000, 10000] = 1600
    ocean_fraction: float = Field(0.6, ge=wc.OCEAN_RANGE[0], le=wc.OCEAN_RANGE[1], allow_inf_nan=False)
    mountain_area: float = Field(0.25, ge=0.20, le=0.30, allow_inf_nan=False)
    seed: int = Field(wc.DEFAULT_WORLD_SEED, ge=0, lt=2 ** 63, strict=True)
    use_gpu: bool = Field(False, strict=True)


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
    def memory_gate_bytes(size_km):
        return max(MIN_FREE_BYTES, int(est.world_process_peak_mb(size_km) * 2 ** 20))

    def options(self, refresh_gpu=False):
        try:
            avail = int(self.memory())
        except Exception:
            avail = None
        with self._lock:
            active = self._active
        return dict(
            world_types=[dict(id=t, label=wc.WORLD_TYPE_LABELS[t]) for t in wc.WORLD_TYPES],
            sizes=[dict(km=s, label=SIZE_LABELS[s], slow=s == 10000) for s in SIZES_KM],
            defaults=dict(world_type='multi-continent', size_km=1600, ocean_fraction=0.6, mountain_area=0.25,
                          seed=wc.DEFAULT_WORLD_SEED, use_gpu=False),
            ranges=dict(ocean_fraction=list(wc.OCEAN_RANGE), mountain_area=[0.20, 0.30], seed=[0, 2 ** 63 - 1]),
            gpu=self.gpu_status(refresh_gpu),
            estimates={str(s): dict(cpu=est.chain(s, False), gpu=est.chain(s, True)) for s in SIZES_KM},
            memory=dict(available_bytes=avail, min_free_bytes={str(s): self.memory_gate_bytes(s) for s in SIZES_KM}),
            active_job=active,
            td=dict(skip_ocean_km=TD_SKIP_OCEAN_KM, steps=TD_STEPS, spec='docs/td-coarse-ridges-spec.md §6'),
            notes=['estimates 标 measured 的是本机实测，extrapolated 是推算',
                   'Final world: 2km CPU graph hydrology; GPU additionally prepares qualified island interiors and coarse ridge comparison'])

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
            avail, gate = int(self.memory()), self.memory_gate_bytes(req.size_km)
            if avail < gate:
                raise WorldGenRefused(409, f'可用内存 {avail / 2 ** 30:.2f} GiB，低于所需 {gate / 2 ** 30:.2f} GiB，未启动')
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
            job = dict(id=jid, name='web-' + jid, status='queued', created=_now(), owner_pid=os.getpid(), started=None, finished=None, stage=None,
                       params=req.model_dump(), paths=paths, stages=[], error=None, result=None, gpu_check=gpu,
                       memory_check=dict(available_bytes=avail, required_bytes=gate), estimate=est.chain(req.size_km, req.use_gpu))
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

    def default_stages(self, job):
        p, P, r = job['params'], job['paths'], self.root
        tg, py = str(self.tg_python), str(self.web_python)
        stages = [
            Stage('skeleton', '板块骨架 (orogen)',
                  [tg, str(r / 'tools/generate_world_skeleton.py'), '--preset', p['world_type'], '--size-km', str(p['size_km']),
                   '--name', job['name'], '--seed', str(p['seed']), '--ocean', repr(float(p['ocean_fraction'])), '--ridges', 'orogen',
                   '--mountain-area', repr(float(p['mountain_area'])), '--cell-km', str(est.skeleton_cell_km(p['size_km'])),
                   '--out-root', str(Path(P['world_dir']).parent), '--record-history']),
            Stage('islands', 'Frozen islands and fixed 1km mountain plans (CPU)',
                  [tg, str(r / 'app/world_gen/web_island_stage.py'), 'prepare', '--skeleton', P['skeleton'],
                   '--run', str(Path(P['world_dir'])/'skeleton-run.json'), '--out', str(Path(P['world_dir'])/'ocean-islands'),
                   '--world-type', p['world_type'], '--seed', str(p['seed'])]),
            Stage('island-mountains', 'Island TD interiors' if p['use_gpu'] else 'Island mountain pending state (CPU)',
                  [tg, str(r / 'app/world_gen/web_island_stage.py'), 'schedule',
                   '--input', str(Path(P['world_dir'])/'ocean-islands'/'prepared.json'),
                   '--out', str(Path(P['world_dir'])/'island-mountains')] + (['--use-gpu'] if p['use_gpu'] else []), gpu=p['use_gpu']),
            Stage('fast', 'Final world layer with frozen islands (CPU)',
                  [tg, str(r / 'app/world_gen/web_island_stage.py'), 'fast',
                   '--input', str(Path(P['world_dir'])/'island-mountains'/'world-input.json'), '--out', P['fast_dir'], '--world-processes'])]
        stages.append(Stage('render', '发布粗世界预览',
                     [py, str(r/'tools/render_world_relief_atlas.py'), '--product', P['fast_dir'], '--out', P['atlas_dir']]))
        stages.append(Stage('details', '重点河段、湖口与河口续算',
                     [tg, str(r/'app/world_gen/world_process_details.py'), '--preview', P['fast_dir'],
                      '--out', P['detail_dir']] + (['--use-gpu'] if p['use_gpu'] else []), gpu=p['use_gpu']))
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

    def _env(self, gpu):
        env = dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
        if not gpu:
            env['CUDA_VISIBLE_DEVICES'] = '-1'   # '' does not hide the GPU; only the TD stage may see it
        return env

    def _run_proc(self, jid, stage, log, rec):
        log.write(f'\n===== {stage.name} {_now()} =====\n$ {" ".join(stage.argv)}\n')
        log.flush()
        flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0) | getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
        proc = subprocess.Popen(stage.argv, cwd=str(self.root), stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                env=self._env(stage.gpu), creationflags=flags)
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
                job.update(status=outcome, seconds_total=round(time.perf_counter() - t_job, 2))
        except Exception as e:
            with self._lock:
                job.update(status='failed', error=f'{type(e).__name__}: {e}'[:500])
            if log:
                log.write(traceback.format_exc())
        finally:
            if log:
                log.close()
            with self._lock:
                job.update(finished=_now(), stage=None)
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
            if self.memory() < self.memory_gate_bytes(job['params']['size_km']):
                raise WorldGenRefused(409, '可用内存不足以恢复世界任务')
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


# ------------------------------------------------------------------------------------------------------------- summary
def summarize(job):
    """Key numbers from the frozen products; the fast layer is loaded through app.map_source (identity verified)."""
    import numpy as np
    from app.map_source import load_source
    P = job['paths']
    out = dict(params=job['params'])
    sk = _read_json(Path(P['world_dir']) / 'skeleton-run.json') or {}
    a, t = sk.get('actual', {}), sk.get('targets', {})
    out['skeleton'] = dict(algorithm=sk.get('algorithm'), identity=sk.get('identity'),
                           plate_identity=(sk.get('product') or {}).get('plate_identity'),
                           ocean_fraction=a.get('ocean_fraction'), ocean_target=t.get('ocean_fraction'),
                           mountain_area_land_fraction=a.get('mountain_area_land_fraction'),
                           mountain_area_target=t.get('mountain_area_target'), mountain_area_band=t.get('mountain_area_land_fraction_band'),
                           mountain_area_within_band=a.get('mountain_area_within_band'),
                           high_mountain_land_fraction=a.get('high_mountain_land_fraction'),
                           seconds=sk.get('seconds'), peak_rss_bytes=sk.get('peak_rss_bytes'))
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
