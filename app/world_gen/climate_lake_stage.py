"""Replay saved liquid through stateful land buckets and connected bed lakes.

One empty-stock finite year, not equilibrium or permanent-channel certification.
Snow/ice and climate are immutable upstream inputs and are never recomputed here.
"""
from __future__ import annotations

import numpy as np

SCHEMA = 'dream-climate-lake-year-1'
MESH_SEED = 15386822478918853569
MONTH_DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
PARAMETERS = ('soil_capacity_mm', 'infiltration_fraction', 'quickflow_fraction', 'et_fraction')


def land_bucket_step(liquid_mm, pet_mm, parameters, land, soil_mm):
    """Stateful extraction of TG world_climate._monthly_land_bucket L746-768.

    Same float64 operation order; no alternate runoff coefficient, drainage term
    or stock reset. Caller transfers inundated soil to lakes BEFORE masking wet.
    """
    land = np.asarray(land, bool)
    rain_input, pet, previous = [np.asarray(v, np.float64) for v in (liquid_mm, pet_mm, soil_mm)]
    if any(v.shape != land.shape or not np.isfinite(v).all() or np.any(v < 0)
           for v in (rain_input, pet, previous)):
        raise ValueError('finite nonnegative liquid/PET/soil on matching land grid required')
    if np.any(previous[~land] != 0):
        raise ValueError('wet/nonland soil must be transferred before land step')
    capacity, infiltration, quickflow, et_factor = [np.where(land, parameters[key], 0.) for key in PARAMETERS]
    if (any(v.shape != land.shape or not np.isfinite(v).all() for v in (capacity, infiltration, quickflow, et_factor))
            or np.any(capacity < 0) or np.any(et_factor < 0)
            or np.any((infiltration < 0) | (infiltration > 1))
            or np.any((quickflow < 0) | (quickflow > 1))
            or not np.allclose((infiltration + quickflow)[land], 1., rtol=0, atol=1.e-14)):
        raise ValueError('invalid biome bucket parameters')
    rain = np.where(land, rain_input, 0.)
    quick = rain * quickflow
    available = previous + rain * infiltration
    evap = np.minimum(available, pet * et_factor)
    after_et = available - evap
    overflow = np.maximum(after_et - capacity, 0.)
    storage = after_et - overflow
    runoff = quick + overflow
    return dict(soil_mm=storage, runoff_mm=runoff, actual_et_mm=evap,
                residual_mm=rain - evap - runoff - (storage - previous))


