"""生成 app/static/map-art/map-art-trees-b.svg：暖带/特殊/奇幻 16 个树种，每种主图 + 2–3 个形态变种。

风格：手绘铜版加淡彩。viewBox 0 0 32 40，锚点（树根落地点）(16,38)，光源左上；
外轮廓 #3b2f22 0.8，内部细节 0.4–0.45；树根处 #3b2f22 opacity .18 椭圆地影。
确定性：叶簇/排线的随机抖动用 zlib.crc32(symbol id) 作种子，重复运行输出逐字节相同。
用法：.venv\\Scripts\\python.exe tools/build_tree_art_b.py
"""
from __future__ import annotations

import math
import random
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "app" / "static" / "map-art" / "map-art-trees-b.svg"

INK = "#3b2f22"
BARK = ("#5b4130", "#7a5a40")
LEAF = ("#4f6b35", "#6d8a42", "#93a85a")
DRY = ("#5f6b34", "#7d8a3e", "#a3a35a")
OLIVE = ("#56604f", "#7e8a76", "#aab4a0")         # 银灰绿
SAKURA = ("#b07a86", "#c98d99", "#e3b7bf")
SILVER = ("#8e9b97", "#b9c4c0", "#e1e7e2")
PALE_BARK = ("#7f7a6c", "#ada897")
GLOOM_BARK = ("#4a4148", "#6b6068")
GLOOM_LEAF = ("#3d363c", "#4a4148", "#625761")
CAP = ("#8a3f2b", "#b0563c", "#cf7a55")
STEM = ("#c9b48e", "#e6d6b8", "#f6ecd6")
ICE = ("#4f8aa3", "#7fb4c9", "#c8e4ee")
STONE = ("#55505c", "#77717e")
CULM = ("#6d8a42", "#93a85a", "#b6c47c")
BAOBAB = ("#5b4130", "#7a5a40", "#957452")
# 相近树种拉开：叶色色相 + 树皮颜色各不相同（20 px 下靠色与轮廓区分）
TEAK_LEAF = ("#5f6a22", "#8a9634", "#b7bd5a")      # 黄绿大叶
TEAK_BARK = ("#7a4630", "#a26a4a")                 # 红褐
KAPOK_LEAF = ("#2c5638", "#43774b", "#6c9a62")     # 冷深绿
KAPOK_BARK = ("#78806c", "#a7ad96")                # 带刺灰绿
KAPOK_FLOWER = "#c4473a"
DRAGON_LEAF = ("#1d3d40", "#2c5b58", "#4d8078")    # 深蓝绿
DRAGON_BARK = ("#958f84", "#cbc5b5")               # 灰白
ACACIA_LEAF = ("#69632a", "#928a3c", "#bcb262")    # 橄榄黄绿
ACACIA_BARK = ("#3d291e", "#61432f")               # 深褐
OLIVE_BARK = ("#6b6559", "#948c7a")                # 灰褐扭干
# 巨菌配色
PURPLE = ("#4e2f63", "#7a4a92", "#a780c0")
GLOW = ("#1f5f7a", "#3f97b3", "#93d8e8")
GLOW_STEM = ("#8fb0b8", "#cde2e5", "#eef8f8")
OCHRE = ("#7f5a22", "#ad863c", "#d4b169")
SHELF = ("#94491f", "#c47634", "#e5a85c")


def n(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "", "-") else s


def pt(p) -> str:
    return f"{n(p[0])} {n(p[1])}"


def quad(p0, k, p1, t):
    a, b, c = (1 - t) ** 2, 2 * (1 - t) * t, t * t
    return (a * p0[0] + b * k[0] + c * p1[0], a * p0[1] + b * k[1] + c * p1[1])


def quad_tan(p0, k, p1, t):
    return (2 * (1 - t) * (k[0] - p0[0]) + 2 * t * (p1[0] - k[0]),
            2 * (1 - t) * (k[1] - p0[1]) + 2 * t * (p1[1] - k[1]))


def unit(v):
    length = math.hypot(v[0], v[1]) or 1.0
    return (v[0] / length, v[1] / length)


def ctrl(p0, p1, bend):
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    return ((p0[0] + p1[0]) / 2 - dy * bend, (p0[1] + p1[1]) / 2 + dx * bend)


def about(p, s):
    return f"translate({n(p[0] * (1 - s))} {n(p[1] * (1 - s))}) scale({s})"


def limb_d(p0, p1, w0, w1, k, steps=14):
    left, right = [], []
    for i in range(steps + 1):
        t = i / steps
        p = quad(p0, k, p1, t)
        tx, ty = unit(quad_tan(p0, k, p1, t))
        nx, ny = -ty, tx
        w = (w0 + (w1 - w0) * t) / 2
        left.append((p[0] + nx * w, p[1] + ny * w))
        right.append((p[0] - nx * w, p[1] - ny * w))
    pts = left + right[::-1]
    return "M" + " L".join(pt(q) for q in pts) + "Z", left, right


def lobed(r, cx, cy, rx, ry, k, jitter=0.1, bump=0.32, squash=0.0, start=None):
    start = r.uniform(0, 360) if start is None else start
    pts = []
    for i in range(k):
        a = math.radians(start + 360 * (i + r.uniform(-0.22, 0.22)) / k)
        s = 1 + r.uniform(-jitter, jitter)
        x, y = cx + rx * s * math.cos(a), cy + ry * s * math.sin(a)
        if squash and y > cy:
            y = cy + (y - cy) * (1 - squash)
        pts.append((x, y))
    return scallop_path(pts, (cx, cy), bump, closed=True)


def scallop_path(pts, centre, bump, closed):
    d = "M" + pt(pts[0])
    rng_ = range(len(pts)) if closed else range(len(pts) - 1)
    for i in rng_:
        p, q = pts[i], pts[(i + 1) % len(pts)]
        dx, dy = q[0] - p[0], q[1] - p[1]
        length = math.hypot(dx, dy) or 1.0
        nx, ny = dy / length, -dx / length
        mx, my = (p[0] + q[0]) / 2 - centre[0], (p[1] + q[1]) / 2 - centre[1]
        if nx * mx + ny * my < 0:
            nx, ny = -nx, -ny
        h = bump * length
        c1 = (p[0] + nx * h + dx * 0.1, p[1] + ny * h + dy * 0.1)
        c2 = (q[0] + nx * h - dx * 0.1, q[1] + ny * h - dy * 0.1)
        d += f" C{pt(c1)} {pt(c2)} {pt(q)}"
    return d + ("Z" if closed else "")


