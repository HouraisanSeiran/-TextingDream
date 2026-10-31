# -*- coding: utf-8 -*-
"""Spatial drafts: an author's geometry, stored *before* any economy exists.

Why this module exists (see ``docs/town-space-and-land-use.md``):

``app.towns`` reads ``TownInput.terrain.area_km2`` as **grain-bearing hinterland**
(``towns.py:167`` multiplies it by ``_arable_fraction``). A built-up footprint, a mine or a
sampling window must never land in that field, so a settlement that has only a footprint has
nowhere to go through ``map_import.build_town_input`` — it is refused. This module stores
that intermediate state instead of discarding it.

The three layers stay apart:

1. **environment** — an import id plus the content hash of the file it names, verified
   against the record the resolver returns, plus the author's sampling parameters so the
   point can be re-sampled later. Never a path, never a URL, never a client-supplied sample.
2. **footprint** — where the buildings are. Its own polygon, area reported, and *never*
   used as farmland.
3. **land use** — optional, sparse, author-drawn. A mine is an *intent*: no surveyed deposit,
   no extractable amount, no stock. A pasture is declared but does **not** enter the grain
   formula (``GRAIN_KINDS`` is farmland only). Land nobody drew stays ``unplanned``; it is
   not wasteland.

Nothing here estimates, surveys, mines, harvests or imports. ``to_town_input`` is the only
bridge to the town schema, it goes through ``map_import.build_town_input`` unchanged, and it
keeps the draft when it refuses.

Storage: the existing ``documents`` table, kind ``spatial_draft`` — no second database, no
migration, never a write to the story-package pointer, and never a new hashing scheme: the
draft id is a random id in the same style ``runtime.uid()`` uses, and source identity is the
content hash the import record already carries.
"""
import hashlib
import json
import math
import re
import uuid
from datetime import datetime, timezone

from . import land_footprint as land
from . import map_import
from . import world_basis

SCHEMA = 1
KIND = 'spatial_draft'
ID_PREFIX = 'sd_'
_ID_RE = re.compile(r'^sd_[0-9a-f]{8,32}$')
_IMPORT_ID_RE = re.compile(r'^(?:sn|mi)_[0-9a-f]{6,32}$')
_HEX64_RE = re.compile(r'^[0-9a-f]{64}$')
_REQUEST_ID_RE = re.compile(r'^[A-Za-z0-9_-]{1,64}$')

#: Geometry budget, enforced **before** any O(n^2) self-intersection test runs. The
#: validator allows 4096 vertices per ring, which at 64 rings would be ~4096 x 64 pairwise
#: comparisons; a real settlement ring is tens of vertices, so the budget is generous for
#: the intended use and hard for the pathological one.
MAX_FACES = land.MAX_LAND_USE_ITEMS          # 64 rings total (footprint counts as one)
MAX_FACE_VERTICES = 256                      # per ring
MAX_TOTAL_VERTICES = 512                     # all rings together
#: ``polygon_area_km2`` is an equirectangular shoelace scaled by cos(mean latitude). That is
#: a reasonable approximation for a town-sized ring inside one latitude band; it drifts
#: where the band is wide or the latitude extreme, so both are refused rather than reported
#: as if the number were measured.
MAX_ABS_LAT = 78.0
MAX_LAT_SPAN_DEG = 30.0
#: 边相交筛查的运算预算。总顶点 ≤ 512 时全部面两两比较的边对数上限约 13 万；
#: 超出预算的配对不会被默默当成「不重叠」——扫描会报 complete=False，
#: 转换则必须先由作者重画。
MAX_EDGE_PAIRS = 200000

DEFAULT_RADIUS_KM = map_import.DEFAULT_RADIUS_KM
MIN_RADIUS_KM = 1000.0
MAX_RADIUS_KM = 20000.0
DEFAULT_WINDOW_PX = map_import.MIN_WINDOW_PX
MIN_WINDOW_PX = map_import.MIN_WINDOW_PX
MAX_WINDOW_PX = map_import.MAX_WINDOW_PX

SUPPLY_UNCONFIGURED = 'unconfigured'
SUPPLY_CONFIGURED = 'configured'

AREA_SOURCE_HINTERLAND = 'author_declared_hinterland'
AREA_SOURCE_FARMLAND = 'declared_farmland'

#: Carried on every draft and on every conversion result: what the area number means.
AREA_APPROXIMATION = {
    'method': 'shoelace_on_equirectangular_scaled_by_cos_mean_latitude',
    'area_is_approximate': True,
    'valid_latitude_band': [-MAX_ABS_LAT, MAX_ABS_LAT],
    'max_latitude_span_deg': MAX_LAT_SPAN_DEG,
    'planned_is_not_cultivated': True,
    'overlap_precision': ('重叠用 land_footprint.summarize_land_use 的顶点包含筛查：'
                          '它只报告可疑重叠，不是精确多边形求交或求差，'
                          '本模块既不并集也不做面积扣除'),
    'note': ('面积按等距圆柱投影 + 平均纬度余弦折算，只在上面那个纬带里成立；'
             '用地面积是作者规划的范围，不是实际耕作面积，粮食仍由既有 arable 规则算'),
}

_REQUEST_KEYS = ('site_name', 'footprint', 'land_use', 'environment_ref', 'world_basis_ref',
                 'city_ref', 'hinterland_km2', 'sampling', 'note', 'request_id')
_FOOTPRINT_KEYS = ('vertices', 'note')
_LAND_USE_KEYS = ('kind', 'vertices', 'note')
_ENV_KEYS = ('import_id', 'source_sha256')
_CITY_KEYS = ('import_id', 'source_sha256', 'city_id')
# 上游 civ 的 settlement 实体 id 是数字；这里按 ``settlement:<数字>`` 的稳定引用。
_CITY_ID_RE = re.compile(r'^settlement:[0-9]{1,12}$')
_SAMPLING_KEYS = ('lon', 'lat', 'window_px', 'radius_km')


def _allowed_formats():
    from . import civ_atlas_snapshot
    return (civ_atlas_snapshot.FORMAT, map_import.FORMAT)


class SpatialDraftError(ValueError):
    """A refused draft operation. One sentence, and nothing partially written."""


def _now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def _text(value, label, limit, required=False):
    if value is None:
        if required:
            raise SpatialDraftError('请填写%s' % label)
        return ''
    if not isinstance(value, str):
        raise SpatialDraftError('%s 必须是字符串' % label)
    value = value.strip()
    if required and not value:
        raise SpatialDraftError('请填写%s' % label)
    if len(value) > limit:
        raise SpatialDraftError('%s 过长（上限 %d 字符）' % (label, limit))
    return value


def _number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SpatialDraftError('%s 必须是数字' % label)
    if not math.isfinite(value):
        raise SpatialDraftError('%s 不能是 NaN 或无穷' % label)
    return float(value)


def _keys(raw, allowed, label):
    if not isinstance(raw, dict):
        raise SpatialDraftError('%s必须是对象' % label)
    extra = set(raw) - set(allowed)
    if extra:
        raise SpatialDraftError('%s有未知字段：%s' % (label, '、'.join(sorted(extra))))
    return raw


# ===================================================================== request

