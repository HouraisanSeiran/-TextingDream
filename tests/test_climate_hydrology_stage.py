"""Small saved-source fixture, native snow/bucket/routing, dynamic-export TEST DOUBLE.

No real-world climate or real glacier region is run. Most failure controls replace
the dynamic exporter; one small synthetic test uses the approved native export API.
"""
import hashlib
import json

import numpy as np
import pytest

from app import terrain_source as ts
from app.world_gen import climate_world_stage as cs, climate_hydrology_stage as hs
from tests.test_climate_world_stage import world_map


@pytest.fixture
def saved(tmp_path,request):
    root, _ = world_map(tmp_path)
    path = root/'manifest.json'
    manifest = json.loads(path.read_text(encoding='utf-8'))
    h = np.full((8,8),np.nan); h[1:6,4:8] = 0.; h[3,6] = .1
    np.save(root/'old_H.npy',h,allow_pickle=False)
    manifest['layers']['glacier_ice_thickness_m'] = dict(file='old_H.npy',sha256=cs._sha(root/'old_H.npy'),
        dtype='float64',unit='m',meaning='old bound H only',nodata=None)
    manifest['glacier_regions'] = [dict(identity='old-fixture',window_zx=[1,4,6,8],boundary='closed',
        edge_ice=dict(closed_edge_zero=True),completed_years=20,target_years=20,
        cumulative_melt_water_m3=1e30,pending_melt_water_m3=1e30)]
    manifest.pop('identity')
    manifest['identity'] = hashlib.sha256(ts._canon(manifest).encode()).hexdigest()
    path.write_text(json.dumps(manifest),encoding='utf-8')
    source = cs.climate_source_from_map(root,expected_identity=manifest['identity'])
    temperatures = [[5.]*3]*12 if getattr(request,'param',False) else [[-5.]*3]*6+[[5.]*3]*6
    ref = dict(schema='terragenesis-climate-reference-v1',latitude_deg=[-80.,0.,80.],
        monthly_zonal_sst_c=temperatures,reference_period='synthetic fixture')
    climate_root = tmp_path/'climate'
    climate = cs.prepare(source,climate_root,dict(reference_air_offset_c=0.,
        diagnostic=dict(land_season_amplitude_c=0.,lapse_rate_c_per_m=0.)),ref)
    options = dict(expected_source_identity=manifest['identity'],expected_climate_identity=climate['identity'])
    return root,climate_root,options,[dict(window_zx=[1,4,6,8],old_identity='old-fixture')]


@pytest.fixture
def dynamic_double(monkeypatch):
    cs.climate_module()
    from terrain_pipeline import world_glacier, world_environment
    calls = []
    def double(geometry,t,p,state=None,*,target_years,snow_config=None,config=None,export_monthly=False):
        assert state is None and target_years == 1 and export_monthly is True
        assert config['outflow_sides'] == []
        calls.append(dict(geometry=geometry,t=t.copy(),p=p.copy()))
        result = world_environment.diagnostic_snow_ice(t,p,ocean_mask=np.zeros(t.shape[1:],bool),
            initial_ice_swe_mm=geometry['ice_thickness_m']*917.)
        a = result['arrays']; area = geometry['dx_m']*geometry['dz_m']
        export = dict(rain_water_m3=a['monthly_rainfall_mm']*area/1000.,
            snow_melt_water_m3=a['monthly_snow_melt_mm']*area/1000.,
            ice_melt_water_m3=a['monthly_ice_melt_mm']*area/1000.,
            snow_water_m=a['monthly_snow_swe_mm']/1000.,
            ice_thickness_m=a['monthly_ice_swe_mm']/917.,
            year=np.ones(12,int),month=np.arange(1,13),start_month_index=0,stop_month_index=12)
        return dict(monthly_export=export,metadata=dict(completed=True,completed_years=1,
            parameters=dict(ice_density_kg_m3=917.),model_identity='test-double-not-native'),
            ledger=dict(boundary_ice_out_m3=0.,water_residual_m3=0.))
    monkeypatch.setattr(world_glacier,'generate_climate_slope_glacier',double)
    return calls,double


