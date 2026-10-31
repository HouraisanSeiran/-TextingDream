# -*- coding: utf-8 -*-
"""构库名单扩展（food-supplement / craft-supplement）与增补组的集成测试。

这些测试补的是「扩展后的 14 组名单」这一层：显式名单是否真的把两个增补组带进库、
跨组 `related_ids` 能否解析、多标签检索、重复导入零写入、来源版本 pin、导出/还原
保留，以及**已发布的旧 12 组库同库追加新 namespace 时旧内容不变**。

只依赖 ID / 数量 / 不变量，不断言采集侧的具体措辞（craft-supplement 还在做证据
勘误，正文措辞会变）。所有库都建在系统临时目录，不生成也不覆写
`artifacts/human-encyclopedia/encyclopedia.sqlite3`。

为何导入冻结快照而不直接导入 ``docs/`` 里的文件：增补组此刻正被采集代理逐条复核
改写（同一份 JSON 会在测试跑完后字节变化），直接拿它做重复导入/幂等断言会变成
进程竞争。因此 setUpClass 把当刻读到的文档写成一份临时副本再导入；
「磁盘上的真实文件能被导入且条数相符」由 `RealFileSnapshotTests` 单独覆盖。
"""
import contextlib
import hashlib
import io
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import encyclopedia as enc  # noqa: E402
from tools import encyclopedia_build as build  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
HUMAN_DIR = ROOT / 'docs' / 'human-encyclopedia'
CATALOG_DIR = ROOT / 'docs' / 'element-catalog'

# 现实生产生活六组：构库名单里的原 12 组中的前六组（207 条）。
BASE_HUMAN = ('staples', 'produce', 'flavors', 'animal-foods', 'materials', 'tools')
BASE_HUMAN_TOTAL = 207

# 原 element-catalog 六组（四个虚构题材组 + 现实两分区），274 条。
CATALOG_GROUPS = ('eastern', 'western', 'society', 'steam-horror', 'reality-physical', 'reality-human')
CATALOG_TOTAL = 274

# 本轮新增的两个增补组。
SUPPLEMENT_GROUPS = ('food-supplement', 'craft-supplement')

# 扩展名单后的总量：原 481（207 + 274）+ 本轮 47 = 528，组数 12 + 2 = 14。
EXPECTED_GROUPS = len(BASE_HUMAN) + len(CATALOG_GROUPS) + len(SUPPLEMENT_GROUPS)
EXPECTED_ELEMENTS = BASE_HUMAN_TOTAL + CATALOG_TOTAL + 47

SECTIONS = (
    'definition', 'mechanism', 'conditions', 'exceptions',
    'story_uses', 'historical_scope', 'evidence_and_uncertainty',
)


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


class SupplementCase(unittest.TestCase):
    """源文档读一次 → 冻结成临时副本 → 后续所有导入都拿副本，结果可重复。"""

    @classmethod
    def setUpClass(cls):
        cls.paths = {name: HUMAN_DIR / ('%s.json' % name) for name in BASE_HUMAN + SUPPLEMENT_GROUPS}
        cls.paths.update({name: CATALOG_DIR / ('%s.json' % name) for name in CATALOG_GROUPS})
        missing = [str(path) for path in cls.paths.values() if not path.exists()]
        if missing:
            raise unittest.SkipTest('缺少采集 JSON：%s' % ', '.join(missing))
        cls.documents = {name: load(path) for name, path in cls.paths.items()}
        cls.frozen = tempfile.TemporaryDirectory()
        cls.frozen_paths = {}
        for name, document in cls.documents.items():
            path = Path(cls.frozen.name) / ('%s.json' % name)
            path.write_text(json.dumps(document, ensure_ascii=False), encoding='utf-8')
            cls.frozen_paths[name] = path
        cls.expected_elements = {name: len(doc['elements']) for name, doc in cls.documents.items()}

    @classmethod
    def tearDownClass(cls):
        cls.frozen.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.db = self.dir / 'encyclopedia.sqlite3'

    def tearDown(self):
        self.tmp.cleanup()

    # ------------------------------------------------------------------ 夹具
    def import_group(self, name, db=None):
        return enc.import_file(db or self.db, self.frozen_paths[name])

    def import_all(self, names, db=None):
        return [self.import_group(name, db=db) for name in names]

    def counts(self, db=None):
        return enc.stats(db or self.db)['totals']

    def namespaces(self, db=None):
        return [group['namespace'] for group in enc.stats(db or self.db)['groups']]


