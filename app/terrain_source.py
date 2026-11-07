"""Read-only, finite planar terrain products; no terrain generation dependencies."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re

import numpy as np

WORLD_SEED = 20261020
NATIVE_SPACING_M = 30
UNPREPARED, OUT_OF_BOUNDS, UNKNOWN, OCEAN, CLOSED_BELOW_SEA, LAND = range(6)
STATUS_NAMES = dict(enumerate(("unprepared", "out_of_bounds", "unknown", "ocean", "closed_below_sea", "land")))
_NATIVE_FILES = ("bed_m", "valid_mask", "ocean_mask", "unknown_mask", "closed_below_sea_mask")


class TerrainSourceError(ValueError):
    """Invalid terrain product, configuration, or query."""


def _canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise TerrainSourceError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _json(text):
    return json.loads(text, object_pairs_hook=_pairs)


def _require(condition, message):
    if not condition:
        raise TerrainSourceError(message)


def _hex(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value) is not None


def _shape(value):
    _require(isinstance(value, (list, tuple)) and len(value) == 2 and all(type(n) is int and n > 0 for n in value), "Invalid shape_zx")
    return tuple(value)


def _identity(manifest, excluded, expected):
    identity = hashlib.sha256(_canon({k: v for k, v in manifest.items() if k not in excluded}).encode()).hexdigest()
    _require(_hex(manifest.get("identity")) and manifest["identity"] == identity, "Manifest identity mismatch")
    _require(expected is None or expected == identity, "Expected identity mismatch")
    return identity


def _coordinates(x, z):
    try:
        x, z = np.broadcast_arrays(np.asarray(x, dtype=np.float64), np.asarray(z, dtype=np.float64))
    except (ValueError, TypeError, OverflowError) as exc:
        raise TerrainSourceError("Invalid coordinates") from exc
    _require(np.all(np.isfinite(x)) and np.all(np.isfinite(z)), "Coordinates must be finite")
    return x, z


class _GridProduct:
    def __init__(self, kind, identity, path, spacing, first, elevation, masks):
        self.kind = kind
        self.identity = identity
        self.path = str(path)
        self.spacing_m = float(spacing)
        self.first_xz_m = tuple(float(v) for v in first)
        self.shape_zx = elevation.shape
        self._elevation = elevation
        self._masks = masks
        self.grid_semantics = "native samples; no half-cell offset" if kind == "native-terrain-v3" else "cell centres; finite domain"
        self.unverified_files = []

    @property
    def extent_m(self):
        x, z = self.first_xz_m
        nz, nx = self.shape_zx
        return x, z, x + (nx - 1) * self.spacing_m, z + (nz - 1) * self.spacing_m

    def provenance(self):
        native = self.kind == "native-terrain-v3"
        result = dict(kind=self.kind, identity=self.identity, path=self.path, spacing_m=self.spacing_m,
                      first_sample_xz_m=self.first_xz_m, shape_zx=self.shape_zx,
                      grid_semantics=self.grid_semantics,
                      elevation_meaning="bed: terrain/river/lake bed, not water surface" if native else "macro buoyancy surface elevation",
                      axes="X east, Z south; arrays [z,x]", length_unit="m", sea_level_m=0,
                      world_seed=self.world_seed, boundary="finite; no wrap")
        if native:
            result["unverified_files"] = list(self.unverified_files)
        return result

    def _status(self, iz, ix):
        if self.kind == "native-terrain-v3":
            valid, ocean, unknown, closed = (mask[iz, ix] for mask in self._masks)
            return np.asarray(np.where(~valid | unknown, UNKNOWN, np.where(ocean, OCEAN, np.where(closed, CLOSED_BELOW_SEA, LAND))), dtype=np.uint8)
        return np.asarray(np.where(self._masks[0][iz, ix], OCEAN,
                                   np.where(self._elevation[iz, ix] < 0, CLOSED_BELOW_SEA, LAND)), dtype=np.uint8)

    def sample(self, x_m, z_m):
        x, z = _coordinates(x_m, z_m)
        elevation = np.full(x.shape, np.nan, dtype=np.float64)
        status = np.full(x.shape, OUT_OF_BOUNDS, dtype=np.uint8)
        # Only query the in-domain elements; never materialize full mmap arrays.
        with np.errstate(over="ignore", invalid="ignore"):
            fx = (x - self.first_xz_m[0]) / self.spacing_m
            fz = (z - self.first_xz_m[1]) / self.spacing_m
        nz, nx = self.shape_zx
        inside = (fx >= 0) & (fx <= nx - 1) & (fz >= 0) & (fz <= nz - 1)
        xx, zz = fx[inside], fz[inside]
        ix, iz = np.floor(xx).astype(np.intp), np.floor(zz).astype(np.intp)
        jx, jz = np.minimum(ix + 1, nx - 1), np.minimum(iz + 1, nz - 1)
        dx, dz = xx - ix, zz - iz
        values = ((1 - dx) * (1 - dz) * self._elevation[iz, ix]
                  + dx * (1 - dz) * self._elevation[iz, jx]
                  + (1 - dx) * dz * self._elevation[jz, ix]
                  + dx * dz * self._elevation[jz, jx])
        states = self._status(np.rint(zz).astype(np.intp), np.rint(xx).astype(np.intp))
        unknown = ((self._status(iz, ix) == UNKNOWN) | (self._status(iz, jx) == UNKNOWN)
                   | (self._status(jz, ix) == UNKNOWN) | (self._status(jz, jx) == UNKNOWN))
        states[unknown] = UNKNOWN
        values[unknown] = np.nan
        elevation[inside], status[inside] = values, states
        return dict(elevation_m=elevation, status=status, identity=self.identity)

    def crop(self, x0_m, z0_m, x1_m, z1_m, *, max_cells=16_777_216):
        x0, z0 = _coordinates(x0_m, z0_m)
        x1, z1 = _coordinates(x1_m, z1_m)
        _require(all(a.ndim == 0 for a in (x0, z0, x1, z1)), "Crop bounds must be scalars")
        _require(x1 > x0 and z1 > z0, "Crop must have positive extent")
        _require(type(max_cells) is int and max_cells >= 0, "Invalid max_cells")
        try:
            ix0, ix1 = (math.ceil((float(v) - self.first_xz_m[0]) / self.spacing_m) for v in (x0, x1))
            iz0, iz1 = (math.ceil((float(v) - self.first_xz_m[1]) / self.spacing_m) for v in (z0, z1))
        except (OverflowError, ValueError) as exc:
            raise TerrainSourceError("Crop bounds overflow") from exc
        shape = (iz1 - iz0, ix1 - ix0)
        _require(shape[0] * shape[1] <= max_cells, "Crop exceeds max_cells")
        elevation = np.full(shape, np.nan, dtype=np.float32)
        status = np.full(shape, OUT_OF_BOUNDS, dtype=np.uint8)
        nz, nx = self.shape_zx
        ax, bx, az, bz = max(ix0, 0), min(ix1, nx), max(iz0, 0), min(iz1, nz)
        if bx > ax and bz > az:
            source = (slice(az, bz), slice(ax, bx))
            dest = (slice(az - iz0, bz - iz0), slice(ax - ix0, bx - ix0))
            states = self._status(*source)
            elevation[dest] = np.where(states == UNKNOWN, np.nan, self._elevation[source])
            status[dest] = states
        return dict(elevation_m=elevation, status=status,
                    first_sample_xz_m=(self.first_xz_m[0] + ix0 * self.spacing_m, self.first_xz_m[1] + iz0 * self.spacing_m),
                    spacing_m=self.spacing_m, shape_zx=shape,
                    complete=bool(np.all(status != OUT_OF_BOUNDS)), provenance=self.provenance())


def load_native_terrain(path, *, expected_identity=None, verify_files=True):
    try:
        path = Path(path)
        manifest = _json((path / "manifest.json").read_text(encoding="utf-8"))
        _require(manifest["schema"] == "new-world-terrain-v3", "Unsupported native schema")
        _require(type(manifest["world_seed"]) is int and manifest["spacing_m"] == 30 and manifest["sea_m"] == 0, "Invalid native coordinate contract")
        shape = _shape(manifest["shape_zx"])
        origin = manifest["origin_native_xz"]
        _require(isinstance(origin, list) and len(origin) == 2 and all(type(v) is int for v in origin), "Invalid origin_native_xz")
        files = manifest["files"]
        _require(isinstance(files, dict) and all(_hex(files.get(k)) for k in _NATIVE_FILES), "Invalid file hashes")
        identity = _identity(manifest, {"identity", "source_path"}, expected_identity)
        arrays = []
        for name in _NATIVE_FILES:
            filename = path / (name + ".npy")
            if verify_files:
                _require(_file_sha256(filename) == files[name], f"File hash mismatch: {name}")
            array = np.load(filename, mmap_mode="r", allow_pickle=False)
            _require(array.shape == shape and array.dtype == (np.dtype("float32") if name == "bed_m" else np.dtype("bool")), f"Invalid array: {name}")
            arrays.append(array)
        product = _GridProduct("native-terrain-v3", identity, path, 30, (origin[0] * 30, origin[1] * 30), arrays[0], arrays[1:])
        product.world_seed = manifest["world_seed"]
        product.manifest = manifest
        product.unverified_files = sorted(set(files) - set(_NATIVE_FILES))
        return product
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as exc:
        if isinstance(exc, TerrainSourceError):
            raise
        raise TerrainSourceError(f"Invalid native product: {exc}") from exc


def load_tectonic_product(path, *, expected_identity=None):
    try:
        path = Path(path)
        with np.load(path, allow_pickle=False) as archive:
            raw = archive["manifest_json"]
            _require(raw.shape == () and raw.dtype.kind == "U", "Invalid manifest_json")
            manifest = _json(raw.item())
            _require(manifest["schema"] in ("tectonic-frozen-product-v2", "tectonic-frozen-product-v1"), "Unsupported tectonic schema")
            identity = _identity(manifest, {"identity"}, expected_identity)
            config = manifest["config"]
            shape = _shape(config["shape"])
            spacing = float(config["cell_size_m"])
            origin = (float(config["origin_x_m"]), float(config["origin_z_m"]))
            _require(type(config["world_seed"]) is int and np.isfinite(spacing) and spacing > 0 and all(math.isfinite(v) for v in origin), "Invalid tectonic coordinate contract")
            _require(manifest["coordinates"]["grid"].startswith("cell centres"), "Invalid grid semantics")
            arrays = []
            for key, dtype in (("final/elevation_m", np.dtype("float64")), ("final/ocean_connected", np.dtype("bool"))):
                array = archive[key]
                _require(array.shape == shape and array.dtype == dtype, f"Invalid array: {key}")
                _require(hashlib.sha256(array.tobytes(order="C")).hexdigest() == manifest["arrays"][key]["sha256"], f"Array hash mismatch: {key}")
                array.flags.writeable = False
                arrays.append(array)
        product = _GridProduct("tectonic-macro-v2", identity, path, spacing, tuple(v + spacing / 2 for v in origin), arrays[0], arrays[1:])
        product.world_seed = config["world_seed"]
        product.manifest = manifest
        return product
    except (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError) as exc:
        if isinstance(exc, TerrainSourceError):
            raise
        raise TerrainSourceError(f"Invalid tectonic product: {exc}") from exc


def native_index_to_m(ix, iz):
    ix, iz = _coordinates(ix, iz)
    return ix * 30.0, iz * 30.0


def m_to_native_index(x_m, z_m):
    x, z = _coordinates(x_m, z_m)
    ix, iz = np.rint(x / 30), np.rint(z / 30)
    _require(np.all(np.abs(x - ix * 30) <= 1e-6) and np.all(np.abs(z - iz * 30) <= 1e-6), "Coordinates are off native grid")
    if x.ndim == 0:
        return int(ix), int(iz)
    _require(np.all(np.abs(ix) < 2**63) and np.all(np.abs(iz) < 2**63), "Native indices overflow int64")
    return ix.astype(np.int64), iz.astype(np.int64)


class TerrainCatalog:
    def __init__(self, products):
        self.products = tuple(sorted(products, key=lambda product: product.spacing_m))

    def provenance(self):
        return [product.provenance() for product in self.products]

    def sample(self, x_m, z_m):
        x, z = _coordinates(x_m, z_m)
        elevation = np.full(x.shape, np.nan, dtype=np.float64)
        status = np.full(x.shape, UNPREPARED, dtype=np.uint8)
        source = np.full(x.shape, None, dtype=object)
        for product in self.products:
            pending = status == UNPREPARED
            result = product.sample(x[pending], z[pending])
            covered = result["status"] != OUT_OF_BOUNDS
            positions = np.flatnonzero(pending)[covered]
            elevation.flat[positions] = result["elevation_m"][covered]
            status.flat[positions] = result["status"][covered]
            source.flat[positions] = product.identity
        return dict(elevation_m=elevation, status=status, source=source)


def load_catalog(config_path):
    try:
        config_path = Path(config_path)
        config = _json(config_path.read_text(encoding="utf-8"))
        _require(isinstance(config["sources"], list), "sources must be a list")
        products = []
        for entry in config["sources"]:
            _require(_hex(entry.get("identity")), "Source identity is required")
            _require(isinstance(entry["path"], str), "Source path must be a string")
            path = Path(entry["path"])
            if not path.is_absolute():
                path = config_path.parent / path
            loaders = {"native-terrain-v3": load_native_terrain, "tectonic-macro-v2": load_tectonic_product}
            _require(entry["kind"] in loaders, "Unknown source kind")
            product = loaders[entry["kind"]](path, expected_identity=entry["identity"])
            if "expected_world_seed" in entry:
                _require(type(entry["expected_world_seed"]) is int and entry["expected_world_seed"] == product.world_seed, "Expected world_seed mismatch")
            products.append(product)
        return TerrainCatalog(products)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        if isinstance(exc, TerrainSourceError):
            raise
        raise TerrainSourceError(f"Invalid terrain catalog: {exc}") from exc


def load_default_catalog():
    path = os.environ.get("DREAM_TERRAIN_SOURCES")
    return load_catalog(path) if path else TerrainCatalog(())


__all__ = ["WORLD_SEED", "NATIVE_SPACING_M", "UNPREPARED", "OUT_OF_BOUNDS", "UNKNOWN", "OCEAN", "CLOSED_BELOW_SEA", "LAND", "STATUS_NAMES", "TerrainSourceError", "load_native_terrain", "load_tectonic_product", "native_index_to_m", "m_to_native_index", "TerrainCatalog", "load_catalog", "load_default_catalog"]
