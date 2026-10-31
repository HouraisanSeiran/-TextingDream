# -*- coding: utf-8 -*-
"""历史采纳服务：预览 → 作者审阅 → 固定快照 → 采纳进故事包。

全部用**临时库**；civ 块用自造 fixture（经 `load_civ` 注入），不读用户 `data/`，
不启服务、不跑上游。真实文件路径存在时才跑那条 probe。
"""
import json
import tempfile
import unittest
from pathlib import Path

from app import world_basis
from app import world_history_store as whs
from app.service import Service
from app.storage import Store

from tests.test_civ_atlas_history import civ_block

ROOT = Path(__file__).resolve().parents[1]
REAL_EXPORT = Path(r'D:/Vantaloom/data/temp/project-proj-1792851796-712e540fb0'
                   r'/scratch/real-verify-data/map_imports'
                   r'/2f364872015835be5a905876c6bdf5ae.civsnap')


def import_record(sha='b' * 64):
    """A record shaped like `civ_atlas_snapshot.create_import` returns."""
    return {
        'id': 'sn_abcdef123456',
        'format': 'civ_atlas_snapshot_v1',
        'sha256': sha,
        'bytes': 4609307,
        'file': 'abcdef.civsnap',
        'parts': [
            {'name': 'map', 'sum': 'c' * 64, 'sum_verified_by': 'server',
             'bytes': 2675727, 'zip': 'gzip'},
            {'name': 'eras', 'sum': 'd' * 64, 'sum_verified_by': 'server',
             'bytes': 190, 'zip': 'gzip'},
            {'name': 'civ', 'sum': 'e' * 64, 'sum_verified_by': 'server',
             'bytes': 1932123, 'zip': 'gzip'},
        ],
        'source': {
            'project': 'civ-atlas',
            'commit': '0939c5f1622a5e45cfc16f645ea3845993ab3985',
            'spec_commit': '0939c5f1622a5e45cfc16f645ea3845993ab3985',
            'generator_version': 45,
            'snapshot_format': 1,
            'recipe': 'dc9e079d0cb8',
            'world_id': 'wmvrpuwi29m3yi',
        },
    }


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.svc = Service(Store(Path(self.tmp.name) / 'h.sqlite3'), ROOT)
        self.svc.provider.configure({'offline': True})
        self.rt = self.svc.runtime
        self.block = civ_block()
        self.terrain = {'eras_block': True, 'era_until': [250], 'upheaval_years': []}
        self.hist = whs.WorldHistoryService(
            self.rt, load_civ=lambda record: (self.block, dict(self.terrain)))
        self.record = import_record()

    def preview(self, year=200, **kw):
        return self.hist.preview(self.record, base_year=year, branch='main', **kw)


class PreviewTests(Base):
    def test_preview_does_not_touch_the_story_or_a_session(self):
        before = self.rt.package()
        result = self.preview()
        after = self.rt.package()
        self.assertEqual(before['id'], after['id'], '预览不得新建故事包版本')
        self.assertNotIn('history', (after['story'].get('mechanics') or {}))
        self.assertEqual(len(self.rt.store.all('package')), len(self.rt.store.all('package')))
        self.assertEqual(result['preview']['status'], whs.STATUS_DRAFT)
        self.assertFalse(result['preview']['reviewed'])

    def test_preview_is_idempotent_on_the_same_request(self):
        first = self.preview()
        second = self.preview()
        self.assertFalse(first['reused'])
        self.assertTrue(second['reused'])
        self.assertEqual(first['preview']['id'], second['preview']['id'])
        self.assertEqual(len(self.rt.store.all(whs.PREVIEW_KIND)), 1)

    def test_different_year_is_a_different_preview(self):
        a = self.preview(200)
        b = self.preview(260)
        self.assertNotEqual(a['preview']['id'], b['preview']['id'])

    def test_year_after_end_year_is_refused(self):
        with self.assertRaises(whs.HistoryError):
            self.preview(301)

    def test_preview_records_the_source_pin(self):
        draft = self.preview()['preview']
        self.assertEqual(draft['source_sha256'], 'b' * 64)
        self.assertEqual([p['name'] for p in draft['parts']], ['map', 'eras', 'civ'])
        self.assertEqual(draft['parts'][0]['sum_verified_by'], 'server')

    def test_missing_import_hash_is_refused(self):
        with self.assertRaises(whs.HistoryError):
            self.hist.preview(dict(self.record, sha256=''), base_year=200)

    def test_bad_budget_is_refused(self):
        # ``None`` means "use the default", so only non-positive / non-int values are refused.
        for bad in (0, -1, 'x', 1.5):
            with self.assertRaises(whs.HistoryError):
                self.hist.preview(self.record, base_year=200, max_events=bad)
        with self.assertRaises(whs.HistoryError):
            self.hist.preview(self.record, base_year=200, max_entities=0)


