"""Generate forest-floor grass / understorey symbols for the atlas map.

Outputs
  app/static/map-art/map-art-ground-grass.svg   <symbol> only, id grass-{kind}-{n}
  app/static/map-art/ground-grass.json          id / viewBox / anchor / scenes / weights for the forest mixer

Style: hand-drawn copperplate with light wash, matching map-art-trees-a.svg / -b.svg.
Ink #3b2f22 is laid under the fills as one union (stroke OUTLINE) so only a thin outer line shows;
three tones per palette (dark / mid / light); light from the north-west (upper left), so blades leaning
left are lighter and the faint ground shadow is pushed east.

viewBox 0 0 14 10, ground line y = 9, anchor = bottom centre (7, 9).
Scale: same px-per-unit as the 32x40 trees (tree shown H px tall -> grass box 0.35H x 0.25H).

Deterministic: each symbol draws from random.Random(20261020 ^ crc32(symbol_id)). No time / entropy /
built-in hash. Edit this script and rerun instead of hand-editing the SVG.

Usage: .venv\\Scripts\\python.exe tools/gen_ground_grass_art.py
"""
from __future__ import annotations

import json
import math
import random
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "app" / "static" / "map-art"
OUT_SVG = ART / "map-art-ground-grass.svg"
OUT_JSON = ART / "ground-grass.json"

BASE_SEED = 20261020
INK = "#3b2f22"
VB = (14, 10)
AX, GY = 7.0, 9.0
OUTLINE = 0.8          # ink underlay stroke -> ~0.4 visible outside each fill
WATER = "#5f8ea0"

# palettes: (dark, mid, light)
GREEN = ("#4f6b35", "#6d8a42", "#93a85a")
GREEN_DK = ("#3d5830", "#56763c", "#7d9852")
GREEN_LT = ("#5c7838", "#7f9a48", "#a9bc68")
MEADOW = ("#5f7438", "#87994a", "#b3bb6e")
MEADOW_PALE = ("#6f7a3e", "#98a055", "#c2c37e")
FERN = ("#36573a", "#527a4a", "#7f9f5c")
FERN_DK = ("#2f4c34", "#466c43", "#6f9156")
FERN_LT = ("#46683c", "#6a8f4e", "#9ab768")
SHRUB = ("#44613a", "#638448", "#8faa60")
SHRUB_DK = ("#334c33", "#4b6a42", "#71905a")
SHRUB_OL = ("#555e36", "#7a8448", "#a5ad6a")
DRY = ("#8a6a3a", "#b8954f", "#d9bf7e")
DRY_GR = ("#76644a", "#a08a60", "#c8b586")
DRY_OL = ("#6a6a3a", "#928d4c", "#bdb36e")
REED = ("#55693a", "#7a8c4a", "#a7b46c")
MOSS = ("#4a6230", "#6a8438", "#98ae58")
MOSS_DK = ("#3a5430", "#55723e", "#7f985a")
MOSS_YL = ("#5f7034", "#86993e", "#b4c062")
BROWN = ("#6e4a30", "#946642", "#c0905e")
RED_CAP = ("#7d3a2a", "#9a4c36", "#c27c5c")
TAN = ("#86704a", "#b09366", "#d6bf8e")
STEM, STEM_DK = "#e6dabd", "#c4b48f"
PLUME, PLUME_DK = "#d6c596", "#b9a374"
CATTAIL, CATTAIL_LT = "#6b4a2e", "#93704a"
BELL = ("#8a7656", "#c2ae86", "#e6dcc0")       # bonnet mushroom, cream-beige
HONEY = ("#86672c", "#bf9a4c", "#ddc27e")      # honey fungus, dull yellow
BRACKET = ("#7e4a26", "#ad6c3a", "#d39a62")    # shelf fungus, muted orange-brown
PUFF = ("#b3a684", "#ddd3b6", "#f3ecda")       # puffball, off-white
LILAC = ("#665a72", "#9486a2", "#bdb1c6")      # wood blewit, pale lilac
STUMP = ("#5b4130", "#7a5a40", "#a58460")      # old root stump (bark tones of the trees)

PTS: list[tuple[float, float]] = []   # every point drawn for the current symbol (for extent / shadow)


