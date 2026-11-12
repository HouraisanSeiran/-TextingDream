"""Small causal API/source tests only: never solve the 800k-cell real world."""
import hashlib
import json

import numpy as np
import pytest

from app import terrain_source as ts
from app.world_gen import climate_world_stage as stage


def source(n=8):
    ocean = np.zeros((n, n), bool)
    ocean[:, :n//2] = True
    bed = np.where(ocean, -100., 100.+np.arange(n)[None]*70.).astype(np.float64)
    rec = (np.arange(n*n)-1).reshape(n, n).astype(np.int32)
    return dict(elevation_m=bed, ocean_mask=ocean, receiver=rec,
        order=stage.topological_order(rec), first_xz_m=[-35000., -35000.],
        spacing_m=10000., world_seed=20260903, source_identity='a'*64)


def reference():
    return dict(schema='terragenesis-climate-reference-v1', latitude_deg=[-80., 0., 80.],
        monthly_zonal_sst_c=[[0., 27., 0.]]*12, reference_period='synthetic declared test')


def world_map(tmp_path, *, dtype=np.float64, receiver=None, status=None):
    s = source()
    root = tmp_path/'world'
    root.mkdir()
    arrays = dict(elevation_m=s['elevation_m'].astype(dtype),
        status=np.where(s['ocean_mask'], 3, 5).astype(np.uint8), receiver=s['receiver'])
    if receiver is not None:
        arrays['receiver'] = receiver
    if status is not None:
        arrays['status'] = status
    specs = {}
    for name, array in arrays.items():
        path = root/(name+'.npy')
        np.save(path, array, allow_pickle=False)
        specs[name] = dict(file=path.name, sha256=stage._sha(path), dtype=str(array.dtype),
            unit='m' if name == 'elevation_m' else '1', meaning='synthetic bed/status/saved receiver', nodata=None)
    manifest = dict(schema='world-map-product-v1', ready=True, producer='test', algorithm_version='fixture',
        lineage=[], world_seed=s['world_seed'], subseeds={}, subseed_method='fixture',
        declared_generated=['bed', 'saved receiver'], limitations=['synthetic'], boundary='finite; no wrap',
        vectors={}, layers=specs, files={v['file']:v['sha256'] for v in specs.values()},
        grid=dict(first_sample_xz_m=s['first_xz_m'], spacing_m=10000., shape_zx=[8, 8],
            semantics='cell-centre', axes='X east, Z south; arrays [z,x]', length_unit='m', sea_level_m=0))
    manifest['identity'] = hashlib.sha256(ts._canon(manifest).encode()).hexdigest()
    (root/'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    return root, manifest['identity']


def test_map_adapter_actual_identity_float64_bed_and_saved_receiver(tmp_path):
    root, identity = world_map(tmp_path)
    s = stage.climate_source_from_map(root, expected_identity=identity)
    assert s['source_identity'] == identity
    assert s['elevation_m'].dtype == np.float64
    np.testing.assert_array_equal(s['elevation_m'], source()['elevation_m'])
    np.testing.assert_array_equal(s['receiver'], source()['receiver'])
    assert not s['elevation_m'].flags.writeable
    rank = np.empty(64, int); rank[s['order']] = np.arange(64)
    rec = s['receiver'].ravel(); donors = np.flatnonzero(rec >= 0)
    assert np.all(rank[rec[donors]] < rank[donors])
    assert 'source_process_identity' not in s and 'plate_identity' not in s
    with pytest.raises(ValueError, match='identity'):
        stage.climate_source_from_map(root, expected_identity='b'*64)
    with pytest.raises(ValueError, match='Explicit expected'):
        stage.climate_source_from_map(root, expected_identity=None)
    with (root/'receiver.npy').open('ab') as stream:
        stream.write(b'tamper')
    with pytest.raises(ValueError, match='Receiver manifest'):
        stage.climate_source_from_map(root, expected_identity=identity)


def test_map_reject_float32(tmp_path):
    root, identity = world_map(tmp_path, dtype=np.float32)
    with pytest.raises(ValueError, match='float64'):
        stage.climate_source_from_map(root, expected_identity=identity)


def test_map_reject_unknown_support(tmp_path):
    status = np.where(source()['ocean_mask'], 3, 5).astype(np.uint8)
    status[-1,-1] = 2
    root, identity = world_map(tmp_path, status=status)
    with pytest.raises(ValueError):
        stage.climate_source_from_map(root, expected_identity=identity)


def test_map_reject_wrong_units(tmp_path):
    root, _ = world_map(tmp_path)
    path = root/'manifest.json'
    manifest = json.loads(path.read_text(encoding='utf-8'))
    manifest['layers']['receiver']['unit'] = 'm3/s'
    manifest.pop('identity')
    manifest['identity'] = hashlib.sha256(ts._canon(manifest).encode()).hexdigest()
    path.write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(ValueError, match='Receiver manifest'):
        stage.climate_source_from_map(root, expected_identity=manifest['identity'])


@pytest.mark.parametrize('rec', [np.array([1, 0]), np.array([0, -1]), np.array([-2, -1]),
    np.array([2, -1]), np.array([0., -1.])])
def test_invalid_receiver_order_rejected(rec):
    with pytest.raises(ValueError):
        stage.topological_order(rec)


def test_coordinates_plan_defaults_limits_and_units():
    climate = stage.climate_module()
    lat, lon = climate.spatial_fields((800, 1000), [-4995000., -3995000.], 10000., stage.configuration())
    assert lon.min() == pytest.approx(-44.9211130876)
    assert lon.max() < 45 and lat.min() > -36 and lat.max() < 36
    assert lat[0, 0] > lat[-1, 0] and lon[0, 0] < lon[0, -1]
    planned = stage.plan(source(), references=reference())
    assert planned['macro_shape_zx'] == [2, 2] and planned['macro_spacing_m'] == 40000
    assert planned['steady_monthly_solves'] == 12 and planned['maximum_outer_cycles'] == 0
    assert planned['config']['diagnostic']['exterior_water_kg_m2'] == 0
    assert planned['config']['diagnostic']['open_faces'] == []
    with pytest.raises(ValueError, match='equirectangular'):
        climate.spatial_fields((2, 2), [5100000., 0.], 10000., stage.configuration())
    with pytest.raises(ValueError, match='[Pp]ositive'):
        stage.plan(dict(source(), spacing_m=-1), references=reference())
    with pytest.raises(ValueError, match='game-diagnostic'):
        stage.configuration({'atmosphere_backend':'legacy-synthetic'})
    with pytest.raises(ValueError, match='separate downstream'):
        stage.configuration({'snow_ice':{'enabled':True}})


def test_native_causal_wind_height_sea_land_units_and_no_source_rain():
    stage.climate_module()
    from terrain_pipeline.atmosphere_climate import solve_diagnostic_monthly_rain as solve
    shape = (4, 12)
    bed = np.broadcast_to(np.linspace(0., 1800., 12), shape).copy()
    sea = np.zeros(shape, bool); sea[:, :3] = True; bed[sea] = -100.
    def run(b=bed, ocean=sea, wind=5., **kw):
        return solve(b, ocean, 20., wind, 0., spacing_m=50000., **kw)
    east = run(); west = run(wind=-5.); flat = run(b=np.where(sea, -100., 0.))
    land = run(ocean=np.zeros(shape, bool))
    p = east['arrays']['monthly_precipitation_mm']
    assert p.min() >= 0 and np.isfinite(p).all()
    assert not np.array_equal(p, west['arrays']['monthly_precipitation_mm'])
    assert not np.array_equal(p, flat['arrays']['monthly_precipitation_mm'])
    assert east['arrays']['monthly_terrain_precipitation_mm'].sum() > 0
    assert west['arrays']['monthly_terrain_precipitation_mm'].sum() == 0
    assert np.count_nonzero(land['arrays']['monthly_precipitation_mm']) == 0
    assert not np.array_equal(p, run(ocean=np.fliplr(sea))['arrays']['monthly_precipitation_mm'])
    np.testing.assert_allclose(p[0]/p[1], 31/28, rtol=1e-12)
    np.testing.assert_allclose(east['arrays']['annual_precipitation_mm'], p.sum(0))
    assert east['budgets']['maximum_relative_water_residual'] < 1e-10
    np.testing.assert_array_equal(p, run()['arrays']['monthly_precipitation_mm'])
    with pytest.raises(ValueError, match='nonnegative'):
        run(monthly_evaporation_mm=-1, evaporation_provenance='invalid negative input')
    with pytest.raises(ValueError, match='nonnegative'):
        run(exterior_water_kg_m2=-1)


def test_checkpoint_cold_recovery_shared_parent_crops_and_no_terrain_evolution(tmp_path, monkeypatch):
    climate = stage.climate_module()
    s = source(); before = s['elevation_m'].copy()
    root = tmp_path/'climate'
    record = stage.prepare(s, root, references=reference())
    assert record['metadata']['capability_flags']['snow_ice'] is False
    assert record['fields']['monthly_discharge_m3_s']['units'] == 'm3/s'
    assert record['fields']['monthly_routed_volume_m3']['units'] == 'm3/month'
    assert record['fields']['monthly_temperature_c']['units'] == 'degC'
    np.testing.assert_array_equal(before, s['elevation_m'])
    whole = climate.query_climate(root, ['monthly_precipitation_mm'])['arrays']['monthly_precipitation_mm']
    left = climate.query_climate(root, ['monthly_precipitation_mm'], window=[0,0,8,4])['arrays']['monthly_precipitation_mm']
    right = climate.query_climate(root, ['monthly_precipitation_mm'], window=[0,4,8,8])['arrays']['monthly_precipitation_mm']
    np.testing.assert_array_equal(whole, np.concatenate([left,right], -1))
    def forbidden(*args, **kwargs):
        raise AssertionError('cold recovery must not solve')
    monkeypatch.setattr(climate, 'compute_climate', forbidden)
    assert stage.prepare(s, root, references=reference(), recover=True)['identity'] == record['identity']
    with pytest.raises(ValueError, match='binding differs'):
        stage.prepare(dict(s, source_identity='b'*64), root, references=reference(), recover=True)
    with pytest.raises(FileExistsError):
        stage.prepare(s, root, references=reference())


def test_probe_is_bounded_not_production_and_only_cuts_crossing_edges():
    s = source()
    probe, evidence = stage.probe_source(s, [2,2,6,6])
    assert evidence['production_usable'] is False and evidence['cut_receiver_edges'] == 4
    assert probe['source_identity'] != s['source_identity']
    assert probe['first_xz_m'] == [-15000., -15000.]
    np.testing.assert_array_equal(probe['elevation_m'], s['elevation_m'][2:6,2:6])
    assert np.all(probe['receiver'][:,0] == -1)
    assert np.all(probe['receiver'][:,1:] == np.arange(16).reshape(4,4)[:,1:]-1)
    with pytest.raises(ValueError, match='outside'):
        stage.probe_source(s, [-1,0,4,4])


def test_native_reject_invalid_supplied_order_and_no_diagnostic_resume(tmp_path):
    climate = stage.climate_module()
    s = source()
    with pytest.raises(ValueError, match='receivers must precede'):
        climate.compute_climate(dict(s, order=s['order'][::-1]), stage.configuration(), reference())
    with pytest.raises(ValueError, match='no coupled restart'):
        climate.compute_climate(s, stage.configuration(), reference(), initial_state={})
    out = tmp_path/'partial'
    out.mkdir()
    (out/'source-binding.json').write_text('{}', encoding='utf-8')
    with pytest.raises(FileExistsError, match='rerun interrupted'):
        stage.prepare(s, out, references=reference())
