"""Tiny render-only saved fixtures: no browser, real source, TG or generation."""
from dataclasses import replace
import json
from types import SimpleNamespace

import numpy as np
import pytest

from app.world_gen import surface_water_map as sw
from app.world_relief import atlas


def write_json(path, value):
    path.write_text(json.dumps(value), encoding='utf-8')


@pytest.fixture
def saved(tmp_path, monkeypatch):
    env_root, root = tmp_path / 'env', tmp_path / 'water'
    hydro = tmp_path / 'hydro'
    env_root.mkdir(); root.mkdir(); hydro.mkdir()
    shape = (12, 16)
    bed = np.full(shape, 100.)
    bed[0] = -10
    ocean = bed < 0
    info = SimpleNamespace(identity='env-id', shape_zx=shape, spacing_m=10000.,
        first_sample_xz_m=(5000., 5000.), world_seed=20260903,
        kind='world-map-product', schema='world-map-product-v1', lineage=('terrain-id',),
        limitations=(), grid_semantics='cell-centre')
    h = np.full(shape, np.nan); h[3:5, 3:5] = 2
    dynamic = np.zeros(shape); dynamic[3:5, 3:5] = 1
    product = atlas.Product(path=env_root, source=SimpleNamespace(info=info), elevation=bed,
        ocean=ocean, closed=np.zeros(shape, bool), lake_surface=bed + 50.,
        area_m2=np.ones(shape), rivers=[dict(id=999, coordinates_xz_m=[[0, 0], [10000, 10000]])],
        river_threshold_km2=1e6, ice_thickness=h, ice_surface=bed+h,
        simulated_mask=dynamic, ice_coverage=np.where(dynamic, 1., np.nan),
        saved_biome=np.full(shape, 4, np.uint16), saved_temperature=np.full(shape, 10.),
        saved_precipitation=np.full(shape, 500.), saved_discharge=np.full(shape, 99.),
        saved_snow_swe=np.full(shape, 999.), environment_metadata={})
    terminal = np.zeros(shape); terminal[3:5, 3:5] = 1800
    np.save(env_root / 'ice.npy', terminal)
    region_binding = dict(window_zx=[3, 3, 5, 5])
    write_json(hydro / 'regions.json', [dict(binding=region_binding,
        metadata=dict(parameters=dict(ice_density_kg_m3=900.)))])
    hm = dict(schema='dream-climate-hydrology-year-1', status='complete',
        binding=dict(source_identity='terrain-id', climate_identity='climate-id', regions=[region_binding]),
        files={'regions.json': sw._digest(hydro / 'regions.json')})
    hm['identity'] = sw._identity(hm)
    write_json(hydro / 'manifest.json', hm)
    binding = dict(source_identity='terrain-id', climate_identity='climate-id', hydrology_identity=hm['identity'])
    env = dict(identity='env-id', climate_environment=binding,
               layers=dict(year_end_ice_swe_mm=dict(file='ice.npy')))
    write_json(env_root / 'manifest.json', env)
    depth = np.zeros((12,) + shape)
    depth[0, 6, 6] = 2.
    depth[0, 6, 7] = .0001
    depth[6, 7, 8] = .5
    snow = np.zeros_like(depth); snow[0] = 10; snow[6] = 70; snow[11] = 120
    ice = np.zeros_like(depth); ice[0, 3:5, 3:5] = 900; ice[6, 3:5, 3:5] = 2700
    ice[11, 3:5, 3:5] = 1800
    fields = {}
    for name, value in dict(lake_depth_m=depth, lake_stage_m=bed[None] + depth,
                           wet_mask=depth > 0, monthly_snow_swe_mm=snow, monthly_ice_swe_mm=ice).items():
        np.save(root / (name + '.npy'), value)
        fields[name] = dict(file=name + '.npy', shape=list(value.shape), dtype=str(value.dtype),
                            sha256=sw._digest(root / (name + '.npy')))
    series = [[2.] * 12, [2.] * 3 + [0.] * 9, [2.] + [0.] * 11, [0.] * 12]
    vector = dict(id=1, edge_anchor_cells=[16, 17, 18, 19], edge_monthly_q_m3_s=series)
    draws = [[] for _ in range(12)]
    draws[0] = [dict(id='r', parent_id=1, edge_anchor_cells=[16, 17, 18, 19],
        edge_q_m3_s=[2., 2., 2., 0.], points_xz_m=[[5000+i*10000, 15000] for i in range(5)])]
    network = dict(vectors=[vector], draw_segments=draws,
        parameters=dict(min_active_q_m3_s=.1, perennial_months=12, seasonal_months=3))
    spills = [[] for _ in range(12)]
    spills[0] = [dict(id='s', net_transferred_volume_m3=100,
        points_xz_m=[[5000, 25000], [15000, 25000]], path_semantics='deterministic CSR net schematic')]
    write_json(root / 'hillslope-draw.json', network)
    write_json(root / 'spill-routes.json', spills)
    meta = dict(schema='dream-climate-lake-year-1', status='finite-year-surface-water', publishable=True,
        binding=dict(binding, shape_zx=list(shape)), fields=fields,
        hillslope_draw_file='hillslope-draw.json', spill_routes_file='spill-routes.json',
        original_hydrology_regions=[dict(window_zx=[3, 3, 5, 5])])
    meta['files'] = {p.name: sw._digest(p) for p in root.iterdir()}
    meta['identity'] = sw._identity(meta)
    write_json(root / 'manifest.json', meta)
    def load_environment(kind, path, *, expected_identity):
        assert kind == 'world-map-product' and path == env_root
        assert expected_identity == 'env-id'
        return product.source
    monkeypatch.setattr(sw, 'load_source', load_environment)
    monkeypatch.setattr(atlas, 'product_from_source', lambda source, path: product)
    return env_root, root, product, meta, hydro


