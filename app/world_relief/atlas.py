"""Simple-style atlas rendering of a frozen world-relief product (display only).

美术只决定怎么画：高程、海陆、湖面（填洼水面）、河网全部按冻结产品原样读取，不改数据。
海岸平滑、色阶过渡、雪色、林区、山形符号、装饰都是显示层；图例逐项标明来源。
随机纹理与符号变体的种子 = subseed(world_seed, "atlas/<用途>")，即 SHA-256(f"{world_seed}:atlas/<用途>")
前 8 字节，与产品 subseed_method 相同；同输入两次渲染逐字节一致。

坐标：产品数组 [z, x]，X 东、Z 南、米制格心。显示像素 (x 向右 = 东, y 向下 = 南)，
像素边界在整数处；格心 (iz, ix) 位于 ((ix - x0 + 0.5) * spacing / mpp, (iz - z0 + 0.5) * spacing / mpp)。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import html as _html
import json
import math
import re
from pathlib import Path

import numpy as np
from scipy import ndimage as nd

from app.map_render import ART_DIR, extract_symbols, hex_rgb, hillshade, load_manifest, load_styles, scale_bar
from app.map_source import CLOSED_BELOW_SEA as ST_CLOSED, OCEAN as ST_OCEAN, MapCatalog, load_source
from .source import spatial_noise, subseed

SCHEMA = "world-relief-atlas-1.0"
RIVER_SCHEMA = "coordinate-river-segments-v1"
SOURCE_KIND = "world-relief-pilot"
LAYERS = ("status", "elevation_m", "water_surface_m", "drainage_area_m2")
CONSUMED_LAYERS = LAYERS + ("vectors:rivers",)
CONIFERS = ("tree-fir", "tree-spruce", "tree-pine")
BROADLEAVES = ("tree-oak", "tree-beech", "tree-birch")
TERRAIN_IDS = ("terrain-mountain", "terrain-snowpeak", "terrain-hill")
DECO_IDS = ("deco-compass", "deco-scale", "deco-cartouche")
SHIP_ID = "deco-carrack"
SHIP_SPRITE = "map-art-medieval-deco.svg"


# ---------------------------------------------------------------- product (read through the unified map_source interface)

@dataclass
class Product:
    """Arrays rebuilt from `app.map_source` samples at cell centres; the source object stays the only reader of the files."""
    path: Path
    source: object
    elevation: np.ndarray
    ocean: np.ndarray
    closed: np.ndarray
    lake_surface: np.ndarray
    area_m2: np.ndarray
    rivers: list
    river_threshold_km2: float
    cache: dict = field(default_factory=dict, repr=False)

    @property
    def info(self):
        return self.source.info

    @property
    def identity(self):
        return self.info.identity

    @property
    def spacing(self):
        return float(self.info.spacing_m)

    @property
    def first(self):
        return tuple(float(v) for v in self.info.first_sample_xz_m)

    @property
    def shape(self):
        return tuple(int(v) for v in self.info.shape_zx)

    @property
    def world_seed(self):
        return int(self.info.world_seed)

    @property
    def manifest(self):
        """Provenance view assembled from SourceInfo (the unified interface does not expose the raw manifest)."""
        i = self.info
        return dict(kind=i.kind, schema=i.schema, identity=i.identity,
                    source_identity=(i.lineage[0] if i.lineage else None), world_seed=int(i.world_seed),
                    source_world_seed=int(i.world_seed), shape_zx=list(i.shape_zx),
                    first_sample_xz_m=list(i.first_sample_xz_m), spacing_m=float(i.spacing_m),
                    axes=getattr(i, "grid_semantics", None), limitations=list(i.limitations or ()))


def product_from_source(src, path=None, rows=32):
    """Rebuild the display arrays from GridSource.sample at every cell centre (row blocks), plus the river vectors."""
    info = src.info
    nz, nx = (int(v) for v in info.shape_zx)
    sp = float(info.spacing_m)
    fx, fz = (float(v) for v in info.first_sample_xz_m)
    xs = fx + np.arange(nx) * sp
    elevation = np.empty((nz, nx), np.float32)
    ocean = np.empty((nz, nx), bool)
    closed = np.empty((nz, nx), bool)
    lake = np.empty((nz, nx), np.float32)
    area = np.empty((nz, nx), np.float32)
    for r0 in range(0, nz, rows):
        r1 = min(nz, r0 + rows)
        X, Z = np.meshgrid(xs, fz + np.arange(r0, r1) * sp)
        r = src.sample(X, Z, LAYERS)
        e = r["elevation_m"]
        ws = r["water_surface_m"]
        elevation[r0:r1] = e
        ocean[r0:r1] = r["status"] == ST_OCEAN
        closed[r0:r1] = r["status"] == ST_CLOSED
        lake[r0:r1] = np.where(np.isnan(ws), e, ws)
        area[r0:r1] = np.nan_to_num(r["drainage_area_m2"], nan=0.0)
    rivers = []
    for v in src.vectors("rivers"):
        rivers.append(dict(id=v["id"], coordinates_xz_m=[list(q) for q in v["points_xz_m"]],
                           head_area_km2=float(v["head_drainage_area_m2"]) / 1e6,
                           outlet_area_km2=float(v["drainage_area_m2"]) / 1e6,
                           downstream_id=v.get("downstream_id"), upstream_ids=list(v.get("upstream_ids") or ())))
        if v.get("through_lake"):  # v5+: straight lake entry->exit chords; the display layer must not draw them
            rivers[-1]["through_lake"] = True
            rivers[-1]["lake_spans"] = [list(s) for s in v.get("lake_spans") or ()]
    rivers.sort(key=lambda l: l["id"])
    threshold = math.floor(min(l["head_area_km2"] for l in rivers) / 10.0 + 1e-9) * 10.0 if rivers else 0.0
    return Product(path=Path(path) if path is not None else Path("."), source=src, elevation=elevation, ocean=ocean,
                   closed=closed, lake_surface=lake, area_m2=area, rivers=rivers, river_threshold_km2=float(threshold))


def load_product(path, **kwargs):
    """Load a frozen world-relief product through app.map_source (identity / hash checks live in the adapter)."""
    return product_from_source(load_source(SOURCE_KIND, path, **kwargs), path)


def load_config_product(config_path):
    """Pick the world-relief-pilot source out of a MapCatalog config (kind / identity / path as the catalog defines)."""
    catalog = MapCatalog.from_config(config_path)
    for src in catalog.sources:
        if src.info.kind == SOURCE_KIND:
            return product_from_source(src, config_path)
    raise ValueError("catalog %s has no %s source" % (config_path, SOURCE_KIND))



def atlas_seed(world_seed, purpose):
    return subseed(world_seed, "atlas/" + purpose)


def coast_elevation_medians(p, distances_km=(1, 3, 10, 30, 60, 100)):
    """Land elevation by distance from the sea (band k <= d < 1.5k + 1 km): the coastal check asked for by review."""
    land = ~p.ocean
    d = nd.distance_transform_edt(land) * p.spacing / 1000.0
    h = p.elevation.astype(np.float64)
    out = {}
    for k in distances_km:
        band = land & (d >= k) & (d < 1.5 * k + 1)
        if band.any():
            out[str(k)] = dict(median_m=round(float(np.median(h[band])), 2),
                               negative_fraction=round(float((h[band] < 0).mean()), 6), cells=int(band.sum()))
    return dict(rule="land cells with k <= distance_to_ocean < 1.5k+1 km (EDT on cell centres)",
                land_cells=int(land.sum()), negative_land_cells=int((land & (h < 0)).sum()), bands=out)


# ---------------------------------------------------------------- parameters / view

@dataclass(frozen=True)
class AtlasParams:
    width_px: int = 2400
    margin_ref_px: float = 92.0
    # coast / colour
    coast_smooth_cells: float = 0.75
    plain_relief_m: float = 600.0
    plain_smooth_m: float = 9000.0
    snow_base_m: float = 3500.0
    snow_aspect_m: float = 600.0
    snow_transition_m: float = 800.0
    snow_max_alpha: float = 0.5
    coast_shade_km: float = 14.0
    coast_shade_cut: float = 0.55
    snow_noise_m: float = 120.0
    shade_azimuth_deg: float = 315.0
    shade_altitude_deg: float = 42.0
    shade_z_factor: float = 1.9
    land_shade_strength: float = 0.62
    symbol_shade_keep: float = 0.45
    forest_tint_alpha: float = 0.30
    # terrain classification (metres / slope m per m)
    relief_window_m: float = 15000.0
    base_window_m: float = 41000.0
    mountain_relief_m: float = 900.0
    mountain_rel_m: float = 500.0
    mountain_slope: float = 0.06
    mountain_min_cells: int = 40
    hill_relief_m: float = 480.0
    hill_rel_m: float = 230.0
    hill_slope: float = 0.03
    hill_min_cells: int = 30
    major_rel_m: float = 1800.0
    snowpeak_m: float = 3400.0
    # symbol sizes / spacing in output px (overview targets 24-40 px spacing)
    mountain_px: tuple = (34.0, 28.0, 22.0)
    mountain_spacing_px: tuple = (38.0, 32.0, 26.0)
    hill_px: float = 20.0
    hill_spacing_px: float = 36.0
    tree_px: float = 10.0
    tree_step_px: float = 7.0
    # rivers
    river_spacing_px: float = 55.0
    river_w0_px: float = 0.7
    river_wk_px: float = 0.45
    river_wmax_px: float = 3.6
    river_pad_px: float = 3.0
    river_chaikin: int = 3
    river_smooth_km: float = 5.0
    # lakes
    lake_min_depth_m: float = 3.0
    lake_min_cells: int = 6
    # approximate vegetation (no climate data)
    forest_min_m: float = 30.0
    treeline_m: float = 2300.0
    forest_max_slope: float = 0.30
    forest_coast_km: float = 180.0
    forest_threshold: float = 0.42
    conifer_m: float = 1100.0
    # decorations
    deco_clearance_px: float = 34.0
    # one peak symbol per mountain patch
    peak_px: float = 44.0
    peak_tol_m: float = 60.0
    mount_shade_boost: float = 0.08
    # P2 stripe/block fix: smooth the 960 m relief before shading, soft multi-direction light, floor in mountains
    shade_smooth_cells: float = 1.1
    shade_extra_azimuths: tuple = (270.0, 355.0)
    shade_floor_mount: float = 0.30
    river_merge_cells: float = 2.0     # 并行河线合并距离（以产品格距计；<1.2 px 时按 1.2 px）
    river_merge_frac: float = 0.7
    river_protect_amin: float = 10.0   # 汇水面积 >= 该倍数 x 屏幕门槛的河（干流）不被合并删除
    mount_tint_alpha: float = 0.34
    # forest mixed planting (px values are at the 2048-px-wide reference where s = 1; tree_px is the plain pixel width)
    tree_gap: float = 1.05
    tree_keep: float = 0.80
    tree_keep_edge: float = 0.38
    tree_edge_px: float = 14.0
    edge_px: float = 12.0
    overview_mpp: float = 400.0
    warm_north: float = 0.30
    willow_px: float = 18.0
    block_km: float = 26.0
    rock_step: float = 1.5
    rock_p_forest: float = 0.07
    rock_p_treeline: float = 0.22
    rock_p_alpine: float = 0.30
    rock_plain_factor: float = 0.25
    grass_step: float = 0.9
    grass_density: float = 0.55
    grass_scale: tuple = (1.3, 1.5)
    grass_shrub_factor: float = 0.5
    grass_mushroom_factor: float = 0.35
    edge_boost: float = 1.8
    reed_step: float = 0.6
    reed_ring_px: float = 6.0
    reed_density: float = 0.6


@dataclass(frozen=True)
class View:
    z0: int
    x0: int
    nz: int
    nx: int
    width: int
    spacing: float

    @property
    def mpp(self):
        return self.nx * self.spacing / self.width

    @property
    def height(self):
        return int(round(self.nz * self.spacing / self.mpp))

    @property
    def s(self):
        return self.width / 2048.0


def full_view(p, width):
    return View(0, 0, p.shape[0], p.shape[1], int(width), p.spacing)


def _odd(n):
    n = max(1, int(round(n)))
    return n if n % 2 else n + 1


def _drop_small(mask, min_cells):
    lab, n = nd.label(mask, structure=np.ones((3, 3)))
    if n == 0:
        return mask
    sizes = np.bincount(lab.ravel())
    keep = sizes >= min_cells
    keep[0] = False
    return keep[lab]


def _crest(r):
    """Ridge cells: local maximum across at least two of four directions on a smoothed relief surface."""
    pad = np.pad(r, 1, mode="edge")
    c = pad[1:-1, 1:-1]
    count = np.zeros(r.shape, np.int8)
    for dz, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        a = pad[1 + dz:pad.shape[0] - 1 + dz, 1 + dx:pad.shape[1] - 1 + dx]
        b = pad[1 - dz:pad.shape[0] - 1 - dz, 1 - dx:pad.shape[1] - 1 - dx]
        count += ((c >= a) & (c >= b) & (c - 0.5 * (a + b) > 1e-3)).astype(np.int8)
    return count >= 2


def analyse(p, params):
    """Cell-level display analysis (no data changes): relief classes, lakes, approximate forest."""
    key = ("analyse", params)
    if key in p.cache:
        return p.cache[key]
    sp = p.spacing
    cells = lambda m: m / sp  # noqa: E731
    land = ~p.ocean
    h = p.elevation.astype(np.float64)
    h0 = np.where(land, h, 0.0)
    hs = nd.gaussian_filter(h0, max(cells(1000.0), 0.3))
    gz, gx = np.gradient(hs, sp)
    slope = np.hypot(gx, gz)
    win = _odd(cells(params.relief_window_m))
    relief = nd.maximum_filter(hs, win) - nd.minimum_filter(hs, win)
    bw = _odd(cells(params.base_window_m))
    base = nd.gaussian_filter(nd.minimum_filter(hs, bw), bw / 4.0)
    rel = np.maximum(hs - base, 0.0)
    mountain = land & (relief >= params.mountain_relief_m) & (rel >= params.mountain_rel_m) & (slope >= params.mountain_slope)
    mountain = nd.binary_closing(nd.binary_opening(mountain), iterations=2) & land
    mountain = _drop_small(mountain, params.mountain_min_cells)
    hill = land & ~nd.binary_dilation(mountain, iterations=2) & (relief >= params.hill_relief_m) & \
        (rel >= params.hill_rel_m) & (slope >= params.hill_slope)
    hill = _drop_small(nd.binary_opening(hill), params.hill_min_cells)
    ridge = nd.gaussian_filter(rel, max(cells(3000.0), 0.5))
    crest = _crest(ridge) & mountain
    hpeak = nd.maximum_filter(h0, _odd(cells(3000.0)))
    lake_depth = np.where(land, p.lake_surface.astype(np.float64) - h, 0.0)
    lake = _drop_small(land & (lake_depth > params.lake_min_depth_m), params.lake_min_cells)
    # plains: colour from a smoothed surface where local relief is low (no band speckle on flats)
    w = nd.gaussian_filter(np.clip(relief / params.plain_relief_m, 0.0, 1.0), 2.0)
    ecol = w * h0 + (1.0 - w) * nd.gaussian_filter(h0, cells(params.plain_smooth_m))
    # approximate vegetation: elevation, slope, distance to sea, north-south position (NOT climate data)
    nz, nx = p.shape
    dist_sea_km = nd.distance_transform_edt(land) * sp / 1000.0
    north = (1.0 - (np.arange(nz) + 0.5) / nz)[:, None] * np.ones((1, nx))
    seeds = {"forest-patch-60km": atlas_seed(p.world_seed, "forest-patch-60km"),
             "forest-patch-18km": atlas_seed(p.world_seed, "forest-patch-18km")}
    n1 = spatial_noise(p.shape, p.first, sp, seeds["forest-patch-60km"], 60000.0)
    n2 = spatial_noise(p.shape, p.first, sp, seeds["forest-patch-18km"], 18000.0)
    score = 0.6 * np.exp(-dist_sea_km / params.forest_coast_km) + 0.28 * n1 + 0.14 * n2 + 0.12
    treeline = params.treeline_m - 400.0 * north
    forest = land & ~lake & (h0 > params.forest_min_m) & (h0 < treeline) & (slope < params.forest_max_slope) & \
        (score > params.forest_threshold)
    forest = _drop_small(nd.binary_opening(forest), 20)
    conifer = forest & ((h0 > params.conifer_m + 300.0 * n2) | (north + 0.25 * n1 > 0.72))
    # one record per 8-connected mountain patch (label, bounding slice, highest cell)
    patch_label, npatch = nd.label(mountain, structure=np.ones((3, 3)))
    patches = []
    for k, sl in enumerate(nd.find_objects(patch_label), start=1):
        if sl is None:
            continue
        sub = patch_label[sl] == k
        hh = np.where(sub, h0[sl], -np.inf)
        j = int(np.argmax(hh))
        jz, jx = np.unravel_index(j, hh.shape)
        patches.append(dict(label=k, slice=sl, peak_zx=(int(jz + sl[0].start), int(jx + sl[1].start)),
                            peak_h=float(hh[jz, jx]), cells=int(sub.sum())))
    # mixed-planting features: north index per row, species blocks (quantile bins of coordinate noise)
    seeds["tree-block"] = atlas_seed(p.world_seed, "tree-block")
    nb = spatial_noise(p.shape, p.first, sp, seeds["tree-block"], params.block_km * 1000.0)
    qs = np.quantile(nb, np.linspace(0, 1, 7)[1:-1])
    block_bin = np.searchsorted(qs, nb).astype(np.int8)
    out = dict(land=land, h0=h0, slope=slope, relief=relief, rel=rel, ridge=ridge, mountain=mountain, hill=hill,
               crest=crest, hpeak=hpeak, lake=lake, lake_depth=lake_depth, ecol=ecol, forest=forest,
               conifer=conifer, seeds=seeds, patch_label=patch_label, patches=patches, north_z=north[:, 0].copy(),
               dist_sea_km=dist_sea_km, block_bin=block_bin)
    p.cache[key] = out
    return out


# ---------------------------------------------------------------- display fields and painting

def display_fields(p, a, view, params):
    sp, mpp = p.spacing, view.mpp
    H, W = view.height, view.width
    zs = view.z0 + (np.arange(H) + 0.5) * mpp / sp - 0.5
    xs = view.x0 + (np.arange(W) + 0.5) * mpp / sp - 0.5
    coords = np.array(np.meshgrid(zs, xs, indexing="ij"))

    def S(arr, order=1):
        return nd.map_coordinates(np.asarray(arr, np.float64), coords, order=order, mode="nearest", prefilter=order > 1)

    land = a["land"]
    ocean_depth = np.where(p.ocean, -p.elevation.astype(np.float64), 0.0)
    return dict(
        shade_h=S(nd.gaussian_filter(a["h0"], params.shade_smooth_cells), 3),
        ecol=S(a["ecol"]),
        coast=S(nd.gaussian_filter(land * 2.0 - 1.0, params.coast_smooth_cells)),
        lake=S(nd.gaussian_filter(a["lake"] * 2.0 - 1.0, 0.6)),
        depth=S(nd.gaussian_filter(ocean_depth, 1.0)),
        forest=S(nd.gaussian_filter(a["forest"].astype(np.float64), 1.0)),
        conifer=S(nd.gaussian_filter(a["conifer"].astype(np.float64), 1.2)),
        mount=S(nd.gaussian_filter(a["mountain"].astype(np.float64), 1.0)),
    )


def _coverage(g):
    """Anti-aliased coverage of {g > 0} and signed pixel distance (positive inside)."""
    gy, gx = np.gradient(g)
    sd = g / np.maximum(np.hypot(gx, gy), 1e-6)
    return np.clip(0.5 + sd, 0.0, 1.0), sd


def _smooth_noise(shape, cell, rng):
    h, w = shape
    cell = max(2.0, float(cell))
    small = rng.standard_normal((int(math.ceil(h / cell)) + 4, int(math.ceil(w / cell)) + 4))
    big = nd.zoom(small, cell, order=3, mode="nearest")[:h, :w]
    big = big - big.mean()
    sd = big.std()
    return big / sd if sd > 0 else big


def _blend(rgb, color, alpha):
    a = np.clip(alpha, 0.0, 1.0)[..., None]
    rgb *= 1.0 - a
    rgb += a * color


def _land_palette(style):
    bands = [b for b in style["land_bands"] if b["max_m"] is not None and b["max_m"] <= 3000]
    lows = [0.0] + [float(b["max_m"]) for b in bands[:-1]]
    centers = np.array([(lo + float(b["max_m"])) / 2 for lo, b in zip(lows, bands)])
    colors = np.stack([hex_rgb(b["color"]) for b in bands])
    return centers, colors


def paint_map(p, df, view, params, style, *, shade_reduce=None, forest=True):
    """Display raster (float RGB 0..255) for the map area. Never alters the data it reads."""
    H, W = view.height, view.width
    s, mpp = view.s, view.mpp
    seed_snow = atlas_seed(p.world_seed, "snow-noise")
    centers, colors = _land_palette(style)
    land_rgb = np.stack([np.interp(df["ecol"], centers, colors[:, c]) for c in range(3)], axis=-1)
    if forest:
        tint = np.clip((df["forest"] - 0.25) / 0.5, 0.0, 1.0) * params.forest_tint_alpha
        _blend(land_rgb, hex_rgb("#8f9f62"), tint)
    mount = np.clip(df["mount"], 0.0, 1.0)
    _blend(land_rgb, hex_rgb("#a38c6a"), mount * params.mount_tint_alpha)  # mountain range extent shown by colour
    # snow: elevation + aspect gradient (sun from the south assumed; display only, not snow data)
    hz = df["shade_h"]
    gz, gx = np.gradient(hz, mpp)
    steep = np.hypot(gx, gz)
    sunny = np.clip(-gz * 3.0 / np.sqrt(1.0 + 9.0 * steep * steep), -1.0, 1.0)
    rng = np.random.default_rng(seed_snow)
    noise = _smooth_noise((H, W), 22 * s, rng) * params.snow_noise_m
    line = params.snow_base_m + params.snow_aspect_m * sunny + noise
    t = np.clip((hz - line) / params.snow_transition_m + 0.5, 0.0, 1.0)
    snow = t * t * (3 - 2 * t)
    # shaded (lee) slopes keep more snow: lift coverage where the hillshade is dark
    pre_shade, pre_lz = hillshade(hz, mpp, params.shade_azimuth_deg, params.shade_altitude_deg, params.shade_z_factor)
    lee = np.clip(1.0 - pre_shade / pre_lz, 0.0, 1.0)
    snow = np.clip(snow * (0.45 + 0.9 * lee), 0.0, 1.0)
    _blend(land_rgb, hex_rgb("#f3efe6"), snow * params.snow_max_alpha)
    # hillshade (multiply), weakened under placed mountain symbols
    cfg = style["hillshade"]
    shade, lz = hillshade(hz, mpp, params.shade_azimuth_deg, params.shade_altitude_deg, params.shade_z_factor)
    lum = 2.0 * shade / lz
    for az in params.shade_extra_azimuths:
        sh2, _ = hillshade(hz, mpp, az, params.shade_altitude_deg, params.shade_z_factor)
        lum = lum + sh2 / lz
    lum = lum / (2.0 + len(params.shade_extra_azimuths))
    strength = params.land_shade_strength * (1.0 + params.mount_shade_boost * mount)
    if shade_reduce is not None:
        strength *= 1.0 - (1.0 - params.symbol_shade_keep) * shade_reduce
    # coastal belt: product has fine parallel gullies (D8 comb) next to the shore; soften shading contrast there
    shore_px = nd.distance_transform_edt(df["coast"] >= 0)
    strength *= 1.0 - params.coast_shade_cut * np.exp(-shore_px * mpp / (params.coast_shade_km * 1000.0))
    floor = 0.28 + params.shade_floor_mount * mount
    factor = np.clip(1.0 + strength * (lum - 1.0), floor, 1.0 + cfg.get("highlight", 0.1))
    land_rgb *= factor[..., None]
    # sea by depth band, softened
    oc = style["ocean_bands"]
    th = np.array([b["max_depth_m"] for b in oc[:-1]], np.float64)
    ocolors = np.stack([hex_rgb(b["color"]) for b in oc])
    ocean_rgb = ocolors[np.searchsorted(th, df["depth"], side="left")]
    ocean_rgb = np.stack([nd.gaussian_filter(ocean_rgb[..., c], 1.3 * s) for c in range(3)], axis=-1)
    alpha, sd = _coverage(df["coast"])
    rgb = land_rgb * alpha[..., None] + ocean_rgb * (1.0 - alpha[..., None])
    del land_rgb, ocean_rgb
    # lakes (filled-depression water surface) with a thin ink rim
    la, lsd = _coverage(df["lake"])
    la *= alpha
    if la.any():
        _blend(rgb, hex_rgb(oc[1]["color"]), la)
        _blend(rgb, hex_rgb(style["coast"]["ink"]), np.clip(0.9 * s + 0.5 - lsd, 0, 1) * np.clip(lsd + 0.5, 0, 1) * alpha * 0.8)
    # coast: ink line + second line + fading ripples, all on the sea side
    co = style["coast"]
    ink = hex_rgb(co["ink"])
    sea = df["coast"] < 0
    edt = nd.gaussian_filter(nd.distance_transform_edt(sea), 1.2)
    d = np.where(sd > -3.0, -sd, edt)
    lw = co["line_px"] * s
    _blend(rgb, ink, np.clip(lw + 0.5 - d, 0, 1) * np.clip(d + 0.5, 0, 1))
    d2 = np.abs(d - co["second_line_at_px"] * s)
    _blend(rgb, ink, np.clip(co["second_line_px"] * s / 2 + 0.5 - d2, 0, 1) * co["second_alpha"] * (d > 0))
    step = co["ripple_step_px"] * s
    k = np.round((d - co["ripple_start_px"] * s) / step)
    valid = (k >= 0) & (k < co["ripple_count"]) & (d > lw + 1)
    rd = np.abs(d - (co["ripple_start_px"] * s + k * step))
    fade = 1.0 - np.clip(k, 0, None) / co["ripple_count"]
    _blend(rgb, hex_rgb(co["ripple_color"]), np.clip(co["ripple_px"] * s / 2 + 0.5 - rd, 0, 1) * fade * co["ripple_alpha"] * valid)
    return rgb


def paper_texture(shape, s, seed, cfg):
    h, w = shape
    rng = np.random.default_rng(seed)
    f = np.ones((h, w))
    n = nd.gaussian_filter(rng.standard_normal((h, w)), 0.7)
    n = (n - n.mean()) / max(n.std(), 1e-9)
    f += cfg["grain"] * np.clip(n, -3, 3) * 0.5
    cell = cfg["blotch_cell_px"] * s
    f += cfg["blotch"] * 0.5 * (_smooth_noise((h, w), cell, rng) * 0.7 + _smooth_noise((h, w), cell / 3, rng) * 0.3)
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot((xx - w / 2) / (w / 2), (yy - h / 2) / (h / 2))
    f *= 1.0 - cfg["vignette"] * np.clip((r - 0.7) / 0.75, 0, 1) ** 2
    return f


# ---------------------------------------------------------------- rivers

def pinned_smooth(points, sigma):
    """Gaussian smoothing along a polyline whose weight tapers to 0 at both ends (endpoints never move)."""
    pts = np.asarray(points, np.float64)
    n = len(pts)
    if sigma <= 0 or n < 4:
        return pts
    from scipy.ndimage import gaussian_filter1d
    sm = gaussian_filter1d(pts, sigma, axis=0, mode="nearest")
    i = np.arange(n, dtype=np.float64)
    w = np.clip(np.minimum(i, n - 1 - i) / (2.0 * sigma), 0.0, 1.0)[:, None]
    out = pts * (1.0 - w) + sm * w
    out[0], out[-1] = pts[0], pts[-1]
    return out


def chaikin(points, iterations=2):
    """Corner-cutting smoothing; first and last points stay exactly where they are."""
    pts = np.asarray(points, np.float64)
    for _ in range(iterations):
        if len(pts) < 3:
            break
        q = 0.75 * pts[:-1] + 0.25 * pts[1:]
        r = 0.25 * pts[:-1] + 0.75 * pts[1:]
        mid = np.empty((2 * len(q), pts.shape[1]))
        mid[0::2], mid[1::2] = q, r
        pts = np.vstack([pts[:1], mid, pts[-1:]])
    return pts


def river_min_area_km2(p, view, params):
    return max(p.river_threshold_km2, (params.river_spacing_px * view.mpp / 1000.0) ** 2)


def river_polylines(p, a, view, params):
    """Product river segments in display px, truncated at the screen-scale area threshold, split at lakes, smoothed."""
    sp, mpp = p.spacing, view.mpp
    amin = river_min_area_km2(p, view, params)
    ex = p.first[0] - sp / 2 + view.x0 * sp
    ez = p.first[1] - sp / 2 + view.z0 * sp
    nz, nx = p.shape
    W, H = view.width, view.height
    out = []
    for line in p.rivers:
        c = np.asarray(line["coordinates_xz_m"], np.float64)
        ix = np.clip(np.rint((c[:, 0] - p.first[0]) / sp).astype(int), 0, nx - 1)
        iz = np.clip(np.rint((c[:, 1] - p.first[1]) / sp).astype(int), 0, nz - 1)
        area = p.area_m2[iz, ix].astype(np.float64) / 1e6
        keep = area >= amin
        if not keep.any():
            continue
        i0 = int(np.argmax(keep))
        chord = None  # edge k joins points k and k+1; True = through-lake chord (never drawn)
        if line.get("through_lake") and line.get("lake_spans"):
            chord = np.zeros(max(len(c) - 1, 0), bool)
            for a0, a1 in line["lake_spans"]:
                lo, hi = sorted((int(a0), int(a1)))
                chord[max(lo, 0):max(min(hi, len(chord)), 0)] = True
            chord = chord[i0:]
        c, area, iz, ix = c[i0:], area[i0:], iz[i0:], ix[i0:]
        px = (c[:, 0] - ex) / mpp
        py = (c[:, 1] - ez) / mpp
        if px.max() < -10 or py.max() < -10 or px.min() > W + 10 or py.min() > H + 10:
            continue
        dry = ~a["lake"][iz, ix]
        widths = np.clip(params.river_w0_px + params.river_wk_px * np.log2(area / amin), params.river_w0_px, params.river_wmax_px)
        runs, start = [], None
        for i, ok in enumerate(dry):
            if ok and start is None:
                start = i
            if (not ok or i == len(dry) - 1) and start is not None:
                end = i + 1 if ok else i
                if end - start >= 2:
                    runs.append((start, end))
                start = None
        if chord is not None and chord.any():
            cut = []
            for s0, s1 in runs:
                b = s0
                for k in range(s0, s1 - 1):
                    if chord[k]:
                        cut.append((b, k + 1))
                        b = k + 1
                cut.append((b, s1))
            runs = [(s0, s1) for s0, s1 in cut if s1 - s0 >= 2]
        for s0, s1 in runs:
            raw = np.column_stack([px[s0:s1], py[s0:s1], widths[s0:s1]])
            sm = pinned_smooth(raw, params.river_smooth_km * 1000.0 / sp)
            sm = chaikin(sm, params.river_chaikin)
            out.append(dict(id=line["id"], raw=raw[:, :2], points=sm[:, :2], widths=sm[:, 2],
                            area_km2=(float(area[s0]), float(area[s1 - 1]))))
    if params.river_merge_cells > 0:
        out = merge_parallel_rivers(out, max(params.river_merge_cells * sp / mpp, 1.2), params.river_merge_frac,
                                 protect_km2=params.river_protect_amin * amin)
    return out, amin


def merge_parallel_rivers(rivers, dist_px, frac, protect_km2=None):
    """Display-layer merge of near-parallel river lines (D8 on flat ground yields bundles of 1-cell-spaced lines).

    Lines are visited from the largest end-catchment down; a line is dropped when at least `frac` of its interior
    points lie within `dist_px` of lines already kept; lines with end catchment >= `protect_km2` (trunks) are never
    removed. Tributaries that merely join at an angle touch only a few
    points and survive. Deterministic: ties are broken by id."""
    if len(rivers) < 2:
        return rivers
    order = sorted(range(len(rivers)), key=lambda i: (-rivers[i]["area_km2"][1], str(rivers[i]["id"]), i))
    cell = float(dist_px)
    grid = {}
    kept = []
    d2 = cell * cell
    for i in order:
        pts = rivers[i]["raw"]
        n = len(pts)
        inner = pts[1:-1] if n > 4 else pts[:0]
        amax = float(rivers[i]["area_km2"][1])
        drop = False
        if len(inner) and not (protect_km2 is not None and amax >= protect_km2):
            near = 0
            for x, y in inner:
                gx, gy = int(np.floor(x / cell)), int(np.floor(y / cell))
                hit = False
                for ox in (-1, 0, 1):
                    for oy in (-1, 0, 1):
                        for qx, qy, qa in grid.get((gx + ox, gy + oy), ()):
                            if (qx - x) ** 2 + (qy - y) ** 2 <= d2:
                                hit = True
                                break
                        if hit:
                            break
                    if hit:
                        break
                near += hit
            drop = near >= frac * len(inner)
        if not drop:
            kept.append(i)
            for x, y in pts:
                grid.setdefault((int(np.floor(x / cell)), int(np.floor(y / cell))), []).append((float(x), float(y), amax))
    keep = set(kept)
    return [r for i, r in enumerate(rivers) if i in keep]


def river_mask(rivers, view, pad):
    from PIL import Image, ImageDraw
    img = Image.new("L", (view.width, view.height), 0)
    draw = ImageDraw.Draw(img)
    for r in rivers:
        pts, ws = r["points"], r["widths"]
        for i in range(len(pts) - 1):
            w = int(math.ceil(0.5 * (ws[i] + ws[i + 1]) + 2 * pad))
            draw.line([tuple(pts[i]), tuple(pts[i + 1])], fill=255, width=w)
            rr = w / 2.0
            draw.ellipse([pts[i + 1][0] - rr, pts[i + 1][1] - rr, pts[i + 1][0] + rr, pts[i + 1][1] + rr], fill=255)
    return np.asarray(img) > 0


# ---------------------------------------------------------------- symbol placement

def _integral(mask):
    ii = np.zeros((mask.shape[0] + 1, mask.shape[1] + 1), np.int64)
    ii[1:, 1:] = np.cumsum(np.cumsum(mask, axis=0, dtype=np.int64), axis=1)
    return ii


def _irect(box):
    x0, y0, x1, y1 = box
    return int(math.floor(x0)), int(math.floor(y0)), int(math.ceil(x1)), int(math.ceil(y1))


class _Board:
    """Forbidden raster (static, integral image) + occupancy raster (dynamic)."""

    def __init__(self, forbid):
        self.H, self.W = forbid.shape
        self.ii = _integral(forbid)
        self.occ = np.zeros(forbid.shape, bool)

    def free(self, box):
        x0, y0, x1, y1 = _irect(box)
        if x0 < 0 or y0 < 0 or x1 > self.W or y1 > self.H:
            return False
        ii = self.ii
        if ii[y1, x1] - ii[y0, x1] - ii[y1, x0] + ii[y0, x0]:
            return False
        return not self.occ[y0:y1, x0:x1].any()

    def take(self, box):
        x0, y0, x1, y1 = _irect(box)
        self.occ[max(0, y0):y1, max(0, x0):x1] = True


class _Spacing:
    def __init__(self, cell):
        self.cell = cell
        self.grid = {}

    def ok(self, x, y, d):
        gx, gy = int(x // self.cell), int(y // self.cell)
        for i in range(gx - 2, gx + 3):
            for j in range(gy - 2, gy + 3):
                for (u, v, e) in self.grid.get((i, j), ()):
                    if (u - x) ** 2 + (v - y) ** 2 < (0.5 * (d + e)) ** 2:
                        return False
        return True

    def add(self, x, y, d):
        self.grid.setdefault((int(x // self.cell), int(y // self.cell)), []).append((x, y, d))


def _window(view, arr):
    return arr[view.z0:view.z0 + view.nz, view.x0:view.x0 + view.nx]


def _cell_px(view, iz, ix):
    k = view.spacing / view.mpp
    return (ix + 0.5) * k, (iz + 0.5) * k


def forbidden_mask(df, rmask, view):
    """Where no symbol may sit: sea, lakes (both slightly dilated) and the buffered displayed river lines."""
    water = (df["coast"] < 0) | (df["lake"] > -0.2)
    water = nd.binary_dilation(water, iterations=max(1, int(round(2 * view.s))))
    return water | rmask


# ---------------------------------------------------------------- art catalogue (read from the sprite files at run time)

_SYMBOL_ID = re.compile(r'<symbol[^>]*\bid="([^"]+)"')
TREE_FILES = ("map-art-trees-a.svg", "map-art-trees-b.svg")
ROCK_SVG, ROCK_JSON = "map-art-ground-rocks.svg", "ground-rocks.json"
GRASS_SVG, GRASS_JSON = "map-art-ground-grass.svg", "ground-grass.json"
BASE_SVG = "map-art.svg"
FANTASY_TREES = ("silverleaf", "gloomwood", "mushroom", "crystal")
BROADLEAF_DOMINANT = ("oak", "birch", "beech", "oak", "maple", "birch")
_ART_CACHE = {}


def _variant_no(sid):
    m = re.search(r"-v(\d+)$", sid)
    return int(m.group(1)) if m else 1


def load_art(art_dir=ART_DIR):
    """Species -> variant ids parsed from the tree sprite files (regex on <symbol id>), rock / grass lists from their JSON."""
    key = str(Path(art_dir).resolve())
    if key in _ART_CACHE:
        return _ART_CACHE[key]
    d = Path(art_dir)
    files, trees = {}, {}
    for fname in TREE_FILES:
        for sid in _SYMBOL_ID.findall((d / fname).read_text(encoding="utf-8")):
            files[sid] = fname
            if sid.startswith("tree-"):
                trees.setdefault(re.sub(r"-v\d+$", "", sid)[5:], []).append(sid)
    for ids in trees.values():
        ids.sort(key=_variant_no)
    for fname in (ROCK_SVG, GRASS_SVG):
        for sid in _SYMBOL_ID.findall((d / fname).read_text(encoding="utf-8")):
            files[sid] = fname
    rocks = json.loads((d / ROCK_JSON).read_text(encoding="utf-8"))["rocks"]
    grass = json.loads((d / GRASS_JSON).read_text(encoding="utf-8"))
    art = dict(files=files, trees=dict(sorted(trees.items())), rocks=rocks, grass=grass["symbols"],
               grass_by_scene=grass.get("by_scene", {}))
    _ART_CACHE[key] = art
    return art


def _cdf_pick(weights, u):
    w = np.asarray(weights, np.float64)
    c = np.cumsum(w) / w.sum()
    return np.minimum(np.searchsorted(c, u, side="right"), len(w) - 1)


# ---------------------------------------------------------------- reserved / fantasy regions

def rasterise_regions(regions, p, view):
    """Metric regions (X east, Z south) -> list of screen-pixel bool masks. px = (x - edge_x) / mpp."""
    from PIL import Image, ImageDraw
    sp, mpp = p.spacing, view.mpp
    ex = p.first[0] - sp / 2 + view.x0 * sp
    ez = p.first[1] - sp / 2 + view.z0 * sp
    out = []
    for r in regions or ():
        img = Image.new("L", (view.width, view.height), 0)
        dr = ImageDraw.Draw(img)
        t = r.get("type") or r.get("shape")
        if t == "circle":
            cx, cy, rr = (r["x"] - ex) / mpp, (r["z"] - ez) / mpp, r["r"] / mpp
            dr.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=255)
        elif t == "polyline":
            pts = [((x - ex) / mpp, (z - ez) / mpp) for x, z in r["points"]]
            w = max(1, int(round(r["width"] / mpp)))
            dr.line(pts, fill=255, width=w, joint="curve")
            for q in pts:
                dr.ellipse([q[0] - w / 2.0, q[1] - w / 2.0, q[0] + w / 2.0, q[1] + w / 2.0], fill=255)
        elif t == "polygon":
            dr.polygon([((x - ex) / mpp, (z - ez) / mpp) for x, z in r["points"]], fill=255)
        else:
            raise ValueError("unknown region type %r" % (t,))
        out.append(np.asarray(img) > 0)
    return out


# ---------------------------------------------------------------- mountains: one peak symbol per connected range

def place_mountains(p, a, df, view, params, board):
    """Exactly one mountain / snowpeak symbol per 8-connected mountain patch, at (nearly) its highest free cell."""
    lab, h0 = a["patch_label"], a["h0"]
    w = params.peak_px * view.s
    h = w * 18.0 / 24.0
    symbols = []
    for patch in a["patches"]:
        pz, pxx = patch["peak_zx"]
        if not (view.z0 <= pz < view.z0 + view.nz and view.x0 <= pxx < view.x0 + view.nx):
            continue
        sl = patch["slice"]
        sub = lab[sl] == patch["label"]
        hh = np.where(sub, h0[sl], -np.inf)
        flat = hh.ravel()
        order = np.argsort(-flat, kind="stable")
        for k in order:
            if flat[k] < patch["peak_h"] - params.peak_tol_m:
                break
            iz, ix = np.unravel_index(k, hh.shape)
            iz, ix = int(iz + sl[0].start), int(ix + sl[1].start)
            if not (view.z0 <= iz < view.z0 + view.nz and view.x0 <= ix < view.x0 + view.nx):
                continue
            x, y = _cell_px(view, iz - view.z0, ix - view.x0)
            box = (x - w / 2, y - 0.62 * h, x + w / 2, y + 0.38 * h)
            if not board.free(box):
                continue
            board.take(box)
            snow = bool(h0[iz, ix] >= params.snowpeak_m)
            sid = "terrain-snowpeak" if snow else "terrain-mountain"
            symbols.append(dict(kind="snowpeak" if snow else "mountain", id=sid, tier="peak", x=x, y=y, w=w, h=h, box=box,
                                draw=box, mirror=False, cell_zx=(iz, ix), patch=int(patch["label"])))
            break
    return symbols


# ---------------------------------------------------------------- forest mixed planting (trees + rocks + grass)

def forest_context(df, forbid):
    cov = df["forest"] >= 0.5
    return dict(dedge=nd.distance_transform_edt(cov), dwater=nd.distance_transform_edt(~forbid))


class _Feat:
    def __init__(self, p, a, df, view, ctx):
        self.p, self.a, self.df, self.view, self.ctx = p, a, df, view, ctx

    def at(self, x, y):
        p, a, df, view = self.p, self.a, self.df, self.view
        sp, mpp = p.spacing, view.mpp
        xi = np.clip(x.astype(int), 0, view.width - 1)
        yi = np.clip(y.astype(int), 0, view.height - 1)
        nz, nx = p.shape
        iz = np.clip(np.floor(y * mpp / sp + view.z0).astype(int), 0, nz - 1)
        ix = np.clip(np.floor(x * mpp / sp + view.x0).astype(int), 0, nx - 1)
        return dict(cov=df["forest"][yi, xi], con=df["conifer"][yi, xi], h=df["shade_h"][yi, xi], mount=df["mount"][yi, xi],
                    dedge=self.ctx["dedge"][yi, xi], dwater=self.ctx["dwater"][yi, xi], xi=xi, yi=yi,
                    slope=a["slope"][iz, ix], north=a["north_z"][iz], dsea=a["dist_sea_km"][iz, ix],
                    bin=a["block_bin"][iz, ix])


def _tree_weights(names, f, params, s):
    col = {n: i for i, n in enumerate(names)}
    n = len(f["h"])
    W = np.zeros((n, len(names)))

    def add(name, w):
        if name in col:
            W[:, col[name]] += w

    con = (f["con"] >= 0.5).astype(np.float64)
    br = 1.0 - con
    h, north, dsea = f["h"], f["north"], f["dsea"]
    high = np.clip((h - 800.0) / 1500.0, 0.0, 1.0)
    nth = np.clip((north - 0.4) / 0.4, 0.0, 1.0)
    warm = ((north < params.warm_north) & (h < 700.0)).astype(np.float64)
    # coniferous stands: larch raised (autumn variant included), a few pale-stemmed birch / ash mixed in
    add("larch", con * (0.30 + 0.22 * high + 0.20 * nth))
    add("spruce", con * 0.22)
    add("fir", con * 0.15 * (1.0 - 0.3 * high))
    add("pine", con * (0.08 + 0.10 * (1.0 - high)))
    add("cedar", con * 0.03)
    add("cypress", con * 0.02 * (1.0 + 2.0 * warm))
    add("yew", con * 0.02)
    add("redwood", con * 0.012 * (dsea < 60.0))
    add("birch", con * 0.07)
    add("ash", con * 0.04)
    # broadleaf stands: one dominant species per block (noise bins), rest a loose mixture
    for k, dom in enumerate(BROADLEAF_DOMINANT):
        add(dom, br * 0.55 * (f["bin"] == k))
    for name, w in (("oak", 0.10), ("beech", 0.08), ("birch", 0.08), ("maple", 0.07), ("chestnut", 0.05),
                    ("ash", 0.06), ("elm", 0.05), ("cherry", 0.006)):
        add(name, br * w)
    # warm south, low ground
    for name, w in (("olive", 0.16), ("acacia", 0.08), ("teak", 0.05), ("bamboo", 0.05), ("kapok", 0.015), ("baobab", 0.008)):
        add(name, warm * w)
    add("palm", warm * 0.22 * (dsea < 45.0))
    # willow only beside rivers and lakes
    add("willow", 0.45 * (f["dwater"] <= params.willow_px * s))
    return W


def place_forest_symbols(p, a, df, view, params, board, ctx, *, fantasy=None, art=None):
    """Mixed planting inside the approximate forest: trees (varied species / variant / size / mirror), rocks in the
    gaps, grass (forest floor, forest edge, dry south) and shore reeds. Random numbers come from fixed-shape grids,
    so rejected candidates never shift later draws."""
    art = art or load_art()
    s, mpp = view.s, view.mpp
    H, W = view.height, view.width
    overview = mpp > params.overview_mpp
    wd = params.tree_px
    feat = _Feat(p, a, df, view, ctx)
    seeds = {k: atlas_seed(p.world_seed, k) for k in ("tree-placement", "tree-species", "rock-placement", "grass-placement", "reed-placement")}
    out = []
    # ---- fantasy regions
    freg = None
    if fantasy:
        masks = rasterise_regions(fantasy, p, view)
        freg = [(m, float(r.get("share", 1.0)), [n for n in (r.get("species") or FANTASY_TREES) if n in art["trees"]])
                for m, r in zip(masks, fantasy)]
    # ---- trees
    names = list(art["trees"])
    rng = np.random.default_rng(seeds["tree-placement"])
    cx = params.tree_gap * wd
    cy = params.tree_gap * wd
    nxg, nyg = int(W / cx) + 2, int(H / cy) + 2
    gj, gi = np.mgrid[0:nyg, 0:nxg]
    u = rng.random((10,) + gi.shape)
    x = ((gi + 0.5 + 0.5 * (gj % 2)) * cx + (u[0] - 0.5) * 0.4 * cx).ravel()
    y = ((gj + 0.5) * cy + (u[1] - 0.5) * 0.4 * cy).ravel()
    u = u.reshape(10, -1)
    inside = (x > 0) & (x < W) & (y > 0) & (y < H)
    f = feat.at(x, y)
    pk = params.tree_keep_edge + (params.tree_keep - params.tree_keep_edge) * np.clip(f["dedge"] / (params.tree_edge_px * s), 0.0, 1.0)
    cand = np.nonzero(inside & (f["cov"] >= 0.5) & (u[2] < pk))[0]
    cand = cand[np.argsort(u[7][cand], kind="stable")]
    fc = {k: v[cand] for k, v in f.items()}
    Wt = _tree_weights(names, fc, params, s)
    if freg:
        reg = np.full(len(cand), -1)
        for k, (m, share, sp_names) in enumerate(freg):
            reg[m[fc["yi"], fc["xi"]] & (u[8][cand] < share)] = k
        for k, (m, share, sp_names) in enumerate(freg):
            rows = np.nonzero(reg == k)[0]
            if len(rows) and sp_names:
                Wt[rows] = 0.0
                for nm in sp_names:
                    Wt[rows, names.index(nm)] = 1.0
    keep_fantasy = set()
    if freg:
        for _, _, nms in freg:
            keep_fantasy.update(nms)
    for nm in FANTASY_TREES:
        if nm in names and nm not in keep_fantasy:
            Wt[:, names.index(nm)] = 0.0
    dead = Wt.sum(axis=1) <= 0
    Wt[dead, names.index("oak") if "oak" in names else 0] = 1.0
    cum = np.cumsum(Wt, axis=1)
    cum /= cum[:, -1:]
    sp_idx = np.minimum((cum < u[3][cand][:, None]).sum(axis=1), len(names) - 1)
    for ci, i in enumerate(cand):
        name = names[sp_idx[ci]]
        ids = art["trees"][name]
        if name == "larch" and len(ids) >= 3:
            vw = [0.40, 0.35, 0.25]
        else:
            vw = [1.3] + [1.0] * (len(ids) - 1)
        sid = ids[int(_cdf_pick(vw, u[4][i]))]
        w = wd * (0.9 + 0.2 * u[5][i])
        hh = w * 1.25
        xx, yy = float(x[i]), float(y[i])
        box = (xx - 0.32 * w, yy - 0.75 * hh, xx + 0.32 * w, yy + 0.03 * hh)
        if not board.free(box):
            continue
        board.take(box)
        draw = (xx - 0.5 * w, yy - 38.0 / 40.0 * hh, xx + 0.5 * w, yy + 2.0 / 40.0 * hh)
        scene = "conifer" if fc["con"][ci] >= 0.5 else "broadleaf"
        out.append(dict(kind="tree", id=sid, species=name, scene=scene, x=xx, y=yy, w=w, h=hh, box=box, draw=draw,
                        mirror=bool(u[6][i] < 0.35)))
    tree_w = wd
    # ---- rocks (in the gaps between trees): conifer / broadleaf / treeline / alpine scenes, denser at foot of ranges
    rng = np.random.default_rng(seeds["rock-placement"])
    rs = params.rock_step * wd
    nxg, nyg = int(W / rs) + 2, int(H / rs) + 2
    gj, gi = np.mgrid[0:nyg, 0:nxg]
    u = rng.random((8,) + gi.shape).reshape(8, -1)
    x = ((gi + 0.5) * rs).ravel() + (u[0] - 0.5) * 0.7 * rs
    y = ((gj + 0.5) * rs).ravel() + (u[1] - 0.5) * 0.7 * rs
    f = feat.at(x, y)
    inside = (x > 0) & (x < W) & (y > 0) & (y < H)
    alpine = (f["mount"] > 0.25) & (f["h"] > 0.75 * params.treeline_m)
    treeline = ~alpine & ((f["mount"] > 0.10) | (f["slope"] > 0.07) | (f["h"] > 0.55 * params.treeline_m))
    scene = np.where(alpine, 3, np.where(treeline, 2, np.where(f["con"] >= 0.5, 0, 1)))
    prob = np.select([alpine, treeline], [params.rock_p_alpine, params.rock_p_treeline], default=params.rock_p_forest)
    prob = prob * np.where((f["h"] < 150.0) & (f["slope"] < 0.02), params.rock_plain_factor, 1.0)
    prob = prob * np.where(f["dedge"] <= 3.0 * wd, 1.6, 1.0)
    zone = (f["cov"] >= 0.35) | (f["mount"] > 0.15)
    cand = np.nonzero(inside & zone & (u[2] < prob))[0]
    cand = cand[np.argsort(u[7][cand], kind="stable")]
    scenes = ("conifer", "broadleaf", "treeline", "alpine")
    pools = []
    for sc in scenes:
        items = [r for r in art["rocks"] if sc in r["scenes"] and not (overview and r["kind"] in ("mossy", "scree"))]
        pools.append((items, [float(r.get("weight", 1.0)) for r in items]))
    for i in cand:
        items, wts = pools[int(scene[i])]
        if not items:
            continue
        r = items[int(_cdf_pick(wts, u[3][i]))]
        vw, vh = r["viewBox"]
        ax, ay = r["anchor"]
        w = tree_w * (1.0 + 0.2 * u[4][i])
        k = w / vw
        h = vh * k
        xx, yy = float(x[i]), float(y[i])
        box = (xx - 0.36 * w, yy - 0.8 * h, xx + 0.36 * w, yy + 0.1 * h)
        if not board.free(box):
            continue
        board.take(box)
        out.append(dict(kind="rock", id=r["id"], rock_kind=r["kind"], scene=scenes[int(scene[i])], x=xx, y=yy, w=w, h=h, box=box,
                        draw=(xx - ax * k, yy - ay * k, xx + (vw - ax) * k, yy + (vh - ay) * k), mirror=bool(u[5][i] < 0.4)))
    # ---- grass: forest floor, forest edge (tall / tuft denser), dry south
    gsyms = art["grass"]
    scene_names = ("conifer", "broadleaf", "forest_edge", "dry", "wet", "riparian")
    gpool = {}
    for sc in scene_names:
        sel = [g for g in gsyms if (g.get("scene_weights") or {}).get(sc, 0.0) > 0 and (sc == "riparian" or g["kind"] != "reed")]
        gpool[sc] = (sel, [float(g["scene_weights"][sc]) for g in sel])
    kind_mult = {"shrub": params.grass_shrub_factor, "mushroom": params.grass_mushroom_factor}
    gs = params.grass_step * wd
    rng = np.random.default_rng(seeds["grass-placement"])
    nxg, nyg = int(W / gs) + 2, int(H / gs) + 2
    gj, gi = np.mgrid[0:nyg, 0:nxg]
    u = rng.random((9,) + gi.shape).reshape(9, -1)
    x = ((gi + 0.5) * gs).ravel() + (u[0] - 0.5) * 0.8 * gs
    y = ((gj + 0.5) * gs).ravel() + (u[1] - 0.5) * 0.8 * gs
    f = feat.at(x, y)
    inside = (x > 0) & (x < W) & (y > 0) & (y < H)
    edge = f["dedge"] <= params.edge_px * s
    warm = f["north"] < params.warm_north
    gsc = np.where(edge, 2, np.where(warm, 3, np.where(f["dwater"] <= 30.0 * s, 4, np.where(f["con"] >= 0.5, 0, 1))))
    cand = np.nonzero(inside & (f["cov"] >= 0.5) & (u[2] < params.grass_density))[0]
    cand = cand[np.argsort(u[7][cand], kind="stable")]

    def put_grass(i, sc, mult=1.0):
        sel, wts = gpool[sc]
        if not sel:
            return
        g = sel[int(_cdf_pick(wts, u[3][i]))]
        m = kind_mult.get(g["kind"], 1.0) * (params.edge_boost if (sc == "forest_edge" and g["kind"] in ("tall", "tuft")) else 1.0)
        if u[4][i] >= min(1.0, m * mult):
            return
        vw, vh = g["viewBox"]
        ax, ay = g["anchor"]
        w = wd * (vw / 32.0) * (params.grass_scale[0] + (params.grass_scale[1] - params.grass_scale[0]) * u[5][i])
        k = w / vw
        ex0, ey0, ex1, ey1 = g["extent"]
        xx, yy = float(x[i]), float(y[i])
        box = (xx + (ex0 - ax) * k, yy + (ey0 - ay) * k, xx + (ex1 - ax) * k, yy + (ey1 - ay + 0.3) * k)
        if not board.free(box):
            return
        board.take(box)
        out.append(dict(kind="grass", id=g["id"], grass_kind=g["kind"], scene=sc, x=xx, y=yy, w=w, h=vh * k, box=box,
                        draw=(xx - ax * k, yy - ay * k, xx + (vw - ax) * k, yy + (vh - ay) * k), mirror=bool(u[6][i] < 0.5)))

    for i in cand:
        put_grass(i, scene_names[int(gsc[i])])
    # ---- shore reeds: only a thin ring right next to rivers / lakes, inside or at the edge of the forest
    rng = np.random.default_rng(seeds["reed-placement"])
    rg = params.reed_step * wd
    nxg, nyg = int(W / rg) + 2, int(H / rg) + 2
    gj, gi = np.mgrid[0:nyg, 0:nxg]
    u2 = rng.random((9,) + gi.shape).reshape(9, -1)
    x = ((gi + 0.5) * rg).ravel() + (u2[0] - 0.5) * 0.8 * rg
    y = ((gj + 0.5) * rg).ravel() + (u2[1] - 0.5) * 0.8 * rg
    f = feat.at(x, y)
    inside = (x > 0) & (x < W) & (y > 0) & (y < H)
    ring = (f["dwater"] > 1.0) & (f["dwater"] <= params.reed_ring_px * s) & (f["cov"] > 0.3)
    cand = np.nonzero(inside & ring & (u2[2] < params.reed_density))[0]
    cand = cand[np.argsort(u2[7][cand], kind="stable")]
    u = u2
    for i in cand:
        put_grass(i, "riparian")
    return out, seeds


# ---------------------------------------------------------------- decorations

def _deco_items(view, kind):
    s = view.s
    if kind == "overview":
        return [dict(name="legend", kind="legend", w=430 * s, h=545 * s, target=(0.86, 0.74)),
                dict(name="title", kind="cartouche", w=640 * s, h=192 * s, target=(0.62, 0.56)),
                dict(name="compass", kind="compass", w=170 * s, h=196 * s, target=(0.90, 0.30)),
                dict(name="scale", kind="scale", w=480 * s, h=96 * s, target=(0.42, 0.93)),
                dict(name="ship-1", kind="ship", w=122 * s, h=111 * s, target=(0.46, 0.76), mirror=False),
                dict(name="ship-2", kind="ship", w=104 * s, h=95 * s, target=(0.76, 0.20), mirror=True)]
    return [dict(name="compass", kind="compass", w=150 * s, h=172 * s, target=(0.92, 0.12)),
            dict(name="scale", kind="scale", w=480 * s, h=96 * s, target=(0.5, 0.93))]


def place_decorations(df, view, params, kind="overview"):
    """Decorations only on open sea: whole box at least deco_clearance_px from any land pixel and the map edge."""
    H, W = view.height, view.width
    s = view.s
    sea = df["coast"] < 0
    clear = nd.distance_transform_edt(sea) >= params.deco_clearance_px * s
    edge = int(round(16 * s))
    bad = ~clear
    bad[:edge], bad[-edge:], bad[:, :edge], bad[:, -edge:] = True, True, True, True
    placed, skipped = [], []
    step = max(4, int(round(8 * s)))
    for it in _deco_items(view, kind):
        ii = _integral(bad)
        w, h = int(math.ceil(it["w"])), int(math.ceil(it["h"]))
        ys = np.arange(0, H - h, step)
        xs = np.arange(0, W - w, step)
        if not len(ys) or not len(xs):
            skipped.append(it["name"])
            continue
        Y, X = np.meshgrid(ys, xs, indexing="ij")
        tot = ii[Y + h, X + w] - ii[Y, X + w] - ii[Y + h, X] + ii[Y, X]
        ok = tot == 0
        if not ok.any():
            skipped.append(it["name"])
            continue
        tx, ty = it["target"][0] * W - w / 2, it["target"][1] * H - h / 2
        dist = np.where(ok, (X - tx) ** 2 + (Y - ty) ** 2, np.inf)
        j = np.unravel_index(int(np.argmin(dist)), dist.shape)
        x0, y0 = int(X[j]), int(Y[j])
        g = int(round(14 * s))
        bad[max(0, y0 - g):y0 + h + g, max(0, x0 - g):x0 + w + g] = True
        placed.append(dict(it, x=float(x0), y=float(y0), w=float(w), h=float(h), box=(float(x0), float(y0), float(x0 + w), float(y0 + h))))
    return placed, skipped


# ---------------------------------------------------------------- build

@dataclass
class AtlasLayers:
    view: View
    params: AtlasParams
    map_rgb: np.ndarray        # uint8, map area only
    page_rgb: np.ndarray       # uint8, map + margin (paper)
    relief_rgb: np.ndarray     # uint8, map area only, no symbols / decorations / rivers
    margin: int
    rivers: list
    river_min_area_km2: float
    symbols: list              # terrain + trees, draw order
    decorations: list
    skipped_decorations: list
    scale: dict
    forbidden: np.ndarray
    sea: np.ndarray
    seeds: dict
    title: str
    subtitle: str
    reserved: object = None    # bool raster of reserved clearings (None when not requested)


def build_atlas(p, params=None, view=None, *, deco_kind="overview", title="世 界 地 貌 试 点", subtitle=None,
                reserved=None, fantasy_regions=None):
    params = params or AtlasParams()
    view = view or full_view(p, params.width_px)
    styles = load_styles()
    style = styles["styles"]["simple"]
    a = analyse(p, params)
    df = display_fields(p, a, view, params)
    rivers, amin = river_polylines(p, a, view, params)
    rmask = river_mask(rivers, view, params.river_pad_px)
    forbid = forbidden_mask(df, rmask, view)
    board = _Board(forbid)
    terrain = place_mountains(p, a, df, view, params, board)
    res_mask = None
    if reserved:
        res_mask = np.zeros(forbid.shape, bool)
        for m in rasterise_regions(reserved, p, view):
            res_mask |= m
    fboard = _Board(forbid | res_mask) if res_mask is not None else board
    if fboard is not board:
        fboard.occ |= board.occ
    trees, fseeds = place_forest_symbols(p, a, df, view, params, fboard, forest_context(df, forbid),
                                         fantasy=fantasy_regions)
    decorations, skipped = place_decorations(df, view, params, deco_kind)
    margin = int(round(params.margin_ref_px * view.s))
    H, W = view.height, view.width
    paper_seed = atlas_seed(p.world_seed, "paper")
    paper = paper_texture((H + 2 * margin, W + 2 * margin), view.s, paper_seed, style["paper"])
    inner = paper[margin:margin + H, margin:margin + W, None]
    relief = paint_map(p, df, view, params, style, shade_reduce=None, forest=False)
    relief_rgb = np.clip(relief * inner, 0, 255).round().astype(np.uint8)
    del relief
    rgb = paint_map(p, df, view, params, style, shade_reduce=None, forest=True)
    map_rgb = np.clip(rgb * inner, 0, 255).round().astype(np.uint8)
    page = np.empty((H + 2 * margin, W + 2 * margin, 3))
    page[:] = hex_rgb(style["page"]["background"])
    page *= paper[..., None]
    page_rgb = np.clip(page, 0, 255).round().astype(np.uint8)
    page_rgb[margin:margin + H, margin:margin + W] = map_rgb
    symbols = sorted(terrain + trees, key=lambda q: (round(q["box"][3], 3), round(q["x"], 3)))
    seeds = dict(a["seeds"])
    seeds.update(fseeds)
    seeds.update({"paper": paper_seed, "snow-noise": atlas_seed(p.world_seed, "snow-noise")})
    sc = scale_bar(view.mpp, view.s)
    if subtitle is None:
        subtitle = "%d km 生成地表 · %s × %s km · 每像素 %s m" % (
            round(p.spacing / 1000), _num(view.nx * p.spacing / 1000), _num(view.nz * p.spacing / 1000), _num(view.mpp))
    return AtlasLayers(view=view, params=params, map_rgb=map_rgb, page_rgb=page_rgb, relief_rgb=relief_rgb, margin=margin,
                       rivers=rivers, river_min_area_km2=amin, symbols=symbols, decorations=decorations,
                       skipped_decorations=skipped, scale=sc, forbidden=forbid, sea=df["coast"] < 0, seeds=seeds,
                       title=title, subtitle=subtitle, reserved=res_mask)


def _num(v):
    v = float(v)
    return ("%d" % round(v)) if abs(v - round(v)) < 1e-6 or abs(v) >= 100 else ("%.1f" % v)


# ---------------------------------------------------------------- SVG / HTML composition

def _f(v):
    return ("%.2f" % v).rstrip("0").rstrip(".")


def _text(x, y, txt, cls, size, anchor="middle", extra=""):
    return '<text x="%s" y="%s" class="%s" font-size="%s" text-anchor="%s"%s>%s</text>' % (
        _f(x), _f(y), cls, _f(size), anchor, extra, _html.escape(txt))


def _use(sid, x, y, w, h, extra=""):
    return '<use href="#%s" x="%s" y="%s" width="%s" height="%s"%s/>' % (sid, _f(x), _f(y), _f(w), _f(h), extra)


def sprite_defs(art_dir=ART_DIR, used_ids=()):
    """Only the symbols actually used: base terrain / deco ids from map-art.svg plus the tree / rock / grass ids placed."""
    art = load_art(art_dir)
    used = set(used_ids)
    base = [i for i in list(TERRAIN_IDS) + list(DECO_IDS) if i in used or i in DECO_IDS]
    syms = extract_symbols(Path(art_dir, BASE_SVG).read_text(encoding="utf-8"), base)
    by_file = {}
    for sid in sorted(used):
        if sid in art["files"]:
            by_file.setdefault(art["files"][sid], []).append(sid)
    for fname in sorted(by_file):
        syms += extract_symbols(Path(art_dir, fname).read_text(encoding="utf-8"), by_file[fname])
    syms += extract_symbols(Path(art_dir, SHIP_SPRITE).read_text(encoding="utf-8"), [SHIP_ID])
    return '<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" style="position:absolute"><defs>%s</defs></svg>' % "\n".join(syms)


def river_color():
    return load_manifest()["routes"]["kinds"]["river"]["stroke"]


def _rivers_svg(rivers, color):
    out = ['<g fill="none" stroke="%s" stroke-linecap="round" stroke-linejoin="round" stroke-opacity=".92">' % color]
    for r in rivers:
        pts, ws = r["points"], r["widths"]
        seg_w = np.round(0.5 * (ws[:-1] + ws[1:]) / 0.2) * 0.2
        i = 0
        while i < len(seg_w):
            j = i
            while j + 1 < len(seg_w) and seg_w[j + 1] == seg_w[i]:
                j += 1
            d = "M" + " L".join("%s %s" % (_f(pts[k][0]), _f(pts[k][1])) for k in range(i, j + 2))
            out.append('<path d="%s" stroke-width="%s"/>' % (d, _f(seg_w[i])))
            i = j + 1
    out.append("</g>")
    return out


def _frame_svg(L, p, style):
    view, s = L.view, L.view.s
    W, H = view.width, view.height
    ink = style["page"]["ink"]
    mpp = view.mpp
    edge_x = p.first[0] - p.spacing / 2 + view.x0 * p.spacing
    edge_z = p.first[1] - p.spacing / 2 + view.z0 * p.spacing
    span = W * mpp
    tick = next(t for t in (5e3, 1e4, 2e4, 2.5e4, 5e4, 1e5, 2e5) if span / t <= 24)
    label = tick * 2
    o, t = 6 * s, 7 * s
    q = ['<rect x="-0.5" y="-0.5" width="%s" height="%s" fill="none" stroke="%s" stroke-width="%s"/>' % (_f(W + 1), _f(H + 1), ink, _f(1.4 * s))]
    for side in range(4):
        n_len = W if side % 2 == 0 else H
        start_m = edge_x if side % 2 == 0 else edge_z
        k0 = math.floor(start_m / tick)
        k = k0
        while True:
            a = (k * tick - start_m) / mpp
            b = ((k + 1) * tick - start_m) / mpp
            if a >= n_len:
                break
            a, b = max(a, 0.0), min(b, n_len)
            if k % 2 == 0 and b > a:
                r = {0: (a, -o - t, b - a, t), 2: (a, H + o, b - a, t), 1: (W + o, a, t, b - a), 3: (-o - t, a, t, b - a)}[side]
                q.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s"/>' % (tuple(_f(v) for v in r) + (ink,)))
            k += 1
    for off, sw in ((o, 0.9), (o + t, 0.9), (o + t + 7 * s, 2.4)):
        q.append('<rect x="%s" y="%s" width="%s" height="%s" fill="none" stroke="%s" stroke-width="%s"/>' % (
            _f(-off), _f(-off), _f(W + 2 * off), _f(H + 2 * off), ink, _f(sw * s)))
    lab = o + t + 18 * s
    v = math.ceil(edge_x / label) * label
    while (v - edge_x) / mpp <= W - 120 * s:
        q.append(_text((v - edge_x) / mpp, -lab, "%d" % round(v / 1000), "t-coord", 15 * s))
        v += label
    v = math.ceil(edge_z / label) * label
    while (v - edge_z) / mpp <= H - 60 * s:
        q.append(_text(-lab + 4 * s, (v - edge_z) / mpp + 5 * s, "%d" % round(v / 1000), "t-coord", 15 * s, "end"))
        v += label
    q.append(_text(W + lab - 4 * s, -lab, "X 东 / km", "t-coord", 14 * s, "end"))
    q.append(_text(-lab + 4 * s, H + lab + 4 * s, "Z 南 / km", "t-coord", 14 * s, "start"))
    return q


def _scale_svg(d, sc, style, s):
    L, n = sc["length_px"], sc["segments"]
    x0, yb = d["x"] + (d["w"] - L) / 2 - 12 * s, d["y"] + 40 * s
    q = ['<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="#efe3c6" fill-opacity=".72"/>' % (
        _f(d["x"]), _f(d["y"]), _f(d["w"]), _f(d["h"]), _f(6 * s))]
    k = L / 115.0
    q.append(_use("deco-scale", x0 - 2 * k, yb - 5 * k, 120 * k, 16 * k))
    for i in range(n + 1):
        q.append(_text(x0 + i * L / n, yb - 8 * s, _num(sc["segment_m"] * i / 1000.0), "t-body", 17 * s))
    q.append(_text(x0 + L + 10 * s, yb + 8 * s, "km", "t-body", 17 * s, "start"))
    q.append(_text(x0 + L / 2, yb + 38 * s, "比例尺 · 每像素 %s m" % _num(sc["m_per_px"]), "t-body", 15 * s))
    return q


def legend_rows(L):
    p = L.params
    has = {sym["kind"] for sym in L.symbols}
    rows = [("river", None, "河流 · 产品河网，汇水 ≥ %s km²" % _num(L.river_min_area_km2)),
            ("lake", None, "湖面 · 填洼水面（无水量平衡）")]
    if "mountain" in has:
        rows.append(("symbol", "terrain-mountain", "山脉 · 底色与阴影示范围，每片仅最高点一座"))
    if "snowpeak" in has:
        rows.append(("symbol", "terrain-snowpeak", "高峰 · 附近海拔 ≥ %s m（显示阈值）" % _num(p.snowpeak_m)))
    scenes = {sym.get("scene") for sym in L.symbols if sym["kind"] == "tree"}
    if "conifer" in scenes:
        rows.append(("symbol", "tree-larch", "针叶林 · 混排，近似，非气候数据"))
    if "broadleaf" in scenes:
        rows.append(("symbol", "tree-oak", "阔叶林 · 混排，近似，非气候数据"))
    return rows


def _legend_svg(d, L, style, rcolor):
    s = L.view.s
    ink = style["page"]["ink"]
    x, y, w, h = d["x"], d["y"], d["w"], d["h"]
    q = ['<rect x="%s" y="%s" width="%s" height="%s" fill="#f4ead2" fill-opacity=".94" stroke="%s" stroke-width="%s"/>' % (
        _f(x), _f(y), _f(w), _f(h), ink, _f(1.6 * s)),
        '<rect x="%s" y="%s" width="%s" height="%s" fill="none" stroke="%s" stroke-width="%s"/>' % (
        _f(x + 6 * s), _f(y + 6 * s), _f(w - 12 * s), _f(h - 12 * s), style["page"]["accent"], _f(0.8 * s))]
    q.append(_text(x + w / 2, y + 42 * s, style["text"]["legend_title"], "t-title", 28 * s))
    pad = 24 * s
    bw = w - 2 * pad
    cy = y + 64 * s
    lands = [b for b in style["land_bands"] if b["max_m"] is not None and b["max_m"] <= 3000]
    q.append(_text(x + pad, cy + 10 * s, "海拔（米）· 平原段平滑过渡", "t-body", 15 * s, "start"))
    by = cy + 18 * s
    n = len(lands) + 1
    for i, b in enumerate(lands + [{"color": "#f3efe6"}]):
        q.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s"/>' % (_f(x + pad + i * bw / n), _f(by), _f(bw / n + 0.5), _f(14 * s), b["color"]))
    q.append('<rect x="%s" y="%s" width="%s" height="%s" fill="none" stroke="%s" stroke-width="%s"/>' % (_f(x + pad), _f(by), _f(bw), _f(14 * s), ink, _f(0.8 * s)))
    for i, b in enumerate(lands):
        if i % 2 == 1 or i == len(lands) - 1:
            q.append(_text(x + pad + (i + 1) * bw / n, by + 30 * s, "%d" % b["max_m"], "t-body", 12.5 * s))
    q.append(_text(x + pad, by + 48 * s, "最右格：雪色，按海拔与坡向渐变（显示，非积雪数据）", "t-body", 12.5 * s, "start"))
    cy += 84 * s
    oc = style["ocean_bands"]
    q.append(_text(x + pad, cy + 10 * s, "水深（米）", "t-body", 15 * s, "start"))
    by = cy + 18 * s
    n = len(oc)
    for i, b in enumerate(oc):
        q.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s"/>' % (_f(x + pad + i * bw / n), _f(by), _f(bw / n + 0.5), _f(14 * s), b["color"]))
    q.append('<rect x="%s" y="%s" width="%s" height="%s" fill="none" stroke="%s" stroke-width="%s"/>' % (_f(x + pad), _f(by), _f(bw), _f(14 * s), ink, _f(0.8 * s)))
    for i, b in enumerate(oc[:-1]):
        q.append(_text(x + pad + (i + 1) * bw / n, by + 30 * s, "%d" % b["max_depth_m"], "t-body", 12.5 * s))
    cy += 66 * s
    row = 34 * s
    for kind, sid, label in legend_rows(L):
        ry = cy + row / 2
        ix = x + pad + 22 * s
        if kind == "river":
            q.append('<path d="M%s %s C%s %s %s %s %s %s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
                _f(ix - 20 * s), _f(ry + 5 * s), _f(ix - 6 * s), _f(ry - 8 * s), _f(ix + 6 * s), _f(ry + 8 * s), _f(ix + 20 * s), _f(ry - 4 * s),
                rcolor, _f(2.2 * s)))
        elif kind == "lake":
            q.append('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="%s" stroke="%s" stroke-width="%s"/>' % (
                _f(ix), _f(ry), _f(18 * s), _f(9 * s), style["ocean_bands"][1]["color"], ink, _f(0.9 * s)))
        else:
            vb = (24.0, 12.0) if sid == "terrain-hill" else (16.0, 20.0) if sid.startswith("tree-") else (24.0, 18.0)
            sw = (34 if not sid.startswith("tree-") else 16) * s
            sh = sw * vb[1] / vb[0]
            q.append(_use(sid, ix - sw / 2, ry - sh / 2, sw, sh))
            if sid.startswith("tree-"):
                q.append(_use(sid, ix - sw / 2 - 13 * s, ry - sh / 2 + 3 * s, sw * 0.8, sh * 0.8))
                q.append(_use(sid, ix - sw / 2 + 14 * s, ry - sh / 2 + 2 * s, sw * 0.85, sh * 0.85))
        q.append(_text(x + pad + 52 * s, ry + 5 * s, label, "t-body", 14.5 * s, "start"))
        cy += row
    cy += 10 * s
    for note in ("罗盘、帆船、标题框为制图装饰，不表示数据",
                 "未绘：城镇、道路、地名、资源（无数据）"):
        q.append(_text(x + pad, cy + 8 * s, note, "t-body", 12.5 * s, "start"))
        cy += 20 * s
    return q


def legend_height(L):
    s = L.view.s
    return (64 + 84 + 66 + 34 * len(legend_rows(L)) + 10 + 40 + 24) * s


def compose_html(L, p, base_href, *, with_overlays=True):
    styles = load_styles()
    style = styles["styles"]["simple"]
    s = L.view.s
    ink = style["page"]["ink"]
    fonts = style["fonts"]
    page_h, page_w = L.page_rgb.shape[:2]
    W, H, m = L.view.width, L.view.height, L.margin
    o = ['<!DOCTYPE html><html><head><meta charset="utf-8"><style>html,body{margin:0;padding:0;background:%s;overflow:hidden}'
         '.t-title{font-family:%s;fill:%s}.t-body{font-family:%s;fill:%s}.t-latin{font-family:%s;fill:%s;font-style:italic}'
         '.t-coord{font-family:%s;fill:%s;opacity:.8}</style></head><body>' % (
             style["page"]["background"], fonts["title"], ink, fonts["body"], ink, fonts["latin"], ink, fonts["latin"], ink)]
    o.append(sprite_defs(used_ids={sym["id"] for sym in L.symbols}))
    o.append('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" style="display:block">' % (page_w, page_h, page_w, page_h))
    o.append('<image href="%s" x="0" y="0" width="%d" height="%d"/>' % (_html.escape(base_href), page_w, page_h))
    o.append('<defs><clipPath id="map-clip"><rect x="0" y="0" width="%d" height="%d"/></clipPath></defs>' % (W, H))
    o.append('<g transform="translate(%d,%d)">' % (m, m))
    if with_overlays:
        o.append('<g clip-path="url(#map-clip)">')
        o += _rivers_svg(L.rivers, river_color())
        for sym in L.symbols:
            x0, y0, x1, y1 = sym["draw"]
            if sym.get("mirror"):
                o.append('<g transform="translate(%s,%s) scale(-1,1)">%s</g>' % (_f(x1), _f(y0), _use(sym["id"], 0, 0, x1 - x0, y1 - y0)))
            else:
                o.append(_use(sym["id"], x0, y0, x1 - x0, y1 - y0))
        o.append("</g>")
        rcolor = river_color()
        for d in L.decorations:
            x, y, w, h = d["x"], d["y"], d["w"], d["h"]
            if d["kind"] == "ship":
                if d.get("mirror"):
                    o.append('<g transform="translate(%s,%s) scale(-1,1)">%s</g>' % (_f(x + w), _f(y), _use(SHIP_ID, 0, 0, w, h)))
                else:
                    o.append(_use(SHIP_ID, x, y, w, h))
            elif d["kind"] == "cartouche":
                o.append(_use("deco-cartouche", x, y, w, h))
                o.append(_text(x + w / 2, y + h * 0.47, L.title, "t-title", h * 0.19, extra=' font-weight="bold"'))
                o.append(_text(x + w / 2, y + h * 0.61, "TABULA ORBIS EX DATIS · SIMPLEX", "t-latin", h * 0.072))
                o.append(_text(x + w / 2, y + h * 0.72, L.subtitle, "t-body", h * 0.066))
            elif d["kind"] == "compass":
                o.append(_text(x + w / 2, y + 30 * s, "N", "t-latin", 34 * s, extra=' font-weight="bold" font-style="normal"'))
                cs = min(w, h - 40 * s)
                o.append(_use("deco-compass", x + (w - cs) / 2, y + 40 * s, cs, cs))
            elif d["kind"] == "scale":
                o += _scale_svg(d, L.scale, style, s)
            elif d["kind"] == "legend":
                o += _legend_svg(d, L, style, rcolor)
        if not any(d["kind"] == "scale" for d in L.decorations):  # zoom pages: scale bar in the bottom margin
            o += _scale_svg(dict(x=20.0 * s, y=H - 116 * s, w=480 * s, h=96 * s), L.scale, style, s)
    o += _frame_svg(L, p, style)
    o.append("</g></svg></body></html>")
    return "\n".join(o)


def page_size(L):
    return L.page_rgb.shape[1], L.page_rgb.shape[0]


# ---------------------------------------------------------------- provenance

def summarize(L):
    kinds = {}
    for sym in L.symbols:
        kinds[sym["kind"]] = kinds.get(sym["kind"], 0) + 1
    tiers = {}
    for sym in L.symbols:
        if sym["kind"] in ("mountain", "snowpeak"):
            tiers[sym["tier"]] = tiers.get(sym["tier"], 0) + 1
    return dict(map_px=[L.view.width, L.view.height], margin_px=L.margin, metres_per_pixel=L.view.mpp,
                window_cells_zx=dict(z0=L.view.z0, x0=L.view.x0, nz=L.view.nz, nx=L.view.nx),
                scale_bar=dict(metres=L.scale["meters"], length_px=L.scale["length_px"], segments=L.scale["segments"],
                               check_length_px_times_m_per_px=L.scale["length_px"] * L.view.mpp),
                river_min_area_km2=L.river_min_area_km2, river_polylines=len(L.rivers),
                symbols=kinds, mountain_tiers=tiers,
                decorations=[dict(name=d["name"], kind=d["kind"], box_px=[round(v, 1) for v in d["box"]]) for d in L.decorations],
                skipped_decorations=L.skipped_decorations)


def display_coast_agreement(p, params):
    """Fraction of product cells whose class survives the display-only coast smoothing (evaluated at cell centres)."""
    land = ~p.ocean
    g = nd.gaussian_filter(land * 2.0 - 1.0, params.coast_smooth_cells)
    shown = g > 0
    return dict(land_cells_shown_as_land=float((shown & land).sum() / max(1, land.sum())),
                ocean_cells_shown_as_sea=float((~shown & ~land).sum() / max(1, (~land).sum())),
                land_cells_lost=int((land & ~shown).sum()), ocean_cells_covered=int((~land & shown).sum()),
                rule="display coast = zero level of Gaussian(sigma=%s cells) smoothed land(+1)/sea(-1) indicator" % params.coast_smooth_cells)


def params_dict(params):
    return {k: (list(v) if isinstance(v, tuple) else v) for k, v in asdict(params).items()}


# ---------------------------------------------------------------- relief-only page / provenance

def relief_page(L, p=None):
    """Same paper page and base raster, but no forest tint, rivers, symbols, decorations, frame or text."""
    from PIL import Image
    page = L.page_rgb.copy()
    m, H, W = L.margin, L.view.height, L.view.width
    page[m:m + H, m:m + W] = L.relief_rgb
    return Image.fromarray(page)


def provenance(p, L, params, files, product_path=None):
    """atlas-source.json body: product identity, scale, per-layer origin (data / approximate / decoration), omissions."""
    view = L.view
    return dict(
        schema=SCHEMA,
        product=dict(path=str(product_path or p.path), kind=p.info.kind, identity=p.identity, schema=p.manifest.get("schema"),
                     source_identity=p.manifest.get("source_identity"), world_seed=p.world_seed,
                     source_world_seed=p.manifest.get("source_world_seed"), shape_zx=list(p.shape),
                     first_sample_xz_m=list(p.first), spacing_m=p.spacing, axes=p.manifest.get("axes"),
                     interface="app.map_source (load_source / MapCatalog.from_config); GridSource.sample at every cell centre + vectors('rivers')",
                     consumed_layers=list(CONSUMED_LAYERS),
                     verification="identity / file hashes / manifest shape are verified by the app.map_source adapter before any data is returned; this module never opens .npy or rivers.json",
                     limitations=p.manifest.get("limitations", [])),
        coast_elevation_check=coast_elevation_medians(p),
        display_coast_agreement=display_coast_agreement(p, params),
        scale=dict(metres_per_pixel=view.mpp, map_px=[view.width, view.height],
                   extent_km=[view.nx * p.spacing / 1000, view.nz * p.spacing / 1000],
                   scale_bar_metres=L.scale["meters"], scale_bar_length_px=L.scale["length_px"]),
        layers=dict(
            data=[
                "海陆：ocean_mask 原样（显示海岸为 σ=%s 格高斯平滑的海陆指示零值线，只消除格子台阶，逐格一致率见 display_coast_agreement）" % params.coast_smooth_cells,
                "陆地分层设色：elevation_m；styles.json simple 色板，平原段（局部起伏 < %d m）在 %d m 尺度上平滑过渡，不画等色带边线" % (params.plain_relief_m, params.plain_smooth_m),
                "海洋分档：elevation_m 水深，styles.json simple ocean_bands",
                "山体阴影：elevation_m，方位 %s°、高度角 %s°、z×%s；山脉范围内阴影加强 %d%%（山体范围见下）" % (params.shade_azimuth_deg, params.shade_altitude_deg, params.shade_z_factor, round(params.mount_shade_boost * 100)),
                "湖泊：lake_surface_m − elevation_m ≥ %s m 且连片 ≥ %d 格的填洼水面（产品无湖泊水量平衡）" % (params.lake_min_depth_m, params.lake_min_cells),
                "河流：经 app.map_source vectors('rivers') 读取的折线原样；只画汇水面积 ≥ %.0f km² 的部分（屏幕门槛），线宽随 log2(汇水面积) 加粗；Chaikin %d 次平滑，端点/汇流点/入海点不动" % (L.river_min_area_km2, params.river_chaikin),
                "山地识别：elevation_m 的局部起伏（%d km 窗）、相对基面高度（%d km 窗）与坡度；每片 8 连通山地只在其最高点画一座山峰符号（丘陵不画符号），山脉范围由底图山地色调 + 加强阴影表现" % (params.relief_window_m / 1000, params.base_window_m / 1000),
            ],
            approximate=[
                "雪色：按高程 + 坡向渐变的显示效果（基准 %d m，阴坡低 %d m，过渡 %d m），不是积雪数据" % (params.snow_base_m, params.snow_aspect_m, params.snow_transition_m),
                "雪峰符号：符号所在山峰高程 ≥ %d m（显示参数），不是积雪数据" % params.snowpeak_m,
                "森林与植被：按高程、坡度、离海距离与南北位置粗分（针叶 ≥ %d m 或偏北，阔叶其余），近似，非气候数据" % params.conifer_m,
                "林区混排：树（运行时从 map-art-trees-a/-b.svg 解析的 symbol，按高程/南北/离海/坡度/坐标噪声区块给树种比例，变种/缩放/镜像随机，间距约 %.2f 树宽）+ 石头（ground-rocks）+ 草（ground-grass，水边芦苇仅紧邻河湖）；奇幻树种默认不用" % params.tree_gap,
            ],
            decoration=["纸纹（种子 atlas/paper）", "标题框 deco-cartouche、罗盘 deco-compass（map-art.svg）",
                        "帆船 deco-carrack（map-art-medieval-deco.svg），只放开阔海面，不表示航线或数据",
                        "比例尺：长度 px × 每像素米数 = 标注米数"],
            not_drawn=["城镇", "道路", "地名", "资源", "国界/行政区", "气候/降水", "洋流"],
            display_workarounds_for_data_defects=[
                "河线长直斜段（D8 方向偏好）：沿线高斯平滑（σ=%s km，两端权重渐降为 0）+ Chaikin %d 次，端点/汇流点/入海点与河网连接不变；长直段的走向来自数据，平滑只能软化折角" % (params.river_smooth_km, params.river_chaikin),
                "沿海平行短沟（梳齿）：离岸 %s km 尺度内按 exp 衰减最多减弱 %d%% 阴影强度，高程不变" % (params.coast_shade_km, round(params.coast_shade_cut * 100)),
                "雪线偏硬：雪色按高程 + 坡向（阳坡抬高、阴坡降低 %d m）+ 阴影明暗渐变，过渡带 %d m，最大不透明度 %s" % (params.snow_aspect_m, params.snow_transition_m, params.snow_max_alpha),
                "平原零碎色斑：局部起伏 < %d m 处改用 %d km 平滑高程取色，不画等色带边线" % (params.plain_relief_m, params.plain_smooth_m / 1000),
            ],
        ),
        seeds=dict(method="subseed(world_seed, 'atlas/<purpose>') = first 8 bytes big-endian of SHA-256(UTF-8 f'{world_seed}:atlas/<purpose>')",
                   world_seed=p.world_seed, values={k: int(v) for k, v in L.seeds.items()}),
        parameters=params_dict(params),
        files=files,
    )
