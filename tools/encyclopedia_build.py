# -*- coding: utf-8 -*-
"""可复现构库：显式 14 组源 JSON → 独立候选素材库。

为什么需要它：``artifacts/human-encyclopedia/encyclopedia.sqlite3`` 在 ``.gitignore``
里（属于运行期产物），不能是唯一依赖。新克隆的机器用它一次生成同一份库：

    D:\\anaconda\\python.exe -X utf8 -m tools.encyclopedia_build
    D:\\anaconda\\python.exe -X utf8 -m tools.encyclopedia_build --check
    D:\\anaconda\\python.exe -X utf8 -m tools.encyclopedia_build --out temp/db.sqlite3
    D:\\anaconda\\python.exe -X utf8 -m tools.encyclopedia_build --with-traits --with-cuisine
    python -m tools.encyclopedia_build --with-traits --with-cuisine --with-culture --with-attributes

约定：

* 源文件名单是**显式写死的**，按顺序导入：现实生产生活六组 + 两个增补组
  （food-supplement / craft-supplement）+ 跨题材元素六组 = 历史 14 组。增补组也必须显式登记，
  不能让 ``docs/human-encyclopedia/*.json`` 通配进来——同目录将来还会有别的候选文件，
  通配会把它们悄悄带进交付库。
* 角色特质分区（``docs/playable-demo/character-traits.json``）是**另一份显式名单**
  ``TRAIT_GROUPS``：默认不构入（旧交付口径 14 组 / 528 条不变），
  只有显式传 ``--with-traits`` 才得到最新的 15 组 / 551 条 / 505 来源。
  同样不用通配，避免新起的候选文件被默默带进交付库。
* 饮食／烹饪分区（``docs/human-encyclopedia/cuisine.json``）是**第三份显式名单**
  ``CUISINE_GROUPS``：同样默认不构入，只有显式传 ``--with-cuisine`` 才构入，
  可与 ``--with-traits`` 组合。它也是新起的候选分区，不能靠通配进库；
  条目数会随采集继续变化，本文件**不写死它的条数**。
* 文化与姓名分区（诗歌/小说/口述传统、亚洲姓名、欧洲姓名）是
  ``CULTURE_GROUPS``：只有显式传 ``--with-culture`` 才构入；姓名池不会自动决定
  角色身份、阶层、宗教或性格。
* ``docs/element-catalog/shared-themes.json`` 是聚类索引、不是元素，**故意不在名单里**
  （导入会被元素库拒绝）。
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

# 显式名单：现实生产生活六组 + 增补两组 + 跨题材元素六组（共 14 组）。
# 增补组是独立文件（不是六组的改写版），只能靠这里登记才进库。
GROUPS = (
    'docs/human-encyclopedia/staples.json',
    'docs/human-encyclopedia/produce.json',
    'docs/human-encyclopedia/flavors.json',
    'docs/human-encyclopedia/animal-foods.json',
    'docs/human-encyclopedia/materials.json',
    'docs/human-encyclopedia/tools.json',
    'docs/human-encyclopedia/food-supplement.json',
    'docs/human-encyclopedia/craft-supplement.json',
    'docs/element-catalog/eastern.json',
    'docs/element-catalog/western.json',
    'docs/element-catalog/society.json',
    'docs/element-catalog/steam-horror.json',
    'docs/element-catalog/reality-physical.json',
    'docs/element-catalog/reality-human.json',
)
# 明确排除：聚类索引不是元素文档。
EXCLUDED = ('docs/element-catalog/shared-themes.json',)

# 特质分区是**独立名单**：默认构库仍是历史 14 组（旧测试与旧交付库口径不变），
# 只有显式传 ``--with-traits`` 才把这份 23 条特质一起构入，得到最新 15 组。
# 理由：它是本轮新加的候选分区，不能靠 ``docs/**/*.json`` 通配悄悄进库。
TRAIT_GROUPS = (
    'docs/playable-demo/character-traits.json',
)


# 饮食／烹饪分区也是独立名单：默认不进库，只有 ``--with-cuisine`` 才构入。
# 与特质一样不用通配（同目录还有别的候选文件）。它可与 ``--with-traits`` 组合：
# 两份名单的顺序固定为「14 组 → 特质 → 饮食」。
CUISINE_GROUPS = (
    'docs/human-encyclopedia/cuisine.json',
)
# 文化资料与姓名池是独立名单：默认不进库，只有 ``--with-culture`` 才构入。
# 姓名按语言/地区命名传统分组，避免将跨文化名字混成一个无来源的随机池。
CULTURE_GROUPS = (
    'docs/human-encyclopedia/culture-literature.json',
    'docs/human-encyclopedia/names-asian.json',
    'docs/human-encyclopedia/names-european.json',
)
ATTRIBUTE_GROUPS = (
    'docs/playable-demo/character-attributes.json',
)
# 带特质的历史基线（旧交付口径）；不带任何开关时仍是 ``GROUPS``。
LATEST_GROUPS = GROUPS + TRAIT_GROUPS


def groups_for(with_traits=False, with_cuisine=False, with_attributes=False, with_culture=False):
    """要构库的显式名单。

    不给开关 = 历史 14 组。with_attributes 显式追加现有六项属性资料。
    给了哪个就追加哪个分区；两个都给时顺序是「14 组 → 特质 → 饮食」。
    默认值保持向后兼容，旧调用 ``groups_for(False)`` / ``groups_for(True)`` 行为不变。
    """
    groups = LATEST_GROUPS if with_traits else GROUPS
    if with_cuisine:
        groups = groups + CUISINE_GROUPS
    if with_attributes:
        groups = groups + ATTRIBUTE_GROUPS
    if with_culture:
        groups = groups + CULTURE_GROUPS
    return groups


def _emit(payload, as_json):
    if as_json:
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write('\n')


def _expected(groups=None):
    """名单里每组应有的元素/来源条数（只读源 JSON，不写库）。"""
    groups = tuple(groups or GROUPS)
    rows = []
    for relative in groups:
        path = ROOT / relative
        document = json.loads(path.read_text(encoding='utf-8-sig'))
        rows.append({'file': relative, 'group': document.get('group'),
                     'elements': len(document.get('elements') or []),
                     'sources': len(document.get('sources') or [])})
    return rows


def build(out_path, as_json=False, groups=None):
    groups = tuple(groups or GROUPS)
    missing = [relative for relative in groups if not (ROOT / relative).exists()]
    if missing:
        sys.stderr.write('缺少采集 JSON，未建库：\n  ' + '\n  '.join(missing) + '\n')
        return EXIT_ERROR
    out = Path(out_path)
    if not out.is_absolute():
        out = ROOT / out
    expected = _expected(groups)
    results = []
    for relative in groups:
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


def check(out_path, as_json=False, groups=None):
    out = Path(out_path)
    if not out.is_absolute():
        out = ROOT / out
    if not out.exists():
        sys.stderr.write('库不存在：%s；先运行 tools.encyclopedia_build 生成\n' % out)
        return EXIT_ERROR
    expected = _expected(groups)
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
        description='按显式名单（默认 14 组；可选 --with-traits / --with-cuisine / --with-attributes）'
                    '可复现地生成人类百科候选库（幂等、只读源 JSON）',
    )
    parser.add_argument('--out', default=DEFAULT_OUT,
                        help='库文件路径（默认 %s）' % DEFAULT_OUT)
    parser.add_argument('--check', action='store_true',
                        help='只核对现有库与名单条数是否一致，不写库')
    parser.add_argument('--with-traits', action='store_true',
                        help='在历史 14 组之后追加角色特质分区（23 条），得到最新 15 组')
    parser.add_argument('--with-cuisine', action='store_true',
                        help='追加饮食／烹饪分区（docs/human-encyclopedia/cuisine.json）；'
                             '可与 --with-traits 组合')
    parser.add_argument('--json', action='store_true', help='以 JSON 输出')
    parser.add_argument('--with-attributes', action='store_true',
                        help='追加现有六项角色属性定义；沿用 attribute_v1，不改变角色数值或检定公式')
    parser.add_argument('--with-culture', action='store_true',
                        help='追加诗歌、小说、叙事传统和亚洲/欧洲姓名池（3 个显式分区）')
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    groups = groups_for(args.with_traits, args.with_cuisine, args.with_attributes, args.with_culture)
    try:
        if args.check:
            return check(args.out, args.json, groups)
        return build(args.out, args.json, groups)
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
