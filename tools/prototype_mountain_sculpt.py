"""Generate one local mountain-structure prototype candidate (CPU only, not a world product).

  .venv/Scripts/python.exe tools/prototype_mountain_sculpt.py \
      --skeleton artifacts/terrain-world-10000x8000-20261110/worlds/world-10000x8000-speed-20261110/skeleton.npz \
      --product  artifacts/island-cluster-improvement-20261110/fast-world-clustered \
      --belt 4 --rect -600000 -2800000 1400000 -1000000 \
      --out artifacts/mountain-structure-prototype-20261110/candidate

The output directory holds ``arrays.npz``, ``structure.json`` and a draft ``README.md``; it is **not** a world-map
product and nothing in the default pipeline reads it. No hydrology is computed (no river/lake is drawn). Erosion on
the existing irregular graph is opt-in (``--erode``) and needs the Terragenesis venv (numba).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('NUMBA_CACHE_DIR', str(Path(tempfile.gettempdir()) / 'dream-nbcache'))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--skeleton', required=True, help='dream-world-skeleton-4 npz with ridges/* (hash checked)')
    ap.add_argument('--product', required=True, help='frozen fast-world product directory (elevation/status/water)')
    ap.add_argument('--out', help='candidate directory to write (never an existing world product)')
    ap.add_argument('--expected-identity', default=None, help='expected product manifest identity')
    ap.add_argument('--belt', type=int, default=None, help='orogen belt index to take the chains from (line_belt)')
    ap.add_argument('--rect', nargs=4, type=float, metavar=('X0', 'Z0', 'X1', 'Z1'),
                    help='window in metres at the product cell centres')
    ap.add_argument('--window', nargs=4, type=int, metavar=('IX0', 'IZ0', 'NX', 'NZ'),
                    help='window as product cell indices (alternative to --rect)')
    ap.add_argument('--first-xz', nargs=2, type=float, default=None,
                    help='product first cell centre (default: read from the product manifest)')
    ap.add_argument('--spacing', type=float, default=None, help='product spacing (default: read from the manifest)')
    ap.add_argument('--world-seed', type=int, default=None, help='default: the product manifest world_seed')
    ap.add_argument('--params', default=None, help='JSON object overriding mountain_sculpt.DEFAULTS')
    ap.add_argument('--erode', action='store_true', help='coarse irregular-graph erosion (needs numba/TG venv)')
    ap.add_argument('--no-write', action='store_true', help='compute and print the report, write nothing')
    a = ap.parse_args(argv)
    if bool(a.rect) == bool(a.window):
        ap.error('give exactly one of --rect or --window')
    from app.world_gen import mountain_sculpt as ms
    from app.world_gen import ridge_network as rn
    params = json.loads(a.params) if a.params else None
    manifest, arrays, info = ms.load_product(a.product, a.expected_identity)
    grid_info = manifest['grid']
    if a.first_xz is not None and (abs(a.first_xz[0] - grid_info['first_sample_xz_m'][0]) > 1e-6
                                   or abs(a.first_xz[1] - grid_info['first_sample_xz_m'][1]) > 1e-6):
        ap.error('--first-xz differs from the product grid origin; a window must sit on the source grid')
    if a.spacing is not None and float(a.spacing) != float(grid_info['spacing_m']):
        ap.error('--spacing differs from the product spacing; no resampling is allowed')
    first = tuple(grid_info['first_sample_xz_m'])
    spacing = float(grid_info['spacing_m'])
    shape = tuple(grid_info['shape_zx'])
    world_seed = int(a.world_seed if a.world_seed is not None else manifest['world_seed'])
    if a.rect:
        grid = ms.grid_from_rect(a.rect, first, spacing, shape)
    else:
        grid = ms.grid_from_index(a.window[0], a.window[1], a.window[2], a.window[3], first, spacing)
    net, sk_manifest = rn.load_network(a.skeleton)
    if sk_manifest.get('world_seed') not in (None, world_seed):
        ap.error('skeleton world_seed %r differs from the product %r' % (sk_manifest.get('world_seed'), world_seed))
    if sk_manifest.get('identity') is not None and manifest.get('source_identity') is not None \
            and sk_manifest['identity'] != manifest['source_identity']:
        ap.error('skeleton identity %r differs from the product source_identity %r: not the same world'
                 % (sk_manifest['identity'], manifest['source_identity']))
    print(json.dumps(dict(stage='binding', product_identity=info.identity,
                          source_identity=manifest.get('source_identity'), world_seed=world_seed,
                          window_index=grid['index'], shape=grid['shape'], spacing_m=grid['spacing_m']),
                     ensure_ascii=False))
    structure = ms.select_structure(net, grid['rect_m'], belt=a.belt, world_seed=world_seed, params=params, log=print)
    win = ms.load_window(a.product, grid, expected_identity=a.expected_identity, manifest_arrays=(manifest, arrays, info))
    result = ms.apply_window(win, structure, grid, world_seed=world_seed, params=params, erosion=bool(a.erode), log=print)
    report = dict(identity=result['identity'], grid=dict(first_xz_m=result['first_xz_m'], spacing_m=result['spacing_m'],
                                                        shape_zx=list(result['shape']), rect_m=list(result['rect_m']),
                                                        window_index=list(result['index'])),
                  belt=a.belt, main_lines=structure['meta']['main_lines'],
                  main_direction=structure['meta']['main_direction'], branches=len(structure['branches']),
                  spurs=len(structure['spurs']), passes=len(result['passes']),
                  basins=[b['xz_m'] for b in result['meta']['basins']],
                  support_cells=result['meta']['support_cells'], changed_cells=result['meta']['changed_cells'],
                  changed_land_fraction=result['meta']['changed_land_fraction'],
                  significant_change_cells=result['meta']['significant_change_cells'],
                  source=result['meta']['source'],
                  peak_target_m=result['meta']['peak_target_m'], peak_scale=result['meta']['peak_scale'],
                  floor_range_m=result['meta']['floor_range_m'], volume_change_m3=result['meta']['volume_change_m3'],
                  erosion=result['meta']['erosion'])
    if not a.no_write:
        if not a.out:
            ap.error('--out is required unless --no-write')
        out = Path(a.out)
        if (out / 'manifest.json').exists():
            ap.error('refusing to write into a published world product: %s' % out)
        report['written'] = ms.write_candidate(out, result, note=a.params)
    print(json.dumps(report, ensure_ascii=False, indent=1, default=str))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
