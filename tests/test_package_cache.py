"""Runtime.package 按 revision 缓存：命中不再开库、调用方改返回值不污染缓存、新提交读到新内容。"""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.storage import Store
from tests.fixtures_world import world_service

ROOT = Path(__file__).resolve().parents[1]


class PackageCacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'cache.sqlite3')
        self.service = world_service(self.store, ROOT)
        self.rt = self.service.runtime

    def test_cache_hit_does_not_open_a_connection(self):
        revision = self.rt.package()['id']          # 预热
        with patch.object(Store, 'connect', side_effect=AssertionError('cache hit must not touch sqlite')):
            first = self.rt.package(revision)           # 指定 revision：完全不开库
        self.assertEqual(first['id'], revision)
        # 不指定 revision 时只读 pointer 这一行小记录（pointer 会变，不缓存），不再读整份包体。
        reads = []
        original_get = Store.get

        def spy(store, kind, id, default=None):
            reads.append((kind, id))
            return original_get(store, kind, id, default)
        with patch.object(Store, 'get', spy):
            second = self.rt.package()
        self.assertEqual(second['id'], revision)
        self.assertEqual(reads, [('pointer', 'package')])

    def test_mutating_a_returned_package_does_not_pollute_the_cache(self):
        revision = self.rt.package()['id']
        pristine = copy.deepcopy(self.rt.package(revision))
        victim = self.rt.package(revision)           # 缓存命中的那一份
        victim['story']['title'] = '被污染'
        victim['story']['locations'].clear()
        victim['characters']['characters'].clear()
        again = self.rt.package(revision)
        self.assertEqual(again, pristine)
        self.assertIsNot(again, victim)
        # 首次读（未命中）返回的对象同样不能和缓存共享。
        self.rt._package_cache.clear()
        first = self.rt.package(revision)
        first['story']['title'] = '又被污染'
        self.assertEqual(self.rt.package(revision), pristine)

    def test_new_commit_reads_new_content_and_old_revision_stays(self):
        old = self.rt.package()
        story, characters = copy.deepcopy(old['story']), copy.deepcopy(old['characters'])
        story['title'] = old['story']['title'] + '（新版）'
        new_revision = self.rt.commit_package(story, characters, 'cache test')
        self.assertNotEqual(new_revision, old['id'])
        current = self.rt.package()
        self.assertEqual(current['id'], new_revision)
        self.assertEqual(current['story']['title'], story['title'])
        self.assertEqual(self.rt.package(old['id'])['story']['title'], old['story']['title'])

    def test_cache_is_bounded_lru(self):
        revisions = []
        for index in range(4):
            package = self.rt.package()
            story, characters = copy.deepcopy(package['story']), copy.deepcopy(package['characters'])
            story['title'] = package['story']['title'] + str(index)
            revisions.append(self.rt.commit_package(story, characters, 'lru %d' % index))
        with patch.object(type(self.rt), 'PACKAGE_CACHE_LIMIT', 2):
            for revision in revisions:
                self.rt.package(revision)
            self.assertEqual(list(self.rt._package_cache), revisions[-2:])
            self.rt.package(revisions[-2])            # 触碰后它是最近使用的
            self.rt.package(revisions[0])             # 挤掉最久未用的 revisions[-1]
            self.assertEqual(list(self.rt._package_cache), [revisions[-2], revisions[0]])

    def test_missing_revision_raises_and_is_not_cached(self):
        with self.assertRaises(ValueError):
            self.rt.package('no-such-revision')
        self.assertNotIn('no-such-revision', self.rt._package_cache)


if __name__ == '__main__':
    unittest.main()
