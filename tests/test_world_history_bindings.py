# -*- coding: utf-8 -*-
"""接线阻塞的三处边界：故事身份固定、导入文件目录、terrain 关联。

每条对应一个真实的接线失败模式：

A. 预览草稿没固定故事身份 → 旧世界的草稿能给新世界的当前 revision 采纳。
B. 读导入文件的目录与导入时写的目录不一致 → 生产环境里历史永远读不到自己的原件。
C. 预览不带 terrain 关联 → 有地形大事的世界会把基准年地图盲称 matched。

另含 review 的 CAS（多标签页不得静默覆盖选择）。
"""
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from app import world_history_store as whs
from app.service import Service
from app.storage import Store

from tests.test_civ_atlas_history import civ_block

ROOT = Path(__file__).resolve().parents[1]
REAL_EXPORT = Path(r'D:/Vantaloom/data/temp/project-proj-1792851796-712e540fb0'
                   r'/scratch/real-verify-data/map_imports'
                   r'/2f364872015835be5a905876c6bdf5ae.civsnap')


def import_record(sha='b' * 64, file='abcdef.civsnap'):
    return {
        'id': 'sn_abcdef123456', 'sha256': sha, 'bytes': 4609307, 'file': file,
        'parts': [{'name': 'civ', 'sum': 'e' * 64, 'sum_verified_by': 'server',
                   'bytes': 1932123, 'zip': 'gzip'}],
        'source': {'world_id': 'wA', 'generator_version': 45, 'snapshot_format': 1,
                   'spec_commit': '0939c5f1622a5e45cfc16f645ea3845993ab3985'},
    }


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.svc = Service(Store(Path(self.tmp.name) / 'h.sqlite3'), ROOT)
        self.svc.provider.configure({'offline': True})
        self.rt = self.svc.runtime
        self.block = civ_block()
        self.terrain = {'eras_block': False, 'era_until': [], 'upheaval_years': []}
        self.hist = whs.WorldHistoryService(
            self.rt, load_civ=lambda record: (self.block, dict(self.terrain)))
        self.record = import_record()

    def preview(self, year=200, **kw):
        return self.hist.preview(self.record, base_year=year, branch='main', **kw)

    def switched_world(self, story_id='world-B'):
        """Move the runtime to a different story package, keeping the old one readable."""
        story = json.loads(json.dumps(self.rt.package()['story']))
        characters = json.loads(json.dumps(self.rt.package()['characters']))
        characters['id'] = story_id                 # the character package id changes too
        story['id'] = story_id
        story['character_package_id'] = story_id    # and the story must link to it
        return self.rt.commit_package(story, characters, '切到另一个世界')


class StoryIdentityTests(Base):
    """A: a draft is pinned to its story; adopting into another world is refused."""

    def test_preview_records_the_story_identity(self):
        draft = self.preview()['preview']
        self.assertEqual(draft['base_story_id'], self.rt.package()['story']['id'])
        self.assertEqual(draft['base_story_revision'], self.rt.package()['id'])
        self.assertEqual(draft['revision'], 0)

    def test_two_worlds_never_share_a_preview_id(self):
        first = self.preview()['preview']['id']
        self.switched_world()
        second = self.preview()['preview']['id']
        self.assertNotEqual(first, second, '不同故事包不得复用同一个回放草稿')

    def test_review_after_switching_world_is_refused(self):
        draft = self.preview()['preview']
        ref = self.hist.page(draft['id'], 'polities')['items'][0]['ref']
        self.switched_world()
        with self.assertRaises(whs.HistoryError) as caught:
            self.hist.review(draft['id'], entries=[{'ref': ref}])
        self.assertIn('故事包', str(caught.exception))

    def test_adopt_old_preview_into_new_world_is_refused_even_with_current_revision(self):
        """The exact bypass: submit the *current* revision of another world."""
        draft = self.preview()['preview']
        ref = self.hist.page(draft['id'], 'polities')['items'][0]['ref']
        self.hist.review(draft['id'], entries=[{'ref': ref}],
                         disclosure={'public_refs': [ref]})
        snapshot = self.hist.commit(draft['id'])['snapshot']
        new_revision = self.switched_world()
        self.assertEqual(self.rt.package()['id'], new_revision)
        with self.assertRaises(whs.HistoryError) as caught:
            self.hist.adopt(snapshot['id'], new_revision)
        self.assertIn('新世界', str(caught.exception))
        # and nothing was written into that package
        self.assertNotIn('history',
                         (self.rt.package()['story'].get('mechanics') or {}))

    def test_adopt_against_a_newer_revision_of_the_same_world_is_refused(self):
        draft = self.preview()['preview']
        ref = self.hist.page(draft['id'], 'polities')['items'][0]['ref']
        self.hist.review(draft['id'], entries=[{'ref': ref}])
        snapshot = self.hist.commit(draft['id'])['snapshot']
        story = json.loads(json.dumps(self.rt.package()['story']))
        newer = self.rt.commit_package(story, self.rt.package()['characters'], '同一世界的新版本')
        with self.assertRaises(whs.HistoryError) as caught:
            self.hist.adopt(snapshot['id'], newer)
        self.assertIn('审阅', str(caught.exception))

    def test_retry_on_the_same_world_and_revision_is_still_idempotent(self):
        draft = self.preview()['preview']
        ref = self.hist.page(draft['id'], 'polities')['items'][0]['ref']
        self.hist.review(draft['id'], entries=[{'ref': ref}])
        snapshot = self.hist.commit(draft['id'])['snapshot']
        base = self.rt.package()['id']
        first = self.hist.adopt(snapshot['id'], base)
        second = self.hist.adopt(snapshot['id'], first['revision'])
        self.assertTrue(second['reused'])
        self.assertEqual(first['revision'], second['revision'])


