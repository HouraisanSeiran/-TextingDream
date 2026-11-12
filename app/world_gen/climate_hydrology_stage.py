"""One finite climate year -> snow/ice liquid -> ONE soil bucket -> saved receivers.

Independent sidecar, never a native climate manifest or terrain update. Old glacier
products contribute only their world-bound H, not historical liquid or snow stocks.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile

import numpy as np

from app.world_gen import climate_world_stage as source_stage
from app.world_gen.world_climate_adapter import SavedClimateMap, _saved_array

SCHEMA = 'dream-climate-hydrology-year-1'
MONTH_DAYS = np.array([31,28,31,30,31,30,31,31,30,31,30,31])
PARAMETERS = ('soil_capacity_mm','infiltration_fraction','quickflow_fraction','et_fraction')
FLUXES = ('rain_water_m3','snow_melt_water_m3','ice_melt_water_m3')


def _edge_max(value):
    return float(max(np.max(value[...,0,:]), np.max(value[...,-1,:]),
                     np.max(value[...,:,0]), np.max(value[...,:,-1])))


def _inputs(source_map, climate_product, regions, expected_source_identity, expected_climate_identity):
    if not expected_source_identity or not expected_climate_identity:
        raise ValueError('Explicit source and climate identities required')
    view = SavedClimateMap(source_map, climate_product, expected_source_identity=expected_source_identity,
        expected_climate_identity=expected_climate_identity)
    if view.metadata['algorithm'] != source_stage.climate_module().DIAGNOSTIC_VERSION:
        raise ValueError('Explicit saved diagnostic climate required')
    needed = {'monthly_temperature_c','monthly_precipitation_mm','monthly_pet_mm',*PARAMETERS}
    if not needed <= set(view.fields):
        raise ValueError('Saved monthly climate/PET/biome parameters missing')
    if view.metadata.get('calendar') != 'noleap365' or view.metadata.get('month_days') != MONTH_DAYS.tolist():
        raise ValueError('noleap365 climate calendar required')
    source = source_stage.climate_source_from_map(source_map, expected_identity=expected_source_identity)
    root = Path(source_map).resolve()
    manifest = json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    selected = np.zeros(source['elevation_m'].shape, bool)
    prepared = []
    climate = source_stage.climate_module()
    h_world = None
    if regions:
        h_spec = manifest['layers']['glacier_ice_thickness_m']
        h_world = _saved_array(root, h_spec, climate)
        if h_spec.get('unit') != 'm' or h_world.shape != selected.shape:
            raise ValueError('Old H unit/grid differs from source')
    for request in regions:
        if set(request) != {'window_zx','old_identity'}:
            raise ValueError('Region requires only window_zx and old_identity')
        win = request['window_zx']
        if len(win) != 4 or any(type(n) is not int for n in win):
            raise ValueError('Integer region window required')
        z0,x0,z1,x1 = win
        nz,nx = selected.shape
        if not (0 <= z0 < z1 <= nz and 0 <= x0 < x1 <= nx and 3 <= z1-z0 <= 513 and 3 <= x1-x0 <= 513):
            raise ValueError('Region outside grid or too small')
        sl = np.s_[z0:z1,x0:x1]
        records = [r for r in manifest.get('glacier_regions', [])
                   if r['identity'] == request['old_identity'] and r['window_zx'] == win]
        if len(records) != 1:
            raise ValueError('Selected old glacier identity/window not bound to source')
        old = records[0]
        if (old.get('boundary') != 'closed' or old.get('edge_ice',{}).get('closed_edge_zero') is not True
                or type(old.get('completed_years')) is not int
                or old['completed_years'] != old.get('target_years')):
            raise ValueError('Old region incomplete or not closed-edge-zero')
        h = np.array(h_world[sl], dtype=np.float64)
        if (selected[sl].any() or source['ocean_mask'][sl].any()
                or not np.isfinite(h).all() or np.any(h < 0) or _edge_max(h) != 0):
            raise ValueError('Region overlap/ocean/invalid old H/closed edge')
        selected[sl] = True
        prepared.append(dict(window_zx=list(win), old_identity=request['old_identity'], initial_h=h))
    return view, source, prepared, selected


def plan(source_map, climate_product, regions, *, expected_source_identity, expected_climate_identity):
    view, source, prepared, _ = _inputs(source_map, climate_product, regions,
        expected_source_identity, expected_climate_identity)
    n = source['elevation_m'].size
    r = max((v['initial_h'].size for v in prepared), default=0)
    return dict(schema=SCHEMA, status='ready', source_identity=source['source_identity'],
        climate_identity=view.metadata['identity'], shape_zx=list(source['elevation_m'].shape),
        region_count=len(prepared), region_cells=sum(v['initial_h'].size for v in prepared),
        estimated_peak_increment_bytes=int(128*2**20+n*8*120+r*3360+384),
        estimated_output_bytes=int(n*8*(12*9+8)+sum(v['initial_h'].size for v in prepared)*8),
        storage='monthly liquid/SWE/sublimation/Q/volume memmaps; native one-year bucket retained in RAM',
        calendar='noleap365', years=1, terrain_evolution=False,
        completion='full new diagnostic year only; closed-edge-zero dynamic regions; no coupled climate claim',
        missing=[], estimate_kind='conservative array allowance, not OS peak guarantee')


def prepare(source_map, climate_product, regions, out_dir, *, expected_source_identity,
            expected_climate_identity, diagnostic_snow_parameters=None, glacier_snow_config=None,
            glacier_config=None, max_memory_bytes=2*1024**3):
    view, source, prepared, selected = _inputs(source_map, climate_product, regions,
        expected_source_identity, expected_climate_identity)
    climate = source_stage.climate_module()
    from terrain_pipeline.world_environment import diagnostic_snow_ice
    from terrain_pipeline.world_glacier import generate_climate_slope_glacier
    from terrain_pipeline.drainage import accumulate_graph
    from terrain_pipeline.common_infra import array_sha256, identity
    n = source['elevation_m'].size
    r = max((v['initial_h'].size for v in prepared), default=0)
    estimate = int(128*2**20+n*8*120+r*3360+384)
    if type(max_memory_bytes) is not int or estimate > max_memory_bytes:
        raise ValueError('Planned live arrays exceed memory budget')
    cfg = dict(glacier_config or {})
    if cfg.get('outflow_sides'):
        raise ValueError('Dynamic region outflow needs explicit upstream decision; refusing publication')
    cfg['outflow_sides'] = []
    out = Path(out_dir).resolve()
    for parent in (Path(source_map).resolve(),Path(climate_product).resolve()):
        if out == parent or out.is_relative_to(parent):
            raise ValueError('Sidecar must not be inside immutable parent')
    if out.exists():
        raise FileExistsError('New sidecar output directory required')
    out.parent.mkdir(parents=True,exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='.climate-hydrology-',dir=out.parent))
    arrays = {}
    try:
        shape = source['elevation_m'].shape
        monthly_shape = (12,*shape)
        area = source['spacing_m']**2
        land = ~source['ocean_mask']
        def monthly(name):
            value = np.lib.format.open_memmap(work/(name+'.npy'),mode='w+',dtype=np.float64,shape=monthly_shape)
            arrays[name] = value
            return value
        liquid = monthly('monthly_liquid_input_mm')
        snow_stock = monthly('monthly_snow_swe_mm')
        ice_stock = monthly('monthly_ice_swe_mm')
        sublimation = monthly('monthly_sublimation_mm')
        snow, ice = np.zeros(shape), np.zeros(shape)
        diagnostic_metadata = None
        # No precomputed climate runoff/ET/soil fields are read.
        precipitation_totals = np.zeros(12)
        for month in range(12):
            forcing = view.query(['monthly_temperature_c','monthly_precipitation_mm'],months=[month+1])['arrays']
            t, p = forcing['monthly_temperature_c'], forcing['monthly_precipitation_mm']
            result = diagnostic_snow_ice(t,p,ocean_mask=source['ocean_mask'],
                initial_snow_swe_mm=snow,initial_ice_swe_mm=ice,start_month=month+1,
                parameters=diagnostic_snow_parameters)
            a = result['arrays']
            liquid[month] = a['monthly_liquid_water_input_to_bucket_mm'][0]
            snow_stock[month] = a['monthly_snow_swe_mm'][0]
            ice_stock[month] = a['monthly_ice_swe_mm'][0]
            sublimation[month] = a['monthly_sublimation_mm'][0]
            snow,ice = result['state']['snow_swe_mm'],result['state']['ice_swe_mm']
            precipitation_totals[month] = p[0,land].astype(np.float64).sum()*area/1000.
            diagnostic_metadata = result['metadata']
        initial_ice = np.zeros(shape)
        region_records = []
        for region in prepared:
            z0,x0,z1,x1 = region['window_zx']; sl = np.s_[z0:z1,x0:x1]
            forcing = view.query(['monthly_temperature_c','monthly_precipitation_mm'],window=region['window_zx'])['arrays']
            geometry = dict(bed_m=source['elevation_m'][sl],ice_thickness_m=region['initial_h'],
                dx_m=source['spacing_m'],dz_m=source['spacing_m'],
                origin_xz_m=[source['first_xz_m'][0]+x0*source['spacing_m'],source['first_xz_m'][1]+z0*source['spacing_m']],
                source_identity=source['source_identity'],terrain_identity=source['source_identity'])
            result = generate_climate_slope_glacier(geometry,forcing['monthly_temperature_c'],
                forcing['monthly_precipitation_mm'],state=None,target_years=1,
                snow_config=glacier_snow_config,config=cfg,export_monthly=True)
            meta, export = result['metadata'],result.get('monthly_export',{})
            if (meta.get('completed') is not True or meta.get('completed_years') != 1
                    or export.get('start_month_index') != 0 or export.get('stop_month_index') != 12
                    or not np.array_equal(export.get('year'), np.ones(12,int))
                    or not np.array_equal(export.get('month'),np.arange(1,13))):
                raise ValueError('Incomplete dynamic glacier year/month export; refusing publication')
            for name in (*FLUXES,'snow_water_m','ice_thickness_m'):
                value = np.asarray(export[name])
                if value.shape != (12,z1-z0,x1-x0) or not np.isfinite(value).all() or np.any(value < 0):
                    raise ValueError('Invalid native monthly glacier export')
            if _edge_max(export['ice_thickness_m']) != 0 or result['ledger']['boundary_ice_out_m3'] != 0:
                raise ValueError('Dynamic ice reaches closed boundary; report upstream, never crop/delete ice')
            rho = meta['parameters']['ice_density_kg_m3']
            initial_ice[sl] = region['initial_h']*rho
            # SOLE replacement: old cumulative/pending/melt stocks never enter.
            liquid[:,sl[0],sl[1]] = sum(export[k] for k in FLUXES)*1000./area
            snow_stock[:,sl[0],sl[1]] = export['snow_water_m']*1000.
            ice_stock[:,sl[0],sl[1]] = export['ice_thickness_m']*rho
            sublimation[:,sl[0],sl[1]] = 0.
            experiment = dict(old_identity=region['old_identity'],window_zx=region['window_zx'],
                initial_H_sha256=array_sha256(region['initial_h']),new_climate_identity=view.metadata['identity'],
                source_identity=source['source_identity'],native_model_identity=meta['model_identity'])
            region_records.append(dict(binding=experiment,metadata=meta,ledger=result['ledger']))
        native = view.query([*PARAMETERS,'monthly_pet_mm'])['arrays']
        bucket,residual = climate._monthly_land_bucket(liquid,native['monthly_pet_mm'],native,land)
        for name,value in bucket.items():
            np.save(work/(name+'.npy'),value,allow_pickle=False)
        volume = monthly('monthly_routed_volume_m3')
        discharge = monthly('monthly_discharge_m3_s')
        surface = dict(monthly_liquid_input_m3=[],monthly_actual_et_m3=[],monthly_runoff_m3=[],monthly_soil_change_m3=[],monthly_residual_m3=[],maximum_cell_residual_mm=float(residual.max()))
        snow_budget = dict(monthly_precipitation_m3=precipitation_totals.tolist(),monthly_liquid_m3=[],monthly_sublimation_m3=[],monthly_storage_change_m3=[],monthly_residual_m3=[])
        routing = dict(monthly_local_input_m3=[],monthly_terminal_export_m3=[],monthly_residual_m3=[])
        previous_soil = np.zeros(shape)
        previous_snowice = initial_ice
        terminals = np.asarray(source['receiver']).ravel() < 0
        for month in range(12):
            local = bucket['monthly_runoff_mm'][month]*area/1000.
            volume[month] = accumulate_graph(np.asarray(source['receiver'],np.int64).ravel(),source['order'],local)
            discharge[month] = volume[month]/(MONTH_DAYS[month]*86400.)
            liq = float(liquid[month,land].sum()*area/1000.)
            et = float(bucket['monthly_actual_et_mm'][month].sum()*area/1000.)
            runoff = float(local.sum())
            stock = bucket['monthly_soil_water_mm'][month]
            delta = float((stock-previous_soil).sum()*area/1000.)
            previous_soil = stock
            for key,value in zip(('monthly_liquid_input_m3','monthly_actual_et_m3','monthly_runoff_m3','monthly_soil_change_m3','monthly_residual_m3'),(liq,et,runoff,delta,liq-et-runoff-delta)):
                surface[key].append(value)
            snowice = snow_stock[month]+ice_stock[month]
            change = float((snowice-previous_snowice).sum()*area/1000.)
            previous_snowice = snowice
            sub = float(sublimation[month].sum()*area/1000.)
            for key,value in zip(('monthly_liquid_m3','monthly_sublimation_m3','monthly_storage_change_m3','monthly_residual_m3'),(liq,sub,change,float(precipitation_totals[month]-liq-sub-change))):
                snow_budget[key].append(value)
            terminal = float(volume[month].ravel()[terminals].sum())
            for key,value in zip(routing,(runoff,terminal,runoff-terminal)):
                routing[key].append(value)
        for account, scale in ((surface, surface['monthly_liquid_input_m3']),
                               (snow_budget, precipitation_totals+initial_ice.sum()*area/1000.),
                               (routing, routing['monthly_local_input_m3'])):
            errors = np.asarray(account['monthly_residual_m3'])
            if not np.isfinite(errors).all() or np.any(abs(errors) > 1.e-8*np.maximum(np.asarray(scale),1.)):
                raise ValueError('Water account failed; refusing publication')
        saved_static = dict(initial_snow_swe_mm=np.zeros(shape),initial_ice_swe_mm=initial_ice,
            final_snow_swe_mm=np.array(snow_stock[-1]),final_ice_swe_mm=np.array(ice_stock[-1]),
            initial_soil_water_mm=np.zeros(shape),final_soil_water_mm=bucket['monthly_soil_water_mm'][-1],
            dynamic_glacier_mask=selected,receiver=np.asarray(source['receiver']),order=source['order'])
        for name,value in saved_static.items():
            np.save(work/(name+'.npy'),value,allow_pickle=False)
        for value in arrays.values():
            value.flush(); value._mmap.close()
        arrays.clear()
        snow_budget.update(initial_snow_water_m3=0.,initial_ice_water_m3=float(initial_ice.sum()*area/1000.),
            final_snow_water_m3=float(saved_static['final_snow_swe_mm'].sum()*area/1000.),
            final_ice_water_m3=float(saved_static['final_ice_swe_mm'].sum()*area/1000.))
        for name,record in [('surface-budget.json',surface),('snow-ice-budget.json',snow_budget),('routing-budget.json',routing),('regions.json',region_records)]:
            source_stage._write_json(work/name,record)
        binding = dict(source_identity=source['source_identity'],climate_identity=view.metadata['identity'],
            climate_manifest_identity=view.manifest_identity,world_seed=source['world_seed'],
            grid=dict(first_xz_m=source['first_xz_m'],spacing_m=source['spacing_m'],shape_zx=list(shape)),
            receiver_sha256=array_sha256(np.asarray(source['receiver'],np.int64).ravel()),order_sha256=array_sha256(source['order']),
            regions=[v['binding'] for v in region_records],diagnostic_snow_parameters=diagnostic_metadata['parameters'],
            glacier_config=cfg,glacier_snow_config=glacier_snow_config)
        files = {p.name:source_stage._sha(p) for p in work.iterdir() if p.is_file()}
        fields = {}
        for path in work.glob('*.npy'):
            name = path.stem
            value = np.load(path,mmap_mode='r',allow_pickle=False)
            unit = ('m3/month' if name == 'monthly_routed_volume_m3' else
                    'm3/s' if name == 'monthly_discharge_m3_s' else
                    '1' if name in ('receiver','order','dynamic_glacier_mask') else
                    'mm/month' if name in ('monthly_liquid_input_mm','monthly_runoff_mm','monthly_actual_et_mm','monthly_sublimation_mm') else 'mm')
            fields[name] = dict(file=path.name,sha256=files[path.name],shape=list(value.shape),
                dtype=str(value.dtype),units=unit)
            value._mmap.close()
        record = dict(schema=SCHEMA,status='complete',binding=binding,fields=fields,calendar='noleap365',month_days=MONTH_DAYS.tolist(),
            year=1,initial_stocks='new year snow=0, soil=0, ice=0 outside explicit old-H regions',
            units='monthly depths mm water; SWE mm water; routed volume m3/month; discharge m3/s',
            handoff='dynamic monthly rain+snow_melt+ice_melt replaces diagnostic liquid once; one bucket; saved receivers',
            ignored_inputs='all old cumulative/pending/melt and climate diagnostic runoff/soil/ET',
            terrain_evolution=False,files=files)
        record['identity'] = identity({},record)
        source_stage._write_json(work/'manifest.json',record)
        work.rename(out)
        return record
    finally:
        for value in arrays.values():
            if isinstance(value,np.memmap):
                value._mmap.close()
        if work.exists():
            shutil.rmtree(work)
