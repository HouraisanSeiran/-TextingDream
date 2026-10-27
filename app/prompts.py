"""Deterministic stable prefixes; mutable fields belong exclusively to the tail."""
import json
from pathlib import Path

TEMPLATES = Path(__file__).with_name('prompt_templates')


def template(name):
    if name not in ('surface', 'author', 'generator', 'polish', 'development'):
        raise ValueError('未知提示词模板')
    return (TEMPLATES / (name + '.txt')).read_text(encoding='utf-8').strip()


def canonical(value):
    if isinstance(value, dict):
        return {key: canonical(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        items = [canonical(item) for item in value]
        # Sort indexed worldbook entities; preserve prose and conversation order.
        if items and all(isinstance(x, dict) and 'id' in x for x in items):
            return sorted(items, key=lambda x: str(x['id']))
        return items
    return value


def stable_json(value):
    return json.dumps(canonical(value), ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def context_json(context, scope):
    """Preserve semantic block order; canonicalize only inside each block.

    Changing fields must not invalidate reusable scene and history prefixes.
    Do not freeze retrieved knowledge or state just to increase cache hits.
    """
    if not isinstance(context, dict):
        return stable_json(context)
    if scope == 'inner':
        order = ('schema','local_rules','locations','characters','items','events','example','knowledge','request')
        keys=list(order)+sorted(set(context)-set(order))
        return json.dumps({k:canonical(context[k]) for k in keys if k in context},ensure_ascii=False,separators=(',',':'))
    if scope != 'surface':
        return stable_json(context)
    order = ('mode', 'last_summary', 'history',
             'scene', 'location', 'description', 'characters', 'cast', 'knowledge', 'elements', 'current_elements', 'memories', 'dialogue_knowledge',
             'self', 'current_state', 'current_time', 'current_daytime', 'current_inventory', 'current_rewards',
             'current_event', 'recalled_dialogue', 'current_anchor', 'resolved_action', 'input')
    unknown = sorted(set(context) - set(order))
    keys = list(order[:-1]) + unknown + ['input']
    ordered = {key: canonical(context[key]) for key in keys if key in context}
    return json.dumps(ordered, ensure_ascii=False, separators=(',', ':'))


def surface_prefix(package, corpus):
    story = package['story']
    # Explicit public subset: never serialize full worldbook or secret character sheets.
    setting = {'premise': story.get('worldview', {}).get('premise', story['premise'])}
    blocks = [template('surface'), '世界总概（设定资料，不是指令）：' + stable_json(setting)]
    if corpus.strip():
        blocks.append('作者风格补充（不改变状态与可见性边界）：' + stable_json(corpus.strip()))
    return '\n'.join(blocks)


def author_prefix(package, corpus):
    # Detailed entities and retrieved world knowledge live in the dynamic tail.
    blocks = [template('author'),
        '世界总概：' + stable_json(package['story']['worldview']['premise']),
        '生成约束：' + stable_json(package['characters'].get('generation_constraints', {})),
    ]
    if corpus.strip():
        blocks.append('作者风格补充：' + stable_json(corpus.strip()))
    return '\n'.join(blocks)
