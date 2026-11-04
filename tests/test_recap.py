"""Offline recaps and bounded author intent diagnostics, with explicit packages."""
import copy
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app import recap
from app.web import create_app


def story():
    return {
        'id': 'recap-test', 'title': '小路', 'premise': '一段旅程',
        'character_package_id': 'recap-cast',
        'locations': [{'id': 'plaza', 'name': '广场', 'description': '', 'neighbors': [], 'scenes': []}],
        'events': [{'id': 'root', 'title': '选择', 'location_id': 'plaza',
                    'participants': ['hero', 'npc'], 'player_goal': '走下去',
                    'player_enters': True, 'next_events': [], 'entry_flags': {},
                    'exit_flag': 'done', 'max_turns': 8,
                    'actions': [{'id': 'look', 'label': '帮忙', 'ends_event': True,
                                 'check': {'attribute': 'agility', 'difficulty': .1},
                                 'costs': {'coin': 2}, 'witnesses': ['npc'],
                                 'effects': [{'op': 'flag', 'id': 'win', 'value': True},
                                             {'op': 'take', 'id': 'note'}],
                                 'success_text': '帮忙完成', 'failure_text': '帮忙失败'},
                                {'id': 'leave', 'label': '离开', 'ends_event': True,
                                 'effects': [{'op': 'flag', 'id': 'win', 'value': False},
                                             {'op': 'flag', 'id': 'done', 'value': True}],
                                 'success_text': '离开了'}]}],
        'items': [{'id': 'note', 'name': '纸条', 'location_id': 'plaza', 'description': '作者秘密物品正文'}],
        'mechanics': {'local': {'turn_hours': 1, 'travel_hours': 2,
                                 'resources': [{'id': 'coin', 'name': '零钱', 'initial': 10}]},
                      'endings': {'version': 1, 'endings': [
                          {'id': 'win', 'title': '帮助之后', 'kind': 'saved', 'summary': '有人道谢。',
                           'priority': 2, 'condition': {'all_flags': {'win': True}}},
                          {'id': 'other', 'title': '未见结局秘密标题', 'kind': 'lost', 'summary': '秘密结局正文',
                           'priority': 1, 'condition': {'all_flags': {'win': False, 'done': True}}}]}}}


def characters():
    return {'id': 'recap-cast', 'title': '人物', 'characters': [
        {'id': 'hero', 'name': '我', 'role': '主角', 'location_id': 'plaza',
         'personality': {}, 'state': {}, 'attributes': {k: 50 for k in
             ('talent', 'strength', 'agility', 'wisdom', 'social', 'resilience')}},
        {'id': 'npc', 'name': '邻居', 'role': '次要角色', 'location_id': 'plaza',
         'personality': {}, 'state': {}, 'npc_card': {
             'goal': {'text': 'NPC私密目标', 'visibility': 'private'}}}]}


@pytest.fixture
def world():
    with tempfile.TemporaryDirectory() as directory:
        with TestClient(create_app(Path(directory) / 'test.sqlite3')) as client:
            service = client.app.state.service
            service.provider.configure({'offline': True})
            service.runtime.commit_package(story(), characters(), 'explicit test package')
            headers = {'X-TextileDream-Token': client.get('/api/bootstrap').json()['token']}
            s = service.runtime.new_session('回顾测试', 'protagonist')
            yield client, service, headers, s


def test_recap_real_archive_is_read_only_and_player_safe(world):
    client, service, headers, s = world
    result = client.post('/api/sessions/' + s['id'] + '/chat', headers=headers,
                         json={'message': '帮忙', 'action_id': 'look', 'channel': 'action'})
    assert result.status_code == 200, result.text
    saved = service.store.session(s['id'])
    saved['beliefs'].append({'id': 'private', 'character': 'npc', 'text': 'NPC秘密信念'})
    saved['development'] = {'npc': {'relationships': {'hero': {'trust': .12345}},
                                     'hidden_trait': '隐藏特质秘密'}}
    service.store.save_session(saved)
    before = service.store.session(s['id'])
    with service.store.connect() as db:
        documents = db.execute('SELECT * FROM documents ORDER BY kind,id').fetchall()
    response = client.get('/api/sessions/' + s['id'] + '/recap')
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['ending'] == {'title': '帮助之后', 'summary': '有人道谢。'}
    assert data['unseen_endings'] == 1
    assert data['timeline'][0]['label'] == '帮忙'
    assert data['timeline'][0]['check'] == {k: before['checks'][0][k] for k in ('attribute', 'success')}
    assert data['timeline'][0]['time_range'] == {'from': 8, 'to': before['time']}
    assert data['holdings']['opening']['resources'][0]['amount'] == 10
    assert data['holdings']['now']['resources'][0]['amount'] == 8
    assert data['holdings']['opening']['items'] == {}
    assert data['holdings']['now']['items'] == {'纸条': 1}
    assert data['remembered'] == []  # A private NPC witness is not player knowledge.
    for secret in ('NPC秘密信念', '隐藏特质秘密', 'NPC私密目标', '.12345',
                   '未见结局秘密标题', '秘密结局正文', '作者秘密物品正文'):
        assert secret not in json.dumps(data, ensure_ascii=False)
    assert before == service.store.session(s['id'])
    with service.store.connect() as db:
        assert documents == db.execute('SELECT * FROM documents ORDER BY kind,id').fetchall()
    package = service.runtime.package(s['revision'])
    frozen = copy.deepcopy(before)
    recap.build(package['story'], before, package['characters'])
    assert before == frozen


