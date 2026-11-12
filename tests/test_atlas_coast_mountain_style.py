"""自然图的两项显示调整（只改显示层，不动数据）：

1. 海岸只留一条海陆墨线：styles.json 的海侧第二道岸线与一圈圈波纹环纹默认关闭（params.coast_ripples = False）。
   显式打开 coast_ripples 时旧画法（含 coast_deco_gate 门控）照旧可用，供兼容/测试。
   海陆覆盖、高程分档、海深与河湖都不因该开关改变。
2. 自然图山域柔和加深：仅 natural（forest=True 且 df 带 biome_rgb）页在 mountain 掩码上按平滑 mount 小幅乘性压暗，
   雪面按雪覆盖度退让、林内减力；纯地形页 / 小页面 / forest=False 一律不受影响，mount 数据不被修改。

不生成地形、不起浏览器、不跑 GPU：产品是测试自己 tmp 目录里的极小合成 world-relief 产品。
"""
from dataclasses import replace
import copy

import numpy as np
import pytest
from scipy import ndimage as nd

from app.map_render import load_styles
from app.world_relief import atlas
from tests.test_world_relief_atlas import _write_product

SMALL = dict(width_px=800, river_spacing_px=20.0)                 # 250 m/px：旧小页面
COARSE = dict(SMALL, forest_area_mpp=200.0, biome_mpp=200.0)      # 强制自然图（群系）路径
NO_TONE = dict(mount_tone_alpha=0.0)


@pytest.fixture(scope="module")
def product(tmp_path_factory):
    return atlas.load_product(_write_product(tmp_path_factory.mktemp("coast-mountain-style")))


def _style():
    return load_styles()["styles"]["simple"]


def _style_no_deco():
    """同一个 style、只把第二道岸线与环纹清零：用来证明墨线那段代码不受装饰开关影响。"""
    st = copy.deepcopy(_style())
    st["coast"]["second_line_px"] = 0
    st["coast"]["ripple_count"] = 0
    return st


def _coarse_view():
    return atlas.View(0, 0, 150, 200, 100, 1000.0)               # 2000 m/px


def _small_view():
    return atlas.View(0, 0, 150, 200, 800, 1000.0)               # 250 m/px


def _fields(p, params, view):
    return atlas.display_fields(p, atlas.analyse(p, params), view, params)


def _coast_geometry(df):
    """paint_map 内部使用的海侧距离 d 与覆盖率（与实现同式，便于对准岸线/环纹像素）。"""
    alpha, sd = atlas._coverage(df["coast"])
    sea = df["coast"] < 0
    edt = nd.gaussian_filter(nd.distance_transform_edt(sea), 1.2)
    return alpha, np.where(sd > -3.0, -sd, edt)


def _lum(rgb):
    return np.asarray(rgb, np.float64).sum(axis=-1) / 3.0


# ---------------------------------------------------------------- 海岸：默认只留墨线


@pytest.mark.parametrize("view_of", [_small_view, _coarse_view], ids=["small", "coarse"])
def test_default_keeps_one_ink_line_and_drops_the_rings(product, view_of):
    view, params, style = view_of(), atlas.AtlasParams(**SMALL), _style()
    df = _fields(product, params, view)
    ink = atlas.hex_rgb(style["coast"]["ink"])
    co = style["coast"]
    on = atlas.paint_map(product, df, view, replace(params, coast_ripples=True), style, forest=False)
    off = atlas.paint_map(product, df, view, params, style, forest=False)
    alpha, d = _coast_geometry(df)
    changed = np.any(on != off, axis=-1)
    assert changed.any(), "旧装饰开关没有生效：显式打开 coast_ripples 后画面必须与默认不同"
    # 变化只落海侧（d > 0），陆地本体一个像素都不变
    assert not changed[(d <= 0) & (alpha > 0.5)].any()
    assert np.array_equal(on[alpha > 0.999], off[alpha > 0.999])
    # 默认比旧画法更亮：环纹/第二道岸线是往海里加墨，关掉之后只能变亮或持平
    assert (off >= on - 1e-9).all()
    # 打开时确实画了东西：海侧确实被压暗（否则下面「默认没有环纹」的断言就没意义）
    ring = (d > co["ripple_start_px"] * view.s) & (d < (co["ripple_start_px"] + 3 * co["ripple_step_px"]) * view.s)
    assert ring.sum() > 20
    assert (_lum(on[ring]).mean()) < (_lum(off[ring]).mean()) - 0.5
    # 默认结果在海侧就是纯海深分档色：不再有任何环纹墨污
    band = [atlas.hex_rgb(b["color"]) for b in style["ocean_bands"]]
    near = np.isclose(off[ring][:, None, :], np.stack(band)[None, :, :], atol=1.6).any(axis=(1, 2))
    assert near.mean() > 0.6
    # 墨线仍在：岸线带上最深的像素明显深于几像素外的海面（与装饰开关无关）
    lw = style["coast"]["line_px"] * view.s
    band = (d > 0.0) & (d < lw + 1.0)
    outer = (d > 2.0) & (d < 5.0)
    assert band.sum() > 20 and outer.sum() > 20
    floor = _lum(off[outer]).min()
    ink_px = band & (_lum(off) < floor - 10.0)
    assert ink_px.any(), "默认图仍应有一条比海面色明显更深的岸线墨色"
    assert _lum(off[band]).mean() < _lum(off[outer]).mean()
    # 墨线本身与开关无关：把 styles 里的第二道岸线/环纹清零后再画（墨线那几行一字未改）
    bare = atlas.paint_map(product, df, view, params, _style_no_deco(), forest=False)
    assert np.allclose(off, bare, atol=1e-9)
    dark = off[ink_px][_lum(off[ink_px]).argmin()]
    ocean = np.stack([atlas.hex_rgb(b["color"]) for b in style["ocean_bands"]])
    # 那道线确实是把墨往海里加：最深的岸线像素比任何一档海色都深，且色相向墨色靠
    assert _lum(dark) < _lum(ocean).min() - 5.0
    assert np.abs(dark - ink).max() < np.abs(ocean.mean(axis=0) - ink).max()


