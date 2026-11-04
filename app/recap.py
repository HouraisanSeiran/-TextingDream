"""Read-only, player-safe journey recaps derived from existing saves."""
from collections import Counter
from copy import deepcopy

from . import endings, local_rules, rewards

MAX_CHOICES = 30


def _holdings(story, session):
    view = rewards.public_state(session, story) or {}
    names = {item['id']: item['name'] for item in story.get('items', [])}
    items = Counter(names[i] for i in session.get('inventory', []) if i in names)
    for item in view.get('items', []):
        items[item['label']] += item.get('quantity', 1)
    return {'wallet': view.get('wallet', []),
            'resources': local_rules.view(session, story).get('resources', []),
            'items': dict(items)}


def build(story, session, characters=None, limit=MAX_CHOICES):
    """Never expose raw snapshots, conditions, beliefs or development scores.

    Archives do not persist per-action times. Their time ranges are deliberately
    reported as ranges; missing precision is not reconstructed from prose.
    """
    events = {e['id']: e for e in story.get('events', [])}
    episodes = list(session.get('archives', []))
    if session.get('active'):
        episodes.append(session['active'])
    opening = episodes[0].get('before') if episodes else None
    if opening is None:
        opening = {'inventory': [], 'time': 8}
    timeline = []
    for episode in episodes:
        before = episode.get('before', {})
        after = episode.get('after', session)
        audits = after.get('checks', [])[len(before.get('checks', [])):]
        checks = iter(audits)
        actions = {a['id']: a for a in events.get(episode.get('node'), {}).get('actions', [])}
        checked_count = sum(bool(actions.get(aid, {}).get('check'))
                            for aid in episode.get('actions_done', []))
        for aid in episode.get('actions_done', []):
            action = actions.get(aid)
            # Dynamic actions have no persisted public label in legacy archives.
            if action is None:
                continue
            check = None
            if action.get('check'):
                seed = f"{session.get('seed')}:{episode.get('node')}:{aid}"
                check = next((r for r in audits if r.get('seed') == seed), None)
                # Older test/import audits may lack seeds; only align when the
                # complete checked-action count agrees, never across dynamic gaps.
                if check is None and len(audits) == checked_count:
                    candidate = next(checks, None)
                    if candidate and not candidate.get('seed') and candidate.get('attribute') == action['check']['attribute']:
                        check = candidate
            timeline.append({'label': action['label'],
                             'time': None,
                             'time_range': {'from': before.get('time'), 'to': after.get('time')},
                             'check': ({'attribute': check.get('attribute'),
                                        'success': check.get('success')} if check else None)})
    known = session.get('heard', [])
    names = {c['id']: c.get('public_name') or c['name']
             for c in (characters or {}).get('characters', [])}
    remembered = []
    # Public reaction receipts are copied from heard, never from private NPC state.
    cfg = (story.get('mechanics', {}).get('scene_judgment') or {}).get('actors', {})
    for judgment in session.get('scene_judgments', []):
        for reaction in judgment.get('reactions', []):
            cid, choice = reaction['character'], reaction['choice']
            option = cfg.get(cid, {}).get('choices', {}).get(choice, {})
            for record in known:
                if (record.get('source') == 'scene-reaction:' + choice
                        and record.get('text') == option.get('line')):
                    row = {'name': names.get(cid, '人物'), 'kind': 'reaction',
                           'text': record['text'], 'time': record.get('time')}
                    if row not in remembered:
                        remembered.append(row)
    for record in session.get('beliefs', []):
        if record.get('kind') != 'npc_event':
            continue
        disclosed = ('player' in record.get('known_by', []) or any(
            r.get('character') == record.get('character')
            and r.get('source') == record.get('source') and r.get('text') == record.get('text')
            for r in known))
        if disclosed:
            remembered.append({'name': names.get(record.get('character'), '人物'),
                               'kind': 'witness', 'text': record['text'],
                               'time': record.get('time')})
    ending = session.get('ending') or endings.resolve(session, story)
    public_ending = ({k: ending[k] for k in ('title', 'summary')}
                     if ending else {'title': '进行中', 'summary': '旅程还在继续。'})
    cfg_endings = endings.config(story)
    seen = {ending['id']} if ending else set()
    unseen = sum(e.id not in seen for e in cfg_endings.endings) if cfg_endings else 0
    return deepcopy({'session_id': session['id'], 'ending': public_ending,
                     'timeline': timeline[-max(1, min(int(limit), MAX_CHOICES)):],
                     'timeline_total': len(timeline), 'remembered': remembered[-30:],
                     'holdings': {'opening': _holdings(story, opening),
                                  'now': _holdings(story, session)},
                     'unseen_endings': unseen,
                     'note': '时间区间来自事件归档；未披露的关系与目击不列出。'})
