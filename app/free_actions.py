# -*- coding: utf-8 -*-
"""自由行动：把「我想……」变成**有界结构化候选**，由玩家确认后才执行。

三条边界（设计文档 §4 + 首轮审查意见 5）：

1. **只建议、不执行**。``suggest()`` 是纯函数：不写库、不保存 pending、不生成标记。
   GET/POST 都不会因为「问了一句」而改变 ``state_version``。
2. **有最低阀值、停用字、否定与歧义**。匹配只看**公开文本**（`label` + 作者声明的
   `intent_aliases`），绝不用成功/失败描述或叙事线索。字符重叠要同时满足：
   * 归一化后的有效字符达到 ``MIN_OVERLAP``（或原句包含整条公开别名）；
   * 命中至少一个**实义** token（常见汉字/虚词被停用，避免「我不去开闸」
     因为「开闸」两个字重叠就被推荐去开闸）；
   * 意图里出现否定词时，**同一动作**若被否定则不推荐（「不去开闸」不推荐「开闸」）；
   * 多个候选分数并列时返回 ``ambiguous=True``，让玩家自己挑，不代为排序。
3. **不把自然语言变 effect**。候选只引用**已声明**的 action；``intent`` 文本永远
   不会进入 effects、不会生成标记、不会授予物品或法术。

执行仍走既有 ``/chat`` + ``action_id``；``confirm`` 是 CAS 凭据：
``seed`` + ``state_version`` + 事件分支键 + ``action_id`` + 成本/时长摘要 一起哈希。
任何一处不符（凭据过期、成本变了、动作已执行、前置不再满足）都在 ``charge`` /
``communicate`` / ``effects`` **之前**拒绝。
"""
from __future__ import annotations

import hashlib
import json
import re

from . import local_rules

MAX_CANDIDATES = 3
MIN_OVERLAP = 2
MIN_TOKEN_CHARS = 2
MAX_INTENT_ALIASES = 6
MAX_INTENT_ALIAS_CHARS = 30

# 常见汉字与虚词停用：这些字出现在任何句子里都不构成「想做这个动作」的证据。
STOP_CHARS = set('的一了是我你他她它们在和有就不都也很到说要去这那些什么么呢吧啊呀吗'
                 '把被给对从向为以并且或者但而且还再就又才刚已经可会能得着过个某些'
                 '个人上下来去回里外前后中间时候点多少几怎样如何为什么这样那样'
                 '请帮我你想他她它咱们我们你们他们别人大家自己')
STOP_TOKENS = ('一下', '一个', '那个', '这个', '他们', '我们', '什么', '怎么',
               '可以', '应该', '是不是', '有没有', '要不要', '能不能')
NEGATIONS = ('不', '没', '别', '勿', '拒绝', '不去', '不想', '不要', '算了', '不必')


def normalize(text):
    """NFKC + 去空白 + 小写；只用于匹配，不改变原文本。"""
    if not isinstance(text, str):
        return ''
    return re.sub(r'\s+', '', text.strip().lower())


def tokens(text):
    """把文本切成语义上可用的字符/词，掉停用字与重复。"""
    text = normalize(text)
    kept = [ch for ch in text if ch not in STOP_CHARS]
    rows = []
    for size in (3, 2):
        for start in range(0, max(0, len(kept) - size + 1)):
            chunk = ''.join(kept[start:start + size])
            if len(chunk) == size and chunk not in rows and chunk not in STOP_TOKENS:
                rows.append(chunk)
    return rows


def _has_negation(text):
    text = normalize(text)
    return any(word in text for word in NEGATIONS)


def _match_text(action):
    """**只**用玩家本来就能看到的文本做匹配：标签 + 作者公开的意图别名。

    成功/失败描述与 `narrative_cues` 是**未发生的结果**与作者隐藏提示，
    把它们算进匹配，等于让玩家拿毒词探一探就能问出隐成结局；
    所以候选能显示的、能匹配的，都只限这一份公开文本（作者层仍完整保留）。
    """
    parts = [action.get('label', '')]
    parts.extend(action.get('intent_aliases') or [])
    return ' '.join(part for part in parts if part)


def score(intent, action):
    """确定性匹配分：实义 token 的重叠数量。

    不用余弦、不用词向量——字符重叠是刻意选的弱匹配，宁可漏，也不猜。
    """
    wanted = set(tokens(intent))
    have = set(tokens(_match_text(action)))
    if not wanted or not have:
        return 0
    return len(wanted & have)


