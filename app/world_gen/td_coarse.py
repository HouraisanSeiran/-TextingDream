"""Terrain Diffusion (TD) coarse model only: large-scale elevation under plate-skeleton conditioning -> mountain trend field.

Only the TD *coarse* U-Net is run (7.68 km lattice, 64x64-cell tiles, stride 48, 20 DPM steps). No latent/base/decoder model.
Terragenesis is imported read-only (vendor ``terrain_diffusion`` + ``diffusion.physical_config``); nothing there is modified.

Conditioning is the same as the TD world layer: the plate skeleton elevation replaces channel 0 of the physical conditioning stack
(``app.world_relief.td_resident.periodic_factory``; outside the finite skeleton the conditioning wraps periodically = scheme C).
Tiles are blended exactly as TD's InfiniteTensor does (linear weight window, sum(w*x)/sum(w)).

Coarse output channels (denormalised): 0 sqrt-elevation (m^.5), 1 p5 elevation spread, 2 temperature, 3 temperature std,
4 precipitation, 5 precipitation cv-like. Elevation in metres = sign(c0)*c0**2 (``_compute_elev`` / ``_compute_climate`` convention).

Lattice: cell (i, j) is the point sample at x = j*7680 m, z = i*7680 m (absolute metres, X east, Z south), not a cell-centre mean.

CPU/GPU: torch device is chosen by ``pick_device``; integrated GPUs without CUDA run on CPU. Pure-array helpers
(``mountain_mask``, ``ridge_orientation_field``, ``extent_cond_range``) need only numpy + scipy and are testable without the model.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
from scipy import ndimage

from .config import derive_subseed, sha256_json
from .sysmem import available_memory_bytes

SCHEMA = 'dream-td-coarse-ridges-v1'
ALGORITHM = 'dream-td-coarse-only-1'
PURPOSE = 'td-coarse-ridges'
COND_SPACING_M = 7680
TILE = 64
STRIDE = 48
STEPS = 20
MIN_FREE_BYTES = 2 * 2 ** 30
MODEL_SUBDIR = 'models/terrain-diffusion-30m'
DEFAULT_ROOT = Path(__file__).resolve().parents[2].parent / '山川形意Terragenesis'


# ----------------------------------------------------------------------------------------------------------------- resources
def terragenesis_root(root=None):
    return Path(root or os.environ.get('TERRAGENESIS_ROOT') or DEFAULT_ROOT).resolve()


def require_memory(min_bytes=MIN_FREE_BYTES):
    free = available_memory_bytes()
    if free < min_bytes:
        raise MemoryError(f'available memory {free / 2**30:.2f} GiB < required {min_bytes / 2**30:.2f} GiB; not starting')
    return free


def peak_working_set_bytes():
    if sys.platform == 'win32':
        import ctypes
        from ctypes import wintypes

        class PMC(ctypes.Structure):
            _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD), ('PeakWorkingSetSize', ctypes.c_size_t),
                        ('WorkingSetSize', ctypes.c_size_t), ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
                        ('QuotaPagedPoolUsage', ctypes.c_size_t), ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
                        ('QuotaNonPagedPoolUsage', ctypes.c_size_t), ('PagefileUsage', ctypes.c_size_t),
                        ('PeakPagefileUsage', ctypes.c_size_t)]
        k32, psapi = ctypes.windll.kernel32, ctypes.windll.psapi
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
        pmc = PMC(); pmc.cb = ctypes.sizeof(PMC)
        if psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb):
            return int(pmc.PeakWorkingSetSize)
        return None
    try:
        import resource
        return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024
    except Exception:
        return None


def pick_device(max_gpu_mib=1024):
    """CUDA only when present with >= max_gpu_mib free; integrated GPUs / DirectML are not used -> CPU."""
    import torch
    info = dict(cuda_available=bool(torch.cuda.is_available()), torch=torch.__version__)
    if info['cuda_available']:
        free, total = torch.cuda.mem_get_info()
        info.update(cuda_free_mib=free // 2**20, cuda_total_mib=total // 2**20)
        if free >= max_gpu_mib * 2**20:
            torch.cuda.set_per_process_memory_fraction(min(1.0, max_gpu_mib * 2**20 / total))
            return torch.device('cuda'), info
    return torch.device('cpu'), info


NO_GPU_MESSAGE = '无可用显卡(no usable CUDA device): --benchmark measures GPU seconds per tile and does not fall back to CPU'


def gpu_status(min_free_mib=1024):
    """(usable, info) for a CUDA device with >= min_free_mib free. Never raises; torch missing / CPU-only torch -> (False, reason)."""
    try:
        import torch
    except Exception as e:  # torch not installed in this environment
        return False, dict(cuda_available=False, reason=f'torch not importable: {type(e).__name__}')
    if not torch.cuda.is_available():
        return False, dict(cuda_available=False, torch=torch.__version__, reason='torch.cuda.is_available() is False')
    free, total = torch.cuda.mem_get_info()
    info = dict(cuda_available=True, torch=torch.__version__, cuda_free_mib=free // 2**20, cuda_total_mib=total // 2**20,
                name=torch.cuda.get_device_name(0))
    return free >= min_free_mib * 2**20, info


# ------------------------------------------------------------------------------------------------------------------ seeds
def coarse_seed(world_seed):
    """Stable named sub-seed of the skeleton's world seed (written into the manifest)."""
    return derive_subseed(int(world_seed), PURPOSE)


