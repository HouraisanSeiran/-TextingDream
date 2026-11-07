# -*- coding: utf-8 -*-
"""AI 草稿：元素 / NPC 角色卡 / 故事包简化入口。

全部跑在临时目录：临时旅程库（Store）、临时百科库（现场从采集 JSON 只读导入），
provider 一律离线或打补丁的假 provider，不发真实模型请求。
"""
import asyncio
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import ai_drafts as ad
from app import encyclopedia as enc
from app.storage import Store
from tests.fixtures_world import world_app, world_service

ROOT = Path(__file__).resolve().parents[1]
BASE_GROUP = 'docs/human-encyclopedia/staples.json'


def run(coro):
    return asyncio.run(coro)


def good_element(**changes):
    value = {
        'summary': '一种在北方雪原游荡、会结群迁徙的白色大鹿。',
        'aliases': ['雪鹿'],
        'primary': 'beast',
        'tags': ['kind:beast', 'theme:snow'],
        'game': {'price': {'min': None, 'max': None, 'per': '', 'tier': 'not_for_sale'},
                 'terrains': ['tundra'], 'seasons': ['winter'], 'keeps': 'years',
                 'sold_by': ['none'], 'note': '活物不作商品。'},
        'details': {key: '%s：示例段落，设定推演。' % key for key in enc.DETAIL_SECTIONS},
    }
    value.update(changes)
    return value


def good_card(**changes):
    card = {key: {'text': key + ' 的内容', 'visibility': 'public'} for key in
            ('identity', 'experiences', 'values', 'goal', 'pressure', 'boundaries',
             'bargaining', 'social_context', 'emotion', 'failure_response')}
    card['knowledge'] = [{'text': '听说关外有人走私盐', 'kind': 'rumor', 'source': '商队闲谈',
                          'confidence': 0.4, 'visibility': 'private'}]
    card.update(changes)
    return card


class FakeProvider:
    """按顺序吐出预设输出；记录每次收到的 context。"""

    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.contexts = []

    def config(self):
        return {'offline': False}

    async def complete(self, system, context, json_mode=False, scope='', max_tokens=None, thinking=None):
        self.contexts.append(copy.deepcopy(context))
        return copy.deepcopy(self.outputs.pop(0)), {'prompt_tokens': 1}

    def offline_trace(self, *args, **kwargs):  # pragma: no cover - online path never calls it
        raise AssertionError('online fake must not use offline trace')


class DraftCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = tempfile.TemporaryDirectory()
        cls.base_library = Path(cls.base.name) / 'base.sqlite3'
        enc.import_file(cls.base_library, ROOT / BASE_GROUP)

    @classmethod
    def tearDownClass(cls):
        cls.base.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        # 每个用例一份可写的库副本：确认会往里写 player-created。
        self.library = self.dir / 'library.sqlite3'
        self.library.write_bytes(self.base_library.read_bytes())
        self.svc = world_service(Store(self.dir / 'state.sqlite3'), ROOT)
        self.svc.provider.configure({'offline': True})
        self.svc.elements.configure(self.library, allowed_roots=[self.tmp.name])
        self.drafts = self.svc.ai_drafts

    def tearDown(self):
        self.tmp.cleanup()

    def fake(self, outputs):
        fake = FakeProvider(outputs)
        patcher = patch.object(self.svc, 'provider', fake)
        patcher.start()
        self.addCleanup(patcher.stop)
        return fake

    def element_request(self, **changes):
        data = {'name': '霜角鹿', 'tags': ['雪原', '野兽', '迁徙'], 'direction': '北方部落追随它迁徙'}
        data.update(changes)
        return ad.ElementDraftRequest(**data)

    def player_search(self, **kwargs):
        return enc.search(self.library, namespace=ad.NAMESPACE, **kwargs)


