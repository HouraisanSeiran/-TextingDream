# -*- coding: utf-8 -*-
"""AI 草稿：按玩家给的名字、标签和大概方向补全元素 / NPC 角色卡 / 故事包。

规则（用户拍板，见 ``docs/ai-drafts-使用说明.md``）：

1. 生成结果**一律只存为草稿**（Store 文档 ``kind='ai_draft'``）。游戏进行中也能生成，
   但本模块**从不**改当前故事包的 ``story.mechanics.element_manifest``，也不改运行中的
   NPC 绑定：旅程只读自己绑定的包版本。
2. 草稿必须经作者**显式确认**才进库（元素）或成为新卡版本（NPC）；也可以拒绝。
3. 强制口径由代码覆盖，不信任模型：元素一律 ``evidence_grade='inferred'``、``source_ids=[]``、
   不带 sources、``review_status='needs_review'``、``detail_status='needs_detail'``，
   id 由代码生成（``player_`` 前缀），命名空间 / 组为 ``player-created``。
4. 校验失败把错误回传模型重试一次；仍失败整体拒绝，**零写入**（不存草稿、不写库）。

故事包入口只是 ``world_generator.generate`` 的薄封装，草稿 → 校验 → 发布仍走它自己的流程。
"""
from __future__ import annotations

import copy
import re
from typing import Literal

from pydantic import Field, ValidationError

from . import encyclopedia as enc
from . import npc_cards
from .contracts import Strict
from .runtime import now, uid
from .token_budget import output_tokens
from tools import catalog_overlay, game_fields

NAMESPACE = 'player-created'
KIND = 'ai_draft'
CONFIRMED_KIND = 'ai_confirmed_element'
ID_PREFIX = 'player_'
ORIGIN_TAG = 'origin:ai_player_draft'
EVIDENCE_NOTICE = '本条由 AI 按玩家方向生成，为设定推演，未经来源核实。'
DOCUMENT_META = {
    'schema_version': 1,
    'group': NAMESPACE,
    'status': 'candidate',
    'note': '玩家经 AI 草稿生成、作者显式确认的设定推演条目；evidence 一律 inferred，'
            '没有来源，不代表事实已核实。',
}
MAX_ATTEMPTS = 2
ELEMENT_TOKENS = output_tokens('ai_draft_element')
NPC_TOKENS = output_tokens('ai_draft_npc')
MAX_SUMMARY = 600
MAX_SECTION = 3000
MEDICINAL = ('medicinal_herb', 'medicinal_mineral', 'medicinal_animal', 'formula')
MEDICINAL_WORDS = ('剂量', '用量', '服用', '内服', '外敷', '外用', '煎服', '每日', '疗程',
                   '主治', '治疗', '疗效', '功效', '药效', '可治', '治愈', '治病', '处方')
MEDICINAL_AMOUNT = re.compile(r'\d+(\.\d+)?\s*(克|钱|两|毫升|毫克|g|mg|ml)', re.IGNORECASE)
GAME_PREFIXES = game_fields.TAG_PREFIXES
WITNESS_WORDS = ('亲眼', '亲见', '目睹', '亲自看到', '亲眼看见')
AI_NOTICE = 'AI 推演、未核实：确认前不进库、不进任何故事包，也不影响正在进行的旅程。'


class DraftRejected(ValueError):
    """两次尝试都没通过校验：整体拒绝，什么都没写。"""

    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__('AI 草稿两次都未通过校验，已整体拒绝、未写入任何内容：'
                         + '；'.join(self.errors[:8]))


# --------------------------------------------------------------------- 请求
Tag = Field(min_length=1, max_length=40)


class ElementDraftRequest(Strict):
    name: str = Field(min_length=1, max_length=80)
    tags: list[str] = Field(default_factory=list, max_length=16)
    direction: str = Field(default='', max_length=500)
    primary: str | None = Field(default=None, max_length=64)
    tradition: str | None = Field(default=None, max_length=40)


class NPCDraftRequest(Strict):
    name: str = Field(min_length=1, max_length=80)
    tags: list[str] = Field(default_factory=list, max_length=16)
    direction: str = Field(default='', max_length=300)
    character_id: str | None = Field(default=None, max_length=80)
    location_id: str | None = Field(default=None, max_length=80)


class StoryDraftRequest(Strict):
    title: str | None = Field(default=None, max_length=80)
    tags: list[str] = Field(default_factory=list, max_length=16)
    direction: str = Field(min_length=1, max_length=2000)
    kind: Literal['worldview', 'complete'] = 'worldview'
    historical_reference: str = Field(default='', max_length=500)
    city_count: int = Field(default=3, ge=2, le=5)
    output_tokens: int = Field(default=output_tokens('generator_world'), ge=1500, le=8192)


