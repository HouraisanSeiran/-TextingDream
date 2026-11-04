# -*- coding: utf-8 -*-
"""判定系统 v2（d20）专项测试。

覆盖规格 ``docs/check-system-v2.md`` 的每一条硬约定：

* 开启与兼容：没有 ``mechanics.checks`` 的旧包逐字节不变；v1 的
  ``attribute_v1`` 记录仍与 v2 的 ``d20_v2`` 记录并存。
* 数值：属性修正、疲劳、因素夹取、DC 换算与夹取、确定性 d20、优势/劣势。
* 五档：三个处境 × 天然 1/20 优先；布尔兼容。
* 效果与档位后果：效果升档、``tiers`` 覆盖、默认代价按列表顺序取第一条可执行、
  setback 不软锁、disaster 危险钟。
* 钟：进度/危险钟推进、满格 ``on_full`` 恰好一次、满格后不变、危险钟不重复加、
  隐藏钟不进投影、随快照回滚。
* 社交：底线拒绝（不掷骰、零副作用）、诉求减 DC、信任调整、目标不在场。
* 自动成功：空条件不能无条件成功。
* 因素：封闭清单、由引擎判定、隐藏因素不进投影。
* 察觉：主检定后的察觉检定、目击集合替换、未察觉者不记忆、不说「确定没人看到」。
* 重试与加码：refuse/harder、凭据含 push、付不起零副作用。
* 公开投影：``last_check`` / ``clocks``、qualitative 隐藏数值、给模型的上下文只给档位。

所有测试只用临时根 + 临时 SQLite；不碰正式 ``data/``、``StoryPackage/``、
``character_packages/``，不启动服务，不联网（``offline: True`` 且 provider 被打桩）。
"""
import asyncio
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import attributes, checks, free_actions, npc_cards
from app.contracts import Turn
from app.service import Service
from app.storage import Store


def axes(value=50, **overrides):
    row = {k: value for k in attributes.AXES}
    row.update(overrides)
    return row


def story_doc(**overrides):
    """一个最小 v2 包：一个地点、一名 NPC、四个动作（社交/孤注/隐匿/离开）。"""
    story = {
        'id': 'v2_test', 'title': '判定 v2 测试', 'premise': '测试用短篇',
        'worldview': {'premise': '测试用短篇'},
        'character_package_id': 'v2_test_cast',
        'locations': [{'id': 'hall', 'name': '厅堂', 'description': '厅堂',
                       'neighbors': [], 'scenes': [], 'tags': ['town']}],
        'items': [{'id': 'manifest', 'name': '运货单', 'location_id': 'hall'}],
        'events': [{
            'id': 'open', 'title': '开场', 'location_id': 'hall',
            'participants': ['player', 'broker'], 'player_enters': True,
            'player_goal': '谈成', 'next_events': [], 'entry_flags': {},
            'exit_flag': 'done', 'max_turns': 20,
            'actions': [
                {'id': 'pitch', 'label': '谈买卖', 'ends_event': False,
                 'success_text': '谈成了', 'failure_text': '没谈成',
                 'check': {'attribute': 'social', 'difficulty': .5,
                           'social': {'target': 'broker', 'appeals': ['profit'],
                                      'violates': []},
                           'clock': {'id': 'sway'},
                           'danger_clock': {'id': 'suspicion'},
                           'auto': {'max_dc': 6}}},
                {'id': 'bully', 'label': '硬抢', 'ends_event': False,
                 'success_text': '抢到了', 'failure_text': '没抢到',
                 'check': {'attribute': 'strength', 'difficulty': .5,
                           'position': 'desperate',
                           'social': {'target': 'broker', 'appeals': [],
                                      'violates': ['theft']}}},
                {'id': 'sneak', 'label': '悄悄下手', 'ends_event': False,
                 'success_text': '得手了', 'failure_text': '被发现了',
                 'check': {'attribute': 'agility', 'difficulty': .5,
                           'concealed': {'observers': 'present',
                                         'notice_attribute': 'wisdom'}}},
                {'id': 'leave', 'label': '离开', 'ends_event': True,
                 'success_text': '我走了', 'effects': []},
            ]}],
        'mechanics': {
            'attributes': attributes.specification(),
            'local': {'turn_hours': 0, 'travel_hours': 1, 'resources': [
                {'id': 'pence', 'name': '便士', 'unit': '便士', 'initial': 18,
                 'maximum': 1000}]},
            'checks': {
                'version': 2, 'die': 'd20', 'display': 'transparent',
                'default_position': 'risky', 'default_effect': 'standard',
                'factors': [
                    {'id': 'manifest', 'label': '你拿着运货单', 'mod': 2,
                     'when': {'kind': 'item', 'id': 'manifest'}},
                    {'id': 'secret', 'label': '他知道你的秘密', 'mod': -3,
                     'visibility': 'hidden',
                     'when': {'kind': 'flag', 'id': 'secret_known', 'value': True}},
                ],
                'push': [
                    {'id': 'grease', 'label': '多塞两便士', 'cost': {'pence': 2},
                     'bonus': 2},
                    {'id': 'favor', 'label': '动用人情',
                     'relationship': {'target': 'check_target', 'delta': -0.1},
                     'bonus': 3},
                ],
                'clocks': [
                    {'id': 'sway', 'label': '说服行会', 'segments': 4,
                     'kind': 'progress', 'known_by': ['player'],
                     'on_full': [{'op': 'flag', 'id': 'guild_convinced',
                                  'value': True}]},
                    {'id': 'suspicion', 'label': '守卫起疑', 'segments': 4,
                     'kind': 'danger', 'known_by': ['player']},
                    {'id': 'hidden_clock', 'label': '暗中的钟', 'segments': 3,
                     'kind': 'progress', 'known_by': ['broker']},
                ],
                'social': {'broker': {'interests': ['profit', 'reputation'],
                                      'boundaries': ['family', 'theft'],
                                      'trust_weight': 10,
                                      'refusal_text': '这触到了他的底线'}},
                'default_costs': [{'kind': 'time', 'hours': 1}],
                'retry': {'same_approach': 'refuse'},
            },
        },
    }
    for key, value in overrides.items():
        if key == 'checks':
            story['mechanics']['checks'] = value
        elif key == 'actions':
            story['events'][0]['actions'] = value
        elif key == 'no_checks':
            story['mechanics'].pop('checks', None)
        else:
            story[key] = value
    return story


def characters_doc():
    return {'id': 'v2_test_cast', 'title': '测试人物', 'characters': [
        {'id': 'player', 'name': '我', 'public_name': '我', 'role': '主角',
         'location_id': 'hall', 'personality': {}, 'state': {},
         'attributes': axes(60)},
        {'id': 'broker', 'name': '粮商', 'public_name': '粮商', 'role': '次要角色',
         'location_id': 'hall', 'personality': {'谨慎': .6}, 'state': {},
         'attributes': axes(50)},
    ]}


