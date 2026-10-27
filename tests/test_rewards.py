"""Rewards: deterministic generation, batch atomicity, idempotent grants, isolation."""
import asyncio
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import rewards as R
from app.contracts import Turn
from app.service import Service
from app.storage import Store
from app.web import create_app

ROOT = Path(__file__).resolve().parents[1]
FRAGMENT = ROOT / 'docs/examples/rewards-demo.story-fragment.json'


def fragment():
    return json.loads(FRAGMENT.read_text(encoding='utf-8'))['mechanics']['rewards']


class RewardCase(unittest.TestCase):
    """Every test runs on its own temporary database; the real save is never touched."""

    use_config = True

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'rewards.sqlite3'
        self.svc = Service(Store(self.path), ROOT)
        self.svc.provider.configure({'offline': True})
        self.rt = self.svc.runtime
        if self.use_config:
            package = copy.deepcopy(self.rt.package())
            # A fresh deep copy per test: one test mutating its config must not leak.
            package['story'].setdefault('mechanics', {})['rewards'] = fragment()
            self.config_declare(package['story'])
            self.rt.commit_package(package['story'], package['characters'], '奖励测试配置')
        self.s = self.rt.new_session('奖励测试', 'protagonist')

    def config_declare(self, story):
        story['events'][0]['actions'][0]['rewards'] = {'success': ['coin_small', 'charm']}

    def tearDown(self):
        self.tmp.cleanup()

    def turn(self, action=None, message='继续'):
        asyncio.run(self.svc.turn(self.s['id'], Turn(message=message, action_id=action)))
        self.s = self.svc.store.session(self.s['id'])

    def story(self):
        return self.rt.package(self.s['revision'])['story']

    def reload(self):
        self.s = self.svc.store.session(self.s['id'])
        return self.s


class UnconfiguredTests(RewardCase):
    """An untouched package must behave exactly as before this feature existed."""

    use_config = False

    def test_no_reward_keys_and_no_state_block(self):
        self.turn('pack')
        surface = self.rt.surface(self.s)
        self.assertNotIn('rewards', surface)
        self.assertEqual(surface['inventory'], ['万言机'])
        context = self.rt.context(self.s, 'player', '背包', self.svc.preferences())
        self.assertNotIn('current_rewards', context)
        self.assertNotIn('rewards', self.s)

    def test_reward_effect_rejected_without_config(self):
        self.rt.effects(self.s, [], 'test:noop')
        with self.assertRaisesRegex(ValueError, 'mechanics.rewards'):
            self.rt.effects(self.s, [], 'test:x', [{'entry': 'anything'}])
        # A declaration in the package is a config error, not a silent no-op.
        package = copy.deepcopy(self.rt.package())
        package['story']['events'][0]['actions'][0]['rewards'] = {'success': ['coin_small']}
        with self.assertRaisesRegex(ValueError, 'mechanics.rewards'):
            self.rt.commit_package(package['story'], package['characters'], '非法声明')

    def test_legacy_save_not_rewritten_by_reads(self):
        self.turn('pack')
        before = self.svc.store.session(self.s['id'])
        for _ in range(3):
            self.rt.surface(before)
            self.rt.context(before, 'player', '看看', self.svc.preferences())
        after = self.svc.store.session(self.s['id'])
        self.assertEqual(before, after)
        self.assertEqual(after['state_version'], before['state_version'])


