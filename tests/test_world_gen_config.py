import json

import pytest

from app.world_gen import config as wc


def base(**world):
    return {'world_name': 'unit', 'world': dict(world)}


def test_defaults_and_identity_stable():
    a = wc.normalize(base())
    b = wc.normalize(base())
    assert a['world_seed'] == 20260903 == wc.DEFAULT_WORLD_SEED
    assert a['world']['type'] == 'multi-continent'
    assert a['world']['ocean_fraction'] == 0.6
    assert a['world']['mountain_target_land_fraction'] == 0.12
    assert a['skeleton']['cell_size_km'] == 10 and a['skeleton']['plates'] == 8
    assert a['identity'] == b['identity'] and len(a['identity']) == 64
    assert wc.normalize(base(type='pangaea'))['identity'] != a['identity']


@pytest.mark.parametrize('size,cell', [(1600, 10), (5000, 20), (10000, 25)])
def test_skeleton_cell_by_size(size, cell):
    cfg = wc.normalize(base(size_km=size))
    assert cfg['skeleton']['cell_size_km'] == cell
    assert cfg['world']['width_km'] == cfg['world']['height_km'] == size


@pytest.mark.parametrize('world,field', [
    (dict(type='nope'), 'world.type'),
    (dict(ocean_fraction=0.4), 'world.ocean_fraction'),
    (dict(ocean_fraction=0.9), 'world.ocean_fraction'),
    (dict(mountain_cover='huge'), 'world.mountain_cover'),
    (dict(mountain_cover=0.9), 'world.mountain_cover'),
])
def test_invalid_world_fields_name_the_field(world, field):
    with pytest.raises(wc.ConfigError, match=field.replace('.', r'\.')):
        wc.normalize(base(**world))


def test_unknown_key_and_seed_rejected():
    with pytest.raises(wc.ConfigError, match='unknown keys'):
        wc.normalize({'world_name': 'x', 'bogus': 1})
    with pytest.raises(wc.ConfigError, match='world_seed'):
        wc.normalize({'world_name': 'x', 'world_seed': True})
    with pytest.raises(wc.ConfigError, match='world_name'):
        wc.normalize({'world_name': 'a/b'})


def test_mountain_levels_and_fraction():
    assert wc.normalize(base(mountain_cover='high'))['world']['mountain_target_land_fraction'] == 0.20
    assert wc.normalize(base(mountain_cover=0.1))['world']['mountain_target_land_fraction'] == 0.1


def test_subseeds_stable_and_distinct():
    a = wc.derive_subseed(20260903, 'land-noise')
    assert a == wc.derive_subseed(20260903, 'land-noise')
    assert a != wc.derive_subseed(20260903, 'land-fine')
    assert a != wc.derive_subseed(20261020, 'land-noise')
    assert 0 <= a < 2 ** 64


def test_local_sites_validation():
    site = dict(id='a', type='town', center_x_m=0, center_z_m=0, radius_m=5000, reason='harbour')
    cfg = wc.normalize({'world_name': 'x', 'local_sites': [site]})
    assert cfg['local_sites'][0]['size_m'] == 10000
    with pytest.raises(wc.ConfigError, match='reason'):
        wc.normalize({'world_name': 'x', 'local_sites': [dict(site, reason='')]})
    with pytest.raises(wc.ConfigError, match='id'):
        wc.normalize({'world_name': 'x', 'local_sites': [site, site]})
    with pytest.raises(wc.ConfigError, match='type'):
        wc.normalize({'world_name': 'x', 'local_sites': [dict(site, type='castle')]})


def test_existing_skeleton_needs_identity():
    with pytest.raises(wc.ConfigError, match='skeleton.identity'):
        wc.normalize({'world_name': 'x', 'skeleton': {'source': 'existing', 'path': 'p.npz', 'identity': 'abc'}})


def test_load_config_roundtrip(tmp_path):
    p = tmp_path / 'c.json'
    p.write_text(json.dumps(base()), encoding='utf-8')
    assert wc.load_config(p)['identity'] == wc.normalize(base())['identity']
    with pytest.raises(wc.ConfigError):
        wc.load_config(tmp_path / 'missing.json')
