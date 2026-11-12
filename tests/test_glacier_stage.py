"""Small synthetic mechanism checks, not TD morphology acceptance."""
from copy import deepcopy

import numpy as np
import pytest

from app.world_gen.glacier_stage import (glacier_from_arrays, load_state,
                                         read_bed_region, save_product)


def run(years=2, **kwargs):
    options = dict(bed_m=np.full((5, 7), 3500.0), spacing_m=[100, 150],
                   first_xz_m=[1000, -2000], source_identity="synthetic-source",
                   terrain_identity="synthetic-terrain", source_kind="synthetic-test",
                   boundary="closed", target_years=years,
                   elevation_config={"generation_height_m": 3100}, annual_snow_cap_water_m=.5)
    options.update(kwargs)
    return glacier_from_arrays(**options)


def test_geometry_fixed_bed_units_and_native_schema():
    result = run()
    a, m, l = (result[key] for key in ("arrays", "metadata", "ledger"))
    assert m["completed"] and m["completed_years"] == 2
    assert result["state"]["physical_time_s"] == 2 * 365.25 * 86400
    np.testing.assert_array_equal(a["bed_m"], np.full((5, 7), 3500))
    np.testing.assert_allclose(a["ice_thickness_m"], 1/.917)
    np.testing.assert_allclose(a["ice_surface_m"], a["bed_m"] + a["ice_thickness_m"])
    assert l["accumulation_water_m3"] == pytest.approx(35 * 15000)
    assert abs(l["water_residual_m3"]) < 1e-8
    assert not m["hydrology_coupled"] and not m["default_world_published"]


def test_npz_crop_uses_cell_centres_not_edges(tmp_path):
    path = tmp_path / "mountain.npz"
    bed = np.arange(100).reshape(10, 10) + 3000
    np.savez(path, after_m=bed, spacing_m=[10], first_xz_m=[105, -195], ocean=np.zeros((10, 10), bool))
    args = read_bed_region(path, bed_key="after_m", region=[2, 3, 7, 10], ocean_key="ocean")
    assert args["first_xz_m"] == [135, -175]
    np.testing.assert_array_equal(args["bed_m"], bed[2:7, 3:10])
    with pytest.raises(ValueError, match="outside"):
        read_bed_region(path, bed_key="after_m", region=[0, 0, 12, 10])


def test_persist_restart_equals_whole(tmp_path):
    z, x = np.indices((5, 7))
    bed = 3250 - 20*x + (z-2)**2
    full = run(4, bed_m=bed)
    first = run(2, bed_m=bed)
    save_product(first, tmp_path / "first")
    loaded = load_state(tmp_path / "first" / "state.npz")
    resumed = run(4, bed_m=bed, state=loaded)
    for key in full["arrays"]:
        np.testing.assert_array_equal(resumed["arrays"][key], full["arrays"][key])
    assert resumed["state"]["total_substeps"] == full["state"]["total_substeps"]
    with pytest.raises(FileExistsError):
        save_product(first, tmp_path / "first")


def test_cumulative_budget_and_atomic_year():
    limited = run(3, config={"max_total_substeps": 13})
    assert limited["metadata"]["completed_years"] == 1
    assert not limited["metadata"]["completed"] and limited["metadata"]["stop_reason"]
    np.testing.assert_array_equal(limited["arrays"]["ice_thickness_m"], run(1)["arrays"]["ice_thickness_m"])
    again = run(3, state=limited["state"], config={"max_total_substeps": 13})
    assert again["metadata"]["completed_years"] == 1
    assert again["state"]["total_substeps"] == 13
    wall = deepcopy(run(1)["state"])
    wall["total_wall_s"] = 30.
    assert run(3, state=wall)["metadata"]["completed_years"] == 1
    with pytest.raises(ValueError, match="memory"):
        run(config={"max_memory_bytes": 1})


@pytest.mark.parametrize("change", [dict(source_identity="other"), dict(terrain_identity="other"),
    dict(source_kind="other"), dict(first_xz_m=[0, 0]), dict(spacing_m=200),
    dict(elevation_config={"generation_height_m": 3200}), dict(annual_snow_cap_water_m=.2),
    dict(boundary="outflow", outflow_sides=["east"])])
def test_restart_identity(change):
    state = run(1)["state"]
    with pytest.raises(ValueError, match="identity"):
        run(2, state=state, **change)


@pytest.mark.parametrize("bad", [dict(bed_m=np.full((5, 7), np.nan)),
    dict(bed_m=np.full((5, 7), -1.)), dict(bed_m=np.ones((514, 3))),
    dict(first_xz_m=[float("inf"), 0]), dict(spacing_m=0),
    dict(ocean_mask=np.ones((5, 7), bool)), dict(boundary="closed", outflow_sides=["east"]),
    dict(boundary="outflow"), dict(source_mask=np.ones((5, 7), float)),
    dict(annual_snow_cap_water_m=float("nan"))])
def test_invalid_fields_rejected(bad):
    with pytest.raises(ValueError):
        run(**bad)


