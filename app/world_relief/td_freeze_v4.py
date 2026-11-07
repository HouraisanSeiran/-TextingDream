"""td-world-960m-v4: v3 terrain (elevation_m bit-identical) with meandering flat routing and slope-zoned river extraction.

Differences to v3, both in the derived hydrology layer only (``elevation_m`` is never touched):

* ``td_flats.route_flats(meander=...)``: the in-flat step cost is modulated by a deterministic, coordinate-addressed smooth
  noise (see ``td_flats.meander_noise``), so the towards-outlet distance is a Dijkstra distance and open-plain channels bend
  instead of running on straight shortest paths.
* River lines are extracted with a slope-zoned contributing-area threshold (low in steep terrain, high on plains) plus a
  downstream closure, so mountain/inland tributaries come back while river mouths stay as few trunk channels.
"""
from __future__ import annotations
import functools
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from scipy import ndimage
from .td_pages import file_sha, write_json
from .source import identity, subseed
from .td_freeze import assemble, standard_rivers
from .td_freeze_v2 import (smooth_offshore_blend, DEPTH_MIN_M, AREA_MIN_M2, BLEND_NEAR_M, BLEND_FAR_M, BLEND_SIGMA_CELLS,
                           RUNTIME_KEYS)
from . import drainage, td_hydro, td_flats

SCHEMA = 'td-world-960m-v4'
RIVER_LO_M2 = 100e6          # threshold where the smoothed slope >= SLOPE_SPLIT (steep terrain)
RIVER_HI_M2 = 300e6          # threshold on plains (same as v1-v3)
SLOPE_SPLIT = 0.015          # m/m, 5x5 box-smoothed |grad elevation_m| on the 960 m grid
SLOPE_SMOOTH_CELLS = 5


def zoned_threshold(elevation, spacing=960.0, lo=RIVER_LO_M2, hi=RIVER_HI_M2, split=SLOPE_SPLIT, smooth=SLOPE_SMOOTH_CELLS):
    gz, gx = np.gradient(np.asarray(elevation, np.float64), float(spacing))
    sm = ndimage.uniform_filter(np.hypot(gx, gz), smooth)
    return np.where(sm >= split, lo, hi)


def active_rivers(receiver, area, ocean, threshold):
    """Cells with area >= local threshold, plus the downstream closure (every active cell keeps a connected path to its outlet)."""
    rec = np.asarray(receiver, np.int64).ravel(); area = np.asarray(area).ravel(); oc = np.asarray(ocean, bool).ravel()
    selfrec = rec == np.arange(rec.size)
    active = (area >= np.asarray(threshold).ravel()) & ~oc & ~selfrec
    seeds = np.flatnonzero(active)
    for i in seeds[np.argsort(area[seeds], kind='stable')].tolist():
        r = int(rec[i])
        while not active[r] and not oc[r] and rec[r] != r:
            active[r] = True
            r = int(rec[r])
    return active


