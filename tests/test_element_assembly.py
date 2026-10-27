# -*- coding: utf-8 -*-
"""元素装配：库访问策略、检索与版本固定、选择校验、typed 规则、上限与公开投影。

测试全部跑在临时目录：库是从采集 JSON 现场导入的小库（只读源文件），旅程库是
``Store`` 的临时文件。``StoryPackage/玄陆``、``data/`` 与正式百科库都不碰。
"""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from app import element_assembly as ea
from app import encyclopedia as enc
from app.service import Service
from app.storage import Store

ROOT = Path(__file__).resolve().parents[1]
GROUPS = (
    'docs/human-encyclopedia/staples.json',
    'docs/human-encyclopedia/materials.json',
    'docs/element-catalog/western.json',
)
WHEAT = ('staples', 'staples_wheat')
STEEL = ('materials', 'materials_steel')
DRAGON = ('western', 'western_dragon')


def digest_of(relative):
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


class AssemblyCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shared = tempfile.TemporaryDirectory()
        cls.library_path = Path(cls.shared.name) / 'library.sqlite3'
        for relative in GROUPS:
            enc.import_file(cls.library_path, ROOT / relative)
        cls.source_digests = {relative: digest_of(relative) for relative in GROUPS}

    @classmethod
    def tearDownClass(cls):
        after = {relative: digest_of(relative) for relative in GROUPS}
        assert after == cls.source_digests, '采集 JSON 被改写了'
        cls.shared.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.svc = Service(Store(self.dir / 'state.sqlite3'), ROOT)
        self.svc.provider.configure({'offline': True})
        self.svc.elements.configure(self.library_path, allowed_roots=[self.shared.name])
        package = self.svc.runtime.package()
        self.place = package['story']['locations'][0]['id']
        self.characters = [c['id'] for c in package['characters']['characters']]

    def tearDown(self):
        self.tmp.cleanup()

    # ------------------------------------------------------------------ 夹具
    def selection(self, ref, **overrides):
        namespace, element_id = ref
        data = {'namespace': namespace, 'element_id': element_id, 'version': 1,
                'state': 'existing', 'acknowledge_candidate': True,
                'disclosure': {'public_description': '作者写的公开说明。',
                               'location_id': self.place, 'known_by': ['player']}}
        for key, value in overrides.items():
            if key == 'disclosure':
                data['disclosure'] = {**data['disclosure'], **value}
            else:
                data[key] = value
        return data

    def build(self, entries, rules=None):
        return self.svc.elements.build_manifest(entries, rules)

    def commit_draft(self, draft, story_revision=None):
        return self.svc.elements.commit(
            draft['id'], expected_draft_revision=draft['revision'],
            expected_story_revision=story_revision or self.svc.runtime.package()['id'])

    def story_with(self, manifest):
        return {'mechanics': {'element_manifest': manifest},
                'locations': [{'id': self.place, 'name': '测试地点', 'neighbors': []}]}


# --------------------------------------------------------------------- 库访问
class LibraryAccessTests(AssemblyCase):
    def test_missing_library_only_reports_and_never_creates(self):
        target = self.dir / 'not-built.sqlite3'
        self.svc.elements.configure(target, allowed_roots=[self.tmp.name])
        status = self.svc.elements.status()
        self.assertFalse(status['exists'])
        self.assertIn('tools.encyclopedia_build', status['error'])
        self.assertNotIn(str(self.dir), json.dumps(status, ensure_ascii=False))
        with self.assertRaises(ea.LibraryUnavailable):
            self.svc.elements.search(text='小麦')
        # 页面/接口读不存在的库时绝不顺手建一个空库。
        self.assertFalse(target.exists())

    def test_library_outside_allowed_roots_is_refused(self):
        self.svc.elements.configure(self.library_path)  # 没有 allowed_roots
        with self.assertRaises(ea.LibraryUnavailable) as caught:
            self.svc.elements.search(text='小麦')
        self.assertIn('允许的目录', str(caught.exception))
        self.assertNotIn(self.shared.name, str(caught.exception))

    def test_status_reports_counts_and_whitelist(self):
        status = self.svc.elements.status()
        self.assertTrue(status['exists'] and status['readable'])
        self.assertEqual(status['schema_version'], enc.SCHEMA_VERSION)
        self.assertGreaterEqual(status['totals']['elements'], 100)
        namespaces = {group['namespace'] for group in status['groups']}
        self.assertTrue({'staples', 'materials', 'western'} <= namespaces)
        self.assertIn('evidence_and_uncertainty', status['public_fields'])
        self.assertEqual([state['id'] for state in status['states']],
                         ['existing', 'potential'])
        self.assertTrue(status['read_only'])

    def test_source_json_is_never_rewritten(self):
        for relative in GROUPS:
            self.assertEqual(digest_of(relative), self.source_digests[relative])