def cross_ref_element(case, name):
    """找一个 related_ids 指向本组以外的元素；跨组解析必须有真实对象可验。"""
    document = case.documents[name]
    own = {element['id'] for element in document['elements']}
    for element in document['elements']:
        targets = list(element.get('related_ids') or [])
        if any(target not in own for target in targets):
            return element, targets
    case.fail('%s 里没有任何跨组 related_ids，跨组解析无从验证' % name)


def external_targets(document):
    """整份文档里指向别组的 related_id 全集（去重）。"""
    own = {element['id'] for element in document['elements']}
    return {target for element in document['elements']
            for target in element.get('related_ids') or [] if target not in own}


# --------------------------------------------------------------------------- 真实文件
class RealFileSnapshotTests(SupplementCase):
    """磁盘上的两份增补 JSON：真能整批导入，且条数与本轮冻结快照一致。"""

    def test_both_real_files_import_with_snapshot_counts(self):
        for name in SUPPLEMENT_GROUPS:
            path = self.paths[name]
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            result = enc.import_file(self.db, path)
            self.assertEqual(result.adapter, enc.ADAPTER_HUMAN, name)
            self.assertEqual(result.namespace, name)
            self.assertEqual(result.element_versions, self.expected_elements[name], name)
            self.assertEqual(result.element_versions, len(load(path)['elements']), name)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest,
                             '%s 在导入过程中被改动了' % path)
        # 本轮快照：23 + 24 = 47；六组 207 + 原六组 274 + 47 = 528。
        self.assertEqual(self.counts()['elements'], 47)
        self.assertEqual(self.counts()['groups'], 2)
        self.assertEqual(EXPECTED_GROUPS, 14)
        self.assertEqual(EXPECTED_ELEMENTS, 528)

    def test_snapshot_documents_are_candidates_with_seven_sections(self):
        for name in SUPPLEMENT_GROUPS:
            document = self.documents[name]
            self.assertEqual(document.get('schema_version'), 1, name)
            self.assertEqual(document.get('status'), 'candidate', name)
            self.assertEqual(document.get('group'), name, name)
            for element in document['elements']:
                self.assertEqual(element.get('review_status'), 'needs_review', element['id'])
                self.assertEqual(sorted(element['details']), sorted(SECTIONS), element['id'])


