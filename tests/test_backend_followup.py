"""Regression coverage for saved actions, concurrent notes and usage retention."""
import json
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.knowledge import PackageFiles
from app.file_locks import file_lock
from app.service import Service
from app.storage import Store
from app.web import create_app
from tests import test_adventure_execution as adventure_execution
from tests.test_empty_world_startup import _characters, _story


def test_local_action_note_failure_is_saved_once_and_can_be_rebuilt():
    case = adventure_execution.LocalActionTests('test_rest_after_event_charges_and_advances_once')
    case.setUp()
    try:
        before = case.close_event()
        plan = case.plan('rest', before)
        with patch.object(PackageFiles, 'save_notes', side_effect=OSError('note file unavailable')):
            result = case.turn('歇一会', plan['action_id'], case.local_token(plan, before))
        after = case.reload()
        assert after['state_version'] == before['state_version'] + 1
        assert after['time'] == before['time'] + 4
        assert after['local']['resources']['food'] == before['local']['resources']['food'] - 1
        assert result['notes_sync']['status'] == 'pending'
        assert case.store.get('session_notes_pending', after['id'])
        assert case.rt.rebuild_session_notes(after['id'])
        assert case.store.get('session_notes_pending', after['id']) is None
        assert case.reload()['state_version'] == after['state_version']
    finally:
        case.tearDown()


def test_notes_from_two_services_cannot_publish_an_older_revision_last(tmp_path):
    first = Service(Store(tmp_path / 'notes.sqlite3'), tmp_path)
    first.runtime.commit_package(_story(), _characters(), 'fixture')
    session = first.runtime.new_session('notes', 'protagonist')
    second = Service(Store(tmp_path / 'notes.sqlite3'), tmp_path)
    entered, release, committed = threading.Event(), threading.Event(), threading.Event()
    original_notes, original_save = PackageFiles.save_notes, second.store.save_session

    def delayed_notes(files, scope, identity, notes):
        contents = {n['content'] for n in notes}
        if 'V1' in contents and 'V2' not in contents:
            entered.set()
            assert release.wait(10)
        return original_notes(files, scope, identity, notes)

    def save_second(*args, **kwargs):
        result = original_save(*args, **kwargs)
        committed.set()
        return result

    def add_note(service, text):
        snapshot = service.store.session(session['id'])
        snapshot['heard'].append({'id': text, 'text': text, 'source': 'fixture:' + text,
                                  'distortion': 0})
        service.runtime.save_session_with_notes(snapshot)

    with patch.object(PackageFiles, 'save_notes', delayed_notes), \
            patch.object(second.store, 'save_session', side_effect=save_second), \
            ThreadPoolExecutor(max_workers=2) as pool:
        older = pool.submit(add_note, first, 'V1')
        try:
            assert entered.wait(10)
            newer = pool.submit(add_note, second, 'V2')
            assert committed.wait(10)
            try:
                newer.result(timeout=0.5)
            except TimeoutError:
                pass  # A serialised writer waits for the first publication to finish.
        finally:
            release.set()
        older.result(timeout=10)
        newer.result(timeout=10)
    note = next(first.runtime.files.directory.rglob(session['id'] + '.md')).read_text(encoding='utf-8')
    assert 'V2' in note
    assert first.store.get('session_notes_pending', session['id']) is None


def test_usage_api_keeps_totals_after_debug_trace_eviction_and_clear(tmp_path):
    app = create_app(tmp_path / 'usage.sqlite3')
    store = app.state.service.store
    created = datetime.now(timezone.utc).isoformat()
    for i in range(205):
        store.record_trace({'id': f't{i}', 'created': created, 'scope': 'surface', 'status': 'success',
                            'request': {'private': 'prompt'}, 'response': 'private response',
                            'usage': {'prompt_tokens': 100, 'completion_tokens': 10}})
    assert len(store.all('trace')) == 200
    with TestClient(app) as client:
        headers = {'X-TextileDream-Token': client.get('/api/bootstrap').json()['token']}
        report = client.get('/api/inner/token-usage?hours=24', headers=headers).json()
        assert report['overall']['calls'] == 205
        assert report['overall']['total_tokens'] == 22550
        assert report['coverage']['window_complete'] is False
        assert client.delete('/api/inner/traces', headers=headers).status_code == 200
        assert client.get('/api/inner/traces', headers=headers).json() == []
        assert client.get('/api/inner/token-usage?hours=24', headers=headers).json()['overall']['calls'] == 205