# --------------------------------------------------------------------------------------------------------------- geometry
def extent_cond_range(config, spacing=COND_SPACING_M):
    """Conditioning-lattice index ranges [ci0, ci1) x [cj0, cj1) whose points lie inside the finite skeleton extent."""
    x0, z0 = float(config['origin_x_m']), float(config['origin_z_m'])
    x1 = x0 + config['shape'][1] * config['cell_size_m']
    z1 = z0 + config['shape'][0] * config['cell_size_m']
    return (int(math.ceil(z0 / spacing)), int(math.ceil(z1 / spacing)), int(math.ceil(x0 / spacing)), int(math.ceil(x1 / spacing)))


def window_cond_range(center_xz_m, size_m, spacing=COND_SPACING_M):
    n = max(2, int(round(size_m / spacing)))
    cj0 = int(round(center_xz_m[0] / spacing)) - n // 2
    ci0 = int(round(center_xz_m[1] / spacing)) - n // 2
    return ci0, ci0 + n, cj0, cj0 + n


def tile_ranges(ci0, ci1, cj0, cj1, pad=8, stride=STRIDE):
    """Tile index ranges (a..b inclusive) so the union of 64-cell tiles at ``stride`` covers the padded region."""
    def rng(lo, hi):
        lo, hi = lo - pad, hi + pad
        return int(math.floor(lo / stride)), int(math.ceil((hi - TILE) / stride))
    return rng(ci0, ci1), rng(cj0, cj1)


# -------------------------------------------------------------------------------------------------- run options and tile plan
PRECISIONS = ('fp32', 'autocast')
DEFAULT_SKIP_OCEAN_KM = 0.0


@dataclass(frozen=True)
class RunOptions:
    """Parameters of one coarse run.

    stride, steps, pad, skip_ocean_km and precision change the numbers and are written to the manifest (product identity).
    batch_size, threads and device change speed only and are written to runtime-stats.json.
    skip_ocean_km = 0 computes every tile; > 0 skips tiles whose whole 64x64 window is farther than that from land.
    """
    stride: int = STRIDE
    steps: int = STEPS
    pad: int = 8
    skip_ocean_km: float = DEFAULT_SKIP_OCEAN_KM
    precision: str = 'fp32'
    batch_size: int = 1
    threads: int | None = None
    device: str = 'cpu'

    def validate(self):
        if not 8 <= int(self.stride) <= TILE:
            raise ValueError(f'stride must be in [8, {TILE}], got {self.stride}')
        if int(self.steps) < 1:
            raise ValueError(f'steps must be >= 1, got {self.steps}')
        if int(self.batch_size) < 1:
            raise ValueError(f'batch_size must be >= 1, got {self.batch_size}')
        if self.precision not in PRECISIONS:
            raise ValueError(f'precision must be one of {PRECISIONS}, got {self.precision!r}')
        if float(self.skip_ocean_km) < 0:
            raise ValueError('skip_ocean_km must be >= 0')
        return self


def precision_label(precision, device_type='cpu'):
    if precision == 'fp32':
        return 'float32'
    return 'autocast-float16' if device_type == 'cuda' else 'autocast-bfloat16'


