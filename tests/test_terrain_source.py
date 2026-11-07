"""Contract tests using temporary frozen products, plus an opt-in real fixture."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from app import terrain_source as ts


def identity(manifest, native=False):
    excluded = {"identity", "source_path"} if native else {"identity"}
    return hashlib.sha256(json.dumps({k: v for k, v in manifest.items() if k not in excluded}, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


class TerrainSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.native = self.root / "native"
        self.native.mkdir()
        self.bed = np.arange(20, dtype=np.float32).reshape(4, 5)
        self.arrays = {"bed_m": self.bed, "valid_mask": np.ones((4, 5), dtype=bool),
                       "ocean_mask": np.zeros((4, 5), dtype=bool), "unknown_mask": np.zeros((4, 5), dtype=bool),
                       "closed_below_sea_mask": np.zeros((4, 5), dtype=bool)}
        self.arrays["ocean_mask"][0, 4] = True
        self.arrays["closed_below_sea_mask"][1, 4] = True
        self.arrays["unknown_mask"][3, 4] = True
        self.manifest = dict(schema="new-world-terrain-v3", world_seed=20261020, spacing_m=30, sea_m=0,
                             shape_zx=[4, 5], origin_native_xz=[-2, -2], source_path="original", files={})
        for name, array in self.arrays.items():
            path = self.native / (name + ".npy")
            np.save(path, array)
            self.manifest["files"][name] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.manifest["files"]["climate_base"] = "0" * 64
        self.write_native()
        self.macro = self.root / "product.npz"
        self.elev = np.arange(20, dtype=np.float64).reshape(4, 5)
        self.elev[0, 0] = -3
        self.elev[0, 1] = -2
        self.ocean = np.zeros((4, 5), dtype=bool)
        self.ocean[0, 0] = True
        self.macro_manifest = dict(schema="tectonic-frozen-product-v2",
            config=dict(shape=[4, 5], cell_size_m=10000, origin_x_m=-15000, origin_z_m=-15000, world_seed=20261020),
            coordinates={"grid": "cell centres; periodic source"}, arrays={})
        for key, arr in (("final/elevation_m", self.elev), ("final/ocean_connected", self.ocean)):
            self.macro_manifest["arrays"][key] = {"sha256": hashlib.sha256(arr.tobytes(order="C")).hexdigest()}
        self.write_macro()

    def write_native(self):
        self.manifest["identity"] = identity(self.manifest, True)
        (self.native / "manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")

    def write_macro(self):
        self.macro_manifest["identity"] = identity(self.macro_manifest)
        np.savez(self.macro, manifest_json=np.array(json.dumps(self.macro_manifest)),
                 **{"final/elevation_m": self.elev, "final/ocean_connected": self.ocean})

    def test_01_native_load(self):
        product = ts.load_native_terrain(self.native, expected_identity=self.manifest["identity"])
        self.assertEqual(product.identity, self.manifest["identity"])
        self.assertEqual(product.unverified_files, ["climate_base"])
        self.assertIsInstance(product._elevation, np.memmap)
        self.assertFalse(product._elevation.flags.writeable)
        self.manifest["source_path"] = "moved"
        self.write_native()
        self.assertEqual(ts.load_native_terrain(self.native).identity, product.identity)
        self.assertEqual(product.provenance()["boundary"], "finite; no wrap")
        self.assertIn("not water surface", product.provenance()["elevation_meaning"])

    def test_02_manifest_identity(self):
        with self.assertRaises(ts.TerrainSourceError):
            ts.load_native_terrain(self.native, expected_identity="0" * 64)
        self.manifest["extra"] = True
        path = self.native / "manifest.json"
        path.write_text(json.dumps(self.manifest), encoding="utf-8")
        with self.assertRaises(ts.TerrainSourceError):
            ts.load_native_terrain(self.native)
        path.write_text('{"schema":1,"schema":2}', encoding="utf-8")
        with self.assertRaises(ts.TerrainSourceError):
            ts.load_native_terrain(self.native)

    def test_03_file_tamper(self):
        bed = self.bed.copy()
        bed[0, 0] = 99
        np.save(self.native / "bed_m.npy", bed)
        with self.assertRaises(ts.TerrainSourceError):
            ts.load_native_terrain(self.native)
        self.assertEqual(ts.load_native_terrain(self.native, verify_files=False).sample(-60, -60)["elevation_m"], 99)

    def test_04_native_sample(self):
        product = ts.load_native_terrain(self.native)
        self.assertEqual(product.first_xz_m, (-60, -60))
        self.assertEqual(product.extent_m, (-60, -60, 60, 30))
        result = product.sample([-60, -45, 60, 60, 60, 60.01], [-60, -45, -60, -30, 30, 30])
        np.testing.assert_allclose(result["elevation_m"][:4], [0, 3, 4, 9])
        np.testing.assert_array_equal(result["status"], [ts.LAND, ts.LAND, ts.OCEAN, ts.CLOSED_BELOW_SEA, ts.UNKNOWN, ts.OUT_OF_BOUNDS])
        self.assertTrue(np.isnan(result["elevation_m"][-2:]).all())
        self.assertEqual(product.sample(45, 15)["status"], ts.UNKNOWN)
        self.assertEqual(product.sample(np.array([[-60], [-30]]), np.array([-60, -30, 0]))["status"].shape, (2, 3))
        self.assertEqual(result["status"].dtype, np.uint8)
        self.assertEqual(result["elevation_m"].dtype, np.float64)

    def test_05_native_crop(self):
        product = ts.load_native_terrain(self.native)
        crop = product.crop(-60, -60, 30, 0)
        np.testing.assert_array_equal(crop["elevation_m"], self.bed[:2, :3])
        self.assertEqual(crop["shape_zx"], (2, 3))
        self.assertEqual(crop["first_sample_xz_m"], (-60, -60))
        self.assertTrue(crop["complete"])
        self.assertEqual(crop["elevation_m"].dtype, np.float32)
        crop["elevation_m"][0, 0] = 999
        self.assertEqual(product.sample(-60, -60)["elevation_m"], 0)
        outside = product.crop(-90, -90, 0, 0)
        self.assertFalse(outside["complete"])
        self.assertTrue(np.all(outside["status"][0] == ts.OUT_OF_BOUNDS))
        self.assertTrue(np.all(outside["status"][:, 0] == ts.OUT_OF_BOUNDS))
        self.assertTrue(np.isnan(outside["elevation_m"][0]).all())
        with self.assertRaises(ts.TerrainSourceError):
            product.crop(-60, -60, 30, 0, max_cells=5)
        with self.assertRaises(ts.TerrainSourceError):
            product.crop(0, 0, 0, 30)

    def test_06_tectonic(self):
        product = ts.load_tectonic_product(self.macro, expected_identity=self.macro_manifest["identity"])
        result = product.sample([-10000, 0, 10000, -10000.01], [-10000] * 4)
        np.testing.assert_array_equal(result["status"], [ts.OCEAN, ts.CLOSED_BELOW_SEA, ts.LAND, ts.OUT_OF_BOUNDS])
        self.assertEqual(result["elevation_m"][0], self.elev[0, 0])
        self.assertTrue(np.isnan(result["elevation_m"][-1]))
        self.elev[0, 0] = -100
        self.write_macro()
        with self.assertRaises(ts.TerrainSourceError):
            ts.load_tectonic_product(self.macro)

    def test_07_coordinates(self):
        self.assertEqual(ts.native_index_to_m(-2, 3), (-60, 90))
        self.assertEqual(ts.m_to_native_index(-60, 90), (-2, 3))
        with self.assertRaises(ts.TerrainSourceError):
            ts.m_to_native_index(30.001, 0)
        product = ts.load_native_terrain(self.native)
        for value in (np.nan, np.inf, -np.inf):
            with self.assertRaises(ts.TerrainSourceError):
                product.sample(value, 0)
            with self.assertRaises(ts.TerrainSourceError):
                product.crop(0, 0, value, 30)
            with self.assertRaises(ts.TerrainSourceError):
                ts.m_to_native_index(value, 0)

    def test_08_catalog(self):
        native, macro = ts.load_native_terrain(self.native), ts.load_tectonic_product(self.macro)
        catalog = ts.TerrainCatalog([macro, native])
        self.assertEqual(catalog.products, (native, macro))
        result = catalog.sample([0, 10000, 5e6], [0, 0, 5e6])
        np.testing.assert_array_equal(result["source"], [native.identity, macro.identity, None])
        self.assertEqual(result["status"][-1], ts.UNPREPARED)
        self.assertEqual(catalog.sample(0, 0)["source"].item(), native.identity)
        # Fine unknowns must not silently fall back to coarse land.
        self.assertEqual(catalog.sample(60, 30)["status"], ts.UNKNOWN)
        config = self.root / "sources.json"
        sources = [dict(kind=native.kind, path="native", identity=native.identity), dict(kind=macro.kind, path="product.npz", identity=macro.identity)]
        config.write_text(json.dumps({"sources": sources}), encoding="utf-8")
        self.assertEqual(len(ts.load_catalog(config).products), 2)
        del sources[0]["identity"]
        config.write_text(json.dumps({"sources": sources}), encoding="utf-8")
        with self.assertRaises(ts.TerrainSourceError):
            ts.load_catalog(config)
        with patch.dict(os.environ):
            os.environ.pop("DREAM_TERRAIN_SOURCES", None)
            self.assertEqual(ts.load_default_catalog().products, ())

    def test_seed_from_manifest_and_optional_expectation(self):
        self.manifest["world_seed"] = 123
        self.write_native()
        self.macro_manifest["config"]["world_seed"] = 456
        self.write_macro()
        self.assertEqual(ts.load_native_terrain(self.native).provenance()["world_seed"], 123)
        self.assertEqual(ts.load_tectonic_product(self.macro).provenance()["world_seed"], 456)
        config = self.root / "seeds.json"
        for kind, path, manifest, seed in (("native-terrain-v3", "native", self.manifest, 123),
                                            ("tectonic-macro-v2", "product.npz", self.macro_manifest, 456)):
            entry = dict(kind=kind, path=path, identity=manifest["identity"], expected_world_seed=seed)
            config.write_text(json.dumps({"sources": [entry]}), encoding="utf-8")
            self.assertEqual(ts.load_catalog(config).products[0].world_seed, seed)
            entry["expected_world_seed"] += 1
            config.write_text(json.dumps({"sources": [entry]}), encoding="utf-8")
            with self.assertRaisesRegex(ts.TerrainSourceError, "world_seed"):
                ts.load_catalog(config)

    def test_09_real_fixture(self):
        path = os.environ.get("DREAM_TERRAIN_V3_FIXTURE")
        if not path:
            self.skipTest("DREAM_TERRAIN_V3_FIXTURE is not set")
        product = ts.load_native_terrain(path, expected_identity="c751a09a6f02e8c336b6b9b8fb4b11b5dc67386e9a8470b0b1d90858bf1ffb72")
        self.assertEqual(product.shape_zx, (4096, 4096))
        self.assertEqual(product.first_xz_m, (-61440, -61440))
        self.assertTrue(np.isfinite(product.sample(0, 0)["elevation_m"]))


if __name__ == "__main__":
    unittest.main()
