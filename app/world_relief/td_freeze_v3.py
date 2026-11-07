"""td-world-960m-v3: v2 terrain (elevation_m bit-identical) with convergent flat routing in the derived hydrology layer.

Only hydro_bed_m / receiver / drainage_area_m2 / rivers / lakes are re-derived: flats drain through ``td_flats.route_flats``
(Barnes et al. 2014 style towards-outlet + away-from-high-ground gradient) instead of parallel flood-parent lines.
"""
from __future__ import annotations
import json
from pathlib import Path
import time
import numpy as np
from .td_pages import file_sha, write_json
from .source import identity
from .td_freeze import assemble, standard_rivers
from .td_freeze_v2 import (smooth_offshore_blend, DEPTH_MIN_M, AREA_MIN_M2, BLEND_NEAR_M, BLEND_FAR_M, BLEND_SIGMA_CELLS,
                           RUNTIME_KEYS)
from . import drainage, td_hydro, td_flats

SCHEMA = 'td-world-960m-v3'


def freeze_v3(directory, out_name='world-960m-v3', depth_min_m=DEPTH_MIN_M, area_min_m2=AREA_MIN_M2, smooth_blend=True):
    directory = Path(directory); started = time.perf_counter()
    h1, plan, metrics, skeleton, weight, td = assemble(directory, return_td=True)
    if smooth_blend:
        h, blend_changed = smooth_offshore_blend(h1, skeleton, td, weight)
    else:
        h, blend_changed = h1, np.zeros(h1.shape, bool)
    product = directory / out_name; product.mkdir(parents=True, exist_ok=True)
    ocean = drainage.ocean_mask(h); closed = (h < 0) & ~ocean
    t0 = time.perf_counter()
    res = td_hydro.breach_and_lakes(h, ocean, 960, depth_min_m, area_min_m2, router=td_flats.route_flats)
    hydro_seconds = time.perf_counter() - t0
    bed = res['bed'].astype(np.float32); filled = res['filled'].astype(np.float32)
    flow = res['flow']; wet = res['lake_wet'] & ~ocean
    water = np.where(wet, filled, np.nan).astype(np.float32)
    status = np.where(ocean, 3, np.where(closed, 4, 5)).astype(np.uint8)
    first = plan['first_sample_xz_m']
    raw_lines = drainage.river_lines(flow, ocean, first, 960)
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
            ('drainage_area_m2', 'm2', 'D8 contributing area on hydro_bed_m with convergent flat routing, NOT discharge')):
        path = product / (name + '.npy')
        layers[name] = dict(file=path.name, sha256=file_sha(path), dtype=str(arrays[name].dtype), unit=unit, meaning=meaning, nodata=None)
    vectors = {kind: dict(file=f'vectors/{kind}.json', sha256=file_sha(product / f'vectors/{kind}.json'), schema=kind + '-v1')
               for kind in ('rivers', 'lakes')}
    summary = json.loads((directory / 'generation-summary.json').read_text())
    runtime = {k: summary[k] for k in RUNTIME_KEYS if k in summary}
    generation = {k: v for k, v in summary.items() if k not in RUNTIME_KEYS}
    upstream_root = Path(__file__).resolve().parents[2].parent / '山川形意Terragenesis'
    model_root = upstream_root / 'models/terrain-diffusion-30m'
    code_names = ('td_resident.py', 'td_pages.py', 'td_freeze.py', 'td_freeze_v2.py', 'td_freeze_v3.py', 'td_hydro.py',
                  'td_flats.py', 'drainage.py')
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
    manifest = dict(schema=SCHEMA, producer='Terragenesis', algorithm_version=plan['algorithm'],
        lineage=[plan['plate_identity']], source_identity=plan['plate_identity'], world_seed=plan['world_seed'],
        subseed_method='No stochastic postprocessing; TD seed read from plate manifest', subseeds={}, ready=True,
        grid=dict(first_sample_xz_m=first, spacing_m=960, shape_zx=plan['shape_zx'], semantics='cell-centre',
                  axes='X east, Z south; arrays [z,x]', length_unit='m', sea_level_m=0),
        shape_zx=plan['shape_zx'], first_sample_xz_m=first, spacing_m=960,
        axes='arrays [z,x]; X east; Z south; metres; cell centres; sea=0', boundary='finite; no wrap',
        requested_domain_bounds_m=plan['extent_bounds_m'], plan_identity=plan['plan_identity'], layers=layers, vectors=vectors,
        hydrology=dict(method='breach-then-lake+convergent-flats', depth_min_m=depth_min_m, area_min_m2=area_min_m2,
                       eps_drop_m=td_hydro.EPS_DROP, river_threshold_m2=300e6, derived_layer='hydro_bed_m',
                       elevation_m_modified=False, flats='Barnes-2014-style towards-outlet + away-from-high gradient, D8 single receiver',
                       area='D8 receiver-tree contributing area (consistent with receiver and river lines)',
                       lake_rule='depression kept as lake only if depth>=depth_min_m AND area>=area_min_m2, or closed basin whose lowest cell is below sea level; others are breached along the flood-parent path'),
        blend=dict(smooth=bool(smooth_blend), near_m=BLEND_NEAR_M, far_m=BLEND_FAR_M, sigma_cells=BLEND_SIGMA_CELLS,
                   rule='same as v2: ocean cells farther than near_m from land low-passed; land and <=near_m unchanged from v1',
                   cells_changed_vs_v1=int(blend_changed.sum())),
        declared_generated=['Same terrain as td-world-960m-v2 (elevation_m bit-identical)',
            'Hydrology bed: priority-flood depressions shallower than D or smaller than A are breached; flats drain convergently (towards outlet, away from high ground) instead of parallel flood-parent lines; terrain elevation_m is NOT eroded or filled',
            'D8 contributing area and single-receiver river lines at 300km2 threshold on the hydrology bed',
            'Lake pixel-edge polygons with holes, one per kept lake id; potential level, no water balance'],
        limitations=['960m D8 receiver direction bias; area is not discharge; no real precipitation-runoff simulation',
            'Breach channels are 1-cell wide cuts in a derived layer; valley widths/depths are not physical',
            'Lake surface is potential flood level of kept depressions, not permanent water. Boundary-crossing basins drain through finite rim',
            'Flat gradient is a routing device, not a terrain modification'],
        statistics=dict(**det_metrics, river_segments=len(rivers), potential_lakes=len(lakes), kept_lakes=len(lakes),
            ocean_cells=int(ocean.sum()), closed_below_sea_cells=int(closed.sum()),
            breach_cells_lowered=res['cells_lowered'], breach_passes=len(res['passes']),
            unresolved_depressions=res['unresolved_depressions'],
            flats=flow.get('flats'),
            elevation_min_m=float(h.min()), elevation_max_m=float(h.max())),
        generation=generation, td_source=td_source,
        files={p.name: file_sha(p) for p in sorted(product.glob('*.npy'))})
    manifest['files']['rivers.json'] = file_sha(product / 'rivers.json')
    manifest['identity'] = identity(manifest)
    write_json(product / 'manifest.json', manifest)
    runtime.update(hydrology_seconds=hydro_seconds, total_seconds=time.perf_counter() - started, breach_passes_detail=res['passes'])
    write_json(product / 'runtime-stats.json', dict(note='run-time fields, deliberately outside manifest/identity', **runtime))
    print('FROZEN-V3 ' + manifest['identity'], flush=True)
    return product, manifest