class ConfigTests(RewardCase):
    use_config = False

    def test_strict_numbers_reject_bool_nan_and_overlaps(self):
        for mutate in (
            lambda c: c['currencies'][0].__setitem__('maximum', True),
            lambda c: c['currencies'][0].__setitem__('maximum', float('nan')),
            lambda c: c['templates'][0].__setitem__('weight', 1.5),
            lambda c: c['rewards'][0].__setitem__('amount_min', 20),
            lambda c: c['templates'].append({**c['templates'][1], 'id': 'bad', 'enchantments': ['ward', 'gloom']}),
            lambda c: c['abilities'][1].__setitem__('requires', ['missing']),
            lambda c: c['rewards'].append({'id': 'ghost', 'kind': 'item', 'templates': ['nope']}),
            lambda c: c['rewards'].append({'id': 'pay', 'kind': 'currency', 'currency': 'coin', 'payer': 'purse', 'amount_min': 1, 'amount_max': 1}),
            lambda c: c['tables'][0]['entries'].append({'reward': 'missing', 'weight': 1}),
            lambda c: c['tables'][0]['entries'].append({'reward': 'blade', 'weight': 1}),
            lambda c: c['tables'][0]['entries'][0].__setitem__('weight', 0),
            lambda c: c['abilities'][0].__setitem__('requires', ['deep_skill']),
            lambda c: c['rewards'].append({'id': 'odd', 'kind': 'ability', 'ability': 'sea_reading', 'templates': ['iron_blade']}),
            lambda c: c['rewards'].append({'id': 'odd2', 'kind': 'item', 'templates': ['iron_blade'], 'amount_min': 3}),
            lambda c: c.__setitem__('version', True),
            lambda c: c['templates'].append({**c['templates'][1], 'id': 'zero_mana', 'mana_capacity': 0}),
            lambda c: c['templates'].append({**c['templates'][0], 'id': 'dupe', 'enchantments': ['ward', 'ward']}),
        ):
            with self.subTest(mutate=mutate):
                package = copy.deepcopy(self.rt.package())
                config = fragment()
                mutate(config)
                package['story'].setdefault('mechanics', {})['rewards'] = config
                with self.assertRaises(ValueError):
                    self.rt.commit_package(package['story'], package['characters'], '非法配置')

    def test_reward_amount_must_fit_the_grant_budget(self):
        # Budget is 5000 in the example; anything above it must be refused at commit.
        for mutate in (
            lambda c: c['rewards'][0].__setitem__('amount_max', 6000),
            lambda c: (c['rewards'][0].__setitem__('amount_min', 6000),
                       c['rewards'][0].__setitem__('amount_max', 6000)),
            lambda c: c['tables'][0]['entries'][0].__setitem__('weight', 0),
        ):
            package = copy.deepcopy(self.rt.package())
            config = fragment()
            mutate(config)
            package['story'].setdefault('mechanics', {})['rewards'] = config
            with self.assertRaises(ValueError):
                self.rt.commit_package(package['story'], package['characters'], '超预算')

    def test_lowered_budget_vs_declared_amount(self):
        package = copy.deepcopy(self.rt.package())
        config = fragment()
        config['max_value_per_grant'] = 4
        package['story'].setdefault('mechanics', {})['rewards'] = config
        with self.assertRaisesRegex(ValueError, '预算'):
            self.rt.commit_package(package['story'], package['characters'], '预算过低')

    def test_table_and_entry_ids_must_not_collide(self):
        package = copy.deepcopy(self.rt.package())
        config = fragment()
        config['tables'][0]['id'] = 'coin_small'
        package['story'].setdefault('mechanics', {})['rewards'] = config
        with self.assertRaisesRegex(ValueError, '同一个ID'):
            self.rt.commit_package(package['story'], package['characters'], 'ID冲突')

    def test_unknown_action_reward_rejected(self):
        package = copy.deepcopy(self.rt.package())
        package['story'].setdefault('mechanics', {})['rewards'] = fragment()
        package['story']['events'][0]['actions'][0]['rewards'] = {'success': ['nope']}
        with self.assertRaisesRegex(ValueError, '未定义'):
            self.rt.commit_package(package['story'], package['characters'], '非法引用')

    def test_author_endpoint_is_read_only_and_hidden_from_player(self):
        package = copy.deepcopy(self.rt.package())
        package['story'].setdefault('mechanics', {})['rewards'] = fragment()
        self.rt.commit_package(package['story'], package['characters'], '配置奖励')
        with TestClient(create_app(Path(self.tmp.name) / 'web.sqlite3')) as client:
            boot = client.get('/api/bootstrap').json()
            headers = {'X-TextileDream-Token': boot['token']}
            self.assertEqual(client.get('/api/inner/rewards').status_code, 403)
            data = client.get('/api/inner/rewards', headers=headers).json()
            self.assertTrue(data['configured'])
            self.assertEqual(data['rules']['version'], 1)
            self.assertIn('weight', data['derivation'])
            session = client.post('/api/sessions', headers=headers, json={}).json()
            player = client.get('/api/sessions/' + session['id']).json()
            self.assertNotIn('grants', player['rewards'])
            self.assertNotIn('ledger', player['rewards'])
            full = client.get('/api/inner/rewards?session=' + session['id'], headers=headers).json()
            self.assertIn('grants', full['journey'])


