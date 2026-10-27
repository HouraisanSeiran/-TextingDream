# -*- coding: utf-8 -*-
"""人类生产生活百科库：独立 SQLite、版本/幂等、检索/分页、导出再导入、274 适配。

全部测试都跑在随机的临时目录里，不触碰 ``data/``、``StoryPackage/`` 与游戏
runtime；对 ``docs/`` 下的采集 JSON **只读**（测试还会断言原文件字节没变）。
"""
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import encyclopedia as enc  # noqa: E402
from tools import encyclopedia_cli as cli  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
HUMAN_DIR = ROOT / 'docs' / 'human-encyclopedia'
CATALOG_DIR = ROOT / 'docs' / 'element-catalog'

# 原六组：四个虚构题材组 + 现实两分区，合计 274 条（element-catalog/README.md 实测）。
CATALOG_GROUPS = ('eastern', 'western', 'society', 'steam-horror', 'reality-physical', 'reality-human')
CATALOG_TOTAL = 274

SECTIONS = (
    'definition', 'mechanism', 'conditions', 'exceptions',
    'story_uses', 'historical_scope', 'evidence_and_uncertainty',
)


# --------------------------------------------------------------------------- 夹具
def make_source(source_id, title='来源', access='read', extra=None):
    source = {
        'id': source_id,
        'title': title,
        'url': 'https://example.invalid/%s' % source_id,
        'access': access,
        'supports': '支撑范围',
        'rights_note': '仅转述',
    }
    if extra:
        source.update(extra)
    return source


def make_details(prefix='内容'):
    return {section: '%s-%s' % (prefix, section) for section in SECTIONS}


def make_element(element_id, name, *, aliases=None, tags=None, source_ids=None,
                 related_ids=None, details=None, review_status='needs_review',
                 extra=None):
    element = {
        'id': element_id,
        'name': name,
        'aliases': aliases or [],
        'tags': tags or ['food'],
        'summary': '%s 的摘要' % name,
        'details': details if details is not None else make_details(name),
        'source_ids': source_ids or [],
        'related_ids': related_ids or [],
        'review_status': review_status,
    }
    if extra:
        element.update(extra)
    return element


def make_document(group, elements, sources=None, **meta):
    document = {
        'schema_version': 1,
        'group': group,
        'status': 'candidate',
        'sources': sources if sources is not None else [],
        'elements': elements,
    }
    document.update(meta)
    return document


def legacy_element(element_id, name, *, category='life', genres=('xianxia',),
                   source_ids=None, related=None, detail_status='needs_detail'):
    """旧 element-catalog 形状：七节是 story_consequences / adaptation_limits 等。"""
    return {
        'id': element_id,
        'name': name,
        'genres': list(genres),
        'category': category,
        'summary': '%s 摘要' % name,
        'variants': ['变体一', '变体二'],
        'story_roles': ['角色一'],
        'requires': ['前提一'],
        'excludes': ['排除一'],
        'background': '背景说明',
        'entry_modes': ['existing'],
        'introduction_limits': '引入限制',
        'source_ids': source_ids or [],
        'evidence_note': '来源与设计归纳之分',
        'detail_status': detail_status,
        'details': {
            'definition': '定义',
            'mechanism': '机制',
            'conditions': '前提',
            'exceptions': '例外',
            'story_consequences': '剧情后果（原字段）',
            'adaptation_limits': '跨题材边界（原字段）',
            'evidence_and_uncertainty': '证据与不确定',
            'parameter_dimensions': {'scale': 'small', 'levels': ['a', 'b']},
        },
    }


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.db = self.dir / 'encyclopedia.sqlite3'

    def tearDown(self):
        self.tmp.cleanup()

    def import_doc(self, document, **kwargs):
        return enc.import_document(self.db, document, **kwargs)

    def counts(self, db=None):
        return enc.stats(db or self.db)['totals']

    def raw_counts(self):
        """绕过只读 API 直接数行，用来断言「半批零写入」。"""
        if not self.db.exists():
            return {key: 0 for key in ('elements', 'element_versions', 'sources', 'source_versions',
                                       'groups', 'batches', 'relations')}
        conn = sqlite3.connect(str(self.db))
        try:
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}

            def count(table):
                return conn.execute('SELECT COUNT(*) FROM %s' % table).fetchone()[0] if table in tables else 0

            return {
                'elements': count('elements'),
                'element_versions': count('element_versions'),
                'sources': count('sources'),
                'source_versions': count('source_versions'),
                'groups': count('groups'),
                'batches': count('import_batches'),
                'relations': count('element_relations'),
            }
        finally:
            conn.close()


# --------------------------------------------------------------------------- 导入与版本
class ImportAndVersionTests(Base):
    def test_first_import_creates_current_schema_and_one_version(self):
        doc = make_document('demo', [make_element('demo_a', '甲')], [make_source('demo_src_a')])
        result = self.import_doc(doc)
        self.assertFalse(result.idempotent)
        self.assertEqual(result.element_versions, 1)
        self.assertEqual(result.source_versions, 1)
        conn = sqlite3.connect(str(self.db))
        try:
            value = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(value, str(enc.SCHEMA_VERSION))
        self.assertEqual(enc.SCHEMA_VERSION, 2)
        item = enc.get(self.db, 'demo_a')
        self.assertEqual(item['version'], 1)
        self.assertEqual(item['current_version'], 1)
        self.assertTrue(item['is_current'])
        self.assertEqual(item['payload']['name'], '甲')

    def test_same_payload_is_idempotent_and_adds_no_version(self):
        doc = make_document('demo', [make_element('demo_a', '甲')], [make_source('demo_src_a')])
        self.import_doc(doc)
        before = self.raw_counts()
        again = self.import_doc(json.loads(json.dumps(doc)))
        after = self.raw_counts()
        self.assertTrue(again.idempotent)
        self.assertEqual(again.element_versions, 0)
        self.assertEqual(before, after)
        self.assertEqual(len(enc.versions(self.db, 'demo_a')['versions']), 1)

    def test_element_idempotent_even_when_batch_metadata_changes(self):
        """只改文档级字段（批次哈希变）时，元素内容同哈希 → 不新增版本。"""
        element = make_element('demo_a', '甲')
        self.import_doc(make_document('demo', [element], [make_source('demo_src_a')]))
        self.import_doc(make_document('demo', [element], [make_source('demo_src_a')], updated='2026-10-26'))
        rows = enc.versions(self.db, 'demo_a')['versions']
        self.assertEqual(len(rows), 1)

    def test_changed_content_creates_new_version_and_keeps_old_readable(self):
        first = make_element('demo_a', '甲')
        self.import_doc(make_document('demo', [first], [make_source('demo_src_a')]))
        second = json.loads(json.dumps(first))
        second['summary'] = '改过的摘要'
        result = self.import_doc(make_document('demo', [second], [make_source('demo_src_a')]))
        self.assertEqual(result.element_versions, 1)
        self.assertEqual(result.unchanged_elements, 0)
        head = enc.get(self.db, 'demo_a')
        self.assertEqual(head['version'], 2)
        self.assertEqual(head['summary'], '改过的摘要')
        old = enc.get(self.db, 'demo_a', version=1)
        self.assertEqual(old['summary'], '甲 的摘要')
        self.assertFalse(old['is_current'])
        self.assertEqual([row['version'] for row in enc.versions(self.db, 'demo_a')['versions']], [1, 2])
        # 旧版本内容不可被覆盖：版本 1 的哈希与 payload 保持原样。
        self.assertEqual(old['payload']['summary'], '甲 的摘要')

    def test_missing_version_is_not_found(self):
        self.import_doc(make_document('demo', [make_element('demo_a', '甲')], [make_source('demo_src_a')]))
        with self.assertRaises(enc.NotFound):
            enc.get(self.db, 'demo_a', version=9)

    def test_unknown_element_is_not_found(self):
        self.import_doc(make_document('demo', [make_element('demo_a', '甲')], [make_source('demo_src_a')]))
        with self.assertRaises(enc.NotFound):
            enc.get(self.db, 'demo_missing')

    def test_tags_and_aliases_are_deduplicated(self):
        element = make_element('demo_a', '甲', aliases=['甲甲', '甲甲', 'jia'], tags=['crop', 'crop', 'food'])
        self.import_doc(make_document('demo', [element], [make_source('demo_src_a')]))
        item = enc.get(self.db, 'demo_a')
        self.assertEqual(item['tags'], ['crop', 'food'])
        self.assertEqual(item['aliases'], ['甲甲', 'jia'])
        self.assertEqual(len(enc.get(self.db, 'demo_a')['tags']), len(set(item['tags'])))

    def test_cross_namespace_source_is_resolved_as_external(self):
        self.import_doc(make_document('alpha', [make_element('alpha_a', '甲')], [make_source('alpha_src')]))
        self.import_doc(make_document('beta', [make_element('beta_b', '乙', source_ids=['alpha_src'])], []))
        item = enc.get(self.db, 'beta_b')
        self.assertEqual(item['sources'][0]['source_namespace'], 'alpha')
        self.assertEqual(item['sources'][0]['status'], 'resolved_external')


