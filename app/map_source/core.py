"""Shared query semantics; frozen source buffers never escape as writable views."""
import copy
from dataclasses import asdict

import numpy as np

from app import terrain_source as ts
from .types import DEFAULT_LAYERS, MissingLayerError


class ArrayGrid(ts._GridProduct):
    def _status(self, iz, ix):
        return np.array(self._masks[0][iz, ix], dtype=np.uint8, copy=True)


class GridSource:
    def __init__(self, grid, info, extras=None, vectors=None):
        self._grid = grid
        self.info = info
        self._extras = extras or {}
        self._vectors = vectors or {}
        for array in self._extras.values():
            array.flags.writeable = False

    @property
    def identity(self):
        return self.info.identity

    @property
    def spacing_m(self):
        return self.info.spacing_m

    @property
    def extent_m(self):
        return self.info.extent_m

    def provenance(self):
        return asdict(self.info)

    def _layers(self, layers):
        layers = (layers,) if isinstance(layers, str) else tuple(layers)
        for name in layers:
            if name not in self.info.layers:
                raise MissingLayerError(f"{self.info.kind}/{self.info.schema} has no layer {name!r}")
        return layers

    def sample(self, x_m, z_m, layers=DEFAULT_LAYERS):
        layers = self._layers(layers)
        x, z = ts._coordinates(x_m, z_m)
        status = np.full(x.shape, ts.OUT_OF_BOUNDS, dtype=np.uint8)
        elevation = np.full(x.shape, np.nan)
        with np.errstate(over="ignore", invalid="ignore"):
            fx = (x - self.info.first_sample_xz_m[0]) / self.spacing_m
            fz = (z - self.info.first_sample_xz_m[1]) / self.spacing_m
        nz, nx = self.info.shape_zx
        covered = (fx >= 0) & (fx <= nx - 1) & (fz >= 0) & (fz <= nz - 1)
        xx, zz = fx[covered], fz[covered]
        ix, iz = np.floor(xx).astype(np.intp), np.floor(zz).astype(np.intp)
        jx, jz = np.minimum(ix + 1, nx - 1), np.minimum(iz + 1, nz - 1)
        dx, dz = xx - ix, zz - iz
        states = self._grid._status(np.rint(zz).astype(np.intp), np.rint(xx).astype(np.intp))
        values = np.zeros(xx.shape)
        invalid = states == ts.UNKNOWN
        for zi, xi, weight in ((iz, ix, (1-dx)*(1-dz)), (iz, jx, dx*(1-dz)),
                               (jz, ix, (1-dx)*dz), (jz, jx, dx*dz)):
            used = weight > 0
            corner = self._grid._elevation[zi[used], xi[used]]
            values[used] += weight[used] * corner
            invalid[used] |= self._grid._status(zi[used], xi[used]) == ts.UNKNOWN
        values[invalid] = np.nan
        status[covered], elevation[covered] = states, values
        base = {"status": status, "elevation_m": elevation}
        result = {name: base[name] for name in layers if name in DEFAULT_LAYERS}
        inside = (base["status"] != ts.OUT_OF_BOUNDS) & (base["status"] != ts.UNKNOWN)
        # Optional layers use nearest samples: in particular, never spread a lake
        # across dry cells or invent a water surface by interpolating nodata.
        ix = np.rint((x[inside] - self.info.first_sample_xz_m[0]) / self.spacing_m).astype(np.intp)
        iz = np.rint((z[inside] - self.info.first_sample_xz_m[1]) / self.spacing_m).astype(np.intp)
        for name in layers:
            if name in self._extras:
                values = np.full(x.shape, np.nan)
                values[inside] = self._extras[name][iz, ix]
                result[name] = values
        result["identity"] = self.identity
        result["source_info"] = self.info
        for value in result.values():
            if isinstance(value, np.ndarray):
                value.flags.writeable = False
        return result

    def crop(self, x0, z0, x1, z1, layers=DEFAULT_LAYERS, *, max_cells=16_777_216):
        layers = self._layers(layers)
        base = self._grid.crop(x0, z0, x1, z1, max_cells=max_cells)
        first = base["first_sample_xz_m"]
        nz, nx = base["shape_zx"]
        # Legacy crops are float32; the unified interface preserves source dtype.
        elevation = np.full((nz, nx), np.nan, dtype=self._grid._elevation.dtype)
        ix0 = int(round((first[0] - self.info.first_sample_xz_m[0]) / self.spacing_m))
        iz0 = int(round((first[1] - self.info.first_sample_xz_m[1]) / self.spacing_m))
        az, bz = max(0, iz0), min(self.info.shape_zx[0], iz0+nz)
        ax, bx = max(0, ix0), min(self.info.shape_zx[1], ix0+nx)
        if bz > az and bx > ax:
            source = (slice(az, bz), slice(ax, bx))
            dest = (slice(az-iz0, bz-iz0), slice(ax-ix0, bx-ix0))
            elevation[dest] = self._grid._elevation[source]
        elevation[base["status"] == ts.UNKNOWN] = np.nan
        base["elevation_m"] = elevation
        result = {name: base[name] for name in layers if name in DEFAULT_LAYERS}
        extra = tuple(name for name in layers if name in self._extras)
        if extra:
            x, z = np.meshgrid(first[0] + np.arange(nx) * self.spacing_m,
                               first[1] + np.arange(nz) * self.spacing_m)
            sampled = self.sample(x, z, extra)
            result.update({name: sampled[name].copy() for name in extra})
        result.update({key: base[key] for key in ("first_sample_xz_m", "spacing_m", "shape_zx", "complete")})
        result["source_info"] = self.info
        result["provenance"] = self.provenance()
        return result

    def vectors(self, kind):
        if kind not in ("rivers", "lakes"):
            raise ts.TerrainSourceError(f"Unknown vector kind: {kind!r}")
        return copy.deepcopy(self._vectors.get(kind, []))