def n(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def clampp(p):
    return (clamp(p[0], 0.3, VB[0] - 0.3), clamp(p[1], 0.3, VB[1] - 0.35))


def poly(pts, close=True) -> str:
    pts = [clampp(p) for p in pts]
    PTS.extend(pts)
    d = f"M{n(pts[0][0])} {n(pts[0][1])}L" + " ".join(f"{n(x)} {n(y)}" for x, y in pts[1:])
    return d + ("Z" if close else "")


def bez2(a, c, b, t):
    u = 1 - t
    return (u * u * a[0] + 2 * u * t * c[0] + t * t * b[0], u * u * a[1] + 2 * u * t * c[1] + t * t * b[1])


def dbez2(a, c, b, t):
    u = 1 - t
    return (2 * u * (c[0] - a[0]) + 2 * t * (b[0] - c[0]), 2 * u * (c[1] - a[1]) + 2 * t * (b[1] - c[1]))


def ribbon(a, c, b, w, profile="taper", steps=7) -> str:
    """Filled blade along the quadratic a-c-b. taper: full width at a -> 0; leaf: lens; stem: slight taper."""
    left, right = [], []
    for i in range(steps + 1):
        t = i / steps
        x, y = bez2(a, c, b, t)
        dx, dy = dbez2(a, c, b, t)
        ln = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / ln, dx / ln
        if profile == "taper":
            hw = w / 2 * (1 - t) ** 0.85
        elif profile == "leaf":
            hw = w / 2 * math.sin(math.pi * (0.08 + 0.92 * t)) ** 0.8
        else:  # stem
            hw = w / 2 * (1 - 0.6 * t)
        left.append((x + nx * hw, y + ny * hw))
        right.append((x - nx * hw, y - ny * hw))
    return poly(left + right[::-1])


def tone_for(rng, lean):
    t = 2 if lean < -0.5 else 0 if lean > 0.5 else 1
    if rng.random() < 0.18:
        t = rng.choice((0, 1, 2))
    return t


def tuft_specs(rng, cx, nb, spread, hr, fan, lean, wr=(0.7, 0.95), droop=0.0, curl=0.25):
    out = []
    for i in range(nb):
        f = ((i + 0.5) / nb) * 2 - 1 + rng.uniform(-0.12, 0.12)
        x0 = cx + f * spread / 2 + rng.uniform(-0.15, 0.15)
        h = rng.uniform(*hr) * (1 - 0.3 * abs(f))
        dx = f * fan + lean + rng.uniform(-0.35, 0.35)
        if rng.random() < droop:       # arching blade, tip falls back down
            c, b = (x0 + dx * 0.45, GY - h * 1.05), (x0 + dx * 1.25, GY - h * 0.6)
        else:
            c, b = (x0 + dx * curl, GY - h * 0.62), (x0 + dx, GY - h)
        out.append({"a": (x0, GY), "c": c, "b": b, "w": rng.uniform(*wr), "lean": dx})
    return out


class Sym:
    def __init__(self, kind, idx):
        self.kind, self.idx = kind, idx
        self.id = f"grass-{kind}-{idx}"
        self.rng = random.Random(BASE_SEED ^ zlib.crc32(self.id.encode("ascii")))
        self.under, self.ink, self.fill, self.top = [], [], [], []
        self.shadow = True
        PTS.clear()

    # --- primitives -------------------------------------------------------------------------------------
    def _shape(self, geom, color, ink=True):
        if ink:
            self.ink.append(f"<{geom}/>")
        self.fill.append(f'<{geom} fill="{color}"/>')

    def path(self, d, color, ink=True):
        self._shape(f'path d="{d}"', color, ink)

    def circle(self, x, y, r, color, ink=True):
        PTS.extend([(x - r, y - r), (x + r, y + r)])
        self._shape(f'circle cx="{n(x)}" cy="{n(y)}" r="{n(r)}"', color, ink)

    def ellipse(self, x, y, rx, ry, color, ink=True):
        PTS.extend([(x - rx, y - ry), (x + rx, y + ry)])
        self._shape(f'ellipse cx="{n(x)}" cy="{n(y)}" rx="{n(rx)}" ry="{n(ry)}"', color, ink)

    def stroke(self, d, color, w, opacity=None, layer=None):
        op = f' stroke-opacity="{opacity}"' if opacity is not None else ""
        (self.top if layer is None else layer).append(
            f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}"{op}/>')

    def line(self, d, color, w, opacity=None):
        """Stroke kept in the fill stack (drawn in order), so shapes added later can cover it."""
        op = f' stroke-opacity="{opacity}"' if opacity is not None else ""
        self.fill.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}"{op}/>')

    def dot(self, x, y, r, color, opacity=None):
        op = f' opacity="{opacity}"' if opacity is not None else ""
        self.top.append(f'<circle cx="{n(x)}" cy="{n(y)}" r="{n(r)}" fill="{color}"{op}/>')

    def draw_blades(self, specs, pal, base=True, profile="taper"):
        if base and specs:
            xs = [sp["a"][0] for sp in specs]
            self.ellipse((min(xs) + max(xs)) / 2 + 0.15, GY - 0.3, (max(xs) - min(xs)) / 2 + 0.35, 0.42, pal[0])
        for sp in specs:
            sp.setdefault("tone", tone_for(self.rng, sp["lean"]))
        for sp in sorted(specs, key=lambda q: q["tone"]):
            self.path(ribbon(sp["a"], sp["c"], sp["b"], sp["w"], sp.get("profile", profile)), pal[sp["tone"]])

    def water(self, lines):
        for x0, x1, y in lines:
            PTS.extend([(x0, y), (x1, y)])
            self.stroke(f"M{n(x0)} {n(y)}H{n(x1)}", WATER, ".45", layer=self.under)

    # --- output -----------------------------------------------------------------------------------------
    def extent(self):
        pad = OUTLINE / 2
        xs, ys = [p[0] for p in PTS], [p[1] for p in PTS]
        return [round(max(0.0, min(xs) - pad), 1), round(max(0.0, min(ys) - pad), 1),
                round(min(VB[0], max(xs) + pad), 1), round(min(VB[1], max(ys) + pad), 1)]

    def render(self):
        parts = list(self.under)
        if self.shadow:
            base = [p[0] for p in PTS if p[1] > GY - 1.5] or [p[0] for p in PTS]
            rx = clamp((max(base) - min(base)) / 2 + 0.7, 1.2, 6.0)
            cx = clamp((max(base) + min(base)) / 2 + 0.45, rx + 0.2, VB[0] - rx - 0.2)
            parts.append(f'<ellipse cx="{n(cx)}" cy="{n(GY + 0.12)}" rx="{n(rx)}" ry=".55" fill="{INK}" opacity=".18"/>')
        parts.append(f'<g fill="{INK}" stroke="{INK}" stroke-width="{OUTLINE}">{"".join(self.ink)}</g>')
        parts += self.fill + self.top
        body = "\n".join(parts)
        return (f'<symbol id="{self.id}" viewBox="0 0 {VB[0]} {VB[1]}" data-anchor="{n(AX)} {n(GY)}" '
                f'data-kind="{self.kind}"><g stroke-linejoin="round" stroke-linecap="round">\n{body}\n</g></symbol>')


# ======================================================================================================
# kinds
# ======================================================================================================
TUFT = {1: (9, 2.2, (3.0, 4.8), 2.4, 0.0, GREEN),      # standard
        2: (12, 3.6, (2.0, 3.4), 3.0, 0.2, GREEN_LT),  # wide and low
        3: (8, 1.8, (3.6, 5.6), 1.6, 1.3, GREEN_DK),   # tall, leaning east
        4: (7, 1.5, (2.4, 4.0), 2.0, -0.8, GREEN)}     # small, leaning west


def k_tuft(s, v):
    nb, sp, hr, fan, lean, pal = TUFT[v]
    s.draw_blades(tuft_specs(s.rng, AX, nb, sp, hr, fan, lean), pal)


def plume(s, top, side, k, color=(PLUME, PLUME_DK)):
    rng = s.rng
    s.path(ribbon(top, (top[0] + side * 0.1, top[1] - 0.5), (top[0] + side * 0.25, top[1] - 1.1), 0.5, "leaf", 5),
           color[0])
    for j in range(k):
        st = (top[0], top[1] + 0.25 * j)
        e = (st[0] + side * (0.8 + 0.3 * j) + rng.uniform(-0.15, 0.15), st[1] + 0.5 + 0.3 * j)
        c = (st[0] + side * 0.5, st[1] - 0.2)
        s.path(ribbon(st, c, e, 0.5, "leaf", 5), color[j % 2])