class PageTests(Base):
    def test_page_is_explicit_not_silent_truncation(self):
        draft = self.preview(260)['preview']
        total = draft['document']['annals']['counts']['inside_window']
        self.assertGreater(total, 2)
        first = self.hist.page(draft['id'], 'annals', page=0, size=2)
        self.assertEqual(len(first['items']), 2)
        self.assertEqual(first['total'], total)
        self.assertTrue(first['truncated_by_page'])
        self.assertEqual(first['pages'], (total + 1) // 2)

    def test_page_beyond_the_end_is_refused(self):
        draft = self.preview(260)['preview']
        with self.assertRaises(whs.HistoryError):
            self.hist.page(draft['id'], 'annals', page=99, size=5)

    def test_unknown_category_is_refused(self):
        draft = self.preview()['preview']
        with self.assertRaises(whs.HistoryError):
            self.hist.page(draft['id'], 'religion', page=0, size=5)

    def test_people_page_never_carries_a_death_year(self):
        draft = self.preview(200)['preview']
        page = self.hist.page(draft['id'], 'people', page=0, size=10)
        for item in page['items']:
            self.assertNotIn('died', item)


class ReviewTests(Base):
    def first_ref(self, draft, category='polities'):
        return self.hist.page(draft['id'], category)['items'][0]['ref']

    def test_review_requires_known_refs(self):
        draft = self.preview()['preview']
        with self.assertRaises(whs.HistoryError):
            self.hist.review(draft['id'], entries=[{'ref': 'casnap:nope/polity/9'}])

    def test_review_marks_the_decision_without_touching_the_story(self):
        draft = self.preview()['preview']
        ref = self.first_ref(draft)
        before = self.rt.package()['id']
        reviewed = self.hist.review(draft['id'], entries=[{'ref': ref}])
        self.assertEqual(reviewed['status'], 'reviewed')
        self.assertEqual(reviewed['counts']['selected'], 1)
        self.assertEqual(self.rt.package()['id'], before)

    def test_reviewing_twice_is_refused(self):
        draft = self.preview()['preview']
        ref = self.first_ref(draft)
        self.hist.review(draft['id'], entries=[{'ref': ref}])
        with self.assertRaises(whs.HistoryError):
            self.hist.review(draft['id'], entries=[{'ref': ref}])

    def test_public_ref_must_be_inside_the_selection(self):
        draft = self.preview(260)['preview']
        ref = self.first_ref(draft, 'annals')
        other = self.hist.page(draft['id'], 'annals')['items'][1]['ref']
        with self.assertRaises(whs.HistoryError):
            self.hist.review(draft['id'], entries=[{'ref': ref}],
                             disclosure={'public_refs': [other]})

    def test_empty_selection_is_refused(self):
        draft = self.preview()['preview']
        with self.assertRaises(whs.HistoryError):
            self.hist.review(draft['id'], entries=[])


class LinkTests(Base):
    def test_linking_an_unknown_settlement_is_refused(self):
        draft = self.preview(200)['preview']
        with self.assertRaises(whs.HistoryError):
            self.hist.review(draft['id'], entries=[{'ref': self._any(draft)}],
                             local_links={'casnap:nope/settlement/1': 'loc_x'})

    def _any(self, draft):
        return self.hist.page(draft['id'], 'polities')['items'][0]['ref']

    def test_two_settlements_cannot_share_one_local_location(self):
        draft = self.preview(260)['preview']
        page = self.hist.page(draft['id'], 'settlements', size=5)
        if len(page['items']) < 2:
            self.skipTest('这一次回放的城镇不足两个')
        a, b = page['items'][0]['ref'], page['items'][1]['ref']
        with self.assertRaises(whs.HistoryError):
            self.hist.review(draft['id'], entries=[{'ref': a}],
                             local_links={a: 'loc_1', b: 'loc_1'})

    def test_link_is_idempotent_and_recorded_once(self):
        draft = self.preview(260)['preview']
        page = self.hist.page(draft['id'], 'settlements', size=5)
        ref = page['items'][0]['ref']
        reviewed = self.hist.review(draft['id'], entries=[{'ref': ref}],
                                    local_links={ref: 'loc_1'})
        self.assertEqual(reviewed['selection']['local_links'], {ref: 'loc_1'})
        self.assertEqual(reviewed['counts']['linked'], 1)


class CommitTests(Base):
    def reviewed(self, year=200):
        draft = self.preview(year)['preview']
        ref = self.hist.page(draft['id'], 'polities')['items'][0]['ref']
        self.hist.review(draft['id'], entries=[{'ref': ref}],
                         disclosure={'public_refs': [ref]})
        return draft['id'], ref

    def test_commit_requires_a_reviewed_preview(self):
        draft = self.preview()['preview']
        with self.assertRaises(whs.HistoryError):
            self.hist.commit(draft['id'])

    def test_commit_is_idempotent(self):
        preview_id, _ref = self.reviewed()
        first = self.hist.commit(preview_id)
        second = self.hist.commit(preview_id)
        self.assertTrue(first['created'])
        self.assertFalse(second['created'])
        self.assertEqual(first['snapshot']['id'], second['snapshot']['id'])
        self.assertEqual(len(self.rt.store.all(whs.SNAPSHOT_KIND)), 1)

    def test_snapshot_is_self_contained_and_pins_the_source(self):
        preview_id, _ref = self.reviewed()
        snapshot = self.hist.commit(preview_id)['snapshot']
        self.assertEqual(snapshot['source']['content_sha256'], 'b' * 64)
        self.assertEqual(len(snapshot['source']['parts']), 3)
        self.assertEqual(snapshot['source']['parts'][0]['sum'], 'c' * 64)
        self.assertEqual(snapshot['world_basis']['world_id'], 'wmvrpuwi29m3yi')
        self.assertEqual(snapshot['world_basis']['civ_seed'], 4242)
        self.assertEqual(snapshot['world_basis']['civ_seed_source'], 'civ.seed')
        self.assertTrue(snapshot['for_author_review'])
        self.assertFalse(snapshot['auto_canonical'])

    def test_snapshot_field_status_matches_world_basis(self):
        preview_id, _ref = self.reviewed()
        result = self.hist.commit(preview_id)
        statuses = result['snapshot']['field_status']
        basis = result['world_basis']
        self.assertEqual(basis['history']['state'], world_basis.STATE_REPLAYED)
        for field, row in statuses.items():
            self.assertEqual(basis['field_status'][field], row['status'], field)
        self.assertIn('region_polity', basis['restorable'])
        self.assertIn('population', basis['not_restorable'])

    def test_tampered_snapshot_is_refused_at_adoption(self):
        preview_id, _ref = self.reviewed()
        snapshot = self.hist.commit(preview_id)['snapshot']
        broken = dict(snapshot, base_year=999)
        self.rt.store.put(whs.SNAPSHOT_KIND, snapshot['id'], broken)
        with self.assertRaises(whs.HistoryError):
            self.hist.adopt(snapshot['id'], self.rt.package()['id'])

    def test_more_picks_than_the_budget_is_refused(self):
        preview_id, _ref = self.reviewed()
        with self.assertRaises(whs.HistoryError):
            self.hist.commit(preview_id, max_entries=0)


class DisclosureTests(Base):
    def snapshot_with_two_picks(self):
        draft = self.preview(260)['preview']
        page = self.hist.page(draft['id'], 'annals', size=2)
        a, b = page['items'][0]['ref'], page['items'][1]['ref']
        self.hist.review(draft['id'], entries=[{'ref': a}, {'ref': b}],
                         disclosure={'public_refs': [a], 'summaries': {a: '公开的一句话'}})
        return self.hist.commit(draft['id'])['snapshot']

    def test_only_disclosed_entries_reach_the_player(self):
        snapshot = self.snapshot_with_two_picks()
        view = self.hist.public_view(snapshot['id'])
        self.assertEqual(len(view['items']), 1)
        self.assertEqual(view['counts']['public'], 1)
        self.assertEqual(view['counts']['withheld'], 1)
        self.assertEqual(view['items'][0]['summary'], '公开的一句话')

    def test_nothing_disclosed_means_nothing_projected(self):
        draft = self.preview()['preview']
        ref = self.hist.page(draft['id'], 'polities')['items'][0]['ref']
        self.hist.review(draft['id'], entries=[{'ref': ref}])
        snapshot = self.hist.commit(draft['id'])['snapshot']
        view = self.hist.public_view(snapshot['id'])
        self.assertEqual(view['items'], [])

    def test_public_person_carries_no_death_year(self):
        draft = self.preview(200)['preview']
        page = self.hist.page(draft['id'], 'people', size=5)
        if not page['items']:
            self.skipTest('这一次回放没有存活人物')
        ref = page['items'][0]['ref']
        self.hist.review(draft['id'], entries=[{'ref': ref}],
                         disclosure={'public_refs': [ref]})
        snapshot = self.hist.commit(draft['id'])['snapshot']
        view = self.hist.public_view(snapshot['id'])
        self.assertTrue(view['items'])
        for item in view['items']:
            self.assertNotIn('died', item)
            self.assertNotIn('fate', item)
            self.assertNotIn('until', item)

    def test_summary_for_an_undisclosed_entry_is_refused(self):
        draft = self.preview(260)['preview']
        page = self.hist.page(draft['id'], 'annals', size=2)
        a, b = page['items'][0]['ref'], page['items'][1]['ref']
        with self.assertRaises(whs.HistoryError):
            self.hist.review(draft['id'], entries=[{'ref': a}, {'ref': b}],
                             disclosure={'public_refs': [a], 'summaries': {b: 'x'}})


class AdoptionTests(Base):
    def snapshot(self, year=200):
        draft = self.preview(year)['preview']
        ref = self.hist.page(draft['id'], 'polities')['items'][0]['ref']
        self.hist.review(draft['id'], entries=[{'ref': ref}],
                         disclosure={'public_refs': [ref]})
        return self.hist.commit(draft['id'])['snapshot']

    def test_adopt_creates_one_new_revision_with_the_snapshot(self):
        snapshot = self.snapshot()
        base = self.rt.package()['id']
        result = self.hist.adopt(snapshot['id'], base)
        self.assertFalse(result['reused'])
        self.assertNotEqual(result['revision'], base)
        package = self.rt.package(result['revision'])
        block = package['story']['mechanics']['history']
        self.assertEqual(block['schema'], whs.MECHANICS_SCHEMA)
        self.assertEqual([e['snapshot_id'] for e in block['entries']], [snapshot['id']])
        self.assertEqual(block['entries'][0]['world_basis_id'],
                         snapshot['world_basis']['id'])

    def test_adopt_twice_does_not_mint_a_second_revision(self):
        snapshot = self.snapshot()
        base = self.rt.package()['id']
        first = self.hist.adopt(snapshot['id'], base)
        second = self.hist.adopt(snapshot['id'], first['revision'])
        self.assertFalse(first['reused'])
        self.assertTrue(second['reused'])
        self.assertEqual(second['revision'], first['revision'])
        entries = self.rt.package()['story']['mechanics']['history']['entries']
        self.assertEqual(len(entries), 1, '重复采纳不得重复条目')

    def test_stale_expected_revision_is_refused(self):
        snapshot = self.snapshot()
        base = self.rt.package()['id']
        self.hist.adopt(snapshot['id'], base)
        # a second, different snapshot adopted against the now-stale base must be refused
        other = self.snapshot(260)
        with self.assertRaises(whs.HistoryError):
            self.hist.adopt(other['id'], base)

    def test_adoption_does_not_change_the_map_link(self):
        story = self.rt.package()['story']
        story.setdefault('mechanics', {})['map'] = {
            'kind': 'civ_atlas', 'import_id': 'sn_abcdef123456',
            'fog': {'reveal_radius_km': 300}}
        revision = self.rt.commit_package(story, self.rt.package()['characters'],
                                         '加地图链接')
        before = self.rt.package(revision)['story']['mechanics']['map']
        snapshot = self.snapshot()
        self.hist.adopt(snapshot['id'], revision)
        after = self.rt.package()['story']['mechanics']['map']
        self.assertEqual(before, after, '采纳历史不得偷改地图来源')

    def test_adoption_index_is_written_once(self):
        snapshot = self.snapshot()
        base = self.rt.package()['id']
        first = self.hist.adopt(snapshot['id'], base)
        second = self.hist.adopt(snapshot['id'], first['revision'])
        self.assertEqual(first['adoption']['id'], second['adoption']['id'])
        self.assertEqual(len(self.rt.store.all(whs.ADOPTION_KIND)), 1)

    def test_adopted_history_survives_losing_the_import_record(self):
        snapshot = self.snapshot()
        self.hist.adopt(snapshot['id'], self.rt.package()['id'])
        # the import record and the whole preview can vanish; the package still reads
        self.rt.store.put(whs.PREVIEW_KIND, 'gone', None)
        reread = self.rt.package()['story']['mechanics']['history']['entries'][0]
        self.assertEqual(reread['snapshot']['entries'][0]['ref'].split('/')[-1], '0')
        self.assertEqual(reread['content_sha256'], 'b' * 64)

    def test_old_journey_revision_is_unaffected(self):
        base = self.rt.package()['id']
        snapshot = self.snapshot()
        self.hist.adopt(snapshot['id'], base)
        old = self.rt.package(base)['story'].get('mechanics', {}).get('history')
        self.assertIsNone(old, '旧版本不应被采纳修改')


class WorldBasisWiringTests(Base):
    def test_build_from_history_marks_replayed(self):
        document = self.preview()['preview']['document']
        basis = world_basis.build_from_history(self.record, document, base_year=200,
                                               branch='main')
        self.assertEqual(basis['history']['state'], world_basis.STATE_REPLAYED)
        self.assertIn('annals', basis['history']['replayed_fields'])
        self.assertEqual(basis['world']['civ_seed'], 4242)
        self.assertEqual(basis['world']['civ_seed_source'], 'civ.seed')

    def test_year_mismatch_is_refused(self):
        document = self.preview()['preview']['document']
        with self.assertRaises(ValueError):
            world_basis.build_from_history(self.record, document, base_year=260,
                                           branch='main')

    def test_branch_mismatch_is_refused(self):
        document = self.preview()['preview']['document']
        with self.assertRaises(ValueError):
            world_basis.build_from_history(self.record, document, base_year=200,
                                           branch='alt')

    def test_source_hash_mismatch_is_refused(self):
        document = self.preview()['preview']['document']
        other = dict(self.record, sha256='f' * 64)
        with self.assertRaises(ValueError):
            world_basis.build_from_history(other, document, base_year=200,
                                           branch='main')

    def test_old_build_keeps_unresolved_and_integer_year(self):
        basis = world_basis.build(self.record, base_year=1500)
        self.assertEqual(basis['history']['state'], world_basis.STATE_UNRESOLVED)
        self.assertEqual(basis['restorable'], [])
        with self.assertRaises(ValueError):
            world_basis.build(self.record, base_year=1.5)

    def test_fractional_year_flows_through_the_history_path(self):
        document = self.preview(50.5)['preview']['document']
        basis = world_basis.build_from_history(self.record, document, base_year=50.5,
                                               branch='main')
        self.assertEqual(basis['selection']['base_year'], 50.5)
        self.assertEqual(basis['selection']['base_year'], document['selection']['base_year'])


class RealFileProbeTests(Base):
    """真实导出的 ``.civsnap``（只读）：走默认的读文件路径，不注入 block。"""

    def setUp(self):
        super().setUp()
        if not REAL_EXPORT.exists():
            self.skipTest('真实 .civsnap 不在预期路径（**未验真**）')

    def test_reads_the_registered_file_and_replays(self):
        import shutil
        root = Path(self.tmp.name)
        target = root / 'map_imports' / ('%s.civsnap' % ('a' * 32))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REAL_EXPORT, target)
        import hashlib
        sha = hashlib.sha256(target.read_bytes()).hexdigest()
        record = import_record(sha=sha)
        record['file'] = target.name
        service = whs.WorldHistoryService(self.rt)          # default loader: reads bytes
        result = service.preview(record, base_year=1500, branch='main')
        draft = result['preview']
        self.assertEqual(draft['base_year'], 1500)
        self.assertEqual(draft['document']['region_replay']['status'], 'as_of_interval')
        self.assertEqual(draft['document']['identity']['civ_seed'], 531844)

    def test_swapped_file_is_refused(self):
        import shutil
        root = Path(self.tmp.name)
        target = root / 'map_imports' / 'wrong.civsnap'
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REAL_EXPORT, target)
        record = import_record(sha='b' * 64)               # pinned hash does not match
        record['file'] = target.name
        service = whs.WorldHistoryService(self.rt)
        with self.assertRaises(whs.HistoryError):
            service.preview(record, base_year=1500, branch='main')


if __name__ == '__main__':
    unittest.main()