class RevisionIsolationTests(RewardCase):
    """A journey keeps its own package version; the author query must follow it."""

    def test_journey_query_uses_the_bound_revision(self):
        """The query must read the journey's own config, not the newer active one."""
        old_revision = self.s['revision']
        old_cfg = R.rules(self.story())
        # Grant on the old revision first, so the journey holds an instance whose
        # material only the old revision names that way.
        candidate = copy.deepcopy(self.s)
        applied, _ = R.apply(candidate, old_cfg, [{'entry': 'relic'}], 'departure:pack')
        self.assertEqual(applied['items'][0]['template'], 'hidden_charm')
        self.s['rewards'] = applied
        self.svc.store.save_session(self.s)

        # A *valid* new revision: the jade material is renamed and the charm entry is
        # removed together with the table entry that referenced it.
        package = copy.deepcopy(self.rt.package())
        rewards = package['story']['mechanics']['rewards']
        jade = next(x for x in rewards['materials'] if x['id'] == 'jade')
        jade['name'] = '改名后的青玉'
        rewards['rewards'] = [x for x in rewards['rewards'] if x['id'] != 'charm']
        rewards['tables'][0]['entries'] = [x for x in rewards['tables'][0]['entries']
                                           if x['reward'] != 'charm']
        # Every reference must stay valid: the action declared `charm` as a reward.
        for action in package['story']['events'][0]['actions']:
            declared = action.get('rewards')
            if declared:
                action['rewards'] = {k: [x for x in v if x != 'charm'] for k, v in declared.items()}
        new_revision = self.rt.commit_package(package['story'], package['characters'], '改过的奖励配置')
        self.assertNotEqual(new_revision, old_revision)
        self.assertEqual(self.rt.package()['id'], new_revision)

        self.reload()
        self.assertEqual(self.s['revision'], old_revision)
        with TestClient(create_app(self.path)) as client:
            headers = {'X-TextileDream-Token': client.get('/api/bootstrap').json()['token']}
            full = client.get('/api/inner/rewards?session=' + self.s['id'], headers=headers).json()
            self.assertEqual(full['revision'], old_revision)
            self.assertEqual(full['journey_revision'], old_revision)
            self.assertTrue(full['configured'])
            # The newer revision deleted `charm`; the journey's revision still has it.
            self.assertIn('charm', [x['id'] for x in full['rules']['rewards']])
            self.assertEqual(full['rules']['materials'][0]['name'], '生铁')
            # The decisive check: the held instance projects through the OLD material
            # name. Using the active config would say 改名后的青玉 instead.
            instances = full['journey']['projection']['items']
            self.assertTrue(instances)
            self.assertEqual(instances[0]['material'], '青玉')
            self.assertNotEqual(instances[0]['material'], '改名后的青玉')
            self.assertTrue(full['journey']['grants'])
            # Read-only: the query must not bump the journey version or mutate state.
            before = self.svc.store.session(self.s['id'])
            client.get('/api/inner/rewards?session=' + self.s['id'], headers=headers)
            self.assertEqual(self.svc.store.session(self.s['id']), before)

    def test_journey_query_when_current_package_has_no_rewards(self):
        old_revision = self.s['revision']
        package = copy.deepcopy(self.rt.package())
        package['story']['mechanics'].pop('rewards', None)
        package['story']['events'][0]['actions'][0].pop('rewards', None)
        self.rt.commit_package(package['story'], package['characters'], '去掉奖励配置')
        self.turn('pack')
        self.reload()
        self.assertEqual(self.s['revision'], old_revision)
        with TestClient(create_app(self.path)) as client:
            headers = {'X-TextileDream-Token': client.get('/api/bootstrap').json()['token']}
            active = client.get('/api/inner/rewards', headers=headers).json()
            self.assertFalse(active['configured'])
            journey = client.get('/api/inner/rewards?session=' + self.s['id'], headers=headers).json()
            self.assertEqual(journey['journey_revision'], old_revision)
            self.assertTrue(journey['configured'])
            self.assertTrue(journey['rules']['rewards'])
            self.assertTrue(journey['journey']['grants'])
            self.assertEqual(len(self.svc.store.session(self.s['id'])['rewards']['grants']),
                             len(journey['journey']['grants']))


class DeterminismTests(RewardCase):

    def test_same_seed_same_items_different_seed_differs(self):
        cfg = R.rules(self.story())
        claims = [{'entry': 'charm'}, {'entry': 'coin_small'}]
        first, _ = R.apply(copy.deepcopy(self.s), cfg, claims, 'ev:act')
        again, _ = R.apply(copy.deepcopy(self.s), cfg, claims, 'ev:act')
        self.assertEqual(first, again)
        other = copy.deepcopy(self.s)
        other['seed'] = 'another-seed'
        third, _ = R.apply(other, cfg, claims, 'ev:act')
        self.assertNotEqual(first['items'], third['items'])
        # A different source action is a different grant (and a different roll stream).
        fourth, _ = R.apply(copy.deepcopy(self.s), cfg, claims, 'ev:other')
        self.assertNotEqual([x['id'] for x in first['items']], [x['id'] for x in fourth['items']])
        # The roll stream is a function of the grant identity plus the rules version.
        seed = R._rolls(R.grant_id(self.s, 'ev:act', 'charm')).seed
        self.assertIn(R.RULES_VERSION, seed)
        self.assertIn(R.grant_id(self.s, 'ev:act', 'charm'), seed)
        # Instance identity never depends on list position inside a batch.
        alone, _ = R.apply(copy.deepcopy(self.s), cfg, [{'entry': 'charm'}], 'ev:act')
        paired, _ = R.apply(copy.deepcopy(self.s), cfg,
                            [{'entry': 'coin_small'}, {'entry': 'charm'}], 'ev:act')
        self.assertEqual(alone['items'][0]['id'], paired['items'][0]['id'])
        self.assertEqual(alone['items'][0], paired['items'][0])

    def test_rollback_and_replay_regenerate_identical_rewards(self):
        self.turn('pack')
        self.reload()
        original = copy.deepcopy(self.s['rewards'])
        self.assertTrue(original['items'] or original['wallet'])
        archive = self.s['archives'][-1]['id']
        self.s = self.rt.rollback(self.s, archive)
        self.assertEqual(self.s['rewards']['wallet']['coin'], 0)
        self.assertEqual(self.s['rewards']['items'], [])
        self.assertEqual(self.s['rewards']['grants'], [])
        self.turn('pack')
        self.reload()
        self.assertEqual(self.s['rewards']['wallet'], original['wallet'])
        self.assertEqual(self.s['rewards']['items'], original['items'])
        self.assertEqual([g['id'] for g in self.s['rewards']['grants']],
                         [g['id'] for g in original['grants']])

    def test_instance_ids_do_not_collide_across_journeys(self):
        other = self.rt.new_session('另一段', 'protagonist')
        cfg = R.rules(self.story())
        one, _ = R.apply(copy.deepcopy(self.s), cfg, [{'entry': 'blade'}], 'ev:act')
        two, _ = R.apply(copy.deepcopy(other), cfg, [{'entry': 'blade'}], 'ev:act')
        self.assertNotEqual(one['items'][0]['id'], two['items'][0]['id'])

    def test_no_python_hash_or_clock_in_generation(self):
        text = (ROOT / 'app/rewards.py').read_text(encoding='utf-8')
        code = '\n'.join(line for line in text.splitlines() if not line.strip().startswith('#'))
        for forbidden in ('hash(', 'time.time', 'random.', 'datetime', 'eval(', 'exec('):
            self.assertNotIn(forbidden, code)


