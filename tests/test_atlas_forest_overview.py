"""大尺度总览的林相显示：面状林色块 + 轻冠层纹理，树只作点缀（显示层，数据不动）。

小页面（每像素 < forest_area_mpp，现有全部 1600/5000 km 图册）保持旧的单一林色调与小尺码完整林符号；
只有超大总览（如 10000 km、8333 m/px）才换成“清晰林色块 + 冠层纹理”，同一近似 forest 掩码、同一阈值。
本文件只验证显示层：不生成地形、不起浏览器、不碰 GPU，产品是测试自己 tmp 目录里的极小合成 world-relief 产品。
"""
import hashlib
import json

import numpy as np
import pytest
from scipy import ndimage as nd

from app.map_render import load_styles
from app.world_relief import atlas
from app.world_relief.source import subseed
from tests.test_world_relief_atlas import _write_product

CONIFER_RGB = atlas.hex_rgb(atlas.FOREST_CONIFER_HEX)
BROADLEAF_RGB = atlas.hex_rgb(atlas.FOREST_BROADLEAF_HEX)
FOREST = ("tree", "rock", "grass")


def _style():
    return load_styles()["styles"]["simple"]


@pytest.fixture(scope="module")
def product_dir(tmp_path_factory):
    return _write_product(tmp_path_factory.mktemp("forest-overview"))


@pytest.fixture(scope="module")
def product(product_dir):
    return atlas.load_product(product_dir)


SMALL = dict(width_px=800, river_spacing_px=20.0)          # mpp = 250 m/px: 旧的小页面路径
COARSE = dict(SMALL, forest_area_mpp=200.0)                # mpp 250 ≥ 200: 强制走超大总览路径（同一产品，便于对照）


@pytest.fixture(scope="module")
def small_layers(product):
    return atlas.build_atlas(product, atlas.AtlasParams(**SMALL))


@pytest.fixture(scope="module")
def coarse_layers(product):
    return atlas.build_atlas(product, atlas.AtlasParams(**COARSE))


def _fields(p, params, L):
    return atlas.display_fields(p, atlas.analyse(p, params), L.view, params)


# ------------------------------------------------------------ 触发条件


def test_threshold_only_catches_very_coarse_overviews(product):
    small = atlas.View(0, 0, 150, 200, 800, 1000.0)      # 250 m/px: 世界 1000 km 级别的一张总览，旧样式
    big = atlas.View(0, 0, 8000, 10000, 1200, 1000.0)    # 8333 m/px: 真 10 000 km 总览（本工程现有最大图册）
    assert small.mpp == pytest.approx(250.0)
    assert big.mpp == pytest.approx(10000 * 1000.0 / 1200.0)
    default = atlas.AtlasParams()
    assert atlas.forest_area_mode(big, default) is True
    assert atlas.forest_area_mode(small, default) is False
    assert atlas.forest_area_mode(small, atlas.AtlasParams(forest_area_mpp=200.0)) is True


def test_small_pages_keep_the_old_forest_paint(product, small_layers):
    assert small_layers.forest_paint == "tint"
    assert "forest-canopy-coarse" not in small_layers.seeds
    # 新参数只是超大总览的开关：抬到 1e6 m/px 对同一张小图毫无影响（仍是旧单一林色调）
    other = atlas.build_atlas(product, atlas.AtlasParams(**dict(SMALL, forest_area_mpp=1e6)))
    assert other.forest_paint == "tint"
    assert np.array_equal(other.page_rgb, small_layers.page_rgb)
    assert np.array_equal(other.map_rgb, small_layers.map_rgb)
    assert [(s["id"], s["box"]) for s in other.symbols] == [(s["id"], s["box"]) for s in small_layers.symbols]


# ------------------------------------------------------------ 面状林色 + 冠层纹理


def test_coarse_page_paints_forest_blocks(product, coarse_layers):
    assert coarse_layers.forest_paint == "blocks"
    params = coarse_layers.params
    df = _fields(product, params, coarse_layers)
    style = _style()
    with_tint = atlas.paint_map(product, df, coarse_layers.view, params, style, forest=True)
    without = atlas.paint_map(product, df, coarse_layers.view, params, style, forest=False)
    forest = df["forest"] > 0.9
    open_land = (~nd.binary_dilation(df["forest"] > 0.05, iterations=4)) & (df["coast"] > 0.5) \
        & (df["lake"] < -0.5) & (df["mount"] < 0.2)
    assert forest.sum() > 2000 and open_land.sum() > 2000
    # 林内：色块明显接近林色（阔叶/针叶混色），而不是底色 + 一点点透明色
    gap_in = np.abs(with_tint[forest] - without[forest]).mean()
    assert gap_in > 25.0
    # 林外空地：一点不变（冠层纹理与林色只作用于掩码内）
    assert np.array_equal(with_tint[open_land], without[open_land])
    # 色块方向：林内转向林中绿（离林色更近、红-绿差更小），非林陆地仍走高程色阶
    wood = 0.5 * (BROADLEAF_RGB + CONIFER_RGB)
    assert np.abs(with_tint[forest] - wood).mean() < np.abs(with_tint[open_land] - wood).mean() - 20.0
    rg = with_tint[..., 0] - with_tint[..., 1]
    assert rg[forest].mean() < rg[open_land].mean() - 15.0


