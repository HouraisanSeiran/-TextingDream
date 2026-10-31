# -*- coding: utf-8 -*-
"""三种起点（start_profiles）：严格配置 + **原子初始化**。

关键顺序（首轮审查意见 3）：``apply()`` 必须发生在任何 ``clock.advance()`` 与
``Runtime.enter()`` **之前**。否则会出现「先按旧开局跑了一次日程/效果，再覆盖成新开局」，
日程与一次性效果已经执行过，玩家却看到新起点。因此本模块只做一件事：
把包里的声明**一次性**写进候选 session，然后再让 clock / enter 接手。

所有写入都在调用方传进来的 session（已经是深拷贝候选）上完成；任何一条非法
（未知货币、超额、未知物品/角色/模板/事件、关系目标不存在、入口事件不可达）都抛错，
调用方此时还没有保存，于是**零写入**。

开局钱货与物品由引擎侧发放（``rewards.seed_start``），与模型正文完全无关：
模型写「你得到一袋米」不会改变 wallet / inventory。

严格性（预审 A）：本模块模型一律 ``strict=True``，并对 wallet / flags / trust /
public / version 另加 ``mode='before'`` 的原始类型检查——Pydantic 的数值塔会把
``true`` 与 ``'3'`` 强转成整数，那会让后面的 ``isinstance`` 检查形同虚设。
"""
from __future__ import annotations

import copy
import hashlib

from pydantic import BaseModel, ConfigDict, Field, model_validator

from . import rewards as rewards_rules
from . import traits as traits_rules

MECHANICS_KEY = 'start_profiles'
SCHEMA_VERSION = 1
ID = r'^[A-Za-z0-9_-]{1,60}$'
MAX_PROFILES = 6
MAX_ITEMS = 8
MAX_WALLET_ENTRIES = 4
MAX_REWARD_ITEMS = 4
MAX_RELATIONS = 6
MAX_KNOWN = 6
MAX_EXPLORED = 6
KNOWN_CHARS = 300
# 新旅程固定从第 8 小时开始（与 Runtime.new_session 的 time=8 一致）。
INITIAL_TIME = 8


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


def _reject_raw(value, label, kinds, extra=''):
    if isinstance(value, bool) and bool not in kinds:
        raise ValueError('%s不接受布尔值%s' % (label, extra))
    if not isinstance(value, kinds):
        raise ValueError('%s类型无效（得到 %s）%s' % (label, type(value).__name__, extra))


class Relation(Strict):
    trust: float = Field(ge=0, le=1, allow_inf_nan=False)
    note: str = Field(default='', max_length=120)

    @model_validator(mode='before')
    @classmethod
    def raw_types(cls, data):
        if isinstance(data, dict):
            if 'trust' in data:
                _reject_raw(data['trust'], '关系 trust', (int, float),
                            '；请写 0 到 1 之间的数值')
                if data['trust'] != data['trust'] or data['trust'] in (
                        float('inf'), float('-inf')):
                    raise ValueError('关系 trust 必须是有限数值')
            if 'note' in data:
                _reject_raw(data['note'], '关系 note', (str,))
        return data


class Known(Strict):
    id: str = Field(pattern=ID)
    text: str = Field(min_length=1, max_length=KNOWN_CHARS)
    source: str = Field(default='开局已知', min_length=1, max_length=60)
    # public=True 表示玩家开局就知道；False 表示只有 known_by 里的角色知道。
    # 二者是「谁知道」的差别，不是「真/假」：非公开信息同样确定，只是玩家没被告知。
    public: bool = True
    known_by: list[str] = Field(default_factory=list, max_length=6)

    @model_validator(mode='before')
    @classmethod
    def raw_types(cls, data):
        if isinstance(data, dict) and 'public' in data:
            _reject_raw(data['public'], '已知信息 public', (bool,))
        return data


