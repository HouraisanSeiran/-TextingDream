"""Print observed model token rate from the local trace store.

Usage: python tools/token_usage_report.py --db data/textiledream.sqlite3 --hours 24
No provider request is made and no prompt/response body is printed.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.storage import Store
from app.token_usage import summarize


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/textiledream.sqlite3")
    parser.add_argument("--hours", type=float, default=24)
    args = parser.parse_args(argv)
    report = summarize(Store(Path(args.db)).all("trace"), hours=args.hours)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    overall = report["overall"]
    if overall["total_tokens_per_hour"] is None:
        print("\n没有可计量的供应商 usage；离线调用不计 token，不能把未知当作 0。")
    else:
        print("\n观测速率：%s token/小时（输入 %s，输出 %s）。" %
              (overall["total_tokens_per_hour"], overall["input_tokens_per_hour"],
               overall["output_tokens_per_hour"]))


if __name__ == "__main__":
    main()
