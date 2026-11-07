# -*- coding: utf-8 -*-
"""事件池：按最终传播范围分级、沿道路逐日扩散的“局势”事件。

* 只有包声明 ``mechanics.events`` 才生效；旧包不加任何键、行为逐字节不变。
* 传播图是**中立的地点图**（节点=城镇/地点，边=相邻+路程小时+道路类型，节点可带国家）。
  本模块不 import civ 快照，也不 import play_map，也不另建路网；图只从包里已有数据读：
  ``story_locations``：``story.locations[*].neighbors`` + ``mechanics.adventure.routes``；
  ``exploration``：``civ_exploration`` 已编译进包的 ``mechanics.exploration``
  （towns / roads，``source == 'civ_routes'``，途中驿站并成一条边）。
* 国家归属：``mechanics.events.polities[地点 id]``（civ 世界由
  ``civ_exploration.town_polities`` 从 polity 取），或地点上的 ``polity`` 字段。没声明就是
  “国家缺失”：它不计入国家数，所以这样的世界最高只会出中事件。
* 每隔 ``interval_hours`` 游戏小时检查一次（默认 24=每日）；一次推进跨过多个边界就逐个检查。
  传播/遏制/消退全部用确定性种子 ``{session.seed}:event:{id}:day:{n}:{a}>{b}``，状态在
  ``session['event_pool']`` 里，随快照回滚。
* 玩家只通过“听说”得知：远处事件以**未确认** information 进 ``heard``（来源写“局势”，不含事件
  id），按距离可延迟；绝不写 facts。公开局势提示 ``event_notices[{kind,label,text}]`` 只在
  变化发生的那一步响应里出现一次。作者视图 ``authority_view`` 能看全部。
* 后果只能是引擎白名单 op：flag / resource / information / clock / signal。
"""
from __future__ import annotations

import copy
import hashlib
import heapq
import math
import re

from pydantic import BaseModel, ConfigDict, Field, model_validator

from . import checks

MECHANICS_KEY = 'events'
STATE_KEY = 'event_pool'
SCHEMA_VERSION = 1
ID = checks.ID
LEVELS = ('small', 'medium', 'large')
LEVEL_RANK = {name: index for index, name in enumerate(LEVELS)}
LEVEL_LABELS = {'small': '小', 'medium': '中', 'large': '大'}
EFFECT_OPS = ('flag', 'resource', 'information', 'clock', 'signal')
MAX_EVENTS = 16
MAX_NEWS = 40
SOURCE = '局势'
NOTICE_KINDS = ('start', 'rise', 'fall', 'end')
DEFAULT_ROAD_FACTOR = {'road': 1.0, 'trail': 0.6, 'sea': 0.8, 'town_lane': 1.0, 'street': 1.0}


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Gate(Strict):
    """flag（当前值）/ signal（发出过）/ quest_done（任务已完成），三选一。"""
    flag: str | None = None
    signal: str | None = None
    quest_done: str | None = None

    @model_validator(mode='after')
    def exactly_one(self):
        if sum(value is not None for value in (self.flag, self.signal, self.quest_done)) != 1:
            raise ValueError('条件必须且只能写 flag / signal / quest_done 之一')
        return self


class Texts(Strict):
    small: str | None = Field(default=None, max_length=300)
    medium: str | None = Field(default=None, max_length=300)
    large: str | None = Field(default=None, max_length=300)
    ended: str | None = Field(default=None, max_length=300)


class LevelEffects(Strict):
    small: list[dict] = Field(default_factory=list, max_length=6)
    medium: list[dict] = Field(default_factory=list, max_length=6)
    large: list[dict] = Field(default_factory=list, max_length=6)
    ended: list[dict] = Field(default_factory=list, max_length=6)