# --------------------------------------------------------------------------- 标签与检索
class SearchTests(Base):
    def setUp(self):
        super().setUp()
        elements = [
            make_element('demo_wheat', '小麦', aliases=['wheat', 'Triticum aestivum'],
                         tags=['crop', 'cereal', 'food', 'agriculture']),
            make_element('demo_barley', '大麦', aliases=['barley'], tags=['crop', 'cereal', 'food']),
            make_element('demo_plough', '犁', aliases=['plough', 'ard'], tags=['tool', 'agriculture']),
            make_element('demo_iron', '铁', aliases=['iron'], tags=['metal', 'processed_material']),
        ]
        self.import_doc(make_document('demo', elements, [make_source('demo_src_a')]))

    def ids(self, page):
        return [item['element_id'] for item in page['items']]

    def test_chinese_name_search(self):
        page = enc.search(self.db, text='小麦')
        self.assertEqual(page['total'], 1)
        self.assertEqual(self.ids(page), ['demo_wheat'])

    def test_chinese_alias_search(self):
        page = enc.search(self.db, text='大麦')
        self.assertEqual(self.ids(page), ['demo_barley'])
        # 别名（拉丁名）也能命中，且大小写不敏感。
        page = enc.search(self.db, text='triticum')
        self.assertEqual(self.ids(page), ['demo_wheat'])

    def test_substring_search_does_not_leak_all_rows(self):
        page = enc.search(self.db, text='不存在的名字')
        self.assertEqual(page['total'], 0)
        self.assertEqual(page['items'], [])

    def test_tags_or_filter(self):
        page = enc.search(self.db, tags_any=['cereal', 'tool'])
        self.assertEqual(sorted(self.ids(page)), ['demo_barley', 'demo_plough', 'demo_wheat'])

    def test_tags_and_filter(self):
        page = enc.search(self.db, tags_all=['crop', 'cereal'])
        self.assertEqual(sorted(self.ids(page)), ['demo_barley', 'demo_wheat'])
        page = enc.search(self.db, tags_all=['crop', 'cereal', 'tool'])
        self.assertEqual(page['total'], 0)

    def test_tags_and_or_combined_with_text(self):
        page = enc.search(self.db, text='麦', tags_any=['cereal'], tags_all=['crop'])
        self.assertEqual(sorted(self.ids(page)), ['demo_barley', 'demo_wheat'])

    def test_unknown_tag_returns_empty_not_error(self):
        page = enc.search(self.db, tags_all=['no_such_tag'])
        self.assertEqual(page['total'], 0)

    def test_pagination_boundaries(self):
        page = enc.search(self.db, tags_all=['crop'], limit=1, offset=0)
        self.assertEqual((page['total'], page['returned'], page['has_more']), (2, 1, True))
        second = enc.search(self.db, tags_all=['crop'], limit=1, offset=1)
        self.assertEqual((second['returned'], second['has_more']), (1, False))
        self.assertNotEqual(self.ids(page), self.ids(second))
        beyond = enc.search(self.db, tags_all=['crop'], limit=1, offset=99)
        self.assertEqual((beyond['total'], beyond['returned'], beyond['has_more']), (2, 0, False))

    def test_pagination_limits_are_enforced(self):
        with self.assertRaises(enc.EncyclopediaError):
            enc.search(self.db, limit=0)
        with self.assertRaises(enc.EncyclopediaError):
            enc.search(self.db, limit=enc.MAX_PAGE_SIZE + 1)
        with self.assertRaises(enc.EncyclopediaError):
            enc.search(self.db, offset=-1)
        ok = enc.search(self.db, limit=enc.MAX_PAGE_SIZE)
        self.assertEqual(ok['limit'], enc.MAX_PAGE_SIZE)

    def test_namespace_scoped_search_and_ambiguous_get(self):
        self.import_doc(make_document('other', [make_element('demo_wheat', '小麦二')],
                                      [make_source('other_src')]))
        self.assertEqual(enc.search(self.db, text='小麦', namespace='other')['total'], 1)
        with self.assertRaises(enc.Ambiguous):
            enc.get(self.db, 'demo_wheat')
        self.assertEqual(enc.get(self.db, 'demo_wheat', namespace='other')['name'], '小麦二')

    def test_tags_listing(self):
        data = enc.list_tags(self.db)
        tags = {row['tag']: row['count'] for row in data['tags']}
        self.assertEqual(tags['crop'], 2)
        self.assertEqual(tags['cereal'], 2)
        self.assertEqual(data['total'], 7)