class LandSource:
    """Skeleton elevation sampled on the 7.68 km conditioning lattice (periodic outside the finite extent, like the conditioning).

    ``stretch`` k > 1 samples the skeleton as if it were k times larger about its centre (plan-only what-if for bigger worlds).
    ``sea_level_m`` is the land threshold; ``from_skeleton(land_fraction=f)`` sets it so that a fraction f of the skeleton is land.
    """

    def __init__(self, elevation, config, sea_level_m=0.0, stretch=1.0):
        self.elevation = np.asarray(elevation, np.float32)
        self.config = dict(config)
        self.sea_level_m = float(sea_level_m)
        self.stretch = float(stretch)
        cell = float(config['cell_size_m'])
        self.center_x = float(config['origin_x_m']) + config['shape'][1] * cell / 2.0
        self.center_z = float(config['origin_z_m']) + config['shape'][0] * cell / 2.0

    @classmethod
    def from_skeleton(cls, path, land_fraction=None, stretch=1.0):
        from ..world_relief.td_resident import read_plate
        elevation, manifest = read_plate(path)
        sea_level = 0.0
        if land_fraction is not None:
            sea_level = float(np.quantile(elevation, 1.0 - float(land_fraction)))
        return cls(elevation, manifest['config'], sea_level, stretch)

    def land(self, i0, i1, j0, j1):
        """Boolean land mask over lattice rows [i0, i1) and columns [j0, j1)."""
        from ..world_relief.td_resident import sample_periodic
        z = np.arange(i0, i1, dtype=np.float64)[:, None] * COND_SPACING_M
        x = np.arange(j0, j1, dtype=np.float64)[None, :] * COND_SPACING_M
        if self.stretch != 1.0:
            x = self.center_x + (x - self.center_x) / self.stretch
            z = self.center_z + (z - self.center_z) / self.stretch
        return sample_periodic(self.elevation, self.config, x, z) > self.sea_level_m


def land_distance_km(land_source, i0, i1, j0, j1, max_km):
    """Distance (km) from each lattice cell of [i0, i1) x [j0, j1) to the nearest land cell.

    Exact wherever the true distance is <= max_km; larger values only mean "farther than max_km". inf when no land is near.
    """
    margin = int(math.ceil(max_km * 1000.0 / COND_SPACING_M)) + 2
    land = land_source.land(i0 - margin, i1 + margin, j0 - margin, j1 + margin)
    if not land.any():
        return np.full((i1 - i0, j1 - j0), np.inf, np.float32)
    dist = ndimage.distance_transform_edt(~land) * (COND_SPACING_M / 1000.0)
    return dist[margin:-margin, margin:-margin].astype(np.float32)


@dataclass(frozen=True)
class Tile:
    ti: int
    tj: int
    i1: int                   # first lattice row of the 64x64 window
    j1: int                   # first lattice column
    min_land_km: float | None  # distance from the window's nearest cell to land (None when skipping is off)
    computed: bool


@dataclass
class TilePlan:
    ranges: tuple
    options: RunOptions
    r0: int
    c0: int
    height: int
    width: int
    tile_rows: int
    tile_cols: int
    tiles: list

    @property
    def computed_tiles(self):
        return [t for t in self.tiles if t.computed]

    def summary(self):
        computed = sum(1 for t in self.tiles if t.computed)
        km = float(self.options.skip_ocean_km)
        rule = None
        if km > 0:
            rule = (f'tile skipped when every lattice point of its {TILE}x{TILE} window (blend edge included) is more than '
                    f'{km:g} km from the nearest skeleton land cell (elevation > sea level)')
        return dict(tile=TILE, stride=self.options.stride, pad=self.options.pad, tile_rows=self.tile_rows, tile_cols=self.tile_cols,
                    tiles_total=len(self.tiles), tiles_computed=computed, tiles_skipped=len(self.tiles) - computed,
                    skip_ocean_km=km, rule=rule)


def plan_tiles(ranges, options, land_source=None):
    """Tile grid for lattice ranges (ci0, ci1, cj0, cj1) and which tiles are computed under ``options``."""
    ci0, ci1, cj0, cj1 = ranges
    stride = int(options.stride)
    (ta0, ta1), (tb0, tb1) = tile_ranges(ci0, ci1, cj0, cj1, options.pad, stride)
    r0, c0 = ta0 * stride, tb0 * stride
    height = (ta1 - ta0) * stride + TILE
    width = (tb1 - tb0) * stride + TILE
    skip_km = float(options.skip_ocean_km)
    distance = None
    if skip_km > 0:
        if land_source is None:
            raise ValueError('skip_ocean_km > 0 needs a land source')
        distance = land_distance_km(land_source, r0, r0 + height, c0, c0 + width, skip_km)
    tiles = []
    for ti in range(ta0, ta1 + 1):
        for tj in range(tb0, tb1 + 1):
            i1, j1 = ti * stride, tj * stride
            if distance is None:
                nearest, computed = None, True
            else:
                window = distance[i1 - r0:i1 - r0 + TILE, j1 - c0:j1 - c0 + TILE]
                nearest = float(window.min())
                computed = nearest <= skip_km
            tiles.append(Tile(ti, tj, i1, j1, nearest, computed))
    return TilePlan(tuple(ranges), options, r0, c0, height, width, ta1 - ta0 + 1, tb1 - tb0 + 1, tiles)


