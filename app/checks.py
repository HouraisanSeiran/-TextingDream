# -*- coding: utf-8 -*-
"""判定系统 v2（d20）结算核心：纯规则，模型只负责表达。

规格见 ``docs/check-system-v2.md``。本模块只做三件事：

1. **解析与校验**作者声明（``mechanics.checks``，``version: 2``）；
2. **确定性结算**：d20 骰面、处境/档位、修正因素、社交底线与自动成功、
   重试与加码、察觉检定、进度钟与危险钟；
3. **公开投影**：只给玩家与模型「已经发生且允许公开」的部分——隐藏因素、
   NPC 秘密（底线/兴趣/信任数值）、未察觉者、隐藏钟一律不进投影。

它**不改**任何游戏状态：``plan()`` / ``roll()`` / ``consequences()`` 都是纯函数，
真正写 session 的只有 ``Runtime._apply_effects``（``clock`` op）和调用方拿到的
effect/relationship 列表。没有 ``mechanics.checks`` 的旧包在本模块里全部 no-op，
既有 ``attribute_v1`` 路径逐字节不变。

三条与规格对齐的硬边界：

* **天然覆盖按模式**：旧五档优先天然 1/20；margin_four 默认只看差值，作者可显式开启覆盖。
* **骰子只由引擎算**：``d = sha256(seed)[:12] % 20 + 1``；优势/劣势第二颗用
  ``seed + ":b"``。模型拿不到任何可改结果的输入。
* **叠加不重复**：钟一旦满格不再变化；作者已经用 ``clock`` op 手动推进的钟，
  引擎不再按档位自动推第二次；危险钟同理。
"""
from __future__ import annotations

import hashlib
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from . import attributes

MECHANICS_KEY = 'checks'
SCHEMA_VERSION = 2
RULES_VERSION = 'd20_v2'
MARGIN_RULES_VERSION = 'd20_margin_v3'
FOUR_TIERS = ('critical', 'success', 'failure', 'disaster')
ID = r'^[A-Za-z0-9_-]{1,60}$'
FLAG_ID = r'^[A-Za-z0-9_.:-]{1,80}$'
MAX_FACTORS = 60
MAX_PUSH = 20
MAX_CLOCKS = 24
MAX_EFFECTS = 12

POSITIONS = ('controlled', 'risky', 'desperate')
EFFECTS = ('limited', 'standard', 'great')
TIERS = ('critical', 'success', 'partial', 'setback', 'disaster')
TIERS_SUCCESS = ('critical', 'success', 'partial')
EFFECT_SEGMENTS = {'limited': 1, 'standard': 2, 'great': 3}
EFFECT_UPGRADE = {'limited': 'standard', 'standard': 'great', 'great': 'great'}

TIER_LABELS = {'critical': '大成功', 'success': '成功', 'partial': '成功但有代价',
               'setback': '失败但前进', 'disaster': '失败且恶化', 'refused': '拒绝'}
POSITION_LABELS = {'controlled': '稳妥', 'risky': '冒险', 'desperate': '孤注一掷'}
EFFECT_LABELS = {'limited': '有限', 'standard': '标准', 'great': '显著'}

#: 作者可以在 tier / on_full 里写的效果 op = 既有 ``Runtime._apply_effects`` 的 op
#: 再加 v2 的 ``clock``。``reward`` 也在这里，但只允许在声明了 mechanics.rewards 的包里。
EFFECT_OPS = ('flag', 'take', 'fact', 'rumor', 'status', 'resource', 'information',
              'health', 'reward', 'clock')

#: 玩家可见/模型可见的文案。全部是**不确定语气**：引擎不知道谁看见了什么时，
#: 绝不说「没人看到」，只说「似乎没人注意」。
NOTICED_SOME = '似乎有人注意到了'
NOTICED_VISIBLE = '似乎有人注意到了，你看得见其中的人'
NOTICED_NONE = '似乎没有旁人注意到'
GENERIC_PARTIAL = '做到了，但不太体面'
GENERIC_SETBACK = '没成，但你看清了阻碍在哪'
BLOCKED_TEXT = '同样的办法刚失败过：换个方法、找帮手、做准备或等局面变化'
DEFAULT_REFUSAL = '这触到了他的底线'
ABSENT_REFUSAL = '这个人此刻不在场'

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


# --------------------------------------------------------------------- 条件
class When(Strict):
    """修正因素/自动成功的条件。**封闭清单**：只有这七种，模型与玩家都不能自称。

    与既有项目约定一致的部分：``visibility: author`` 与未成立的 ``reveal_flag``
    一律视为「玩家看不见」，因此由这类目标派生出来的因素标记为 hidden，
    仍然参与结算，但不进任何公开投影。
    """
    model_config = ConfigDict(extra='forbid', populate_by_name=True)

    kind: Literal['item', 'flag', 'companion', 'profile', 'place', 'time', 'attribute_axis']
    id: str | None = Field(default=None, max_length=80)
    template: str | None = Field(default=None, max_length=80)
    value: bool = True
    min_trust: float = Field(default=0.0, ge=0, le=1, allow_inf_nan=False)
    tag: str | None = Field(default=None, max_length=60)
    start: int | None = Field(default=None, alias='from', ge=0, le=23)
    end: int | None = Field(default=None, alias='to', ge=0, le=24)
    attribute: str | None = Field(default=None, max_length=20)

    @model_validator(mode='after')
    def shape(self):
        kind = self.kind
        if kind == 'item':
            if not self.id and not self.template:
                raise ValueError('item 条件需要 id（持有物品）或 template（奖励实例模板）')
            if self.id and self.template:
                raise ValueError('item 条件只能写 id 或 template 之一')
        elif kind == 'flag':
            if not self.id:
                raise ValueError('flag 条件需要 id')
        elif kind == 'companion':
            if not self.id:
                raise ValueError('companion 条件需要 id')
        elif kind == 'profile':
            if not self.id:
                raise ValueError('profile 条件需要 id（开局起点 id）')
        elif kind == 'place':
            if not self.id and not self.tag:
                raise ValueError('place 条件需要 id（地点）或 tag（地点标签）')
            if self.id and self.tag:
                raise ValueError('place 条件只能写 id 或 tag 之一')
        elif kind == 'time':
            if self.start is None or self.end is None:
                raise ValueError('time 条件需要 from 与 to（游戏小时，可跨午夜）')
            if self.start == self.end:
                raise ValueError('time 条件的 from 与 to 不能相同（那是空区间）')
        elif kind == 'attribute_axis':
            if not self.attribute:
                raise ValueError('attribute_axis 条件需要 attribute')
        return self


# --------------------------------------------------------------------- 因素
class Factor(Strict):
    """一条修正因素：``mod`` −3..+3，或 advantage/disadvantage。

    ``visibility: hidden`` 表示这条因素**只在引擎内部生效**：它照常改骰，
    但标签与符号都不出现在候选、确认预览和结算公开结果里（防止用因素标签
    反推隐藏标记、隐藏 NPC 或未发现的事实）。
    """
    id: str = Field(pattern=ID)
    label: str = Field(min_length=1, max_length=80)
    mod: int = Field(default=0, ge=-3, le=3, strict=True)
    advantage: bool = False
    disadvantage: bool = False
    visibility: Literal['public', 'hidden'] = 'public'
    when: When

    @model_validator(mode='after')
    def shape(self):
        if self.mod and (self.advantage or self.disadvantage):
            raise ValueError('因素 %s：mod 与 advantage/disadvantage 不能同时写' % self.id)
        return self


# --------------------------------------------------------------------- 加码
class PushRelationship(Strict):
    #: 只允许指向本次检定的社交目标（``check.social.target``），不开放任意人物：
    #: 加码代价不能变成「随便扣某人的信任」。
    target: Literal['check_target'] = 'check_target'
    delta: float = Field(ge=-0.2, le=0.2, allow_inf_nan=False)


class PushOption(Strict):
    id: str = Field(pattern=ID)
    label: str = Field(min_length=1, max_length=80)
    cost: dict[str, int] = Field(default_factory=dict)
    bonus: int = Field(default=0, ge=-5, le=5, strict=True)
    fatigue: float = Field(default=0.0, ge=0, le=1, allow_inf_nan=False)
    advantage: bool = False
    relationship: PushRelationship | None = None


