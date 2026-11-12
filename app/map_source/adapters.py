"""Format adapters. Identity/file hashing is shared with terrain_source."""
import copy
import math
from pathlib import Path

import numpy as np

from app import terrain_source as ts
from .core import ArrayGrid, GridSource
from .types import SourceInfo, STANDARD_LAYERS


def _info(kind, manifest, grid, layers, vectors=(), **extra):
    config = manifest.get("config", manifest)
    seed = config["world_seed"]
    ts._require(type(seed) is int, "world_seed must be an integer")
    lineage = manifest.get("lineage", [manifest["source_identity"]] if "source_identity" in manifest else [])
    ts._require(isinstance(lineage, list) and all(ts._hex(v) for v in lineage), "Invalid lineage")
    values = dict(
        kind=kind, schema=manifest["schema"], identity=grid.identity,
        lineage=tuple(lineage), producer=manifest.get("producer", "terragenesis" if kind != "world-relief-pilot" else "dream/" + manifest["schema"]),
        world_seed=seed, subseeds=copy.deepcopy(manifest.get("subseeds", {})),
        algorithm_version=manifest.get("algorithm_version", ""),
        subseed_method=manifest.get("subseed_method", ""), extent_m=grid.extent_m,
        spacing_m=grid.spacing_m, first_sample_xz_m=grid.first_xz_m,
        shape_zx=grid.shape_zx, grid_semantics=grid.grid_semantics,
        boundary="finite; no wrap", layers=tuple(layers), vectors=tuple(vectors),
        declared_generated=copy.deepcopy(manifest.get("declared_generated", [])),
        limitations=copy.deepcopy(manifest.get("limitations", [])),
        elevation_meaning="bed: terrain/river/lake bed, not water surface",
    )
    values.update(extra)
    values["derivations"] = (*values.get("derivations", ()), "elevation bilinear; status and optional layers nearest; no optional-layer interpolation across nodata")
    return SourceInfo(**values)


def load_native(path, *, expected_identity=None):
    grid = ts.load_native_terrain(path, expected_identity=expected_identity)
    info = _info(grid.kind, grid.manifest, grid, ("status", "elevation_m"), grid_semantics="native-sample",
                 layer_metadata={"elevation_m": {"unit": "m", "meaning": grid.provenance()["elevation_meaning"]}},
                 derivations=("status mapped from valid/ocean/unknown/closed masks",))
    return GridSource(grid, info)


def load_tectonic(path, *, expected_identity=None):
    grid = ts.load_tectonic_product(path, expected_identity=expected_identity)
    return GridSource(grid, _info(grid.kind, grid.manifest, grid, ("status", "elevation_m"),
                      grid_semantics=grid.manifest["coordinates"]["grid"],
                      elevation_meaning="macro buoyancy proxy, not ground surface",
                      derivations=("status from ocean_connected; disconnected negative elevations map to 4",)))


def _file(path, name, expected):
    ts._require(isinstance(name, str), "Invalid product filename")
    root = Path(path).resolve()
    target = (root / name).resolve()
    ts._require(target.is_relative_to(root), f"File outside product: {name!r}")
    ts._require(ts._hex(expected) and ts._file_sha256(target) == expected, f"File hash mismatch: {name}")
    return target


def _array(path, name, expected, shape, dtype):
    array = np.load(_file(path, name, expected), mmap_mode="r", allow_pickle=False)
    ts._require(array.shape == shape and array.dtype == np.dtype(dtype) and array.flags.c_contiguous, f"Invalid array shape/dtype/order: {name}")
    return array


def _grid(kind, manifest, spacing, first, shape, arrays):
    ts._require(isinstance(first, (list, tuple)) and len(first) == 2 and all(type(v) in (int, float) and math.isfinite(v) for v in first), "Invalid first sample")
    ts._require(type(spacing) in (int, float) and math.isfinite(spacing) and spacing > 0, "Invalid spacing")
    for array in arrays.values():
        array.flags.writeable = False
    grid = ArrayGrid(kind, manifest["identity"], "", spacing, first, arrays["elevation_m"], [arrays["status"]])
    grid.world_seed = manifest["world_seed"]
    ts._require(grid.shape_zx == shape, "Grid shape mismatch")
    return grid


