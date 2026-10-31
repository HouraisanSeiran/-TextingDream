# -*- coding: utf-8 -*-
"""任务与地方后果：状态机、成本/报酬来源、原子性、期限、知情投影、回滚。

全部用临时库与真实 ``Runtime.effects`` / ``rewards`` / ``local_rules``；不启服务、
不碰用户 ``data/``。fixture 是自造的，但走的是真实执行器。
"""
import copy
import tempfile
import unittest
from pathlib import Path

from app import quests
from app.service import Service
from app.storage import Store

ROOT = Path(__file__).resolve().parents[1]


def story_with_quests(extra_mechanics=None, base=None):
    """The project's real story package, with the quest/local/reward blocks added.

    Starting from the shipped package (not a hand-written minimum) is what makes
    ``Runtime.commit_package`` able to validate it: the base schema has many required
    fields, and a partial fixture would refuse for the wrong reason.
    """
    story = copy.deepcopy(base) if base is not None else {}
    story['mechanics'] = dict(story.get('mechanics') or {})
    story['mechanics'].update({
            'local': {'resources': [
                {'id': 'firewood', 'name': '柴火', 'initial': 20, 'per_hour': 0},
                {'id': 'plank', 'name': '木板', 'initial': 4, 'per_hour': 0},
            ]},
            'rewards': {
                'version': 1,
                'currencies': [{'id': 'coin', 'name': '铜币', 'unit': '文'}],
                'accounts': [{'id': 'miller', 'name': '磨坊主',
                              'currency': 'coin', 'initial': 500}],
                'materials': [], 'shapes': [], 'qualities': [],
                'enchantments': [], 'abilities': [], 'templates': [],
                'tables': [],
                'rewards': [
                    {'id': 'escort_pay', 'kind': 'currency', 'currency': 'coin',
                     'amount_min': 30, 'amount_max': 30, 'payer': 'miller'},
                ],
            },
            'quests': {
                'version': 1,
                'quests': [
                    {
                        'id': 'escort',
                        'giver': 'miller',
                        'location': 'square',
                        'title': '送柴去磨坊',
                        'public_summary': '把一捆柴火送到磨坊。',
                        'secret_objective': '（隐藏）磨坊主在清点货物',
                        'known_by': ['player'],
                        'objectives': ['把柴火送到'],
                        'evidence': [
                            {'kind': 'flag', 'id': 'firewood_delivered'},
                        ],
                        'rewards': [{'kind': 'currency', 'id': 'escort_pay'}],
                        'effects': [
                            {'op': 'flag', 'id': 'mill_refurbished', 'value': True},
                            {'op': 'resource', 'id': 'plank', 'delta': 2},
                        ],
                    },
                    {
                        'id': 'investigate',
                        'giver': 'miller',
                        'location': 'mill',
                        'title': '查清磨坊的怪声',
                        'public_summary': '夜里磨坊有怪声。',
                        'objectives': ['找出声源'],
                        'evidence': [{'kind': 'flag', 'id': 'sound_found'}],
                        'rewards': [{'kind': 'clue', 'text': '声源来自旧粮仓'}],
                        'effects': [
                            {'op': 'information', 'text': '旧粮仓的地板朽了',
                             'confirmed': True, 'known_by': ['player']},
                        ],
                    },
                    {
                        'id': 'repair',
                        'giver': 'miller',
                        'location': 'mill',
                        'title': '修好磨坊的水轮',
                        'public_summary': '水轮坏了，需要木板。',
                        'objectives': ['换下旧木板'],
                        'evidence': [{'kind': 'resource', 'id': 'plank', 'at_least': 2}],
                        'costs': [{'kind': 'resource', 'id': 'plank', 'amount': 2}],
                        'duration': 10,
                        'rewards': [{'kind': 'relationship', 'text': '磨坊主记你一份人情'}],
                        'effects': [
                            {'op': 'flag', 'id': 'mill_working', 'value': True},
                        ],
                    },
                ],
            },
    })
    if extra_mechanics:
        story['mechanics'].update(extra_mechanics)
    return story


def session_for(story, **over):
    session = {'id': 's1', 'revision': 'rev1', 'seed': 'seed-1', 'time': 0,
               'location': 'square', 'explored': ['square'], 'inventory': [],
               'flags': {}, 'facts': [], 'beliefs': [], 'heard': [],
               'characters': {}, 'hero': 'hero', 'facts': [],
               'local': {'resources': {r['id']: r['initial']
                                       for r in story['mechanics']['local']['resources']},
                         'ledger': []}}
    session.update(over)
    return session


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.svc = Service(Store(Path(self.tmp.name) / 'q.sqlite3'), ROOT)
        self.svc.provider.configure({'offline': True})
        self.rt = self.svc.runtime
        self.story = story_with_quests(base=self.rt.package()['story'])
        # ``Runtime.effects`` resolves the package through ``s['revision']``, so the
        # fixture has to be a real package revision rather than an in-memory dict.
        characters = copy.deepcopy(self.rt.package()['characters'])
        self.story['character_package_id'] = characters['id']
        self.revision = self.rt.commit_package(self.story, characters, '任务夹具')

    def session(self, **over):
        rows = session_for(self.story, **over)
        rows['revision'] = self.revision
        return rows

    def effects_fn(self, session, effects, source, claims):
        return self.rt.effects(session, effects, source, claims)