def load(saved, month):
    return sw.load_surface_product(saved[0], saved[1], month,
        expected_environment_identity='env-id', expected_surface_identity=saved[3]['identity'], hydrology=saved[4])


def test_actual_lakes_disappear_no_potential_fill_and_shallow_visual_threshold(saved):
    jan, jul, dec = load(saved, 1), load(saved, 7), load(saved, 12)
    assert jan.product.lake_surface[6, 6] == 102
    assert jul.product.lake_surface[6, 6] == 100
    assert jul.product.lake_surface[7, 8] == 100.5
    np.testing.assert_array_equal(dec.product.lake_surface, dec.product.elevation)
    assert jan.product.lake_surface[6, 7] > jan.product.elevation[6, 7]  # physical field unchanged
    assert jan.provenance['shallow_wet_fraction'] == .5
    assert jan.provenance['displayed_wet_cells'] == 1
    params = replace(atlas.AtlasParams(width_px=80), lake_min_depth_m=.1, lake_min_cells=1)
    analysis = atlas.analyse(jan.product, params)
    assert analysis['lake'][6, 6] and not analysis['lake'][6, 7]
    assert not atlas.analyse(dec.product, params)['lake'].any()


def test_no_q_no_blue_and_edge_classes_styles_without_area_filter(saved):
    jan, jul = load(saved, 1), load(saved, 7)
    assert [s['kind'] for s in jan.segments] == ['perennial', 'seasonal', 'intermittent', 'spill']
    assert not jul.segments and not jul.product.rivers
    text = sw.water_svg(jan, atlas.full_view(jan.product, 80), 3)
    assert 'stroke-dasharray="7 4"' in text and 'stroke-dasharray="1 4"' in text
    assert 'CSR' in text and 'dry_valley' not in text
    assert all(s.get('q_m3_s', 1) > 0 for s in jan.segments)


def test_monthly_swe_dynamic_h_no_reice_and_env_arrays_unchanged(saved):
    original = saved[2]
    before = {k: v.copy() for k, v in vars(original).items() if isinstance(v, np.ndarray)}
    for month, snow, h in ((1, 10, 1), (7, 70, 3), (12, 120, 2)):
        surface = load(saved, month)
        p = surface.product
        np.testing.assert_allclose(p.saved_snow_swe, snow)
        np.testing.assert_allclose(p.ice_thickness[3:5, 3:5], h)
        assert np.isnan(p.ice_thickness[0, 0])
        np.testing.assert_allclose(p.ice_surface[3:5, 3:5], 100+h)
        assert p.identity == original.identity == 'env-id'
        assert p.saved_biome is original.saved_biome and p.elevation is original.elevation
        assert p.cache is not original.cache and p.saved_discharge is None
    for name, value in before.items():
        np.testing.assert_equal(getattr(original, name), value)
    assert original.rivers[0]['id'] == 999


