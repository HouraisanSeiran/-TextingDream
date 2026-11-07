import json

import pytest

from app.world_gen import tiles as T


def test_tile_window_native_sample_semantics():
    w = T.tile_window(1, -2)
    assert w['origin_native_xz'] == [512, -1024]
    assert w['first_sample_xz_m'] == [15360, -30720]
    assert w['side_native'] == 513
    assert w['extent_m'] == [15360, -30720, 15360 + 30 * 512, -30720 + 30 * 512]
    assert w['id'] == 'x+001z-002'


def test_tiles_close_without_gap():
    a, b = T.tile_window(0, 0), T.tile_window(1, 0)
    # last sample of tile 0 (index 512) is the first sample of tile 1
    assert a['first_sample_xz_m'][0] + 30 * 512 == b['first_sample_xz_m'][0]


def test_tile_aligned_with_world_cells():
    assert T.TILE_NATIVE % T.WORLD_CELL_NATIVE == 0
    assert T.TILE_NATIVE // T.WORLD_CELL_NATIVE == 16


def test_tiles_for_box_order_and_cover():
    span = 30 * 512
    tl = T.tiles_for_box(0, 0, span * 2, span)
    assert [(t['ix'], t['iz']) for t in tl] == [(0, 0), (1, 0)]
    one = T.tiles_for_box(100, 100, 200, 200)
    assert len(one) == 1
    neg = T.tiles_for_box(-10, -10, 10, 10)
    assert {(t['ix'], t['iz']) for t in neg} == {(-1, -1), (0, -1), (-1, 0), (0, 0)}


def test_tiles_for_box_rejects_bad_box():
    with pytest.raises(ValueError):
        T.tiles_for_box(float('nan'), 0, 1, 1)
    with pytest.raises(ValueError):
        T.tiles_for_box(5, 0, 1, 1)


def test_box_from_center():
    assert T.box_from_center(100, 200, 50) == (75, 175, 125, 225)


def test_decoded_rate_from_benchmark(tmp_path):
    bench = dict(pages=[dict(mode='decoded', ok=True, inference_seconds=20.0, side_native=1000, model_loading_seconds=4.0,
                             reserved_peak_mib=3000, allocated_peak_mib=2000),
                        dict(mode='latent', ok=True, inference_seconds=1.0, side_native=1000, model_loading_seconds=30.0,
                             reserved_peak_mib=1000, allocated_peak_mib=900)])
    p = tmp_path / 'b.json'
    p.write_text(json.dumps(bench))
    r = T.decoded_rate(p)
    assert r['seconds_per_native_px'] == pytest.approx(20.0 / 1000 ** 2)
    assert r['cold_model_loading_seconds'] == 30.0 and r['model_loading_seconds'] == 4.0
    assert not r['fallback']
    cost = T.tile_cost(r, 2)
    assert cost['inference_seconds'] == pytest.approx(2 * 513 ** 2 * 20.0 / 1000 ** 2)


def test_decoded_rate_fallback_flagged(tmp_path):
    r = T.decoded_rate(tmp_path / 'missing.json')
    assert r['fallback'] is True and 'FALLBACK' in r['basis']