class DraftEdit(Strict):
    revision: int = Field(ge=1, strict=True)
    content: dict


class DraftDecision(Strict):
    revision: int | None = Field(default=None, ge=1, strict=True)
    # NPC 确认才用：挂到哪个 NPC、基于哪个故事包版本（与现有角色卡保存同一口径）。
    character_id: str | None = Field(default=None, max_length=80)
    package_revision: str | None = Field(default=None, max_length=80)


def _clean_tags(tags):
    out = []
    for tag in tags:
        text = str(tag).strip()
        if not text or len(text) > 40:
            raise ValueError('每个标签需为 1–40 字')
        if text not in out:
            out.append(text)
    return out


# ----------------------------------------------------------------- 提示词
ELEMENT_SYSTEM = """织梦·玩家元素草稿协议 v1
只输出一个 JSON 对象，不输出 Markdown 或推理。按 request 的名字、标签和方向，补全一个设定元素草稿。
字段：summary（一两句）、aliases（字符串数组，可空）、primary（必须是 vocab.primary 的一个键）、tags（次标签数组）、game（见 vocab 与 example）、details（七节 definition、mechanism、conditions、exceptions、story_uses、historical_scope、evidence_and_uncertainty，每节都是非空中文段落）。
tags 每个都是小写英文 snake_case，可含冒号，例如 kind:dish、tradition:western、theme:fire；至少一个 kind: 标签。玩家标签多为中文自然词：能对应规范标签的写成英文标签，对应不了的写进 aliases 或正文，绝不写含中文、大写或空格的标签。tags 里不要写 primary:、evidence:，也不要写 price:/terrain:/season:/sold_by:/restriction:（程序按 game 生成）。
game：价格以便士计，12 便士=1 先令，240 便士=1 镑；锚点：麦酒一杯 2 便士，一袋干麦 12 便士，渡船 12 便士。tier 按 max 推：小于1 farthing，1–3 penny，4–11 groat，12–239 shilling，240 起 pound；不可买卖用 not_for_sale，传说无价用 priceless，二者 min/max 为 null、sold_by 只能是 ["none"]。terrains 1–3 个、seasons 1–4 个、sold_by 1–3 个，都取自 vocab；keeps 取自 vocab.keeps。
这是设定推演，不是史实：不要编造来源、引文、书名或"据某某记载"；evidence_and_uncertainty 说明哪些是推演、哪些待作者确认。非人但有心智的生物（如西幻的龙）primary 取 race。
药材与方剂：不写剂量、用量、服用或外用方法、疗程、主治与疗效断言，只写形态、产地、交易、保存、真伪与故事用途。
context 里若有 errors，说明上一版没通过校验：逐条修正后重新输出完整 JSON。"""

NPC_SYSTEM = """织梦·玩家 NPC 角色卡草稿协议 v1
只输出一个 JSON 对象，不输出 Markdown 或推理。按 request 的名字、标签和方向补全一张 NPC 角色卡。
字段：identity、experiences、values、goal、pressure、boundaries、bargaining、social_context、emotion、failure_response，每个都是 {"text": 非空中文、不超过400字, "visibility": "public" 或 "private"}；公开内容可用于现场对话，私密内容只给本人视角与作者。
knowledge：1–8 条 {"text", "kind", "source", "confidence"(0–1), "visibility"}，kind 只能是 rumor（传闻）、interpretation（个人推测）、misunderstanding（误解）之一，不要用 observation。
人物所知只是人物的说法，不是世界事实。经历只写旅程开始前的过往；不得声称人物亲眼见过、目睹或亲历故事里尚未发生的事件，也不写"亲眼""目睹"之类措辞。
不编造故事包里不存在的地点或人物；context.package 给出的才是现有内容。
context 里若有 errors，说明上一版没通过校验：逐条修正后重新输出完整 JSON。"""


def vocabulary():
    return {'primary': dict(catalog_overlay.PRIMARY),
            'price_tiers': list(game_fields.PRICE_TIERS),
            'terrains': list(game_fields.TERRAINS),
            'seasons': list(game_fields.SEASONS),
            'keeps': list(game_fields.KEEPS),
            'sold_by': list(game_fields.SOLD_BY),
            'restrictions': list(game_fields.RESTRICTIONS)}


