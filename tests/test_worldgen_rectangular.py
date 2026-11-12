"""矩形作者世界（width_km x height_km）：API 校验、档位/格距选择、骨架 argv、upgrade 继承、估算边界。

只跑参数、argv 与纯估算，不启动任何真实生成（子进程全是 fake）。重点交付 10000x8000 speed CPU：
40 km 骨架、可整除的 10000 m 格距、1000x800 网格 = 800000 节点（fast 岛栅格 1e6 预算内）。
"""
import sys
import time

import pytest

pytest.importorskip('fastapi')   # Terragenesis venv（numba / torch）没有 web 栈
from fastapi.testclient import TestClient  # noqa: E402

from app.web import create_app
from app.world_gen import estimates as est, web_jobs as wj

GIB = 2 ** 30
GPU_OK = (True, dict(cuda_available=True, cuda_free_mib=7000, cuda_total_mib=8191, name='Fake GPU'))
GPU_NONE = (False, dict(cuda_available=False, torch='2.9.1', reason='torch.cuda.is_available() is False'))
BIG = dict(width_km=10000, height_km=8000)


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


def job_dict(m, *, params, name='web-rect'):
    base = dict(world_type='pangaea', size_km=1600, ocean_fraction=0.6, mountain_area=0.22, seed=7,
                use_gpu=False, quality='speed', pipeline='playable')
    base.update(params)
    w, h = wj.job_dims(base)
    base.setdefault('spacing_m', wj.requested_spacing_m(w, h, base['quality']))
    return dict(name=name, params=base, paths=m._paths('20261105-120000-abcd'))


# ---------------------------------------------------------------- request validation
def test_request_rectangle_accepted_and_dims():
    req = wj.WorldGenRequest(**BIG)
    assert req.dims == (10000, 8000) and req.explicit_rect is True
    # 旧写法：只有 size_km，仍是正方形
    old = wj.WorldGenRequest(size_km=5000)
    assert old.dims == (5000, 5000) and old.explicit_rect is False
    # 显式两边相等也按显式矩形走（尺寸与档位都由自身决定，不查旧表）
    assert wj.WorldGenRequest(width_km=3000, height_km=3000).dims == (3000, 3000)


@pytest.mark.parametrize('body', [
    dict(width_km=10000),                                  # 只给一边
    dict(height_km=8000),
    dict(width_km=True, height_km=8000),                   # bool 不是整数
    dict(width_km=10000, height_km=False),
    dict(width_km=10000, height_km=8000.5),                # 非整数
    dict(width_km='10000', height_km='8000'),              # 字符串不隐式转换
    dict(width_km=99, height_km=8000),                     # 下界 100
    dict(width_km=10000, height_km=10001),                 # 上界 10000
    dict(width_km=0, height_km=0),
    dict(width_km=-5000, height_km=8000),
])
def test_request_rectangle_rejects_bad_sides(client, tmp_path, body):
    app, c = client
    app.state.worldgen = make_mgr(tmp_path)
    assert c.post('/api/inner/worldgen/jobs', json=body).status_code == 422
    assert app.state.worldgen.list() == []


def wait(c, jid, timeout=30):
    end = time.time() + timeout
    while time.time() < end:
        j = c.get(f'/api/inner/worldgen/jobs/{jid}').json()
        if j['status'] in wj.FINISHED:
            return j
        time.sleep(0.1)
    raise AssertionError('job did not finish')


def test_request_nan_inf_rejected_in_process():
    """NaN / inf 过不了 JSON 层，但模型本身也必须拒绝（本地调用走同一套校验）。"""
    from pydantic import ValidationError
    for bad in (float('nan'), float('inf'), float('-inf')):
        with pytest.raises(ValidationError):
            wj.WorldGenRequest(width_km=bad, height_km=8000)


