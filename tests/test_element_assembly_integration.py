# -*- coding: utf-8 -*-
"""元素装配接入面：提交/幂等/陈旧拒绝、旅程锁版、导出空库、生成器与城镇联动、真实 provider 输入。

每个用例都用临时库；库文件是本模块现场从采集 JSON 导入的小库（源文件只读）。
"""
import asyncio
import copy
import json
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import element_assembly as ea
from app import towns
from app.contracts import Turn
from app.service import Service
from app.storage import Store
from app.town_schema import DraftRequest as TownDraftRequest, TownInput
from app.towns_store import TownError
from app.web import create_app
from app.world_generator import GenerateWorldRequest
from app.world_pipeline import PipelineRequest, WorldPipeline

from tests.test_element_assembly import (AssemblyCase, DRAGON, ROOT, STEEL, WHEAT)


def private_commit(svc, story_title):
    """在故事包上做一次与元素无关的编辑，用来制造「基准已陈旧」。"""
    package = svc.runtime.package()
    story = copy.deepcopy(package['story'])
    story['title'] = story_title
    return svc.runtime.commit_package(story, copy.deepcopy(package['characters']), '别处编辑')


class CommitTests(AssemblyCase):
    def test_commit_creates_one_revision_and_repeats_idempotently(self):
        draft = self.svc.elements.save_draft([self.selection(WHEAT)], [])
        before = len(self.svc.store.all('package'))
        result = self.commit_draft(draft, self.svc.runtime.package()['id'])
        self.assertFalse(result['reused'])
        self.assertEqual(len(self.svc.store.all('package')), before + 1)
        manifest = self.svc.elements.manifest()
        self.assertEqual(manifest['count'], 1)
        self.assertEqual(manifest['elements'][0]['ref'], 'staples/staples_wheat')
        self.assertEqual(self.svc.elements.get_draft(draft['id'])['status'], 'committed')
        again = self.commit_draft(draft, self.svc.runtime.package()['id'])
        self.assertTrue(again['reused'])
        self.assertEqual(again['revision'], result['revision'])
        self.assertEqual(len(self.svc.store.all('package')), before + 1)

    def test_stale_base_revision_is_refused_with_zero_side_effects(self):
        stale = self.svc.runtime.package()['id']
        private_commit(self.svc, '原标题·别处编辑')
        draft = self.svc.elements.save_draft([self.selection(WHEAT)], [])
        before = len(self.svc.store.all('package'))
        # 草稿是在新版本上创建的，却拿着旧基准提交：不做隐式 rebase，零副作用。
        with self.assertRaisesRegex(ea.AssemblyError, '是基于'):
            self.commit_draft(draft, stale)
        self.assertEqual(len(self.svc.store.all('package')), before)
        self.assertIsNone(self.svc.elements.manifest())
        self.assertEqual(self.svc.elements.get_draft(draft['id'])['status'], 'draft')

    def test_failed_validation_writes_nothing(self):
        draft = self.svc.elements.save_draft([self.selection(WHEAT)], [])
        draft['elements'][0]['disclosure']['known_by'] = ['ghost']
        self.svc.store.put('element_draft', draft['id'], draft)
        before = len(self.svc.store.all('package'))
        with self.assertRaisesRegex(ea.AssemblyError, '受众不存在'):
            self.commit_draft(draft, self.svc.runtime.package()['id'])
        self.assertEqual(len(self.svc.store.all('package')), before)
        self.assertIsNone(self.svc.elements.manifest())
        self.assertEqual(self.svc.elements.get_draft(draft['id'])['status'], 'draft')

    def test_committed_draft_is_immutable(self):
        draft = self.svc.elements.save_draft([self.selection(WHEAT)], [])
        self.commit_draft(draft, self.svc.runtime.package()['id'])
        with self.assertRaisesRegex(ea.AssemblyError, '不能修改'):
            self.svc.elements.save_draft([self.selection(WHEAT)], [], draft_id=draft['id'],
                                         expected_revision=self.svc.elements.get_draft(
                                             draft['id'])['revision'])


