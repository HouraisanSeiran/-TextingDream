# -*- coding: utf-8 -*-
"""Dynasty / people / faith layer: deterministic and present in chronicle."""
import numpy as np

from app.civ_sim import CivSimConfig, LoreCatalog, habitat_from_arrays, simulate, to_history_candidate
from app.terrain_source import LAND


def _land():
    elevation = np.full((8, 8), 40.0)
    status = np.full((8, 8), LAND, np.uint8)
    return habitat_from_arrays(
        identity="society-land",
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


def test_society_produces_dynasty_people_faith_and_repeats():
    habitat = _land()
    lore = LoreCatalog(
        era_chars=("青", "澜"),
        dynasty_suffixes=("朝",),
        house_names=("北原",),
        titles=("王",),
        given_names=("明", "德", "安"),
        roles=("君主", "储君", "宰相", "将军", "祭司"),
        faiths=(
            {"id": "sky", "name": "天道", "element_ref": None},
            {"id": "sea", "name": "海祀", "element_ref": None},
        ),
        name_tokens=("青", "澜", "明", "德"),
        source="fixture",
    )
    config = CivSimConfig(
        seed=21, end_year=60, found_period=1, max_polities=3, min_capital_hops=1,
        reign_years=10, succession_per_mille=200, usurp_per_mille=100,
        appoint_per_mille=100, convert_per_mille=50,
    )
    first = simulate(habitat, config, lore=lore)
    second = simulate(habitat, config, lore=lore)
    assert first == second
    kinds = {event["kind"] for event in first["annals"]}
    assert {"found", "dynasty", "succession", "faith_adopt"} <= kinds
    assert first["dynasties"]
    assert first["people"]
    assert first["faiths"]
    assert first["counts"]["people"] >= 1
    snap = first["snapshots"][-1]
    assert snap["people"]
    assert snap["dynasties"]
    candidate = to_history_candidate(first, base_year=60)
    assert candidate["people"]["items"]
    assert candidate["dynasties"]["items"]
    assert candidate["religion"]["items"]
    assert candidate["field_status"]["religion_events"]["status"] == "exact"


def test_society_can_be_disabled():
    habitat = _land()
    chronicle = simulate(
        habitat,
        CivSimConfig(seed=3, end_year=10, found_period=1, max_polities=2,
                     min_capital_hops=1, society=False),
    )
    kinds = {event["kind"] for event in chronicle["annals"]}
    assert "dynasty" not in kinds
    assert chronicle["people"] == []
    assert chronicle["dynasties"] == []