# --------------------------------------------------------------------------- 命名空间 / 冲突
class NamespaceTests(Base):
    def test_same_element_id_in_two_namespaces_does_not_overwrite(self):
        self.import_doc(make_document('alpha', [make_element('same_id', '甲版')], [make_source('alpha_src')]))
        self.import_doc(make_document('beta', [make_element('same_id', '乙版')], [make_source('beta_src')]))
        self.assertEqual(enc.get(self.db, 'same_id', namespace='alpha')['name'], '甲版')
        self.assertEqual(enc.get(self.db, 'same_id', namespace='beta')['name'], '乙版')
        self.assertEqual(self.counts()['elements'], 2)

    def test_same_source_id_in_two_namespaces_stays_separate(self):
        self.import_doc(make_document('alpha', [make_element('alpha_a', '甲', source_ids=['shared_src'])],
                                      [make_source('shared_src', title='甲的来源')]))
        self.import_doc(make_document('beta', [make_element('beta_b', '乙', source_ids=['shared_src'])],
                                      [make_source('shared_src', title='乙的来源')]))
        alpha = enc.get(self.db, 'alpha_a')['sources'][0]
        beta = enc.get(self.db, 'beta_b')['sources'][0]
        self.assertEqual(alpha['title'], '甲的来源')
        self.assertEqual(beta['title'], '乙的来源')
        self.assertEqual(alpha['status'], 'batch')
        self.assertEqual(alpha['source_namespace'], 'alpha')

    def test_namespace_cannot_be_rebound_to_another_adapter_or_group(self):
        self.import_doc(make_document('demo', [make_element('demo_a', '甲')], [make_source('demo_src_a')]))
        legacy = make_document('demo', [legacy_element('demo_b', '乙')])
        with self.assertRaises(enc.Conflict):
            self.import_doc(legacy, adapter=enc.ADAPTER_CATALOG)

    def test_import_result_reports_shared_ids(self):
        self.import_doc(make_document('alpha', [make_element('same_id', '甲版')], [make_source('alpha_src')]))
        result = self.import_doc(make_document('beta', [make_element('same_id', '乙版')], [make_source('beta_src')]))
        self.assertEqual(result.shared_element_ids, [{'element_id': 'same_id', 'other_namespaces': ['alpha']}])


# --------------------------------------------------------------------------- 拒绝：半批零写入
class RejectTests(Base):
    def assert_nothing_written(self):
        self.assertEqual(self.raw_counts(), {
            'elements': 0, 'element_versions': 0, 'sources': 0, 'source_versions': 0,
            'groups': 0, 'batches': 0, 'relations': 0,
        })

    def test_dangling_source_rejects_whole_batch(self):
        doc = make_document('demo', [
            make_element('demo_a', '甲', source_ids=['demo_src_a']),
            make_element('demo_b', '乙', source_ids=['demo_src_missing']),
        ], [make_source('demo_src_a')])
        with self.assertRaises(enc.InvalidDocument):
            self.import_doc(doc)
        self.assert_nothing_written()

    def test_duplicate_element_id_in_one_document_rejects(self):
        doc = make_document('demo', [make_element('demo_a', '甲'), make_element('demo_a', '甲二')],
                            [make_source('demo_src_a')])
        with self.assertRaises(enc.InvalidDocument):
            self.import_doc(doc)
        self.assert_nothing_written()

    def test_duplicate_source_id_in_one_document_rejects(self):
        doc = make_document('demo', [make_element('demo_a', '甲', source_ids=['demo_src_a'])],
                            [make_source('demo_src_a'), make_source('demo_src_a', title='另一个')])
        with self.assertRaises(enc.InvalidDocument):
            self.import_doc(doc)
        self.assert_nothing_written()

    def test_missing_detail_section_rejects(self):
        element = make_element('demo_a', '甲')
        del element['details']['exceptions']
        with self.assertRaises(enc.InvalidDocument):
            self.import_doc(make_document('demo', [element], [make_source('demo_src_a')]))
        self.assert_nothing_written()

    def test_empty_detail_section_rejects(self):
        element = make_element('demo_a', '甲')
        element['details']['mechanism'] = '   '
        with self.assertRaises(enc.InvalidDocument):
            self.import_doc(make_document('demo', [element], [make_source('demo_src_a')]))
        self.assert_nothing_written()

    def test_bad_tag_and_bad_id_reject(self):
        with self.assertRaises(enc.InvalidDocument):
            self.import_doc(make_document('demo', [make_element('demo_a', '甲', tags=['Not lower case'])],
                                          [make_source('demo_src_a')]))
        with self.assertRaises(enc.InvalidDocument):
            self.import_doc(make_document('demo', [make_element('Demo A', '甲')], [make_source('demo_src_a')]))
        self.assert_nothing_written()

    def test_nan_is_rejected_on_parse_and_on_document(self):
        with self.assertRaises(enc.InvalidDocument):
            enc.loads_json('{"elements": [], "x": NaN}')
        with self.assertRaises(enc.InvalidDocument):
            enc.loads_json('{"x": Infinity}')
        document = make_document('demo', [make_element('demo_a', '甲', extra={'weird': float('nan')})],
                                 [make_source('demo_src_a')])
        with self.assertRaises(enc.InvalidDocument):
            self.import_doc(document)
        self.assert_nothing_written()

    def test_size_limits_are_enforced(self):
        element = make_element('demo_a', '甲')
        element['summary'] = '长' * (enc.MAX_TEXT_CHARS + 1)
        with self.assertRaises(enc.LimitExceeded):
            self.import_doc(make_document('demo', [element], [make_source('demo_src_a')]))
        many_tags = make_element('demo_b', '乙', tags=['tag_%03d' % index for index in range(enc.MAX_TAGS + 1)])
        with self.assertRaises(enc.LimitExceeded):
            self.import_doc(make_document('demo', [many_tags], [make_source('demo_src_a')]))
        self.assert_nothing_written()

    def test_shared_themes_and_spec_like_documents_are_refused(self):
        with self.assertRaises(enc.InvalidDocument):
            self.import_doc({'schema_version': 1, 'themes': [], 'purpose': '聚类索引'})
        with self.assertRaises(enc.InvalidDocument):
            self.import_doc({'schema_version': 1, 'group': 'x', 'elements': [], 'sources': []})
        self.assert_nothing_written()

    def test_unrecognised_element_shape_is_refused(self):
        with self.assertRaises(enc.InvalidDocument):
            self.import_doc({'schema_version': 1, 'group': 'x', 'sources': [],
                             'elements': [{'id': 'x_a', 'name': '甲'}]})
        self.assert_nothing_written()

    def test_explicit_version_collision_is_refused(self):
        """导出后擅自改 payload，再把同一版本号写回已有库 → 必须拒绝（旧版本不可被覆盖）。"""
        self.import_doc(make_document('demo', [make_element('demo_a', '甲')], [make_source('demo_src_a')]))
        exported = enc.export_document(self.db)
        exported['elements'][0]['payload']['summary'] = '篡改'
        exported['elements'][0].pop('content_hash')  # 绕过哈希校验，直接測版本号冲突
        with self.assertRaises(enc.Conflict):
            enc.restore_document(self.db, exported)
        self.assertEqual(enc.get(self.db, 'demo_a', version=1)['payload']['summary'], '甲 的摘要')

    def test_export_hash_mismatch_is_refused(self):
        self.import_doc(make_document('demo', [make_element('demo_a', '甲')], [make_source('demo_src_a')]))
        exported = enc.export_document(self.db)
        exported['elements'][0]['payload']['summary'] = '偷偷改一行'
        with self.assertRaises(enc.Conflict):
            enc.restore_document(self.dir / 'copy.sqlite3', exported)


