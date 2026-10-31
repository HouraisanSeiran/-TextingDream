# -*- coding: utf-8 -*-
"""任务与地方后果：有界因果，复用现有状态引擎（纯规则 + 原子应用候选）。

这不是一个 "NPC 循环"，而是一套**作者已经写好的有限因果**：一个委托人、一个需求、
一组完成证据、一组后果。没有证据就不完成，没有作者声明的报酬就不发赏。

与既有模块的分工（一样也不新建）：

========================  ==============================================
已有的东西                 本模块怎么用
========================  ==============================================
``LocalState.flags``        地方后果的开关（``flag`` op），不另建标记表
``local_rules`` 资源        ``resource`` op，不另建库存账
``rewards`` 账户/模板        报酬只能引用**已声明**的 ``account`` / ``template``
``Runtime.effects``        唯一的执行器；本模块只产出它吃得下的 effect 列表
``pressure`` 时钟          期限只用游戏时刻（``s['time']``），不新建第二时钟
``session`` 快照          任务状态住在 ``session['quests']``，跟着既有回滚
``facts``/``beliefs``/``heard``  知情用既有 ``information`` op，不另写知识层
========================  ==============================================

三条硬边界：

1. **报酬必须有来源。**金币必须指定一个已声明且余额够的 ``account``（就是既有
   ``rewards`` 的 ``payer``）；物品必须引用已声明的 ``template``。没有声明就只能
   给“关系 / 线索”这类非财物收益，绝不让模型凭空造钱造物。
2. **完成必须有证据。**``evidence`` 声明的是“作者已经存在的”状态：某个 flag、
   某个资源阈值、某个已到访地点。证据不足时 ``complete`` 直接拒收并说明缺什么，
   不把“玩家说完成了”当成完成。
3. **知情是分级制的。**被救的人知道，不等于全天下知道。``public_summary`` /
   ``known_by`` / ``location`` / ``reveal_flag`` 四个字段共同决定谁能看到什么；
   未公开的任务数量、隐藏目标、失败原因都不会钻进玩家投影。

作者声明位置：``story.mechanics.quests``（纯新增键；没有它就全部 no-op）。
声明结构见 ``docs/quests-contract.md``。
"""
import copy
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from . import local_rules, rewards as rewards_rules

SCHEMA_VERSION = 1
MECHANICS_KEY = 'quests'
#: 任务状态。故意只保留流程真正需要的几个：
#: ``proposed``（已发出）→ ``accepted``（已接下）→ ``active``（进行中）
#: → ``completed`` / ``failed``；随时可 ``cancelled``。
STATES = ('proposed', 'accepted', 'active', 'completed', 'failed', 'cancelled')
#: 可以继续推进的状态（终态不再接受 update）。
OPEN_STATES = frozenset({'proposed', 'accepted', 'active'})
TERMINAL_STATES = frozenset({'completed', 'failed', 'cancelled'})

ID = r'^[A-Za-z0-9_-]{1,60}$'
MAX_QUESTS = 60
MAX_EVIDENCE = 8
MAX_EFFECTS = 12
MAX_OBJECTIVES = 6
MAX_TEXT = 400

#: 本模块可能发出的 effect op（全部是 ``Runtime.effects`` 已经支持的）。
EFFECT_OPS = ('flag', 'resource', 'information', 'reward', 'take')


class QuestError(ValueError):
    """A refused quest operation. Nothing is written when this is raised."""


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


def _int(low, high, default=0):
    return Field(default=default, ge=low, le=high, strict=True)


# --------------------------------------------------------------------- schema
class Evidence(Strict):
    """One completion condition, expressed only over state the engine already keeps."""
    kind: Literal['flag', 'resource', 'visited']
    #: ``flag`` 必需；``resource`` 看 id+at_least；``visited`` 看 id=地点。
    id: str = Field(pattern=ID)
    at_least: int = _int(0, 1000000)