def _parse_footprint(raw):
    if raw is None:
        return None
    if isinstance(raw, (list, tuple)):
        raise SpatialDraftError('建筑范围请写成 {"vertices": [[经度, 纬度], …]}，'
                                '不接受裸顶点数组')
    raw = _keys(raw, _FOOTPRINT_KEYS, '建筑范围')
    if 'vertices' not in raw:
        raise SpatialDraftError('建筑范围缺少 vertices')
    return {'vertices': raw['vertices'], 'note': _text(raw.get('note'), '建筑范围说明', 300)}


def _parse_land_use(raw):
    if raw is None:
        return []
    if not isinstance(raw, (list, tuple)):
        raise SpatialDraftError('用地规划必须是数组')
    if len(raw) > MAX_FACES:
        raise SpatialDraftError('用地规划条数过多（上限 %d 条）' % MAX_FACES)
    items = []
    for index, item in enumerate(raw):
        item = _keys(item, _LAND_USE_KEYS, '第 %d 条用地规划' % index)
        if 'kind' not in item or 'vertices' not in item:
            raise SpatialDraftError('第 %d 条用地规划必须给出 kind 与 vertices' % index)
        items.append({'kind': item['kind'], 'vertices': item['vertices'],
                      'note': _text(item.get('note'), '第 %d 条用地规划说明' % index, 300)})
    return items


def _parse_environment_ref(raw):
    raw = _keys(raw, _ENV_KEYS, '环境引用')
    import_id = raw.get('import_id')
    if not isinstance(import_id, str) or not _IMPORT_ID_RE.fullmatch(import_id):
        raise SpatialDraftError('环境引用的 import_id 必须是 mi_/sn_ 开头的导入编号，'
                                '不接受路径或链接')
    digest = raw.get('source_sha256')
    if not isinstance(digest, str) or not _HEX64_RE.fullmatch(digest.lower()):
        raise SpatialDraftError('环境引用的 source_sha256 必须是 64 位十六进制')
    return {'import_id': import_id, 'source_sha256': digest.lower()}


def _parse_city_ref(raw):
    """可选的 civ 城市引用：**只链接**原件里已有的城市，不新建。

    三键必填：哪份原件（import_id + source_sha256）、原件里哪个城市实体（city_id）。
    这里只校验形状；「这个城市真的存在」必须到原件里查（见 _resolve_city）。
    """
    if raw is None:
        return None
    raw = _keys(raw, _CITY_KEYS, '城市引用')
    import_id = raw.get('import_id')
    if not isinstance(import_id, str) or not _IMPORT_ID_RE.fullmatch(import_id):
        raise SpatialDraftError('城市引用的 import_id 必须是 mi_/sn_ 开头的导入编号，'
                                '不接受路径或链接')
    digest = raw.get('source_sha256')
    if not isinstance(digest, str) or not _HEX64_RE.fullmatch(digest.lower()):
        raise SpatialDraftError('城市引用的 source_sha256 必须是 64 位十六进制')
    city_id = raw.get('city_id')
    if not isinstance(city_id, str) or not _CITY_ID_RE.fullmatch(city_id):
        raise SpatialDraftError('城市引用需要原件里的城市实体 id（settlement:…），'
                                '不能只用地点名')
    return {'import_id': import_id, 'source_sha256': digest.lower(), 'city_id': city_id}


def _parse_window(raw):
    if raw is None:
        return DEFAULT_WINDOW_PX
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise SpatialDraftError('取样窗格必须是整数')
    if raw < MIN_WINDOW_PX or raw > MAX_WINDOW_PX or raw % 2 == 0:
        raise SpatialDraftError('取样窗格必须是 %d…%d 之间的奇数'
                                % (MIN_WINDOW_PX, MAX_WINDOW_PX))
    return raw


def _parse_sampling(raw):
    """The author's sampling point, saved so the server can re-sample after a restart.

    Without this a draft would name an import but no place, and no later conversion could
    know what to sample. Only the point and the two numeric knobs are stored; nothing about
    the resulting climate is trusted from here.
    """
    if raw is None:
        return None
    raw = _keys(raw, _SAMPLING_KEYS, '取样选点')
    lon = _number(raw.get('lon'), '选点经度')
    lat = _number(raw.get('lat'), '选点纬度')
    if not -180.0 <= lon <= 180.0:
        raise SpatialDraftError('选点经度必须在 −180…180 之间')
    if not -90.0 <= lat <= 90.0:
        raise SpatialDraftError('选点纬度必须在 −90…90 之间')
    if abs(lat) > 89.5:
        raise SpatialDraftError('选点太靠近极点（|纬度| > 89.5），该处取样会被拉伸')
    radius = (DEFAULT_RADIUS_KM if raw.get('radius_km') is None
              else _number(raw.get('radius_km'), '星体半径'))
    if not MIN_RADIUS_KM <= radius <= MAX_RADIUS_KM:
        raise SpatialDraftError('星体半径必须在 %g…%g km 之间'
                                % (MIN_RADIUS_KM, MAX_RADIUS_KM))
    return {'lon': round(lon, 4), 'lat': round(lat, 4),
            'window_px': _parse_window(raw.get('window_px')),
            'radius_km': round(radius, 4),
            'source': 'author_stated'}


def parse_request(body):
    """Strict, bounded request body. Unknown keys are refused, never ignored."""
    if not isinstance(body, dict):
        raise SpatialDraftError('空间草稿请求必须是对象')
    extra = set(body) - set(_REQUEST_KEYS)
    if extra:
        raise SpatialDraftError('空间草稿请求有未知字段：%s' % '、'.join(sorted(extra)))
    site_name = _text(body.get('site_name'), '地点名', 80, required=True)
    footprint = _parse_footprint(body.get('footprint'))
    land_use = _parse_land_use(body.get('land_use'))
    if footprint is None and not land_use:
        raise SpatialDraftError(
            '请至少圈出建筑范围（footprint）或一条用地规划（land_use）；'
            '只圈建筑范围也可以，那样会存成「供给未配置」的空间草稿')
    world_basis_ref = body.get('world_basis_ref')
    if world_basis_ref is not None:
        if not isinstance(world_basis_ref, str) or not world_basis_ref.startswith('wb_'):
            raise SpatialDraftError('world_basis_ref 必须是 wb_… 编号或留空')
    hinterland = body.get('hinterland_km2')
    if hinterland is not None:
        hinterland = _number(hinterland, '城镇腹地')
        if not 0.5 <= hinterland <= 20000.0:
            raise SpatialDraftError('城镇腹地必须在 0.5…20000 km² 之间（收到 %.2f）' % hinterland)
    request_id = body.get('request_id')
    if request_id is not None:
        if not isinstance(request_id, str) or not _REQUEST_ID_RE.fullmatch(request_id):
            raise SpatialDraftError('request_id 只能是 1–64 位字母数字、下划线或连字符')
    return {
        'site_name': site_name,
        'note': _text(body.get('note'), '备注', 300),
        'footprint': footprint,
        'land_use': land_use,
        'environment_ref': _parse_environment_ref(body.get('environment_ref')),
        'city_ref': _parse_city_ref(body.get('city_ref')),
        'world_basis_ref': world_basis_ref,
        'hinterland_km2': hinterland,
        'sampling': _parse_sampling(body.get('sampling')),
        'request_id': request_id,
    }


# ==================================================================== geometry

