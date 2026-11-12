"""Synthetic frozen readers: no generation/planner/numba, no real artifact writes."""
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from app import map_bundle as mb
from app.map_source import load_source
from app.world_gen.world_climate_adapter import _climate_module
from tests.test_climate_world_stage import world_map


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


def seal_map(m):
    from app.terrain_source import _canon
    import hashlib
    m.pop('identity', None)
    m['identity'] = hashlib.sha256(_canon(m).encode()).hexdigest()


def seal_hydro(m):
    from terrain_pipeline.common_infra import identity
    m['identity'] = identity({}, {k:v for k,v in m.items() if k != 'identity'})


@pytest.fixture
def registered(tmp_path, monkeypatch):
    # Existing fixture only writes tiny fixed arrays; does not call prepare.
    source, _ = world_map(tmp_path)
    parent = mb.read_json(source/'manifest.json')
    for kind, item in [('rivers',dict(id='r',points_xz_m=[[-35000.,-35000.],[-25000.,-35000.]],
            downstream_id=None,upstream_ids=[],outlet='ocean',drainage_area_m2=1e8)),
                       ('lakes',dict(id='l',ring_xz_m=[[0.,0.],[1.,0.],[1.,1.]],surface_m=1.))]:
        path = source/(kind+'.json')
        write_json(path, dict(schema=kind+'-v1', **{('lines' if kind == 'rivers' else 'lakes'):[item]}))
        parent['vectors'][kind] = dict(file=path.name,sha256=mb.digest(path),schema=kind+'-v1')
    seal_map(parent); write_json(source/'manifest.json', parent)
    _climate_module()  # Lightweight saved-climate import; does not import world_environment/numba.
    from terrain_pipeline.common_infra import array_sha256
    days = [31,28,31,30,31,30,31,31,30,31,30,31]
    climate_path = tmp_path/'climate'; climate_path.mkdir()
    temp = np.broadcast_to(np.arange(12,dtype=np.float32)[:,None,None],(12,8,8)).copy()
    np.save(climate_path/'monthly_temperature_c.npy',temp)
    cf = dict(monthly_temperature_c=dict(file='monthly_temperature_c.npy',sha256=mb.digest(climate_path/'monthly_temperature_c.npy'),
        dtype='float32',shape=[12,8,8],units='degC'))
    climate = dict(identity='c'*64, manifest_identity='d'*64, fields=cf, metadata=dict(month_days=days))
    write_json(climate_path/'manifest.json',climate)
    write_json(climate_path/'source-binding.json',{'fixture':True})
    # Isolate the already-tested climate seam; exercise bundle hydro + map_source
    # real static binding below without invoking any climate solver in tests.
    class SavedDouble:
        def __init__(self, src, product, expected_source_identity, expected_climate_identity):
            self.terrain=load_source('world-map-product',src,expected_identity=expected_source_identity)
            assert expected_climate_identity == climate['identity']
            self.fields=deepcopy(cf);self.metadata=climate['metadata'];self.manifest_identity=climate['manifest_identity']
    monkeypatch.setattr(mb,'SavedClimateMap',SavedDouble)
    rec=np.load(source/'receiver.npy');order=mb.topological_order(rec)
    hydro_path=tmp_path/'hydro';hydro_path.mkdir()
    arrays=dict(receiver=rec,order=order,dynamic_glacier_mask=np.zeros((8,8),bool),
        final_soil_water_mm=np.zeros((8,8)),final_snow_swe_mm=np.zeros((8,8)),final_ice_swe_mm=np.zeros((8,8)),
        monthly_routed_volume_m3=np.broadcast_to(np.arange(12.)[:,None,None],(12,8,8)).copy())
    hf={}; files={}
    for name,a in arrays.items():
        np.save(hydro_path/(name+'.npy'),a)
        unit='m3/month' if name=='monthly_routed_volume_m3' else '1' if name in ('receiver','order','dynamic_glacier_mask') else 'mm'
        hf[name]=dict(file=name+'.npy',sha256=mb.digest(hydro_path/(name+'.npy')),dtype=str(a.dtype),shape=list(a.shape),units=unit)
        files[name+'.npy']=hf[name]['sha256']
    write_json(hydro_path/'regions.json',[]);files['regions.json']=mb.digest(hydro_path/'regions.json')
    hydro=dict(schema='dream-climate-hydrology-year-1',status='complete',calendar='noleap365',year=1,month_days=days,
        fields=hf,files=files,binding=dict(source_identity=parent['identity'],climate_identity=climate['identity'],
        climate_manifest_identity=climate['manifest_identity'],world_seed=parent['world_seed'],
        grid=dict(first_xz_m=[-35000.,-35000.],spacing_m=10000.,shape_zx=[8,8]),
        receiver_sha256=array_sha256(np.asarray(rec,np.int64).ravel()),order_sha256=array_sha256(order),regions=[]))
    seal_hydro(hydro);write_json(hydro_path/'manifest.json',hydro)
    environment_path=tmp_path/'environment';environment_path.mkdir()
    env=deepcopy(parent)
    for n,s in env['layers'].items():
        # Copy fixed source bytes, no generation.
        (environment_path/s['file']).write_bytes((source/s['file']).read_bytes())
    for n,s in env['vectors'].items():
        (environment_path/s['file']).write_bytes((source/s['file']).read_bytes())
    np.save(environment_path/'year_end_ice_swe_mm.npy',np.full((8,8),np.nan))
    env['layers']['year_end_ice_swe_mm']=dict(file='year_end_ice_swe_mm.npy',sha256=mb.digest(environment_path/'year_end_ice_swe_mm.npy'),
        dtype='float64',unit='mm',meaning='synthetic unknown terminal ice',nodata=None)
    env['source_identity']=parent['identity'];env['climate_environment']=dict(source_identity=parent['identity'],
        climate_identity=climate['identity'],hydrology_identity=hydro['identity'])
    seal_map(env);write_json(environment_path/'manifest.json',env)
    ocean_path=tmp_path/'ocean';ocean_path.mkdir()
    oa=dict(ocean_mask=np.array([[True,False],[True,False]]),
        monthly_sea_temperature_c=np.full((12,2,2),10.),monthly_current_x_m_s=np.full((12,2,2),.01))
    of={}
    for name,a in oa.items():
        np.save(ocean_path/(name+'.npy'),a)
        of[name]=dict(file=name+'.npy',sha256=mb.digest(ocean_path/(name+'.npy')),dtype=str(a.dtype),shape=list(a.shape),
            unit='degC' if name.endswith('_c') else '1',nodata=None)
    ocean=dict(schema='dream-ocean-current-overlay-1',status='finite-year-candidate',
        source_ids=dict(world=parent['identity'],climate=climate['identity'],ocean_forcing='f'*64),
        native_grid=dict(first_xz_m=[-35000.,-35000.],spacing_m=10000.,shape_zx=[8,8]),
        macro_grid=dict(first_xz_m=[-20000.,-20000.],spacing_m=40000.,shape_zx=[2,2]),arrays=list(oa),
        render=dict(atlas_environment_identity=env['identity']))
    write_json(ocean_path/'manifest.json',ocean)
    write_json(ocean_path/'routes.json',dict(routes=[dict(id='current',month=1,coordinates_xz_m=[[0,0],[1,1]])]))
    sources={}
    for g,p in dict(terrain=source,environment=environment_path,climate=climate_path,hydrology=hydro_path,ocean=ocean_path).items():
        m=mb.read_json(p/'manifest.json')
        sources[g]=dict(path=p.relative_to(tmp_path).as_posix(),identity=m.get('identity'),manifest_sha256=mb.digest(p/'manifest.json'))
    sources['ocean'].update(fields=of,forcing_identity='f'*64,
        routes=dict(path='ocean/routes.json',sha256=mb.digest(ocean_path/'routes.json')))
    Image.new('RGB',(8,8)).save(tmp_path/'atlas.png')
    record=dict(id='synthetic-world',title='Synthetic',status='current',sources=sources,history=[],warnings=['potential/unvalidated'],
        previews=[dict(key='atlas',title='atlas',months=[],georeferenced=True,image_size=[8,8],
        map_rect=dict(x=0,y=0,width=8,height=8),world_extent_m=[-40000.,-40000.,40000.,40000.],
        files=dict(static=dict(path='atlas.png',sha256=mb.digest(tmp_path/'atlas.png'))))])
    write_json(tmp_path/'config/map-bundles.json',dict(schema='dream-map-bundles-1',bundles=[record]))
    return tmp_path,record


