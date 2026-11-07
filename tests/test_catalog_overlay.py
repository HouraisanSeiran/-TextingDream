# -*- coding: utf-8 -*-
"""主标签 / 证据等级（catalog_overlay_v1）与禁售选项（game.restriction）。"""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from app import encyclopedia as enc
from tools import catalog_overlay as co
from tools import game_fields as gf

SECTIONS = {key: '文本' for key in ('definition', 'mechanism', 'conditions', 'exceptions',
                                   'story_uses', 'historical_scope', 'evidence_and_uncertainty')}


def doc(elements, group='g'):
    return {'schema_version': 1, 'status': 'candidate', 'group': group,
            'sources': [{'id': 's1', 'title': 't', 'access': 'read'}], 'elements': elements}


def el(ident, **extra):
    body = {'id': ident, 'name': ident, 'summary': '', 'tags': ['kind:x'], 'details': dict(SECTIONS),
            'source_ids': ['s1']}
    body.update(extra)
    return body


class EngineCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / 'db.sqlite3'

    def tearDown(self):
        self.tmp.cleanup()

    def test_primary_and_evidence_become_tags(self):
        enc.import_document(self.db, doc([el('a', primary='vegetable', evidence_grade='sourced')]))
        self.assertEqual(enc.search(self.db, tags_all=['primary:vegetable'])['total'], 1)
        self.assertEqual(enc.search(self.db, tags_all=['evidence:sourced'])['total'], 1)

    def test_tier_fields_become_tags(self):
        enc.import_document(self.db, doc([el('a', tech_tier='steam', magic_tier='rare')]))
        self.assertEqual(enc.search(self.db, tags_all=['tech:steam', 'magic:rare'])['total'], 1)

    def test_tier_field_must_match_handwritten_tag(self):
        enc.import_document(self.db, doc([el('a', tags=['kind:x', 'tech:steam'], tech_tier='steam')]))
        with self.assertRaises(enc.InvalidDocument):
            enc.import_document(self.db, doc([el('b', tags=['kind:x', 'tech:steam'], tech_tier='medieval')],
                                             group='g2'))

    def test_bad_tier_is_refused(self):
        with self.assertRaises(enc.InvalidDocument):
            enc.import_document(self.db, doc([el('a', magic_tier='legendary')]))

    def test_handwritten_primary_tag_is_refused(self):
        with self.assertRaises(enc.InvalidDocument):
            enc.import_document(self.db, doc([el('a', tags=['primary:vegetable'])]))

    def test_bad_evidence_grade_is_refused(self):
        with self.assertRaises(enc.InvalidDocument):
            enc.import_document(self.db, doc([el('a', evidence_grade='certain')]))

    def test_element_without_fields_is_unchanged(self):
        result = enc.import_document(self.db, doc([el('a')]))
        self.assertEqual(result.as_dict()['elements'], 1)
        self.assertEqual(enc.search(self.db, tags_all=['kind:x'])['total'], 1)


class OverlayCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / co.OVERLAY_DIR).mkdir(parents=True)
        self.document = doc([el('a'), el('b', related_catalog_ids=['x'])])

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, entries):
        (self.root / co.OVERLAY_DIR / 'g.json').write_text(json.dumps(
            {'schema': co.SCHEMA, 'group': 'g', 'entries': entries}), encoding='utf-8')

    def test_no_overlay_returns_document_unchanged(self):
        before = copy.deepcopy(self.document)
        self.assertEqual(co.overlay(self.document, self.root), before)

    def test_overlay_sets_fields_and_appends_relations(self):
        self.write({'a': {'primary': 'vegetable', 'evidence_grade': 'sourced'},
                    'b': {'primary': 'formula', 'evidence_grade': 'mixed', 'related_add': ['x', 'y']}})
        merged = co.overlay(self.document, self.root)
        self.assertEqual(merged['elements'][0]['primary'], 'vegetable')
        self.assertEqual(merged['elements'][1]['related_catalog_ids'], ['x', 'y'])
        self.assertNotIn('primary', self.document['elements'][0], '入参不得被修改')

    def test_genres_add_appends_without_duplicates(self):
        self.document['elements'][0]['genres'] = ['real_world']
        self.write({'a': {'primary': 'vegetable', 'evidence_grade': 'sourced',
                          'genres_add': ['real_world', 'historical', 'western_fantasy']},
                    'b': {'primary': 'formula', 'evidence_grade': 'mixed'}})
        merged = co.overlay(self.document, self.root)
        self.assertEqual(merged['elements'][0]['genres'], ['real_world', 'historical', 'western_fantasy'])
        self.assertNotIn('genres', merged['elements'][1])
        self.write({'a': {'primary': 'vegetable', 'evidence_grade': 'sourced', 'genres_add': ['sci_fi']},
                    'b': {'primary': 'formula', 'evidence_grade': 'mixed'}})
        with self.assertRaises(co.OverlayError):
            co.overlay(self.document, self.root)

    def test_must_cover_every_element_exactly(self):
        self.write({'a': {'primary': 'vegetable', 'evidence_grade': 'sourced'}})
        with self.assertRaises(co.OverlayError):
            co.overlay(self.document, self.root)
        self.write({'a': {'primary': 'vegetable', 'evidence_grade': 'sourced'},
                    'b': {'primary': 'fruit', 'evidence_grade': 'sourced'},
                    'zz': {'primary': 'fruit', 'evidence_grade': 'sourced'}})
        with self.assertRaises(co.OverlayError):
            co.overlay(self.document, self.root)

    def test_vocabulary_is_enforced(self):
        self.write({'a': {'primary': 'cabbage', 'evidence_grade': 'sourced'},
                    'b': {'primary': 'fruit', 'evidence_grade': 'sourced'}})
        with self.assertRaises(co.OverlayError):
            co.overlay(self.document, self.root)

    def test_shop_is_in_the_vocabulary(self):
        self.assertIn('shop', co.PRIMARY)


GAME = {'price': {'min': 24, 'max': 96, 'per': '一两', 'tier': 'shilling'},
        'terrains': ['mountain'], 'seasons': ['all_year'], 'keeps': 'years',
        'sold_by': ['apothecary'], 'note': ''}


class RestrictionCase(unittest.TestCase):
    def test_medieval_baseline_sells_restricted_goods(self):
        game = dict(GAME, restriction='endangered_animal')
        self.assertTrue(gf.is_for_sale(game))
        self.assertFalse(gf.is_for_sale(game, {'endangered_animal'}))
        self.assertTrue(gf.is_for_sale(game, {'toxic'}))

    def test_restriction_adds_a_tag(self):
        tags = gf.validate_game(dict(GAME, restriction='toxic'), 'x')
        self.assertIn('restriction:toxic', tags)

    def test_unknown_restriction_is_refused(self):
        with self.assertRaises(gf.GameFieldError):
            gf.validate_game(dict(GAME, restriction='illegal'), 'x')
        with self.assertRaises(gf.GameFieldError):
            gf.is_for_sale(GAME, {'illegal'})

    def test_priceless_is_never_for_sale(self):
        game = dict(GAME, price={'min': None, 'max': None, 'per': '', 'tier': 'priceless'},
                    sold_by=['none'])
        self.assertFalse(gf.is_for_sale(game))

    def test_shop_keys_exclude_non_shops(self):
        self.assertIn('blacksmith', gf.SOLD_BY)
        self.assertIn('armorer', gf.SOLD_BY)


if __name__ == '__main__':
    unittest.main()