# ------------------------------------------------------------ 离线模板（元素）
GUESS = (
    (('魔药',), 'potion'), (('丹药', '灵丹'), 'elixir_pill'), (('方剂',), 'formula'),
    (('药材', '草药', '药'), 'medicinal_herb'),
    (('种族', '龙', '精灵', '矮人', '族'), 'race'),
    (('亡灵', '鬼', '魔物'), 'undead_demon'), (('精怪', '妖'), 'spirit'),
    (('兽', '狼', '虎', '鸟', '鱼', '马'), 'beast'),
    (('酒',), 'alcohol'), (('茶', '饮'), 'beverage'), (('面包',), 'bread'), (('汤',), 'soup'),
    (('菜', '肴', '食'), 'dish'),
    (('剑', '刀', '枪', '弓', '兵器'), 'weapon'), (('甲', '盔'), 'armor'),
    (('船', '车'), 'vehicle_vessel'), (('矿',), 'ore'), (('金属', '铁', '铜'), 'metal'),
    (('木材',), 'timber'), (('布', '织'), 'fiber_textile'),
    (('法宝', '神器'), 'artifact'), (('灵材',), 'magic_material'),
    (('法术', '魔法', '咒'), 'magic_power'), (('仪式', '信仰', '祭', '神'), 'belief_ritual'),
    (('组织', '门派', '帮', '会'), 'organization'), (('制度', '法律'), 'institution'),
    (('职业', '匠'), 'profession'), (('店', '铺'), 'shop'),
    (('城', '村', '山', '河', '地点'), 'place'), (('工具',), 'tool'),
)
FOOD = ('grain', 'legume', 'root_tuber', 'vegetable', 'fruit', 'nut_seed', 'oil_crop', 'mushroom',
        'spice', 'culinary_herb', 'condiment', 'sweetener', 'beverage', 'alcohol', 'meat', 'poultry',
        'seafood', 'dairy', 'egg', 'preserved_food', 'dish', 'soup', 'bread', 'pastry', 'snack',
        'noodle', 'sauce', 'fat_oil')
NOT_GOODS = ('race', 'beast', 'plant', 'spirit', 'undead_demon', 'magic_power', 'technology',
             'craft_process', 'institution', 'organization', 'profession', 'belief_ritual',
             'economy_trade', 'conflict_event', 'place', 'natural_phenomenon', 'character_trait',
             'character_attribute', 'literature_form', 'name_pool', 'shop', 'cooking_technique',
             'facility', 'livestock')


def guess_primary(name, tags):
    for text in list(tags) + [name]:
        for words, primary in GUESS:
            if any(word in text for word in words):
                return primary
    return 'tool'


def offline_game(primary):
    note = '离线模板估价，是游戏设计数值，待作者调整。'
    if primary in FOOD:
        return {'price': {'min': 1, 'max': 3, 'per': '一份', 'tier': 'penny'},
                'terrains': ['workshop', 'farmland'], 'seasons': ['all_year'], 'keeps': 'days',
                'sold_by': ['tavern', 'market'], 'note': note}
    if primary in MEDICINAL or primary in ('potion', 'elixir_pill'):
        return {'price': {'min': 4, 'max': 8, 'per': '一包', 'tier': 'groat'},
                'terrains': ['mountain', 'temperate_forest'], 'seasons': ['autumn'],
                'keeps': 'months', 'sold_by': ['apothecary', 'herbalist'], 'note': note}
    if primary in NOT_GOODS:
        return {'price': {'min': None, 'max': None, 'per': '', 'tier': 'not_for_sale'},
                'terrains': ['temperate_forest'], 'seasons': ['all_year'], 'keeps': 'years',
                'sold_by': ['none'], 'note': '不作为商品买卖；离线模板，待作者调整。'}
    return {'price': {'min': 12, 'max': 36, 'per': '一件', 'tier': 'shilling'},
            'terrains': ['workshop'], 'seasons': ['all_year'], 'keeps': 'years',
            'sold_by': ['market'], 'note': note}


def offline_element(request):
    """确定性的离线模板：同一请求得到同一份输出。只填结构，不假装完成了创作。"""
    primary = request['primary'] or guess_primary(request['name'], request['tags'])
    name = request['name']
    tags_text = '、'.join(request['tags']) or '（未给）'
    medicinal = primary in MEDICINAL
    # 药材类不回显玩家方向：玩家原话里可能有疗效说法，红线由校验守住，模板不替它背书。
    direction = '（方向见草稿请求）' if medicinal else (request['direction'] or '（未给方向）')
    tags = ['kind:' + primary]
    if request.get('tradition'):
        tags.append('tradition:' + request['tradition'])
    return {
        'summary': '%s：按玩家标签（%s）起草的设定元素，离线模板，待作者改写。' % (name, tags_text),
        'aliases': [],
        'primary': primary,
        'tags': tags,
        'game': offline_game(primary),
        'details': {
            'definition': '%s是按玩家方向起草的设定元素。玩家给出的标签：%s。方向：%s。本段是离线模板，'
                          '没有调用模型，待作者改写。' % (name, tags_text, direction),
            'mechanism': '%s靠什么运作、由谁维持，离线模板不作推演；请作者补写它的来源、代价与限制。' % name,
            'conditions': '出现前提（地域、季节、人群、材料）待作者确定。',
            'exceptions': '例外与反例待作者补充；作者确认前不要把本条当成世界通则。',
            'story_uses': '可作为线索、交易物或冲突起点，具体用法待作者按玩家方向细化。',
            'historical_scope': '架空设定，不对应任何现实时代或地区的史实。',
            'evidence_and_uncertainty': '离线模板没有调用模型，全部内容待作者核对。',
        },
    }