# ----------------------------------------------------------------------- 检索
class SearchTests(AssemblyCase):
    def test_name_and_alias_search_with_paging(self):
        page = self.svc.elements.search(text='小麦', limit=2, offset=0)
        self.assertGreaterEqual(page['total'], 1)
        self.assertLessEqual(page['returned'], 2)
        detail = self.svc.elements.get(*WHEAT)
        self.assertTrue(detail['aliases'], '小麦应当有别名')
        by_alias = self.svc.elements.search(text=detail['aliases'][0], limit=20)
        self.assertIn('staples_wheat', [item['element_id'] for item in by_alias['items']])
        second = self.svc.elements.search(text='小麦', limit=2, offset=2)
        self.assertEqual(second['offset'], 2)
        self.assertEqual(page['has_more'], page['total'] > page['returned'])

    def test_tag_filters(self):
        page = self.svc.elements.search(tags_any=['cereal'], limit=50)
        self.assertGreaterEqual(page['total'], 1)
        self.assertTrue(all('cereal' in item['tags'] for item in page['items']))
        both = self.svc.elements.search(tags_all=['cereal', 'food'], limit=50)
        self.assertLessEqual(both['total'], page['total'])
        for item in both['items']:
            self.assertIn('cereal', item['tags'])
            self.assertIn('food', item['tags'])

    def test_pinned_version_keeps_its_own_evidence(self):
        detail = self.svc.elements.get(*WHEAT, version=1)
        self.assertEqual(detail['version'], 1)
        self.assertTrue(detail['is_current'])
        self.assertEqual(detail['review_status'], 'needs_review')
        self.assertEqual(detail['detail_status'], 'needs_detail')
        self.assertTrue(detail['sources'])
        for source in detail['sources']:
            self.assertGreaterEqual(source['source_version'], 1)
            self.assertEqual(source['payload_hash'], enc.payload_hash(source['payload']))
            self.assertIn('title', source['payload'])
        with self.assertRaisesRegex(ea.AssemblyError, '没有版本'):
            self.svc.elements.get(*WHEAT, version=99)


