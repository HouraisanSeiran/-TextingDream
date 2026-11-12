"""Verify weather / roads readiness against the default Terragenesis product."""
from app import tg_weather_roads
from app.paths import ROOT


def test_inspect_default_product():
    info = tg_weather_roads.inspect_product(ROOT)
    assert info['spacing_m'] == 4000.0
    assert 'elevation_m' in info['layers']
    assert info['sample_elevation_m'] is not None
    assert info['has_rivers'] is True


def test_weather_partial_ready():
    wx = tg_weather_roads.weather_readiness(ROOT)
    assert wx['can_run_with_story_climate'] is True
    assert wx['elevation_from_product'] is True
    assert wx['planar_metres_as_lonlat'] is False
    assert wx['planar_metres_rejected_by_weather'] is True
    assert wx['status'] == 'partial'


def test_roads_not_wired_but_rivers_present():
    roads = tg_weather_roads.roads_readiness(ROOT)
    assert roads['status'] == 'not_wired'
    assert roads['product_has_rivers'] is True
    assert roads['package_adventure_routes_ok'] is True


def test_verify_bundle(monkeypatch):
    monkeypatch.setenv('TEXTILE_CIV_ATLAS', '0')
    report = tg_weather_roads.verify(ROOT)
    assert report['map_policy']['civ_atlas_enabled'] is False
    assert report['map_policy']['default_map_kind'] == 'world_map_product'
    assert report['verdict']['player_default_is_terragenesis'] is True
    assert report['weather']['planar_metres_rejected_by_weather'] is True