def _ring_vertices(raw, label):
    """Count the ring *before* the O(n^2) self-intersection test runs on it."""
    if not isinstance(raw, (list, tuple)):
        raise SpatialDraftError('%s 的顶点必须是数组' % label)
    if len(raw) > MAX_FACE_VERTICES:
        raise SpatialDraftError('%s 有 %d 个顶点，超过单面上限 %d'
                                % (label, len(raw), MAX_FACE_VERTICES))
    return len(raw)


def _latitude_guard(ring, label):
    lats = [lat for _lon, lat in ring]
    if max(abs(value) for value in lats) > MAX_ABS_LAT:
        raise SpatialDraftError('%s 超出 ±%g° 纬带：这一带面积用平均纬度余弦近似没有依据，'
                                '请改圈中低纬度的范围' % (label, MAX_ABS_LAT))
    if max(lats) - min(lats) > MAX_LAT_SPAN_DEG:
        raise SpatialDraftError('%s 的纬度跨度 %.1f° 超过 %g°：面积近似要求环带在一段纬度内'
                                % (label, max(lats) - min(lats), MAX_LAT_SPAN_DEG))


def _check_budget(footprint, land_use):
    faces = (1 if footprint is not None else 0) + len(land_use)
    if faces > MAX_FACES:
        raise SpatialDraftError('面数过多（%d 个），上限 %d' % (faces, MAX_FACES))
    shapes = []
    if footprint is not None:
        shapes.append(('建筑范围', footprint['vertices']))
    for index, item in enumerate(land_use):
        shapes.append(('用地规划#%d（%s）' % (index, item['kind']), item['vertices']))
    total = 0
    for label, vertices in shapes:
        total += _ring_vertices(vertices, label)
    if total > MAX_TOTAL_VERTICES:
        raise SpatialDraftError('所有多边形的顶点合计 %d 个，超过总预算 %d'
                                % (total, MAX_TOTAL_VERTICES))
    return {'faces': faces, 'vertices': total, 'per_face_vertices': MAX_FACE_VERTICES,
            'max_faces': MAX_FACES, 'total_vertices_budget': MAX_TOTAL_VERTICES,
            'note': ('顶点预算在自交检测之前执行：4096 顶点 × 64 面是 O(n²)，'
                     '正常城镇环只有几十个顶点')}


def _unwrapped_edges(ring):
    """Edges of one validated ring, longitudes unwrapped so ±180 is a 2° step."""
    points = land._unwrap_longitudes([(float(lon), float(lat)) for lon, lat in ring])
    count = len(points)
    return [(points[index], points[(index + 1) % count]) for index in range(count)]


def _edges_cross(one, two):
    """Bounded-bbox prefilter, then the project's own segment-intersection test.

    ``land_footprint._segments_cross`` is reused rather than reimplemented: the shared file
    is not modified. Touching or collinear edges (an author drawing a field against the
    town wall) do not count as crossing, which is why the vertex-containment screen is kept
    alongside this one.
    """
    (ax1, ay1), (ax2, ay2) = one
    (bx1, by1), (bx2, by2) = two
    if max(ax1, ax2) < min(bx1, bx2) or max(bx1, bx2) < min(ax1, ax2):
        return False
    if max(ay1, ay2) < min(by1, by2) or max(by1, by2) < min(ay1, ay2):
        return False
    return land._segments_cross(one[0], one[1], two[0], two[1])


def _shape_overlaps(shapes):
    """Overlaps among already-validated faces: existing screen + a bounded edge check.

    Two capabilities are consumed, neither invented here:

    * ``land_footprint.summarize_land_use`` — the vertex-in-polygon screen;
    * ``land_footprint._segments_cross`` — the same segment test the self-intersection
      validator uses, applied **between** two rings.

    The second one exists because the first misses one shape of overlap: a long thin field
    crossed by another field whose four corners all sit outside each other (a cross). Nothing
    is resolved, unioned or subtracted, and the pair count is budgeted: a pair that cannot be
    checked is reported as *undetermined*, never as clean.

    ``shapes`` are ``(label, kind, entry)`` tuples; indices in the result point into that list.
    """
    summary = land.summarize_land_use([{'kind': kind, 'vertices': entry['vertices'],
                                        'area_km2': entry['area_km2']}
                                       for _label, kind, entry in shapes])
    found = {}
    for conflict in summary['conflicts']:
        found[(conflict['a'], conflict['b'])] = ['vertex_containment']

    edges = [_unwrapped_edges(entry['vertices']) for _label, _kind, entry in shapes]
    planned = 0
    untested = []
    for left in range(len(shapes)):
        for right in range(left + 1, len(shapes)):
            if (left, right) in found:
                continue
            cost = len(edges[left]) * len(edges[right])
            if planned + cost > MAX_EDGE_PAIRS:
                untested.append([left, right])
                continue
            planned += cost
            if any(_edges_cross(one, two) for one in edges[left] for two in edges[right]):
                found[(left, right)] = ['edge_crossing']

    conflicts = []
    for (left, right) in sorted(found):
        conflicts.append({'a': left, 'b': right,
                          'labels': [shapes[left][0], shapes[right][0]],
                          'kinds': [shapes[left][1], shapes[right][1]],
                          'methods': found[(left, right)],
                          'note': '两块范围重叠，需作者确认归属，不自动择一也不做差集'})
    scan = {'edge_pairs_checked': planned, 'edge_pair_budget': MAX_EDGE_PAIRS,
            'vertex_containment': True, 'edge_crossing': True,
            'complete': not untested, 'untested_pairs': untested,
            'note': ('顶点包含筛查 + 环间边相交筛查；不是精确多边形求交，'
                     '共边/共点不算重叠；complete=false 表示有配对因预算未查，'
                     '不能当作「不重叠」')}
    return conflicts, scan


def _geometry(parsed):
    """Validate the rings with the existing parser, after the cheap budget checks."""
    budget = _check_budget(parsed['footprint'], parsed['land_use'])
    # Cheap linear pass first: latitude band, then the (quadratic) polygon parser.
    if parsed['footprint'] is not None:
        ring = land.parse_vertices(parsed['footprint']['vertices'], label='建筑范围')
        _latitude_guard(ring, '建筑范围')
    for index, item in enumerate(parsed['land_use']):
        label = '用地规划#%d（%s）' % (index, item['kind'])
        ring = land.parse_vertices(item['vertices'], label=label)
        _latitude_guard(ring, label)
    footprint = (land.parse_footprint(parsed['footprint']['vertices'])
                 if parsed['footprint'] is not None else None)
    entries = land.parse_land_use(parsed['land_use'])
    summary = land.summarize_land_use(entries)
    shapes = []
    if footprint is not None:
        shapes.append(('建筑范围', 'footprint', footprint))
    for index, entry in enumerate(entries):
        shapes.append(('用地规划#%d（%s）' % (index, entry['kind']), entry['kind'], entry))
    # 建筑范围与农田叠在一起时，农田面积把建成区也算进去了：这是作者必须重画的冲突，
    # 不是可以静默扣减的差集（本模块不做多边形差）。
    overlaps, scan = _shape_overlaps(shapes)
    footprint_conflicts = [conflict for conflict in overlaps
                           if 'footprint' in conflict['kinds']]
    return {'footprint': footprint, 'land_use': entries, 'land_use_summary': summary,
            'overlaps': overlaps, 'overlap_scan': scan,
            'footprint_conflicts': footprint_conflicts, 'geometry_budget': budget}