# --------------------------------------------------------------------- 钟
class ClockSpec(Strict):
    id: str = Field(pattern=ID)
    label: str = Field(min_length=1, max_length=80)
    segments: int = Field(ge=1, le=24, strict=True)
    kind: Literal['progress', 'danger'] = 'progress'
    #: 只有列在这里的受众看得到这个钟（含 label/segments/filled）。
    known_by: list[str] = Field(default_factory=lambda: ['player'], max_length=12)
    on_full: list[dict] = Field(default_factory=list, max_length=MAX_EFFECTS)


# --------------------------------------------------------------------- 社交
class SocialProfile(Strict):
    """NPC 社交画像：作者显式声明，**不从自然语言猜**。

    ``boundaries`` 是底线（撞上就拒绝，不掷骰），``interests`` 是有效诉求
    （每命中一项 DC −3，最多 −6），``trust_weight`` 决定信任对 DC 的权重。
    这三样都**不进**任何玩家/模型投影：玩家只会看到通用拒绝句或作者写的
    ``refusal_text``。
    """
    interests: list[str] = Field(default_factory=list, max_length=12)
    boundaries: list[str] = Field(default_factory=list, max_length=12)
    trust_weight: int = Field(default=10, ge=0, le=40, strict=True)
    refusal_text: str = Field(default='', max_length=200)
    #: 可选的公开阻碍说明（目标不在场时用）；不写就用通用句。
    absent_text: str = Field(default='', max_length=200)


# --------------------------------------------------------------------- 默认代价
class DefaultCost(Strict):
    """成功但有代价（partial）时引擎自取的默认代价。

    只在作者**没有**为该动作写 ``tiers.partial`` 时使用，按声明顺序取第一条
    当前可执行的；都不可执行时只写一条公开回执。
    """
    kind: Literal['time', 'resource', 'relationship', 'flag']
    hours: int | None = Field(default=None, ge=1, le=24)
    id: str | None = Field(default=None, max_length=80)
    amount: int | None = Field(default=None, ge=1, le=1000000)
    target: Literal['present'] | None = None
    delta: float | None = Field(default=None, ge=-0.05, le=0.05, allow_inf_nan=False)
    value: bool = True

    @model_validator(mode='after')
    def shape(self):
        if self.kind == 'time':
            if not self.hours:
                raise ValueError('time 代价需要 hours')
        elif self.kind == 'resource':
            if not self.id or not self.amount:
                raise ValueError('resource 代价需要 id 与 amount')
        elif self.kind == 'relationship':
            if self.target != 'present' or self.delta is None:
                raise ValueError('relationship 代价需要 target="present" 与 delta')
        elif self.kind == 'flag':
            if not self.id:
                raise ValueError('flag 代价需要 id')
        return self


class RetryConfig(Strict):
    same_approach: Literal['refuse', 'harder'] = 'refuse'


class _AutoGate(Strict):
    """自动成功门槛：任一子条件可省，但不能一个都不写。"""

    all_flags: dict[str, bool] = Field(default_factory=dict)
    items: list[str] = Field(default_factory=list, max_length=12)
    max_dc: int | None = Field(default=None, ge=2, le=30, strict=True)

    @model_validator(mode='after')
    def not_empty(self):
        if not self.all_flags and not self.items and self.max_dc is None:
            raise ValueError('check.auto 不能是空条件：至少写 all_flags / items / max_dc 之一')
        return self


def _check_auto(raw):
    return _AutoGate.model_validate(raw)


# --------------------------------------------------------------------- 包级配置
class MarginThresholds(Strict):
    critical: int = Field(default=10, strict=True)
    success: int = Field(default=0, strict=True)
    disaster: int = Field(default=-10, strict=True)

    @model_validator(mode='after')
    def ordered(self):
        if not self.disaster < self.success < self.critical:
            raise ValueError('thresholds 必须满足 disaster < success < critical')
        return self


class ChecksConfig(Strict):
    version: int = Field(strict=True)
    tier_mode: Literal['legacy_five', 'margin_four'] = 'legacy_five'
    thresholds: MarginThresholds = Field(default_factory=MarginThresholds)
    natural_override: bool = Field(default=False, strict=True)

    @model_validator(mode='after')
    def mode_options(self):
        if self.version != SCHEMA_VERSION:
            raise ValueError('mechanics.checks.version 必须是 2')
        if self.tier_mode == 'legacy_five' and (
                {'thresholds', 'natural_override'} & self.model_fields_set):
            raise ValueError('thresholds/natural_override 仅适用于 margin_four')
        return self
    die: Literal['d20'] = 'd20'
    display: Literal['transparent', 'qualitative'] = 'transparent'
    default_position: Literal['controlled', 'risky', 'desperate'] = 'risky'
    default_effect: Literal['limited', 'standard', 'great'] = 'standard'
    factors: list[Factor] = Field(default_factory=list, max_length=MAX_FACTORS)
    push: list[PushOption] = Field(default_factory=list, max_length=MAX_PUSH)
    clocks: list[ClockSpec] = Field(default_factory=list, max_length=MAX_CLOCKS)
    social: dict[str, SocialProfile] = Field(default_factory=dict)
    default_costs: list[DefaultCost] = Field(default_factory=list, max_length=8)
    retry: RetryConfig = Field(default_factory=RetryConfig)

    @model_validator(mode='after')
    def unique_ids(self):
        for name, rows in (('factors', self.factors), ('push', self.push),
                           ('clocks', self.clocks)):
            ids = [row.id for row in rows]
            if len(set(ids)) != len(ids):
                raise ValueError('mechanics.checks.%s 的 id 重复' % name)
        return self


def config(story):
    """作者声明或 ``None``（没有这个键 → 本模块全部 no-op，旧包一字不变）。"""
    mechanics = (story or {}).get('mechanics')
    if not isinstance(mechanics, dict):
        return None
    raw = mechanics.get(MECHANICS_KEY)
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError('mechanics.%s 必须是对象' % MECHANICS_KEY)
    return ChecksConfig.model_validate(raw)


def enabled(story):
    return config(story) is not None


# --------------------------------------------------------------------- 工具
def _axis(name):
    axis = attributes.ALIASES.get(name, name)
    if axis not in attributes.AXES:
        raise ValueError('判定属性必须是六项属性之一（得到 %r）' % (name,))
    return axis


def modifier(value):
    """``round((属性值 − 50) / 5)``：0–100 → −10..+10。"""
    return int(round((float(value) - 50) / 5))


def fatigue_penalty(fatigue):
    return -int(round(float(fatigue) * 4))


def effect_segments(effect):
    return EFFECT_SEGMENTS[effect]


def upgrade_effect(effect):
    return EFFECT_UPGRADE[effect]


def tier_success(tier):
    """兼容布尔：``success = tier in (critical, success, partial)``。"""
    return tier in TIERS_SUCCESS


def _clamp(value, low, high):
    return max(low, min(high, value))


def _hero_status(session):
    return (session.get('characters') or {}).get(session.get('hero'), {}).get('status') or {}


def _char_value(characters, cid, axis, default=None):
    """取一个人的属性值。

    ``default`` 只给**主角**用：与 v1 的回退口径一致——属性缺失时按 50（修正 0）算，
    而不是让「没带上人物文档」变成一次必然失败。NPC 的属性没有回退：那会把一个不存在
    的人当成在场者，所以仍然报错。
    """
    actor = next((c for c in (characters or {}).get('characters') or [] if c['id'] == cid), None)
    if actor is None:
        if default is not None:
            return default
        raise ValueError('人物不存在：' + str(cid))
    values = attributes.values(actor.get('attributes'),
                               legacy=set(actor.get('attributes') or {}) != set(attributes.AXES))
    return values[axis]


def _trust(session, cid):
    return ((session.get('development') or {}).get(cid, {})
            .get('relationships', {}).get(session.get('hero'), {}).get('trust', 0.5))


def _npc_seat(session, cid):
    return ((session.get('characters') or {}).get(cid) or {}).get('location')


def _present(session, node, characters):
    """与主角同地、且在本次事件里出场的 NPC id（确定性顺序）。"""
    hero = session.get('hero')
    rows = []
    for cid in sorted((node or {}).get('participants') or []):
        if cid == hero:
            continue
        if _npc_seat(session, cid) != session.get('location'):
            continue
        rows.append(cid)
    return rows


def _npc_visible(character, session):
    """作者没把这个 NPC 藏起来、且揭示标记已成立。"""
    if character is None:
        return False
    if character.get('visibility') == 'author':
        return False
    flag = character.get('reveal_flag')
    if isinstance(flag, str) and flag and not ((session.get('flags') or {}).get(flag)):
        return False
    return True


