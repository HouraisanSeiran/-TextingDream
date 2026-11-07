import numpy as np
import pytest

from app.map_render import (ART_DIR, base_colors, compose_html, compose_icon_sheet, display_grid, hex_rgb, load_manifest,
                            load_styles, render_map, resolve_town_symbol, scale_bar, sprite_ids, style_sprites_svg,
                            terrain_candidates, validate_towns)
from app.terrain_source import CLOSED_BELOW_SEA, LAND, OCEAN, UNKNOWN

STYLES = load_styles()
MANIFEST = load_manifest()
ALL_STYLES = ["simple", "medieval", "eastern"]
TERRAIN_IDS = {"terrain-mountain", "terrain-snowpeak", "terrain-hill", "terrain-marsh",
               "east-ink-peak", "east-ink-snowpeak", "east-ink-hill", "east-ink-marsh"}
RESOURCE_KINDS = list(MANIFEST["resources"]["kinds"]) + [k for k in MANIFEST["resources"]["trade_kinds"] if k != "note"]
REQUIRED_IDS = ({"town-hamlet", "town-town", "town-city", "town-capital"}
                | {"res-%s" % k for k in RESOURCE_KINDS}
                | {"mark-bridge", "mark-ford", "mark-pass", "mark-port"})


def _fixture(n=256, spacing=30.0):
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    elev = 1600.0 * np.exp(-((xx - 70) ** 2 + (yy - 70) ** 2) / (2 * 22.0 ** 2))
    elev += 900.0 * np.exp(-((xx - 140) ** 2 + (yy - 60) ** 2) / (2 * 14.0 ** 2))
    elev += 40.0 * np.sin(xx / 5.0) * np.cos(yy / 7.0) + 20.0
    sea = xx + 0.4 * yy > 190
    elev[sea] = -40.0 - 6.0 * (xx[sea] + 0.4 * yy[sea] - 190)
    status = np.full((n, n), LAND, dtype=np.uint8)
    status[sea] = OCEAN
    # inland depression: below sea level but NOT ocean
    dep = (xx - 40) ** 2 + (yy - 190) ** 2 < 12 ** 2
    elev[dep] = -8.0
    status[dep] = CLOSED_BELOW_SEA
    unk = (xx < 12) & (yy < 12)
    status[unk] = UNKNOWN
    elev[unk] = np.nan
    return dict(elevation_m=elev.astype(np.float32), status=status, spacing_m=spacing,
                first_sample_xz_m=(-3840.0, -3840.0), shape_zx=(n, n))


def test_render_deterministic_bytes():
    crop = _fixture()
    seen = []
    for name in ALL_STYLES:
        a = render_map(crop, name, 128, styles=STYLES)
        b = render_map(crop, name, 128, styles=STYLES)
        assert a.rgb.tobytes() == b.rgb.tobytes(), name
        assert a.symbols == b.symbols and a.decorations == b.decorations
        seen.append(a.rgb.tobytes())
    assert len(set(seen)) == 3  # three distinct looks


@pytest.mark.parametrize("style_name", ALL_STYLES)
def test_status_colours_come_from_their_ramp(style_name):
    style = STYLES["styles"][style_name]
    elev = np.array([[500.0, -1500.0, -8.0, np.nan, -2.0]])
    status = np.array([[LAND, OCEAN, CLOSED_BELOW_SEA, UNKNOWN, LAND]], dtype=np.uint8)
    rgb = base_colors(elev, status, style)
    land = [tuple(hex_rgb(b["color"])) for b in style["land_bands"]]
    ocean = [tuple(hex_rgb(b["color"])) for b in style["ocean_bands"]]
    assert tuple(rgb[0, 0]) in land
    assert tuple(rgb[0, 1]) in ocean
    assert tuple(rgb[0, 2]) == tuple(hex_rgb(style["closed_below_sea"]["color"]))
    assert tuple(rgb[0, 2]) not in ocean  # 内陆洼地不是海色
    assert tuple(rgb[0, 3]) == tuple(hex_rgb(style["unknown"]["color"]))
    # status decides, not height<0: a negative-height LAND sample still gets a land colour
    assert tuple(rgb[0, 4]) == land[0]
    assert land[0] not in ocean


def test_display_grid_point_samples_status_exactly():
    crop = _fixture()
    grid = display_grid(crop, 128)
    assert grid["factor"] == 2 and grid["m_per_px"] == 60.0
    assert np.array_equal(grid["status"], crop["status"][::2, ::2])


