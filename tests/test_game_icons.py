# -*- coding: utf-8 -*-
"""物品属性图示（货币 / 产地 / 季节）与 game_fields_v1 词表一一对应。

图示改动或词表扩充时，两边必须同步：缺图、多图、映射指向不存在的 symbol 都直接失败。
"""
import json
import re
import unittest
from pathlib import Path

from tools import game_fields

ROOT = Path(__file__).resolve().parents[1]
SPRITE = ROOT / 'app/static/item-art/game-icons.svg'
MANIFEST = ROOT / 'app/static/item-art/game-icons.json'


class GameIconsCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.svg = SPRITE.read_text(encoding='utf-8')
        cls.manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
        cls.symbols = re.findall(r'<symbol id="([^"]+)"', cls.svg)

    def test_manifest_keys_match_the_vocabulary(self):
        self.assertEqual(set(self.manifest['price']), set(game_fields.PRICE_TIERS))
        self.assertEqual(set(self.manifest['terrain']), set(game_fields.TERRAINS))
        self.assertEqual(set(self.manifest['season']), set(game_fields.SEASONS))

    def test_every_mapped_symbol_exists_once(self):
        self.assertEqual(len(self.symbols), len(set(self.symbols)), '有重复 symbol id')
        mapped = [item['symbol'] for family in ('price', 'terrain', 'season')
                  for item in self.manifest[family].values()]
        missing = sorted(set(mapped) - set(self.symbols))
        self.assertEqual(missing, [], '映射指向不存在的 symbol')

    def test_no_orphan_symbols(self):
        mapped = {item['symbol'] for family in ('price', 'terrain', 'season')
                  for item in self.manifest[family].values()}
        orphans = sorted(set(self.symbols) - mapped)
        self.assertEqual(orphans, [], 'sprite 里有未登记的 symbol')

    def test_symbols_use_the_shared_prefix_and_viewbox(self):
        for match in re.finditer(r'<symbol id="([^"]+)" viewBox="([^"]+)"', self.svg):
            self.assertTrue(match.group(1).startswith('gi-'), match.group(1))
            self.assertEqual(match.group(2), '0 0 24 24', match.group(1))

    def test_every_entry_has_a_chinese_label(self):
        for family in ('price', 'terrain', 'season'):
            for key, item in self.manifest[family].items():
                self.assertTrue(item.get('label'), '%s:%s 缺 label' % (family, key))

    def test_sprite_has_no_external_references(self):
        """静态资源必须自包含：不引用外部图片、字体或脚本。"""
        self.assertNotRegex(self.svg, r'(?i)<script|<image|href="https?:|@import')


if __name__ == '__main__':
    unittest.main()
