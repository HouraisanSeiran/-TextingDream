# -*- coding: utf-8 -*-
"""历史作者路由的端到端 HTTP 测试（真实 TestClient + 临时库 + 真实导入记录）。

守的是接线上的实际失败模式：

* 作者路由必须带 token，**包括读预览**（预览是未公开的作者草稿）；
* 请求体只接受 import_id / 年 / 分支；record、file、url、客户端 civ 一律 422；
* expected_revision / expected_story_revision 必须由作者带上来，不能由服务端补当前值；
* 预览不改故事包，采纳后才新建一个 revision；
* 玩家侧历史从包内读，删掉快照行仍可读；
* 地图来源与历史来源不一致时拒收。
"""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app import world_history_store as whs
from app.service import Service
from app.storage import Store
from app.web import create_app

from tests.test_civ_atlas_history import civ_block

ROOT = Path(__file__).resolve().parents[1]
REAL_EXPORT = Path(r'D:/Vantaloom/data/temp/project-proj-1792851796-712e540fb0'
                   r'/scratch/real-verify-data/map_imports'
                   r'/2f364872015835be5a905876c6bdf5ae.civsnap')


def import_record(sha='b' * 64, import_id='sn_abcdef123456'):
    return {
        'id': import_id, 'sha256': sha, 'bytes': 4609307,
        'file': 'abcdef.civsnap',
        'parts': [{'name': 'civ', 'sum': 'e' * 64, 'sum_verified_by': 'server',
                   'bytes': 1932123, 'zip': 'gzip'}],
        'source': {'world_id': 'wmvrpuwi29m3yi', 'generator_version': 45,
                   'snapshot_format': 1},
    }


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        db_path = Path(self.tmp.name) / 'h.sqlite3'
        self.app = create_app(db_path)
        self.svc = self.app.state.service
        self.svc.provider.configure({'offline': True})
        self.store = self.svc.store
        self.block = civ_block()
        self.svc.history = whs.WorldHistoryService(
            self.svc.runtime,
            load_civ=lambda record: (self.block, {'eras_block': False, 'era_until': [],
                                                  'upheaval_years': []}))
        self.store.put('map_import', 'sn_abcdef123456', import_record())
        self.client = TestClient(self.app)
        with self.client as client:
            self.token = client.get('/api/bootstrap').json()['token']

    def head(self):
        return {'X-TextileDream-Token': self.token}

    def post(self, path, body):
        return self.client.post(path, json=body, headers=self.head())

    def preview(self, year=200):
        res = self.post('/api/inner/history/previews',
                        {'import_id': 'sn_abcdef123456', 'base_year': year,
                         'branch': 'main'})
        self.assertEqual(res.status_code, 200, res.text)
        return res.json()['preview']


class AuthorRouteGuardTests(Base):
    def test_reading_a_preview_requires_the_token(self):
        draft = self.preview()
        anonymous = TestClient(self.app)
        res = anonymous.get('/api/inner/history/previews/%s' % draft['id'])
        self.assertEqual(res.status_code, 403, '预览是作者草稿，匿名不得读')

    def test_writing_requires_the_token(self):
        anonymous = TestClient(self.app)
        res = anonymous.post('/api/inner/history/previews',
                             json={'import_id': 'sn_abcdef123456', 'base_year': 200})
        self.assertEqual(res.status_code, 403)

    def test_public_prefix_is_not_served(self):
        draft = self.preview()
        res = self.client.get('/api/history/previews/%s' % draft['id'], headers=self.head())
        self.assertEqual(res.status_code, 404, '只有一个作者侧前缀')

    def test_imports_list_only_registered_records(self):
        res = self.client.get('/api/inner/history/imports', headers=self.head())
        self.assertEqual(res.status_code, 200)
        rows = res.json()['imports']
        self.assertEqual([row['import_id'] for row in rows], ['sn_abcdef123456'])
        self.assertEqual(rows[0]['parts'], ['civ'])


