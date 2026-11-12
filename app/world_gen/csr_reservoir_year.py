"""Saved-liquid finite year: TG CSR reservoirs, not instant single-pool settling."""
from __future__ import annotations

from types import SimpleNamespace
import time
import numpy as np

from .climate_lake_stage import SCHEMA, MESH_SEED, MONTH_DAYS, PARAMETERS, land_bucket_step, _saved_inputs, _field_unit
from .csr_reservoir_adapter import build_csr_reservoirs

VERSION = 'dream-csr-finite-conductance-1'
BACKEND = 'tg-csr-reservoir-finite-conductance'


def build_network(bed, mesh, ocean, *, lagoon=None, finite_boundary=True, area_m2=1.,
                  max_owners=10000, face_width_m=1., face_conductance_m_s=.6):
    """All native nonterminal land supplies full owner hypsometry, not clipped banks.

    Hillslopes remain true-bed routed; grouping their supply into sink owners is
    the lumped-catchment forcing of TG's reservoir backend, not channel travel.
    """
    from .lake_basin_geometry import _bed_routes
    z = np.asarray(bed, float).ravel()
    shape = np.asarray(bed).shape
    terminal = np.asarray(ocean, bool).reshape(shape).copy()
    if lagoon is not None:
        terminal |= np.asarray(lagoon, bool).reshape(shape)
    if finite_boundary:
        if len(shape) != 2:
            raise ValueError('finite rim requires a 2D native grid')
        terminal[[0, -1], :] = True; terminal[:, [0, -1]] = True
    receiver, order, sink = _bed_routes(z, mesh.indptr, mesh.indices, terminal.ravel())
    active = ~terminal.ravel()
    faces = []
    for c in np.flatnonzero(active):
        for j in mesh.indices[mesh.indptr[c]:mesh.indptr[c + 1]]:
            if terminal.ravel()[j]:
                faces.append(dict(cell_id=int(c), receiver_cell_id=int(j), sill_m=float(max(z[c], z[j])),
                                  width_m=float(face_width_m), kind='ocean'))
    # Boundary metadata below distinguishes native ocean, lagoon and finite rim.
    g = None if not active.any() else build_csr_reservoirs(z, mesh, area_m2,
        cell_mask=active, boundary_faces=faces, face_width_m=face_width_m,
        face_conductance_m_s=face_conductance_m_s, boundary_conductance_m_s=face_conductance_m_s)
    if g is not None and g.owner_count > max_owners:
        raise ValueError('CSR owner budget exceeded')
    if g is not None:
        from .csr_reservoir_adapter import _tg
        for face in g.topology['engineering_boundaries']:
            j = face['receiver_cell_id']
            face['terminal_kind'] = ('ocean' if np.asarray(ocean).ravel()[j] else
                                     'lagoon' if lagoon is not None and np.asarray(lagoon).ravel()[j] else 'finite-rim')
        g.topology['identity_sha256'] = _tg()._topology_identity(g.topology)
    return SimpleNamespace(reservoirs=g, bed_m=z, area_m2=np.broadcast_to(area_m2, shape).ravel().copy(),
                           receiver=receiver, order=order, sink=sink, terminal=terminal.ravel(),
                           shape=shape, mesh=mesh, ocean=np.asarray(ocean, bool).ravel())