def _item_visible(item, session):
    if not isinstance(item, dict):
        return False
    if item.get('visibility') == 'author':
        return False
    flag = item.get('reveal_flag')
    if isinstance(flag, str) and flag and not ((session.get('flags') or {}).get(flag)):
        return False
    return True


def _by_id(rows):
    return {row['id']: row for row in rows or []}


def _place(session, story):
    place_id = session.get('location')
    return next((p for p in story.get('locations') or [] if p['id'] == place_id), None)


# --------------------------------------------------------------------- 条件求值
def when_matches(when, session, story, characters, attribute=None):
    """引擎判定条件是否成立。**只读** session/story/characters，不看模型文本。"""
    if when is None:
        return True
    kind = when.kind
    if kind == 'item':
        if when.id:
            if when.id not in (session.get('inventory') or []):
                return False
        else:
            instances = ((session.get('rewards') or {}).get('items') or [])
            if not any(row.get('template') == when.template
                       and row.get('owner') in (None, 'player') for row in instances):
                return False
        return True
    if kind == 'flag':
        return bool((session.get('flags') or {}).get(when.id, False)) == bool(when.value)
    if kind == 'companion':
        if _npc_seat(session, when.id) != session.get('location'):
            return False
        return _trust(session, when.id) >= when.min_trust
    if kind == 'profile':
        return ((session.get('start') or {}).get('profile_id') == when.id)
    if kind == 'place':
        place = _place(session, story)
        if place is None:
            return False
        if when.id:
            return place['id'] == when.id
        tags = [str(tag) for tag in (place.get('tags') or [])]
        return when.tag in tags
    if kind == 'time':
        hour = int(session.get('time', 0)) % 24
        start, end = when.start, when.end
        if start < end:
            return start <= hour < end
        return hour >= start or hour < end
    if kind == 'attribute_axis':
        return attribute is not None and _axis(attribute) == _axis(when.attribute)
    raise ValueError('未支持的条件类型：' + str(kind))


def _condition_visible(when, session, story, characters):
    """条件来源对玩家是否可见（不可见 → 派生因素标为 hidden，不泄露标签）。"""
    if when is None:
        return True
    if when.kind == 'item':
        items = _by_id(story.get('items') or [])
        if when.id:
            item = items.get(when.id)
            return _item_visible(item, session) if item is not None else False
        return True
    if when.kind == 'companion':
        actor = next((c for c in (characters or {}).get('characters') or []
                      if c['id'] == when.id), None)
        return _npc_visible(actor, session)
    if when.kind == 'place':
        place = _place(session, story)
        return place is not None
    return True


# --------------------------------------------------------------------- 因素
def factor_rows(session, story, characters, action, attribute):
    """本次检定实际适用的因素（含作者的全局库与动作内联）。

    **全部由引擎判定**：玩家不能自称，模型不参与；返回顺序 = 全局声明序 + 动作内联序。
    """
    cfg = config(story)
    if cfg is None:
        return []
    check = (action or {}).get('check') or {}
    inline = []
    for raw in check.get('factors') or []:
        inline.append(Factor.model_validate(raw) if 'when' in raw else _resolve_ref(cfg, raw))
    rows = []
    for factor in list(cfg.factors) + inline:
        if factor is None:
            continue
        if not when_matches(factor.when, session, story, characters, attribute):
            continue
        visibility = factor.visibility
        if visibility == 'public' and not _condition_visible(
                factor.when, session, story, characters):
            visibility = 'hidden'
        rows.append({'id': factor.id, 'label': factor.label, 'mod': factor.mod,
                     'advantage': factor.advantage, 'disadvantage': factor.disadvantage,
                     'visibility': visibility})
    return rows


def _resolve_ref(cfg, raw):
    """动作内联因素：要么引用全局 id（字符串），要么写完整对象。"""
    if isinstance(raw, str):
        row = next((f for f in cfg.factors if f.id == raw), None)
        if row is None:
            raise ValueError('因素引用不存在：' + raw)
        return row
    return Factor.model_validate(raw)


def factor_summary(rows, transparent=True, numeric=False):
    """公开因素投影：只给 label 与有利/不利。

    规格 §5：玩家**预览**只给 label 与「有利 / 不利」，不给数字；数字（``mod``）
    只在 ``display=transparent`` 的**结算后**结果里给（``numeric=True``）。
    """
    out = []
    for row in rows:
        if row['visibility'] != 'public':
            continue
        sign = '+'
        if row['disadvantage'] or row['mod'] < 0:
            sign = '-'
        item = {'label': row['label'], 'sign': sign}
        if numeric and transparent:
            if row['advantage']:
                item['advantage'] = True
            elif row['disadvantage']:
                item['disadvantage'] = True
            elif row['mod']:
                item['mod'] = row['mod']
        out.append(item)
    return out


def factor_mod(rows):
    return _clamp(sum(row['mod'] for row in rows), -5, 5)


def _net_advantage(rows, push_option):
    advantaged = any(row['advantage'] for row in rows) or bool(
        push_option and push_option.advantage)
    disadvantaged = any(row['disadvantage'] for row in rows)
    if advantaged and disadvantaged:
        return None
    if advantaged:
        return 'advantage'
    if disadvantaged:
        return 'disadvantage'
    return None


# --------------------------------------------------------------------- 钟
def clock_state(session, story):
    """``{id: {'filled': n, 'full_at': time|None}}``，缺失按 0 读（只读）。"""
    cfg = config(story)
    if cfg is None:
        return {}
    block = session.get('clocks') or {}
    return {spec.id: {'filled': int((block.get(spec.id) or {}).get('filled', 0)),
                      'full_at': (block.get(spec.id) or {}).get('full_at')}
            for spec in cfg.clocks}


def ensure(session, story):
    """在**候选** session 上建立钟与尝试记录；未配置时返回 ``None`` 且不加任何键。

    只在写路径（new_session / 结算前）调用；只读投影一律用 ``clock_state`` 或
    ``session.get('clocks')``，所以 GET 不会因为读一次就改状态。
    """
    cfg = config(story)
    if cfg is None:
        return None
    block = session.setdefault('clocks', {})
    for spec in cfg.clocks:
        row = block.setdefault(spec.id, {'filled': 0, 'full_at': None})
        row.setdefault('filled', 0)
        row.setdefault('full_at', None)
    session.setdefault('check_attempts', {})
    return cfg


def public_clocks(session, story, audience='player'):
    """该受众可见的钟：只有 ``known_by`` 含它的钟才出现（隐藏钟完全不出现）。"""
    cfg = config(story)
    if cfg is None:
        return []
    state = clock_state(session, story)
    rows = []
    for spec in cfg.clocks:
        if audience not in spec.known_by:
            continue
        row = state[spec.id]
        rows.append({'id': spec.id, 'label': spec.label, 'segments': spec.segments,
                     'filled': row['filled'], 'kind': spec.kind})
    return rows


def clock_public_row(session, story, clock_id):
    cfg = config(story)
    if cfg is None:
        return None
    spec = next((c for c in cfg.clocks if c.id == clock_id), None)
    if spec is None:
        return None
    state = clock_state(session, story)[clock_id]
    return {'label': spec.label, 'segments': spec.segments, 'filled': state['filled'],
            'kind': spec.kind, 'known_by': list(spec.known_by)}


def advance_clock(session, story, clock_id, delta, effects=None, source=''):
    """推进/回退一个钟；满格时 ``on_full`` 恰好执行一次，满格后不再变化。

    这是 ``clock`` 效果的唯一实现，由 ``Runtime._apply_effects`` 调用：
    钟的状态属于快照（``session['clocks']``），随回滚一起恢复。
    """
    cfg = config(story)
    if cfg is None:
        raise ValueError('这个故事包没有声明 mechanics.checks.clocks')
    spec = next((c for c in cfg.clocks if c.id == clock_id), None)
    if spec is None:
        raise ValueError('未声明的钟：' + str(clock_id))
    if isinstance(delta, bool) or not isinstance(delta, int):
        raise ValueError('钟的变化必须是整数')
    block = session.setdefault('clocks', {})
    row = block.setdefault(clock_id, {'filled': 0, 'full_at': None})
    row.setdefault('full_at', None)
    before = int(row.get('filled', 0))
    if row['full_at'] is not None:
        # 满格以后不再变化：重复加码不会制造第二次满格效果。
        return {'id': clock_id, 'label': spec.label, 'kind': spec.kind,
                'segments': spec.segments, 'from': before, 'to': before,
                'changed': False, 'full': True}
    after = _clamp(before + int(delta), 0, spec.segments)
    row['filled'] = after
    changed = after != before
    if after >= spec.segments:
        row['full_at'] = session.get('time', 0)
        if spec.on_full:
            if effects is None:
                raise ValueError('钟的满格效果必须由 Runtime.effects 应用')
            effects(session, [dict(effect) for effect in spec.on_full],
                    'clock:%s' % clock_id)
    return {'id': clock_id, 'label': spec.label, 'kind': spec.kind,
            'segments': spec.segments, 'from': before, 'to': after,
            'changed': changed, 'full': after >= spec.segments}