def plan_for_skeleton(skeleton_path, options, window=None, extent_km=None, mode='mosaic', land_fraction=None):
    """Tile counts without loading torch or the model; with and without the deep-ocean skip.

    Default region: the skeleton's own extent (or ``window``). ``extent_km`` plans a hypothetical square world of that size
    centred on the skeleton: mode 'mosaic' tiles the skeleton periodically (same coast geometry per km), 'stretch' enlarges
    it (continents and oceans grow). ``land_fraction`` re-thresholds the skeleton so that fraction of it is land.
    """
    stretch = 1.0
    from ..world_relief.td_resident import read_plate
    elevation, manifest = read_plate(skeleton_path)
    config = manifest['config']
    extent_native_km = config['shape'][1] * config['cell_size_m'] / 1000.0
    if extent_km is not None and mode == 'stretch':
        stretch = float(extent_km) / extent_native_km
    sea_level = 0.0
    if land_fraction is not None:
        sea_level = float(np.quantile(elevation, 1.0 - float(land_fraction)))
    source = LandSource(elevation, config, sea_level, stretch)
    if extent_km is not None:
        ranges = window_cond_range((source.center_x, source.center_z), float(extent_km) * 1000.0)
    elif window:
        ranges = window_cond_range(window[:2], window[2])
    else:
        ranges = extent_cond_range(config)
    land_fraction_region = float(source.land(*ranges).mean())
    plain = replace(options, skip_ocean_km=0.0)
    out = dict(
        ranges_ci0_ci1_cj0_cj1=list(ranges), lattice_shape_zx=[ranges[1] - ranges[0], ranges[3] - ranges[2]],
        region_km=[(ranges[3] - ranges[2]) * COND_SPACING_M / 1000.0, (ranges[1] - ranges[0]) * COND_SPACING_M / 1000.0],
        land_fraction=land_fraction_region, sea_level_m=sea_level, hypothetical=extent_km is not None,
        mode=mode if extent_km is not None else 'native', stretch=stretch,
        without_skip=plan_tiles(ranges, plain).summary())
    if options.skip_ocean_km > 0:
        out['with_skip'] = plan_tiles(ranges, options, source).summary()
    return out


# -------------------------------------------------------------------------------------------------------------- model run
def _model_dir(root):
    return terragenesis_root(root) / MODEL_SUBDIR


def model_identity(root=None):
    h = hashlib.sha256()
    p = _model_dir(root) / 'coarse_model' / 'diffusion_pytorch_model.safetensors'
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def load_conditioning(skeleton_path, root=None):
    """(factory, skeleton_manifest, cond_snr). factory(x1, z1, x2, z2) -> torch (5, z, x) normalised-sqrt conditioning."""
    from ..world_relief.td_pages import add_upstream
    from ..world_relief.td_resident import periodic_factory
    add_upstream(terragenesis_root(root))
    from diffusion.physical_config import PhysicalGenerationConfig
    cfg = PhysicalGenerationConfig()
    factory, manifest = periodic_factory(str(skeleton_path), cfg)
    return factory, manifest, [float(v) for v in cfg.cond_snr]


def load_coarse_model(root=None, device=None):
    from ..world_relief.td_pages import add_upstream
    add_upstream(terragenesis_root(root))
    from terrain_diffusion.models.edm_unet import EDMUnet2D
    mdir = _model_dir(root)
    cfg = json.loads((mdir / 'config.json').read_text(encoding='utf-8'))
    model = EDMUnet2D.from_pretrained(str(mdir), subfolder='coarse_model').eval()
    if device is not None:
        model = model.to(device)
    for p in model.parameters():
        p.requires_grad_(False)
    return model, cfg


