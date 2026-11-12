"""Author climate HTTP projection over a real saved, source-bound mechanism product."""
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
import pytest

pytest.importorskip('fastapi')
from fastapi.testclient import TestClient  # noqa: E402

from app.web import create_app  # noqa: E402
from app.world_gen import web_jobs  # noqa: E402
from app.world_gen.world_climate_adapter import _climate_module  # noqa: E402

BASE = '/api/inner/worldgen/climate/'


@pytest.fixture(scope='module')
def products(tmp_path_factory):
    root = tmp_path_factory.mktemp('climate-http')
    artifacts = root / 'artifacts'
    artifacts.mkdir()
    producer_python = Path(__file__).resolve().parents[2] / '山川形意Terragenesis/runtime/venv/Scripts/python.exe'
    # The web venv intentionally has no Numba. Prepare the real tiny product
    # with the existing producer interpreter, then query only from the web venv.
    code = ('import sys; from pathlib import Path; sys.path.insert(0, "tests"); '
            'from test_world_climate_adapter import create_saved_products; '
            'create_saved_products(Path(sys.argv[1]))')
    subprocess.run([str(producer_python), '-B', '-X', 'utf8', '-c', code, str(artifacts)],
                   cwd=Path(__file__).resolve().parents[1], check=True, capture_output=True, text=True)
    source = json.loads((artifacts/'world/manifest.json').read_text(encoding='utf-8'))
    climate = json.loads((artifacts/'climate/manifest.json').read_text(encoding='utf-8'))
    return root, artifacts, source, climate


@pytest.fixture
def client(products, tmp_path):
    _, artifacts, source, climate = products
    app = create_app(tmp_path/'climate.sqlite3')
    app.state.service.provider.configure({'offline': True})
    app.state.worldgen = web_jobs.WorldGenManager(tmp_path, artifacts=artifacts)
    body = dict(source_map='world', climate_product='climate',
                expected_source_identity=source['identity'], expected_climate_identity=climate['identity'],
                fields=['monthly_temperature_c', 'monthly_precipitation_mm',
                        'monthly_current_x_m_s', 'cover_fraction'], months=[7, 1])
    with TestClient(app) as connection:
        connection.headers['X-TextileDream-Token'] = connection.get('/api/bootstrap').json()['token']
        yield app, connection, body


def test_author_token_guard_and_exact_saved_month_window_point_json(client, products, monkeypatch):
    _, connection, body = client
    _, artifacts, _, _ = products
    before = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in artifacts.rglob('*') if path.is_file()}
    climate = _climate_module()
    def forbidden(*args, **kwargs):
        raise AssertionError('HTTP climate query must not generate or connect')
    monkeypatch.setattr(climate, 'compute_climate', forbidden)
    monkeypatch.setattr(climate, 'prepare_climate', forbidden)
    import socket
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    response = connection.post(BASE+'query', json=dict(body, window=[1, 2, 5, 6]),
                               headers={'X-TextileDream-Token': 'wrong'})
    assert response.status_code == 403
    response = connection.post(BASE+'query', json=dict(body, window=[1, 2, 5, 6]))
    assert response.status_code == 200, response.text
    result = response.json()
    temperature = np.load(artifacts/'climate/monthly_temperature_c.npy')
    np.testing.assert_array_equal(result['arrays']['monthly_temperature_c'], temperature[[6, 0], 1:5, 2:6])
    assert result['months'] == [7, 1]
    assert result['grid']['first_xz_m'] == [20000., 10000.]
    assert result['fields']['monthly_precipitation_mm']['units'] == 'mm/month'
    assert result['arrays']['monthly_current_x_m_s'][0][1][0] is None  # land [2,2]
    assert isinstance(result['arrays']['monthly_current_x_m_s'][0][0][0], float)
    point = connection.post(BASE+'point', json=dict(body, x_m=20000., z_m=30000.))
    assert point.status_code == 200, point.text
    point = point.json()
    assert point['cell_zx'] == [3, 2]
    np.testing.assert_array_equal(point['arrays']['monthly_temperature_c'], temperature[[6, 0], 3, 2])
    assert point['arrays']['monthly_current_x_m_s'] == [None, None]
    assert point['arrays']['cover_fraction'] == pytest.approx(.4)
    assert connection.post(BASE+'point', json=dict(body, x_m=-1., z_m=0.)).status_code == 422
    after = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
             for path in artifacts.rglob('*') if path.is_file()}
    assert after == before


@pytest.mark.parametrize('changes', [
    dict(source_map='../world'), dict(source_map='C:/world'), dict(source_map='/world'),
    dict(climate_product='..\\climate'), dict(climate_product='C:\\climate'),
    dict(fields=['unknown_field']), dict(months=[0]), dict(months=[True]),
    dict(window=[0, 0, 0, 1]), dict(window=[0, 0, 100000, 100000]),
    dict(window=[0, 0, 7, 6]), dict(unrecognized=True),
    dict(expected_source_identity='0'*64), dict(expected_climate_identity='0'*64),
])
def test_rejects_escaping_paths_unknown_inputs_source_mismatch_and_bad_windows(client, changes):
    _, connection, body = client
    payload = dict(body, window=[0, 0, 3, 3])
    payload.update(changes)
    response = connection.post(BASE+'query', json=payload)
    assert response.status_code == 422, response.text


def test_missing_product_is_meaningful_404_and_candidate_is_rejected(client, products):
    _, connection, body = client
    response = connection.post(BASE+'query', json=dict(body, source_map='absent', window=[0, 0, 2, 2]))
    assert response.status_code == 404 and 'manifest is missing' in response.json()['detail']
    _, artifacts, _, manifest = products
    path = artifacts/'climate/manifest.json'
    original = path.read_bytes()
    try:
        manifest = dict(manifest, status='candidate-unconverged')
        manifest['manifest_identity'] = _climate_module()._manifest_hash(
            {k: v for k, v in manifest.items() if k != 'manifest_identity'})
        path.write_text(json.dumps(manifest), encoding='utf-8')
        response = connection.post(BASE+'query', json=dict(body, window=[0, 0, 2, 2]))
        assert response.status_code == 422 and 'not converged' in response.json()['detail']
    finally:
        path.write_bytes(original)
