# -*- coding: utf-8 -*-
"""奇幻生物分区（种族 / 西幻动植物 / 东方玄幻动植物）并入统一百科库。

分工边界：三份内容文件 ``docs/element-catalog/fantasy-races.json`` /
``western-biology.json`` / ``eastern-biology.json`` 由采集侧定稿，**本测试不写它们，
也不改它们**；本文件验的是「构库侧接入」＋「内容可交付的最低约束」。

**正式交付口径（本文件遵守的约定）**：缺文件、JSON 坏、``elements`` 为空
**一律测试失败**，不存在“准备中就 skip”的模式——库要能建、名单要能核对，
内容没齐就是没齐，不能用一片绿把这个事实盖住。

标签只做**检索入口**，引擎不读它做判定：

* ``kind:race`` / ``kind:fauna`` / ``kind:flora``（以及其他 ``kind:<token>``，如 ``kind:spirit``）；
* ``tradition:eastern`` / ``tradition:western`` 等题材/传统维度。

因此下面刻意**不写死 kind 的完整取值集**：东方组把某条从 ``kind:fauna`` 改成
``kind:spirit`` 时，这些断言不应因为“分类名换了一个”而误报；该变形只影响计入
fauna / flora 的条数，而 fauna / flora 各有下限（≥ 8）保障。

状态与证据的口径：``review_status`` / ``detail_status`` 保持候选（``needs_review`` /
``needs_detail``），导入不升格；来源 ``access: read`` 只表示采集侧声称读过正文，
**不等于事实已核验**——测试能验的是引用不悬空、pin 可追溯、access 如实标注。

所有库都建在系统临时目录，**不读写** ``artifacts/human-encyclopedia/encyclopedia.sqlite3``；
交付库由主代理显式跑 ``--with-fantasy-biology`` 生成。
"""
import json
import re
import tempfile
import unittest
from pathlib import Path

from app import encyclopedia as enc
from tools import catalog_overlay
from tools import encyclopedia_build as build
from tools import game_fields

ROOT = Path(__file__).resolve().parents[1]

RACES_RELATIVE = 'docs/element-catalog/fantasy-races.json'
WESTERN_RELATIVE = 'docs/element-catalog/western-biology.json'
EASTERN_RELATIVE = 'docs/element-catalog/eastern-biology.json'
EXPECTED_FILES = (RACES_RELATIVE, WESTERN_RELATIVE, EASTERN_RELATIVE)

SECTIONS = (
    'definition', 'mechanism', 'conditions', 'exceptions',
    'story_uses', 'historical_scope', 'evidence_and_uncertainty',
)
LEGACY_SECTIONS = (
    'definition', 'mechanism', 'conditions', 'exceptions',
    'story_consequences', 'adaptation_limits', 'evidence_and_uncertainty',
)

KIND_TAGS = ('kind:race', 'kind:fauna', 'kind:flora')
# 每个生物组至少要有这么多 fauna / flora：数量低于此就说明“分好了类”只是名义上的。
MIN_BIOLOGY_PER_KIND = 8
# 与 ``app.encyclopedia._TAG_RE`` 同口径：kind:* 的取值必须是这种小写 token。
_KIND_TAG_RE = re.compile(r'^kind:[a-z0-9][a-z0-9_.-]*$')
_KIND_RE = re.compile(r'^[a-z0-9][a-z0-9_.-]*$')


class ContentNotDeliverable(AssertionError):
    """内容文件不满足“可交付”的最低要求（缺失 / 坏 JSON / 空 elements）。

    故意用 ``AssertionError``：它是**测试失败**，不是跳过。
    """