# --------------------------------------------------------------------- 社交
def social_target(action):
    return ((action or {}).get('check') or {}).get('social', {}).get('target')


def social_gate(session, story, characters, node, action, push_option=None):
    """社交门槛：底线、诉求、信任 → 拒绝 / DC 调整。**不掷骰**。

    底线与诉求来自作者声明的 social 画像，不来自自然语言：模型既不能提出诉求，
    也不能替 NPC 决定底线。
    """
    cfg = config(story)
    check = (action or {}).get('check') or {}
    raw = check.get('social')
    if cfg is None or raw is None:
        return {'present': True, 'refused': None, 'dc_delta': 0, 'target': None,
                'refusal_text': None}
    target = raw.get('target')
    profile = cfg.social.get(target)
    if not target:
        raise ValueError('check.social 需要 target')
    if characters is not None and not any(
            c['id'] == target for c in characters.get('characters') or []):
        # 有作者人物文档时，社交目标必须真实存在（打包/运行都会传）。
        raise ValueError('check.social.target 引用了不存在的角色：%r' % (target,))
    if target not in _present(session, node, characters):
        text = (profile.absent_text if profile and profile.absent_text else ABSENT_REFUSAL)
        return {'present': False, 'refused': text, 'dc_delta': 0, 'target': target,
                'refusal_text': text}
    if profile is None:
        return {'present': True, 'refused': None, 'dc_delta': 0, 'target': target,
                'refusal_text': None}
    violations = set(raw.get('violates') or []) & set(profile.boundaries)
    if violations:
        text = profile.refusal_text or DEFAULT_REFUSAL
        return {'present': True, 'refused': text, 'dc_delta': 0, 'target': target,
                'refusal_text': text}
    appeals = set(raw.get('appeals') or []) & set(profile.interests)
    delta = -3 * min(2, len(appeals))
    trust = _trust(session, target)
    if push_option is not None and push_option.relationship is not None:
        # 加码里的关系代价在掷骰前扣除，所以它也会影响到难度。
        trust = _clamp(trust + push_option.relationship.delta, 0, 1)
    delta -= int(round((trust - 0.5) * profile.trust_weight))
    return {'present': True, 'refused': None, 'dc_delta': delta, 'target': target,
            'refusal_text': None}


# --------------------------------------------------------------------- 重试
def signature(action, push_id=None):
    """这次尝试的「做法」指纹：属性 + 因素集合 + 是否加码。"""
    check = (action or {}).get('check') or {}
    return {'attribute': _axis(check.get('attribute')),
            'factors': sorted(str(row) for row in (check.get('factors') or [])
                              if isinstance(row, str)),
            'push': push_id or None}


def attempt_key(node, action):
    return '%s:%s' % ((node or {}).get('id', ''), (action or {}).get('id', ''))


def attempts(session, node, action):
    log = (session.get('check_attempts') or {}).get(attempt_key(node, action)) or []
    return list(log)


def retry_gate(session, story, node, action, push_id=None):
    """重试门槛：同样的做法刚失败过 → 拒绝（refuse）或更难（harder，最多 +9）。"""
    cfg = config(story)
    if cfg is None:
        return {'repeats': 0, 'blocked': False, 'dc_bonus': 0}
    log = attempts(session, node, action)
    if not log:
        return {'repeats': 0, 'blocked': False, 'dc_bonus': 0}
    current = signature(action, push_id)
    same = [row for row in log
            if row.get('tier') in ('failure', 'setback', 'disaster')
            and row.get('attribute') == current['attribute']
            and list(row.get('factors') or []) == current['factors']
            and not current['push']]
    if not same:
        return {'repeats': 0, 'blocked': False, 'dc_bonus': 0}
    repeats = len(same)
    if cfg.retry.same_approach == 'refuse':
        return {'repeats': repeats, 'blocked': True, 'dc_bonus': 0}
    return {'repeats': repeats, 'blocked': False, 'dc_bonus': 3 * min(3, repeats)}


def record_attempt(session, node, action, tier, push_id=None):
    """记一次尝试（写路径）。回滚时随快照恢复。"""
    block = session.setdefault('check_attempts', {})
    sig = signature(action, push_id)
    block.setdefault(attempt_key(node, action), []).append(
        {'attribute': sig['attribute'], 'factors': sig['factors'],
         'push': sig['push'], 'tier': tier})


# --------------------------------------------------------------------- 自动成功
def auto_gate(session, story, action, dc):
    """条件成立或最终 DC ≤ max_dc → 直接判 success，不掷骰。空条件绝不自动成功。"""
    raw = ((action or {}).get('check') or {}).get('auto')
    if raw is None:
        return {'auto': False, 'reason': None}
    gate = _check_auto(raw)
    flags = session.get('flags') or {}
    if gate.all_flags and all(flags.get(k, False) == v for k, v in gate.all_flags.items()):
        return {'auto': True, 'reason': '准备充分：本次无需掷骰'}
    if gate.items and all(item in (session.get('inventory') or []) for item in gate.items):
        return {'auto': True, 'reason': '你带着需要用上的东西：本次无需掷骰'}
    if gate.max_dc is not None and dc <= gate.max_dc:
        return {'auto': True, 'reason': '难度已经低到不需要掷骰'}
    return {'auto': False, 'reason': None}


# --------------------------------------------------------------------- DC
def base_dc(check):
    if check.get('dc') is not None:
        dc = int(check['dc'])
        if not 2 <= dc <= 30:
            raise ValueError('check.dc 必须在 2..30')
        return dc
    difficulty = check.get('difficulty')
    if difficulty is None:
        raise ValueError('check 需要 dc 或 difficulty')
    return 11 + int(round((float(difficulty) - 0.5) * 20))


# --------------------------------------------------------------------- 主流程
def plan(session, story, characters, node, action, push=None):
    """一次检定的**纯计算**结果：处境、效果、因素、DC、加码、社交门槛、重试、自动成功。

    候选预览、确认预览与真正结算都用它，所以界面看到的与结算时用的是同一份判断，
    不存在「预览说能掷、执行时换了难度」的缺口。
    """
    cfg = config(story)
    if cfg is None:
        raise ValueError('这个故事包没有开启判定 v2')
    check = (action or {}).get('check')
    if not check:
        raise ValueError('这个动作没有检定')
    attribute = _axis(check.get('attribute'))
    position = check.get('position') or cfg.default_position
    if position not in POSITIONS:
        raise ValueError('未知处境：' + str(position))
    effect = check.get('effect') or cfg.default_effect
    if effect not in EFFECTS:
        raise ValueError('未知效果：' + str(effect))
    if position == 'desperate':
        effect = upgrade_effect(effect)
    allowed = check.get('push_allowed')
    push_option = None
    if push:
        push_option = next((row for row in cfg.push if row.id == push), None)
        if push_option is None:
            raise ValueError('没有这个加码选项：' + str(push))
        if allowed is not None and push not in allowed:
            raise ValueError('这个动作不能用这个加码：' + str(push))
    rows = factor_rows(session, story, characters, action, attribute)
    f_mod = factor_mod(rows)
    advantage = _net_advantage(rows, push_option)
    hero = session.get('hero')
    # 主角属性缺失时按 50（修正 0）——与 v1 的 `hero.get('attributes',{}).get(..., .5)` 一致。
    hero_value = _char_value(characters, hero, attribute, default=50)
    mod = modifier(hero_value)
    fatigue = float(_hero_status(session).get('疲劳', 0) or 0)
    fatigue_pen = fatigue_penalty(fatigue)
    push_bonus = push_option.bonus if push_option is not None else 0
    social = social_gate(session, story, characters, node, action, push_option)
    retry = retry_gate(session, story, node, action, push)
    dc = base_dc(check) + social['dc_delta'] + retry['dc_bonus']
    dc = _clamp(dc, 2, 30)
    auto = auto_gate(session, story, action, dc)
    total_mod = mod + fatigue_pen + f_mod + push_bonus
    probability = chance(total_mod, dc, advantage)
    if cfg.tier_mode == 'margin_four':
        faces = [(face, face) for face in range(1, 21)] if advantage is None else [
            (a, b) for a in range(1, 21) for b in range(1, 21)]
        wins = 0
        for a, b in faces:
            face = min(a, b) if advantage == 'disadvantage' else max(a, b)
            wins += tier_success(margin_tier(face, face + total_mod - dc, cfg))
        probability = wins / len(faces)
    return {'rule_config': cfg.model_dump() if cfg.tier_mode == 'margin_four' else None,
            'attribute': attribute, 'position': position, 'effect': effect,
            'factors': rows, 'factor_mod': f_mod, 'modifier': mod,
            'fatigue': fatigue, 'fatigue_pen': fatigue_pen,
            'push': push_option, 'push_bonus': push_bonus, 'advantage': advantage,
            'dc': dc, 'social': social, 'retry': retry, 'auto': auto,
            'total_mod': total_mod,
            'chance': 1.0 if auto['auto'] and cfg.tier_mode == 'margin_four' else probability,
            'refused': social['refused'],
            'blocked': BLOCKED_TEXT if retry['blocked'] else None}


