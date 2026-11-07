"""Render specimen sheets for the forest-floor grass symbols.

输出（artifacts/ground-art-sample/）：
  grass-sheet.png   每种一行，全部变种各按 1× / 2× / 4×（1× = viewBox 单位 1 px，即 14×10 px）画一遍；
  grass-forest.png  小林区示意：组 A 现有树（显示高 20–30 px）+ 草按 ground-grass.json 的 scene_weights 抽样混排。
                    上排草与树同一 px/单位（规格尺度），下排草放大 1.4 倍，便于比较。
符号来自 map-art-ground-grass.svg 与 map-art-trees-a.svg（只读），内联进 HTML，用本机 Edge 无头截图。
固定种子：random.Random(20261020 ^ crc32(名称))。

用法：.venv\\Scripts\\python.exe tools/render_ground_grass_sample.py [--out artifacts/ground-art-sample]
"""
from __future__ import annotations

import argparse
import html
import json
import random
import re
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.render_terrain_sample import find_edge, screenshot  # noqa: E402

ART = ROOT / "app" / "static" / "map-art"
GRASS_SVG = ART / "map-art-ground-grass.svg"
GRASS_JSON = ART / "ground-grass.json"
TREES_SVG = ART / "map-art-trees-a.svg"
SEED = 20261020
PAPER = "#eadcbc"
PANEL = "#e3d3ae"
CONIFERS = ("pine", "spruce", "fir", "larch")
BROADLEAVES = ("oak", "beech", "birch", "maple", "chestnut", "ash", "elm")
EDGE_TREES = ("oak", "birch", "ash", "pine")
RIPARIAN_TREES = ("willow", "ash", "elm", "birch")


def rng_for(name):
    return random.Random(SEED ^ zlib.crc32(name.encode("utf-8")))


def strip_svg(text):
    """Keep only the <symbol> elements so several sprites can share one hidden <svg>."""
    return "\n".join(re.findall(r"<symbol\b.*?</symbol>", text, flags=re.S))


def use_grass(sid, x, y, scale):
    """Anchor (7,9) of the 14×10 box lands on (x, y); scale = px per viewBox unit."""
    return (f'<svg x="{x - 7 * scale:.2f}" y="{y - 9 * scale:.2f}" width="{14 * scale:.2f}" '
            f'height="{10 * scale:.2f}" viewBox="0 0 14 10" overflow="visible"><use href="#{sid}"/></svg>')


def use_tree(sid, x, y, h):
    s = h / 40.0
    return (f'<svg x="{x - 16 * s:.2f}" y="{y - 38 * s:.2f}" width="{32 * s:.2f}" height="{h:.2f}" '
            f'viewBox="0 0 32 40" overflow="visible"><use href="#{sid}"/></svg>')


def sheet(meta):
    kinds = meta["kinds"]
    label_w, row_h, w = 150, 78, 1180
    parts, y = [], 64
    per_line = 4
    for kind, info in kinds.items():
        vs = info["variants"]
        for li in range(0, len(vs), per_line):   # wrap kinds with more than 4 variants onto extra lines
            base = y + row_h - 16
            parts.append(f'<line x1="20" y1="{base + .5}" x2="{w - 20}" y2="{base + .5}" stroke="#b9a47a" stroke-width=".6"/>')
            if li == 0:
                parts.append(f'<text x="24" y="{base - 30}" class="cn">{html.escape(info["name"])}</text>')
                parts.append(f'<text x="24" y="{base - 12}" class="en">{kind} · {len(vs)} 个变种</text>')
            x = label_w + 10
            for sid in vs[li:li + per_line]:
                gx = x
                for sc in (1, 2, 4):
                    parts.append(use_grass(sid, gx + 7 * sc, base - 1, sc))
                    gx += 14 * sc + 10
                parts.append(f'<text x="{x}" y="{base + 12}" class="id">{sid}</text>')
                x += 248  # 1×+2×+4× widths (14+28+56) + 3 gaps of 10, then 120 px between variants
            y += row_h
    h = y + 30
    title = '林下草类点缀 · 每个变种依次为 1× / 2× / 4×（1× = 14×10 px，与 40 px 高的树同一 px/单位）'
    return parts, w, h, title