class Profile(Strict):
    id: str = Field(pattern=ID)
    title: str = Field(min_length=1, max_length=40)
    summary: str = Field(min_length=1, max_length=200)
    identity: str = Field(min_length=1, max_length=120)
    location: str = Field(min_length=1, max_length=60)
    # 起点明确声明的「以前去过的地方」。不声明就只有起点本身——
    # 绝不把 new_session 里那个角色包默认地点顺手算作已探索（那会让不同起点
    # 共享同一份地图知识，等于泄露另一个起点的默认位置）。
    explored: list[str] = Field(default_factory=list, max_length=MAX_EXPLORED)
    items: list[str] = Field(default_factory=list, max_length=MAX_ITEMS)
    wallet: dict[str, int] = Field(default_factory=dict)
    reward_items: list[str] = Field(default_factory=list, max_length=MAX_REWARD_ITEMS)
    relations: dict[str, Relation] = Field(default_factory=dict)
    known: list[Known] = Field(default_factory=list, max_length=MAX_KNOWN)
    goal: str = Field(min_length=1, max_length=200)
    traits: list[dict] = Field(default_factory=list, max_length=traits_rules.MAX_REFS)
    # 起点自带的标记。入口事件的每个前置都必须在这里被显式声明为相同取值，
    # 且不能多声明入口事件不要求的标记（那会让它与 candidates() 不一致）。
    flags: dict[str, bool] = Field(default_factory=dict)
    entry_event: str | None = Field(default=None, max_length=60)

    @model_validator(mode='before')
    @classmethod
    def raw_types(cls, data):
        """在 Pydantic 转换之前核对原始类型，堵住 true→1 / '3'→3 这条捷径。"""
        if not isinstance(data, dict):
            return data
        wallet = data.get('wallet')
        if wallet is not None:
            if not isinstance(wallet, dict):
                raise ValueError('开局钱货必须是对象')
            if len(wallet) > MAX_WALLET_ENTRIES:
                raise ValueError('开局钱货最多 %d 种货币' % MAX_WALLET_ENTRIES)
            for key, value in wallet.items():
                _reject_raw(key, '开局钱货的货币 ID', (str,))
                _reject_raw(value, '开局钱货「%s」的数量' % key, (int,),
                            '；字符串与布尔都不算整数')
                if not 0 <= value <= 10 ** 9:
                    raise ValueError('开局钱货必须在 0..1000000000：%s' % key)
        flags = data.get('flags')
        if flags is not None:
            if not isinstance(flags, dict):
                raise ValueError('起点 flags 必须是对象')
            for key, value in flags.items():
                _reject_raw(key, '起点 flags 的标记名', (str,))
                _reject_raw(value, '起点 flags「%s」' % key, (bool,),
                            '；不接受 0/1 或文本')
        relations = data.get('relations')
        if relations is not None and not isinstance(relations, dict):
            raise ValueError('开局关系必须是对象')
        for key in ('items', 'reward_items', 'explored', 'known', 'traits'):
            if key in data and data[key] is not None and not isinstance(data[key], list):
                raise ValueError('%s 必须是列表' % key)
        if 'entry_event' in data and data['entry_event'] is not None:
            _reject_raw(data['entry_event'], '起点 entry_event', (str,))
        return data

    @model_validator(mode='after')
    def bounds(self):
        if len(self.relations) > MAX_RELATIONS:
            raise ValueError('开局关系最多 %d 个角色' % MAX_RELATIONS)
        if len(self.wallet) > MAX_WALLET_ENTRIES:
            raise ValueError('开局钱货最多 %d 种货币' % MAX_WALLET_ENTRIES)
        if len(set(self.items)) != len(self.items):
            raise ValueError('开局物品不能重复')
        if len(set(self.reward_items)) != len(self.reward_items):
            raise ValueError('开局物品实例不能重复')
        if len(set(self.explored)) != len(self.explored):
            raise ValueError('起点已探索地点不能重复')
        if self.location in self.explored:
            raise ValueError('起点地点 %s 不要重复写进 explored（引擎会自动包含它）'
                             % self.location)
        for label, values in (('开局物品', self.items),
                              ('开局物品实例', self.reward_items),
                              ('已探索地点', self.explored)):
            if any(not isinstance(v, str) or not v.strip() for v in values):
                raise ValueError('%s必须是非空文本' % label)
        seen = set()
        for known in self.known:
            if known.id in seen:
                raise ValueError('同一起点里已知信息 ID 重复：' + known.id)
            seen.add(known.id)
            audiences = list(dict.fromkeys(known.known_by))
            if len(audiences) != len(known.known_by):
                raise ValueError('已知信息 %s 的受众列表有重复' % known.id)
            if known.public and 'player' in audiences:
                raise ValueError('已知信息 %s 已是 public，known_by 里不要再写 player'
                                 % known.id)
            if not known.public and 'player' in audiences:
                raise ValueError('已知信息 %s 是 public=false，不能把 player 列进受众；'
                                 '要玩家开局就知道请用 public=true' % known.id)
        return self


