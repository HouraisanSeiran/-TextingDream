# -*- coding: utf-8 -*-
"""可复现构库：显式 14 组源 JSON → 独立候选素材库。

为什么需要它：``artifacts/human-encyclopedia/encyclopedia.sqlite3`` 在 ``.gitignore``
里（属于运行期产物），不能是唯一依赖。新克隆的机器用它一次生成同一份库：

    D:\\anaconda\\python.exe -X utf8 -m tools.encyclopedia_build
    D:\\anaconda\\python.exe -X utf8 -m tools.encyclopedia_build --check
    D:\\anaconda\\python.exe -X utf8 -m tools.encyclopedia_build --out temp/db.sqlite3
    D:\\anaconda\\python.exe -X utf8 -m tools.encyclopedia_build --with-traits --with-cuisine
    python -m tools.encyclopedia_build --with-traits --with-cuisine --with-culture --with-attributes
    D:\\anaconda\\python.exe -X utf8 -m tools.encyclopedia_build --with-fantasy-biology
    D:\\anaconda\\python.exe -X utf8 -m tools.encyclopedia_build --with-alchemy
    D:\\anaconda\\python.exe -X utf8 -m tools.encyclopedia_build --with-world-setting
    python -m tools.town_art_elements
    python -m tools.encyclopedia_build --with-town-buildings

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
* 奇幻生物分区（种族／西幻动植物／东方玄幻动植物）是**另一份独立名单**
  ``FANTASY_BIOLOGY_GROUPS``：只有显式传 ``--with-fantasy-biology`` 才构入，
  可与上面任何开关组合。三份文件由采集侧定稿、条数会变，本文件**不写死它们的条数**；
  种族／兽／草木的区分靠条目自带的 ``kind:race`` / ``kind:fauna`` / ``kind:flora``
  与 ``tradition:*`` 标签做检索，引擎不读标签做判定。
* 魔药／丹药分区（西幻魔药／东方丹药）是 ``FANTASY_ALCHEMY_GROUPS``：同样只有显式传
  ``--with-alchemy`` 才构入，与 ``--with-fantasy-biology`` **互不隐含**（只要生物不自动带药，
  反之亦然）。它们是游戏与小说素材，**不是任何现实用药依据**，也不含配方剂量。
* 世界设定素材分区（国家与政体模板 / 补充种族 / 蒸汽与近现代技术）是 ``WORLD_SETTING_GROUPS``：
  只有显式传 ``--with-world-setting`` 才构入，与其他开关互不隐含。条目带 ``kind:polity``、
  ``polity:*``、``tech:*``、``magic:*`` 标签（定义见 ``docs/world-setting.md``），均为待审候选。
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
from tools import game_fields  # noqa: E402
from tools import catalog_overlay  # noqa: E402
from tools import affix_fields  # noqa: E402

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
    'docs/element-catalog/poetry-forms.json',
    'docs/element-catalog/poetry-classics.json',
    'docs/element-catalog/professions-bard.json',
    'docs/element-catalog/myth-greco-roman.json',
    'docs/element-catalog/myth-chinese-taoist.json',
    'docs/element-catalog/religions.json',
)
ATTRIBUTE_GROUPS = (
    'docs/playable-demo/character-attributes.json',
)
# 奇幻生物分区（种族 / 西幻动植物 / 东方玄幻动植物）也是独立名单：
# 默认不进库，只有 ``--with-fantasy-biology`` 才构入。三份文件由采集侧逐条定稿，
# 条数会变，所以这里同样不写死任何数字，也不靠 ``docs/element-catalog/*.json`` 通配——
# 同目录还有 shared-themes（聚类索引）与后续候选文件，通配会把它们默默带进交付库。
# 顺序固定为「... → 种族 → 西幻生物 → 东方生物」，不与其他名单交错。
FANTASY_BIOLOGY_GROUPS = (
    'docs/element-catalog/fantasy-races.json',
    'docs/element-catalog/western-biology.json',
    'docs/element-catalog/eastern-biology.json',
)
# 魔药／丹药分区：同样独立名单，只有 ``--with-alchemy`` 才构入。
# 与奇幻生物分组但互不隐含：只要生物不自动带药，反之亦然。
# 内容仍待审候选，不构成任何现实用药依据。
FANTASY_ALCHEMY_GROUPS = (
    'docs/element-catalog/western-alchemy.json',
    'docs/element-catalog/eastern-alchemy.json',
)
# 现实药材、方剂与西方菜系分区：同样逐文件显式登记，不用通配。
# 药材与方剂是**文献与设定资料**，不含剂量与处方，不构成医疗建议；
# 已与其他组重合的条目已在源文件里除出（见 tools/encyclopedia_merge）：
# 它们的补充内容并入了原有元素，所以这里的文件条数是归并后的结果。
REALITY_HERBS_GROUPS = (
    'docs/element-catalog/reality-herbs-roots.json',
    'docs/element-catalog/reality-herbs-aerial.json',
    'docs/element-catalog/reality-herbs-other.json',
    'docs/element-catalog/reality-herbs-western.json',
)
FORMULA_GROUPS = (
    'docs/element-catalog/reality-formulae.json',
)
CUISINE_WESTERN_GROUPS = (
    'docs/element-catalog/cuisine-french.json',
    'docs/element-catalog/cuisine-british.json',
)
# 世界设定素材分区：同样逐文件显式登记、不用通配，只有 ``--with-world-setting`` 才构入。
# 条数由采集侧定稿，这里不写死。
WORLD_SETTING_GROUPS = (
    'docs/element-catalog/polities.json',
    'docs/element-catalog/races-supplement.json',
    'docs/element-catalog/steam-tech.json',
    'docs/element-catalog/era-tech.json',
    'docs/element-catalog/polities-extra.json',
)
# 世界各地菜系分区（中餐 / 欧陆 / 拉美）：只有 ``--with-cuisine-world`` 才构入，逐文件登记。
# 欧陆与拉美采集完成后再追加到这里，避免缺文件导致构库失败。
CUISINE_WORLD_GROUPS = (
    'docs/element-catalog/cuisine-chinese.json',
    'docs/element-catalog/cuisine-european.json',
    'docs/element-catalog/cuisine-latin-american.json',
)
# 店铺分区：只有 ``--with-shops`` 才构入。shop.key 与 game.sold_by 词表一一对应（见 shops-spec.md）。
SHOP_GROUPS = (
    'docs/element-catalog/shops.json',
)
# 城镇美术候选分区：只有 --with-town-buildings 才构入，不隐含其他开关。
TOWN_BUILDING_GROUPS = (
    'docs/human-encyclopedia/town-buildings.json',
)
# 职业分区（现实与历史职业 / 奇幻职业）：只有 ``--with-professions`` 才构入。
# profession.shop_key 与 game.sold_by 店铺键对应（见 docs/element-catalog/professions-spec.md）。
PROFESSION_GROUPS = (
    'docs/element-catalog/professions.json',
    'docs/element-catalog/professions-fantasy.json',
)
# 文明模拟用的王朝风格 / 人名用字：只有 ``--with-civ-lore`` 才构入。
# 宗教本体仍走 ``--with-culture`` 里的 religions.json；本组不重复教义条目。
CIV_LORE_GROUPS = (
    'docs/human-encyclopedia/civ-dynasty-styles.json',
    'docs/human-encyclopedia/civ-given-names.json',
)
# 词条分区（西幻 / 游戏常见的人物与物品词条，affix_fields_v1）：只有 ``--with-affixes`` 才构入。
# 与 character-traits（行为特质、不承担数值）是两回事，详见 docs/element-catalog/affixes-spec.md。
AFFIX_GROUPS = (
    'docs/element-catalog/fantasy-affixes.json',
)
# 带特质的历史基线（旧交付口径）；不带任何开关时仍是 ``GROUPS``。
LATEST_GROUPS = GROUPS + TRAIT_GROUPS


def groups_for(with_traits=False, with_cuisine=False, with_attributes=False, with_culture=False,
               with_fantasy_biology=False, with_alchemy=False, with_reality_herbs=False,
               with_formulae=False, with_cuisine_western=False, with_world_setting=False,
               with_cuisine_world=False, with_shops=False, with_town_buildings=False,
               with_professions=False, with_civ_lore=False, with_affixes=False):
    """要构库的显式名单。

    不给开关 = 历史 14 组。with_attributes 显式追加现有六项属性资料。
    给了哪个就追加哪个分区；都给了时顺序是
    「14 组 → 特质 → 饮食 → 属性 → 文化 → 种族 → 西幻生物 → 东方生物 → 西幻魔药 → 东方丹药」。
    默认值保持向后兼容：旧调用 ``groups_for(False)`` / ``groups_for(True)`` /
    ``groups_for(True, True, True)`` / ``groups_for(with_culture=True)`` 行为全部不变；
    新参数追加在末尾且默认为 False，因此旧的**位置传参**也不会被改变含义。
    """
    groups = LATEST_GROUPS if with_traits else GROUPS
    if with_cuisine:
        groups = groups + CUISINE_GROUPS
    if with_attributes:
        groups = groups + ATTRIBUTE_GROUPS
    if with_culture:
        groups = groups + CULTURE_GROUPS
    if with_fantasy_biology:
        groups = groups + FANTASY_BIOLOGY_GROUPS
    if with_alchemy:
        groups = groups + FANTASY_ALCHEMY_GROUPS
    if with_reality_herbs:
        groups = groups + REALITY_HERBS_GROUPS
    if with_formulae:
        groups = groups + FORMULA_GROUPS
    if with_cuisine_western:
        groups = groups + CUISINE_WESTERN_GROUPS
    if with_world_setting:
        groups = groups + WORLD_SETTING_GROUPS
    if with_cuisine_world:
        groups = groups + CUISINE_WORLD_GROUPS
    if with_shops:
        groups = groups + SHOP_GROUPS
    if with_town_buildings:
        groups = groups + TOWN_BUILDING_GROUPS
    if with_professions:
        groups = groups + PROFESSION_GROUPS
    if with_civ_lore:
        groups = groups + CIV_LORE_GROUPS
    if with_affixes:
        groups = groups + AFFIX_GROUPS
    return groups


# 全部开关一次打开（校验工具用；按关键字传，新增开关不会错位）。
ALL_FLAGS = {name: True for name in (
    'with_traits', 'with_cuisine', 'with_attributes', 'with_culture', 'with_fantasy_biology',
    'with_alchemy', 'with_reality_herbs', 'with_formulae', 'with_cuisine_western',
    'with_world_setting', 'with_cuisine_world', 'with_shops', 'with_town_buildings',
    'with_professions', 'with_civ_lore', 'with_affixes')}


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
        # 先在内存里叠加 game 旁挂字段（docs/element-catalog/game-fields/<group>.json）；
        # 没有旁挂文件、元素也不带 game 时文档原样导入，内容哈希不变。源 JSON 从不改写。
        text = (ROOT / relative).read_bytes().decode('utf-8')
        document = game_fields.overlay(enc.loads_json(text))
        # 再叠加主标签 / 证据等级 / 补充关联（docs/element-catalog/overlays/<group>.json）；同样只在内存。
        document = catalog_overlay.overlay(document)
        # 词条字段（affix_fields_v1）：字段不合规、或 affix: 标签与对象不一致，整批拒绝。
        affix_fields.check_document(document)
        result = enc.import_document(out, document)
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
        description='按显式名单（默认 14 组；可选 --with-traits / --with-cuisine / --with-attributes'
                    ' / --with-culture / --with-fantasy-biology）'
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
    parser.add_argument('--with-fantasy-biology', action='store_true',
                        help='追加奇幻生物分区（种族 / 西幻动植物 / 东方玄幻动植物，3 个显式分区）；'
                             '可与上面任何开关组合')
    parser.add_argument('--with-alchemy', action='store_true',
                        help='追加魔药分区（西幻魔药 / 东方丹药，2 个显式分区）；'
                             '与 --with-fantasy-biology 独立，不互相隐含')
    parser.add_argument('--with-reality-herbs', action='store_true', dest='with_reality_herbs',
                        help='追加现实药材分区（根茎 / 茎叶花果实 / 皮木菌矿物动物 / 西方草药，4 个显式分区）；'
                             '为文献与设定资料，不构成医疗建议')
    parser.add_argument('--with-formulae', action='store_true',
                        help='追加现实经典方剂分区（只录药味名称与出处，不含剂量与服法）')
    parser.add_argument('--with-cuisine-western', action='store_true', dest='with_cuisine_western',
                        help='追加西方菜系分区（法餐 / 英国菜）')
    parser.add_argument('--with-world-setting', action='store_true', dest='with_world_setting',
                        help='追加世界设定素材分区（国家与政体模板 / 补充种族 / 蒸汽与近现代技术，3 个显式分区）')
    parser.add_argument('--with-cuisine-world', action='store_true', dest='with_cuisine_world',
                        help='追加世界各地菜系分区（中餐 / 欧陆 / 拉美）')
    parser.add_argument('--with-shops', action='store_true', dest='with_shops',
                        help='追加店铺分区（铁匠铺、盔甲铺、药铺等，与 sold_by 词表对应）')
    parser.add_argument('--with-town-buildings', action='store_true',
                        help='追加城镇建筑美术候选分区；先运行 python -m tools.town_art_elements；与其他开关独立')
    parser.add_argument('--with-professions', action='store_true', dest='with_professions',
                        help='追加职业分区（现实与历史职业 / 奇幻职业，2 个显式分区）')
    parser.add_argument('--with-civ-lore', action='store_true', dest='with_civ_lore',
                        help='追加文明模拟用王朝命名风格与人名用字（2 个显式分区）；'
                             '宗教本体仍用 --with-culture 中的 religions')
    parser.add_argument('--with-affixes', action='store_true', dest='with_affixes',
                        help='追加词条分区（西幻 / 游戏常见的人物与物品词条，affix_fields_v1）；'
                             '数值是候选设计口径，不改角色属性、不改奖励配置')
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    groups = groups_for(args.with_traits, args.with_cuisine, args.with_attributes, args.with_culture,
                        args.with_fantasy_biology, args.with_alchemy, args.with_reality_herbs,
                        args.with_formulae, args.with_cuisine_western, args.with_world_setting,
                        args.with_cuisine_world, args.with_shops, args.with_town_buildings,
                        args.with_professions, args.with_civ_lore, args.with_affixes)
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