# ----------------------------------------------------------------- 阶段一：元素
class ElementGenerationTests(DraftCase):
    def test_offline_draft_is_compliant_and_not_in_library(self):
        draft = run(self.drafts.generate_element(self.element_request()))
        element = draft['content']
        self.assertEqual(draft['status'], 'draft')
        self.assertTrue(draft['offline'])
        self.assertEqual(ad.validate_element(element), [])
        self.assertTrue(element['id'].startswith('player_'))
        self.assertEqual(element['primary'], 'beast')
        self.assertEqual(element['evidence_grade'], 'inferred')
        self.assertEqual(element['source_ids'], [])
        self.assertEqual(element['review_status'], 'needs_review')
        self.assertEqual(element['detail_status'], 'needs_detail')
        self.assertIn(ad.EVIDENCE_NOTICE, element['details']['evidence_and_uncertainty'])
        self.assertTrue(all(element['details'][k].strip() for k in enc.DETAIL_SECTIONS))
        self.assertEqual(self.player_search()['total'], 0)
        # 同一请求离线模板是确定性的（id 除外）。
        again = run(self.drafts.generate_element(self.element_request()))['content']
        self.assertEqual(again['details'], element['details'])

    def test_bad_json_then_bad_tags_is_rejected_with_zero_writes(self):
        fake = self.fake([['不是对象'], good_element(tags=['种类:野兽', 'Kind:Beast'])])
        with self.assertRaises(ad.DraftRejected):
            run(self.drafts.generate_element(self.element_request()))
        self.assertEqual(len(fake.contexts), 2)
        self.assertIn('errors', fake.contexts[1])
        self.assertEqual(self.svc.store.all(ad.KIND), [])
        self.assertEqual(self.player_search()['total'], 0)

    def test_retry_once_can_succeed(self):
        fake = self.fake([good_element(primary='dragon_thing'), good_element()])
        draft = run(self.drafts.generate_element(self.element_request()))
        self.assertEqual(len(draft['attempts']), 2)
        self.assertTrue(draft['attempts'][0]['errors'])
        self.assertEqual(draft['attempts'][1]['errors'], [])
        self.assertEqual(draft['usage']['calls'], 2)
        self.assertIn('primary', ' '.join(fake.contexts[1]['errors']))

    def test_model_cannot_set_evidence_sources_or_identity(self):
        self.fake([good_element(evidence_grade='sourced', source_ids=['staples_src_01'],
                                sources=[{'id': 'fake', 'title': '假书', 'access': 'read'}],
                                review_status='reviewed', detail_status='reviewed_detail',
                                id='evil_id', group='staples', name='别的名字')])
        element = run(self.drafts.generate_element(self.element_request()))['content']
        self.assertEqual(element['evidence_grade'], 'inferred')
        self.assertEqual(element['source_ids'], [])
        self.assertNotIn('sources', element)
        self.assertNotIn('group', element)
        self.assertEqual(element['review_status'], 'needs_review')
        self.assertEqual(element['detail_status'], 'needs_detail')
        self.assertTrue(element['id'].startswith('player_'))
        self.assertEqual(element['name'], '霜角鹿')

    def test_handwritten_game_tags_are_replaced_by_derived_ones(self):
        self.fake([good_element(tags=['kind:beast', 'price:pound', 'terrain:ocean'])])
        element = run(self.drafts.generate_element(self.element_request()))['content']
        self.assertNotIn('price:pound', element['tags'])
        self.assertIn('price:not_for_sale', element['tags'])
        self.assertIn('terrain:tundra', element['tags'])

    def test_medicinal_red_line(self):
        details = {key: '设定推演段落。' for key in enc.DETAIL_SECTIONS}
        details['mechanism'] = '每日煎服 3 克，主治风寒。'
        herb = good_element(primary='medicinal_herb', tags=['kind:herb'], details=details,
                            game={'price': {'min': 4, 'max': 8, 'per': '一包', 'tier': 'groat'},
                                  'terrains': ['mountain'], 'seasons': ['autumn'], 'keeps': 'months',
                                  'sold_by': ['apothecary'], 'note': ''})
        self.fake([herb, herb])
        with self.assertRaises(ad.DraftRejected) as caught:
            run(self.drafts.generate_element(self.element_request(name='雪参')))
        self.assertIn('药材', str(caught.exception))
        self.assertEqual(self.svc.store.all(ad.KIND), [])

    def test_offline_medicinal_template_passes_red_line(self):
        draft = run(self.drafts.generate_element(
            self.element_request(name='岩苔', tags=['药材'], direction='据说能治风寒', primary='medicinal_herb')))
        self.assertEqual(ad.validate_element(draft['content']), [])
        self.assertNotIn('治风寒', ''.join(draft['content']['details'].values()))


