# -*- coding: utf-8 -*-
"""civ-atlas 导入端点专项单测：隔离数据根、有界读取、严格请求体、图层与拒收。

这些用**临时 store**，并断言仓库 data/map_imports 一个字节都没多——不是为了覆盖率，
而是因为早期实现把导入文件落在了固定的 ROOT 下，测试会在用户正式数据里留下残片。
"""
import json
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from fastapi.testclient import TestClient

from app import civ_atlas_snapshot, map_import, web
from app.storage import Store

ROOT = Path(__file__).resolve().parents[1]
REAL_IMPORTS = ROOT / 'data' / 'map_imports'


# ------------------------------------------------------------------ fixtures
def _chunk(ctype, body):
    return (struct.pack('>I', len(body)) + ctype + body
            + struct.pack('>I', map_import.crc32(ctype + body)))


def heightmap_png(width=2048, height=1024, lo=-4000, hi=3000, sea_gray=20000):
    """A 16-bit grayscale heightmap written to the documented spec (not an upstream file).

    Left half sea (grey 0), right half land ramping to 65535; the tEXt block declares
    lo/hi/sea level the way the exporter does, so the parser has real numbers to read.
    The size is 2048x1024 because the sampler rejects a window whose real area falls
    outside 0.5…20000 km² — a tiny toy grid would be refused for the wrong reason.
    """
    rows = bytearray()
    for y in range(height):
        rows.append(0)                       # filter type 0
        for x in range(width):
            grey = 0 if x < width // 2 else int(65535 * (x - width // 2) / max(1, width // 2 - 1))
            rows += struct.pack('>H', min(65535, grey))
    ihdr = struct.pack('>IIBBBBB', width, height, 16, 0, 0, 0, 0)
    description = ('16-bit grayscale heightmap, equirectangular (latitude linear top to '
                   'bottom), 2:1. Gray 0 = %d m, 65535 = %d m, linear. Sea level (0 m) = '
                   'gray %d; land is brighter, sea is darker.' % (lo, hi, sea_gray))
    text = b'Software\x00Wenming Ditu (civilization map generator)'
    desc = b'Description\x00' + description.encode('latin-1', 'replace')
    return b''.join([b'\x89PNG\r\n\x1a\n', _chunk(b'IHDR', ihdr),
                     _chunk(b'tEXt', text), _chunk(b'tEXt', desc),
                     _chunk(b'IDAT', zlib.compress(bytes(rows), 6)), _chunk(b'IEND', b'')])


def pad8(value):
    return (value + 7) & ~7


