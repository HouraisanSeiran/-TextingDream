# -*- coding: utf-8 -*-
"""Run against the frozen fast world: reproducible, quick, and it does not touch the bed."""
import hashlib
import json
import time
from pathlib import Path

import pytest

from app.civ_sim import CivSimConfig, CivSimError, run_product, to_history_candidate
from app.civ_sim.chronicle import chronicle_sha256
from app.terrain_source import TerrainSourceError

PRODUCT = Path(__file__).resolve().parents[1] / "artifacts" / "fast-world" / "tg-speed-archipelago-1600-20261108"
IDENTITY = "db09ec0f6a166d311a0055adeee3601868e618f81e7cdc92f28117524fcbc199"
PINNED = (
    "manifest.json",
    "elevation_m.npy",
    "status.npy",
    "vectors/rivers.json",
)


def _digests():
    found = {}
    for name in PINNED:
        path = PRODUCT / name
        found[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return found


pytestmark = pytest.mark.skipif(not (PRODUCT / "manifest.json").is_file(), reason="fast world product is not in this workspace")


def test_output_cannot_land_inside_the_product(tmp_path):
    product = tmp_path / "product"
    product.mkdir()
    with pytest.raises(CivSimError):
        run_product(product, identity="ab" * 32, config=CivSimConfig(seed=1, end_year=1), out_dir=product / "history")


def test_short_run_is_reproducible_and_leaves_the_product_alone(tmp_path):
    before = _digests()
    config = CivSimConfig(seed=20261108, start_year=0, end_year=80, max_polities=6)
    started = time.perf_counter()
    first = run_product(PRODUCT, identity=IDENTITY, config=config, out_dir=tmp_path / "run-a")
    elapsed = time.perf_counter() - started
    second = run_product(PRODUCT, identity=IDENTITY, config=config, out_dir=tmp_path / "run-b")
    assert elapsed < 12
    assert before == _digests()
    assert first["map_identity"] == IDENTITY
    assert first["chronicle_sha256"] == second["chronicle_sha256"]
    chronicle = json.loads((tmp_path / "run-a" / "chronicle.json").read_text(encoding="utf-8"))
    manifest = json.loads((tmp_path / "run-a" / "manifest.json").read_text(encoding="utf-8"))
    assert chronicle_sha256(chronicle) == manifest["chronicle_sha256"]
    assert manifest["terrain_modified"] is False
    assert manifest["map"]["identity"] == IDENTITY
    assert manifest["upstream_code_copied"] is False
    years = [event["year"] for event in chronicle["annals"]]
    assert years == sorted(years)
    assert any(event["kind"] == "found" for event in chronicle["annals"])
    by_id = {region["id"]: region for region in chronicle["regions"]}
    for event in chronicle["annals"]:
        if event["region"] is None:
            continue
        assert by_id[event["region"]]["land_cells"] > 0
    assert chronicle["habitat"]["ocean_cells"] > 0
    assert chronicle["habitat"]["habitable_cells"] > 0
    assert chronicle["habitat"]["region_count"] > 0
    candidate = to_history_candidate(chronicle, base_year=80)
    assert candidate["provenance"]["map_identity"] == IDENTITY
    assert candidate["store_bridge"]["source_kind"] == "civ_sim"
    assert candidate["identity"]["map_identity"]
    assert candidate["selection"]["base_year"] == 80


def test_wrong_identity_is_refused(tmp_path):
    with pytest.raises(TerrainSourceError):
        run_product(PRODUCT, identity="0" * 64, config=CivSimConfig(seed=1, end_year=1), out_dir=tmp_path / "nope")
    assert not (tmp_path / "nope").exists()