def test_month_point_query_unknown_and_no_month_rehash(registered,monkeypatch):
    root,record=registered;registry=mb.BundleRegistry(root);bundle=registry.get(record['id'])
    january=bundle.point(-20000.,-20000.,1);july=bundle.point(-20000.,-20000.,7)
    assert january['groups']['climate']['values']['monthly_temperature_c']==0
    assert july['groups']['climate']['values']['monthly_temperature_c']==6
    assert july['groups']['environment']['values']['year_end_ice_swe_mm'] is None
    assert july['groups']['ocean']['values']['monthly_sea_temperature_c']==10.
    assert bundle.point(20000.,-20000.,7)['groups']['ocean']['values']['monthly_sea_temperature_c'] is None
    assert bundle.query(['climate.monthly_temperature_c'],[0,0,1,1],[7,1])['arrays']['climate.monthly_temperature_c']==[[[6.]],[[0.]]]
    monkeypatch.setattr(mb,'digest',lambda *_: (_ for _ in ()).throw(AssertionError('repeat hash')))
    assert registry.get(record['id']) is bundle
    bundle.point(-20000.,-20000.,7)
    assert bundle.vectors('lakes')['items'][0]['status']=='potential/unvalidated'
    assert bundle.vectors('ocean-currents',7)['total']==0
    assert bundle.detail()['groups']['hydrology']['fields']['order']['queryable'] is False


