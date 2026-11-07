# -*- coding: utf-8 -*-
"""元素图标对照表（app/static/item-art/element-icons.json）与 sprite、元素库三方一致。"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / 'app/static/item-art'
MANIFEST = DIR / 'element-icons.json'
NEW_SPRITE = DIR / 'element-icons.svg'


def symbols(path):
    return re.findall(r'<symbol id="([^"]+)"', path.read_text(encoding='utf-8'))


def element_ids(group):
    # 分区名可能用下划线（如 professions_fantasy），文件名用连字符（professions-fantasy.json）。
    for base in ('docs/element-catalog', 'docs/human-encyclopedia', 'docs/playable-demo'):
        for stem in dict.fromkeys((group, group.replace('_', '-'))):
            path = ROOT / base / (stem + '.json')
            if path.is_file():
                document = json.loads(path.read_text(encoding='utf-8-sig'))
                if document.get('group', stem) == group:
                    return {element['id'] for element in document.get('elements') or []}
    return None


class ElementIconsCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
        cls.sprite_symbols = {key: set(symbols((DIR / rel).resolve()))
                              for key, rel in cls.manifest['sprites'].items()}

    def test_every_entry_points_to_an_existing_symbol(self):
        for key, item in self.manifest['entries'].items():
            self.assertIn(item['sprite'], self.sprite_symbols, key)
            self.assertIn(item['symbol'], self.sprite_symbols[item['sprite']], key)

    def test_every_entry_points_to_an_existing_element(self):
        for key in self.manifest['entries']:
            group, element_id = key.split('/', 1)
            ids = element_ids(group)
            self.assertIsNotNone(ids, '分区不存在：%s' % group)
            self.assertIn(element_id, ids, key)

    def test_reuse_flag_matches_the_sprite(self):
        for key, item in self.manifest['entries'].items():
            self.assertEqual(bool(item.get('reuse')), item['sprite'] != 'element', key)

    def test_new_symbols_are_all_used_once_with_prefix_and_viewbox(self):
        names = symbols(NEW_SPRITE)
        self.assertEqual(len(names), len(set(names)), '有重复 symbol id')
        used = [item['symbol'] for item in self.manifest['entries'].values() if item['sprite'] == 'element']
        self.assertEqual(sorted(set(names)), sorted(set(used)), '新画图标与对照表不一致')
        text = NEW_SPRITE.read_text(encoding='utf-8')
        for match in re.finditer(r'<symbol id="([^"]+)" viewBox="([^"]+)"', text):
            self.assertTrue(match.group(1).startswith('ei-'), match.group(1))
            self.assertEqual(match.group(2), '0 0 24 24', match.group(1))

    def test_sprite_has_no_external_references(self):
        self.assertNotRegex(NEW_SPRITE.read_text(encoding='utf-8'),
                            r'(?i)<script|<image|href="https?:|@import')


if __name__ == '__main__':
    unittest.main()
