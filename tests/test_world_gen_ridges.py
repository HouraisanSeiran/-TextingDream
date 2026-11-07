"""dream-world-skeleton-3 (vector ridge network) and dream-fast-relief-2 (fast layer from the ridge network).

Skeleton tests need numpy/scipy only (Dream .venv). Fast-layer freeze tests need numba (Terragenesis venv) and skip otherwise.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from app.world_gen import config as wc, fast_relief as fr, ridge_network as rn, skeleton as sk

ROOT = Path(__file__).resolve().parents[1]


def _cfg(name='ridge-small', preset='multi-continent', size=800):
    return wc.normalize({'world_name': name, 'world': {'type': preset, 'size_km': size, 'ocean_fraction': 0.6}})


def _arrays(path):
    with np.load(path, allow_pickle=False) as z:
        return {k: np.asarray(z[k]) for k in z.files}


@pytest.fixture(scope='module')
def worlds(tmp_path_factory):
    root = tmp_path_factory.mktemp('ridges')
    cfg = _cfg()
    m3a = sk.generate_skeleton(cfg, root / 'v3a', max_iterations=3, ridges='fractal')
    m3b = sk.generate_skeleton(cfg, root / 'v3b', max_iterations=3, ridges='fractal')
    m2 = sk.generate_skeleton(cfg, root / 'v2', max_iterations=3, enhance=True)
    return root, cfg, m3a, m3b, m2


def test_v3_manifest_and_ridge_arrays(worlds):
    root, _, m, _, _ = worlds
    assert m['algorithm'] == 'dream-world-skeleton-3'
    assert abs(m['actual']['mountain_deviation']) <= 0.02 and m['actual']['mountain_within_tolerance']
    assert abs(m['actual']['ocean_deviation']) <= 0.015
    assert {'ridge-net/main-shape', 'ridge-net/branches', 'ridge-net/passes'} <= set(m['subseeds'])
    net, pm = rn.load_network(root / 'v3a' / 'skeleton.npz')
    assert pm['algorithm'] == 'dream-world-skeleton-3' and pm['ridge_network']['identity'] == rn.network_identity(net)
    levels = set(int(v) for v in net['line_level'])
    assert {1, 2} <= levels                         # main ridges and branches
    o = net['line_offsets']
    assert o[0] == 0 and o[-1] == len(net['vertex_amp']) and np.all(np.diff(o) >= 2)
    assert np.all(net['line_parent'][net['line_level'] == 1] == -1)
    child = net['line_level'] > 1
    assert np.all(net['line_parent'][child] >= 0)
    assert np.all(net['line_level'][net['line_parent'][child]] == net['line_level'][child] - 1)
    # TD reader still accepts the npz (identity + elevation hash)
    from app.world_relief.td_resident import read_plate
    read_plate(root / 'v3a' / 'skeleton.npz')


def test_v3_same_seed_is_byte_identical(worlds):
    root, _, m1, m2, _ = worlds
    a, b = _arrays(root / 'v3a' / 'skeleton.npz'), _arrays(root / 'v3b' / 'skeleton.npz')
    assert a.keys() == b.keys()
    for k in a:
        assert np.array_equal(a[k], b[k]), k
    assert m1['product']['sha256'] == m2['product']['sha256']
    assert m1['identity'] == m2['identity']


def test_v3_land_and_ocean_identical_to_v2(worlds):
    root, _, _, _, _ = worlds
    e3 = _arrays(root / 'v3a' / 'skeleton.npz')['final/elevation_m']
    a2 = _arrays(root / 'v2' / 'skeleton.npz')
    e2 = a2['final/elevation_m']
    assert np.array_equal(e3 > 0, e2 > 0)           # land/sea split cell by cell
    assert np.array_equal(e3[e2 <= 0], e2[e2 <= 0])  # ocean values untouched
    a3 = _arrays(root / 'v3a' / 'skeleton.npz')
    for k in ('final/plate_id', 'final/crust_thickness_m', 'final/continental_fraction', 'final/ocean_connected'):
        assert np.array_equal(a3[k], a2[k]), k
    assert not any(k.startswith('ridges/') for k in a2)


def test_unknown_ridge_mode_rejected(tmp_path):
    with pytest.raises(ValueError):
        sk.generate_skeleton(_cfg(), tmp_path, ridges='gaussian')


def test_v2_skeleton_unchanged_against_frozen_product(tmp_path):
    """Regenerating world1600-pangaea-v2 must give the frozen bytes (old enhance path untouched)."""
    frozen = json.loads((ROOT / 'artifacts/worlds/world1600-pangaea-v2/skeleton-run.json').read_text(encoding='utf-8'))
    cfg = wc.normalize({'world_name': 'world1600-pangaea-v2', 'world_seed': 20260903, 'skeleton': {'source': 'new'},
                        'world': {'size_km': 1600.0, 'type': 'pangaea', 'ocean_fraction': 0.6, 'mountain_cover': 'medium'}})
    m = sk.generate_skeleton(cfg, tmp_path / 'v2', enhance=True)
    assert m['algorithm'] == 'dream-world-skeleton-2'
    assert m['product']['sha256'] == frozen['product']['sha256']
    assert m['identity'] == frozen['identity']


def test_ridged_multifractal_is_coordinate_addressed():
    x = np.linspace(-4e5, 4e5, 120)[None, :]
    z = np.linspace(-3e5, 3e5, 90)[:, None]
    wl = (56e3, 28e3, 14e3)
    a = rn.ridged_multifractal(x, z, 99, wl)
    assert np.array_equal(a, rn.ridged_multifractal(x, z, 99, wl))
    assert np.array_equal(a[10:20, 30:40], rn.ridged_multifractal(x[:, 30:40], z[10:20], 99, wl))
    assert np.isfinite(a).all() and a.min() >= -0.05 and a.max() <= 1.6


def test_rasterize_profile_is_tent_not_gaussian():
    """A single straight ridge: the envelope falls linearly-ish ((1-d/w)^1.5) and is exactly 0 beyond the half width."""
    xs = np.arange(-60e3, 60e3 + 1, 2e3)
    n = len(xs)
    net = dict(vertex_xz_m=np.stack([xs, np.zeros(n)], 1), vertex_width_wide_m=np.full(n, 20e3, np.float32),
               vertex_width_steep_m=np.full(n, 10e3, np.float32), vertex_amp=np.ones(n, np.float32),
               vertex_side=np.ones(n, np.int8), line_offsets=np.array([0, n]), line_level=np.array([1], np.int8),
               line_parent=np.array([-1], np.int32), line_chain=np.array([0], np.int32),
               pass_xz_m=np.zeros((0, 2)), pass_depth=np.zeros(0, np.float32), pass_line=np.zeros(0, np.int32))
    _, parts = rn.rasterize(net, (100, 100), (-99e3, -99e3), 2e3, world_seed=1, params=dict(warp_amp_km=0.0), return_parts=True)
    env = parts['envelope']
    col = env[:, 50]
    zc = -99e3 + np.arange(100) * 2e3
    assert col.max() > 0.9
    assert np.all(col[np.abs(zc) > 20e3 + 1] == 0)          # compact support (a Gaussian never reaches 0)
    left, right = col[zc < 0], col[zc > 0]
    assert (left > 0).sum() != (right > 0).sum()              # asymmetric flanks


# ------------------------------------------------------------------ fast layer v2
def test_upsample_limited_stays_within_cells():
    a = np.zeros((12, 12)); a[:, 6:] = 3000.0
    out = fr.upsample_limited(a, (60, 60), 2000.0, 10000.0)
    assert out.min() >= 0.0 and out.max() <= 3000.0
    plain = fr.upsample(a, (60, 60), 2000.0, 10000.0, 3)
    assert plain.min() < -1.0                                  # the plain spline undershoots (the v1 "thin lake" trough)


def test_talus_only_changes_steep_steps_and_conserves_mass():
    h = np.zeros((20, 20)); h[:, 10:] = 100.0; h[5, 5] = 2000.0
    oc = np.zeros(h.shape, bool)
    out = fr.talus_relax(h, oc, 900.0, 0.25)
    assert abs(out.sum() - h.sum()) < 1e-6
    assert out[5, 5] < 2000.0
    assert np.array_equal(out[15:, :], h[15:, :])               # the 100 m step is below the threshold


def test_relief_mode_validation():
    with pytest.raises(ValueError):
        fr.compute(dict(), relief='blur')
    with pytest.raises(ValueError):
        fr.build_terrain_v2(dict(ridges=None))


def test_terrain_v2_land_follows_skeleton_and_is_deterministic(worlds):
    root, _, _, _, _ = worlds
    s = fr.load_skeleton(root / 'v3a' / 'skeleton.npz')
    assert s['ridges'] is not None and s['algorithm'] == 'dream-world-skeleton-3'
    a = fr.build_terrain_v2(s)
    b = fr.build_terrain_v2(s)
    assert np.array_equal(a['elevation'], b['elevation'])
    el = a['elevation']
    assert el.dtype == np.float32 and np.isfinite(el).all()
    assert (el[~a['ocean']] >= fr.DEFAULTS_V2['land_min_m'] - 1e-3).all() and (el[a['ocean']] <= 0).all()
    assert el.max() > 1500.0


@pytest.fixture(scope='module')
def frozen_v2(worlds, tmp_path_factory):
    pytest.importorskip('numba', reason='numba is not installed in this interpreter (Terragenesis irregular_drainage needs it)')
    root = worlds[0]
    d = tmp_path_factory.mktemp('fast2')
    skp = root / 'v3a' / 'skeleton.npz'
    _, m1 = fr.freeze(skp, d / 'p1', relief='ridges', log=lambda *_: None)
    _, m2 = fr.freeze(skp, d / 'p2', relief='ridges', log=lambda *_: None)
    return d, m1, m2


def test_fast_v2_freeze_is_deterministic(frozen_v2):
    d, m1, m2 = frozen_v2
    assert m1['identity'] == m2['identity'] and m1['files'] == m2['files']
    assert m1['algorithm_version'] == 'dream-fast-relief-2' and m1['schema'] == fr.SCHEMA
    assert m1['skeleton']['ridge_network_identity'] and m1['hydrology']['no_d8'] is True
    assert m1['parameters']['erosion_iterations'] >= 10 and m1['parameters']['erosion_max_f'] is None
    assert m1['parameters']['diffusion'] == 0.0
    assert 'terrain_pipeline/procedural_mountain_erosion.py' in m1['reused_code']['terragenesis_sha256']
    for name in m1['files']:
        assert hashlib.sha256((d / 'p1' / name).read_bytes()).hexdigest() == hashlib.sha256((d / 'p2' / name).read_bytes()).hexdigest()
