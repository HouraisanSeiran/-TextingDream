# -*- coding: utf-8 -*-
"""统一轻量剧情压力：**唯一的时间推进入口**，复用 local_rules 的时钟。

设计要点（设计文档 §3 + 首轮审查意见 4）：

* **只有一个推进函数**：``advance()``。它先调 ``local_rules.advance`` 推进资源/日程/
  作息，再用**同一个** ``s['time']`` 判定压力阶段。因此不存在「调用方自己调一次、
  压力又调一次」的双推进——所有时间推进路径（new_session / turn / move / wait）
  都必须走这里。
* **只读路径不执行阶段**：``known()`` / ``context()`` / ``phase()`` 只读，不写库、
  不应用效果。GET 接口因此没有副作用。
* **原子**：阶段效果复用 ``Runtime.effects``（同一个白名单、同一份原子批次），
  且只写内存态；只有 ``finish_turn``/``move``/``wait`` 的 ``save_session`` 才落库。
  模型失败时整轮不写。
* **幂等 + 跨阶段语义**：``applied[stage_key]`` 记录应用时刻，同一阶段永不多发。
  一次大幅推进跨过多个阈值时按小时交错推进，阈值在它真正到达的那个小时生效。
* **时间粒度**：``advance(N)`` 等于连续 N 次 ``advance(1)``（无玩家干预时）：
  每个小时先跑 ``local_rules.advance(1)``，再应用此刻到期的阶段，所以
  10 点的灾难不会被拖到 20 点才生效，也不会让 11 点的日程先读到「灾后」的标记。
* **同刻顺序**：``at_hours`` 相同时按 ``(kind 优先级, stage id)`` 排序——
  ``lift``(化解) → ``warning`` → ``escalation`` → ``trigger`` → ``resolution`` →
  ``aftermath``，且每应用一条都重新求值。
* **化解是终止，不只是记账**：``lift`` 阶段生效后，同一压力里**尚未生效**的阶段
  全部标为 ``cancelled``，永不再补放（已发生的阶段不回滚）。作者的
  ``when.not_flags`` 仍是第二道锁，两者都是幂等的。
* **不回填历史**：``when`` 在阈值到达之后才满足时，阶段在**满足的那一刻**触发；
  后来的标记不会追溯到过去的时刻，也不会把已应用过的阶段重新算一遍。
* **已知范围**：只有 ``known_by`` 含该受众、且写了 ``public_text`` 的阶段进上下文；
  不返回阶段计数、阈值或未发生的结果。
"""
from __future__ import annotations

import hashlib
import re

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from . import local_rules

MECHANICS_KEY = 'pressure'
SCHEMA_VERSION = 1
MAX_PRESSURES = 8
MAX_STAGES = 12
MAX_EFFECTS = 8
MAX_TEXT = 600
ID = r'^[A-Za-z0-9_-]{1,60}$'
FLAG_RE = r'^[A-Za-z0-9_-]{1,60}$'
TEXT_MAX = 240
CONTEXT_MAX_CHARS = 600

KINDS = ('lift', 'warning', 'escalation', 'trigger', 'resolution', 'aftermath')
# 同刻排序：化解优先，随后按紧迫度；id 兜底保证确定性。
KIND_ORDER = {kind: index for index, kind in enumerate(KINDS)}
EFFECT_OPS = ('flag', 'resource', 'notice', 'information', 'fact')


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Condition(Strict):
    all_flags: dict[str, bool] = Field(default_factory=dict)
    any_flags: dict[str, bool] = Field(default_factory=dict)
    not_flags: list[str] = Field(default_factory=list, max_length=16)

    @model_validator(mode='before')
    @classmethod
    def raw_types(cls, data):
        if not isinstance(data, dict):
            return data
        for key in ('all_flags', 'any_flags'):
            flags = data.get(key)
            if flags is None:
                continue
            if not isinstance(flags, dict):
                raise ValueError('%s 必须是对象' % key)
            for name, value in flags.items():
                if not isinstance(name, str) or not re.match(FLAG_RE, name):
                    raise ValueError('%s 的标记名无效：%r' % (key, name))
                if not isinstance(value, bool):
                    raise ValueError('%s.%s 必须是 true/false（不接受 0/1 或文本）'
                                     % (key, name))
        not_flags = data.get('not_flags')
        if not_flags is not None:
            if not isinstance(not_flags, list):
                raise ValueError('not_flags 必须是列表')
            for name in not_flags:
                if not isinstance(name, str) or not re.match(FLAG_RE, name):
                    raise ValueError('not_flags 的标记名无效：%r' % (name,))
        return data


