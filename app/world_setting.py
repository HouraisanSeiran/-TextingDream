# -*- coding: utf-8 -*-
"""世界设定：类型配比 + 科技 / 魔法档位 + 国家 / 种族 / 势力短表（规范见 docs/world-setting.md）。

存放在故事包 ``story.worldview.setting``。它只驱动**推荐与越档提示**，不是引擎硬规则：
作者仍可手动采纳任何元素。推荐只读元素库（经 ``ElementAssembly.search``），从不写库。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

CATEGORIES_FILE = Path(__file__).resolve().parents[1] / 'docs/element-catalog/world-categories.json'


def categories():
    """大类定义（docs/element-catalog/world-categories.json）。每次读文件，改了不用重启。"""
    data = json.loads(CATEGORIES_FILE.read_text(encoding='utf-8'))
    return data['categories']

GENRES = {
    'western_fantasy': '西幻', 'dark_fantasy': '黑暗奇幻', 'eastern_fantasy': '东方玄幻',
    'xianxia': '仙侠', 'steampunk': '蒸汽朋克', 'historical': '历史', 'real_world': '现实',
    'modern': '近现代（止于二战前）', 'folk_horror': '民俗恐怖',
}
# 5 档，按先后顺序（越档判断按下标）。原有 4 个 id 不变，文艺复兴插在中世纪与蒸汽之间。
TECH = ('classical', 'medieval', 'renaissance', 'steam', 'early_modern')
# 每档：(名称, 说明, 代表性科技 markers)。markers 是「该档出现了什么」的判据，每档 3 项。
TECH_INFO = {
    'classical': ('古典', '青铜—古典铁器时代（约前1200—500）：铁器、战车、帆桨船、水渠与拱券、城邦；没有火药、印刷机、钟表。',
                  ['铁器冶炼', '拱券与水渠', '帆桨船']),
    'medieval': ('中世纪', '约500—1500：重犁与三圃制、水车风车、板甲与城堡、手抄本；没有火药火器、印刷机、远洋航海，更没有蒸汽机、铁路、电报。',
                 ['重犁与三圃制', '水车与风车', '板甲与城堡筑城']),
    'renaissance': ('文艺复兴', '约1500—1700：火绳枪与大炮、活字印刷机、远洋帆船与罗盘导航、机械钟、望远镜；仍靠人力畜力水力风力，没有蒸汽机、铁路、电报。',
                    ['火药火器（火绳枪）', '活字印刷机', '远洋帆船与罗盘导航']),
    'steam': ('蒸汽', '约1700—1880：蒸汽机、机械纺纱机、铁路、工厂、煤气灯、电报、铁甲舰、早期飞艇；没有汽车普及、无线电、飞机。',
              ['蒸汽机', '机械纺纱机', '铁路']),
    'early_modern': ('近现代', '约1880—1939：电网、内燃机、汽车、电话与无线电、飞机、机枪；止于二战前，没有核能、喷气机、电子计算机。',
                     ['电力与电网', '内燃机', '无线电']),
}
# 全部代表性科技 → 所属档位
MARKER_TIER = {m: tier for tier in TECH for m in TECH_INFO[tier][2]}
MAX_MARKERS = 15
MAGIC = ('none', 'rare', 'common', 'abundant')
MAGIC_INFO = {
    'none': ('无魔', '没有可验证的超自然力量；传说、迷信与宗教存在，但不产生实际效果。'),
    'rare': ('稀少', '超自然力量真实存在但罕见、代价高或被隐藏，普通人一生可能只听说过。'),
    'common': ('常见', '魔法是公开行当：有学院、行会和法律管制，城镇里找得到施法者，但需要专门训练。'),
    'abundant': ('丰富', '魔法渗入日常与基础设施：照明、交通、生产都可能依赖它，普通人也会用简单法术或魔法器具。'),
}
LISTS = {'polities': '国家', 'races': '种族', 'factions': '势力'}
POLITY_TAGS = {
    'polity:monarchy': '君主国', 'polity:empire': '帝国', 'polity:republic': '共和国',
    'polity:city_state': '城邦', 'polity:theocracy': '神权国', 'polity:tribal': '部族联盟',
    'polity:merchant': '商业共和',
}
# 推荐分组：组名 → (显示名, 必须带的标签之一)。国家模板、种族各有专属组，
# 其余组排除它们，避免同一条（例如带 tech:* 的国家模板）在多组重复出现。
OWN_GROUP_TAGS = ('kind:polity', 'kind:race')
RECOMMEND_GROUPS = (
    ('polities', '国家与政体', ('kind:polity',)),
    ('races', '种族', ('kind:race',)),
    ('factions', '组织与势力', ('category:organization', 'category:institution')),
    ('powers', '力量体系', ('category:power',)),
    ('tech', '技术与器物', ('tech:classical', 'tech:medieval', 'tech:renaissance', 'tech:steam', 'tech:early_modern')),
    ('places', '地点与经济', ('category:place', 'category:economy')),
)
PER_GROUP = 8

MAX_LIST = 32
MAX_ITEM_TAGS = 16
_ID_RE = re.compile(r'^[a-z0-9][a-z0-9_.-]{0,63}$')
_REF_RE = re.compile(r'^[a-z0-9][a-z0-9_.:-]*/[a-z0-9][a-z0-9_.:-]*$')
_TAG_BAD = re.compile(r'[\s,，]')


class SettingError(ValueError):
    pass


def _text(value, label, limit, empty=True):
    if value is None:
        value = ''
    if not isinstance(value, str):
        raise SettingError(label + '必须是文本')
    value = value.strip()
    if not value and not empty:
        raise SettingError(label + '不能为空')
    if len(value) > limit:
        raise SettingError('%s最多 %d 字' % (label, limit))
    return value


def _tags(value, label):
    if value is None:
        return []
    if not isinstance(value, list):
        raise SettingError(label + '标签必须是列表')
    if len(value) > MAX_ITEM_TAGS:
        raise SettingError('%s标签最多 %d 个' % (label, MAX_ITEM_TAGS))
    out = []
    for tag in value:
        if not isinstance(tag, str) or not tag.strip() or len(tag.strip()) > 40 or _TAG_BAD.search(tag.strip()):
            raise SettingError('%s标签无效：%r（不能为空、不含空格逗号、最多 40 字）' % (label, tag))
        tag = tag.strip()
        if tag not in out:
            out.append(tag)
    return out


def normalize(raw):
    """校验并规范化一份设定；``None`` 表示没有设定。作者手写内容与标签都允许。"""
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise SettingError('世界设定必须是对象')
    genres = []
    for row in raw.get('genres') or []:
        if not isinstance(row, dict) or row.get('tag') not in GENRES:
            raise SettingError('类型配比只能用：' + '、'.join(GENRES))
        weight = row.get('weight', 1)
        if not isinstance(weight, int) or isinstance(weight, bool) or not 1 <= weight <= 3:
            raise SettingError('类型权重必须是 1–3 的整数')
        if any(g['tag'] == row['tag'] for g in genres):
            raise SettingError('类型重复：' + row['tag'])
        genres.append({'tag': row['tag'], 'weight': weight})
    tech = raw.get('tech') or None
    if tech is not None and tech not in TECH:
        raise SettingError('科技档位只能是：' + ' / '.join(TECH))
    magic = raw.get('magic') or None
    if magic is not None and magic not in MAGIC:
        raise SettingError('魔法档位只能是：' + ' / '.join(MAGIC))
    markers = raw.get('tech_markers')
    if markers is not None:
        if not isinstance(markers, list):
            raise SettingError('代表性科技必须是列表')
        picked_markers = []
        for m in markers:
            if not isinstance(m, str) or m not in MARKER_TIER:
                raise SettingError('代表性科技只能取自各档定义：%r' % (m,))
            if m not in picked_markers:
                picked_markers.append(m)
        markers = picked_markers
    known = {c['id'] for c in categories()}
    picked = []
    for cid in raw.get('categories') or []:
        if cid not in known:
            raise SettingError('未知大类：%r' % (cid,))
        if cid not in picked:
            picked.append(cid)
    result = {'genres': genres, 'categories': picked, 'tech': tech, 'magic': magic,
              'note': _text(raw.get('note'), '设定说明', 1200)}
    if markers is not None:
        # 可选字段：没写就不出现，老设定规范化结果不变。
        result['tech_markers'] = markers
    for key, label in LISTS.items():
        rows = raw.get(key) or []
        if not isinstance(rows, list):
            raise SettingError(label + '必须是列表')
        if len(rows) > MAX_LIST:
            raise SettingError('%s最多 %d 项' % (label, MAX_LIST))
        seen, items = set(), []
        for row in rows:
            if not isinstance(row, dict):
                raise SettingError(label + '条目必须是对象')
            item_id = row.get('id')
            if not isinstance(item_id, str) or not _ID_RE.match(item_id):
                raise SettingError('%s ID 无效：%r（小写字母、数字、_ . -）' % (label, item_id))
            if item_id in seen:
                raise SettingError('%s ID 重复：%s' % (label, item_id))
            seen.add(item_id)
            ref = row.get('element_ref') or None
            if ref is not None and (not isinstance(ref, str) or not _REF_RE.match(ref)):
                raise SettingError('%s引用格式应为 namespace/element_id：%r' % (label, ref))
            items.append({'id': item_id, 'name': _text(row.get('name'), label + '名称', 40, empty=False),
                          'summary': _text(row.get('summary'), label + '说明', 400),
                          'tags': _tags(row.get('tags'), label), 'element_ref': ref})
        result[key] = items
    return result


def of_story(story):
    return ((story or {}).get('worldview') or {}).get('setting')


def validate(story):
    """故事包提交时调用：没有设定是合法的（老包不受影响）。"""
    setting = of_story(story)
    if setting is not None:
        normalize(setting)


def tier_from_markers(present):
    """由已出现的代表性科技推断档位：「该档及以下所有档的代表科技都已出现」的最高档。

    只用于判定与前端高亮，不强制作者使用。第一档的代表科技没凑齐时返回 None；
    不认识的名称忽略。
    """
    have = {m for m in present or () if m in MARKER_TIER}
    best = None
    for tier in TECH:
        if all(m in have for m in TECH_INFO[tier][2]):
            best = tier
        else:
            break
    return best


def tier_of(tags, prefix, order):
    """元素标签里该维度的最高档位下标；没有标签返回 None。"""
    hits = [order.index(t[len(prefix):]) for t in tags or () if t.startswith(prefix) and t[len(prefix):] in order]
    return max(hits) if hits else None


def conflicts(tags, setting):
    """元素相对世界设定的越档说明列表（空 = 不越档）。档位未设定时不判断。"""
    out = []
    if not setting:
        return out
    if setting.get('tech'):
        level = tier_of(tags, 'tech:', TECH)
        if level is not None and level > TECH.index(setting['tech']):
            out.append('需要科技「%s」，世界是「%s」' % (TECH_INFO[TECH[level]][0], TECH_INFO[setting['tech']][0]))
    if setting.get('magic'):
        level = tier_of(tags, 'magic:', MAGIC)
        if level is not None and level > MAGIC.index(setting['magic']):
            out.append('需要魔法「%s」，世界是「%s」' % (MAGIC_INFO[MAGIC[level]][0], MAGIC_INFO[setting['magic']][0]))
    return out


def recommend(elements, setting, adopted=()):
    """按设定从元素库挑候选，分组返回。``elements`` 是 ``ElementAssembly``（只读查询）。

    打分 = 命中的类型权重之和；越档条目排除（单独计数）；已采纳的标记出来但不重复推荐。
    没有类型配比时按组标签直接取，不做类型过滤。
    """
    setting = normalize(setting) or {'genres': [], 'tech': None, 'magic': None}
    weights = {'genre:' + g['tag']: g['weight'] for g in setting['genres']}
    adopted = set(adopted or ())
    groups = []
    for key, title, group_tags in RECOMMEND_GROUPS:
        page = elements.search(tags_any=list(group_tags), limit=200)
        scored, skipped = [], 0
        for item in page.get('items', []):
            tags = item.get('tags') or []
            if key not in ('polities', 'races') and any(t in tags for t in OWN_GROUP_TAGS):
                continue
            if weights:
                score = sum(w for tag, w in weights.items() if tag in tags)
                if not score:
                    continue
            else:
                score = 0
            if conflicts(tags, setting):
                skipped += 1
                continue
            ref = item['namespace'] + '/' + item['element_id']
            scored.append({'ref': ref, 'namespace': item['namespace'], 'element_id': item['element_id'],
                           'version': item.get('version'),
                           'name': item.get('name'), 'summary': item.get('summary') or '',
                           'tags': [t for t in tags if t.startswith(('genre:', 'tech:', 'magic:', 'kind:', 'polity:'))],
                           'score': score, 'adopted': ref in adopted})
        scored.sort(key=lambda row: (row['adopted'], -row['score'], row['name'] or ''))
        groups.append({'id': key, 'title': title, 'items': scored[:PER_GROUP],
                       'more': max(0, len(scored) - PER_GROUP), 'skipped_by_tier': skipped})
    return {'setting': setting, 'groups': groups}


TECH_TAGS = tuple('tech:' + t for t in TECH)
MAX_CATEGORY_SCAN = 200


def is_technology(tags):
    """技术元素 = 带 tech:* 档位标签、且不是国家 / 种族模板（它们也可能带 tech:* 表示最早档位）。"""
    return any(t in TECH_TAGS for t in tags) and not any(t in OWN_GROUP_TAGS for t in tags)


def category_elements(elements, setting):
    """选中的大类 → 纳入的元素。

    * 大类元素：命中任一所选大类的 tags_any，且不越科技 / 魔法档位；
    * 技术元素（带 tech:* 且不是国家 / 种族模板）不属于大类，只按科技档位单独纳入：没设科技档位时不纳入；
    * 返回按大类分组的条目与越档排除数，供作者确认后采纳。
    """
    setting = normalize(setting) or {'categories': [], 'tech': None, 'magic': None}
    defs = {c['id']: c for c in categories()}
    groups, seen = [], set()
    for cid in setting['categories']:
        cat = defs[cid]
        page = elements.search(tags_any=list(cat['tags_any']), limit=MAX_CATEGORY_SCAN)
        rows, skipped = [], 0
        for item in page.get('items', []):
            tags = item.get('tags') or []
            if is_technology(tags):
                continue
            ref = item['namespace'] + '/' + item['element_id']
            if conflicts(tags, setting):
                skipped += 1
                continue
            rows.append(_brief(item, ref, ref in seen))
            seen.add(ref)
        groups.append({'id': cid, 'title': cat['label'], 'items': rows,
                       'total': page.get('total', len(rows)), 'skipped_by_tier': skipped})
    tech_rows, tech_skipped = [], 0
    if setting.get('tech'):
        page = elements.search(tags_any=list(TECH_TAGS), limit=MAX_CATEGORY_SCAN)
        for item in page.get('items', []):
            tags = item.get('tags') or []
            if not is_technology(tags):
                continue
            ref = item['namespace'] + '/' + item['element_id']
            if conflicts(tags, setting):
                tech_skipped += 1
                continue
            tech_rows.append(_brief(item, ref, ref in seen))
            seen.add(ref)
    groups.append({'id': 'technology', 'title': '科技（按档位）', 'items': tech_rows,
                   'total': len(tech_rows) + tech_skipped, 'skipped_by_tier': tech_skipped})
    return {'setting': setting, 'groups': groups, 'unique': len(seen)}


MAX_SNAPSHOT = 400


def snapshot(resolved):
    """大类元素快照：ref + 版本 + 名称 + 摘要 + 所属大类，去重，有上限。"""
    out = []
    for group in resolved.get('groups', []):
        for item in group['items']:
            if item.get('duplicate'):
                continue
            out.append({'ref': item['ref'], 'version': item.get('version'), 'name': item.get('name'),
                        'summary': (item.get('summary') or '')[:200], 'group': group['id']})
    if len(out) > MAX_SNAPSHOT:
        raise SettingError('所选大类共 %d 条元素，超过上限 %d：请少选几个大类' % (len(out), MAX_SNAPSHOT))
    return out


def _brief(item, ref, duplicate):
    return {'ref': ref, 'namespace': item['namespace'], 'element_id': item['element_id'],
            'version': item.get('version'), 'name': item.get('name'),
            'summary': item.get('summary') or '', 'duplicate': duplicate,
            'tags': [t for t in item.get('tags') or [] if t.startswith(('genre:', 'tech:', 'magic:', 'kind:', 'polity:'))]}


def options():
    """界面用的选项与说明（缺库时也能渲染设定表单）。"""
    return {
        'genres': [{'id': k, 'label': v} for k, v in GENRES.items()],
        'categories': [{'id': c['id'], 'label': c['label'], 'description': c.get('description', '')}
                       for c in categories()],
        'tech': [{'id': k, 'label': TECH_INFO[k][0], 'description': TECH_INFO[k][1],
                  'markers': list(TECH_INFO[k][2])} for k in TECH],
        'magic': [{'id': k, 'label': MAGIC_INFO[k][0], 'description': MAGIC_INFO[k][1]} for k in MAGIC],
        'lists': [{'id': k, 'label': v} for k, v in LISTS.items()],
        'polity_tags': [{'id': k, 'label': v} for k, v in POLITY_TAGS.items()],
    }


def prompt_block(story):
    """进入叙事上下文的设定摘要（短）；没有设定返回 None。"""
    setting = of_story(story)
    if not setting:
        return None
    setting = normalize(setting)
    block = {}
    if setting['categories']:
        labels = {c['id']: c['label'] for c in categories()}
        block['categories'] = '、'.join(labels[c] for c in setting['categories'])
    if setting['genres']:
        block['genres'] = '、'.join(GENRES[g['tag']] + ('（主体）' if g['weight'] == 3 else '')
                                   for g in sorted(setting['genres'], key=lambda g: -g['weight']))
    if setting['categories']:
        labels = {c['id']: c['label'] for c in categories()}
        block['categories'] = '、'.join(labels[c] for c in setting['categories'])
    if setting['tech']:
        block['tech'] = TECH_INFO[setting['tech']][0] + '：' + TECH_INFO[setting['tech']][1]
    if setting['magic']:
        block['magic'] = MAGIC_INFO[setting['magic']][0] + '：' + MAGIC_INFO[setting['magic']][1]
    for key in LISTS:
        rows = [r['name'] + ('：' + r['summary'] if r['summary'] else '') for r in setting[key][:8]]
        if rows:
            block[key] = rows
    if setting['note']:
        block['note'] = setting['note'][:400]
    return block or None