def compute_year(network, liquid_mm, pet_mm, parameters, land, *, month_days=MONTH_DAYS,
                 max_cells=1024, max_steps=4096, max_wet_iterations=32, wall_seconds=1200.,
                 output_sink=None, cell_coords_xz_m=None, progress=None):
    from .graph_hydro import load_terragenesis
    drainage, _ = load_terragenesis()
    started = time.monotonic()
    n, shape, g = network.bed_m.size, network.shape, network.reservoirs
    land = np.asarray(land, bool).reshape(shape)
    liquid, pet = np.asarray(liquid_mm), np.asarray(pet_mm)
    days = np.asarray(month_days, float)
    if n > max_cells or liquid.shape != (12,) + shape or pet.shape != liquid.shape:
        raise ValueError('cell/month input budget or shape differs')
    if days.shape != (12,) or not np.isfinite(days).all() or (days <= 0).any():
        raise ValueError('positive finite month calendar required')
    if max_steps < 1 or max_wet_iterations < 1 or not np.isfinite(wall_seconds) or wall_seconds <= 0:
        raise ValueError('positive integration/wet/wall budgets required')
    area = network.area_m2.reshape(shape)
    soil = np.zeros(shape)
    stocks = np.zeros(0 if g is None else g.owner_count)
    def geometry():
        if g is not None:
            return g.geometry_at_volumes(stocks)
        return dict(wet_mask=np.zeros(n, bool), stage_by_cell_m=network.bed_m.copy(),
                    depth_by_cell_m=np.zeros(n), volume_by_cell_m3=np.zeros(n))
    state, histories, accounts, routes, work, ledgers = geometry(), {}, [], [], [], []
    coords = None if cell_coords_xz_m is None else np.asarray(cell_coords_xz_m)
    for month in range(12):
        if time.monotonic() - started > wall_seconds:
            raise ValueError('CSR year wall budget exceeded')
        rain, demand_depth = np.asarray(liquid[month], float), np.asarray(pet[month], float)
        if any(not np.isfinite(v).all() or (v < 0).any() for v in (rain, demand_depth)):
            raise ValueError('finite nonnegative saved liquid/PET required')
        month_started = time.monotonic()
        old_soil, old_lake = float((soil * area / 1000.).sum()), float(stocks.sum())
        oldwet = state['wet_mask'].reshape(shape) & land
        transfers = np.where(oldwet, soil * area / 1000., 0.)
        start_transfers = transfers.copy()
        end_transfers = np.zeros(shape)
        soil = np.where(oldwet, 0., soil)
        bucket = land_bucket_step(rain, demand_depth, parameters, land & ~oldwet, soil)
        soil = bucket['soil_mm']
        direct = np.where(oldwet, rain * area / 1000., 0.)
        source = bucket['runoff_mm'] * area / 1000. + direct + transfers
        demand = np.where(oldwet, demand_depth * area / 1000., 0.)
        terminal = np.where(network.terminal.reshape(shape), source, 0.).copy()
        actual = np.zeros(shape)
        forward = reverse = np.zeros(0)
        if g is not None:
            owner_demand = g.aggregate_cells(demand.ravel())
            # Explicit engineering split: monthly source impulse, old-wet ET,
            # then exactly ONE month of finite-conductance TG exchange.
            available = stocks + g.aggregate_cells(source.ravel())
            result = g.advance(available, np.zeros(g.owner_count), days[month] * 86400.,
                               withdrawal_m3=owner_demand, max_steps=max_steps)
            stocks = result['owner_stocks_m3']
            ratio = np.divide(result['withdrawn_m3'], owner_demand, out=np.zeros_like(owner_demand), where=owner_demand > 0)
            selected = g.cell_owner >= 0
            actual.ravel()[selected] = demand.ravel()[selected] * ratio[g.cell_owner[selected]]
            for face, amount in zip(g.topology['engineering_boundaries'], result['boundary_exports_m3']):
                terminal.ravel()[face['receiver_cell_id']] += amount
            forward, reverse = result['face_forward_m3'], result['face_reverse_m3']
            work.append(result['metadata'])
            ledgers.append(dict(month=month+1, face_forward_m3=forward.tolist(), face_reverse_m3=reverse.tolist(),
                face_net_m3=(forward-reverse).tolist(), boundary_exports_m3=result['boundary_exports_m3'].tolist(),
                owner_initial_m3=available.tolist(), owner_withdrawn_m3=result['withdrawn_m3'].tolist(),
                owner_after_exchange_m3=stocks.tolist(), owner_residual_m3=result['budget']['owner_residual_m3'].tolist(),
                roundoff_correction_by_owner_m3=result['budget']['roundoff_correction_by_owner_m3'].tolist()))
        state = geometry()
        maximum_wet = oldwet.ravel() | state['wet_mask']
        # Soil transfer is internal stock conversion at month end, not another dt.
        for _ in range(max_wet_iterations):
            wet_soil = state['wet_mask'].reshape(shape) & land & (soil > 0.)
            if not wet_soil.any():
                break
            extra = np.where(wet_soil, soil * area / 1000., 0.)
            transfers += extra; end_transfers += extra; soil = np.where(wet_soil, 0., soil)
            stocks += g.aggregate_cells(extra.ravel())
            state = geometry(); maximum_wet |= state['wet_mask']
        else:
            if (state['wet_mask'].reshape(shape) & (soil > 0)).any():
                raise ValueError('CSR month-end soil support budget exceeded')
        cut = np.where(maximum_wet, -1, network.receiver)
        hillslope = drainage.accumulate_graph(cut, network.order, (bucket['runoff_mm'] * area / 1000.).ravel())
        support = land.ravel() & ~maximum_wet & (network.receiver >= 0)
        hillslope[~support] = np.nan
        current_routes = []
        if g is not None and coords is not None:
            for index, (face, volume) in enumerate(zip(g.topology['faces'], forward - reverse)):
                a, b = face['cell_ids']
                if abs(volume) <= 1e-12 or (maximum_wet[a] and maximum_wet[b]):
                    continue
                if volume < 0:
                    a, b = b, a
                current_routes.append(dict(id=f'csr-m{month+1:02d}-{index}', month=month+1, nodes=[a,b],
                    points_xz_m=coords[[a,b]].tolist(), net_transferred_volume_m3=abs(float(volume)),
                    symbol_mean_m3_s=abs(float(volume))/(days[month]*86400.), blue=True, symbol_width=1.,
                    path_semantics='actual TG owner-face net quadrature on one true CSR edge; not lake-interior channel Q'))
        routes.append(current_routes)
        values = dict(soil_mm=soil, runoff_mm=bucket['runoff_mm'], land_actual_et_mm=bucket['actual_et_mm'],
            lake_volume_m3=state['volume_by_cell_m3'].reshape(shape), lake_stage_m=state['stage_by_cell_m'].reshape(shape),
            lake_depth_m=state['depth_by_cell_m'].reshape(shape), wet_mask=state['wet_mask'].reshape(shape),
            lake_et_demand_m3=demand, soil_to_lake_m3=transfers, direct_lake_liquid_m3=direct,
            terminal_overflow_m3=terminal, hillslope_routed_volume_m3=hillslope.reshape(shape),
            hillslope_discharge_m3_s=hillslope.reshape(shape)/(days[month]*86400.),
            hillslope_q_support=support.reshape(shape), lake_actual_et_m3=actual, flow_wet_support=maximum_wet.reshape(shape))
        if output_sink is None:
            for name, value in values.items():
                histories.setdefault(name, []).append(value.copy())
        else:
            output_sink(month, values)
        input_m3, land_et = float((np.where(land, rain, 0.) * area / 1000.).sum()), float((bucket['actual_et_mm'] * area / 1000.).sum())
        final_soil, final_lake = float((soil * area / 1000.).sum()), float(stocks.sum())
        correction_m3 = 0. if g is None else result['budget']['roundoff_correction_m3']
        residual = old_soil + old_lake + input_m3 + correction_m3 - final_soil - final_lake - land_et - actual.sum() - terminal.sum()
        if not np.isfinite(residual) or abs(residual) > 1e-9 * max(1., old_soil + old_lake + input_m3):
            raise ValueError('CSR monthly source/soil/lake/ET/export budget failed')
        accounts.append(dict(month=month+1, liquid_input_m3=input_m3, initial_soil_m3=old_soil, initial_lake_m3=old_lake,
            final_soil_m3=final_soil, final_lake_m3=final_lake, land_et_m3=land_et, lake_et_m3=float(actual.sum()),
            lake_et_unmet_m3=float(demand.sum()-actual.sum()), soil_transfer_m3=float(transfers.sum()),
            terminal_overflow_m3=float(terminal.sum()), roundoff_correction_m3=correction_m3, residual_m3=float(residual)))
        if g is not None:
            ledgers[-1].update(owner_final_m3=stocks.tolist(),
                owner_month_start_soil_transfer_m3=g.aggregate_cells(start_transfers.ravel()).tolist(),
                owner_postexchange_soil_transfer_m3=g.aggregate_cells(end_transfers.ravel()).tolist())
        if progress is not None:
            progress(dict(month=month+1, owner_count=0 if g is None else g.owner_count,
                accepted_steps=0 if g is None else work[-1]['accepted_steps'], nfev=0 if g is None else work[-1]['nfev'],
                elapsed_s=time.monotonic()-started, month_elapsed_s=time.monotonic()-month_started))
    identity = 'no-reservoirs' if g is None else g.topology['identity_sha256']
    return dict(schema=SCHEMA, backend=BACKEND, geometry_version=VERSION, status='finite-year-surface-water', publishable=True,
        arrays={k:np.stack(v) for k,v in histories.items()}, accounts=accounts, spill_routes=routes,
        integration_work=work, face_ledgers=ledgers, hydraulic_ready=False, natural_outlet_verified=False,
        geometry_numerics='cell depth from TG relative owner head minus bed relative to owner bottom; absolute stage for display',
        geometry_identity=identity, geometry_certification=dict(status='engineering-csr-adapter', original_source_certified=False,
            natural_outlet_verified=False, hydraulic_ready=False), geometry_node_semantics='independent downhill owners coupled by real CSR saddle faces; no merge tree',
        month_days=days.tolist(), initial_stocks='soil=0, lake=0; saved liquid/SWE/ice immutable', seepage_m3=0.,
        splitting='month-start input impulse; month-start-wet owner-local ET availability; one month TG finite exchange; month-end soil-to-lake geometry-only transfer (may drain next month)',
        lake_evaporation='PET coefficient 1; old wet only; owner-local, not whole-connected-pool withdrawal',
        flow_scope='true-bed hillslope runoff to first monthly wet support; wet-interior Q unknown; lumped owner supplies have no channel travel time',
        lake_actual_et_map_semantics='owner-local demand attribution, not column extraction', channel_q_available=False,
        scope='one finite empty-stock year; engineering conductance, no steady/perennial/hydraulic certification')


