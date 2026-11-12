"""Saved map climate queries exercise the real producer and exact source binding."""
import hashlib
import json
import numpy as np
import pytest

from app.world_gen.world_climate_adapter import SavedClimateMap, _climate_module


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_array(root, name, value):
    path = root / (name + '.npy')
    np.save(path, value, allow_pickle=False)
    return dict(file=path.name, sha256=digest(path), dtype=str(value.dtype), shape=list(value.shape))


def seal_map(manifest):
    manifest['identity'] = hashlib.sha256(json.dumps(
        {k: v for k, v in manifest.items() if k not in {'identity', 'source_path'}},
        sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def create_saved_products(tmp_path, *, dual_grid=False):
    climate = _climate_module()
    source = tmp_path / 'world'
    process = source / 'world-processes'
    process.mkdir(parents=True)
    n, spacing = (20, 2000.) if dual_grid else (6, 10000.)
    ocean = np.ones((n, n), bool)
    island = slice(4, 16) if dual_grid else slice(2, 4)
    ocean[island, island] = False
    bed = np.where(ocean, -100., 100.123456789)
    cover = np.where(ocean, 0., .4)
    physical = {name: save_array(process, name, value) for name, value in
                dict(elevation_m=bed, ocean_mask=ocean, cover_fraction=cover).items()}
    process_metadata = dict(world_seed=20260903, plate_identity='fixture-plate',
                            first_xz_m=[0., 0.], spacing_m=spacing)
    process_manifest = dict(identity='fixture-process', metadata=process_metadata, arrays=physical)
    (process / 'manifest.json').write_text(json.dumps(process_manifest), encoding='utf-8')
    layers = {}
    for name, value, unit in (('elevation_m', bed.astype(np.float32), 'm'),
                               ('status', np.where(ocean, 3, 5).astype(np.uint8), '1'),
                               ('cover_fraction', cover.astype(np.float32), '1')):
        layers[name] = save_array(source, name, value)
        layers[name].update(unit=unit, nodata=None, meaning='mechanism fixture only')
        if name == 'cover_fraction':
            layers[name]['process_identity'] = 'fixture-process'
    manifest = dict(schema='world-map-product-v1', producer='mechanism-test',
        algorithm_version='fixture', lineage=[], world_seed=20260903,
        subseed_method='fixed', subseeds={}, ready=True, declared_generated=['mechanism fixture'],
        limitations=['synthetic test; not real-world acceptance'], vectors={}, layers=layers,
        grid=dict(first_sample_xz_m=[0., 0.], spacing_m=spacing, shape_zx=[n, n],
                  axes='X east, Z south; arrays [z,x]', length_unit='m', sea_level_m=0,
                  semantics='cell-centre'),
        world_processes=dict(file='world-processes/manifest.json', sha256=digest(process/'manifest.json'),
                             metadata=process_metadata))
    seal_map(manifest)
    (source / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    parent = dict(elevation_m=bed, ocean_mask=ocean, first_xz_m=[0., 0.], spacing_m=spacing,
                  world_seed=20260903, plate_identity='fixture-plate', source_identity=manifest['identity'])
    sst = 20. + 4.*np.cos(2*np.pi*(np.arange(12)-7)/12.)
    reference = dict(schema='terragenesis-climate-reference-v1', latitude_deg=[-80., 0., 80.],
                     monthly_zonal_sst_c=(sst[:, None]+np.array([-15., 8., -15.])[None]).tolist(),
                     reference_period='mechanism fixture', requests=[])
    product = tmp_path / 'climate'
    config = (dict(atmosphere_backend='layered', ocean_spacing_m=4000.,
        atmosphere_spacing_m=10000., atmosphere=dict(moisture_step_s=3.*86400.,
        maximum_monthly_steps=11), layered_atmosphere=dict(
        layer_edges_m=list(np.arange(0., 10001., 1000.)))) if dual_grid else None)
    climate_manifest = climate.prepare_climate(parent, product, config=config, references=reference)
    assert climate_manifest['status'] == 'complete'
    return source, product, manifest, climate_manifest


@pytest.fixture
def saved(tmp_path):
    return create_saved_products(tmp_path)


def hashes(*roots):
    return {str(p): digest(p) for root in roots for p in root.rglob('*') if p.is_file()}


def test_selected_months_crop_and_point_curves_are_exact_and_read_only(saved, monkeypatch):
    source, product, manifest, climate_manifest = saved
    before = hashes(source, product)
    climate = _climate_module()
    def forbidden(*args, **kwargs):
        raise AssertionError('A saved climate map query must never generate or connect')
    monkeypatch.setattr(climate, 'compute_climate', forbidden)
    monkeypatch.setattr(climate, 'prepare_climate', forbidden)
    import socket
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    adapter = SavedClimateMap(source, product,
                              expected_source_identity=manifest['identity'],
                              expected_climate_identity=climate_manifest['identity'])
    names = ['monthly_temperature_c', 'monthly_precipitation_mm', 'monthly_current_x_m_s',
             'monthly_wind_x_m_s', 'koppen_geiger_id', 'cover_fraction']
    result = adapter.query(names, months=[7, 1], window=[1, 2, 5, 6])
    for name in names[:-1]:
        full = np.load(product / climate_manifest['fields'][name]['file'])
        expected = full[[6, 0], 1:5, 2:6] if full.ndim == 3 else full[1:5, 2:6]
        np.testing.assert_array_equal(result['arrays'][name], expected)
        assert not result['arrays'][name].flags.writeable
    np.testing.assert_allclose(result['arrays']['cover_fraction'],
                               np.load(source/'cover_fraction.npy')[1:5, 2:6])
    assert result['grid']['first_xz_m'] == [20000., 10000.]
    assert result['fields']['monthly_precipitation_mm']['units'] == 'mm/month'
    assert result['fields']['monthly_precipitation_mm']['shape'] == [2, 4, 4]
    assert result['fields']['monthly_precipitation_mm']['source_shape'] == [12, 6, 6]
    assert result['fields']['cover_fraction']['dtype'] == str(result['arrays']['cover_fraction'].dtype)
    assert result['fields']['cover_fraction']['role'] == 'realized-environment-at-saved-process-time'
    assert result['fields']['koppen_geiger_id']['role'] != result['fields']['cover_fraction']['role']
    point = adapter.point(20900., 30500., names, months=[1, 7])
    assert point['cell_zx'] == [3, 2]
    assert point['cell_xz_m'] == [20000., 30000.]
    assert point['fields']['monthly_temperature_c']['shape'] == [2]
    np.testing.assert_array_equal(point['arrays']['monthly_temperature_c'],
                                  np.load(product/'monthly_temperature_c.npy')[[0, 6], 3, 2])
    assert float(point['arrays']['cover_fraction']) == pytest.approx(.4)
    assert adapter.terrain.sample(20000., 30000.)['elevation_m'] == pytest.approx(100.123456789)
    assert before == hashes(source, product)


@pytest.mark.parametrize(('key', 'value', 'error'), [
    ('source_identity', 'another-world', 'terrain/grid'),
    ('terrain_sha256', '0'*64, 'terrain/grid'),
    ('first_xz_m', [1., 0.], 'terrain/grid'),
    ('spacing_m', 20000., 'terrain/grid'),
    ('world_seed', 20260904, 'seed/plate'),
    ('plate_identity', 'another-plate', 'seed/plate'),
])
def test_rejects_other_source_terrain_grid_seed_and_plate(saved, key, value, error):
    source, product, _, manifest = saved
    manifest['metadata'][key] = value
    manifest['manifest_identity'] = _climate_module()._manifest_hash(
        {k: v for k, v in manifest.items() if k != 'manifest_identity'})
    (product/'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(ValueError, match=error):
        SavedClimateMap(source, product)


def test_rejects_candidate_missing_fields_invalid_months_and_outside_points(saved):
    source, product, _, manifest = saved
    adapter = SavedClimateMap(source, product)
    with pytest.raises(ValueError, match='unavailable'):
        adapter.query(['made_up_ecology'])
    with pytest.raises(ValueError, match='Months'):
        adapter.query(['cover_fraction'], months=[0])
    with pytest.raises(ValueError, match='outside'):
        adapter.query(window=[0, 0, 7, 6])
    with pytest.raises(ValueError, match='outside'):
        adapter.point(-1., 0.)
    manifest['status'] = 'candidate-unconverged'
    manifest['manifest_identity'] = _climate_module()._manifest_hash(
        {k: v for k, v in manifest.items() if k != 'manifest_identity'})
    (product/'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(ValueError, match='not converged'):
        SavedClimateMap(source, product)


def test_requested_file_tampering_is_detected(saved):
    source, product, _, _ = saved
    adapter = SavedClimateMap(source, product)
    path = product/'monthly_temperature_c.npy'
    data = bytearray(path.read_bytes())
    data[-1] ^= 1
    path.write_bytes(data)
    with pytest.raises(ValueError, match='hash'):
        adapter.query(['monthly_temperature_c'])


@pytest.fixture(scope='module')
def saved_dual_grid(tmp_path_factory):
    # Actual solver product with 4km sea/10km air/10 layers/3-day moisture;
    # this 40km synthetic fixture makes no 1600km world-consumption claim.
    return create_saved_products(tmp_path_factory.mktemp('dual-grid'), dual_grid=True)


def test_real_dual_grid_product_query_window_point_and_read_only(saved_dual_grid, monkeypatch):
    source, product, world, manifest = saved_dual_grid
    assert manifest['metadata']['algorithm'] == 'regional-dual-grid-layered-climate-1'
    assert manifest['metadata']['convergence']['converged']
    assert manifest['metadata']['ocean_grid']['shape_zx'] == [10, 10]
    assert manifest['metadata']['atmosphere_grid']['shape_zx'] == [4, 4]
    before = hashes(source, product)
    def forbidden(*args, **kwargs):
        raise AssertionError('Saved consumer must never start a solver or network connection')
    climate = _climate_module()
    monkeypatch.setattr(climate, 'compute_climate', forbidden)
    monkeypatch.setattr(climate, 'prepare_climate', forbidden)
    import socket
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    adapter = SavedClimateMap(source, product, expected_source_identity=world['identity'],
                              expected_climate_identity=manifest['identity'])
    names = ['monthly_temperature_c', 'monthly_precipitation_mm', 'monthly_sea_temperature_c',
             'monthly_wind_x_m_s', 'koppen_geiger_id', 'cover_fraction']
    result = adapter.query(names, months=[12, 1, 7], window=[2, 3, 8, 10])
    assert result['months'] == [12, 1, 7]
    assert result['grid']['first_xz_m'] == [6000., 4000.]
    for name in names[:-1]:
        full = np.load(product/manifest['fields'][name]['file'], allow_pickle=False)
        expected = full[[11, 0, 6], 2:8, 3:10] if full.ndim == 3 else full[2:8, 3:10]
        np.testing.assert_array_equal(result['arrays'][name], expected)
        assert not result['arrays'][name].flags.writeable
    point = adapter.point(10100., 14200., names[:2], months=[7, 1])
    assert point['cell_zx'] == [7, 5]
    for name in names[:2]:
        np.testing.assert_array_equal(point['arrays'][name],
            np.load(product/manifest['fields'][name]['file'])[[6, 0], 7, 5])
        assert not point['arrays'][name].flags.writeable
    assert hashes(source, product) == before


@pytest.mark.parametrize(('key', 'value', 'error'), [
    ('source_identity', 'wrong-parent', 'terrain/grid'),
    ('terrain_sha256', '0'*64, 'terrain/grid'),
    ('world_seed', 20260904, 'seed/plate'),
    ('plate_identity', 'wrong-plate', 'seed/plate'),
    ('convergence', {'converged':False}, 'completion'),
])
def test_dual_grid_retains_parent_and_convergence_gates(saved_dual_grid, key, value, error):
    source, product, _, _ = saved_dual_grid
    path = product/'manifest.json'
    original = path.read_bytes()
    manifest = json.loads(original)
    manifest['metadata'][key] = value
    manifest['manifest_identity'] = _climate_module()._manifest_hash(
        {k:v for k,v in manifest.items() if k != 'manifest_identity'})
    try:
        path.write_text(json.dumps(manifest), encoding='utf-8')
        with pytest.raises(ValueError, match=error):
            SavedClimateMap(source, product)
    finally:
        path.write_bytes(original)


def test_dual_grid_rejects_candidate_and_manifest_tamper(saved_dual_grid):
    source, product, _, _ = saved_dual_grid
    path = product/'manifest.json'
    original = path.read_bytes()
    manifest = json.loads(original)
    manifest['status'] = 'candidate-unconverged'
    manifest['manifest_identity'] = _climate_module()._manifest_hash(
        {k:v for k,v in manifest.items() if k != 'manifest_identity'})
    try:
        path.write_text(json.dumps(manifest), encoding='utf-8')
        with pytest.raises(ValueError, match='not converged'):
            SavedClimateMap(source, product)
        manifest['manifest_identity'] = '0'*64
        path.write_text(json.dumps(manifest), encoding='utf-8')
        with pytest.raises(ValueError, match='identity'):
            SavedClimateMap(source, product)
    finally:
        path.write_bytes(original)