def plume_stems(s, pal, count, hr, xr=1.0, lean=(-0.8, 0.8), tones=(PLUME, PLUME_DK)):
    rng = s.rng
    for _ in range(count):
        x0 = AX + rng.uniform(-xr, xr)
        lx = rng.uniform(*lean)
        top = (x0 + lx, GY - rng.uniform(*hr))
        s.path(ribbon((x0, GY), (x0 + lx * 0.2, GY - 4.5), top, 0.45, "stem", 7), pal[1])
        plume(s, top, 1 if lx >= 0 else -1, 3, tones)


def k_tall(s, v):
    rng = s.rng
    if v == 1:    # miscanthus clump with silky plumes
        s.draw_blades(tuft_specs(rng, AX, 7, 2.0, (4.6, 6.4), 2.6, 0.2, wr=(0.6, 0.75), droop=0.35), MEADOW)
        plume_stems(s, MEADOW, 3, (6.6, 7.6))
    elif v == 2:  # wind-bent tall grass
        s.draw_blades(tuft_specs(rng, AX - 1.0, 8, 2.2, (5.5, 7.6), 1.2, 2.2, wr=(0.55, 0.7), droop=0.2,
                                 curl=0.15), MEADOW)
    elif v == 3:  # arching fountain clump
        s.draw_blades(tuft_specs(rng, AX, 10, 2.6, (4.5, 6.4), 3.6, 0.0, wr=(0.6, 0.75), droop=0.6), GREEN)
    else:         # sparse, pale, seed heads
        s.draw_blades(tuft_specs(rng, AX, 6, 2.4, (5.2, 7.4), 1.6, -0.4, wr=(0.5, 0.65), droop=0.1), MEADOW_PALE)
        plume_stems(s, MEADOW_PALE, 2, (7.0, 7.8), xr=1.4, tones=(PLUME_DK, "#a48e66"))


def frond(s, base, ang, L, pin, pal, droop=0.0):
    a = math.radians(ang)
    b = (base[0] + L * math.sin(a), base[1] - L * math.cos(a) + droop)
    c = (base[0] + L * 0.55 * math.sin(a * 0.55), base[1] - L * 0.62 * math.cos(a * 0.55))
    nodes = max(4, int(L * 1.3))
    pinnae = []
    for j in range(nodes):
        t = 0.14 + 0.82 * j / (nodes - 1)
        p = bez2(base, c, b, t)
        dx, dy = dbez2(base, c, b, t)
        ln = math.hypot(dx, dy) or 1.0
        tx, ty = dx / ln, dy / ln
        pl = pin * (1.08 - t) ** 0.75 + 0.2
        for side in (-1, 1):
            ux, uy = -ty * side, tx * side
            ex, ey = ux * 0.78 + tx * 0.62, uy * 0.78 + ty * 0.62
            e = (p[0] + ex * pl, p[1] + ey * pl + 0.12 * pl)
            cc = (p[0] + ex * pl * 0.5, p[1] + ey * pl * 0.5 - 0.05)
            tone = 2 if (ey < -0.15 or ex < -0.35) else 1
            if s.rng.random() < 0.15:
                tone -= 1
            pinnae.append((tone, ribbon(p, cc, e, 0.62 * (1 - 0.35 * t) + 0.08, "leaf", 5)))
    s.path(ribbon(base, c, b, 0.38, "stem", 8), pal[0])
    for tone, d in sorted(pinnae, key=lambda q: q[0]):
        s.path(d, pal[tone])
    s.stroke(f"M{n(base[0])} {n(base[1])}Q{n(c[0])} {n(c[1])} {n(b[0])} {n(b[1])}", INK, ".25", ".5")


FERNS = {1: ([-62, -32, -5, 25, 55], [4.6, 6.0, 6.6, 6.0, 4.8], 1.3, FERN, 0.0),
         2: ([-25, -8, 12, 30], [6.2, 7.2, 6.8, 5.6], 1.1, FERN_DK, 0.0),
         3: ([-75, -55, -30, 30, 55, 75], [4.8, 5.2, 4.2, 4.2, 5.2, 4.8], 1.15, FERN_LT, 1.2),
         4: ([-45, -15, 20, 48], [4.4, 5.4, 5.0, 4.2], 1.0, FERN_LT, 0.0)}


def fiddlehead(s, x, h, pal, side):
    top = (x + side * 0.4, GY - h)
    s.path(ribbon((x, GY), (x, GY - h * 0.7), top, 0.4, "stem", 6), pal[0])
    s.circle(top[0] + side * 0.25, top[1] + 0.1, 0.5, pal[1])
    cx, cy = top[0] + side * 0.25, top[1] + 0.1
    s.stroke(f"M{n(cx + 0.28 * side)} {n(cy + 0.1)}q{n(-0.45 * side)} .15 {n(-0.4 * side)} -.32"
             f"q{n(0.1 * side)} -.25 {n(0.32 * side)} -.05", INK, ".25", ".7")


def k_fern(s, v):
    angs, Ls, pin, pal, dr = FERNS[v]
    rng = s.rng
    order = sorted(range(len(angs)), key=lambda i: -angs[i])   # right-leaning (shadow side) first
    for i in order:
        base = (AX + angs[i] / 90 * 0.9 + rng.uniform(-0.15, 0.15), GY)
        L = Ls[i] * rng.uniform(0.94, 1.04)
        frond(s, base, angs[i] + rng.uniform(-4, 4), L, pin, pal, dr if abs(angs[i]) > 50 else 0.0)
    if v == 4:
        fiddlehead(s, AX - 0.5, 2.6, pal, -1)
        fiddlehead(s, AX + 0.9, 2.1, pal, 1)


SHRUBS = {1: (8.5, 5.0, SHRUB, False), 2: (11.0, 3.8, SHRUB_DK, False),
          3: (7.5, 4.6, SHRUB, True), 4: (6.0, 5.6, SHRUB_OL, False)}


