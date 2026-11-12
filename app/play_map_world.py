# -*- coding: utf-8 -*-
"""Planar metre-space player basemap for ``mechanics.map.kind = world_map_product``.

Loads a frozen ``terragenesis-fast-relief-v1`` directory through ``map_source``, crops in
metres, paints a simple elevation ramp, and fog-masks with planar (Euclidean) reach.
This is the **default** player map path (:mod:`app.map_policy`); civ-atlas is opt-in.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

import numpy as np

from . import fog_art, map_import
from .map_source import load_source
from .map_source.cache import ProductCache

KIND = 'world_map_product'
SCHEME = 'planar_metres'
ALLOWED_ROOT_PARTS = ('artifacts', 'fast-world')
MAX_CROP_CELLS = 4_000_000
PRODUCT_CACHE_CAPACITY = 8

# 玩家地图每个请求都会 resolve_product，而完整 ``load_source`` 要把每一层重新 SHA-256、还要与绑定的过程
# 数组逐元素对比——真正重复付出的是校验。首次加载仍是一次完整校验；后续请求复用那次校验的结果，只用
# 目录快照（文件集合 + 每文件 stat）判断它是否还是当前产品。失败不入缓存；含符号链接/junction 的产品不
# 复用；``registry.load_source`` 的默认全量校验一个字都没改。
_PRODUCT_CACHE = ProductCache(PRODUCT_CACHE_CAPACITY)


def clear_source_cache():
    """Drop cached products (tests, and anything that rewrites a product in place)."""
    _PRODUCT_CACHE.clear()


# 旧叫法的别名：缓存的是 map_source source，名字以 clear_source_cache 为准。
clear_product_cache = clear_source_cache


def parse_world_link(raw):
    keys = {'kind', 'product_path', 'product_identity', 'spacing_m', 'fog', 'worldgen_job_id'}
    extra = set(raw) - keys
    if extra:
        raise ValueError('mechanics.map 有未知字段：%s' % '、'.join(sorted(extra)))
    path = raw.get('product_path')
    if not isinstance(path, str) or not path.strip() or '..' in Path(path).parts:
        raise ValueError('mechanics.map.product_path 必须是相对路径且不得含 ..')
    identity = raw.get('product_identity')
    if not isinstance(identity, str) or len(identity) < 16:
        raise ValueError('mechanics.map.product_identity 必须是产品身份哈希')
    spacing = raw.get('spacing_m')
    if spacing is not None:
        if isinstance(spacing, bool) or not isinstance(spacing, (int, float)) or not math.isfinite(spacing) or spacing <= 0:
            raise ValueError('mechanics.map.spacing_m 必须是正数')
        spacing = float(spacing)
    fog = raw.get('fog') or {}
    if not isinstance(fog, dict):
        raise ValueError('mechanics.map.fog 必须是对象')
    if set(fog) - {'reveal_radius_km'}:
        raise ValueError('mechanics.map.fog 有未知字段：%s' % '、'.join(sorted(set(fog) - {'reveal_radius_km'})))
    from . import play_map as pm
    radius = pm._finite(fog.get('reveal_radius_km', pm.DEFAULT_REVEAL_KM), 'mechanics.map.fog.reveal_radius_km')
    if not pm.MIN_REVEAL_KM <= radius <= pm.MAX_REVEAL_KM:
        raise ValueError('reveal_radius_km 必须在 %g…%g km 之间' % (pm.MIN_REVEAL_KM, pm.MAX_REVEAL_KM))
    job_id = raw.get('worldgen_job_id')
    if job_id is not None and (not isinstance(job_id, str) or not job_id):
        raise ValueError('mechanics.map.worldgen_job_id 无效')
    return dict(kind=KIND, product_path=path.replace('\\', '/'), product_identity=identity,
                spacing_m=spacing, reveal_radius_km=radius, worldgen_job_id=job_id)


def resolve_product(repo_root, link):
    root = Path(repo_root).resolve()
    target = (root / link['product_path']).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError('product_path 超出仓库根') from exc
    if not any(part in target.parts for part in ('artifacts', 'fast-world')):
        raise ValueError('product_path 必须位于 artifacts 下的世界层产物')
    if not (target / 'manifest.json').is_file():
        raise FileNotFoundError('缺少 manifest.json')
    # ``load_source`` 以模块全局传入：命中时不再哈希任何文件，测试 monkeypatch 也照旧生效。
    src = _PRODUCT_CACHE.load(target, kind='world-map-product',
                              expected_identity=link['product_identity'], loader=load_source)
    spacing = float(src.info.spacing_m)
    if link.get('spacing_m') is not None and abs(link['spacing_m'] - spacing) > 1e-6:
        raise ValueError('spacing_m 与产品不一致')
    return src, target


def location_xz(place):
    """Finite metre coordinates stored in the lon/lat slots for planar packages."""
    coords = place.get('coordinates')
    if coords is None or isinstance(coords, (str, bytes)) or not isinstance(coords, (list, tuple)):
        return None
    if len(coords) != 2:
        return None
    try:
        x = float(coords[0]); z = float(coords[1])
    except (TypeError, ValueError):
        return None
    if not math.isfinite(x) or not math.isfinite(z):
        return None
    return x, z


def bbox_planar(circles, margin=0.25):
    if not circles:
        return None
    x0 = z0 = 1e30
    x1 = z1 = -1e30
    for c in circles:
        r = c['radius_km'] * 1000.0
        x0 = min(x0, c['lon'] - r); x1 = max(x1, c['lon'] + r)
        z0 = min(z0, c['lat'] - r); z1 = max(z1, c['lat'] + r)
    pad_x = (x1 - x0) * margin; pad_z = (z1 - z0) * margin
    box = (x0 - pad_x, x1 + pad_x, z0 - pad_z, z1 + pad_z)
    if box[1] - box[0] < 1.0 or box[3] - box[2] < 1.0:
        return None
    return box, False


def _hypsometric_rgb(elev, status):
    """Simple land/sea colouring for the journey crop (not the author atlas)."""
    h, w = elev.shape
    out = np.empty((h, w, 3), dtype=np.uint8)
    ocean = status == 3
    closed = status == 4
    land = ~(ocean | closed)
    out[ocean] = (40, 90, 140)
    out[closed] = (70, 110, 150)
    e = np.nan_to_num(elev, nan=0.0)
    t = np.clip(e / 4000.0, 0.0, 1.0)
    out[land, 0] = (60 + 140 * t[land]).astype(np.uint8)
    out[land, 1] = (110 + 80 * (1.0 - t[land])).astype(np.uint8)
    out[land, 2] = (50 + 40 * t[land]).astype(np.uint8)
    return out


def _mark_planar(mask, circles, box, width, height):
    x_min, x_max, z_min, z_max = box
    sx = (x_max - x_min) / width
    sz = (z_max - z_min) / height
    for c in circles:
        cx, cz, r_m = c['lon'], c['lat'], c['radius_km'] * 1000.0
        r2 = r_m * r_m
        ix0 = max(0, int((cx - r_m - x_min) / sx) - 1)
        ix1 = min(width, int((cx + r_m - x_min) / sx) + 2)
        iz0 = max(0, int((cz - r_m - z_min) / sz) - 1)
        iz1 = min(height, int((cz + r_m - z_min) / sz) + 2)
        for iz in range(iz0, iz1):
            z = z_min + (iz + 0.5) * sz
            base = iz * width
            for ix in range(ix0, ix1):
                x = x_min + (ix + 0.5) * sx
                if (x - cx) ** 2 + (z - cz) ** 2 <= r2:
                    mask[base + ix] = 1


def _draw_rivers(rgb, rivers, box, width, height):
    """Stroke river polylines (metres) onto the crop; fog layer still wins outside reveals."""
    if not rivers:
        return
    x_min, x_max, z_min, z_max = box
    sx = (x_max - x_min) / max(width, 1)
    sz = (z_max - z_min) / max(height, 1)
    colour = np.asarray((30, 70, 130), dtype=np.uint8)
    for line in rivers:
        pts = np.asarray(line.get('points_xz_m') or (), dtype=float)
        if pts.ndim != 2 or pts.shape[0] < 2 or pts.shape[1] != 2:
            continue
        for i in range(len(pts) - 1):
            x0, z0 = pts[i]; x1, z1 = pts[i + 1]
            steps = max(2, int(max(abs(x1 - x0), abs(z1 - z0)) / max(min(sx, sz), 1.0)))
            for t in range(steps + 1):
                u = t / steps
                x = x0 + (x1 - x0) * u
                z = z0 + (z1 - z0) * u
                ix = int((x - x_min) / sx)
                iz = int((z - z_min) / sz)
                if 0 <= ix < width and 0 <= iz < height:
                    rgb[iz, ix] = colour
                    if ix + 1 < width:
                        rgb[iz, ix + 1] = colour
                    if iz + 1 < height:
                        rgb[iz + 1, ix] = colour


def basemap_png(source, places, link, clues=None, *, cache, cache_put, crop_dimensions):
    from . import map_clues
    from . import play_map as pm
    circles = pm.reveal_circles(places, link)
    boxed = bbox_planar(circles + map_clues.frame_circles(clues or []))
    if not boxed:
        return None
    box, _ = boxed
    width, height = crop_dimensions(box)
    key = hashlib.sha256(
        ('%s|%.1f,%.1f,%.1f,%.1f|%d,%d|%s|rivers' % (
            link['product_identity'], *box, width, height,
            ';'.join('%.1f,%.1f,%.2f' % (c['lon'], c['lat'], c['radius_km']) for c in circles))
         ).encode('utf-8')).hexdigest()
    hit = cache.get(key)
    if hit is not None:
        return hit
    x0, x1, z0, z1 = box
    # map_source crop is half-open; pad one spacing so the frame is covered
    spacing = float(source.info.spacing_m)
    cropped = source.crop(x0, z0, x1 + spacing * 0.5, z1 + spacing * 0.5, max_cells=MAX_CROP_CELLS)
    elev = np.asarray(cropped['elevation_m'], dtype=np.float32)
    status = np.asarray(cropped['status'], dtype=np.uint8)
    # resample crop to requested PNG size
    zh, xw = elev.shape
    yy = (np.arange(height) + 0.5) / height * (zh - 1)
    xx = (np.arange(width) + 0.5) / width * (xw - 1)
    yi = np.clip(np.rint(yy).astype(int), 0, zh - 1)
    xi = np.clip(np.rint(xx).astype(int), 0, xw - 1)
    elev_i = elev[yi][:, xi]
    status_i = status[yi][:, xi]
    terrain = _hypsometric_rgb(elev_i, status_i)
    try:
        rivers = source.vectors('rivers') if 'rivers' in (source.info.vectors or ()) else []
    except Exception:
        rivers = []
    _draw_rivers(terrain, rivers, box, width, height)
    mask = bytearray(width * height)
    _mark_planar(mask, circles, box, width, height)
    fog = np.broadcast_to(np.asarray(fog_art.FOG_RGB, dtype=np.uint8), (height, width, 3)).copy()
    outside = np.frombuffer(bytes(mask), dtype=np.uint8).reshape(height, width) == 0
    terrain[outside] = fog[outside]
    png = map_import.encode_rgb_preview(terrain.tobytes(), width, height)
    cache_put(key, png)
    return png


def source_summary(link, story, source):
    return {
        'map': KIND,
        'world': story.get('title'),
        'opaque_id': link['product_identity'][:12],
        'format': 'terragenesis-fast-relief',
        'spacing_m': float(source.info.spacing_m),
        'shape_zx': list(source.info.shape_zx),
        'note': '地图来自作者生成的快速世界层；玩家侧只拿到已探索范围内的像素',
    }
