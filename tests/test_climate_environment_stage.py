"""Small saved-product publication only; never publish a real climate candidate."""
import hashlib
import json

import numpy as np
import pytest

from app import terrain_source as ts
from app.map_source import load_source
from app.world_gen import climate_environment_stage as es, climate_hydrology_stage as hs
from app.world_gen import climate_world_stage as cs
from tests.test_climate_hydrology_stage import saved as climate_fixture, dynamic_double


@pytest.fixture
def prepared(climate_fixture,dynamic_double,tmp_path):
    source,climate,options,regions=climate_fixture
    m=json.loads((source/'manifest.json').read_text())
    vector_data=dict(rivers=dict(schema='rivers-v1',lines=[dict(id='r-fixed',points_xz_m=[[0.,0.],[10000.,0.]],
        downstream_id=None,upstream_ids=[],outlet='closed',drainage_area_m2=100000000.)]),
        lakes=dict(schema='lakes-v1',lakes=[dict(id='l-fixed',ring_xz_m=[[0.,0.],[10000.,0.],[10000.,10000.]],surface_m=50.)]))
    for name,data in vector_data.items():
        file=name+'.json'; (source/file).write_text(json.dumps(data))
        m['vectors'][name]=dict(file=file,sha256=cs._sha(source/file),schema=name+'-v1')
    m.pop('identity')
    m['identity']=hashlib.sha256(ts._canon(m).encode()).hexdigest()
    (source/'manifest.json').write_text(json.dumps(m))
    # Fixture-only source reseal requires a fresh climate from that exact identity.
    old=json.loads((climate/'manifest.json').read_text())
    src=cs.climate_source_from_map(source,expected_identity=m['identity'])
    climate2=tmp_path/'climate-with-vectors'
    ref=dict(schema='terragenesis-climate-reference-v1',latitude_deg=[-80.,0.,80.],
        monthly_zonal_sst_c=[[-5.]*3]*6+[[5.]*3]*6,reference_period='synthetic vector fixture')
    cm=cs.prepare(src,climate2,old['metadata']['config'],ref)
    climate=climate2;options=dict(expected_source_identity=m['identity'],expected_climate_identity=cm['identity'])
    hydro=tmp_path/'hydrology'
    h=hs.prepare(source,climate,regions,hydro,**options)
    return source,climate,hydro,dict(options,expected_hydrology_identity=h['identity'])


def seal_hydro(hydro,m):
    from terrain_pipeline.common_infra import identity
    m['identity']=identity({}, {k:v for k,v in m.items() if k!='identity'})
    (hydro/'manifest.json').write_text(json.dumps(m),encoding='utf-8')


def test_publish_preserves_source_bed_receiver_and_annual_volume_mean(prepared,tmp_path):
    source,climate,hydro,opts=prepared
    before={p.name:cs._sha(p) for p in source.iterdir() if p.is_file()}
    output=tmp_path/'environment'
    manifest=es.publish(source,climate,hydro,output,**opts)
    assert manifest['producer']=='Terragenesis'
    mapped=load_source('world-map-product',output,expected_identity=manifest['identity'])
    for name in ('elevation_m','status','receiver'):
        original=np.load(source/(name+'.npy'))
        actual=np.load(output/manifest['layers'][name]['file'])
        np.testing.assert_array_equal(actual,original)
    assert before=={p.name:cs._sha(p) for p in source.iterdir() if p.is_file()}
    original_manifest=json.loads((source/'manifest.json').read_text())
    for name,spec in original_manifest['vectors'].items():
        assert (source/spec['file']).read_bytes()==(output/manifest['vectors'][name]['file']).read_bytes()
    assert mapped.vectors('rivers')[0]['id']=='r-fixed'
    assert mapped.vectors('lakes')[0]['id']=='l-fixed'
    q=np.load(output/'discharge_m3_s.npy')
    volume=np.load(hydro/'monthly_routed_volume_m3.npy')
    np.testing.assert_allclose(q,volume.sum(0)/(365*86400),rtol=1e-15)
    wrong=np.load(hydro/'monthly_discharge_m3_s.npy').mean(0)
    assert not np.allclose(q,wrong,rtol=1e-8,atol=0)
    np.testing.assert_array_equal(np.load(output/'biome.npy'),np.load(climate/'biome_id.npy'))
    np.testing.assert_array_equal(np.load(output/'temperature_c.npy'),np.load(climate/'temperature_c.npy'))
    assert manifest['stable_biome_ids']
    assert 'world_processes' not in manifest
    assert 'glacier_cumulative_melt_water_m3' not in manifest['layers']
    assert manifest['climate_environment']['hydrology_identity']==opts['expected_hydrology_identity']
    assert all(manifest['layers'][n]['unit']==u for n,u in [('temperature_c','degC'),('discharge_m3_s','m3/s'),('snow_swe_mm','mm')])
    h=np.load(output/'glacier_ice_thickness_m.npy'); mask=np.load(hydro/'dynamic_glacier_mask.npy')
    assert np.isnan(h[~mask]).all()
    np.testing.assert_array_equal(h[mask],np.load(hydro/'final_ice_swe_mm.npy')[mask]/917.)
    assert 'year_end_ice_swe_mm' not in mapped.info.layers  # extra explicitly non-dynamic inventory
    assert {'biome','discharge_m3_s','snow_swe_mm','soil_water_mm'}<=set(mapped.info.layers)


