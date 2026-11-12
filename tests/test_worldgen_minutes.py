"""概览快档（quality=speed + pipeline=playable）：成图只出 1200 px 概览、无附页。

只验证本次最小改动：render argv 追加 --overview-only --width 1200、估算链只有 render/atlas 项变化、
其余组合（balanced / precise / full，以及 use_gpu）行为保持旧样。不跑真实生成。
"""
import pytest

from app.world_gen import estimates as est, web_jobs as wj

GIB = 2 ** 30
GPU_OK = (True, dict(cuda_available=True, cuda_free_mib=7000, cuda_total_mib=8191, name='Fake GPU'))


def manager(tmp_path, **kw):
    opts = dict(artifacts=tmp_path / 'artifacts', gpu_probe=lambda: GPU_OK, memory=lambda: 8 * GIB,
                gpu_jobs=lambda: [], gpu_sampler=lambda: 1000)
    opts.update(kw)
    opts.setdefault('stage_builder', lambda job: [wj.Stage('summary', 'fake', fn=lambda j: dict(ok=True))])
    return wj.WorldGenManager(tmp_path, **opts)


def job_dict(m, *, quality='speed', pipeline='playable', use_gpu=False, size_km=1600):
    return dict(name='web-x', params=dict(world_type='pangaea', size_km=size_km, ocean_fraction=0.6, mountain_area=0.22,
                                          seed=7, use_gpu=use_gpu, quality=quality, pipeline=pipeline,
                                          spacing_m=wj.spacing_m(size_km, quality)),
                paths=m._paths('20261105-120000-abcd'))


def render_of(stages):
    return next(s for s in stages if s.name == 'render')


def test_quick_overview_policy_only_default_pair():
    assert est.quick_overview('speed', 'playable') is True
    assert est.quick_overview('speed') is True                     # pipeline 缺省按 playable
    assert est.quick_overview('balanced', 'playable') is False
    assert est.quick_overview('precise', 'playable') is False
    assert est.quick_overview('speed', 'full') is False
    assert est.OVERVIEW_WIDTH_PX == 1200


def test_quick_render_estimate_only_touches_render_and_atlas():
    slow = est.chain(1600, False, 4000.0, pipeline='playable')
    quick = est.chain(1600, False, 4000.0, pipeline='playable', quick_render=True)
    assert slow['quick_render'] is False and quick['quick_render'] is True
    # 阶段序列、格距、其它阶段的秒数一律不变
    assert [s['stage'] for s in slow['stages']] == [s['stage'] for s in quick['stages']]
    assert quick['spacing_m'] == slow['spacing_m'] == 4000.0
    assert quick['peak_mb'] == slow['peak_mb']
    for name in ('skeleton', 'fast'):
        a = next(s for s in slow['stages'] if s['stage'] == name)
        b = next(s for s in quick['stages'] if s['stage'] == name)
        assert a['seconds'] == b['seconds'] and a['basis'] == b['basis']
    # 只有 render 换概览：保守推算 15-45 s、1200 px、推算（非实测）
    qr = next(s for s in quick['stages'] if s['stage'] == 'render')
    sr = next(s for s in slow['stages'] if s['stage'] == 'render')
    assert qr['seconds'] == list(est.QUICK_RENDER_SECONDS) == [15.0, 45.0]
    assert qr['width_px'] == 1200 and qr['overview_only'] is True and qr['basis'] == est.EXTRAPOLATED
    assert sr['seconds'] == [140.0, 140.0] and sr['basis'] == est.MEASURED
    assert 'width_px' not in sr
    # 磁盘只调 atlas 项
    assert quick['disk']['breakdown']['atlas'] < slow['disk']['breakdown']['atlas']
    for key in ('grids', 'skeleton', 'vectors', 'islands'):
        assert quick['disk']['breakdown'][key] == slow['disk']['breakdown'][key]
    assert quick['disk_bytes'] < slow['disk_bytes']
    # quick_render 只对 playable 生效，full 不受影响
    full = est.chain(1600, False, 4000.0, pipeline='full', quick_render=True)
    assert full['quick_render'] is False and full['disk']['quick_render'] is False
    assert [s['stage'] for s in full['stages']][-1] == 'final-render'


def test_balanced_and_full_estimates_unchanged():
    # 旧的 balanced/playable 测量点（balanced 只改格距 2 km，pipeline 仍是 playable）：render 仍是实测 140 s，磁盘不缩
    bal = est.chain(1600, False, 2000.0, pipeline='playable')
    assert bal['basis'] == est.MEASURED and bal['quick_render'] is False
    assert next(s for s in bal['stages'] if s['stage'] == 'render')['seconds'] == [140.0, 140.0]
    assert bal['disk_bytes'] == est.disk_product_bytes(1600, 2000.0, pipeline='playable')['bytes']
    assert est.disk_product_bytes(1600, 2000.0, pipeline='playable', quick_render=False) == \
        est.disk_product_bytes(1600, 2000.0, pipeline='playable')
    full = est.chain(1600, True, 2000.0, pipeline='full')
    assert {s['stage'] for s in full['stages']} >= {'skeleton', 'fast', 'td', 'render', 'world-processes', 'final-render'}
    assert full['basis'] == est.EXTRAPOLATED
    # 格距表不动
    assert wj.spacing_m(1600, 'speed') == 4000.0 and wj.spacing_m(1600, 'balanced') == 2000.0