class BatchTests(RewardCase):

    def test_whole_batch_rejected_on_late_failure(self):
        package = copy.deepcopy(self.rt.package())
        package['story']['mechanics']['rewards']['max_grants_per_event'] = 1
        self.rt.commit_package(package['story'], package['characters'], '单次上限')
        self.s = self.rt.new_session('单次上限', 'protagonist')
        candidate = copy.deepcopy(self.s)
        before = copy.deepcopy(candidate.get('rewards'))
        with self.assertRaisesRegex(ValueError, '上限'):
            self.rt.effects(candidate, [], 'ev:act', [{'entry': 'coin_small'}, {'entry': 'blade'}])
        self.assertEqual(candidate.get('rewards'), before)

    def test_batch_limits_are_cumulative_per_event(self):
        package = copy.deepcopy(self.rt.package())
        package['story']['mechanics']['rewards']['max_grants_per_event'] = 2
        self.rt.commit_package(package['story'], package['characters'], '事件上限')
        self.s = self.rt.new_session('事件上限', 'protagonist')
        candidate = copy.deepcopy(self.s)
        cfg = R.rules(self.story())
        applied, _ = R.apply(candidate, cfg, [{'entry': 'coin_small'}], 'ev:a')
        candidate['rewards'] = applied
        # Same entry, same action: idempotent, not a second payout.
        again, audits = R.apply(candidate, cfg, [{'entry': 'coin_small'}], 'ev:a')
        self.assertEqual(again['wallet'], applied['wallet'])
        self.assertEqual(audits, [])
        # A different source in the same event still counts against the event budget,
        # and the third new grant is refused: the budget is cumulative, not per turn.
        applied, _ = R.apply(candidate, cfg, [{'entry': 'blade'}], 'ev:b')
        candidate['rewards'] = applied
        with self.assertRaisesRegex(ValueError, '上限'):
            R.apply(candidate, cfg, [{'entry': 'charm'}], 'ev:c')

    def test_currency_cap_rejects_whole_batch(self):
        package = copy.deepcopy(self.rt.package())
        package['story']['mechanics']['rewards']['currencies'][0]['maximum'] = 20
        self.rt.commit_package(package['story'], package['characters'], '低上限')
        self.s = self.rt.new_session('低上限', 'protagonist')
        candidate = copy.deepcopy(self.s)
        candidate['rewards'] = R.blank(R.rules(self.story()))
        candidate['rewards']['wallet']['coin'] = 19
        cfg = R.rules(self.story())
        with self.assertRaisesRegex(ValueError, '上限'):
            R.apply(candidate, cfg, [{'entry': 'coin_small'}], 'ev:a')
        self.assertEqual(candidate['rewards']['wallet']['coin'], 19)

    def test_payer_debits_supply_account_in_the_same_batch(self):
        package = copy.deepcopy(self.rt.package())
        package['story']['mechanics']['rewards']['accounts'] = [
            {'id': 'merchant_purse', 'name': '商家钱袋', 'currency': 'coin', 'initial': 10}]
        rewards = package['story']['mechanics']['rewards']
        paid = next(x for x in rewards['rewards'] if x['id'] == 'coin_from_purse')
        self.assertEqual(paid['payer'], 'merchant_purse')
        rewards['rewards'] = [x for x in rewards['rewards']
                              if x['kind'] == 'currency' and x['id'] == 'coin_from_purse']
        rewards['tables'] = []
        package['story']['events'][0]['actions'][0]['rewards'] = {'success': ['coin_from_purse']}
        self.rt.commit_package(package['story'], package['characters'], '付款账户')
        self.s = self.rt.new_session('付款', 'protagonist')
        cfg = R.rules(self.story())
        session = copy.deepcopy(self.s)
        self.assertEqual(R.state(session, cfg)['accounts']['merchant_purse'], 10)
        applied, audits = R.apply(session, cfg, [{'entry': 'coin_from_purse'}], 'ev:a')
        # Same currency, one account debited, player wallet credited; nothing minted.
        self.assertEqual(applied['accounts']['merchant_purse'], 4)
        self.assertEqual(applied['wallet']['coin'], 6)
        self.assertEqual(audits[0]['payer']['before'], 10)
        # The debit stays traceable in the author ledger after the batch returns.
        self.assertEqual(applied['ledger'][0]['account'],
                         {'id': 'merchant_purse', 'currency': 'coin', 'before': 10, 'after': 4})
        self.assertEqual(applied['grants'][0]['account']['after'], 4)
        # An under-funded account refuses the whole batch.
        poor = copy.deepcopy(session)
        poor['rewards'] = R.blank(cfg)
        poor['rewards']['accounts']['merchant_purse'] = 5
        with self.assertRaisesRegex(ValueError, '余额不足'):
            R.apply(poor, cfg, [{'entry': 'coin_from_purse'}], 'ev:a')
        self.assertEqual(poor['rewards']['wallet']['coin'], 0)
        # The supply account is author-only: never in a player projection.
        paid_state = copy.deepcopy(session)
        paid_state['rewards'] = applied
        self.assertNotIn('accounts', R.public_state(paid_state, self.story(), 'player'))
        self.assertEqual(R.public_state(paid_state, self.story(), 'author')['accounts'][0]['amount'], 4)

    def test_ability_prerequisite_and_flags(self):
        candidate = copy.deepcopy(self.s)
        cfg = R.rules(self.story())
        with self.assertRaisesRegex(ValueError, '前置'):
            R.apply(candidate, cfg, [{'entry': 'deep_skill'}], 'ev:a')
        candidate['flags']['tide_heard'] = True
        applied, _ = R.apply(candidate, cfg, [{'entry': 'tide_skill'}, {'entry': 'deep_skill'}], 'ev:a')
        self.assertEqual([x['id'] for x in applied['abilities']], ['sea_reading', 'deep_current'])
        # Repeating an unlocked ability is a no-op rather than a duplicate entry.
        again, audits = R.apply({**candidate, 'rewards': applied}, cfg, [{'entry': 'tide_skill'}], 'ev:a')
        self.assertEqual(len(again['abilities']), 2)
        self.assertEqual(audits, [])

    def test_legacy_effect_failure_leaves_candidate_untouched(self):
        candidate = copy.deepcopy(self.s)
        snapshot = copy.deepcopy(candidate)
        with self.assertRaises(ValueError):
            self.rt.effects(candidate, [{'op': 'reward', 'entry': 'coin_small'},
                                        {'op': 'health', 'delta': -40},
                                        {'op': 'resource', 'id': 'missing', 'delta': 1}], 'ev:act')
        # The trailing resource change fails after the reward and health were applied.
        self.assertEqual(candidate, snapshot)

    def test_instance_value_cap(self):
        package = copy.deepcopy(self.rt.package())
        rewards = package['story']['mechanics']['rewards']
        # Drop the currency entries so the budget only has to accept the item declared below.
        rewards['rewards'] = [x for x in rewards['rewards'] if x['kind'] != 'currency']
        rewards['tables'] = []
        rewards['accounts'] = []
        rewards['max_value_per_grant'] = 1
        package['story']['events'][0]['actions'][0]['rewards'] = {'success': ['blade']}
        self.rt.commit_package(package['story'], package['characters'], '价值上限')
        session = self.rt.new_session('价值上限', 'protagonist')
        cfg = R.rules(self.rt.package(session['revision'])['story'])
        self.assertEqual(cfg.max_value_per_grant, 1)
        with self.assertRaisesRegex(ValueError, '价值'):
            R.apply(copy.deepcopy(session), cfg, [{'entry': 'blade'}], 'ev:a')


