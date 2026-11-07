"""Declared large-island CPU scheduling, separate from real-world acceptance."""
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from app.world_gen import island_mountains as adapter,local30,tiles as T

TG=Path(__file__).resolve().parents[2]/'山川形意Terragenesis'
sys.path.insert(0,str(TG))
from terrain_pipeline.island_mountains import (
    IslandMountainConfig,analyze_island_mountains,save_mountain_plan,sample_mountain_weights,
)
fixture_spec=importlib.util.spec_from_file_location('mountain_strict_source_fixture',
    Path(__file__).with_name('test_ocean_island_integration.py'))
fixture_module=importlib.util.module_from_spec(fixture_spec);fixture_spec.loader.exec_module(fixture_module)
frozen=fixture_module.frozen


@pytest.fixture
def declared(tmp_path,monkeypatch):
    def query(x,z):
        x,z=np.broadcast_arrays(np.asarray(x,float),np.asarray(z,float))
        land=x*x+z*z<35000.**2
        return dict(elevation_m=np.where(land,500.,-4000.),base_elevation_m=np.full(x.shape,-4000.),
                    protected=np.ones(x.shape,bool),lagoon=np.zeros(x.shape,bool))
    product=SimpleNamespace(identity='a'*64,source=SimpleNamespace(identity='c'*64,
        bounds_m=(-100000.,-100000.,100000.,100000.)),config=SimpleNamespace(world_seed=20260903),query=query)
    plan=analyze_island_mountains(product)
    # These pre-existing dispatch/cache checks retain the frozen v2 policy.
    # Whole-component v3 normalization is covered by the dedicated test below.
    from terrain_pipeline.island_mountains import IslandMountainPlan,AREA_ALGORITHM,AREA_POLICY,identity
    m=plan.manifest;m.update(algorithm=AREA_ALGORITHM,blend_policy=AREA_POLICY,schema='island-mountain-plan-v2')
    m.pop('peak_normalization_required');m['identity']=identity({k:v for k,v in m.items() if k!='identity'})
    plan=IslandMountainPlan(m,plan.selected_interior,plan.coast_distance_m,plan.interior_distance_m)
    path=tmp_path/'plan.npz'
    np.savez_compressed(path,manifest_json=np.array(json.dumps(plan.manifest)),selected_interior=plan.selected_interior,
        coast_distance_m=plan.coast_distance_m,interior_distance_m=plan.interior_distance_m)
    binding=SimpleNamespace(product=product,record=dict(plate_identity='c'*64,island_identity=product.identity,
        condition_policy='declared-cpu-fixture',source_kind='declared-analytic-large-island-fixture'))
    monkeypatch.setattr(adapter,'load_plan',lambda *args:(binding,plan))
    from app.world_relief import td_resident
    monkeypatch.setattr(td_resident,'read_plate',lambda *args:(None,dict(identity='c'*64,config=dict(world_seed=20260903))))
    from app.world_gen import ocean_island_adapter
    monkeypatch.setattr(ocean_island_adapter,'load_binding',lambda *args:binding)
    opts=dict(source=tmp_path/'declared-source',product_path=tmp_path/'declared-islands',
        island_identity=product.identity,plan_path=path,plan_identity=plan.identity,out_root=tmp_path/'world',
        reason='Declared analytic large-island CPU mechanism test',available_bytes=8*2**30)
    return SimpleNamespace(plan=plan,product=product,binding=binding,options=opts)


def fail_gate(*args,**kwargs):
    raise AssertionError('GPU/model/memory path must not run')


def test_empty_and_dry_plan_never_touch_gpu_memory_model(declared,monkeypatch):
    monkeypatch.setattr(local30,'memory_gate',fail_gate)
    monkeypatch.setattr(local30,'gpu_gate',fail_gate)
    monkeypatch.setattr(local30,'_default_generator',fail_gate)
    report=adapter.prepare_mountains(**declared.options,dry_run=True,generator_factory=fail_gate)
    assert report['tiles_to_prepare'] and not report['model_started']
    empty=analyze_island_mountains(declared.product,IslandMountainConfig(min_area_km2=10000))
    monkeypatch.setattr(adapter,'load_plan',lambda *args:(declared.binding,empty))
    report=adapter.prepare_mountains(**declared.options,generator_factory=fail_gate)
    assert report['empty'] and report['generator_factory_calls']==0
    assert not Path(declared.options['out_root']).exists()


