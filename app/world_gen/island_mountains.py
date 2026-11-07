"""Explicit TD scheduling and derived publication; qualification lives in TG."""
import json
import hashlib
from pathlib import Path

import numpy as np

from . import local30, ocean_island_adapter as islands, tiles as T


def _api():
    islands._public_api()
    from terrain_pipeline import island_mountains
    return island_mountains


def load_plan(source,product_path,island_identity,plan_path,plan_identity,skeleton_run=None):
    binding=islands.load_binding(source,product_path,island_identity,skeleton_run)
    before=islands.file_sha(plan_path)
    plan=_api().load_mountain_plan(plan_path,plan_identity,binding.product)
    if before!=islands.file_sha(plan_path):
        raise ValueError('mountain plan changed while loading')
    return binding,plan


def scheduled_tiles(plan):
    """Only tiles intersecting selected interior, bounded by the finite source."""
    grid=plan.manifest['grid'];spacing=grid['spacing_m'];bounds=grid['bounds_m']
    zz,xx=np.nonzero(plan.selected_interior)
    todo=set()
    span=T.TILE_NATIVE*T.NATIVE_M
    if plan.manifest.get('peak_normalization_required'):
        api=_api()
        for component in plan.manifest['selected_components']:
            todo.update(api.component_native_tiles(plan,component))
    for z,x in zip(zz,xx):
        x0,z0=bounds[0]+x*spacing,bounds[1]+z*spacing
        x1,z1=min(x0+spacing,bounds[2]),min(z0+spacing,bounds[3])
        for iz in range(int(np.floor(z0/span)),int(np.ceil(z1/span))):
            for ix in range(int(np.floor(x0/span)),int(np.ceil(x1/span))):
                todo.add((ix,iz))
    tiles=[];skipped=[]
    for ix,iz in sorted(todo,key=lambda t:(t[1],t[0])):
        tile=T.tile_window(ix,iz);box=tile['extent_m']
        source_bounds=grid.get('source_bounds_m',bounds)
        if box[0]<source_bounds[0] or box[1]<source_bounds[1] or box[2]>=source_bounds[2] or box[3]>=source_bounds[3]:
            skipped.append(dict(tile=tile['id'],reason='tile extends outside finite source; no invented external base'))
        else:
            tiles.append(tile)
    return tiles,skipped


