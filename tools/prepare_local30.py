"""Explicit preparation of 30 m local tiles (GPU). Queries never call this.

  python tools/prepare_local30.py --config world.json --site harbour-town [--dry-run]
  python tools/prepare_local30.py --config world.json --tile 0 0 --plate <product.npz> --reason "..."

--dry-run only reports tiles, memory and GPU gates. Without it, the two-stage memory check and the GPU gate
run first; when either blocks, the command stops with an error (thresholds are never lowered).
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.world_gen import config as wc, local30, tiles as T  # noqa: E402

TERRAGENESIS = ROOT.parent / '山川形意Terragenesis'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--config', required=True)
    ap.add_argument('--site')
    ap.add_argument('--tile', nargs=2, type=int, metavar=('IX', 'IZ'))
    ap.add_argument('--reason', default='')
    ap.add_argument('--out-root', default=str(ROOT / 'artifacts' / 'worlds'))
    ap.add_argument('--td-dir', default=str(ROOT / 'artifacts' / 'td-world'))
    ap.add_argument('--world-layer-identity',default=None)
    ap.add_argument('--island-product-path','--islands-product',dest='island_product_path',default=None)
    ap.add_argument('--expected-island-identity',default=None)
    ap.add_argument('--skeleton-run',default=None)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--regenerate-stale', action='store_true',
                    help='also regenerate tiles whose cache no longer matches the plate/world layer (replaces them; GPU)')
    a = ap.parse_args(argv)
    if bool(a.island_product_path)!=bool(a.expected_island_identity):
        ap.error('--island-product-path and --expected-island-identity must be supplied together')
    if a.skeleton_run and not a.island_product_path:
        ap.error('--skeleton-run requires an island product')
    cfg = wc.load_config(a.config)
    sk = cfg['skeleton']
    if sk['source'] != 'existing':
        raise SystemExit('prepare_local30: config needs an existing skeleton plate (skeleton.path)')
    plate = Path(sk['path'])
    from app.world_relief import td_resident
    plate_identity = td_resident.read_plate(plate)[1]['identity']
    binding = None
    if a.island_product_path is not None:
        from app.world_gen import ocean_island_adapter as islands
        binding = islands.load_binding(plate,a.island_product_path,a.expected_island_identity,a.skeleton_run)
    lineage_options=dict(plate_identity=plate_identity,world_layer_identity=a.world_layer_identity,
                         island_identity=None if binding is None else binding.product.identity,
                         island_condition_policy=None if binding is None else binding.record['condition_policy'])
    world_root = Path(a.out_root) / cfg['world_name']
    if a.site:
        site = next((s for s in cfg['local_sites'] if s['id'] == a.site), None)
        if site is None:
            raise SystemExit(f'prepare_local30: site {a.site!r} is not registered in the config')
        req = local30.request_local(world_root, site['center_x_m'], site['center_z_m'], site['size_m'], **lineage_options)
        wanted = ('unprepared', 'stale') if a.regenerate_stale else ('unprepared',)
        todo = [(t['ix'], t['iz']) for t in req['tiles'] if t['status'] in wanted]
        stale = {t['id']: t['stale_reasons'] for t in req['tiles'] if t['status'] == 'stale'}
        reason = site['reason']
    elif a.tile:
        if not a.reason.strip():
            raise SystemExit('prepare_local30: --reason is required for an unregistered tile')
        todo, reason = [tuple(a.tile)], a.reason
        stale = {}
    else:
        raise SystemExit('prepare_local30: give --site or --tile')
    from app.world_gen.sysmem import available_memory_bytes
    report = dict(world_root=str(world_root), tiles_to_prepare=[T.tile_id(*t) for t in todo],
                  available_bytes=available_memory_bytes(), stale_tiles=stale)
    if binding is not None:
        report['ocean_island_binding']=binding.record
    try:
        report['memory_gate'] = local30.memory_gate(report['available_bytes'])
    except MemoryError as exc:
        report['memory_gate'] = dict(blocked=str(exc))
    try:
        report['gpu_gate'] = local30.gpu_gate()
    except RuntimeError as exc:
        report['gpu_gate'] = dict(blocked=str(exc))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if a.dry_run or not todo:
        return 0
    if 'blocked' in report['memory_gate'] or 'blocked' in report['gpu_gate']:
        print('blocked: not starting generation', file=sys.stderr)
        return 2
    for ix, iz in todo:
        cells = local30.world_cells_from_pages(a.td_dir, ix, iz)
        m = local30.prepare_tile(world_root, ix, iz, purpose='local-30m', reason=reason, plate_path=plate, world_cells=cells,
                                 world_layer_identity=a.world_layer_identity,terragenesis_root=TERRAGENESIS, reuse=not a.regenerate_stale,
                                 island_product_path=a.island_product_path,expected_island_identity=a.expected_island_identity,
                                 skeleton_run_path=a.skeleton_run)
        print(T.tile_id(ix, iz), 'identity', m['identity'], 'consistency', m['consistency'].get('mae_m'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