def k_shrub(s, v):
    W, H, pal, berries = SHRUBS[v]
    rng = s.rng
    cx, bot = AX + rng.uniform(-0.2, 0.2), GY - 0.55
    for _ in range(3):   # a few stems showing under the mound (ink only)
        x = cx + rng.uniform(-W * 0.22, W * 0.22)
        d = ribbon((x, GY), (x + 0.1, GY - 0.6), (x + rng.uniform(-0.4, 0.4), bot - 1.2), 0.45, "taper", 4)
        s.ink.append(f'<path d="{d}"/>')
    r0 = clamp(H * 0.3, 1.0, 1.55)
    m = max(5, int(W / 1.25))
    clumps = []
    for k in range(m):
        th = math.pi * (k + 0.5) / m
        r = r0 * rng.uniform(0.82, 1.12)
        px = cx - (W / 2 - r) * math.cos(th) + rng.uniform(-0.2, 0.2)
        py = bot - r * 0.75 - (H - r * 1.75) * math.sin(th) ** 0.9 + rng.uniform(-0.15, 0.15)
        clumps.append((px, py, r, th))
    for _ in range(2 + int(W > 8)):
        clumps.append((cx + rng.uniform(-0.25, 0.25) * W, bot - H * rng.uniform(0.3, 0.55), r0 * 0.9,
                       rng.uniform(0.2, 0.8) * math.pi))
    s.ellipse(cx, bot - H * 0.42, W / 2 - r0 * 0.6, H * 0.42, pal[0])
    for px, py, r, _ in clumps:
        s.circle(px, py, r, pal[0])
    s.ellipse(cx - 0.35, bot - H * 0.5, max(0.8, W / 2 - r0 * 1.2), H * 0.3, pal[1], ink=False)
    for px, py, r, _ in clumps:
        s.circle(px - 0.22, py - 0.28, r * 0.74, pal[1], ink=False)
    for px, py, r, th in clumps:
        if th < 0.62 * math.pi:
            s.circle(px - 0.42, py - 0.48, r * 0.4, pal[2], ink=False)
    for px, py, r, th in clumps:
        if th > 0.5 * math.pi and rng.random() < 0.7:
            s.stroke(f"M{n(px + 0.1)} {n(py + 0.45 * r)}q{n(0.35 * r)} .1 {n(0.6 * r)} {n(-0.35 * r)}", INK, ".3", ".45")
    if berries:
        for _ in range(5):
            px, py, r, _ = rng.choice(clumps)
            bx, by = px + rng.uniform(-0.5, 0.5) * r, py + rng.uniform(-0.3, 0.5) * r
            s.dot(bx, by, 0.32, "#8e3b2c")
            s.dot(bx - 0.1, by - 0.1, 0.11, "#c9785e")


FLOWERS = {1: ("#efe6cc", "#c9a24a", 5, GREEN_LT), 2: ("#d4b24c", "#9c7a2e", 4, GREEN),
           3: ("#c48a7a", "#8e5a4e", 4, GREEN_LT), 4: ("#9096b8", "#5f6488", 4, GREEN)}


def k_flower(s, v):
    col, ctr, nfl, pal = FLOWERS[v]
    rng = s.rng
    s.draw_blades(tuft_specs(rng, AX, 8, 2.4, (2.2, 3.6), 2.4, rng.uniform(-0.3, 0.3), wr=(0.65, 0.85)), pal)
    heads = []
    for k in range(nfl):
        x0 = AX + (k / (nfl - 1) * 2 - 1) * 1.5 + rng.uniform(-0.25, 0.25)
        top = (x0 + (x0 - AX) * 0.7 + rng.uniform(-0.4, 0.4), GY - rng.uniform(3.2, 5.0))
        c = (x0 + (top[0] - x0) * 0.2, GY - 2.0)
        s.stroke(f"M{n(x0)} {n(GY - 0.3)}Q{n(c[0])} {n(c[1])} {n(top[0])} {n(top[1])}", pal[0], ".35")
        heads.append(top)
        PTS.append((top[0], top[1] - 0.6))
    for x, y in heads:
        s.top.append(f'<circle cx="{n(x)}" cy="{n(y)}" r=".55" fill="{col}" stroke="{INK}" stroke-width=".3"/>')
        if v in (1, 2):
            s.dot(x + 0.05, y + 0.05, 0.2, ctr)
        else:
            s.dot(x + 0.15, y + 0.15, 0.22, ctr, ".7")


def k_dry(s, v):
    rng = s.rng
    if v == 1:
        s.draw_blades(tuft_specs(rng, AX, 10, 2.4, (2.8, 4.6), 2.6, 0.3, droop=0.3), DRY)
    elif v == 2:   # taller, bent, with seed heads
        specs = tuft_specs(rng, AX, 8, 2.0, (4.2, 6.0), 2.0, 0.8, wr=(0.55, 0.7), droop=0.45)
        s.draw_blades(specs, DRY)
        ups = [sp for sp in specs if sp["b"][1] < GY - 4.0][:3]
        for sp in ups:
            b = sp["b"]
            c = bez2(sp["a"], sp["c"], sp["b"], 0.78)
            s.path(ribbon(c, ((c[0] + b[0]) / 2, (c[1] + b[1]) / 2), b, 0.75, "leaf", 5), "#e2cb8c")
    elif v == 3:   # sparse, broken, grey-brown
        s.draw_blades(tuft_specs(rng, AX, 7, 2.6, (1.8, 3.6), 2.8, -0.2, droop=0.5), DRY_GR)
        for _ in range(3):
            x0 = AX + rng.uniform(-2.2, 2.2)
            b = (x0 + rng.uniform(-0.3, 0.3), GY - rng.uniform(0.8, 1.3))
            s.path(ribbon((x0, GY), ((x0 + b[0]) / 2, (GY + b[1]) / 2), b, 0.6, "stem", 3), DRY_GR[1])
    else:          # olive remnants behind golden front
        back = tuft_specs(rng, AX + 0.4, 6, 2.0, (3.0, 4.4), 2.2, 0.6)
        for sp in back:
            sp["tone"] = rng.choice((0, 1))
        s.draw_blades(back, DRY_OL)
        s.draw_blades(tuft_specs(rng, AX - 0.3, 7, 2.2, (2.4, 4.0), 2.6, -0.2, droop=0.35), DRY, base=False)


