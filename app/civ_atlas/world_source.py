# -*- coding: utf-8 -*-
"""civ-atlas 适配器：``.civsnap`` → 与引擎无关的 :class:`app.world_source.RegionSnapshot`。

本文件是**唯一**允许 import civ-atlas 读取模块的流程相关代码；
``app/world_package_pipeline.py`` 只认识 ``RegionSnapshot``。

复用的现有模块（不重写）：

* ``app/civ_atlas_snapshot``：``parse_container`` / ``read_world``（地块数组与邻接）；
* ``app/civ_atlas_history``：``decode_civ_part`` / ``identity_from`` / ``build``
  （基准年的政区回放、在世国家与国都、聚落、史事 annals）；
* ``app/map_import``：``import_dir``（登记文件所在目录）；
* ``app/terrain_rules.classify_cell``（经 ``world_source.classify_cells``）。

地区选择规则（确定、可复现）
----------------------------
1. 基准年默认取模拟结束年 ``endYear``；政区归属用 ``civ_atlas_history.build`` 回放到基准年。
2. 每个在基准年**有领土**的国家 P 生成一个候选地区 ``civ-polity-<P.id>``：
   P 的邻国 = 与 P 的州在 ``regions.adj`` 上相邻、且归属其他国家的州所属国家；
   按「相邻州对数」降序、国家 id 升序，取前 ``MAX_NEIGHBOURS``（3）个。
   地区 = P 与这些邻国在基准年的全部州（2–4 个国家）。没有邻国的国家不出候选。
3. ``list_regions()`` 按核心国家 id 升序；首轮默认地区 = 列表第一项（``default_region_id``）。
4. 事件 = 窗口 ``[基准年 - window_years, 基准年]`` 内、``a`` / ``b`` 列为国家且至少一方是
   地区内国家的 annals。``event_id`` 由来源身份 + ``annal/<下标>`` 稳定散列得到。

数据口径（缺的不猜）
--------------------
* 地块坐标、海拔、海陆湖、年均温、年降水、群落都取自 ``map`` 块原值。
* ``slope_deg`` / ``relief_m``：本格与相邻陆格比较（格距百余公里，是区域坡度，不是建筑坡度）。
* ``dist_to_sea_km``：与海格相邻记 0（格内有海岸线）；否则取 3 跳内最近海格的格心距离，
  3 跳内没有海时记 3 跳格距的下界。
* 图层：``lake`` = 本格或相邻格是湖；``wetland`` = civ-atlas 群落编号 15（湿地）。
  ``river`` 记为缺：导出的河网是折线，本适配器未做到地块的映射；也不把 ``flux`` 当河流判据。
* 聚落等级：只有基准年的国都能定为 ``capital``，其余 ``missing``（导出没有等级，人口也是 unknown）。
* 政体提示 ``form_hint`` 由上游 ``lineage`` 映射：republic→republic、realm→monarchy、
  khanate→tribal（适配器口径，原值保留在 ``native_form``）。
* 国家名、聚落名都是**导出时**的名字（见 ``civ_atlas_history`` 的说明），不当基准年的事实。
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

from . import history as _history
from . import snapshot as _snapshot
from .. import map_import as _map_import
from .. import world_source as ws
from ..world_basis import INTERVAL

ENGINE = 'civ-atlas'
MAX_NEIGHBOURS = 3
DEFAULT_WINDOW_YEARS = 300
COAST_SEARCH_HOPS = 3
WETLAND_BIOME = 15                 # civ_atlas_snapshot.BIOME_NAMES[15] == '湿地'
LINEAGE_FORM = {'republic': 'republic', 'realm': 'monarchy', 'khanate': 'tribal'}
WATER_NAME = {0: 'land', 1: 'ocean', 2: 'lake'}

#: 事件模板：{a} {b} 国名，{place} 州名或城名，{y} 年。方向不明的种类用中性写法。
KIND_TEXT = {
    'found': '{y}年，{a}立国',
    'rank': '{y}年，{a}晋升位阶',
    'war': '{y}年，{a}与{b}开战',
    'conquer': '{y}年，{a}从{b}手中夺取{place}',
    'peace': '{y}年，{a}与{b}议和',
    'fall': '{y}年，{a}被{b}所灭',
    'capital': '{y}年，{a}迁都{place}',
    'split': '{y}年，{a}与{b}之间发生分裂',
    'merge': '{y}年，{a}与{b}合并',
    'dynasty': '{y}年，{a}改朝换代',
    'sack': '{y}年，{a}洗劫{b}的{place}',
    'ruin': '{y}年，{place}在{a}与{b}的战事中沦为废墟',
    'rebuild': '{y}年，{a}重建{place}',
    'decline': '{y}年，{a}国势衰退',
    'intervene': '{y}年，{a}出手干预',
    'battle': '{y}年，{a}与{b}在{place}交战',
    'sunk': '{y}年，{a}有领土因地形大事沉没',
    'alliance': '{y}年，{a}与{b}结盟',
    'unally': '{y}年，{a}与{b}解除同盟',
    'submit': '{y}年，{a}与{b}之间发生臣服',
    'defect': '{y}年，{a}与{b}之间发生倒戈',
    'famine': '{y}年，{a}发生饥荒',
    'revolt': '{y}年，{a}与{b}之间爆发叛乱',
    'collapse': '{y}年，{a}崩解',
    'plague': '{y}年，{a}爆发瘟疫',
    'warlord': '{y}年，{a}境内出现割据',
    'reclaim': '{y}年，{a}收复割据之地',
    'defy': '{y}年，{a}与{b}对抗',
    'fiscal': '{y}年，{a}陷入财政危机',
    'council': '{y}年，{a}与{b}会盟议事',
    'stand': '{y}年，{a}与{b}之间有一场守城',
    'regent': '{y}年，{a}出现摄政',
    'marry': '{y}年，{a}与{b}联姻',
    'pandemic': '{y}年，{a}遭遇大疫',
    'desolate': '{y}年，{a}境内因瘟疫荒芜',
    'treaty': '{y}年，{a}与{b}立约',
    'breach': '{y}年，{a}与{b}毁约',
    'expire': '{y}年，{a}与{b}的条约期满',
    'neutral': '{y}年，{a}参与共建中立地',
    'exile': '{y}年，{a}与{b}之间发生出奔',
    'keep': '{y}年，{a}维持干预',
}
FALL_SELF = {-1: '{y}年，{a}自行瓦解', -2: '{y}年，{a}亡于地形灾变'}


class CivAtlasSourceError(ValueError):
    pass


def _r(value, digits):
    return None if value is None else round(float(value), digits)


class CivAtlasSource:
    """``WorldSource`` 的 civ-atlas 实现（只读；同一文件、同一参数重复读取结果一致）。"""

    def __init__(self, data, *, base_year=None, window_years=DEFAULT_WINDOW_YEARS,
                 record=None, branch='main', radius_km=_map_import.DEFAULT_RADIUS_KM):
        data = bytes(data)
        self._digest = hashlib.sha256(data).hexdigest()
        if record and record.get('sha256') and record['sha256'] != self._digest:
            raise CivAtlasSourceError('文件内容与登记记录的哈希不符')
        manifest, parts = _snapshot.parse_container(data)
        self._manifest = manifest
        self._world = _snapshot.read_world(manifest, parts)
        self._civ = _history.decode_civ_part(manifest, parts)
        self._radius = float(radius_km)
        record = dict(record or {})
        record.setdefault('sha256', self._digest)
        self._hist_identity = _history.identity_from(manifest, record, branch=branch)
        end_year = self._civ.get('endYear')
        self._base_year = int(end_year if base_year is None else base_year)
        if isinstance(window_years, bool) or not isinstance(window_years, int) or window_years < 0:
            raise CivAtlasSourceError('window_years 必须是非负整数')
        self._window = (max(0, self._base_year - window_years), self._base_year)
        self._doc = None
        self._neighbour_cache = None
        self._cell_area = 4.0 * math.pi * self._radius ** 2 / self._world.cells

    # ----------------------------------------------------------------- 构造
    @classmethod
    def from_path(cls, path, **kwargs):
        return cls(Path(path).read_bytes(), **kwargs)

    @classmethod
    def from_store(cls, store, root, import_id=None, **kwargs):
        """读已登记的 civsnap（``map_import`` 记录）。不给 import_id 时取最新一条 civsnap 记录。"""
        rows = [row for row in store.all('map_import')
                if row.get('format') == _snapshot.FORMAT]
        if import_id:
            rows = [row for row in rows if row.get('id') == import_id]
        if not rows:
            raise CivAtlasSourceError('没有登记的 civ-atlas 世界（.civsnap）')
        rows.sort(key=lambda row: (str(row.get('created') or ''), row.get('id')))
        record = rows[-1]
        target = _map_import.import_dir(Path(root)) / record['file']
        if not target.exists():
            raise CivAtlasSourceError('登记的原件文件不在：%s' % record['file'])
        return cls(target.read_bytes(), record=record, **kwargs)

    # ----------------------------------------------------------------- 协议
    def identity(self):
        snap = self._manifest.get('snapshot') or {}
        return {
            'engine': ENGINE,
            'world_id': self._hist_identity.get('world_id') or 'unknown',
            'version': 'generator-%s/format-%s' % (snap.get('generator'), snap.get('format')),
            'content_hash': self._digest,
            'details': {'import_id': self._hist_identity.get('import_id'),
                        'branch': self._hist_identity.get('branch'),
                        'base_year': self._base_year,
                        'window': list(self._window),
                        'spec_commit': _history.SPEC_COMMIT},
        }

    def capabilities(self):
        return {'cells', 'cells.elevation_m', 'cells.slope_deg', 'cells.relief_m',
                'cells.dist_to_sea_km', 'cells.temperature_c', 'cells.precipitation_mm',
                'cells.area_km2', 'cells.layers.lake', 'cells.layers.wetland',
                'terrains', 'settlements', 'polities', 'polities.territory',
                'polities.capital', 'polities.form_hint', 'events'}

    def list_regions(self):
        doc = self._document()
        owner = self._owners()
        alive = {item['id']: item for item in doc['polities']['items']}
        out = []
        for pid in sorted(alive):
            neighbours = self._neighbours(pid)
            if not neighbours:
                continue
            members = [pid] + neighbours
            out.append({'region_id': 'civ-polity-%d' % pid,
                        'name': '%s及其邻国' % self._polity_name(pid),
                        'bbox': self._bbox([c for c in range(self._world.cells)
                                            if self._cell_owner(c, owner) in members]),
                        'core_polity_id': 'p%d' % pid,
                        'polity_ids': ['p%d' % m for m in members]})
        return out

    def default_region_id(self):
        regions = self.list_regions()
        if not regions:
            raise CivAtlasSourceError('这个世界在基准年没有可选地区（没有相邻的国家）')
        return regions[0]['region_id']

    def region(self, region_id):
        pid = self._parse_region_id(region_id)
        neighbours = self._neighbours(pid)
        if not neighbours:
            raise CivAtlasSourceError('地区 %s 不存在（国家不在世或没有邻国）' % region_id)
        members = [pid] + neighbours
        owner = self._owners()
        identity = self.identity()
        world = self._world

        cell_ids = [c for c in range(world.cells) if self._cell_owner(c, owner) in members]
        cells = [self._cell(c, owner) for c in cell_ids]
        terrains = ws.classify_cells(cells)
        settlements, capitals = self._settlements(members, owner)
        events, actors = self._events(members, identity)
        polities = self._polities(members, actors, owner, capitals)
        snap = ws.RegionSnapshot(
            region_id=region_id, name='%s及其邻国' % self._polity_name(pid),
            bbox=self._bbox(cell_ids), cells=cells, terrains=terrains,
            settlements=settlements, polities=polities, events=events,
            source=identity,
            missing_fields={
                'cells.layers.river': '河网是折线，未映射到地块；flux 不当河流判据',
                'settlements.level': '导出没有聚落等级与逐年人口；只有基准年国都记 capital',
                'settlements.population': '导出没有逐年人口序列',
            },
            notes=['基准年 %d，事件窗口 %d–%d' % (self._base_year, *self._window),
                   '国家名、聚落名为导出时（endYear）的名字',
                   'dist_to_sea_km：与海格相邻记 0（格内有海岸线），否则为格心距离或 3 跳下界',
                   '坡度/起伏为相邻格（约 %.0f km）之间的区域值' % math.sqrt(self._cell_area)])
        return snap.validate()

    # ------------------------------------------------------------- 内部：历史
    def _document(self):
        if self._doc is None:
            self._doc = _history.build(
                self._civ, base_year=self._base_year, window=self._window,
                identity=self._hist_identity, include_regions=True,
                max_events=_history.MAX_ANNALS, max_entities=_history.MAX_ENTITIES)
            replay = self._doc['region_replay']
            if replay.get('status') != INTERVAL or not isinstance(replay.get('polity'), list):
                raise CivAtlasSourceError('基准年 %d 的政区回放不可用：%s'
                                          % (self._base_year, replay.get('reason')))
        return self._doc

    def _owners(self):
        return self._document()['region_replay']['polity']

    def _cell_owner(self, cell, owner):
        region = self._civ['regions']['of'][cell]
        if isinstance(region, int) and 0 <= region < len(owner):
            return owner[region]
        return -1

    def _polity_name(self, pid):
        for row in self._civ.get('polities') or ():
            if row.get('id') == pid:
                return str(row.get('name') or 'polity-%d' % pid)
        return 'polity-%d' % pid

    def _polity_row(self, pid):
        for row in self._civ.get('polities') or ():
            if row.get('id') == pid:
                return row
        return {}

    def _parse_region_id(self, region_id):
        prefix = 'civ-polity-'
        if not isinstance(region_id, str) or not region_id.startswith(prefix):
            raise CivAtlasSourceError('地区 id 格式应为 civ-polity-<国家 id>')
        try:
            return int(region_id[len(prefix):])
        except ValueError:
            raise CivAtlasSourceError('地区 id 格式应为 civ-polity-<国家 id>') from None

    def _neighbours(self, pid):
        if self._neighbour_cache is None:
            owner = self._owners()
            regions = self._civ['regions']
            adj_start, adj = regions['adjStart'], regions['adj']
            pairs = {}
            for region in range(len(owner)):
                a = owner[region]
                if a < 0:
                    continue
                for k in range(adj_start[region], adj_start[region + 1]):
                    b = owner[adj[k]]
                    if b >= 0 and b != a:
                        pairs.setdefault(a, {}).setdefault(b, 0)
                        pairs[a][b] += 1
            self._neighbour_cache = {
                a: [b for b, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]
                for a, counts in pairs.items()}
        return list(self._neighbour_cache.get(pid, [])[:MAX_NEIGHBOURS])

    def _events(self, members, identity):
        doc = self._document()
        regions = self._civ['regions']
        names = regions.get('name') or []
        settlement_names = {row.get('id'): row.get('name')
                            for row in self._civ.get('settlements') or ()}
        member_set = set(members)
        events, actors = [], set()
        for item in doc['annals']['events']:
            if not item.get('kind_known') or item.get('a_means') != 'polity':
                continue
            a = item.get('a_id')
            b = item.get('b_id') if item.get('b_means') == 'polity' else None
            if a is None or not ({a, b} & member_set):
                continue
            year = int(math.floor(item['year']))
            place = None
            if item.get('settlement_ref'):
                sid = int(item['settlement_ref'].rsplit('/', 1)[1])
                place = settlement_names.get(sid)
            region = item.get('region')
            if place is None and item['kind'] not in ('peace',) and isinstance(region, int) \
                    and 0 <= region < len(names):
                place = names[region]
            kind = item['kind']
            template = KIND_TEXT[kind]
            raw_b = (item.get('raw_columns') or {}).get('b')
            if kind == 'fall' and b is None:
                template = FALL_SELF.get(raw_b, '{y}年，{a}灭亡')
            if '{b}' in template and b is None:
                template = template.replace('从{b}手中', '').replace('{b}的', '') \
                    .replace('与{b}之间', '').replace('与{b}', '').replace('{b}', '')
            if '{place}' in template and not place:
                template = template.replace('{place}', '某地')
            text = template.format(y=year, a=self._polity_name(a),
                                   b=self._polity_name(b) if b is not None else '',
                                   place=place or '')
            ids = ['p%d' % a] + (['p%d' % b] if b is not None else [])
            actors.update(x for x in (a, b) if x is not None)
            events.append({'event_id': ws.make_event_id(identity, 'annal/%d' % item['index']),
                           'year': year, 'year_exact': item['year'], 'kind': kind,
                           'actors': ids, 'place': place, 'text': text,
                           'native_ref': item['ref']})
        events.sort(key=lambda e: (e['year_exact'], e['event_id']))
        return events, actors

    def _polities(self, members, actors, owner, capitals):
        doc = self._document()
        alive = {item['id']: item for item in doc['polities']['items']}
        out = []
        for pid in sorted(set(members) | set(actors)):
            row = self._polity_row(pid)
            item = alive.get(pid)
            lineage = row.get('lineage')
            in_region = pid in members
            territory = ws.missing('不在本地区，未取疆域')
            if in_region:
                region_ids = [r for r in range(len(owner)) if owner[r] == pid]
                territory = {'region_ids': ['r%d' % r for r in region_ids],
                             'region_count': len(region_ids)}
            if in_region:
                capital = capitals.get(pid) or ws.missing(
                    '基准年国都不在本地区的聚落里，或导出没有该年的 capitals[]'
                    if item is not None else '基准年不在世，没有国都')
            else:
                capital = ws.missing('不在本地区，未取国都' if item is not None
                                     else '基准年不在世，没有国都')
            founded = row.get('founded')
            ended = row.get('ended')
            out.append({
                'polity_id': 'p%d' % pid, 'name': self._polity_name(pid),
                'in_region': in_region, 'alive_at_base_year': item is not None,
                'founded': None if founded is None else int(math.floor(founded)),
                'ended': None if ended is None else int(math.floor(ended)),
                'capital': capital, 'territory': territory,
                'form_hint': LINEAGE_FORM.get(lineage, ws.MISSING),
                'native_form': lineage,
                'culture_native_id': row.get('culture'),
            })
        return out

    def _settlements(self, members, owner):
        doc = self._document()
        world = self._world
        alive_polities = {item['id']: item for item in doc['polities']['items']}
        capital_of = {}
        for pid, item in alive_polities.items():
            ref = item.get('capital_ref')
            if ref:
                capital_of[int(ref.rsplit('/', 1)[1])] = pid
        raw = {row.get('id'): row for row in self._civ.get('settlements') or ()}
        out, capitals = [], {}
        for item in doc['settlements']['items']:
            cell = item.get('cell')
            if not isinstance(cell, int) or not 0 <= cell < world.cells:
                continue
            pid = self._cell_owner(cell, owner)
            if pid not in members:
                continue
            sid = item['id']
            is_capital = capital_of.get(sid) == pid
            entry = {'settlement_id': 's%d' % sid, 'name': item['display_name'],
                     'level': 'capital' if is_capital else ws.MISSING,
                     'polity_id': 'p%d' % pid, 'cell_id': 'c%d' % cell,
                     'lon': _r(world.lon[cell], 4), 'lat': _r(world.lat[cell], 4),
                     'founded': int(math.floor(item['founded'])),
                     'port': bool((raw.get(sid) or {}).get('port'))}
            out.append(entry)
            if is_capital:
                capitals[pid] = {'settlement_id': entry['settlement_id'], 'name': entry['name']}
        out.sort(key=lambda s: int(s['settlement_id'][1:]))
        return out, capitals

    # ------------------------------------------------------------- 内部：地块
    def _adjacent(self, cell):
        adj_start, adj = self._world.neighbours
        if adj_start is None:
            return []
        return [adj[k] for k in range(adj_start[cell], adj_start[cell + 1])]

    def _distance_km(self, a, b):
        w = self._world
        return _snapshot._angular_distance(w.lon[a], w.lat[a], w.lon[b], w.lat[b]) * self._radius

    def _water(self, cell):
        return 0 if self._world.water is None else self._world.water[cell]

    def _cell(self, cell, owner):
        w = self._world
        elev = w.elevation[cell] if w.elevation else None
        water = self._water(cell)
        near = self._adjacent(cell)
        land = [o for o in near if self._water(o) != 1]
        slope = relief = None
        if elev is not None and land:
            slopes = []
            for o in land:
                metres = self._distance_km(cell, o) * 1000.0
                if metres >= 1.0:
                    slopes.append(math.degrees(math.atan(abs(w.elevation[o] - elev) / metres)))
            slope = max(slopes) if slopes else None
            heights = [elev] + [w.elevation[o] for o in land]
            relief = max(heights) - min(heights)
        if w.water is None:
            dist = None
        elif any(self._water(o) == 1 for o in near) or water == 1:
            dist = 0.0
        else:
            ring = _snapshot._ring(w, cell, COAST_SEARCH_HOPS)
            sea = [o for o in ring if self._water(o) == 1]
            if sea:
                dist = min(self._distance_km(cell, o) for o in sea)
            else:
                dist = COAST_SEARCH_HOPS * math.sqrt(self._cell_area)
        layers = {}
        if w.water is not None:
            layers['lake'] = water == 2 or any(self._water(o) == 2 for o in near)
        if w.biome is not None:
            layers['wetland'] = w.biome[cell] == WETLAND_BIOME
        pid = self._cell_owner(cell, owner)
        return {
            'cell_id': 'c%d' % cell, 'lon': _r(w.lon[cell], 4), 'lat': _r(w.lat[cell], 4),
            'is_sea': water == 1, 'water': WATER_NAME.get(water, 'unknown'),
            'elevation_m': _r(elev, 1), 'slope_deg': _r(slope, 3), 'relief_m': _r(relief, 1),
            'dist_to_sea_km': _r(dist, 1),
            'temperature_c': _r(w.temperature[cell], 2) if w.temperature else None,
            'precipitation_mm': _r(w.precipitation[cell], 1) if w.precipitation else None,
            'area_km2': _r(self._cell_area, 1), 'layers': layers,
            'polity_id': 'p%d' % pid if pid >= 0 else None,
            'region_ref': 'r%d' % self._civ['regions']['of'][cell],
        }

    def _bbox(self, cells):
        w = self._world
        if not cells:
            return {'lon_min': None, 'lon_max': None, 'lat_min': None, 'lat_max': None}
        lons = [w.lon[c] for c in cells]
        lats = [w.lat[c] for c in cells]
        return {'lon_min': _r(min(lons), 4), 'lon_max': _r(max(lons), 4),
                'lat_min': _r(min(lats), 4), 'lat_max': _r(max(lats), 4),
                'note': '经度按 −180…180 直接取最值，跨日界线的地区会显得很宽'}
