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
# An explicit coarse-map request stops before any qualification. No analysis
# budget is lowered to look qualified, and the status stays pending-analysis.
DEFERRED_ANALYSIS_REASON = ('explicit coarse-map request: island mountain analysis deferred before qualification; '
                            'no island cells analysed in this preparation')
DEFERRED_ANALYSIS_QUALIFICATION = 'not qualified: island mountain analysis deferred by an explicit coarse-map request'
# The published product inventory is bounded by the frozen reader's manifest
# budget. Only this declared density selector controls the feature count; the
# reader's encoding and limit checks are never relaxed or bypassed here.
ISLAND_DENSITIES = ('none', 'low', 'medium', 'high')
DEFAULT_ISLAND_DENSITY = 'medium'


# Island candidate *layout* handed to the frozen OceanIslandConfig. 'old' is the historical
# absolute-slot v5 geometry and passes no new keyword; 'clustered' declares the
# clustered-provinces preset explicitly. Nothing here qualifies cells, relaxes a reader limit
# or reinterprets a quality/size setting.
ISLAND_LAYOUTS = ('old', 'clustered')
DEFAULT_ISLAND_LAYOUT = 'old'
OLD_LAYOUT_POLICY = 'absolute-slots-v1'
CLUSTERED_LAYOUT_POLICY = 'clustered-provinces-v1'
# Every field the clustered-provinces preset declares on top of the historical v5 defaults.
# The preset is passed as explicit keywords; it is never derived from a request's quality.
CLUSTERED_LAYOUT_CONFIG = dict(
    layout_policy=CLUSTERED_LAYOUT_POLICY,
    province_count=5,
    province_radius_m=600000.,
    province_hotspots=6,
    isolated_hotspot_count=3,
    max_age_steps=300.,
    max_chain_length_m=600000.,
    stages=8,
    boundary_spacing_m=150000.,
    ridge=False,
)


def island_config_kwargs(island_layout):
    """Explicit OceanIslandConfig keywords for a layout; the old layout adds none."""
    if island_layout not in ISLAND_LAYOUTS:
        raise ValueError('island layout must be one of ' + ', '.join(ISLAND_LAYOUTS))
    return {} if island_layout == DEFAULT_ISLAND_LAYOUT else dict(CLUSTERED_LAYOUT_CONFIG)


def island_config_record(island_layout, *, world_type, world_seed, island_density):
    """The actual config a preparation asks for, recorded for strict reuse comparison."""
    record = dict(world_type=world_type, world_seed=world_seed, density=island_density)
    record.update(island_config_kwargs(island_layout))
    return record


def _layout_record(island_layout, config_record):
    """Declared-layout keys of a prepared record.

    The old layout records nothing new: its record keeps exactly the historical shape so an
    already frozen old-layout preparation and the frozen v5 product manifest keep their
    identity. Only an explicitly clustered preparation carries the actual config.
    """
    if island_layout == DEFAULT_ISLAND_LAYOUT:
        return {}
    return dict(island_layout=island_layout, island_config=json.loads(json.dumps(config_record)))


def _config_class_kwargs(core, island_layout):
    """Refuse a clustered request while the TG core has no such config fields."""
    kwargs = island_config_kwargs(island_layout)
    fields = getattr(getattr(core, 'OceanIslandConfig', None), '__dataclass_fields__', {})
    missing = sorted(name for name in kwargs if name not in fields)
    if missing:
        raise ValueError('Terragenesis OceanIslandConfig lacks the clustered layout fields: '
                         + ', '.join(missing))
    return kwargs


def _verify_product_layout(product, island_layout, config_record):
    """The frozen product must actually carry the config that was recorded, not just the ask."""
    config = product.config
    expected = dict(config_record)
    for name, value in expected.items():
        actual = getattr(config, name, None)
        if isinstance(value, bool):
            if actual is not value:
                raise ValueError('frozen island product config differs in ' + name)
        elif actual != value:
            raise ValueError('frozen island product config differs in ' + name)
    if island_layout == DEFAULT_ISLAND_LAYOUT:
        policy = getattr(config, 'layout_policy', None)
        if policy not in (None, OLD_LAYOUT_POLICY):
            raise ValueError('frozen island product declares a different island layout: ' + str(policy))