# --------------------------------------------------------------------------- 显式名单
class BuildManifestTests(SupplementCase):
    """构库名单是显式 14 组：两个增补组必须在册，shared-themes 必须不在册。"""

    def test_manifest_lists_fourteen_explicit_files(self):
        self.assertEqual(len(build.GROUPS), EXPECTED_GROUPS)
        self.assertEqual(len(set(build.GROUPS)), len(build.GROUPS), '名单里有重复项')
        for relative in build.GROUPS:
            self.assertNotIn('*', relative, '构库名单不允许通配，必须逐组显式登记')
            self.assertTrue(relative.endswith('.json'), relative)
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_supplement_groups_are_registered_by_name(self):
        human = [name for name in build.GROUPS if name.startswith('docs/human-encyclopedia/')]
        self.assertEqual(sorted(human),
                         sorted('docs/human-encyclopedia/%s.json' % name
                                for name in BASE_HUMAN + SUPPLEMENT_GROUPS))
        for name in SUPPLEMENT_GROUPS:
            self.assertIn('docs/human-encyclopedia/%s.json' % name, build.GROUPS)

    def test_cluster_index_stays_excluded_and_off_manifest(self):
        self.assertIn('docs/element-catalog/shared-themes.json', build.EXCLUDED)
        self.assertNotIn('docs/element-catalog/shared-themes.json', build.GROUPS)

    def test_manifest_counts_match_source_documents(self):
        """名单里的预期条数只从源 JSON 读，写库前就能核对；总数不写死。"""
        rows = build._expected()
        self.assertEqual(len(rows), EXPECTED_GROUPS)
        by_file = {row['file']: row for row in rows}
        for name, expected in self.expected_elements.items():
            prefix = 'docs/human-encyclopedia/' if name in BASE_HUMAN + SUPPLEMENT_GROUPS \
                else 'docs/element-catalog/'
            row = by_file[prefix + '%s.json' % name]
            self.assertEqual(row['elements'], expected, name)
            self.assertEqual(row['group'], name, name)
        self.assertEqual(sum(row['elements'] for row in rows), EXPECTED_ELEMENTS)
        # 来源条数一律从 JSON 现算，不写死历史值。
        sources = sum(row['sources'] for row in rows)
        self.assertEqual(sources, sum(len(doc['sources']) for doc in self.documents.values()))

    def test_build_and_check_report_fourteen_groups_and_528_elements(self):
        """真实走一遍构库 + --check（输出丢进缓冲，不刷屏）。"""
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            self.assertEqual(build.build(str(self.db)), 0)
            self.assertEqual(build.check(str(self.db)), 0)
        totals = self.counts()
        self.assertEqual(totals['groups'], EXPECTED_GROUPS)
        self.assertEqual(totals['elements'], EXPECTED_ELEMENTS)
        self.assertEqual(totals['element_versions'], EXPECTED_ELEMENTS)
        self.assertEqual(totals['unresolved_relations'], 0)
        self.assertEqual(sorted(self.namespaces()),
                         sorted(BASE_HUMAN + SUPPLEMENT_GROUPS + CATALOG_GROUPS))
        self.assertIn('14 组', stream.getvalue())
        self.assertIn('528', stream.getvalue())
        # 构库把两个增补组写进了各自的命名空间，且都是一份新版本。
        for name in SUPPLEMENT_GROUPS:
            group = [row for row in enc.stats(self.db)['groups'] if row['namespace'] == name][0]
            self.assertEqual(group['elements'], self.expected_elements[name])
            self.assertEqual(group['element_versions'], self.expected_elements[name])

    def test_check_reports_missing_namespace_instead_of_silently_passing(self):
        self.import_group('food-supplement')
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            self.assertEqual(build.check(str(self.db)), 1)
        self.assertIn('craft-supplement', stream.getvalue())


# --------------------------------------------------------------------------- 增补导入
class SupplementImportTests(SupplementCase):
    """两个增补组整批导入：条数、adapter、状态、payload 无损。"""

    def test_both_supplement_groups_import_with_their_own_namespace(self):
        total = 0
        for name in SUPPLEMENT_GROUPS:
            result = self.import_group(name)
            self.assertEqual(result.adapter, enc.ADAPTER_HUMAN, name)
            self.assertEqual(result.namespace, name)
            self.assertFalse(result.idempotent)
            self.assertEqual(result.element_versions, self.expected_elements[name], name)
            self.assertEqual(result.sources, len(self.documents[name]['sources']), name)
            self.assertEqual(result.shared_element_ids, [], '%s 的 id 与其他组撞了' % name)
            total += result.element_versions
        self.assertEqual(total, 47)
        totals = self.counts()
        self.assertEqual(totals['groups'], len(SUPPLEMENT_GROUPS))
        self.assertEqual(totals['elements'], 47)
        self.assertEqual(totals['sources'],
                         sum(len(self.documents[name]['sources']) for name in SUPPLEMENT_GROUPS))

    def test_every_supplement_element_reads_back_byte_for_byte(self):
        self.import_all(SUPPLEMENT_GROUPS)
        for name in SUPPLEMENT_GROUPS:
            for raw in self.documents[name]['elements']:
                item = enc.get(self.db, raw['id'], namespace=name)
                self.assertEqual(item['payload'], raw, '%s/%s' % (name, raw['id']))
                self.assertEqual(item['review_status'], 'needs_review', raw['id'])
                self.assertEqual(item['detail_status'], 'needs_detail', raw['id'])
                self.assertEqual(sorted(item['details']), sorted(SECTIONS), raw['id'])
                self.assertFalse(item['legacy_schema'], raw['id'])

    def test_supplement_elements_are_not_promoted_by_import(self):
        self.import_all(SUPPLEMENT_GROUPS)
        conn = sqlite3.connect(str(self.db))
        try:
            review = {row[0] for row in conn.execute(
                'SELECT DISTINCT review_status FROM elements WHERE namespace IN (?,?)',
                SUPPLEMENT_GROUPS)}
            detail = {row[0] for row in conn.execute(
                'SELECT DISTINCT detail_status FROM elements WHERE namespace IN (?,?)',
                SUPPLEMENT_GROUPS)}
        finally:
            conn.close()
        self.assertEqual(review, {'needs_review'})
        self.assertEqual(detail, {'needs_detail'})

    def test_supplement_sources_record_access_verbatim(self):
        """access 原值入库：read 只是采集侧声明读过正文，不等于事实核实。"""
        self.import_all(SUPPLEMENT_GROUPS)
        for name in SUPPLEMENT_GROUPS:
            rows = {source['id']: source for source in self.documents[name]['sources']}
            for element in self.documents[name]['elements']:
                item = enc.get(self.db, element['id'], namespace=name)
                self.assertTrue(item['sources'], element['id'])
                for source in item['sources']:
                    self.assertEqual(source['access'], rows[source['source_id']]['access'], element['id'])
                    self.assertIn(source['access'], ('read', 'search_only', 'unavailable'))
                    self.assertEqual(source['status'], 'batch')


