# -*- coding: utf-8 -*-
"""与地图引擎无关的「地区快照」RegionSnapshot 与 WorldSource 适配器协议。

设计见 ``docs/world-package-pipeline.md`` §2–3。分层：

    世界引擎（civ-atlas / 以后的 Terragenesis 冻结产品）
            │  只经适配器读（适配器是唯一可以 import 引擎模块的地方）
            ▼
    WorldSource 适配器 ──► RegionSnapshot（纯数据、带来源身份）
            ▼
    app/world_package_pipeline.py（只认识本模块，不 import 任何引擎模块）

本模块只放数据结构、校验与引擎无关的小工具（稳定事件 id、产地判定封装），
不读文件、不连网、不碰数据库。

缺的数据不猜：适配器给不出的字段写成 :func:`missing` 标记 ``{'status': 'missing',
'reason': …}``；逐地块缺某个数值时该值为 ``None``，并在 ``missing_fields`` 里写明原因。
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from . import terrain_rules

SCHEMA = 'region_snapshot_v1'
MISSING = 'missing'

#: 快照的五个数据字段（``source`` 另算）。每个要么是列表，要么是 missing 标记。
FIELDS = ('cells', 'terrains', 'settlements', 'polities', 'events')

#: ``capabilities()`` 可以声明的字段名（适配器只声明它真能给的）。
CAPABILITY_NAMES = (
    'cells', 'cells.elevation_m', 'cells.slope_deg', 'cells.relief_m',
    'cells.dist_to_sea_km', 'cells.temperature_c', 'cells.precipitation_mm',
    'cells.area_km2', 'cells.layers.lake', 'cells.layers.river', 'cells.layers.wetland',
    'terrains', 'settlements', 'settlements.level', 'polities', 'polities.territory',
    'polities.capital', 'polities.form_hint', 'events',
)

#: 聚落等级的通用词表；适配器给不出时写字符串 ``'missing'``。
SETTLEMENT_LEVELS = ('hamlet', 'town', 'city', 'capital')

#: 国家政体提示的通用词表（与 ``docs/world-setting.md`` 的 ``polity:*`` 标签同名）。
FORM_HINTS = ('monarchy', 'empire', 'republic', 'city_state', 'theocracy', 'tribal', 'merchant')

IDENTITY_KEYS = ('engine', 'world_id', 'version', 'content_hash')


class SnapshotError(ValueError):
    """快照结构不合规（适配器写错了），流程拒绝继续。"""


def missing(reason):
    return {'status': MISSING, 'reason': str(reason)}


def is_missing(value):
    return isinstance(value, dict) and value.get('status') == MISSING


def canonical(value):
    """稳定序列化：同样的数据永远得到同样的字节（用于摘要与比较）。"""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                      allow_nan=False)


def make_event_id(identity, native_key):
    """稳定事件 id：同一世界、同一版本、同一份数据、同一个原生键 → 同一个 id。

    ``native_key`` 是适配器自己的稳定键（例如 civ-atlas 的 ``annal/<下标>``）。
    身份里任何一项变化（换了数据文件、换了版本），id 都会变，旧叙述随之失效。
    """
    identity = identity if isinstance(identity, dict) else {}
    basis = '|'.join(str(identity.get(key) or '') for key in IDENTITY_KEYS)
    digest = hashlib.sha256((basis + '|' + str(native_key)).encode('utf-8')).hexdigest()
    return 'ev_' + digest[:16]


def classify_cells(cells):
    """逐地块调用 ``terrain_rules.classify_cell``（规则与引擎无关，两种引擎共用）。

    地块缺海拔或纬度时不判，记为 missing，不猜。
    """
    out = []
    for cell in cells:
        elev, lat = cell.get('elevation_m'), cell.get('lat')
        if elev is None or lat is None:
            out.append({'cell_id': cell['cell_id'], 'terrains': [], 'suitable': [],
                        'candidates': [], 'assumed': [],
                        'missing': ['全部：缺海拔或纬度，不判定产地']})
            continue
        result = terrain_rules.classify_cell(
            is_sea=bool(cell.get('is_sea')), elev_m=elev, lat_deg=lat,
            slope_deg=cell.get('slope_deg'), relief_m=cell.get('relief_m'),
            dist_to_sea_km=cell.get('dist_to_sea_km'), temp_c=cell.get('temperature_c'),
            precip_mm=cell.get('precipitation_mm'), layers=cell.get('layers') or None)
        out.append({'cell_id': cell['cell_id'], **result})
    return out


@runtime_checkable
class WorldSource(Protocol):
    """世界引擎适配器。换引擎时只新写一个实现，流程代码不改。"""

    def identity(self) -> dict:
        """``{engine, world_id, version, content_hash}``（可另带 ``details``）。"""

    def list_regions(self) -> list:
        """``[{region_id, name, bbox, ...}]``，顺序必须确定。"""

    def region(self, region_id) -> 'RegionSnapshot':
        """该地区的快照；同一身份下重复调用必须得到逐字节一致的数据。"""

    def capabilities(self) -> set:
        """能提供的字段名集合（取自 :data:`CAPABILITY_NAMES`）。"""


@dataclass
class RegionSnapshot:
    region_id: str
    name: str
    bbox: dict
    cells: object
    terrains: object
    settlements: object
    polities: object
    events: object
    source: dict
    missing_fields: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)

    # ------------------------------------------------------------ 序列化
    def to_dict(self):
        return {'schema': SCHEMA, 'region_id': self.region_id, 'name': self.name,
                'bbox': copy.deepcopy(self.bbox),
                **{key: copy.deepcopy(getattr(self, key)) for key in FIELDS},
                'source': copy.deepcopy(self.source),
                'missing_fields': copy.deepcopy(self.missing_fields),
                'notes': list(self.notes)}

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or data.get('schema') != SCHEMA:
            raise SnapshotError('不是 %s 快照' % SCHEMA)
        return cls(region_id=data['region_id'], name=data['name'], bbox=data['bbox'],
                   cells=data['cells'], terrains=data['terrains'],
                   settlements=data['settlements'], polities=data['polities'],
                   events=data['events'], source=data['source'],
                   missing_fields=data.get('missing_fields') or {},
                   notes=data.get('notes') or [])

    def digest(self):
        return hashlib.sha256(canonical(self.to_dict()).encode('utf-8')).hexdigest()

    # ------------------------------------------------------------ 便捷读
    def has(self, key):
        return not is_missing(getattr(self, key))

    def polity_list(self):
        return [] if is_missing(self.polities) else list(self.polities)

    def region_polities(self):
        return [p for p in self.polity_list() if p.get('in_region')]

    def event_list(self):
        return [] if is_missing(self.events) else list(self.events)

    def event_index(self):
        return {event['event_id']: event for event in self.event_list()}

    def polity_names(self):
        return {p['polity_id']: p['name'] for p in self.polity_list()}

    def terrain_union(self):
        """地区内确定成立的产地 ∪ 适宜的生产用地（候选群落不算）。"""
        have = set()
        if is_missing(self.terrains):
            return have
        for entry in self.terrains:
            have.update(entry.get('terrains') or ())
            have.update(entry.get('suitable') or ())
        return have

    def validate(self):
        errors = validate_snapshot(self)
        if errors:
            raise SnapshotError('；'.join(errors[:8]))
        return self


def _finite(value):
    return value is None or (isinstance(value, (int, float)) and not isinstance(value, bool)
                             and math.isfinite(value))


def validate_snapshot(snap):
    """结构校验（适配器写错时尽早报，而不是让流程在下游拿到半截数据）。"""
    errors = []
    if not isinstance(snap, RegionSnapshot):
        return ['不是 RegionSnapshot']
    if not isinstance(snap.region_id, str) or not snap.region_id:
        errors.append('region_id 为空')
    if not isinstance(snap.name, str) or not snap.name:
        errors.append('name 为空')
    source = snap.source if isinstance(snap.source, dict) else {}
    for key in IDENTITY_KEYS:
        if not source.get(key):
            errors.append('source 缺 %s' % key)
    for key in FIELDS:
        value = getattr(snap, key)
        if not (isinstance(value, list) or is_missing(value)):
            errors.append('%s 必须是列表或 missing 标记' % key)
    if errors:
        return errors

    cell_ids = set()
    for cell in ([] if is_missing(snap.cells) else snap.cells):
        cid = cell.get('cell_id')
        if not isinstance(cid, str) or cid in cell_ids:
            errors.append('地块 id 无效或重复：%r' % (cid,))
        cell_ids.add(cid)
        for key in ('lon', 'lat', 'elevation_m', 'slope_deg', 'relief_m', 'dist_to_sea_km',
                    'temperature_c', 'precipitation_mm', 'area_km2'):
            if not _finite(cell.get(key)):
                errors.append('地块 %s 的 %s 不是有限数值' % (cid, key))
    if not is_missing(snap.terrains):
        for entry in snap.terrains:
            if not is_missing(snap.cells) and entry.get('cell_id') not in cell_ids:
                errors.append('产地判定指向不存在的地块 %r' % (entry.get('cell_id'),))

    polity_ids = set()
    for polity in snap.polity_list():
        pid = polity.get('polity_id')
        if not isinstance(pid, str) or pid in polity_ids:
            errors.append('国家 id 无效或重复：%r' % (pid,))
        polity_ids.add(pid)
        if not isinstance(polity.get('name'), str) or not polity['name'].strip():
            errors.append('国家 %s 没有名称' % pid)
        hint = polity.get('form_hint')
        if hint not in FORM_HINTS and hint != MISSING:
            errors.append('国家 %s 的 form_hint 不在词表里：%r' % (pid, hint))
    for settlement in ([] if is_missing(snap.settlements) else snap.settlements):
        level = settlement.get('level')
        if level not in SETTLEMENT_LEVELS and level != MISSING:
            errors.append('聚落 %s 的等级不在词表里：%r' % (settlement.get('settlement_id'), level))

    event_ids = set()
    for event in snap.event_list():
        eid = event.get('event_id')
        if not isinstance(eid, str) or not eid or eid in event_ids:
            errors.append('事件 id 无效或重复：%r' % (eid,))
        event_ids.add(eid)
        if isinstance(event.get('year'), bool) or not isinstance(event.get('year'), int):
            errors.append('事件 %s 的 year 必须是整数' % eid)
        if not isinstance(event.get('kind'), str) or not isinstance(event.get('text'), str):
            errors.append('事件 %s 缺 kind / text' % eid)
        actors = event.get('actors')
        if not isinstance(actors, list):
            errors.append('事件 %s 的 actors 必须是列表' % eid)
        elif polity_ids:
            unknown = [a for a in actors if a not in polity_ids]
            if unknown:
                errors.append('事件 %s 的参与国不在 polities 里：%s' % (eid, unknown))
    return errors


def identity_matches(recorded, current):
    """草稿记录的来源身份与当前身份是否一致；返回不一致的键列表（空 = 一致）。"""
    recorded = recorded if isinstance(recorded, dict) else {}
    current = current if isinstance(current, dict) else {}
    return [key for key in IDENTITY_KEYS if recorded.get(key) != current.get(key)]