class GrantIdempotenceTests(RewardCase):

    def test_repeat_action_does_not_pay_twice(self):
        self.turn('pack')
        first = copy.deepcopy(self.s['rewards'])
        # Re-running the same committed action cannot add value.
        self.rt.effects(self.s, [], 'departure:pack', [{'entry': 'coin_small'}])
        self.assertEqual(self.s['rewards']['wallet'], first['wallet'])
        self.assertEqual(len(self.s['rewards']['grants']), len(first['grants']))

    def test_two_journeys_are_isolated(self):
        self.turn('pack')
        other = self.rt.new_session('隔离', 'protagonist')
        asyncio.run(self.svc.turn(other['id'], Turn(message='整理', action_id='pack')))
        other = self.svc.store.session(other['id'])
        self.assertEqual(self.svc.store.session(self.s['id'])['rewards']['wallet'], self.s['rewards']['wallet'])
        self.assertEqual(len(other['rewards']['items']), len(self.s['rewards']['items']))
        self.assertNotEqual(other['rewards']['grants'][0]['id'], self.s['rewards']['grants'][0]['id'])
        self.assertEqual(other['rewards']['grants'][0]['branch'] != self.s['rewards']['grants'][0]['branch'], True)


class IsolationTests(RewardCase):

    def test_unidentified_item_discloses_nothing_derived(self):
        # `relic` can only produce the hidden template, so the test is deterministic.
        candidate = copy.deepcopy(self.s)
        cfg = R.rules(self.story())
        applied, _ = R.apply(candidate, cfg, [{'entry': 'relic'}], 'ev:a')
        candidate['rewards'] = applied
        instance = applied['items'][0]
        self.assertEqual(instance['template'], 'hidden_charm')
        public = R.public_item(cfg, instance)
        self.assertFalse(public['identified'])
        for hidden in ('damage', 'value', 'durability', 'enchantments', 'material', 'quality'):
            self.assertNotIn(hidden, public)
        self.assertNotIn(instance['name'], json.dumps(public, ensure_ascii=False))
        self.assertEqual(public['figures'], 'visible_estimate')
        author = R.public_state(candidate, self.story(), 'author')
        hidden_item = next(x for x in author['items'] if x['id'] == instance['id'])
        self.assertTrue(hidden_item['identified'] is False)
        self.assertEqual(hidden_item['damage'], instance['stats_cache']['damage'])
        # A modified cache cannot forge the numbers: the view is recomputed from config,
        # and the public value deliberately excludes the hidden contribution.
        forged = copy.deepcopy(candidate)
        target = next(x for x in forged['rewards']['items'] if x['id'] == instance['id'])
        target['identified'] = True
        target['stats_cache']['value'] = 999999999
        view = R.public_item(cfg, target)
        self.assertNotEqual(view['value'], 999999999)
        self.assertEqual(view['value'], R.instance_stats(cfg, target)['value'])
        self.assertLessEqual(view['value'], instance['stats_cache']['value'])
        self.assertEqual(view['figures'], 'visible_estimate')

    def test_hidden_enchantment_and_abilities_stay_author_only(self):
        candidate = copy.deepcopy(self.s)
        candidate['flags']['tide_heard'] = True
        cfg = R.rules(self.story())
        applied, _ = R.apply(candidate, cfg, [{'entry': 'relic'}, {'entry': 'charm'},
                                              {'entry': 'tide_skill'}, {'entry': 'deep_skill'}], 'ev:a')
        candidate['rewards'] = applied
        # Even after identification, a hidden enchantment is never disclosed to the player.
        for instance in applied['items']:
            instance['identified'] = True
        player = R.public_state(candidate, self.story(), 'player')
        self.assertNotIn('潜影', json.dumps(player, ensure_ascii=False))
        self.assertIn('观潮', json.dumps(player, ensure_ascii=False))
        self.assertNotIn('潜流', json.dumps(player, ensure_ascii=False))
        author = R.public_state(candidate, self.story(), 'author')
        self.assertIn('潜影', json.dumps(author, ensure_ascii=False))
        self.assertIn('潜流', json.dumps(author, ensure_ascii=False))
        # NPC viewpoints never receive the player's wallet, items or secret abilities.
        self.assertIsNone(R.public_state(candidate, self.story(), 'pass_guard'))

    def test_hidden_enchantment_does_not_leak_through_numbers(self):
        candidate = copy.deepcopy(self.s)
        cfg = R.rules(self.story())
        applied, _ = R.apply(candidate, cfg, [{'entry': 'relic'}], 'ev:a')
        candidate['rewards'] = applied
        instance = applied['items'][0]
        instance['identified'] = True
        view = R.public_item(cfg, instance)
        # The hidden contribution is excluded, so the public numbers equal a plain jade
        # charm with no enchantment at all.
        plain = copy.deepcopy(instance)
        plain['enchantments'] = []
        baseline = R.public_item(cfg, plain)
        for key in ('damage', 'value', 'durability', 'weight'):
            self.assertEqual(view[key], baseline[key])
        self.assertEqual(view['enchantments'], [])
        # The author view still shows both the hidden name and its contribution.
        author = R.public_state(candidate, self.story(), 'author')['items'][0]
        self.assertGreater(author['damage'], view['damage'])

    def test_table_draws_one_weighted_entry_deterministically(self):
        cfg = R.rules(self.story())
        first, audits = R.apply(copy.deepcopy(self.s), cfg, [{'entry': 'dock_loot'}], 'ev:act')
        again, _ = R.apply(copy.deepcopy(self.s), cfg, [{'entry': 'dock_loot'}], 'ev:act')
        self.assertEqual(first, again)
        self.assertEqual(len(audits), 1)
        self.assertIn(audits[0]['reward'], {x.reward for x in cfg.tables[0].entries})
        # A different source action draws from the same table with its own stream, so the
        # outcome may differ; what must hold is that it stays a single valid entry.
        other, other_audits = R.apply(copy.deepcopy(self.s), cfg, [{'entry': 'dock_loot'}], 'ev:other')
        self.assertEqual(len(other_audits), 1)
        self.assertIn(other_audits[0]['reward'], {x.reward for x in cfg.tables[0].entries})
        self.assertEqual(len(other['grants']), 1)
        # Weight distribution is respected over many seeds, and never leaves the table.
        counts = {}
        for index in range(60):
            session = copy.deepcopy(self.s)
            session['seed'] = f'seed-{index}'
            drawn, _ = R.apply(session, cfg, [{'entry': 'dock_loot'}], 'ev:act')
            picked = drawn['grants'][0]['reward']
            self.assertIn(picked, {x.reward for x in cfg.tables[0].entries})
            counts[picked] = counts.get(picked, 0) + 1
        self.assertGreater(counts.get('coin_small', 0), counts.get('charm', 0))

    def test_table_reference_in_action_is_validated(self):
        package = copy.deepcopy(self.rt.package())
        package['story']['mechanics']['rewards'] = fragment()
        package['story']['events'][0]['actions'][0]['rewards'] = {'success': ['dock_loot']}
        revision = self.rt.commit_package(package['story'], package['characters'], '奖励表引用')
        session = self.rt.new_session('奖励表', 'protagonist')
        self.assertEqual(session['revision'], revision)
        self.turn('pack')

    def test_summary_and_anchor_use_public_projection_only(self):
        self.turn('pack')
        self.reload()
        summary = self.s['archives'][-1]['summary']
        cfg = R.rules(self.story())
        public = R.public_state(self.s, self.story(), 'player')
        self.assertTrue(public['items'])
        self.assertIn('物品 +', summary)
        for item in public['items']:
            self.assertIn(item['label'], summary)
            self.assertNotIn(item['label'], ('暗影护符', '青玉护符'))
        context = self.rt.context(self.s, 'player', '查看', self.svc.preferences())
        anchor = context['current_anchor']['inventory']
        self.assertEqual(anchor, ['万言机'] + [x['label'] for x in public['items']])
        text = json.dumps(context, ensure_ascii=False)
        for template in cfg.templates:
            self.assertNotIn(template.name, text)
        npc = self.rt.context(self.s, 'pass_guard', '', self.svc.preferences())
        self.assertNotIn('current_rewards', npc)
        self.assertEqual(json.dumps(npc, ensure_ascii=False).count('暗影护符'), 0)


