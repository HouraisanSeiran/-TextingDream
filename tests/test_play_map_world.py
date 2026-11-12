"""world_map_product link parsing and planar helpers (no Terragenesis venv required)."""
import json
from pathlib import Path

import numpy as np
import pytest

from app import play_map, play_map_world as pmw


def test_parse_link_accepts_world_and_civ():
    civ = play_map.parse_link({'mechanics': {'map': {
        'kind': 'civ_atlas', 'import_id': 'mi_' + 'a' * 12,
        'fog': {'reveal_radius_km': 200}}}})
    assert civ['kind'] == 'civ_atlas' and civ['reveal_radius_km'] == 200
    world = play_map.parse_link({'mechanics': {'map': {
        'kind': 'world_map_product',
        'product_path': 'artifacts/fast-world/web-x',
        'product_identity': 'b' * 64,
        'spacing_m': 4000,
        'worldgen_job_id': '20261108-120000-abcd',
        'fog': {'reveal_radius_km': 150}}}})
    assert world['kind'] == play_map.LINK_KIND_WORLD
    assert world['spacing_m'] == 4000.0 and world['reveal_radius_km'] == 150


def test_parse_world_rejects_traversal():
    with pytest.raises(ValueError, match='\\.\\.'):
        pmw.parse_world_link(dict(kind='world_map_product', product_path='../secret',
                                  product_identity='c' * 64, fog={}))


def test_planar_bbox_and_location():
    place = {'coordinates': [120000.0, -80000.0]}
    assert pmw.location_xz(place) == (120000.0, -80000.0)
    assert play_map.location_coordinates(place, planar=True) == (120000.0, -80000.0)
    assert play_map.location_coordinates(place, planar=False) is None
    box = pmw.bbox_planar([{'lon': 0.0, 'lat': 0.0, 'radius_km': 10.0}])
    assert box and box[0][0] < 0 < box[0][1]


def test_validate_story_map_planar_coords():
    story = {
        'locations': [{'id': 'a', 'coordinates': [5000.0, -5000.0]}],
        'mechanics': {'map': {
            'kind': 'world_map_product',
            'product_path': 'artifacts/fast-world/web-demo',
            'product_identity': 'd' * 64,
            'fog': {'reveal_radius_km': 100},
        }},
    }
    link = play_map.validate_story_map(story)
    assert link['kind'] == play_map.LINK_KIND_WORLD


def test_hypsometric_and_resolve_missing(tmp_path):
    elev = np.array([[100.0, -50.0], [2000.0, -10.0]], np.float32)
    status = np.array([[5, 3], [5, 4]], np.uint8)
    rgb = pmw._hypsometric_rgb(elev, status)
    assert rgb.shape == (2, 2, 3) and rgb.dtype == np.uint8
    link = dict(kind=pmw.KIND, product_path='artifacts/missing', product_identity='e' * 64,
                spacing_m=2000.0, reveal_radius_km=100)
    status_code, ctx = play_map.resolve(store=None, root=tmp_path, story={'mechanics': {'map': {
        'kind': pmw.KIND, 'product_path': 'nope', 'product_identity': 'e' * 64, 'fog': {}}}},
        repo_root=tmp_path)
    assert status_code in (play_map.STATUS_MISSING, play_map.STATUS_UNREADABLE)
    assert ctx['link']['kind'] == pmw.KIND


def test_draw_rivers_strokes_polyline():
    rgb = np.zeros((20, 20, 3), dtype=np.uint8)
    rivers = [{'points_xz_m': [[0.0, 0.0], [19000.0, 19000.0]]}]
    pmw._draw_rivers(rgb, rivers, (0.0, 20000.0, 0.0, 20000.0), 20, 20)
    assert np.any(rgb[:, :, 2] > 0)  # blue channel of river colour
    assert not np.all(rgb == 0)
