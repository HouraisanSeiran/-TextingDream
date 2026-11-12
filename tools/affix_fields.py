# -*- coding: utf-8 -*-
"""词条字段 affix_fields_v1（人物 / 物品词条）的校验与标签派生。

规范见 ``docs/element-catalog/affixes-spec.md``。本模块只校验，**不应用**：

* 词条数值不改角色属性、不改 ``mechanics.rewards``、不进检定公式。作者要让它在世界里
  生效，必须自己把等价内容写进故事包（角色包的 ``attributes``、奖励配置的材质与附魔）。
* 不做「词条等级 / 成长」推算，也不把 ``narrative`` 里的自然语言当机器规则。

``attribute_mods`` 的键只能是 ``app.attributes.AXES`` 那六项；写别的名字（charisma、
intelligence……）会造出平行属性体系，一律拒绝。幅度上限按 ``grade`` 分档，只为拦住
明显跑偏的值（0–100 量程上写 +60 力量），不是平衡实测结论。

命令行：``python -X utf8 -m tools.affix_fields --check`` 校验全部构库分区里带 ``affix`` 的元素。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.attributes import AXES  # noqa: E402

SCHEMA = 'affix_fields_v1'
APPLIES_TO = ('character', 'item')
POLARITIES = ('boon', 'bane', 'mixed')
GRADES = ('common', 'uncommon', 'rare', 'legendary')
STACKINGS = ('unique', 'stack', 'exclusive')
VISIBILITIES = ('public', 'hidden')
TAG_PREFIX = 'affix:'

# 幅度上限（规范 §5）：单轴属性、属性绝对值合计、血量、物品伤害、百分比相对 100 的偏移。
GRADE_CAPS = {
    'common': {'axis': 6, 'sum': 10, 'hp': 10, 'damage': 3, 'percent': 30},
    'uncommon': {'axis': 10, 'sum': 18, 'hp': 20, 'damage': 6, 'percent': 60},
    'rare': {'axis': 15, 'sum': 26, 'hp': 35, 'damage': 10, 'percent': 120},
    'legendary': {'axis': 20, 'sum': 34, 'hp': 50, 'damage': 15, 'percent': 200},
}
# 与 app/rewards.py 的 Material / Enchantment 字段同量程，方便作者原样抄进奖励配置。
ITEM_RANGES = {
    'damage': (-50, 50),
    'value_percent': (10, 1000),
    'weight_percent': (10, 1000),
    'durability_percent': (25, 500),
}
ALLOWED_KEYS = {'schema', 'applies_to', 'polarity', 'grade', 'stacking', 'exclusive_group',
                'visibility', 'attribute_mods', 'hp_mod', 'item_mods', 'narrative', 'note'}
ID_RE = re.compile(r'^[a-z][a-z0-9_.:-]*$')
MAX_NARRATIVE = 3
MAX_NARRATIVE_CHARS = 60
MAX_NOTE_CHARS = 120


class AffixFieldError(ValueError):
    """``affix`` 对象不合规。消息里点名元素 id 与出错字段。"""


def _int(value, label):
    if isinstance(value, bool) or not isinstance(value, int):
        raise AffixFieldError('%s 必须是整数（布尔与文本不接受）' % label)
    return value


def _keys(value, allowed, label, element_id, lo, hi):
    if not isinstance(value, dict):
        raise AffixFieldError('%s：%s 必须是对象' % (element_id, label))
    extra = set(value) - set(allowed)
    if extra:
        raise AffixFieldError('%s：%s 有未定义字段 %s' % (element_id, label, sorted(extra)))
    if not lo <= len(value) <= hi:
        raise AffixFieldError('%s：%s 需要 %d–%d 项' % (element_id, label, lo, hi))
    return value


def validate_affix(affix, element_id):
    """校验一个 ``affix`` 对象。返回该对象应有的 ``affix:`` 标签列表（已排序）。"""
    if not isinstance(affix, dict):
        raise AffixFieldError('%s：affix 必须是对象' % element_id)
    extra = set(affix) - ALLOWED_KEYS
    if extra:
        raise AffixFieldError('%s：affix 有未定义字段 %s' % (element_id, sorted(extra)))
    if affix.get('schema') != SCHEMA:
        raise AffixFieldError('%s：schema 必须是 %s' % (element_id, SCHEMA))

    applies_to = affix.get('applies_to')
    if not isinstance(applies_to, list) or not 1 <= len(applies_to) <= 2:
        raise AffixFieldError('%s：applies_to 必须是 1–2 项的数组' % element_id)
    if len(set(applies_to)) != len(applies_to):
        raise AffixFieldError('%s：applies_to 有重复值' % element_id)
    bad = [item for item in applies_to if item not in APPLIES_TO]
    if bad:
        raise AffixFieldError('%s：applies_to 有词表外取值 %s（只允许 character / item）'
                              % (element_id, bad))

    polarity = affix.get('polarity')
    if polarity not in POLARITIES:
        raise AffixFieldError('%s：polarity 非法 %r' % (element_id, polarity))
    grade = affix.get('grade')
    if grade not in GRADES:
        raise AffixFieldError('%s：grade 非法 %r' % (element_id, grade))
    caps = GRADE_CAPS[grade]

    stacking = affix.get('stacking')
    if stacking not in STACKINGS:
        raise AffixFieldError('%s：stacking 非法 %r' % (element_id, stacking))
    group = affix.get('exclusive_group')
    if stacking == 'exclusive':
        if not isinstance(group, str) or not ID_RE.match(group):
            raise AffixFieldError('%s：stacking=exclusive 时必须给出合法 exclusive_group' % element_id)
    elif group is not None:
        raise AffixFieldError('%s：只有 stacking=exclusive 才能写 exclusive_group' % element_id)

    visibility = affix.get('visibility')
    if visibility not in VISIBILITIES:
        raise AffixFieldError('%s：visibility 非法 %r' % (element_id, visibility))

    mods = affix.get('attribute_mods', {})
    if not isinstance(mods, dict):
        raise AffixFieldError('%s：attribute_mods 必须是对象' % element_id)
    bad = sorted(set(mods) - set(AXES))
    if bad:
        raise AffixFieldError('%s：attribute_mods 有六项属性以外的键 %s（只允许 %s）'
                              % (element_id, bad, list(AXES)))
    for axis, value in mods.items():
        _int(value, '%s：attribute_mods.%s' % (element_id, axis))
        if value == 0:
            raise AffixFieldError('%s：attribute_mods.%s 为 0，没有效果就别写这一项'
                                  % (element_id, axis))
        if abs(value) > caps['axis']:
            raise AffixFieldError('%s：attribute_mods.%s=%d 超过 %s 的单轴上限 %d'
                                  % (element_id, axis, value, grade, caps['axis']))
    if sum(abs(value) for value in mods.values()) > caps['sum']:
        raise AffixFieldError('%s：属性绝对值合计超过 %s 的上限 %d'
                              % (element_id, grade, caps['sum']))

    hp_mod = affix.get('hp_mod')
    if hp_mod is not None:
        _int(hp_mod, '%s：hp_mod' % element_id)
        if hp_mod == 0:
            raise AffixFieldError('%s：hp_mod 为 0，没有效果就别写' % element_id)
        if abs(hp_mod) > caps['hp']:
            raise AffixFieldError('%s：hp_mod=%d 超过 %s 的上限 %d'
                                  % (element_id, hp_mod, grade, caps['hp']))

    item_mods = affix.get('item_mods')
    if item_mods is not None:
        if 'item' not in applies_to:
            raise AffixFieldError('%s：item_mods 只能用在 applies_to 含 item 的词条上' % element_id)
        _keys(item_mods, ITEM_RANGES, 'item_mods', element_id, 1, len(ITEM_RANGES))
        for key, value in item_mods.items():
            _int(value, '%s：item_mods.%s' % (element_id, key))
            low, high = ITEM_RANGES[key]
            if key == 'damage':
                if value == 0:
                    raise AffixFieldError('%s：item_mods.damage 为 0，没有效果就别写' % element_id)
                if abs(value) > caps['damage']:
                    raise AffixFieldError('%s：item_mods.damage=%d 超过 %s 的上限 %d'
                                          % (element_id, value, grade, caps['damage']))
                if not low <= value <= high:
                    raise AffixFieldError('%s：item_mods.damage 必须在 %d..%d' % (element_id, low, high))
            else:
                if not low <= value <= high:
                    raise AffixFieldError('%s：item_mods.%s 必须在 %d..%d（与 rewards 同量程）'
                                          % (element_id, key, low, high))
                if value == 100:
                    raise AffixFieldError('%s：item_mods.%s=100 等于没改，没有效果就别写'
                                          % (element_id, key))
                if abs(value - 100) > caps['percent']:
                    raise AffixFieldError('%s：item_mods.%s=%d 相对 100 的偏移超过 %s 的上限 %d'
                                          % (element_id, key, value, grade, caps['percent']))

    narrative = affix.get('narrative', [])
    if not isinstance(narrative, list) or len(narrative) > MAX_NARRATIVE:
        raise AffixFieldError('%s：narrative 必须是最多 %d 项的数组' % (element_id, MAX_NARRATIVE))
    for line in narrative:
        if not isinstance(line, str) or not line.strip():
            raise AffixFieldError('%s：narrative 的每一项必须是非空文本' % element_id)
        if len(line.strip()) > MAX_NARRATIVE_CHARS:
            raise AffixFieldError('%s：narrative 的每一项不能超过 %d 字'
                                  % (element_id, MAX_NARRATIVE_CHARS))

    note = affix.get('note', '')
    if not isinstance(note, str) or len(note) > MAX_NOTE_CHARS:
        raise AffixFieldError('%s：note 必须是最多 %d 字的文本' % (element_id, MAX_NOTE_CHARS))

    # 正负号自洽（规范 §4）：把每一项数值折算成「对持有者是好还是坏」再校验。
    # 属性 / 血量 / 伤害直接看符号；百分比字段看方向：耐久更高、价值更高是好事，
    # 重量更轻是好事——所以要分别反转后再参与判定（不能拿原始 80% 重量当「负值」）。
    signed = list(mods.values())
    if hp_mod is not None:
        signed.append(hp_mod)
    if item_mods:
        if 'damage' in item_mods:
            signed.append(item_mods['damage'])
        if 'durability_percent' in item_mods:
            signed.append(item_mods['durability_percent'] - 100)
        if 'value_percent' in item_mods:
            signed.append(item_mods['value_percent'] - 100)
        if 'weight_percent' in item_mods:
            signed.append(100 - item_mods['weight_percent'])
    if polarity == 'boon':
        if any(value < 0 for value in signed):
            raise AffixFieldError('%s：polarity=boon 不能带对持有者不利的数值（折算 %s）'
                                  % (element_id, signed))
        if not any(value > 0 for value in signed):
            raise AffixFieldError('%s：polarity=boon 至少要有一个有利项' % element_id)
    elif polarity == 'bane':
        if any(value > 0 for value in signed):
            raise AffixFieldError('%s：polarity=bane 不能带对持有者有利的数值（折算 %s）'
                                  % (element_id, signed))
        if not any(value < 0 for value in signed):
            raise AffixFieldError('%s：polarity=bane 至少要有一个不利项' % element_id)

    has_number = bool(signed) or bool(item_mods)
    if not has_number and not narrative:
        raise AffixFieldError('%s：既没有数值影响也没有 narrative，这条词条什么都没说' % element_id)
    if not has_number and polarity != 'mixed':
        raise AffixFieldError('%s：只有 narrative 的词条必须写 polarity=mixed' % element_id)

    tags = [TAG_PREFIX + target for target in applies_to]
    tags.append(TAG_PREFIX + polarity)
    tags.append('%sgrade:%s' % (TAG_PREFIX, grade))
    if visibility == 'hidden':
        tags.append(TAG_PREFIX + 'hidden')
    tags.extend('%sattr:%s' % (TAG_PREFIX, axis) for axis in sorted(mods))
    if hp_mod is not None:
        tags.append(TAG_PREFIX + 'hp')
    return sorted(tags)


def check_element_tags(element):
    """元素自带 ``affix`` 对象时，``affix:`` 前缀的标签必须与对象推出的完全一致。"""
    element_id = element.get('id')
    expected = validate_affix(element['affix'], element_id)
    tags = element.get('tags') or []
    if 'kind:affix' not in tags:
        raise AffixFieldError('%s：词条元素必须有 kind:affix 标签' % element_id)
    actual = [tag for tag in tags if tag.startswith(TAG_PREFIX)]
    if sorted(actual) != expected:
        raise AffixFieldError('%s：affix 标签不一致，应为 %s，实际 %s'
                              % (element_id, expected, sorted(actual)))


def check_document(document):
    """校验一份源文档：带 ``affix`` 的元素逐条校验；带词条标签却没有对象的也拒绝。"""
    elements = document.get('elements') or []
    if not isinstance(elements, list):
        raise AffixFieldError('%s：elements 必须是数组' % document.get('group'))
    for element in elements:
        if not isinstance(element, dict):
            continue
        has_tags = any(tag.startswith(TAG_PREFIX) for tag in element.get('tags') or [])
        if 'affix' in element:
            check_element_tags(element)
        elif has_tags:
            raise AffixFieldError('%s：写了 affix: 标签却没有 affix 对象（标签不能自己编）'
                                  % element.get('id'))
    return document


def check_all(files, root=None):
    """校验一批源文件。返回 (分组, 带词条的元素数, 元素总数) 列表。"""
    rows = []
    for relative in files:
        document = json.loads((Path(root or ROOT) / relative).read_text(encoding='utf-8-sig'))
        check_document(document)
        elements = document.get('elements') or []
        rows.append((document.get('group'), sum(1 for e in elements if 'affix' in e), len(elements)))
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(prog='affix_fields', description='校验 affix_fields_v1')
    parser.add_argument('--check', action='store_true', help='校验全部构库分区里的词条字段')
    args = parser.parse_args(argv)
    from tools import encyclopedia_build as build
    files = build.groups_for(**build.ALL_FLAGS) if args.check else ()
    try:
        rows = check_all(files)
    except (AffixFieldError, ValueError) as error:
        sys.stderr.write('词条字段校验失败：%s\n' % error)
        return 1
    for group, with_affix, total in rows:
        if with_affix:
            sys.stdout.write('%-24s affix %3d / %3d\n' % (group, with_affix, total))
    return 0


if __name__ == '__main__':
    sys.exit(main())
