"""Small genuine TG routing/glacier checks. Never load or run the real world."""
import json

import numpy as np
import pytest

from app import map_source
from app.world_gen import world_hydrology_stage as wh, world_mountain_stage as wm
from app.world_gen import mountain_sculpt as ms
from app.world_gen.glacier_stage import glacier_from_arrays, save_product

PARAMS = dict(river_lo_km2=100, river_hi_km2=100, lake_min_catch_km2=0,
              depth_min_m=1, lake_area_min_km2=0, mesh_seed=42)


def checkpoint(tmp_path, name='mountains', source_identity='a'*64, shape=(11, 17)):
    z, x = np.indices(shape)
    bed = (3350 - x*18 + (z-5)**2*2).astype(np.float64)
    ocean = np.zeros(shape, bool); ocean[:, 0] = True; bed[:, 0] = -20
    closed = np.zeros(shape, bool); closed[-1, -1] = True; bed[-1, -1] = -5
    g = ms.grid_from_index(0, 0, shape[1], shape[0], [5000, -5000], 10000)
    binding = dict(grid=g, world_seed=123, source=dict(product_identity=source_identity),
                   skeleton_identity='b'*64, ridge_identity='c'*64, reference_identity='d'*64,
                   params={}, schema=wm.SCHEMA)
    r = dict(before_m=bed.copy(), bed_m=bed, support=np.zeros(shape, np.float32),
        blend_weight=np.zeros(shape), weight_sum=np.zeros(shape), changed_mask=np.zeros(shape, bool),
        ocean=ocean, closed=closed, protected_mask=ocean|closed, island_support=np.zeros(shape, bool), binding=binding)
    r['identity'] = wm.checkpoint_identity(r)
    r['metadata'] = dict(schema=wm.SCHEMA, identity=r['identity'], binding=binding)
    path = tmp_path/name
    wm.write_checkpoint(path, r)
    return path, r


def glacier(tmp_path, r, name='glacier', win=(2, 3, 9, 10), years=3, **kwargs):
    sl = np.s_[win[0]:win[2], win[1]:win[3]]
    first = [r['binding']['grid']['first_xz_m'][0]+win[1]*10000,
             r['binding']['grid']['first_xz_m'][1]+win[0]*10000]
    opts = dict(spacing_m=10000, first_xz_m=first,
        source_identity=r['binding']['source']['product_identity'], terrain_identity=r['identity'],
        source_kind='synthetic-test', boundary='closed', target_years=years,
        elevation_config=dict(generation_height_m=3240), annual_snow_cap_water_m=1)
    opts.update(kwargs)
    native = glacier_from_arrays(r['bed_m'][sl], **opts)
    path = save_product(native, tmp_path/name)
    return dict(path=path, window_zx=list(win)), native


