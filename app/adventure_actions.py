# -*- coding: utf-8 -*-
"""冒险行动：把作者已配置的目标变成**有界、可复核的行动方案**（纯规则，不执行）。

八类通用行动共用一条装配路径（``_action_dict`` / ``_plan``），只有「目标从哪来」和
「效果从哪来」按类分开：

============  ================================  ===================================
类            目标（合法目标的全部来源）          效果来源（只能是作者声明的）
============  ================================  ===================================
observe       当前地点                         该地点绑定、``action_kinds`` 含 observe 的线索
investigate   当前地点的物品（地点对象）        绑定到该物品的线索
ask           在场人物                          topic(ask) 中**首个**条件成立的分支
negotiate     在场人物                          topic(negotiate) 的首个分支
travel        当前地点的邻接且玩家已知的地点     邻接表 + 作者 route（可选）
rest          自己                              模板声明的 effects（不声明就只有时间推进）
take          当前地点的物品                   既有 ``take`` op（Runtime 已支持）
use           已持有的 legacy 物品             模板声明的 effects（不声明就不产生方案）
give          已持有物品 × 在场人物             无执行器 → supported=False，不虚构 op
============  ================================  ===================================

与既有模块的分工（不重复任何引擎）：

* **不掷骰**：``check`` 原样透传，由 ``drama.resolve_check`` 在 ``Runtime.prepare_turn``
  里执行；这里只校验属性名与难度范围。
* **不扣费、不推进时钟、不改 state**：建议零副作用。旅行由 ``Runtime.move`` 执行，
  休息走既有 ``/wait`` 或既有 action 管线，两者都只经过 ``pressure.advance`` 这一个时钟。
* **不发奖、不保存**：这个模块没有任何 ``rewards`` / ``store`` 调用，也不写 session。
* **不把自然语言变 effect**：只有作者声明的线索/分支/模板能进 ``effects``；玩家那句话
  永远不会成为标记、物品、通行或知识。
* **不认模型知识**：目标只来自作者数据；未声明的目标不会因为「模型觉得这里有东西」出现。
* **不造第二套确认凭据**：方案里的 ``action`` 就是既有故事动作 schema，``free_actions``
  的 ``summarise`` / ``confirm_token`` / ``verify`` 可以原样吃（CAS 仍是 ``state_version``）。

可见性与合法性是两件事：``play_map.visible_places`` 决定一个地点**能不能被提及**，
本模块的邻接/条件判断决定**能不能被建议**。未公开的地点既不出现在方案里，也不出现在
拒绝理由里，更不计数；已知但被条件封锁的地点只返回作者写的 ``public_obstruction``，
不返回秘密条件本身。

作者声明位置：``story.mechanics.adventure``（纯新增键；没有这个键时本模块全部 no-op，
老故事包一字不变）。声明结构见 ``docs/adventure-actions-contract.md``。
"""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

from . import attributes, free_actions, local_rules, play_map

SCHEMA_VERSION = 1
MECHANICS_KEY = 'adventure'
#: 运行时方案专用的 id 前缀：``adventure:<kind>:...``。静态事件动作不得占用。
ID_PREFIX = 'adventure:'
ID = r'^[A-Za-z0-9_-]{1,60}$'
MAX_HOURS = 168
MAX_EFFECTS = 12
MAX_ANSWERS = 6
MAX_CLUES = 200
MAX_TOPICS = 100
MAX_ROUTES = 200
MAX_TEMPLATES = 100
MAX_INSTANCES = 20

ActionKind = Literal['observe', 'investigate', 'ask', 'negotiate', 'travel',
                     'rest', 'take', 'use', 'give']
KINDS = ('observe', 'investigate', 'ask', 'negotiate', 'travel', 'rest',
         'take', 'use', 'give')
#: 可以反复做的类：时间推进与移动本身不记录在 ``actions_done`` 里。
REPEATABLE = frozenset({'rest', 'travel'})

#: 每类行动允许的目标种类。``object`` = ``story['items']`` 里的地点对象；
#: ``npc`` = 同地点的角色；``place`` = ``story['locations']``。
TARGET_KINDS = {'observe': ('place',), 'investigate': ('object',), 'ask': ('npc',),
                'negotiate': ('npc',), 'travel': ('place',), 'rest': (),
                'take': ('object',), 'use': ('object',), 'give': ('object',)}

#: 玩家可见的默认阻碍文本。**不含**秘密条件、数量或未发生的结果。
DEFAULT_OBSTRUCTION = {
    'observe': '这里暂时看不出更多可确认的细节。',
    'investigate': '这个物件眼下还给不出更多可确认的信息。',
    'ask': '这件事现在问不出结果。',
    'negotiate': '现在谈不成。',
    'travel': '这条路现在走不通。',
    'rest': '现在休息不了。',
    'take': '现在还拿不走。',
    'use': '现在用不了。',
    'give': '现在交不出去。',
}
UNRULED_TEXT = ('作者没有为这种情况定义结果分支；引擎不裁定，这句话只作为台词，不改变状态。')
WORLD_MISMATCH_TEXT = '这条路线不属于这段旅程的世界，已拒绝。'
WORLD_UNVERIFIED_TEXT = '这段旅程还没有关联地图，无法确认这条路线属于同一世界。'
NEED_WIRING_TEXT = ('动态方案集合还没有接进执行管线：确认凭据 free_actions.confirm_token '
                    '只认当前 node.actions 里的动作，接线层适配后复用同一个凭据；'
                    '本函数不签发凭据。')

DEFAULT_LABEL = {
    'observe': '观察{target}', 'investigate': '查看{target}', 'ask': '向{target}打听',
    'negotiate': '与{target}交谈', 'travel': '前往{target}',
    'rest': '原地休息 {hours} 小时', 'take': '拿起{target}', 'use': '使用{target}',
    'give': '把{target}交给{npc}',
}


