# -*- coding: utf-8 -*-
"""Player-side map projection for one journey: link, fog whitelist, masked basemap.

Four rules this module exists to enforce:

1. **The server decides the map.** A journey's map comes from the story revision the
   journey is bound to (``story.mechanics.map``), never from a query parameter. No route
   here takes an import id, a coordinate, a layer or a size from the client.
2. **Fog is a whitelist, not a sticker.** Only places the journey has reached or borders
   are described, and only if the package does not mark them author-only or locked behind
   a flag the journey has not set. The basemap is rasterised server-side and every pixel
   outside a reveal circle is *painted* fog colour: hidden terrain is never in the bytes
   the player receives.
3. **Identity is pinned to bytes.** The link carries an import id; the record must be the
   one that id names (``sn_``/``mi_`` + content hash prefix) and the file on disk is
   re-hashed on every read. A swapped record with the same key is refused, not displayed.
4. **Nothing is invented.** An unlinked journey says so; a declared but unreadable import
   says so; a place without recorded ``coordinates`` gets ``lon/lat = null``. There is no
   fallback basemap and no second map engine — per-cell data still comes from
   :mod:`civ_atlas_snapshot` / :mod:`map_import`.

Read-only: ``projection()`` and ``basemap_png()`` never write a session, so a GET cannot
move ``state_version``. The only state kept by this module is a bounded in-memory cache of
encoded crop images, keyed by content hash.
"""
import hashlib
import math
import re

from . import civ_atlas_snapshot, map_import

#: Sphere radius, used only to turn the gameplay reveal radius (km) into degrees.
EARTH_RADIUS_KM = 6371.0088

DEFAULT_REVEAL_KM = 300.0
MIN_REVEAL_KM = 10.0
MAX_REVEAL_KM = 2000.0
#: A place merely known about reveals strictly less than one actually visited.
#: ``KNOWN_FRACTION * r <= r`` for every allowed r, so "heard of" is never wider than
#: "been there" — including at the minimum configured radius.
KNOWN_FRACTION = 0.5

#: Pixels outside every reveal circle. Terrain never reaches these bytes.
FOG_RGB = (17, 20, 24)

MAX_BASEMAP_WIDTH = 640
MIN_BASEMAP_WIDTH = 256
MIN_BASEMAP_HEIGHT = 96
MAX_BASEMAP_PIXELS = 240_000
#: Degrees of padding around the revealed area, so the patch is not flush to the edge.
BBOX_MARGIN = 0.25

#: Bounded image cache: how many encoded crops are kept, keyed by content hash.
CACHE_LIMIT = 8
_CACHE = {}

#: The only two id shapes the import adapters ever mint: ``sn_``/``mi_`` + hash prefix.
_IMPORT_ID = re.compile(r'^(?:sn|mi)_[0-9a-f]{6,32}$')
_BASIS_ID = re.compile(r'^wb_[0-9a-f]{8,32}$')

LINK_KIND = 'civ_atlas'
_LINK_KEYS = {'kind', 'import_id', 'world_basis_id', 'fog'}
_FOG_KEYS = {'reveal_radius_km'}

STATUS_OK = 'ok'
STATUS_NOT_LINKED = 'not_linked'
STATUS_MISSING = 'import_missing'
STATUS_UNREADABLE = 'import_unreadable'
STATUS_MISMATCH = 'import_mismatch'

STATUS_TEXT = {
    STATUS_NOT_LINKED: '这段旅程还没有关联 civ-atlas 地图',
    STATUS_MISSING: '关联的 civ-atlas 导入记录已不在（可能被清理了）',
    STATUS_UNREADABLE: '关联的 civ-atlas 原件读不出来（文件缺失或校验失败）',
    STATUS_MISMATCH: '关联的导入记录与它自己声明的内容哈希不一致，拒绝使用',
}


def _km_to_deg(km):
    return km / (math.pi * EARTH_RADIUS_KM / 180.0)


