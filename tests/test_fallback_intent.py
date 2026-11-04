# -*- coding: utf-8 -*-
"""未匹配意图的有界兜底（``mechanics.adventure.fallback``）。

全部离线、私有临时库；世界由测试**显式** ``commit_package`` 创建（空世界启动是产品行为，
不依赖任何自动加载）。检定结果用 ``patch('app.runtime.resolve_check')`` 固定成功/失败，
公式与种子本身不变。
"""
import asyncio
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import adventure_actions as A
from app import drama, free_actions
from app.contracts import Turn
from app.service import Service
from app.storage import Store

HINT_1 = '石缝里卡着半片湿透的麻袋布。'
HINT_2 = '台阶边的苔藓被人踩掉了一道。'
SECRET_HINT = '匣底压着一张欠条。'
ASK_HINT = '米商说昨夜有船没点灯。'


def fallback_block(**over):
    block = {
        'enabled': True,
        'kinds': {'observe': {'difficulty': 0.4}},
        'hints': [
            {'id': 'plaza_1', 'target': {'kind': 'place', 'id': 'plaza'},
             'kinds': ['observe'], 'text': HINT_1},
            {'id': 'plaza_2', 'target': {'kind': 'place', 'id': 'plaza'},
             'kinds': ['observe'], 'text': HINT_2},
            {'id': 'cache_1', 'target': {'kind': 'object', 'id': 'cache'},
             'kinds': ['observe'], 'text': SECRET_HINT},
            {'id': 'merchant_1', 'target': {'kind': 'npc', 'id': 'merchant'},
             'kinds': ['ask'], 'text': ASK_HINT},
        ],
    }
    block.update(over)
    return block


def story_doc(fallback=True, adventure=True, extra_actions=()):
    mechanics = {'local': {'resources': [{'id': 'coin', 'name': '铜币', 'unit': '枚',
                                          'initial': 10, 'maximum': 50}],
                           'turn_hours': 1, 'travel_hours': 2}}
    if adventure:
        mechanics['adventure'] = {'version': 1}
        if fallback is not None and fallback is not False:
            mechanics['adventure']['fallback'] = (fallback_block() if fallback is True
                                                  else fallback)
    return {
        'id': 'fallback-test', 'title': '兜底测试', 'premise': '测试用的小世界。',
        'character_package_id': 'fallback-test-characters',
        'locations': [
            {'id': 'plaza', 'name': '米市街', 'description': '', 'neighbors': ['gate', 'vault'],
             'scenes': []},
            {'id': 'gate', 'name': '上闸', 'description': '', 'neighbors': ['plaza'], 'scenes': []},
            {'id': 'vault', 'name': '粮仓深处', 'description': '', 'neighbors': ['plaza'],
             'scenes': [], 'visibility': 'author'},
        ],
        'events': [
            {'id': 'root_event', 'title': '米市街的清晨', 'location_id': 'plaza',
             'participants': ['player', 'merchant'], 'player_goal': '弄清米价',
             'player_enters': True, 'next_events': [], 'entry_flags': {},
             'exit_flag': 'done_root', 'max_turns': 30,
             'actions': [{'id': 'look', 'label': '看看街面', 'ends_event': False,
                          'success_text': '我先看了看街面。'},
                         {'id': 'done_talk', 'label': '谈完了', 'ends_event': True,
                          'success_text': '这次谈话告一段落。'}] + list(extra_actions)},
        ],
        'items': [
            {'id': 'ledger', 'name': '账页', 'description': '', 'authority': 'engine',
             'location_id': 'plaza'},
            {'id': 'cache', 'name': '夹层里的匣子', 'description': '', 'authority': 'engine',
             'location_id': 'plaza', 'visibility': 'author'},
        ],
        'mechanics': mechanics,
    }


