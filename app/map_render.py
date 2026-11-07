"""Display-only map renderer for read-only terrain crops (app/terrain_source.py).

美术只决定怎么画，不改地形：海陆/高程/分类完全取自 crop 结果（海 = status OCEAN，
不按 height<0），显示降采样逐 f 取原生样点（不合成新分类），纸纹/晕染/水纹/海岸线
都只是叠加的显示纹理。所有随机纹理用由名称经 SHA-256 派生的固定种子，结果逐字节确定。
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import html
import json
import math
from pathlib import Path

import numpy as np
from scipy import ndimage as nd

from app.terrain_source import CLOSED_BELOW_SEA, LAND, OCEAN, UNKNOWN, WORLD_SEED

ART_DIR = Path(__file__).resolve().parent / "static" / "map-art"
STYLES_PATH = ART_DIR / "styles.json"
MANIFEST_PATH = ART_DIR / "manifest.json"
SYMBOL_KINDS = ("snowpeak", "mountain", "hill", "marsh")
TOWN_TIERS = ("hamlet", "town", "city", "capital")
ROUTE_KINDS = ("royal_road", "road", "track", "trail", "sea_route", "river")
ROUTE_MARKS = ("bridge", "ford", "pass", "port")
_NICE = (1.0, 2.0, 2.5, 5.0)


def load_styles(path=STYLES_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_manifest(path=MANIFEST_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def layer_on(style, name):
    """Per-style symbol-layer switch (styles.json styles.<name>.layers)."""
    return bool(style.get("layers", {}).get(name, False))


def _style(style, styles=None):
    if isinstance(style, str):
        return (styles or load_styles())["styles"][style]
    return style


def resolve_town_symbol(style, race, tier, styles=None):
    """(sprite file, symbol id) for a town of `race` / `tier` in a style.

    Race towns (elf/dwarf/orc/halfling) come from styles.<s>.race_towns when enabled; human and unknown races fall
    back to the style's own town symbols (manifest towns.race_source: 未知种族回落到人类图标).
    """
    st = _style(style, styles)
    if tier not in TOWN_TIERS:
        raise ValueError("unknown town tier %r" % (tier,))
    rt = st.get("race_towns") or {}
    if rt.get("enabled") and race in rt.get("races", ()):
        return rt["sprite"], rt.get("pattern", "town-{race}-{tier}").format(race=race, tier=tier)
    towns = st["towns"]
    return towns["sprite"], towns["pattern"].format(race=towns.get("default_race", "human"), tier=tier)


def validate_towns(style, towns, styles=None):
    """Resolve every town ({'tier', 'race'?}) to its symbol; enforce styles.<s>.towns.capital_unique.

    The uniqueness rule counts capital-tier towns of every race. Violations raise ValueError (no silent downgrade).
    """
    st = _style(style, styles)
    towns = list(towns)
    if st["towns"].get("capital_unique"):
        n = sum(1 for t in towns if t["tier"] == "capital")
        if n > 1:
            raise ValueError("%s: 都城全图唯一，但输入里有 %d 个 capital 级城镇（含种族城镇）" % (st.get("label", "style"), n))
    out = []
    for t in towns:
        sprite, sid = resolve_town_symbol(st, t.get("race"), t["tier"])
        out.append(dict(t, sprite=sprite, id=sid))
    return out


_SYMBOL_RE = r'<symbol id="%s"[\s\S]*?</symbol>'


def extract_symbols(svg_text, ids):
    """Pull individual <symbol> elements out of a sprite (so sprites with clashing ids can be mixed by id)."""
    import re
    out = []
    for sid in ids:
        m = re.search(_SYMBOL_RE % re.escape(sid), svg_text)
        if not m:
            raise KeyError("symbol %s not found" % sid)
        out.append(m.group(0))
    return out


def sprite_ids(svg_text):
    import re
    return re.findall(r'<symbol id="([^"]+)"', svg_text)


def style_sprites_svg(style, art_dir=ART_DIR, extra=None):
    """Inline SVG defs for a style: whole icon sprites + decoration symbols extracted by id (+ optional extra {file: ids})."""
    parts = [Path(art_dir, name).read_text(encoding="utf-8") for name in style["sprites"]]
    picks = {}
    for src in (style.get("decoration_symbols") or {}, extra or {}):
        for name, ids in src.items():
            picks.setdefault(name, [])
            picks[name] += [i for i in ids if i not in picks[name]]
    syms = []
    for name, ids in picks.items():
        syms += extract_symbols(Path(art_dir, name).read_text(encoding="utf-8"), ids)
    if syms:
        parts.append('<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" style="position:absolute"><defs>%s</defs></svg>' % "\n".join(syms))
    return "\n".join(parts)


def stable_seed(name):
    """Deterministic sub-seed derived from WORLD_SEED and a stable purpose name."""
    return int.from_bytes(hashlib.sha256(f"{WORLD_SEED}/map-render/{name}".encode()).digest()[:8], "little")


def hex_rgb(color):
    c = color.lstrip("#")
    return np.array([int(c[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float64)


def _odd(n):
    n = max(1, int(round(n)))
    return n if n % 2 else n + 1


def _normalize(a):
    a = a - a.mean()
    sd = a.std()
    return a / sd if sd > 0 else a


def _smooth_noise(shape, cell, rng):
    h, w = shape
    cell = max(2.0, float(cell))
    small = rng.standard_normal((int(math.ceil(h / cell)) + 4, int(math.ceil(w / cell)) + 4))
    big = nd.zoom(small, cell, order=3, mode="nearest")
    return _normalize(big[:h, :w])


def _blend(rgb, color, alpha):
    a = np.clip(alpha, 0.0, 1.0)[..., None]
    rgb *= 1.0 - a
    rgb += a * color


# ---------------------------------------------------------------- data → display grid

def display_grid(crop, width):
    """Point-decimate a crop by an integer factor (display only; every pixel is a source sample)."""
    elev = np.asarray(crop["elevation_m"], dtype=np.float64)
    status = np.asarray(crop["status"], dtype=np.uint8)
    nz, nx = status.shape
    factor = max(1, int(round(nx / float(width))))
    h, w = nz // factor, nx // factor
    if h < 1 or w < 1:
        raise ValueError("Crop smaller than one display pixel")
    st = np.ascontiguousarray(status[:h * factor:factor, :w * factor:factor])
    el = np.ascontiguousarray(elev[:h * factor:factor, :w * factor:factor])
    # Block mean only feeds hillshade/slope (smooth shading); classes and colours use point samples.
    blocks = elev[:h * factor, :w * factor].reshape(h, factor, w, factor)
    valid = np.isfinite(blocks)
    count = valid.sum(axis=(1, 3))
    total = np.where(valid, blocks, 0.0).sum(axis=(1, 3))
    shade = np.where(count > 0, total / np.maximum(count, 1), 0.0)
    spacing = float(crop["spacing_m"])
    first = tuple(float(v) for v in crop["first_sample_xz_m"])
    return dict(elevation=el, status=st, shade_elevation=shade, factor=factor,
                m_per_px=spacing * factor, source_spacing_m=spacing, first_sample_xz_m=first,
                source_shape_zx=(nz, nx), display_shape_zx=(h, w),
                downsample="point sample every %d native samples (display only); hillshade from %dx%d block mean" % (factor, factor, factor))


def _band_index(values, bands, key):
    thresholds = np.array([b[key] for b in bands[:-1]], dtype=np.float64)
    return np.searchsorted(thresholds, values, side="left")


def _band_colors(values, bands, key, blend):
    colors = np.stack([hex_rgb(b["color"]) for b in bands])
    if not blend:
        return colors[_band_index(values, bands, key)]
    th = [float(b[key]) for b in bands[:-1]]
    lows = [0.0] + th
    highs = th + [th[-1] + (th[-1] - (th[-2] if len(th) > 1 else 0.0))]
    centers = np.array([(a + b) / 2 for a, b in zip(lows, highs)])
    return np.stack([np.interp(values, centers, colors[:, c]) for c in range(3)], axis=-1)


def base_colors(elevation, status, style):
    """Flat colour layer: land by elevation band, ocean by depth band, closed / unknown by status."""
    elevation = np.asarray(elevation, dtype=np.float64)
    status = np.asarray(status)
    e = np.nan_to_num(elevation, nan=0.0)
    blend = bool(style.get("land_blend", False))
    rgb = np.empty(status.shape + (3,), dtype=np.float64)
    rgb[:] = hex_rgb(style["unknown"]["color"])
    land = status == LAND
    ocean = status == OCEAN
    closed = status == CLOSED_BELOW_SEA
    rgb[land] = _band_colors(np.maximum(e[land], 0.0), style["land_bands"], "max_m", blend)
    rgb[ocean] = _band_colors(np.maximum(-e[ocean], 0.0), style["ocean_bands"], "max_depth_m", blend)
    rgb[closed] = hex_rgb(style["closed_below_sea"]["color"])
    return rgb


def hillshade(z, spacing, azimuth_deg, altitude_deg, z_factor):
    """Lambert hillshade; array rows run south (Z south), columns east (X east)."""
    gz, gx = np.gradient(z * z_factor, spacing)
    dzdx, dzdn = gx, -gz
    az, alt = math.radians(azimuth_deg), math.radians(altitude_deg)
    lx, ly, lz = math.sin(az) * math.cos(alt), math.cos(az) * math.cos(alt), math.sin(alt)
    norm = np.sqrt(dzdx * dzdx + dzdn * dzdn + 1.0)
    return (-dzdx * lx - dzdn * ly + lz) / norm, lz


def scale_bar(m_per_px, s, segments=5, target_ref_px=380.0):
    """Nice round scale bar whose pixel length × metres-per-pixel equals its labelled metres exactly."""
    want = target_ref_px * s * m_per_px
    best = None
    for k in range(0, 9):
        for n in _NICE:
            meters = n * 10 ** k
            if meters <= want * 1.15 and (best is None or meters > best):
                best = meters
    meters = best or 1.0
    return dict(meters=meters, segments=segments, segment_m=meters / segments,
                length_px=meters / m_per_px, m_per_px=m_per_px)


# ---------------------------------------------------------------- symbols

def terrain_candidates(grid, ts, s):
    elev, status, mpp = grid["elevation"], grid["status"], grid["m_per_px"]
    land = status == LAND
    e = np.where(land | (status == CLOSED_BELOW_SEA), np.nan_to_num(elev, nan=0.0), 0.0)
    rw = _odd(ts["relief_window_m"] / mpp)
    relief = nd.maximum_filter(e, rw) - nd.minimum_filter(e, rw)
    pw = _odd(ts["peak_window_m"] / mpp)
    peak = land & (e >= nd.maximum_filter(e, pw)) & (relief >= ts["hill_relief_m"])
    ys, xs = np.nonzero(peak)
    rel, el = relief[ys, xs], e[ys, xs]
    kind = np.where(rel >= ts["mountain_relief_m"], np.where(el >= ts["snowline_m"], 0, 1), 2)
    order = np.lexsort((xs, ys, -el, -rel, kind))
    out = [(SYMBOL_KINDS[kind[i]], int(ys[i]), int(xs[i]), float(rel[i]), float(el[i])) for i in order]
    gz, gx = np.gradient(grid["shade_elevation"], mpp)
    slope = np.hypot(gx, gz)
    marsh = land & (slope <= ts["marsh_slope_max"]) & (e <= ts["marsh_elevation_max_m"])
    if marsh.any():
        box = _odd(ts["marsh_box_px"] * s)
        frac = nd.uniform_filter(marsh.astype(np.float64), box, mode="constant")
        frac = np.round(frac, 9)
        pick = marsh & (frac >= ts["marsh_min_fraction"]) & (frac >= nd.maximum_filter(frac, box))
        my, mx = np.nonzero(pick)
        morder = np.lexsort((mx, my, -frac[my, mx]))
        out += [("marsh", int(my[i]), int(mx[i]), float(frac[my[i], mx[i]]), float(e[my[i], mx[i]])) for i in morder]
    return out


def _integral(mask):
    ii = np.zeros((mask.shape[0] + 1, mask.shape[1] + 1), dtype=np.int64)
    ii[1:, 1:] = np.cumsum(np.cumsum(mask, axis=0, dtype=np.int64), axis=1)
    return ii


def _rect_sum(ii, x0, y0, x1, y1):
    return int(ii[y1, x1] - ii[y0, x1] - ii[y1, x0] + ii[y0, x0])


def place_symbols(candidates, status, style, s, occupied):
    cfg = style["symbols"]
    h_img, w_img = status.shape
    ocean_ii = _integral(status == OCEAN)
    counts = dict.fromkeys(SYMBOL_KINDS, 0)
    placed = []
    for kind, y, x, score, elev in candidates:
        c = cfg[kind]
        if counts[kind] >= c["max"]:
            continue
        pad = max(1, int(round(c.get("pad_px", cfg.get("pad_px", 3)) * s)))
        w = max(6.0, c["px"] * s)
        h = w * c["viewbox"][1] / c["viewbox"][0]
        ay = y + h / 2 if kind == "marsh" else y + 0.06 * h
        x0, x1 = int(math.floor(x - w / 2)), int(math.ceil(x + w / 2))
        y0, y1 = int(math.floor(ay - h)), int(math.ceil(ay))
        if x0 < 0 or y0 < 0 or x1 > w_img or y1 > h_img:
            continue
        if status[y, x] != LAND or _rect_sum(ocean_ii, x0, y0, x1, y1):
            continue
        if occupied[max(0, y0 - pad):y1 + pad, max(0, x0 - pad):x1 + pad].any():
            continue
        occupied[y0:y1, x0:x1] = True
        counts[kind] += 1
        placed.append(dict(kind=kind, id=c["id"], x=float(x), y=float(ay), w=round(w, 2), h=round(h, 2),
                           bbox=(x0, y0, x1, y1), score=round(score, 3), elevation_m=round(elev, 1)))
    return placed


# ---------------------------------------------------------------- decorations

LEGEND_ROW = 34.0


def legend_rows(style, kinds, has_closed, has_unknown, has_soundings, ts, has_spots=True):
    east = style.get("legend_language") == "east"
    names = {
        "snowpeak": ("雪峰（起伏≥%d 米且高于 %d 米）" if east else "雪峰 · 起伏≥%d m 且海拔≥%d m") % (ts["mountain_relief_m"], ts["snowline_m"]),
        "mountain": ("山峰（局部起伏≥%d 米）" if east else "山峰 · 局部起伏≥%d m") % ts["mountain_relief_m"],
        "hill": ("丘陵（起伏 %d–%d 米）" if east else "丘陵 · 起伏 %d–%d m") % (ts["hill_relief_m"], ts["mountain_relief_m"]),
        "marsh": "低平湿洼（近似，非实测湿地）" if east else "低平湿洼 · 近似（无湿地数据）",
    }
    rows = []
    for k in SYMBOL_KINDS:
        if k in kinds:
            rows.append(("symbol", k, names[k]))
    if has_spots:
        rows.append(("spot", None, "▲ 高程点（米）" if east else "▲ 高程点（米，取样值）"))
    if has_soundings:
        rows.append(("sounding", None, "水深注记（米）"))
    if has_closed:
        rows.append(("closed", None, "内陆洼地（低于海面，非海）"))
    if has_unknown:
        rows.append(("unknown", None, "未知 / 无数据"))
    return rows


def legend_size(rows, s):
    return 430.0 * s, (56 + 2 * 66 + LEGEND_ROW * len(rows) + 46) * s


def place_decorations(status, ocean_dist, style, s, occupied, sizes):
    h_img, w_img = status.shape
    ocean = status == OCEAN
    inset = int(round(16 * s))
    step = max(2, int(round(8 * s)))
    gap = int(round(14 * s))
    placed, skipped = [], []
    for deco in style["decorations"]:
        w, h = sizes.get(deco["name"], (deco["w"] * s, deco["h"] * s))
        wi, hi = int(math.ceil(w)), int(math.ceil(h))
        margin = (34 if deco["kind"] in ("ship", "serpent", "cloud") else 10) * s
        blocked = ~(ocean & (ocean_dist >= margin))
        if occupied.any():
            blocked |= nd.maximum_filter(occupied, size=2 * gap + 1)
        ii = _integral(blocked)
        ys = np.arange(inset, h_img - hi - inset + 1, step)
        xs = np.arange(inset, w_img - wi - inset + 1, step)
        if len(ys) == 0 or len(xs) == 0:
            skipped.append(deco["name"])
            continue
        Y, X = np.meshgrid(ys, xs, indexing="ij")
        sums = ii[Y + hi, X + wi] - ii[Y, X + wi] - ii[Y + hi, X] + ii[Y, X]
        ok = sums == 0
        if not ok.any():
            skipped.append(deco["name"])
            continue
        tx, ty = deco["target"][0] * w_img, deco["target"][1] * h_img
        dist = (X + w / 2 - tx) ** 2 + (Y + h / 2 - ty) ** 2
        dist = np.where(ok, dist, np.inf)
        k = int(np.argmin(dist))
        x0, y0 = int(X.flat[k]), int(Y.flat[k])
        occupied[y0:y0 + hi, x0:x0 + wi] = True
        placed.append(dict(name=deco["name"], kind=deco["kind"], symbol=deco.get("symbol"), x=x0, y=y0,
                           w=round(w, 2), h=round(h, 2), mirror=bool(deco.get("mirror", False))))
    return placed, skipped


def spot_heights(grid, s, occupied, count=5):
    e = np.where(grid["status"] == LAND, np.nan_to_num(grid["elevation"], nan=0.0), -1e9)
    win = _odd(12000.0 / grid["m_per_px"])
    peak = (grid["status"] == LAND) & (e >= nd.maximum_filter(e, win)) & (e > 0)
    ys, xs = np.nonzero(peak)
    order = np.lexsort((xs, ys, -e[ys, xs]))
    out = []
    h_img, w_img = e.shape
    for i in order:
        if len(out) >= count:
            break
        y, x = int(ys[i]), int(xs[i])
        label = "%d" % int(round(e[y, x]))
        w, h = (18 + 13 * len(label)) * s, 26 * s
        x0, y0 = int(x - 7 * s), int(y - h / 2)
        x1, y1 = int(math.ceil(x0 + w)), int(math.ceil(y0 + h))
        if x0 < 0 or y0 < 0 or x1 > w_img or y1 > h_img or occupied[y0:y1, x0:x1].any():
            continue
        occupied[y0:y1, x0:x1] = True
        out.append(dict(x=float(x), y=float(y), elevation_m=int(round(e[y, x])), label=label, bbox=(x0, y0, x1, y1)))
    return out


def soundings(grid, ocean_dist, cfg, s, occupied):
    if not cfg:
        return []
    status, elev = grid["status"], grid["elevation"]
    h_img, w_img = status.shape
    step = cfg["step_px"] * s
    out = []
    row = 0
    y = step / 2
    while y < h_img:
        x = step / 2 + (step / 2 if row % 2 else 0)
        while x < w_img:
            yi, xi = int(y), int(x)
            if status[yi, xi] == OCEAN and ocean_dist[yi, xi] >= cfg["min_coast_px"] * s:
                label = "%d" % int(round(-elev[yi, xi]))
                w, h = 9.5 * len(label) * s + 4, 16 * s
                x0, y0 = int(xi - w / 2), int(yi - h / 2)
                x1, y1 = int(math.ceil(x0 + w)), int(math.ceil(y0 + h))
                if x0 >= 0 and y0 >= 0 and x1 <= w_img and y1 <= h_img and not occupied[y0:y1, x0:x1].any():
                    occupied[y0:y1, x0:x1] = True
                    out.append(dict(x=float(xi), y=float(yi), depth_m=int(label), label=label))
            x += step
        y += step * 0.866
        row += 1
    return out


# ---------------------------------------------------------------- raster styling

def _paint(grid, style, s):
    elev, status = grid["elevation"], grid["status"]
    h, w = status.shape
    mpp = grid["m_per_px"]
    rgb = base_colors(elev, status, style)
    land = (status == LAND) | (status == CLOSED_BELOW_SEA)
    ocean = status == OCEAN
    other = ~(land | ocean)
    hs_cfg = style["hillshade"]
    zsh = nd.gaussian_filter(grid["shade_elevation"], 0.7)
    shade, flat = hillshade(zsh, mpp, hs_cfg["azimuth_deg"], hs_cfg["altitude_deg"], hs_cfg["z_factor"])
    lum = shade / flat
    strength = np.where(land, hs_cfg["land_strength"], np.where(ocean, hs_cfg["ocean_strength"], 0.0))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    if hs_cfg["mode"] == "multiply":
        factor = np.clip(1.0 + strength * (lum - 1.0), 0.28, 1.0 + hs_cfg.get("highlight", 0.1))
        rgb *= factor[..., None]
        eng = style.get("engraving")
        if eng:  # copper-plate hatching on shaded slopes (display texture only)
            erng = np.random.default_rng(stable_seed(eng["seed_name"]))
            a = math.radians(eng["angle_deg"])
            u = xx * math.cos(a) + yy * math.sin(a) + _smooth_noise((h, w), 60 * s, erng) * eng["wobble_px"] * s
            p = eng["period_px"] * s
            m = np.mod(u, p)
            d = np.minimum(m, p - m)
            line = np.clip(eng["line_px"] * s / 2 + 0.5 - d, 0.0, 1.0)
            dark = np.clip((1.0 - lum - eng["threshold"]) * eng["gain"], 0.0, 1.0)
            _blend(rgb, hex_rgb(eng["color"]), line * dark * eng["alpha"] * (status == LAND))
    else:  # ink wash: dark slopes take ink, high ground takes a faint extra wash, bleeding a little
        dark = np.clip(1.0 - lum, 0.0, 1.0) ** hs_cfg.get("gamma", 1.0)
        top = max(1.0, float(np.nanmax(np.where(land, np.nan_to_num(elev), 0.0))))
        elev_ink = hs_cfg.get("elevation_ink", 0.0) * np.clip(np.nan_to_num(elev) / top, 0.0, 1.0)
        ink = strength * dark + np.where(land, elev_ink, 0.0)
        bleed = hs_cfg.get("ink_bleed_px", 0.0) * s
        if bleed > 0:
            ink = nd.gaussian_filter(ink, bleed) * 0.6 + ink * 0.4
        ink = np.where(land | ocean, np.clip(ink, 0.0, 0.85), 0.0)
        _blend(rgb, hex_rgb(hs_cfg["ink"]), ink)
        light = np.where(land, np.clip(lum - 1.0, 0.0, 1.0) * hs_cfg.get("highlight", 0.0), 0.0)
        _blend(rgb, hex_rgb(style["page"]["background"]), light * 2.0)
        desat = hs_cfg.get("desaturate", 0.0)
        if desat > 0:
            grey = rgb.mean(axis=-1, keepdims=True)
            rgb += (grey - rgb) * desat * (land | ocean)[..., None]
    # faint hypsometric band contours (land only)
    ca = style.get("band_contour_alpha", 0.0)
    if ca > 0:
        idx = _band_index(np.maximum(np.nan_to_num(elev), 0.0), style["land_bands"], "max_m")
        edge = np.zeros_like(land)
        edge[:, 1:] |= idx[:, 1:] != idx[:, :-1]
        edge[1:, :] |= idx[1:, :] != idx[:-1, :]
        edge &= land & (status == LAND)
        _blend(rgb, hex_rgb(style["band_contour_color"]), edge * ca)
    # moss dots (eastern 苔点): display texture on high ground only
    moss = style.get("moss_dots")
    if moss:
        rng = np.random.default_rng(stable_seed(moss["seed_name"]))
        p = moss["density"] * np.clip((np.nan_to_num(elev) - moss["from_m"]) / moss["span_m"], 0.0, 1.0)
        p = np.where(status == LAND, p, 0.0)
        dots = (rng.random((h, w)) < p).astype(np.float64)
        dots = np.clip(nd.gaussian_filter(dots, moss["radius_px"] * s) * moss["gain"], 0.0, 1.0)
        _blend(rgb, hex_rgb(moss["color"]), dots * moss["alpha"])
    # inland depressions: own colour + dots + outline (never sea colours)
    closed = status == CLOSED_BELOW_SEA
    if closed.any():
        c = style["closed_below_sea"]
        p = max(3.0, c["pattern_px"] * s)
        dots = np.clip(1.2 - np.hypot(yy % p - p / 2, (xx + (yy // p % 2) * p / 2) % p - p / 2), 0.0, 1.0)
        _blend(rgb, hex_rgb(c["pattern_color"]), dots * c["pattern_alpha"] * closed)
        rim = closed & ~nd.binary_erosion(closed, iterations=max(1, int(round(1.5 * s))))
        _blend(rgb, hex_rgb(style["page"]["ink"]), rim * c["outline_alpha"])
    if other.any():
        u = style["unknown"]
        p = max(3.0, u["pattern_px"] * s)
        hatch = np.clip(1.1 - np.abs((xx + yy) % p - p / 2), 0, 1)
        _blend(rgb, hex_rgb(u["pattern_color"]), hatch * u["pattern_alpha"] * other)
    # coast: lines live on the sea side only, so the data shoreline is never moved or covered
    co = style["coast"]
    dist = nd.distance_transform_edt(ocean)
    rng = np.random.default_rng(stable_seed(style["paper"]["seed_name"] + "/coast"))
    wob = _smooth_noise((h, w), 48 * s, rng) * co.get("wobble_px", 0.0) * s
    lw = co["line_px"] * s * (1.0 + co.get("line_jitter", 0.0) * np.clip(_smooth_noise((h, w), 70 * s, rng), -1, 1))
    a = np.clip(lw + 0.5 - dist, 0.0, 1.0) * ocean
    _blend(rgb, hex_rgb(co["ink"]), a)
    if co.get("second_line_px", 0) > 0:
        d2 = np.abs(dist - co["second_line_at_px"] * s)
        _blend(rgb, hex_rgb(co["ink"]), np.clip(co["second_line_px"] * s / 2 + 0.5 - d2, 0, 1) * co["second_alpha"] * ocean)
    wash = hs_cfg.get("coast_wash_px", 0) * s
    if wash > 0:  # pale ink halo on the sea side of the coast
        _blend(rgb, hex_rgb(hs_cfg["coast_wash_color"]), np.exp(-dist / wash) * hs_cfg["coast_wash_alpha"] * ocean)
    dw = dist + wob
    step = co["ripple_step_px"] * s
    k = np.round((dw - co["ripple_start_px"] * s) / step)
    valid = (k >= 0) & (k < co["ripple_count"]) & ocean & (dist > lw + 1)
    rd = np.abs(dw - (co["ripple_start_px"] * s + k * step))
    fade = 1.0 - np.clip(k, 0, None) / co["ripple_count"]
    _blend(rgb, hex_rgb(co["ripple_color"]), np.clip(co["ripple_px"] * s / 2 + 0.5 - rd, 0, 1) * fade * co["ripple_alpha"] * valid)
    sea = style.get("open_sea_pattern")
    if sea:
        stp, amp, per = sea["step_px"] * s, sea["amp_px"] * s, sea["period_px"] * s
        phase = _smooth_noise((h, w), 120 * s, rng) * 1.2
        yw = yy + amp * np.sin(2 * math.pi * xx / per + phase)
        ld = np.abs((yw % stp) - stp / 2)
        dash = np.clip(_smooth_noise((h, w), sea["dash_period_px"] * s / 3, rng) * 1.5 + 0.3, 0, 1)
        fin = np.clip((dist - sea["start_px"] * s) / (50 * s), 0, 1) * ocean
        _blend(rgb, hex_rgb(sea["color"]), np.clip(sea["line_px"] * s / 2 + 0.5 - ld, 0, 1) * dash * fin * sea["alpha"])
    return rgb, dist


def _paper(page, cfg, s):
    h, w = page.shape[:2]
    rng = np.random.default_rng(stable_seed(cfg["seed_name"]))
    f = np.ones((h, w))
    if cfg.get("grain"):
        f += cfg["grain"] * np.clip(_normalize(nd.gaussian_filter(rng.standard_normal((h, w)), 0.7)), -3, 3) * 0.5
    if cfg.get("blotch"):
        cell = cfg["blotch_cell_px"] * s
        f += cfg["blotch"] * 0.5 * (_smooth_noise((h, w), cell, rng) * 0.7 + _smooth_noise((h, w), cell / 3, rng) * 0.3)
    if cfg.get("fiber"):
        fib = _normalize(nd.gaussian_filter(rng.standard_normal((h, w)), (0.6, 9 * s))) + \
            _normalize(nd.gaussian_filter(rng.standard_normal((h, w)), (9 * s, 0.6))) * 0.6
        f -= cfg["fiber"] * np.clip(fib - 1.2, 0, None)
    if cfg.get("vignette"):
        yy, xx = np.mgrid[0:h, 0:w]
        r = np.hypot((xx - w / 2) / (w / 2), (yy - h / 2) / (h / 2))
        f *= 1.0 - cfg["vignette"] * np.clip((r - 0.7) / 0.75, 0, 1) ** 2
    page *= f[..., None]
    return page


@dataclass
class RenderResult:
    style_name: str
    rgb: np.ndarray  # whole page (map + margin), uint8
    margin: int
    map_size: tuple  # (width, height) px
    grid_info: dict
    scale: dict
    symbols: list = field(default_factory=list)
    decorations: list = field(default_factory=list)
    skipped_decorations: list = field(default_factory=list)
    spot_heights: list = field(default_factory=list)
    soundings: list = field(default_factory=list)
    legend: list = field(default_factory=list)
    status_counts: dict = field(default_factory=dict)


def render_map(crop, style_name, width=2048, *, styles=None):
    styles = styles or load_styles()
    style = styles["styles"][style_name]
    ts = styles["terrain_symbols"]
    grid = display_grid(crop, width)
    status = grid["status"]
    h, w = status.shape
    s = w / float(styles["reference_px"])
    rgb, ocean_dist = _paint(grid, style, s)
    margin = int(round(style["page"]["margin_px"] * s))
    page = np.empty((h + 2 * margin, w + 2 * margin, 3), dtype=np.float64)
    page[:] = hex_rgb(style["page"]["background"])
    page[margin:margin + h, margin:margin + w] = rgb
    page = np.clip(np.rint(_paper(page, style["paper"], s)), 0, 255).astype(np.uint8)

    scale = scale_bar(grid["m_per_px"], s)
    # terrain symbols are a per-style layer: off for medieval/eastern, where relief lives only in the base raster
    cands = terrain_candidates(grid, ts, s) if layer_on(style, "terrain_symbols") else []
    kinds = {c[0] for c in cands}
    rows = legend_rows(style, kinds, bool((status == CLOSED_BELOW_SEA).any()),
                       bool((~np.isin(status, (LAND, OCEAN, CLOSED_BELOW_SEA))).any()),
                       bool(style.get("soundings")) and layer_on(style, "soundings"), ts, layer_on(style, "spot_heights"))
    sizes = {"legend": legend_size(rows, s), "scale": ((scale["length_px"] + 70 * s), 84 * s)}
    occupied = np.zeros((h, w), dtype=bool)
    if layer_on(style, "decorations"):
        decos, skipped = place_decorations(status, ocean_dist, style, s, occupied, sizes)
    else:
        decos, skipped = [], []
    spots = spot_heights(grid, s, occupied) if layer_on(style, "spot_heights") else []
    symbols = place_symbols(cands, status, style, s, occupied) if cands else []
    sounds = soundings(grid, ocean_dist, style.get("soundings"), s, occupied) if layer_on(style, "soundings") else []
    info = {k: v for k, v in grid.items() if k not in ("elevation", "status", "shade_elevation")}
    counts = {name: int((status == code).sum()) for name, code in
              (("unknown", UNKNOWN), ("ocean", OCEAN), ("closed_below_sea", CLOSED_BELOW_SEA), ("land", LAND))}
    return RenderResult(style_name, page, margin, (w, h), info, scale, symbols, decos, skipped, spots, sounds, rows, counts)


# ---------------------------------------------------------------- SVG / HTML composition

def _f(v):
    return ("%.2f" % v).rstrip("0").rstrip(".")


def _text(x, y, txt, cls, size, anchor="middle", extra=""):
    return '<text class="%s" x="%s" y="%s" font-size="%s" text-anchor="%s"%s>%s</text>' % (
        cls, _f(x), _f(y), _f(size), anchor, extra, html.escape(txt))


def _scale_svg(d, sc, style, s, east):
    ink = style["page"]["ink"]
    L, n = sc["length_px"], sc["segments"]
    x0 = d["x"] + 30 * s
    yb = d["y"] + 34 * s
    parts = []
    if not east:
        uw = L * 120.0 / 115.0
        parts.append('<use href="#deco-scale" x="%s" y="%s" width="%s" height="%s"/>' % (
            _f(x0 - 2 * uw / 120), _f(yb - 5 * uw / 120 + 3 * s), _f(uw), _f(16 * uw / 120)))
    else:
        bh = 7 * s
        parts.append('<rect x="%s" y="%s" width="%s" height="%s" fill="none" stroke="%s" stroke-width="%s"/>' % (
            _f(x0), _f(yb), _f(L), _f(bh), ink, _f(1.2 * s)))
        for i in range(n):
            if i % 2 == 0:
                parts.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s"/>' % (
                    _f(x0 + i * L / n), _f(yb), _f(L / n), _f(bh), ink))
    unit = 1000.0
    for i in range(n + 1):
        v = sc["segment_m"] * i / unit
        parts.append(_text(x0 + i * L / n, yb - 7 * s, _f(v), "t-body", 17 * s))
    parts.append(_text(x0 + L + 10 * s, yb + 8 * s, "公里" if east else "km", "t-body", 17 * s, "start"))
    cap = ("比例尺 · 每像素 %s 米" if east else "比例尺 · 每像素 %s m") % _f(sc["m_per_px"])
    parts.append(_text(x0 + L / 2, yb + 36 * s, cap, "t-body", 15 * s))
    return parts


def _legend_svg(d, res, style, styles, s, east):
    ink = style["page"]["ink"]
    x, y, w, h = d["x"], d["y"], d["w"], d["h"]
    p = []
    fill = "#f4ead2" if not east else "#f3ecdc"
    p.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s" fill-opacity=".93" stroke="%s" stroke-width="%s"/>' % (
        _f(x), _f(y), _f(w), _f(h), fill, ink, _f(1.6 * s)))
    p.append('<rect x="%s" y="%s" width="%s" height="%s" fill="none" stroke="%s" stroke-width="%s"/>' % (
        _f(x + 6 * s), _f(y + 6 * s), _f(w - 12 * s), _f(h - 12 * s), style["page"]["accent"] if not east else ink, _f(0.8 * s)))
    p.append(_text(x + w / 2, y + 40 * s, style["text"]["legend_title"], "t-title", 28 * s))
    pad = 24 * s
    bw = w - 2 * pad
    cy = y + 62 * s
    for key, bands, label, unit_key in (("land", style["land_bands"], "海拔（米）", "max_m"),
                                        ("ocean", style["ocean_bands"], "水深（米）", "max_depth_m")):
        n = len(bands)
        p.append(_text(x + pad, cy + 10 * s, label, "t-body", 16 * s, "start"))
        by = cy + 18 * s
        for i, b in enumerate(bands):
            p.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s"/>' % (
                _f(x + pad + i * bw / n), _f(by), _f(bw / n + 0.5), _f(14 * s), b["color"]))
        p.append('<rect x="%s" y="%s" width="%s" height="%s" fill="none" stroke="%s" stroke-width="%s"/>' % (
            _f(x + pad), _f(by), _f(bw), _f(14 * s), ink, _f(0.8 * s)))
        for i, b in enumerate(bands[:-1]):
            if key == "ocean" or i % 2 == 1:
                p.append(_text(x + pad + (i + 1) * bw / n, by + 30 * s, "%d" % b[unit_key], "t-body", 13 * s))
        cy += 66 * s
    for kind, sym_kind, label in res.legend:
        ry = cy + LEGEND_ROW * s / 2
        ix = x + pad + 22 * s
        if kind == "symbol":
            c = style["symbols"][sym_kind]
            sw = 36 * s
            sh = sw * c["viewbox"][1] / c["viewbox"][0]
            p.append('<use href="#%s" x="%s" y="%s" width="%s" height="%s"/>' % (c["id"], _f(ix - sw / 2), _f(ry - sh / 2), _f(sw), _f(sh)))
        elif kind == "spot":
            label = label[2:]
            p.append('<path d="M%s %s l%s %s h%s z" fill="%s"/>' % (_f(ix), _f(ry - 7 * s), _f(6 * s), _f(10 * s), _f(-12 * s), ink))
        elif kind == "sounding":
            p.append(_text(ix, ry + 6 * s, "1250", "t-sound", 15 * s))
        elif kind in ("closed", "unknown"):
            col = style["closed_below_sea" if kind == "closed" else "unknown"]["color"]
            p.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s" stroke="%s" stroke-width="%s"/>' % (
                _f(ix - 14 * s), _f(ry - 9 * s), _f(28 * s), _f(18 * s), col, ink, _f(1.0 * s)))
            if kind == "closed":
                for dx in (-7, 0, 7):
                    p.append('<circle cx="%s" cy="%s" r="%s" fill="%s"/>' % (_f(ix + dx * s), _f(ry), _f(1.3 * s), style["closed_below_sea"]["pattern_color"]))
        p.append(_text(ix + 32 * s, ry + 6 * s, label, "t-body", 16 * s, "start"))
        cy += LEGEND_ROW * s
    p.append(_text(x + w / 2, y + h - 18 * s, style["text"]["decoration_note"], "t-body", 13.5 * s))
    return p


def _frame_svg(res, style, s, east):
    w, h = res.map_size
    ink = style["page"]["ink"]
    mpp = res.grid_info["m_per_px"]
    fx, fz = res.grid_info["first_sample_xz_m"]
    p = []
    if not east:
        L = 5000.0 / mpp
        p.append('<rect x="%s" y="%s" width="%s" height="%s" fill="none" stroke="%s" stroke-width="%s"/>' % (
            _f(-0.5), _f(-0.5), _f(w + 1), _f(h + 1), ink, _f(1.4 * s)))
        o, t = 6 * s, 7 * s
        for side in range(4):
            n = int(math.ceil((w if side % 2 == 0 else h) / L))
            for k in range(0, n, 2):
                a = k * L
                b = min((k + 1) * L, w if side % 2 == 0 else h)
                if side == 0:
                    r = (a, -o - t, b - a, t)
                elif side == 2:
                    r = (a, h + o, b - a, t)
                elif side == 1:
                    r = (w + o, a, t, b - a)
                else:
                    r = (-o - t, a, t, b - a)
                p.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s"/>' % tuple([_f(v) for v in r] + [ink]))
        for off, sw in ((o, 0.9), (o + t, 0.9), (o + t + 7 * s, 2.4)):
            p.append('<rect x="%s" y="%s" width="%s" height="%s" fill="none" stroke="%s" stroke-width="%s"/>' % (
                _f(-off), _f(-off), _f(w + 2 * off), _f(h + 2 * off), ink, _f(sw * s)))
        lab_off = o + t + 16 * s
    else:
        for off, sw, col in ((5 * s, 1.0, style["page"]["accent"]), (12 * s, 1.2, ink), (20 * s, 3.4, ink)):
            p.append('<rect x="%s" y="%s" width="%s" height="%s" fill="none" stroke="%s" stroke-width="%s" stroke-opacity=".9"/>' % (
                _f(-off), _f(-off), _f(w + 2 * off), _f(h + 2 * off), col, _f(sw * s)))
        lab_off = 30 * s
    step = 20000.0
    xs = math.ceil(fx / step) * step
    while (xs - fx) / mpp <= w:
        px = (xs - fx) / mpp
        if px > w - 150 * s:
            break
        p.append(_text(px, -lab_off, "%d" % (xs / 1000), "t-coord", 15 * s))
        xs += step
    zs = math.ceil(fz / step) * step
    while (zs - fz) / mpp <= h:
        pz = (zs - fz) / mpp
        if pz > h - 60 * s:
            break
        p.append(_text(-lab_off + 4 * s, pz + 5 * s, "%d" % (zs / 1000), "t-coord", 15 * s, "end"))
        zs += step
    p.append(_text(w + lab_off - 4 * s, -lab_off, "X 东 / km", "t-coord", 14 * s, "end"))
    p.append(_text(-lab_off + 4 * s, h + lab_off + 2 * s, "Z 南 / km", "t-coord", 14 * s, "start"))
    return p


def compose_html(res, base_href, provenance_line, *, styles=None, art_dir=ART_DIR):
    styles = styles or load_styles()
    style = styles["styles"][res.style_name]
    east = style.get("legend_language") == "east"
    s = res.map_size[0] / float(styles["reference_px"])
    ink = style["page"]["ink"]
    fonts = style["fonts"]
    page_h, page_w = res.rgb.shape[:2]
    m = res.margin
    sprites = style_sprites_svg(style, art_dir)
    o = []
    o.append('<!DOCTYPE html><html><head><meta charset="utf-8"><style>html,body{margin:0;padding:0;background:%s;overflow:hidden}'
             '.t-title{font-family:%s;fill:%s}.t-body{font-family:%s;fill:%s}.t-latin{font-family:%s;fill:%s;font-style:italic}'
             '.t-coord{font-family:%s;fill:%s;opacity:.8}.t-sound{font-family:%s;fill:#3f514f;font-style:italic}'
             '.t-spot{font-family:%s;fill:%s;paint-order:stroke;stroke:%s;stroke-opacity:.75}'
             '</style></head><body>' % (style["page"]["background"], fonts["title"], ink, fonts["body"], ink, fonts["latin"], ink,
                                        fonts["latin"], ink, fonts["latin"], fonts["latin"], ink, style["page"]["background"]))
    o.append(sprites)
    o.append('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" style="display:block">' % (page_w, page_h, page_w, page_h))
    o.append('<image href="%s" x="0" y="0" width="%d" height="%d"/>' % (html.escape(base_href), page_w, page_h))
    o.append('<g transform="translate(%d,%d)">' % (m, m))
    for sym in res.symbols:
        x0 = sym["x"] - sym["w"] / 2
        y0 = sym["y"] - sym["h"] if sym["kind"] != "marsh" else sym["y"] - sym["h"]
        o.append('<use href="#%s" x="%s" y="%s" width="%s" height="%s"/>' % (sym["id"], _f(x0), _f(y0), _f(sym["w"]), _f(sym["h"])))
    for sp in res.spot_heights:
        o.append('<path d="M%s %s l%s %s h%s z" fill="%s"/>' % (_f(sp["x"]), _f(sp["y"] - 6 * s), _f(5.5 * s), _f(9 * s), _f(-11 * s), ink))
        o.append(_text(sp["x"] + 9 * s, sp["y"] + 7 * s, sp["label"], "t-spot", 20 * s, "start", ' stroke-width="%s"' % _f(3.5 * s)))
    for so in res.soundings:
        o.append(_text(so["x"], so["y"] + 5 * s, so["label"], "t-sound", 14 * s))
    for d in res.decorations:
        x, y, w, h = d["x"], d["y"], d["w"], d["h"]
        k = d["kind"]
        if k in ("ship", "serpent", "cloud"):
            if d["mirror"]:
                o.append('<g transform="translate(%s,%s) scale(-1,1)"><use href="#%s" x="0" y="0" width="%s" height="%s"/></g>' % (
                    _f(x + w), _f(y), d["symbol"], _f(w), _f(h)))
            else:
                o.append('<use href="#%s" x="%s" y="%s" width="%s" height="%s"/>' % (d["symbol"], _f(x), _f(y), _f(w), _f(h)))
        elif k == "cartouche":
            o.append('<use href="#deco-cartouche" x="%s" y="%s" width="%s" height="%s"/>' % (_f(x), _f(y), _f(w), _f(h)))
            t = style["text"]
            o.append(_text(x + w / 2, y + h * 0.47, t["title"], "t-title", h * 0.2, extra=' font-weight="bold"'))
            o.append(_text(x + w / 2, y + h * 0.61, t["subtitle"], "t-latin", h * 0.075))
            o.append(_text(x + w / 2, y + h * 0.72, "原生 30 m 高程 · 显示每像素 %s m · %s km 见方" % (
                _f(res.grid_info["m_per_px"]), _f(res.map_size[0] * res.grid_info["m_per_px"] / 1000)), "t-body", h * 0.068))
        elif k == "compass":
            o.append(_text(x + w / 2, y + 30 * s, "N", "t-latin", 34 * s, extra=' font-weight="bold" font-style="normal"'))
            o.append('<use href="#deco-compass" x="%s" y="%s" width="%s" height="%s"/>' % (_f(x), _f(y + h - w), _f(w), _f(w)))
        elif k == "north":
            o.append(_text(x + w / 2, y + 32 * s, "北", "t-title", 34 * s))
            o.append('<use href="#east-north" x="%s" y="%s" width="%s" height="%s"/>' % (_f(x), _f(y + 36 * s), _f(w), _f(h - 36 * s)))
        elif k == "scale":
            o.extend(_scale_svg(d, res.scale, style, s, east))
        elif k == "legend":
            o.extend(_legend_svg(d, res, style, styles, s, east))
        elif k == "title_vertical":
            t = style["text"]
            o.append('<rect x="%s" y="%s" width="%s" height="%s" fill="#f3ecdc" fill-opacity=".92" stroke="%s" stroke-width="%s"/>' % (
                _f(x), _f(y), _f(w), _f(h), ink, _f(1.6 * s)))
            o.append('<rect x="%s" y="%s" width="%s" height="%s" fill="none" stroke="%s" stroke-width="%s"/>' % (
                _f(x + 6 * s), _f(y + 6 * s), _f(w - 12 * s), _f(h - 12 * s), ink, _f(0.7 * s)))
            fs = min((h - 70 * s) / max(1, len(t["title"])), w * 0.52)
            cx = x + w * 0.60
            for i, ch in enumerate(t["title"]):
                o.append(_text(cx, y + 40 * s + fs * (i + 0.85), ch, "t-title", fs * 0.92))
            fs2 = fs * 0.42
            for i, ch in enumerate(t["subtitle"]):
                o.append(_text(x + w * 0.2, y + 60 * s + fs2 * 1.05 * (i + 0.85), ch, "t-body", fs2))
        elif k == "seal":
            o.append('<use href="#east-seal" x="%s" y="%s" width="%s" height="%s"/>' % (_f(x), _f(y), _f(w), _f(h)))
            chars = style["text"]["seal"]
            fs = w * 0.32
            pos = ((0.68, 0.43), (0.68, 0.79), (0.32, 0.43), (0.32, 0.79))
            for ch, (px, py) in zip(chars, pos):
                o.append('<text x="%s" y="%s" font-size="%s" text-anchor="middle" style="font-family:%s;fill:#f6ead8" font-weight="bold">%s</text>' % (
                    _f(x + w * px), _f(y + h * py), _f(fs), html.escape(fonts["title"]), html.escape(ch)))
    o.extend(_frame_svg(res, style, s, east))
    o.append('</g>')
    o.append(_text(page_w / 2, page_h - m * 0.28, provenance_line, "t-coord", 13.5 * s))
    o.append('</svg></body></html>')
    return "\n".join(o)


# ---------------------------------------------------------------- icon specimen sheet

def paper_page(style, width, height, s=1.0):
    """Blank page in the style's paper colour + paper texture (uint8 RGB)."""
    page = np.empty((height, width, 3), dtype=np.float64)
    page[:] = hex_rgb(style["page"]["background"])
    cfg = dict(style["paper"], seed_name=style["paper"]["seed_name"] + "/icons")
    return np.clip(np.rint(_paper(page, cfg, s)), 0, 255).astype(np.uint8)