def _finite(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('%s 必须是数字' % label)
    if not math.isfinite(value):
        raise ValueError('%s 不能是 NaN 或无穷' % label)
    return float(value)


# --------------------------------------------------------------- the story link
def parse_link(story):
    """Normalise ``story.mechanics.map``, or ``None`` when the package declares none.

    Unknown keys are refused rather than ignored, so a typo cannot silently become "use
    the default", and a boolean or a string can never stand in for the radius. Only
    civ-atlas is accepted: this project has exactly one map basis.
    """
    mechanics = story.get('mechanics') or {}
    raw = mechanics.get('map')
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError('mechanics.map 必须是对象')
    extra = set(raw) - _LINK_KEYS
    if extra:
        raise ValueError('mechanics.map 有未知字段：%s' % '、'.join(sorted(extra)))
    kind = raw.get('kind')
    if kind != LINK_KIND:
        raise ValueError('mechanics.map.kind 只支持 %r（收到 %r）' % (LINK_KIND, kind))
    import_id = raw.get('import_id')
    if not isinstance(import_id, str) or not _IMPORT_ID.fullmatch(import_id):
        raise ValueError('mechanics.map.import_id 必须是 mi_/sn_ 开头的导入编号')
    basis_id = raw.get('world_basis_id')
    if basis_id is not None:
        if not isinstance(basis_id, str) or not _BASIS_ID.fullmatch(basis_id):
            raise ValueError('mechanics.map.world_basis_id 必须是 wb_… 编号或留空')
    fog = raw.get('fog') or {}
    if not isinstance(fog, dict):
        raise ValueError('mechanics.map.fog 必须是对象')
    extra = set(fog) - _FOG_KEYS
    if extra:
        raise ValueError('mechanics.map.fog 有未知字段：%s' % '、'.join(sorted(extra)))
    radius = _finite(fog.get('reveal_radius_km', DEFAULT_REVEAL_KM),
                     'mechanics.map.fog.reveal_radius_km')
    if not MIN_REVEAL_KM <= radius <= MAX_REVEAL_KM:
        raise ValueError('reveal_radius_km 必须在 %g…%g km 之间'
                         % (MIN_REVEAL_KM, MAX_REVEAL_KM))
    return {'kind': kind, 'import_id': import_id, 'world_basis_id': basis_id,
            'reveal_radius_km': radius}


def location_coordinates(place):
    """``(lon, lat)`` in [-180, 180) × [-90, 90], or ``None`` when not recorded.

    Longitude is normalised once here, so a place at 179.9 and one at −179.9 both land on
    the same frame the equirectangular basemap uses. Nothing is clamped or guessed.
    """
    coords = place.get('coordinates')
    if coords is None:
        return None
    if isinstance(coords, (str, bytes)) or not isinstance(coords, (list, tuple)):
        return None
    if len(coords) != 2:
        return None
    try:
        lon = _finite(coords[0], '经度')
        lat = _finite(coords[1], '纬度')
    except ValueError:
        return None
    if not -180.0 <= lon <= 180.0 or not -90.0 <= lat <= 90.0:
        return None
    return (((lon + 180.0) % 360.0) - 180.0, lat)


def validate_story_map(story):
    """Package-level check: the link, if present, is well formed, and so is every
    declared location coordinate.

    Wired into :meth:`app.runtime.Runtime.validate_package`, which means an imported
    package can no longer carry a malformed map link or a location whose coordinates do
    not project. A package that declares neither stays untouched.
    """
    link = parse_link(story)
    for place in story.get('locations') or []:
        if place.get('coordinates') is None:
            continue
        if location_coordinates(place) is None:
            raise ValueError('地点 %r 的 coordinates 不是合法的 [经度, 纬度]'
                             % place.get('id'))
    return link


# ------------------------------------------------------------ visibility rules
def known_radius_km(link):
    """Radius for a place merely known about. Always <= the visited radius."""
    radius = (link or {}).get('reveal_radius_km', DEFAULT_REVEAL_KM)
    return KNOWN_FRACTION * radius


def _place_withheld(place, session):
    """True when the package itself keeps this place out of the player projection.

    The location schema has no visibility flag, but an author can still mark a place
    author-only or tie it to a reveal flag; both are honoured here rather than being
    disclosed just because the place happens to be a neighbour.
    """
    if place.get('visibility') == 'author':
        return True
    flag = place.get('reveal_flag')
    if isinstance(flag, str) and flag and not (session.get('flags') or {}).get(flag):
        return True
    return False


def visible_places(session, story):
    """The three map states, and only for places this journey may name.

    Same starting set as :meth:`app.runtime.Runtime.surface` (current ∪ explored ∪ current
    neighbours) — so the map and the place list cannot disagree — then narrowed by
    :func:`_place_withheld`. Anything else is dropped entirely: no id, no name, no
    coordinates, and no count. Seeing a place on the map says nothing about being able to
    enter it; travel permission is still the engine's.
    """
    locations = story.get('locations') or []
    by_id = {place['id']: place for place in locations}
    current_id = session.get('location')
    current = by_id.get(current_id)
    explored = {pid for pid in (session.get('explored') or []) if pid in by_id}
    neighbours = set((current or {}).get('neighbors') or [])
    rows = []
    for place in locations:
        pid = place['id']
        if pid == current_id:
            state = 'current'
        elif pid in explored:
            state = 'explored'
        elif pid in neighbours:
            state = 'known'
        else:
            continue
        if _place_withheld(place, session):
            continue
        coords = location_coordinates(place)
        rows.append({'id': pid, 'name': place.get('name') or pid, 'state': state,
                     'lon': coords[0] if coords else None,
                     'lat': coords[1] if coords else None})
        if story.get('mechanics', {}).get('exploration') and place.get('town_id'):
            rows[-1]['town_id'] = place['town_id']
    order = {'current': 0, 'explored': 1, 'known': 2}
    rows.sort(key=lambda row: order[row['state']])   # stable: keeps package order
    return rows


def reveal_circles(places, link):
    """Gameplay reach around each visible place, in km. Not a line of sight."""
    radius = (link or {}).get('reveal_radius_km', DEFAULT_REVEAL_KM)
    known = known_radius_km(link)
    out = []
    for row in places:
        if row['lon'] is None or row['lat'] is None:
            continue
        out.append({'lon': row['lon'], 'lat': row['lat'],
                    'radius_km': radius if row['state'] in ('current', 'explored') else known,
                    'state': row['state']})
    return out


def bbox_for_circles(circles):
    """Tight lon/lat box around the reveal circles; never straddles ±180.

    A place near the date line gets a one-sided box (just its own side) rather than a box
    spanning the whole world, so the crop stays small and no wrap-around is implied. The
    far side of such a place is simply fogged — that limitation is reported in the JSON.
    """
    if not circles:
        return None
    lon_min = lat_min = 1e9
    lon_max = lat_max = -1e9
    clipped = False
    for circle in circles:
        lat = circle['lat']
        dlat = _km_to_deg(circle['radius_km'])
        cos_lat = max(0.02, math.cos(math.radians(max(-89.0, min(89.0, lat)))))
        dlon = dlat / cos_lat
        if circle['lon'] - dlon < -180.0 or circle['lon'] + dlon > 180.0:
            clipped = True
        lon_min = min(lon_min, circle['lon'] - dlon)
        lon_max = max(lon_max, circle['lon'] + dlon)
        lat_min = min(lat_min, lat - dlat)
        lat_max = max(lat_max, lat + dlat)
    pad_lon = (lon_max - lon_min) * BBOX_MARGIN
    pad_lat = (lat_max - lat_min) * BBOX_MARGIN
    lon_min, lon_max = max(-180.0, lon_min - pad_lon), min(180.0, lon_max + pad_lon)
    lat_min, lat_max = max(-84.0, lat_min - pad_lat), min(84.0, lat_max + pad_lat)
    if lon_max - lon_min < 1e-6 or lat_max - lat_min < 1e-6:
        return None
    box = (lon_min, lon_max, lat_min, lat_max)
    return box, clipped


# ------------------------------------------------------------ import resolution
def _record_pinned(record):
    """The record must be the one its own id names: ``sn_``/``mi_`` + content hash prefix."""
    identifier = str(record.get('id') or '')
    digest = str(record.get('sha256') or '')
    if identifier.startswith(('mi_', 'sn_')) and len(digest) == 64:
        return identifier[3:] == digest[:len(identifier) - 3]
    return False


def resolve(store, root, story):
    """Follow the link to the parsed world. Returns ``(status, context)``.

    ``context`` never carries the per-cell arrays to the caller of :func:`projection`:
    only :func:`basemap_png` reads them, and only inside the crop it is drawing.
    """
    link = parse_link(story)
    if link is None:
        return STATUS_NOT_LINKED, {'reason': STATUS_TEXT[STATUS_NOT_LINKED], 'link': None}
    record = store.get('map_import', link['import_id'])
    if not record:
        return STATUS_MISSING, {'reason': STATUS_TEXT[STATUS_MISSING], 'link': link}
    if not _record_pinned(record):
        return STATUS_MISMATCH, {'reason': STATUS_TEXT[STATUS_MISMATCH], 'link': link}
    try:
        if record.get('format') == civ_atlas_snapshot.FORMAT:
            world = civ_atlas_snapshot.load_world(root, record)   # re-hashes the file
            return STATUS_OK, {'link': link, 'record': record, 'world': world,
                               'heightmap': None}
        if record.get('format') == map_import.FORMAT:
            heightmap = map_import.load_heightmap(root, record)   # re-hashes the file
            return STATUS_OK, {'link': link, 'record': record, 'world': None,
                               'heightmap': heightmap}
    except (ValueError, OSError) as error:
        return STATUS_UNREADABLE, {'reason': STATUS_TEXT[STATUS_UNREADABLE],
                                   'detail': type(error).__name__, 'link': link}
    return STATUS_UNREADABLE, {'reason': STATUS_TEXT[STATUS_UNREADABLE],
                               'detail': 'unsupported_format', 'link': link}


def _source_summary(record, story):
    """What the player may see about the map's provenance.

    No import id, no file name, no path, no internal error text: the id is the author's
    handle for the record, and the player only needs a stable opaque identity plus the
    projection the drawing uses. The hash prefix is the same one embedded in that id, so
    it reveals nothing the record id did not already encode.
    """
    digest = str(record.get('sha256') or '')
    return {
        'map': 'civ_atlas',
        'world': story.get('title'),
        'opaque_id': hashlib.sha256(digest.encode('utf-8')).hexdigest()[:12] if digest else None,
        'format': ('snapshot' if record.get('format') == civ_atlas_snapshot.FORMAT
                   else 'heightmap'),
        'cells': record.get('pixels'),
        'note': '地图来自作者导出的 civ-atlas 世界；玩家侧只拿到已探索范围内的像素',
    }


# -------------------------------------------------------------- the projection
def projection(session, story, *, status, context, session_id):
    """The one JSON document the player map page reads."""
    places = visible_places(session, story)
    link = context.get('link') or parse_link(story)
    radius = (link or {}).get('reveal_radius_km', DEFAULT_REVEAL_KM)
    circles = reveal_circles(places, link)
    box = bbox_for_circles(circles) if status == STATUS_OK else None
    bbox, clipped = box if box else (None, False)
    player = next((row for row in places if row['state'] == 'current'), None)
    payload = {
        'status': status,
        'session': {'id': session_id, 'revision': session.get('revision')},
        'source': _source_summary(context['record'], story) if context.get('record') else None,
        'projection': {
            'scheme': 'equirectangular',
            'lon_range': [-180, 180], 'lat_range': [-90, 90],
            'x': '(lon + 180) / 360', 'y': '(90 - lat) / 180',
            'note': ('与 civ-atlas 逐格经纬度同一帧：倒三角与地标用同一公式定位。'
                     '经度已归一化到 [−180,180)，跨日界的地点只画一个点、不做对侧复制。'),
        },
        'player': ({'location_id': player['id'], 'name': player['name'],
                    'lon': player['lon'], 'lat': player['lat']} if player else None),
        'places': places,
        'fog': {
            'basis': 'gameplay_travel_reach',
            'reveal_radius_km': radius,
            'known_radius_km': known_radius_km(link),
            'masked_by': 'server',
            'note': ('可见范围是按玩法设定定的可达距离，不是真实视线，也不含地形遮蔽；'
                     '范围外的格子由服务器画成雾色，客户端拿不到那里的地形。'),
        },
        'basemap': {
            'available': bool(bbox),
            'url': ('/api/sessions/%s/play-map/basemap.png' % session_id) if bbox else None,
            'bbox': list(bbox) if bbox else None,
            'clipped_at_dateline': clipped,
            'note': ('底图只覆盖已知位置周围的裁切框；框外是雾，没有数据。'
                     if bbox else '还没有任何带经纬度的已知位置，所以没有底图可给'),
        },
        'notes': [],
    }
    if status != STATUS_OK:
        payload['reason'] = context.get('reason') or '地图不可用'
        payload['author_entry'] = {'page': 'map-tools',
                                   'label': '去世界地图工具关联 civ-atlas 数据'}
        payload['basemap']['note'] = '未关联 civ-atlas 数据时不提供底图，也不会自动接一张无关的地图'
    if status == STATUS_OK:
        if any(row['lon'] is None for row in places):
            payload['notes'].append('有地点没有记录经纬度，只列名字、不画标记（不伪造位置）')
        if not circles:
            payload['notes'].append('当前没有任何带经纬度的已知地点，底图暂不可用')
        if clipped:
            payload['notes'].append('已知位置靠近日界：只绘制了同侧范围，另一侧显示为雾')
    return payload


# ------------------------------------------------------------------- basemap
def _crop_dimensions(box):
    lon_min, lon_max, lat_min, lat_max = box
    lon_span = max(1e-6, lon_max - lon_min)
    lat_span = max(1e-6, lat_max - lat_min)
    width = int(round(lon_span * 24))
    width = max(MIN_BASEMAP_WIDTH, min(MAX_BASEMAP_WIDTH, width))
    height = max(MIN_BASEMAP_HEIGHT, int(round(width * lat_span / lon_span)))
    height = min(height, MAX_BASEMAP_WIDTH)
    if width * height > MAX_BASEMAP_PIXELS:
        scale = math.sqrt(MAX_BASEMAP_PIXELS / float(width * height))
        width = max(64, int(width * scale))
        height = max(48, int(height * scale))
    return width, height


def _blank_grid(width, height):
    size = width * height
    return {'width': width, 'height': height, 'land': [0] * size, 'water': [-1] * size,
            'cells': [0] * size, 'elevation': [0.0] * size, 'temperature': [0.0] * size,
            'precipitation': [0.0] * size, 'biome': [-1] * size}


def _grid_from_world(world, box, width, height):
    """Rasterise the import's own per-cell arrays into the crop box.

    Several cells can land in one pixel. Land wins over water and the *highest* land cell
    in a pixel is kept, so a coastline stays a coastline instead of dissolving into an
    average belonging to neither. Nothing is interpolated.
    """
    grid = _blank_grid(width, height)
    lon_min, lon_max, lat_min, lat_max = box
    span_lon = lon_max - lon_min
    span_lat = lat_max - lat_min
    for cell in range(world.cells):
        lon, lat = world.lon[cell], world.lat[cell]
        if not (lon_min <= lon <= lon_max and lat_min <= lat <= lat_max):
            continue
        x = min(width - 1, int((lon - lon_min) / span_lon * width))
        y = min(height - 1, int((lat_max - lat) / span_lat * height))
        index = y * width + x
        water = None if world.water is None else world.water[cell]
        elevation = None if world.elevation is None else world.elevation[cell]
        if water == 1 and grid['land'][index]:
            continue                       # an already-found land cell wins over sea
        grid['cells'][index] = 1
        if water is not None:
            grid['water'][index] = water
        if water != 1:
            grid['land'][index] = 1
            if elevation is not None and elevation > grid['elevation'][index]:
                grid['elevation'][index] = round(elevation, 1)
        if world.temperature is not None:
            grid['temperature'][index] = round(world.temperature[cell], 1)
        if world.precipitation is not None:
            grid['precipitation'][index] = round(world.precipitation[cell], 0)
        if world.biome is not None:
            grid['biome'][index] = world.biome[cell]
    return grid


def _grid_from_heightmap(heightmap, box, width, height):
    """Nearest-pixel read of a 16-bit heightmap. Sea/land uses the exporter's own test."""
    grid = _blank_grid(width, height)
    lon_min, lon_max, lat_min, lat_max = box
    span_lon = lon_max - lon_min
    span_lat = lat_max - lat_min
    gray = heightmap.gray
    source_w = heightmap.width
    source_h = heightmap.height
    for y in range(height):
        lat = lat_max - (y + 0.5) / height * span_lat
        row = min(source_h - 1, max(0, int((90.0 - lat) / 180.0 * source_h)))
        base = row * source_w
        for x in range(width):
            lon = lon_min + (x + 0.5) / width * span_lon
            col = int((lon + 180.0) / 360.0 * source_w) % source_w
            value = gray[base + col]
            index = y * width + x
            sea = heightmap.is_sea(value)
            grid['cells'][index] = 1
            grid['water'][index] = 1 if sea else 0
            if not sea:
                grid['land'][index] = 1
                grid['elevation'][index] = round(heightmap.elev_m(value), 1)
    return grid


def _mark_revealed(mask, circles, box, width, height):
    """Set ``mask`` true for pixels inside any reveal circle (great-circle distance)."""
    lon_min, lon_max, lat_min, lat_max = box
    span_lon = lon_max - lon_min
    span_lat = lat_max - lat_min
    px_per_deg_x = width / span_lon
    px_per_deg_y = height / span_lat
    for circle in circles:
        lon, lat, radius = circle['lon'], circle['lat'], circle['radius_km']
        dlat = _km_to_deg(radius)
        cos_lat = max(0.02, math.cos(math.radians(max(-89.0, min(89.0, lat)))))
        dlon = dlat / cos_lat
        x0 = max(0, int((lon - dlon - lon_min) * px_per_deg_x) - 1)
        x1 = min(width, int((lon + dlon - lon_min) * px_per_deg_x) + 2)
        y0 = max(0, int((lat_max - (lat + dlat)) * px_per_deg_y) - 1)
        y1 = min(height, int((lat_max - (lat - dlat)) * px_per_deg_y) + 2)
        if x0 >= x1 or y0 >= y1:
            continue
        rad_lat = math.radians(lat)
        sin_lat, cos_lat_c = math.sin(rad_lat), math.cos(rad_lat)
        for y in range(y0, y1):
            lat_p = lat_max - (y + 0.5) / height * span_lat
            rp = math.radians(lat_p)
            sin_p, cos_p = math.sin(rp), math.cos(rp)
            base = y * width
            for x in range(x0, x1):
                lon_p = lon_min + (x + 0.5) / width * span_lon
                cos_d = (sin_lat * sin_p + cos_lat_c * cos_p
                         * math.cos(math.radians(lon_p) - math.radians(lon)))
                cos_d = max(-1.0, min(1.0, cos_d))
                # Great-circle distance, not a lon/lat rectangle: a pixel in the corner of
                # the bounding box at high latitude must not be revealed by accident.
                if math.acos(cos_d) <= dlat + 1e-12:
                    mask[base + x] = 1


def _cache_key(record, box, width, height, circles):
    digest = str(record.get('sha256') or record.get('id'))
    shaped = '%.4f,%.4f,%.4f,%.4f' % box
    radii = ';'.join('%.4f,%.4f,%.2f' % (c['lon'], c['lat'], c['radius_km']) for c in circles)
    return hashlib.sha256(('%s|%s|%d,%d|%s' % (digest, shaped, width, height, radii))
                          .encode('utf-8')).hexdigest()


def _cache_put(key, value):
    if len(_CACHE) >= CACHE_LIMIT:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[key] = value


def clear_cache():
    """Tests and the app can drop the encoded crops; the cache holds no session state."""
    _CACHE.clear()


def basemap_png(context, places, link):
    """Return the fog-masked crop PNG, or ``None`` when there is nothing to draw.

    Colours come from :func:`civ_atlas_snapshot.preview_rgb` (the same code the author
    canvas uses), so what the player sees is the import's real values, coarsened. Every
    pixel outside a reveal circle is then overwritten with :data:`FOG_RGB` **before**
    encoding, so hidden terrain is never in the bytes the player receives.
    """
    circles = reveal_circles(places, link)
    boxed = bbox_for_circles(circles)
    if not boxed:
        return None
    box, _clipped = boxed
    width, height = _crop_dimensions(box)
    record = context.get('record') or {}
    key = _cache_key(record, box, width, height, circles)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    if context.get('world') is not None:
        grid = _grid_from_world(context['world'], box, width, height)
    elif context.get('heightmap') is not None:
        grid = _grid_from_heightmap(context['heightmap'], box, width, height)
    else:
        return None
    mask = bytearray(width * height)
    _mark_revealed(mask, circles, box, width, height)
    out = bytearray(civ_atlas_snapshot.preview_rgb(grid, 'elevation'))
    fog = bytes(FOG_RGB)
    for index in range(width * height):
        if not mask[index]:
            base = index * 3
            out[base:base + 3] = fog
    png = map_import.encode_rgb_preview(bytes(out), width, height)
    _cache_put(key, png)
    return png