@pytest.mark.parametrize("style_name", ALL_STYLES)
def test_symbols_on_land_without_overlap(style_name):
    crop = _fixture()
    res = render_map(crop, style_name, 256, styles=STYLES)
    status = display_grid(crop, 256)["status"]
    if style_name == "simple":
        assert res.symbols, "fixture should produce terrain symbols"
    boxes = [s["bbox"] for s in res.symbols] + [sp["bbox"] for sp in res.spot_heights]
    for i, (x0, y0, x1, y1) in enumerate(boxes):
        assert 0 <= x0 < x1 <= status.shape[1] and 0 <= y0 < y1 <= status.shape[0]
        for (a0, b0, a1, b1) in boxes[i + 1:]:
            assert x1 <= a0 or a1 <= x0 or y1 <= b0 or b1 <= y0
    for sym in res.symbols:
        x0, y0, x1, y1 = sym["bbox"]
        assert not (status[y0:y1, x0:x1] == OCEAN).any()
        assert status[int(sym["y"] if sym["kind"] == "marsh" else sym["y"] - 0.06 * sym["h"]), int(sym["x"])] == LAND
    for d in res.decorations:
        x0, y0 = d["x"], d["y"]
        region = status[y0:y0 + int(np.ceil(d["h"])), x0:x0 + int(np.ceil(d["w"]))]
        assert (region == OCEAN).all(), d["name"]


def test_terrain_symbols_only_in_simple():
    crop = _fixture()
    simple = render_map(crop, "simple", 256, styles=STYLES)
    kinds = {s["kind"] for s in simple.symbols}
    assert kinds & {"mountain", "snowpeak", "hill"}
    assert {s["id"] for s in simple.symbols} <= {"terrain-mountain", "terrain-snowpeak", "terrain-hill", "terrain-marsh"}
    assert any(r[0] == "symbol" for r in simple.legend)
    for name in ("medieval", "eastern"):
        style = STYLES["styles"][name]
        assert style["layers"]["terrain_symbols"] is False
        assert "symbols" not in style  # no terrain symbol config at all
        res = render_map(crop, name, 256, styles=STYLES)
        assert res.symbols == []
        assert not any(r[0] == "symbol" for r in res.legend)
        page = compose_html(res, "base.png", "prov", styles=STYLES)
        for tid in TERRAIN_IDS:
            assert '#%s"' % tid not in page and 'id="%s"' % tid not in page, (name, tid)


def test_spot_heights_only_in_simple():
    crop = _fixture()
    simple = render_map(crop, "simple", 256, styles=STYLES)
    assert STYLES["styles"]["simple"]["layers"]["spot_heights"] is True
    assert simple.spot_heights, "fixture should produce spot heights in simple"
    assert any(r[0] == "spot" for r in simple.legend)
    for name in ("medieval", "eastern"):
        assert STYLES["styles"][name]["layers"]["spot_heights"] is False
        res = render_map(crop, name, 256, styles=STYLES)
        assert res.spot_heights == []
        assert not any(r[0] == "spot" for r in res.legend)
        page = compose_html(res, "base.png", "prov", styles=STYLES)
        assert "t-spot\"" not in page and "高程点" not in page and "\u25b2" not in page, name


def test_simple_keeps_former_medieval_look():
    simple = STYLES["styles"]["simple"]
    assert simple["sprites"] == ["map-art.svg"] and simple["layers"]["terrain_symbols"] is True
    assert simple["paper"]["seed_name"] == "medieval/paper" and simple["hillshade"]["mode"] == "multiply"
    assert "engraving" not in simple


@pytest.mark.parametrize("name", ["map-art-medieval.svg", "map-art-eastern.svg"])
def test_icon_sprites_have_exactly_required_ids(name):
    ids = sprite_ids((ART_DIR / name).read_text(encoding="utf-8"))
    assert len(ids) == len(set(ids)) == 38
    assert set(ids) == REQUIRED_IDS
    assert not set(ids) & TERRAIN_IDS
    res_ids = {i[4:] for i in ids if i.startswith("res-")}
    assert res_ids == set(RESOURCE_KINDS) and len(res_ids) == 30