def test_saved_sidecar_window_months_read_only(prepared):
    source,climate,hydro,opts=prepared
    s=es.SavedClimateHydrology(source,climate,hydro,**opts)
    r=s.query(['monthly_liquid_input_mm','final_snow_swe_mm'],months=[7,1],window=[1,4,5,8])
    np.testing.assert_array_equal(r['arrays']['monthly_liquid_input_mm'],
        np.load(hydro/'monthly_liquid_input_mm.npy')[[6,0],1:5,4:8])
    assert not r['arrays']['monthly_liquid_input_mm'].flags.writeable
    assert r['grid']['first_xz_m']==[5000.,-25000.]
    assert r['grid']['shape_zx']==[4,4]
    with pytest.raises(ValueError,match='Months'):s.query(['final_snow_swe_mm'],months=[0])
    with pytest.raises(ValueError,match='outside'):s.query(['final_snow_swe_mm'],window=[0,0,9,8])
    with pytest.raises(ValueError,match='unavailable'):s.query(['made_up'])
    with (hydro/'final_snow_swe_mm.npy').open('ab') as stream:stream.write(b'tamper')
    with pytest.raises(ValueError,match='hash'):s.query(['final_snow_swe_mm'])


@pytest.mark.parametrize('kind',['source','climate','grid','receiver','complete','identity','file','unit','partial'])
def test_reject_hydrology_cross_binding_and_partial(prepared,tmp_path,kind):
    source,climate,hydro,opts=prepared
    m=json.loads((hydro/'manifest.json').read_text())
    if kind in ('source','climate'):m['binding'][kind+'_identity']='f'*64
    elif kind=='grid':m['binding']['grid']['spacing_m']=5000
    elif kind=='receiver':m['binding']['receiver_sha256']='f'*64
    elif kind=='complete':m['status']='partial'
    elif kind=='identity':m['identity']='f'*64
    elif kind=='unit':m['fields']['monthly_routed_volume_m3']['units']='m3/s'
    elif kind=='partial':(hydro/'manifest.json').unlink()
    else:
        with (hydro/'monthly_liquid_input_mm.npy').open('ab') as stream:stream.write(b'tamper')
    if kind not in ('partial','file'):
        if kind!='identity':seal_hydro(hydro,m)
        else:(hydro/'manifest.json').write_text(json.dumps(m))
        opts['expected_hydrology_identity']=None
    with pytest.raises((ValueError,FileNotFoundError)):
        es.publish(source,climate,hydro,tmp_path/'rejected',**opts)
    assert not (tmp_path/'rejected').exists()


def test_pending_candidate_plan_no_publication_or_solver(prepared,monkeypatch):
    source,climate,_,opts=prepared
    opts.pop('expected_hydrology_identity')
    def forbidden(*a,**k):raise AssertionError('plan never opens annual fields or runs generation')
    monkeypatch.setattr(es.SavedClimateMap,'query',forbidden)
    result=es.plan(source,climate,**opts)
    assert result['status']=='pending-input'
    assert result['missing']==['completed-same-source-climate-hydrology-sidecar']
    assert result['default_story_publication'] is False