def test_real_routing_ice_surface_immutable_bed_and_melt_units(tmp_path):
    path, r = checkpoint(tmp_path)
    region, native = glacier(tmp_path, r)
    assert native['arrays']['ice_thickness_m'].max() > 0
    assert native['arrays']['cumulative_melt_water_m3'].sum() > 0
    before_files = {p.name: p.read_bytes() for p in region['path'].iterdir()}
    out = wh.compute(path, [region], params=PARAMS, boundary_policy='finite')
    a = out['arrays']; h = native['arrays']['ice_thickness_m']; sl = np.s_[2:9, 3:10]
    np.testing.assert_array_equal(a['elevation_m'], r['bed_m'])
    np.testing.assert_array_equal(a['routing_surface_m'][sl], r['bed_m'][sl]+h)
    unknown = a['glacier_simulated_fraction'] == 0
    np.testing.assert_array_equal(a['routing_surface_m'][unknown], r['bed_m'][unknown])
    assert np.isnan(a['glacier_ice_thickness_m'][unknown]).all()
    assert np.isnan(a['glacier_coverage_fraction'][unknown]).all()
    np.testing.assert_array_equal(a['glacier_ice_volume_m3'][sl], h*1e8)
    source = np.nan_to_num(a['glacier_cumulative_melt_water_m3'], nan=0).ravel()
    # Independent topological accumulation by following the actual TG receiver.
    expected = np.zeros(source.size); rec = a['receiver'].ravel()
    for i, volume in enumerate(source):
        for _ in range(source.size+1):
            if i < 0:
                break
            expected[i] += volume
            i = int(rec[i])
        else:
            pytest.fail('cycle in native receiver')
    seconds = native['metadata']['elapsed_physical_seconds']
    np.testing.assert_allclose(a['glacier_melt_mean_m3_s'].ravel(), expected/seconds)
    sinks = rec < 0
    assert a['glacier_melt_mean_m3_s'].ravel()[sinks].sum()*seconds == pytest.approx(source.sum())
    assert {p.name: p.read_bytes() for p in region['path'].iterdir()} == before_files
    assert (a['status'] == 3).sum() == r['ocean'].sum()
    assert (a['status'] == 4).sum() == r['closed'].sum()
    assert out['rivers']
    assert all('NOT subglacial' in item['surface_routing'] for item in out['rivers'])


@pytest.mark.parametrize('change, match', [
    (dict(terrain_identity='other'), 'terrain identity'),
    (dict(source_identity='other'), 'source identity'),
    (dict(first_xz_m=[0, 0]), 'grid mismatch'),
    (dict(spacing_m=5000), 'grid mismatch')])
def test_reject_different_source_terrain_grid(tmp_path, change, match):
    path, r = checkpoint(tmp_path)
    region, _ = glacier(tmp_path, r, **change)
    with pytest.raises(ValueError, match=match):
        wh.compute(path, [region], params=PARAMS, boundary_policy='finite')


def test_overlap_incomplete_and_boundary_rejected(tmp_path):
    path, r = checkpoint(tmp_path)
    region, _ = glacier(tmp_path, r)
    with pytest.raises(ValueError, match='closed-edge-zero'):
        wh.compute(path, [region], params=PARAMS)
    with pytest.raises(ValueError, match='overlapping'):
        wh.compute(path, [region, region], params=PARAMS, boundary_policy='finite')
    mpath = region['path']/'metadata.json'; m = json.loads(mpath.read_text())
    m['completed'] = False; mpath.write_text(json.dumps(m), encoding='utf-8')
    with pytest.raises(ValueError, match='incomplete'):
        wh.compute(path, [region], params=PARAMS, boundary_policy='finite')


def test_bed_and_checkpoint_tamper_rejected(tmp_path):
    path, r = checkpoint(tmp_path)
    region, native = glacier(tmp_path, r)
    native['arrays']['bed_m'][2, 2] += 1
    np.savez(region['path']/'arrays.npz', **native['arrays'])
    with pytest.raises(ValueError, match='bed/surface'):
        wh.compute(path, [region], params=PARAMS, boundary_policy='finite')
    with np.load(path/'mountains.npz') as archive:
        fields = {k: archive[k].copy() for k in archive.files}
    fields['bed_m'][2, 2] += 1
    np.savez(path/'mountains.npz', **fields)
    with pytest.raises(ValueError, match='checkpoint identity'):
        wh.load_checkpoint(path)


def test_different_physical_windows_rejected(tmp_path):
    path, r = checkpoint(tmp_path, shape=(13, 21))
    one, _ = glacier(tmp_path, r, name='one', win=(1, 2, 6, 8), years=1)
    two, _ = glacier(tmp_path, r, name='two', win=(7, 10, 12, 17), years=2)
    with pytest.raises(ValueError, match='different physical time'):
        wh.compute(path, [one, two], params=PARAMS, boundary_policy='finite')