class Cost(Strict):
    """What finishing costs. Only author-declared resources/items are accepted."""
    kind: Literal['resource', 'item']
    id: str = Field(pattern=ID)
    amount: int = _int(1, 1000000, 1)


class RewardEntry(Strict):
    """One payable reward. ``currency`` needs a declared paying account."""
    kind: Literal['currency', 'item', 'relationship', 'clue']
    id: str = Field(default='', max_length=60)
    amount: int = _int(0, 1000000)
    #: ``currency`` 专用：谁付这笔钱（已声明的 ``rewards.accounts``）。
    payer: str = Field(default='', max_length=60)
    #: ``relationship`` / ``clue`` 的公开描述（非财物收益必须写清楚）。
    text: str = Field(default='', max_length=MAX_TEXT)


class Effect(Strict):
    """A declared consequence, in ``Runtime.effects`` vocabulary."""
    op: Literal['flag', 'resource', 'information']
    id: str = Field(default='', max_length=60)
    value: bool = False
    delta: int = _int(-1000000, 1000000)
    text: str = Field(default='', max_length=MAX_TEXT)
    confirmed: bool = False
    known_by: list[str] = Field(default_factory=list, max_length=8)


class Quest(Strict):
    id: str = Field(pattern=ID)
    #: 谁委托的：已声明的人物或组织 id。
    giver: str = Field(min_length=1, max_length=60)
    location: str = Field(default='', max_length=60)
    title: str = Field(min_length=1, max_length=80)
    #: 玩家可见的一句话。没写就不给玩家看这个任务。
    public_summary: str = Field(default='', max_length=MAX_TEXT)
    #: 隐藏目标（作者侧）；绝不进玩家投影。
    secret_objective: str = Field(default='', max_length=MAX_TEXT)
    known_by: list[str] = Field(default_factory=list, max_length=8)
    reveal_flag: str = Field(default='', max_length=60)
    objectives: list[str] = Field(default_factory=list, max_length=MAX_OBJECTIVES)
    evidence: list[Evidence] = Field(default_factory=list, max_length=MAX_EVIDENCE)
    costs: list[Cost] = Field(default_factory=list, max_length=MAX_EFFECTS)
    rewards: list[RewardEntry] = Field(default_factory=list, max_length=MAX_EFFECTS)
    #: 完成后对地方的影响（flag / 资源 / 知情），可为空。
    effects: list[Effect] = Field(default_factory=list, max_length=MAX_EFFECTS)
    #: 失败后又怎么走：可空（不继续就结束），也可指向另一条已声明任务。
    on_failure: str = Field(default='', max_length=60)
    #: 期限（游戏时刻，同一个 session['time'] 进制）。0 = 无期限。
    deadline: int = _int(0, 1000000000)
    #: 接受后多少游戏单位内完成（与 deadline 二选一，都以 session['time'] 计）。
    duration: int = _int(0, 1000000000)

    @model_validator(mode='after')
    def _one_clock(self):
        if self.deadline and self.duration:
            raise ValueError('任务 %s 同时写了 deadline 与 duration；两者只能选一个'
                             % self.id)
        return self


class Quests(Strict):
    version: int = Field(default=1, strict=True)
    #: 当前游戏时刻从哪取（只有一个时钟：既有 ``session['time']``）。
    quests: list[Quest] = Field(default_factory=list, max_length=MAX_QUESTS)


# ------------------------------------------------------------------- config
def rules(story):
    """The parsed quest config, or ``None`` when the author configured nothing."""
    raw = (story or {}).get('mechanics', {}).get(MECHANICS_KEY)
    if raw is None:
        return None
    return Quests.model_validate(raw)