class StartProfiles(Strict):
    version: int = Field(ge=1, le=1)
    note: str = Field(default='', max_length=300)
    default_profile: str | None = Field(default=None, max_length=60)
    profiles: list[Profile] = Field(min_length=1, max_length=MAX_PROFILES)

    @model_validator(mode='before')
    @classmethod
    def raw_types(cls, data):
        if isinstance(data, dict) and 'version' in data:
            _reject_raw(data['version'], '起点配置版本', (int,),
                        '；本版只支持 1，布尔与文本都不接受')
            if data['version'] != SCHEMA_VERSION:
                raise ValueError('起点配置版本必须是 %d' % SCHEMA_VERSION)
        return data

    @model_validator(mode='after')
    def unique_ids(self):
        ids = [p.id for p in self.profiles]
        if len(set(ids)) != len(ids):
            raise ValueError('起点 ID 重复')
        if self.default_profile is not None and self.default_profile not in ids:
            raise ValueError('默认起点不在 profiles 里：' + self.default_profile)
        return self


# ----------------------------------------------------------------- 读取/校验
def config(story):
    """故事包声明的起点配置；没有就是 None（老包行为完全不变）。"""
    mechanics = (story or {}).get('mechanics') or {}
    if not isinstance(mechanics, dict):
        return None
    raw = mechanics.get(MECHANICS_KEY)
    if raw is None:
        return None
    return StartProfiles.model_validate(raw)


def entry_eligibility(story, profile):
    """入口事件的**入口资格**：正前置、负前置、上游、时间窗一起看。

    刻意不做「把上游当作已完成」的便利——那会让玩家跳过整段调查，
    等于把未发生的进展默认写进开局。
    """
    events = {e['id']: e for e in story.get('events', [])}
    event = events.get(profile.entry_event)
    if event is None:
        raise ValueError('起点 %s 的入口事件不存在：%s'
                         % (profile.id, profile.entry_event))
    if event['location_id'] != profile.location:
        raise ValueError('起点 %s 的入口事件 %s 在 %s，不在起点地点 %s'
                         % (profile.id, profile.entry_event, event['location_id'],
                            profile.location))
    incoming = sorted(other['id'] for other in story.get('events', [])
                      if profile.entry_event in (other.get('next_events') or []))
    if incoming:
        # 入口事件必须是根节点：有上游说明它是续篇，一开局就进去等于把
        # 未完成的上游默认成已完成。
        raise ValueError('起点 %s 的入口事件 %s 还有上游事件（%s）；'
                         '入口事件必须是根节点'
                         % (profile.id, profile.entry_event, '、'.join(incoming)))
    required = dict(event.get('entry_flags') or {})
    for flag, value in required.items():
        declared = profile.flags.get(flag)
        if declared is None:
            raise ValueError('起点 %s 的入口事件 %s 需要前置 %s=%s，起点没有声明该 flag'
                             % (profile.id, profile.entry_event, flag,
                                'true' if value else 'false'))
        if declared is not value:
            raise ValueError('起点 %s 的入口事件 %s 需要 %s=%s，起点声明的是 %s'
                             % (profile.id, profile.entry_event, flag,
                                'true' if value else 'false', declared))
    extra = set(profile.flags) - set(required)
    if extra:
        # 起点可以声明额外标记（用于区分三种起点），但必须有人真的读它：
        # 某个动作的前置、某条压力条件或某个结局条件。否则它就是一条死声明。
        used = set()
        for other in story.get('events', []):
            for action in other.get('actions', []):
                used |= set((action.get('requires') or {}))
        for pressure in (((story.get('mechanics') or {}).get('pressure') or {})
                         .get('pressures') or []):
            for stage in pressure.get('stages') or []:
                when = stage.get('when') or {}
                used |= set(when.get('all_flags') or {})
                used |= set(when.get('any_flags') or {})
                used |= set(when.get('not_flags') or [])
        for ending in (((story.get('mechanics') or {}).get('endings') or {})
                       .get('endings') or []):
            condition = ending.get('condition') or {}
            used |= set(condition.get('all_flags') or {})
            used |= set(condition.get('any_flags') or {})
            used |= set(condition.get('not_flags') or [])
        dead = extra - used
        if dead:
            raise ValueError('起点 %s 声明了没人读取的 flag：%s'
                             % (profile.id, '、'.join(sorted(dead))))
    low = event.get('time_min', 0)
    high = event.get('time_max', 10 ** 9)
    if not low <= INITIAL_TIME <= high:
        raise ValueError('起点 %s 的入口事件 %s 的时间窗是 %s..%s，开局时刻 %d 不在其中'
                         % (profile.id, profile.entry_event, low, high, INITIAL_TIME))
    nexts = set(event.get('next_events') or [])
    if set(event.get('next_events') or []) - set(events):
        raise ValueError('起点 %s 的入口事件引用了不存在的后继事件' % profile.id)
    return {'event': event, 'incoming': incoming, 'next': sorted(nexts)}