def test_retry_notes_route_does_not_replay_game_state(tmp_path):
    app = create_app(tmp_path / 'retry.sqlite3')
    svc = app.state.service
    svc.runtime.commit_package(_story(), _characters(), 'fixture')
    session = svc.runtime.new_session('retry', 'protagonist')
    svc.store.put('session_notes_pending', session['id'], {'version': session['state_version']})
    with TestClient(app) as client:
        url = '/api/sessions/' + session['id'] + '/notes-sync'
        assert client.post(url).status_code == 403
        headers = {'X-TextileDream-Token': client.get('/api/bootstrap').json()['token']}
        with patch.object(PackageFiles, 'save_notes', side_effect=OSError('still unavailable')):
            response = client.post(url, headers=headers)
            assert response.status_code == 200
            assert response.json()['notes_sync']['status'] == 'pending'
        response = client.post(url, headers=headers)
        assert response.status_code == 200
        assert response.json()['notes_sync']['status'] == 'synced'
    assert svc.store.session(session['id']) == session


def test_legacy_trace_usage_backfill_survives_restart_without_prompt_data(tmp_path):
    path = tmp_path / 'legacy.sqlite3'
    store = Store(path)
    legacy = {'id': 'old', 'created': datetime.now(timezone.utc).isoformat(), 'status': 'success',
              'scope': 'surface', 'usage': {'prompt_tokens': 3, 'completion_tokens': 2},
              'request': {'private': 'prompt'}, 'response': 'private response'}
    # Simulate an existing database before the usage history schema was installed.
    with store.connect() as db:
        db.execute('DROP TABLE IF EXISTS model_usage')
        db.execute("DELETE FROM documents WHERE kind='settings' AND id='token_usage_history'")
        db.execute('INSERT INTO documents VALUES(?,?,?)', ('trace', 'old', json.dumps(legacy)))
    store = Store(path)
    store.clear_traces()
    store = Store(path)
    report = store.token_usage_summary(hours=24)
    assert report['overall']['calls'] == 1
    assert report['overall']['total_tokens'] == 5
    with store.connect() as db:
        body = db.execute('SELECT body FROM model_usage').fetchone()[0]
    assert 'private' not in body and 'prompt"' not in body


def test_usage_retention_and_naive_legacy_timestamps(tmp_path):
    store = Store(tmp_path / 'retention.sqlite3')
    now = datetime.now(timezone.utc)
    for identity, created in [('expired', (now - timedelta(days=91)).isoformat()),
                               ('recent', now.replace(tzinfo=None).isoformat())]:
        store.record_trace({'id': identity, 'created': created, 'status': 'success',
                            'usage': {'prompt_tokens': 2, 'completion_tokens': 1}})
    assert store.token_usage_summary(hours=24)['overall']['calls'] == 1
    with store.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM model_usage').fetchone()[0] == 1


def test_note_file_lock_coordinates_separate_processes(tmp_path):
    lock = tmp_path / 'notes.lock'
    code = ('import sys; from app.file_locks import file_lock; '
            'print("ready", flush=True)\n'
            'with file_lock(sys.argv[1]): print("acquired", flush=True)')
    child = None
    try:
        with file_lock(lock):
            child = subprocess.Popen([sys.executable, '-c', code, str(lock)],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            assert child.stdout.readline().strip() == 'ready'
            try:
                child.communicate(timeout=0.3)
            except subprocess.TimeoutExpired:
                pass
            else:
                raise AssertionError('second process acquired a held note lock')
        output, errors = child.communicate(timeout=10)
        assert child.returncode == 0, errors
        assert 'acquired' in output
    finally:
        if child is not None and child.poll() is None:
            child.kill()
            child.communicate()