def chance(total_mod, dc, advantage):
    """按当前总修正与 DC 精确算成功率（0..1）。天然 1/20 的覆盖不在其中：
    它只影响档位，不改变「掷到多少算成功」的习惯表达。"""
    def hit(face):
        return face + total_mod >= dc
    if advantage is None:
        return sum(1 for face in range(1, 21) if hit(face)) / 20.0
    wins = 0
    for first in range(1, 21):
        for second in range(1, 21):
            face = max(first, second) if advantage == 'advantage' else min(first, second)
            if hit(face):
                wins += 1
    return wins / 400.0


def chance_label(value):
    if value >= 0.65:
        return '大'
    if value >= 0.35:
        return '中'
    return '小'


def roll_d20(seed, advantage=None):
    """确定性 d20：同一 seed 永远同一骰面；优势/劣势再掷一颗（seed + ":b"）。"""
    def face(key):
        digest = hashlib.sha256(str(key).encode('utf-8')).hexdigest()
        return int(digest[:12], 16) % 20 + 1
    first = face(seed)
    if advantage is None:
        return {'dice': [first], 'kept': first, 'advantage': None}
    second = face(str(seed) + ':b')
    if advantage == 'advantage':
        kept = max(first, second)
    else:
        kept = min(first, second)
    return {'dice': [first, second], 'kept': kept, 'advantage': advantage}


def rules_version(cfg):
    return MARGIN_RULES_VERSION if cfg.tier_mode == 'margin_four' else RULES_VERSION


def margin_tier(natural, margin, cfg):
    if cfg.natural_override:
        if natural == 20:
            return 'critical'
        if natural == 1:
            return 'disaster'
    if margin >= cfg.thresholds.critical:
        return 'critical'
    if margin >= cfg.thresholds.success:
        return 'success'
    if margin <= cfg.thresholds.disaster:
        return 'disaster'
    return 'failure'


def tier_for(position, natural, margin):
    """五档判定。天然 1/20 **优先**于 margin。"""
    if natural == 20:
        return 'critical'
    if natural == 1:
        return 'setback' if position == 'controlled' else 'disaster'
    if position == 'controlled':
        if margin >= 10:
            return 'critical'
        if margin >= 0:
            return 'success'
        if margin >= -5:
            return 'partial'
        return 'setback'          # 稳妥最差到 setback
    if position == 'risky':
        if margin >= 10:
            return 'critical'
        if margin >= 0:
            return 'success'
        if margin >= -3:
            return 'partial'
        if margin >= -9:
            return 'setback'
        return 'disaster'
    # desperate
    if margin >= 8:
        return 'critical'
    if margin >= 0:
        return 'success'
    if margin >= -5:
        return 'setback'          # 孤注一掷没有 partial
    return 'disaster'


def resolve(session, story, characters, node, action, push=None, seed=None, planned=None):
    """掷骰并算出 tier/margin。纯函数，不写 session。``plan`` 的结果会一并返回。

    ``planned`` 是**冻结**的那一份计划（确认预览算出来的那份）。调用方在扣成本/加码
    代价**之前**已经算好它，就必须把它传进来：否则结算时重新 ``plan`` 会读取代价后的
    状态（疲劳升高、信任下降、钱变少导致资源因素变化），使实际 DC/修正与玩家确认时
    看到的那一份不一致——这等于让代价反过来改已经确认的判定。
    """
    cfg = config(story)
    if planned is None:
        planned = plan(session, story, characters, node, action, push)
    if planned.get('rule_config') is not None:
        cfg = ChecksConfig.model_validate(planned['rule_config'])
    dice = ({'dice': [], 'kept': None, 'advantage': planned['advantage']}
            if planned['auto']['auto'] and cfg.tier_mode == 'margin_four'
            else roll_d20(seed, planned['advantage']))
    total = dice['kept'] + planned['total_mod'] if dice['kept'] is not None else None
    margin = total - planned['dc'] if total is not None else None
    tier = ('success' if planned['auto']['auto'] else
            margin_tier(dice['kept'], margin, cfg) if cfg.tier_mode == 'margin_four' else
            tier_for(planned['position'], dice['kept'], margin))
    if planned['auto']['auto']:
        # 自动成功：不掷骰，只记档位与理由。
        tier = 'success'
    return {**planned, 'seed': seed, 'dice': dice['dice'], 'kept': dice['kept'],
            'rolled': not planned['auto']['auto'], 'total': total, 'margin': margin,
            'tier': tier, 'success': tier_success(tier),
            'rules_version': rules_version(cfg), 'config': cfg}


# --------------------------------------------------------------------- 档位后果
def _tier_block(action, tier):
    check = (action or {}).get('check') or {}
    return (check.get('tiers') or {}).get(tier) or {}


def _clock_ops(effects):
    return {effect.get('id') for effect in effects or [] if effect.get('op') == 'clock'}


def _default_cost(session, story, characters, node, cfg, allow_resource=True):
    """按声明顺序取第一条**当前可执行**的默认代价；没有就返回 ``None``。"""
    for cost in cfg.default_costs:
        if cost.kind == 'time':
            if cost.hours:
                return {'kind': 'time', 'hours': cost.hours}
        elif cost.kind == 'resource':
            if not allow_resource:
                continue
            balances = (session.get('local') or {}).get('resources') or {}
            if balances.get(cost.id, 0) >= cost.amount:
                return {'kind': 'resource', 'id': cost.id, 'amount': cost.amount}
        elif cost.kind == 'relationship':
            present = _present(session, node, characters)
            if present:
                return {'kind': 'relationship', 'characters': present,
                        'delta': float(cost.delta)}
        elif cost.kind == 'flag':
            if bool((session.get('flags') or {}).get(cost.id, False)) != cost.value:
                return {'kind': 'flag', 'id': cost.id, 'value': cost.value}
    return None


def _hint_pool(session, node, action):
    """``fallback_hints``（与兜底共用格式）：动作优先，其次事件。"""
    rows = (action or {}).get('fallback_hints')
    if rows is None:
        rows = (node or {}).get('fallback_hints')
    return list(rows or [])


def next_hint(session, node, action):
    """下一条未给出的提示（确定性：声明顺序）。"""
    given = set((session.get('check_hints') or []))
    for row in _hint_pool(session, node, action):
        if not isinstance(row, dict):
            continue
        requires = row.get('requires') or {}
        flags = session.get('flags') or {}
        if any(flags.get(k, False) != v for k, v in (requires.get('all_flags') or {}).items()):
            continue
        if any(bool(flags.get(k, False)) for k in (requires.get('not_flags') or [])):
            continue
        if row.get('id') in given:
            continue
        return row
    return None


