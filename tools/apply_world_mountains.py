"""Apply all saved mountain belts on the complete frozen CPU world grid.

Writes a mountain-only checkpoint in a NEW directory, never a published world
product. No GPU, model, river/lake reuse, glacier or final hydrology is run here.
Use the Terragenesis runtime interpreter for the optional coarse graph erosion.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--product', required=True)
    ap.add_argument('--skeleton', required=True)
    ap.add_argument('--out', required=True, help='must not already exist')
    ap.add_argument('--expected-identity', required=True, help='frozen source world identity')
    ap.add_argument('--reference', default=str(ROOT / 'artifacts/mountain-structure-prototype-20261110/candidate-mountain-group-final'))
    ap.add_argument('--expected-reference', default='09a1faab2138d200492ab68a1bc871e4014ef3fbf856fe7ba594a208397502ba')
    ap.add_argument('--no-erosion', action='store_true', help='diagnostic: omit the approved six coarse erosion rounds')
    a = ap.parse_args(argv)
    from app.world_gen.world_mountain_stage import run_stage
    def log(value):
        print(json.dumps(value, ensure_ascii=False), flush=True)
    try:
        report = run_stage(a.product, a.skeleton, a.out, expected_identity=a.expected_identity,
                           reference=a.reference, expected_reference=a.expected_reference,
                           erosion=not a.no_erosion, log=log)
    except ValueError as exc:
        ap.error(str(exc))
    log(report)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