class EventSpec(Strict):
    id: str = Field(pattern=ID)
    label: str = Field(min_length=1, max_length=40)       # 公开局势提示的标签
    origin: str = Field(min_length=1, max_length=80)      # 起始城镇/地点（图节点 id）
    starts_at: int = Field(default=1, ge=0, le=100000)    # 第 n 次检查时（含）起可以开始
    start_on: Gate | None = None
    start_chance: float = Field(default=1.0, ge=0, le=1)  # 每次检查满足条件时的开始概率（1=必开始，行为不变）
    contagion: float = Field(default=0.3, ge=0, le=1)     # 每条边每次检查的基础传播率
    hours_half: float = Field(default=24, gt=0, le=100000)  # 路程小时的衰减尺度
    road_factor: dict[str, float] = Field(default_factory=dict)
    max_towns: int = Field(default=8, ge=1, le=24)
    contain_on: list[Gate] = Field(default_factory=list, max_length=4)
    fade_after: int | None = Field(default=None, ge=1, le=100000)  # 自然消退：开始后第 n 次检查
    recede_per_check: int = Field(default=1, ge=1, le=8)
    heard: Texts = Field(default_factory=Texts)           # 进 heard 的未确认传闻
    notice: Texts = Field(default_factory=Texts)          # 公开局势提示文案
    on_level: LevelEffects = Field(default_factory=LevelEffects)


class EventsConfig(Strict):
    version: int = SCHEMA_VERSION
    interval_hours: int = Field(default=24, ge=1, le=168)
    offset_hours: int = Field(default=0, ge=0, le=167)
    graph: str | None = Field(default=None, pattern='^(story_locations|exploration)$')
    polities: dict[str, int | str | None] = Field(default_factory=dict)
    medium_towns: int = Field(default=2, ge=2, le=24)
    large_countries: int = Field(default=2, ge=2, le=24)
    max_active: int = Field(default=3, ge=1, le=8)
    radius_hours: float | None = Field(default=96, gt=0)
    hear_delay_hours: float = Field(default=0, ge=0)
    events: list[EventSpec] = Field(default_factory=list, max_length=MAX_EVENTS)


def config(story):
    block = ((story or {}).get('mechanics') or {}).get(MECHANICS_KEY)
    if block is None:
        return None
    if not isinstance(block, dict):
        raise ValueError('mechanics.events 必须是对象')
    return EventsConfig.model_validate(block)


def enabled(story):
    return config(story) is not None


# ------------------------------------------------------------------ 中立地点图
def _polity(value):
    if value is None or value == '' or value == -1:
        return None
    return str(value)


class PlaceGraph:
    """节点=城镇/地点；边=相邻+路程小时+道路类型；节点可带国家（可缺）。"""

    def __init__(self, source):
        self.source = source
        self.nodes = {}
        self.adj = {}
        self.locations = {}

    def add_node(self, node_id, name, polity=None):
        self.nodes[node_id] = {'name': name or node_id, 'polity': _polity(polity)}
        self.adj.setdefault(node_id, {})

    def add_edge(self, a, b, hours, kind):
        if a == b or a not in self.nodes or b not in self.nodes:
            return
        hours = max(0.0, float(hours))
        for x, y in ((a, b), (b, a)):
            old = self.adj.setdefault(x, {}).get(y)
            if old is None or hours < old['hours']:
                self.adj[x][y] = {'hours': hours, 'kind': str(kind or 'path')}

    def neighbors(self, node):
        return sorted(self.adj.get(node, {}))

    def edge(self, a, b):
        return self.adj[a][b]

    def town_of(self, location_id):
        return self.locations.get(location_id)

    def hours_from(self, source):
        if source not in self.nodes:
            return {}
        costs = {source: 0.0}
        queue = [(0.0, source)]
        while queue:
            cost, node = heapq.heappop(queue)
            if cost != costs[node]:
                continue
            for other in sorted(self.adj.get(node, {})):
                candidate = cost + self.adj[node][other]['hours']
                if candidate < costs.get(other, math.inf):
                    costs[other] = candidate
                    heapq.heappush(queue, (candidate, other))
        return costs

    def edge_count(self):
        return sum(len(v) for v in self.adj.values()) // 2