def test_small_atlas_composition_and_new_outputs_only(saved, tmp_path):
    out = tmp_path / 'render'
    before = {str(p): p.read_bytes() for root in saved[:2] for p in root.iterdir()}
    records = sw.render_months(*saved[:2], out, expected_environment_identity='env-id',
        expected_surface_identity=saved[3]['identity'], width=80, hydrology=saved[4])
    assert [r['month'] for r in records] == [1, 7, 12]
    text = (out / 'month-01.html').read_text(encoding='utf-8')
    assert 'monthly-water' in text and 'data-flow-class="seasonal"' in text
    assert '粗格' in text and '图符' in text
    assert (out / 'month-12-source.json').exists()
    assert records[0]['environment_parent_identity'] == 'env-id'
    assert records[0]['surface_water_identity'] == saved[3]['identity']
    for path, content in before.items():
        from pathlib import Path
        assert Path(path).read_bytes() == content


def test_wrong_parent_and_output_in_parent_rejected(saved):
    meta = dict(saved[3], binding=dict(saved[3]['binding'], hydrology_identity='wrong'))
    meta['identity'] = sw._identity(meta)
    saved[3]['identity'] = meta['identity']
    write_json(saved[1] / 'manifest.json', meta)
    with pytest.raises(ValueError, match='parent binding'):
        load(saved, 1)
    with pytest.raises(ValueError, match='immutable parents'):
        sw.render_months(*saved[:2], saved[0] / 'atlas', expected_environment_identity='env-id',
                        expected_surface_identity=saved[3]['identity'], width=80, hydrology=saved[4])


def test_zero_terminal_ice_still_uses_original_saved_density(saved):
    saved[2].ice_thickness[3:5, 3:5] = 0
    np.testing.assert_allclose(load(saved, 1).product.ice_thickness[3:5, 3:5], 1.)


def test_wrong_original_hydrology_and_regions_tamper_rejected(saved):
    path = saved[4] / 'manifest.json'
    original = path.read_bytes()
    meta = json.loads(original)
    meta['identity'] = 'wrong'
    write_json(path, meta)
    with pytest.raises(ValueError, match='hydrology identity'):
        load(saved, 1)
    path.write_bytes(original)
    write_json(saved[4] / 'regions.json', [])
    with pytest.raises(ValueError, match='regions hash'):
        load(saved, 1)


@pytest.mark.parametrize('filename', ['lake_depth_m.npy', 'hillslope-draw.json', 'spill-routes.json'])
def test_consumed_sidecar_tamper_rejected(saved, filename):
    with (saved[1] / filename).open('ab') as stream:
        stream.write(b'changed')
    with pytest.raises(ValueError, match='file hash'):
        load(saved, 1)


def test_sidecar_manifest_tamper_rejected(saved):
    meta = dict(saved[3], scope='tampered')
    write_json(saved[1] / 'manifest.json', meta)
    with pytest.raises(ValueError, match='manifest identity'):
        load(saved, 1)


def test_preview_metadata_uses_actual_atlas_frame_and_image(saved, tmp_path):
    from PIL import Image
    def capture(html, png, width, height):
        Image.new('RGB', (width, height)).save(png)
    out = tmp_path / 'preview'
    records = sw.render_months(*saved[:2], out, expected_environment_identity='env-id',
        expected_surface_identity=saved[3]['identity'], width=80, months=(1,),
        screenshot=capture, hydrology=saved[4])
    record = records[0]
    assert record['source_identity'] == record['environment_parent_identity'] == 'env-id'
    assert record['map_rect']['width'] == 80
    assert record['map_rect']['height'] == 60
    assert record['world_extent_m'] == [0., 0., 160000., 120000.]
    assert record['image_sha256'] == sw._digest(out / record['image'])
    with Image.open(out / record['image']) as image:
        assert list(image.size) == record['image_size']