# ----------------------------------------------------------------- 选择结构
class SelectionShapeTests(AssemblyCase):
    def test_candidate_must_be_confirmed_explicitly(self):
        with self.assertRaisesRegex(ea.AssemblyError, '显式确认'):
            self.build([self.selection(WHEAT, acknowledge_candidate=False)])

    def test_unknown_selection_field_is_rejected(self):
        entry = self.selection(WHEAT)
        entry['payload'] = {'id': 'forged'}  # 浏览器伪造的 payload 不被接受
        with self.assertRaisesRegex(ea.AssemblyError, '未知字段'):
            self.build([entry])

    def test_strict_types(self):
        for version in (True, False, '1', 1.0, 0, -1):
            with self.subTest(version=version):
                with self.assertRaises(ea.AssemblyError):
                    self.build([self.selection(WHEAT, version=version)])
        with self.assertRaises(ea.AssemblyError):
            self.build([self.selection(WHEAT, state='existing_or_maybe')])
        with self.assertRaisesRegex(ea.AssemblyError, 'true/false'):
            self.build([self.selection(WHEAT, acknowledge_candidate=1)])
        with self.assertRaises(ea.AssemblyError):
            self.build([self.selection(('staples', 'Staples_Wheat'))])

    def test_public_fields_are_an_explicit_whitelist(self):
        with self.assertRaisesRegex(ea.AssemblyError, '白名单'):
            self.build([self.selection(WHEAT, disclosure={'public_fields': ['secret_note']})])
        # 名字里带 secret 的字段也不会因为名字被猜中而放行，反之白名单字段可以公开。
        manifest, _ = self.build([self.selection(WHEAT, disclosure={'public_fields': ['summary']})])
        disclosure = manifest['elements'][0]['disclosure']
        self.assertEqual(disclosure['public_fields'], ['summary'])
        self.assertIn('summary', disclosure['public_text'])

    def test_reveal_potential_only_for_potential(self):
        with self.assertRaisesRegex(ea.AssemblyError, 'reveal_potential'):
            self.build([self.selection(WHEAT, disclosure={'reveal_potential': True})])

    def test_known_by_is_validated(self):
        with self.assertRaisesRegex(ea.AssemblyError, '无效受众'):
            self.build([self.selection(WHEAT, disclosure={'known_by': ['Player Name']})])

    def test_missing_version_and_duplicates(self):
        with self.assertRaisesRegex(ea.AssemblyError, '没有版本'):
            self.build([self.selection(WHEAT, version=7)])
        with self.assertRaisesRegex(ea.AssemblyError, '重复选择'):
            self.build([self.selection(WHEAT), self.selection(WHEAT)])

    def test_public_text_too_long_is_refused_not_truncated(self):
        with self.assertRaisesRegex(ea.AssemblyError, '不自动截断|超过'):
            self.build([self.selection(WHEAT, disclosure={
                'public_fields': ['definition'],
                'public_description': '说' * (ea.MAX_PUBLIC_DESCRIPTION + 1)})])


# ------------------------------------------------------------------- typed 规则
class RuleTests(AssemblyCase):
    def test_requires_closure_is_accepted(self):
        manifest, warnings = self.build(
            [self.selection(WHEAT), self.selection(STEEL)],
            [{'kind': 'requires', 'from': 'staples/staples_wheat',
              'to': 'materials/materials_steel', 'note': '设计依赖'}])
        self.assertEqual(manifest['rules']['items'][0]['kind'], 'requires')
        self.assertIsInstance(warnings, list)

    def test_requires_with_missing_end_is_refused(self):
        with self.assertRaisesRegex(ea.AssemblyError, '缺引用'):
            self.build([self.selection(WHEAT)],
                       [{'kind': 'requires', 'from': 'staples/staples_wheat',
                         'to': 'materials/materials_steel'}])

    def test_dependency_cycle_is_refused_with_a_path(self):
        with self.assertRaisesRegex(ea.AssemblyError, '环'):
            self.build([self.selection(WHEAT), self.selection(STEEL)],
                       [{'kind': 'requires', 'from': 'staples/staples_wheat',
                         'to': 'materials/materials_steel'},
                        {'kind': 'requires', 'from': 'materials/materials_steel',
                         'to': 'staples/staples_wheat'}])

    def test_both_sides_selected_conflict_is_refused(self):
        with self.assertRaisesRegex(ea.AssemblyError, '互斥'):
            self.build([self.selection(WHEAT), self.selection(STEEL)],
                       [{'kind': 'conflicts', 'from': 'staples/staples_wheat',
                         'to': 'materials/materials_steel'}])

    def test_guard_conflict_against_an_unselected_ref_warns(self):
        manifest, warnings = self.build(
            [self.selection(WHEAT)],
            [{'kind': 'conflicts', 'from': 'staples/staples_wheat',
              'to': 'steam-horror/steam_high_pressure_boiler'}])
        self.assertEqual(len(manifest['rules']['items']), 1)
        self.assertTrue(any('守卫' in text for text in warnings))

    def test_conflict_between_two_unselected_refs_is_refused(self):
        with self.assertRaisesRegex(ea.AssemblyError, '都不在清单里'):
            self.build([self.selection(WHEAT)],
                       [{'kind': 'conflicts', 'from': 'materials/materials_steel',
                         'to': 'western/western_dragon'}])

    def test_rule_version_must_match_the_pinned_version(self):
        with self.assertRaisesRegex(ea.AssemblyError, '版本必须一致'):
            self.build([self.selection(WHEAT), self.selection(STEEL)],
                       [{'kind': 'requires', 'from': 'staples/staples_wheat',
                         'to': 'materials/materials_steel', 'to_version': 2}])

    def test_duplicate_and_malformed_rules(self):
        rule = {'kind': 'requires', 'from': 'staples/staples_wheat',
                'to': 'materials/materials_steel'}
        with self.assertRaisesRegex(ea.AssemblyError, '重复规则'):
            self.build([self.selection(WHEAT), self.selection(STEEL)], [rule, dict(rule)])
        with self.assertRaisesRegex(ea.AssemblyError, 'namespace/element_id'):
            self.build([self.selection(WHEAT)],
                       [{'kind': 'requires', 'from': 'staples_wheat', 'to': 'x/y'}])
        with self.assertRaisesRegex(ea.AssemblyError, 'requires（依赖）'):
            self.build([self.selection(WHEAT)],
                       [{'kind': 'maybe', 'from': 'staples/staples_wheat',
                         'to': 'staples/staples_wheat'}])

    def test_self_conflict_is_refused(self):
        with self.assertRaisesRegex(ea.AssemblyError, '不能与自己互斥'):
            self.build([self.selection(WHEAT)],
                       [{'kind': 'conflicts', 'from': 'staples/staples_wheat',
                         'to': 'staples/staples_wheat'}])


