"""td_coarse: pure helpers (mountain mask, ridge direction field, geometry, seeds, product identity) need only numpy/scipy.

The model run test needs torch + the Terragenesis checkpoint + vendor code; it is skipped when they are missing and runs with
``D:/codexwork/山川形意Terragenesis/runtime/venv/Scripts/python.exe -m pytest tests/test_td_coarse.py``.
"""
import json

import numpy as np
import pytest

from app.world_gen import td_coarse as tc


def ridge_field(angle_rad, n=96):
    """Gaussian ridge of height 3000 m along a straight line through the centre with the given axis angle (x east, z south)."""
    z, x = np.mgrid[0:n, 0:n].astype(np.float64)
    c = (n - 1) / 2
    d = -(x - c) * np.sin(angle_rad) + (z - c) * np.cos(angle_rad)   # signed distance to the line
    return (3000.0 * np.exp(-d ** 2 / (2 * 5.0 ** 2))).astype(np.float32)


def test_mountain_mask_threshold_and_sea():
    e = np.full((20, 20), 200.0, np.float32)
    e[5:15, 5:15] = 2000.0
    e[0:3, 0:3] = -500.0
    m = tc.mountain_mask(e, threshold_m=1000.0, sigma_cells=0.5)
    assert m[10, 10] and not m[1, 1] and not m[18, 18]
    assert not m[e < 0].any()


@pytest.mark.parametrize('deg', [0, 30, 90, 135])
def test_ridge_orientation_recovers_axis(deg):
    ang = np.radians(deg)
    e = ridge_field(ang)
    mask = tc.mountain_mask(e, 1000.0, 0.5)
    a, coh = tc.ridge_orientation_field(e, mask)
    c = e.shape[0] // 2
    assert mask[c, c]
    assert tc.axial_diff_deg(a[c, c], ang) < 5.0
    assert coh[c, c] > 0.8


def test_ridge_orientation_empty_mask_is_zero():
    e = ridge_field(0.3)
    a, coh = tc.ridge_orientation_field(e, np.zeros(e.shape, bool))
    assert float(coh.max()) == 0.0 and float(np.abs(a).max()) == 0.0
    assert a.dtype == np.float32 and coh.dtype == np.float32


def test_ridge_angle_range_and_axial_diff():
    e = ridge_field(1.0)
    a, coh = tc.ridge_orientation_field(e, tc.mountain_mask(e, 1000.0, 0.5))
    assert a.min() >= 0 and a.max() < np.pi + 1e-6
    assert coh.min() >= 0 and coh.max() <= 1
    assert tc.axial_diff_deg(0.0, np.pi) == pytest.approx(0.0, abs=1e-4)
    assert tc.axial_diff_deg(0.1, np.pi - 0.1) == pytest.approx(np.degrees(0.2), abs=1e-3)


def test_elevation_m_sign_preserving():
    s = np.array([-3.0, 0.0, 2.0, 10.0], np.float32)
    assert np.allclose(tc.elevation_m(s), [-9.0, 0.0, 4.0, 100.0])


def test_extent_cond_range_inside_extent():
    cfg = dict(origin_x_m=-800000.0, origin_z_m=-640000.0, cell_size_m=10000.0, shape=[128, 160])
    ci0, ci1, cj0, cj1 = tc.extent_cond_range(cfg)
    sp = tc.COND_SPACING_M
    assert cj0 * sp >= -800000.0 and (cj1 - 1) * sp < 800000.0 and (cj1 * sp) >= 800000.0
    assert ci0 * sp >= -640000.0 and (ci1 - 1) * sp < 640000.0 and (ci1 * sp) >= 640000.0


def test_window_cond_range_size():
    ci0, ci1, cj0, cj1 = tc.window_cond_range((0.0, 0.0), 300000.0)
    assert ci1 - ci0 == cj1 - cj0 == round(300000 / tc.COND_SPACING_M)


def test_tile_ranges_cover_padded_region():
    (ta0, ta1), (tb0, tb1) = tc.tile_ranges(-83, 84, -104, 105, pad=8)
    assert ta0 * tc.STRIDE <= -83 - 8 and ta1 * tc.STRIDE + tc.TILE >= 84 + 8
    assert tb0 * tc.STRIDE <= -104 - 8 and tb1 * tc.STRIDE + tc.TILE >= 105 + 8