# --------------------------------------------------------- 规范化与校验（元素）
def _text_or_none(value):
    return value if isinstance(value, str) else None


def normalize_element(raw, *, element_id, name, primary=None, tradition=None, origin=None):
    """把模型（或作者编辑）的输出套上强制口径。返回 (element, errors)。

    只取白名单字段；来源、证据等级、审核状态、id、组一律由代码写，不读模型的值。
    """
    errors = []
    if not isinstance(raw, dict):
        return None, ['输出必须是 JSON 对象（得到 %s）' % type(raw).__name__]
    details_raw = raw.get('details')
    if not isinstance(details_raw, dict):
        errors.append('details 必须是对象，且含七节')
        details_raw = {}
    details = {key: details_raw.get(key) for key in enc.DETAIL_SECTIONS}
    evidence = details.get('evidence_and_uncertainty')
    if isinstance(evidence, str) and evidence.strip():
        if EVIDENCE_NOTICE not in evidence:
            details['evidence_and_uncertainty'] = EVIDENCE_NOTICE + evidence.strip()
    else:
        errors.append('details.evidence_and_uncertainty 不能为空')
    aliases = raw.get('aliases') or []
    if not isinstance(aliases, list) or not all(isinstance(a, str) for a in aliases):
        errors.append('aliases 必须是字符串数组')
        aliases = []
    aliases = enc.dedupe([a.strip() for a in aliases if a.strip() and a.strip() != name])
    tags = raw.get('tags') or []
    if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
        errors.append('tags 必须是字符串数组')
        tags = []
    tags = [t.strip() for t in tags if not t.strip().startswith(GAME_PREFIXES + (ORIGIN_TAG,))]
    if tradition:
        tags = [t for t in tags if not t.startswith('tradition:')] + ['tradition:' + tradition]
    game = raw.get('game')
    if isinstance(game, dict):
        game = copy.deepcopy(game)
        game['schema'] = game_fields.SCHEMA
        try:
            tags += game_fields.validate_game(game, element_id)
        except game_fields.GameFieldError as error:
            errors.append(str(error))
    else:
        errors.append('game 必须是对象')
    tags.append(ORIGIN_TAG)
    element = {
        'id': element_id,
        'name': name,
        'aliases': aliases,
        'summary': raw.get('summary'),
        'primary': primary or raw.get('primary'),
        'evidence_grade': 'inferred',
        'tags': enc.dedupe(tags),
        'details': details,
        'game': game,
        'source_ids': [],
        'review_status': 'needs_review',
        'detail_status': 'needs_detail',
    }
    if origin:
        element['origin'] = copy.deepcopy(origin)
    return element, errors


def wrap_document(elements):
    return {**DOCUMENT_META, 'elements': list(elements)}


def validate_element(element):
    """引擎 + 游戏字段 + 主标签 + 药材红线。返回错误列表（空 = 通过）。"""
    errors = []
    primary = element.get('primary')
    if primary not in catalog_overlay.PRIMARY:
        errors.append('primary %r 不在主标签词表' % (primary,))
    summary = element.get('summary')
    if not isinstance(summary, str) or not summary.strip():
        errors.append('summary 不能为空')
    elif len(summary) > MAX_SUMMARY:
        errors.append('summary 超过 %d 字' % MAX_SUMMARY)
    for key in enc.DETAIL_SECTIONS:
        value = element['details'].get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append('details.%s 不能为空' % key)
        elif len(value) > MAX_SECTION:
            errors.append('details.%s 超过 %d 字' % (key, MAX_SECTION))
    tags = element.get('tags') or []
    bad = [t for t in tags if not enc._TAG_RE.match(t) or len(t) > enc.MAX_TAG_CHARS]
    if bad:
        errors.append('标签必须是小写英文（可含下划线/点/冒号/连字符），不合法：%s' % bad)
    if any(t.startswith(('primary:', 'evidence:')) for t in tags):
        errors.append('tags 里不许手写 primary:/evidence:（由 primary 与 evidence_grade 派生）')
    if not any(t.startswith('kind:') and len(t) > 5 for t in tags):
        errors.append('至少需要一个 kind: 次标签')
    if isinstance(element.get('game'), dict):
        try:
            game_fields.check_element_tags(element)
        except game_fields.GameFieldError as error:
            errors.append(str(error))
    if primary in MEDICINAL:
        text = '\n'.join([str(summary or '')] + [str(v or '') for v in element['details'].values()]
                         + [str((element.get('game') or {}).get('note') or '')])
        hits = [word for word in MEDICINAL_WORDS if word in text]
        if MEDICINAL_AMOUNT.search(text):
            hits.append('数量单位')
        if hits:
            errors.append('药材/方剂不得写剂量、用法或疗效断言，命中：%s' % '、'.join(hits))
    if not errors:
        try:
            enc.prepare_document(wrap_document([element]), namespace=NAMESPACE,
                                 adapter=enc.ADAPTER_HUMAN)
        except enc.EncyclopediaError as error:
            errors.append(str(error))
    return errors


