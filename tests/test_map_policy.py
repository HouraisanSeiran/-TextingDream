"""map_policy: Terragenesis default; civ-atlas opt-in."""
import json
from pathlib import Path

import pytest

from app import map_policy, play_map, play_map_world as pmw
from app.paths import ROOT


def test_civ_atlas_disabled_when_unset_or_zero(monkeypatch):
    monkeypatch.setenv('TEXTILE_CIV_ATLAS', '0')
    assert map_policy.civ_atlas_enabled() is False
    with pytest.raises(map_policy.CivAtlasDisabled):
        map_policy.require_civ_atlas('unit')
    monkeypatch.delenv('TEXTILE_CIV_ATLAS', raising=False)
    # Empty / missing also means off (production default).
    assert map_policy.civ_atlas_enabled({'TEXTILE_CIV_ATLAS': ''}) is False
    assert map_policy.civ_atlas_enabled({}) is False


def test_civ_atlas_enable_env(monkeypatch):
    monkeypatch.setenv('TEXTILE_CIV_ATLAS', '1')
    assert map_policy.civ_atlas_enabled() is True
    map_policy.require_civ_atlas('unit')


def test_default_product_present():
    assert map_policy.default_product_exists(ROOT)
    raw = map_policy.default_player_map_raw(ROOT)
    assert raw['kind'] == 'world_map_product'
    assert raw['product_path'].startswith('artifacts/')
    assert len(raw['product_identity']) == 64


def test_parse_link_applies_default_when_absent():
    link = play_map.parse_link({'title': 'x'}, apply_default=True, repo_root=ROOT)
    assert link is not None
    assert link['kind'] == play_map.LINK_KIND_WORLD
    assert 'product_identity' in link


def test_resolve_default_tg_product(tmp_path):
    """Resolve with no mechanics.map loads the real TG speed product from the repo."""
    status, ctx = play_map.resolve(store=None, root=tmp_path,
                                   story={'title': 'no-map'}, repo_root=ROOT)
    assert status == play_map.STATUS_OK
    assert ctx['link']['kind'] == play_map.LINK_KIND_WORLD
    assert ctx['map_source'] is not None
    assert ctx['map_source'].info.identity == map_policy.default_world_identity(ROOT)


def test_resolve_civ_atlas_refused_when_disabled(monkeypatch, tmp_path):
    monkeypatch.setenv('TEXTILE_CIV_ATLAS', '0')
    story = {'mechanics': {'map': {
        'kind': 'civ_atlas', 'import_id': 'mi_' + 'a' * 12,
        'fog': {'reveal_radius_km': 200}}}}
    status, ctx = play_map.resolve(store=type('S', (), {'get': staticmethod(lambda *a: None)})(),
                                   root=tmp_path, story=story, repo_root=tmp_path)
    assert status == play_map.STATUS_BACKEND_OFF
    assert ctx['link']['kind'] == 'civ_atlas'


def test_civ_atlas_package_isolated():
    import app.civ_atlas as pkg
    assert 'app.civ_atlas.snapshot' in pkg.MODULES
    from app.civ_atlas import snapshot, history, exploration
    assert hasattr(snapshot, 'FORMAT')
    assert hasattr(history, 'build')
    assert hasattr(exploration, 'road_graph')
