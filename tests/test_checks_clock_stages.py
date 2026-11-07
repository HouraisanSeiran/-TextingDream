# -*- coding: utf-8 -*-
"""判定系统：多阶段钟 / 信号 / 隐藏与开启，以及 margin_four 的失败兜底。

规格见 ``docs/check-system-v2.md`` 末尾「多阶段钟与信号」「四档兜底」两节。
全部是确定性测试：不联网、不掷随机骰（兜底测试直接喂给 ``consequences`` 一个已裁定的档位）。
"""
import asyncio
import copy
import json
import unittest
from unittest.mock import patch

from app import checks
from app.contracts import Turn
from tests.test_checks_v2 import Base, story_doc, characters_doc


def sig(signal_id, delta=1):
    return {'signal': signal_id, 'delta': delta}


def stage_checks():
    return {
        'version': 2, 'die': 'd20', 'display': 'transparent',
        'default_position': 'risky', 'default_effect': 'standard',
        'clocks': [
            {'id': 'deal', 'label': '干麦生意', 'segments': 4, 'kind': 'progress',
             'known_by': ['player'],
             'advance_on': [sig('sig_a'), sig('sig_big', 3), sig('sig_tap')],
             'stages': [
                 {'id': 's1', 'at': 1, 'label': '开了头', 'text': '第一步'},
                 {'id': 's2', 'at': 2, 'label': '半程', 'text': ''},
                 {'id': 's3', 'at': 4, 'label': '了结', 'text': '了结了'}],
             'on_full': [{'op': 'flag', 'id': 'deal_done', 'value': True}]},
            # 阶段效果互相发信号：x → ping → y → pong → x（已发过，必须停）
            {'id': 'ping', 'label': '乒', 'segments': 2, 'known_by': ['player'],
             'advance_on': [sig('sig_x')],
             'stages': [{'id': 'p1', 'at': 1, 'label': 'P',
                         'effects': [{'op': 'signal', 'id': 'sig_y'}]}]},
            {'id': 'pong', 'label': '乓', 'segments': 2, 'known_by': ['player'],
             'advance_on': [sig('sig_y')],
             'stages': [{'id': 'q1', 'at': 1, 'label': 'Q',
                         'effects': [{'op': 'signal', 'id': 'sig_x'}]}]},
            {'id': 'tide_hidden', 'label': '暗潮', 'segments': 3, 'known_by': ['player'],
             'visibility': 'hidden', 'reveal_on': {'signal': 'sig_reveal'},
             'reveal_text': '风向变了', 'advance_on': [sig('sig_whisper')]},
            {'id': 'later', 'label': '后手', 'segments': 2, 'known_by': ['player'],
             'enabled_on': {'flag': 'opened'}},
            {'id': 'gate_sig', 'label': '闸门', 'segments': 2, 'known_by': ['player'],
             'enabled_on': {'signal': 'sig_unlock'}, 'advance_on': [sig('sig_step')]},
        ],
    }


ACTIONS = [
    {'id': 'tap', 'label': '敲一下', 'ends_event': False, 'success_text': '敲了',
     'effects': [{'op': 'signal', 'id': 'sig_tap'}]},
    {'id': 'leave', 'label': '离开', 'ends_event': True, 'success_text': '我走了',
     'effects': []},
]


class StageBase(Base):
    story_kwargs = {'checks': stage_checks(), 'actions': ACTIONS}

    def emit(self, s, *ids):
        for signal_id in ids:
            self.rt.effects(s, [{'op': 'signal', 'id': signal_id}], 'test')

    def clock(self, s, clock_id):
        return checks.clock_state(s, self.package()['story'])[clock_id]

    def public(self, s):
        return {c['id']: c for c in checks.public_clocks(s, self.package()['story'])}

    def turn_surface(self, action_id):
        s = self.reload()
        described = self.describe(action_id, s)
        request = Turn(message=described['label'], action_id=action_id,
                       confirm=described['confirm'])
        return asyncio.run(self.svc.turn(s['id'], request))