def compute_year(geometry, liquid_mm, pet_mm, parameters, land, *, month_days=MONTH_DAYS,
                 max_wet_iterations=32, max_cells=1024, output_sink=None, cell_coords_xz_m=None,
                 max_spill_path_nodes=2000000):
    """Finite-year surface-water inventory; optional monthly sink avoids history RAM.

    Explicit monthly operator split: old wet soil -> lake; split upstream liquid
    by MONTH-START wet; dry bucket; settle; transfer newly flooded soil and settle
    until support stabilizes; then lake PET * month-start wet area, coefficient 1,
    limited by connected available lake stock. New inundation is not charged a
    full month's PET. Thus a completely dry initial month has ZERO lake ET.
    Seepage=0 is a declared boundary, not invented groundwater. Actual ET maps
    attribute connected-pool demand, not local column extraction. Hillslope Q and
    schematic CSR spill paths do not claim a unique hydraulic Q inside wet lakes.
    """
    from app.world_gen import lake_basin_geometry as core, graph_hydro as gh
    drainage, _ = gh.load_terragenesis()
    if geometry.certification.get('status') != 'certified':
        raise ValueError('unresolved lake geometry; refusing publication')
    land = np.asarray(land, bool)
    shape = land.shape
    n = land.size
    if n > max_cells:
        raise ValueError('finite-year compute exceeds explicit max_cells')
    if len(shape) != 2 or geometry.bed_m.size != n:
        raise ValueError('geometry/land grid mismatch')
    liquid, pet = [np.asarray(v) for v in (liquid_mm, pet_mm)]
    if any(v.shape != (12,) + shape for v in (liquid, pet)):
        raise ValueError('matching 12-month liquid/PET required')
    days = np.asarray(month_days, np.float64)
    if days.shape != (12,) or np.any(days <= 0) or not np.isfinite(days).all():
        raise ValueError('invalid month calendar')
    if (type(max_wet_iterations) is not int or max_wet_iterations < 1
            or type(max_spill_path_nodes) is not int or max_spill_path_nodes < 1):
        raise ValueError('positive wet iteration and spill path budgets required')
    area = np.asarray(geometry.area_m2).reshape(shape)
    soil = np.zeros(shape)
    state = core.settle(geometry)
    names = ('soil_mm', 'runoff_mm', 'land_actual_et_mm', 'lake_volume_m3', 'lake_stage_m',
             'lake_depth_m', 'wet_mask', 'lake_et_demand_m3', 'soil_to_lake_m3',
             'direct_lake_liquid_m3', 'terminal_overflow_m3')
    arrays = {name: [] for name in names}
    accounts = []
    monthly_transfers = []
    hillslope_volumes = []
    hillslope_support = []
    actual_lake_et_maps = []
    spill_routes = []
    for month in range(12):
        if any(not np.isfinite(v[month]).all() or np.any(v[month] < 0) for v in (liquid, pet)):
            raise ValueError('finite nonnegative monthly liquid/PET required')
        old_soil = float(np.sum(soil * area / 1000.))
        old_lake = float(state.layer_volume_by_node_m3.sum())
        month_start_wet = state.wet_mask.reshape(shape) & land
        # Rain/PET depths use float64 monthly views, not full-year copies.
        current_liquid = np.asarray(liquid[month], np.float64)
        current_pet = np.asarray(pet[month], np.float64)
        transfers = np.where(month_start_wet, soil * area / 1000., 0.)
        soil = np.where(month_start_wet, 0., soil)
        bucket = land_bucket_step(current_liquid, current_pet, parameters, land & ~month_start_wet, soil)
        soil = bucket['soil_mm']
        direct_lake = np.where(month_start_wet, current_liquid * area / 1000., 0.)
        source = bucket['runoff_mm'] * area / 1000. + direct_lake + transfers
        state = core.settle(geometry, state, source_by_cell_m3=source)
        events = list(state.transfers)
        terminal = state.overflow_by_outlet_m3.copy()
        maximum_wet = state.wet_mask.copy() | month_start_wet.ravel()
        # Each transfer clears its soil once. Bounded support iteration is needed
        # because the extra transferred soil can itself inundate additional land.
        for _ in range(max_wet_iterations):
            inundated = state.wet_mask.reshape(shape) & land & (soil > 0)
            if not inundated.any():
                break
            extra = np.where(inundated, soil * area / 1000., 0.)
            transfers += extra
            soil = np.where(inundated, 0., soil)
            state = core.settle(geometry, state, source_by_cell_m3=extra)
            events.extend(state.transfers)
            maximum_wet |= state.wet_mask
            terminal += state.overflow_by_outlet_m3
        else:
            if np.any(state.wet_mask.reshape(shape) & land & (soil > 0)):
                raise ValueError('inundated-soil support did not stabilize; refusing publication')
        demand = np.where(month_start_wet, current_pet * area / 1000., 0.)
        state = core.settle(geometry, state, withdrawal_by_cell_m3=demand)
        terminal += state.overflow_by_outlet_m3
        actual_lake_et = float(state.actual_withdrawal_m3)
        actual_map = state.actual_withdrawal_by_cell_m3.reshape(shape)
        if output_sink is None:
            actual_lake_et_maps.append(actual_map)
            monthly_transfers.append(events)
        # Defined only on slope receiver edges before entry to any monthly wet
        # support. Source/spill paths inside the pool have no unique hydraulic Q.
        # Cut OUTGOING wet edges, not incoming edges: upstream volume reaches
        # the first wet cell but never crosses the pool on a bed receiver.
        slope_receiver = np.where(maximum_wet, -1, geometry.receiver)
        hillslope = drainage.accumulate_graph(slope_receiver, geometry.order,
            (bucket['runoff_mm'] * area / 1000.).ravel())
        support = land.ravel() & ~maximum_wet & (geometry.receiver >= 0)
        path_nodes = 0
        for event in events:
            for cell in event.path:
                path_nodes += 1
                if path_nodes > max_spill_path_nodes:
                    raise ValueError('monthly spill path node budget exceeded; refusing publication')
                support[cell] = False  # separate schematic spill layer, not complete slope-only Q
        hillslope[~support] = np.nan
        if output_sink is None:
            hillslope_volumes.append(hillslope.reshape(shape))
            hillslope_support.append(support.reshape(shape))
        land_et = float(np.sum(bucket['actual_et_mm'] * area / 1000.))
        input_m3 = float(np.sum(np.where(land, current_liquid, 0.) * area / 1000.))
        new_soil = float(np.sum(soil * area / 1000.))
        new_lake = float(state.layer_volume_by_node_m3.sum())
        residual = old_soil + old_lake + input_m3 - new_soil - new_lake - land_et - actual_lake_et - terminal.sum()
        scale = max(old_soil + old_lake + input_m3, 1.)
        if not np.isfinite(residual) or abs(residual) > 1e-9 * scale or abs(state.balance_error_m3) > 1e-9 * scale:
            raise ValueError('monthly water account failed; refusing publication')
        values = (soil, bucket['runoff_mm'], bucket['actual_et_mm'], state.volume_by_cell_m3.reshape(shape),
                  state.stage_by_cell_m.reshape(shape), np.maximum(state.stage_by_cell_m - geometry.bed_m, 0.).reshape(shape),
                  state.wet_mask.reshape(shape), demand, transfers, direct_lake, terminal.reshape(shape))
        month_values = dict(zip(names, values))
        month_values.update(hillslope_routed_volume_m3=hillslope.reshape(shape),
                            hillslope_discharge_m3_s=hillslope.reshape(shape) / (days[month] * 86400.),
                            hillslope_q_support=support.reshape(shape), lake_actual_et_m3=actual_map,
                            flow_wet_support=maximum_wet.reshape(shape))
        if output_sink is None:
            for name, value in zip(names, values):
                arrays[name].append(np.array(value, copy=True))
        else:
            output_sink(month, month_values)
        if cell_coords_xz_m is not None:
            spill_routes.append(_spill_routes([events], [maximum_wet], np.asarray(cell_coords_xz_m),
                                              [days[month]], month_index=month, max_path_nodes=max_spill_path_nodes)[0])
        accounts.append(dict(month=month + 1, liquid_input_m3=input_m3, initial_soil_m3=old_soil,
                             initial_lake_m3=old_lake, final_soil_m3=new_soil, final_lake_m3=new_lake,
                             land_et_m3=land_et, lake_et_m3=actual_lake_et,
                             lake_et_unmet_m3=float(state.unmet_withdrawal_m3),
                             soil_transfer_m3=float(transfers.sum()), terminal_overflow_m3=float(terminal.sum()),
                             residual_m3=float(residual)))
    history = {} if output_sink is not None else {**{name: np.stack(values) for name, values in arrays.items()},
                        'hillslope_routed_volume_m3': np.stack(hillslope_volumes),
                        'hillslope_discharge_m3_s': np.stack(hillslope_volumes) / (days[:, None, None] * 86400.),
                        'hillslope_q_support': np.stack(hillslope_support),
                        'lake_actual_et_m3': np.stack(actual_lake_et_maps)}
    return dict(schema=SCHEMA, status='finite-year-surface-water', publishable=True, arrays=history,
                geometry_certification=geometry.certification, geometry_identity=geometry.geometry_identity,
                geometry_node_semantics='exclusive TG single-sink pool DAG plus zero-stock terminal nodes; not merge layers',
                spill_routes=spill_routes,
                lake_actual_et_map_semantics='connected-pool demand attribution, NOT local water-column extraction',
                accounts=accounts, transfer_events=monthly_transfers,
                flow_scope='hillslope runoff to first wet cell/bed sink only; spill transfers separate; wet interior flow unknown',
                month_days=days.tolist(), initial_stocks='soil=0, lake=0; saved liquid/SWE/ice immutable',
                lake_evaporation='monthly PET engineering proxy coefficient 1; month-start wet only; availability limited',
                splitting='dry first month has zero lake ET; new wet cells not charged whole-month PET',
                monthly_geometry_scope='hillslope cuts use maximum ever-wet support within month; lake background uses final wet after ET; monthly approximation may show retreated dry ground without a river',
                spill_support_scope='all cells traversed by schematic spill/terminal paths are unknown hillslope Q; both-direction gross is netted only in separate spill symbols',
                seepage_m3=0., channel_q_available=False,
                missing=['unique hydraulic lake-interior channel flux: intentionally not modeled'],
                lake_interior_q='unknown/unsupported; not a prerequisite for connected-pool inventory',
                scope='one finite empty-lake year; no steady state or perennial-channel certification')