def test_coarse_seed_stable_and_named():
    assert tc.coarse_seed(20261020) == tc.coarse_seed(20261020)
    assert tc.coarse_seed(20261020) != tc.coarse_seed(20260903)
    assert tc.coarse_seed(20261020) != 20261020
    assert 0 <= tc.coarse_seed(1) < 2 ** 64


def test_identity_excludes_runtime_stats():
    m = dict(schema=tc.SCHEMA, a=1)
    i = tc.identity_of(m)
    assert tc.identity_of({**m, 'identity': 'x'}) == i
    assert tc.identity_of({**m, 'a': 2}) != i


def test_require_memory_refuses_when_low(monkeypatch):
    monkeypatch.setattr(tc, 'available_memory_bytes', lambda: 1 * 2 ** 30)
    with pytest.raises(MemoryError):
        tc.require_memory(2 * 2 ** 30)
    monkeypatch.setattr(tc, 'available_memory_bytes', lambda: 3 * 2 ** 30)
    assert tc.require_memory(2 * 2 ** 30) == 3 * 2 ** 30


def _fake_result(n=40):
    e = ridge_field(0.5, n) - 200.0
    return dict(channels=np.stack([np.sqrt(np.abs(e))] * 6).astype(np.float32), elevation_m=e.astype(np.float32), ranges=[0, n, 0, n],
                seed=123, world_seed=7, skeleton_identity='a' * 64,
                skeleton_config=dict(origin_x_m=0.0, origin_z_m=0.0, cell_size_m=10000.0, shape=[8, 8], world_seed=7),
                cond_snr=[.5] * 5, first_sample_xz_m=[0, 0], coarse_means=[0] * 6, coarse_stds=[1] * 6)


def test_write_product_deterministic_identity(tmp_path, monkeypatch):
    monkeypatch.setattr(tc, 'model_identity', lambda root=None: 'f' * 64)
    r = _fake_result()
    m1 = tc.write_product(tmp_path / 'a', r, stats=dict(generate_seconds=1.0))
    m2 = tc.write_product(tmp_path / 'b', r, stats=dict(generate_seconds=99.0))
    assert m1['identity'] == m2['identity']
    assert tc.identity_of(json.loads((tmp_path / 'a' / 'manifest.json').read_text(encoding='utf-8'))) == m1['identity']
    assert (tmp_path / 'a' / 'runtime-stats.json').exists()
    assert 'generate_seconds' not in json.dumps({k: v for k, v in m1.items() if k != 'arrays'})
    for name in ('elevation_m', 'mountain_mask', 'ridge_angle_rad', 'ridge_coherence', 'coarse_channels'):
        assert (tmp_path / 'a' / f'{name}.npy').exists()


def _have_model():
    try:
        import torch  # noqa: F401
        root = tc.terragenesis_root()
        return (root / tc.MODEL_SUBDIR / 'coarse_model' / 'diffusion_pytorch_model.safetensors').exists()
    except Exception:
        return False


@pytest.mark.skipif(not _have_model(), reason='torch / Terragenesis TD checkpoint not available')
def test_model_tiny_window_runs_on_synthetic_skeleton(tmp_path):
    pytest.importorskip('numba')
    # Only checks that the tile loop + denormalisation run and are deterministic for a fixed seed; uses the real frozen skeleton.
    sk = tc.terragenesis_root() / '.scratch/plate-formation-coast-20261101/shaped-run-v4/product.npz'
    if not sk.exists():
        pytest.skip('frozen skeleton not available')
    if tc.available_memory_bytes() < tc.MIN_FREE_BYTES:
        pytest.skip('less than 2 GiB free')
    r1, _ = tc.generate(sk, window=(-475000.0, -315000.0, 7680.0 * 8))
    r2, _ = tc.generate(sk, window=(-475000.0, -315000.0, 7680.0 * 8))
    assert np.isfinite(r1['elevation_m']).all()
    assert np.array_equal(r1['elevation_m'], r2['elevation_m'])


# ------------------------------------------------------------------------------------- run options, tile plan, deep-ocean skip
SKELETON_CFG = dict(origin_x_m=-640000.0, origin_z_m=-640000.0, cell_size_m=10000.0, shape=[128, 128])