class Sym:
    def __init__(self, sid: str):
        self.id = sid
        self.parts: list[str] = []
        self.r = random.Random(zlib.crc32(sid.encode("utf-8")))
        self.mark_w = (1.1, 1.9)  # 叶簇小弧长度；大叶树种调大

    def add(self, s: str):
        self.parts.append(s)

    def svg(self) -> str:
        body = "\n".join("  " + p for p in self.parts)
        return (f'<symbol id="{self.id}" viewBox="0 0 32 40" data-anchor="16 38">'
                f'<g stroke-linejoin="round" stroke-linecap="round">\n{body}\n</g></symbol>')

    # ---- ground ----
    def shadow(self, rx, cx=16.0, ry=None):
        ry = ry if ry is not None else max(1.0, rx * 0.16)
        self.add(f'<ellipse cx="{n(cx)}" cy="38" rx="{n(rx)}" ry="{n(ry)}" fill="{INK}" opacity=".18"/>')

    # ---- foliage ----
    def leafmarks(self, box, density=1.0, hatch=True):
        x0, y0, x1, y1 = box
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        rx, ry = (x1 - x0) / 2 * 0.72, (y1 - y0) / 2 * 0.72
        m = int(math.pi * rx * ry / 7 * density) + 2
        segs = []
        for _ in range(m * 4):
            if len(segs) >= m:
                break
            a = self.r.uniform(0, 2 * math.pi)
            rr = math.sqrt(self.r.random())
            x, y = cx + rx * rr * math.cos(a), cy + ry * rr * math.sin(a)
            bias = 0.3 + 0.7 * ((x - cx) / (rx * 2) + (y - cy) / (ry * 2) + 0.5)
            if self.r.random() > bias:
                continue
            w = self.r.uniform(*self.mark_w)
            segs.append(f"M{n(x - w / 2)} {n(y)}q{n(w / 2)} {n(w * 0.5)} {n(w)} 0")
        if segs:
            self.add(f'<path d="{"".join(segs)}" fill="none" stroke="{INK}" stroke-width=".42" opacity=".6"/>')
        if hatch:
            lines = []
            for _ in range(max(2, int(rx * 0.9))):
                a = math.radians(self.r.uniform(-5, 95))
                rr = self.r.uniform(0.5, 0.9)
                x, y = cx + rx * rr * math.cos(a), cy + ry * rr * math.sin(a)
                h = self.r.uniform(0.55, 0.85)
                lines.append(f"M{n(x - h)} {n(y + h)}l{n(2 * h)} {n(-2 * h)}")
            self.add(f'<path d="{"".join(lines)}" fill="none" stroke="{INK}" stroke-width=".4" opacity=".55"/>')

    def crown(self, d, box, tones, marks=1.0, hatch=True, s1=0.84, s2=0.48, ow=0.8):
        x0, y0, x1, y1 = box
        w, h = x1 - x0, y1 - y0
        p1 = (x0 + w * 0.24, y0 + h * 0.2)
        p2 = (x0 + w * 0.3, y0 + h * 0.26)
        self.add(f'<path d="{d}" fill="{tones[0]}"/>')
        self.add(f'<path d="{d}" fill="{tones[1]}" transform="{about(p1, s1)}"/>')
        self.add(f'<path d="{d}" fill="{tones[2]}" transform="{about(p2, s2)}"/>')
        if marks:
            self.leafmarks(box, marks, hatch)
        self.add(f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{ow}"/>')

    def lobe(self, cx, cy, rx, ry, k, tones=LEAF, jitter=0.1, bump=0.32, squash=0.0, marks=1.0, hatch=True):
        d = lobed(self.r, cx, cy, rx, ry, k, jitter, bump, squash)
        self.crown(d, (cx - rx, cy - ry, cx + rx, cy + ry * (1 - squash * 0.5)), tones, marks, hatch)

    def dome(self, cx, yb, rx, ry, k, tones=LEAF, marks=1.0, bump=0.3, fringe=True):
        pts = []
        for i in range(k + 1):
            a = math.pi * (1 + i / k)
            s = 1 if i in (0, k) else 1 + self.r.uniform(-0.06, 0.06)
            pts.append((cx + rx * s * math.cos(a), yb + ry * s * math.sin(a)))
        d = scallop_path(pts, (cx, yb), bump, closed=False)
        d = d + f" Q{n(cx)} {n(yb + ry * 0.2)} {pt(pts[0])}Z"
        self.crown(d, (cx - rx, yb - ry, cx + rx, yb + ry * 0.12), tones, marks)
        if fringe:
            ticks = []
            for i in range(1, 12):
                x = cx - rx + 2 * rx * i / 12
                tt = (x - cx) / rx
                y = yb + ry * 0.1 * (1 - tt * tt)
                ticks.append(f"M{n(x)} {n(y - 0.3)}l{n(self.r.uniform(-0.3, 0.3))} 1")
            self.add(f'<path d="{"".join(ticks)}" fill="none" stroke="{INK}" stroke-width=".45" opacity=".8"/>')

    def star(self, cx, cy, ro, ri, k, tones=DRY, rot=None):
        rot = self.r.uniform(0, 360) if rot is None else rot
        pts = []
        for i in range(2 * k):
            a = math.radians(rot + 180 * i / k)
            up = -math.sin(a)
            rad = (ro * (1 + 0.18 * up) * self.r.uniform(0.85, 1.1)) if i % 2 == 0 else ri
            pts.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
        d = "M" + " L".join(pt(p) for p in pts) + "Z"
        self.crown(d, (cx - ro, cy - ro, cx + ro, cy + ro), tones, marks=0, s1=0.8, s2=0.45, ow=0.6)
        ray = "".join(f"M{pt((cx, cy))}L{pt((cx + (ro * 0.7) * math.cos(math.radians(a)), cy + (ro * 0.7) * math.sin(math.radians(a))))}"
                      for a in (-150, -110, -70, -30, 10, 60, 120, 170))
        self.add(f'<path d="{ray}" fill="none" stroke="{INK}" stroke-width=".35" opacity=".55"/>')

    def frond(self, c, ang, length, droop, fill, w=None, ticks=True, ow=0.6):
        a = math.radians(ang)
        u = (math.cos(a), math.sin(a))
        tip = (c[0] + u[0] * length, c[1] + u[1] * length + droop)
        k = (c[0] + u[0] * length * 0.55, c[1] + u[1] * length * 0.55 - droop * 0.35)
        w = w if w is not None else max(1.1, length * 0.15)
        left, right, rib = [], [], []
        steps = 12
        for i in range(steps + 1):
            t = i / steps
            p = quad(c, k, tip, t)
            tx, ty = unit(quad_tan(c, k, tip, t))
            nx, ny = -ty, tx
            hw = w / 2 * (math.sin(math.pi * min(1.0, t * 1.08)) ** 0.7 if t < 1 else 0)
            left.append((p[0] + nx * hw, p[1] + ny * hw))
            right.append((p[0] - nx * hw, p[1] - ny * hw))
            rib.append(p)
        d = "M" + " L".join(pt(q) for q in left + right[::-1]) + "Z"
        self.add(f'<path d="{d}" fill="{fill}" stroke="{INK}" stroke-width="{ow}"/>')
        if ticks:
            segs = []
            for i in range(2, steps - 1):
                t = i / steps
                p = quad(c, k, tip, t)
                tx, ty = unit(quad_tan(c, k, tip, t))
                nx, ny = -ty, tx
                hw = w / 2 * math.sin(math.pi * t) ** 0.7
                for sgn in (1, -1):
                    base = (p[0] + nx * sgn * hw * 0.3, p[1] + ny * sgn * hw * 0.3)
                    dv = unit((nx * sgn + tx * 0.5, ny * sgn + ty * 0.5 + 0.55))
                    ln = hw + 0.75
                    segs.append(f"M{pt(base)}l{n(dv[0] * ln)} {n(dv[1] * ln)}")
            self.add(f'<path d="{"".join(segs)}" fill="none" stroke="{INK}" stroke-width=".4" opacity=".75"/>')
            self.add(f'<path d="M{" L".join(pt(q) for q in rib[:-1])}" fill="none" stroke="{INK}" stroke-width=".4" opacity=".6"/>')

    def palm_crown(self, c, fronds, tones=LEAF, nuts=True, width=None):
        groups = {0: [], 1: [], 2: []}
        for ang, length, droop in fronds:
            a = ((ang + 180) % 360) - 180
            if -55 <= a <= 55:
                tone = 0
            elif a < -120 or a > 125:
                tone = 2
            else:
                tone = 1
            groups[tone].append((ang, length, droop))
        for ang, length, droop in groups[0]:
            self.frond(c, ang, length, droop, tones[0], w=width)
        if nuts:
            for dx, dy in ((-0.9, 1.2), (0.7, 1.4), (0.0, 2.1)):
                self.add(f'<circle cx="{n(c[0] + dx)}" cy="{n(c[1] + dy)}" r=".85" fill="{BARK[0]}" stroke="{INK}" stroke-width=".5"/>')
        for tone in (1, 2):
            for ang, length, droop in groups[tone]:
                self.frond(c, ang, length, droop, tones[tone], w=width)

    # ---- wood ----
    def trunk(self, p0, p1, w0, w1, bend=0.0, k=None, tones=BARK, bark=True, ow=0.8):
        k = k or ctrl(p0, p1, bend)
        d, left, right = limb_d(p0, p1, w0, w1, k)
        if sum(q[0] for q in left) > sum(q[0] for q in right):
            left, right = right, left
        m = len(left)
        centre = [quad(p0, k, p1, i / (m - 1)) for i in range(m)]
        hl = [(c[0] + (left[i][0] - c[0]) * 0.5, c[1] + (left[i][1] - c[1]) * 0.5) for i, c in enumerate(centre)][1:-1]
        self.add(f'<path d="{d}" fill="{tones[0]}"/>')
        self.add(f'<path d="M{" L".join(pt(q) for q in hl)}" fill="none" stroke="{tones[1]}" stroke-width="{n((w0 + w1) / 2 * 0.36)}"/>')
        if bark:
            segs = []
            for i in range(1, m - 2, 3):
                a = (centre[i][0] + (right[i][0] - centre[i][0]) * 0.15, centre[i][1] + (right[i][1] - centre[i][1]) * 0.15)
                b = (centre[i + 1][0] + (right[i + 1][0] - centre[i + 1][0]) * 0.75,
                     centre[i + 1][1] + (right[i + 1][1] - centre[i + 1][1]) * 0.75)
                segs.append(f"M{pt(a)}L{pt(b)}")
            self.add(f'<path d="{"".join(segs)}" fill="none" stroke="{INK}" stroke-width=".4" opacity=".6"/>')
        self.add(f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{ow}"/>')
        return k

    def tubes(self, items, tones=BARK, ow=0.8, trunks=(), ribs=False):
        """items: [(path d, width)]；先画全部外轮廓，再画 trunks（多边形树干），最后填色 → 枝干接缝融合。"""
        for d, w in items:
            self.add(f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{n(w + 2 * ow)}"/>')
        for args, kw in trunks:
            self.trunk(*args, **kw)
        for d, w in items:
            self.add(f'<path d="{d}" fill="none" stroke="{tones[0]}" stroke-width="{n(w)}"/>')
        for d, w in items:
            if len(tones) >= 3:
                self.add(f'<path d="{d}" fill="none" stroke="{tones[1]}" stroke-width="{n(w * 0.62)}" transform="translate({n(-w * 0.12)} {n(-w * 0.1)})"/>')
                self.add(f'<path d="{d}" fill="none" stroke="{tones[2]}" stroke-width="{n(w * 0.22)}" transform="translate({n(-w * 0.25)} {n(-w * 0.2)})"/>')
            else:
                self.add(f'<path d="{d}" fill="none" stroke="{tones[1]}" stroke-width="{n(w * 0.38)}" transform="translate({n(-w * 0.17)} {n(-w * 0.1)})"/>')
        if ribs:
            for d, w in items:
                self.add(f'<path d="{d}" fill="none" stroke="{INK}" stroke-width=".35" opacity=".45" transform="translate({n(w * 0.2)} 0)"/>')

    def buttress(self, cx, wb, h, tw, tones=BARK):
        y = 38
        d = (f"M{n(cx - wb / 2)} {y} Q{n(cx - tw / 2 - 0.2)} {n(y - h * 0.2)} {n(cx - tw / 2)} {n(y - h)}"
             f" L{n(cx + tw / 2)} {n(y - h)} Q{n(cx + tw / 2 + 0.2)} {n(y - h * 0.2)} {n(cx + wb / 2)} {y}Z")
        sides = (f"M{n(cx - wb / 2)} {y} Q{n(cx - tw / 2 - 0.2)} {n(y - h * 0.2)} {n(cx - tw / 2)} {n(y - h)}"
                 f" M{n(cx + tw / 2)} {n(y - h)} Q{n(cx + tw / 2 + 0.2)} {n(y - h * 0.2)} {n(cx + wb / 2)} {y}"
                 f" M{n(cx - wb / 2)} {y} L{n(cx + wb / 2)} {y}")
        self.add(f'<path d="{d}" fill="{tones[0]}"/>')
        self.add(f'<path d="M{n(cx - wb * 0.32)} {y} Q{n(cx - tw * 0.3)} {n(y - h * 0.3)} {n(cx - tw * 0.25)} {n(y - h)}" '
                 f'fill="none" stroke="{tones[1]}" stroke-width="{n(tw * 0.35)}"/>')
        ridges = (f"M{n(cx - wb * 0.22)} {y} Q{n(cx - tw * 0.1)} {n(y - h * 0.35)} {n(cx - tw * 0.05)} {n(y - h * 0.85)}"
                  f"M{n(cx + wb * 0.24)} {y} Q{n(cx + tw * 0.2)} {n(y - h * 0.35)} {n(cx + tw * 0.2)} {n(y - h * 0.8)}")
        self.add(f'<path d="{ridges}" fill="none" stroke="{INK}" stroke-width=".45" opacity=".75"/>')
        self.add(f'<path d="{sides}" fill="none" stroke="{INK}" stroke-width=".8"/>')

    def thorns(self, x, y0, y1, w, step=1.6):
        """沿竖直树干两侧的小刺（木棉）。"""
        segs, side, y = [], 1, y0
        while y > y1:
            hw = w(y) / 2
            bx = x + side * hw
            segs.append(f"M{n(bx)} {n(y + 0.35)}L{n(bx + side * 0.75)} {n(y - 0.2)}L{n(bx)} {n(y - 0.35)}")
            side = -side
            y -= step
        self.add(f'<path d="{"".join(segs)}" fill="{INK}" stroke="{INK}" stroke-width=".3"/>')

    # ---- crystal / sparkle ----
    def shard(self, b, t, w, tones=ICE):
        u = unit((t[0] - b[0], t[1] - b[1]))
        length = math.hypot(t[0] - b[0], t[1] - b[1])
        r = (-u[1], u[0])
        if r[0] < 0 or (abs(r[0]) < 1e-6 and r[1] < 0):
            r = (-r[0], -r[1])

        def at(along, side):
            return (b[0] + u[0] * along + r[0] * side, b[1] + u[1] * along + r[1] * side)
        bl, br = at(0, -w / 2), at(0, w / 2)
        sl, sr = at(length * 0.74, -w / 2), at(length * 0.74, w / 2)
        bml, bmr = at(0, -w / 6), at(0, w / 6)
        poly = lambda ps: "M" + " L".join(pt(p) for p in ps) + "Z"  # noqa: E731
        self.add(f'<path d="{poly([bl, bml, t, sl])}" fill="{tones[2]}"/>')
        self.add(f'<path d="{poly([bml, bmr, t])}" fill="{tones[1]}"/>')
        self.add(f'<path d="{poly([bmr, br, sr, t])}" fill="{tones[0]}"/>')
        hl_a, hl_b = at(length * 0.12, -w * 0.32), at(length * 0.66, -w * 0.32)
        self.add(f'<path d="M{pt(hl_a)}L{pt(hl_b)}" stroke="#ffffff" stroke-width=".45" opacity=".85"/>')
        self.add(f'<path d="M{pt(bml)}L{pt(t)}M{pt(bmr)}L{pt(t)}" fill="none" stroke="{INK}" stroke-width=".4" opacity=".7"/>')
        self.add(f'<path d="{poly([bl, sl, t, sr, br])}" fill="none" stroke="{INK}" stroke-width=".75"/>')

    def sparkle(self, x, y, s, color="#ffffff"):
        q = s * 0.25
        d = (f"M{n(x)} {n(y - s)}L{n(x + q)} {n(y - q)}L{n(x + s)} {n(y)}L{n(x + q)} {n(y + q)}"
             f"L{n(x)} {n(y + s)}L{n(x - q)} {n(y + q)}L{n(x - s)} {n(y)}L{n(x - q)} {n(y - q)}Z")
        self.add(f'<path d="{d}" fill="{color}" opacity=".9"/>')

    def dots(self, pts, r, fill, stroke=None, opacity=1.0):
        st = f' stroke="{stroke}" stroke-width=".3"' if stroke else ""
        op = f' opacity="{n(opacity)}"' if opacity < 1 else ""
        self.add("".join(f'<circle cx="{n(x)}" cy="{n(y)}" r="{n(r)}" fill="{fill}"{st}{op}/>' for x, y in pts))

    def scatter(self, box, count, bias_ul=True):
        x0, y0, x1, y1 = box
        cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2 * 0.78, (y1 - y0) / 2 * 0.78
        out = []
        for _ in range(count * 6):
            if len(out) >= count:
                break
            a = self.r.uniform(0, 2 * math.pi)
            rr = math.sqrt(self.r.random())
            x, y = cx + rx * rr * math.cos(a), cy + ry * rr * math.sin(a)
            v = (x - cx) / (2 * rx) + (y - cy) / (2 * ry) + 0.5
            if bias_ul and self.r.random() < v * 0.8:
                continue
            if not bias_ul and self.r.random() > v * 1.2:
                continue
            out.append((x, y))
        return out


def forks(p, ang, length, w, depth, spread=30.0, decay=0.74, tilt=0.0):
    """多次二叉分枝（龙血树）：返回 tubes 用的 [(d, w)] 与末梢点。"""
    a = math.radians(ang)
    q = (p[0] + math.cos(a) * length, p[1] + math.sin(a) * length)
    items, tips = [(f"M{pt(p)} L{pt(q)}", w)], []
    if depth <= 1:
        return items, [q]
    for sgn in (-1, 1):
        it, tp = forks(q, ang + sgn * spread + tilt, length * decay, w * 0.72, depth - 1, spread * 0.95, decay, tilt)
        items += it
        tips += tp
    return items, tips


# =====================================================================  species
# 每个函数画一个 symbol；命名 <species>_<n>，n=1 为主图。

def _teak_flowers(s, cx, top, rx):
    """柚木顶生的乳白小花序。"""
    pts = [(cx + rx * f, top + 0.9 + 2.4 * f * f + s.r.uniform(-.25, .25)) for f in (-0.6, -0.3, 0.0, 0.3, 0.55)]
    s.dots(pts, .55, "#efe6c4", stroke=INK)


def teak_1(s):
    """红褐直干 + 宽卵形大叶团（黄绿）。"""
    s.mark_w = (1.9, 3.0)
    s.shadow(9)
    s.tubes([("M16 27 Q12.5 24.5 10 21.5", 1.2), ("M16 26 Q19.5 23.5 22.5 21", 1.2), ("M16 25 L16 16", 1.0)],
            tones=TEAK_BARK, trunks=[(((16, 38), (16, 24), 2.9, 1.7), {"tones": TEAK_BARK})])
    s.lobe(16, 15, 12.5, 8.6, 9, tones=TEAK_LEAF, jitter=0.08, bump=0.4, squash=0.12)
    s.lobe(23.6, 21.6, 3.8, 2.6, 5, tones=TEAK_LEAF, bump=0.4, marks=0.5, hatch=False)
    _teak_flowers(s, 15.5, 6.6, 7.5)


def teak_2(s):
    """高窄卵团，右下侧枝一小团。"""
    s.mark_w = (1.9, 3.0)
    s.shadow(7.5)
    s.tubes([("M16.2 26.5 Q19.5 24.5 22 23", .9)],
            tones=TEAK_BARK, trunks=[(((15.5, 38), (16.3, 14), 2.6, 1.3), {"bend": 0.02, "tones": TEAK_BARK})])
    s.lobe(16, 13.6, 8.6, 10.6, 9, tones=TEAK_LEAF, jitter=0.08, bump=0.4)
    s.lobe(22.8, 22.6, 3.6, 2.7, 5, tones=TEAK_LEAF, bump=0.4, marks=0.5, hatch=False)
    _teak_flowers(s, 15.6, 3.4, 5)


def teak_3(s):
    """斜干，冠偏右，左侧一小团留缺口。"""
    s.mark_w = (1.9, 3.0)
    s.shadow(8.5, cx=16.5)
    s.tubes([("M17 26 Q13 23 9.5 20.5", 1.0)],
            tones=TEAK_BARK, trunks=[(((14.5, 38), (18.5, 18), 2.7, 1.5), {"bend": 0.04, "tones": TEAK_BARK})])
    s.lobe(9, 19, 4.4, 3.3, 6, tones=TEAK_LEAF, bump=0.4, marks=0.6)
    s.lobe(20, 13.5, 10, 7.6, 9, tones=TEAK_LEAF, jitter=0.08, bump=0.4)
    _teak_flowers(s, 19.5, 6.2, 6)


def _kapok(s, trunk, branches, butt, lobes, flowers=2):
    """木棉：灰绿粗直干带刺 + 板根 + 分层平冠（冷深绿）+ 红花点。"""
    (p0, p1, w0, w1) = trunk
    s.tubes(branches, tones=KAPOK_BARK, trunks=[((p0, p1, w0, w1), {"tones": KAPOK_BARK})])
    s.buttress(*butt, tones=KAPOK_BARK)
    s.thorns(p0[0], p0[1] - 7, p1[1] + 2, lambda y: w1 + (w0 - w1) * (y - p1[1]) / (p0[1] - p1[1]))
    pts = []
    for cx, cy, rx, ry, k in lobes:
        s.lobe(cx, cy, rx, ry, k, tones=KAPOK_LEAF, squash=0.35)
        for _ in range(flowers):
            f = s.r.uniform(-0.65, 0.65)
            pts.append((cx + rx * f, cy - ry * 0.75 * math.sqrt(1 - f * f) + s.r.uniform(0, .6)))
    s.dots(pts, .62, KAPOK_FLOWER, stroke=INK)


def kapok_1(s):
    s.shadow(9.5)
    _kapok(s, ((16, 36), (16, 10), 3.0, 1.7),
           [("M16 12.5 Q11 9 7 8.5", 1.2), ("M16 12 Q21 8.5 25 8", 1.2), ("M16 18 Q20 15.5 22.5 14.5", .9)],
           (16, 9.5, 5.5, 3.1),
           [(21.8, 14, 3.8, 1.9, 5), (7.5, 7.2, 5.2, 2.4, 7), (24.5, 6.8, 5.5, 2.6, 7), (15.5, 5.4, 6.8, 2.8, 8)])


def kapok_2(s):
    s.shadow(8)
    _kapok(s, ((16, 36.5), (16, 5), 2.7, 1.4),
           [("M16 19.5 Q19.5 17.5 22 16", 1.0), ("M16 13.5 Q12.5 12 9.5 11", .9), ("M16 7.5 Q13 6 10.5 5.5", .8)],
           (16, 8, 4.5, 2.8),
           [(22.8, 15.6, 5, 2.0, 7), (9.6, 10.8, 4.4, 1.9, 6), (16.5, 4.8, 7.6, 2.4, 9)])


def kapok_3(s):
    s.shadow(10.5, cx=15.5)
    _kapok(s, ((16.5, 36), (15.5, 16), 3.4, 2.1),
           [("M15.5 19 Q10.5 16 6.5 13.5", 1.3), ("M16 18.5 Q20.5 16.5 25 15.5", 1.2), ("M16 18 Q15 14 13 11.5", 1.0)],
           (16.5, 11.5, 6.5, 3.5),
           [(25.5, 14.2, 4.2, 2.2, 6), (13.5, 10.5, 11.5, 4.6, 12)], flowers=4)


def acacia_1(s):
    """深褐细干 + 放射状斜伞骨 + 扁薄平顶（橄榄黄绿）。"""
    s.mark_w = (0.9, 1.5)
    s.shadow(10)
    s.tubes([("M15.8 29.5 Q11 25 7 18.8", .85), ("M15.8 29.5 Q13 24 11.5 18.4", .65), ("M15.9 29.5 Q16.5 24 17.2 18.4", .6),
             ("M15.9 29.5 Q20 25 21.5 18.4", .65), ("M15.9 29.5 Q21 26 25.5 18.8", .85)],
            tones=ACACIA_BARK, trunks=[(((16.4, 38), (15.9, 29), 1.6, 1.15), {"bend": 0.03, "tones": ACACIA_BARK})])
    s.lobe(16, 17.3, 13.8, 2.1, 15, tones=ACACIA_LEAF, jitter=0.07, bump=0.24, squash=0.5)
    s.lobe(12.5, 15.4, 7, 1.3, 8, tones=ACACIA_LEAF, jitter=0.07, bump=0.26, squash=0.4, marks=0.5, hatch=False)


def acacia_2(s):
    """斜干双层，冠左高右低。"""
    s.mark_w = (0.9, 1.5)
    s.shadow(9, cx=15)
    s.tubes([("M13.6 27.5 Q10 23 8 17.6", .85), ("M13.6 27.5 Q18.5 25 22.5 21", .8), ("M9.4 21.2 L5 18", .5),
             ("M13.6 27.5 Q13 22 12.6 17.4", .55)],
            tones=ACACIA_BARK, trunks=[(((18, 38), (13.6, 27.2), 1.6, 1.1), {"bend": -0.08, "tones": ACACIA_BARK})])
    s.lobe(22.6, 19.9, 7.2, 1.6, 8, tones=ACACIA_LEAF, jitter=0.07, bump=0.26, squash=0.45)
    s.lobe(8.8, 16.4, 7.8, 1.8, 9, tones=ACACIA_LEAF, jitter=0.07, bump=0.26, squash=0.45)


def acacia_3(s):
    """高干两层薄冠。"""
    s.mark_w = (0.9, 1.5)
    s.shadow(8)
    s.tubes([("M16 23 Q12 18 9.5 13", .8), ("M16 23 Q20 18 22.5 13", .8), ("M16 23 L16.2 13.5", .6),
             ("M16 29 Q18.5 25 21.5 21.5", .6)],
            tones=ACACIA_BARK, trunks=[(((16, 38), (16, 22.5), 1.5, 1.1), {"bend": 0.03, "tones": ACACIA_BARK})])
    s.lobe(21.8, 20.8, 4.8, 1.2, 6, tones=ACACIA_LEAF, jitter=0.07, bump=0.26, squash=0.45, marks=0.5)
    s.lobe(16, 12.3, 11.5, 1.8, 12, tones=ACACIA_LEAF, jitter=0.07, bump=0.24, squash=0.5)


def _bottle(cx, wb, wt, yt, bulge):
    return (f"M{n(cx - wb / 2)} 38 C{n(cx - wb / 2 - bulge)} 32 {n(cx - wt / 2 - bulge * 0.3)} {n(yt + 5)} {n(cx - wt / 2)} {n(yt)}"
            f" L{n(cx + wt / 2)} {n(yt)} C{n(cx + wt / 2 + bulge * 0.3)} {n(yt + 5)} {n(cx + wb / 2 + bulge)} 32 {n(cx + wb / 2)} 38"
            f" Q{n(cx)} 38.8 {n(cx - wb / 2)} 38Z")


def _folds(s, cx, wb, yt, k=4):
    segs = []
    for i in range(k):
        x = cx - wb * 0.3 + wb * 0.6 * i / (k - 1)
        segs.append(f"M{n(x + s.r.uniform(-.3, .3))} 37.3Q{n(x + (x - cx) * 0.2)} {n((37 + yt) / 2)} {n(cx + (x - cx) * 0.45)} {n(yt + 1.5)}")
    s.add(f'<path d="{"".join(segs)}" fill="none" stroke="{INK}" stroke-width=".4" opacity=".55"/>')


def baobab_1(s):
    s.shadow(9)
    s.tubes([("M13.6 20 Q11 17 8.5 12.5 L7 10.8", 1.8), ("M15 19.5 Q14 15 12.5 9.5", 1.5),
             ("M17 19.5 Q18.5 15 19.5 9", 1.5), ("M18.4 20 Q21 17 24 12.5 L26 10.6", 1.8)])
    d = _bottle(16, 12.5, 6, 19, 1.4)
    s.crown(d, (9.5, 19, 22.5, 38), BAOBAB, marks=0, s1=0.82, s2=0.42)
    _folds(s, 16, 12.5, 19)
    for cx, cy, rx in ((7.2, 10.2, 2.7), (12.3, 8.3, 2.4), (19.8, 7.8, 2.6), (25.6, 10, 2.5)):
        s.lobe(cx, cy, rx, 1.6, 5, bump=0.35, marks=0.4, hatch=False)


def baobab_2(s):
    s.shadow(10)
    s.tubes([("M13 23.5 Q10.5 21.5 8.5 18.5", 1.9), ("M15.5 23 Q15 20 14.5 17", 1.5), ("M18.5 23.5 Q21.5 21 23.5 18", 1.9),
             ("M8.8 19 L7 18", .9), ("M23.2 18.5 L25 16.4", .9)])
    d = _bottle(16, 14.5, 8, 23, 2.4)
    s.crown(d, (8, 23, 24, 38), BAOBAB, marks=0, s1=0.82, s2=0.42)
    _folds(s, 16, 14.5, 23, 5)
    for cx, cy, rx in ((7.2, 17.2, 2.2), (14.4, 15.6, 2.0), (24.6, 15.4, 2.3)):
        s.lobe(cx, cy, rx, 1.4, 5, tones=DRY, bump=0.35, marks=0.3, hatch=False)


def baobab_3(s):
    s.shadow(6.5)
    s.tubes([("M14.2 13.5 Q11 11.5 8 11", 1.0), ("M15.2 13 Q14 10.5 12.5 9", 0.9), ("M16.8 13 Q18 10.5 19.5 9", 0.9),
             ("M17.8 13.5 Q21 11.5 24 11", 1.0)])
    d = _bottle(16, 7, 4.8, 13, 0.5)
    s.crown(d, (12, 13, 20, 38), BAOBAB, marks=0, s1=0.8, s2=0.4)
    _folds(s, 16, 7, 13, 3)
    s.lobe(16, 9.6, 9, 2.1, 10, bump=0.32, squash=0.45, marks=0.6)


def olive_1(s):
    s.mark_w = (0.8, 1.3)
    s.shadow(8.5)
    s.tubes([("M12.8 27.5 Q10.5 25 8.5 22", 1.0), ("M19.3 27.5 Q21.5 25 23.5 22", 1.0)], tones=OLIVE_BARK,
            trunks=[(((14.6, 38), (12.6, 27), 2.2, 1.3), {"bend": -0.18, "tones": OLIVE_BARK}),
                    (((17.4, 38), (19.4, 26.5), 2.2, 1.3), {"bend": 0.18, "tones": OLIVE_BARK})])
    s.add(f'<ellipse cx="16" cy="33.5" rx=".5" ry="1.3" fill="{INK}" opacity=".35"/>')
    s.lobe(16, 19.2, 11.5, 6.4, 12, tones=OLIVE, jitter=0.15, bump=0.3)
    s.lobe(10.5, 22, 4.6, 2.6, 6, tones=OLIVE, jitter=0.12, marks=0.6)


def olive_2(s):
    s.mark_w = (0.8, 1.3)
    s.shadow(8, cx=15)
    s.tubes([("M15.5 28 Q18.5 25 21 22.5", .9)], tones=OLIVE_BARK,
            trunks=[(((17.5, 38), (12, 25), 2.5, 1.2), {"k": (21, 31), "tones": OLIVE_BARK})])
    s.lobe(21.2, 21.4, 3.8, 2.5, 5, tones=OLIVE, jitter=0.12, marks=0.6)
    s.lobe(12, 18.6, 9.5, 5.6, 10, tones=OLIVE, jitter=0.15, bump=0.3)


def olive_3(s):
    s.mark_w = (0.8, 1.3)
    s.shadow(10)
    s.tubes([("M16 29.5 Q11 27 8 23", 1.3), ("M16 29.5 Q16.5 24 16 19", 1.2), ("M16 29.5 Q21 27 24 23", 1.3)], tones=OLIVE_BARK,
            trunks=[(((16, 38), (16, 29), 4.4, 2.6), {"bend": 0.03, "tones": OLIVE_BARK})])
    s.add(f'<ellipse cx="16.3" cy="34" rx=".9" ry="2.2" fill="{INK}" opacity=".55"/>')
    s.lobe(7.8, 22, 4.6, 3.3, 6, tones=OLIVE, jitter=0.12)
    s.lobe(24.2, 21.6, 4.8, 3.3, 6, tones=OLIVE, jitter=0.12)
    s.lobe(16, 17, 6.2, 4.3, 7, tones=OLIVE, jitter=0.12)


def _palm_trunk(s, p0, k, p1, w0, w1):
    d, left, right = limb_d(p0, p1, w0, w1, k, steps=16)
    s.trunk(p0, p1, w0, w1, k=k, bark=False)
    rings = "".join(f"M{pt(left[i])}L{pt(right[i])}" for i in range(1, 16))
    s.add(f'<path d="{rings}" fill="none" stroke="{INK}" stroke-width=".4" opacity=".7"/>')


def palm_1(s):
    s.shadow(7, cx=15.5)
    _palm_trunk(s, (16.5, 38), (13.5, 24), (17.5, 10), 1.9, 1.2)
    s.palm_crown((17.5, 9.5), [(-172, 11, 5), (-140, 10, 2), (-105, 7, 1), (-68, 8, 1.2), (-32, 10.5, 3),
                               (0, 11, 5.5), (40, 7.5, 4.5), (148, 8, 4.5)])


def palm_2(s):
    s.shadow(7, cx=17)
    _palm_trunk(s, (19, 38), (19.5, 22), (10.5, 11), 2.0, 1.2)
    s.palm_crown((10.5, 10.5), [(-178, 9.5, 5), (-145, 9, 2), (-100, 7, 1), (-60, 9, 1.5), (-20, 11, 4),
                                (15, 10.5, 6.5), (150, 7, 5)])


def palm_3(s):
    s.shadow(8)
    _palm_trunk(s, (16, 38), (15.6, 32), (16, 25.5), 2.4, 1.9)
    s.palm_crown((16, 25), [(-170, 12, 7), (-135, 11, 3.5), (-98, 10, 1.2), (-60, 11, 2.5), (-18, 12, 6.5),
                            (160, 9, 6), (25, 9, 6.5)], nuts=False)


def palm_4(s):
    s.shadow(8.5)
    _palm_trunk(s, (15, 38), (12, 26), (8.5, 13.5), 1.7, 1.1)
    s.palm_crown((8.5, 13), [(-175, 7.5, 4), (-130, 7, 1.5), (-80, 6.5, 1), (-35, 7.5, 2.5), (5, 7.5, 4.5), (150, 6, 4)],
                 nuts=False)
    _palm_trunk(s, (17, 38), (20.5, 24), (22.5, 8.5), 1.8, 1.1)
    s.palm_crown((22.5, 8), [(-170, 8.5, 4.5), (-135, 8, 2), (-95, 6.5, 1), (-55, 7.5, 1.5), (-15, 8.5, 4), (25, 7, 5),
                             (155, 6.5, 4)])


def _skirt(s, x, y0, y1, w):
    segs = []
    y = y0
    while y < y1:
        segs.append(f"M{n(x - w / 2)} {n(y)}l{n(w / 4)} 1.1M{n(x)} {n(y + 0.3)}l0 1.1M{n(x + w / 2)} {n(y)}l{n(-w / 4)} 1.1")
        y += 1.6
    s.add(f'<path d="{"".join(segs)}" fill="none" stroke="{INK}" stroke-width=".4" opacity=".6"/>')


def joshua_1(s):
    s.shadow(8)
    s.tubes([("M16 27 Q12 24.5 10.5 19.5 Q10 16.5 8 14", 1.4), ("M10.6 20 Q12.5 17.5 13.5 14.5", 1.0),
             ("M16 27 Q20 24.5 21 20 Q22 17 24.5 14.5", 1.4), ("M21 20.5 Q19 18 18.5 16", 1.0)],
            trunks=[(((16, 38), (16, 26), 2.5, 1.9), {"bark": False})])
    _skirt(s, 16, 27, 37, 2.2)
    for x, y, ro in ((18.5, 14.5, 2.8), (7.8, 13.2, 3.1), (13.6, 13.4, 2.9), (24.7, 13.6, 3.1)):
        s.star(x, y, ro, ro * 0.42, 9)


def joshua_2(s):
    s.shadow(6)
    s.tubes([("M16.5 18 Q14 14.5 12.5 11", 1.2), ("M16.5 18 Q19 14 19.5 9", 1.2)],
            trunks=[(((16, 38), (16.5, 17), 2.1, 1.5), {"bend": 0.03, "bark": False})])
    _skirt(s, 16.2, 19, 37, 1.8)
    s.star(12.3, 10.2, 3.1, 1.3, 9)
    s.star(19.6, 7.8, 3.3, 1.4, 9)


def joshua_3(s):
    s.shadow(10)
    s.tubes([("M16 30.5 Q11 29 7.5 25 Q5.5 22.5 5 20", 1.4), ("M8 25.5 Q9.5 22 10.5 19", 1.0),
             ("M16 30.5 Q16.5 25 15.5 19", 1.2), ("M16 30.5 Q21 28.5 23.5 24 Q24.5 22 27 21", 1.4),
             ("M23.3 24.5 Q21.5 21.5 20.5 19", 1.0)],
            trunks=[(((16, 38), (16, 30), 3.0, 2.4), {"bark": False})])
    _skirt(s, 16, 31, 37, 2.6)
    for x, y, ro in ((10.6, 18.5, 2.6), (20.4, 18.4, 2.6), (4.9, 19.4, 2.8), (15.5, 17.6, 2.9), (27, 20.3, 2.8)):
        s.star(x, y, ro, ro * 0.42, 9)


def cactus_1(s):
    s.shadow(5.5)
    s.tubes([("M16 37.5 L16 10.5", 4.4), ("M16 27 L12.5 27 Q10.8 27 10.8 25.2 L10.8 17.5", 3.0),
             ("M16 23 L19.6 23 Q21.3 23 21.3 21.3 L21.3 15", 3.0)], tones=LEAF, ribs=True)


def cactus_2(s):
    s.shadow(6)
    s.tubes([("M16 37.5 L16 6.5", 4.0), ("M16 30 L11.8 30 Q10.4 30 10.4 28.6 L10.4 22.5", 2.8),
             ("M16 19 L12.6 19 Q11.4 19 11.4 17.8 L11.4 12.5", 2.5), ("M16 25 L20.6 25 Q22 25 22 23.6 L22 15.5", 2.9)],
            tones=LEAF, ribs=True)


def cactus_3(s):
    s.shadow(8)
    pads = [(9.2, 19.5, 2.4, 3.0, -35), (22.6, 18.6, 2.6, 3.2, 30), (16.3, 21.5, 2.7, 3.3, 5),
            (11.6, 26.3, 3.2, 3.8, -25), (20.4, 25.8, 3.4, 4.0, 20), (16, 32.8, 4.0, 4.8, 0)]
    for cx, cy, rx, ry, rot in pads:
        d = f"M{n(cx - rx)} {n(cy)}A{n(rx)} {n(ry)} 0 1 1 {n(cx + rx)} {n(cy)}A{n(rx)} {n(ry)} 0 1 1 {n(cx - rx)} {n(cy)}Z"
        s.add(f'<g transform="rotate({rot} {n(cx)} {n(cy)})">')
        s.crown(d, (cx - rx, cy - ry, cx + rx, cy + ry), LEAF, marks=0, s1=0.82, s2=0.45, ow=0.75)
        spines = [(cx + dx * rx * 0.55, cy + dy * ry * 0.55) for dx, dy in ((-0.6, -0.5), (0.3, -0.7), (0.7, 0.1), (-0.2, 0.2), (0.4, 0.75), (-0.7, 0.6))]
        s.dots(spines, 0.2, INK, opacity=0.6)
        s.add("</g>")
    s.dots([(8.2, 16.6), (10.6, 16.9), (23.6, 15.6), (16.3, 18.3)], 0.75, SAKURA[1], stroke=INK)


def cactus_4(s):
    s.shadow(8)
    s.tubes([("M15.5 37.5 Q13 28 8 19", 2.4), ("M16.5 37.5 Q24 29 24.5 20.5", 2.4), ("M15.5 37.5 Q14 25 11.5 12", 2.7),
             ("M16.5 37.5 Q19.5 25 20.5 13", 2.7), ("M16 37.5 Q16 22 16 8", 3.0)], tones=LEAF, ribs=True)


def _dragon_cap(s, tips, ry, pad=2.4, rx_min=0.0, cx=None, marks=1.0):
    """盖住所有末梢的密实倒伞冠：底边在最低末梢处，末梢全藏在冠下。"""
    cx = sum(x for x, _ in tips) / len(tips) if cx is None else cx
    rx = max(rx_min, max(abs(x - cx) for x, _ in tips) + pad)
    yb = max(y for _, y in tips) + 0.5
    s.dome(cx, yb, rx, ry, max(6, int(rx * 0.95)), tones=DRAGON_LEAF, marks=marks, bump=0.22)


def dragonblood_1(s):
    """灰白短粗干，三次二叉，宽厚倒伞（深蓝绿）。"""
    s.shadow(9.5)
    items, tips = forks((16, 30), -90, 3.4, 2.1, 4, 42, 0.86)
    s.tubes(items, tones=DRAGON_BARK, trunks=[(((16, 38), (16, 29.6), 3.8, 2.7), {"tones": DRAGON_BARK})])
    _dragon_cap(s, tips, 6.6, rx_min=12)


def dragonblood_2(s):
    """干更高、分叉少，小而高的蘑菇盖。"""
    s.shadow(7)
    items, tips = forks((16, 26.5), -90, 2.8, 1.8, 3, 36, 0.86)
    s.tubes(items, tones=DRAGON_BARK, trunks=[(((16, 38), (16, 26.1), 3.2, 2.4), {"tones": DRAGON_BARK})])
    _dragon_cap(s, tips, 7.6, rx_min=8.5)


def dragonblood_3(s):
    """一分为二后各自再叉，左右两顶高低不一的伞。"""
    s.shadow(9.5)
    left, lt = forks((15.4, 31), -132, 3.6, 1.9, 3, 32, 0.84)
    right, rt = forks((16.6, 31), -58, 4.6, 1.9, 3, 32, 0.84)
    s.tubes(left + right, tones=DRAGON_BARK, trunks=[(((16, 38), (16, 30.6), 3.8, 3.0), {"tones": DRAGON_BARK})])
    _dragon_cap(s, lt, 4.8, pad=2.0, rx_min=5.5)
    _dragon_cap(s, rt, 5.8, pad=2.0, rx_min=6.5)


def _blossom(s, box, k_light=12, k_dark=8):
    s.dots(s.scatter(box, k_light, True), 0.38, "#f8e9ea")
    s.dots(s.scatter(box, k_dark, False), 0.34, "#9c6371")


def cherry_1(s):
    s.shadow(9)
    s.tubes([("M15.2 28 Q12 25 9 22.5", 1.2), ("M15.3 27.5 Q18.5 24 22.5 21.5", 1.2), ("M15.2 27.5 Q15.5 23 16 19.5", 1.0)],
            trunks=[(((16, 38), (15.2, 27), 2.3, 1.7), {"bend": 0.05})])
    s.lobe(16, 17.5, 11.5, 7.8, 12, tones=SAKURA, jitter=0.14, bump=0.3, marks=0.6)
    s.add(f'<path d="M13.5 24.5 Q12 22 10 21 M18 23.5 Q19.5 21 21.5 20" fill="none" stroke="{BARK[0]}" stroke-width=".7"/>')
    _blossom(s, (4.5, 9.7, 27.5, 25.3))


def cherry_2(s):
    s.shadow(8)
    s.trunk((16, 38), (16, 19), 2.3, 1.5, bend=-0.03)
    for cx, cy in ((8.3, 23.8), (23.7, 23.8)):
        s.lobe(cx, cy, 2.5, 6.2, 7, tones=SAKURA, jitter=0.12, bump=0.3, marks=0.4, hatch=False)
    for cx, cy in ((12.2, 25.6), (19.8, 25.6)):
        s.lobe(cx, cy, 2.5, 6.4, 7, tones=SAKURA, jitter=0.12, bump=0.3, marks=0.4, hatch=False)
    s.lobe(16, 17, 9.5, 6.4, 11, tones=SAKURA, jitter=0.1, bump=0.3, marks=0.6)
    strands = "M9 22Q8.5 26 8.8 30M12.5 22.5Q12 27 12.4 31.5M19.5 22.5Q20 27 19.6 31.5M23 22Q23.5 26 23.2 30"
    s.add(f'<path d="{strands}" fill="none" stroke="{INK}" stroke-width=".4" opacity=".55"/>')
    _blossom(s, (6.5, 10.6, 25.5, 30), 14, 8)


def cherry_3(s):
    s.shadow(9, cx=15)
    s.tubes([("M15 31 Q18 27 21 23", 1.1), ("M12.5 26 Q10 22.5 8 20", 1.0)],
            trunks=[(((18, 38), (11.5, 24.5), 2.6, 1.5), {"k": (19.5, 30)})])
    s.lobe(21.3, 20.8, 5, 3.6, 7, tones=SAKURA, jitter=0.12, marks=0.6)
    s.lobe(10, 17.8, 7.6, 5.6, 9, tones=SAKURA, jitter=0.14, marks=0.6)
    _blossom(s, (2.4, 12.2, 17.6, 23.4), 9, 6)
    _blossom(s, (16.3, 17.2, 26.3, 24.4), 5, 3)


def _bamboo(s, culms, leaves, width=1.5, shadow=6.0):
    s.shadow(shadow)
    s.tubes([(f"M{pt(p0)} Q{pt(k)} {pt(p1)}", w) for p0, k, p1, w in [(c[0], c[1], c[2], c[3] if len(c) > 3 else width) for c in culms]],
            tones=CULM, ow=0.65)
    nodes = []
    for c in culms:
        p0, k, p1 = c[0], c[1], c[2]
        w = (c[3] if len(c) > 3 else width) / 2 + 0.55
        for i in range(1, 9):
            t = i / 9
            p = quad(p0, k, p1, t)
            tx, ty = unit(quad_tan(p0, k, p1, t))
            nodes.append(f"M{n(p[0] - ty * w)} {n(p[1] + tx * w)}L{n(p[0] + ty * w)} {n(p[1] - tx * w)}")
    s.add(f'<path d="{"".join(nodes)}" fill="none" stroke="{INK}" stroke-width=".45"/>')
    order = sorted(leaves, key=lambda lf: lf[4])
    for ci, t, ang, length, tone in order:
        c = culms[ci]
        p = quad(c[0], c[1], c[2], t)
        s.frond(p, ang, length, length * 0.25, LEAF[tone], w=1.25, ticks=False, ow=0.5)


def bamboo_1(s):
    culms = [((15, 38), (14, 22), (10.5, 6)), ((16, 38), (16.5, 20), (15, 3)), ((17, 38), (18.5, 22), (21, 5)),
             ((17.5, 38), (21, 25), (25, 11.5))]
    leaves = []
    for ci, side in ((0, -1), (1, -1), (2, 1), (3, 1)):
        for t in (0.55, 0.72, 0.88, 1.0):
            base = -150 if side < 0 else -30
            leaves += [(ci, t, base + s.r.uniform(-20, 20), s.r.uniform(3.6, 4.6), 2 if side < 0 else 0),
                       (ci, t, base + 160 * (1 if side < 0 else -1) * 0.5 + s.r.uniform(-15, 15), s.r.uniform(3.2, 4.2), 1)]
    _bamboo(s, culms, leaves)


def bamboo_2(s):
    culms = [((15, 38), (16, 20), (22.5, 4.5), 1.35), ((16.5, 38), (19, 24), (26, 11), 1.15)]
    leaves = []
    for ci in (0, 1):
        for t in (0.45, 0.62, 0.78, 0.92, 1.0):
            leaves += [(ci, t, -20 + s.r.uniform(-15, 25), s.r.uniform(3.8, 4.8), 0),
                       (ci, t, 165 + s.r.uniform(-20, 15), s.r.uniform(3.0, 4.0), 2)]
    _bamboo(s, culms, leaves, shadow=6.5)


def bamboo_3(s):
    culms = [((13.5, 38), (12, 28), (7.5, 17)), ((14.5, 38), (14, 26), (11.5, 14)), ((15.5, 38), (15.5, 26), (15, 12.5)),
             ((16.5, 38), (17.5, 27), (19.5, 13.5)), ((17.5, 38), (20, 28), (23, 16)), ((18.5, 38), (22.5, 31), (26.5, 22))]
    leaves = []
    for ci in range(6):
        for t in (0.5, 0.68, 0.84, 1.0):
            left = ci < 3
            leaves += [(ci, t, (-155 if left else -25) + s.r.uniform(-25, 25), s.r.uniform(3.4, 4.4), 2 if left else 0),
                       (ci, t, (150 if left else 30) + s.r.uniform(-15, 15) - (0 if left else 0), s.r.uniform(3.0, 3.8), 1)]
    _bamboo(s, culms, leaves, width=1.35, shadow=8.5)


def _mangrove(s, roots, trunk, crowns, water=True):
    if water:
        s.add('<path d="M3.5 37.4H8.5M12 38.4H19.5M22.5 37.4H28.5" fill="none" stroke="#6f8f8c" stroke-width=".5" opacity=".75"/>')
    s.tubes([(d, w) for d, w in roots], trunks=[trunk])
    for c in crowns:
        s.lobe(*c)


def mangrove_1(s):
    s.shadow(9.5)
    roots = [("M16 29 Q10.5 28.5 7.5 38", .85), ("M16 30.5 Q12.5 31.5 11.5 38", .85), ("M16 30.5 Q19.5 31.5 20.5 38", .85),
             ("M16 29 Q21.5 28.5 24.5 38", .85), ("M15.5 27 Q7.5 26.5 4.5 37.8", .75), ("M16.5 27 Q24.5 26.5 27.5 37.8", .75),
             ("M10 22 Q9.5 30 9.5 38", .5), ("M22.5 22 Q23 30 22.5 38", .5)]
    _mangrove(s, roots, (((16, 31.5), (16, 21), 2.1, 1.4), {}), [(16, 16.2, 11.2, 7.4, 11)])


def mangrove_2(s):
    s.shadow(11)
    roots = [("M15 29 Q8 28 4 37.8", .8), ("M15.5 30 Q11 30.5 9 38", .85), ("M16 31 Q14 33 13.5 38", .8),
             ("M16.5 31 Q19 33 19 38", .8), ("M17 30 Q22 30.5 23.5 38", .85), ("M17.5 29 Q24.5 28 28 37.8", .8),
             ("M7 22 Q6.5 30 6.5 38", .5), ("M25 21.5 Q25.5 30 25.5 38", .5)]
    _mangrove(s, roots, (((16, 31.5), (16, 24), 2.2, 1.6), {}),
              [(9.8, 20.5, 7.2, 4.4, 9), (22.4, 19.2, 7.6, 5, 9)])


def mangrove_3(s):
    s.shadow(8)
    roots = [("M16 25 Q10 25.5 8.5 38", .8), ("M16 26.5 Q12.5 29 12.5 38", .8), ("M16 26.5 Q19.5 29 19.5 38", .8),
             ("M16 25 Q22 25.5 23.5 38", .8), ("M16 24 Q8 23 5.5 37.5", .7), ("M16 24 Q24 23 26.5 37.5", .7),
             ("M16 28 Q15.5 33 16 38", .7)]
    _mangrove(s, roots, (((16, 27.5), (16.5, 16), 1.9, 1.3), {"bend": 0.03}), [(16.5, 12.6, 8.2, 6.2, 9)])


def silverleaf_1(s):
    s.shadow(7)
    s.tubes([("M15.4 37.6 Q13.6 37.6 12.2 38.3", .7), ("M16.6 37.6 Q18.4 37.6 19.8 38.3", .7)], tones=PALE_BARK,
            trunks=[(((16, 38), (16, 19), 2.0, 1.0), {"tones": PALE_BARK})])
    s.lobe(16, 14.5, 7.8, 11, 13, tones=SILVER, jitter=0.06, bump=0.25)
    s.lobe(11.8, 21.5, 3.6, 2.8, 6, tones=SILVER, jitter=0.08, marks=0.5)
    s.lobe(20.4, 20.3, 3.6, 2.8, 6, tones=SILVER, jitter=0.08, marks=0.5)
    for x, y, sz in ((12.5, 9, 1.0), (10.5, 14.5, 0.8), (14.8, 5.8, 0.7)):
        s.sparkle(x, y, sz)


def silverleaf_2(s):
    s.shadow(8)
    s.tubes([("M16 25 Q12.5 21 11 15", 1.2), ("M16 25 Q19.5 20 21 13", 1.2)], tones=PALE_BARK,
            trunks=[(((16, 38), (16, 24.5), 2.1, 1.6), {"tones": PALE_BARK})])
    s.lobe(10.6, 14.2, 5, 8.2, 10, tones=SILVER, jitter=0.07, bump=0.25)
    s.lobe(21.6, 11.4, 5.5, 9, 11, tones=SILVER, jitter=0.07, bump=0.25)
    for x, y, sz in ((8.5, 10, 0.9), (19.2, 6.5, 0.9), (10, 16.5, 0.6)):
        s.sparkle(x, y, sz)


def silverleaf_3(s):
    s.shadow(10)
    s.trunk((16, 38), (16, 8), 2.6, 1.0, tones=PALE_BARK)
    s.lobe(16, 26.4, 10.5, 2.9, 11, tones=SILVER, jitter=0.07, bump=0.3, squash=0.3)
    s.lobe(16, 19.4, 8.4, 3.1, 10, tones=SILVER, jitter=0.07, bump=0.3, squash=0.3)
    s.lobe(16, 12.8, 6, 3.2, 8, tones=SILVER, jitter=0.07, bump=0.3, squash=0.3)
    s.lobe(16, 7.4, 3.4, 2.7, 6, tones=SILVER, jitter=0.07, bump=0.3, marks=0.4, hatch=False)
    for x, y, sz in ((9, 24.6, 0.8), (11, 17.6, 0.8), (13.5, 6, 0.8)):
        s.sparkle(x, y, sz)


def gloomwood_1(s):
    s.shadow(7.5)
    s.tubes([("M15 23 Q12 20 11 16.5 Q10.5 13 7.8 11.2 L6 9.8", 1.3), ("M11.2 16.5 Q13 14 12.8 10.4 L12 8.5", .8),
             ("M15.2 22.5 Q18 19 20 15.8 Q21.5 13 24.3 12.6 L26.5 11", 1.3), ("M20 15.8 Q19 12.5 20.4 9.3 L21.5 7.3", .8),
             ("M15 22.5 Q15.6 17 15 13.5 L14.5 11", 1.0), ("M14.6 37 Q12 37.3 10 38.2", .9), ("M17.6 37 Q20 37.4 22 38.2", .9)],
            tones=GLOOM_BARK, trunks=[(((16, 38), (15, 22), 3.2, 1.6), {"k": (19.5, 31), "tones": GLOOM_BARK})])
    s.add(f'<ellipse cx="17" cy="31" rx=".8" ry="1.8" fill="#241e22"/>')


def gloomwood_2(s):
    s.shadow(7, cx=15)
    s.tubes([("M13.6 24.5 Q19 22.5 22.5 18.5 Q24.5 16 25.5 12.5 L26.6 10.5", 1.2), ("M22.4 18.6 L25.5 18.2", .6),
             ("M13 21 Q9.5 19.5 8 16.5", .8), ("M18.5 37.4 Q21 37.6 23 38.3", .9)],
            tones=GLOOM_BARK, trunks=[(((17, 38), (12, 18), 2.9, 1.8), {"k": (18.5, 27), "tones": GLOOM_BARK})])
    s.add(f'<path d="M11 18.5 L11.1 16.4 L11.7 17.6 L12.2 15.4 L12.6 17.2 L13 16.6 L13 18.4Z" fill="{GLOOM_BARK[0]}" stroke="{INK}" stroke-width=".6"/>')
    s.add('<ellipse cx="15.6" cy="29.5" rx=".6" ry="1.4" fill="#241e22"/>')


def gloomwood_3(s):
    s.shadow(9)
    s.tubes([("M16 24 Q12 21 9.5 18", 1.2), ("M16 23.5 Q20 20 22 16", 1.2), ("M16 23.5 Q16.5 18 15.5 13", 1.0),
             ("M9.6 18.2 L7 18.8", .6), ("M22 16.2 L25 16.6", .6)],
            tones=GLOOM_BARK, trunks=[(((16, 38), (16, 23), 2.9, 1.6), {"bend": -0.05, "tones": GLOOM_BARK})])
    for c in ((9.5, 17, 4.2, 2.5, 7), (21.8, 15.6, 4.6, 2.8, 7), (15.5, 12, 3.6, 2.4, 6)):
        s.lobe(*c, tones=GLOOM_LEAF, jitter=0.3, bump=0.22, marks=0.5, hatch=False)
    moss = "M7.5 18.8Q7.3 21 7.8 23.2M11 19Q11.2 21.5 10.8 23.5M19.5 17.6Q19.4 20.5 19.9 22.5M23.5 17.8Q23.8 20 23.4 21.6M14 13.8Q13.8 16 14.2 17.5"
    s.add(f'<path d="{moss}" fill="none" stroke="#6b6068" stroke-width=".55" opacity=".9"/>')


def _mushroom(s, cx, yb, rx, h, stem, sw, spots=7, tilt=0.0, cap_t=CAP, stem_t=STEM, spot=("#f0e2c4", "#d9c7a4"),
              gill_c="#d9c39b", pinch=1.0, peak=1.3, ribs=False):
    """pinch<1 收窄控制点成钟形；ribs 画伞面放射纹。"""
    s.tubes([(stem, sw)], tones=stem_t, ow=0.7)
    if tilt:
        s.add(f'<g transform="rotate({n(tilt)} {n(cx)} {n(yb)})">')
    gill = f"M{n(cx - rx + 0.8)} {n(yb)} C{n(cx - rx * 0.5)} {n(yb + h * 0.32)} {n(cx + rx * 0.5)} {n(yb + h * 0.32)} {n(cx + rx - 0.8)} {n(yb)}Z"
    s.add(f'<path d="{gill}" fill="{gill_c}" stroke="{INK}" stroke-width=".6"/>')
    lines = "".join(f"M{n(cx)} {n(yb - 0.2)}L{n(cx + (rx - 1) * f)} {n(yb + h * 0.24 * (1 - f * f) + 0.05)}" for f in (-0.8, -0.5, -0.2, 0.15, 0.45, 0.75))
    s.add(f'<path d="{lines}" fill="none" stroke="{INK}" stroke-width=".35" opacity=".6"/>')
    kx = rx * pinch
    cap = (f"M{n(cx - rx)} {n(yb)} C{n(cx - kx)} {n(yb - h * peak)} {n(cx + kx)} {n(yb - h * peak)} {n(cx + rx)} {n(yb)}"
           f" C{n(cx + rx * 0.6)} {n(yb + h * 0.18)} {n(cx - rx * 0.6)} {n(yb + h * 0.18)} {n(cx - rx)} {n(yb)}Z")
    s.crown(cap, (cx - rx, yb - h, cx + rx, yb + h * 0.12), cap_t, marks=0, s1=0.82, s2=0.45)
    if ribs:
        rb = "".join(f"M{n(cx + f * rx * 0.88)} {n(yb - 0.4)}Q{n(cx + f * rx * 0.62)} {n(yb - h * 0.45)} {n(cx + f * rx * 0.2)} {n(yb - h * 0.82)}"
                     for f in (-0.66, -0.33, 0.0, 0.33, 0.66))
        s.add(f'<path d="{rb}" fill="none" stroke="{INK}" stroke-width=".38" opacity=".55"/>')
    out = []
    for _ in range(spots * 6):
        if len(out) >= spots:
            break
        f = s.r.uniform(-0.8, 0.8)
        top = h * 0.97 * (1 - f * f)
        y = yb - s.r.uniform(0.2, 0.85) * top
        x = cx + f * rx * 0.92
        if any(math.hypot(x - a, y - b) < rx * 0.22 for a, b, _ in out):
            continue
        out.append((x, y, s.r.uniform(0.45, 0.85) * min(1.0, rx / 6)))
    s.add("".join(f'<ellipse cx="{n(x)}" cy="{n(y)}" rx="{n(r * 1.25)}" ry="{n(r * 0.85)}" fill="{spot[0] if x < cx + rx * 0.3 else spot[1]}" stroke="{INK}" stroke-width=".35"/>' for x, y, r in out))
    if tilt:
        s.add("</g>")


def mushroom_1(s):
    s.shadow(7)
    s.add(f'<ellipse cx="16" cy="36.9" rx="2.8" ry="1.3" fill="{STEM[0]}" stroke="{INK}" stroke-width=".7"/>')
    _mushroom(s, 16, 16, 11, 8.5, "M16.2 37 Q14.8 27 16 17.5", 3.4, spots=8)
    s.add(f'<path d="M13.6 21 Q16 22.6 18.6 21" fill="none" stroke="{INK}" stroke-width=".5"/>')


SHELF_WOOD = ("#5e4c3e", "#86705a")


def _bracket(s, x, y, w, h, side):
    """层叠架状菌的一片：贴干的半月托盘，上面两道生长环，下缘浅色菌孔面。"""
    tip = x + side * w
    edge = f"M{n(x)} {n(y - h)} C{n(x + side * w * 0.6)} {n(y - h * 1.15)} {n(tip)} {n(y - h * 0.6)} {n(tip)} {n(y)}"
    d = edge + f" Q{n(x + side * w * 0.5)} {n(y + h * 0.42)} {n(x)} {n(y + h * 0.2)}Z"
    s.add(f'<path d="M{n(x)} {n(y + h * 0.2)} Q{n(x + side * w * 0.5)} {n(y + h * 0.42)} {n(tip)} {n(y)}" '
          f'fill="none" stroke="#f2d9a6" stroke-width="1.1"/>')
    s.crown(d, (min(x, tip), y - h, max(x, tip), y + h * 0.3), SHELF, marks=0, s1=0.8, s2=0.42)
    rings = "".join(f'<path d="{edge}" transform="{about((x, y), f)}"/>' for f in (0.45, 0.72))
    s.add(f'<g fill="none" stroke="{INK}" stroke-width=".38" opacity=".55">{rings}</g>')


def mushroom_2(s):
    """层叠架状菌：枯桩上左右交错的橙褐托盘。"""
    s.shadow(8.5)
    s.trunk((16, 38), (16.3, 9.6), 5.0, 3.8, tones=SHELF_WOOD)
    s.add(f'<path d="M14.4 10 L14.9 7.6 L15.9 8.9 L16.7 6.4 L17.4 8.7 L18 7.9 L18.2 10Z" fill="{SHELF_WOOD[0]}" stroke="{INK}" stroke-width=".7"/>')
    for x, y, w, h, side in ((14.6, 31.5, 6.4, 2.6, -1), (17.6, 27, 7, 2.8, 1), (14.6, 21.8, 6, 2.5, -1),
                             (17.6, 17, 5.4, 2.3, 1), (14.8, 13, 4, 1.8, -1), (17.4, 10.6, 3, 1.4, 1)):
        _bracket(s, x, y, w, h, side)


def mushroom_3(s):
    """黄褐平盖，斜伞 + 脚边小菇。"""
    s.shadow(7.5)
    kw = dict(cap_t=OCHRE, spot=("#efdcaa", "#cfb47a"), gill_c="#e3cfa0")
    _mushroom(s, 17.5, 12.5, 12.2, 4.4, "M15 37.5 Q13.5 25 17.2 13", 2.2, spots=6, tilt=-8, peak=1.15, ribs=True, **kw)
    _mushroom(s, 23, 35, 2.5, 2.2, "M23 38 L23 35.5", 1.5, spots=0, **kw)


def mushroom_4(s):
    """紫色细高钟形伞，旁生一小钟。"""
    s.shadow(6.5)
    kw = dict(cap_t=PURPLE, stem_t=("#a99bb0", "#d8cfe0", "#f1ecf5"), gill_c="#cdb9d8", pinch=0.62, peak=1.45, ribs=True)
    _mushroom(s, 22.4, 30.2, 3, 4.6, "M22.6 38 Q23 34 22.3 30.6", 1.4, spots=0, **kw)
    _mushroom(s, 15.6, 15.5, 5.4, 9.4, "M16 37.5 Q17.3 27 15.6 16", 2.0, spots=0, **kw)
    s.dots([(14, 9.5), (13.2, 12.5), (17.2, 11)], .45, "#d9c4ea", stroke=INK)


def mushroom_5(s):
    """蓝色荧光菌丛：三朵带光晕，周围飘孢子。"""
    s.shadow(9)
    caps = ((20.5, 18.5, 7, 5.2, "M20.5 37.5 Q21.8 28 20.6 19", 2.4, 5),
            (10.8, 25, 5.6, 4.4, "M11.4 38 Q10.2 32 10.8 25.5", 2.0, 4),
            (25.6, 31.2, 3.2, 2.7, "M25.6 38 Q26 35 25.6 31.6", 1.4, 2))
    for cx, yb, rx, h, *_ in caps:
        s.add(f'<ellipse cx="{n(cx)}" cy="{n(yb - h * 0.45)}" rx="{n(rx * 1.45)}" ry="{n(h * 1.25)}" fill="{GLOW[2]}" opacity=".32"/>')
    for cx, yb, rx, h, stem, sw, sp in caps:
        _mushroom(s, cx, yb, rx, h, stem, sw, spots=sp, cap_t=GLOW, stem_t=GLOW_STEM, spot=("#f2feff", "#bfeef7"), gill_c="#b6e2ea")
    s.dots([(7, 15.5), (14.5, 9.5), (27.5, 22), (5.5, 21.5), (16.5, 13)], .5, "#d8f7fc", stroke=GLOW[0])


def crystal_1(s):
    s.shadow(7.5)
    s.shard((15.5, 27), (8, 12), 3.0)
    s.shard((16.5, 25), (24.5, 10.5), 3.0)
    s.shard((15.5, 31), (10.5, 22), 2.0)
    s.shard((16.5, 30), (22, 21.5), 2.0)
    s.shard((16, 38), (16, 6), 4.4)
    s.shard((12.5, 38), (11, 34.5), 1.6)
    s.shard((19.5, 38), (21, 35), 1.5)
    for x, y, sz in ((14.8, 10, 1.1), (8.9, 15, 0.8), (23, 13.5, 0.7)):
        s.sparkle(x, y, sz)


def crystal_2(s):
    s.shadow(11)
    s.shard((16, 38), (16.5, 14), 4.0)
    s.shard((14.5, 38), (8.5, 21.5), 3.2)
    s.shard((17.5, 38), (24, 19.5), 3.2)
    s.shard((13, 38), (4.5, 30), 2.4)
    s.shard((19, 38), (28, 29.5), 2.4)
    s.shard((15.5, 38), (12.5, 29), 2.2)
    s.shard((17, 38), (20, 30.5), 2.0)
    for x, y, sz in ((15, 18, 1.0), (9.5, 25, 0.8), (6, 31.5, 0.6)):
        s.sparkle(x, y, sz)


def crystal_3(s):
    s.shadow(8)
    s.tubes([("M16 24 Q12.5 21 10.5 17.5", 1.4), ("M16 23 Q19.5 19 21.5 15", 1.4), ("M16 23 L16 13", 1.2)], tones=STONE,
            trunks=[(((16, 38), (16, 22.5), 3.0, 1.9), {"tones": STONE})])
    for bx, by, tips in (((10.5, 17.5), None, ((6, 12.5), (10, 10.5), (13.5, 13))),
                         ((21.5, 15), None, ((19, 9), (23, 8.5), (26.5, 12))),
                         ((16, 13), None, ((14, 6.5), (16.5, 3.5), (19, 7.5)))):
        for tx in tips:
            far = (bx[0] + (tx[0] - bx[0]) * 1.15, bx[1] + (tx[1] - bx[1]) * 1.15)
            s.shard(bx, far, 2.6)
    for x, y, sz in ((9.5, 12, 0.7), (15.8, 6, 0.8), (22.3, 10.5, 0.7)):
        s.sparkle(x, y, sz)


SPECIES = ["teak", "bamboo", "kapok", "acacia", "mangrove", "olive", "palm", "baobab", "joshua", "cactus",
           "dragonblood", "cherry", "silverleaf", "gloomwood", "mushroom", "crystal"]


def build() -> str:
    g = globals()
    syms = []
    for sp in SPECIES:
        i = 1
        while f"{sp}_{i}" in g:
            sid = f"tree-{sp}" if i == 1 else f"tree-{sp}-v{i}"
            sym = Sym(sid)
            g[f"{sp}_{i}"](sym)
            syms.append(sym.svg())
            i += 1
    head = ('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="0" height="0" style="position:absolute">\n'
            "<!-- 织梦 · 地图树木图示 B 组（暖带/特殊/奇幻 16 种）。手绘铜版加淡彩，由 tools/build_tree_art_b.py 生成，勿手改。\n"
            "     tree-{species} 为主图，tree-{species}-v2..v4 为形态变种，绘制时混排。\n"
            "     viewBox 0 0 32 40，锚点（树根落地点）(16,38) 见 data-anchor；光源左上；外轮廓 #3b2f22。 -->\n")
    return head + "\n".join(syms) + "\n</svg>\n"


def main():
    OUT.write_text(build(), encoding="utf-8", newline="\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
