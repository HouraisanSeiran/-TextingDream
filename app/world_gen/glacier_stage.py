"""Opt-in, bounded TG mountain glacier adapter; no terrain regeneration or routing.

Contract: TG generate_mountain_glacier has IMMUTABLE bed (live-bed erosion is
only in its separate flowline entry). H/surface/bed are metres, cumulative melt
and water residual are m3 WATER, faces/cell ice residual are m3 ICE. Physical
seconds use 365.25-day years; target_years is absolute, saved years transactional.
Engineering ELA is not climate, annual external snow is not a native snow debit.
A source mask limits accumulation ONLY. Choose a land-only rectangular region;
we never delete ocean ice or crop a simulated ice body to manufacture a seam.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

import numpy as np

from app.world_gen.terragenesis_bridge import ensure_path, tg_root

SCHEMA = "dream-tg-glacier-region-1"


def _kernel():
    ensure_path()
    # Read-only imports must not populate the neighbouring TG source cache.
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        from terrain_pipeline import world_glacier
        return world_glacier
    finally:
        sys.dont_write_bytecode = previous


def _producer():
    files = ("world_glacier.py", "environment_processes.py", "common_infra.py")
    return {name: hashlib.sha256((tg_root() / "terrain_pipeline" / name).read_bytes()).hexdigest()
            for name in files}


def _identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def _region(region, shape):
    if (not isinstance(region, (list, tuple)) or len(region) != 4
            or any(type(v) is not int for v in region)):
        raise ValueError("explicit integer region [z0,x0,z1,x1] required")
    z0, x0, z1, x1 = region
    if not (0 <= z0 < z1 <= shape[0] and 0 <= x0 < x1 <= shape[1]):
        raise ValueError("region outside source; no silent clipping")
    return slice(z0, z1), slice(x0, x1)


def read_bed_region(path, *, bed_key, region, spacing_m=None, first_xz_m=None,
                    ocean_key=None):
    """Read a named NPZ bed without resampling; region is half-open [z,x,z,x].

    NPZ first_xz_m is a CELL CENTRE, not the rectangular extent's lower edge.
    For other schemas explicitly supply spacing_m/first_xz_m from their metadata.
    Returns keyword arguments suitable for glacier_from_arrays.
    """
    with np.load(path, allow_pickle=False) as data:
        bed = np.asarray(data[bed_key], dtype=np.float64)
        if bed.ndim != 2:
            raise ValueError("2D source bed required")
        slices = _region(region, bed.shape)
        spacing = spacing_m if spacing_m is not None else data["spacing_m"]
        first = first_xz_m if first_xz_m is not None else data["first_xz_m"]
        dx, dz = _spacing(spacing)
        origin = np.asarray(first, dtype=float)
        if origin.shape != (2,) or not np.isfinite(origin).all():
            raise ValueError("finite first cell centre [X,Z] required")
        ocean = None
        if ocean_key is not None:
            mask = data[ocean_key]
            if mask.shape != bed.shape or mask.dtype != np.dtype(bool):
                raise ValueError("boolean ocean mask must match source bed")
            ocean = mask[slices].copy()
        return dict(bed_m=bed[slices].copy(), spacing_m=[dx, dz],
                    first_xz_m=[origin[0] + region[1] * dx, origin[1] + region[0] * dz],
                    ocean_mask=ocean)


def _spacing(value):
    values = np.asarray(value, dtype=float).reshape(-1)
    if values.size not in (1, 2) or not np.isfinite(values).all() or np.any(values <= 0):
        raise ValueError("positive spacing scalar or [dx,dz] required")
    return float(values[0]), float(values[-1])


def _finite_fields(fields):
    for name, value in fields.items():
        a = np.asarray(value)
        if a.dtype.kind in "biufc" and not np.isfinite(a).all():
            raise ValueError("nonfinite field: " + name)


def load_state(path):
    """Load flat native state without pickle; scalar values restored as scalars."""
    with np.load(path, allow_pickle=False) as data:
        state = {k: v.item() if v.ndim == 0 else v.copy() for k, v in data.items()}
    _finite_fields(state)
    return state


def glacier_from_arrays(bed_m, *, spacing_m, first_xz_m, source_identity,
                        terrain_identity, source_kind, boundary, target_years,
                        elevation_config, state=None, source_mask=None,
                        annual_snow_cap_water_m=None, ocean_mask=None,
                        outflow_sides=(), config=None, provenance=None,
                        edge_ice_threshold_m=1.0):
    """Advance ONE bounded land region using TG, preserving its native schema.

    first_xz_m is the first cell CENTRE. boundary must be explicit 'closed' or
    'outflow'; outflow_sides must name chosen edges. Independent/overlapping
    region outputs are NOT seamless and must not be summed as world inventory.
    The geometry bed is copied, never modified or reconstructed from state.
    """
    threshold = float(edge_ice_threshold_m)
    if not np.isfinite(threshold) or threshold < 0:
        raise ValueError("finite nonnegative edge ice diagnostic threshold required")
    for value in (source_identity, terrain_identity, source_kind):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("explicit nonempty source/terrain identity and source_kind required")
    bed = np.array(bed_m, dtype=np.float64, copy=True)
    if bed.ndim != 2 or min(bed.shape) < 3 or max(bed.shape) > 513 or not np.isfinite(bed).all():
        raise ValueError("finite bed [z,x] with each axis 3..513 required")
    sea = float(elevation_config.get("sea_level_m", 0.0))
    if not np.isfinite(sea) or np.any(bed <= sea):
        raise ValueError("choose a land-only region above sea level; no post-hoc ice masking")
    if ocean_mask is not None:
        ocean = np.asarray(ocean_mask)
        if ocean.shape != bed.shape or ocean.dtype != np.dtype(bool) or ocean.any():
            raise ValueError("choose an ocean-free region with a matching boolean mask")
    dx, dz = _spacing(spacing_m)
    origin = np.asarray(first_xz_m, dtype=float)
    if origin.shape != (2,) or not np.isfinite(origin).all():
        raise ValueError("finite first cell centre [X,Z] required")
    sides = list(outflow_sides)
    if boundary not in ("closed", "outflow") or (boundary == "closed" and sides) or (boundary == "outflow" and not sides):
        raise ValueError("explicit closed boundary or outflow with selected sides required")
    cfg = dict(config or {})
    if "outflow_sides" in cfg:
        raise ValueError("set boundary/outflow_sides explicitly, not through config")
    cfg["outflow_sides"] = sides
    cfg.setdefault("effective_sliding_speed_m_per_year", 0.0)
    cfg.setdefault("max_total_wall_s", 30.0)
    cfg.setdefault("max_memory_bytes", 256 * 1024**2)
    producer = _producer()
    binding = _identity(dict(schema=SCHEMA, producer=producer, source_kind=source_kind))
    if state is not None:
        _finite_fields(state)
        required = {"model_identity", "geometry_identity", "kernel_model_identity", "forcing_identity",
                    "completed_years", "physical_time_s", "ice_thickness_m", "pending_melt_water_m3",
                    "total_substeps", "total_wall_s", "accumulation_water_m3", "melt_water_m3",
                    "face_x_ice_transfer_m3", "face_z_ice_transfer_m3", "dream_adapter_identity"}
        if sides:
            required.update(("boundary_export_ice_m3", "boundary_export_water_m3"))
        if cfg["effective_sliding_speed_m_per_year"] > 0:
            required.update("face_" + axis + "_" + part + "_ice_transfer_m3"
                            for axis in "xz" for part in ("sia", "slide"))
        if not required.issubset(state) or state["dream_adapter_identity"] != binding:
            raise ValueError("restart adapter/producer identity or required state fields differ")
        for name in ("completed_years", "total_substeps"):
            if type(state[name]) is not int or state[name] < 0:
                raise ValueError("nonnegative integer restart counter required: " + name)
    geometry = dict(bed_m=bed, dx_m=dx, dz_m=dz, origin_xz_m=origin.tolist(),
                    source_identity=source_identity, terrain_identity=terrain_identity)
    result = _kernel().generate_mountain_glacier(
        geometry, state, target_years=target_years, elevation_config=elevation_config,
        source_mask=source_mask, annual_snow_cap_water_m=annual_snow_cap_water_m, config=cfg)
    _finite_fields(result["state"])
    _finite_fields(result["arrays"])
    result["state"]["dream_adapter_identity"] = binding
    # Native melt_water_m3 is already cumulative since experiment time zero.
    # This alias is the generated melt component for a downstream explicit
    # handoff. Pending is the retained inventory of that SAME water, not an
    # additional source. No consumer/debit protocol is implemented here.
    arrays, ledger = result["arrays"], result["ledger"]
    arrays["cumulative_melt_water_m3"] = arrays["melt_water_m3"]
    elapsed = float(result["state"]["physical_time_s"])
    ledger.update(elapsed_physical_seconds=elapsed,
                  completed_years=result["metadata"]["completed_years"], target_years=target_years,
                  cumulative_melt_water_m3=ledger["melt_water_m3"])
    h = arrays["ice_thickness_m"]
    edge = np.zeros(h.shape, dtype=bool)
    edge[[0, -1], :] = True
    edge[:, [0, -1]] = True
    closed_edge_zero = boundary == "closed" and not np.any(h[edge] > 0)
    edge_status = dict(
        threshold_m=threshold, max_thickness_m=float(h[edge].max()),
        positive_cells=int(np.count_nonzero(h[edge] > 0)),
        above_threshold_cells=int(np.count_nonzero(h[edge] > threshold)),
        side_max_thickness_m=dict(west=float(h[:, 0].max()), east=float(h[:, -1].max()),
                                  north=float(h[0, :].max()), south=float(h[-1, :].max())),
        exported_ice_m3=ledger["boundary_ice_out_m3"],
        exported_ice_water_equivalent_m3=ledger.get("boundary_water_out_m3", 0.0),
        closed_edge_zero=closed_edge_zero,
        composition_status=("closed-edge-zero" if closed_edge_zero else
                            "finite-boundary-only; enlarge region or explicitly retain its boundary limitation"))
    result["metadata"].update(
        elapsed_physical_seconds=elapsed, physical_start_s=0.0,
        physical_end_s=elapsed, edge_ice=edge_status,
        melt_handoff_contract={
            "component_array": "cumulative_melt_water_m3", "units": "m3 water per cell",
            "time_window": "experiment physical_start_s=0 to physical_end_s; includes saved continuation",
            "pending_array": "pending_melt_water_m3",
            "accounting": "cumulative generated melt and retained pending stock are the same water; NEVER add both; no handoff/debit yet",
            "interpretation": "cumulative melt only, not total runoff; dividing by elapsed seconds gives only this window mean melt component; zero elapsed has no rate"},
        domain_semantics="all local cells simulated; outside this region is unmodelled, NOT verified ice-free",
    )
    result["metadata"].update(
        adapter_schema=SCHEMA, adapter_identity=binding, tg_producer_sha256=producer,
        source_kind=source_kind, shape_zx=list(bed.shape), first_xz_m=origin.tolist(),
        grid_semantics="first cell centre; arrays[z,x]; X east/Z south; metres",
        boundary=boundary, selected_outflow_sides=sides, bed_evolution="immutable; no erosion",
        units="bed/H/surface: m; annual forcing: m water/year; water sums/residual: m3 water; faces/cell residual: m3 ice; physical_time_s: SI seconds",
        memory_budget_semantics="TG conservative live-array estimate, not an OS RSS hard cap; runtime overhead separate",
        hydrology_coupled=False, default_world_published=False,
        region_continuity="independent finite window, NOT seamless; overlapping inventories must not be summed",
        provenance=provenance or {}, operational_config=cfg,
        arrays_schema={k: dict(shape=list(v.shape), dtype=str(v.dtype)) for k, v in result["arrays"].items()})
    return result


def save_product(result, output):
    """Write a new directory atomically. Native state/arrays and JSON companions."""
    output = Path(output).resolve()
    if output == tg_root().resolve() or tg_root().resolve() in output.parents:
        raise ValueError("TG source workspace is read-only")
    if output.exists():
        raise FileExistsError("new output directory required; resume to a new directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".glacier-", dir=output.parent))
    try:
        np.savez_compressed(staging / "state.npz", **result["state"])
        np.savez_compressed(staging / "arrays.npz", **result["arrays"])
        for key in ("ledger", "metadata"):
            (staging / (key + ".json")).write_text(
                json.dumps(result[key], ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        staging.rename(output)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return output
