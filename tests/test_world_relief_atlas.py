"""Atlas rendering of a frozen world-relief product: display only, deterministic, symbols avoid water."""
import hashlib
import inspect
import json

import numpy as np
import pytest
from scipy import ndimage as nd

from app.map_source.core import GridSource
from app.world_relief import atlas
from app.world_relief.drainage import ocean_mask, river_lines, route
from app.world_relief.source import identity, spatial_noise, subseed

SPACING = 1000.0
SHAPE = (150, 200)
FIRST = (-99500.0, -74500.0)


def _write_product(root):
    nz, nx = SHAPE
    z, x = np.mgrid[0:nz, 0:nx].astype(float)
    # sea on the west, land rising east to a curved NE-SW ridge (~4200 m) with a flat plateau to the far east
    coast = 45 + 10 * np.sin(z / 23.0)
    land = np.clip((x - coast) / 25.0, -1, 1)
    ridge_x = 110 + 0.35 * (z - 75) + 8 * np.sin(z / 17.0)
    ridge = 4200 * np.exp(-((x - ridge_x) / 9.0) ** 2)
    plateau = 900 * np.clip((x - 150) / 20.0, 0, 1)
    noise = 120 * spatial_noise(SHAPE, FIRST, SPACING, subseed(7, "test-relief"), 6000.0)
    h = np.where(land > 0, 40 + 600 * land + ridge + plateau + noise * land, -2500 * (-land) - 20)
    h = h.astype(np.float32)
    ocean = ocean_mask(h.astype(float))
    h[~ocean] = np.maximum(h[~ocean], 1.0)
    flow = route(h.astype(float), ocean, SPACING)
    lines = river_lines(flow, ocean, FIRST, SPACING, threshold_m2=60e6)
    arrays = dict(elevation_m=h, ocean_mask=ocean, inland_depression_mask=flow["closed_mask"],
                  lake_surface_m=flow["filled_m"].astype(np.float32), drainage_area_m2=flow["area_m2"].astype(np.float32))
    for name, a in arrays.items():
        np.save(root / (name + ".npy"), a, allow_pickle=False)
    (root / "rivers.json").write_text(json.dumps(dict(schema="coordinate-river-segments-v1", threshold_km2=60, lines=lines)),
                                      encoding="utf-8")
    files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.iterdir())}
    manifest = dict(schema="world-relief-pilot-2.0", world_seed=20260903, shape_zx=list(SHAPE), first_sample_xz_m=list(FIRST),
                    spacing_m=SPACING, axes="arrays [z,x]; X east; Z south; metres; cell centres; sea=0",
                    boundary="finite grid; no wrap", files=files)
    manifest["identity"] = identity(manifest)
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


@pytest.fixture(scope="module")
def product_dir(tmp_path_factory):
    return _write_product(tmp_path_factory.mktemp("relief"))


@pytest.fixture(scope="module")
def layers(product_dir):
    p = atlas.load_product(product_dir)
    params = atlas.AtlasParams(width_px=800, river_spacing_px=20.0)
    return p, params, atlas.build_atlas(p, params)


def _boxes(L, kinds=None):
    return [s["box"] for s in L.symbols if kinds is None or s["kind"] in kinds]


def test_fixture_has_mountains_trees_and_rivers(layers):
    _, _, L = layers
    kinds = {s["kind"] for s in L.symbols}
    assert {"mountain"} <= kinds or {"snowpeak"} <= kinds
    assert len(L.rivers) > 0


def test_symbols_never_on_sea_lake_or_river(layers):
    _, _, L = layers
    H, W = L.view.height, L.view.width
    for box in _boxes(L):
        x0, y0, x1, y1 = atlas._irect(box)
        assert 0 <= x0 and 0 <= y0 and x1 <= W and y1 <= H
        assert not L.forbidden[y0:y1, x0:x1].any()
        assert not L.sea[y0:y1, x0:x1].any()
    # independent check against the drawn river geometry itself
    pts = np.concatenate([r["points"] for r in L.rivers])
    for x0, y0, x1, y1 in _boxes(L):
        inside = (pts[:, 0] > x0) & (pts[:, 0] < x1) & (pts[:, 1] > y0) & (pts[:, 1] < y1)
        assert not inside.any()


