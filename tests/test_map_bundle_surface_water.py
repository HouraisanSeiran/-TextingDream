"""Sixth sidecar pure frozen reads; no solver, products, registration or world run."""
from copy import deepcopy
import json

import numpy as np
import pytest

from app import map_bundle as mb
from tests.test_map_bundle import registered, write_json, seal_hydro


@pytest.fixture
def surface(registered):
    from terrain_pipeline.common_infra import array_sha256
    root, record = registered
    path = root / 'surface'; path.mkdir()
    shape = (8, 8); n = 64
    old = np.load(root / 'world/receiver.npy')
    bed = np.load(root / 'world/elevation_m.npy')
    rec = np.full(shape, -1, np.int64)
    rec[1:-1, 5:7] = np.arange(n).reshape(shape)[1:-1, 4:6]
    order = mb.topological_order(rec)
    adjacency = [[i-1] * (i % 8 > 0) + [i+1] * (i % 8 < 7) for i in range(n)]
    arrays = dict(receiver=rec, order=order, old_no_lake_receiver=old, basin_id=np.zeros(shape, np.int64),
                  geometry_parent=np.array([-1]), geometry_birth_m=np.array([0.]), geometry_crest_m=np.array([np.inf]),
                  geometry_cell_node=np.zeros(shape, np.int64), geometry_area_m2=np.full(shape, 1e8),
                  mesh_indptr=np.r_[0, np.cumsum([len(v) for v in adjacency])],
                  mesh_indices=np.array([j for v in adjacency for j in v]),
                  mesh_node_x_m=np.tile(np.arange(8)*10000.-35000, 8),
                  mesh_node_z_m=np.repeat(np.arange(8)*10000.-35000, 8),
                  annual_mean_hillslope_discharge_m3_s=np.full(shape, np.nan))
    units = dict(soil_mm='mm', runoff_mm='mm/month', land_actual_et_mm='mm/month', lake_volume_m3='m3',
        lake_stage_m='m', lake_depth_m='m', wet_mask='1', lake_et_demand_m3='m3/month',
        soil_to_lake_m3='m3/month', direct_lake_liquid_m3='m3/month', terminal_overflow_m3='m3/month',
        hillslope_routed_volume_m3='m3/month', hillslope_discharge_m3_s='m3/s', hillslope_q_support='1',
        lake_actual_et_m3='m3/month', flow_wet_support='1', monthly_liquid_input_mm='mm/month',
        monthly_snow_swe_mm='mm', monthly_ice_swe_mm='mm')
    for name in units:
        arrays[name] = np.zeros((12, *shape), bool if name in ('wet_mask','hillslope_q_support','flow_wet_support') else float)
    arrays['lake_stage_m'][:] = bed
    arrays['hillslope_discharge_m3_s'][:] = np.nan
    arrays['hillslope_routed_volume_m3'][:] = np.nan
    arrays['hillslope_q_support'][:, 1, 5] = True
    arrays['hillslope_discharge_m3_s'][:, 1, 5] = np.arange(12) + 1
    arrays['hillslope_routed_volume_m3'][:, 1, 5] = 100
    arrays['wet_mask'][6, 2, 4] = True
    arrays['flow_wet_support'][6, 2, 4] = True
    arrays['lake_depth_m'][6, 2, 4] = 2
    arrays['lake_stage_m'][6, 2, 4] += 2
    arrays['lake_volume_m3'][6, 2, 4] = 2e8
    fields = {}; files = {}
    for name, value in arrays.items():
        np.save(path / (name+'.npy'), value)
        unit = units.get(name, 'm3/s' if name.endswith('_m3_s') else 'm2' if name.endswith('_m2') else 'm' if name.endswith('_m') else '1')
        files[name+'.npy'] = mb.digest(path / (name+'.npy'))
        fields[name] = dict(file=name+'.npy', sha256=files[name+'.npy'], shape=list(value.shape), dtype=str(value.dtype), units=unit)
    draws = [[] for _ in range(12)]
    draws[6] = [dict(id='r@m07', parent_id='r', month=7, points_xz_m=[[15000.,-25000.],[5000.,-25000.]])]
    for filename, value in [('hillslope-draw.json', dict(draw_segments=draws)),
                            ('spill-routes.json', [[] for _ in range(12)]), ('water-budget.json', [])]:
        write_json(path / filename, value); files[filename] = mb.digest(path / filename)
    status = np.load(root / 'world/status.npy')
    outlets = status == 3; outlets[[0,-1],:] = True; outlets[:,[0,-1]] = True
    m = dict(schema='dream-climate-lake-year-1', status='finite-year-surface-water', publishable=True,
        binding=dict(source_identity=record['sources']['terrain']['identity'], climate_identity=record['sources']['climate']['identity'],
                     hydrology_identity=record['sources']['hydrology']['identity'], shape_zx=[8,8], calendar='noleap365', years=1, finite_boundary=True, mesh_seed=15386822478918853569),
        month_days=[31,28,31,30,31,30,31,31,30,31,30,31], fields=fields, files=files,
        geometry_binding=dict(mesh_seed=15386822478918853569, bed_sha256=array_sha256(bed), receiver_sha256=array_sha256(rec.ravel()), outlet_sha256=array_sha256(outlets)),
        lagoon_binding=dict(origin='saved registered_lagoon layer', array_sha256=array_sha256(np.zeros(shape,bool))),
        hillslope_draw_file='hillslope-draw.json', spill_routes_file='spill-routes.json', water_budget_file='water-budget.json')
    seal_hydro(m); write_json(path/'manifest.json', m)
    record['sources']['surface_water'] = dict(path='surface', identity=m['identity'], manifest_sha256=mb.digest(path/'manifest.json'))
    return root, record


