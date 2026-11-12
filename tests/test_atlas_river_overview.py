"""Overview river symbols only: synthetic saved-like arrays, no world generation or browser."""
import copy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from app.world_relief import atlas


@pytest.fixture
def product():
    shape, spacing = (32, 40), 10000.0
    z, x = np.indices(shape)
    ocean = x < 4
    elevation = np.where(ocean, -200.0, 100.0 + x * 15 + z * 2).astype(np.float32)
    area = np.zeros(shape, np.float64)
    rivers = []
    for row, catchment in ((8, 40000.0), (16, 160000.0), (24, 1809300.0)):
        area[row, 8:36] = catchment * 1e6
        rivers.append(dict(id=str(row), coordinates_xz_m=[[(i + 0.5) * spacing, (row + 0.5) * spacing]
                                                       for i in range(8, 36)],
                           head_area_km2=catchment, outlet_area_km2=catchment))
    info = SimpleNamespace(spacing_m=spacing, shape_zx=shape, first_sample_xz_m=(5000.0, 5000.0),
                           identity="synthetic-river-overview", world_seed=7, kind=atlas.SOURCE_KIND,
                           schema="test", lineage=(), limitations=())
    return atlas.Product(path=Path("synthetic"), source=SimpleNamespace(info=info), elevation=elevation,
                         ocean=ocean, closed=np.zeros(shape, bool), lake_surface=elevation.copy(),
                         area_m2=area, rivers=rivers, river_threshold_km2=60.0)


def _draw(product, params, width=48, lake=None):
    view = atlas.full_view(product, width)
    a = {"lake": np.zeros(product.shape, bool) if lake is None else lake}
    return atlas.river_polylines(product, a, view, params), view


def test_overview_threshold_and_more_existing_tributaries(product):
    params = atlas.AtlasParams()
    (new, amin), view = _draw(product, params)
    (old, old_amin), _ = _draw(product, replace(params, river_overview=False))
    assert view.mpp == pytest.approx(8333.333333)
    assert amin == pytest.approx(40000.0)
    assert old_amin == pytest.approx((55 * view.mpp / 1000) ** 2)
    assert {r["id"] for r in old} == {"24"}
    assert {r["id"] for r in new} == {r["id"] for r in product.rivers}
    assert len(new) > len(old)
    trunk = next(r for r in new if r["id"] == "24")
    assert np.array_equal(trunk["raw"], old[0]["raw"])
    assert np.array_equal(trunk["points"], old[0]["points"])
    product.river_threshold_km2 = 80000.0
    assert atlas.river_min_area_km2(product, view, params) == 80000.0


def test_fixed_anchor_widths_are_monotone_fine_and_capped(product):
    params = atlas.AtlasParams()
    (rivers, _), _ = _draw(product, params)
    widths = [r["widths"][0] for r in rivers]
    assert widths == pytest.approx([0.55, 1.55, 0.55 + 0.5 * np.log2(1809300 / 40000)])
    assert np.all(np.diff(widths) > 0)
    assert 3.25 < widths[-1] < 3.4
    # Changing which tributaries pass the filter must not inflate a surviving trunk.
    (filtered, _), _ = _draw(product, replace(params, river_overview_spacing_px=40))
    assert np.array_equal(filtered[-1]["widths"], rivers[-1]["widths"])
    product.area_m2[24, 8:36] = 1e14
    (huge, _), _ = _draw(product, params)
    assert huge[-1]["widths"].max() == pytest.approx(3.4)


@pytest.mark.parametrize("width", [48, 201])
def test_off_and_small_pages_use_exact_legacy_formula(product, width):
    params = atlas.AtlasParams(river_overview=False)
    (rivers, amin), view = _draw(product, params, width)
    assert amin == max(product.river_threshold_km2, (params.river_spacing_px * view.mpp / 1000) ** 2)
    for river in rivers:
        area = river["area_km2"][0]
        expected = np.clip(params.river_w0_px + params.river_wk_px * np.log2(area / amin),
                           params.river_w0_px, params.river_wmax_px)
        np.testing.assert_allclose(river["widths"], expected, rtol=0, atol=1e-14)
    if width == 201:
        assert view.mpp < 2000
        (default, default_amin), _ = _draw(product, replace(params, river_overview=True), width)
        assert default_amin == amin
        assert atlas._rivers_svg(default, "blue") == atlas._rivers_svg(rivers, "blue")
    assert atlas.river_overview_mode(atlas.View(0, 0, 32, 40, 200, 10000), replace(params, river_overview=True))


def test_lake_shore_splits_and_no_through_lake_chord(product):
    product.rivers[-1].update(through_lake=True, lake_spans=[[12, 16]])
    lake = np.zeros(product.shape, bool)
    lake[8, 18:21] = True
    (rivers, _), view = _draw(product, atlas.AtlasParams(), lake=lake)
    # Existing geometry is preserved; neither the lake interior nor its explicit chord is bridged.
    assert len([r for r in rivers if r["id"] == "8"]) == 2
    trunk = [r for r in rivers if r["id"] == "24"]
    assert len(trunk) == 2
    for r in rivers:
        source = next(line for line in product.rivers if line["id"] == r["id"])
        source_px = np.asarray(source["coordinates_xz_m"]) / view.mpp
        assert all(any(np.array_equal(q, s) for s in source_px) for q in r["raw"])
        assert np.array_equal(r["points"][0], r["raw"][0])
        assert np.array_equal(r["points"][-1], r["raw"][-1])
    assert trunk[0]["raw"][-1, 0] == pytest.approx(20.5 * product.spacing / view.mpp)
    assert trunk[1]["raw"][0, 0] == pytest.approx(24.5 * product.spacing / view.mpp)


def test_relief_control_inputs_and_provenance_unchanged(product):
    names = ("elevation", "ocean", "closed", "lake_surface", "area_m2")
    arrays = {name: getattr(product, name).copy() for name in names}
    vectors = copy.deepcopy(product.rivers)
    params = atlas.AtlasParams(width_px=48)
    new = atlas.build_atlas(product, params)
    old = atlas.build_atlas(product, replace(params, river_overview=False))
    assert len(new.rivers) > len(old.rivers)
    assert np.array_equal(new.relief_rgb, old.relief_rgb)
    assert np.array_equal(np.asarray(atlas.relief_page(new)), np.asarray(atlas.relief_page(old)))
    for name in names:
        assert np.array_equal(getattr(product, name), arrays[name])
    assert product.rivers == vectors
    prov = atlas.provenance(product, new, params, {})
    assert prov["river_display"]["overview"] is True
    assert prov["river_display"]["width_anchor_km2"] == 40000
    assert "not physical river width or discharge" in prov["river_display"]["width_semantics"]
    assert "非真实河宽或流量" in " ".join(prov["layers"]["data"])
    small = atlas.build_atlas(product, replace(params, width_px=201))
    small_off = atlas.build_atlas(product, replace(params, width_px=201, river_overview=False))
    assert np.array_equal(small.page_rgb, small_off.page_rgb)
    assert atlas.compose_html(small, product, "base.png") == atlas.compose_html(small_off, product, "base.png")
