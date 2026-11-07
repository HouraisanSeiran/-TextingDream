"""Author-side binding to Terragenesis world processes; queries only read products."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from . import graph_hydro as gh


def load_history(sk, config=None):
    """Require saved initial states; never infer old geology from final plates."""
    gh.load_terragenesis()
    from terrain_pipeline.world_geology import build_history
    required = ('elevation_m', 'continental_fraction', 'plate_id', 'crust_thickness_m')
    with np.load(sk['path'], allow_pickle=False) as archive:
        manifest = json.loads(archive['manifest_json'].item())
        initial = {}
        final = {}
        for prefix, fields in (('initial/', initial), ('final/', final)):
            for name in required:
                key = prefix + name
                if key not in archive:
                    raise ValueError('world geology needs a new skeleton with --record-history: missing ' + key)
                value = np.asarray(archive[key])
                if hashlib.sha256(value.tobytes()).hexdigest() != manifest['arrays'][key]['sha256']:
                    raise ValueError('history source array SHA mismatch: ' + key)
                fields[name] = value
        for name in required:
            key = 'history/' + name
            if key in archive:
                value = np.asarray(archive[key])
                if hashlib.sha256(value.tobytes()).hexdigest() != manifest['arrays'][key]['sha256']:
                    raise ValueError('trajectory SHA mismatch')
                initial['stage_' + name] = value
                if name == 'elevation_m':
                    final['raw_elevation_m'] = value[-1]
        correction = np.asarray(archive['history/layout_correction_m'])
    cfg = config or {}
    history = build_history(initial, final, world_seed=sk['world_seed'], origin_xz_m=sk['origin_xz_m'],
                            spacing_m=sk['cell_m'], stages=cfg.get('history_stages', cfg.get('geology_stages', 50)),
                            span_ma=cfg.get('history_span_ma', cfg.get('geology_span_ma', 500.)),
                            initial_source_identity=sk['identity'], final_source_identity=sk['identity'])
    history['arrays']['tectonic_to_layout_correction_m'] = correction
    history['metadata']['layout_correction'] = 'stored separately; generated mountain layout and ocean smoothing, not a geological event'
    from terrain_pipeline.common_infra import identity
    history['metadata'].pop('identity', None)
    history['metadata']['identity'] = identity(history['arrays'], history['metadata'])
    return history


def compute(sk, elevation, ocean, mesh, outlets, first, spacing, *, lagoon=None, protected=None, config=None, out_dir=None):
    gh.load_terragenesis()
    from terrain_pipeline import drainage, world_processes
    from terrain_pipeline.common_infra import identity
    routing = drainage.route_graph(elevation, outlets, mesh)
    area = drainage.accumulate_graph(routing.receiver, routing.order, np.full(elevation.shape, spacing ** 2))
    source = dict(elevation_m=np.asarray(elevation, np.float64), ocean_mask=ocean,
                  receiver=routing.receiver, order=routing.order, drainage_area_m2=area,
                  lake_id=np.zeros(elevation.shape, np.int32), first_xz_m=first, spacing_m=spacing,
                  world_seed=sk['world_seed'], source_identity=identity(
                      dict(elevation_m=np.asarray(elevation), ocean_mask=np.asarray(ocean),
                           receiver=routing.receiver),
                      dict(plate_identity=sk['identity'], first_xz_m=list(first), spacing_m=spacing)),
                  plate_identity=sk['identity'], mesh=mesh,
                  geology_history=load_history(sk, config))
    if lagoon is not None:
        source['lagoon_mask'] = lagoon
    if protected is not None:
        source['protected_mask'] = protected
    if out_dir is None:
        return world_processes.compute(source, config)
    root = Path(out_dir)
    if (root/'manifest.json').exists():
        result = world_processes.query(root)
        if result['metadata']['source_identity'] != source['source_identity']:
            raise ValueError('saved world processes belong to another initial bed')
        return result
    if (root/'checkpoint.json').exists():
        checkpoint = json.loads((root/'checkpoint.json').read_text(encoding='utf-8'))
        if checkpoint['source']['source_identity'] != source['source_identity']:
            raise ValueError('saved checkpoint belongs to another initial world bed')
        requested = world_processes.plan(source, config)['config']
        operational = {'pause_after_round', 'wallclock_budget_seconds'}
        if {k: v for k, v in requested.items() if k not in operational} != {
                k: v for k, v in checkpoint['config'].items() if k not in operational}:
            raise ValueError('saved checkpoint numerical configuration differs')
        manifest = world_processes.resume(root/'checkpoint.json')
    else:
        manifest = world_processes.prepare(source, root, config)
    if manifest.get('status') == 'paused':
        raise WorldProcessPaused(manifest)
    return world_processes.query(root)


class WorldProcessPaused(RuntimeError):
    def __init__(self, record):
        super().__init__('World processes paused with saved checkpoint: ' + str(record['checkpoint']))
        self.record = record


def publish(result, out_dir):
    gh.load_terragenesis()
    from terrain_pipeline import world_processes
    root = Path(out_dir)
    if (root/'manifest.json').exists():
        return world_processes.query(root)
    return world_processes.save_product(result, root)


def island_peak_reports(binding, mountain_record, process):
    """Read prepared component ownership and delegate sampled peak accounting."""
    from terrain_pipeline import island_mountains
    from terrain_pipeline.world_process_reporting import island_peak_report
    metadata, arrays = process['metadata'], process['arrays']
    shape = arrays['elevation_m'].shape
    first, spacing = metadata['first_xz_m'], metadata['spacing_m']
    x, z = np.meshgrid(first[0]+np.arange(shape[1])*spacing, first[1]+np.arange(shape[0])*spacing)
    reports = []
    for entry in mountain_record['plans']:
        plan = island_mountains.load_mountain_plan(entry['path'], entry['identity'], binding.product)
        owner = island_mountains.sample_mountain_components(plan, binding.product, x, z)
        components = {row['component_id']: row['island_key'] for row in plan.manifest['components']}
        report = island_peak_report(arrays['layout_elevation_m'], arrays['elevation_m'], owner,
            spacing_m=spacing, source_identity=metadata['source_identity'],
            final_identity=process['identity'], component_ids=components)
        report['plan_identity'] = plan.identity
        sampled = {row['component_label'] for row in report['components']}
        report['unsampled_components'] = [label for label in components if label not in sampled]
        reports.append(report)
    return reports
