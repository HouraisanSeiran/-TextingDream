# -*- coding: utf-8 -*-
"""词条分区 fantasy-affixes：名单显式、字段自洽、标签派生、入库检索、不碰其他分区的边界。

这些测试只构库到临时目录；不读写 ``artifacts/human-encyclopedia/encyclopedia.sqlite3``。
"""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from app import attributes, encyclopedia as enc
from tools import affix_fields as af
from tools import encyclopedia_build as build

ROOT = Path(__file__).resolve().parents[1]
RELATIVE = 'docs/element-catalog/fantasy-affixes.json'
NAMESPACE = 'fantasy-affixes'
SECTIONS = enc.DETAIL_SECTIONS


def document():
    return json.loads((ROOT / RELATIVE).read_text(encoding='utf-8-sig'))


def good_affix(**changes):
    value = {
        'schema': 'affix_fields_v1',
        'applies_to': ['character'],
        'polarity': 'boon',
        'grade': 'common',
        'stacking': 'unique',
        'visibility': 'public',
        'attribute_mods': {'strength': 4},
    }
    value.update(changes)
    return value


def element(ident='affix_x', affix=None, tags=None):
    tags = list(tags if tags is not None else
                ['kind:affix', 'affix:character', 'affix:boon', 'affix:grade:common',
                 'affix:attr:strength'])
    body = {'id': ident, 'name': ident, 'summary': '', 'tags': tags,
            'details': {key: '文本' for key in SECTIONS},
            'source_ids': ['s1'], 'primary': 'affix', 'evidence_grade': 'inferred'}
    if affix is not None:
        body['affix'] = affix
    return body


def doc(elements, group=NAMESPACE):
    return {'schema_version': 1, 'status': 'candidate', 'group': group,
            'sources': [{'id': 's1', 'title': 't', 'access': 'read'}], 'elements': elements}


class ManifestCase(unittest.TestCase):
    """名单层：显式、独立、默认不入库、旧调用不受影响。"""

    def test_group_is_explicit_and_opt_in(self):
        self.assertEqual(tuple(build.AFFIX_GROUPS), (RELATIVE,))
        self.assertNotIn(RELATIVE, build.GROUPS, '词条分区不能默认进库')
        for groups in (build.LATEST_GROUPS, build.CUISINE_GROUPS, build.CULTURE_GROUPS,
                       build.ATTRIBUTE_GROUPS, build.TRAIT_GROUPS, build.GROUPS):
            self.assertNotIn(RELATIVE, groups)
        self.assertTrue((ROOT / RELATIVE).exists())

    def test_old_callers_are_unchanged(self):
        self.assertEqual(build.groups_for(), build.GROUPS)
        self.assertEqual(len(build.groups_for()), 14)
        self.assertEqual(build.groups_for(True), build.LATEST_GROUPS)
        self.assertEqual(build.groups_for(True, True, True),
                         build.LATEST_GROUPS + build.CUISINE_GROUPS + build.ATTRIBUTE_GROUPS)

    def test_flag_appends_last_and_combines(self):
        only = build.groups_for(with_affixes=True)
        self.assertEqual(only, build.GROUPS + build.AFFIX_GROUPS)
        combined = build.groups_for(True, False, True, with_affixes=True)
        self.assertEqual(combined,
                         build.GROUPS + build.TRAIT_GROUPS + build.ATTRIBUTE_GROUPS
                         + build.AFFIX_GROUPS)
        self.assertEqual(len(set(combined)), len(combined))

    def test_parser_exposes_the_flag(self):
        parser = build.build_parser()
        self.assertFalse(parser.parse_args([]).with_affixes)
        self.assertTrue(parser.parse_args(['--with-affixes']).with_affixes)
        args = parser.parse_args(['--with-traits', '--with-affixes'])
        self.assertTrue(args.with_traits and args.with_affixes)