class StrictBodyTests(Base):
    def test_client_cannot_supply_a_record_file_or_url(self):
        for extra in ({'record': {'sha256': 'x'}}, {'file': '../../etc/passwd'},
                      {'url': 'http://example.com/a.civsnap'},
                      {'civ': {'endYear': 9}}):
            body = {'import_id': 'sn_abcdef123456', 'base_year': 200}
            body.update(extra)
            res = self.post('/api/inner/history/previews', body)
            self.assertEqual(res.status_code, 422, '%r 应被拒' % (extra,))

    def test_unknown_import_is_refused(self):
        res = self.post('/api/inner/history/previews',
                        {'import_id': 'sn_000000000000', 'base_year': 200})
        self.assertEqual(res.status_code, 400)
        self.assertIn('找不到这个导入记录', res.json()['detail'])

    def test_year_past_end_year_is_refused_by_the_replay(self):
        res = self.post('/api/inner/history/previews',
                        {'import_id': 'sn_abcdef123456', 'base_year': 301})
        self.assertEqual(res.status_code, 400)
        self.assertIn('结束年', res.json()['detail'])


class FullFlowTests(Base):
    def test_preview_page_review_commit_adopt(self):
        before = self.svc.runtime.package()['id']
        draft = self.preview()
        self.assertEqual(self.svc.runtime.package()['id'], before, '预览不得新建版本')

        res = self.client.get('/api/inner/history/previews/%s/page' % draft['id'],
                              params={'category': 'polities', 'page': 0, 'size': 20},
                              headers=self.head())
        self.assertEqual(res.status_code, 200)
        page = res.json()
        self.assertTrue(page['items'])
        ref = page['items'][0]['ref']

        res = self.post('/api/inner/history/previews/%s/review' % draft['id'],
                        {'entries': [{'ref': ref}],
                         'disclosure': {'public_refs': [ref]},
                         'expected_revision': draft['revision']})
        self.assertEqual(res.status_code, 200, res.text)
        reviewed = res.json()
        self.assertEqual(reviewed['revision'], 1)

        res = self.post('/api/inner/history/previews/%s/commit' % draft['id'],
                        {'expected_revision': reviewed['revision']})
        self.assertEqual(res.status_code, 200, res.text)
        snapshot = res.json()['snapshot']
        self.assertEqual(snapshot['story']['base_story_revision'], before)

        res = self.post('/api/inner/history/snapshots/%s/adopt' % snapshot['id'],
                        {'expected_story_revision': before})
        self.assertEqual(res.status_code, 200, res.text)
        revision = res.json()['revision']
        self.assertNotEqual(revision, before)
        block = self.svc.runtime.package(revision)['story']['mechanics']['history']
        self.assertEqual([e['snapshot_id'] for e in block['entries']], [snapshot['id']])

    def test_stale_draft_revision_is_refused_over_http(self):
        draft = self.preview()
        res = self.post('/api/inner/history/previews/%s/review' % draft['id'],
                        {'entries': [{'ref': draft['document']['polities']['items'][0]['ref']}],
                         'expected_revision': 9})
        self.assertEqual(res.status_code, 400)
        self.assertIn('刷新', res.json()['detail'])

    def test_stale_story_revision_is_refused_over_http(self):
        draft = self.preview()
        ref = draft['document']['polities']['items'][0]['ref']
        reviewed = self.post('/api/inner/history/previews/%s/review' % draft['id'],
                             {'entries': [{'ref': ref}], 'expected_revision': 0}).json()
        snapshot = self.post('/api/inner/history/previews/%s/commit' % draft['id'],
                             {'expected_revision': reviewed['revision']}).json()['snapshot']
        res = self.post('/api/inner/history/snapshots/%s/adopt' % snapshot['id'],
                        {'expected_story_revision': 'not-the-base'})
        self.assertEqual(res.status_code, 400)


