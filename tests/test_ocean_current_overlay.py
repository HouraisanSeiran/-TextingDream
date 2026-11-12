"""Small synthetic tests only; never solve the actual 50k-cell ocean."""
from copy import deepcopy
import json
from types import SimpleNamespace
import time

import numpy as np
import pytest

from app.world_gen import ocean_current_overlay as overlay


def fixture(n=12, *, factor=1, split=False):
    climate, _ = overlay._modules()
    wet = np.ones((n,n), bool)
    if split:
        # Two native wet pieces inside the northwest factor=4 macro cell.
        wet[:4,:4] = False
        wet[0,:4] = True
        wet[3,:4] = True
    source = dict(elevation_m=np.where(wet,-100.,300.),ocean_mask=wet,
        spacing_m=10000.,first_xz_m=[5000.,5000.],world_seed=20260903,source_identity='synthetic-world')
    reference = dict(schema='terragenesis-climate-reference-v1',latitude_deg=[-80.,0.,80.],
        monthly_zonal_sst_c=[[2.,25.,2.]]*12,reference_period='synthetic-not-observations')
    cfg = dict(macro_spacing_m=10000.*factor,reference_latitude_deg=30.,center_xz_m=[0.,0.])
    context = climate.prepare_context(source,cfg,reference)
    metadata = dict(identity='synthetic-climate',config=dict(cfg,atmosphere_backend='game-diagnostic'),
        macro_grid=dict(first_xz_m=context['first_xz_m'],spacing_m=context['spacing_m'],shape_zx=list(context['ocean_mask'].shape)),
        reference_identity=context['reference_identity'])
    wind_x = np.full((12,)+context['ocean_mask'].shape,5.)
    wind_z = np.zeros_like(wind_x)
    return source,metadata,(wind_x,wind_z),reference


def trace_fixture(n=12):
    source,meta,winds,ref = fixture(n)
    context = overlay.prepare_context(source,meta,winds,references=ref)
    arrays = dict(monthly_current_x_m_s=np.ones((12,n,n)),monthly_current_z_m_s=np.zeros((12,n,n)),
                  monthly_sst_anomaly_c=np.zeros((12,n,n)),basin_id=np.ones((n,n),int))
    return source,context,arrays


def test_physical_macro_not_diagnostic_majority_and_split_ports_closed():
    source,meta,winds,reference = fixture(12,factor=4,split=True)
    before = source['ocean_mask'].copy()
    context = overlay.prepare_context(source,meta,winds,references=reference)
    assert context['unresolved_split_ocean_blocks'] == [[0,0,2]]
    assert not context['ocean_mask'][0,0]
    boundary = context['ocean_boundary']
    assert not boundary['face_open_x'][0,0] and not boundary['face_open_z'][0,0]
    assert boundary['face_width_fraction_x'][0,0] == 0
    assert boundary['wet_area_fraction'][0,0] == 0
    assert boundary['west']['kind'][0] == 'closed'
    assert boundary['west']['open_width_fraction'][0] == 0
    assert context['topology']['excluded_native_wet_cells'] == 8
    assert np.all(context['bed_m'][context['ocean_mask']] == -100.)
    np.testing.assert_array_equal(source['ocean_mask'],before)
    np.testing.assert_array_equal(context['monthly_winds'][0],winds[0])


def test_one_connected_small_partial_cell_keeps_real_area_and_face_width():
    source,meta,winds,reference = fixture(12,factor=4)
    source['ocean_mask'][:4,:4] = False
    source['ocean_mask'][0,:4] = True
    source['elevation_m'] = np.where(source['ocean_mask'],-123.,400.)
    context = overlay.prepare_context(source,meta,winds,references=reference)
    assert context['ocean_mask'][0,0]  # Only 25% wet; majority climate would discard it.
    assert context['bed_m'][0,0] == -123.
    assert context['ocean_boundary']['wet_area_fraction'][0,0] == .25
    assert context['ocean_boundary']['face_width_fraction_x'][0,0] == .25


def test_reference_and_saved_month_grid_must_match():
    source,meta,winds,reference = fixture()
    bad = deepcopy(meta)
    bad['reference_identity'] = 'different'
    with pytest.raises(ValueError,match='Reference SST'):
        overlay.prepare_context(source,bad,winds,references=reference)
    with pytest.raises(ValueError,match='macro winds'):
        overlay.prepare_context(source,meta,(winds[0][:1],winds[1]),references=reference)


