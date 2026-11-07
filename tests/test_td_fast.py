import json
import numpy as np
import pytest
from app.world_relief import td_fast
from app.world_relief.td_pages import file_sha, write_json

FIRST = [-26880 * 30 + 465, -3200 * 30 + 465]


def test_plan_covers_region_exactly_ragged_edges():
    region = [0, 97, 5, 130]
    blocks = td_fast.plan_blocks(region, 40)
    needed, covered = td_fast.check_coverage(blocks, region)
    assert needed == covered == 97 * 125
    assert any(b['cells_zx'] != [40, 40] for b in blocks)


def test_plan_with_weight_drops_empty_blocks_but_covers_all_positive_cells():
    w = np.zeros((100, 100), dtype=np.float32)
    w[3:10, 3:10] = 1
    w[80:90, 85:99] = .5
    blocks = td_fast.plan_blocks([0, 100, 0, 100], 32, w)
    assert 0 < len(blocks) < 16
    td_fast.check_coverage(blocks, [0, 100, 0, 100], w)


def test_coverage_detects_gap_and_overlap():
    region = [0, 64, 0, 64]
    blocks = td_fast.plan_blocks(region, 32)
    with pytest.raises(ValueError, match='uncovered'):
        td_fast.check_coverage(blocks[:-1], region)
    with pytest.raises(ValueError, match='overlapping'):
        td_fast.check_coverage(blocks + [blocks[0]], region)
    bad = [dict(id='x', cell_zx=[60, 60], cells_zx=[8, 8])]
    with pytest.raises(ValueError, match='outside'):
        td_fast.check_coverage(bad, region)


def test_plan_rejects_bad_input():
    with pytest.raises(ValueError):
        td_fast.plan_blocks([0, 0, 0, 5], 4)
    with pytest.raises(ValueError):
        td_fast.plan_blocks([0, 5, 0, 5], 0)
    with pytest.raises(ValueError):
        td_fast.plan_blocks([0, 50, 0, 5], 4, np.ones((10, 10)))