def _validate_vectors(kind, items):
    ts._require(isinstance(items, list), f"Invalid {kind} list")
    ids = [v["id"] for v in items]
    ts._require(all(isinstance(v, str) and v for v in ids) and len(set(ids)) == len(ids), f"Duplicate or invalid {kind} IDs")
    ids = set(ids)
    for item in items:
        points = np.asarray(item["points_xz_m" if kind == "rivers" else "ring_xz_m"], dtype=float)
        ts._require(points.ndim == 2 and points.shape[1] == 2 and len(points) >= (2 if kind == "rivers" else 3) and np.all(np.isfinite(points)), "Invalid vector coordinates")
        if kind == "rivers":
            downstream = item["downstream_id"]
            upstream = item["upstream_ids"]
            ts._require(downstream is None or downstream in ids, "Unresolved downstream_id")
            ts._require(isinstance(upstream, list) and len(set(upstream)) == len(upstream) and all(v in ids for v in upstream), "Unresolved upstream_ids")
            ts._require(item["outlet"] in ("ocean", "lake", "closed", "edge"), "Invalid river outlet")
            ts._require(math.isfinite(item["drainage_area_m2"]) and item["drainage_area_m2"] >= 0, "Invalid drainage area")
            if "discharge_m3_s" in item:
                ts._require(math.isfinite(item["discharge_m3_s"]) and item["discharge_m3_s"] >= 0, "Invalid discharge")
        else:
            ts._require(math.isfinite(item["surface_m"]), "Invalid lake surface")
    if kind == "rivers":
        by_id = {item["id"]: item for item in items}
        # Build the reverse topology once instead of rescanning all rivers per edge.
        # The same membership, reciprocity and cycle checks still apply.
        upstream_by_id = {identifier: [] for identifier in by_id}
        for item in items:
            downstream = item["downstream_id"]
            if downstream is not None:
                upstream_by_id[downstream].append(item["id"])
        for item in items:
            expected = sorted(upstream_by_id[item["id"]])
            ts._require(sorted(item["upstream_ids"]) == expected, "Non-reciprocal river topology")
        done = set()
        for identifier in ids:
            chain = set()
            while identifier is not None and identifier not in done:
                ts._require(identifier not in chain, "Cyclic river topology")
                chain.add(identifier)
                identifier = by_id[identifier]["downstream_id"]
            done.update(chain)
    return items