def _costs_of(action, story):
    """把成本翻成可读文本：资源名 + 数量；同时保留原始 map 供 CAS。"""
    resources = {r['id']: r for r in
                 ((story.get('mechanics') or {}).get('local') or {}).get('resources') or []}
    rows = []
    for resource_id, amount in sorted((action.get('costs') or {}).items()):
        spec = resources.get(resource_id)
        rows.append({'id': resource_id, 'name': spec.get('name', resource_id)
                     if spec else resource_id, 'amount': amount,
                     'unit': (spec or {}).get('unit', '')})
    return rows


def effective_duration(action, story):
    """动作真正会推进的小时数：**按键是否存在**取默认，不用 `or`。

    `duration_hours: 0` 是合法的「瞬时动作」，`0 or cfg.turn_hours` 会把它
    错误地改成默认时长；缺键才落回 `mechanics.local.turn_hours`，与
    `Runtime.prepare_turn` 的 `action.get('duration_hours', cfg.turn_hours)` 语义一致。
    """
    if 'duration_hours' in action:
        return action['duration_hours']
    return local_rules.rules(story).turn_hours


def summarise(action, story):
    """候选的**公开**摘要（玩家确认的就是这一份，也是唯一进候选的字段集）。

    未发生的结果（`success_text` / `failure_text`）与作者隐藏提示（`narrative_cues`）
    一律不在这里出现；它们只在真正执行后由 narrate 分支呈现。
    """
    check = action.get('check') or None
    aliases = [item for item in (action.get('intent_aliases') or []) if item]
    result = {'action_id': action['id'], 'label': action.get('label', action['id']),
            'costs': _costs_of(action, story),
            'duration_hours': effective_duration(action, story),
            'check': ({'attribute': check.get('attribute'),
                       'difficulty': check.get('difficulty')} if check else None),
            'ends_event': bool(action.get('ends_event')),
            'intent_aliases': aliases}
    if action.get('risk_notice'):
        result['risk_notice'] = action['risk_notice']
    return result


def confirm_token(session, node, action, story):
    """确认凭据：把「这一次、这个事件、这个动作、这份成本」绑在一起。

    包含 ``state_version``，所以任何状态推进都会让旧凭据失效（CAS）。
    只哈希公开信息：成本、**有效时长**、完整的检定（属性 + 难度）；
    所以「同难度换了属性」或「0 小时 ↔ 缺省」都会让旧凭据失效。
    """
    check = action.get('check') or {}
    payload = {'session': session.get('id', ''),
               'revision': session.get('revision', ''),
               'seed': session.get('seed', ''),
               'version': session.get('state_version', 0),
               'branch': (session.get('active') or {}).get('key', ''),
               # 没有进行中的事件时（空白地点上的动态方案）节点位为空串：凭据仍然绑定
               # session / version / 动作 / 成本 / 时长 / 检定，CAS 语义不变。
               'node': (node or {}).get('id', ''),
               'action': action['id'],
               'costs': sorted((action.get('costs') or {}).items()),
               'duration': effective_duration(action, story),
               'check': {'attribute': check.get('attribute'),
                         'difficulty': check.get('difficulty')} if check else None}
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:32]


def validate_action_aliases(action):
    """作者声明的意图别名：**公开**文本，有界、去重、非空。

    它会被返回给玩家（候选里可见）并参与匹配，所以不能写隐成内容；
    这里只保证形状，不替作者判断该不该公开。
    """
    aliases = action.get('intent_aliases')
    if aliases is None:
        return []
    if not isinstance(aliases, list):
        raise ValueError('动作 %s 的 intent_aliases 必须是列表' % action.get('id'))
    if len(aliases) > MAX_INTENT_ALIASES:
        raise ValueError('动作 %s 的 intent_aliases 最多 %d 条'
                         % (action.get('id'), MAX_INTENT_ALIASES))
    seen = set()
    cleaned = []
    for item in aliases:
        if not isinstance(item, str):
            raise ValueError('动作 %s 的意图别名必须是文本' % action.get('id'))
        text = item.strip()
        if not text or len(text) > MAX_INTENT_ALIAS_CHARS:
            raise ValueError('动作 %s 的意图别名必须是 1..%d 字'
                             % (action.get('id'), MAX_INTENT_ALIAS_CHARS))
        if text in seen:
            raise ValueError('动作 %s 的意图别名重复：%s' % (action.get('id'), text))
        seen.add(text)
        cleaned.append(text)
    return cleaned


