"""dream-world-skeleton-4 (orogen belts) and dream-fast-relief-3 (fast layer from the belts, lakes off ridges, rivers cut at lakes).

Skeleton / helper tests need numpy/scipy only (Dream .venv). The fast-layer freeze tests need numba (Terragenesis venv) and skip otherwise.
"""
import hashlib

import numpy as np
import pytest

from app.world_gen import config as wc, fast_relief as fr, graph_hydro as gh, ridge_network as rn, skeleton as sk


def _cfg(name='orogen-small', preset='pangaea', size=800):
    return wc.normalize({'world_name': name, 'world': {'type': preset, 'size_km': size, 'ocean_fraction': 0.6}})


def _arrays(path):
    with np.load(path, allow_pickle=False) as z:
        return {k: np.asarray(z[k]) for k in z.files}


@pytest.fixture(scope='module')
def worlds(tmp_path_factory):
    root = tmp_path_factory.mktemp('orogen')
    cfg = _cfg()
    m4a = sk.generate_skeleton(cfg, root / 'v4a', max_iterations=3, ridges='orogen')
    m4b = sk.generate_skeleton(cfg, root / 'v4b', max_iterations=3, ridges='orogen')
    m3 = sk.generate_skeleton(cfg, root / 'v3', max_iterations=3, ridges='fractal')
    return root, m4a, m4b, m3


def test_v4_manifest_and_belt_arrays(worlds):
    root, m, _, _ = worlds
    assert m['algorithm'] == 'dream-world-skeleton-4'
    assert m['ridge_network']['algorithm'] == rn.OROGEN_ALGORITHM
    assert 'mountain_area_land_fraction' in m['actual'] and 'high_mountain_land_fraction' in m['actual']
    assert m['targets']['mountain_area_land_fraction_band'] == [0.2, 0.3]
    net, pm = rn.load_network(root / 'v4a' / 'skeleton.npz')
    for k in ('belt_offsets', 'belt_xz_m', 'belt_half_width_m', 'belt_class', 'line_belt', 'gap_xz_m'):
        assert k in net, k
    o = net['belt_offsets']
    assert o[0] == 0 and o[-1] == len(net['belt_xz_m'])
    assert len(net['line_belt']) == len(net['line_level'])
    lv1 = net['line_level'] == 1
    assert np.all(net['line_belt'][lv1] >= 0)
    from app.world_relief.td_resident import read_plate
    read_plate(root / 'v4a' / 'skeleton.npz')


def test_v4_same_seed_is_byte_identical(worlds):
    root, m1, m2, _ = worlds
    a, b = _arrays(root / 'v4a' / 'skeleton.npz'), _arrays(root / 'v4b' / 'skeleton.npz')
    assert a.keys() == b.keys()
    for k in a:
        assert np.array_equal(a[k], b[k]), k
    assert m1['identity'] == m2['identity']


def test_v4_land_sea_and_ocean_identical_to_v3(worlds):
    root, _, _, _ = worlds
    a4, a3 = _arrays(root / 'v4a' / 'skeleton.npz'), _arrays(root / 'v3' / 'skeleton.npz')
    e4, e3 = a4['final/elevation_m'], a3['final/elevation_m']
    assert np.array_equal(e4 > 0, e3 > 0)
    assert np.array_equal(e4[e3 <= 0], e3[e3 <= 0])
    for k in ('final/plate_id', 'final/crust_thickness_m', 'final/ocean_connected'):
        assert np.array_equal(a4[k], a3[k]), k


def test_belt_platform_is_flat_topped_not_gaussian():
    """One straight belt: footprint q = 1 - d/W reaches exactly 0 beyond W, floor is flat in the belt core."""
    xs = np.arange(-200e3, 200e3 + 1, 5e3)
    belts = [dict(xz=np.stack([xs, np.zeros(len(xs))], 1), W=np.full(len(xs), 60e3), floor=np.full(len(xs), 800.0))]
    shape = (100, 100)
    wx = np.zeros(shape, np.float32); wz = np.zeros(shape, np.float32)
    q, fl, bid = rn._belt_fields(belts, shape, (-198e3, -198e3), 4e3, wx, wz, 0.0, 0.32)
    zc = -198e3 + np.arange(100) * 4e3
    col_q, col_f = q[:, 50], fl[:, 50]
    assert np.all(col_q[np.abs(zc) > 60e3 + 1] == 0) and np.all(bid[np.abs(zc) > 60e3 + 1, 50] == -1)
    core = np.abs(zc) < 30e3
    assert np.allclose(col_f[core], 800.0)                     # flat platform top
    assert col_f.max() == pytest.approx(800.0)