@pytest.mark.parametrize('failure',[None,'hydraulic','ledger','topology'])
def test_finite_csr_render_policy_and_saved_binding_only(saved,failure,monkeypatch):
    import builtins
    root=saved[1];meta=dict(saved[3])
    topology=dict(metadata=dict(hydraulic_ready=False,natural_outlet_verified=False),arrays={},faces=[],engineering_boundaries=[])
    payload=dict(topology,schema='td-original-bed-overflow-topology-v1')
    topology['identity_sha256']=__import__('hashlib').sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    write_json(root/'csr-topology.json',topology);write_json(root/'csr-face-ledger.json',[])
    meta['files']=dict(meta['files'],**{name:sw._digest(root/name) for name in ('csr-topology.json','csr-face-ledger.json')})
    meta.update(backend='tg-csr-reservoir-finite-conductance',geometry_version='dream-csr-finite-conductance-1',
        hydraulic_ready=False,natural_outlet_verified=False,channel_q_available=False,
        topology_file='csr-topology.json',face_ledger_file='csr-face-ledger.json',geometry_identity=topology['identity_sha256'],
        splitting='month-start impulse; finite month exchange',lake_evaporation='owner-local, not whole connected pool')
    if failure=='hydraulic':meta['hydraulic_ready']=True
    elif failure=='topology':meta['geometry_identity']='bad'
    meta['identity']=sw._identity(meta);write_json(root/'manifest.json',meta);saved[3]['identity']=meta['identity']
    if failure=='ledger':
        with (root/'csr-face-ledger.json').open('ab') as f:f.write(b'changed')
    original=builtins.__import__
    def guard(name,*args,**kwargs):
        if any(v in name for v in ('numba','csr_reservoir','basin_storage')):pytest.fail('renderer imported solver')
        return original(name,*args,**kwargs)
    monkeypatch.setattr(builtins,'__import__',guard)
    if failure:
        with pytest.raises(ValueError):load(saved,1)
    else:
        rendered=load(saved,1)
        assert rendered.provenance['hydraulic_ready'] is False
        assert 'owner-local' in rendered.provenance['lake_evaporation']
        assert rendered.product.identity=='env-id'


def test_real_world_map_environment_source_kind_without_loader_mock(tmp_path, monkeypatch):
    """Real 8x8 world-map adapter + atlas conversion; no source-kind mock seam."""
    import hashlib
    from app import terrain_source as ts
    from tests.test_climate_world_stage import world_map
    env, _ = world_map(tmp_path)
    manifest = json.loads((env/'manifest.json').read_text(encoding='utf-8'))
    shape=(8,8); bed=np.load(env/'elevation_m.npy')
    for name,value,unit in [('water_surface_m',bed.copy(),'m'),('drainage_area_m2',np.ones(shape),'m2'),
        ('biome',np.full(shape,4,np.uint16),'1'),
        ('temperature_c',np.full(shape,10.),'degC'),('precipitation_mm_yr',np.full(shape,500.),'mm/yr'),
        ('discharge_m3_s',np.zeros(shape),'m3/s'),('snow_swe_mm',np.zeros(shape),'mm')]:
        np.save(env/(name+'.npy'),value)
        spec=dict(file=name+'.npy',sha256=sw._digest(env/(name+'.npy')),dtype=str(value.dtype),unit=unit,
                  meaning='fixed synthetic saved environment',nodata=None,
                  source='tiny fixed source-kind regression',approximation='synthetic test values',scenario='synthetic finite year')
        manifest['layers'][name]=spec;manifest['files'][spec['file']]=spec['sha256']
    parents=dict(source_identity='a'*64,climate_identity='b'*64,hydrology_identity='c'*64)
    manifest['climate_environment']=dict(parents,schema='dream-climate-environment-publication-1',year=1,calendar='noleap365')
    manifest['stable_biome_ids']={str(k):v[0] for k,v in atlas.SAVED_BIOMES.items()}
    manifest.pop('identity')
    manifest['identity']=hashlib.sha256(ts._canon(manifest).encode()).hexdigest()
    write_json(env/'manifest.json',manifest)
    water=tmp_path/'water';water.mkdir()
    depth=np.zeros((12,)+shape);depth[0,2,4]=2.
    fields={}
    for name,value in dict(lake_depth_m=depth,lake_stage_m=bed[None]+depth,wet_mask=depth>0,
        monthly_snow_swe_mm=np.zeros_like(depth),monthly_ice_swe_mm=np.zeros_like(depth)).items():
        np.save(water/(name+'.npy'),value)
        fields[name]=dict(file=name+'.npy',shape=list(value.shape),dtype=str(value.dtype),sha256=sw._digest(water/(name+'.npy')))
    write_json(water/'hillslope-draw.json',dict(vectors=[],parameters={},draw_segments=[[] for _ in range(12)]))
    write_json(water/'spill-routes.json',[[] for _ in range(12)])
    meta=dict(schema='dream-climate-lake-year-1',status='finite-year-surface-water',publishable=True,
        binding=dict(parents,shape_zx=list(shape)),fields=fields,hillslope_draw_file='hillslope-draw.json',spill_routes_file='spill-routes.json',
        files={p.name:sw._digest(p) for p in water.iterdir()})
    meta['identity']=sw._identity(meta);write_json(water/'manifest.json',meta)
    def forbidden(*args,**kwargs):
        pytest.fail('renderer used atlas default world-relief-pilot source kind')
    monkeypatch.setattr(atlas,'load_product',forbidden)
    loaded=sw.load_surface_product(env,water,1,expected_environment_identity=manifest['identity'],expected_surface_identity=meta['identity'])
    assert loaded.product.source.info.kind=='world-map-product'
    assert loaded.product.source.info.schema=='world-map-product-v1'
    assert loaded.product.identity==manifest['identity']
    assert loaded.product.lake_surface[2,4]==bed[2,4]+2.
    np.testing.assert_array_equal(loaded.product.saved_biome,np.full(shape,4))