def _sampling(parsed, geometry):
    """Explicit sampling parameters, or a footprint vertex mean labelled as such."""
    if parsed['sampling'] is not None:
        return {**parsed['sampling'],
                'note': '作者给出的取样选点与参数；转换时由服务端按这组参数重算'}
    footprint = geometry['footprint']
    if not footprint:
        return None
    vertices = footprint['vertices']
    lon = math.degrees(math.atan2(sum(math.sin(math.radians(v[0])) for v in vertices),
                                  sum(math.cos(math.radians(v[0])) for v in vertices)))
    lat = sum(v[1] for v in vertices) / float(len(vertices))
    return {'lon': round(lon, 4), 'lat': round(lat, 4), 'window_px': DEFAULT_WINDOW_PX,
            'radius_km': round(DEFAULT_RADIUS_KM, 4),
            'source': 'footprint_vertex_mean',
            'note': ('按建筑范围的顶点均值取的初始选点：它可能落在凹多边形外面，'
                     '转换时必须真实取样才能确认；这里不冒充精确中心')}


def _area_plan(geometry, hinterland):
    summary = geometry['land_use_summary']
    by_kind = summary['by_kind_km2']
    farmland = float(by_kind.get('farmland', 0.0))
    plan = {
        'planned_km2': summary['declared_km2'],
        'by_kind_km2': dict(by_kind),
        'farmland_km2': farmland,
        # 牧场显式声明了，但牧草不能按谷物单产折算，所以不进 terrain.area_km2。
        'pasture_km2': float(by_kind.get('pasture', 0.0)),
        'grain_km2': farmland,
        'hinterland_km2': hinterland,
        'planned_is_not_cultivated': True,
        'note': ('terrain.area_km2 只能来自已声明的农田或作者显式腹地；'
                 '建筑范围、矿山、林地、荒地都不进这个字段'),
    }
    if hinterland is not None:
        plan['terrain_area_km2'] = hinterland
        plan['area_source'] = AREA_SOURCE_HINTERLAND
    elif farmland > 0.0:
        plan['terrain_area_km2'] = farmland
        plan['area_source'] = AREA_SOURCE_FARMLAND
    else:
        plan['terrain_area_km2'] = None
        plan['area_source'] = None
    supply = {'state': (SUPPLY_CONFIGURED if plan['terrain_area_km2'] else
                        SUPPLY_UNCONFIGURED),
              'area_km2': plan['terrain_area_km2'],
              'source': plan['area_source'],
              'note': ('已声明可进粮食规则的面积' if plan['terrain_area_km2'] else
                       '还没有农田也没有显式腹地：草稿可以存在，但不能发布成可运行城镇')}
    return plan, supply


# ================================================================= environment

def _resolve_environment(store, ref, resolver):
    resolve = resolver or (lambda identifier: map_import.get_import(store, identifier))
    try:
        record = resolve(ref['import_id'])
    except ValueError as error:
        raise SpatialDraftError('环境引用的导入 %s 读不出来：%s'
                                % (ref['import_id'], error))
    if not isinstance(record, dict):
        raise SpatialDraftError('环境引用解析出的记录不是对象')
    if record.get('id') != ref['import_id']:
        raise SpatialDraftError('环境引用解析出的记录编号（%r）与请求的 %r 不一致'
                                % (record.get('id'), ref['import_id']))
    digest = str(record.get('sha256') or '')
    if not _HEX64_RE.fullmatch(digest):
        raise SpatialDraftError('导入记录没有自带内容哈希，无法固定来源')
    if not digest.startswith(ref['import_id'][3:]):
        raise SpatialDraftError('导入编号与自身内容哈希不自洽（%s 对 %s…），拒绝使用'
                                % (ref['import_id'], digest[:12]))
    if digest != ref['source_sha256']:
        raise SpatialDraftError('源哈希冲突：环境引用声明 %s…，这条导入记录是 %s…，拒绝关联'
                                % (ref['source_sha256'][:12], digest[:12]))
    fmt = record.get('format')
    if fmt not in _allowed_formats():
        raise SpatialDraftError('这条导入的格式（%r）不是 civ-atlas 地形数据' % fmt)
    source = record.get('source') or {}
    return ({'import_id': ref['import_id'], 'source_sha256': digest, 'format': fmt,
             'width': record.get('width'), 'height': record.get('height'),
             'cells': record.get('pixels'), 'world_id': source.get('world_id'),
             'import_created': record.get('created')}, record)


def _store_root(store):
    """原件所在的目录：与 web/服务层同一条规则（数据根旁边的 map_imports）。"""
    from pathlib import Path
    return Path(store.path).resolve().parent


def _resolve_city(store, root, city_ref, environment, record):
    """把 ``city_ref`` 绑定到原件里**真实存在的** civ 城市实体。

    三件事，顺序固定：

    1. 引用必须指向同一个来源：``import_id``/``source_sha256`` 与环境引用一致，
       否则就是“用 A 的坐标声称属于 B 的城市”。
    2. 只有 CASNAP 原件有 civ 实体；高度图没有城市，直接拒。
    3. 从原件里读出 civ，按 id 找到那条 settlement，回填它自己的 name/region/cell/founded
       ——**不回显 site_name**，也不把整份 civ 复制进草稿。

    本函数不生成任何城市：找不到就是找不到。
    """
    if city_ref is None:
        return None
    if environment is None:
        raise SpatialDraftError('城市引用必须同时给出 environment_ref（同一份原件）')
    if (city_ref['import_id'] != environment['import_id']
            or city_ref['source_sha256'] != environment['source_sha256']):
        raise SpatialDraftError('城市引用与环境引用必须指向同一份原件'
                                '（import_id 与 source_sha256 都要一致）')
    from . import civ_atlas_history, civ_atlas_snapshot
    if record.get('format') != civ_atlas_snapshot.FORMAT:
        raise SpatialDraftError('只有 civ-atlas 原生快照里才有城市实体；'
                                '当前环境引用是 %r' % record.get('format'))
    # 读原件字节**不自己拼路径、不自己算哈希**：复用已验的 native_worlds 桥。
    # 它在返回前强制文件名不出 map_imports 目录，并重算整件 SHA-256 与记录比对，
    # 所以「记录指向 A、磁盘实际是 B」在拿到字节前就被拒。
    from . import native_worlds
    try:
        data, _checked = native_worlds.snapshot_bytes(
            store, _store_root(store), city_ref['import_id'])
    except ValueError as error:
        raise SpatialDraftError('城市引用的原件读不出来：%s' % error)
    try:
        civ, _manifest = civ_atlas_history.load_civ(data)
    except ValueError as error:
        raise SpatialDraftError('原件里的 civ 那块读不出来：%s' % error)
    wanted = city_ref['city_id']
    for settlement in civ.get('settlements') or ():
        if not isinstance(settlement, dict):
            continue
        if 'settlement:%s' % settlement.get('id') != wanted:
            continue
        return {'import_id': city_ref['import_id'],
                'source_sha256': city_ref['source_sha256'],
                'city_id': wanted,
                'name': settlement.get('name'),
                'region': settlement.get('region'),
                'cell': settlement.get('cell'),
                'founded': settlement.get('founded'),
                'identity_verified': 'snapshot_civ'}
    raise SpatialDraftError('这个原件里没有这个城市实体（%s）；'
                            '不会新建同名城，请从原件已有的城市里选' % wanted)