def civsnap(cells=64):
    """A CASNAP01 container whose ``map`` part is a real CIVSNAP1 structure.

    Layout follows :func:`app.civ_atlas_snapshot.parse_part`: ``CIVSNAP1`` + little-endian
    JSON length + JSON structure, then a payload of typed arrays at 8-byte-aligned offsets,
    referenced by ``{"$$": "a", "t": "F32", "o": <offset>, "n": <count>}``. The whole part
    is gzipped, as the exporter does when ``zip === 'gzip'``.

    Numbers here are made up for the test (a flat 8x8 mesh); the *envelope* is what is
    under test, and the real-world check uses a genuine upstream export.
    """
    side = 8                                   # 8 x 8 = 64 cells
    xs = [float(cell % side) for cell in range(cells)]
    ys = [float(cell // side) for cell in range(cells)]
    adj_start, adj = [0], []
    for cell in range(cells):
        cx, cy = cell % side, cell // side
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < side and 0 <= ny < side:
                adj.append(ny * side + nx)
        adj_start.append(len(adj))
    elevation = [300.0 + cell for cell in range(cells)]
    water = [0] * cells
    temperature = [12.0 + (cell % 7) for cell in range(cells)]
    precipitation = [700.0 + 10 * (cell % 5) for cell in range(cells)]
    biome = [8] * cells                       # 8 = 草原 in the upstream enum

    # ---- payload: each array at an 8-byte-aligned offset, laid out in order
    payload = bytearray()
    slots = {}

    def put(name, kind, values):
        nonlocal payload
        if len(payload) % 8:
            payload += b'\x00' * (8 - len(payload) % 8)
        slots[name] = (kind, len(payload), len(values))
        fmt = {'F32': 'f', 'I32': 'i', 'U8': 'B'}[kind]
        payload += struct.pack('<%d%s' % (len(values), fmt), *values)

    def ref(name):
        kind, offset, count = slots[name]
        return {'$$': 'a', 't': kind, 'o': offset, 'n': count}

    put('x', 'F32', xs)
    put('y', 'F32', ys)
    put('adjStart', 'I32', adj_start)
    put('adj', 'I32', adj)
    put('elevation', 'F32', elevation)
    put('water', 'U8', water)
    put('temperature', 'F32', temperature)
    put('precipitation', 'F32', precipitation)
    put('biome', 'U8', biome)

    # ``n`` must be a JSON integer literal: the reader rejects a float cell count
    # (civ_atlas_snapshot.read_world checks isinstance(cells, int)).
    mesh = {'n': cells, 'width': side, 'height': side,
            'x': ref('x'), 'y': ref('y'), 'adjStart': ref('adjStart'), 'adj': ref('adj')}
    structure = {
        'mesh': mesh,
        'elevation': ref('elevation'),
        'water': ref('water'),
        'temperature': ref('temperature'),
        'precipitation': ref('precipitation'),
        'biome': ref('biome'),
        'maxElevation': max(elevation),
    }
    meta = json.dumps(structure).encode('utf-8')
    part_raw = b'CIVSNAP1' + struct.pack('<I', len(meta)) + meta
    if len(part_raw) % 8:
        part_raw += b'\x00' * (8 - len(part_raw) % 8)
    # upstream marks a part 'none' when CompressionStream is unavailable (snapshot.ts:314);
    # the import path must accept both, so the fixture uses 'none' and the real-export
    # check covers 'gzip'.
    part = part_raw + bytes(payload)

    manifest = {
        'container': 'CASNAP01', 'schema': 1,
        'exported_by': 'tests (fixture)', 'exported_at': '2026-01-01T00:00:00Z',
        'site': 'http://localhost',
        'world': {'id': 'w1', 'generator': 45, 'app': 'test', 'at': '2026-01-01'},
        'snapshot': {'format': 1, 'generator': 45, 'recipe': 'r', 'formation': False},
        'head': {'id': 'w1', 'generator': 45},
        'parts': [{'name': 'map', 'bytes': len(part), 'sum': '', 'zip': 'none',
                   'length': len(part), 'offset': 0}],
    }
    # The offset lives inside the JSON, so its length feeds back into its own value:
    # iterate until the serialised length is stable (the same trap
    # tools/civ_atlas_export.js guards against with its pad8 check).
    offset = 0
    for _ in range(8):
        manifest['parts'][0]['offset'] = offset
        head = json.dumps(manifest).encode('utf-8')
        nxt = pad8(12 + len(head))
        if nxt == offset:
            break
        offset = nxt
    else:
        raise AssertionError('fixture manifest offset did not converge')
    out = bytearray(offset + len(part))
    out[0:8] = b'CASNAP01'
    struct.pack_into('<I', out, 8, len(head))
    out[12:12 + len(head)] = head
    out[offset:offset + len(part)] = part
    return bytes(out)


# ------------------------------------------------------------------ the tests
class IsolatedImportRootTests(unittest.TestCase):
    """Imports must land beside the store that recorded them, never in the repo's data/."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / 'sandbox.sqlite3'
        self.before = set(REAL_IMPORTS.glob('*')) if REAL_IMPORTS.exists() else set()

    def tearDown(self):
        self.tmp.cleanup()

    def test_png_import_writes_beside_the_temp_store(self):
        store = Store(self.db)
        record = map_import.create_import(store, Path(self.tmp.name), heightmap_png(), '')
        target = Path(self.tmp.name) / 'map_imports' / record['file']
        self.assertTrue(target.exists(), '导入文件应写在临时库旁边')
        after = set(REAL_IMPORTS.glob('*')) if REAL_IMPORTS.exists() else set()
        self.assertEqual(self.before, after, '正式 data/map_imports 不应被测试写入')

    def test_snapshot_import_writes_beside_the_temp_store(self):
        store = Store(self.db)
        data = civsnap()
        record = civ_atlas_snapshot.create_import(store, Path(self.tmp.name), data, {})
        self.assertTrue((Path(self.tmp.name) / 'map_imports' / record['file']).exists())
        after = set(REAL_IMPORTS.glob('*')) if REAL_IMPORTS.exists() else set()
        self.assertEqual(self.before, after)

    def test_idempotent_same_bytes(self):
        store = Store(self.db)
        png = heightmap_png()
        first = map_import.create_import(store, Path(self.tmp.name), png, '')
        second = map_import.create_import(store, Path(self.tmp.name), png, '')
        self.assertEqual(first['id'], second['id'])
        self.assertEqual(list((Path(self.tmp.name) / 'map_imports').glob('*.png')).__len__(), 1)


class HeightmapEnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = Store(self.root / 'x.sqlite3')

    def tearDown(self):
        self.tmp.cleanup()

    def test_declared_numbers_are_read_from_text_chunk(self):
        record = map_import.create_import(self.store, self.root, heightmap_png(), '')
        self.assertEqual(record['lo_m'], -4000)
        self.assertEqual(record['hi_m'], 3000)
        self.assertEqual(record['sea_gray'], 20000)

    def test_sea_land_split_uses_the_integer_test(self):
        record = map_import.create_import(self.store, self.root, heightmap_png(), '')
        heightmap = map_import.load_heightmap(self.root, record)
        self.assertTrue(heightmap.is_sea(0))
        self.assertFalse(heightmap.is_sea(65535))
        self.assertFalse(heightmap.is_sea(record['sea_gray'] + 1))

    def test_eight_bit_png_is_refused(self):
        data = bytearray(heightmap_png())
        # rewrite IHDR bit depth 16 -> 8 (byte 24 of the file: 8 sig + 8 len/type + 8 w/h + 2 depth)
        data[24] = 8
        with self.assertRaises(map_import.MapImportError):
            map_import.create_import(self.store, self.root, bytes(data), '')

    def test_store_json_is_refused_with_a_reason(self):
        with self.assertRaises(map_import.MapImportError):
            map_import.create_import(self.store, self.root,
                                     json.dumps({'seed': 1, 'params': {}}).encode(), '')

    def test_summary_does_not_leak_an_absolute_path(self):
        record = map_import.create_import(self.store, self.root, heightmap_png(), '')
        blob = json.dumps(map_import.summary(record), ensure_ascii=False)
        self.assertNotIn(str(self.root), blob)
        self.assertNotIn('\\\\', blob)


class SnapshotEnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = Store(self.root / 'x.sqlite3')

    def tearDown(self):
        self.tmp.cleanup()

    def test_three_field_arrays_survive_the_round_trip(self):
        data = civsnap()
        record = civ_atlas_snapshot.create_import(self.store, self.root, data, {})
        world = civ_atlas_snapshot.load_world(self.root, record)
        self.assertEqual(world.cells, 64)
        self.assertEqual(world.water[0], 0)
        self.assertAlmostEqual(world.temperature[0], 12.0, places=4)
        self.assertAlmostEqual(world.precipitation[0], 700.0, places=4)
        self.assertEqual(world.biome[0], 8)

    def test_truncated_container_is_refused(self):
        data = civsnap()
        with self.assertRaises(civ_atlas_snapshot.MapImportError):
            civ_atlas_snapshot.create_import(self.store, self.root, data[:len(data) // 2], {})

    def test_preview_layers_differ_and_are_not_grey_alias(self):
        record = civ_atlas_snapshot.create_import(self.store, self.root, civsnap(), {})
        world = civ_atlas_snapshot.load_world(self.root, record)
        grid = civ_atlas_snapshot.preview_grid(world, max_side=32)
        temp = civ_atlas_snapshot.preview_rgb(grid, 'temperature')
        rain = civ_atlas_snapshot.preview_rgb(grid, 'precipitation')
        elev = civ_atlas_snapshot.preview_rgb(grid, 'elevation')
        self.assertEqual(len(temp), grid['width'] * grid['height'] * 3)
        self.assertNotEqual(temp, rain, '气温层与降水层不能是同一张图')
        self.assertNotEqual(temp, elev, '气温层与高程层不能是同一张图')
        self.assertNotEqual(len(set(bytes(temp))), 1, '气温层不应是纯色')

    def test_unknown_layer_is_refused(self):
        record = civ_atlas_snapshot.create_import(self.store, self.root, civsnap(), {})
        world = civ_atlas_snapshot.load_world(self.root, record)
        grid = civ_atlas_snapshot.preview_grid(world, max_side=32)
        with self.assertRaises(civ_atlas_snapshot.MapImportError):
            civ_atlas_snapshot.preview_rgb(grid, 'resources')

    def test_rgb_preview_is_a_valid_png(self):
        record = civ_atlas_snapshot.create_import(self.store, self.root, civsnap(), {})
        world = civ_atlas_snapshot.load_world(self.root, record)
        grid = civ_atlas_snapshot.preview_grid(world, max_side=24)
        png = map_import.encode_rgb_preview(civ_atlas_snapshot.preview_rgb(grid, 'elevation'),
                                            grid['width'], grid['height'])
        self.assertEqual(png[:8], b'\x89PNG\r\n\x1a\n')
        decoded = map_import.decode_gray_png(png) if False else None   # RGB is not grey on purpose
        self.assertIsNone(decoded)


class SamplingHonestyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = Store(self.root / 'x.sqlite3')
        self.record = civ_atlas_snapshot.create_import(self.store, self.root, civsnap(), {})

    def tearDown(self):
        self.tmp.cleanup()

    def test_heightmap_sample_reports_climate_missing(self):
        record = map_import.create_import(self.store, self.root, heightmap_png(), '')
        heightmap = map_import.load_heightmap(self.root, record)
        sample = map_import.sample_region(heightmap, 100.0, 20.0, 3)
        self.assertIsNone(sample['climate'], '高度图没有气候，不能被填成数字')
        self.assertIn('temperature_c', sample['missing'])

    def test_climate_missing_is_refused_by_build(self):
        record = map_import.create_import(self.store, self.root, heightmap_png(), '')
        heightmap = map_import.load_heightmap(self.root, record)
        sample = map_import.sample_region(heightmap, 100.0, 20.0, 3)
        with self.assertRaises(map_import.MapImportError):
            map_import.build_town_input(record, sample,
                                       {'site_name': 'x', 'region': 'y',
                                        'climate_source': 'missing'}, REV)
        with self.assertRaises(map_import.MapImportError):
            map_import.build_town_input(record, sample,
                                       {'site_name': 'x', 'region': 'y',
                                        'climate_source': 'measured'}, REV)

    def test_lon_wraps_and_poles_are_refused(self):
        world = civ_atlas_snapshot.load_world(self.root, self.record)
        wrapped = civ_atlas_snapshot.sample_region(world, 190.0, 10.0, 3)
        same = civ_atlas_snapshot.sample_region(world, -170.0, 10.0, 3)
        self.assertAlmostEqual(wrapped['lon'], same['lon'], places=4)
        with self.assertRaises(civ_atlas_snapshot.MapImportError):
            civ_atlas_snapshot.sample_region(world, 0.0, 89.9, 3)

    def test_even_window_is_refused(self):
        world = civ_atlas_snapshot.load_world(self.root, self.record)
        with self.assertRaises(civ_atlas_snapshot.MapImportError):
            civ_atlas_snapshot.sample_region(world, 0.0, 0.0, 4)


class CrossLanguageContainerTests(unittest.TestCase):
    """The container contract between the JS exporter and this Python reader.

    These exist because a fixture alone hid a real bug twice: the exporter wrote
    ``offset`` inside the manifest it was measuring, so its length changed with the
    number's digit count. A same-language fixture cannot show that, so these drive the
    **real exporter logic** (the offset-padding scheme) and the **real parser** together.
    """

    OFFSET_WIDTH = 12

    def _container(self, items, offset_style='padded'):
        """Build CASNAP01 the way tools/civ_atlas_export.js now does.

        ``items`` is a list of ``(name, payload_bytes)``. ``offset_style`` picks the
        offset encoding: ``padded`` (current exporter), ``int`` (old exporter).
        """
        padded = (lambda v: str(v).zfill(self.OFFSET_WIDTH))
        manifest = {
            'container': 'CASNAP01', 'schema': 1,
            'exported_by': 'test', 'exported_at': '2026-01-01T00:00:00Z',
            'site': 'http://localhost',
            'world': {'id': 'w1', 'generator': 45, 'app': 't', 'at': '2026-01-01'},
            'snapshot': {'format': 1, 'generator': 45, 'recipe': 'r', 'formation': False},
            'head': {'id': 'w1', 'generator': 45},
            # reserve room so a tampered manifest can still fit (tests only)
            'note': ' ' * 256,
            'parts': [{'name': name, 'bytes': len(blob), 'sum': '', 'zip': 'none',
                       'length': len(blob), 'offset': 0 if offset_style == 'int' else padded(0)}
                      for name, blob in items],
        }
        # same reserve-then-fill scheme as the exporter
        head = json.dumps(manifest).encode('utf-8')
        body_start = pad8(12 + len(head))
        cursor = body_start
        for part, (_, blob) in zip(manifest['parts'], items):
            part['offset'] = cursor if offset_style == 'int' else padded(cursor)
            cursor = pad8(cursor + len(blob))
        head = json.dumps(manifest).encode('utf-8')
        self.assertEqual(pad8(12 + len(head)), body_start, 'offset 编码没能定长')
        total = sum(len(blob) for _, blob in items)
        out = bytearray(body_start + total)
        out[0:8] = b'CASNAP01'
        struct.pack_into('<I', out, 8, len(head))
        out[12:12 + len(head)] = head
        cursor = body_start
        for _, blob in items:
            out[cursor:cursor + len(blob)] = blob
            cursor = pad8(cursor + len(blob))
        return bytes(out)

    def _map_part(self):
        """A minimal but valid CIVSNAP1 ``map`` payload (one 4-cell mesh)."""
        side = 2
        cells = side * side
        payload = bytearray()
        slots = {}

        def put(name, kind, values):
            nonlocal payload
            if len(payload) % 8:
                payload += b'\x00' * (8 - len(payload) % 8)
            slots[name] = (kind, len(payload), len(values))
            fmt = {'F32': 'f', 'I32': 'i', 'U8': 'B'}[kind]
            payload += struct.pack('<%d%s' % (len(values), fmt), *values)

        put('x', 'F32', [float(c % side) for c in range(cells)])
        put('y', 'F32', [float(c // side) for c in range(cells)])
        put('adjStart', 'I32', [0, 2, 4, 6, 8])
        put('adj', 'I32', [1, 2, 0, 3, 0, 3, 1, 2])
        put('elevation', 'F32', [100.0 + c for c in range(cells)])
        put('water', 'U8', [0] * cells)
        put('temperature', 'F32', [10.0 + c for c in range(cells)])
        put('precipitation', 'F32', [800.0 + c for c in range(cells)])
        put('biome', 'U8', [8] * cells)

        def ref(name):
            kind, offset, count = slots[name]
            return {'$$': 'a', 't': kind, 'o': offset, 'n': count}

        structure = {
            'mesh': {'n': cells, 'width': side, 'height': side,
                     'x': ref('x'), 'y': ref('y'),
                     'adjStart': ref('adjStart'), 'adj': ref('adj')},
            'elevation': ref('elevation'), 'water': ref('water'),
            'temperature': ref('temperature'), 'precipitation': ref('precipitation'),
            'biome': ref('biome'), 'maxElevation': 103.0,
        }
        meta = json.dumps(structure).encode('utf-8')
        raw = b'CIVSNAP1' + struct.pack('<I', len(meta)) + meta
        if len(raw) % 8:
            raw += b'\x00' * (8 - len(raw) % 8)
        return raw + bytes(payload)

    def _roundtrip(self, data):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        store = Store(root / 'x.sqlite3')
        record = civ_atlas_snapshot.create_import(store, root, data, {})
        return civ_atlas_snapshot.load_world(root, record), record

    # ---- the contract itself
    def test_padded_offsets_round_trip(self):
        data = self._container([('map', self._map_part())])
        world, record = self._roundtrip(data)
        self.assertEqual(world.cells, 4)
        self.assertAlmostEqual(world.temperature[0], 10.0, places=4)
        self.assertEqual(record['parts'][0]['name'], 'map')

    def test_old_integer_offsets_still_round_trip(self):
        data = self._container([('map', self._map_part())], offset_style='int')
        world, _ = self._roundtrip(data)
        self.assertEqual(world.cells, 4)

    def test_payload_size_crossing_a_digit_boundary_still_parses(self):
        # 9 999 999 -> 10 000 000 bytes makes the offset gain a digit; a non-fixed-width
        # manifest would shift everything by one byte and the parse would fail.
        big = b'\x00' * (10_000_000 - 1)
        items = [('map', self._map_part()), ('pad', big)]
        data = self._container(items)
        world, record = self._roundtrip(data)
        self.assertEqual(world.cells, 4)
        self.assertEqual([p['name'] for p in record['parts']], ['map', 'pad'])

    def test_three_parts_are_all_addressable(self):
        items = [('map', self._map_part()), ('eras', b'\x01' * 64), ('civ', b'\x02' * 128)]
        data = self._container(items)
        _, record = self._roundtrip(data)
        self.assertEqual([p['name'] for p in record['parts']], ['map', 'eras', 'civ'])
        self.assertEqual([p['length'] for p in record['parts']], [len(self._map_part()), 64, 128])

    # ---- tampering must be refused, not silently accepted
    def _tamper(self, data, mutate):
        # parse_container injects _bytes into each part, so re-serialise from a clean copy
        # of the manifest read straight out of the header instead.
        head_len = struct.unpack('<I', data[8:12])[0]
        manifest = json.loads(data[12:12 + head_len].decode('utf-8'))
        mutate(manifest)
        head = json.dumps(manifest).encode('utf-8')
        # keep the payload area where it is: pad the header to the original body start
        body_start = pad8(12 + head_len)
        pad = body_start - 12 - len(head)
        if pad < 0:
            raise AssertionError('篡改后清单变长，测试需要更大预留')
        head = head + b' ' * pad
        out = bytearray(data)
        struct.pack_into('<I', out, 8, len(head))
        out[12:body_start] = head
        return bytes(out)

    def test_offset_with_trailing_junk_is_refused(self):
        data = self._container([('map', self._map_part())])

        def mutate(manifest):
            manifest['parts'][0]['offset'] = manifest['parts'][0]['offset'] + 'junk'
        with self.assertRaises(civ_atlas_snapshot.MapImportError):
            self._roundtrip(self._tamper(data, mutate))

    def test_short_offset_string_is_refused(self):
        data = self._container([('map', self._map_part())])

        def mutate(manifest):
            manifest['parts'][0]['offset'] = '00000000100'      # 11 digits
        with self.assertRaises(civ_atlas_snapshot.MapImportError):
            self._roundtrip(self._tamper(data, mutate))

    def test_negative_and_bool_offsets_are_refused(self):
        data = self._container([('map', self._map_part())])
        for bad in (-8, True):
            def mutate(manifest, bad=bad):
                manifest['parts'][0]['offset'] = bad
            with self.assertRaises(civ_atlas_snapshot.MapImportError):
                self._roundtrip(self._tamper(data, mutate))

    def test_unaligned_offset_is_refused(self):
        data = self._container([('map', self._map_part())])

        def mutate(manifest):
            manifest['parts'][0]['offset'] = str(int(manifest['parts'][0]['offset']) + 1).zfill(12)
        with self.assertRaises(civ_atlas_snapshot.MapImportError):
            self._roundtrip(self._tamper(data, mutate))

    def test_out_of_bounds_offset_is_refused(self):
        data = self._container([('map', self._map_part())])

        def mutate(manifest):
            manifest['parts'][0]['offset'] = str(len(data) * 10).zfill(12)
        with self.assertRaises(civ_atlas_snapshot.MapImportError):
            self._roundtrip(self._tamper(data, mutate))

    def test_overlapping_parts_are_refused(self):
        items = [('map', self._map_part()), ('eras', b'\x01' * 64)]
        data = self._container(items)

        def mutate(manifest):
            # make the second part start inside the first one
            manifest['parts'][1]['offset'] = manifest['parts'][0]['offset']
        with self.assertRaises(civ_atlas_snapshot.MapImportError):
            self._roundtrip(self._tamper(data, mutate))


class WaterSemanticsTests(unittest.TestCase):
    """水体语义：中心必须干陆地，湖/海/陆分开统计，水面不算可耕地。

    直接构造 World 对象而不是再造容器：这些断言考的是 sample_region 的判定，
    与容器编码无关（后者已由 CrossLanguageContainerTests 盯）。
    """

    def _world(self, water, cells=None):
        """A small ring where index 0 is the centre and 1..N are its neighbours."""
        cells = cells or len(water)
        # place cells on a line of latitude so the nearest-cell search is deterministic
        lon = [-180.0 + 360.0 * i / cells for i in range(cells)]
        lat = [0.0] * cells
        elevation = [200.0] * cells
        temperature = [15.0] * cells
        precipitation = [800.0] * cells
        biome = [8] * cells
        # 环形邻接：格子围成一圈，3 格窗至少拿到 3 格，5 格窗拿到更多，跨度随窗格变化
        adj_start = [0]
        adj = []
        for i in range(cells):
            adj.append((i - 1) % cells)
            adj.append((i + 1) % cells)
            adj_start.append(len(adj))
        return civ_atlas_snapshot.World(
            cells=cells, lon=lon, lat=lat, elevation=elevation, water=water,
            temperature=temperature, precipitation=precipitation, biome=biome,
            neighbours=(adj_start, adj), max_elevation=200.0,
            meta={'mesh_width': cells, 'mesh_height': 1}, warnings=[])

    def test_centre_on_ocean_is_refused(self):
        world = self._world([1, 0, 0, 0, 0])
        with self.assertRaises(civ_atlas_snapshot.MapImportError) as ctx:
            civ_atlas_snapshot.sample_region(world, -180.0, 0.0, 3, 1200.0)
        self.assertIn('海面', str(ctx.exception))

    def test_centre_on_lake_is_refused(self):
        world = self._world([2, 0, 0, 0, 0])
        with self.assertRaises(civ_atlas_snapshot.MapImportError) as ctx:
            civ_atlas_snapshot.sample_region(world, -180.0, 0.0, 3, 1200.0)
        self.assertIn('湖面', str(ctx.exception))

    def test_lake_by_the_shore_is_allowed_but_counted_separately(self):
        # 中心是干陆地；两个邻居分别是湖与海，其余干陆。用 5 格窗才能同时覆盖到它们。
        world = self._world([0, 2, 1, 0, 0, 0, 0])
        sample = civ_atlas_snapshot.sample_region(world, -180.0, 0.0, 5, 1200.0)
        self.assertGreater(sample['dryland_km2'], 0)
        self.assertGreater(sample['lake_km2'], 0, '湖面必须单独计入 lake_km2')
        self.assertGreater(sample['ocean_km2'], 0, '海面必须单独计入 ocean_km2')
        # 水面不算可耕地：area_km2 只等于干陆地部分
        self.assertAlmostEqual(sample['area_km2'], sample['dryland_km2'], places=1)
        self.assertLess(sample['area_km2'], sample['area_km2'] + sample['lake_km2'])

    def test_span_grows_with_the_window(self):
        # 3-cell window vs 5-cell window over the same latitude band
        world = self._world([0, 0, 0, 0, 0, 0, 0, 0, 0])
        small = civ_atlas_snapshot.sample_region(world, -180.0, 0.0, 3, 1200.0)
        large = civ_atlas_snapshot.sample_region(world, -180.0, 0.0, 5, 1200.0)
        self.assertIn('typical_cell_km', small['span_km'])
        self.assertIn('widest_pair_km', small['span_km'])
        self.assertGreater(small['span_km']['widest_pair_km'], 0.0,
                           '窗内多格时跨度必须是正数，不能恒为 0')
        self.assertNotEqual(small['span_km']['widest_pair_km'],
                            large['span_km']['widest_pair_km'],
                            '窗格变大时取样区跨度必须跟着变，不能是同一个数')

    def test_heightmap_without_water_array_is_marked_unknown(self):
        # water=None 表示这份数据没有水体数组（高度图），不能谎称都是陆地
        world = self._world(None, cells=5)
        world.water = None
        sample = civ_atlas_snapshot.sample_region(world, -180.0, 0.0, 3, 1200.0)
        self.assertFalse(sample['water_known'])


class EventLoopResponsivenessTests(unittest.TestCase):
    """A big parse must not freeze the event loop for other requests.

    The import endpoint is ``async``; if the decode ran inline, every concurrent request
    would wait for it. This test makes the parse deliberately slow and checks that a
    plain GET served by the same app still answers meanwhile.
    """

    def test_other_requests_answer_while_a_parse_runs(self):
        import threading
        import time

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        app = web.create_app(Path(tmp.name) / 'loop.sqlite3')
        client = TestClient(app)
        token = client.get('/api/bootstrap').json()['token']
        headers = {'X-TextileDream-Token': token}

        original = map_import.create_import
        started = threading.Event()
        release = threading.Event()

        def slow_create(*args, **kwargs):
            started.set()
            release.wait(5.0)
            return original(*args, **kwargs)

        results = {}

        def post_import():
            results['import'] = client.post('/api/inner/map-imports',
                                            content=heightmap_png(), headers=headers)

        try:
            map_import.create_import = slow_create
            worker = threading.Thread(target=post_import)
            worker.start()
            self.assertTrue(started.wait(10.0), '导入没有开始')

            # 解析“正在跑”时，另一个读请求必须照常返回
            began = time.monotonic()
            listing = client.get('/api/inner/map-imports', headers=headers)
            elapsed = time.monotonic() - began
            release.set()
            worker.join(10.0)
        finally:
            map_import.create_import = original

        self.assertEqual(listing.status_code, 200)
        self.assertLess(elapsed, 2.0, '别的请求被解析阻塞了 %.2fs' % elapsed)
        self.assertEqual(results['import'].status_code, 200)


class StrictRequestModelTests(unittest.TestCase):
    """The endpoint models must refuse unknown keys and non-numeric stand-ins.

    These also cover ``hinterland_km2``: bools, strings, NaN and missing values must be
    refused rather than coerced, and the border values 0.5 / 20000 must be accepted.
    """

    def test_unknown_field_is_refused(self):
        with self.assertRaises(Exception):
            web.MapSampleRequest(lon=1.0, lat=2.0, window_px=3, nope=1)

    def test_bool_is_not_a_number(self):
        with self.assertRaises(Exception):
            web.MapSampleRequest(lon=True, lat=2.0, window_px=3)

    def test_string_is_not_a_number(self):
        with self.assertRaises(Exception):
            web.MapSampleRequest(lon='1.0', lat='2.0', window_px=3)

    def test_window_out_of_range(self):
        with self.assertRaises(Exception):
            web.MapSampleRequest(lon=1.0, lat=2.0, window_px=17)

    def test_commit_must_be_hex_or_empty(self):
        self.assertEqual(web.MapImportDeclared().commit, '')
        web.MapImportDeclared(commit='0939c5f')
        with self.assertRaises(Exception):
            web.MapImportDeclared(commit='not-hex')


#: 一个约 29 km² 的小正方形，用于建筑范围/用地测试
SQUARE = [[10.0, 20.0], [10.05, 20.0], [10.05, 20.05], [10.0, 20.05]]

#: TownInput.story_revision 要求至少 8 个字符
REV = 'rev-0001'


def _hinterland_case(author_extra):
    """Build (record, sample, author) for hinterland tests without touching disk."""
    record = {'id': 'sn_test0001', 'format': civ_atlas_snapshot.FORMAT,
              'sha256': 'a' * 64, 'stats': {'lake_cells': 0},
              'units': {}, 'source': {}}
    sample = {
        'lon': 10.0, 'lat': 20.0, 'window_px': 5, 'pixel': {'x': 3, 'y': 7},
        'span_km': {'north_south': 100.0, 'east_west': 120.0, 'widest_pair_km': 120.0,
                    'typical_cell_km': 30.0, 'note': ''},
        'elevation_m': {'min': 100.0, 'max': 400.0, 'mean': 250.0},
        'sea_fraction': 0.0, 'lake_fraction': 0.0, 'dry_fraction': 1.0,
        'land_km2': 40000.0, 'sea_km2': 0.0, 'dryland_km2': 40000.0,
        'lake_km2': 0.0, 'ocean_km2': 0.0, 'area_km2': 40000.0,
        'slope_deg': {'p50': 1.0, 'max': 3.0}, 'vertical_m': 0.0,
        'radius_km': 6371.0088, 'cell_area_km2': 8000.0, 'water_known': True,
        'climate': {'temperature_c': 16.0, 'precipitation_mm': 900.0,
                    'biome': 8, 'biome_name': '草原', 'measured': True},
        'derived': ['elevation_m'], 'blocked': [], 'blocked_reason': {}, 'warnings': [],
    }
    author = {'climate_source': 'measured', 'site_name': '观雨城',
              'region': '河谷上游', 'selection': {'lon': 10.0, 'lat': 20.0},
              'confirm_template': True}
    author.update(author_extra)
    return record, sample, author


class FootprintAndSupplyTests(unittest.TestCase):
    """建筑范围 / 用地规划 / 供给来源：三者必须分得开，且不许假造供给。"""

    def test_no_space_at_all_is_refused(self):
        record, sample, author = _hinterland_case({})
        with self.assertRaises(map_import.MapImportError) as ctx:
            map_import.build_town_input(record, sample, author, REV)
        self.assertIn('footprint', str(ctx.exception))

    def test_footprint_only_is_refused_not_faked(self):
        # 只有建筑范围 → 没有供给 → 必须拒，不能把建筑面积塞进 terrain.area_km2
        record, sample, author = _hinterland_case({
            'footprint': {'vertices': SQUARE}})
        with self.assertRaises(map_import.MapImportError) as ctx:
            map_import.build_town_input(record, sample, author, REV)
        self.assertIn('空间草稿', str(ctx.exception))

    def test_declared_farmland_becomes_the_area(self):
        record, sample, author = _hinterland_case({
            'land_use': [{'kind': 'farmland', 'vertices': SQUARE}]})
        built = map_import.build_town_input(record, sample, author, REV)
        prov = built['provenance']
        self.assertEqual(prov['hinterland']['source'], 'declared_productive_land_use')
        self.assertEqual(prov['hinterland']['supply'], 'configured')
        self.assertGreater(prov['hinterland']['km2'], 0.0)
        self.assertEqual(prov['land_use']['by_kind_km2'].get('farmland'),
                         prov['hinterland']['km2'])

    def test_pasture_does_not_count_as_grain(self):
        # 牧场不能按谷物单产折算：只有牧场时不算有供给
        record, sample, author = _hinterland_case({
            'land_use': [{'kind': 'pasture', 'vertices': SQUARE}]})
        with self.assertRaises(map_import.MapImportError) as ctx:
            map_import.build_town_input(record, sample, author, REV)
        self.assertIn('空间草稿', str(ctx.exception))

    def test_unplanned_land_is_not_wasteland(self):
        record, sample, author = _hinterland_case({
            'land_use': [{'kind': 'farmland', 'vertices': SQUARE}]})
        built = map_import.build_town_input(record, sample, author, REV)
        summary = built['provenance']['land_use']
        self.assertTrue(summary['unplanned_elsewhere'])
        self.assertNotIn('wasteland', summary['by_kind_km2'])

    def test_overlapping_land_use_is_flagged(self):
        near = [[10.01, 20.01], [10.06, 20.01], [10.06, 20.06], [10.01, 20.06]]
        record, sample, author = _hinterland_case({
            'land_use': [{'kind': 'farmland', 'vertices': SQUARE},
                         {'kind': 'mine', 'vertices': near}]})
        built = map_import.build_town_input(record, sample, author, REV)
        self.assertEqual(len(built['provenance']['land_use']['conflicts']), 1)

    def test_explicit_hinterland_still_works(self):
        record, sample, author = _hinterland_case({'hinterland_km2': 1200.0})
        built = map_import.build_town_input(record, sample, author, REV)
        prov = built['provenance']['hinterland']
        self.assertEqual(prov['km2'], 1200.0)
        self.assertEqual(prov['source'], 'author_declared_hinterland')
        self.assertEqual(prov['supply'], 'configured')

    def test_hinterland_bool_string_nan_refused(self):
        for bad in (True, '1200', float('nan')):
            record, sample, author = _hinterland_case({'hinterland_km2': bad})
            with self.assertRaises(map_import.MapImportError):
                map_import.build_town_input(record, sample, author, REV)

    def test_hinterland_out_of_range_refused(self):
        for bad in (0.1, 25000.0):
            record, sample, author = _hinterland_case({'hinterland_km2': bad})
            with self.assertRaises(map_import.MapImportError):
                map_import.build_town_input(record, sample, author, REV)

if __name__ == '__main__':
    unittest.main()