# --------------------------------------------------------------------------- 关联
class RelationTests(Base):
    def test_unresolved_relation_is_pending_then_resolves(self):
        first = make_document('alpha', [make_element('alpha_a', '甲', related_ids=['beta_b'])],
                              [make_source('alpha_src')])
        result = self.import_doc(first)
        self.assertEqual(result.unresolved_relations,
                         [{'element_id': 'alpha_a', 'rel_kind': 'related', 'target_id': 'beta_b'}])
        relation = enc.get(self.db, 'alpha_a')['relations'][0]
        self.assertEqual(relation['status'], 'pending')
        self.assertIsNone(relation['target_namespace'])
        self.assertEqual(self.counts()['unresolved_relations'], 1)

        self.import_doc(make_document('beta', [make_element('beta_b', '乙')], [make_source('beta_src')]))
        relation = enc.get(self.db, 'alpha_a')['relations'][0]
        self.assertEqual(relation['status'], 'resolved')
        self.assertEqual(relation['target_namespace'], 'beta')
        self.assertEqual(self.counts()['unresolved_relations'], 0)

    def test_relation_target_in_same_namespace_is_resolved(self):
        doc = make_document('demo', [
            make_element('demo_a', '甲', related_ids=['demo_b']),
            make_element('demo_b', '乙'),
        ], [make_source('demo_src_a')])
        self.import_doc(doc)
        relation = enc.get(self.db, 'demo_a')['relations'][0]
        self.assertEqual((relation['status'], relation['target_namespace']), ('resolved', 'demo'))

    def test_relation_ambiguous_across_namespaces_is_flagged(self):
        self.import_doc(make_document('alpha', [make_element('same_id', '甲')], [make_source('alpha_src')]))
        self.import_doc(make_document('beta', [make_element('same_id', '乙')], [make_source('beta_src')]))
        result = self.import_doc(make_document('gamma', [make_element('gamma_a', '丙', related_ids=['same_id'])],
                                               [make_source('gamma_src')]))
        self.assertEqual(result.ambiguous_relations,
                         [{'element_id': 'gamma_a', 'rel_kind': 'related', 'target_id': 'same_id'}])
        self.assertEqual(enc.get(self.db, 'gamma_a')['relations'][0]['status'], 'ambiguous')

    def test_pending_relation_survives_export_and_restore(self):
        self.import_doc(make_document('alpha', [make_element('alpha_a', '甲', related_ids=['beta_b'])],
                                      [make_source('alpha_src')]))
        document = enc.export_document(self.db)
        self.assertEqual(document['elements'][0]['relations'][0]['status'], 'pending')
        other = self.dir / 'copy.sqlite3'
        enc.restore_document(other, document)
        restored = enc.get(other, 'alpha_a')
        self.assertEqual(restored['relations'][0]['status'], 'pending')
        self.assertEqual(restored['payload']['related_ids'], ['beta_b'])


