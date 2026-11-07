# -*- coding: utf-8 -*-
"""交易结算：买、卖、以物易物、讨价还价；钱包 / 货物袋 / 商人账户的变化、回滚、无配置零变化。"""
import copy
import unittest

from app import economy as ec
from app import free_actions, rewards, trade, attributes

AXES = {k: 50 for k in attributes.AXES}


def make_story(tech='renaissance', with_checks=True, **eco):
    cfg = {
        'currency': 'pence',
        'market_day': {'every_days': 7, 'offset': 0},
        'polities': {'home': {'customs': 20}, 'far': {'customs': 0}},
        'places': {'market': {'polity': 'home', 'produces': ['wool'], 'lacks': ['salt']}},
        'merchants': [{
            'id': 'smith', 'name': '老铁匠', 'location': 'market', 'npc': 'smith', 'account': 'purse',
            'haggle_difficulty': 0.25,
            'sells': [
                {'id': 'grain', 'name': '干麦', 'base': 12, 'unit': '袋', 'resource': 'grain',
                 'season_class': 'grain', 'stock': 5},
                {'id': 'lamp', 'name': '黄铜灯', 'base': 100, 'item': 'lamp'},
                {'id': 'ale', 'name': '麦酒', 'base': 2, 'unit': '杯', 'always': True},
                {'id': 'spice', 'name': '香料', 'base': 40, 'unit': '包', 'origin': 'imported',
                 'origin_polity': 'far'},
            ],
            'buys': [
                {'id': 'wool', 'name': '羊毛', 'base': 20, 'unit': '捆'},
                {'id': 'grain', 'name': '干麦', 'base': 12, 'unit': '袋'},
            ],
        }],
    }
    cfg.update(eco)
    story = {
        'id': 't', 'locations': [{'id': 'market', 'name': '集市'}],
        'items': [{'id': 'lamp', 'name': '黄铜灯'}],
        'worldview': {'setting': {'tech': tech}},
        'mechanics': {
            'economy': cfg,
            'rewards': {'currencies': [{'id': 'pence', 'name': '便士', 'unit': '便士'}],
                        'accounts': [{'id': 'purse', 'name': '钱袋', 'currency': 'pence',
                                      'initial': 300}]},
        },
    }
    if with_checks:
        story['mechanics']['checks'] = {'version': 2, 'tier_mode': 'margin_four'}
    return story


CHARS = {'characters': [{'id': 'player', 'name': '我', 'attributes': dict(AXES)},
                        {'id': 'smith', 'name': '老铁匠', 'attributes': dict(AXES)}]}


def make_session(story, wallet=500, day=1, seed='s1'):
    s = {'id': 's', 'revision': 'r', 'seed': seed, 'hero': 'player', 'location': 'market',
         'time': (day - 1) * 24 + 8, 'inventory': [], 'flags': {}, 'mode': 'player',
         'state_version': 1, 'active': None,
         'characters': {'player': {'location': 'market'}, 'smith': {'location': 'market'}}}
    rewards.ensure(s, story)
    s['rewards']['wallet']['pence'] = wallet
    return s


def run(s, story, action_id):
    work = copy.deepcopy(s)
    result = trade.settle(work, story, CHARS, action_id)
    return result, work


class RegimeTests(unittest.TestCase):
    def test_renaissance_defaults_to_early_capitalism(self):
        self.assertEqual(ec.regime_of(make_story('renaissance', eco_none=None) if False else
                                      {'worldview': {'setting': {'tech': 'renaissance'}}}),
                         'early_capitalism')
        self.assertEqual(ec.regime_of({'worldview': {'setting': {'tech': 'medieval'}}}), 'feudal')
        self.assertEqual(ec.regime_of({'worldview': {'setting': {'tech': 'steam'}}}), 'market')

    def test_quote_order_all_regimes(self):
        for regime in ec.REGIMES:
            for base in (1, 2, 12, 100, 240):
                for imported in (False, True):
                    q = ec.quote(base, regime, imported=imported)
                    self.assertGreaterEqual(q['ask'], q['floor'])
                    self.assertGreater(q['floor'], q['bid'])

    def test_early_capitalism_between_the_other_two(self):
        f, e, m = (ec.quote(100, r) for r in ('feudal', 'early_capitalism', 'market'))
        self.assertGreater(f['ask'], e['ask'])
        self.assertGreater(e['ask'], m['ask'])
        self.assertLess(f['bid'], e['bid'])
        self.assertLess(e['bid'], m['bid'])


