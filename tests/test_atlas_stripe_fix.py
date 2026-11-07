"""P2 display fixes: soft multi-direction hillshade with a mountain brightness floor, and merging of parallel river lines.

Display layers only; the product arrays are never touched (covered by test_world_relief_atlas.test_data_arrays_unchanged)."""
import dataclasses

import numpy as np
import pytest

from app.world_relief import atlas
from tests.test_world_relief_atlas import _write_product

OLD_SHADE = dict(shade_z_factor=2.2, snow_max_alpha=0.72, mount_shade_boost=0.18, shade_smooth_cells=0.6,
                 shade_extra_azimuths=(), shade_floor_mount=0.0)


def _line(i, pts, area_end=500.0):
    pts = np.asarray(pts, float)
    return dict(id=i, raw=pts, points=pts, widths=np.ones(len(pts)), area_km2=(area_end / 10, area_end))


def test_parallel_bundle_is_merged_but_tributary_survives():
    ys = np.arange(0, 40, 2.0)
    main = _line("a", np.column_stack([np.full_like(ys, 10.0), ys]), 900)
    twin1 = _line("b", np.column_stack([np.full_like(ys, 11.2), ys]), 300)
    twin2 = _line("c", np.column_stack([np.full_like(ys, 8.9), ys]), 200)
    xs = np.arange(10.0, 40, 2.0)
    trib = _line("d", np.column_stack([xs, 20.0 + (xs - 10.0) * 0.5]), 150)   # joins at an angle, leaves the trunk
    out = atlas.merge_parallel_rivers([twin1, trib, main, twin2], dist_px=1.8, frac=0.7)
    ids = sorted(r["id"] for r in out)
    assert ids == ["a", "d"]


def test_merge_is_order_independent_and_idempotent():
    rng = np.random.default_rng(3)
    lines = []
    for i in range(12):
        y = np.arange(0, 30, 1.5)
        x = 5.0 + (i % 4) * 0.9 + (i // 4) * 25.0 + 0.0 * y
        lines.append(_line("r%02d" % i, np.column_stack([x, y]), 1000 if i % 4 == 0 else 100 + 10 * i))
    shuffled = [lines[i] for i in rng.permutation(len(lines))]
    a = [r["id"] for r in atlas.merge_parallel_rivers(lines, 1.8, 0.7)]
    b = [r["id"] for r in atlas.merge_parallel_rivers(shuffled, 1.8, 0.7)]
    assert sorted(a) == sorted(b)
    again = atlas.merge_parallel_rivers([r for r in lines if r["id"] in set(a)], 1.8, 0.7)
    assert sorted(r["id"] for r in again) == sorted(a)
    assert len(a) < len(lines)


def test_distant_lines_are_never_merged():
    ys = np.arange(0, 30, 1.5)
    ls = [_line("x%d" % i, np.column_stack([np.full_like(ys, 5.0 + 6.0 * i), ys]), 100 + i) for i in range(5)]
    assert len(atlas.merge_parallel_rivers(ls, 1.8, 0.7)) == 5


@pytest.fixture(scope="module")
def product(tmp_path_factory):
    return atlas.load_product(_write_product(tmp_path_factory.mktemp("stripe")))


def _lum(img):
    a = np.asarray(img.convert("L"), np.float64)
    return a


def test_new_shading_is_softer_than_old_on_mountains(product):
    new = atlas.AtlasParams(width_px=800, river_spacing_px=20.0)
    old = dataclasses.replace(new, **OLD_SHADE)
    Ln, Lo = atlas.build_atlas(product, new), atlas.build_atlas(product, old)
    mount = atlas.display_fields(product, atlas.analyse(product, new), Ln.view, new)["mount"] > 0.8
    assert mount.sum() > 200
    ln, lo = _lum(atlas.relief_page(Ln, product)), _lum(atlas.relief_page(Lo, product))
    m = Ln.margin
    ln, lo = ln[m:m + mount.shape[0], m:m + mount.shape[1]][mount], lo[m:m + mount.shape[0], m:m + mount.shape[1]][mount]
    assert np.percentile(ln, 2) > np.percentile(lo, 2) + 5          # dark blotches lifted
    assert (ln < 0.5 * np.median(ln)).mean() < (lo < 0.5 * np.median(lo)).mean() + 1e-9
    assert ln.std() < lo.std()                                       # lower overall block contrast


def test_mountain_brightness_has_a_floor(product):
    p = atlas.AtlasParams(width_px=800, river_spacing_px=20.0)
    assert p.shade_floor_mount > 0 and p.shade_smooth_cells > 0.6 and len(p.shade_extra_azimuths) >= 2
    L = atlas.build_atlas(product, p)
    a = atlas.analyse(product, p)
    df = atlas.display_fields(product, a, L.view, p)
    from app.map_render import load_styles
    style = load_styles()["styles"]["simple"]
    base = atlas.paint_map(product, df, L.view, p, style, forest=False)
    flat = atlas.paint_map(product, df, L.view, dataclasses.replace(p, land_shade_strength=0.0), style, forest=False)
    mount = df["mount"] > 0.9
    ratio = (base.sum(axis=2) / np.maximum(flat.sum(axis=2), 1e-6))[mount & (df["coast"] > 0.5)]
    assert ratio.size > 100
    assert ratio.min() >= 0.28 + p.shade_floor_mount * 0.9 - 0.02


def test_stripe_fix_render_is_deterministic(product):
    p = atlas.AtlasParams(width_px=600, river_spacing_px=20.0)
    a = atlas.build_atlas(product, p)
    b = atlas.build_atlas(product, p)
    assert np.array_equal(np.asarray(atlas.relief_page(a, product)), np.asarray(atlas.relief_page(b, product)))
    assert [r["id"] for r in a.rivers] == [r["id"] for r in b.rivers] if hasattr(a, "rivers") else True


def test_river_merge_never_adds_lines(product):
    p = atlas.AtlasParams(width_px=800, river_spacing_px=20.0)
    view = atlas.full_view(product, 800)
    merged, _ = atlas.river_polylines(product, atlas.analyse(product, p), view, p)
    raw, _ = atlas.river_polylines(product, atlas.analyse(product, p), view, dataclasses.replace(p, river_merge_cells=0.0))
    assert len(merged) <= len(raw)
    assert {r["id"] for r in merged} <= {r["id"] for r in raw}
