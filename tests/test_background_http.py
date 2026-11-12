"""Full author HTTP flow, with synthetic frozen data and a temporary encyclopedia."""
from copy import deepcopy

from fastapi.testclient import TestClient
import pytest

from app.storage import Store
from app.service import Service
from app.web import create_app
from tests.test_background_geography import FrozenBundle
from tests.test_world_package_pipeline import build_library, SETTING


class Registry:
    def __init__(self):
        self.bundle = FrozenBundle()

    def list(self):
        return {'bundles': [{'id': self.bundle.id, 'title': 'Frozen fixture', 'status': 'fixture'}]}

    def get(self, bundle_id):
        if bundle_id != self.bundle.id:
            raise ValueError('Unknown bundle')
        self.bundle.check_unchanged()
        return self.bundle


@pytest.fixture
def author(tmp_path, monkeypatch):
    db = tmp_path / 'encyclopedia.sqlite3'
    build_library(db)
    monkeypatch.setenv('TEXTILEDREAM_ENCYCLOPEDIA_DB', str(db))
    monkeypatch.setenv('TEXTILEDREAM_ENCYCLOPEDIA_ROOTS', str(tmp_path))
    monkeypatch.setenv('TEXTILE_CIV_ATLAS', '0')
    app = create_app(tmp_path / 'runtime.sqlite3')
    service = app.state.service
    registry = Registry()
    service.world_package.backgrounds.registry = registry
    service.provider.configure({'offline': True})
    with TestClient(app) as client:
        headers = {'X-TextileDream-Token': client.get('/api/bootstrap').json()['token']}
        yield client, headers, service, registry


def request(client, headers, method, path, data=None):
    response = client.request(method, '/api/inner/world-package' + path,
                              headers=headers, json=data)
    assert response.status_code == 200, response.text
    return response.json()


def create(client, headers):
    return request(client, headers, 'POST', '/propose', {
        'target': 'background', 'bundle_id': 'fixture-world', 'title': 'Fixture background',
        'requirements': 'Create background only.', 'setting': deepcopy(SETTING),
        'config': {'seed': 2, 'start_year': 0, 'end_year': 2, 'block_cells': 4,
                   'min_land_cells': 1, 'max_polities': 2, 'found_period': 1,
                   'min_capital_hops': 1, 'war_per_mille': 0}, 'year': 1})


def test_author_flow_publishes_without_playable_entities_and_reloads(author, tmp_path):
    client, headers, service, registry = author
    for path in ('/sources', '/backgrounds', '/drafts'):
        assert client.get('/api/inner/world-package' + path).status_code == 403
    sources = request(client, headers, 'GET', '/sources')
    assert sources['bundles'][0]['id'] == 'fixture-world'
    assert sources['defaults']['seed'] == 20261112
    original_pointer = service.store.get('pointer', 'package')
    draft = create(client, headers)
    prefix = '/drafts/' + draft['id']
    for action in ('auto-select', 'simulate', 'generate'):
        body = {'expected_revision': draft['revision']}
        if action == 'auto-select':
            body['acknowledge_candidates'] = True
        draft = request(client, headers, 'POST', prefix + '/' + action, body)
    assert draft['content']['overview']
    assert draft['simulation']['background_year'] == 1
    draft = request(client, headers, 'PUT', prefix, {
        'expected_revision': draft['revision'], 'content': draft['content'],
        'approved_history_ids': []})
    published = request(client, headers, 'POST', prefix + '/confirm', {
        'expected_revision': draft['revision']})
    version_id = published['published']['version_id']
    version = request(client, headers, 'GET', '/backgrounds/' + version_id)
    assert version['can_start'] is False
    assert 'characters' not in version and 'events' not in version
    folder = service.runtime.library / version['folder']
    assert (folder / 'background.json').is_file()
    assert (folder / '总概.md').is_file()
    assert not (folder / 'story.json').exists()
    kingdom_id = version['simulation']['kingdoms'][0]['id']
    located = request(client, headers, 'GET', '/backgrounds/' + version_id + '/town-context?polity_id=' + kingdom_id)
    assert located['environment_query']['expected_source'] == version['source']
    assert located['environment_query']['point']['path'].endswith('/fixture-world/point')
    assert located['historical_constraints']['province_locations']
    assert service.store.get('pointer', 'package') == original_pointer
    packages = client.get('/api/inner/packages', headers=headers).json()
    entry = next(p for p in packages if p.get('version_id') == version_id)
    assert entry['kind'] == 'background' and not entry['can_start']
    response = client.post('/api/inner/packages/' + entry['folder'] + '/activate', headers=headers)
    assert response.status_code == 400
    kingdoms = version['simulation']['kingdoms']
    assert kingdoms
    context = request(client, headers, 'GET', '/backgrounds/' + version_id +
                      '/town-context?polity_id=' + str(kingdoms[0]['id']))
    assert context['version_id'] == version_id
    assert not context['roads_generated'] and not context['settlements_generated']
    territories = request(client, headers, 'GET', '/backgrounds/' + version_id + '/territories')
    assert territories['kingdoms'] == kingdoms
    restarted = Service(Store(tmp_path / 'runtime.sqlite3'), service.runtime.root)
    assert restarted.world_package.backgrounds.get_version(version_id) == version
    revised = request(client, headers, 'POST', '/backgrounds/' + version_id + '/revise')
    assert revised['parent_version'] == version_id
    assert revised['id'] != draft['id']
    assert revised['revision'] == 1 and revised['status'] == 'draft'
    assert service.world_package.backgrounds.get_version(version_id) == version


def test_background_revisions_invalid_inputs_and_source_change(author):
    client, headers, service, registry = author
    draft = create(client, headers)
    prefix = '/drafts/' + draft['id']
    bad = client.put('/api/inner/world-package' + prefix + '/configure', headers=headers,
                     json={'expected_revision': 0, 'year': 1})
    assert bad.status_code == 400
    assert service.world_package.get(draft['id']) == draft
    bad = client.post('/api/inner/world-package' + prefix + '/auto-select', headers=headers,
                      json={'expected_revision': 1, 'acknowledge_candidates': False})
    assert bad.status_code == 400
    bad = client.put('/api/inner/world-package' + prefix + '/configure', headers=headers,
                     json={'expected_revision': 1, 'polity_preferences': {}})
    assert bad.status_code == 422
    registry.bundle.changed = True
    response = client.get('/api/inner/world-package' + prefix + '/freshness', headers=headers)
    assert response.status_code == 400
