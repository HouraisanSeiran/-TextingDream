"""Kingdom planning uses fixed background versions and existing single-town rules."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from app.kingdom_settlements import KingdomSettlements, _route
from app import towns
from app.town_schema import DraftRequest, TownInput
from tests.test_background_package import factory, generated  # noqa: F401


@pytest.fixture
def kingdom(factory):  # noqa: F811
    pipe, draft, _, _ = factory(count=1)
    draft = generated(pipe, draft)
    draft = pipe.confirm(draft['id'], draft['revision'])
    document = pipe.get_version(draft['published']['version_id'])
    pipe.service.world_package.backgrounds = pipe
    planner = KingdomSettlements(pipe.service)
    pipe.service.kingdoms = planner
    country = document['simulation']['kingdoms'][0]['id']
    return planner, document['version_id'], country, pipe


def filled_input(planner, plan, site):
    template = planner.site_input(plan['id'], site['id'])['template']
    declared = towns.preset_entry('wet_valley', 'declared-water-soil').model_dump(mode='json')
    declared['bindings'] = []
    for key, value in template['terrain'].items():
        if value is not None or key == 'coordinates':
            declared['terrain'][key] = value
    for key in ('story_revision', 'seed', 'site', 'site_location_id', 'region', 'map', 'background'):
        declared[key] = template[key]
    return declared


def test_fixed_territory_sites_and_deterministic_land_routes(kingdom):
    planner, version, country, pipe = kingdom
    request = {'count': 3, 'seed': 'network-1', 'min_distance_m': 1000.}
    plan = planner.generate(version, country, request)
    assert planner.generate(version, country, request) == plan
    context = pipe.town_context(version, country)
    spans = context['polity']['geometry']['spans']
    land = {(z, x) for z, x0, x1 in spans for x in range(x0, x1)}
    assert plan['sites'][0]['province_id'] == context['polity']['capital_region_id']
    assert all(tuple(site['cell_zx']) in land for site in plan['sites'])
    assert len(plan['sites']) == 3
    for road in plan['roads']:
        assert road['status'] == 'planned'
        assert all(tuple(cell) in land for cell in road['cells_zx'])
        assert all(abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1
                   for a, b in zip(road['cells_zx'], road['cells_zx'][1:]))
    assert planner.list(version)[0] == plan
    assert pipe.service.store.get('pointer', 'package') is None


def test_site_template_preserves_unknowns_and_rejects_forged_observations(kingdom):
    planner, version, country, _ = kingdom
    plan = planner.generate(version, country, {'count': 1})
    site = plan['sites'][0]
    template = planner.site_input(plan['id'], site['id'])
    assert template['template']['terrain']['precipitation_mm'] is None
    assert 'terrain.precipitation_mm' in template['required_fields']
    with pytest.raises(ValueError):
        TownInput.model_validate(template['template'])
    entry = filled_input(planner, plan, site)
    planner.validate_entry(TownInput.model_validate(entry).model_dump(mode='json'))
    forged = deepcopy(entry)
    forged['terrain']['elevation_m'] += 1
    with pytest.raises(ValueError, match='冻结地图观测'):
        planner.create_town(plan['id'], site['id'], forged, plan['revision'])
    forged = deepcopy(entry)
    forged['terrain']['coordinates'] = [1., 1.]
    with pytest.raises(ValueError, match='米制坐标'):
        planner.validate_entry(forged)
    assert planner.get(plan['id']) == plan
    assert planner.service.towns.list_drafts() == []


def test_background_binding_and_direct_town_endpoint_cannot_bypass_pin(kingdom):
    planner, version, country, _ = kingdom
    plan = planner.generate(version, country, {'count': 1})
    site = plan['sites'][0]
    entry = filled_input(planner, plan, site)
    forged = deepcopy(entry)
    forged['background']['context']['background_year'] += 1
    with pytest.raises(ValueError, match='固定上下文不匹配'):
        planner.service.towns.create(DraftRequest(input=forged))
    entry['bindings'] = [{'id': 'not_adopted', 'kind': 'element', 'version': '1', 'summary': 'not in world'}]
    with pytest.raises(ValueError, match='固定背景采用清单'):
        planner.create_town(plan['id'], site['id'], entry, 0)
    assert planner.service.towns.list_drafts() == []


def test_publish_embeds_real_town_versions_and_reopens_without_store_index(kingdom):
    planner, version, country, pipe = kingdom
    plan = planner.generate(version, country, {'count': 2})
    with pytest.raises(ValueError, match='生成并发布城镇'):
        planner.publish(plan['id'], plan['revision'])
    for site in plan['sites']:
        result = planner.create_town(plan['id'], site['id'], filled_input(planner, plan, site), plan['revision'])
        plan = result['plan']
        draft = result['draft']
        planner.service.towns.publish(draft['id'], draft['revision'])
    published = planner.publish(plan['id'], plan['revision'])
    document = published['version']
    assert document['can_start'] is False
    assert len(document['town_versions']) == 2
    assert document['background_context']['version_id'] == version
    for row in document['town_versions']:
        assert row['version']['snapshot']['input']['background']['version_id'] == version
        assert row['version']['snapshot']['input']['terrain']['coordinates'] is None
    with pipe.service.store.transact() as db:
        db.execute('DELETE FROM documents WHERE kind=?', ('kingdom_settlement_version',))
    reopened = KingdomSettlements(pipe.service)
    assert reopened.get_version(document['id']) == document
    assert reopened.versions(version) == [document]
    assert reopened.publish(plan['id'], published['plan']['revision']) == published
    paths = list(Path(pipe.service.runtime.library).glob('背景_bgv_*/kingdoms/*.json'))
    serialized = json.loads(paths[0].read_text(encoding='utf-8'))
    assert serialized['id'] == document['id']


def test_source_change_and_stale_plan_rejected(kingdom):
    planner, version, country, pipe = kingdom
    plan = planner.generate(version, country, {'count': 1})
    site = plan['sites'][0]
    entry = filled_input(planner, plan, site)
    with pytest.raises(ValueError, match='规划已更新'):
        planner.create_town(plan['id'], site['id'], entry, 4)
    pipe.registry.bundle.changed = True
    with pytest.raises(ValueError, match='changed'):
        planner.site_input(plan['id'], site['id'])
    with pytest.raises(ValueError, match='changed'):
        planner.generate(version, country, {'count': 1})
    assert planner.service.towns.list_drafts() == []


def test_route_avoids_sea_and_missing_elevation():
    import numpy as np
    elevation = np.zeros((4, 6))
    traversable = np.ones_like(elevation, dtype=bool)
    traversable[1:3, 2] = False
    route = _route([1, 0], [1, 5], traversable, elevation, 1000.)
    assert route and all(traversable[tuple(cell)] for cell in route)
    traversable[:, 2] = False
    assert _route([1, 0], [1, 5], traversable, elevation, 1000.) is None


def test_disconnected_islands_do_not_become_roads(kingdom, monkeypatch):
    planner, version, country, pipe = kingdom
    original = pipe.town_context
    context = original(version, country)
    status = pipe.registry.bundle.arrays['terrain.status']
    from app.background_geography import _spans
    from app.terrain_source import LAND
    context['polity']['geometry']['spans'] = _spans(status == LAND)
    context['polity']['region_ids'] = [row['id'] for row in
                                     pipe.get_version(version)['simulation']['chronicle']['regions']]
    monkeypatch.setattr(pipe, 'town_context', lambda *args: deepcopy(context))
    plan = planner.generate(version, country, {'count': 2, 'seed': 'islands-test'})
    assert plan['sites'][0]['component'] != plan['sites'][1]['component']
    assert plan['roads'] == []
    assert plan['disconnected'][0]['reason'] == 'separate_land_component'


def test_native_climate_grid_complete_months_and_units(kingdom):
    import numpy as np
    planner, version, country, pipe = kingdom
    bundle = pipe.registry.bundle
    native_grid = {'shape_zx': [2, 4], 'first_xz_m': [0., 0.], 'spacing_m': 2000., 'semantics': 'cell-centre'}
    bundle.grids['climate'] = native_grid
    for name, value, unit in (('monthly_temperature_c', 12., 'degC'),
                              ('monthly_precipitation_mm', 30., 'mm')):
        bundle.specs['climate'][name] = {'shape': [12, 2, 4], 'dtype': 'float64',
                                       'queryable': True, 'unit': unit}
        bundle.arrays['climate.' + name] = np.full((12, 2, 4), value)
    plan = planner.generate(version, country, {'count': 1, 'seed': 'climate-known'})
    observations = plan['sites'][0]['observations']
    assert observations['temperature_c'] == 12.
    assert observations['precipitation_mm'] == 360.
    assert observations['climate_sources']['temperature_c']['native_grid'] == native_grid
    bundle.specs['climate']['monthly_temperature_c']['unit'] = 'K'
    bundle.arrays['climate.monthly_precipitation_mm'][3] = np.nan
    unknown = planner.generate(version, country, {'count': 1, 'seed': 'climate-unknown'})
    assert unknown['sites'][0]['observations']['temperature_c'] is None
    assert unknown['sites'][0]['observations']['precipitation_mm'] is None