def test_bounds_are_inclusive(client, tmp_path):
    app, c = client
    app.state.worldgen = make_mgr(tmp_path)
    for body in (dict(width_km=100, height_km=100), dict(width_km=1600, height_km=1200)):
        r = c.post('/api/inner/worldgen/jobs', json=body)
        assert r.status_code == 200, r.text
        j = r.json()
        assert (j['params']['width_km'], j['params']['height_km']) == (body['width_km'], body['height_km'])
        assert wait(c, j['id'])['status'] == 'succeeded'   # 跑完释放锁，才能提交下一个


# ---------------------------------------------------------------- size class / spacing
def test_size_class_uses_longest_side_and_never_keyerrors():
    assert wj.size_class(10000, 8000) == 10000
    assert wj.size_class(8000, 10000) == 10000
    assert wj.size_class(1600, 1200) == 1600
    assert wj.size_class(1200, 900) == 1600
    assert wj.size_class(2000, 100) == 1600        # <=2000 档
    assert wj.size_class(2001, 100) == 5000        # <=6000 档
    assert wj.size_class(6000, 100) == 5000
    assert wj.size_class(6001, 100) == 10000
    # 现有精度表分档：<=2000 / <=6000 / 其余，每个档位都能取到值（不是按 size 直接查表）
    for w, h in ((1600, 1200), (2500, 1200), (10000, 8000), (100, 100), (10000, 100)):
        for q in wj.QUALITIES:
            assert wj.requested_spacing_m(w, h, q) > 0


def test_big_rectangle_speed_spacing_divides_and_hits_node_budget():
    sp = wj.requested_spacing_m(10000, 8000, 'speed')
    assert sp == 10000.0                                  # 12000 不能整除，取能整除两边的最大整米值
    fl = est.fast_layer(10000, 8000, sp)
    assert fl['nodes'] == 1000 * 800 == 800000 <= wj.FAST_NODE_BUDGET
    # 真实网格不是方形重复：节点数就是 10000x8000 / sp^2
    assert fl['nodes'] == int(round(10000 * 1000 / sp)) * int(round(8000 * 1000 / sp))
    assert fl['nodes'] != int(round(10000 * 1000 / sp)) ** 2
    # 该格距同时整除两边的米制长度（fast_relief.grid_of 的整除前置条件）
    assert (10000 * 1000) % int(sp) == 0 and (8000 * 1000) % int(sp) == 0


@pytest.mark.parametrize('quality', ['speed', 'balanced', 'precise'])
def test_every_rectangle_spacing_divides_both_sides(quality):
    for w, h in ((10000, 8000), (1600, 1200), (5000, 3000), (2001, 1500), (1234, 1000), (6001, 6000)):
        sp = wj.requested_spacing_m(w, h, quality)
        assert sp > 0
        assert (w * 1000) % int(sp) == 0 and (h * 1000) % int(sp) == 0, (w, h, quality, sp)
        assert sp <= wj.QUALITY_SPACING_M[wj.size_class(w, h)][quality]


def test_legacy_square_values_untouched():
    assert wj.requested_spacing_m(1600, 1600, 'speed') == 4000.0
    assert wj.requested_spacing_m(5000, 5000, 'balanced') == 4000.0
    assert wj.requested_spacing_m(10000, 10000, 'speed') == 12000.0     # 旧表值不变
    assert wj.spacing_m(10000, 'speed') == 12000.0


def test_explicit_square_uses_rectangular_rule():
    """显式给两边（即使相等）就走矩形规则：格距要真能整除；旧表只在未显式时生效。"""
    assert wj.requested_spacing_m(10000, 10000, 'speed') == 12000.0                    # 推断=旧方形
    assert wj.requested_spacing_m(10000, 10000, 'speed', explicit=True) == 10000.0     # 显式矩形
    assert wj.requested_spacing_m(10000, 10000, 'speed', explicit=False) == 12000.0
    for w, h in ((10000, 10000), (5000, 5000), (1600, 1600)):
        sp = wj.requested_spacing_m(w, h, 'speed', explicit=True)
        assert (w * 1000) % int(sp) == 0 and (h * 1000) % int(sp) == 0


