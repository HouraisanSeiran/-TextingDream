"""作者 API 的岛布局（island_layout）：old 是默认、完全不变；只有显式 clustered 才动 prepare argv。

upgrade 复用源岛、summary 读已存岛记录的 *实际* 布局与 config policy，都不按新 quality / size 重选；
use_gpu 与 defer / 候选密度的原有判断不受布局影响（本文件只验参数、argv、记录读取，不起真实生成）。
"""
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip('fastapi')   # Terragenesis venv（numba / torch）没有 web 栈
from fastapi.testclient import TestClient  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from app.web import create_app  # noqa: E402
from app.world_gen import web_jobs as wj  # noqa: E402

GIB = 2 ** 30
GPU_OK = (True, dict(cuda_available=True, cuda_free_mib=7000, cuda_total_mib=8191, name='Fake GPU'))
GPU_NONE = (False, dict(cuda_available=False, torch='2.9.1', reason='torch.cuda.is_available() is False'))
BIG = dict(width_km=10000, height_km=8000)

# 复用缓存测试的最小冻结 fast 产品夹具（与真实 world 层同布局：manifest.json + layers/*.npy）。
_spec = importlib.util.spec_from_file_location('island_layout_fast_fixture',
                                               Path(__file__).with_name('test_map_source_cache.py'))
_fixture = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fixture)


def fake_stages(script='print("ok")'):
    def build(job):
        return [wj.Stage('skeleton', 'fake skeleton', [sys.executable, '-c', script]),
                wj.Stage('summary', 'fake summary', fn=lambda j: dict(ok=True))]
    return build


def make_mgr(tmp_path, *, gpu=GPU_OK, memory=8 * GIB, stages=None):
    return wj.WorldGenManager(tmp_path, artifacts=tmp_path / 'artifacts', gpu_probe=lambda: gpu, memory=lambda: memory,
                              gpu_jobs=lambda: [], stage_builder=stages or fake_stages(), gpu_sampler=lambda: 1000)


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


def job_dict(m, *, params, jid='20261105-120000-abcd', name='web-layout'):
    base = dict(world_type='pangaea', size_km=1600, ocean_fraction=0.6, mountain_area=0.22, seed=7,
                use_gpu=False, quality='speed', pipeline='playable')
    base.update(params)
    w, h = wj.job_dims(base)
    base.setdefault('spacing_m', wj.requested_spacing_m(w, h, base['quality']))
    return dict(name=name, params=base, paths=m._paths(jid), stages=[])


def write_prepared(world_dir, *, layout=None, density=None, analysis_status='complete'):
    """写一份已冻结的岛准备记录（只用于读回布局 / 密度 / 分析状态）。"""
    d = Path(world_dir) / 'ocean-islands'
    d.mkdir(parents=True, exist_ok=True)
    record = dict(schema='x', analysis=dict(status=analysis_status, qualification='ok'), island_identity='b' * 64)
    if layout == 'clustered':
        record['island_layout'] = 'clustered'
        record['island_config'] = dict(layout_policy=wj.CLUSTERED_LAYOUT_POLICY)
    elif layout is not None:
        record['island_layout'] = layout
    if density is not None:
        record['island_density'] = density
    (d / 'prepared.json').write_text(json.dumps(record), encoding='utf-8')
    return record


