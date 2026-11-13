# -*- coding: utf-8 -*-
"""由地理 + 百科生成故事包（首轮：单一地区）。设计见 ``docs/world-package-pipeline.md``。

本模块**只认识** :class:`app.world_source.RegionSnapshot`，不 import 任何地图引擎模块；
引擎由调用方以 ``WorldSource`` 适配器的形式传进来（civ-atlas 见
``app/world_source_civ_atlas.py``，以后的 Terragenesis 冻结产品另写一个适配器即可）。

流程与草稿状态（``service.store`` 的 ``world_package_draft``）::

    propose(source, region_id, setting)   挑元素：候选清单草稿（不调模型） stage=proposed
    select(draft_id, refs, acknowledge)   作者勾选 → element_assembly.build_manifest 锁定  stage=selected
    generate(draft_id)                    写历史 → 定政治 → 写设定与知识点（模型或离线示例） stage=generated
    edit(draft_id, content)               作者改写，按同样规则重新校验
    confirm(draft_id, source)             过期检查 → world_generator.compile_package 编译
                                          → world_setting.validate / runtime.validate_package → 写故事包目录

规则（全部由代码校验，不靠提示词自觉）：

* 历史严格跟模拟走：每段叙述必须带 ``event_ids``；引用的 id 必须在本次输入的事件里；
  段落里出现的国家名必须是所引事件的参与方（或出现在所引事件原文里）；出现的阿拉伯数字
  「N年」必须是所引事件的年份；形如「××王国/帝国/王朝…」而引擎里没有的名字一律拒绝。
* 定政治：每个地区内国家匹配 ``docs/element-catalog/polities.json`` 的政体模板作 ``element_ref``；
  种族、文化只能取作者已选元素。
* 设定与知识点只能引用已选元素（``element_refs``）与已生成历史（``event_ids`` 只能取历史段落
  引用过的事件）；正文出现候选清单里**未选**元素的名字也拒绝。
* 模型调用与 ``app/ai_drafts.py`` 同口径（复用其 ``_run``）：在线失败重试一次，仍失败整体拒绝、
  草稿不变；离线返回由快照确定性生成的示例。
* 确认前不写故事包；确认时比对来源身份与地区快照摘要，引擎数据变了就拒绝（过期）。
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

from . import element_assembly, world_setting
from . import world_generator as wg
from . import world_source as ws
from .ai_drafts import DraftRejected
from .knowledge import PackageFiles, atomic_text
from .prompts import stable_json
from .runtime import now, uid
from .terrain_rules import RULES as TERRAIN_RULES
from .token_budget import output_tokens

KIND = 'world_package_draft'
SCHEMA = 'world_package_draft_v1'
POLITIES_FILE = Path(__file__).resolve().parents[1] / 'docs/element-catalog/polities.json'
POLITY_NAMESPACE = 'polities'

PAGE = 200
MAX_SCAN = 5000
MAX_RECOMMENDED = 120
MAX_HINTED = 40
MAX_SELECTED = element_assembly.MAX_ELEMENTS
MAX_HISTORY_EVENTS = 80
OFFLINE_SECTION_EVENTS = 10
MAX_SECTIONS = 16
MAX_SECTION_CHARS = 3000
MAX_KNOWLEDGE = 24
MAX_OFFLINE_ELEMENT_POINTS = 12
STEP_TOKENS = output_tokens('world_package_history')
NOTICE = 'AI 推演、未核实：历史只改写模拟事件；确认前不写任何故事包。'

TERRAIN_NAMES = {
    'ocean': '海洋', 'lake': '湖泊', 'tundra': '苔原', 'taiga': '针叶林', 'cold_desert': '寒漠',
    'temperate_desert': '温带荒漠', 'steppe': '草原', 'temperate_forest': '温带森林',
    'temperate_rainforest': '温带雨林', 'hot_desert': '热带荒漠', 'savanna': '稀树草原',
    'tropical_dry_forest': '热带季雨林', 'rainforest': '热带雨林', 'wetland': '湿地',
    'mountain': '山地', 'plateau': '高原', 'coast': '海岸', 'river': '河流',
    'farmland': '农田（适宜）', 'orchard': '果园（适宜）', 'pasture': '牧场（适宜）',
    'mine': '矿坑（适宜）', 'workshop': '作坊', 'import': '远途输入',
}
FOREST = {'taiga', 'temperate_forest', 'temperate_rainforest', 'tropical_dry_forest', 'rainforest'}
DESERT = {'cold_desert', 'temperate_desert', 'hot_desert'}

#: 引擎的政体提示没有对应模板（或模板越档）时依次尝试的相近政体。
FORM_FALLBACK = {
    'republic': ('merchant', 'city_state'), 'merchant': ('republic', 'city_state'),
    'city_state': ('merchant', 'republic'), 'monarchy': ('empire',), 'empire': ('monarchy',),
    'tribal': (), 'theocracy': (),
}

#: 历史输入的取舍顺序（只决定**挑哪些**事件给模型，不改事件本身）。越靠前越优先。
KIND_ORDER = ('found', 'fall', 'collapse', 'split', 'merge', 'dynasty', 'capital', 'war', 'peace',
              'treaty', 'alliance', 'unally', 'breach', 'expire', 'submit', 'defect', 'revolt',
              'marry', 'council', 'rank', 'sack', 'ruin', 'rebuild', 'decline', 'plague',
              'pandemic', 'famine', 'desolate', 'warlord', 'reclaim', 'defy', 'stand', 'exile',
              'neutral', 'intervene', 'keep', 'sunk', 'fiscal', 'regent', 'battle', 'conquer')
KIND_RANK = {kind: index for index, kind in enumerate(KIND_ORDER)}
STANCE = {'war': '交战', 'battle': '交战', 'conquer': '交战', 'sack': '交战', 'ruin': '交战',
          'defy': '对抗', 'revolt': '对抗', 'peace': '议和', 'treaty': '立约', 'alliance': '结盟',
          'marry': '联姻', 'council': '会盟', 'submit': '臣服', 'unally': '解盟',
          'breach': '毁约', 'expire': '约满'}

_ID_RE = re.compile(r'^[A-Za-z0-9_-]{1,80}$')
_SAFE_RE = re.compile(r'[^a-z0-9_.-]')
YEAR_RE = re.compile(r'(?<![\d.])(\d{1,7})\s*年')
SUFFIX_RE = re.compile(r'([\u4e00-\u9fff]{1,6}?)(共和国|王国|帝国|汗国|公国|王朝)')
#: 「××王国」前一个字是这些时按泛称处理（两国、该王朝、建立王朝、新的帝国……）。
GENERIC_LAST = set('两该此本其邻各诸旧新这那全前后的个一整小大强弱友敌盟原某立成了为入向与和及同对被将把从在是有归称建灭亡')

HISTORY_SYSTEM = """织梦·地区历史改写协议 v1
你把给定的模拟事件（events）改写成几段可读的历史叙述，返回 JSON：
{"sections":[{"title":"…","text":"…","event_ids":["ev_…"]}]}
硬规则（程序逐条校验，违反即整体拒绝）：
1. 只能改写 events 里的事件，不得新增事件、王朝、战争、人物或年份。
2. 每段必须带 event_ids，且只能取 events 里的 event_id。
3. 段落里出现的国家必须是所引事件的参与方；出现的「N年」必须是所引事件的年份；
   不要写持续年数、世纪、中文数字年份；不要给国家另起「××王国/帝国/王朝」之类的新名字。
4. 段数 1–16，每段正文不超过 3000 字。"""

POLITICS_SYSTEM = """织梦·地区政治设定协议 v1
为 polities 里每个地区内国家补政府形式、主要势力与相互关系，返回 JSON：
{"polities":[{"polity_id":"…","element_ref":"polities/…","summary":"…","government":"…",
  "powers":["…"],"relations":[{"polity_id":"…","stance":"…","text":"…","event_ids":["ev_…"]}],
  "race_refs":[],"culture_refs":[]}]}