def test_single_cpu_generator_raw_immutable_derived_coast_lineage_reuse_and_stale(declared,monkeypatch):
    calls=[];factories=[]
    def factory():
        factories.append(1)
        def generate(origin,side):
            calls.append(origin)
            x=(origin[0]+np.arange(side)[None,:])*30.
            z=(origin[1]+np.arange(side)[:,None])*30.
            return (1000.+.01*x+.02*z).astype(np.float32)
        return generate
    monkeypatch.setattr(local30,'gpu_gate',fail_gate)
    selected=[(0,0),(1,0),(2,0)]
    report=adapter.prepare_mountains(**declared.options,tile_indices=selected,generator_factory=factory)
    assert len(factories)==1 and len(calls)==3 and not report['model_started']
    assert report['generator_factory_calls']==1
    snapshots={}
    surfaces=[]
    for row in report['products']:
        rm=Path(row['raw_manifest']);dm=Path(row['derived_manifest'])
        raw=json.loads(rm.read_text());derived=json.loads(dm.read_text())
        raw_file=rm.parent/raw['layers']['elevation_m']['file'];snapshots[str(raw_file)]=raw_file.read_bytes()
        assert raw['generator']['kind']=='fake/injected'
        assert derived['lineage']==['c'*64,declared.product.identity,declared.plan.identity]
        assert derived['mountain_binding']['raw_identity']==raw['identity']
        assert 'mountain_plan_identity' not in raw
        h=np.load(dm.parent/derived['layers']['elevation_m']['file']);surfaces.append(h)
        tile=derived['tile'];x=tile['first_sample_xz_m'][0]+np.arange(513)[None,:]*30
        z=tile['first_sample_xz_m'][1]+np.arange(513)[:,None]*30
        w=sample_mountain_weights(declared.plan,declared.product,x,z)
        base=declared.product.query(x,z)['elevation_m'].astype(np.float32)
        decoded=np.load(raw_file)
        expected=(base+w*(np.maximum(decoded,2.)-base)).astype(np.float32)
        np.testing.assert_array_equal(h,expected)
        np.testing.assert_array_equal(h[w==0],base[w==0])
        derived_root=dm.parents[2]
        kw=dict(plate_identity='c'*64,island_identity=declared.product.identity,
                island_condition_policy=declared.binding.record['condition_policy'])
        assert local30.tile_state(derived_root,row['tile'],**kw)['status']=='stale'
        assert local30.tile_state(derived_root,row['tile'],**kw,mountain_plan_identity=declared.plan.identity,
                                  mountain_blend_policy='changed')['status']=='stale'
        assert local30.tile_state(derived_root,row['tile'],**kw,mountain_plan_identity=declared.plan.identity,
                                  mountain_blend_policy=declared.plan.manifest['blend_policy'])['status']=='prepared'
    np.testing.assert_array_equal(surfaces[0][:,-1],surfaces[1][:,0])
    np.testing.assert_array_equal(surfaces[1][:,-1],surfaces[2][:,0])
    again=adapter.prepare_mountains(**declared.options,tile_indices=selected,generator_factory=fail_gate)
    assert again['generator_factory_calls']==0
    with pytest.raises(local30.StaleTile,match='injected'):
        adapter.prepare_mountains(**declared.options,tile_indices=selected)
    from terrain_pipeline.island_mountains import IslandMountainPlan,identity
    m=declared.plan.manifest;m['config']['min_area_km2']=3000
    m['identity']=identity({k:v for k,v in m.items() if k!='identity'})
    changed=IslandMountainPlan(m,declared.plan.selected_interior,declared.plan.coast_distance_m,declared.plan.interior_distance_m)
    assert not changed.empty and changed.identity!=declared.plan.identity
    path=Path(declared.options['plan_path']).with_name('changed-plan.npz')
    np.savez_compressed(path,manifest_json=np.array(json.dumps(changed.manifest)),selected_interior=changed.selected_interior,
        coast_distance_m=changed.coast_distance_m,interior_distance_m=changed.interior_distance_m)
    monkeypatch.setattr(adapter,'load_plan',lambda *args:(declared.binding,changed))
    options=dict(declared.options,plan_path=path,plan_identity=changed.identity)
    changed_report=adapter.prepare_mountains(**options,tile_indices=selected,generator_factory=fail_gate)
    assert changed_report['generator_factory_calls']==0
    assert changed_report['products'][0]['raw_identity']==report['products'][0]['raw_identity']
    assert changed_report['products'][0]['derived_identity']!=report['products'][0]['derived_identity']
    for path,data in snapshots.items():
        assert Path(path).read_bytes()==data