def tree_pool(ids, species):
    return [i for i in ids for sp in species if i == f"tree-{sp}" or re.fullmatch(rf"tree-{sp}-v\d", i)]


def choose(rng, pool):
    ids, ws = zip(*pool)
    return rng.choices(ids, weights=ws, k=1)[0]


def grass_pool(meta, scene, *, exclude_water=False):
    out = []
    for s in meta["symbols"]:
        wv = s["scene_weights"].get(scene, 0)
        if wv <= 0:
            continue
        if exclude_water and s.get("requires_water_adjacent"):
            continue
        out.append((s["id"], wv))
    return out


def panel(rng, meta, tree_ids, kind, ox, oy, pw, ph, gscale):
    """One small forest patch. Returns list of (y, svg) so caller can z-sort by ground line."""
    items = []
    clip_top, clip_bot = oy + 34, oy + ph - 8
    if kind in ("conifer", "broadleaf"):
        trees = tree_pool(tree_ids, CONIFERS if kind == "conifer" else BROADLEAVES)
        cols, rows = 13, 6
        tree_band = (clip_top + 26, clip_bot)
        gpool = grass_pool(meta, kind)
        ngrass = 120
        gband = (clip_top + 6, clip_bot)
    elif kind == "forest_edge":
        trees = tree_pool(tree_ids, EDGE_TREES)
        cols, rows = 13, 3
        tree_band = (clip_top + 26, clip_top + (clip_bot - clip_top) * 0.5)
        gpool = grass_pool(meta, "forest_edge")
        ngrass = 130
        gband = (clip_top + 10, clip_bot)
    else:  # riparian
        trees = tree_pool(tree_ids, RIPARIAN_TREES)
        cols, rows = 12, 3
        tree_band = (clip_top + 26, clip_top + (clip_bot - clip_top) * 0.48)
        gpool = grass_pool(meta, "riparian", exclude_water=True)
        ngrass = 70
        gband = (clip_top + 10, clip_top + (clip_bot - clip_top) * 0.62)
    cw = (pw - 30) / cols
    rh = (tree_band[1] - tree_band[0]) / rows
    for r in range(rows):
        for c in range(cols):
            if rng.random() < 0.12:
                continue
            x = ox + 15 + (c + 0.5 + (0.45 if r % 2 else 0) - 0.2) * cw + rng.uniform(-.35, .35) * cw
            y = tree_band[0] + (r + 0.5) * rh + rng.uniform(-.3, .3) * rh
            h = rng.uniform(20, 30)
            items.append((y, use_tree(rng.choice(trees), x, y, h)))
    for _ in range(ngrass):
        if kind == "forest_edge":   # denser toward the meadow side
            t = rng.random() ** 0.6
            y = gband[0] + t * (gband[1] - gband[0])
        else:
            y = rng.uniform(*gband)
        x = rng.uniform(ox + 10, ox + pw - 10)
        sc = 25 / 40 * gscale * rng.uniform(0.85, 1.15)  # trees ~25 px tall → 0.625 px/unit
        items.append((y, use_grass(choose(rng, gpool), x, y, sc)))
    if kind == "riparian":
        wy = clip_top + (clip_bot - clip_top) * 0.74
        items.append((wy - 100, f'<rect x="{ox + 1}" y="{wy}" width="{pw - 2}" height="{clip_bot - wy + 7}" fill="#a9c0bc" opacity=".75"/>'
                      f'<path d="M{ox + 1} {wy} H{ox + pw - 1}" stroke="#5f8ea0" stroke-width=".8"/>'))
        rpool = [(i, w) for i, w in grass_pool(meta, "riparian") if i.startswith("grass-reed")]
        for _ in range(34):
            x = rng.uniform(ox + 10, ox + pw - 10)
            y = wy + rng.uniform(-3, 5)
            sc = 25 / 40 * gscale * rng.uniform(0.9, 1.2)
            items.append((y, use_grass(choose(rng, rpool), x, y, sc)))
    return items


