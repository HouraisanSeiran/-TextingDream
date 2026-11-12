# -*- coding: utf-8 -*-
"""Stepper: same seed repeats; sea is not settled; the four event kinds occur."""
import numpy as np

from app.civ_sim import CivSimConfig, CivSimError, habitat_from_arrays, simulate, to_history_candidate
from app.terrain_source import LAND, OCEAN


def _two_provinces():
    """Two adjacent land blocks. A river runs only through the western one."""
    elevation = np.full((4, 8), 40.0)
    status = np.full((4, 8), LAND, np.uint8)
    rivers = [{"points_xz_m": [[0.0, 1500.0], [3000.0, 1500.0]]}]
    return habitat_from_arrays(
        identity="two-provinces",
        map_kind="arrays",
        map_schema="arrays",
        world_seed=7,
        elevation_m=elevation,
        status=status,
        spacing_m=1000.0,
        first_sample_xz_m=(0.0, 0.0),
        rivers=rivers,
        block_cells=4,
        min_land_cells=1,
        river_radius_m=0,
        coast_scale_m=20_000,
    )


def _kinds(chronicle):
    return {event["kind"] for event in chronicle["annals"]}


def test_same_seed_repeats_and_years_are_monotonic():
    habitat = _two_provinces()
    config = CivSimConfig(seed=11, end_year=40, found_period=1, max_polities=4, min_capital_hops=1)
    first = simulate(habitat, config)
    second = simulate(habitat, config)
    assert first == second
    years = [event["year"] for event in first["annals"]]
    assert years == sorted(years)
    assert [row["year"] for row in first["snapshots"]] == list(range(0, 41))
    assert first["provenance"]["map_identity"] == "two-provinces"
    assert first["provenance"]["upstream_code_copied"] is False


def test_seed_changes_the_course():
    habitat = _two_provinces()
    signatures = []
    for seed in range(1, 7):
        chronicle = simulate(habitat, CivSimConfig(
            seed=seed, end_year=25, found_period=1, max_polities=4,
            min_capital_hops=1, found_jitter=50_000, war_per_mille=500,
        ))
        signatures.append((
            tuple(polity["name"] for polity in chronicle["polities"]),
            tuple((event["year"], event["kind"], event["region"]) for event in chronicle["annals"]),
        ))
    assert len(set(signatures)) > 1


def test_ocean_never_receives_a_polity():
    elevation = np.full((6, 6), -30.0)
    status = np.full((6, 6), OCEAN, np.uint8)
    habitat = habitat_from_arrays(
        identity="open-ocean",
        elevation_m=elevation,
        status=status,
        spacing_m=1000.0,
        first_sample_xz_m=(0.0, 0.0),
        block_cells=3,
        min_land_cells=1,
        river_radius_m=0,
        coast_scale_m=1000,
    )
    chronicle = simulate(habitat, CivSimConfig(seed=3, end_year=15, max_polities=4))
    assert chronicle["annals"] == []
    assert chronicle["polities"] == []
    assert chronicle["counts"]["regions"] == 0
    assert "found" not in _kinds(chronicle)


def test_peaceful_expand_and_forced_war_peace_and_fall():
    habitat = _two_provinces()
    expanded = simulate(habitat, CivSimConfig(
        seed=1, end_year=2, max_polities=1, found_period=1, found_jitter=0,
        expand_budget=1_000_000, war_per_mille=0,
    ))
    assert "found" in _kinds(expanded)
    assert "expand" in _kinds(expanded)
    assert all(event["region"] in (0, 1) for event in expanded["annals"] if event["region"] is not None)
    assert expanded["polities"][0]["regions"] == [0, 1]

    peace = simulate(habitat, CivSimConfig(
        seed=2, end_year=3, max_polities=2, found_period=1, found_jitter=0,
        min_capital_hops=1, expand_budget=-1_000_000_000,
        war_per_mille=1000, peace_per_mille=1000, conquer_per_mille=0,
        max_new_wars_per_year=1,
    ))
    assert "war" in _kinds(peace) and "peace" in _kinds(peace)
    assert all(peace["annals"][i]["year"] <= peace["annals"][i + 1]["year"]
               for i in range(len(peace["annals"]) - 1))

    fallen = simulate(habitat, CivSimConfig(
        seed=4, end_year=3, max_polities=2, found_period=1, found_jitter=0,
        min_capital_hops=1, expand_budget=-1_000_000_000,
        war_per_mille=1000, peace_per_mille=0, conquer_per_mille=1000,
        max_new_wars_per_year=1, max_war_years=50,
    ))
    assert "fall" in _kinds(fallen)
    dead = [row for row in fallen["polities"] if not row["alive"]]
    assert dead and dead[0]["ended"] is not None
    assert dead[0]["regions"] == []


def test_annals_stop_at_the_cap_and_config_rejects_bools():
    habitat = _two_provinces()
    chronicle = simulate(habitat, CivSimConfig(
        seed=1, end_year=4, found_period=1, max_polities=2, min_capital_hops=1,
        found_jitter=0, expand_budget=-1_000_000_000, war_per_mille=0, max_annals=1,
    ))
    assert chronicle["truncated"] is True
    assert len(chronicle["annals"]) == 1
    try:
        CivSimConfig(seed=1, end_year=True)
    except CivSimError:
        pass
    else:
        raise AssertionError("bool year must be refused")


def test_history_candidate_is_not_a_civ_atlas_preview():
    habitat = _two_provinces()
    chronicle = simulate(habitat, CivSimConfig(
        seed=4, end_year=3, max_polities=2, found_period=1, found_jitter=0,
        min_capital_hops=1, expand_budget=-1_000_000_000,
        war_per_mille=1000, peace_per_mille=0, conquer_per_mille=1000,
    ))
    candidate = to_history_candidate(chronicle, base_year=3)
    assert candidate["kind"] == "zhimeng_civ_sim_history_candidate"
    assert candidate["kind"] != "civ_atlas_history_background"
    assert candidate["store_bridge"]["source_kind"] == "civ_sim"
    assert "field_status" in candidate and candidate["annals"]["events"]
    assert candidate["store_bridge"]["preview_written"] is False
    assert candidate["provenance"]["map_identity"] == "two-provinces"
    assert candidate["provenance"]["road_version"] == chronicle["snapshots"][3]["road_version"]
    events = candidate["annals"]["events"]
    assert events
    assert [event["year"] for event in events] == sorted(event["year"] for event in events)
    assert all(event["a_ref"] for event in events)
    assert all("ref" in event and "kind" in event and "region" in event for event in events)
    assert candidate["settlements"]["items"]  # capital proxies from alive polities
    assert all(item["location_id"] is None for item in candidate["settlements"]["items"])
    assert candidate["people"]["items"]  # monarchs / heirs when society on
    assert candidate["dynasties"]["items"]
    assert candidate["religion"]["items"]