def test_plan_static_only_and_resource_estimate(saved,monkeypatch):
    root,climate,options,regions = saved
    def forbid(*args,**kwargs):
        raise AssertionError('plan does not read monthly arrays or solve snow/ice')
    monkeypatch.setattr(hs.SavedClimateMap,'query',forbid)
    p = hs.plan(root,climate,regions,**options)
    assert p['status'] == 'ready' and p['region_count'] == 1 and p['region_cells'] == 20
    assert p['estimated_peak_increment_bytes'] > 128*2**20
    assert p['calendar'] == 'noleap365' and p['terrain_evolution'] is False


def test_monthly_snow_liquid_replacement_single_bucket_saved_receivers_units(saved,dynamic_double,tmp_path,monkeypatch):
    root,climate,options,regions = saved
    calls,_ = dynamic_double
    native = cs.climate_module()
    counts = []
    bucket = native._monthly_land_bucket
    def counted(*args,**kwargs):
        counts.append(1); return bucket(*args,**kwargs)
    monkeypatch.setattr(native,'_monthly_land_bucket',counted)
    queries=[]
    query = hs.SavedClimateMap.query
    def tracked(self,fields,*args,**kwargs):
        assert not {'monthly_runoff_mm','monthly_actual_et_mm','monthly_soil_water_mm'} & set(fields)
        queries.append(fields)
        return query(self,fields,*args,**kwargs)
    monkeypatch.setattr(hs.SavedClimateMap,'query',tracked)
    out = tmp_path/'sidecar'
    m = hs.prepare(root,climate,regions,out,**options)
    assert counts == [1] and len(calls) == 1
    np.testing.assert_array_equal(calls[0]['geometry']['bed_m'],np.load(root/'elevation_m.npy')[1:6,4:8])
    assert m['schema'] == hs.SCHEMA and m['schema'] != native.SCHEMA
    assert m['calendar'] == 'noleap365' and sum(m['month_days']) == 365
    assert m['fields']['monthly_discharge_m3_s']['units']=='m3/s'
    assert m['fields']['monthly_liquid_input_mm']['units']=='mm/month'
    assert m['fields']['monthly_ice_swe_mm']['units']=='mm'
    assert m['binding']['regions'][0]['old_identity'] == 'old-fixture'
    read = lambda name:np.load(out/(name+'.npy'))
    liquid = read('monthly_liquid_input_mm')
    assert np.count_nonzero(liquid[:6]) == 0  # cold rain becomes SWE, not bucket rain
    p = np.load(climate/'monthly_precipitation_mm.npy').astype(float)
    # Full-year handoff = P + initial H melt - terminal snow/ice; never + old melt/pending.
    land = np.load(root/'status.npy') != 3
    initial = read('initial_ice_swe_mm')
    np.testing.assert_allclose(liquid.sum(0),np.where(land,p.sum(0),0)+initial-
        read('final_snow_swe_mm')-read('final_ice_swe_mm'),atol=1e-10)
    assert initial.sum() == pytest.approx(91.7)
    assert liquid.max() < 1e6
    volume,Q = read('monthly_routed_volume_m3'),read('monthly_discharge_m3_s')
    np.testing.assert_allclose(Q*hs.MONTH_DAYS[:,None,None]*86400.,volume,rtol=1e-14)
    rec = np.load(root/'receiver.npy').ravel(); runoff=read('monthly_runoff_mm')
    for month in range(12):
        local = runoff[month].ravel()*1e8/1000.
        expected=local.copy()
        for i in range(63,0,-1):
            expected[rec[i]] += expected[i]
        np.testing.assert_allclose(volume[month].ravel(),expected,rtol=1e-14)
        assert volume[month].ravel()[rec<0].sum() == pytest.approx(local.sum())
    for name in ('surface-budget','snow-ice-budget','routing-budget'):
        account=json.loads((out/(name+'.json')).read_text())
        assert np.max(abs(np.asarray(account['monthly_residual_m3']))) < .01
    assert not list(tmp_path.glob('.climate-hydrology-*'))


def test_no_region_diagnostic_state_month_handoff(saved,tmp_path):
    root,climate,options,_=saved
    out=tmp_path/'no-regions'
    hs.prepare(root,climate,[],out,**options)
    snow=np.load(out/'monthly_snow_swe_mm.npy')
    assert snow[5].sum() > snow[0].sum() > 0
    assert np.load(out/'initial_ice_swe_mm.npy').sum() == 0
    assert np.load(out/'monthly_liquid_input_mm.npy')[:6].sum() == 0