def consequences(session, story, characters, node, action, resolved, scope='action',
                 include_base=True):
    """把已裁定的档位翻译成**可执行后果**（效果列表 + 关系微调 + 额外小时 + 结果文本）。

    返回的是计划，不是执行：调用方（``Runtime``）用 ``self.effects`` 应用，
    因此 v2 不会绕开既有的白名单与原子批次。

    ``scope='fallback'``（未匹配意图的兜底尝试）额外禁两件事：默认代价不能用资源
    （兜底永不发钱物），也不用 ``fallback_hints`` 的提示池（兜底有自己的提示池）。
    """
    cfg = resolved['config']
    tier = resolved['tier']
    check = (action or {}).get('check') or {}
    success = tier_success(tier)
    block = _tier_block(action, tier)
    tier_effects = [dict(effect) for effect in (block.get('effects') or [])]
    base = list(action.get('effects') or []) + list(
        action.get('success' if success else 'failure') or [])
    text = block.get('text') or action.get(
        'success_text' if success else 'failure_text') or action.get('label', '')
    effects = (base if include_base else []) + tier_effects
    relationships = []
    extra_hours = 0
    clocks = []
    hints = []

    # partial：作者没写 tiers.partial 时由引擎从 default_costs 取一项代价。
    if tier == 'partial' and not _tier_block(action, 'partial'):
        cost = _default_cost(session, story, characters, node, cfg,
                             allow_resource=(scope != 'fallback'))
        if cost is None:
            # 都不可执行：只给一条公开回执（规格 §2.4）。
            text = GENERIC_PARTIAL
        elif cost['kind'] == 'time':
            extra_hours += cost['hours']
        elif cost['kind'] == 'resource':
            effects.append({'op': 'resource', 'id': cost['id'], 'delta': -cost['amount']})
        elif cost['kind'] == 'relationship':
            for cid in cost['characters']:
                relationships.append({'character': cid, 'delta': cost['delta']})
        elif cost['kind'] == 'flag':
            effects.append({'op': 'flag', 'id': cost['id'], 'value': cost['value']})

    # setback：作者没写 tiers.setback 时给下一条未给的提示，否则通用回执。
    if tier == 'setback' and not _tier_block(action, 'setback'):
        hint = next_hint(session, node, action) if scope != 'fallback' else None
        if hint is not None and hint.get('text'):
            hints.append(hint['id'])
            effects.append({'op': 'information', 'text': hint['text'],
                            'known_by': ['player'], 'confirmed': False})
        elif not text:
            text = GENERIC_SETBACK
    # 进度钟：critical 多一格，partial 少一格；作者已手写同一钟的 clock op 就不再自动加。
    manual = _clock_ops(tier_effects)
    clock = check.get('clock') or {}
    if clock.get('id') and clock['id'] not in manual and tier in (
            'critical', 'success', 'partial'):
        steps = effect_segments(resolved['effect'])
        if tier == 'critical':
            steps += 1
        elif tier == 'partial':
            steps = max(0, steps - 1)
        if steps:
            clocks.append({'id': clock['id'], 'delta': steps})

    # 危险钟：setback/disaster 按声明加；作者写了 disaster 时如果没写 clock op，
    # 仍按 check.danger_clock 的 disaster 值走（不重复加）。
    danger = check.get('danger_clock') or {}
    if danger.get('id') and danger['id'] not in manual:
        if tier in ('setback', 'failure'):
            key = 'failure' if cfg.tier_mode == 'margin_four' else 'setback'
            delta = int(danger.get(key, 1) or 0)
            if delta:
                clocks.append({'id': danger['id'], 'delta': delta})
        elif tier == 'disaster':
            delta = int(danger.get('disaster', 2) or 0)
            if delta:
                clocks.append({'id': danger['id'], 'delta': delta})

    return {'tier': tier, 'text': text, 'effects': effects,
            'relationships': relationships, 'extra_hours': extra_hours,
            'clocks': clocks, 'hints': hints,
            'success': success,
            'used_default_cost': bool(tier == 'partial' and not _tier_block(action, 'partial'))}


# --------------------------------------------------------------------- 察觉
def concealed_config(action):
    return ((action or {}).get('check') or {}).get('concealed')


def notice(session, story, characters, node, action, resolved, seed):
    """察觉检定（目击）。

    当前事件参与者里与主角**同地**的每个 NPC 各掷一颗：``d20(seed:notice:npc) +
    mod(该 NPC 的 notice_attribute) + notice_bonus``，``≥ 主检定 total`` 即察觉。
    目击集合 = 作者声明的 ``witnesses`` ∪ 察觉成功者。

    返回的公开部分**只**说「似乎有人注意到了 / 似乎没有旁人注意到」，
    以及察觉者是否在玩家可见范围内；未察觉的 NPC 不记忆、不作反应，
    引擎也绝不因此宣称「确定没人看到」。
    """
    declared = concealed_config(action)
    if declared is None:
        return None
    observers = declared.get('observers', 'present')
    if observers != 'present':
        raise ValueError('check.concealed.observers 只支持 "present"')
    attribute = _axis(declared.get('notice_attribute', 'wisdom'))
    bonus = int(declared.get('notice_bonus', 0) or 0)
    present = _present(session, node, characters)
    noticed = []
    rolls = {}
    for cid in present:
        dice = roll_d20('%s:notice:%s' % (seed, cid))
        face = dice['kept']
        total = face + modifier(_char_value(characters, cid, attribute)) + bonus
        rolls[cid] = face
        if resolved['total'] is not None and total >= resolved['total']:
            noticed.append(cid)
    declared_witnesses = set((action or {}).get('witnesses') or [])
    witnesses = set(declared_witnesses) | set(noticed)
    actors = {c['id']: c for c in (characters or {}).get('characters') or []}
    visible = [cid for cid in noticed if _npc_visible(actors.get(cid), session)]
    if noticed:
        public_text = NOTICED_VISIBLE if visible else NOTICED_SOME
    elif declared_witnesses:
        # 有人是作者声明必然看见的：不能说「没人注意」。
        public_text = NOTICED_SOME
    else:
        public_text = NOTICED_NONE
    public = {'noticed': public_text, 'aware': bool(noticed or declared_witnesses)}
    if config(story).display == 'transparent':
        public['dice'] = {cid: rolls[cid] for cid in sorted(rolls)}
        public['in_view'] = [actors[cid].get('public_name') or actors[cid].get('name')
                             for cid in visible if cid in actors]
    return {'witnesses': witnesses, 'noticed': noticed, 'declared': declared_witnesses,
            'public': public}


# --------------------------------------------------------------------- 公开投影
def preview(session, story, characters, node, action, push=None):
    """候选/确认预览的 ``check.v2`` 段（规格 §9）。纯函数，绝不改状态。

    公开部分：处境、效果、把握、因素标签（有利/不利，不给数字）、自动成功、
    拒绝/阻断理由、可选加码、**玩家可见的**钟。隐藏因素、隐藏钟、NPC 的
    底线/兴趣/信任一概不出现。
    """
    cfg = config(story)
    if cfg is None:
        return None
    check = (action or {}).get('check')
    if not check:
        return None
    planned = plan(session, story, characters, node, action, push)
    transparent = cfg.display == 'transparent'
    block = {'rules_version': rules_version(cfg), 'tier_mode': cfg.tier_mode,
             'position': planned['position'], 'effect': planned['effect'],
             'chance': chance_label(planned['chance']),
             'factors': factor_summary(planned['factors'], transparent),
             'auto': bool(planned['auto']['auto']),
             'refused': planned['refused'], 'blocked': planned['blocked']}
    if transparent:
        block['dc'] = planned['dc']
    if planned['auto']['auto']:
        block['auto_reason'] = planned['auto']['reason']
    if push:
        block['push'] = push
    allowed = check.get('push_allowed')
    options = []
    for row in cfg.push:
        if allowed is not None and row.id not in allowed:
            continue
        options.append({'id': row.id, 'label': row.label,
                        'cost_text': _cost_text(row, story)})
    if options:
        block['push_options'] = options
    clock = check.get('clock') or {}
    if clock.get('id'):
        row = clock_public_row(session, story, clock['id'])
        if row is not None and 'player' in row['known_by']:
            block['clock'] = {'label': row['label'], 'segments': row['segments'],
                              'filled': row['filled'], 'kind': row['kind']}
    return block


def _cost_text(option, story):
    resources = {r.id: r for r in (local_resources(story))}
    parts = []
    for rid, amount in sorted((option.cost or {}).items()):
        spec = resources.get(rid)
        name = spec.name if spec else rid
        parts.append('%d %s' % (amount, name))
    if option.fatigue:
        parts.append('更累一些')
    if option.relationship is not None:
        parts.append('动用交情')
    return '、'.join(parts)


def local_resources(story):
    from . import local_rules
    return local_rules.rules(story).resources


