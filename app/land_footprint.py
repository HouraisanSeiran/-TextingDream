# -*- coding: utf-8 -*-
"""Settlement footprint and sparse land-use polygons (validation only, no IO).

Three layers, kept apart on purpose (see ``docs/town-space-and-land-use.md``):

1. **environment sampling** — climate/terrain of a region; never becomes arable area;
2. **settlement footprint** — where the buildings are, drawn by the author as a lon/lat
   polygon; **never** fed into ``TownInput.terrain.area_km2``, because the town rules
   treat that field as *farmland*, not as built-up land;
3. **land-use polygons** — optional and **sparse**: farmland, mine, explicitly declared
   wasteland, forest, pasture. Land nobody planned stays ``unplanned`` — it is *not*
   silently treated as wasteland, and nothing outside the footprint is assumed to be
   farmland.

A mine polygon only records an *intent*: it never yields a surveyed deposit, never an
extractable amount and never a stock. Farmland is a declared use, not instant harvest.

Everything here is pure computation: no file access, no model calls, no clock.
"""
import math

#: Hard bounds. Generous but finite: a footprint is a building cluster, not a province.
MAX_VERTICES = 4096
MIN_VERTICES = 3
MAX_FOOTPRINT_KM2 = 50.0
MAX_LANDUSE_KM2 = 20000.0
MAX_LAND_USE_ITEMS = 64

LAND_USE_KINDS = ('farmland', 'pasture', 'mine', 'forest', 'wasteland', 'other')
#: 只有农田能进现有粮食公式（GRAIN_YIELD_T_PER_KM2_YEAR 是谷物单产）。
#: 牧场不参与：牧草不能直接按谷物折算，需要单独的生产模型。
GRAIN_KINDS = ('farmland',)
#: 列出来是为了不让它们被默默当成粮食；目前不参与任何产出计算。
DEFERRED_PRODUCTIVE_KINDS = ('pasture',)


class FootprintError(ValueError):
    """A refused polygon or land-use list. One sentence, no partial result."""


def _finite(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise FootprintError('%s 必须是数字' % label)
    if not math.isfinite(value):
        raise FootprintError('%s 不能是 NaN 或无穷' % label)
    return float(value)


def parse_vertices(vertices, *, label='多边形', min_vertices=MIN_VERTICES):
    """Validate a closed lon/lat ring. Returns ``[(lon, lat), ...]`` without repetition."""
    if not isinstance(vertices, (list, tuple)):
        raise FootprintError('%s 的顶点必须是数组' % label)
    if len(vertices) < min_vertices:
        raise FootprintError('%s 至少要 %d 个顶点（收到 %d）'
                             % (label, min_vertices, len(vertices)))
    if len(vertices) > MAX_VERTICES:
        raise FootprintError('%s 的顶点过多（上限 %d）' % (label, MAX_VERTICES))
    out = []
    for index, pair in enumerate(vertices):
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise FootprintError('%s 第 %d 个顶点不是 [经度, 纬度]' % (label, index))
        lon = _finite(pair[0], '%s 第 %d 个经度' % (label, index))
        lat = _finite(pair[1], '%s 第 %d 个纬度' % (label, index))
        if not -180.0 <= lon <= 180.0:
            raise FootprintError('%s 第 %d 个经度 %r 超出 −180…180' % (label, index, lon))
        if not -90.0 <= lat <= 90.0:
            raise FootprintError('%s 第 %d 个纬度 %r 超出 −90…90' % (label, index, lat))
        out.append((lon, lat))
    # 首尾重复视为闭合，去掉末尾重复点
    if len(out) > 1 and out[0] == out[-1]:
        out.pop()
    if len(out) < min_vertices:
        raise FootprintError('%s 去掉重复闭合点后不足 %d 个顶点' % (label, min_vertices))
    if len(set(out)) != len(out):
        raise FootprintError('%s 里有重复顶点' % label)
    return out


def _unwrap_longitudes(ring):
    """Make a ring that crosses ±180 continuous, so area/self-intersection make sense.

    A ring given as 179, -179 is really a 2° step across the date line, not a 358° one.
    """
    out = [ring[0]]
    for lon, lat in ring[1:]:
        prev = out[-1][0]
        while lon - prev > 180.0:
            lon -= 360.0
        while lon - prev < -180.0:
            lon += 360.0
        out.append((lon, lat))
    return out


def _planar_area(ring):
    """Signed area in squared degrees (shoelace)."""
    total = 0.0
    for i in range(len(ring)):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % len(ring)]
        total += x1 * y2 - x2 * y1
    return total / 2.0