class ProviderBoundaryTests(RewardCase):

    def test_model_input_has_no_reward_audit(self):
        import httpx
        self.svc.provider.configure({'base_url': 'https://api.deepseek.com', 'model': 'deepseek-chat',
                                     'api_key': 'test-only', 'offline': False, 'max_tokens': 1200})
        sent = []

        def respond(request):
            sent.append(json.loads(request.content))
            return httpx.Response(200, json={'choices': [{'finish_reason': 'stop',
                                                          'message': {'content': '正文'}}], 'usage': {}})

        original = httpx.AsyncClient
        with patch('app.provider.httpx.AsyncClient',
                   side_effect=lambda **kw: original(transport=httpx.MockTransport(respond), **kw)):
            asyncio.run(self.svc.turn(self.s['id'], Turn(message='整理', action_id='pack')))
        payload = json.loads(sent[0]['messages'][1]['content'])
        resolved = payload['resolved_action']
        # The audit trail (before/after, template, hidden levels) never reaches the model.
        self.assertNotIn('reward_audit', resolved)
        self.assertIn('rewards', resolved)
        text = json.dumps(payload, ensure_ascii=False)
        for internal in ('origin_result_id', 'stats_cache', 'ledger', 'grants', 'origin_source'):
            self.assertNotIn(internal, text)
        # An unidentified item is disclosed only by its observable label, never by
        # template name, material, quality or derived stats.
        for template in R.rules(self.story()).templates:
            self.assertNotIn(template.name, text)
        public = R.public_state(self.svc.store.session(self.s['id']), self.story(), 'player')
        for item in public['items']:
            self.assertIn(item['label'], text)

    def test_identified_item_still_hides_hidden_enchantment_from_model(self):
        candidate = copy.deepcopy(self.s)
        cfg = R.rules(self.story())
        applied, _ = R.apply(candidate, cfg, [{'entry': 'relic'}], 'ev:a')
        candidate['rewards'] = applied
        self.assertEqual(applied['items'][0]['identified'], False)
        self.assertNotIn('潜影', json.dumps(R.public_state(candidate, self.story(), 'player'),
                                           ensure_ascii=False))
        # Identifying it, and even planting a stray `revealed` flag on the instance, still
        # keeps a hidden enchantment out of every player-facing projection: knowing that
        # an instance exists is never enough to learn its hidden layer.
        applied['items'][0]['identified'] = True
        applied['items'][0]['revealed'] = True
        player = R.public_state(candidate, self.story(), 'player')
        self.assertNotIn('潜影', json.dumps(player, ensure_ascii=False))
        self.assertEqual(player['items'][0]['enchantments'], [])
        self.assertIn('潜影', json.dumps(R.public_state(candidate, self.story(), 'author'),
                                         ensure_ascii=False))

    def test_online_failure_does_not_commit_rewards(self):
        before = self.svc.store.session(self.s['id'])
        self.svc.provider.configure({'offline': False})
        async def fail(*args, **kwargs):
            raise ValueError('network down')
        with patch.object(self.svc.provider, 'complete', fail):
            with self.assertRaises(ValueError):
                asyncio.run(self.svc.turn(self.s['id'], Turn(message='整理', action_id='pack')))
        after = self.svc.store.session(self.s['id'])
        self.assertEqual(before, after)
        self.assertEqual(after['rewards']['wallet'], {'coin': 0})
        self.assertEqual(after['rewards']['grants'], [])

    def test_cas_conflict_does_not_pay_out(self):
        self.svc.provider.configure({'offline': False})

        async def concurrent(*args, **kwargs):
            other = self.svc.store.session(self.s['id'])
            other['time'] += 1
            self.svc.store.save_session(other)
            return '正文', {'prompt_tokens': 1, 'completion_tokens': 1}

        with patch.object(self.svc.provider, 'complete', concurrent):
            with self.assertRaisesRegex(ValueError, '其他操作更新'):
                asyncio.run(self.svc.turn(self.s['id'], Turn(message='整理', action_id='pack')))
        after = self.svc.store.session(self.s['id'])
        self.assertEqual(after['rewards']['grants'], [])
        self.assertEqual(after['rewards']['wallet'], {'coin': 0})