def public_result(session, story, resolved, node=None, action=None, notice_info=None,
                  clock_changes=()):
    """结算后的公开结果（写进 surface 的 ``last_check``）。

    ``display=qualitative`` 时只给骰面、档位、因素标签与钟，不给
    modifier/dc/total/margin。
    """
    cfg = config(story)
    transparent = cfg is not None and cfg.display == 'transparent'
    tier = resolved['tier']
    row = {'rules_version': resolved['rules_version'], 'rolled': bool(resolved['rolled']),
           'dice': list(resolved['dice']), 'kept': resolved['kept'],
           'advantage': resolved['advantage'],
           'tier': tier, 'tier_label': TIER_LABELS.get(tier, tier),
           'factors': factor_summary(resolved['factors'], transparent, numeric=True)}
    if cfg.tier_mode == 'margin_four':
        row['tier_mode'] = cfg.tier_mode
        row['status'] = 'auto' if resolved['auto']['auto'] else 'rolled'
        row['tier_label'] = {'critical': '大成功', 'success': '成功',
                             'failure': '失败', 'disaster': '大失败'}[tier]
    if transparent:
        row.update(kept=resolved['kept'], modifier=resolved['total_mod'],
                   dc=resolved['dc'], total=resolved['total'], margin=resolved['margin'])
    if resolved['auto']['auto']:
        row['auto'] = True
        row['reason'] = resolved['auto']['reason']
    if resolved['push'] is not None:
        row['push'] = {'id': resolved['push'].id, 'label': resolved['push'].label}
    if notice_info is not None:
        row['noticed'] = notice_info['public']['noticed']
        if transparent and 'dice' in notice_info['public']:
            row['notice'] = notice_info['public']
    for change in clock_changes or ():
        if change is None or not change.get('changed'):
            continue
        spec = clock_public_row(session, story, change['id'])
        if spec is None or 'player' not in spec['known_by']:
            continue
        row['clock'] = {'label': change['label'], 'from': change['from'],
                        'to': change['to'], 'segments': change['segments'],
                        'kind': change['kind']}
        break
    return row


def execution_refusal(story, reason):
    cfg = config(story)
    if cfg.tier_mode != 'margin_four':
        return refused_result(reason)
    return {'rules_version': rules_version(cfg), 'tier_mode': cfg.tier_mode,
            'status': 'refused', 'rolled': False, 'dice': [], 'kept': None,
            'advantage': None, 'tier': None, 'tier_label': '拒绝',
            'factors': [], 'refused': reason, 'reason': reason}


def refused_result(reason):
    return {'rules_version': RULES_VERSION, 'rolled': False, 'dice': [], 'kept': None,
            'advantage': None, 'tier': 'refused', 'tier_label': TIER_LABELS['refused'],
            'factors': [], 'refused': reason}


def blocked_result(reason):
    return {'rules_version': RULES_VERSION, 'rolled': False, 'dice': [], 'kept': None,
            'advantage': None, 'tier': 'blocked', 'tier_label': '未掷骰',
            'factors': [], 'blocked': reason}


# --------------------------------------------------------------------- 校验
def _check_flag_name(name, where):
    if not isinstance(name, str) or not re.match(FLAG_ID, name):
        raise ValueError('%s 的标记名无效：%r' % (where, name))


def _validate_effects(effects, story, characters, resources, items, clocks, where):
    if not isinstance(effects, list):
        raise ValueError('%s 的效果必须是列表' % where)
    if len(effects) > MAX_EFFECTS:
        raise ValueError('%s 的效果最多 %d 条' % (where, MAX_EFFECTS))
    for effect in effects:
        if not isinstance(effect, dict):
            raise ValueError('%s 的效果必须是对象' % where)
        op = effect.get('op')
        if op not in EFFECT_OPS:
            raise ValueError('%s 的效果 op 不受支持：%r' % (where, op))
        if op in ('flag', 'status', 'take', 'resource', 'health', 'clock', 'reward') \
                and not effect.get('id') and op != 'reward':
            raise ValueError('%s 的 %s 效果需要 id' % (where, op))
        if op == 'item' or (op == 'take' and effect['id'] not in items):
            raise ValueError('%s 的 take 引用了不存在的物品：%s' % (where, effect.get('id')))
        if op == 'resource' and effect.get('id') not in resources:
            raise ValueError('%s 的 resource 引用了未声明的资源：%s'
                             % (where, effect.get('id')))
        if op == 'clock' and effect.get('id') not in clocks:
            raise ValueError('%s 的 clock 引用了未声明的钟：%s' % (where, effect.get('id')))
        if op == 'clock':
            delta = effect.get('delta')
            if isinstance(delta, bool) or not isinstance(delta, int):
                raise ValueError('%s 的 clock 效果需要整数 delta' % where)
        if op == 'health':
            delta = effect.get('delta')
            if isinstance(delta, bool) or not isinstance(delta, int):
                raise ValueError('%s 的 health 效果需要整数 delta' % where)
        if op == 'information':
            targets = set(effect.get('known_by') or [])
            if not targets or targets - (set(characters) | {'player'}):
                raise ValueError('%s 的 information 需要有效知情对象' % where)
            if not isinstance(effect.get('text'), str) or not effect['text'].strip():
                raise ValueError('%s 的 information 需要文本' % where)
        if op == 'fact' and not (isinstance(effect.get('text'), str) and effect['text'].strip()):
            raise ValueError('%s 的 fact 需要文本' % where)
        if op == 'rumor' and effect.get('character') not in characters:
            raise ValueError('%s 的 rumor 角色不存在：%s' % (where, effect.get('character')))


def _validate_when(when, story, characters, items, places, profiles, resources, where):
    kind = when.kind
    if kind == 'item':
        if when.id and when.id not in items:
            raise ValueError('%s 的 item 条件引用了不存在的物品：%s' % (where, when.id))
        if when.template:
            templates = {t['id'] for t in
                         ((story.get('mechanics') or {}).get('rewards') or {})
                         .get('templates') or [] if isinstance(t, dict) and 'id' in t}
            if templates and when.template not in templates:
                raise ValueError('%s 的 item 条件引用了不存在的奖励模板：%s'
                                 % (where, when.template))
    elif kind == 'companion':
        if when.id not in characters:
            raise ValueError('%s 的 companion 条件引用了不存在的角色：%s' % (where, when.id))
    elif kind == 'profile':
        if profiles is not None and when.id not in profiles:
            raise ValueError('%s 的 profile 条件引用了不存在的起点：%s' % (where, when.id))
    elif kind == 'place':
        if when.id and when.id not in places:
            raise ValueError('%s 的 place 条件引用了不存在的地点：%s' % (where, when.id))
    elif kind == 'attribute_axis':
        _axis(when.attribute)


def validate_package(story, characters):
    """包校验：结构、引用与边界。旧包（没有 ``mechanics.checks``）直接 no-op。"""
    cfg = config(story)
    if cfg is None:
        return None
    if cfg.version != SCHEMA_VERSION:
        raise ValueError('mechanics.checks.version 必须是 %d（得到 %r）'
                         % (SCHEMA_VERSION, cfg.version))
    places = {p['id']: p for p in story.get('locations') or []}
    items = {i['id'] for i in story.get('items') or []}
    chars = {c['id'] for c in (characters or {}).get('characters') or []}
    from . import local_rules
    resources = {r.id for r in local_rules.rules(story).resources}
    clocks = {c.id for c in cfg.clocks}
    audiences = chars | {'player'}
    start_cfg = (story.get('mechanics') or {}).get('start_profiles') or {}
    profiles = {p['id'] for p in start_cfg.get('profiles') or []} if start_cfg else None

    for factor in cfg.factors:
        _validate_when(factor.when, story, characters, items, places, profiles,
                       resources, '因素 %s' % factor.id)

    for option in cfg.push:
        for rid, amount in (option.cost or {}).items():
            if rid not in resources:
                raise ValueError('加码 %s 的费用引用了未声明的资源：%s' % (option.id, rid))
            if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
                raise ValueError('加码 %s 的费用必须是非负整数：%s' % (option.id, rid))

    for spec in cfg.clocks:
        unknown = set(spec.known_by) - audiences
        if unknown:
            raise ValueError('钟 %s 的已知受众不存在：%s'
                             % (spec.id, '、'.join(sorted(unknown))))
        _validate_effects(spec.on_full, story, characters, resources, items, clocks,
                          '钟 %s 的 on_full' % spec.id)

    for cid, profile in cfg.social.items():
        if cid not in chars:
            raise ValueError('社交画像引用了不存在的角色：' + cid)
        if len(set(profile.interests)) != len(profile.interests):
            raise ValueError('社交画像 %s 的兴趣重复' % cid)
        if len(set(profile.boundaries)) != len(profile.boundaries):
            raise ValueError('社交画像 %s 的底线重复' % cid)

    for cost in cfg.default_costs:
        if cost.kind == 'resource' and cost.id not in resources:
            raise ValueError('默认代价引用了未声明的资源：' + str(cost.id))
        if cost.kind == 'flag':
            _check_flag_name(cost.id, '默认代价')

    for event in story.get('events') or []:
        for action in event.get('actions') or []:
            check = action.get('check')
            if not check:
                continue
            where = '事件 %s 的动作 %s' % (event.get('id'), action.get('id'))
            _validate_check(check, story, characters, items, places, profiles, resources,
                            clocks, chars, event, where)
            _validate_action_clocks(action, clocks, where)
    return cfg