def _segments_cross(p1, p2, p3, p4):
    def orient(a, b, c):
        value = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if abs(value) < 1e-12:
            return 0
        return 1 if value > 0 else -1
    o1, o2 = orient(p1, p2, p3), orient(p1, p2, p4)
    o3, o4 = orient(p3, p4, p1), orient(p3, p4, p2)
    return o1 != o2 and o3 != o4


def is_self_intersecting(ring):
    """True when a non-adjacent pair of edges crosses."""
    count = len(ring)
    if count < 4:
        return False
    for i in range(count):
        a1, a2 = ring[i], ring[(i + 1) % count]
        for j in range(i + 1, count):
            if j == i or (j + 1) % count == i or (i + 1) % count == j:
                continue
            b1, b2 = ring[j], ring[(j + 1) % count]
            if _segments_cross(a1, a2, b1, b2):
                return True
    return False


def polygon_area_km2(ring, radius_km=6371.0088):
    """Approximate spherical area of a small ring, in km².

    Uses the shoelace area on an equirectangular projection scaled by cos(latitude) — good
    for town-sized polygons, and it says "approximate" rather than pretending to be exact.
    Date-line crossing is handled by unwrapping longitudes first.
    """
    ring = _unwrap_longitudes(list(ring))
    mean_lat = sum(lat for _, lat in ring) / len(ring)
    cos_lat = max(1e-6, math.cos(math.radians(mean_lat)))
    deg_area = abs(_planar_area(ring))
    km_per_deg_lat = math.pi * radius_km / 180.0
    km_per_deg_lon = km_per_deg_lat * cos_lat
    return deg_area * km_per_deg_lat * km_per_deg_lon


class Polygon:
    """A validated ring plus the facts worth reporting about it."""

    __slots__ = ('name', 'vertices', 'area_km2', 'crosses_date_line')

    def __init__(self, name, vertices, area_km2, crosses_date_line):
        self.name = name
        self.vertices = vertices
        self.area_km2 = area_km2
        self.crosses_date_line = crosses_date_line

    def as_dict(self):
        return {'name': self.name, 'vertices': [list(p) for p in self.vertices],
                'area_km2': round(self.area_km2, 4),
                'area_is_approximate': True,
                'crosses_date_line': self.crosses_date_line}


def parse_polygon(vertices, *, name='多边形', max_area_km2=MAX_FOOTPRINT_KM2,
                  radius_km=6371.0088, min_vertices=MIN_VERTICES):
    ring = parse_vertices(vertices, label=name, min_vertices=min_vertices)
    unwrapped = _unwrap_longitudes(ring)
    if is_self_intersecting(unwrapped):
        raise FootprintError('%s 的边自交了，请按顺序圈一个不自交的范围' % name)
    area = polygon_area_km2(ring, radius_km)
    if area <= 0.0:
        raise FootprintError('%s 的面积是 0，请圈出一个有范围的多边形' % name)
    if area > max_area_km2:
        raise FootprintError('%s 面积约 %.1f km²，超过 %s 允许的 %.1f km²'
                             % (name, area, name, max_area_km2))
    crosses = any(abs(abs(lon) - 180.0) < 1e-9 for lon, _ in ring) or \
        max(lon for lon, _ in ring) - min(lon for lon, _ in ring) > 180.0
    return Polygon(name, ring, area, crosses)


def parse_footprint(vertices, *, max_area_km2=MAX_FOOTPRINT_KM2, radius_km=6371.0088):
    """The settlement's built-up area. Never used as farmland."""
    poly = parse_polygon(vertices, name='建筑范围', max_area_km2=max_area_km2,
                         radius_km=radius_km)
    return {
        'vertices': [list(p) for p in poly.vertices],
        'area_km2': round(poly.area_km2, 4),
        'area_is_approximate': True,
        'crosses_date_line': poly.crosses_date_line,
        # 底图是粗网格，这里的边界是作者规划出来的，不是测量出来的
        'boundary_source': 'author_planned_boundary',
        'terrain_detail': 'coarse_mesh_reference_only',
        'unknown': ['精细道路走向', '微观地形（单格约 14959 km² 远大于城镇）'],
    }