class ValidateCase(unittest.TestCase):
    """字段自洽：幅度、符号、词表、互斥组、空效果。"""

    def assertRejected(self, affix, ident='affix_x'):
        with self.assertRaises(af.AffixFieldError):
            af.validate_affix(affix, ident)

    def test_good_affix_yields_expected_tags(self):
        self.assertEqual(
            af.validate_affix(good_affix(hp_mod=5), 'affix_x'),
            ['affix:attr:strength', 'affix:boon', 'affix:character', 'affix:grade:common',
             'affix:hp'])

    def test_hidden_and_item_and_grade_tags(self):
        tags = af.validate_affix(good_affix(applies_to=['character', 'item'], grade='rare',
                                            visibility='hidden',
                                            item_mods={'damage': 4}), 'affix_y')
        self.assertIn('affix:hidden', tags)
        self.assertIn('affix:item', tags)
        self.assertIn('affix:character', tags)
        self.assertIn('affix:grade:rare', tags)

    def test_unknown_attribute_is_refused(self):
        self.assertRejected(good_affix(attribute_mods={'charisma': 5}))
        self.assertRejected(good_affix(attribute_mods={'intelligence': 5}))

    def test_axis_and_total_caps_follow_grade(self):
        self.assertRejected(good_affix(attribute_mods={'strength': 7}))          # common 单轴 6
        af.validate_affix(good_affix(grade='uncommon', attribute_mods={'strength': 7}), 'x')
        self.assertRejected(good_affix(grade='uncommon',
                                       attribute_mods={'strength': 10, 'agility': 9}))  # 合计 19 > 18
        # 恰好等于上限不拒（上限是「不超过」而不是「小于」）
        af.validate_affix(good_affix(grade='uncommon',
                                     attribute_mods={'strength': 9, 'agility': 9}), 'x')
        self.assertRejected(good_affix(grade='legendary',
                                       attribute_mods={'strength': 21}))         # legendary 20
        self.assertRejected(good_affix(hp_mod=11))                               # common hp 10

    def test_zero_effects_are_refused(self):
        self.assertRejected(good_affix(attribute_mods={'strength': 0}))
        self.assertRejected(good_affix(attribute_mods={}, hp_mod=0))

    def test_polarity_must_match_direction(self):
        self.assertRejected(good_affix(polarity='boon',
                                       attribute_mods={'strength': 4, 'agility': -2}))
        self.assertRejected(good_affix(polarity='bane',
                                       attribute_mods={'strength': 4}))
        self.assertRejected(good_affix(polarity='boon', attribute_mods={}))
        # mixed 允许两边都有
        af.validate_affix(good_affix(polarity='mixed',
                                     attribute_mods={'strength': 5, 'agility': -3}), 'x')

    def test_percentage_direction_is_understood(self):
        # 更轻、更耐久、更值钱对持有者有利；更重是不利。
        af.validate_affix(good_affix(applies_to=['item'], attribute_mods={},
                                     item_mods={'weight_percent': 80,
                                                'durability_percent': 130}), 'x')
        self.assertRejected(good_affix(applies_to=['item'], attribute_mods={},
                                       item_mods={'weight_percent': 120}))

    def test_item_mods_need_item_target(self):
        self.assertRejected(good_affix(item_mods={'damage': 3}))

    def test_percentage_must_differ_from_100(self):
        self.assertRejected(good_affix(applies_to=['item'], attribute_mods={},
                                       item_mods={'value_percent': 100}))

    def test_narrative_only_needs_mixed(self):
        only_text = good_affix(attribute_mods={}, polarity='mixed', narrative=['旁人开始避着他'])
        af.validate_affix(only_text, 'x')
        self.assertRejected(good_affix(attribute_mods={}, polarity='boon',
                                       narrative=['旁人开始避着他']))
        self.assertRejected(good_affix(attribute_mods={}, polarity='mixed'))

    def test_exclusive_group_rules(self):
        self.assertRejected(good_affix(stacking='exclusive'))
        af.validate_affix(good_affix(stacking='exclusive',
                                     exclusive_group='affix.curse'), 'x')
        self.assertRejected(good_affix(stacking='unique', exclusive_group='affix.curse'))

    def test_unknown_fields_and_bad_schema_are_refused(self):
        self.assertRejected(good_affix(schema='affix_fields_v2'))
        self.assertRejected(good_affix(effects=[{'kind': 'x'}]))

    def test_tags_must_match_the_object(self):
        good = element(affix=good_affix())
        af.check_element_tags(good)
        mismatched = element(affix=good_affix(), tags=['kind:affix', 'affix:character',
                                                       'affix:boon', 'affix:grade:rare',
                                                       'affix:attr:strength'])
        with self.assertRaises(af.AffixFieldError):
            af.check_element_tags(mismatched)

    def test_tags_without_object_are_refused(self):
        with self.assertRaises(af.AffixFieldError):
            af.check_document(doc([element(tags=['kind:affix', 'affix:character'])]))

    def test_missing_kind_tag_is_refused(self):
        with self.assertRaises(af.AffixFieldError):
            af.check_element_tags(element(affix=good_affix(),
                                          tags=['affix:character', 'affix:boon',
                                                'affix:grade:common', 'affix:attr:strength']))