def test_publish_roundtrip_atlas_source_and_immutable_output(tmp_path):
    path, r = checkpoint(tmp_path)
    region, _ = glacier(tmp_path, r)
    output, manifest = wh.publish(path, [region], tmp_path/'world', params=PARAMS, boundary_policy='finite')
    assert manifest['schema'] == 'world-map-product-v1' and manifest['ready']
    assert manifest['producer'] == 'Terragenesis'
    src = map_source.load_source('world-map-product', output, expected_identity=manifest['identity'])
    assert 'glacier_simulated_fraction' in src.info.layers
    assert 'glacier_melt_mean_m3_s' in src.info.layers
    assert 'discharge_m3_s' not in src.info.layers
    assert manifest['layers']['glacier_melt_mean_m3_s']['unit'] == 'm3/s'
    assert 'runtime-stats.json' not in manifest['files']
    assert r['identity'] in manifest['lineage']
    from app.world_relief import atlas
    view = atlas.product_from_source(src, output)
    assert view.identity == manifest['identity']
    np.testing.assert_array_equal(view.elevation, r['bed_m'].astype(np.float32))
    assert len(view.rivers) == len(src.vectors('rivers'))
    for file, digest in manifest['files'].items():
        assert wh.ts._file_sha256(output/file) == digest
    # source_path is deliberately excluded by the existing generic identity.
    mpath = output/'manifest.json'; moved = dict(manifest, source_path='portable')
    mpath.write_text(json.dumps(moved), encoding='utf-8')
    map_source.load_source('world-map-product', output)
    with pytest.raises(FileExistsError):
        wh.publish(path, [region], output)
    runtime = json.loads((output/'runtime-stats.json').read_text())
    assert runtime['total_seconds'] >= runtime['compute_seconds'] >= 0


def test_default_zero_edge_zero_elapsed_and_cli(tmp_path):
    path, r = checkpoint(tmp_path)
    region, native = glacier(tmp_path, r, years=0)
    assert native['metadata']['edge_ice']['closed_edge_zero']
    out = wh.compute(path, [region], params=PARAMS)
    assert np.isnan(out['arrays']['glacier_melt_mean_m3_s']).all()
    from tools.publish_mountain_glacier_world import main
    listing = tmp_path/'regions.json'
    listing.write_text(json.dumps([dict(path='glacier', window_zx=region['window_zx'])]), encoding='utf-8')
    pfile = tmp_path/'params.json'; pfile.write_text(json.dumps(PARAMS), encoding='utf-8')
    assert main(['--mountains', str(path), '--glaciers', str(listing), '--params', str(pfile),
                 '--expected-mountain-identity', r['identity'], '--output', str(tmp_path/'cli-world')]) == 0
    map_source.load_source('world-map-product', tmp_path/'cli-world')


def test_same_source_lagoon_protection_no_old_vectors(tmp_path):
    path, r = checkpoint(tmp_path)
    old, old_manifest = wh.publish(path, [], tmp_path/'old', params=PARAMS)
    # Make a valid old source containing unmistakably obsolete lake/river vectors.
    river = dict(id='OLD-RIVER', points_xz_m=[[35000, 15000], [45000, 25000]],
                 downstream_id=None, upstream_ids=[], outlet='closed', drainage_area_m2=1, head_drainage_area_m2=1)
    lake = dict(id='OLD-LAKE', ring_xz_m=[[35000,15000],[45000,15000],[35000,25000],[35000,15000]], surface_m=99999)
    for kind, key, item in [('rivers', 'lines', river), ('lakes', 'lakes', lake)]:
        spec = old_manifest['vectors'][kind]
        wh.fr.write_json(old/spec['file'], dict(schema=kind+'-v1', **{key:[item]}))
        spec['sha256'] = wh.ts._file_sha256(old/spec['file'])
        old_manifest['files'][spec['file']] = spec['sha256']
    lagoon = np.zeros(r['bed_m'].shape, bool); lagoon[3, 4] = True
    np.save(old/'registered_lagoon.npy', lagoon)
    spec = dict(file='registered_lagoon.npy', sha256=wh.ts._file_sha256(old/'registered_lagoon.npy'),
                dtype='bool', unit='1', meaning='synthetic protected lagoon', nodata=None)
    old_manifest['layers']['registered_lagoon'] = spec
    old_manifest['files'][spec['file']] = spec['sha256']
    old_manifest['identity'] = wh._digest(old_manifest)
    wh.fr.write_json(old/'manifest.json', old_manifest)
    newpath, newr = checkpoint(tmp_path, name='new-mountains', source_identity=old_manifest['identity'])
    result = wh.compute(newpath, [], source_product=old, params=PARAMS)
    assert result['arrays']['lake_id'][3,4] == 0
    assert result['arrays']['receiver'][3,4] == -1
    assert all(v['id'] != 'OLD-RIVER' for v in result['rivers'])
    assert all(v['id'] != 'OLD-LAKE' for v in result['lakes'])
    otherpath, _ = checkpoint(tmp_path, name='other-mountains')
    with pytest.raises(map_source.MapSourceError, match='identity'):
        wh.compute(otherpath, [], source_product=old, params=PARAMS)


