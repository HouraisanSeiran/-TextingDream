# -*- coding: utf-8 -*-
"""检定先结算、后叙述：作者可以不写某档文本；离线用短句，在线交给模型。

临时 SQLite，不联网（provider 被打桩）。
"""
import asyncio
import json
import unittest
from unittest.mock import patch

from app import checks, scene_judgment
from app.contracts import Turn
from tests.test_checks_clock_stages import margin_story
from tests.test_checks_v2 import Base, characters_doc

BARE = {'id': 'try', 'label': '试试', 'ends_event': False, 'success_text': '',
        'check': {'attribute': 'social', 'difficulty': .5}}


def settle(story, tier, session=None):
    node = story['events'][0]
    action = node['actions'][0]
    resolved = {'config': checks.config(story), 'tier': tier, 'effect': 'standard'}
    session = session or {'flags': {}, 'check_hints': [], 'local': {'resources': {'pence': 1}}}
    return checks.consequences(session, story, characters_doc(), node, action, resolved)


class OfflineLineTests(unittest.TestCase):
    def test_unwritten_tier_gets_a_per_tier_short_line_never_the_generic_fallback(self):
        story = margin_story(action=dict(BARE, success_text=''))
        seen = {}
        for tier in ('critical', 'success', 'failure', 'disaster'):
            out = settle(story, tier)
            seen[tier] = out['text']
            self.assertEqual(out['text'], checks.OFFLINE_TIER_LINES[tier])
            self.assertEqual(out['authored_text'], '')
            self.assertNotEqual(out['text'], checks.GENERIC_FALLBACK)
        self.assertEqual(len(set(seen.values())), 4)
        # 大成功/大失败的短句要体现方向。
        self.assertIn('好', seen['critical'])
        self.assertIn('坏', seen['disaster'])

    def test_failure_fallback_still_only_feeds_heard(self):
        out = settle(margin_story(action=dict(BARE)), 'failure')
        self.assertEqual(out['fallback'], 'generic')
        self.assertEqual(out['effects'][0]['text'], checks.GENERIC_FALLBACK)
        self.assertNotEqual(out['text'], checks.GENERIC_FALLBACK)

    def test_authored_text_is_used_as_written(self):
        story = margin_story(action={'success_text': '作者成功', 'failure_text': '作者失败'})
        self.assertEqual(settle(story, 'success')['text'], '作者成功')
        out = settle(story, 'failure')
        self.assertEqual((out['text'], out['authored_text'], out['fallback']),
                         ('作者失败', '作者失败', None))
        tiered = margin_story(action={'check': {
            'attribute': 'social', 'difficulty': .5,
            'tiers': {'disaster': {'text': '作者大失败'}}}})
        out = settle(tiered, 'disaster')
        self.assertEqual((out['text'], out['authored_text']), ('作者大失败', '作者大失败'))

    def test_action_failure_text_counts_as_authored_so_no_fallback(self):
        out = settle(margin_story(action={'failure_text': '没谈成'}), 'failure')
        self.assertIsNone(out['fallback'])
        self.assertEqual(out['effects'], [])