def test_sixth_group_month_point_query_vectors_and_no_solver(surface, monkeypatch):
    import builtins
    original = builtins.__import__
    def guard(name, *args, **kwargs):
        if name.startswith('numba') or name.endswith(('lake_basin_geometry','climate_lake_stage','world_environment')):
            raise AssertionError('frozen bundle must not import a solver')
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', guard)
    root, record = surface
    b = mb.MapBundle(root, record)
    assert len(b.detail()['groups']) == 6
    assert b.point(15000., -25000., 7)['groups']['surface_water']['values']['hillslope_discharge_m3_s'] == 7
    wet = b.point(5000., -15000., 7)['groups']['surface_water']['values']
    assert wet['lake_depth_m'] == 2 and wet['wet_mask'] is True
    assert wet['hillslope_discharge_m3_s'] is None and wet['hillslope_q_support'] is False
    q = b.query(['surface_water.lake_depth_m','climate.monthly_temperature_c'],[2,4,3,5],[7,1])
    assert q['arrays']['surface_water.lake_depth_m'] == [[[2.]], [[0.]]]
    assert b.vectors('surface-rivers',7)['total'] == 1
    assert b.vectors('surface-rivers',1)['total'] == 0
    assert 'historical' in b.vectors('lakes')['status']
    assert 'historical-noLake' in b.detail()['groups']['hydrology']['fields']['monthly_routed_volume_m3']['time_semantics']
    with pytest.raises(ValueError, match='descriptor-only'):
        b.query(['surface_water.mesh_indices'], [0,0,1,1])
    monkeypatch.setattr(mb, 'digest', lambda *_: (_ for _ in ()).throw(AssertionError('repeat hash')))
    b.point(5000.,-15000.,12)


@pytest.mark.parametrize('failure', ['identity','source','climate','hydro','bed','outlet','lagoon','units','order','hash','shape'])
def test_surface_wrong_binding_refused_even_resealed(surface, failure):
    root, record = surface; path = root/'surface/manifest.json'; m = mb.read_json(path)
    if failure in ('source','climate','hydro'):
        m['binding'][dict(source='source_identity',climate='climate_identity',hydro='hydrology_identity')[failure]] = 'f'*64
    elif failure in ('bed','outlet'):
        m['geometry_binding'][failure+'_sha256'] = 'f'*64
    elif failure == 'lagoon':
        m['lagoon_binding']['array_sha256'] = 'f'*64
    elif failure == 'units':
        m['fields']['lake_depth_m']['units'] = 'mm'
    elif failure == 'shape':
        m['fields']['lake_depth_m']['shape'] = [12,4,16]
    elif failure == 'hash':
        (root/'surface/soil_mm.npy').write_bytes(b'bad')
    elif failure == 'order':
        p = root/'surface/order.npy'; np.save(p,np.zeros(64,np.int64))
        m['files'][p.name] = m['fields']['order']['sha256'] = mb.digest(p)
    seal_hydro(m)
    if failure == 'identity': m['identity'] = 'f'*64
    write_json(path,m); record['sources']['surface_water'].update(identity=m['identity'],manifest_sha256=mb.digest(path))
    with pytest.raises(mb.BundleIdentityError): mb.MapBundle(root,record)


def test_optional_absent_keeps_five_groups(registered):
    root, record = registered
    b = mb.MapBundle(root,record)
    assert list(b.detail()['groups']) == list(mb.GROUPS)
    with pytest.raises(mb.BundleMissing): b.vectors('surface-rivers')


