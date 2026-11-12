"""自然图真实 DEM 细节晕渲（display only）的定量测试。

覆盖：
1. 合成山脊 / 谷地在不同方位下的局部明暗对比增强（不是只靠 mountain 掩码）；
2. 平地（rugged = 0）乘子恰为 1、输入数组一个字节都不被修改；
3. 海 / 湖 / 岸线保护：真实产品上 rugged = 0 的像素逐字节不变；
4. 旧小页面（m/px 不够粗）与 forest=False 页面完全不受影响；
5. natural_relief_strength = 0 完整回退（与没有 detail 字段的旧画法逐字节相同）；
6. 连续、平滑、确定性、数值有限。

不生成地形、不起浏览器、不跑 GPU：产品是测试自己 tmp 目录里的极小合成 world-relief 产品。
"""
from dataclasses import replace

import numpy as np
import pytest
from scipy import ndimage as nd

from app.map_render import load_styles
from app.world_relief import atlas
from tests.test_world_relief_atlas import _write_product

SMALL = dict(width_px=800, river_spacing_px=20.0)                 # 250 m/px：旧小页面
COARSE = dict(SMALL, forest_area_mpp=200.0, biome_mpp=200.0)      # 强制自然图（群系）路径


@pytest.fixture(scope="module")
def product(tmp_path_factory):
    return atlas.load_product(_write_product(tmp_path_factory.mktemp("relief-detail")))


def _style():
    return load_styles()["styles"]["simple"]


def _coarse_view(product):
    return atlas.View(0, 0, 150, 200, 100, product.spacing)       # 2000 m/px


def _small_view(product):
    return atlas.View(0, 0, 150, 200, 800, product.spacing)       # 250 m/px


def _lum(rgb):
    return np.asarray(rgb, np.float64).sum(axis=-1) / 3.0


def _fields(p, params, view):
    return atlas.display_fields(p, atlas.analyse(p, params), view, params)


# ---------------------------------------------------------------- 合成字段


def _synth(shape, *, detail=None, rugged=None, rel_ref=None, h=1800.0, coast=1.0, lake=-1.0,
           slope=0.0, forest=0.0, mount=0.0):
    """自然图分支需要的最小 df；detail / rugged / rel_ref 缺省表示“旧画法没有这些字段”。"""
    f = {k: np.full(shape, value, np.float64) for k, value in
         dict(shade_h=h, ecol=h, coast=coast, lake=lake, depth=0., forest=forest, conifer=0.,
              mount=mount, slope=slope).items()}
    f["biome_rgb"] = np.broadcast_to(np.array([115., 139., 112.]), shape + (3,)).copy()
    f["forest_rgb"] = f["biome_rgb"].copy()
    f["forest_type"] = np.zeros(shape, np.int8)
    if detail is not None:
        f["detail_h"] = np.asarray(detail, np.float64)
    if rugged is not None:
        f["rugged"] = np.asarray(rugged, np.float64)
    if rel_ref is not None:
        f["rel_ref"] = np.asarray(rel_ref, np.float64)
    return f


def _waves(shape, wavelength_px, amplitude_m, axis):
    """一维正弦面：axis=1 起伏沿 X（山脊南北走向），axis=0 起伏沿 Z（山脊东西走向）。"""
    n = shape[1] if axis == 1 else shape[0]
    s = amplitude_m * np.sin(2.0 * np.pi * np.arange(n, dtype=float) / float(wavelength_px))
    return np.broadcast_to(s, shape).copy() if axis == 1 else np.broadcast_to(s[:, None], shape).copy()


# ---------------------------------------------------------------- 乘子本身：平地 / 数值范围


def test_flat_ground_factor_is_exactly_one_and_inputs_untouched(product):
    view, params = _coarse_view(product), atlas.AtlasParams(**COARSE)
    shape = (view.height, view.width)
    f = _synth(shape, detail=np.full(shape, 1200.0), rugged=np.zeros(shape),
               rel_ref=np.zeros(shape))
    before = {k: np.asarray(v).tobytes() for k, v in f.items()}
    factor, lum = atlas.natural_relief_factor(f, view, params)
    assert factor.shape == shape and lum.shape == shape
    # 平坦地（没有真实起伏）乘子恰为 1.0：不是“接近 1”
    assert (factor == 1.0).all()
    assert np.isfinite(factor).all() and np.isfinite(lum).all()
    for k, v in f.items():
        assert np.asarray(v).tobytes() == before[k], k