def characters_doc():
    axes = {'talent': 50, 'strength': 45, 'agility': 55, 'wisdom': 60,
            'social': 65, 'resilience': 50}
    return {'id': 'fallback-test-characters', 'title': '测试角色', 'characters': [
        {'id': 'player', 'name': '我', 'role': '主角', 'location_id': 'plaza',
         'personality': {'谨慎': 0.6}, 'state': {'疲劳': 0.1}, 'attributes': dict(axes)},
        {'id': 'merchant', 'name': '米商', 'role': '次要角色', 'location_id': 'plaza',
         'personality': {'社交': 0.6}, 'state': {}, 'attributes': dict(axes)},
        {'id': 'spy', 'name': '暗处的人', 'role': '次要角色', 'location_id': 'plaza',
         'visibility': 'author', 'personality': {}, 'state': {}, 'attributes': dict(axes)},
    ]}


def dumped(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def fingerprint(session):
    return dumped({k: v for k, v in session.items() if k != 'state_version'})


def forced(success):
    real = drama.resolve_check

    def fake(*args):
        return {**real(*args), 'success': success}
    return patch('app.runtime.resolve_check', side_effect=fake)


class Base(unittest.TestCase):
    story_kwargs = {}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.svc = Service(Store(Path(self.tmp.name) / 'fallback.sqlite3'), Path(self.tmp.name))
        self.svc.provider.configure({'offline': True})
        self.rt = self.svc.runtime
        self.rt.commit_package(story_doc(**self.story_kwargs), characters_doc(), '兜底测试')
        self.s = self.rt.new_session('兜底', 'protagonist')

    def reload(self):
        return self.svc.store.session(self.s['id'])

    def node(self, s):
        return self.rt.node(s) if s['active'] else None

    def suggest(self, text, s=None, characters=True):
        s = s or self.reload()
        p = self.rt.package(s['revision'])
        return free_actions.suggest(s, p['story'], self.node(s), text,
                                    characters=p['characters'] if characters else None)

    def turn(self, text, action_id, confirm):
        return asyncio.run(self.svc.turn(self.s['id'], Turn(
            message=text, action_id=action_id, confirm=confirm)))

    def attempt(self, text, success=True):
        row = self.suggest(text)['matched'][0]
        with forced(success):
            self.turn(text, row['action_id'], row['confirm'])
        return row, self.reload()


class LegacyTests(Base):
    story_kwargs = {'fallback': False}

    def test_package_without_fallback_block_is_unchanged(self):
        out = self.suggest('仔细观察一下这条街')
        self.assertEqual(out, {'matched': [], 'ambiguous': False, 'unjudged': True,
                               'note': '没有匹配到已配置的动作；引擎不裁定未配置的行动，'
                                       '这句话只作为台词或描述，不改变状态'})
        s = self.reload()
        with self.assertRaises(ValueError):
            self.turn('看', 'fallback:observe:place:plaza', 'x' * 32)
        self.assertEqual(fingerprint(s), fingerprint(self.reload()))

    def test_static_fallback_prefix_is_allowed_when_block_absent(self):
        story = story_doc(fallback=False, extra_actions=[
            {'id': 'fallback:old', 'label': '旧动作', 'ends_event': False}])
        self.rt.commit_package(story, characters_doc(), '旧包')   # 不报错


class DisabledTests(Base):
    story_kwargs = {'fallback': fallback_block(enabled=False)}

    def test_disabled_block_behaves_like_absent(self):
        out = self.suggest('仔细观察一下这条街')
        self.assertTrue(out['unjudged'])
        self.assertEqual(out['matched'], [])
        self.assertNotIn('fallback', out)


class NoAdventureTests(Base):
    story_kwargs = {'adventure': False}

    def test_legacy_package_without_adventure(self):
        out = self.suggest('仔细观察一下这条街')
        self.assertEqual((out['matched'], out['unjudged']), ([], True))
        self.assertNotIn('fallback', out)


class CandidateTests(Base):
    def test_unclassified_intent_stays_unjudged(self):
        for text in ('今天天气真好', '我不想偷偷溜走', '别问了'):
            out = self.suggest(text)
            self.assertTrue(out['unjudged'], text)
            self.assertEqual(out['matched'], [], text)
            self.assertNotIn('fallback', out, text)

    def test_classify_is_deterministic(self):
        self.assertEqual(A.classify('四处打量一下'), 'observe')
        self.assertEqual(A.classify('向米商打听消息'), 'ask')
        self.assertEqual(A.classify('求他便宜点'), 'persuade')
        self.assertEqual(A.classify('偷偷溜到后面'), 'sneak')
        self.assertEqual(A.classify('砸开门'), 'force')
        self.assertEqual(A.classify('找地方歇歇脚'), 'rest')
        self.assertIsNone(A.classify('唱一首歌'))

    def test_candidate_is_whitelisted_and_writes_nothing(self):
        before = self.reload()
        out = self.suggest('仔细观察一下这条街', before)
        self.assertEqual(fingerprint(before), fingerprint(self.reload()))
        self.assertEqual(before['state_version'], self.reload()['state_version'])
        self.assertFalse(out['unjudged'])
        self.assertTrue(out['fallback'])
        self.assertEqual(len(out['matched']), 1)
        row = out['matched'][0]
        self.assertEqual(row['action_id'], 'fallback:observe:place:plaza')
        self.assertEqual(row['check'], {'attribute': 'wisdom', 'difficulty': 0.4})
        self.assertEqual(row['duration_hours'], 1)
        self.assertEqual(row['costs'], [])
        self.assertFalse(row['ends_event'])
        self.assertEqual(set(row), {'action_id', 'label', 'costs', 'duration_hours', 'check',
                                    'ends_event', 'intent_aliases', 'kind', 'fallback_kind',
                                    'target', 'repeat', 'supported', 'confirm', 'match'})

    def test_target_resolution_only_uses_visible_targets(self):
        row = self.suggest('向米商打听一下')['matched'][0]
        self.assertEqual(row['action_id'], 'fallback:ask:npc:merchant')
        row = self.suggest('翻找账页')['matched'][0]
        self.assertEqual(row['action_id'], 'fallback:observe:object:ledger')
        # 作者隐藏的物件/人物/地点：解析不到 → 落回当前地点，名字也不出现。
        for text in ('观察夹层里的匣子', '观察暗处的人', '观察粮仓深处'):
            out = self.suggest(text)
            self.assertEqual(out['matched'][0]['action_id'], 'fallback:observe:place:plaza')
            for hidden in ('cache', 'spy', 'vault', '夹层', '暗处', '粮仓'):
                self.assertNotIn(hidden, dumped(out['matched']))
        s = self.reload()
        for action_id in ('fallback:observe:object:cache', 'fallback:ask:npc:spy',
                          'fallback:observe:place:vault', 'fallback:steal:place:plaza'):
            with self.assertRaises(ValueError):
                self.turn('看', action_id, 'x' * 32)
        self.assertEqual(fingerprint(s), fingerprint(self.reload()))

    def test_hints_never_leak_into_candidates_or_confirm(self):
        s = self.reload()
        p = self.rt.package(s['revision'])
        texts = []
        for text in ('仔细观察一下这条街', '向米商打听', '观察夹层里的匣子', '翻找账页'):
            out = self.suggest(text)
            texts.append(dumped(out))
            for row in out['matched']:
                texts.append(dumped(free_actions.describe(
                    s, p['story'], self.node(s), row['action_id'],
                    characters=p['characters'])))
        blob = ''.join(texts)
        for secret in (HINT_1, HINT_2, SECRET_HINT, ASK_HINT, '半片', '欠条'):
            self.assertNotIn(secret, blob)
        surface = dumped(self.rt.surface(s))
        for secret in (HINT_1, SECRET_HINT, ASK_HINT):
            self.assertNotIn(secret, surface)

    def test_web_style_call_without_characters_still_offers_place(self):
        # /intent 现在只传 (session, story, node, text)：没有人物文档时人物目标不出现。
        out = self.suggest('向米商打听一下', characters=False)
        self.assertEqual(out['matched'][0]['action_id'], 'fallback:ask:place:plaza')


class ConfirmTests(Base):
    def test_missing_and_stale_confirm_are_refused_before_side_effects(self):
        before = self.reload()
        row = self.suggest('仔细观察一下这条街', before)['matched'][0]
        with self.assertRaises(ValueError):
            self.turn('看', row['action_id'], None)
        self.assertEqual(fingerprint(before), fingerprint(self.reload()))
        self.svc.store.save_session(copy.deepcopy(before))        # state_version += 1
        moved = self.reload()
        with self.assertRaises(ValueError):
            self.turn('看', row['action_id'], row['confirm'])
        self.assertEqual(fingerprint(moved), fingerprint(self.reload()))


class SettlementTests(Base):
    def assert_whitelist_only(self, before, after, flag):
        self.assertEqual(after['inventory'], before['inventory'])
        self.assertEqual(after['local']['resources'], before['local']['resources'])
        self.assertEqual(after['local']['ledger'], before['local']['ledger'])
        self.assertEqual(after['facts'], before['facts'])
        self.assertEqual(after.get('rewards'), before.get('rewards'))
        self.assertEqual(after['active']['node'], before['active']['node'])
        self.assertEqual(after['active']['actions_done'], before['active']['actions_done'])
        self.assertEqual(after['completed'], before['completed'])
        new_flags = {k: v for k, v in after['flags'].items() if before['flags'].get(k) != v}
        self.assertEqual(new_flags, {flag: True})
        self.assertEqual(after['time'], before['time'] + 1)

    def test_success_gives_next_author_hint_as_unconfirmed_heard(self):
        before = self.reload()
        row, after = self.attempt('仔细观察一下这条街', success=True)
        self.assert_whitelist_only(before, after, 'fallback_tried:observe:place:plaza')
        self.assertIn(HINT_1, [r['text'] for r in after['heard']])
        self.assertNotIn(HINT_1, [r['text'] for r in after['facts']])
        self.assertNotIn(HINT_2, dumped(after))
        self.assertIn(HINT_1, after['active']['turns'][-1]['reply'])   # 离线正文
        self.assertEqual(after.get('development', {}), before.get('development', {}))

    def test_failure_gives_no_information(self):
        before = self.reload()
        _, after = self.attempt('仔细观察一下这条街', success=False)
        self.assert_whitelist_only(before, after, 'fallback_tried:observe:place:plaza')
        self.assertEqual(after['heard'], before['heard'])

    def test_relationship_is_bounded_and_negative_only_on_witnessed_failure(self):
        _, after = self.attempt('求米商便宜点', success=False)
        trust = after['development']['merchant']['relationships']['player']['trust']
        self.assertAlmostEqual(trust, 0.45)
        _, after = self.attempt('偷偷溜到米商背后', success=True)
        self.assertAlmostEqual(
            after['development']['merchant']['relationships']['player']['trust'], 0.45)
        _, after = self.attempt('砸开账页', success=False)
        self.assertAlmostEqual(
            after['development']['merchant']['relationships']['player']['trust'], 0.40)
        self.assertNotIn('spy', after.get('development', {}))      # 隐藏人物不算目击者
        _, after = self.attempt('向米商打听', success=False)
        self.assertAlmostEqual(
            after['development']['merchant']['relationships']['player']['trust'], 0.40)

    def test_persuade_success_is_capped(self):
        _, after = self.attempt('说服米商', success=True)
        self.assertAlmostEqual(
            after['development']['merchant']['relationships']['player']['trust'], 0.55)

    def test_repeat_rule_is_harder_and_pool_is_finite(self):
        first, _ = self.attempt('仔细观察一下这条街', success=True)
        out = self.suggest('仔细观察一下这条街')
        again = out['matched'][0]
        self.assertTrue(again['repeat'])
        self.assertEqual(again['check']['difficulty'], 0.6)
        self.assertIn('repeat_notice', again)
        self.assertNotEqual(again['confirm'], first['confirm'])
        _, after = self.attempt('仔细观察一下这条街', success=True)
        self.assertIn(HINT_2, [r['text'] for r in after['heard']])
        heard = list(after['heard'])
        _, after = self.attempt('仔细观察一下这条街', success=True)
        self.assertEqual(after['heard'], heard)                     # 池空：无新信息
        self.assertIn(A.FALLBACK_EMPTY_TEXT, after['active']['turns'][-1]['reply'])
        self.assertEqual(len(after['fallback_log']), 3)

    def test_repeat_persuade_does_not_farm_trust(self):
        self.attempt('说服米商', success=True)
        _, after = self.attempt('说服米商', success=True)
        self.assertAlmostEqual(
            after['development']['merchant']['relationships']['player']['trust'], 0.55)

    def test_no_active_event_uses_local_path_with_same_whitelist(self):
        self.turn('结束', 'done_talk', None)
        s = self.reload()
        self.assertIsNone(s['active'])
        row = self.suggest('仔细观察一下这条街')['matched'][0]
        with forced(True):
            view = self.turn('看', row['action_id'], row['confirm'])
        after = self.reload()
        self.assertEqual(after['state_version'], s['state_version'] + 1)
        self.assertIn(HINT_1, [r['text'] for r in after['heard']])
        self.assertEqual(after['facts'], s['facts'])
        self.assertEqual(after['time'], s['time'] + 1)
        self.assertEqual(view['local_result']['kind'], 'fallback')


class RollbackTests(Base):
    def test_rollback_restores_flag_log_heard_and_trust(self):
        before = self.reload()
        self.attempt('仔细观察一下这条街', success=True)
        self.attempt('说服米商', success=True)
        with forced(True):
            self.turn('结束', 'done_talk', None)
        done = self.reload()
        self.assertTrue(done['flags']['fallback_tried:observe:place:plaza'])
        restored = self.rt.rollback(done, done['archives'][-1]['id'])
        for key in ('flags', 'heard', 'facts', 'development'):
            self.assertEqual(restored.get(key), before.get(key), key)
        self.assertEqual(restored.get('fallback_log'), before.get('fallback_log'))
        # 回滚后同一尝试又是「首次」，提示池从头开始。
        row = self.suggest('仔细观察一下这条街')['matched'][0]
        self.assertFalse(row['repeat'])
        self.assertEqual(row['check']['difficulty'], 0.4)


class ValidationTests(Base):
    def test_static_action_cannot_take_fallback_prefix(self):
        story = story_doc(extra_actions=[{'id': 'fallback:observe:place:plaza',
                                          'label': '冒充', 'ends_event': False}])
        with self.assertRaises(ValueError):
            self.rt.commit_package(story, characters_doc(), '冒用前缀')

    def test_bad_config_is_refused(self):
        for bad in (fallback_block(relationship_delta=0.2),
                    fallback_block(kinds={'observe': {'attribute': '魔法'}}),
                    fallback_block(kinds={'rest': {'attribute': 'wisdom'}}),
                    fallback_block(kinds={'steal': {}}),
                    fallback_block(hints=[{'id': 'x', 'target': {'kind': 'place', 'id': 'nowhere'},
                                           'text': 'a'}]),
                    fallback_block(surprise=True)):
            with self.assertRaises(ValueError):
                self.rt.commit_package(story_doc(fallback=bad), characters_doc(), '坏配置')


if __name__ == '__main__':
    unittest.main()
