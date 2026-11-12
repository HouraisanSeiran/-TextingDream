"""map_source adapter for terragenesis-regional-climate-v1 (mocked TG query)."""
import json
import sys
import types
from pathlib import Path

import numpy as np
import pytest

from app import map_source as ms
from app.map_source import adapters


def test_load_regional_climate_via_mocked_query(tmp_path, monkeypatch):
    root = tmp_path / "climate"
    root.mkdir()
    ocean = np.array([[True, False], [False, True]], dtype=bool)
    temperature = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
    precip = np.array([[10.0, 20.0], [30.0, 40.0]], dtype=np.float32)
    identity = "a" * 64
    (root / "manifest.json").write_text(json.dumps({
        "schema": adapters.CLIMATE_SCHEMA,
        "identity": identity,
        "fields": {
            "ocean_mask": {},
            "temperature_c": {},
            "precipitation_mm_yr": {},
        },
    }), encoding="utf-8")

    def query_climate(path, fields=None, allow_candidate=False):
        assert Path(path) == root.resolve()
        assert allow_candidate is False
        arrays = {"ocean_mask": ocean, "temperature_c": temperature}
        if "precipitation_mm_yr" in (fields or []):
            arrays["precipitation_mm_yr"] = precip
        return {
            "arrays": arrays,
            "metadata": {
                "identity": identity,
                "world_seed": 42,
                "shape_zx": [2, 2],
                "first_xz_m": [0.0, 0.0],
                "spacing_m": 2000.0,
                "algorithm": "fixture",
                "source_identity": "b" * 64,
            },
            "manifest_identity": "c" * 64,
        }

    package = types.ModuleType("terrain_pipeline")
    package.__path__ = []
    climate = types.ModuleType("terrain_pipeline.world_climate")
    climate.query_climate = query_climate
    package.world_climate = climate
    monkeypatch.setitem(sys.modules, "terrain_pipeline", package)
    monkeypatch.setitem(sys.modules, "terrain_pipeline.world_climate", climate)
    monkeypatch.setattr("app.world_gen.terragenesis_bridge.ensure_path", lambda: None)

    source = ms.load_source(adapters.CLIMATE_KIND, root, expected_identity=identity)
    assert source.info.kind == adapters.CLIMATE_KIND
    assert source.info.schema == adapters.CLIMATE_SCHEMA
    assert source.info.world_seed == 42
    assert "temperature_c" in source.info.layers
    assert "precipitation_mm_yr" in source.info.layers
    sample = source.sample([0.0], [0.0], layers=("elevation_m", "status", "temperature_c"))
    assert sample["status"][0] == ms.OCEAN
    assert sample["elevation_m"][0] == 0.0
    assert sample["temperature_c"][0] == pytest.approx(1.0)


def test_climate_schema_registered():
    assert adapters.CLIMATE_SCHEMA in ms.SUPPORTED_SCHEMAS[adapters.CLIMATE_KIND]


def test_terragenesis_bridge_probe_paths():
    from app.world_gen import terragenesis_bridge as bridge
    report = bridge.probe(check_import=False)
    assert "root" in report and "product_schemas" in report
    assert adapters.CLIMATE_SCHEMA in report["product_schemas"]