def validate_mountain_reader(record, current_sha, binding_compatibility):
    saved_sha = record['imported_sha256']
    policy = 'identical-mountain-reader'
    if saved_sha != current_sha:
        # This frozen CPU input has no TD corrections to reinterpret. Plans
        # are still loaded with their saved SHA/identity below. Nonempty
        # mountain products require their original reader and fail closed.
        if not (binding_compatibility['policy'] == 'audited-frozen-v3-reader-stack' and
                record['binding']['island_algorithm'] == 'ocean-islands-metric-detail-smooth-seabed-v3' and
                not record['mountains']['products'] and
                saved_sha == '6ad03099ff2b2eccd59fb02183e2b56494b974f7faaf285eb858aa28ff342879' and
                current_sha == 'c1cf6326a9a093a2a5f08dde76d906b075921f410cbef911998db0ba75e4db92'):
            raise ValueError('world mountain algorithm changed; prepare a new world input')
        policy = 'audited-v3-empty-correction-reader'
    return dict(policy=policy, producer_sha256=saved_sha, consumer_sha256=current_sha)


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


def _verified_reuse(reuse_prepared, source, run, world_type, world_seed, island_density, island_layout):
    """Prove an existing frozen preparation covers exactly this request.

    Every mismatch fails closed: a different skeleton identity, a different
    source/run path, a different seed/world type, a changed plan file or an
    unreadable plan all raise instead of preparing anything new.
    """
    path = Path(reuse_prepared).resolve()
    record = read_record(path)
    for key in ('source','skeleton_run','island_product_path','island_identity','binding','analysis','plans','imported_sha256'):
        if key not in record:
            raise ValueError('reuse prepared record is missing a required field: ' + key)
    if run is None or not str(run).strip():
        raise ValueError('reuse prepared requires the original skeleton run to re-check the island binding')
    if record.get('mountains',{}).get('products'):
        raise ValueError('reuse prepared already carries scheduled mountain products; reuse its world input instead')
    binding = islands.load_binding(source, record['island_product_path'], record['island_identity'], run)
    if record['source'] != str(Path(source).resolve()):
        raise ValueError('reuse prepared belongs to a different skeleton source path')
    if record['skeleton_run'] != str(Path(run).resolve()):
        raise ValueError('reuse prepared belongs to a different skeleton-run path')
    if binding.product.config.world_seed != world_seed:
        raise ValueError('reuse prepared world seed differs from the requested seed')
    if binding.product.config.world_type != world_type:
        raise ValueError('reuse prepared world type differs from the requested type')
    if binding.product.config.density != island_density:
        raise ValueError('reuse prepared island density differs from the requested density')
    recorded_layout = record.get('island_layout', DEFAULT_ISLAND_LAYOUT)
    if recorded_layout != island_layout:
        raise ValueError('reuse prepared island layout differs from the requested layout: '
                         + str(recorded_layout))
    _verify_product_layout(binding.product, island_layout,
                           island_config_record(island_layout, world_type=world_type, world_seed=world_seed,
                                               island_density=island_density))
    islands.validate_saved_binding(record['binding'], binding.record)
    api = mountains._api()
    plans = []
    for entry in record['plans']:
        if islands.file_sha(entry['path']) != entry['sha256']:
            raise ValueError('reused world mountain plan SHA changed: ' + str(entry['path']))
        plan = api.load_mountain_plan(entry['path'], entry['identity'], binding.product)
        if plan.manifest['blend_policy'] != entry['blend_policy']:
            raise ValueError('reused world mountain blend policy differs from its record')
        plans.append(dict(entry))
    return path, record, plans