# --------------------------------------------------------------------------- 跨组关联
class CrossGroupRelationTests(SupplementCase):
    """增补组的 related_ids 指向六组 / 原六组的 id：先 pending，目标入库后 resolved。"""

    def test_cross_group_relations_are_pending_before_targets_import(self):
        element, _ = cross_ref_element(self, 'food-supplement')
        result = self.import_group('food-supplement')
        self.assertTrue(result.unresolved_relations, '首次导入应有跨组未解析关联')
        pending_ids = {item['target_id'] for item in result.unresolved_relations}
        # 报告里的未解析目标必须全部是本组以外的真实引用，不多不少。
        self.assertEqual(pending_ids, external_targets(self.documents['food-supplement']))
        relations = enc.get(self.db, element['id'], namespace='food-supplement')['relations']
        self.assertTrue(any(relation['status'] == 'pending' for relation in relations))
        # pending 不是有效关联：目标命名空间为空。
        for relation in relations:
            if relation['status'] == 'pending':
                self.assertIsNone(relation['target_namespace'])

    def test_relations_resolve_once_base_groups_are_imported(self):
        elements = {name: cross_ref_element(self, name)[0] for name in SUPPLEMENT_GROUPS}
        self.import_all(SUPPLEMENT_GROUPS)
        self.import_all(BASE_HUMAN)
        for name, element in elements.items():
            relations = enc.get(self.db, element['id'], namespace=name)['relations']
            self.assertTrue(relations, element['id'])
            for relation in relations:
                self.assertEqual(relation['status'], 'resolved',
                                 '%s/%s -> %s' % (name, element['id'], relation['target_id']))
                self.assertIsNotNone(relation['target_namespace'])
                target = enc.get(self.db, relation['target_id'],
                                 namespace=relation['target_namespace'])
                self.assertEqual(target['namespace'], relation['target_namespace'])
        self.assertEqual(self.counts()['unresolved_relations'], 0)

    def test_relations_to_unimported_groups_stay_pending_not_faked(self):
        """只导入增补组时，指向生活六组的关联全为 pending，不假称解析。"""
        for name in SUPPLEMENT_GROUPS:
            result = self.import_group(name)
            self.assertEqual({item['target_id'] for item in result.unresolved_relations},
                             external_targets(self.documents[name]), name)
        self.import_all(BASE_HUMAN)
        self.assertEqual(self.counts()['unresolved_relations'], 0)
        # 目标组全部入库后，再拿一个原本 pending 的关联验它真的 resolved。
        element, _ = cross_ref_element(self, 'craft-supplement')
        relations = enc.get(self.db, element['id'], namespace='craft-supplement')['relations']
        self.assertTrue(relations, element['id'])
        self.assertTrue(all(relation['status'] == 'resolved' for relation in relations),
                        [(relation['target_id'], relation['status']) for relation in relations])

    def test_supplement_sources_do_not_resolve_across_namespaces(self):
        self.import_all(SUPPLEMENT_GROUPS + BASE_HUMAN)
        conn = sqlite3.connect(str(self.db))
        try:
            rows = conn.execute(
                'SELECT es.namespace, es.element_id, es.source_namespace FROM element_sources es'
                ' WHERE es.source_namespace <> es.namespace').fetchall()
        finally:
            conn.close()
        self.assertEqual(rows, [], '增补组的来源不应跨命名空间解析')


