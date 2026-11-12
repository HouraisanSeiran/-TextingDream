"""Diagnostic SavedClimateMap seam: static binding and lazy monthly queries."""
import json

import numpy as np
import pytest

from app.world_gen import climate_world_stage as stage
from app.world_gen.world_climate_adapter import SavedClimateMap
from tests.test_climate_world_stage import world_map, reference


@pytest.fixture
def saved(tmp_path):
    root, identity = world_map(tmp_path)
    source = stage.climate_source_from_map(root, expected_identity=identity)
    product = tmp_path/'climate'
    manifest = stage.prepare(source, product, references=reference())
    return root, product, identity, manifest


def reseal(product, manifest):
    climate = stage.climate_module()
    manifest['manifest_identity'] = climate._manifest_hash({k:v for k,v in manifest.items() if k != 'manifest_identity'})
    (product/'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')


def test_diagnostic_static_only_init_then_lazy_month_window_point(saved, monkeypatch):
    root, product, identity, manifest = saved
    climate = stage.climate_module()
    calls = []
    original = climate.query_climate
    def tracked(path, fields=None, **kwargs):
        calls.append((fields, kwargs))
        assert fields is not None, 'never request every yearly field'
        return original(path, fields=fields, **kwargs)
    monkeypatch.setattr(climate, 'query_climate', tracked)
    def forbidden(*args, **kwargs):
        raise AssertionError('Saved map must never generate or recover an entire year')
    monkeypatch.setattr(climate, 'compute_climate', forbidden)
    monkeypatch.setattr(stage, 'prepare', forbidden)
    view = SavedClimateMap(root, product, expected_source_identity=identity,
        expected_climate_identity=manifest['identity'])
    assert [f for f,_ in calls] == [['ocean_mask'], ['receiver']]
    assert view.process_identity is None and view._environment_fields == {}
    assert view.metadata['convergence']['converged'] is False
    assert view.metadata['convergence']['not_applicable'] is True
    assert 'koppen_geiger_id' not in view.fields and 'biome_id' in view.fields
    fields = ['monthly_precipitation_mm', 'monthly_temperature_c', 'biome_id']
    result = view.query(fields, months=[7,1], window=[2,3,6,7])
    for name in fields:
        raw = np.load(product/manifest['fields'][name]['file'])
        expected = raw[[6,0],2:6,3:7] if raw.ndim == 3 else raw[2:6,3:7]
        np.testing.assert_array_equal(result['arrays'][name], expected)
        assert not result['arrays'][name].flags.writeable
    assert result['grid']['first_xz_m'] == [-5000.,-15000.]
    assert result['process_identity'] is None
    assert 'diagnostic liquid' in result['environment_time']
    point = view.point(-4900., -14900., fields=fields, months=[1,12])
    assert point['cell_zx'] == [2,3]
    assert point['cell_xz_m'] == [-5000.,-15000.]
    np.testing.assert_array_equal(point['arrays']['monthly_temperature_c'],
        np.load(product/'monthly_temperature_c.npy')[[0,11],2,3])
    with pytest.raises(ValueError, match='unavailable'):
        view.query()  # unchanged legacy default includes unsupported Koppen
    with pytest.raises(ValueError, match='unavailable'):
        view.query(['koppen_geiger_id'])
    with pytest.raises(ValueError, match='Months'):
        view.query(fields, months=[0])
    with pytest.raises(ValueError, match='outside'):
        view.point(100000.,0.)


@pytest.mark.parametrize('key,value', [
    ('source_identity','b'*64), ('world_seed',20260904), ('first_xz_m',[0.,0.]),
    ('spacing_m',20000.), ('shape_zx',[4,16]), ('terrain_sha256','0'*64),
    ('binding','0'*64), ('plate_identity','invented-plate'),
])
def test_diagnostic_reject_incorrect_metadata_parent(saved,key,value):
    root,product,_,manifest = saved
    manifest['metadata'][key] = value
    reseal(product,manifest)
    with pytest.raises(ValueError):
        SavedClimateMap(root,product)


@pytest.mark.parametrize('kind', ['receiver','order','config','schema','missing'])
def test_diagnostic_reject_incorrect_source_binding(saved,kind):
    root,product,_,_ = saved
    path = product/'source-binding.json'
    if kind == 'missing':
        path.unlink()
    else:
        binding = json.loads(path.read_text(encoding='utf-8'))
        if kind in ('receiver','order'):
            binding[kind+'_sha256'] = '0'*64
        elif kind == 'config':
            binding['config']['background_wind_m_s'] += 1
        else:
            binding['schema'] = 'unknown'
        path.write_text(json.dumps(binding),encoding='utf-8')
    with pytest.raises(ValueError,match='source-binding'):
        SavedClimateMap(root,product)


@pytest.mark.parametrize('kind', ['source-file','published-file','published-resealed','wrong-expected-source','wrong-expected-climate'])
def test_diagnostic_reject_receiver_tamper_and_identity(saved,kind):
    root,product,identity,manifest = saved
    options = {}
    if kind.endswith('file'):
        path = (root if kind == 'source-file' else product)/'receiver.npy'
        with path.open('ab') as stream:
            stream.write(b'tamper')
    elif kind == 'published-resealed':
        path = product/'receiver.npy'
        rec = np.load(path); rec[-1,-1] = -1
        np.save(path,rec,allow_pickle=False)
        manifest['fields']['receiver']['sha256'] = stage._sha(path)
        reseal(product,manifest)
    elif kind == 'wrong-expected-source':
        options['expected_source_identity'] = 'b'*64
    else:
        options['expected_climate_identity'] = 'b'*64
    with pytest.raises(ValueError):
        SavedClimateMap(root,product,**options)


@pytest.mark.parametrize('kind', ['candidate','metadata-incomplete','wrong-identity','not-applicable-false','algorithm-unknown','snow-enabled'])
def test_diagnostic_reject_incomplete_or_forged_semantics(saved,kind):
    root,product,_,manifest = saved
    if kind == 'candidate':
        manifest['status'] = 'candidate-unconverged'
    elif kind == 'metadata-incomplete':
        manifest['metadata']['status'] = 'candidate-unconverged'
    elif kind == 'wrong-identity':
        manifest['metadata']['identity'] = '0'*64
    elif kind == 'not-applicable-false':
        manifest['metadata']['convergence']['not_applicable'] = False
    elif kind == 'algorithm-unknown':
        manifest['metadata']['algorithm'] = 'unknown-diagnostic'
    else:
        manifest['metadata']['config']['snow_ice']['enabled'] = True
    reseal(product,manifest)
    with pytest.raises(ValueError):
        SavedClimateMap(root,product)


def test_reject_unpublished_partial_product(saved,tmp_path):
    root,_,_,_ = saved
    partial = tmp_path/'partial'; partial.mkdir()
    (partial/'source-binding.json').write_text('{}',encoding='utf-8')
    with pytest.raises(FileNotFoundError):
        SavedClimateMap(root,partial)


def test_old_complete_but_unconverged_product_still_rejected(tmp_path):
    from tests.test_world_climate_adapter import create_saved_products
    root,product,_,manifest = create_saved_products(tmp_path)
    manifest['metadata']['convergence']['converged'] = False
    manifest['metadata']['convergence']['not_applicable'] = True
    reseal(product,manifest)
    with pytest.raises(ValueError,match='completion/identity'):
        SavedClimateMap(root,product)