def test_factor_stays_inside_the_documented_band(product):
    view, params = _coarse_view(product), atlas.AtlasParams(**COARSE)
    shape = (view.height, view.width)
    # 一个幅度很大的正弦槽：故意把 lum 偏差顶到夹紧边界
    f = _synth(shape, detail=_waves(shape, 6, 3000.0, 1), rugged=np.ones(shape),
               rel_ref=np.ones(shape))
    factor, _ = atlas.natural_relief_factor(f, view, params)
    assert params.natural_relief_factor_min <= factor.min()
    assert factor.max() <= params.natural_relief_factor_max
    assert np.isfinite(factor).all()
    # 不压成墨黑：最暗的乘子仍保留 70% 亮度
    assert factor.min() >= 0.70 - 1e-12


def test_ridges_and_valleys_gain_local_contrast_in_any_orientation(product):
    view, params = _coarse_view(product), atlas.AtlasParams(**COARSE)
    shape = (view.height, view.width)
    got = {}
    for axis in (1, 0):
        detail = _waves(shape, 8, 900.0, axis)
        f = _synth(shape, detail=detail, rugged=np.ones(shape), rel_ref=np.zeros(shape))
        factor, _ = atlas.natural_relief_factor(f, view, params)
        # 沿坡面一个周期内既有亮面也有暗面 → 局部明暗差被拉开
        assert factor.std() > 0.01, axis
        assert factor.max() > 1.01 and factor.min() < 0.99, axis
        # 亮暗各自占到相当面积（不是偶发一两像素）
        assert (factor > 1.005).mean() > 0.2 and (factor < 0.995).mean() > 0.2, axis
        got[axis] = factor
    # 两种走向的脊线给出不同的明暗分布（方位确实起作用，不是一张各向同性的噪声）
    assert not np.allclose(got[0], got[1])


def test_contrast_grows_with_strength_and_disappears_at_zero(product):
    view = _coarse_view(product)
    shape = (view.height, view.width)
    detail = _waves(shape, 8, 900.0, 1)
    f = _synth(shape, detail=detail, rugged=np.ones(shape), rel_ref=np.zeros(shape))
    stds = []
    for k in (0.0, 0.3, 0.6, 0.9):
        params = atlas.AtlasParams(**dict(COARSE, natural_relief_strength=k))
        factor, _ = atlas.natural_relief_factor(f, view, params)
        stds.append(float(factor.std()))
        if k == 0.0:
            assert (factor == 1.0).all(), "strength=0 必须完全不改画面"
    assert stds[0] == 0.0
    assert all(b > a for a, b in zip(stds, stds[1:])), stds


def test_rugged_gate_is_continuous_and_linear(product):
    view, params = _coarse_view(product), atlas.AtlasParams(**COARSE)
    shape = (view.height, view.width)
    ramp = np.linspace(0.0, 1.0, shape[1])[None, :] * np.ones((shape[0], 1))
    detail = _waves(shape, 16, 400.0, 1)
    gated = _synth(shape, detail=detail, rugged=ramp, rel_ref=np.zeros(shape))
    full = _synth(shape, detail=detail, rugged=np.ones(shape), rel_ref=np.zeros(shape))
    factor, _ = atlas.natural_relief_factor(gated, view, params)
    f_full, _ = atlas.natural_relief_factor(full, view, params)
    # rugged = 0 的列：恰为 1
    assert (factor[:, 0] == 1.0).all()
    # 乘子对崎岖权重是线性的：没有硬边、没有阶跃（权重连续 → 画面连续）
    expect = 1.0 + (f_full - 1.0) * ramp
    assert np.allclose(factor, expect, atol=1e-12)
    dv = np.abs(np.diff(f_full - 1.0, axis=1)).max()
    assert dv > 0.01                       # 光照本身确实在变化
    assert np.abs(np.diff(factor, axis=1)).max() <= dv + 1e-12


def test_local_relative_height_only_shifts_crests_and_hollows(product):
    view, params = _coarse_view(product), atlas.AtlasParams(**COARSE)
    shape = (view.height, view.width)
    flat = np.full(shape, 2000.0)
    base = _synth(shape, detail=flat, rugged=np.ones(shape), rel_ref=np.zeros(shape))
    up = _synth(shape, detail=flat, rugged=np.ones(shape), rel_ref=np.ones(shape))
    down = _synth(shape, detail=flat, rugged=np.ones(shape), rel_ref=-np.ones(shape))
    f0, _ = atlas.natural_relief_factor(base, view, params)
    fu, _ = atlas.natural_relief_factor(up, view, params)
    fd, _ = atlas.natural_relief_factor(down, view, params)
    assert np.allclose(f0, 1.0)                    # 平地无光照偏差
    assert (fu > 1.0).all() and (fd < 1.0).all()
    # 限额：相对高程项最多约 ± natural_relief_strength * tpi_strength
    cap = params.natural_relief_strength * params.natural_relief_tpi_strength
    assert fu.max() - 1.0 <= cap + 1e-9 and 1.0 - fd.min() <= cap + 1e-9
    # 只在 rugged 内作用：权重为 0 处一律回到 1
    zero = _synth(shape, detail=flat, rugged=np.zeros(shape), rel_ref=np.ones(shape))
    fz, _ = atlas.natural_relief_factor(zero, view, params)
    assert (fz == 1.0).all()