def test_legacy_job_shape_still_works_without_dims(tmp_path):
    """旧 job（params 只有 size_km、没有 width/height）照旧走 --size-km，不因矩形改动而变。"""
    m = make_mgr(tmp_path)
    old = dict(name='web-old', paths=m._paths('20261105-120000-abcd'),
               params=dict(world_type='pangaea', size_km=5000, ocean_fraction=0.6, mountain_area=0.22, seed=7,
                           use_gpu=False, quality='speed', pipeline='playable'))
    assert wj.job_dims(old['params']) == (5000, 5000) and wj.explicit_rect(old['params']) is False
    st = {s.name: s for s in m.default_stages(old)}
    assert '--size-km' in st['skeleton'].argv and '--width-km' not in st['skeleton'].argv
    assert st['skeleton'].argv[st['skeleton'].argv.index('--cell-km') + 1] == '20'
    assert st['fast'].argv[st['fast'].argv.index('--spacing-m') + 1] == '8000.0'   # 旧表值
    assert '--defer-mountain-analysis' not in st['islands'].argv
    assert wj.defer_island_analysis(old['params']) is False


# ---------------------------------------------------------------- estimates
def test_estimates_use_real_rectangle_grid():
    sp = wj.requested_spacing_m(10000, 8000, 'speed')
    rect = est.chain(10000, False, sp, pipeline='playable', quick_render=True, height_km=8000)
    fast = next(s for s in rect['stages'] if s['stage'] == 'fast')
    assert fast['spacing_m'] == sp
    assert rect['disk']['nodes'] == 800000
    # 不是把 10000 当方形重复：方形 10000/10000 的磁盘网格项更大
    square = est.chain(10000, False, sp, pipeline='playable', quick_render=True)
    assert rect['disk']['nodes'] < square['disk']['nodes']
    assert rect['disk_bytes'] < square['disk_bytes']
    assert rect['peak_mb'] < square['peak_mb']
    assert rect['total_seconds'] != square['total_seconds']
    assert rect['size_km'] == 10000


def test_skeleton_estimate_and_cell_from_longest_side():
    sk = est.skeleton(10000, 8000)
    assert sk['cell_km'] == 40 and sk['cells'] == 250 * 200
    assert sk['width_km'] == 10000 and sk['height_km'] == 8000
    assert est.skeleton_cell_km(10000, 8000) == 40 == est.skeleton_cell_km(8000, 10000)
    assert est.skeleton_cell_km(1600, 1200) == 10
    assert est.skeleton_cell_km(6000, 1200) == 20
    assert est.skeleton_cell_km(1200, 900) == 10
    # 1600 的实测点只对正方形成立
    assert est.skeleton(1600)['basis'] == 'measured'
    assert est.skeleton(1600, 1200)['basis'] == 'extrapolated'


def test_td_and_disk_accept_rectangle_height():
    # 旧调用（位置参数 + device）保持不变
    assert est.td_coarse(5000, 'cuda')['basis'] == 'extrapolated'
    assert est.td_coarse(5000, 'cuda')['tiles'] == [155, 155]
    sq = est.td_coarse(10000, 'cuda')
    rect = est.td_coarse(10000, 'cuda', height_km=8000)
    assert rect['tiles'][0] < sq['tiles'][0]                     # 矩形面积更小，瓦片更少
    assert rect['tiles'][0] == int(round(sq['tiles'][0] * 0.8))
    assert est.disk_product_bytes(10000, 10000.0, height_km=8000)['nodes'] == 1000 * 800
    assert est.atlas(1600)['basis'] == 'measured' and est.atlas(10000, height_km=8000)['seconds'][0] > 0


def test_memory_gate_is_keyword_compatible():
    old = wj.WorldGenManager.memory_gate_bytes(1600, quality='balanced')
    assert old >= 3200 * 2 ** 20
    assert wj.WorldGenManager.memory_gate_bytes(1600, 2000.0) == old          # 旧位置参数仍在
    gate_rect = wj.WorldGenManager.memory_gate_bytes(10000, 10000.0, height_km=8000)
    assert gate_rect == max(wj.MIN_FREE_BYTES, int(est.world_process_peak_mb(10000, 10000.0, height_km=8000) * 2 ** 20))
    assert gate_rect >= wj.MIN_FREE_BYTES


