"""World generation page: parameter validation, GPU gate, single-job lock, memory gate, job state flow (fake child processes)."""
import sys
import time

import pytest

pytest.importorskip('fastapi')   # the Terragenesis venv (numba / torch) has no web stack
from fastapi.testclient import TestClient  # noqa: E402

from app.web import create_app
from app.world_gen import estimates as est, web_jobs as wj

GIB = 2 ** 30
GPU_OK = (True, dict(cuda_available=True, cuda_free_mib=7000, cuda_total_mib=8191, name='Fake GPU'))
GPU_NONE = (False, dict(cuda_available=False, torch='2.9.1', reason='torch.cuda.is_available() is False'))


def fake_stages(script='print("ok")', gpu_stage=False, summary=None):
    def build(job):
        st = [wj.Stage('skeleton', 'fake skeleton', [sys.executable, '-c', script])]
        if job['params']['use_gpu'] or gpu_stage:
            st.append(wj.Stage('td', 'fake td', [sys.executable, '-c', 'print("td")'], gpu=True))
        st.append(wj.Stage('summary', 'fake summary', fn=summary or (lambda j: dict(ok=True, nan=float('nan')))))
        return st
    return build


def make_mgr(tmp_path, *, gpu=GPU_OK, memory=8 * GIB, others=(), stages=None):
    return wj.WorldGenManager(tmp_path, artifacts=tmp_path / 'artifacts', gpu_probe=lambda: gpu, memory=lambda: memory,
                              gpu_jobs=lambda: list(others), stage_builder=stages or fake_stages(), gpu_sampler=lambda: 1000)


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path / 'wg.sqlite3')
    app.state.service.provider.configure({'offline': True})
    with TestClient(app) as c:
        c.headers['X-TextileDream-Token'] = c.get('/api/bootstrap').json()['token']
        yield app, c


def wait(c, jid, timeout=30):
    end = time.time() + timeout
    while time.time() < end:
        j = c.get(f'/api/inner/worldgen/jobs/{jid}').json()
        if j['status'] in wj.FINISHED:
            return j
        time.sleep(0.1)
    raise AssertionError('job did not finish')


def test_token_required(client, tmp_path):
    app, c = client
    app.state.worldgen = make_mgr(tmp_path)
    r = c.get('/api/inner/worldgen/options', headers={'X-TextileDream-Token': 'wrong'})
    assert r.status_code == 403


def test_options_defaults_and_gpu_reason(client, tmp_path):
    app, c = client
    app.state.worldgen = make_mgr(tmp_path, gpu=GPU_NONE)
    o = c.get('/api/inner/worldgen/options').json()
    assert o['defaults'] == dict(world_type='multi-continent', size_km=1600, ocean_fraction=0.6, mountain_area=0.25,
                                 seed=20260903, use_gpu=False)
    assert [s['km'] for s in o['sizes']] == [1600, 5000, 10000] and o['sizes'][2]['slow']
    assert o['ranges']['mountain_area'] == [0.2, 0.3]
    assert o['gpu']['usable'] is False and 'CUDA' in o['gpu']['reason']
    e = o['estimates']['1600']
    assert e['cpu']['basis'] == 'extrapolated' and e['gpu']['basis'] == 'extrapolated'
    assert {s['stage'] for s in e['gpu']['stages']} >= {'skeleton', 'fast', 'td', 'render'}


@pytest.mark.parametrize('body', [
    dict(size_km=3000), dict(ocean_fraction=0.3), dict(ocean_fraction=0.9), dict(mountain_area=0.35), dict(mountain_area=0.1),
    dict(seed=-1), dict(seed='1'), dict(world_type='flat'), dict(use_gpu='yes'), dict(extra=1)])
def test_params_validated(client, tmp_path, body):
    app, c = client
    app.state.worldgen = make_mgr(tmp_path)
    assert c.post('/api/inner/worldgen/jobs', json=body).status_code == 422
    assert app.state.worldgen.list() == []