def river_lines_from_active(receiver, area, active, ocean, first, spacing):
    """Same segment tracing and ids as ``drainage.river_lines`` but for a precomputed active mask."""
    rec = np.asarray(receiver, np.int64).ravel(); area = np.asarray(area).ravel(); nx = ocean.shape[1]
    indegree = np.bincount(rec[active], minlength=rec.size)
    starts = np.flatnonzero(active & (indegree != 1))

    def stable(i):
        x = first[0] + (int(i) % nx) * spacing; z = first[1] + (int(i) // nx) * spacing
        return 'r-' + hashlib.sha256(f'{x:.3f},{z:.3f}'.encode()).hexdigest()[:20]
    lines = []
    for start in starts:
        path = [int(start)]; end = int(rec[start]); path.append(end)
        while active[end] and indegree[end] == 1:
            end = int(rec[end]); path.append(end)
        coords = [[first[0] + (i % nx) * spacing, first[1] + (i // nx) * spacing] for i in path]
        lines.append(dict(id=stable(start), downstream_id=stable(end) if active[end] else None, coordinates_xz_m=coords,
                          head_area_km2=float(area[start] / 1e6), outlet_area_km2=float(area[end] / 1e6)))
    upstream = {line['id']: [] for line in lines}
    for line in lines:
        if line['downstream_id'] in upstream:
            upstream[line['downstream_id']].append(line['id'])
    for line in lines:
        line['upstream_ids'] = sorted(upstream[line['id']])
    return sorted(lines, key=lambda line: line['id'])


def freeze_v4(directory, out_name='world-960m-v4', depth_min_m=DEPTH_MIN_M, area_min_m2=AREA_MIN_M2, smooth_blend=True):
    directory = Path(directory); started = time.perf_counter()
    h1, plan, metrics, skeleton, weight, td = assemble(directory, return_td=True)
    if smooth_blend:
        h, blend_changed = smooth_offshore_blend(h1, skeleton, td, weight)
    else:
        h, blend_changed = h1, np.zeros(h1.shape, bool)
    product = directory / out_name; product.mkdir(parents=True, exist_ok=True)
    ocean = drainage.ocean_mask(h); closed = (h < 0) & ~ocean
    first = plan['first_sample_xz_m']
    meander = dict(world_seed=int(plan['world_seed']), first_xz=(first[0], first[1]))
    router = functools.partial(td_flats.route_flats, meander=meander)
    t0 = time.perf_counter()
    res = td_hydro.breach_and_lakes(h, ocean, 960, depth_min_m, area_min_m2, router=router)
    hydro_seconds = time.perf_counter() - t0
    bed = res['bed'].astype(np.float32); filled = res['filled'].astype(np.float32)
    flow = res['flow']; wet = res['lake_wet'] & ~ocean
    water = np.where(wet, filled, np.nan).astype(np.float32)
    status = np.where(ocean, 3, np.where(closed, 4, 5)).astype(np.uint8)
    thr = zoned_threshold(h)
    active = active_rivers(flow['receiver'], flow['area_m2'], ocean, thr)
    raw_lines = river_lines_from_active(flow['receiver'], flow['area_m2'], active, ocean, first, 960)
    rivers = standard_rivers(raw_lines, ocean, closed, wet, first, 960)
    lakes = td_hydro.lake_vectors_labeled(np.where(wet, res['lake_id'], 0), filled, first, 960)
    arrays = dict(elevation_m=h, hydro_bed_m=bed, status=status, ocean_mask=ocean, inland_depression_mask=closed,
                  lake_id=np.where(wet, res['lake_id'], 0).astype(np.int32), lake_surface_m=filled, water_surface_m=water,
                  drainage_area_m2=flow['area_m2'].reshape(h.shape).astype(np.float32),
                  receiver=flow['receiver'].reshape(h.shape).astype(np.int32))
    for name, a in arrays.items():
        np.save(product / (name + '.npy'), a, allow_pickle=False)
    write_json(product / 'rivers.json', dict(schema='coordinate-river-segments-v1', lines=raw_lines))
    (product / 'vectors').mkdir(exist_ok=True)
    write_json(product / 'vectors/rivers.json', dict(schema='rivers-v1', lines=rivers))
    write_json(product / 'vectors/lakes.json', dict(schema='lakes-v1', lakes=lakes))
    layers = {}
    for name, unit, meaning in (
            ('elevation_m', 'm', 'terrain low-frequency surface/bed (blended TD/skeleton), NOT breached, not water surface'),
            ('hydro_bed_m', 'm', 'derived hydrology bed: elevation_m with narrow breach channels cut through shallow/small depressions; routing only'),
            ('status', '1', '3 ocean; 4 closed below sea; 5 land'),
            ('water_surface_m', 'm', 'priority-flood surface of kept lakes (deep and wide) on the breached bed; NaN dry'),
            ('drainage_area_m2', 'm2', 'D8 contributing area on hydro_bed_m with meandering convergent flat routing, NOT discharge')):
        path = product / (name + '.npy')
        layers[name] = dict(file=path.name, sha256=file_sha(path), dtype=str(arrays[name].dtype), unit=unit, meaning=meaning, nodata=None)
    vectors = {kind: dict(file=f'vectors/{kind}.json', sha256=file_sha(product / f'vectors/{kind}.json'), schema=kind + '-v1')
               for kind in ('rivers', 'lakes')}
    summary = json.loads((directory / 'generation-summary.json').read_text())
    runtime = {k: summary[k] for k in RUNTIME_KEYS if k in summary}
    generation = {k: v for k, v in summary.items() if k not in RUNTIME_KEYS}
    upstream_root = Path(__file__).resolve().parents[2].parent / '山川形意Terragenesis'
    model_root = upstream_root / 'models/terrain-diffusion-30m'
    code_names = ('td_resident.py', 'td_pages.py', 'td_freeze.py', 'td_freeze_v2.py', 'td_freeze_v3.py', 'td_freeze_v4.py',
                  'td_hydro.py', 'td_flats.py', 'drainage.py', 'source.py')
    if plan['algorithm'] == 'test-only':
        td_source = dict(test_fixture=True)
    else:
        td_source = dict(model_manifest=json.loads((model_root / 'manifest.json').read_text(encoding='utf-8')),
                         model_config=json.loads((model_root / 'config.json').read_text(encoding='utf-8')),
                         model_config_sha256=file_sha(model_root / 'config.json'),
                         upstream=json.loads((upstream_root / 'runtime/upstream.json').read_text(encoding='utf-8')),
                         conditioning_spacing_m=7680, cond_snr=[.65, .1, 1., .1, 1.], dtype='fp32', latents_batch_size=1,
                         provenance_capture='at CPU freeze after generation; per-page receipts do not bind model/config/code signatures')
    td_source['local_code_sha256'] = {n: file_sha(Path(__file__).with_name(n)) for n in code_names}
    det_metrics = {k: v for k, v in metrics.items() if k in ('pages', 'overlap_pairs', 'overlap_max_abs_m', 'overlap_mae_m')}
    runtime.update({k: v for k, v in metrics.items() if k not in det_metrics})
    meander_subseeds = {'flats/meander/%dm' % int(w): subseed(plan['world_seed'], 'flats/meander/%dm' % int(w))
                        for w, _ in td_flats.MEANDER_OCTAVES}
    meander_subseeds = {k: str(v) for k, v in meander_subseeds.items()}   # uint64 as decimal strings (JSON-safe)
    manifest = dict(schema=SCHEMA, producer='Terragenesis', algorithm_version=plan['algorithm'],
        lineage=[plan['plate_identity']], source_identity=plan['plate_identity'], world_seed=plan['world_seed'],
        subseed_method='subseed(world_seed, purpose) = first 8 bytes (big endian) of sha256("{world_seed}:{purpose}"); meander noise is coordinate-addressed lattice value noise (source.spatial_noise); TD seed read from plate manifest',
        subseeds=meander_subseeds, ready=True,
        grid=dict(first_sample_xz_m=first, spacing_m=960, shape_zx=plan['shape_zx'], semantics='cell-centre',
                  axes='X east, Z south; arrays [z,x]', length_unit='m', sea_level_m=0),
        shape_zx=plan['shape_zx'], first_sample_xz_m=first, spacing_m=960,
        axes='arrays [z,x]; X east; Z south; metres; cell centres; sea=0', boundary='finite; no wrap',
        requested_domain_bounds_m=plan['extent_bounds_m'], plan_identity=plan['plan_identity'], layers=layers, vectors=vectors,
        hydrology=dict(method='breach-then-lake+meandering-convergent-flats', depth_min_m=depth_min_m, area_min_m2=area_min_m2,
                       eps_drop_m=td_hydro.EPS_DROP, derived_layer='hydro_bed_m',
                       river_threshold=dict(rule='slope-zoned: area >= lo where 5x5 box-smoothed |grad elevation_m| >= split, else hi; plus downstream closure',
                                            lo_m2=RIVER_LO_M2, hi_m2=RIVER_HI_M2, slope_split=SLOPE_SPLIT, smooth_cells=SLOPE_SMOOTH_CELLS),
                       meander=dict(amp=td_flats.MEANDER_AMP, ortho_step_cost=td_flats.MEANDER_ORTHO_COST,
                                    away_weight=td_flats.MEANDER_AWAY_WEIGHT,
                                    octaves_wavelength_m_weight=[list(o) for o in td_flats.MEANDER_OCTAVES],
                                    purpose_names=sorted(meander_subseeds)),
                       elevation_m_modified=False,
                       flats='Barnes-2014-style towards-outlet + away-from-high gradient where the in-flat step cost is modulated by smooth coordinate noise (Dijkstra distance), D8 single receiver',
                       area='D8 receiver-tree contributing area (consistent with receiver and river lines)',
                       lake_rule='depression kept as lake only if depth>=depth_min_m AND area>=area_min_m2, or closed basin whose lowest cell is below sea level; others are breached along the flood-parent path'),
        blend=dict(smooth=bool(smooth_blend), near_m=BLEND_NEAR_M, far_m=BLEND_FAR_M, sigma_cells=BLEND_SIGMA_CELLS,
                   rule='same as v2: ocean cells farther than near_m from land low-passed; land and <=near_m unchanged from v1',
                   cells_changed_vs_v1=int(blend_changed.sum())),
        declared_generated=['Same terrain as td-world-960m-v3 and v2 (elevation_m bit-identical)',
            'Hydrology bed: priority-flood depressions shallower than D or smaller than A are breached; flats drain convergently with a small deterministic smooth perturbation so open-plain channels bend; terrain elevation_m is NOT eroded or filled',
            'D8 contributing area and single-receiver river lines with slope-zoned threshold (100 km2 steep / 300 km2 plains) plus downstream closure',
            'Lake pixel-edge polygons with holes, one per kept lake id; potential level, no water balance'],
        limitations=['960m D8 receiver direction bias; area is not discharge; no real precipitation-runoff simulation',
            'Breach channels are 1-cell wide cuts in a derived layer; valley widths/depths are not physical',
            'Lake surface is potential flood level of kept depressions, not permanent water. Boundary-crossing basins drain through finite rim',
            'Flat gradient and meander noise are routing devices, not terrain modifications; bends are noise-driven, not physical meander dynamics'],
        statistics=dict(**det_metrics, river_segments=len(rivers), potential_lakes=len(lakes), kept_lakes=len(lakes),
            ocean_cells=int(ocean.sum()), closed_below_sea_cells=int(closed.sum()),
            breach_cells_lowered=res['cells_lowered'], breach_passes=len(res['passes']),
            unresolved_depressions=res['unresolved_depressions'],
            flats=flow.get('flats'), river_cells=int(active.sum()),
            elevation_min_m=float(h.min()), elevation_max_m=float(h.max())),
        generation=generation, td_source=td_source,
        files={p.name: file_sha(p) for p in sorted(product.glob('*.npy'))})
    manifest['files']['rivers.json'] = file_sha(product / 'rivers.json')
    manifest['identity'] = identity(manifest)
    write_json(product / 'manifest.json', manifest)
    runtime.update(hydrology_seconds=hydro_seconds, total_seconds=time.perf_counter() - started, breach_passes_detail=res['passes'])
    write_json(product / 'runtime-stats.json', dict(note='run-time fields, deliberately outside manifest/identity', **runtime))
    print('FROZEN-V4 ' + manifest['identity'], flush=True)
    return product, manifest
