# -*- coding: utf-8 -*-
"""The canvas fog must never be more transparent than the server's reveal whitelist.

``app/static/map-fog.js`` is decorative, so the safety property lives in its alpha:

* ``ratio >= OPAQUE_AT`` (0.985) must be fully opaque - hard rule;
* ``ratio >= 1`` (outside the rough reveal discs) must also be fully opaque - stricter;
* pixels inside the discs may be transparent or partly opaque (the cloud edge only pulls
  the visible area *inwards*);
* nothing at all is painted outside the basemap rectangle.

The probe (``tests/fog_alpha_probe.cjs``) runs the real drawing code in a headless Node
sandbox with a mock canvas, over three regions x zoom 1/2 x one/all reveal discs x
device pixel ratio 1/2.
"""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FOG_JS = ROOT / 'app' / 'static' / 'map-fog.js'
REGIONS = ROOT / 'app' / 'static' / 'map-art' / 'fog-fixtures' / 'regions.json'
PROBE = ROOT / 'tests' / 'fog_alpha_probe.cjs'


@unittest.skipUnless(shutil.which('node'), 'node is not installed')
class FogAlphaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        proc = subprocess.run(['node', str(PROBE), str(FOG_JS), str(REGIONS), '1,2'],
                              cwd=str(ROOT), capture_output=True, text=True,
                              encoding='utf-8', errors='replace', timeout=600)
        if proc.returncode != 0:
            raise AssertionError('fog probe failed: %s%s' % (proc.stdout, proc.stderr))
        cls.rows = json.loads(proc.stdout)

    def _each(self):
        for row in self.rows:
            with self.subTest(region=row['region'], zoom=row['zoom'], dpr=row['dpr'],
                              discs=row['discs']):
                yield row

    def test_covers_zoom_and_disc_count(self):
        zooms = {row['zoom'] for row in self.rows}
        dprs = {row['dpr'] for row in self.rows}
        discs = {row['discs'] for row in self.rows}
        self.assertEqual(zooms, {1, 2})
        self.assertEqual(dprs, {1, 2})
        self.assertGreaterEqual(len(discs), 2, '单圆与多圆都要覆盖')

    def test_hard_rule_opaque_from_opaque_at(self):
        for row in self._each():
            self.assertGreater(row['hardFogged'], 0)
            self.assertEqual(row['hardOpaque'], row['hardFogged'], row['bad'])

    def test_stricter_rule_opaque_from_ratio_one(self):
        for row in self._each():
            self.assertEqual(row['softOpaque'], row['softFogged'], row['bad'])

    def test_nothing_is_painted_outside_the_basemap(self):
        for row in self._each():
            self.assertEqual(row['outsideRectPainted'], 0)

    def test_clouds_stay_inside_the_reveal(self):
        # 雾边只向内收：可见区里只有贴边那一圈被雾盖住，大部分地图像素仍暴露给底图。
        for row in self._each():
            self.assertLess(row['insideCoveredPct'], 50,
                            '雾把可见区盖得太多了：%d%%' % row['insideCoveredPct'])


if __name__ == '__main__':
    unittest.main()
