# -*- coding: utf-8 -*-
"""Server side of the player-map fog: the *safety* half only.

The painted look lives in the browser (``app/static/map-fog.js``), drawn at screen
resolution on a canvas over the basemap. This module decides, from geometry alone, which
basemap pixels may carry terrain and what every other pixel is:

* **Fog pixels carry no terrain.** Outside the revealed area every pixel is the single
  constant :data:`FOG_RGB` (a parchment wash the canvas paints over). It is not even a
  function of position, so swapping the hidden terrain cannot change one fogged byte.
* **Nothing beyond the gameplay radius is revealed.** Each reveal disc has a rough edge
  (:func:`edge_profile`): its radius at any bearing is between ``EDGE_MIN`` and
  ``EDGE_MAX`` (< 1) times the configured radius, so the rough edge only ever pulls the
  visible area *inwards*. The same profile is sent to the client in the projection JSON
  (``fog.reveal[*].edge``), so the canvas fog opens exactly the same, or a smaller, area.
* **Deterministic.** Same frame + same circles = same bytes (the PNG is cached by key).
"""
import math

import numpy as np

#: The visible disc is at least / at most this share of the configured radius.
EDGE_MIN = 0.80
EDGE_MAX = 0.97
#: Samples of the rough edge around a disc (bearing 0 = east, counter-clockwise).
EDGE_SAMPLES = 64
#: Inside this share of the effective radius terrain is shown untouched (server fallback
#: for clients without canvas; the canvas paints its own softer edge on top).
CLEAR_FRACTION = 0.93

#: The one colour of every fogged basemap pixel: the mean tone of the painted fog.
FOG_RGB = (198, 186, 160)


def _smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _mix32(*values):
    """Small 32-bit integer hash (same recipe as ``mix32`` in map-fog.js)."""
    h = 0x9E3779B9
    for v in values:
        h ^= v & 0xFFFFFFFF
        h = (h * 0x85EBCA6B) & 0xFFFFFFFF
        h ^= h >> 13
        h = (h * 0xC2B2AE35) & 0xFFFFFFFF
        h ^= h >> 16
    return h


# ------------------------------------------------------------ geometry
def pixel_grid(box, width, height):
    """Longitude / latitude of every pixel centre, as two (height, width) arrays."""
    lon_min, lon_max, lat_min, lat_max = box
    xs = lon_min + (np.arange(width, dtype=np.float64) + 0.5) / width * (lon_max - lon_min)
    ys = lat_max - (np.arange(height, dtype=np.float64) + 0.5) / height * (lat_max - lat_min)
    return np.meshgrid(xs, ys)


def edge_profile(lon, lat):
    """Radius fraction of the rough reveal edge at ``EDGE_SAMPLES`` bearings.

    A few low harmonics with phases and weights hashed from the centre (rounded to
    0.001°), so every place gets its own outline: a rough circle, never a perfect one,
    never a star. Values are rounded to 0.001 so the JSON copy is exactly what the
    server uses. All values lie in ``[EDGE_MIN, EDGE_MAX]``.
    """
    key = (int(round((lon + 180.0) * 1000)), int(round((lat + 90.0) * 1000)))
    rnd = [_mix32(key[0], key[1], salt) / 4294967296.0 for salt in range(1, 9)]
    harmonics = [(2, 0.30 + 0.25 * rnd[0], rnd[1]), (3, 0.30 + 0.20 * rnd[2], rnd[3]),
                 (5, 0.16 + 0.10 * rnd[4], rnd[5]), (7, 0.08 + 0.06 * rnd[6], rnd[7])]
    raw = []
    for k in range(EDGE_SAMPLES):
        b = 2.0 * math.pi * k / EDGE_SAMPLES
        raw.append(sum(w * math.sin(n * b + 2.0 * math.pi * p) for n, w, p in harmonics))
    lo, hi = min(raw), max(raw)
    span = (hi - lo) or 1.0
    return [round(EDGE_MIN + (EDGE_MAX - EDGE_MIN) * (v - lo) / span, 3) for v in raw]