def validate_package(story, characters):
    """包级校验：起点里引用的地点/物品/角色/货币/模板/事件必须真实存在。"""
    cfg = config(story)
    if cfg is None:
        return None
    places = {x['id'] for x in story.get('locations', [])}
    items = {x['id'] for x in story.get('items', [])}
    chars = {c['id'] for c in characters.get('characters', [])}
    reward_cfg = rewards_rules.rules(story)
    currencies = {c.id: c for c in (reward_cfg.currencies if reward_cfg else [])}
    templates = {t.id for t in (reward_cfg.templates if reward_cfg else [])}
    snapshotted = traits_rules.package_traits(story) is not None
    for profile in cfg.profiles:
        if profile.location not in places:
            raise ValueError('起点 %s 的地点不存在：%s' % (profile.id, profile.location))
        unknown_explored = [x for x in profile.explored if x not in places]
        if unknown_explored:
            raise ValueError('起点 %s 的已探索地点不存在：%s'
                             % (profile.id, '、'.join(unknown_explored)))
        unknown_items = [i for i in profile.items if i not in items]
        if unknown_items:
            raise ValueError('起点 %s 引用了不存在的物品：%s'
                             % (profile.id, '、'.join(unknown_items)))
        for currency in profile.wallet:
            if currency not in currencies:
                raise ValueError('起点 %s 的钱货引用了未在 mechanics.rewards 声明的货币：%s'
                                 % (profile.id, currency))
            if profile.wallet[currency] > currencies[currency].maximum:
                raise ValueError('起点 %s 的 %s 超过该货币上限'
                                 % (profile.id, currency))
        unknown_templates = [t for t in profile.reward_items if t not in templates]
        if unknown_templates:
            raise ValueError('起点 %s 引用了不存在的物品模板：%s'
                             % (profile.id, '、'.join(unknown_templates)))
        if profile.reward_items and reward_cfg is None:
            raise ValueError('起点 %s 要发放物品实例，但故事包未配置 mechanics.rewards'
                             % profile.id)
        for character in profile.relations:
            if character not in chars:
                raise ValueError('起点 %s 的关系引用了不存在的角色：%s'
                                 % (profile.id, character))
        for known in profile.known:
            unknown = set(known.known_by) - chars
            if unknown:
                raise ValueError('起点 %s 的已知信息受众不存在：%s'
                                 % (profile.id, '、'.join(sorted(unknown))))
        if profile.traits:
            if not snapshotted:
                raise ValueError('起点 %s 声明了特质，但故事包没有 mechanics.traits 快照'
                                 % profile.id)
            traits_rules.validate_character({'trait_refs': profile.traits}, story)
        if profile.entry_event is not None:
            entry_eligibility(story, profile)
    return cfg