# --------------------------------------------------------------------------- 证据版本固定（schema 2）
class SourcePinTests(Base):
    """元素版本必须固定「写入当时」的来源版本；来源更新不得改写旧证据。"""

    def source_v1(self, url='https://example.invalid/a', access='read', title='来源甲 v1'):
        return make_source('demo_src', title=title, access=access, extra={'url': url})

    def source_v2(self, url='https://example.invalid/a-v2', access='search_only', title='来源甲 v2'):
        return make_source('demo_src', title=title, access=access, extra={'url': url})

    def import_element(self, element, source, **meta):
        return self.import_doc(make_document('demo', [element], [source], **meta))

    def test_element_v1_keeps_source_v1_after_source_updates(self):
        element = make_element('demo_a', '甲', source_ids=['demo_src'])
        self.import_element(element, self.source_v1())
        first = enc.get(self.db, 'demo_a', version=1)
        self.assertEqual(first['sources'][0]['source_version'], 1)
        self.assertEqual(first['sources'][0]['url'], 'https://example.invalid/a')
        self.assertEqual(first['sources'][0]['access'], 'read')
        self.assertEqual(first['sources'][0]['title'], '来源甲 v1')
        self.assertTrue(first['sources'][0]['is_current_source_version'])

        # 只改来源（元素 payload 不变）→ 来源升到 v2。
        result = self.import_element(element, self.source_v2(), updated='2026-10-27')
        self.assertEqual(result.source_versions, 1)
        self.assertEqual(result.element_versions, 0)  # 元素内容没变，不新增元素版本
        self.assertEqual(result.unchanged_elements, 1)

        # 元素 v1 的证据仍固定 v1，**不得**静默换成 v2。
        again = enc.get(self.db, 'demo_a', version=1)
        self.assertEqual(again['sources'][0]['source_version'], 1)
        self.assertEqual(again['sources'][0]['url'], 'https://example.invalid/a')
        self.assertEqual(again['sources'][0]['access'], 'read')
        self.assertEqual(again['sources'][0]['title'], '来源甲 v1')
        self.assertFalse(again['sources'][0]['is_current_source_version'])
        self.assertEqual(again['sources'][0]['payload']['url'], 'https://example.invalid/a')
        self.assertEqual(again['version'], 1)  # 元素本身也没变

        # 来源当前版本确实是 v2（更新的确有发生，只是不污染历史）。
        conn = sqlite3.connect(str(self.db))
        try:
            current = conn.execute(
                'SELECT current_version, title FROM sources WHERE namespace=? AND source_id=?',
                ('demo', 'demo_src')).fetchone()
        finally:
            conn.close()
        self.assertEqual(current, (2, '来源甲 v2'))

    def test_new_element_version_can_pin_newer_source(self):
        element = make_element('demo_a', '甲', source_ids=['demo_src'])
        self.import_element(element, self.source_v1())
        self.import_element(element, self.source_v2(), updated='x')
        changed = dict(element, summary='改了内容，因而需要新版本与新证据')
        result = self.import_element(changed, self.source_v2(), updated='y')
        self.assertEqual(result.element_versions, 1)
        v2 = enc.get(self.db, 'demo_a', version=2)
        self.assertEqual(v2['sources'][0]['source_version'], 2)
        self.assertEqual(v2['sources'][0]['url'], 'https://example.invalid/a-v2')
        v1 = enc.get(self.db, 'demo_a', version=1)
        self.assertEqual(v1['sources'][0]['source_version'], 1)
        # 两个版本共存，各自的证据不交叉。
        self.assertNotEqual(v1['sources'][0]['payload'], v2['sources'][0]['payload'])

    def test_pin_survives_export_and_restore(self):
        element = make_element('demo_a', '甲', source_ids=['demo_src'])
        self.import_element(element, self.source_v1())
        self.import_element(element, self.source_v2(), updated='x')
        exported = enc.export_document(self.db)
        pinned = exported['elements'][0]['source_refs'][0]
        self.assertEqual(pinned['source_version'], 1)
        self.assertEqual(exported['export_version'], enc.EXPORT_VERSION)

        other = self.dir / 'pinned-copy.sqlite3'
        enc.restore_document(other, exported)
        restored = enc.get(other, 'demo_a', version=1)
        self.assertEqual(restored['sources'][0]['source_version'], 1)
        self.assertEqual(restored['sources'][0]['url'], 'https://example.invalid/a')
        self.assertEqual(restored['sources'][0]['title'], '来源甲 v1')
        # 还原后 current 仍是 v2，pin 仍是 v1。
        self.assertFalse(restored['sources'][0]['is_current_source_version'])
        self.assertEqual(enc.export_document(other)['elements'], exported['elements'])

    def test_pin_does_not_mix_across_namespaces_with_same_source_id(self):
        self.import_doc(make_document('alpha', [make_element('alpha_a', '甲', source_ids=['shared_src'])],
                                      [make_source('shared_src', title='甲的来源')]))
        self.import_doc(make_document('beta', [make_element('beta_b', '乙', source_ids=['shared_src'])],
                                      [make_source('shared_src', title='乙的来源')]))
        # beta 的来源再升一版。
        self.import_doc(make_document('beta', [make_element('beta_b', '乙', source_ids=['shared_src'])],
                                      [make_source('shared_src', title='乙的来源 v2')], updated='x'))
        alpha = enc.get(self.db, 'alpha_a')['sources'][0]
        beta = enc.get(self.db, 'beta_b')['sources'][0]
        self.assertEqual((alpha['source_namespace'], alpha['source_version']), ('alpha', 1))
        self.assertEqual((beta['source_namespace'], beta['source_version']), ('beta', 1))
        self.assertEqual(alpha['title'], '甲的来源')
        self.assertEqual(beta['title'], '乙的来源')

    def test_missing_pin_is_rejected_without_partial_write(self):
        element = make_element('demo_a', '甲', source_ids=['demo_src'])
        self.import_element(element, self.source_v1())
        exported = enc.export_document(self.db)
        # 把 pin 指到一个不存在的来源版本。
        exported['elements'][0]['source_refs'][0]['source_version'] = 99
        with self.assertRaises(enc.InvalidDocument):
            enc.restore_document(self.dir / 'bad-pin.sqlite3', exported)
        bad = self.dir / 'bad-pin.sqlite3'
        conn = sqlite3.connect(str(bad))
        try:
            counts = {table: conn.execute('SELECT COUNT(*) FROM %s' % table).fetchone()[0]
                      for table in ('elements', 'element_versions', 'sources', 'element_sources')}
        finally:
            conn.close()
        self.assertEqual(counts, {'elements': 0, 'element_versions': 0, 'sources': 0, 'element_sources': 0})

    def test_pin_pointing_outside_export_document_is_rejected(self):
        element = make_element('demo_a', '甲', source_ids=['demo_src'])
        self.import_element(element, self.source_v1())
        exported = enc.export_document(self.db)
        # 声称引用的来源根本不在导出文件的 sources 里。
        exported['elements'][0]['source_refs'][0].update(
            {'source_namespace': 'ghost', 'source_id': 'ghost_src', 'source_version': 1})
        with self.assertRaises(enc.InvalidDocument):
            enc.restore_document(self.dir / 'ghost.sqlite3', exported)
        self.assertFalse((self.dir / 'ghost.sqlite3').exists()
                         and enc.stats(self.dir / 'ghost.sqlite3')['totals']['elements'])

    def test_export_without_pins_is_rejected(self):
        element = make_element('demo_a', '甲', source_ids=['demo_src'])
        self.import_element(element, self.source_v1())
        exported = enc.export_document(self.db)
        exported['elements'][0].pop('source_refs')
        with self.assertRaises(enc.InvalidDocument):
            enc.restore_document(self.dir / 'nopin.sqlite3', exported)

    def test_export_version_one_document_is_refused(self):
        element = make_element('demo_a', '甲', source_ids=['demo_src'])
        self.import_element(element, self.source_v1())
        exported = enc.export_document(self.db)
        exported['export_version'] = 1
        with self.assertRaises(enc.InvalidDocument):
            enc.restore_document(self.dir / 'v1.sqlite3', exported)

    def test_schema_one_database_is_refused_not_silently_upgraded(self):
        element = make_element('demo_a', '甲', source_ids=['demo_src'])
        self.import_element(element, self.source_v1())
        conn = sqlite3.connect(str(self.db))
        try:
            conn.execute("UPDATE meta SET value='1' WHERE key='schema_version'")
            conn.commit()
        finally:
            conn.close()
        with self.assertRaises(enc.Conflict) as caught:
            enc.stats(self.db)
        self.assertIn('不支持就地升级', str(caught.exception))

    def test_every_stored_element_source_has_a_valid_pin(self):
        """全库不变量：每条 element_sources 行都能 join 到真实来源版本。"""
        self.import_element(make_element('demo_a', '甲', source_ids=['demo_src']), self.source_v1())
        self.import_element(make_element('demo_a', '甲', source_ids=['demo_src']), self.source_v2(), updated='x')
        conn = sqlite3.connect(str(self.db))
        try:
            orphans = conn.execute(
                'SELECT COUNT(*) FROM element_sources es LEFT JOIN source_versions sv'
                '  ON sv.namespace=es.source_namespace AND sv.source_id=es.source_id'
                ' AND sv.version=es.source_version WHERE sv.version IS NULL').fetchone()[0]
            nulls = conn.execute(
                'SELECT COUNT(*) FROM element_sources WHERE source_version IS NULL').fetchone()[0]
        finally:
            conn.close()
        self.assertEqual((orphans, nulls), (0, 0))


