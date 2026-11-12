# -*- coding: utf-8 -*-
"""civ_sim chronicle → history_preview → review → commit → adopt."""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient

from app import world_history_store as whs
from app.civ_sim import (
    CivSimConfig, habitat_from_arrays, run_product, simulate, to_history_candidate,
)
from app.terrain_source import LAND
from tests.fixtures_world import world_app as create_app


def _habitat():
    elevation = np.full((8, 8), 50.0)
    status = np.full((8, 8), LAND, np.uint8)
    return habitat_from_arrays(
        identity="a" * 64,
        elevation_m=elevation,
        status=status,
        spacing_m=1000.0,
        first_sample_xz_m=(0.0, 0.0),
        rivers=[{"points_xz_m": [[0.0, 1000.0], [7000.0, 1000.0]]}],
        block_cells=4,
        min_land_cells=1,
        river_radius_m=500,
        coast_scale_m=20_000,
    )


class CandidateShapeTests(unittest.TestCase):
    def test_candidate_has_store_fields_and_settlements(self):
        chronicle = simulate(
            _habitat(),
            CivSimConfig(seed=5, end_year=30, found_period=1, max_polities=3, min_capital_hops=1),
        )
        doc = to_history_candidate(chronicle, base_year=30, max_events=50)
        self.assertEqual(doc["kind"], "zhimeng_civ_sim_history_candidate")
        self.assertEqual(doc["selection"]["base_year"], 30)
        self.assertTrue(doc["annals"]["events"])
        self.assertTrue(doc["polities"]["items"])
        self.assertTrue(doc["settlements"]["items"])
        self.assertIn("annals", doc["field_status"])
        self.assertEqual(doc["identity"]["content_sha256"],
                         __import__("app.civ_sim.chronicle", fromlist=["chronicle_sha256"])
                         .chronicle_sha256(chronicle))


class StoreFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        db_path = self.root / "h.sqlite3"
        self.app = create_app(db_path)
        self.svc = self.app.state.service
        self.svc.provider.configure({"offline": True})
        self.hist = whs.WorldHistoryService(self.svc.runtime)
        self.svc.history = self.hist
        self.client = TestClient(self.app)
        with self.client as client:
            self.token = client.get("/api/bootstrap").json()["token"]
        # Write a tiny civ-sim run under a temp artifacts tree the API won't see;
        # exercise the service method directly, then also the HTTP path with a
        # repo-relative fixture if available.
        self.run_dir = self.root / "civ-run"
        self.run_dir.mkdir()
        chronicle = simulate(
            _habitat(),
            CivSimConfig(seed=9, end_year=25, found_period=1, max_polities=3, min_capital_hops=1),
        )
        from app.civ_sim.chronicle import chronicle_json, chronicle_sha256
        digest = chronicle_sha256(chronicle)
        (self.run_dir / "chronicle.json").write_text(chronicle_json(chronicle), encoding="utf-8")
        (self.run_dir / "manifest.json").write_text(json.dumps({
            "schema": "zhimeng-civ-sim-run-v1",
            "chronicle_sha256": digest,
            "map": {"identity": "a" * 64},
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        self.digest = digest

    def head(self):
        return {"X-TextileDream-Token": self.token}

    def test_preview_review_commit_adopt(self):
        before = self.svc.runtime.package()["id"]
        out = self.hist.preview_civ_sim(self.run_dir, base_year=25, branch="main")
        draft = out["preview"]
        self.assertEqual(draft["source_kind"], "civ_sim")
        self.assertEqual(self.svc.runtime.package()["id"], before)

        page = self.hist.page(draft["id"], "polities", page=0, size=20)
        self.assertTrue(page["items"])
        ref = page["items"][0]["ref"]
        reviewed = self.hist.review(
            draft["id"], entries=[{"ref": ref}],
            disclosure={"public_refs": [ref]},
            expected_revision=draft["revision"],
        )
        committed = self.hist.commit(draft["id"], expected_revision=reviewed["revision"])
        snapshot = committed["snapshot"]
        self.assertEqual(snapshot["kind"], "zhimeng_civ_sim_history_snapshot")
        self.assertEqual(snapshot["source"]["content_sha256"], self.digest)
        self.assertEqual(snapshot["world_basis"]["map_identity"], "a" * 64)

        adopted = self.hist.adopt(snapshot["id"], before)
        self.assertNotEqual(adopted["revision"], before)
        block = self.svc.runtime.package(adopted["revision"])["story"]["mechanics"]["history"]
        self.assertEqual(block["entries"][-1]["snapshot_id"], snapshot["id"])

    def test_http_rejects_path_outside_artifacts(self):
        res = self.client.post(
            "/api/inner/history/civ-sim/previews",
            json={"run_dir": str(self.run_dir), "base_year": 25},
            headers=self.head(),
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("artifacts/civ-sim", res.json()["detail"])


if __name__ == "__main__":
    unittest.main()