def test_gpu_unavailable_rejects_gpu_option(client, tmp_path):
    app, c = client
    app.state.worldgen = make_mgr(tmp_path, gpu=GPU_NONE)
    r = c.post('/api/inner/worldgen/jobs', json=dict(use_gpu=True))
    assert r.status_code == 409 and '显卡' in r.json()['detail']
    low = (False, dict(cuda_available=True, cuda_free_mib=2000, cuda_total_mib=8191, name='Fake GPU'))
    app.state.worldgen = make_mgr(tmp_path, gpu=low)
    r = c.post('/api/inner/worldgen/jobs', json=dict(use_gpu=True))
    assert r.status_code == 409 and '4096' in r.json()['detail']
    app.state.worldgen = make_mgr(tmp_path, others=['pid 1: python td_coarse_ridges.py'])
    r = c.post('/api/inner/worldgen/jobs', json=dict(use_gpu=True))
    assert r.status_code == 409 and '别的显卡任务' in r.json()['detail']
    assert app.state.worldgen.list() == []
    # CPU-only job is still allowed without a GPU
    app.state.worldgen = make_mgr(tmp_path, gpu=GPU_NONE)
    r = c.post('/api/inner/worldgen/jobs', json=dict(use_gpu=False))
    assert r.status_code == 200
    assert wait(c, r.json()['id'])['status'] == 'succeeded'


def test_memory_gate(client, tmp_path):
    app, c = client
    app.state.worldgen = make_mgr(tmp_path, memory=int(1.5 * GIB))
    r = c.post('/api/inner/worldgen/jobs', json={})
    assert r.status_code == 409 and '可用内存' in r.json()['detail']
    assert wj.WorldGenManager.memory_gate_bytes(1600) >= 3200 * 2 ** 20
    assert wj.WorldGenManager.memory_gate_bytes(10000) > 2 * GIB


def test_single_job_and_cancel(client, tmp_path):
    app, c = client
    app.state.worldgen = make_mgr(tmp_path, stages=fake_stages('import time; print("start", flush=True); time.sleep(60)'))
    r = c.post('/api/inner/worldgen/jobs', json={})
    assert r.status_code == 200
    jid = r.json()['id']
    r2 = c.post('/api/inner/worldgen/jobs', json={})
    assert r2.status_code == 409 and '同一时间只允许一个' in r2.json()['detail']
    end = time.time() + 10
    while c.get(f'/api/inner/worldgen/jobs/{jid}').json()['stage'] != 'skeleton' and time.time() < end:
        time.sleep(0.05)
    t0 = time.time()
    assert c.post(f'/api/inner/worldgen/jobs/{jid}/cancel').status_code == 200
    j = wait(c, jid, 20)
    assert j['status'] == 'cancelled' and time.time() - t0 < 15
    assert j['stages'][0]['status'] == 'cancelled' and j['stages'][-1]['status'] == 'skipped'
    assert c.post(f'/api/inner/worldgen/jobs/{jid}/cancel').status_code == 409
    # lock released: a new job may start
    app.state.worldgen.stage_builder = fake_stages()
    r3 = c.post('/api/inner/worldgen/jobs', json={})
    assert r3.status_code == 200 and wait(c, r3.json()['id'])['status'] == 'succeeded'


def test_state_flow_success_and_failure(client, tmp_path):
    app, c = client
    app.state.worldgen = make_mgr(tmp_path)
    r = c.post('/api/inner/worldgen/jobs', json=dict(world_type='pangaea', use_gpu=True))
    assert r.status_code == 200 and r.json()['status'] in ('queued', 'running')
    jid = r.json()['id']
    assert wj.JOB_ID_RE.match(jid)
    j = wait(c, jid)
    assert j['status'] == 'succeeded' and j['stage'] is None
    assert [s['name'] for s in j['stages']] == ['skeleton', 'td', 'summary']
    assert all(s['status'] == 'succeeded' and s['seconds'] >= 0 for s in j['stages'])
    assert j['stages'][1]['gpu_monitor']['peak_mib'] == 1000
    assert j['result'] == dict(ok=True, nan=None)
    assert any('td' in line for line in j['log_tail'])
    assert j['paths_relative']['fast_dir'] == f'artifacts/fast-world/web-{jid}'
    assert j['paths_relative']['world_dir'] == f'artifacts/worlds/web-{jid}'
    assert c.get(f'/api/inner/worldgen/jobs/{jid}/preview/overview').status_code == 404
    assert c.get(f'/api/inner/worldgen/jobs/{jid}/preview/../../x').status_code == 404
    assert c.get('/api/inner/worldgen/jobs/nope').status_code == 404
    assert c.get('/api/inner/worldgen/jobs').json()[0]['id'] == jid
    # a failing stage stops the chain
    app.state.worldgen.stage_builder = fake_stages('import sys; sys.exit(3)')
    j = wait(c, c.post('/api/inner/worldgen/jobs', json={}).json()['id'])
    assert j['status'] == 'failed' and j['stages'][0]['returncode'] == 3 and j['stages'][1]['status'] == 'skipped'