# ---------------------------------------------------------------- submit / stages
def test_submit_rectangle_params_and_stage_argv(client, tmp_path):
    app, c = client
    app.state.worldgen = make_mgr(tmp_path)
    r = c.post('/api/inner/worldgen/jobs', json=BIG)
    assert r.status_code == 200, r.text
    j = r.json()
    p = j['params']
    assert (p['width_km'], p['height_km']) == (10000, 8000)
    assert p['spacing_m'] == 10000.0 and p['skeleton_cell_km'] == 40 and p['fast_nodes'] == 800000
    assert j['disk_check']['estimated_bytes'] > 0 and j['estimate']['size_km'] == 10000
    assert j['estimate']['disk']['nodes'] == 800000
    # 骨架 CLI 收到独立长宽（不是 --size-km 方形）；cell 按最长边 40 km
    m = app.state.worldgen
    st = {s.name: s for s in m.default_stages(dict(j))}
    sk = st['skeleton'].argv
    assert sk[sk.index('--width-km') + 1] == '10000' and sk[sk.index('--height-km') + 1] == '8000'
    assert '--size-km' not in sk
    assert sk[sk.index('--cell-km') + 1] == '40'
    # 矩形 speed + playable + CPU：岛准备延后 1km 资格分析（不覆盖 GPU 与其他组合）
    assert '--defer-mountain-analysis' in st['islands'].argv
    assert st['islands'].gpu is False
    fast = st['fast'].argv
    assert fast[fast.index('--spacing-m') + 1] == '10000.0'
    assert '--world-processes' not in fast


def test_square_job_keeps_legacy_cli_and_no_defer(tmp_path):
    m = make_mgr(tmp_path)
    st = {s.name: s for s in m.default_stages(job_dict(m, params={}))}
    sk = st['skeleton'].argv
    assert '--size-km' in sk and '--width-km' not in sk and sk[sk.index('--cell-km') + 1] == '10'
    assert '--defer-mountain-analysis' not in st['islands'].argv


@pytest.mark.parametrize('params,defer', [
    (dict(width_km=10000, height_km=8000), True),                       # speed + playable + CPU
    (dict(width_km=10000, height_km=8000, use_gpu=True), False),        # GPU 任务不延后
    (dict(width_km=10000, height_km=8000, quality='balanced'), False),   # 非速度档不延后
    (dict(width_km=10000, height_km=8000, pipeline='full'), False),      # 完整链不延后
    (dict(size_km=10000), False),                                       # 旧方形路径不变
])
def test_defer_island_analysis_only_for_rectangle_speed_cpu(tmp_path, params, defer):
    m = make_mgr(tmp_path)
    st = {s.name: s for s in m.default_stages(job_dict(m, params=params))}
    assert ('--defer-mountain-analysis' in st['islands'].argv) is defer


@pytest.mark.parametrize('params,density', [
    (dict(width_km=10000, height_km=8000), 'low'),                    # 显式矩形 + 最长边 >6000 + speed/playable/CPU
    (dict(width_km=8000, height_km=10000), 'low'),                    # 宽高倒过来一样
    (dict(width_km=6001, height_km=8000), 'low'),                     # 6001-10000 范围内
    (dict(width_km=6000, height_km=6000), None),                      # 最长边 = 6000 不降密度
    (dict(width_km=5000, height_km=3000), None),
    (dict(width_km=10000, height_km=8000, use_gpu=True), None),       # GPU 不动
    (dict(width_km=10000, height_km=8000, quality='balanced'), None), # 非速度档不动
    (dict(width_km=10000, height_km=8000, pipeline='full'), None),    # 完整链不动
    (dict(size_km=10000), None),                                      # 旧方形保 medium
])
def test_island_density_only_for_big_rectangle_speed_cpu(tmp_path, params, density):
    m = make_mgr(tmp_path)
    j = job_dict(m, params=params)
    st = {s.name: s for s in m.default_stages(j)}
    assert wj.island_density(j['params']) == density
    argv = st['islands'].argv
    if density is None:
        assert '--island-density' not in argv                      # 其他请求不动 argv
        assert 'medium' not in argv
    else:
        assert argv[argv.index('--island-density') + 1] == 'low'
        assert '候选密度' in st['islands'].label


