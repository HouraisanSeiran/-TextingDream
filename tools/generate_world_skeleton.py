"""Generate a new tectonic skeleton (CPU) from a world config or from preset arguments.

  python tools/generate_world_skeleton.py --config world.json [--plan-only]
  python tools/generate_world_skeleton.py --preset archipelago --size-km 1600 --name sample-archipelago

Output: artifacts/worlds/<world_name>/ {skeleton.npz, preview.png, skeleton-run.json}.
--plan-only runs only the Terragenesis plan() pre-check and prints it. Generation refuses to start
when available memory is below app.world_gen.skeleton.MIN_FREE_BYTES.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.world_gen import config as wc, skeleton as sk  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--config')
    ap.add_argument('--preset', choices=wc.WORLD_TYPES)
    ap.add_argument('--size-km', type=float, default=1600)
    ap.add_argument('--name')
    ap.add_argument('--seed', type=int, default=wc.DEFAULT_WORLD_SEED)
    ap.add_argument('--ocean', type=float, default=0.6)
    ap.add_argument('--mountain', default='medium')
    ap.add_argument('--cell-km', type=float)
    ap.add_argument('--out-root', default=str(ROOT / 'artifacts' / 'worlds'))
    ap.add_argument('--plan-only', action='store_true')
    ap.add_argument('--record-history', action='store_true', help='save actual initial state and offline-step trajectory for world geology')
    ap.add_argument('--max-iterations', type=int, default=5)
    ap.add_argument('--enhance', action='store_true', help='dream-world-skeleton-2: convergent-boundary mountain belts + plains relief')
    ap.add_argument('--ridges', choices=('fractal', 'orogen'), default=None,
                    help='fractal = dream-world-skeleton-3: vector ridge network (fractal main ridges, branches, passes, gaps) stored in the npz; '
                         'orogen = dream-world-skeleton-4: 150-400 km orogen belts with 2-4 parallel ranges, basins, foothills, plateaus')
    ap.add_argument('--mountain-area', type=float, default=None,
                    help='--ridges orogen only: target belt footprint share of land, 0.20-0.30 (default 0.25 = OROGEN_DEFAULTS)')
    a = ap.parse_args(argv)
    if a.mountain_area is not None and (a.ridges != 'orogen' or not 0.20 <= a.mountain_area <= 0.30):
        ap.error('--mountain-area needs --ridges orogen and a value in [0.20, 0.30]')
    if a.config:
        cfg = wc.load_config(a.config)
    else:
        if not a.preset:
            ap.error('--config or --preset required')
        mountain = float(a.mountain) if a.mountain.replace('.', '', 1).isdigit() else a.mountain
        skel = {'source': 'new'}
        if a.cell_km:
            skel['cell_size_km'] = a.cell_km
        cfg = wc.normalize({'world_name': a.name or f'sample-{a.preset}', 'world_seed': a.seed,
                            'world': {'size_km': a.size_km, 'type': a.preset, 'ocean_fraction': a.ocean,
                                      'mountain_cover': mountain}, 'skeleton': skel})
    if a.plan_only:
        print(json.dumps(sk.plan_skeleton(cfg), indent=2, ensure_ascii=False))
        return 0
    out = Path(a.out_root) / cfg['world_name']
    orogen = {'target_cover': a.mountain_area} if a.mountain_area is not None else None
    m = sk.generate_skeleton(cfg, out, max_iterations=a.max_iterations, enhance=a.enhance, ridges=a.ridges,
                             orogen_params=orogen, record_history=a.record_history)
    print(json.dumps({'out': str(out), 'targets': m['targets'], 'actual': m['actual'], 'seconds': m['seconds'],
                      'peak_rss_bytes': m['peak_rss_bytes']}, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