def k_reed(s, v):
    rng = s.rng
    cfg = {1: (5, 5, (6.6, 8.4), 2, 0, True), 2: (6, 6, (6.8, 8.4), 0, 4, False),
           3: (8, 6, (6.0, 8.2), 0, 0, True), 4: (3, 4, (4.8, 6.2), 0, 0, True)}
    nst, nlf, hr, ncat, nplume, wet = cfg[v]
    if wet:
        s.shadow = False
        s.water([(0.8, 4.6, 9.15), (9.4, 13.2, 9.15), (2.6, 6.0, 9.75), (8.2, 11.0, 9.7)])
    leaves = []
    for _ in range(nlf):
        x0 = AX + rng.uniform(-1.6, 1.6)
        side = -1 if x0 < AX + rng.uniform(-0.5, 0.5) else 1
        b = (x0 + side * rng.uniform(1.8, 3.0), GY - rng.uniform(3.0, 4.8))
        c = (x0 + side * 0.35, b[1] - rng.uniform(0.4, 1.0))
        leaves.append({"a": (x0, GY), "c": c, "b": b, "w": rng.uniform(0.6, 0.75), "lean": side * 1.0})
    s.draw_blades(leaves, REED)
    xs = sorted(AX + rng.uniform(-2.2, 2.2) for _ in range(nst))
    stems = []
    for i, x0 in enumerate(xs):
        lx = rng.uniform(-0.5, 0.7)
        h = rng.uniform(*hr)
        a, c, b = (x0, GY), (x0 + lx * 0.3, GY - h * 0.5), (x0 + lx, GY - h)
        stems.append((a, c, b))
        tone = 2 if lx < -0.25 else 0 if lx > 0.45 else 1
        s.path(ribbon(a, c, b, 0.55, "taper", 8), REED[tone])
    for a, c, b in rng.sample(stems, ncat):     # cattail heads
        p = bez2(a, c, b, 0.8)
        geom = f'rect x="{n(p[0] - 0.48)}" y="{n(p[1] - 1.0)}" width=".96" height="2" rx=".48"'
        PTS.extend([(p[0] - 0.5, p[1] - 1.0), (p[0] + 0.5, p[1] + 1.0)])
        s._shape(geom, CATTAIL)
        s.stroke(f"M{n(p[0] - 0.2)} {n(p[1] - 0.6)}V{n(p[1] + 0.6)}", CATTAIL_LT, ".3")
    for a, c, b in rng.sample(stems, nplume):   # phragmites plumes
        plume(s, b, 1 if b[0] >= a[0] else -1, 3, ("#b49a7a", "#9a8064"))
    if v == 4:
        s.stroke(f"M{n(AX - 1.8)} 9.35H{n(AX + 1.4)}", WATER, ".45")


MOSSES = {1: (9.0, 6, (0.55, 0.85), MOSS), 2: (8.0, 4, (1.0, 1.35), MOSS_DK), 3: (7.0, 5, (0.6, 0.95), MOSS_YL)}


def k_moss(s, v):
    W, k, ryr, pal = MOSSES[v]
    rng = s.rng
    cush = []
    for i in range(k):
        x = AX + ((i + 0.5) / k * 2 - 1) * W / 2 + rng.uniform(-0.3, 0.3)
        ry = rng.uniform(*ryr)
        rx = rng.uniform(1.0, 1.6) * (1.15 if v == 2 else 1.0)
        rx = min(rx, W / k * 0.95 + 0.4)
        cush.append((x, GY - ry * 0.75, rx, ry))
    for x, y, rx, ry in cush:
        s.ellipse(x, y, rx, ry, pal[0])
    for x, y, rx, ry in cush:
        s.ellipse(x - 0.2, y - 0.18, rx * 0.75, ry * 0.7, pal[1], ink=False)
    for x, y, rx, ry in cush:
        s.ellipse(x - rx * 0.4, y - ry * 0.35, rx * 0.35, ry * 0.3, pal[2], ink=False)
        for _ in range(2):
            s.dot(x + rng.uniform(0.0, 0.6) * rx, y + rng.uniform(0.0, 0.4) * ry, 0.13, INK, ".45")
        s.dot(x + rng.uniform(-0.6, 0.0) * rx, y - rng.uniform(0.1, 0.5) * ry, 0.13, pal[2])
    if v == 1:
        specs = tuft_specs(rng, AX + 0.5, 4, 3.0, (1.0, 1.6), 1.2, 0.0, wr=(0.4, 0.5))
        for sp in specs:
            sp["a"] = (sp["a"][0], GY - 0.5)
        s.draw_blades(specs, GREEN, base=False)
    if v == 3:
        for _ in range(6):
            x, y, rx, ry = rng.choice(cush)
            bx = x + rng.uniform(-0.5, 0.5) * rx
            by = y - ry * 0.8
            tx, ty = bx + rng.uniform(-0.3, 0.3), by - rng.uniform(1.0, 1.8)
            PTS.append((tx, ty - 0.2))
            s.stroke(f"M{n(bx)} {n(by)}L{n(tx)} {n(ty)}", "#8a5a34", ".25")
            s.dot(tx, ty, 0.2, "#a0703e")


def mush(s, x, sh, cr, ch, pal, lean=0.0, spots=False):
    top = GY - sh
    cx = x + lean
    s.path(poly([(x - 0.36, GY), (cx - 0.27, top + 0.1), (cx + 0.27, top + 0.1), (x + 0.36, GY)]), STEM)
    s.path(poly([(x + 0.05, GY), (cx + 0.03, top + 0.1), (cx + 0.27, top + 0.1), (x + 0.36, GY)]), STEM_DK, ink=False)
    y0 = top + 0.15
    cap = (f"M{n(cx - cr)} {n(y0)}C{n(cx - cr)} {n(y0 - ch * 1.3)} {n(cx + cr)} {n(y0 - ch * 1.3)} {n(cx + cr)} {n(y0)}"
           f"Q{n(cx)} {n(y0 + 0.4)} {n(cx - cr)} {n(y0)}Z")
    PTS.extend([(cx - cr, y0), (cx + cr, y0), (cx, y0 - ch)])
    s.path(cap, pal[1])
    hx, hr, hh = cx - 0.28 * cr, 0.55 * cr, 0.6 * ch
    s.path(f"M{n(hx - hr)} {n(y0 - 0.1)}C{n(hx - hr)} {n(y0 - 0.1 - hh * 1.3)} {n(hx + hr)} {n(y0 - 0.1 - hh * 1.3)} "
           f"{n(hx + hr)} {n(y0 - 0.1)}Z", pal[2], ink=False)
    s.stroke(f"M{n(cx - cr + 0.15)} {n(y0 + 0.05)}Q{n(cx)} {n(y0 + 0.45)} {n(cx + cr - 0.15)} {n(y0 + 0.05)}", pal[0], ".35")
    if spots:
        for fx, fy in ((-0.45, 0.45), (0.2, 0.7), (0.55, 0.35)):
            s.dot(cx + fx * cr, y0 - fy * ch, 0.16, "#efe6cc")


