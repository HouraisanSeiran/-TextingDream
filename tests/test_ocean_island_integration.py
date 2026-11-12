"""CPU-only real public consumers of a strictly frozen synthetic plate fixture."""
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
TG = ROOT.parent / '山川形意Terragenesis'
sys.path.insert(0,str(TG))
from terrain_pipeline import ocean_islands as core
from terrain_pipeline.ocean_island_consumers import sample_td_condition
from app.world_gen import ocean_island_adapter as bridge, fast_relief as fr, local30
from app.world_gen.config import sha256_json
from app.world_relief import td_resident as td


@pytest.fixture(scope='module')
def frozen(tmp_path_factory):
    directory=tmp_path_factory.mktemp('ocean-integration')
    shape=(40,40)
    arrays={'final/elevation_m':np.full(shape,-4000.),'final/plate_id':np.zeros(shape,np.int64),
            'final/continental_fraction':np.zeros(shape),'final/ocean_connected':np.ones(shape,bool),
            'final/velocities_m_per_step':np.array([[1800.,500.]]),'final/crust_thickness_m':np.full(shape,7000.)}
    config=dict(shape=list(shape),cell_size_m=20000.,origin_x_m=-400000.,origin_z_m=-400000.,world_seed=20260903)
    manifest=dict(schema='dream-world-skeleton-plate-v1',algorithm='declared-integration-fixture',world_config_identity='c'*64,
                  config=config,arrays={k:dict(shape=list(a.shape),dtype=str(a.dtype),sha256=__import__('hashlib').sha256(a.tobytes()).hexdigest()) for k,a in arrays.items()})
    manifest['identity']=sha256_json(manifest)
    source_path=directory/'skeleton.npz'
    np.savez_compressed(source_path,manifest_json=np.array(json.dumps(manifest)),**arrays)
    source=core.PlateOceanSource.from_npz(source_path)
    product=core.prepare_ocean_islands(source,core.OceanIslandConfig(hotspot_count=12,density='high',arcs=False,ridge=False,atolls=True,warm_water_scenario=True))
    island_path=directory/'islands.npz';core.save_product(product,island_path)
    disabled=core.prepare_ocean_islands(source,core.OceanIslandConfig(density='none'))
    disabled_path=directory/'disabled.npz';core.save_product(disabled,disabled_path)
    run=dict(schema='dream-world-skeleton-run-v1',config_identity='c'*64,
             product=dict(plate_identity=source.identity,sha256=bridge.file_sha(source_path)),
             targets=dict(ocean_fraction=.6,ocean_tolerance_abs=.015))
    run['identity']=sha256_json(run)
    run_path=directory/'skeleton-run.json';run_path.write_text(json.dumps(run),encoding='utf-8')
    assert product.features and any(f.kind=='atoll' for f in product.features)
    return SimpleNamespace(directory=directory,source=source,source_path=source_path,product=product,island_path=island_path,
                           disabled=disabled,disabled_path=disabled_path,run_path=run_path)


def options(frozen):
    return dict(island_product_path=frozen.island_path,expected_island_identity=frozen.product.identity,skeleton_run_path=frozen.run_path)


def test_binding_source_target_integrity_and_missing_product(frozen,tmp_path):
    binding=bridge.load_binding(frozen.source_path,frozen.island_path,frozen.product.identity,frozen.run_path)
    assert binding.record['ocean_quota']['target_fraction']==.6
    assert binding.record['ocean_quota']['tolerance_abs']==.015
    unknown=bridge.load_binding(frozen.source_path,frozen.island_path,frozen.product.identity)
    assert unknown.record['ocean_quota']['status']=='unknown'
    with pytest.raises(ValueError):
        bridge.load_binding(frozen.source_path,frozen.island_path,'0'*64)
    with pytest.raises(FileNotFoundError):
        bridge.load_binding(frozen.source_path,tmp_path/'missing.npz',frozen.product.identity)
    wrong=json.loads(frozen.run_path.read_text());wrong['product']['plate_identity']='0'*64
    wrong.pop('identity');wrong['identity']=sha256_json(wrong)
    path=tmp_path/'wrong-run.json';path.write_text(json.dumps(wrong))
    with pytest.raises(ValueError,match='does not bind'):
        bridge.load_binding(frozen.source_path,frozen.island_path,frozen.product.identity,path)
    with np.load(frozen.source_path,allow_pickle=False) as archive:
        arrays={k:archive[k] for k in archive.files}
    manifest=json.loads(str(arrays['manifest_json']))
    manifest['world_config_identity']='d'*64
    manifest.pop('identity');manifest['identity']=sha256_json(manifest)
    arrays['manifest_json']=np.array(json.dumps(manifest))
    foreign=tmp_path/'foreign-skeleton.npz';np.savez_compressed(foreign,**arrays)
    with pytest.raises(ValueError,match='different skeleton identity'):
        bridge.load_binding(foreign,frozen.island_path,frozen.product.identity)