def test_preview_served(client, tmp_path):
    app, c = client
    png = b'\x89PNG\r\n\x1a\nfake'

    def summary(job):
        from pathlib import Path
        d = Path(job['paths']['atlas_dir']); d.mkdir(parents=True, exist_ok=True)
        (d / 'simple-atlas.png').write_bytes(png)
        return {}
    app.state.worldgen = make_mgr(tmp_path, stages=fake_stages(summary=summary))
    j = wait(c, c.post('/api/inner/worldgen/jobs', json={}).json()['id'])
    assert j['previews'] == ['overview']
    r = c.get(f"/api/inner/worldgen/jobs/{j['id']}/preview/overview")
    assert r.status_code == 200 and r.content == png and r.headers['content-type'] == 'image/png'


def test_restart_marks_unfinished_interrupted(tmp_path):
    m = make_mgr(tmp_path)
    jid = '20261105-120000-abcd'
    job = dict(id=jid, status='running', created='x', owner_pid=999999999, paths=m._paths(jid), params={}, stages=[])
    m._save(job)
    m2 = make_mgr(tmp_path)
    assert m2.view(jid)['status'] == 'interrupted'


def test_default_stages_commands(tmp_path):
    m = make_mgr(tmp_path)
    job = dict(name='web-x', params=dict(world_type='pangaea', size_km=5000, ocean_fraction=0.6, mountain_area=0.22, seed=7,
                                         use_gpu=True), paths=m._paths('20261105-120000-abcd'))
    st = {s.name: s for s in m.default_stages(job)}
    assert list(st) == ['skeleton', 'islands', 'island-mountains', 'fast', 'render', 'details', 'final-render', 'td', 'compare', 'summary']
    assert '--record-history' in st['skeleton'].argv
    assert '--world-processes' in st['fast'].argv
    assert st['details'].gpu and '--use-gpu' in st['details'].argv
    sk = st['skeleton'].argv
    assert sk[sk.index('--ridges') + 1] == 'orogen' and sk[sk.index('--mountain-area') + 1] == '0.22'
    assert sk[sk.index('--cell-km') + 1] == '20'
    fa = st['fast'].argv
    assert 'web_island_stage.py' in fa[1] and fa[2]=='fast'
    assert '--input' in fa and st['island-mountains'].gpu
    assert '--use-gpu' in st['island-mountains'].argv
    td = st['td'].argv
    assert st['td'].gpu and td[td.index('--device') + 1] == 'cuda'
    assert td[td.index('--skip-ocean-km') + 1] == '120' and td[td.index('--steps') + 1] == '15'
    assert not st['fast'].gpu and m._env(False)['CUDA_VISIBLE_DEVICES'] == '-1'
    assert all('d8' not in ' '.join(s.argv or []).lower() for s in st.values())


def test_estimates_marked():
    assert est.fast_layer(1600)['basis'] == 'measured' and est.fast_layer(1600)['nodes'] == 640000
    assert est.fast_layer(5000)['cpu_seconds'] == 960.0
    assert est.td_coarse(5000, 'cuda')['basis'] == 'extrapolated'
    assert est.skeleton_cell_km(10000) == 20


def test_resume_reuses_completed_stages(client, tmp_path):
    app, c = client
    manager = make_mgr(tmp_path, stages=fake_stages('import sys; sys.exit(3)'))
    app.state.worldgen = manager
    first = wait(c, c.post('/api/inner/worldgen/jobs', json={}).json()['id'])
    assert first['status'] == 'failed'
    manager.stage_builder = fake_stages('print("resumed")')
    reply = c.post(f"/api/inner/worldgen/jobs/{first['id']}/continue")
    assert reply.status_code == 200
    resumed = wait(c, first['id'])
    assert resumed['status'] == 'succeeded'
    assert 'resumed' in '\n'.join(resumed['log_tail'])