class Base(unittest.TestCase):
    story_kwargs = {}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.svc = Service(Store(self.root / 'v2.sqlite3'), self.root)
        self.svc.provider.configure({'offline': True})
        self.rt = self.svc.runtime
        self.story = story_doc(**self.story_kwargs)
        self.characters = characters_doc()
        self.rt.commit_package(self.story, self.characters, 'v2 测试')
        self.s = self.rt.new_session('v2 测试', 'protagonist')
        # 一切模型调用都必须失败：v2 不依赖模型裁定任何状态。
        patch.object(self.svc.provider, 'complete',
                     side_effect=AssertionError('network call')).start()
        self.addCleanup(patch.stopall)

    # ---- 工具
    def reload(self, s=None):
        return self.svc.store.session((s or self.s)['id'])

    def node(self, s=None):
        return self.rt.node(s or self.s)

    def action(self, action_id, s=None):
        return next(a for a in self.node(s)['actions'] if a['id'] == action_id)

    def package(self):
        return self.rt.package()

    def describe(self, action_id, s=None, push=None):
        return free_actions.describe(s or self.reload(), self.package()['story'],
                                     self.node(s), action_id,
                                     characters=self.package()['characters'], push=push)

    def do(self, action_id, s=None, push=None, message=None):
        s = s or self.reload()
        described = self.describe(action_id, s, push)
        request = Turn(message=message or described['label'], action_id=action_id,
                       confirm=described['confirm'], push=push)
        asyncio.run(self.svc.turn(s['id'], request))
        return self.reload(s)

    def fingerprint(self, s=None):
        s = s or self.reload()
        return json.dumps({k: v for k, v in s.items() if k != 'state_version'},
                          ensure_ascii=False, sort_keys=True)

    def surface(self, s=None):
        return self.rt.surface(s or self.reload())


class NumericTests(unittest.TestCase):
    def test_attribute_modifier_and_fatigue_match_the_spec_table(self):
        self.assertEqual(checks.modifier(0), -10)
        self.assertEqual(checks.modifier(50), 0)
        self.assertEqual(checks.modifier(100), 10)
        self.assertEqual(checks.modifier(60), 2)
        self.assertEqual(checks.modifier(75), 5)
        self.assertEqual(checks.fatigue_penalty(0), 0)
        self.assertEqual(checks.fatigue_penalty(.5), -2)
        self.assertEqual(checks.fatigue_penalty(1), -4)

    def test_dc_comes_from_dc_first_then_difficulty(self):
        self.assertEqual(checks.base_dc({'dc': 15}), 15)
        self.assertEqual(checks.base_dc({'difficulty': .5}), 11)
        self.assertEqual(checks.base_dc({'difficulty': 1}), 21)
        self.assertEqual(checks.base_dc({'dc': 12, 'difficulty': .1}), 12)
        with self.assertRaises(ValueError):
            checks.base_dc({'dc': 31})

    def test_d20_is_deterministic_and_advantage_uses_a_second_die(self):
        first = checks.roll_d20('seed:one')
        self.assertEqual(first, checks.roll_d20('seed:one'))
        self.assertNotEqual(first, checks.roll_d20('seed:other'))
        flat = checks.roll_d20('abc')
        self.assertEqual(flat['advantage'], None)
        self.assertEqual(flat['dice'], [flat['kept']])
        adv = checks.roll_d20('abc', 'advantage')
        dis = checks.roll_d20('abc', 'disadvantage')
        self.assertEqual(len(adv['dice']), 2)
        self.assertEqual(adv['kept'], max(adv['dice']))
        self.assertEqual(dis['kept'], min(dis['dice']))
        self.assertEqual(adv['dice'], dis['dice'])
        for face in (flat['kept'], *adv['dice']):
            self.assertTrue(1 <= face <= 20)

    def test_chance_is_computed_from_total_modifier_and_dc(self):
        self.assertAlmostEqual(checks.chance(0, 11, None), .5)
        self.assertAlmostEqual(checks.chance(9, 11, None), .95)
        self.assertAlmostEqual(checks.chance(-9, 11, None), .05)
        self.assertAlmostEqual(checks.chance(0, 21, None), 0.0)
        self.assertAlmostEqual(checks.chance(20, 21, None), 1.0)
        big = checks.chance(0, 11, 'advantage')
        small = checks.chance(0, 11, 'disadvantage')
        self.assertGreater(big, .5)
        self.assertLess(small, .5)
        self.assertEqual(checks.chance_label(.7), '大')
        self.assertEqual(checks.chance_label(.5), '中')
        self.assertEqual(checks.chance_label(.2), '小')


class TierTests(unittest.TestCase):
    def test_natural_20_always_criticals_and_natural_1_never_succeeds(self):
        for position in checks.POSITIONS:
            with self.subTest(position=position):
                self.assertEqual(checks.tier_for(position, 20, -30), 'critical')
                self.assertEqual(checks.tier_for(position, 1, 30), 'setback'
                                 if position == 'controlled' else 'disaster')

    def test_margin_table_matches_the_spec(self):
        matrix = {
            'controlled': [(10, 'critical'), (0, 'success'), (-1, 'partial'),
                           (-5, 'partial'), (-6, 'setback'), (-99, 'setback')],
            'risky': [(10, 'critical'), (0, 'success'), (-1, 'partial'),
                      (-3, 'partial'), (-4, 'setback'), (-9, 'setback'),
                      (-10, 'disaster')],
            'desperate': [(8, 'critical'), (7, 'success'), (0, 'success'),
                          (-1, 'setback'), (-5, 'setback'), (-6, 'disaster')],
        }
        for position, rows in matrix.items():
            for margin, tier in rows:
                with self.subTest(position=position, margin=margin):
                    self.assertEqual(checks.tier_for(position, 11, margin), tier)

    def test_desperate_has_no_partial_and_boolean_compatibility(self):
        tiers = {checks.tier_for('desperate', face, 0) for face in range(2, 20)}
        self.assertNotIn('partial', tiers)
        for tier in ('critical', 'success', 'partial'):
            self.assertTrue(checks.tier_success(tier))
        for tier in ('setback', 'disaster', 'refused'):
            self.assertFalse(checks.tier_success(tier))