class _NoiseTiles:
    """TD's tile-seeded noise field with the aligned 64x64 tiles cached.

    A window at stride 48 straddles up to four aligned noise tiles, and neighbouring windows share them; generating each tile
    once (bit-identical to ``gaussian_noise_patch``) removes the repeated work.
    """

    def __init__(self, make_patch, seed, channels, limit=256):
        self._make = make_patch
        self.seed = int(seed)
        self.channels = int(channels)
        self.limit = int(limit)
        self._tiles = {}

    def _tile(self, ty, tx):
        key = (ty, tx)
        tile = self._tiles.get(key)
        if tile is None:
            tile = self._make(self.seed, ty * TILE, tx * TILE, TILE, TILE, channels=self.channels, tile_h=TILE, tile_w=TILE)
            if len(self._tiles) >= self.limit:
                self._tiles.pop(next(iter(self._tiles)))
            self._tiles[key] = tile
        return tile

    def patch(self, y0, x0):
        out = np.empty((self.channels, TILE, TILE), np.float32)
        for ty in range(y0 // TILE, (y0 + TILE - 1) // TILE + 1):
            for tx in range(x0 // TILE, (x0 + TILE - 1) // TILE + 1):
                tile = self._tile(ty, tx)
                ty0, tx0 = ty * TILE, tx * TILE
                oy0, oy1 = max(y0, ty0), min(y0 + TILE, ty0 + TILE)
                ox0, ox1 = max(x0, tx0), min(x0 + TILE, tx0 + TILE)
                out[:, oy0 - y0:oy1 - y0, ox0 - x0:ox1 - x0] = tile[:, oy0 - ty0:oy1 - ty0, ox0 - tx0:ox1 - tx0]
        return out


def run_coarse(factory, model, model_cfg, cond_snr, seed, ci0, ci1, cj0, cj1, device=None, pad=8, progress=None,
               options=None, land_source=None, tile_limit=None):
    """Run the coarse U-Net over tiles covering [ci0-pad, ci1+pad) x [cj0-pad, cj1+pad); return blended (6, ci1-ci0, cj1-cj0).

    Tile logic follows ``WorldPipeline._coarse_inference`` (pool_size 1) without InfiniteTensor/HDF5. Tiles are processed in
    batches of ``options.batch_size`` (sigma schedule is shared, so a batch is bit-identical to running its tiles one by one up to
    BLAS reduction order). Tiles skipped by ``options.skip_ocean_km`` contribute nothing; cells covered only by skipped tiles are
    NaN in the result and False in the returned computed mask (``info['_computed_mask']``).
    """
    import torch
    from terrain_diffusion.inference.world_pipeline import gaussian_noise_patch, linear_weight_window
    from terrain_diffusion.scheduler.dpmsolver import EDMDPMSolverMultistepScheduler
    options = (options or RunOptions(pad=pad)).validate()
    device = device or torch.device(options.device)
    steps = int(options.steps)
    batch = int(options.batch_size)
    cuda = device.type == 'cuda'
    autocast = options.precision == 'autocast'
    ac_dtype = torch.float16 if cuda else torch.bfloat16
    means = torch.tensor(model_cfg['coarse_means'])
    stds = torch.tensor(model_cfg['coarse_stds'])
    cond_means = means[[0, 2, 3, 4, 5]].view(-1, 1, 1)
    cond_stds = stds[[0, 2, 3, 4, 5]].view(-1, 1, 1)
    scheduler = EDMDPMSolverMultistepScheduler(sigma_min=0.002, sigma_max=80, sigma_data=0.5)
    sigma_data = scheduler.config.sigma_data
    window = linear_weight_window(TILE, 'cpu', torch.float32).numpy()
    t_cond = torch.atan(torch.tensor(cond_snr, dtype=torch.float32)).to(device)
    cos_t = torch.cos(t_cond.view(1, -1, 1, 1))
    sin_t = torch.sin(t_cond.view(1, -1, 1, 1))
    cond_inputs = [v.detach().view(-1) for v in torch.log(torch.tan(t_cond) / 8.0)]
    plan = plan_tiles((ci0, ci1, cj0, cj1), options, land_source)
    todo = plan.computed_tiles
    if tile_limit is not None and len(todo) > int(tile_limit):
        pick = np.linspace(0, len(todo) - 1, int(tile_limit)).round().astype(int)
        todo = [todo[k] for k in pick]
    acc = np.zeros((7, plan.height, plan.width), np.float32)
    cond_noise = _NoiseTiles(gaussian_noise_patch, seed, 5)
    start_noise = _NoiseTiles(gaussian_noise_patch, seed + 1, 6)
    phase = dict(conditioning=0.0, noise=0.0, unet=0.0, scheduler=0.0, accumulate=0.0)
    labels_cn = []
    batch_seconds = []

    def sync():
        if cuda:
            torch.cuda.synchronize()

    done = 0
    started = time.perf_counter()
    with torch.inference_mode():
        for first in range(0, len(todo), batch):
            chunk = todo[first:first + batch]
            n = len(chunk)
            tb = time.perf_counter()
            cond = torch.stack([(factory(t.j1, t.i1, t.j1 + TILE, t.i1 + TILE) - cond_means) / cond_stds for t in chunk])
            cond = cond.to(device, dtype=torch.float32)
            t1 = time.perf_counter()
            noise_in = torch.from_numpy(np.stack([cond_noise.patch(t.i1, t.j1) for t in chunk])).to(device, dtype=torch.float32)
            noise_x = torch.from_numpy(np.stack([start_noise.patch(t.i1, t.j1) for t in chunk])).to(device, dtype=torch.float32)
            cond_img = cos_t * cond + sin_t * noise_in
            scheduler.set_timesteps(steps)
            sample = noise_x * scheduler.sigmas[0]
            batch_inputs = [v.expand(n) for v in cond_inputs]
            t2 = time.perf_counter()
            unet = sched = 0.0
            for k, (t, sigma) in enumerate(zip(scheduler.timesteps, scheduler.sigmas)):
                ta = time.perf_counter()
                t, sigma = t.to(device), sigma.to(device)
                scaled = scheduler.precondition_inputs(sample, sigma)
                if k >= len(labels_cn):
                    labels_cn.append(float(scheduler.trigflow_precondition_noise(sigma.view(-1)).item()))
                labels = torch.full((n,), labels_cn[k], device=device, dtype=torch.float32)
                inputs = torch.cat([scaled, cond_img], dim=1)
                sync()
                tb1 = time.perf_counter()
                with torch.autocast(device_type=device.type, dtype=ac_dtype, enabled=autocast):
                    out = model(inputs, noise_labels=labels, conditional_inputs=batch_inputs)
                if autocast:
                    out = out.float()
                sync()
                tb2 = time.perf_counter()
                sample = scheduler.step(out, t, sample).prev_sample
                tb3 = time.perf_counter()
                sched += (tb1 - ta) + (tb3 - tb2)
                unet += tb2 - tb1
            t3 = time.perf_counter()
            sample = sample.cpu().float() / sigma_data
            sample = sample * stds.view(1, -1, 1, 1) + means.view(1, -1, 1, 1)
            sample[:, 1] = sample[:, 0] - sample[:, 1]
            sample = sample.numpy()
            for k, t in enumerate(chunk):
                a, b = t.i1 - plan.r0, t.j1 - plan.c0
                acc[:6, a:a + TILE, b:b + TILE] += sample[k] * window[None]
                acc[6, a:a + TILE, b:b + TILE] += window
            t4 = time.perf_counter()
            phase['conditioning'] += t1 - tb
            phase['noise'] += t2 - t1
            phase['unet'] += unet
            phase['scheduler'] += sched
            phase['accumulate'] += t4 - t3
            batch_seconds.append(t4 - tb)
            done += n
            if progress:
                progress(done, len(todo), time.perf_counter() - started)
    weight = acc[6:7]
    ch = np.divide(acc[:6], weight, out=np.full(acc[:6].shape, np.nan, np.float32), where=weight > 0)
    crop = (slice(ci0 - plan.r0, ci1 - plan.r0), slice(cj0 - plan.c0, cj1 - plan.c0))
    info = dict(plan.summary(), tiles_run=len(todo), batch_size=batch, phase_seconds={k: round(v, 4) for k, v in phase.items()},
                batch_seconds=[round(v, 4) for v in batch_seconds])
    info['_computed_mask'] = (acc[6] > 0)[crop]
    return ch[(slice(None),) + crop].astype(np.float32), info


def elevation_m(sqrt_elev):
    """Coarse channel 0 (sqrt space) -> metres, sign preserved."""
    s = np.asarray(sqrt_elev, np.float32)
    return (np.sign(s) * np.square(s)).astype(np.float32)


def generate(skeleton_path, ranges=None, window=None, root=None, seed=None, progress=None, device=None, min_free=MIN_FREE_BYTES,
             options=None, tile_limit=None):
    """Generate coarse channels for the whole skeleton extent (default), explicit ``ranges`` or ``window=(cx_m, cz_m, size_m)``.

    ``options`` is a RunOptions (stride, steps, deep-ocean skip, precision, batch size, threads, device); the default reproduces the
    frozen product. Returns (result dict, stats dict). stats holds device, wall time, peak memory (never part of identity).
    """
    options = (options or RunOptions()).validate()
    free0 = require_memory(min_free)
    t0 = time.perf_counter()
    import torch
    threads = options.threads or int(os.environ.get('TD_COARSE_THREADS', 8))
    torch.set_num_threads(int(threads))
    # 'cpu' means CPU only (never auto-selects CUDA); 'auto' picks CUDA when usable; anything else is passed to torch as-is
    if device is not None:
        dev, dev_info = torch.device(device), {}
    elif options.device == 'auto':
        dev, dev_info = pick_device()
    else:
        dev, dev_info = torch.device(options.device), dict(cuda_available=bool(torch.cuda.is_available()), torch=torch.__version__,
                                                           selection=f'explicit {options.device}')
    factory, manifest, cond_snr = load_conditioning(skeleton_path, root)
    model, mcfg = load_coarse_model(root, dev)
    load_s = time.perf_counter() - t0
    world_seed = int(manifest['config']['world_seed'])
    seed = coarse_seed(world_seed) if seed is None else int(seed)
    if ranges is None:
        ranges = window_cond_range(window[:2], window[2]) if window else extent_cond_range(manifest['config'])
    ci0, ci1, cj0, cj1 = ranges
    t1 = time.perf_counter()
    land_source = LandSource.from_skeleton(skeleton_path) if options.skip_ocean_km > 0 else None
    ch, tinfo = run_coarse(factory, model, mcfg, cond_snr, seed, ci0, ci1, cj0, cj1, dev, progress=progress, options=options,
                           land_source=land_source, tile_limit=tile_limit)
    run_s = time.perf_counter() - t1
    computed_mask = tinfo.pop('_computed_mask')
    plan_summary = {k: v for k, v in tinfo.items() if k in ('tile', 'stride', 'pad', 'tile_rows', 'tile_cols', 'tiles_total',
                                                              'tiles_computed', 'tiles_skipped', 'skip_ocean_km', 'rule')}
    result = dict(channels=ch, elevation_m=elevation_m(ch[0]), ranges=[ci0, ci1, cj0, cj1], seed=seed, world_seed=world_seed,
                  computed_mask=computed_mask, options=options, plan=plan_summary,
                  skeleton_identity=manifest['identity'], skeleton_config=manifest['config'], cond_snr=cond_snr,
                  first_sample_xz_m=[cj0 * COND_SPACING_M, ci0 * COND_SPACING_M], coarse_means=mcfg['coarse_means'],
                  coarse_stds=mcfg['coarse_stds'])
    computed = max(1, tinfo['tiles_run'])
    stats = dict(device=str(dev), device_info=dev_info, threads=torch.get_num_threads(), model_load_seconds=load_s,
                 generate_seconds=run_s, seconds_per_tile=run_s / computed, peak_working_set_bytes=peak_working_set_bytes(),
                 free_memory_before_bytes=free0, free_memory_after_bytes=available_memory_bytes(),
                 tiles=tinfo['tiles_run'], precision=precision_label(options.precision, dev.type),
                 options=dict(stride=options.stride, steps=options.steps, pad=options.pad, skip_ocean_km=options.skip_ocean_km,
                              precision=options.precision, batch_size=options.batch_size, threads=int(threads), device=str(dev)),
                 **tinfo)
    return result, stats


# ------------------------------------------------------------------------------------------------- mountain trend (pure)
def mountain_mask(elev, threshold_m=1000.0, sigma_cells=1.0, sea_m=0.0):
    """Land cells whose gaussian-smoothed elevation exceeds ``threshold_m`` (coarse model is a low-passed field, so lower than 1500)."""
    e = np.asarray(elev, np.float32)
    return (e > sea_m) & (ndimage.gaussian_filter(e, sigma_cells) > threshold_m)


def ridge_orientation_field(elev, mask, sigma_grad=1.0, sigma_window=3.0):
    """Mask-weighted structure tensor of the smoothed elevation.

    Returns (angle_rad, coherence): angle is the ridge axis in [0, pi) measured from +x (east) toward +z (south), perpendicular to
    the dominant gradient; coherence in [0, 1] (1 = one clean ridge direction, 0 = isotropic). Cells without mask weight in the
    window get coherence 0 and angle 0.
    """
    e = np.asarray(elev, np.float32)
    s = ndimage.gaussian_filter(e, sigma_grad)
    gz, gx = np.gradient(s)
    w = np.asarray(mask, np.float32)
    jxx = ndimage.gaussian_filter(w * gx * gx, sigma_window)
    jzz = ndimage.gaussian_filter(w * gz * gz, sigma_window)
    jxz = ndimage.gaussian_filter(w * gx * gz, sigma_window)
    th = 0.5 * np.arctan2(2 * jxz, jxx - jzz)
    angle = np.mod(th + np.pi / 2, np.pi)
    tr = jxx + jzz
    coh = np.sqrt((jxx - jzz) ** 2 + 4 * jxz ** 2) / np.maximum(tr, 1e-12)
    coh = np.where(tr > 1e-9, coh, 0.0)
    angle = np.where(tr > 1e-9, angle, 0.0)
    return angle.astype(np.float32), np.clip(coh, 0, 1).astype(np.float32)


def axial_diff_deg(a, b):
    d = np.abs(np.asarray(a) - np.asarray(b)) % np.pi
    return np.degrees(np.minimum(d, np.pi - d))


# ------------------------------------------------------------------------------------------------------------------ product
def identity_of(manifest):
    return sha256_json({k: v for k, v in manifest.items() if k != 'identity'})


def build_manifest(result, arrays, extra_parameters, root=None):
    cfg = result['skeleton_config']
    options = result.get('options') or RunOptions()
    plan = result.get('plan') or {}
    m = dict(
        schema=SCHEMA, producer='Terragenesis', algorithm=ALGORITHM,
        source=dict(skeleton_identity=result['skeleton_identity'], world_seed=result['world_seed'], skeleton_config=cfg),
        seed=dict(purpose=PURPOSE, derivation='SHA256(f"{world_seed}:dream-world-gen:td-coarse-ridges")[:8] little endian',
                  td_coarse_seed=result['seed'], note='TD world layer v6 used the raw skeleton seed; this product uses the named sub-seed'),
        model=dict(name='terrain-diffusion-30m/coarse_model', safetensors_sha256=model_identity(root), only_coarse=True,
                   tile=TILE, stride=int(options.stride), steps=int(options.steps), cond_snr=result['cond_snr'],
                   blend='linear weight window, sum(w*x)/sum(w)', precision=precision_label(options.precision, options.device)),
        grid=dict(spacing_m=COND_SPACING_M, first_sample_xz_m=result['first_sample_xz_m'], shape_zx=list(result['elevation_m'].shape),
                  ranges_ci0_ci1_cj0_cj1=result['ranges'], axes='arrays [z,x]; X east; Z south; metres; point samples on the 7680 m conditioning lattice; sea=0',
                  boundary='finite extent of the skeleton; conditioning beyond the edge wraps periodically (scheme C), output is cropped to the extent'),
        parameters=extra_parameters,
        arrays=arrays,
        declared_generated=['TD coarse U-Net elevation (7.68 km low-pass field, 20-step DPM sampling)', 'mountain mask and ridge direction field from that elevation'],
        limitations=['Coarse model only: no latent/base/decoder; elevation is a low-frequency field, absolute heights are lower than 30 m detail',
                     'Not a Terragenesis certified product; ridge field is a trend guide, not terrain',
                     'Not interpolated detail: resampling to finer grids adds no information'],
    )
    if float(options.skip_ocean_km) > 0:
        m['deep_ocean_skip'] = dict(
            rule=plan.get('rule'), skip_ocean_km=float(options.skip_ocean_km), tiles_total=plan.get('tiles_total'),
            tiles_computed=plan.get('tiles_computed'), tiles_skipped=plan.get('tiles_skipped'),
            uncomputed_cells='NaN in elevation_m and coarse_channels; computed_mask.npy is 0 there; mountain_mask=0, ridge_coherence=0 and '
                            'ridge_angle_rad=0 are placeholders, not results')
    m['identity'] = identity_of(m)
    return m


def write_product(out_dir, result, mask_threshold_m=1000.0, sigma_cells=1.0, sigma_grad=1.0, sigma_window=3.0, root=None, stats=None):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    el = result['elevation_m']
    computed = result.get('computed_mask')
    partial = computed is not None and not bool(np.all(computed))
    el_work = np.where(computed, el, 0.0).astype(np.float32) if partial else el
    mask = mountain_mask(el_work, mask_threshold_m, sigma_cells)
    ang, coh = ridge_orientation_field(el_work, mask, sigma_grad, sigma_window)
    if partial:
        mask = mask & computed
        ang = np.where(computed, ang, 0.0).astype(np.float32)
        coh = np.where(computed, coh, 0.0).astype(np.float32)
    data = {'elevation_m': el, 'mountain_mask': mask.astype(np.uint8), 'ridge_angle_rad': ang, 'ridge_coherence': coh,
            'coarse_channels': result['channels']}
    if partial:
        data['computed_mask'] = computed.astype(np.uint8)
    arrays = {}
    for name, a in data.items():
        np.save(out / f'{name}.npy', a)
        arrays[name] = dict(dtype=str(a.dtype), shape=list(a.shape), sha256=hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest())
    params = dict(mountain_threshold_m=mask_threshold_m, mountain_smooth_sigma_cells=sigma_cells, ridge_sigma_grad_cells=sigma_grad,
                  ridge_sigma_window_cells=sigma_window,
                  ridge_angle_definition='axis in [0,pi) from +x (east) toward +z (south), perpendicular to the gradient')
    m = build_manifest(result, arrays, params, root)
    (out / 'manifest.json').write_text(json.dumps(m, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    if stats is not None:
        (out / 'runtime-stats.json').write_text(json.dumps(stats, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
    return m
