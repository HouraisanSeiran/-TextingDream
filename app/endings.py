# -*- coding: utf-8 -*-
"""阶段结局：由**权威状态条件**判定，而不是由模型文字判定。

三条约束（两轮审查后的边界）：

1. **条件两两互斥（可验证的部分）**：条件按 ``priority`` 降序评估，第一个成立的即为结局。
   包校验时对每对结局条件的标记数做**有界精确枚举**（见 ``conditions_overlap()``）：
   在标记数 ≤ ``EXHAUSTIVE_FLAGS`` 时结论是精确的；超过上限时直接报错，
   不把未验证的情况当已验证。``allow_overlap`` 是显式豁免。
2. **标记来源覆盖（不是可达性证明）**：``flag_sources()`` 只检查结局声明的
   ``all_flags`` 在包里有没有人写过（动作/压力/日程/起点）。没来源 ⇒ 永不可能成立，
   因此可以拒；有来源 ⇒ 只说明不是漏写。真正的可达性由**故事包的具体路线测试**
   （三起点到真实结局的离线 E2E）证明，不由本模块声称。
3. **失败后仍可继续**：允许声明 ``continue_event``，让失败结局把玩家送进一段
   后续内容，而不是把存档卡死。
"""
from __future__ import annotations

import itertools
import re

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

MECHANICS_KEY = 'endings'
SCHEMA_VERSION = 1
ID = r'^[A-Za-z0-9_-]{1,60}$'
FLAG_RE = r'^[A-Za-z0-9_-]{1,60}$'
MAX_ENDINGS = 8
MAX_FLAGS = 16
MAX_TEXT = 400
# 互斥检查精确枚举的标记数上限（2^n 种赋值）；超过就明确拒绝，不冒充已验证。
EXHAUSTIVE_FLAGS = 14


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Condition(Strict):
    all_flags: dict[str, bool] = Field(default_factory=dict)
    any_flags: dict[str, bool] = Field(default_factory=dict)
    not_flags: list[str] = Field(default_factory=list, max_length=MAX_FLAGS)
    min_resources: dict[str, int] = Field(default_factory=dict)

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
                    raise ValueError('%s.%s 必须是 true/false' % (key, name))
        not_flags = data.get('not_flags')
        if not_flags is not None:
            if not isinstance(not_flags, list):
                raise ValueError('not_flags 必须是列表')
            for name in not_flags:
                if not isinstance(name, str) or not re.match(FLAG_RE, name):
                    raise ValueError('not_flags 的标记名无效：%r' % (name,))
        min_resources = data.get('min_resources')
        if min_resources is not None:
            if not isinstance(min_resources, dict):
                raise ValueError('min_resources 必须是对象')
            for name, value in min_resources.items():
                if not isinstance(name, str):
                    raise ValueError('min_resources 的键必须是文本')
                if isinstance(value, bool) or not isinstance(value, int):
                    raise ValueError('min_resources.%s 必须是整数（布尔不算）' % name)
                if value < 0:
                    raise ValueError('min_resources.%s 不能为负' % name)
        return data

    @model_validator(mode='after')
    def non_empty(self):
        if not (self.all_flags or self.any_flags or self.not_flags
                or self.min_resources):
            raise ValueError('结局条件不能为空（否则它会立刻成立）')
        return self


class Ending(Strict):
    id: str = Field(pattern=ID)
    title: str = Field(min_length=1, max_length=40)
    kind: Literal['saved', 'traded', 'lost', 'negotiated']
    summary: str = Field(min_length=1, max_length=MAX_TEXT)
    condition: Condition
    priority: int = Field(default=0, ge=0, le=100)
    # 失败结局可以接着玩：引擎在结束时把入口指向这里，而不是把存档挂死。
    continue_event: str | None = Field(default=None, max_length=60)
    allow_overlap: bool = Field(default=False)

    @model_validator(mode='before')
    @classmethod
    def raw_types(cls, data):
        """priority / allow_overlap 不接受 ``True``、``'50'``、``50.0`` 这类强制转换。"""
        if not isinstance(data, dict):
            return data
        if 'priority' in data:
            value = data['priority']
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError('结局 priority 必须是整数（布尔、文本、小数不接受）')
            if not 0 <= value <= 100:
                raise ValueError('结局 priority 必须在 0..100')
        if 'allow_overlap' in data and not isinstance(data['allow_overlap'], bool):
            raise ValueError('结局 allow_overlap 必须是 true/false（不接受 0/1 或文本）')
        return data


