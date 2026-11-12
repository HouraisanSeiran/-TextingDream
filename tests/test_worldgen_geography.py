"""Finite author intent, original TG evolution, and explicit Web/CLI plumbing."""
import json
import sys

import numpy as np
import pytest

from app.world_gen import config as wc, geography as geo, skeleton as sk


def feature(**kw):
    return dict(dict(id='west', center_x_m=-55000, center_z_m=5000,
                     radius_m=40000, strength=3), **kw)


def raw(features=None):
    value = dict(world_name='anchor-unit', world=dict(size_km=200))
    if features is not None:
        value['geography_features'] = features
    return value


def test_old_identity_and_exact_noop():
    cfg = wc.normalize(raw())
    assert cfg['identity'] == 'c2019b422929872c65e2b19931c6de221e5322d72614f36db07a61be8426ecb9'
    assert wc.normalize(raw([])) == cfg
    base = sk.land_field('multi-continent', (20, 20), wc.DEFAULT_WORLD_SEED)
    assert geo.bias_land_field(base, cfg) is base
    np.testing.assert_array_equal(base, sk.land_field('multi-continent', (20, 20), wc.DEFAULT_WORLD_SEED))


def test_kernel_sign_determinism_no_wrap_and_bearing():
    base = np.zeros((20, 20))
    cfg = wc.normalize(raw([feature(center_x_m=-95000)]))
    a = geo.bias_land_field(base, cfg)
    np.testing.assert_array_equal(a, geo.bias_land_field(base, cfg))
    assert a[10, 0] == 3 and not a[:, -1].any()
    assert not base.any()
    neg = wc.normalize(raw([feature(center_x_m=-95000, strength=-3)]))
    np.testing.assert_array_equal(geo.bias_land_field(base, neg), -a)
    north = geo.bias_land_field(base, wc.normalize(raw([feature(aspect=2)])))
    east = geo.bias_land_field(base, wc.normalize(raw([feature(aspect=2, bearing_deg=90)])))
    assert north[15, 4] > east[15, 4]


def test_identity_sensitive_and_canonical_order():
    a, b = feature(), feature(id='east', center_x_m=55000, strength=-2)
    cfg = wc.normalize(raw([a, b]))
    assert wc.normalize(raw([b, a])) == cfg
    assert wc.normalize(raw([dict(a, strength=2), b]))['identity'] != cfg['identity']
    assert cfg['identity'] != wc.normalize(raw())['identity']


@pytest.mark.parametrize('change', [dict(strength=True), dict(strength=float('nan')),
    dict(center_x_m=100000), dict(center_z_m=-100001), dict(radius_m=9999),
    dict(radius_m=float('inf')), dict(aspect=.5), dict(aspect=True), dict(bearing_deg='90'),
    dict(bearing_deg=-1), dict(extra=1), dict(id='')])
def test_invalid_features(change):
    with pytest.raises(wc.ConfigError, match='geography_features'):
        wc.normalize(raw([feature(**change)]))


@pytest.mark.parametrize('features', [None, {}, [feature()] * 33, [feature(), feature()], [None]])
def test_invalid_lists_and_duplicates(features):
    value = raw()
    value['geography_features'] = features
    with pytest.raises(wc.ConfigError, match='geography_features'):
        wc.normalize(value)


def test_existing_skeleton_rejects_new_intent():
    value = raw([feature()])
    value['skeleton'] = dict(source='existing', path='frozen.npz', identity='a' * 64)
    with pytest.raises(wc.ConfigError, match='new skeleton'):
        wc.normalize(value)


def test_cli_passes_features_and_rejects_ambiguous_input(monkeypatch, tmp_path):
    from tools import generate_world_skeleton as cli
    captured = []
    monkeypatch.setattr(cli.sk, 'plan_skeleton', lambda cfg: captured.append(cfg) or {})
    assert cli.main(['--preset', 'pangaea', '--size-km', '200', '--plan-only',
                     '--geography-json', json.dumps([feature()])]) == 0
    assert captured[0]['geography_features'] == wc.normalize(raw([feature()]))['geography_features']
    with pytest.raises(SystemExit):
        cli.main(['--config', str(tmp_path/'not-read.json'), '--geography-json', '[]'])
    with pytest.raises(SystemExit):
        cli.main(['--preset', 'pangaea', '--geography-json', 'not json'])