class JourneyTests(AssemblyCase):
    def commit_wheat(self, disclosure=None):
        entries = [self.selection(WHEAT, disclosure=disclosure or {})]
        draft = self.svc.elements.save_draft(entries, [])
        return self.commit_draft(draft, self.svc.runtime.package()['id'])

    def test_old_journey_keeps_its_revision_and_never_sees_the_manifest(self):
        old = self.svc.runtime.new_session('旧旅程', 'protagonist')
        self.commit_wheat()
        reloaded = self.svc.store.session(old['id'])
        self.assertEqual(reloaded['revision'], old['revision'])
        context = self.svc.runtime.context(reloaded, 'player', '小麦', self.svc.preferences())
        self.assertNotIn('current_elements', context)
        fresh = self.svc.runtime.new_session('新旅程', 'protagonist')
        fresh = self.svc.store.session(fresh['id'])
        block = self.svc.runtime.context(fresh, 'player', '小麦',
                                         self.svc.preferences())['current_elements']
        self.assertEqual([item['name'] for item in block['items']], ['小麦'])

    def test_journey_survives_library_deletion_and_upgrade(self):
        copy_path = self.dir / 'library-copy.sqlite3'
        shutil.copyfile(self.library_path, copy_path)
        self.svc.elements.configure(copy_path, allowed_roots=[self.tmp.name])
        self.commit_wheat()
        session = self.svc.runtime.new_session('锁版', 'protagonist')
        before = self.svc.runtime.context(self.svc.store.session(session['id']), 'player',
                                          '小麦', self.svc.preferences())['current_elements']
        copy_path.unlink()
        after = self.svc.runtime.context(self.svc.store.session(session['id']), 'player',
                                         '小麦', self.svc.preferences())['current_elements']
        self.assertEqual(json.dumps(before, sort_keys=True, ensure_ascii=False),
                         json.dumps(after, sort_keys=True, ensure_ascii=False))
        # 库没了，运行期照样读；再想装配新清单则明确报不可用，而不是静默空清单。
        with self.assertRaises(ea.LibraryUnavailable):
            self.svc.elements.build_manifest([self.selection(WHEAT)])

    def test_export_imports_into_an_empty_database(self):
        self.commit_wheat({'public_description': '当地以小麦为主食。'})
        exported = copy.deepcopy(self.svc.runtime.package())
        empty = Service(Store(self.dir / 'imported.sqlite3'), ROOT)
        empty.runtime.commit_package(copy.deepcopy(exported['story']),
                                     copy.deepcopy(exported['characters']), '导入组合包')
        manifest = empty.elements.manifest()
        self.assertEqual(manifest['count'], 1)
        self.assertEqual(manifest['elements'][0]['sources'],
                          self.svc.elements.manifest()['elements'][0]['sources'])
        session = empty.runtime.new_session('导入后旅程', 'protagonist')
        block = empty.runtime.context(empty.store.session(session['id']), 'player', '小麦',
                                      empty.preferences())['current_elements']
        self.assertEqual([item['name'] for item in block['items']], ['小麦'])
        # 导入包里没有百科库也能读；装配端清空配置后仍然读得到（运行期不依赖库）。
        empty.elements.configure(self.dir / 'gone.sqlite3', allowed_roots=[self.tmp.name])
        self.assertFalse(empty.elements.status()['exists'])
        again = empty.runtime.context(empty.store.session(session['id']), 'player', '小麦',
                                      empty.preferences())['current_elements']
        self.assertEqual(again, block)


class ProviderPayloadTests(AssemblyCase):
    def build_context(self, query='小麦'):
        captured = {}

        async def fake(system, context, **kwargs):
            captured['context'] = context
            return '小麦磨成面粉。', {'prompt_tokens': 10}

        entries = [
            self.selection(WHEAT, disclosure={
                'public_description': '当地以小麦为主粮，面粉是日常食物。',
                'known_by': ['player']}),
            self.selection(STEEL, state='potential', disclosure={
                'known_by': ['player'], 'public_description': '尚无成品的技术设想。',
                'reveal_potential': False}),
            self.selection(DRAGON, disclosure={
                'known_by': [self.characters[1]], 'public_description': '山里有巨龙。',
                'location_id': None}),
        ]
        package = self.svc.runtime.package()
        draft = self.svc.elements.save_draft(entries, [])
        self.commit_draft(draft, package['id'])
        session = self.svc.runtime.new_session('叙事输入', 'protagonist')
        self.assertIsNotNone(self.svc.elements.manifest())
        self.svc.provider.configure({'offline': False})
        with patch.object(self.svc.provider, 'complete', fake):
            asyncio.run(self.svc.turn(session['id'], Turn(message=query)))
        return captured['context'], session['id']

    def test_real_provider_payload_only_carries_public_elements(self):
        context, _session = self.build_context()
        block = context['current_elements']
        self.assertEqual([item['name'] for item in block['items']], ['小麦'])
        self.assertIn('不等于已经发生', block['basis'])
        serialized = json.dumps(context, ensure_ascii=False)
        payload = self.svc.elements.manifest()['elements'][0]['payload']
        self.assertNotIn(payload['details']['evidence_and_uncertainty'], serialized)
        self.assertNotIn(payload['details']['definition'], serialized)
        self.assertNotIn('needs_review', serialized)
        self.assertNotIn('materials_steel', serialized)
        self.assertNotIn('western_dragon', serialized)
        self.assertNotIn('山里有巨龙', serialized)

    def test_character_viewpoint_uses_its_own_knowledge(self):
        _context, session_id = self.build_context()
        npc = self.svc.runtime.context(self.svc.store.session(session_id),
                                       self.characters[1], '巨龙', self.svc.preferences())
        items = (npc.get('current_elements') or {}).get('items', [])
        self.assertEqual([item['name'] for item in items], ['巨龙'])
        self.assertNotIn('小麦', [item['name'] for item in items])


