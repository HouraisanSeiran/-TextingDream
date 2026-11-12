"""Generate a new tectonic skeleton (CPU) from a world config or from preset arguments.

  python tools/generate_world_skeleton.py --config world.json [--plan-only]
  python tools/generate_world_skeleton.py --preset archipelago --size-km 1600 --name sample-archipelago
  python tools/generate_world_skeleton.py --preset pangaea --width-km 10000 --height-km 8000 --name big-rect

Output: artifacts/worlds/<world_name>/ {skeleton.npz, preview.png, skeleton-run.json}.
--size-km is the legacy square shortcut; --width-km/--height-km must be given together and write the real
rectangle into the config, so skeleton-run.json reports the true shape (cell class from the longest side).
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
    ap.add_argument('--geography-json', help='JSON array of finite metric soft land/crust features (positive land, negative sea)')
    ap.add_argument('--preset', choices=wc.WORLD_TYPES)
    ap.add_argument('--size-km', type=float, default=None, help='legacy square world side in km (default 1600)')
    ap.add_argument('--width-km', type=float, help='world width in km; must be given together with --height-km')
    ap.add_argument('--height-km', type=float, help='world height in km; must be given together with --width-km')
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
    if (a.width_km is None) != (a.height_km is None):
        ap.error('--width-km and --height-km must be given together (or use --size-km for a square)')
    if a.width_km is not None and a.size_km is not None:
        ap.error('--width-km/--height-km replace --size-km; give one or the other')
    if a.config and a.geography_json is not None:
        ap.error('--geography-json cannot be combined with --config; put features in that config')
    if a.config:
        cfg = wc.load_config(a.config)
    else:
        if not a.preset:
            ap.error('--config or --preset required')
        mountain = float(a.mountain) if a.mountain.replace('.', '', 1).isdigit() else a.mountain
        skel = {}
        if a.cell_km:
            skel['cell_size_km'] = a.cell_km
        world = {'type': a.preset, 'ocean_fraction': a.ocean, 'mountain_cover': mountain}
        if a.width_km is not None:
            world.update(width_km=a.width_km, height_km=a.height_km)
        else:
            world['size_km'] = 1600.0 if a.size_km is None else a.size_km
        try:
            features = json.loads(a.geography_json) if a.geography_json is not None else []
        except ValueError as exc:
            ap.error(f'--geography-json: {exc}')
        cfg = wc.normalize({'world_name': a.name or f'sample-{a.preset}', 'world_seed': a.seed,
                            'world': world, 'skeleton': skel, 'geography_features': features})
    if a.plan_only:
        print(json.dumps(sk.plan_skeleton(cfg), indent=2, ensure_ascii=False))
        return 0
    out = Path(a.out_root) / cfg['world_name']
    orogen = {'target_cover': a.mountain_area} if a.mountain_area is not None else None
    m = sk.generate_skeleton(cfg, out, max_iterations=a.max_iterations, enhance=a.enhance, ridges=a.ridges,
                             orogen_params=orogen, record_history=a.record_history)
    w = cfg['world']
    print(json.dumps({'out': str(out), 'world': dict(width_km=w['width_km'], height_km=w['height_km'],
                                                     cell_size_km=cfg['skeleton']['cell_size_km']),
                      'targets': m['targets'], 'actual': m['actual'], 'seconds': m['seconds'],
                      'peak_rss_bytes': m['peak_rss_bytes']}, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
