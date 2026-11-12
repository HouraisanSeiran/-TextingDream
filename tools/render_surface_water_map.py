"""Render saved monthly lake/river sidecar over an immutable environment atlas."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))

from app.world_gen.surface_water_map import render_months
from render_terrain_sample import find_edge, screenshot


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--environment', required=True)
    parser.add_argument('--surface-water', required=True)
    parser.add_argument('--hydrology', required=True, help='Original completed hydrology product (verified regions.json density)')
    parser.add_argument('--river-display', help='Optional source-bound display-only river JSON; never recompute water')
    parser.add_argument('--environment-identity', required=True)
    parser.add_argument('--surface-identity', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--months', nargs='+', type=int, default=[1, 7, 12])
    parser.add_argument('--width', type=int, default=1800)
    parser.add_argument('--html-only', action='store_true')
    args = parser.parse_args(argv)
    capture = None
    if not args.html_only:
        edge = find_edge()
        capture = lambda html, png, w, h: screenshot(edge, html, png, w, h)
    records = render_months(args.environment, args.surface_water, args.out,
        expected_environment_identity=args.environment_identity,
        expected_surface_identity=args.surface_identity, months=tuple(args.months),
        width=args.width, screenshot=capture, hydrology=args.hydrology, river_display=args.river_display)
    print(f'Saved {len(records)} monthly maps to {args.out}; render-only, parents unchanged')


if __name__ == '__main__':
    main()
