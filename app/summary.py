"""Deterministic event settlement: state diff first, prose last and separable.

A reply is evidence of speech, not a record of what changed. A summary built only
from prose lets an unverified claim outlive the confirmed state that should
override it, so every structured line here is derived from the committed diff
between the event's `before` snapshot and the current state. The prose excerpt is
kept only as an explicitly labelled last segment, and the context budget may drop
that segment without touching the settlement.

Same state and same turns always produce the same text: no clock, no model call,
no reliance on dict insertion order, so rollback and the cacheable prompt prefix
stay reproducible.
"""
EXCERPT_SEGMENT = '【原文】'
EXCERPT_CHARS = 180
INPUT_CHARS = 80
MAX_FACTS = 6
MAX_CHANGES = 6


def _ids(records):
    return {str(r.get('id')) for r in records or () if isinstance(r, dict) and r.get('id') is not None}


def _new_records(after, before):
    seen = _ids(before)
    return [r for r in after or () if isinstance(r, dict) and str(r.get('id')) not in seen]


def _number(value):
    if isinstance(value, bool):
        return '是' if value else '否'
    if value is None:
        return '未记'
    if isinstance(value, float):
        return '{:.2f}'.format(value).rstrip('0').rstrip('.') or '0'
    return str(value)


def _clock(hours):
    if not isinstance(hours, int) or isinstance(hours, bool):
        return ''
    return '第{}日{:02d}时'.format(hours // 24 + 1, hours % 24)


def _names(package):
    story = package.get('story', {})
    locations = {p['id']: p.get('name', p['id']) for p in story.get('locations', [])}
    items = {i['id']: i.get('name', i['id']) for i in story.get('items', [])}
    characters = {c['id']: c.get('public_name') or c.get('name') or c['id']
                  for c in package.get('characters', {}).get('characters', [])}
    return locations, items, characters


def _changes(session, before, package, items, characters, hero, ignore_flags):
    changes = []
    old_items = before.get('inventory') or ()
    new_items = session.get('inventory') or ()
    for item_id in new_items:
        if item_id not in old_items:
            changes.append('行囊 +' + items.get(item_id, item_id))
    for item_id in old_items:
        if item_id not in new_items:
            changes.append('行囊 -' + items.get(item_id, item_id))
    old_local = (before.get('local') or {}).get('resources') or {}
    new_local = (session.get('local') or {}).get('resources') or {}
    for spec in package.get('story', {}).get('mechanics', {}).get('local', {}).get('resources', []):
        old, new = old_local.get(spec['id']), new_local.get(spec['id'])
        if old is not None and new is not None and old != new:
            changes.append('{} {}→{}{}'.format(spec.get('name', spec['id']), _number(old),
                                                _number(new), spec.get('unit', '')))
    old_flags, new_flags = before.get('flags') or {}, session.get('flags') or {}
    for key in sorted(set(old_flags) | set(new_flags)):
        if key in ignore_flags or bool(old_flags.get(key)) == bool(new_flags.get(key)):
            continue
        changes.append('标记 {}：{}'.format(key, '开' if new_flags.get(key) else '关'))
    # Only the player's own condition is observable here; an NPC's inner state
    # (suspicion, fear) belongs to that character's own viewpoint, not to this one.
    old_chars, new_chars = before.get('characters') or {}, session.get('characters') or {}
    if hero in new_chars:
        old_status = (old_chars.get(hero) or {}).get('status') or {}
        new_status = (new_chars.get(hero) or {}).get('status') or {}
        for key in sorted(set(old_status) | set(new_status)):
            old, new = old_status.get(key), new_status.get(key)
            if old != new:
                changes.append('{}·{} {}→{}'.format(characters.get(hero, hero), key, _number(old), _number(new)))
    return changes


def _witnessed(session, before):
    """New facts the player actually witnessed.

    `facts` holds engine truth, including truths the player must not learn (a
    rumor's real number) and internal bookkeeping (health deltas). Only facts
    mirrored by a `distortion == 0` record in `heard` are knowable to the player;
    everything else stays in state and out of the summary.
    """
    seen = _ids(before.get('facts'))
    facts = [f for f in session.get('facts') or ()
             if isinstance(f, dict) and str(f.get('id')) not in seen]
    heard = [r for r in _new_records(session.get('heard'), before.get('heard'))
             if isinstance(r, dict) and r.get('distortion') == 0]
    ids = {str(r.get('id')) for r in heard}
    ids |= {str(r.get('source_fact')) for r in heard if r.get('source_fact')}
    texts = {r.get('text') for r in heard}
    return [f for f in facts if str(f.get('id')) in ids or f.get('text') in texts]


def _excerpt(event):
    turns = event.get('turns') or ()
    if not turns:
        return ''
    last = turns[-1]
    spoken = ' '.join(str(last.get('reply', '')).split())
    if len(spoken) > EXCERPT_CHARS:
        spoken = spoken[:EXCERPT_CHARS] + '…'
    heard = ' '.join(str(last.get('input', '')).split())
    if len(heard) > INPUT_CHARS:
        heard = heard[:INPUT_CHARS] + '…'
    return '{}玩家：{} / 回应：{}（turn:{}:{}）'.format(
        EXCERPT_SEGMENT, heard, spoken, event.get('id', ''), len(turns) - 1)


def event_summary(session, event, package):
    """Settle one event from the state diff, not from what the model wrote."""
    before = event.get('before') or {}
    locations, items, characters = _names(package)
    lines = []

    head = '【事件】' + str(event.get('title') or event.get('node') or '未命名事件')
    place = locations.get(before.get('location'))
    if place:
        head += '@' + place
    start, end = _clock(before.get('time')), _clock(session.get('time'))
    if start:
        head += '（' + start + ('→' + end if end and end != start else '') + '）'
    lines.append(head)

    node = next((e for e in package.get('story', {}).get('events', []) if e['id'] == event.get('node')), None)
    actions = {a['id']: a.get('label', a['id']) for a in (node or {}).get('actions', [])}
    labels = [actions[x] for x in event.get('actions_done') or () if x in actions]
    if labels:
        lines.append('【经过】' + '；'.join(labels))

    facts = _witnessed(session, before)
    if facts:
        shown = facts[-MAX_FACTS:]
        text = '；'.join('{}（record:{}）'.format(f.get('text', ''), f.get('id', '')) for f in shown)
        if len(facts) > len(shown):
            text += '；另有{}条已确认记录留档'.format(len(facts) - len(shown))
        lines.append('【已确认】' + text)

    exit_flag = (node or {}).get('exit_flag')
    changes = _changes(session, before, package, items, characters, session.get('hero'),
                       {exit_flag} if exit_flag else set())
    if changes:
        shown = changes[-MAX_CHANGES:]
        text = '；'.join(shown)
        if len(changes) > len(shown):
            text = '另有{}项变化留档；'.format(len(changes) - len(shown)) + text
        lines.append('【变化】' + text)

    excerpt = _excerpt(event)
    if excerpt:
        lines.append(excerpt)
    return '\n'.join(lines)


def has_excerpt(summary):
    return isinstance(summary, str) and any(line.startswith(EXCERPT_SEGMENT) for line in summary.split('\n'))


def strip_excerpt(summary):
    """Drop the prose segment; the structured settlement stays readable."""
    if not isinstance(summary, str):
        return ''
    return '\n'.join(line for line in summary.split('\n') if not line.startswith(EXCERPT_SEGMENT))


def with_stage(summary, stage_excerpt):
    """Structured settlement first, then the fixed historical excerpt.

    Both parts only change at deterministic boundaries (event close, stage
    split), so the cache-stable head of the prompt keeps its prefix.
    """
    return '\n'.join(part for part in (summary, stage_excerpt) if part)