def _saved_inputs(source_map, climate_product, hydrology_product, expected_source_identity,
                  expected_climate_identity, expected_hydrology_identity, *, monthly=False):
    import json
    from pathlib import Path
    from app.world_gen import climate_world_stage as cs
    from app.world_gen.world_climate_adapter import SavedClimateMap
    from app.world_gen.climate_hydrology_stage import SCHEMA as HYDRO_SCHEMA
    if not all((expected_source_identity, expected_climate_identity, expected_hydrology_identity)):
        raise ValueError('explicit source/climate/hydrology identities required')
    view = SavedClimateMap(source_map, climate_product, expected_source_identity=expected_source_identity,
                           expected_climate_identity=expected_climate_identity)
    # SavedClimateMap already validates bed/status/receiver/source binding. Avoid
    # climate_source_from_map: its plan_climate config check invokes a snow model.
    from app.world_gen.world_climate_adapter import _saved_array
    source_root = Path(source_map).resolve()
    source_manifest = json.loads((source_root / 'manifest.json').read_text(encoding='utf-8'))
    climate = cs.climate_module()
    layers = source_manifest['layers']
    bed = _saved_array(source_root, layers['elevation_m'], climate)
    status = _saved_array(source_root, layers['status'], climate)
    receiver = _saved_array(source_root, layers['receiver'], climate)
    info = view.terrain.info
    lagoon = (_saved_array(source_root, layers['registered_lagoon'], climate).astype(bool)
              if 'registered_lagoon' in layers else np.zeros(bed.shape, bool))
    source = dict(elevation_m=bed, ocean_mask=status == 3, receiver=receiver, registered_lagoon=lagoon,
                  order=cs.topological_order(receiver), first_xz_m=list(info.first_sample_xz_m),
                  spacing_m=float(info.spacing_m), source_identity=info.identity)
    root = Path(hydrology_product).resolve()
    meta = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    binding = meta.get('binding', {})
    if (meta.get('schema') != HYDRO_SCHEMA or meta.get('status') != 'complete'
            or meta.get('identity') != expected_hydrology_identity
            or binding.get('source_identity') != expected_source_identity
            or binding.get('climate_identity') != expected_climate_identity
            or meta.get('month_days') != list(MONTH_DAYS) or meta.get('calendar') != 'noleap365'):
        raise ValueError('saved liquid year binding/status/calendar differs')
    cs.climate_module()
    from terrain_pipeline.common_infra import identity
    if identity({}, {k: v for k, v in meta.items() if k != 'identity'}) != meta['identity']:
        raise ValueError('hydrology manifest identity differs')
    expected_grid = dict(shape_zx=list(source['elevation_m'].shape), first_xz_m=source['first_xz_m'],
                         spacing_m=source['spacing_m'])
    if binding.get('grid') != expected_grid:
        raise ValueError('saved liquid grid differs from physical source bed')
    names = ('monthly_liquid_input_mm', 'monthly_snow_swe_mm', 'monthly_ice_swe_mm')
    saved = {}
    for name in names:
        descriptor = meta['fields'].get(name, {})
        path = (root / descriptor.get('file', '')).resolve()
        expected_unit = 'mm/month' if name == 'monthly_liquid_input_mm' else 'mm'
        if (not path.is_relative_to(root) or descriptor.get('units') != expected_unit
                or descriptor.get('shape') != [12, *source['elevation_m'].shape]):
            raise ValueError('saved monthly liquid/SWE/ice descriptor differs')
        if monthly:
            if cs._sha(path) != descriptor.get('sha256'):
                raise ValueError('saved monthly input file changed')
            value = np.load(path, mmap_mode='r', allow_pickle=False)
            if value.shape != tuple(descriptor['shape']) or str(value.dtype) != descriptor['dtype']:
                raise ValueError('invalid saved monthly input')
            for month in range(12):
                if not np.isfinite(value[month]).all() or np.any(value[month] < 0):
                    raise ValueError('invalid saved monthly input')
            saved[name] = value
    return source, view, meta, saved