def validate(story):
    """Refuse a quest config that could pay without a source or end without evidence."""
    cfg = rules(story)
    if cfg is None:
        return None
    if cfg.version != SCHEMA_VERSION:
        raise QuestError('任务配置版本必须是整数 %d' % SCHEMA_VERSION)
    seen = set()
    for quest in cfg.quests:
        if quest.id in seen:
            raise QuestError('任务 id 重复：%s' % quest.id)
        seen.add(quest.id)
    by_id = {quest.id: quest for quest in cfg.quests}
    characters = {c.get('id') for c in (story.get('characters') or {}).get('characters') or []}
    places = {p.get('id') for p in story.get('locations') or []}
    reward_cfg = rewards_rules.rules(story)
    accounts = {a.id: a for a in (reward_cfg.accounts if reward_cfg else [])}
    reward_entries = {r.id: r for r in (reward_cfg.rewards if reward_cfg else [])}
    templates = {t.id: t for t in (reward_cfg.templates if reward_cfg else [])}
    currencies = {c.id for c in (reward_cfg.currencies if reward_cfg else [])}
    resource_ids = {r.id for r in local_rules.rules(story).resources}

    for quest in cfg.quests:
        where = 'task %s' % quest.id
        if quest.location and quest.location not in places:
            raise QuestError('%s 的 location %r 不是已声明的地点'
                             % (where, quest.location))
        if quest.on_failure and quest.on_failure not in by_id:
            raise QuestError('%s 的 on_failure 指向未声明的任务 %r'
                             % (where, quest.on_failure))
        if quest.on_failure == quest.id:
            raise QuestError('%s 的 on_failure 不能指向自己' % where)
        if not quest.evidence and not quest.objectives:
            raise QuestError('%s 既没有 evidence 也没有 objectives：无法判定完成' % where)
        # 报酬必须有来源
        paid = False
        for entry in quest.rewards:
            if entry.kind in ('currency', 'item'):
                reward = reward_entries.get(entry.id)
                if reward is None:
                    raise QuestError('%s 的报酬 %r 不是已声明的 mechanics.rewards.rewards 项'
                                     % (where, entry.id))
                if reward.kind != entry.kind:
                    raise QuestError('%s 的报酬 %r 声明为 %s，不是 %s'
                                     % (where, entry.id, reward.kind, entry.kind))
                if entry.kind == 'currency':
                    account = accounts.get(reward.payer)
                    if account is None:
                        raise QuestError('%s 的报酬 %r 没有已声明的付款账户 %r'
                                         % (where, entry.id, reward.payer))
                    if currencies and account.currency not in currencies:
                        raise QuestError('%s 的付款账户 %r 使用了未声明的货币'
                                         % (where, reward.payer))
                    if account.initial < (reward.amount_max or reward.amount_min):
                        raise QuestError('%s 的报酬 %r 上限超过账户 %r 的初始余额'
                                         % (where, entry.id, reward.payer))
                else:
                    for template in reward.templates:
                        if template not in templates:
                            raise QuestError('%s 的报酬 %r 引用了未声明的模板 %r'
                                             % (where, entry.id, template))
                paid = True
            elif entry.kind in ('relationship', 'clue'):
                if not entry.text.strip():
                    raise QuestError('%s 的 %s 收益必须写清楚是什么'
                                     % (where, entry.kind))
            else:                                   # pragma: no cover - Literal
                raise QuestError('%s 有未知报酬种类 %r' % (where, entry.kind))
        if not quest.rewards:
            # 允许没有物质报酬，但必须说明白换来的是关系还是线索。
            if not quest.effects:
                raise QuestError('%s 既没有报酬也没有后果：完成了也什么都不变' % where)
        for effect in quest.effects:
            if effect.op == 'flag' and not effect.id:
                raise QuestError('%s 的 flag 后果没有 id' % where)
            if effect.op == 'resource':
                if not effect.id:
                    raise QuestError('%s 的资源后果没有 id' % where)
                if effect.id not in resource_ids:
                    raise QuestError('%s 的资源后果 %r 不是已声明的本地资源'
                                     % (where, effect.id))
            if effect.op == 'information':
                if not effect.text.strip():
                    raise QuestError('%s 的知情后果没有文本' % where)
                unknown = set(effect.known_by) - ({'player'} | characters)
                if unknown:
                    raise QuestError('%s 的知情受众不存在：%s'
                                     % (where, '、'.join(sorted(unknown))))
        for audience in quest.known_by:
            if audience != 'player' and audience not in characters:
                raise QuestError('%s 的 known_by 受众不存在：%s' % (where, audience))
        for cost in quest.costs:
            if cost.kind == 'resource' and cost.id not in resource_ids:
                raise QuestError('%s 的成本资源 %r 不是已声明的本地资源'
                                 % (where, cost.id))
            if cost.kind == 'item':
                items = {i.get('id') for i in story.get('items') or []}
                if cost.id not in items:
                    raise QuestError('%s 的成本物品 %r 不是已声明的地点物品'
                                     % (where, cost.id))
    _reject_cycles(by_id)
    return cfg


