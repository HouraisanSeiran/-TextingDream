# -*- coding: utf-8 -*-
"""价格一致性审计：把同类、同计价单位的物品放在一起比，挑出明显偏离的估价。

价格是几路采集分别估的，同类东西可能落在不同档。本工具只**报告**，不改任何文件：

* 分组键：主标签（有 primary 时）否则第一个 ``kind:`` 标签，再加计价单位 ``per``。
* 组内取 max 的中位数；某条 max 高于中位数 ``--ratio`` 倍或低于 1/``--ratio`` 就列为异常。
* 组内少于 ``--min-group`` 条不比（样本太少，中位数没意义）。
* ``not_for_sale`` / ``priceless`` 不参与比较。

用法::

    python -X utf8 -m tools.price_audit            # 文本报告
    python -X utf8 -m tools.price_audit --json     # JSON
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import catalog_overlay  # noqa: E402
from tools import encyclopedia_build as build  # noqa: E402
from tools import game_fields  # noqa: E402


def collect(files=None):
    """读全部构库分区（叠加旁挂后），返回带价格的行。"""
    rows = []
    for relative in files or build.groups_for(**build.ALL_FLAGS):
        document = json.loads((ROOT / relative).read_text(encoding='utf-8-sig'))
        document = catalog_overlay.overlay(game_fields.overlay(document))
        for element in document.get('elements') or []:
            game = element.get('game')
            if not game:
                continue
            price = game.get('price') or {}
            if price.get('tier') in game_fields.NO_PRICE_TIERS:
                continue
            kinds = [tag.split(':', 1)[1] for tag in element.get('tags') or [] if tag.startswith('kind:')]
            rows.append({
                'group': document.get('group'),
                'id': element.get('id'),
                'name': element.get('name'),
                'class': element.get('primary') or (kinds[0] if kinds else 'unknown'),
                'per': price.get('per'),
                'min': price.get('min'),
                'max': price.get('max'),
                'tier': price.get('tier'),
            })
    return rows


ACCEPTED_FILE = 'docs/element-catalog/game-fields/price-audit-accepted.json'


def load_accepted(root=None):
    """人工复核后确认合理的偏离（元素 id → 理由）。文件不存在就是空表。"""
    path = Path(root or ROOT) / ACCEPTED_FILE
    if not path.is_file():
        return {}
    document = json.loads(path.read_text(encoding='utf-8-sig'))
    entries = document.get('entries')
    if document.get('schema') != 'price_audit_accepted_v1' or not isinstance(entries, dict):
        raise ValueError('%s 格式不对' % ACCEPTED_FILE)
    return entries


def audit(rows, ratio=4.0, min_group=4):
    buckets = {}
    for row in rows:
        buckets.setdefault((row['class'], row['per']), []).append(row)
    findings = []
    for (klass, per), items in sorted(buckets.items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1]))):
        if len(items) < min_group:
            continue
        median = statistics.median(max(item['max'], 1) for item in items)
        for item in items:
            value = max(item['max'], 1)
            if value > median * ratio or value < median / ratio:
                findings.append(dict(item, median=median, size=len(items),
                                     direction='high' if value > median else 'low'))
    return findings


def main(argv=None):
    parser = argparse.ArgumentParser(prog='price_audit', description='价格一致性审计（只报告）')
    parser.add_argument('--ratio', type=float, default=4.0, help='偏离中位数多少倍算异常（默认 4）')
    parser.add_argument('--min-group', type=int, default=4, help='组内至少几条才比较（默认 4）')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    rows = collect()
    accepted = load_accepted()
    known = {row['id'] for row in rows}
    stale = sorted(set(accepted) - known)
    if stale:
        sys.stderr.write('已审清单指向不存在或无价的元素：%s\n' % ', '.join(stale))
        return 1
    all_findings = audit(rows, args.ratio, args.min_group)
    findings = [item for item in all_findings if item['id'] not in accepted]
    if not args.json:
        sys.stdout.write('已审确认合理 %d 条（见 %s）\n'
                         % (len(all_findings) - len(findings), ACCEPTED_FILE))
    if args.json:
        json.dump({'priced': len(rows), 'findings': findings}, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write('\n')
        return 0
    sys.stdout.write('有价条目 %d，异常 %d（偏离同类同单位中位数 %.1f 倍以上）\n'
                     % (len(rows), len(findings), args.ratio))
    for item in findings:
        sys.stdout.write('  [%s] %-6s %s/%s %s 「%s」 %s–%s 便士/%s（同组 %d 条中位 %s）\n'
                         % (item['direction'], item['tier'], item['group'], item['id'], item['class'],
                            item['name'], item['min'], item['max'], item['per'], item['size'],
                            item['median']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