def load_relief(path, *, expected_identity=None):
    path = Path(path)
    manifest = ts._json((path / "manifest.json").read_text(encoding="utf-8"))
    ts._identity(manifest, {"identity"}, expected_identity)
    shape = ts._shape(manifest["shape_zx"])
    ts._require(manifest["axes"] == "arrays [z,x]; X east; Z south; metres; cell centres; sea=0", "Invalid relief axes")
    ts._require("no wrap" in manifest["boundary"] and "finite" in manifest["boundary"], "Invalid relief boundary")
    arrays = {}
    for name in ("elevation_m", "ocean_mask", "inland_depression_mask", "lake_surface_m", "drainage_area_m2"):
        dtype = "bool" if name.endswith("mask") else "float32"
        arrays[name] = _array(path, name + ".npy", manifest["files"][name + ".npy"], shape, dtype)
    ocean, closed = arrays["ocean_mask"], arrays["inland_depression_mask"]
    arrays["status"] = np.where(ocean, ts.OCEAN, np.where(closed, ts.CLOSED_BELOW_SEA, ts.LAND)).astype(np.uint8)
    # filled_m is also equal to the bed on dry land and ocean: not actual water.
    wet = ~ocean & ((arrays["lake_surface_m"] > arrays["elevation_m"]) | closed)
    water = np.where(wet, arrays["lake_surface_m"], np.nan).astype(np.float32)
    grid = _grid("world-relief-pilot", manifest, manifest["spacing_m"], manifest["first_sample_xz_m"], shape, arrays)
    grid.grid_semantics = "cell-centre"
    raw = ts._json(_file(path, "rivers.json", manifest["files"]["rivers.json"]).read_text(encoding="utf-8"))
    ts._require(raw["schema"] == "coordinate-river-segments-v1", "Unsupported relief river schema")
    lines = []
    for line in raw["lines"]:
        lines.append(dict(id=line["id"], points_xz_m=line["coordinates_xz_m"],
                          downstream_id=line["downstream_id"], upstream_ids=line["upstream_ids"],
                          drainage_area_m2=line["outlet_area_km2"] * 1e6,
                          head_drainage_area_m2=line["head_area_km2"] * 1e6))
    by_id = {line["id"]: line for line in lines}
    ts._require(len(by_id) == len(lines), "Duplicate river IDs")
    outlets = {}
    for line in lines:
        chain, seen, end = [], set(), line
        while end["id"] not in outlets:
            ts._require(end["id"] not in seen, "Cyclic river topology")
            seen.add(end["id"])
            chain.append(end["id"])
            downstream = end["downstream_id"]
            if downstream is None:
                point = end["points_xz_m"][-1]
                ix, iz = (int(round((point[i] - grid.first_xz_m[i]) / grid.spacing_m)) for i in range(2))
                ts._require(0 <= ix < shape[1] and 0 <= iz < shape[0], "River endpoint outside grid")
                outlet = "ocean" if ocean[iz, ix] else "edge" if iz in (0, shape[0]-1) or ix in (0, shape[1]-1) else "lake" if wet[iz, ix] else "closed"
                outlets[end["id"]] = outlet
                break
            ts._require(downstream in by_id, "Unresolved downstream_id")
            end = by_id[downstream]
        for identifier in chain:
            outlets[identifier] = outlets[end["id"]]
    for line in lines:
        line["outlet"] = outlets[line["id"]]
    _validate_vectors("rivers", lines)
    derivations = (
        "status: ocean_mask -> 3; else inland_depression_mask -> 4; else -> 5 (4 includes above-sea depressions)",
        "water_surface_m: lake_surface_m only on non-ocean cells where filled surface > bed or inland_depression_mask; priority-flood potential water, not observed/permanent water",
        "rivers-v1: stable IDs/topology preserved; outlet_area_km2 * 1e6 -> drainage_area_m2; outlet propagated from terminal endpoint (ocean, rim=edge, wet=lake, otherwise closed)",
    )
    extras = {"water_surface_m": water, "drainage_area_m2": arrays["drainage_area_m2"]}
    info = _info(grid.kind, manifest, grid, ("status", "elevation_m", *extras), ("rivers",),
                 grid_semantics="cell-centre", derivations=derivations,
                 layer_metadata={name: {"unit": STANDARD_LAYERS[name]} for name in ("status", "elevation_m", *extras)})
    return GridSource(grid, info, extras, {"rivers": lines})