硬规则：element_ref 只能取该国 allowed_templates 里的 ref（default_template 是按引擎政体提示的匹配）；
race_refs / culture_refs 只能取 selected_elements 里的 ref（race_refs 只能是种族元素）；
relations 的依据只能是 history_events 里的事件，正文的年份、国家规则同历史协议；不得新增战争或王朝。"""

SETTING_SYSTEM = """织梦·地区设定与知识点协议 v1
根据已生成的历史与政治、作者已选元素，写故事包的总概、知识点与城市文本，返回 JSON：
{"title":"…","overview":"…","knowledge":[{"id":"…","title":"…","category":"…","keywords":["…"],
  "content":"…","visibility":"public|author","element_refs":[],"event_ids":[]}],
 "cities":[{"settlement_id":"…","description":"…","faction_description":"…","event_title":"…",
  "goal":"…","discovery":"…","secret":"…"}],
 "hero":{"name":"…","appearance":"…","occupation":"…","personality":{"好奇":0.7},"secret":"…"},
 "guide":{同 hero},"item_name":"…","item_description":"…"}
硬规则：只能引用 selected_elements 的元素（element_refs）与 history_event_ids 里的事件（event_ids）；
正文出现的「N年」必须是所引事件的年份；不得出现未选元素的名字，不得新造国家或王朝；
cities 必须恰好覆盖 city_plan 的每个 settlement_id；知识点 id 只用字母数字下划线连字符，
不要以 history_ 或 polity_ 开头；知识点 1–24 条。"""


class WorldPackageError(ValueError):
    pass


# ============================================================== 小工具
def _text(value, label, low, high, errors):
    if not isinstance(value, str):
        errors.append('%s 必须是文本' % label)
        return ''
    value = value.strip()
    if not low <= len(value) <= high:
        errors.append('%s 长度应为 %d–%d 字（得到 %d）' % (label, low, high, len(value)))
    return value


def _str_list(value, label, errors, limit=12, item_limit=200):
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > limit:
        errors.append('%s 必须是不超过 %d 项的列表' % (label, limit))
        return []
    out = []
    for item in value:
        if not isinstance(item, str) or not item.strip() or len(item) > item_limit:
            errors.append('%s 里有无效项：%r' % (label, item))
            continue
        if item.strip() not in out:
            out.append(item.strip())
    return out


def _safe_id(value):
    out = _SAFE_RE.sub('_', str(value).lower())[:64].strip('_.-')
    return out if out and out[0].isalnum() else 'x' + out[:63]


def _clamp(value, low, high, default):
    if value is None:
        return default
    return max(low, min(high, float(value)))


def polity_templates():
    """``polities.json`` 的政体模板（只读）。ref = ``polities/<id>``，与元素库命名空间一致。"""
    data = json.loads(POLITIES_FILE.read_text(encoding='utf-8'))
    out = []
    for row in data.get('elements') or []:
        tags = list(row.get('tags') or [])
        if 'kind:polity' not in tags:
            continue
        out.append({'ref': POLITY_NAMESPACE + '/' + row['id'], 'element_id': row['id'],
                    'name': row.get('name') or row['id'], 'summary': row.get('summary') or '',
                    'tags': tags, 'forms': [t[7:] for t in tags if t.startswith('polity:')]})
    return sorted(out, key=lambda t: t['ref'])


def _weights(setting):
    return {'genre:' + g['tag']: g['weight'] for g in (setting or {}).get('genres') or []}


def _tech_index(tags):
    level = world_setting.tier_of(tags, 'tech:', world_setting.TECH)
    return -1 if level is None else level


# ============================================================== 1. 挑元素
def judge_element(item, setting, weights, region_terrains):
    """一个库条目相对「设定 + 地区产地」的判定（纯函数，测试直接用）。"""
    tags = list(item.get('tags') or [])
    score = sum(w for tag, w in weights.items() if tag in tags) if weights else 0
    conflicts = world_setting.conflicts(tags, setting)
    terrains = sorted({t[len('terrain:'):] for t in tags if t.startswith('terrain:')})
    geographic = [t for t in terrains if TERRAIN_RULES.get(t) != 'non_geographic']
    match = sorted(set(geographic) & set(region_terrains))
    if not terrains:
        terrain_status = 'not_applicable'
    elif geographic:
        terrain_status = 'match' if match else 'no_match'
    else:
        terrain_status = 'non_geographic'
    genre_ok = score > 0 or not weights
    terrain_ok = terrain_status in ('match', 'not_applicable')
    reasons = []
    if not genre_ok:
        reasons.append('类型不在世界设定里')
    if conflicts:
        reasons.extend(conflicts)
    if terrain_status == 'no_match':
        reasons.append('产地 %s 与本地区不相交' % '、'.join(geographic))
    if terrain_status == 'non_geographic':
        reasons.append('只有作坊 / 远途输入产地，本地产地无从核对')
    return {
        'ref': element_assembly.ref_of(item['namespace'], item['element_id']),
        'namespace': item['namespace'], 'element_id': item['element_id'],
        'version': item.get('version'), 'name': item.get('name') or item['element_id'],
        'primary': next((t[8:] for t in tags if t.startswith('primary:')), None),
        'is_race': 'primary:race' in tags or 'kind:race' in tags,
        'tags': [t for t in tags if t.startswith(('genre:', 'tech:', 'magic:', 'kind:', 'primary:',
                                                   'terrain:', 'polity:'))],
        'score': score, 'tier_conflicts': conflicts, 'terrains': terrains,
        'terrain_status': terrain_status, 'terrain_match': match,
        'recommended': genre_ok and terrain_ok and not conflicts,
        'hint_only': genre_ok and terrain_ok and bool(conflicts),
        'reasons': reasons,
    }


def scan_candidates(elements, setting, region_terrains):
    """扫元素库（只读），返回推荐清单与越档提示清单。``kind:polity`` 由「定政治」单独处理。"""
    weights = _weights(setting)
    tags_any = sorted(weights)
    offset, scanned, truncated = 0, 0, False
    recommended, hinted, counts = [], [], {'no_genre': 0, 'tier': 0, 'terrain': 0}
    while True:
        kwargs = {'limit': PAGE, 'offset': offset}
        if tags_any:
            kwargs['tags_any'] = tags_any
        page = elements.search(**kwargs)
        rows = page.get('items') or []
        for item in rows:
            if 'kind:polity' in (item.get('tags') or []):
                continue
            scanned += 1
            row = judge_element(item, setting, weights, region_terrains)
            if row['recommended']:
                recommended.append(row)
            elif row['hint_only']:
                hinted.append(row)
            if not (row['score'] > 0 or not weights):
                counts['no_genre'] += 1
            if row['tier_conflicts']:
                counts['tier'] += 1
            if row['terrain_status'] in ('no_match', 'non_geographic'):
                counts['terrain'] += 1
        offset += len(rows)
        if not rows or not page.get('has_more'):
            break
        if offset >= MAX_SCAN:
            truncated = True
            break
    order = lambda row: (-row['score'], row['ref'])
    recommended.sort(key=order)
    hinted.sort(key=order)
    return {'recommended': recommended[:MAX_RECOMMENDED], 'hinted': hinted[:MAX_HINTED],
            'counts': {'scanned': scanned, 'recommended': len(recommended),
                       'hinted': len(hinted), 'excluded': counts,
                       'recommended_truncated': len(recommended) > MAX_RECOMMENDED,
                       'hinted_truncated': len(hinted) > MAX_HINTED,
                       'scan_truncated': truncated},
            'rule': ('推荐 = 类型命中（未设类型时不过滤）且不越科技/魔法档位，且元素若有地理产地则与'
                     '地区产地（确定成立 + 生产用地适宜，不含候选群落）相交；没有产地标签的'
                     '（种族、制度等）不按产地过滤；只有作坊/远途输入的不推荐。越档只列在 hinted。')}


# ============================================================== 3. 政体模板匹配
def match_template(polity, templates, setting):
    weights = _weights(setting)
    allowed = [t for t in templates if not world_setting.conflicts(t['tags'], setting)]
    hint = polity.get('form_hint')
    base = {'polity_id': polity['polity_id'], 'form_hint': hint,
            'allowed_templates': [t['ref'] for t in allowed]}
    if not hint or hint == ws.MISSING:
        return dict(base, element_ref=None, status='missing',
                    note='引擎没有给政体提示，需作者从 allowed_templates 指定')
    for rank, form in enumerate((hint,) + FORM_FALLBACK.get(hint, ())):
        hits = [t for t in allowed if form in t['forms']]
        if hits:
            hits.sort(key=lambda t: (-sum(w for g, w in weights.items() if g in t['tags']),
                                     -_tech_index(t['tags']), t['ref']))
            best = hits[0]
            return dict(base, element_ref=best['ref'], template_name=best['name'],
                        status='matched' if rank == 0 else 'fallback',
                        note=('按引擎政体提示 %s 匹配' % hint) if rank == 0 else
                        ('%s 没有不越档的模板，改用相近的 %s' % (hint, form)))
    return dict(base, element_ref=None, status='no_template',
                note='政体提示 %s 及相近政体都没有不越档的模板，需作者处理' % hint)


# ============================================================== 2. 历史输入
def history_events(events, limit=MAX_HISTORY_EVENTS):
    """挑给模型的事件：按种类优先、同类取较晚的，至多 ``limit`` 条，再按原顺序排回。"""
    order = {event['event_id']: index for index, event in enumerate(events)}
    ranked = sorted(events, key=lambda e: (KIND_RANK.get(e.get('kind'), len(KIND_ORDER)),
                                           -e['year'], e['event_id']))
    picked = ranked[:limit]
    picked.sort(key=lambda e: order[e['event_id']])
    return picked


def _polity_brief(polity):
    """给模型看的国家摘要：不带逐州疆域清单（上百个州 id 只会撑爆上下文）。"""
    territory = polity.get('territory')
    return {'polity_id': polity['polity_id'], 'name': polity['name'],
            'form_hint': polity.get('form_hint'), 'capital': polity.get('capital'),
            'founded': polity.get('founded'),
            'region_count': (territory or {}).get('region_count')
            if isinstance(territory, dict) and not ws.is_missing(territory) else None}


def _event_view(event, names):
    return {'event_id': event['event_id'], 'year': event['year'], 'kind': event['kind'],
            'actors': list(event.get('actors') or []),
            'actor_names': [names.get(a, a) for a in event.get('actors') or []],
            'place': event.get('place'), 'text': event['text']}


# ============================================================== 叙述校验
class NarrativeChecker:
    """「段落提到的国家、年份能在所引事件里找到」的程序化判定。"""

    def __init__(self, polities, events, allowed_terms=()):
        self.events = {event['event_id']: event for event in events}
        groups = {}
        for polity in polities:
            if polity.get('name'):
                groups.setdefault(polity['name'], set()).add(polity['polity_id'])
        self.groups = groups
        self.names = sorted(groups, key=lambda n: (-len(n), n))
        self.terms = sorted({t for t in allowed_terms if t}, key=lambda t: (-len(t), t))

    def _scan(self, text, extra_terms=()):
        found, masked = [], text
        for name in self.names:
            if name in masked:
                found.append(name)
                masked = masked.replace(name, '\x00')
        for term in sorted(set(self.terms) | {t for t in extra_terms if t},
                           key=lambda t: (-len(t), t)):
            masked = masked.replace(term, '\x00')
        return found, masked

    def check(self, label, text, event_ids, extra_polities=(), any_polity=False):
        errors = []
        unknown = [i for i in event_ids if i not in self.events]
        if unknown:
            errors.append('%s 引用了不存在的事件：%s' % (label, '、'.join(unknown[:5])))
        cited = [self.events[i] for i in event_ids if i in self.events]
        actors = {a for event in cited for a in event.get('actors') or ()} | set(extra_polities)
        cited_text = ''.join(event.get('text') or '' for event in cited)
        places = [event.get('place') for event in cited if event.get('place')]
        years = {event['year'] for event in cited}
        found, masked = self._scan(text, places)
        if not any_polity:
            stray = [name for name in found
                     if not (self.groups[name] & actors) and name not in cited_text]
            if stray:
                errors.append('%s 提到的国家不在所引事件里：%s' % (label, '、'.join(stray[:5])))
        bad_years = sorted({int(m.group(1)) for m in YEAR_RE.finditer(masked)} - years)
        if bad_years:
            errors.append('%s 出现所引事件里没有的年份：%s' % (
                label, '、'.join(str(y) for y in bad_years[:5])))
        for m in SUFFIX_RE.finditer(masked):
            if m.group(1)[-1] in GENERIC_LAST:
                continue
            errors.append('%s 出现引擎里没有的国家/王朝名「%s」' % (label, m.group(1) + m.group(2)))
        return errors


def unselected_names_errors(label, text, candidates, selected_refs):
    names = sorted({row['name'] for row in candidates
                    if row['ref'] not in selected_refs and len(row['name']) >= 3})
    hits = [name for name in names if name in text]
    return ['%s 提到了未选元素：%s' % (label, '、'.join(hits[:5]))] if hits else []


# ============================================================== 草稿内各步的规范化与校验
def normalize_history(raw, input_ids):
    errors = []
    if not isinstance(raw, dict) or not isinstance(raw.get('sections'), list):
        return None, ['历史输出必须是 {"sections": [...]}']
    rows = raw['sections']
    if not 1 <= len(rows) <= MAX_SECTIONS:
        errors.append('历史段数应为 1–%d' % MAX_SECTIONS)
    sections = []
    for index, row in enumerate(rows[:MAX_SECTIONS]):
        label = '第 %d 段' % (index + 1)
        if not isinstance(row, dict):
            errors.append(label + ' 不是对象')
            continue
        ids = _str_list(row.get('event_ids'), label + ' event_ids', errors, limit=60, item_limit=80)
        if not ids:
            errors.append(label + ' 没有 event_ids：每段叙述都必须能追溯到模拟事件')
        sections.append({'title': _text(row.get('title'), label + '标题', 1, 60, errors),
                         'text': _text(row.get('text'), label + '正文', 1, MAX_SECTION_CHARS,
                                       errors),
                         'event_ids': ids})
    return {'sections': sections}, errors


def validate_history(content, checker):
    errors = []
    for index, section in enumerate(content['sections']):
        errors.extend(checker.check('第 %d 段' % (index + 1),
                                    section['title'] + '\n' + section['text'],
                                    section['event_ids']))
    return errors


def history_coverage(content, input_ids):
    cited = sorted({i for s in content['sections'] for i in s['event_ids']})
    return {'input_events': len(input_ids), 'cited_events': len(cited),
            'share': round(len(cited) / len(input_ids), 4) if input_ids else 0.0,
            'uncited': [i for i in input_ids if i not in set(cited)][:200]}


def normalize_politics(raw):
    errors = []
    if not isinstance(raw, dict) or not isinstance(raw.get('polities'), list):
        return None, ['政治输出必须是 {"polities": [...]}']
    out = []
    for index, row in enumerate(raw['polities'][:8]):
        label = '国家 %d' % (index + 1)
        if not isinstance(row, dict):
            errors.append(label + ' 不是对象')
            continue
        relations = []
        for k, rel in enumerate((row.get('relations') or [])[:8]):
            if not isinstance(rel, dict):
                errors.append('%s 关系 %d 不是对象' % (label, k + 1))
                continue
            relations.append({
                'polity_id': str(rel.get('polity_id') or ''),
                'stance': _text(rel.get('stance'), '%s 关系立场' % label, 1, 20, errors),
                'text': _text(rel.get('text') or '', '%s 关系说明' % label, 0, 600, errors),
                'event_ids': _str_list(rel.get('event_ids'), '%s 关系 event_ids' % label, errors,
                                       limit=12, item_limit=80)})
        ref = row.get('element_ref')
        out.append({
            'polity_id': str(row.get('polity_id') or ''),
            'element_ref': ref if isinstance(ref, str) and ref else None,
            'summary': _text(row.get('summary'), label + ' 说明', 1, 400, errors),
            'government': _text(row.get('government'), label + ' 政府形式', 1, 800, errors),
            'powers': _str_list(row.get('powers'), label + ' 主要势力', errors, limit=8),
            'relations': relations,
            'race_refs': _str_list(row.get('race_refs'), label + ' race_refs', errors, limit=8),
            'culture_refs': _str_list(row.get('culture_refs'), label + ' culture_refs', errors,
                                      limit=8),
        })
    return {'polities': out}, errors


def validate_politics(content, region_polities, matches, selected, checker, candidates):
    errors = []
    region_ids = [p['polity_id'] for p in region_polities]
    got = [p['polity_id'] for p in content['polities']]
    if sorted(got) != sorted(region_ids):
        errors.append('政治输出必须恰好覆盖地区内国家 %s（得到 %s）' % (region_ids, got))
    match_of = {m['polity_id']: m for m in matches}
    selected_refs = {row['ref'] for row in selected}
    race_refs = {row['ref'] for row in selected if row.get('is_race')}
    for row in content['polities']:
        pid = row['polity_id']
        label = '国家 %s' % pid
        allowed = match_of.get(pid, {}).get('allowed_templates') or []
        if row['element_ref'] is None:
            if allowed:
                errors.append(label + ' 没有匹配政体模板（element_ref 为空）')
        elif row['element_ref'] not in allowed:
            errors.append('%s 的模板 %s 不在可用模板里（越档或不存在）' % (label, row['element_ref']))
        bad = [r for r in row['race_refs'] if r not in race_refs]
        if bad:
            errors.append('%s 的种族不是已选的种族元素：%s' % (label, '、'.join(bad)))
        bad = [r for r in row['culture_refs'] if r not in selected_refs]
        if bad:
            errors.append('%s 的文化不是已选元素：%s' % (label, '、'.join(bad)))
        own = '\n'.join([row['summary'], row['government']] + row['powers'])
        errors.extend(checker.check(label, own, [], extra_polities=[pid]))
        errors.extend(unselected_names_errors(label, own, candidates, selected_refs))
        for rel in row['relations']:
            if rel['polity_id'] not in region_ids or rel['polity_id'] == pid:
                errors.append('%s 的关系对象 %r 不是地区内的其他国家' % (label, rel['polity_id']))
            errors.extend(checker.check('%s→%s 关系' % (label, rel['polity_id']),
                                        rel['stance'] + '\n' + rel['text'], rel['event_ids'],
                                        extra_polities=[pid, rel['polity_id']]))
    return errors


PERSON_KEYS = ('name', 'appearance', 'occupation', 'personality', 'secret')
CITY_TEXT = (('description', 1, 800), ('faction_description', 1, 800), ('event_title', 1, 80),
             ('goal', 1, 300), ('discovery', 1, 800), ('secret', 1, 800))


def normalize_setting(raw):
    errors = []
    if not isinstance(raw, dict):
        return None, ['设定输出必须是对象']
    content = {'title': _text(raw.get('title'), '标题', 1, 80, errors),
               'overview': _text(raw.get('overview'), '总概', 20, 2500, errors),
               'knowledge': [], 'cities': [],
               'item_name': _text(raw.get('item_name'), '物品名', 1, 80, errors),
               'item_description': _text(raw.get('item_description'), '物品说明', 1, 400, errors)}
    rows = raw.get('knowledge')
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_KNOWLEDGE:
        errors.append('知识点应为 1–%d 条' % MAX_KNOWLEDGE)
        rows = rows if isinstance(rows, list) else []
    for index, row in enumerate(rows[:MAX_KNOWLEDGE]):
        label = '知识点 %d' % (index + 1)
        if not isinstance(row, dict):
            errors.append(label + ' 不是对象')
            continue
        visibility = row.get('visibility', 'author')
        if visibility not in ('public', 'author'):
            errors.append(label + ' 可见性只能是 public / author')
        keywords = _str_list(row.get('keywords'), label + ' 关键词', errors, limit=12, item_limit=40)
        if not keywords:
            errors.append(label + ' 至少一个关键词')
        content['knowledge'].append({
            'id': str(row.get('id') or ''),
            'title': _text(row.get('title'), label + ' 标题', 1, 100, errors),
            'category': _text(row.get('category'), label + ' 分类', 1, 60, errors),
            'keywords': keywords,
            'content': _text(row.get('content'), label + ' 正文', 1, 3000, errors),
            'visibility': visibility,
            'element_refs': _str_list(row.get('element_refs'), label + ' element_refs', errors,
                                      limit=16),
            'event_ids': _str_list(row.get('event_ids'), label + ' event_ids', errors, limit=40,
                                   item_limit=80)})
    for index, row in enumerate((raw.get('cities') or [])[:5]):
        label = '城市 %d' % (index + 1)
        if not isinstance(row, dict):
            errors.append(label + ' 不是对象')
            continue
        city = {'settlement_id': str(row.get('settlement_id') or '')}
        for key, low, high in CITY_TEXT:
            city[key] = _text(row.get(key), '%s %s' % (label, key), low, high, errors)
        content['cities'].append(city)
    for key in ('hero', 'guide'):
        person = raw.get(key)
        if not isinstance(person, dict):
            errors.append('%s 必须是对象' % key)
            continue
        try:
            wg.Person.model_validate({k: person.get(k) for k in PERSON_KEYS})
        except ValueError as error:
            errors.append('%s 不合规：%s' % (key, str(error)[:300]))
        content[key] = {k: person.get(k) for k in PERSON_KEYS}
    return content, errors


def validate_setting(content, city_plan, selected, candidates, checker):
    errors = []
    selected_refs = {row['ref'] for row in selected}
    want = [c['settlement_id'] for c in city_plan]
    got = [c['settlement_id'] for c in content['cities']]
    if sorted(want) != sorted(got):
        errors.append('cities 必须恰好覆盖 %s（得到 %s）' % (want, got))
    seen = set()
    for point in content['knowledge']:
        pid = point['id']
        label = '知识点 %s' % pid
        if not _ID_RE.match(pid) or pid in seen:
            errors.append('%s 的 id 无效或重复' % label)
        if pid.startswith(('history_', 'polity_', 'gen_', 'worldview_')):
            errors.append('%s 的 id 用了保留前缀' % label)
        seen.add(pid)
        bad = [r for r in point['element_refs'] if r not in selected_refs]
        if bad:
            errors.append('%s 引用了未选元素：%s' % (label, '、'.join(bad)))
        text = point['title'] + '\n' + point['content']
        errors.extend(checker.check(label, text, point['event_ids'], any_polity=True))
        errors.extend(unselected_names_errors(label, text, candidates, selected_refs))
    blocks = [('总概', content['title'] + '\n' + content['overview'])]
    blocks.append(('物品', content['item_name'] + '\n' + content['item_description']))
    for city in content['cities']:
        blocks.append(('城市 %s' % city['settlement_id'],
                       '\n'.join(city[key] for key, _, _ in CITY_TEXT)))
    for key in ('hero', 'guide'):
        if key in content:
            blocks.append((key, '\n'.join(str(content[key].get(k) or '')
                                          for k in ('name', 'appearance', 'occupation', 'secret'))))
    for label, text in blocks:
        errors.extend(checker.check(label, text, [], any_polity=True))
        errors.extend(unselected_names_errors(label, text, candidates, selected_refs))
    return errors


# ============================================================== 离线示例（由快照确定性生成）
def offline_history(events):
    sections = []
    for start in range(0, len(events), OFFLINE_SECTION_EVENTS):
        chunk = events[start:start + OFFLINE_SECTION_EVENTS]
        y0, y1 = chunk[0]['year'], chunk[-1]['year']
        title = ('%d年' % y0) if y0 == y1 else ('%d年至%d年' % (y0, y1))
        sections.append({'title': title,
                         'text': '；'.join(event['text'] for event in chunk) + '。',
                         'event_ids': [event['event_id'] for event in chunk]})
        if len(sections) >= MAX_SECTIONS:
            break
    return {'sections': sections}


def offline_politics(region_polities, matches, selected, history, events, templates):
    by_id = {e['event_id']: e for e in events}
    cited = [by_id[i] for s in history['sections'] for i in s['event_ids'] if i in by_id]
    names = {t['ref']: t['name'] for t in templates}
    races = sorted(row['ref'] for row in selected if row.get('is_race'))
    match_of = {m['polity_id']: m for m in matches}
    out = []
    for polity in region_polities:
        pid, name = polity['polity_id'], polity['name']
        match = match_of[pid]
        territory = polity.get('territory')
        size = ('疆域数据缺失' if ws.is_missing(territory) or not isinstance(territory, dict)
                else '基准年领有 %s 个州' % territory.get('region_count'))
        relations = []
        for other in region_polities:
            if other['polity_id'] == pid:
                continue
            shared = [e for e in cited if {pid, other['polity_id']} <= set(e.get('actors') or ())]
            if shared:
                last = shared[-1]
                relations.append({'polity_id': other['polity_id'],
                                  'stance': STANCE.get(last['kind'], '往来'),
                                  'text': '最近一次有记录的往来：' + last['text'],
                                  'event_ids': [last['event_id']]})
            else:
                relations.append({'polity_id': other['polity_id'], 'stance': '无直接记录',
                                  'text': '所选史事里两国没有直接往来的记录。', 'event_ids': []})
        template = names.get(match.get('element_ref'), '（无可用模板）')
        out.append({
            'polity_id': pid, 'element_ref': match.get('element_ref'),
            'summary': '%s：%s。离线示例，待作者改写。' % (name, size),
            'government': '%s以「%s」为模板改写（引擎政体提示：%s）。具体官制待作者补写。'
                          % (name, template, polity.get('form_hint')),
            'powers': ['%s的统治集团' % name, '%s的地方豪强' % name],
            'relations': relations,
            'race_refs': races[:1], 'culture_refs': [],
        })
    return {'polities': out}


def offline_setting(region, selected, city_plan, history):
    polity_names = [p['name'] for p in region['polities'] if p.get('in_region')]
    terrains = '、'.join(TERRAIN_NAMES.get(t, t) for t in region['terrain_union']) or '（产地数据缺失）'
    knowledge = [{
        'id': 'region_geography', 'title': region['name'] + '的地理', 'category': '地区与地理',
        'keywords': [region['name'], '地理'],
        'content': ('本地区可见的产地：%s。生产用地只表示适宜，不等于已有田地或矿。缺的数据：%s。'
                    % (terrains, '；'.join('%s（%s）' % (k, v)
                                          for k, v in sorted(region['missing_fields'].items()))
                       or '无')),
        'visibility': 'public', 'element_refs': [], 'event_ids': []}]
    for row in selected[:MAX_OFFLINE_ELEMENT_POINTS]:
        match = '、'.join(TERRAIN_NAMES.get(t, t) for t in row.get('terrain_match') or []) \
            or '不按产地判定'
        knowledge.append({
            'id': 'element_' + _safe_id(row['element_id'])[:60].replace('.', '_'),
            'title': row['name'], 'category': '本地元素', 'keywords': [row['name']],
            'content': '%s：作者已从候选清单选入本地区。对应产地：%s。具体用法待作者改写。'
                       % (row['name'], match),
            'visibility': 'author', 'element_refs': [row['ref']], 'event_ids': []})
    cities = []
    for city in city_plan:
        cities.append({
            'settlement_id': city['settlement_id'],
            'description': '%s是%s的聚落%s。' % (city['name'], city['polity_name'],
                                            '，也是国都' if city['capital'] else ''),
            'faction_description': '%s在此地的官署与地方势力，政体见国家设定。' % city['polity_name'],
            'event_title': '抵达' + city['name'],
            'goal': '了解此地与邻国的往来。',
            'discovery': '我在%s听说了%s的近况。' % (city['name'], city['polity_name']),
            'secret': '离线示例：此地的内情待作者补写。'})
    return {
        'title': region['name'][:80],
        'overview': ('本故事包取自地区「%s」：%s相邻而居。地区内可见的产地有%s。'
                     '历史只依据模拟事件改写，设定只引用作者已选元素。此为离线示例文本，待作者改写。'
                     % (region['name'], '、'.join(polity_names), terrains))[:2500],
        'knowledge': knowledge, 'cities': cities,
        'hero': {'name': '行旅者', 'appearance': '带着旧行囊的旅人。', 'occupation': '旅人',
                 'personality': {'好奇': 0.7, '谨慎': 0.5}, 'secret': '尚未向别人提起自己的出行缘由。'},
        'guide': {'name': '引路人', 'appearance': '随身携带路线册的本地向导。', 'occupation': '向导',
                  'personality': {'谨慎': 0.8}, 'secret': '曾替官署递送过未公开的信件。'},
        'item_name': '行路册', 'item_description': '记录已公开驿站与道路的纸册，不揭示未探索地区的秘密。'}


# ============================================================== 快照 → 草稿里存的有界数据
def city_plan_of(snap):
    """每个地区内国家一座城：基准年国都优先，否则该国在地区内最早的聚落（同年按 id）。"""
    if not snap.has('settlements'):
        raise WorldPackageError('快照没有聚落（%s），无法编出城市' % snap.settlements.get('reason'))
    cells = {} if not snap.has('cells') else {c['cell_id']: c for c in snap.cells}
    terrains = {} if not snap.has('terrains') else {t['cell_id']: t for t in snap.terrains}
    plan = []
    for polity in snap.region_polities():
        own = [s for s in snap.settlements if s.get('polity_id') == polity['polity_id']
               and s.get('lon') is not None and s.get('lat') is not None]
        capital = polity.get('capital')
        pick = None
        if isinstance(capital, dict) and not ws.is_missing(capital):
            pick = next((s for s in own if s['settlement_id'] == capital.get('settlement_id')), None)
        if pick is None and own:
            pick = sorted(own, key=lambda s: (s.get('founded') is None, s.get('founded') or 0,
                                              s['settlement_id']))[0]
        if pick is None:
            continue
        cell = cells.get(pick.get('cell_id')) or {}
        terr = terrains.get(pick.get('cell_id')) or {}
        plan.append({'settlement_id': pick['settlement_id'], 'name': pick['name'],
                     'polity_id': polity['polity_id'], 'polity_name': polity['name'],
                     'capital': pick.get('level') == 'capital',
                     'lon': pick['lon'], 'lat': pick['lat'],
                     'cell': {k: cell.get(k) for k in ('elevation_m', 'slope_deg', 'temperature_c',
                                                       'precipitation_mm', 'area_km2')},
                     'terrains': sorted(set(terr.get('terrains') or []) |
                                        set(terr.get('suitable') or []))})
    if len(plan) < 2:
        raise WorldPackageError('地区内能编成城市的聚落不足两座（得到 %d），换一个地区' % len(plan))
    return plan[:5]


def _terrain_kind(terrains):
    have = set(terrains)
    for key, kind in (('mountain', 'mountain'), ('plateau', 'plateau'), ('wetland', 'wetland')):
        if key in have:
            return kind
    if have & DESERT:
        return 'desert'
    if have & FOREST:
        return 'forest'
    if have & {'steppe', 'savanna', 'tundra', 'farmland', 'pasture'}:
        return 'plain'
    return 'unspecified'


# ============================================================== 服务
class WorldPackagePipeline:
    def __init__(self, service):
        self.service = service
        from .background_package import BackgroundPackages
        self.backgrounds = BackgroundPackages(service)

    # ------------------------------------------------------------ 读
    def list(self):
        rows = self.service.store.all(KIND)
        return sorted(rows, key=lambda d: (d['created'], d['id']), reverse=True)

    def get(self, draft_id):
        draft = self.service.store.get(KIND, draft_id)
        if not draft:
            raise WorldPackageError('地区故事包草稿不存在')
        return draft

    def _put(self, draft, expected_revision=None):
        if expected_revision is not None:
            current = self.get(draft['id'])
            if current.get('revision') != expected_revision:
                raise WorldPackageError('草稿已被更新（当前 %s，提交 %s），请刷新后重试'
                                        % (current.get('revision'), expected_revision))
        self.service.store.put(KIND, draft['id'], draft)
        return draft

    @staticmethod
    def _editable(draft):
        if draft.get('status') != 'draft':
            raise WorldPackageError('已确认的草稿不能再改，请重新生成')

    # ------------------------------------------------------------ 1. 候选
    def propose(self, source, region_id=None, setting=None, note=''):
        if not isinstance(source, ws.WorldSource):
            raise WorldPackageError('source 不是 WorldSource 适配器')
        if setting is None and self.service.store.get('pointer', 'package'):
            setting = world_setting.of_story(self.service.runtime.package()['story'])
        setting = world_setting.normalize(setting)
        if not setting:
            raise WorldPackageError('需要世界设定（类型配比与科技 / 魔法档位）才能挑元素')
        if region_id is None:
            regions = source.list_regions()
            if not regions:
                raise WorldPackageError('这个世界没有可选地区')
            region_id = regions[0]['region_id']
        identity = source.identity()
        snap = source.region(region_id).validate()
        mismatch = ws.identity_matches(snap.source, identity)
        if mismatch:
            raise WorldPackageError('快照的来源身份与适配器不一致：%s' % '、'.join(mismatch))
        region_polities = snap.region_polities()
        if not 2 <= len(region_polities) <= 4:
            raise WorldPackageError('首轮只做 2–4 个国家的地区（%s 有 %d 个）'
                                    % (region_id, len(region_polities)))
        terrain_union = sorted(snap.terrain_union())
        candidates = scan_candidates(self.service.elements, setting, terrain_union)
        templates = polity_templates()
        matches = [match_template(p, templates, setting) for p in region_polities]
        names = snap.polity_names()
        events, history_budget = self._fit_history(snap, names)
        notes = list(snap.notes)
        if not snap.has('events'):
            notes.append('引擎没有史事（%s）：历史章节跳过，不让 AI 补写' % snap.events.get('reason'))
        stamp = now()
        draft = {
            'id': uid(), 'schema': SCHEMA, 'status': 'draft', 'stage': 'proposed', 'revision': 1,
            'created': stamp, 'updated': stamp, 'note': str(note or '')[:400],
            'source': copy.deepcopy(identity), 'snapshot_digest': snap.digest(),
            'capabilities': sorted(source.capabilities()),
            'setting': setting,
            'region': {'region_id': snap.region_id, 'name': snap.name, 'bbox': snap.bbox,
                       'polities': snap.polity_list(), 'terrain_union': terrain_union,
                       'missing_fields': dict(snap.missing_fields), 'notes': notes,
                       'counts': {'cells': 0 if not snap.has('cells') else len(snap.cells),
                                  'settlements': 0 if not snap.has('settlements')
                                  else len(snap.settlements),
                                  'events': len(snap.event_list()),
                                  'polities_in_region': len(region_polities)},
                       'missing': [key for key in ws.FIELDS if not snap.has(key)]},
            'candidates': candidates, 'polity_matches': matches,
            'history_input': events, 'history_budget': history_budget,
            'city_plan': city_plan_of(snap),
            'selection': None, 'element_manifest': None, 'element_warnings': [],
            'content': None, 'attempts': {}, 'usage': {}, 'offline': None,
            'validation': None, 'notice': NOTICE, 'confirmed': None,
        }
        return self._put(draft)

    # ------------------------------------------------------------ 作者勾选 → 元素装配
    def select(self, draft_id, refs, *, acknowledge_candidates=False, expected_revision=None):
        if self.get(draft_id).get('target') == 'background':
            return self.backgrounds.select(draft_id, refs, expected_revision,
                                           acknowledge_candidates)
        draft = self.get(draft_id)
        self._editable(draft)
        if acknowledge_candidates is not True:
            raise WorldPackageError('采纳候选资料需要作者显式确认候选状态（acknowledge_candidates=true）')
        refs = list(dict.fromkeys(refs or []))
        if not refs:
            raise WorldPackageError('至少勾选一个元素')
        if len(refs) > MAX_SELECTED:
            raise WorldPackageError('最多勾选 %d 个元素' % MAX_SELECTED)
        pool = {row['ref']: row for row in draft['candidates']['recommended']
                + draft['candidates']['hinted']}
        unknown = [ref for ref in refs if ref not in pool]
        if unknown:
            raise WorldPackageError('只能从候选清单勾选：%s' % '、'.join(unknown[:5]))
        rows = [pool[ref] for ref in refs]
        entries = [{'namespace': row['namespace'], 'element_id': row['element_id'],
                    'version': row['version'], 'state': 'existing',
                    'acknowledge_candidate': True} for row in rows]
        manifest, warnings = self.service.elements.build_manifest(
            entries, note='地区故事包 %s 的元素选择' % draft['region']['region_id'])
        hint_notes = ['%s 越档：%s' % (row['name'], '；'.join(row['tier_conflicts']))
                      for row in rows if row['tier_conflicts']]
        draft.update(stage='selected', selection={'refs': refs, 'elements': rows,
                                                  'tier_notes': hint_notes},
                     element_manifest=manifest, element_warnings=list(warnings) + hint_notes,
                     content=None, validation=None, attempts={}, usage={},
                     revision=draft['revision'] + 1, updated=now())
        return self._put(draft, expected_revision)

    # ------------------------------------------------------------ 2–4. 模型各步
    def _checkers(self, draft, history=None):
        templates = [t['name'] for t in polity_templates()]
        selected = (draft.get('selection') or {}).get('elements') or []
        terms = templates + [row['name'] for row in selected] \
            + [c['name'] for c in draft['city_plan']]
        polities = draft['region']['polities']
        events = draft['history_input']
        history_checker = NarrativeChecker(polities, events, terms)
        cited = set()
        if history:
            cited = {i for s in history['sections'] for i in s['event_ids']}
        setting_checker = NarrativeChecker(polities, [e for e in events if e['event_id'] in cited],
                                           terms)
        return history_checker, setting_checker

    def _validate_all(self, draft, content):
        selected = draft['selection']['elements']
        candidates = draft['candidates']['recommended'] + draft['candidates']['hinted']
        region_polities = [p for p in draft['region']['polities'] if p.get('in_region')]
        history_checker, setting_checker = self._checkers(draft, content['history'])
        input_ids = [e['event_id'] for e in draft['history_input']]
        errors = []
        if draft['history_input']:
            errors += validate_history(content['history'], history_checker)
        elif content['history']['sections']:
            errors.append('引擎没有史事，历史章节必须为空')
        errors += validate_politics(content['politics'], region_polities,
                                    draft['polity_matches'], selected, history_checker, candidates)
        errors += validate_setting(content['setting'], draft['city_plan'], selected, candidates,
                                   setting_checker)
        return errors, input_ids

    def _context_limit(self):
        return self.service.preferences().get('context_chars')

    def _budget(self, system, context):
        limit = self._context_limit()
        if limit and len(system) + len(stable_json(context)) > limit:
            raise WorldPackageError('生成上下文超过预算，请提高设置中的上下文预算')

    @staticmethod
    def _history_context(name, events, polities):
        return {'region': name, 'events': events,
                'polities': [{'polity_id': p['polity_id'], 'name': p['name']} for p in polities]}

    def _fit_history(self, snap, names):
        """按上下文预算挑历史输入：从 MAX_HISTORY_EVENTS 起逐步减少条数，直到放得下。

        只决定**挑哪些**模拟事件（按种类优先级），不改写事件；结果与预算一起记进草稿，
        同一预算下重复生成一致。
        """
        all_events = snap.event_list()
        limit = self._context_limit()
        count = min(MAX_HISTORY_EVENTS, len(all_events))
        while True:
            events = [_event_view(e, names) for e in history_events(all_events, count)]
            size = len(HISTORY_SYSTEM) + len(stable_json(
                self._history_context(snap.name, events, snap.polity_list())))
            if not limit or size <= limit or count <= 1:
                return events, {'context_chars': limit, 'events_total': len(all_events),
                                'events_used': len(events), 'chars': size}
            count = max(1, count - max(1, count // 8))

    async def generate(self, draft_id):
        if self.get(draft_id).get('target') == 'background':
            return await self.backgrounds.generate(draft_id)
        draft = self.get(draft_id)
        self._editable(draft)
        if draft['stage'] not in ('selected', 'generated') or not draft.get('selection'):
            raise WorldPackageError('请先勾选元素（select），再生成历史与设定')
        revision = draft['revision']
        runner = self.service.ai_drafts._run      # 与 ai_drafts 同口径：离线示例 / 在线至多两次
        selected = draft['selection']['elements']
        candidates = draft['candidates']['recommended'] + draft['candidates']['hinted']
        region_polities = [p for p in draft['region']['polities'] if p.get('in_region')]
        events = draft['history_input']
        input_ids = [e['event_id'] for e in events]
        history_checker, _ = self._checkers(draft)
        attempts, usage = {}, {}

        # ---- 写历史
        if events:
            context = self._history_context(draft['region']['name'], events,
                                            draft['region']['polities'])
            self._budget(HISTORY_SYSTEM, context)
            history, attempts['history'], usage['history'], offline = await runner(
                'world_package_history', HISTORY_SYSTEM, context, offline_history(events),
                lambda raw: normalize_history(raw, input_ids),
                lambda content: validate_history(content, history_checker), STEP_TOKENS)
        else:
            history, offline = {'sections': []}, bool(self.service.provider.config()['offline'])
        cited_ids = {i for s in history['sections'] for i in s['event_ids']}
        cited_events = [e for e in events if e['event_id'] in cited_ids]

        # ---- 定政治
        templates = polity_templates()
        context = {'polities': [dict(_polity_brief(p), **{k: m.get(k) for k in
                                                          ('allowed_templates', 'status', 'note')},
                                     default_template=m.get('element_ref'))
                                for p, m in zip(region_polities, draft['polity_matches'])],
                   'templates': [{k: t[k] for k in ('ref', 'name', 'summary', 'forms')}
                                 for t in templates],
                   'selected_elements': [{k: row[k] for k in ('ref', 'name', 'is_race', 'primary')}
                                         for row in selected],
                   'history_events': [{k: e[k] for k in ('event_id', 'year', 'kind', 'actors')}
                                      for e in cited_events]}
        self._budget(POLITICS_SYSTEM, context)
        example = offline_politics(region_polities, draft['polity_matches'], selected, history,
                                   events, templates)
        politics, attempts['politics'], usage['politics'], _ = await runner(
            'world_package_politics', POLITICS_SYSTEM, context, example, normalize_politics,
            lambda content: validate_politics(content, region_polities, draft['polity_matches'],
                                              selected, history_checker, candidates),
            STEP_TOKENS)

        # ---- 写设定与知识点
        _, setting_checker = self._checkers(draft, history)
        context = {'region': {k: draft['region'][k] for k in ('name', 'terrain_union',
                                                               'missing_fields')},
                   'setting': draft['setting'], 'history': history, 'politics': politics,
                   'history_event_ids': sorted(cited_ids),
                   'selected_elements': [{k: row[k] for k in ('ref', 'name', 'primary',
                                                              'terrain_match')}
                                         for row in selected],
                   'city_plan': [{k: c[k] for k in ('settlement_id', 'name', 'polity_name',
                                                    'capital', 'terrains')}
                                 for c in draft['city_plan']]}
        self._budget(SETTING_SYSTEM, context)
        setting, attempts['setting'], usage['setting'], _ = await runner(
            'world_package_setting', SETTING_SYSTEM, context,
            offline_setting(draft['region'], selected, draft['city_plan'], history),
            normalize_setting,
            lambda content: validate_setting(content, draft['city_plan'], selected, candidates,
                                             setting_checker),
            STEP_TOKENS)

        content = {'history': history, 'politics': politics, 'setting': setting}
        errors, _ = self._validate_all(draft, content)
        if errors:                                  # 各步单独通过、合起来不通过：同样零写入
            raise DraftRejected(errors)
        async with self.service.lock:
            current = self.get(draft_id)
            if current.get('revision') != revision or current.get('status') != 'draft':
                raise WorldPackageError('生成期间草稿被改动，结果未写入，请重试')
            stamp = now()
            current.update(stage='generated', content=content, attempts=attempts, usage=usage,
                           offline=offline, revision=revision + 1, updated=stamp,
                           validation={'ok': True, 'errors': [], 'checked_at': stamp,
                                       'history_coverage': history_coverage(history, input_ids)})
            return self._put(current)

    def edit(self, draft_id, content, expected_revision=None):
        if self.get(draft_id).get('target') == 'background':
            return self.backgrounds.edit(draft_id, content, expected_revision)
        """作者改写生成结果：按与生成时相同的规则整体重新校验，不通过就不写。"""
        draft = self.get(draft_id)
        self._editable(draft)
        if draft['stage'] != 'generated':
            raise WorldPackageError('还没有生成结果可改')
        content = dict(draft['content'], **(content or {}))
        input_ids = [e['event_id'] for e in draft['history_input']]
        history, e1 = normalize_history(content['history'], input_ids)
        politics, e2 = normalize_politics(content['politics'])
        setting, e3 = normalize_setting(content['setting'])
        errors = e1 + e2 + e3
        if not errors:
            normalized = {'history': history, 'politics': politics, 'setting': setting}
            errors, _ = self._validate_all(draft, normalized)
        if errors:
            raise DraftRejected(errors)
        stamp = now()
        draft.update(content=normalized, revision=draft['revision'] + 1, updated=stamp,
                     validation={'ok': True, 'errors': [], 'checked_at': stamp,
                                 'history_coverage': history_coverage(history, input_ids)})
        return self._put(draft, expected_revision)

    # ------------------------------------------------------------ 过期判定
    def freshness(self, draft_id, source):
        if self.get(draft_id).get('target') == 'background':
            return self.backgrounds.freshness(draft_id)
        draft = self.get(draft_id)
        mismatch = ws.identity_matches(draft['source'], source.identity())
        digest = None
        if not mismatch:
            digest = source.region(draft['region']['region_id']).digest()
        stale = bool(mismatch) or digest != draft['snapshot_digest']
        return {'stale': stale, 'identity_mismatch': mismatch,
                'snapshot_changed': (digest is not None and digest != draft['snapshot_digest']),
                'recorded': draft['source']}

    # ------------------------------------------------------------ 编译（复用现有）
    def compile(self, draft):
        """草稿 → (story, characters)。复用 ``world_generator.compile_package``。"""
        content = draft['content']
        setting_out, politics = content['setting'], content['politics']
        names = {p['polity_id']: p['name'] for p in draft['region']['polities']}
        templates = {t['ref']: t for t in polity_templates()}
        selected = draft['selection']['elements']
        knowledge = []
        for index, section in enumerate(content['history']['sections']):
            mentioned = [n for n in names.values() if n and n in section['text']]
            knowledge.append({'id': 'history_%02d' % (index + 1), 'title': section['title'],
                              'category': '历史（模拟事件改写）',
                              'keywords': ([section['title']] + mentioned)[:12],
                              'content': section['text'], 'visibility': 'public',
                              'status': '生成草案，作者已确认',
                              'event_ids': list(section['event_ids'])})
        for row in politics['polities']:
            name = names.get(row['polity_id'], row['polity_id'])
            template = templates.get(row['element_ref'])
            lines = [row['summary'], '政府形式：' + row['government']]
            if row['powers']:
                lines.append('主要势力：' + '、'.join(row['powers']))
            for rel in row['relations']:
                lines.append('与%s：%s。%s' % (names.get(rel['polity_id'], rel['polity_id']),
                                              rel['stance'], rel['text']))
            knowledge.append({'id': 'polity_' + _safe_id(row['polity_id']).replace('.', '_'),
                              'title': name, 'category': '国家与政体',
                              'keywords': [name] + ([template['name']] if template else []),
                              'content': '\n'.join(lines)[:3000], 'visibility': 'public',
                              'status': '生成草案，作者已确认',
                              'element_ref': row['element_ref'],
                              'event_ids': sorted({i for rel in row['relations']
                                                   for i in rel['event_ids']})})
        for point in setting_out['knowledge']:
            knowledge.append(dict(point, status='生成草案，作者已确认'))
        view = {'title': setting_out['title'], 'overview': setting_out['overview'],
                'knowledge': knowledge}
        texts = {c['settlement_id']: c for c in setting_out['cities']}
        engine = draft['source'].get('engine')
        cities = []
        for plan in draft['city_plan']:
            text = texts[plan['settlement_id']]
            cell = plan['cell']
            environment = {
                'elevation_m': _clamp(cell.get('elevation_m'), -500, 9000, 200),
                'slope_deg': _clamp(cell.get('slope_deg'), 0, 90, 5),
                'precipitation_mm': _clamp(cell.get('precipitation_mm'), 0, 12000, 650),
                'temperature_c': _clamp(cell.get('temperature_c'), -60, 60, 15),
                'area_km2': _clamp(cell.get('area_km2'), 0.001, 10000000, 1000),
                'source': ('地区快照取样（%s）；淡水、土壤、交通等为默认值，引擎未给出' % engine)[:200]}
            terrain = '产地：' + ('、'.join(TERRAIN_NAMES.get(t, t) for t in plan['terrains'])
                                  or '数据缺失')
            cities.append({'environment': environment, 'name': plan['name'][:80],
                           'region': plan['polity_name'][:80], 'terrain': terrain[:300],
                           'terrain_kind': _terrain_kind(plan['terrains']),
                           'description': text['description'],
                           'faction': plan['polity_name'][:80],
                           'faction_description': text['faction_description'],
                           'coordinates': [plan['lon'], plan['lat']],
                           'event_title': text['event_title'], 'goal': text['goal'],
                           'discovery': text['discovery'], 'secret': text['secret']})
        world = {'cities': cities, 'hero': setting_out['hero'], 'guide': setting_out['guide'],
                 'item_name': setting_out['item_name'],
                 'item_description': setting_out['item_description']}
        story, characters = wg.compile_package(view, world, draft['id'],
                                               manifest=draft.get('element_manifest'))
        base = draft['setting']
        polity_rows = []
        for row in politics['polities']:
            pid = row['polity_id']
            hint = next((p.get('form_hint') for p in draft['region']['polities']
                         if p['polity_id'] == pid), None)
            tags = (['polity:' + hint] if hint in ws.FORM_HINTS else []) + \
                [t for t in (templates.get(row['element_ref']) or {}).get('tags', [])
                 if t.startswith(('tech:', 'magic:'))]
            polity_rows.append({'id': _safe_id(pid), 'name': names.get(pid, pid)[:40],
                                'summary': row['summary'][:400], 'tags': tags[:16],
                                'element_ref': row['element_ref']})
        race_rows = [{'id': _safe_id(row['element_id']), 'name': row['name'][:40], 'summary': '',
                      'tags': [], 'element_ref': row['ref']}
                     for row in selected if row.get('is_race')]
        story['worldview']['setting'] = world_setting.normalize(
            dict(base, polities=polity_rows, races=race_rows, factions=[]))
        story['generator']['world_package'] = {
            'draft_id': draft['id'], 'source': copy.deepcopy(draft['source']),
            'region_id': draft['region']['region_id'], 'snapshot_digest': draft['snapshot_digest'],
            'history_coverage': (draft.get('validation') or {}).get('history_coverage')}
        world_setting.validate(story)
        self.service.runtime.validate_package(story, characters)
        return story, characters

    def confirm(self, draft_id, source, expected_revision=None):
        if self.get(draft_id).get('target') == 'background':
            return self.backgrounds.confirm(draft_id, expected_revision)
        """作者确认：过期就拒绝；否则编译并写入故事包目录（不启用、不改当前世界）。"""
        draft = self.get(draft_id)
        if draft['status'] == 'confirmed':
            return draft
        if draft['stage'] != 'generated':
            raise WorldPackageError('还没有生成结果，不能确认')
        if expected_revision is not None and expected_revision != draft['revision']:
            raise WorldPackageError('草稿已被更新，请刷新后重试')
        fresh = self.freshness(draft_id, source)
        if fresh['stale']:
            raise WorldPackageError('引擎数据已变化，草稿已过期，请重新生成（%s）'
                                    % ('、'.join(fresh['identity_mismatch']) or '地区快照不同'))
        errors, _ = self._validate_all(draft, draft['content'])
        if errors:
            raise DraftRejected(errors)
        story, characters = self.compile(draft)
        rt = self.service.runtime
        folder = '地区_' + draft['id']
        target = rt.library / folder
        stage = rt.library / ('.pending_' + draft['id'])
        if target.exists():
            raise WorldPackageError('目标目录已存在，未覆盖')
        if stage.exists():
            raise WorldPackageError('上次保存未完成，请检查临时目录后重试')
        PackageFiles(stage).write(story)
        atomic_text(rt.character_directory / (characters['id'] + '.json'),
                    json.dumps(characters, ensure_ascii=False, indent=2))
        atomic_text(stage / '生成说明.json', json.dumps({
            'source': draft['source'], 'region': draft['region']['region_id'],
            'snapshot_digest': draft['snapshot_digest'], 'usage': draft['usage'],
            'offline': draft['offline'], 'created': draft['created'],
            'history_coverage': draft['validation'].get('history_coverage')},
            ensure_ascii=False, indent=2))
        atomic_text(stage / '使用说明.md', '# %s\n\n由地区快照 %s 生成并经作者确认。'
                    '在世界创作的故事包列表中点击“启用”后使用。历史段落只改写模拟事件，'
                    '知识点 event_ids 指向来源事件。\n' % (story['title'], draft['region']['region_id']))
        stage.rename(target)
        draft.update(status='confirmed', confirmed={'folder': folder, 'at': now(),
                                                    'story_id': story['id']},
                     revision=draft['revision'] + 1, updated=now())
        return self._put(draft)


def summary(draft):
    """草稿摘要（接口列表与汇报用）。"""
    if draft.get('target') == 'background':
        return {k: copy.deepcopy(draft.get(k)) for k in
                ('id', 'kind', 'target', 'title', 'status', 'stage', 'revision', 'created',
                 'bundle_id', 'year', 'offline', 'published')}
    content = draft.get('content') or {}
    validation = draft.get('validation') or {}
    return {'id': draft['id'], 'status': draft['status'], 'stage': draft['stage'],
            'revision': draft['revision'], 'created': draft['created'],
            'region': {k: draft['region'][k] for k in ('region_id', 'name', 'counts')},
            'source': draft['source'],
            'candidates': draft['candidates']['counts'],
            'selected': len((draft.get('selection') or {}).get('refs') or []),
            'polity_matches': [{k: m.get(k) for k in ('polity_id', 'element_ref', 'status')}
                               for m in draft['polity_matches']],
            'history_sections': len((content.get('history') or {}).get('sections') or []),
            'history_coverage': {k: v for k, v in (validation.get('history_coverage') or {}).items()
                                 if k != 'uncited'},
            'knowledge': len((content.get('setting') or {}).get('knowledge') or []),
            'offline': draft.get('offline'), 'confirmed': draft.get('confirmed')}