class StageTests(StageBase):
    def test_signal_is_ordered_deduplicated_list(self):
        self.emit(self.s, 'sig_a', 'sig_a', 'sig_tap', 'sig_a')
        self.assertEqual(self.s['signals'], ['sig_a', 'sig_tap'])
        self.assertEqual(self.clock(self.s, 'deal')['filled'], 2)

    def test_stage_fires_once_even_when_progress_moves_back_and_forth(self):
        with patch.object(self.rt, 'effects', wraps=self.rt.effects) as spy:
            self.emit(self.s, 'sig_a')
            self.rt.effects(self.s, [{'op': 'clock', 'id': 'deal', 'delta': -1}], 'test')
            self.rt.effects(self.s, [{'op': 'clock', 'id': 'deal', 'delta': 1}], 'test')
        sources = [c.args[2] for c in spy.call_args_list if len(c.args) > 2]
        self.assertEqual(sources.count('clock:deal:stage:s1'), 1)
        self.assertEqual(self.clock(self.s, 'deal')['stages_done'], ['s1'])

    def test_one_jump_crosses_several_stages_in_order(self):
        self.emit(self.s, 'sig_big')
        row = self.clock(self.s, 'deal')
        self.assertEqual(row['filled'], 3)
        self.assertEqual(row['stages_done'], ['s1', 's2'])
        self.assertFalse(self.s['flags'].get('deal_done'))
        self.emit(self.s, 'sig_a')
        row = self.clock(self.s, 'deal')
        self.assertEqual(row['stages_done'], ['s1', 's2', 's3'])
        self.assertTrue(self.s['flags']['deal_done'])
        self.assertIsNotNone(row['full_at'])

    def test_stage_effects_that_signal_each_other_terminate(self):
        self.emit(self.s, 'sig_x')
        self.assertEqual(self.s['signals'], ['sig_x', 'sig_y'])
        self.assertEqual(self.clock(self.s, 'ping')['filled'], 1)
        self.assertEqual(self.clock(self.s, 'pong')['filled'], 1)
        self.assertEqual(self.clock(self.s, 'ping')['stages_done'], ['p1'])

    def test_unsubscribed_signal_is_recorded_without_error_and_bad_id_is_rejected(self):
        self.emit(self.s, 'nobody_listens')
        self.assertIn('nobody_listens', self.s['signals'])
        with self.assertRaises(ValueError):
            self.emit(self.s, 'bad id!')

    def test_hidden_clock_stays_out_of_every_player_projection_until_revealed(self):
        self.emit(self.s, 'sig_whisper')
        self.assertEqual(self.clock(self.s, 'tide_hidden')['filled'], 1)
        self.assertNotIn('tide_hidden', self.public(self.s))
        dumped = json.dumps(self.rt.surface(self.s), ensure_ascii=False)
        for secret in ('tide_hidden', '暗潮', 'sig_whisper', 'sig_reveal', '风向变了',
                       'sig_tap', 'later', 'gate_sig', '了结', '半程'):
            self.assertNotIn(secret, dumped, secret)
        before = copy.deepcopy(self.s)
        self.emit(self.s, 'sig_reveal')
        row = self.public(self.s)['tide_hidden']
        self.assertEqual((row['label'], row['filled']), ('暗潮', 1))
        rows = checks.clock_notices(before, self.s, self.package()['story'])
        self.assertEqual(rows, [{'kind': 'reveal', 'clock_label': '暗潮',
                                 'text': '风向变了'}])

    def test_unreached_stage_names_are_blank_in_the_public_row(self):
        self.emit(self.s, 'sig_a')
        row = self.public(self.s)['deal']
        self.assertEqual(row['stages'], [{'at': 1, 'label': '开了头', 'reached': True},
                                         {'at': 2, 'label': '', 'reached': False},
                                         {'at': 4, 'label': '', 'reached': False}])
        self.assertEqual(row['stage_label'], '开了头')
        self.assertNotIn('stage_label', self.public(self.s)['ping'])
        author = {c['id']: c for c in checks.authority_clocks(self.s, self.package()['story'])}
        self.assertIn('tide_hidden', author)
        self.assertEqual(author['deal']['stages'][2]['label'], '了结')

    def test_flag_enabled_clock_waits_for_its_flag(self):
        self.assertNotIn('later', self.public(self.s))
        self.rt.effects(self.s, [{'op': 'clock', 'id': 'later', 'delta': 1}], 'test')
        self.assertEqual(self.clock(self.s, 'later')['filled'], 0)
        self.rt.effects(self.s, [{'op': 'flag', 'id': 'opened', 'value': True}], 'test')
        self.assertIn('later', self.public(self.s))
        self.rt.effects(self.s, [{'op': 'clock', 'id': 'later', 'delta': 1}], 'test')
        self.assertEqual(self.clock(self.s, 'later')['filled'], 1)

    def test_signal_enabled_clock_ignores_steps_before_unlock(self):
        self.emit(self.s, 'sig_step')
        self.assertEqual(self.clock(self.s, 'gate_sig')['filled'], 0)
        self.assertNotIn('gate_sig', self.public(self.s))
        before = copy.deepcopy(self.s)
        self.emit(self.s, 'sig_unlock')
        self.assertIn('gate_sig', self.public(self.s))
        rows = checks.clock_notices(before, self.s, self.package()['story'])
        self.assertEqual([(r['kind'], r['clock_label']) for r in rows], [('enable', '闸门')])
        # sig_step 已经发过：信号去重，不会补推（作者要“解锁后再算”就用新信号名）。
        self.assertEqual(self.clock(self.s, 'gate_sig')['filled'], 0)

    def test_snapshot_restore_replays_the_same_stage_once(self):
        snapshot = self.rt.snapshot(self.s)
        self.emit(self.s, 'sig_a')
        self.assertEqual(self.clock(self.s, 'deal')['stages_done'], ['s1'])
        self.s.clear()
        self.s.update(copy.deepcopy(snapshot))
        self.assertNotIn('sig_a', self.s.get('signals', []))
        self.assertEqual(self.clock(self.s, 'deal')['stages_done'], [])
        self.emit(self.s, 'sig_a')
        self.assertEqual(self.clock(self.s, 'deal')['stages_done'], ['s1'])
        self.assertEqual(self.clock(self.s, 'deal')['filled'], 1)

    def test_clock_notices_shape_and_text_rules(self):
        story = self.package()['story']
        before = copy.deepcopy(self.s)
        self.emit(self.s, 'sig_big')
        rows = checks.clock_notices(before, self.s, story)
        # s1 有文字，s2 没有文字：只报 s1。
        self.assertEqual(rows, [{'kind': 'stage', 'clock_label': '干麦生意',
                                 'text': '第一步'}])
        self.assertEqual(checks.clock_notices(self.s, self.s, story), [])

    def test_notices_reach_the_surface_once_after_a_turn(self):
        first = self.turn_surface('tap')
        self.assertEqual(first['clock_notices'],
                         [{'kind': 'stage', 'clock_label': '干麦生意', 'text': '第一步'}])
        self.assertNotIn('quest_notices', first)
        self.assertNotIn('clock_notices', self.rt.surface(self.reload()))