def _reject_cycles(by_id):
    for start in by_id:
        seen = set()
        current = by_id[start].on_failure
        while current:
            if current in seen:
                raise QuestError('任务的 on_failure 形成环：%s' % start)
            seen.add(current)
            quest = by_id.get(current)
            if quest is None:
                break
            current = quest.on_failure
    return True

# ================================================================= state machine
def blank():
    """The empty quest state. Lives in ``session['quests']``; no second store."""
    return {'version': SCHEMA_VERSION, 'entries': {}}


def state(session, cfg):
    """Read-only view: a missing block is reported empty, never written."""
    current = (session or {}).get('quests') or {}
    entries = current.get('entries')
    if not isinstance(entries, dict):
        entries = {}
    out = {}
    known = {quest.id for quest in (cfg.quests if cfg else [])}
    for quest_id, row in entries.items():
        if quest_id not in known:
            continue                      # a quest the package no longer declares
        out[quest_id] = {'state': row.get('state', 'proposed'),
                         'since': row.get('since'),
                         'due': row.get('due'),
                         'evidence': dict(row.get('evidence') or {}),
                         'paid': row.get('paid') or None,
                         'note': row.get('note', '')}
    return {'version': current.get('version', SCHEMA_VERSION), 'entries': out}


def ensure(session, story):
    """Create the quest block on a candidate session; never called from a read."""
    cfg = rules(story)
    if cfg is None:
        return None
    if not isinstance(session.get('quests'), dict):
        session['quests'] = blank()
    return cfg


def _quest(cfg, quest_id):
    found = next((quest for quest in cfg.quests if quest.id == quest_id), None)
    if found is None:
        raise QuestError('故事包没有声明任务 %r' % quest_id)
    return found


def _now(session):
    """The one clock: the existing ``session['time']``."""
    value = session.get('time')
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return value


def _due(moment, quest):
    if quest.deadline:
        return quest.deadline
    if quest.duration:
        return moment + quest.duration
    return None


def due_at(session, quest_id, story):
    """Read-only: when this quest falls due (``None`` = no deadline). Never advances it."""
    cfg = rules(story)
    if cfg is None:
        return None
    quest = _quest(cfg, quest_id)
    row = state(session, cfg)['entries'].get(quest_id)
    if row is None:
        return _due(_now(session), quest) if quest.deadline else None
    return row['due']


# ------------------------------------------------------------------- evidence
def missing_evidence(session, quest, story):
    """What the declared evidence still lacks, as a list of player-safe strings.

    Only *what is missing* is reported — never a hidden threshold the author did not
    publish, and never a future value.
    """
    gaps = []
    for item in quest.evidence:
        if item.kind == 'flag':
            if not (session.get('flags') or {}).get(item.id):
                gaps.append('还差一件已发生的事（%s）' % item.id)
        elif item.kind == 'resource':
            cfg = local_rules.rules(story)
            have = ((session.get('local') or {}).get('resources') or {}).get(item.id)
            if have is None:
                spec = next((r for r in cfg.resources if r.id == item.id), None)
                have = spec.initial if spec is not None else 0
            if have < item.at_least:
                gaps.append('本地%s还不够（要 %d，现在 %d）'
                            % (item.id, item.at_least, have))
        elif item.kind == 'visited':
            if item.id not in (session.get('explored') or []):
                gaps.append('还没到过%s' % item.id)
    return gaps