def story_graph(story):
    """适配器一：故事包自己的地点邻接。

    读 ``locations[*].id/name/neighbors/town_id/polity`` 与
    ``mechanics.adventure.routes[*].origin/destination/hours/kind``（缺路由时按 1 小时、path）。
    有 ``town_id`` 的地点并入同一个城镇节点。
    """
    graph = PlaceGraph('story_locations')
    locations = [loc for loc in (story.get('locations') or []) if isinstance(loc, dict) and loc.get('id')]
    for loc in locations:
        node = loc.get('town_id') or loc['id']
        graph.locations[loc['id']] = node
        if node not in graph.nodes:
            graph.add_node(node, loc.get('name'), loc.get('polity'))
        elif graph.nodes[node]['polity'] is None:
            graph.nodes[node]['polity'] = _polity(loc.get('polity'))
    routes = {}
    adventure = (story.get('mechanics') or {}).get('adventure') or {}
    for route in adventure.get('routes') or []:
        if isinstance(route, dict) and route.get('origin') and route.get('destination'):
            key = (route['origin'], route['destination'])
            old = routes.get(key)
            if old is None or route.get('hours', 1) < old.get('hours', 1):
                routes[key] = route
    for loc in locations:
        for other in loc.get('neighbors') or []:
            route = routes.get((loc['id'], other)) or routes.get((other, loc['id'])) or {}
            if other in graph.locations:
                graph.add_edge(graph.locations[loc['id']], graph.locations[other],
                               route.get('hours', 1), route.get('kind', 'path'))
    return graph


def exploration_graph(story):
    """适配器二：``civ_exploration.compile_region`` 已编译进包的城镇与世界道路。

    读 ``mechanics.exploration.towns[*].id/name/polity`` 与
    ``mechanics.exploration.roads[*]`` 中 ``source == 'civ_routes'`` 的
    ``origin/destination/kind/hours``；中途驿站（不是城镇的端点）沿链并成一条城到城的边，
    小时相加、类型合并。镇内街道（``generated_town_plan``）不是城际道路，忽略。
    """
    exploration = (story.get('mechanics') or {}).get('exploration')
    if not isinstance(exploration, dict):
        raise ValueError('mechanics.events.graph=exploration 需要 mechanics.exploration')
    graph = PlaceGraph('exploration')
    towns = {t['id']: t for t in exploration.get('towns') or [] if isinstance(t, dict) and t.get('id')}
    for town_id, town in towns.items():
        graph.add_node(town_id, town.get('name'), town.get('polity'))
    for loc in story.get('locations') or []:
        if not isinstance(loc, dict):
            continue
        town_id = loc.get('town_id')
        if town_id in towns:
            graph.locations[loc['id']] = town_id
        elif loc.get('id') in towns:
            graph.locations[loc['id']] = loc['id']
    raw = {}
    for road in exploration.get('roads') or []:
        if not isinstance(road, dict) or road.get('source') != 'civ_routes':
            continue
        a, b = road.get('origin'), road.get('destination')
        edge = (float(road.get('hours', 1)), str(road.get('kind') or 'road'))
        raw.setdefault(a, []).append((b, *edge))
        raw.setdefault(b, []).append((a, *edge))
    for town_id in sorted(towns):
        for first, hours, kind in sorted(raw.get(town_id, [])):
            previous, current, total, kinds = town_id, first, hours, {kind}
            for _ in range(len(raw) + 1):
                if current in towns:
                    break
                onward = [item for item in raw.get(current, []) if item[0] != previous]
                if len(onward) != 1:
                    current = None
                    break
                previous, (current, hours, kind) = current, onward[0]
                total += hours
                kinds.add(kind)
            else:
                current = None
            if current in towns and current != town_id:
                graph.add_edge(town_id, current, total, '/'.join(sorted(kinds)))
    return graph