def _resolve_basis(store, basis_id, record, environment):
    if basis_id is None:
        return None
    try:
        basis = world_basis.get(store, basis_id)
    except ValueError as error:
        raise SpatialDraftError('world_basis_ref 读不出来：%s' % error)
    if environment is None:
        raise SpatialDraftError('世界基础必须绑定到具体导入：请同时给出 environment_ref')
    try:
        world_basis.refuse_stale(store, basis, record)
    except ValueError as error:
        raise SpatialDraftError(str(error))
    selection = basis.get('selection') or {}
    return {'id': basis['id'], 'digest': basis.get('digest'),
            'content_sha256': (basis.get('source') or {}).get('content_sha256'),
            'world_id': (basis.get('world') or {}).get('source_world_id'),
            'branch': selection.get('branch'), 'base_year': selection.get('base_year'),
            'history_state': (basis.get('history') or {}).get('state')}


# ==================================================================== document

def content_hash(doc):
    """Digest of what a save may change; ``revision``, ids, timestamps and the pinned story
    base are excluded — those identify the document, they are not its content."""
    body = {key: doc.get(key) for key in
            ('site_name', 'environment_ref', 'world_basis_ref', 'footprint', 'land_use',
             'land_use_summary', 'overlaps', 'overlap_scan', 'footprint_conflicts',
             'area_plan', 'hinterland_km2', 'sampling', 'note')}
    return hashlib.sha256(_canonical(body).encode('utf-8')).hexdigest()[:32]


def _document(store, parsed, *, story_base_revision, resolver):
    environment, record = _resolve_environment(store, parsed['environment_ref'], resolver)
    basis = _resolve_basis(store, parsed['world_basis_ref'], record, environment)
    city = _resolve_city(store, _store_root(store), parsed.get('city_ref'), environment, record)
    geometry = _geometry(parsed)
    plan, supply = _area_plan(geometry, parsed['hinterland_km2'])
    warnings = []
    summary = geometry['land_use_summary']
    if geometry['footprint'] is not None:
        warnings.append('建筑范围只表示作者规划的建成边界（约 %.2f km²），'
                        '不是测量结果，也不会被当成耕地'
                        % geometry['footprint']['area_km2'])
    if supply['state'] == SUPPLY_UNCONFIGURED:
        warnings.append('还没有农田也没有显式腹地：草稿可以保存，但转换不出可运行城镇')
    if plan['pasture_km2']:
        warnings.append('牧场已声明，但牧草不能按谷物单产折算，本版不把它计入粮食')
    if any(entry['kind'] == 'mine' for entry in geometry['land_use']):
        warnings.append('矿山只表达规划意图：不是已勘探矿藏，不产生可采量或库存')
    if geometry['overlaps']:
        warnings.append('有 %d 处范围重叠（顶点包含或边相交），需作者确认归属，不自动择一'
                        % len(geometry['overlaps']))
    if geometry['footprint_conflicts']:
        warnings.append('建筑范围与其它用地重叠 %d 处：农田面积把建成区也算进去了，'
                        '这种草稿不能转换，请重画到不重叠' % len(geometry['footprint_conflicts']))
    if not geometry['overlap_scan']['complete']:
        warnings.append('有 %d 对范围因运算预算未做重叠检查：不能当作「不重叠」，'
                        '请减少顶点或减少面数后重画'
                        % len(geometry['overlap_scan']['untested_pairs']))
    warnings.append(summary['unplanned_note'])
    doc = {
        'id': ID_PREFIX + uuid.uuid4().hex[:16],
        'kind': KIND,
        'schema': SCHEMA,
        'story_base_revision': story_base_revision,
        'request_id': parsed['request_id'],
        'site_name': parsed['site_name'],
        'note': parsed['note'],
        'footprint': geometry['footprint'],
        'land_use': geometry['land_use'],
        'land_use_summary': summary,
        'overlaps': geometry['overlaps'],
        'overlap_scan': geometry['overlap_scan'],
        'footprint_conflicts': geometry['footprint_conflicts'],
        'area_plan': plan,
        'supply': supply,
        'hinterland_km2': parsed['hinterland_km2'],
        'sampling': _sampling(parsed, geometry),
        'environment_ref': environment,
        'city_ref': city,
        'world_basis_ref': basis,
        'geometry_budget': geometry['geometry_budget'],
        'area_approximation': dict(AREA_APPROXIMATION),
        'warnings': warnings,
    }
    doc['content_hash'] = content_hash(doc)
    return doc


# ====================================================================== writes

def _read(store, draft_id):
    if not isinstance(draft_id, str) or not _ID_RE.fullmatch(draft_id):
        raise SpatialDraftError('空间草稿编号格式不对')
    row = store.get(KIND, draft_id)
    if not row:
        raise SpatialDraftError('找不到这个空间草稿')
    return row


def get(store, draft_id):
    """Read one draft. Read-only: never advances a revision."""
    return _read(store, draft_id)


def list_drafts(store):
    """All drafts, oldest first. Read-only."""
    return sorted(store.all(KIND), key=lambda row: (row.get('created') or '',
                                                    row.get('id') or ''))


def _resolve_story(story_base_revision):
    """空间草稿依据的故事版本；空世界时允许 ``None``。

    ``None`` 只表示“画的时候还没有世界”：这份草稿能保存、能读取、能 CAS 更新，
    但**不能**转换成城镇（转换需要目标故事，见 ``prepare_conversion`` 的
    ``story_base_revision_missing``）。不会静默改绑到之后出现的某个故事。
    """
    if story_base_revision is None:
        return None
    if not isinstance(story_base_revision, str) or not 8 <= len(story_base_revision) <= 64:
        raise SpatialDraftError('空间草稿必须固定它所依据的故事包版本（或空世界时留空）')
    return story_base_revision


def save(store, body, *, story_base_revision, resolver=None):
    """Create one draft inside one short transaction.

    The id is random (``sd_`` + 16 hex), so two places that share a name — or the same
    place drawn twice — are two independent drafts. Idempotent creation, when a caller wants
    it, is opt-in through ``request_id``: the same id with the same content returns the
    stored row, and the same id with different content is refused instead of silently
    overwriting.
    """
    revision = _resolve_story(story_base_revision)
    try:
        parsed = parse_request(body)
        doc = _document(store, parsed, story_base_revision=revision, resolver=resolver)
    except land.FootprintError as error:
        raise SpatialDraftError(str(error))
    with store.transact() as db:
        if parsed['request_id'] is not None:
            rows = db.execute('SELECT body FROM documents WHERE kind=?', (KIND,)).fetchall()
            same_request = [row for row in (json.loads(text[0]) for text in rows)
                            if row.get('request_id') == parsed['request_id']]
            if same_request:
                existing = same_request[0]
                if existing.get('story_base_revision') != revision:
                    raise SpatialDraftError(
                        'request_id「%s」的草稿基于故事包版本 %s，本次是 %s；'
                        '换一个 request_id 再建'
                        % (parsed['request_id'], existing.get('story_base_revision'), revision))
                if existing.get('content_hash') != doc['content_hash']:
                    raise SpatialDraftError(
                        'request_id「%s」已有内容不同的空间草稿（%s）；'
                        '要改内容请用 update 携带 expected_revision'
                        % (parsed['request_id'], existing.get('id')))
                return {'draft': existing, 'created': False}
        doc['revision'] = 0
        doc['created'] = _now()
        doc['updated'] = doc['created']
        db.execute('INSERT INTO documents(kind,id,body) VALUES(?,?,?)',
                   (KIND, doc['id'],
                    json.dumps(doc, ensure_ascii=False, separators=(',', ':'))))
    return {'draft': doc, 'created': True}