def _route_svg(kind_cfg, x0, x1, y, k):
    """One gently curving sample of a route line type, scaled by k."""
    L = x1 - x0
    d = "M%s %s C%s %s %s %s %s %s S%s %s %s %s" % tuple(_f(v) for v in (
        x0, y, x0 + L * .2, y - 14 * k, x0 + L * .35, y - 14 * k, x0 + L * .5, y, x0 + L * .85, y + 14 * k, x1, y))
    out = []
    cap = kind_cfg.get("linecap", "butt")
    if kind_cfg.get("casing"):
        out.append('<path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (d, kind_cfg["casing"], _f(kind_cfg["casing_width"] * k)))
    if kind_cfg.get("double"):
        out.append('<path d="%s" fill="none" stroke="%s" stroke-width="%s"/>' % (d, kind_cfg["edge"], _f(kind_cfg["casing_width"] * k)))
        out.append('<path d="%s" fill="none" stroke="%s" stroke-width="%s"/>' % (d, kind_cfg["casing"], _f((kind_cfg["casing_width"] - 2 * kind_cfg["edge_width"]) * k)))
    dash = kind_cfg.get("dash") or []
    da = ' stroke-dasharray="%s"' % " ".join(_f(v * k) for v in dash) if dash else ""
    if kind_cfg.get("taper"):
        # river: draw thin → thick in a few overlapping segments
        n = 6
        for i in range(n):
            t0, t1 = i / n, (i + 1) / n
            w = kind_cfg["width"] * k * (0.45 + 0.75 * t1)
            out.append('<path d="%s" fill="none" stroke="%s" stroke-width="%s" pathLength="1" stroke-dasharray="%s %s" stroke-dashoffset="%s" stroke-linecap="round"/>' % (
                d, kind_cfg["stroke"], _f(w), _f(t1 - t0 + 0.002), 2, _f(-t0)))
    else:
        out.append('<path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="%s"%s/>' % (d, kind_cfg["stroke"], _f(kind_cfg["width"] * k), cap, da))
    return out


def compose_icon_sheet(style_name, *, styles=None, manifest=None, art_dir=ART_DIR, base_href=None, width=1800):
    """HTML specimen of a style's icon sprite grouped as 城市 / [种族城镇] / 资源 / 道路线型与道路符号.

    Returns (html, (width, height)). Pure layout of symbols with names; nothing is placed on a map.
    """
    styles = styles or load_styles()
    manifest = manifest or load_manifest()
    style = styles["styles"][style_name]
    east = style.get("legend_language") == "east"
    ink = style["page"]["ink"]
    accent = style["page"]["accent"]
    fonts = style["fonts"]
    tier_names = style["towns"]["names"]
    res_names = {k: v for k, v in manifest["resources"]["kinds"].items()}
    res_names.update({k: v for k, v in manifest["resources"]["trade_kinds"].items() if k != "note"})
    base_kinds = list(manifest["resources"]["kinds"])
    trade_kinds = [k for k in manifest["resources"]["trade_kinds"] if k != "note"]
    mark_names = {"bridge": "桥", "ford": "渡口", "pass": "关隘", "port": "港口"}
    race_names = {k: v["name"] for k, v in manifest["towns"]["races"].items()}
    W, M = width, 70
    body = []
    y = 0.0

    def head(text, sub=None):
        nonlocal y
        y += 58
        body.append(_text(M, y, text, "t-title", 30, "start"))
        if sub:
            body.append(_text(M + 30 * len(text) + 24, y, sub, "t-note", 16, "start"))
        body.append('<path d="M%s %s H%s" stroke="%s" stroke-width="1.2"/>' % (M, _f(y + 12), W - M, ink))
        body.append('<path d="M%s %s H%s" stroke="%s" stroke-width=".6"/>' % (M, _f(y + 16), W - M, accent))
        y += 28

    def use(sid, x, yy, w, h):
        body.append('<use href="#%s" x="%s" y="%s" width="%s" height="%s"/>' % (sid, _f(x), _f(yy), _f(w), _f(h)))

    def grid(items, cols, cell_h, big, small_sizes, vb_h_ratio=1.0, label_size=19):
        nonlocal y
        cw = (W - 2 * M) / cols
        for i, (sid, name, sub) in enumerate(items):
            r, c = divmod(i, cols)
            cx = M + c * cw
            cy = y + r * cell_h
            bh = big * vb_h_ratio
            use(sid, cx + 10, cy + 8, big, bh)
            sx = cx + 10 + big + 10
            for ss in small_sizes:
                use(sid, sx, cy + 8 + bh - ss * vb_h_ratio, ss, ss * vb_h_ratio)
                sx += ss + 8
            body.append(_text(cx + 12, cy + bh + 36, name, "t-body", label_size, "start"))
            if sub:
                body.append(_text(cx + 12, cy + bh + 58, sub, "t-id", 13, "start"))
        rows = (len(items) + cols - 1) // cols
        y += rows * cell_h

    title = style.get("label", style_name)
    y = 40
    body.append(_text(W / 2, y + 40, "%s · 图示样张" % title, "t-title", 44))
    body.append(_text(W / 2, y + 74, "sprite：%s · 大图旁为 32 / 24 px 实尺小样 · 本样区无城镇/道路/资源数据，图示只在此展示，不摆到地图上" % style["icon_sprite"],
                      "t-note", 17))
    y += 90

    head("城市", "郡县制四级 · town-{tier}" if east else "四级 · town-{tier}")
    grid([("town-%s" % t, tier_names[t], "town-%s" % t) for t in TOWN_TIERS], 4, 196, 112, (32, 24))

    rt = style.get("race_towns") or {}
    if rt.get("enabled") and not east:
        head("种族城镇", "沿用 %s 的 town-{race}-{tier}（本轮不重画）；人类与未知种族用上方本风格城市" % rt["sprite"])
        items = []
        for race in rt["races"]:
            for t in TOWN_TIERS:
                items.append(("town-%s-%s" % (race, t), "%s·%s" % (race_names.get(race, race), tier_names[t]), None))
        grid(items, 8, 118, 64, (24,), label_size=17)
    elif rt.get("enabled"):
        y += 6
        body.append(_text(M, y + 18, "注：种族城镇可沿用西幻图示（%s 的 town-{race}-{tier}），属次要用途。" % rt["sprite"], "t-note", 17, "start"))
        y += 30

    head("资源", "res-{kind}，与 manifest.json 同名 · 前 16 种为基础资源，后 14 种为贸易品与奇物")
    grid([("res-%s" % k, res_names[k], "res-%s" % k) for k in base_kinds], 8, 150, 60, (28,), label_size=18)
    y += 6
    body.append('<path d="M%s %s H%s" stroke="%s" stroke-width=".6" stroke-dasharray="4 4"/>' % (M, _f(y), W - M, ink))
    y += 12
    grid([("res-%s" % k, res_names[k], "res-%s" % k) for k in trade_kinds], 8, 150, 60, (28,), label_size=18)

    head("道路线型", "routes.kinds · 按 1.6 倍参考像素绘制")
    kinds = style["routes"]["kinds"]
    colw = (W - 2 * M) / 2
    for i, rk in enumerate(ROUTE_KINDS):
        r, c = divmod(i, 2)
        x0 = M + c * colw
        yy = y + r * 74 + 34
        body.extend(_route_svg(kinds[rk], x0 + 10, x0 + 360, yy, 1.6))
        dash = kinds[rk].get("dash") or []
        desc = "%s · %s" % (kinds[rk]["name"], rk)
        body.append(_text(x0 + 390, yy + 7, desc, "t-body", 20, "start"))
        body.append(_text(x0 + 390, yy + 29, "宽 %s%s%s" % (_f(kinds[rk]["width"]), (" · 底边 %s" % _f(kinds[rk]["casing_width"])) if kinds[rk].get("casing") else "",
                                                           (" · 虚线 %s" % "/".join(_f(v) for v in dash)) if dash else ""), "t-id", 13, "start"))
    y += 3 * 74 + 10

    head("道路符号", "mark-{bridge|ford|pass|port}")
    grid([("mark-%s" % k, mark_names[k], "mark-%s" % k) for k in ROUTE_MARKS], 4, 170, 96, (32, 24))

    y += 20
    body.append(_text(W / 2, y + 10, "织梦 · %s · 本工程原创图示" % title, "t-note", 15))
    H = int(math.ceil(y + 50))
    extra = {}
    if rt.get("enabled") and not east:
        extra[rt["sprite"]] = ["town-%s-%s" % (race, t) for race in rt["races"] for t in TOWN_TIERS]
    st = dict(style, decoration_symbols={})
    sprites = style_sprites_svg(st, art_dir, extra)
    o = ['<!DOCTYPE html><html><head><meta charset="utf-8"><style>html,body{margin:0;padding:0;background:%s;overflow:hidden}'
         '.t-title{font-family:%s;fill:%s}.t-body{font-family:%s;fill:%s}.t-note{font-family:%s;fill:%s;opacity:.8}'
         '.t-id{font-family:Consolas,"Courier New",monospace;fill:%s;opacity:.6}</style></head><body>' % (
             style["page"]["background"], fonts["title"], ink, fonts["body"], ink, fonts["body"], ink, ink),
         sprites,
         '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" style="display:block">' % (W, H, W, H)]
    if base_href:
        o.append('<image href="%s" x="0" y="0" width="%d" height="%d"/>' % (html.escape(base_href), W, H))
    o.append('<rect x="22" y="22" width="%d" height="%d" fill="none" stroke="%s" stroke-width="2.4"/>' % (W - 44, H - 44, ink))
    o.append('<rect x="30" y="30" width="%d" height="%d" fill="none" stroke="%s" stroke-width=".8"/>' % (W - 60, H - 60, accent if east else ink))
    o.extend(body)
    o.append("</svg></body></html>")
    return "\n".join(o), (W, H)


__all__ = ["load_styles", "load_manifest", "resolve_town_symbol", "validate_towns", "layer_on", "compose_icon_sheet", "paper_page",
           "style_sprites_svg", "sprite_ids", "extract_symbols", "stable_seed", "display_grid", "base_colors", "hillshade", "scale_bar", "terrain_candidates",
           "place_symbols", "place_decorations", "render_map", "compose_html", "RenderResult", "ART_DIR", "STYLES_PATH"]