def test_styles_point_at_their_sprites_and_routes():
    for name, sprite in (("medieval", "map-art-medieval.svg"), ("eastern", "map-art-eastern.svg")):
        st = STYLES["styles"][name]
        assert st["icon_sprite"] == sprite and st["sprites"] == [sprite]
        assert set(st["routes"]["kinds"]) == set(MANIFEST["routes"]["kinds"])
        for k, v in st["routes"]["kinds"].items():
            assert {"name", "stroke", "width", "dash", "casing"} <= set(v), (name, k)
        # every decoration symbol a style uses exists in the sprite it is pulled from
        svg = style_sprites_svg(st)
        for d in st["decorations"]:
            if d.get("symbol"):
                assert 'id="%s"' % d["symbol"] in svg, (name, d["symbol"])


def test_eastern_capital_unique_and_names():
    east = STYLES["styles"]["eastern"]["towns"]
    assert east["capital_unique"] is True
    assert east["names"] == {"hamlet": "村", "town": "县城", "city": "郡城", "capital": "都城"}
    assert STYLES["styles"]["medieval"]["towns"]["capital_unique"] is False
    ok = validate_towns("eastern", [{"tier": "capital"}, {"tier": "city"}, {"tier": "city", "race": "elf"}], styles=STYLES)
    assert [t["id"] for t in ok] == ["town-capital", "town-city", "town-elf-city"]
    with pytest.raises(ValueError):
        validate_towns("eastern", [{"tier": "capital"}, {"tier": "capital"}], styles=STYLES)
    with pytest.raises(ValueError):  # race towns count toward the single capital too
        validate_towns("eastern", [{"tier": "capital"}, {"tier": "capital", "race": "dwarf"}], styles=STYLES)
    # medieval has no such limit
    assert len(validate_towns("medieval", [{"tier": "capital"}, {"tier": "capital", "race": "orc"}], styles=STYLES)) == 2


def test_resolve_town_symbol_races():
    for name, own in (("medieval", "map-art-medieval.svg"), ("eastern", "map-art-eastern.svg")):
        assert resolve_town_symbol(name, "human", "city", styles=STYLES) == (own, "town-city")
        assert resolve_town_symbol(name, None, "hamlet", styles=STYLES) == (own, "town-hamlet")
        assert resolve_town_symbol(name, "goblin", "town", styles=STYLES) == (own, "town-town")  # unknown race falls back
        for race in ("elf", "dwarf", "orc", "halfling"):
            sprite, sid = resolve_town_symbol(name, race, "capital", styles=STYLES)
            assert sprite == "map-art.svg" and sid == "town-%s-capital" % race
            assert sid in sprite_ids((ART_DIR / sprite).read_text(encoding="utf-8"))
    assert resolve_town_symbol("simple", "goblin", "city", styles=STYLES) == ("map-art.svg", "town-human-city")
    with pytest.raises(ValueError):
        resolve_town_symbol("medieval", "elf", "metropolis", styles=STYLES)


def test_icon_sheet_lists_every_symbol():
    for name in ("medieval", "eastern"):
        page, (w, h) = compose_icon_sheet(name, styles=STYLES, manifest=MANIFEST)
        for sid in REQUIRED_IDS:
            assert 'href="#%s"' % sid in page, (name, sid)
        for tid in TERRAIN_IDS:
            assert tid not in page
    east, _ = compose_icon_sheet("eastern", styles=STYLES, manifest=MANIFEST)
    for label in ("村", "县城", "郡城", "都城"):
        assert ">%s<" % label in east
    assert "唯一" not in east  # uniqueness is a rule, not a caption
    med, _ = compose_icon_sheet("medieval", styles=STYLES, manifest=MANIFEST)
    assert "精灵·城镇" in med and 'href="#town-halfling-capital"' in med


def test_candidates_never_on_sea_or_depression():
    crop = _fixture()
    grid = display_grid(crop, 256)
    for kind, y, x, *_ in terrain_candidates(grid, STYLES["terrain_symbols"], 1.0):
        assert grid["status"][y, x] == LAND


def test_scale_bar_metres():
    sc = scale_bar(60.0, 1.0)
    assert sc["length_px"] * 60.0 == pytest.approx(sc["meters"])
    # 380 ref px × 60 m ≈ 22.8 km → nice round 25 km in 5 × 5 km segments, 416.67 px long
    assert sc["meters"] == 25000.0 and sc["segment_m"] == 5000.0
    assert sc["length_px"] == pytest.approx(25000.0 / 60.0)
    crop = _fixture()
    res = render_map(crop, "simple", 128, styles=STYLES)
    assert res.grid_info["m_per_px"] == 60.0
    assert res.scale["length_px"] * res.grid_info["m_per_px"] == pytest.approx(res.scale["meters"])