def build_graph(story, cfg):
    source = cfg.graph
    if source is None:
        has = isinstance(((story.get('mechanics') or {}).get('exploration')), dict)
        source = 'exploration' if has else 'story_locations'
    graph = exploration_graph(story) if source == 'exploration' else story_graph(story)
    for place, value in cfg.polities.items():
        if place in graph.nodes:
            graph.nodes[place]['polity'] = _polity(value)
    return graph


# ------------------------------------------------------------------ 确定性与概率
def roll(seed, event_id, check, a, b):
    """[0,1) 的确定性随机数：只由种子、事件、检查序号与边决定，与存档/读档无关。"""
    key = '%s:event:%s:day:%d:%s>%s' % (seed, event_id, check, a, b)
    return int.from_bytes(hashlib.sha256(key.encode('utf-8')).digest()[:8], 'big') / 2.0 ** 64


def start_roll(seed, event_id, check):
    """[0,1) 的确定性随机数：决定满足条件的这次检查是否真的开始（start_chance）。"""
    key = '%s:event:%s:start:%d' % (seed, event_id, check)
    return int.from_bytes(hashlib.sha256(key.encode('utf-8')).digest()[:8], 'big') / 2.0 ** 64


def edge_probability(spec, edge):
    factors = {**DEFAULT_ROAD_FACTOR, **spec.road_factor}
    kinds = [k for k in str(edge['kind']).split('/') if k]
    factor = min((factors.get(k, 1.0) for k in kinds), default=1.0)
    p = spec.contagion * factor / (1.0 + edge['hours'] / spec.hours_half)
    return max(0.0, min(1.0, p))


def level_of(graph, cfg, towns):
    countries = {graph.nodes[t]['polity'] for t in towns
                 if t in graph.nodes and graph.nodes[t]['polity'] is not None}
    if len(countries) >= cfg.large_countries:
        return 'large'
    if len(towns) >= cfg.medium_towns:
        return 'medium'
    return 'small'


def countries_of(graph, towns):
    return sorted({graph.nodes[t]['polity'] for t in towns
                   if t in graph.nodes and graph.nodes[t]['polity'] is not None})


def gate_met(session, gate):
    if gate.flag is not None:
        return bool((session.get('flags') or {}).get(gate.flag))
    if gate.signal is not None:
        signals = session.get('signals')
        return isinstance(signals, list) and gate.signal in signals
    entries = ((session.get('quests') or {}).get('entries') or {})
    row = entries.get(gate.quest_done)
    return isinstance(row, dict) and row.get('state') == 'completed'


# ------------------------------------------------------------------ 状态
def index_of(cfg, time):
    return (int(time) - cfg.offset_hours) // cfg.interval_hours


def _blank_item():
    return {'status': 'pending', 'level': None, 'started': None, 'affected': [], 'since': {},
            'fading': False, 'contained': False, 'history': [], 'queue': []}


def ensure(session, story, time=None):
    """在候选 session 上建事件池状态；没声明 ``mechanics.events`` 时什么都不碰。"""
    cfg = config(story)
    if cfg is None:
        return None
    state = session.get(STATE_KEY)
    if not isinstance(state, dict):
        base = session.get('time', 0) if time is None else time
        state = {'version': SCHEMA_VERSION, 'last_check': index_of(cfg, base),
                 'items': {}, 'news': [], 'seq': 0, 'news_seq': 0}
        session[STATE_KEY] = state
    for spec in cfg.events:
        state['items'].setdefault(spec.id, _blank_item())
    return state


def _apply(session, effects, batch):
    if not batch:
        return
    if effects is None:
        raise ValueError('事件池的效果必须由 Runtime.effects 应用；不允许直接改状态')
    effects(session, copy.deepcopy(batch), SOURCE)


def _record(item, n, at_hours, old, new, kind, graph, towns):
    item['history'].append({'check': n, 'at_hours': at_hours, 'kind': kind, 'from': old, 'to': new,
                            'towns': len(towns), 'countries': len(countries_of(graph, towns))})


