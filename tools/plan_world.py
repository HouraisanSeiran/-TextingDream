"""Read a world config and write plan.json (no generation).

  python tools/plan_world.py --config docs/examples/world-config.example.json --out artifacts/worlds/<name>/plan.json
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.world_gen import config as wc, planner  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--config', required=True)
    ap.add_argument('--out')
    ap.add_argument('--no-verify', action='store_true', help='skip loading the existing skeleton product')
    a = ap.parse_args(argv)
    cfg = wc.load_config(a.config)
    plan = planner.build_plan(cfg, verify_skeleton=not a.no_verify)
    out = Path(a.out) if a.out else ROOT / 'artifacts' / 'worlds' / cfg['world_name'] / 'plan.json'
    planner.write_plan(plan, out)
    print(json.dumps(dict(out=str(out), identity=plan['identity'], world_layer_status=plan['world_layer'].get('status'),
                          local_tiles=plan['local']['tiles_unique'], local_gpu_seconds=plan['local']['gpu_estimate']['inference_seconds_total'],
                          problems=plan['local']['problems']), indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