# --------------------------------------------------------------------- 声明 schema
class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Information(Strict):
    """与 ``Runtime._apply_effects`` 的 ``information`` 同一个形状。"""
    op: Literal['information'] = 'information'
    text: str = Field(min_length=1, max_length=1000)
    known_by: list[str] = Field(min_length=1, max_length=12)
    confirmed: bool = False


class FlagEffect(Strict):
    op: Literal['flag'] = 'flag'
    id: str = Field(pattern=ID)
    value: bool = True


class ResourceEffect(Strict):
    op: Literal['resource'] = 'resource'
    id: str = Field(pattern=ID)
    delta: int = Field(ge=-1000000000, le=1000000000, strict=True)


class StatusEffect(Strict):
    op: Literal['status'] = 'status'
    id: str = Field(min_length=1, max_length=60)
    delta: float = Field(ge=-1, le=1)


class HealthEffect(Strict):
    op: Literal['health'] = 'health'
    delta: int = Field(ge=-10000, le=10000, strict=True)


class FactEffect(Strict):
    op: Literal['fact'] = 'fact'
    text: str = Field(min_length=1, max_length=600)
    visible: bool = False


#: 只用 Runtime 已经实现的效果 op；``take`` 由本模块自己生成（见 ``take``），
#: ``rumor`` 未收进来（需要 truth/character 组合，作者可改用 information + flag）。
Effect = Annotated[Union[Information, FlagEffect, ResourceEffect, StatusEffect,
                         HealthEffect, FactEffect], Field(discriminator='op')]


class Target(Strict):
    kind: Literal['place', 'object', 'npc']
    id: str = Field(pattern=ID)


class Condition(Strict):
    """条件只用既有的 flags 协议，编译结果与 ``Runtime.prepare_turn`` 的检查同形。"""
    all_flags: dict[str, bool] = Field(default_factory=dict)
    not_flags: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode='after')
    def _no_contradiction(self):
        for name in self.not_flags:
            if name in self.all_flags:
                raise ValueError('标记 %s 不能同时出现在 all_flags 与 not_flags' % name)
        return self

    def compiled(self):
        out = dict(self.all_flags)
        for name in self.not_flags:
            out[name] = False
        return out

    def met(self, session):
        flags = (session or {}).get('flags') or {}
        return all(flags.get(k, False) == v for k, v in self.compiled().items())


class Check(Strict):
    attribute: str = Field(min_length=1, max_length=20)
    difficulty: float = Field(ge=0, le=1)


class Template(Strict):
    """一条**已声明动作**的模板：字段与既有故事动作一一对应，只差目标要由本模块填。"""
    kind: ActionKind
    target: Target | None = None
    label: str = Field(default='', max_length=120)
    duration_hours: int | None = Field(default=None, ge=0, le=MAX_HOURS, strict=True)
    costs: dict[str, int] = Field(default_factory=dict)
    check: Check | None = None
    requires: Condition = Field(default_factory=Condition)
    effects: list[Effect] = Field(default_factory=list, max_length=MAX_EFFECTS)
    success_text: str = Field(default='', max_length=600)
    failure_text: str = Field(default='', max_length=600)
    intent_aliases: list[str] = Field(default_factory=list, max_length=6)
    # 「给谁」只能由作者点名：不点名就没有转交方案（不做“向任何在场者”的万能转交）。
    recipients: list[str] = Field(default_factory=list, max_length=8)
    public_obstruction: str = Field(default='', max_length=200)


class Clue(Strict):
    """一条只对**指定目标**、**指定条件**生效的可观察线索。"""
    id: str = Field(pattern=ID)
    target: Target
    effects: list[Effect] = Field(min_length=1, max_length=8)
    requires: Condition = Field(default_factory=Condition)
    action_kinds: list[Literal['observe', 'investigate']] = Field(
        default_factory=lambda: ['observe', 'investigate'], max_length=2)
    public_obstruction: str = Field(default='', max_length=200)


class Answer(Strict):
    when: Condition = Field(default_factory=Condition)
    effects: list[Effect] = Field(default_factory=list, max_length=8)
    success_text: str = Field(default='', max_length=600)


class Topic(Strict):
    """一条对话分支：``target`` 留空表示「对任何在场人物都成立」，但这仍是作者声明。"""
    id: str = Field(pattern=ID)
    kind: Literal['ask', 'negotiate']
    target: Target | None = None
    answers: list[Answer] = Field(min_length=1, max_length=MAX_ANSWERS)
    requires: Condition = Field(default_factory=Condition)
    public_obstruction: str = Field(default='', max_length=200)


class Route(Strict):
    """一条**作者声明**的路线。不声明 ≠ 没有路，只是本模块不声称有路。"""
    origin: str = Field(pattern=ID)
    destination: str = Field(pattern=ID)
    kind: str = Field(default='', max_length=40)
    hours: int | None = Field(default=None, ge=0, le=MAX_HOURS, strict=True)
    requires: Condition = Field(default_factory=Condition)
    public_obstruction: str = Field(default='', max_length=200)
    import_id: str | None = Field(default=None, max_length=40)


class AdventureConfig(Strict):
    version: int = Field(strict=True)
    clues: list[Clue] = Field(default_factory=list, max_length=MAX_CLUES)
    topics: list[Topic] = Field(default_factory=list, max_length=MAX_TOPICS)
    routes: list[Route] = Field(default_factory=list, max_length=MAX_ROUTES)
    templates: list[Template] = Field(default_factory=list, max_length=MAX_TEMPLATES)
    rest_hours: int = Field(default=8, ge=0, le=MAX_HOURS, strict=True)
    max_rest_hours: int = Field(default=MAX_HOURS, ge=1, le=MAX_HOURS, strict=True)

    @model_validator(mode='after')
    def _rest_bounds(self):
        if self.rest_hours > self.max_rest_hours:
            raise ValueError('rest_hours 不能超过 max_rest_hours')
        return self