def test_current_known_flow_with_unknown_regime_is_not_hidden_or_treated_zero():
    from app.world_gen.river_flow_network import build_flow_network
    q = np.ones((12, 5)); q[1, 0] = np.nan; q[1, 1] = np.nan; q[:, 3] = 0
    net = build_flow_network([1, 2, 3, 4, -1], [4, 3, 2, 1, 0], q,
        np.zeros(5), dict(shape_zx=(1, 5), first_xz_m=(0, 0), spacing_m=10000),
        cartography_profile='all-active')
    jan = sw._segments(net, [[] for _ in range(12)], 1)
    feb = sw._segments(net, [[] for _ in range(12)], 2)
    assert [s['kind'] for s in jan] == ['unknown_regime', 'perennial']
    assert jan[0]['edge_anchor_cells'] == [0, 1] and len(jan[0]['points_xz_m']) == 3
    assert feb[0]['edge_anchor_cells'] == [2] and len(feb) == 1
    assert all(3 not in s['edge_anchor_cells'] for s in jan + feb)
    assert sw.STYLES['unknown_regime'][1] == '7 3 1 3'


def test_same_class_edges_one_polyline_dash_phase_and_absolute_monotonic_width():
    from app.world_gen.river_flow_network import build_flow_network, symbol_width
    q = np.ones((12, 5)); q[3:] = 0
    net = build_flow_network([1, 2, 3, 4, -1], [4, 3, 2, 1, 0], q,
        np.zeros(5), dict(shape_zx=(1, 5), first_xz_m=(0, 0), spacing_m=10000))
    segments = sw._segments(net, [[] for _ in range(12)], 1)
    assert len(segments) == 1 and segments[0]['kind'] == 'seasonal'
    assert len(segments[0]['points_xz_m']) == 5
    assert segments[0]['edge_q_m3_s'] == [1.] * 4
    assert segments[0]['width'] == symbol_width(1.)
    widths = [symbol_width(q) for q in (.1, 1., 10., 100., 1000.)]
    assert widths == sorted(widths) and widths[0] >= 1.1 and widths[-1] <= 3.8


def display_fixture(saved, tmp_path):
    meta = saved[3]
    record = dict(schema='dream-river-display-sidecar-1',
        binding=dict(surface_water_identity=meta['identity'], physical_source_identity='terrain-id',
            environment_identity='env-id', surface_manifest_sha256=sw._digest(saved[1] / 'manifest.json'),
            source_files={'wet_mask.npy': meta['files']['wet_mask.npy']}),
        network=sw._json(saved[1] / 'hillslope-draw.json'), recipe=dict(profile='test'))
    record['identity'] = sw._identity(record)
    path = tmp_path / 'river-display.json'; write_json(path, record)
    return path, record