def load_world_map(path, *, expected_identity=None):
    path = Path(path)
    manifest = ts._json((path / "manifest.json").read_text(encoding="utf-8"))
    ts._identity(manifest, {"identity", "source_path"}, expected_identity)
    process = manifest.get('world_processes')
    if process is not None:
        saved = ts._json(_file(path, process['file'], process['sha256']).read_text(encoding='utf-8'))
        metadata = saved['metadata']
        ts._require(metadata == process['metadata'], 'World process metadata binding differs')
        ts._require(metadata['world_seed'] == manifest['world_seed'], 'World process seed binding differs')
        ts._require(metadata['first_xz_m'] == manifest['grid']['first_sample_xz_m'] and
                    metadata['spacing_m'] == manifest['grid']['spacing_m'], 'World process coordinate binding differs')
    ts._require(manifest["ready"] is True, "Product is not ready")
    for key in ("producer", "algorithm_version", "lineage", "world_seed", "subseed_method", "subseeds", "declared_generated", "limitations", "vectors"):
        ts._require(key in manifest, f"Missing manifest field: {key}")
    grid_spec = manifest["grid"]
    ts._require(grid_spec["axes"] == "X east, Z south; arrays [z,x]" and grid_spec["length_unit"] == "m" and grid_spec["sea_level_m"] == 0, "Invalid world-map axes/unit/sea level")
    ts._require(grid_spec["semantics"] in ("cell-centre", "native-sample"), "Invalid grid semantics")
    shape = ts._shape(grid_spec["shape_zx"])
    layers = manifest["layers"]
    ts._require(isinstance(layers, dict) and {"status", "elevation_m"} <= layers.keys(), "Missing required layers")
    arrays, metadata = {}, {}
    for name, spec in layers.items():
        # Unknown future fields/layers are ignored, never exposed as standard layers.
        if name not in STANDARD_LAYERS:
            continue
        for key in ("file", "sha256", "dtype", "unit", "meaning", "nodata"):
            ts._require(key in spec, f"Missing {name} field: {key}")
        ts._require(spec["unit"] == STANDARD_LAYERS[name], f"Invalid unit for {name}")
        array = _array(path, spec["file"], spec["sha256"], shape, spec["dtype"])
        if spec.get('process_identity') is not None:
            ts._require(process is not None and spec['process_identity']==saved['identity'],
                        'Environment layer belongs to another process revision')
            ts._require(name in saved['arrays'],'Environment field missing from bound process')
            p_spec=saved['arrays'][name]
            p_value=np.load(_file((path/process['file']).parent,p_spec['file'],p_spec['sha256']),mmap_mode='r',allow_pickle=False)
            ts._require(np.array_equal(array,np.asarray(p_value,dtype=array.dtype),equal_nan=True),
                        'Environment field differs from bound process arrays')
        if name == "status":
            ts._require(array.dtype.kind in "ui", "Status must be integer")
            mapping = manifest.get("status_codes")
            if mapping:
                ts._require(isinstance(mapping, dict), "status_codes must map source integer strings to standard integers")
                converted = np.full(shape, ts.UNKNOWN, dtype=np.uint8)
                covered = np.zeros(shape, dtype=bool)
                for old, new in mapping.items():
                    ts._require(type(new) is int and 0 <= new <= 5, "Invalid status mapping")
                    match = array == int(old)
                    converted[match] = new
                    covered |= match
                ts._require(np.all(covered), "Unmapped status value")
                array = converted
            else:
                ts._require(array.dtype == np.dtype("uint8") and np.all(array <= 5), "Invalid status codes/dtype")
        elif name in ("biome", "rock_index"):
            ts._require(array.dtype.kind in "ui", "biome must use integer categories")
        else:
            ts._require(array.dtype.kind == "f", f"{name} must be floating point")
            if spec["nodata"] is not None:
                array = np.where(array == spec["nodata"], np.nan, array)
        if name == "discharge_m3_s":
            ts._require(bool(spec.get("scenario")), "Discharge requires scenario")
        if name in ("temperature_c", "precipitation_mm_yr", "biome"):
            ts._require(bool(spec.get("source")) and "approximation" in spec, f"{name} requires source and approximation")
        array.flags.writeable = False
        arrays[name], metadata[name] = array, copy.deepcopy(spec)
    grid = _grid("world-map-product", manifest, grid_spec["spacing_m"], grid_spec["first_sample_xz_m"], shape, arrays)
    grid.grid_semantics = grid_spec["semantics"]
    vectors = {}
    for kind, spec in manifest["vectors"].items():
        if kind not in ("rivers", "lakes"):
            continue
        schema = kind + "-v1"
        ts._require(spec["schema"] == schema, f"Unsupported vector schema: {spec['schema']!r}")
        value = ts._json(_file(path, spec["file"], spec["sha256"]).read_text(encoding="utf-8"))
        ts._require(value["schema"] == schema, "Vector schema mismatch")
        vectors[kind] = _validate_vectors(kind, value["lines" if kind == "rivers" else "lakes"])
    info = _info(grid.kind, manifest, grid, arrays, vectors, elevation_meaning=layers["elevation_m"]["meaning"],
                 layer_metadata=metadata, derivations=("optional numeric layers sampled nearest; elevation bilinear; no water spread across nodata",))
    return GridSource(grid, info, {k: v for k, v in arrays.items() if k not in ("status", "elevation_m")}, vectors)


def load_td_world(path, *, expected_identity=None):
    """td-world-960m-v1: the generic world-map loader plus a hash check of every file the manifest lists.

    Identity is recomputed by load_world_map; here the remaining manifest files (masks, receiver, coordinate
    rivers.json ...) are hashed too so a tampered diagnostic file is also refused. A manifest without `files`
    (contract fixtures) skips only this extra step.
    """
    source = load_world_map(path, expected_identity=expected_identity)
    manifest = ts._json((Path(path) / "manifest.json").read_text(encoding="utf-8"))
    files = manifest.get("files")
    if files is not None:
        ts._require(isinstance(files, dict) and files, "Invalid files table")
        for name, digest in files.items():
            _file(path, name, digest)
    return source


LOCAL30_KIND = "terragenesis-local30"
LOCAL30_SCHEMA = "terragenesis-local30-v1"
CLIMATE_KIND = "terragenesis-regional-climate"
CLIMATE_SCHEMA = "terragenesis-regional-climate-v1"


