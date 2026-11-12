"""Small synthetic CPU integration; no real world generation or model loading."""
from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pytest

from app.world_gen import mountain_sculpt as ms
from app.world_gen import world_mountain_stage as wm

SEED = 20260903


def fixture_world():
    shape = (48, 64)
    S = 20000.0
    grid = ms.grid_from_index(0, 0, shape[1], shape[0], (S/2, S/2), S)
    lines = [np.array([[210000., 350000.], [570000., 390000.], [1040000., 430000.]]),
             np.array([[230000., 520000.], [680000., 480000.], [1060000., 530000.]])]
    net = dict(line_offsets=np.array([0, 3, 6]), vertex_xz_m=np.concatenate(lines),
               vertex_width_wide_m=np.full(6, 90000.), vertex_width_steep_m=np.full(6, 60000.),
               vertex_amp=np.array([.6, .9, .7, .7, .85, .6]), vertex_side=np.ones(6, np.int8),
               line_level=np.ones(2, np.int8), line_parent=np.full(2, -1), line_belt=np.arange(2),
               line_chain=np.arange(2), pass_xz_m=np.empty((0, 2)),
               pass_depth=np.empty(0), pass_line=np.empty(0, np.int32),
               belt_offsets=np.array([0, 3, 6]), belt_xz_m=np.concatenate(lines),
               belt_half_width_m=np.full(6, 180000.))
    z, x = np.indices(shape)
    before = (3000. + 300*np.sin(x*.14) + 100*np.cos(z*.16)).astype(np.float64)
    status = np.full(shape, 5, np.uint8)
    status[:, :5] = 3
    before[:, :5] = -600.
    # Small island in ocean, entirely coastal: must not become a giant mountain.
    status[15:18, 1:4] = 5
    before[15:18, 1:4] = 200.
    status[25:27, 35:37] = 4
    before[25:27, 35:37] = -80.
    # Old positive lake: status/old water surfaces are deliberately not an exclusion.
    status[22:25, 25:28] = 1
    island_support = np.zeros(shape, bool)
    island_support[15:18, 1:4] = True
    source = dict(product_identity='source-A', source_identity='skeleton-A', world_seed=SEED,
                  shape_zx=list(shape), spacing_m=S, first_sample_xz_m=list(grid['first_xz_m']))
    skeleton = dict(identity='skeleton-A', world_seed=SEED)
    params = dict(halo_cells=2, edge_taper_km=40., coast_guard_cells=2, basins_max=1,
                  vertex_step_km=20., erosion_iterations=1)
    return dict(before_m=before, status=status, grid=grid, net=net, source=source,
                skeleton=skeleton, world_seed=SEED, params=params, island_support=island_support)


def run(f=None, **kw):
    args = fixture_world() if f is None else f
    return wm.apply_world_mountains(**args, **dict(erosion=False, **kw))


def test_deterministic_belt_sorting_immutable_and_overlap():
    f = fixture_world()
    saved = f['before_m'].copy()
    a = run(f, belts=[0, 1])
    b = run(f, belts=[1, 0])
    c = run(f, belts=[0, 1])
    assert a['identity'] == b['identity'] == c['identity']
    np.testing.assert_array_equal(a['bed_m'], b['bed_m'])
    np.testing.assert_array_equal(f['before_m'], saved)
    assert a['metadata']['stats']['overlap_cells'] > 0
    # Directly reconstruct the claimed once-only composition from independent runs.
    r0, r1 = run(f, belts=[0]), run(f, belts=[1])
    expected = saved + ((r0['bed_m']-saved)+(r1['bed_m']-saved))/np.maximum(1, r0['weight_sum']+r1['weight_sum'])
    np.testing.assert_array_equal(a['bed_m'], expected)


