import json
import numpy as np
import pytest
from app.world_relief.td_pages import block_mean, latent_lowfreq, stats, write_json, run_page


def test_block_mean_exact_and_rejects_truncation():
    a=np.arange(64,dtype=float).reshape(8,8)
    np.testing.assert_allclose(block_mean(a,4),[[13.5,17.5],[45.5,49.5]])
    with pytest.raises(ValueError):
        block_mean(a,3)
    a[0,0]=np.nan
    with pytest.raises(ValueError):
        block_mean(a,4)


def test_latent_channel_uses_signed_square_metre_transform():
    a=np.array([[-1,0,1]],dtype=np.float32)
    q=a*38.6-31.4
    np.testing.assert_allclose(latent_lowfreq(a),np.sign(q)*q*q,rtol=1e-6)
    assert latent_lowfreq(a)[0,0]<0


def test_difference_stats_sign_not_connected_ocean():
    a=np.array([[-2.,3.]])
    b=np.array([[2.,5.]])
    result=stats(a,b)
    assert result['mae_m']==3
    assert result['sign_agreement']==.5
    assert result['bias_m']==-3


def test_atomic_json_rejects_nan(tmp_path):
    p=tmp_path/'receipt.json'
    write_json(p,{'ok':True})
    assert json.loads(p.read_text())=={'ok':True}
    with pytest.raises(ValueError):
        write_json(p,{'bad':float('nan')})
    assert json.loads(p.read_text())=={'ok':True}


def test_run_page_refuses_invalid_window_without_torch(tmp_path):
    with pytest.raises(ValueError):
        run_page(tmp_path,tmp_path,(0,1),tmp_path/'output')
    with pytest.raises(ValueError):
        run_page(tmp_path,tmp_path,(0,0),tmp_path/'output',side=1344)


def test_four_neighbour_ocean_preserves_closed_negative():
    from app.world_relief.drainage import ocean_mask
    h=np.ones((5,5));h[0,0]=-1;h[1,1]=-1;h[3,3]=-1
    ocean=ocean_mask(h)
    assert ocean[0,0]
    assert not ocean[1,1] and not ocean[3,3]


def test_periodic_plate_sample_wraps_coordinates_not_output_domain():
    from app.world_relief.td_resident import sample_periodic
    a=np.arange(12,dtype=float).reshape(3,4)
    config=dict(origin_x_m=-20,origin_z_m=-15,cell_size_m=10)
    x=np.array([[-15,-5,5,15]],float)
    z=np.array([[-10],[0],[10]],float)
    np.testing.assert_allclose(sample_periodic(a,config,x,z),a)
    np.testing.assert_allclose(sample_periodic(a,config,x+40,z-30),a)
    # Crossing the edge interpolates periodically rather than clamping.
    assert sample_periodic(a,config,np.array([20.]),np.array([-10.]))[0]==1.5


def test_world_plan_is_finite_native_block_aligned_and_covers_positive_blend():
    from pathlib import Path
    from app.world_relief.td_resident import world_plan
    source=Path(__file__).resolve().parents[2]/'山川形意Terragenesis/.scratch/plate-formation-coast-20261101/shaped-run-v4/product.npz'
    if not source.exists():
        pytest.skip('frozen plate not installed')
    plan,h,w=world_plan(source)
    first=plan['first_sample_xz_m'];nz,nx=plan['shape_zx']
    x0,z0,x1,z1=plan['extent_bounds_m']
    assert x0<=first[0]<x1 and z0<=first[1]<z1
    assert first[0]+(nx-1)*960<x1 and first[1]+(nz-1)*960<z1
    assert plan['world_seed']==20261020
    assert 0<=w.min()<=w.max()<=1
    covered=np.zeros(h.shape,bool)
    for p in plan['pages']:
        z,x=p['grid_zx']
        assert all(v%32==0 for v in p['origin_native_xz'])
        covered[z:z+30,x:x+30]=True
    assert np.all(covered[w>0])
    assert np.all(w[h>=0]==1)


def test_resident_headroom_does_not_double_count_model_rss():
    from app.world_relief.td_resident import resident_headroom
    # 2GiB free is below cold-launch threshold but above page staging+1GiB.
    r=resident_headroom(2*2**30,3000,4096)
    assert r['required_host_bytes']==300_000_000+1024*1024*160+1024*2**20
    assert r['worker_rss_mib']==3000
    with pytest.raises(RuntimeError,match='insufficient'):
        resident_headroom(r['required_host_bytes']-1,3000,4096)
    with pytest.raises(RuntimeError,match='RSS budget'):
        resident_headroom(10*2**30,4097,4096)


def test_lake_pixel_edge_rings_preserve_hole():
    from app.world_relief.td_freeze import lake_vectors
    wet=np.ones((5,5),bool);wet[2,2]=False
    lakes=lake_vectors(wet,np.full((5,5),10.),[0,0],960)
    assert len(lakes)==1
    assert len(lakes[0]['holes_xz_m'])==1
    assert lakes[0]['ring_xz_m'][0]==lakes[0]['ring_xz_m'][-1]
    assert lakes[0]['area_m2']==24*960**2