def forest(meta, tree_ids):
    pw, ph = 380, 250
    w = 40 + 3 * pw + 2 * 20
    parts = []
    scenes = (("conifer", "针叶林下"), ("broadleaf", "阔叶林下"), ("forest_edge", "林缘 → 草地"))
    extra = (("riparian", "河岸林"),)
    y0 = 70
    for row, (gscale, label) in enumerate(((1.0, "草与树同一 px/单位（规格尺度）"), (1.4, "草放大 1.4 倍"))):
        oy = y0 + row * (ph + 50)
        parts.append(f'<text x="24" y="{oy - 10}" class="en">{label}</text>')
        row_scenes = scenes if row == 0 else (scenes[0], scenes[1], extra[0])
        for k, (kind, title) in enumerate(row_scenes):
            ox = 20 + k * (pw + 20)
            rng = rng_for(f"grass-forest-{kind}-{row}")
            parts.append(f'<clipPath id="clip-{row}-{k}"><rect x="{ox}" y="{oy}" width="{pw}" height="{ph}"/></clipPath>')
            parts.append(f'<rect x="{ox}" y="{oy}" width="{pw}" height="{ph}" fill="{PANEL}" stroke="#b9a47a"/>')
            items = panel(rng, meta, tree_ids, kind, ox, oy, pw, ph, gscale)
            items.sort(key=lambda t: t[0])
            parts.append(f'<g clip-path="url(#clip-{row}-{k})">' + "".join(s for _, s in items) + "</g>")
            parts.append(f'<rect x="{ox}" y="{oy}" width="{pw}" height="26" fill="{PANEL}" opacity=".85"/>')
            parts.append(f'<text x="{ox + 10}" y="{oy + 18}" class="en">{title} · 树高 20–30 px</text>')
    h = y0 + 2 * (ph + 50) - 20
    title = "林区示意 · 组 A 树 + 草类点缀（按 ground-grass.json 的 scene_weights 抽样）"
    return parts, w, h, title


def page(sprites, parts, w, h, title):
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;background:{PAPER};}}
text{{font-family:"Microsoft YaHei","SimSun",serif;fill:#3b2f22}}
.cn{{font-size:18px}} .en{{font-size:12px;fill:#6b5a44}} .id{{font-size:10px;fill:#8a7658}} .title{{font-size:20px}}
</style></head><body>
<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" style="position:absolute"><defs>
{sprites}
</defs></svg>
<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<text x="24" y="36" class="title">{html.escape(title)}</text>
{''.join(parts)}
</svg></body></html>"""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(ROOT / "artifacts" / "ground-art-sample"))
    args = ap.parse_args(argv)
    out = Path(args.out)
    build = out / "build"
    build.mkdir(parents=True, exist_ok=True)
    meta = json.loads(GRASS_JSON.read_text(encoding="utf-8"))
    grass = strip_svg(GRASS_SVG.read_text(encoding="utf-8"))
    trees_text = TREES_SVG.read_text(encoding="utf-8")
    tree_ids = re.findall(r'<symbol id="([^"]+)"', trees_text)
    edge = find_edge()
    for name, (parts, w, h, title), sprites in (
        ("grass-sheet", sheet(meta), grass),
        ("grass-forest", forest(meta, tree_ids), grass + "\n" + strip_svg(trees_text)),
    ):
        hp = build / f"{name}.html"
        hp.write_text(page(sprites, parts, w, h, title), encoding="utf-8")
        png = out / f"{name}.png"
        screenshot(edge, hp, png, w, h)
        print(f"{png} {w}x{h}")


if __name__ == "__main__":
    main()
