"""Explicit regional TG glacier job; never publishes a world or routes melt."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.world_gen.glacier_stage import (glacier_from_arrays, load_state,
                                         read_bed_region, save_product)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True, help="existing mountain checkpoint NPZ")
    p.add_argument("--bed-key", required=True)
    p.add_argument("--region", nargs=4, type=int, required=True, metavar=("Z0", "X0", "Z1", "X1"))
    p.add_argument("--spacing-m", nargs="+", type=float, help="scalar or dx dz; defaults to NPZ spacing_m")
    p.add_argument("--first-xz-m", nargs=2, type=float, help="source FIRST CELL CENTRE, never extent edge")
    p.add_argument("--ocean-key", help="optional matching NPZ boolean ocean mask")
    p.add_argument("--source-identity", required=True)
    p.add_argument("--terrain-identity", required=True)
    p.add_argument("--source-kind", required=True, help="real source type, e.g. procedural-mountain, NOT TD")
    p.add_argument("--terrain-metadata", type=Path, help="optional checkpoint JSON; verifies its identity")
    p.add_argument("--boundary", choices=("closed", "outflow"), required=True)
    p.add_argument("--outflow-sides", nargs="*", default=[], choices=("west", "east", "north", "south"))
    p.add_argument("--generation-height-m", type=float, required=True)
    p.add_argument("--annual-snow-cap-mwe", type=float, required=True)
    p.add_argument("--target-years", type=int, required=True, help="absolute year, NOT additional years")
    p.add_argument("--sliding-m-per-year", type=float, default=0.0)
    p.add_argument("--edge-ice-threshold-m", type=float, default=1.0,
                   help="diagnostic only; no ice clipping; closed composition still requires exact edge zero")
    p.add_argument("--max-wall-s", type=float, default=30.0, help="cumulative solver budget, including restart")
    p.add_argument("--max-substeps", type=int, default=200000)
    p.add_argument("--max-memory-mb", type=int, default=256, help="TG conservative live-array estimate, not RSS cap")
    p.add_argument("--state", type=Path)
    p.add_argument("--output", type=Path, required=True, help="new directory; no overwrite")
    args = p.parse_args(argv)
    if args.terrain_metadata:
        meta = json.loads(args.terrain_metadata.read_text(encoding="utf-8"))
        if meta["identity"] != args.terrain_identity:
            raise ValueError("checkpoint metadata terrain identity differs")
        grid = meta.get("grid", {})
        if args.spacing_m is None and "spacing_m" in grid:
            args.spacing_m = grid["spacing_m"]
        if args.first_xz_m is None and "first_xz_m" in grid:
            args.first_xz_m = grid["first_xz_m"]
    geometry = read_bed_region(args.input, bed_key=args.bed_key, region=args.region,
                               spacing_m=args.spacing_m, first_xz_m=args.first_xz_m,
                               ocean_key=args.ocean_key)
    result = glacier_from_arrays(
        **geometry, source_identity=args.source_identity, terrain_identity=args.terrain_identity,
        source_kind=args.source_kind, boundary=args.boundary, outflow_sides=args.outflow_sides,
        target_years=args.target_years, elevation_config={"generation_height_m": args.generation_height_m},
        annual_snow_cap_water_m=args.annual_snow_cap_mwe,
        edge_ice_threshold_m=args.edge_ice_threshold_m,
        state=load_state(args.state) if args.state else None,
        config={"max_total_wall_s": args.max_wall_s, "max_total_substeps": args.max_substeps,
                "max_memory_bytes": args.max_memory_mb * 1024**2,
                "effective_sliding_speed_m_per_year": args.sliding_m_per_year},
        provenance={"input_npz": str(args.input.resolve()), "bed_key": args.bed_key,
                    "region_zx_half_open": args.region, "terrain_metadata": str(args.terrain_metadata) if args.terrain_metadata else None})
    save_product(result, args.output)
    print(json.dumps({"output": str(args.output), "completed_years": result["metadata"]["completed_years"],
                      "completed": result["metadata"]["completed"], "stop_reason": result["metadata"]["stop_reason"],
                      "ledger": result["ledger"], "edge_ice": result["metadata"]["edge_ice"],
                      "total_wall_s": result["metadata"]["total_wall_s"]}, ensure_ascii=False))
    return 0 if result["metadata"]["completed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