def plan(source_map, climate_product, hydrology_product, *, expected_source_identity, expected_climate_identity,
         expected_hydrology_identity, finite_boundary=True, max_cells=1024, max_memory_bytes=3*2**30,
         max_owners=10000, max_steps=4096, wall_seconds=1200., face_conductance_m_s=.6):
    source, _, hydro, _ = _saved_inputs(source_map, climate_product, hydrology_product,
        expected_source_identity, expected_climate_identity, expected_hydrology_identity)
    n = source['elevation_m'].size
    estimate = 384*2**20 + 2304*n
    return dict(schema=SCHEMA, backend=BACKEND, geometry_version=VERSION,
        status='ready' if n <= max_cells and estimate <= max_memory_bytes else 'budget-exceeded',
        source_identity=expected_source_identity, climate_identity=expected_climate_identity, hydrology_identity=hydro['identity'],
        shape_zx=list(source['elevation_m'].shape), mesh_seed=MESH_SEED, finite_boundary=finite_boundary,
        estimated_peak_increment_bytes=estimate, estimate_kind='array allowance, not measured sparse LU/RSS; enforce external process limits',
        max_cells=max_cells, max_memory_bytes=max_memory_bytes, max_owners=max_owners, max_steps=max_steps, wall_seconds=wall_seconds,
        face_conductance_m_s=face_conductance_m_s, calendar='noleap365', years=1,
        geometry_admission='true CSR topology identity checked; no D4 or single-sink certification',
        network_support='all native nonterminal land for full owner hypsometry; not truncated positive-fill banks',
        upstream_reuse='saved monthly liquid/SWE/ice; no rainfall/baseflow/snow/ice recalculation')