class GeneratorTests(AssemblyCase):
    def commit_manifest(self):
        entries = [
            self.selection(WHEAT, disclosure={'public_description': '主食。'}),
            self.selection(STEEL, state='potential', disclosure={'known_by': []}),
        ]
        draft = self.svc.elements.save_draft(entries, [])
        return self.commit_draft(draft, self.svc.runtime.package()['id'])

    def test_generator_pins_and_keeps_the_manifest(self):
        self.commit_manifest()
        pin = self.svc.elements.manifest()
        draft = asyncio.run(self.svc.world_generator.generate(
            GenerateWorldRequest(kind='world', title='元素世界', instruction='生成可探索的世界',
                                 city_count=2)))
        self.assertIsNotNone(draft['element_manifest'])
        self.assertEqual(draft['element_manifest']['count'], pin['count'])
        saved = self.svc.world_generator.save(draft['id'])
        story = json.loads((self.svc.runtime.library / saved['folder'] / 'story.json')
                           .read_text(encoding='utf-8'))
        manifest = story['mechanics'][ea.MECHANICS_KEY]
        self.assertEqual(manifest['count'], 2)
        # 新世界的地点/角色 ID 不同：解析不了的公开范围被清空并记警告，绝不沿用非法 ID。
        self.assertIn('请作者重新指定', json.dumps(manifest['warnings'], ensure_ascii=False))
        self.assertTrue(manifest['warnings'])

    def test_generator_accepts_only_a_subset_of_the_locked_manifest(self):
        self.commit_manifest()
        draft = asyncio.run(self.svc.world_generator.generate(
            GenerateWorldRequest(kind='world', title='子集世界', instruction='只用一个元素',
                                 city_count=2, elements=['staples/staples_wheat'])))
        self.assertEqual(draft['element_manifest']['count'], 1)
        self.assertEqual(draft['element_manifest']['elements'][0]['ref'],
                         'staples/staples_wheat')
        with self.assertRaisesRegex(ea.AssemblyError, '不在当前故事包清单里'):
            asyncio.run(self.svc.world_generator.generate(
                GenerateWorldRequest(kind='world', title='越界世界', instruction='选库外元素',
                                     city_count=2, elements=['western/western_dragon'])))

    def test_generator_refuses_explicit_elements_without_a_manifest(self):
        self.assertIsNone(self.svc.elements.manifest())
        with self.assertRaisesRegex(ea.AssemblyError, '还没有元素清单'):
            asyncio.run(self.svc.world_generator.generate(
                GenerateWorldRequest(kind='world', title='没有清单', instruction='直接选元素',
                                     city_count=2, elements=['staples/staples_wheat'])))

    def test_pipeline_carries_the_manifest_through_all_stages(self):
        self.commit_manifest()
        runner = WorldPipeline(self.svc)
        document = runner.start(PipelineRequest(title='装配流水线', instruction='四阶段世界',
                                                regions=2))
        self.assertIsNotNone(document['element_manifest'])
        for _ in range(4):
            document = asyncio.run(runner.advance(document['id']))
        self.assertEqual(len(document['stages']), 4)
        saved = runner.save(document['id'])
        story = json.loads((self.svc.runtime.library / saved['folder'] / 'story.json')
                           .read_text(encoding='utf-8'))
        self.assertIn(ea.MECHANICS_KEY, story['mechanics'])
        self.assertEqual(story['mechanics'][ea.MECHANICS_KEY]['count'], 2)


class TownBindingTests(AssemblyCase):
    def preset(self, **bindings):
        entry = towns.preset_entry('wet_valley', 'town_elem_seed',
                                   story_revision=self.svc.runtime.package()['id']
                                   ).model_dump(mode='json')
        entry['bindings'] = bindings.get('bindings', [])
        return entry

    def create(self, entry):
        return self.svc.towns.create(TownDraftRequest(input=TownInput(**entry)))

    def commit_manifest(self):
        entries = [
            self.selection(WHEAT, disclosure={'known_by': []}),
            self.selection(STEEL, state='potential', disclosure={'known_by': []}),
        ]
        draft = self.svc.elements.save_draft(entries, [])
        self.commit_draft(draft, self.svc.runtime.package()['id'])

    def test_bindings_must_match_the_locked_ids_and_versions(self):
        self.commit_manifest()
        ok = self.create(self.preset(bindings=[
            {'id': 'staples_wheat', 'kind': 'element', 'version': '1',
             'summary': '本镇以小麦为主粮', 'state': 'existing'}]))
        self.assertEqual(ok['input']['bindings'][0]['id'], 'staples_wheat')
        with self.assertRaisesRegex(TownError, '不在当前故事包清单里'):
            self.create(self.preset(bindings=[
                {'id': 'western_western_dragon', 'kind': 'element', 'version': '1',
                 'summary': '库里有但没采纳'}]))
        with self.assertRaisesRegex(TownError, '版本与故事包清单不一致'):
            self.create(self.preset(bindings=[
                {'id': 'staples_wheat', 'kind': 'element', 'version': '2',
                 'summary': '版本不对'}]))
        with self.assertRaisesRegex(TownError, '状态与清单不一致'):
            self.create(self.preset(bindings=[
                {'id': 'materials_steel', 'kind': 'element', 'version': '1',
                 'summary': '把潜在当已启用', 'state': 'existing'}]))

    def test_potential_binding_is_recorded_but_never_enabled(self):
        self.commit_manifest()
        draft = self.create(self.preset(bindings=[
            {'id': 'materials_steel', 'kind': 'element', 'version': '1',
             'summary': '还在设想阶段', 'state': 'potential'}]))
        self.assertTrue(any('不视为已启用的技术' in text for text in draft['warnings']))
        self.assertEqual(draft['input']['bindings'][0]['state'], 'potential')

    def test_without_a_manifest_bindings_behave_as_before(self):
        self.assertIsNone(self.svc.elements.manifest())
        draft = self.create(self.preset(bindings=[
            {'id': 'el_irrigation_custom', 'kind': 'element', 'version': 'v1',
             'summary': '老行为：请求内自证'}]))
        self.assertEqual(draft['input']['bindings'][0]['id'], 'el_irrigation_custom')
        self.assertFalse(any('不视为已启用' in text for text in draft['warnings']))