def update(store, draft_id, body, *, expected_revision, resolver=None):
    """Replace one draft's geometry with a compare-and-swap on ``revision``.

    The CAS is re-evaluated against the row as it exists *inside* the write lock, so a
    concurrent writer that got in between leaves this call with zero side effects.
    """
    if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
        raise SpatialDraftError('乐观版本号必须是整数')
    stale = _read(store, draft_id)
    try:
        parsed = parse_request(body)
        doc = _document(store, parsed, story_base_revision=stale['story_base_revision'],
                        resolver=resolver)
    except land.FootprintError as error:
        raise SpatialDraftError(str(error))
    doc['id'] = stale['id']
    doc['request_id'] = stale.get('request_id')
    with store.transact() as db:
        row = db.execute('SELECT body FROM documents WHERE kind=? AND id=?',
                         (KIND, draft_id)).fetchone()
        if row is None:
            raise SpatialDraftError('找不到这个空间草稿')
        latest = json.loads(row[0])
        if latest.get('revision') != expected_revision:
            raise SpatialDraftError('空间草稿已被其他操作更新（当前版本 %s，提交版本 %s），'
                                    '请刷新后重试'
                                    % (latest.get('revision'), expected_revision))
        doc['created'] = latest.get('created') or _now()
        doc['updated'] = _now()
        doc['revision'] = expected_revision + 1
        db.execute('INSERT OR REPLACE INTO documents VALUES(?,?,?)',
                   (KIND, doc['id'],
                    json.dumps(doc, ensure_ascii=False, separators=(',', ':'))))
    return doc


# ================================================================== conversion

def _check_expected(draft, expected_revision):
    """Optional explicit revision pin: refuse before doing any work if it already moved."""
    if expected_revision is None:
        return True
    if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
        raise SpatialDraftError('乐观版本号必须是整数')
    if draft.get('revision') != expected_revision:
        raise SpatialDraftError('空间草稿已被其他操作更新（当前版本 %s，提交版本 %s），'
                                '请刷新后重试'
                                % (draft.get('revision'), expected_revision))
    return True


def _check_unchanged(store, draft):
    """Re-read after the slow part: the conversion must describe the draft it started with.

    Read-only: this never repairs, retries or takes a write lock. A draft that moved in
    between makes the whole conversion refused rather than returning an input that mixes two
    revisions of the geometry.
    """
    latest = _read(store, draft['id'])
    if latest.get('revision') != draft.get('revision'):
        raise SpatialDraftError(
            '转换期间这份空间草稿被改了（开始时版本 %s，现在 %s）；为避免把两个版本的'
            '几何混在一起，本次转换作废，请刷新后重试'
            % (draft.get('revision'), latest.get('revision')))
    if latest.get('content_hash') != draft.get('content_hash'):
        raise SpatialDraftError('转换期间这份空间草稿的内容变了（版本号未变），本次转换作废')
    return True


def _blocking_overlaps(draft):
    """Overlaps that forbid a conversion, and why.

    Two rules, both *blocking* rather than warning, because silently adding areas would put
    houses into the grain field:

    1. a footprint touching **any** other face (a built-up area inside a field, or a field
       crossing the town wall) — the author must redraw; this module never subtracts area;
    2. two farmland faces overlapping (or farmland overlapping anything) — summing them
       would double-count.

    ``undetermined`` is returned too: a pair the bounded scan could not check is treated
    exactly like an overlap for the purpose of refusing, never as clean.
    """
    overlaps = list(draft.get('overlaps')
                    or (draft.get('land_use_summary') or {}).get('conflicts') or [])
    scan = draft.get('overlap_scan') or {}
    blocking = []
    for conflict in overlaps:
        kinds = conflict.get('kinds') or []
        if 'footprint' in kinds or any(kind in land.GRAIN_KINDS for kind in kinds):
            blocking.append(conflict)
    undetermined = [pair for pair in (scan.get('untested_pairs') or [])]
    return blocking, undetermined


def prepare_conversion(draft, *, current_story_revision=None):
    """What a conversion would need. Pure read: changes nothing, deletes nothing.

    ``blocking`` entries are refusals the *author* has to resolve (no supply, a footprint or
    field overlap, no sampling point, a moved story base). They never destroy the draft: the
    geometry stays and can keep being edited until the author redraws it.
    """
    summary = draft.get('land_use_summary') or {}
    plan = draft.get('area_plan') or {}
    conflicts = list(draft.get('overlaps') or summary.get('conflicts') or [])
    blocking, undetermined = _blocking_overlaps(draft)
    story_current = (current_story_revision is None
                     or current_story_revision == draft.get('story_base_revision'))
    missing = []
    # 空世界时画的草稿没绑任何故事版本：不能凭空找当前故事转换，明确拒绝。
    if draft.get('story_base_revision') is None:
        missing.append('story_base_revision_missing')
    if not plan.get('terrain_area_km2'):
        missing.append('farmland_or_hinterland')
    if not story_current:
        missing.append('story_base_revision_mismatch')
    if any('footprint' in (c.get('kinds') or []) for c in blocking):
        missing.append('footprint_overlaps_land_use')
    if any((c.get('kinds') or []) and 'footprint' not in (c.get('kinds') or [])
           and any(kind in land.GRAIN_KINDS for kind in c.get('kinds') or [])
           for c in blocking):
        missing.append('overlapping_farmland')
    if undetermined:
        missing.append('overlap_undetermined')
    if (draft.get('sampling') or {}).get('lon') is None:
        missing.append('sampling_point')
    return {
        'draft_id': draft.get('id'),
        'draft_revision': draft.get('revision'),
        'site_name': draft.get('site_name'),
        'story_base_revision': draft.get('story_base_revision'),
        'story_current': story_current,
        'supply': (draft.get('supply') or {}).get('state'),
        'area_source': plan.get('area_source'),
        'terrain_area_km2': plan.get('terrain_area_km2'),
        'farmland_km2': plan.get('farmland_km2'),
        'planned_km2': plan.get('planned_km2'),
        'footprint_area_km2': ((draft.get('footprint') or {}).get('area_km2')),
        'sampling': draft.get('sampling'),
        'conflicts': conflicts,
        'blocking_conflicts': blocking,
        'undetermined_pairs': undetermined,
        'overlap_scan': draft.get('overlap_scan'),
        'footprint_conflicts': list(draft.get('footprint_conflicts') or []),
        'missing': missing,
        'ready': not missing,
        'notes': [
            '地形面积只来自已声明农田或作者显式腹地；建筑范围与矿山不进这个字段',
            '规划用地面积是范围，不是实际耕作面积；粮食仍由既有 arable 规则算',
            '重叠按 land_footprint 的顶点包含筛查 + 环间边相交筛查报告，'
            '不做精确求交/差集；查不起的配对算「不明」而不是「干净」',
            ('缺少：' + '、'.join(missing)) if missing else '可以转换',
        ],
    }


