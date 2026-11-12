"""超大总览的近似群系配色与林型分色（显示层，非气候数据）。

只在每像素 ≥ biome_mpp 的超大总览启用；小页面输出逐字节不变。群系由南北位置、海拔、离海距离和坐标噪声推算，
森林掩码不变，只改林色。本文件用测试自己 tmp 目录里的极小合成产品，不生成地形、不起浏览器。
"""
import numpy as np
import pytest
from scipy import ndimage as nd

from app.map_render import load_styles
from app.world_relief import atlas
from app.world_relief.source import subseed
from tests.test_world_relief_atlas import _write_product

SMALL = dict(width_px=800, river_spacing_px=20.0)
COARSE = dict(SMALL, forest_area_mpp=200.0, biome_mpp=200.0)
OFF = dict(SMALL, forest_area_mpp=200.0, biome_mpp=1e9)       # 林色块开、群系关：对照


def _style():
    return load_styles()["styles"]["simple"]


@pytest.fixture(scope="module")
def product(tmp_path_factory):
    return atlas.load_product(_write_product(tmp_path_factory.mktemp("biome-colors")))


@pytest.fixture(scope="module")
def coarse(product):
    return atlas.build_atlas(product, atlas.AtlasParams(**COARSE))


@pytest.fixture(scope="module")
def blocks_only(product):
    return atlas.build_atlas(product, atlas.AtlasParams(**OFF))


def test_biome_classes_are_deterministic_and_land_only(product):
    params = atlas.AtlasParams(**COARSE)
    a = atlas.analyse(product, params)
    b = a["biome"]
    assert b.shape == product.shape and b.dtype == np.int8
    assert (b[~a["land"]] == 0).all() and (b[a["lake"]] == 0).all()
    land = a["land"] & ~a["lake"]
    assert (b[land] > 0).all() and b.max() <= len(atlas.BIOMES)
    assert len(np.unique(b[land])) >= 3
    product.cache.clear()
    assert np.array_equal(b, atlas.analyse(product, params)["biome"])


def test_classifier_follows_its_proxies():
    params = atlas.AtlasParams()
    land = np.ones((1, 6), bool)
    h0 = np.array([[100.0, 100.0, 100.0, 100.0, 100.0, 4000.0]])
    temp = np.array([[0.05, 0.25, 0.5, 0.5, 0.8, 0.5]])
    moist = np.array([[0.5, 0.5, 0.8, 0.1, 0.9, 0.5]])
    b = atlas.classify_display_biome(land, h0, temp, moist, np.full((1, 6), 2300.0), params)
    names = [atlas.BIOMES[i - 1][0] for i in b[0]]
    assert names == ["tundra", "boreal", "temperate_humid", "cold_desert", "tropical_humid", "alpine"]


def test_forest_mask_unchanged_and_types_only_inside(product):
    params = atlas.AtlasParams(**COARSE)
    a = atlas.analyse(product, params)
    old = atlas.analyse(product, atlas.AtlasParams(**SMALL))
    assert np.array_equal(a["forest"], old["forest"])
    t = a["forest_type"]
    assert ((t > 0) == a["forest"]).all()
    assert (t[a["conifer"]] == 2).all()
    assert len(np.unique(t[a["forest"]])) >= 2


def test_small_pages_are_unchanged(product):
    L = atlas.build_atlas(product, atlas.AtlasParams(**SMALL))
    off = atlas.build_atlas(product, atlas.AtlasParams(**dict(SMALL, biome_mpp=1e9)))
    assert L.biome_paint is False and "biome-moisture" not in L.seeds
    assert np.array_equal(L.page_rgb, off.page_rgb)
    assert all(row[0] != "biome" for row in atlas.legend_rows(L))
    df = atlas.display_fields(product, atlas.analyse(product, L.params), L.view, L.params)
    assert "biome_rgb" not in df and "forest_rgb" not in df


def test_biome_page_varies_land_colour_but_not_sea_or_relief(product, coarse, blocks_only):
    assert coarse.biome_paint is True
    assert coarse.seeds["biome-moisture"] == subseed(20260903, "atlas/biome-moisture")
    sea = coarse.sea
    # open sea (past the anti-aliased coast pixels, which carry a little land colour by design) is untouched
    open_sea = nd.binary_erosion(sea, iterations=2)
    assert open_sea.sum() > 1000
    assert np.array_equal(coarse.map_rgb[open_sea], blocks_only.map_rgb[open_sea])
    assert np.array_equal(coarse.relief_rgb, blocks_only.relief_rgb)
    land = ~sea
    diff = np.abs(coarse.map_rgb.astype(float) - blocks_only.map_rgb.astype(float))[land].mean()
    assert diff > 2.0
    # the biome colour field itself varies across land (several classes, not one flat tint)
    df = atlas.display_fields(product, atlas.analyse(product, coarse.params), coarse.view, coarse.params)
    assert df["biome_rgb"][df["coast"] > 0.5].std(axis=0).max() > 3.0


def test_forest_colours_vary_by_type(product, coarse):
    params = coarse.params
    a = atlas.analyse(product, params)
    df = atlas.display_fields(product, a, coarse.view, params)
    fr = df["forest_rgb"][df["forest"] > 0.9]
    assert fr.shape[0] > 500
    assert fr.std(axis=0).max() > 3.0
    assert np.isfinite(df["biome_rgb"]).all() and np.isfinite(df["forest_rgb"]).all()


def test_legend_and_provenance_say_approximate(product, coarse):
    rows = atlas.legend_rows(coarse)
    kinds = [r[0] for r in rows]
    assert "biome" in kinds and "forest_area" in kinds
    assert "非气候" in dict((r[0], r[2]) for r in rows)["biome"]
    prov = atlas.provenance(product, coarse, coarse.params, {})
    approx = " ".join(prov["layers"]["approximate"])
    assert "近似群系" in approx and "不是气候" in approx and "林型分色" in approx
    assert atlas.summarize(coarse)["biome_paint"] is True
    html = atlas.compose_html(coarse, product, "base.png")
    assert "近似群系" in html and html.rstrip().endswith("</html>")
