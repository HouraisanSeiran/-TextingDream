# -*- coding: utf-8 -*-
"""Location clues: a displaced, honest circle over the fog; never the true position.

Self-contained: a temporary Store, a synthetic heightmap import and a minimal committed
world built in this file, so nothing touches ``data/`` or the user's worlds.
"""
import copy
import json
import math
import tempfile
import unittest
from pathlib import Path

from app import map_clues, map_import, play_map
from app.service import Service
from app.storage import Store

from .test_civ_atlas_import import heightmap_png
from .test_play_map import decode_png, fog_at, pixel

TREASURE = [24.0, -8.0]


def great_circle_km(a, b):
    lon1, lat1, lon2, lat2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    cos_d = (math.sin(lat1) * math.sin(lat2)
             + math.cos(lat1) * math.cos(lat2) * math.cos(lon2 - lon1))
    return math.acos(max(-1.0, min(1.0, cos_d))) * play_map.EARTH_RADIUS_KM


def world(import_id, withheld=False, extra_effects=None):
    hoard = {'id': 'hidden_hoard', 'name': '沉船藏宝地', 'description': '',
             'coordinates': list(TREASURE), 'neighbors': [], 'scenes': []}
    if withheld:
        hoard['visibility'] = 'author'
    story = {
        'id': 'clue-test', 'title': '线索世界', 'premise': '寻宝。',
        'character_package_id': 'clue-cast',
        'locations': [{'id': 'harbor', 'name': '港口', 'description': '',
                       'coordinates': [10.0, 10.0], 'neighbors': [], 'scenes': []}, hoard],
        'events': [{'id': 'root', 'title': '酒馆', 'location_id': 'harbor',
                    'participants': ['player'], 'player_goal': '打听',
                    'player_enters': True, 'next_events': [], 'entry_flags': {},
                    'exit_flag': 'done', 'max_turns': 8,
                    'actions': [{'id': 'ask', 'label': '打听', 'ends_event': True,
                                 'success_text': '听到了传闻。',
                                 'effects': list(extra_effects or [])}]}],
        'items': [],
        'mechanics': {'local': {'turn_hours': 1, 'travel_hours': 2},
                      'map': {'kind': 'civ_atlas', 'import_id': import_id,
                              'fog': {'reveal_radius_km': 300}}},
    }
    axes = {k: 50 for k in ('talent', 'strength', 'agility', 'wisdom', 'social', 'resilience')}
    characters = {'id': 'clue-cast', 'title': '角色', 'characters': [
        {'id': 'player', 'name': '我', 'role': '主角', 'location_id': 'harbor',
         'personality': {}, 'state': {}, 'attributes': dict(axes)}]}
    return story, characters


class ClueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.svc = Service(Store(cls.root / 'clue.sqlite3'), cls.root)
        cls.svc.provider.configure({'offline': True})
        cls.record = map_import.create_import(cls.svc.store, cls.root,
                                             heightmap_png(width=1024, height=512))

    @classmethod
    def tearDownClass(cls):
        play_map.clear_cache()
        cls.tmp.cleanup()

    def setUp(self):
        play_map.clear_cache()

    def journey(self, withheld=False):
        story, characters = world(self.record['id'], withheld)
        self.svc.runtime.commit_package(story, characters, '线索测试')
        return self.svc.store.session(self.svc.runtime.new_session('寻宝', 'protagonist')['id'])

    def story_of(self, session):
        return self.svc.runtime.package(session['revision'])['story']

    def grant(self, session, **effect):
        effect = {'op': 'place_clue', 'place': 'hidden_hoard', 'precision_km': 200,
                  'label': '', 'text': '老水手说沉船就在南边那片礁石附近', **effect}
        self.svc.runtime.effects(session, [effect], 'test')
        return session

    def projection(self, session):
        story = self.story_of(session)
        status, context = play_map.resolve(self.svc.store, self.root, story)
        payload = play_map.projection(session, story, status=status, context=context,
                                      session_id=session['id'])
        return payload, status, context, story

    # ------------------------------------------------------------------ tests
    def test_clue_circle_contains_the_truth_but_is_not_centred_on_it(self):
        session = self.grant(self.journey())
        clue = session['clues'][0]
        offset = great_circle_km((clue['lon'], clue['lat']), TREASURE)
        self.assertLessEqual(offset, clue['radius_km'] * map_clues.MAX_OFFSET_FRACTION + 1)
        self.assertGreaterEqual(offset, clue['radius_km'] * map_clues.MIN_OFFSET_FRACTION - 1)

    def test_projection_never_carries_the_true_position_or_hidden_id(self):
        session = self.grant(self.journey(withheld=True))
        payload, status, _context, _story = self.projection(session)
        self.assertEqual(status, play_map.STATUS_OK)
        self.assertEqual(len(payload['clues']), 1)
        text = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn('hidden_hoard', text)
        self.assertNotIn('沉船藏宝地', text, '被保留的地点不得以真名出现')
        self.assertEqual(payload['clues'][0]['label'], map_clues.UNKNOWN_LABEL)
        self.assertNotIn('"lon": 24.0,', text)

    def test_named_place_uses_its_name_or_the_author_label(self):
        session = self.grant(self.journey())
        payload, *_ = self.projection(session)
        self.assertEqual(payload['clues'][0]['label'], '沉船藏宝地')
        self.grant(session, label='藏宝图上的X')
        payload, *_ = self.projection(session)
        self.assertEqual(payload['clues'][1]['label'], '藏宝图上的X')

    def test_clue_widens_the_crop_but_reveals_no_terrain(self):
        session = self.journey()
        before, *_ = self.projection(session)
        self.grant(session)
        payload, _status, context, story = self.projection(session)
        self.assertNotEqual(before['basemap']['bbox'], payload['basemap']['bbox'])
        places = play_map.visible_places(session, story)
        png = play_map.basemap_png(context, places, context.get('link'), payload['clues'])
        image = decode_png(png)
        bbox = payload['basemap']['bbox']
        clue = payload['clues'][0]
        fog = lambda lon, lat: fog_at(places, context.get('link'), payload['clues'], lon, lat)
        self.assertEqual(pixel(image, bbox, clue['lon'], clue['lat']), fog(clue['lon'], clue['lat']))
        self.assertEqual(pixel(image, bbox, *TREASURE), fog(*TREASURE))
        player = payload['player']
        self.assertNotEqual(pixel(image, bbox, player['lon'], player['lat']),
                            fog(player['lon'], player['lat']))

    def test_same_effect_is_deterministic_and_a_second_clue_moves(self):
        session = self.grant(self.journey())
        again = map_clues.displaced_centre(session['seed'], 'hidden_hoard', 0, *TREASURE, 200.0)
        self.assertAlmostEqual(session['clues'][0]['lon'], round(again[0], 5))
        self.grant(session)
        a, b = session['clues']
        self.assertNotEqual((a['lon'], a['lat']), (b['lon'], b['lat']))

    def test_clue_resolves_once_the_place_is_reached(self):
        session = self.grant(self.journey())
        session['explored'].append('hidden_hoard')
        self.assertEqual(map_clues.projection(session, self.story_of(session)), [])

    def test_text_goes_to_the_heard_log(self):
        session = self.grant(self.journey())
        self.assertTrue(any(h.get('clue') == session['clues'][0]['id'] for h in session['heard']))

    def test_package_validation_refuses_bad_clues(self):
        for bad in ({'place': 'nowhere'}, {'precision_km': 5}, {'precision_km': True},
                    {'label': 'x' * 41}):
            effect = {'op': 'place_clue', 'place': 'hidden_hoard', **bad}
            story, characters = world(self.record['id'], extra_effects=[effect])
            with self.assertRaises(ValueError, msg=repr(bad)):
                self.svc.runtime.validate_package(story, characters)

    def test_package_validation_accepts_a_good_clue(self):
        effect = {'op': 'place_clue', 'place': 'hidden_hoard', 'precision_km': 300, 'label': '藏宝地'}
        story, characters = world(self.record['id'], extra_effects=[effect])
        self.svc.runtime.validate_package(copy.deepcopy(story), characters)

    def test_place_without_coordinates_is_refused(self):
        story, characters = world(self.record['id'])
        story['locations'][1].pop('coordinates')
        with self.assertRaises(ValueError):
            map_clues.validate_effect({'op': 'place_clue', 'place': 'hidden_hoard'}, story)


if __name__ == '__main__':
    unittest.main()
