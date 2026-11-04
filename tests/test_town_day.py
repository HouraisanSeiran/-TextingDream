"""Offline acceptance routes for the integrated town-day package."""
import asyncio
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import endings, free_actions, pressure
from app.contracts import Turn
from app.service import Service
from app.storage import Store
from tools.playable_scenes import ROOT, bridge, market, tavern, town_day


class TownDayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        # Package commits write author files as well as SQLite; isolate BOTH.
        self.root = Path(self.tmp.name)
        self.service = Service(Store(self.root / 'test.sqlite3'), self.root)
        self.service.provider.configure({'offline': True})
        self.rt = self.service.runtime
        self.data = town_day()
        self.rt.commit_package(self.data['story'], self.data['characters'], 'town-day test')
        self.addCleanup(patch.stopall)
        patch.object(self.service.provider, 'complete', side_effect=AssertionError('network call')).start()

    def start(self):
        return self.rt.new_session('town-day test', 'protagonist')

    def reload(self, s):
        return self.service.store.session(s['id'])

    def do(self, s, action_id, success=None):
        package = self.rt.package(s['revision'])
        # 判定 v2 的预览要用角色属性算修正与把握，所以把人物文档一并传入
        # （与 Runtime 内部调用 describe 时一致）。
        described = free_actions.describe(s, package['story'], self.rt.node(s), action_id,
                                         characters=package['characters'])
        request = Turn(message=described['label'], action_id=action_id, confirm=described['confirm'])
        if success is None:
            asyncio.run(self.service.turn(s['id'], request))
        else:
            # 这个包已开启判定 v2：徽面由引擎算，所以这里只有钉**档位**才能做
            # 「成功/失败路线」的确定性验证；后果、钟、目击仍走真实实现。
            tier = 'success' if success else 'failure'
            with patch('app.checks.margin_tier', return_value=tier):
                asyncio.run(self.service.turn(s['id'], request))
        result = self.reload(s)
        self.assert_money(result)
        return result

    def move(self, s, destination):
        before = s['time']
        self.rt.move(s, destination)
        result = self.reload(s)
        self.assertEqual(result['time'], before + 1)
        return result

    def available(self, s):
        return {row['id']: row for row in self.rt.surface(s)['actions']}

    def assert_money(self, s):
        rows = [r for r in s['local']['ledger'] if r['resource'] == 'pence']
        self.assertEqual(s['local']['resources']['pence'], 18 + sum(r['delta'] for r in rows))
        self.assertGreaterEqual(s['local']['resources']['pence'], 0)

    def run_steps(self, steps, checks=True):
        s = self.start()
        for step in steps:
            if step.startswith('@'):
                s = self.move(s, step[1:])
            else:
                if step.startswith('?'):
                    step = step[1:]
                    if step not in self.available(s):
                        continue
                s = self.do(s, step, checks if step == 'day_inspect' else None)
        return s

    def to_bridge(self, route='route', checks=True):
        steps = self.data['playtest'][route]
        return self.run_steps(steps[:steps.index('@town_bridge') + 1], checks)

    def test_package_export_validation_and_old_exports_unchanged(self):
        self.rt.validate_package(self.data['story'], self.data['characters'])
        cfg = endings.config(self.data['story'])
        for index, left in enumerate(cfg.endings):
            for right in cfg.endings[index + 1:]:
                self.assertFalse(endings.conditions_overlap(left.condition, right.condition))
        self.assertEqual(len(self.data['story']['locations']), 3)
        self.assertEqual(len(self.data['characters']['characters']) - 1, 4)
        for data in (tavern(), bridge(), market(), self.data):
            exported = json.loads((ROOT / 'docs/playable-scenes' / (data['story']['id'] + '.json')).read_text(encoding='utf-8'))
            self.assertEqual(exported, data)
        self.assertTrue((self.root / 'StoryPackage').exists())

    def test_normal_failed_alternative_and_chaos_reach_distinct_endings(self):
        routes = [('route', True, 'day_normal', 8),
                  ('alternative', False, 'day_friend', 8),
                  ('chaos', False, 'day_chaos', 0)]
        for route, checks, ending_id, balance in routes:
            with self.subTest(route=route):
                s = self.run_steps(self.data['playtest'][route], checks)
                self.assertEqual(s['ending']['id'], ending_id)
                self.assertEqual(len(s['archives']), 4)
                self.assertEqual(s['local']['resources']['pence'], balance)
                self.assertEqual(s['local']['resources']['wheat'], 0)
                self.assertFalse(s['active'])
                self.assertLess(s['time'], 18)
                if route == 'alternative':
                    self.assertTrue(s['flags']['day_inspect_failed'])
                    self.assertTrue(s['flags']['day_quality'])
                    self.assertTrue(s['flags']['introduced'])
                    self.assertAlmostEqual(s['development']['bess']['relationships']['player']['trust'], .7)
                    self.assertFalse(any(r['source'].endswith(':day_pay') for r in s['local']['ledger']))
                if route == 'chaos':
                    self.assertAlmostEqual(s['development']['bess']['relationships']['player']['trust'], .3)

    def test_rumor_is_heard_not_fact_and_changes_credit_and_check(self):
        normal = self.to_bridge()
        normal_actions = self.available(normal)
        self.assertIn('day_credit', normal_actions)
        self.assertEqual(normal_actions['day_bargain']['check']['difficulty'], .45)
        s = self.to_bridge('chaos')
        actions = self.available(s)
        self.assertNotIn('day_credit', actions)
        self.assertNotIn('day_bargain', actions)
        self.assertEqual(actions['day_hard_bargain']['check']['difficulty'], .7)
        self.assertNotIn('day_letter', actions)
        self.assertTrue(any('跑腿转述' in r['text'] and r['distortion'] == 1 for r in s['heard']))
        self.assertTrue(any(r['character'] == 'guard' and '跑腿转述' in r['text'] for r in s['beliefs']))
        self.assertFalse(any('跑腿转述' in r['text'] for r in s['facts']))
        before = copy.deepcopy(s)
        with self.assertRaises(ValueError):
            self.do(s, 'day_credit')
        self.assertEqual(self.reload(s), before)
        s = self.do(s, 'day_hard_bargain', False)
        self.assertTrue(s['flags']['day_repair_failed'])
        self.assertIn('day_carry', self.available(s))
        s = self.do(s, 'day_carry')
        s = self.do(s, 'day_register_work')
        s = self.do(s, 'day_prank_sail')
        self.assertEqual(s['ending']['id'], 'day_chaos')
        self.assertEqual(s['local']['resources']['pence'], 8)

    def test_market_money_and_shared_receipt_are_real_cross_scene_choices(self):
        steps = self.data['playtest']['alternative']
        s = self.run_steps(steps[:steps.index('day_deliver')])
        self.assertEqual(s['local']['resources']['pence'], 0)
        self.assertEqual(s['local']['resources']['wheat'], 1)
        s = self.do(s, 'day_deliver')
        self.assertEqual(s['local']['resources']['pence'], 16)
        s = self.do(s, 'day_share')
        s = self.do(s, 'day_lamp')
        self.assertEqual(s['local']['resources']['pence'], 8)
        s = self.do(s, 'day_return')
        s = self.move(s, 'town_hall')
        self.assertIn('day_introduction', self.available(s))
        s = self.do(s, 'day_to_bridge')
        s = self.move(s, 'town_bridge')
        s = self.do(s, 'day_pay')
        self.assertEqual(s['local']['resources']['pence'], 0)
        s = self.do(s, 'day_sail')
        self.assertEqual(s['ending']['id'], 'day_normal')

    def test_repair_failure_can_pay_or_record_real_debt(self):
        for fallback in ('day_pay', 'day_credit'):
            with self.subTest(fallback=fallback):
                s = self.to_bridge()
                s = self.do(s, 'day_bargain', False)
                self.assertTrue(s['flags']['day_repair_failed'])
                self.assertIn(fallback, self.available(s))
                s = self.do(s, fallback)
                s = self.do(s, 'day_sail')
                self.assertEqual(s['ending']['id'], 'day_normal')
                self.assertEqual(s['local']['resources']['toll_debt'], 8 if fallback == 'day_credit' else 0)
                self.assertEqual(s['local']['resources']['pence'], 16 if fallback == 'day_credit' else 8)

    def test_deadline_warning_trigger_and_continue_work(self):
        s = self.to_bridge()
        self.assertEqual(s['time'], 13)
        before = s['local']['resources']['pence']
        s = self.do(s, 'day_wait')
        self.assertEqual(s['time'], 18)
        self.assertTrue(s['flags']['day_last_call'])
        self.assertTrue(s['flags']['day_missed'])
        self.assertEqual(s['pressure']['applied']['day_boat:escalation'], 15)
        self.assertEqual(s['pressure']['applied']['day_boat:missed'], 18)
        self.assertNotIn('day_pay', self.available(s))
        s = self.do(s, 'day_stay')
        self.assertEqual(s['ending']['id'], 'day_missed')
        self.assertEqual(s['active']['node'], 'town_tomorrow')
        s = self.do(s, 'day_next_work')
        self.assertEqual(s['local']['resources']['pence'], before + 8)
        self.assertTrue(s['flags']['day_rebuilt'])
        s = self.do(s, 'day_next_close')
        self.assertEqual(s['ending']['id'], 'day_missed')

    def test_secured_pass_lifts_deadline_even_after_longer_travel(self):
        s = self.to_bridge()
        s = self.do(s, 'day_pay')
        self.assertIn('day_boat:reserved', s['pressure']['lifted'])
        self.assertIn('day_boat:missed', s['pressure']['cancelled'])
        s = self.do(s, 'day_sail')
        for destination in ('town_hall', 'town_market', 'town_hall', 'town_market', 'town_hall', 'town_bridge'):
            s = self.move(s, destination)
        self.assertGreaterEqual(s['time'], 18)
        self.assertFalse(s['flags'].get('day_missed'))
        self.assertEqual(s['ending']['id'], 'day_normal')

    def test_rollback_restores_cross_scene_money_rumor_relationships_and_pressure(self):
        s = self.run_steps(self.data['playtest']['chaos'])
        for index in (3, 2, 0):
            last = s['archives'][index]
            s = self.rt.rollback(s, last['id'])
            for key in ('local', 'development', 'flags', 'pressure', 'heard', 'beliefs', 'time'):
                self.assertEqual(s.get(key), last['before'].get(key), key)
            self.assert_money(s)
        self.assertFalse(s['flags'].get('rumor_arrived'))
        self.assertEqual(s['local']['resources']['pence'], 18)

    def test_player_projection_hides_private_pressure_and_unresolved_results(self):
        s = self.start()
        story = self.rt.package(s['revision'])['story']
        public = json.dumps(self.rt.surface(s), ensure_ascii=False)
        self.assertNotIn('备用铁钉', public)
        self.assertNotIn('guard_private', public)
        self.assertIn('备用铁钉', json.dumps(pressure.known(s, story, 'guard'), ensure_ascii=False))
        described = free_actions.describe(s, story, self.rt.node(s), 'day_prank',
                                         characters=self.rt.package(s['revision'])['characters'])
        self.assertNotIn('success_text', described)
        self.assertNotIn('failure_text', described)
        self.assertFalse(s['flags'].get('rumor_arrived'))


if __name__ == '__main__':
    unittest.main()