def _queue(state, cfg, spec, item, n, kind, level, near, graph, towns):
    key = 'ended' if kind == 'end' else level
    heard, notice = getattr(spec.heard, key), getattr(spec.notice, key)
    if not heard and not notice:
        return
    delay = 0
    if cfg.hear_delay_hours > 0 and near is not None:
        distance = min((near.get(t, math.inf) for t in towns), default=math.inf)
        if distance == math.inf:
            return                      # 路网上到不了：传闻也到不了
        delay = int(distance // cfg.hear_delay_hours)
    item['queue'].append({'due': n + delay, 'seq': state['seq'], 'kind': kind, 'level': level,
                          'heard': heard, 'notice': notice})
    state['seq'] += 1


def _deliver(session, state, cfg, n, effects):
    due = []
    for spec in cfg.events:
        item = state['items'][spec.id]
        for entry in item['queue']:
            if entry['due'] <= n:
                due.append((entry['due'], entry['seq'], spec, entry))
        item['queue'] = [e for e in item['queue'] if e['due'] > n]
    due.sort(key=lambda row: (row[0], row[1]))
    for _, _, spec, entry in due:
        if entry['heard']:
            _apply(session, effects, [{'op': 'information', 'text': entry['heard'],
                                       'known_by': ['player'], 'confirmed': False}])
        if entry['notice']:
            state['news_seq'] += 1
            state['news'].append({'n': state['news_seq'], 'check': n, 'kind': entry['kind'],
                                  'label': spec.label, 'text': entry['notice']})
            del state['news'][:-MAX_NEWS]


def _spread(session, cfg, spec, graph, near, n, affected):
    seed = str(session.get('seed', ''))
    current = set(affected)
    added = []
    for a in sorted(current):
        for b in graph.neighbors(a):
            if b in current or b in added:
                continue
            if len(current) + len(added) >= spec.max_towns:
                return added
            if cfg.radius_hours is not None and near is not None \
                    and near.get(b, math.inf) > cfg.radius_hours:
                continue
            if roll(seed, spec.id, n, a, b) < edge_probability(spec, graph.edge(a, b)):
                added.append(b)
    return added


def _recede(spec, graph, affected):
    from_origin = graph.hours_from(spec.origin)
    order = sorted(affected, key=lambda t: (t == spec.origin, -from_origin.get(t, 1e9), t))
    gone = order[:spec.recede_per_check]
    return [t for t in affected if t not in gone], gone


def _step(session, cfg, graph, state, spec, item, near, n, at_hours, effects):
    if item['status'] == 'pending':
        if n < spec.starts_at:
            return
        if spec.start_on is not None and not gate_met(session, spec.start_on):
            return
        if sum(1 for it in state['items'].values() if it['status'] == 'active') >= cfg.max_active:
            return
        if cfg.radius_hours is not None and near is not None \
                and near.get(spec.origin, math.inf) > cfg.radius_hours:
            return
        if spec.start_chance < 1.0 \
                and start_roll(session.get('seed', ''), spec.id, n) >= spec.start_chance:
            return
        item.update(status='active', level='small', started=n, affected=[spec.origin],
                    since={spec.origin: n}, fading=False, contained=False)
        _record(item, n, at_hours, None, 'small', 'start', graph, item['affected'])
        _queue(state, cfg, spec, item, n, 'start', 'small', near, graph, item['affected'])
        _apply(session, effects, spec.on_level.small)
        return
    contained = any(gate_met(session, gate) for gate in spec.contain_on)
    if spec.fade_after is not None and not item['fading'] and n - item['started'] >= spec.fade_after:
        item['fading'] = True
    item['contained'] = contained
    affected = list(item['affected'])
    if contained or item['fading']:
        affected, gone = _recede(spec, graph, affected)
        for town in gone:
            item['since'].pop(town, None)
    else:
        for town in _spread(session, cfg, spec, graph, near, n, affected):
            affected.append(town)
            item['since'][town] = n
    old = item['level']
    if not affected:
        item.update(status='ended', level=None, affected=[], contained=contained)
        _record(item, n, at_hours, old, None, 'end', graph, [])
        _queue(state, cfg, spec, item, n, 'end', old, near, graph, [spec.origin])
        _apply(session, effects, spec.on_level.ended)
        return
    item['affected'] = affected
    new = level_of(graph, cfg, affected)
    if new != old:
        kind = 'rise' if LEVEL_RANK[new] > LEVEL_RANK[old] else 'fall'
        item['level'] = new
        _record(item, n, at_hours, old, new, kind, graph, affected)
        _queue(state, cfg, spec, item, n, kind, new, near, graph, affected)
        _apply(session, effects, getattr(spec.on_level, new))


def tick(session, story, characters, before_time, effects=None):
    """时间推进之后调用：把跨过的检查边界逐个处理；返回处理过的检查序号列表。"""
    cfg = config(story)
    if cfg is None:
        return []
    state = ensure(session, story, before_time)
    target = index_of(cfg, session.get('time', 0))
    first = state['last_check'] + 1
    if target < first:
        return []
    graph = build_graph(story, cfg)
    town = graph.town_of(session.get('location'))
    near = graph.hours_from(town) if town else None
    done = []
    for n in range(first, target + 1):
        at_hours = cfg.offset_hours + n * cfg.interval_hours
        for spec in cfg.events:
            item = state['items'][spec.id]
            if item['status'] != 'ended':
                _step(session, cfg, graph, state, spec, item, near, n, at_hours, effects)
        _deliver(session, state, cfg, n, effects)
        state['last_check'] = n
        done.append(n)
    return done


# ------------------------------------------------------------------ 玩家侧：只有局势提示
def notices(before_session, after_session, story):
    """一步前后新到达的公开局势提示 ``{kind, label, text}``（纯 diff，只读）。

    不含事件 id、内部等级、波及城镇；``kind`` ∈ start / rise / fall / end。
    """
    if config(story) is None:
        return []
    before = (before_session or {}).get(STATE_KEY)
    after = (after_session or {}).get(STATE_KEY)
    if not isinstance(after, dict):
        return []
    seen = before.get('news_seq', 0) if isinstance(before, dict) else 0
    return [{'kind': row['kind'], 'label': row['label'], 'text': row['text']}
            for row in after.get('news') or [] if row['n'] > seen]


# ------------------------------------------------------------------ 作者视图
def authority_view(session, story):
    """作者/内部视图：全部事件、当前等级、波及城镇与国家、下次检查日、等级变化历史。"""
    cfg = config(story)
    if cfg is None:
        return None
    graph = build_graph(story, cfg)
    state = session.get(STATE_KEY) if isinstance(session.get(STATE_KEY), dict) else None
    last = state['last_check'] if state else index_of(cfg, session.get('time', 0))
    nxt = last + 1
    missing = sorted(t for t, node in graph.nodes.items() if node['polity'] is None)
    rows = []
    for spec in cfg.events:
        item = (state or {}).get('items', {}).get(spec.id) or _blank_item()
        towns = [{'id': t, 'name': graph.nodes[t]['name'], 'polity': graph.nodes[t]['polity'],
                  'since_check': item['since'].get(t)} for t in item['affected'] if t in graph.nodes]
        rows.append({
            'id': spec.id, 'label': spec.label, 'status': item['status'], 'level': item['level'],
            'origin': spec.origin, 'starts_at': spec.starts_at, 'started_check': item['started'],
            'towns': towns, 'countries': countries_of(graph, item['affected']),
            'polity_missing_towns': [t['id'] for t in towns if t['polity'] is None],
            'country_missing': any(t['polity'] is None for t in towns),
            'fading': item['fading'], 'contained': item['contained'],
            'contagion': spec.contagion,
            'pending_hearing': [{'due_check': e['due'], 'kind': e['kind'], 'level': e['level']}
                                for e in item['queue']],
            'history': copy.deepcopy(item['history'])})
    return {'projection': 'events.authority_view', 'version': cfg.version,
            'interval_hours': cfg.interval_hours, 'offset_hours': cfg.offset_hours,
            'last_check': last, 'next_check': nxt,
            'next_check_at_hours': cfg.offset_hours + nxt * cfg.interval_hours,
            'thresholds': {'medium_towns': cfg.medium_towns, 'large_countries': cfg.large_countries},
            'max_active': cfg.max_active, 'radius_hours': cfg.radius_hours,
            'graph': {'source': graph.source, 'nodes': len(graph.nodes), 'edges': graph.edge_count(),
                      'polity_missing': missing[:60],
                      'note': ('国家归属缺失：缺失的城镇不计入国家数，事件最高到中等级' if missing else '')},
            'events': rows, 'news': copy.deepcopy((state or {}).get('news') or [])}


# ------------------------------------------------------------------ 包校验
def _check_gate(gate, story, where, quest_ids):
    if gate.flag is not None:
        checks._check_flag_name(gate.flag, where)
    if gate.signal is not None:
        checks._check_flag_name(gate.signal, where)
    if gate.quest_done is not None and gate.quest_done not in quest_ids:
        raise ValueError('%s 引用了不存在的任务：%s' % (where, gate.quest_done))


def validate(story, characters):
    """严格校验 ``mechanics.events``；没有这个块就是 no-op。"""
    cfg = config(story)
    if cfg is None:
        return None
    if cfg.version != SCHEMA_VERSION:
        raise ValueError('mechanics.events.version 必须是 %d（得到 %r）' % (SCHEMA_VERSION, cfg.version))
    graph = build_graph(story, cfg)
    if not graph.nodes:
        raise ValueError('mechanics.events 需要至少一个城镇/地点')
    for place in cfg.polities:
        if place not in graph.nodes:
            raise ValueError('mechanics.events.polities 引用了不存在的城镇：%s' % place)
    quest_block = (story.get('mechanics') or {}).get('quests')
    quest_ids = {q.get('id') for q in (quest_block.get('quests') if isinstance(quest_block, dict) else None) or []
                 if isinstance(q, dict)}
    chars = {c['id'] for c in (characters or {}).get('characters') or []}
    items = {i['id'] for i in story.get('items') or []}
    from . import local_rules
    resources = {r.id for r in local_rules.rules(story).resources}
    checks_cfg = checks.config(story)
    clocks = {c.id for c in checks_cfg.clocks} if checks_cfg is not None else set()
    seen = set()
    for spec in cfg.events:
        where = '事件 %s' % spec.id
        if spec.id in seen:
            raise ValueError('事件 id 重复：%s' % spec.id)
        seen.add(spec.id)
        if spec.origin not in graph.nodes:
            raise ValueError('%s 的 origin 不是图里的城镇：%s' % (where, spec.origin))
        for key, value in spec.road_factor.items():
            if not 0 <= value <= 2 or not re.match(r'^[A-Za-z0-9_]{1,24}$', key):
                raise ValueError('%s 的 road_factor 必须是 0–2 的数，键是道路类型：%s' % (where, key))
        for gate in ([spec.start_on] if spec.start_on else []) + list(spec.contain_on):
            _check_gate(gate, story, where, quest_ids)
        for group in (spec.heard, spec.notice):
            for key in ('small', 'medium', 'large', 'ended'):
                text = getattr(group, key)
                if text is not None and not text.strip():
                    raise ValueError('%s 的文案不能为空白：%s' % (where, key))
        for key in ('small', 'medium', 'large', 'ended'):
            batch = getattr(spec.on_level, key)
            for effect in batch:
                if not isinstance(effect, dict) or effect.get('op') not in EFFECT_OPS:
                    raise ValueError('%s 的 on_level.%s 只允许 %s' % (where, key, '/'.join(EFFECT_OPS)))
                if effect['op'] == 'information' and effect.get('confirmed', False):
                    raise ValueError('%s 的 information 不能是已确认事实（事件池只产生传闻）' % where)
            checks._validate_effects(batch, story, chars, resources, items, clocks,
                                     '%s 的 on_level.%s' % (where, key))
    return cfg
