import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
import subprocess
import sys
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app import native_starts
from app.contracts import Turn
from app.knowledge import PackageFiles
from app.service import Service
from app.storage import Store
from app.web import create_app
from tests.test_empty_world_startup import _story, _characters
from tests import test_native_starts


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


def test_native_confirm_concurrent_and_retry():
    case = test_native_starts.NativeStartTests()
    case.setUp()
    try:
        store, rt = case.service.store, case.service.runtime
        draft = native_starts.save(store, case.draft()['draft'])['draft']
        entered, release = threading.Event(), threading.Event()
        original = rt.commit_package
        def delayed(*args, **kwargs):
            entered.set()
            assert release.wait(15)
            return original(*args, **kwargs)
        with patch.object(rt, 'commit_package', side_effect=delayed):
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(native_starts.confirm, rt, store, draft['id'], expected_revision=0)
                assert entered.wait(15)
                second = pool.submit(native_starts.confirm, rt, store, draft['id'], expected_revision=0)
                release.set()
                results = [first.result(30), second.result(30)]
        assert [r['created'] for r in results] == [True, False]
        assert results[0]['revision'] == results[1]['revision']
        assert len(store.all('package')) == 1
    finally:
        case.tearDown()


def test_claim_failure_retry_and_interrupted_recovery():
    case = test_native_starts.NativeStartTests()
    case.setUp()
    try:
        store, rt = case.service.store, case.service.runtime
        draft = native_starts.save(store, case.draft()['draft'])['draft']
        with patch.object(rt, 'commit_package', side_effect=OSError('failure')):
            with pytest.raises(OSError):
                native_starts.confirm(rt, store, draft['id'], expected_revision=0)
        assert not native_starts.get(store, draft['id']).get('claim')
        script = ("import os,sys; from app import native_starts as n; "
                  "from app.storage import Store; s=Store(sys.argv[1]); "
                  "d=n.get(s,sys.argv[2]); "
                  "lock=n._draft_lock(s,d['id']); lock.__enter__(); "
                  "assert n._claim(s,d,0); os._exit(0)")
        subprocess.run([sys.executable, '-X', 'utf8', '-c', script, str(store.path), draft['id']],
                       check=True, timeout=30)
        assert native_starts.get(store, draft['id']).get('claim')
        assert not native_starts._claim(store, draft, 0)
        result = native_starts.confirm(rt, store, draft['id'], expected_revision=0)
        assert result['created']
        with store.transact() as db:
            import json
            doc = native_starts.get(store, draft['id'])
            doc.pop('confirmed_revision')
            doc['claim'] = 'crashed'
            db.execute('UPDATE documents SET body=? WHERE kind=? AND id=?',
                       (json.dumps(doc), native_starts.KIND, draft['id']))
        recovered = native_starts.confirm(rt, store, draft['id'], expected_revision=0)
        assert not recovered['created'] and recovered['revision'] == result['revision']
        assert len(store.all('package')) == 1
    finally:
        case.tearDown()


def test_confirm_recovers_after_package_commit_before_draft_update():
    case = test_native_starts.NativeStartTests()
    case.setUp()
    try:
        store, rt = case.service.store, case.service.runtime
        draft = native_starts.save(store, case.draft()['draft'])['draft']
        with patch.object(native_starts, '_mark_confirmed', side_effect=OSError('interrupted')):
            with pytest.raises(OSError):
                native_starts.confirm(rt, store, draft['id'], expected_revision=0)
        first = store.all('package')[0]['id']
        result = native_starts.confirm(rt, store, draft['id'], expected_revision=0)
        assert not result['created'] and result['revision'] == first
        assert len(store.all('package')) == 1
    finally:
        case.tearDown()


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