def prepare_mountains(*,source,product_path,island_identity,plan_path,plan_identity,out_root,reason,
                      skeleton_run=None,dry_run=False,tile_indices=None,generator_factory=None,
                      available_bytes=None,raw_root_override=None,memory_wait_s=300.,memory_poll_s=5.):
    """One explicit task, at most one model factory. Empty plan never starts it.

    A factory override is for declared CPU tests only. Default dispatch uses the
    same local30._default_generator and model instance as ordinary local30 work.
    Host memory gates are never lowered; `memory_wait_s` only polls for the declared budget.
    """
    if not reason.strip():
        raise ValueError('explicit mountain preparation reason is required')
    binding,plan=load_plan(source,product_path,island_identity,plan_path,plan_identity,skeleton_run)
    plan_sha=islands.file_sha(plan_path)
    tiles,skipped=scheduled_tiles(plan)
    if tile_indices is not None:
        wanted=set(map(tuple,tile_indices))
        known={(t['ix'],t['iz']) for t in tiles}
        if not wanted<=known:
            raise ValueError('requested tile is not eligible in the finite mountain plan')
        tiles=[t for t in tiles if (t['ix'],t['iz']) in wanted]
    report=dict(schema='dream-island-mountain-task-v1',plan_identity=plan.identity,island_identity=island_identity,
        empty=plan.empty,dry_run=dry_run,tiles_to_prepare=[t['id'] for t in tiles],skipped=skipped,
        model_started=False,generator_factory_calls=0,products=[])
    # Before sysmem, GPU checks, imports of torch/WorldPipeline, or worker start.
    if plan.empty or dry_run or not tiles:
        return report
    api=_api()
    root=Path(out_root)
    raw_root=Path(raw_root_override) if raw_root_override is not None else root/'raw'/island_identity
    derived_root=root/'derived'/plan.identity
    peak_required=bool(plan.manifest.get('peak_normalization_required'))
    producer=None
    def shared_generator(origin,side):
        nonlocal producer
        if producer is None:
            if generator_factory is None:
                local30.await_memory_gate(starting_worker=True, wait_s=float(memory_wait_s),
                    poll_s=float(memory_poll_s), available_bytes=available_bytes)
                local30.gpu_gate()
                producer=local30._default_generator(source,islands._public_api()[0],island_product_path=product_path,
                    expected_island_identity=island_identity,skeleton_run_path=skeleton_run)
                report['model_started']=True
            else:
                producer=generator_factory()
            report['generator_factory_calls']+=1
        return producer(origin,side)
    if generator_factory is None:
        shared_generator.__name__='_gpu_generate'
    raw_inputs=[]
    for tile in tiles:
        if islands.file_sha(plan_path)!=plan_sha:
            raise ValueError('mountain plan file changed during task')
        ix,iz=tile['ix'],tile['iz']
        raw=local30.prepare_tile(raw_root,ix,iz,purpose='island-mountains-raw',reason=reason,plate_path=source,
            generator=shared_generator,available_bytes=available_bytes,island_product_path=product_path,
            expected_island_identity=island_identity,skeleton_run_path=skeleton_run,
            memory_wait_s=memory_wait_s,memory_poll_s=memory_poll_s)
        if generator_factory is None and raw['generator']['kind']!='terragenesis-gpu':
            raise local30.StaleTile(tile['id'],['raw cache is injected, not the requested TD model generator'])
        raw_dir=local30.tile_manifest_path(raw_root,tile['id']).parent
        raw_file=raw_dir/raw['layers']['elevation_m']['file']
        raw_sha=islands.file_sha(raw_file)
        if raw_sha!=raw['layers']['elevation_m']['sha256']:
            raise ValueError('raw TD elevation SHA mismatch')
        raw_inputs.append(dict(tile=tile,manifest=raw,path=raw_file,sha256=raw_sha,manifest_path=raw_dir/'manifest.json'))
    normalization=None
    normalization_path=None
    if peak_required:
        records=[dict(ix=r['tile']['ix'],iz=r['tile']['iz'],identity=r['manifest']['identity'],
                      elevation_sha256=r['sha256'],array_sha256=hashlib.sha256(
                          np.load(r['path'],allow_pickle=False).tobytes()).hexdigest()) for r in raw_inputs]
        builder=api.PeakNormalizationBuilder(plan,binding.product,records)
        for r in raw_inputs:
            builder.observe_raw(r['tile']['ix'],r['tile']['iz'],np.load(r['path'],mmap_mode='r',allow_pickle=False))
        for r in raw_inputs:
            builder.observe_scale(r['tile']['ix'],r['tile']['iz'],np.load(r['path'],mmap_mode='r',allow_pickle=False))
        normalization=builder.finalize()
        directory=root/'normalization'/plan.identity
        directory.mkdir(parents=True,exist_ok=True)
        normalization_path=directory/(normalization['identity']+'.json')
        text=json.dumps(normalization,sort_keys=True,indent=2,allow_nan=False)+'\n'
        if normalization_path.exists():
            if normalization_path.read_text(encoding='utf-8')!=text:
                raise ValueError('frozen peak normalization differs')
        else:
            with normalization_path.open('x',encoding='utf-8') as stream:stream.write(text)
        derived_root=derived_root/normalization['identity']
        report['peak_normalization']=dict(identity=normalization['identity'],path=str(normalization_path.resolve()),
            sha256=islands.file_sha(normalization_path),components=normalization['components'])
        report['height_status']='ready' if all(c['status']=='ready' for c in normalization['components']) else 'pending-or-rejected'
    report['raw_products']=[dict(tile=r['tile']['id'],raw_identity=r['manifest']['identity'],
        raw_manifest=str(r['manifest_path'].resolve()),raw_elevation_sha256=r['sha256']) for r in raw_inputs]
    for r in raw_inputs:
        if islands.file_sha(plan_path)!=plan_sha or islands.file_sha(r['path'])!=r['sha256']:
            raise ValueError('plan/raw changed during peak normalization')
        tile=r['tile'];ix,iz=tile['ix'],tile['iz'];raw=r['manifest'];raw_file=r['path'];raw_sha=r['sha256']
        raw_dir=r['manifest_path'].parent
        raw_height=np.load(raw_file,mmap_mode='r',allow_pickle=False)
        state=local30.tile_state(derived_root,tile['id'],plate_identity=binding.product.source.identity,
            island_identity=island_identity,island_condition_policy=binding.record['condition_policy'],
            mountain_plan_identity=plan.identity,mountain_blend_policy=plan.manifest['blend_policy'])
        if state['status']=='stale':
            raise local30.StaleTile(tile['id'],state['reasons'])
        if state['status']=='prepared':
            derived=json.loads(local30.tile_manifest_path(derived_root,tile['id']).read_text(encoding='utf-8'))
            if derived['mountain_binding']['raw_identity']!=raw['identity'] or derived['mountain_binding']['raw_elevation_sha256']!=raw_sha:
                raise local30.StaleTile(tile['id'],['raw TD product changed'])
            derived_file=local30.tile_manifest_path(derived_root,tile['id']).parent/derived['layers']['elevation_m']['file']
            if islands.file_sha(derived_file)!=derived['layers']['elevation_m']['sha256']:
                raise ValueError('derived mountain elevation SHA mismatch')
        else:
            x=tile['first_sample_xz_m'][0]+np.arange(T.TILE_SAMPLES)[None,:]*T.NATIVE_M
            z=tile['first_sample_xz_m'][1]+np.arange(T.TILE_SAMPLES)[:,None]*T.NATIVE_M
            height,weight=(api.apply_peak_surface(plan,binding.product,normalization,x,z,raw_height) if peak_required
                           else api.blend_mountain_surface(plan,binding.product,x,z,raw_height))
            record=dict(plan_identity=plan.identity,blend_policy=plan.manifest['blend_policy'],island_identity=island_identity,
                plan_file_sha256=plan_sha,raw_identity=raw['identity'],raw_elevation_sha256=raw_sha,
                raw_manifest_path=str((raw_dir/'manifest.json').resolve()),
                base_policy='Same frozen island product analytic elevation at absolute 30m native coordinates',
                land_floor_m=plan.manifest['config']['land_floor_m'],nonzero_weight_samples=int((weight>0).sum()),
                imported_module_sha256=islands.file_sha(Path(api.__file__)),adapter_sha256=islands.file_sha(Path(__file__)))
            if peak_required:
                record['peak_normalization']=dict(identity=normalization['identity'],path=str(normalization_path.resolve()),
                    sha256=islands.file_sha(normalization_path))
            derived=local30.freeze_tile(derived_root,ix,iz,height,purpose='island-mountains-derived',reason=reason,
                world_layer_identity=None,world_seed=binding.product.config.world_seed,plate_identity=binding.product.source.identity,
                consistency_report=dict(status='not-checked',reason='analytic island base; independent of 960m TD pages'),
                generator_info=dict(kind='island-interior-derived',raw_kind=raw['generator']['kind']),
                island_binding=binding.record,mountain_binding=record)
        if islands.file_sha(raw_file)!=raw_sha:
            raise ValueError('raw TD changed during derivation')
        report['products'].append(dict(tile=tile['id'],raw_identity=raw['identity'],derived_identity=derived['identity'],
            raw_manifest=str((raw_dir/'manifest.json').resolve()),
            derived_manifest=str(local30.tile_manifest_path(derived_root,tile['id']).resolve())))
    return report
