"""td-world-960m-v5: v4 terrain/hydrology plus explicit through-lake river connections.

Differences to v4 (derived layers only; ``elevation_m`` and the ocean/land mask are never touched):

* River vectors: inside a kept lake the D8 receiver path is only a routing product on a flat potential surface (it runs in
  45 degree diagonals and straight orthogonal lines, and many of them side by side). Every maximal run of >= 2 consecutive
  river points that lie in a kept lake (``lake_id > 0``) is replaced in ``vectors/rivers.json`` by one straight connection
  from the lake-entry point to the lake-exit point, and the line is flagged ``through_lake``. Line ids, areas, upstream /
  downstream topology and ``outlet`` are unchanged. The raw ``rivers.json`` (receiver trace) is written as in v4.
* ``td_flats.route_flats(meander=dict(..., boost=...))`` (optional, default off): stronger step-cost modulation on large flat
  blocks that touch the near-coast zone. Receivers/areas are identical to v4 when ``boost`` is None.
"""
from __future__ import annotations
import functools
import json
from pathlib import Path
import time
import numpy as np
from .td_pages import file_sha, write_json
from .source import identity, subseed
from .td_freeze import assemble, standard_rivers
from .td_freeze_v2 import (smooth_offshore_blend, DEPTH_MIN_M, AREA_MIN_M2, BLEND_NEAR_M, BLEND_FAR_M, BLEND_SIGMA_CELLS,
                           RUNTIME_KEYS)
from .td_freeze_v4 import (zoned_threshold, active_rivers, river_lines_from_active, RIVER_LO_M2, RIVER_HI_M2, SLOPE_SPLIT,
                           SLOPE_SMOOTH_CELLS)
from . import drainage, td_hydro, td_flats

SCHEMA = 'td-world-960m-v5'
BOOST_DEFAULT = None     # set per run; None = v4 flat routing


def through_lake_lines(lines, lake_id, first, spacing):
    """Return (new_lines, stats). ``lines`` = ``standard_rivers`` output; ``lake_id`` = int array [z, x] (0 = no kept lake)."""
    nz, nx = lake_id.shape
    out = []; n_through = 0; n_whole = 0; pts_before = 0; pts_after = 0
    for line in lines:
        c = np.asarray(line['points_xz_m'], np.float64)
        ix = np.clip(np.rint((c[:, 0] - first[0]) / spacing).astype(int), 0, nx - 1)
        iz = np.clip(np.rint((c[:, 1] - first[1]) / spacing).astype(int), 0, nz - 1)
        wet = lake_id[iz, ix] > 0
        item = dict(line)
        pts_before += len(c)
        if not wet.any():
            item.update(through_lake=False, lake_spans=[])
            out.append(item); pts_after += len(c)
            continue
        keep = np.ones(len(c), bool)
        runs = []; i = 0; n = len(c)
        while i < n:
            if wet[i]:
                j = i
                while j + 1 < n and wet[j + 1]:
                    j += 1
                if j > i:
                    runs.append((i, j)); keep[i + 1:j] = False
                i = j + 1
            else:
                i += 1
        new_pts = c[keep]
        # span indices into the NEW point list: the chord edge between the kept run ends
        new_index = np.cumsum(keep) - 1
        spans = [[int(new_index[a]), int(new_index[b])] for a, b in runs]
        item['points_xz_m'] = [[float(x), float(z)] for x, z in new_pts]
        item['through_lake'] = bool(runs)
        item['lake_spans'] = spans
        item['wholly_in_lake'] = bool(wet.all())
        item['lake_ids'] = sorted({int(v) for v in lake_id[iz, ix][wet]})
        if runs:
            n_through += 1
        if wet.all():
            n_whole += 1
        pts_after += len(new_pts)
        out.append(item)
    return out, dict(lines=len(lines), through_lake_lines=n_through, wholly_in_lake_lines=n_whole,
                     points_before=pts_before, points_after=pts_after)


