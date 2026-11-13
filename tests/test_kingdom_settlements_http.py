"""Author HTTP closure from a published background to independent kingdom town content."""
from copy import deepcopy

import numpy as np

from app import towns
from app.service import Service
from app.storage import Store
from tests.test_background_http import author, create, request  # noqa: F401


def call(client, headers, method, path, body=None):
    response = client.request(method, '/api/inner/' + path, headers=headers, json=body)
    assert response.status_code == 200, response.text
    return response.json()


def background(client, headers):
    draft = create(client, headers)
    prefix = '/drafts/' + draft['id']
    for action in ('auto-select', 'simulate', 'generate'):
        body = {'expected_revision': draft['revision']}
        if action == 'auto-select':
            body['acknowledge_candidates'] = True
        draft = request(client, headers, 'POST', prefix + '/' + action, body)
    draft = request(client, headers, 'POST', prefix + '/confirm', {'expected_revision': draft['revision']})
    return request(client, headers, 'GET', '/backgrounds/' + draft['published']['version_id'])


def declared(template):
    # Test author explicitly declares unknown water/soil/materials; the map is not a preset.
    entry = towns.preset_entry('wet_valley', 'author-declaration').model_dump(mode='json')
    for key in ('story_revision', 'seed', 'site', 'site_location_id', 'region', 'map', 'background'):
        entry[key] = deepcopy(template[key])
    for key, value in template['terrain'].items():
        if value is not None or key == 'coordinates':
            entry['terrain'][key] = value
    entry['bindings'] = []
    entry['founded_period'] = template['founded_period']
    entry['notes'] = 'Author-declared test assumptions for soil and supply; not measured map facts.'
    return entry


def test_background_civilization_to_towns_routes_publish_and_restart(author, tmp_path):  # noqa: F811
    client, headers, service, registry = author
    bundle = registry.bundle
    shape = bundle.grids['environment']['shape_zx']
    for name, value, unit in [('temperature_c', 16., 'degC'), ('precipitation_mm_yr', 1100., 'mm/year')]:
        bundle.specs['environment'][name] = {'shape': shape, 'dtype': 'float64', 'queryable': True, 'unit': unit}
        bundle.arrays['environment.' + name] = np.full(shape, value)
    document = background(client, headers)
    version = document['version_id']
    country = document['simulation']['kingdoms'][0]['id']
    base = 'world-package/backgrounds/' + version
    for path in (base + '/settlements', base + '/kingdom-versions', 'settlement-plans/unknown'):
        assert client.get('/api/inner/' + path).status_code == 403
    plan = call(client, headers, 'POST', base + '/settlements?polity_id=' + country,
                {'count': 2, 'seed': 'author-network', 'min_distance_m': 1000.})
    assert len(plan['sites']) == 2
    assert all(s['observations']['temperature_c'] == 16. for s in plan['sites'])
    assert call(client, headers, 'POST', base + '/settlements?polity_id=' + country,
                {'count': 2, 'seed': 'author-network', 'min_distance_m': 1000.}) == plan
    prefix = 'settlement-plans/' + plan['id']
    refused = client.post('/api/inner/' + prefix + '/publish', headers=headers,
                          json={'expected_revision': plan['revision']})
    assert refused.status_code == 400
    for site in plan['sites']:
        site_path = prefix + '/sites/' + site['id']
        inputs = call(client, headers, 'GET', site_path + '/town-input')
        assert inputs['background_context']['civilization']['year'] == document['background_year']
        assert inputs['template']['terrain']['soil_fertility'] is None
        entry = declared(inputs['template'])
        forged = deepcopy(entry)
        forged['terrain']['temperature_c'] += 1
        response = client.post('/api/inner/' + site_path + '/town', headers=headers,
                               json={'input': forged, 'expected_revision': plan['revision']})
        assert response.status_code == 400
        assert len(service.towns.list_drafts()) == len(plan['towns'])
        response = call(client, headers, 'POST', site_path + '/town',
                        {'input': entry, 'expected_revision': plan['revision']})
        plan, draft = response['plan'], response['draft']
        assert draft['input']['background']['version_id'] == version
        assert draft['input']['terrain']['coordinates'] is None
        layout = call(client, headers, 'POST', 'towns/' + draft['id'] + '/layout', {})
        assert layout['source']['id'] == draft['id']
        published = call(client, headers, 'POST', 'towns/' + draft['id'] + '/publish',
                         {'expected_revision': draft['revision']})
        assert published['version']['snapshot']['input']['background']['site_id'] == site['id']
    output = call(client, headers, 'POST', prefix + '/publish', {'expected_revision': plan['revision']})
    content = output['version']
    assert len(content['town_versions']) == 2
    assert content['background_context']['version_id'] == version
    assert content['can_start'] is False
    assert all(r['status'] == 'planned' for r in content['plan']['roads'])
    assert call(client, headers, 'GET', base + '/kingdom-versions') == [content]
    assert call(client, headers, 'GET', 'kingdom-versions/' + content['id']) == content
    restarted = Service(Store(tmp_path / 'runtime.sqlite3'), service.runtime.root)
    assert restarted.kingdoms.get_version(content['id']) == content
    assert restarted.world_package.backgrounds.get_version(version) == document
    assert restarted.store.get('pointer', 'package') is None
    assert call(client, headers, 'GET', prefix)['status'] == 'published'


def test_request_bounds_source_drift_and_direct_town_validation(author):  # noqa: F811
    client, headers, service, registry = author
    document = background(client, headers)
    base = 'world-package/backgrounds/' + document['version_id']
    country = document['simulation']['kingdoms'][0]['id']
    for body in ({'count': True}, {'count': 25}, {'count': 1, 'extra': 'no'}, {'seed': '../escape'}):
        response = client.post('/api/inner/' + base + '/settlements?polity_id=' + country,
                               headers=headers, json=body)
        assert response.status_code == 422
    plan = call(client, headers, 'POST', base + '/settlements?polity_id=' + country, {'count': 1})
    prefix = 'settlement-plans/' + plan['id']
    site_path = prefix + '/sites/' + plan['sites'][0]['id']
    entry = declared(call(client, headers, 'GET', site_path + '/town-input')['template'])
    entry['background']['context']['background_year'] += 1
    response = client.post('/api/inner/towns', headers=headers, json={'input': entry})
    assert response.status_code == 400
    assert service.towns.list_drafts() == []
    registry.bundle.changed = True
    response = client.get('/api/inner/' + site_path + '/town-input', headers=headers)
    assert response.status_code == 400
    assert service.kingdoms.get(plan['id']) == plan