class PersistenceTests(RewardCase):

    def test_reward_survives_restart_and_rollback(self):
        self.turn('pack')
        self.reload()
        wallet = copy.deepcopy(self.s['rewards']['wallet'])
        items = copy.deepcopy(self.s['rewards']['items'])
        version = self.s['state_version']
        restarted = Service(Store(self.path), ROOT)
        reloaded = restarted.store.session(self.s['id'])
        self.assertEqual(reloaded['rewards']['wallet'], wallet)
        self.assertEqual(reloaded['rewards']['items'], items)
        self.assertEqual(restarted.runtime.surface(reloaded)['rewards']['wallet'][0]['amount'],
                         sum(wallet.values()))
        archive = reloaded['archives'][-1]['id']
        rolled = restarted.runtime.rollback(reloaded, archive)
        self.assertEqual(rolled['rewards']['wallet']['coin'], 0)
        self.assertEqual(rolled['rewards']['items'], [])
        self.assertEqual(rolled['rewards']['abilities'], [])
        self.assertEqual(rolled['rewards']['ledger'], [])
        self.assertEqual(rolled['state_version'], version + 1)

    def test_ledger_records_before_after_and_is_idempotent(self):
        self.turn('pack')
        self.reload()
        ledger = self.s['rewards']['ledger']
        self.assertTrue(ledger)
        for entry in ledger:
            self.assertIn('before', entry)
            self.assertIn('after', entry)
            self.assertIn('rules_version', entry)
            self.assertIn('branch', entry)
            self.assertTrue(entry['source'].startswith('departure:'))
        grants = [g['id'] for g in self.s['rewards']['grants']]
        self.assertEqual(grants, [x['grant'] for x in ledger])

    def test_surface_protocol_reaches_ui(self):
        self.turn('pack')
        self.reload()
        surface = self.rt.surface(self.s)
        self.assertEqual(surface['inventory'], ['万言机'])
        rewards = surface['rewards']
        self.assertEqual(rewards['rules_version'], 'rewards_v1')
        self.assertTrue(all('amount' in w for w in rewards['wallet']))
        for item in rewards['items']:
            self.assertIn('label', item)
            self.assertNotIn('stats_cache', item)
            self.assertNotIn('origin_result_id', item)
        self.assertNotIn('ledger', rewards)
        # The supply-account block is author-only and must never reach the surface.
        self.assertNotIn('accounts', rewards)
        # Public figures are explicitly labelled as a visible estimate; for an
        # unidentified item that means the label-only note, not the full one.
        self.assertTrue(rewards['items'])
        self.assertEqual(rewards['items'][0]['figures'], 'visible_estimate')
        self.assertTrue(rewards['items'][0]['figures_note'])
        # No author-side payer trace in the player projection.
        self.assertNotIn('account', json.dumps(rewards, ensure_ascii=False))

    def test_offline_narration_mentions_public_reward_only(self):
        self.turn('pack')
        self.reload()
        reply = self.s['archives'][-1]['turns'][0]['reply']
        self.assertIn('铜币 +', reply)
        for template in R.rules(self.story()).templates:
            self.assertNotIn(template.name, reply)
        self.assertNotIn('stats_cache', reply)


if __name__ == '__main__':
    unittest.main()
