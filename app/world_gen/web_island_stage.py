"""Explicit world island preparation, TD scheduling, and frozen input consumption.

No function called by map queries generates terrain. World products sample saved
30m derived-minus-analytic-base corrections before final erosion and hydrology.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from app.world_gen import ocean_island_adapter as islands, island_mountains as mountains, local30
from app.world_gen.config import sha256_json

SCHEMA = 'dream-world-island-input-v2'
POLICY = 'frozen-derived-delta-before-final-hydrology-v2'


def read_record(path):
    record = json.loads(Path(path).read_text(encoding='utf-8'))
    if record.get('schema') != SCHEMA or record.get('identity') != sha256_json({k:v for k,v in record.items() if k!='identity'}):
        raise ValueError('world island input identity/schema mismatch')
    return record


def write_record(path, record):
    path = Path(path)
    if path.exists():
        raise FileExistsError('refusing to overwrite frozen world island input: '+str(path))
    record = dict(record)
    record['identity'] = sha256_json(record)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2, allow_nan=False)
    return record


def prepare(source, run, out, *, world_type, world_seed):
    """Prepare a new sidecar and bounded fixed-1km qualification plans."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    _, core, _ = islands._public_api()
    api = mountains._api()
    plate = core.PlateOceanSource.from_npz(source)
    product = core.prepare_ocean_islands(plate, core.OceanIslandConfig(world_type=world_type,world_seed=world_seed))
    product_path = out/'islands.npz'
    core.save_product(product, product_path)
    binding = islands.load_binding(source,product_path,product.identity,run)
    config = api.IslandMountainConfig()
    bounds = plate.bounds_m
    cells = math.ceil((bounds[2]-bounds[0])/1000)*math.ceil((bounds[3]-bounds[1])/1000)
    plans = []
    pending = []
    catalog = []
    if cells <= config.max_analysis_cells:
        windows = [None]
    elif hasattr(api, 'mountain_analysis_windows'):
        catalog = api.mountain_analysis_windows(product, config, tile_margin_m=15360.)
        windows = [entry['bounds_m'] for entry in catalog if entry['status']=='ready']
        pending = [entry for entry in catalog if entry['status']!='ready']
    else:
        windows = []
        pending = [dict(reason='fixed 1km full domain exceeds bounded analysis budget; explicit bounded preparation required',
                        bounds_m=list(bounds),analysis_cells=cells,max_analysis_cells=config.max_analysis_cells)]
    for i, window in enumerate(windows):
        from dataclasses import replace
        cfg = config if window is None else replace(config,analysis_bounds_m=tuple(window))
        plan = api.analyze_island_mountains(product,cfg)
        path = out/('plan-%04d.npz'%i)
        api.save_mountain_plan(plan,path)
        plans.append(dict(path=str(path.resolve()),identity=plan.identity,sha256=islands.file_sha(path),
                          empty=plan.empty,grid=plan.manifest['grid'],blend_policy=plan.manifest['blend_policy']))
    record = dict(schema=SCHEMA,policy=POLICY,source=str(Path(source).resolve()),skeleton_run=str(Path(run).resolve()),
                  island_product_path=str(product_path.resolve()),island_identity=product.identity,binding=binding.record,
                  analysis=dict(status='pending-analysis' if pending else 'complete',spacing_m=1000.,
                                qualification=f'actual exposed connected area strictly >{config.min_area_km2:g} km2; no width gate',pending=pending,windows=catalog),
                  plans=plans,mountains=dict(status='not-scheduled',products=[]),
                  imported_sha256=islands.file_sha(Path(api.__file__)))
    return write_record(out/'prepared.json',record)


def schedule(prepared, out, *, use_gpu, generator_factory=None, available_bytes=None, tile_indices=None):
    """Explicit author task only; CPU requests never enter GPU/model preparation."""
    record = read_record(prepared)
    if record['imported_sha256'] != islands.file_sha(Path(mountains._api().__file__)):
        raise ValueError('mountain algorithm changed after qualification')
    products = []
    tasks = []
    for entry in record['plans']:
        if islands.file_sha(entry['path']) != entry['sha256']:
            raise ValueError('world mountain plan SHA changed')
        opts = dict(source=record['source'],product_path=record['island_product_path'],
                    island_identity=record['island_identity'],plan_path=entry['path'],plan_identity=entry['identity'],
                    skeleton_run=record['skeleton_run'],out_root=Path(out)/'tiles',
                    reason='Explicit world generation island mountains',available_bytes=available_bytes,tile_indices=tile_indices)
        if use_gpu:
            task = mountains.prepare_mountains(**opts,generator_factory=generator_factory)
        else:
            task = mountains.prepare_mountains(**opts,dry_run=True)
        tasks.append(task)
        for row in task['products']:
            row = dict(row,plan_identity=entry['identity'],
                       raw_manifest_sha256=islands.file_sha(row['raw_manifest']),
                       derived_manifest_sha256=islands.file_sha(row['derived_manifest']))
            products.append(row)
    incomplete = any(t['skipped'] or t.get('height_status')=='pending-or-rejected' for t in tasks) or tile_indices is not None
    required = any(t['tiles_to_prepare'] for t in tasks)
    status = ('pending-analysis' if record['analysis']['pending'] else
              'partial' if incomplete else 'prepared' if use_gpu and required else 'pending-gpu' if required else 'empty')
    record.pop('identity')
    record['mountains'] = dict(status=status,use_gpu=use_gpu,model_started=any(t['model_started'] for t in tasks),
                              tasks=tasks,products=products)
    return write_record(Path(out)/'world-input.json',record)