def _affordable(session, quest, story):
    """Costs the journey can actually pay now, as player-safe gaps."""
    gaps = []
    for cost in quest.costs:
        if cost.kind == 'resource':
            have = ((session.get('local') or {}).get('resources') or {}).get(cost.id, 0)
            if have < cost.amount:
                gaps.append('本地%s不足（要 %d，现在 %s）' % (cost.id, cost.amount, have))
        elif cost.kind == 'item':
            if cost.id not in (session.get('inventory') or []):
                gaps.append('手上没有%s' % cost.id)
    return gaps


# ---------------------------------------------------------------- transitions
def _entry(session, quest_id):
    entries = session.setdefault('quests', blank()).setdefault('entries', {})
    row = entries.get(quest_id)
    if row is None:
        row = {'state': 'proposed', 'since': _now(session), 'due': None,
               'evidence': {}, 'paid': None, 'note': ''}
        entries[quest_id] = row
    return row


def propose(session, story, quest_id, note=''):
    """Make a quest visible as ``proposed``. Idempotent; never re-proposes a closed one."""
    cfg = ensure(session, story)
    if cfg is None:
        raise QuestError('这个故事包没有配置任务')
    quest = _quest(cfg, quest_id)
    row = _entry(session, quest_id)
    if row['state'] in TERMINAL_STATES:
        raise QuestError('任务 %s 已经结束（%s），不会再出现' % (quest_id, row['state']))
    if row['state'] == 'proposed':
        return {'quest_id': quest_id, 'state': 'proposed', 'changed': False}
    return {'quest_id': quest_id, 'state': row['state'], 'changed': False,
            'note': '任务已在更后面的状态，提案不覆盖它'}


def accept(session, story, quest_id):
    """``proposed`` → ``accepted``, and fix the deadline on the one existing clock."""
    cfg = ensure(session, story)
    if cfg is None:
        raise QuestError('这个故事包没有配置任务')
    quest = _quest(cfg, quest_id)
    row = _entry(session, quest_id)
    if row['state'] != 'proposed':
        raise QuestError('任务 %s 现在是 %s，只能从 proposed 接受'
                         % (quest_id, row['state']))
    row['state'] = 'accepted'
    row['since'] = _now(session)
    row['due'] = _due(_now(session), quest)
    return {'quest_id': quest_id, 'state': 'accepted', 'due': row['due'],
            'changed': True}


def start(session, story, quest_id):
    """``accepted`` → ``active``. Only ``active`` may complete."""
    cfg = ensure(session, story)
    if cfg is None:
        raise QuestError('这个故事包没有配置任务')
    _quest(cfg, quest_id)
    row = _entry(session, quest_id)
    if row['state'] == 'active':
        return {'quest_id': quest_id, 'state': 'active', 'changed': False}
    if row['state'] != 'accepted':
        raise QuestError('任务 %s 现在是 %s，只能从 accepted 开始'
                         % (quest_id, row['state']))
    row['state'] = 'active'
    return {'quest_id': quest_id, 'state': 'active', 'changed': True}


def cancel(session, story, quest_id, reason=''):
    """Any open state → ``cancelled``. Never fatal: the journey keeps going."""
    cfg = ensure(session, story)
    if cfg is None:
        raise QuestError('这个故事包没有配置任务')
    _quest(cfg, quest_id)
    row = _entry(session, quest_id)
    if row['state'] in TERMINAL_STATES:
        return {'quest_id': quest_id, 'state': row['state'], 'changed': False}
    row['state'] = 'cancelled'
    row['note'] = str(reason or '')[:MAX_TEXT]
    return {'quest_id': quest_id, 'state': 'cancelled', 'changed': True}


