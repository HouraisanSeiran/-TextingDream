import json
import numpy as np
import pytest
from app.world_relief.source import load_source, identity, spatial_noise, subseed
from app.world_relief.tectonic_uplift import uplift_field
from app.world_relief.drainage import ocean_mask, route, river_lines
from app.world_relief.erosion import evolve


def test_convergence_only():
    plate=np.zeros((12,12),int);plate[:,6:]=1
    thick=np.full(plate.shape,35000.);cf=np.ones(plate.shape)
    convergent,_=uplift_field(plate,np.array([[100.,0],[-100.,0]]),thick,cf,1000)
    divergent,_=uplift_field(plate,np.array([[-100.,0],[100.,0]]),thick,cf,1000)
    transform,_=uplift_field(plate,np.array([[0.,100.],[0.,-100.]]),thick,cf,1000)
    assert convergent.max()>0
    assert np.all(divergent==0) and np.all(transform==0)


def test_inland_negative_is_not_ocean():
    h=np.full((15,15),100.);h[0,:]=-10;h[7,7]=-200
    ocean=ocean_mask(h)
    assert ocean[0,7] and not ocean[7,7]
    flow=route(h,ocean,1000)
    assert flow['closed_mask'][7,7]


def test_erosion_depressions_and_acyclic_flow():
    z,x=np.indices((28,32));h=500-np.hypot(z-14,x-16)*10
    h[10:14,12:16]-=200
    ocean=np.zeros(h.shape,bool)
    bed,flow=evolve(h,ocean,np.zeros(h.shape),1000,steps=3)
    order=flow['order'];rank=np.empty(h.size,int);rank[order]=np.arange(h.size)
    rec=flow['receiver'];active=rec!=np.arange(h.size)
    assert np.all(rank[rec[active]]<rank[active])
    assert np.all(flow['closed_mask'][(flow['filled_m']-bed)>1e-5])
    assert flow['area_m2'].max()>=1e6


def test_repeatability_and_coordinate_sampling():
    seed=subseed(20260903,'relief-8km')
    a=spatial_noise((24,24),(-11500.,-11500.),1000,seed,8000)
    b=spatial_noise((12,12),(-7500.,-6500.),1000,seed,8000)
    assert np.array_equal(a[5:17,4:16],b)
    results=[]
    for _ in range(2):
        bed,flow=evolve(500+a*50,np.zeros(a.shape,bool),np.zeros(a.shape),1000,steps=2)
        results.append((bed.tobytes(),flow['receiver'].tobytes(),json.dumps(river_lines(flow,np.zeros(a.shape,bool),(-11500,-11500),1000,2e6))))
    assert results[0]==results[1]


def test_bad_source_identity_refused(tmp_path):
    m=dict(identity='bad',arrays={},config={})
    p=tmp_path/'bad.npz';np.savez(p,manifest_json=np.array(json.dumps(m)))
    with pytest.raises(ValueError,match='identity'):
        load_source(p)


def test_river_connections_and_area_conservation():
    z,x=np.indices((20,22));h=(20-z)*10+abs(x-11)*4
    flow=route(h,np.zeros(h.shape,bool),1000)
    rec=flow['receiver'];outlets=rec==np.arange(h.size)
    assert np.isclose(flow['area_m2'].ravel()[outlets].sum(),h.size*1e6)
    lines=river_lines(flow,np.zeros(h.shape,bool),(500,500),1000,3e6)
    byid={line['id']:line for line in lines}
    for line in lines:
        if line['downstream_id']:
            target=byid[line['downstream_id']]
            assert line['id'] in target['upstream_ids']
            assert line['coordinates_xz_m'][-1]==target['coordinates_xz_m'][0]


