# -*- coding: utf-8 -*-
"""Ground rock sprites: parseable SVG, unique well-named ids, json <-> svg one-to-one, >=3 variants per kind."""
import json
import re
import unittest
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

from app.map_render import extract_symbols

ART = Path(__file__).resolve().parents[1] / "app" / "static" / "map-art"
SVG = ART / "map-art-ground-rocks.svg"
MANIFEST = ART / "ground-rocks.json"
NS = "{http://www.w3.org/2000/svg}"
ID_RE = re.compile(r"^rock-([a-z]+)-([1-9][0-9]*)$")
REQUIRED_KINDS = {"boulder", "cluster", "flat", "mossy", "scree", "snowcap"}


def svg_symbols():
    root = ET.fromstring(SVG.read_text(encoding="utf-8"))
    return root, list(root.iter(NS + "symbol"))


class GroundRocksArtTest(unittest.TestCase):
    def setUp(self):
        self.root, self.symbols = svg_symbols()
        self.ids = [s.get("id") for s in self.symbols]
        self.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_svg_parses_and_has_symbols(self):
        self.assertEqual(self.root.tag, NS + "svg")
        self.assertGreater(len(self.symbols), 0)

    def test_ids_unique_and_named(self):
        dup = [i for i, n in Counter(self.ids).items() if n > 1]
        self.assertEqual(dup, [])
        for sid in self.ids:
            self.assertRegex(sid, ID_RE)

    def test_variants_numbered_from_one(self):
        by_kind = {}
        for sid in self.ids:
            kind, n = ID_RE.match(sid).groups()
            by_kind.setdefault(kind, []).append(int(n))
        for kind, ns in by_kind.items():
            self.assertEqual(sorted(ns), list(range(1, len(ns) + 1)), kind)

    def test_each_kind_has_three_variants(self):
        kinds = Counter(ID_RE.match(sid).group(1) for sid in self.ids)
        self.assertTrue(REQUIRED_KINDS <= set(kinds), REQUIRED_KINDS - set(kinds))
        for kind, n in kinds.items():
            self.assertGreaterEqual(n, 3, kind)

    def test_json_matches_svg(self):
        rocks = self.manifest["rocks"]
        jids = [r["id"] for r in rocks]
        self.assertEqual(len(jids), len(set(jids)))
        self.assertEqual(set(jids), set(self.ids))
        vb = {s.get("id"): [float(v) for v in s.get("viewBox").split()] for s in self.symbols}
        for r in rocks:
            self.assertEqual(r["kind"], ID_RE.match(r["id"]).group(1))
            self.assertEqual(vb[r["id"]], [0.0, 0.0] + [float(v) for v in r["viewBox"]])
            ax, ay = r["anchor"]
            self.assertTrue(0 <= ax <= r["viewBox"][0] and 0 <= ay <= r["viewBox"][1])
            self.assertGreater(r["weight"], 0)
            self.assertTrue(r["scenes"])
            self.assertTrue(set(r["scenes"]) <= set(self.manifest["scenes"]), r["id"])

    def test_symbols_self_contained_and_extractable(self):
        text = SVG.read_text(encoding="utf-8")
        for sym, sid in zip(extract_symbols(text, self.ids), self.ids):
            self.assertNotIn("href", sym, sid)
            inner = re.findall(r'\sid="([^"]+)"', sym)
            self.assertEqual(inner, [sid])


if __name__ == "__main__":
    unittest.main()