class ConfigTests(Base):
    def test_absent_key_is_a_no_op(self):
        story = story_with_quests(base=self.story)
        story['mechanics'].pop('quests')
        self.assertIsNone(quests.rules(story))
        self.assertIsNone(quests.validate(story))
        self.assertEqual(quests.available(self.session(), story), [])
        self.assertEqual(quests.actions(self.session(), story), [])

    def test_currency_reward_needs_a_declared_payer(self):
        story = story_with_quests(base=self.story)
        story['mechanics']['quests']['quests'][0]['rewards'][0]['payer'] = 'nobody'
        with self.assertRaises(quests.QuestError) as caught:
            quests.validate(story)
        self.assertIn('未声明的账户', str(caught.exception))

    def test_currency_reward_cannot_exceed_the_account(self):
        story = story_with_quests(base=self.story)
        story['mechanics']['quests']['quests'][0]['rewards'][0]['amount'] = 99999
        with self.assertRaises(quests.QuestError):
            quests.validate(story)

    def test_item_reward_must_be_a_declared_template(self):
        story = story_with_quests(base=self.story)
        story['mechanics']['quests']['quests'][0]['rewards'] = [
            {'kind': 'item', 'id': 'no-such-template'}]
        with self.assertRaises(quests.QuestError):
            quests.validate(story)

    def test_a_quest_that_changes_nothing_is_refused(self):
        story = story_with_quests(base=self.story)
        quest = story['mechanics']['quests']['quests'][0]
        quest['rewards'] = []
        quest['effects'] = []
        with self.assertRaises(quests.QuestError) as caught:
            quests.validate(story)
        self.assertIn('什么都不变', str(caught.exception))

    def test_deadline_and_duration_are_mutually_exclusive(self):
        story = story_with_quests(base=self.story)
        story['mechanics']['quests']['quests'][0]['deadline'] = 50
        story['mechanics']['quests']['quests'][0]['duration'] = 10
        with self.assertRaises(ValueError):
            quests.rules(story)

    def test_on_failure_must_point_at_a_declared_quest(self):
        story = story_with_quests(base=self.story)
        story['mechanics']['quests']['quests'][0]['on_failure'] = 'ghost'
        with self.assertRaises(quests.QuestError):
            quests.validate(story)

    def test_on_failure_cycle_is_refused(self):
        story = story_with_quests(base=self.story)
        rows = story['mechanics']['quests']['quests']
        rows[0]['on_failure'] = rows[1]['id']
        rows[1]['on_failure'] = rows[0]['id']
        with self.assertRaises(quests.QuestError) as caught:
            quests.validate(story)
        self.assertIn('环', str(caught.exception))

    def test_unknown_effect_resource_is_refused(self):
        story = story_with_quests(base=self.story)
        story['mechanics']['quests']['quests'][0]['effects'][1]['id'] = 'gold'
        with self.assertRaises(quests.QuestError):
            quests.validate(story)

    def test_unknown_key_is_refused(self):
        story = story_with_quests(base=self.story)
        story['mechanics']['quests']['quests'][0]['free_money'] = 1
        with self.assertRaises(ValueError):
            quests.rules(story)


class StateMachineTests(Base):
    def test_full_escort_flow(self):
        session = self.session()
        quests.propose(session, self.story, 'escort')
        self.assertEqual(
            quests.state(session, quests.rules(self.story))['entries']['escort']['state'],
            'proposed')
        quests.accept(session, self.story, 'escort')
        quests.start(session, self.story, 'escort')
        # the evidence is not there yet, so completion is refused
        with self.assertRaises(quests.QuestError):
            quests.apply_completion(session, self.story, 'escort',
                                    effects_fn=self.effects_fn)
        # the delivery happens, then the same call succeeds
        session['flags']['firewood_delivered'] = True
        result = quests.apply_completion(session, self.story, 'escort',
                                         effects_fn=self.effects_fn)
        self.assertTrue(result['changed'])

    def test_cannot_complete_without_evidence(self):
        session = self.session()
        quests.accept(session, self.story, 'escort')
        quests.start(session, self.story, 'escort')
        with self.assertRaises(quests.QuestError) as caught:
            quests.apply_completion(session, self.story, 'escort',
                                    effects_fn=self.effects_fn)
        self.assertIn('还不能完成', str(caught.exception))
        self.assertFalse(session['flags'].get('mill_refurbished'), '拒收时不应写半截')

    def test_cannot_start_before_accept(self):
        session = self.session()
        quests.propose(session, self.story, 'escort')
        with self.assertRaises(quests.QuestError):
            quests.start(session, self.story, 'escort')

    def test_cancel_is_not_fatal(self):
        session = self.session()
        quests.accept(session, self.story, 'escort')
        result = quests.cancel(session, self.story, 'escort', reason='不想去')
        self.assertEqual(result['state'], 'cancelled')
        self.assertEqual(quests.available(session, self.story), [], '取消后不再提供')

    def test_unknown_quest_id_is_refused(self):
        session = self.session()
        with self.assertRaises(quests.QuestError):
            quests.accept(session, self.story, 'ghost')