def build_fast(tmp_path, jid, *, island_record=None):
    """artifacts/fast-world/web-<jid> 下一个可被 map_source 加载的冻结产品（summary 会真的读它）。"""
    product, manifest = _fixture.build_product(tmp_path, name='web-' + jid)
    # summarize 还会直接 mmap 根下的 elevation_m.npy / status.npy（与真实 fast 层一致）
    for name in ('elevation_m', 'status'):
        np.save(product / (name + '.npy'), np.load(product / 'layers' / (name + '.npy')))
    if island_record is not None:
        manifest['island_mountains'] = dict(record=island_record)
        _fixture._seal(manifest)
        (product / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    return product, manifest


def ready_source(c, jid):
    """把一份已成功的源任务补齐到 upgrade 可用的状态（只看 manifest / world-input / prepared）。"""
    j = wait(c, jid)
    assert j['status'] == 'succeeded'
    fast_dir = Path(j['paths']['fast_dir'])
    fast_dir.mkdir(parents=True, exist_ok=True)
    (fast_dir / 'manifest.json').write_text(json.dumps(dict(identity='a' * 64, grid=dict(spacing_m=10000.0))),
                                            encoding='utf-8')
    mountains = Path(j['paths']['world_dir']) / 'island-mountains'
    mountains.mkdir(parents=True, exist_ok=True)
    (mountains / 'world-input.json').write_text('{}', encoding='utf-8')
    return j


# ---------------------------------------------------------------- request validation
def test_request_defaults_to_old_and_accepts_clustered():
    assert wj.WorldGenRequest().island_layout == wj.DEFAULT_ISLAND_LAYOUT == 'old'
    assert wj.WorldGenRequest(island_layout='old').island_layout == 'old'
    assert wj.WorldGenRequest(island_layout='clustered').island_layout == 'clustered'
    # 与尺寸/档位无关：clustered 不因 world_type=archipelago 之类被隐式选中
    assert wj.WorldGenRequest(world_type='archipelago').island_layout == 'old'
    assert wj.ISLAND_LAYOUTS == ('old', 'clustered')


@pytest.mark.parametrize('layout', ['spiral', '', 'Clustered', 'cluster', 1, None, True])
def test_request_rejects_unknown_layout(layout):
    with pytest.raises(ValidationError):
        wj.WorldGenRequest(island_layout=layout)


def test_options_expose_layouts_without_touching_defaults(client, tmp_path):
    app, c = client
    app.state.worldgen = make_mgr(tmp_path)
    o = c.get('/api/inner/worldgen/options').json()
    assert [l['id'] for l in o['island_layouts']] == ['old', 'clustered']
    assert [l['default'] for l in o['island_layouts']] == [True, False]
    assert o['island_layouts'][0]['label'] and o['island_layouts'][1]['label']
    # 旧 defaults 字典形状不变（布局是并列的新清单，不混进 defaults）
    assert 'island_layout' not in o['defaults']
    assert o['defaults'] == dict(world_type='multi-continent', size_km=1600, ocean_fraction=0.6, mountain_area=0.25,
                                seed=20260903, use_gpu=False, quality='speed', pipeline='playable')
    notes = ' '.join(o['notes'])
    assert 'island_layout' in notes and 'clustered' in notes and 'old' in notes


# ---------------------------------------------------------------- prepare argv
def test_old_and_legacy_jobs_keep_the_historical_prepare_argv(tmp_path):
    m = make_mgr(tmp_path)
    old = {s.name: s for s in m.default_stages(job_dict(m, params=dict(BIG, island_layout='old')))}
    legacy = {s.name: s for s in m.default_stages(job_dict(m, params=dict(BIG)))}
    assert '--island-layout' not in old['islands'].argv
    assert '--island-layout' not in legacy['islands'].argv
    assert old['islands'].argv == legacy['islands'].argv          # 显式 old 与旧任务字节一致
    assert '聚类' not in old['islands'].label
    assert wj.island_layout(dict(island_layout='old')) is None
    assert wj.island_layout({}) is None                            # 旧任务没有这个字段


def test_clustered_adds_only_the_layout_flag(tmp_path):
    m = make_mgr(tmp_path)
    old = {s.name: s for s in m.default_stages(job_dict(m, params=dict(BIG)))}
    cl = {s.name: s for s in m.default_stages(job_dict(m, params=dict(BIG, island_layout='clustered')))}
    argv = cl['islands'].argv
    assert argv.count('--island-layout') == 1
    assert argv[argv.index('--island-layout') + 1] == 'clustered'
    assert argv[:-2] == old['islands'].argv                    # 只多这一对参数，其余完全一样
    assert '岛群聚类布局' in cl['islands'].label
    # 其余 stage 不因布局变化
    for name in ('skeleton', 'island-mountains', 'fast', 'render'):
        assert cl[name].argv == old[name].argv


def test_clustered_does_not_override_the_original_defer_and_density_rules(tmp_path):
    m = make_mgr(tmp_path)
    # 显式矩形 + speed + playable + CPU：延后分析与低候选密度是原流程决定的，clustered 不改它
    j = job_dict(m, params=dict(BIG, island_layout='clustered'))
    st = {s.name: s for s in m.default_stages(j)}
    assert '--defer-mountain-analysis' in st['islands'].argv
    assert st['islands'].argv[st['islands'].argv.index('--island-density') + 1] == 'low'
    assert wj.defer_island_analysis(j['params']) is True and wj.island_density(j['params']) == 'low'
    # use_gpu=true 的 clustered 任务不禁 GPU：岛内 TD 仍按原流程走 GPU
    gpu = job_dict(m, params=dict(BIG, use_gpu=True, island_layout='clustered'))
    gst = {s.name: s for s in m.default_stages(gpu)}
    assert gst['island-mountains'].gpu is True and '--use-gpu' in gst['island-mountains'].argv
    assert '--defer-mountain-analysis' not in gst['islands'].argv   # GPU 任务原本就不延后


def test_submit_records_the_requested_layout(client, tmp_path):
    app, c = client
    app.state.worldgen = make_mgr(tmp_path)
    j = c.post('/api/inner/worldgen/jobs', json=dict(island_layout='clustered')).json()
    assert j['params']['island_layout'] == 'clustered'
    assert wait(c, j['id'])['status'] == 'succeeded'
    assert c.post('/api/inner/worldgen/jobs', json={}).json()['params']['island_layout'] == 'old'
    n = len(app.state.worldgen.list())
    bad = c.post('/api/inner/worldgen/jobs', json=dict(island_layout='spiral'))
    assert bad.status_code == 422 and len(app.state.worldgen.list()) == n


# ---------------------------------------------------------------- upgrade 复用实际布局
def test_upgrade_keeps_the_frozen_layout_not_the_new_quality(client, tmp_path):
    app, c = client
    app.state.worldgen = make_mgr(tmp_path)
    j = c.post('/api/inner/worldgen/jobs', json=dict(island_layout='clustered')).json()
    ready_source(c, j['id'])
    write_prepared(j['paths']['world_dir'], layout='clustered', analysis_status='pending-analysis')
    up = c.post(f"/api/inner/worldgen/jobs/{j['id']}/upgrade", json=dict(quality='balanced'))
    assert up.status_code == 200, up.text
    u = up.json()
    assert u['params']['island_layout'] == 'clustered'
    assert 'islands' not in {s.name for s in app.state.worldgen.upgrade_stages(dict(u))}   # 不重跑 prepare


def test_upgrade_reads_the_layout_from_the_frozen_record(client, tmp_path):
    """源任务 params 没写布局（旧任务），但盘上的岛记录声明 clustered：upgrade 按记录保留 clustered。"""
    app, c = client
    app.state.worldgen = make_mgr(tmp_path)
    j = c.post('/api/inner/worldgen/jobs', json={}).json()
    ready_source(c, j['id'])
    app.state.worldgen._jobs[j['id']]['params'].pop('island_layout', None)
    write_prepared(j['paths']['world_dir'], layout='clustered')
    up = c.post(f"/api/inner/worldgen/jobs/{j['id']}/upgrade", json=dict(quality='balanced'))
    assert up.status_code == 200, up.text
    assert up.json()['params']['island_layout'] == 'clustered'


def test_upgrade_legacy_source_falls_back_to_old(client, tmp_path):
    """旧源既没 params 也没记录：落回 old，不凭空造 clustered。"""
    app, c = client
    app.state.worldgen = make_mgr(tmp_path)
    j = c.post('/api/inner/worldgen/jobs', json={}).json()
    ready_source(c, j['id'])
    app.state.worldgen._jobs[j['id']]['params'].pop('island_layout', None)
    write_prepared(j['paths']['world_dir'])
    up = c.post(f"/api/inner/worldgen/jobs/{j['id']}/upgrade", json=dict(quality='balanced'))
    assert up.status_code == 200, up.text
    assert up.json()['params']['island_layout'] == 'old'


def test_saved_layout_prefers_the_record_over_the_param():
    assert wj.saved_island_layout({'island_layout': 'clustered'}) == 'clustered'
    assert wj.saved_island_layout({}) == 'old'
    assert wj.saved_island_layout({'island_layout': 'bogus'}) == 'old'
    assert wj.saved_island_layout(None, {'island_config': {'layout_policy': wj.CLUSTERED_LAYOUT_POLICY}}) == 'clustered'
    assert wj.saved_island_layout({'island_config': {'layout_policy': 'absolute-slots-v1'}}) == 'old'
    # 记录胜过 params：upgrade 不按新请求重选
    assert wj.island_record_layout({'island_layout': 'old'}, {'island_layout': 'clustered'}) == 'clustered'
    assert wj.island_record_layout({'island_layout': 'clustered'}, None) == 'clustered'
    assert wj.island_record_layout({}, {}) == 'old'


# ---------------------------------------------------------------- summary 读实际记录
def test_summary_reports_the_saved_clustered_layout(tmp_path):
    m = make_mgr(tmp_path)
    jid = '20261105-120000-abcd'
    job = job_dict(m, jid=jid, params=dict(world_type='pangaea', quality='balanced', spacing_m=8000.0,
                                           skeleton_cell_km=40, fast_nodes=1000 * 800))
    build_fast(tmp_path, jid)
    write_prepared(job['paths']['world_dir'], layout='clustered', density='low', analysis_status='pending-analysis')
    out = wj.summarize(job)
    world = out['world']
    assert world['island_layout'] == 'clustered'
    assert world['island_layout_policy'] == wj.CLUSTERED_LAYOUT_POLICY
    assert world['island_layout_source'] == 'ocean-islands/prepared.json'
    assert world['island_layout_requested'] == 'old'      # 当前请求没要 clustered，但报告的是实际冻结的那个
    assert world['island_density'] == 'low' and world['island_analysis_status'] == 'pending-analysis'


def test_summary_falls_back_to_the_fast_manifest_record(tmp_path):
    """没有 prepared.json 时读 fast manifest 的岛记录：布局与 policy 同样以实际为准。"""
    m = make_mgr(tmp_path)
    jid = '20261105-120000-abcd'
    job = job_dict(m, jid=jid, params=dict(world_type='pangaea', quality='speed', spacing_m=8000.0,
                                           skeleton_cell_km=40, fast_nodes=1000 * 800))
    build_fast(tmp_path, jid, island_record=dict(island_layout='clustered', island_density='medium',
                                                 island_config=dict(layout_policy=wj.CLUSTERED_LAYOUT_POLICY),
                                                 analysis=dict(status='complete'), mountains=dict(status='prepared')))
    out = wj.summarize(job)
    world = out['world']
    assert world['island_layout'] == 'clustered'
    assert world['island_layout_policy'] == wj.CLUSTERED_LAYOUT_POLICY
    assert world['island_layout_source'] == 'fast manifest island_mountains.record'
    assert world['island_analysis_deferred'] is False


def test_summary_old_product_reports_old_and_no_policy(tmp_path):
    """旧产品没任何布局字段：报 old、policy 为 None，不编造 clustered。"""
    m = make_mgr(tmp_path)
    jid = '20261105-120000-abcd'
    job = job_dict(m, jid=jid, params=dict(world_type='pangaea', spacing_m=8000.0, skeleton_cell_km=40,
                                           fast_nodes=1000 * 800))
    build_fast(tmp_path, jid)
    out = wj.summarize(job)
    world = out['world']
    assert world['island_layout'] == 'old'
    assert world['island_layout_policy'] is None
    assert world['island_layout_source'] is None