def test_complete_belt_crosses_output_cuts_without_internal_seam():
    r = run()
    left = wm.extract_checkpoint(r, 0, 0, 32, 48)
    right = wm.extract_checkpoint(r, 32, 0, 32, 48)
    joined = np.concatenate([left['bed_m'], right['bed_m']], axis=1)
    np.testing.assert_array_equal(joined, r['bed_m'])
    overlap_a = wm.extract_checkpoint(r, 15, 10, 25, 25)
    overlap_b = wm.extract_checkpoint(r, 30, 10, 20, 25)
    np.testing.assert_array_equal(overlap_a['bed_m'][:, 15:], overlap_b['bed_m'][:, :10])
    assert r['changed_mask'][10:-10, 31:33].any(), 'cut must actually cross sculpted mountain support'
    # Reject pretending a cropped source is the same complete calibrated world.
    f = fixture_world()
    f['grid'] = ms.grid_from_index(0, 0, 32, 48, (10000., 10000.), 20000.)
    f['before_m'] = f['before_m'][:, :32]
    f['status'] = f['status'][:, :32]
    with pytest.raises(ValueError, match='complete bound source'):
        run(f)


def test_coast_islands_closed_negative_and_old_lake_policy():
    f = fixture_world()
    r = run(f)
    np.testing.assert_array_equal(r['bed_m'][r['protected_mask']], f['before_m'][r['protected_mask']])
    np.testing.assert_array_equal(r['bed_m'][15:18, 1:4], f['before_m'][15:18, 1:4])
    np.testing.assert_array_equal(r['bed_m'][:, 5], f['before_m'][:, 5])
    assert r['changed_mask'][22:25, 25:28].any(), 'old lake beds must be available to sculpt'
    assert not r['protected_mask'][22:25, 25:28].any()
    np.testing.assert_array_equal(r['bed_m'][0], f['before_m'][0])


def test_periodic_unwrapped_images_keep_segments_and_no_false_bridge():
    f = fixture_world()
    net = f['net']
    # One belt crossing the right periodic boundary; image appears at both finite edges.
    net['vertex_xz_m'][:3] = [[1180000., 350000.], [1280000., 390000.], [1380000., 430000.]]
    net['belt_xz_m'][:3] = net['vertex_xz_m'][:3]
    st = wm.finite_structure(net, 0, f['grid'], world_seed=SEED,
                             params=ms._params(dict(f['params'], structure_policy='mountain-group')))
    images = {tuple(e['periodic_image']) for e in st['main']}
    assert (0, 0) in images and (-1, 0) in images
    for ent in st['main']:
        assert np.max(np.linalg.norm(np.diff(ent['xz_m'], axis=0), axis=1)) < 200000
    parts = st['meta']['belt_geometry']['parts']
    assert len(parts) >= 2
    r = run(f, belts=[0])
    assert r['support'][20, 8] > 0 and r['support'][20, 60] > 0
    assert r['support'][20, 32] == 0, 'periodic pieces must not draw a bridge through the middle'


def test_segment_intersection_with_both_endpoints_outside_is_retained():
    images = list(wm._images([[-100., 50.], [1100., 50.]], [0., 0., 1000., 100.], [1000., 100.], 0.))
    assert any(k == [0, 0] for _, k in images)
    np.testing.assert_array_equal([p for p, k in images if k == [0, 0]][0], [[-100., 50.], [1100., 50.]])


def test_periodic_child_alignment_precedes_free_tip_taper():
    f = fixture_world()
    n = f['net']
    # Put one child in the next periodic chart, with its first endpoint at the parent.
    n['line_belt'][1] = 0
    n['line_level'][1] = 2
    n['line_parent'][1] = 0
    n['vertex_xz_m'][3:] = [[570000.+1280000., 390000.],
                              [590000.+1280000., 490000.], [610000.+1280000., 590000.]]
    saved = n['vertex_xz_m'].copy()
    p = ms._params(dict(f['params'], structure_policy='mountain-group'))
    st = wm.finite_structure(n, 0, f['grid'], world_seed=SEED, params=p)
    branch = next(e for e in st['branches'] if e['periodic_image'] == [0, 0])
    assert branch['parent'] == 0
    np.testing.assert_array_equal(branch['xz_m'][0], [570000., 390000.])
    # First endpoint is the junction, not an incorrectly attenuated free tip.
    assert branch['amp'][0] > branch['amp'][-1]
    np.testing.assert_array_equal(n['vertex_xz_m'], saved)