def load_deliverable(path, label=None):
    """严格读取一份交付文档；不满足最低要求就抛 ``ContentNotDeliverable``。

    比引擎的校验更早失败，并把理由说清楚（缺哪个文件 / 哪一行坏 / 为什么是空的）。
    """
    path = Path(path)
    label = label or str(path)
    if not path.is_file():
        raise ContentNotDeliverable('%s 不存在：正式交付不允许缺文件' % label)
    try:
        text = path.read_text(encoding='utf-8-sig')
    except (OSError, UnicodeDecodeError) as error:
        raise ContentNotDeliverable('%s 读不出来：%s' % (label, error)) from error
    try:
        document = json.loads(text)
    except ValueError as error:
        raise ContentNotDeliverable('%s JSON 不可解析（半份文件）：%s' % (label, error)) from error
    if not isinstance(document, dict):
        raise ContentNotDeliverable('%s 顶层不是 JSON 对象' % label)
    elements = document.get('elements')
    if not isinstance(elements, list) or not elements:
        raise ContentNotDeliverable('%s 的 elements 为空或不是数组：空文档不算交付' % label)
    if not isinstance(document.get('sources'), list) or not document['sources']:
        raise ContentNotDeliverable('%s 没有任何 sources：无来源条目不可入库' % label)
    return document


def built_document(relative):
    """与 tools.encyclopedia_build.build 同口径：读源文件，再叠加 game 旁挂与主标签旁挂。"""
    document = load_deliverable(ROOT / relative, relative)
    return catalog_overlay.overlay(game_fields.overlay(document))


def tags_of(element, legacy=False):
    """原 ``tags`` + 由 ``category`` / ``genres`` 派生的标签（与引擎同口径）。

    旧 schema（元素靠 ``category`` 识别）下原 ``tags`` 不入库，只追加
    ``category:X`` / ``genre:Y``——这是既有引擎行为，本测试如实跟着走。
    """
    tags = [] if legacy else list(element.get('tags') or [])
    # 主标签与证据等级由字段派生（旧 schema 也派生），见 app/encyclopedia._prepare_element。
    if element.get('primary') is not None:
        tags.append('primary:' + element['primary'])
    if element.get('evidence_grade') is not None:
        tags.append('evidence:' + element['evidence_grade'])
    # 科技 / 魔法档位同样由字段派生（tech_tier / magic_tier，null 不出标签）。
    if element.get('tech_tier') is not None:
        tags.append('tech:' + element['tech_tier'])
    if element.get('magic_tier') is not None:
        tags.append('magic:' + element['magic_tier'])
    category = element.get('category')
    if category is not None:
        tags.append('category:' + category)
    for genre in element.get('genres') or []:
        tags.append('genre:' + genre)
    out = []
    for tag in tags:
        if tag not in out:
            out.append(tag)
    return out


def kind_tags(element):
    return [tag for tag in (element.get('tags') or []) if tag.startswith('kind:')]


def tradition_tags(element):
    return [tag for tag in tags_of(element) if tag.startswith('tradition:')]


def schema_is_legacy(document):
    """与 ``enc.detect_adapter`` 同口径：全带 tags → 新 schema，否则旧 schema。"""
    elements = [item for item in document.get('elements') or [] if isinstance(item, dict)]
    return not all('tags' in item for item in elements)


def expected_namespace(document, relative):
    return document.get('group') or Path(relative).stem


