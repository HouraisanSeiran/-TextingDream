"""Quick path (`--overview-only`) of tools/render_world_relief_atlas.py, with the browser and detail work stubbed out.

不启浏览器 / GPU / 服务：find_edge + screenshot 换成写同尺寸空白 PNG 的桩，产品是本测试自己 tmp 目录里的
极小合成 world-relief 产品。验证四件事：
  1. --overview-only 只出 simple-atlas.png / relief-only.png / atlas-source.json，且不进入详情分支（detail_views /
     forest_view / reserved_demo_items 一调就失败），不重复 analyse；
  2. atlas-source.json 仍带同源 manifest/provenance，并记录 overview_only / width / elapsed_seconds；
  3. 不加开关时仍是完整图册（detail-*.png + reserved-demo.png）；
  4. 渲染失败向上透传，不留下半个 atlas-source.json。
"""
import contextlib
import hashlib
import json

import numpy as np
import pytest
from PIL import Image

from app.world_relief import atlas
from app.world_relief.drainage import ocean_mask, river_lines, route
from app.world_relief.source import identity, spatial_noise, subseed
from tools import render_world_relief_atlas as rwra

SPACING = 1000.0
SHAPE = (90, 120)
FIRST = (-59500.0, -44500.0)
_MISSING = object()


def _make_product(root):
    nz, nx = SHAPE
    z, x = np.mgrid[0:nz, 0:nx].astype(float)
    coast = 28 + 7 * np.sin(z / 23.0)
    land = np.clip((x - coast) / 18.0, -1, 1)
    ridge_x = 68 + 0.3 * (z - 45) + 6 * np.sin(z / 17.0)
    ridge = 4200 * np.exp(-((x - ridge_x) / 8.0) ** 2)
    plateau = 900 * np.clip((x - 95) / 15.0, 0, 1)
    noise = 120 * spatial_noise(SHAPE, FIRST, SPACING, subseed(7, "quick-atlas"), 6000.0)
    h = np.where(land > 0, 40 + 600 * land + ridge + plateau + noise * land, -2500 * (-land) - 20).astype(np.float32)
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
    return manifest


@contextlib.contextmanager
def _patched(module, **attrs):
    """setattr/restore without monkeypatch (so module-scoped fixtures can use it)."""
    old = {k: getattr(module, k, _MISSING) for k in attrs}
    for k, v in attrs.items():
        setattr(module, k, v)
    try:
        yield
    finally:
        for k, v in old.items():
            if v is _MISSING:
                delattr(module, k)
            else:
                setattr(module, k, v)


def _browser_stub():
    """Replace Edge with a flat PNG of exactly the requested page size (screenshot() does the same size check)."""
    def screenshot(edge, html_path, png_path, width, height):
        assert edge == "edge-stub"
        Image.new("RGB", (width, height), (250, 246, 238)).save(png_path)

    return dict(find_edge=lambda: "edge-stub", screenshot=screenshot)


@pytest.fixture(scope="module")
def quick_run(tmp_path_factory):
    """One --overview-only run; the detail entry points fail loudly if they are ever reached."""
    root = tmp_path_factory.mktemp("quick-relief")
    manifest = _make_product(root)
    out = tmp_path_factory.mktemp("quick-atlas") / "atlas"
    calls = {"detail_views": 0, "forest_view": 0, "reserved_demo_items": 0, "analyse": 0}

    def boom(name):
        def f(*a, **k):
            calls[name] += 1
            raise AssertionError("--overview-only must not enter the detail path: %s" % name)
        return f

    real_analyse = atlas.analyse

    def counting_analyse(*a, **k):
        calls["analyse"] += 1
        return real_analyse(*a, **k)

    with _patched(rwra, detail_views=boom("detail_views"), forest_view=boom("forest_view"),
                  reserved_demo_items=boom("reserved_demo_items"), **_browser_stub()), \
            _patched(atlas, analyse=counting_analyse):
        rwra.main(["--product", str(root), "--out", str(out), "--width", "600", "--overview-only"])
    src = json.loads((out / "atlas-source.json").read_text(encoding="utf-8"))
    return dict(product=root, out=out, source=src, calls=calls, manifest=manifest)


