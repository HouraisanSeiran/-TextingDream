"""Render the simple-style atlas of a frozen world-relief product (display only; data unchanged).

用法：
  .venv\\Scripts\\python.exe tools/render_world_relief_atlas.py [--product artifacts/world-relief-pilot | --config catalog.json]
        [--out artifacts/world-relief-pilot/atlas] [--width 2400] [--reserved reserved.json] [--fantasy fantasy.json]
        [--overview-only]
数据一律经统一接口 app.map_source 读取（--config = MapCatalog.from_config，取其中 kind=world-relief-pilot 的源；
--product = load_source("world-relief-pilot", path)）。
产出 simple-atlas.png（河、山、林石草混排、装饰）、relief-only.png（无任何符号/装饰/河线的对照底图）、
detail-*.png（局部放大）、reserved-demo.png（林区局部：圆形空地 + 道路带）、atlas-source.json（产品身份、尺度、各层来源、
与旧版直读 npy/rivers.json 的一致性对比）。
--overview-only：只出 simple-atlas.png / relief-only.png / atlas-source.json（快档，推荐配 --width 1200），
跳过 detail-*.png / reserved-demo / reserved-compare 多页渲染与重复的 analyse，并跳过旧 PNG 像素对比的额外重建；
不加该开关时仍是完整图册（行为不变）。atlas-source.json 记录 overview_only / width / elapsed_seconds。
底图 numpy 绘制，符号/装饰/文字为 SVG（复用 map-art sprite），本机 Edge 无头截图成 PNG。
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from app.world_relief import atlas  # noqa: E402
from render_terrain_sample import find_edge, screenshot  # noqa: E402


def detail_views(p, a, params, width):
    """Two 400 x 300 km windows: the most rugged mountain belt and the densest large-river lowland (chosen from data)."""
    from scipy import ndimage as nd
    sp = p.spacing
    nz, nx = int(round(300000 / sp)), int(round(400000 / sp))
    big = int(round(40000 / sp))
    mountain = nd.uniform_filter(a["mountain"].astype(float), (nz // 2, nx // 2))
    rivers = nd.uniform_filter(((p.area_m2 / 1e6 > 2000) & ~p.ocean & ~a["mountain"]).astype(float), (nz // 2, nx // 2))
    land = nd.uniform_filter((~p.ocean).astype(float), (nz, nx))
    views = []
    for name, score in (("mountains", mountain * (land > 0.55)), ("rivers", rivers * (land > 0.55))):
        sc = score.copy()
        sc[:nz // 2 + big], sc[-(nz // 2) - 1:], sc[:, :nx // 2 + 1], sc[:, -(nx // 2) - 1:] = 0, 0, 0, 0
        for v in views:
            sc[max(0, v.z0 - nz // 2):v.z0 + nz + nz // 2, max(0, v.x0 - nx // 2):v.x0 + nx + nx // 2] *= 0.0
        cz, cx = np.unravel_index(int(np.argmax(sc)), sc.shape)
        z0 = int(min(max(cz - nz // 2, 0), p.shape[0] - nz))
        x0 = int(min(max(cx - nx // 2, 0), p.shape[1] - nx))
        views.append(atlas.View(z0, x0, nz, nx, width, sp))
    return list(zip(("mountains", "rivers"), views))


def forest_view(p, a, width, km=(160, 110)):
    """A window (160 x 110 km) with the densest inland forest, for the reserved-clearing demo."""
    from scipy import ndimage as nd
    sp = p.spacing
    nz, nx = int(round(km[1] * 1000 / sp)), int(round(km[0] * 1000 / sp))
    dens = nd.uniform_filter(a["forest"].astype(float), (nz, nx)) * (nd.uniform_filter((~p.ocean).astype(float), (nz, nx)) > 0.97)
    dens *= 1.0 - nd.uniform_filter(a["lake"].astype(float) * 10.0, (nz, nx)).clip(0, 1)
    dens[:nz // 2], dens[-(nz // 2):], dens[:, :nx // 2], dens[:, -(nx // 2):] = 0, 0, 0, 0
    cz, cx = np.unravel_index(int(np.argmax(dens)), dens.shape)
    z0 = int(min(max(cz - nz // 2, 0), p.shape[0] - nz))
    x0 = int(min(max(cx - nx // 2, 0), p.shape[1] - nx))
    return atlas.View(z0, x0, nz, nx, width, sp)


def reserved_demo_items(p, view, forest=None):
    """Circle clearing + road band + polygon (metres, X east / Z south).

    Anchors are snapped to the densest forest nearby (`forest` = bool grid of the window's cells) so that the
    clearings cut into woodland instead of sitting on a natural plain."""
    from scipy import ndimage as nd
    sp, mpp = p.spacing, view.mpp
    ex = p.first[0] - sp / 2 + view.x0 * sp
    ez = p.first[1] - sp / 2 + view.z0 * sp
    W, H = view.width * mpp, view.height * mpp
    dens = None
    if forest is not None:
        dens = nd.uniform_filter(np.asarray(forest, float), (max(3, view.nz // 10), max(3, view.nx // 10)))

    def snap(fx, fz, rad=0.12):
        if dens is None:
            return ex + fx * W, ez + fz * H
        z0, z1 = int(max(0, (fz - rad) * view.nz)), int(min(view.nz, (fz + rad) * view.nz))
        x0, x1 = int(max(0, (fx - rad) * view.nx)), int(min(view.nx, (fx + rad) * view.nx))
        sub = dens[z0:z1, x0:x1]
        iz, ix = np.unravel_index(int(np.argmax(sub)), sub.shape)
        return ex + (x0 + ix + 0.5) * sp, ez + (z0 + iz + 0.5) * sp

    cx, cz = snap(0.30, 0.45)
    road = [list(snap(f, g, 0.06)) for f, g in ((0.03, 0.80), (0.30, 0.78), (0.55, 0.60), (0.75, 0.35), (0.97, 0.25))]
    poly = [list(snap(f, g, 0.03)) for f, g in ((0.62, 0.72), (0.82, 0.68), (0.80, 0.90), (0.60, 0.88))]
    return [{"type": "circle", "x": cx, "z": cz, "r": 0.10 * H},
            {"type": "polyline", "points": road, "width": 0.045 * H},
            {"type": "polygon", "points": poly}]


def outline_png(png_path, mask, margin, step=8, color=(190, 30, 30)):
    """Draw a thin dashed outline of a bool mask (map pixels) onto a rendered page; comparison image only."""
    from scipy import ndimage as nd
    im = np.asarray(Image.open(png_path).convert("RGB")).copy()
    edge = mask & ~nd.binary_erosion(mask, iterations=1)
    ys, xs = np.nonzero(edge)
    keep = ((xs + ys) // step) % 2 == 0
    ys, xs = ys[keep] + margin, xs[keep] + margin
    ok = (ys < im.shape[0]) & (xs < im.shape[1])
    for dy in (0, 1):
        for dx in (0, 1):
            im[np.minimum(ys[ok] + dy, im.shape[0] - 1), np.minimum(xs[ok] + dx, im.shape[1] - 1)] = color
    return Image.fromarray(im)


def render_page(L, p, out_png, work, edge, with_overlays=True):
    base = work / (out_png.stem + "-base.png")
    Image.fromarray(L.page_rgb).save(base)
    html_text = atlas.compose_html(L, p, base.name, with_overlays=with_overlays)
    hp = work / (out_png.stem + ".html")
    hp.write_text(html_text, encoding="utf-8")
    w, h = atlas.page_size(L)
    screenshot(edge, hp, out_png, w, h)
    return html_text


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def product_dir_from_config(config):
    cfg = json.loads(Path(config).read_text(encoding="utf-8"))
    for e in cfg["sources"]:
        if e.get("kind") == atlas.SOURCE_KIND:
            pth = Path(e["path"])
            return pth if pth.is_absolute() else Path(config).resolve().parent / pth
    raise ValueError("config has no %s source" % atlas.SOURCE_KIND)


def legacy_comparison(p, pdir, params, legacy_relief_png, L_relief_png_bytes=None, rebuild_pixels=True):
    """Compare what the unified interface returned with a direct read of the product files (comparison only).

    rebuild_pixels=False skips the two extra full atlas builds used for the old-PNG pixel diff (fast path only)."""
    pdir = Path(pdir)
    out = dict(product_dir=str(pdir))
    arrs = {}
    for name, mine in (("elevation_m", p.elevation), ("ocean_mask", p.ocean), ("inland_depression_mask", p.closed),
                       ("lake_surface_m", p.lake_surface), ("drainage_area_m2", p.area_m2)):
        f = pdir / (name + ".npy")
        if f.exists():
            old = np.load(f, allow_pickle=False)
            arrs[name] = bool(old.shape == mine.shape and np.array_equal(old.astype(mine.dtype), mine))
    out["arrays_equal"] = arrs
    rj = pdir / "rivers.json"
    if rj.exists():
        old = json.loads(rj.read_text(encoding="utf-8"))
        lines = sorted(old["lines"], key=lambda l: l["id"])
        same_pts = len(lines) == len(p.rivers) and all(
            a["id"] == b["id"] and np.array_equal(np.asarray(a["coordinates_xz_m"], float), np.asarray(b["coordinates_xz_m"], float))
            for a, b in zip(lines, p.rivers))
        out["rivers"] = dict(old_lines=len(lines), unified_lines=len(p.rivers), points_equal=bool(same_pts),
                             old_threshold_km2=float(old.get("threshold_km2", 0.0)), unified_threshold_km2=p.river_threshold_km2,
                             threshold_equal=bool(float(old.get("threshold_km2", -1)) == p.river_threshold_km2))
    if not rebuild_pixels:
        out["relief_only_vs_old_png"] = "skipped with --overview-only (no extra atlas rebuild for the old-PNG pixel diff)"
    elif legacy_relief_png is not None and Path(legacy_relief_png).exists():
        old_img = np.asarray(Image.open(legacy_relief_png).convert("RGB")).astype(int)
        legacy_params = dataclasses.replace(params, mount_tint_alpha=0.0, mount_shade_boost=0.0)
        Ll = atlas.build_atlas(p, legacy_params)
        new = np.asarray(atlas.relief_page(Ll, p)).astype(int)
        out["relief_only_vs_old_png"] = _diff(old_img, new, "new base with mountain tint/shade disabled (same code path as old base)")
        Ln = atlas.build_atlas(p, params)
        new2 = np.asarray(atlas.relief_page(Ln, p)).astype(int)
        d = _diff(old_img, new2, "new base with mountain tint + stronger shade")
        out["relief_only_new_style_vs_old_png"] = d
    else:
        out["relief_only_vs_old_png"] = "old relief-only.png not available"
    return out


def _diff(a, b, note):
    if a.shape != b.shape:
        return dict(note=note, shape_old=list(a.shape), shape_new=list(b.shape), comparable=False)
    d = np.abs(a - b).max(axis=2)
    return dict(note=note, comparable=True, pixels=int(d.size), differing_pixels=int((d > 0).sum()), max_abs_diff=int(d.max()),
                mean_abs_diff=float(np.abs(a - b).mean()), pixels_diff_gt_2=int((d > 2).sum()))


def render_overview(p, params, out, edge, work, files, t0, reserved=None, fantasy=None):
    """Simple atlas page + relief-only page (the only two PNGs needed by the quick path). Returns the layers."""
    L = atlas.build_atlas(p, params, reserved=reserved, fantasy_regions=fantasy)
    print("overview layers %.1fs" % (time.perf_counter() - t0), atlas.summarize(L)["symbols"], flush=True)
    render_page(L, p, out / "simple-atlas.png", work, edge)
    files["simple-atlas.png"] = dict(kind="atlas", summary=atlas.summarize(L))
    atlas.relief_page(L, p).save(out / "relief-only.png")
    files["relief-only.png"] = dict(kind="relief-only", note="same base raster, no forest tint, no rivers, no symbols, no decorations",
                                    map_px=[L.view.width, L.view.height])
    return L


def render_details(p, params, out, edge, work, files, t0, detail_width, reserved=None, fantasy=None):
    """Detail windows (mountain / river), forest reserved-demo page + comparison page (full atlas only)."""
    a = atlas.analyse(p, params)
    for name, view in detail_views(p, a, params, detail_width):
        D = atlas.build_atlas(p, params, view, deco_kind="detail", title="局部 · " + ("山系" if name == "mountains" else "河网"),
                              reserved=reserved, fantasy_regions=fantasy)
        fn = "detail-%s.png" % name
        render_page(D, p, out / fn, work, edge)
        files[fn] = dict(kind="detail", summary=atlas.summarize(D))
        print(fn, "%.1fs" % (time.perf_counter() - t0), flush=True)
    fv = forest_view(p, a, detail_width)
    items = reserved_demo_items(p, fv, a["forest"][fv.z0:fv.z0 + fv.nz, fv.x0:fv.x0 + fv.nx] > 0.5)
    R0 = atlas.build_atlas(p, params, fv, deco_kind="detail", title="局部 · 林区（无预留）")
    R = atlas.build_atlas(p, params, fv, deco_kind="detail", title="局部 · 预留空位演示", reserved=items)
    render_page(R, p, out / "reserved-demo.png", work, edge)
    render_page(R0, p, work / "reserved-none.png", work, edge)
    rmask = R.reserved
    left = outline_png(work / "reserved-none.png", rmask, R0.margin)
    right = outline_png(out / "reserved-demo.png", rmask, R.margin)
    cmp_img = Image.new("RGB", (left.width + right.width + 12, left.height), (255, 255, 255))
    cmp_img.paste(left, (0, 0))
    cmp_img.paste(right, (left.width + 12, 0))
    cmp_img.save(out / "reserved-compare.png")
    inside0 = int(sum(1 for q in R0.symbols if q["kind"] in ("tree", "rock", "grass")
                      and rmask[max(0, min(R.view.height - 1, int(q["y"]))), max(0, min(R.view.width - 1, int(q["x"])))]))
    inside = int(sum(1 for q in R.symbols if q["kind"] in ("tree", "rock", "grass")
                     and R.reserved[max(0, min(R.view.height - 1, int(q["y"]))), max(0, min(R.view.width - 1, int(q["x"])))]))
    files["reserved-demo.png"] = dict(kind="reserved-demo", reserved=items, window_cells_zx=[fv.z0, fv.x0, fv.nz, fv.nx],
                                      summary=atlas.summarize(R), symbols_without_reserved=atlas.summarize(R0)["symbols"],
                                       forest_symbols_with_anchor_inside_reserved=inside,
                                       forest_symbols_inside_reserved_without_reserved=inside0,
                                       compare_image="reserved-compare.png")
    print("reserved-demo.png %.1fs" % (time.perf_counter() - t0), flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--product", type=Path, default=None, help="产品目录（load_source('world-relief-pilot', path)）")
    ap.add_argument("--config", type=Path, default=None, help="MapCatalog 配置 JSON（取 kind=world-relief-pilot 的源）")
    ap.add_argument("--source-kind", choices=("world-relief-pilot", "world-map-product"), default="world-relief-pilot")
    ap.add_argument("--no-glacier-display", action="store_true", help="仅关闭已存冰体显示，不改冰物理或来源数据")
    ap.add_argument("--out", type=Path, default=None, help="默认 <product>/atlas")
    ap.add_argument("--width", type=int, default=2400)
    ap.add_argument("--detail-width", type=int, default=1600)
    ap.add_argument("--overview-only", action="store_true",
                    help="快档：只出 simple-atlas.png / relief-only.png / atlas-source.json，跳过局部页与预留演示页（推荐配 --width 1200）")
    ap.add_argument("--reserved", type=Path, default=None, help="预留空位 JSON 列表：circle / polyline / polygon（米制 X东 Z南）")
    ap.add_argument("--fantasy", type=Path, default=None, help="奇幻树种区域 JSON 列表（shape circle/polygon + species + share）")
    ap.add_argument("--legacy-relief", type=Path, default=None, help="旧 relief-only.png（对比像素差；默认读 <out>/relief-only.png 的现有版本）")
    args = ap.parse_args(argv)
    t0 = time.perf_counter()
    if args.source_kind == "world-map-product":
        if args.config is not None:
            raise ValueError("world-map-product requires explicit --product, not legacy --config")
        if args.product is None:
            raise ValueError("world-map-product requires explicit --product")
        pdir = args.product
        p = atlas.product_from_source(atlas.load_source(args.source_kind, pdir), pdir)
        origin = "product:" + str(pdir)
    elif args.config is not None:
        pdir = product_dir_from_config(args.config)
        p = atlas.load_config_product(args.config)
        origin = "config:" + str(args.config)
    else:
        pdir = args.product or (ROOT / "artifacts/world-relief-pilot")
        p = atlas.load_product(pdir)
        origin = "product:" + str(pdir)
    out = (args.out or (Path(pdir) / "atlas")).resolve()  # Edge needs an absolute screenshot path
    out.mkdir(parents=True, exist_ok=True)
    # 旧图只在显式给出且与当前产品同源时才有可比性（旧 relief-only.png 出自 world-relief-pilot-v2，不是 world-relief-pilot）
    legacy_png = args.legacy_relief
    legacy_bytes = Path(legacy_png).read_bytes() if legacy_png and Path(legacy_png).exists() else None
    reserved = json.loads(args.reserved.read_text(encoding="utf-8")) if args.reserved else None
    fantasy = json.loads(args.fantasy.read_text(encoding="utf-8")) if args.fantasy else None
    params = atlas.AtlasParams(width_px=args.width)
    if args.no_glacier_display:
        params = dataclasses.replace(params, glacier_display=False)
    print("product", p.identity, p.shape, "spacing", p.spacing, origin, flush=True)
    edge = find_edge()
    files = {}
    with tempfile.TemporaryDirectory(prefix="world-atlas-") as tmp:
        work = Path(tmp)
        L = render_overview(p, params, out, edge, work, files, t0, reserved=reserved, fantasy=fantasy)
        if not args.overview_only:
            render_details(p, params, out, edge, work, files, t0, args.detail_width, reserved=reserved, fantasy=fantasy)
    for fn in files:
        files[fn]["sha256"] = sha(out / fn)
    source = atlas.provenance(p, L, params, files, pdir)
    source["unified_interface_check"] = dict(
        origin=origin,
        **legacy_comparison(p, pdir, params, Path(legacy_png) if legacy_bytes is not None else None,
                            rebuild_pixels=not args.overview_only))
    source["overview_only"] = bool(args.overview_only)
    source["width"] = int(args.width)
    source["elapsed_seconds"] = round(time.perf_counter() - t0, 1)
    (out / "atlas-source.json").write_text(json.dumps(source, indent=2, ensure_ascii=False), encoding="utf-8")
    print("done %.1fs" % (time.perf_counter() - t0), flush=True)


if __name__ == "__main__":
    main()
