# -*- coding: utf-8 -*-
"""Server fog: terrain-free, rough-round, never wider than the gameplay reach.

The painted clouds are drawn by the browser (``app/static/map-fog.js``); the server only
decides which basemap pixels may carry terrain and fills the rest with one flat colour.
"""
import math
import unittest

import numpy as np

from app import fog_art, map_clues, play_map

R = play_map.EARTH_RADIUS_KM
PLACES = [{'id': 'a', 'name': 'a', 'state': 'current', 'lon': 10.0, 'lat': 10.0},
          {'id': 'b', 'name': 'b', 'state': 'explored', 'lon': 14.0, 'lat': 11.0},
          {'id': 'c', 'name': 'c', 'state': 'known', 'lon': 12.0, 'lat': 6.0}]
LINK = {'reveal_radius_km': 300.0}


def frame():
    box, w, h, fog, ratio = play_map.fog_reference(PLACES, LINK)
    return box, w, h, fog, ratio, play_map.reveal_circles(PLACES, LINK)


def point_at(lon, lat, distance_km, bearing):
    d = distance_km / R
    p1, l1 = math.radians(lat), math.radians(lon)
    p2 = math.asin(math.sin(p1) * math.cos(d) + math.cos(p1) * math.sin(d) * math.cos(bearing))
    l2 = l1 + math.atan2(math.sin(bearing) * math.sin(d) * math.cos(p1),
                         math.cos(d) - math.sin(p1) * math.sin(p2))
    return math.degrees(l2), math.degrees(p2)


def server_pixels(terrain, places=PLACES, link=LINK):
    """The exact bytes basemap_png would encode for this terrain (same pipeline)."""
    circles = play_map.reveal_circles(places, link)
    box, _ = play_map.bbox_for_circles(circles + map_clues.frame_circles([]))
    w, h = play_map._crop_dimensions(box)
    mask = bytearray(w * h)
    play_map._mark_revealed(mask, circles, box, w, h)
    painted = fog_art.reference(box, w, h, circles, R)
    out, _ = fog_art.compose(terrain(w, h).tobytes(), box, w, h, circles, R, fog=painted)
    px = np.frombuffer(out, np.uint8).reshape(-1, 3).copy()
    outside = np.frombuffer(bytes(mask), np.uint8) == 0
    px[outside] = painted[0].reshape(-1, 3)[outside]
    return px, outside


class FogArtTests(unittest.TestCase):
    def test_fogged_pixels_do_not_depend_on_terrain(self):
        rng = np.random.default_rng(7)
        a, outside = server_pixels(lambda w, h: rng.integers(0, 256, (h, w, 3), dtype=np.uint8))
        b, _ = server_pixels(lambda w, h: np.full((h, w, 3), 245, np.uint8))
        _box, _w, _h, _fog, ratio, _c = frame()
        fogged = ratio.reshape(-1) >= 1.0
        self.assertGreater(fogged.mean(), 0.3)
        # Everything outside the great-circle whitelist, and everything the rough edge
        # fogs, is byte-identical whatever the terrain — and is the one flat fog colour.
        hidden = outside | fogged
        self.assertFalse((a[hidden] != b[hidden]).any(), '雾里的像素不能随地形变化')
        self.assertTrue((a[hidden] == np.array(fog_art.FOG_RGB, np.uint8)).all())
        # The revealed part does carry terrain (otherwise the map would be useless).
        self.assertTrue((a[~hidden] != b[~hidden]).any())

    def test_rough_disc_stays_inside_the_whitelist(self):
        box, w, h, _fog, ratio, circles = frame()
        mask = bytearray(w * h)
        play_map._mark_revealed(mask, circles, box, w, h)
        whitelist = np.frombuffer(bytes(mask), np.uint8).reshape(h, w) == 1
        self.assertFalse(((ratio < 1.0) & ~whitelist).any(), '粗糙边缘不能超出揭示白名单')

    def test_edge_never_reaches_beyond_the_reach(self):
        _box, _w, _h, _fog, _ratio, circles = frame()
        for circle in circles:
            for k in range(96):
                bearing = 2 * math.pi * k / 96
                lon, lat = point_at(circle['lon'], circle['lat'], circle['radius_km'] * 1.001, bearing)
                r = fog_art.reveal_ratio(np.array([[lon]]), np.array([[lat]]), [circle], R)[0, 0]
                self.assertGreaterEqual(r, 1.0, '半径之外必须是雾')
                lon, lat = point_at(circle['lon'], circle['lat'],
                                    circle['radius_km'] * (fog_art.EDGE_MIN - 0.01), bearing)
                r = fog_art.reveal_ratio(np.array([[lon]]), np.array([[lat]]), [circle], R)[0, 0]
                self.assertLess(r, 1.0, '视野至少是 EDGE_MIN 倍半径的大致圆形')

    def test_edge_is_rough_not_a_perfect_circle_and_differs_per_place(self):
        profiles = [fog_art.edge_profile(c['lon'], c['lat']) for c in frame()[5]]
        for p in profiles:
            self.assertEqual(len(p), fog_art.EDGE_SAMPLES)
            self.assertGreater(max(p) - min(p), 0.1, '边缘应有起伏')
            self.assertLessEqual(max(p), fog_art.EDGE_MAX)
            self.assertLess(fog_art.EDGE_MAX, 1.0)
            self.assertGreaterEqual(min(p), fog_art.EDGE_MIN)
        self.assertNotEqual(profiles[0], profiles[1], '不同地点的轮廓应不同')

    def test_projection_shapes_match_the_server_mask(self):
        circles = frame()[5]
        shapes = fog_art.reveal_shapes(circles)
        for c, s in zip(circles, shapes):
            self.assertEqual((s['lon'], s['lat'], s['radius_km']), (c['lon'], c['lat'], c['radius_km']))
        lon, lat = fog_art.pixel_grid(frame()[0], 120, 90)
        self.assertTrue((fog_art.reveal_ratio(lon, lat, shapes, R)
                         == fog_art.reveal_ratio(lon, lat, circles, R)).all())

    def test_deterministic(self):
        box, w, h, fog, ratio, circles = frame()
        again, ratio2 = fog_art.reference(box, w, h, circles, R)
        self.assertTrue((fog == again).all())
        self.assertTrue((ratio == ratio2).all())
        self.assertEqual(fog_art.edge_profile(10.0, 10.0), fog_art.edge_profile(10.0, 10.0))


if __name__ == '__main__':
    unittest.main()