def island_source(sea_level_m=0.0, stretch=1.0):
    """Skeleton with one square island (land) in an ocean; 128x128 cells of 10 km."""
    e = np.full((128, 128), -3000.0, np.float32)
    e[56:72, 56:72] = 500.0
    return tc.LandSource(e, SKELETON_CFG, sea_level_m, stretch)


def test_run_options_validate():
    assert tc.RunOptions().validate().stride == tc.STRIDE
    for bad in (dict(stride=4), dict(stride=65), dict(steps=0), dict(batch_size=0), dict(precision='fp16'), dict(skip_ocean_km=-1)):
        with pytest.raises(ValueError):
            tc.RunOptions(**bad).validate()


def test_defaults_match_frozen_product_settings():
    o = tc.RunOptions()
    assert (o.stride, o.steps, o.skip_ocean_km, o.precision, o.batch_size) == (48, 20, 0.0, 'fp32', 1)
    assert tc.precision_label('fp32') == 'float32'


@pytest.mark.parametrize('stride', [48, 56])
def test_tile_ranges_cover_padded_region_for_stride(stride):
    (ta0, ta1), (tb0, tb1) = tc.tile_ranges(-83, 84, -104, 105, pad=8, stride=stride)
    assert ta0 * stride <= -83 - 8 and ta1 * stride + tc.TILE >= 84 + 8
    assert tb0 * stride <= -104 - 8 and tb1 * stride + tc.TILE >= 105 + 8


def test_tile_ranges_default_stride_unchanged():
    assert tc.tile_ranges(-83, 84, -104, 105, pad=8) == tc.tile_ranges(-83, 84, -104, 105, pad=8, stride=48)


def test_plan_without_skip_computes_everything():
    plan = tc.plan_tiles((-83, 84, -104, 105), tc.RunOptions())
    s = plan.summary()
    assert s['tiles_total'] == s['tiles_computed'] == s['tile_rows'] * s['tile_cols']
    assert s['tiles_skipped'] == 0 and s['rule'] is None
    assert all(t.computed and t.min_land_km is None for t in plan.tiles)


def test_plan_skip_needs_land_source():
    with pytest.raises(ValueError):
        tc.plan_tiles((-83, 84, -104, 105), tc.RunOptions(skip_ocean_km=100.0))


def test_plan_skips_only_tiles_farther_than_rule():
    ranges = (-83, 84, -83, 84)
    src = island_source()
    full = tc.plan_tiles(ranges, tc.RunOptions())
    plan = tc.plan_tiles(ranges, tc.RunOptions(skip_ocean_km=100.0), src)
    s = plan.summary()
    assert s['tiles_total'] == full.summary()['tiles_total']
    assert 0 < s['tiles_skipped'] < s['tiles_total']
    assert s['tiles_computed'] + s['tiles_skipped'] == s['tiles_total']
    assert '100' in s['rule'] and 'skipped' in s['rule']
    for t in plan.tiles:
        assert t.computed == (t.min_land_km <= 100.0)
    # the island itself must always be computed
    assert any(t.computed and t.min_land_km == 0.0 for t in plan.tiles)


def test_plan_larger_distance_skips_fewer_tiles():
    ranges = (-83, 84, -83, 84)
    src = island_source()
    counts = [tc.plan_tiles(ranges, tc.RunOptions(skip_ocean_km=km), src).summary()['tiles_skipped'] for km in (50.0, 100.0, 150.0, 300.0)]
    assert counts == sorted(counts, reverse=True)
    assert counts[0] > counts[-1]


def test_plan_no_land_skips_everything_and_all_land_skips_nothing():
    ranges = (-40, 40, -40, 40)
    sea = tc.LandSource(np.full((128, 128), -100.0, np.float32), SKELETON_CFG)
    land = tc.LandSource(np.full((128, 128), 100.0, np.float32), SKELETON_CFG)
    assert tc.plan_tiles(ranges, tc.RunOptions(skip_ocean_km=100.0), sea).summary()['tiles_computed'] == 0
    assert tc.plan_tiles(ranges, tc.RunOptions(skip_ocean_km=100.0), land).summary()['tiles_skipped'] == 0


