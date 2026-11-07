# -*- coding: utf-8 -*-
"""Journey weather is deterministic, read-only and independent of the journal."""
import copy
import pathlib
import tempfile
import unittest

from fastapi.testclient import TestClient

from app import weather_view
from tests._legacy_world import STORY
from tests.fixtures_world import world_app


def story_with_weather():
    story = copy.deepcopy(STORY)
    story['mechanics']['weather'] = {
        'seed': 12345,
        'climate': 'maritime',
        'locations': {story['locations'][0]['id']: {'coast_distance_km': 12}},
    }
    story['locations'][0]['coordinates'] = [120.0, 25.0]
    story['locations'][0]['environment'] = {'elevation_m': 20}
    story['mechanics']['calendar'] = {'start_day_of_year': 80, 'utc_offset': 8}
    return story


class WeatherViewTests(unittest.TestCase):
    def test_time_maps_to_day_and_hour(self):
        story = story_with_weather()
        session = {'location': story['locations'][0]['id'], 'time': 49}
        report = weather_view.report(story, session, hours=6)
        self.assertEqual(report['day'], 3)
        self.assertEqual(report['hour'], 1)
        self.assertEqual(len(report['forecast']), 6)
        self.assertEqual(report['climate'], 'maritime')
        self.assertEqual(report['climate_source'], 'config')

    def test_same_inputs_give_the_same_weather(self):
        story = story_with_weather()
        session = {'location': story['locations'][0]['id'], 'time': 12}
        first = weather_view.report(story, session, hours=3)
        second = weather_view.report(story, session, hours=3)
        self.assertEqual(first, second)

    def test_missing_config_is_derived_not_guessed_from_nothing(self):
        story = copy.deepcopy(STORY)
        story['mechanics'].pop('weather', None)
        story['locations'][0].pop('coordinates', None)
        story['locations'][0].pop('environment', None)
        session = {'location': story['locations'][0]['id'], 'time': 0}
        report = weather_view.report(story, session)
        self.assertEqual(report['climate_source'], 'default')
        self.assertEqual(report['climate'], 'temperate')
        self.assertEqual(report['seed_source'], 'derived')

    def test_invalid_hours_are_clamped(self):
        story = story_with_weather()
        session = {'location': story['locations'][0]['id'], 'time': 0}
        self.assertEqual(len(weather_view.report(story, session, hours=999)['forecast']),
                         weather_view.MAX_FORECAST_HOURS)
        self.assertEqual(weather_view.report(story, session, hours=-1)['forecast'], [])


class WeatherHttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.app = world_app(pathlib.Path(self.tmp.name) / 'weather.sqlite3')
        self.service = self.app.state.service
        self.session = self.service.runtime.new_session('天气测试', 'protagonist')
        self.client = TestClient(self.app)

    def test_route_returns_current_weather_without_touching_the_save(self):
        before = self.service.store.session(self.session['id'])['state_version']
        response = self.client.get('/api/sessions/%s/weather?hours=6' % self.session['id'])
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body['enabled'])
        self.assertIn('label', body['current'])
        self.assertEqual(len(body['forecast']), 6)
        after = self.service.store.session(self.session['id'])['state_version']
        self.assertEqual(before, after)

    def test_unknown_session_is_404(self):
        response = self.client.get('/api/sessions/missing/weather')
        self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    unittest.main()