def prepare(source_map, climate_product, hydrology_product, out_dir, *, checkpoint_dir=None,
            min_display_area_m2=0., dry_valley_min_area_m2=1e10, display_policy=None, **options):
    """New immutable sidecar; bounded compute. Does not publish or modify bundles."""
    import shutil, tempfile
    from pathlib import Path
    from . import climate_world_stage as cs, graph_hydro as gh
    from .world_climate_adapter import _saved_array
    started = time.monotonic()
    planned = plan(source_map, climate_product, hydrology_product, **options)
    if planned['status'] != 'ready':
        raise ValueError('CSR plan budget exceeded')
    out = Path(out_dir).resolve()
    if out.exists() or any(out == Path(p).resolve() or out.is_relative_to(Path(p).resolve())
                           for p in (source_map, climate_product, hydrology_product)):
        raise ValueError('new sidecar outside immutable input directories required')
    checkpoint = Path(checkpoint_dir).resolve() if checkpoint_dir is not None else out.with_name(out.name+'.months-checkpoint')
    if checkpoint.exists() or checkpoint == out or any(checkpoint == Path(p).resolve() or checkpoint.is_relative_to(Path(p).resolve())
                          for p in (source_map, climate_product, hydrology_product)):
        raise ValueError('new independent monthly checkpoint directory required')
    source, view, hydro, saved = _saved_inputs(source_map, climate_product, hydrology_product,
        planned['source_identity'], planned['climate_identity'], planned['hydrology_identity'], monthly=True)
    shape, spacing = source['elevation_m'].shape, source['spacing_m']
    mesh = gh.build_graph(shape, source['first_xz_m'], spacing, MESH_SEED)
    net = build_network(source['elevation_m'], mesh, source['ocean_mask'], lagoon=source['registered_lagoon'],
        finite_boundary=planned['finite_boundary'], area_m2=spacing**2, max_owners=planned['max_owners'],
        face_width_m=spacing, face_conductance_m_s=planned['face_conductance_m_s'])
    native = view.query(list(PARAMETERS))['arrays']
    pet = _saved_array(view.product, view.fields['monthly_pet_mm'], cs.climate_module())
    out.parent.mkdir(parents=True, exist_ok=True)
    workdir = Path(tempfile.mkdtemp(prefix='.csr-lakes-', dir=out.parent))
    maps = {}
    try:
        def sink(month, values):
            for name, value in values.items():
                if name not in maps:
                    maps[name] = np.lib.format.open_memmap(workdir/(name+'.npy'), mode='w+', dtype=value.dtype, shape=(12,)+shape)
                maps[name][month] = value
        coords = np.column_stack((mesh.node_x_m, mesh.node_z_m))
        result = compute_year(net, saved['monthly_liquid_input_mm'], pet, native, ~source['ocean_mask'],
            max_cells=planned['max_cells'], max_steps=planned['max_steps'], wall_seconds=planned['wall_seconds'],
            output_sink=sink, cell_coords_xz_m=coords,
            progress=lambda data: print('CSR_MONTH ' + __import__('json').dumps(data), flush=True))
        mean, known = np.zeros(shape), np.ones(shape, bool)
        for month in range(12):
            v = maps['hillslope_routed_volume_m3'][month]
            known &= np.isfinite(v); mean += np.nan_to_num(v, nan=0.)
        mean /= sum(MONTH_DAYS)*86400.; mean[~known] = np.nan
        g = net.reservoirs
        owner = np.full(net.bed_m.size, -1, np.int64) if g is None else g.cell_owner
        bottom = np.zeros(0) if g is None else g.exchange.system.bottom
        crest = np.full(bottom.size, np.inf)
        if g is not None:
            for face in g.topology['faces']:
                for leaf in face['leaf_ids']:
                    i = int(g.cell_owner[leaf])
                    crest[i] = min(crest[i], face['sill_m'])
            for face in g.topology['engineering_boundaries']:
                i = int(g.cell_owner[face['cell_id']]); crest[i] = min(crest[i], face['sill_m'])
        static = dict(receiver=net.receiver.reshape(shape), order=net.order, old_no_lake_receiver=np.asarray(source['receiver']),
            basin_id=owner.reshape(shape), geometry_cell_node=owner.reshape(shape), geometry_parent=np.full(bottom.size,-1,np.int64),
            geometry_birth_m=bottom, geometry_crest_m=crest, geometry_area_m2=net.area_m2.reshape(shape),
            mesh_indptr=mesh.indptr, mesh_indices=mesh.indices, mesh_node_x_m=mesh.node_x_m, mesh_node_z_m=mesh.node_z_m,
            annual_mean_hillslope_discharge_m3_s=mean)
        if g is not None:
            cs._write_json(workdir/'csr-topology.json', dict(metadata=g.topology['metadata'],
                arrays={k:v.tolist() for k,v in g.topology['arrays'].items()}, faces=g.topology['faces'],
                engineering_boundaries=g.topology['engineering_boundaries'], identity_sha256=g.topology['identity_sha256']))
        for name, value in static.items():
            np.save(workdir/(name+'.npy'), value, allow_pickle=False)
        for value in maps.values():
            value.flush(); value._mmap.close()
        maps.clear()
        for name in saved:
            shutil.copyfile(Path(hydrology_product)/hydro['fields'][name]['file'], workdir/(name+'.npy'))
        fields = {}
        for path in workdir.glob('*.npy'):
            value = np.load(path, mmap_mode='r', allow_pickle=False)
            fields[path.stem] = dict(file=path.name, shape=list(value.shape), dtype=str(value.dtype), units=_field_unit(path.stem), sha256=cs._sha(path))
            value._mmap.close()
        cs._write_json(workdir/'spill-routes.json', result['spill_routes']); cs._write_json(workdir/'water-budget.json', result['accounts'])
        cs._write_json(workdir/'csr-face-ledger.json', result['face_ledgers'])
        record = {k:v for k,v in result.items() if k not in ('arrays','accounts','spill_routes','face_ledgers')}
        from terrain_pipeline.common_infra import identity, array_sha256
        record.update(binding=planned, fields=fields, geometry_code_sha256=cs._sha(Path(__file__)),
            geometry_binding=dict(bed_sha256=array_sha256(source['elevation_m']), receiver_sha256=array_sha256(net.receiver),
                mesh_seed=MESH_SEED, outlet_sha256=array_sha256(net.terminal.reshape(shape)), backend=BACKEND),
            lagoon_binding=dict(origin='saved registered_lagoon layer', array_sha256=array_sha256(source['registered_lagoon'])),
            hillslope_draw_file='hillslope-draw.json',
            spill_routes_file='spill-routes.json', water_budget_file='water-budget.json',
            topology_file='csr-topology.json' if g is not None else None, face_ledger_file='csr-face-ledger.json',
            cost=dict(elapsed_s=time.monotonic()-started, owner_count=0 if g is None else g.owner_count,
                      face_count=0 if g is None else g.exchange.faces, max_steps_per_month=planned['max_steps']),
            files={p.name:cs._sha(p) for p in workdir.iterdir() if p.is_file()},
            original_hydrology_regions=hydro['binding'].get('regions',[]), source_receiver_role='historical only; no lake spill Q')
        # Persist all completed physical month data BEFORE display extraction.
        # This is deliberately not a complete surface-water manifest.
        np.save(workdir/'_checkpoint_ocean.npy', source['ocean_mask'], allow_pickle=False)
        checkpoint_record = dict(schema='dream-csr-month-checkpoint-1', status='monthly-complete-not-finalized',
            months_complete=12, record=record,
            grid=dict(shape_zx=list(shape), first_xz_m=source['first_xz_m'], spacing_m=spacing),
            files={p.name:cs._sha(p) for p in workdir.iterdir() if p.is_file()})
        checkpoint_record['identity'] = identity({},checkpoint_record)
        cs._write_json(workdir/'checkpoint.json', checkpoint_record)
        checkpoint.parent.mkdir(parents=True,exist_ok=True)
        workdir.rename(checkpoint)
        print('CSR_CHECKPOINT '+str(checkpoint),flush=True)
        return finalize_checkpoint(checkpoint,out,min_display_area_m2=min_display_area_m2,
            dry_valley_min_area_m2=dry_valley_min_area_m2,display_policy=display_policy)
    finally:
        for value in maps.values():
            value._mmap.close()
        if workdir.exists():
            shutil.rmtree(workdir)