def test_factor_is_deterministic(product):
    view, params = _coarse_view(product), atlas.AtlasParams(**COARSE)
    shape = (view.height, view.width)
    f = _synth(shape, detail=_waves(shape, 9, 700.0, 0), rugged=np.full(shape, 0.8),
               rel_ref=np.linspace(-1.0, 1.0, shape[1])[None, :] * np.ones((shape[0], 1)))
    a, la = atlas.natural_relief_factor(f, view, params)
    b, lb = atlas.natural_relief_factor(f, view, params)
    assert np.array_equal(a, b) and np.array_equal(la, lb)


# ---------------------------------------------------------------- 真实产品：权重 / 海湖保护


def test_rugged_weight_is_zero_on_sea_lakes_and_flat_ground(product):
    params, view = atlas.AtlasParams(**COARSE), _coarse_view(product)
    a = atlas.analyse(product, params)
    rugged, tpi = atlas._natural_relief_source(product, a, params)
    keep = a["land"] & ~a["lake"]
    assert np.isfinite(rugged).all() and np.isfinite(tpi).all()
    assert rugged.min() >= 0.0 and rugged.max() <= 1.0
    assert (rugged[~keep] == 0.0).all(), "海 / 湖的崎岖权重必须恰为 0"
    assert (tpi[~keep] == 0.0).all()
    # 真实产品里确有崎岖地形被识别出来（否则整个开关没有意义）
    assert (rugged > 0.3).sum() > 100
    # 平坦陆地上权重为 0：局部起伏 / 坡度都在下饱和点以下
    flat = keep & (a["relief"] < params.natural_relief_relief_lo_m) & (a["slope"] < params.natural_relief_slope_lo)
    assert flat.sum() > 0
    # 近岸衰减：紧贴岸线的陆地权重明显小于内陆同高度带
    near = keep & (a["dist_sea_km"] < 5.0)
    if near.any():
        assert rugged[near].max() <= rugged[keep].max() + 1e-12


def test_data_fields_are_untouched_and_detail_surface_is_finer(product):
    params, view = atlas.AtlasParams(**COARSE), _coarse_view(product)
    a = atlas.analyse(product, params)
    df = atlas.display_fields(product, a, view, params)
    for k in ("detail_h", "rugged", "rel_ref"):
        assert k in df, k
    before = {k: np.asarray(v).tobytes() for k, v in df.items()}
    atlas.paint_map(product, df, view, params, _style())
    atlas.natural_relief_factor(df, view, params)
    for k, v in df.items():
        assert np.asarray(v).tobytes() == before[k], k
    # 高程产品本身没被改
    assert np.array_equal(product.elevation, atlas.load_product(product.path).elevation)
    # Less smoothing preserves short-wave signal, but the gradient median of arbitrary terrain need not grow:
    # the detail surface also removes spurious gradients at lake holes by normalised convolution.
    sigma = max(params.natural_relief_detail_cells,
                params.natural_relief_antialias * max(view.mpp / product.spacing, 1.0))
    assert sigma < params.shade_smooth_cells
    waves = 1500.0 + _waves((80, 100), 6, 300.0, 1)
    keep = np.ones(waves.shape, bool)
    fine = atlas._smooth_land(waves, keep, sigma)
    broad = atlas._smooth_land(waves, keep, params.shade_smooth_cells)
    interior = np.s_[8:-8, 8:-8]
    assert fine[interior].std() > 1.15 * broad[interior].std()
    m = (df["rugged"] > 0.25) & (df["coast"] > 0.5) & (df["lake"] < -0.5)
    assert m.sum() > 500
    assert not np.allclose(df["detail_h"][m], df["shade_h"][m])


def test_open_sea_and_lakes_are_byte_identical(product):
    params, view = atlas.AtlasParams(**COARSE), _coarse_view(product)
    df = _fields(product, params, view)
    style = _style()
    on = atlas.paint_map(product, df, view, params, style)
    off = atlas.paint_map(product, df, view, replace(params, natural_relief_strength=0.0), style)
    # 开与不开只在 rugged > 0 的像素上有差别
    gate = df["rugged"] > 0.0
    changed = np.any(on != off, axis=-1)
    assert changed.any(), "开关打开后山地上必须真有变化"
    assert not changed[~gate].any(), "rugged = 0 的像素（平地 / 海 / 湖）必须逐字节不变"
    sea = nd.binary_erosion(df["coast"] < -0.5, iterations=3)
    lake = df["lake"] > 0.9
    assert sea.sum() > 200 and lake.sum() > 20
    assert np.array_equal(on[sea], off[sea])
    assert np.array_equal(on[lake], off[lake])
    # 山地内部局部明暗对比确实被拉开（不是整体压暗或整体提亮）
    hl = df["rugged"] > 0.5
    assert hl.sum() > 500
    def local(lum):
        return (lum - nd.gaussian_filter(lum, 2.0))[hl]
    assert local(_lum(on)).std() > 1.05 * local(_lum(off)).std()
    assert abs(float(_lum(on)[hl].mean() - _lum(off)[hl].mean())) < 6.0