def test_display_override_binds_saved_source_and_keeps_all_physical_files(saved, tmp_path):
    path, record = display_fixture(saved, tmp_path)
    before = {str(p): p.read_bytes() for root in saved[:2] for p in root.iterdir()}
    rendered = sw.load_surface_product(*saved[:2], 1, expected_environment_identity='env-id',
        expected_surface_identity=saved[3]['identity'], hydrology=saved[4], river_display=path)
    assert rendered.product.identity == 'env-id'
    assert rendered.provenance['river_display_identity'] == record['identity']
    assert rendered.provenance['surface_water_identity'] == saved[3]['identity']
    assert rendered.provenance['river_display_sha256'] == sw._digest(path)
    from pathlib import Path
    assert all(Path(p).read_bytes() == data for p, data in before.items())


@pytest.mark.parametrize('failure', ['parent', 'pin', 'network'])
def test_display_override_rejects_wrong_parent_pin_and_modified_network(saved, tmp_path, failure):
    path, record = display_fixture(saved, tmp_path)
    if failure == 'parent':
        record['binding']['surface_water_identity'] = 'wrong'
    elif failure == 'pin':
        record['binding']['source_files']['wet_mask.npy'] = 'wrong'
    else:
        record['network']['vectors'][0]['edge_monthly_q_m3_s'][0][0] = 999.
    if failure != 'network':
        record['identity'] = sw._identity(record)
    write_json(path, record)
    with pytest.raises(ValueError, match='river display'):
        sw.load_surface_product(*saved[:2], 1, expected_environment_identity='env-id',
            expected_surface_identity=saved[3]['identity'], hydrology=saved[4], river_display=path)


def test_rebuild_reads_existing_arrays_only_and_writes_independent_display(saved, tmp_path, monkeypatch):
    from tools.rebuild_river_display import rebuild
    from app.world_gen import graph_hydro as gh
    shape = saved[2].shape; n = int(np.prod(shape)); root = saved[1]
    rec = np.full(n, -1, np.int64); rec[16:19] = [17, 18, 19]
    q = np.zeros((12,) + shape); q.reshape(12, n)[:, 16:19] = 2.
    zz, xx = np.indices(shape)
    values = dict(receiver=rec.reshape(shape), order=np.arange(n - 1, -1, -1),
        hillslope_discharge_m3_s=q, geometry_area_m2=np.ones(shape),
        mesh_node_x_m=(5000. + xx.ravel() * 10000.), mesh_node_z_m=(5000. + zz.ravel() * 10000.),
        flow_wet_support=np.zeros_like(q, bool))
    meta = saved[3]
    for name, value in values.items():
        np.save(root / (name + '.npy'), value)
        digest = sw._digest(root / (name + '.npy'))
        meta['fields'][name] = dict(file=name + '.npy', shape=list(value.shape), dtype=str(value.dtype), sha256=digest)
        meta['files'][name + '.npy'] = digest
    meta['identity'] = sw._identity(meta); write_json(root / 'manifest.json', meta)
    calls = []
    def accumulate(receiver, order, area):
        calls.append('area-only')
        return np.ones_like(area)
    monkeypatch.setattr(gh, 'load_terragenesis', lambda: (SimpleNamespace(accumulate_graph=accumulate), None))
    before = {p: p.read_bytes() for root in saved[:2] for p in root.iterdir()}
    path = tmp_path / 'independent.json'
    record = rebuild(saved[0], saved[1], path, environment_identity='env-id',
        surface_identity=meta['identity'], profile='all-active')
    assert calls == ['area-only']
    assert record['summary']['display_candidate_edge_count'] == 3
    assert record['summary']['monthly_render'][0]['known_active_draw_edges'] == 3
    assert record['network']['vectors'][0]['nodes'] == [16, 17, 18, 19]
    result = sw.load_surface_product(*saved[:2], 1, expected_environment_identity='env-id',
        expected_surface_identity=meta['identity'], hydrology=saved[4], river_display=path)
    assert result.product.identity == 'env-id'
    assert result.provenance['river_display_identity'] == record['identity']
    assert all(p.read_bytes() == content for p, content in before.items())
    with pytest.raises(ValueError, match='max_file_bytes'):
        rebuild(saved[0], saved[1], tmp_path / 'budget.json', environment_identity='env-id',
            surface_identity=meta['identity'], profile='all-active', max_bytes=100)
    assert not (tmp_path / 'budget.json').exists()