# ----------------------------------------------------------------------- 上限
class LimitTests(AssemblyCase):
    def test_too_many_elements(self):
        page = self.svc.elements.search(namespace='staples', limit=ea.MAX_ELEMENTS + 1)
        ids = [item['element_id'] for item in page['items']]
        self.assertGreater(len(ids), ea.MAX_ELEMENTS)
        entries = [self.selection(('staples', element_id)) for element_id in ids]
        with self.assertRaisesRegex(ea.AssemblyError, '最多'):
            self.svc.elements.save_draft(entries, [])
        with self.assertRaisesRegex(ea.AssemblyError, '最多'):
            self.build(entries)

    def _manifest(self):
        manifest, _ = self.build([self.selection(WHEAT)])
        return manifest

    def test_oversized_payload(self):
        manifest = self._manifest()
        payload = dict(manifest['elements'][0]['payload'])
        payload['padded'] = 'x' * (ea.MAX_ELEMENT_PAYLOAD_CHARS + 10)
        manifest['elements'][0]['payload'] = payload
        manifest['elements'][0]['payload_hash'] = ea.payload_digest(payload)
        # 库内取值本身没问题；越界是被清单校验拒绝的。
        with self.assertRaisesRegex(ea.AssemblyError, '上限'):
            ea.validate_package(self.story_with(manifest),
                                self.svc.runtime.package()['characters'])

    def test_tampered_payload_hash(self):
        manifest = self._manifest()
        manifest['elements'][0]['payload']['name'] = '被改过的名字'
        with self.assertRaisesRegex(ea.AssemblyError, '哈希不一致'):
            ea.validate_package(self.story_with(manifest),
                                self.svc.runtime.package()['characters'])

    def test_nan_and_infinity_are_refused(self):
        for value in (float('nan'), float('inf')):
            with self.subTest(value=value):
                manifest = self._manifest()
                manifest['elements'][0]['payload'] = {'bad': value}
                with self.assertRaisesRegex(ea.AssemblyError, '非法数值'):
                    ea.validate_package(self.story_with(manifest),
                                        self.svc.runtime.package()['characters'])

    def test_source_payload_tamper_is_refused(self):
        manifest = self._manifest()
        source = manifest['elements'][0]['sources'][0]
        source['payload'] = dict(source['payload'], title='被改过的标题')
        with self.assertRaisesRegex(ea.AssemblyError, '哈希不一致'):
            ea.validate_package(self.story_with(manifest),
                                self.svc.runtime.package()['characters'])

    def test_dangling_public_scope_is_refused(self):
        characters = self.svc.runtime.package()['characters']
        manifest = self._manifest()
        manifest['elements'][0]['disclosure']['location_id'] = 'no_such_place'
        with self.assertRaisesRegex(ea.AssemblyError, '不存在的地点'):
            ea.validate_package(self.story_with(manifest), characters)
        manifest = self._manifest()
        manifest['elements'][0]['disclosure']['known_by'] = ['nobody']
        with self.assertRaisesRegex(ea.AssemblyError, '受众不存在'):
            ea.validate_package(self.story_with(manifest), characters)

    def test_manifest_field_types(self):
        manifest = self._manifest()
        manifest['elements'][0]['version'] = True
        with self.assertRaises(ea.AssemblyError):
            ea.validate_package(self.story_with(manifest),
                                self.svc.runtime.package()['characters'])
        broken = self._manifest()
        broken['elements'][0]['disclosure']['public_fields'] = ['secret_note']
        with self.assertRaises(ea.AssemblyError):
            ea.validate_package(self.story_with(broken),
                                self.svc.runtime.package()['characters'])

    def test_old_package_without_manifest_is_untouched(self):
        story = json.loads(json.dumps(self.svc.runtime.package()['story']))
        story.get('mechanics', {}).pop(ea.MECHANICS_KEY, None)
        self.assertIsNone(ea.validate_package(story, self.svc.runtime.package()['characters']))
        self.assertIsNone(ea.package_manifest(story))


