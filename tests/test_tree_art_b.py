"""map-art-trees-b.svg（暖带/特殊/奇幻 16 个树种）的结构检查。"""
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

SVG = Path(__file__).resolve().parents[1] / "app" / "static" / "map-art" / "map-art-trees-b.svg"
NS = "{http://www.w3.org/2000/svg}"
SPECIES = ["teak", "bamboo", "kapok", "acacia", "mangrove", "olive", "palm", "baobab", "joshua", "cactus",
           "dragonblood", "cherry", "silverleaf", "gloomwood", "mushroom", "crystal"]
ID_RE = re.compile(r"^tree-(?P<sp>[a-z]+)(?:-v(?P<v>[2-5]))?$")
# 变种数上限：默认 3（v2..v4）；巨菌按用户追加要求放宽到 4（v2..v5）
MAX_VARIANTS = {"mushroom": 4}


class TreeArtBTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = ET.parse(SVG).getroot()
        cls.symbols = list(cls.root.iter(NS + "symbol"))

    def test_parses_and_has_symbols(self):
        self.assertEqual(self.root.tag, NS + "svg")
        self.assertTrue(self.symbols)

    def test_ids_follow_pattern(self):
        for el in self.root.iter():
            sid = el.get("id")
            if sid is None:
                continue
            m = ID_RE.match(sid)
            self.assertIsNotNone(m, f"非法 id：{sid}")
            self.assertIn(m.group("sp"), SPECIES, f"不在 B 组的树种：{sid}")
            if m.group("v") == "5":
                self.assertIn(m.group("sp"), MAX_VARIANTS, f"只有巨菌允许 v5：{sid}")

    def test_each_species_has_main_and_allowed_variants(self):
        ids = {s.get("id") for s in self.symbols}
        self.assertEqual(len(ids), len(self.symbols), "id 重复")
        for sp in SPECIES:
            self.assertIn(f"tree-{sp}", ids)
            extra = [i for i in ids if i.startswith(f"tree-{sp}-v")]
            self.assertTrue(1 <= len(extra) <= MAX_VARIANTS.get(sp, 3), f"{sp} 变种数 {len(extra)}")
            # 变种编号从 v2 连续
            self.assertEqual(sorted(extra), [f"tree-{sp}-v{k}" for k in range(2, 2 + len(extra))])

    def test_viewbox_and_anchor(self):
        for s in self.symbols:
            self.assertEqual(s.get("viewBox"), "0 0 32 40", s.get("id"))
            self.assertEqual(s.get("data-anchor"), "16 38", s.get("id"))

    def test_ground_shadow_present(self):
        for s in self.symbols:
            shadows = [e for e in s.iter(NS + "ellipse")
                       if e.get("fill") == "#3b2f22" and e.get("opacity") == ".18" and e.get("cy") == "38"]
            self.assertTrue(shadows, f"{s.get('id')} 缺地影")


if __name__ == "__main__":
    unittest.main()