def config(story):
    """作者声明，或 ``None``（没有这个键 → 本模块全部 no-op）。"""
    mechanics = (story or {}).get('mechanics')
    if not isinstance(mechanics, dict):
        return None
    raw = mechanics.get(MECHANICS_KEY)
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError('mechanics.%s 必须是对象' % MECHANICS_KEY)
    return AdventureConfig.model_validate(raw)


# ------------------------------------------------------------------------- 校验
def _axis(name):
    axis = attributes.ALIASES.get(name, name)
    if axis not in attributes.AXES:
        raise ValueError('检定必须引用六项属性之一（得到 %r）' % (name,))
    return axis


def _check_effects(effects, characters, resources):
    for effect in effects:
        if effect.op == 'information':
            allowed = set(characters) | {'player'}
            unknown = set(effect.known_by) - allowed
            if unknown:
                raise ValueError('线索/分支信息的知情对象不存在：%s' % '、'.join(sorted(unknown)))
        elif effect.op == 'resource':
            if effect.id not in resources:
                raise ValueError('效果引用了未定义的本地资源：' + effect.id)


def _check_target(target, places, items, characters):
    if target is None:
        return
    if target.kind == 'place' and target.id not in places:
        raise ValueError('目标地点不存在：' + target.id)
    if target.kind == 'object' and target.id not in items:
        raise ValueError('目标物品不存在：' + target.id)
    if target.kind == 'npc' and characters and target.id not in characters:
        raise ValueError('目标人物不存在：' + target.id)


def validate(story, characters=None):
    """声明期校验：结构、引用与边界。返回 :class:`AdventureConfig` 或 ``None``。

    这条检查不在 ``Runtime.validate_package`` 的调用链里（那个方法属于共享入口，
    由接线方一次性加入调用 ``adventure_actions.validate``），但同一个函数对同一份
    声明是幂等的，作者侧与打包侧都可以直接调。
    """
    cfg = config(story)
    if cfg is None:
        return None
    if cfg.version != SCHEMA_VERSION:
        raise ValueError('mechanics.%s.version 必须是 %d' % (MECHANICS_KEY, SCHEMA_VERSION))
    places = {p['id'] for p in story.get('locations') or []}
    items = {i['id'] for i in story.get('items') or []}
    characters = {c['id'] for c in (characters or {}).get('characters') or []}
    resources = {r.id for r in local_rules.rules(story).resources}
    by_place = {p['id']: p for p in story.get('locations') or []}
    # 地图链接（若声明）必须本身合法；异世界判断在运行时按 route.import_id 比。
    play_map.parse_link(story)

    seen = set()
    for clue in cfg.clues:
        if clue.id in seen:
            raise ValueError('线索 ID 重复：' + clue.id)
        seen.add(clue.id)
        if clue.target.kind not in ('place', 'object'):
            raise ValueError('线索 %s 只能绑定地点或地点对象' % clue.id)
        _check_target(clue.target, places, items, characters)
        if not clue.action_kinds:
            raise ValueError('线索 %s 至少要有一个触发的行动类' % clue.id)
        _check_effects(clue.effects, characters, resources)

    seen = set()
    for topic in cfg.topics:
        if topic.id in seen:
            raise ValueError('对话分支 ID 重复：' + topic.id)
        seen.add(topic.id)
        if topic.target is not None and topic.target.kind != 'npc':
            raise ValueError('对话分支 %s 只能指向在场人物或留空' % topic.id)
        _check_target(topic.target, places, items, characters)
        for answer in topic.answers:
            _check_effects(answer.effects, characters, resources)

    seen = set()
    for route in cfg.routes:
        if route.origin not in places or route.destination not in places:
            raise ValueError('路线端点不是已声明地点：%s→%s' % (route.origin, route.destination))
        if route.origin == route.destination:
            raise ValueError('路线不能原地不动：' + route.origin)
        if route.destination not in (by_place[route.origin].get('neighbors') or []):
            raise ValueError('路线 %s→%s 不是邻接关系，移动管线会拒绝'
                             % (route.origin, route.destination))
        pair = (route.origin, route.destination)
        if pair in seen:
            raise ValueError('同一条路线重复声明：%s→%s' % pair)
        seen.add(pair)
        if route.import_id is not None and not route.import_id.strip():
            raise ValueError('路线的 import_id 留空就删掉这个字段')

    seen = set()
    for template in cfg.templates:
        allowed = TARGET_KINDS[template.kind]
        if template.target is None:
            if template.kind == 'rest':
                pass
        elif template.target.kind not in allowed:
            raise ValueError('模板（%s）的目标种类只能是 %s'
                             % (template.kind, '、'.join(allowed) or '无'))
        _check_target(template.target, places, items, characters)
        key = (template.kind, template.target.kind if template.target else None,
               template.target.id if template.target else None)
        if key in seen:
            raise ValueError('模板重复声明：%s / %s' % (template.kind, key[2] or '默认'))
        seen.add(key)
        for rid, amount in template.costs.items():
            if rid not in resources:
                raise ValueError('模板费用引用了未定义的本地资源：' + rid)
            if amount < 0:
                raise ValueError('模板费用必须是非负整数：' + rid)
        if template.check is not None:
            _axis(template.check.attribute)
        free_actions.validate_action_aliases({'id': template.kind + (':' + (key[2] or '')),
                                              'intent_aliases': list(template.intent_aliases)})
        _check_effects(template.effects, characters, resources)
        unknown = set(template.recipients) - characters
        if template.kind == 'give' and not template.recipients:
            raise ValueError('give 模板必须点名接收人（不点名就不存在转交方案）')
        if unknown:
            raise ValueError('give 模板的接收人不存在：%s' % '、'.join(sorted(unknown)))
    return cfg


# --------------------------------------------------------------------- 纯工具
def _fill(text, **values):
    out = text or ''
    for key, value in values.items():
        out = out.replace('{' + key + '}', str(value))
    return out