class CompletionTests(Base):
    def ready(self, **over):
        session = self.session(**over)
        quests.accept(session, self.story, 'escort')
        quests.start(session, self.story, 'escort')
        session['flags']['firewood_delivered'] = True
        return session

    def test_escort_pays_from_the_declared_account_and_changes_the_place(self):
        session = self.ready()
        result = quests.apply_completion(session, self.story, 'escort',
                                         effects_fn=self.effects_fn)
        self.assertTrue(result['changed'])
        self.assertEqual(result['state'], 'completed')
        self.assertTrue(session['flags']['mill_refurbished'], '地方后果要真的落下来')
        self.assertEqual(session['local']['resources']['plank'], 6, '资源 +2')
        wallet = session['rewards']['wallet']['coin']
        self.assertEqual(wallet, 30)
        self.assertEqual(session['rewards']['accounts']['miller'], 470, 'payer 要真的被扣')

    def test_repeating_completion_does_not_pay_twice(self):
        session = self.ready()
        first = quests.apply_completion(session, self.story, 'escort',
                                        effects_fn=self.effects_fn)
        wallet = session['rewards']['wallet']['coin']
        second = quests.apply_completion(session, self.story, 'escort',
                                         effects_fn=self.effects_fn)
        self.assertTrue(first['changed'])
        self.assertFalse(second['changed'])
        self.assertEqual(session['rewards']['wallet']['coin'], wallet, '不重复发奖')
        self.assertEqual(len(session['rewards']['items']), 0)

    def test_unaffordable_cost_writes_nothing_at_all(self):
        session = self.ready()
        session['local']['resources']['plank'] = 1        # 维修要 2 块
        quests.accept(session, self.story, 'repair')
        quests.start(session, self.story, 'repair')
        before = copy.deepcopy(session)
        with self.assertRaises(quests.QuestError):
            quests.apply_completion(session, self.story, 'repair',
                                    effects_fn=self.effects_fn)
        self.assertEqual(session, before, '整批零写：什么都没变')

    def test_repair_spends_material_and_marks_the_facility(self):
        session = self.session()
        quests.accept(session, self.story, 'repair')
        quests.start(session, self.story, 'repair')
        result = quests.apply_completion(session, self.story, 'repair',
                                         effects_fn=self.effects_fn)
        self.assertTrue(result['changed'])
        self.assertEqual(session['local']['resources']['plank'], 2, '4 − 2 成本')
        self.assertTrue(session['flags']['mill_working'])

    def test_investigation_leaves_a_confirmed_fact_for_the_player_only(self):
        session = self.session()
        quests.accept(session, self.story, 'investigate')
        quests.start(session, self.story, 'investigate')
        session['flags']['sound_found'] = True
        quests.apply_completion(session, self.story, 'investigate',
                                effects_fn=self.effects_fn)
        texts = [row['text'] for row in session['facts']]
        self.assertIn('旧粮仓的地板朽了', texts)
        self.assertEqual(session['beliefs'], [], '没声明给谁就不写进别人的信念')

    def test_completion_without_effects_fn_is_refused(self):
        session = self.ready()
        with self.assertRaises(quests.QuestError):
            quests.apply_completion(session, self.story, 'escort')