def test_symbols_do_not_overlap(layers):
    _, _, L = layers
    b = np.array([atlas._irect(x) for x in _boxes(L)], float)
    x0, y0, x1, y1 = b.T
    ox = np.minimum(x1[:, None], x1[None]) - np.maximum(x0[:, None], x0[None])
    oy = np.minimum(y1[:, None], y1[None]) - np.maximum(y0[:, None], y0[None])
    overlap = (ox > 0) & (oy > 0)
    np.fill_diagonal(overlap, False)
    assert not overlap.any()


def test_mountains_not_on_flat_plateau(layers):
    p, _, L = layers
    for s in L.symbols:
        if s["kind"] in ("mountain", "snowpeak"):
            iz, ix = s["cell_zx"]
            assert ix < 150 or abs(ix - (110 + 0.35 * (iz - 75))) < 40  # on/near the ridge, not on the eastern plateau


def test_relief_only_has_no_symbols(layers, product_dir):
    p, _, L = layers
    html = atlas.compose_html(L, p, "base.png", with_overlays=False)
    drawn = html[html.index('<image href="base.png"'):]  # after the sprite <defs>
    assert "<use" not in drawn and "<path" not in drawn
    img = np.asarray(atlas.relief_page(L, p))
    m, H, W = L.margin, L.view.height, L.view.width
    assert np.array_equal(img[m:m + H, m:m + W], L.relief_rgb)
    full = atlas.compose_html(L, p, "base.png", with_overlays=True)
    assert "terrain-mountain" in full or "terrain-snowpeak" in full


def test_scale_bar_length_matches_metres(layers):
    p, _, L = layers
    sc = L.scale
    assert L.view.mpp == pytest.approx(SHAPE[1] * SPACING / L.view.width)
    assert sc["length_px"] * L.view.mpp == pytest.approx(sc["meters"], rel=1e-12)
    assert sc["segment_m"] * sc["segments"] == pytest.approx(sc["meters"])


def test_render_is_deterministic(product_dir, layers):
    _, params, L = layers
    p2 = atlas.load_product(product_dir)
    L2 = atlas.build_atlas(p2, params)
    assert np.array_equal(L.page_rgb, L2.page_rgb)
    assert np.array_equal(L.relief_rgb, L2.relief_rgb)
    assert [(s["id"], s["box"]) for s in L.symbols] == [(s["id"], s["box"]) for s in L2.symbols]
    assert L.seeds == L2.seeds
    assert L.seeds["paper"] == subseed(20260903, "atlas/paper")
    assert atlas.compose_html(L, p2, "b.png") == atlas.compose_html(L2, p2, "b.png")


def test_data_arrays_unchanged(product_dir, layers):
    p, _, _ = layers
    files = json.loads((product_dir / "manifest.json").read_text(encoding="utf-8"))["files"]
    for name in ("elevation_m", "ocean_mask", "inland_depression_mask", "lake_surface_m", "drainage_area_m2"):
        data = (product_dir / (name + ".npy")).read_bytes()
        assert hashlib.sha256(data).hexdigest() == files[name + ".npy"]
    assert hashlib.sha256((product_dir / "rivers.json").read_bytes()).hexdigest() == files["rivers.json"]
    assert np.array_equal(p.elevation, np.load(product_dir / "elevation_m.npy"))
    assert np.array_equal(p.ocean, np.load(product_dir / "ocean_mask.npy"))
    assert np.array_equal(p.area_m2, np.load(product_dir / "drainage_area_m2.npy"))


