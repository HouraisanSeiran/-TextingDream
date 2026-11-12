# -*- coding: utf-8 -*-
"""元素主标签 / 证据等级 / 补充关联的旁挂叠加（catalog_overlay_v1）。

规范见 ``docs/element-catalog/primary-tags-spec.md``。

* 每个元素**恰好一个主标签** ``primary``（取自 :data:`PRIMARY`），其余标签都是次标签。
  例：白菜 primary=vegetable，次标签有 crop、food、season:winter……
* ``evidence_grade``：sourced / mixed / inferred，区分「有已读来源」与「本项目推演」。
* ``related_add``：补充关联（如方剂 → 药材），追加到 ``related_catalog_ids``，不删已有关联。

旁挂文件 ``docs/element-catalog/overlays/<group>.json``；构库时 :func:`overlay` 在内存里写入
``primary`` / ``evidence_grade`` 字段（引擎据此派生 ``primary:`` / ``evidence:`` 标签，旧 schema
也能拿到），源 JSON 永不改写。指向不存在的元素、主标签不在词表、缺覆盖都直接报错。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OVERLAY_DIR = 'docs/element-catalog/overlays'
SCHEMA = 'catalog_overlay_v1'
EVIDENCE_GRADES = ('sourced', 'mixed', 'inferred')
TECH_TIERS = ('classical', 'medieval', 'renaissance', 'steam', 'early_modern')
MAGIC_TIERS = ('none', 'rare', 'common', 'abundant')
# 可经 genres_add 追加的类型（与 app/world_setting.GENRES 键一致）。
GENRES = ('western_fantasy', 'dark_fantasy', 'eastern_fantasy', 'xianxia', 'steampunk',
          'historical', 'real_world', 'modern', 'folk_horror')

# 主标签词表：键 → 中文名。按大类分组只是为了读，标签本身是扁平的。
PRIMARY = {
    # 食物原料
    'grain': '谷物', 'legume': '豆类', 'root_tuber': '薯芋根茎', 'vegetable': '蔬菜',
    'fruit': '水果', 'nut_seed': '坚果籽实', 'oil_crop': '油料', 'mushroom': '食用菌',
    'spice': '香料', 'culinary_herb': '香草', 'condiment': '调味品', 'sweetener': '糖与甜味',
    'beverage': '饮品', 'alcohol': '酒类',
    'livestock': '牲畜', 'meat': '肉类', 'poultry': '禽类', 'seafood': '水产',
    'dairy': '乳品', 'egg': '蛋类', 'preserved_food': '腌熏保存食品',
    # 成品食物
    'dish': '菜肴', 'soup': '汤羹', 'bread': '面包', 'pastry': '糕点酥点', 'snack': '小吃点心',
    'noodle': '面食', 'sauce': '酱汁', 'cooking_technique': '烹饪技法',
    # 药
    'medicinal_herb': '药材（植物）', 'medicinal_mineral': '药材（矿物）',
    'medicinal_animal': '药材（动物）', 'formula': '方剂',
    'potion': '魔药', 'elixir_pill': '丹药',
    # 材料与器物
    'ore': '矿石', 'metal': '金属', 'stone_earth': '石料与土', 'fuel': '燃料',
    'building_material': '建材', 'glass_ceramic': '玻璃陶瓷', 'timber': '木材',
    'fiber_textile': '纤维织物', 'hide_leather': '皮革骨角', 'tool': '工具',
    'weapon': '兵器', 'armor': '甲胄', 'vehicle_vessel': '车船',
    'artifact': '法宝与神器', 'magic_material': '灵材与奇异材料',
    'facility': '设施（粮仓、水井、磨坊、锻炉等固定设施）', 'fat_oil': '食用油脂',
    # 生灵
    'race': '种族', 'beast': '动物（含奇幻兽）', 'plant': '植物（非食用为主）', 'spirit': '精怪',
    'undead_demon': '亡灵与魔物',
    # 力量、知识与社会
    'magic_power': '法术与超凡力量', 'technology': '技术', 'craft_process': '工艺流程',
    'institution': '制度', 'organization': '组织', 'profession': '职业',
    'belief_ritual': '信仰与仪式', 'economy_trade': '经济与贸易', 'conflict_event': '冲突与事件',
    'place': '地点与地貌', 'natural_phenomenon': '自然现象',
    'character_trait': '性格特质', 'character_attribute': '角色属性',
    'affix': '词条（人物 / 物品的增益与减益）',
    'literature_form': '文学与叙事', 'name_pool': '姓名池',
    'shop': '店铺',
}


class OverlayError(ValueError):
    """叠加文件不合规。消息里点名分组与元素 id。"""


def overlay_path(group, root=None):
    return Path(root or ROOT) / OVERLAY_DIR / (group + '.json')


def load_overlay(group, root=None):
    path = overlay_path(group, root)
    if not path.is_file():
        return None
    document = json.loads(path.read_text(encoding='utf-8-sig'))
    if document.get('schema') != SCHEMA or document.get('group') != group:
        raise OverlayError('%s：叠加文件 schema/group 不符' % path.name)
    entries = document.get('entries')
    if not isinstance(entries, dict) or not entries:
        raise OverlayError('%s：entries 必须是非空对象' % path.name)
    return entries


def validate_entry(entry, element_id):
    if not isinstance(entry, dict):
        raise OverlayError('%s：叠加条目必须是对象' % element_id)
    extra = set(entry) - {'primary', 'evidence_grade', 'related_add', 'note', 'tech_tier', 'magic_tier',
                          'genres_add'}
    if extra:
        raise OverlayError('%s：未定义字段 %s' % (element_id, sorted(extra)))
    if entry.get('primary') not in PRIMARY:
        raise OverlayError('%s：primary %r 不在主标签词表' % (element_id, entry.get('primary')))
    if entry.get('evidence_grade') not in EVIDENCE_GRADES:
        raise OverlayError('%s：evidence_grade %r 非法' % (element_id, entry.get('evidence_grade')))
    related = entry.get('related_add', [])
    if not isinstance(related, list) or not all(isinstance(item, str) and item for item in related):
        raise OverlayError('%s：related_add 必须是 id 字符串数组' % element_id)
    if len(set(related)) != len(related):
        raise OverlayError('%s：related_add 有重复' % element_id)
    for field, vocab in (('tech_tier', TECH_TIERS), ('magic_tier', MAGIC_TIERS)):
        if field in entry and entry[field] is not None and entry[field] not in vocab:
            raise OverlayError('%s：%s %r 不在档位词表' % (element_id, field, entry[field]))
    genres = entry.get('genres_add', [])
    if not isinstance(genres, list) or len(set(genres)) != len(genres) \
            or any(g not in GENRES for g in genres):
        raise OverlayError('%s：genres_add 必须是不重复的类型词表取值' % element_id)


def has_tiers(entry):
    """档位是否已判定：两个键都在（值可为 null，表示不受该档位约束）。"""
    return 'tech_tier' in entry and 'magic_tier' in entry


def overlay(document, root=None):
    """把叠加字段写进文档副本。没有叠加文件就原样返回；元素自带 primary 的只校验词表。"""
    group = document.get('group')
    elements = document.get('elements') or []
    entries = load_overlay(group, root) if group else None
    if entries is None:
        for element in elements:
            if 'primary' in element and element['primary'] not in PRIMARY:
                raise OverlayError('%s：primary %r 不在主标签词表' % (element.get('id'), element['primary']))
        return document
    ids = [element.get('id') for element in elements]
    unknown = sorted(set(entries) - set(ids))
    if unknown:
        raise OverlayError('%s 叠加文件指向不存在的元素：%s' % (group, unknown))
    missing = [element_id for element_id in ids if element_id not in entries]
    if missing:
        raise OverlayError('%s 叠加文件未覆盖全部元素，缺：%s' % (group, missing))
    merged = dict(document)
    merged['elements'] = []
    for element in elements:
        entry = entries[element['id']]
        validate_entry(entry, element['id'])
        if 'primary' in element and element['primary'] != entry['primary']:
            raise OverlayError('%s：元素自带 primary 与叠加文件冲突' % element['id'])
        copy = dict(element)
        copy['primary'] = entry['primary']
        copy['evidence_grade'] = entry['evidence_grade']
        for field in ('tech_tier', 'magic_tier'):
            if field in entry:
                if field in element and element[field] != entry[field]:
                    raise OverlayError('%s：元素自带 %s 与叠加文件冲突' % (element['id'], field))
                if entry[field] is not None:
                    copy[field] = entry[field]
        # 类型追加：并到元素自己的 genres，引擎据此派生 genre: 标签（旧 schema 也生效）。
        genres_add = entry.get('genres_add') or []
        if genres_add:
            existing = list(element.get('genres') or [])
            copy['genres'] = existing + [g for g in genres_add if g not in existing]
        related = entry.get('related_add') or []
        if related:
            existing = list(element.get('related_catalog_ids') or [])
            if element['id'] in related:
                raise OverlayError('%s：related_add 不能指向自己' % element['id'])
            copy['related_catalog_ids'] = existing + [item for item in related if item not in existing]
        merged['elements'].append(copy)
    return merged


def main(argv=None):
    parser = argparse.ArgumentParser(prog='catalog_overlay', description='校验 catalog_overlay_v1')
    parser.add_argument('--check', action='store_true', help='校验全部构库分区的叠加文件')
    parser.add_argument('--require-tiers', action='store_true',
                        help='同时要求每个元素都已判定科技 / 魔法档位（tech_tier / magic_tier 两键齐全，值可为 null）')
    args = parser.parse_args(argv)
    if not args.check:
        parser.print_help()
        return 0
    from tools import encyclopedia_build as build
    from tools import game_fields
    rows, problems = [], []
    for relative in build.groups_for(**build.ALL_FLAGS):
        document = json.loads((ROOT / relative).read_text(encoding='utf-8-sig'))
        try:
            merged = overlay(game_fields.overlay(document))
        except (OverlayError, ValueError) as error:
            problems.append('%s：%s' % (relative, error))
            continue
        elements = merged.get('elements') or []
        entries = load_overlay(document.get('group')) or {}
        # 已判定档位：叠加文件两键齐全，或新分区元素自带两键（值可为 null）。
        def judged(e):
            return has_tiers(entries.get(e.get('id'), {})) or has_tiers(e)
        tiered = sum(1 for e in elements if judged(e))
        rows.append((merged.get('group'), sum(1 for e in elements if 'primary' in e), tiered, len(elements)))
        if args.require_tiers and tiered != len(elements):
            missing = [e.get('id') for e in elements if not judged(e)]
            problems.append('%s：%d 条未判定档位，如 %s' % (relative, len(missing), missing[:3]))
    for group, with_primary, tiered, total in rows:
        sys.stdout.write('%-24s primary %3d / %3d   tiers %3d / %3d\n'
                         % (group, with_primary, total, tiered, total))
    if problems:
        sys.stderr.write('叠加校验失败：\n  ' + '\n  '.join(problems) + '\n')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