def test_invalid_requests_and_paths(registered,monkeypatch):
    root,record=registered;b=mb.MapBundle(root,record)
    for path in ['../outside','C:/outside','/outside','world/../world','world\\manifest.json']:
        with pytest.raises(mb.BundleIdentityError):mb.relative_file(root,path)
    for fields,window,months in [(['monthly_temperature_c'],[0,0,1,1],[1]),
            (['climate.nope'],[0,0,1,1],[1]),(['hydrology.order'],[0,0,1,1],[1]),
            (['terrain.status','ocean.ocean_mask'],[0,0,1,1],[1]),
            (['terrain.status'],[0,0,9,9],[1]),(['terrain.status'],[0,0,1,1],[0])]:
        with pytest.raises(ValueError):b.query(fields,window,months)
    monkeypatch.setattr(mb,'MAX_VALUES',1)
    with pytest.raises(ValueError,match='MAX_VALUES'):b.query(['terrain.status'],[0,0,2,2],[1])
    with pytest.raises(ValueError):b.point(1e8,0.,1)
    with pytest.raises(ValueError):b.point(0.,0.,True)
    with pytest.raises(mb.BundleMissing):b.preview('manifest.json')
    with pytest.raises(mb.BundleMissing):mb.BundleRegistry(root).get('not-registered')


def test_immutable_change_refused(registered):
    root,record=registered;b=mb.MapBundle(root,record)
    with (root/'hydro/final_soil_water_mm.npy').open('ab') as f:f.write(b'changed')
    with pytest.raises(mb.BundleIdentityError):b.point(0.,0.,1)


@pytest.mark.parametrize('group,key,value',[('hydrology','climate_identity','a'*64),
    ('hydrology','receiver_sha256','a'*64),('hydrology','order_sha256','a'*64),
    ('hydrology','world_seed',-1),('ocean','climate','a'*64),('environment','hydrology_identity','a'*64)])
def test_wrong_source_binding_refused_even_resealed(registered,group,key,value):
    root,record=registered;p=root/record['sources'][group]['path']/'manifest.json';m=mb.read_json(p)
    if group=='hydrology':m['binding'][key]=value;seal_hydro(m)
    elif group=='environment':m['climate_environment'][key]=value;seal_map(m)
    else:m['source_ids'][key]=value
    write_json(p,m);record['sources'][group]['manifest_sha256']=mb.digest(p)
    record['sources'][group]['identity']=m.get('identity')
    with pytest.raises(ValueError):mb.MapBundle(root,record)


def test_missing_file_and_preview_escape(registered):
    root,record=registered
    record['previews'][0]['files']['static']['path']='../outside.png'
    with pytest.raises(mb.BundleIdentityError):mb.MapBundle(root,record)
    (root/'ocean/routes.json').unlink()
    with pytest.raises(mb.BundleMissing):mb.MapBundle(root,record)


def test_real_registration_is_read_only_and_no_numba_planner(monkeypatch):
    # Fixed current-product smoke, skipped on clean checkouts lacking local products.
    root=Path(__file__).resolve().parents[1]
    if not (root/'config/map-bundles.json').is_file():pytest.skip('local registered products absent')
    from app.world_gen import climate_world_stage as stage
    monkeypatch.setattr(stage,'climate_source_from_map',lambda *a,**k: (_ for _ in ()).throw(AssertionError('planner dependency')))
    reg=mb.BundleRegistry(root);b=reg.get('terragenesis-world-20261111')
    d=b.detail();assert d['world_extent_m']==[-5e6,-4e6,5e6,4e6]
    assert len(d['previews'])==8
    # Actual registered native cell [2,238] and macro [0,59] are both wet.
    # The north-west corner [0,0] is land and must never return SST.
    p=b.point(-2615000.,-3975000.,7)
    assert p['groups']['terrain']['values']['status']==3
    assert p['groups']['ocean']['values']['ocean_mask'] is True
    assert p['groups']['ocean']['values']['monthly_sea_temperature_c'] is not None
    land=b.point(-4995000.,-3995000.,7)
    assert land['groups']['terrain']['values']['status']!=3
    assert land['groups']['ocean']['values']['monthly_sea_temperature_c'] is None
    assert b.vectors('ocean-currents',1)['total']+b.vectors('ocean-currents',7)['total']==36
    for preview in d['previews']:
        if not preview['georeferenced']:assert preview['map_rect'] is None