def test_positive_closed_edge_zero_genuine_glacier(tmp_path):
    _, r = checkpoint(tmp_path, name='template', shape=(41, 41))
    r['bed_m'][:] = 3500
    r['before_m'][:] = 3500
    for name in ('ocean', 'closed', 'protected_mask'):
        r[name][:] = False
    r['identity'] = wm.checkpoint_identity(r)
    r['metadata']['identity'] = r['identity']
    path = tmp_path/'flat-mountains'
    wm.write_checkpoint(path, r)
    mask = np.zeros((41, 41), bool); mask[20, 20] = True
    region, native = glacier(tmp_path, r, win=(0, 0, 41, 41), years=1,
                             source_mask=mask, elevation_config=dict(generation_height_m=3100))
    assert native['arrays']['ice_thickness_m'].max() > 0
    assert native['metadata']['edge_ice']['closed_edge_zero']
    result = wh.compute(path, [region], params=PARAMS)
    assert result['arrays']['glacier_simulated_fraction'].min() == 1
    assert result['arrays']['routing_surface_m'][20,20] > 3500


def _chain_mesh(shape, first=(0, 0), spacing=10000):
    """Explicit tiny native graph for deterministic saddle/cut regression."""
    drain = wh._drainage()
    n = int(np.prod(shape))
    indices = []; indptr = [0]
    for i in range(n):
        indices.extend(j for j in (i-1, i+1) if 0 <= j < n)
        indptr.append(len(indices))
    z, x = np.indices(shape)
    return drain.IrregularMesh(shape=shape, origin_native_xz=(0, 0), spacing_m=spacing,
        world_seed=42, node_x_m=(first[0]+x.ravel()*spacing).astype(float),
        node_z_m=(first[1]+z.ravel()*spacing).astype(float),
        indptr=np.asarray(indptr, np.int64), indices=np.asarray(indices, np.int64),
        edge_length_m=np.full(len(indices), spacing))


def _inside_ring(point, ring):
    x, z = point
    inside = False
    for a, b in zip(ring, ring[1:]):
        if (a[1] > z) != (b[1] > z):
            crossing = a[0] + (z-a[1])*(b[0]-a[0])/(b[1]-a[1])
            if x < crossing:
                inside = not inside
    return inside