class Effect(Strict):
    """只允许与既有 Runtime.effects 相同的白名单操作，不新增 op。"""

    op: Literal['flag', 'resource', 'notice', 'information', 'fact']
    id: str = Field(default='', max_length=60)
    value: bool = True
    delta: int = Field(default=0, ge=-1000000000, le=1000000000)
    text: str = Field(default='', max_length=TEXT_MAX)
    visible: bool = False
    confirmed: bool = False
    known_by: list[str] = Field(default_factory=list, max_length=8)

    @model_validator(mode='before')
    @classmethod
    def raw_types(cls, data):
        if not isinstance(data, dict):
            return data
        if 'delta' in data:
            value = data['delta']
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError('效果 delta 必须是整数（布尔值不算）')
        if 'value' in data and not isinstance(data['value'], bool):
            raise ValueError('效果 value 必须是 true/false')
        return data

    @model_validator(mode='after')
    def shape(self):
        if self.op == 'flag':
            if not self.id:
                raise ValueError('flag 效果需要 id')
        elif self.op == 'resource':
            if not self.id:
                raise ValueError('resource 效果需要 id')
        elif self.op == 'information':
            if not self.text.strip():
                raise ValueError('information 效果需要文本')
            if not self.known_by:
                raise ValueError('information 效果需要 known_by')
        elif self.op == 'fact':
            if not self.text.strip():
                raise ValueError('fact 效果需要文本')
        elif self.op == 'notice':
            if not self.text.strip():
                raise ValueError('notice 效果需要文本')
        return self


class Stage(Strict):
    id: str = Field(pattern=ID)
    at_hours: int = Field(ge=0, le=10 ** 7)
    kind: Literal['lift', 'warning', 'escalation', 'trigger', 'resolution', 'aftermath']
    title: str = Field(default='', max_length=60)
    when: Condition | None = None
    effects: list[Effect] = Field(default_factory=list, max_length=MAX_EFFECTS)
    # 只有列在这里的受众才看得到 public_text；没有 public_text 的阶段永远不进上下文。
    known_by: list[str] = Field(default_factory=list, max_length=8)
    public_text: str = Field(default='', max_length=TEXT_MAX)


class Pressure(Strict):
    id: str = Field(pattern=ID)
    title: str = Field(min_length=1, max_length=60)
    stages: list[Stage] = Field(min_length=1, max_length=MAX_STAGES)
    note: str = Field(default='', max_length=TEXT_MAX)

    @model_validator(mode='after')
    def unique_stages(self):
        ids = [stage.id for stage in self.stages]
        if len(set(ids)) != len(ids):
            raise ValueError('压力 %s 的阶段 ID 重复' % self.id)
        # 同一压力内的阶段不得同 id；同 at_hours 允许（同刻顺序由排序规则决定）。
        if not any(stage.kind == 'trigger' for stage in self.stages):
            raise ValueError('压力 %s 缺少 trigger 阶段（阶段推进需要明确的引爆点）' % self.id)
        return self