# --------------------------------------------------------------------------- 导出 / 再导入
class ExportRestoreTests(Base):
    def build(self):
        self.import_doc(make_document('alpha', [
            make_element('alpha_a', '甲', related_ids=['beta_b']),
        ], [make_source('alpha_src')]))
        self.import_doc(make_document('beta', [
            make_element('beta_b', '乙'),
            make_element('beta_c', '丙'),
        ], [make_source('beta_src')]))
        element = make_element('beta_b', '乙改')
        self.import_doc(make_document('beta', [element], [make_source('beta_src')]))

    def test_round_trip_preserves_every_version_and_payload(self):
        self.build()
        exported = enc.export_document(self.db)
        self.assertEqual(exported['format'], enc.EXPORT_FORMAT)
        self.assertEqual(exported['export_version'], enc.EXPORT_VERSION)
        self.assertEqual(exported['schema_version'], enc.SCHEMA_VERSION)
        self.assertEqual(enc.EXPORT_VERSION, 2)
        self.assertEqual(exported['counts'], {'groups': 2, 'source_versions': 2, 'element_versions': 4})

        other = self.dir / 'restored.sqlite3'
        result = enc.restore_document(other, exported)
        self.assertEqual(result.element_versions, 4)
        self.assertEqual(result.source_versions, 2)

        again = enc.export_document(other)
        self.assertEqual(again['groups'], exported['groups'])
        self.assertEqual(again['sources'], exported['sources'])
        self.assertEqual(again['elements'], exported['elements'])
        self.assertEqual(again['counts'], exported['counts'])

    def test_restore_into_non_empty_database_is_idempotent(self):
        self.build()
        exported = enc.export_document(self.db)
        enc.restore_document(self.db, exported)
        self.assertEqual(self.counts()['element_versions'], 4)
        second = enc.restore_document(self.db, exported)
        self.assertTrue(second.idempotent)
        self.assertEqual(self.counts()['element_versions'], 4)

    def test_export_can_be_scoped_to_one_namespace(self):
        self.build()
        exported = enc.export_document(self.db, namespaces=['beta'])
        self.assertEqual([group['namespace'] for group in exported['groups']], ['beta'])
        self.assertTrue(all(item['namespace'] == 'beta' for item in exported['elements']))
        # 单个命名空间导出时，跨命名空间的关联在还原后应保持 pending，不假称解析。
        other = self.dir / 'only-beta.sqlite3'
        enc.restore_document(other, exported)
        self.assertEqual(self.counts(other)['unresolved_relations'], 0)

    def test_restore_is_atomic_across_namespaces(self):
        """多命名空间导出里某一组非法时，其他组也不得写进库（全有或全无）。"""
        self.build()
        exported = enc.export_document(self.db)
        for item in exported['elements']:
            if item['namespace'] == 'beta':
                item['payload']['source_ids'] = ['ghost_source']
                item['payload']['summary'] = '故意制造非法引用'
                item.pop('content_hash')
                break
        other = self.dir / 'atomic.sqlite3'
        with self.assertRaises(enc.InvalidDocument):
            enc.restore_document(other, exported)
        conn = sqlite3.connect(str(other))
        try:
            rows = {table: conn.execute('SELECT COUNT(*) FROM %s' % table).fetchone()[0]
                    for table in ('elements', 'element_versions', 'sources', 'import_batches')}
        finally:
            conn.close()
        self.assertEqual(rows, {'elements': 0, 'element_versions': 0, 'sources': 0, 'import_batches': 0})

    def test_export_refuses_non_export_document(self):
        with self.assertRaises(enc.InvalidDocument):
            enc.restore_document(self.dir / 'x.sqlite3', {'elements': []})


# --------------------------------------------------------------------------- 只读边界
class ReadOnlyTests(Base):
    def test_missing_database_is_not_created_by_queries(self):
        missing = self.dir / 'nope.sqlite3'
        for call in (
            lambda: enc.search(missing),
            lambda: enc.get(missing, 'x'),
            lambda: enc.stats(missing),
            lambda: enc.export_document(missing),
            lambda: enc.list_tags(missing),
        ):
            with self.assertRaises(enc.NotFound):
                call()
        self.assertFalse(missing.exists())

    def test_query_on_foreign_database_is_refused(self):
        foreign = self.dir / 'foreign.sqlite3'
        conn = sqlite3.connect(str(foreign))
        conn.execute('CREATE TABLE unrelated (id INTEGER)')
        conn.commit()
        conn.close()
        with self.assertRaises(enc.Conflict):
            enc.stats(foreign)

    def test_search_does_not_write(self):
        self.import_doc(make_document('demo', [make_element('demo_a', '甲')], [make_source('demo_src_a')]))
        before = hashlib.sha256(self.db.read_bytes()).hexdigest()
        enc.search(self.db, text='甲')
        enc.get(self.db, 'demo_a')
        enc.stats(self.db)
        enc.export_document(self.db)
        after = hashlib.sha256(self.db.read_bytes()).hexdigest()
        self.assertEqual(before, after)

    def test_schema_version_mismatch_is_refused(self):
        self.import_doc(make_document('demo', [make_element('demo_a', '甲')], [make_source('demo_src_a')]))
        conn = sqlite3.connect(str(self.db))
        conn.execute("UPDATE meta SET value='99' WHERE key='schema_version'")
        conn.commit()
        conn.close()
        with self.assertRaises(enc.Conflict):
            enc.stats(self.db)
        with self.assertRaises(enc.Conflict):
            enc.import_document(self.db, make_document('demo', [make_element('demo_b', '乙')],
                                                       [make_source('demo_src_a')]))


