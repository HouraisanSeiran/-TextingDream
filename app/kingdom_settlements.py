"""Published kingdom background -> reviewed town sites and planned land routes.

The planner reuses the frozen terrain and the existing single-town generator.
Unknown water, soil, building and social inputs require an author's declaration.
Routes are proposals on the source grid, never claims about built historical roads.
"""
from copy import deepcopy
import hashlib
import heapq
import json
import math
from pathlib import Path
import re

import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from scipy import ndimage

from .background_geography import source_pin, _window_values
from .civ_sim.geography import full_crop_bounds
from .civ_sim.schema import MAX_CELLS
from .knowledge import atomic_text
from .runtime import now
from .terrain_source import LAND
from .town_schema import DraftRequest, TownInput
from .towns_store import content_hash


PLAN_KIND = 'kingdom_settlement_plan'
VERSION_KIND = 'kingdom_settlement_version'
SCHEMA = 'kingdom_settlements_v1'
NEIGHBORS = ((-1, 0), (0, -1), (0, 1), (1, 0))


class GenerateSettlements(BaseModel):
    model_config = ConfigDict(extra='forbid')
    seed: str = Field(default='kingdom-1', pattern=r'^[A-Za-z0-9_-]{4,64}$')
    count: int = Field(default=3, ge=1, le=24, strict=True)
    min_distance_m: float = Field(default=1000., ge=0, le=10000000,
                                  allow_inf_nan=False)


def _digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode('utf-8')).hexdigest()


def _metric(grid, cell):
    z, x = cell
    return (float(grid['first_xz_m'][0] + x * grid['spacing_m']),
            float(grid['first_xz_m'][1] + z * grid['spacing_m']))


def _slopes(elevation, spacing):
    gradients = []
    for axis in (0, 1):
        gradients.append(np.gradient(elevation, spacing, axis=axis)
                         if elevation.shape[axis] > 1 else np.zeros_like(elevation))
    return np.degrees(np.arctan(np.hypot(*gradients)))


def _route(start, end, traversable, elevation, spacing):
    """A* with four-neighbour land cells; fixed ordering makes equal costs stable."""
    start, end = tuple(start), tuple(end)
    frontier = [(0., 0., start)]
    cost = {start: 0.}
    parent = {}
    while frontier:
        _, distance, node = heapq.heappop(frontier)
        if distance != cost[node]:
            continue
        if node == end:
            cells = [node]
            while node != start:
                node = parent[node]
                cells.append(node)
            return [list(cell) for cell in reversed(cells)]
        for dz, dx in NEIGHBORS:
            target = (node[0] + dz, node[1] + dx)
            if not (0 <= target[0] < traversable.shape[0] and
                    0 <= target[1] < traversable.shape[1] and traversable[target]):
                continue
            step = spacing + 8. * abs(float(elevation[target] - elevation[node]))
            proposed = distance + step
            if proposed >= cost.get(target, math.inf):
                continue
            cost[target] = proposed
            parent[target] = node
            remaining = (abs(target[0] - end[0]) + abs(target[1] - end[1])) * spacing
            heapq.heappush(frontier, (proposed + remaining, proposed, target))
    return None