def bind_existing(*, source, run, product_path, island_identity, plan_path, plan_identity, task_report, out):
    """Publish an explicit existing task as world input; missing tiles stay partial."""
    binding,plan=mountains.load_plan(source,product_path,island_identity,plan_path,plan_identity,run)
    task=json.loads(Path(task_report).read_text(encoding='utf-8'))
    if task['plan_identity']!=plan.identity or task['island_identity']!=island_identity:
        raise ValueError('existing mountain task belongs to a different plan/island')
    expected,skipped=mountains.scheduled_tiles(plan)
    expected_ids={t['id'] for t in expected}
    products=[]
    for row in task['products']:
        if row['tile'] not in expected_ids:
            raise ValueError('existing mountain task contains an ineligible tile')
        products.append(dict(row,plan_identity=plan.identity,
            raw_manifest_sha256=islands.file_sha(row['raw_manifest']),
            derived_manifest_sha256=islands.file_sha(row['derived_manifest'])))
    actual={r['tile'] for r in products}
    if len(actual)!=len(products):raise ValueError('duplicate existing task tile')
    missing=sorted(expected_ids-actual)
    record=dict(schema=SCHEMA,policy=POLICY,source=str(Path(source).resolve()),skeleton_run=str(Path(run).resolve()),
        island_product_path=str(Path(product_path).resolve()),island_identity=island_identity,binding=binding.record,
        analysis=dict(status='complete',spacing_m=plan.manifest['grid']['spacing_m'],pending=[]),
        plans=[dict(path=str(Path(plan_path).resolve()),identity=plan.identity,sha256=islands.file_sha(plan_path),
                    empty=plan.empty,grid=plan.manifest['grid'],blend_policy=plan.manifest['blend_policy'])],
        mountains=dict(status='partial' if missing or skipped else 'prepared' if products else 'empty',
                       model_started=task['model_started'],use_gpu=True,products=products,tasks=[task],
                       missing_tiles=missing,skipped=skipped,imported_task_sha256=islands.file_sha(task_report)),
        imported_sha256=islands.file_sha(Path(mountains._api().__file__)))
    return write_record(out,record)