def test_lake_filter_rejects_lakes_on_ridges():
    keep = np.array([True, True])
    labels = np.array([1, 1, 2, 2])
    forbid = np.array([False, False, True, False])
    out, info = gh.lake_filter(keep, labels, None, None, 2000.0, None, forbid=forbid)
    assert out.tolist() == [True, False] and info['rejected_on_ridge'] == 1


def test_rivers_are_cut_at_the_lake_shore():
    px = np.arange(6, dtype=float) * 1000.0; pz = np.zeros(6)
    lake = np.array([0, 0, 1, 1, 0, 0])
    lines = [dict(id='r-a', downstream_id=None, nodes=[0, 1, 2, 3, 4, 5])]
    rivers, links = gh.cut_lines_at_lakes(lines, px, pz, np.arange(1, 7) * 4e6, (1, 6), np.zeros(6, bool), lake)
    assert len(rivers) == 2
    inflow = [r for r in rivers if r['to_lake'] == 1]; outflow = [r for r in rivers if r['from_lake'] == 1]
    assert len(inflow) == 1 and len(outflow) == 1
    assert inflow[0]['points_xz_m'][-1] == [1500.0, 0.0] and outflow[0]['points_xz_m'][0] == [3500.0, 0.0]
    assert links[1]['inflow'] and links[1]['outflow']
    assert all(not r['through_lake'] for r in rivers)
    ov = gh.river_lake_overlap(rivers, lake.reshape(1, 6), (0.0, 0.0), 1000.0)
    assert ov['over_lake_km'] < 0.3                               # only the half-cell stubs to the shore


def test_terrain_v3_requires_orogen_skeleton_and_is_deterministic(worlds):
    root, _, _, _ = worlds
    with pytest.raises(ValueError):
        fr.build_terrain_v3(fr.load_skeleton(root / 'v3' / 'skeleton.npz'))
    s = fr.load_skeleton(root / 'v4a' / 'skeleton.npz')
    a, b = fr.build_terrain_v3(s), fr.build_terrain_v3(s)
    assert np.array_equal(a['elevation'], b['elevation'])
    el = a['elevation']
    assert np.isfinite(el).all() and (el[a['ocean']] <= 0).all() and el.max() > 1500.0
    assert a['lake_forbid'].any() and a['mountain_area'].any()


@pytest.fixture(scope='module')
def frozen_v3(worlds, tmp_path_factory):
    pytest.importorskip('numba', reason='numba is not installed in this interpreter (Terragenesis irregular_drainage needs it)')
    root = worlds[0]
    d = tmp_path_factory.mktemp('fast3')
    skp = root / 'v4a' / 'skeleton.npz'
    _, m1 = fr.freeze(skp, d / 'p1', relief='orogen', log=lambda *_: None)
    _, m2 = fr.freeze(skp, d / 'p2', relief='orogen', log=lambda *_: None)
    return d, m1, m2


def test_fast_v3_freeze_is_deterministic_and_rivers_avoid_lakes(frozen_v3):
    d, m1, m2 = frozen_v3
    assert m1['identity'] == m2['identity'] and m1['files'] == m2['files']
    assert m1['algorithm_version'] == 'dream-fast-relief-3' and m1['hydrology']['no_d8'] is True
    st = m1['statistics']
    assert st['through_lake']['through_lake_lines'] == 0
    assert st['river_length_over_lake_km'] < 0.01 * max(st['kept_lakes'], 1) * 50
    assert st['lakes_without_outflow'] == 0
    for name in m1['files']:
        assert hashlib.sha256((d / 'p1' / name).read_bytes()).hexdigest() == hashlib.sha256((d / 'p2' / name).read_bytes()).hexdigest()
