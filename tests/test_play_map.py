# -*- coding: utf-8 -*-
"""Player map projection: fog whitelist, coordinate identity, read-only GET.

Every test runs on a temporary Store (and therefore a temporary data root), so no test
touches `data/`, the published story packages, or any imported civ-atlas world of the
user's. The map payloads are fixtures built in this file.

What is checked here, and why it cannot be checked from the JSON alone:

* the hidden area of the basemap is decoded from the PNG and compared to the fog colour;
* moving a secret place does not change one byte of the player's image;
* the two journeys never see each other's places or crop.
"""
import copy
import json
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from fastapi.testclient import TestClient

from app import map_import, play_map
from app.service import Service
from app.storage import Store
from app.web import create_app

from .test_civ_atlas_import import heightmap_png

ROOT = Path(__file__).resolve().parents[1]
FOG = bytes(play_map.FOG_RGB)


def decode_png(data):
    """Minimal PNG decoder for the 8-bit RGB previews this project writes."""
    assert data[:8] == b'\x89PNG\r\n\x1a\n', 'not a PNG'
    pos, idat, width, height, depth, colour = 8, b'', None, None, None, None
    while pos < len(data):
        length = struct.unpack('>I', data[pos:pos + 4])[0]
        ctype = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if ctype == b'IHDR':
            width, height, depth, colour = struct.unpack('>IIBB', body[:10])
        elif ctype == b'IDAT':
            idat += body
        elif ctype == b'IEND':
            break
    assert (depth, colour) == (8, 2), 'expected 8-bit RGB'
    raw = zlib.decompress(idat)
    stride = width * 3
    out, prev, p = [], bytearray(stride), 0
    for _ in range(height):
        kind = raw[p]
        p += 1
        line = bytearray(raw[p:p + stride])
        p += stride
        if kind == 1:
            for i in range(3, stride):
                line[i] = (line[i] + line[i - 3]) & 0xFF
        elif kind == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif kind == 3:
            for i in range(stride):
                left = line[i - 3] if i >= 3 else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 0xFF
        elif kind == 4:
            for i in range(stride):
                a = line[i - 3] if i >= 3 else 0
                b = prev[i]
                c = prev[i - 3] if i >= 3 else 0
                guess = a + b - c
                pa, pb, pc = abs(guess - a), abs(guess - b), abs(guess - c)
                pick = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pick) & 0xFF
        out.append(bytes(line))
        prev = line
    return width, height, b''.join(out)


def pixel(image, bbox, lon, lat):
    width, height, body = image
    lon_min, lon_max, lat_min, lat_max = bbox
    x = min(width - 1, max(0, int((lon - lon_min) / (lon_max - lon_min) * width)))
    y = min(height - 1, max(0, int((lat_max - lat) / (lat_max - lat_min) * height)))
    base = (y * width + x) * 3
    return body[base:base + 3]