def _template(cfg, kind, target_row=None):
    """最具体的模板优先：``(kind, 目标)`` > ``(kind, 默认)`` > 无模板。"""
    if cfg is None:
        return None
    if target_row is not None:
        for template in cfg.templates:
            if (template.kind == kind and template.target is not None
                    and template.target.kind == target_row['kind']
                    and template.target.id == target_row['id']):
                return template
    for template in cfg.templates:
        if template.kind == kind and template.target is None:
            return template
    return None


def _action_dict(action_id, label, template, *, effects=(), requires=None,
                 success_text='', duration_hours=None):
    """把模板 + 目标拼成**既有故事动作 schema**。

    ``duration_hours`` 只有在模板显式声明（或这次调用显式给出，如休息小时）时才写进
    action：缺键时 ``free_actions.effective_duration`` 与 ``Runtime.prepare_turn``
    都会落回 ``mechanics.local.turn_hours``，与旧动作语义完全一致。
    """
    action = {'id': action_id, 'label': label, 'ends_event': False}
    if template is not None:
        if template.costs:
            action['costs'] = {rid: int(amount) for rid, amount in template.costs.items()}
        if template.check is not None:
            action['check'] = {'attribute': _axis(template.check.attribute),
                               'difficulty': template.check.difficulty}
        if template.failure_text:
            action['failure_text'] = template.failure_text
        if template.intent_aliases:
            action['intent_aliases'] = list(template.intent_aliases)
        if template.duration_hours is not None and duration_hours is None:
            duration_hours = template.duration_hours
        if template.success_text and not success_text:
            success_text = template.success_text
    if requires:
        action['requires'] = {name: bool(value) for name, value in requires.items()}
    if effects:
        action['effects'] = [dict(effect) for effect in effects]
    if success_text:
        action['success_text'] = success_text
    if duration_hours is not None:
        action['duration_hours'] = duration_hours
    return action


def _duration_of(action, story, source):
    """与 ``free_actions.effective_duration`` 同一口径：按键是否存在取默认。"""
    if 'duration_hours' in action:
        return action['duration_hours'], source
    return local_rules.rules(story).turn_hours, 'local.turn_hours'


def _plan(action_id, kind, target, label, *, action, duration_hours, duration_source,
          supported=True, unsupported=(), notes=(), extra=None, aliases=()):
    plan = {'action_id': action_id, 'kind': kind, 'target': target, 'label': label,
            'supported': bool(supported), 'unsupported': list(unsupported),
            'action': action, 'duration_hours': duration_hours,
            'duration_source': duration_source, 'notes': list(notes),
            'intent_aliases': list(aliases) or list((action or {}).get('intent_aliases') or [])}
    if extra:
        plan.update(extra)
    return plan


def _refusal(action_id, kind, target, reason, text):
    return {'action_id': action_id, 'kind': kind, 'target': target,
            'reason': reason, 'text': text}


def _obstruction(config_row, default_text):
    if config_row is not None and getattr(config_row, 'public_obstruction', ''):
        return config_row.public_obstruction
    return default_text


def _current_place(session, story):
    place_id = (session or {}).get('location')
    return next((p for p in story.get('locations') or [] if p['id'] == place_id), None)


def _scene(session, story, characters):
    """在场且可知的人物：同时在同地点、且没有被作者藏起来。

    只看两个已存在的公开事实：会话里这个人的位置，与作者声明的角色文档。
    角色 ID 存在于包里不等于玩家看得见他；``visibility: 'author'`` 与未成立的
    ``reveal_flag`` 沿用地图/知识点同一套约定，把这类角色排除在目标外。
    """
    hero = (session or {}).get('hero')
    flags = (session or {}).get('flags') or {}
    rows = []
    for character in (characters or {}).get('characters') or []:
        cid = character['id']
        if cid == hero or character.get('visibility') == 'author':
            continue
        flag = character.get('reveal_flag')
        if isinstance(flag, str) and flag and not flags.get(flag):
            continue
        seat = ((session.get('characters') or {}).get(cid) or {}).get('location')
        if seat != session.get('location'):
            continue
        rows.append({'kind': 'npc', 'id': cid,
                     'name': character.get('public_name') or character.get('name') or cid})
    return sorted(rows, key=lambda row: row['id'])


def _perceivable(item, session):
    """物品是否**可能已被玩家知道存在**：作者没有把它标成作者专属，且揭示标记已成立。

    ``story['items']`` 里有 ``description`` 不等于玩家就知道它在这里。沿用地图/知识
    点同一套两个字段：``visibility: 'author'`` 一律不出现，``reveal_flag`` 未成立也不出现。
    没写这两个字段的物品按旧包语义视为可见，但**仍然要求它在当前地点**。
    """
    if not isinstance(item, dict):
        return False
    if item.get('visibility') == 'author':
        return False
    flag = item.get('reveal_flag')
    if isinstance(flag, str) and flag and not ((session or {}).get('flags') or {}).get(flag):
        return False
    return True


def _shortfall(session, story, action):
    resources = {r.id: r for r in local_rules.rules(story).resources}
    balances = (session.get('local') or {}).get(
        'resources', {rid: spec.initial for rid, spec in resources.items()})
    short = []
    for rid, amount in sorted((action.get('costs') or {}).items()):
        if balances.get(rid, 0) < amount:
            spec = resources.get(rid)
            short.append((spec.name if spec else rid) + ' 缺 %d' % (amount - balances.get(rid, 0)))
    return short