def test_explicit_registration_previews_preserve_old_identity_and_month_availability(surface):
    from tools.register_map_bundle import attach_surface_water
    from PIL import Image
    root, record = surface
    parent = deepcopy(record['sources']['environment'])
    render = root/'render'; render.mkdir()
    records = []
    for month in (1,7,12):
        image = render/f'month-{month:02d}.png'; Image.new('RGB',(8,8)).save(image)
        records.append(dict(month=month, image=image.name, image_sha256=mb.digest(image),
            surface_water_identity=record['sources']['surface_water']['identity'],
            environment_parent_identity=parent['identity'], physical_source_identity=record['sources']['terrain']['identity'],
            image_size=[8,8], map_rect=dict(x=0,y=0,width=8,height=8), world_extent_m=[-40000.,-40000.,40000.,40000.]))
    write_json(render/'surface-water-source.json',records)
    attach_surface_water(root,record,'surface','render/surface-water-source.json')
    assert record['sources']['environment'] == parent
    b = mb.MapBundle(root,record)
    assert b.preview('atlas',7).name == 'month-07.png'
    assert b.preview('atlas-history').name == 'atlas.png'
    with pytest.raises(mb.BundleMissing): b.preview('atlas',2)
    assert (root/'config/map-bundles.json').is_file()  # fixture old registration was not overwritten
    old = mb.read_json(root/'config/map-bundles.json')['bundles'][0]
    assert 'surface_water' not in old['sources']
    records[0]['surface_water_identity'] = 'bad'; write_json(render/'surface-water-source.json',records)
    with pytest.raises(ValueError,match='provenance'):
        attach_surface_water(root,deepcopy(record),'surface','render/surface-water-source.json')


def test_surface_changed_after_open_and_query_limits(surface, monkeypatch):
    root, record = surface; b = mb.MapBundle(root,record)
    monkeypatch.setattr(mb,'MAX_VALUES',1)
    with pytest.raises(ValueError,match='MAX_VALUES'):
        b.query(['surface_water.lake_depth_m'],[0,0,2,2],[1])
    with (root/'surface/soil_mm.npy').open('ab') as stream: stream.write(b'changed')
    with pytest.raises(mb.BundleIdentityError,match='changed'):
        b.point(5000.,-15000.,1)


@pytest.mark.parametrize('certified', [True, False])
def test_single_sink_dag_branch_requires_its_own_actual_certification(surface, certified):
    root, record = surface
    path = root / 'surface/manifest.json'
    m = mb.read_json(path)
    m['geometry_version'] = 'tg-certified-single-sink-pool-dag-2'
    m['geometry_certification'] = dict(status='certified' if certified else 'unresolved',
        pool_count=1, certified_pool_count=1 if certified else 0,
        unresolved_pool_count=0 if certified else 1, unresolved_cell_count=0 if certified else 3,
        unresolved_pools=[] if certified else [dict(pool_id=0)])
    seal_hydro(m); write_json(path, m)
    record['sources']['surface_water'].update(identity=m['identity'], manifest_sha256=mb.digest(path))
    if certified:
        assert mb.MapBundle(root, record).point(5000., -15000., 7)['groups']['surface_water']['values']['wet_mask'] is True
    else:
        with pytest.raises(mb.BundleIdentityError, match='not certified'):
            mb.MapBundle(root, record)