def test_web_submission_and_inline_cli(monkeypatch, tmp_path):
    pytest.importorskip('pydantic')
    from app.world_gen import web_jobs as wj
    monkeypatch.setattr(wj.threading.Thread, 'start', lambda self: None)
    manager = wj.WorldGenManager(tmp_path, artifacts=tmp_path/'artifacts', tg_python=sys.executable,
        memory=lambda: 8 * 2**30, gpu_jobs=lambda: [])
    req = wj.WorldGenRequest(width_km=200, height_km=200, geography_features=[feature()])
    job = manager.submit(req)
    saved = manager._get(job['id'])
    features = saved['params']['geography_features']
    argv = manager.default_stages(saved)[0].argv
    assert json.loads(argv[argv.index('--geography-json') + 1]) == features
    assert features[0]['aspect'] == 1
    other = wj.WorldGenManager(tmp_path/'bad', artifacts=tmp_path/'bad-artifacts', tg_python=sys.executable,
        memory=lambda: 8 * 2**30, gpu_jobs=lambda: [])
    with pytest.raises(wj.WorldGenRefused) as error:
        other.submit(wj.WorldGenRequest(width_km=200, height_km=200,
            geography_features=[feature(radius_m=True)]))
    assert error.value.status == 422 and not other.list() and not other._busy


def test_real_tg_generation_records_input_and_final_outcome(tmp_path):
    pytest.importorskip('psutil')
    cfgraw = raw([feature()])
    cfgraw['skeleton'] = dict(plates=4, steps=1, microcells_per_plate=16, min_plate_cells=4)
    cfg = wc.normalize(cfgraw)
    manifest = sk.generate_skeleton(cfg, tmp_path/'new', max_iterations=1)
    with np.load(tmp_path/'new'/'skeleton.npz', allow_pickle=False) as saved:
        plate = json.loads(str(saved['manifest_json']))
        elevation = saved['final/elevation_m']
    assert plate['geography']['features'] == cfg['geography_features']
    assert manifest['geography']['algorithm'] == geo.ALGORITHM
    row = manifest['geography']['outcomes'][0]
    z, x = row['cell_zx']
    assert row['final_elevation_m'] == float(elevation[z, x])
    assert row['soft_intent_met'] == bool(elevation[z, x] > 0)
    assert plate['world_config_identity'] == cfg['identity']
    from app.world_relief.td_resident import read_plate
    loaded, info = read_plate(tmp_path/'new'/'skeleton.npz')
    np.testing.assert_array_equal(loaded, elevation)
    assert info['identity'] == manifest['product']['plate_identity']


def test_real_tg_initial_crust_bias_and_empty_replay(tmp_path):
    pytest.importorskip('psutil')
    base_raw = raw()
    base_raw['skeleton'] = dict(plates=4, steps=1, microcells_per_plate=16, min_plate_cells=4)
    cfg = wc.normalize(base_raw)
    te, _ = sk._terragenesis()
    tc = sk.tectonic_config(cfg)
    field = sk.land_field('multi-continent', (20, 20), cfg['world_seed'])
    f = feature()
    positive = wc.normalize(dict(base_raw, geography_features=[f]))
    negative = wc.normalize(dict(base_raw, geography_features=[dict(f, strength=-3)]))
    p = sk._initial_state(te, tc, positive, geo.bias_land_field(field, positive), .6)
    n = sk._initial_state(te, tc, negative, geo.bias_land_field(field, negative), .6)
    assert p.continental_m[:, 10, 4].sum() > n.continental_m[:, 10, 4].sum()
    first = sk.generate_skeleton(cfg, tmp_path/'none', max_iterations=1)
    empty = wc.normalize(dict(base_raw, geography_features=[]))
    second = sk.generate_skeleton(empty, tmp_path/'empty', max_iterations=1)
    assert first['product']['plate_identity'] == second['product']['plate_identity']
    assert 'geography' not in first and 'geography' not in second
    assert first['identity'] == second['identity']