class LegacySurfaceTests(Base):
    def test_old_package_gets_no_new_keys(self):
        surface = self.rt.surface(self.reload())
        self.assertNotIn('clock_notices', surface)
        self.assertNotIn('quest_notices', surface)
        self.assertNotIn('signals', self.reload())
        for row in surface['clocks']:
            self.assertEqual(set(row), {'id', 'label', 'segments', 'filled', 'kind'})


def margin_story(**overrides):
    cfg = copy.deepcopy(story_doc()['mechanics']['checks'])
    cfg['tier_mode'] = 'margin_four'
    cfg.update(overrides.pop('cfg', {}))
    action = {'id': 'try', 'label': '试试', 'ends_event': False, 'success_text': '成了',
              'check': {'attribute': 'social', 'difficulty': .5}}
    action.update(overrides.pop('action', {}))
    return story_doc(checks=cfg, actions=[action,
                                          {'id': 'leave', 'label': '离开', 'ends_event': True,
                                           'success_text': '走了', 'effects': []}])


class FallbackTests(unittest.TestCase):
    def run_fallback(self, story, session, tier='failure'):
        node = story['events'][0]
        action = node['actions'][0]
        resolved = {'config': checks.config(story), 'tier': tier, 'effect': 'standard'}
        return checks.consequences(session, story, characters_doc(), node, action, resolved)

    @staticmethod
    def fresh():
        return {'flags': {}, 'check_hints': [], 'local': {'resources': {'pence': 18}}}

    def test_text_source_order_hint_then_package_then_generic(self):
        hints = [{'id': 'h1', 'text': '线索一'}, {'id': 'h2', 'text': '线索二'}]
        story = margin_story(action={'fallback_hints': hints},
                             cfg={'fallback_text': '包级兜底'})
        session = self.fresh()
        seen = []
        for _ in range(4):
            out = self.run_fallback(story, session)
            seen.append((out['fallback'], out['effects'][0]['text']))
            session['check_hints'] += out['hints']
        self.assertEqual(seen, [('hint', '线索一'), ('hint', '线索二'),
                                ('package', '包级兜底'), ('package', '包级兜底')])
        bare = margin_story(action={'fallback_hints': hints})
        session = {**self.fresh(), 'check_hints': ['h1', 'h2']}
        out = self.run_fallback(bare, session)
        self.assertEqual((out['fallback'], out['effects'][0]['text']),
                         ('generic', checks.GENERIC_FALLBACK))

    def test_fallback_gives_only_a_heard_line_never_goods_or_tier_changes(self):
        story = margin_story(cfg={'fallback_text': '包级兜底'})
        for tier in ('failure', 'disaster'):
            out = self.run_fallback(story, self.fresh(), tier)
            self.assertEqual(out['tier'], tier)
            self.assertEqual(out['effects'],
                             [{'op': 'information', 'text': '包级兜底',
                               'known_by': ['player'], 'confirmed': False}])
            self.assertEqual((out['relationships'], out['extra_hours'], out['clocks']),
                             ([], 0, []))

    def test_author_written_failure_tier_suppresses_the_fallback(self):
        story = margin_story(cfg={'fallback_text': '包级兜底'}, action={
            'check': {'attribute': 'social', 'difficulty': .5,
                      'tiers': {'failure': {'text': '作者写的失败'},
                                'disaster': {'effects': [
                                    {'op': 'flag', 'id': 'oops', 'value': True}]}}}})
        out = self.run_fallback(story, self.fresh(), 'failure')
        self.assertIsNone(out['fallback'])
        self.assertEqual((out['text'], out['effects']), ('作者写的失败', []))
        out = self.run_fallback(story, self.fresh(), 'disaster')
        self.assertIsNone(out['fallback'])
        self.assertEqual([e['op'] for e in out['effects']], ['flag'])

    def test_package_validation_does_not_require_a_failure_route(self):
        # 作者没必要给每个检定都写失败后果：缺失败出路也能提交。
        chars = characters_doc()
        checks.validate_package(margin_story(), chars)
        checks.validate_package(margin_story(cfg={'fallback_text': '兜底'}), chars)
        checks.validate_package(
            margin_story(action={'fallback_hints': [{'id': 'h', 'text': '提示'}]}), chars)
        checks.validate_package(margin_story(action={'check': {
            'attribute': 'social', 'difficulty': .5,
            'tiers': {'failure': {'text': '失败了'}}}}), chars)

    def test_legacy_five_never_needs_a_route(self):
        story = story_doc()
        self.assertNotEqual(story['mechanics']['checks'].get('tier_mode'), 'margin_four')
        checks.validate_package(story, characters_doc())


