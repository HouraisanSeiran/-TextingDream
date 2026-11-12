"""Tiny monthly replay, no original products/world solve."""
from types import SimpleNamespace
import numpy as np
import pytest

from app.world_gen import csr_reservoir_year as year
from app.world_gen.climate_lake_stage import land_bucket_step


def mesh(n):
    rows = [[j for j in (i-1,i+1) if 0 <= j < n] for i in range(n)]
    return SimpleNamespace(indptr=np.r_[0,np.cumsum([len(r) for r in rows])],
        indices=np.array([j for r in rows for j in r],np.int64),
        node_x_m=np.arange(n,dtype=float),node_z_m=np.zeros(n))


def parameters(shape, capacity=0., infiltration=0., et=1.):
    return dict(soil_capacity_mm=np.full(shape,capacity), infiltration_fraction=np.full(shape,infiltration),
                quickflow_fraction=np.full(shape,1.-infiltration),et_fraction=np.full(shape,et))


def run(bed, liquid, pet=None, params=None, ocean=None):
    bed=np.array([bed],float)
    ocean=np.zeros_like(bed,bool) if ocean is None else np.array([ocean],bool)
    net=year.build_network(bed,mesh(bed.size),ocean,finite_boundary=False,area_m2=1.)
    rain=np.zeros((12,)+bed.shape); rain[:len(liquid),0]=liquid
    evap=np.zeros_like(rain) if pet is None else np.broadcast_to(pet,rain.shape).copy()
    result=year.compute_year(net,rain,evap,parameters(bed.shape) if params is None else params,~ocean)
    for account in result['accounts']:
        assert account['residual_m3']==pytest.approx(0.,abs=1e-8)
    np.testing.assert_allclose(result['arrays']['lake_depth_m'],result['arrays']['lake_stage_m']-bed)
    return net,result


def test_three_sink_receiving_chain_and_dry_equal_saddle():
    _,r=run([0,3,0,2,0],[[4000,0,0,0,0]])
    assert r['arrays']['lake_volume_m3'][0,0,2]>0
    assert r['arrays']['lake_volume_m3'][0,0,4]==0
    _,r=run([0,2,0,2,0],[[0,0,0,0,3000]])
    assert r['arrays']['lake_volume_m3'][0,0,0]==0
    assert 0<r['arrays']['lake_volume_m3'][0,0,2]<2
    assert r['hydraulic_ready'] is False
    assert r['natural_outlet_verified'] is False


def test_month_start_owner_local_et_and_no_created_sources():
    _,r=run([0,2,0],[[1000,0,0]],pet=1000.)
    assert r['accounts'][0]['lake_et_m3']==0
    assert r['accounts'][1]['lake_et_m3']==pytest.approx(1.)
    assert r['accounts'][-1]['final_lake_m3']==0
    assert sum(a['liquid_input_m3'] for a in r['accounts'])==1.


def test_inundated_soil_is_internal_transfer_without_second_dt(monkeypatch):
    params=parameters((1,3),capacity=500.,infiltration=.5)
    from app.world_gen.csr_reservoir_adapter import CSRReservoirs
    original=CSRReservoirs.advance
    calls=[]
    def counted(self,*args,**kwargs):
        calls.append(args[2]); return original(self,*args,**kwargs)
    monkeypatch.setattr(CSRReservoirs,'advance',counted)
    _,r=run([0,3,0],[[1000,0,0]],params=params)
    assert len(calls)==12
    assert r['accounts'][0]['soil_transfer_m3']==pytest.approx(.5)
    assert r['accounts'][0]['final_lake_m3']==pytest.approx(1.)
    assert r['arrays']['soil_mm'][0].sum()==0


def test_no_reservoirs_matches_stateful_land_bucket():
    params=parameters((1,3),capacity=200.,infiltration=1.)
    _,r=run([3,2,1],[[100,50,20]],pet=10.,params=params,ocean=[False,False,True])
    soil=np.zeros((1,3)); land=np.array([[True,True,False]])
    for m in range(12):
        rain=np.array([[100,50,20.]]) if m==0 else np.zeros((1,3))
        bucket=land_bucket_step(rain,np.full((1,3),10.),params,land,soil)
        np.testing.assert_allclose(r['arrays']['runoff_mm'][m],bucket['runoff_mm'])
        np.testing.assert_allclose(r['arrays']['land_actual_et_mm'][m],bucket['actual_et_mm'])
        soil=bucket['soil_mm']
    assert not r['arrays']['wet_mask'].any()
    assert r['accounts'][-1]['final_lake_m3']==0.


def test_stream_sink_and_progress_have_exact_twelve_intervals():
    bed=np.array([[0.,2.,0.]])
    net=year.build_network(bed,mesh(3),np.zeros_like(bed,bool),finite_boundary=False)
    saved=[]; progress=[]
    result=year.compute_year(net,np.zeros((12,1,3)),np.zeros((12,1,3)),parameters((1,3)),
        np.ones((1,3),bool),output_sink=lambda m,v:saved.append((m,set(v))),progress=progress.append)
    assert not result['arrays']
    assert len(saved)==len(progress)==12
    assert progress[-1]['month']==12
    assert all(p['owner_count']==2 for p in progress)
    assert len(result['face_ledgers'])==12