def test_island_density_submit_params(client, tmp_path):
    """提交后 params 落实际密度（低/默认 medium）。"""
    app, c = client
    app.state.worldgen = make_mgr(tmp_path)
    j = c.post('/api/inner/worldgen/jobs', json=BIG).json()
    assert j['params']['island_density'] == 'low'
    assert wait(c, j['id'])['status'] == 'succeeded'
    j2 = c.post('/api/inner/worldgen/jobs', json=dict(size_km=10000)).json()
    assert j2['params']['island_density'] == 'medium' and wj.island_density(j2['params']) is None


def test_estimate_short_spacing_is_prechecked(client, tmp_path):
    """明细档在 10000x8000 会超 fast 节点上限：预检拒绝（保留预算报错，不抬上限）。"""
    app, c = client
    app.state.worldgen = make_mgr(tmp_path)
    r = c.post('/api/inner/worldgen/jobs', json=dict(BIG, quality='precise'))
    assert r.status_code == 422 and str(wj.FAST_NODE_BUDGET) in r.json()['detail']
    assert app.state.worldgen.list() == []
    # 速度档通过（同等尺寸）
    ok = c.post('/api/inner/worldgen/jobs', json=BIG)
    assert ok.status_code == 200


# ---------------------------------------------------------------- upgrade
def test_upgrade_inherits_rectangle(client, tmp_path):
    app, c = client
    app.state.worldgen = make_mgr(tmp_path)
    r = c.post('/api/inner/worldgen/jobs', json=BIG)
    assert r.status_code == 200
    jid = r.json()['id']
    j = wait(c, jid)
    assert j['status'] == 'succeeded'
    from pathlib import Path
    import json as _json
    fast_dir = Path(j['paths']['fast_dir'])
    fast_dir.mkdir(parents=True, exist_ok=True)
    (fast_dir / 'manifest.json').write_text(_json.dumps(dict(identity='a' * 64, grid=dict(spacing_m=10000.0))), encoding='utf-8')
    mountains = Path(j['paths']['world_dir']) / 'island-mountains'
    mountains.mkdir(parents=True, exist_ok=True)
    (mountains / 'world-input.json').write_text('{}', encoding='utf-8')
    up = c.post(f'/api/inner/worldgen/jobs/{jid}/upgrade', json=dict(quality='speed'))
    assert up.status_code == 409 and '相同' in up.json()['detail']          # 同格距仍拒绝
    up = c.post(f'/api/inner/worldgen/jobs/{jid}/upgrade', json=dict(quality='balanced'))
    assert up.status_code == 200, up.text
    u = up.json()
    assert (u['params']['width_km'], u['params']['height_km']) == (10000, 8000)
    assert u['params']['quality'] == 'balanced'
    sp = u['params']['spacing_m']
    assert sp == wj.requested_spacing_m(10000, 8000, 'balanced')
    assert (10000 * 1000) % int(sp) == 0 and (8000 * 1000) % int(sp) == 0
    assert u['estimate']['disk']['nodes'] == int(round(10000 * 1000 / sp)) * int(round(8000 * 1000 / sp))
    stages = {s.name: s for s in app.state.worldgen.upgrade_stages(dict(u))}
    assert 'skeleton' not in stages                                   # 复用骨架，不重跑
    assert stages['fast'].argv[stages['fast'].argv.index('--spacing-m') + 1] == str(sp)