def test_land_distance_km_values():
    src = island_source()
    # lattice cells (7.68 km): the island spans x,z in [-80000, 80000); a cell 20 lattice steps beyond its edge is ~150 km away
    d = tc.land_distance_km(src, -10, 10, -10, 10, 200.0)
    assert d[10, 10] == 0.0
    far = tc.land_distance_km(src, 40, 41, 0, 1, 500.0)
    # row 40 is z = 307.2 km; the island's last land sample is at z = 70 km -> ~237 km (rounded up by the 7.68 km lattice)
    assert 230.0 < float(far[0, 0]) < 245.0
    no_land = tc.land_distance_km(tc.LandSource(np.full((128, 128), -1.0, np.float32), SKELETON_CFG), 0, 3, 0, 3, 100.0)
    assert np.isinf(no_land).all()


def test_stretch_enlarges_the_island():
    ranges = (-83, 84, -83, 84)
    small = tc.plan_tiles(ranges, tc.RunOptions(skip_ocean_km=50.0), island_source()).summary()['tiles_computed']
    big = tc.plan_tiles(ranges, tc.RunOptions(skip_ocean_km=50.0), island_source(stretch=3.0)).summary()['tiles_computed']
    assert big > small


def test_noise_tiles_match_direct_patch_and_cache():
    calls = []

    def make(seed, y0, x0, h, w, channels, tile_h, tile_w):
        calls.append((y0, x0))
        yy, xx = np.mgrid[y0:y0 + h, x0:x0 + w]
        return np.stack([yy * 1000.0 + xx + c * 1e6 + seed for c in range(channels)]).astype(np.float32)

    nt = tc._NoiseTiles(make, 5, 3)
    for y0, x0 in ((0, 0), (48, 48), (48, 96), (-48, 20), (100, -7)):
        got = nt.patch(y0, x0)
        yy, xx = np.mgrid[y0:y0 + 64, x0:x0 + 64]
        want = np.stack([yy * 1000.0 + xx + c * 1e6 + 5 for c in range(3)]).astype(np.float32)
        assert np.array_equal(got, want)
    n = len(calls)
    nt.patch(48, 48)
    assert len(calls) == n and len(set(calls)) == len(calls)


def _fake_result_with(options=None, plan=None, computed=None):
    r = _fake_result()
    if options is not None:
        r['options'] = options
    if plan is not None:
        r['plan'] = plan
    if computed is not None:
        r['computed_mask'] = computed
    return r


def test_default_manifest_has_no_new_keys_and_frozen_model_fields(tmp_path, monkeypatch):
    monkeypatch.setattr(tc, 'model_identity', lambda root=None: 'f' * 64)
    plain = tc.write_product(tmp_path / 'a', _fake_result())
    same = tc.write_product(tmp_path / 'b', _fake_result_with(options=tc.RunOptions(), computed=np.ones((40, 40), bool)))
    assert plain['identity'] == same['identity']
    assert 'deep_ocean_skip' not in plain
    assert (plain['model']['stride'], plain['model']['steps'], plain['model']['precision']) == (48, 20, 'float32')
    assert not (tmp_path / 'b' / 'computed_mask.npy').exists()
    assert set(plain['model']) == {'name', 'safetensors_sha256', 'only_coarse', 'tile', 'stride', 'steps', 'cond_snr', 'blend', 'precision'}


def test_changed_numeric_options_change_identity(tmp_path, monkeypatch):
    monkeypatch.setattr(tc, 'model_identity', lambda root=None: 'f' * 64)
    base = tc.write_product(tmp_path / 'a', _fake_result())['identity']
    for opts in (tc.RunOptions(stride=56), tc.RunOptions(steps=10), tc.RunOptions(precision='autocast')):
        m = tc.write_product(tmp_path / 'x', _fake_result_with(options=opts))
        assert m['identity'] != base
    speed_only = tc.write_product(tmp_path / 'y', _fake_result_with(options=tc.RunOptions(batch_size=8, threads=16)))
    assert speed_only['identity'] == base