def cap_path(cx, y0, cr, ch, shape):
    """Closed cap outline sitting on y0 (gill line). dome / bell / flat."""
    if shape == "bell":
        top = y0 - ch * 1.2
        return (f"M{n(cx - cr)} {n(y0)}C{n(cx - cr * 0.95)} {n(y0 - ch * 0.8)} {n(cx - cr * 0.55)} {n(top)} {n(cx)} {n(top)}"
                f"C{n(cx + cr * 0.55)} {n(top)} {n(cx + cr * 0.95)} {n(y0 - ch * 0.8)} {n(cx + cr)} {n(y0)}"
                f"Q{n(cx)} {n(y0 - 0.2)} {n(cx - cr)} {n(y0)}Z"), top
    if shape == "flat":
        top = y0 - ch
        return (f"M{n(cx - cr)} {n(y0)}Q{n(cx - cr * 0.75)} {n(top)} {n(cx)} {n(top)}"
                f"Q{n(cx + cr * 0.75)} {n(top)} {n(cx + cr)} {n(y0)}Q{n(cx)} {n(y0 + 0.3)} {n(cx - cr)} {n(y0)}Z"), top
    top = y0 - ch
    return (f"M{n(cx - cr)} {n(y0)}C{n(cx - cr)} {n(y0 - ch * 1.3)} {n(cx + cr)} {n(y0 - ch * 1.3)} {n(cx + cr)} {n(y0)}"
            f"Q{n(cx)} {n(y0 + 0.4)} {n(cx - cr)} {n(y0)}Z"), top


def shroom(s, x, gy, sh, cr, ch, pal, *, lean=0.0, shape="dome", stem_w=0.5, stem=(STEM, STEM_DK), eye=None):
    """One mushroom standing at (x, gy): curved stem ribbon + cap with a north-west highlight."""
    cx, y0 = x + lean, gy - sh
    a, c, b = (x, gy), (x + lean * 0.2, gy - sh * 0.5), (cx, y0 + 0.1)
    s.path(ribbon(a, c, b, stem_w, "stem", 5), stem[0])
    if stem_w >= 0.4:   # shaded east half of the stem
        s.path(ribbon((x + stem_w * 0.22, gy), (c[0] + stem_w * 0.2, c[1]), (cx + stem_w * 0.15, y0 + 0.1),
                      stem_w * 0.45, "stem", 5), stem[1], ink=False)
    d, top = cap_path(cx, y0, cr, ch, shape)
    PTS.extend([(cx - cr, y0), (cx + cr, y0), (cx, top)])
    s.path(d, pal[1])
    hd, _ = cap_path(cx - 0.3 * cr, y0 - 0.12, 0.5 * cr, 0.6 * ch, shape)
    s.path(hd, pal[2], ink=False)
    s.line(f"M{n(cx - cr + 0.12)} {n(y0 + 0.03)}Q{n(cx)} {n(y0 + 0.35)} {n(cx + cr - 0.12)} {n(y0 + 0.03)}", pal[0], ".3")
    if eye:   # darker cap centre (honey fungus, blewit)
        s.fill.append(f'<ellipse cx="{n(cx + 0.05)}" cy="{n(top + ch * 0.3)}" rx="{n(cr * 0.28)}" ry="{n(ch * 0.18)}" '
                      f'fill="{eye}" opacity=".55"/>')


def k_mushroom_bell(s):
    """4: bonnet mushrooms, small bell caps on tall thin stems, cream-beige, from one tight base."""
    rng = s.rng
    s.draw_blades(tuft_specs(rng, AX, 4, 3.4, (1.0, 1.8), 1.4, 0.0, wr=(0.45, 0.6)), GREEN_DK, base=False)
    for x, sh, cr, ch, ln in ((AX - 1.3, 2.6, 0.62, 0.95, -0.55), (AX + 1.25, 2.9, 0.58, 0.9, 0.5),
                              (AX - 0.25, 4.3, 0.72, 1.1, -0.15), (AX + 0.45, 3.5, 0.62, 1.0, 0.3)):
        shroom(s, x + rng.uniform(-0.1, 0.1), GY, sh, cr, ch, BELL, lean=ln, shape="bell", stem_w=0.3)


def k_mushroom_cluster(s):
    """5: honey-fungus clump, flat caps on stems fanning from one base, dull yellow with darker centres."""
    rng = s.rng
    base = AX - 0.2
    caps = [(-2.4, 2.0, 1.05), (2.2, 2.2, 1.0), (-1.2, 3.1, 1.15), (1.0, 3.4, 1.2), (0.0, 4.2, 1.25)]
    for dx, sh, cr in caps:   # back (taller) caps last, so they are drawn on top like a clump seen from the front
        x0 = base + dx * 0.25
        shroom(s, x0, GY, sh, cr, 0.55 + rng.uniform(0, 0.12), HONEY, lean=dx * 0.75, shape="flat",
               stem_w=0.42, eye=HONEY[0])
    s.draw_blades(tuft_specs(rng, AX + 0.4, 4, 5.0, (0.8, 1.4), 1.2, 0.0, wr=(0.45, 0.6)), GREEN, base=False)


def k_mushroom_bracket(s):
    """6: shelf fungus on an old root stump, muted orange-brown shelves stacked on the east face."""
    rng = s.rng
    x0, x1, top = AX - 2.3, AX + 0.9, GY - 3.6
    s.path(poly([(x0 - 0.5, GY), (x0, GY - 0.6), (x0 + 0.1, top + 0.3), (x1 - 0.15, top), (x1, GY - 0.7),
                 (x1 + 0.7, GY)]), STUMP[1])
    s.path(poly([(AX - 0.4, GY), (AX - 0.3, top + 0.2), (x1 - 0.15, top), (x1, GY - 0.7), (x1 + 0.7, GY)]),
           STUMP[0], ink=False)
    s.ellipse((x0 + x1) / 2 + 0.05, top + 0.12, (x1 - x0) / 2 - 0.05, 0.42, STUMP[2])
    s.line(f"M{n((x0 + x1) / 2 - 0.6)} {n(top + 0.12)}q.6 -.22 1.2 0", STUMP[0], ".3")
    for gx in (x0 + 0.7, AX - 0.9, AX + 0.2):
        s.line(f"M{n(gx)} {n(top + 0.7)}q{n(rng.uniform(-0.2, 0.2))} 1.6 0 {n(GY - top - 1.3)}", STUMP[0], ".3", ".7")
    for y, w, h in ((GY - 1.0, 2.5, 0.85), (GY - 2.0, 2.1, 0.75), (GY - 2.9, 1.6, 0.6)):
        bx = x1 - 0.2
        d = (f"M{n(bx)} {n(y - h * 0.4)}Q{n(bx + w * 0.75)} {n(y - h * 1.1)} {n(bx + w)} {n(y)}"
             f"Q{n(bx + w * 0.55)} {n(y + 0.4)} {n(bx)} {n(y + 0.25)}Z")
        PTS.extend([(bx, y - h), (bx + w, y + 0.4)])
        s.path(d, BRACKET[1])
        s.line(f"M{n(bx + 0.2)} {n(y - h * 0.45)}Q{n(bx + w * 0.6)} {n(y - h * 0.9)} {n(bx + w * 0.85)} {n(y - 0.12)}",
               BRACKET[2], ".35")
        s.line(f"M{n(bx + 0.15)} {n(y + 0.18)}Q{n(bx + w * 0.55)} {n(y + 0.3)} {n(bx + w - 0.1)} {n(y + 0.02)}",
               BRACKET[0], ".3")
    s.ellipse(x0 + 0.5, GY - 0.25, 0.75, 0.32, MOSS[1])   # moss at the foot
    s.draw_blades(tuft_specs(rng, x1 + 2.0, 3, 1.8, (0.9, 1.5), 1.0, 0.3, wr=(0.45, 0.6)), GREEN, base=False)


