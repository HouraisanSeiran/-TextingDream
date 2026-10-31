import json
import tempfile
import unittest
from pathlib import Path

from app import encyclopedia as enc
from tools import encyclopedia_build as build

ROOT = Path(__file__).resolve().parents[1]


class CultureCatalogTests(unittest.TestCase):
    def test_culture_manifest_is_explicit_and_sources_are_pinned(self):
        self.assertEqual(len(build.CULTURE_GROUPS), 3)
        self.assertEqual(len(set(build.CULTURE_GROUPS)), 3)
        for relative in build.CULTURE_GROUPS:
            self.assertTrue((ROOT / relative).is_file())
            self.assertNotIn('*', relative)
            document = json.loads((ROOT / relative).read_text(encoding='utf-8'))
            self.assertTrue(document['elements'])
            self.assertTrue(document['sources'])
            self.assertTrue(all(item['review_status'] == 'needs_review' for item in document['elements']))
            self.assertTrue(all(set(item['source_ids']) <= {source['id'] for source in document['sources']}
                                for item in document['elements']))

    def test_culture_build_roundtrip_and_name_search(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / 'culture.sqlite3'
            groups = build.groups_for(with_culture=True)
            self.assertEqual(build.build(db, groups=groups), 0)
            stats = enc.stats(db)['totals']
            self.assertEqual(stats['groups'], 17)
            self.assertEqual(stats['elements'], 561)
            self.assertEqual(enc.search(db, text='汉语', namespace='names-asian')['total'], 1)
            results = enc.search(db, text='弗蕾雅', namespace='names-european')
            self.assertEqual(results['total'], 1)
            self.assertEqual(enc.get(db, 'culture_novel_epistolary', namespace='culture-literature')['review_status'], 'needs_review')

    def test_default_manifest_stays_backward_compatible(self):
        self.assertEqual(len(build.groups_for()), 14)
        self.assertNotIn('culture-literature', build.groups_for())