class KingdomSettlements:
    def __init__(self, service):
        self.service = service

    @property
    def backgrounds(self):
        return self.service.world_package.backgrounds

    def _context(self, version_id, polity_id):
        document = self.backgrounds.get_version(version_id)
        context = self.backgrounds.town_context(version_id, polity_id)
        return document, context

    def _bundle(self, document):
        bundle = self.backgrounds.registry.get(document['bundle_id'])
        if source_pin(bundle) != document['source']:
            raise ValueError('地图来源已变化，不能继续生成该背景版本的城镇')
        return bundle

    def _terrain(self, document, context):
        bundle = self._bundle(document)
        grid = context['polity']['geometry']['grid']
        if bundle.grids['terrain'] != grid:
            raise ValueError('王国疆域与地图栅格不一致')
        shape = tuple(grid['shape_zx'])
        if math.prod(shape) > MAX_CELLS:
            raise ValueError('城镇规划地图超过现有栅格读取上限')
        crop = bundle.environment.crop(*full_crop_bounds(grid['first_xz_m'],
                    grid['spacing_m'], shape), layers=('status', 'elevation_m'), max_cells=MAX_CELLS)
        elevation = np.asarray(crop['elevation_m'], dtype=float)
        status = np.asarray(crop['status'])
        if elevation.shape != shape or status.shape != shape:
            raise ValueError('地形裁切形状与已发布疆域不一致')
        mask = np.zeros(shape, bool)
        for z, x0, x1 in context['polity']['geometry']['spans']:
            mask[z, x0:x1] = True
        mask &= (status == LAND) & np.isfinite(elevation)
        slope = _slopes(elevation, grid['spacing_m'])
        eligible = mask & np.isfinite(slope) & (slope <= 60) & (elevation >= -500) & (elevation <= 9000)
        bundle.check_unchanged()
        return bundle, grid, elevation, slope, mask, eligible

    def _climate(self, bundle, grid, cell):
        x_m, z_m = _metric(grid, cell)
        result = {'temperature_c': None, 'precipitation_mm': None, 'climate_sources': {}}
        fields = (
            ('temperature_c', 'temperature_c', False, 'mean'),
            ('temperature_c', 'monthly_temperature_c', True, 'mean'),
            ('precipitation_mm', 'precipitation_mm_yr', False, 'sum'),
            ('precipitation_mm', 'monthly_precipitation_mm', True, 'sum'),
        )
        for target, name, monthly, reduction in fields:
            if result[target] is not None:
                continue
            for group in ('climate', 'environment', 'terrain'):
                spec = bundle.specs.get(group, {}).get(name)
                if not spec or not spec.get('queryable'):
                    continue
                unit = str(spec.get('unit', '')).lower().replace(' ', '')
                expected = ('c', '°c', 'degc', 'celsius', 'degree_celsius') if target == 'temperature_c' else (
                    'mm', 'mm/yr', 'mm/year', 'mmyr-1', 'mmmonth-1', 'mm/month')
                if unit not in expected:
                    continue
                native = bundle.grids[group]
                spacing = native['spacing_m']
                nx = int(math.floor((x_m - native['first_xz_m'][0]) / spacing + .5))
                nz = int(math.floor((z_m - native['first_xz_m'][1]) / spacing + .5))
                if not (0 <= nz < native['shape_zx'][0] and 0 <= nx < native['shape_zx'][1]):
                    continue
                values = np.asarray(_window_values(bundle, group, name, [nz, nx, nz + 1, nx + 1],
                                    tuple(range(1, 13)) if monthly else (1,)), dtype=float).reshape(-1)
                if values.size != (12 if monthly else 1) or not np.isfinite(values).all():
                    continue
                value = float(values.mean() if reduction == 'mean' else values.sum())
                bound = (-55, 55) if target == 'temperature_c' else (0, 6000)
                if not bound[0] <= value <= bound[1]:
                    continue
                result[target] = value
                result['climate_sources'][target] = {'field': group + '.' + name,
                    'unit': spec.get('unit'), 'cell_zx': [nz, nx], 'months': list(range(1, 13)) if monthly else [],
                    'aggregation': ('equal-month mean' if reduction == 'mean' else 'annual sum') if monthly else 'saved annual value',
                    'native_grid': deepcopy(native)}
                break
        return result

    def generate(self, version_id, polity_id, request):
        request = GenerateSettlements.model_validate(request).model_dump()
        document, context = self._context(version_id, polity_id)
        identity = 'ksp_' + _digest([version_id, context['polity']['id'], request])[:24]
        previous = self.service.store.get(PLAN_KIND, identity)
        if previous is not None:
            self._bundle(document)
            return previous
        bundle, grid, elevation, slope, mask, eligible = self._terrain(document, context)
        candidates = np.argwhere(eligible)
        if not candidates.size:
            raise ValueError('王国内没有具备有效陆地高程和坡度的城镇候选格')
        labels, _ = ndimage.label(mask, structure=ndimage.generate_binary_structure(2, 1))
        config = document['generation']['config']
        side = config['block_cells']
        provinces = document['simulation']['chronicle'].get('regions', [])
        region_at = {tuple(row['block_zx']): row['id'] for row in provinces}
        capital = context['polity']['capital_region_id']
        capital_cells = [tuple(map(int, cell)) for cell in candidates
                         if region_at.get((int(cell[0]) // side, int(cell[1]) // side)) == capital]
        if not capital_cells:
            raise ValueError('首都州内没有有效城镇候选格；不能把首都静默移到其他州')
        def tie(cell):
            return _digest([request['seed'], list(map(int, cell))])
        first = min(capital_cells, key=lambda cell: (float(slope[cell]), tie(cell)))
        chosen = [first]
        distance_sq = ((candidates[:, 0] - first[0]) ** 2 + (candidates[:, 1] - first[1]) ** 2).astype(float)
        threshold = (request['min_distance_m'] / grid['spacing_m']) ** 2
        while len(chosen) < request['count']:
            available = distance_sq >= threshold
            available &= distance_sq > 0
            if not available.any():
                break
            # Farthest coverage first, then flatter terrain, then deterministic seed tie.
            max_distance = distance_sq[available].max()
            finalists = candidates[available & (distance_sq == max_distance)]
            cell = min((tuple(map(int, row)) for row in finalists),
                       key=lambda row: (float(slope[row]), tie(row)))
            chosen.append(cell)
            new_distance = (candidates[:, 0] - cell[0]) ** 2 + (candidates[:, 1] - cell[1]) ** 2
            distance_sq = np.minimum(distance_sq, new_distance)
        sites = []
        for index, cell in enumerate(chosen):
            x_m, z_m = _metric(grid, cell)
            site_id = 'site_' + _digest([identity, cell])[:20]
            sites.append({'id': site_id, 'name': ('首都候选点' if index == 0 else '聚落候选点 %d' % index),
                          'rank': index, 'role': 'capital_candidate' if index == 0 else 'settlement_candidate',
                          'cell_zx': list(cell), 'x_m': x_m, 'z_m': z_m,
                          'province_id': region_at.get((cell[0] // side, cell[1] // side)),
                          'component': int(labels[cell]),
                          'observations': {'elevation_m': float(elevation[cell]),
                              'slope_deg': float(slope[cell]), **self._climate(bundle, grid, cell)}})
        roads, disconnected = [], []
        for site in sites[1:]:
            same = [other for other in sites[:site['rank']] if other['component'] == site['component']]
            if not same:
                disconnected.append({'site_id': site['id'], 'reason': 'separate_land_component',
                                     'requires': '作者另行规划跨海或其他交通，不自动造桥'})
                continue
            other = min(same, key=lambda row: ((row['x_m'] - site['x_m']) ** 2 +
                                               (row['z_m'] - site['z_m']) ** 2, row['id']))
            cells = _route(other['cell_zx'], site['cell_zx'], mask, elevation, grid['spacing_m'])
            if cells is None:
                disconnected.append({'site_id': site['id'], 'reason': 'no_supported_land_path'})
                continue
            roads.append({'id': 'route_' + _digest([other['id'], site['id']])[:20],
                          'from_site': other['id'], 'to_site': site['id'], 'status': 'planned',
                          'cells_zx': cells, 'points_xz_m': [list(_metric(grid, cell)) for cell in cells],
                          'length_m': (len(cells) - 1) * float(grid['spacing_m']),
                          'basis': '4-neighbour LAND path; distance + 8*absolute elevation change; design estimate'})
        bundle.check_unchanged()
        plan = {'schema': SCHEMA, 'id': identity, 'revision': 0, 'created': now(), 'status': 'draft',
                'background_version_id': version_id, 'background_content_hash': document['content_hash'],
                'background_year': document['background_year'], 'polity_id': context['polity']['id'],
                'polity_name': context['polity']['name'], 'source': deepcopy(document['source']),
                'seed': request['seed'], 'request': request, 'grid': deepcopy(grid), 'sites': sites,
                'roads': roads, 'disconnected': disconnected, 'towns': {}, 'published': [],
                'warnings': ([] if len(sites) == request['count'] else ['陆地范围和最小间距不能容纳全部请求聚落']),
                'semantics': 'author settlement and route proposals; not past settlement or constructed-road facts'}
        self.service.store.put(PLAN_KIND, identity, plan)
        return plan

    def list(self, version_id):
        self.backgrounds.get_version(version_id)
        return [row for row in self.service.store.all(PLAN_KIND)
                if row['background_version_id'] == version_id]

    def get(self, plan_id):
        plan = self.service.store.get(PLAN_KIND, plan_id)
        if plan is None:
            raise ValueError('王国聚落规划不存在')
        return plan

    def _site(self, plan_id, site_id):
        plan = self.get(plan_id)
        site = next((row for row in plan['sites'] if row['id'] == site_id), None)
        if site is None:
            raise ValueError('聚落候选点不属于该规划')
        document, context = self._context(plan['background_version_id'], plan['polity_id'])
        if document['content_hash'] != plan['background_content_hash']:
            raise ValueError('背景版本内容已变化')
        self._bundle(document)
        return plan, site, document, context

    def _binding(self, plan, site, document, context):
        return {'version_id': document['version_id'], 'content_hash': document['content_hash'],
                'polity_id': plan['polity_id'], 'plan_id': plan['id'], 'site_id': site['id'],
                'x_m': site['x_m'], 'z_m': site['z_m'], 'background_year': plan['background_year'],
                'context': deepcopy(context)}

    def site_input(self, plan_id, site_id):
        plan, site, document, context = self._site(plan_id, site_id)
        sample = {key: site['observations'][key] for key in
                  ('elevation_m', 'slope_deg', 'temperature_c', 'precipitation_mm')}
        sample.update(freshwater=None, soil_fertility=None, flood_risk=None, area_km2=None, coordinates=None)
        template = {'story_revision': document['version_id'],
                    'seed': _digest([plan['seed'], site_id])[:24], 'site': 'selected_location',
                    'site_name': site['name'], 'site_location_id': site_id, 'region': plan['polity_name'],
                    'founded_period': '未定（不从候选点推断建城年份）',
                    'map': {'input_version': plan['id'], 'coordinate_system': document['geography'].get('coordinate_system', 'X/Z metres'),
                            'scale': '原生格距 %s m' % plan['grid']['spacing_m'], 'source': 'external_adapter'},
                    'terrain': sample,
                    'water': {'source': None, 'reliability': None, 'daily_capacity_l': None,
                              'storage': 'none', 'distance_km': None},
                    'transport': {'road': 'none', 'water_route': False, 'portage': False,
                                  'seasonal_closed_days': 0, 'nearest_market_days': 0},
                    'resources': [], 'materials': [], 'technology': [], 'cultures': [], 'peoples': [],
                    'social_mode': 'artistic_extrapolation',
                    'artistic': {'prototypes': [], 'inventions': [], 'design_goal': ''},
                    'imports': [], 'bindings': [], 'notes': '缺项由作者补充；规划道路不表示已经建成。',
                    'background': self._binding(plan, site, document, context)}
        unknown = ['terrain.' + key for key, value in sample.items() if value is None and key != 'coordinates']
        return {'template': template, 'required_fields': unknown + ['water', 'materials', 'cultures', 'peoples', 'artistic'],
                'observations': deepcopy(site['observations']), 'background_context': context}

    def validate_entry(self, entry):
        binding = entry.get('background')
        if not binding:
            return
        plan, site, document, context = self._site(binding['plan_id'], binding['site_id'])
        if binding != self._binding(plan, site, document, context):
            raise ValueError('城镇背景来源、国家、候选点或固定上下文不匹配')
        template = self.site_input(plan['id'], site['id'])['template']
        for key in ('story_revision', 'seed', 'site', 'site_location_id', 'region', 'map'):
            if entry.get(key) != template[key]:
                raise ValueError('城镇输入改写了固定来源字段：' + key)
        if entry['terrain'].get('coordinates') is not None:
            raise ValueError('背景地图使用米制坐标，不能填入旧版经纬度字段')
        for key in ('elevation_m', 'slope_deg', 'temperature_c', 'precipitation_mm'):
            if site['observations'][key] is not None and entry['terrain'][key] != site['observations'][key]:
                raise ValueError('城镇输入改写了已冻结地图观测：' + key)
        manifest = document['element_manifest'].get('elements', [])
        allowed = {row['element_id']: row for row in manifest}
        allowed.update({row['ref']: row for row in manifest})
        for row in entry.get('bindings', []):
            element = allowed.get(row['id'])
            if (element is None or str(row['version']) != str(element['version']) or
                    row.get('state', 'existing') != element['state']):
                raise ValueError('城镇绑定的资料、版本或采用状态不在固定背景采用清单中')

    @staticmethod
    def _revision(plan, expected_revision):
        if type(expected_revision) is not int or plan['revision'] != expected_revision:
            raise ValueError('王国聚落规划已更新，请刷新后重试')

    def _commit(self, plan, expected_revision):
        with self.service.store.transact() as db:
            record = db.execute('SELECT body FROM documents WHERE kind=? AND id=?',
                                (PLAN_KIND, plan['id'])).fetchone()
            if record is None:
                raise ValueError('王国聚落规划不存在')
            self._revision(json.loads(record[0]), expected_revision)
            plan['revision'] = expected_revision + 1
            db.execute('INSERT OR REPLACE INTO documents VALUES(?,?,?)',
                       (PLAN_KIND, plan['id'], json.dumps(plan, ensure_ascii=False, separators=(',', ':'))))
        return plan

    def create_town(self, plan_id, site_id, entry, expected_revision):
        plan, site, document, context = self._site(plan_id, site_id)
        self._revision(plan, expected_revision)
        if plan['status'] != 'draft':
            raise ValueError('已发布规划不可修改，请使用新种子建立新规划')
        entry = deepcopy(entry)
        entry['background'] = self._binding(plan, site, document, context)
        entry = TownInput.model_validate(entry).model_dump(mode='json')
        self.validate_entry(entry)
        existing = plan['towns'].get(site_id)
        if existing:
            draft = self.service.towns.get_draft(existing['draft_id'])
            if draft['input'] == entry:
                return {'plan': plan, 'draft': draft}
            raise ValueError('该候选点已有城镇草稿，请编辑已有草稿或建立新规划')
        draft = self.service.towns.create(DraftRequest(input=entry))
        plan['towns'][site_id] = {'draft_id': draft['id']}
        return {'plan': self._commit(plan, expected_revision), 'draft': draft}

    def publish(self, plan_id, expected_revision):
        plan = self.get(plan_id)
        self._revision(plan, expected_revision)
        if plan['published']:
            return {'plan': plan, 'version': self.get_version(plan['published'][-1])}
        document, context = self._context(plan['background_version_id'], plan['polity_id'])
        self._bundle(document)
        versions = []
        for site in plan['sites']:
            link = plan['towns'].get(site['id'])
            if not link:
                raise ValueError('请先为每个聚落候选点生成并发布城镇')
            draft = self.service.towns.get_draft(link['draft_id'])
            if not draft.get('published'):
                raise ValueError('城镇草稿尚未发布：' + site['id'])
            self.validate_entry(draft['input'])
            version = self.service.towns.get_version(draft['published'][-1])
            if content_hash(self.service.towns.snapshot(draft)) != version['content_hash']:
                raise ValueError('城镇草稿已编辑但尚未发布新版本：' + site['id'])
            versions.append({'site_id': site['id'], 'version': version})
        body = {'schema': SCHEMA, 'background_version_id': document['version_id'],
                'background_content_hash': document['content_hash'], 'background_context': context,
                'plan': deepcopy(plan), 'town_versions': versions, 'can_start': False,
                'route_status': 'author_confirmed_plan; not constructed or historical road facts'}
        version_id = 'ksv_' + _digest(body)[:24]
        version = {**body, 'id': version_id, 'created': now()}
        version['content_hash'] = _digest(version)
        folder = Path(self.service.runtime.library) / document['folder'] / 'kingdoms'
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / (version_id + '.json')
        if path.exists():
            version = self._read_version(path)
        else:
            atomic_text(path, json.dumps(version, ensure_ascii=False, indent=2) + '\n')
        self.service.store.put(VERSION_KIND, version_id, version)
        plan['published'] = [version_id]
        plan['status'] = 'published'
        return {'plan': self._commit(plan, expected_revision), 'version': version}

    @staticmethod
    def _read_version(path):
        body = json.loads(path.read_text(encoding='utf-8'))
        recorded = body.pop('content_hash', None)
        if body.get('schema') != SCHEMA or recorded != _digest(body):
            raise ValueError('王国城镇版本格式或内容哈希不符')
        body['content_hash'] = recorded
        return body

    def versions(self, background_version_id):
        document = self.backgrounds.get_version(background_version_id)
        folder = Path(self.service.runtime.library) / document['folder'] / 'kingdoms'
        return [self._read_version(path) for path in sorted(folder.glob('ksv_*.json'))]

    def get_version(self, version_id):
        if not re.fullmatch(r'ksv_[a-f0-9]{24}', version_id):
            raise ValueError('王国城镇版本 ID 无效')
        for path in Path(self.service.runtime.library).glob('背景_bgv_*/kingdoms/' + version_id + '.json'):
            body = self._read_version(path)
            if body['id'] != version_id:
                raise ValueError('王国城镇版本身份不符')
            return body
        raise ValueError('王国城镇版本不存在')
