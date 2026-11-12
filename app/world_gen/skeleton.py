"""New tectonic skeleton generation for the world presets (CPU only, imports Terragenesis read-only).

Imports `terrain_pipeline.tectonic` from the Terragenesis workspace (evolve / freeze / save_product);
none of its files are modified. Legacy module names `tectonic_evolution` / `tectonic_product` are gone.
`plan_skeleton` is the resource pre-check (no generation). `generate_skeleton` is
explicit and refuses to run without enough free memory.

The starting continent mask is replaced through `evolve(config, initial_state)` (an official injection point)
by a preset-shaped periodic field. The land share is tuned by iterating the field threshold; mountain
cover is tuned through plate speed (faster plates -> more convergence thickening). Both targets and the
actual results are written to the manifest. Mountain cover is a proxy: share of land cells whose kinematic
buoyancy elevation exceeds MOUNTAIN_PROXY_M; it is not a measured geological quantity.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

from .config import WORLD_TYPES, derive_subseed, sha256_json

TERRAGENESIS = Path(__file__).resolve().parents[3] / '山川形意Terragenesis'
MOUNTAIN_PROXY_M = 1500.0
ALGORITHM = 'dream-world-skeleton-1'
ALGORITHM_V2 = 'dream-world-skeleton-2'
ALGORITHM_V3 = 'dream-world-skeleton-3'
ALGORITHM_V4 = 'dream-world-skeleton-4'
RIDGE_MODES = (None, 'fractal', 'orogen')
MIN_FREE_BYTES = 2 * 2 ** 30      # refuse below this: the task budget for this CPU job is 1.5 GiB


def _terragenesis():
    root = str(TERRAGENESIS)
    if root not in sys.path:
        sys.path.insert(0, root)
    from terrain_pipeline import tectonic
    return tectonic, tectonic


def periodic_noise(shape, seed, exponent=2.0, cutoff=None):
    """Smooth zero-mean unit-std noise on the torus (FFT filtered white noise)."""
    rng = np.random.default_rng(seed)
    white = rng.standard_normal(shape)
    fz = np.fft.fftfreq(shape[0])[:, None]
    fx = np.fft.fftfreq(shape[1])[None, :]
    radius = np.sqrt(fz ** 2 + fx ** 2)
    radius[0, 0] = 1.0
    gain = radius ** (-exponent / 2)
    gain[0, 0] = 0.0
    if cutoff:
        gain = gain * (radius < cutoff)
    out = np.fft.ifft2(np.fft.fft2(white) * gain).real
    return (out - out.mean()) / (out.std() + 1e-12)


def _pdist(delta, length):
    return (delta + length / 2) % length - length / 2


def _blobs(shape, rng, count, radius_range, aspect=(0.7, 1.4)):
    nz, nx = shape
    z, x = np.meshgrid((np.arange(nz) + .5) / nz, (np.arange(nx) + .5) / nx, indexing='ij')
    field = np.full(shape, -1.0)
    for _ in range(count):
        cx, cz = rng.random(2)
        r = rng.uniform(*radius_range)
        a = rng.uniform(*aspect)
        d = np.sqrt((_pdist(x - cx, 1.0) / (r * a)) ** 2 + (_pdist(z - cz, 1.0) / (r / a)) ** 2)
        field = np.maximum(field, 1 - d)
    return field


def land_field(preset, shape, world_seed):
    """Higher = more likely continental crust. Thresholding by quantile gives the land share."""
    if preset not in WORLD_TYPES:
        raise ValueError(f'unknown world type {preset!r}')
    rng = np.random.default_rng(derive_subseed(world_seed, 'preset-' + preset))
    noise = periodic_noise(shape, derive_subseed(world_seed, 'land-noise'), exponent=3.0)
    fine = periodic_noise(shape, derive_subseed(world_seed, 'land-fine'), exponent=1.6)
    nz, nx = shape
    z, x = np.meshgrid((np.arange(nz) + .5) / nz, (np.arange(nx) + .5) / nx, indexing='ij')
    if preset == 'multi-continent':
        base = _blobs(shape, rng, 5, (0.12, 0.22))
        return base * 2.0 + 0.55 * noise + 0.12 * fine
    if preset == 'pangaea':
        cx, cz = rng.uniform(0.35, 0.65, 2)
        d = np.sqrt((_pdist(x - cx, 1.0) / 0.5) ** 2 + (_pdist(z - cz, 1.0) / 0.5) ** 2)
        return (1 - d) * 2.2 + 0.5 * noise + 0.1 * fine
    if preset == 'archipelago':
        base = _blobs(shape, rng, 30, (0.03, 0.07))
        return base * 2.0 + 0.5 * noise + 0.35 * fine
    if preset == 'two-continents':
        base = np.full(shape, -1.0)
        for k, cx in enumerate((0.25, 0.75)):
            cz = rng.uniform(0.35, 0.65)
            r = rng.uniform(0.2, 0.25)
            d = np.sqrt((_pdist(x - cx, 1.0) / r) ** 2 + (_pdist(z - cz, 1.0) / (r * 1.3)) ** 2)
            base = np.maximum(base, 1 - d)
        return base * 2.0 + 0.5 * noise + 0.12 * fine
    # inland-sea: an annulus of land around a central sea, surrounded by the outer ocean
    cx, cz = rng.uniform(0.4, 0.6, 2)
    d = np.sqrt(_pdist(x - cx, 1.0) ** 2 + _pdist(z - cz, 1.0) ** 2)
    r0 = 0.24
    return -np.abs(d - r0) * 6.0 + 0.55 * noise + 0.12 * fine


def tectonic_config(cfg, *, speed_m_per_step=None, ocean_quantile=None):
    """TectonicConfig for a normalized world config (new-skeleton branch)."""
    te, _ = _terragenesis()
    w, sk = cfg['world'], cfg['skeleton']
    cell = sk['cell_size_km'] * 1000.0
    shape = (int(round(w['height_km'] / sk['cell_size_km'])), int(round(w['width_km'] / sk['cell_size_km'])))
    speed = speed_m_per_step if speed_m_per_step is not None else min(2000.0, cell * 0.2)
    return te.TectonicConfig(shape=shape, cell_size_m=cell, origin_x_m=w['origin_km'][0] * 1000.0,
                             origin_z_m=w['origin_km'][1] * 1000.0, plate_count=sk['plates'],
                             microcells_per_plate=sk['microcells_per_plate'], min_plate_cells=sk['min_plate_cells'],
                             world_seed=cfg['world_seed'], steps=sk['steps'], max_speed_m_per_step=float(speed))


def plan_skeleton(cfg, *, max_memory_bytes=2_000_000_000, max_cell_plate_steps=200_000_000):
    """Resource pre-check through Terragenesis `plan()`. Does not generate anything."""
    _, tp = _terragenesis()
    tc = tectonic_config(cfg)
    # tp.plan() validates world_seed == 20261020 (tp.WORLD_SEED); plan() only uses the seed for an upper bound of the
    # shape search, so the pinned seed is substituted for the pre-check only.
    import dataclasses
    report = tp.plan(dataclasses.replace(tc, world_seed=tp.WORLD_SEED), max_memory_bytes=max_memory_bytes,
                     max_cell_plate_steps=max_cell_plate_steps)
    report = {k: v for k, v in report.items() if k != 'config'}
    report['plan_seed_substituted'] = tp.WORLD_SEED if tc.world_seed != tp.WORLD_SEED else None
    cell = cfg['skeleton']['cell_size_km']
    report['shape_zx'] = list(tc.shape)
    report['cell_size_km'] = cell
    report['prepare_tectonic_world_args'] = (
        f"plan --shape {tc.shape[0]} {tc.shape[1]} --cell-size-m {tc.cell_size_m:g} "
        f"--origin-m {tc.origin_x_m:g} {tc.origin_z_m:g} --plates {tc.plate_count} "
        f"--microcells-per-plate {tc.microcells_per_plate} --min-plate-cells {tc.min_plate_cells} --steps {tc.steps}")
    report['note'] = ('prepare_tectonic_world.py hard-codes world_seed=20261020; this module passes the configured '
                      'world_seed itself, so use tools/generate_world_skeleton.py to generate (not that CLI).')
    return report


def _initial_state(te, tc, cfg, field, ocean_quantile):
    base = te.initialize(tc)
    thr = np.quantile(field, ocean_quantile)
    soft = 0.15 * (field.max() - field.min())
    continent = np.clip((field - thr) / soft + 0.5, 0, 1)
    cov = base.plate_coverage
    return te.CrustState(cov, cov * continent * tc.continental_thickness_m, cov * (1 - continent) * tc.oceanic_thickness_m,
                         base.plate_seeds_m, base.velocities_m_per_step, 0, base.formation)


def measure(te, result):
    f = te.surface_fields(result.final)
    elev = f['elevation_m']
    land = elev > 0
    land_n = int(land.sum())
    return dict(ocean_fraction=float(1 - land.mean()),
                mountain_land_fraction=float((elev > MOUNTAIN_PROXY_M)[land].mean()) if land_n else 0.0,
                land_cells=land_n, max_elevation_m=float(elev.max()), min_elevation_m=float(elev.min())), elev


def generate_skeleton(cfg, out_dir, *, max_iterations=5, ocean_tol=0.02, mountain_tol=0.35, available_bytes=None,
                      enhance=False, ridges=None, orogen_params=None, record_history=False):
    """Explicit generation into out_dir (artifacts/worlds/<name>/). Returns the manifest dict.

    enhance=False: algorithm dream-world-skeleton-1 (v1; mountains only from the kinematic thickening, speed tuned).
    enhance=True: algorithm dream-world-skeleton-2: speed fixed, only the ocean share is iterated (tolerance 0.01
    unless ocean_tol is tighter), then app.world_gen.mountains.enhance_mountains rebuilds convergent-boundary
    mountain belts on land only (land/sea split untouched) to hit the mountain target.
    ridges='fractal': algorithm dream-world-skeleton-3: same ocean loop as v2, then app.world_gen.ridge_network builds a vector
    ridge network (main ridges, branches, passes, gaps) that is stored in the npz (ridges/*) and from which the land
    elevation is derived (no Gaussian cross-section, no Gaussian blur). Takes precedence over enhance.
    orogen_params: optional overrides of ridge_network.OROGEN_DEFAULTS for ridges='orogen' (e.g. {'target_cover': 0.22});
    None keeps the defaults (identical product). The applied values are recorded in ridge_network.params.
    """
    if ridges not in RIDGE_MODES:
        raise ValueError(f'unknown ridges mode {ridges!r}')
    v4 = ridges == 'orogen'                  # dream-world-skeleton-4: orogen belts (ridge_network.build_orogen_mountains)
    v3 = ridges == 'fractal' or v4           # v4 shares the v3 path (ocean copied from v2, ridges/* arrays)
    if v3:
        enhance = True                       # v3 uses the v2 ocean loop (speed fixed, ocean share only)
    if enhance:
        ocean_tol = min(ocean_tol, 0.01)
    from .sysmem import available_memory_bytes
    te, tp = _terragenesis()
    avail = available_memory_bytes() if available_bytes is None else available_bytes
    if avail < MIN_FREE_BYTES:
        raise MemoryError(f'available memory {avail} < {MIN_FREE_BYTES} bytes; not starting skeleton generation')
    sk = cfg['skeleton']
    if sk['source'] != 'new':
        raise ValueError('config does not ask for a new skeleton')
    w = cfg['world']
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cell = sk['cell_size_km'] * 1000.0
    cfl_cap = cell * 0.45                   # L1 CFL: |vx|+|vz| <= cell; speeds are scaled in (0.4..1)*max, worst diagonal 1.414*max
    speed = min(2000.0, cell * 0.2)
    shape = (int(round(w['height_km'] / sk['cell_size_km'])), int(round(w['width_km'] / sk['cell_size_km'])))
    field = land_field(w['type'], shape, cfg['world_seed'])
    if cfg.get('geography_features'):
        from .geography import bias_land_field
        field = bias_land_field(field, cfg)
    quantile = w['ocean_fraction']
    target_m = w['mountain_target_land_fraction']
    history, best = [], None
    started = time.perf_counter()
    for it in range(max_iterations):
        tc = tectonic_config(cfg, speed_m_per_step=speed)
        plan = plan_skeleton(cfg, max_memory_bytes=1_500_000_000)
        if not plan['allowed']:
            raise ValueError('Terragenesis plan() rejected the configuration: ' + json.dumps(plan))
        trajectory = []
        def capture_stage(index, fields):
            trajectory.append({k: np.asarray(fields[k]).copy() for k in
                               ('elevation_m', 'continental_fraction', 'plate_id', 'crust_thickness_m')})
        initial_state = _initial_state(te, tc, cfg, field, quantile)
        result = (te.evolve(tc, initial_state, stage_callback=capture_stage) if record_history
                  else te.evolve(tc, initial_state))
        m, elev = measure(te, result)
        m.update(iteration=it, ocean_quantile=float(quantile), speed_m_per_step=float(speed))
        history.append(m)
        score = abs(m['ocean_fraction'] - w['ocean_fraction']) / ocean_tol
        if not enhance:
            score += abs(m['mountain_land_fraction'] - target_m) / (target_m * mountain_tol)
        if best is None or score < best[0]:
            best = (score, tc, result, m, trajectory)
        ocean_ok = abs(m['ocean_fraction'] - w['ocean_fraction']) <= ocean_tol
        mount_ok = enhance or abs(m['mountain_land_fraction'] - target_m) <= target_m * mountain_tol
        if ocean_ok and mount_ok:
            break
        quantile = float(np.clip(quantile + 0.9 * (w['ocean_fraction'] - m['ocean_fraction']), 0.05, 0.97))
        if not enhance:
            ratio = target_m / max(m['mountain_land_fraction'], 0.01)
            speed = float(np.clip(speed * ratio ** 0.5, 500.0, cfl_cap))
    _, tc, result, final, trajectory = best
    # tp.freeze/save_product pin world_seed to 20261020 and cannot hold a configured seed, so the skeleton is stored
    # as the evolved surface fields in a plain npz with the world manifest (not tp's frozen-product format).
    path = out_dir / 'skeleton.npz'
    fin = dict(te.surface_fields(result.final))
    raw_elev = np.asarray(fin['elevation_m'], dtype=np.float64)
    enh_meta = None
    ridge_arrays = None
    if v3:
        from . import ridge_network as rn, mountains as mt
        raw_land = raw_elev > 0
        raw_mountain = float((raw_elev > MOUNTAIN_PROXY_M)[raw_land].mean())
        # ocean values are exactly the v2 ones: the v2 enhancement + deep-ocean smoothing is recomputed and only its ocean
        # cells are kept (v2's smoothing kernel sees land values, so smoothing the v3 land would shift the open ocean)
        v2_elev, _ = mt.enhance_mountains(raw_elev, np.asarray(fin['plate_id']), result.final.velocities_m_per_step,
                                          cell_m=tc.cell_size_m, world_seed=cfg['world_seed'], target_fraction=target_m,
                                          proxy_m=MOUNTAIN_PROXY_M)
        raw_smoothed, smoothing = smooth_deep_ocean(v2_elev)
        del v2_elev
        if v4:
            land_elev, _, net, enh_meta = rn.build_orogen_mountains(
                raw_elev, np.asarray(fin['plate_id']), result.final.velocities_m_per_step, np.asarray(fin['crust_thickness_m']),
                cell_m=tc.cell_size_m, origin_xz_m=(tc.origin_x_m, tc.origin_z_m), world_seed=cfg['world_seed'],
                params=orogen_params, proxy_m=MOUNTAIN_PROXY_M)
        else:
            land_elev, _, net, enh_meta = rn.build_skeleton_mountains(
                raw_elev, np.asarray(fin['plate_id']), result.final.velocities_m_per_step, cell_m=tc.cell_size_m,
                origin_xz_m=(tc.origin_x_m, tc.origin_z_m), world_seed=cfg['world_seed'], target_fraction=target_m,
                proxy_m=MOUNTAIN_PROXY_M)
        enh_meta['mountain_land_fraction_before'] = raw_mountain
        assert ((land_elev > 0) == raw_land).all()
        fin['elevation_m'] = np.where(raw_land, land_elev, raw_smoothed).astype(np.float32)
        assert ((fin['elevation_m'] > 0) == raw_land).all()
        final = dict(final, mountain_land_fraction=float((fin['elevation_m'] > MOUNTAIN_PROXY_M)[raw_land].mean()))
        ridge_arrays = rn.npz_arrays(net)
        smoothing = dict(smoothing, note='v3: ocean cells copied from the v2 path (v2 enhancement + this smoothing), so the ocean is identical to dream-world-skeleton-2 of the same config')
    elif enhance:
        from . import mountains as mt
        raw_land = raw_elev > 0
        raw_mountain = float((raw_elev > MOUNTAIN_PROXY_M)[raw_land].mean())
        raw_elev, enh_meta = mt.enhance_mountains(raw_elev, np.asarray(fin['plate_id']), result.final.velocities_m_per_step,
                                                  cell_m=tc.cell_size_m, world_seed=cfg['world_seed'], target_fraction=target_m,
                                                  proxy_m=MOUNTAIN_PROXY_M)
        enh_meta['mountain_land_fraction_before'] = raw_mountain
        assert ((raw_elev > 0) == raw_land).all()
        final = dict(final, mountain_land_fraction=float((raw_elev > MOUNTAIN_PROXY_M)[raw_land].mean()))
    if not v3:
        fin['elevation_m'], smoothing = smooth_deep_ocean(raw_elev)
    extra_arrays = dict(ridge_arrays or {})
    if record_history:
        for key in ('elevation_m', 'continental_fraction', 'plate_id', 'crust_thickness_m'):
            extra_arrays['initial/' + key] = np.asarray(te.surface_fields(result.initial)[key])
            extra_arrays['history/' + key] = np.stack([stage[key] for stage in trajectory])
        extra_arrays['history/layout_correction_m'] = fin['elevation_m'] - te.surface_fields(result.final)['elevation_m']
    plate_identity = write_plate_npz(path, tc, fin, result.final.velocities_m_per_step, smoothing, cfg, tp,
                                     extra_arrays=extra_arrays,
                                     extra_manifest=None if not v3 else dict(
                                         algorithm=ALGORITHM_V4 if v4 else ALGORITHM_V3,
                                         ridge_network=dict(algorithm=enh_meta['algorithm'], identity=enh_meta['identity'],
                                                            arrays=sorted(ridge_arrays), layout=rn.LAYOUT,
                                                            width_scale=float(enh_meta['width_scale']),
                                                            amp_m=float(enh_meta['amp_m']), params=enh_meta['params'],
                                                            subseeds=enh_meta['subseeds'],
                                                            mountain_land_fraction=final['mountain_land_fraction'],
                                                            target_land_fraction=float(target_m), proxy_m=MOUNTAIN_PROXY_M)))
    import hashlib
    file_sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    preview = out_dir / 'preview.png'
    render_preview(elev=fin['elevation_m'], path=preview)
    manifest = dict(
        schema='dream-world-skeleton-run-v1',
        algorithm=ALGORITHM_V4 if v4 else ALGORITHM_V3 if v3 else ALGORITHM_V2 if enhance else ALGORITHM,
        config_identity=cfg['identity'],
        world_name=cfg['world_name'], world_seed=cfg['world_seed'], world_type=w['type'],
        subseeds={k: derive_subseed(cfg['world_seed'], k) for k in ('preset-' + w['type'], 'land-noise', 'land-fine')},
        subseed_method="SHA256(f'{world_seed}:dream-world-gen:{purpose}')[:8] little-endian; tectonic purposes use Terragenesis' own derivation",
        product=dict(file='skeleton.npz', sha256=file_sha(path), plate_identity=plate_identity, deep_ocean_smoothing=smoothing,
                     format='TD-readable plate npz (manifest_json + final/* arrays; read by app.world_relief.td_resident.read_plate); not tp frozen product', shape_zx=list(tc.shape),
                     cell_size_m=tc.cell_size_m, origin_xz_m=[tc.origin_x_m, tc.origin_z_m], plates=tc.plate_count, steps=tc.steps),
        targets=dict(ocean_fraction=w['ocean_fraction'], mountain_cover=w['mountain_cover'], mountain_target_land_fraction=target_m),
        actual=dict(ocean_fraction=final['ocean_fraction'], mountain_land_fraction=final['mountain_land_fraction'],
                    ocean_deviation=final['ocean_fraction'] - w['ocean_fraction'],
                    mountain_deviation=final['mountain_land_fraction'] - target_m,
                    speed_m_per_step=final['speed_m_per_step']),
        iterations=history, mountain_proxy=f'share of land cells (elevation>0) with proxy elevation > {MOUNTAIN_PROXY_M} m',
        limitations=['kinematic buoyancy proxy, not geodynamics', 'ocean fraction = cells with proxy elevation < 0',
                     'deep-ocean stripes: the donor-cell advection of Terragenesis leaves 1-2 cell period column/row ripples (60-300 m) in oceanic thickness after plate shear; elevation_m is smoothed with a wrap-around Gaussian only >= 3 cells from land (coast and land cells untouched, see product.deep_ocean_smoothing); the other fields are the raw evolution output',
                     'preview has no symbols; colours are elevation only', 'tuned within <= %d iterations; deviations are reported, not hidden' % max_iterations],
        seconds=time.perf_counter() - started, peak_rss_bytes=_peak_rss())
    if v3:
        manifest['subseeds'].update({k: int(v) for k, v in enh_meta['subseeds'].items()})
        manifest['ridge_network'] = {k: v for k, v in enh_meta.items() if k != 'subseeds'}
        manifest['terragenesis_reuse'] = [r for r in mt.reuse_record(TERRAGENESIS) if r['file'] != 'terrain_pipeline/skeleton_mountains.py']
        manifest['limitations'].append('v3: land elevation_m is derived from the vector ridge network (ridges/* arrays); continental_fraction / crust_thickness_m / plate_id stay raw evolution output; ridges follow convergent plate boundaries, not a geodynamic model; at the skeleton cell the relief is a box mean of the 2 km raster, so single spurs are below the cell size - read ridges/* for the structure')
        manifest['targets']['mountain_tolerance_abs'] = 0.02
        manifest['targets']['ocean_tolerance_abs'] = 0.015
        manifest['actual']['mountain_within_tolerance'] = abs(manifest['actual']['mountain_deviation']) <= 0.02
        manifest['actual']['ocean_within_tolerance'] = abs(manifest['actual']['ocean_deviation']) <= 0.015
        if v4:
            lo, hi = enh_meta['cover_band']
            area = enh_meta['mountain_area_land_fraction']
            manifest['targets'].update(mountain_area_land_fraction_band=[lo, hi], mountain_area_target=enh_meta['target_cover'],
                                       high_mountain_note='share of land > 1500 m is reported, not a target (user 2026-11-05)')
            manifest['actual'].update(mountain_area_land_fraction=area, high_mountain_land_fraction=enh_meta['high_mountain_land_fraction'],
                                      mountain_area_within_band=bool(lo <= area <= hi))
            manifest['limitations'][-1] = ('v4: land elevation_m is derived from the orogen belt network (ridges/* arrays incl. belt_*): '
                                           'belt platform + foothill ring + 2-4 parallel fractal ranges with water gaps, branches and spurs; '
                                           'belts follow convergent plate boundaries, not a geodynamic model; mountain area = belt footprint '
                                           '(incl. foothills, basins, plateaus), box mean of the 2 km raster at the skeleton cell')
    elif enhance:
        manifest['subseeds'].update(enh_meta['subseeds'])
        meta_out = {k: v for k, v in enh_meta.items() if k != 'subseeds'}
        manifest['mountain_enhancement'] = meta_out
        manifest['terragenesis_reuse'] = mt.reuse_record(TERRAGENESIS)
        manifest['limitations'].append('mountain enhancement rewrites land elevation_m only; continental_fraction / crust_thickness_m / plate_id stay raw evolution output; belts follow convergent plate boundaries, not a geodynamic model')
        manifest['targets']['mountain_tolerance_abs'] = 0.02
        manifest['targets']['ocean_tolerance_abs'] = 0.015
        manifest['actual']['mountain_within_tolerance'] = abs(manifest['actual']['mountain_deviation']) <= 0.02
        manifest['actual']['ocean_within_tolerance'] = abs(manifest['actual']['ocean_deviation']) <= 0.015
    if cfg.get('geography_features'):
        from .geography import result_record
        manifest['geography'] = result_record(cfg, fin['elevation_m'])
    manifest['identity'] = sha256_json({k: v for k, v in manifest.items() if k not in ('seconds', 'peak_rss_bytes')})
    (out_dir / 'skeleton-run.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    return manifest


def smooth_deep_ocean(elev, sigma=1.5, near_cells=2, ramp_cells=3):
    """Remove advection ripples in open ocean. Weight 0 within `near_cells` of land, ramps to 1 over `ramp_cells`."""
    from scipy import ndimage
    e = np.asarray(elev, dtype=np.float64)
    ocean = e < 0
    if not ocean.any() or ocean.all():
        return e.astype(np.float32), dict(applied=False)
    pad = int(near_cells + ramp_cells + 2)
    wrapped = np.pad(ocean, pad, mode='wrap')
    dist = ndimage.distance_transform_edt(wrapped)[pad:-pad, pad:-pad]
    w = np.clip((dist - near_cells) / ramp_cells, 0, 1) * ocean
    smooth = ndimage.gaussian_filter(e, sigma, mode='wrap')
    out = e * (1 - w) + np.minimum(smooth, -1.0) * w
    out = np.where(ocean, np.minimum(out, -1.0), e)
    before = float(np.abs(np.diff(e, axis=1))[ocean[:, 1:] & ocean[:, :-1]].mean())
    after = float(np.abs(np.diff(out, axis=1))[ocean[:, 1:] & ocean[:, :-1]].mean())
    return out.astype(np.float32), dict(applied=True, sigma_cells=sigma, near_land_cells_untouched=near_cells, ramp_cells=ramp_cells,
                                         mean_abs_dx_ocean_before_m=before, mean_abs_dx_ocean_after_m=after)


def write_plate_npz(path, tc, fields, velocities, smoothing, cfg, tp, extra_arrays=None, extra_manifest=None):
    """Write skeleton.npz in the layout TD's read_plate expects: manifest_json (0-d str) + final/<name> arrays.

    identity = SHA-256 of canonical manifest without 'identity' (sort_keys, compact, allow_nan=False), the same rule as
    app/world_relief/source.identity. arrays[...]['sha256'] = SHA-256 of array.tobytes()."""
    import hashlib
    arrays = {
        'final/elevation_m': np.ascontiguousarray(fields['elevation_m'], dtype=np.float32),
        'final/plate_id': np.ascontiguousarray(fields['plate_id'], dtype=np.int16),
        'final/continental_fraction': np.ascontiguousarray(fields['continental_fraction'], dtype=np.float32),
        'final/crust_thickness_m': np.ascontiguousarray(fields['crust_thickness_m'], dtype=np.float32),
        'final/velocities_m_per_step': np.ascontiguousarray(velocities, dtype=np.float64),
    }
    ocean, _ = tp.connected_ocean(arrays['final/elevation_m'].astype(np.float64))
    arrays['final/ocean_connected'] = np.ascontiguousarray(ocean)
    for k, v in (extra_arrays or {}).items():
        arrays[k] = np.ascontiguousarray(v)
    cfgd = dict(shape=list(tc.shape), cell_size_m=tc.cell_size_m, origin_x_m=tc.origin_x_m, origin_z_m=tc.origin_z_m,
                plate_count=tc.plate_count, world_seed=int(tc.world_seed), steps=tc.steps,
                max_speed_m_per_step=tc.max_speed_m_per_step, microcells_per_plate=tc.microcells_per_plate,
                min_plate_cells=tc.min_plate_cells)
    manifest = dict(schema='dream-world-skeleton-plate-v1', algorithm=ALGORITHM, config=cfgd,
                    world_name=cfg['world_name'], world_type=cfg['world']['type'], world_config_identity=cfg['identity'],
                    deep_ocean_smoothing=smoothing,
                    arrays={k: dict(dtype=str(v.dtype), shape=list(v.shape), sha256=hashlib.sha256(v.tobytes()).hexdigest())
                            for k, v in arrays.items()})
    if extra_manifest:
        manifest.update(extra_manifest)
    if cfg.get('geography_features'):
        from .geography import result_record
        manifest['geography'] = result_record(cfg, arrays['final/elevation_m'])
    manifest['identity'] = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    np.savez_compressed(path, manifest_json=np.array(json.dumps(manifest, sort_keys=True)), **{k: v for k, v in arrays.items()})
    return manifest['identity']


def _peak_rss():
    try:
        import psutil
        info = psutil.Process().memory_info()
        return int(getattr(info, 'peak_wset', info.rss))
    except Exception:
        pass
    try:                                   # no psutil: Windows PeakWorkingSetSize through ctypes
        import ctypes
        from ctypes import wintypes

        class _PMC(ctypes.Structure):
            _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD), ('PeakWorkingSetSize', ctypes.c_size_t),
                        ('WorkingSetSize', ctypes.c_size_t), ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
                        ('QuotaPagedPoolUsage', ctypes.c_size_t), ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
                        ('QuotaNonPagedPoolUsage', ctypes.c_size_t), ('PagefileUsage', ctypes.c_size_t),
                        ('PeakPagefileUsage', ctypes.c_size_t)]
        pmc = _PMC()
        pmc.cb = ctypes.sizeof(pmc)
        k32 = ctypes.WinDLL('kernel32')
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi = ctypes.WinDLL('psapi')
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(_PMC), wintypes.DWORD]
        if psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb):
            return int(pmc.PeakWorkingSetSize)
    except Exception:
        pass
    return None


def render_preview(elev, path, scale=4):
    """Elevation-only hypsometric preview with light shading. No symbols, no labels."""
    from PIL import Image
    e = np.asarray(elev, dtype=np.float64)
    img = np.zeros(e.shape + (3,), dtype=np.float64)
    sea = e <= 0
    depth = np.clip(-e / 4500.0, 0, 1)[sea]
    img[sea] = np.stack([20 + 60 * (1 - depth), 80 + 90 * (1 - depth), 140 + 90 * (1 - depth)], axis=1)
    stops = [(0, (96, 150, 80)), (600, (170, 180, 100)), (1500, (150, 120, 80)), (3000, (120, 100, 90)), (5000, (245, 245, 245))]
    land = ~sea
    hv = np.clip(e[land], 0, 5000)
    xs = [s[0] for s in stops]
    for c in range(3):
        img[..., c][land] = np.interp(hv, xs, [s[1][c] for s in stops])
    gz, gx = np.gradient(e)
    shade = np.where(sea, 1.0, np.clip(1 + (gx - gz) / 6000.0, 0.7, 1.25))   # no relief shading in the ocean
    img = np.clip(img * shade[..., None], 0, 255).astype(np.uint8)
    im = Image.fromarray(img).resize((e.shape[1] * scale, e.shape[0] * scale), Image.NEAREST)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    im.save(path)