# --------------------------------------------------------------------------- 原六组 274 适配
class LegacyCatalogAdapterTests(Base):
    """原 element-catalog 六组 274 条：字段保留、七节适配、状态不升格、原文件不改。"""

    @classmethod
    def setUpClass(cls):
        cls.files = [CATALOG_DIR / ('%s.json' % name) for name in CATALOG_GROUPS]
        for path in cls.files:
            if not path.exists():
                raise unittest.SkipTest('缺少 %s' % path)
        cls.before = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in cls.files}
        cls.documents = {path.stem: json.loads(path.read_text(encoding='utf-8')) for path in cls.files}

    def test_all_six_groups_import_with_274_elements(self):
        total = 0
        for name in CATALOG_GROUPS:
            result = self.import_doc(self.documents[name])
            total += result.element_versions
            self.assertEqual(result.adapter, enc.ADAPTER_CATALOG)
            self.assertEqual(result.namespace, name)
        self.assertEqual(total, CATALOG_TOTAL)
        totals = self.counts()
        self.assertEqual(totals['groups'], 6)
        self.assertEqual(totals['elements'], CATALOG_TOTAL)
        self.assertEqual(totals['element_versions'], CATALOG_TOTAL)

    def test_every_element_keeps_its_original_payload_byte_for_byte(self):
        for name in CATALOG_GROUPS:
            self.import_doc(self.documents[name])
        for name in CATALOG_GROUPS:
            for raw in self.documents[name]['elements']:
                item = enc.get(self.db, raw['id'], namespace=name)
                # 原对象整份保留（含 variants/story_roles/genre_relevance/related_catalog_ids…）
                self.assertEqual(item['payload'], raw)
                for key in raw:
                    self.assertIn(key, item['payload'])
                self.assertEqual(item['content_hash'],
                                 hashlib.sha256(enc.canonical_json(raw).encode('utf-8')).hexdigest())

    def test_legacy_details_are_mapped_and_originals_stay_in_details_extra(self):
        self.import_doc(self.documents['eastern'])
        item = enc.get(self.db, 'eastern_cultivator_strata')
        self.assertEqual(item['details_map']['story_uses'], 'story_consequences')
        self.assertEqual(item['details_map']['historical_scope'], 'adaptation_limits')
        self.assertEqual(item['details']['story_uses'],
                         item['payload']['details']['story_consequences'])
        self.assertEqual(item['details']['historical_scope'],
                         item['payload']['details']['adaptation_limits'])
        self.assertEqual(sorted(item['details']), sorted(SECTIONS))

    def test_extra_detail_sections_are_preserved_not_dropped(self):
        self.import_doc(self.documents['western'])
        item = enc.get(self.db, 'western_dragon')
        self.assertIn('parameter_dimensions', item['details_extra'])
        # 既不是七节也不是字符串——原样保留，不强制转类型、不丢弃。
        self.assertEqual(item['details_extra']['parameter_dimensions'],
                         item['payload']['details']['parameter_dimensions'])
        self.assertIn('parameter_dimensions', item['payload']['details'])

    def test_category_and_genres_become_namespaced_tags(self):
        self.import_doc(self.documents['eastern'])
        item = enc.get(self.db, 'eastern_cultivator_strata')
        self.assertIn('category:life', item['tags'])
        self.assertIn('genre:eastern_fantasy', item['tags'])
        self.assertIn('genre:xianxia', item['tags'])
        # 原始 genres/category 仍在 payload 里，标签只是检索手段。
        self.assertEqual(item['payload']['category'], 'life')

    def test_no_review_or_detail_status_is_ever_promoted(self):
        for name in CATALOG_GROUPS:
            self.import_doc(self.documents[name])
        conn = sqlite3.connect(str(self.db))
        try:
            detail = {row[0] for row in conn.execute('SELECT DISTINCT detail_status FROM elements')}
            review = {row[0] for row in conn.execute('SELECT DISTINCT review_status FROM elements')}
        finally:
            conn.close()
        self.assertEqual(detail, {'needs_detail'})
        self.assertNotIn('reviewed_detail', detail)
        self.assertEqual(review, {'needs_review'})

    def test_source_access_read_is_recorded_not_treated_as_verified(self):
        self.import_doc(self.documents['steam-horror'])
        item = enc.get(self.db, 'steam_reciprocating_engine')
        self.assertTrue(item['sources'])
        for source in item['sources']:
            self.assertIn(source['access'], ('read', 'search_only', 'unavailable'))
            self.assertEqual(source['status'], 'batch')
        # 状态字段仍是候选，不因来源是 read 而变成 reviewed。
        self.assertEqual(item['review_status'], 'needs_review')
        self.assertEqual(item['detail_status'], 'needs_detail')

    def test_catalog_relations_resolve_across_groups_and_report_pending_first(self):
        first = self.import_doc(self.documents['reality-physical'])
        self.assertTrue(first.unresolved_relations, '现实分区首次导入应存在跨组未解析关联')
        pending = enc.get(self.db, 'reality_phys_gravity_load')['relations']
        self.assertTrue(any(relation['status'] == 'pending' for relation in pending))
        for name in ('steam-horror', 'society', 'western', 'eastern', 'reality-human'):
            self.import_doc(self.documents[name])
        resolved = enc.get(self.db, 'reality_phys_gravity_load')['relations']
        self.assertTrue(all(relation['status'] == 'resolved' for relation in resolved))
        for relation in resolved:
            target = enc.get(self.db, relation['target_id'])
            self.assertEqual(target['namespace'], relation['target_namespace'])

    def test_shared_themes_file_is_not_imported_as_elements(self):
        path = CATALOG_DIR / 'shared-themes.json'
        if not path.exists():
            self.skipTest('缺少 shared-themes.json')
        with self.assertRaises(enc.InvalidDocument):
            enc.import_file(self.db, path)
        self.assertEqual(self.raw_counts()['elements'], 0)

    def test_source_files_are_never_modified(self):
        for name in CATALOG_GROUPS:
            self.import_doc(self.documents[name])
        for path in self.files:
            after = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(after, self.before[path.name], '%s 被改动了' % path.name)

    def test_full_catalog_export_restore_round_trip(self):
        for name in CATALOG_GROUPS:
            self.import_doc(self.documents[name])
        exported = enc.export_document(self.db)
        self.assertEqual(exported['counts']['groups'], 6)
        self.assertEqual(exported['counts']['element_versions'], CATALOG_TOTAL)
        other = self.dir / 'catalog-copy.sqlite3'
        enc.restore_document(other, exported)
        again = enc.export_document(other)
        self.assertEqual(again['elements'], exported['elements'])
        self.assertEqual(again['sources'], exported['sources'])
        self.assertEqual(again['groups'], exported['groups'])


# --------------------------------------------------------------------------- 新七节 schema（人类百科）
class HumanSchemaTests(Base):
    def test_new_schema_requires_all_seven_sections(self):
        element = make_element('demo_a', '甲')
        del element['details']['historical_scope']
        with self.assertRaises(enc.InvalidDocument):
            self.import_doc(make_document('demo', [element], [make_source('demo_src_a')]))

    def test_new_schema_keeps_tags_and_payload(self):
        element = make_element('demo_a', '小麦', tags=['crop', 'cereal'],
                               extra={'custom_field': {'nested': [1, 2, 3]}})
        self.import_doc(make_document('demo', [element], [make_source('demo_src_a')]))
        item = enc.get(self.db, 'demo_a')
        self.assertEqual(item['adapter'], enc.ADAPTER_HUMAN)
        self.assertFalse(item['legacy_schema'])
        self.assertEqual(item['details_map'], {section: section for section in SECTIONS})
        self.assertEqual(item['payload']['custom_field'], {'nested': [1, 2, 3]})

    def test_schema_version_must_be_accepted_but_extra_meta_is_kept(self):
        document = make_document('demo', [make_element('demo_a', '甲')], [make_source('demo_src_a')],
                                 scope_note='范围说明', schema_version=1)
        self.import_doc(document)
        exported = enc.export_document(self.db)
        self.assertEqual(exported['groups'][0]['meta']['scope_note'], '范围说明')
        self.assertNotIn('elements', exported['groups'][0]['meta'])

    def test_every_delivered_human_group_imports_when_parseable(self):
        """已交付且可解析的组都应能整批导入；正在被写入的半份 JSON 直接跳过。

        不写死条数：采集侧还在交付中，写死会让测试变成进度快照。
        """
        imported = 0
        for path in sorted(HUMAN_DIR.glob('*.json')):
            try:
                document = json.loads(path.read_text(encoding='utf-8'))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue  # 其他代理正在写入的半份文件
            if not isinstance(document.get('elements'), list) or not document['elements']:
                continue
            result = enc.import_file(self.db, path)
            self.assertEqual(result.adapter, enc.ADAPTER_HUMAN, path.name)
            self.assertEqual(result.namespace, path.stem)
            self.assertEqual(result.element_versions, len(document['elements']), path.name)
            imported += 1
        if not imported:
            self.skipTest('当前没有可解析的人类百科组')
        totals = self.counts()
        self.assertEqual(totals['groups'], imported)
        self.assertEqual(totals['elements'], totals['element_versions'])
        # 每组内元素数对得上，且每个条目都能按自己的命名空间读回。
        for path in sorted(HUMAN_DIR.glob('*.json')):
            try:
                document = json.loads(path.read_text(encoding='utf-8'))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            if not isinstance(document.get('elements'), list) or not document['elements']:
                continue
            page = enc.search(self.db, namespace=path.stem, limit=enc.MAX_PAGE_SIZE)
            self.assertEqual(page['total'], len(document['elements']), path.name)
            for raw in document['elements']:
                item = enc.get(self.db, raw['id'], namespace=path.stem)
                self.assertEqual(item['payload'], raw, '%s/%s' % (path.name, raw['id']))

    def test_staples_file_imports_when_present(self):
        path = HUMAN_DIR / 'staples.json'
        if not path.exists():
            self.skipTest('缺少 staples.json')
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        result = enc.import_file(self.db, path)
        self.assertEqual(result.adapter, enc.ADAPTER_HUMAN)
        self.assertEqual(result.namespace, 'staples')
        self.assertGreater(result.element_versions, 0)
        item = enc.get(self.db, 'staples_wheat')
        self.assertEqual(item['name'], '小麦')
        self.assertEqual(item['detail_status'], 'needs_detail')
        self.assertEqual(item['review_status'], 'needs_review')
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)


