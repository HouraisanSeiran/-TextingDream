# -*- coding: utf-8 -*-
"""Read-only habitat grid built from a world-map product.

The bed is never written. Settlement uses ``status`` (land only), elevation
bands, a coarse slope, distance to ocean, and river-vector proximity. Climate
layers are used only when the source already carries them.
"""
import math
from dataclasses import dataclass

import numpy as np
from scipy import ndimage

from app.terrain_source import CLOSED_BELOW_SEA, LAND, OCEAN

from .errors import CivSimError
from .schema import HABITAT_SCHEMA, MAX_CELLS

#: Upper edges of bands 0, 1 and 2. Band 3 is everything higher. Metres.
BAND_EDGES_M = (200, 800, 2000)


def full_crop_bounds(first_xz_m, spacing_m, shape_zx):
    """Half-open metre window that includes every cell centre.

    ``terrain_source`` crop uses ``ceil((bound - first) / spacing)`` as the
    exclusive index. Passing the centre of the last cell would drop that row.
    """
    nz, nx = shape_zx
    spacing = float(spacing_m)
    x0 = float(first_xz_m[0]) - spacing * 0.5 + spacing * 1e-6
    z0 = float(first_xz_m[1]) - spacing * 0.5 + spacing * 1e-6
    x1 = float(first_xz_m[0]) + (int(nx) - 0.5) * spacing
    z1 = float(first_xz_m[1]) + (int(nz) - 0.5) * spacing
    return x0, z0, x1, z1


def _band(mean_elevation_m):
    if mean_elevation_m < BAND_EDGES_M[0]:
        return 0
    if mean_elevation_m < BAND_EDGES_M[1]:
        return 1
    if mean_elevation_m < BAND_EDGES_M[2]:
        return 2
    return 3


@dataclass(frozen=True)
class Region:
    """One land block used as a province stand-in."""

    id: int
    block_z: int
    block_x: int
    land_cells: int
    mean_elevation_m: int
    band: int
    slope_millis: int
    river_millis: int
    coast_m: int
    coast_millis: int
    climate_millis: int | None

    def to_dict(self):
        return {
            "id": self.id,
            "block_zx": [self.block_z, self.block_x],
            "land_cells": self.land_cells,
            "mean_elevation_m": self.mean_elevation_m,
            "band": self.band,
            "slope_millis": self.slope_millis,
            "river_millis": self.river_millis,
            "coast_m": self.coast_m,
            "coast_millis": self.coast_millis,
            "climate_millis": self.climate_millis,
        }


@dataclass(frozen=True)
class Habitat:
    """In-memory habitat. Arrays are copies and are not written back."""

    schema: str
    map_identity: str
    map_kind: str
    map_schema: str
    world_seed: int | None
    spacing_m: float
    first_sample_xz_m: tuple
    shape_zx: tuple
    block_cells: int
    min_land_cells: int
    river_radius_m: int
    coast_scale_m: int
    climate: str
    habitable_cells: int
    ocean_cells: int
    closed_below_sea_cells: int
    regions: tuple
    neighbors: tuple
    status: np.ndarray
    cell_region: np.ndarray

    def summary(self):
        return {
            "schema": self.schema,
            "map_identity": self.map_identity,
            "map_kind": self.map_kind,
            "map_schema": self.map_schema,
            "world_seed": self.world_seed,
            "shape_zx": [int(self.shape_zx[0]), int(self.shape_zx[1])],
            "spacing_m": float(self.spacing_m),
            "first_sample_xz_m": [float(self.first_sample_xz_m[0]), float(self.first_sample_xz_m[1])],
            "block_cells": self.block_cells,
            "min_land_cells": self.min_land_cells,
            "river_radius_m": self.river_radius_m,
            "coast_scale_m": self.coast_scale_m,
            "band_edges_m": list(BAND_EDGES_M),
            "climate": self.climate,
            "habitable_cells": self.habitable_cells,
            "ocean_cells": self.ocean_cells,
            "closed_below_sea_cells": self.closed_below_sea_cells,
            "region_count": len(self.regions),
            "regions": [region.to_dict() for region in self.regions],
            "neighbors": [list(row) for row in self.neighbors],
        }


