# -*- coding: utf-8 -*-
"""game_fields_v1（价格 / 产地 / 季节 / 保存期 / 谁在卖）的校验与旁挂叠加。

规范见 docs/element-catalog/game-fields-spec.md。临时目录构造旁挂文件，不碰真实源文件；
最后一组用例校验仓库里真实的旁挂文件全部合规且覆盖完整。
"""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools import encyclopedia_build as build
from tools import game_fields as gf

GOOD = {
    'price': {'min': 1, 'max': 3, 'per': '一杯', 'tier': 'penny'},
    'terrains': ['farmland'],
    'seasons': ['all_year'],
    'keeps': 'days',
    'sold_by': ['tavern'],
    'note': '',
}


def game(**changes):
    value = copy.deepcopy(GOOD)
    value.update(changes)
    return value


class TierCase(unittest.TestCase):
    def test_tier_boundaries_follow_the_spec(self):
        self.assertEqual(gf.tier_for(0), 'farthing')
        self.assertEqual(gf.tier_for(1), 'penny')
        self.assertEqual(gf.tier_for(3), 'penny')
        self.assertEqual(gf.tier_for(4), 'groat')
        self.assertEqual(gf.tier_for(11), 'groat')
        self.assertEqual(gf.tier_for(12), 'shilling')
        self.assertEqual(gf.tier_for(239), 'shilling')
        self.assertEqual(gf.tier_for(240), 'pound')


class ValidateCase(unittest.TestCase):
    def test_good_game_yields_matching_tags(self):
        self.assertEqual(gf.validate_game(game(), 'x'),
                         ['price:penny', 'terrain:farmland', 'season:all_year', 'sold_by:tavern'])

    def assertRejected(self, value):
        with self.assertRaises(gf.GameFieldError):
            gf.validate_game(value, 'x')

    def test_tier_must_match_max(self):
        self.assertRejected(game(price={'min': 1, 'max': 12, 'per': '一杯', 'tier': 'penny'}))

    def test_min_cannot_exceed_max(self):
        self.assertRejected(game(price={'min': 5, 'max': 3, 'per': '一杯', 'tier': 'penny'}))

    def test_no_price_tiers_need_null_and_none_seller(self):
        self.assertRejected(game(price={'min': 0, 'max': 0, 'per': '', 'tier': 'not_for_sale'},
                                 sold_by=['none']))
        self.assertRejected(game(price={'min': None, 'max': None, 'per': '', 'tier': 'not_for_sale'},
                                 sold_by=['apothecary']))
        gf.validate_game(game(price={'min': None, 'max': None, 'per': '', 'tier': 'not_for_sale'},
                              sold_by=['none']), 'x')

    def test_vocabulary_and_mixing_rules(self):
        self.assertRejected(game(terrains=['moon']))
        self.assertRejected(game(seasons=['all_year', 'spring']))
        self.assertRejected(game(sold_by=['none', 'tavern']))
        self.assertRejected(game(keeps='forever'))
        self.assertRejected(game(terrains=['farmland', 'farmland']))
        self.assertRejected(game(extra_field=1))


class OverlayCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / gf.SIDECAR_DIR).mkdir(parents=True)
        self.document = {'group': 'g', 'elements': [
            {'id': 'a', 'name': '甲', 'tags': ['kind:dish']},
            {'id': 'b', 'name': '乙'},
        ]}

    def tearDown(self):
        self.tmp.cleanup()

    def sidecar(self, entries):
        (self.root / gf.SIDECAR_DIR / 'g.json').write_text(json.dumps(
            {'schema': gf.SCHEMA, 'group': 'g', 'entries': entries}, ensure_ascii=False),
            encoding='utf-8')

    def test_without_sidecar_document_is_returned_unchanged(self):
        before = copy.deepcopy(self.document)
        self.assertEqual(gf.overlay(self.document, self.root), before)

    def test_overlay_adds_game_and_tags_without_mutating_input(self):
        self.sidecar({'a': game(), 'b': game()})
        before = copy.deepcopy(self.document)
        merged = gf.overlay(self.document, self.root)
        self.assertEqual(self.document, before)
        first, second = merged['elements']
        self.assertEqual(first['game']['schema'], gf.SCHEMA)
        self.assertIn('price:penny', first['tags'])
        self.assertIn('kind:dish', first['tags'])
        # 旧 schema 元素（没有 tags）只写 game，不凭空加 tags。
        self.assertIn('game', second)
        self.assertNotIn('tags', second)

    def test_sidecar_must_cover_exactly_the_group(self):
        self.sidecar({'a': game()})
        with self.assertRaises(gf.GameFieldError):
            gf.overlay(self.document, self.root)
        self.sidecar({'a': game(), 'b': game(), 'ghost': game()})
        with self.assertRaises(gf.GameFieldError):
            gf.overlay(self.document, self.root)


class RepositorySidecarCase(unittest.TestCase):
    """仓库里真实的旁挂文件与自带 game 的分区全部合规。"""

    def test_all_build_groups_pass(self):
        rows = gf.check_all(build.groups_for(*([True] * 9)))
        with_game = {group: (count, total) for group, count, total in rows if count}
        self.assertTrue(with_game, '没有任何分区带 game 字段')
        for group, (count, total) in with_game.items():
            self.assertEqual(count, total, '%s 只有部分元素带 game' % group)


if __name__ == '__main__':
    unittest.main()
