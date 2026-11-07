"""Generate app/static/map-art/map-art-trees-a.svg: group-A tree symbols (8 conifers + 8 broadleaves).

Style: hand-drawn copperplate with light wash, for the old-paper atlas.
viewBox 0 0 32 40, anchor (16,38). Light comes from the upper left.
Outline #3b2f22 0.8 (the ink is laid under the fill with a 1.6 stroke so only the outer 0.8 shows);
inner lines 0.4-0.5.

Deterministic: each symbol's random stream is random.Random(20261020 ^ crc32(symbol_id)), so the same code
always produces the same file. No time, entropy or the built-in hash.

Usage: .venv\\Scripts\\python.exe tools/gen_tree_art_a.py
"""
from __future__ import annotations

import math
import random
import re
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "app" / "static" / "map-art" / "map-art-trees-a.svg"
BASE_SEED = 20261020

INK = "#3b2f22"
CON = ("#2f4a32", "#3f6140", "#5a7d4f")
BRD = ("#4f6b35", "#6d8a42", "#93a85a")
LARCH = ("#4a6a38", "#6f8c45", "#9bb062")
GOLD = ("#93652f", "#c79a4a", "#e0bf72")
AUTUMN = ("#8a4f2c", "#a8743a", "#c79a4a")
BIRCH = ("#56763a", "#7f9c4a", "#a9bd6c")
WILLOW = ("#56703a", "#7d9447", "#a8b766")
BARK = ("#5b4130", "#7a5a40")
RED_BARK = ("#6b3c2a", "#92573b")
GREY_BARK = ("#6b6354", "#958a76")
BIRCH_BARK = ("#bdb4a0", "#ece6d6")
DEAD = ("#6b5f50", "#8f8270")

TAU = 2 * math.pi


# ----------------------------------------------------------------------------- formatting / geometry
def n(v: float) -> str:
    s = f"{v:.1f}"
    if s.endswith(".0"):
        s = s[:-2]
    return "0" if s == "-0" else s


def pt(p) -> str:
    return f"{n(p[0])} {n(p[1])}"


def poly(pts, close=True) -> str:
    d = "M" + pt(pts[0]) + "L" + " ".join(pt(p) for p in pts[1:])
    return d + ("Z" if close else "")


def bez(a, c, b, t):
    u = 1 - t
    return (u * u * a[0] + 2 * u * t * c[0] + t * t * b[0], u * u * a[1] + 2 * u * t * c[1] + t * t * b[1])


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def taper(center, widths):
    """Offset a centre line both ways; returns the two sides (same order as centre)."""
    a, b = [], []
    m = len(center)
    for i, p in enumerate(center):
        q0, q1 = center[max(i - 1, 0)], center[min(i + 1, m - 1)]
        tx, ty = q1[0] - q0[0], q1[1] - q0[1]
        ln = math.hypot(tx, ty) or 1.0
        nx, ny = -ty / ln, tx / ln
        h = widths[i] / 2
        a.append((p[0] + nx * h, p[1] + ny * h))
        b.append((p[0] - nx * h, p[1] - ny * h))
    return a, b


def angle_in(th, gap):
    a = math.degrees(th) % 360
    d0, d1 = gap[0] % 360, gap[1] % 360
    return d0 <= a <= d1 if d0 <= d1 else (a >= d0 or a <= d1)


# ----------------------------------------------------------------------------- compact path data
_TOK = re.compile(r"[A-Za-z]|-?(?:\d+\.?\d*|\.\d+)")
_D_ATTR = re.compile(r' d="([^"]*)"')


def _parse(d):
    """Parse M/L/Q/Z (abs + rel) into absolute segments."""
    toks = _TOK.findall(d)
    segs, i, cmd = [], 0, None
    cur = start = (0.0, 0.0)
    while i < len(toks):
        t = toks[i]
        if t.isalpha():
            if t not in "MLQZmlqz":
                raise ValueError(f"unsupported path command {t!r}")
            cmd = t
            i += 1
            if cmd in "Zz":
                segs.append(("Z", ()))
                cur = start
            continue
        rel = cmd.islower()
        ox, oy = cur if rel else (0.0, 0.0)
        if cmd in "Mm":
            cur = start = (float(toks[i]) + ox, float(toks[i + 1]) + oy)
            i += 2
            segs.append(("M", (cur,)))
            cmd = "l" if rel else "L"
        elif cmd in "Ll":
            cur = (float(toks[i]) + ox, float(toks[i + 1]) + oy)
            i += 2
            segs.append(("L", (cur,)))
        else:
            c = (float(toks[i]) + ox, float(toks[i + 1]) + oy)
            cur = (float(toks[i + 2]) + ox, float(toks[i + 3]) + oy)
            i += 4
            segs.append(("Q", (c, cur)))
    return segs


Q = 2  # output grid: integer coordinates in half units (0.5 precision), the symbol body is wrapped in scale(.5)
SPACING_K = 1.25   # global thinning of clump clouds (fewer, slightly larger-looking clumps; smaller file)
DENSITY_K = 0.6
BUMP_CUT = 3       # scallops per clump = species value - BUMP_CUT
_SCALED = re.compile(r'\b(cx|cy|rx|ry|stroke-width)="([-\d.]+)"')


def _num(v):
    return str(v)


def scale_attrs(s):
    def f(m):
        v = float(m.group(2)) * Q
        txt = str(round(v)) if m.group(1) != "stroke-width" or abs(v - round(v)) < 0.05 else f"{v:.1f}"
        return f'{m.group(1)}="{txt}"'
    return _SCALED.sub(f, s)


def compact(d):
    """Re-encode path data on the Q grid: absolute M, relative l/q, integers, minimal separators.
    Deltas are taken between rounded absolute points, so there is no drift."""
    out, prev, last = [], None, None
    cur = start = (0, 0)

    def r(p):
        return (round(p[0] * Q), round(p[1] * Q))

    def emit(cmd, nums):
        nonlocal prev, last
        if cmd != last or cmd in "MZ":
            out.append(cmd)
            prev = None
        last = cmd
        for v in nums:
            s = _num(v)
            if prev is not None and s[0] != "-":
                out.append(" ")
            out.append(s)
            prev = s

    for cmd, pts in _parse(d):
        if cmd == "M":
            cur = start = r(pts[0])
            emit("M", cur)
        elif cmd == "Z":
            emit("Z", ())
            cur = start
        elif cmd == "L":
            p = r(pts[0])
            if p != cur:
                emit("l", (p[0] - cur[0], p[1] - cur[1]))
                cur = p
        else:
            c, p = r(pts[0]), r(pts[1])
            emit("q", (c[0] - cur[0], c[1] - cur[1], p[0] - cur[0], p[1] - cur[1]))
            cur = p
    return "".join(out)


def ell(cx, cy, rx, ry, seg=8):
    """Ellipse as quadratic path (same winding as Blob) so it can be merged with other subpaths."""
    k = 1 / math.cos(math.pi / seg)
    p = [(cx + rx * math.cos(TAU * i / seg), cy + ry * math.sin(TAU * i / seg)) for i in range(seg)]
    d = "M" + pt(p[0])
    for i in range(seg):
        a = TAU * (i + 0.5) / seg
        c = (cx + rx * k * math.cos(a), cy + ry * k * math.sin(a))
        d += "Q" + pt(c) + " " + pt(p[(i + 1) % seg])
    return d + "Z"


def inside(x, y, e, k=0.95):
    cx, cy, rx, ry = e
    return ((x - cx) / (rx * k)) ** 2 + ((y - cy) / (ry * k)) ** 2 <= 1.0


def covered(c, others, samples=12, grow=1.2):
    """True when the clump's outer edge lies inside other clumps, i.e. it never reaches the silhouette."""
    cx, cy, rx, ry = c
    for i in range(samples):
        a = TAU * i / samples
        x, y = cx + rx * grow * math.cos(a), cy + ry * grow * math.sin(a)
        if not any(inside(x, y, o) for o in others):
            return False
    return True


class Blob:
    """A scalloped closed outline in unit space; drawn at any centre/radius."""

    def __init__(self, rng, count, bump, jitter=0.07):
        ph = rng.uniform(0, TAU)
        self.pts = []
        for i in range(count):
            a = ph + TAU * i / count + rng.uniform(-0.22, 0.22) * TAU / count
            k = 1 + rng.uniform(-jitter, jitter)
            self.pts.append((math.cos(a) * k, math.sin(a) * k))
        self.bump = [bump * rng.uniform(0.7, 1.3) for _ in range(count)]

    def coarse(self):
        """Same shape with every other scallop (for inner tone layers that need less detail)."""
        c = Blob.__new__(Blob)
        c.pts = self.pts[::2]
        c.bump = self.bump[::2]
        return c

    def path(self, cx, cy, rx, ry):
        p = [(cx + x * rx, cy + y * ry) for x, y in self.pts]
        d = "M" + pt(p[0])
        for i in range(len(p)):
            a, b = p[i], p[(i + 1) % len(p)]
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            ox, oy = mx - cx, my - cy
            ol = math.hypot(ox, oy) or 1.0
            ch = math.hypot(b[0] - a[0], b[1] - a[1])
            c = (mx + ox / ol * ch * self.bump[i], my + oy / ol * ch * self.bump[i])
            d += "Q" + pt(c) + " " + pt(b)
        return d + "Z"