# ------------------------------------------------------------------- 应用
def resolve(cfg, profile_id):
    """选出一个起点。``None`` 只有一种含义：不应用任何起点（旧行为）。

    * 传了 id → 必须是配置里存在的那个，否则报错（不静默退回默认）。
    * 没传 id 但配置声明了 ``default_profile`` → 用它。
    * 都没给 → 返回 None。
    """
    if cfg is None:
        if profile_id:
            raise ValueError('本故事包没有声明起点（mechanics.start_profiles）')
        return None
    if profile_id:
        chosen = next((p for p in cfg.profiles if p.id == profile_id), None)
        if chosen is None:
            raise ValueError('起点不存在：%s（可选：%s）'
                             % (profile_id, '、'.join(p.id for p in cfg.profiles)))
        return chosen
    if cfg.default_profile:
        return next(p for p in cfg.profiles if p.id == cfg.default_profile)
    return None


def _digest(*parts):
    return hashlib.sha256(':'.join(str(x) for x in parts).encode('utf-8')).hexdigest()[:16]


def _known_audiences(known):
    """一个已知信息应当到达谁：public 给玩家 + 各自声明的角色，绝不重复。"""
    audiences = []
    if known.public:
        audiences.append('player')
    for character in known.known_by:
        if character not in audiences:
            audiences.append(character)
    return audiences


def apply(session, story, characters, profile):
    """把起点写进**候选** session。返回回执；任何失败都不留半套。

    调用方保证：本函数在任何 ``clock.advance()`` 与 ``enter()`` 之前调用，
    且 session 尚未保存（失败时天然零写入）。
    """
    if profile is None:
        return None
    hero = session['hero']
    if session.get('start'):
        raise ValueError('本次旅程已经应用过起点，不能重复应用')
    receipt = {'profile_id': profile.id, 'title': profile.title,
               'identity': profile.identity, 'goal': profile.goal,
               'location': profile.location, 'applied_at': session['time'],
               'key': _digest(session['seed'], profile.id)}
    # 1) 位置：地点、主角位置、已探索三处一起重建。explored 只来自起点声明，
    #    不继承 new_session 里那个角色包默认地点。
    session['location'] = profile.location
    session['characters'][hero]['location'] = profile.location
    explored = [profile.location]
    for place in profile.explored:
        if place not in explored:
            explored.append(place)
    session['explored'] = explored
    # 2) 起点声明的标记（入口事件的前置只能来自这里，已在校验里核过）。
    for flag, value in profile.flags.items():
        session['flags'][flag] = bool(value)
    # 3) 身份与目标作为引擎事实（公开、确定性），不走模型正文。
    fact_id = 'start:' + receipt['key'] + ':identity'
    fact = {'id': fact_id, 'text': '开局身份：' + profile.identity,
            'time': session['time'], 'source': 'start:' + profile.id}
    session['facts'].append(fact)
    session['heard'].append({**fact, 'id': fact_id + ':heard', 'source_fact': fact_id,
                             'distortion': 0, 'intensity': 0.6})
    # 4) 世界物品：作者显式声明，因此不要求该物品此刻绑定在本地点；
    #    这是唯一绕过 `take` 的地点检查的路径，且只发生在开局。
    for item_id in profile.items:
        if item_id in session['inventory']:
            continue
        session['inventory'].append(item_id)
        name = next(i['name'] for i in story.get('items', []) if i['id'] == item_id)
        session['facts'].append({'id': 'start:%s:item:%s' % (receipt['key'], item_id),
                                 'text': '随身带来' + name, 'time': session['time'],
                                 'source': 'start:' + profile.id})
    # 5) 钱货与物品实例：引擎侧发放，命名空间 `start:` 与后续 grant 隔离。
    seeded = rewards_rules.seed_start(session, story, profile.wallet,
                                      profile.reward_items, 'start:' + profile.id)
    if seeded:
        receipt['rewards'] = seeded
    # 6) 关系：写进既有的 development.relationships（不新开第二份关系表）。
    for character_id, relation in profile.relations.items():
        block = session.setdefault('development', {}).setdefault(character_id, {})
        block.setdefault('relationships', {}).setdefault(hero, {})['trust'] = relation.trust
        if relation.note:
            block['relationships'][hero]['note'] = relation.note
    # 7) 已知信息：按受众分别落位，同一受众只写一次。非公开信息仍是确定信息
    #    （distortion 0 + 明确来源），只是玩家没被告知——秘密不等于虚假。
    for known in profile.known:
        audiences = _known_audiences(known)
        base = {'text': known.text, 'time': session['time'],
                'source': known.source, 'distortion': 0, 'intensity': 0.5}
        for audience in audiences:
            if audience == 'player':
                session['heard'].append({**base,
                                         'id': 'start:%s:known:%s'
                                               % (receipt['key'], known.id)})
            else:
                session['beliefs'].append({**base, 'character': audience,
                                           'kind': 'information',
                                           'certainty': '开局已知，来源见 source',
                                           'id': 'start:%s:known:%s:%s'
                                                 % (receipt['key'], known.id, audience)})
        if not audiences:
            # 谁都不该知道：只进客观事实层，供作者核对；玩家与角色都读不到。
            session['facts'].append({**base,
                                     'id': 'start:%s:known:%s:fact'
                                           % (receipt['key'], known.id)})
    # 8) 主角特质：起点追加，不覆盖角色包里已有的；同一 ref 必须同版本，
    #    合并后的总数仍受上限约束。角色包对象本身不被修改。
    if profile.traits:
        hero_character = next(c for c in characters['characters'] if c['id'] == hero)
        merged = [dict(ref) for ref in (hero_character.get('trait_refs') or [])]
        index = {ref.get('template'): ref for ref in merged}
        for raw in profile.traits:
            name = raw.get('template')
            if name in index:
                if index[name].get('version') != raw.get('version'):
                    raise ValueError('起点 %s 的特质 %s 与角色包已有版本冲突'
                                     '（%s vs %s）'
                                     % (profile.id, name, index[name].get('version'),
                                        raw.get('version')))
                continue
            merged.append(dict(raw))
            index[name] = raw
        if len(merged) > traits_rules.MAX_REFS:
            raise ValueError('主角特质超过 %d 条上限（角色包 %d + 起点 %d）'
                             % (traits_rules.MAX_REFS,
                                len(hero_character.get('trait_refs') or []),
                                len(profile.traits)))
        session['hero_traits'] = traits_rules.validate_character(
            {'trait_refs': merged}, story)
    receipt['traits'] = len(session.get('hero_traits') or [])
    if profile.entry_event:
        receipt['entry_event'] = profile.entry_event
    session['start'] = receipt
    return receipt