def test_options_expose_rectangles(client, tmp_path):
    app, c = client
    app.state.worldgen = make_mgr(tmp_path)
    o = c.get('/api/inner/worldgen/options').json()
    assert o['rectangles']['width_km'] == [100, 10000] and o['rectangles']['height_km'] == [100, 10000]
    assert o['rectangles']['together'] is True and o['rectangles']['size_class_by'] == 'longest'
    assert o['defaults']['size_km'] == 1600                              # 旧默认形状不变
    assert 'width_km' not in o['defaults']                               # 旧 defaults 形状不变（矩形是可选新增）
    assert [s['km'] for s in o['sizes']] == [1600, 5000, 10000]
    assert o['estimates']['10000']['speed']['spacing_m'] == 12000.0      # 旧方形估算不变


def test_cli_accepts_paired_sides_only(tmp_path):
    """骨架 CLI：--width-km/--height-km 成对，且与 --size-km 互斥（不真生成）。"""
    sys.path.insert(0, str(wj.ROOT / 'tools'))
    import generate_world_skeleton as gws  # noqa: E402
    from app.world_gen.config import ConfigError
    with pytest.raises(SystemExit):
        gws.main(['--preset', 'pangaea', '--width-km', '10000'])
    with pytest.raises(SystemExit):
        gws.main(['--preset', 'pangaea', '--width-km', '10000', '--height-km', '8000', '--size-km', '1600'])
    with pytest.raises(ConfigError):                                  # 越界交给 config.normalize 拒
        gws.main(['--preset', 'pangaea', '--width-km', '50', '--height-km', '8000', '--plan-only'])


# ---------------------------------------------------------------- upgrade 复用岛的元数据
def write_prepared(world_dir, *, density=None, analysis_status='complete', analysis_qualification='ok'):
    """写入一份已冻结的岛准备记录（只用于读回 density / analysis）。"""
    import json
    from pathlib import Path
    d = Path(world_dir) / 'ocean-islands'
    d.mkdir(parents=True, exist_ok=True)
    record = dict(schema='x', analysis=dict(status=analysis_status, qualification=analysis_qualification),
                  island_identity='b' * 64)
    if density is not None:
        record['island_density'] = density
    (d / 'prepared.json').write_text(json.dumps(record), encoding='utf-8')
    return record


def test_upgrade_keeps_source_island_density_not_new_quality(client, tmp_path):
    """upgrade 复用 src 岛：已备 low 就不能因换到 balanced 而报 medium（没重跑 prepare）。"""
    app, c = client
    app.state.worldgen = make_mgr(tmp_path)
    j = c.post('/api/inner/worldgen/jobs', json=dict(width_km=8000, height_km=5000)).json()
    assert j['params']['island_density'] == 'low'          # speed + 最长边 8000 > 6000
    assert wait(c, j['id'])['status'] == 'succeeded'
    from pathlib import Path
    import json as _json
    fast_dir = Path(j['paths']['fast_dir'])
    fast_dir.mkdir(parents=True, exist_ok=True)
    (fast_dir / 'manifest.json').write_text(_json.dumps(dict(identity='a' * 64, grid=dict(spacing_m=10000.0))), encoding='utf-8')
    mountains = Path(j['paths']['world_dir']) / 'island-mountains'
    mountains.mkdir(parents=True, exist_ok=True)
    (mountains / 'world-input.json').write_text('{}', encoding='utf-8')
    write_prepared(j['paths']['world_dir'], density='low', analysis_status='pending-analysis')
    up = c.post(f"/api/inner/worldgen/jobs/{j['id']}/upgrade", json=dict(quality='balanced'))
    assert up.status_code == 200, up.text
    u = up.json()
    assert u['params']['island_density'] == 'low'          # 仍是在盘岛的 low，不是按 balanced 重算的 medium
    assert wj.island_density({'width_km': 8000, 'height_km': 5000, 'quality': 'balanced',
                              'pipeline': 'playable'}) is None       # 新请求本身也不会要 low