def test_sea_level_base_and_closed_bed_preserved():
    z,x=np.indices((15,15));h=100+(14-z)*30+abs(x-7)*4.
    h[-1,:]=-4000
    ocean=np.zeros(h.shape,bool);ocean[-1,:]=True
    h[5,5]=-100
    before=h.copy()
    bed,flow=evolve(h,ocean,np.zeros(h.shape),1000,steps=2,diffusivity=0)
    assert np.array_equal(bed[ocean],before[ocean])
    assert bed[5,5]==before[5,5]
    assert np.all(bed[(~ocean)&(before>0)]>=0)


def test_river_uses_lake_surface_not_lake_bed():
    h=np.full((9,9),100.);h[4,4]=-2000;h[3,4]=150;h[0,:]=0
    bed,flow=evolve(h,np.zeros(h.shape,bool),np.zeros(h.shape),1000,steps=1,k=1,diffusivity=0)
    assert bed[4,4]==-2000
    assert bed[3,4]>=99.9


def test_connected_negative_coast_is_ocean_four_neighbors():
    from scipy import ndimage
    h=np.full((30,40),400.)
    h[:,:8]=-2400;h[10:15,8:20]=-500;h[20,25]=-800
    ocean=ocean_mask(h)
    adjacent=ndimage.binary_dilation(ocean,structure=ndimage.generate_binary_structure(2,1))&~ocean
    assert not np.any(h[adjacent]<0)
    assert np.all(ocean[10:15,8:20])
    assert not ocean[20,25]
    diagonal=np.ones((5,5));diagonal[0,0]=-1;diagonal[1,1]=-1
    assert not ocean_mask(diagonal)[1,1]


def test_v2_morphology_repeatable_curved_and_coast_preserved():
    from app.world_relief.morphology import initial_surface
    z,x=np.indices((80,96));base=1000+3000*np.exp(-((x-45)/5)**2)
    ocean=np.zeros(base.shape,bool);ocean[:,0:5]=True;base[ocean]=-1000
    uplift=np.exp(-((x-45)/5)**2)*.3
    args=(base,uplift,np.full(base.shape,40000.),ocean,(-47500,-39500),1000)
    a,rate,seeds,parameters=initial_surface(*args)
    b,rate_b,seeds_b,_=initial_surface(*args)
    assert a.tobytes()==b.tobytes() and rate.tobytes()==rate_b.tobytes()
    assert np.array_equal(a[ocean],base[ocean])
    assert np.std(a[10:70,65:90])>10
    peaks=np.argmax(a[:,25:65],axis=1)
    assert np.ptp(peaks)>3
    assert len(seeds)==10 and seeds==seeds_b


def test_direction_diagnostics_report_d8_constraint():
    from app.world_relief.diagnostics import mountain_directions
    z,x=np.indices((50,50));h=5000-z*30+abs(x-25)*40
    flow=route(h,np.zeros(h.shape,bool),1000)
    stats=mountain_directions(h,flow['receiver'],flow['area_m2'],1000)
    assert stats['single_step_grid_angles_fraction']==1
    assert stats['mountain_channel_cells']>0
    assert 0<=stats['ten_cell_reach_within_5deg_of_grid_angles_fraction']<=1


def test_mfd_conservation_dispersal_and_repeatability():
    z,x=np.indices((36,40));h=4000-z*30+abs(x-20)*4
    ocean=np.zeros(h.shape,bool)
    a=route(h,ocean,1000,'mfd');b=route(h,ocean,1000,'mfd')
    rec=a['receiver'];outlets=rec==np.arange(h.size)
    assert np.isclose(a['area_m2'].ravel()[outlets].sum(),h.size*1e6)
    assert a['area_m2'].tobytes()==b['area_m2'].tobytes()
    d8=route(h,ocean,1000)
    assert not np.array_equal(a['area_m2'],d8['area_m2'])
    lines=river_lines(a,ocean,(500,500),1000,3e6)
    byid={line['id']:line for line in lines}
    for line in lines:
        if line['downstream_id']:
            assert line['id'] in byid[line['downstream_id']]['upstream_ids']