# ------------------------------------------------------- 规范化与校验（NPC）
PUBLIC_DEFAULT = ('identity', 'values', 'goal', 'bargaining', 'social_context', 'emotion')


def normalize_card(raw):
    if not isinstance(raw, dict):
        return None, ['输出必须是 JSON 对象（得到 %s）' % type(raw).__name__]
    card, errors = {'version': 1}, []
    for key in npc_cards.FIELDS:
        value = raw.get(key)
        default = 'public' if key in PUBLIC_DEFAULT else 'private'
        if isinstance(value, str):
            value = {'text': value, 'visibility': default}
        if not isinstance(value, dict):
            errors.append('%s 必须是 {text, visibility}' % key)
            value = {'text': '', 'visibility': default}
        card[key] = {'text': value.get('text', ''), 'visibility': value.get('visibility', default)}
    knowledge = raw.get('knowledge') or []
    if not isinstance(knowledge, list):
        errors.append('knowledge 必须是数组')
        knowledge = []
    card['knowledge'] = [
        {k: entry[k] for k in ('text', 'kind', 'source', 'confidence', 'visibility') if k in entry}
        if isinstance(entry, dict) else entry for entry in knowledge]
    return card, errors


def validate_card(card):
    errors = []
    try:
        npc_cards.NPCCard.model_validate(card)
    except ValidationError as error:
        return ['角色卡结构校验失败：' + '；'.join(
            '%s: %s' % ('.'.join(str(p) for p in item['loc']), item['msg'])
            for item in error.errors()[:8])]
    for key in npc_cards.FIELDS:
        if not card[key]['text'].strip():
            errors.append('%s 不能为空（需补全全部字段）' % key)
    if not card['knowledge']:
        errors.append('knowledge 至少一条')
    for index, entry in enumerate(card['knowledge']):
        if entry['kind'] == 'observation':
            errors.append('knowledge[%d] 不能是 observation：AI 草稿不声称人物亲见任何事' % index)
        text = entry['text'] + entry['source']
        if any(word in text for word in WITNESS_WORDS):
            errors.append('knowledge[%d] 不得声称人物亲眼见过或目睹某事' % index)
    return errors


def offline_card(request):
    name, direction = request['name'], request['direction'] or '（未给方向）'
    tags_text = '、'.join(request['tags']) or '身份待定'
    fields = {
        'identity': ('%s，%s。离线模板，待作者改写。' % (name, tags_text), 'public'),
        'experiences': ('旅程开始前的过往按玩家方向起草：%s。具体经历待作者补写。' % direction, 'private'),
        'values': ('看重信用与自身安危，先后次序待作者确定。', 'public'),
        'goal': ('眼下想要的东西与玩家给的方向有关，待作者细化。', 'public'),
        'pressure': ('有尚未说出口的顾虑，内容待作者补写。', 'private'),
        'boundaries': ('不会为陌生人冒生命危险，也不出卖亲近的人。', 'private'),
        'bargaining': ('可以用钱、消息或帮忙换取合作。', 'public'),
        'social_context': ('所属阶层、阵营与当地习俗待作者按故事包补写。', 'public'),
        'emotion': ('对来者保持礼貌而谨慎。', 'public'),
        'failure_response': ('交涉失败时客气地结束谈话，并记住这次不愉快。', 'private'),
    }
    card = {key: {'text': text, 'visibility': vis} for key, (text, vis) in fields.items()}
    card['knowledge'] = [
        {'text': '听人说起过一些与自己有关的传闻，真假未知。', 'kind': 'rumor',
         'source': '街谈巷议', 'confidence': 0.4, 'visibility': 'private'},
        {'text': '觉得最近来的生面孔里有人别有用心。', 'kind': 'interpretation',
         'source': '自己的揣测', 'confidence': 0.5, 'visibility': 'private'}]
    return card