@pytest.mark.parametrize('failure',['incomplete','edge','bad-month','bad-flux','bad-water-account'])
def test_failure_never_publishes_and_does_not_trim_ice(saved,dynamic_double,tmp_path,monkeypatch,failure):
    root,climate,options,regions=saved
    _,double=dynamic_double
    from terrain_pipeline import world_glacier
    def broken(*args,**kwargs):
        r=double(*args,**kwargs)
        if failure=='incomplete': r['metadata']['completed']=False
        elif failure=='edge': r['monthly_export']['ice_thickness_m'][3,0,0]=.01
        elif failure=='bad-month': r['monthly_export']['stop_month_index']=11
        elif failure=='bad-water-account': r['monthly_export']['rain_water_m3'][6,2,2]+=1e9
        else: r['monthly_export']['rain_water_m3'][0,0,0]=-1
        return r
    monkeypatch.setattr(world_glacier,'generate_climate_slope_glacier',broken)
    out=tmp_path/'rejected'
    with pytest.raises(ValueError): hs.prepare(root,climate,regions,out,**options)
    assert not out.exists() and not list(tmp_path.glob('.climate-hydrology-*'))


@pytest.mark.parametrize('change',['wrong-source','wrong-climate','wrong-old-id','overlap','memory','outflow'])
def test_source_binding_regions_and_budget_rejections(saved,dynamic_double,tmp_path,change):
    root,climate,options,regions=saved
    extra={}
    if change=='wrong-source':options['expected_source_identity']='f'*64
    elif change=='wrong-climate':options['expected_climate_identity']='f'*64
    elif change=='wrong-old-id':regions[0]['old_identity']='other'
    elif change=='overlap':regions=regions+regions
    elif change=='memory':extra['max_memory_bytes']=1
    else:extra['glacier_config']=dict(outflow_sides=['east'])
    out=tmp_path/'rejected'
    with pytest.raises(ValueError):hs.prepare(root,climate,regions,out,**options,**extra)
    assert not out.exists()


def test_actual_native_monthly_export_small_synthetic_year(saved,tmp_path,monkeypatch):
    root,climate,options,regions=saved
    cs.climate_module()
    from terrain_pipeline import world_glacier
    original=world_glacier.generate_climate_slope_glacier
    exports=[]
    def tracked(*args,**kwargs):
        result=original(*args,**kwargs)
        exports.append(result)
        return result
    monkeypatch.setattr(world_glacier,'generate_climate_slope_glacier',tracked)
    out=tmp_path/'actual-native-synthetic'
    # Native finite-window transport can put arbitrarily small positive H on
    # the edge. That is a real rejection, never a reason to silently trim ice.
    with pytest.raises(ValueError,match='reaches closed boundary'):
        hs.prepare(root,climate,regions,out,**options)
    assert len(exports)==1 and exports[0]['metadata']['completed'] is True
    export=exports[0]['monthly_export']
    assert export['ice_melt_water_m3'].sum()>0
    assert hs._edge_max(export['ice_thickness_m'])>0
    assert not out.exists()
    assert not list(tmp_path.glob('.climate-hydrology-*'))


@pytest.mark.parametrize('saved',[True],indirect=True)
def test_actual_native_warm_synthetic_export_replaces_not_adds(saved,tmp_path,monkeypatch):
    root,climate,options,regions=saved
    cs.climate_module()
    from terrain_pipeline import world_glacier
    original=world_glacier.generate_climate_slope_glacier
    exports=[]
    def tracked(*args,**kwargs):
        result=original(*args,**kwargs); exports.append(result); return result
    monkeypatch.setattr(world_glacier,'generate_climate_slope_glacier',tracked)
    out=tmp_path/'native-warm'
    hs.prepare(root,climate,regions,out,**options)
    e=exports[0]['monthly_export']
    np.testing.assert_array_equal(np.load(out/'monthly_liquid_input_mm.npy')[:,1:6,4:8],
        sum(e[k] for k in hs.FLUXES)*1000/1e8)
    assert e['ice_melt_water_m3'].sum()>0 and hs._edge_max(e['ice_thickness_m'])==0
    assert np.load(out/'initial_ice_swe_mm.npy').sum()==pytest.approx(91.7)