class ImportDirectoryTests(unittest.TestCase):
    """B: the reader looks exactly where the importer wrote the file."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.data = self.repo / 'data'
        self.data.mkdir(parents=True, exist_ok=True)
        # The runtime loads its story package from <root>/StoryPackage; give the sandbox one.
        shutil.copytree(ROOT / 'StoryPackage' / '玄陆', self.repo / 'StoryPackage' / '玄陆',
                       ignore=shutil.ignore_patterns('.backup_*', '.pending_*'))
        # The runtime also loads the matching character package from <root>/character_packages.
        shutil.copytree(ROOT / 'character_packages', self.repo / 'character_packages',
                       ignore=shutil.ignore_patterns('.backup_*', '.pending_*'))
        if not REAL_EXPORT.exists():
            self.skipTest('真实 .civsnap 不在预期路径（**未验真**）')
        self.target = self.data / 'map_imports' / 'real.civsnap'
        self.target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REAL_EXPORT, self.target)
        self.sha = hashlib.sha256(self.target.read_bytes()).hexdigest()

    def test_history_reads_from_beside_the_production_database(self):
        store = Store(self.data / 'textiledream.sqlite3')
        service = Service(store, self.repo)
        service.provider.configure({'offline': True})
        svc = whs.WorldHistoryService(service.runtime)
        record = import_record(sha=self.sha, file=self.target.name)
        result = svc.preview(record, base_year=1500, branch='main')
        self.assertEqual(result['preview']['document']['identity']['civ_seed'], 531844)

    def test_no_fallback_to_the_repo_root(self):
        """The importer never writes ``<repo>/map_imports``; the reader must not look there."""
        store = Store(self.data / 'textiledream.sqlite3')
        service = Service(store, self.repo)
        service.provider.configure({'offline': True})
        svc = whs.WorldHistoryService(service.runtime)
        moved = self.repo / 'map_imports' / 'real.civsnap'
        moved.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(self.target), str(moved))
        self.assertFalse((self.data / 'map_imports' / 'real.civsnap').exists())
        with self.assertRaises(whs.HistoryError):
            svc.preview(import_record(sha=self.sha, file='real.civsnap'),
                        base_year=1500, branch='main')
        self.assertEqual(svc._data_root(), self.data, '永远不会回退到仓库根')


class ImportRootRuleTests(unittest.TestCase):
    """``_data_root`` is ``store.path.parent``, independent of any sample file."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        shutil.copytree(ROOT / 'StoryPackage' / '玄陆', self.repo / 'StoryPackage' / '玄陆',
                       ignore=shutil.ignore_patterns('.backup_*', '.pending_*'))
        shutil.copytree(ROOT / 'character_packages', self.repo / 'character_packages',
                       ignore=shutil.ignore_patterns('.backup_*', '.pending_*'))

    def test_temp_store_reads_its_own_directory(self):
        store = Store(self.repo / 'sandbox' / 'x.sqlite3')
        service = Service(store, self.repo)
        svc = whs.WorldHistoryService(service.runtime)
        self.assertEqual(svc._data_root(), (self.repo / 'sandbox').resolve())

    def test_production_store_reads_beside_its_own_database(self):
        store = Store(self.repo / 'data' / 'textiledream.sqlite3')
        service = Service(store, self.repo)
        svc = whs.WorldHistoryService(service.runtime)
        self.assertEqual(svc._data_root(), (self.repo / 'data').resolve(),
                         '与 web._import_root() 一致，不是仓库根')