# --------------------------------------------------------------- 名单与兼容
class FantasyBiologyManifestCase(unittest.TestCase):
    """名单层：显式、独立、默认不入库、旧调用不受影响。"""

    def test_manifest_is_explicit_three_files(self):
        self.assertEqual(tuple(build.FANTASY_BIOLOGY_GROUPS), EXPECTED_FILES)
        self.assertEqual(len(set(build.FANTASY_BIOLOGY_GROUPS)), 3)
        for relative in build.FANTASY_BIOLOGY_GROUPS:
            self.assertNotIn('*', relative, '名单不能是通配，必须逐组显式登记')
            self.assertTrue(relative.endswith('.json'), relative)
            self.assertTrue(relative.startswith('docs/element-catalog/'), relative)

    def test_new_group_is_not_pulled_in_by_any_old_flag(self):
        for relative in EXPECTED_FILES:
            self.assertNotIn(relative, build.GROUPS, '奇幻生物不能默认进库')
            self.assertNotIn(relative, build.TRAIT_GROUPS)
            self.assertNotIn(relative, build.CUISINE_GROUPS)
            self.assertNotIn(relative, build.CULTURE_GROUPS)
            self.assertNotIn(relative, build.ATTRIBUTE_GROUPS)
            for groups in (build.groups_for(), build.groups_for(True),
                           build.groups_for(True, True, True),
                           build.groups_for(False, False, False, True)):
                self.assertNotIn(relative, groups, '未传 --with-fantasy-biology 就不能带这三组')

    def test_default_and_legacy_callers_are_unchanged(self):
        """新参数在末尾且默认 False：旧调用（含位置传参）含义一字不变。"""
        self.assertEqual(build.groups_for(), build.GROUPS)
        self.assertEqual(len(build.groups_for()), 14)
        self.assertEqual(build.groups_for(False), build.GROUPS)
        self.assertEqual(build.groups_for(True), build.LATEST_GROUPS)
        self.assertEqual(build.LATEST_GROUPS, build.GROUPS + build.TRAIT_GROUPS)
        self.assertEqual(build.groups_for(False, True), build.GROUPS + build.CUISINE_GROUPS)
        self.assertEqual(build.groups_for(True, True),
                         build.GROUPS + build.TRAIT_GROUPS + build.CUISINE_GROUPS)
        self.assertEqual(build.groups_for(True, True, True),
                         build.LATEST_GROUPS + build.CUISINE_GROUPS + build.ATTRIBUTE_GROUPS)
        self.assertEqual(build.groups_for(with_culture=True),
                         build.GROUPS + build.CULTURE_GROUPS)

    def test_new_groups_are_appended_last_and_can_combine(self):
        only = build.groups_for(with_fantasy_biology=True)
        self.assertEqual(only, build.GROUPS + build.FANTASY_BIOLOGY_GROUPS)
        everything = build.groups_for(True, True, True, True, True)
        self.assertEqual(everything,
                         build.GROUPS + build.TRAIT_GROUPS + build.CUISINE_GROUPS
                         + build.ATTRIBUTE_GROUPS + build.CULTURE_GROUPS
                         + build.FANTASY_BIOLOGY_GROUPS)
        for groups in (only, everything):
            self.assertEqual(len(set(groups)), len(groups), '名单里有重复项')

    def test_parser_exposes_the_flag_and_keeps_old_defaults(self):
        parser = build.build_parser()
        self.assertFalse(parser.parse_args([]).with_fantasy_biology)
        args = parser.parse_args(['--with-fantasy-biology'])
        self.assertTrue(args.with_fantasy_biology)
        for flag in ('with_traits', 'with_cuisine', 'with_culture', 'with_attributes'):
            self.assertFalse(getattr(args, flag), flag)
        combined = parser.parse_args(['--with-traits', '--with-fantasy-biology'])
        self.assertTrue(combined.with_traits and combined.with_fantasy_biology)
        self.assertEqual(build.groups_for(False, False, False, False, True),
                         build.GROUPS + build.FANTASY_BIOLOGY_GROUPS)

    def test_cluster_index_stays_excluded(self):
        for relative in EXPECTED_FILES:
            self.assertNotIn(relative, build.EXCLUDED, '三份文件是元素文档，不是被排除的聚类索引')
        self.assertIn('docs/element-catalog/shared-themes.json', build.EXCLUDED)