def expire(session, story, quest_id=None):
    """Advance the clock rule for quests that fell due.

    Called explicitly by a Runtime time-advance hook — never from a read. A due quest
    fails (and follows ``on_failure`` if declared); nothing is deleted, the journey keeps
    going.
    """
    cfg = ensure(session, story)
    if cfg is None:
        return {'expired': []}
    moment = _now(session)
    expired = []
    for quest in cfg.quests:
        if quest_id is not None and quest.id != quest_id:
            continue
        row = (session.get('quests') or {}).get('entries', {}).get(quest.id)
        if row is None or row['state'] in TERMINAL_STATES:
            continue
        due = row.get('due')
        if due is None or moment < due:
            continue
        row['state'] = 'failed'
        row['note'] = 'due %s' % due
        expired.append({'quest_id': quest.id, 'state': 'failed',
                        'on_failure': quest.on_failure or None})
        if quest.on_failure:
            follower = (session.get('quests') or {}).get('entries', {}).get(quest.on_failure)
            if follower is None or follower['state'] in TERMINAL_STATES:
                _entry(session, quest.on_failure)['state'] = 'proposed'
    return {'expired': expired}


# ------------------------------------------------------------------- complete
def completion(session, story, quest_id):
    """Dry-run: what would ``complete`` do, and is anything still missing?

    Pure and read-only. This is how a caller shows \"you still need X\" without touching
    state, and how a test proves that a refused completion wrote nothing.
    """
    cfg = rules(story)
    if cfg is None:
        raise QuestError('这个故事包没有配置任务')
    quest = _quest(cfg, quest_id)
    row = state(session, cfg)['entries'].get(quest_id)
    if row is None:
        return {'quest_id': quest_id, 'ok': False, 'state': 'proposed',
                'missing': ['任务还没有发出'], 'effects': [], 'rewards': []}
    if row['state'] != 'active':
        return {'quest_id': quest_id, 'ok': False, 'state': row['state'],
                'missing': ['任务不在进行中（%s）' % row['state']],
                'effects': [], 'rewards': []}
    gaps = missing_evidence(session, quest, story) + _affordable(session, quest, story)
    effects, claims = _plan_effects(quest, row)
    return {'quest_id': quest_id, 'ok': not gaps, 'state': row['state'],
            'missing': gaps, 'effects': effects, 'rewards': claims}


def apply_completion(session, story, quest_id, effects_fn=None, source=None):
    """Complete a quest **atomically**: costs, effects and pay happen in one batch.

    ``effects_fn(session, effects, source, reward_claims)`` is the existing
    ``Runtime.effects`` callback; this module never writes rewards or flags itself. The
    whole thing runs on a deep copy and only replaces the caller's session when every
    step succeeded, so an unaffordable batch leaves nothing half-written.

    Repeating a completion is a no-op: the quest is already ``completed`` and the reward
    claims carry a stable ``quest:<id>`` source, so ``rewards.apply`` grants once.
    """
    cfg = ensure(session, story)
    if cfg is None:
        raise QuestError('这个故事包没有配置任务')
    quest = _quest(cfg, quest_id)
    row = _entry(session, quest_id)
    if row['state'] == 'completed':
        return {'quest_id': quest_id, 'state': 'completed', 'changed': False,
                'audits': [], 'note': '任务已经完成，不重复发奖'}
    if row['state'] != 'active':
        raise QuestError('任务 %s 现在是 %s，只能完成进行中的任务'
                         % (quest_id, row['state']))
    gaps = missing_evidence(session, quest, story) + _affordable(session, quest, story)
    if gaps:
        raise QuestError('任务还不能完成：' + '；'.join(gaps))
    effects, claims = _plan_effects(quest, row)
    work = copy.deepcopy(session)
    work_row = work['quests']['entries'][quest_id]
    if effects:
        if effects_fn is None:
            raise QuestError('完成这个任务需要执行 effects，但没有给执行回调')
        audits = effects_fn(work, effects, source or ('quest:' + quest.id), claims)
    else:
        audits = []
    work_row['state'] = 'completed'
    work_row['paid'] = source or ('quest:' + quest.id)
    session.clear()
    session.update(work)
    return {'quest_id': quest_id, 'state': 'completed', 'changed': True,
            'audits': audits, 'note': ''}


