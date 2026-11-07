# -*- coding: utf-8 -*-
"""诗歌创作：给 AI 生成诗歌内容调用的规则层。

数据全部来自元素库（只读）：
* 体裁条目 ``kind:poetry_form``，payload 里的 ``poetry_form`` 字段给出行数、每行字数/音步、格律、
  押韵格式、分节和逐条约束（见 docs/element-catalog/poetry-forms.json）；
* 经典诗歌 ``kind:poem``，payload 里的 ``poem`` 字段给出原文，作为范例（few-shot）。

本模块只负责：列出体裁、把体裁约束与范例拼成给模型的上下文、检查模型返回的结构（行数、
行长、是否空行），不调用模型。调用在 ``app/web.py`` 的 ``/api/inner/poetry/generate``。
检查只做机器能可靠判断的部分：行数、中文每行字数；平仄与英文格律不做机器判断，
只作为约束交给模型，并在结果里如实标为「未机检」。
"""
from __future__ import annotations

import re

FORM_TAG = 'kind:poetry_form'
POEM_TAG = 'kind:poem'
MAX_SCAN = 200
MAX_EXAMPLES = 2
MAX_THEME = 200
MAX_LINES_OUT = 120

SYSTEM = (
    '你是诗人。按给定体裁写一首诗，必须逐条遵守 constraints；行数、每行字数或音步、押韵格式都要符合 form。'
    '范例只用来理解体裁，不得照抄或改写范例的句子。'
    '如果给了 speaker（说话人，例如酒馆里的吟游诗人）和 setting（世界设定），'
    '诗的用词、意象与科技水平都要符合这个人物和世界，不出现超出世界科技档位的事物。'
    '计量单位用公制。只输出 JSON 对象：{"title": 标题, "lines": [每行一个字符串], "notes": 一句话说明你如何满足格律}。'
)

_CJK = re.compile(r'[\u4e00-\u9fff]')
_PUNCT = re.compile(r'[，。、；：！？,.;:!?「」『』“”"\'（）()《》—…\s]')


class PoetryError(ValueError):
    pass


def _payload(item):
    return item.get('payload') or {}


def forms(elements):
    """体裁列表（给界面和模型选用）。``elements`` 是 ElementAssembly。"""
    page = elements.search(tags_any=[FORM_TAG], limit=MAX_SCAN, include_payload=True)
    out = []
    for item in page.get('items', []):
        spec = _payload(item).get('poetry_form')
        if not isinstance(spec, dict):
            continue
        out.append({'id': item['element_id'], 'ref': item['namespace'] + '/' + item['element_id'],
                    'name': item.get('name'), 'summary': item.get('summary') or '',
                    'tradition': spec.get('tradition'), 'language': spec.get('language'),
                    'lines': spec.get('lines'), 'rhyme_scheme': spec.get('rhyme_scheme')})
    out.sort(key=lambda f: (f['tradition'] or '', f['name'] or ''))
    return out


def _find_form(elements, form_id):
    page = elements.search(tags_any=[FORM_TAG], limit=MAX_SCAN, include_payload=True)
    for item in page.get('items', []):
        if item['element_id'] == form_id or item['namespace'] + '/' + item['element_id'] == form_id:
            spec = _payload(item).get('poetry_form')
            if isinstance(spec, dict):
                return item, spec
    raise PoetryError('未知诗歌体裁：%r（先在元素库导入 poetry-forms）' % (form_id,))


def _examples(elements, form_item, spec):
    """同体裁的经典诗歌范例：优先 example_ref，再找 form_ref 指向本体裁的诗。"""
    page = elements.search(tags_any=[POEM_TAG], limit=MAX_SCAN, include_payload=True)
    wanted = spec.get('example_ref') or ''
    hits = []
    for item in page.get('items', []):
        poem = _payload(item).get('poem')
        if not isinstance(poem, dict) or not poem.get('text'):
            continue
        same = poem.get('form_ref') in (form_item['element_id'], form_item['namespace'] + '/' + form_item['element_id'])
        if item['element_id'] == wanted or same:
            hits.append((item['element_id'] != wanted, {
                'title': poem.get('title'), 'author': poem.get('author'), 'era': poem.get('era'),
                'excerpt': bool(poem.get('excerpt')), 'text': poem['text']}))
    hits.sort(key=lambda h: h[0])
    return [h[1] for h in hits[:MAX_EXAMPLES]]


def build_context(elements, form_id, theme, speaker='', mood='', setting=None):
    """给模型的上下文：体裁约束 + 范例 + 主题 / 说话人 / 世界设定。"""
    if not isinstance(theme, str) or not theme.strip():
        raise PoetryError('请给出诗的主题')
    if len(theme) > MAX_THEME or len(speaker or '') > MAX_THEME or len(mood or '') > MAX_THEME:
        raise PoetryError('主题、说话人、情绪各最多 %d 字' % MAX_THEME)
    item, spec = _find_form(elements, form_id)
    ctx = {
        'form': {'name': item.get('name'), 'tradition': spec.get('tradition'), 'language': spec.get('language'),
                 'lines': spec.get('lines'), 'line_pattern': spec.get('line_pattern'), 'meter': spec.get('meter'),
                 'rhyme_scheme': spec.get('rhyme_scheme'), 'stanza': spec.get('stanza')},
        'constraints': list(spec.get('constraints') or []),
        'examples': _examples(elements, item, spec),
        'theme': theme.strip(),
    }
    if speaker:
        ctx['speaker'] = speaker.strip()
    if mood:
        ctx['mood'] = mood.strip()
    if setting:
        ctx['setting'] = setting
    return ctx, spec


def _chars_per_line(spec):
    """中文体裁每行固定字数（从 line_pattern 里读「每句五字」「每句七字」）；读不到返回 None。"""
    text = spec.get('line_pattern') or ''
    m = re.search(r'([五七四六三])\s*字', text)
    return {'三': 3, '四': 4, '五': 5, '六': 6, '七': 7}[m.group(1)] if m else None


def check(raw, spec):
    """把模型输出收敛成固定结构，并做机器能可靠判断的检查。"""
    if not isinstance(raw, dict):
        raise PoetryError('模型没有返回 JSON 对象')
    lines = raw.get('lines')
    if isinstance(lines, str):
        lines = lines.split('\n')
    if not isinstance(lines, list):
        raise PoetryError('模型返回缺少 lines')
    lines = [str(x).strip() for x in lines if str(x).strip()][:MAX_LINES_OUT]
    if not lines:
        raise PoetryError('模型返回了空诗')
    issues, checked = [], []
    want = spec.get('lines')
    if isinstance(want, int):
        checked.append('行数')
        if len(lines) != want:
            issues.append('行数应为 %d，实际 %d' % (want, len(lines)))
    per = _chars_per_line(spec) if spec.get('language') == 'classical_chinese' else None
    if per:
        checked.append('每行字数')
        for i, line in enumerate(lines, 1):
            n = len(_CJK.findall(_PUNCT.sub('', line)))
            if n != per:
                issues.append('第 %d 行应为 %d 字，实际 %d 字' % (i, per, n))
    return {'title': str(raw.get('title') or '')[:60], 'lines': lines, 'notes': str(raw.get('notes') or '')[:300],
            'checked': checked, 'not_checked': ['平仄 / 格律', '押韵'], 'issues': issues, 'ok': not issues}
