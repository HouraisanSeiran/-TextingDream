"""Atlas frame coordinates on large and tall extents (regression: StopIteration at a 10 000 km span).

A real 10 000 x 8 000-cell product spans 10 000 km, far beyond the former fixed tick list
(5 / 10 / 20 / 25 / 50 / 100 / 200 km), so `atlas._frame_svg` raised StopIteration before it could draw
anything. These tests pin the replacement rule (1 / 2 / 2.5 / 5 x 10^n, smallest step with span / step <= 24),
check that small extents keep the exact numbers the old list produced, that the longer pixel side drives the
choice (a tall narrow page must not be ticked denser than a wide one), and that compose_html still builds a
page instead of emitting a huge tick list. Display layer only: no product arrays are rendered here.
"""
import types

import numpy as np
import pytest

from app.world_relief import atlas

LEGACY_TICKS_M = (5e3, 1e4, 2e4, 2.5e4, 5e4, 1e5, 2e5)   # the fixed list _frame_svg used before the fix
MAX_PER_SIDE = atlas.FRAME_TICK_MAX_PER_SIDE              # 24 ticks along the longer pixel side
NICE = atlas.FRAME_TICK_MANTISSAS


def _legacy_tick(span_m):
    """The replaced expression: next(tick for tick in LEGACY_TICKS_M if span / tick <= 24)."""
    return next(t for t in LEGACY_TICKS_M if span_m / t <= MAX_PER_SIDE)


def _nice_steps(lo_m=atlas.FRAME_TICK_MIN_M, decades=12):
    steps = [m * 10.0 ** k for k in range(3, 3 + decades) for m in NICE]
    return [v for v in sorted(set(steps)) if v >= lo_m]


def _style():
    return atlas.load_styles()["styles"]["simple"]


def _product_stub(spacing=1000.0, first=(-500.0, -500.0)):
    return types.SimpleNamespace(first=first, spacing=spacing)


def _layers(nx, nz, width, spacing=1000.0, first=(-500.0, -500.0), margin=24):
    """The attribute surface compose_html / _frame_svg read, without running build_atlas (no raster, no render)."""
    view = atlas.View(0, 0, nz, nx, int(width), spacing)
    page = np.zeros((view.height + 2 * margin, view.width + 2 * margin, 3), np.uint8)
    return types.SimpleNamespace(
        view=view, params=atlas.AtlasParams(), margin=margin,
        page_rgb=page, map_rgb=page[margin:margin + view.height, margin:margin + view.width],
        relief_rgb=page[margin:margin + view.height, margin:margin + view.width].copy(),
        rivers=[], river_min_area_km2=60.0, symbols=[], decorations=[], skipped_decorations=[],
        scale=atlas.scale_bar(view.mpp, view.s), seeds={}, title="t", subtitle="s",
        forbidden=np.zeros((view.height, view.width), bool), sea=np.zeros((view.height, view.width), bool))


def _counts(svg):
    """(drawn tick rects, coordinate labels) — the frame itself contributes 1 border + 3 outline rects."""
    rects = sum(1 for s in svg if s.startswith("<rect")) - 4
    labels = sum(1 for s in svg if 'class="t-coord"' in s)
    return rects, labels


@pytest.mark.parametrize("span_km", [5, 50, 100, 120, 200, 400, 800, 1600, 2400, 4800])
def test_small_extents_keep_the_legacy_numbers(span_km):
    span = span_km * 1000.0
    assert atlas.frame_tick_m(span) == pytest.approx(_legacy_tick(span))


def test_ten_thousand_km_span_used_to_raise_stopiteration():
    with pytest.raises(StopIteration):                     # documents why the fixed list had to go
        _legacy_tick(10_000_000.0)
    assert atlas.frame_tick_m(10_000_000.0) == pytest.approx(5e5)


@pytest.mark.parametrize("span_km", [200, 1600, 4000, 10000, 20000, 100000])
def test_tick_is_the_smallest_nice_step_with_at_most_24_per_side(span_km):
    span = span_km * 1000.0
    tick = atlas.frame_tick_m(span)
    assert tick == pytest.approx(min(s for s in _nice_steps() if span / s <= MAX_PER_SIDE))
    assert span / tick <= MAX_PER_SIDE
    assert tick / atlas.FRAME_TICK_MIN_M >= 1.0


def test_tick_never_decreases_with_the_span():
    spans = [1e3, 5e3, 1e4, 1.2e5, 2e5, 1.6e6, 1e7, 5e7, 1e8]
    ticks = [atlas.frame_tick_m(s) for s in spans]
    assert ticks == sorted(ticks)
    assert all(t >= atlas.FRAME_TICK_MIN_M for t in ticks)


@pytest.mark.parametrize("bad", [0.0, -1.0, float("nan"), float("inf")])
def test_degenerate_spans_fall_back_to_the_legacy_minimum(bad):
    assert atlas.frame_tick_m(bad) == atlas.FRAME_TICK_MIN_M


def test_ten_thousand_km_frame_draws_a_bounded_tick_list():
    view = atlas.View(0, 0, 8000, 10000, 2400, 1000.0)     # the real product: 10 000 km x 8 000 km
    assert view.width * view.mpp == pytest.approx(1e7)
    q = atlas._frame_svg(types.SimpleNamespace(view=view), _product_stub(), _style())
    ticks, labels = _counts(q)
    assert ticks > 0
    assert ticks <= 4 * MAX_PER_SIDE
    assert labels <= 4 + 2 * MAX_PER_SIDE
    assert "<text" in "".join(q)
    # 500 km ticks -> 1 000 km labels on a 10 000 km side
    assert any(">1000<" in s for s in q)


def test_tall_narrow_extent_is_ticked_by_its_long_side():
    tall = atlas.View(0, 0, 2000, 200, 240, 1000.0)        # 200 km wide, 2 000 km tall
    assert tall.height > 4 * tall.width
    q = atlas._frame_svg(types.SimpleNamespace(view=tall), _product_stub(), _style())
    ticks, labels = _counts(q)
    expected = atlas.frame_tick_m(tall.nz * 1000.0)        # long side, not the 200 km width
    assert expected == pytest.approx(1e5)
    assert expected != pytest.approx(atlas.frame_tick_m(tall.nx * 1000.0))
    assert ticks <= 4 * MAX_PER_SIDE and labels <= 4 + 2 * MAX_PER_SIDE
    assert tall.nz * 1000.0 / expected <= MAX_PER_SIDE
    wide = atlas._frame_svg(types.SimpleNamespace(view=atlas.View(0, 0, 200, 2000, 240, 1000.0)), _product_stub(), _style())
    assert _counts(wide) == (ticks, labels)                # same extent, transposed page: same density


def test_compose_html_works_on_a_ten_thousand_km_product():
    p = _product_stub()
    L = _layers(10000, 8000, 480)
    assert L.view.width * L.view.mpp == pytest.approx(1e7)
    label_km = atlas.frame_tick_m(1e7) * 2 / 1000.0
    for overlays in (False, True):
        html = atlas.compose_html(L, p, "base.png", with_overlays=overlays)
        assert html.rstrip().endswith("</html>")
        assert html.count('class="t-coord"') <= 4 + 2 * MAX_PER_SIDE   # not a wall of ticks
        assert ">%d<" % round(label_km) in html
        assert "NaN" not in html and "inf" not in html
