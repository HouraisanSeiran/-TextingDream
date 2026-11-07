# -*- coding: utf-8 -*-
"""Forest-floor grass sprite: parseable SVG, well-named unique ids, json <-> svg one-to-one, >=3 variants per kind."""
import json
import re
import unittest
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ART = Path(__file__).resolve().parents[1] / "app" / "static" / "map-art"
SVG = ART / "map-art-ground-grass.svg"
JSON = ART / "ground-grass.json"
NS = "{http://www.w3.org/2000/svg}"
ID_RE = re.compile(r"grass-([a-z]+)-([1-9]\d*)")
REQUIRED_KINDS = {"tuft", "tall", "fern", "shrub", "flower", "dry", "reed"}


def svg_symbols():
    root = ET.parse(SVG).getroot()
    return list(root.iter(NS + "symbol"))


def meta():
    return json.loads(JSON.read_text(encoding="utf-8"))


class GroundGrassArtTest(unittest.TestCase):
    def test_svg_parses_and_contains_only_symbols(self):
        syms = svg_symbols()
        self.assertGreater(len(syms), 0)
        root = ET.parse(SVG).getroot()
        for el in root.iter():
            self.assertNotIn(el.tag, (NS + "use",), "sprite should hold only <symbol> definitions")
        for s in syms:
            self.assertEqual(s.get("viewBox"), "0 0 14 10", s.get("id"))

    def test_ids_unique_and_named(self):
        ids = [s.get("id") for s in svg_symbols()]
        self.assertEqual(len(ids), len(set(ids)), [i for i, c in Counter(ids).items() if c > 1])
        for i in ids:
            self.assertRegex(i, r"^grass-[a-z]+-[1-9]\d*$")
        by_kind = {}
        for i in ids:
            k, v = ID_RE.fullmatch(i).groups()
            by_kind.setdefault(k, []).append(int(v))
        for k, vs in by_kind.items():   # variants numbered 1..n without gaps
            self.assertEqual(sorted(vs), list(range(1, len(vs) + 1)), k)

    def test_json_matches_svg(self):
        m = meta()
        svg_ids = {s.get("id") for s in svg_symbols()}
        json_ids = [s["id"] for s in m["symbols"]]
        self.assertEqual(len(json_ids), len(set(json_ids)))
        self.assertEqual(set(json_ids), svg_ids)
        kind_ids = {i for info in m["kinds"].values() for i in info["variants"]}
        self.assertEqual(kind_ids, svg_ids)
        scenes = set(m["scenes"])
        for s in m["symbols"]:
            self.assertEqual(s["viewBox"], [14, 10], s["id"])
            self.assertEqual(s["anchor"], [7.0, 9.0], s["id"])
            self.assertEqual(s["kind"], ID_RE.fullmatch(s["id"]).group(1))
            self.assertTrue(s["scenes"] and set(s["scenes"]) <= scenes, s["id"])
            self.assertGreater(s["weight"], 0)

    def test_scene_weights_are_distributions(self):
        m = meta()
        for scene in m["scenes"]:
            total = sum(s["scene_weights"].get(scene, 0) for s in m["symbols"])
            self.assertAlmostEqual(total, 1.0, places=2, msg=scene)

    def test_water_flag_and_sparse_mushrooms(self):
        m = meta()
        for s in m["symbols"]:
            self.assertIsInstance(s.get("requires_water_adjacent"), bool, s["id"])
        wet = {s["id"] for s in m["symbols"] if s["requires_water_adjacent"]}
        self.assertEqual(wet, {"grass-reed-1", "grass-reed-3", "grass-reed-4"})
        for scene in m["scenes"]:
            share = sum(s["scene_weights"].get(scene, 0) for s in m["symbols"] if s["kind"] == "mushroom")
            self.assertLessEqual(share, 0.0601, scene)

    def test_each_kind_has_three_or_more_variants(self):
        counts = Counter(ID_RE.fullmatch(s.get("id")).group(1) for s in svg_symbols())
        self.assertTrue(REQUIRED_KINDS <= set(counts), REQUIRED_KINDS - set(counts))
        for k, c in counts.items():
            self.assertGreaterEqual(c, 3, k)


if __name__ == "__main__":
    unittest.main()