# ------------------------------------------------------------------ 各类方案
def _reveal(kind, target_row, clues, session, story, cfg):
    """观察/调查共用的一条：满足条件的线索 → 一个方案；全被挡住 → 一条公开阻碍。"""
    name = target_row.get('name') or target_row['id']
    action_id = 'adventure:%s:%s' % (kind, target_row['id'])
    met = [clue for clue in clues if clue.requires.met(session)]
    template = _template(cfg, kind, target_row)
    # 模板自己的条件也要成立：不成立就不发方案（否则调用方会拿到一个必被 Runtime 拒的死按钮）。
    if met and (template is None or template.requires.met(session)):
        effects = [effect.model_dump() for clue in met for effect in clue.effects]
        label = _fill(template.label if template and template.label else DEFAULT_LABEL[kind],
                      target=name)
        action = _action_dict(action_id, label, template, effects=effects,
                              requires=template.requires.compiled() if template else None)
        duration, source = _duration_of(action, story, 'template')
        return _plan(action_id, kind, dict(target_row), label, action=action,
                     duration_hours=duration, duration_source=source), None
    blocked = clues or []
    template = _template(cfg, kind, target_row)
    text = DEFAULT_OBSTRUCTION[kind]
    for row in [template] + blocked:
        if row is not None and getattr(row, 'public_obstruction', ''):
            text = row.public_obstruction
            break
    return None, _refusal(action_id, kind, dict(target_row), 'condition', text)


def _talk(kind, session, story, cfg, characters):
    plans, refused = [], []
    scene = _scene(session, story, characters)
    for topic in cfg.topics:
        if topic.kind != kind:
            continue
        reachable = [row for row in scene
                     if topic.target is None or row['id'] == topic.target.id]
        if not reachable:
            continue
        if not topic.requires.met(session):
            # 话题本身是作者的秘密分支：没写公开阻碍就不透露它存在。
            if topic.public_obstruction:
                for row in reachable:
                    refused.append(_refusal(
                        'adventure:%s:%s:%s' % (kind, row['id'], topic.id), kind, dict(row),
                        'condition', topic.public_obstruction))
            continue
        for row in reachable:
            action_id = 'adventure:%s:%s:%s' % (kind, row['id'], topic.id)
            branch = next((a for a in topic.answers if a.when.met(session)), None)
            if branch is None:
                refused.append(_refusal(action_id, kind, dict(row), 'unruled', UNRULED_TEXT))
                continue
            template = _template(cfg, kind, row)
            if template is not None and not template.requires.met(session):
                refused.append(_refusal(action_id, kind, dict(row), 'condition',
                                        template.public_obstruction
                                        or DEFAULT_OBSTRUCTION[kind]))
                continue
            label = _fill(template.label if template and template.label else DEFAULT_LABEL[kind],
                          target=row['name'])
            effects = [effect.model_dump() for effect in branch.effects]
            action = _action_dict(action_id, label, template, effects=effects,
                                  requires=template.requires.compiled() if template else None,
                                  success_text=branch.success_text)
            duration, source = _duration_of(action, story, 'template')
            plans.append(_plan(action_id, kind, dict(row), label, action=action,
                               duration_hours=duration, duration_source=source))
    return plans, refused


def _travel(session, story, cfg):
    """旅行方案：只走邻接且玩家已知的地点；不按坐标算距离，也不重算全球导航。"""
    plans, refused = [], []
    place = _current_place(session, story)
    if place is None:
        return plans, refused
    by_id = {p['id']: p for p in story.get('locations') or []}
    visible = {row['id']: row for row in play_map.visible_places(session, story)}
    link = play_map.parse_link(story)
    local = local_rules.rules(story)
    for destination in place.get('neighbors') or []:
        # 作者未公开的地点：不出现、不计数、连拒绝理由都不给（否则等于报了个数）。
        if destination == place['id'] or destination not in by_id or destination not in visible:
            continue
        target_row = {'kind': 'place', 'id': destination,
                      'name': visible[destination].get('name') or by_id[destination].get('name')
                      or destination}
        action_id = 'adventure:travel:' + destination
        route = next((r for r in cfg.routes
                      if r.origin == place['id'] and r.destination == destination), None)
        template = _template(cfg, 'travel', target_row)
        requires = {}
        if route is not None:
            requires.update(route.requires.compiled())
        if template is not None:
            requires.update(template.requires.compiled())
        if route is not None and route.import_id:
            if link is None:
                refused.append(_refusal(action_id, 'travel', target_row, 'world_unverified',
                                        WORLD_UNVERIFIED_TEXT))
                continue
            if link['import_id'] != route.import_id:
                refused.append(_refusal(action_id, 'travel', target_row, 'world_mismatch',
                                        WORLD_MISMATCH_TEXT))
                continue
        flags = session.get('flags') or {}
        if not all(flags.get(k, False) == v for k, v in requires.items()):
            text = DEFAULT_OBSTRUCTION['travel']
            for row in (route, template):
                if row is not None and row.public_obstruction:
                    text = row.public_obstruction
                    break
            refused.append(_refusal(action_id, 'travel', target_row, 'condition', text))
            continue
        if route is not None and route.hours is not None:
            hours, hours_source = route.hours, 'route'
        elif template is not None and template.duration_hours is not None:
            hours, hours_source = template.duration_hours, 'template'
        else:
            hours, hours_source = local.travel_hours, 'local.travel_hours'
        from_coords = play_map.location_coordinates(place)
        to_coords = play_map.location_coordinates(by_id[destination])
        position = {'from': list(from_coords) if from_coords else None,
                    'to': list(to_coords) if to_coords else None}
        notes = []
        if route is None:
            notes.append('这条邻接没有作者声明的路线数据：耗时按 mechanics.local.travel_hours，'
                         '不代表这里有一条已绘制的道路。')
        if not from_coords or not to_coords:
            position_source = 'unrecorded'
            notes.append('地点缺少 coordinates：这里只给声明时长，不按坐标推算距离或耗时。')
        else:
            position_source = 'story_coordinates'
        costs = dict(template.costs) if template is not None else {}
        # 路费只支持 ``mechanics.local.resources`` 里声明过的资源；不足时整次移动零写入
        # （Runtime.move 在候选副本上先 charge 再写回）。不碰 rewards 货币体系。
        unsupported = []
        if any(costs.values()):
            if not local_rules.affordable(session, story, {'costs': costs}):
                refused.append(_refusal(action_id, 'travel', target_row, 'resource',
                                        '走不了：' + '、'.join(
                                            _shortfall(session, story, {'costs': costs}))))
                continue
            notes.append('这条路线要付费用：移动前在同一事务里扣除，扣不起就整次不动。')
        label = _fill(template.label if template and template.label else DEFAULT_LABEL['travel'],
                      target=target_row['name'])
        plans.append(_plan(
            action_id, 'travel', target_row, label, action=None,
            duration_hours=hours,
            duration_source=hours_source,
            supported=not unsupported,
            unsupported=unsupported,
            notes=notes,
            aliases=template.intent_aliases if template is not None else (),
            extra={'travel': {'destination': destination,
                              'route_declared': route is not None,
                              'route_kind': route.kind if route is not None else '',
                              'hours': hours, 'hours_source': hours_source,
                              'position': position, 'position_source': position_source,
                               'costs': costs, 'charges': bool(any(costs.values()))}}))
    return plans, refused


