import tempfile
import unittest
from pathlib import Path
from app.service import Service
from app.storage import Store

ROOT = Path(__file__).resolve().parents[1]


class StateAnchorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.svc = Service(Store(Path(self.tmp.name) / 'test.sqlite3'), ROOT)
        self.rt = self.svc.runtime
        self.s = self.rt.new_session('时空边界', 'protagonist')

    def tearDown(self):
        self.tmp.cleanup()

    def test_clock_and_chapter_are_distinct(self):
        for time, day, hour in [(23,1,'23:00'), (24,2,'00:00'), (30,2,'06:00'), (42,2,'18:00')]:
            self.s['time'] = time
            c = self.rt.context(self.s, 'player', '现在何时何地？', self.svc.preferences())
            a = c['current_anchor']
            self.assertEqual(a['clock']['game_day'], day)
            self.assertEqual(a['clock']['local_time'], hour)
            self.assertEqual(a['location_id'], self.s['location'])
            self.assertIn('离乡前夜', a['chapter_title'])
            self.assertTrue(a['inventory_complete'])

    def test_npc_view_does_not_inherit_player_location(self):
        self.s['characters']['pass_guard']['location'] = 'crescent_oasis'
        c = self.rt.context(self.s, 'pass_guard', '现在在哪里？', self.svc.preferences())
        a = c['current_anchor']
        self.assertEqual(a['location_id'], 'crescent_oasis')
        self.assertNotEqual(a['location_id'], self.s['location'])
        self.assertIn('pass_guard', [x['id'] for x in a['co_located_characters']])
        self.assertNotIn(self.s['hero'], [x['id'] for x in a['co_located_characters']])
        self.assertEqual([x['id'] for x in c['cast']], ['pass_guard'])
        self.assertFalse(a['inventory_complete'])
        self.assertNotIn('local_state', c)
        self.assertEqual(c['history'], [])
