"""CPU integration evidence: real qualification, scheduling, publication and map reads."""
import json
from pathlib import Path
import numpy as np
import pytest

from app.world_gen import web_island_stage as stage, island_mountains as mountains, local30, fast_relief as fr
from app.world_gen import ocean_island_adapter as islands
from app.map_source import load_source
import importlib.util
fixture_spec=importlib.util.spec_from_file_location('world_island_fixture',Path(__file__).with_name('test_ocean_island_integration.py'))
fixture_module=importlib.util.module_from_spec(fixture_spec);fixture_spec.loader.exec_module(fixture_module)
frozen,options=fixture_module.frozen,fixture_module.options


def frozen_input(frozen,tmp_path):
    api=mountains._api()
    plan=api.analyze_island_mountains(frozen.product)
    assert not plan.empty
    assert all(c['exposed_area_km2']>plan.manifest['config']['min_area_km2']
               for c in plan.manifest['components'] if c['accepted'])
    path=tmp_path/'plan.npz';api.save_mountain_plan(plan,path)
    binding=islands.load_binding(frozen.source_path,frozen.island_path,frozen.product.identity,frozen.run_path)
    record=dict(schema=stage.SCHEMA,policy=stage.POLICY,source=str(frozen.source_path),skeleton_run=str(frozen.run_path),
        island_product_path=str(frozen.island_path),island_identity=frozen.product.identity,binding=binding.record,
        analysis=dict(status='complete',spacing_m=1000.,pending=[]),
        plans=[dict(path=str(path),identity=plan.identity,sha256=islands.file_sha(path),empty=False,
                    grid=plan.manifest['grid'],blend_policy=plan.manifest['blend_policy'])],
        mountains=dict(status='not-scheduled',products=[]),imported_sha256=islands.file_sha(Path(api.__file__)))
    stage.write_record(tmp_path/'prepared.json',record)
    return plan


def fail(*args,**kwargs):raise AssertionError('CPU task entered GPU path')


def test_real_prepare_cpu_pending_and_no_gpu(frozen,tmp_path,monkeypatch):
    monkeypatch.setattr(local30,'gpu_gate',fail)
    monkeypatch.setattr(local30,'memory_gate',fail)
    monkeypatch.setattr(local30,'_default_generator',fail)
    stage.prepare(frozen.source_path,frozen.run_path,tmp_path/'islands',world_type='archipelago',world_seed=20260903)
    report=stage.schedule(tmp_path/'islands'/'prepared.json',tmp_path/'cpu',use_gpu=False)
    assert report['analysis']['status']=='complete' and report['plans']
    assert report['analysis']['qualification']=='actual exposed connected area strictly >25 km2; no width gate'
    assert report['binding']['ocean_quota']['status']=='bound'
    assert not report['mountains']['products'] and not report['mountains']['model_started']
    assert report['mountains']['status'] in ('pending-gpu','empty','partial')
    assert not (tmp_path/'cpu'/'tiles').exists()
    with pytest.raises(FileExistsError):
        stage.prepare(frozen.source_path,frozen.run_path,tmp_path/'islands',world_type='archipelago',world_seed=20260903)


def test_saved_td_changes_final_world_and_map_consumer(frozen,tmp_path,monkeypatch):
    plan=frozen_input(frozen,tmp_path)
    tiles,_=mountains.scheduled_tiles(plan)
    # Explicit bounded one-tile CPU injection exercises the actual raw and derived publishers.
    world_centres=-398000.+np.arange(200)*4000.
    def score(tile):
        x0,z0,x1,z1=tile['extent_m']
        x=world_centres[(world_centres>=x0)&(world_centres<=x1)]
        z=world_centres[(world_centres>=z0)&(world_centres<=z1)]
        if not len(x) or not len(z):return 0
        return int(np.count_nonzero(mountains._api().sample_mountain_weights(plan,frozen.product,x[None,:],z[:,None])>0))
    tile=max(tiles,key=score)
    assert score(tile)>0
    api=mountains._api()
    valid={(t['ix'],t['iz']) for t in tiles}
    candidates=[]
    for component in plan.manifest['selected_components']:
        needed=set(api.component_native_tiles(plan,component))
        if needed<=valid and any(score(t)>0 for t in tiles if (t['ix'],t['iz']) in needed):
            candidates.append(needed)
    selected=min(candidates,key=len)
    calls=[]
    def factory():
        calls.append('factory')
        return lambda origin,side:np.full((side,side),3500.,np.float32)
    monkeypatch.setattr(local30,'gpu_gate',fail)
    report=stage.schedule(tmp_path/'prepared.json',tmp_path/'td',use_gpu=True,generator_factory=factory,
                          available_bytes=8*2**30,tile_indices=sorted(selected))
    assert calls==['factory'] and report['mountains']['products']
    assert any(c['status']=='ready' for t in report['mountains']['tasks'] for c in t['peak_normalization']['components'])
    product=report['mountains']['products'][0]
    raw_manifest=Path(product['raw_manifest']);raw=json.loads(raw_manifest.read_text())
    raw_file=raw_manifest.parent/raw['layers']['elevation_m']['file'];before=raw_file.read_bytes()
    params=dict(spacing_m=4000.,erosion_iterations=1,smooth_rivers=False,breach_passes=1)
    plain=fr.compute(fr.load_skeleton(frozen.source_path),params,erosion=True,**options(frozen))
    out,manifest=fr.freeze(frozen.source_path,tmp_path/'final',params=params,erosion=True,min_free_bytes=1,
        log=lambda *_:None,mountain_input_path=tmp_path/'td'/'world-input.json',**options(frozen))
    data=manifest['island_mountains']
    assert data['nonzero_delta_cells']>0
    height=np.load(out/'elevation_m.npy')
    assert np.max(np.abs(height-plain['elevation']))>1
    assert manifest['algorithm_version'].endswith('+frozen-island-mountains-v3')
    assert data['record']['identity'] in manifest['lineage']
    src=load_source('world-map-product',out,expected_identity=manifest['identity'])
    atlas=load_source('world-relief-pilot',out,expected_identity=manifest['identity'])
    z,x=np.unravel_index(np.argmax(np.abs(height-plain['elevation'])),height.shape)
    grid=manifest['grid'];px=grid['first_sample_xz_m'][0]+x*grid['spacing_m'];pz=grid['first_sample_xz_m'][1]+z*grid['spacing_m']
    assert src.sample(px,pz)['elevation_m']==pytest.approx(float(height[z,x]))
    assert atlas.sample(px,pz)['elevation_m']==pytest.approx(float(height[z,x]))
    assert raw_file.read_bytes()==before
    # The published normalization remains part of the final-world input chain.
    dm=json.loads(Path(product['derived_manifest']).read_text())
    normalization_path=Path(dm['mountain_binding']['peak_normalization']['path'])
    normalization_bytes=normalization_path.read_bytes()
    normalization_path.write_bytes(normalization_bytes+b' ')
    with pytest.raises(ValueError,match='normalization SHA'):
        fr.compute(fr.load_skeleton(frozen.source_path),params,erosion=False,
                   mountain_input_path=tmp_path/'td'/'world-input.json',**options(frozen))
    normalization_path.write_bytes(normalization_bytes)
    with raw_file.open('ab') as stream:stream.write(b'tampered')
    with pytest.raises(ValueError,match='elevation SHA'):
        fr.compute(fr.load_skeleton(frozen.source_path),params,erosion=False,
                   mountain_input_path=tmp_path/'td'/'world-input.json',**options(frozen))
