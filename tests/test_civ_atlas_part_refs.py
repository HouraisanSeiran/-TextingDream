# -*- coding: utf-8 -*-
"""Back-reference numbering inside one ``CIVSNAP1`` part.

Regression for a real bug found by parsing a genuine civ-atlas export: a **typed array** is
an object for back-reference numbering upstream (``src/gen/snapshot.ts:276-287`` — ``case
'a'`` does ``objs.push(out)``), so it consumes the next index exactly like an
object/array/Map/Set. The decoder here decoded arrays but never registered them, so in any
part where one array is referenced twice (a real ``civ`` part shares
``religion.faiths[].color`` across 20+ faiths) every later ``{"$$":"r"}`` index pointed
one-too-far and the whole part was refused.

Index bookkeeping used below: the root structure passed to ``_decode_structure`` is itself
registered as index 0, so a top-level key's object/array starts at 1.

These are **hand-built** structures, not upstream files: each isolates one branch of the
numbering so a future change cannot silently re-break it.
"""
import json
import struct
import unittest

from app import civ_atlas_snapshot as snap


def part_from(structure, payload=b''):
    """Pack a raw structure dict into a ``CIVSNAP1`` part (no compression)."""
    meta = json.dumps(structure).encode('utf-8')
    raw = b'CIVSNAP1' + struct.pack('<I', len(meta)) + meta
    if len(raw) % 8:
        raw += b'\x00' * (8 - len(raw) % 8)
    return raw + payload


def array_ref(kind, offset, count):
    return {'$$': 'a', 't': kind, 'o': offset, 'n': count}


def f32(values):
    return struct.pack('<%df' % len(values), *values)


class TypedArrayReferenceTests(unittest.TestCase):
    def test_array_followed_by_reference_resolves(self):
        """root=0, colour=1, first=2 — so index 2 is `first`."""
        payload = f32([1.0, 2.0, 3.0])
        structure = {
            'colour': array_ref('F32', 0, 3),
            'first': {'name': 'a'},
            'second': {'$$': 'r', 'i': 2},
        }
        decoded = snap.parse_part(part_from(structure, payload), 't')
        self.assertEqual(decoded['colour'], [1.0, 2.0, 3.0])
        self.assertEqual(decoded['second'], {'name': 'a'})
        self.assertIs(decoded['second'], decoded['first'])

    def test_array_itself_is_addressable_at_its_own_index(self):
        """root=0, colour=1: index 1 must be the array, not the following object."""
        payload = f32([1.0, 2.0, 3.0])
        structure = {
            'colour': array_ref('F32', 0, 3),
            'first': {'name': 'a'},
            'second': {'$$': 'r', 'i': 1},
        }
        decoded = snap.parse_part(part_from(structure, payload), 't')
        self.assertIs(decoded['second'], decoded['colour'])
        self.assertEqual(decoded['second'], [1.0, 2.0, 3.0])

    def test_repeated_reference_returns_one_identical_object(self):
        """root=0, a=1, b=2, same→1, after=3, same2→1"""
        payload = f32([7.0, 8.0, 9.0])
        structure = {
            'a': array_ref('F32', 0, 3),
            'b': array_ref('F32', 0, 3),
            'same': {'$$': 'r', 'i': 1},
            'after': {'k': 1},
            'same2': {'$$': 'r', 'i': 1},
        }
        decoded = snap.parse_part(part_from(structure, payload), 't')
        self.assertIs(decoded['same'], decoded['a'])
        self.assertIs(decoded['same2'], decoded['a'])
        self.assertEqual(decoded['same'], [7.0, 8.0, 9.0])
        self.assertIsNot(decoded['b'], decoded['a'], '两个不同位置的数组是两份')

    def test_shared_colour_like_a_real_civ_part(self):
        """The exact shape that broke: one array shared by many entries of a list.

        root=0, faiths=1, faiths[0]=2, its colour=3 — every later copy is index 3.
        """
        payload = struct.pack('<3B', 214, 96, 77)
        colour = array_ref('U8', 0, 3)
        structure = {
            'faiths': [
                {'id': 0, 'colour': colour},
                {'id': 1, 'colour': {'$$': 'r', 'i': 3}},
                {'id': 2, 'colour': {'$$': 'r', 'i': 3}},
                {'id': 3, 'colour': {'$$': 'r', 'i': 3}},
            ],
        }
        decoded = snap.parse_part(part_from(structure, payload), 't')
        colours = [faith['colour'] for faith in decoded['faiths']]
        self.assertEqual(colours, [[214, 96, 77]] * 4)
        for faith in decoded['faiths']:
            self.assertIs(faith['colour'], decoded['faiths'][0]['colour'])

    def test_reference_beyond_what_was_seen_is_still_refused(self):
        payload = f32([1.0])
        structure = {'late': {'$$': 'r', 'i': 9}, 'a': array_ref('F32', 0, 1)}
        with self.assertRaises(snap.MapImportError) as caught:
            snap.parse_part(part_from(structure, payload), 't')
        self.assertIn('尚未出现', str(caught.exception))

    def test_negative_and_bool_reference_indices_are_refused(self):
        for bad in (-1, True):
            structure = {'a': {'x': 1}, 'r': {'$$': 'r', 'i': bad}}
            with self.assertRaises(snap.MapImportError):
                snap.parse_part(part_from(structure), 't')

    def test_map_and_set_register_and_renumber_like_upstream(self):
        """root=0, array=1, map=2, set=3"""
        payload = f32([5.0, 6.0])
        structure = {
            'array': array_ref('F32', 0, 2),
            'map': {'$$': 'm', 'v': [['k', 1]]},
            'set': {'$$': 's', 'v': [1, 2]},
            'toSet': {'$$': 'r', 'i': 3},
            'toMapTwice': {'$$': 'r', 'i': 2},
        }
        decoded = snap.parse_part(part_from(structure, payload), 't')
        self.assertEqual(decoded['toMapTwice'], {'k': 1})
        self.assertIs(decoded['toMapTwice'], decoded['map'])
        self.assertEqual(decoded['toSet'], [1, 2])

    def test_o_tag_registers(self):
        """root=0, array=1, wrapped=2"""
        structure = {
            'array': array_ref('F32', 0, 1),
            'wrapped': {'$$': 'o', 'v': {'k': 'v'}},
            'again': {'$$': 'r', 'i': 2},
        }
        decoded = snap.parse_part(part_from(structure, f32([1.0])), 't')
        self.assertIs(decoded['again'], decoded['wrapped'])
        self.assertEqual(decoded['again'], {'k': 'v'})

    def test_undefined_and_nan_do_not_consume_an_index(self):
        """root=0, array=1, afterUndefined=2 — `u`/`n` are leaves upstream too."""
        payload = f32([1.0])
        structure = {
            'array': array_ref('F32', 0, 1),
            'u': {'$$': 'u'},
            'n': {'$$': 'n', 'v': 'NaN'},
            'afterUndefined': {'x': 1},
            'ref': {'$$': 'r', 'i': 2},
        }
        decoded = snap.parse_part(part_from(structure, payload), 't')
        self.assertIsNone(decoded['u'])
        self.assertIs(decoded['ref'], decoded['afterUndefined'])


if __name__ == '__main__':
    unittest.main()