# --------------------------------------------------------------------------- 多标签检索
class MultiTagQueryTests(SupplementCase):
    """多标签 AND/OR/组合与命名空间限定在增补组上成立。"""

    def pick(self, name, minimum=3):
        for element in self.documents[name]['elements']:
            if len(element.get('tags') or []) >= minimum:
                return element
        self.fail('%s 里没有 %d 个以上标签的条目' % (name, minimum))

    def test_tags_all_and_tags_any_narrow_the_same_row_set(self):
        self.import_all(SUPPLEMENT_GROUPS)
        element = self.pick('food-supplement')
        tags = list(element['tags'])[:3]
        every = enc.search(self.db, tags_all=tags, limit=enc.MAX_PAGE_SIZE)
        some = enc.search(self.db, tags_any=tags, limit=enc.MAX_PAGE_SIZE)
        self.assertGreaterEqual(some['total'], every['total'])
        self.assertIn(element['id'], {item['element_id'] for item in every['items']})
        for item in every['items']:
            self.assertTrue(set(tags) <= set(item['tags']), item['element_id'])
        self.assertEqual(every['total'], len(every['items']))

    def test_namespace_scoping_keeps_supplements_separate(self):
        self.import_all(SUPPLEMENT_GROUPS)
        element = self.pick('craft-supplement')
        tag = element['tags'][0]
        scoped = enc.search(self.db, tags_any=[tag], namespace='craft-supplement',
                            limit=enc.MAX_PAGE_SIZE)
        self.assertIn(element['id'], {item['element_id'] for item in scoped['items']})
        for item in scoped['items']:
            self.assertEqual(item['namespace'], 'craft-supplement')
        unscoped = enc.search(self.db, tags_any=[tag], limit=enc.MAX_PAGE_SIZE)
        self.assertGreaterEqual(unscoped['total'], scoped['total'])

    def test_text_and_tags_combine_on_supplement_rows(self):
        self.import_all(SUPPLEMENT_GROUPS)
        element = self.pick('craft-supplement')
        page = enc.search(self.db, text=element['name'], tags_all=element['tags'][:2],
                          limit=enc.MAX_PAGE_SIZE)
        self.assertIn(element['id'], {item['element_id'] for item in page['items']})

    def test_unknown_tag_returns_empty_not_error(self):
        self.import_all(SUPPLEMENT_GROUPS)
        page = enc.search(self.db, tags_all=['no_such_tag_at_all'])
        self.assertEqual(page['total'], 0)
        self.assertEqual(page['items'], [])

    def test_tag_listing_includes_supplement_tags(self):
        self.import_all(SUPPLEMENT_GROUPS)
        tags = {row['tag'] for row in enc.list_tags(self.db, namespace='craft-supplement')['tags']}
        for tag in self.pick('craft-supplement')['tags']:
            self.assertIn(tag, tags)