def test_land_barrier_and_closed_macro_port_truncate_instead_of_bridge():
    source,context,arrays = trace_fixture()
    source['ocean_mask'][:,6] = False
    assert not overlay.segment_is_ocean([5000.,15000.],[115000.,15000.],source,context)
    routes = overlay.trace_routes(source,context,arrays,max_routes=4,min_length_m=15000.,max_steps=20)
    assert routes
    for route in routes:
        points = np.asarray(route['coordinates_xz_m'])
        assert np.all(np.diff(points[:,0]) > 0)  # flow-to, including backward half.
        assert all(overlay.segment_is_ocean(a,b,source,context) for a,b in zip(points[:-1],points[1:]))
        assert not (points[:,0].min() < 65000. < points[:,0].max())
    source['ocean_mask'][:] = True
    context['ocean_boundary']['face_open_x'][:,5] = False
    assert not overlay.segment_is_ocean([55000.,15000.],[65000.,15000.],source,context)
    assert not overlay.segment_is_ocean([5000.,15000.],[-6000.,15000.],source,context)


def test_exact_corner_cut_is_rejected_even_when_uniform_samples_miss_tiny_land_visit():
    source,context,_ = trace_fixture()
    source['ocean_mask'][1,1] = False
    assert not overlay.segment_is_ocean([5000.,19999.],[35000.,20001.],source,context)


@pytest.mark.parametrize('value,kind',[(.5,'warm'),(-.5,'cold'),(.1,'neutral'),(None,'unclassified')])
def test_types_use_anomaly_not_absolute_temperature_and_no_random_lines(value,kind):
    source,context,arrays = trace_fixture()
    if value is None:
        arrays.pop('monthly_sst_anomaly_c')
    else:
        arrays['monthly_sst_anomaly_c'][:] = value
    kwargs = dict(max_routes=3,min_length_m=15000.,max_steps=20,source_ids={'world':'synthetic'})
    first = overlay.trace_routes(source,context,arrays,**kwargs)
    second = overlay.trace_routes(source,context,arrays,**kwargs)
    assert first == second and first
    assert all(r['type'] == kind and r['source_ids']['world'] == 'synthetic' for r in first)
    assert len(first) <= 3


def test_native_latitude_reference_is_subtracted_not_air_or_coarse_anomaly():
    source,context,arrays = trace_fixture()
    native_ref = np.interp(context['native_latitude_deg'],context['reference']['latitude_deg'],
                           context['reference']['monthly_zonal_sst_c'][0])
    arrays['monthly_sea_temperature_c'] = np.broadcast_to(native_ref[None]+.8,(12,12,12))
    arrays['monthly_sst_anomaly_c'][:] = -50  # Must be ignored when actual SST exists.
    routes = overlay.trace_routes(source,context,arrays,max_routes=2,min_length_m=15000.,max_steps=20)
    assert routes and all(r['type'] == 'warm' and abs(r['mean_sst_anomaly_c']-.8) < 1e-10 for r in routes)


def test_small_real_cpu_kernel_probe_one_year_and_thermal_budget_failure(tmp_path):
    import psutil
    source,meta,winds,reference = fixture(12)
    context = overlay.prepare_context(source,meta,winds,references=reference)
    start = time.perf_counter()
    result = overlay.solve(context,max_substeps_per_month=128)
    print(json.dumps(dict(probe_shape=[12,12],device='cpu',wall_seconds=time.perf_counter()-start,
        process_rss_bytes=psutil.Process().memory_info().rss,
        process_peak_working_set_bytes=getattr(psutil.Process().memory_info(),'peak_wset',None),
        solver=result['metadata']['wall_seconds'],
        thermal_substeps=result['metadata']['thermal_substeps_per_month'])))
    assert result['metadata']['completed_cycles'] == 1
    assert result['metadata']['converged'] is False
    assert result['metadata']['parameters']['heat_advection'] is True
    assert np.isfinite(result['arrays']['monthly_sea_temperature_c']).all()
    assert result['budgets']['coastal_normal_leakage_m3_s'] == 0
    assert max(abs(v) for v in result['budgets']['monthly_relative_heat_residual']) < 1e-10
    with pytest.raises(ValueError,match='budget'):
        overlay.solve(context,max_substeps_per_month=1)


def test_atlas_frame_uses_saved_margin_and_rejects_wrong_identity():
    meta = dict(product=dict(identity=overlay.ENVIRONMENT_ID,first_sample_xz_m=[-4995000.,-3995000.],
        spacing_m=10000.,shape_zx=[800,1000]),files={'simple-atlas.png':dict(summary=dict(
            margin_px=81,map_px=[1800,1440],decorations=[dict(box_px=[10,20,30,40])]))})
    result = overlay.atlas_geometry(meta,(1962,1727))
    assert result['origin_px'] == [81,81]
    assert result['reserved_boxes'] == [[91,101,111,121]]
    with pytest.raises(ValueError,match='size'):
        overlay.atlas_geometry(meta,(1800,1440))
    meta['product']['identity'] = 'other'
    with pytest.raises(ValueError,match='identity'):
        overlay.atlas_geometry(meta,(1962,1727))