def test_saved_targets_restore_erosion_without_recomposition_and_publish_dtype(frozen):
    binding=bridge.load_binding(frozen.source_path,frozen.island_path,frozen.product.identity)
    atoll=next(f for f in frozen.product.features if f.kind=='atoll')
    x=np.array([[atoll.center_x_m]])
    z=np.array([[atoll.center_z_m]])
    from terrain_pipeline.ocean_island_consumers import compose_surface
    q=compose_surface(binding.product,x,z,np.full((1,1),-3900.))
    elevation,ocean,lagoon=bridge.restore_after_erosion(q,np.full((1,1),5.))
    assert elevation.dtype==np.float32 and elevation[0,0]<0
    assert lagoon[0,0] and not ocean[0,0]
    tiny=dict(elevation_m=np.array([[-1e-50]]),protection_weight=np.ones((1,1)),lagoon=np.ones((1,1),bool))
    h,oc,lag=bridge.restore_after_erosion(tiny,np.zeros((1,1)))
    assert h[0,0]==0 and not oc.any() and not lag.any()


def test_real_fast_compute_and_freeze_keep_lagoons_status_and_fractions(frozen,tmp_path):
    pytest.importorskip('numba', reason='fast_relief hydrology needs Terragenesis runtime/venv (numba)')
    before=bridge.file_sha(frozen.source_path)
    sk=fr.load_skeleton(frozen.source_path,frozen.source.identity)
    params=dict(spacing_m=4000.,erosion_iterations=1,smooth_rivers=False,breach_passes=1)
    result=fr.compute(sk,params,erosion=True,log=None,**options(frozen))
    data=result['ocean_islands'];lagoon=data['lagoon'];h=result['elevation']
    assert lagoon.any() and np.all(h[lagoon]<0) and not (result['ocean']&lagoon).any()
    assert not (result['ocean']&(h>=0)).any()
    assert not result['wet'][lagoon].any()
    assert data['fractions'].metadata['feature_ids']==[f.feature_id for f in frozen.product.features]
    assert (data['fractions'].land_fraction>0).any()
    out,manifest=fr.freeze(frozen.source_path,tmp_path/'fast',params=params,erosion=True,expected_identity=frozen.source.identity,
                           min_free_bytes=1,log=lambda *_:None,**options(frozen))
    status=np.load(out/'status.npy');height=np.load(out/'elevation_m.npy');lags=np.load(out/'registered_lagoon.npy')
    assert np.all(status[lags]==4) and np.all(height[lags]<0)
    assert np.isnan(np.load(out/'water_surface_m.npy')[lags]).all()
    assert manifest['statistics']['land_fraction']==float((height>=0).mean())
    assert manifest['statistics']['closed_below_sea_fraction']==float(((height<0)&(status!=3)).mean())
    assert manifest['lineage'][-1]==frozen.product.identity
    assert (out/'vectors/ocean-islands.json').exists() and (out/'ocean-island-binding.json').exists()
    assert manifest['ocean_islands']['quota']['target_fraction']==.6
    assert bridge.file_sha(frozen.source_path)==before
    spec=importlib.util.spec_from_file_location('test_world_island_audit',ROOT/'tests/ocean_island_integration_audit.py')
    auditor=importlib.util.module_from_spec(spec);spec.loader.exec_module(auditor)
    checked=auditor.audit(out,frozen.source_path,frozen.island_path,frozen.product.identity,frozen.run_path)
    assert checked['unprotected_original_negative_cells']>0
    assert checked['unprotected_original_negative_max_error_m']==0


