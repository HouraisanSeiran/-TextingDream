"""Source-backed ice display, synthetic grids only; no browser/GPU/world jobs."""
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

from app.map_render import load_styles
from app.map_source import LAND
from app.world_relief import atlas


class Source:
    def __init__(self, ice=True):
        shape = (32, 40)
        self.arrays = dict(status=np.full(shape, LAND, np.uint8), elevation_m=np.full(shape, 800.),
                           water_surface_m=np.full(shape, np.nan), drainage_area_m2=np.full(shape, 1e6))
        if ice:
            self.arrays.update(glacier_ice_thickness_m=np.full(shape, 20.),
                               glacier_ice_surface_m=np.full(shape, 820.),
                               glacier_coverage_fraction=np.ones(shape), glacier_simulated_fraction=np.ones(shape))
            self.arrays['glacier_simulated_fraction'][:, :10] = 0
            self.arrays['glacier_ice_thickness_m'][0, 0] = np.nan
        self.info = SimpleNamespace(shape_zx=shape, spacing_m=10000., first_sample_xz_m=(5000., 5000.),
            layers=tuple(self.arrays), identity='synthetic', kind='world-map-product', schema='world-map-product-v1',
            world_seed=20260903, lineage=('parent',), limitations=(), grid_semantics='cell-centre', layer_metadata={})
        self.requests = []

    def sample(self, x, z, layers):
        self.requests.append(layers)
        iz = np.rint((z-5000)/10000).astype(int)
        ix = np.rint((x-5000)/10000).astype(int)
        return {k: self.arrays[k][iz, ix] for k in layers}

    def vectors(self, kind):
        assert kind == 'rivers'
        return []


def fields(product, params=None):
    params = params or atlas.AtlasParams(width_px=80)
    view = atlas.full_view(product, params.width_px)
    return atlas.display_fields(product, atlas.analyse(product, params), view, params), view, params


def test_optional_source_layers_preserved_and_missing_domain_not_zero():
    source = Source()
    original = {k: v.copy() for k, v in source.arrays.items()}
    p = atlas.product_from_source(source, rows=7)
    assert set(atlas.GLACIER_LAYERS).issubset(source.requests[0])
    np.testing.assert_equal(p.ice_thickness, source.arrays['glacier_ice_thickness_m'])
    f, _, _ = fields(p)
    assert np.isnan(f['ice_thickness_m'][0, 0])
    assert not f['glacier_valid'][:, :20].any()
    assert not f['glacier_alpha'][:, :20].any()
    assert f['glacier_alpha'][:, 20:].min() > .99  # actual 20m H visible despite being below snowline
    for name in original:
        np.testing.assert_equal(source.arrays[name], original[name])


def test_ice_covers_forest_and_snow_colour_without_data_edits():
    p = atlas.product_from_source(Source())
    f, view, params = fields(p)
    a = atlas.analyse(p, params)
    originals = {k: v.copy() for k, v in a.items() if isinstance(v, np.ndarray)}
    style = load_styles()['styles']['simple']
    on = atlas.paint_map(p, f, view, params, style)
    off = atlas.paint_map(p, f, view, replace(params, glacier_display=False), style)
    known = f['glacier_mask']
    unknown = ~f['glacier_valid']
    target = atlas.hex_rgb(atlas.GLACIER_HEX)
    assert np.abs(on[known]-target).mean() < 2
    assert np.abs(on[known]-off[known]).mean() > 20
    np.testing.assert_array_equal(on[unknown], off[unknown])
    for name, before in originals.items():
        np.testing.assert_array_equal(a[name], before)
    np.testing.assert_array_equal(p.elevation, np.full(p.shape, 800))


def test_no_glacier_legacy_pixels_and_sample_call_unchanged():
    src = Source(ice=False)
    p = atlas.product_from_source(src)
    assert p.ice_thickness is None and p.simulated_mask is None
    assert all(q == atlas.LAYERS for q in src.requests)
    f, view, params = fields(p)
    off, _, _ = fields(p, replace(params, glacier_display=False))
    assert f.keys() == off.keys() and 'glacier_alpha' not in f
    for key in f:
        np.testing.assert_array_equal(f[key], off[key])
    style = load_styles()['styles']['simple']
    np.testing.assert_array_equal(atlas.paint_map(p, f, view, params, style),
                                  atlas.paint_map(p, off, view, replace(params, glacier_display=False), style))


def test_coverage_and_missing_fields_have_no_fabricated_ice():
    src = Source()
    src.arrays['glacier_coverage_fraction'][:] = .25
    p = atlas.product_from_source(src)
    f, _, _ = fields(p)
    assert f['glacier_alpha'].max() == pytest.approx(.25 * (1-np.exp(-5)))
    p.ice_thickness[:] = 0
    f, _, _ = fields(p)
    assert not f['glacier_alpha'].any()


def test_ice_forbids_symbols_but_is_not_sea_and_legend_is_distinct():
    source = Source()
    source.arrays['glacier_simulated_fraction'][:] = 1
    source.arrays['glacier_ice_thickness_m'][:] = 20
    p = atlas.product_from_source(source)
    params = atlas.AtlasParams(width_px=100)
    L = atlas.build_atlas(p, params)
    assert L.forbidden.all() and not L.sea.any()
    assert not L.symbols  # no forest or mountain sprite bounding box can overlap ice
    rows = atlas.legend_rows(L)
    assert any(k == 'glacier' and '非近似雪色' in text for k, _, text in rows)
    prov = atlas.provenance(p, L, params, {})
    assert set(atlas.GLACIER_LAYERS).issubset(prov['product']['consumed_layers'])
    assert 'unmodelled' in prov['glacier_display']['known_domain']
    assert 'not elevation snow proxy' in prov['glacier_display']['source']
    assert any('不是积雪数据' in text for text in prov['layers']['approximate'])
    assert '域外未模拟' in '\n'.join(atlas._natural_legend_footer(L))
    assert atlas.GLACIER_HEX in '\n'.join(atlas._natural_legend_footer(L))


def test_cli_world_product_path_preserves_legacy_loader_branch(tmp_path, monkeypatch):
    from tools import render_world_relief_atlas as cli
    p = atlas.product_from_source(Source())
    calls = []
    monkeypatch.setattr(atlas, 'load_source', lambda kind, path: (calls.append((kind, path)) or p.source))
    monkeypatch.setattr(atlas, 'load_product', lambda *a, **k: pytest.fail('legacy loader called'))
    monkeypatch.setattr(cli, 'find_edge', lambda: 'unused')
    captured = []

    def overview(product, params, *args, **kwargs):
        captured.append((product, params))
        return SimpleNamespace()

    monkeypatch.setattr(cli, 'render_overview', overview)
    monkeypatch.setattr(atlas, 'provenance', lambda *a: {})
    monkeypatch.setattr(cli, 'legacy_comparison', lambda *a, **k: {})
    cli.main(['--source-kind', 'world-map-product', '--product', str(tmp_path),
              '--out', str(tmp_path/'atlas'), '--overview-only', '--no-glacier-display'])
    assert calls == [('world-map-product', tmp_path)]
    assert captured[0][0].ice_thickness is not None
    assert not captured[0][1].glacier_display