def finalize_checkpoint(checkpoint_dir, out_dir, *, min_display_area_m2=0.,
                        dry_valley_min_area_m2=1e10, display_policy=None):
    """Display-only retry from twelve persisted months; never rerun water physics."""
    import json, shutil, tempfile
    from pathlib import Path
    from . import climate_world_stage as cs, graph_hydro as gh
    from .river_flow_network import build_flow_network
    gh.load_terragenesis()
    from terrain_pipeline.common_infra import identity
    started=time.monotonic(); checkpoint=Path(checkpoint_dir).resolve(); out=Path(out_dir).resolve()
    state=json.loads((checkpoint/'checkpoint.json').read_text(encoding='utf-8'))
    if (state.get('schema')!='dream-csr-month-checkpoint-1' or state.get('status')!='monthly-complete-not-finalized'
            or state.get('months_complete')!=12
            or identity({}, {k:v for k,v in state.items() if k!='identity'})!=state.get('identity')):
        raise ValueError('complete-month checkpoint identity/status differs')
    if out.exists() or out==checkpoint or out.is_relative_to(checkpoint) or checkpoint.is_relative_to(out):
        raise ValueError('new final output outside retained checkpoint required')
    for name, sha in state['files'].items():
        path=(checkpoint/name).resolve()
        if not path.is_relative_to(checkpoint) or cs._sha(path)!=sha:
            raise ValueError('completed monthly checkpoint file changed')
    maps={}
    def load(name):
        maps[name]=np.load(checkpoint/(name+'.npy'),mmap_mode='r',allow_pickle=False)
        return maps[name]
    out.parent.mkdir(parents=True,exist_ok=True)
    work=Path(tempfile.mkdtemp(prefix='.csr-finalize-',dir=out.parent))
    try:
        receiver,order=load('receiver').ravel(),load('order')
        area=load('geometry_area_m2').ravel()
        drainage,_=gh.load_terragenesis()
        route_area=drainage.accumulate_graph(receiver,order,area)
        coords=np.column_stack((load('mesh_node_x_m'),load('mesh_node_z_m')))
        rivers=build_flow_network(receiver,order,load('hillslope_discharge_m3_s'),route_area,state['grid'],
            ocean=load('_checkpoint_ocean'),monthly_wet_lake=load('flow_wet_support'),cell_coords_xz_m=coords,
            min_display_area_m2=min_display_area_m2,dry_valley_min_area_m2=dry_valley_min_area_m2)
        # Copies isolate immutable physics checkpoint from final display artifacts.
        for name in state['record']['files']:
            shutil.copyfile(checkpoint/name,work/name)
        cs._write_json(work/'hillslope-draw.json',rivers)
        record=state['record']
        record.update(river_parameters=rivers['parameters'],cartographic_policy=display_policy or
            'explicit display-only geometric-area thresholds; no hydrological absence inference',
            river_display_summary=rivers['summary'],checkpoint_identity=state['identity'])
        record['cost'].update(finalize_elapsed_s=time.monotonic()-started)
        record['files']={p.name:cs._sha(p) for p in work.iterdir() if p.is_file()}
        record['identity']=identity({},record)
        cs._write_json(work/'manifest.json',record); work.rename(out)
        return record
    finally:
        for value in maps.values():
            value._mmap.close()
        if work.exists():
            shutil.rmtree(work)
