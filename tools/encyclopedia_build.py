# -*- coding: utf-8 -*-
"""可复现构库：显式 12 组源 JSON → 独立候选素材库。

为什么需要它：``artifacts/human-encyclopedia/encyclopedia.sqlite3`` 在 ``.gitignore``
里（属于运行期产物），不能是唯一依赖。新克隆的机器用它一次生成同一份库：

    D:\\anaconda\\python.exe -X utf8 -m tools.encyclopedia_build
    D:\\anaconda\\python.exe -X utf8 -m tools.encyclopedia_build --check
    D:\\anaconda\\python.exe -X utf8 -m tools.encyclopedia_build --out temp/db.sqlite3

约定：

* 源文件名单是**显式写死的 12 组**，按顺序导入；``docs/element-catalog/shared-themes.json``
  是聚类索引、不是元素，**故意不在名单里**（导入会被元素库拒绝）。
* 源 JSON 只读，本工具从不改写它们。
* 重复运行同一批文件是幂等的（元素级 + 批次级哈希），不会重复写版本。
* 本工具不参与 app 启动；页面缺库时只提示运行它，不会顺手建库或填库。
* 退出码：0 成功；1 领域错误（校验失败 / 缺文件 / 库不可用）；2 参数用法错误。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import encyclopedia as enc  # noqa: E402

EXIT_OK = 0
EXIT_ERROR = 1

DEFAULT_OUT = 'artifacts/human-encyclopedia/encyclopedia.sqlite3'

# 显式名单：现实生产生活六组 + 跨题材元素六组。
GROUPS = (
    'docs/human-encyclopedia/staples.json',
    'docs/human-encyclopedia/produce.json',
    'docs/human-encyclopedia/flavors.json',
    'docs/human-encyclopedia/animal-foods.json',
    'docs/human-encyclopedia/materials.json',
    'docs/human-encyclopedia/tools.json',
    'docs/element-catalog/eastern.json',
    'docs/element-catalog/western.json',
    'docs/element-catalog/society.json',
    'docs/element-catalog/steam-horror.json',
    'docs/element-catalog/reality-physical.json',
    'docs/element-catalog/reality-human.json',
)
# 明确排除：聚类索引不是元素文档。
EXCLUDED = ('docs/element-catalog/shared-themes.json',)


def _emit(payload, as_json):
    if as_json:
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write('\n')


def _expected():
    """名单里每组应有的元素/来源条数（只读源 JSON，不写库）。"""
    rows = []
    for relative in GROUPS:
        path = ROOT / relative
        document = json.loads(path.read_text(encoding='utf-8-sig'))
        rows.append({'file': relative, 'group': document.get('group'),
                     'elements': len(document.get('elements') or []),
                     'sources': len(document.get('sources') or [])})
    return rows


def build(out_path, as_json=False):
    missing = [relative for relative in GROUPS if not (ROOT / relative).exists()]
    if missing:
        sys.stderr.write('缺少采集 JSON，未建库：\n  ' + '\n  '.join(missing) + '\n')
        return EXIT_ERROR
    out = Path(out_path)
    if not out.is_absolute():
        out = ROOT / out
    expected = _expected()
    results = []
    for relative in GROUPS:
        result = enc.import_file(out, ROOT / relative)
        results.append(result.as_dict())
    stats = enc.stats(out)
    if not as_json:
        for row, result in zip(expected, results):
            extra = '  重复批次：零写入' if result['idempotent'] else ''
            sys.stdout.write('%s → %s：元素 %d（新版本 %d / 未变 %d），来源 %d%s\n'
                             % (row['file'], result['namespace'], result['elements'],
                                result['element_versions_written'],
                                result['unchanged_elements'], result['sources'], extra))
        totals = stats['totals']
        sys.stdout.write('库：%s\n  组 %d，元素 %d，元素版本 %d，来源 %d，来源版本 %d，未解析关联 %d\n'
                         % (out, totals['groups'], totals['elements'],
                            totals['element_versions'], totals['sources'],
                            totals['source_versions'], totals['unresolved_relations']))
        sys.stdout.write('  内容为待审候选（needs_review / needs_detail）：库里存在不等于事实已核实，'
                         '也不等于世界里有。\n')
    _emit({'db': str(out), 'groups': expected, 'imports': results,
           'totals': stats['totals']}, as_json)
    return EXIT_OK


def check(out_path, as_json=False):
    out = Path(out_path)
    if not out.is_absolute():
        out = ROOT / out
    if not out.exists():
        sys.stderr.write('库不存在：%s；先运行 tools.encyclopedia_build 生成\n' % out)
        return EXIT_ERROR
    expected = _expected()
    stats = enc.stats(out)
    by_namespace = {group['namespace']: group for group in stats['groups']}
    problems = []
    for row in expected:
        group = by_namespace.get(row['group'])
        if group is None:
            problems.append('%s：库里没有命名空间 %s' % (row['file'], row['group']))
        elif group['elements'] != row['elements']:
            problems.append('%s：库里 %d 条，源文件 %d 条'
                            % (row['file'], group['elements'], row['elements']))
    if not as_json:
        for row in expected:
            group = by_namespace.get(row['group']) or {}
            sys.stdout.write('%-46s %-18s 库内 %3s / 源 %3d\n'
                             % (row['file'], row['group'], group.get('elements', '—'),
                                row['elements']))
        if problems:
            sys.stdout.write('不一致：\n  ' + '\n  '.join(problems) + '\n')
        else:
            sys.stdout.write('一致：%d 组、%d 条元素（与显式名单相符）\n'
                             % (len(expected), sum(row['elements'] for row in expected)))
    _emit({'db': str(out), 'ok': not problems, 'problems': problems}, as_json)
    return EXIT_OK if not problems else EXIT_ERROR


def build_parser():
    parser = argparse.ArgumentParser(
        prog='encyclopedia_build',
        description='按显式 12 组名单可复现地生成人类百科候选库（幂等、只读源 JSON）',
    )
    parser.add_argument('--out', default=DEFAULT_OUT,
                        help='库文件路径（默认 %s）' % DEFAULT_OUT)
    parser.add_argument('--check', action='store_true',
                        help='只核对现有库与名单条数是否一致，不写库')
    parser.add_argument('--json', action='store_true', help='以 JSON 输出')
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.check:
            return check(args.out, args.json)
        return build(args.out, args.json)
    except enc.EncyclopediaError as error:
        sys.stderr.write('拒绝：%s\n' % error)
        return EXIT_ERROR
    except FileNotFoundError as error:
        sys.stderr.write('文件不存在：%s\n' % error)
        return EXIT_ERROR
    except (OSError, ValueError) as error:
        sys.stderr.write('失败：%s\n' % error)
        return EXIT_ERROR


if __name__ == '__main__':
    raise SystemExit(main())