def test_forest_blocks_use_the_conifer_split(product, coarse_layers):
    params = coarse_layers.params
    df = _fields(product, params, coarse_layers)
    con = df["conifer"] > 0.9
    brd = (df["forest"] > 0.9) & (df["conifer"] < 0.1)
    if con.sum() < 200 or brd.sum() < 200:
        pytest.skip("合成小产品没有足够的针叶/阔叶两种林型")
    style = _style()
    rgb = atlas.paint_map(product, df, coarse_layers.view, params, style, forest=True)
    # 针叶块更暗更偏青，阔叶块更亮更偏黄绿：同一掩码、两档林色
    assert rgb[brd].mean() > rgb[con].mean() + 6.0
    assert abs(BROADLEAF_RGB - CONIFER_RGB).max() > 0


def test_canopy_texture_is_world_addressed_and_deterministic(product):
    params = atlas.AtlasParams(**COARSE)
    a = atlas.View(0, 0, 100, 100, 200, 1000.0)         # 500 m/px，起点格 0
    b = atlas.View(0, 10, 100, 100, 200, 1000.0)         # 同一产品，向东平移 10 格 = 20 px
    assert a.mpp == pytest.approx(b.mpp) == pytest.approx(500.0)
    ta = atlas.forest_canopy_texture(product, a, params)
    tb = atlas.forest_canopy_texture(product, b, params)
    assert ta.shape == tb.shape == (200, 200)
    assert np.allclose(ta[:, 20:], tb[:, :180])          # 同一世界坐标 = 同一纹理（不依赖渲染顺序/视窗）
    assert not np.allclose(ta[:, :20], tb[:, :20])       # 不同世界坐标处不同
    assert -1.2 < ta.min() and ta.max() < 1.2
    assert 0.2 < float(ta.std()) < 0.8                   # 轻纹理：有明暗起伏，但不把色块打碎
    assert np.array_equal(ta, atlas.forest_canopy_texture(product, a, params))


def test_canopy_gives_local_mottle_inside_the_blocks(product, coarse_layers):
    params = coarse_layers.params
    df = _fields(product, params, coarse_layers)
    style = _style()
    flat = atlas.paint_map(product, df, coarse_layers.view, params, style, forest=True)
    smooth = atlas.paint_map(product, df, coarse_layers.view,
                             atlas.AtlasParams(**dict(COARSE, forest_canopy_contrast=0.0)), style, forest=True)
    forest = df["forest"] > 0.9
    assert forest.sum() > 2000
    assert flat[forest].std() > smooth[forest].std() + 0.5
    # 纹理是轻的：不把色块打碎成噪声
    assert np.abs(flat[forest] - smooth[forest]).mean() < 20.0


# ------------------------------------------------------------ 树缩小 / 仅点缀，草与芦苇不抢眼


def _counts(L):
    out = {}
    for s in L.symbols:
        out[s["kind"]] = out.get(s["kind"], 0) + 1
    return out


def _areas(L):
    out = {}
    for s in L.symbols:
        out[s["kind"]] = out.get(s["kind"], 0.0) + s["w"] * s["h"]
    return out


def test_trees_shrink_to_accents_on_coarse_pages(small_layers, coarse_layers):
    small, coarse = _counts(small_layers), _counts(coarse_layers)
    assert small.get("tree", 0) > 20 and coarse.get("tree", 0) > 0           # 仍有树，但只作点缀
    # 林相主体是色块：树/石/草的占图面积大幅下降（符号缩小 + 候选抽稀，即便小符号能多塞几个）
    a_small, a_coarse = _areas(small_layers), _areas(coarse_layers)
    for kind in FOREST:
        assert a_coarse.get(kind, 0.0) < 0.55 * a_small.get(kind, 1.0), kind
    # 树本身变小：中位宽度降到旧小页面的 80% 以下
    w_small = np.median([s["w"] for s in small_layers.symbols if s["kind"] == "tree"])
    w_coarse = np.median([s["w"] for s in coarse_layers.symbols if s["kind"] == "tree"])
    assert w_coarse < 0.8 * w_small
    # 芦苇 / 草不能抢过林色块
    reed = lambda L: sum(s["w"] * s["h"] for s in L.symbols if s.get("grass_kind") == "reed")  # noqa: E731
    assert reed(coarse_layers) <= reed(small_layers)
    assert coarse.get("grass", 0) <= small.get("grass", 0)