# --------------------------------------------------------------------------- 幂等
class RepeatImportTests(SupplementCase):
    """重复导入同一批增补文件是零写入的（元素级 + 批次级哈希）。"""

    def test_second_import_of_same_file_adds_no_version(self):
        self.import_group('food-supplement')
        before = self.counts()
        groups_before = {group['namespace']: group for group in enc.stats(self.db)['groups']}
        again = self.import_group('food-supplement')
        self.assertTrue(again.idempotent)
        self.assertEqual(again.element_versions, 0)
        self.assertEqual(again.source_versions, 0)
        self.assertEqual(self.counts(), before)
        self.assertEqual({group['namespace']: group for group in enc.stats(self.db)['groups']},
                         groups_before)

    def test_repeat_after_full_build_is_still_zero_write(self):
        self.import_all(BASE_HUMAN + SUPPLEMENT_GROUPS + CATALOG_GROUPS)
        before = self.counts()
        digest = hashlib.sha256(self.db.read_bytes()).hexdigest()
        for name in SUPPLEMENT_GROUPS:
            result = self.import_group(name)
            self.assertTrue(result.idempotent, name)
            self.assertEqual(result.element_versions, 0, name)
            self.assertEqual(result.source_versions, 0, name)
        self.assertEqual(hashlib.sha256(self.db.read_bytes()).hexdigest(), digest,
                         '重复导入不该改动库文件')
        self.assertEqual(self.counts(), before)
        versions = enc.versions(self.db, 'food_supp_proso_millet')
        self.assertEqual([row['version'] for row in versions['versions']], [1])


# --------------------------------------------------------------------------- 证据 pin
class SupplementSourcePinTests(SupplementCase):
    """增补组的元素版本固定当批来源版本，pin 不能为 NULL、不能指向不存在的版本。"""

    def test_every_supplement_element_source_has_a_resolvable_pin(self):
        self.import_all(SUPPLEMENT_GROUPS)
        conn = sqlite3.connect(str(self.db))
        try:
            total = conn.execute(
                'SELECT COUNT(*) FROM element_sources WHERE namespace IN (?,?)',
                SUPPLEMENT_GROUPS).fetchone()[0]
            unpinned = conn.execute(
                'SELECT COUNT(*) FROM element_sources WHERE namespace IN (?,?)'
                ' AND source_version IS NULL', SUPPLEMENT_GROUPS).fetchone()[0]
            orphans = conn.execute(
                'SELECT COUNT(*) FROM element_sources es'
                ' LEFT JOIN source_versions sv ON sv.namespace=es.source_namespace'
                '  AND sv.source_id=es.source_id AND sv.version=es.source_version'
                ' WHERE es.namespace IN (?,?) AND sv.source_id IS NULL',
                SUPPLEMENT_GROUPS).fetchone()[0]
        finally:
            conn.close()
        self.assertGreater(total, 0)
        self.assertEqual(unpinned, 0)
        self.assertEqual(orphans, 0)

    def test_element_and_source_versions_are_pinned_together(self):
        self.import_all(SUPPLEMENT_GROUPS)
        element = self.documents['craft-supplement']['elements'][0]
        item = enc.get(self.db, element['id'], namespace='craft-supplement')
        self.assertTrue(item['sources'], element['id'])
        for source in item['sources']:
            self.assertEqual(source['source_version'], 1)
            self.assertTrue(source['is_current_source_version'])
            self.assertEqual(source['payload']['access'], source['access'])
        exported = enc.export_document(self.db, namespaces=['craft-supplement'])
        refs = [ref for row in exported['elements'] for ref in row['source_refs']]
        self.assertTrue(refs)
        for ref in refs:
            self.assertIn('source_version', ref)
            self.assertIsNotNone(ref['source_version'])


# --------------------------------------------------------------------------- 导出/还原
class SupplementExportRestoreTests(SupplementCase):
    def test_export_then_restore_preserves_supplement_rows(self):
        names = SUPPLEMENT_GROUPS + ('staples',)
        self.import_all(names)
        exported = enc.export_document(self.db)
        self.assertEqual(exported['export_version'], enc.EXPORT_VERSION)
        self.assertEqual(exported['counts']['groups'], len(names))
        self.assertEqual(exported['counts']['element_versions'],
                         sum(self.expected_elements[name] for name in names))
        other = self.dir / 'restored.sqlite3'
        enc.restore_document(other, exported)
        again = enc.export_document(other)
        self.assertEqual(again['groups'], exported['groups'])
        self.assertEqual(again['sources'], exported['sources'])
        self.assertEqual(again['elements'], exported['elements'])
        self.assertEqual(self.counts(other), self.counts(), '还原后的计数必须与原库一致')
        self.assertEqual(sorted(self.namespaces(other)), sorted(names))

    def test_supplement_only_export_keeps_relations_pending_not_faked(self):
        """只导出 food-supplement 时，指向其他组的关联在还原后仍是 pending。"""
        self.import_all(SUPPLEMENT_GROUPS)
        exported = enc.export_document(self.db, namespaces=['food-supplement'])
        other = self.dir / 'only-food.sqlite3'
        enc.restore_document(other, exported)
        self.assertEqual(self.namespaces(other), ['food-supplement'])
        element, _ = cross_ref_element(self, 'food-supplement')
        relations = enc.get(other, element['id'], namespace='food-supplement')['relations']
        self.assertTrue(any(relation['status'] == 'pending' for relation in relations))
        for relation in relations:
            self.assertIn(relation['status'], ('pending', 'resolved'))