def _plan_effects(quest, row):
    """The effect list handed to ``Runtime.effects``, plus the reward claims."""
    effects = []
    claims = []
    for cost in quest.costs:
        if cost.kind == 'resource':
            effects.append({'op': 'resource', 'id': cost.id, 'delta': -cost.amount})
        elif cost.kind == 'item':
            effects.append({'op': 'take', 'id': cost.id})
    for effect in quest.effects:
        if effect.op == 'flag':
            effects.append({'op': 'flag', 'id': effect.id, 'value': effect.value})
        elif effect.op == 'resource':
            effects.append({'op': 'resource', 'id': effect.id, 'delta': effect.delta})
        elif effect.op == 'information':
            effects.append({'op': 'information', 'text': effect.text,
                            'confirmed': effect.confirmed,
                            'known_by': list(effect.known_by)})
    for entry in quest.rewards:
        # A payable reward must name an author-declared ``rewards.rewards[]`` entry: that
        # is the only thing ``rewards.apply`` will pay, and it is where the currency,
        # amount range, templates and payer are already declared. This module never
        # inlines an amount of its own.
        if entry.kind in ('currency', 'item'):
            claims.append({'entry': entry.id})
        # relationship / clue are narrative outcomes: they are already visible in the
        # quest's public text and never mint currency or an item.
    return effects, claims

# ------------------------------------------------------------------ projections
def _visible(quest, session, audience):
    """Is this quest's *existence* visible to ``audience`` right now?"""
    if not quest.public_summary:
        return False                      # author kept it entirely off-stage
    if quest.reveal_flag and not (session.get('flags') or {}).get(quest.reveal_flag):
        return False
    if quest.known_by and audience not in quest.known_by:
        return False
    return True


def _near(quest, session):
    """A location-bound quest is only offered where that place actually is."""
    if not quest.location:
        return True
    location = session.get('location')
    if location == quest.location:
        return True
    return quest.location in (session.get('explored') or [])


def available(session, story, audience='player'):
    """Quests this audience may be offered right now — with nothing hidden leaking.

    A quest with no ``public_summary`` never appears; one gated by ``reveal_flag`` waits
    for that flag; one bound to ``location`` needs that place. Hidden objectives, costs,
    payment accounts and the failure rule are never in this projection.
    """
    cfg = rules(story)
    if cfg is None:
        return []
    rows = state(session, cfg)['entries']
    out = []
    for quest in cfg.quests:
        row = rows.get(quest.id)
        current = row['state'] if row else 'proposed'
        if current in TERMINAL_STATES:
            continue
        if not _visible(quest, session, audience):
            continue
        if not _near(quest, session):
            continue
        # ``giver`` is an author-side entity id: it is not exposed, only the human
        # ``title`` and the author's ``public_summary`` are.
        item = {'quest_id': quest.id, 'title': quest.title,
                'summary': quest.public_summary, 'state': current,
                'location': quest.location or None,
                'due': row['due'] if row else None}
        if current == 'active':
            item['missing'] = missing_evidence(session, quest, story)
        out.append(item)
    out.sort(key=lambda item: item['quest_id'])
    return out


def public_view(session, story, audience='player'):
    """Player-safe projection. Counts stay out unless the audience may see the quest."""
    rows = available(session, story, audience)
    return {'audience': audience, 'quests': rows, 'counts': {'visible': len(rows)}}


def context_snippet(session, story, limit=400):
    """One bounded line for a prompt: the visible quests, titles only."""
    rows = available(session, story, 'player')
    if not rows:
        return ''
    parts = []
    for row in rows[:4]:
        text = '%s（%s）' % (row['title'], row['state'])
        if row.get('summary'):
            text += '：' + row['summary']
        parts.append(text)
    text = '；'.join(parts)
    return text[:limit]