def available(session, story, node):
    """当前可用的动作：未执行、前置满足、资源付得起。

    与 ``Runtime.surface`` 用同一套判断，因此界面上的按钮与这里永远一致。
    """
    from . import local_rules
    done = (session.get('active') or {}).get('actions_done') or []
    flags = session.get('flags') or {}
    rows = []
    # ``node`` 可以为 None（没有进行中的事件）：那时没有静态动作可列。
    for action in (node or {}).get('actions') or []:
        if action['id'] in done:
            continue
        if not all(flags.get(k, False) == v for k, v in (action.get('requires') or {}).items()):
            continue
        if not local_rules.affordable(session, story, action):
            continue
        rows.append(action)
    return rows


def dynamic_actions(plans):
    """动态方案里**可执行**的 action（带 action 且 supported）。"""
    return [plan['action'] for plan in (plans or [])
            if plan.get('supported') and plan.get('action')]


def adventure_plans(session, story, characters=None, plans=None):
    """运行时方案：给了就用，没给则**现算**（纯函数，不写库）。

    这里自动现算，是为了让既有的 ``/intent`` ``/confirm/{id}`` 调用点（它们只传
    session/story/node）不用改就能拿到动态候选；包没声明 ``mechanics.adventure`` 时
    返回空列表，老包的产物一字不变。``characters`` 只影响人物类方案（询问/交涉），
    不传时这些类不出现，其余类照常。
    """
    if plans is not None:
        return list(plans)
    from . import adventure_actions
    if adventure_actions.config(story) is None:
        return []
    return adventure_actions.build(session, story, characters)


def available_with(session, story, node, plans=None, characters=None):
    """静态可用动作 + 动态可用动作；**静态命名空间优先**。

    静态 ``node['actions']`` 里出现过的 id 整个占住该命名空间，同名动态方案直接丢弃：
    作者写死的动作永远不会被运行时方案盖掉（新机制包里的 ``adventure:`` 前缀另由
    ``adventure_actions.validate`` 在打包时拦住，这里是防御性的一道）。
    """
    rows = list(available(session, story, node))
    dynamic = dynamic_actions(adventure_plans(session, story, characters, plans))
    if not dynamic:
        return rows
    taken = {a['id'] for a in (node or {}).get('actions') or []}
    done = (session.get('active') or {}).get('actions_done') or []
    flags = session.get('flags') or {}
    for action in dynamic:
        if action['id'] in taken or action['id'] in done:
            continue
        if not all(flags.get(k, False) == v for k, v in (action.get('requires') or {}).items()):
            continue
        if not local_rules.affordable(session, story, action):
            continue
        rows.append(action)
    return rows


def alias_hits(intent, action):
    """意图里**原句包含**的作者公开别名。

    别名是作者显式声明的短语（如「放水」），不像字符重叠那样容易误命中，
    所以只要原句包含整条别名，就当作达到阀值；它仍然只看公开文本。
    """
    text = normalize(intent)
    hits = []
    for alias in action.get('intent_aliases') or []:
        target = normalize(alias)
        if target and target in text:
            hits.append(alias)
    return hits