# ----------------------------------------------------------------------------- tree builder
class Tree:
    def __init__(self, sid):
        self.sid = sid
        self.rng = random.Random(BASE_SEED ^ zlib.crc32(sid.encode("utf-8")))
        self.shadow = (16.5, 6.0)
        self.wood = []        # (d, fill)
        self.wood_top = []    # shading / bark marks drawn over wood fills
        self.fol_ink = []     # d strings, union outline of all foliage
        self.fol = []         # foliage elements in paint order
        self.defer = {}       # attrs -> [d]: thin marks merged into one path, painted after all foliage
        self.top = []         # final overlays
        self.bbox = [99.0, 99.0, -99.0, -99.0]

    def later(self, attrs, d):
        self.defer.setdefault(attrs, []).append(d)

    def extent(self, x0, y0, x1, y1):
        b = self.bbox
        self.bbox = [min(b[0], x0), min(b[1], y0), max(b[2], x1), max(b[3], y1)]

    # -- wood
    def _limb(self, a, c, b, w0, w1, pal, *, flare=0.0, shade=True, marks=0, birch=False, steps=10):
        rng = self.rng
        ts = [i / steps for i in range(steps + 1)]
        center = [bez(a, c, b, t) for t in ts]
        widths = [w1 + (w0 - w1) * (1 - t) ** 1.2 + flare * max(0.0, 1 - t * 5) ** 2 for t in ts]
        sa, sb = taper(center, widths)
        self.wood.append((poly(sa + sb[::-1]), pal[1]))
        # shaded side = lower-right
        right, left = (sa, sb) if sum(p[0] + p[1] for p in sa) > sum(p[0] + p[1] for p in sb) else (sb, sa)
        if shade:
            inner = [(c0[0] + (r[0] - c0[0]) * 0.1, c0[1] + (r[1] - c0[1]) * 0.1) for c0, r in zip(center, right)]
            self.wood_top.append(f'<path d="{poly(inner + right[::-1])}" fill="{pal[0]}"/>')
        for _ in range(marks):
            i0 = rng.randint(0, max(0, steps - 3))
            i1 = min(steps, i0 + rng.randint(2, 3))
            f = rng.uniform(-0.35, 0.3)
            seg = [(c0[0] + (r[0] - c0[0]) * f * 2, c0[1] + (r[1] - c0[1]) * f * 2) for c0, r in zip(center[i0:i1 + 1], right[i0:i1 + 1])]
            if birch:
                continue
            self.wood_top.append(f'<path d="{poly(seg, False)}" fill="none" stroke="{INK}" stroke-width=".4" stroke-opacity=".55"/>')
        if birch:  # dark lenticels across the white bark
            for i in range(1, steps):
                if rng.random() < 0.55:
                    c0, lp, rp = center[i], left[i], right[i]
                    s0 = rng.uniform(0.0, 0.35)
                    s1 = rng.uniform(0.55, 0.9)
                    p0 = (lp[0] + (rp[0] - lp[0]) * s0, lp[1] + (rp[1] - lp[1]) * s0)
                    p1 = (lp[0] + (rp[0] - lp[0]) * s1, lp[1] + (rp[1] - lp[1]) * s1)
                    self.wood_top.append(f'<path d="M{pt(p0)}L{pt(p1)}" stroke="{INK}" stroke-width=".55"/>')
        return center, widths

    def trunk(self, a, c, b, w0, w1, pal=BARK, *, flare=0.8, marks=2, shade=True, birch=False):
        return self._limb(a, c, b, w0, w1, pal, flare=flare, marks=marks, shade=shade, birch=birch)

    def branch(self, a, c, b, w0, w1, pal=BARK, *, shade=True, birch=False):
        return self._limb(a, c, b, w0, w1, pal, shade=shade, steps=6, birch=birch)

    # -- broadleaf / clump foliage
    def crown(self, clumps, pal, *, cores=(), bumps=(6, 8), bump=0.34, marks="arc", hatch=True, light_bias=0.0,
              inner_stroke=0.42):
        rng = self.rng
        clumps = [c for c in clumps if c[2] > 0.2 and c[3] > 0.2]
        if not clumps:
            return
        # drop clumps completely hidden under clumps painted after them (paint order = top-to-bottom, left-to-right)
        srt = sorted(clumps, key=lambda c: (c[1], c[0]))
        keep = []
        for i, c in enumerate(srt):
            after = srt[i + 1:]
            pts = [(c[0], c[1])] + [(c[0] + c[2] * 1.15 * math.cos(TAU * k / 12), c[1] + c[3] * 1.15 * math.sin(TAU * k / 12))
                                    for k in range(12)]
            if not all(any(inside(x, y, o, 0.9) for o in after) for x, y in pts):
                keep.append(c)
        clumps = [c for c in clumps if c in keep]
        for cx, cy, rx, ry in cores:
            b = Blob(rng, rng.randint(9, 12), 0.25)
            d = b.path(cx, cy, rx, ry)
            self.fol_ink.append(d)
            self.fol.append(f'<path d="{d}" fill="{pal[0]}"/>')
        blobs = [Blob(rng, rng.randint(max(4, bumps[0] - BUMP_CUT), max(4, bumps[1] - BUMP_CUT)), bump) for _ in clumps]
        for i, (b, c) in enumerate(zip(blobs, clumps)):
            # the ink underlay only shows at the silhouette; clumps buried inside others add bytes, not ink
            if not covered(c, clumps[:i] + clumps[i + 1:] + list(cores), grow=1.35):
                self.fol_ink.append(b.path(*c))
            self.extent(c[0] - c[2] * 1.25, c[1] - c[3] * 1.25, c[0] + c[2] * 1.25, c[1] + c[3] * 1.25)
        x0 = min(c[0] - c[2] for c in clumps)
        x1 = max(c[0] + c[2] for c in clumps)
        y0 = min(c[1] - c[3] for c in clumps)
        y1 = max(c[1] + c[3] for c in clumps)
        ccx, ccy = (x0 + x1) / 2, (y0 + y1) / 2
        hw, hh = max((x1 - x0) / 2, 1.0), max((y1 - y0) / 2, 1.0)
        order = sorted(range(len(clumps)), key=lambda i: (clumps[i][1], clumps[i][0]))
        mark_attrs = f'fill="none" stroke="{pal[0]}" stroke-width=".4"'
        hatch_attrs = f'fill="none" stroke="{INK}" stroke-width=".4" stroke-opacity=".5"'
        # paint in depth bands (back -> front); inside a band dark / mid / light are each one merged path
        nb = max(1, min(3, round(len(order) / 7)))
        band_of = {i: min(nb - 1, idx * nb // len(order)) for idx, i in enumerate(order)}
        layers = [([], [], []) for _ in range(nb)]
        for idx, i in enumerate(order):
            cx, cy, rx, ry = clumps[i]
            b = blobs[i]
            later = [clumps[j] for j in order[idx + 1:]]

            def vis(x, y, later=later):
                return not any(inside(x, y, o, 1.12) for o in later)
            lit = clamp(-(0.75 * (cx - ccx) / hw + 0.9 * (cy - ccy) / hh) + light_bias + rng.uniform(-0.15, 0.15), -1, 1)
            dk, md, lt = layers[band_of[i]]
            dk.append(b.path(cx, cy, rx, ry))
            s = 0.64 + 0.2 * lit
            mx, my = cx - 0.14 * rx, cy - 0.16 * ry
            md.append((b.coarse() if len(b.pts) >= 8 else b).path(mx, my, rx * s, ry * s))
            if lit > -0.4 and min(rx, ry) > 1.5:
                s2 = 0.3 + 0.16 * lit
                lt.append(ell(cx - 0.3 * rx, cy - 0.32 * ry, rx * s2, ry * s2 * 0.85, seg=4))
            size = min(rx, ry)
            if marks == "arc" and size > 1.3:
                for _k in range(1 + (size > 2.4)):
                    px = mx + rng.uniform(-0.35, 0.3) * rx * s
                    py = my + rng.uniform(-0.1, 0.4) * ry * s
                    a = rng.uniform(0.35, 0.55) * min(size, 2.4) * 0.45
                    if vis(px, py):
                        self.later(mark_attrs, f"M{pt((px - a, py))}q{n(a)} {n(a * 0.75)} {n(2 * a)} 0")
            elif marks == "tick" and size > 0.9:
                for _k in range(2):
                    px = cx + rng.uniform(-0.3, 0.45) * rx
                    py = cy + rng.uniform(0.0, 0.45) * ry
                    if vis(px + 0.25, py + 0.3):
                        self.later(mark_attrs, f"M{pt((px, py))}l.5 .55")
            if hatch and lit < -0.15 and size > 1.2:
                ang = math.radians(48)
                bx, by = cx + 0.72 * rx * math.cos(ang), cy + 0.72 * ry * math.sin(ang)
                tx, ty = -math.sin(ang), math.cos(ang)
                ln = 0.42 * size
                for k in (-1, 0, 1):
                    qx, qy = bx + k * 0.36 * tx * rx / max(rx, 1) * 1.6, by + k * 0.36 * ty * 1.6
                    if vis(qx, qy):
                        self.later(hatch_attrs, f"M{pt((qx - 0.45 * ln, qy + 0.35 * ln))}l{n(0.9 * ln)} {n(-0.7 * ln)}")
        for dk, md, lt in layers:
            if dk:
                self.fol.append(f'<path d="{"".join(dk)}" fill="{pal[0]}" stroke="{INK}" '
                                f'stroke-width="{inner_stroke}" stroke-opacity=".6"/>')
            if md:
                self.fol.append(f'<path d="{"".join(md)}" fill="{pal[1]}"/>')
            if lt:
                self.fol.append(f'<path d="{"".join(lt)}" fill="{pal[2]}"/>')

    # -- conifer tiers
    def tier(self, ax, ay, by, w, pal, *, curv=0.0, depth=1.0, teeth=4, sag=0.3, droop=0.0, asym=0.0, needles=3):
        rng = self.rng
        wr, wl = w * (1 + asym), w * (1 - asym)
        apex = (ax, ay)
        rt, lt = (ax + wr, by + droop), (ax - wl, by + droop)

        def side(end, sign, ww):
            c = (ax + sign * ww * (0.5 + curv), ay + (by - ay) * (0.55 - 0.25 * curv))
            return [bez(apex, c, end, k / 6) for k in range(1, 7)]

        right, left = side(rt, 1, wr), side(lt, -1, wl)

        def base(x):
            q = clamp((x - ax) / (wr if x > ax else wl), -1, 1)
            return by + sag * (1 - q * q) + droop * q * q

        m = 2 * teeth
        span = rt[0] - lt[0]
        bottom = []
        for k in range(m + 1):
            x = rt[0] - k * span / m
            if 0 < k < m:
                x += rng.uniform(-0.15, 0.15) * span / m
            y = base(x)
            if k % 2:
                y -= depth * rng.uniform(0.6, 1.15)
            elif 0 < k < m:
                y += rng.uniform(-0.15, 0.25) * depth
            bottom.append((x, y))
        outline = [apex] + right + bottom[1:-1] + left[::-1]
        self.fol_ink.append(poly(outline))
        bx = ax + 0.12 * wr
        dark = [apex] + right + [p for p in bottom[1:] if p[0] >= bx] + [(bx, base(bx) - depth * 0.4)]
        lx = ax - 0.48 * wl
        light = [apex] + left + [p for p in bottom[::-1][1:] if p[0] <= lx] + \
            [(lx, base(lx) - depth * 0.9), (ax - 0.2 * wl, ay + 0.5 * (by - ay))]
        self.fol.append(f'<path d="{poly(outline)}" fill="{pal[1]}"/>')
        self.fol.append(f'<path d="{poly(dark)}" fill="{pal[0]}"/>')
        if len(light) > 4:
            self.fol.append(f'<path d="{poly(light)}" fill="{pal[2]}"/>')
        strokes_d, strokes_l = [], []
        for j in range(needles):
            t = rng.uniform(0.4, 0.85)
            y = ay + t * (by - ay)
            sgn = 1 if j % 2 == 0 else -1
            half = (wr if sgn > 0 else wl) * t * 0.9
            x0 = ax + sgn * half * rng.uniform(0.15, 0.45)
            dx = sgn * rng.uniform(0.8, 1.4) * min(1.0, w / 4)
            seg = f"M{pt((x0, y))}l{n(dx)} {n(abs(dx) * 0.55 + max(droop, 0) * 0.25)}"
            (strokes_d if sgn > 0 else strokes_l).append(seg)
        if strokes_d:
            self.fol.append(f'<path d="{"".join(strokes_d)}" fill="none" stroke="{INK}" stroke-width=".4" stroke-opacity=".55"/>')
        if strokes_l:
            self.fol.append(f'<path d="{"".join(strokes_l)}" fill="none" stroke="{pal[0]}" stroke-width=".45"/>')
        self.fol.append(f'<path d="{poly(bottom, False)}" fill="none" stroke="{INK}" stroke-width=".45" stroke-opacity=".75"/>')

    def cone(self, cx, top, bottom, w_top, w_bot, count, pal, *, lean=0.0, pw=1.0, overlap=0.6, asym=0.15,
             tweak=None, **kw):
        rng = self.rng
        h = bottom - top
        specs = []
        for k in range(count):
            f = (k + 1) / count
            by = top + h * f
            hk = h / count * (1 + overlap) * (1.3 if k == 0 else 1.0)
            ay = top if k == 0 else max(top, by - hk)
            w = w_top + (w_bot - w_top) * f ** pw
            ax = cx + lean * (1 - (ay - top) / h)
            spec = dict(ax=ax, ay=ay, by=by, w=w, asym=rng.uniform(-asym, asym), **kw)
            if tweak:
                tweak(k, spec)
            specs.append(spec)
        for s in reversed(specs):
            ax, ay, by, w = s.pop("ax"), s.pop("ay"), s.pop("by"), s.pop("w")
            self.tier(ax, ay, by, w, pal, **s)

    # -- weeping curtain (willow): separate tapered strands with paper showing between them
    def curtain(self, x0, x1, yt, yb, pal, *, count=7, gap=0.0, slope=0.0, taper_k=1.3):
        rng = self.rng
        width = x1 - x0
        mid = (x0 + x1) / 2
        sp = width / count
        strands = []
        for i in range(count):
            x = x0 + sp * (i + 0.5) + rng.uniform(-0.12, 0.12) * sp
            q = (x - mid) / (width / 2)
            y = yb - gap * max(0.0, 1 - abs(q) / 0.38) + slope * q + rng.uniform(-1.4, 0.6)
            y -= 2.6 * max(0.0, abs(q) - 0.72)  # outermost strands a little shorter
            sway = rng.uniform(-0.5, 0.5) + 0.7 * q
            a, c, b = (x, yt), (x + sway, (yt + y) / 2), (x + sway * 0.7, y)
            ts = [k / 8 for k in range(9)]
            center = [bez(a, c, b, t) for t in ts]
            widths = [sp * 0.78 * (1 - t) ** taper_k + 0.55 for t in ts]
            sa, sb = taper(center, widths)
            strands.append((x, center, sa, sb))
        # back-to-front: outer strands first, central (front) strands last
        strands.sort(key=lambda s: -abs(s[0] - mid))
        light_lines, dark_lines = [], []
        for x, center, sa, sb in strands:
            outline = sa + sb[::-1]
            self.fol_ink.append(poly(outline))
            lit = x < mid - 0.1 * width
            self.fol.append(f'<path d="{poly(outline)}" fill="{pal[1] if lit else pal[0]}"/>')
            # shaded right edge of lit strands / lit left edge of dark strands
            right, left = (sa, sb) if sum(p[0] for p in sa) > sum(p[0] for p in sb) else (sb, sa)
            if lit:
                inner = [(c0[0] + (r[0] - c0[0]) * 0.15, c0[1]) for c0, r in zip(center, right)]
                self.fol.append(f'<path d="{poly(inner + right[::-1])}" fill="{pal[0]}"/>')
                light_lines.append(poly([(p[0] - 0.25, p[1]) for p in center[1:-2]], False))
            else:
                dark_lines.append(poly([(p[0] + 0.15, p[1]) for p in center[2:-2]], False))
        if light_lines:
            self.later(f'fill="none" stroke="{pal[2]}" stroke-width=".5"', "".join(light_lines))
        if dark_lines:
            self.later(f'fill="none" stroke="{INK}" stroke-width=".4" stroke-opacity=".5"', "".join(dark_lines))

    # -- output
    def svg(self) -> str:
        sx, srx = self.shadow
        out = [f'<symbol id="{self.sid}" viewBox="0 0 32 40" data-anchor="16 38">'
               '<g stroke-linejoin="round" stroke-linecap="round">',
               f'<ellipse cx="{n(sx)}" cy="38.2" rx="{n(srx)}" ry="{n(max(0.9, srx * 0.22))}" fill="{INK}" opacity=".18"/>']
        if self.wood:
            out.append(f'<path d="{"".join(d for d, _ in self.wood)}" fill="{INK}" stroke="{INK}" stroke-width="1.4"/>')
            fills = {}
            for d, f in self.wood:
                fills.setdefault(f, []).append(d)
            for f, ds in fills.items():
                out.append(f'<path d="{"".join(ds)}" fill="{f}"/>')
            out.extend(self.wood_top)
        if self.fol_ink:
            out.append(f'<path d="{"".join(self.fol_ink)}" fill="{INK}" stroke="{INK}" stroke-width="1.6"/>')
            out.extend(merge_runs(self.fol))
        for attrs, ds in self.defer.items():
            out.append(f'<path d="{"".join(ds)}" {attrs}/>')
        out.extend(self.top)
        out.append("</g></symbol>")
        sc = f"{1 / Q:.4g}".lstrip("0")
        out[0] = out[0].replace('<g stroke-linejoin', f'<g transform="scale({sc})" stroke-linejoin')
        return "\n".join(scale_attrs(_D_ATTR.sub(lambda m: f' d="{compact(m.group(1))}"', s)) for s in out)


def merge_runs(elems):
    """Merge consecutive <path> elements with identical attributes (paint order is kept)."""
    out, key, ds = [], None, []
    pat = re.compile(r'<path d="([^"]*)"(.*)/>$')
    for e in elems:
        m = pat.match(e)
        k = m.group(2) if m else None
        if k is not None and k == key:
            ds.append(m.group(1))
            continue
        if key is not None:
            out.append(f'<path d="{"".join(ds)}"{key}/>')
        if k is None:
            out.append(e)
            key, ds = None, []
        else:
            key, ds = k, [m.group(1)]
    if key is not None:
        out.append(f'<path d="{"".join(ds)}"{key}/>')
    return out


# ----------------------------------------------------------------------------- clump layouts
def cloud(rng, cx, cy, a, b, *, rr=(2.8, 3.6), ri=None, aspect=0.85, spacing=1.55, inner_density=1.0, gaps=(),
          mod=None, keep_out=()):
    spacing *= SPACING_K
    inner_density *= DENSITY_K
    rmean = sum(rr) / 2
    perim = math.pi * (3 * (a + b) - math.sqrt((3 * a + b) * (a + 3 * b)))
    ring = max(5, math.ceil(perim / (spacing * rmean)))
    ri = ri or rr
    ph = rng.uniform(0, TAU)
    out = []

    def blocked(x, y):
        return any(math.hypot(x - kx, y - ky) < kr for kx, ky, kr in keep_out)

    for i in range(ring):
        th = ph + TAU * i / ring + rng.uniform(-0.18, 0.18) * TAU / ring
        if any(angle_in(th, g) for g in gaps):
            continue
        m = mod(th) if mod else 1.0
        ex, ey = cx + a * m * math.cos(th), cy + b * m * math.sin(th)
        r = rng.uniform(*rr)
        dx, dy = cx - ex, cy - ey
        d = math.hypot(dx, dy) or 1.0
        px, py = ex + dx / d * r * 0.7, ey + dy / d * r * aspect * 0.7
        if blocked(px, py):
            continue
        out.append((px, py, r, r * aspect))
    rim = sum(ri) / 2
    for _ in range(round(inner_density * (a * 0.6) * (b * 0.6) / (rim * rim * 0.9))):
        for _try in range(30):
            ang = rng.uniform(0, TAU)
            rad = math.sqrt(rng.random()) * 0.6
            m = mod(ang) if mod else 1.0
            px, py = cx + a * m * rad * math.cos(ang), cy + b * m * rad * math.sin(ang)
            if not blocked(px, py):
                break
        else:
            continue
        r = rng.uniform(*ri)
        out.append((px, py, r, r * aspect))
    return out


def flat_bottom(k=0.82):
    """Envelope modifier: squash the lower part (angles around 90 deg, y down)."""
    return lambda th: 1 - (1 - k) * max(0.0, math.sin(th)) ** 2


def plates(rng, rows, ry=(1.3, 1.7)):
    out = []
    for y, xl, xr in rows:
        w = xr - xl
        k = max(2, round(w / 5.0))
        for i in range(k):
            x = xl + w * (i + 0.5) / k + rng.uniform(-0.4, 0.4)
            rx = w / k * 0.62 + rng.uniform(-0.2, 0.3)
            droop = abs(i - (k - 1) / 2) / k * 0.9
            out.append((x, y + rng.uniform(-0.3, 0.3) + droop, rx, rng.uniform(*ry)))
    return out


def spindle(rng, top, bottom, wmax, *, peak=0.62, xfun=lambda t: 16.0, step=1.7, skip=()):
    step *= 1.3  # fewer, taller scale clumps (file size)
    out = []
    h = bottom - top
    y = top + 1.4
    row = 0
    while y < bottom - 1.0:
        t = (y - top) / h
        hw = wmax * ((t / peak) ** 0.65 if t < peak else 1 - 0.45 * ((t - peak) / (1 - peak)) ** 1.5)
        cx = xfun(t)
        for s in (-1, 1):
            if (row, s) in skip:
                continue
            rx = hw * 0.62 + 0.35 + rng.uniform(-0.1, 0.2)
            out.append((cx + s * hw * 0.42 + rng.uniform(-0.25, 0.25), y + rng.uniform(-0.3, 0.3), rx, max(1.2, rx * 1.35)))
        y += step * rng.uniform(0.85, 1.15)
        row += 1
    out.append((xfun(0.0), top + 1.0, 0.8, 1.3))
    return out


def jit(rng, clumps, s=0.3):
    return [(x + rng.uniform(-s, s), y + rng.uniform(-s * 0.6, s * 0.6), rx * rng.uniform(0.94, 1.06), ry) for x, y, rx, ry in clumps]


# ----------------------------------------------------------------------------- conifers
def pine(t, v):
    r = t.rng
    if v == 1:  # Scots pine: tall clear trunk, flat cloud-like crown on top
        t.shadow = (17, 6.5)
        t.trunk((16, 38), (15.2, 24), (16.6, 7.5), 2.5, 0.9, marks=3)
        t.branch((16.2, 18.5), (12, 16.5), (8, 14.4), 1.1, 0.5)
        t.branch((16.4, 14.5), (20.5, 12.8), (25, 11.8), 1.0, 0.5)
        t.branch((16.5, 11), (14.5, 9), (12.2, 8.6), 0.9, 0.45)
        # wide flat crown so the pine still reads as a broad umbrella at 20 px
        cl = [(16.6, 6.2, 5.6, 2.8), (10.4, 9.4, 5.2, 2.6), (22.4, 9.2, 5.4, 2.6), (6.6, 13.8, 4.2, 2.2),
              (26, 13.2, 4.0, 2.1), (15.6, 11.4, 4.4, 2.4), (20, 4.2, 3.2, 1.9), (12.2, 5.0, 3.0, 1.8)]
    elif v == 2:  # windswept, leaning, crown streams to the right
        t.shadow = (18.5, 7)
        t.trunk((14.5, 38), (13.5, 25), (19.5, 12), 2.4, 1.0, marks=3)
        t.branch((18.2, 14.5), (22, 13.5), (26, 13.6), 1.0, 0.45)
        t.branch((17.2, 16.5), (14.5, 15), (12.4, 15.4), 0.9, 0.45)
        cl = [(19.5, 10.8, 5.0, 2.4), (25.2, 12.4, 4.0, 2.0), (13.6, 13.6, 3.4, 1.9), (21.4, 7.8, 3.4, 1.9),
              (28, 15.2, 2.4, 1.5), (16.2, 9.6, 3.0, 1.8)]
    else:  # two separate crown layers with trunk visible between
        t.shadow = (16, 6)
        t.trunk((16, 38), (16.8, 22), (15.6, 4), 2.3, 0.8, marks=3)
        t.branch((16.3, 19.5), (12.5, 18.5), (10, 18.4), 0.9, 0.45)
        t.branch((16.4, 21.5), (20, 20.5), (22.6, 19.6), 0.9, 0.45)
        cl = [(15.8, 5.2, 3.8, 2.2), (12, 8.2, 3.6, 2.0), (20, 8, 3.8, 2.1), (16, 9.6, 3.2, 1.8),
              (9.8, 17.6, 3.2, 1.8), (22.6, 18.8, 3.4, 1.8), (13.2, 18.4, 2.2, 1.4)]
    t.crown(jit(r, cl), CON, bumps=(7, 9), bump=0.3, marks="tick")


def spruce(t, v):
    if v == 1:  # tall narrow spire, drooping spiky tiers
        t.shadow = (16.8, 6.5)
        t.trunk((16, 38), (16, 30), (16, 4), 1.9, 0.6, flare=0.6, marks=0)
        t.cone(16, 1.6, 33, 1.6, 8.6, 7, CON, curv=-0.18, depth=1.3, teeth=4, sag=0.2, droop=1.1, overlap=0.7)
    elif v == 2:  # short, stocky, wide skirt
        t.shadow = (16.8, 7.5)
        t.trunk((16, 38), (16, 32), (16, 10), 2.1, 0.7, flare=0.6, marks=0)
        t.cone(16, 8.5, 34.6, 2.0, 10.6, 5, CON, curv=-0.12, depth=1.5, teeth=5, sag=0.3, droop=1.3, overlap=0.65)
    else:  # slim, leaning top, one tier stripped on the left
        t.shadow = (17, 5.5)
        t.trunk((16, 38), (16, 30), (17, 4), 1.7, 0.5, flare=0.5, marks=0)

        def tw(k, s):
            if k == 4:
                s["asym"] = 0.55
            if k == 2:
                s["asym"] = -0.35

        t.cone(16, 1.2, 31.5, 1.3, 6.4, 8, CON, lean=1.6, curv=-0.2, depth=1.2, teeth=3, sag=0.2, droop=1.0,
               overlap=0.6, tweak=tw)


def fir(t, v):
    if v == 1:  # dense symmetric cone, smooth upturned tiers
        t.shadow = (16.8, 6.5)
        t.trunk((16, 38), (16, 32), (16, 6), 2.0, 0.7, flare=0.6, marks=0)
        t.cone(16, 2.4, 34, 1.4, 8.0, 8, CON, curv=0.12, depth=0.75, teeth=3, sag=0.5, droop=-0.7, overlap=0.95,
               pw=1.1, asym=0.06)
    elif v == 2:  # young fir, short and round
        t.shadow = (16.6, 6.2)
        t.trunk((16, 38), (16, 34), (16, 16), 1.8, 0.7, flare=0.5, marks=0)
        t.cone(16, 12.5, 35.6, 2.0, 7.6, 4, CON, curv=0.22, depth=0.8, teeth=3, sag=0.6, droop=-0.6, overlap=0.95,
               pw=0.9, asym=0.08)
    else:  # old fir: broken top with a bare snag, fuller lower tiers
        t.shadow = (17, 7)
        t.trunk((16, 38), (16, 32), (16, 10), 2.3, 0.9, flare=0.8, marks=0)
        t.branch((16, 11), (15.6, 6), (16.4, 2.4), 0.9, 0.3, DEAD)
        t.branch((16.1, 6.5), (17.4, 5.6), (18.6, 5.8), 0.45, 0.2, DEAD, shade=False)
        t.cone(16, 8.5, 34, 3.4, 9.2, 6, CON, curv=0.1, depth=0.8, teeth=3, sag=0.5, droop=-0.6, overlap=0.9,
               pw=1.0, asym=0.12)


def larch(t, v):
    if v == 1:  # airy tiers with gaps; trunk shows through
        t.shadow = (16.6, 6)
        t.trunk((16, 38), (16, 25), (16, 3), 1.9, 0.5, flare=0.6, marks=0)
        t.cone(16, 2.6, 33, 1.4, 8.0, 6, LARCH, curv=-0.3, depth=1.5, teeth=5, sag=0.1, droop=1.4, overlap=-0.1,
               asym=0.18, needles=2)
    elif v == 2:  # autumn gold, shorter, slightly leaning and uneven
        t.shadow = (17.2, 6.4)
        t.trunk((15.6, 38), (15.6, 26), (17.4, 6.5), 2.0, 0.5, flare=0.6, marks=0)
        t.cone(16, 6.4, 33.6, 1.6, 8.6, 5, GOLD, lean=1.4, curv=-0.25, depth=1.5, teeth=4, sag=0.1, droop=1.3,
               overlap=0.0, asym=0.28, needles=2)
    else:  # sparse and thin: few narrow tiers far apart
        t.shadow = (16.2, 5)
        t.trunk((16, 38), (16.4, 24), (15.4, 3.5), 1.6, 0.4, flare=0.5, marks=0)
        t.cone(15.6, 3.4, 30.5, 1.2, 6.2, 4, LARCH, lean=-0.4, curv=-0.35, depth=1.4, teeth=4, sag=0.1, droop=1.6,
               overlap=-0.35, asym=0.3, needles=2)


def cedar(t, v):
    r = t.rng
    if v == 1:  # Lebanon cedar: stacked flat plates, offset, thick trunk
        t.shadow = (16.6, 9)
        t.trunk((16, 38), (15.6, 25), (16, 9), 3.0, 1.2, flare=1.0, marks=3)
        for y, xl, xr in ((12.6, 9.5, 22), (18.2, 5, 15.5), (17.6, 16, 25.5), (24, 3.5, 29), (29, 7, 24)):
            t.branch((16, y + 1), ((16 + xl) / 2, y + 0.6), (xl + 1.2, y + 0.4), 0.9, 0.45)
            t.branch((16, y + 1), ((16 + xr) / 2, y + 0.6), (xr - 1.2, y + 0.4), 0.9, 0.45)
        rows = ((12.6, 9.5, 22), (18.2, 5, 15.5), (17.6, 16, 25.5), (24, 3.5, 29), (29, 7, 24))
        cl = plates(r, rows) + [(16.4, 9.2, 2.4, 1.5)]
    elif v == 2:  # young cedar: pyramid of plates, nodding leader
        t.shadow = (16.4, 7.5)
        t.trunk((16, 38), (16, 25), (16, 6), 2.2, 0.7, flare=0.7, marks=2)
        t.branch((16, 6.5), (16.6, 3.6), (18.4, 3.2), 0.6, 0.25)
        rows = ((7.6, 13.4, 19), (12, 11, 21.4), (16.6, 8.4, 23.6), (21.4, 6, 26), (26.4, 4.4, 27.6), (31, 6.8, 25))
        cl = plates(r, rows, ry=(1.2, 1.5)) + [(17.6, 4.2, 1.4, 1.0)]
    else:  # old, broad, two great umbrella plates, forked trunk
        t.shadow = (17, 10)
        t.trunk((16, 38), (15.8, 30), (14.5, 18), 3.4, 1.8, flare=1.2, marks=3)
        t.branch((15.6, 26), (19.5, 21), (22, 16.5), 1.6, 0.9)
        t.branch((14.6, 19), (10, 16.5), (6, 15.8), 1.0, 0.5)
        t.branch((20.5, 18.6), (25, 15.8), (28, 15.4), 0.9, 0.45)
        rows = ((14.2, 3, 29.5), (20.4, 6.5, 26.5), (9.6, 9.5, 23))
        cl = plates(r, rows, ry=(1.4, 1.9))
    t.crown(jit(r, cl, 0.2), CON, bumps=(8, 10), bump=0.28, marks="tick", hatch=True)


def cypress(t, v):
    r = t.rng
    if v == 1:  # Mediterranean cypress: narrow column/flame
        t.shadow = (16.6, 4.4)
        t.trunk((16, 38), (16, 36), (16, 30), 1.6, 1.0, flare=0.4, marks=0)
        cl = spindle(r, 1.4, 36, 3.8, peak=0.66)
        cores = [(16, 21, 2.9, 13)]
    elif v == 2:  # broader flame, shorter
        t.shadow = (16.8, 5.6)
        t.trunk((16, 38), (16, 36), (16, 30), 1.8, 1.1, flare=0.4, marks=0)
        cl = spindle(r, 6, 36.2, 5.4, peak=0.55, step=1.9)
        cores = [(16, 23, 4.0, 11)]
    else:  # tall, gently S-curved, with a bite out of one side
        t.shadow = (16.4, 4)
        t.trunk((16, 38), (16, 36), (16.2, 30), 1.5, 1.0, flare=0.4, marks=0)

        def xf(tt):
            return 16 + 1.5 * math.sin(math.pi * (1 - tt)) - 0.2

        cl = spindle(r, 1.0, 36, 3.2, peak=0.7, xfun=xf, skip={(9, -1), (10, -1)})
        cores = [(xf(0.3), 10.5, 1.8, 6.5), (xf(0.75), 27, 2.2, 6.5)]
    t.crown(cl, CON, cores=cores, bumps=(6, 8), bump=0.32, marks="tick", hatch=True)


def yew(t, v):
    r = t.rng
    if v == 1:  # dense dark rounded cone, several short reddish stems
        t.shadow = (17, 10)
        for a, b, c in (((14.4, 38), (14, 34), (13.4, 29)), ((16.6, 38), (16.8, 34), (17, 28)), ((18.4, 38), (19, 34), (20.4, 30))):
            t.trunk(a, b, c, 1.8, 1.1, RED_BARK, flare=0.3, marks=1)
        cl = cloud(r, 16, 20, 12.0, 12.6, rr=(2.3, 3.0), aspect=0.82, spacing=1.45,
                   mod=lambda th: 1 - 0.18 * max(0.0, -math.sin(th)) ** 3 * abs(math.cos(th)) * 2 - 0.12 * max(0.0, math.sin(th)) ** 2)
        cores = [(16, 21, 9.5, 10)]
    elif v == 2:  # old yew: hollow, split into two masses, fluted trunk
        t.shadow = (16.6, 9)
        t.trunk((16, 38), (15.6, 33), (14.2, 25), 4.2, 2.4, RED_BARK, flare=1.0, marks=4)
        t.branch((15.6, 30), (19.5, 26), (21, 20), 1.8, 1.0, RED_BARK)
        cl = cloud(r, 11.6, 15.5, 7.2, 9.4, rr=(2.2, 2.8), aspect=0.82) + \
            cloud(r, 21.4, 19.5, 6.6, 8.2, rr=(2.2, 2.8), aspect=0.82)
        cores = [(11.6, 15.5, 5.4, 7), (21.4, 19.5, 4.8, 6)]
    else:  # low, wide spreading mound
        t.shadow = (16.6, 12)
        for a, b, c in (((14.6, 38), (13.6, 35.5), (11, 33)), ((17.4, 38), (18.6, 35.5), (21.4, 33))):
            t.trunk(a, b, c, 1.9, 1.1, RED_BARK, flare=0.3, marks=1)
        cl = cloud(r, 16, 27.6, 14.2, 7.4, rr=(2.1, 2.8), aspect=0.8, mod=flat_bottom(0.85))
        cores = [(16, 28, 11.5, 5.6)]
    t.crown(cl, CON, cores=cores, bumps=(7, 9), bump=0.3, marks="tick", light_bias=-0.15)


def redwood(t, v):
    r = t.rng

    def column(y0, y1, wmax, step=2.3, center=lambda y: 16.0):
        out = []
        y = y0
        i = 0
        while y <= y1:
            hw = 1.0 + (y - y0) / max(1.0, y1 - y0) * wmax
            c = center(y)
            sh = 0.35 if i % 2 else -0.35
            out.append((c - hw * 0.55 + sh, y + r.uniform(-0.3, 0.3), hw * 0.62 + 0.4, 1.35))
            out.append((c + hw * 0.55 + sh, y + 0.9 + r.uniform(-0.3, 0.3), hw * 0.62 + 0.4, 1.35))
            y += step * r.uniform(0.9, 1.1)
            i += 1
        out.append((center(y0), y0 - 1.2, 0.9, 1.4))
        return out

    if v == 1:  # very tall, massive red trunk, narrow crown high up
        t.shadow = (16.8, 6)
        t.trunk((16, 38), (16, 20), (16, 2.5), 4.2, 0.6, RED_BARK, flare=1.4, marks=5)
        cl = column(4, 26, 5.6)
    elif v == 2:  # emergent giant: crown confined to the top, dead stubs below
        t.shadow = (17, 6)
        t.trunk((16, 38), (16.2, 20), (17.2, 2), 4.0, 0.6, RED_BARK, flare=1.4, marks=5)
        for y, s in ((22.5, -1), (24.6, 1), (27, -1)):
            t.branch((16.3, y), (16.3 + s * 1.6, y - 0.2), (16.3 + s * 3.0, y + 0.4), 0.6, 0.25, DEAD, shade=False)
        cl = column(3.4, 18.5, 4.4, step=2.1, center=lambda y: 16.0 + (19 - y) / 17 * 1.1)
    else:  # younger: denser crown reaching lower, shorter
        t.shadow = (16.6, 6.5)
        t.trunk((16, 38), (16, 24), (16, 7), 3.2, 0.6, RED_BARK, flare=1.1, marks=4)
        cl = column(8.4, 29.5, 6.4, step=2.0)
    t.crown(cl, CON, bumps=(7, 9), bump=0.3, marks="tick", hatch=True)


# ----------------------------------------------------------------------------- broadleaves
def oak(t, v):
    r = t.rng
    if v == 1:  # broad spreading crown, stout short trunk, big limbs
        t.shadow = (17, 11)
        # wide and low, flat underside: the oak reads as a broad loaf at 20 px
        t.shadow = (17, 12.5)
        t.trunk((16, 38), (16.2, 32), (16, 27), 4.0, 2.8, flare=1.3, marks=3)
        t.branch((16, 28.5), (10.5, 27.5), (5.5, 23), 1.8, 0.8)
        t.branch((16.2, 28.5), (22, 27), (26.6, 22.6), 1.8, 0.8)
        t.branch((16, 27.5), (15.4, 22), (15.6, 16), 1.6, 0.7)
        cl = cloud(r, 16, 18.2, 14.8, 8.2, rr=(3.0, 3.8), aspect=0.8, mod=flat_bottom(0.62))
        cores = [(16, 18.6, 12, 5.6)]
    elif v == 2:  # taller, lopsided to the right with a notch on the lower left
        t.shadow = (18, 9.5)
        t.trunk((15.4, 38), (15, 30), (17.4, 21), 3.2, 2.0, flare=1.1, marks=3)
        t.branch((17, 23.5), (12.5, 22.2), (10.2, 18.6), 1.3, 0.6)
        t.branch((17.2, 22), (21.5, 19.5), (24.6, 16), 1.4, 0.6)
        cl = cloud(r, 17.8, 12.6, 11.4, 10.6, rr=(2.8, 3.7), aspect=0.84, gaps=((140, 175),),
                   keep_out=((8.6, 19.5, 3.2),))
        cores = [(18.4, 12, 8, 7.6)]
    else:  # old gnarled oak: two separated masses and a dead limb
        t.shadow = (16.6, 11.5)
        t.trunk((16, 38), (15.2, 31), (16.6, 24), 4.4, 2.8, flare=1.5, marks=4)
        t.branch((15.8, 26), (11.5, 24.6), (9.8, 18.5), 2.0, 0.9)
        t.branch((16.8, 25), (20, 21.5), (21.6, 15.5), 1.9, 0.9)
        t.branch((16.4, 25), (14.5, 14), (13.6, 4.6), 1.2, 0.35, DEAD)
        t.branch((14, 10), (11.8, 8.6), (11, 7), 0.5, 0.2, DEAD, shade=False)
        cl = cloud(r, 9.6, 17.4, 7.6, 6.8, rr=(2.6, 3.3), aspect=0.82) + \
            cloud(r, 22, 13.2, 8.4, 7.8, rr=(2.7, 3.5), aspect=0.82)
        cores = [(9.6, 17.6, 5.2, 4.6), (22, 13.4, 6, 5.4)]
    t.crown(cl, BRD, cores=cores, bumps=(6, 8), bump=0.36)


def beech(t, v):
    r = t.rng
    pal = ("#506a36", "#708c45", "#98ab5e")
    if v == 1:  # smooth tall dome that reaches low, smooth grey trunk
        t.shadow = (17, 10)
        t.trunk((16, 38), (16, 30), (16, 18), 2.8, 1.7, GREY_BARK, flare=0.9, marks=0)
        # tall egg: narrower towards the top, widest low down
        cl = cloud(r, 16, 15.6, 9.8, 13.8, rr=(2.6, 3.2), aspect=0.9, spacing=1.4,
                   mod=lambda th: 1 - 0.2 * max(0.0, -math.sin(th)) ** 1.5 + 0.06 * max(0.0, math.sin(th)))
        cores = [(16, 16.2, 7.6, 11.2)]
    elif v == 2:  # tall and narrow oval
        t.shadow = (16.6, 7.5)
        t.trunk((16, 38), (16, 31), (16, 18), 2.4, 1.5, GREY_BARK, flare=0.8, marks=0)
        cl = cloud(r, 16, 15.4, 8.4, 13.4, rr=(2.4, 3.0), aspect=0.9, spacing=1.4)
        cores = [(16, 15.6, 6.4, 11)]
    else:  # broad low dome, trunk leaning a little
        t.shadow = (17, 12)
        t.trunk((15, 38), (15.2, 33), (17, 24), 3.0, 2.0, GREY_BARK, flare=1.0, marks=0)
        t.branch((16.6, 26), (12.5, 24.5), (8.6, 24), 1.3, 0.6, GREY_BARK)
        cl = cloud(r, 16.6, 19.4, 14.0, 9.6, rr=(2.8, 3.4), aspect=0.88, spacing=1.4, mod=flat_bottom(0.88))
        cores = [(16.6, 19.8, 11.4, 7.2)]
    t.top.append(f'<path d="M15.4 33.6q.5-.5 1 0" fill="none" stroke="{INK}" stroke-width=".4" stroke-opacity=".6"/>')
    t.crown(cl, pal, cores=cores, bumps=(8, 11), bump=0.22)


def birch(t, v):
    r = t.rng
    if v == 1:  # single slender white stem, narrow airy crown
        t.shadow = (16.4, 5.5)
        t.trunk((16, 38), (15.2, 24), (16.4, 5), 1.9, 0.6, BIRCH_BARK, flare=0.4, marks=0, birch=True)
        t.branch((15.7, 21), (13, 18.5), (11.6, 15), 0.7, 0.3, BIRCH_BARK, birch=True)
        t.branch((15.9, 17), (18.6, 14.5), (20, 11), 0.7, 0.3, BIRCH_BARK, birch=True)
        cl = cloud(r, 16, 13.6, 6.6, 11.0, rr=(1.9, 2.5), aspect=0.9, spacing=1.5, inner_density=1.4,
                   gaps=((15, 38),), keep_out=((14.4, 10.6, 2.5),))
    elif v == 2:  # three-stemmed clump, splayed
        t.shadow = (16.6, 8)
        t.trunk((15.2, 38), (14.4, 25), (10.6, 9), 1.6, 0.5, BIRCH_BARK, flare=0.3, marks=0, birch=True)
        t.trunk((16.4, 38), (16.8, 22), (16.6, 4.5), 1.7, 0.5, BIRCH_BARK, flare=0.3, marks=0, birch=True)
        t.trunk((17.4, 38), (19, 26), (22.6, 10), 1.5, 0.5, BIRCH_BARK, flare=0.3, marks=0, birch=True)
        cl = cloud(r, 10.8, 13.6, 4.6, 7.6, rr=(1.9, 2.4), aspect=0.9, spacing=1.9, inner_density=0.4) + \
            cloud(r, 16.6, 10.0, 4.8, 8.4, rr=(1.9, 2.4), aspect=0.9, spacing=1.9, inner_density=0.4) + \
            cloud(r, 22.2, 14.8, 4.4, 7.0, rr=(1.9, 2.4), aspect=0.9, spacing=1.9, inner_density=0.4)
    else:  # leaning stem, small crown with drooping lower edge
        t.shadow = (15, 6)
        t.trunk((17.6, 38), (17.8, 26), (12.6, 9), 1.8, 0.6, BIRCH_BARK, flare=0.4, marks=0, birch=True)
        t.branch((15.6, 18.5), (19, 16.5), (20.2, 13.4), 0.6, 0.3, BIRCH_BARK, birch=True)
        cl = cloud(r, 14.4, 14.8, 7.4, 9.0, rr=(1.8, 2.4), aspect=0.95, spacing=1.5, inner_density=1.4,
                   gaps=((165, 188),), keep_out=((16.2, 17.6, 2.4),),
                   mod=lambda th: 1 + 0.18 * max(0.0, math.sin(th)) ** 2)
    t.crown(cl, BIRCH, bumps=(6, 8), bump=0.34, light_bias=0.15)


def maple(t, v):
    r = t.rng
    pal = ("#4c6a34", "#6a8a40", "#91a856")
    if v == 1:  # compact round crown
        t.shadow = (17, 9.5)
        t.trunk((16, 38), (16, 31), (16, 22), 2.6, 1.7, flare=0.9, marks=2)
        t.branch((16, 24), (12.5, 22.5), (10.5, 19), 1.2, 0.5)
        t.branch((16, 23.5), (19.6, 22), (21.6, 18.6), 1.2, 0.5)
        # shallow lobes around the rim (palmate outline), not a smooth ball
        cl = cloud(r, 16, 14.6, 12.0, 11.2, rr=(2.6, 3.2), aspect=0.86,
                   mod=lambda th: 1 + 0.16 * math.cos(5 * th + 1.57))
        cores = [(16, 15, 8.6, 8.0)]
    elif v == 2:  # wide and short spreading crown, short trunk
        t.shadow = (17, 11.5)
        t.trunk((16, 38), (16.4, 33), (16, 27), 2.8, 2.0, flare=1.0, marks=2)
        t.branch((16, 28.5), (11, 27.2), (7, 23.4), 1.4, 0.6)
        t.branch((16.2, 28.5), (21, 27), (25, 23.4), 1.4, 0.6)
        cl = cloud(r, 16, 19.4, 13.8, 8.4, rr=(2.7, 3.3), aspect=0.84, mod=flat_bottom(0.85))
        cores = [(16, 20, 11, 6)]
    else:  # autumn: upright oval, smaller
        t.shadow = (16.6, 8)
        t.trunk((16, 38), (15.6, 31), (16.4, 21), 2.3, 1.4, flare=0.8, marks=2)
        t.branch((16.2, 24), (13, 21.5), (12, 17.5), 1.0, 0.45)
        cl = cloud(r, 16.2, 14.2, 9.4, 11.6, rr=(2.5, 3.1), aspect=0.88)
        cores = [(16.2, 14.6, 7, 9)]
        pal = AUTUMN
    t.crown(cl, pal, cores=cores, bumps=(6, 7), bump=0.42)


def chestnut(t, v):
    r = t.rng
    pal = ("#4a6432", "#668340", "#8ea257")
    if v == 1:  # tall dome of pointed clumps, thick trunk with spiral bark
        t.shadow = (17, 10.5)
        # thick trunk, crown rising to a blunt point
        t.trunk((16, 38), (15.4, 31), (16.2, 23), 4.6, 3.0, flare=1.4, marks=0)
        t.branch((16, 25), (11.5, 23.5), (9.4, 19.5), 1.6, 0.7)
        t.branch((16.4, 25), (20.5, 23.2), (22.8, 19.5), 1.6, 0.7)
        cl = cloud(r, 16, 14.6, 11.6, 11.0, rr=(2.7, 3.4), aspect=0.84,
                   mod=lambda th: 1 + 0.42 * max(0.0, -math.sin(th)) ** 7 - 0.1 * max(0.0, -math.sin(th)) ** 2 * abs(math.cos(th)))
        cores = [(16, 14.8, 8.6, 8.4), (16, 7.4, 3.2, 3.6)]
    elif v == 2:  # ancient wide chestnut: huge short trunk, low broad crown
        t.shadow = (16.6, 12)
        t.trunk((16, 38), (16.6, 32), (15.6, 27.5), 5.0, 3.4, flare=1.6, marks=0)
        t.branch((15.4, 29), (10, 28), (6.4, 24), 1.9, 0.8)
        t.branch((16.6, 29), (22, 27.6), (26, 24), 1.9, 0.8)
        cl = cloud(r, 16, 19.0, 14.4, 9.4, rr=(2.8, 3.6), aspect=0.82, gaps=((300, 322),), mod=flat_bottom(0.86))
        cores = [(16, 19.6, 11.6, 6.6)]
    else:  # young upright chestnut
        t.shadow = (16.6, 8)
        t.trunk((16, 38), (16.4, 31), (16, 22), 2.6, 1.6, flare=0.8, marks=0)
        cl = cloud(r, 16, 14.4, 8.8, 12.2, rr=(2.5, 3.1), aspect=0.86)
        cores = [(16, 14.8, 6.6, 9.6)]
    # spiral (twisted) bark on the visible trunk
    t.top.append(f'<path d="M14.6 37.2l2.4-2.8M14.8 34.4l2.4-2.8M15.6 37.4l1.8-2" fill="none" stroke="{INK}" '
                 f'stroke-width=".4" stroke-opacity=".55"/>')
    t.crown(cl, pal, cores=cores, bumps=(5, 6), bump=0.5)


def ash(t, v):
    r = t.rng
    pal = ("#4f6b35", "#72904a", "#9cb063")
    if v == 1:  # open airy oval crown, ascending branches show through gaps
        t.shadow = (16.8, 8.5)
        t.trunk((16, 38), (16.2, 26), (15.8, 10), 2.4, 0.8, GREY_BARK, flare=0.8, marks=2)
        for a, c, b in (((16, 27), (12, 24), (9, 17)), ((16, 25), (20, 22), (23, 15)), ((16, 20), (12.5, 16), (11, 9.5)),
                        ((16, 18), (19.5, 14), (20.6, 8))):
            t.branch(a, c, b, 1.1, 0.4, GREY_BARK)
        cl = cloud(r, 16, 15.6, 11.2, 12.4, rr=(2.0, 2.7), aspect=0.86, spacing=1.6, inner_density=1.4,
                   gaps=((205, 224), (338, 352)), keep_out=((19.4, 17.6, 2.7), (12.2, 12.4, 2.3)))
    elif v == 2:  # lopsided ash, crown thrown to the left, gap upper right
        t.shadow = (15.6, 8.5)
        t.trunk((16.6, 38), (17, 27), (14.6, 12), 2.4, 0.8, GREY_BARK, flare=0.8, marks=2)
        for a, c, b in (((16.4, 26), (12.5, 23), (8.6, 18)), ((16, 22), (19.5, 18.5), (21.5, 13)),
                        ((15.4, 18), (11.5, 14), (9.5, 10))):
            t.branch(a, c, b, 1.1, 0.4, GREY_BARK)
        cl = cloud(r, 14.2, 15.4, 10.6, 11.2, rr=(2.0, 2.7), aspect=0.86, spacing=1.6, inner_density=1.3,
                   gaps=((290, 330),), keep_out=((20.5, 9.5, 3.2),))
    else:  # young ash: narrow, tall, sparse
        t.shadow = (16.4, 6)
        t.trunk((16, 38), (15.6, 26), (16.4, 6), 2.0, 0.6, GREY_BARK, flare=0.6, marks=2)
        t.branch((16, 24), (13, 21), (12, 16), 0.9, 0.35, GREY_BARK)
        t.branch((16.2, 20), (19, 17.5), (19.8, 12), 0.9, 0.35, GREY_BARK)
        cl = cloud(r, 16, 15.0, 7.4, 12.8, rr=(1.9, 2.5), aspect=0.88, spacing=1.6, inner_density=1.3,
                   gaps=((8, 26),), keep_out=((14.6, 12.0, 2.3),))
    t.crown(cl, pal, bumps=(6, 8), bump=0.36, light_bias=0.1)


def elm(t, v):
    r = t.rng
    if v == 1:  # vase: trunk forks into upward-spreading limbs, crown widest at the top
        t.shadow = (16.8, 9)
        t.trunk((16, 38), (16, 32), (16, 26.5), 2.8, 2.2, flare=1.0, marks=2)
        for a, c, b in (((15.6, 27.5), (12, 22), (8.4, 13)), ((16.4, 27.5), (20, 22), (23.6, 13)),
                        ((16, 27), (15.4, 19), (15.6, 9))):
            t.branch(a, c, b, 1.7, 0.6)
        # bottle/vase: wide top, crown pinched in towards the fork
        cl = cloud(r, 16, 11.4, 14.2, 9.0, rr=(2.6, 3.3), aspect=0.84,
                   mod=lambda th: 1 - 0.42 * max(0.0, math.sin(th)) ** 1.6) + \
            [(11.4, 18.4, 2.0, 1.8), (20.6, 18.2, 2.0, 1.8)]
        cores = [(16, 10.8, 11.2, 5.4)]
    elif v == 2:  # broad umbrella with drooping outer edges
        t.shadow = (17, 11)
        t.trunk((16, 38), (16.2, 32), (16, 25), 3.0, 2.2, flare=1.1, marks=2)
        for a, c, b in (((15.6, 26), (10, 20), (5.4, 16)), ((16.4, 26), (22, 20), (26.6, 16)),
                        ((16, 25.5), (14, 17), (12.6, 10)), ((16.2, 25.5), (18.4, 17), (20.4, 9.6))):
            t.branch(a, c, b, 1.6, 0.5)
        cl = cloud(r, 16, 11.4, 14.4, 6.8, rr=(2.6, 3.2), aspect=0.82) + \
            [(3.6, 16.6, 2.2, 2.4), (28.4, 16.8, 2.2, 2.4), (6.6, 17.6, 2.0, 1.8), (25.4, 17.8, 2.0, 1.8)]
        cores = [(16, 11.6, 11.5, 4.8)]
    else:  # slender elm, leaning, narrow vase
        t.shadow = (17.4, 7)
        t.trunk((15.4, 38), (15.2, 31), (17, 25), 2.4, 1.8, flare=0.9, marks=2)
        for a, c, b in (((16.6, 26), (14, 20), (12.4, 12)), ((17.2, 26), (20.5, 20), (22.6, 12)),
                        ((17, 25.5), (17.6, 18), (18.2, 8))):
            t.branch(a, c, b, 1.4, 0.5)
        cl = cloud(r, 17.6, 11.4, 9.0, 8.6, rr=(2.4, 3.0), aspect=0.86, mod=flat_bottom(0.8))
        cores = [(17.6, 11.2, 6.8, 6)]
    t.crown(cl, BRD, cores=cores, bumps=(7, 9), bump=0.3)


def willow(t, v):
    r = t.rng
    if v == 1:  # weeping willow: dome with a curtain of hanging strands, trunk visible in the gap
        t.shadow = (17, 12)
        t.trunk((16, 38), (16.4, 31), (15.6, 20), 3.2, 2.0, flare=1.1, marks=3)
        t.curtain(3.6, 28.4, 13, 35.4, WILLOW, count=7, gap=6.0)
        cl = cloud(r, 16, 11.4, 12.6, 7.2, rr=(2.6, 3.2), aspect=0.78, mod=flat_bottom(0.9))
        cores = [(16, 11.6, 10, 5)]
    elif v == 2:  # leaning over water: trunk slants right, curtain longer on the right
        t.shadow = (19, 11)
        t.trunk((12.6, 38), (12.6, 29), (19, 16), 3.0, 1.8, flare=1.0, marks=3)
        t.curtain(8.4, 30.4, 13, 33.2, WILLOW, count=6, gap=2.0, slope=2.4)
        cl = cloud(r, 19.4, 11.2, 11.0, 6.6, rr=(2.4, 3.0), aspect=0.78)
        cores = [(19.4, 11.4, 8.6, 4.6)]
    else:  # pollard-like: thick short trunk, rounder head, short curtain
        t.shadow = (16.6, 10)
        t.trunk((16, 38), (15.6, 32), (16, 23.5), 3.6, 3.0, flare=1.2, marks=3)
        t.curtain(5.6, 26.4, 17, 32.6, WILLOW, count=6, gap=5.0)
        cl = cloud(r, 16, 15.2, 10.6, 6.6, rr=(2.4, 3.0), aspect=0.8)
        cores = [(16, 15.4, 8.4, 4.6)]
    t.crown(cl, WILLOW, cores=cores, bumps=(7, 9), bump=0.3)


SPECIES = (
    ("pine", pine), ("spruce", spruce), ("larch", larch), ("fir", fir), ("cedar", cedar), ("cypress", cypress),
    ("yew", yew), ("redwood", redwood), ("oak", oak), ("beech", beech), ("birch", birch), ("maple", maple),
    ("chestnut", chestnut), ("ash", ash), ("elm", elm), ("willow", willow),
)
VARIANTS = 3  # main + v2 + v3


def symbol_ids():
    out = []
    for name, _fn in SPECIES:
        out.append(f"tree-{name}")
        out.extend(f"tree-{name}-v{k}" for k in range(2, VARIANTS + 1))
    return out


def build() -> str:
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" style="position:absolute">',
             "<!-- 织梦 · 地图树种（组 A：针叶 pine spruce larch fir cedar cypress yew redwood；"
             "阔叶 oak beech birch maple chestnut ash elm willow）。本工程原创。",
             "     手绘铜版加淡彩：外轮廓 #3b2f22 0.8（墨线垫在填色下方，1.6 描边只露外侧 0.8），内线 0.4-0.5，光源左上。",
             "     tree-{species} 为主图，tree-{species}-v2/-v3 为变种，供绘制时混排。viewBox 0 0 32 40，锚点（树根落地点）(16,38)。",
             "     由 tools/gen_tree_art_a.py 确定性生成（种子 20261020 ^ crc32(id)），请改脚本后重新生成，不要手改。 -->",
             "<defs>"]
    for name, fn in SPECIES:
        for k in range(1, VARIANTS + 1):
            sid = f"tree-{name}" if k == 1 else f"tree-{name}-v{k}"
            t = Tree(sid)
            fn(t, k)
            parts.append(t.svg())
    parts.append("</defs>\n</svg>\n")
    return "\n".join(parts)


def main(argv=None):
    import argparse
    global Q
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--q", type=int, default=Q, help="output grid per unit (4 = quarter units)")
    args = ap.parse_args(argv)
    Q = args.q
    out = Path(args.out)
    text = build()
    out.write_text(text, encoding="utf-8", newline="\n")
    print(f"{out}: {len(symbol_ids())} symbols, {len(text.encode('utf-8'))} bytes")


if __name__ == "__main__":
    main()