def validate_sample(sample):
    """Structural check of a sampler result; never a claim about where it came from."""
    if not isinstance(sample, dict):
        raise SpatialDraftError('取样结果必须是对象')
    lon = _number(sample.get('lon'), '取样经度')
    lat = _number(sample.get('lat'), '取样纬度')
    if not -180.0 <= lon <= 180.0 or not -90.0 <= lat <= 90.0:
        raise SpatialDraftError('取样经纬度超出范围')
    window_px = sample.get('window_px')
    if isinstance(window_px, bool) or not isinstance(window_px, int) \
            or not MIN_WINDOW_PX <= window_px <= MAX_WINDOW_PX or window_px % 2 == 0:
        raise SpatialDraftError('取样窗格必须是 %d…%d 之间的奇数'
                                % (MIN_WINDOW_PX, MAX_WINDOW_PX))
    radius = _number(sample.get('radius_km'), '星体半径')
    if not MIN_RADIUS_KM <= radius <= MAX_RADIUS_KM:
        raise SpatialDraftError('星体半径必须在 %g…%g km 之间'
                                % (MIN_RADIUS_KM, MAX_RADIUS_KM))
    area = _number(sample.get('area_km2'), '取样面积')
    # 不按 TownInput 的 20000 km² 上限拒收：civ_atlas_snapshot.sample_region 已经明确
    # 不这么做（单个地块就可能 14959 km²），面积上限是城镇规则的事，不是取样的事。
    if area <= 0.0:
        raise SpatialDraftError('取样面积必须大于 0 km²')
    elevation = sample.get('elevation_m')
    if not isinstance(elevation, dict):
        raise SpatialDraftError('取样结果缺少 elevation_m')
    mean = _number(elevation.get('mean'), '取样均海拔')
    if not -500.0 <= mean <= 9000.0:
        raise SpatialDraftError('取样均海拔 %.0f 米超出 −500…9000 米' % mean)
    slope = sample.get('slope_deg')
    if not isinstance(slope, dict):
        raise SpatialDraftError('取样结果缺少 slope_deg')
    p50 = _number(slope.get('p50'), '取样坡度')
    if not 0.0 <= p50 <= 60.0:
        raise SpatialDraftError('取样坡度 %.1f° 超出 0…60°' % p50)
    pixel = sample.get('pixel')
    if not isinstance(pixel, dict):
        raise SpatialDraftError('取样结果缺少 pixel')
    for key in ('x', 'y'):
        value = pixel.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise SpatialDraftError('取样结果的 pixel.%s 必须是非负整数' % key)
    span = sample.get('span_km')
    if not isinstance(span, dict):
        raise SpatialDraftError('取样结果缺少 span_km')
    for key in ('north_south', 'east_west'):
        _number(span.get(key), '取样跨度 %s' % key)
    return {'lon': round(lon, 4), 'lat': round(lat, 4), 'window_px': window_px,
            'radius_km': round(radius, 4), 'area_km2': area,
            'elevation_m': {'mean': mean, 'min': elevation.get('min'),
                            'max': elevation.get('max')},
            'slope_deg': {'p50': p50, 'max': slope.get('max')},
            'pixel': {'x': pixel['x'], 'y': pixel['y']},
            'span_km': {'north_south': span['north_south'],
                        'east_west': span['east_west']},
            'climate': sample.get('climate'),
            'derived': list(sample.get('derived') or []),
            'warnings': list(sample.get('warnings') or [])}


def check_sample_matches(draft, sample):
    """The sample must be *this* draft's point and parameters, not some other place's."""
    saved = draft.get('sampling') or {}
    if saved.get('lon') is None:
        raise SpatialDraftError('这个空间草稿还没有取样选点，无法核对取样结果')
    if (round(sample['lon'], 4), round(sample['lat'], 4)) != (round(saved['lon'], 4),
                                                             round(saved['lat'], 4)):
        raise SpatialDraftError('取样点与草稿保存的选点不一致（草稿 %.4f,%.4f，取样 %.4f,%.4f）'
                                % (saved['lon'], saved['lat'], sample['lon'], sample['lat']))
    if sample['window_px'] != saved.get('window_px'):
        raise SpatialDraftError('取样窗格与草稿保存的不一致（草稿 %s，取样 %s）'
                                % (saved.get('window_px'), sample['window_px']))
    if abs(sample['radius_km'] - float(saved.get('radius_km')
                                       or DEFAULT_RADIUS_KM)) > 1e-6:
        raise SpatialDraftError('取样用的星体半径与草稿保存的不一致（草稿 %s，取样 %s）'
                                % (saved.get('radius_km'), sample['radius_km']))
    return True


def _author_for(author, draft):
    """The author's declarations, with geometry pinned to the draft."""
    if author is None:
        author = {}
    if not isinstance(author, dict):
        raise SpatialDraftError('作者字段必须是对象')
    author = dict(author)
    for key in ('footprint', 'land_use', 'hinterland_km2'):
        if key in author:
            raise SpatialDraftError('几何与腹地以空间草稿为准，请不要在 author 里另给 %s' % key)
    if 'site_name' in author and author['site_name'] != draft['site_name']:
        raise SpatialDraftError('author 里的地点名与空间草稿不一致（草稿是「%s」）'
                                % draft['site_name'])
    author['site_name'] = draft['site_name']
    if draft.get('footprint'):
        author['footprint'] = {'vertices': draft['footprint']['vertices']}
    author['land_use'] = [{'kind': entry['kind'], 'vertices': entry['vertices'],
                           'note': entry.get('note') or ''}
                          for entry in (draft.get('land_use') or [])]
    if draft.get('hinterland_km2') is not None:
        author['hinterland_km2'] = draft['hinterland_km2']
    return author