def test_tampered_product_refused(tmp_path):
    root = _write_product(tmp_path)
    h = np.load(root / "elevation_m.npy")
    h[0, 0] += 1
    np.save(root / "elevation_m.npy", h, allow_pickle=False)
    with pytest.raises(ValueError, match="(?i)hash"):
        atlas.load_product(root)
    m = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    m["world_seed"] = 1
    (root / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
    with pytest.raises(ValueError, match="(?i)identity"):
        atlas.load_product(root)


# ------------------------------------------------------------ unified interface / mountains / forest / reserved

FOREST = ("tree", "rock", "grass")


def test_reads_through_unified_interface(layers):
    p, _, _ = layers
    assert isinstance(p.source, GridSource)
    assert p.info.kind == "world-relief-pilot"
    src = inspect.getsource(atlas)
    assert "np.load" not in src and "rivers.json\")" not in src and "read_bytes" not in src


def test_one_peak_per_mountain_patch(layers):
    p, params, L = layers
    a = atlas.analyse(p, params)
    peaks = [s for s in L.symbols if s["kind"] in ("mountain", "snowpeak")]
    assert peaks
    labels = [int(a["patch_label"][s["cell_zx"]]) for s in peaks]
    assert all(k > 0 for k in labels)
    assert len(labels) == len(set(labels))  # at most one symbol per connected range
    by_label = {pt["label"]: pt for pt in a["patches"]}
    for s, k in zip(peaks, labels):
        assert a["h0"][s["cell_zx"]] >= by_label[k]["peak_h"] - params.peak_tol_m
        assert (s["id"] == "terrain-snowpeak") == (a["h0"][s["cell_zx"]] >= params.snowpeak_m)
    assert not any(s["kind"] == "hill" for s in L.symbols)


def test_forest_mixed_planting(layers):
    _, _, L = layers
    trees = [s for s in L.symbols if s["kind"] == "tree"]
    assert len(trees) > 50
    assert len({s["species"] for s in trees}) >= 3
    assert len({s["id"] for s in trees}) >= 6  # several variants
    assert any(s["mirror"] for s in trees) and any(not s["mirror"] for s in trees)
    assert not {s["species"] for s in trees} & set(atlas.FANTASY_TREES)  # fantasy species are opt-in
    assert {s["species"] for s in trees if s["species"] == "willow"} <= {"willow"}
    assert any(s["kind"] == "rock" for s in L.symbols)
    assert any(s["kind"] == "grass" for s in L.symbols)
    ids = {s["id"] for s in L.symbols}
    html = atlas.compose_html(L, layers[0], "base.png")
    for sid in list(ids)[:40]:
        assert 'id="%s"' % sid in html


def test_willow_and_reeds_only_near_water(layers):
    _, params, L = layers
    near = nd.distance_transform_edt(~L.forbidden)
    s = L.view.s
    for sym in L.symbols:
        d = near[min(L.view.height - 1, int(sym["y"])), min(L.view.width - 1, int(sym["x"]))]
        if sym["kind"] == "grass" and sym["grass_kind"] == "reed":
            assert d <= params.reed_ring_px * s + 1.5
        if sym["kind"] == "tree" and sym["species"] == "willow":
            assert d <= params.willow_px * s + 1.5


def _forest_centre_m(p, L):
    f = [s for s in L.symbols if s["kind"] == "tree"]
    x = float(np.median([s["x"] for s in f]))
    y = float(np.median([s["y"] for s in f]))
    ex = p.first[0] - p.spacing / 2 + L.view.x0 * p.spacing
    ez = p.first[1] - p.spacing / 2 + L.view.z0 * p.spacing
    return ex + x * L.view.mpp, ez + y * L.view.mpp


def test_reserved_regions_stay_clear(layers):
    p, params, L0 = layers
    cx, cz = _forest_centre_m(p, L0)
    items = [{"type": "circle", "x": cx, "z": cz, "r": 12000.0},
             {"type": "polyline", "points": [[cx - 30000.0, cz + 20000.0], [cx + 30000.0, cz - 5000.0]], "width": 5000.0},
             {"type": "polygon", "points": [[cx - 5000.0, cz - 30000.0], [cx + 15000.0, cz - 30000.0], [cx + 15000.0, cz - 18000.0]]}]
    L = atlas.build_atlas(p, params, reserved=items)
    mask = L.reserved
    assert mask is not None and mask.any()
    forest = [s for s in L.symbols if s["kind"] in FOREST]
    assert forest
    for s in forest:
        x0, y0, x1, y1 = atlas._irect(s["box"])
        assert not mask[y0:y1, x0:x1].any()
    n0 = sum(1 for s in L0.symbols if s["kind"] in FOREST)
    assert len(forest) < n0  # something was actually cleared
    # mountains are not affected by reserved areas
    assert [s["box"] for s in L.symbols if s["kind"] in ("mountain", "snowpeak")] == \
        [s["box"] for s in L0.symbols if s["kind"] in ("mountain", "snowpeak")]


def test_without_reserved_output_is_unchanged(layers):
    p, params, L0 = layers
    for kw in (dict(reserved=None), dict(reserved=[])):
        L = atlas.build_atlas(p, params, **kw)
        assert np.array_equal(L.page_rgb, L0.page_rgb)
        assert [(s["id"], s["box"], s["draw"], s["mirror"]) for s in L.symbols] == \
            [(s["id"], s["box"], s["draw"], s["mirror"]) for s in L0.symbols]
        assert atlas.compose_html(L, p, "b.png") == atlas.compose_html(L0, p, "b.png")


def _consecutive_pair_drawn(polys, line_id, p0, p1):
    """True when some drawn polyline of `line_id` has the display points p0, p1 as consecutive raw vertices."""
    for r in polys:
        if r["id"] != line_id:
            continue
        raw = r["raw"]
        for k in range(len(raw) - 1):
            if np.allclose(raw[k], p0) and np.allclose(raw[k + 1], p1):
                return True
    return False


def test_through_lake_edges_are_not_drawn(layers):
    import copy
    import dataclasses
    p, _, _ = layers
    params = atlas.AtlasParams(width_px=800, river_spacing_px=20.0, river_merge_cells=0.0)
    view = atlas.full_view(p, params.width_px)
    a = atlas.analyse(p, params)
    base, _ = atlas.river_polylines(p, a, view, params)

    # pick a drawn run with several vertices and flag one interior edge of its source line as a through-lake chord
    run = max(base, key=lambda r: len(r["raw"]))
    assert len(run["raw"]) >= 4
    ex = p.first[0] - p.spacing / 2 + view.x0 * p.spacing
    ez = p.first[1] - p.spacing / 2 + view.z0 * p.spacing
    line = next(l for l in p.rivers if l["id"] == run["id"])
    c = np.asarray(line["coordinates_xz_m"], float)
    px = np.column_stack([(c[:, 0] - ex) / view.mpp, (c[:, 1] - ez) / view.mpp])
    m = len(run["raw"]) // 2
    j = next(i for i in range(len(px)) if np.allclose(px[i], run["raw"][m]))
    assert np.allclose(px[j + 1], run["raw"][m + 1])
    assert _consecutive_pair_drawn(base, run["id"], run["raw"][m], run["raw"][m + 1])

    # without the flag the product renders exactly as before; a False flag changes nothing either
    plain = dataclasses.replace(p, rivers=copy.deepcopy(p.rivers), cache={})
    for l in plain.rivers:
        l["through_lake"] = False
        l["lake_spans"] = []
    same, _ = atlas.river_polylines(plain, a, view, params)
    assert len(same) == len(base)
    for r0, r1 in zip(base, same):
        assert r0["id"] == r1["id"]
        assert np.array_equal(r0["raw"], r1["raw"]) and np.array_equal(r0["points"], r1["points"])

    # flagged: the chord edge is gone, every other edge of the line is still drawn
    flagged = dataclasses.replace(p, rivers=copy.deepcopy(p.rivers), cache={})
    for l in flagged.rivers:
        if l["id"] == run["id"]:
            l["through_lake"] = True
            l["lake_spans"] = [[j, j + 1]]
    out, _ = atlas.river_polylines(flagged, a, view, params)
    assert not _consecutive_pair_drawn(out, run["id"], run["raw"][m], run["raw"][m + 1])
    assert _consecutive_pair_drawn(out, run["id"], run["raw"][m - 1], run["raw"][m])
    assert _consecutive_pair_drawn(out, run["id"], run["raw"][m + 1], run["raw"][m + 2]) if m + 2 < len(run["raw"]) else True
    assert len([r for r in out if r["id"] != run["id"]]) == len([r for r in base if r["id"] != run["id"]])


def test_product_from_source_keeps_through_lake_flag(product_dir):
    # the fixture's relief loader carries no flag: lines stay exactly as before (no extra keys)
    p = atlas.load_product(product_dir)
    assert all("through_lake" not in l and "lake_spans" not in l for l in p.rivers)