@pytest.fixture
def finite_surface(surface):
    """Frozen JSON/npy fixture only: no TG import, topology build or year solve."""
    import hashlib
    root, record = surface
    path = root / 'surface'
    m = mb.read_json(path / 'manifest.json')
    bed = np.load(root / 'world/elevation_m.npy').ravel()
    owner = np.full(64, -1, np.int64)
    leaves, levels, areas, offsets, leaf_area, faces, boundaries = [], [], [], [0], [], [], []
    for row in range(1, 7):
        c = row*8+4
        for cells in ([c], [c+1, c+2]):
            k = len(leaves)
            owner[cells] = k
            leaves.append(cells[0])
            lv, inverse = np.unique(bed[cells], return_inverse=True)
            weights = np.bincount(inverse, weights=np.full(len(cells), 1e8))
            levels.extend(lv.tolist()); areas.extend(weights.tolist()); offsets.append(len(levels))
            leaf_area.append(len(cells)*1e8)
        faces.append(dict(leaf_ids=leaves[-2:], cell_ids=[c,c+1], sill_m=float(bed[c+1])))
        for a,b in ((c,c-1),(c+2,c+3)):
            boundaries.append(dict(cell_id=a, receiver_cell_id=b, leaf_id=leaves[-2] if a==c else leaves[-1],
                sill_m=float(max(bed[a],bed[b])), width_m=10000.,kind='ocean'))
    topology = dict(metadata=dict(original_source_certified=False, hydraulic_ready=False, natural_outlet_verified=False),
        arrays=dict(leaf_ids=leaves,curve_offsets=offsets,curve_level_m=levels,curve_area_m2=areas,leaf_area_m2=leaf_area),
        faces=faces,engineering_boundaries=boundaries)
    payload = dict(topology, schema='td-original-bed-overflow-topology-v1')
    topology['identity_sha256'] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    def save_array(name,value):
        np.save(path/(name+'.npy'),value)
        m['files'][name+'.npy'] = mb.digest(path/(name+'.npy'))
        m['fields'][name].update(shape=list(value.shape),dtype=str(value.dtype),sha256=m['files'][name+'.npy'])
    save_array('geometry_cell_node',owner.reshape(8,8)); save_array('basin_id',owner.reshape(8,8))
    save_array('geometry_parent',np.full(12,-1,np.int64))
    save_array('geometry_birth_m',bed[leaves]); save_array('geometry_crest_m',bed[leaves]+1000.)
    ledger, budgets = [], []
    stockmaps = np.load(path/'lake_volume_m3.npy')
    for month in range(12):
        stocks = np.bincount(owner[owner>=0],weights=stockmaps[month].ravel()[owner>=0],minlength=12).tolist()
        ledger.append(dict(month=month+1,face_forward_m3=[0.]*6,face_reverse_m3=[0.]*6,face_net_m3=[0.]*6,
            boundary_exports_m3=[0.]*12,owner_initial_m3=stocks,owner_withdrawn_m3=[0.]*12,
            owner_after_exchange_m3=stocks,owner_final_m3=stocks,owner_residual_m3=[0.]*12,
            roundoff_correction_by_owner_m3=[0.]*12,owner_postexchange_soil_transfer_m3=[0.]*12))
        budgets.append(dict(month=month+1,final_lake_m3=sum(stocks)))
    for name,value in [('csr-topology.json',topology),('csr-face-ledger.json',ledger),('water-budget.json',budgets)]:
        write_json(path/name,value); m['files'][name] = mb.digest(path/name)
    m.update(backend='tg-csr-reservoir-finite-conductance',geometry_version='dream-csr-finite-conductance-1',
        geometry_identity=topology['identity_sha256'], topology_file='csr-topology.json',face_ledger_file='csr-face-ledger.json',
        hydraulic_ready=False,natural_outlet_verified=False,channel_q_available=False,
        lake_actual_et_map_semantics='owner-local demand attribution, not column extraction',
        limitations=['month-start source impulse; owner-local PET; finite engineering conductance, not natural hydraulics'])
    seal_hydro(m); write_json(path/'manifest.json',m)
    record['sources']['surface_water'].update(identity=m['identity'],manifest_sha256=mb.digest(path/'manifest.json'))
    return root,record


def test_finite_csr_branch_is_read_only_and_exposes_engineering_limits(finite_surface, monkeypatch):
    import builtins
    original = builtins.__import__
    def guard(name,*args,**kwargs):
        if name.startswith('numba') or any(s in name for s in ('basin_storage','csr_reservoir','lake_basin_geometry')):
            pytest.fail('consumer imported solver: '+name)
        return original(name,*args,**kwargs)
    monkeypatch.setattr(builtins,'__import__',guard)
    b = mb.MapBundle(*finite_surface)
    limits = b.detail()['groups']['surface_water']['limitations']
    assert any('owner-local' in v for v in limits)
    assert any('finite engineering conductance' in v for v in limits)
    assert b.point(5000.,-15000.,7)['groups']['surface_water']['values']['lake_depth_m'] == 2.


