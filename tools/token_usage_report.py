"""Print observed model token rate from the independent local usage history.

Usage: python tools/token_usage_report.py --db saves/textiledream.sqlite3 --hours 24
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
from app.paths import SAVE_DB


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(SAVE_DB))
    parser.add_argument("--hours", type=float, default=24)
    args = parser.parse_args(argv)
    report = Store(Path(args.db)).token_usage_summary(hours=args.hours)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    overall = report["overall"]
    if overall["total_tokens_per_hour"] is None:
        print("\n输入或输出用量计量不完整，合计速率未知；离线调用不计 token，不能把未知当作 0。")
    else:
        print("\n观测速率：%s token/小时（输入 %s，输出 %s）。" %
              (overall["total_tokens_per_hour"], overall["input_tokens_per_hour"],
               overall["output_tokens_per_hour"]))
    if not report['coverage']['window_complete']:
        print("历史覆盖不完整；连续记录起点：%s。" % report['coverage']['complete_since'])


if __name__ == "__main__":
    main()