def plan(source_map, climate_product, hydrology_product, *, expected_source_identity,
         expected_climate_identity, expected_hydrology_identity, finite_boundary=True,
         max_cells=1024, max_memory_bytes=512 * 2**20):
    """Read static bindings/descriptors only. Never solve climate, glaciers or lakes."""
    source, _, hydro, _ = _saved_inputs(source_map, climate_product, hydrology_product,
        expected_source_identity, expected_climate_identity, expected_hydrology_identity)
    n = source['elevation_m'].size
    # CSR degree~6 for the restored irregular grid; core+mesh plus current-month
    # arrays and interpreter allowance. This is an allowance, NOT measured RSS.
    estimate = 256 * 2**20 + 2304 * n
    return dict(schema=SCHEMA, status='ready' if n <= max_cells and estimate <= max_memory_bytes else 'budget-exceeded',
                source_identity=expected_source_identity, climate_identity=expected_climate_identity,
                hydrology_identity=hydro['identity'], shape_zx=list(source['elevation_m'].shape),
                mesh_seed=MESH_SEED, mesh_policy='rebuild current TG mesh with original seed; no old code-pin bitwise equivalence claim',
                bed='immutable elevation_m; NOT bed+ice', finite_boundary=bool(finite_boundary),
                outlet_policy='ocean | explicit registered lagoon | finite domain rim' if finite_boundary else 'ocean | explicit registered lagoon',
                estimated_peak_increment_bytes=estimate, estimated_output_bytes=12 * n * 8 * 18,
                storage='monthly memmap sink; current soil/lake state only; no 12-month history stack',
                estimate_kind='conservative array allowance, not measured RSS; external process wall/RSS budget still required',
                max_cells=max_cells, max_memory_bytes=max_memory_bytes,
                flow_scope='hillslope receiver Q plus separate CSR spill path events; lake interior flow unknown',
                calendar='noleap365', years=1, initial_stocks='soil=0, lake=0',
                upstream_reuse='saved liquid/SWE/ice; no snow/ice/climate solve; old no-lake runoff/Q ignored',
                geometry_admission='unchecked: static budget plan only; call plan_geometry for TG pool certification',
                publication_requires='all TG pools single-sink certified; unresolved internal saddles/closed components reject')