class TerrainAssociationTests(Base):
    """C: the eras block reaches the replay, so the map is not blindly called matched."""

    def test_eras_segments_mark_an_earlier_year_as_unmatched(self):
        self.terrain = {'eras_block': True, 'era_until': [250], 'upheaval_years': []}
        draft = self.preview(200)['preview']
        terrain = draft['document']['terrain']
        self.assertEqual(terrain['state'], 'unmatched')
        self.assertTrue(terrain['era_block_present'])
        self.assertFalse(terrain['base_year_uses_current_map'])

    def test_year_after_the_last_era_uses_the_current_map(self):
        self.terrain = {'eras_block': True, 'era_until': [250], 'upheaval_years': []}
        draft = self.preview(260)['preview']
        self.assertEqual(draft['document']['terrain']['state'], 'current_terrain')

    def test_no_eras_and_no_upheaval_is_same_terrain(self):
        draft = self.preview(200)['preview']
        self.assertEqual(draft['document']['terrain']['state'], 'same_terrain_all_years')

    def test_terrain_is_frozen_into_the_preview_and_snapshot(self):
        self.terrain = {'eras_block': True, 'era_until': [250], 'upheaval_years': []}
        draft = self.preview(200)['preview']
        self.assertEqual(draft['terrain']['state'], 'unmatched')
        ref = self.hist.page(draft['id'], 'polities')['items'][0]['ref']
        self.hist.review(draft['id'], entries=[{'ref': ref}])
        snapshot = self.hist.commit(draft['id'])['snapshot']
        self.assertEqual(snapshot['terrain']['state'], 'unmatched')

    def test_empty_eras_block_is_not_an_era(self):
        """A real export with ``eras: []`` carries no terrain event at all."""
        parts = [{'name': 'eras', '_bytes': self._empty_eras_part(), 'zip': 'none'}]
        terrain = whs._terrain_from_parts(parts)
        self.assertFalse(terrain['eras_block'])
        self.assertEqual(terrain['era_until'], [])

    def test_undecodable_eras_part_does_not_claim_matched(self):
        parts = [{'name': 'eras', '_bytes': b'not-a-part', 'zip': 'none'}]
        terrain = whs._terrain_from_parts(parts)
        self.assertFalse(terrain['eras_block'])
        self.assertEqual(terrain['era_until'], [])

    @staticmethod
    def _empty_eras_part():
        import struct
        meta = json.dumps({'baseKey': None, 'eras': []}).encode('utf-8')
        raw = b'CIVSNAP1' + struct.pack('<I', len(meta)) + meta
        return raw + b'\x00' * ((8 - len(raw) % 8) % 8)


class ReviewCasTests(Base):
    """Two author tabs must not silently overwrite each other's selection."""

    def test_stale_expected_draft_revision_is_refused(self):
        draft = self.preview()['preview']
        ref = self.hist.page(draft['id'], 'polities')['items'][0]['ref']
        # Simulate a second tab that read revision 0, then someone else saved revision 5.
        stored = self.hist.get_preview(draft['id'])
        stored['revision'] = 5
        self.rt.store.put(whs.PREVIEW_KIND, draft['id'], stored)
        with self.assertRaises(whs.HistoryError) as caught:
            self.hist.review(draft['id'], entries=[{'ref': ref}], expected_revision=0)
        self.assertIn('刷新', str(caught.exception))
        # nothing was written: still revision 5, still an unreviewed draft
        self.assertEqual(self.hist.get_preview(draft['id'])['revision'], 5)
        self.assertEqual(self.hist.get_preview(draft['id'])['status'], 'draft')

    def test_review_advances_the_draft_revision(self):
        draft = self.preview()['preview']
        ref = self.hist.page(draft['id'], 'polities')['items'][0]['ref']
        reviewed = self.hist.review(draft['id'], entries=[{'ref': ref}],
                                    expected_revision=0)
        self.assertEqual(reviewed['revision'], 1)

    def test_commit_can_pin_the_reviewed_revision(self):
        draft = self.preview()['preview']
        ref = self.hist.page(draft['id'], 'polities')['items'][0]['ref']
        self.hist.review(draft['id'], entries=[{'ref': ref}])
        result = self.hist.commit(draft['id'], expected_revision=1)
        self.assertTrue(result['created'])
        with self.assertRaises(whs.HistoryError):
            self.hist.commit(draft['id'], expected_revision=0)


if __name__ == '__main__':
    unittest.main()
