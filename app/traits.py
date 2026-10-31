# -*- coding: utf-8 -*-
"""角色特质模板：复用百科命名空间与固定版本，但**只有一个权威、一份正文**。

四条边界（设计文档 §1 + 两轮预审）：

1. **单一正文来源**。``content_hash`` 只哈希 ``payload``；而 ``name`` / ``summary`` /
   ``details`` / ``tags`` 全部**从 payload 派生**，不信任与 payload 并列的外层字段。
   校验时逐字段比对（``_derive`` 与快照里存的值必须逐字相等），因此「改外层 details、
   保留原 payload」会被当场拒绝，而不是通过哈希却消费未认证的正文。
2. **不与元素清单形成双权威**。同一 ``namespace/element_id`` 若同时出现在
   ``mechanics.element_manifest``，两处必须同 ``version`` 且同 ``payload`` 哈希；
   读取路径只有一条 ``package_traits()``，不存在「这边读不到读那边」。
3. **不产出倾向分值**。``influence()`` 只给可观察的表达提示与「不能推出」的边界，
   因此不参与 ``prepare_turn`` 的 personality argmax，也不改写任何权重。
4. **投影按受众切开**。``public`` = 在场的人也能观察到；``hidden`` = 只有作者视图可见，
   且 ``aware`` 决定**角色本人**是否知道（默认 False，不自省）。
   「公开可观察」不等于「全世界都知道」：``context()`` 只给自视角与人物的当前视野内
   同场角色，绝不把远处人物的公开特质塞给 NPC。

临时情绪仍走 ``development.emotion`` + ``emotion_expires_after_turn``，与特质不合并。
"""
from __future__ import annotations

import hashlib
import json
import math
import re

MECHANICS_KEY = 'traits'
SCHEMA_VERSION = 1
NAMESPACE = 'character-traits'

# 进入模型上下文的硬上限。这些数字**不是**额外预算：``runtime.context`` 把它们算进
# 同一个 ``context_chars`` 总额，并走同一条 trim 路径。
CONTEXT_MAX_ENTRIES = 4
CONTEXT_MAX_CHARS = 900
MAX_PAYLOAD_CHARS = 30000

ID_RE = re.compile(r'^[a-z0-9][a-z0-9_.:-]*$')
MAX_TEMPLATES = 64
MAX_REFS = 6
MAX_PERSONAL_CHARS = 200
MAX_EVIDENCE = 4
MAX_EVIDENCE_CHARS = 60
MAX_NAME_CHARS = 60
MAX_SUMMARY_CHARS = 300
MAX_SECTION_CHARS = 1200
MAX_CUE_CHARS = 120
MAX_TAGS = 32
MAX_TAG_CHARS = 64

SECTIONS = ('definition', 'mechanism', 'conditions', 'exceptions',
            'story_uses', 'historical_scope', 'evidence_and_uncertainty')
VISIBILITIES = ('public', 'hidden')

# 快照里允许出现的外层键（全部由 payload 派生，多一个都拒绝）。
TEMPLATE_FIELDS = {'element_id', 'version', 'name', 'summary', 'details', 'tags',
                   'visibility', 'review_status', 'payload', 'payload_hash',
                   'sources'}
REF_FIELDS = {'template', 'version', 'visibility', 'personal', 'evidence', 'aware'}


class TraitError(ValueError):
    """所有拒绝都发生在写入之前；调用方失败时不留半套。"""


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def payload_hash(payload):
    return hashlib.sha256(_canonical(payload).encode('utf-8')).hexdigest()


