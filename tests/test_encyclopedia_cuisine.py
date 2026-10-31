# -*- coding: utf-8 -*-
"""饮食／烹饪分区并入统一百科库：显式名单、flag 组合、检索、幂等、来源引用。

这些测试只构库到临时目录；**不读写** `artifacts/human-encyclopedia/encyclopedia.sqlite3`
与 `data/`。交付库由验收方显式跑 `--with-cuisine`（可叠加 `--with-traits`）生成。

`cuisine.json` 还在增补中，条数会变：所以所有数量断言都从**源文件当前内容**算，
不写死 21 / 任何固定数字。
"""
import json
import tempfile
import unittest
from pathlib import Path

from app import encyclopedia as enc
from tools import encyclopedia_build as build

ROOT = Path(__file__).resolve().parents[1]
CUISINE_RELATIVE = 'docs/human-encyclopedia/cuisine.json'
CUISINE_FILE = ROOT / CUISINE_RELATIVE
NAMESPACE = 'cuisine'


def _document():
    return json.loads(CUISINE_FILE.read_text(encoding='utf-8-sig'))


class CuisineManifestCase(unittest.TestCase):
    """名单本身：显式、独立、不默认进库、不靠通配。"""

    def test_cuisine_manifest_is_explicit_and_separate(self):
        self.assertEqual(tuple(build.CUISINE_GROUPS), (CUISINE_RELATIVE,))
        self.assertNotIn(CUISINE_RELATIVE, build.GROUPS, '饮食分区不能默认进库')
        self.assertNotIn(CUISINE_RELATIVE, build.TRAIT_GROUPS, '两份名单不能互相混')
        for relative in build.CUISINE_GROUPS:
            self.assertNotIn('*', relative, '名单不能是通配')
            self.assertTrue((ROOT / relative).exists(), relative)

    def test_legacy_and_trait_behaviour_is_unchanged(self):
        """旧调用与旧口径不变：这是本次增补必须保住的兼容。"""
        self.assertEqual(build.groups_for(), build.GROUPS)
        self.assertEqual(build.groups_for(False), build.GROUPS)
        self.assertEqual(build.groups_for(True), build.LATEST_GROUPS)
        self.assertEqual(build.LATEST_GROUPS, build.GROUPS + build.TRAIT_GROUPS)
        self.assertNotIn(CUISINE_RELATIVE, build.groups_for(), '默认不能带饮食')
        self.assertNotIn(CUISINE_RELATIVE, build.groups_for(True), '只给 traits 时不能带饮食')

    def test_flags_combine_in_a_fixed_order(self):
        only_cuisine = build.groups_for(False, True)
        both = build.groups_for(True, True)
        self.assertEqual(only_cuisine, build.GROUPS + build.CUISINE_GROUPS)
        self.assertEqual(both, build.GROUPS + build.TRAIT_GROUPS + build.CUISINE_GROUPS)
        # 名单不重复，且每一项都真实存在
        for groups in (only_cuisine, both):
            self.assertEqual(len(set(groups)), len(groups))
            for relative in groups:
                self.assertTrue((ROOT / relative).exists(), relative)

    def test_parser_exposes_the_flag(self):
        parser = build.build_parser()
        args = parser.parse_args(['--with-cuisine'])
        self.assertTrue(args.with_cuisine)
        self.assertFalse(args.with_traits)
        both = parser.parse_args(['--with-traits', '--with-cuisine'])
        self.assertTrue(both.with_traits and both.with_cuisine)
        self.assertFalse(parser.parse_args([]).with_cuisine)