def k_mushroom_puffball(s):
    """7: puffballs, off-white spheres sitting in short grass, dotted texture."""
    rng = s.rng
    s.draw_blades(tuft_specs(rng, AX, 5, 6.0, (0.9, 1.6), 1.6, 0.0, wr=(0.45, 0.6)), GREEN, base=False)
    for x, r in ((AX - 2.4, 0.75), (AX + 1.9, 1.0), (AX - 0.5, 1.45), (AX + 3.4, 0.55)):
        cy = GY - r * 0.92
        s.ellipse(x, cy, r, r * 0.92, PUFF[1])
        s.fill.append(f'<ellipse cx="{n(x + r * 0.12)}" cy="{n(cy + r * 0.35)}" rx="{n(r * 0.85)}" ry="{n(r * 0.45)}" '
                      f'fill="{PUFF[0]}" opacity=".55"/>')
        s.fill.append(f'<ellipse cx="{n(x - r * 0.3)}" cy="{n(cy - r * 0.3)}" rx="{n(r * 0.42)}" ry="{n(r * 0.34)}" '
                      f'fill="{PUFF[2]}"/>')
        for _ in range(2 if r < 0.8 else 4):
            a = rng.uniform(-0.4, 2.2)
            rr = rng.uniform(0.3, 0.7) * r
            s.dot(x + math.cos(a) * rr, cy - math.sin(a) * rr * 0.6, 0.08, PUFF[0], ".8")


def k_mushroom_ring(s):
    """8: fairy ring, small pale-lilac caps on an elliptical arc in the grass, back ones smaller."""
    rng = s.rng
    cy, rx, ry = GY - 1.3, 4.7, 1.15
    s.stroke(f"M{n(AX - rx)} {n(cy)}A{n(rx)} {n(ry)} 0 1 0 {n(AX + rx)} {n(cy)}A{n(rx)} {n(ry)} 0 1 0 {n(AX - rx)} {n(cy)}",
             GREEN[0], ".5", ".45", layer=s.under)
    PTS.extend([(AX - rx, cy), (AX + rx, cy)])
    spots = []
    for i in range(8):
        th = (i + 0.3) / 8 * 2 * math.pi + rng.uniform(-0.15, 0.15)
        spots.append((cy + ry * math.sin(th), AX + rx * math.cos(th)))
    for gy, x in sorted(spots):
        k = 0.75 + 0.25 * (gy - (cy - ry)) / (2 * ry)   # nearer (lower) = larger
        shroom(s, x, gy, 1.3 * k, 0.75 * k, 0.6 * k, LILAC, lean=rng.uniform(-0.15, 0.15), stem_w=0.36 * k,
               stem=("#e2dccc", "#c0b8a6"))
    s.draw_blades(tuft_specs(rng, AX - 0.2, 3, 2.0, (0.8, 1.3), 1.0, 0.0, wr=(0.45, 0.55)), GREEN_LT, base=False)


NEW_MUSHROOMS = {4: k_mushroom_bell, 5: k_mushroom_cluster, 6: k_mushroom_bracket, 7: k_mushroom_puffball,
                 8: k_mushroom_ring}


def k_mushroom(s, v):
    if v in NEW_MUSHROOMS:
        NEW_MUSHROOMS[v](s)
        return
    rng = s.rng
    s.draw_blades(tuft_specs(rng, AX + 0.3, 5, 4.0, (1.2, 2.2), 1.6, 0.0, wr=(0.5, 0.65)), GREEN, base=False)
    if v == 1:
        mush(s, AX + 1.4, 1.5, 0.95, 0.9, BROWN, lean=0.2)
        mush(s, AX - 1.0, 2.6, 1.5, 1.4, BROWN)
    elif v == 2:
        mush(s, AX + 1.7, 1.2, 0.8, 0.7, RED_CAP, lean=0.15, spots=True)
        mush(s, AX - 0.4, 3.0, 1.7, 1.5, RED_CAP, spots=True)
    else:
        for x, sh, cr, ch, ln in ((AX + 1.7, 1.4, 0.7, 0.65, 0.2), (AX - 1.8, 1.7, 0.8, 0.7, -0.2),
                                  (AX + 0.5, 2.0, 0.9, 0.8, 0.1), (AX - 0.6, 2.4, 1.0, 0.9, -0.1)):
            mush(s, x, sh, cr, ch, TAN, lean=ln)


KINDS = {
    "tuft": ("普通草丛", 4, k_tuft, [1.0, 1.0, 0.8, 0.8]),
    "tall": ("高草/芒草", 4, k_tall, [1.0, 0.7, 1.0, 0.8]),
    "fern": ("蕨类", 4, k_fern, [1.0, 0.8, 1.0, 0.6]),
    "shrub": ("低矮灌丛", 4, k_shrub, [1.0, 0.8, 0.5, 0.8]),
    "flower": ("带小花的草丛", 4, k_flower, [1.0, 1.0, 0.7, 0.6]),
    "dry": ("枯黄草丛", 4, k_dry, [1.0, 0.8, 0.8, 1.0]),
    "reed": ("芦苇/水草", 4, k_reed, [1.0, 1.0, 0.8, 0.7]),
    "moss": ("苔藓地被", 3, k_moss, [1.0, 1.0, 0.7]),
    # 1 褐伞 2 红伞白点 3 淡褐丛 4 奶白钟形细柄 5 黄色平盖丛生 6 橙褐架状(树根) 7 白色马勃 8 淡紫蘑菇圈
    # 饱和度高的（红 2、橙 6、紫 8）权重压低。
    "mushroom": ("林下蘑菇", 8, k_mushroom, [1.0, 0.35, 0.8, 0.8, 0.6, 0.35, 0.6, 0.3]),
}