def test_upgrade_legacy_source_without_density_falls_back_to_medium(client, tmp_path):
    """旧源（没有 island_density 字段、记录也没写）→ medium，不捧高也不造假 low。"""
    app, c = client
    app.state.worldgen = make_mgr(tmp_path)
    j = c.post('/api/inner/worldgen/jobs', json=dict(width_km=8000, height_km=5000)).json()
    assert wait(c, j['id'])['status'] == 'succeeded'
    src = app.state.worldgen._jobs[j['id']]
    src['params'].pop('island_density', None)
    from pathlib import Path
    import json as _json
    fdir = Path(j['paths']['fast_dir'])
    fdir.mkdir(parents=True, exist_ok=True)
    (fdir / 'manifest.json').write_text(
        _json.dumps(dict(identity='a' * 64, grid=dict(spacing_m=10000.0))), encoding='utf-8')
    mountains = Path(j['paths']['world_dir']) / 'island-mountains'
    mountains.mkdir(parents=True, exist_ok=True)
    (mountains / 'world-input.json').write_text('{}', encoding='utf-8')
    write_prepared(j['paths']['world_dir'])                 # 记录里也没有 density
    assert wj.saved_island_density({}) == 'medium'
    assert wj.saved_island_density({'island_density': 'bogus'}) == 'medium'
    up = c.post(f"/api/inner/worldgen/jobs/{j['id']}/upgrade", json=dict(quality='balanced'))
    assert up.status_code == 200, up.text
    assert up.json()['params']['island_density'] == 'medium'


def test_summary_reports_saved_density_and_real_analysis(tmp_path):
    """summary 读已存岛记录：density 与 analysis 都是实际值，不按当前 quality 推测。"""
    m = make_mgr(tmp_path)
    job = dict(name='web-x', paths=m._paths('20261105-120000-abcd'),
               params=dict(world_type='pangaea', size_km=1600, width_km=10000, height_km=8000, ocean_fraction=0.6,
                           mountain_area=0.22, seed=7, use_gpu=False, quality='balanced', pipeline='playable',
                           spacing_m=8000.0, skeleton_cell_km=40, fast_nodes=1000 * 800))
    write_prepared(job['paths']['world_dir'], density='low', analysis_status='pending-analysis',
                   analysis_qualification='not qualified: deferred')
    assert wj.island_density(job['params']) is None                     # 当前请求并不要求 low
    record, where = wj.saved_island_record(job)
    assert where == 'ocean-islands/prepared.json'
    assert wj.island_record_density(job['params'], record) == 'low'      # 实际保存的 low
    assert wj.island_record_analysis(record) == ('pending-analysis', True)
    # 记录里是完成的分析时不会谎报 deferred
    record2 = dict(analysis=dict(status='complete'))
    assert wj.island_record_analysis(record2) == ('complete', False)
    assert wj.island_record_analysis({}) == (None, None)


def test_summary_prefers_fast_manifest_record_over_param(tmp_path):
    """没有 prepared.json 时读 fast manifest 的岛记录（同样以实际为准）。"""
    import json as _json
    from pathlib import Path
    m = make_mgr(tmp_path)
    job = dict(name='web-x', paths=m._paths('20261105-120000-abcd'),
               params=dict(world_type='pangaea', size_km=1600, ocean_fraction=0.6, mountain_area=0.22, seed=7,
                           use_gpu=False, quality='speed', pipeline='playable', spacing_m=4000.0))
    fdir = Path(job['paths']['fast_dir'])
    fdir.mkdir(parents=True, exist_ok=True)
    (fdir / 'manifest.json').write_text(_json.dumps(dict(identity='a' * 64, island_mountains=dict(
        record=dict(island_density='low', analysis=dict(status='pending-analysis'))))), encoding='utf-8')
    record, where = wj.saved_island_record(job)
    assert where == 'fast manifest island_mountains.record'
    assert wj.island_record_density(job['params'], record) == 'low'
    assert wj.island_record_analysis(record) == ('pending-analysis', True)
    # 什么记录都没有时退回 job param（旧行为），再退回 medium
    assert wj.island_record_density({'island_density': 'low'}, {}) == 'low'
    assert wj.island_record_density({}, {}) == 'medium'