def habitat_from_source(source, *, block_cells, min_land_cells, river_radius_m, coast_scale_m):
    """Build a habitat by reading one map source. Does not write the product."""
    info = source.info
    shape = tuple(int(v) for v in info.shape_zx)
    if shape[0] * shape[1] > MAX_CELLS:
        raise CivSimError("栅格 %d×%d 超过文明模拟第一版上限 %d 格" % (shape[0], shape[1], MAX_CELLS))
    layers = ["elevation_m", "status"]
    climate_names = []
    if "temperature_c" in info.layers:
        layers.append("temperature_c")
        climate_names.append("temperature")
    if "precipitation_mm_yr" in info.layers:
        layers.append("precipitation_mm_yr")
        climate_names.append("precipitation")
    x0, z0, x1, z1 = full_crop_bounds(info.first_sample_xz_m, info.spacing_m, shape)
    cropped = source.crop(x0, z0, x1, z1, layers=tuple(layers), max_cells=MAX_CELLS)
    if tuple(int(v) for v in cropped["shape_zx"]) != shape:
        raise CivSimError("整幅裁切的形状与产品栅格不一致")
    rivers = source.vectors("rivers") if "rivers" in getattr(info, "vectors", ()) else []
    world_seed = info.world_seed
    if type(world_seed) is not int:
        world_seed = None
    return habitat_from_arrays(
        identity=info.identity,
        map_kind=info.kind,
        map_schema=info.schema,
        world_seed=world_seed,
        elevation_m=cropped["elevation_m"],
        status=cropped["status"],
        spacing_m=info.spacing_m,
        first_sample_xz_m=info.first_sample_xz_m,
        rivers=rivers,
        temperature_c=cropped.get("temperature_c"),
        precipitation_mm_yr=cropped.get("precipitation_mm_yr"),
        block_cells=block_cells,
        min_land_cells=min_land_cells,
        river_radius_m=river_radius_m,
        coast_scale_m=coast_scale_m,
        climate_names=tuple(climate_names),
    )


def habitat_from_arrays(
    *,
    identity,
    elevation_m,
    status,
    spacing_m,
    first_sample_xz_m,
    rivers=(),
    temperature_c=None,
    precipitation_mm_yr=None,
    block_cells,
    min_land_cells,
    river_radius_m,
    coast_scale_m,
    map_kind="arrays",
    map_schema="arrays",
    world_seed=None,
    climate_names=None,
):
    """Pure builder. Copies every array it keeps."""
    if not isinstance(identity, str) or not identity:
        raise CivSimError("地图 identity 必须是非空字符串")
    if type(block_cells) is not int or block_cells < 1:
        raise CivSimError("block_cells 必须是正整数")
    if type(min_land_cells) is not int or min_land_cells < 1:
        raise CivSimError("min_land_cells 必须是正整数")
    if type(river_radius_m) is not int or river_radius_m < 0:
        raise CivSimError("river_radius_m 必须是非负整数")
    if type(coast_scale_m) is not int or coast_scale_m < 1:
        raise CivSimError("coast_scale_m 必须是正整数")
    elevation = np.array(elevation_m, dtype=np.float64, copy=True)
    status_a = np.array(status, dtype=np.uint8, copy=True)
    if elevation.ndim != 2 or status_a.shape != elevation.shape:
        raise CivSimError("高程与 status 必须是同形状的二维栅格")
    if int(elevation.shape[0]) * int(elevation.shape[1]) > MAX_CELLS:
        raise CivSimError("栅格超过文明模拟第一版上限")
    if int(status_a.max(initial=0)) > 5:
        raise CivSimError("status 含有无法识别的取值")
    spacing = float(spacing_m)
    if not math.isfinite(spacing) or spacing <= 0:
        raise CivSimError("spacing_m 必须是正数")
    first = (float(first_sample_xz_m[0]), float(first_sample_xz_m[1]))
    if not all(math.isfinite(v) for v in first):
        raise CivSimError("first_sample_xz_m 必须是有限坐标")
    if world_seed is not None and type(world_seed) is not int:
        raise CivSimError("world_seed 必须是整数或空")

    habitable = status_a == np.uint8(LAND)
    ocean = status_a == np.uint8(OCEAN)
    slope = _slope(elevation, habitable, spacing)
    near_river = _river_mask(elevation.shape, first, spacing, rivers, river_radius_m)
    coast_m = _coast_metres(ocean, spacing)
    temp = _optional_grid(temperature_c, elevation.shape, "temperature_c")
    precip = _optional_grid(precipitation_mm_yr, elevation.shape, "precipitation_mm_yr")
    if climate_names is None:
        if temp is not None and precip is not None:
            climate = "temperature+precipitation"
        elif temp is not None:
            climate = "temperature"
        else:
            climate = "absent"
    else:
        climate = "+".join(climate_names) if climate_names else "absent"

    regions, neighbors, cell_region = _regions(
        elevation, habitable, slope, near_river, coast_m, temp, precip,
        block_cells, min_land_cells, coast_scale_m,
    )
    elevation.flags.writeable = False
    status_a.flags.writeable = False
    cell_region.flags.writeable = False
    return Habitat(
        schema=HABITAT_SCHEMA,
        map_identity=identity,
        map_kind=str(map_kind),
        map_schema=str(map_schema),
        world_seed=world_seed,
        spacing_m=spacing,
        first_sample_xz_m=first,
        shape_zx=tuple(int(v) for v in elevation.shape),
        block_cells=block_cells,
        min_land_cells=min_land_cells,
        river_radius_m=river_radius_m,
        coast_scale_m=coast_scale_m,
        climate=climate,
        habitable_cells=int(habitable.sum()),
        ocean_cells=int(ocean.sum()),
        closed_below_sea_cells=int((status_a == np.uint8(CLOSED_BELOW_SEA)).sum()),
        regions=tuple(regions),
        neighbors=tuple(tuple(row) for row in neighbors),
        status=status_a,
        cell_region=cell_region,
    )