def test_identity_binds_source_reference_params_and_arrays(tmp_path):
    f = fixture_world()
    r = run(f)
    f['source'] = dict(f['source'], product_identity='source-B')
    other = run(f)
    assert other['identity'] != r['identity']
    other = run(reference_identity='different-reference')
    assert other['identity'] != r['identity']
    fp = fixture_world()
    fp['params']['group_body_amp_m'] = 400.
    assert run(fp)['identity'] != r['identity']
    r['bed_m'][20, 30] += 1
    with pytest.raises(ValueError, match='identity mismatch'):
        wm.write_checkpoint(tmp_path / 'bad', r)
    f['skeleton'] = dict(identity='wrong', world_seed=SEED)
    with pytest.raises(ValueError, match='identity mismatch'):
        run(f)


def test_checkpoint_schema_no_stale_hydrology_and_no_overwrite(tmp_path):
    r = run()
    written = wm.write_checkpoint(tmp_path / 'checkpoint', r)
    doc = json.loads((tmp_path / 'checkpoint/mountains.json').read_text(encoding='utf8'))
    assert doc['schema'] == wm.SCHEMA
    assert doc['identity'] == written['identity']
    assert doc['product_complete'] is False
    assert doc['hydrology']['computed'] is False
    assert doc['hydrology']['old_lakes_protected'] is False
    with np.load(tmp_path / 'checkpoint/mountains.npz', allow_pickle=False) as a:
        assert set(a.files) == set(wm.ARRAY_KEYS) | {'first_xz_m', 'spacing_m', 'shape_zx'}
        assert not {'rivers', 'water_surface_m', 'status'} & set(a.files)
        replay = dict(binding=doc['binding'], **{k: a[k] for k in wm.ARRAY_KEYS})
        assert wm.checkpoint_identity(replay) == doc['identity']
    assert not (tmp_path / 'checkpoint/manifest.json').exists()
    with pytest.raises(ValueError, match='already exists'):
        wm.write_checkpoint(tmp_path / 'checkpoint', r)


def test_real_small_graph_erosion_reuses_immutable_bed():
    pytest.importorskip('numba')
    f = fixture_world()
    r = wm.apply_world_mountains(**f, erosion=True)
    other = wm.apply_world_mountains(**f, erosion=True, belts=[1, 0])
    np.testing.assert_array_equal(r['bed_m'], other['bed_m'])
    assert all(b['erosion']['applied'] for b in r['metadata']['belts'])
    assert not r['metadata']['hydrology']['computed']


def test_run_stage_binding_and_cli_synthetic_integration(tmp_path, monkeypatch):
    from tools import apply_world_mountains as cli
    f = fixture_world()
    reference = tmp_path / 'reference'
    reference.mkdir()
    doc = dict(identity=wm.APPROVED_REFERENCE, schema=ms.SCHEMA_G,
               meta=dict(structure_policy='mountain-group', params=f['params'], source=f['source']))
    (reference / 'structure.json').write_text(json.dumps(doc), encoding='utf8')
    source = f['source']
    info = SimpleNamespace(identity=source['product_identity'], schema='synthetic', producer='test',
        world_seed=SEED, algorithm_version='test', spacing_m=source['spacing_m'],
        first_sample_xz_m=source['first_sample_xz_m'], shape_zx=source['shape_zx'])
    def load(product, expected):
        assert expected == 'source-A'
        product = tmp_path / 'synthetic-product'
        product.mkdir(exist_ok=True)
        np.save(product / 'island.npy', f['island_support'].astype(np.float32))
        # Real TG semantics: exposed land fraction includes the entire continent,
        # whereas protected fraction only covers the frozen feature envelope.
        np.save(product / 'land.npy', (f['before_m'] > 0).astype(np.float32))
        layers = dict(protected_fraction=dict(file='island.npy', sha256=ms.fr.file_sha(product / 'island.npy')),
                      frozen_island_land_fraction=dict(file='land.npy', sha256=ms.fr.file_sha(product / 'land.npy')))
        return dict(source_identity='skeleton-A', layers=layers), dict(elevation_m=f['before_m'], status=f['status']), info
    monkeypatch.setattr(ms, 'load_product', load)
    monkeypatch.setattr(wm.rn, 'load_network', lambda path: (f['net'], f['skeleton']))
    out = tmp_path / 'cli-checkpoint'
    assert cli.main(['--product', str(tmp_path / 'synthetic-product'), '--skeleton', 'synthetic', '--out', str(out),
                     '--expected-identity', 'source-A', '--reference', str(reference), '--no-erosion']) == 0
    assert (out / 'mountains.json').exists()
    with np.load(out / 'mountains.npz') as arrays:
        np.testing.assert_array_equal(arrays['island_support'], f['island_support'])
        np.testing.assert_array_equal(arrays['bed_m'][f['island_support']], f['before_m'][f['island_support']])
        assert np.count_nonzero(arrays['changed_mask'][10:-10, 10:-10]) > 500
        assert not arrays['protected_mask'][22:25, 25:28].any(), 'continent must not be locked by land fraction'
    policy = json.loads((out / 'mountains.json').read_text(encoding='utf8'))['island_support_policy']
    assert policy['ignored_layers'] == ['frozen_island_land_fraction']
    doc['identity'] = 'wrong'
    (reference / 'structure.json').write_text(json.dumps(doc), encoding='utf8')
    with pytest.raises(ValueError, match='reference identity'):
        wm.run_stage('synthetic', 'synthetic', tmp_path / 'refused', expected_identity='source-A', reference=reference)