def test_breach_high_original_saddle_not_published_as_lake(tmp_path, monkeypatch):
    _, r = checkpoint(tmp_path, name='template', shape=(3, 7))
    r['bed_m'][:] = 200
    r['bed_m'][1] = [200, 100, 105, 10, 103, 0, 0]
    r['before_m'][:] = r['bed_m']
    for name in ('ocean', 'closed', 'protected_mask'):
        r[name][:] = False
    r['ocean'][1, 5:] = True
    r['identity'] = wm.checkpoint_identity(r)
    r['metadata']['identity'] = r['identity']
    path = tmp_path/'saddle-mountains'; wm.write_checkpoint(path, r)
    g = r['binding']['grid']
    mesh = _chain_mesh(r['bed_m'].shape, g['first_xz_m'])
    outlets = r['ocean'].copy(); outlets[[0,-1]] = True; outlets[:,[0,-1]] = True
    raw = wh.gh.hydrology(r['bed_m'], r['ocean'], mesh, outlets, 20, 0)
    # Genuine TG routing lowers 105 saddle for the shallow 100 pit, and then
    # retains it in the deep depression at 103. It is NOT water on actual bed.
    assert raw['bed'][1,2] < 100
    assert raw['filled'][1,2] == 103
    assert raw['lake_id'][1,2] > 0
    assert r['bed_m'][1,2] > raw['filled'][1,2]
    monkeypatch.setattr(wh.gh, 'build_graph', lambda *args: mesh)
    params = dict(PARAMS, depth_min_m=20, smooth_rivers=False)
    output, manifest = wh.publish(path, [], tmp_path/'saddle-world', params=params)
    a = {k: np.load(output/(k+'.npy')) for k in
         ('elevation_m', 'routing_surface_m', 'water_surface_m', 'lake_id', 'hydro_bed_m')}
    np.testing.assert_array_equal(a['elevation_m'], r['bed_m'])
    assert a['hydro_bed_m'][1,2] < a['elevation_m'][1,2]
    assert a['lake_id'][1,2] == 0 and np.isnan(a['water_surface_m'][1,2])
    assert a['lake_id'][1,1] > 0 and a['lake_id'][1,3] > 0
    assert a['lake_id'][1,1] != a['lake_id'][1,3]
    wet = np.isfinite(a['water_surface_m'])
    assert np.all(a['water_surface_m'][wet] > a['routing_surface_m'][wet])
    src = map_source.load_source('world-map-product', output)
    # Rasterize every published polygon at every native cell centre. The high
    # saddle must be in neither polygon, not merely hidden in the scalar layer.
    covered = np.zeros(r['bed_m'].shape, bool)
    for lake in src.vectors('lakes'):
        assert lake['surface_range_m'] == [103,103]
        for z, x in np.ndindex(covered.shape):
            point = [g['first_xz_m'][0]+x*10000, g['first_xz_m'][1]+z*10000]
            contains = _inside_ring(point, lake['ring_xz_m']) and not any(
                _inside_ring(point, hole) for hole in lake.get('holes_xz_m', []))
            if contains:
                assert r['bed_m'][z,x] < lake['surface_m']
                covered[z,x] = True
    np.testing.assert_array_equal(covered, wet)
    assert not covered[1,2]
    assert len(src.vectors('lakes')) == 2
    published_ids = set(int(v) for v in np.unique(a['lake_id']) if v > 0)
    for river in src.vectors('rivers'):
        for key in ('from_lake', 'to_lake'):
            assert river[key] is None or river[key] in published_ids
    stats = manifest['hydrology']['lake_surface_revalidation']
    assert stats['removed_above_original_surface_cells'] == 1
    assert stats['original_lakes'] == 1 and stats['fragments'] == 2


def test_lake_fragments_respect_graph_parent_level_and_exclusion():
    # Adjacent grid cells are not enough; only the provided mesh connects them.
    mesh = _chain_mesh((1, 7))
    surface = np.zeros((1,7))
    filled = np.array([[10,10,20,20,20,20,20.]])
    parent = np.array([[1,1,1,2,2,2,2]])
    excluded = np.zeros((1,7), bool); excluded[0,5] = True
    labels, stats = wh._surface_lake_fragments(mesh, surface, filled, parent, excluded)
    assert labels.tolist() == [[1,1,2,3,3,0,4]]
    assert stats['source_lake_by_fragment'] == {'1':1, '2':1, '3':2, '4':2}