class ElementConfirmTests(DraftCase):
    def test_confirm_imports_and_is_searchable_by_primary(self):
        draft = run(self.drafts.generate_element(self.element_request()))
        result = self.drafts.confirm(draft['id'], ad.DraftDecision(revision=draft['revision']))
        self.assertFalse(result['idempotent'])
        self.assertEqual(result['status'], 'confirmed')
        self.assertEqual(result['confirmed']['version'], 1)
        hits = self.player_search(tags_all=['primary:beast', 'evidence:inferred'])
        self.assertEqual([i['element_id'] for i in hits['items']], [draft['element_id']])
        detail = enc.get(self.library, draft['element_id'], namespace=ad.NAMESPACE)
        self.assertEqual(detail['sources'], [])
        # 元素装配能从库里选中它（作者另行装配，不是自动进包）。
        manifest, _ = self.svc.elements.build_manifest([{
            'namespace': ad.NAMESPACE, 'element_id': draft['element_id'], 'version': 1,
            'state': 'existing', 'acknowledge_candidate': True,
            'disclosure': {'public_description': '雪原上的白鹿。',
                           'location_id': self.svc.runtime.package()['story']['locations'][0]['id'],
                           'known_by': ['player']}}])
        self.assertEqual(manifest['elements'][0]['ref'], ad.NAMESPACE + '/' + draft['element_id'])

    def test_repeat_confirm_is_idempotent_and_edit_makes_a_new_version(self):
        draft = run(self.drafts.generate_element(self.element_request()))
        self.drafts.confirm(draft['id'], ad.DraftDecision())
        again = self.drafts.confirm(draft['id'], ad.DraftDecision())
        self.assertTrue(again['idempotent'])
        versions = enc.versions(self.library, draft['element_id'], namespace=ad.NAMESPACE)
        self.assertEqual(len(versions['versions']), 1)
        current = self.drafts.get(draft['id'])
        content = copy.deepcopy(current['content'])
        content['summary'] = '改过的摘要：雪原白鹿。'
        content['evidence_grade'] = 'sourced'  # 编辑也不能升格
        edited = self.drafts.edit(draft['id'], ad.DraftEdit(revision=current['revision'], content=content))
        self.assertEqual(edited['status'], 'draft')
        self.assertEqual(edited['content']['evidence_grade'], 'inferred')
        second = self.drafts.confirm(draft['id'], ad.DraftDecision())
        self.assertEqual(second['confirmed']['version'], 2)
        self.assertEqual(len(enc.versions(self.library, draft['element_id'], namespace=ad.NAMESPACE)['versions']), 2)

    def test_restore_after_rebuild(self):
        draft = run(self.drafts.generate_element(self.element_request()))
        self.drafts.confirm(draft['id'], ad.DraftDecision())
        current = self.drafts.get(draft['id'])
        content = copy.deepcopy(current['content'])
        content['summary'] = '第二版摘要。'
        self.drafts.edit(draft['id'], ad.DraftEdit(revision=current['revision'], content=content))
        self.drafts.confirm(draft['id'], ad.DraftDecision())
        rebuilt = self.dir / 'rebuilt.sqlite3'
        rebuilt.write_bytes(self.base_library.read_bytes())
        first = self.drafts.restore_confirmed(rebuilt)
        self.assertEqual(first['element_versions_written'], 2)
        second = self.drafts.restore_confirmed(rebuilt)
        self.assertEqual(second['element_versions_written'], 0)
        detail = enc.get(rebuilt, draft['element_id'], namespace=ad.NAMESPACE)
        self.assertEqual(detail['version'], 2)
        self.assertEqual(detail['summary'], '第二版摘要。')

    def test_rejected_draft_cannot_be_confirmed(self):
        draft = run(self.drafts.generate_element(self.element_request()))
        rejected = self.drafts.reject(draft['id'], ad.DraftDecision())
        self.assertEqual(rejected['status'], 'rejected')
        with self.assertRaises(ValueError):
            self.drafts.confirm(draft['id'], ad.DraftDecision())
        self.assertEqual(self.player_search()['total'], 0)

    def test_edit_with_invalid_content_changes_nothing(self):
        draft = run(self.drafts.generate_element(self.element_request()))
        content = copy.deepcopy(draft['content'])
        content['tags'] = ['中文标签']
        with self.assertRaises(ValueError):
            self.drafts.edit(draft['id'], ad.DraftEdit(revision=1, content=content))
        self.assertEqual(self.drafts.get(draft['id'])['content'], draft['content'])

    def test_missing_library_keeps_draft_unconfirmed(self):
        self.svc.elements.configure(self.dir / 'absent.sqlite3', allowed_roots=[self.tmp.name])
        draft = run(self.drafts.generate_element(self.element_request()))
        with self.assertRaises(ValueError):
            self.drafts.confirm(draft['id'], ad.DraftDecision())
        self.assertFalse((self.dir / 'absent.sqlite3').exists())
        self.assertEqual(self.drafts.get(draft['id'])['status'], 'draft')

    def test_generate_and_confirm_leave_locked_manifest_and_journey_alone(self):
        place = self.svc.runtime.package()['story']['locations'][0]['id']
        saved = self.svc.elements.save_draft([{
            'namespace': 'staples', 'element_id': 'staples_wheat', 'version': 1,
            'state': 'existing', 'acknowledge_candidate': True,
            'disclosure': {'public_description': '麦子。', 'location_id': place, 'known_by': ['player']}}])
        self.svc.elements.commit(saved['id'], expected_draft_revision=saved['revision'],
                                 expected_story_revision=self.svc.runtime.package()['id'])
        package = self.svc.runtime.package()
        manifest = copy.deepcopy(package['story']['mechanics']['element_manifest'])
        session = self.svc.runtime.new_session('进行中', 'protagonist')
        draft = run(self.drafts.generate_element(self.element_request()))
        self.drafts.confirm(draft['id'], ad.DraftDecision())
        after = self.svc.runtime.package()
        self.assertEqual(after['id'], package['id'])
        self.assertEqual(after['story']['mechanics']['element_manifest'], manifest)
        self.assertEqual(self.svc.store.session(session['id'])['revision'], session['revision'])
        refs = [e['ref'] for e in manifest['elements']]
        self.assertNotIn(ad.NAMESPACE + '/' + draft['element_id'], refs)