def test_skipped_tiles_are_marked_not_computed_in_product(tmp_path, monkeypatch):
    monkeypatch.setattr(tc, 'model_identity', lambda root=None: 'f' * 64)
    r = _fake_result()
    computed = np.ones((40, 40), bool)
    computed[:, 25:] = False
    r['elevation_m'] = np.where(computed, r['elevation_m'], np.nan).astype(np.float32)
    r['channels'] = np.where(computed[None], r['channels'], np.nan).astype(np.float32)
    plan = dict(tiles_total=10, tiles_computed=6, tiles_skipped=4, rule='RULE-TEXT')
    m = tc.write_product(tmp_path / 'p', _fake_result_with(options=tc.RunOptions(skip_ocean_km=120.0), plan=plan, computed=computed) | dict(
        elevation_m=r['elevation_m'], channels=r['channels']))
    skip = m['deep_ocean_skip']
    assert skip['rule'] == 'RULE-TEXT' and skip['tiles_skipped'] == 4 and skip['tiles_total'] == 10 and skip['skip_ocean_km'] == 120.0
    assert 'computed_mask' in m['arrays']
    el = np.load(tmp_path / 'p' / 'elevation_m.npy')
    mask = np.load(tmp_path / 'p' / 'mountain_mask.npy')
    coh = np.load(tmp_path / 'p' / 'ridge_coherence.npy')
    cm = np.load(tmp_path / 'p' / 'computed_mask.npy').astype(bool)
    assert np.array_equal(cm, computed)
    assert np.isnan(el[~cm]).all() and np.isfinite(el[cm]).all()
    assert not mask[~cm].any() and float(coh[~cm].max()) == 0.0
    json.loads((tmp_path / 'p' / 'manifest.json').read_text(encoding='utf-8'))


SKELETON_V4 = '.scratch/plate-formation-coast-20261101/shaped-run-v4/product.npz'


def test_plan_for_skeleton_counts_without_model():
    sk = tc.terragenesis_root() / SKELETON_V4
    if not sk.exists():
        pytest.skip('frozen skeleton not available')
    p48 = tc.plan_for_skeleton(sk, tc.RunOptions(skip_ocean_km=120.0))
    assert p48['without_skip']['tiles_total'] == 24 and p48['without_skip']['tiles_skipped'] == 0
    assert p48['with_skip']['tiles_total'] == 24
    assert p48['with_skip']['tiles_computed'] + p48['with_skip']['tiles_skipped'] == 24
    p56 = tc.plan_for_skeleton(sk, tc.RunOptions(stride=56))
    assert p56['without_skip']['tiles_total'] < 24 and 'with_skip' not in p56
    big = tc.plan_for_skeleton(sk, tc.RunOptions(), extent_km=2000.0)
    assert big['hypothetical'] and big['without_skip']['tiles_total'] > 24


@pytest.mark.skipif(not _have_model(), reason='torch / Terragenesis TD checkpoint not available')
def test_model_batch_equals_single_and_steps_option():
    pytest.importorskip('numba')
    sk = tc.terragenesis_root() / SKELETON_V4
    if not sk.exists():
        pytest.skip('frozen skeleton not available')
    if tc.available_memory_bytes() < tc.MIN_FREE_BYTES:
        pytest.skip('less than 2 GiB free')
    win = (-475000.0, -315000.0, 7680.0 * 8)
    r1, s1 = tc.generate(sk, window=win, options=tc.RunOptions(batch_size=1))
    r2, s2 = tc.generate(sk, window=win, options=tc.RunOptions(batch_size=2, steps=20))
    assert s1['tiles_total'] == s2['tiles_total'] and s1['tiles_skipped'] == 0
    assert np.allclose(r1['elevation_m'], r2['elevation_m'], atol=1.0)
    assert r1['computed_mask'].all()
    r3, s3 = tc.generate(sk, window=win, options=tc.RunOptions(steps=10))
    assert np.isfinite(r3['elevation_m']).all() and s3['options']['steps'] == 10
    assert not np.array_equal(r1['elevation_m'], r3['elevation_m'])


def _cli():
    import importlib.util
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / 'tools' / 'td_coarse_ridges.py'
    spec = importlib.util.spec_from_file_location('td_coarse_ridges_cli', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_benchmark_refuses_without_gpu(monkeypatch):
    cli = _cli()
    monkeypatch.setattr(tc, 'gpu_status', lambda min_free_mib=1024: (False, dict(cuda_available=False, reason='test')))
    called = []
    monkeypatch.setattr(tc, 'generate', lambda *a, **k: called.append(1))
    with pytest.raises(SystemExit) as e:
        cli.main(['--skeleton', 'unused.npz', '--benchmark', '2'])
    assert '无可用显卡' in str(e.value) and not called


def test_default_device_is_cpu_only():
    # default runs never auto-select CUDA; only --device auto / cuda do
    assert tc.RunOptions().device == 'cpu'