# --------------------------------------------------------------------------- 旧库兼容
class OldLibraryCompatibilityTests(SupplementCase):
    """已发布的旧 12 组库：同一库文件追加两个新 namespace，旧内容逐字段不变。"""

    OLD_GROUPS = BASE_HUMAN + CATALOG_GROUPS

    def test_adding_supplements_to_existing_library_leaves_old_rows_untouched(self):
        self.import_all(self.OLD_GROUPS)
        old_totals = self.counts()
        self.assertEqual(old_totals['groups'], 12)
        self.assertEqual(old_totals['elements'], BASE_HUMAN_TOTAL + CATALOG_TOTAL)
        before = enc.export_document(self.db, namespaces=list(self.OLD_GROUPS))

        for name in SUPPLEMENT_GROUPS:
            result = self.import_group(name)
            self.assertFalse(result.idempotent, name)
            self.assertEqual(result.element_versions, self.expected_elements[name], name)

        after = enc.export_document(self.db, namespaces=list(self.OLD_GROUPS))
        self.assertEqual(after['groups'], before['groups'], '旧组的 group 行被改动了')
        self.assertEqual(after['sources'], before['sources'], '旧组的来源版本被改动了')
        self.assertEqual(after['elements'], before['elements'], '旧组的元素版本被改动了')
        self.assertEqual(after['counts'], before['counts'])

        totals = self.counts()
        self.assertEqual(totals['groups'], EXPECTED_GROUPS)
        self.assertEqual(totals['elements'], EXPECTED_ELEMENTS)
        self.assertEqual(totals['element_versions'], EXPECTED_ELEMENTS)
        self.assertEqual(totals['unresolved_relations'], 0)
        self.assertEqual(totals['elements'] - old_totals['elements'], 47)

    def test_old_namespaces_remain_queryable_after_supplement_import(self):
        self.import_all(self.OLD_GROUPS + SUPPLEMENT_GROUPS)
        for name, element_id in (('staples', 'staples_wheat'),
                                 ('materials', 'materials_steel'),
                                 ('western', 'western_dragon')):
            item = enc.get(self.db, element_id, namespace=name, include_payload=False)
            self.assertEqual(item['namespace'], name)
            self.assertEqual(item['review_status'], 'needs_review')
        # 旧组与增补组各 1 个版本——没有因为追加而重写历史。
        for name in self.OLD_GROUPS + SUPPLEMENT_GROUPS:
            group = [row for row in enc.stats(self.db)['groups'] if row['namespace'] == name][0]
            self.assertEqual(group['element_versions'], group['elements'], name)

    def test_export_of_extended_library_restores_into_empty_database(self):
        self.import_all(self.OLD_GROUPS + SUPPLEMENT_GROUPS)
        exported = enc.export_document(self.db)
        other = self.dir / 'extended.sqlite3'
        enc.restore_document(other, exported)
        again = enc.export_document(other)
        self.assertEqual(again['groups'], exported['groups'])
        self.assertEqual(again['elements'], exported['elements'])
        self.assertEqual(again['sources'], exported['sources'])
        self.assertEqual(self.counts(other)['groups'], EXPECTED_GROUPS)
        self.assertEqual(self.counts(other)['elements'], EXPECTED_ELEMENTS)


if __name__ == '__main__':
    unittest.main()
