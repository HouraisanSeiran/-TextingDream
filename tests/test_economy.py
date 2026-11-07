# -*- coding: utf-8 -*-
"""对话用轻量经济规则：经济形态推断、配置校验、买卖价边界、提示词块。"""
import unittest

from app import economy as ec


def story(tech=None, cfg=None):
    s = {'worldview': {'setting': {'tech': tech}} if tech else {}, 'mechanics': {}}
    if cfg is not None:
        s['mechanics']['economy'] = cfg
    return s


class RegimeTests(unittest.TestCase):
    def test_default_follows_tech_tier(self):
        self.assertEqual(ec.regime_of(story('medieval')), 'feudal')
        self.assertEqual(ec.regime_of(story('classical')), 'feudal')
        self.assertEqual(ec.regime_of(story('renaissance')), 'early_capitalism')
        self.assertEqual(ec.regime_of(story('steam')), 'market')
        self.assertEqual(ec.regime_of(story('early_modern')), 'market')

    def test_explicit_regime_wins(self):
        self.assertEqual(ec.regime_of(story('steam', {'regime': 'feudal'})), 'feudal')

    def test_no_setting_no_config_means_none(self):
        self.assertIsNone(ec.regime_of(story()))
        self.assertIsNone(ec.prompt_block(story()))

    def test_validate(self):
        ec.validate(story())
        ec.validate(story(cfg={'regime': 'market', 'note': '港口城市'}))
        for bad in ({'regime': 'socialist'}, {'stock': 1}, {'note': 'x' * 601}, 'feudal'):
            with self.assertRaises(ec.EconomyError, msg=bad):
                ec.validate(story(cfg=bad))


class QuoteTests(unittest.TestCase):
    def test_buy_high_sell_low(self):
        for regime in ec.REGIMES:
            for base in (1, 2, 12, 240):
                q = ec.quote(base, regime)
                self.assertGreaterEqual(q['ask'], q['floor'], (regime, base))
                self.assertGreater(q['floor'], q['bid'], (regime, base))

    def test_feudal_values(self):
        self.assertEqual(ec.quote(12, 'feudal'), {'ask': 15, 'floor': 12, 'bid': 6})
        self.assertEqual(ec.quote(12, 'feudal', imported=True)['ask'], 31)

    def test_market_is_tighter(self):
        f, m = ec.quote(100, 'feudal'), ec.quote(100, 'market')
        self.assertLess(m['ask'] - m['bid'], f['ask'] - f['bid'])

    def test_zero_and_bad_input(self):
        self.assertEqual(ec.quote(0, 'feudal'), {'ask': 0, 'floor': 0, 'bid': 0})
        for bad in (-1, 1.5, True):
            with self.assertRaises(ec.EconomyError):
                ec.quote(bad, 'feudal')
        with self.assertRaises(ec.EconomyError):
            ec.quote(10, 'barter')


class PromptTests(unittest.TestCase):
    def test_feudal_block(self):
        block = ec.prompt_block(story('medieval', {'note': '盐由领主专卖'}))
        self.assertEqual(block['regime'], '封建经济')
        self.assertIn('以物易物', ''.join(block['traits']))
        self.assertIn('没有纸币', block['currency'])
        self.assertEqual(block['note'], '盐由领主专卖')
        self.assertTrue(any('引擎结算' in line for line in block['trading']))

    def test_market_block(self):
        block = ec.prompt_block(story('early_modern'))
        self.assertIn('资本主义', block['regime'])
        self.assertIn('纸币', block['currency'])


if __name__ == '__main__':
    unittest.main()