def suggest(session, story, node, intent, plans=None, characters=None):
    """把意图变成**至多 3 条**结构化候选。纯函数：不写库、不保存 pending。

    ``plans`` / ``characters`` 可选：不传时若包声明了 ``mechanics.adventure``，本函数
    会**现算**一份运行时方案（见 :func:`adventure_plans`）；没有人物文档时询问/交涉
    这两类不出现（它们需要作者角色文档才能给出人名与在场判断）。

    返回结构：
    ``{'matched': [...], 'ambiguous': bool, 'unjudged': bool, 'note': '...'}``
    """
    actions = available_with(session, story, node, plans, characters)
    if not actions:
        return {'matched': [], 'ambiguous': False, 'unjudged': True,
                'note': '此刻没有引擎可以替你执行的动作；这句话只会作为对话或描述'}
    negated = _has_negation(intent)
    stripped = intent.replace('不', '').replace('没', '')
    scored = []
    for action in actions:
        value = score(intent, action)
        hits = alias_hits(intent, action)
        if value < MIN_OVERLAP and not hits:
            continue
        if negated and (score(stripped, action) >= MIN_OVERLAP
                        or alias_hits(stripped, action)):
            # 「不去开闸」这类否定在原句里也命中同一动作：不推荐，明确跳过。
            continue
        rank = value if value >= MIN_OVERLAP else MIN_OVERLAP
        scored.append((rank, action))
    if not scored:
        return {'matched': [], 'ambiguous': False, 'unjudged': True,
                'note': '没有匹配到已配置的动作；引擎不裁定未配置的行动，'
                        '这句话只作为台词或描述，不改变状态'}
    scored.sort(key=lambda row: (-row[0], row[1]['id']))
    best = scored[0][0]
    top = [(value, action) for value, action in scored if value == best]
    rows = []
    for value, action in scored[:MAX_CANDIDATES]:
        item = summarise(action, story)
        item['confirm'] = confirm_token(session, node, action, story)
        item['match'] = value
        rows.append(item)
    return {'matched': rows, 'ambiguous': len(top) > 1 and len(top) > 0,
            'unjudged': False,
            'note': ('候选按已配置动作的字符重叠（含作者公开别名整条命中）排序；'
                     '这是弱匹配，不是语义理解。确认具体动作与成本后才会执行。'
                     + ('有多个同分候选，请自己挑一个。' if len(top) > 1 else ''))}


def resolve_action(session, story, node, action_id, plans=None, characters=None):
    """按 id 取动作：**先静态、后动态**。找不到返回 ``None``。

    静态动作只要 id 对得上就返回（即使已执行或暂时条件不足），因为调用方需要的是
    「这个 id 属于谁」而不是「能不能用」；能不能用由 ``describe`` / ``verify`` 判。
    """
    # ``node`` 可以为 None（没有进行中的事件时只有本地行动）：那时没有静态命名空间。
    action = next((a for a in (node or {}).get('actions') or [] if a['id'] == action_id), None)
    if action is not None:
        return action
    for plan in adventure_plans(session, story, characters, plans):
        if plan.get('supported') and plan.get('action') \
                and plan['action']['id'] == action_id:
            return plan['action']
    return None


def dynamic_plan(session, story, action_id, plans=None, characters=None):
    """取**当前算出的**动态方案（含 supported / unsupported / travel 参数）。"""
    for plan in adventure_plans(session, story, characters, plans):
        if plan.get('action_id') == action_id:
            return plan
    return None


def describe(session, story, node, action_id, plans=None, characters=None):
    """单个动作的确认摘要（GET 用，只读）。动作不可用时报错并说明缺什么。

    静态与动态两个命名空间都支持；凭据同一个 ``confirm_token``（CAS 靠 state_version）。
    """
    done = (session.get('active') or {}).get('actions_done') or []
    from . import local_rules
    flags = session.get('flags') or {}
    action = resolve_action(session, story, node, action_id, plans, characters)
    if action is None:
        raise ValueError('动作不存在：' + action_id)
    if action_id in done:
        raise ValueError('这个动作已经执行过')
    missing = {k: v for k, v in (action.get('requires') or {}).items()
               if flags.get(k, False) != v}
    if missing:
        raise ValueError('这个动作的前置标记还没满足：' + '、'.join(sorted(missing)))
    if not local_rules.affordable(session, story, action):
        short = [spec['name'] for spec in _costs_of(action, story)
                 if int(((session.get('local') or {}).get('resources') or {})
                        .get(spec['id'], 0)) < spec['amount']]
        raise ValueError('资源不够，缺：' + '、'.join(short))
    item = summarise(action, story)
    item['confirm'] = confirm_token(session, node, action, story)
    return item


def verify(session, story, node, action_id, token, plans=None, characters=None):
    """执行前核对确认凭据。任何不符都在副作用之前抛错。

    静态与动态动作共用同一个凭据算法；动态动作**必须**带凭据（由 Runtime 强制），
    静态动作不传凭据时保持旧的直接按钮行为（由 ``Runtime`` 决定传不传）。
    """
    if not isinstance(token, str) or not token:
        raise ValueError('确认凭据无效')
    action = resolve_action(session, story, node, action_id, plans, characters)
    if action is None:
        raise ValueError('动作不存在：' + action_id)
    expected = confirm_token(session, node, action, story)
    if token != expected:
        raise ValueError('确认已过期或与当前动作/成本不符，请重新确认后执行')
    return action
