"""Town art candidate generation, coverage, and versioned import integration."""
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from app import encyclopedia as enc
from tools import encyclopedia_build as build
from tools import town_art_elements as town


class TownArtElementsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.warnings = []
        cls.document = town.generate_document(warn=cls.warnings.append)

    def test_prepared_unique_candidates_and_sources(self):
        prepared = enc.prepare_document(self.document)
        self.assertEqual(prepared.namespace, town.NAMESPACE)
        ids = [row['id'] for row in self.document['elements']]
        self.assertEqual(len(ids), len(set(ids)))
        sources = {source['id'] for source in self.document['sources']}
        for source in self.document['sources']:
            self.assertEqual(source['access'], 'read')
            self.assertTrue((town.ROOT / source['url']).is_file())
            self.assertIn('非历史事实核实', source['supports'])
        for row in self.document['elements']:
            self.assertEqual(row['review_status'], 'needs_review')
            self.assertEqual(row['detail_status'], 'needs_detail')
            self.assertTrue(set(row['source_ids']) <= sources)
            self.assertTrue(row['source_ids'])
            self.assertNotIn('race:common', row['tags'])
            self.assertRegex(row['name'], r'[\u3400-\u9fff]')
        self.assertFalse([warning for warning in self.warnings if '未命名' in warning])

    def test_all_symbols_exactly_once_and_grouped_by_type(self):
        expected = []
        keys = set()
        for path in sorted((town.ROOT / town.ART_ROOT).glob('*/meta.json')):
            for meta in json.loads(path.read_text(encoding='utf-8-sig')):
                expected.append(meta['id'])
                race = 'human' if meta['race'] == 'common' else meta['race']
                keys.add((meta['style'], race, meta['kind']))
        actual = [symbol for row in self.document['elements'] for symbol in row['art_symbols']]
        self.assertEqual(Counter(actual), Counter(expected))
        self.assertEqual(len(actual), len(set(actual)))
        self.assertEqual(len(keys), len(self.document['elements']))
        for row in self.document['elements']:
            for variant in row['art_variants']:
                race = 'human' if variant['race'] == 'common' else variant['race']
                for tag in (f'race:{race}', f'style:{variant["style"]}',
                            f'category:{variant["category"]}'):
                    self.assertIn(tag, row['tags'])
                for field in ('facility', 'culture', 'resource'):
                    if variant.get(field):
                        self.assertIn(f'{field}:{variant[field]}', row['tags'])
                self.assertIn(variant['footprint'], row['footprint'])

    def test_import_idempotent_and_versioned(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / 'encyclopedia.sqlite3'
            first = enc.import_document(db, self.document)
            second = enc.import_document(db, self.document)
            self.assertFalse(first.idempotent)
            self.assertTrue(second.idempotent)
            self.assertEqual(second.element_versions, 0)
            self.assertEqual(first.element_versions, len(self.document['elements']))
            changed = json.loads(json.dumps(self.document))
            changed['elements'][0]['summary'] += ' 人工补充。'
            third = enc.import_document(db, changed)
            self.assertEqual(third.element_versions, 1)
            totals = enc.stats(db)['totals']
            self.assertEqual(totals['elements'], len(self.document['elements']))
            self.assertEqual(totals['element_versions'], totals['elements'] + 1)

    def test_explicit_opt_in_independent_and_compatible(self):
        self.assertEqual(build.groups_for(), build.GROUPS)
        self.assertEqual(build.groups_for(True, True, True),
                         build.LATEST_GROUPS + build.CUISINE_GROUPS + build.ATTRIBUTE_GROUPS)
        self.assertEqual(build.groups_for(with_town_buildings=True),
                         build.GROUPS + build.TOWN_BUILDING_GROUPS)
        self.assertEqual(build.TOWN_BUILDING_GROUPS, (town.OUTPUT.as_posix(),))
        self.assertTrue(build.build_parser().parse_args(['--with-town-buildings']).with_town_buildings)
        self.assertFalse(build.build_parser().parse_args([]).with_town_buildings)

    def test_new_directories_missing_metadata_and_material_merging(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            art = root / town.ART_ROOT
            (art / 'unfinished').mkdir(parents=True)
            finished = art / 'new-art'
            finished.mkdir()
            rows = [{'id': f'west-common-road-stone-{index:04b}', 'kind': 'road_stone',
                     'style': 'west', 'race': 'common', 'category': 'road',
                     'facility': None, 'footprint': [1, 1], 'name_zh': '石板路'}
                    for index in range(16)]
            (finished / 'meta.json').write_text(json.dumps(rows), encoding='utf-8')
            warnings = []
            document = town.generate_document(root, warn=warnings.append)
            self.assertEqual(len(document['elements']), 1)
            self.assertEqual(len(document['elements'][0]['art_symbols']), 16)
            self.assertEqual(document['elements'][0]['source_ids'], ['town_buildings_src_spec'])
            self.assertTrue(any('unfinished' in warning for warning in warnings))
            self.assertEqual(document, town.generate_document(root, warn=lambda _: None))


if __name__ == '__main__':
    unittest.main()