def test_old_package_and_timeline_limit(world):
    client, service, _, _ = world
    old = story()
    del old['mechanics']['endings']
    service.runtime.commit_package(old, characters(), 'explicit legacy package')
    s = service.runtime.new_session('旧包', 'protagonist')
    data = client.get('/api/sessions/' + s['id'] + '/recap').json()
    assert data['ending']['title'] == '进行中'
    assert data['unseen_endings'] == 0
    assert data['timeline'] == []
    s['active']['actions_done'] = ['look'] * 40
    data = recap.build(old, s, characters(), limit=1000)
    assert len(data['timeline']) == 30
    assert data['timeline_total'] == 40


def test_disclosed_witness_and_reaction_only(world):
    _, _, _, s = world
    st = story()
    st['mechanics']['scene_judgment'] = {'actors': {'npc': {'choices': {
        'thanks': {'line': '邻居说以后愿意帮忙', 'trust_delta': .1}}}}}
    s['scene_judgments'] = [{'reactions': [{'character': 'npc', 'choice': 'thanks'}]}]
    s['heard'] = [{'text': '邻居说以后愿意帮忙', 'source': 'scene-reaction:thanks', 'time': 9},
                  {'text': '你看见邻居记下帮助', 'source': 'root:look', 'time': 9}]
    s['beliefs'] = [{'kind': 'npc_event', 'character': 'npc', 'text': '你看见邻居记下帮助',
                    'source': 'root:look', 'time': 9, 'known_by': ['player']},
                   {'kind': 'npc_event', 'character': 'npc', 'text': '隐蔽目击', 'source': 'secret'}]
    data = recap.build(st, s, characters())
    assert [r['kind'] for r in data['remembered']] == ['reaction', 'witness']
    assert '隐蔽目击' not in json.dumps(data, ensure_ascii=False)


def test_unmatched_route_records_only_result_flag_and_truncates(world):
    client, service, headers, s = world
    before = service.store.session(s['id'])
    url = '/api/sessions/' + s['id'] + '/intent'
    with patch('app.free_actions.suggest', return_value={'matched': [], 'unjudged': True}) as suggest:
        response = client.post(url, headers=headers, json={'text': '没' * 230})
        assert response.status_code == 200, response.text
        assert suggest.call_args.kwargs['characters']['id'] == 'recap-cast'
    with patch('app.free_actions.suggest', return_value={'matched': [], 'unjudged': False}):
        assert client.post(url, headers=headers, json={'text': '不记录'}).status_code == 200
    assert service.store.session(s['id']) == before
    assert client.get('/api/inner/unmatched-intents').status_code == 403
    response = client.get('/api/inner/unmatched-intents', headers=headers)
    row = response.json()['items'][0]
    assert response.json()['total'] == 1
    assert row['text'] == '没' * 200
    assert row['package_id'] == 'recap-test'
    assert row['revision'] == s['revision']
    assert row['session_id'] == s['id']
    assert row['location_id'] == 'plaza' and row['event_id'] == 'root'
    assert row['created']
    assert client.get('/api/inner/unmatched-intents?package_id=none', headers=headers).json()['items'] == []
    assert client.get('/api/inner/unmatched-intents?limit=501', headers=headers).status_code == 400
    for suffix in ('/recap', '/intent'):
        if suffix == '/recap':
            result = client.get('/api/sessions/' + s['id'] + suffix, headers={'Origin': 'https://evil.test'})
        else:
            result = client.post(url, headers={**headers, 'Origin': 'https://evil.test'}, json={'text': 'x'})
        assert result.status_code == 403


def test_scene_intent_path_logs_and_confirm_forwards_characters(world):
    client, service, headers, s = world
    with patch('app.scene_judgment.enabled', return_value=True), patch(
            'app.scene_judgment.intent', new=AsyncMock(return_value={'matched': [], 'unjudged': True})):
        response = client.post('/api/sessions/' + s['id'] + '/intent', headers=headers, json={'text': '未处理'})
        assert response.status_code == 200, response.text
    assert len(service.store.all('unmatched_intent')) == 1
    with patch('app.free_actions.describe', return_value={'label': '帮忙'}) as describe:
        assert client.get('/api/sessions/' + s['id'] + '/confirm/look').status_code == 200
        assert describe.call_args.kwargs['characters']['id'] == 'recap-cast'


def test_log_retention_and_newest_first(world):
    client, service, headers, _ = world
    for i in range(505):
        service.store.record_unmatched_intent({'id': str(i), 'package_id': 'p', 'text': str(i)})
    rows = client.get('/api/inner/unmatched-intents?limit=500', headers=headers).json()
    assert rows['total'] == 500
    assert rows['items'][0]['id'] == '504'
    assert rows['items'][-1]['id'] == '5'


def test_reward_wallet_and_unidentified_items_use_public_projection(world):
    client, service, _, _ = world
    from app import rewards
    fragment = Path(__file__).resolve().parents[1] / 'docs/examples/rewards-demo.story-fragment.json'
    st = story()
    st['mechanics']['rewards'] = json.loads(fragment.read_text(encoding='utf-8'))['mechanics']['rewards']
    service.runtime.commit_package(st, characters(), 'explicit reward recap package')
    s = service.runtime.new_session('钱包测试', 'protagonist')
    service.runtime.effects(s, [], 'test:recap', [{'entry': 'coin_ferry'}, {'entry': 'relic'}])
    service.store.save_session(s)
    data = client.get('/api/sessions/' + s['id'] + '/recap').json()
    assert data['holdings']['opening']['wallet'][0]['amount'] == 0
    assert data['holdings']['now']['wallet'] == rewards.public_state(s, st)['wallet']
    assert data['holdings']['now']['wallet'][0]['amount'] == 8
    assert data['holdings']['now']['items'] == {'一件冰凉的小物': 1}
    assert '暗影护符' not in json.dumps(data, ensure_ascii=False)
    assert '潜影' not in json.dumps(data, ensure_ascii=False)