def freeze_v5(directory, out_name='world-960m-v5', depth_min_m=DEPTH_MIN_M, area_min_m2=AREA_MIN_M2, smooth_blend=True,
              boost=None):
    directory = Path(directory); started = time.perf_counter()
    h1, plan, metrics, skeleton, weight, td = assemble(directory, return_td=True)
    if smooth_blend:
        h, blend_changed = smooth_offshore_blend(h1, skeleton, td, weight)
    else:
        h, blend_changed = h1, np.zeros(h1.shape, bool)
    product = Path(out_name) if Path(out_name).is_absolute() else directory / out_name
    product.mkdir(parents=True, exist_ok=True)
    ocean = drainage.ocean_mask(h); closed = (h < 0) & ~ocean
    first = plan['first_sample_xz_m']
    meander = dict(world_seed=int(plan['world_seed']), first_xz=(first[0], first[1]))
    if boost:
        meander['boost'] = dict(boost)
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
    lake_id = np.where(wet, res['lake_id'], 0).astype(np.int32)
    rivers0 = standard_rivers(raw_lines, ocean, closed, wet, first, 960)
    rivers, tl_stats = through_lake_lines(rivers0, lake_id, first, 960)
    lakes = td_hydro.lake_vectors_labeled(np.where(wet, res['lake_id'], 0), filled, first, 960)
    arrays = dict(elevation_m=h, hydro_bed_m=bed, status=status, ocean_mask=ocean, inland_depression_mask=closed,
                  lake_id=lake_id, lake_surface_m=filled, water_surface_m=water,
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
                  'td_freeze_v5.py', 'td_hydro.py', 'td_flats.py', 'drainage.py', 'source.py')
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
        hydrology=dict(method='breach-then-lake+meandering-convergent-flats+through-lake-connections', depth_min_m=depth_min_m,
                       area_min_m2=area_min_m2, eps_drop_m=td_hydro.EPS_DROP, derived_layer='hydro_bed_m',
                       river_threshold=dict(rule='slope-zoned: area >= lo where 5x5 box-smoothed |grad elevation_m| >= split, else hi; plus downstream closure',
                                            lo_m2=RIVER_LO_M2, hi_m2=RIVER_HI_M2, slope_split=SLOPE_SPLIT, smooth_cells=SLOPE_SMOOTH_CELLS),
                       meander=dict(amp=td_flats.MEANDER_AMP, ortho_step_cost=td_flats.MEANDER_ORTHO_COST,
                                    away_weight=td_flats.MEANDER_AWAY_WEIGHT,
                                    octaves_wavelength_m_weight=[list(o) for o in td_flats.MEANDER_OCTAVES],
                                    purpose_names=sorted(meander_subseeds), coastal_flat_boost=(dict(boost) if boost else None)),
                       through_lake=dict(rule='every maximal run of >=2 consecutive river points with lake_id>0 is replaced in vectors/rivers.json by one straight chord from the entry to the exit point; the line gets through_lake=true, lake_spans (point-index pairs of the chord edges), wholly_in_lake, lake_ids; ids/areas/topology unchanged; raw rivers.json (receiver trace) is not modified',
                                         **tl_stats),
                       elevation_m_modified=False,
                       flats='Barnes-2014-style towards-outlet + away-from-high gradient where the in-flat step cost is modulated by smooth coordinate noise (Dijkstra distance), D8 single receiver',
                       area='D8 receiver-tree contributing area (consistent with receiver and river lines)',
                       lake_rule='depression kept as lake only if depth>=depth_min_m AND area>=area_min_m2, or closed basin whose lowest cell is below sea level; others are breached along the flood-parent path'),
        blend=dict(smooth=bool(smooth_blend), near_m=BLEND_NEAR_M, far_m=BLEND_FAR_M, sigma_cells=BLEND_SIGMA_CELLS,
                   rule='same as v2: ocean cells farther than near_m from land low-passed; land and <=near_m unchanged from v1',
                   cells_changed_vs_v1=int(blend_changed.sum())),
        declared_generated=['Same terrain as td-world-960m-v4, v3 and v2 (elevation_m bit-identical)',
            'Hydrology bed: priority-flood depressions shallower than D or smaller than A are breached; flats drain convergently with a small deterministic smooth perturbation so open-plain channels bend; terrain elevation_m is NOT eroded or filled',
            'D8 contributing area and single-receiver river lines with slope-zoned threshold (100 km2 steep / 300 km2 plains) plus downstream closure',
            'River vectors: lake interiors are a single straight through-lake connection per line run (flagged through_lake), not a physical channel',
            'Lake pixel-edge polygons with holes, one per kept lake id; potential level, no water balance'],
        limitations=['960m D8 receiver direction bias; area is not discharge; no real precipitation-runoff simulation',
            'Breach channels are 1-cell wide cuts in a derived layer; valley widths/depths are not physical',
            'Lake surface is potential flood level of kept depressions, not permanent water. Boundary-crossing basins drain through finite rim',
            'Flat gradient and meander noise are routing devices, not terrain modifications; bends are noise-driven, not physical meander dynamics',
            'through_lake chords are display/topology connections between lake entry and exit points; receiver.npy and drainage_area_m2.npy still follow the flat routing path inside lakes'],
        statistics=dict(**det_metrics, river_segments=len(rivers), potential_lakes=len(lakes), kept_lakes=len(lakes),
            ocean_cells=int(ocean.sum()), closed_below_sea_cells=int(closed.sum()),
            breach_cells_lowered=res['cells_lowered'], breach_passes=len(res['passes']),
            unresolved_depressions=res['unresolved_depressions'],
            flats=flow.get('flats'), river_cells=int(active.sum()), through_lake=tl_stats,
            elevation_min_m=float(h.min()), elevation_max_m=float(h.max())),
        generation=generation, td_source=td_source,
        files={p.name: file_sha(p) for p in sorted(product.glob('*.npy'))})
    manifest['files']['rivers.json'] = file_sha(product / 'rivers.json')
    manifest['identity'] = identity(manifest)
    write_json(product / 'manifest.json', manifest)
    runtime.update(hydrology_seconds=hydro_seconds, total_seconds=time.perf_counter() - started, breach_passes_detail=res['passes'])
    write_json(product / 'runtime-stats.json', dict(note='run-time fields, deliberately outside manifest/identity', **runtime))
    print('FROZEN-V5 ' + manifest['identity'], flush=True)
    return product, manifest
