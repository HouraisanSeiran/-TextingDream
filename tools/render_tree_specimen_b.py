"""树木图示 B 组样张：每个树种一行，全部变种在 20/40/96 px 下各画一遍；末尾三块混合林示例。

用法：.venv\\Scripts\\python.exe tools/render_tree_specimen_b.py [--out artifacts/tree-art]
读 app/static/map-art/map-art-trees-b.svg 与 manifest.json（只读），拼 HTML，用本机 Edge 无头截图
（截图做法同 tools/render_terrain_sample.py 的 find_edge/screenshot）。混合林随机排布用固定种子。
"""
from __future__ import annotations

import argparse
import json
import random
import re
import shutil
import subprocess
import tempfile
import zlib
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "app" / "static" / "map-art"
SPRITE = ART / "map-art-trees-b.svg"
MANIFEST = ART / "manifest.json"
SPECIES = ["teak", "bamboo", "kapok", "acacia", "mangrove", "olive", "palm", "baobab", "joshua", "cactus",
           "dragonblood", "cherry", "silverleaf", "gloomwood", "mushroom", "crystal"]
SIZES = (20, 40, 96)
COMPARE = ["teak", "kapok", "dragonblood", "acacia", "olive"]
MIX_SEED = zlib.crc32(b"tree-specimen-b/mix")  # 固定种子：稳定名称派生
EDGE_CANDIDATES = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
)
MIXES = [
    ("热带林", "#93ad7a", {"kapok": 0.4, "teak": 0.2, "bamboo": 0.15, "palm": 0.15, "mangrove": 0.1}),
    ("干旱稀树", "#dac98a", {"acacia": 0.5, "baobab": 0.22, "dragonblood": 0.1, "joshua": 0.08, "cactus": 0.1}),
    ("奇幻古林", "#98ae81", {"silverleaf": 0.4, "gloomwood": 0.2, "mushroom": 0.2, "crystal": 0.2}),
]


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


def variants(ids, sp):
    pat = re.compile(rf"^tree-{sp}(-v[2-5])?$")
    return sorted((i for i in ids if pat.match(i)), key=lambda i: (len(i), i))


def use(sid, x, y, h):
    """把锚点 (16,38) 放在 (x,y)，显示高度 h。"""
    w = h * 0.8
    return (f'<use href="#{sid}" x="{x - w / 2:.1f}" y="{y - h * 38 / 40:.1f}" '
            f'width="{w:.1f}" height="{h:.1f}"/>')


def mix_block(ox, oy, w, h, title, fill, weights, rng, ids, count=40):
    parts = [f'<rect x="{ox}" y="{oy}" width="{w}" height="{h}" fill="{fill}" stroke="#8a7350" stroke-width="1"/>',
             f'<text x="{ox + 8}" y="{oy + 20}" class="t">{title}</text>']
    cols, rows = 8, 5
    pts = []
    for i in range(cols * rows):
        c, r = i % cols, i // cols
        x = ox + 22 + (c + 0.5 + rng.uniform(-0.42, 0.42)) * (w - 44) / cols
        y = oy + 58 + (r + 0.5 + rng.uniform(-0.4, 0.4)) * (h - 70) / rows
        pts.append((x, y))
    pts = pts[:count]
    names, wts = zip(*weights.items())
    trees = []
    for x, y in pts:
        sp = rng.choices(names, wts)[0]
        trees.append((y, x, rng.choice(variants(ids, sp)), rng.uniform(22, 38)))
    for y, x, sid, sz in sorted(trees):
        parts.append(use(sid, x, y, sz))
    return parts


def build_html(sprite_text, names):
    ids = re.findall(r'<symbol id="([^"]+)"', sprite_text)
    width, label_w, gap = 1180, 170, 14
    row_h = 112
    body = []
    y = 40
    body.append('<text x="20" y="26" class="h">织梦 · 树木图示 B 组（暖带/特殊/奇幻）· 20 px / 40 px / 96 px</text>')
    for sp in SPECIES:
        vs = variants(ids, sp)
        base = y + row_h - 10
        body.append(f'<line x1="10" y1="{y + row_h}" x2="{width - 10}" y2="{y + row_h}" stroke="#c9b48e" stroke-width=".6"/>')
        body.append(f'<text x="20" y="{y + row_h / 2 + 4}" class="t">{names.get(sp, sp)}</text>')
        body.append(f'<text x="20" y="{y + row_h / 2 + 20}" class="s">{sp} ×{len(vs)}</text>')
        x = label_w
        for size in SIZES:
            w = size * 0.8
            for sid in vs:
                body.append(use(sid, x + w / 2, base, size))
                x += w + gap * (0.6 if size == 20 else 1)
            x += 36
        y += row_h
    # 相近树种对比：20 px（地图实际尺寸）并排，下方 40 px 参照
    body.append(f'<text x="20" y="{y + 26}" class="t">相近树种 20 px 并排对比</text>')
    body.append(f'<text x="20" y="{y + 44}" class="s">上：20 px　下：40 px</text>')
    x = label_w
    for sp in COMPARE:
        vs = variants(ids, sp)
        x0 = x
        for sid in vs:
            body.append(use(sid, x + 8, y + 50, 20))
            x += 22
        xb = x0
        for sid in vs:
            body.append(use(sid, xb + 16, y + 100, 40))
            xb += 36
        body.append(f'<text x="{x0}" y="{y + 118}" class="s">{names.get(sp, sp).split("（")[0]}</text>')
        x = max(x, xb) + 40
    y += 130
    body.append(f'<line x1="10" y1="{y}" x2="{width - 10}" y2="{y}" stroke="#c9b48e" stroke-width=".6"/>')
    y += 20
    rng = random.Random(MIX_SEED)
    bw = (width - 40 - 2 * 16) // 3
    bh = 280
    for i, (title, fill, weights) in enumerate(MIXES):
        body.extend(mix_block(20 + i * (bw + 16), y, bw, bh, title, fill, weights, rng, ids))
    height = int(y + bh + 20)
    html = f"""<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;background:#ede0c0}} svg.sheet{{display:block}}
.h{{font:600 17px 'Microsoft YaHei',sans-serif;fill:#3b2f22}} .t{{font:600 15px 'Microsoft YaHei',sans-serif;fill:#3b2f22}}
.s{{font:12px Consolas,monospace;fill:#6b5a44}}
</style></head><body>{sprite_text}
<svg class="sheet" xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="{width}" height="{height}" fill="#ede0c0"/>
{chr(10).join(body)}
</svg></body></html>"""
    return html, width, height


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(ROOT / "artifacts" / "tree-art"))
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    names = dict(manifest["trees"]["species"])
    names.update({k: v for k, v in manifest["trees"]["fantasy_species"].items() if k != "note"})
    sprite_text = SPRITE.read_text(encoding="utf-8")
    sprite_text = re.sub(r"<!--.*?-->", "", sprite_text, flags=re.S)
    html, width, height = build_html(sprite_text, names)
    html_path = out / "trees-b.html"
    html_path.write_text(html, encoding="utf-8")
    png = out / "trees-b.png"
    screenshot(find_edge(), html_path, png, width, height)
    print(f"wrote {png} ({width}x{height})")


if __name__ == "__main__":
    main()