class DeadlineTests(Base):
    def test_duration_is_fixed_on_accept_from_the_one_clock(self):
        session = self.session(time=100)
        quests.accept(session, self.story, 'repair')
        row = quests.state(session, quests.rules(self.story))['entries']['repair']
        self.assertEqual(row['due'], 110)
        self.assertEqual(quests.due_at(session, 'repair', self.story), 110)

    def test_reading_does_not_advance_or_expire(self):
        session = self.session(time=100)
        quests.accept(session, self.story, 'repair')
        session['time'] = 999
        before = copy.deepcopy(session)
        quests.due_at(session, 'repair', self.story)
        quests.public_view(session, self.story)
        quests.actions(session, self.story)
        self.assertEqual(session, before, 'GET 类调用不推进任务')
        self.assertEqual(quests.state(session, quests.rules(self.story))
                         ['entries']['repair']['state'], 'accepted')

    def test_expire_fails_and_continues_to_the_successor(self):
        session = self.session(time=100)
        quests.accept(session, self.story, 'repair')
        session['time'] = 200
        result = quests.expire(session, self.story)
        self.assertEqual(result['expired'][0]['quest_id'], 'repair')
        row = quests.state(session, quests.rules(self.story))['entries']['repair']
        self.assertEqual(row['state'], 'failed')
        offers = [o for o in quests.actions(session, self.story)
                  if o['quest_id'] == 'repair']
        self.assertEqual(offers, [], '失败的那条不再可交')

    def test_expire_is_idempotent(self):
        session = self.session(time=100)
        quests.accept(session, self.story, 'repair')
        session['time'] = 200
        quests.expire(session, self.story)
        again = quests.expire(session, self.story)
        self.assertEqual(again['expired'], [], '已失败的不重复记')


class AudienceTests(Base):
    def test_hidden_quest_never_appears(self):
        story = story_with_quests(base=self.story)
        story['mechanics']['quests']['quests'][1]['public_summary'] = ''
        session = self.session()
        ids = [row['quest_id'] for row in quests.available(session, story)]
        self.assertNotIn('investigate', ids)

    def test_reveal_flag_gates_the_quest(self):
        story = story_with_quests(base=self.story)
        story['mechanics']['quests']['quests'][0]['reveal_flag'] = 'heard_rumour'
        session = self.session()
        self.assertEqual(quests.available(session, story), [])
        session['flags']['heard_rumour'] = True
        self.assertTrue(quests.available(session, story))

    def test_known_by_limits_the_audience(self):
        story = story_with_quests(base=self.story)
        story['mechanics']['quests']['quests'][0]['known_by'] = ['npc1']
        session = self.session()
        self.assertEqual(quests.available(session, story, 'player'), [])
        self.assertTrue(quests.available(session, story, 'npc1'))

    def test_projection_carries_no_secret_or_payment_detail(self):
        session = self.session()
        rows = quests.public_view(session, self.story)
        blob = str(rows)
        for secret in ('隐藏', 'miller', 'payer', 'coin'):
            self.assertNotIn(secret, blob, '玩家投影不得包含 %r' % secret)

    def test_location_gates_a_far_quest(self):
        session = self.session(location='square', explored=['square'])
        ids = [row['quest_id'] for row in quests.available(session, self.story)]
        self.assertIn('escort', ids)
        self.assertNotIn('investigate', ids, '磨坊还没到过')

    def test_author_view_keeps_everything(self):
        session = self.session()
        view = quests.authority_view(session, self.story, 'escort')
        row = view['quests'][0]
        self.assertIn('隐藏', row['secret_objective'])
        self.assertEqual(row['rewards'][0]['payer'], 'miller')


class ActionTests(Base):
    def test_offer_follows_the_state(self):
        session = self.session()
        offers = quests.actions(session, self.story)
        self.assertEqual([o['transition'] for o in offers if o['quest_id'] == 'escort'],
                         ['accept'])
        quests.accept(session, self.story, 'escort')
        offers = quests.actions(session, self.story)
        self.assertEqual([o['transition'] for o in offers if o['quest_id'] == 'escort'],
                         ['start'])

    def test_incomplete_offer_is_marked_unsupported_with_a_reason(self):
        session = self.session()
        quests.accept(session, self.story, 'escort')
        quests.start(session, self.story, 'escort')
        offers = quests.actions(session, self.story)
        escort = [o for o in offers if o['quest_id'] == 'escort'][0]
        self.assertFalse(escort['supported'])
        self.assertIn('还差', escort['obstruction'])

    def test_apply_transition_dispatches(self):
        session = self.session()
        quests.apply_transition(session, self.story, 'escort', 'accept')
        row = quests.state(session, quests.rules(self.story))['entries']['escort']
        self.assertEqual(row['state'], 'accepted')
        with self.assertRaises(quests.QuestError):
            quests.apply_transition(session, self.story, 'escort', 'teleport')


class SnapshotTests(Base):
    def test_quest_state_rolls_back_with_the_session(self):
        session = self.session()
        quests.accept(session, self.story, 'escort')
        snapshot = copy.deepcopy(session)
        session['flags']['firewood_delivered'] = True
        quests.start(session, self.story, 'escort')
        # rolling back to the snapshot drops the quest progress too
        session.clear()
        session.update(copy.deepcopy(snapshot))
        row = quests.state(session, quests.rules(self.story))['entries']['escort']
        self.assertEqual(row['state'], 'accepted')
        self.assertNotIn('firewood_delivered', session['flags'])


if __name__ == '__main__':
    unittest.main()
