"""Natural-surface display: muted biomes, suitable supplemental woodland, typed canopy, no data edits."""
from dataclasses import replace

import numpy as np
import pytest

from app.map_render import load_styles
from app.world_relief import atlas
from tests.test_world_relief_atlas import _write_product


@pytest.fixture(scope="module")
def product(tmp_path_factory):
    return atlas.load_product(_write_product(tmp_path_factory.mktemp("natural-surface")))


@pytest.fixture(scope="module")
def params():
    return atlas.AtlasParams(width_px=800, forest_area_mpp=200, biome_mpp=200, river_spacing_px=20)


def test_low_saturation_palette_and_no_default_altitude_fade(params):
    for _, _, col in atlas.BIOMES + atlas.FOREST_TYPES:
        rgb = atlas.hex_rgb(col)
        assert (rgb.max() - rgb.min()) / rgb.max() < 0.35
    assert params.biome_alpha >= 0.85 and params.biome_fade_max == 0


def test_supplemental_woodland_is_separate_and_suitable(product, params):
    a = atlas.analyse(product, params)
    off = atlas.analyse(product, replace(params, natural_forest_extra=False))
    assert np.array_equal(a["forest"], off["forest"])
    assert np.array_equal(off["natural_forest"], off["forest"])
    assert not (a["forest"] & ~a["natural_forest"]).any()
    extra = a["natural_forest"] & ~a["forest"]
    assert extra.any()
    assert not (extra & (~a["land"] | a["lake"])).any()
    assert np.isin(a["biome"][extra], (2, 3, 6)).all()
    assert (a["slope"][extra] < params.forest_max_slope).all()
    assert ((a["natural_type"] > 0) == a["natural_forest"]).all()
    product.cache.clear()
    assert np.array_equal(a["natural_forest"], atlas.analyse(product, params)["natural_forest"])


def test_only_natural_pages_consume_extra_woodland(product, params):
    v = atlas.full_view(product, params.width_px)
    a = atlas.analyse(product, params)
    df = atlas.display_fields(product, a, v, params)
    offp = replace(params, natural_forest_extra=False)
    off = atlas.display_fields(product, atlas.analyse(product, offp), v, offp)
    assert (df["forest"] >= off["forest"] - 1e-12).all()
    assert (df["forest"] > off["forest"] + 0.1).any()
    small = replace(params, biome_mpp=1e9)
    smalloff = replace(small, natural_forest_extra=False)
    d1 = atlas.display_fields(product, atlas.analyse(product, small), v, small)
    d2 = atlas.display_fields(product, atlas.analyse(product, smalloff), v, smalloff)
    for k in d1:
        assert np.array_equal(d1[k], d2[k]), k


def test_typed_canopy_varies_but_is_world_addressed(product, params):
    v1 = atlas.View(0, 0, 100, 100, 200, product.spacing)
    v2 = atlas.View(0, 10, 100, 100, 200, product.spacing)
    fields = []
    for k in range(1, 5):
        types = np.full((200, 200), k, np.int8)
        t1 = atlas.natural_forest_texture(product, v1, params, types)
        t2 = atlas.natural_forest_texture(product, v2, params, types)
        assert np.allclose(t1[:, 20:], t2[:, :180])
        assert np.array_equal(t1, atlas.natural_forest_texture(product, v1, params, types))
        assert np.isfinite(t1).all() and t1.std() > 0.01 and np.abs(t1).max() < 1.5
        fields.append(t1)
    assert all(not np.allclose(fields[0], t) for t in fields[1:])
    assert fields[3].std() < fields[2].std()  # open woodland is quieter than rainforest


def test_gentle_highlands_keep_biome_hue_and_steep_ground_gains_rock(product, params):
    # Isolate the slope-based rock treatment from the newer optional mountain emphasis.
    params = replace(params, mount_tone_alpha=0.0)
    v = atlas.View(0, 0, 40, 40, 80, product.spacing)
    shape = (v.height, v.width)
    f = {k: np.full(shape, value) for k, value in dict(shade_h=1800., ecol=1800., coast=1., lake=-1.,
         depth=0., forest=0., conifer=0., mount=1., slope=0.).items()}
    f["biome_rgb"] = np.broadcast_to(np.array([115., 139., 112.]), shape + (3,)).copy()
    f["forest_rgb"] = f["biome_rgb"].copy()
    f["forest_type"] = np.zeros(shape, np.int8)
    style = load_styles()["styles"]["simple"]
    gentle = atlas.paint_map(product, f, v, params, style)
    # Mountain membership alone must not add blanket brown on natural pages.
    unmarked = atlas.paint_map(product, dict(f, mount=np.zeros(shape)), v, replace(params, mount_shade_boost=0), style)
    assert np.allclose(gentle, unmarked)
    steep = atlas.paint_map(product, dict(f, slope=np.full(shape, 0.3)), v, params, style)
    assert np.abs(gentle - steep).mean() > 1
    assert (gentle[..., 1] - gentle[..., 0]).mean() > (steep[..., 1] - steep[..., 0]).mean()


def test_footer_and_provenance_describe_display_supplement(product, params):
    L = atlas.build_atlas(product, params)
    text = atlas.compose_html(L, product, "base.png")
    assert "补充林区" in text and "非气候或生态数据" in text
    assert all(name in text for _, name, _ in atlas.FOREST_TYPES)
    assert L.page_rgb.shape[0] > L.view.height + 2 * L.margin
    # Footer background must not stretch the last noise row into vertical stripes.
    assert np.ptp(L.page_rgb[-10:].astype(float), axis=1).max() == 0
    assert atlas.relief_page(L).height == L.view.height + 2 * L.margin
    prov = atlas.provenance(product, L, params, {})
    notes = " ".join(prov["layers"]["approximate"])
    assert "近似补林" in notes and "natural_forest" in notes and "不是气候" in notes
    assert atlas.summarize(L)["surface_style"] == "natural-low-saturation"
    assert atlas.summarize(L)["supplemental_woodland"] is True
