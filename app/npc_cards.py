"""NPC author cards, audience projections and engine-witnessed event memory."""
from copy import deepcopy
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=400)]
FIELDS = ('identity', 'experiences', 'values', 'goal', 'pressure', 'boundaries',
          'bargaining', 'social_context', 'emotion', 'failure_response')


class Detail(BaseModel):
    model_config = ConfigDict(extra='forbid')
    text: str = Field(default='', max_length=400)
    visibility: Literal['public', 'private'] = 'public'


class Knowledge(BaseModel):
    model_config = ConfigDict(extra='forbid')
    text: Text
    kind: Literal['observation', 'rumor', 'interpretation', 'misunderstanding']
    source: Text
    confidence: float = Field(default=.5, ge=0, le=1, allow_inf_nan=False)
    visibility: Literal['public', 'private'] = 'private'


class NPCCard(BaseModel):
    model_config = ConfigDict(extra='forbid')
    version: Literal[1] = 1
    identity: Detail = Field(default_factory=Detail)
    experiences: Detail = Field(default_factory=Detail)
    values: Detail = Field(default_factory=Detail)
    goal: Detail = Field(default_factory=Detail)
    pressure: Detail = Field(default_factory=Detail)
    boundaries: Detail = Field(default_factory=Detail)
    bargaining: Detail = Field(default_factory=Detail)
    social_context: Detail = Field(default_factory=Detail)
    emotion: Detail = Field(default_factory=Detail)
    failure_response: Detail = Field(default_factory=Detail)
    knowledge: list[Knowledge] = Field(default_factory=list, max_length=16)


class CardEdit(BaseModel):
    model_config = ConfigDict(extra='forbid')
    revision: str
    card: NPCCard


def validate(story, characters):
    for actor in characters['characters']:
        if actor.get('npc_card') is not None:
            if actor['role'] == '主角':
                raise ValueError('NPC 角色卡只能用于次要角色')
            NPCCard.model_validate(actor['npc_card'])
    for event in story.get('events', []):
        for action in event.get('actions', []):
            witnesses = action.get('witnesses', [])
            if not isinstance(witnesses, list) or any(
                    not isinstance(cid, str) or cid not in event['participants'] for cid in witnesses):
                raise ValueError('行动目击者必须属于当前事件参与者')


def project(actor, session, audience):
    """Public text goes to the narrator; private text only to the owner/author."""
    raw = actor.get('npc_card')
    if raw is None:
        return None
    card = NPCCard.model_validate(raw).model_dump()
    owner = audience in (actor['id'], 'author')
    fields = {key: card[key]['text'] for key in FIELDS
              if card[key]['text'].strip() and (owner or card[key]['visibility'] == 'public')}
    knowledge = []
    for entry in card['knowledge']:
        if not owner and entry['visibility'] != 'public':
            continue
        item = {k: entry[k] for k in ('text', 'kind', 'source', 'confidence')}
        # A character believes their misunderstanding; only the author knows its label.
        if audience != 'author' and item['kind'] == 'misunderstanding':
            item['kind'] = 'interpretation'
        knowledge.append(item)
    state = session.get('development', {}).get(actor['id'], {})
    result = {'id': actor['id'], 'profile': fields, 'knowledge': knowledge,
              'knowledge_rule': '人物所知与推测，不是世界事实；确信程度不代表真实性。'}
    if state.get('emotion_expires_after_turn', -1) >= session.get('turn_index', 0) and state.get('emotion'):
        result['emotion'] = deepcopy(state['emotion'])
    if owner:
        result['relationships'] = deepcopy(state.get('relationships', {}))
    # Only explicit engine witness records are shared with the public narrator.
    records = [r for r in session.get('beliefs', []) if r.get('character') == actor['id']
               and (owner or r.get('kind') == 'npc_event')]
    result['memories'] = [{k: r[k] for k in ('text', 'kind', 'source', 'speaker', 'certainty',
                          'distortion', 'time', 'result') if k in r} for r in records[-8:]]
    return result


def context(package, session, audience, participants):
    rows = []
    for actor in package['characters']['characters']:
        cid = actor['id']
        if cid == session['hero'] or cid not in participants:
            continue
        if audience != 'player' and cid != audience:
            continue
        if session['characters'][cid]['location'] != session['location']:
            continue
        row = project(actor, session, audience)
        if row is not None:
            rows.append(row)
    return {'items': rows} if rows else None


def remember_action(package, session, node, action, result):
    """Only declared, co-located witnesses remember the executed branch, never prose."""
    if not action:
        return
    branch = result.get('narrative', {}).get('result', 'success')
    witnesses = set(action.get('witnesses', [])) | set(action.get('social', {}).get(branch, {}))
    actors = {c['id']: c for c in package['characters']['characters']}
    for cid in sorted(witnesses):
        if (cid == session['hero'] or cid not in node['participants']
                or actors[cid].get('npc_card') is None
                or session['characters'][cid]['location'] != session['location']):
            continue
        key = f"npc-event:{session['active']['id']}:{session['turn_index']}:{action['id']}:{cid}"
        if any(r['id'] == key for r in session['beliefs']):
            continue
        session['beliefs'].append({'id': key, 'character': cid, 'kind': 'npc_event',
                                  'text': result['outcome'], 'source': node['id'] + ':' + action['id'],
                                  'speaker': session['hero'], 'time': session['time'],
                                  'certainty': 1, 'distortion': 0, 'intensity': .7, 'result': branch})