class ApiTests(AssemblyCase):
    def client(self):
        app = create_app(self.dir / 'api.sqlite3')
        app.state.service.elements.configure(self.library_path,
                                            allowed_roots=[self.shared.name])
        return app, TestClient(app)

    def test_author_pages_require_the_token(self):
        app, client = self.client()
        with client:
            self.assertEqual(client.get('/api/inner/elements/library').status_code, 403)
            token = client.get('/api/bootstrap').json()['token']
            headers = {'X-TextileDream-Token': token}
            status = client.get('/api/inner/elements/library', headers=headers)
            self.assertEqual(status.status_code, 200, status.text)
            body = status.json()
            self.assertTrue(body['exists'])
            self.assertEqual(body['path'], 'library.sqlite3')
            self.assertNotIn(self.shared.name, status.text)
            # 任何查询参数都不能换库：路径只来自服务端配置。
            forced = client.get('/api/inner/elements/library?db=/etc/passwd&path=..%2F..%2Fetc',
                                headers=headers)
            self.assertEqual(forced.json()['path'], 'library.sqlite3')
            search = client.get('/api/inner/elements/search?text=小麦&limit=3',
                                headers=headers)
            self.assertEqual(search.status_code, 200, search.text)
            self.assertGreaterEqual(search.json()['total'], 1)

    def test_draft_preview_commit_and_manifest_endpoints(self):
        app, client = self.client()
        with client:
            token = client.get('/api/bootstrap').json()['token']
            headers = {'X-TextileDream-Token': token}
            package = client.get('/api/inner/package', headers=headers).json()
            place = package['story']['locations'][0]['id']
            created = client.post('/api/inner/elements/drafts', headers=headers, json={
                'elements': [{'namespace': 'staples', 'element_id': 'staples_wheat',
                              'version': 1, 'state': 'existing',
                              'acknowledge_candidate': True,
                              'disclosure': {'public_description': '当地主食。',
                                             'location_id': place,
                                             'known_by': ['player']}}],
                'rules': []})
            self.assertEqual(created.status_code, 200, created.text)
            draft = created.json()
            preview = client.post(f"/api/inner/elements/drafts/{draft['id']}/preview",
                                  headers=headers)
            self.assertEqual(preview.status_code, 200, preview.text)
            self.assertEqual(preview.json()['count'], 1)
            committed = client.post(f"/api/inner/elements/drafts/{draft['id']}/commit",
                                    headers=headers,
                                    json={'expected_story_revision': package['id'],
                                          'expected_draft_revision': draft['revision']})
            self.assertEqual(committed.status_code, 200, committed.text)
            self.assertFalse(committed.json()['reused'])
            manifest = client.get('/api/inner/elements/manifest', headers=headers).json()
            self.assertEqual(manifest['count'], 1)
            self.assertIn('payload', manifest['elements'][0])
            session = client.post('/api/sessions', headers=headers,
                                  json={'title': '接口旅程', 'mode': 'protagonist'}).json()
            public = client.get('/api/inner/elements/manifest?audience=player&session='
                                + session['id'], headers=headers).json()
            self.assertEqual([row['name'] for row in public['elements']], ['小麦'])
            self.assertNotIn('payload', json.dumps(public, ensure_ascii=False))
            no_session = client.get('/api/inner/elements/manifest?audience=player',
                                    headers=headers)
            self.assertEqual(no_session.status_code, 400)


class IsolationTests(unittest.TestCase):
    def test_runtime_never_imports_the_writable_library_api(self):
        source = (ROOT / 'app' / 'runtime.py').read_text(encoding='utf-8')
        self.assertNotIn('open_writable', source)
        self.assertNotIn('import_file', source)
        assembly = (ROOT / 'app' / 'element_assembly.py').read_text(encoding='utf-8')
        for forbidden in ('open_writable', 'import_file'):
            self.assertNotIn(forbidden, assembly)
        # 启动流程不碰百科库：入口不引用装配模块（装配只在作者显式操作时走库）。
        self.assertNotIn('element_assembly', (ROOT / 'app' / 'main.py').read_text(encoding='utf-8'))
        launch = ROOT / 'launch.py'
        if launch.exists():
            self.assertNotIn('element_assembly', launch.read_text(encoding='utf-8'))