def _rest(session, story, cfg, hours):
    """休息方案：只推进时间；没有声明效果就没有回血/恢复。"""
    if isinstance(hours, bool) or not isinstance(hours, int):
        raise ValueError('休息时长必须是整数小时')
    if not 0 <= hours <= cfg.max_rest_hours:
        raise ValueError('休息时长必须在 0 到 %d 小时之间' % cfg.max_rest_hours)
    template = _template(cfg, 'rest')
    action_id = 'adventure:rest:%d' % hours
    label = _fill(template.label if template and template.label else DEFAULT_LABEL['rest'],
                  hours=hours)
    effects = [effect.model_dump() for effect in (template.effects if template else [])]
    action = _action_dict(action_id, label, template, effects=effects,
                          requires=template.requires.compiled() if template else None,
                          duration_hours=hours)
    if template is not None and template.costs and not local_rules.affordable(session, story, action):
        return None, _refusal(action_id, 'rest', None, 'resource',
                              '休息也要付出：' + '、'.join(_shortfall(session, story, action)))
    notes = []
    if not effects:
        notes.append('作者没有为休息声明效果：这里只有时间推进，不回血、不恢复疲劳。')
    # 声明了 effects / costs 的休息**不是缺口**：它走既有 action 管线（charge → effects
    # → pressure.advance 的一个事务），本模块只给出可确认的方案，不自己结算。
    plan = _plan(action_id, 'rest', None, label, action=action,
                 duration_hours=hours, duration_source='declared_hours', notes=notes,
                 extra={'wait': {'hours': hours, 'charges': False}})
    if effects or (template is not None and template.costs):
        plan['notes'].append('作者为休息声明了效果或费用：成本与效果按声明在同一个事务里结算；'
                             '没有声明就没有回血。')
    return plan, None


def _take(session, story, cfg):
    plans, refused = [], []
    place = _current_place(session, story)
    if place is None:
        return plans, refused
    held = set(session.get('inventory') or [])
    for item in story.get('items') or []:
        if item.get('location_id') != place['id'] or item['id'] in held:
            continue
        if not _perceivable(item, session):
            continue
        target_row = {'kind': 'object', 'id': item['id'],
                      'name': item.get('name') or item['id']}
        template = _template(cfg, 'take', target_row)
        action_id = 'adventure:take:' + item['id']
        effects = [{'op': 'take', 'id': item['id']}]
        effects += [effect.model_dump() for effect in (template.effects if template else [])]
        label = _fill(template.label if template and template.label else DEFAULT_LABEL['take'],
                      target=target_row['name'])
        action = _action_dict(action_id, label, template, effects=effects,
                              requires=template.requires.compiled() if template else None)
        if not all((session.get('flags') or {}).get(k, False) == v
                   for k, v in (action.get('requires') or {}).items()):
            refused.append(_refusal(action_id, 'take', target_row, 'condition',
                                    _obstruction(template, DEFAULT_OBSTRUCTION['take'])))
            continue
        if not local_rules.affordable(session, story, action):
            refused.append(_refusal(action_id, 'take', target_row, 'resource',
                                    '拿不动：' + '、'.join(_shortfall(session, story, action))))
            continue
        duration, source = _duration_of(action, story, 'template')
        plans.append(_plan(action_id, 'take', target_row, label, action=action,
                           duration_hours=duration, duration_source=source,
                           extra={'source': 'world_item'}))
    return plans, refused


def _use(session, story, cfg):
    """使用：legacy 物品只在作者声明效果时才成方案；物品实例本版没有执行器。"""
    plans, refused = [], []
    held = list(session.get('inventory') or [])
    by_item = {item['id']: item for item in story.get('items') or []}
    for item_id in held:
        item = by_item.get(item_id)
        target_row = {'kind': 'object', 'id': item_id,
                      'name': (item or {}).get('name') or item_id}
        template = _template(cfg, 'use', target_row)
        if template is None or not template.effects:
            continue   # 没声明就没有「使用」：不做万能物品
        action_id = 'adventure:use:' + item_id
        effects = [effect.model_dump() for effect in template.effects]
        label = _fill(template.label if template.label else DEFAULT_LABEL['use'],
                      target=target_row['name'])
        action = _action_dict(action_id, label, template, effects=effects,
                              requires=template.requires.compiled())
        if not local_rules.affordable(session, story, action):
            refused.append(_refusal(action_id, 'use', target_row, 'resource',
                                    '暂时用不起：' + '、'.join(_shortfall(session, story, action))))
            continue
        duration, source = _duration_of(action, story, 'template')
        plans.append(_plan(action_id, 'use', target_row, label, action=action,
                           duration_hours=duration, duration_source=source,
                           extra={'source': 'legacy_inventory'}))
    instances = ((session.get('rewards') or {}).get('items') or [])[:MAX_INSTANCES]
    for instance in instances:
        if instance.get('owner') not in (None, 'player'):
            continue
        target_row = {'kind': 'object', 'id': instance['id'],
                      'name': instance.get('name') or instance['id']}
        # 实例效果没有执行器：这条只如实标注缺口，不生成任何 op。
        plans.append(_plan('adventure:use:' + instance['id'], 'use', target_row,
                           _fill(DEFAULT_LABEL['use'], target=target_row['name']),
                           action=None, duration_hours=0, duration_source='none',
                           supported=False, unsupported=['instance_effect'],
                           notes=['物品实例（rewards.items，含隐藏附魔等派生数值）没有使用执行器，'
                                  '待 p5；本版不输出虚构效果。'],
                           extra={'source': 'reward_instance'}))
    return plans, refused