class ConfigTests(Base):
    def test_old_package_without_checks_is_untouched(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        svc = Service(Store(root / 'old.sqlite3'), root)
        svc.provider.configure({'offline': True})
        story = story_doc(no_checks=True)
        svc.runtime.commit_package(story, characters_doc(), '旧包')
        s = svc.runtime.new_session('旧包', 'protagonist')
        self.assertNotIn('clocks', s)
        self.assertNotIn('check_attempts', s)
        self.assertNotIn('clocks', svc.runtime.surface(s))
        self.assertNotIn('last_check', svc.runtime.surface(s))
        self.assertIsNone(checks.config(story))
        described = svc.runtime.surface(s)['actions']
        self.assertEqual(set(described[0]), {'id', 'label'})
        # 旧包的动作仍走 attribute_v1。
        svc.store.save_session(s)
        target = svc.runtime.node(s)['actions'][0]
        token = free_actions.confirm_token(s, svc.runtime.node(s), target, story)
        asyncio.run(svc.turn(s['id'], Turn(message=target['label'], action_id=target['id'],
                                          confirm=token)))
        saved = svc.store.session(s['id'])
        self.assertEqual(saved['checks'][-1]['rules_version'], 'attribute_v1')
        self.assertIn('probability', saved['checks'][-1])

    def test_strict_schema_refuses_unknown_keys_and_bad_versions(self):
        raw = copy.deepcopy(story_doc()['mechanics']['checks'])
        with self.assertRaises(ValueError):
            checks.ChecksConfig.model_validate({**raw, 'unknown': 1})
        with self.assertRaises(ValueError):
            checks.ChecksConfig.model_validate({**raw, 'die': 'd24'})
        with self.assertRaises(ValueError):
            checks.ChecksConfig.model_validate({**raw, 'display': 'curtain'})

    def test_references_must_resolve(self):
        cases = [
            ('clocks', [{'id': 'c', 'label': 'x', 'segments': 2, 'known_by': ['ghost']}],
             '已知受众不存在'),
            ('social', {'ghost': {'interests': [], 'boundaries': []}}, '不存在的角色'),
            ('push', [{'id': 'p', 'label': 'x', 'cost': {'gold': 1}}], '未声明的资源'),
        ]
        for key, value, message in cases:
            with self.subTest(key=key):
                story = story_doc()
                story['mechanics']['checks'][key] = value
                with self.assertRaises(ValueError) as caught:
                    checks.validate_package(story, characters_doc())
                self.assertIn(message, str(caught.exception))

    def test_clock_op_is_only_legal_in_v2_packages(self):
        story = story_doc()
        # 引用了未声明的钟：包校验拒绝。
        story['events'][0]['actions'][0]['success'] = [
            {'op': 'clock', 'id': 'nope', 'delta': 1}]
        with self.assertRaises(ValueError):
            self.rt.validate_package(story, characters_doc())
        # 合法引用在 v2 包里通过。
        story['events'][0]['actions'][0]['success'] = [
            {'op': 'clock', 'id': 'sway', 'delta': 1}]
        self.rt.validate_package(story, characters_doc())
        legacy = story_doc(no_checks=True)
        legacy['events'][0]['actions'][0]['success'] = [
            {'op': 'clock', 'id': 'any', 'delta': 1}]
        with self.assertRaises(ValueError):
            self.rt.validate_package(legacy, characters_doc())

    def test_auto_gate_without_conditions_never_succeeds_for_free(self):
        with self.assertRaises(ValueError):
            checks._check_auto({})
        with self.assertRaises(ValueError):
            checks._check_auto({'all_flags': {}, 'items': []})


class FactorTests(Base):
    def test_factors_are_engine_decided_and_capped(self):
        s = self.reload()
        story, chars = self.package()['story'], self.package()['characters']
        action = self.action('pitch', s)
        before = checks.factor_rows(s, story, chars, action, 'social')
        self.assertEqual([row['id'] for row in before], [])
        s['inventory'].append('manifest')
        self.svc.store.save_session(s)
        s = self.reload()
        rows = checks.factor_rows(s, story, chars, action, 'social')
        self.assertEqual([row['id'] for row in rows], ['manifest'])
        self.assertEqual(checks.factor_mod(rows), 2)
        # 夹取到 −5..+5
        self.assertEqual(checks.factor_mod([{'mod': 3}] * 6), 5)
        self.assertEqual(checks.factor_mod([{'mod': -3}] * 6), -5)

    def test_hidden_factor_changes_the_die_but_never_the_projection(self):
        s = self.reload()
        s['flags']['secret_known'] = True
        self.svc.store.save_session(s)
        s = self.reload()
        block = self.describe('pitch', s)['check']['v2']
        labels = [row['label'] for row in block['factors']]
        self.assertNotIn('他知道你的秘密', labels)
        story, chars = self.package()['story'], self.package()['characters']
        rows = checks.factor_rows(s, story, chars, self.action('pitch', s), 'social')
        self.assertIn('secret', [row['id'] for row in rows])
        self.assertEqual(checks.factor_mod(rows), -3)
        # 结算后的公开结果同样不泄露隐藏因素。
        resolved = checks.resolve(s, story, chars, self.node(s), self.action('pitch', s),
                                  None, 'hidden:seed')
        public = checks.public_result(s, story, resolved)
        self.assertNotIn('他知道你的秘密', json.dumps(public, ensure_ascii=False))

    def test_when_kinds_are_a_closed_list(self):
        for kind, extra in (
                ('item', {'id': 'manifest'}),
                ('flag', {'id': 'f', 'value': False}),
                ('companion', {'id': 'broker', 'min_trust': .4}),
                ('profile', {'id': 'traveller'}),
                ('place', {'id': 'hall'}),
                ('place', {'tag': 'town'}),
                ('time', {'from': 22, 'to': 6}),
                ('attribute_axis', {'attribute': 'wisdom'})):
            with self.subTest(kind=kind):
                when = checks.When.model_validate({'kind': kind, **extra})
                self.assertEqual(when.kind, kind)
        with self.assertRaises(ValueError):
            checks.When.model_validate({'kind': 'weather', 'id': 'rain'})
        with self.assertRaises(ValueError):
            checks.When.model_validate({'kind': 'time', 'from': 8, 'to': 8})

    def test_time_window_wraps_past_midnight(self):
        story, chars = self.package()['story'], self.package()['characters']
        s = self.reload()
        night = checks.When.model_validate({'kind': 'time', 'from': 22, 'to': 6})
        s['time'] = 23
        self.assertTrue(checks.when_matches(night, s, story, chars))
        s['time'] = 3
        self.assertTrue(checks.when_matches(night, s, story, chars))
        s['time'] = 12
        self.assertFalse(checks.when_matches(night, s, story, chars))


class SocialTests(Base):
    def test_boundary_hit_is_refused_without_rolling_or_side_effects(self):
        before = self.fingerprint()
        block = self.describe('bully')['check']['v2']
        self.assertEqual(block['refused'], '这触到了他的底线')
        s = self.do('bully')
        self.assertEqual(s['checks'], [])
        self.assertEqual(s['local']['resources']['pence'], 18)
        self.assertNotIn('bully', s['active']['actions_done'])
        self.assertEqual(s['time'], json.loads(before)['time'])
        self.assertEqual(s['clocks']['sway']['filled'], 0)
        self.assertEqual(s['clocks']['suspicion']['filled'], 0)
        public = self.surface(s)['last_check']
        self.assertEqual(public['tier'], 'refused')
        self.assertFalse(public['rolled'])
        self.assertEqual(public['refused'], '这触到了他的底线')
        # 拒绝不写任何状态效果，只有 last_check 与轮次记录变化。
        stripped = self.fingerprint(s)
        original = json.loads(before)
        current = json.loads(stripped)
        for key in ('last_check', 'usage', 'turn_index', 'active'):
            original.pop(key, None)
            current.pop(key, None)
        for key in ('checks',):
            self.assertEqual(current.get(key), original.get(key))

    def test_interests_lower_dc_up_to_six_and_trust_adjusts_it(self):
        story, chars = self.package()['story'], self.package()['characters']
        s = self.reload()
        action = self.action('pitch', s)
        base = checks.plan(s, story, chars, self.node(s), action)
        self.assertEqual(checks.base_dc(action['check']), 11)
        # 一个诉求 −3，信任 0.5 不调整 → DC 8
        self.assertEqual(base['dc'], 8)
        s['development'] = {'broker': {'relationships': {'player': {'trust': .9}}}}
        better = checks.plan(s, story, chars, self.node(s), action)
        self.assertEqual(better['social']['dc_delta'], -3 - 4)
        self.assertEqual(better['dc'], 4)
        two = copy.deepcopy(action)
        two['check']['social']['appeals'] = ['profit', 'reputation']
        capped = checks.plan(s, story, chars, self.node(s), {**action,
                                                             'check': two['check']})
        self.assertEqual(capped['social']['dc_delta'], -6 - 4)

    def test_social_target_must_be_present(self):
        story, chars = self.package()['story'], self.package()['characters']
        s = self.reload()
        s['characters']['broker']['location'] = 'elsewhere'
        gate = checks.social_gate(s, story, chars, self.node(s),
                                  self.action('pitch', s))
        self.assertFalse(gate['present'])
        self.assertEqual(gate['refused'], '这个人此刻不在场')

    def test_social_profile_is_never_leaked_in_projections(self):
        block = self.describe('pitch')['check']['v2']
        dumped = json.dumps(block, ensure_ascii=False)
        for secret in ('profit', 'reputation', 'family', 'theft', 'trust_weight',
                       'boundaries', 'interests'):
            self.assertNotIn(secret, dumped)


class AutoSuccessTests(Base):
    def test_max_dc_auto_success_skips_the_die(self):
        story, chars = self.package()['story'], self.package()['characters']
        s = self.reload()
        action = self.action('pitch', s)
        # 抬到 DC 7（默认 DC 8 > 6 不自动）→ 先确认不自动
        self.assertFalse(checks.plan(s, story, chars, self.node(s), action)['auto']['auto'])
        s['development'] = {'broker': {'relationships': {'player': {'trust': .6}}}}
        planned = checks.plan(s, story, chars, self.node(s), action)
        self.assertEqual(planned['dc'], 7)
        hand = copy.deepcopy(action)
        hand['check']['auto'] = {'max_dc': 8}
        planned = checks.plan(s, story, chars, self.node(s), {**action,
                                                             'check': hand['check']})
        self.assertTrue(planned['auto']['auto'])
        resolved = checks.resolve(s, story, chars, self.node(s),
                                  {**action, 'check': hand['check']}, None, 'auto:seed')
        self.assertFalse(resolved['rolled'])
        self.assertEqual(resolved['tier'], 'success')
        public = checks.public_result(s, story, resolved)
        self.assertTrue(public['auto'])
        self.assertFalse(public['rolled'])

    def test_auto_by_flags_or_items(self):
        story, chars = self.package()['story'], self.package()['characters']
        s = self.reload()
        action = copy.deepcopy(self.action('pitch', s))
        action['check']['auto'] = {'all_flags': {'prepared': True}}
        self.assertFalse(checks.plan(s, story, chars, self.node(s), action)['auto']['auto'])
        s['flags']['prepared'] = True
        self.assertTrue(checks.plan(s, story, chars, self.node(s), action)['auto']['auto'])
        action['check']['auto'] = {'items': ['manifest']}
        self.assertFalse(checks.plan(s, story, chars, self.node(s), action)['auto']['auto'])
        s['inventory'].append('manifest')
        self.assertTrue(checks.plan(s, story, chars, self.node(s), action)['auto']['auto'])


class ClockTests(Base):
    def test_progress_clock_fills_by_effect_and_success_tier(self):
        story, chars = self.package()['story'], self.package()['characters']
        s = self.reload()
        action = self.action('pitch', s)
        for tier, expect in (('critical', 3), ('success', 2), ('partial', 1)):
            with self.subTest(tier=tier):
                resolved = {**checks.resolve(s, story, chars, self.node(s), action,
                                             None, 'seed:%s' % tier), 'tier': tier}
                row = checks.consequences(s, story, chars, self.node(s), action, resolved)
                self.assertEqual(row['clocks'], [{'id': 'sway', 'delta': expect}])

    def test_clock_full_fires_on_full_exactly_once_and_freezes(self):
        story = self.package()['story']
        s = self.reload()
        s['clocks'] = {'sway': {'filled': 0, 'full_at': None}}
        applied = []

        def fake_effects(session, effects, source):
            applied.append((source, list(effects)))

        checks.advance_clock(s, story, 'sway', 4, effects=fake_effects)
        self.assertEqual(s['clocks']['sway']['filled'], 4)
        self.assertIsNotNone(s['clocks']['sway']['full_at'])
        self.assertEqual(applied, [('clock:sway',
                                    [{'op': 'flag', 'id': 'guild_convinced',
                                      'value': True}])])
        # 满格后不再变化，也不会第二次执行 on_full。
        second = checks.advance_clock(s, story, 'sway', 4, effects=fake_effects)
        self.assertEqual(second['to'], 4)
        self.assertFalse(second['changed'])
        self.assertEqual(len(applied), 1)

    def test_clock_clamps_to_bounds(self):
        story = self.package()['story']
        s = self.reload()
        s['clocks'] = {'suspicion': {'filled': 2, 'full_at': None}}
        out = checks.advance_clock(s, story, 'suspicion', -10)
        self.assertEqual((out['from'], out['to']), (2, 0))

    def test_hidden_clock_never_reaches_the_player_projection(self):
        s = self.reload()
        clocks = self.surface(s)['clocks']
        ids = [row['id'] for row in clocks]
        self.assertEqual(ids, ['sway', 'suspicion'])
        self.assertNotIn('hidden_clock', json.dumps(self.surface(s), ensure_ascii=False))
        story = self.package()['story']
        # known_by 是逐个钟声明的：broker 只看见它自己那个钟。
        self.assertEqual([row['id'] for row in checks.public_clocks(s, story, 'broker')],
                         ['hidden_clock'])

    def test_danger_clock_fires_once_per_tier_and_not_twice(self):
        story, chars = self.package()['story'], self.package()['characters']
        s = self.reload()
        action = self.action('pitch', s)
        for tier, expect in (('setback', 1), ('disaster', 2)):
            with self.subTest(tier=tier):
                resolved = {**checks.resolve(s, story, chars, self.node(s), action,
                                             None, 'seed:%s' % tier), 'tier': tier}
                row = checks.consequences(s, story, chars, self.node(s), action, resolved)
                self.assertEqual(row['clocks'], [{'id': 'suspicion', 'delta': expect}])

    def test_manual_clock_effect_suppresses_the_automatic_one(self):
        story = self.package()['story']
        action = copy.deepcopy(self.action('pitch', self.reload()))
        action['check']['tiers'] = {'success': {'effects': [
            {'op': 'clock', 'id': 'sway', 'delta': 1}]}}
        resolved = checks.resolve(self.reload(), story, self.package()['characters'],
                                  self.node(), action, None, 'manual:seed')
        resolved = {**resolved, 'tier': 'success'}
        row = checks.consequences(self.reload(), story, self.package()['characters'],
                                  self.node(), action, resolved)
        self.assertEqual(row['clocks'], [])
        self.assertEqual(row['effects'], [{'op': 'clock', 'id': 'sway', 'delta': 1}])

    def test_clock_state_rolls_back_with_the_snapshot(self):
        # 事件的 before 快照是进事件时拍的；这一杆无论成功与否，回滚都必须回到当时的钟。
        s = self.do('pitch')
        s = self.do('leave', s)
        self.assertIsNone(s['active'])
        archive = s['archives'][0]
        self.assertIn('clocks', archive['before'])
        restored = self.rt.rollback(s, archive['id'])
        self.assertEqual(restored['clocks'], archive['before']['clocks'])
        # 同一份快照里也带着尝试记录：回滚后重试记录不能留在副本里。
        self.assertEqual(restored.get('check_attempts', {}),
                         archive['before'].get('check_attempts', {}))


class NoticeTests(Base):
    def notice_for(self, seed):
        story, chars = self.package()['story'], self.package()['characters']
        s = self.reload()
        action = self.action('sneak', s)
        resolved = checks.resolve(s, story, chars, self.node(s), action, None, seed)
        return checks.notice(s, story, chars, self.node(s), action, resolved, seed), resolved

    def test_notice_roll_is_deterministic_and_uses_own_seed(self):
        first, _ = self.notice_for('notice:seed')
        second, _ = self.notice_for('notice:seed')
        self.assertEqual(first, second)
        other, _ = self.notice_for('notice:other')
        self.assertNotEqual(first, second if first != second else other)

    def test_unnoticed_npc_does_not_remember_and_nothing_claims_certainty(self):
        story, chars = self.package()['story'], self.package()['characters']
        s = self.reload()
        action = self.action('sneak', s)
        # 找一个「没察觉」的 seed：主检定 total 极高 → 不可能被察觉。
        resolved = {**checks.resolve(s, story, chars, self.node(s), action, None,
                                     'x'), 'total': 999}
        info = checks.notice(s, story, chars, self.node(s), action, resolved, 'x')
        self.assertEqual(info['noticed'], [])
        self.assertEqual(info['witnesses'], set())
        self.assertEqual(info['public']['noticed'], checks.NOTICED_NONE)
        package = copy.deepcopy(self.package())
        for actor in package['characters']['characters']:
            if actor['id'] == 'broker':
                actor['npc_card'] = {'version': 1}
        npc_cards.remember_action(package, s, self.node(s), action,
                                  {'outcome': '我悄悄动了手',
                                   'narrative': {'result': 'success'}},
                                  witnesses=info['witnesses'])
        self.assertEqual([r for r in s['beliefs'] if r.get('character') == 'broker'], [])

    def test_noticed_npc_remembers_and_sees_the_action(self):
        story, chars = self.package()['story'], self.package()['characters']
        s = self.reload()
        action = self.action('sneak', s)
        resolved = {**checks.resolve(s, story, chars, self.node(s), action, None,
                                     'x'), 'total': -999}
        info = checks.notice(s, story, chars, self.node(s), action, resolved, 'x')
        self.assertEqual(info['noticed'], ['broker'])
        self.assertIn('broker', info['witnesses'])
        self.assertEqual(info['public']['noticed'], checks.NOTICED_VISIBLE)
        package = copy.deepcopy(self.package())
        for actor in package['characters']['characters']:
            if actor['id'] == 'broker':
                actor['npc_card'] = {'version': 1}
        npc_cards.remember_action(package, s, self.node(s), action,
                                  {'outcome': '我悄悄动了手',
                                   'narrative': {'result': 'success'}},
                                  witnesses=info['witnesses'])
        memories = [r for r in s['beliefs'] if r.get('character') == 'broker']
        self.assertEqual(len(memories), 1)
        self.assertEqual(memories[0]['text'], '我悄悄动了手')

    def test_declared_witnesses_are_always_included_without_claiming_nobody_saw(self):
        story, chars = self.package()['story'], self.package()['characters']
        s = self.reload()
        action = copy.deepcopy(self.action('sneak', s))
        action['witnesses'] = ['broker']
        resolved = {**checks.resolve(s, story, chars, self.node(s), action, None,
                                     'x'), 'total': 999}
        info = checks.notice(s, story, chars, self.node(s), action, resolved, 'x')
        self.assertIn('broker', info['witnesses'])
        self.assertEqual(info['public']['noticed'], checks.NOTICED_SOME)
        self.assertTrue(info['public']['aware'])

    def test_concealed_is_validated(self):
        story = story_doc()
        story['events'][0]['actions'][2]['check']['concealed']['observers'] = 'all'
        with self.assertRaises(ValueError):
            checks.validate_package(story, characters_doc())

    def test_action_without_concealed_keeps_declarative_witnesses(self):
        story, chars = self.package()['story'], self.package()['characters']
        s = self.reload()
        self.assertIsNone(checks.concealed_config(self.action('pitch', s)))
        self.assertIsNone(checks.notice(s, story, chars, self.node(s),
                                        self.action('pitch', s),
                                        checks.resolve(s, story, chars, self.node(s),
                                                       self.action('pitch', s), None, 'x'),
                                        'x'))


class PushTests(Base):
    def test_confirm_token_binds_the_push_id(self):
        s = self.reload()
        story, node = self.package()['story'], self.node(s)
        action = self.action('pitch', s)
        plain = free_actions.confirm_token(s, node, action, story)
        greasy = free_actions.confirm_token(s, node, action, story, 'grease')
        self.assertNotEqual(plain, greasy)
        self.assertEqual(greasy, free_actions.confirm_token(s, node, action, story, 'grease'))

    def test_switching_push_invalidates_the_old_token_before_side_effects(self):
        s = self.reload()
        stale = self.describe('pitch', s)['confirm']
        before = self.fingerprint(s)
        fresh = self.describe('pitch', s, push='grease')
        self.assertNotEqual(stale, fresh['confirm'])
        with self.assertRaises(ValueError):
            asyncio.run(self.svc.turn(s['id'], Turn(message='谈买卖', action_id='pitch',
                                                    confirm=stale, push='grease')))
        self.assertEqual(before, self.fingerprint())

    def test_push_cost_is_charged_before_the_roll_and_refused_when_unaffordable(self):
        s = self.reload()
        s['local']['resources']['pence'] = 1
        self.svc.store.save_session(s)
        s = self.reload()
        before = self.fingerprint(s)
        with self.assertRaises(ValueError) as caught:
            self.describe('pitch', s, push='grease')
        self.assertIn('加码付不起', str(caught.exception))
        self.assertEqual(before, self.fingerprint())

    def test_push_bonus_lands_in_the_audit_and_the_charge(self):
        s = self.do('pitch', push='grease')
        self.assertEqual(s['local']['resources']['pence'], 16)
        audit = s['checks'][-1]
        self.assertEqual(audit['push'], 'grease')
        self.assertEqual(s['checks'][-1]['rules_version'], 'd20_v2')
        self.assertEqual(s['last_check']['push']['id'], 'grease')

    def test_relationship_push_moves_trust_of_the_check_target(self):
        s = self.do('pitch', push='favor')
        trust = s['development']['broker']['relationships']['player']['trust']
        self.assertAlmostEqual(trust, .4)
        self.assertEqual(s['last_check']['push']['id'], 'favor')

    def test_push_allowed_restricts_the_options(self):
        story = self.package()['story']
        action = copy.deepcopy(self.action('pitch', self.reload()))
        action['check']['push_allowed'] = ['favor']
        block = checks.preview(self.reload(), story, self.package()['characters'],
                               self.node(), action)
        self.assertEqual([row['id'] for row in block['push_options']], ['favor'])
        with self.assertRaises(ValueError):
            checks.preview(self.reload(), story, self.package()['characters'],
                           self.node(), action, 'grease')


class RetryTests(unittest.TestCase):
    story_kwargs = {'checks': {**story_doc()['mechanics']['checks'],
                               'retry': {'same_approach': 'harder'}}}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.svc = Service(Store(self.root / 'retry.sqlite3'), self.root)
        self.svc.provider.configure({'offline': True})
        self.rt = self.svc.runtime
        story = story_doc()
        story['mechanics']['checks']['retry'] = {'same_approach': 'harder'}
        story['events'][0]['actions'][0]['check'].pop('auto', None)
        self.rt.commit_package(story, characters_doc(), '重试测试')
        self.s = self.rt.new_session('重试', 'protagonist')

    def reload(self):
        return self.svc.store.session(self.s['id'])

    def action(self):
        return next(a for a in self.rt.node(self.s)['actions'] if a['id'] == 'pitch')

    def test_harder_adds_three_per_repeat_capped_at_nine(self):
        s = self.reload()
        story = self.rt.package()['story']
        chars = self.rt.package()['characters']
        node, action = self.rt.node(s), self.action()
        base = checks.plan(s, story, chars, node, action)['dc']
        for index in (1, 2, 3, 4):
            checks.record_attempt(s, node, action, 'setback')
            planned = checks.plan(s, story, chars, node, action)
            self.assertEqual(planned['dc'], min(30, base + 3 * min(3, index)))
            self.assertFalse(planned['blocked'])

    def test_changing_the_approach_clears_the_penalty(self):
        s = self.reload()
        story = self.rt.package()['story']
        chars = self.rt.package()['characters']
        node, action = self.rt.node(s), self.action()
        base = checks.plan(s, story, chars, node, action)['dc']
        checks.record_attempt(s, node, action, 'setback')
        self.assertEqual(checks.plan(s, story, chars, node, action)['dc'], base + 3)
        pushed = checks.plan(s, story, chars, node, action, 'grease')
        self.assertEqual(pushed['dc'], base)
        self.assertFalse(pushed['retry']['blocked'])

    def test_successful_attempts_do_not_block(self):
        s = self.reload()
        story = self.rt.package()['story']
        chars = self.rt.package()['characters']
        node, action = self.rt.node(s), self.action()
        checks.record_attempt(s, node, action, 'success')
        planned = checks.plan(s, story, chars, node, action)
        self.assertFalse(planned['blocked'])
        self.assertEqual(planned['retry']['dc_bonus'], 0)


class RetryRefuseTests(Base):
    def test_same_approach_after_setback_is_blocked_in_the_preview_and_refused(self):
        s = self.reload()
        node, action = self.node(s), self.action('pitch', s)
        checks.record_attempt(s, node, action, 'setback')
        self.svc.store.save_session(s)
        s = self.reload()
        block = self.describe('pitch', s)['check']['v2']
        self.assertEqual(block['blocked'], checks.BLOCKED_TEXT)
        before = self.fingerprint(s)
        described = self.describe('pitch', s)
        with self.assertRaises(ValueError) as caught:
            asyncio.run(self.svc.turn(s['id'], Turn(message='谈买卖', action_id='pitch',
                                                    confirm=described['confirm'])))
        self.assertEqual(str(caught.exception), checks.BLOCKED_TEXT)
        self.assertEqual(before, self.fingerprint())

    def test_recorded_attempts_survive_a_rollback(self):
        s = self.reload()
        checks.record_attempt(s, self.node(s), self.action('pitch', s), 'disaster')
        self.svc.store.save_session(s)
        s = self.reload()
        self.assertEqual(len(checks.attempts(s, self.node(s), self.action('pitch', s))), 1)
        # 回滚到事件开始前的快照后，尝试记录随之消失（会话开局快照里它是空的）。
        s = self.do('leave', s)
        restored = self.rt.rollback(s, s['archives'][0]['id'])
        self.assertEqual(restored.get('check_attempts', {}), {})


class FrozenPlanTests(Base):
    """确认预览承诺的那一份判定，必须就是本次真正结算的那一份。

    回归点：``Runtime._v2_turn`` 曾先 plan、再扣成本与加码代价、最后重新 plan 结算；
    扣费会改疲劳/信任/资源，从而改变 DC 与修正。那样代价会反过来改写已经确认的判定。
    """

    def test_confirm_preview_dc_equals_the_settled_audit_dc(self):
        # 每个子用例起一个全新旅程：静态动作是一次性的（actions_done）。
        for push in (None, 'grease', 'favor'):
            with self.subTest(push=push):
                fresh = self.rt.new_session('v2 preview %s' % push, 'protagonist')
                block = self.describe('pitch', fresh, push)['check']['v2']
                s = self.do('pitch', fresh, push=push)
                audit = s['checks'][-1]
                # 关键：冻结 plan 后，结算的 DC 与确认预览完全相等。
                self.assertEqual(audit['dc'], block['dc'])
                self.assertEqual(s['last_check']['dc'], block['dc'])

    def test_fatigue_push_does_not_lower_this_rolls_modifier(self):
        # 「咬牙硬撑」在包内是 advantage 加疲劳；疲劳代价不能回过来削弱这一次。
        story = copy.deepcopy(self.package()['story'])
        action = copy.deepcopy(self.action('pitch', self.reload()))
        s = self.reload()
        before = checks.plan(s, story, self.package()['characters'], self.node(s), action)
        frozen = copy.deepcopy(before)
        # 模拟扣费后的状态：疲劳升高。
        s['characters'][s['hero']]['status']['疲劳'] = 0.8
        after = checks.plan(s, story, self.package()['characters'], self.node(s), action)
        self.assertLess(after['fatigue_pen'], frozen['fatigue_pen'])
        resolved_frozen = checks.resolve(s, story, self.package()['characters'],
                                        self.node(s), action, None, 'seed:x',
                                        planned=frozen)
        resolved_fresh = checks.resolve(s, story, self.package()['characters'],
                                       self.node(s), action, None, 'seed:x')
        self.assertEqual(resolved_frozen['total_mod'], frozen['total_mod'])
        self.assertLess(resolved_fresh['total_mod'], resolved_frozen['total_mod'])

    def test_relationship_push_does_not_raise_this_rolls_dc(self):
        story = copy.deepcopy(self.package()['story'])
        action = copy.deepcopy(self.action('pitch', self.reload()))
        s = self.reload()
        frozen = checks.plan(s, story, self.package()['characters'], self.node(s), action,
                             'favor')
        # 人情代价扣掉的信任会让同一个动作更难；但已经确认的那一份不能变。
        s['development'] = {'broker': {'relationships': {'player': {'trust': .1}}}}
        after = checks.plan(s, story, self.package()['characters'], self.node(s), action,
                           'favor')
        self.assertGreater(after['dc'], frozen['dc'])
        resolved = checks.resolve(s, story, self.package()['characters'], self.node(s),
                                  action, 'favor', 'seed:x', planned=frozen)
        self.assertEqual(resolved['dc'], frozen['dc'])

    def test_spending_exactly_held_resource_does_not_change_this_roll(self):
        story = copy.deepcopy(self.package()['story'])
        # 一条「有钱才有利」的因素：正好花光加码费时，预结算前它有、结算后它没有。
        story['mechanics']['checks']['factors'].append(
            {'id': 'flush', 'label': '你身上还有钱', 'mod': 3,
             'when': {'kind': 'flag', 'id': 'has_manifest', 'value': False}})
        s = self.reload()
        s['local']['resources']['pence'] = 2
        self.svc.store.save_session(s)
        s = self.reload()
        action = self.action('pitch', s)
        frozen = checks.plan(s, story, self.package()['characters'], self.node(s), action,
                            'grease')
        s['local']['resources']['pence'] = 0
        after = checks.plan(s, story, self.package()['characters'], self.node(s), action)
        self.assertEqual(frozen['factor_mod'], 3)
        self.assertEqual(after['factor_mod'], 3)     # 资源不是因素来源，必须相等
        resolved = checks.resolve(s, story, self.package()['characters'], self.node(s),
                                  action, 'grease', 'seed:x', planned=frozen)
        self.assertEqual(resolved['total_mod'], frozen['total_mod'])

    def test_http_audit_matches_the_confirm_preview_for_favor(self):
        """真实一回：confirm(favor) 的 dc/total 与结算后的审计完全一致。"""
        s = self.reload()
        preview = self.describe('pitch', s, 'favor')['check']['v2']
        s = self.do('pitch', s, push='favor')
        audit = s['checks'][-1]
        self.assertEqual(audit['dc'], preview['dc'])
        self.assertEqual(s['development']['broker']['relationships']['player']['trust'], .4)


class ConsequenceTests(Base):
    def test_partial_uses_the_first_executable_default_cost(self):
        story, chars = self.package()['story'], self.package()['characters']
        s = self.reload()
        action = self.action('pitch', s)
        resolved = {**checks.resolve(s, story, chars, self.node(s), action, None, 'x'),
                    'tier': 'partial'}
        row = checks.consequences(s, story, chars, self.node(s), action, resolved)
        self.assertEqual(row['extra_hours'], 1)
        self.assertTrue(row['used_default_cost'])
        # 时间代价不可执行时退到下一条：资源。
        story2 = copy.deepcopy(story)
        story2['mechanics']['checks']['default_costs'] = [
            {'kind': 'resource', 'id': 'pence', 'amount': 2},
            {'kind': 'flag', 'id': 'exposed', 'value': True}]
        row = checks.consequences(s, story2, chars, self.node(s), action, {
            **resolved, 'config': checks.config(story2)})
        self.assertIn({'op': 'resource', 'id': 'pence', 'delta': -2}, row['effects'])
        s['local']['resources']['pence'] = 0
        row = checks.consequences(s, story2, chars, self.node(s), action, {
            **resolved, 'config': checks.config(story2)})
        self.assertIn({'op': 'flag', 'id': 'exposed', 'value': True}, row['effects'])

    def test_no_default_cost_keeps_a_public_receipt_only(self):
        story = copy.deepcopy(self.package()['story'])
        story['mechanics']['checks']['default_costs'] = []
        s = self.reload()
        action = copy.deepcopy(self.action('pitch', s))
        action.pop('success_text')
        resolved = {**checks.resolve(s, story, self.package()['characters'],
                                     self.node(s), action, None, 'x'), 'tier': 'partial'}
        row = checks.consequences(s, story, self.package()['characters'],
                                  self.node(s), action, resolved)
        self.assertEqual(row['extra_hours'], 0)
        self.assertEqual(row['effects'], [])
        self.assertEqual(row['text'], checks.GENERIC_PARTIAL)

    def test_fallback_scope_never_takes_resource_costs(self):
        story = copy.deepcopy(self.package()['story'])
        story['mechanics']['checks']['default_costs'] = [
            {'kind': 'resource', 'id': 'pence', 'amount': 2}]
        s = self.reload()
        action = self.action('pitch', s)
        resolved = {**checks.resolve(s, story, self.package()['characters'],
                                     self.node(s), action, None, 'x'), 'tier': 'partial'}
        row = checks.consequences(s, story, self.package()['characters'],
                                  self.node(s), action, resolved, scope='fallback',
                                  include_base=False)
        self.assertEqual(row['effects'], [])
        self.assertEqual(row['extra_hours'], 0)

    def test_setback_never_soft_locks(self):
        story, chars = self.package()['story'], self.package()['characters']
        s = self.reload()
        action = self.action('pitch', s)
        resolved = {**checks.resolve(s, story, chars, self.node(s), action, None, 'x'),
                    'tier': 'setback'}
        row = checks.consequences(s, story, chars, self.node(s), action, resolved)
        self.assertFalse(row['success'])
        for effect in row['effects']:
            self.assertNotIn(effect.get('op'), ('ends_event',))
        self.assertFalse(row.get('ends'))

    def test_tier_text_beats_the_plain_branch_text(self):
        story, chars = self.package()['story'], self.package()['characters']
        s = self.reload()
        action = copy.deepcopy(self.action('pitch', s))
        action['check']['tiers'] = {'critical': {'text': '额外收获的结果文本',
                                                 'effects': [
                                                     {'op': 'flag', 'id': 'bonus',
                                                      'value': True}]}}
        resolved = {**checks.resolve(s, story, chars, self.node(s), action, None, 'x'),
                    'tier': 'critical'}
        row = checks.consequences(s, story, chars, self.node(s), action, resolved)
        self.assertEqual(row['text'], '额外收获的结果文本')
        self.assertIn({'op': 'flag', 'id': 'bonus', 'value': True}, row['effects'])

    def test_desperate_upgrades_the_effect_but_caps_at_great(self):
        story, chars = self.package()['story'], self.package()['characters']
        s = self.reload()
        action = copy.deepcopy(self.action('pitch', s))
        action['check'].pop('social', None)
        action['check']['position'] = 'desperate'
        action['check']['effect'] = 'standard'
        self.assertEqual(checks.plan(s, story, chars, self.node(s), action)['effect'], 'great')
        action['check']['effect'] = 'great'
        self.assertEqual(checks.plan(s, story, chars, self.node(s), action)['effect'], 'great')


class ProjectionTests(Base):
    def test_surface_exposes_clocks_and_the_last_check(self):
        surface = self.surface()
        self.assertEqual([row['id'] for row in surface['clocks']], ['sway', 'suspicion'])
        self.assertNotIn('last_check', surface)
        s = self.do('pitch')
        surface = self.surface(s)
        check = surface['last_check']
        self.assertEqual(check['rules_version'], 'd20_v2')
        self.assertTrue(check['rolled'])
        self.assertEqual(len(check['dice']), 1)
        self.assertEqual(check['kept'], check['dice'][0])
        self.assertEqual(check['total'], check['kept'] + check['modifier'])
        self.assertEqual(check['margin'], check['total'] - check['dc'])
        self.assertEqual(check['tier_label'],
                         checks.TIER_LABELS[check['tier']])
        # 只保留本轮那一条：rolling back to a fresh event leaves the old one behind.
        self.assertEqual(len(s['checks']), 1)

    def test_qualitative_display_hides_the_numbers(self):
        story = story_doc()
        story['mechanics']['checks']['display'] = 'qualitative'
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        svc = Service(Store(root / 'q.sqlite3'), root)
        svc.provider.configure({'offline': True})
        svc.runtime.commit_package(story, characters_doc(), '定性展示')
        s = svc.runtime.new_session('定性', 'protagonist')
        described = free_actions.describe(s, svc.runtime.package()['story'],
                                          svc.runtime.node(s), 'pitch',
                                          characters=svc.runtime.package()['characters'])
        block = described['check']['v2']
        self.assertNotIn('dc', block)
        asyncio.run(svc.turn(s['id'], Turn(message='谈买卖', action_id='pitch',
                                          confirm=described['confirm'])))
        saved = svc.store.session(s['id'])
        public = svc.runtime.surface(saved)['last_check']
        for key in ('modifier', 'dc', 'total', 'margin'):
            self.assertNotIn(key, public)
        self.assertIn('tier', public)
        self.assertIn('dice', public)

    def test_preview_gives_signs_but_no_factor_numbers(self):
        s = self.reload()
        s['inventory'].append('manifest')
        self.svc.store.save_session(s)
        block = self.describe('pitch', s)['check']['v2']
        self.assertEqual(block['factors'], [{'label': '你拿着运货单', 'sign': '+'}])
        self.assertNotIn('mod', block['factors'][0])

    def test_surface_action_rows_carry_the_v2_block(self):
        rows = {row['id']: row for row in self.surface()['actions']}
        self.assertIn('check_v2', rows['pitch'])
        self.assertEqual(rows['pitch']['check_v2']['position'], 'risky')
        self.assertEqual(rows['bully']['check_v2']['refused'], '这触到了他的底线')
        self.assertNotIn('check_v2', rows['leave'])

    def test_model_context_gets_only_the_tier(self):
        from app import scene_judgment
        self.story['mechanics']['scene_judgment'] = {
            'version': 1, 'law': '当地规矩',
            'actors': {'broker': {'values': '看重利润',
                                  'choices': {'ok': {'line': '他点了头'}}}}}
        self.rt.commit_package(self.story, self.characters, 'v2 + 短篇裁定')
        self.s = self.rt.new_session('v2 场景', 'protagonist')
        s = self.do('pitch')

        class _Request:
            message = '谈买卖'
            channel = 'action'
            action_id = 'pitch'

        data = scene_judgment.context(self.rt, s, _Request(), {'outcome': '谈成了'},
                                      self.action('pitch', s))
        self.assertEqual(set(data['check']),
                         {'attribute', 'success', 'tier', 'tier_label', 'boundary'})
        self.assertNotIn('margin', data['check'])
        self.assertNotIn('dc', data['check'])


class RuntimeTests(Base):
    def test_refused_turn_keeps_time_cost_and_done_list_untouched(self):
        before = self.reload()
        s = self.do('bully')
        self.assertEqual(s['local'], before['local'])
        self.assertEqual(s['time'], before['time'])
        self.assertEqual(s['active']['actions_done'], [])
        self.assertEqual(s['turn_index'], before['turn_index'] + 1)

    def test_v2_audit_lives_next_to_v1_records(self):
        s = self.do('pitch')
        self.assertEqual([row['rules_version'] for row in s['checks']], ['d20_v2'])
        audit = s['checks'][-1]
        for key in ('dice', 'kept', 'tier', 'position', 'effect', 'dc', 'total',
                    'margin', 'modifier'):
            self.assertIn(key, audit)

    def test_broken_confirm_never_writes(self):
        s = self.reload()
        described = self.describe('pitch', s)
        before = self.fingerprint(s)
        with self.assertRaises(ValueError):
            asyncio.run(self.svc.turn(s['id'], Turn(message='谈买卖', action_id='pitch',
                                                    confirm='0' * 32)))
        self.assertEqual(before, self.fingerprint(s))
        self.assertTrue(described['confirm'])

    def test_explicit_mechanics_are_required(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        svc = Service(Store(root / 'plain.sqlite3'), root)
        svc.provider.configure({'offline': True})
        story = story_doc(no_checks=True)
        svc.runtime.commit_package(story, characters_doc(), '无判定块')
        s = svc.runtime.new_session('无判定', 'protagonist')
        self.assertFalse(checks.enabled(story))
        self.assertIsNone(checks.preview(s, story, {'characters': []},
                                        svc.runtime.node(s),
                                        svc.runtime.node(s)['actions'][0]))


if __name__ == '__main__':
    unittest.main()