class ConcurrencyTests(AssemblyCase):
    """并发、世界切换、省略基准、提交后源库删除重试、索引写失败的失败用例。"""

    def other_world(self):
        package = self.svc.runtime.package()
        story = copy.deepcopy(package['story'])
        characters = copy.deepcopy(package['characters'])
        story['id'] = 'world_other_1'
        characters['id'] = 'characters_other_1'
        story['character_package_id'] = characters['id']
        return self.svc.runtime.commit_package(story, characters, '另一个世界')

    def test_saving_a_draft_is_cas_inside_one_transaction(self):
        draft = self.svc.elements.save_draft([self.selection(WHEAT)], [])
        first = self.svc.elements.save_draft(
            [self.selection(WHEAT), self.selection(STEEL)], [],
            draft_id=draft['id'], expected_revision=0)
        # 第二个写入者拿着同一份旧 revision：事务内 CAS 拒绝，且不覆盖第一次的结果。
        with self.assertRaisesRegex(ea.AssemblyError, '已被其他操作更新'):
            self.svc.elements.save_draft([self.selection(DRAGON)], [],
                                         draft_id=draft['id'], expected_revision=0)
        stored = self.svc.elements.get_draft(draft['id'])
        self.assertEqual(stored['revision'], first['revision'])
        self.assertEqual([row['element_id'] for row in stored['elements']],
                         ['staples_wheat', 'materials_steel'])

    def test_draft_pins_its_world_and_refuses_another_world(self):
        draft = self.svc.elements.save_draft([self.selection(WHEAT)], [])
        self.assertEqual(draft['base_story_id'], self.svc.runtime.package()['story']['id'])
        self.other_world()
        before = len(self.svc.store.all('package'))
        with self.assertRaisesRegex(ea.AssemblyError, '不同|不跨世界'):
            self.commit_draft(draft)
        self.assertEqual(len(self.svc.store.all('package')), before)

    def test_commit_requires_both_revisions(self):
        draft = self.svc.elements.save_draft([self.selection(WHEAT)], [])
        current = self.svc.runtime.package()['id']
        with self.assertRaisesRegex(ea.AssemblyError, 'expected_draft_revision'):
            self.svc.elements.commit(draft['id'], expected_draft_revision=None,
                                     expected_story_revision=current)
        with self.assertRaisesRegex(ea.AssemblyError, 'expected_story_revision'):
            self.svc.elements.commit(draft['id'], expected_draft_revision=0,
                                     expected_story_revision=None)
        with self.assertRaisesRegex(ea.AssemblyError, '草稿已被其他操作更新'):
            self.svc.elements.commit(draft['id'], expected_draft_revision=9,
                                     expected_story_revision=current)
        self.assertIsNone(self.svc.elements.manifest())

    def test_retry_after_success_needs_no_library(self):
        copy_path = self.dir / 'lib-copy.sqlite3'
        shutil.copyfile(self.library_path, copy_path)
        self.svc.elements.configure(copy_path, allowed_roots=[self.tmp.name])
        draft = self.svc.elements.save_draft([self.selection(WHEAT)], [])
        first = self.commit_draft(draft)
        copy_path.unlink()
        self.assertFalse(self.svc.elements.status()['exists'])
        again = self.svc.elements.commit(
            draft['id'], expected_draft_revision=draft['revision'],
            expected_story_revision=self.svc.runtime.package()['id'])
        self.assertTrue(again['reused'])
        self.assertEqual(again['revision'], first['revision'])

    def test_committed_manifest_does_not_survive_a_later_manifest_change(self):
        draft = self.svc.elements.save_draft([self.selection(WHEAT)], [])
        self.commit_draft(draft)
        # 与元素无关的编辑不会动清单：世界仍然带着同一份快照，重试依旧是幂等的。
        private_commit(self.svc, '原标题·别处编辑')
        still = self.svc.elements.commit(
            draft['id'], expected_draft_revision=draft['revision'],
            expected_story_revision=self.svc.runtime.package()['id'])
        self.assertTrue(still['reused'])
        # 作者随后把清单换成另一份：旧草稿不能再声称「已提交」。
        other = self.svc.elements.save_draft([self.selection(STEEL)], [])
        self.commit_draft(other)
        with self.assertRaisesRegex(ea.AssemblyError, '凭据不一致|不一致'):
            self.svc.elements.commit(
                draft['id'], expected_draft_revision=draft['revision'],
                expected_story_revision=self.svc.runtime.package()['id'])

    def test_index_write_failure_is_not_a_failed_commit(self):
        draft = self.svc.elements.save_draft([self.selection(WHEAT)], [])
        with patch.object(ea.ElementAssembly, '_mark_committed', lambda *a, **k: False):
            result = self.commit_draft(draft)
        self.assertFalse(result['indexed'])
        self.assertIn('幂等补齐', result['note'])
        self.assertIsNotNone(self.svc.elements.manifest())  # 世界确实已经改变
        self.assertEqual(self.svc.elements.get_draft(draft['id'])['status'], 'committing')
        repair = self.svc.elements.commit(
            draft['id'], expected_draft_revision=draft['revision'],
            expected_story_revision=self.svc.runtime.package()['id'])
        self.assertTrue(repair['reused'])
        self.assertTrue(repair['indexed'])
        self.assertEqual(self.svc.elements.get_draft(draft['id'])['status'], 'committed')

    def test_rebind_keeps_payload_hashes_and_clears_public_scope(self):
        draft = self.svc.elements.save_draft(
            [self.selection(WHEAT, disclosure={'public_description': '主食。'}),
             self.selection(STEEL, state='potential', disclosure={'known_by': []})], [])
        self.commit_draft(draft)
        generated = asyncio.run(self.svc.world_generator.generate(
            GenerateWorldRequest(kind='world', title='重绑定世界', instruction='生成可探索世界',
                                 city_count=2)))
        saved = self.svc.world_generator.save(generated['id'])
        story = json.loads((self.svc.runtime.library / saved['folder'] / 'story.json')
                           .read_text(encoding='utf-8'))
        manifest = story['mechanics'][ea.MECHANICS_KEY]
        characters = json.loads(
            (self.svc.runtime.character_directory
             / (story['character_package_id'] + '.json')).read_text(encoding='utf-8'))
        # 清空 disclosure 之后整份清单仍然自洽（哈希、白名单、规则一起复验）。
        self.assertIsNotNone(ea.validate_package(story, characters))
        for element in manifest['elements']:
            self.assertEqual(element['payload_hash'], ea.payload_digest(element['payload']))
            self.assertEqual(element['disclosure']['public_fields'], [])
            self.assertEqual(element['disclosure']['public_text'], {})
            self.assertEqual(element['disclosure']['public_description'], '')
            self.assertEqual(element['disclosure']['known_by'], [])
            for source in element['sources']:
                self.assertEqual(source['payload_hash'],
                                 ea.payload_digest(source['payload']))
        anywhere = sorted(place['id'] for place in story['locations'])[0]
        self.assertEqual(ea.public_view(manifest, 'player',
                                        {'location': anywhere, 'flags': {}}), [])
        # 原世界的清单不动：payload 与来源仍是同一份快照。
        original = self.svc.elements.manifest()
        self.assertEqual(original['elements'][0]['payload_hash'],
                         manifest['elements'][0]['payload_hash'])