def apply_to_fields(path, binding, fields, first_xz_m, spacing_m):
    """Read-only sampling of verified native derived products into final targets."""
    record = read_record(path)
    if record['policy'] != POLICY or record['binding'] != binding.record:
        raise ValueError('world mountain source/island/run binding differs')
    api = mountains._api()
    if islands.file_sha(Path(api.__file__)) != record['imported_sha256']:
        raise ValueError('world mountain algorithm changed; prepare a new world input')
    plans = {}
    for entry in record['plans']:
        if islands.file_sha(entry['path']) != entry['sha256']:
            raise ValueError('world mountain plan SHA changed')
        plan = api.load_mountain_plan(entry['path'],entry['identity'],binding.product)
        if plan.manifest['blend_policy'] != entry['blend_policy']:
            raise ValueError('world mountain blend policy changed')
        plans[entry['identity']] = entry
        del plan
    nz,nx = fields['elevation_m'].shape
    x = first_xz_m[0]+np.arange(nx)*spacing_m
    z = first_xz_m[1]+np.arange(nz)*spacing_m
    delta = np.zeros((nz,nx),np.float32)
    assigned = np.zeros((nz,nx),bool)
    from scipy.ndimage import map_coordinates
    current_plan_id = None
    plan = None
    for row in record['mountains']['products']:
        dm,rm = Path(row['derived_manifest']),Path(row['raw_manifest'])
        if islands.file_sha(dm)!=row['derived_manifest_sha256'] or islands.file_sha(rm)!=row['raw_manifest_sha256']:
            raise ValueError('world mountain raw/derived manifest SHA changed')
        derived=json.loads(dm.read_text(encoding='utf-8'));raw=json.loads(rm.read_text(encoding='utf-8'))
        if (local30._identity(derived)!=row['derived_identity'] or local30._identity(raw)!=row['raw_identity']
                or derived['identity']!=row['derived_identity'] or raw['identity']!=row['raw_identity']):
            raise ValueError('world mountain raw/derived identity mismatch')
        if current_plan_id != row['plan_identity']:
            entry=plans[row['plan_identity']]
            plan=api.load_mountain_plan(entry['path'],entry['identity'],binding.product)
            current_plan_id=plan.identity
        state=local30.tile_state(dm.parents[2],row['tile'],plate_identity=binding.product.source.identity,
            island_identity=binding.product.identity,island_condition_policy=binding.record['condition_policy'],
            mountain_plan_identity=plan.identity,mountain_blend_policy=plan.manifest['blend_policy'])
        if state['status']!='prepared':
            raise ValueError('world mountain derived cache is stale: '+str(state['reasons']))
        mb=derived['mountain_binding']
        if plan.manifest.get('peak_normalization_required'):
            nb=mb.get('peak_normalization',{})
            if not nb.get('path') or islands.file_sha(nb['path'])!=nb.get('sha256'):
                raise ValueError('world peak normalization SHA mismatch')
            normalization=json.loads(Path(nb['path']).read_text(encoding='utf-8'))
            api.validate_peak_normalization(plan,binding.product,normalization)
            if normalization['identity']!=nb.get('identity'):
                raise ValueError('world peak normalization identity differs')
        if (mb['plan_identity']!=plan.identity or mb['blend_policy']!=plan.manifest['blend_policy']
                or mb['raw_identity']!=raw['identity'] or mb['island_identity']!=binding.product.identity):
            raise ValueError('world mountain derived binding mismatch')
        for mp,m in ((dm,derived),(rm,raw)):
            spec=m['layers']['elevation_m']
            target=(mp.parent/spec['file']).resolve()
            if not target.is_relative_to(mp.parent.resolve()):
                raise ValueError('world mountain elevation escapes product')
            if islands.file_sha(target)!=spec['sha256']:
                raise ValueError('world mountain elevation SHA mismatch')
        if mb['raw_elevation_sha256']!=raw['layers']['elevation_m']['sha256']:
            raise ValueError('world mountain raw elevation binding differs')
        grid=derived['grid'];fx,fz=grid['first_sample_xz_m'];step=grid['spacing_m'];sz,sx=grid['shape_zx']
        ix=np.flatnonzero((x>=fx)&(x<=fx+(sx-1)*step))
        iz=np.flatnonzero((z>=fz)&(z<=fz+(sz-1)*step))
        if not len(ix) or not len(iz):continue
        xx,zz=np.meshgrid(x[ix],z[iz])
        native=np.load(dm.parent/derived['layers']['elevation_m']['file'],mmap_mode='r',allow_pickle=False)
        height=map_coordinates(native,[(zz-fz)/step,(xx-fx)/step],order=1,mode='nearest')
        base=binding.product.query(xx,zz)['elevation_m']
        weights=api.sample_mountain_weights(plan,binding.product,xx,zz)
        if plan.manifest.get('peak_normalization_required'):
            ready=[r['component_id'] for r in normalization['components'] if r['status']=='ready']
            components=api.sample_mountain_components(plan,binding.product,xx,zz)
            weights=np.where(np.isin(components,ready),weights,0.)
        window=np.ix_(iz,ix)
        use=(weights>0)&~assigned[window]
        patch=delta[window];patch[use]=(height-base)[use];delta[window]=patch
        mask=assigned[window];mask[use]=True;assigned[window]=mask
    fields=dict(fields)
    fields['elevation_m']=(fields['elevation_m']+delta).astype(np.float32)
    return fields,dict(record=record,input_file_sha256=islands.file_sha(path),
                       sampled_cells=int(assigned.sum()),nonzero_delta_cells=int(np.count_nonzero(delta)),
                       meaning='30m frozen derived-minus-analytic-base correction sampled at final world cell centres before erosion/hydrology')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','schedule','fast','bind-existing'))
    parser.add_argument('--skeleton');parser.add_argument('--run');parser.add_argument('--out',required=True)
    parser.add_argument('--world-type',default='multi-continent');parser.add_argument('--seed',type=int,default=20260903)
    parser.add_argument('--island-product');parser.add_argument('--island-identity')
    parser.add_argument('--plan');parser.add_argument('--plan-identity');parser.add_argument('--task-report')
    parser.add_argument('--input');parser.add_argument('--use-gpu',action='store_true')
    parser.add_argument('--world-processes', action='store_true')
    parser.add_argument('--resume-processes', action='store_true')
    args=parser.parse_args(argv)
    if args.action=='prepare':prepare(args.skeleton,args.run,args.out,world_type=args.world_type,world_seed=args.seed)
    elif args.action=='schedule':schedule(args.input,args.out,use_gpu=args.use_gpu)
    elif args.action=='bind-existing':
        bind_existing(source=args.skeleton,run=args.run,product_path=args.island_product,island_identity=args.island_identity,
            plan_path=args.plan,plan_identity=args.plan_identity,task_report=args.task_report,out=args.out)
    else:
        from app.world_gen import fast_relief
        if Path(args.out).exists() and not (args.resume_processes and args.world_processes
                and not (Path(args.out)/'manifest.json').exists()
                and (Path(args.out)/'world-processes'/'checkpoint.json').exists()):
            raise FileExistsError('final world output must be a new directory')
        record=read_record(args.input)
        fast_relief.freeze(record['source'],args.out,relief='orogen',
            island_product_path=record['island_product_path'],expected_island_identity=record['island_identity'],
            skeleton_run_path=record['skeleton_run'],mountain_input_path=args.input,
            process_config={} if args.world_processes else None)
    return 0

if __name__=='__main__':raise SystemExit(main())