@pytest.mark.parametrize('failure',['hydraulic','natural','version','backend','owner','face','curve','ledger','stock','pin','identity','correction','soiltransfer'])
def test_finite_csr_branch_rejects_resealed_bad_geometry_and_accounts(finite_surface,failure):
    import hashlib
    root,record = finite_surface; path=root/'surface'; m=mb.read_json(path/'manifest.json')
    if failure in ('hydraulic','natural'):
        m[dict(hydraulic='hydraulic_ready',natural='natural_outlet_verified')[failure]]=True
    elif failure=='version':
        m['geometry_version']='unknown'
    elif failure=='backend':
        m.pop('backend')
    elif failure=='owner':
        value=np.load(path/'geometry_cell_node.npy'); value[1,4]=-1; np.save(path/'geometry_cell_node.npy',value)
        m['files']['geometry_cell_node.npy']=m['fields']['geometry_cell_node']['sha256']=mb.digest(path/'geometry_cell_node.npy')
    elif failure=='pin':
        m['files'].pop('csr-face-ledger.json')
    elif failure in ('face','curve','identity'):
        t=mb.read_json(path/'csr-topology.json')
        if failure=='face': t['faces'][0]['cell_ids'][1]=22
        elif failure=='curve': t['arrays']['curve_area_m2'][0]*=2
        else: t['identity_sha256']='f'*64
        if failure!='identity':
            payload={k:v for k,v in t.items() if k!='identity_sha256'}
            payload['schema']='td-original-bed-overflow-topology-v1'
            t['identity_sha256']=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
            m['geometry_identity']=t['identity_sha256']
        write_json(path/'csr-topology.json',t);m['files']['csr-topology.json']=mb.digest(path/'csr-topology.json')
    else:
        rows=mb.read_json(path/'csr-face-ledger.json')
        rows[0]['face_net_m3'][0]=1. if failure=='ledger' else 0.
        if failure=='stock':rows[0]['owner_final_m3'][0]=1e6
        if failure=='correction':rows[0]['roundoff_correction_by_owner_m3']=[1e6]*12
        if failure=='soiltransfer':rows[0]['owner_postexchange_soil_transfer_m3']=[1e6]*12
        write_json(path/'csr-face-ledger.json',rows);m['files']['csr-face-ledger.json']=mb.digest(path/'csr-face-ledger.json')
    seal_hydro(m);write_json(path/'manifest.json',m)
    record['sources']['surface_water'].update(identity=m['identity'],manifest_sha256=mb.digest(path/'manifest.json'))
    with pytest.raises(mb.BundleIdentityError):mb.MapBundle(root,record)


def test_actual_tiny_csr_writer_opens_in_frozen_bundle(registered,tmp_path,monkeypatch):
    """8x8 synthetic writer→reader integration, never original-source/world year."""
    from types import SimpleNamespace
    from app.world_gen import csr_reservoir_year as year,graph_hydro as gh,world_climate_adapter as adapter
    from tests.test_csr_reservoir_year import parameters
    root,record=registered
    shape=(8,8); bed=np.load(root/'world/elevation_m.npy'); ocean=np.load(root/'world/status.npy')==3
    rows=[[i-1]*(i%8>0)+[i+1]*(i%8<7) for i in range(64)]
    mesh=SimpleNamespace(indptr=np.r_[0,np.cumsum([len(r) for r in rows])],indices=np.array([j for r in rows for j in r],np.int64),
        node_x_m=np.tile(np.arange(8)*10000.-35000,8),node_z_m=np.repeat(np.arange(8)*10000.-35000,8))
    source=dict(elevation_m=bed,ocean_mask=ocean,registered_lagoon=np.zeros(shape,bool),receiver=np.load(root/'world/receiver.npy'),
        first_xz_m=[-35000.,-35000.],spacing_m=10000.)
    saved={};fields={}
    for name in ('monthly_liquid_input_mm','monthly_snow_swe_mm','monthly_ice_swe_mm'):
        data=np.zeros((12,)+shape)
        if name=='monthly_liquid_input_mm':data[0,1:-1,4]=1.
        np.save(root/'hydro'/(name+'.npy'),data);saved[name]=data;fields[name]=dict(file=name+'.npy')
    view=SimpleNamespace(product=root/'climate',fields={'monthly_pet_mm':{}},query=lambda _:dict(arrays=parameters(shape)))
    hydro=dict(identity=record['sources']['hydrology']['identity'],fields=fields,binding={})
    monkeypatch.setattr(year,'_saved_inputs',lambda *args,**kwargs:(source,view,hydro,saved if kwargs.get('monthly') else {}))
    monkeypatch.setattr(gh,'build_graph',lambda *args:mesh)
    monkeypatch.setattr(adapter,'_saved_array',lambda *args:np.zeros((12,)+shape))
    m=year.prepare(root/'world',root/'climate',root/'hydro',root/'csr-water',
        expected_source_identity=record['sources']['terrain']['identity'],expected_climate_identity=record['sources']['climate']['identity'],
        expected_hydrology_identity=record['sources']['hydrology']['identity'])
    record['sources']['surface_water']=dict(path='csr-water',identity=m['identity'],manifest_sha256=mb.digest(root/'csr-water/manifest.json'))
    b=mb.MapBundle(root,record)
    assert b.detail()['groups']['surface_water']['status']=='finite-year-surface-water'
    assert b.point(5000.,-15000.,1)['groups']['surface_water']['values']['lake_volume_m3']>=0.