class Endings(Strict):
    version: int = Field(ge=1, le=1)
    note: str = Field(default='', max_length=300)
    endings: list[Ending] = Field(min_length=2, max_length=MAX_ENDINGS)

    @model_validator(mode='before')
    @classmethod
    def raw_types(cls, data):
        if isinstance(data, dict) and 'version' in data:
            value = data['version']
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError('结局配置版本必须是整数（布尔不算）')
            if value != SCHEMA_VERSION:
                raise ValueError('结局配置版本必须是 %d' % SCHEMA_VERSION)
        return data

    @model_validator(mode='after')
    def unique(self):
        ids = [e.id for e in self.endings]
        if len(set(ids)) != len(ids):
            raise ValueError('结局 ID 重复')
        priorities = [e.priority for e in self.endings]
        if len(set(priorities)) != len(priorities):
            # 同优先级会让「第一个成立的赢」变成列表顺序的偶然，直接拒绝。
            raise ValueError('结局的 priority 必须互不相同（否则判定依赖声明顺序）')
        return self


def config(story):
    mechanics = (story or {}).get('mechanics') or {}
    if not isinstance(mechanics, dict):
        return None
    raw = mechanics.get(MECHANICS_KEY)
    if raw is None:
        return None
    return Endings.model_validate(raw)


# ------------------------------------------------------------------ 条件求值
def matches(condition, session):
    flags = session.get('flags') or {}
    for name, value in condition.all_flags.items():
        if bool(flags.get(name, False)) != value:
            return False
    if condition.any_flags:
        if not any(bool(flags.get(name, False)) == value
                   for name, value in condition.any_flags.items()):
            return False
    for name in condition.not_flags:
        if bool(flags.get(name, False)):
            return False
    resources = ((session.get('local') or {}).get('resources') or {})
    for name, amount in condition.min_resources.items():
        if int(resources.get(name, 0)) < amount:
            return False
    return True


def resolve(session, story):
    """返回此刻成立的结局（按 priority 降序取第一个），或 None。**只读。**"""
    cfg = config(story)
    if cfg is None:
        return None
    for ending in sorted(cfg.endings, key=lambda e: (-e.priority, e.id)):
        if matches(ending.condition, session):
            return {'id': ending.id, 'title': ending.title, 'kind': ending.kind,
                    'summary': ending.summary, 'priority': ending.priority,
                    'continue_event': ending.continue_event}
    return None


def conditions_overlap(left, right):
    """两个条件能否同时成立：在**有界标记集内精确枚举**，不是启发式判断。

    只枚举两边的条件里出现过的标记（全部。any。not_flags），逐个赋值试一次。
    ``min_resources`` 都是下界，取较大者即可同时满足，所以不参与枚举。
    标记数超过 ``EXHAUSTIVE_FLAGS`` 时**明确报错**，而不是猜一个结论。
    """
    names = _condition_flags(left, right)
    if len(names) > EXHAUSTIVE_FLAGS:
        raise ValueError('结局条件涉及 %d 个标记，超过精确枚举上限 %d；'
                         '请减少标记或显式声明 allow_overlap（不冒充已验证互斥）'
                         % (len(names), EXHAUSTIVE_FLAGS))
    for bits in range(1 << len(names)):
        flags = {name: bool((bits >> index) & 1) for index, name in enumerate(names)}
        if _holds(left, flags) and _holds(right, flags):
            return True
    return False


def _condition_flags(*conditions):
    names = set()
    for condition in conditions:
        names |= set(condition.all_flags)
        names |= set(condition.any_flags)
        names |= set(condition.not_flags)
    return sorted(names)


