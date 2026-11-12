"""Publish a NEW mountain -> TG glacier -> graph-hydrology world product.

Run under the TG Python environment. No generation, resume, or default switch.
Regions JSON: [{"path":"relative/region-dir","window_zx":[z0,x0,z1,x1]}].
Paths in the list are relative to the JSON file, not the current directory.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

from app.world_gen.world_hydrology_stage import publish


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mountains', required=True, type=Path, help='mountains.npz + mountains.json directory')
    parser.add_argument('--glaciers', required=True, type=Path, help='explicit region list JSON; [] allowed, never auto-discovers')
    parser.add_argument('--output', required=True, type=Path, help='new directory only')
    parser.add_argument('--source-product', type=Path, help='same bound frozen source; restores registered lagoon/island protection')
    parser.add_argument('--expected-mountain-identity')
    parser.add_argument('--params', type=Path, help='hydrology overrides JSON; defaults reuse fast_relief DEFAULTS_V3, max 4 breach passes')
    parser.add_argument('--boundary-policy', choices=('closed-edge-zero', 'finite'), default='closed-edge-zero')
    args = parser.parse_args(argv)
    regions = json.loads(args.glaciers.read_text(encoding='utf-8'))
    if not isinstance(regions, list):
        parser.error('--glaciers must contain a JSON list')
    resolved = []
    for item in regions:
        path = Path(item['path'])
        if not path.is_absolute():
            path = args.glaciers.resolve().parent/path
        resolved.append(dict(path=str(path), window_zx=item['window_zx']))
    params = json.loads(args.params.read_text(encoding='utf-8')) if args.params else None
    output, manifest = publish(args.mountains, resolved, args.output, source_product=args.source_product,
        params=params, boundary_policy=args.boundary_policy,
        expected_mountain_identity=args.expected_mountain_identity)
    print(json.dumps(dict(directory=str(output), identity=manifest['identity'], schema=manifest['schema']), ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