def test_old_decoration_switch_is_the_only_difference(product):
    """默认参数与显式开旧装饰只差在海侧装饰上；门控函数与参数语义未动。"""
    view, params, style = _coarse_view(), atlas.AtlasParams(**SMALL), _style()
    assert atlas.AtlasParams().coast_ripples is False
    df = _fields(product, params, view)
    assert atlas.coast_deco_gate(df, view, params).any()          # 旧门控仍可用、仍按参数工作
    assert not atlas.coast_deco_gate(df, view, replace(params, coast_deco_min_land_px=1e9)).all()
    on = atlas.paint_map(product, df, view, replace(params, coast_ripples=True), style, forest=False)
    off = atlas.paint_map(product, df, view, params, style, forest=False)
    assert not np.array_equal(on, off)
    # 海深分档色（水深不同 → 不同海色）仍在：只去掉装饰，不是把海画平
    sea = nd.binary_erosion(df["coast"] < -0.5, iterations=2)
    assert sea.sum() > 200
    assert off[sea].std(axis=0).max() > 1.0


def test_rings_off_is_deterministic_and_inputs_untouched(product):
    view, params, style = _coarse_view(), atlas.AtlasParams(**SMALL), _style()
    df = _fields(product, params, view)
    before = {k: np.asarray(v).tobytes() for k, v in df.items()}
    a = atlas.paint_map(product, df, view, params, style, forest=True)
    b = atlas.paint_map(product, df, view, params, style, forest=True)
    assert np.array_equal(a, b)
    for k, v in df.items():
        assert np.asarray(v).tobytes() == before[k], k


# ---------------------------------------------------------------- 山域：自然图温和加深


def _mount_fields(shape, mount, *, forest=0.0, h=1800.0, biome=True):
    f = {k: np.full(shape, value, np.float64) for k, value in
         dict(shade_h=h, ecol=1800., coast=1., lake=-1., depth=0., forest=forest, conifer=0.,
              mount=0., slope=0.).items()}
    f["mount"] = np.asarray(mount, np.float64).copy()
    if biome:
        f["biome_rgb"] = np.broadcast_to(np.array([115., 139., 112.]), shape + (3,)).copy()
        f["forest_rgb"] = f["biome_rgb"].copy()
        f["forest_type"] = np.zeros(shape, np.int8)
    return f


def test_natural_mountains_are_darker_but_mount_is_untouched(product):
    view, params, style = atlas.View(0, 0, 40, 40, 80, product.spacing), atlas.AtlasParams(**COARSE), _style()
    shape = (view.height, view.width)
    mount = np.linspace(0.0, 1.0, shape[0])[:, None] * np.ones((1, shape[1]))
    f = _mount_fields(shape, mount)
    keep = f["mount"].copy()
    tone = atlas.paint_map(product, f, view, params, style)
    flat = atlas.paint_map(product, f, view, replace(params, **NO_TONE), style)
    assert np.array_equal(f["mount"], keep), "山色不得修改 mount 数据"
    assert params.mount_tone_alpha > 0
    top = mount > 0.9
    none = mount < 1e-9
    # mount 内亮度降低（只有压暗，不会变亮），mount=0 处逐字节不变
    assert (_lum(tone[top]).mean()) < (_lum(flat[top]).mean()) - 2.0
    assert (tone[top] <= flat[top] + 1e-9).all()
    assert np.array_equal(tone[none], flat[none])
    # 随 mount 平滑变化：逐行 mount 升高，压暗量也跟着增加（不反向、无硬边）
    rows = [int(round(v * (shape[0] - 1))) for v in (0.1, 0.3, 0.5, 0.7, 0.9)]
    deltas = [float((flat[r] - tone[r]).mean()) for r in rows]
    assert all(b >= a - 1e-6 for a, b in zip(deltas, deltas[1:]))
    assert deltas[0] < deltas[-1] and deltas[-1] > 2.0
    # 温和：深色但不到墨黑，绿色底仍读得出（树林色相不被吃掉）
    assert (_lum(tone[top]).mean()) > 0.55 * (_lum(flat[top]).mean())
    assert (tone[top][:, 1] > tone[top][:, 0]).mean() > 0.9