def test_default_dispatch_uses_one_existing_local30_factory_and_gates(declared,monkeypatch):
    calls=[];gate=[]
    monkeypatch.setattr(local30,'gpu_gate',lambda:gate.append('gpu'))
    def existing(source,root,**kwargs):
        assert Path(root).resolve()==TG.resolve()
        assert (Path(root)/'terrain_pipeline/ocean_islands.py').is_file()
        assert source==declared.options['source']
        assert kwargs==dict(island_product_path=declared.options['product_path'],
            expected_island_identity=declared.product.identity,skeleton_run_path=None)
        calls.append((root,kwargs))
        def _gpu_generate(origin,side):return np.full((side,side),1200.,np.float32)
        return _gpu_generate
    monkeypatch.setattr(local30,'_default_generator',existing)
    report=adapter.prepare_mountains(**declared.options,tile_indices=[(0,0),(1,0)])
    assert len(calls)==len(gate)==1 and report['model_started']
    assert calls[0][1]['expected_island_identity']==declared.product.identity
    for row in report['products']:
        raw=json.loads(Path(row['raw_manifest']).read_text())
        assert raw['generator']['kind']=='terragenesis-gpu'


def test_real_tool_main_dispatches_plan_without_gpu(declared,monkeypatch,tmp_path):
    tool=Path(__file__).resolve().parents[1]/'tools/prepare_island_mountains.py'
    spec=importlib.util.spec_from_file_location('declared_mountain_tool',tool)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    monkeypatch.setattr(local30,'gpu_gate',fail_gate)
    monkeypatch.setattr(local30,'memory_gate',fail_gate)
    report=tmp_path/'report.json'
    result=module.main(['--skeleton',str(declared.options['source']),
        '--island-product-path',str(declared.options['product_path']),
        '--expected-island-identity',declared.product.identity,'--plan',str(declared.options['plan_path']),
        '--expected-plan-identity',declared.plan.identity,'--out-root',str(tmp_path/'unused'),
        '--reason','Declared fixture CLI dry task','--dry-run','--report',str(report)])
    assert result==0 and json.loads(report.read_text())['tiles_to_prepare']


def test_actual_frozen_source_binding_empty_default_plan_no_gpu(frozen,tmp_path,monkeypatch):
    # This is the strict frozen synthetic source/product from the real adapter
    # integration fixture, with normal production thresholds, never enlarged.
    plan=analyze_island_mountains(frozen.disabled)
    assert plan.empty
    path=tmp_path/'actual-empty-plan.npz';save_mountain_plan(plan,path)
    monkeypatch.setattr(local30,'memory_gate',fail_gate)
    monkeypatch.setattr(local30,'gpu_gate',fail_gate)
    monkeypatch.setattr(local30,'_default_generator',fail_gate)
    report=adapter.prepare_mountains(source=frozen.source_path,product_path=frozen.disabled_path,
        island_identity=frozen.disabled.identity,plan_path=path,plan_identity=plan.identity,
        skeleton_run=frozen.run_path,out_root=tmp_path/'not-created',reason='Actual strict binding empty-plan CPU test')
    assert report['empty'] and not report['products'] and not report['model_started']
    assert not (tmp_path/'not-created').exists()