def test_owner_budget_rejects_without_dropping_sink():
    with pytest.raises(ValueError,match='owner budget'):
        year.build_network(np.array([[0.,2.,0.]]),mesh(3),np.zeros((1,3),bool),finite_boundary=False,max_owners=1)


def test_prepare_writes_new_sidecar_and_preserves_saved_inputs(tmp_path, monkeypatch):
    from app.world_gen import graph_hydro as gh, world_climate_adapter as adapter
    shape=(1,3); bed=np.array([[0.,3.,0.]])
    source_dir,climate_dir,hydro_dir=[tmp_path/name for name in ('source','climate','hydro')]
    for root in (source_dir,climate_dir,hydro_dir):
        root.mkdir()
    saved={}
    fields={}
    for name in ('monthly_liquid_input_mm','monthly_snow_swe_mm','monthly_ice_swe_mm'):
        data=np.zeros((12,)+shape)
        if name=='monthly_liquid_input_mm':
            data[0,0,0]=1000.
        np.save(hydro_dir/(name+'.npy'),data)
        saved[name]=data; fields[name]=dict(file=name+'.npy')
    before={p.name:p.read_bytes() for p in hydro_dir.iterdir()}
    source=dict(elevation_m=bed,ocean_mask=np.zeros(shape,bool),registered_lagoon=np.zeros(shape,bool),
                receiver=np.array([[-1,0,-1]]),first_xz_m=[0.,0.],spacing_m=1.)
    view=SimpleNamespace(product=climate_dir,fields={'monthly_pet_mm':{}},query=lambda names:dict(arrays=parameters(shape)))
    hydro=dict(identity='h',fields=fields,binding={})
    monkeypatch.setattr(year,'_saved_inputs',lambda *args,**kwargs:(source,view,hydro,saved if kwargs.get('monthly') else {}))
    monkeypatch.setattr(gh,'build_graph',lambda *args:mesh(3))
    monkeypatch.setattr(adapter,'_saved_array',lambda *args:np.zeros((12,)+shape))
    # Deliberately fail display extraction AFTER all physical months are saved.
    from app.world_gen import river_flow_network as flow
    original_builder=flow.build_flow_network
    def fail_display(*args,**kwargs):
        raise ValueError('forced display-only failure')
    monkeypatch.setattr(flow,'build_flow_network',fail_display)
    with pytest.raises(ValueError,match='display-only'):
        year.prepare(source_dir,climate_dir,hydro_dir,tmp_path/'failed',expected_source_identity='s',
            expected_climate_identity='c',expected_hydrology_identity='h',finite_boundary=False)
    checkpoint=tmp_path/'failed.months-checkpoint'
    import json
    status=json.loads((checkpoint/'checkpoint.json').read_text())
    assert status['status']=='monthly-complete-not-finalized'
    assert status['months_complete']==12
    assert not (checkpoint/'manifest.json').exists()
    physical_before={p.name:p.read_bytes() for p in checkpoint.iterdir()}
    monkeypatch.setattr(flow,'build_flow_network',original_builder)
    def forbidden_physics(*args,**kwargs):
        raise AssertionError('physics rerun during finalize')
    with monkeypatch.context() as context:
        context.setattr(year,'compute_year',forbidden_physics)
        resumed=year.finalize_checkpoint(checkpoint,tmp_path/'resumed',min_display_area_m2=1e12,
            display_policy='fixture explicit display scale')
    assert resumed['river_parameters']['min_display_area_m2']==1e12
    assert all((checkpoint/name).read_bytes()==data for name,data in physical_before.items())
    result=year.prepare(source_dir,climate_dir,hydro_dir,tmp_path/'out',expected_source_identity='s',
        expected_climate_identity='c',expected_hydrology_identity='h',finite_boundary=False)
    assert result['geometry_version']==year.VERSION
    assert result['face_ledger_file']=='csr-face-ledger.json'
    assert result['topology_file']=='csr-topology.json'
    assert (tmp_path/'out'/'manifest.json').is_file()
    assert (tmp_path/'out.months-checkpoint'/'checkpoint.json').is_file()
    for name in result['fields']:
        assert (tmp_path/'resumed'/(name+'.npy')).read_bytes()==(tmp_path/'out'/(name+'.npy')).read_bytes()
    assert (tmp_path/'resumed'/'water-budget.json').read_bytes()==(tmp_path/'out'/'water-budget.json').read_bytes()
    assert all((hydro_dir/name).read_bytes()==data for name,data in before.items())
    for name in saved:
        assert (tmp_path/'out'/(name+'.npy')).read_bytes()==before[name+'.npy']


def test_open_owner_recession_near_zero_longtail():
    params=parameters((1,3),capacity=20.,infiltration=.6)
    _,r=run([3,2,1],[[100,50,20]],pet=10.,params=params,ocean=[False,False,True])
    assert r['accounts'][-1]['final_lake_m3'] >= 0.
    assert r['accounts'][-1]['final_lake_m3'] < 1e-8
    assert all(np.min(ledger['owner_final_m3'])>=0 for ledger in r['face_ledgers'])