class SubsetDependencyTests(AssemblyCase):
    """生成子集不得删除已声明的硬依赖：闭包自动展开、冲突守卫保留、同时出现则拒绝。"""

    A = 'staples/staples_wheat'
    B = 'materials/materials_steel'
    C = 'western/western_dragon'
    CHAIN = [{'kind': 'requires', 'from': 'staples/staples_wheat',
              'to': 'materials/materials_steel'},
             {'kind': 'requires', 'from': 'materials/materials_steel',
              'to': 'western/western_dragon'}]

    def connect(self, rules):
        draft = self.svc.elements.save_draft(
            [self.selection(WHEAT), self.selection(STEEL),
             self.selection(DRAGON, disclosure={'known_by': []})], rules)
        self.commit_draft(draft)
        return self.svc.elements.manifest()

    def generated_story(self, draft_id):
        saved = self.svc.world_generator.save(draft_id)
        return json.loads((self.svc.runtime.library / saved['folder'] / 'story.json')
                          .read_text(encoding='utf-8'))

    def test_generator_expands_a_requires_chain(self):
        self.connect(self.CHAIN)
        draft = asyncio.run(self.svc.world_generator.generate(
            GenerateWorldRequest(kind='world', title='闭包世界', instruction='生成可探索世界',
                                 city_count=2, elements=[self.A])))
        manifest = draft['element_manifest']
        self.assertEqual([row['ref'] for row in manifest['elements']],
                         [self.A, self.B, self.C])
        self.assertEqual([rule['kind'] for rule in manifest['rules']['items']],
                         ['requires', 'requires'])
        self.assertEqual(manifest['requested_refs'], [self.A])
        self.assertTrue(any('自动加入' in text for text in draft['element_warnings']))
        kept = self.generated_story(draft['id'])['mechanics'][ea.MECHANICS_KEY]
        self.assertEqual([row['ref'] for row in kept['elements']], [self.A, self.B, self.C])
        self.assertEqual(len(kept['rules']['items']), 2)

    def test_requesting_the_middle_element_keeps_its_own_dependency(self):
        self.connect(self.CHAIN)
        manifest, _notes = ea.subset_manifest(self.svc.elements.manifest(), [self.B])
        self.assertEqual([row['ref'] for row in manifest['elements']], [self.B, self.C])
        self.assertEqual(manifest['rules']['items'][0]['from'], self.B)
        self.assertEqual(manifest['rules']['items'][0]['to'], self.C)

    def test_conflict_guard_survives_the_subset(self):
        self.connect([{'kind': 'conflicts', 'from': self.A,
                       'to': 'steam-horror/steam_high_pressure_boiler'}])
        manifest, notes = ea.subset_manifest(self.svc.elements.manifest(), [self.A])
        self.assertEqual([row['ref'] for row in manifest['elements']], [self.A])
        self.assertEqual([rule['kind'] for rule in manifest['rules']['items']],
                         ['conflicts'])
        self.assertTrue(any('守卫' in text for text in notes))
        draft = asyncio.run(self.svc.world_generator.generate(
            GenerateWorldRequest(kind='world', title='守卫世界', instruction='生成可探索世界',
                                 city_count=2, elements=[self.A])))
        kept = self.generated_story(draft['id'])['mechanics'][ea.MECHANICS_KEY]
        self.assertEqual([rule['kind'] for rule in kept['rules']['items']], ['conflicts'])

    def test_subset_containing_both_sides_of_a_conflict_is_refused(self):
        boiler = 'steam-horror/steam_high_pressure_boiler'
        manifest = {
            'version': ea.SCHEMA_VERSION, 'locked_at': 'hand-built', 'count': 3,
            'elements': [
                {'ref': self.A, 'namespace': 'staples', 'element_id': 'staples_wheat',
                 'version': 1, 'state': 'existing'},
                {'ref': self.B, 'namespace': 'materials', 'element_id': 'materials_steel',
                 'version': 1, 'state': 'existing'},
                {'ref': boiler, 'namespace': 'steam-horror',
                 'element_id': 'steam_high_pressure_boiler', 'version': 1,
                 'state': 'existing'}],
            'rules': {'version': ea.SCHEMA_VERSION,
                      'items': [{'kind': 'conflicts', 'from': self.A, 'to': boiler}]},
            'warnings': [], 'unsupported': [], 'note': '',
        }
        with self.assertRaisesRegex(ea.AssemblyError, '互斥'):
            ea.subset_manifest(manifest, [self.A, boiler])

    def test_pipeline_save_keeps_the_closure(self):
        self.connect(self.CHAIN)
        runner = WorldPipeline(self.svc)
        document = runner.start(PipelineRequest(title='闭包流水线', instruction='四阶段世界',
                                                regions=2, elements=[self.A]))
        for _ in range(4):
            document = asyncio.run(runner.advance(document['id']))
        saved = runner.save(document['id'])
        story = json.loads((self.svc.runtime.library / saved['folder'] / 'story.json')
                           .read_text(encoding='utf-8'))
        kept = story['mechanics'][ea.MECHANICS_KEY]
        self.assertEqual([row['ref'] for row in kept['elements']],
                         [self.A, self.B, self.C])
        self.assertEqual(len(kept['rules']['items']), 2)