class SourceDataCase(unittest.TestCase):
    """仓库里那份真实源文件：条数、七节、来源、状态、ID 六项属性对齐。"""

    @classmethod
    def setUpClass(cls):
        cls.document = document()

    def test_every_element_has_affix_and_seven_sections(self):
        for item in self.document['elements']:
            self.assertIn('affix', item, item['id'])
            for section in SECTIONS:
                self.assertTrue(item['details'][section].strip(), '%s/%s' % (item['id'], section))
            self.assertEqual(item['review_status'], 'needs_review')
            self.assertEqual(item['detail_status'], 'needs_detail')
            self.assertEqual(item['primary'], 'affix')
            self.assertEqual(item['evidence_grade'], 'inferred')
            self.assertIn('tech_tier', item)
            self.assertIn('magic_tier', item)

    def test_source_ids_resolve_inside_the_file(self):
        known = {source['id'] for source in self.document['sources']}
        for item in self.document['elements']:
            self.assertTrue(set(item['source_ids']) <= known, item['id'])

    def test_attribute_ids_are_the_six_axes(self):
        for item in self.document['elements']:
            mods = item['affix'].get('attribute_mods') or {}
            self.assertTrue(set(mods) <= set(attributes.AXES), item['id'])

    def test_related_ids_point_inside_the_file(self):
        known = {item['id'] for item in self.document['elements']}
        for item in self.document['elements']:
            self.assertTrue(set(item.get('related_ids') or []) <= known, item['id'])

    def test_whole_document_passes_the_validator(self):
        af.check_document(self.document)

    def test_both_character_and_item_coverage_exists(self):
        slots = set()
        for item in self.document['elements']:
            slots.update(item['affix']['applies_to'])
        self.assertEqual(slots, {'character', 'item'})

    def test_exclusive_groups_are_declared_together(self):
        groups = {}
        for item in self.document['elements']:
            affix = item['affix']
            if affix.get('stacking') == 'exclusive':
                groups.setdefault(affix['exclusive_group'], []).append(item['id'])
        for group, members in groups.items():
            self.assertGreaterEqual(len(members), 1, group)
            for member in members:
                again = copy.deepcopy(document()['elements'])
                self.assertTrue(any(x['id'] == member for x in again))


class BuildCase(unittest.TestCase):
    """入库：条数、标签检索、幂等、按 grade 检索、默认库不受影响。"""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = Path(cls.tmp.name) / 'affixes.sqlite3'
        code = build.build(cls.db, as_json=True, groups=build.AFFIX_GROUPS)
        if code != build.EXIT_OK:
            raise AssertionError('构库失败：%s' % code)
        cls.document = document()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_totals_match_the_source(self):
        totals = enc.stats(self.db)['totals']
        self.assertEqual(totals['groups'], 1)
        self.assertEqual(totals['elements'], len(self.document['elements']))
        self.assertEqual(totals['sources'], len(self.document['sources']))
        self.assertEqual(totals['unresolved_relations'], 0)

    def test_search_by_tag(self):
        self.assertEqual(enc.search(self.db, namespace=NAMESPACE, tags_all=['primary:affix'])['total'],
                         len(self.document['elements']))
        for tag in ('affix:character', 'affix:item', 'affix:boon', 'affix:bane',
                    'affix:mixed', 'affix:hidden', 'kind:affix'):
            page = enc.search(self.db, namespace=NAMESPACE, tags_all=[tag])
            self.assertGreater(page['total'], 0, tag)
        self.assertEqual(
            enc.search(self.db, namespace=NAMESPACE, tags_all=['affix:attr:strength'])['total'],
            sum(1 for e in self.document['elements'] if 'strength' in (e['affix'].get('attribute_mods') or {})))

    def test_search_by_name(self):
        page = enc.search(self.db, namespace=NAMESPACE, text='邪神')
        self.assertGreaterEqual(page['total'], 1)

    def test_payload_keeps_the_affix_object(self):
        detail = enc.get(self.db, 'affix_strong', namespace=NAMESPACE)
        self.assertEqual(detail['payload']['affix']['attribute_mods'], {'strength': 6})

    def test_rebuild_is_idempotent(self):
        again = Path(self.tmp.name) / 'again.sqlite3'
        first = enc.stats(self.db)['totals']
        code = build.build(again, as_json=True, groups=build.AFFIX_GROUPS)
        self.assertEqual(code, build.EXIT_OK)
        second = enc.stats(again)['totals']
        self.assertEqual(first['elements'], second['elements'])
        self.assertEqual(second['element_versions'], second['elements'])


class BoundaryCase(unittest.TestCase):
    """边界：词条不该被别的机制静默消费。"""

    def test_affix_is_not_a_character_trait_namespace(self):
        from app import traits
        self.assertNotEqual(NAMESPACE, traits.NAMESPACE)
        # 词条不写进 mechanics.traits：源文件里既没有 traits 快照，也没有 payload 混用
        installed = {relative: True for relative in build.LATEST_GROUPS}
        self.assertNotIn(RELATIVE, installed)

    def test_affix_does_not_define_new_axes(self):
        self.assertEqual(attributes.AXES,
                         ('talent', 'strength', 'agility', 'wisdom', 'social', 'resilience'))

    def test_health_formula_is_untouched(self):
        spec = attributes.specification()
        self.assertEqual(spec['hp'], {'base': 50, 'per_resilience': 2})
        self.assertEqual(spec['scale'], [0, 100])


if __name__ == '__main__':
    unittest.main()