def plan_geometry(source_map, climate_product, hydrology_product, *, expected_source_identity,
                  expected_climate_identity, expected_hydrology_identity, finite_boundary=True,
                  max_cells=1024, max_memory_bytes=512 * 2**20):
    """Explicit mesh/flood/certification probe. No monthly reads or finite-year run.

    Unlike plan(), this performs actual TG graph work. An unresolved report lists
    ALL rejected pool IDs/sinks, rather than silently removing their water stock.
    """
    from app.world_gen import graph_hydro as gh, lake_basin_geometry as core
    options = dict(expected_source_identity=expected_source_identity,
        expected_climate_identity=expected_climate_identity,
        expected_hydrology_identity=expected_hydrology_identity)
    planned = plan(source_map, climate_product, hydrology_product, **options,
        finite_boundary=finite_boundary, max_cells=max_cells, max_memory_bytes=max_memory_bytes)
    if planned['status'] != 'ready':
        return planned
    source, _, _, _ = _saved_inputs(source_map, climate_product, hydrology_product,
        expected_source_identity, expected_climate_identity, expected_hydrology_identity)
    shape = source['elevation_m'].shape
    mesh = gh.build_graph(shape, source['first_xz_m'], source['spacing_m'], MESH_SEED)
    outlets = source['ocean_mask'] | source['registered_lagoon']
    if finite_boundary:
        outlets = outlets.copy()
        outlets[[0, -1], :] = True
        outlets[:, [0, -1]] = True
    try:
        geometry = core.build_geometry(source['elevation_m'], mesh, outlets,
            source['spacing_m']**2, expected_source_identity, budget_bytes=max_memory_bytes)
        report = geometry.certification
    except core.GeometryCertificationError as exc:
        report = exc.report
    return dict(planned, status='geometry-certified' if report['status'] == 'certified' else 'geometry-unresolved',
        geometry_admission=report, geometry_version=core.VERSION, year_computed=False)