def test_stage_argv_quick_overview_for_speed_playable(tmp_path):
    m = manager(tmp_path)
    st = m.default_stages(job_dict(m))
    names = [s.name for s in st]
    assert names == ['skeleton', 'islands', 'island-mountains', 'fast', 'render', 'summary']
    rend = render_of(st)
    assert '--overview-only' in rend.argv and rend.argv[rend.argv.index('--width') + 1] == '1200'
    assert '概览' in rend.label
    fast = next(s for s in st if s.name == 'fast')
    assert '--world-processes' not in fast.argv                       # 物理/阶段不受影响
    sk = next(s for s in st if s.name == 'skeleton')
    assert sk.argv[sk.argv.index('--cell-km') + 1] == '10'
    assert not [s for s in st if s.name in ('details', 'final-render')]


def test_stage_argv_unchanged_for_balanced_full_and_upgrade(tmp_path):
    m = manager(tmp_path)
    bal = m.default_stages(job_dict(m, quality='balanced'))
    assert '--overview-only' not in render_of(bal).argv and '--width' not in render_of(bal).argv
    full = m.default_stages(job_dict(m, quality='speed', pipeline='full'))
    assert '--overview-only' not in render_of(full).argv            # 完整链仍出完整图册
    assert '--world-processes' in next(s for s in full if s.name == 'fast').argv
    # upgrade：speed+playable 同样快档，balanced 不用
    speed_job = job_dict(m)
    up = {s.name: s for s in m.upgrade_stages(speed_job)}
    assert '--overview-only' in up['render'].argv and up['render'].argv[up['render'].argv.index('--width') + 1] == '1200'
    assert 'skeleton' not in up and 'details' not in up
    bal_job = job_dict(m, quality='balanced')
    up_bal = {s.name: s for s in m.upgrade_stages(bal_job)}
    assert '--overview-only' not in up_bal['render'].argv


def test_gpu_job_keeps_gpu_and_quick_overview(tmp_path):
    m = manager(tmp_path)
    st = {s.name: s for s in m.default_stages(job_dict(m, use_gpu=True))}
    assert st['island-mountains'].gpu and '--use-gpu' in st['island-mountains'].argv   # GPU 未被关掉
    assert '--overview-only' in st['render'].argv
    assert '--use-gpu' not in st['render'].argv
    gpu_chain = est.chain(1600, True, 4000.0, pipeline='playable', quick_render=True)
    assert 'td' not in {s['stage'] for s in gpu_chain['stages']}       # playable 不因快档多出阶段


def test_options_and_submit_use_same_policy(tmp_path):
    m = manager(tmp_path)
    o = m.options()
    for size in ('1600', '5000', '10000'):
        speed = o['estimates'][size]['speed']['pipelines']['playable']['cpu']
        assert speed['quick_render'] is True
        rend = next(s for s in speed['stages'] if s['stage'] == 'render')
        assert rend['width_px'] == 1200 and rend['seconds'] == [15.0, 45.0]
        bal = o['estimates'][size]['balanced']['pipelines']['playable']['cpu']
        assert bal['quick_render'] is False
        assert 'width_px' not in next(s for s in bal['stages'] if s['stage'] == 'render')
        full = o['estimates'][size]['speed']['pipelines']['full']['cpu']
        assert full['quick_render'] is False
    notes = '\n'.join(o['notes'])
    assert '1200' in notes and '概览' in notes and '不承诺分钟级' in notes
    # 提交的任务：估算/磁盘与 policy 一致
    m.stage_builder = lambda job: [wj.Stage('summary', 'fake', fn=lambda j: dict(ok=True))]
    m.tg_python = tmp_path / 'fake-python.exe'
    m.tg_python.write_bytes(b'')
    if not m.tg_python.is_file():
        pytest.skip('cannot create fake interpreter')
    job = m.submit(wj.WorldGenRequest())
    params = job['params']
    assert params['quality'] == 'speed' and params['pipeline'] == 'playable' and params['quick_render'] is True
    assert job['estimate']['quick_render'] is True
    rend = next(s for s in job['estimate']['stages'] if s['stage'] == 'render')
    assert rend['width_px'] == 1200 and rend['overview_only'] is True
    assert job['disk_check']['estimated_bytes'] == est.disk_product_bytes(
        1600, params['spacing_m'], pipeline='playable', quick_render=True)['bytes']
    st = {s.name: s for s in m.default_stages(dict(job, params=params))}
    assert '--overview-only' in st['render'].argv
    # 非默认组合：submit 不传快档
    m._busy = False
    job2 = m.submit(wj.WorldGenRequest(quality='balanced'))
    assert job2['params']['quick_render'] is False
    assert job2['estimate']['quick_render'] is False
    assert '--overview-only' not in render_of(m.default_stages(dict(job2, params=job2['params']))).argv