def prepare(source, run, out, *, world_type, world_seed, island_density=DEFAULT_ISLAND_DENSITY,
            reuse_prepared=None, defer_mountain_analysis=False, island_layout=DEFAULT_ISLAND_LAYOUT):
    """Prepare a new sidecar and bounded fixed-1km qualification plans.

    `reuse_prepared` republishes an existing frozen preparation that is strictly
    bound to this source, skeleton run, world seed and world type: the island
    sidecar and mountain plans are referenced after identity/SHA/read checks and
    are never regenerated or re-qualified. `defer_mountain_analysis` records an
    explicit pending-analysis instead of spending the bounded CPU qualification
    budget (coarse 10000x8000 maps): island geometry is still prepared and saved
    once, plans stay empty and the status is never reported complete or empty.

    `island_density` is the declared island-feature density handed to the frozen
    OceanIslandConfig. It is recorded in the input and must match on reuse: a
    10000x8000 world keeps the real island shapes and just publishes fewer
    features, so the product manifest stays inside the frozen reader's byte
    budget without relaxing any reader limit.

    `island_layout` selects the island candidate layout handed to the same frozen
    OceanIslandConfig: 'old' (default) passes no new keyword and keeps every old
    call byte-identical, 'clustered' passes CLUSTERED_LAYOUT_CONFIG as explicit
    keywords. The actual config is recorded only for a clustered preparation;
    an old-layout record keeps its historical shape and identity. Reuse compares
    the recorded config with the frozen product config field by field and never
    derives a layout from a new quality or size.
    """
    if island_density not in ISLAND_DENSITIES:
        raise ValueError('island density must be one of ' + ', '.join(ISLAND_DENSITIES))
    config_record = island_config_record(island_layout, world_type=world_type, world_seed=world_seed,
                                         island_density=island_density)
    # Refuse a layout this core cannot express before any directory, sidecar or plan exists,
    # so a clustered request never leaves a half-prepared output behind.
    _, core, _ = islands._public_api()
    layout_kwargs = _config_class_kwargs(core, island_layout)
    reused = None if reuse_prepared is None else _verified_reuse(
        reuse_prepared, source, run, world_type, world_seed, island_density, island_layout)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    if reused is not None:
        prepared_path, old, plans = reused
        return write_record(out/'prepared.json', dict(
            schema=SCHEMA,policy=POLICY,source=old['source'],skeleton_run=old['skeleton_run'],
            island_product_path=old['island_product_path'],island_identity=old['island_identity'],
            binding=old['binding'],analysis=json.loads(json.dumps(old['analysis'])),plans=plans,
            mountains=dict(status='not-scheduled',products=[]),imported_sha256=old['imported_sha256'],
            island_density=island_density, **_layout_record(island_layout, config_record),
            reuse=dict(prepared=str(prepared_path),prepared_identity=old['identity'],
                       reused=dict(islands=old['island_product_path'],plans=[entry['path'] for entry in plans]),
                       deferred_mountain_analysis=bool(defer_mountain_analysis),
                       meaning='republished references to an existing frozen preparation; no island generation and no mountain re-qualification')))
    api = mountains._api()
    plate = core.PlateOceanSource.from_npz(source)
    product = core.prepare_ocean_islands(plate, core.OceanIslandConfig(
        world_type=world_type, world_seed=world_seed, density=island_density,
        **layout_kwargs))
    # The frozen product must carry the config that the record claims before anything else
    # (binding, plans) is allowed to depend on it.
    _verify_product_layout(product, island_layout, config_record)
    product_path = out/'islands.npz'
    core.save_product(product, product_path)
    binding = islands.load_binding(source,product_path,product.identity,run)
    config = api.IslandMountainConfig()
    bounds = plate.bounds_m
    cells = math.ceil((bounds[2]-bounds[0])/1000)*math.ceil((bounds[3]-bounds[1])/1000)
    plans = []
    pending = []
    catalog = []
    if defer_mountain_analysis:
        # Explicit coarse-map request: qualify nothing and fake no budget.
        windows = []
        pending = [dict(reason=DEFERRED_ANALYSIS_REASON, bounds_m=list(bounds))]
    elif cells <= config.max_analysis_cells:
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
                                qualification=DEFERRED_ANALYSIS_QUALIFICATION if defer_mountain_analysis else
                                f'actual exposed connected area strictly >{config.min_area_km2:g} km2; no width gate',pending=pending,windows=catalog),
                  plans=plans,mountains=dict(status='not-scheduled',products=[]),
                  island_density=island_density, **_layout_record(island_layout, config_record),
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
    if record['policy'] != POLICY:
        raise ValueError('world mountain source/island/run binding differs')
    compatibility = islands.validate_saved_binding(record['binding'], binding.record)
    api = mountains._api()
    mountain_reader = validate_mountain_reader(record, islands.file_sha(Path(api.__file__)), compatibility)
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
    return fields,dict(record=record,input_file_sha256=islands.file_sha(path), binding_compatibility=compatibility,
                       mountain_reader=mountain_reader,
                       sampled_cells=int(assigned.sum()),nonzero_delta_cells=int(np.count_nonzero(delta)),
                       meaning='30m frozen derived-minus-analytic-base correction sampled at final world cell centres before erosion/hydrology')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','schedule','fast','bind-existing'))
    parser.add_argument('--skeleton');parser.add_argument('--run');parser.add_argument('--out',required=True)
    parser.add_argument('--world-type',default='multi-continent');parser.add_argument('--seed',type=int,default=20260903)
    parser.add_argument('--island-density',default=DEFAULT_ISLAND_DENSITY,choices=ISLAND_DENSITIES,
                        help='declared island-feature density handed to OceanIslandConfig; record it and reuse must match '
                             '(10000x8000 maps use low to keep the product manifest inside the frozen budget)')
    parser.add_argument('--island-layout', default=DEFAULT_ISLAND_LAYOUT, choices=ISLAND_LAYOUTS,
                        help='island candidate layout handed to OceanIslandConfig; old (default) keeps every existing '
                             'call unchanged, clustered declares the clustered-provinces preset explicitly')
    parser.add_argument('--island-product');parser.add_argument('--island-identity')
    parser.add_argument('--plan');parser.add_argument('--plan-identity');parser.add_argument('--task-report')
    parser.add_argument('--input');parser.add_argument('--use-gpu',action='store_true')
    parser.add_argument('--reuse-prepared',default=None,
                        help='republish an existing prepared.json strictly bound to this skeleton/run/seed/world-type; no island generation, no mountain re-qualification')
    parser.add_argument('--defer-mountain-analysis',action='store_true',
                        help='record an explicit pending-analysis instead of qualifying island mountains (coarse 10000x8000 maps)')
    parser.add_argument('--world-processes', action='store_true')
    parser.add_argument('--resume-processes', action='store_true')
    parser.add_argument('--min-free-gib', type=float, default=None,
                        help='optional free-memory floor for fast freeze only; default keeps fast_relief.MIN_FREE_BYTES (2 GiB)')
    parser.add_argument('--spacing-m', type=float, default=None,
                        help='fast-layer sample spacing in metres (default: fast_relief.SPACING_M = 2000)')
    args=parser.parse_args(argv)
    if args.action=='prepare':prepare(args.skeleton,args.run,args.out,world_type=args.world_type,world_seed=args.seed,
        island_density=args.island_density,
        reuse_prepared=args.reuse_prepared,defer_mountain_analysis=args.defer_mountain_analysis,
        island_layout=args.island_layout)
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
        min_free = None if args.min_free_gib is None else int(args.min_free_gib * 2 ** 30)
        params = None if args.spacing_m is None else {'spacing_m': float(args.spacing_m)}
        kwargs = dict(island_product_path=record['island_product_path'],expected_island_identity=record['island_identity'],
            skeleton_run_path=record['skeleton_run'],mountain_input_path=args.input,
            process_config={} if args.world_processes else None, params=params)
        if min_free is not None:
            kwargs['min_free_bytes'] = min_free
        fast_relief.freeze(record['source'],args.out,relief='orogen', **kwargs)
    return 0

if __name__=='__main__':raise SystemExit(main())