class PressureConfig(Strict):
    version: int = Field(ge=1, le=1)
    note: str = Field(default='', max_length=300)
    pressures: list[Pressure] = Field(min_length=1, max_length=MAX_PRESSURES)

    @model_validator(mode='before')
    @classmethod
    def raw_types(cls, data):
        if isinstance(data, dict) and 'version' in data:
            value = data['version']
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError('压力配置版本必须是整数（布尔值不算）')
            if value != SCHEMA_VERSION:
                raise ValueError('压力配置版本必须是 %d' % SCHEMA_VERSION)
        return data


# ------------------------------------------------------------------ 读取
def config(story):
    """故事包声明的压力配置；没有就是 None（老包行为完全不变）。"""
    mechanics = (story or {}).get('mechanics') or {}
    if not isinstance(mechanics, dict):
        return None
    raw = mechanics.get(MECHANICS_KEY)
    if raw is None:
        return None
    return PressureConfig.model_validate(raw)


def validate_package(story, characters):
    """包校验：效果必须引用已声明的资源/角色，受众必须真实存在。"""
    cfg = config(story)
    if cfg is None:
        return None
    local = local_rules.rules(story)
    resources = {r.id for r in local.resources}
    chars = {c['id'] for c in (characters or {}).get('characters', [])}
    audiences = chars | {'player'}
    for pressure in cfg.pressures:
        for stage in pressure.stages:
            for effect in stage.effects:
                if effect.op == 'resource' and effect.id not in resources:
                    raise ValueError('压力 %s 的阶段 %s 引用了未声明的资源：%s'
                                     % (pressure.id, stage.id, effect.id))
                if effect.op == 'information':
                    unknown = set(effect.known_by) - audiences
                    if unknown:
                        raise ValueError('压力 %s 的阶段 %s 的信息受众不存在：%s'
                                         % (pressure.id, stage.id,
                                            '、'.join(sorted(unknown))))
            unknown = set(stage.known_by) - audiences
            if unknown:
                raise ValueError('压力 %s 的阶段 %s 的已知受众不存在：%s'
                                 % (pressure.id, stage.id, '、'.join(sorted(unknown))))
            if stage.public_text and not stage.known_by:
                # 写了预警文本却没人被列进已知范围：它永远不会出现，作者多半是漏写了。
                raise ValueError('压力 %s 的阶段 %s 有 public_text 但 known_by 为空'
                                 % (pressure.id, stage.id))
    return cfg


# -------------------------------------------------------------- session 状态
def ensure(session, story):
    """在候选 session 上建立压力状态；未配置时返回 None（不新增任何键）。"""
    cfg = config(story)
    if cfg is None:
        return None
    block = session.setdefault('pressure', {})
    block.setdefault('version', SCHEMA_VERSION)
    block.setdefault('applied', {})
    block.setdefault('log', [])
    block.setdefault('lifted', {})
    block.setdefault('cancelled', {})
    return cfg


def _stage_key(pressure_id, stage_id):
    return '%s:%s' % (pressure_id, stage_id)


def _when_matches(stage, session):
    """条件求值：只读标记，不读时钟、不读模型文本。"""
    if stage.when is None:
        return True
    flags = session.get('flags') or {}
    for name, value in stage.when.all_flags.items():
        if bool(flags.get(name, False)) != value:
            return False
    if stage.when.any_flags:
        if not any(bool(flags.get(name, False)) == value
                   for name, value in stage.when.any_flags.items()):
            return False
    for name in stage.when.not_flags:
        if bool(flags.get(name, False)):
            return False
    return True


