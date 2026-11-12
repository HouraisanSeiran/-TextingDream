"""大尺度总览的海岸装饰：小岛不拖大光晕，大陆/大岛保持原波纹（显示层，数据不动）。

每像素≥ 2000 m 的总览里，一座真岛可能只占几个像素，而第二道岸线与波纹环伸到十几像素外，
看起来像一座空海域里的大光晕。本文件验证：
* 门控只看陆地连通分量占多少**输出像素**，不是固定物理面积；
* 小岛只丢掉 secondline/ripples，ink 描边与真实陆地色逐字节不变，岛仍存在，不删岛也不扩岛；
* 大陆与大岛保留原岸纹；
* 小图（每像素 < coast_deco_mpp）逐位保持原结果；
* 全海/全陆安全，输出确定且输入不被修改。

不生成地形、不开浏览器、不用 GPU：产品是测试自己 tmp 目录里的极小合成 world-relief 产品。
"""
import dataclasses

import numpy as np
from scipy import ndimage as nd

from app.map_render import load_styles
from app.world_relief import atlas
from tests.test_world_relief_atlas import _write_product

GATE_OFF = 1e9  # 阈值抬到不可能达到 = 无门控的旧画法
ISLAND_PX = (3, 3)


def _style():
    return load_styles()["styles"]["simple"]


def _coarse_view():
    # 200 格 x 1000 m / 100 px = 2000 m/px，高 75 px
    return atlas.View(0, 0, 150, 200, 100, 1000.0)


def _small_view():
    # 200 格 x 1000 m / 800 px = 250 m/px
    return atlas.View(0, 0, 150, 200, 800, 1000.0)


def _params(**overrides):
    # This suite checks the optional legacy ripple gate; default ring-free style has its own tests.
    base = dict(width_px=100, river_spacing_px=20.0, coast_ripples=True)
    base.update(overrides)
    return atlas.AtlasParams(**base)


def _fields(p, params, view):
    return atlas.display_fields(p, atlas.analyse(p, params), view, params)


def _owner(labels, land):
    """每个像素最近陆地分量的标签（sea 与 land 都能得到自己的归属分量）。"""
    _, (iz, ix) = nd.distance_transform_edt(~land, return_indices=True)
    return labels[iz, ix]


def _with_tiny_island(p, params, view):
    """在远离大陆的海面上放一个 3x3 的真实陆地连通分量。"""
    df = dict(_fields(p, params, view))
    H, W = view.height, view.width
    z0, x0 = H // 5, int(0.62 * W)
    df["coast"] = np.array(df["coast"], dtype=float, copy=True)
    df["ecol"] = np.array(df["ecol"], dtype=float, copy=True)
    df["coast"][z0:z0 + 10, x0:x0 + 10] = -6.0
    df["coast"][z0 + 3:z0 + 6, x0 + 3:x0 + 6] = 6.0
    df["ecol"][z0 + 3:z0 + 6, x0 + 3:x0 + 6] = 0.35
    island = np.zeros((H, W), bool)
    island[z0 + 3:z0 + 6, x0 + 3:x0 + 6] = True
    return df, island


def _labels_of(df):
    return nd.label(df["coast"] > 0)


# ------------------------------------------------------------ 触发条件与像素门槛


def test_gate_only_applies_to_coarse_overviews(tmp_path):
    p = atlas.load_product(_write_product(tmp_path))
    params = _params()
    coarse, small = _coarse_view(), _small_view()
    assert coarse.mpp == 2000.0 and small.mpp == 250.0
    assert atlas.coast_deco_gate(_fields(p, params, coarse), coarse, params).any()
    # 小图：整张掩码都是 True，完全走旧画法
    assert atlas.coast_deco_gate(_fields(p, params, small), small, params).all()


def test_threshold_is_output_pixel_area(tmp_path):
    p = atlas.load_product(_write_product(tmp_path))
    view, params = _coarse_view(), _params()
    df, island = _with_tiny_island(p, params, view)
    labels, _ = _labels_of(df)
    own = int(labels[island][0])
    assert island.sum() == ISLAND_PX[0] * ISLAND_PX[1] < params.coast_deco_min_land_px
    sea = (_owner(labels, df["coast"] > 0) == own) & ~island
    assert sea.any()
    # 该岛自己的海侧装饰全部关掉
    assert not atlas.coast_deco_gate(df, view, params)[sea].any()
    # 同一个像素面积、把阈值降到岛以下：同一批像素重新开启，证明判据是输出像素数
    loose = atlas.coast_deco_gate(df, view, _params(coast_deco_min_land_px=4.0))
    assert loose[sea].all()