class SignalValidationTests(unittest.TestCase):
    def story(self, effect_id, **cfg):
        checks_cfg = stage_checks()
        checks_cfg.update(cfg)
        actions = [{'id': 'tap', 'label': '敲', 'ends_event': False, 'success_text': '敲了',
                    'effects': [{'op': 'signal', 'id': effect_id}]},
                   {'id': 'leave', 'label': '离开', 'ends_event': True,
                    'success_text': '走了', 'effects': []}]
        return story_doc(checks=checks_cfg, actions=actions)

    def test_signal_effect_needs_a_subscriber(self):
        checks.validate_package(self.story('sig_tap'), characters_doc())
        with self.assertRaises(ValueError):
            checks.validate_package(self.story('sig_nobody'), characters_doc())

    def test_quest_subscription_counts(self):
        story = self.story('sig_for_quest')
        story['mechanics']['quests'] = {'quests': [
            {'id': 'q', 'enabled_on': {'signal': 'sig_for_quest'}}]}
        checks.validate_package(story, characters_doc())
        self.assertIn('sig_for_quest', checks.referenced_signals(story))

    def test_declared_table_restricts_effects_and_subscriptions(self):
        declared = [{'id': s} for s in ('sig_tap', 'sig_a', 'sig_big', 'sig_x', 'sig_y',
                                        'sig_whisper', 'sig_reveal', 'sig_unlock',
                                        'sig_step')]
        checks.validate_package(self.story('sig_tap', signals=declared), characters_doc())
        with self.assertRaises(ValueError):
            checks.validate_package(self.story('sig_tap', signals=declared[1:]),
                                    characters_doc())

    def test_invalid_signal_id_is_rejected_by_the_schema(self):
        cfg = stage_checks()
        cfg['clocks'][0]['advance_on'] = [sig('has space')]
        with self.assertRaises(ValueError):
            checks.ChecksConfig.model_validate(cfg)


if __name__ == '__main__':
    unittest.main()
