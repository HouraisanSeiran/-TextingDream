"""Attribute catalog round trip and existing Runtime adjudication, on temporary stores."""
import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from app import attributes, encyclopedia as enc
from app.contracts import Turn
from app.drama import resolve_check
from app.element_assembly import ElementLibrary
from app.service import Service
from app.storage import Store
from tests.test_empty_world_startup import _story, _characters
from tools import encyclopedia_build as build

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs/playable-demo/character-attributes.json'


class AttributeCatalogTests(unittest.TestCase):
    def test_definitions_match_existing_rules(self):
        document = json.loads(SOURCE.read_text(encoding='utf-8'))
        spec = attributes.specification()
        self.assertEqual([e['id'] for e in document['elements']], list(attributes.AXES))
        for element, axis in zip(document['elements'], spec['axes']):
            self.assertEqual(element['name'], axis['name'])
            self.assertEqual(element['details']['attribute_definition'],
                             {'version': spec['version'], 'scale': spec['scale'], **axis})
        self.assertNotIn('???', SOURCE.read_text(encoding='utf-8'))
        self.assertEqual(build.groups_for(with_attributes=True),
                         build.GROUPS + build.ATTRIBUTE_GROUPS)
        self.assertEqual(build.groups_for(True, True, True),
                         build.LATEST_GROUPS + build.CUISINE_GROUPS + build.ATTRIBUTE_GROUPS)

    def test_import_is_searchable_and_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / 'elements.sqlite3'
            first = enc.import_file(db, SOURCE)
            self.assertEqual(first.elements, 6)
            library = ElementLibrary(ROOT, path=db, allowed_roots=[Path(temp)])
            for name in attributes.NAMES.values():
                result = library.search(text=name, namespace='character-attributes')
                self.assertTrue(any(item['name'] == name for item in result['items']))
            again = enc.import_file(db, SOURCE)
            self.assertTrue(again.idempotent)
            self.assertEqual(again.as_dict()['element_versions_written'], 0)

    def test_runtime_uses_existing_attribute_formula_for_each_axis(self):
        for axis in attributes.AXES:
            with self.subTest(axis=axis), tempfile.TemporaryDirectory() as temp:
                service = Service(Store(Path(temp) / 'session.sqlite3'), ROOT)
                service.provider.configure({'offline': True})
                story, characters = _story(), _characters()
                characters['characters'][0]['attributes'][axis] = 80
                action = story['events'][0]['actions'][0]
                action['check'] = {'attribute': axis, 'difficulty': .6}
                action['failure_text'] = '尝试受阻。'
                service.runtime.commit_package(story, characters, '属性接线测试')
                session = service.runtime.new_session('属性测试', 'protagonist')
                fatigue = session['characters']['player']['status'].get('疲劳', 0)
                expected = resolve_check(f"{session['seed']}:root:look", axis, .8, .6, fatigue)
                asyncio.run(service.turn(session['id'], Turn(message='尝试', action_id='look')))
                saved = service.store.session(session['id'])
                for key, value in expected.items():
                    self.assertEqual(saved['checks'][-1][key], value)


if __name__ == '__main__':
    unittest.main()
