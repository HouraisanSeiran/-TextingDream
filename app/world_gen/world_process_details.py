"""Author-side TD preparation and serial world process continuation.

Only this explicit command may prepare missing model terrain. Map queries read
the immutable coarse preview or the newly published detailed revision.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.world_gen import graph_hydro as gh, local30, tiles
from app.world_gen.fast_relief import file_sha, identity_of, write_json


def _read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _preparation_identity(record):
    result = {key: value for key, value in record.items() if key not in ('memory_wait_s', 'memory_poll_s')}
    result.setdefault('terrain_roots', [])  # early preparations predate explicit cache roots
    return result


def _verified_entry(path, *, plate_identity):
    gh.load_terragenesis()
    from terrain_pipeline.world_process_detail import load_native_terrain
    manifest = _read(path)
    if manifest.get('generator', {}).get('kind') != 'terragenesis-gpu':
        raise ValueError('native world continuation requires actual model terrain')
    entry = dict(manifest_path=str(Path(path).resolve()), manifest_sha256=file_sha(path))
    load_native_terrain(entry, source_identity=plate_identity)
    return entry


def prepare_coast(preview):
    """Return a public, source-derived regional recipe; do not generate terrain.

    Pass the returned revision to continue_world(coast_preparation=...). Annual
    graph work remains pending until a finite source-bound event is measured.
    """
    gh.load_terragenesis()
    from terrain_pipeline import world_processes
    from terrain_pipeline.common_infra import array_sha256
    from terrain_pipeline.world_coast_reuse import preparation_revision
    preview=Path(preview)
    manifest=_read(preview/'manifest.json')
    if identity_of(manifest)!=manifest['identity']:
        raise ValueError('coarse world manifest identity mismatch')
    spec=manifest['world_processes']
    process_file=preview/spec['file']
    if file_sha(process_file)!=spec['sha256']:
        raise ValueError('coarse process manifest SHA mismatch')
    process=world_processes.query(process_file.parent)
    source=dict(process['metadata'],**process['arrays'])
    source['parent_terrain_revision']=array_sha256(source['elevation_m'])
    plate_path=manifest.get('island_mountains',{}).get('record',{}).get('source') or manifest['skeleton']['path']
    return preparation_revision(source,process['metadata'].get('native_environment',{}).get('candidates',[]),
        plate_path,process['metadata']['config'].get('native_environment',{}))


def continue_world(preview, out, *, use_gpu=False, memory_wait_s=300., memory_poll_s=5., terrain_roots=(), coast_preparation=None):
    """Continue a published preview, keeping CPU requests free of model work.

    GPU preparation adapts without lowering memory gates: cached tiles are used
    first, one model worker is reused across missing tiles (window-stage budget
    after start), and the declared host budget may be polled until `memory_wait_s`.
    """
    gh.load_terragenesis()
    from terrain_pipeline import world_processes
    preview, out = Path(preview), Path(out)
    manifest = _read(preview/'manifest.json')
    if identity_of(manifest) != manifest['identity']:
        raise ValueError('coarse world manifest identity mismatch')
    marker = out/'preparation.json'
    binding = dict(schema='dream-process-revision-preparation-v1', preview_identity=manifest['identity'],
                   preview_path=str(preview.resolve()), use_gpu=bool(use_gpu),
                   memory_wait_s=float(memory_wait_s), memory_poll_s=float(memory_poll_s),
                   terrain_roots=[str(Path(root).resolve()) for root in terrain_roots])
    if coast_preparation is not None:
        binding['coast_preparation']=coast_preparation
    if out.exists():
        if not marker.exists() or _preparation_identity(_read(marker)) != _preparation_identity(binding):
            raise FileExistsError('existing detailed directory is not this resumable preparation')
        if (out/'continuation.json').exists():
            published = _read(out/'manifest.json')
            if identity_of(published) != published['identity']:
                raise ValueError('completed detailed map identity mismatch')
            saved_process = world_processes.query(out/'world-processes')
            delivery = _read(out/'continuation.json')
            if (delivery['preview_identity'] != manifest['identity'] or
                    delivery['process_identity'] != saved_process['identity'] or
                    published.get('parent_preview_identity') != manifest['identity']):
                raise ValueError('completed continuation belongs to another preview/process')
            from app.map_source import load_source
            load_source('world-map-product', out, expected_identity=published['identity'])
            return delivery
    spec = manifest['world_processes']
    process_file = preview/spec['file']
    if file_sha(process_file) != spec['sha256']:
        raise ValueError('coarse process manifest SHA mismatch')
    process = world_processes.query(process_file.parent)
    record = manifest.get('island_mountains', {}).get('record', {})
    source = record.get('source') or manifest['skeleton']['path']
    run = record.get('skeleton_run')
    plate_identity = manifest['skeleton']['identity']
    island_path = record.get('island_product_path')
    island_identity = record.get('island_identity')
    existing = {}
    for product in record.get('mountains', {}).get('products', []):
        path = Path(product['raw_manifest'])
        existing[product['tile']] = path
    entries, terrain_states = [], []
    if process['metadata']['config'].get('integrated_environment'):
        native_candidates=process['metadata'].get('native_environment',{}).get('candidates',[])
        unique_tiles=sorted({tuple(int(np.floor(value/15360.)) for value in row['location_xz_m'])
                             for row in native_candidates})
        backend=(coast_preparation or {}).get('backend',process['metadata']['config'].get('native_environment',{}).get('coast_backend'))
        if backend=='regional-existing-delta-v1':
            from terrain_pipeline.world_coast_reuse import dependency_request
            from terrain_pipeline.common_infra import array_sha256
            source_binding=dict(source_identity=process['metadata']['source_identity'],
                plate_identity=process['metadata']['plate_identity'],world_seed=process['metadata']['world_seed'],
                parent_terrain_revision=array_sha256(process['arrays']['elevation_m']))
            regional_config=dict(process['metadata']['config'].get('native_environment',{}))
            if coast_preparation is not None:
                regional_config['coast_regions']=coast_preparation.get('regions',{})
            requests=[dependency_request(source_binding,row,regional_config)
                      for row in native_candidates if row['kind']=='coast']
            unique_tiles=sorted(set(unique_tiles)|{tuple(tile) for request in requests for tile in request['required_tiles']})
    else:
        unique_tiles = sorted({tuple(row['native_td_tile_xz']) for row in process['details']})
    if len(unique_tiles) > 4 and not (process['metadata']['config'].get('integrated_environment') and backend=='regional-existing-delta-v1'):
        raise ValueError('first continuation exceeds four native TD tiles')
    raw_root = preview.parent/(preview.name+'-process-raw-td')
    # Prefer already frozen tiles so a short host budget never blocks reuse.
    ordered = []
    for ix, iz in unique_tiles:
        tile = tiles.tile_window(ix, iz)
        cached = existing.get(tile['id'], local30.tile_manifest_path(raw_root, tile['id']))
        if not Path(cached).exists():
            for root in terrain_roots:
                candidate = local30.tile_manifest_path(root, tile['id'])
                if candidate.exists():
                    _verified_entry(candidate, plate_identity=plate_identity)
                    cached = candidate
                    break
        ordered.append((0 if Path(cached).exists() else 1, ix, iz, tile, Path(cached)))
    ordered.sort()
    producer = None
    model_started = False
    resource_waits = []

    def shared_generator(origin, side):
        nonlocal producer, model_started
        if producer is None:
            gate = local30.await_memory_gate(starting_worker=True, wait_s=memory_wait_s, poll_s=memory_poll_s)
            resource_waits.append(dict(stage='worker-start', **{k: gate[k] for k in
                ('available_bytes', 'required_bytes', 'waited_s', 'polls') if k in gate}))
            gate['gpu'] = local30.gpu_gate()
            producer = local30._default_generator(source, None, island_product_path=island_path,
                expected_island_identity=island_identity, skeleton_run_path=run)
            model_started = True
        return producer(origin, side)

    shared_generator.__name__ = '_gpu_generate'
    for _, ix, iz, tile, cached in ordered:
        if not cached.exists() and use_gpu:
            try:
                local30.prepare_tile(raw_root, ix, iz, purpose='world-process-detail',
                    reason='Explicit world process continuation after published coarse preview',
                    plate_path=source, island_product_path=island_path,
                    expected_island_identity=island_identity, skeleton_run_path=run,
                    generator=shared_generator, memory_wait_s=memory_wait_s, memory_poll_s=memory_poll_s)
                cached = local30.tile_manifest_path(raw_root, tile['id'])
            except (MemoryError, RuntimeError) as exc:
                terrain_states.append(dict(tile=tile['id'], status='pending-resource', reason=str(exc)))
                continue
        if cached.exists():
            entries.append(_verified_entry(cached, plate_identity=plate_identity))
            terrain_states.append(dict(tile=tile['id'], status='prepared', manifest_path=str(cached.resolve())))
        else:
            terrain_states.append(dict(tile=tile['id'], status='pending-terrain',
                                       reason='CPU task; explicit GPU preparation not permitted by original request'))
    out.mkdir(parents=True, exist_ok=True)
    write_json(marker, binding)
    process_out = out/'world-processes'
    if (process_out/'manifest.json').exists():
        world_processes.query(process_out)
        result = _read(process_out/'manifest.json')
        if result['parent_product_identity'] != process['identity']:
            raise ValueError('resumed detailed product belongs to a different preview')
    else:
        if process_out.exists():
            # Preserve interrupted solver output for diagnosis before repeating
            # its fixed workload. No published product is replaced or deleted.
            attempt = 1
            while (out/('interrupted-processes-%d' % attempt)).exists():
                attempt += 1
            process_out.rename(out/('interrupted-processes-%d' % attempt))
        kwargs={} if coast_preparation is None else dict(coast_preparation=coast_preparation)
        result = world_processes.continue_details(process_file.parent, process_out, terrain_entries=entries,
                                                   plate_identity=plate_identity,**kwargs)
    _publish_map_revision(preview, out, result)
    delivery = dict(schema='dream-world-process-continuation-v1', preview_identity=manifest['identity'],
                    process_identity=result['identity'], use_gpu=use_gpu, terrain=terrain_states,
                    detailed_regions=result.get('detailed_regions', []), pending_regions=result.get('pending_regions', []),
                    status=result['metadata']['stages']['detailed'],
                    adaptive_resources=dict(model_started=model_started, memory_wait_s=float(memory_wait_s),
                                            memory_poll_s=float(memory_poll_s), waits=resource_waits,
                                            policy='reuse-one-worker; prefer-cache; wait-for-declared-budget; never-lower-gates'))
    write_json(out/'continuation.json', delivery)
    return delivery


def _publish_map_revision(preview, out, process_manifest):
    """Publish revised arrays and vectors; preserve preview and raw TD."""
    gh.load_terragenesis()
    from terrain_pipeline import world_processes
    old = _read(preview/'manifest.json')
    result = world_processes.query(out/'world-processes')
    if (out/'manifest.json').exists():
        existing = _read(out/'manifest.json')
        if (existing.get('parent_preview_identity') != old['identity'] or
                existing.get('world_processes', {}).get('sha256') != file_sha(out/'world-processes/manifest.json')):
            raise ValueError('published map revision belongs to another preview/process')
        from app.map_source import load_source
        load_source('world-map-product', out, expected_identity=existing['identity'])
        return
    arrays = result['arrays']
    manifest = json.loads(json.dumps(old))
    bed = np.asarray(arrays['elevation_m'])
    ocean = np.asarray(arrays['ocean_mask'], bool)
    status = np.where(ocean, 3, np.where(bed < 0, 4, 5)).astype(np.uint8)
    wet_lakes = (np.asarray(arrays['lake_id']) > 0) & ~ocean & np.isfinite(arrays['water_surface_m'])
    published_arrays = dict(arrays, hydro_bed_m=bed, status=status,
                            water_surface_m=np.where(wet_lakes, arrays['water_surface_m'], np.nan),
                            lake_id=np.where(wet_lakes, arrays['lake_id'], 0).astype(np.int32))
    from app.world_gen.world_process_adapter import ENVIRONMENT_LAYERS
    for name,unit in ENVIRONMENT_LAYERS.items():
        if name in arrays and np.asarray(arrays[name]).shape==bed.shape:
            manifest['layers'][name]=dict(file=name+'.npy',dtype=str(np.asarray(arrays[name]).dtype),
                unit=unit,meaning='Current published integrated environment: '+name,nodata=None,
                source='world-processes/manifest.json',process_identity=result['identity'])
    for name, spec in manifest['layers'].items():
        destination = out/spec['file']
        destination.parent.mkdir(parents=True, exist_ok=True)
        if name in published_arrays:
            np.save(destination, np.asarray(published_arrays[name], dtype=spec['dtype']), allow_pickle=False)
        else:
            shutil.copyfile(preview/spec['file'], destination)
        spec['sha256'] = file_sha(destination)
        if name == 'discharge_m3_s':
            spec['scenario'] = 'Published output-year mean discharge, with detailed event budgets recorded separately'
        if name in ('temperature_c', 'precipitation_mm_yr'):
            spec.update(source='world-processes/manifest.json', approximation='generated seasonal world climate')
    for spec in manifest['vectors'].values():
        target = out/spec['file']
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(preview/spec['file'], target)
    if (preview/'ocean-island-binding.json').exists():
        shutil.copyfile(preview/'ocean-island-binding.json', out/'ocean-island-binding.json')
    grid = manifest['grid']
    receiver = np.asarray(arrays['receiver']).ravel()
    area = np.asarray(arrays['drainage_area_m2']).ravel()
    lake_id = published_arrays['lake_id']
    first, spacing = grid['first_sample_xz_m'], grid['spacing_m']
    # Draw the receivers supplied by the process revision; never reroute on a
    # different DEM merely for presentation.
    params = old['parameters']
    threshold = gh.zoned_threshold(bed, spacing, params['river_lo_km2']*1e6,
                                   params['river_hi_km2']*1e6, params['slope_split'])
    active = gh.active_rivers(receiver, arrays['order'], area, ocean, threshold)
    mesh = gh.build_graph(bed.shape, first, spacing, int(old['subseeds']['fast-relief/mesh']))
    lines = gh.trace_lines(receiver, area, active, bed.shape, first, spacing)
    rivers, _ = gh.cut_lines_at_lakes(lines, mesh.node_x_m, mesh.node_z_m, area, bed.shape, ocean, lake_id)
    lakes = gh.lake_vectors_labeled(lake_id, arrays['water_surface_m'], first, spacing)
    for kind, values in (('rivers', dict(schema='rivers-v1', lines=rivers)), ('lakes', dict(schema='lakes-v1', lakes=lakes))):
        spec = manifest['vectors'][kind]
        write_json(out/spec['file'], values)
        spec['sha256'] = file_sha(out/spec['file'])
    manifest['parent_preview_identity'] = old['identity']
    manifest['lineage'].append(old['identity'])
    manifest['world_processes'] = dict(file='world-processes/manifest.json', sha256=file_sha(out/'world-processes/manifest.json'),
                                      metadata=result['metadata'])
    from app.world_gen.world_process_adapter import environment_status
    manifest['world_processes']['environment_status'] = environment_status(result['metadata'])
    manifest['algorithm_version'] += '+detail-revision-v1'
    provenance = manifest.setdefault('reused_code', {})
    provenance.setdefault('local_sha256', {})['world_process_details.py'] = file_sha(Path(__file__))
    native_sources = ('world_processes.py', 'world_process_detail.py', 'world_process_hydrology.py',
        'world_process_estuary.py', 'world_process_reporting.py', 'world_process_backwater.py',
        'channel_geometry.py', 'surface_hydraulics.py', 'environment_delta_fv.py',
        'new_world_sediment.py', 'surface_rivers/metric_sediment.py',
        'surface_rivers/metric_fv_bedload_v4.py', 'surface_rivers/metric_fv_coastal_sediment.py',
        'surface_rivers/metric_fv_suspended_supply.py')
    tg_pipeline = gh.terragenesis_root()/'terrain_pipeline'
    provenance.setdefault('terragenesis_sha256', {}).update({
        'terrain_pipeline/' + name: file_sha(tg_pipeline/name)
        for name in native_sources if (tg_pipeline/name).exists()})
    manifest['statistics'].update(final_ocean_fraction=float(ocean.mean()), land_fraction=float((bed>=0).mean()),
                                  connected_ocean_fraction=float(ocean.mean()),
                                  closed_below_sea_fraction=float(((bed<0)&~ocean).mean()),
                                  river_segments=len(rivers), kept_lakes=len(lakes), river_nodes=int(active.sum()),
                                  max_drainage_area_m2=float(area.max()), elevation_min_m=float(bed.min()),
                                  elevation_max_m=float(bed.max()),
                                  published_height_quantization_max_m=float(np.max(np.abs(bed.astype(np.float32).astype(float)-bed))),
                                  detailed_region_count=len(process_manifest.get('detailed_regions', [])),
                                  pending_region_count=len(process_manifest.get('pending_regions', [])))
    manifest['files'] = {p.name: file_sha(p) for p in sorted(out.glob('*.npy'))}
    manifest['identity'] = identity_of(manifest)
    write_json(out/'manifest.json', manifest)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--use-gpu', action='store_true')
    parser.add_argument('--memory-wait-s', type=float, default=300.,
                        help='poll for the declared host memory budget before starting/using the TD worker; 0 disables waiting')
    parser.add_argument('--memory-poll-s', type=float, default=5., help='seconds between memory polls while waiting')
    parser.add_argument('--terrain-root', action='append', default=[], help='explicit same-source native TD cache root to reuse')
    args = parser.parse_args(argv)
    print(json.dumps(continue_world(args.preview, args.out, use_gpu=args.use_gpu,
                                    memory_wait_s=args.memory_wait_s, memory_poll_s=args.memory_poll_s,
                                    terrain_roots=args.terrain_root),
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