def _mini_world(tmp_path):
    from app.world_relief.td_pages import write_json,file_sha
    nz,nx=60,60
    zz,xx=np.indices((62,62))
    h=(zz*3+xx*2-15).astype(np.float32)
    h[20:25,20:25]-=50
    np.save(tmp_path/'world-skeleton-960m.npy',h[:60,:60])
    np.save(tmp_path/'world-td-weight.npy',np.ones((60,60),np.float32))
    pages=[]
    for z in (0,30):
        for x in (0,30):
            page=dict(id=f'{z}-{x}',grid_zx=[z,x],origin_native_xz=[x*32,z*32],side_native=1024)
            pages.append(page)
            dest=tmp_path/'world-pages'/page['id'];dest.mkdir(parents=True)
            np.save(dest/'elevation_960m.npy',h[z:z+32,x:x+32])
            write_json(dest/'receipt.json',dict(plan_identity='test-plan',plate_identity='a'*64,
                files={'elevation_960m.npy':file_sha(dest/'elevation_960m.npy')},inference_seconds=1,
                peak_child_rss_mib=2000,allocated_peak_mib=1000,reserved_peak_mib=1456,
                preflight={'available_host_bytes':3*2**30}))
    from app.world_relief.source import identity
    plan=dict(plate_identity='a'*64,world_seed=17,
        algorithm='test-only',first_sample_xz_m=[465,465],shape_zx=[nz,nx],extent_bounds_m=[0,0,nx*960,nz*960],pages=pages)
    plan['plan_identity']=identity(plan)
    write_json(tmp_path/'world-plan.json',plan)
    for page in pages:
        dest=tmp_path/'world-pages'/page['id']
        receipt=json.loads((dest/'receipt.json').read_text())
        receipt.update(page)
        receipt.update({key:plan[key] for key in ('algorithm','world_seed','plan_identity')})
        write_json(dest/'receipt.json',receipt)
    write_json(tmp_path/'generation-summary.json',dict(completed_pages=4,total_pages=4))
    return h[:60,:60]


def test_freeze_complete_pages_routes_without_modifying_bed_and_loads_contract(tmp_path):
    from app.world_relief.td_freeze import freeze
    from app.map_source import load_source
    original=_mini_world(tmp_path)
    product,manifest=freeze(tmp_path)
    np.testing.assert_array_equal(np.load(product/'elevation_m.npy'),original)
    assert manifest['schema']=='td-world-960m-v1'
    source=load_source('world-map-product',product,expected_identity=manifest['identity'],expected_world_seed=17)
    assert source.info.schema=='td-world-960m-v1'
    assert source.sample(465,465)['status']==3
    assert source.sample(-100,465)['status']==1
    assert source.vectors('lakes')
    assert manifest['statistics']['overlap_max_abs_m']==0


def test_assembly_refuses_missing_or_corrupted_page(tmp_path):
    from app.world_relief.td_freeze import assemble
    _mini_world(tmp_path)
    path=tmp_path/'world-pages/0-0/elevation_960m.npy'
    a=np.load(path);a[0,0]+=1;np.save(path,a)
    with pytest.raises(ValueError,match='corrupt'):
        assemble(tmp_path)


def test_assembly_recomputes_plan_identity(tmp_path):
    from app.world_relief.td_freeze import assemble
    from app.world_relief.td_pages import write_json
    _mini_world(tmp_path)
    path=tmp_path/'world-plan.json';plan=json.loads(path.read_text())
    plan['first_sample_xz_m'][0]+=960
    write_json(path,plan)
    with pytest.raises(ValueError,match='plan identity'):
        assemble(tmp_path)


def test_assembly_rejects_receipt_wrong_seed_or_origin(tmp_path):
    from app.world_relief.td_freeze import assemble
    from app.world_relief.td_pages import write_json
    _mini_world(tmp_path)
    path=tmp_path/'world-pages/0-0/receipt.json';receipt=json.loads(path.read_text())
    receipt['world_seed']=18;write_json(path,receipt)
    with pytest.raises(ValueError,match='request/plan/source'):
        assemble(tmp_path)


def test_freeze_v2_identity_is_stable_across_runs_and_ignores_runtime_fields(tmp_path):
    from app.world_relief.td_freeze_v2 import freeze_v2
    from app.world_relief.td_pages import write_json
    from app.map_source import load_source
    original=_mini_world(tmp_path)
    _,m1=freeze_v2(tmp_path,out_name='v2-a')
    # change only run-time fields (timings / memory peaks) in the generation summary, then freeze again
    path=tmp_path/'generation-summary.json'
    summary=json.loads(path.read_text())
    summary.update(elapsed_seconds_this_invocation=123.4,sum_page_inference_seconds=99.9,peak_child_rss_mib=1.0)
    write_json(path,summary)
    _,m2=freeze_v2(tmp_path,out_name='v2-b')
    assert m1['identity']==m2['identity']
    assert m1['schema']=='td-world-960m-v2'
    np.testing.assert_array_equal(np.load(tmp_path/'v2-a'/'elevation_m.npy'),np.load(tmp_path/'v2-b'/'elevation_m.npy'))
    source=load_source('world-map-product',tmp_path/'v2-a',expected_identity=m1['identity'])
    assert source.info.schema=='td-world-960m-v2'