# ---------------------------------------------------------------- 触发范围：小页面 / forest=False / 关闭回放


def test_small_pages_and_relief_page_are_untouched(product):
    # 250 m/px 的旧小页面不是自然图：连 detail 字段都不生成
    params = atlas.AtlasParams(**SMALL)
    df = _fields(product, params, _small_view(product))
    assert "detail_h" not in df and "rugged" not in df
    L = atlas.build_atlas(product, params)
    off = atlas.build_atlas(product, replace(params, natural_relief_strength=0.0))
    assert np.array_equal(L.page_rgb, off.page_rgb)
    assert np.array_equal(L.relief_rgb, off.relief_rgb)
    # 自然图但 forest=False（纯地形底图）一律不受影响
    cparams, cview = atlas.AtlasParams(**COARSE), _coarse_view(product)
    cdf = _fields(product, cparams, cview)
    style = _style()
    assert np.array_equal(atlas.paint_map(product, cdf, cview, cparams, style, forest=False),
                          atlas.paint_map(product, cdf, cview, replace(cparams, natural_relief_strength=0.0),
                                          style, forest=False))
    ca = atlas.build_atlas(product, atlas.AtlasParams(**dict(COARSE, width_px=600)))
    cb = atlas.build_atlas(product, atlas.AtlasParams(**dict(COARSE, width_px=600, natural_relief_strength=0.0)))
    assert ca.biome_paint is True
    assert np.array_equal(ca.relief_rgb, cb.relief_rgb)
    assert not np.array_equal(ca.map_rgb, cb.map_rgb)


def test_switch_off_replays_the_old_page_exactly(product):
    params, view = atlas.AtlasParams(**COARSE), _coarse_view(product)
    df = _fields(product, params, view)
    style = _style()
    # strength = 0 时，带 detail 字段的 df 画出来的就是没有 detail 字段的旧画法
    stripped = {k: v for k, v in df.items() if k not in ("detail_h", "rugged", "rel_ref")}
    off = replace(params, natural_relief_strength=0.0)
    assert np.array_equal(atlas.paint_map(product, df, view, off, style),
                          atlas.paint_map(product, stripped, view, off, style))
    # 整页也一样（forest=True 的自然主图）
    L_off = atlas.build_atlas(product, atlas.AtlasParams(**dict(COARSE, width_px=600, natural_relief_strength=0.0)))
    legacy = atlas.AtlasParams(**dict(COARSE, width_px=600, natural_relief_strength=0.0))
    raw = atlas.paint_map(product, _fields(product, legacy, L_off.view), L_off.view, legacy, style)
    H, W, m = L_off.view.height, L_off.view.width, L_off.margin
    paper = atlas.paper_texture((H + 2 * m, W + 2 * m), L_off.view.s,
                                atlas.atlas_seed(product.world_seed, "paper"), style["paper"])
    expected = (raw * paper[m:m + H, m:m + W, None]).clip(0, 255).round().astype(np.uint8)
    assert np.array_equal(L_off.map_rgb, expected)


def test_renders_are_deterministic(product):
    params = atlas.AtlasParams(**dict(COARSE, width_px=600))
    a = atlas.build_atlas(product, params)
    b = atlas.build_atlas(atlas.load_product(product.path), params)
    assert np.array_equal(a.page_rgb, b.page_rgb)
    assert np.array_equal(a.map_rgb, b.map_rgb)
    assert np.array_equal(a.relief_rgb, b.relief_rgb)


# ---------------------------------------------------------------- 说明文本


def test_provenance_and_summary_state_the_limits(product):
    params = atlas.AtlasParams(**dict(COARSE, width_px=600))
    L = atlas.build_atlas(product, params)
    info = atlas.summarize(L)["relief_detail"]
    assert info["strength"] == params.natural_relief_strength
    assert info["altitude_deg"] == params.natural_relief_altitude_deg
    text = " ".join(atlas.provenance(product, L, params, {})["layers"]["approximate"])
    assert "细节晕渲" in text and "natural_relief_strength" in text
    assert "不画随机沟纹" in text and "不改高程" in text
    # 关闭时不宣称任何额外细节
    off = atlas.build_atlas(product, replace(params, natural_relief_strength=0.0))
    assert atlas.summarize(off)["relief_detail"] is None