def _optional_grid(values, shape, label):
    if values is None:
        return None
    grid = np.array(values, dtype=np.float64, copy=True)
    if grid.shape != shape:
        raise CivSimError("%s 的形状与高程不一致" % label)
    grid.flags.writeable = False
    return grid


def _slope(elevation, habitable, spacing):
    slope = np.zeros(elevation.shape, dtype=np.float64)
    finite = np.isfinite(elevation) & habitable
    horizontal = finite[:, 1:] & finite[:, :-1]
    rise = np.abs(elevation[:, 1:] - elevation[:, :-1]) / spacing
    rise = np.where(horizontal, rise, 0.0)
    slope[:, 1:] = np.maximum(slope[:, 1:], rise)
    slope[:, :-1] = np.maximum(slope[:, :-1], rise)
    vertical = finite[1:, :] & finite[:-1, :]
    rise = np.abs(elevation[1:, :] - elevation[:-1, :]) / spacing
    rise = np.where(vertical, rise, 0.0)
    slope[1:, :] = np.maximum(slope[1:, :], rise)
    slope[:-1, :] = np.maximum(slope[:-1, :], rise)
    return slope


def _river_mask(shape, first, spacing, rivers, radius_m):
    near = np.zeros(shape, dtype=bool)
    radius_cells = int(math.ceil(radius_m / spacing)) if radius_m else 0
    limit = radius_cells * radius_cells
    nz, nx = shape
    for line in rivers or ():
        if not isinstance(line, dict) or "points_xz_m" not in line:
            raise CivSimError("河流折线缺少 points_xz_m")
        points = line["points_xz_m"]
        if len(points) < 2:
            continue
        for start, stop in zip(points, points[1:]):
            ax, az = float(start[0]), float(start[1])
            bx, bz = float(stop[0]), float(stop[1])
            length = math.hypot(bx - ax, bz - az)
            steps = max(1, int(math.ceil(length / (spacing * 0.5))))
            for step in range(steps + 1):
                t = step / steps
                ix = int(round((ax + (bx - ax) * t - first[0]) / spacing))
                iz = int(round((az + (bz - az) * t - first[1]) / spacing))
                z0 = max(0, iz - radius_cells)
                z1 = min(nz, iz + radius_cells + 1)
                x0 = max(0, ix - radius_cells)
                x1 = min(nx, ix + radius_cells + 1)
                for zz in range(z0, z1):
                    dz = zz - iz
                    for xx in range(x0, x1):
                        dx = xx - ix
                        if dz * dz + dx * dx <= limit:
                            near[zz, xx] = True
    return near