@pytest.fixture(scope="module")
def full_run(tmp_path_factory):
    """One default run: real detail/reserved rendering, but only on tiny windows and with the browser stubbed."""
    root = tmp_path_factory.mktemp("full-relief")
    manifest = _make_product(root)
    out = tmp_path_factory.mktemp("full-atlas") / "atlas"
    calls = []

    def small_detail_views(p, a, params, width):
        calls.append("detail_views")
        return [(name, atlas.View(0, 0, 30, 40, 300, p.spacing)) for name in ("mountains", "rivers")]

    def small_forest_view(p, a, width, km=(160, 110)):
        calls.append("forest_view")
        return atlas.View(0, 0, 30, 40, 300, p.spacing)

    with _patched(rwra, detail_views=small_detail_views, forest_view=small_forest_view, **_browser_stub()):
        rwra.main(["--product", str(root), "--out", str(out), "--width", "500"])
    src = json.loads((out / "atlas-source.json").read_text(encoding="utf-8"))
    return dict(product=root, out=out, source=src, calls=calls, manifest=manifest)


def _png_names(out):
    return sorted(p.name for p in out.glob("*.png"))


def test_overview_only_renders_only_overview_pages(quick_run):
    assert _png_names(quick_run["out"]) == ["relief-only.png", "simple-atlas.png"]
    assert quick_run["calls"] == dict(detail_views=0, forest_view=0, reserved_demo_items=0, analyse=1)
    for name in ("simple-atlas.png", "relief-only.png"):
        with Image.open(quick_run["out"] / name) as img:
            assert img.format == "PNG" and img.size[0] > 0 and img.size[1] > 0


def test_overview_only_source_json_is_same_source_and_records_quick_path(quick_run):
    src, manifest = quick_run["source"], quick_run["manifest"]
    assert src["overview_only"] is True
    assert src["width"] == 600
    assert src["elapsed_seconds"] >= 0.0
    # same-source provenance: product identity + per-layer origin still point at this frozen product
    assert src["schema"] == atlas.SCHEMA
    assert src["product"]["kind"] == atlas.SOURCE_KIND
    assert src["product"]["identity"] == manifest["identity"]
    assert src["product"]["world_seed"] == manifest["world_seed"]
    assert src["product"]["spacing_m"] == SPACING
    assert src["layers"]["data"] and src["layers"]["decoration"]
    # only the two overview pages are declared, and their hashes are the files on disk
    assert sorted(src["files"]) == ["relief-only.png", "simple-atlas.png"]
    for name, entry in src["files"].items():
        assert hashlib.sha256((quick_run["out"] / name).read_bytes()).hexdigest() == entry["sha256"]
    # unified-interface check survives, but the old-PNG pixel diff (two extra atlas rebuilds) is skipped
    check = src["unified_interface_check"]
    assert check["origin"] == "product:" + str(quick_run["product"])
    assert all(check["arrays_equal"].values())
    assert check["rivers"]["points_equal"] is True
    assert str(check["relief_only_vs_old_png"]).startswith("skipped with --overview-only")


def test_default_run_still_renders_detail_pages(full_run):
    names = _png_names(full_run["out"])
    assert names == ["detail-mountains.png", "detail-rivers.png", "relief-only.png", "reserved-compare.png",
                     "reserved-demo.png", "simple-atlas.png"]
    assert "detail_views" in full_run["calls"] and "forest_view" in full_run["calls"]
    src = full_run["source"]
    assert src["overview_only"] is False
    assert src["width"] == 500
    assert sorted(src["files"]) == ["detail-mountains.png", "detail-rivers.png", "relief-only.png",
                                     "reserved-demo.png", "simple-atlas.png"]
    assert src["files"]["detail-mountains.png"]["kind"] == "detail"
    assert src["files"]["reserved-demo.png"]["kind"] == "reserved-demo"
    assert src["files"]["reserved-demo.png"]["compare_image"] == "reserved-compare.png"


def test_render_failure_propagates_and_leaves_no_source_json(tmp_path):
    root = tmp_path / "relief"
    root.mkdir()
    _make_product(root)
    out = tmp_path / "atlas"

    def broken_screenshot(edge, html_path, png_path, width, height):
        raise RuntimeError("edge screenshot failed")

    with _patched(rwra, screenshot=broken_screenshot, find_edge=lambda: "edge-stub"):
        with pytest.raises(RuntimeError, match="screenshot failed"):
            rwra.main(["--product", str(root), "--out", str(out), "--width", "300", "--overview-only"])
    assert not (out / "atlas-source.json").exists()