class PackageProjectionTests(Base):
    def adopted(self):
        draft = self.preview(260)
        page = self.client.get('/api/inner/history/previews/%s/page' % draft['id'],
                               params={'category': 'annals', 'page': 0, 'size': 5},
                               headers=self.head()).json()
        ref = page['items'][0]['ref']
        reviewed = self.post('/api/inner/history/previews/%s/review' % draft['id'],
                             {'entries': [{'ref': ref}],
                              'disclosure': {'public_refs': [ref],
                                             'summaries': {ref: '公开的一句'}},
                              'expected_revision': 0}).json()
        snapshot = self.post('/api/inner/history/previews/%s/commit' % draft['id'],
                             {'expected_revision': reviewed['revision']}).json()['snapshot']
        base = self.svc.runtime.package()['id']
        result = self.post('/api/inner/history/snapshots/%s/adopt' % snapshot['id'],
                           {'expected_story_revision': base}).json()
        return snapshot, result['revision'], ref

    def test_player_projection_reads_the_package_not_the_store(self):
        snapshot, revision, ref = self.adopted()
        # A journey binds its own revision; the projection reads *that* package.
        session = {'revision': revision}
        package = self.svc.runtime.package(session['revision'])
        rows = whs.package_history_public(package['story'], session)
        self.assertTrue(rows)
        self.assertEqual(rows[0]['summary'], '公开的一句')
        # delete the store row: the package copy is what a journey reads
        with self.svc.store.transact() as db:
            db.execute('DELETE FROM documents WHERE kind=? AND id=?',
                       (whs.SNAPSHOT_KIND, snapshot['id']))
        again = whs.package_history_public(
            self.svc.runtime.package(revision)['story'], session)
        self.assertEqual(again, rows)

    def test_old_journey_revision_sees_no_history(self):
        snapshot, revision, ref = self.adopted()
        # a journey created before the adoption is bound to the earlier package
        older = [row['id'] for row in self.svc.store.all('package') if row['id'] != revision]
        self.assertTrue(older)
        for old_id in older:
            rows = whs.package_history_public(
                self.svc.runtime.package(old_id)['story'], {'revision': old_id})
            self.assertEqual(rows, [], '早期故事包没有这段历史')

    def test_undisclosed_entry_never_reaches_the_player(self):
        draft = self.preview(260)
        page = self.client.get('/api/inner/history/previews/%s/page' % draft['id'],
                               params={'category': 'annals', 'page': 0, 'size': 2},
                               headers=self.head()).json()
        a, b = page['items'][0]['ref'], page['items'][1]['ref']
        reviewed = self.post('/api/inner/history/previews/%s/review' % draft['id'],
                             {'entries': [{'ref': a}, {'ref': b}],
                              'disclosure': {'public_refs': [a]},
                              'expected_revision': 0}).json()
        snapshot = self.post('/api/inner/history/previews/%s/commit' % draft['id'],
                             {'expected_revision': reviewed['revision']}).json()['snapshot']
        base = self.svc.runtime.package()['id']
        revision = self.post('/api/inner/history/snapshots/%s/adopt' % snapshot['id'],
                             {'expected_story_revision': base}).json()['revision']
        rows = whs.package_history_public(
            self.svc.runtime.package(revision)['story'], {'revision': revision})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['ref'], a)

    def test_tampered_package_snapshot_is_refused(self):
        snapshot, revision, ref = self.adopted()
        story = json.loads(json.dumps(self.svc.runtime.package(revision)['story']))
        story['mechanics']['history']['entries'][0]['snapshot']['base_year'] = 999
        with self.assertRaises(whs.HistoryError):
            whs.validate_package_history(story)

    def test_unknown_key_in_history_block_is_refused(self):
        snapshot, revision, ref = self.adopted()
        story = json.loads(json.dumps(self.svc.runtime.package(revision)['story']))
        story['mechanics']['history']['extra'] = 1
        with self.assertRaises(whs.HistoryError):
            whs.validate_package_history(story)

    def test_package_without_history_is_untouched(self):
        self.assertTrue(whs.validate_package_history({'mechanics': {}}))
        self.assertEqual(whs.package_history_public({'mechanics': {}}, {'revision': 'x'}), [])


