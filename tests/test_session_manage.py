import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from tests.fixtures_world import world_app

LAYER_TABLES = ('facts', 'beliefs', 'heard')


class SessionManageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'test.sqlite3'
        self.app = world_app(self.path)
        self.service = self.app.state.service
        self.store = self.service.store
        self.keep = self.service.runtime.new_session('保留的旅程', 'protagonist')
        self.target = self.service.runtime.new_session('待处理的旅程', 'protagonist')
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)
        token = self.client.get('/api/bootstrap').json()['token']
        self.headers = {'X-TextileDream-Token': token}

    def titles(self):
        return {s['id']: s['title'] for s in self.client.get('/api/bootstrap').json()['sessions']}

    def seed_related(self, sid):
        """Rows keyed to one session in every side table that can hold them."""
        with self.store.connect() as db:
            for table in LAYER_TABLES:
                db.execute(f'INSERT OR REPLACE INTO {table} VALUES(?,?,?)', (sid, 'seed', '{}'))
            db.execute('INSERT OR REPLACE INTO recall_vectors VALUES(?,?,?,?,?)',
                       (sid, 'src', 'sig', '{}', '{}'))
        self.store.put('session_notes_pending', sid, {'id': sid, 'version': 1})
        self.store.put('development_draft', 'draft-' + sid, {'id': 'draft-' + sid, 'session_id': sid})

    def counts(self, sid):
        with self.store.connect() as db:
            result = {t: db.execute(f'SELECT COUNT(*) FROM {t} WHERE session=?', (sid,)).fetchone()[0]
                      for t in (*LAYER_TABLES, 'recall_vectors')}
            result['session'] = db.execute('SELECT COUNT(*) FROM documents WHERE kind=? AND id=?',
                                           ('session', sid)).fetchone()[0]
            result['pending'] = db.execute('SELECT COUNT(*) FROM documents WHERE kind=? AND id=?',
                                           ('session_notes_pending', sid)).fetchone()[0]
            result['draft'] = db.execute('SELECT COUNT(*) FROM documents WHERE kind=? AND id=?',
                                         ('development_draft', 'draft-' + sid)).fetchone()[0]
        return result

    def test_rename_trims_and_persists(self):
        before = self.store.session(self.target['id'])
        r = self.client.patch('/api/sessions/' + self.target['id'], json={'title': '  新名字  '},
                              headers=self.headers)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {'id': self.target['id'], 'title': '新名字'})
        after = self.store.session(self.target['id'])
        self.assertEqual(after['title'], '新名字')
        self.assertEqual(after['state_version'], before['state_version'])
        self.assertEqual({k: v for k, v in after.items() if k != 'title'},
                         {k: v for k, v in before.items() if k != 'title'})
        self.assertEqual(self.titles()[self.target['id']], '新名字')
        self.assertEqual(self.titles()[self.keep['id']], '保留的旅程')
        self.assertEqual(self.client.get('/api/sessions/' + self.target['id']).json()['title'], '新名字')

    def test_rename_accepts_80_characters(self):
        title = '长' * 80
        r = self.client.patch('/api/sessions/' + self.target['id'], json={'title': title},
                              headers=self.headers)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.store.session(self.target['id'])['title'], title)

    def test_rename_rejects_invalid_titles(self):
        for body in ({'title': ''}, {'title': '   \t\n'}, {'title': '长' * 81},
                     {'title': ' ' + '长' * 81 + ' '}, {}, {'title': 'x', 'extra': 1}, {'title': 5}):
            r = self.client.patch('/api/sessions/' + self.target['id'], json=body, headers=self.headers)
            self.assertIn(r.status_code, (400, 422), body)
        self.assertEqual(self.store.session(self.target['id'])['title'], '待处理的旅程')

    def test_rename_unknown_session_and_token(self):
        r = self.client.patch('/api/sessions/nope', json={'title': '新名字'}, headers=self.headers)
        self.assertEqual(r.status_code, 404)
        self.assertIn('存档不存在', r.json()['detail'])
        r = self.client.patch('/api/sessions/' + self.target['id'], json={'title': '新名字'})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.store.session(self.target['id'])['title'], '待处理的旅程')

    def test_delete_removes_session_and_related_rows_only(self):
        self.seed_related(self.target['id'])
        self.seed_related(self.keep['id'])
        keep_before = self.counts(self.keep['id'])
        target_before = self.counts(self.target['id'])
        for key, value in target_before.items():
            self.assertGreaterEqual(value, 1, key)

        r = self.client.delete('/api/sessions/' + self.target['id'], headers=self.headers)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {'deleted': self.target['id']})

        self.assertEqual(self.counts(self.target['id']), {k: 0 for k in target_before})
        self.assertEqual(self.counts(self.keep['id']), keep_before)
        self.assertNotIn(self.target['id'], self.titles())
        self.assertIn(self.keep['id'], self.titles())
        self.assertEqual(self.client.get('/api/sessions/' + self.target['id']).status_code, 404)
        self.assertEqual(self.store.session(self.keep['id'])['title'], '保留的旅程')

    def test_delete_keeps_story_package(self):
        revision = self.target['revision']
        folder = self.service.runtime.package(revision).get('folder')
        packages = len(self.store.all('package'))
        library_files = sorted(p.relative_to(self.service.runtime.library).as_posix()
                               for p in self.service.runtime.library.rglob('*') if p.is_file())
        self.assertEqual(self.client.delete('/api/sessions/' + self.target['id'],
                                            headers=self.headers).status_code, 200)
        self.assertEqual(len(self.store.all('package')), packages)
        self.assertTrue(self.store.get('package', revision))
        if folder:
            self.assertTrue((self.service.runtime.library / folder).is_dir())
        self.assertEqual(sorted(p.relative_to(self.service.runtime.library).as_posix()
                                for p in self.service.runtime.library.rglob('*') if p.is_file()),
                         library_files)

    def test_delete_unknown_session_errors_and_changes_nothing(self):
        self.seed_related(self.keep['id'])
        before = self.counts(self.keep['id'])
        r = self.client.delete('/api/sessions/nope', headers=self.headers)
        self.assertEqual(r.status_code, 404)
        self.assertIn('存档不存在', r.json()['detail'])
        self.assertEqual(self.counts(self.keep['id']), before)
        self.assertEqual(set(self.titles()), {self.keep['id'], self.target['id']})

    def test_delete_twice_and_without_token(self):
        self.assertEqual(self.client.delete('/api/sessions/' + self.target['id']).status_code, 403)
        self.assertIn(self.target['id'], self.titles())
        self.assertEqual(self.client.delete('/api/sessions/' + self.target['id'],
                                            headers=self.headers).status_code, 200)
        self.assertEqual(self.client.delete('/api/sessions/' + self.target['id'],
                                            headers=self.headers).status_code, 404)


if __name__ == '__main__':
    unittest.main()