class CuisineLibraryCase(unittest.TestCase):
    """真构一份带饮食分区的临时库，验行为（数量从源文件动态算）。"""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.document = _document()
        cls.db = Path(cls.tmp.name) / 'with-cuisine.sqlite3'
        code = build.build(cls.db, as_json=True,
                           groups=build.groups_for(True, True))
        if code != build.EXIT_OK:
            raise AssertionError('构库失败：%s' % code)
        cls.totals = enc.stats(cls.db)['totals']

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    # ------------------------------------------------------------- 入库与数量
    def test_cuisine_group_landed_with_source_counts(self):
        group = enc.stats(self.db, namespace=NAMESPACE)['totals']
        self.assertEqual(group['elements'], len(self.document['elements']))
        self.assertEqual(group['sources'], len(self.document['sources']))
        namespaces = [row['namespace'] for row in enc.stats(self.db)['groups']]
        self.assertIn(NAMESPACE, namespaces)
        # 组数 = 14 + 特质 + 饮食（不写死总条数：源文件在增补）
        self.assertEqual(self.totals['groups'],
                         len(build.GROUPS) + len(build.TRAIT_GROUPS) + len(build.CUISINE_GROUPS))
        self.assertEqual(self.totals['unresolved_relations'], 0)

    def test_entries_stay_candidates_not_verified(self):
        rows = enc.search(self.db, namespace=NAMESPACE, limit=200)['items']
        self.assertTrue(rows, '饮食分区里应当有条目')
        for row in rows:
            detail = enc.get(self.db, row['element_id'], namespace=NAMESPACE, version=1)
            self.assertEqual(detail['payload']['review_status'], 'needs_review', row['element_id'])

    # --------------------------------------------------------------- 标签/检索
    def test_tags_come_from_the_source_document(self):
        expected = set()
        for element in self.document['elements']:
            expected.update(element.get('tags') or [])
        actual = {row['tag'] for row in enc.list_tags(self.db, namespace=NAMESPACE)['tags']}
        self.assertTrue(expected, 'cuisine.json 里的条目应当带标签')
        self.assertEqual(actual, expected)

    def test_search_by_name_and_alias(self):
        sample = self.document['elements'][0]
        by_name = enc.search(self.db, text=sample['name'], namespace=NAMESPACE, limit=10)
        self.assertIn(sample['id'], [row['element_id'] for row in by_name['items']])
        alias = (sample.get('aliases') or [None])[0]
        if alias and alias.strip():
            by_alias = enc.search(self.db, text=alias, namespace=NAMESPACE, limit=10)
            self.assertIn(sample['id'], [row['element_id'] for row in by_alias['items']])

    def test_search_finds_the_sushi_entry_when_present(self):
        """中文关键词能命中最典型的那一条（条目可能改名/增补，所以只在存在时断言）。"""
        hits = enc.search(self.db, text='寿司', namespace=NAMESPACE, limit=20)
        self.assertTrue(hits['items'], '寿司条目应能通过中文名称检索')
        matched = [row['element_id'] for row in hits['items']]
        expected = [element['id'] for element in self.document['elements']
                    if '寿司' in (element.get('name') or '')
                    or '寿司' in json.dumps(element, ensure_ascii=False)]
        for ident in matched:
            self.assertIn(ident, expected, '%s 不该因为「寿司」被命中' % ident)

    def test_tag_filter_returns_exactly_the_matching_elements(self):
        tag = (self.document['elements'][0].get('tags') or [None])[0]
        if not tag:
            self.skipTest('cuisine.json 第一条没有标签')
        expected = sorted(element['id'] for element in self.document['elements']
                          if tag in (element.get('tags') or []))
        found = enc.search(self.db, namespace=NAMESPACE, tags_all=[tag], limit=200)
        self.assertEqual(sorted(row['element_id'] for row in found['items']), expected)

    # ------------------------------------------------------ 幂等 / 来源引用不悬空
    def test_reimport_is_idempotent(self):
        sample = self.document['elements'][0]['id']
        before = [row['version'] for row in
                  enc.versions(self.db, sample, namespace=NAMESPACE)['versions']]
        again = enc.import_file(self.db, CUISINE_FILE)
        self.assertTrue(again.as_dict()['idempotent'], '同一份源文件重跑必须零写入')
        self.assertEqual(again.as_dict()['element_versions_written'], 0)
        after = [row['version'] for row in
                 enc.versions(self.db, sample, namespace=NAMESPACE)['versions']]
        self.assertEqual(before, after)

    def test_source_references_are_not_dangling(self):
        """每条 source_ids 都必须能在库里找到 v1 pin；related_ids 不能悬空成未解析。"""
        document = self.document
        known_sources = {source['id'] for source in document['sources']}
        conn = enc.open_readonly(self.db)
        try:
            for element in document['elements']:
                for source_id in element.get('source_ids') or []:
                    self.assertIn(source_id, known_sources,
                                  '%s 引用了源文件里不存在的来源' % element['id'])
                    self.assertTrue(enc.pin_exists(conn, NAMESPACE, source_id, 1),
                                    '%s → %s 没有 v1 pin' % (element['id'], source_id))
        finally:
            conn.close()
        self.assertEqual(enc.stats(self.db)['totals']['unresolved_relations'], 0,
                         'related_ids 不该留成未解析（同库内引用应全部 resolved）')

    def test_check_passes_on_the_built_library(self):
        code = build.check(self.db, as_json=True, groups=build.groups_for(True, True))
        self.assertEqual(code, build.EXIT_OK)

    def test_check_reports_a_missing_cuisine_group(self):
        """库里没有饮食分区时，`--check --with-cuisine` 必须报不一致（退 1），不静默放过。"""
        legacy_db = Path(self.tmp.name) / 'legacy-only.sqlite3'
        self.assertEqual(build.build(legacy_db, as_json=True), build.EXIT_OK)
        code = build.check(legacy_db, as_json=True, groups=build.groups_for(False, True))
        self.assertEqual(code, build.EXIT_ERROR)


if __name__ == '__main__':
    unittest.main()