class MapLinkTests(Base):
    """作者显式「本图为开局地图」是独立动作，与采纳历史互不代劳。"""

    def test_link_sets_the_map_without_touching_history(self):
        base = self.svc.runtime.package()['id']
        res = self.post('/api/inner/history/map-link',
                        {'import_id': 'sn_abcdef123456',
                         'expected_story_revision': base})
        self.assertEqual(res.status_code, 200, res.text)
        body = res.json()
        self.assertFalse(body['reused'])
        story = self.svc.runtime.package(body['revision'])['story']
        self.assertEqual(story['mechanics']['map']['import_id'], 'sn_abcdef123456')
        self.assertNotIn('history', story['mechanics'], '关联地图不得顺手采纳历史')

    def test_linking_twice_is_idempotent(self):
        base = self.svc.runtime.package()['id']
        first = self.post('/api/inner/history/map-link',
                          {'import_id': 'sn_abcdef123456',
                           'expected_story_revision': base}).json()
        second = self.post('/api/inner/history/map-link',
                           {'import_id': 'sn_abcdef123456',
                            'expected_story_revision': first['revision']}).json()
        self.assertTrue(second['reused'])
        self.assertEqual(second['revision'], first['revision'])

    def test_stale_revision_is_refused(self):
        res = self.post('/api/inner/history/map-link',
                        {'import_id': 'sn_abcdef123456',
                         'expected_story_revision': 'not-the-base'})
        self.assertEqual(res.status_code, 400)
        self.assertIn('刷新', res.json()['detail'])

    def test_swapping_the_map_under_foreign_history_is_refused(self):
        draft = self.preview()
        ref = draft['document']['polities']['items'][0]['ref']
        reviewed = self.post('/api/inner/history/previews/%s/review' % draft['id'],
                             {'entries': [{'ref': ref}], 'expected_revision': 0}).json()
        snapshot = self.post('/api/inner/history/previews/%s/commit' % draft['id'],
                             {'expected_revision': reviewed['revision']}).json()['snapshot']
        base = self.svc.runtime.package()['id']
        adopted = self.post('/api/inner/history/snapshots/%s/adopt' % snapshot['id'],
                            {'expected_story_revision': base}).json()
        self.store.put('map_import', 'sn_111111111111',
                       import_record(import_id='sn_111111111111'))
        res = self.post('/api/inner/history/map-link',
                        {'import_id': 'sn_111111111111',
                         'expected_story_revision': adopted['revision']})
        self.assertEqual(res.status_code, 400)
        self.assertIn('两个世界', res.json()['detail'])

    def test_unknown_import_is_refused(self):
        base = self.svc.runtime.package()['id']
        res = self.post('/api/inner/history/map-link',
                        {'import_id': 'sn_999999999999',
                         'expected_story_revision': base})
        self.assertEqual(res.status_code, 400)

    def test_extra_keys_are_refused(self):
        base = self.svc.runtime.package()['id']
        res = self.post('/api/inner/history/map-link',
                        {'import_id': 'sn_abcdef123456',
                         'expected_story_revision': base,
                         'adopt_history': True})
        self.assertEqual(res.status_code, 422, '关联地图不接受任何“顺手做点别的”开关')


class SourceMatchingTests(Base):
    def test_history_from_another_import_is_refused_when_map_is_linked(self):
        draft = self.preview()
        ref = draft['document']['polities']['items'][0]['ref']
        reviewed = self.post('/api/inner/history/previews/%s/review' % draft['id'],
                             {'entries': [{'ref': ref}], 'expected_revision': 0}).json()
        snapshot = self.post('/api/inner/history/previews/%s/commit' % draft['id'],
                             {'expected_revision': reviewed['revision']}).json()['snapshot']
        # link the package to a *different* import, then try to adopt this history
        story = json.loads(json.dumps(self.svc.runtime.package()['story']))
        story.setdefault('mechanics', {})['map'] = {
            'kind': 'civ_atlas', 'import_id': 'sn_deadbeef0000',
            'fog': {'reveal_radius_km': 300}}
        base = self.svc.runtime.commit_package(story,
                                              self.svc.runtime.package()['characters'],
                                              '链接另一份地图')
        res = self.post('/api/inner/history/snapshots/%s/adopt' % snapshot['id'],
                        {'expected_story_revision': base})
        self.assertEqual(res.status_code, 400)
        self.assertIn('两个世界', res.json()['detail'])


if __name__ == '__main__':
    unittest.main()