def test_prepare_save_and_pil_overlay_without_atlas_rebuild(tmp_path):
    from PIL import Image
    source,meta,winds,reference = fixture(8)
    product = tmp_path/'ocean'
    manifest = overlay.prepare(source,meta,winds,product,references=reference,months=(1,),max_routes=2)
    assert manifest['producer'] == 'Terragenesis'
    assert manifest['solver']['completed_cycles'] == 1
    assert 'monthly_sea_temperature_c' in manifest['arrays']
    with pytest.raises(FileExistsError):
        overlay.prepare(source,meta,winds,product,references=reference)
    # The small real domain is shorter than the 400km major-route cutoff.
    # Add a short validated synthetic render-only path to exercise labels/arrows.
    route = dict(month=1,coordinates_xz_m=[[5000.,15000.],[65000.,15000.]],name='北部中性流',type='neutral')
    overlay.write_json(product/'routes.json',dict(routes=[route]))
    atlas = tmp_path/'atlas.png'
    Image.new('RGB',(500,570),(210,225,230)).save(atlas)
    metadata = dict(product=dict(identity=overlay.ENVIRONMENT_ID,source_identity=source['source_identity'],
        first_sample_xz_m=source['first_xz_m'],spacing_m=source['spacing_m'],shape_zx=[8,8]),
        climate_environment=dict(climate_identity=meta['identity']),
        files={'simple-atlas.png':dict(summary=dict(margin_px=30,map_px=[440,440],decorations=[]))})
    atlas_meta = tmp_path/'atlas-source.json'
    overlay.write_json(atlas_meta,metadata)
    before = atlas.read_bytes()
    outputs = overlay.render(product,source,atlas,atlas_meta)
    assert len(outputs) == 3 and atlas.read_bytes() == before
    overlay_image = Image.open(product/'overlay-month-01.png')
    assert overlay_image.mode == 'RGBA' and overlay_image.size == (500,570)
    assert overlay_image.getpixel((0,0))[3] == 0


def test_saved_macro_winds_loaded_unchanged_and_parent_mismatch_rejected(tmp_path,monkeypatch):
    from app import map_source
    climate,_ = overlay._modules()
    from terrain_pipeline.common_infra import array_sha256
    source,meta,winds,_ = fixture(8)
    info = SimpleNamespace(grid_semantics='cell-centre',first_sample_xz_m=source['first_xz_m'],
        shape_zx=[8,8],spacing_m=source['spacing_m'],identity=source['source_identity'],world_seed=source['world_seed'])
    crop = dict(complete=True,elevation_m=source['elevation_m'],status=np.full((8,8),3,np.uint8))
    mapped = SimpleNamespace(info=info,crop=lambda *a,**k: crop)
    monkeypatch.setattr(map_source,'load_source',lambda *a,**k: mapped)
    entries = {}
    for name,value in dict(ocean_mask=source['ocean_mask'],monthly_wind_x_m_s=winds[0],monthly_wind_z_m_s=winds[1]).items():
        path = tmp_path/(name+'.npy')
        np.save(path,value,allow_pickle=False)
        entries[name] = dict(file=path.name,sha256=climate._digest(path))
    meta.update(source_identity=source['source_identity'],world_seed=source['world_seed'],shape_zx=[8,8],
        first_xz_m=source['first_xz_m'],spacing_m=source['spacing_m'],terrain_sha256=array_sha256(source['elevation_m']))
    manifest = dict(identity=meta['identity'],status='complete',metadata=meta,fields=dict(ocean_mask=entries['ocean_mask']),
        diagnostics=dict(atmosphere={k:entries[k] for k in ('monthly_wind_x_m_s','monthly_wind_z_m_s')}))
    manifest['manifest_identity'] = climate._manifest_hash(manifest)
    overlay.write_json(tmp_path/'manifest.json',manifest)
    loaded,_,actual = overlay.load_inputs(tmp_path,tmp_path,expected_source=source['source_identity'],expected_climate=meta['identity'])
    np.testing.assert_array_equal(actual[0],winds[0])
    np.testing.assert_array_equal(loaded['ocean_mask'],source['ocean_mask'])
    manifest['metadata']['source_identity'] = 'wrong-parent'
    manifest.pop('manifest_identity')
    manifest['manifest_identity'] = climate._manifest_hash(manifest)
    overlay.write_json(tmp_path/'manifest.json',manifest)
    with pytest.raises(ValueError,match='source/grid'):
        overlay.load_inputs(tmp_path,tmp_path,expected_source=source['source_identity'],expected_climate=meta['identity'])


def test_plan_only_never_calls_ocean_or_atmosphere_solver(monkeypatch):
    source,meta,winds,reference = fixture(8)
    climate,ocean = overlay._modules()
    def forbidden(*args,**kwargs):
        raise AssertionError('Planning must not solve')
    monkeypatch.setattr(ocean,'solve_ocean',forbidden)
    monkeypatch.setattr(climate,'compute_climate',forbidden)
    result = overlay.plan(source,meta,winds,references=reference)
    assert result['solver_config']['max_cycles'] == 1
    assert result['limits']['rss_bytes'] == 2*1024**3