def to_town_input(store, draft_id, *, author, current_story_revision, sample=None,
                  sampler=None, resolver=None, expected_revision=None):
    """Turn a spatial draft into a ``TownInput`` through the existing adapter.

    Snapshot discipline (a conversion must never mix two drafts):

    * the draft is read **once**; every later step — the environment resolution, the
      sampler arguments, the author geometry — uses that one snapshot, so "source ref A but
      bytes of B" cannot happen;
    * a ``sampler`` passed as ``sampler(draft, lon, lat, window_px, radius_km)`` or the old
      ``sampler(lon, lat, window_px, radius_km)`` form never re-reads the draft itself
      unless it chooses to;
    * ``expected_revision`` is optional but re-checked **after** the (possibly slow) sampling
      and immediately before the input is handed back; a draft that moved in between is
      refused, and nothing is written either way.

    Refusals the draft itself encodes (no supply, footprint/field overlap, undetermined
    overlap, no sampling point) come back as ``status='blocked'`` with the draft untouched;
    a request the author must fix (moved story revision, bad author fields) raises
    :class:`SpatialDraftError`.

    The draft is never modified, published, bound or deleted here, and the story-package
    pointer is never touched.
    """
    draft = _read(store, draft_id)
    _check_expected(draft, expected_revision)
    if current_story_revision is None:
        raise SpatialDraftError('转换必须给出当前故事包版本，用于核对草稿没有过期')
    report = prepare_conversion(draft, current_story_revision=current_story_revision)
    if not report['story_current']:
        raise SpatialDraftError(
            '这个空间草稿基于故事包版本 %s，当前是 %s；旧草稿不能挂到新世界上，'
            '请基于当前版本重新圈选' % (draft.get('story_base_revision'),
                                      current_story_revision))
    spatial = {key: report[key] for key in
               ('supply', 'area_source', 'terrain_area_km2', 'farmland_km2',
                'planned_km2', 'footprint_area_km2', 'conflicts', 'blocking_conflicts',
                'undetermined_pairs', 'overlap_scan', 'footprint_conflicts', 'sampling')}
    spatial['area_approximation'] = draft.get('area_approximation')
    spatial['geometry_budget'] = draft.get('geometry_budget')
    if report['missing']:
        return {'status': 'blocked', 'draft_id': draft['id'],
                'draft_revision': draft['revision'], 'missing': report['missing'],
                'spatial': spatial, 'input': None, 'provenance': None,
                'warnings': list(draft.get('warnings') or []) + report['notes']}

    # Resolve the source from this snapshot, and keep the *same* record for the build.
    environment, record = _resolve_environment(store, draft['environment_ref'], resolver)
    saved = draft['sampling']
    if sampler is not None:
        try:
            effective = sampler(draft, saved['lon'], saved['lat'], saved['window_px'],
                                saved.get('radius_km') or DEFAULT_RADIUS_KM)
        except TypeError:
            effective = sampler(saved['lon'], saved['lat'], saved['window_px'],
                                saved.get('radius_km') or DEFAULT_RADIUS_KM)
        sample_source = 'server_recomputed'
    elif sample is not None:
        effective = sample
        sample_source = 'caller_supplied_checked_against_draft'
    else:
        raise SpatialDraftError('转换必须给出服务端重算的取样（sampler）或一份取样结果')
    checked = validate_sample(effective)
    check_sample_matches(draft, checked)

    author_fields = _author_for(author, draft)
    try:
        built = map_import.build_town_input(record, checked, author_fields,
                                            current_story_revision)
    except map_import.MapImportError as error:
        raise SpatialDraftError(str(error))

    # Last gate before handing the input out: the draft must still be the one we read.
    _check_unchanged(store, draft)

    provenance = dict(built['provenance'])
    provenance['spatial_draft'] = {
        'draft_id': draft['id'], 'draft_revision': draft['revision'],
        'content_hash': draft.get('content_hash'), 'sample_source': sample_source,
        'mapping_source': 'author_spatial_draft',
        'world_basis_id': (draft.get('world_basis_ref') or {}).get('id'),
        'environment_import_id': environment['import_id'],
        'environment_source_sha256': environment['source_sha256'],
        'footprint_area_km2': spatial['footprint_area_km2'],
        'area_approximation': draft.get('area_approximation'),
    }
    warnings = list(built['warnings']) + list(draft.get('warnings') or [])
    if sample_source != 'server_recomputed':
        warnings.append('这次转换用的是调用方给的取样，只核对过与草稿选点一致；'
                        '端点必须先自己做服务端取样，否则气候与地形可能是客户端编的')
    return {'status': 'ready', 'draft_id': draft['id'], 'draft_revision': draft['revision'],
            'missing': [], 'spatial': spatial,
            'input': built['input'].model_dump(mode='json'),
            'provenance': provenance, 'warnings': warnings}


# ==================================================================== projection

def summary(doc):
    """Bounded list/detail view: geometry stays, no pixel arrays ever existed."""
    plan = doc.get('area_plan') or {}
    return {
        'id': doc.get('id'), 'kind': doc.get('kind'), 'schema': doc.get('schema'),
        'site_name': doc.get('site_name'), 'revision': doc.get('revision'),
        'created': doc.get('created'), 'updated': doc.get('updated'),
        'story_base_revision': doc.get('story_base_revision'),
        'request_id': doc.get('request_id'),
        # 这两个是**可编辑的原始字段**，必须能 GET 回来再 PUT 出去（无损往返）。
        # ``city_ref`` 回填了原件里的城市身份；可写输入只有 ``city_id``（三键同源），
        # 前端拿到的解析结果是只读参考，不要把它原样当请求值发回来。
        'note': doc.get('note'),
        'city_ref': doc.get('city_ref'),
        'supply': doc.get('supply'), 'area_source': plan.get('area_source'),
        'terrain_area_km2': plan.get('terrain_area_km2'),
        'farmland_km2': plan.get('farmland_km2'), 'planned_km2': plan.get('planned_km2'),
        'footprint_area_km2': (doc.get('footprint') or {}).get('area_km2'),
        'land_use_summary': doc.get('land_use_summary'),
        'overlaps': doc.get('overlaps'),
        'overlap_scan': doc.get('overlap_scan'),
        'footprint_conflicts': doc.get('footprint_conflicts'),
        'sampling': doc.get('sampling'),
        'environment_ref': doc.get('environment_ref'),
        'world_basis_ref': doc.get('world_basis_ref'),
        'geometry_budget': doc.get('geometry_budget'),
        'area_approximation': doc.get('area_approximation'),
        'content_hash': doc.get('content_hash'),
        'warnings': list(doc.get('warnings') or []),
    }


class SpatialDraftService:
    """Thin wiring for ``app.service.Service``; the module functions stay standalone."""

    def __init__(self, service):
        self.service = service

    @property
    def store(self):
        return self.service.store

    def root(self):
        from pathlib import Path
        # Same rule as the import endpoints: payloads live beside the database.
        return Path(self.store.path).resolve().parent

    def base_revision(self):
        """当前故事版本；**没有世界时返回 None**（作者仍能画、存、CAS 更新草稿）。

        旧实现无条件 ``runtime.package()``，空态下 POST 直接崩。这里不造 dummy 故事：
        空就是空，草稿的 ``story_base_revision`` 实事求是地存 ``None``。
        """
        runtime = self.service.runtime
        return runtime.package()['id'] if runtime.has_world() else None

    def save(self, body):
        return save(self.store, body, story_base_revision=self.base_revision())

    def update(self, draft_id, body, expected_revision):
        return update(self.store, draft_id, body, expected_revision=expected_revision)

    def get(self, draft_id):
        return get(self.store, draft_id)

    def list(self):
        return list_drafts(self.store)

    def prepare(self, draft_id, current_story_revision=None):
        return prepare_conversion(get(self.store, draft_id),
                                  current_story_revision=current_story_revision
                                  or self.base_revision())

    def sampler(self, draft_or_id):
        """Server-side sampler bound to one draft **snapshot**.

        ``to_town_input`` passes the snapshot it already read, so the sampling cannot follow a
        newer draft revision (that would be "resolved source ref A but read B"). It falls back
        to reading by id only when called directly, and then resolves the source with the
        same id/hash check as the conversion. No long transaction is taken: the parse is CPU
        on a freshly re-hashed payload, not a lock.
        """
        from . import civ_atlas_snapshot

        def sample(draft, lon, lat, window_px, radius_km):
            if isinstance(draft, str):
                draft = get(self.store, draft)
            environment, record = _resolve_environment(self.store,
                                                      draft['environment_ref'], None)
            root = self.root()
            if environment['format'] == civ_atlas_snapshot.FORMAT:
                world = civ_atlas_snapshot.load_world(root, record)
                return civ_atlas_snapshot.sample_region(world, lon, lat, window_px, radius_km)
            heightmap = map_import.load_heightmap(root, record)
            return map_import.sample_region(heightmap, lon, lat, window_px, radius_km)

        return sample

    def to_town_input(self, draft_id, *, author, current_story_revision=None, sample=None,
                      expected_revision=None):
        return to_town_input(self.store, draft_id, author=author,
                             current_story_revision=current_story_revision
                             or self.base_revision(),
                             sample=sample, sampler=self.sampler(draft_id),
                             expected_revision=expected_revision)

    def view(self, doc):
        return summary(doc)