class ValidateTests(unittest.TestCase):
    def test_valid_config(self):
        ec.validate(make_story(), CHARS)

    def test_rejects_bad_references(self):
        def broken(mutate):
            story = make_story()
            mutate(story['mechanics']['economy'])
            with self.assertRaises(ec.EconomyError):
                ec.validate(story, CHARS)
        broken(lambda c: c['merchants'][0].update(location='nowhere'))
        broken(lambda c: c['merchants'][0].update(account='ghost'))
        broken(lambda c: c['merchants'][0].update(npc='ghost'))
        broken(lambda c: c.update(currency='gold'))
        broken(lambda c: c['merchants'][0]['sells'][1].update(item='nope'))
        broken(lambda c: c['merchants'][0]['sells'][0].update(season_class='weather'))
        broken(lambda c: c['merchants'][0]['sells'][3].update(origin_polity='mars'))
        broken(lambda c: c['merchants'].append(copy.deepcopy(c['merchants'][0])))
        broken(lambda c: c['merchants'][0].update(surprise=1))

    def test_merchants_need_rewards(self):
        story = make_story()
        del story['mechanics']['rewards']
        with self.assertRaises(ec.EconomyError):
            ec.validate(story, CHARS)


class PriceTests(unittest.TestCase):
    def setUp(self):
        self.story = make_story('medieval')
        self.cfg = ec.model(self.story)
        self.m = self.cfg.merchants[0]

    def price(self, good_id, s, rows='sells'):
        g = next(x for x in getattr(self.m, rows) if x.id == good_id)
        return ec.price_for(self.story, s, self.m, g, self.cfg, 'feudal')

    def test_local_product_cheaper_and_lack_dearer(self):
        s = make_session(self.story)
        wool = ec.price_for(self.story, s, self.m, self.m.buys[0], self.cfg, 'feudal')
        self.assertEqual(wool['bid'], 20 * 85 // 100 * 50 // 100)
        self.m.buys[0]  # 出产使收购价也按本地价算
        salt = ec.Good(id='salt', name='盐', base=100)
        self.assertEqual(ec.price_for(self.story, s, self.m, salt, self.cfg, 'feudal')['ask'],
                         100 * 125 // 100 * 130 // 100)

    def test_customs_on_foreign_goods(self):
        s = make_session(self.story)
        row = self.price('spice', s)
        self.assertIn('关税 +20%', row['notes'])
        self.assertEqual(row['ask'], (40 * 120 // 100) * 200 // 100 * 130 // 100)

    def test_season_moves_grain(self):
        autumn = make_session(self.story, day=200)   # 年内第 ~280 天：秋
        spring = make_session(self.story, day=30)    # 年内第 ~108 天：春
        self.assertEqual(ec.season_of(self.story, autumn), 'autumn')
        self.assertEqual(ec.season_of(self.story, spring), 'spring')
        self.assertLess(self.price('grain', autumn)['ask'], self.price('grain', spring)['ask'])

    def test_market_day_cycle(self):
        for day, expected in ((1, True), (2, False), (8, True)):
            self.assertEqual(ec.is_market_day(self.cfg, make_session(self.story, day=day)), expected)
        self.assertEqual(ec.days_to_market(self.cfg, make_session(self.story, day=2)), 6)


class SettleTests(unittest.TestCase):
    def setUp(self):
        self.story = make_story()
        self.s = make_session(self.story)

    def test_buy_moves_money_and_bag(self):
        row = ec.price_for(self.story, self.s, ec.model(self.story).merchants[0],
                           ec.model(self.story).merchants[0].sells[0], None, 'early_capitalism')
        result, work = run(self.s, self.story, 'trade:buy:smith:grain:2')
        self.assertEqual(work['rewards']['wallet']['pence'], 500 - 2 * row['ask'])
        self.assertEqual(work['rewards']['accounts']['purse'], 300 + 2 * row['ask'])
        self.assertEqual(work['trade']['bag'], {'grain': 2})
        self.assertEqual(result['local_result']['trade']['total'], 2 * row['ask'])
        # 候选副本之外的原状态没动
        self.assertEqual(self.s['rewards']['wallet']['pence'], 500)
        self.assertNotIn('trade', self.s)

    def test_buy_unique_item_goes_to_inventory(self):
        _, work = run(self.s, self.story, 'trade:buy:smith:lamp')
        self.assertEqual(work['inventory'], ['lamp'])
        with self.assertRaises(ValueError):
            trade.settle(work, self.story, CHARS, 'trade:buy:smith:lamp')

    def test_not_enough_money_and_stock(self):
        poor = make_session(self.story, wallet=3)
        with self.assertRaises(ValueError):
            run(poor, self.story, 'trade:buy:smith:grain')
        self.assertEqual(poor['rewards']['wallet']['pence'], 3)
        with self.assertRaises(ValueError):
            run(self.s, self.story, 'trade:buy:smith:grain:6')   # 现货只有 5

    def test_stock_is_daily(self):
        _, work = run(self.s, self.story, 'trade:buy:smith:grain:5')
        with self.assertRaises(ValueError):
            trade.settle(work, self.story, CHARS, 'trade:buy:smith:grain')
        work['time'] += 24 * 7           # 下个集市日，现货恢复
        trade.settle(work, self.story, CHARS, 'trade:buy:smith:grain')

    def test_sell_pays_from_merchant_account(self):
        self.s['trade'] = dict(trade.blank(), bag={'wool': 3})
        result, work = run(self.s, self.story, 'trade:sell:smith:wool:2')
        paid = result['local_result']['trade']['total']
        self.assertGreater(paid, 0)
        self.assertEqual(work['rewards']['accounts']['purse'], 300 - paid)
        self.assertEqual(work['rewards']['wallet']['pence'], 500 + paid)
        self.assertEqual(work['trade']['bag'], {'wool': 1})

    def test_sell_refused_when_merchant_broke(self):
        self.s['trade'] = dict(trade.blank(), bag={'wool': 3})
        self.s['rewards']['accounts']['purse'] = 1
        with self.assertRaises(ValueError):
            run(self.s, self.story, 'trade:sell:smith:wool:2')
        self.assertEqual(self.s['rewards']['accounts']['purse'], 1)

    def test_cannot_sell_what_you_do_not_have(self):
        with self.assertRaises(ValueError):
            run(self.s, self.story, 'trade:sell:smith:wool')

    def test_barter_swaps_goods_without_money(self):
        self.s['trade'] = dict(trade.blank(), bag={'wool': 9})
        result, work = run(self.s, self.story, 'trade:barter:smith:grain:wool')
        t = result['local_result']['trade']
        self.assertEqual(work['rewards']['wallet']['pence'], 500)
        self.assertEqual(work['rewards']['accounts']['purse'], 300)
        self.assertEqual(work['trade']['bag']['grain'], 1)
        self.assertEqual(work['trade']['bag']['wool'], 9 - t['give']['qty'])

    def test_barter_off_for_market_regime(self):
        story = make_story('steam')
        s = make_session(story)
        s['trade'] = dict(trade.blank(), bag={'wool': 9})
        with self.assertRaises(ValueError):
            run(s, story, 'trade:barter:smith:grain:wool')

    def test_feudal_closed_off_market_day_except_always(self):
        story = make_story('medieval')
        off = make_session(story, day=3)
        with self.assertRaises(ValueError):
            run(off, story, 'trade:buy:smith:grain')
        _, work = run(off, story, 'trade:buy:smith:ale')
        self.assertEqual(work['trade']['bag'], {'ale': 1})
        _, work = run(make_session(story, day=1), story, 'trade:buy:smith:grain')
        self.assertEqual(work['trade']['bag'], {'grain': 1})

    def test_merchant_must_be_here(self):
        self.s['location'] = 'elsewhere'
        with self.assertRaises(ValueError):
            run(self.s, self.story, 'trade:buy:smith:ale')

    def test_bad_ids(self):
        for bad in ('trade:buy', 'trade:swap:smith:ale', 'trade:buy:smith:ghost',
                    'trade:buy:ghost:ale', 'trade:buy:smith:ale:0', 'trade:buy:smith:ale:99',
                    'trade:haggle:smith:grain:2'):
            with self.assertRaises(ValueError, msg=bad):
                run(self.s, self.story, bad)


class HaggleTests(unittest.TestCase):
    def setUp(self):
        self.story = make_story()
        self.row = None

    def settle_with(self, seed, action='trade:haggle:smith:lamp'):
        s = make_session(self.story, seed=seed)
        return run(s, self.story, action)

    def by_tier(self):
        found = {}
        for i in range(400):
            result, work = self.settle_with('seed%d' % i)
            found.setdefault(result['local_result']['trade']['tier'], (i, result, work))
        return found

    def test_prices_follow_tier(self):
        found = self.by_tier()
        self.assertTrue({'critical', 'success', 'failure'} <= set(found), set(found))
        s = make_session(self.story)
        m = ec.model(self.story).merchants[0]
        row = ec.price_for(self.story, s, m, m.sells[1], None, 'early_capitalism')
        ask, floor = row['ask'], row['floor']
        self.assertLess(floor, ask)
        crit = found['critical'][1]['local_result']['trade']
        self.assertEqual(crit['unit_price'], floor)
        succ = found['success'][1]['local_result']['trade']
        self.assertEqual(succ['unit_price'], ask - (ask - floor) // 2)
        self.assertTrue(floor <= succ['unit_price'] <= ask)
        fail = found['failure'][1]['local_result']['trade']
        self.assertFalse(fail['deal'])
        self.assertEqual(fail['unit_price'], ask)

    def test_deal_moves_money_failure_does_not(self):
        found = self.by_tier()
        _, res, work = found['critical']
        paid = res['local_result']['trade']['unit_price']
        self.assertEqual(work['rewards']['wallet']['pence'], 500 - paid)
        self.assertEqual(work['inventory'], ['lamp'])
        _, res, work = found['failure']
        self.assertEqual(work['rewards']['wallet']['pence'], 500)
        self.assertEqual(work['inventory'], [])
        # 失败后今天不再谈价，但还能按开价买
        with self.assertRaises(ValueError):
            trade.settle(work, self.story, CHARS, 'trade:haggle:smith:lamp')
        trade.settle(work, self.story, CHARS, 'trade:buy:smith:lamp')

    def test_disaster_refuses_sale_today(self):
        # 难度拉到最高（DC 21）：骰面不高于 11 就是大失败（差值 ≤ -10），一定能扫到。
        story = make_story()
        story['mechanics']['economy']['merchants'][0]['haggle_difficulty'] = 1.0
        work = None
        for i in range(60):
            result, w = run(make_session(story, seed='d%d' % i), story, 'trade:haggle:smith:lamp')
            if result['local_result']['trade']['tier'] == 'disaster':
                work = w
                break
        self.assertIsNotNone(work, '难度 1.0 下 60 个种子内应出现大失败')
        self.assertFalse(work['inventory'])
        with self.assertRaises(ValueError):
            trade.settle(work, story, CHARS, 'trade:buy:smith:lamp')

    def test_same_seed_same_result(self):
        a, _ = self.settle_with('fixed')
        b, _ = self.settle_with('fixed')
        self.assertEqual(a['local_result']['trade'], b['local_result']['trade'])

    def test_needs_checks(self):
        story = make_story(with_checks=False)
        with self.assertRaises(ValueError):
            run(make_session(story), story, 'trade:haggle:smith:lamp')


class SurfaceAndPromptTests(unittest.TestCase):
    def test_no_config_changes_nothing(self):
        story = {'id': 'x', 'worldview': {'setting': {'tech': 'steam'}}, 'mechanics': {}}
        self.assertFalse(trade.declared(story))
        self.assertIsNone(trade.surface({'location': 'market', 'time': 8}, story, CHARS))
        self.assertIsNone(free_actions.resolve_action({}, story, None, 'trade:buy:smith:ale'))
        block = ec.prompt_block(story, {'location': 'market', 'time': 8})
        self.assertNotIn('local_market', block)
        self.assertEqual(block, ec.prompt_block(story))
        self.assertIsNone(ec.prompt_block({'mechanics': {}}, {'time': 8}))

    def test_surface_hides_floor_and_balance(self):
        story = make_story()
        s = make_session(story)
        card = trade.surface(s, story, CHARS)
        text = repr(card)
        self.assertNotIn('floor', text)
        self.assertNotIn('purse', text)
        self.assertNotIn('300', text)
        lines = {g['good']: g for g in card['merchants'][0]['sells']}
        self.assertEqual(lines['grain']['buy_action'], 'trade:buy:smith:grain')
        self.assertEqual(lines['grain']['haggle_action'], 'trade:haggle:smith:grain')
        self.assertNotIn('trade', s)               # 投影不写 session

    def test_prompt_block_has_local_market_and_oral_agreement_rule(self):
        story = make_story()
        s = make_session(story)
        block = ec.prompt_block(story, s)
        self.assertIn('local_market', block)
        self.assertTrue(any('口头约定' in x for x in block['trading']))
        self.assertEqual(block['regime'], '早期资本主义')

    def test_confirm_token_binds_state(self):
        story = make_story()
        s = make_session(story)
        action = free_actions.resolve_action(s, story, None, 'trade:buy:smith:ale', characters=CHARS)
        token = free_actions.confirm_token(s, None, action, story)
        s2 = dict(s, state_version=2)
        self.assertNotEqual(token, free_actions.confirm_token(s2, None, action, story))
        item = free_actions.describe(s, story, None, 'trade:buy:smith:ale', characters=CHARS)
        self.assertEqual(item['confirm'], token)
        self.assertEqual(item['trade']['total'], item['trade']['unit_price'])



class ExampleFileTests(unittest.TestCase):
    """docs/examples 里的示例片段必须能通过校验，并真能做一笔买卖。"""

    def _story(self):
        import json
        from pathlib import Path
        path = Path(__file__).resolve().parent.parent / 'docs' / 'examples' / 'economy-demo.story-fragment.json'
        frag = json.loads(path.read_text(encoding='utf-8'))
        need = frag['_需要的地点与物品']
        return {'id': 'demo', 'locations': need['locations'], 'items': need['items'],
                'worldview': {'setting': {'tech': 'medieval'}},
                'mechanics': frag['mechanics']}

    def test_example_validates(self):
        story = self._story()
        ec.validate(story, CHARS)
        self.assertTrue(trade.declared(story))

    def test_example_can_buy(self):
        story = self._story()
        s = make_session(story, wallet=200)
        s['location'] = 'market'
        s['characters'] = {'player': {'location': 'market'}}
        result, work = run(s, story, 'trade:buy:smith:ale:2')
        self.assertLess(work['rewards']['wallet']['pence'], 200)


if __name__ == '__main__':
    unittest.main()