def _give(session, story, cfg, characters):
    """转交：只对**作者点名的**「把某个世界物品交给某个人」出现，并如实标注缺口。

    模板的 target 是一个 ``story['items']`` 条目（运行时奖励实例 id 在声明期无法点名，
    所以实例转交本版不产生方案）；接收人必须是模板 ``recipients`` 里写下的角色，且此刻
    真的在场。因为没有任何转移执行器，方案一律 ``supported=False``、不含 op。
    """
    plans = []
    scene = {row['id']: row for row in _scene(session, story, characters)}
    if not scene:
        return plans, []
    held = set(session.get('inventory') or [])
    for template in cfg.templates:
        if template.kind != 'give' or template.target is None:
            continue
        item_id = template.target.id
        if item_id not in held:
            continue
        item = next((i for i in story.get('items') or [] if i['id'] == item_id), None)
        target_row = {'kind': 'object', 'id': item_id,
                      'name': (item or {}).get('name') or item_id}
        for npc_id in template.recipients:
            npc = scene.get(npc_id)
            if npc is None:
                continue
            label = _fill(template.label or DEFAULT_LABEL['give'],
                          target=target_row['name'], npc=npc['name'])
            plans.append(_plan(
                'adventure:give:%s:%s' % (item_id, npc_id), 'give', target_row, label,
                action=None, duration_hours=0, duration_source='none', supported=False,
                unsupported=['inventory_handover'],
                notes=['没有物品转移执行器（legacy inventory 与 rewards 实例都算），'
                       '待 p5 的物品转移执行器；本版不虚构交出的 op，物品不会真的易手。'],
                extra={'recipient': dict(npc), 'source': 'legacy_inventory'}))
    return plans, []


# ------------------------------------------------------------------- 对外入口
def scan(session, story, characters=None, rest_hours=None):
    """一次扫描：(合法方案, 公开阻碍)。纯函数：不写 session、不碰 store。

    公开这一层是给接线用的：Runtime 需要同时看到「合法方案」与「公开阻碍」才能给出
    可操作的提示（而不是死按钮）。
    """
    cfg = config(story)
    if cfg is None:
        return [], []
    place = _current_place(session, story)
    if place is None:
        return [], []
    plans, refused = [], []
    scene_place = {'kind': 'place', 'id': place['id'],
                   'name': place.get('name') or place['id']}

    for kind in ('observe', 'investigate'):
        if kind == 'observe':
            group = [clue for clue in cfg.clues
                     if clue.target.kind == 'place' and clue.target.id == place['id']
                     and 'observe' in clue.action_kinds]
            if group:
                plan, refusal = _reveal(kind, scene_place, group, session, story, cfg)
                if plan is not None:
                    plans.append(plan)
                if refusal is not None:
                    refused.append(refusal)
        else:
            for item in story.get('items') or []:
                if item.get('location_id') != place['id'] or not _perceivable(item, session):
                    continue
                group = [clue for clue in cfg.clues
                         if clue.target.kind == 'object' and clue.target.id == item['id']
                         and 'investigate' in clue.action_kinds]
                if not group:
                    continue
                target_row = {'kind': 'object', 'id': item['id'],
                              'name': item.get('name') or item['id']}
                plan, refusal = _reveal(kind, target_row, group, session, story, cfg)
                if plan is not None:
                    plans.append(plan)
                if refusal is not None:
                    refused.append(refusal)

    for kind in ('ask', 'negotiate'):
        found, blocked = _talk(kind, session, story, cfg, characters)
        plans.extend(found)
        refused.extend(blocked)

    found, blocked = _travel(session, story, cfg)
    plans.extend(found)
    refused.extend(blocked)

    hours = cfg.rest_hours if rest_hours is None else rest_hours
    plan, refusal = _rest(session, story, cfg, hours)
    if plan is not None:
        plans.append(plan)
    if refusal is not None:
        refused.append(refusal)

    for group in (_take(session, story, cfg), _use(session, story, cfg),
                  _give(session, story, cfg, characters)):
        plans.extend(group[0])
        refused.extend(group[1])

    done = set((session.get('active') or {}).get('actions_done') or [])
    plans = [p for p in plans if p['kind'] in REPEATABLE or p['action_id'] not in done]
    order = {kind: index for index, kind in enumerate(KINDS)}
    plans.sort(key=lambda p: (order[p['kind']], p['target']['id'] if p['target'] else '',
                              p['action_id']))
    return plans, refused


def build(session, story, characters=None, rest_hours=None):
    """当前所有**合法方案**（含 ``supported=False`` 的缺口标注）。

    ``characters`` 是包里的角色文档（``Runtime.package()['characters']``）；在场人物与
    人名都来自它。没有它时人物类方案为空，其余类照常。
    """
    return scan(session, story, characters, rest_hours)[0]


def refusals(session, story, characters=None, rest_hours=None):
    """玩家已知道、但当前被挡住的方案：只给作者写的公开阻碍或通用文本。"""
    return scan(session, story, characters, rest_hours)[1]