def _check_json(value, path='$'):
    """与百科模块同一口径：只允许 dict/list/str/int/float/None，且拒绝 NaN/Infinity。"""
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TraitError('%s 的键必须是字符串（得到 %r）' % (path, key))
            _check_json(item, '%s.%s' % (path, key))
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _check_json(item, '%s[%d]' % (path, index))
        return
    if value is None or isinstance(value, (bool, int, str)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise TraitError('%s 是 NaN/Infinity，拒绝' % path)
        return
    raise TraitError('%s 的类型 %s 不允许' % (path, type(value).__name__))


def _text(value, label, limit, allow_empty=False):
    if not isinstance(value, str):
        raise TraitError('%s必须是文本' % label)
    text = value.strip()
    if not text and not allow_empty:
        raise TraitError('%s不能为空' % label)
    if len(text) > limit:
        raise TraitError('%s超过 %d 字上限（%d）' % (label, limit, len(text)))
    return text


def _check_id(value, label):
    if not isinstance(value, str) or not ID_RE.match(value) or len(value) > 96:
        raise TraitError('%s格式无效：%r' % (label, value))
    return value


def _strict_int(value, label, low, high):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TraitError('%s必须是整数（布尔值不算）' % label)
    if not low <= value <= high:
        raise TraitError('%s必须在 %d..%d（%r）' % (label, low, high, value))
    return value


# --------------------------------------------------------------------- 派生
def derive(payload):
    """**唯一**正文来源：从 payload 派生出快照里要用的字段。

    外层的 name / summary / details / tags 不是独立数据，而是这份派生的结果；
    校验时逐字段比对，所以篡改外层不会「绕过哈希」。
    """
    if not isinstance(payload, dict):
        raise TraitError('特质 payload 必须是对象')
    _check_json(payload)
    element_id = _check_id(payload.get('id'), '特质 payload 的 id')
    name = _text(payload.get('name'), '特质 payload 的 name', MAX_NAME_CHARS)
    details = payload.get('details')
    if not isinstance(details, dict):
        raise TraitError('特质 %s 的 payload 缺少 details' % element_id)
    extra = set(details) - set(SECTIONS)
    if extra:
        # 七节之外的分节一律拒绝：不让快照夹带隐藏字段。
        raise TraitError('特质 %s 的 details 含七节以外的分节：%s'
                         % (element_id, '、'.join(sorted(extra))))
    sections = {}
    for section in SECTIONS:
        sections[section] = _text(details.get(section),
                                  '特质 %s 的 %s' % (element_id, section),
                                  MAX_SECTION_CHARS)
    summary = payload.get('summary') or ''
    _text(summary, '特质 %s 的 summary' % element_id, MAX_SUMMARY_CHARS,
          allow_empty=True)
    tags = payload.get('tags') or []
    if not isinstance(tags, list) or len(tags) > MAX_TAGS:
        raise TraitError('特质 %s 的 tags 必须是最多 %d 项的列表'
                         % (element_id, MAX_TAGS))
    for tag in tags:
        _text(tag, '特质 %s 的 tag' % element_id, MAX_TAG_CHARS)
    aliases = payload.get('aliases') or []
    if not isinstance(aliases, list) or len(aliases) > MAX_TAGS:
        raise TraitError('特质 %s 的 aliases 无效' % element_id)
    status = payload.get('review_status') or 'needs_review'
    if status not in ('needs_review', 'reviewed_detail', 'reviewed'):
        raise TraitError('特质 %s 的 review_status 非法：%r' % (element_id, status))
    visibility = payload.get('visibility')
    if visibility is None:
        visibility = 'hidden' if 'trait.hidden' in tags else 'public'
    if visibility not in VISIBILITIES:
        raise TraitError('特质 %s 的 visibility 无效：%r' % (element_id, visibility))
    return {'element_id': element_id, 'name': name, 'summary': summary,
            'details': sections, 'tags': list(tags), 'aliases': list(aliases),
            'review_status': status, 'visibility': visibility}


def build_template(payload, version, sources=()):
    """把一条百科 payload 变成快照条目：先派生，再哈希，再回填校验。"""
    _strict_int(version, '特质模板版本', 1, 10 ** 6)
    if len(_canonical(payload)) > MAX_PAYLOAD_CHARS:
        raise TraitError('特质 payload 超过 %d 字符上限' % MAX_PAYLOAD_CHARS)
    derived = derive(payload)
    template = {'element_id': derived['element_id'], 'version': version,
                'name': derived['name'], 'summary': derived['summary'],
                'details': dict(derived['details']), 'tags': derived['tags'],
                'visibility': derived['visibility'],
                'review_status': derived['review_status'],
                'payload': payload, 'payload_hash': payload_hash(payload),
                'sources': [dict(item) for item in sources]}
    return template


def _validate_template(template):
    if not isinstance(template, dict):
        raise TraitError('特质模板必须是对象')
    unknown = set(template) - TEMPLATE_FIELDS
    if unknown:
        raise TraitError('特质模板有未知字段：' + '、'.join(sorted(unknown)))
    element_id = _check_id(template.get('element_id'), '特质模板 ID')
    _strict_int(template.get('version'), '特质模板版本', 1, 10 ** 6)
    payload = template.get('payload')
    if len(_canonical(payload)) > MAX_PAYLOAD_CHARS:
        raise TraitError('特质 %s 的 payload 超过 %d 字符上限'
                         % (element_id, MAX_PAYLOAD_CHARS))
    recorded = template.get('payload_hash')
    if not isinstance(recorded, str) or recorded != payload_hash(payload):
        raise TraitError('特质 %s 的 payload 与记录哈希不一致（被改过）' % element_id)
    derived = derive(payload)
    if derived['element_id'] != element_id:
        raise TraitError('特质模板 %s 的 payload id 是 %s'
                         % (element_id, derived['element_id']))
    # 逐字段比对：外层只要与 payload 不一致就拒绝，因此「改外层保留 payload」
    # 不可能通过哈希检查蒙混过去。
    for field in ('name', 'summary', 'details', 'tags', 'visibility', 'review_status'):
        if template.get(field) != derived[field]:
            raise TraitError('特质 %s 的外层 %s 与 payload 派生值不一致（被改过）'
                             % (element_id, field))
    sources = template.get('sources')
    if not isinstance(sources, list):
        raise TraitError('特质 %s 的 sources 必须是列表' % element_id)
    for source in sources:
        if not isinstance(source, dict) or set(source) - {'source_id', 'source_version'}:
            raise TraitError('特质 %s 的来源快照字段无效' % element_id)
        _check_id(source.get('source_id'), '特质来源 ID')
        _strict_int(source.get('source_version'), '特质来源版本', 1, 10 ** 6)
    if 'trait' not in derived['tags']:
        raise TraitError('特质 %s 缺少 trait 标签（分区标记）' % element_id)
    return template


# --------------------------------------------------------------------- 快照
def package_traits(story):
    """故事包里的特质快照；没有这个键就是 None（老包行为完全不变）。"""
    mechanics = (story or {}).get('mechanics') or {}
    if not isinstance(mechanics, dict):
        return None
    snapshot = mechanics.get(MECHANICS_KEY)
    if snapshot is None:
        return None
    if not isinstance(snapshot, dict):
        raise TraitError('mechanics.%s 必须是对象' % MECHANICS_KEY)
    return snapshot


def _validate_snapshot(snapshot):
    unknown = set(snapshot) - {'version', 'namespace', 'locked_note', 'templates'}
    if unknown:
        raise TraitError('特质快照有未知字段：' + '、'.join(sorted(unknown)))
    if isinstance(snapshot.get('version'), bool) or not isinstance(snapshot.get('version'), int):
        # ``True == 1`` in Python; a boolean is not a schema version.
        raise TraitError('特质快照版本必须是整数 %d（布尔与文本不接受）' % SCHEMA_VERSION)
    if snapshot.get('version') != SCHEMA_VERSION:
        raise TraitError('特质快照版本必须是 %d' % SCHEMA_VERSION)
    if snapshot.get('namespace') != NAMESPACE:
        raise TraitError('特质快照命名空间必须是 %s' % NAMESPACE)
    templates = snapshot.get('templates')
    if not isinstance(templates, list) or not templates:
        raise TraitError('特质快照缺少 templates')
    if len(templates) > MAX_TEMPLATES:
        raise TraitError('特质快照最多 %d 条' % MAX_TEMPLATES)
    seen = set()
    checked = []
    for template in templates:
        _validate_template(template)
        if template['element_id'] in seen:
            raise TraitError('特质模板重复：' + template['element_id'])
        seen.add(template['element_id'])
        checked.append(template)
    return checked


def index_of(templates):
    """快照索引：``character-traits/<id>`` → template。"""
    return {('%s/%s' % (NAMESPACE, t['element_id'])): t for t in templates}


def validate_package(story, characters=None):
    """包校验。返回 templates 列表，或 None（未配置）。"""
    snapshot = package_traits(story)
    if snapshot is None:
        return None
    templates = _validate_snapshot(snapshot)
    by_ref = index_of(templates)
    manifest = ((story or {}).get('mechanics') or {}).get('element_manifest')
    if isinstance(manifest, dict):
        for element in manifest.get('elements') or []:
            ref = element.get('ref')
            template = by_ref.get(ref)
            if template is None:
                continue
            if element.get('version') != template['version']:
                raise TraitError('特质 %s 在快照里是 v%s、在元素清单里是 v%s；'
                                 '两处必须同版本'
                                 % (ref, template['version'], element.get('version')))
            payload = element.get('payload')
            digest = payload_hash(payload) if isinstance(payload, dict) \
                else element.get('payload_hash')
            if digest != template['payload_hash']:
                raise TraitError('特质 %s 在快照与元素清单里的 payload 哈希不一致' % ref)
    if characters is not None:
        for character in characters.get('characters') or []:
            validate_character(character, story)
    return templates


# ---------------------------------------------------------------- 角色引用
def validate_character(character, story):
    """校验一个角色的 ``trait_refs``；缺这个键就是 None（旧包不变）。"""
    refs = character.get('trait_refs')
    if refs is None:
        return None
    if not isinstance(refs, list) or not refs:
        raise TraitError('角色的 trait_refs 必须是非空列表（不用特质请省略该键）')
    if len(refs) > MAX_REFS:
        raise TraitError('一个角色最多 %d 条特质' % MAX_REFS)
    templates = package_traits(story)
    index = index_of(_validate_snapshot(templates)) if templates is not None else {}
    seen = set()
    prepared = []
    for raw in refs:
        if not isinstance(raw, dict):
            raise TraitError('特质引用必须是对象')
        unknown = set(raw) - REF_FIELDS
        if unknown:
            raise TraitError('特质引用有未知字段：' + '、'.join(sorted(unknown)))
        ref = _text(raw.get('template'), '特质引用 template', 96)
        if not ID_RE.match(ref):
            raise TraitError('特质引用格式无效：%r' % ref)
        if ref in seen:
            raise TraitError('同一角色重复引用同一特质：' + ref)
        seen.add(ref)
        version = _strict_int(raw.get('version'), '特质引用版本', 1, 10 ** 6)
        visibility = raw.get('visibility', 'public')
        if visibility not in VISIBILITIES:
            raise TraitError('特质引用 visibility 只能是 public 或 hidden')
        personal = _text(raw.get('personal'), '特质引用的个人化解释', MAX_PERSONAL_CHARS)
        evidence = raw.get('evidence') or []
        if not isinstance(evidence, list) or len(evidence) > MAX_EVIDENCE:
            raise TraitError('特质引用 evidence 必须是最多 %d 项的列表' % MAX_EVIDENCE)
        evidence = [_text(item, '特质引用 evidence 条目', MAX_EVIDENCE_CHARS)
                    for item in evidence]
        aware = raw.get('aware', False)
        if not isinstance(aware, bool):
            raise TraitError('特质引用 aware 必须是 true/false')
        if visibility == 'public':
            # 公开特质默认谁都能观察到，不需要「自知」开关；写了只会制造歧义。
            if 'aware' in raw and aware is False:
                raise TraitError('公开特质不需要 aware=false；要隐藏请用 visibility=hidden')
        template = index.get('%s/%s' % (NAMESPACE, ref))
        if templates is not None and template is None:
            raise TraitError('特质引用 %s 不在本故事包的特质快照里' % ref)
        if template is not None:
            if template['version'] != version:
                raise TraitError('特质引用 %s 固定 v%d，快照里是 v%d'
                                 % (ref, version, template['version']))
            if template['visibility'] == 'hidden' and visibility != 'hidden':
                # 模板本身是隐藏的，角色却按公开引用：拒绝，避免一条 hiddentag
                # 因为在角色包里写成 public 就泄进玩家视图。
                raise TraitError('特质 %s 在快照里是 hidden，角色引用不能写成 public'
                                 % ref)
        prepared.append({'template': ref, 'namespace': NAMESPACE, 'version': version,
                         'visibility': visibility, 'personal': personal,
                         'evidence': evidence,
                         # 隐藏且不自知：连角色自己的模型上下文都不含它。
                         'aware': True if visibility == 'public' else aware})
    return prepared


# --------------------------------------------------------------- 影响/边界
def influence(template, personal=''):
    """把一条模板压成表达提示 + 边界。**刻意不返回任何分值。**

    没有权重、没有倾向强度、没有排序，因此它无法参与 ``prepare_turn`` 的 argmax。
    """
    details = template.get('details') or {}
    def clip(value):
        text = details.get(value) or ''
        return text if len(text) <= MAX_CUE_CHARS else text[:MAX_CUE_CHARS]
    return {'name': template.get('name', ''), 'cue': clip('mechanism') or clip('definition'),
            'boundary': clip('exceptions'), 'when': clip('conditions'),
            'personal': personal,
            'rules': '特质只解释可观察的表达，不改变检定、不授予能力或物品，'
                     '也不参与 personality 权重排序'}


def _templates_of(story):
    templates = package_traits(story)
    return [] if templates is None else _validate_snapshot(templates)


def _refs_of(character):
    return [r for r in (character.get('trait_refs') or []) if isinstance(r, dict)]


def _visible_refs(character, audience):
    """按受众过滤引用。

    * ``audience == 'player'``：只给 public（玩家看不到隐藏特质）。
    * 某个角色看**自己**（``audience`` 就是这个人物的 id）：public + 他自己 ``aware`` 的
      hidden。
    * 某个角色看**别人**：只给对方的 public。别人的隐藏特质（哪怕对方自知）不进这一视角，
      否则一个 NPC 就能读到另一个 NPC 的隐藏设定。
    """
    own = audience != 'player' and audience == character.get('id')
    rows = []
    for ref in _refs_of(character):
        if ref.get('visibility', 'public') == 'public':
            rows.append(ref)
        elif own and ref.get('aware'):
            rows.append(ref)
    return rows


def projections(story, character, audience, visible_only=True):
    """一个角色被某个受众看到的特质摘要。

    ``visible_only`` 仅影响 hidden 引用的取舍（见 ``_visible_refs``）；
    public 引用一律保留，因为它是「可被观察到」的，不是「全世界已知」。
    """
    if character is None:
        return []
    templates = index_of(_templates_of(story))
    rows = []
    for ref in _visible_refs(character, audience):
        template = templates.get(ref['template'] if '/' in ref['template']
                                 else '%s/%s' % (NAMESPACE, ref['template']))
        if template is None:
            continue
        rows.append({'template': '%s/%s' % (NAMESPACE, template['element_id']),
                     'version': ref['version'],
                     'visibility': ref.get('visibility', 'public'),
                     'name': template['name'],
                     'personal': ref.get('personal', ''),
                     'summary': template.get('summary', '')})
    return rows


def present_characters(session, characters, audience):
    """谁的特质此刻可能被这个受众观察到。

    「公开可观察」不等于「全世界都知道」：只有与受众同处一地、且在作者声明为
    可被观察范围内的角色才进上下文。玩家视角看自己一人；NPC 视角看自己 +
    同地点的其他角色。远处人物的公开特质不会被塞进模型上下文。
    """
    by_id = {c['id']: c for c in (characters or {}).get('characters', [])}
    hero = session.get('hero')
    states = session.get('characters') or {}
    if audience == 'player':
        return [by_id[hero]] if hero in by_id else []
    location = (states.get(audience) or {}).get('location') or session.get('location')
    rows = []
    for character_id, state in states.items():
        character = by_id.get(character_id)
        if character is None or state.get('location') != location:
            continue
        rows.append(character)
    return sorted(rows, key=lambda c: c['id'])


def context(story, session, audience, budget=None, characters=None):
    """进入模型上下文的有界摘要；没有可见特质时返回 None（prompt 一字不变）。

    * 只包含「此刻可能被观察到」的角色（见 ``present_characters``）。
    * 预算由调用方从**同一个** ``context_chars`` 余额里扣；超限整条丢弃、绝不切片。
    """
    # ``characters`` is the assembled character package; ``story`` alone does not carry
    # the roster. Callers inside Runtime pass it explicitly.
    roster = characters if characters is not None else story.get('characters')
    heroes = present_characters(session, roster, audience)
    if not heroes:
        return None
    templates = index_of(_templates_of(story))
    items = []
    for character in heroes:
        refs = _visible_refs(character, audience)
        if character['id'] == session.get('hero') and session.get('hero_traits'):
            # 玩家自己的特质可能来自起点追加，读旅程快照而不是角色包；没有起点追加时
            # 仍然读角色包里那条引用（否则包内声明的主角特质会被这条分支吞掉）。
            refs = [r for r in (session.get('hero_traits') or [])
                    if r.get('visibility', 'public') == 'public']
        for ref in refs:
            if len(items) >= CONTEXT_MAX_ENTRIES:
                break
            key = ref['template'] if '/' in ref['template'] \
                else '%s/%s' % (NAMESPACE, ref['template'])
            template = templates.get(key)
            if template is None:
                continue
            shaped = influence(template, ref.get('personal', ''))
            entry = {'who': character.get('public_name') or character['name'],
                     'name': shaped['name'], 'cue': shaped['cue'],
                     'boundary': shaped['boundary']}
            if shaped['when']:
                entry['when'] = shaped['when']
            if shaped['personal']:
                entry['personal'] = shaped['personal']
            items.append(entry)
    if not items:
        return None
    payload = {'basis': '特质是作者为本世界写的行为解释，不是数值、不是心理学结论；'
                        '只说明大概会怎么表达，不能推出道德、能力或秘密；'
                        '只列出此刻同一地点可能被观察到的人',
               'items': items}
    while items and len(json.dumps(payload, ensure_ascii=False)) > CONTEXT_MAX_CHARS:
        items.pop()
        payload['items'] = items
    if budget is not None:
        while items and len(json.dumps(payload, ensure_ascii=False)) > budget:
            items.pop()
            payload['items'] = items
    return payload if items else None


# ------------------------------------------------------------------ 库侧助手
def snapshot_from_library(library, refs, note=''):
    """从百科库把若干 ``(element_id, version)`` 锁成包内快照。

    只由作者侧构建脚本调用；运行期**从不**读库。
    """
    templates = []
    for element_id, version in refs:
        detail = library.get(NAMESPACE, element_id, version=version)
        payload = detail.get('payload')
        if not isinstance(payload, dict):
            raise TraitError('库返回的特质 %s 没有 payload' % element_id)
        if payload.get('id') != element_id:
            raise TraitError('库返回的 payload id 与请求不一致：%s' % element_id)
        sources = [{'source_id': s.get('source_id'),
                    'source_version': s.get('source_version')}
                   for s in (detail.get('sources') or [])]
        templates.append(build_template(payload, version, sources))
    snapshot = {'version': SCHEMA_VERSION, 'namespace': NAMESPACE,
                'locked_note': note or '特质模板快照：运行期只读，不查库',
                'templates': templates}
    _validate_snapshot(snapshot)
    return snapshot