def surface(session, story):
    """玩家可见的起点回执：只讲他自己知道的事。

    刻意不写「引擎一次性写入」「模型不会补发」这类实现说明——那是作者侧边界，
    不该出现在前台叙事里（预审 F）。
    """
    receipt = session.get('start')
    if not receipt or 'profile_id' not in receipt:
        return None
    cfg = config(story)
    profile = None
    if cfg is not None:
        profile = next((p for p in cfg.profiles if p.id == receipt['profile_id']), None)
    return {'profile_id': receipt['profile_id'], 'title': receipt.get('title', ''),
            'identity': receipt.get('identity', ''), 'goal': receipt.get('goal', ''),
            'location': receipt.get('location'),
            'known': [{'id': k.id, 'text': k.text, 'source': k.source}
                      for k in (profile.known if profile else []) if k.public]}


def author_view(session, story):
    """作者视图：实现说明 + 全部已知信息（含非公开）。"""
    public = surface(session, story)
    if public is None:
        return None
    cfg = config(story)
    profile = None
    if cfg is not None:
        profile = next((p for p in cfg.profiles if p.id == public['profile_id']), None)
    result = copy.deepcopy(public)
    result['receipt'] = copy.deepcopy(session.get('start'))
    result['known_all'] = [{'id': k.id, 'text': k.text, 'source': k.source,
                            'public': k.public, 'known_by': list(k.known_by)}
                           for k in (profile.known if profile else [])]
    result['note'] = ('开局由引擎一次性写入：钱货、物品、关系、已知信息与标记都在同一个事务里；'
                      '模型正文不会补发其中任何一项；标记与位置在 advance/enter 之前就位')
    return result