# ----------------------------------------------------------------- 服务
class AIDrafts:
    def __init__(self, service):
        self.service = service

    # ------------------------------------------------------------ 公共读
    def list(self, kind=None):
        rows = [d for d in self.service.store.all(KIND) if kind in (None, '', d['type'])]
        return sorted(rows, key=lambda d: (d['created'], d['id']), reverse=True)

    def get(self, draft_id):
        draft = self.service.store.get(KIND, draft_id)
        if not draft:
            raise ValueError('AI 草稿不存在')
        return draft

    # ------------------------------------------------------------ 模型调用
    async def _run(self, scope, system, context, example, normalize, validate, max_tokens):
        """离线 → 确定性模板；在线 → 至多两次（第二次带上错误）。全部失败抛 DraftRejected。"""
        provider = self.service.provider
        offline = bool(provider.config()['offline'])
        attempts, usage = [], {'mode': 'offline' if offline else 'online', 'calls': 0}
        for attempt in range(1 if offline else MAX_ATTEMPTS):
            ctx = dict(context)
            if attempts:
                ctx['previous_output'] = attempts[-1]['output']
                ctx['errors'] = attempts[-1]['errors']
            if offline:
                output = copy.deepcopy(example)
                provider.offline_trace(scope, ctx, output)
            else:
                try:
                    output, used = await provider.complete(system, ctx, json_mode=True,
                                                           scope=scope, max_tokens=max_tokens)
                    usage['calls'] += 1
                    usage.setdefault('attempts', []).append(used)
                except ValueError as error:
                    usage['calls'] += 1
                    attempts.append({'output': None, 'errors': ['模型调用失败：' + str(error)]})
                    continue
            content, errors = normalize(output)
            if content is not None and not errors:
                errors = validate(content)
            attempts.append({'output': output, 'errors': errors})
            if not errors:
                return content, attempts, usage, offline
        raise DraftRejected(attempts[-1]['errors'])

    def _new_draft(self, kind, request, content, attempts, usage, offline, extra=None):
        stamp = now()
        return {'id': uid(), 'type': kind, 'status': 'draft', 'revision': 1,
                'created': stamp, 'updated': stamp, 'offline': offline,
                'request': request, 'attempts': attempts, 'usage': usage,
                'content': content,
                'validation': {'ok': True, 'errors': [], 'checked_at': stamp},
                'notice': AI_NOTICE, 'confirmed': None, 'history': [], **(extra or {})}

    async def _store_new(self, draft):
        async with self.service.lock:
            if self.service.store.get(KIND, draft['id']) is not None:
                raise ValueError('草稿标识冲突，请重试')
            self.service.store.put(KIND, draft['id'], draft)
        return draft

    # -------------------------------------------------------------- 元素
    async def generate_element(self, req: ElementDraftRequest):
        request = req.model_dump()
        request['name'] = request['name'].strip()
        request['tags'] = _clean_tags(request['tags'])
        if request['primary'] is not None and request['primary'] not in catalog_overlay.PRIMARY:
            raise ValueError('primary 提示 %r 不在主标签词表' % request['primary'])
        if request['tradition'] is not None:
            request['tradition'] = request['tradition'].strip().lower()
            if not enc._TAG_RE.match(request['tradition']):
                raise ValueError('tradition 必须是小写英文（如 western、eastern）')
        element_id = ID_PREFIX + uid()
        origin = {'kind': 'ai_player_draft', 'request': {k: request[k] for k in ('name', 'tags', 'direction')}}
        example = offline_element(request)
        context = {'request': request, 'vocab': vocabulary(), 'example': example}

        def normalize(raw):
            return normalize_element(raw, element_id=element_id, name=request['name'],
                                     primary=request['primary'], tradition=request['tradition'],
                                     origin=origin)

        content, attempts, usage, offline = await self._run(
            'ai_draft_element', ELEMENT_SYSTEM, context, example, normalize, validate_element,
            ELEMENT_TOKENS)
        content['origin']['offline'] = offline
        draft = self._new_draft('element', request, content, attempts, usage, offline,
                                {'element_id': element_id, 'namespace': NAMESPACE})
        return await self._store_new(draft)

    # ---------------------------------------------------------------- NPC
    def _package_context(self, request):
        runtime = self.service.runtime
        if not runtime.has_world():
            if request.get('character_id') or request.get('location_id'):
                raise ValueError('还没有可用的世界，不能指定人物或地点')
            return None
        package = runtime.package()
        story, chars = package['story'], package['characters']['characters']
        actor = None
        if request.get('character_id'):
            actor = next((c for c in chars if c['id'] == request['character_id']), None)
            if actor is None or actor['role'] == '主角':
                raise ValueError('请选择有效的 NPC')
        place = None
        if request.get('location_id'):
            place = next((p for p in story['locations'] if p['id'] == request['location_id']), None)
            if place is None:
                raise ValueError('地点不在当前故事包里')
        return {'revision': package['id'], 'title': story.get('title', ''),
                'characters': [{'id': c['id'], 'name': c['name']} for c in chars if c['role'] != '主角'],
                'locations': [{'id': p['id'], 'name': p['name']} for p in story['locations']],
                'location': None if place is None else {'id': place['id'], 'name': place['name'],
                                                        'description': place.get('description', '')},
                'current_card': None if actor is None else actor.get('npc_card')}

    async def generate_npc(self, req: NPCDraftRequest):
        request = req.model_dump()
        request['name'] = request['name'].strip()
        request['tags'] = _clean_tags(request['tags'])
        package = self._package_context(request)
        example = offline_card(request)
        context = {'request': request, 'package': package, 'example': example}
        content, attempts, usage, offline = await self._run(
            'ai_draft_npc', NPC_SYSTEM, context, example, normalize_card, validate_card, NPC_TOKENS)
        draft = self._new_draft('npc', request, content, attempts, usage, offline,
                                {'base_revision': None if package is None else package['revision']})
        return await self._store_new(draft)

    # ------------------------------------------------------------ 故事包
    async def generate_story(self, req: StoryDraftRequest):
        """薄封装：组装成 world_generator 的现有请求，草稿/校验/发布全走它自己的流程。"""
        from .world_generator import GenerateWorldRequest
        tags = _clean_tags(req.tags)
        lines = ['玩家给的标签：' + ('、'.join(tags) if tags else '（未给）'),
                 '大概方向：' + req.direction.strip(),
                 '请按标签与方向补全；没给的细节标为待定，不要假装已核实。']
        gen = GenerateWorldRequest(kind=req.kind, title=(req.title or '').strip() or '未命名世界',
                                   instruction='\n'.join(lines),
                                   historical_reference=req.historical_reference,
                                   city_count=req.city_count, output_tokens=req.output_tokens)
        return await self.service.world_generator.generate(gen)

    # -------------------------------------------------------------- 编辑
    def edit(self, draft_id, req: DraftEdit):
        draft = self.get(draft_id)
        if draft['status'] == 'rejected':
            raise ValueError('已拒绝的草稿不能再编辑，请重新生成')
        if draft['revision'] != req.revision:
            raise ValueError('草稿已被其他操作更新，请刷新后再改')
        if draft['type'] == 'element':
            name = req.content.get('name')
            name = name.strip() if isinstance(name, str) and name.strip() else draft['content']['name']
            content, errors = normalize_element(
                req.content, element_id=draft['element_id'], name=name,
                origin=draft['content'].get('origin'))
            if content is not None and not errors:
                errors = validate_element(content)
        else:
            content, errors = normalize_card(req.content)
            if content is not None and not errors:
                errors = validate_card(content)
        if errors:
            raise ValueError('修改未通过校验，草稿未改动：' + '；'.join(errors[:8]))
        stamp = now()
        draft['content'] = content
        draft['revision'] += 1
        draft['updated'] = stamp
        draft['validation'] = {'ok': True, 'errors': [], 'checked_at': stamp}
        if draft['status'] == 'confirmed':
            draft['status'] = 'draft'  # 再改需再确认，确认后形成新版本。
        draft['history'].append({'action': 'edit', 'at': stamp, 'revision': draft['revision']})
        self.service.store.put(KIND, draft_id, draft)
        return draft

    def reject(self, draft_id, req: DraftDecision):
        draft = self.get(draft_id)
        if req.revision is not None and draft['revision'] != req.revision:
            raise ValueError('草稿已被其他操作更新，请刷新后再操作')
        if draft['status'] == 'rejected':
            return draft
        if draft['status'] == 'confirmed':
            raise ValueError('草稿已确认，拒绝不会撤回已入库的版本；如需改动请编辑后重新确认')
        stamp = now()
        draft['status'], draft['updated'] = 'rejected', stamp
        draft['history'].append({'action': 'reject', 'at': stamp})
        self.service.store.put(KIND, draft_id, draft)
        return draft

    # -------------------------------------------------------------- 确认
    def confirm(self, draft_id, req: DraftDecision):
        draft = self.get(draft_id)
        if draft['status'] == 'rejected':
            raise ValueError('已拒绝的草稿不能确认')
        if req.revision is not None and draft['revision'] != req.revision:
            raise ValueError('草稿已被其他操作更新，请刷新后再确认')
        if draft['type'] == 'element':
            return self._confirm_element(draft)
        return self._confirm_npc(draft, req)

    def library_path(self, must_exist=True):
        path = self.service.elements.library().resolve()
        if must_exist and not path.is_file():
            raise ValueError('百科库不存在：请先运行 python -m tools.encyclopedia_build 生成库；'
                             '确认不会自动建库，草稿保持未确认')
        return path

    def _confirm_element(self, draft):
        element = draft['content']
        errors = validate_element(element)
        if errors:
            raise ValueError('草稿未通过校验，未入库：' + '；'.join(errors[:8]))
        digest = enc.payload_hash(element)
        path = self.library_path()
        previous = draft.get('confirmed') or {}
        idempotent = draft['status'] == 'confirmed' and previous.get('content_hash') == digest
        result = enc.import_document(path, wrap_document([element]), namespace=NAMESPACE,
                                     adapter=enc.ADAPTER_HUMAN)
        rows = enc.versions(path, element['id'], namespace=NAMESPACE)['versions']
        version = next(row['version'] for row in rows if row['content_hash'] == digest)
        stamp = now()
        self._keep_copy(element, digest, draft['id'], stamp)
        if not idempotent:
            draft['confirmed'] = {'namespace': NAMESPACE, 'element_id': element['id'],
                                  'version': version, 'content_hash': digest, 'at': stamp}
            draft['status'], draft['updated'] = 'confirmed', stamp
            draft['history'].append({'action': 'confirm', 'at': stamp, 'version': version,
                                     'revision': draft['revision']})
            self.service.store.put(KIND, draft['id'], draft)
        return {**draft, 'idempotent': idempotent,
                'import': {'element_versions_written': result.element_versions,
                           'unchanged_elements': result.unchanged_elements}}

    def _keep_copy(self, element, digest, draft_id, stamp):
        """确认过的每个版本在旅程存储里留完整副本，库重建后可幂等恢复。"""
        store = self.service.store
        record = store.get(CONFIRMED_KIND, element['id']) or {
            'element_id': element['id'], 'namespace': NAMESPACE, 'versions': []}
        if any(v['content_hash'] == digest for v in record['versions']):
            return
        record['versions'].append({'content_hash': digest, 'element': copy.deepcopy(element),
                                   'draft_id': draft_id, 'confirmed_at': stamp})
        store.put(CONFIRMED_KIND, element['id'], record)

    def restore_confirmed(self, db_path=None):
        """把存储里全部已确认元素按确认顺序重新导入（幂等）。库被重建后用它恢复。"""
        path = self.library_path() if db_path is None else db_path
        written = unchanged = 0
        records = sorted(self.service.store.all(CONFIRMED_KIND),
                         key=lambda r: (r['versions'][0]['confirmed_at'], r['element_id']))
        for record in records:
            for item in record['versions']:
                result = enc.import_document(path, wrap_document([item['element']]),
                                             namespace=NAMESPACE, adapter=enc.ADAPTER_HUMAN)
                written += result.element_versions
                unchanged += result.unchanged_elements
        return {'elements': len(records), 'element_versions_written': written,
                'unchanged': unchanged}

    def _confirm_npc(self, draft, req):
        card = draft['content']
        errors = validate_card(card)
        if errors:
            raise ValueError('草稿未通过校验，未保存：' + '；'.join(errors[:8]))
        digest = enc.payload_hash(card)
        previous = draft.get('confirmed') or {}
        if draft['status'] == 'confirmed' and previous.get('card_hash') == digest:
            return {**draft, 'idempotent': True}
        character_id = req.character_id or draft['request'].get('character_id')
        if not character_id:
            raise ValueError('请选择要挂上这张角色卡的 NPC')
        if not req.package_revision:
            raise ValueError('确认需要 package_revision（请先读取最新角色卡）')
        # 走现有作者保存路径：新故事包版本；已开始的旅程仍绑旧版本，不自动换卡。
        revision = npc_cards.save_card(self.service.runtime, req.package_revision, character_id,
                                       card, note='AI 草稿确认 NPC 角色卡：')
        stamp = now()
        draft['confirmed'] = {'character_id': character_id, 'base_revision': req.package_revision,
                              'revision': revision, 'card_hash': digest, 'at': stamp}
        draft['status'], draft['updated'] = 'confirmed', stamp
        draft['history'].append({'action': 'confirm', 'at': stamp, 'revision': draft['revision'],
                                 'package_revision': revision})
        self.service.store.put(KIND, draft['id'], draft)
        return {**draft, 'idempotent': False}
