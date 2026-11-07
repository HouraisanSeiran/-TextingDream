# -*- coding: utf-8 -*-
"""世界观生成 agent：所选大类的元素 + 世界设定 → 一份世界观草稿，作者审阅后再采纳。

流程（与里层草稿一致，不直接改故事包）：
1. ``generate``：把设定（大类 / 科技与魔法档位 / 国家种族势力 / 补充说明）和大类元素的
   名称+摘要（有界）交给模型，要求返回 JSON 世界观；结果存为 ``worldview_draft``。
2. ``adopt``：作者确认后，把草稿写进 ``story.worldview``（保留 ``setting`` 与大类快照），
   提交为故事包新版本。已有旅程仍绑定旧版本。

离线模式不发请求，直接报错提示配置模型——不拿占位文本冒充生成结果。
"""
from __future__ import annotations

import json

from . import world_setting

MAX_CONTEXT_ELEMENTS = 80
SUMMARY_CHARS = 80
LIST_KEYS = ('polities', 'races', 'factions')

SYSTEM = (
    '你是世界观设计助手。根据作者给出的世界设定与可用元素，写一份连贯的世界观。\n'
    '硬性要求：\n'
    '1. 只能使用不超过给定科技档位与魔法档位的事物；科技止于二战前。\n'
    '2. 作者已写的国家 / 种族 / 势力必须保留原名与原意，可以补充细节，不得删改或改名。\n'
    '3. 优先从「可用元素」里取材并在 used_elements 里列出所用元素的 ref；不要编造元素 ref。\n'
    '4. 不同大类混搭时，要说明它们在这个世界里如何共存（例如魔法与蒸汽机的关系）。\n'
    '5. 只输出 JSON 对象，字段：premise(字符串，200字内), laws(字符串数组，3-6条世界规则),'
    ' chronology(数组，每项{era, summary}，3-6项), geography({overview, regions:[{name, summary}]}),'
    ' cultures(数组，每项{name, summary}), polities / races / factions(数组，每项{name, summary}),'
    ' used_elements(字符串数组)。全部用中文。'
)


class AgentError(ValueError):
    pass


def build_context(setting, resolved):
    """给模型的上下文：设定说明 + 有界的元素摘要。``resolved`` 是 category_elements 的结果。"""
    setting = world_setting.normalize(setting)
    cats = {c['id']: c for c in world_setting.categories()}
    rows = []
    for group in resolved.get('groups', []):
        for item in group['items']:
            if item.get('duplicate'):
                continue
            rows.append({'ref': item['ref'], 'group': group['title'], 'name': item['name'],
                         'summary': (item.get('summary') or '')[:SUMMARY_CHARS]})
    # 每组轮流取，避免第一个大类把名额占满。
    by_group = {}
    for row in rows:
        by_group.setdefault(row['group'], []).append(row)
    picked = []
    while len(picked) < MAX_CONTEXT_ELEMENTS and any(by_group.values()):
        for key in list(by_group):
            if by_group[key] and len(picked) < MAX_CONTEXT_ELEMENTS:
                picked.append(by_group[key].pop(0))
    info = world_setting.TECH_INFO.get(setting['tech']) if setting['tech'] else None
    magic = world_setting.MAGIC_INFO.get(setting['magic']) if setting['magic'] else None
    return {
        'categories': [{'label': cats[c]['label'], 'description': cats[c]['description']}
                       for c in setting['categories']],
        'tech': {'label': info[0], 'description': info[1]} if info else '未限定',
        'magic': {'label': magic[0], 'description': magic[1]} if magic else '未限定',
        'author_note': setting['note'],
        'author_lists': {k: [{'name': r['name'], 'summary': r['summary'], 'tags': r['tags']}
                             for r in setting[k]] for k in LIST_KEYS},
        'available_elements': picked,
        'available_total': len(rows),
    }


def _named_list(value, label, limit=24):
    if not isinstance(value, list):
        raise AgentError('模型返回的 %s 不是列表' % label)
    out = []
    for row in value[:limit]:
        if isinstance(row, dict) and isinstance(row.get('name'), str) and row['name'].strip():
            out.append({'name': row['name'].strip()[:40], 'summary': str(row.get('summary') or '')[:600]})
    return out


def validate_result(raw, setting, allowed_refs):
    """把模型输出收敛成固定结构；检查作者写的条目没被丢掉，ref 不是编的。"""
    if not isinstance(raw, dict):
        raise AgentError('模型没有返回 JSON 对象')
    premise = raw.get('premise')
    if not isinstance(premise, str) or not premise.strip():
        raise AgentError('模型返回缺少 premise')
    laws = [str(x)[:300] for x in raw.get('laws') or [] if isinstance(x, str) and x.strip()][:8]
    chronology = [{'era': str(r.get('era') or '')[:40], 'summary': str(r.get('summary') or '')[:600]}
                  for r in raw.get('chronology') or [] if isinstance(r, dict)][:8]
    geo = raw.get('geography') if isinstance(raw.get('geography'), dict) else {}
    geography = {'overview': str(geo.get('overview') or '')[:800],
                 'regions': _named_list(geo.get('regions') or [], 'regions')}
    result = {'premise': premise.strip()[:400], 'laws': laws, 'chronology': chronology,
              'geography': geography, 'cultures': _named_list(raw.get('cultures') or [], 'cultures')}
    warnings = []
    for key in LIST_KEYS:
        rows = _named_list(raw.get(key) or [], key)
        names = {r['name'] for r in rows}
        for mine in setting[key]:
            if mine['name'] not in names:
                # 作者条目必须保留：模型漏了就补回作者原文，并提示。
                rows.append({'name': mine['name'], 'summary': mine['summary']})
                warnings.append('模型漏掉了作者写的%s「%s」，已按原文补回' % (world_setting.LISTS[key], mine['name']))
        result[key] = rows
    refs = [r for r in raw.get('used_elements') or [] if isinstance(r, str)]
    result['used_elements'] = [r for r in refs if r in allowed_refs][:MAX_CONTEXT_ELEMENTS]
    unknown = [r for r in refs if r not in allowed_refs]
    if unknown:
        warnings.append('模型引用了 %d 个不在可用元素里的 ref，已忽略' % len(unknown))
    return result, warnings


def merge_into_worldview(worldview, result):
    """采纳：世界观正文换成草稿，setting 与大类快照保持不动。"""
    merged = dict(worldview or {})
    merged['premise'] = result['premise']
    merged['laws'] = result['laws']
    merged['chronology'] = result['chronology']
    merged['geography'] = result['geography']
    merged['cultures'] = result['cultures']
    merged['generated'] = {k: result[k] for k in LIST_KEYS + ('used_elements',)}
    return merged


def context_size(context):
    return len(SYSTEM) + len(json.dumps(context, ensure_ascii=False))
