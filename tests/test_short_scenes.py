import asyncio
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import free_actions, scene_judgment
from app.contracts import Turn
from app.service import Service
from app.storage import Store
from tools.playable_scenes import ROOT, scenes


class ShortSceneTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.service = Service(Store(Path(self.tmp.name) / 'test.sqlite3'), ROOT)
        self.service.provider.configure({'offline': True})
        self.rt = self.service.runtime

    def start(self, data):
        self.rt.commit_package(data['story'], data['characters'], 'short-scene test')
        return self.rt.new_session('test', 'protagonist')

    def do(self, s, action_id, token=True):
        action = free_actions.describe(s, self.rt.package(s['revision'])['story'], self.rt.node(s), action_id)
        asyncio.run(self.service.turn(s['id'], Turn(message=action['label'], action_id=action_id,
                    confirm=action['confirm'] if token else None)))
        return self.service.store.session(s['id'])

    def route(self, data, name):
        s = self.start(data)
        visited = []
        for step in data['playtest'][name]:
            if step.startswith('@'):
                self.rt.move(s, step[1:])
                s = self.service.store.session(s['id'])
                visited.append(step[1:])
                continue
            if step.startswith('?'):
                step = step[1:]
                available = {row['id'] for row in self.rt.surface(s)['actions']}
                if step not in available:
                    continue
            s = self.do(s, step)
        self.assertIsNotNone(s.get('ending'))
        self.assertEqual(len(s['archives']), 4)
        self.assertGreaterEqual(len(visited), 3)
        resources = s['local']['resources']
        self.assertGreaterEqual(resources['pence'], 0)
        self.assertEqual(resources.get('linen', 0), 0)
        self.assertEqual(resources.get('wheat', 0), 0)
        # Every change in money must be accounted for by the existing ledger.
        deltas = sum(row['delta'] for row in s['local']['ledger'] if row['resource'] == 'pence')
        self.assertEqual(resources['pence'], 18 + deltas)
        return s

    def test_all_routes_reach_distinct_endings(self):
        for data in scenes():
            with self.subTest(story=data['story']['id']):
                first = self.route(data, 'route')
                second = self.route(data, 'alternative')
                self.assertNotEqual(first['ending']['id'], second['ending']['id'])

    def yard(self):
        s = self.start(scenes()[0])
        s = self.do(s, 'ask_job')
        s = self.do(s, 'go_search')
        self.rt.move(s, 'yard')
        return self.service.store.session(s['id'])

    def test_risky_action_needs_confirmation_and_cannot_show_before_take(self):
        s = self.yard()
        before = copy.deepcopy(s)
        with self.assertRaises(ValueError):
            self.do(s, 'steal_linen', token=False)
        with self.assertRaises(ValueError):
            self.do(s, 'show_linen')
        self.assertEqual(before, self.service.store.session(s['id']))
        old = free_actions.describe(s, self.rt.package(s['revision'])['story'], self.rt.node(s), 'steal_linen')
        s = self.do(s, 'search_slowly')
        with self.assertRaises(ValueError):
            asyncio.run(self.service.turn(s['id'], Turn(message='偷取', action_id='steal_linen', confirm=old['confirm'])))
        self.assertEqual(s, self.service.store.session(s['id']))

    def test_hidden_success_and_visible_failure_are_different(self):
        for success in (True, False):
            s = self.yard()
            with patch('app.runtime.resolve_check', return_value={
                'attribute': 'agility', 'probability': .45, 'success': success, 'margin': .1 if success else -.1}):
                s = self.do(s, 'steal_linen')
            self.assertEqual(s['local']['resources']['linen'], int(success))
            reactions = s['scene_judgments'][-1]['reactions']
            self.assertEqual(len(reactions), 0 if success else 1)
            if success:
                s = self.do(s, 'show_linen')
                self.assertTrue(s['flags']['tavern_banned'])
                s = self.do(s, 'return_linen')
                self.assertFalse(s['flags']['linen_held'])
                self.assertEqual(s['local']['resources']['linen'], 0)

    def test_model_invented_consequence_is_rejected_without_saving(self):
        s = self.yard()
        self.service.provider.configure({'offline': False, 'api_key': 'local-test'})
        async def invalid(*args, **kwargs):
            return {'narration': '卫兵凭空出现。', 'reactions': [{'character': 'guard', 'choice': 'jail'}]}, {}
        with patch.object(self.service.provider, 'complete', side_effect=invalid):
            with self.assertRaises(ValueError):
                self.do(s, 'steal_linen')
        self.assertEqual(s, self.service.store.session(s['id']))

    def test_model_choices_use_authorized_effects_and_original_check(self):
        s = self.yard()
        self.service.provider.configure({'offline': False, 'api_key': 'local-test'})
        seen = []
        async def select(*args, **kwargs):
            data = args[1]
            seen.append(data)
            return {'narration': '我碰响衣夹，贝丝转过身。',
                    'reactions': [{'character': 'bess', 'choice': 'report'}]}, {}
        with patch('app.runtime.resolve_check', return_value={
            'attribute': 'agility', 'probability': .45, 'success': False, 'margin': -.2}), \
             patch.object(self.service.provider, 'complete', side_effect=select):
            s = self.do(s, 'steal_linen')
        self.assertFalse(seen[0]['check']['success'])
        self.assertTrue(s['flags']['report_planned'])
        self.assertEqual(s['local']['resources']['pence'], 18)
        self.assertEqual(s['local']['resources']['linen'], 0)
        self.assertEqual(s['development']['bess']['relationships']['player']['trust'], .2)

    def test_rollback_restores_money_and_reactions(self):
        s = self.route(scenes()[2], 'route')
        last = s['archives'][-1]
        restored = self.rt.rollback(s, last['id'])
        self.assertEqual(restored['local'], last['before']['local'])
        self.assertEqual(restored.get('development'), last['before'].get('development'))
        self.assertEqual(restored.get('scene_judgments'), last['before'].get('scene_judgments'))

    def test_intent_cannot_execute_or_invent_an_action(self):
        s = self.yard()
        story = self.rt.package(s['revision'])['story']
        self.service.provider.configure({'offline': False, 'api_key': 'local-test'})
        async def good(*args, **kwargs):
            return {'action_id': 'steal_linen', 'reason': '先尝试偷取，不能提前炫耀。'}, {}
        with patch.object(self.service.provider, 'complete', side_effect=good):
            result = asyncio.run(scene_judgment.intent(self.service, s, story, self.rt.node(s), '偷走再炫耀'))
        self.assertEqual(result['matched'][0]['action_id'], 'steal_linen')
        self.assertTrue(result['matched'][0]['risk_notice'])
        self.assertEqual(s, self.service.store.session(s['id']))
        async def bad(*args, **kwargs):
            return {'action_id': 'fly_to_moon', 'reason': '飞走'}, {}
        with patch.object(self.service.provider, 'complete', side_effect=bad), self.assertRaises(ValueError):
            asyncio.run(scene_judgment.intent(self.service, s, story, self.rt.node(s), '飞到月亮'))

    def test_private_thought_is_not_npc_evidence_and_manual_close_cannot_skip(self):
        s = self.yard()
        request = Turn(message='我在心里盘算偷走衣物', channel='thought')
        work = copy.deepcopy(s)
        result = self.rt.prepare_turn(work, request)
        data = scene_judgment.context(self.rt, work, request, result, None)
        self.assertEqual(data['observers'], [])
        self.assertTrue(all(p['heard_input'] is None for p in data['conversation_partners']))
        self.assertFalse(any('盘算' in r['text'] for r in work['beliefs']))
        with self.assertRaises(ValueError):
            self.rt.close_event(s)

    def test_stale_model_reply_cannot_overwrite_new_state(self):
        s = self.start(scenes()[1])
        self.service.provider.configure({'offline': False, 'api_key': 'local-test'})
        async def raced(*args, **kwargs):
            latest = self.service.store.session(s['id'])
            latest['flags']['other_operation'] = True
            self.service.store.save_session(latest)
            return {'narration': '奥伦要求澄清。', 'reactions': [{'character': 'guard', 'choice': 'stern'}]}, {}
        with patch.object(self.service.provider, 'complete', side_effect=raced), self.assertRaises(ValueError):
            self.do(s, 'accuse')
        latest = self.service.store.session(s['id'])
        self.assertTrue(latest['flags']['other_operation'])
        self.assertNotIn('guard_offended', latest['flags'])
        self.assertNotIn('scene_judgments', latest)


if __name__ == '__main__':
    unittest.main()