# ------------------------------------------ 正式交付：缺损必须失败（不是跳过）
class DeliverableGuardCase(unittest.TestCase):
    """把“缺损即失败”这条约定本身钉在测试里。

    正式交付不允许静默：缺文件、JSON 坏成半份、``elements`` 为空，
    在读取阶段就抛 ``ContentNotDeliverable``（AssertionError），测试失败。
    """

    def test_missing_file_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / 'fantasy-races.json'
            with self.assertRaises(ContentNotDeliverable):
                load_deliverable(missing)

    def test_broken_json_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'eastern-biology.json'
            path.write_text('{"group": "eastern-biology", "elements": [', encoding='utf-8')
            with self.assertRaises(ContentNotDeliverable):
                load_deliverable(path)

    def test_empty_elements_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'western-biology.json'
            path.write_text(json.dumps({'group': 'western-biology', 'sources': [],
                                        'elements': []}, ensure_ascii=False), encoding='utf-8')
            with self.assertRaises(ContentNotDeliverable):
                load_deliverable(path)

    def test_no_sources_fails(self):
        """无来源的“元素”不可入库（引擎会整批拒绝），这里更早拒绝。"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'fantasy-races.json'
            path.write_text(json.dumps({'group': 'fantasy-races', 'sources': [], 'elements': [
                {'id': 'x', 'name': 'x', 'tags': ['kind:race'],
                 'details': {section: 'y' for section in SECTIONS}, 'source_ids': []}]},
                ensure_ascii=False), encoding='utf-8')
            with self.assertRaises(ContentNotDeliverable):
                load_deliverable(path)

    def test_the_three_real_files_pass_the_guard(self):
        for relative in EXPECTED_FILES:
            with self.subTest(relative=relative):
                document = load_deliverable(ROOT / relative, relative)
                self.assertTrue(document['elements'], relative)


# ------------------------------------------------------------------- 内容与库
class FantasyBiologyLibraryCase(unittest.TestCase):
    """三组真导入的临时库；内容缺损时这里**失败**，不再 skip。"""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.db = Path(cls.tmp.name) / 'with-fantasy-biology.sqlite3'
        # 构库会在内存里叠加游戏字段与主标签旁挂（tools.game_fields / tools.catalog_overlay），
        # 所以这里比对的是叠加后的文档，与库里实际导入的内容同口径。
        cls.documents = {relative: built_document(relative) for relative in EXPECTED_FILES}
        cls.namespaces = {relative: expected_namespace(document, relative)
                          for relative, document in cls.documents.items()}
        code = build.build(cls.db, as_json=True,
                           groups=build.groups_for(with_fantasy_biology=True))
        if code != build.EXIT_OK:
            raise AssertionError('构库失败：退出码 %s' % code)
        cls.totals = enc.stats(cls.db)['totals']

    def document_for(self, relative):
        return self.documents[relative]

    def elements_of(self, relative):
        return self.document_for(relative)['elements']

    # ------------------------------------------------------------ 文档可交付性
    def test_documents_are_self_consistent(self):
        """group 与文件名对得上、三组命名空间互不相同。"""
        for relative, namespace in self.namespaces.items():
            self.assertEqual(namespace, Path(relative).stem, '%s 的 group 与文件名不一致' % relative)
        self.assertEqual(len(set(self.namespaces.values())), len(EXPECTED_FILES))

    def test_three_groups_imported_with_their_own_namespaces(self):
        landed = {group['namespace'] for group in enc.stats(self.db)['groups']}
        for relative, namespace in self.namespaces.items():
            self.assertIn(namespace, landed, relative)
            group = [row for row in enc.stats(self.db)['groups']
                     if row['namespace'] == namespace][0]
            document = self.document_for(relative)
            self.assertEqual(group['elements'], len(document['elements']), relative)
            self.assertEqual(group['sources'], len(document['sources']), relative)
            self.assertEqual(group['element_versions'], len(document['elements']), relative)
        self.assertEqual(self.totals['groups'],
                         len(build.groups_for(with_fantasy_biology=True)))
        self.assertEqual(self.totals['unresolved_relations'], 0,
                         '三组一起导入后不该留下未解析关联')
        # 这个库是按「14 组 + 三组新分区」一起构的，所以总数不等于三组之和；
        # 这里只核三组自己的条数，不把旧组也拉进来。
        for relative, namespace in self.namespaces.items():
            group = [row for row in enc.stats(self.db)['groups']
                     if row['namespace'] == namespace][0]
            self.assertEqual(group['elements'], len(self.elements_of(relative)), relative)
        fantasy_total = sum(len(self.elements_of(relative)) for relative in EXPECTED_FILES)
        self.assertEqual(
            sum(group['elements'] for group in enc.stats(self.db)['groups']
                if group['namespace'] in self.namespaces.values()), fantasy_total)

    def test_entries_stay_candidates_with_seven_non_empty_sections(self):
        for relative, namespace in self.namespaces.items():
            legacy = schema_is_legacy(self.document_for(relative))
            wanted = LEGACY_SECTIONS if legacy else SECTIONS
            for raw in self.elements_of(relative):
                item = enc.get(self.db, raw['id'], namespace=namespace, version=1)
                self.assertEqual(item['payload'], raw, '%s/%s' % (namespace, raw['id']))
                self.assertEqual(item['review_status'], 'needs_review', raw['id'])
                self.assertEqual(item['detail_status'], 'needs_detail', raw['id'])
                self.assertEqual(sorted(item['details']), sorted(wanted), raw['id'])
                for section in wanted:
                    self.assertTrue(item['details'][section].strip(),
                                    '%s/%s 的 details.%s 是空的' % (relative, raw['id'], section))

    # --------------------------------------------------- 内容最低约束（主审口径）
    def test_every_element_has_exactly_one_well_formed_kind_tag(self):
        """每条只能有一个 ``kind:*``，且取值是合法 token（不写死全集，容纳 spirit 等）。"""
        for relative in EXPECTED_FILES:
            for element in self.elements_of(relative):
                kinds = kind_tags(element)
                self.assertEqual(len(kinds), 1,
                                 '%s/%s 的 kind:* 标签数为 %d（应恰为 1）：%r'
                                 % (relative, element['id'], len(kinds), kinds))
                self.assertRegex(kinds[0], _KIND_TAG_RE,
                                 '%s/%s 的 kind 标签格式不对：%r'
                                 % (relative, element['id'], kinds[0]))
                self.assertRegex(kinds[0].split(':', 1)[1], _KIND_RE,
                                 '%s/%s 的 kind 取值不合法' % (relative, element['id']))

    def test_race_group_is_entirely_kind_race(self):
        """种族组的每一条都必须是 ``kind:race``，不能混入动植物。"""
        races = self.elements_of(RACES_RELATIVE)
        self.assertTrue(races)
        for element in races:
            self.assertEqual(kind_tags(element), ['kind:race'], element['id'])
        found = enc.search(self.db, namespace=self.namespaces[RACES_RELATIVE],
                           tags_all=['kind:race'], limit=enc.MAX_PAGE_SIZE)
        self.assertEqual(found['total'], len(races))
        self.assertEqual({item['element_id'] for item in found['items']},
                         {element['id'] for element in races})

    def test_biology_groups_cover_fauna_and_flora_at_least_eight_each(self):
        """两份生物组：fauna 与 flora 各自都不低于下限（不是只剩名义上的分类）。"""
        for relative in (WESTERN_RELATIVE, EASTERN_RELATIVE):
            elements = self.elements_of(relative)
            counts = {}
            for kind in ('kind:fauna', 'kind:flora'):
                counts[kind] = sum(1 for element in elements if kind in kind_tags(element))
                self.assertGreaterEqual(counts[kind], MIN_BIOLOGY_PER_KIND,
                                        '%s 的 %s 只有 %d 条（下限 %d）'
                                        % (relative, kind, counts[kind], MIN_BIOLOGY_PER_KIND))
                page = enc.search(self.db, namespace=self.namespaces[relative],
                                  tags_all=[kind], limit=enc.MAX_PAGE_SIZE)
                self.assertEqual(page['total'], counts[kind], '%s 的 %s 检索条数不符' % (relative, kind))
            # 除 fauna / flora 之外的 kind（如 spirit）允许存在，但必须是合法 token 且可检索。
            others = {tag for element in elements for tag in kind_tags(element)
                      if tag not in ('kind:fauna', 'kind:flora')}
            for other in others:
                self.assertRegex(other, _KIND_TAG_RE, other)
                page = enc.search(self.db, namespace=self.namespaces[relative],
                                  tags_all=[other], limit=enc.MAX_PAGE_SIZE)
                self.assertGreater(page['total'], 0, other)

    def test_tradition_tags_are_accurate(self):
        """传统维度要标准：种族组按条目分东西，两份生物组各自单传统。"""
        races = self.elements_of(RACES_RELATIVE)
        seen = set()
        for element in races:
            traditions = tradition_tags(element)
            self.assertEqual(len(traditions), 1,
                             '%s/%s 的 tradition 标签应恰为 1：%r'
                             % (RACES_RELATIVE, element['id'], traditions))
            self.assertIn(traditions[0], ('tradition:eastern', 'tradition:western'), element['id'])
            seen.add(traditions[0])
        self.assertEqual(seen, {'tradition:eastern', 'tradition:western'},
                         '种族组应同时覆盖东方与西方两个传统')
        for relative, tradition in ((WESTERN_RELATIVE, 'tradition:western'),
                                    (EASTERN_RELATIVE, 'tradition:eastern')):
            for element in self.elements_of(relative):
                self.assertEqual(tradition_tags(element), [tradition],
                                 '%s/%s 的传统标签不是 %s' % (relative, element['id'], tradition))
            page = enc.search(self.db, namespace=self.namespaces[relative],
                              tags_all=[tradition], limit=enc.MAX_PAGE_SIZE)
            self.assertEqual(page['total'], len(self.elements_of(relative)), relative)

    def test_sourceless_entries_are_declared_as_design_templates(self):
        """确实无来源的条目可以有，但**必须自证**是设计归纳，不能默不作声。

        内容侧约定：纯原创的类型/生态模板不假装有出处。这条不把它们放宽成“随便”，
        而是把“无来源”变成可核验的声明：``source_ids`` 为空时，
        ``evidence_and_uncertainty`` 必须写明“来源：无”。
        """
        for relative in EXPECTED_FILES:
            for element in self.elements_of(relative):
                if element.get('source_ids'):
                    continue
                self.assertIn('来源：无', element['details']['evidence_and_uncertainty'],
                              '%s/%s 没有来源，却没有在 evidence_and_uncertainty 里声明'
                              % (relative, element['id']))
                self.assertEqual(element['review_status'], 'needs_review', element['id'])
        # 无来源条目在库里必须真的没有任何 element_sources 行（不凭空造证据）。
        conn = enc.open_readonly(self.db)
        try:
            for relative, namespace in self.namespaces.items():
                for element in self.elements_of(relative):
                    rows = conn.execute(
                        'SELECT COUNT(*) FROM element_sources'
                        ' WHERE namespace=? AND element_id=? AND version=1',
                        (namespace, element['id'])).fetchone()[0]
                    self.assertEqual(rows, len(element.get('source_ids') or []),
                                     '%s/%s 的来源行数与 source_ids 不符'
                                     % (relative, element['id']))
        finally:
            conn.close()

    def test_all_referenced_sources_were_read_not_merely_listed(self):
        """每个被引用的来源都必须 ``access: read``（无来源条目见上一个用例）。

        这只是“采集侧声称读过正文”，**不等于事实已核实**；核实仍靠 review_status，
        而这些条目全都还是 ``needs_review``。
        """
        for relative in EXPECTED_FILES:
            access = {source['id']: source.get('access')
                      for source in self.document_for(relative)['sources']}
            for element in self.elements_of(relative):
                for source_id in element.get('source_ids') or []:
                    self.assertIn(source_id, access,
                                  '%s/%s 引用了文档里没有的来源 %s'
                                  % (relative, element['id'], source_id))
                    self.assertEqual(access[source_id], 'read',
                                     '%s/%s 引用的来源 %s 是 %r，不是 read'
                                     % (relative, element['id'], source_id, access[source_id]))
        # 库里也必须是这一口径（access 原值入库，不被改写）。
        for relative, namespace in self.namespaces.items():
            for raw in self.elements_of(relative):
                item = enc.get(self.db, raw['id'], namespace=namespace, version=1)
                for source in item['sources']:
                    self.assertEqual(source['access'], 'read', source['source_id'])

    # ------------------------------------------------------------- 标签与检索
    def test_tags_match_the_documented_derivation(self):
        for relative, namespace in self.namespaces.items():
            legacy = schema_is_legacy(self.document_for(relative))
            actual = {row['tag'] for row in enc.list_tags(self.db, namespace=namespace)['tags']}
            expected = set()
            for element in self.elements_of(relative):
                expected.update(tags_of(element, legacy))
            self.assertTrue(expected, '%s 里应当有标签' % relative)
            self.assertEqual(actual, expected, relative)

    def test_kind_and_tradition_tags_are_queryable(self):
        """``kind:*`` / ``tradition:*`` 都能按标签检索，结果不带进不相干的行。"""
        for tag in KIND_TAGS + ('tradition:eastern', 'tradition:western'):
            page = enc.search(self.db, tags_all=[tag], limit=enc.MAX_PAGE_SIZE)
            self.assertGreater(page['total'], 0, tag)
            for item in page['items']:
                self.assertIn(tag, item['tags'], item['element_id'])
        # 命名空间限定只会缩小，不会串组。
        for relative, namespace in self.namespaces.items():
            scoped = enc.search(self.db, tags_all=['kind:race'], namespace=namespace,
                                limit=enc.MAX_PAGE_SIZE)
            for item in scoped['items']:
                self.assertEqual(item['namespace'], namespace)

    def test_unknown_tag_returns_empty_not_error(self):
        page = enc.search(self.db, tags_all=['kind:no_such_kind'])
        self.assertEqual(page['total'], 0)
        self.assertEqual(page['items'], [])

    def test_search_by_name_and_alias(self):
        for relative, namespace in self.namespaces.items():
            sample = self.elements_of(relative)[0]
            hits = enc.search(self.db, text=sample['name'], namespace=namespace, limit=20)
            self.assertIn(sample['id'], [row['element_id'] for row in hits['items']], sample['id'])
            alias = (sample.get('aliases') or [None])[0]
            if alias and alias.strip():
                by_alias = enc.search(self.db, text=alias, namespace=namespace, limit=20)
                self.assertIn(sample['id'],
                              [row['element_id'] for row in by_alias['items']], sample['id'])

    # --------------------------------------------------- 来源引用与版本固定
    def test_source_references_are_complete_and_pinned(self):
        conn = enc.open_readonly(self.db)
        try:
            orphan_rows = conn.execute(
                'SELECT COUNT(*) FROM element_sources es'
                ' LEFT JOIN source_versions sv ON sv.namespace=es.source_namespace'
                '  AND sv.source_id=es.source_id AND sv.version=es.source_version'
                ' WHERE sv.source_id IS NULL').fetchone()[0]
            unpinned = conn.execute(
                'SELECT COUNT(*) FROM element_sources WHERE source_version IS NULL').fetchone()[0]
            for relative, namespace in self.namespaces.items():
                known = {source['id'] for source in self.document_for(relative)['sources']}
                for element in self.elements_of(relative):
                    for source_id in element['source_ids']:
                        self.assertIn(source_id, known,
                                      '%s/%s 引用了文档里不存在的来源 %s'
                                      % (relative, element['id'], source_id))
                        self.assertTrue(enc.pin_exists(conn, namespace, source_id, 1),
                                        '%s → %s 没有 v1 pin' % (element['id'], source_id))
        finally:
            conn.close()
        self.assertEqual(orphan_rows, 0, '有 element_sources 指向不存在的来源版本')
        self.assertEqual(unpinned, 0, '有 element_sources 没记住来源版本')

    def test_every_element_version_has_readable_sources(self):
        for relative, namespace in self.namespaces.items():
            for raw in self.elements_of(relative):
                item = enc.get(self.db, raw['id'], namespace=namespace, version=1)
                # 库里按 source_id 排序返回，不与 payload 里的书写顺序挂钩。
                self.assertEqual(sorted(source['source_id'] for source in item['sources']),
                                 sorted(raw['source_ids']), raw['id'])
                for source in item['sources']:
                    self.assertEqual(source['status'], 'batch')

    # ----------------------------------------------------------- 幂等与核对
    def test_reimport_is_idempotent(self):
        for relative, namespace in self.namespaces.items():
            sample = self.elements_of(relative)[0]['id']
            before = [row['version']
                      for row in enc.versions(self.db, sample, namespace=namespace)['versions']]
            again = enc.import_document(self.db, built_document(relative))
            self.assertTrue(again.as_dict()['idempotent'], '%s 重跑必须零写入' % relative)
            self.assertEqual(again.as_dict()['element_versions_written'], 0, relative)
            self.assertEqual(again.as_dict()['source_versions_written'], 0, relative)
            after = [row['version']
                     for row in enc.versions(self.db, sample, namespace=namespace)['versions']]
            self.assertEqual(before, after, relative)

    def test_check_passes_on_the_built_library(self):
        code = build.check(self.db, as_json=True,
                           groups=build.groups_for(with_fantasy_biology=True))
        self.assertEqual(code, build.EXIT_OK)

    def test_check_reports_the_missing_group(self):
        """库里没有这三组时 ``--check --with-fantasy-biology`` 必须报不一致（退 1）。"""
        other = Path(self.tmp.name) / 'without-fantasy.sqlite3'
        self.assertEqual(build.build(other, as_json=True), build.EXIT_OK)
        code = build.check(other, as_json=True,
                           groups=build.groups_for(with_fantasy_biology=True))
        self.assertEqual(code, build.EXIT_ERROR)


# --------------------------------------------------- 不依赖采集内容的自检
class ImportPathSelfCheckCase(unittest.TestCase):
    """用合成文档跑一遍「三组 → 导入 → 标签检索 → 幂等」链路。

    内容文件变动（改 kind 取值、增补条目）时，上面的真内容断言可能随之调整；
    这个类把**接入代码本身**的能力单独钉死，保证出问题时能分清是
    「接入代码坏了」还是「内容变了」。合成文档只活在临时目录里，不写 docs/。
    """

    @staticmethod
    def _document(group, prefix):
        def element(ident, kind, tradition):
            return {
                'id': '%s_%s' % (prefix, ident),
                'name': '%s %s' % (prefix, ident),
                'summary': '合成条目 %s' % ident,
                'tags': [kind, 'tradition:' + tradition],
                'details': {section: '合成内容 %s' % section for section in SECTIONS},
                'source_ids': ['%s_src_%s' % (prefix, ident)],
                'review_status': 'needs_review',
                'detail_status': 'needs_detail',
            }
        return {
            'schema_version': 1,
            'status': 'candidate',
            'group': group,
            'sources': [{'id': '%s_src_%s' % (prefix, ident), 'title': '合成来源 %s' % ident,
                         'access': 'read', 'supports': '合成自检用'}
                        for ident in ('a', 'b')],
            'elements': [element('a', 'kind:race', 'eastern'),
                         element('b', 'kind:flora', 'western')],
        }

    def test_three_group_import_tag_query_and_idempotency(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / 'synthetic.sqlite3'
            paths = []
            for relative, group, prefix in (
                    (RACES_RELATIVE, 'fantasy-races', 'synthetic_race'),
                    (WESTERN_RELATIVE, 'western-biology', 'synthetic_west'),
                    (EASTERN_RELATIVE, 'eastern-biology', 'synthetic_east')):
                path = root / (Path(relative).stem + '.json')
                path.write_text(json.dumps(self._document(group, prefix), ensure_ascii=False),
                                encoding='utf-8')
                paths.append((path, group))
            for path, group in paths:
                result = enc.import_file(db, path)
                self.assertEqual(result.namespace, group)
                self.assertEqual(result.element_versions, 2, group)
                self.assertEqual(result.adapter, enc.ADAPTER_HUMAN, group)
            totals = enc.stats(db)['totals']
            self.assertEqual(totals['groups'], len(build.FANTASY_BIOLOGY_GROUPS))
            self.assertEqual(totals['elements'], 6)
            self.assertEqual(totals['unresolved_relations'], 0)
            for tag in ('kind:race', 'kind:flora'):
                self.assertEqual(enc.search(db, tags_all=[tag], limit=enc.MAX_PAGE_SIZE)['total'], 3,
                                 tag)
            for namespace in ('fantasy-races', 'western-biology', 'eastern-biology'):
                self.assertEqual(
                    enc.search(db, tags_all=['kind:race'], namespace=namespace)['total'], 1, namespace)
                self.assertEqual(
                    enc.search(db, tags_all=['tradition:eastern'], namespace=namespace)['total'], 1,
                    namespace)
            item = enc.get(db, 'synthetic_race_a', namespace='fantasy-races')
            self.assertEqual(item['review_status'], 'needs_review')
            self.assertEqual(item['detail_status'], 'needs_detail')
            self.assertEqual(item['tags'], ['kind:race', 'tradition:eastern'])
            again = enc.import_file(db, paths[0][0])
            self.assertTrue(again.as_dict()['idempotent'])
            self.assertEqual(again.as_dict()['element_versions_written'], 0)
            self.assertEqual(enc.stats(db)['totals'], totals)


if __name__ == '__main__':
    unittest.main()
