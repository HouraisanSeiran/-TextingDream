import asyncio
import copy
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app import free_actions, npc_cards, scene_judgment
from app.contracts import Turn
from app.web import create_app
from tools.playable_scenes import scenes


@pytest.fixture
def game(tmp_path):
    app = create_app(tmp_path / 'cards.sqlite3')
    service = app.state.service
    service.provider.configure({'offline': True})
    data = copy.deepcopy(scenes()[0])
    bess = next(c for c in data['characters']['characters'] if c['id'] == 'bess')
    bess['npc_card'] = {
        'goal': {'text': '保住酒馆生意'},
        'pressure': {'text': '秘密欠债七十镑', 'visibility': 'private'},
        'knowledge': [{'text': '渡船工偷了账本', 'kind': 'misunderstanding',
                       'source': '根据争执自行猜测', 'visibility': 'public', 'confidence': .9},
                      {'text': '秘密账本藏在井底', 'kind': 'observation', 'source': '亲自放置'}]}
    data['story']['events'][0]['actions'][0]['witnesses'] = ['bess']
    service.runtime.commit_package(data['story'], data['characters'], 'NPC card test')
    with TestClient(app) as client:
        token = client.get('/api/bootstrap').json()['token']
        client.headers['X-TextileDream-Token'] = token
        yield service, client


def execute(service, session, action_id):
    runtime = service.runtime
    action = free_actions.describe(session, runtime.package(session['revision'])['story'], runtime.node(session), action_id)
    asyncio.run(service.turn(session['id'], Turn(message=action['label'], action_id=action_id,
                                               confirm=action.get('confirm'))))
    return service.store.session(session['id'])


def test_edit_persist_revision_conflict_and_pinned_journey(game):
    service, client = game
    old = service.runtime.new_session('旧旅程', 'protagonist')
    data = client.get('/api/inner/npc-cards').json()
    card = data['characters'][0]['card']
    card['goal']['text'] = '收回欠款'
    body = {'revision': data['revision'], 'card': card}
    response = client.put('/api/inner/npc-cards/bess', json=body)
    assert response.status_code == 200, response.text
    assert client.put('/api/inner/npc-cards/bess', json=body).status_code == 400
    assert client.get('/api/inner/npc-cards').json()['characters'][0]['card']['goal']['text'] == '收回欠款'
    pinned = client.get('/api/inner/npc-cards', params={'session_id': old['id']}).json()
    assert pinned['characters'][0]['card']['goal']['text'] == '保住酒馆生意'
    chars_path = service.runtime.character_directory / (service.runtime.package()['characters']['id'] + '.json')
    assert '收回欠款' in chars_path.read_text(encoding='utf-8')


def test_validation_and_author_access(game):
    service, client = game
    data = client.get('/api/inner/npc-cards').json()
    for card in ({'knowledge': [{'text': 'a', 'kind': 'rumor', 'source': 'b', 'confidence': 2}]},
                 {'inner_voices': ['不采用']}, {'goal': {'text': 'x', 'visibility': 'everyone'}}):
        response = client.put('/api/inner/npc-cards/bess', json={'revision': data['revision'], 'card': card})
        assert response.status_code == 422
    client.headers.pop('X-TextileDream-Token')
    assert client.get('/api/inner/npc-cards').status_code == 403
    assert service.runtime.package()['id'] == data['revision']


def test_projection_preserves_secrets_and_uncertainty(game):
    service, _ = game
    runtime = service.runtime
    s = runtime.new_session('隔离', 'protagonist')
    public = runtime.context(s, 'player', '', service.preferences())['npc_cards']['items'][0]
    own = runtime.context(s, 'bess', '', service.preferences())['npc_cards']['items'][0]
    assert '秘密' not in str(public)
    assert '秘密欠债' in str(own)
    assert public['knowledge'][0]['kind'] == 'interpretation'
    assert own['knowledge'][0]['kind'] == 'interpretation'
    assert not any('账本' in f['text'] for f in s['facts'])
    request = Turn(message='问好')
    data = scene_judgment.context(runtime, s, request, {'listeners': ['bess']}, None)
    assert '秘密' not in str(data)
    assert data['conversation_partners'][0]['npc_card']['profile']['goal'] == '保住酒馆生意'
    # Another NPC cannot acquire Bess's card even from their own viewpoint.
    other = runtime.context(s, 'ferryman', '', service.preferences())
    assert '秘密欠债' not in str(other)


def test_witness_memory_persists_without_inventing_observers_and_rolls_back(game):
    service, _ = game
    s = service.runtime.new_session('记忆', 'protagonist')
    s = execute(service, s, 'read_prices')
    memories = [r for r in s['beliefs'] if r['kind'] == 'npc_event']
    assert len(memories) == 1 and memories[0]['character'] == 'bess'
    assert memories[0]['result'] == 'success'
    s = execute(service, s, 'ask_job')
    s = execute(service, s, 'go_search')
    s = service.runtime.rollback(s, s['archives'][0]['id'])
    assert not [r for r in s['beliefs'] if r.get('kind') == 'npc_event']


def test_failure_records_resolved_outcome_and_model_error_is_atomic(game):
    service, _ = game
    s = service.runtime.new_session('失败经历', 'protagonist')
    s = execute(service, s, 'ask_job')
    s = execute(service, s, 'go_search')
    service.runtime.move(s, 'yard')
    s = service.store.session(s['id'])
    with patch('app.runtime.resolve_check', return_value={'success': False, 'attribute': 'dexterity',
               'probability': .1, 'margin': -.3}):
        s = execute(service, s, 'steal_linen')
    memories = [r for r in s['beliefs'] if r.get('kind') == 'npc_event']
    assert len(memories) == 1 and memories[0]['result'] == 'failure'
    assert memories[0]['text'] != 'steal_linen'
    row = service.runtime.context(s, 'player', '', service.preferences())['npc_cards']['items'][0]
    assert any(m['result'] == 'failure' for m in row['memories'])
    # A model failure must not persist even engine-prepared memories.
    fresh = service.runtime.new_session('失败重试', 'protagonist')
    before = copy.deepcopy(service.store.session(fresh['id']))
    service.provider.configure({'offline': False})
    with patch.object(service.provider, 'complete', side_effect=ValueError('offline test error')):
        with pytest.raises(ValueError, match='offline test error'):
            execute(service, fresh, 'read_prices')
    assert service.store.session(fresh['id']) == before


def test_legacy_cards_and_distant_witnesses(game):
    service, _ = game
    p = service.runtime.package()
    actor = next(c for c in p['characters']['characters'] if c['id'] == 'ferryman')
    assert npc_cards.project(actor, {}, 'player') is None
    s = service.runtime.new_session('远处人物', 'protagonist')
    s['characters']['bess']['location'] = 'quay'
    node = service.runtime.node(s)
    npc_cards.remember_action(p, s, node, node['actions'][0], {'outcome': '已发生'})
    assert not [r for r in s['beliefs'] if r.get('kind') == 'npc_event']
