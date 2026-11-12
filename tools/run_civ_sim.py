# -*- coding: utf-8 -*-
"""Run the civilisation simulator on a frozen world-map product.

Writes ``artifacts/civ-sim/<name>/manifest.json`` and ``chronicle.json``.
Does not modify the terrain product.

Example (from the repository root)::

    .venv\\Scripts\\python.exe tools/run_civ_sim.py ^
        --product artifacts/fast-world/tg-speed-archipelago-1600-20261108 ^
        --identity db09ec0f6a166d311a0055adeee3601868e618f81e7cdc92f28117524fcbc199 ^
        --seed 20261108 --start-year 0 --end-year 120 --name archipelago-demo
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.civ_sim import CivSimConfig, run_product  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description="织梦文明模拟：读世界层，写编年史，不改地形。")
    parser.add_argument("--product", required=True, help="world-map-product 目录")
    parser.add_argument("--identity", required=True, help="产品 manifest 的 identity，必须一致才跑")
    parser.add_argument("--seed", type=int, required=True, help="文明种子，与地形 world_seed 分开")
    parser.add_argument("--start-year", type=int, default=0)
    parser.add_argument("--end-year", type=int, default=120)
    parser.add_argument("--max-polities", type=int, default=8)
    parser.add_argument("--name", required=True, help="运行名，输出到 <out-root>/<name>/")
    parser.add_argument("--out-root", default="artifacts/civ-sim")
    parser.add_argument(
        "--encyclopedia-db",
        default="artifacts/human-encyclopedia/encyclopedia.sqlite3",
        help="已有人类百科 SQLite；只读姓名池，缺库则回退内置音节",
    )
    parser.add_argument(
        "--require-catalog", action="store_true",
        help="百科库缺失或姓名池为空时直接失败（默认容错回退）",
    )
    args = parser.parse_args(argv)
    config = CivSimConfig(
        seed=args.seed,
        start_year=args.start_year,
        end_year=args.end_year,
        max_polities=args.max_polities,
    )
    out = Path(args.out_root) / args.name
    result = run_product(
        args.product, identity=args.identity, config=config, out_dir=out,
        encyclopedia_db=args.encyclopedia_db, require_catalog=args.require_catalog,
    )
    print(result["out_dir"])
    print("map %s" % result["map_identity"])
    print("chronicle %s" % result["chronicle_sha256"])
    print("counts %s" % result["counts"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