def due(session, story):
    """按确定性顺序列出**此刻应当应用**的阶段（只读，不改状态）。

    排序：``at_hours`` → 同刻 KIND_ORDER → 压力 id → 阶段 id。
    已应用过、或已被同压力里的化解阶段终止（cancelled）的阶段不再出现。

    「化解后不再补放」有两道锁：化解阶段会终止同压力尚未生效的阶段（见
    ``_cancel_rest``）；作者的 ``when.not_flags`` 同时也能表达「开闸之后这条灾难
    不成立」。两者都是幂等的：一旦应用或被取消，就不会再回来。
    """
    cfg = config(story)
    if cfg is None:
        return []
    block = session.get('pressure') or {}
    applied = block.get('applied') or {}
    cancelled = block.get('cancelled') or {}
    now = session.get('time', 0)
    rows = []
    for pressure in cfg.pressures:
        for stage in pressure.stages:
            key = _stage_key(pressure.id, stage.id)
            if key in applied or key in cancelled:
                continue
            if stage.at_hours > now:
                continue
            if not _when_matches(stage, session):
                # 条件在阈值到达之后才满足：等它满足的那一刻再触发，
                # 不回填到早已过去的时刻。
                continue
            rows.append((stage.at_hours, KIND_ORDER[stage.kind], pressure.id, stage.id,
                         pressure, stage, key))
    rows.sort(key=lambda row: (row[0], row[1], row[2], row[3]))
    return [{'pressure': row[4], 'stage': row[5], 'key': row[6],
             'at_hours': row[0], 'kind': row[5].kind} for row in rows]


def _record(session, pressure, stage, key, outcome):
    session['pressure']['applied'][key] = session.get('time', 0)
    session['pressure']['log'].append({
        'key': key, 'pressure': pressure.id, 'stage': stage.id, 'kind': stage.kind,
        'at': session.get('time', 0), 'threshold': stage.at_hours,
        'outcome': outcome, 'title': stage.title})


def advance(session, story, characters, hours, effects=None):
    """**唯一**的时间推进入口，且**逐小时交错**推进两个系统。

    推进 1 小时 = ``local_rules.advance(1)`` → 再应用此刻到期的压力阶段。
    所以 ``advance(12)`` 与连续 12 次 ``advance(1)`` 在无玩家干预时结果相同：
    10 点的灾难在 10 点生效，10 点之后的资源/日程不会先按「灾前」算完；
    11 点的日程读到的是 10 点压力改过的标记，而不是反过来。

    ``effects`` 是 ``Runtime.effects``（白名单 + 原子批次）；未提供时，
    含状态效果的压力阶段会被拒绝——不允许压力模块自己私改状态。
    返回本次实际应用的阶段列表（供作者审计与测试），不改 ``session['active']``。
    """
    if isinstance(hours, bool) or not isinstance(hours, int) or not 0 <= hours <= 168:
        raise ValueError('推进时长必须为0到168小时')
    cfg = ensure(session, story)
    if cfg is None:
        # 未配置压力时保持旧行为：一次调用推进全部小时。
        local_rules.advance(session, story, characters, hours)
        return []
    applied = []
    if hours == 0:
        local_rules.advance(session, story, characters, 0)
        return applied + _drain(session, story, effects)
    for _ in range(hours):
        local_rules.advance(session, story, characters, 1)
        applied.extend(_drain(session, story, effects))
    return applied


def _drain(session, story, effects):
    """把此刻应当生效的阶段逐条应用（每应用一条重新求值）。"""
    applied = []
    while True:
        rows = due(session, story)
        if not rows:
            return applied
        row = rows[0]
        stage = row['stage']
        pressure = row['pressure']
        if stage.effects:
            if effects is None:
                raise ValueError('压力阶段含状态效果，必须由 Runtime.effects 应用；'
                                 '不允许压力模块直接改状态')
            effects(session, [effect.model_dump() for effect in stage.effects],
                    'pressure:%s:%s' % (pressure.id, stage.id))
        if stage.kind == 'lift':
            # 化解不只是记账：它**终止同一压力里尚未生效的阶段**（记 cancelled）。
            # 已经发生过的阶段不回滚；作者自己写的 when.not_flags 仍然是第二道锁。
            session['pressure']['lifted'][row['key']] = session.get('time', 0)
            _record(session, pressure, stage, row['key'], 'lifted')
            _cancel_rest(session, pressure)
        else:
            _record(session, pressure, stage, row['key'], 'applied')
        applied.append({'pressure': pressure.id, 'stage': stage.id,
                        'kind': stage.kind, 'at': session.get('time', 0),
                        'threshold': stage.at_hours})


