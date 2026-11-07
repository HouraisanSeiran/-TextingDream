"""Fast procedural world layer (2 km grid, CPU only) from a tectonic skeleton: ``terragenesis-fast-relief-v1``.

Replaces the Terrain Diffusion world layer (user decision 2026-11-05, docs/terrain-generation-rules.md section 6). TD is only
used for the local 30 m layer. Same skeleton conditions both; mountain *trends* must match, details may differ.

Pipeline (all steps are declared in the manifest):
1. skeleton (10-20 km cells, periodic) -> bicubic upsample to the 2 km grid (elevation proxy, crust thickness, ocean_connected);
2. coast refinement: skeleton elevation + coordinate-addressed fractal noise decides sea/land; tiny ocean specks removed;
3. broad relief: ``base + gain_u * max(skeleton - 850 m, 0) + gain_t * crust-thickness excess`` (the mountain belts follow the
   skeleton convergence/uplift zones; main ridges are the skeleton ridge lines, side ridges come from domain-warped ridged
   noise scaled by the belt weight); coastal ramp and low-amplitude lowland undulation;
4. optional light coarse erosion: implicit stream-power incision on the irregular drainage graph + gentle hillslope diffusion;
5. irregular-graph hydrology (Terragenesis ``grid_mesh`` / ``route_graph`` / ``accumulate_graph``, no D8): breach-then-lake,
   rivers by area threshold, lake polygons.
Everything is addressed by absolute world coordinates and stable sub-seeds (no stateful RNG, no time/entropy).
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as nd

from .config import derive_subseed
from . import graph_hydro as gh

SCHEMA = 'terragenesis-fast-relief-v1'
ALGORITHM = 'dream-fast-relief-1'
SPACING_M = 2000.0
MIN_FREE_BYTES = 2 * 2 ** 30
SKELETON_KEYS = ('elevation_m', 'crust_thickness_m', 'continental_fraction', 'ocean_connected', 'plate_id')
SUBSEED_PURPOSES = ('fast-relief/coast', 'fast-relief/ridge', 'fast-relief/warp', 'fast-relief/lowland', 'fast-relief/mesh')
TG_FILES = gh.TG_FILES
# v2 (relief='ridges'): mountains from the skeleton v3 vector ridge network; same product layout/schema, new algorithm id
ALGORITHM_V2 = 'dream-fast-relief-2'
SUBSEED_PURPOSES_V2 = SUBSEED_PURPOSES + ('fast-relief-2/gullies',)
TG_FILES_V2 = TG_FILES + ('terrain_pipeline/procedural_mountain_erosion.py',)

DEFAULTS = dict(
    spacing_m=SPACING_M,
    coast_noise_amp_m=250.0, coast_wavelengths_km=(90.0, 36.0, 14.0), coast_weights=(0.55, 0.3, 0.15),
    base_m=800.0, uplift_threshold_m=850.0, gain_u=0.24, gain_t=118.0, thickness_ref_m=35000.0, thickness_min_km=-5.0,
    belt_lo_m=1000.0, belt_span_m=900.0,
    ridge_amp=0.30, ridge_wavelengths_km=(46.0, 19.0), ridge_weights=(0.65, 0.35), ridge_centre=0.55,
    warp_wavelength_km=70.0, warp_amp_km=14.0,
    coast_ramp_km=120.0, lowland_amp_m=60.0, lowland_wavelengths_km=(70.0, 28.0),
    land_min_m=2.0, ocean_max_m=-5.0, ocean_speck_nodes=30,
    erosion_iterations=3, erosion_k=1.5e-3, erosion_area_exp=0.5, erosion_max_f=3.0, diffusion=0.4, diffusion_sigma=0.8,
    river_lo_km2=400.0, river_hi_km2=1200.0, slope_split=0.008, depth_min_m=60.0, lake_area_min_km2=300.0, breach_passes=4,
    smooth_rivers=True,
)
# v2: no Gaussian anywhere in the land relief; erosion has more rounds, no incision cap, talus (thermal) relaxation instead of
# the v1 Gaussian hillslope diffusion; directional gully appearance filter (Terragenesis) on the mountain flanks
DEFAULTS_V2 = dict(
    DEFAULTS, coast_ramp_km=30.0, lowland_amp_m=45.0,
    erosion_iterations=14, erosion_k=4.0e-3, erosion_max_f=None, diffusion=0.0, hillslope='talus',
    talus_slope=0.45, talus_rate=0.25, talus_passes=2,
    gully_scale=12.0, gully_gain=7.0, gully_strength=1.0, gully_env_min=0.02,
)
# v3 (relief='orogen', dream-fast-relief-3): mountains from the skeleton v4 orogen belts (ridge_network.rasterize_orogen);
# stronger stream-power incision so valleys cut into the belts; lakes are not allowed on the ridge envelope and need a
# catchment; river lines are cut at the lake shore (no through-lake chord)
ALGORITHM_V3 = 'dream-fast-relief-3'
SUBSEED_PURPOSES_V3 = SUBSEED_PURPOSES_V2
DEFAULTS_V3 = dict(
    DEFAULTS_V2, erosion_iterations=20, erosion_k=1.6e-2, talus_slope=0.5,
    lake_forbid_env=0.10, lake_min_catch_km2=3000.0, lake_area_min_km2=300.0,
)


# ------------------------------------------------------------------ small utilities
def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def identity_of(manifest):
    return hashlib.sha256(canonical({k: v for k, v in manifest.items() if k != 'identity'}).encode()).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False), encoding='utf-8')


def memory_guard(min_free_bytes=MIN_FREE_BYTES):
    from .sysmem import available_memory_bytes
    avail = available_memory_bytes()
    if avail < min_free_bytes:
        raise MemoryError('only %.2f GiB available, need >= %.2f GiB; nothing was started' % (avail / 2 ** 30, min_free_bytes / 2 ** 30))
    return avail


def peak_memory_mb():
    try:
        import psutil
        mi = psutil.Process().memory_info()
        return float(getattr(mi, 'peak_wset', mi.rss)) / 2 ** 20
    except ImportError:
        return float('nan')


def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


# ------------------------------------------------------------------ coordinate-addressed noise
def _lattice(a, b, seed):
    with np.errstate(over='ignore'):
        q = a.astype(np.uint64) * np.uint64(0x9e3779b185ebca87) ^ b.astype(np.uint64) * np.uint64(0xc2b2ae3d27d4eb4f) ^ np.uint64(seed)
        q = (q ^ (q >> np.uint64(30))) * np.uint64(0xbf58476d1ce4e5b9)
        q = (q ^ (q >> np.uint64(27))) * np.uint64(0x94d049bb133111eb)
        q ^= q >> np.uint64(31)
    return (q >> np.uint64(11)).astype(np.float64) / 2 ** 53 * 2 - 1


def noise_xz(x_m, z_m, seed, wavelength_m):
    """Smooth value noise in [-1, 1] at absolute metric coordinates (arrays broadcast to a common shape)."""
    xx = np.asarray(x_m, np.float64) / wavelength_m
    zz = np.asarray(z_m, np.float64) / wavelength_m
    ix, iz = np.floor(xx).astype(np.int64), np.floor(zz).astype(np.int64)
    fx, fz = xx - ix, zz - iz
    fx, fz = fx * fx * (3 - 2 * fx), fz * fz * (3 - 2 * fz)
    return ((1 - fz) * ((1 - fx) * _lattice(ix, iz, seed) + fx * _lattice(ix + 1, iz, seed))
            + fz * ((1 - fx) * _lattice(ix, iz + 1, seed) + fx * _lattice(ix + 1, iz + 1, seed)))


def fbm_xz(x_m, z_m, seed, wavelengths_m, weights, ridged=False):
    total = 0.0
    for k, (wl, w) in enumerate(zip(wavelengths_m, weights)):
        n = noise_xz(x_m, z_m, (seed + 0x9E3779B97F4A7C15 * (k + 1)) % (1 << 64), wl)
        total = total + w * ((1.0 - np.abs(n)) if ridged else n)
    return total


def blocked_grid(shape, first, spacing, fn, rows=256, dtype=np.float32):
    """Evaluate ``fn(x[1,nx], z[nrows,1])`` over the grid in row blocks (bounds temporaries on large worlds)."""
    out = np.empty(shape, dtype)
    x = (first[0] + np.arange(shape[1]) * spacing)[None, :]
    for r0 in range(0, shape[0], rows):
        z = (first[1] + np.arange(r0, min(r0 + rows, shape[0])) * spacing)[:, None]
        out[r0:r0 + z.shape[0]] = fn(x, z)
    return out


# ------------------------------------------------------------------ skeleton
def load_skeleton(path, expected_identity=None, strict=True):
    """Read the skeleton npz. Identity and per-array hashes are verified when the manifest allows; the result says what was."""
    with np.load(path, allow_pickle=False) as z:
        raw = z['manifest_json']
        if raw.shape != () or raw.dtype.kind != 'U':
            raise ValueError('Invalid manifest_json')
        m = json.loads(raw.item())
        fields = {k: np.asarray(z['final/' + k]) for k in SKELETON_KEYS if 'final/' + k in z.files}
    computed = identity_of(m)
    identity_ok = computed == m.get('identity')
    if expected_identity is not None and m.get('identity') != expected_identity:
        raise ValueError('skeleton identity differs from the expected one')
    if strict and not identity_ok and expected_identity is not None:
        raise ValueError('skeleton manifest identity does not recompute')
    arrays_ok = True
    for k, a in fields.items():
        spec = (m.get('arrays') or {}).get('final/' + k)
        if isinstance(spec, dict) and 'sha256' in spec:
            if hashlib.sha256(np.ascontiguousarray(a).tobytes(order='C')).hexdigest() != spec['sha256']:
                arrays_ok = False
        else:
            arrays_ok = False
    cfg = m['config']
    for need in ('elevation_m', 'crust_thickness_m'):
        if need not in fields:
            raise ValueError('skeleton lacks final/' + need)
    ridges = ridge_meta = None
    if m.get('ridge_network'):                       # dream-world-skeleton-3: vector ridge network (hash-checked)
        from . import ridge_network as rn
        ridges, _ = rn.load_network(path)
        ridge_meta = m['ridge_network']
    return dict(fields=fields, identity=str(m['identity']), identity_recomputes=bool(identity_ok), arrays_verified=bool(arrays_ok),
                cell_m=float(cfg['cell_size_m']), origin_xz_m=(float(cfg['origin_x_m']), float(cfg['origin_z_m'])),
                world_seed=int(cfg['world_seed']), shape=tuple(fields['elevation_m'].shape), path=str(path),
                algorithm=m.get('algorithm'), ridges=ridges, ridge_meta=ridge_meta)


def grid_of(sk, spacing=SPACING_M):
    nz, nx = sk['shape']
    cell = sk['cell_m']
    shape = (int(round(nz * cell / spacing)), int(round(nx * cell / spacing)))
    if abs(shape[0] * spacing - nz * cell) > 1e-6 or abs(shape[1] * spacing - nx * cell) > 1e-6:
        raise ValueError('skeleton extent is not a whole number of grid cells')
    first = (sk['origin_xz_m'][0] + spacing / 2, sk['origin_xz_m'][1] + spacing / 2)
    return shape, first


def upsample(a, shape, spacing, cell, order=3, rows=128):
    """Cell-centre aligned spline resample of a periodic skeleton field onto the target grid (wrap padding)."""
    pad = 4
    p = np.pad(np.asarray(a, np.float64), pad, mode='wrap')
    if order > 1:
        p = nd.spline_filter(p, order=order)
    xs = (np.arange(shape[1]) + .5) * spacing / cell - .5 + pad
    out = np.empty(shape, np.float32)
    for r0 in range(0, shape[0], rows):
        zs = (np.arange(r0, min(r0 + rows, shape[0])) + .5) * spacing / cell - .5 + pad
        zz, xx = np.meshgrid(zs, xs, indexing='ij')
        out[r0:r0 + zs.size] = nd.map_coordinates(p, [zz, xx], order=order, mode='nearest', prefilter=False)
    return out


# ------------------------------------------------------------------ terrain
def subseeds_for(world_seed, purposes=SUBSEED_PURPOSES):
    return {name: derive_subseed(world_seed, name) for name in purposes}


def upsample_limited(a, shape, spacing, cell, rows=128):
    """Bicubic upsample clamped to the min/max of the 2x2 skeleton cells around each sample (no spline over/undershoot).

    The plain bicubic spline rings next to sharp skeleton steps (flat plain cell next to a mountain cell): it digs a narrow
    trough of ~100 m parallel to the mountain front, which the v1 hydrology kept as a long thin lake."""
    out = upsample(a, shape, spacing, cell, 3, rows)
    pad = 4
    p = np.pad(np.asarray(a, np.float64), pad, mode='wrap')
    xs = (np.arange(shape[1]) + .5) * spacing / cell - .5 + pad
    zs = (np.arange(shape[0]) + .5) * spacing / cell - .5 + pad
    ix = np.floor(xs).astype(np.int64); iz = np.floor(zs).astype(np.int64)
    c = [p[np.ix_(iz + a0, ix + b0)] for a0 in (0, 1) for b0 in (0, 1)]
    lo = np.minimum(np.minimum(c[0], c[1]), np.minimum(c[2], c[3]))
    hi = np.maximum(np.maximum(c[0], c[1]), np.maximum(c[2], c[3]))
    return np.clip(out, lo, hi).astype(np.float32)


def _coast(su, oc_up, shape, first, S, p, seeds):
    wl = [v * 1000.0 for v in p['coast_wavelengths_km']]
    coast = blocked_grid(shape, first, S, lambda x, z: p['coast_noise_amp_m'] * fbm_xz(x, z, seeds['fast-relief/coast'], wl, p['coast_weights']))
    land = (su + coast) > 0
    land |= (su <= 0) & ~oc_up
    lab, n = nd.label(~land)
    if n:
        sizes = np.bincount(lab.ravel())
        rim = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
        small = sizes < int(p['ocean_speck_nodes']); small[0] = False
        small[rim] = False
        land |= small[lab]
    del lab
    lab, n = nd.label(land)
    if n:
        sizes = np.bincount(lab.ravel())
        land &= ~(sizes < 3)[lab]
    return land


def gully_detail(h, env, R, shape, first, S, p, seed):
    """Terragenesis directional-gullies-v1 on the mountain cells, evaluated in coordinates compressed by gully_scale (its fixed
    1.2/0.6/0.3 km octaves become 14/7/3.6 km at the default scale, above the 4 km Nyquist length of the 2 km grid)."""
    root = str(gh.terragenesis_root())             # path only: importing irregular_drainage would need numba
    if root not in sys.path:
        sys.path.append(root)
    from terrain_pipeline import procedural_mountain_erosion as pme
    k = float(p['gully_scale'])
    gz, gx = np.gradient(np.asarray(h, np.float64), S)
    mask = env > float(p['gully_env_min'])
    idx = np.flatnonzero(mask.ravel())
    out = np.zeros(h.size, np.float64)
    if idx.size == 0:
        return out.reshape(shape).astype(np.float32), 0
    zi, xi = np.divmod(idx, shape[1])
    x = first[0] + xi * S; z = first[1] + zi * S
    target = np.clip(2.0 * R.ravel()[idx] - 1.0, -1.0, 1.0)
    fade = smoothstep(env.ravel()[idx] / 0.15)
    step = pme.MAX_SAMPLES
    for a in range(0, idx.size, step):
        b = min(a + step, idx.size)
        d = pme.directional_detail(x[a:b] / k, z[a:b] / k, h.ravel()[idx[a:b]], gx.ravel()[idx[a:b]] * k, gz.ravel()[idx[a:b]] * k,
                                   target[a:b], world_seed=int(seed), strength=float(p['gully_strength']))
        out[idx[a:b]] = d * float(p['gully_gain']) * fade[a:b]
    return out.reshape(shape).astype(np.float32), int(idx.size)


def build_terrain_v2(sk, params=None, log=None):
    """dream-fast-relief-2 terrain: lowland base + ridge-network relief (same raster the v3 skeleton was derived from) +
    directional gullies. No Gaussian profile, no Gaussian blur. Needs a dream-world-skeleton-3 skeleton (sk['ridges'])."""
    from . import ridge_network as rn
    if not sk.get('ridges'):
        raise ValueError('skeleton has no ridge network (needs dream-world-skeleton-3, --ridges fractal)')
    p = dict(DEFAULTS_V2); p.update(params or {})
    S = float(p['spacing_m'])
    shape, first = grid_of(sk, S)
    seeds = subseeds_for(sk['world_seed'], SUBSEED_PURPOSES_V2)
    cell = sk['cell_m']
    rmeta = sk['ridge_meta']
    t0 = time.perf_counter()
    su = upsample_limited(sk['fields']['elevation_m'], shape, S, cell)
    th = upsample(sk['fields']['crust_thickness_m'], shape, S, cell, 1)
    if 'ocean_connected' in sk['fields']:
        oc_up = upsample(sk['fields']['ocean_connected'].astype(np.float32), shape, S, cell, 1) > 0.5
    else:
        oc_up = su <= 0
    land_sk = np.asarray(sk['fields']['elevation_m']) > 0
    base_sk = rn.lowland_base(land_sk, cell, sk['world_seed'])
    base = upsample_limited(base_sk, shape, S, cell)
    t_up = time.perf_counter() - t0
    t0 = time.perf_counter()
    land = _coast(su, oc_up, shape, first, S, p, seeds)
    ocean = ~land
    t_coast = time.perf_counter() - t0
    t0 = time.perf_counter()
    relief, parts = rn.rasterize(sk['ridges'], shape, first, S, world_seed=sk['world_seed'], params=rmeta.get('params'),
                                 width_scale=float(rmeta['width_scale']), return_parts=True)
    env, R = parts['envelope'], parts['ridged']
    t_raster = time.perf_counter() - t0
    t0 = time.perf_counter()
    lmin = float(p['land_min_m'])
    dist_m = nd.distance_transform_edt(land).astype(np.float32) * S
    ramp = smoothstep(dist_m / (float(p['coast_ramp_km']) * 1000.0))
    lwl = [v * 1000.0 for v in p['lowland_wavelengths_km']]
    low = blocked_grid(shape, first, S, lambda x, z: fbm_xz(x, z, seeds['fast-relief/lowland'], lwl, (0.65, 0.35)))
    belt = smoothstep(env / 0.3).astype(np.float32)
    h = lmin + (base - lmin) * ramp + float(p['lowland_amp_m']) * ramp * (1.0 - belt) * low + float(rmeta['amp_m']) * relief
    del low
    gul, gul_n = gully_detail(h, env, R, shape, first, S, p, seeds['fast-relief-2/gullies'])
    h = h + gul
    land_h = np.maximum(h, lmin)
    ocean_h = np.minimum(su, float(p['ocean_max_m']))
    elevation = np.where(land, land_h, ocean_h).astype(np.float32)
    t_relief = time.perf_counter() - t0
    timing = dict(upsample_s=t_up, coast_s=t_coast, raster_s=t_raster, relief_s=t_relief)
    if log:
        log(dict(stage='terrain-v2', **timing, gully_nodes=gul_n))
    return dict(elevation=elevation, ocean=ocean, belt=belt, envelope=env, skeleton_up=su, thickness_up=th, shape=shape, first=first,
                seeds=seeds, params=p, gully_nodes=gul_n, gully_abs_max_m=float(np.abs(gul).max()), timing=timing)


def build_terrain_v3(sk, params=None, log=None):
    """dream-fast-relief-3 terrain: lowland base + orogen relief of the skeleton v4 belts (belt platform, foothills, parallel
    ranges, branches; same raster the skeleton elevation was box-averaged from) + directional gullies. No Gaussian."""
    from . import ridge_network as rn
    rmeta = sk.get('ridge_meta') or {}
    if not sk.get('ridges') or 'belt_offsets' not in sk['ridges']:
        raise ValueError('skeleton has no orogen belts (needs dream-world-skeleton-4, --ridges orogen)')
    p = dict(DEFAULTS_V3); p.update(params or {})
    S = float(p['spacing_m'])
    shape, first = grid_of(sk, S)
    seeds = subseeds_for(sk['world_seed'], SUBSEED_PURPOSES_V3)
    cell = sk['cell_m']
    t0 = time.perf_counter()
    su = upsample_limited(sk['fields']['elevation_m'], shape, S, cell)
    th = upsample(sk['fields']['crust_thickness_m'], shape, S, cell, 1)
    if 'ocean_connected' in sk['fields']:
        oc_up = upsample(sk['fields']['ocean_connected'].astype(np.float32), shape, S, cell, 1) > 0.5
    else:
        oc_up = su <= 0
    land_sk = np.asarray(sk['fields']['elevation_m']) > 0
    base = upsample_limited(rn.lowland_base(land_sk, cell, sk['world_seed']), shape, S, cell)
    t_up = time.perf_counter() - t0
    t0 = time.perf_counter()
    land = _coast(su, oc_up, shape, first, S, p, seeds)
    ocean = ~land
    t_coast = time.perf_counter() - t0
    t0 = time.perf_counter()
    parts = rn.rasterize_orogen(sk['ridges'], shape, first, S, world_seed=sk['world_seed'], params=rmeta.get('params'))
    env, R, q = parts['envelope'], parts['ridged'], parts['footprint']
    t_raster = time.perf_counter() - t0
    t0 = time.perf_counter()
    lmin = float(p['land_min_m'])
    dist_m = nd.distance_transform_edt(land).astype(np.float32) * S
    ramp = smoothstep(dist_m / (float(p['coast_ramp_km']) * 1000.0))
    lwl = [v * 1000.0 for v in p['lowland_wavelengths_km']]
    low = blocked_grid(shape, first, S, lambda x, z: fbm_xz(x, z, seeds['fast-relief/lowland'], lwl, (0.65, 0.35)))
    belt = smoothstep(q / 0.15).astype(np.float32)
    h = lmin + (base - lmin) * ramp + float(p['lowland_amp_m']) * ramp * (1.0 - belt) * low + parts['relief_m']
    del low
    gul, gul_n = gully_detail(h, env, R, shape, first, S, p, seeds['fast-relief-2/gullies'])
    h = h + gul
    land_h = np.maximum(h, lmin)
    ocean_h = np.minimum(su, float(p['ocean_max_m']))
    elevation = np.where(land, land_h, ocean_h).astype(np.float32)
    t_relief = time.perf_counter() - t0
    timing = dict(upsample_s=t_up, coast_s=t_coast, raster_s=t_raster, relief_s=t_relief)
    if log:
        log(dict(stage='terrain-v3', **timing, gully_nodes=gul_n))
    fp_min = float((rmeta.get('params') or {}).get('footprint_min', 0.02))
    return dict(elevation=elevation, ocean=ocean, belt=belt, envelope=env, footprint=q, mountain_area=(q > fp_min) & land,
                belt_id=parts['belt_id'], level=parts['level'], lake_forbid=(env > float(p['lake_forbid_env'])) & land,
                skeleton_up=su, thickness_up=th, shape=shape, first=first, seeds=seeds, params=p, gully_nodes=gul_n,
                gully_abs_max_m=float(np.abs(gul).max()), timing=timing)


def build_terrain(sk, params=None, log=None):
    """Steps 1-3. Returns dict(elevation, ocean, belt, skeleton_up, thickness_up, shape, first). Needs numpy/scipy only."""
    p = dict(DEFAULTS); p.update(params or {})
    S = float(p['spacing_m'])
    shape, first = grid_of(sk, S)
    seeds = subseeds_for(sk['world_seed'])
    cell = sk['cell_m']
    t0 = time.perf_counter()
    su = upsample(sk['fields']['elevation_m'], shape, S, cell, 3)
    th = upsample(sk['fields']['crust_thickness_m'], shape, S, cell, 3)
    if 'ocean_connected' in sk['fields']:
        oc_up = upsample(sk['fields']['ocean_connected'].astype(np.float32), shape, S, cell, 1) > 0.5
    else:
        oc_up = su <= 0
    t_up = time.perf_counter() - t0
    # ---- coast refinement
    t0 = time.perf_counter()
    wl = [v * 1000.0 for v in p['coast_wavelengths_km']]
    coast = blocked_grid(shape, first, S, lambda x, z: p['coast_noise_amp_m'] * fbm_xz(x, z, seeds['fast-relief/coast'], wl, p['coast_weights']))
    land = (su + coast) > 0
    land |= (su <= 0) & ~oc_up                       # skeleton inland basins stay land (hydrology decides lakes)
    # ocean specks (not touching the domain rim) become land; one-node land specks vanish
    lab, n = nd.label(~land)
    if n:
        sizes = np.bincount(lab.ravel())
        rim = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
        small = sizes < int(p['ocean_speck_nodes']); small[0] = False
        small[rim] = False
        land |= small[lab]
    del lab
    lab, n = nd.label(land)
    if n:
        sizes = np.bincount(lab.ravel())
        land &= ~(sizes < 3)[lab]
    del lab
    ocean = ~land
    t_coast = time.perf_counter() - t0
    # ---- broad relief
    t0 = time.perf_counter()
    u = np.maximum(su - float(p['uplift_threshold_m']), 0.0)
    dt_km = np.maximum((th - float(p['thickness_ref_m'])) / 1000.0, float(p['thickness_min_km']))
    broad = float(p['base_m']) + float(p['gain_u']) * u + float(p['gain_t']) * dt_km
    belt = smoothstep((broad - float(p['belt_lo_m'])) / float(p['belt_span_m'])).astype(np.float32)
    del u, dt_km
    warp_wl = float(p['warp_wavelength_km']) * 1000.0; warp_amp = float(p['warp_amp_km']) * 1000.0
    rwl = [v * 1000.0 for v in p['ridge_wavelengths_km']]

    def ridge_fn(x, z):
        wx = warp_amp * noise_xz(x, z, seeds['fast-relief/warp'], warp_wl)
        wz = warp_amp * noise_xz(x + 31337.0, z - 7919.0, seeds['fast-relief/warp'], warp_wl)
        return fbm_xz(x + wx, z + wz, seeds['fast-relief/ridge'], rwl, p['ridge_weights'], ridged=True)
    ridge = blocked_grid(shape, first, S, ridge_fn)
    detail = float(p['ridge_amp']) * (broad - float(p['base_m'])) * belt * (ridge - float(p['ridge_centre'])) * 2.0
    del ridge
    lwl = [v * 1000.0 for v in p['lowland_wavelengths_km']]
    low = blocked_grid(shape, first, S, lambda x, z: fbm_xz(x, z, seeds['fast-relief/lowland'], lwl, (0.65, 0.35)))
    dist_m = nd.distance_transform_edt(land).astype(np.float32) * S
    ramp = smoothstep(dist_m / (float(p['coast_ramp_km']) * 1000.0))
    s = np.maximum(ramp, belt)
    lmin = float(p['land_min_m'])
    land_h = lmin + (broad + detail - lmin) * s + float(p['lowland_amp_m']) * (1.0 - belt) * ramp * low
    del detail, low, broad
    land_h = np.maximum(land_h, lmin)
    ocean_h = np.minimum(su, float(p['ocean_max_m']))
    elevation = np.where(land, land_h, ocean_h).astype(np.float32)
    t_relief = time.perf_counter() - t0
    if log:
        log(dict(stage='terrain', upsample_s=t_up, coast_s=t_coast, relief_s=t_relief))
    return dict(elevation=elevation, ocean=ocean, belt=belt, skeleton_up=su, thickness_up=th, shape=shape, first=first,
                seeds=seeds, params=p, timing=dict(upsample_s=t_up, coast_s=t_coast, relief_s=t_relief))


# ------------------------------------------------------------------ coarse erosion on the irregular graph
def erode(elevation, ocean, mesh, outlets, p, log=None):
    """Implicit stream-power incision (n=1) along the graph receivers + gentle hillslope diffusion. Land stays >= land_min_m."""
    h = np.asarray(elevation, np.float64).copy()
    oc = np.asarray(ocean, bool)
    ocl = oc.ravel().tolist()
    px = np.asarray(mesh.node_x_m); pz = np.asarray(mesh.node_z_m)
    lmin = float(p['land_min_m']); incised = []
    for it in range(int(p['erosion_iterations'])):
        _, rec, order, area = gh.route_area(h, outlets, mesh)
        valid = rec >= 0
        safe = np.where(valid, rec, 0)
        length = np.maximum(np.hypot(px - px[safe], pz - pz[safe]), 1.0)
        f = np.where(valid, float(p['erosion_k']) * area ** float(p['erosion_area_exp']) / length, 0.0)
        if p.get('erosion_max_f') is not None:          # v2: None = no incision cap
            f = np.minimum(f, float(p['erosion_max_f']))
        hl = h.ravel().tolist(); fl = f.tolist(); rl = rec.tolist()
        before = h.ravel().copy()
        for i in order.tolist():                       # receivers before donors
            r = rl[i]
            if r < 0 or ocl[i]:
                continue
            hr = hl[r]
            if hl[i] > hr:
                hl[i] = (hl[i] + fl[i] * hr) / (1.0 + fl[i])
        h = np.asarray(hl, np.float64).reshape(h.shape)
        d = float(p['diffusion'])
        if d > 0:
            sm = nd.gaussian_filter(h, float(p['diffusion_sigma']))
            h = np.where(oc, h, h + d * (sm - h))
        if p.get('hillslope') == 'talus':
            for _ in range(int(p['talus_passes'])):
                h = talus_relax(h, oc, float(p['talus_slope']) * float(mesh.spacing_m), float(p['talus_rate']))
        h = np.where(oc, h, np.maximum(h, lmin))
        incised.append(float((before - h.ravel())[~oc.ravel()].mean()))
        if log:
            log(dict(stage='erosion', iteration=it, mean_lowering_m=incised[-1]))
    return h.astype(np.float32), incised


def talus_relax(h, ocean, max_drop_m, rate):
    """Thermal (talus) relaxation: only height steps above max_drop_m between 4-neighbours are reduced, by `rate` of the
    excess (mass-conserving exchange between the two land cells). Slopes below the threshold, valley floors and ridge
    crests that are not over-steep stay untouched (no smoothing kernel). Ocean cells neither give nor take."""
    h = np.asarray(h, np.float64)
    land = ~np.asarray(ocean, bool)
    delta = np.zeros_like(h)
    for axis in (0, 1):
        a = [slice(None)] * 2; b = [slice(None)] * 2
        a[axis] = slice(0, -1); b[axis] = slice(1, None)
        a, b = tuple(a), tuple(b)
        diff = h[a] - h[b]
        both = land[a] & land[b]
        ex = np.where(both, np.sign(diff) * np.maximum(np.abs(diff) - max_drop_m, 0.0), 0.0) * (rate * 0.25)
        delta[a] -= ex
        delta[b] += ex
    return h + delta


# ------------------------------------------------------------------ whole computation
RELIEF_MODES = ('skeleton', 'ridges', 'orogen')


def compute(sk, params=None, erosion=True, log=None, relief='skeleton', *, island_product_path=None,
            expected_island_identity=None, skeleton_run_path=None, mountain_input_path=None, process_config=None, process_out=None):
    """Terrain + irregular-graph hydrology for one skeleton. Needs numba (Terragenesis venv).

    relief='skeleton': dream-fast-relief-1 (v1, unchanged). relief='ridges': dream-fast-relief-2 from the v3 ridge network."""
    if relief not in RELIEF_MODES:
        raise ValueError('unknown relief mode %r' % (relief,))
    binding = None
    if island_product_path is not None:
        from . import ocean_island_adapter as islands
        binding = islands.load_binding(sk['path'],island_product_path,expected_island_identity,skeleton_run_path)
        if binding.product.source.identity != sk['identity']:
            raise ValueError('island product differs from the loaded skeleton')
    elif expected_island_identity is not None or skeleton_run_path is not None:
        raise ValueError('island identity/run binding requires island_product_path')
    T = (build_terrain_v3(sk, params, log) if relief == 'orogen' else build_terrain_v2(sk, params, log) if relief == 'ridges'
         else build_terrain(sk, params, log))
    v3 = relief == 'orogen'
    p = T['params']; S = float(p['spacing_m']); shape = T['shape']; first = T['first']
    ocean = T['ocean']
    mountain_data = None
    if mountain_input_path is not None and binding is None:
        raise ValueError('mountain input requires the frozen island binding')
    before_islands = T['elevation'].copy() if binding is not None else None
    island_fields = fractions = None
    if binding is not None:
        island_fields, fractions = islands.compose_world(binding,T['elevation'],first,S)
        if mountain_input_path is not None:
            from .web_island_stage import apply_to_fields
            island_fields, mountain_data = apply_to_fields(mountain_input_path,binding,island_fields,first,S)
        T['elevation'], ocean, lagoon = islands.restore_after_erosion(island_fields,island_fields['elevation_m'])
        T['ocean'] = ocean
    t0 = time.perf_counter()
    mesh_seed = T['seeds']['fast-relief/mesh']
    mesh = gh.build_graph(shape, first, S, mesh_seed)
    t_mesh = time.perf_counter() - t0
    outlets = ocean.copy()
    if binding is not None:
        outlets |= lagoon  # registered saltwater lagoon is a local sink, not external ocean
    outlets[0] = True; outlets[-1] = True; outlets[:, 0] = True; outlets[:, -1] = True
    t0 = time.perf_counter()
    elevation, incised = (T['elevation'], [])
    process = None
    if process_config is not None:
        from . import world_process_adapter
        process = world_process_adapter.compute(sk, elevation, ocean, mesh, outlets, first, S,
                    lagoon=lagoon if binding is not None else None, config=process_config, out_dir=process_out)
        elevation = np.asarray(process['arrays']['elevation_m'], np.float64)
    elif erosion and int(p['erosion_iterations']) > 0:
        # The erosion land clamp must preserve every initial negative bed,
        # including closed basins. This is not the hydrology external-ocean mask.
        erosion_fixed_water = ocean if binding is None else ocean | (elevation < 0)
        elevation, incised = erode(elevation, erosion_fixed_water, mesh, outlets, p, log)
    if binding is not None and process is None:
        elevation, ocean, lagoon = islands.restore_after_erosion(island_fields,elevation)
        outlets = ocean.copy()
        outlets |= lagoon
        outlets[0] = True; outlets[-1] = True; outlets[:,0] = True; outlets[:,-1] = True
    t_erode = time.perf_counter() - t0
    t0 = time.perf_counter()
    if process is not None:
        pa = process['arrays']
        hyd = dict(bed=elevation, filled=np.where(np.isfinite(pa['water_surface_m']), pa['water_surface_m'], elevation),
                   receiver=np.asarray(pa['receiver']).ravel(), order=pa['order'],
                   area_m2=np.asarray(pa['drainage_area_m2']).ravel(), lake_id=pa['lake_id'],
                   passes=[], unresolved_depressions=0)
    elif v3:
        forbid = T['lake_forbid'] if binding is None else (T['lake_forbid'] | lagoon)
        hyd = gh.hydrology(elevation, ocean, mesh, outlets, float(p['depth_min_m']), float(p['lake_area_min_km2']) * 1e6,
                           int(p['breach_passes']), log, forbid=forbid, min_catch_m2=float(p['lake_min_catch_km2']) * 1e6)
    else:
        if binding is None:
            hyd = gh.hydrology(elevation, ocean, mesh, outlets, float(p['depth_min_m']), float(p['lake_area_min_km2']) * 1e6,
                               int(p['breach_passes']), log)
        else:
            hyd = gh.hydrology(elevation, ocean, mesh, outlets, float(p['depth_min_m']), float(p['lake_area_min_km2']) * 1e6,
                               int(p['breach_passes']), log,forbid=lagoon)
    t_hyd = time.perf_counter() - t0
    t0 = time.perf_counter()
    wet = (hyd['lake_id'] > 0) & ~ocean
    if process is not None:
        wet &= np.isfinite(process['arrays']['water_surface_m'])
    if binding is not None:
        wet &= ~lagoon
    lake_id = np.where(wet, hyd['lake_id'], 0).astype(np.int32)
    thr = gh.zoned_threshold(elevation, S, float(p['river_lo_km2']) * 1e6, float(p['river_hi_km2']) * 1e6, float(p['slope_split']))
    river_water = ocean if binding is None else (ocean | lagoon)
    active = gh.active_rivers(hyd['receiver'], hyd['order'], hyd['area_m2'], river_water, thr)
    lines = gh.trace_lines(hyd['receiver'], hyd['area_m2'], active, shape, first, S)
    px = np.asarray(mesh.node_x_m, np.float64); pz = np.asarray(mesh.node_z_m, np.float64)
    if p['smooth_rivers']:
        sx, sz, reverted = gh.smooth_centerline(px, pz, hyd['receiver'], active, S)
    else:
        sx, sz, reverted = px, pz, 0
    lake_links = None
    if v3:                                         # cut at the lake shore: no river over a lake, no through-lake chord
        rivers, lake_links = gh.cut_lines_at_lakes(lines, sx, sz, hyd['area_m2'], shape, ocean, lake_id)
        tl = dict(method='river lines cut at the lake shore (midpoint between last dry and first lake node); no through-lake chord',
                  through_lake_lines=0, pieces=len(rivers), raw_lines=len(lines))
    else:
        _, rivers0 = gh.standard_lines(lines, sx, sz, shape, ocean, wet)
        rivers, tl = gh.through_lake_lines(rivers0, lake_id, first, S)
    t_riv = time.perf_counter() - t0
    result = dict(terrain=T, elevation=elevation, ocean=ocean, mesh_seed=int(mesh_seed), hyd=hyd, wet=wet, lake_id=lake_id,
                active=active, rivers=rivers, through_lake=tl, lake_links=lake_links, smooth_reverted_nodes=int(reverted), incised=incised,
                timing=dict(**T['timing'], mesh_s=t_mesh, erosion_s=t_erode, hydrology_s=t_hyd, rivers_s=t_riv))
    if process is not None:
        result['world_processes'] = process
    if binding is not None:
        result['ocean_islands'] = dict(binding=binding,fields=island_fields,fractions=fractions,lagoon=lagoon,
                                      quota=islands.quota_statistics(binding,before_islands,elevation))
    if mountain_data is not None:
        if process is not None:
            mountain_data['process_peak_reports'] = world_process_adapter.island_peak_reports(
                binding, mountain_data['record'], process)
        result['island_mountains'] = mountain_data
    return result


# ------------------------------------------------------------------ freeze
def freeze(skeleton_path, out_dir, params=None, erosion=True, expected_identity=None, min_free_bytes=MIN_FREE_BYTES, log=print,
           relief='skeleton', *, island_product_path=None, expected_island_identity=None, skeleton_run_path=None, mountain_input_path=None,
           process_config=None):
    started = time.perf_counter()
    avail = memory_guard(min_free_bytes)
    sk = load_skeleton(skeleton_path, expected_identity)
    res = compute(sk, params, erosion, log, relief,island_product_path=island_product_path,
                  expected_island_identity=expected_island_identity,skeleton_run_path=skeleton_run_path,mountain_input_path=mountain_input_path,
                  process_config=process_config, process_out=Path(out_dir)/'world-processes' if process_config is not None else None)
    v3 = relief == 'orogen'
    v2 = relief == 'ridges' or v3                  # v3 shares the v2 manifest extras (ridge network, gullies)
    T = res['terrain']; p = T['params']; S = float(p['spacing_m']); shape = T['shape']; first = list(T['first'])
    hyd = res['hyd']; ocean = res['ocean']; wet = res['wet']; elevation = res['elevation']
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True); (out / 'vectors').mkdir(exist_ok=True)
    filled = hyd['filled'].astype(np.float32)
    status = np.where(ocean, 3, 5).astype(np.uint8)
    if 'ocean_islands' in res:
        status[(elevation<0)&~ocean] = 4
    arrays = dict(elevation_m=elevation.astype(np.float32), hydro_bed_m=hyd['bed'].astype(np.float32), status=status,
                  water_surface_m=np.where(wet, filled, np.nan).astype(np.float32),
                  drainage_area_m2=hyd['area_m2'].reshape(shape).astype(np.float32),
                  receiver=hyd['receiver'].reshape(shape).astype(np.int32), lake_id=res['lake_id'])
    if 'ocean_islands' in res:
        island_data = res['ocean_islands']
        fraction = island_data['fractions']
        arrays.update(frozen_island_land_fraction=fraction.land_fraction,protected_fraction=fraction.protected_fraction,
                      frozen_island_lagoon_fraction=fraction.lagoon_fraction,registered_lagoon=island_data['lagoon'])
    process_layers = {}
    if 'world_processes' in res:
        process_arrays = res['world_processes']['arrays']
        for name, unit in dict(discharge_m3_s='m3/s', temperature_c='degC', precipitation_mm_yr='mm/yr',
                              rock_index='1', bed_hardness='1', permeability_m2='m2', erosion_m='m', deposition_m='m',
                              soil_water_mm='mm', snow_swe_mm='mm', cover_fraction='1').items():
            if name in process_arrays and np.asarray(process_arrays[name]).shape == tuple(shape):
                arrays[name] = np.asarray(process_arrays[name])
                process_layers[name] = unit
    for name, a in arrays.items():
        np.save(out / (name + '.npy'), a, allow_pickle=False)
    lakes = gh.lake_vectors_labeled(np.where(wet, hyd['lake_id'], 0), filled, first, S)
    write_json(out / 'vectors/rivers.json', dict(schema='rivers-v1', lines=res['rivers']))
    write_json(out / 'vectors/lakes.json', dict(schema='lakes-v1', lakes=lakes))
    meanings = dict(
        elevation_m='fast procedural terrain surface/bed (skeleton-conditioned belts + light coarse erosion), NOT breached, not water surface',
        hydro_bed_m='derived hydrology bed: elevation plus breach cuts along irregular-graph receivers; routing only',
        status='3 ocean; 5 land (no closed-below-sea cells in this product)',
        water_surface_m='priority-flood surface (irregular graph) of kept lakes (deep and wide) on the breached bed; NaN dry',
        drainage_area_m2='contributing area on the irregular Delaunay routing graph (each node owns one grid cell of area), NOT discharge')
    units = dict(elevation_m='m', hydro_bed_m='m', status='1', water_surface_m='m', drainage_area_m2='m2')
    units.update(process_layers)
    meanings.update({name: 'Terragenesis published world process: ' + name for name in process_layers})
    if 'ocean_islands' in res:
        meanings['status'] = '3 final border-connected ocean; 4 closed below-sea bed including registered lagoon; 5 nonnegative land'
        for name in ('frozen_island_land_fraction','protected_fraction','frozen_island_lagoon_fraction','registered_lagoon'):
            units[name] = '1'
            meanings[name] = ('Frozen island source cell-footprint estimate; not final external-base land area' if name.startswith('frozen_')
                             else 'Registered island protection/lagoon; independent of cell-centre land')
    layers = {n: dict(file=n + '.npy', sha256=file_sha(out / (n + '.npy')), dtype=str(arrays[n].dtype), unit=units[n],
                      meaning=meanings[n], nodata=None) for n in units}
    for name in process_layers:
        layers[name].update(source='world-processes/manifest.json',
                            approximation='2km generated world process; monthly water and climate approximation')
        if name == 'discharge_m3_s':
            layers[name]['scenario'] = 'Mean discharge over one output year after one spinup year; generated monthly climate and lake storage'
    vectors = {k: dict(file='vectors/%s.json' % k, sha256=file_sha(out / ('vectors/%s.json' % k)), schema=k + '-v1') for k in ('rivers', 'lakes')}
    tg_root = gh.terragenesis_root()
    here = Path(__file__).parent
    stats = dict(land_fraction=float((~ocean).mean()), river_segments=len(res['rivers']), kept_lakes=len(lakes),
                 breach_passes=len(hyd['passes']), unresolved_depressions=hyd['unresolved_depressions'],
                 river_nodes=int(res['active'].sum()), through_lake=res['through_lake'],
                 max_drainage_area_m2=float(hyd['area_m2'].max()), elevation_min_m=float(elevation.min()),
                 elevation_max_m=float(elevation.max()), erosion_mean_lowering_m=[round(v, 3) for v in res['incised']])
    if 'ocean_islands' in res:
        stats.update(land_fraction=float((elevation>=0).mean()),closed_below_sea_fraction=float(((elevation<0)&~ocean).mean()),
                     connected_ocean_fraction=float(ocean.mean()),registered_lagoon_fraction=float(res['ocean_islands']['lagoon'].mean()))
    clean_params = {k: (list(v) if isinstance(v, tuple) else v) for k, v in p.items()}
    manifest = dict(
        schema=SCHEMA, producer='Terragenesis', algorithm_version=ALGORITHM_V3 if v3 else ALGORITHM_V2 if v2 else ALGORITHM,
        lineage=[sk['identity']], source_identity=sk['identity'],
        world_seed=sk['world_seed'],
        subseed_method='derive_subseed(world_seed, purpose) = first 8 bytes (little endian) of sha256("{world_seed}:dream-world-gen:{purpose}"); noise is value noise hashed from absolute metric lattice coordinates; the irregular mesh jitter is SplitMix64 of absolute native cell indices keyed by fast-relief/mesh',
        subseeds={k: str(v) for k, v in T['seeds'].items()}, ready=True,
        routing='irregular-delaunay (terragenesis irregular_drainage)',
        grid=dict(first_sample_xz_m=first, spacing_m=S, shape_zx=list(shape), semantics='cell-centre',
                  axes='X east, Z south; arrays [z,x]', length_unit='m', sea_level_m=0),
        shape_zx=list(shape), first_sample_xz_m=first, spacing_m=S, axes='arrays [z,x]; X east; Z south; metres; cell centres; sea=0',
        boundary='finite; no wrap',
        requested_domain_bounds_m=[sk['origin_xz_m'][0], sk['origin_xz_m'][1], sk['origin_xz_m'][0] + shape[1] * S, sk['origin_xz_m'][1] + shape[0] * S],
        layers=layers, vectors=vectors, parameters=clean_params, erosion_enabled=bool(erosion),
        hydrology=dict(method='irregular-graph breach-then-lake + irregular-graph accumulation + through-lake connections',
                       routing='irregular-delaunay (terragenesis irregular_drainage)', no_d8=True),
        skeleton=dict(identity=sk['identity'], path=str(Path(sk['path']).resolve()), identity_recomputes=sk['identity_recomputes'], arrays_verified=sk['arrays_verified'],
                      cell_m=sk['cell_m'], shape=list(sk['shape'])),
        declared_generated=[
            'Terrain: skeleton elevation proxy + crust thickness upsampled (bicubic, periodic) and mapped to belts; ridge detail from domain-warped ridged value noise scaled by belt weight',
            'Coast refinement: skeleton elevation plus fractal value noise decides sea/land; ocean specks removed',
            'Light coarse erosion: implicit stream-power incision on the irregular graph plus gentle hillslope diffusion (when erosion_enabled)',
            'Receivers, contributing area, lakes and river lines from irregular Delaunay graph routing (no D8, no 8-neighbour direction set)',
            'River vectors: metric node positions with constrained centreline smoothing; lake interiors are one through-lake connection per run'],
        limitations=[
            'World layer is NOT Terrain Diffusion output: valley/ridge detail differs from TD; mountain trends follow the shared skeleton',
            'Local 30 m TD rivers and coasts may not coincide with this 2 km layer; deviations are accepted (rule section 6)',
            'Graph nodes are jittered representative positions of grid cells, not new terrain samples; river geometry is a drawing of the routing graph',
            'area is not discharge; no precipitation-runoff simulation',
            'Lake surface is potential flood level of kept depressions, not permanent water. Boundary-crossing basins drain through the finite rim',
            'Skeleton periodicity is used for upsampling only; the product is a finite domain, edge continuity is not enforced'],
        statistics=stats,
        reused_code=dict(terragenesis_sha256={n: file_sha(tg_root / n) for n in (TG_FILES_V2 if v2 else TG_FILES)},
                         local_sha256={n: file_sha(here / n) for n in (('fast_relief.py', 'graph_hydro.py', 'config.py', 'ridge_network.py')
                                                                       if v2 else ('fast_relief.py', 'graph_hydro.py', 'config.py'))}),
        files={q.name: file_sha(q) for q in sorted(out.glob('*.npy'))})
    if v2:
        rm = sk['ridge_meta']
        manifest['skeleton'].update(algorithm=sk.get('algorithm'), path=str(Path(skeleton_path).resolve()),
                                    ridge_network_identity=rm['identity'], ridge_network_algorithm=rm['algorithm'],
                                    ridge_width_scale=rm['width_scale'], ridge_amp_m=rm['amp_m'])
        manifest['layers']['elevation_m']['meaning'] = ('fast procedural terrain surface/bed (lowland base + skeleton v3 ridge-network relief + '
                                                        'directional gullies + coarse erosion), NOT breached, not water surface')
        manifest['declared_generated'] = [
            'Terrain: lowland base (coast-distance ramp + FFT plains relief, skeleton cell, min/max-clamped bicubic upsample) plus the '
            'skeleton v3 vector ridge network rasterized at 2 km: max-union of segment tent profiles (1-d/w)^1.5 on domain-warped coordinates '
            'times a ridged multifractal crest field (same raster the skeleton elevation was box-averaged from); no Gaussian cross-section, no blur',
            'Gullies: Terragenesis directional-gullies-v1 on mountain cells, coordinates compressed by gully_scale',
            'Coast refinement: skeleton elevation plus fractal value noise decides sea/land; ocean specks removed',
            'Coarse erosion: %d rounds of implicit stream-power incision on the irregular graph, no incision cap; talus relaxation of '
            'over-steep 4-neighbour steps instead of Gaussian hillslope diffusion; no final smoothing' % int(p['erosion_iterations']),
            'Receivers, contributing area, lakes and river lines from irregular Delaunay graph routing (no D8, no 8-neighbour direction set)',
            'River vectors: metric node positions with constrained centreline smoothing; lake interiors are one through-lake connection per run']
        manifest['statistics'].update(gully_nodes=int(T['gully_nodes']), gully_abs_max_m=float(T['gully_abs_max_m']))
    if v3:
        links = res['lake_links'] or {}
        overlap = gh.river_lake_overlap(res['rivers'], res['lake_id'], first, S)
        manifest['statistics'].update(
            lake_links={str(k): v for k, v in sorted(links.items())},
            lakes_without_inflow=int(sum(1 for v in links.values() if not v['inflow'])),
            lakes_without_outflow=int(sum(1 for v in links.values() if not v['outflow'])),
            river_length_over_lake_km=overlap['over_lake_km'], river_lines_over_lake=overlap['lines_over_lake'], lake_filter=[{k: v for k, v in q.items()} for q in hyd['passes']])
        manifest['skeleton']['ridge_network_amp_m'] = float(sk['ridge_meta'].get('amp_m', 0.0))
        manifest['layers']['elevation_m']['meaning'] = ('fast procedural terrain surface/bed (lowland base + skeleton v4 orogen relief + '
                                                        'directional gullies + coarse erosion), NOT breached, not water surface')
        manifest['hydrology']['method'] = ('irregular-graph breach-then-lake (lakes not allowed on the ridge envelope, minimum catchment) '
                                           '+ irregular-graph accumulation; river lines cut at the lake shore')
        manifest['declared_generated'][0] = (
            'Terrain: lowland base plus the skeleton v4 orogen belts rasterized at 2 km: flat-topped belt platform floor * smoothstep(x/edge), '
            'x = 1 - d/W on domain-warped coordinates (plateau where the crust is thick), foothill ring of ridged-noise hills, 2-4 parallel '
            'fractal ranges with water gaps, branches and spurs (tent profile x ridged multifractal); no Gaussian cross-section, no blur')
        manifest['declared_generated'][-1] = ('River vectors: metric node positions with constrained centreline smoothing; lines are cut at the '
                                              'lake shore (inflow pieces carry to_lake, outflow pieces from_lake); no through-lake chord')
    if 'ocean_islands' in res:
        from . import ocean_island_adapter as islands
        data = res['ocean_islands']; binding = data['binding']
        write_json(out/'ocean-island-binding.json',binding.record)
        write_json(out/'vectors/ocean-islands.json',dict(schema='frozen-ocean-island-features-v1',
                   island_identity=binding.product.identity,features=islands.feature_records(binding)))
        manifest['lineage'].append(binding.product.identity)
        manifest['ocean_islands'] = dict(binding=binding.record,quota=data['quota'],area_sampling=data['fractions'].metadata)
        manifest['vectors']['ocean_islands'] = dict(file='vectors/ocean-islands.json',sha256=file_sha(out/'vectors/ocean-islands.json'),schema='frozen-ocean-island-features-v1')
        manifest['declared_generated'].append('Optional frozen Terragenesis island sidecar sampled after coast cleanup; initial mountain calibration precedes generation processes' if 'world_processes' in res else 'Optional frozen Terragenesis island sidecar sampled after coast cleanup; saved targets restored after erosion; final finite ocean topology recomputed')
        manifest['limitations'].extend(['Fraction layers describe frozen island source, not exact external-base combined area',
                                        'Registered lagoons excluded from ocean and ordinary freshwater lake vectors; no lagoon hydrodynamics or TD response verified'])
        manifest['reused_code']['local_sha256']['ocean_island_adapter.py'] = file_sha(Path(__file__).with_name('ocean_island_adapter.py'))
        manifest['ocean_islands']['binding_file'] = dict(file='ocean-island-binding.json',sha256=file_sha(out/'ocean-island-binding.json'))
    if 'island_mountains' in res:
        data = res['island_mountains']
        manifest['island_mountains'] = data
        peak_mode=any(p.get('blend_policy')=='frozen-island-global-raw-area-peak-v3'
                      for p in res['island_mountains']['record']['plans'])
        manifest['algorithm_version'] += '+frozen-island-mountains-v3' if peak_mode else '+frozen-island-mountains-v2'
        manifest['lineage'].append(data['record']['identity'])
        manifest['declared_generated'].append(data['meaning'])
        manifest['limitations'].append('Final world elevation samples native 30m island corrections at the coarse world grid; native detail is referenced separately')
        manifest['reused_code']['local_sha256']['web_island_stage.py'] = file_sha(Path(__file__).with_name('web_island_stage.py'))
    if 'world_processes' in res:
        from . import world_process_adapter
        world_process_adapter.publish(res['world_processes'], out/'world-processes')
        process_manifest = out/'world-processes'/'manifest.json'
        manifest['world_processes'] = dict(file='world-processes/manifest.json', sha256=file_sha(process_manifest),
                                           metadata=res['world_processes']['metadata'])
        manifest['reused_code']['terragenesis_sha256'].update({
            'terrain_pipeline/' + name: file_sha(tg_root/'terrain_pipeline'/name)
            for name in ('world_processes.py', 'world_process_hydrology.py', 'world_process_detail.py',
                         'world_geology.py', 'world_environment.py', 'world_environment_conditional.py',
                         'world_environment_world.py')})
        manifest['reused_code']['local_sha256']['world_process_adapter.py'] = file_sha(here/'world_process_adapter.py')
        manifest['algorithm_version'] += '+world-processes-v1'
        manifest['limitations'] = [v for v in manifest['limitations'] if 'no precipitation-runoff' not in v]
        manifest['declared_generated'] = [v for v in manifest['declared_generated'] if not v.startswith(('Coarse erosion:', 'Light coarse erosion:'))]
        manifest['declared_generated'].append('Terragenesis generation water/sediment shaping replaces old incision; geological materials and monthly environment are source-bound in world-processes')
        manifest['layers']['elevation_m']['meaning'] = 'Final generation bed after conservative coarse water/sediment shaping; initial island peak calibration is not reapplied'
        manifest['layers']['hydro_bed_m']['meaning'] = 'Same final process bed; no additional routing excavation'
        manifest['statistics']['published_height_quantization_max_m'] = float(np.max(np.abs(arrays['elevation_m'].astype(np.float64)-elevation)))
        manifest['layers']['water_surface_m']['meaning'] = 'Actual final output-month stored lake water level; NaN dry, independently budgeted from generation shaping'
        manifest['hydrology']['method'] = 'Terragenesis irregular graph routing, finite lake storage and monthly runoff; river vectors consume the same final receivers'
        manifest['limitations'] = [v for v in manifest['limitations'] if 'Lake surface is potential flood level' not in v]
        manifest['statistics']['geometric_breach_solid_volume_m3'] = float(np.maximum(elevation-hyd['bed'],0).sum()*S*S)
    manifest['identity'] = identity_of(manifest)
    write_json(out / 'manifest.json', manifest)
    write_json(out / 'runtime-stats.json', dict(
        note='run-time fields, deliberately outside manifest/identity', total_seconds=time.perf_counter() - started,
        **res['timing'], peak_working_set_mb=peak_memory_mb(), available_gib_at_start=avail / 2 ** 30, python=sys.version.split()[0],
        numpy=np.__version__, scipy=__import__('scipy').__version__, numba=__import__('numba').__version__, nodes=int(np.prod(shape))))
    log('FROZEN ' + manifest['identity'])
    return out, manifest