def test_feature_support_rectangles_lagoons_and_layer_checks(tmp_path):
    f = fixture_world()
    info = SimpleNamespace(shape_zx=f['before_m'].shape, spacing_m=20000.,
                           first_sample_xz_m=(10000., 10000.))
    land = (f['before_m'] > 0).astype(np.float32)
    protected = f['island_support'].astype(np.float32)
    lagoon = np.zeros(land.shape, np.float32)
    lagoon[12, 8] = .125
    registered = np.zeros(land.shape, bool)
    registered[12, 10] = True
    layers = {}
    for key, value in [('frozen_island_land_fraction', land), ('protected_fraction', protected),
                       ('frozen_island_lagoon_fraction', lagoon), ('registered_lagoon', registered)]:
        path = tmp_path / (key+'.npy')
        np.save(path, value)
        layers[key] = dict(file=path.name, sha256=ms.fr.file_sha(path))
    # Published TG support-cell rectangles preserve an unsampled feature fringe.
    # They are small feature bounds, not an inference from all exposed land.
    sampling = dict(shape_zx=list(land.shape), spacing_m=20000.,
                    bounds_m=list(f['grid']['rect_m']),
                    feature_support_cells=[dict(feature_id='small-island', support_cells_zx=[14, 0, 19, 5]),
                                           dict(feature_id='outside', support_cells_zx=None)])
    manifest = dict(layers=layers, ocean_islands=dict(area_sampling=sampling))
    support, policy = wm.load_island_support(tmp_path, manifest, info)
    assert support[14:19, :5].all()
    assert support[12, 8] and support[12, 10]
    assert not support[20:40, 20:50].any(), 'continental land_fraction=1 must not protect the continent'
    assert policy['protected_cells'] == 27
    assert policy['feature_support_rectangles'] == 2
    r = wm.apply_world_mountains(**dict(f, island_support=support), erosion=False)
    np.testing.assert_array_equal(r['bed_m'][support], f['before_m'][support])
    assert r['changed_mask'][20:40, 20:50].sum() > 200
    # The main agent's byte validation must still reject a modified support layer.
    np.save(tmp_path / 'protected_fraction.npy', protected+1)
    with pytest.raises(ValueError, match='hash mismatch: protected_fraction'):
        wm.load_island_support(tmp_path, manifest, info)


def test_feature_support_metadata_grid_must_match(tmp_path):
    f = fixture_world()
    info = SimpleNamespace(shape_zx=f['before_m'].shape, spacing_m=20000.,
                           first_sample_xz_m=(10000., 10000.))
    manifest = dict(ocean_islands=dict(area_sampling=dict(shape_zx=[1, 1], spacing_m=20000.,
        feature_support_cells=[dict(feature_id='wrong-grid', support_cells_zx=[0, 0, 1, 1])])))
    with pytest.raises(ValueError, match='metadata grid mismatch'):
        wm.load_island_support(tmp_path, manifest, info)