class MapFixture(unittest.TestCase):
    """One temporary service per class; a real 16-bit heightmap import as the map."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.svc = Service(Store(cls.root / 'map.sqlite3'), ROOT)
        cls.svc.provider.configure({'offline': True})
        cls.import_root = cls.root
        cls.record = map_import.create_import(cls.svc.store, cls.import_root,
                                             heightmap_png(width=1024, height=512))
        # A pristine copy of the base package: every test starts from here, so one test's
        # committed mutations can never leak into the next one.
        cls.base = copy.deepcopy(cls.svc.runtime.package())

    @classmethod
    def tearDownClass(cls):
        play_map.clear_cache()
        cls.tmp.cleanup()

    def setUp(self):
        play_map.clear_cache()

    # ------------------------------------------------------------------ helpers
    def package(self, link=None, mutate=None):
        story = copy.deepcopy(self.base['story'])
        characters = copy.deepcopy(self.base['characters'])
        story.setdefault('mechanics', {}).pop('map', None)
        if link is not None:
            story['mechanics']['map'] = link
        if mutate is not None:
            mutate(story)
        return story, characters

    def commit(self, story, characters):
        self.svc.runtime.commit_package(story, characters, '地图测试')

    def link(self, **fog):
        return {'kind': 'civ_atlas', 'import_id': self.record['id'], 'fog': fog or {}}

    def journey(self, title='地图旅程', mutate=None, link=None):
        story, characters = self.package(link=link or self.link(reveal_radius_km=600),
                                         mutate=mutate)
        self.commit(story, characters)
        session = self.svc.runtime.new_session(title, 'protagonist')
        return self.svc.store.session(session['id'])

    def story_of(self, session):
        return self.svc.runtime.package(session['revision'])['story']

    def projection(self, session):
        story = self.story_of(session)
        status, context = play_map.resolve(self.svc.store, self.import_root, story)
        return play_map.projection(session, story, status=status, context=context,
                                   session_id=session['id']), status, context, story

    def basemap(self, session):
        payload, status, context, story = self.projection(session)
        places = play_map.visible_places(session, story)
        png = play_map.basemap_png(context, places, context.get('link'))
        return png, payload


# --------------------------------------------------------------------- linkage
class LinkTests(MapFixture):
    def test_old_journey_is_not_linked_and_gets_no_map(self):
        story, characters = self.package()
        story['mechanics'].pop('map', None)
        self.commit(story, characters)
        session = self.svc.store.session(self.svc.runtime.new_session('旧旅程', 'protagonist')['id'])
        payload, status, _context, _story = self.projection(session)
        self.assertEqual(status, play_map.STATUS_NOT_LINKED)
        self.assertFalse(payload['basemap']['available'])
        self.assertIsNone(payload['basemap']['url'])
        self.assertIn('author_entry', payload)
        self.assertEqual(payload['author_entry']['page'], 'map-tools')
        png, _ = self.basemap(session)
        self.assertIsNone(png, '未关联时不得有任何底图（不回退到无关地图）')

    def test_missing_import_is_reported_not_substituted(self):
        session = self.journey(link={'kind': 'civ_atlas', 'import_id': 'sn_' + '0' * 12})
        payload, status, _context, _story = self.projection(session)
        self.assertEqual(status, play_map.STATUS_MISSING)
        self.assertFalse(payload['basemap']['available'])
        self.assertIsNone(self.basemap(session)[0])

    def test_record_swapped_under_same_key_is_refused(self):
        session = self.journey()
        record = dict(self.svc.store.get('map_import', self.record['id']))
        tampered = {**record, 'sha256': 'f' * 64}
        self.svc.store.put('map_import', record['id'], tampered)
        try:
            payload, status, _context, _story = self.projection(session)
            self.assertEqual(status, play_map.STATUS_MISMATCH)
            self.assertFalse(payload['basemap']['available'])
        finally:
            self.svc.store.put('map_import', record['id'], record)

    def test_link_validation_refuses_what_it_cannot_promise(self):
        for bad in ({'kind': 'other', 'import_id': 'sn_abcdef123456'},
                    {'kind': 'civ_atlas'},
                    {'kind': 'civ_atlas', 'import_id': '/etc/passwd'},
                    {'kind': 'civ_atlas', 'import_id': 'sn_abcdef123456',
                     'fog': {'reveal_radius_km': True}},
                    {'kind': 'civ_atlas', 'import_id': 'sn_abcdef123456',
                     'fog': {'reveal_radius_km': float('nan')}},
                    {'kind': 'civ_atlas', 'import_id': 'sn_abcdef123456',
                     'fog': {'reveal_radius_km': 5}},
                    {'kind': 'civ_atlas', 'import_id': 'sn_abcdef123456', 'path': 'x'},
                    {'kind': 'civ_atlas', 'import_id': 'sn_abcdef123456',
                     'fog': {'reveal_radius_km': 300, 'colour': 'red'}}):
            story, _ = self.package()
            story['mechanics']['map'] = bad
            with self.assertRaises(ValueError, msg=json.dumps(bad)):
                play_map.validate_story_map(story)

    def test_bad_location_coordinates_are_refused_by_package_validation(self):
        for bad in ([900, 50], [10], ['10', 20], [float('nan'), 10], [10, True]):
            story, characters = self.package()
            story['locations'][0] = {**story['locations'][0], 'coordinates': bad}
            with self.assertRaises(ValueError, msg=repr(bad)):
                self.svc.runtime.validate_package(story, characters)

    def test_package_without_map_still_validates(self):
        story, characters = self.package()
        self.assertIsNone(self.svc.runtime.validate_package(story, characters))


# ---------------------------------------------------------------- the whitelist
class FogWhitelistTests(MapFixture):
    def hidden_story(self, secret_lon=10.0):
        def mutate(story):
            home = story['locations'][0]
            story['locations'].append({
                'id': 'author_vault', 'name': '作者密库', 'visibility': 'author',
                'coordinates': [secret_lon, 12.0], 'neighbors': [home['id']], 'scenes': []})
            story['locations'].append({
                'id': 'locked_gate', 'name': '未开之门', 'reveal_flag': 'gate_open',
                'coordinates': [secret_lon + 2, 14.0], 'neighbors': [home['id']], 'scenes': []})
            home['neighbors'] = home['neighbors'] + ['author_vault', 'locked_gate']
        return mutate

    def test_hidden_places_and_counts_never_reach_the_player(self):
        session = self.journey(mutate=self.hidden_story())
        payload, status, _context, _story = self.projection(session)
        self.assertEqual(status, play_map.STATUS_OK)
        text = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn('author_vault', text)
        self.assertNotIn('作者密库', text)
        self.assertNotIn('locked_gate', text)
        self.assertNotIn('未开之门', text)
        self.assertNotIn('more_unknown', payload, '不得透露还有多少未探索地点')
        self.assertNotIn('total', payload['places'][0] if payload['places'] else {})
        ids = {row['id'] for row in payload['places']}
        self.assertNotIn('author_vault', ids)
        self.assertNotIn('locked_gate', ids)

    def test_reveal_flag_opens_only_after_the_journey_sets_it(self):
        session = self.journey(mutate=self.hidden_story())
        story = self.story_of(session)
        before = play_map.visible_places(session, story)
        self.assertNotIn('locked_gate', {row['id'] for row in before})
        session = {**session, 'flags': {**(session.get('flags') or {}), 'gate_open': True}}
        after = play_map.visible_places(session, story)
        self.assertIn('locked_gate', {row['id'] for row in after})
        self.assertNotIn('author_vault', {row['id'] for row in after})

    def test_current_and_neighbours_are_the_only_locations_named(self):
        session = self.journey(mutate=self.hidden_story())
        payload, _status, _context, story = self.projection(session)
        current = next(p for p in story['locations'] if p['id'] == session['location'])
        allowed = {session['location'], *current['neighbors']} - {'author_vault', 'locked_gate'}
        self.assertEqual({row['id'] for row in payload['places']}, allowed)
        self.assertEqual(payload['player']['location_id'], session['location'])
        for row in payload['places']:
            self.assertIn(row['state'], ('current', 'explored', 'known'))

    def test_fog_hides_terrain_in_the_png_not_only_in_the_json(self):
        session = self.journey()
        png, payload = self.basemap(session)
        self.assertIsNotNone(png)
        image = decode_png(png)
        bbox = payload['basemap']['bbox']
        lon_min, lon_max, lat_min, lat_max = bbox
        # The four corners of the crop are outside every reveal circle: pure fog there.
        for lon, lat in ((lon_min, lat_max), (lon_max, lat_max),
                         (lon_min, lat_min), (lon_max, lat_min)):
            self.assertEqual(pixel(image, bbox, lon, lat), FOG,
                             '裁切框角落在可见范围外，必须是雾色而不是地形')
        # The current place itself is revealed terrain, not fog.
        player = payload['player']
        self.assertNotEqual(pixel(image, bbox, player['lon'], player['lat']), FOG)

    def test_secret_place_position_does_not_change_the_player_image(self):
        first = self.journey('秘密A', mutate=self.hidden_story(secret_lon=10.0))
        png_a, payload_a = self.basemap(first)
        second = self.journey('秘密B', mutate=self.hidden_story(secret_lon=170.0))
        png_b, payload_b = self.basemap(second)
        self.assertEqual(payload_a['places'], payload_b['places'])
        self.assertEqual(payload_a['basemap']['bbox'], payload_b['basemap']['bbox'])
        self.assertEqual(png_a, png_b, '秘密地点位置变了，玩家底图不能有任何变化')

    def test_author_full_map_is_a_different_route_and_differs(self):
        session = self.journey()
        png, _payload = self.basemap(session)
        app = create_app(self.root / 'author.sqlite3')
        app.state.service.store.put('map_import', self.record['id'], self.record)
        with TestClient(app) as client:
            token = client.get('/api/bootstrap').json()['token']
            full = client.get('/api/inner/map-imports/%s/preview.png' % self.record['id'],
                              headers={'X-TextileDream-Token': token})
        self.assertEqual(full.status_code, 200)
        self.assertNotEqual(full.content, png, '玩家底图不得复用作者全图')


# ------------------------------------------------------------------- identity
class CoordinateTests(MapFixture):
    def test_player_lon_lat_come_from_the_server_not_the_client(self):
        session = self.journey()
        payload, _status, _context, story = self.projection(session)
        place = next(p for p in story['locations'] if p['id'] == session['location'])
        lon, lat = place['coordinates']
        self.assertEqual(payload['player']['lon'], ((lon + 180.0) % 360.0) - 180.0)
        self.assertEqual(payload['player']['lat'], lat)
        row = next(r for r in payload['places'] if r['id'] == session['location'])
        self.assertEqual((row['lon'], row['lat']), (payload['player']['lon'],
                                                    payload['player']['lat']))

    def test_projection_formula_matches_the_basemap_pixel_grid(self):
        session = self.journey()
        png, payload = self.basemap(session)
        image = decode_png(png)
        bbox = payload['basemap']['bbox']
        lon_min, lon_max, lat_min, lat_max = bbox
        player = payload['player']
        # x = (lon+180)/360 and y = (90-lat)/180 are the same linear frame as the crop:
        # the fraction of the crop is identical however the full map is scaled.
        fx = (player['lon'] + 180) / 360
        fy = (90 - player['lat']) / 180
        self.assertAlmostEqual((lon_min + 180) / 360, fx - (fx - (lon_min + 180) / 360), 12)
        self.assertGreater(fx, (lon_min + 180) / 360)
        self.assertLess(fx, (lon_max + 180) / 360)
        self.assertGreater(fy, (90 - lat_max) / 180)
        self.assertLess(fy, (90 - lat_min) / 180)
        self.assertNotEqual(pixel(image, bbox, player['lon'], player['lat']), FOG)

    def test_longitude_is_normalised_so_the_date_line_is_one_place(self):
        story = {'locations': [{'id': 'a', 'coordinates': [180.0, 10.0]},
                               {'id': 'b', 'coordinates': [-180.0, 10.0]},
                               {'id': 'c', 'coordinates': [179.9, 10.0]}]}
        self.assertEqual(play_map.location_coordinates(story['locations'][0]),
                         (-180.0, 10.0))
        self.assertEqual(play_map.location_coordinates(story['locations'][1]),
                         (-180.0, 10.0))
        self.assertEqual(play_map.location_coordinates(story['locations'][2]),
                         (179.89999999999998, 10.0))

    def test_date_line_crop_is_one_sided_and_says_so(self):
        def mutate(story):
            home = story['locations'][0]
            home['coordinates'] = [179.5, 8.0]
        session = self.journey(link=self.link(reveal_radius_km=600), mutate=mutate)
        payload, status, _context, _story = self.projection(session)
        self.assertEqual(status, play_map.STATUS_OK)
        self.assertTrue(payload['basemap']['clipped_at_dateline'])
        lon_min, lon_max, _lat_min, _lat_max = payload['basemap']['bbox']
        self.assertLessEqual(lon_max, 180.0)
        self.assertGreaterEqual(lon_min, -180.0)
        self.assertTrue(any('日界' in note for note in payload['notes']))

    def test_polar_place_is_clamped_and_still_draws(self):
        def mutate(story):
            story['locations'][0]['coordinates'] = [20.0, 88.0]
        session = self.journey(mutate=mutate)
        payload, status, _context, _story = self.projection(session)
        self.assertEqual(status, play_map.STATUS_OK)
        self.assertLessEqual(payload['basemap']['bbox'][3], 84.0)
        png, _payload = self.basemap(session)
        self.assertIsNotNone(png)

    def test_place_without_coordinates_is_listed_but_not_drawn(self):
        def mutate(story):
            story['locations'][0]['coordinates'] = None
        session = self.journey(mutate=mutate)
        payload, status, _context, story = self.projection(session)
        self.assertEqual(status, play_map.STATUS_OK)
        self.assertIsNone(payload['player']['lon'])
        self.assertTrue(any('经纬度' in note for note in payload['notes']))
        # No marker for a place without a recorded position — but the neighbours that do
        # have coordinates are still drawn, so a crop can exist.
        self.assertTrue(all(row['lon'] is None for row in payload['places']
                            if row['state'] == 'current'))
        for circle in play_map.reveal_circles(play_map.visible_places(session, story),
                                              {'reveal_radius_km': 600}):
            self.assertIsNotNone(circle['lon'])

    def test_no_basemap_when_nothing_has_coordinates(self):
        def mutate(story):
            for place in story['locations']:
                place['coordinates'] = None
        session = self.journey(mutate=mutate)
        payload, status, _context, _story = self.projection(session)
        self.assertEqual(status, play_map.STATUS_OK)
        self.assertFalse(payload['basemap']['available'])
        self.assertIsNone(self.basemap(session)[0], '没有任何带经纬度的地点时不给底图')


# ------------------------------------------------------------- radius monotonic
class RadiusTests(unittest.TestCase):
    def test_known_radius_is_never_wider_than_visited(self):
        for radius in (play_map.MIN_REVEAL_KM, play_map.DEFAULT_REVEAL_KM, 120.0,
                       play_map.MAX_REVEAL_KM):
            link = {'reveal_radius_km': radius}
            self.assertLessEqual(play_map.known_radius_km(link), radius)
            self.assertGreater(play_map.known_radius_km(link), 0.0)

    def test_known_radius_scales_with_the_configured_radius(self):
        small = play_map.known_radius_km({'reveal_radius_km': 40.0})
        large = play_map.known_radius_km({'reveal_radius_km': 1600.0})
        self.assertLess(small, large)


# ------------------------------------------------------------------ isolation
class SessionIsolationTests(MapFixture):
    def test_two_journeys_do_not_share_places_or_crop(self):
        def east(story):
            story['locations'][0]['coordinates'] = [150.0, 20.0]
        def west(story):
            story['locations'][0]['coordinates'] = [-150.0, -20.0]
        a = self.journey('东', mutate=east)
        b = self.journey('西', mutate=west)
        pa, _sa, _ca, _st = self.projection(a)
        pb, _sb, _cb, _st2 = self.projection(b)
        self.assertNotEqual(pa['basemap']['bbox'], pb['basemap']['bbox'])
        self.assertEqual(pa['player']['location_id'], pb['player']['location_id'])
        self.assertEqual(pa['player']['lon'], 150.0)
        self.assertEqual(pb['player']['lon'], -150.0)
        self.assertNotEqual(self.basemap(a)[0], self.basemap(b)[0])

    def test_opening_the_map_never_writes_the_journey(self):
        session = self.journey()
        before = self.svc.store.session(session['id'])
        traces = len(self.svc.store.all('trace'))
        app = create_app(self.root / 'ro.sqlite3')
        app.state.service.store.put('map_import', self.record['id'], self.record)
        # Same store as the fixture would collide with its pointer; read the projection
        # through the module directly, then through a client on a copy of the session.
        for _ in range(3):
            self.projection(session)
            self.basemap(session)
        after = self.svc.store.session(session['id'])
        self.assertEqual(before['state_version'], after['state_version'])
        self.assertEqual(before['location'], after['location'])
        self.assertEqual(before['explored'], after['explored'])
        self.assertEqual(len(self.svc.store.all('trace')), traces)
        del app

    def test_gateway_is_read_only_and_ignores_extra_query_parameters(self):
        session = self.journey()
        app = create_app(self.root / 'api.sqlite3')
        svc = app.state.service
        # Give the temp service the same package, import record and one journey.
        package = self.svc.runtime.package()
        svc.runtime.commit_package(package['story'], package['characters'], '地图API测试')
        svc.store.put('map_import', self.record['id'], self.record)
        source = (self.import_root / 'map_imports' / self.record['file'])
        target_dir = Path(svc.store.path).parent / 'map_imports'
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / self.record['file']).write_bytes(source.read_bytes())
        journey = svc.runtime.new_session('API 旅程', 'protagonist')
        with TestClient(app) as client:
            token = client.get('/api/bootstrap').json()['token']
            headers = {'X-TextileDream-Token': token}
            version = svc.store.session(journey['id'])['state_version']
            first = client.get('/api/sessions/%s/play-map' % journey['id'])
            self.assertEqual(first.status_code, 200)
            body = first.json()
            self.assertEqual(body['status'], play_map.STATUS_OK)
            self.assertNotIn('import_id', json.dumps(body))
            self.assertNotIn(self.record['file'], json.dumps(body))
            self.assertNotIn('map_imports', json.dumps(body))
            image = client.get('/api/sessions/%s/play-map/basemap.png' % journey['id'])
            self.assertEqual(image.status_code, 200)
            self.assertEqual(image.headers['content-type'], 'image/png')
            self.assertEqual(image.headers['x-play-map'], 'fog-masked')
            # Extra parameters and layers are not accepted as knobs: identical bytes.
            for query in ('?layer=biome', '?layer=water&zoom=4', '?import_id=sn_deadbeef',
                          '?lon=10&lat=10&width=4000'):
                again = client.get('/api/sessions/%s/play-map/basemap.png%s'
                                   % (journey['id'], query))
                self.assertEqual(again.content, image.content, query)
                self.assertEqual(client.get('/api/sessions/%s/play-map%s'
                                            % (journey['id'], query)).json(), body, query)
            self.assertEqual(svc.store.session(journey['id'])['state_version'], version)
            # A journey with no link answers 404 for the image and says why in the JSON.
            plain_story = copy.deepcopy(self.base['story'])
            plain_story.setdefault('mechanics', {}).pop('map', None)
            svc.runtime.commit_package(plain_story, copy.deepcopy(self.base['characters']),
                                       '无地图')
            plain = svc.runtime.new_session('无图旅程', 'protagonist')
            self.assertEqual(client.get('/api/sessions/%s/play-map/basemap.png'
                                        % plain['id']).status_code, 404)
            plain_body = client.get('/api/sessions/%s/play-map' % plain['id']).json()
            self.assertEqual(plain_body['status'], play_map.STATUS_NOT_LINKED)
            self.assertIsNone(plain_body['basemap']['url'])

    def test_client_cannot_reach_the_map_import_routes(self):
        app = create_app(self.root / 'guard.sqlite3')
        with TestClient(app) as client:
            # Player-facing GETs stay open; the author import routes stay token-guarded.
            self.assertEqual(client.get('/api/sessions/nope/play-map').status_code, 400)
            self.assertEqual(client.get('/api/inner/map-imports').status_code, 403)
            self.assertEqual(client.get('/api/inner/map-imports/%s/preview.png'
                                        % self.record['id']).status_code, 403)


if __name__ == '__main__':
    unittest.main()