def _holds(condition, flags):
    """纯标记求值（用于枚举验证；min_resources 不在这里判定）。"""
    for name, value in condition.all_flags.items():
        if flags.get(name, False) != bool(value):
            return False
    if condition.any_flags:
        if not any(flags.get(name, False) == bool(value)
                   for name, value in condition.any_flags.items()):
            return False
    for name in condition.not_flags:
        if flags.get(name, False):
            return False
    return True


def validate_package(story, characters=None):
    """包校验：条件引用真实存在的标记/资源，结局两两互斥，每个结局可达。"""
    cfg = config(story)
    if cfg is None:
        return None
    local = ((story or {}).get('mechanics') or {}).get('local') or {}
    resources = {r['id'] for r in local.get('resources') or []}
    events = {e['id']: e for e in (story or {}).get('events') or []}
    for ending in cfg.endings:
        unknown = set(ending.condition.min_resources) - resources
        if unknown:
            raise ValueError('结局 %s 引用了未声明的资源：%s'
                             % (ending.id, '、'.join(sorted(unknown))))
        if ending.continue_event is not None and ending.continue_event not in events:
            raise ValueError('结局 %s 的后续事件不存在：%s'
                             % (ending.id, ending.continue_event))
    # 互斥：两两比较；显式 allow_overlap 的除外。
    for left, right in itertools.combinations(cfg.endings, 2):
        if left.allow_overlap or right.allow_overlap:
            continue
        if conditions_overlap(left.condition, right.condition):
            raise ValueError('结局 %s 与 %s 的条件可能同时成立；'
                             '请加互斥标记或显式声明 allow_overlap'
                             % (left.id, right.id))
    # 标记来源覆盖：每个结局要的 all_flags 必须有人写过。它**不是**可达性证明。
    report = flag_sources(story)
    dead = {ending_id: row['missing_flags'] for ending_id, row in (report or {}).items()
            if not row['documented']}
    if dead:
        raise ValueError('结局引用了包里没有任何来源的标记：' + '；'.join(
            '%s 缺 %s' % (key, '、'.join(value)) for key, value in dead.items()))
    return cfg


def flag_sources(story):
    """每个结局的 ``all_flags`` 在包里是否**有已声明来源**。

    它只回答一个很窄的问题：这个标记有没有人能写出来——动作的 effects / success /
    failure、压力阶段效果、本地日程效果、起点声明。

    它**不是**可达性证明：没有来源 ⇒ 永远不可能成立（因此拒绝可以）；
    有来源 ⇒ 只能说明「不是漏写」，位置、时间窗、前置、资源是否付得起、
    互斥分支能不能都走到，这里一概不判断。也只看 ``all_flags``，
    不看 ``any_flags`` / ``not_flags`` / ``min_resources``。
    """
    cfg = config(story)
    if cfg is None:
        return None
    story = story or {}
    sources = set()
    for event in story.get('events') or []:
        for action in event.get('actions') or []:
            for branch in ('effects', 'success', 'failure'):
                for effect in action.get(branch) or []:
                    if effect.get('op') == 'flag':
                        sources.add(effect.get('id'))
    mechanics = story.get('mechanics') or {}
    for pressure in ((mechanics.get('pressure') or {}).get('pressures') or []):
        for stage in pressure.get('stages') or []:
            for effect in stage.get('effects') or []:
                if effect.get('op') == 'flag':
                    sources.add(effect.get('id'))
    for timer in ((mechanics.get('local') or {}).get('schedules') or []):
        for effect in timer.get('effects') or []:
            if effect.get('op') == 'flag':
                sources.add(effect.get('id'))
    for profile in ((mechanics.get('start_profiles') or {}).get('profiles') or []):
        for name in (profile.get('flags') or {}):
            sources.add(name)
    report = {}
    for ending in cfg.endings:
        missing = [name for name, value in ending.condition.all_flags.items()
                   if value and name not in sources]
        report[ending.id] = {'documented': not missing, 'missing_flags': missing}
    return report