def test_restart_finite_required_fields():
    state = deepcopy(run(1)["state"])
    state["ice_thickness_m"][0, 0] = np.nan
    with pytest.raises(ValueError, match="nonfinite"):
        run(state=state)
    state = deepcopy(run(1)["state"])
    del state["accumulation_water_m3"]
    with pytest.raises(ValueError, match="required"):
        run(state=state)


def test_source_mask_does_not_crop_ice_and_outflow_has_water_account():
    z, x = np.indices((5, 7))
    bed = 3500 - 5*x + z*0
    mask = np.zeros((5, 7), bool)
    mask[:, :3] = True
    result = run(3, bed_m=bed, source_mask=mask, boundary="outflow", outflow_sides=["east"])
    assert np.any(result["arrays"]["ice_thickness_m"][:, 3] > 0)
    assert not np.any(result["arrays"]["accumulation_water_m3"][:, 3:])
    assert "boundary_export_water_m3" in result["arrays"]
    assert abs(result["ledger"]["water_residual_m3"]) < 1e-7


def test_input_immutable_changed_bed_and_producer_rejected():
    bed = np.full((5, 7), 3500.)
    before = bed.copy()
    first = run(1, bed_m=bed)
    np.testing.assert_array_equal(bed, before)
    state_before = deepcopy(first["state"])
    run(2, bed_m=bed, state=first["state"])
    for key, value in state_before.items():
        np.testing.assert_equal(first["state"][key], value)
    bed[0, 0] += 1
    with pytest.raises(ValueError, match="identity"):
        run(2, bed_m=bed, state=first["state"])
    first["state"]["dream_adapter_identity"] = "different-producer"
    with pytest.raises(ValueError, match="producer identity"):
        run(2, state=first["state"])


def test_outflow_restart_and_required_export_fields():
    opts = dict(boundary="outflow", outflow_sides=["east"])
    first = run(1, **opts)
    resumed = run(2, state=first["state"], **opts)
    whole = run(2, **opts)
    for key in whole["arrays"]:
        np.testing.assert_array_equal(resumed["arrays"][key], whole["arrays"][key])
    del first["state"]["boundary_export_water_m3"]
    with pytest.raises(ValueError, match="required"):
        run(2, state=first["state"], **opts)


def test_cli_checkpoint_and_resume(tmp_path):
    from tools.generate_world_glaciers import main
    path = tmp_path / "mountains.npz"
    np.savez(path, bed_m=np.full((7, 9), 3500.), spacing_m=[10000], first_xz_m=[5000, 5000])
    common = ["--input", str(path), "--bed-key", "bed_m", "--region", "1", "2", "6", "9",
              "--source-identity", "synthetic", "--terrain-identity", "bed", "--source-kind", "synthetic",
              "--boundary", "closed", "--generation-height-m", "3100", "--annual-snow-cap-mwe", "1"]
    assert main(common + ["--target-years", "1", "--output", str(tmp_path / "one")]) == 0
    assert main(common + ["--target-years", "2", "--state", str(tmp_path / "one/state.npz"),
                          "--output", str(tmp_path / "two")]) == 0
    assert load_state(tmp_path / "two/state.npz")["completed_years"] == 2


def test_melt_handoff_time_window_and_pending_not_double_counted():
    z, x = np.indices((5, 7))
    bed = 3250 - 20*x + (z-2)**2
    first = run(1, bed_m=bed)
    resumed = run(3, bed_m=bed, state=first["state"])
    a, l, m = (resumed[key] for key in ("arrays", "ledger", "metadata"))
    np.testing.assert_array_equal(a["cumulative_melt_water_m3"], a["melt_water_m3"])
    np.testing.assert_array_equal(a["cumulative_melt_water_m3"], a["pending_melt_water_m3"])
    assert l["elapsed_physical_seconds"] == m["elapsed_physical_seconds"] == 3 * 365.25 * 86400
    assert l["completed_years"] == l["target_years"] == 3
    assert l["cumulative_melt_water_m3"] == pytest.approx(a["cumulative_melt_water_m3"].sum())
    assert "NEVER add both" in m["melt_handoff_contract"]["accounting"]
    assert "not total runoff" in m["melt_handoff_contract"]["interpretation"]


def test_edge_diagnostics_do_not_clear_ice_or_allow_threshold_composition():
    result = run(1, edge_ice_threshold_m=1000.)
    edge = result["metadata"]["edge_ice"]
    assert edge["positive_cells"] == 20
    assert edge["above_threshold_cells"] == 0
    assert edge["max_thickness_m"] > 0
    assert not edge["closed_edge_zero"]
    assert edge["composition_status"].startswith("finite-boundary-only")
    assert edge["exported_ice_m3"] == 0
    zero = run(0)
    assert zero["metadata"]["edge_ice"]["closed_edge_zero"]
    assert zero["ledger"]["elapsed_physical_seconds"] == 0
    assert zero["metadata"]["edge_ice"]["composition_status"] == "closed-edge-zero"
    limited = run(3, config={"max_total_substeps": 13})
    assert limited["ledger"]["elapsed_physical_seconds"] == 365.25 * 86400
    assert limited["ledger"]["completed_years"] == 1
    assert limited["ledger"]["target_years"] == 3
    for bad in (float("nan"), -1):
        with pytest.raises(ValueError, match="threshold"):
            run(edge_ice_threshold_m=bad)