class CommitGuardTests(AssemblyCase):
    """原始基准、索引失败窗口的无库重试、构建期间的并发改动、幂等重试零写。"""

    def test_commit_requires_the_original_base_revision(self):
        draft = self.svc.elements.save_draft([self.selection(WHEAT)], [])
        base = draft['base_story_revision']
        advanced = private_commit(self.svc, '原标题·推进一个版本')
        self.assertNotEqual(advanced, base)
        before = len(self.svc.store.all('package'))
        # 世界已经前进：即便调用方给出「当前」的基准，也不允许用旧草稿隐式 rebase。
        with self.assertRaisesRegex(ea.AssemblyError, '是基于'):
            self.svc.elements.commit(draft['id'],
                                     expected_draft_revision=draft['revision'],
                                     expected_story_revision=advanced)
        self.assertEqual(len(self.svc.store.all('package')), before)
        self.assertIsNone(self.svc.elements.manifest())
        self.assertEqual(self.svc.elements.get_draft(draft['id'])['status'], 'draft')

    def test_retry_in_the_index_failure_window_needs_no_library(self):
        copy_path = self.dir / 'lib-copy.sqlite3'
        shutil.copyfile(self.library_path, copy_path)
        self.svc.elements.configure(copy_path, allowed_roots=[self.tmp.name])
        draft = self.svc.elements.save_draft([self.selection(WHEAT)], [])
        with patch.object(ea.ElementAssembly, '_mark_committed', lambda *a, **k: False):
            result = self.commit_draft(draft)
        self.assertFalse(result['indexed'])          # 世界已保存，索引没写
        copy_path.unlink()                            # 失败窗口里源库没了
        self.assertFalse(self.svc.elements.status()['exists'])
        repair = self.svc.elements.commit(
            draft['id'], expected_draft_revision=draft['revision'],
            expected_story_revision=self.svc.runtime.package()['id'])
        self.assertTrue(repair['reused'])
        self.assertTrue(repair['indexed'])
        self.assertEqual(self.svc.elements.get_draft(draft['id'])['status'], 'committed')

    def test_interleaved_draft_update_blocks_the_commit(self):
        draft = self.svc.elements.save_draft([self.selection(WHEAT)], [])
        original = ea.ElementAssembly.build_manifest

        def racing(instance, *args, **kwargs):
            manifest = original(instance, *args, **kwargs)
            # 模拟另一个写入者恰好在 build_manifest 之后、commit_package 之前改了草稿
            stored = instance.get_draft(draft['id'])
            stored['revision'] += 3
            stored['note'] = '被别人改过'
            instance.service.store.put('element_draft', draft['id'], stored)
            return manifest

        before = len(self.svc.store.all('package'))
        with patch.object(ea.ElementAssembly, 'build_manifest', racing):
            with self.assertRaisesRegex(ea.AssemblyError, '构建清单期间'):
                self.commit_draft(draft)
        self.assertEqual(len(self.svc.store.all('package')), before)  # 零世界副作用
        self.assertIsNone(self.svc.elements.manifest())

    def test_idempotent_retry_does_not_write_the_draft_again(self):
        draft = self.svc.elements.save_draft([self.selection(WHEAT)], [])
        first = self.commit_draft(draft)
        stored = self.svc.elements.get_draft(draft['id'])
        again = self.commit_draft(draft)
        self.assertTrue(again['reused'])
        self.assertEqual(again['revision'], first['revision'])
        after = self.svc.elements.get_draft(draft['id'])
        self.assertEqual(after['revision'], stored['revision'])
        self.assertEqual(after['updated'], stored['updated'])
        self.assertEqual(after['status'], 'committed')