def prepare(source_map, climate_product, hydrology_product, out_dir, *, expected_source_identity,
            expected_climate_identity, expected_hydrology_identity, finite_boundary=True,
            registered_lagoon_mask=None, max_cells=1024, max_memory_bytes=512 * 2**20,
            max_wet_iterations=32, max_spill_path_nodes=2000000, river_options=None):
    """Write a NEW independent finite-year surface-water diagnostic sidecar.

    Cannot run a real whole world under the default small-fixture budget. Sources,
    historic no-lake diagnostics, TG, map bundles and their identities are untouched.
    """
    from pathlib import Path
    import shutil
    import tempfile
    from app.world_gen import climate_world_stage as cs, graph_hydro as gh, lake_basin_geometry as core
    planned = plan(source_map, climate_product, hydrology_product,
        expected_source_identity=expected_source_identity, expected_climate_identity=expected_climate_identity,
        expected_hydrology_identity=expected_hydrology_identity, finite_boundary=finite_boundary,
        max_cells=max_cells, max_memory_bytes=max_memory_bytes)
    if planned['status'] != 'ready':
        raise ValueError('planned cell/memory budget exceeded; refusing publication')
    out = Path(out_dir).resolve()
    for parent in map(lambda p: Path(p).resolve(), (source_map, climate_product, hydrology_product)):
        if out == parent or out.is_relative_to(parent):
            raise ValueError('new sidecar must be outside immutable parents')
    if out.exists():
        raise FileExistsError('new sidecar directory required')
    source, view, hydro, saved = _saved_inputs(source_map, climate_product, hydrology_product,
        expected_source_identity, expected_climate_identity, expected_hydrology_identity, monthly=True)
    shape = source['elevation_m'].shape
    mesh = gh.build_graph(shape, source['first_xz_m'], source['spacing_m'], MESH_SEED)
    lagoon = (source['registered_lagoon'] if registered_lagoon_mask is None
              else np.asarray(registered_lagoon_mask, bool))
    if lagoon.shape != shape:
        raise ValueError('registered lagoon mask grid mismatch')
    outlets = source['ocean_mask'] | lagoon
    if finite_boundary:
        outlets = outlets.copy(); outlets[[0, -1], :] = True; outlets[:, [0, -1]] = True
    geometry = core.build_geometry(source['elevation_m'], mesh, outlets, source['spacing_m']**2,
                                   expected_source_identity, budget_bytes=max_memory_bytes)
    planned = dict(planned, geometry_admission=geometry.certification)
    native = view.query(list(PARAMETERS))['arrays']
    from app.world_gen.world_climate_adapter import _saved_array
    pet = _saved_array(view.product, view.fields['monthly_pet_mm'], cs.climate_module())
    out.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='.climate-lakes-', dir=out.parent))
    maps = {}
    try:
        def sink(month, values):
            for name, value in values.items():
                if name not in maps:
                    maps[name] = np.lib.format.open_memmap(work / (name + '.npy'), mode='w+',
                        dtype=value.dtype, shape=(12,) + shape)
                maps[name][month] = value
        coords = np.column_stack((mesh.node_x_m, mesh.node_z_m))
        result = compute_year(geometry, saved['monthly_liquid_input_mm'], pet, native, ~source['ocean_mask'],
                              max_cells=max_cells, max_wet_iterations=max_wet_iterations,
                              output_sink=sink, cell_coords_xz_m=coords, max_spill_path_nodes=max_spill_path_nodes)
        # Integrate monthly volumes one month at a time; unknown support in any
        # month remains unknown annual mean rather than nanmean pretending zero.
        mean = np.zeros(shape); all_known = np.ones(shape, bool)
        for month in range(12):
            v = maps['hillslope_routed_volume_m3'][month]
            all_known &= np.isfinite(v); mean += np.nan_to_num(v, nan=0.)
        mean /= sum(MONTH_DAYS) * 86400.; mean[~all_known] = np.nan
        for value in maps.values():
            value.flush(); value._mmap.close()
        maps.clear()
        static = dict(receiver=geometry.receiver.reshape(shape), order=geometry.order,
                      old_no_lake_receiver=np.asarray(source['receiver']), basin_id=geometry.drain_node_by_cell.reshape(shape),
                      mesh_node_x_m=mesh.node_x_m, mesh_node_z_m=mesh.node_z_m,
                      annual_mean_hillslope_discharge_m3_s=mean,
                      geometry_parent=geometry.parent, geometry_birth_m=geometry.birth_m,
                      geometry_crest_m=geometry.crest_m, geometry_cell_node=geometry.cell_node.reshape(shape),
                      geometry_area_m2=geometry.area_m2.reshape(shape),
                      mesh_indptr=geometry.indptr, mesh_indices=geometry.indices)
        for name, value in static.items():
            np.save(work / (name + '.npy'), value, allow_pickle=False)
        # Trace the supplied true-bed receiver with geometrical area accumulated
        # on THIS graph, never the historical no-lake area/receiver product.
        from app.world_gen.river_flow_network import build_flow_network
        drainage, _ = gh.load_terragenesis()
        route_area = drainage.accumulate_graph(geometry.receiver, geometry.order, geometry.area_m2)
        qmap = np.load(work / 'hillslope_discharge_m3_s.npy', mmap_mode='r')
        wetmap = np.load(work / 'flow_wet_support.npy', mmap_mode='r')
        try:
            rivers = build_flow_network(geometry.receiver, geometry.order, qmap, route_area,
                dict(shape_zx=shape, first_xz_m=source['first_xz_m'], spacing_m=source['spacing_m']),
                ocean=source['ocean_mask'], monthly_wet_lake=wetmap, cell_coords_xz_m=coords,
                **(river_options or {}))
            cs._write_json(work / 'hillslope-draw.json', rivers)
        finally:
            qmap._mmap.close(); wetmap._mmap.close()
        # Saved snow/ice/liquid are reused verbatim, not recalculated or added.
        for name, value in saved.items():
            shutil.copyfile(Path(hydrology_product) / hydro['fields'][name]['file'], work / (name + '.npy'))
        fields = {}
        for path in work.glob('*.npy'):
            value = np.load(path, mmap_mode='r', allow_pickle=False)
            fields[path.stem] = dict(file=path.name, shape=list(value.shape), dtype=str(value.dtype),
                                     units=_field_unit(path.stem), sha256=cs._sha(path))
            value._mmap.close()
        cs._write_json(work / 'spill-routes.json', result['spill_routes'])
        cs._write_json(work / 'water-budget.json', result['accounts'])
        record = {k: v for k, v in result.items() if k not in ('arrays', 'accounts', 'transfer_events', 'spill_routes')}
        from terrain_pipeline.common_infra import array_sha256
        record.update(binding=planned, fields=fields, geometry_version=core.VERSION,
                      lagoon_binding=dict(origin='saved registered_lagoon layer' if registered_lagoon_mask is None else 'explicit override',
                                          array_sha256=array_sha256(lagoon)),
                      geometry_binding=dict(bed_sha256=array_sha256(source['elevation_m']),
                          receiver_sha256=array_sha256(geometry.receiver), mesh_seed=MESH_SEED,
                          outlet_sha256=array_sha256(outlets)),
                      hillslope_draw_file='hillslope-draw.json', river_parameters=rivers['parameters'],
                      geometry_code_sha256=cs._sha(Path(core.__file__)),
                      max_spill_path_nodes_per_month=max_spill_path_nodes,
                      spill_routes_file='spill-routes.json', water_budget_file='water-budget.json',
                      files={p.name: cs._sha(p) for p in work.iterdir() if p.is_file()},
                      classification_scope='finite-year supply symbols, NOT permanent channel existence or long-term perennial certification',
                      original_hydrology_regions=hydro['binding'].get('regions', []),
                      source_receiver_role='historic no-lake receiver retained separately, never physical lake spill Q')
        from terrain_pipeline.common_infra import identity
        record['identity'] = identity({}, record)
        cs._write_json(work / 'manifest.json', record)
        work.rename(out)
        return record
    finally:
        for value in maps.values():
            value._mmap.close()
        if work.exists():
            shutil.rmtree(work)