def load_local30(path, *, expected_identity=None):
    """terragenesis-local30-v1: a 30 m native-sample window written by app.world_gen.local30.

    Same on-disk layout as world-map-product (manifest.json + layers/*.npy); the generic loader validates identity,
    layer hashes and axes, then the source is relabelled so callers see the finer kind and the catalog can prefer it.
    """
    from dataclasses import replace
    source = load_world_map(path, expected_identity=expected_identity)
    manifest = ts._json((Path(path) / "manifest.json").read_text(encoding="utf-8"))
    ts._require(manifest["schema"] == LOCAL30_SCHEMA, "Not a local30 manifest")
    ts._require(source.info.spacing_m == 30 and source.info.grid_semantics == "native-sample", "local30 requires 30 m native-sample grid")
    source._grid.kind = LOCAL30_KIND
    source.info = replace(source.info, kind=LOCAL30_KIND)
    return source


def load_regional_climate(path, *, expected_identity=None):
    """``terragenesis-regional-climate-v1``: annual climate on the parent world grid.

    Validates through Terragenesis ``query_climate`` (converged only). ``elevation_m`` is a
    zero placeholder for grid geometry; ``temperature_c`` is the annual mean. Monthly fields
    stay on ``SavedClimateMap`` / climate HTTP routes.
    """
    from app.world_gen import terragenesis_bridge as bridge
    bridge.ensure_path()
    from terrain_pipeline import world_climate

    root = Path(path).resolve()
    manifest = ts._json((root / "manifest.json").read_text(encoding="utf-8"))
    ts._require(manifest.get("schema") == CLIMATE_SCHEMA, "Not a regional climate manifest")
    field_names = ["ocean_mask", "temperature_c"]
    if "precipitation_mm_yr" in (manifest.get("fields") or {}):
        field_names.append("precipitation_mm_yr")
    loaded = world_climate.query_climate(root, fields=field_names, allow_candidate=False)
    meta = loaded["metadata"]
    if expected_identity is not None:
        ts._require(meta.get("identity") == expected_identity, "Expected climate identity mismatch")
    ocean = np.asarray(loaded["arrays"]["ocean_mask"])
    temperature = np.asarray(loaded["arrays"]["temperature_c"], dtype=np.float32)
    ts._require(ocean.shape == temperature.shape, "Climate field shape mismatch")
    status = np.where(ocean, np.uint8(3), np.uint8(5))
    elevation = np.zeros(temperature.shape, dtype=np.float32)
    shape = tuple(int(v) for v in meta["shape_zx"])
    first = tuple(float(v) for v in meta["first_xz_m"])
    spacing = float(meta["spacing_m"])
    seed = int(meta["world_seed"])
    identity = meta["identity"]
    ts._require(ts._hex(identity), "Invalid climate identity")
    fake_manifest = dict(
        schema=CLIMATE_SCHEMA, identity=identity, world_seed=seed,
        producer="terragenesis/world_climate", algorithm_version=str(meta.get("algorithm", "")),
        lineage=[meta.get("source_identity") or identity],
        limitations=["elevation_m is a zero placeholder; bed lives on the parent world-map-product",
                     "monthly climate fields are not exposed here; use SavedClimateMap"],
        declared_generated=["regional climate annual fields"],
    )
    arrays = {"elevation_m": elevation, "status": status, "temperature_c": temperature}
    if "precipitation_mm_yr" in loaded["arrays"]:
        arrays["precipitation_mm_yr"] = np.asarray(loaded["arrays"]["precipitation_mm_yr"], dtype=np.float32)
    grid = _grid(CLIMATE_KIND, fake_manifest, spacing, first, shape, arrays)
    metadata = {
        "elevation_m": {"unit": "m", "meaning": "placeholder zeros; not terrain bed"},
        "temperature_c": {"unit": "degC", "source": "terragenesis-regional-climate",
                          "approximation": "annual mean from monthly climate product"},
    }
    if "precipitation_mm_yr" in arrays:
        metadata["precipitation_mm_yr"] = {
            "unit": "mm/yr", "source": "terragenesis-regional-climate",
            "approximation": "annual total from climate product",
        }
    info = _info(CLIMATE_KIND, fake_manifest, grid, tuple(arrays),
                 elevation_meaning=metadata["elevation_m"]["meaning"],
                 layer_metadata=metadata, grid_semantics="cell-centre",
                 derivations=("status from climate ocean_mask; temperature nearest; no bed",))
    extras = {k: v for k, v in arrays.items() if k not in ("status", "elevation_m")}
    return GridSource(grid, info, extras)