# ------------------------------------------------------------ 小岛 / 大陆


def test_tiny_island_loses_halo_but_keeps_ink_and_land_colour(tmp_path):
    p = atlas.load_product(_write_product(tmp_path))
    view, params, style = _coarse_view(), _params(), _style()
    df, island = _with_tiny_island(p, params, view)
    gated = atlas.paint_map(p, df, view, params, style, forest=False)
    ungated = atlas.paint_map(p, df, view, dataclasses.replace(params, coast_deco_mpp=GATE_OFF), style, forest=False)
    # 岛本体逐字节不变：陆地色与 ink 描边都不受门控影响，岛不会被删
    assert np.array_equal(gated[island], ungated[island])
    assert np.all(atlas._coverage(df["coast"])[0][island] > 0.99)
    # 有变化，但只发生在海侧，且只在该岛近旁
    changed = np.any(gated != ungated, axis=-1)
    assert changed.any()
    assert not changed[island].any()
    assert not changed[~(nd.binary_dilation(island, iterations=24))].any()
    # 岛仍然可见：岛内不是纯海色（与同处海面像素有明显差异）
    ocean_band = style["ocean_bands"][-1]["color"]
    assert not np.allclose(gated[island], atlas.hex_rgb(ocean_band), atol=1.0)


def test_mainland_and_large_land_keep_their_ripples(tmp_path):
    p = atlas.load_product(_write_product(tmp_path))
    view, params, style = _coarse_view(), _params(), _style()
    df, island = _with_tiny_island(p, params, view)
    labels, _ = _labels_of(df)
    sizes = np.bincount(labels.ravel())
    own = int(labels[island][0])
    big = int(np.argmax(np.where(np.arange(len(sizes)) == own, -1, sizes)))
    assert sizes[big] >= params.coast_deco_min_land_px
    near_big = (_owner(labels, df["coast"] > 0) == big) & ~(labels == big)
    assert near_big.any()
    assert atlas.coast_deco_gate(df, view, params)[near_big].all()
    gated = atlas.paint_map(p, df, view, params, style, forest=False)
    ungated = atlas.paint_map(p, df, view, dataclasses.replace(params, coast_deco_mpp=GATE_OFF), style, forest=False)
    assert np.array_equal(gated[near_big], ungated[near_big])


# ------------------------------------------------------------ 旧页面 / 边界情形


def test_small_page_output_is_bit_identical(tmp_path):
    p = atlas.load_product(_write_product(tmp_path))
    view, style = _small_view(), _style()
    params = _params(width_px=800)
    df = _fields(p, params, view)
    assert atlas.coast_deco_gate(df, view, params).all()
    a = atlas.paint_map(p, df, view, params, style, forest=True)
    b = atlas.paint_map(p, df, view, dataclasses.replace(params, coast_deco_mpp=GATE_OFF), style, forest=True)
    assert np.array_equal(a, b)
    # 全 True 乘因子与全 True valid 掩码乘/与都不改变浮点数组
    second = np.asarray(df["coast"], dtype=float) * np.ones((view.height, view.width), bool)
    assert np.array_equal(second, np.asarray(df["coast"], dtype=float))


def test_all_sea_and_all_land_are_safe(tmp_path):
    p = atlas.load_product(_write_product(tmp_path))
    view, params, style = _coarse_view(), _params(), _style()
    df = dict(_fields(p, params, view))
    coast = np.asarray(df["coast"], dtype=float)
    sea = dict(df, coast=np.full_like(coast, -4.0))
    land = dict(df, coast=np.full_like(coast, 4.0))
    assert atlas.coast_deco_gate(sea, view, params).all()
    assert atlas.coast_deco_gate(land, view, params).all()
    for case in (sea, land):
        rgb = atlas.paint_map(p, case, view, params, style, forest=False)
        assert np.isfinite(rgb).all()


def test_gate_is_deterministic_and_inputs_untouched(tmp_path):
    p = atlas.load_product(_write_product(tmp_path))
    view, params, style = _coarse_view(), _params(), _style()
    df, island = _with_tiny_island(p, params, view)
    before = {key: np.asarray(value).tobytes() for key, value in df.items()}
    assert np.array_equal(atlas.coast_deco_gate(df, view, params), atlas.coast_deco_gate(df, view, params))
    assert np.array_equal(atlas.paint_map(p, df, view, params, style, forest=False),
                          atlas.paint_map(p, df, view, params, style, forest=False))
    for key, value in df.items():
        assert np.asarray(value).tobytes() == before[key]
    assert island.sum() == 9