def _coast_metres(ocean, spacing):
    if not bool(ocean.any()):
        return np.full(ocean.shape, 1.0e12, dtype=np.float64)
    # Distance to the nearest False cell. Ocean cells are the background.
    cells = ndimage.distance_transform_edt(~ocean)
    return np.asarray(cells, dtype=np.float64) * float(spacing)


def _climate_millis(temp_values, precip_values):
    if temp_values is None:
        return None
    finite = np.isfinite(temp_values)
    if not bool(finite.any()):
        return None
    temps = temp_values[finite]
    comfort = 1000.0 - np.minimum(1000.0, np.abs(temps - 15.0) * 40.0)
    if precip_values is not None:
        wet = precip_values[finite]
        wet = np.where(np.isfinite(wet) & (wet >= 0), np.minimum(1000.0, wet), 0.0)
        comfort = (comfort + wet) / 2.0
    return int(round(float(comfort.mean())))


def _regions(elevation, habitable, slope, near_river, coast_m, temp, precip,
             block_cells, min_land_cells, coast_scale_m):
    nz, nx = elevation.shape
    n_bz = (nz + block_cells - 1) // block_cells
    n_bx = (nx + block_cells - 1) // block_cells
    block_id = -np.ones((n_bz, n_bx), dtype=np.int32)
    cell_region = np.full((nz, nx), -1, dtype=np.int32)
    regions = []
    for izb in range(n_bz):
        z0, z1 = izb * block_cells, min(nz, (izb + 1) * block_cells)
        for ixb in range(n_bx):
            x0, x1 = ixb * block_cells, min(nx, (ixb + 1) * block_cells)
            mask = habitable[z0:z1, x0:x1]
            count = int(mask.sum())
            if count < min_land_cells:
                continue
            elev = elevation[z0:z1, x0:x1][mask]
            elev = elev[np.isfinite(elev)]
            if elev.size == 0:
                continue
            mean_elev = int(round(float(elev.mean())))
            slope_millis = int(round(float(slope[z0:z1, x0:x1][mask].mean()) * 1000.0))
            river_millis = int(round(1000.0 * float(near_river[z0:z1, x0:x1][mask].mean())))
            coast_mean = int(round(float(coast_m[z0:z1, x0:x1][mask].mean())))
            coast_millis = max(0, 1000 - (max(0, coast_mean) * 1000) // coast_scale_m)
            climate = None
            if temp is not None:
                climate = _climate_millis(temp[z0:z1, x0:x1][mask], None if precip is None else precip[z0:z1, x0:x1][mask])
            rid = len(regions)
            block_id[izb, ixb] = rid
            view = cell_region[z0:z1, x0:x1]
            view[mask] = rid
            regions.append(Region(
                id=rid,
                block_z=izb,
                block_x=ixb,
                land_cells=count,
                mean_elevation_m=mean_elev,
                band=_band(mean_elev),
                slope_millis=max(0, slope_millis),
                river_millis=min(1000, max(0, river_millis)),
                coast_m=max(0, coast_mean) if coast_mean < 10**11 else coast_mean,
                coast_millis=min(1000, coast_millis),
                climate_millis=climate,
            ))
    neighbors = [[] for _ in regions]
    for izb in range(n_bz):
        for ixb in range(n_bx):
            rid = int(block_id[izb, ixb])
            if rid < 0:
                continue
            for dz, dx in ((1, 0), (0, 1)):
                zz, xx = izb + dz, ixb + dx
                if zz >= n_bz or xx >= n_bx:
                    continue
                other = int(block_id[zz, xx])
                if other < 0:
                    continue
                neighbors[rid].append(other)
                neighbors[other].append(rid)
    for row in neighbors:
        row.sort()
    return regions, neighbors, cell_region