def _cancel_rest(session, pressure):
    """化解后把同一压力剩下的阶段标为 cancelled（不再补放，但留下审计记录）。"""
    block = session['pressure']
    cancelled = block.setdefault('cancelled', {})
    for stage in pressure.stages:
        key = _stage_key(pressure.id, stage.id)
        if key in block['applied'] or key in cancelled:
            continue
        cancelled[key] = session.get('time', 0)
        block['log'].append({'key': key, 'pressure': pressure.id, 'stage': stage.id,
                             'kind': stage.kind, 'at': session.get('time', 0),
                             'threshold': stage.at_hours, 'outcome': 'cancelled',
                             'title': stage.title})
    return cancelled


# ------------------------------------------------------------------- 只读视图
def known(session, story, audience):
    """该受众**已经知道**的预警（只读）。

    只包含：已生效、``known_by`` 含该受众、且写了 ``public_text`` 的阶段。
    不返回阶段计数、阈值、未发生的结果，也不返回别人的私有预警。
    """
    cfg = config(story)
    if cfg is None:
        return []
    block = session.get('pressure') or {}
    applied = block.get('applied') or {}
    rows = []
    for pressure in cfg.pressures:
        for stage in pressure.stages:
            key = _stage_key(pressure.id, stage.id)
            if key not in applied:
                continue
            if audience not in stage.known_by:
                continue
            if not stage.public_text.strip():
                continue
            rows.append({'pressure': pressure.title, 'text': stage.public_text,
                         'at': applied[key], 'kind': stage.kind})
    return rows


def context(session, story, audience):
    """进入模型上下文的有界摘要；没有已知预警时返回 None（prompt 一字不变）。"""
    rows = known(session, story, audience)
    if not rows:
        return None
    items = []
    for row in rows:
        items.append({'text': row['text']})
        if len(''.join(x['text'] for x in items)) > CONTEXT_MAX_CHARS:
            items.pop()
            break
    if not items:
        return None
    return {'basis': '这些是已发生、且这个视角确实知道的消息；不是预言，'
                     '也不代表灾难一定会发生或已经被阻止',
            'items': items}


def phase(session, story):
    """作者视图：当前阶段进度（含未生效阶段与阈值），只给作者与测试用。"""
    cfg = config(story)
    if cfg is None:
        return None
    block = session.get('pressure') or {}
    applied = block.get('applied') or {}
    return {
        'version': SCHEMA_VERSION,
        'time': session.get('time', 0),
        'pressures': [{
            'id': pressure.id, 'title': pressure.title,
            'stages': [{'id': stage.id, 'kind': stage.kind, 'at_hours': stage.at_hours,
                        'applied_at': applied.get(_stage_key(pressure.id, stage.id)),
                        'lifted': _stage_key(pressure.id, stage.id) in (block.get('lifted') or {}),
                        'cancelled': _stage_key(pressure.id, stage.id) in (block.get('cancelled') or {}),
                        'applied': _stage_key(pressure.id, stage.id) in applied,
                        'public': bool(stage.public_text), 'known_by': list(stage.known_by)}
                       for stage in pressure.stages]} for pressure in cfg.pressures],
        'log': list(block.get('log') or []),
        'note': '作者视图：含阈值与未发生阶段；玩家侧只走 known()/context()',
    }


def advance_hours(session, story, characters, hours, effects=None):
    """``advance`` 的别名，供既有代码以「推进小时」的语义调用，避免两处实现。"""
    return advance(session, story, characters, hours, effects=effects)


def digest(session):
    """压力状态指纹：用于「无重复效果」的测试与回滚对比。"""
    block = session.get('pressure') or {}
    text = repr(sorted((block.get('applied') or {}).items()))
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]
