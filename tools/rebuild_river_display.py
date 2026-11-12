"""Re-trace saved receiver/Q only into an independent, immutable-parent display JSON.

No monthly solver, climate, glacier or lake inventory update is imported or run.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
from app.world_gen import surface_water_map as sw
from app.world_gen import graph_hydro as gh
from app.world_gen.river_flow_network import build_flow_network


def rebuild(environment, surface_water, out, *, environment_identity, surface_identity,
            profile='overview-mainstem-30km', max_segments=18000, max_nodes=1000000,
            max_bytes=150000000):
    """Read saved monthly arrays and original mesh, write ONE new display-only file."""
    env_root, root, out = (Path(p).resolve() for p in (environment, surface_water, out))
    if min(max_segments, max_nodes, max_bytes) <= 0:
        raise ValueError('positive display budgets required')
    if out.exists():
        raise FileExistsError('new display file required')
    if any(out == p or out.is_relative_to(p) for p in (env_root, root)):
        raise ValueError('display output must be outside immutable parents')
    meta, env = sw._json(root / 'manifest.json'), sw._json(env_root / 'manifest.json')
    if (meta.get('identity') != surface_identity or sw._identity(meta) != surface_identity
            or env.get('identity') != environment_identity
            or meta.get('status') != 'finite-year-surface-water' or not meta.get('publishable')):
        raise ValueError('explicit saved parent identities required')
    if any(meta['binding'][k] != env['climate_environment'][k]
           for k in ('source_identity', 'climate_identity', 'hydrology_identity')):
        raise ValueError('environment physical parent differs')
    source = sw.load_source('world-map-product', env_root, expected_identity=environment_identity)
    p = sw.atlas.product_from_source(source, env_root)
    shape = tuple(meta['binding']['shape_zx'])
    if shape != p.shape:
        raise ValueError('saved display grid differs')
    names = ('receiver', 'order', 'hillslope_discharge_m3_s', 'geometry_area_m2',
             'mesh_node_x_m', 'mesh_node_z_m', 'flow_wet_support', 'wet_mask', 'lake_depth_m')
    arrays = {}
    try:
        for name in names:
            arrays[name] = sw._array(root, meta['fields'][name], meta)
        receiver, order = arrays['receiver'].ravel(), arrays['order']
        drainage, _ = gh.load_terragenesis()
        area = drainage.accumulate_graph(receiver, order, arrays['geometry_area_m2'].ravel())
        coords = np.column_stack((arrays['mesh_node_x_m'], arrays['mesh_node_z_m']))
        wet = np.asarray(arrays['wet_mask'], bool) | np.asarray(arrays['flow_wet_support'], bool)
        network = build_flow_network(receiver, order, arrays['hillslope_discharge_m3_s'], area,
            dict(shape_zx=shape, first_xz_m=p.first, spacing_m=p.spacing),
            ocean=p.ocean, monthly_wet_lake=wet, cell_coords_xz_m=coords,
            min_active_q_m3_s=.1, min_display_area_m2=0., cartography_profile=profile,
            max_segments=max_segments, month_days=meta.get('month_days'))
        nodes = sum(len(v['nodes']) for v in network['vectors'])
        if nodes > max_nodes:
            raise ValueError('display exceeds declared max_nodes; no truncation')
        lengths = np.array([np.linalg.norm(np.diff(v['points_xz_m'], axis=0), axis=1).sum()
                            for v in network['vectors']])
        monthly = []
        for m in range(1, 13):
            lines = sw._segments(network, [[] for _ in range(12)], m)
            if len(lines) > max_segments:
                raise ValueError('classified monthly polylines exceed max_segments; no truncation')
            widths = [v['width'] for v in lines]
            drawn_length = sum(np.linalg.norm(np.diff(v['points_xz_m'], axis=0), axis=1).sum() for v in lines)
            monthly.append(dict(month=m, rendered_polylines=len(lines),
                known_active_draw_edges=sum(len(v['edge_anchor_cells']) for v in lines),
                drawn_length_m=float(drawn_length),
                width_range_px=[min(widths), max(widths)] if widths else [],
                unknown_regime_polylines=sum(v['kind'] == 'unknown_regime' for v in lines)))
        summary = dict(network['summary'], stored_nodes=nodes, monthly_render=monthly,
            retained_active_fraction=network['summary']['display_candidate_edge_count'] /
                max(network['summary']['raw_active_edge_count'], 1),
            whole_reach_length_quantiles_m=dict(zip(('p0', 'p25', 'p50', 'p75', 'p90', 'p95', 'p99', 'max'),
                np.percentile(lengths, [0, 25, 50, 75, 90, 95, 99, 100]).tolist())) if lengths.size else {})
        recipe = dict(network['cartography'],
            monthly_lake_cut='union of saved flow_wet_support and actual wet_mask, including invisible shallow water; shore midpoint approximation',
            support_limitation='physical hillslope Q stops at saved monthly wet support; unknown lake-interior/outlet Q NOT reconstructed; short reaches remain, not a restored natural permanent backbone',
            lake_display_min_depth_m=.1,
            invisible_shallow_wet_cells_monthly=np.sum(np.asarray(arrays['wet_mask']) &
                (np.asarray(arrays['lake_depth_m']) <= .1), axis=(1, 2)).tolist(),
            max_segments=max_segments, max_nodes=max_nodes, max_file_bytes=max_bytes)
        record = dict(schema='dream-river-display-sidecar-1',
            binding=dict(surface_water_identity=surface_identity,
                physical_source_identity=meta['binding']['source_identity'],
                surface_manifest_sha256=sw._digest(root / 'manifest.json'),
                environment_identity=environment_identity,
                source_files={meta['fields'][n]['file']: meta['fields'][n]['sha256'] for n in names}),
            recipe=recipe, network=network, summary=summary,
            scope='display only; saved physical Q/receiver/monthly lake inventories and source identity unchanged')
        record['identity'] = sw._identity(record)
        content = json.dumps(record, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
        if len(content.encode('utf-8')) > max_bytes:
            raise ValueError('display exceeds declared max_file_bytes; no truncation')
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding='utf-8')
        return record
    finally:
        for a in arrays.values():
            a._mmap.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--environment', required=True)
    parser.add_argument('--environment-identity', required=True)
    parser.add_argument('--surface-water', required=True)
    parser.add_argument('--surface-identity', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--profile', choices=['all-active', 'overview-mainstem-30km'], default='overview-mainstem-30km')
    parser.add_argument('--max-segments', type=int, default=18000)
    parser.add_argument('--max-nodes', type=int, default=1000000)
    parser.add_argument('--max-bytes', type=int, default=150000000)
    args = parser.parse_args(argv)
    result = rebuild(args.environment, args.surface_water, args.out,
        environment_identity=args.environment_identity, surface_identity=args.surface_identity,
        profile=args.profile, max_segments=args.max_segments, max_nodes=args.max_nodes, max_bytes=args.max_bytes)
    print(json.dumps(dict(identity=result['identity'], file=args.out, summary=result['summary']), ensure_ascii=False))


if __name__ == '__main__':
    main()