def parse_land_use(items, *, radius_km=6371.0088, max_items=MAX_LAND_USE_ITEMS):
    """Optional, sparse land-use polygons. Nothing outside them is assumed anything."""
    if items is None:
        items = []
    if not isinstance(items, (list, tuple)):
        raise FootprintError('用地规划必须是数组')
    if len(items) > max_items:
        raise FootprintError('用地规划条数过多（上限 %d）' % max_items)
    parsed = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise FootprintError('第 %d 条用地规划不是对象' % index)
        extra = set(item) - {'kind', 'vertices', 'note', 'surveyed'}
        if extra:
            raise FootprintError('第 %d 条用地规划有未知字段：%s'
                                 % (index, '、'.join(sorted(extra))))
        kind = item.get('kind')
        if kind not in LAND_USE_KINDS:
            raise FootprintError('第 %d 条用地规划的类型 %r 不认识（可选 %s）'
                                 % (index, kind, '、'.join(LAND_USE_KINDS)))
        label = '用地规划#%d（%s）' % (index, kind)
        poly = parse_polygon(item.get('vertices'), name=label,
                             max_area_km2=MAX_LANDUSE_KM2, radius_km=radius_km)
        note = str(item.get('note') or '')[:300]
        entry = {
            'kind': kind,
            'vertices': [list(p) for p in poly.vertices],
            'area_km2': round(poly.area_km2, 4),
            'note': note,
            # 矿山只表达意图：不产生已勘探、可采、库存
            'productive_now': False,
        }
        if kind == 'mine':
            entry['surveyed'] = False
            entry['note_supply'] = '仅规划意图：不是已勘探矿藏，不产生可采量或库存'
        elif kind in GRAIN_KINDS:
            entry['note_supply'] = '已声明的农田；仍需通过城镇粮食/人口规则才产出'
        elif kind in DEFERRED_PRODUCTIVE_KINDS:
            entry['note_supply'] = ('已声明的牧场，但牧草不能按谷物单产折算：'
                                    '不参与现有粮食公式，需单独的生产模型')
        else:
            entry['note_supply'] = '非生产用地'
        parsed.append(entry)
    return parsed


def _rings_overlap(a, b):
    """Rough overlap test: do any vertices fall inside the other ring?"""
    def inside(point, ring):
        x, y = point
        result = False
        count = len(ring)
        for i in range(count):
            x1, y1 = ring[i]
            x2, y2 = ring[(i + 1) % count]
            if (y1 > y) != (y2 > y):
                xin = x1 + (y - y1) * (x2 - x1) / ((y2 - y1) or 1e-12)
                if x < xin:
                    result = not result
        return result
    ra = _unwrap_longitudes([tuple(p) for p in a])
    rb = _unwrap_longitudes([tuple(p) for p in b])
    return any(inside(p, rb) for p in ra) or any(inside(p, ra) for p in rb)


def summarize_land_use(entries, *, radius_km=6371.0088):
    """Totals by kind, explicit overlaps, and the fact that unplanned land stays unplanned."""
    by_kind = {}
    for entry in entries:
        by_kind[entry['kind']] = round(by_kind.get(entry['kind'], 0.0) + entry['area_km2'], 4)
    conflicts = []
    for i in range(len(entries)):
        for j in range(i + 1, len(entries)):
            if _rings_overlap(entries[i]['vertices'], entries[j]['vertices']):
                conflicts.append({
                    'a': i, 'b': j,
                    'kinds': [entries[i]['kind'], entries[j]['kind']],
                    'note': '两块用地重叠，需作者确认归属，不自动择一',
                })
    productive = round(sum(by_kind.get(kind, 0.0) for kind in GRAIN_KINDS), 4)
    return {
        'by_kind_km2': by_kind,
        'declared_km2': round(sum(by_kind.values()), 4),
        'productive_declared_km2': productive,
        'item_count': len(entries),
        # 没画到的区域就是没规划，不是荒地
        'unplanned_elsewhere': True,
        'unplanned_note': '图上未圈出的区域一律记为「未规划」，不当作荒地、也不当作农田',
        'conflicts': conflicts,
        'radius_km': round(radius_km, 4),
    }