def authority_view(session, story, quest_id=None):
    """Author-side view: every declared field, including secrets and the due rule."""
    cfg = rules(story)
    if cfg is None:
        return None
    rows = state(session, cfg)['entries']
    picked = [q for q in cfg.quests if quest_id is None or q.id == quest_id]
    out = []
    for quest in picked:
        row = rows.get(quest.id) or {'state': 'proposed', 'since': None, 'due': None,
                                     'paid': None, 'note': '', 'evidence': {}}
        out.append({'quest_id': quest.id, 'title': quest.title, 'giver': quest.giver,
                    'location': quest.location or None, 'state': row['state'],
                    'due': row['due'], 'paid': row['paid'], 'note': row['note'],
                    'secret_objective': quest.secret_objective,
                    'objectives': list(quest.objectives),
                    'evidence': [e.model_dump() for e in quest.evidence],
                    'costs': [c.model_dump() for c in quest.costs],
                    'rewards': [r.model_dump() for r in quest.rewards],
                    'effects': [e.model_dump() for e in quest.effects],
                    'on_failure': quest.on_failure or None,
                    'missing_now': (missing_evidence(session, quest, story)
                                    + _affordable(session, quest, story))
                    if row['state'] == 'active' else []})
    return {'quests': out}


# --------------------------------------------------------------- action offers
def actions(session, story, audience='player'):
    """Offer the transitions the engine can already execute, as existing action dicts.

    The shape follows ``adventure_actions`` (id / label / requires / effects) so the
    Runtime can consume it without a second vocabulary. Nothing here executes; the ids
    carry a reserved ``quest:`` prefix and the real state change goes through
    :func:`apply_completion` with the Runtime's own confirmation token.
    """
    cfg = rules(story)
    if cfg is None:
        return []
    rows = state(session, cfg)['entries']
    offers = []
    for item in available(session, story, audience):
        quest = _quest(cfg, item['quest_id'])
        row = rows.get(quest.id)
        current = row['state'] if row else 'proposed'
        if current == 'proposed':
            offers.append({'id': 'quest:accept:%s' % quest.id,
                           'label': '接下：%s' % quest.title,
                           'kind': 'quest', 'quest_id': quest.id,
                           'transition': 'accept', 'supported': True})
        elif current == 'accepted':
            offers.append({'id': 'quest:start:%s' % quest.id,
                           'label': '开始：%s' % quest.title,
                           'kind': 'quest', 'quest_id': quest.id,
                           'transition': 'start', 'supported': True})
        elif current == 'active':
            gaps = missing_evidence(session, quest, story) + _affordable(
                session, quest, story)
            offers.append({'id': 'quest:complete:%s' % quest.id,
                           'label': '交付：%s' % quest.title,
                           'kind': 'quest', 'quest_id': quest.id,
                           'transition': 'complete',
                           'supported': not gaps,
                           'obstruction': ('；'.join(gaps) if gaps else None)})
    return offers


# --------------------------------------------------------------------- callback
def runtime_hooks():
    """The two call sites the Runtime needs, as plain names (no import cycle).

    ``on_time_advance`` is called from the single existing clock advance (``pressure``),
    ``on_action`` from the existing action confirmation path. Both are no-ops when the
    package declares no quests, so an old journey is byte-for-byte unchanged.
    """
    return {'validate': 'quests.validate',
            'on_time_advance': 'quests.expire',
            'on_action': 'quests.apply_transition',
            'projection': 'quests.public_view'}


def apply_transition(session, story, quest_id, transition, effects_fn=None, source=None):
    """One entry point for the Runtime: accept / start / complete / cancel."""
    if transition == 'accept':
        return accept(session, story, quest_id)
    if transition == 'start':
        return start(session, story, quest_id)
    if transition == 'complete':
        return apply_completion(session, story, quest_id, effects_fn=effects_fn,
                                source=source)
    if transition == 'cancel':
        return cancel(session, story, quest_id)
    raise QuestError('不认识的任务推进：%r' % (transition,))