# ------------------------------------------------------------- 阶段二：NPC 卡
class NPCDraftTests(DraftCase):
    def npc_request(self, **changes):
        data = {'name': '关城守卫', 'tags': ['老兵', '贪杯'], 'direction': '收点小钱就放行',
                'character_id': 'pass_guard'}
        data.update(changes)
        return ad.NPCDraftRequest(**data)

    def card_of(self, revision, cid='pass_guard'):
        chars = self.svc.runtime.package(revision)['characters']['characters']
        return next(c for c in chars if c['id'] == cid).get('npc_card')

    def test_offline_draft_then_confirm_creates_a_new_card_version(self):
        before = self.svc.runtime.package()['id']
        old_session = self.svc.runtime.new_session('旧旅程', 'protagonist')
        draft = run(self.drafts.generate_npc(self.npc_request()))
        self.assertEqual(ad.validate_card(draft['content']), [])
        self.assertEqual(draft['base_revision'], before)
        self.assertEqual(self.svc.runtime.package()['id'], before)  # 草稿不动包
        self.assertIsNone(self.card_of(before))
        result = self.drafts.confirm(draft['id'], ad.DraftDecision(package_revision=before))
        after = result['confirmed']['revision']
        self.assertNotEqual(after, before)
        self.assertEqual(self.svc.runtime.package()['id'], after)
        self.assertEqual(self.card_of(after)['identity'], draft['content']['identity'])
        # 已开始的旅程仍绑旧版本，不自动换卡。
        self.assertEqual(self.svc.store.session(old_session['id'])['revision'], before)
        self.assertIsNone(self.card_of(before))
        again = self.drafts.confirm(draft['id'], ad.DraftDecision(package_revision=after))
        self.assertTrue(again['idempotent'])
        self.assertEqual(self.svc.runtime.package()['id'], after)

    def test_stale_package_revision_is_refused(self):
        draft = run(self.drafts.generate_npc(self.npc_request()))
        with self.assertRaises(ValueError):
            self.drafts.confirm(draft['id'], ad.DraftDecision(package_revision='stale'))
        self.assertEqual(self.drafts.get(draft['id'])['status'], 'draft')

    def test_witness_claims_and_bad_structure_are_rejected_with_zero_writes(self):
        before = self.svc.runtime.package()['id']
        witness = good_card(knowledge=[{'text': '亲眼看见商人杀了人', 'kind': 'observation',
                                        'source': '自己', 'confidence': 0.9, 'visibility': 'private'}])
        fake = self.fake([{'identity': 5}, witness])
        with self.assertRaises(ad.DraftRejected):
            run(self.drafts.generate_npc(self.npc_request()))
        self.assertEqual(len(fake.contexts), 2)
        self.assertEqual(self.svc.store.all(ad.KIND), [])
        self.assertEqual(self.svc.runtime.package()['id'], before)

    def test_empty_field_is_retried(self):
        empty = good_card()
        empty['pressure'] = {'text': '', 'visibility': 'private'}
        self.fake([empty, good_card()])
        draft = run(self.drafts.generate_npc(self.npc_request()))
        self.assertEqual(len(draft['attempts']), 2)

    def test_unknown_character_is_refused(self):
        with self.assertRaises(ValueError):
            run(self.drafts.generate_npc(self.npc_request(character_id='protagonist')))
        self.assertEqual(self.svc.store.all(ad.KIND), [])