def test_geometry_matches_old_page_origin_formula():
    # td_resident: origin = (first-465)//30 + x*32 for page grid x
    block = dict(cell_zx=[60, 90], cells_zx=[120, 120])
    g = td_fast.block_geometry(FIRST, block)
    assert g['origin_native_xz'] == [(FIRST[0] - 465) // 30 + 90 * 32, (FIRST[1] - 465) // 30 + 60 * 32]
    (a0, a1), (b0, b1) = g['latent_slice']
    assert a1 - a0 == 480 and b1 - b0 == 480
    assert b0 * 8 == g['origin_native_xz'][0] and a0 * 8 == g['origin_native_xz'][1]
    with pytest.raises(ValueError):
        td_fast.block_geometry([FIRST[0] + 1, FIRST[1]], block)


def test_staging_has_old_page_floor_and_grows_with_block_and_cache():
    small = dict(cells_zx=[30, 30])
    big = dict(cells_zx=[240, 240])
    assert td_fast.staging_bytes(small, 0) >= 300_000_000 + 1024 * 1024 * 160
    assert td_fast.staging_bytes(big, 0) > td_fast.staging_bytes(small, 0)
    assert td_fast.staging_bytes(big, 2 ** 30) > td_fast.staging_bytes(big, 0)


def test_headroom_requires_staging_plus_one_gib_and_rss_budget():
    staging = 500_000_000
    ok = td_fast.block_headroom(staging + 1024 * 2 ** 20, 100, 4096, staging)
    assert ok['required_host_bytes'] == staging + 1024 * 2 ** 20
    with pytest.raises(RuntimeError, match='available host memory'):
        td_fast.block_headroom(staging + 1024 * 2 ** 20 - 1, 100, 4096, staging)
    with pytest.raises(RuntimeError, match='RSS budget'):
        td_fast.block_headroom(10 ** 12, 5000, 4096, staging)


def _finished(tmp_path, expected, block, value=1.0):
    dest = tmp_path / block['id']
    dest.mkdir(parents=True)
    a = np.full(block['cells_zx'], value, dtype=np.float32)
    np.save(dest / 'elevation_960m.npy', a, allow_pickle=False)
    write_json(dest / 'receipt.json', {**expected, **block, 'files': {'elevation_960m.npy': file_sha(dest / 'elevation_960m.npy')}})
    return dest


EXPECTED = dict(algorithm=td_fast.ALGORITHM, plan_identity='p', plate_identity='q', world_seed=1, precision='fp32')


def test_resume_skips_verified_block_and_reports_missing(tmp_path):
    b = td_fast.plan_blocks([0, 8, 0, 8], 8)[0]
    assert td_fast.check_block(tmp_path / b['id'], EXPECTED, b) is None
    _finished(tmp_path, EXPECTED, b)
    assert td_fast.check_block(tmp_path / b['id'], EXPECTED, b)['cell_zx'] == b['cell_zx']


def test_resume_rejects_corruption_mismatch_and_nan(tmp_path):
    b = td_fast.plan_blocks([0, 8, 0, 8], 8)[0]
    dest = _finished(tmp_path, EXPECTED, b)
    with pytest.raises(ValueError, match='mismatch'):
        td_fast.check_block(dest, {**EXPECTED, 'precision': 'fp16'}, b)
    with pytest.raises(ValueError, match='mismatch'):
        td_fast.check_block(dest, EXPECTED, dict(b, cells_zx=[4, 8]))
    np.save(dest / 'elevation_960m.npy', np.zeros((8, 8), dtype=np.float32), allow_pickle=False)
    with pytest.raises(ValueError, match='corrupted'):
        td_fast.check_block(dest, EXPECTED, b)
    (dest / 'elevation_960m.npy').unlink()
    with pytest.raises(ValueError, match='corrupted'):
        td_fast.check_block(dest, EXPECTED, b)


def test_resume_rejects_nonfinite_even_with_matching_hash(tmp_path):
    b = td_fast.plan_blocks([0, 4, 0, 4], 4)[0]
    dest = _finished(tmp_path, EXPECTED, b, value=np.nan)
    with pytest.raises(ValueError, match='invalid'):
        td_fast.check_block(dest, EXPECTED, b)


def test_assemble_places_blocks_at_cell_positions(tmp_path):
    region = [10, 18, 20, 31]
    blocks = td_fast.plan_blocks(region, 6)
    for i, b in enumerate(blocks):
        _finished(tmp_path, EXPECTED, b, value=float(i))
    m = td_fast.assemble(tmp_path, blocks, region)
    assert m.shape == (8, 11) and np.isfinite(m).all()
    for i, b in enumerate(blocks):
        z, x = b['cell_zx']
        h, w = b['cells_zx']
        assert (m[z - 10:z - 10 + h, x - 20:x - 20 + w] == i).all()


def test_gpu_monitor_summary_filters_by_time():
    m = td_fast.GpuMonitor()
    m.samples = [(1, 10, 100), (5, 50, 300), (6, 70, 200)]
    s = m.summary(since=4)
    assert s['samples'] == 2 and s['util_mean_pct'] == 60 and s['mem_used_max_mib'] == 300
    assert m.summary(since=10) == dict(samples=0)


def test_unknown_precision_rejected_before_any_gpu_work(tmp_path):
    with pytest.raises(ValueError, match='precision'):
        td_fast.generate_blocks(tmp_path, tmp_path, {}, [], tmp_path / 'o', purpose='t', options=dict(precision='int4'))


def test_scale_is_part_of_resume_identity_and_default_is_one():
    assert 'scale' in td_fast.NUMERIC_KEYS
    assert td_fast.DEFAULT_OPTIONS['scale'] == 1


def test_scale_origin_is_model_position_of_region_first_cell():
    spec = dict(first_sample_xz_m=FIRST, region=[360, 570, 240, 450])
    assert td_fast.scale_origin(spec) == [FIRST[0] + 240 * 960, FIRST[1] + 360 * 960]


def test_resume_rejects_block_made_with_other_scale(tmp_path):
    b = td_fast.plan_blocks([0, 8, 0, 8], 8)[0]
    dest = _finished(tmp_path, {**EXPECTED, 'scale': 2}, b)
    assert td_fast.check_block(dest, {**EXPECTED, 'scale': 2}, b) is not None
    with pytest.raises(ValueError, match='mismatch'):
        td_fast.check_block(dest, {**EXPECTED, 'scale': 4}, b)


def test_nonpositive_scale_rejected_before_any_gpu_work(tmp_path):
    with pytest.raises(ValueError, match='scale'):
        td_fast.generate_blocks(tmp_path, tmp_path, {}, [], tmp_path / 'o', purpose='t', options=dict(scale=0))


def test_scale_changes_conditioning_sampling_coordinates():
    import inspect
    from app.world_relief import td_resident
    assert 'scale' in inspect.signature(td_resident.periodic_factory).parameters


def test_round3_options_default_off_and_not_part_of_resume_identity():
    for key in ('cuda_graph', 'noise_cache', 'channels_last', 'writer_thread'):
        assert td_fast.DEFAULT_OPTIONS[key] is False
        assert key not in td_fast.NUMERIC_KEYS
