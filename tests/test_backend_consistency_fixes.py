import asyncio
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.contracts import Turn
from app.knowledge import PackageFiles
from app.service import Service
from app.storage import Store
from app.web import create_app
from tests.test_empty_world_startup import _story, _characters


def test_empty_world_generator_and_pipeline(tmp_path):
    app = create_app(tmp_path / 'db.sqlite3')
    app.state.service.provider.configure({'offline': True})
    with TestClient(app) as client:
        headers = {'X-TextileDream-Token': client.get('/api/bootstrap').json()['token']}
        for kind in ('worldview', 'complete'):
            res = client.post('/api/inner/generators', headers=headers,
                              json={'kind': kind, 'title': '测试世界', 'instruction': '小世界'})
            assert res.status_code == 200, res.text
            if kind == 'complete':
                draft = res.json()
        res = client.post('/api/inner/world-pipelines', headers=headers,
                          json={'title': '测试世界', 'instruction': '小世界'})
        assert res.status_code == 200, res.text
        res = client.post('/api/inner/generators/' + draft['id'] + '/save', headers=headers)
        assert res.status_code == 200, res.text
        folder = res.json()['folder']
        assert client.post('/api/inner/packages/' + folder + '/activate', headers=headers).status_code == 200
        assert client.post('/api/sessions', headers=headers,
                           json={'title': '第一段', 'mode': 'protagonist'}).status_code == 200








def test_note_failure_saved_and_rebuilt(tmp_path):
    svc = Service(Store(tmp_path / 'db.sqlite3'), tmp_path)
    svc.provider.configure({'offline': True})
    svc.runtime.commit_package(_story(), _characters(), 'test')
    state = svc.runtime.new_session('测试', 'protagonist')
    with patch.object(PackageFiles, 'save_notes', side_effect=OSError('disk failure')):
        result = asyncio.run(svc.turn(state['id'], Turn(message='hello', channel='speech')))
        assert result['notes_sync']['status'] == 'pending'
        assert svc.store.session(state['id'])['state_version'] == 1
        assert svc.store.get('session_notes_pending', state['id'])
    svc = Service(Store(tmp_path / 'db.sqlite3'), tmp_path)
    assert svc.store.get('session_notes_pending', state['id']) is None
    assert len(svc.store.session(state['id'])['active']['turns']) == 1