def _validate_action_clocks(action, clocks, where):
    """动作自己的 ``effects``/``success``/``failure`` 里的 ``clock`` op 必须引用已声明的钟。

    ``Runtime.validate_package`` 只负责「v2 包允许 clock op」；这里是同一个包里
    「这个钟真的存在」的那一半，所以未声明的钟在提交时就被拒，不会拖到结算时才炸。
    """
    for branch in ('effects', 'success', 'failure'):
        for effect in action.get(branch) or []:
            if not isinstance(effect, dict) or effect.get('op') != 'clock':
                continue
            if effect.get('id') not in clocks:
                raise ValueError('%s 的 %s 里的 clock 引用了未声明的钟：%s'
                                 % (where, branch, effect.get('id')))
            delta = effect.get('delta')
            if isinstance(delta, bool) or not isinstance(delta, int):
                raise ValueError('%s 的 clock 效果需要整数 delta' % where)


def _validate_check(check, story, characters, items, places, profiles, resources,
                    clocks, chars, event, where):
    _axis(check.get('attribute'))
    if check.get('dc') is not None:
        dc = check['dc']
        if isinstance(dc, bool) or not isinstance(dc, int) or not 2 <= dc <= 30:
            raise ValueError('%s 的 check.dc 必须是 2..30 的整数' % where)
    elif check.get('difficulty') is None:
        raise ValueError('%s 的检定需要 dc 或 difficulty' % where)
    if check.get('position') is not None and check['position'] not in POSITIONS:
        raise ValueError('%s 的 check.position 无效' % where)
    if check.get('effect') is not None and check['effect'] not in EFFECTS:
        raise ValueError('%s 的 check.effect 无效' % where)

    cfg = config(story)
    difficulty = check.get('difficulty')
    if difficulty is not None and (isinstance(difficulty, bool)
            or not isinstance(difficulty, (int, float)) or not 0 <= difficulty <= 1):
        raise ValueError('%s 的 check.difficulty 必须是 0..1 的数值' % where)
    for raw in check.get('factors') or []:
        factor = _resolve_ref(cfg, raw)
        _validate_when(factor.when, story, characters, items, places, profiles,
                       resources, '%s 的因素 %s' % (where, factor.id))

    social = check.get('social')
    if social is not None:
        target = social.get('target')
        if target not in chars:
            raise ValueError('%s 的 check.social.target 不存在：%s' % (where, target))
        profile = cfg.social.get(target)
        if profile is not None:
            unknown = (set(social.get('appeals') or []) | set(social.get('violates') or []))
            known = set(profile.interests) | set(profile.boundaries)
            if unknown - known:
                raise ValueError('%s 的社交诉求/底线没有在该人物的画像里声明：%s'
                                 % (where, '、'.join(sorted(unknown - known))))

    auto = check.get('auto')
    if auto is not None:
        gate = _check_auto(auto)
        for name in (gate.all_flags or {}):
            _check_flag_name(name, where + ' 的 auto')
        unknown = set(gate.items or []) - items
        if unknown:
            raise ValueError('%s 的 auto.items 引用了不存在的物品：%s'
                             % (where, '、'.join(sorted(unknown))))

    concealed = check.get('concealed')
    if concealed is not None:
        if concealed.get('observers', 'present') != 'present':
            raise ValueError('%s 的 check.concealed.observers 只支持 "present"' % where)
        _axis(concealed.get('notice_attribute', 'wisdom'))
        bonus = concealed.get('notice_bonus', 0)
        if isinstance(bonus, bool) or not isinstance(bonus, int) or not -10 <= bonus <= 10:
            raise ValueError('%s 的 notice_bonus 必须是 -10..10 的整数' % where)

    for tier, block in (check.get('tiers') or {}).items():
        if tier not in (FOUR_TIERS if cfg.tier_mode == 'margin_four' else TIERS):
            raise ValueError('%s 的 check.tiers 档位无效：%s' % (where, tier))
        if not isinstance(block, dict):
            raise ValueError('%s 的 check.tiers.%s 必须是对象' % (where, tier))
        _validate_effects(block.get('effects') or [], story, characters, resources,
                          items, clocks, '%s 的 tiers.%s' % (where, tier))
        text = block.get('text')
        if text is not None and (not isinstance(text, str) or len(text) > 600):
            raise ValueError('%s 的 tiers.%s.text 必须是 600 字以内的文本'
                             % (where, tier))

    allowed = check.get('push_allowed')
    if allowed is not None:
        unknown = set(allowed) - {p.id for p in cfg.push}
        if unknown:
            raise ValueError('%s 的 check.push_allowed 引用了不存在的加码：%s'
                             % (where, '、'.join(sorted(unknown))))

    clock = check.get('clock') or {}
    if clock.get('id') and clock['id'] not in clocks:
        raise ValueError('%s 的 check.clock 引用了未声明的钟：%s' % (where, clock['id']))
    danger = check.get('danger_clock') or {}
    if danger.get('id'):
        if danger['id'] not in clocks:
            raise ValueError('%s 的 check.danger_clock 引用了未声明的钟：%s'
                             % (where, danger['id']))
        for key in (('failure', 'disaster') if cfg.tier_mode == 'margin_four'
                    else ('setback', 'disaster')):
            value = danger.get(key, 1)
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 4:
                raise ValueError('%s 的 danger_clock.%s 必须是 0..4 的整数' % (where, key))

    # ``fallback_hints`` 与兜底共用格式，形状与引用统一由 validate_hint_declarations 查。
    if check.get('fallback_hints') is not None and not isinstance(
            check.get('fallback_hints'), list):
        raise ValueError('%s 的 fallback_hints 必须是列表' % where)


def validate_hint_declarations(story, characters):
    """动作/事件上的 ``fallback_hints`` 与兜底共用格式：这里只查形状与引用。"""
    cfg = config(story)
    if cfg is None:
        return
    places = {p['id']: p for p in story.get('locations') or []}
    items = {i['id'] for i in story.get('items') or []}
    chars = {c['id'] for c in (characters or {}).get('characters') or []}
    for event in story.get('events') or []:
        rows = list(event.get('fallback_hints') or [])
        for action in event.get('actions') or []:
            rows += list(action.get('fallback_hints') or [])
        for hint in rows:
            if not isinstance(hint, dict):
                raise ValueError('fallback_hints 每条必须是对象')
            if not hint.get('id') or not isinstance(hint['id'], str):
                raise ValueError('fallback_hints 每条都需要 id')
            if not isinstance(hint.get('text'), str) or not hint['text'].strip():
                raise ValueError('fallback_hints 每条都需要 text')
            target = hint.get('target') or {}
            kind = target.get('kind')
            if kind not in ('place', 'object', 'npc'):
                raise ValueError('fallback_hints 的 target.kind 无效：%r' % (kind,))
            if kind == 'place' and target.get('id') not in places:
                raise ValueError('fallback_hints 的目标地点不存在：%s' % target.get('id'))
            if kind == 'object' and target.get('id') not in items:
                raise ValueError('fallback_hints 的目标物品不存在：%s' % target.get('id'))
            if kind == 'npc' and target.get('id') not in chars:
                raise ValueError('fallback_hints 的目标人物不存在：%s' % target.get('id'))


def validate_all(story, characters):
    """``Runtime.validate_package`` 用的单一入口：包级 + 动作级 + 提示声明。"""
    cfg = validate_package(story, characters)
    validate_hint_declarations(story, characters)
    return cfg