# suggested kind mix per scene (sums to 1). Defaults for drawing, not an ecological model.
BY_SCENE = {
    "conifer": {"moss": 0.28, "fern": 0.2, "tuft": 0.26, "shrub": 0.2, "mushroom": 0.06},
    "broadleaf": {"fern": 0.3, "tuft": 0.25, "shrub": 0.22, "flower": 0.12, "mushroom": 0.06, "moss": 0.05},
    "forest_edge": {"tuft": 0.3, "tall": 0.25, "shrub": 0.15, "flower": 0.15, "dry": 0.15},
    "riparian": {"reed": 0.5, "tall": 0.25, "tuft": 0.15, "fern": 0.1},
    "dry": {"dry": 0.6, "tuft": 0.15, "shrub": 0.15, "tall": 0.1},
    "wet": {"fern": 0.35, "moss": 0.3, "reed": 0.2, "tuft": 0.11, "mushroom": 0.04},
}
SCENE_NOTES = {
    "conifer": "针叶林林下：苔藓、蕨、矮灌为主",
    "broadleaf": "阔叶林/湿润林下：蕨、草丛、灌丛，少量花草",
    "forest_edge": "林缘与草原过渡：高草、花草、枯草",
    "riparian": "河湖岸边林地：芦苇/水草（带水纹的变种只放水边）",
    "dry": "干燥、暖带林缘：枯黄草丛为主",
    "wet": "沼泽化、多雨林下：蕨、苔藓、水草，少量蘑菇",
}
WET_VARIANTS = {"grass-reed-1", "grass-reed-3", "grass-reed-4"}


def header():
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" style="position:absolute">\n'
        "<!-- 织梦 · 地图美术资产 · 林下草类点缀（ground grass）。本工程原创，手绘铜版 + 淡彩，与 map-art-trees-a/-b.svg 同一画风。\n"
        "     规格：全部符号 viewBox 0 0 14 10，地面线 y=9，锚点 = 底边中点 (7,9)（见 data-anchor）。投影椭圆可伸到 y≈9.7。\n"
        "     尺度：与 32×40 的树按同一 px/单位绘制（树显示高 H px → 草符号框 0.35H × 0.25H）；草体高约 1.5–8 单位，远小于树。\n"
        "     光照：光源西北（左上）。墨线 #3b2f22 作整体垫底（描边 0.8，只露外侧约 0.4），亮/中/暗三色淡彩，左倾叶片偏亮；投影偏东南。\n"
        "     id：grass-{kind}-{n}，kind = tuft tall fern shrub flower dry reed moss mushroom；data-kind 同 kind。\n"
        "     grass-reed-1/3/4 自带水纹、不画投影，只放水边（json 里 requires_water_adjacent=true）。场景与权重见 ground-grass.json。\n"
        "     蘑菇 8 种：1 褐伞 2 红伞 3 淡褐丛 4 钟形细柄 5 平盖丛生 6 树根架状菌 7 马勃 8 蘑菇圈；红/橙/紫权重压低，整体保持稀疏。\n"
        "     由 tools/gen_ground_grass_art.py 确定性生成（种子 20261020 ^ crc32(id)），请改脚本后重新生成，不要手改。 -->\n"
        "<defs>\n")


def main():
    symbols, meta_syms = [], []
    for kind, (name, count, fn, weights) in KINDS.items():
        for v in range(1, count + 1):
            s = Sym(kind, v)
            fn(s, v)
            symbols.append(s.render())
            ext = s.extent()
            scenes = [sc for sc, mix in BY_SCENE.items() if kind in mix]
            if s.id in WET_VARIANTS:
                scenes = [sc for sc in scenes if sc in ("riparian", "wet")]
            meta_syms.append({"id": s.id, "kind": kind, "variant": v,
                              "viewBox": [VB[0], VB[1]], "anchor": [AX, GY],
                              "extent": ext, "height_units": round(GY - ext[1], 1),
                              "scenes": scenes, "weight": weights[v - 1],
                              "requires_water_adjacent": s.id in WET_VARIANTS})
    # per-scene probability of each symbol = kind share * variant weight / kind weight sum (in that scene)
    for sc, mix in BY_SCENE.items():
        for kind, share in mix.items():
            pool = [m for m in meta_syms if m["kind"] == kind and sc in m["scenes"]]
            tot = sum(m["weight"] for m in pool)
            for m in pool:
                m.setdefault("scene_weights", {})[sc] = round(share * m["weight"] / tot, 4)
    svg = header() + "\n".join(symbols) + "\n</defs>\n</svg>\n"
    OUT_SVG.write_text(svg, encoding="utf-8", newline="\n")
    meta = {
        "version": 1,
        "sprite": "/static/map-art/map-art-ground-grass.svg",
        "note": "林下草类点缀符号清单（树林里与林缘的草、蕨、灌丛、花草、枯草、芦苇、苔藓、蘑菇）。只描述用哪个符号、建议在哪类林地出现、出现多少；不是生态模型。由 tools/gen_ground_grass_art.py 生成。",
        "viewBox": [VB[0], VB[1]],
        "anchor": [AX, GY],
        "anchor_note": "地面线中点 (7,9) 对准落点；extent 为 [x0,y0,x1,y1] 实际笔迹范围（viewBox 单位，含墨线）。",
        "water_note": "requires_water_adjacent=true 的符号自带水纹、无投影，只能放在紧挨水面的格子（河湖岸线），不要撒在林内。",
        "scale": "与 map-art-trees-a/-b.svg（viewBox 32×40，锚点 16,38）同一 px/单位：树显示高 H px 时草符号框为 0.35H × 0.25H。想让草更显眼可整体放大到 1.3–1.5 倍，但不宜超过树的 1/3 高。",
        "weights_note": "scene_weights[scene] = BY_SCENE[scene][kind] × weight / 同场景同种 weight 之和；同一场景内全部符号的 scene_weights 之和为 1，可直接当抽样概率。weight 为种内变种相对权重。",
        "scenes": SCENE_NOTES,
        "by_scene": BY_SCENE,
        "kinds": {k: {"name": v[0], "variants": [f"grass-{k}-{i}" for i in range(1, v[1] + 1)]} for k, v in KINDS.items()},
        "symbols": meta_syms,
    }
    OUT_JSON.write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"{OUT_SVG.name}: {len(symbols)} symbols; {OUT_JSON.name}")


if __name__ == "__main__":
    main()