# --------------------------------------------------------------------- 草稿
class DraftTests(AssemblyCase):
    def test_cas_and_structures(self):
        draft = self.svc.elements.save_draft([self.selection(WHEAT)], [])
        self.assertEqual(draft['revision'], 0)
        self.assertEqual(draft['status'], 'draft')
        saved = self.svc.elements.save_draft([self.selection(WHEAT), self.selection(STEEL)], [],
                                            draft_id=draft['id'], expected_revision=0)
        self.assertEqual(saved['revision'], 1)
        with self.assertRaisesRegex(ea.AssemblyError, '已被其他操作更新'):
            self.svc.elements.save_draft([self.selection(WHEAT)], [],
                                         draft_id=draft['id'], expected_revision=0)

    def test_preview_does_not_write_a_package(self):
        before = len(self.svc.store.all('package'))
        draft = self.svc.elements.save_draft([self.selection(WHEAT)], [])
        result = self.svc.elements.preview(draft['elements'], draft['rules'])
        self.assertTrue(result['ok'])
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['elements'][0]['review_status'], 'needs_review')
        self.assertEqual(len(self.svc.store.all('package')), before)
        self.assertIsNone(self.svc.elements.manifest())


# --------------------------------------------------------------------- 投影
class ProjectionTests(AssemblyCase):
    def setUp(self):
        super().setUp()
        character = self.characters[1]
        entries = [
            self.selection(WHEAT, disclosure={
                'public_description': '当地以小麦为主粮，面粉是日常食物。',
                'public_fields': ['definition']}),
            self.selection(STEEL, state='potential', disclosure={
                'known_by': ['player'], 'public_description': '',
                'reveal_potential': False}),
            self.selection(DRAGON, disclosure={
                'known_by': [character], 'public_description': '',
                'public_fields': [], 'location_id': None}),
        ]
        # 巨龙只对某个角色公开，且带一个解锁标记。
        entries[2]['disclosure']['reveal_flag'] = 'heard_dragon'
        entries[2]['disclosure']['public_description'] = '山里据说有巨龙。'
        self.manifest = self.build(entries)[0]
        self.character = character

    def session(self, **overrides):
        data = {'location': self.place, 'flags': {}}
        data.update(overrides)
        return data

    def test_player_sees_only_disclosed_and_conditional_entries(self):
        rows = ea.public_view(self.manifest, 'player', self.session())
        self.assertEqual([row['ref'] for row in rows], ['staples/staples_wheat'])
        self.assertEqual(rows[0]['description'], '当地以小麦为主粮，面粉是日常食物。')
        self.assertEqual([fact['field'] for fact in rows[0]['facts']], ['definition'])
        # 潜在元素即使有描述，没有 reveal_potential 也不能被提到。
        self.assertNotIn('materials/materials_steel',
                         [row['ref'] for row in ea.public_view(self.manifest, 'player',
                                                               self.session(flags={}))])

    def test_potential_element_requires_explicit_reveal(self):
        manifest, _ = self.build([self.selection(
            STEEL, state='potential',
            disclosure={'public_description': '有人设想过更高炉温，但没有成品。',
                        'reveal_potential': True, 'known_by': ['player']})])
        rows = ea.public_view(manifest, 'player', self.session())
        self.assertEqual(rows[0]['state'], 'potential')
        self.assertIn('尚未出现', rows[0]['state_label'])
        hidden, _ = self.build([self.selection(
            STEEL, state='potential',
            disclosure={'public_description': '有人设想过更高炉温，但没有成品。',
                        'reveal_potential': False, 'known_by': ['player']})])
        self.assertEqual(ea.public_view(hidden, 'player', self.session()), [])

    def test_location_and_flag_gate_the_projection(self):
        elsewhere = next(item['id'] for item in self.svc.runtime.package()['story']['locations']
                         if item['id'] != self.place)
        self.assertEqual(ea.public_view(self.manifest, 'player',
                                         self.session(location=elsewhere)), [])
        # 角色视角：地点对、但没有 reveal_flag 时看不到带标记的条目。
        self.assertEqual(ea.public_view(self.manifest, self.character, self.session()), [])
        rows = ea.public_view(self.manifest, self.character,
                              self.session(flags={'heard_dragon': True}))
        self.assertEqual([row['ref'] for row in rows], ['western/western_dragon'])
        # 没有旅程就等于没有「现在在哪」，不猜也不透露。
        self.assertEqual(ea.public_view(self.manifest, 'player', None), [])

    def test_known_by_empty_discloses_nothing(self):
        manifest, warnings = self.build([self.selection(
            WHEAT, disclosure={'known_by': [], 'public_description': '谁都不该看到'})])
        self.assertEqual(ea.public_view(manifest, 'player', self.session()), [])
        self.assertTrue(any('known_by 为空' in text for text in warnings))

    def test_projection_never_touches_the_payload(self):
        rows = ea.public_view(self.manifest, 'player', self.session())
        blob = json.dumps(rows, ensure_ascii=False)
        payload = self.manifest['elements'][0]['payload']
        self.assertNotIn(payload['details']['evidence_and_uncertainty'], blob)
        self.assertNotIn('sources', blob)
        self.assertNotIn('review_status', blob)
        author = ea.author_view(self.manifest)
        self.assertIn('payload', author['elements'][0])
        self.assertEqual(author['elements'][0]['review_status'], 'needs_review')

    def test_context_projection_is_bounded_and_never_sliced(self):
        long_text = '这是一段包含限定的公开说明：没有炉温与耐火材料就不能生产，' * 6
        long_text = long_text[:ea.MAX_PUBLIC_DESCRIPTION]
        manifest, _ = self.build([self.selection(
            WHEAT, disclosure={'public_description': long_text, 'known_by': ['player']})])
        story = self.story_with(manifest)
        block = ea.context_elements(story, 'player', self.session())
        self.assertIsNotNone(block)
        self.assertIn('不等于已经发生', block['basis'])
        self.assertEqual(block['items'][0]['description'], long_text)
        self.assertLessEqual(len(json.dumps(block, ensure_ascii=False)),
                             ea.CONTEXT_MAX_CHARS + 200)
        self.assertLessEqual(len(block['items']), ea.CONTEXT_MAX_ENTRIES)
        # 没有清单时返回 None：老故事包的提示词一字不变。
        self.assertIsNone(ea.context_elements({'mechanics': {}}, 'player', self.session()))

    def test_context_entries_are_capped_whole(self):
        entries = []
        for item in self.svc.elements.search(namespace='staples', limit=10)['items']:
            entries.append(self.selection(('staples', item['element_id']), disclosure={
                'known_by': ['player'],
                'public_description': '说' * 399,
                'public_fields': ['definition']}))
        manifest, _ = self.build(entries)
        block = ea.context_elements(self.story_with(manifest), 'player', self.session())
        self.assertLessEqual(len(block['items']), ea.CONTEXT_MAX_ENTRIES)
        self.assertLessEqual(len(json.dumps(block, ensure_ascii=False)),
                             ea.CONTEXT_MAX_CHARS + 200)
        for item in block['items']:
            self.assertEqual(len(item['description']), 399)
            self.assertEqual(set(item['description']), {'说'})
