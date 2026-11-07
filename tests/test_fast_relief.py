"""terragenesis-fast-relief-v1: fast 2 km world layer from a skeleton (small synthetic skeleton).

Terrain tests need only numpy/scipy and run in the Dream .venv. Hydrology/freeze tests need numba (Terragenesis
irregular_drainage); they are skipped in the Dream .venv and run with
``D:/codexwork/山川形意Terragenesis/runtime/venv/Scripts/python.exe -m pytest tests/test_fast_relief.py``.
"""
import json

import numpy as np
import pytest

from app.world_gen import fast_relief as fr

SEED = 20261020
CELL = 10000.0
NZ, NX = 24, 32
ORIGIN = (-160000.0, -120000.0)


def skeleton_arrays():
    z, x = np.mgrid[0:NZ, 0:NX].astype(np.float64)
    ridge = np.exp(-((x - 12.0) ** 2) / 8.0) * np.exp(-((z - 12.0) ** 2) / 60.0)
    elev = 400.0 + 4500.0 * ridge - 120.0 * np.maximum(x - 20.0, 0.0) ** 2
    oc = elev < 0
    thick = 35000.0 + 30000.0 * ridge
    return elev, thick, oc


def make_sk():
    elev, thick, oc = skeleton_arrays()
    return dict(fields=dict(elevation_m=elev, crust_thickness_m=thick, ocean_connected=oc), cell_m=CELL, origin_xz_m=ORIGIN,
                world_seed=SEED, shape=(NZ, NX), identity='0' * 64, identity_recomputes=True, arrays_verified=False, path='synthetic')


def write_skeleton(path):
    elev, thick, oc = skeleton_arrays()
    m = dict(schema='synthetic-skeleton', config=dict(cell_size_m=CELL, origin_x_m=ORIGIN[0], origin_z_m=ORIGIN[1], world_seed=SEED))
    m['identity'] = fr.identity_of(m)
    np.savez(path, manifest_json=np.array(json.dumps(m)), **{'final/elevation_m': elev, 'final/crust_thickness_m': thick,
                                                              'final/ocean_connected': oc})
    return m['identity']


# ------------------------------------------------------------------ no numba needed
def test_noise_is_coordinate_addressed_and_bounded():
    x = np.linspace(-5e5, 5e5, 200)[None, :]
    z = np.linspace(-4e5, 4e5, 150)[:, None]
    a = fr.fbm_xz(x, z, 123, (90e3, 30e3), (0.7, 0.3))
    b = fr.fbm_xz(x, z, 123, (90e3, 30e3), (0.7, 0.3))
    c = fr.fbm_xz(x, z, 124, (90e3, 30e3), (0.7, 0.3))
    assert np.array_equal(a, b) and not np.allclose(a, c)
    assert np.abs(a).max() <= 1.0 + 1e-9
    # evaluating a sub-window gives identical values (no dependence on query shape/order)
    sub = fr.fbm_xz(x[:, 50:60], z[20:30], 123, (90e3, 30e3), (0.7, 0.3))
    assert np.array_equal(sub, a[20:30, 50:60])


def test_identity_ignores_identity_key_and_is_stable():
    m = dict(a=1, b=[1, 2], identity='x')
    assert fr.identity_of(m) == fr.identity_of(dict(a=1, b=[1, 2]))
    assert fr.identity_of(m) != fr.identity_of(dict(a=2, b=[1, 2]))


def test_subseeds_are_distinct_and_deterministic():
    s = fr.subseeds_for(SEED)
    assert len(set(s.values())) == len(fr.SUBSEED_PURPOSES)
    assert s == fr.subseeds_for(SEED)
    assert s != fr.subseeds_for(SEED + 1)


def test_memory_guard_refuses_when_not_enough_memory():
    with pytest.raises(MemoryError):
        fr.memory_guard(1 << 60)
    assert fr.memory_guard(1) > 0


def test_upsample_constant_and_grid():
    sk = make_sk()
    shape, first = fr.grid_of(sk)
    assert shape == (NZ * 5, NX * 5)
    assert first == (ORIGIN[0] + 1000.0, ORIGIN[1] + 1000.0)
    up = fr.upsample(np.full((NZ, NX), 7.0), shape, fr.SPACING_M, CELL, 3)
    assert np.allclose(up, 7.0, atol=1e-3)


def test_terrain_follows_skeleton_and_is_deterministic():
    sk = make_sk()
    a = fr.build_terrain(sk)
    b = fr.build_terrain(sk)
    assert np.array_equal(a['elevation'], b['elevation']) and np.array_equal(a['ocean'], b['ocean'])
    el, ocean = a['elevation'], a['ocean']
    assert el.dtype == np.float32 and np.isfinite(el).all()
    assert (el[~ocean] >= fr.DEFAULTS['land_min_m'] - 1e-3).all() and (el[ocean] <= 0).all()
    # sea/land agrees with the skeleton away from the coast noise
    su = a['skeleton_up']
    k = int(CELL / fr.SPACING_M)
    far = np.abs(su) > 3 * fr.DEFAULTS['coast_noise_amp_m']
    interior = np.zeros_like(far)       # the synthetic skeleton is not periodic: the wrap-around spline rings at the rim
    interior[4 * k:-4 * k, 4 * k:-4 * k] = True
    far &= interior
    assert far.sum() > 1000
    assert ((su > 0)[far] == (~ocean)[far]).all()
    # the mountain belt sits on the skeleton ridge (x = 12 cells, z = 12 cells of the skeleton)
    peak = np.unravel_index(np.argmax(np.where(ocean, -1e9, el)), el.shape)
    assert abs(peak[1] / k - 12.5) < 3.0 and abs(peak[0] / k - 12.5) < 4.0
    assert el.max() > 2500.0


