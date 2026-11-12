"""Mountain checkpoint + bounded TG glacier regions -> NEW finite world product.

No terrain generation, D8, native inventory debit, or total-runoff claim. All
routing kernels are imported via graph_hydro; elevation_m remains immutable bed.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time

import numpy as np
from scipy import sparse
from scipy.sparse import csgraph

from app import map_source, terrain_source as ts
from app.map_source.adapters import _file
from . import fast_relief as fr, graph_hydro as gh, world_mountain_stage as wm
from .glacier_stage import SCHEMA as GLACIER_SCHEMA, _region, load_state

ALGORITHM = 'dream-mountain-glacier-graph-hydrology-1'
DEFAULTS = {k: fr.DEFAULTS_V3[k] for k in (
    'river_lo_km2', 'river_hi_km2', 'slope_split', 'depth_min_m',
    'lake_area_min_km2', 'breach_passes', 'smooth_rivers', 'lake_min_catch_km2')}
DEFAULTS['mesh_seed'] = None


def _json(path):
    return ts._json(Path(path).read_text(encoding='utf-8'))


def _digest(value):
    # Generic world-map identity excludes BOTH identity and source_path.
    return hashlib.sha256(ts._canon({k: v for k, v in value.items()
                                    if k not in ('identity', 'source_path')}).encode()).hexdigest()


def _drainage():
    # Same read-only import policy as glacier_stage: no TG source bytecode writes.
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        return gh.load_terragenesis()[0]
    finally:
        sys.dont_write_bytecode = previous


def load_checkpoint(path, *, expected_identity=None):
    """Verify the existing mountain checkpoint identity; never regenerate it."""
    root = Path(path)
    doc = _json(root / 'mountains.json')
    if doc.get('schema') != wm.SCHEMA:
        raise ValueError('not a mountain checkpoint')
    with np.load(root / 'mountains.npz', allow_pickle=False) as archive:
        r = {k: archive[k].copy() for k in wm.ARRAY_KEYS}
        first = archive['first_xz_m'].tolist()
        spacing = float(archive['spacing_m'].reshape(-1)[0])
        shape = archive['shape_zx'].tolist()
    r.update(binding=doc['binding'], identity=doc['identity'], metadata=doc)
    if wm.checkpoint_identity(r) != r['identity'] or (expected_identity is not None and expected_identity != r['identity']):
        raise ValueError('checkpoint identity mismatch')
    g = r['binding']['grid']
    bed = r['bed_m']
    if (bed.dtype != np.dtype('float64') or bed.ndim != 2 or min(bed.shape) < 3
            or not np.isfinite(bed).all() or spacing <= 0 or not np.isfinite(spacing)
            or shape != list(bed.shape) or list(g['shape']) != shape
            or first != list(g['first_xz_m']) or spacing != float(g['spacing_m'])
            or len(first) != 2 or not np.isfinite(first).all()):
        raise ValueError('checkpoint bed/grid mismatch')
    for k in ('ocean', 'closed', 'island_support', 'protected_mask'):
        if r[k].dtype != np.dtype(bool) or r[k].shape != bed.shape:
            raise ValueError('checkpoint mask mismatch: ' + k)
    if np.any(r['ocean'] & r['closed']):
        raise ValueError('checkpoint status masks overlap')
    return r


def _source_layers(r, source_product):
    """Optional same-source island protection; NEVER reuse old lakes or rivers."""
    shape = r['bed_m'].shape
    status = np.where(r['ocean'], 3, np.where(r['closed'], 4, 5)).astype(np.uint8)
    extras = {}
    if source_product is not None:
        source = map_source.load_source('world-map-product', source_product,
                         expected_identity=r['binding']['source']['product_identity'])
        info = source.info
        g = r['binding']['grid']
        if (tuple(info.shape_zx) != shape or info.spacing_m != g['spacing_m']
                or list(info.first_sample_xz_m) != list(g['first_xz_m'])
                or info.world_seed != r['binding']['world_seed']):
            raise ValueError('source grid/seed mismatch')
        manifest = _json(Path(source_product) / 'manifest.json')
        spec = manifest['layers']['status']
        status = np.asarray(np.load(_file(source_product, spec['file'], spec['sha256']),
                                    allow_pickle=False)).copy()
        if manifest.get('status_codes'):
            native_status = status
            status = np.full(shape, map_source.UNKNOWN, dtype=np.uint8)
            for old, new in manifest['status_codes'].items():
                status[native_status == int(old)] = new
        if not np.array_equal(status == 3, r['ocean']) or not np.array_equal(status == 4, r['closed']):
            raise ValueError('source/checkpoint status mismatch')
        for name in ('registered_lagoon', 'frozen_island_land_fraction',
                     'frozen_island_lagoon_fraction', 'protected_fraction'):
            spec = manifest['layers'].get(name)
            if spec is not None:
                a = np.load(_file(source_product, spec['file'], spec['sha256']), allow_pickle=False)
                if a.shape != shape or not np.isfinite(a).all():
                    raise ValueError('source island layer shape/values mismatch')
                extras[name] = a.copy()
    # A lagoon is not identified from a negative elevation or a stale lake mask.
    return status, extras


def compose_glaciers(r, glacier_regions, *, boundary_policy='closed-edge-zero'):
    """Compose disjoint explicit half-open [z0,x0,z1,x1] windows, without resampling.

    Returns arrays, provenance, common (start,end) seconds. Default strictly
    requires completed native experiments with exactly zero ice on closed edges.
    'finite' explicitly retains independent finite-window boundary limitations.
    """
    if boundary_policy not in ('closed-edge-zero', 'finite'):
        raise ValueError('unknown glacier boundary policy')
    bed = r['bed_m']; g = r['binding']['grid']; S = float(g['spacing_m'])
    valid = np.zeros(bed.shape, bool)
    h = np.full(bed.shape, np.nan)
    melt = np.full(bed.shape, np.nan)
    records = []; window_time = None
    for region in glacier_regions:
        root = Path(region['path'])
        win = region['window_zx']; sl = _region(win, bed.shape)
        if valid[sl].any():
            raise ValueError('overlapping glacier regions would double-count inventory')
        m, ledger = _json(root/'metadata.json'), _json(root/'ledger.json')
        if m.get('adapter_schema') != GLACIER_SCHEMA:
            raise ValueError('glacier adapter schema mismatch')
        if m.get('terrain_identity') != r['identity']:
            raise ValueError('glacier terrain identity mismatch')
        if m.get('source_identity') != r['binding']['source']['product_identity']:
            raise ValueError('glacier source identity mismatch')
        local_bed = bed[sl]
        first = [g['first_xz_m'][0] + win[1]*S, g['first_xz_m'][1] + win[0]*S]
        if (m.get('shape_zx') != list(local_bed.shape) or m.get('first_xz_m') != first
                or m.get('origin_xz_m') != first or m.get('dx_m') != S or m.get('dz_m') != S):
            raise ValueError('glacier grid mismatch')
        if m.get('completed') is not True or m['completed_years'] != m['target_years']:
            raise ValueError('incomplete glacier experiment')
        start, end = float(m['physical_start_s']), float(m['physical_end_s'])
        elapsed = float(m['elapsed_physical_seconds'])
        if (not np.isfinite([start, end, elapsed]).all() or start != 0 or end < start
                or elapsed != end-start or elapsed != float(m['year_s'])*m['completed_years']
                or ledger['elapsed_physical_seconds'] != elapsed):
            raise ValueError('glacier physical time mismatch')
        if window_time is not None and window_time != (start, end):
            raise ValueError('glacier regions have different physical time windows')
        window_time = (start, end)
        with np.load(root/'arrays.npz', allow_pickle=False) as archive:
            a = {k: archive[k].copy() for k in ('bed_m', 'ice_thickness_m', 'ice_surface_m',
                 'cumulative_melt_water_m3', 'pending_melt_water_m3')}
        if any(v.shape != local_bed.shape or not np.isfinite(v).all() for v in a.values()):
            raise ValueError('glacier arrays shape/nonfinite mismatch')
        if (not np.array_equal(a['bed_m'], local_bed)
                or not np.array_equal(a['ice_surface_m'], local_bed+a['ice_thickness_m'])):
            raise ValueError('glacier bed/surface samples mismatch')
        if (np.any(local_bed <= 0) or np.any(r['ocean'][sl]) or np.any(a['ice_thickness_m'] < 0)
                or np.any(a['cumulative_melt_water_m3'] < 0) or np.any(a['pending_melt_water_m3'] < 0)):
            raise ValueError('invalid glacier land/ice/melt values')
        state = load_state(root/'state.npz')
        for key in ('geometry_identity', 'model_identity', 'forcing_identity'):
            if state[key] != m[key]:
                raise ValueError('native glacier state identity mismatch')
        # Use TG's existing geometry identity, not a parallel geometry hash scheme.
        _drainage()
        from terrain_pipeline.common_infra import identity
        gid = identity({'bed_m': local_bed}, dict(dx_m=S, dz_m=S, origin_xz_m=first,
                       source_identity=m['source_identity'], terrain_identity=m['terrain_identity']))
        if gid != m['geometry_identity']:
            raise ValueError('native glacier geometry identity mismatch')
        if state['physical_time_s'] != elapsed or state['completed_years'] != m['completed_years']:
            raise ValueError('native glacier state time mismatch')
        for key in ('ice_thickness_m', 'pending_melt_water_m3'):
            if not np.array_equal(state[key], a[key]):
                raise ValueError('native glacier inventory mismatch')
        if not np.array_equal(state['melt_water_m3'], a['cumulative_melt_water_m3']):
            raise ValueError('native cumulative melt mismatch')
        if not np.isclose(a['cumulative_melt_water_m3'].sum(), ledger['cumulative_melt_water_m3'], rtol=1e-12, atol=1e-6):
            raise ValueError('native glacier ledger melt mismatch')
        edge = np.r_[a['ice_thickness_m'][0], a['ice_thickness_m'][-1],
                     a['ice_thickness_m'][:, 0], a['ice_thickness_m'][:, -1]]
        if boundary_policy == 'closed-edge-zero' and (m.get('boundary') != 'closed'
                or m.get('edge_ice', {}).get('closed_edge_zero') is not True or np.any(edge != 0)):
            raise ValueError('glacier requires closed-edge-zero; enlarge region or explicitly choose finite policy')
        valid[sl] = True; h[sl] = a['ice_thickness_m']; melt[sl] = a['cumulative_melt_water_m3']
        files = {name: ts._file_sha256(root/name) for name in
                 ('state.npz', 'arrays.npz', 'metadata.json', 'ledger.json')}
        records.append(dict(identity=_digest(files), window_zx=list(win), files=files,
            terrain_identity=m['terrain_identity'], source_identity=m['source_identity'],
            model_identity=m['model_identity'], forcing_identity=m['forcing_identity'],
            geometry_identity=m['geometry_identity'], target_years=m['target_years'],
            completed_years=m['completed_years'], physical_start_s=start, physical_end_s=end,
            elapsed_physical_seconds=elapsed, edge_ice=m['edge_ice'], boundary=m['boundary'],
            elevation_parameters=m['elevation_parameters'], parameters=m['parameters'],
            operational_config=m.get('operational_config'), reused=m.get('tg_producer_sha256'),
            units=m.get('units'), melt_handoff_contract=m.get('melt_handoff_contract'),
            cumulative_melt_water_m3=float(melt[sl].sum())))
    arrays = dict(glacier_simulated_fraction=valid.astype(np.float64), glacier_ice_thickness_m=h,
        glacier_ice_surface_m=np.where(valid, bed+h, np.nan),
        glacier_ice_volume_m3=h*(S*S), glacier_coverage_fraction=np.where(valid, h > 0, np.nan),
        glacier_cumulative_melt_water_m3=melt)
    return arrays, records, window_time


def _surface_lake_fragments(mesh, surface, filled, kept_id, excluded):
    """Keep only original-surface water-bearing subsets of breached-bed lakes.

    Cuts can connect a deep lake through a high ORIGINAL saddle. That saddle is
    still terrain in elevation_m, so it cannot be published as water. Re-label
    connected components using mesh edges, SAME original lake id and SAME flood
    level. Do not raise water to the bed or infer new hydraulic spill outlets.
    """
    shape = np.shape(surface)
    surface = np.asarray(surface).ravel(); filled = np.asarray(filled).ravel()
    old = np.asarray(kept_id).ravel()
    candidate = (old > 0) & ~np.asarray(excluded, bool).ravel()
    wet = candidate & np.isfinite(filled) & (filled - surface > gh.WET_TOL)
    src = np.repeat(np.arange(surface.size, dtype=np.int32), np.diff(mesh.indptr))
    dst = mesh.indices
    edge = (wet[src] & wet[dst] & (old[src] == old[dst])
            & (filled[src] == filled[dst]))
    graph = sparse.coo_matrix((np.ones(int(edge.sum()), np.int8), (src[edge], dst[edge])),
                              shape=(surface.size, surface.size))
    _, component = csgraph.connected_components(graph, directed=False)
    ids = np.zeros(surface.size, np.int32)
    _, inverse = np.unique(component[wet], return_inverse=True)
    ids[wet] = inverse + 1
    parents = np.zeros(int(ids.max(initial=0)) + 1, np.int32)
    parents[ids[wet]] = old[wet]
    return ids.reshape(shape), dict(
        method='mesh-connected same-original-lake same-level subsets; filled-original-routing-surface > WET_TOL',
        removed_above_original_surface_cells=int(np.count_nonzero(candidate & ~wet)),
        original_lakes=int(np.unique(old[candidate]).size), fragments=int(parents.size-1),
        source_lake_by_fragment={str(i): int(parents[i]) for i in range(1, parents.size)},
        outlet_semantics='river shore links on published subsets only; NOT reconstructed original-bed hydraulic spill outlets')


def compute(checkpoint, glacier_regions, *, source_product=None, params=None,
            boundary_policy='closed-edge-zero', log=None):
    """Compute ONLY downstream hydrology. checkpoint is a verified directory."""
    r = load_checkpoint(checkpoint)
    unknown = set(params or {}) - set(DEFAULTS)
    if unknown:
        raise ValueError('unknown hydrology parameters: ' + ','.join(sorted(unknown)))
    p = dict(DEFAULTS, **(params or {}))
    if (type(p['breach_passes']) is not int or not 1 <= p['breach_passes'] <= 4
            or any(not np.isfinite(p[k]) or p[k] < 0 for k in
                   ('river_lo_km2', 'river_hi_km2', 'slope_split', 'depth_min_m',
                    'lake_area_min_km2', 'lake_min_catch_km2'))):
        raise ValueError('invalid hydrology thresholds/passes (maximum 4)')
    status, extras = _source_layers(r, source_product)
    arrays, regions, physical_time = compose_glaciers(r, glacier_regions, boundary_policy=boundary_policy)
    bed = r['bed_m']; g = r['binding']['grid']; S = float(g['spacing_m'])
    first = g['first_xz_m']; shape = bed.shape
    simulated = arrays['glacier_simulated_fraction'] > 0
    ice = simulated & (arrays['glacier_ice_thickness_m'] > 0)
    surface = np.where(simulated, arrays['glacier_ice_surface_m'], bed)
    lagoon = np.asarray(extras.get('registered_lagoon', np.zeros(shape, bool)), bool)
    outlets = r['ocean'] | lagoon
    outlets[[0, -1], :] = True; outlets[:, [0, -1]] = True
    if p['mesh_seed'] is None:
        from .config import derive_subseed
        p['mesh_seed'] = int(derive_subseed(r['binding']['world_seed'], 'fast-relief/mesh'))
    drain = _drainage()
    mesh = gh.build_graph(shape, first, S, p['mesh_seed'])
    hyd = gh.hydrology(surface, r['ocean'], mesh, outlets, float(p['depth_min_m']),
        float(p['lake_area_min_km2'])*1e6, p['breach_passes'], log,
        forbid=ice | lagoon, min_catch_m2=float(p['lake_min_catch_km2'])*1e6)
    lake_id, lake_revalidation = _surface_lake_fragments(
        mesh, surface, hyd['filled'], hyd['lake_id'], r['ocean'] | lagoon | ice)
    threshold = gh.zoned_threshold(surface, S, float(p['river_lo_km2'])*1e6,
                    float(p['river_hi_km2'])*1e6, float(p['slope_split']))
    active = gh.active_rivers(hyd['receiver'], hyd['order'], hyd['area_m2'], r['ocean'] | lagoon, threshold)
    lines = gh.trace_lines(hyd['receiver'], hyd['area_m2'], active, shape, first, S)
    px, pz = np.asarray(mesh.node_x_m), np.asarray(mesh.node_z_m)
    if p['smooth_rivers']:
        px, pz, _ = gh.smooth_centerline(px, pz, hyd['receiver'], active, S)
    rivers, links = gh.cut_lines_at_lakes(lines, px, pz, hyd['area_m2'], shape, r['ocean'], lake_id)
    for line in rivers:
        line['surface_routing'] = 'schematic bed/ice-surface path, NOT subglacial drainage'
    lakes = gh.lake_vectors_labeled(lake_id, hyd['filled'], first, S)
    for lake in lakes:
        lake['meaning'] = ('Original-surface water-bearing connected subset of a kept breached-bed depression; '
                           'potential inherited flood level, NOT a reconstructed spill outlet or balanced lake')
    arrays.update(elevation_m=bed.copy(), status=status, routing_surface_m=surface,
        hydro_bed_m=np.asarray(hyd['bed']).reshape(shape),
        water_surface_m=np.where(lake_id > 0, hyd['filled'], np.nan),
        drainage_area_m2=hyd['area_m2'].reshape(shape),
        receiver=hyd['receiver'].reshape(shape).astype(np.int32), lake_id=lake_id, **extras)
    # Diagnostic transport only: cumulative generated melt ONCE, never pending.
    arrays['glacier_melt_mean_m3_s'] = np.full(shape, np.nan)
    if physical_time is not None and physical_time[1] > physical_time[0]:
        source = np.nan_to_num(arrays['glacier_cumulative_melt_water_m3'], nan=0).ravel()
        volume = drain.accumulate_graph(hyd['receiver'], hyd['order'], source)
        arrays['glacier_melt_mean_m3_s'] = np.asarray(volume).reshape(shape)/(physical_time[1]-physical_time[0])
    return dict(arrays=arrays, rivers=rivers, lakes=lakes, lake_links=links,
        checkpoint=r, regions=regions, physical_time_s=physical_time, parameters=p,
        boundary_policy=boundary_policy, passes=hyd['passes'], lake_revalidation=lake_revalidation,
        unresolved_depressions=hyd['unresolved_depressions'])


def publish(checkpoint, glacier_regions, output, *, source_product=None, params=None,
            boundary_policy='closed-edge-zero', expected_mountain_identity=None, log=None):
    """Publish into a NEW directory; validated ready manifest is written LAST.

    No default catalog, save, TG directory, or checkpoint is modified. Runtime
    timings live outside the identity-bearing manifest. Returns (Path, manifest).
    """
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError('new output directory required')
    if output == gh.terragenesis_root().resolve() or gh.terragenesis_root().resolve() in output.parents:
        raise ValueError('TG workspace is read-only')
    started = time.perf_counter()
    load_checkpoint(checkpoint, expected_identity=expected_mountain_identity)
    result = compute(checkpoint, glacier_regions, source_product=source_product,
                     params=params, boundary_policy=boundary_policy, log=log)
    compute_seconds = time.perf_counter()-started
    r = result['checkpoint']; g = r['binding']['grid']; arrays = result['arrays']
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.world-hydrology-', dir=output.parent))
    try:
        layers = {}
        units = dict(map_source.STANDARD_LAYERS, routing_surface_m='m', hydro_bed_m='m',
                     receiver='1', lake_id='1', glacier_cumulative_melt_water_m3='m3',
                     registered_lagoon='1', frozen_island_land_fraction='1',
                     frozen_island_lagoon_fraction='1', protected_fraction='1')
        meanings = dict(elevation_m='Immutable mountain terrain bed; never ice/water surface or breached routing bed',
            status='Original source classes: 3 ocean, 4 closed below sea, 5 land; not a new lake class',
            routing_surface_m='bed + native ice thickness in simulated regions; bed elsewhere',
            hydro_bed_m='Derived routing surface after geometric breach cuts; NOT terrain bed or ice inventory update',
            water_surface_m='Inherited potential flood level ONLY on original-routing-surface water-bearing connected subsets of kept depressions; NaN dry; not permanent water',
            drainage_area_m2='Irregular graph contributing cell area; NOT discharge',
            receiver='Final irregular-graph flat receiver index; -1 sink', lake_id='Original-surface same-level mesh-connected fragment of a kept depression; 0 dry/excluded',
            glacier_simulated_fraction='1 simulated native region, 0 unmodelled; 0 does NOT mean ice-free',
            glacier_ice_thickness_m='Native TG H; NaN outside simulated regions',
            glacier_ice_surface_m='Immutable bed + native H; NaN outside simulated regions',
            glacier_ice_volume_m3='Native H times cell area, m3 ICE per cell; NaN unmodelled',
            glacier_coverage_fraction='Native H>0 in simulated cells; NaN unmodelled',
            glacier_cumulative_melt_water_m3='Cumulative generated m3 WATER per cell since time zero; pending is the SAME stock, not added; NaN unmodelled',
            glacier_melt_mean_m3_s='Cumulative represented-region generated melt accumulated along FINAL surface receivers / common elapsed SI seconds; diagnostic mean component only, NOT total discharge; no debit or storage transport; zero outside represented upstream contributions, NOT verified zero world runoff')
        for name, a in arrays.items():
            a = np.ascontiguousarray(a)
            np.save(staging/(name+'.npy'), a, allow_pickle=False)
            layers[name] = dict(file=name+'.npy', sha256=ts._file_sha256(staging/(name+'.npy')),
                dtype=str(a.dtype), unit=units[name], meaning=meanings.get(name, 'Same-source frozen island protection layer'), nodata=None)
        (staging/'vectors').mkdir()
        vectors = {}
        for kind, items, key in [('rivers', result['rivers'], 'lines'), ('lakes', result['lakes'], 'lakes')]:
            file = 'vectors/'+kind+'.json'
            fr.write_json(staging/file, dict(schema=kind+'-v1', **{key: items}))
            vectors[kind] = dict(file=file, sha256=ts._file_sha256(staging/file), schema=kind+'-v1')
        files = {v['file']: v['sha256'] for v in [*layers.values(), *vectors.values()]}
        fr.write_json(staging/'glacier-regions.json', dict(regions=result['regions'],
            physical_time_s=result['physical_time_s'], boundary_policy=boundary_policy,
            inventory_accounting='diagnostic only; no pending addition; no native handoff/debit'))
        files['glacier-regions.json'] = ts._file_sha256(staging/'glacier-regions.json')
        manifest = dict(schema='world-map-product-v1', producer='Terragenesis', algorithm_version=ALGORITHM,
            ready=True, source_identity=r['binding']['skeleton_identity'],
            lineage=list(dict.fromkeys([r['binding']['source']['product_identity'],
                    r['identity'], *[v['identity'] for v in result['regions']]])),
            world_seed=int(r['binding']['world_seed']), subseeds={'mesh': str(result['parameters']['mesh_seed'])},
            subseed_method='existing derive_subseed(world_seed, fast-relief/mesh)',
            grid=dict(first_sample_xz_m=list(g['first_xz_m']), spacing_m=float(g['spacing_m']),
                      shape_zx=list(g['shape']), semantics='cell-centre',
                      axes='X east, Z south; arrays [z,x]', length_unit='m', sea_level_m=0),
            boundary='finite; no wrap', layers=layers, vectors=vectors, files=files,
            parameters=result['parameters'], mountain_identity=r['identity'], mountain_binding=r['binding'],
            glacier_regions=result['regions'], physical_time_s=result['physical_time_s'],
            glacier_boundary_policy=boundary_policy,
            same_source_island_protection_loaded=source_product is not None,
            hydrology=dict(method='TG irregular graph breach-then-lake; new shore-cut vectors', no_d8=True,
                passes=result['passes'], unresolved_depressions=result['unresolved_depressions'],
                lake_links={str(k): v for k, v in result['lake_links'].items()},
                lake_surface_revalidation=result['lake_revalidation'],
                melt='diagnostic mean since experiment zero; FINAL surface routing, not historical routing; no debit'),
            declared_generated=['New graph/receivers/lakes/rivers from mountain bed + composed TG ice surface',
                                'Terrain bed preserved exactly; glacier inventory copied, not regenerated'],
            limitations=['NOT Terrain Diffusion output; coarse world grid (10 km in approved world run)',
                'Engineering bed-height ELA and external annual snow, NOT climate or native snow debit',
                'Fixed glacier bed; geometric routing breaches do not alter terrain or ice inventory',
                'Independent finite glacier regions; unmodelled cells are unknown, not ice-free',
                'Potential filled-depression lakes, not balanced or permanent water',
                'Published lakes are only original-surface water-bearing connected subsets; inherited flood levels and shore links do not reconstruct original-bed hydraulic spill outlets',
                'No total runoff/discharge model; represented melt mean is diagnostic only, no storage/delay/debit',
                'River drawings over ice are schematic surface drainage, NOT subglacial hydrology',
                'Final receiver field is applied retrospectively to cumulative melt, not a transient coupled simulation'],
            reused_code=dict(terragenesis_sha256={n: ts._file_sha256(gh.terragenesis_root()/n) for n in gh.TG_FILES},
                local_sha256={n: ts._file_sha256(Path(__file__).with_name(n)) for n in
                              ('graph_hydro.py', 'world_hydrology_stage.py', 'world_mountain_stage.py', 'glacier_stage.py')}))
        manifest['identity'] = _digest(manifest)
        fr.write_json(staging/'runtime-stats.json', dict(compute_seconds=compute_seconds,
                     total_seconds=time.perf_counter()-started, note='runtime only; outside product identity'))
        fr.write_json(staging/'manifest.json', manifest)
        # Canonical adapter owns identity/layer/vector reciprocity/cycle validation.
        map_source.load_source('world-map-product', staging, expected_identity=manifest['identity'])
        for name, digest in files.items():
            _file(staging, name, digest)
        staging.rename(output)
        return output, manifest
    finally:
        if staging.exists():
            shutil.rmtree(staging)
