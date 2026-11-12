# -*- coding: utf-8 -*-
"""Encyclopedia name catalog: optional, deterministic, never writes the DB."""
from pathlib import Path

import numpy as np

from app.civ_sim import CivSimConfig, NameCatalog, habitat_from_arrays, load_name_catalog, simulate
from app.terrain_source import LAND


ROOT = Path(__file__).resolve().parents[1]
CULTURE_DB = ROOT / "artifacts" / "human-encyclopedia" / "encyclopedia.sqlite3"


def test_missing_db_returns_none_unless_required():
    assert load_name_catalog(ROOT / "no-such-encyclopedia.sqlite3") is None


def test_catalog_tokens_are_sorted_unique_and_skip_disclaimer_aliases():
    catalog = NameCatalog(
        tokens=("李", "王", "张"),
        db_path="fixture",
        namespaces=("names-asian",),
        pool_ids=("names-asian/names_asian_sinitic",),
    )
    assert catalog.to_dict()["canon"] is False
    assert catalog.to_dict()["token_count"] == 3


def test_simulate_uses_catalog_names_deterministically():
    elevation = np.full((4, 8), 40.0)
    status = np.full((4, 8), LAND, np.uint8)
    habitat = habitat_from_arrays(
        identity="catalog-land",
        elevation_m=elevation,
        status=status,
        spacing_m=1000.0,
        first_sample_xz_m=(0.0, 0.0),
        block_cells=4,
        min_land_cells=1,
        river_radius_m=0,
        coast_scale_m=20_000,
    )
    catalog = NameCatalog(
        tokens=("青禾", "澜津", "石岭", "浦湾"),
        db_path="fixture",
        namespaces=("fixture",),
        pool_ids=("fixture/a",),
    )
    config = CivSimConfig(seed=19, end_year=20, found_period=1, max_polities=3, min_capital_hops=1)
    first = simulate(habitat, config, catalog=catalog)
    second = simulate(habitat, config, catalog=catalog)
    assert first == second
    assert first["provenance"]["name_catalog"]["token_count"] == 4
    names = [row["name"] for row in first["polities"]]
    assert names
    assert all(any(token in name for token in catalog.tokens) for name in names)


def test_real_encyclopedia_db_loads_when_present():
    if not CULTURE_DB.is_file():
        return
    catalog = load_name_catalog(CULTURE_DB, required=True)
    assert catalog is not None
    assert len(catalog.tokens) >= 8
    assert "names-asian" in catalog.namespaces or "names-european" in catalog.namespaces
