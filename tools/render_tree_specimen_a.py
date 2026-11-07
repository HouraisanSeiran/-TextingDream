"""Render the group-A tree specimen sheet: artifacts/tree-art/trees-a.png.

每个树种一行：所有变种并排，各以 20 px / 40 px / 96 px（显示高度）画一遍，左侧写中文名（取自 manifest.json）；
底部两块"混合林"：针叶林与阔叶林各约 60 棵、随机混排同组全部变种（固定种子，可复现）。
符号来自 app/static/map-art/map-art-trees-a.svg，内联进 HTML，再用本机 Edge 无头截图。

用法：.venv\\Scripts\\python.exe tools/render_tree_specimen_a.py [--out artifacts/tree-art]
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

SPRITE = ROOT / "app" / "static" / "map-art" / "map-art-trees-a.svg"
MANIFEST = ROOT / "app" / "static" / "map-art" / "manifest.json"
CONIFERS = ("pine", "spruce", "larch", "fir", "cedar", "cypress", "yew", "redwood")
BROADLEAVES = ("oak", "beech", "birch", "maple", "chestnut", "ash", "elm", "willow")
SIZES = (20, 40, 96)          # display height in px (viewBox 32×40 → width = h * 0.8)
PAPER = "#eadcbc"
SEED = 20261020

W = 1180
LABEL_W = 150
ROW_H = 122
FOREST_W, FOREST_H = 560, 300
DENSE_H = 180


def symbol_ids(svg_text):
    return re.findall(r'<symbol id="([^"]+)"', svg_text)


def variants_of(ids, sp):
    return [i for i in ids if i == f"tree-{sp}" or re.fullmatch(rf"tree-{sp}-v[2-4]", i)]


def use(sid, x, y, h):
    """Place symbol so its anchor (16,38 in a 32×40 box) lands on (x, y)."""
    w = h * 0.8
    s = h / 40.0
    return (f'<svg x="{x - 16 * s:.2f}" y="{y - 38 * s:.2f}" width="{w:.2f}" height="{h:.2f}" viewBox="0 0 32 40">'
            f'<use href="#{sid}"/></svg>')


def forest(rng, species, ids, ox, oy, count=60):
    pool = [i for sp in species for i in variants_of(ids, sp)]
    cols, rows = 10, 6
    cw, rh = (FOREST_W - 60) / cols, (FOREST_H - 70) / rows
    trees = []
    for r in range(rows):
        for c in range(cols):
            x = ox + 30 + (c + 0.5 + (0.5 if r % 2 else 0) - 0.25) * cw + rng.uniform(-0.35, 0.35) * cw
            y = oy + 60 + (r + 0.5) * rh + rng.uniform(-0.3, 0.3) * rh
            trees.append((y, x, rng.choice(pool), rng.uniform(26, 34)))
    trees = trees[:count]
    trees.sort()
    return "".join(use(sid, x, y, h) for y, x, sid, h in trees)


def use_m(sid, x, y, h, mirror):
    if not mirror:
        return use(sid, x, y, h)
    return f'<g transform="translate({x:.2f},0) scale(-1,1)">{use(sid, 0, y, h)}</g>'


def dense(rng, species, ids, ox, oy, w, hgt):
    """Real map usage: trees 16-20 px high, packed at ~0.6 tree width, a few mirrored."""
    pool = [i for sp in species for i in variants_of(ids, sp)]
    step = 18 * 0.8 * 0.6      # horizontal spacing: 0.6 x symbol width
    row_step = 18 * 0.5        # rows half a tree height apart, so crowns of the row behind show above
    trees = []
    row = 0
    y = oy + 22.0
    while y < oy + hgt - 4:
        x = ox + 8 + (step / 2 if row % 2 else 0)
        while x < ox + w - 8:
            trees.append((y + rng.uniform(-1.5, 1.5), x + rng.uniform(-2, 2), rng.choice(pool), rng.uniform(16, 20),
                          rng.random() < 0.25))
            x += step * rng.uniform(0.85, 1.15)
        y += row_step
        row += 1
    trees.sort()
    return "".join(use_m(sid, x, yy, h, m) for yy, x, sid, h, m in trees), len(trees)


def compose(ids, names):
    species = CONIFERS + BROADLEAVES
    parts = []
    y = 70
    for sp in species:
        vs = variants_of(ids, sp)
        base = y + ROW_H - 18
        parts.append(f'<line x1="20" y1="{base + 0.5}" x2="{W - 20}" y2="{base + 0.5}" stroke="#b9a47a" stroke-width=".6"/>')
        parts.append(f'<text x="24" y="{base - 40}" class="cn">{html.escape(names[sp])}</text>')
        parts.append(f'<text x="24" y="{base - 20}" class="en">{sp} · {len(vs)} 种形</text>')
        x = LABEL_W + 10
        for sid in vs:
            gx = x
            for h in SIZES:
                w = h * 0.8
                parts.append(use(sid, gx + w / 2, base - 2, h))
                gx += w + 14
            parts.append(f'<text x="{x}" y="{base + 13}" class="id">{sid}</text>')
            x += 255
        y += ROW_H
    rng = random.Random(SEED ^ zlib.crc32(b"tree-specimen-a"))
    fy = y + 30
    parts.append(f'<text x="24" y="{fy}" class="cn">混合林示例（每块约 60 棵，同组全部变种随机混排，高 26–34 px）</text>')
    for k, (title, group) in enumerate((("针叶林", CONIFERS), ("阔叶林", BROADLEAVES))):
        ox = 20 + k * (FOREST_W + 20)
        oy = fy + 14
        parts.append(f'<rect x="{ox}" y="{oy}" width="{FOREST_W}" height="{FOREST_H}" fill="#e3d3ae" stroke="#b9a47a"/>')
        parts.append(f'<text x="{ox + 12}" y="{oy + 24}" class="en">{title}</text>')
        parts.append(forest(rng, group, ids, ox, oy))
    dy = fy + 14 + FOREST_H + 50
    parts.append(f'<text x="24" y="{dy}" class="cn">实际用法（树高 16–20 px，间距约 0.6 树宽，同组变种随机混排，约 1/4 镜像）</text>')
    drng = random.Random(SEED ^ zlib.crc32(b"tree-specimen-a-dense"))
    for k, (title, group) in enumerate((("针叶林", CONIFERS), ("阔叶林", BROADLEAVES))):
        ox = 20 + k * (FOREST_W + 20)
        oy = dy + 24
        parts.append(f'<rect x="{ox}" y="{oy}" width="{FOREST_W}" height="{DENSE_H}" fill="#e3d3ae" stroke="#b9a47a"/>')
        body, cnt = dense(drng, group, ids, ox, oy, FOREST_W, DENSE_H)
        parts.append(body)
        parts.append(f'<text x="{ox + 4}" y="{oy - 4}" class="en">{title} · {cnt} 棵</text>')
    total_h = int(dy + 24 + DENSE_H + 30)
    return parts, total_h


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(ROOT / "artifacts" / "tree-art"))
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    sprite = SPRITE.read_text(encoding="utf-8")
    ids = symbol_ids(sprite)
    names = json.loads(MANIFEST.read_text(encoding="utf-8"))["trees"]["species"]
    parts, h = compose(ids, names)
    page = f"""<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;background:{PAPER};}}
text{{font-family:"Microsoft YaHei","SimSun",serif;fill:#3b2f22}}
.cn{{font-size:20px}} .en{{font-size:12px;fill:#6b5a44}} .id{{font-size:10px;fill:#8a7658}}
.title{{font-size:22px}}
</style></head><body>
{sprite}
<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}">
<text x="24" y="40" class="title">树木图标 · 组 A（针叶 8 种 + 阔叶 8 种）· 每组变种依次为 20 / 40 / 96 px</text>
{''.join(parts)}
</svg></body></html>"""
    build = out / "build"
    build.mkdir(exist_ok=True)
    hp = build / "trees-a.html"
    hp.write_text(page, encoding="utf-8")
    png = out / "trees-a.png"
    screenshot(find_edge(), hp, png, W, h)
    print(f"{png} {W}x{h} symbols {len(ids)}")


if __name__ == "__main__":
    main()