def test_optional_islands_preserve_closed_negative_bed_outside_support(frozen,tmp_path,monkeypatch):
    pytest.importorskip('numba', reason='fast_relief hydrology needs Terragenesis runtime/venv (numba)')
    original=fr.build_terrain
    basin=np.zeros((40,40),bool);basin[18:22,18:22]=True
    def terrain(*args,**kwargs):
        result=original(*args,**kwargs)
        height=np.full((40,40),-4000.,np.float32)
        height[15:25,15:25]=100.
        height[basin]=-35.
        result['elevation']=height
        result['ocean']=height<0
        return result
    monkeypatch.setattr(fr,'build_terrain',terrain)
    params=dict(spacing_m=20000.,erosion_iterations=1,breach_passes=1,smooth_rivers=False)
    sk=fr.load_skeleton(frozen.source_path,frozen.source.identity)
    baseline=fr.compute(sk,params,erosion=True)
    out,_=fr.freeze(frozen.source_path,tmp_path/'closed-basin',params=params,erosion=True,
        min_free_bytes=1,log=lambda *_:None,island_product_path=frozen.disabled_path,
        expected_island_identity=frozen.disabled.identity)
    height=np.load(out/'elevation_m.npy');status=np.load(out/'status.npy')
    np.testing.assert_array_equal(height[basin],np.full(basin.sum(),-35.,np.float32))
    assert np.all(status[basin]==4)
    assert not np.load(out/'registered_lagoon.npy').any()
    assert not np.load(out/'protected_fraction.npy').any()
    np.testing.assert_array_equal(height>=0,baseline['elevation']>=0)


def test_real_td_raw_factory_uses_same_product_and_explicit_world_period(frozen):
    from diffusion.physical_config import PhysicalGenerationConfig
    config=PhysicalGenerationConfig()
    factory,_=td.periodic_factory(frozen.source_path,config,**options(frozen))
    axis=np.arange(-40,40)*config.conditioning_spacing_m
    raw=factory.sample_raw(-40,-40,40,40)
    original=td.sample_periodic(frozen.source.elevation_m,
        dict(origin_x_m=-400000.,origin_z_m=-400000.,cell_size_m=20000.),axis[None,:],axis[:,None])
    expected=sample_td_condition(frozen.product,axis[None,:],axis[:,None],original,periodic=True)['elevation_m']
    np.testing.assert_allclose(raw[0],expected,rtol=1e-6,atol=1e-3)
    assert np.max(abs(raw[0]-original))>100
    assert factory.island_binding['island_identity']==frozen.product.identity
    x=np.array([frozen.product.features[0].center_x_m]);z=np.array([frozen.product.features[0].center_z_m])
    np.testing.assert_allclose(bridge.condition_height(bridge.load_binding(frozen.source_path,frozen.island_path,frozen.product.identity),x+800000,z,np.array([-4000.])),
                               bridge.condition_height(bridge.load_binding(frozen.source_path,frozen.island_path,frozen.product.identity),x,z,np.array([-4000.])))