class RecoveryTests(AssemblyCase):
    """预留中断的恢复：重启补索引 / 陈旧预留回草稿（版本单调）/ 失败不留 ABA / pointer 变化零覆盖。"""

    def restart(self, token='next-boot-token'):
        """模拟进程重启：换一个 owner token 重建 Service（包事务日志已由 Runtime 先恢复）。"""
        with patch.object(ea, 'PROCESS_TOKEN', token):
            return Service(Store(self.dir / 'state.sqlite3'), ROOT)

    def test_startup_recovery_repairs_a_crashed_commit(self):
        draft = self.svc.elements.save_draft([self.selection(WHEAT)], [])
        with patch.object(ea.ElementAssembly, '_mark_committed', lambda *a, **k: False):
            result = self.commit_draft(draft)
        self.assertFalse(result['indexed'])
        self.assertEqual(self.svc.elements.get_draft(draft['id'])['status'], 'committing')
        restarted = self.restart()
        report = restarted.elements.startup_report
        self.assertIn(draft['id'], report['repaired'])
        stored = restarted.elements.get_draft(draft['id'])
        self.assertEqual(stored['status'], 'committed')
        self.assertEqual(stored['committed_revision'], result['revision'])
        self.assertGreaterEqual(stored['revision'], 1)      # 版本号单调，不回退
        self.assertNotIn('reserved_by', stored)

    def test_startup_recovery_releases_a_stale_reservation_without_rewinding(self):
        draft = self.svc.elements.save_draft([self.selection(WHEAT)], [])
        stored = self.svc.elements.get_draft(draft['id'])
        reserved = stored['revision'] + 1
        stored.update(status='committing', revision=reserved, reserved_by='previous-boot')
        self.svc.store.put('element_draft', draft['id'], stored)
        restarted = self.restart()
        report = restarted.elements.startup_report
        self.assertIn(draft['id'], report['recovered'])
        after = restarted.elements.get_draft(draft['id'])
        self.assertEqual(after['status'], 'draft')
        self.assertEqual(after['revision'], reserved)
        # 本进程正在提交的预留不会被「恢复」抢走
        live = restarted.elements.save_draft([self.selection(WHEAT)], [])
        row = restarted.elements.get_draft(live['id'])
        row.update(status='committing', revision=row['revision'] + 1,
                   reserved_by=ea.PROCESS_TOKEN)
        restarted.store.put('element_draft', live['id'], row)
        again = restarted.elements.recover_reservations()
        self.assertIn(live['id'], again['skipped'])
        self.assertEqual(restarted.elements.get_draft(live['id'])['status'], 'committing')

    def test_failed_commit_keeps_the_revision_monotonic(self):
        draft = self.svc.elements.save_draft([self.selection(WHEAT)], [])

        def boom(*args, **kwargs):
            raise ea.AssemblyError('模拟提交过程中失败')

        with patch.object(ea, 'validate_package', boom):
            with self.assertRaisesRegex(ea.AssemblyError, '模拟提交'):
                self.commit_draft(draft)
        stored = self.svc.elements.get_draft(draft['id'])
        self.assertEqual(stored['status'], 'draft')
        self.assertGreater(stored['revision'], draft['revision'])   # 不回退 → 无 ABA
        self.assertNotIn('reserved_by', stored)
        self.assertIsNone(self.svc.elements.manifest())
        with self.assertRaisesRegex(ea.AssemblyError, '已被其他操作更新'):
            self.svc.elements.save_draft([self.selection(WHEAT)], [], draft_id=draft['id'],
                                         expected_revision=draft['revision'])
        saved = self.svc.elements.save_draft([self.selection(WHEAT)], [], draft_id=draft['id'],
                                            expected_revision=stored['revision'])
        self.assertEqual(saved['status'], 'draft')

    def test_pointer_switch_during_the_commit_is_refused(self):
        draft = self.svc.elements.save_draft([self.selection(WHEAT)], [])
        original = ea.ElementAssembly.build_manifest

        def racing(instance, *args, **kwargs):
            manifest = original(instance, *args, **kwargs)
            private_commit(instance.service, '别的实例提交')   # 另一个实例推进了 pointer
            return manifest

        before = len(self.svc.store.all('package'))
        with patch.object(ea.ElementAssembly, 'build_manifest', racing):
            with self.assertRaisesRegex(ea.AssemblyError, '预留后|其他操作改动'):
                self.commit_draft(draft)
        self.assertEqual(len(self.svc.store.all('package')), before + 1)  # 只有别人的那版
        self.assertIn('别的实例提交', self.svc.runtime.package()['story']['title'])
        self.assertIsNone(self.svc.elements.manifest())                   # 零覆盖
        self.assertEqual(self.svc.elements.get_draft(draft['id'])['status'], 'draft')