def describe(session, story, action_id, characters=None, rest_hours=None):
    """单个方案的完整内容（**作者/接线侧**：``action`` 里有 success_text，别给玩家看）。"""
    if not isinstance(action_id, str) or not action_id:
        raise ValueError('方案 ID 无效')
    plans, refused = scan(session, story, characters, rest_hours)
    plan = next((p for p in plans if p['action_id'] == action_id), None)
    if plan is None and action_id.startswith('adventure:rest:'):
        cfg = config(story)
        tail = action_id.rsplit(':', 1)[1]
        if cfg is not None and tail.isdigit():
            plan, _ = _rest(session, story, cfg, int(tail))
    if plan is None:
        hit = next((r for r in refused if r['action_id'] == action_id), None)
        if hit is not None:
            raise ValueError(hit['text'])
        raise ValueError('没有这个行动方案：' + action_id)
    return plan


def public(plan, story):
    """玩家可见的确认摘要：**白名单**字段，不含未发生的结果或任何隐藏文本。

    只放：动作 id/标签、公开目标、成本、时长（含时长来源）、检定、是否结束事件、
    作者公开的意图别名，以及本次是否 ``supported``、缺什么能力、旅行/等待的结构参数。
    ``success_text`` / ``failure_text`` / ``narrative_cues`` / 线索与分支的正文一律不出现。
    执行所需的完整 action definition 只在 :func:`describe` 里，归引擎内部。
    """
    if plan is None:
        return None
    view = free_actions.summarise(plan['action'], story) if plan.get('action') else {
        'action_id': plan['action_id'], 'label': plan['label'], 'costs': [],
        'duration_hours': plan['duration_hours'], 'check': None, 'ends_event': False,
        'intent_aliases': list(plan.get('intent_aliases') or [])}
    view = {key: view[key] for key in ('action_id', 'label', 'costs', 'duration_hours',
                                       'check', 'ends_event', 'intent_aliases')}
    view.update({'kind': plan['kind'], 'target': plan['target'],
                 'supported': plan['supported'],
                 'unsupported': list(plan['unsupported']),
                 'duration_source': plan['duration_source']})
    for key in ('travel', 'wait', 'source', 'recipient'):
        if plan.get(key) is not None:
            view[key] = plan[key]
    return view


def rest(session, story, hours=None):
    """任意小时（0..max_rest_hours）的休息方案；越界或不合法直接抛错。"""
    cfg = config(story)
    if cfg is None:
        raise ValueError('故事包没有声明 mechanics.%s，休息仍走既有 /wait' % MECHANICS_KEY)
    plan, refusal = _rest(session, story, cfg, cfg.rest_hours if hours is None else hours)
    if plan is None:
        raise ValueError(refusal['text'])
    return plan


def suggest(session, story, intent, characters=None, rest_hours=None):
    """把一句意图变成**至多 3 条**可执行方案；匹配规则直接复用 ``free_actions``。

    * 只匹配 ``supported`` 的方案：缺口方案能被 ``build`` 列出，但不会被推荐去执行。
    * 只用公开文本（``label`` + 作者公开的 ``intent_aliases``）匹配，与
      ``free_actions.suggest`` 同一套弱匹配；未配置的目标永远不出现。
    * **不签发确认凭据**：``free_actions.confirm_token`` 只认当前 ``node.actions`` 里的
      动作 id，动态方案集合尚未接进执行管线。所以这里如实回 ``confirm_state``，
      接线完成后由 Runtime 用**同一个** token 实现复用，本模块不另造凭据。
    """
    plans, refused = scan(session, story, characters, rest_hours)
    # 可推荐的 = 本模块能交给现有管线的：走 action 的动作，或带 travel/wait 结构参数的
    # 旅行/休息（由调用方交给 Runtime.move / /wait）。带缺口的方案不推荐。
    usable = [plan for plan in plans
              if plan['supported'] and (plan.get('action') or plan.get('travel')
                                        or plan.get('wait'))]
    if not usable:
        note = '当前没有可判定的行动目标；这句话只作为台词或描述，不改变状态'
        if refused:
            note += '。' + refused[0]['text']
        return {'matched': [], 'ambiguous': False, 'unjudged': True, 'note': note,
                'confirm_state': 'not_applicable'}
    text = intent if isinstance(intent, str) else ''
    negated = any(word in free_actions.normalize(text) for word in free_actions.NEGATIONS)
    stripped = text.replace('不', '').replace('没', '')
    scored = []
    for plan in usable:
        # 只看公开文本（标签 + 作者公开的意图别名）；与 free_actions 同一套匹配。
        probe = {'label': plan['label'],
                 'intent_aliases': list(plan.get('intent_aliases') or [])}
        value = free_actions.score(text, probe)
        hits = free_actions.alias_hits(text, probe)
        if value < free_actions.MIN_OVERLAP and not hits:
            continue
        if negated and (free_actions.score(stripped, probe) >= free_actions.MIN_OVERLAP
                        or free_actions.alias_hits(stripped, probe)):
            continue
        scored.append((value if value >= free_actions.MIN_OVERLAP else free_actions.MIN_OVERLAP,
                       plan))
    if not scored:
        return {'matched': [], 'ambiguous': False, 'unjudged': True,
                'note': '没有匹配到已配置的目标；引擎不裁定未声明的行动，'
                        '这句话只作为台词或描述，不改变状态',
                'confirm_state': 'not_applicable'}
    scored.sort(key=lambda row: (-row[0], row[1]['action_id']))
    best = scored[0][0]
    rows = []
    for value, plan in scored[:free_actions.MAX_CANDIDATES]:
        item = public(plan, story)
        item['match'] = value
        rows.append(item)
    top = [row for row in scored if row[0] == best]
    return {'matched': rows, 'ambiguous': len(top) > 1, 'unjudged': False,
            'confirm_state': 'pending_runtime_wiring',
            'note': ('候选只引用作者已声明的目标与效果，且不含未发生的结果。'
                     + NEED_WIRING_TEXT
                     + ('有多个同分候选，请自己挑一个。' if len(top) > 1 else ''))}
