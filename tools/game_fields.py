# -*- coding: utf-8 -*-
"""游戏字段 game_fields_v1（价格 / 产地 / 季节 / 保存期 / 谁在卖）的校验与构库叠加。

规范见 ``docs/element-catalog/game-fields-spec.md``。两条入口：

* 新建分区：元素自带 ``game`` 对象与对应标签，构库时只校验。
* 已有分区：不改写源 JSON（各文件换行与缩进不一，整文件重写会产生无法审阅的 diff），
  而是在 ``docs/element-catalog/game-fields/<group>.json`` 写旁挂文件；构库时
  :func:`overlay` 把它叠加到内存里的文档上（写入 ``game`` 并补标签），再交给引擎导入。

叠加只发生在内存，源 JSON 永远不被改写。旁挂条目指向不存在的元素 id、字段取值不在
词表里、标签与 ``game`` 不一致，都会直接报错，不静默跳过。

命令行：``python -X utf8 -m tools.game_fields --check`` 校验全部旁挂文件与自带 game 的分区。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIDECAR_DIR = 'docs/element-catalog/game-fields'
SCHEMA = 'game_fields_v1'

PRICE_TIERS = ('farthing', 'penny', 'groat', 'shilling', 'pound', 'not_for_sale', 'priceless')
TERRAINS = (
    'ocean', 'lake', 'tundra', 'taiga', 'cold_desert', 'temperate_desert', 'steppe',
    'temperate_forest', 'temperate_rainforest', 'hot_desert', 'savanna',
    'tropical_dry_forest', 'rainforest', 'wetland',
    'mountain', 'plateau', 'coast', 'river',
    'farmland', 'orchard', 'pasture', 'mine', 'workshop', 'import',
)
SEASONS = ('spring', 'summer', 'autumn', 'winter', 'all_year')
KEEPS = ('hours', 'days', 'weeks', 'months', 'years')
# 谁在卖：键与店铺分区（docs/element-catalog/shops.json）的 shop.key 一一对应（'none' 除外）。
SOLD_BY = (
    # 食物与日用
    'tavern', 'inn_kitchen', 'market', 'grocer', 'greengrocer', 'butcher', 'fishmonger', 'baker',
    'confectioner', 'cookshop', 'dairy', 'miller', 'brewer', 'wine_merchant', 'tea_house',
    'chandler', 'spice_merchant',
    # 药与采集
    'apothecary', 'herbalist', 'alchemist',
    # 手工与装备
    'blacksmith', 'armorer', 'weaponsmith', 'bowyer', 'carpenter', 'cooper', 'tanner', 'saddler',
    'tailor', 'draper', 'cobbler', 'potter', 'jeweler',
    # 金融、书籍、车马
    'moneychanger', 'pawnshop', 'bookseller', 'stable',
    # 非店铺卖家
    'farmer', 'noble_kitchen', 'street_vendor',
    'none',
)
# 限售原因：只做标注，是否真的禁售由世界选项决定（见 is_for_sale）。中世纪基线默认全部可售。
RESTRICTIONS = (
    'protected_wild',        # 野生受保护（现实中）
    'endangered_animal',     # 濒危动物制品（现实中禁止交易）
    'controlled_substance',  # 管制或成瘾物
    'toxic',                 # 剧毒，只宜药铺凭方配售
    'cultural_relic',        # 文物
)
TAG_PREFIXES = ('price:', 'terrain:', 'season:', 'sold_by:', 'restriction:')
NO_PRICE_TIERS = ('not_for_sale', 'priceless')


class GameFieldError(ValueError):
    """game 字段不合规。消息里点名元素 id 与出错字段。"""


def tier_for(max_pence):
    """按 max 便士推 tier（规范 §2）。"""
    if max_pence < 1:
        return 'farthing'
    if max_pence <= 3:
        return 'penny'
    if max_pence <= 11:
        return 'groat'
    if max_pence <= 239:
        return 'shilling'
    return 'pound'


def _list(value, vocab, name, element_id, lo, hi):
    if not isinstance(value, list) or not (lo <= len(value) <= hi):
        raise GameFieldError('%s：%s 必须是 %d–%d 项的数组' % (element_id, name, lo, hi))
    if len(set(value)) != len(value):
        raise GameFieldError('%s：%s 有重复值' % (element_id, name))
    bad = [item for item in value if item not in vocab]
    if bad:
        raise GameFieldError('%s：%s 有词表外取值 %s' % (element_id, name, bad))
    return value


def validate_game(game, element_id):
    """校验一个 game 对象（不含标签）。返回该对象应有的标签列表。"""
    if not isinstance(game, dict):
        raise GameFieldError('%s：game 必须是对象' % element_id)
    allowed = {'schema', 'price', 'terrains', 'seasons', 'keeps', 'sold_by', 'note', 'restriction'}
    extra = set(game) - allowed
    if extra:
        raise GameFieldError('%s：game 有未定义字段 %s' % (element_id, sorted(extra)))
    if game.get('schema', SCHEMA) != SCHEMA:
        raise GameFieldError('%s：schema 必须是 %s' % (element_id, SCHEMA))
    price = game.get('price')
    if not isinstance(price, dict):
        raise GameFieldError('%s：price 必须是对象' % element_id)
    tier = price.get('tier')
    if tier not in PRICE_TIERS:
        raise GameFieldError('%s：price.tier 非法 %r' % (element_id, tier))
    low, high = price.get('min'), price.get('max')
    if tier in NO_PRICE_TIERS:
        if low is not None or high is not None:
            raise GameFieldError('%s：%s 的 min/max 必须为 null' % (element_id, tier))
    else:
        for label, value in (('min', low), ('max', high)):
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise GameFieldError('%s：price.%s 必须是非负整数便士' % (element_id, label))
        if low > high:
            raise GameFieldError('%s：price.min 大于 max' % element_id)
        if tier_for(high) != tier:
            raise GameFieldError('%s：max=%d 便士应为 %s，写成了 %s'
                                 % (element_id, high, tier_for(high), tier))
    per = price.get('per')
    if tier not in NO_PRICE_TIERS and (not isinstance(per, str) or not per.strip()):
        raise GameFieldError('%s：price.per 不能为空' % element_id)
    terrains = _list(game.get('terrains'), TERRAINS, 'terrains', element_id, 1, 3)
    seasons = _list(game.get('seasons'), SEASONS, 'seasons', element_id, 1, 4)
    if 'all_year' in seasons and len(seasons) > 1:
        raise GameFieldError('%s：all_year 不能与四季混用' % element_id)
    if game.get('keeps') not in KEEPS:
        raise GameFieldError('%s：keeps 非法 %r' % (element_id, game.get('keeps')))
    sold_by = _list(game.get('sold_by'), SOLD_BY, 'sold_by', element_id, 1, 3)
    if 'none' in sold_by and len(sold_by) > 1:
        raise GameFieldError('%s：sold_by 含 none 时只能单独出现' % element_id)
    if tier == 'not_for_sale' and sold_by != ['none']:
        raise GameFieldError('%s：not_for_sale 的 sold_by 只能是 ["none"]' % element_id)
    note = game.get('note', '')
    if not isinstance(note, str):
        raise GameFieldError('%s：note 必须是字符串' % element_id)
    restriction = game.get('restriction')
    if restriction is not None and restriction not in RESTRICTIONS:
        raise GameFieldError('%s：restriction 非法 %r' % (element_id, restriction))
    tags = (['price:' + tier] + ['terrain:' + item for item in terrains]
            + ['season:' + item for item in seasons] + ['sold_by:' + item for item in sold_by])
    if restriction is not None:
        tags.append('restriction:' + restriction)
    return tags


def is_for_sale(game, banned_restrictions=()):
    """按世界选项判断能否合法买卖。

    ``banned_restrictions`` 是开局时作者选定要禁售的限售原因（如 ``{'endangered_animal'}``）；
    默认空集合 = 中世纪基线，标了限售原因的东西照样有价可买。
    ``not_for_sale`` / ``priceless`` 两档在任何选项下都不可买。
    """
    tier = (game.get('price') or {}).get('tier')
    if tier in NO_PRICE_TIERS:
        return False
    banned = set(banned_restrictions or ())
    unknown = banned - set(RESTRICTIONS)
    if unknown:
        raise GameFieldError('未知的限售原因：%s' % sorted(unknown))
    return game.get('restriction') not in banned


def check_element_tags(element):
    """自带 game 的元素：标签里的四类前缀必须与 game 推出的完全一致。"""
    element_id = element.get('id')
    expected = validate_game(element['game'], element_id)
    actual = [tag for tag in element.get('tags') or [] if tag.startswith(TAG_PREFIXES)]
    if sorted(actual) != sorted(expected):
        raise GameFieldError('%s：game 标签不一致，应为 %s，实际 %s'
                             % (element_id, sorted(expected), sorted(actual)))


def sidecar_path(group, root=None):
    return Path(root or ROOT) / SIDECAR_DIR / (group + '.json')


def load_sidecar(group, root=None):
    path = sidecar_path(group, root)
    if not path.is_file():
        return None
    document = json.loads(path.read_text(encoding='utf-8-sig'))
    if document.get('schema') != SCHEMA or document.get('group') != group:
        raise GameFieldError('%s：旁挂文件 schema/group 不符' % path.name)
    entries = document.get('entries')
    if not isinstance(entries, dict) or not entries:
        raise GameFieldError('%s：entries 必须是非空对象' % path.name)
    return entries


def overlay(document, root=None):
    """把旁挂 game 字段叠加到文档（返回新对象，不改入参）。没有旁挂文件就原样返回校验结果。"""
    group = document.get('group')
    elements = document.get('elements') or []
    entries = load_sidecar(group, root) if group else None
    if entries is None:
        for element in elements:
            if 'game' in element:
                check_element_tags(element)
        return document
    ids = [element.get('id') for element in elements]
    unknown = sorted(set(entries) - set(ids))
    if unknown:
        raise GameFieldError('%s 旁挂文件指向不存在的元素：%s' % (group, unknown))
    missing = [element_id for element_id in ids if element_id not in entries]
    if missing:
        raise GameFieldError('%s 旁挂文件未覆盖全部元素，缺：%s' % (group, missing))
    merged = dict(document)
    merged['elements'] = []
    for element in elements:
        if 'game' in element:
            raise GameFieldError('%s：元素已自带 game，不能再用旁挂文件' % element.get('id'))
        game = dict(entries[element['id']])
        game['schema'] = SCHEMA
        new_tags = validate_game(game, element['id'])
        copy = dict(element)
        copy['game'] = game
        # 旧 schema（元素没有 tags）引擎会丢弃原生标签，这里只写 game 不加标签。
        if 'tags' in element:
            kept = [tag for tag in element.get('tags') or [] if not tag.startswith(TAG_PREFIXES)]
            copy['tags'] = kept + new_tags
        merged['elements'].append(copy)
    return merged


def check_all(files, root=None):
    """校验一批源文件（含旁挂）。返回 (分组, 有 game 的条数, 总条数) 列表。"""
    rows = []
    for relative in files:
        document = json.loads((Path(root or ROOT) / relative).read_text(encoding='utf-8-sig'))
        merged = overlay(document, root)
        elements = merged.get('elements') or []
        rows.append((merged.get('group'), sum(1 for e in elements if 'game' in e), len(elements)))
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(prog='game_fields', description='校验 game_fields_v1')
    parser.add_argument('--check', action='store_true', help='校验全部构库分区的 game 字段')
    args = parser.parse_args(argv)
    from tools import encyclopedia_build as build
    files = build.groups_for(**build.ALL_FLAGS) if args.check else ()
    try:
        rows = check_all(files)
    except (GameFieldError, ValueError) as error:
        sys.stderr.write('game 字段校验失败：%s\n' % error)
        return 1
    for group, with_game, total in rows:
        if with_game:
            sys.stdout.write('%-24s game %3d / %3d\n' % (group, with_game, total))
    return 0


if __name__ == '__main__':
    sys.exit(main())