def _spill_routes(events_by_month, wet_by_month, coords, month_days, max_segments=18000, month_index=0,
                  max_path_nodes=2000000):
    """Net schematic gross transfers on reproducible CSR paths, never lake Q.

    A crossed edge may be traversed in both directions during split settling;
    cancel opposing gross amounts, omit zero, and declare remaining routes as
    monthly net *symbol* transfers. Dry-only edge geometry avoids wet-lake chords.
    """
    routes = []
    for month, events in enumerate(events_by_month):
        net = {}
        count = 0
        for event in events:
            previous = None
            for cell in event.path:
                count += 1
                if count > max_path_nodes:
                    raise ValueError('monthly spill path node budget exceeded; refusing publication')
                if previous is None:
                    previous = cell
                    continue
                a, b = previous, cell
                previous = cell
                key = tuple(sorted((a, b)))
                net[key] = net.get(key, 0.) + (event.volume_m3 if a < b else -event.volume_m3)
        wet = np.asarray(wet_by_month[month]).ravel()
        current = []
        for (lo, hi), amount in sorted(net.items()):
            if abs(amount) < 1e-12 or wet[lo] or wet[hi]:
                continue
            a, b = (lo, hi) if amount > 0 else (hi, lo)
            volume = abs(float(amount))
            current.append(dict(id=f'spill-m{month+month_index+1:02d}:{a}-{b}', month=month + month_index + 1,
                                nodes=[a, b], points_xz_m=coords[[a, b]].tolist(),
                                net_transferred_volume_m3=volume,
                                symbol_mean_m3_s=volume / (month_days[month] * 86400.),
                                path_semantics='deterministic CSR schematic net transfer; NOT hydraulic receiver Q',
                                blue=True, symbol_width=1.0))
        if len(current) > max_segments:
            raise ValueError('spill route symbols exceed max_segments; refusing publication')
        routes.append(current)
    return routes


def _field_unit(name):
    if name.endswith('_m3_s'):
        return 'm3/s'
    if name.endswith('_m3'):
        return 'm3/month' if name in ('runoff_m3', 'terminal_overflow_m3', 'lake_actual_et_m3',
                                      'lake_et_demand_m3', 'direct_lake_liquid_m3',
                                      'soil_to_lake_m3', 'hillslope_routed_volume_m3') else 'm3'
    if name.endswith('_m2'):
        return 'm2'
    if name.endswith('_mm'):
        return 'mm/month' if name in ('monthly_liquid_input_mm', 'runoff_mm', 'land_actual_et_mm') else 'mm'
    if name.endswith('_m'):
        return 'm'
    return '1'
