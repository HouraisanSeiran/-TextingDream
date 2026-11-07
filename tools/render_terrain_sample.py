"""Render style specimen maps of a read-only terrain source (simple / medieval hand-drawn / eastern) + icon specimen sheets.

用法：
  .venv\\Scripts\\python.exe tools/render_terrain_sample.py [--config PATH] [--width 2048] [--out artifacts/terrain-map-sample]
配置缺省读环境变量 DREAM_TERRAIN_SOURCES。只经 app/terrain_source.py 只读读取；不改地形。
底图 PNG 由 numpy/Pillow 渲染，符号/装饰/文字用 SVG 叠加（复用 map-art sprite），最后用本机 Edge 无头截图成 PNG。
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from app.map_render import (compose_html, compose_icon_sheet, layer_on, load_styles, paper_page,  # noqa: E402
                            render_map, sprite_ids)
from app.terrain_source import load_catalog  # noqa: E402

EDGE_CANDIDATES = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
)


def find_edge():
    for path in EDGE_CANDIDATES:
        if Path(path).exists():
            return path
    found = shutil.which("msedge")
    if found:
        return found
    raise SystemExit("找不到 msedge.exe（需要本机 Edge 做无头截图）")


def screenshot(edge, html_path, png_path, width, height):
    with tempfile.TemporaryDirectory(prefix="dream-edge-") as profile:
        cmd = [edge, "--headless", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
               "--no-first-run", "--disable-extensions", "--allow-file-access-from-files",
               f"--user-data-dir={profile}", "--virtual-time-budget=8000",
               f"--window-size={width},{height}", f"--screenshot={png_path}", html_path.resolve().as_uri()]
        subprocess.run(cmd, check=True, timeout=180, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    with Image.open(png_path) as img:
        if img.size != (width, height):
            raise SystemExit(f"截图尺寸不符：{img.size} != {(width, height)}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=os.environ.get("DREAM_TERRAIN_SOURCES"))
    ap.add_argument("--width", type=int, default=2048, help="显示宽度（像素）；原生 4096 → 2048 即每像素 60 m")
    ap.add_argument("--out", default=str(ROOT / "artifacts" / "terrain-map-sample"))
    ap.add_argument("--styles", nargs="*", default=["simple", "medieval", "eastern"])
    ap.add_argument("--icon-styles", nargs="*", default=["medieval", "eastern"])
    args = ap.parse_args(argv)
    if not args.config:
        raise SystemExit("需要 --config 或环境变量 DREAM_TERRAIN_SOURCES")
    out = Path(args.out)
    build = out / "build"
    if build.exists():  # keep build/ to exactly what this run needs
        shutil.rmtree(build)
    build.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    catalog = load_catalog(args.config)
    natives = [p for p in catalog.products if p.kind == "native-terrain-v3"]
    product = (natives or list(catalog.products))[0]
    x0, z0, x1, z1 = product.extent_m
    crop = product.crop(x0, z0, x1 + product.spacing_m, z1 + product.spacing_m)  # half-open → whole product
    t_load = time.perf_counter() - t0
    styles = load_styles()
    edge = find_edge()
    timings, renders = {}, {}
    for name in args.styles:
        t1 = time.perf_counter()
        res = render_map(crop, name, args.width, styles=styles)
        base = build / f"{name}-base.png"
        Image.fromarray(res.rgb).save(base, optimize=False, compress_level=6)
        gi = res.grid_info
        prov = "数据：%s %s…%s · 原生 %d×%d @ %g m → 显示 %d×%d @ %g m/px（逐 %d 点取样，仅显示） · 装饰不表示数据 · 未画：河流 湖面 城镇 道路 群系（缺数据）" % (
            product.kind, product.identity[:8], product.identity[-5:], gi["source_shape_zx"][1], gi["source_shape_zx"][0],
            gi["source_spacing_m"], res.map_size[0], res.map_size[1], gi["m_per_px"], gi["factor"])
        html_path = build / f"{name}.html"
        html_path.write_text(compose_html(res, base.name, prov, styles=styles), encoding="utf-8")
        t2 = time.perf_counter()
        page_h, page_w = res.rgb.shape[:2]
        screenshot(edge, html_path, out / f"{name}.png", page_w, page_h)
        t3 = time.perf_counter()
        timings[name] = dict(raster_s=round(t2 - t1, 2), browser_s=round(t3 - t2, 2), total_s=round(t3 - t1, 2))
        renders[name] = res
        print(f"{name}: {out / (name + '.png')} {page_w}x{page_h} raster {t2 - t1:.1f}s browser {t3 - t2:.1f}s "
              f"symbols {len(res.symbols)} decorations {[d['name'] for d in res.decorations]} skipped {res.skipped_decorations}")
    icon_sheets = {}
    for name in args.icon_styles:
        t1 = time.perf_counter()
        st = styles["styles"][name]
        html_text, (iw, ih) = compose_icon_sheet(name, styles=styles, base_href=f"icons-{name}-paper.png")
        Image.fromarray(paper_page(st, iw, ih, iw / float(styles["reference_px"]))).save(build / f"icons-{name}-paper.png")
        hp = build / f"icons-{name}.html"
        hp.write_text(html_text, encoding="utf-8")
        screenshot(edge, hp, out / f"icons-{name}.png", iw, ih)
        icon_sheets[name] = {"output": f"icons-{name}.png", "page_px": [iw, ih], "sprite": st["icon_sprite"],
                             "symbol_ids": sprite_ids((ROOT / "app" / "static" / "map-art" / st["icon_sprite"]).read_text(encoding="utf-8")),
                             "race_towns": st.get("race_towns"), "timing_s": round(time.perf_counter() - t1, 2)}
        print(f"icons-{name}: {out / ('icons-' + name + '.png')} {iw}x{ih}")
    any_res = next(iter(renders.values()))
    gi = any_res.grid_info
    summary = {
        "generated_by": "tools/render_terrain_sample.py",
        "source": {k: (list(v) if isinstance(v, tuple) else v) for k, v in product.provenance().items()},
        "crop": {"extent_m": [x0, z0, x1, z1], "first_sample_xz_m": list(crop["first_sample_xz_m"]),
                 "shape_zx": list(crop["shape_zx"]), "complete": crop["complete"],
                 "size_km": [crop["shape_zx"][1] * crop["spacing_m"] / 1000, crop["shape_zx"][0] * crop["spacing_m"] / 1000]},
        "status_counts_display": any_res.status_counts,
        "resolution": {"source_spacing_m": gi["source_spacing_m"], "source_shape_zx": list(gi["source_shape_zx"]),
                       "display_shape_zx": list(gi["display_shape_zx"]), "display_m_per_px": gi["m_per_px"],
                       "downsample_factor": gi["factor"], "downsample": gi["downsample"],
                       "page_margin_px": any_res.margin},
        "scale_bar": any_res.scale,
        "from_data": [
            "海陆分类：status（OCEAN=3 海、CLOSED_BELOW_SEA=4 内陆洼地≠海、LAND=5 陆地、UNKNOWN=2 未知），逐像素取原生样点",
            "陆地海拔分层设色、海洋水深分层设色（bed_m：床面，不是水面）",
            "山体阴影/水墨晕染：由高程计算（f×f 块均值，仅用于明暗）",
            "山峰/雪峰/丘陵符号（仅 simple）：局部起伏阈值 + 局部极大（manifest dem_hints）",
            "低平湿洼符号（仅 simple）：坡度近零的低洼陆地，属近似（无湿地/群系数据）",
            "medieval / eastern 不叠地形符号，地形只由底图设色/晕渲/水墨表现",
            "高程点、水深注记（simple / medieval）：显示网格上的取样值",
            "边框坐标（km，X 东 / Z 南）与比例尺：按每像素米数换算",
        ],
        "decorative_only": [
            "纸纹、暗角、宣纸纤维、水波晕线、开阔海面淡墨水纹、苔点、铜版排线（medieval 背光坡）（仅叠加纹理）",
            "图示样张 icons-*.png：只展示符号本身，样区无城镇/道路/资源数据，未把任何图示摆到地图上",
            "海岸描边只画在海一侧像素上，不移动岸线",
            "罗盘玫瑰/指北、卷轴标题框/竖排标题、朱印、帆船/福船、海兽、祥云：制图装饰，只放在开阔海面空白处，不表示航线、生物或地名",
        ],
        "not_drawn_missing_data": {
            "rivers": "无河流中心线数据（bed_m 有刻槽但不推断河流）",
            "lakes": "无湖面高程/湖泊边界（内陆洼地只按 CLOSED_BELOW_SEA 标注，不当作湖或海）",
            "towns_roads": "无城镇/道路数据",
            "biomes_forests": "无气候/群系数据，不画森林群系",
            "place_names": "无地名；标题为中性样图文字",
        },
        "styles": {name: {"output": f"{name}.png", "page_px": [r.rgb.shape[1], r.rgb.shape[0]],
                          "label": styles["styles"][name]["label"],
                          "layers": styles["styles"][name]["layers"],
                          "terrain_symbols_drawn": layer_on(styles["styles"][name], "terrain_symbols"),
                          "icon_sprite": styles["styles"][name]["icon_sprite"],
                          "sprites_inlined": styles["styles"][name]["sprites"],
                          "decoration_symbols": styles["styles"][name].get("decoration_symbols", {}),
                          "towns": {k: styles["styles"][name]["towns"].get(k) for k in ("sprite", "pattern", "names", "capital_unique")},
                          "race_towns": styles["styles"][name].get("race_towns"),
                          "symbols": {k: sum(1 for s in r.symbols if s["kind"] == k) for k in ("snowpeak", "mountain", "hill", "marsh")},
                          "decorations": [d["name"] for d in r.decorations], "skipped_decorations": r.skipped_decorations,
                          "spot_heights": [sp["elevation_m"] for sp in r.spot_heights], "soundings": len(r.soundings),
                          "timing": timings[name]} for name, r in renders.items()},
        "icon_sheets": icon_sheets,
        "timing": {"load_and_crop_s": round(t_load, 2), "total_s": round(time.perf_counter() - t0, 2)},
    }
    (out / "sample-source.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=lambda o: o.item() if isinstance(o, np.generic) else str(o)), encoding="utf-8")
    print("total %.1fs" % (time.perf_counter() - t0))


if __name__ == "__main__":
    main()