def test_local30_cpu_generator_freezes_island_lineage_and_rejects_changed_or_removed(frozen,tmp_path):
    from diffusion.physical_config import PhysicalGenerationConfig
    factory,_=td.periodic_factory(frozen.source_path,PhysicalGenerationConfig(),**options(frozen))
    calls=[]
    def injected(origin,side):
        calls.append(origin)
        # CPU injected generation explicitly consumes the actual raw condition;
        # this does not simulate or claim TD model response.
        raw=factory.sample_raw(0,0,1,1)
        return np.full((side,side),raw[0,0,0],np.float32)
    manifest=local30.prepare_tile(tmp_path,0,0,purpose='cpu-integration',reason='condition wiring test',plate_path=frozen.source_path,
               generator=injected,available_bytes=8*2**30,**options(frozen))
    assert manifest['island_identity']==frozen.product.identity
    assert manifest['island_condition_policy']==bridge.CONDITION_POLICY
    assert manifest['lineage']==[frozen.source.identity,frozen.product.identity]
    assert not local30.request_local(tmp_path,200,200,300)['all_prepared']
    current=local30.request_local(tmp_path,200,200,300,plate_identity=frozen.source.identity,island_identity=frozen.product.identity,
                                  island_condition_policy=bridge.CONDITION_POLICY)
    assert current['all_prepared']
    again=local30.prepare_tile(tmp_path,0,0,purpose='cpu-integration',reason='condition wiring test',plate_path=frozen.source_path,
               generator=injected,available_bytes=8*2**30,**options(frozen))
    assert again['identity']==manifest['identity'] and len(calls)==1
    with pytest.raises(local30.StaleTile,match='island identity'):
        local30.prepare_tile(tmp_path,0,0,purpose='t',reason='t',plate_path=frozen.source_path,generator=injected,available_bytes=8*2**30)
    with pytest.raises(local30.StaleTile):
        local30.prepare_tile(tmp_path,0,0,purpose='t',reason='t',plate_path=frozen.source_path,generator=injected,available_bytes=8*2**30,
               island_product_path=frozen.disabled_path,expected_island_identity=frozen.disabled.identity)
    assert local30.tile_state(tmp_path,'x+000z+000',plate_identity=frozen.source.identity,island_identity=frozen.product.identity,
                              island_condition_policy='changed')['status']=='stale'
    assert len(calls)==1


def test_actual_fast_cli_passes_optional_binding(frozen,tmp_path):
    pytest.importorskip('numba', reason='fast_relief CLI hydrology needs Terragenesis runtime/venv (numba)')
    spec=importlib.util.spec_from_file_location('test_build_fast_tool',ROOT/'tools/build_fast_relief.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    out=tmp_path/'from-cli'
    result=module.main(['--skeleton',str(frozen.source_path),'--out',str(out),'--expected-identity',frozen.source.identity,
        '--island-product-path',str(frozen.island_path),'--expected-island-identity',frozen.product.identity,'--skeleton-run',str(frozen.run_path),
        '--params',json.dumps(dict(spacing_m=4000,erosion_iterations=1,breach_passes=1,smooth_rivers=False)),'--min-free-gib','.001'])
    assert result==0
    manifest=json.loads((out/'manifest.json').read_text())
    assert manifest['ocean_islands']['binding']['island_identity']==frozen.product.identity
    assert manifest['ocean_islands']['quota']['tolerance_abs']==.015


def test_actual_local_cli_passes_islands_without_gpu(frozen,tmp_path,monkeypatch):
    spec=importlib.util.spec_from_file_location('test_local30_tool',ROOT/'tools/prepare_local30.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    from app.world_gen import config as wc,sysmem
    config=dict(world_name='cpu-cli-test',skeleton=dict(source='existing',path=str(frozen.source_path),identity=frozen.source.identity))
    config_path=tmp_path/'world.json';config_path.write_text(json.dumps(config))
    monkeypatch.setattr(local30,'gpu_gate',lambda:dict(status='test-injected-no-gpu'))
    monkeypatch.setattr(sysmem,'available_memory_bytes',lambda:8*2**30)
    monkeypatch.setattr(local30,'world_cells_from_pages',lambda *args:None)
    original=local30.prepare_tile
    calls=[]
    def invoke(*args,**kwargs):
        calls.append(kwargs['expected_island_identity'])
        kwargs['generator']=lambda origin,side:np.full((side,side),-40.,np.float32)
        return original(*args,**kwargs)
    monkeypatch.setattr(local30,'prepare_tile',invoke)
    result=module.main(['--config',str(config_path),'--tile','0','0','--reason','CPU CLI integration',
       '--out-root',str(tmp_path/'worlds'),'--island-product-path',str(frozen.island_path),
       '--expected-island-identity',frozen.product.identity,'--skeleton-run',str(frozen.run_path)])
    assert result==0 and calls==[frozen.product.identity]
    manifest=json.loads((tmp_path/'worlds/cpu-cli-test/local30/x+000z+000/manifest.json').read_text())
    assert manifest['island_identity']==frozen.product.identity