# ------------------------------------------------------- 阶段三：故事包入口
class StoryDraftTests(DraftCase):
    def test_story_entry_wraps_world_generator(self):
        before = self.svc.runtime.package()['id']
        draft = run(self.drafts.generate_story(ad.StoryDraftRequest(
            title='霜原', tags=['雪原', '部落'], direction='追随鹿群迁徙的部落')))
        self.assertEqual(draft['kind'], 'worldview')
        self.assertEqual(draft['status'], 'draft')
        self.assertIn('雪原', draft['request']['instruction'])
        self.assertIsNotNone(self.svc.store.get('world_generation', draft['id']))
        self.assertEqual(self.svc.store.all(ad.KIND), [])
        self.assertEqual(self.svc.runtime.package()['id'], before)

    def test_complete_kind(self):
        draft = run(self.drafts.generate_story(ad.StoryDraftRequest(
            tags=['海港'], direction='港口城邦', kind='complete', city_count=2)))
        self.assertEqual(draft['kind'], 'complete')
        self.assertEqual(len(draft['data']['cities']), 2)


# ------------------------------------------------------------------- HTTP
class HttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = world_app(Path(self.tmp.name) / 'web.sqlite3')
        self.app.state.service.provider.configure({'offline': True})

    def tearDown(self):
        self.tmp.cleanup()

    def test_token_required_and_flow(self):
        with TestClient(self.app) as client:
            body = {'name': '霜角鹿', 'tags': ['雪原'], 'direction': '北方'}
            self.assertEqual(client.post('/api/inner/ai-drafts/elements', json=body).status_code, 403)
            self.assertEqual(client.get('/api/inner/ai-drafts').status_code, 403)
            self.assertEqual(client.post('/api/inner/ai-drafts/npcs', json=body).status_code, 403)
            self.assertEqual(client.post('/api/inner/ai-drafts/stories', json={'direction': 'x'}).status_code, 403)
            self.assertEqual(self.app.state.service.store.all(ad.KIND), [])
            client.headers['X-TextileDream-Token'] = client.get('/api/bootstrap').json()['token']
            created = client.post('/api/inner/ai-drafts/elements', json=body)
            self.assertEqual(created.status_code, 200, created.text)
            draft = created.json()
            listed = client.get('/api/inner/ai-drafts', params={'type': 'element'}).json()
            self.assertEqual([d['id'] for d in listed], [draft['id']])
            self.assertEqual(client.get('/api/inner/ai-drafts/' + draft['id']).json()['status'], 'draft')
            rejected = client.post('/api/inner/ai-drafts/%s/reject' % draft['id'], json={})
            self.assertEqual(rejected.json()['status'], 'rejected')
            self.assertEqual(client.post('/api/inner/ai-drafts/elements',
                                         json={**body, 'tags': ['x'] * 17}).status_code, 422)
            npc = client.post('/api/inner/ai-drafts/npcs', json={'name': '客栈掌柜', 'tags': ['精明']})
            self.assertEqual(npc.status_code, 200, npc.text)
            # 没选 NPC 不能确认，也没写包。
            revision = self.app.state.service.runtime.package()['id']
            refused = client.post('/api/inner/ai-drafts/%s/confirm' % npc.json()['id'], json={})
            self.assertEqual(refused.status_code, 400)
            self.assertEqual(self.app.state.service.runtime.package()['id'], revision)


if __name__ == '__main__':
    unittest.main()