def test_forest_symbols_still_avoid_water(coarse_layers):
    H, W = coarse_layers.view.height, coarse_layers.view.width
    for s in coarse_layers.symbols:
        x0, y0, x1, y1 = atlas._irect(s["box"])
        assert 0 <= x0 and 0 <= y0 and x1 <= W and y1 <= H
        assert not coarse_layers.forbidden[y0:y1, x0:x1].any()
        assert not coarse_layers.sea[y0:y1, x0:x1].any()


# ------------------------------------------------------------ 掩码 / relief-only / 数据身份不变


def test_forest_mask_and_thresholds_are_untouched(product):
    old = atlas.AtlasParams(**SMALL)
    new = atlas.AtlasParams(**COARSE)
    a_old = atlas.analyse(product, old)
    assert np.array_equal(a_old["forest"], atlas.analyse(product, new)["forest"])
    land = int(a_old["land"].sum())
    forest = int(a_old["forest"].sum())
    assert forest > 0 and land > forest
    assert 0.0 < forest / land < 1.0
    # 阈值 / 公式参数没有被新显示开关带动
    for name in ("forest_min_m", "treeline_m", "forest_max_slope", "forest_coast_km", "forest_threshold", "conifer_m"):
        assert getattr(new, name) == getattr(old, name)


def test_relief_only_has_no_forest_in_either_mode(product, small_layers, coarse_layers):
    # 纯地形页 = paint_map(forest=False) × 纸纹；两档林相走的是同一个“无林”分支，所以逐字节相同
    for L in (small_layers, coarse_layers):
        params, m, H, W = L.params, L.margin, L.view.height, L.view.width
        df = _fields(product, params, L)
        paper = atlas.paper_texture((H + 2 * m, W + 2 * m), L.view.s, L.seeds["paper"], _style()["paper"])
        inner = paper[m:m + H, m:m + W, None]
        plain = np.clip(atlas.paint_map(product, df, L.view, params, _style(), forest=False) * inner, 0, 255).round().astype(np.uint8)
        assert np.array_equal(L.relief_rgb, plain)
        assert not np.array_equal(L.relief_rgb, L.map_rgb)      # 主图有林色块，纯地形页没有
    # 林相档不影响纯地形底图：同一张小图抬到 1e6 m/px 仍是同一个 relief_rgb
    assert np.array_equal(atlas.build_atlas(product, atlas.AtlasParams(**dict(SMALL, forest_area_mpp=1e6))).relief_rgb,
                          small_layers.relief_rgb)


def test_renders_are_deterministic_and_do_not_touch_the_source(product_dir, product, coarse_layers):
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(product_dir.iterdir())}
    manifest = json.loads((product_dir / "manifest.json").read_text(encoding="utf-8"))
    L2 = atlas.build_atlas(atlas.load_product(product_dir), atlas.AtlasParams(**COARSE))
    assert np.array_equal(coarse_layers.page_rgb, L2.page_rgb)
    assert np.array_equal(coarse_layers.relief_rgb, L2.relief_rgb)
    assert [(s["id"], s["box"]) for s in coarse_layers.symbols] == [(s["id"], s["box"]) for s in L2.symbols]
    assert coarse_layers.seeds == L2.seeds
    assert coarse_layers.seeds["forest-canopy-coarse"] == subseed(20260903, "atlas/forest-canopy-coarse")
    assert coarse_layers.seeds["forest-canopy-fine"] == subseed(20260903, "atlas/forest-canopy-fine")
    assert hashlib.sha256((product_dir / "elevation_m.npy").read_bytes()).hexdigest() == manifest["files"]["elevation_m.npy"]
    after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(product_dir.iterdir())}
    assert after == before
    assert np.array_equal(product.elevation, np.load(product_dir / "elevation_m.npy"))
    assert product.identity == atlas.load_product(product_dir).identity


def test_provenance_says_the_forest_is_approximate(product, coarse_layers, small_layers):
    summary = atlas.summarize(coarse_layers)
    assert summary["forest_paint"] == "blocks"
    assert atlas.summarize(small_layers)["forest_paint"] == "tint"
    files = {}
    prov = atlas.provenance(product, coarse_layers, coarse_layers.params, files)
    approx = " ".join(prov["layers"]["approximate"])
    assert "近似" in approx and "非气候" in approx
    assert "大面积林相" in approx
    assert prov["product"]["identity"] == product.identity
    assert prov["scale"]["metres_per_pixel"] == pytest.approx(coarse_layers.view.mpp)
    assert prov["parameters"]["forest_area_mpp"] == pytest.approx(200.0)
    small_prov = atlas.provenance(product, small_layers, small_layers.params, {})
    assert "大面积林相" not in " ".join(small_prov["layers"]["approximate"])
    assert atlas.legend_rows(coarse_layers)[-1][0] == "forest_area"
    assert all(row[0] != "forest_area" for row in atlas.legend_rows(small_layers))
    html = atlas.compose_html(coarse_layers, product, "base.png")
    assert "掩码色块" in html and html.rstrip().endswith("</html>")
