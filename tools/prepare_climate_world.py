"""Author-only TG game-diagnostic climate plan / prepare / bounded probe."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.world_gen import climate_world_stage as stage


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('plan', 'prepare', 'probe', 'recover'), default='plan')
    parser.add_argument('--source', type=Path, default=ROOT/'artifacts/mountain-glacier-hydrology-20261111/world')
    parser.add_argument('--expected-source-identity', default=stage.DEFAULT_SOURCE_IDENTITY)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--config-json', type=Path, help='Explicit overrides of approved diagnostic scenario')
    parser.add_argument('--references', type=Path)
    parser.add_argument('--probe-window', type=int, nargs=4, metavar=('Z0', 'X0', 'Z1', 'X1'))
    args = parser.parse_args(argv)
    if args.mode != 'plan' and args.out is None:
        parser.error('--out is required for prepare/probe/recover')
    if args.mode == 'probe' and args.probe_window is None:
        parser.error('--probe-window is required; never silently choose a production domain')
    started = time.perf_counter()
    source = stage.climate_source_from_map(args.source, expected_identity=args.expected_source_identity)
    cfg = json.loads(args.config_json.read_text(encoding='utf-8')) if args.config_json else None
    probe = None
    if args.mode == 'probe':
        source, probe = stage.probe_source(source, args.probe_window)
    planned = stage.plan(source, cfg, args.references)
    if args.mode == 'plan':
        print(json.dumps(planned, ensure_ascii=False, indent=2))
        return 0
    record = stage.prepare(source, args.out, cfg, args.references, recover=args.mode == 'recover')
    report = dict(mode=args.mode, identity=record['identity'], manifest_identity=record['manifest_identity'],
        source_identity=source['source_identity'], plan=planned, fields=record['fields'],
        costs=record['metadata']['costs'], elapsed_wall_seconds=time.perf_counter()-started,
        probe=probe, snow_ice=False, terrain_evolution=False)
    if probe is not None:
        stage._write_json(args.out/'probe-report.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