def _edge_at(profile, bearing):
    """Linear interpolation of ``profile`` at ``bearing`` (radians, any range)."""
    prof = np.asarray(profile, dtype=np.float64)
    t = np.mod(bearing, 2.0 * math.pi) / (2.0 * math.pi) * len(prof)
    i0 = np.floor(t).astype(np.int64) % len(prof)
    i1 = (i0 + 1) % len(prof)
    f = t - np.floor(t)
    return prof[i0] * (1.0 - f) + prof[i1] * f


def cloud_deg(circles, earth_radius_km):
    """Cloud size for this journey in degrees: tied to the configured reach, not the crop."""
    if not circles:
        return 1.0
    r = max(c['radius_km'] for c in circles)
    return round(max(0.05, math.degrees(r / earth_radius_km) * 0.9), 4)


def reveal_shapes(circles):
    """The rough discs as sent to the client: centre, radius and edge profile."""
    return [{'lon': c['lon'], 'lat': c['lat'], 'radius_km': c['radius_km'],
             'edge': edge_profile(c['lon'], c['lat'])} for c in circles]


def reveal_ratio(lon, lat, circles, earth_radius_km):
    """Per pixel: smallest ``distance / effective_radius`` over all circles (inf if none).

    ``< 1`` means inside a reveal disc. Distance is great-circle; the bearing is taken in
    the map's own (cos-latitude scaled) frame, the same formula map-fog.js uses.
    """
    ratio = np.full(lon.shape, np.inf, dtype=np.float64)
    if not circles:
        return ratio
    lat_r, lon_r = np.radians(lat), np.radians(lon)
    sin_p, cos_p = np.sin(lat_r), np.cos(lat_r)
    for circle in circles:
        clat, clon = math.radians(circle['lat']), math.radians(circle['lon'])
        cos_d = np.clip(math.sin(clat) * sin_p + math.cos(clat) * cos_p
                        * np.cos(lon_r - clon), -1.0, 1.0)
        dist = np.arccos(cos_d) * earth_radius_km
        bearing = np.arctan2(lat - circle['lat'],
                             (lon - circle['lon']) * max(0.02, math.cos(clat)))
        profile = circle.get('edge') or edge_profile(circle['lon'], circle['lat'])
        r_eff = circle['radius_km'] * _edge_at(profile, bearing)
        np.minimum(ratio, dist / np.maximum(r_eff, 1e-6), out=ratio)
    return ratio


# --------------------------------------------------------------- the bytes
def fog_layer(box, width, height, ratio=None, scale=1.0):
    """Every fogged pixel's colour: one constant, no position, no terrain."""
    del box, ratio, scale
    out = np.empty((height, width, 3), dtype=np.uint8)
    out[...] = FOG_RGB
    return out


def reference(box, width, height, circles, earth_radius_km):
    """What every fogged pixel of this frame must equal (tests compare against it)."""
    lon, lat = pixel_grid(box, width, height)
    ratio = reveal_ratio(lon, lat, circles, earth_radius_km)
    return fog_layer(box, width, height), ratio


def compose(terrain_rgb, box, width, height, circles, earth_radius_km, fog=None):
    """Terrain inside the rough discs, the fog colour everywhere else; RGB bytes.

    Pixels at ``ratio >= 1`` are replaced by the fog colour outright. Only the thin band
    just *inside* a disc fades terrain toward the fog colour (a fallback edge for
    clients that do not paint the canvas fog).
    """
    terrain = np.frombuffer(bytes(terrain_rgb), dtype=np.uint8).reshape(height, width, 3)
    fog_u8, ratio = fog if fog is not None else reference(box, width, height, circles,
                                                          earth_radius_km)
    alpha = _smoothstep(CLEAR_FRACTION, 1.0, ratio) * 0.6
    out = terrain.astype(np.float32) * (1.0 - alpha[..., None]) \
        + fog_u8.astype(np.float32) * alpha[..., None]
    out = np.where((ratio >= 1.0)[..., None], fog_u8, np.clip(out, 0, 255).astype(np.uint8))
    return out.astype(np.uint8).tobytes(), ratio
