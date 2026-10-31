# -*- coding: utf-8 -*-
"""特质分区并入统一百科库：显式名单、实测总量、标签/检索、固定版本、幂等、source pin、导出回环。

这些测试只构库到临时数据库；不会读写 `artifacts/human-encyclopedia/encyclopedia.sqlite3`，
交付库由验收方用 `--with-traits` 自行重建。
"""
import json
import tempfile
import unittest
from pathlib import Path

from app import encyclopedia as enc
from tools import encyclopedia_build as build

ROOT = Path(__file__).resolve().parents[1]
TRAIT_FILE = ROOT / 'docs/playable-demo/character-traits.json'
PACKAGE_FILE = ROOT / 'StoryPackage' / '河港汛期' / 'story.json'
NAMESPACE = 'character-traits'
TRAIT_RELATIVE = 'docs/playable-demo/character-traits.json'

# 本机实测（同一台机器、同一批源文件）：
#   历史 14 组 → 528 元素 / 502 来源 / 0 未解析
#   --with-traits（15 组）→ 551 元素 / 505 来源 / 0 未解析
# 这两个数字是「交付库应有的量」，一旦源文件变了就应该同步更新这份断言，而不是反过来改实现。
LEGACY_GROUPS = 14
LEGACY_ELEMENTS = 528
LEGACY_SOURCES = 502
DELIVERY_GROUPS = 15
DELIVERY_ELEMENTS = 551
DELIVERY_SOURCES = 505


class TraitLibraryCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = Path(cls.tmp.name) / 'with-traits.sqlite3'
        code = build.build(cls.db, as_json=True, groups=build.LATEST_GROUPS)
        if code != build.EXIT_OK:
            raise AssertionError('构库失败：%s' % code)
        cls.document = json.loads(TRAIT_FILE.read_text(encoding='utf-8-sig'))
        cls.totals = enc.stats(cls.db)['totals']

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    # ----------------------------------------------------------- 名单本身
    def test_manifest_is_explicit_and_opt_in(self):
        self.assertEqual(len(build.GROUPS), LEGACY_GROUPS)
        self.assertNotIn(TRAIT_RELATIVE, build.GROUPS, '特质不能默认进库')
        self.assertEqual(tuple(build.TRAIT_GROUPS), (TRAIT_RELATIVE,))
        self.assertEqual(build.LATEST_GROUPS, build.GROUPS + build.TRAIT_GROUPS)
        self.assertEqual(len(build.LATEST_GROUPS), DELIVERY_GROUPS)
        self.assertEqual(build.groups_for(False), build.GROUPS)
        self.assertEqual(build.groups_for(True), build.LATEST_GROUPS)
        # 名单是逐条写死的：每一项都能在仓库里找到，且没有通配
        for relative in build.LATEST_GROUPS:
            self.assertNotIn('*', relative)
            self.assertTrue((ROOT / relative).exists(), relative)
        self.assertEqual(len(set(build.LATEST_GROUPS)), len(build.LATEST_GROUPS))

    def test_delivery_totals_are_measured_values(self):
        self.assertEqual(self.totals['groups'], DELIVERY_GROUPS)
        self.assertEqual(self.totals['elements'], DELIVERY_ELEMENTS)
        self.assertEqual(self.totals['sources'], DELIVERY_SOURCES)
        self.assertEqual(self.totals['unresolved_relations'], 0)
        traits = enc.stats(self.db, namespace=NAMESPACE)['totals']
        self.assertEqual(traits['elements'], len(self.document['elements']))
        self.assertEqual(traits['sources'], len(self.document['sources']))

    def test_legacy_fourteen_group_set_is_unchanged(self):
        legacy_db = Path(self.tmp.name) / 'legacy.sqlite3'
        code = build.build(legacy_db, as_json=True)
        self.assertEqual(code, build.EXIT_OK)
        totals = enc.stats(legacy_db)['totals']
        self.assertEqual(totals['groups'], LEGACY_GROUPS)
        self.assertEqual(totals['elements'], LEGACY_ELEMENTS)
        self.assertEqual(totals['sources'], LEGACY_SOURCES)
        namespaces = [row['namespace'] for row in enc.stats(legacy_db)['groups']]
        self.assertNotIn(NAMESPACE, namespaces)

    # ------------------------------------------------------------- 标签/检索
    def test_trait_tags_are_queryable(self):
        tags = {row['tag'] for row in enc.list_tags(self.db, namespace=NAMESPACE)['tags']}
        self.assertIn('trait', tags)
        self.assertIn('trait.public', tags)
        self.assertIn('trait.hidden', tags)
        hidden = enc.search(self.db, namespace=NAMESPACE,
                           tags_all=['trait', 'trait.hidden'], limit=50)
        expected = sorted(element['id'] for element in self.document['elements']
                          if 'trait.hidden' in element.get('tags', []))
        self.assertEqual(sorted(row['element_id'] for row in hidden['items']), expected)
        public = enc.search(self.db, namespace=NAMESPACE, tags_all=['trait.public'], limit=50)
        self.assertEqual(public['total'], 21)

    def test_search_finds_a_trait_by_name_and_alias(self):
        sample = self.document['elements'][0]
        by_name = enc.search(self.db, text=sample['name'], namespace=NAMESPACE, limit=10)
        self.assertIn(sample['id'], [row['element_id'] for row in by_name['items']])
        alias = (sample.get('aliases') or [None])[0]
        if alias:
            by_alias = enc.search(self.db, text=alias, namespace=NAMESPACE, limit=10)
            self.assertIn(sample['id'], [row['element_id'] for row in by_alias['items']])

    # ------------------------------------------- 固定版本 / 幂等 / source pin
    def test_version_is_pinned_and_reimport_is_idempotent(self):
        sample = self.document['elements'][0]['id']
        rows = enc.versions(self.db, sample, namespace=NAMESPACE)
        self.assertEqual([row['version'] for row in rows['versions']], [1])
        self.assertTrue(rows['versions'][0]['is_current'])
        again = enc.import_file(self.db, TRAIT_FILE)
        self.assertTrue(again.as_dict()['idempotent'], '同一份源文件重跑必须零写入')
        self.assertEqual(again.as_dict()['element_versions_written'], 0)
        self.assertEqual([row['version'] for row in
                          enc.versions(self.db, sample, namespace=NAMESPACE)['versions']], [1])

    def test_sources_are_pinned_to_version_one(self):
        sample = self.document['elements'][0]['id']
        detail = enc.get(self.db, sample, namespace=NAMESPACE, version=1)
        self.assertTrue(detail['sources'])
        for source in detail['sources']:
            self.assertEqual(source['source_version'], 1)
        conn = enc.open_readonly(self.db)
        try:
            for source_id in self.document['elements'][0].get('source_ids') or []:
                self.assertTrue(enc.pin_exists(conn, NAMESPACE, source_id, 1), source_id)
        finally:
            conn.close()

    # -------------------------------------------------------------- 导出回环
    def test_export_round_trips_into_an_empty_database(self):
        document = enc.export_document(self.db, namespaces=[NAMESPACE])
        fresh = Path(self.tmp.name) / 'roundtrip.sqlite3'
        enc.restore_document(fresh, document)
        totals = enc.stats(fresh)['totals']
        self.assertEqual(totals['groups'], 1)
        self.assertEqual(totals['elements'], len(self.document['elements']))
        self.assertEqual(totals['sources'], len(self.document['sources']))

    def test_package_snapshot_matches_the_library_version(self):
        """包内快照 = 库里那个版本的**完整** payload（单一权威，不似而相同）。

        比整份 payload 与整份哈希（不是几个字段）；另验：源 JSON 的键一个不少，
        来源引用不丢、每个 source 在库里有 v1 pin。
        """
        source = {element['id']: element for element in self.document['elements']}
        story = json.loads(PACKAGE_FILE.read_text(encoding='utf-8'))
        templates = story['mechanics']['traits']['templates']
        self.assertEqual(len(templates), len(source))
        conn = enc.open_readonly(self.db)
        try:
            for template in templates:
                ident = template['element_id']
                detail = enc.get(self.db, ident, namespace=NAMESPACE,
                                 version=template['version'])
                # 1) 整份 payload 逐键相等（含 source_ids / related_ids）
                self.assertEqual(template['payload'], detail['payload'], ident)
                # 2) 整份哈希相等（与库同一函数口径）
                self.assertEqual(template['payload_hash'], enc.payload_hash(detail['payload']))
                # 3) 派生字段来自 payload，而不是第二份正文
                self.assertEqual(template['name'], detail['payload']['name'])
                self.assertEqual(template['details'], detail['payload']['details'])
                self.assertEqual(template['tags'], detail['payload']['tags'])
                # 4) 来源一模一样，且每个都在库里有 pin
                self.assertEqual(template['sources'],
                                 [{'source_id': row['source_id'],
                                   'source_version': row['source_version']}
                                  for row in detail['sources']], ident)
                for row in template['sources']:
                    self.assertTrue(enc.pin_exists(conn, NAMESPACE, row['source_id'],
                                                   row['source_version']))
                # 5) 不丢字段：源 JSON 的键一个不少（反“过滤后冒充同一版本”）
                self.assertEqual(set(template['payload']), set(source[ident]), ident)
                self.assertEqual(template['payload']['source_ids'],
                                 source[ident].get('source_ids'))
                self.assertEqual(template['payload']['related_ids'],
                                 source[ident].get('related_ids'))
        finally:
            conn.close()


if __name__ == '__main__':
    unittest.main()