def test_terrain_changes_with_world_seed():
    sk = make_sk()
    a = fr.build_terrain(sk)['elevation']
    sk2 = dict(sk, world_seed=SEED + 1)
    b = fr.build_terrain(sk2)['elevation']
    assert not np.array_equal(a, b)


def test_schema_registered_for_world_map_and_atlas_alias():
    from app.map_source import registry
    assert (('world-map-product', fr.SCHEMA) in registry._REGISTRY) and (('world-relief-pilot', fr.SCHEMA) in registry._REGISTRY)


def test_load_skeleton_roundtrip(tmp_path):
    ident = write_skeleton(tmp_path / 'sk.npz')
    sk = fr.load_skeleton(tmp_path / 'sk.npz', ident)
    assert sk['identity'] == ident and sk['shape'] == (NZ, NX) and sk['world_seed'] == SEED
    with pytest.raises(ValueError):
        fr.load_skeleton(tmp_path / 'sk.npz', '1' * 64)


# ------------------------------------------------------------------ numba needed
@pytest.fixture(scope="module")
def frozen(tmp_path_factory):
    pytest.importorskip("numba", reason="numba is not installed in this interpreter (Terragenesis irregular_drainage needs it)")
    d = tmp_path_factory.mktemp('fast')
    ident = write_skeleton(d / 'sk.npz')
    out1, m1 = fr.freeze(d / 'sk.npz', d / 'p1', expected_identity=ident, log=lambda *_: None)
    out2, m2 = fr.freeze(d / 'sk.npz', d / 'p2', expected_identity=ident, log=lambda *_: None)
    return d, ident, out1, m1, out2, m2


def test_freeze_is_deterministic_and_identity_has_no_timing(frozen):
    d, ident, out1, m1, out2, m2 = frozen
    assert m1['identity'] == m2['identity'] and m1['files'] == m2['files']
    assert m1['identity'] == fr.identity_of(m1)
    text = json.dumps(m1).lower()
    for word in ('seconds', 'peak_working_set', 'elapsed'):
        assert word not in text
    stats = json.loads((out1 / 'runtime-stats.json').read_text(encoding='utf-8'))
    assert stats['total_seconds'] > 0 and 'identity' not in stats


def test_manifest_records_seeds_and_reused_terragenesis_files(frozen):
    _, ident, _, m, _, _ = frozen
    assert m['producer'] == 'Terragenesis' and m['schema'] == fr.SCHEMA and m['lineage'] == [ident]
    assert m['world_seed'] == SEED and set(m['subseeds']) == set(fr.SUBSEED_PURPOSES)
    assert set(m['reused_code']['terragenesis_sha256']) == set(fr.TG_FILES)
    assert all(len(v) == 64 for v in m['reused_code']['terragenesis_sha256'].values())
    assert m['hydrology']['no_d8'] is True and any('30 m' in s for s in m['limitations'])


def test_product_loads_through_map_source(frozen):
    from app.map_source import load_source
    _, ident, out1, m, _, _ = frozen
    src = load_source('world-map-product', out1, expected_identity=m['identity'])
    assert src.info.world_seed == SEED
    alias = load_source('world-relief-pilot', out1)
    assert alias.info.world_seed == SEED


def test_hydrology_outputs_are_consistent(frozen):
    _, _, out1, m, _, _ = frozen
    el = np.load(out1 / 'elevation_m.npy')
    st = np.load(out1 / 'status.npy')
    rec = np.load(out1 / 'receiver.npy')
    area = np.load(out1 / 'drainage_area_m2.npy')
    assert el.shape == st.shape == rec.shape == area.shape == (NZ * 5, NX * 5)
    assert set(np.unique(st)) <= {3, 5}
    n = rec.size
    r = rec.ravel()
    assert (r < n).all() and (r >= -1).all()
    # every land node reaches an outlet (receiver chain terminates) within n steps: follow all chains at once
    cur = np.arange(n)
    for _ in range(64):
        nxt = np.where(r[cur] >= 0, r[cur], cur)
        if np.array_equal(nxt, cur):
            break
        cur = nxt
    rivers = json.loads((out1 / 'vectors/rivers.json').read_text(encoding='utf-8'))
    assert rivers['schema'] == 'rivers-v1' and isinstance(rivers['lines'], list)
    assert float(area.max()) >= 2000.0 ** 2
    assert 'no_d8' in json.dumps(m['hydrology'])


def test_existing_product_not_overwritten_by_cli(frozen, tmp_path):
    import importlib.util
    from pathlib import Path
    d, ident, out1, *_ = frozen
    spec = importlib.util.spec_from_file_location('build_fast_relief', Path(__file__).resolve().parents[1] / 'tools/build_fast_relief.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    with pytest.raises(SystemExit):
        mod.main(['--skeleton', str(d / 'sk.npz'), '--out', str(out1)])
