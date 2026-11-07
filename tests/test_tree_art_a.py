"""Group-A tree sprite (app/static/map-art/map-art-trees-a.svg): structure and id conventions."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPRITE = ROOT / "app" / "static" / "map-art" / "map-art-trees-a.svg"
SVG_NS = "{http://www.w3.org/2000/svg}"
SPECIES = ("pine", "spruce", "larch", "fir", "cedar", "cypress", "yew", "redwood",
           "oak", "beech", "birch", "maple", "chestnut", "ash", "elm", "willow")
ID_RE = re.compile(r"tree-(%s)(-v[2-4])?" % "|".join(SPECIES))


def _symbols():
    root = ET.fromstring(SPRITE.read_text(encoding="utf-8"))
    return root.findall(f".//{SVG_NS}symbol")


def test_sprite_parses_and_has_symbols():
    assert _symbols()


def test_every_id_follows_the_pattern():
    root = ET.fromstring(SPRITE.read_text(encoding="utf-8"))
    ids = [el.get("id") for el in root.iter() if el.get("id") is not None]
    bad = [i for i in ids if not ID_RE.fullmatch(i)]
    assert not bad, bad
    assert len(ids) == len(set(ids)), "duplicate ids"
    # every id must be on a <symbol>, nothing else may carry an id
    assert len(ids) == len(_symbols())


def test_each_species_has_main_and_1_to_3_variants():
    ids = {s.get("id") for s in _symbols()}
    for sp in SPECIES:
        assert f"tree-{sp}" in ids, sp
        variants = [i for i in ids if re.fullmatch(rf"tree-{sp}-v[2-4]", i)]
        assert 1 <= len(variants) <= 3, (sp, variants)


MAX_FILE_BYTES = 250_000
MAX_SYMBOL_BYTES = 8_000


def test_size_limits():
    text = SPRITE.read_text(encoding="utf-8")
    assert len(text.encode("utf-8")) <= MAX_FILE_BYTES
    big = [(m.group(1), len(m.group(0).encode("utf-8")))
           for m in re.finditer(r'<symbol id="([^"]+)".*?</symbol>', text, re.S)
           if len(m.group(0).encode("utf-8")) > MAX_SYMBOL_BYTES]
    assert not big, big


def test_viewbox_and_anchor():
    for s in _symbols():
        assert s.get("viewBox") == "0 0 32 40", s.get("id")
        assert s.get("data-anchor") == "16 38", s.get("id")