# --------------------------------------------------------------------------- CLI
class CliTests(Base):
    def run_cli(self, *argv):
        buffer = []

        class Capture:
            def write(self, text):
                buffer.append(text)

            def flush(self):
                pass

        stdout, stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = Capture(), Capture()
        try:
            code = cli.main(list(argv))
        finally:
            sys.stdout, sys.stderr = stdout, stderr
        return code, ''.join(buffer)

    def write_doc(self, name, document):
        path = self.dir / name
        path.write_text(json.dumps(document, ensure_ascii=False), encoding='utf-8')
        return path

    def test_import_search_get_and_export_via_cli(self):
        path = self.write_doc('demo.json', make_document(
            'demo', [make_element('demo_wheat', '小麦', aliases=['wheat'], tags=['crop', 'cereal'])],
            [make_source('demo_src_a')]))
        code, out = self.run_cli('import', '--db', str(self.db), str(path), '--json')
        self.assertEqual(code, 0)
        self.assertIn('demo', out)

        code, out = self.run_cli('search', '--db', str(self.db), '--text', '小麦')
        self.assertEqual(code, 0)
        self.assertIn('demo_wheat', out)

        code, out = self.run_cli('get', '--db', str(self.db), 'demo_wheat')
        self.assertEqual(code, 0)
        self.assertIn('小麦', out)

        out_path = self.dir / 'dump.json'
        code, out = self.run_cli('export', '--db', str(self.db), '--out', str(out_path))
        self.assertEqual(code, 0)
        document = json.loads(out_path.read_text(encoding='utf-8'))
        self.assertEqual(document['counts']['element_versions'], 1)

        second = self.dir / 'second.sqlite3'
        code, out = self.run_cli('restore', '--db', str(second), str(out_path))
        self.assertEqual(code, 0)
        self.assertEqual(self.counts(second)['elements'], 1)

    def test_cli_reports_domain_errors_with_exit_one(self):
        code, _ = self.run_cli('stats', '--db', str(self.dir / 'missing.sqlite3'))
        self.assertEqual(code, 1)
        path = self.write_doc('bad.json', make_document(
            'demo', [make_element('demo_a', '甲', source_ids=['nope'])], []))
        code, _ = self.run_cli('import', '--db', str(self.db), str(path))
        self.assertEqual(code, 1)
        conn = sqlite3.connect(str(self.db))
        try:
            version = enc.read_schema_version(conn)
        finally:
            conn.close()
        self.assertEqual(version, enc.SCHEMA_VERSION)
        self.assertEqual(self.raw_counts()['elements'], 0)

    def test_cli_rejects_out_of_range_limit(self):
        path = self.write_doc('demo.json', make_document(
            'demo', [make_element('demo_a', '甲')], [make_source('demo_src_a')]))
        self.run_cli('import', '--db', str(self.db), str(path))
        code, _ = self.run_cli('search', '--db', str(self.db), '--limit', '999')
        self.assertEqual(code, 1)

    def test_cli_requires_db_argument(self):
        stderr = sys.stderr
        sys.stderr = open(os.devnull, 'w', encoding='utf-8')
        try:
            with self.assertRaises(SystemExit):
                self.run_cli('search', '--text', '小麦')
        finally:
            sys.stderr.close()
            sys.stderr = stderr

    def test_cli_module_entry_point(self):
        """真实子进程：确认 -m 入口、UTF-8 输出与退出码。"""
        path = self.write_doc('demo.json', make_document(
            'demo', [make_element('demo_a', '小麦')], [make_source('demo_src_a')]))
        env = dict(os.environ, PYTHONIOENCODING='utf-8')
        run = subprocess.run(
            [sys.executable, '-X', 'utf8', '-m', 'tools.encyclopedia_cli', 'import',
             '--db', str(self.db), str(path), '--json'],
            cwd=str(ROOT), capture_output=True, text=True, encoding='utf-8', env=env,
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn('demo', run.stdout)
        self.assertEqual(self.counts()['elements'], 1)


# --------------------------------------------------------------------------- 不碰运行库
class IsolationTests(unittest.TestCase):
    def test_module_does_not_touch_journey_database_or_startup(self):
        module_path = ROOT / 'app' / 'encyclopedia.py'
        source = module_path.read_text(encoding='utf-8')
        for forbidden in ('from .storage', 'from .service', 'import app.main',
                          'from .runtime', 'textiledream.sqlite3', 'StoryPackage/'):
            self.assertNotIn(forbidden, source)
        self.assertNotIn('encyclopedia', (ROOT / 'launch.py').read_text(encoding='utf-8'))
        self.assertNotIn('encyclopedia', (ROOT / 'app' / 'main.py').read_text(encoding='utf-8'))

    def test_cli_has_no_default_database_path(self):
        parser = cli.build_parser()
        stderr = sys.stderr
        sys.stderr = open(os.devnull, 'w', encoding='utf-8')
        try:
            with self.assertRaises(SystemExit):
                parser.parse_args(['import'])
        finally:
            sys.stderr.close()
            sys.stderr = stderr
        args = parser.parse_args(['import', '--db', 'x.sqlite3', 'a.json'])
        self.assertEqual(args.db, 'x.sqlite3')


if __name__ == '__main__':
    unittest.main()