def test_snow_keeps_its_brightness_under_mountain_tone(product):
    view, params, style = atlas.View(0, 0, 40, 40, 80, product.spacing), atlas.AtlasParams(**COARSE), _style()
    shape = (view.height, view.width)
    mount = np.ones(shape)
    snowy = _mount_fields(shape, mount, h=6000.0)
    hill = _mount_fields(shape, mount, h=1800.0)
    d_snow = np.abs(atlas.paint_map(product, snowy, view, params, style)
                    - atlas.paint_map(product, snowy, view, replace(params, **NO_TONE), style)).mean()
    d_hill = np.abs(atlas.paint_map(product, hill, view, params, style)
                    - atlas.paint_map(product, hill, view, replace(params, **NO_TONE), style)).mean()
    assert d_hill > 1.0
    assert d_snow < 0.7 * d_hill, "雪面必须按雪覆盖度退让，不能跟山体一起压暗"
    snow_rgb = atlas.paint_map(product, snowy, view, params, style)
    assert snow_rgb.min() > 120.0, "雪色应仍然发亮可读"


def test_tone_applies_only_to_natural_pages(product):
    view, params, style = atlas.View(0, 0, 40, 40, 80, product.spacing), atlas.AtlasParams(**COARSE), _style()
    shape = (view.height, view.width)
    mount = np.ones(shape)
    params_off = replace(params, **NO_TONE)
    # 纯地形（无 biome_rgb）＝ 旧高程色 + mount_tint，新参数完全不生效
    legacy = _mount_fields(shape, mount, biome=False)
    assert np.array_equal(atlas.paint_map(product, legacy, view, params, style, forest=False),
                          atlas.paint_map(product, legacy, view, params_off, style, forest=False))
    # 自然图但 forest=False（纯地形底图 / relief_only）也不受山色影响
    natural = _mount_fields(shape, mount)
    assert np.array_equal(atlas.paint_map(product, natural, view, params, style, forest=False),
                          atlas.paint_map(product, natural, view, params_off, style, forest=False))
    # 自然主图（forest=True）才有差别
    assert not np.array_equal(atlas.paint_map(product, natural, view, params, style, forest=True),
                              atlas.paint_map(product, natural, view, params_off, style, forest=True))
    # 纯地形页整页不变（build_atlas 的 relief_rgb 走 forest=False）
    a = atlas.build_atlas(product, atlas.AtlasParams(**dict(COARSE, width_px=600)))
    b = atlas.build_atlas(product, atlas.AtlasParams(**dict(COARSE, width_px=600, **NO_TONE)))
    assert a.biome_paint is True
    assert np.array_equal(a.relief_rgb, b.relief_rgb)
    assert not np.array_equal(a.map_rgb, b.map_rgb)


def test_forest_stands_stay_readable_under_the_tone(product):
    view, params, style = atlas.View(0, 0, 40, 40, 80, product.spacing), atlas.AtlasParams(**COARSE), _style()
    shape = (view.height, view.width)
    mount = np.ones(shape)
    open_land = _mount_fields(shape, mount, forest=0.0)
    wooded = _mount_fields(shape, mount, forest=1.0)
    d_open = float((atlas.paint_map(product, open_land, view, replace(params, **NO_TONE), style)
                    - atlas.paint_map(product, open_land, view, params, style)).mean())
    d_wood = float((atlas.paint_map(product, wooded, view, replace(params, **NO_TONE), style)
                    - atlas.paint_map(product, wooded, view, params, style)).mean())
    assert d_open > d_wood > 0.0, "林内应减力，避免林色块被山色压暗到分不清"


def test_provenance_and_legend_state_the_new_display_choices(product):
    params = atlas.AtlasParams(**COARSE)
    L = atlas.build_atlas(product, params)
    prov = atlas.provenance(product, L, params, {})
    approx = " ".join(prov["layers"]["approximate"])
    assert "山域加深" in approx and "显示近似" in approx
    assert "海岸线" in approx and "coast_ripples" in approx
    assert "第二道岸线" in approx and "墨线" in approx
    assert prov["parameters"]["coast_ripples"] is False
    assert prov["parameters"]["mount_tone_alpha"] > 0
    html = atlas.compose_html(L, product, "base.png")
    assert html.rstrip().endswith("</html>")