class RuntimeNarrationTests(Base):
    story_kwargs = {}

    def setUp(self):
        self.story_kwargs = {}
        super().setUp()

    def run_bare(self, tier_dc, action=None, cfg=None):
        story = margin_story(cfg=cfg or {}, action=action or dict(BARE, check={
            'attribute': 'social', 'difficulty': tier_dc}))
        self.rt.commit_package(story, characters_doc(), 'bare')
        s = self.rt.new_session('bare', 'protagonist')
        return s

    def play(self, s, action_id='try'):
        described = self.describe(action_id, s)
        request = Turn(message=described['label'], action_id=action_id,
                       confirm=described['confirm'])
        result = self.rt.prepare_turn(s, request)
        return request, result

    def test_unwritten_action_commits_executes_and_offline_text_matches_tier(self):
        s = self.run_bare(.5)
        request, result = self.play(s)
        tier = s['last_check']['tier']
        self.assertEqual(s['last_check']['tier_label'], checks.MARGIN_FOUR_LABELS[tier])
        self.assertEqual(result['settled']['tier'], tier)
        self.assertEqual(result['settled']['authored_text'], '')
        self.assertEqual(result['outcome'], checks.OFFLINE_TIER_LINES[tier])
        from app.service import offline_surface
        self.assertIn(checks.OFFLINE_TIER_LINES[tier], offline_surface(s, result, request))

    def test_model_facing_result_has_tier_and_no_generic_or_offline_line(self):
        for dc in (2, 30):  # 易 / 难
            s = self.run_bare(.5, dict(BARE, check={'attribute': 'social', 'dc': dc}),
                              cfg={'display': 'qualitative'})
            _, result = self.play(s)
            public = self.rt.resolved_rewards(result)
            tier = s['last_check']['tier']
            self.assertEqual(public['settled']['tier'], tier)
            self.assertEqual(public['settled']['tier_label'], checks.MARGIN_FOUR_LABELS[tier])
            self.assertEqual(public['settled']['action_label'], '试试')
            self.assertEqual(public['outcome'], '')
            blob = json.dumps(public, ensure_ascii=False)
            self.assertNotIn(checks.GENERIC_FALLBACK, blob)
            for line in checks.OFFLINE_TIER_LINES.values():
                self.assertNotIn(line, blob)
            self.assertIn('不能改结果', public['settled']['rule'])
            self.assertIn('不能发奖励', public['settled']['rule'])
            # qualitative：不给数值。
            self.assertNotIn('"dc"', blob)
            self.assertNotIn('"margin"', blob)
            self.assertNotIn('"total"', blob)

    def authored_expected(self, s):
        return '作者成功' if s['last_check']['tier'] in ('critical', 'success') else '作者失败'

    def test_authored_text_reaches_the_model_unchanged(self):
        s = self.run_bare(.5, dict(BARE, success_text='作者成功', failure_text='作者失败',
                                   check={'attribute': 'social', 'dc': 2}))
        _, result = self.play(s)
        public = self.rt.resolved_rewards(result)
        expected = self.authored_expected(s)
        self.assertEqual(public['outcome'], expected)
        self.assertEqual(public['settled']['authored_text'], expected)
        self.assertEqual(result['outcome'], expected)

    def test_scene_judgment_context_carries_tier_and_hides_generic_text(self):
        s = self.run_bare(.5, dict(BARE, check={'attribute': 'social', 'dc': 30}),
                          cfg={'display': 'qualitative'})
        request, result = self.play(s)
        action = self.action('try', s)
        data = self._scene_context(s, request, result, action)
        check = data['check']
        self.assertEqual(check['tier'], s['last_check']['tier'])
        self.assertEqual(check['tier_label'], checks.MARGIN_FOUR_LABELS[check['tier']])
        self.assertEqual(check['authored_text'], '')
        self.assertEqual(data['resolved'], '')
        self.assertEqual(check['action_label'], '试试')
        blob = json.dumps(data, ensure_ascii=False)
        self.assertNotIn(checks.GENERIC_FALLBACK, blob)
        for line in checks.OFFLINE_TIER_LINES.values():
            self.assertNotIn(line, blob)
        self.assertIn('不能改结果', check['narration_rule'])
        self.assertIn('局面变好', scene_judgment.NARRATOR)
        self.assertIn('实际的不利变化', scene_judgment.NARRATOR)

    def test_scene_judgment_context_uses_authored_text(self):
        s = self.run_bare(.5, dict(BARE, success_text='作者成功', failure_text='作者失败',
                                   check={'attribute': 'social', 'dc': 2}))
        request, result = self.play(s)
        data = self._scene_context(s, request, result, self.action('try', s))
        expected = self.authored_expected(s)
        self.assertEqual(data['resolved'], expected)
        self.assertEqual(data['check']['authored_text'], expected)

    def _scene_context(self, s, request, result, action):
        story = self.package()['story']
        story['mechanics']['scene_judgment'] = {'version': 1, 'law': '测试', 'actors': {}}
        with patch.object(self.rt, 'package',
                          return_value={**self.package(), 'story': story}), \
                patch.object(self.rt, 'node', return_value=self.node(s)):
            return scene_judgment.context(self.rt, s, request, result, action)


if __name__ == '__main__':
    unittest.main()
