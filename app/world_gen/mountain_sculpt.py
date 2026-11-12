"""Local mountain-structure prototype: one interior window, CPU, **not** wired into the default world layer.

The world layer builds mountains from wide orogen belts (``ridge_network.rasterize_orogen``): a 900-1300 km wide
flat-topped platform (belt floor + plateau weight) with the level-1/2/3 ridge envelope and a ridged multifractal on
its surface. Read on a map that is a broad massif, not a readable mountain system. This module reorganises **one
window** of such a world into a clear structure: a narrow main chain (150-400 km across), branches, longitudinal
valleys between chains and a few intramontane basins with a finite-width flat floor.

What it is / is not (docs/terrain-generation-rules.md sections 0 and 6)
----------------------------------------------------------------------
* It is a declared local experiment (``dream-mountain-sculpt-prototype-3``, algorithm
  ``mountain-sculpt-3-envelope-reach``). It is **not** a world-map product, has no game-world manifest identity,
  and nothing in the default pipeline calls it. ``structure_policy='corridor'`` still reproduces v1 bit for bit and
  keeps the v1 identity tags (``dream-mountain-sculpt-prototype-1`` / ``mountain-sculpt-1``).
* v3 fixes the accepted v2 look in one place only: the corridor sub-rectangle is now sized from the **widest
  envelope a segment can actually reach** (``chain_width_gain`` * (1 + ``width_var``), plus the warp), so the
  modulated, widened flanks / fringe are no longer truncated along a straight sub-rectangle edge - the visible
  cut-off edges of candidate-platform-final. Nothing about width, amplitude, the hierarchy of segments or the
  outline parameters changes: the fixed cells are restored to what the same algorithm already asked for. The
  broader-massif / height-width question is still open and is not touched here.
* v2 separates the **safe domain** (where the surface is allowed to change: the selected belt's saved wide band plus
  an outward buffer, dry land only) from the **mountain outline** (rebuilt crest envelope, width-varied, low-frequency
  fringe cut). Inside the domain the old wide platform's excess is replaced by a rebuilt low base + a kept, direction
  modulated share of the old excess + piedmont + chain, so the platform edge may retreat while the massif sits on the
  old trend: a readable mountain system, not the old flat platform with extra texture.
* The belt's level-1 chain is stored as **disconnected segments** (19 on the real belt); v2 takes all of them as the
  backbone (narrowed and slightly lowered) instead of the two longest, which would leave most of the platform with no
  chain. Amplitude is calibrated **after** the outline cut / along-chain / mass modulation, on the selected main lines
  themselves - normalising before the cut is what let a strong cut delete the chain on the real belt. The fringe
  incision is expressed as a share of ``peak_relief_m`` because the chain is still in amplitude units at that point.
* The change meets the kept old surface along a **wide border taper** (``edge_taper_km``, 80-200 km), not a few-cell
  halo: a 4 km platform next to a fixed border must not become a straight wall on the map.
* Real elevation is changed (metres), not a display filter. The main direction comes from the stored ridge network
  (level-1 chain chord + parent/child branch graph); no PCA line replaces it.
* Coastline and everything outside an explicit inland mountain support stay **bitwise** unchanged: ocean, closed
  below-sea bed, lakes and the outermost window ring are fixed, and a halo smoothstep blends old to new.
* **No hydrology is computed.** No river and no lake is drawn and no old river line is copied onto the new surface;
  basins are terrain flats, not water. Optional coarse erosion reuses ``fast_relief.erode`` (irregular graph, never
  D8) with the window border as a finite exit - not a closed catchment of the whole world.
* The volume change is reported and is **artistic generation**, not a mass-conserving geological process.

Reused read-only: ``ridge_network`` (network load/hash check, ridged multifractal, passes), ``fast_relief`` (value
noise, blocked grids, coarse erosion), ``graph_hydro`` (irregular mesh for the erosion). Those modules are neither
modified nor copied; their sha256 goes into the result meta.

Interface (metres, cell centres, arrays ``[z, x]``; X east, Z south)
-------------------------------------------------------------------
    net, sk_manifest = ridge_network.load_network(skeleton_npz)
    grid = grid_from_index(ix0, iz0, nx, nz, first_xz_m, spacing_m)   # or grid_from_rect(rect_m, ...)
    win = load_window(product_dir, grid, expected_identity=...)        # I/O + hash checks
    structure = select_structure(net, grid['rect_m'], belt=4, params=...)
    result = apply_window(win, structure, grid, world_seed=..., params=..., erosion=False)
    write_candidate(out_dir, result)

Result dict keys: ``before_m, after_m, changed_mask`` (every cell whose value moved at all), ``significant_mask``
(>= ``min_rise_m``, report only), ``blend_weight, support, valley_mask, basin_mask, halo_weight`` (window arrays),
``first_xz_m, spacing_m, shape, rect_m, index``, ``structure`` (metres), ``passes``, ``meta`` (with ``source``:
product identity + the skeleton ``source_identity`` it was generated from), ``identity``.
``write_candidate`` writes ``arrays.npz`` + ``structure.json`` + a draft ``README.md`` (the main agent owns the
final wording of that README).
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from pathlib import Path

import numpy as np

from . import fast_relief as fr
from . import ridge_network as rn
from .config import derive_subseed

SCHEMA = 'dream-mountain-sculpt-prototype-3'
ALGORITHM = 'mountain-sculpt-3-envelope-reach'
SCHEMA_V1 = 'dream-mountain-sculpt-prototype-1'      # structure_policy='corridor' keeps the v1 identity tags
ALGORITHM_V1 = 'mountain-sculpt-1'
SCHEMA_G = 'dream-mountain-sculpt-prototype-4'       # structure_policy='mountain-group': own identity, so the
ALGORITHM_G = 'mountain-sculpt-4-mountain-group'    # approved platform-rebuild replay is never rewritten
POLICIES = ('platform-rebuild', 'corridor', 'mountain-group')
SEED_PURPOSES = ('mountain-sculpt/warp', 'mountain-sculpt/crest', 'mountain-sculpt/passes', 'mountain-sculpt/basins',
                 'mountain-sculpt/floor', 'mountain-sculpt/mesh', 'mountain-sculpt/piedmont', 'mountain-sculpt/fringe',
                 'mountain-sculpt/width')
REUSED = ('app/world_gen/ridge_network.py', 'app/world_gen/fast_relief.py', 'app/world_gen/graph_hydro.py')
KIND_KEYS = {'main': 'main', 'branch': 'branches', 'spur': 'spurs'}      # structure dict key per chain kind

DEFAULTS = dict(
    spacing_m=10000.0,
    # --- chain selection: structure from the saved network, never a PCA of the height field ---
    max_main_chains=2, min_main_length_km=250.0, min_direction_coherence=0.55, min_main_separation_km=180.0,
    vertex_step_km=6.0,
    # --- cross sections: asymmetric tent (1-d/w)**exp, never a Gaussian ---
    main_width_scale=1.30, branch_width_scale=0.95, spur_width_scale=0.75,
    profile_exp=1.55, warp_amp_km=5.0, warp_wavelengths_km=(46.0, 17.0),
    crest_floor=0.58, crest_gain=0.48, ridged_wavelengths_km=(56.0, 28.0, 14.0), ridged_h=0.85,
    ridged_gain=2.0, ridged_offset=1.0,
    # --- support: explicit inland mountain support carrying the change ---
    support_width_scale=1.55, support_width_extra_km=18.0, support_exp=0.75,
    branch_support_scale=1.45, branch_support_extra_km=12.0,
    min_rise_m=350.0,                     # significance threshold of the *report* mask only (not a revert)
    # --- valleys / intramontane basins (terrain flats, no water) ---
    floor_radius_km=95.0, floor_start_km=55.0, floor_min_m=400.0, floor_max_m=2200.0,
    basins_max=4, basin_radius_km=55.0, basin_core_frac=0.55, basin_depth_m=260.0,
    basin_separation_km=120.0, basin_edge_km=70.0, basin_max_env=0.16, basin_min_support=0.85,
    connector_half_km=13.0, connector_len_km=130.0, connector_drop_m=90.0,
    # --- passes (saddles): network positions with softened depth, plus a few deterministic ones ---
    min_passes=3, pass_spacing_km=220.0, pass_depth=(0.28, 0.45), pass_half_km=(26.0, 44.0),
    pass_depth_scale=0.5, pass_depth_max=0.45,
    # --- structure policy: 'platform-rebuild' (default, v2) or 'corridor' (exact v1 replay) ---
    structure_policy='platform-rebuild',
    # --- safe domain: saved belt wide band + an outward perturbation buffer (a DOMAIN, not a mountain outline) ---
    belt_support_scale=1.02, belt_support_extra_km=55.0, coast_guard_cells=6,
    # --- rebuilt base: lowland-style ramp, mixed back to the old surface at the domain edge (no step) ---
    base_start_m=120.0, base_rise_m=700.0, base_plateau_km=350.0, base_relief_m=90.0, base_cap_m=1150.0,
    min_land_m=25.0,
    # --- mountain excess rebuilt from scratch: base + piedmont + chain (the old platform is not kept) ---
    piedmont_amp_m=420.0, piedmont_wavelengths_km=(240.0, 150.0, 90.0),
    # --- old massif footprint: the chain excess only grows where the old surface was actually a massif, so a
    #     lowland next to the belt is not turned into mountain; the buffer zone gets foothills only ---
    mass_low_share=0.12, mass_high_share=0.42, piedmont_lowland_share=0.35,
    # --- v2 backbone: take every level-1 line of the belt (the source chain is stored as disconnected segments, so
    #     picking two of them leaves most of the platform without a chain), physically narrower and a bit lower ---
    all_main_chains=True, backbone_width_scale=0.70, backbone_amp_scale=0.85,
    # --- v2 keeps a small, direction-modulated share of the old excess (never the full belt platform) ---
    keep_old_excess=0.30, keep_old_core=0.15,
    # --- v2 amplitude calibration: done on the FINAL chain (after cut / along-chain / mass), so the cut cannot eat
    #     the main chain; the target relief of a 5 km massif is capped by the old peak above the new base ---
    peak_relief_m=5000.0, chain_cal_gain_range=(0.5, 20000.0),   # gain converts amp units -> metres
    # --- v2 window-border transition: a wide taper, never a 6-cell straight wall against the kept old plateau ---
    edge_taper_km=150.0, edge_taper_max_share=0.22,   # never a large share of a small window
    # --- outline: widths vary and the fringe is cut by low-frequency fields (tens of km, visible at 10 km cells) ---
    width_var=0.45, width_var_wavelengths_km=(320.0, 180.0, 100.0), chain_width_gain=1.85,
    fringe_cut=0.65, fringe_level=0.45, fringe_wavelengths_km=(180.0, 110.0, 64.0), fringe_incise_m=320.0,  # share of peak_relief_m
    fringe_core_share=0.40,                # share of the cut that also reaches the crest (0 = flanks only)
    along_amp_var=0.30, along_amp_wavelengths_km=(340.0, 200.0, 110.0),   # high sections / saddles along a chain
    crest_smooth_cells=3,                  # v2: box mean of the crest multiplier, so a chain is continuous, not spikes
    peak_soft_share=0.045,                 # soft cap: summits approach the old peak, never clip to a flat table
    detail_wavelengths_km=(84.0, 52.0, 36.0),      # >= ~40 km detail: no 7-14 km noise on 10 km cells
    # --- v3 mountain-group surface (structure_policy='mountain-group' only; platform-rebuild / corridor ignore these) ---
    # A separate identity (SCHEMA_G) with its own knobs: the approved platform-rebuild replay is never rewritten.
    group_keep_excess=(0.30, 0.50),     # share of the OLD excess kept as the group's regional body (not flattened to base)
    group_body_wavelengths_km=(260.0, 160.0, 100.0),
    group_body_amp_m=520.0,             # <= this share of the local relief holds the group's mid/low mountains
    group_spur_scale=1.55,              # range should: how much wider than a crest the group body is (x tent width)
    group_valley_depth_m=700.0,         # trunk valley incision below the group floor (finite width, no canyon)
    group_valley_half_km=(50.0, 90.0),  # trunk half width range along the chain
    group_valley_share=0.60,            # how much of the basin depth the trunk valley keeps
    group_slope_range=(0.02, 0.06),     # regional mean slope dH / R accepted: about 1-3.4 deg, a range not a law
    group_relief_range_m=(1800.0, 4000.0),
    group_shoulder_half_km=(60.0, 170.0),  # per-crest shoulder half width, mapped from that crest's own dH
    group_shoulder_amp_m=900.0,         # shoulder height in metres (the wide part, below the crest)
    group_skirt_scale=2.10,             # foothill skirt outer edge = shoulder R * this (falls to EXACTLY 0)
    group_skirt_amp_m=280.0,            # skirt height in metres, independent of the shoulder height
    # --- fixed boundary ---
    halo_cells=6,
    # --- optional coarse erosion: finite window exit ---
    erosion_iterations=6, erosion_land_min_m=2.0,
)

# ------------------------------------------------------------------ small helpers
def _params(params=None):
    p = dict(DEFAULTS)
    p.update(params or {})
    if str(p['structure_policy']) not in POLICIES:
        raise ValueError('unknown structure_policy %r (expected one of %s)' % (p['structure_policy'], POLICIES))
    return p


def identity_tags(p):
    """(schema, algorithm) of the generation: v2 for the platform rebuild, the v1 tags for an exact corridor replay."""
    pol = str(p['structure_policy'])
    if pol == 'corridor':
        return SCHEMA_V1, ALGORITHM_V1
    if pol == 'mountain-group':
        return SCHEMA_G, ALGORITHM_G
    return SCHEMA, ALGORITHM


def seeds_for(world_seed):
    return {k: derive_subseed(world_seed, k) for k in SEED_PURPOSES}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False, ensure_ascii=False)


def _smoothstep(x):
    return fr.smoothstep(x)


def grid_from_index(ix0, iz0, nx, nz, first_xz_m, spacing_m):
    """Window grid on the product's own cell centres: window cell (0, 0) is product cell (ix0, iz0)."""
    S = float(spacing_m)
    x0, z0 = float(first_xz_m[0]), float(first_xz_m[1])
    return dict(first_xz_m=(x0 + ix0 * S, z0 + iz0 * S), spacing_m=S, shape=(int(nz), int(nx)),
                rect_m=(x0 + ix0 * S - S / 2, z0 + iz0 * S - S / 2,
                        x0 + (ix0 + nx - 1) * S + S / 2, z0 + (iz0 + nz - 1) * S + S / 2),
                index=(int(ix0), int(iz0)))


def grid_from_rect(rect_m, first_xz_m, spacing_m, shape, *, min_cells=(4, 4)):
    """Snapshot window covering ``rect_m`` = (x0, z0, x1, z1): every cell centre inside it, clipped to the product."""
    x0, z0, x1, z1 = (float(v) for v in rect_m)
    S = float(spacing_m)
    fx, fz = float(first_xz_m[0]), float(first_xz_m[1])
    nzc, nxc = int(shape[0]), int(shape[1])
    ix0 = int(max(0, math.ceil((x0 - fx) / S)))
    ix1 = int(min(nxc - 1, math.floor((x1 - fx) / S)))
    iz0 = int(max(0, math.ceil((z0 - fz) / S)))
    iz1 = int(min(nzc - 1, math.floor((z1 - fz) / S)))
    nx, nz = ix1 - ix0 + 1, iz1 - iz0 + 1
    if nx < min_cells[1] or nz < min_cells[0]:
        raise ValueError('window rect covers %dx%d cells, need at least %dx%d' % (nx, nz, min_cells[1], min_cells[0]))
    g = grid_from_index(ix0, iz0, nx, nz, first_xz_m, S)
    g['requested_rect_m'] = (x0, z0, x1, z1)
    return g


def _dry_fill(a, wet):
    """Nearest-dry sample surface (read-only helper: the array itself is never modified)."""
    from scipy import ndimage
    a = np.asarray(a, np.float64)
    wet = np.asarray(wet, bool)
    if not wet.any() or wet.all():
        return a.copy()
    idx = ndimage.distance_transform_edt(wet, return_distances=False, return_indices=True)
    return a[tuple(idx)]


# ------------------------------------------------------------------ product / skeleton I/O
def load_product(product_dir, expected_identity=None):
    """Validate the frozen product through ``app.map_source.load_source`` and read only the three layers used here.

    The canonical reader owns the identity/hash/axes checks (no second reader is invented); this function only opens
    ``elevation_m``, ``status`` and ``water_surface_m`` (mmap) and never touches the environment layers.
    Returns ``(manifest, arrays, source_info)``.
    """
    from app import map_source
    src = map_source.load_source('world-map-product', product_dir, expected_identity=expected_identity)
    root = Path(product_dir)
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    arrays = {}
    for name in ('elevation_m', 'status', 'water_surface_m'):
        spec = (manifest.get('layers') or {}).get(name)
        if spec is None:
            raise ValueError('product has no %s layer' % name)
        arrays[name] = np.load(root / spec['file'], mmap_mode='r', allow_pickle=False)
    return manifest, arrays, src.info


def source_binding(manifest, info):
    """What this window is bound to: product identity, the skeleton identity it was generated from, and the grid."""
    return dict(product_identity=info.identity, product_schema=info.schema, producer=info.producer,
                world_seed=int(info.world_seed), algorithm_version=info.algorithm_version,
                source_identity=manifest.get('source_identity'), lineage=[str(v) for v in manifest.get('lineage') or []],
                spacing_m=float(info.spacing_m), first_sample_xz_m=[float(v) for v in info.first_sample_xz_m],
                shape_zx=[int(v) for v in info.shape_zx],
                note='the prototype reads a frozen world product; it never writes into it')


def _check_grid(grid, info):
    """Refuse a window whose grid does not sit exactly on the product grid (no resampling, no guessed origin)."""
    if float(grid['spacing_m']) != float(info.spacing_m):
        raise ValueError('window spacing %r differs from the product %r' % (grid['spacing_m'], info.spacing_m))
    nz, nx = info.shape_zx
    ix0, iz0 = grid['index']
    gnz, gnx = grid['shape']
    if ix0 < 0 or iz0 < 0 or ix0 + gnx > nx or iz0 + gnz > nz:
        raise ValueError('window %r+%r falls outside the product grid %r' % ((ix0, iz0), (gnx, gnz), (nx, nz)))
    fx, fz = info.first_sample_xz_m
    if (abs(grid['first_xz_m'][0] - (fx + ix0 * info.spacing_m)) > 1e-6
            or abs(grid['first_xz_m'][1] - (fz + iz0 * info.spacing_m)) > 1e-6):
        raise ValueError('window first cell does not match the product grid origin')
    return True


def load_window(product_dir, grid, *, expected_identity=None, manifest_arrays=None):
    """Cut the window out of a frozen product: old elevation, ocean mask, fixed water (kept lakes, closed sea).

    ``ocean`` = final border-connected ocean (status 3); ``fixed`` also covers kept lake surfaces and closed below-sea
    bed (status 4), so no wet cell is ever rewritten by the prototype. Returns ``win`` (with ``source``) for
    ``apply_window``.
    """
    if manifest_arrays is None:
        manifest, arrays, info = load_product(product_dir, expected_identity)
    else:
        manifest, arrays, info = manifest_arrays
    _check_grid(grid, info)
    ix0, iz0 = grid['index']
    nz, nx = grid['shape']
    sl = (slice(iz0, iz0 + nz), slice(ix0, ix0 + nx))
    before = np.asarray(arrays['elevation_m'])[sl].astype(np.float64)
    status = np.asarray(arrays['status'])[sl]
    oc = status == 3
    closed = status == 4
    surf = (np.asarray(arrays['water_surface_m'])[sl] if 'water_surface_m' in arrays
            else np.full(before.shape, np.nan))
    lake = np.isfinite(surf) & ~oc
    return dict(before_m=np.array(before, np.float64), ocean=oc, lake=lake, closed=closed, fixed=oc | closed | lake,
                status=status, manifest=manifest, grid=grid, source=source_binding(manifest, info))


# ------------------------------------------------------------------ ridge selection (structure, not noise)
def _clip_runs(xz, rect_m):
    """Contiguous runs of vertices inside the window, plus one neighbouring vertex outside at each open end, so a
    corridor continues to the window edge instead of stopping mid-cell."""
    x0, z0, x1, z1 = rect_m
    inside = (xz[:, 0] >= x0) & (xz[:, 0] <= x1) & (xz[:, 1] >= z0) & (xz[:, 1] <= z1)
    runs = []
    if not inside.any():
        return runs
    edges = np.diff(np.concatenate(([0], inside.astype(np.int8), [0])))
    for s, e in zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)):
        runs.append((max(0, int(s) - 1), min(int(len(xz)), int(e) + 1)))
    return runs


def _line_length(xz):
    seg = np.diff(np.asarray(xz, np.float64), axis=0)
    return float(np.hypot(seg[:, 0], seg[:, 1]).sum())


def _direction(xz):
    """Unit chord of the whole saved line (its geographic trend, not a PCA of the window clip)."""
    d = np.asarray(xz[-1], np.float64) - np.asarray(xz[0], np.float64)
    n = float(np.hypot(*d))
    return (d / n, n) if n > 0 else (np.array([1.0, 0.0]), 0.0)


def _coherence(xz, u, tol_deg=45.0):
    """Length-weighted share of segments within ``tol_deg`` of the line chord (1 = a straight-trending chain)."""
    seg = np.diff(np.asarray(xz, np.float64), axis=0)
    L = np.hypot(seg[:, 0], seg[:, 1])
    if L.sum() <= 0:
        return 0.0
    cos = np.abs(seg @ u) / np.maximum(L, 1e-9)
    return float((L * (cos >= math.cos(math.radians(tol_deg)))).sum() / L.sum())


def _belt_geometry(net, belt):
    """Saved belt centre line and half widths of one belt (the wide platform shape that the sculpt replaces)."""
    if belt is None or 'belt_offsets' not in net:
        return None
    o = np.asarray(net['belt_offsets'])
    if int(belt) < 0 or int(belt) + 1 >= len(o):
        return None
    bs, be = int(o[int(belt)]), int(o[int(belt) + 1])
    xz = np.asarray(net['belt_xz_m'], np.float64)[bs:be]
    w = np.asarray(net['belt_half_width_m'], np.float64)[bs:be]
    if len(xz) < 2:
        return None
    return dict(belt=int(belt), xz_m=[[float(a), float(b)] for a, b in xz], half_width_m=[float(v) for v in w],
                half_width_median_m=float(np.median(w)),
                meaning='saved orogen belt centre line + half width: the wide flat platform of the world layer')


def _min_separation(line, others, step=20):
    """Smallest distance between two decimated polylines, metres."""
    a = np.asarray(line, np.float64)[::max(1, int(step))]
    best = float('inf')
    for other in others:
        b = np.asarray(other, np.float64)[::max(1, int(step))]
        best = min(best, float(np.hypot(a[:, None, 0] - b[None, :, 0], a[:, None, 1] - b[None, :, 1]).min()))
    return best


def _decimate(xz, attrs, step_m):
    """Arc-length resample to ~step_m. Returns (xz, idx, attrs) - idx addresses the original vertices, so integer
    per-vertex attributes (``vertex_side``) are taken instead of interpolated."""
    xz = np.asarray(xz, np.float64)
    seg = np.hypot(*np.diff(xz, axis=0).T)
    cum = np.concatenate(([0.0], np.cumsum(seg)))
    if cum[-1] <= step_m:
        idx = np.arange(len(xz), dtype=np.int64)
    else:
        idx = np.unique(np.clip(np.searchsorted(cum, np.arange(0.0, cum[-1], step_m)), 0, len(xz) - 1)).astype(np.int64)
        idx = np.union1d(idx, [len(xz) - 1]).astype(np.int64)
    out = {k: np.interp(cum[idx], cum, np.asarray(v, np.float64)) for k, v in attrs.items()}
    return xz[idx], idx, out


def select_structure(net, rect_m, *, belt=None, world_seed=0, params=None, log=None):
    """Pick 1-2 long level-1 chains inside the window, their parent-linked branches and spurs, and the passes.

    The main direction is the chord of the stored line plus a coherence test on its segments; branches are the lines
    whose ``line_parent`` is a chosen chain, so the saved parent/child graph is kept. Lines of other belts are
    ignored; short cut fragments are rejected instead of being promoted to a main chain.
    """
    p = _params(params)
    o = np.asarray(net['line_offsets'])
    V = np.asarray(net['vertex_xz_m'], np.float64)
    lev = np.asarray(net['line_level'])
    par = np.asarray(net['line_parent'])
    bel = np.asarray(net['line_belt']) if 'line_belt' in net else np.full(len(lev), -1)
    nlines = len(lev)
    runs_of = {li: _clip_runs(V[o[li]:o[li + 1]], rect_m) for li in range(nlines)}
    cand = []
    for li in range(nlines):
        if lev[li] != 1 or not runs_of[li]:
            continue
        if belt is not None and int(bel[li]) != int(belt):
            continue
        xz = V[o[li]:o[li + 1]]
        inlen = float(sum(_line_length(xz[lo:hi]) for lo, hi in runs_of[li]))
        if inlen < float(p['min_main_length_km']) * 1000.0:
            continue
        u, chord = _direction(xz)
        coh = _coherence(xz, u)
        if coh < float(p['min_direction_coherence']) or chord <= 0:
            continue
        cand.append(dict(line=li, length_in_window_m=inlen, chord_m=chord, direction=u, coherence=coh))
    cand.sort(key=lambda c: (-c['length_in_window_m'], c['line']))
    # v2: the belt's level-1 chain is stored as several disconnected segments (19 on the real belt). Taking only the
    # two longest leaves most of the platform without any chain, so every segment of the *same belt* is kept and the
    # segments are narrowed/lowered instead (no fresh straight line is invented). ``corridor`` keeps the v1 rule.
    all_main = bool(p['all_main_chains']) and str(p['structure_policy']) in ('platform-rebuild', 'mountain-group')
    chosen = []
    for c in cand:
        if not all_main and len(chosen) >= int(p['max_main_chains']):
            break
        if not all_main and chosen and _min_separation(V[o[c['line']]:o[c['line'] + 1]],
                                                      [V[o[x['line']]:o[x['line'] + 1]] for x in chosen]
                                                      ) < float(p['min_main_separation_km']) * 1000.0:
            continue
        chosen.append(c)
    if not chosen:
        raise ValueError('no level-1 chain in this window passes the length/coherence test')
    main_idx = [c['line'] for c in chosen]
    branches = [li for li in range(nlines) if lev[li] == 2 and int(par[li]) in main_idx and runs_of[li]]
    spurs = [li for li in range(nlines) if lev[li] == 3 and int(par[li]) in branches and runs_of[li]]
    step_m = float(p['vertex_step_km']) * 1000.0
    entries = []
    w_back = float(p['backbone_width_scale']) if all_main else 1.0
    a_back = float(p['backbone_amp_scale']) if all_main else 1.0
    for li, kind, scale in ([(li, 'main', float(p['main_width_scale']) * w_back) for li in main_idx]
                            + [(li, 'branch', p['branch_width_scale']) for li in branches]
                            + [(li, 'spur', p['spur_width_scale']) for li in spurs]):
        W = net['vertex_width_wide_m'][o[li]:o[li + 1]]
        S_ = net['vertex_width_steep_m'][o[li]:o[li + 1]]
        A = net['vertex_amp'][o[li]:o[li + 1]]
        SD = net['vertex_side'][o[li]:o[li + 1]]
        for lo, hi in runs_of[li]:
            if hi - lo < 2:
                continue
            attrs = dict(wide=W[lo:hi], steep=S_[lo:hi], amp=A[lo:hi])
            xz, idx, att = _decimate(V[o[li]:o[li + 1]][lo:hi], attrs, step_m)
            if len(xz) < 2:
                continue
            entries.append(dict(kind=kind, line=int(li), level=int(lev[li]), parent=int(par[li]), belt=int(bel[li]),
                                xz_m=[[float(a), float(b)] for a, b in xz], vertex=[int(lo), int(hi)],
                                raw_vertices=int(hi - lo), samples=int(len(xz)),
                                half_width_wide_m=[float(v) * float(scale) for v in att['wide']],
                                half_width_steep_m=[float(v) * float(scale) for v in att['steep']],
                                side=[int(v) for v in SD[lo:hi][idx]],
                                amp=[float(v) * (a_back if kind == 'main' else 1.0) for v in att['amp']],
                                length_m=_line_length(xz)))
    if str(p['structure_policy']) == 'mountain-group':
        # Keep parent junctions full-sized; taper only the free end using the original source
        # arclength, so clipping a view does not create a new artificial tip.
        for ent in entries:
            parent = int(ent['parent'])
            if ent['kind'] == 'main' or parent < 0:
                continue
            li = ent['line']
            full = V[o[li]:o[li + 1]]
            pv = V[o[parent]:o[parent + 1]]
            if len(full) < 2 or not len(pv):
                continue
            arc = np.r_[0.0, np.cumsum(np.hypot(*np.diff(full, axis=0).T))]
            start_gap = float(np.min(np.hypot(*(pv - full[0]).T)))
            end_gap = float(np.min(np.hypot(*(pv - full[-1]).T)))
            distance_to_tip = arc[-1] - arc if start_gap <= end_gap else arc
            lo, hi = ent['vertex']
            # nearest original vertices also cover the retained decimated endpoints
            pts = np.asarray(ent['xz_m'])
            ids = np.array([lo + int(np.argmin(np.sum((full[lo:hi] - v) ** 2, axis=1))) for v in pts])
            tip = 0.30 + 0.70 * _smoothstep(distance_to_tip[ids] / max(0.35 * arc[-1], 1.0))
            ent['amp'] = (np.asarray(ent['amp']) * tip).tolist()
            ent['half_width_wide_m'] = (np.asarray(ent['half_width_wide_m']) * np.sqrt(tip)).tolist()
            ent['half_width_steep_m'] = (np.asarray(ent['half_width_steep_m']) * np.sqrt(tip)).tolist()
    passes = []
    if 'pass_xz_m' in net and len(np.asarray(net['pass_xz_m'])):
        x0, z0, x1, z1 = rect_m
        for xz_p, dep, pl in zip(np.asarray(net['pass_xz_m'], np.float64), np.asarray(net['pass_depth'], np.float64),
                                 np.asarray(net['pass_line'])):
            if int(pl) not in (main_idx + branches):
                continue
            if not (x0 <= xz_p[0] <= x1 and z0 <= xz_p[1] <= z1):
                continue
            passes.append(dict(xz_m=[float(xz_p[0]), float(xz_p[1])], depth=float(dep), line=int(pl), source='network'))
    meta = dict(belt=None if belt is None else int(belt), main_lines=[int(i) for i in main_idx],
                belt_geometry=_belt_geometry(net, belt),
                branch_lines=[int(i) for i in branches], spur_lines=[int(i) for i in spurs],
                candidates=[dict(line=int(c['line']), length_in_window_km=c['length_in_window_m'] / 1e3,
                                 chord_km=c['chord_m'] / 1e3, direction=[float(v) for v in c['direction']],
                                 coherence=float(c['coherence'])) for c in cand],
                main_direction=[float(v) for v in chosen[0]['direction']],
                main_coherence=float(chosen[0]['coherence']), vertex_step_km=float(p['vertex_step_km']),
                selection='level-1 chord direction + segment coherence; branches through line_parent; other belts ignored')
    structure = dict(main=[e for e in entries if e['kind'] == 'main'],
                     branches=[e for e in entries if e['kind'] == 'branch'],
                     spurs=[e for e in entries if e['kind'] == 'spur'], passes=passes, meta=meta)
    if log:
        log(dict(stage='select_structure', main_lines=meta['main_lines'], main_direction=meta['main_direction'],
                 main_coherence=meta['main_coherence'], branches=len(structure['branches']),
                 spurs=len(structure['spurs']), passes=len(passes)))
    return structure


# ------------------------------------------------------------------ corridor fields (one pass over segments)
def _segments_of(entries, keep=('main', 'branch', 'spur')):
    """Flat segment stream with per-segment attributes; a segment carries its kind so one pass fills every field."""
    out = []
    for kind in keep:
        for e in entries[KIND_KEYS[kind]]:
            xz = np.asarray(e['xz_m'], np.float64)
            ww = np.asarray(e['half_width_wide_m'], np.float64)
            ws = np.asarray(e['half_width_steep_m'], np.float64)
            sd = np.asarray(e['side'], np.float64)
            am = np.asarray(e['amp'], np.float64)
            for j in range(len(xz) - 1):
                out.append((kind, int(e['line']), float(xz[j, 0]), float(xz[j, 1]),
                            float(xz[j + 1, 0]), float(xz[j + 1, 1]),
                            float(ww[j]), float(ww[j + 1]), float(ws[j]), float(ws[j + 1]),
                            float(sd[j]), float(am[j]), float(am[j + 1])))
    return out


def _group_half_width(amplitude, p):
    """Half width in metres, constrained by a declared relative-relief target, not absolute elevation.

    This is a construction target; final overlapping shoulders, incision and the frozen boundary can change
    the measured slope. When the configured width and slope intervals conflict, the width bound wins.
    """
    amp = np.clip(np.asarray(amplitude, np.float64), 0.0, 1.0)
    rlo, rhi = np.asarray(p['group_shoulder_half_km'], np.float64) * 1000.0
    preferred = rlo + (rhi - rlo) * amp
    dh = np.clip(amp * float(p['peak_relief_m']), 300.0, float(p['group_relief_range_m'][1]))
    slo, shi = p['group_slope_range']
    lower = np.maximum(rlo, dh / max(float(shi), 1e-6))
    upper = np.minimum(rhi, dh / max(float(slo), 1e-6))
    return np.where(lower <= upper, np.clip(preferred, lower, upper), np.clip(preferred, rlo, rhi))


def corridor_fields(structure, grid, wx, wz, params=None, *, log=None, width_mod=None):
    """Envelope of every chain kind, the explicit support, and the distance to the main crest line.

    ``envelope_<kind>`` = max over segments of amp * clip(1 - d/w, 0, 1)**profile_exp with the asymmetric width
    (wide landward / steep seaward side from ``vertex_side``) - a tent profile, never a Gaussian. Each segment only
    touches a local sub-rectangle of the window (and no periodic wrap: the window is finite).
    """
    p = _params(params)
    nz, nx = grid['shape']
    S = float(grid['spacing_m'])
    x0, z0 = float(grid['first_xz_m'][0]), float(grid['first_xz_m'][1])
    X = x0 + np.arange(nx) * S
    Z = z0 + np.arange(nz) * S
    exp = float(p['profile_exp'])
    env = {k: np.zeros((nz, nx), np.float64) for k in ('main', 'branch', 'spur')}
    sup = np.zeros((nz, nx), np.float64)
    dmain = np.full((nz, nx), np.inf, np.float64)
    # v4/mountain-group: ONE extra field pair, used only when a width modulation is in play (the rebuild family).
    # ``envelope_shoulder`` is the wide *shoulder* a crest carries: its half width R is mapped from that crest's own
    # amplitude (the dH proxy), so a high crest gets a wider shoulder - a spatial width coupling, not an amplitude
    # statistic. ``envelope_skirt`` is the still wider foothill band; both are 0..1 and fall to exactly 0 at R.
    sh_enabled = width_mod is not None and str(p['structure_policy']) == 'mountain-group'
    sh_field = np.zeros((nz, nx), np.float64)
    sk_field = np.zeros((nz, nx), np.float64)
    sh_lo, sh_hi = (float(v) for v in p['group_shoulder_half_km'])
    segs = _segments_of(structure)
    # v3: the sub-rectangle must cover the WIDEST envelope this segment can actually reach, not the unmodulated width.
    # The tent is drawn with ``w * clip(chain_width_gain * (1 + width_mod), .30, 3.20)``; the largest multiplier is
    # therefore ``gain * (1 + width_var)`` (1.85 * 1.45 with the accepted defaults). Sizing the sub-rect from the bare
    # width truncated the modulated flanks along a straight sub-rect edge - exactly the cut/straight edges at the
    # outline. ``corridor`` (width_mod=None) has no width modulation and keeps its old reach.
    if width_mod is None:
        env_mult = 1.0
    else:
        env_mult = float(np.clip(float(p['chain_width_gain']) * (1.0 + float(p['width_var'])), 0.30, 3.20))
    skirt_scale = float(p['group_skirt_scale'])
    # the shoulder must fit in the sub-rectangle too, otherwise the wide part is cut off at its edge
    sh_reach = sh_hi * 1000.0 * max(skirt_scale, 1.0)
    warp_reach = 1.5 * float(p['warp_amp_km']) * 1000.0
    for (kind, li, ax, az, bx, bz, ww0, ww1, ws0, ws1, sd, a0, a1) in segs:
        dx, dz = bx - ax, bz - az
        l2 = max(dx * dx + dz * dz, 1e-9)
        wmax = max(ww0, ww1, ws0, ws1)
        sup_reach = wmax * max(float(p['support_width_scale']), float(p['branch_support_scale'])) \
            + max(float(p['support_width_extra_km']), float(p['branch_support_extra_km'])) * 1000.0
        reach = max(wmax * env_mult, sh_reach) + warp_reach
        reach_s = sup_reach + warp_reach
        i0 = int(max(0, math.floor((min(ax, bx) - max(reach, reach_s) - x0) / S)))
        i1 = int(min(nx - 1, math.ceil((max(ax, bx) + max(reach, reach_s) - x0) / S)))
        k0 = int(max(0, math.floor((min(az, bz) - max(reach, reach_s) - z0) / S)))
        k1 = int(min(nz - 1, math.ceil((max(az, bz) + max(reach, reach_s) - z0) / S)))
        if i1 < i0 or k1 < k0:
            continue
        sub = (slice(k0, k1 + 1), slice(i0, i1 + 1))
        px = X[None, i0:i1 + 1] + wx[sub]
        pz = Z[k0:k1 + 1, None] + wz[sub]
        t = np.clip(((px - ax) * dx + (pz - az) * dz) / l2, 0.0, 1.0)
        d = np.hypot(px - (ax + t * dx), pz - (az + t * dz))
        cross = dx * (pz - az) - dz * (px - ax)
        wide = cross * sd >= 0
        w = np.where(wide, ww0 + (ww1 - ww0) * t, ws0 + (ws1 - ws0) * t)
        a = a0 + (a1 - a0) * t
        # ``width_mod`` only moves the tent's own outer edge (where the envelope reaches 0); the support/domain
        # below still uses the unmodulated width, so the permission mask never shrinks with the outline.
        w_env = w if width_mod is None else w * np.clip(float(p['chain_width_gain']) * (1.0 + width_mod[sub]),
                                                    0.30, 3.20)
        x = np.clip(1.0 - d / np.maximum(w_env, 1.0), 0.0, 1.0)
        v = a * np.power(x, exp)
        env[kind][sub] = np.maximum(env[kind][sub], v)
        if sh_enabled and kind in ('main', 'branch'):
            # R from THIS crest's own amplitude: a tall crest carries a broad shoulder, a low spur a narrow one
            R_sh = _group_half_width(a, p)  # per-pixel along-segment interpolation, relative-height target / slope range
            sh_field[sub] = np.maximum(sh_field[sub], np.power(np.clip(1.0 - d / np.maximum(R_sh, 1.0), 0.0, 1.0), 0.5))
            R_sk = R_sh * max(skirt_scale, 1.0)
            sk_field[sub] = np.maximum(sk_field[sub], np.power(np.clip(1.0 - d / np.maximum(R_sk, 1.0), 0.0, 1.0), 1.6))
        if kind in ('main', 'branch'):
            scale = float(p['support_width_scale'] if kind == 'main' else p['branch_support_scale'])
            extra = float(p['support_width_extra_km'] if kind == 'main' else p['branch_support_extra_km']) * 1000.0
            xw = np.clip(1.0 - d / np.maximum(w * scale + extra, 1.0), 0.0, 1.0)
            sup[sub] = np.maximum(sup[sub], xw)
        if kind == 'main':
            dmain[sub] = np.minimum(dmain[sub], d)
    support = np.power(np.clip(sup, 0.0, 1.0), float(p['support_exp']))
    if log:
        log(dict(stage='corridors', segments=len(segs), support_cells=int((support > 0).sum())))
    return dict(envelope_main=env['main'].astype(np.float32), envelope_branch=env['branch'].astype(np.float32),
                envelope_spur=env['spur'].astype(np.float32), support=support.astype(np.float32),
                dist_main_m=np.where(np.isfinite(dmain), dmain, np.inf).astype(np.float32), segments=len(segs),
                envelope_shoulder=sh_field.astype(np.float32), envelope_skirt=sk_field.astype(np.float32))


def crest_factor(grid, wx, wz, params=None, seed=0):
    """Ridged multifractal crest multiplier on the warped coordinates (no Gaussian, no constant crest per line)."""
    p = _params(params)
    nz, nx = grid['shape']
    S = float(grid['spacing_m'])
    X = grid['first_xz_m'][0] + np.arange(nx) * S
    Z = grid['first_xz_m'][1] + np.arange(nz) * S
    px = (X[None, :] + wx).astype(np.float64)
    pz = (Z[:, None] + wz).astype(np.float64)
    wlk = p['detail_wavelengths_km'] if str(p['structure_policy']) in ('platform-rebuild', 'mountain-group') else p['ridged_wavelengths_km']
    rwl = [v * 1000.0 for v in wlk]
    R = np.asarray(rn.ridged_multifractal(px, pz, int(seed), rwl, float(p['ridged_h']), float(p['ridged_gain']),
                                          float(p['ridged_offset'])), np.float64)
    R = np.nan_to_num(R, nan=0.0, posinf=0.0, neginf=0.0)
    lo, hi = np.percentile(R, [2.0, 98.0])
    Rf = np.clip((R - lo) / max(hi - lo, 1e-9), 0.0, 1.0)
    return (float(p['crest_floor']) + float(p['crest_gain']) * Rf).astype(np.float32)


def _window_warp(grid, params=None, world_seed=0):
    p = _params(params)
    seeds = seeds_for(world_seed)
    amp = float(p['warp_amp_km']) * 1000.0
    wl = [v * 1000.0 for v in p['warp_wavelengths_km']]
    sd = seeds['mountain-sculpt/warp']
    nz, nx = grid['shape']
    S = float(grid['spacing_m'])
    first = grid['first_xz_m']
    wx = fr.blocked_grid((nz, nx), first, S, lambda x, z: amp * fr.fbm_xz(x, z, sd, wl, (0.65, 0.35)))
    wz = fr.blocked_grid((nz, nx), first, S,
                        lambda x, z: amp * fr.fbm_xz(x + 51413.0, z - 23071.0, sd, wl, (0.65, 0.35)))
    return wx.astype(np.float32), wz.astype(np.float32)


# ---------------------------------------------------- safe domain / rebuilt base (v2 platform rebuild)
def _field01(grid, wx, wz, seed, wavelengths_km, weights=(0.55, 0.30, 0.15)):
    """Coordinate-addressed fbm on the warped grid, normalised by its own 2/98 percentile to [0, 1]."""
    nz, nx = grid['shape']
    S = float(grid['spacing_m'])
    X = grid['first_xz_m'][0] + np.arange(nx) * S
    Z = grid['first_xz_m'][1] + np.arange(nz) * S
    wl = [float(v) * 1000.0 for v in wavelengths_km]
    F = np.empty((nz, nx), np.float64)
    for r0 in range(0, nz, 128):
        r1 = min(r0 + 128, nz)
        px = X[None, :] + np.asarray(wx, np.float64)[r0:r1]
        pz = Z[r0:r1, None] + np.asarray(wz, np.float64)[r0:r1]
        F[r0:r1] = fr.fbm_xz(px, pz, int(seed), wl, weights)
    lo, hi = np.percentile(F, [2.0, 98.0])
    return np.clip((F - lo) / max(hi - lo, 1e-9), 0.0, 1.0)


def _sample_at(grid, arr, xz, step=1):
    """Values of ``arr`` at decimated polyline vertices (the grid's own cells; nothing is interpolated)."""
    nz, nx = grid['shape']
    S = float(grid['spacing_m'])
    x0, z0 = float(grid['first_xz_m'][0]), float(grid['first_xz_m'][1])
    out = []
    for p in np.asarray(xz, np.float64)[::max(1, int(step))]:
        ix = int(round((p[0] - x0) / S))
        iz = int(round((p[1] - z0) / S))
        if 0 <= ix < nx and 0 <= iz < nz:
            out.append(float(arr[iz, ix]))
    return out


def _edge_taper(grid, km, cells_min=1):
    """Wide smoothstep from the window border inwards (metres-based, not a few cells): the outermost ring is 0, so the
    kept old surface at the border is met along a long ramp instead of a straight wall."""
    nz, nx = grid['shape']
    S = float(grid['spacing_m'])
    hav = max(float(km) * 1000.0, 1e-9)
    iz = np.arange(nz)[:, None]
    ix = np.arange(nx)[None, :]
    d = np.minimum(np.minimum(iz, nz - 1 - iz), np.minimum(ix, nx - 1 - ix)).astype(np.float64) * S
    w = _smoothstep(np.clip(d / hav, 0.0, 1.0))
    ring = max(1, int(cells_min))
    w[:ring, :] = w[-ring:, :] = 0.0
    w[:, :ring] = w[:, -ring:] = 0.0
    return w.astype(np.float64)


def _soft_cap(a, cap, soft):
    """Asymptotic cap: values above ``cap`` approach it instead of being clipped flat (no artificial summit plateau)."""
    a = np.asarray(a, np.float64)
    # Smooth minimum: strictly monotone, approaching cap from below. The former above-cap
    # branch decreased with height and folded the summit back down, leaving artificial bright rims.
    s = max(float(soft), 1e-6)
    return float(cap) - s * np.logaddexp(0.0, (float(cap) - a) / s)


def belt_domain(structure, grid, wx, wz, params=None, *, world_seed=0):
    """The **safe domain**: everywhere the surface is *allowed* to change (v2).

    It is the saved belt's own wide band (half width x ``belt_support_scale``) grown outward by
    ``belt_support_extra_km`` with a smoothstep - plus whatever the selected corridor support covers (unioned by the
    caller). It is deliberately a permission mask, not a mountain outline: inside it the old platform may be lowered
    to foothill or valley, so the rebuilt massif edge can sit *inside* the old platform edge.
    Also returns the low-frequency fields that shape the outline: ``width_mod`` (fractional chain width change),
    ``fringe`` (where thin fringes are cut back) and ``piedmont`` (foothill amplitude modulation).
    """
    p = _params(params)
    seeds = seeds_for(world_seed)
    nz, nx = grid['shape']
    S = float(grid['spacing_m'])
    X = grid['first_xz_m'][0] + np.arange(nx) * S
    Z = grid['first_xz_m'][1] + np.arange(nz) * S
    scale = float(p['belt_support_scale'])
    extra = float(p['belt_support_extra_km']) * 1000.0
    band = np.zeros((nz, nx), np.float64)
    bg = (structure.get('meta') or {}).get('belt_geometry')
    # World-stage periodic images are disjoint pieces, never joined across the finite map.
    parts = bg.get('parts', [bg]) if bg else []
    for part in parts:
        if len(part.get('xz_m') or []) < 2 or len(part.get('half_width_m') or []) < 2:
            continue
        xz = np.asarray(part['xz_m'], np.float64)
        hw = np.asarray(part['half_width_m'], np.float64)
        reach = float(hw.max()) * scale + extra + 2.0 * S
        for j in range(len(xz) - 1):
            ax, az = float(xz[j, 0]), float(xz[j, 1])
            bx, bz = float(xz[j + 1, 0]), float(xz[j + 1, 1])
            i0 = int(max(0, math.floor((min(ax, bx) - reach - X[0]) / S)))
            i1 = int(min(nx - 1, math.ceil((max(ax, bx) + reach - X[0]) / S)))
            k0 = int(max(0, math.floor((min(az, bz) - reach - Z[0]) / S)))
            k1 = int(min(nz - 1, math.ceil((max(az, bz) + reach - Z[0]) / S)))
            if i1 < i0 or k1 < k0:
                continue
            sub = (slice(k0, k1 + 1), slice(i0, i1 + 1))
            px = X[None, i0:i1 + 1]
            pz = Z[k0:k1 + 1, None]
            dx, dz = bx - ax, bz - az
            l2 = max(dx * dx + dz * dz, 1e-9)
            t = np.clip(((px - ax) * dx + (pz - az) * dz) / l2, 0.0, 1.0)
            d = np.hypot(px - (ax + t * dx), pz - (az + t * dz))
            full = (hw[j] + (hw[j + 1] - hw[j]) * t) * scale
            ramp = _smoothstep(np.clip((full + extra - d) / max(extra, 1e-9), 0.0, 1.0))
            band[sub] = np.maximum(band[sub], np.where(d <= full, 1.0, ramp))
    width_mod = float(p['width_var']) * (2.0 * _field01(grid, wx, wz, seeds['mountain-sculpt/width'],
                                                         p['width_var_wavelengths_km']) - 1.0)
    fringe = _field01(grid, wx, wz, seeds['mountain-sculpt/fringe'], p['fringe_wavelengths_km'])
    pied = _field01(grid, wx, wz, seeds['mountain-sculpt/piedmont'], p['piedmont_wavelengths_km'])
    along = _field01(grid, wx, wz, seeds['mountain-sculpt/crest'], p['along_amp_wavelengths_km'])
    amp_mod = 1.0 - float(p['along_amp_var']) * (1.0 - along)
    return dict(belt_band=band.astype(np.float64), width_mod=width_mod.astype(np.float64),
                fringe=fringe.astype(np.float64), piedmont=pied.astype(np.float64),
                amp_mod=amp_mod.astype(np.float64),
                support_scale=scale, extra_m=extra, has_belt=bool(band.any()),
                meaning='safe domain = saved belt wide band x scale grown outward by extra_km (a permission mask); '
                        'the mountain outline is rebuilt separately inside it')


def rebuilt_base(grid, before_m, fixed, params=None, *, world_seed=0):
    """Low base of the rebuilt massif: the existing lowland ramp (``ridge_network.lowland_base``), never the old
    platform. The old value is kept only on fixed water so nothing wet is ever rewritten."""
    p = _params(params)
    seeds = seeds_for(world_seed)
    before = np.asarray(before_m, np.float64)
    land = (~np.asarray(fixed, bool)) & (before > 0.0)
    base = np.asarray(rn.lowland_base(land, float(grid['spacing_m']), int(seeds['mountain-sculpt/floor']) % (1 << 31),
                                      start_m=float(p['base_start_m']), rise_m=float(p['base_rise_m']),
                                      plateau_km=float(p['base_plateau_km']), relief_m=float(p['base_relief_m']),
                                      cap_m=float(p['base_cap_m'])), np.float64)
    return np.where(land, base, before)


# ------------------------------------------------------------------ valleys, basins, passes
def _smooth_field(a, cells):
    from scipy import ndimage
    if cells <= 1:
        return np.asarray(a, np.float64).copy()
    return ndimage.uniform_filter(np.asarray(a, np.float64), size=int(cells), mode='nearest')


def floor_and_basins(grid, before_m, fixed, fields, params=None, *, world_seed=0, log=None, base_m=None):
    """Flat valley floor between the chains plus a few intramontane basins (finite-width flat bottom).

    ``floor_m`` is the lowered base of the old wide platform: a box mean (never a Gaussian) of the old dry surface
    inside the support, clipped to [floor_min_m, floor_max_m]. ``valley_mask`` marks where the sculpted surface is
    that flat base, ``basin_mask`` where it is lowered further by ``basin_depth_m``.
    """
    p = _params(params)
    seeds = seeds_for(world_seed)
    nz, nx = grid['shape']
    S = float(grid['spacing_m'])
    X = grid['first_xz_m'][0] + np.arange(nx) * S
    Z = grid['first_xz_m'][1] + np.arange(nz) * S
    sup = np.asarray(fields['support'], np.float64)
    dry = _dry_fill(before_m, fixed | (np.asarray(before_m) <= 0.0))
    cells = int(max(1, round(2.0 * float(p['floor_radius_km']) * 1000.0 / S)))
    if base_m is not None:
        # v2: the floor IS the rebuilt low base (no box mean clipped to [floor_min, floor_max] - that cap alone
        # would turn every valley into a 2200 m table).
        floor_m = np.asarray(base_m, np.float64).copy()
    else:
        base = _smooth_field(dry, cells)
        floor_m = np.clip(base, float(p['floor_min_m']), float(p['floor_max_m']))
    dmain = np.asarray(fields['dist_main_m'], np.float64)
    floor_zone = (dmain > float(p['floor_radius_km']) * 500.0) & np.isfinite(dmain) & (sup > 0.0)
    # intramontane basins: deterministic centres in the floor zone between chains, kept apart
    rng = np.random.default_rng([seeds['mountain-sculpt/basins'], 1])
    score = np.where(floor_zone, 1.0 - np.asarray(fields['envelope_main'], np.float64), -1.0)
    order = np.argsort(-(np.round(score.ravel(), 9) * 1.0) - 1e-9 * rng.random(score.size))
    Rb = float(p['basin_radius_km']) * 1000.0
    core = float(p['basin_core_frac'])
    sep = float(p['basin_separation_km']) * 1000.0
    edge_cells = float(p['basin_edge_km']) * 1000.0 / S
    chosen, taken = [], []
    for idx in order:
        if len(chosen) >= int(p['basins_max']):
            break
        iz, ix = divmod(int(idx), nx)
        if score[iz, ix] <= 0.0:
            continue
        if fixed[iz, ix] or float(before_m[iz, ix]) <= 0.0:
            continue                    # never put a basin centre on fixed water or below sea level
        if sup[iz, ix] < float(p['basin_min_support']):
            continue                    # the disc must sit where the blend weight is high enough to form its bed
        if ix < edge_cells or iz < edge_cells or (nx - 1 - ix) < edge_cells or (nz - 1 - iz) < edge_cells:
            continue
        xc, zc = X[ix], Z[iz]
        envv = float(np.asarray(fields['envelope_main'], np.float64)[iz, ix])
        if envv > float(p['basin_max_env']):
            continue
        if any(np.hypot(xc - x, zc - z) < sep for x, z in taken):
            continue
        taken.append((xc, zc))
        chosen.append(dict(xz_m=[float(xc), float(zc)], cell=[int(ix), int(iz)], env=envv,
                           floor_m=float(floor_m[iz, ix]), radius_km=float(p['basin_radius_km'])))
    # --- basin discs: a finite-width flat bottom at a defined target bed (never 0 as a stand-in for the bed) ---
    basin = np.zeros((nz, nx), np.float64)
    bed_basin = np.full((nz, nx), np.nan)
    for b in chosen:
        xc, zc = b['xz_m']
        r = np.hypot(X[None, :] - xc, Z[:, None] - zc)
        w = np.where(r <= Rb * core, 1.0, 0.0)
        outer = (r > Rb * core) & (r <= Rb)
        w = np.where(outer, 1.0 - _smoothstep((r - Rb * core) / max(Rb * (1.0 - core), 1.0)), w)
        keep = w > 0.0
        basin[keep] = np.maximum(basin[keep], w[keep])
        target = float(floor_m[b['cell'][1], b['cell'][0]]) - float(p['basin_depth_m'])
        b['target_m'] = target
        bed_basin[keep] = np.where(np.isnan(bed_basin[keep]), target, np.minimum(bed_basin[keep], target))
    # --- connector valleys: their own local bed (the valley floor, with a shallow incision that fades out along
    # the path), so nothing is ever mixed toward 0 m outside the discs ---
    conn = np.zeros((nz, nx), np.float64)
    bed_conn = np.full((nz, nx), np.nan)
    hw = float(p['connector_half_km']) * 1000.0
    drop = float(p['connector_drop_m'])
    for b in chosen:
        pts = _connector(b, floor_m, grid, int(max(2, round(float(p['connector_len_km']) * 1000.0 / S))))
        b['connector_xz_m'] = pts
        for j in range(len(pts) - 1):
            (ax, az), (bx, bz) = pts[j], pts[j + 1]
            dx, dz = bx - ax, bz - az
            l2 = max(dx * dx + dz * dz, 1e-9)
            t = np.clip(((X[None, :] - ax) * dx + (Z[:, None] - az) * dz) / l2, 0.0, 1.0)
            dd = np.hypot(X[None, :] - (ax + t * dx), Z[:, None] - (az + t * dz))
            c = 1.0 - _smoothstep((dd - hw) / max(hw, 1.0))
            c = np.where(dd <= 2.0 * hw, c, 0.0)
            # the wedge is deepest at the basin end and fades to the valley floor at the far end
            wedge = drop * (1.0 - (j + t) / max(len(pts) - 1, 1))
            tgt = floor_m - wedge
            conn = np.maximum(conn, c)
            better = c > 0.0
            bed_conn[better] = np.where(np.isnan(bed_conn[better]), tgt[better],
                                        np.minimum(bed_conn[better], tgt[better]))
    w_b = basin
    w_c = 0.75 * conn * (1.0 - basin)
    total = w_b + w_c
    bed = np.where(np.isnan(bed_basin), np.nan, bed_basin)
    bed = np.where(np.isnan(bed), bed_conn, np.where(np.isnan(bed_conn), bed, np.minimum(bed, bed_conn)))
    both = (w_b > 0.0) & (w_c > 0.0) & np.isfinite(bed_basin) & np.isfinite(bed_conn)
    bed = np.where(both, (bed_basin * w_b + bed_conn * w_c) / np.maximum(total, 1e-9), bed)
    basin_all = np.maximum(w_b, w_c).astype(np.float32)
    basin_bed = np.where(basin_all > 0.0, np.nan_to_num(bed, nan=0.0), 0.0)
    if not np.isfinite(bed[basin_all > 0.0]).all():
        raise ValueError('a basin/connector cell has no defined target bed')
    if log:
        log(dict(stage='floor_basins', basins=len(chosen), floor_zone_cells=int(floor_zone.sum()),
                 basin_cells=int((basin > 0).sum()), connector_cells=int((conn > 0).sum())))
    return dict(floor_m=floor_m, floor_zone=floor_zone, basin_mask=basin_all, basin_floor_m=basin_bed,
                basins=chosen, smooth_cells=cells)


def _connector(basin, floor_m, grid, steps):
    """Short polyline from a basin centre down the floor field (greedy 4-neighbour descent, deterministic)."""
    nz, nx = grid['shape']
    S = float(grid['spacing_m'])
    X = grid['first_xz_m'][0] + np.arange(nx) * S
    Z = grid['first_xz_m'][1] + np.arange(nz) * S
    ix, iz = int(basin['cell'][0]), int(basin['cell'][1])
    pts = [[float(X[ix]), float(Z[iz])]]
    cur = (iz, ix)
    seen = {cur}
    for _ in range(steps):
        z, x = cur
        if z <= 1 or x <= 1 or z >= nz - 2 or x >= nx - 2:
            break
        best, bestv = None, None
        for dz, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nxt = (z + dz, x + dx)
            if nxt in seen:
                continue
            v = float(floor_m[nxt])
            if bestv is None or v < bestv:
                best, bestv = nxt, v
        if best is None:
            break
        seen.add(best)
        cur = best
        pts.append([float(X[cur[1]]), float(Z[cur[0]])])
    return pts if len(pts) >= 2 else []


def pass_factor(passes, grid, wx, wz, params=None):
    """Multiplicative crest lowering at passes: 1 - depth * cosine bump (a cosine bump, never a Gaussian)."""
    p = _params(params)
    nz, nx = grid['shape']
    S = float(grid['spacing_m'])
    X = grid['first_xz_m'][0] + np.arange(nx) * S
    Z = grid['first_xz_m'][1] + np.arange(nz) * S
    f = np.ones((nz, nx), np.float64)
    half_default = 0.5 * (float(p['pass_half_km'][0]) + float(p['pass_half_km'][1])) * 1000.0
    for q in passes:
        xc, zc = q['xz_m']
        half = float(q.get('half_m') or half_default)
        r = np.hypot((X[None, :] + wx) - xc, (Z[:, None] + wz) - zc)
        bump = 0.5 * (1.0 + np.cos(np.pi * np.clip(r / half, 0.0, 1.0)))
        depth = min(float(q['depth']) * (float(p['pass_depth_scale']) if q.get('source') == 'network' else 1.0),
                    float(p['pass_depth_max']))
        f = np.minimum(f, 1.0 - depth * bump)
    return f.astype(np.float32)


def add_passes(structure, params=None, *, world_seed=0):
    """The network's own passes (depth softened) plus deterministic saddles so a long chain has a few gates."""
    p = _params(params)
    seeds = seeds_for(world_seed)
    rng = np.random.default_rng([seeds['mountain-sculpt/passes'], 1])
    out = [dict(q) for q in (structure.get('passes') or [])]
    for e in structure['main']:
        xz = np.asarray(e['xz_m'], np.float64)
        if len(xz) < 4:
            continue
        seg = np.hypot(*np.diff(xz, axis=0).T)
        cum = np.concatenate(([0.0], np.cumsum(seg)))
        have = sum(1 for q in out if q.get('source') == 'network' and q.get('line') == e['line'])
        for k in range(max(0, int(p['min_passes']) - have)):
            target = float(p['pass_spacing_km']) * 1000.0 * (k + 1.0)
            if target >= cum[-1] - 1.0:
                break
            j = int(np.clip(np.searchsorted(cum, target), 1, len(xz) - 2))
            out.append(dict(xz_m=[float(xz[j, 0]), float(xz[j, 1])], depth=float(rng.uniform(*p['pass_depth'])),
                            half_m=float(rng.uniform(*p['pass_half_km'])) * 1000.0, line=int(e['line']),
                            source='sculpt'))
    return out


# ------------------------------------------------------------------ surface assembly
def _peak_scale(envelope, crest, passf, floor_m, before_m, support, dry, p):
    """Amplitude that keeps the peak magnitude of the window: the new crest reaches the old 99th percentile over dry
    land inside the support, so the chain is narrow and structured but not flattened."""
    r = np.asarray(envelope, np.float64) * np.asarray(crest, np.float64) * np.asarray(passf, np.float64)
    zone = np.asarray(support, np.float64) > 0.05
    zone &= dry
    if not zone.any():
        zone = np.ones_like(r, bool)
    q = float(np.percentile(np.asarray(before_m, np.float64)[zone], 99.0))
    ref_floor = float(np.median(np.asarray(floor_m, np.float64)[zone]))
    top = float(r[zone].max())
    if top <= 1e-6:
        raise ValueError('empty crest envelope inside the support')
    return max((q - ref_floor) / top, 1.0)


def _halo(shape, cells):
    """Smoothstep from the window border inwards; the outermost ring is exactly 0 (bitwise old values kept)."""
    nz, nx = shape
    iz = np.arange(nz)[:, None]
    ix = np.arange(nx)[None, :]
    d = np.minimum(np.minimum(iz, nz - 1 - iz), np.minimum(ix, nx - 1 - ix)).astype(np.float64)
    if cells <= 0:
        return np.ones(shape, np.float32)
    w = _smoothstep(d / float(cells))
    w[0, :] = w[-1, :] = 0.0
    w[:, 0] = w[:, -1] = 0.0
    return w.astype(np.float32)


def _erode_window(after_m, fixed, ocean, grid, params=None, *, world_seed=0, log=None):
    """Optional coarse stream-power erosion on the existing irregular graph (``fast_relief.erode``, never D8).

    The window border and every fixed water cell are finite exits of this *local* routing; the window is not a closed
    catchment of the world, and hydrology (lakes/rivers) is not rebuilt.
    """
    from . import graph_hydro as gh
    p = _params(params)
    nz, nx = grid['shape']
    S = float(grid['spacing_m'])
    pe = dict(fr.DEFAULTS_V2)
    pe.update(spacing_m=S, erosion_iterations=int(p['erosion_iterations']), land_min_m=float(p['erosion_land_min_m']),
              diffusion=0.0, hillslope='talus')
    mesh_seed = derive_subseed(world_seed, 'mountain-sculpt/mesh')
    t0 = time.perf_counter()
    mesh = gh.build_graph((nz, nx), grid['first_xz_m'], S, mesh_seed)
    outlets = np.asarray(ocean, bool).copy()
    outlets |= np.asarray(fixed, bool)
    outlets[0, :] = outlets[-1, :] = True
    outlets[:, 0] = outlets[:, -1] = True
    out, incised = fr.erode(np.asarray(after_m, np.float64), outlets, mesh, outlets, pe, log)
    if log:
        log(dict(stage='erode', iterations=int(p['erosion_iterations']), mesh_s=round(time.perf_counter() - t0, 2),
                 mean_incision_m=float(np.mean(incised)) if incised else 0.0))
    return out.astype(np.float64)


def _rebuilt_excess(grid, structure, before, dry, support, env, ridge_m, floor_m, fields, dom, p, log=None):
    """v2: rebuild the massif excess instead of blending texture onto the old platform.

    ``new = base + keep*old_excess + piedmont + chain`` on dry land inside the safe domain:

    * ``base`` is the rebuilt low base (``floor_m``), so wherever the chain envelope is small the old wide platform
      becomes foothill/valley - the old platform top is *not* carried over.
    * ``keep`` is a **small, direction-modulated share** of the old excess (``keep_old_excess``), strongest under the
      rebuilt chain and zero on the flanks: the massif sits on the old trend and its outline still retreats.
    * ``piedmont`` is low-frequency (>= 90 km) relief rolling on the flanks, damped under the crest.
    * ``chain`` is the backbone (all belt level-1 segments, narrowed) x tent envelope x ridged crest x passes, with its
      width varied by ``width_mod`` (see ``corridor_fields``) and its whole cross-section cut by the low-frequency
      ``fringe`` field. Its amplitude is calibrated **after** those modulations, on the selected main lines, so a cut
      can never delete the chain; the gain touches the chain only, so valleys are not lifted with the crests.
    * ``_soft_cap`` at the old peak level: summits approach the old peak asymptotically instead of a flat table.
    """
    base = np.asarray(floor_m, np.float64)
    chain = np.asarray(ridge_m, np.float64)
    e = np.asarray(env, np.float64)
    top = float(e.max()) if e.size else 0.0
    en = np.clip(e / max(top, 1e-9), 0.0, 1.0)
    thr = max(float(p['fringe_level']), 1e-6)
    fringe = np.asarray(dom['fringe'], np.float64) if dom is not None else np.zeros_like(e)
    weak = _smoothstep(np.clip((thr - en) / thr, 0.0, 1.0))
    # the cut acts across the whole cross-section (weakly at the crest, fully on the thin flanks), so a
    # low-frequency fringe field makes a whole section fall away - that is what displaces the outline, not just
    # texture added inside a fixed mask.
    cut_w = np.clip(float(p['fringe_cut']) * fringe * (float(p['fringe_core_share']) + (1.0 - float(p['fringe_core_share'])) * weak),
                    0.0, 1.0)
    chain = chain * (1.0 - cut_w)
    # ``chain`` is in amp units here (envelope x crest x passes), so the incision is expressed as a share of the
    # target relief - subtracting raw metres from an amplitude would delete whole chain sections.
    chain = chain - (float(p['fringe_incise_m']) / max(float(p['peak_relief_m']), 1.0)) \
        * cut_w * (1.0 - np.clip(en, 0.0, 1.0))
    zone = np.asarray(support, np.float64) > 0.05
    dry = np.asarray(dry, bool)
    ref = before[dry & zone] if (dry & zone).any() else before[dry if dry.any() else np.ones_like(dry)]
    cap = float(np.percentile(np.asarray(ref, np.float64), 99.0))
    # old massif footprint: chain excess only where the old surface was already elevated (the belt platform);
    # the buffer outside it gets foothills only, so no plain is turned into a mountain range.
    lo, hi = float(p['mass_low_share']) * cap, float(p['mass_high_share']) * cap
    mass = _smoothstep(np.clip((np.asarray(before, np.float64) - lo) / max(hi - lo, 1e-6), 0.0, 1.0))
    if dom is not None:
        # high sections and saddles along the chain: the chain keeps its line but not a constant height, so the
        # outline breaks where a section falls low instead of running as one smooth band
        chain = chain * np.asarray(dom['amp_mod'], np.float64)
    chain = chain * mass
    # --- calibration AFTER the cut / along-chain / mass modulation: the source main chain itself must still rise a
    #     massif-sized amount, otherwise a strong cut quietly deletes it. The gain is taken on the selected main
    #     lines only (not a global noise multiplier), so the valleys are not lifted along with the crests.
    main_xyz = [e_['xz_m'] for e_ in structure['main']]
    src = []
    for xz in main_xyz:
        src.extend(_sample_at(grid, chain, xz))
    # ``chain`` is in amp units (envelope x crest x passes), so the gain is what converts it to metres
    src = np.asarray([v for v in src if v > 1e-6], np.float64)
    ref_floor = float(np.median(base[zone])) if zone.any() else float(np.median(base))
    target = max(min(float(p['peak_relief_m']), 0.85 * (cap - ref_floor)), 500.0)
    gain = 1.0
    if src.size >= 4:
        # Reserve headroom for the retained old relief: normalising the 90th percentile
        # to the ceiling saturated whole ridge tops instead of preserving varied summits.
        src_hi = float(np.percentile(src, 99.0))
        gain = float(np.clip(target / max(src_hi, 1e-6), *[float(v) for v in p['chain_cal_gain_range']]))
        chain = chain * gain
    if log:
        log(dict(stage='chain_calibration', samples=int(src.size), target_relief_m=float(target),
                  src_p99_amp=(float(np.percentile(src, 99.0)) if src.size else 0.0), gain=float(gain)))
    # a small, direction-modulated share of the old excess is kept: the rebuilt massif sits on the old trend instead
    # of erasing it, but it is never the full belt platform (that is the v1 look the user rejected).
    old_ex = np.maximum(np.asarray(before, np.float64) - base, 0.0)
    # only where the rebuilt chain itself is (en ~ thr): the thin flanks keep nothing, so the outline still retreats
    keep = float(p['keep_old_excess']) * (np.asarray(dom['amp_mod'], np.float64) if dom is not None else 1.0)
    keep = keep * np.clip(en / max(thr, 1e-6), 0.0, 1.0)
    pied = np.asarray(dom['piedmont'], np.float64) if dom is not None else np.full_like(e, 0.5)
    core = np.clip(en / thr, 0.0, 1.0)
    low_share = float(p['piedmont_lowland_share'])
    pied_m = float(p['piedmont_amp_m']) * (2.0 * pied - 1.0) * (1.0 - 0.8 * core) * (low_share + (1.0 - low_share) * mass)
    total = base + keep * old_ex + pied_m + chain
    cap_soft = max(float(p['peak_soft_share']) * cap, 1.0)
    total = _soft_cap(total, cap, cap_soft)
    total = np.where(dry, np.maximum(total, float(p['min_land_m'])), base)
    return total, cut_w, pied_m, cap


def _group_surface(grid, structure, before, dry, support, env, ridge_m, crest, passf, floor_m, fields, dom, p,
                   *, log=None, wx=None, wz=None, world_seed=0):
    """``structure_policy='mountain-group'``: a wide mountain *group*, one function, metres throughout.

    1. **Group body (wide range)**: a low-frequency share ``group_keep_excess`` (0.30..0.50) of the *old* excess is kept
       as the regional massif body, so the domain is not flattened to the base wherever the crest envelope is zero. The
       share varies smoothly and the body carries its own low-frequency relief, so it is mid/low mountain terrain.
    2. **Two-scale section**: a wide *shoulder* (``envelope_shoulder``) with the narrow crest tent on top. The shoulder
       half width R is mapped from **that crest's own amplitude** (the dH proxy) into ``group_shoulder_half_km``, so a
       high crest really gets a wider shoulder in space - not one amplitude scalar for the whole window.
    3. **dH / R coupling**: each crest's target dH is ``clip(s_tgt * R, group_relief_range_m)`` with
       ``s_tgt = clip(group_slope_range)``; one scalar gain (bounded) converts the *sum* of the group's non-crest terms
       into those metres, so the reported relief is the relief actually built, not an amplitude statistic.
    4. **Graded valleys + foothill skirt**: a continuous trunk incision along the backbone (no hard threshold at 25 km)
       and a wide low skirt (``envelope_skirt``) that is exactly 0 outside its own R - no uniform halo.

    ``chain`` is converted to metres by an explicit calibration on the selected main lines, reusing the accepted
    ``chain_cal_gain_range`` bounds; nothing is lifted to a fixed 5 km and the old peak is never exceeded.

    Returns ``(sculpt, cut_w, pied_m, cap_m, report)`` like ``_rebuilt_excess``, so ``apply_window`` keeps one path.
    """
    base = np.asarray(floor_m, np.float64)
    e = np.asarray(env, np.float64)
    top = float(e.max()) if e.size else 0.0
    en = np.clip(e / max(top, 1e-9), 0.0, 1.0)
    zone = np.asarray(support, np.float64) > 0.05
    dry = np.asarray(dry, bool)
    ref = before[dry & zone] if (dry & zone).any() else before[dry if dry.any() else np.ones_like(dry)]
    cap = float(np.percentile(np.asarray(ref, np.float64), 99.0))
    # --- 1. group body: a low-frequency share of the old excess, plus its own broad relief band
    old_ex = np.maximum(np.asarray(before, np.float64) - base, 0.0)
    body = _field01(grid, wx, wz, derive_subseed(world_seed, 'mountain-sculpt/group'),
                    p['group_body_wavelengths_km'])
    lo_k, hi_k = float(p['group_keep_excess'][0]), float(p['group_keep_excess'][1])
    keep = lo_k + (hi_k - lo_k) * body                      # 0.30..0.50 of the old excess, varying smoothly
    near = np.clip(en / max(float(p['fringe_level']), 1e-6), 0.0, 1.0)   # 1 on the crest band, 0 further out
    body_m = keep * old_ex * (0.55 + 0.45 * body)
    body_m = body_m + float(p['group_body_amp_m']) * (2.0 * body - 1.0) * (1.0 - 0.75 * near)
    # --- 2. shoulder: a REAL spatial field, its half width R mapped from each crest's own amplitude
    shoulder = np.asarray(fields.get('envelope_shoulder'), np.float64) if 'envelope_shoulder' in fields \
        else np.zeros_like(e)
    skirt_f = np.asarray(fields.get('envelope_skirt'), np.float64) if 'envelope_skirt' in fields \
        else np.zeros_like(e)
    # --- 3. dH / R: the representative R of the group is the widest shoulder present (a high crest's own shoulder),
    #     so the reported dH is the relief over that shoulder, and one bounded gain sets it in metres.
    sh_lo, sh_hi = (float(v) for v in p['group_shoulder_half_km'])
    amps = [float(v) for e_ in structure['main'] for v in e_['amp']]
    amp_ref = float(np.percentile(np.asarray(amps, np.float64), 90.0)) if amps else 1.0
    an = float(np.clip(amp_ref, 0.0, 1.0))              # absolute, so raising the group really widens it
    R = float(_group_half_width(an, p))
    s_lo, s_hi = float(p['group_slope_range'][0]), float(p['group_slope_range'][1])
    dH_lo, dH_hi = float(p['group_relief_range_m'][0]), float(p['group_relief_range_m'][1])
    shoulder_amp = float(p['group_shoulder_amp_m'])
    # the generic (non-crest) relief the group actually carries, in metres
    generic = body_m + shoulder_amp * shoulder + float(p['group_skirt_amp_m']) * skirt_f
    dH_in = float(np.percentile(generic[zone], 90.0) - np.percentile(generic[zone], 10.0)) if zone.any() else 0.0
    s_in = dH_in / max(R, 1e-9)
    s_tgt = float(np.clip(s_in, s_lo, s_hi))
    dH_tgt = float(np.clip(s_tgt * R, dH_lo, dH_hi))
    # The slope band is a diagnostic target, not a reason to inflate a gentle mountain body.
    # Only reduce over-strong backgrounds; a lower-than-target slope is allowed.
    body_gain = float(np.clip(dH_tgt / max(dH_in, 1e-6), 0.25, 1.0))
    generic = generic * body_gain
    # --- crest term in AMP units (unchanged shape), then ONE explicit metres conversion on the main lines
    chain = np.asarray(crest, np.float64) * np.asarray(passf, np.float64) * e
    if dom is not None:
        chain = chain * np.asarray(dom['amp_mod'], np.float64)
    chain = chain * (keep / max(hi_k, 1e-9))
    src = []
    for xz in [e_['xz_m'] for e_ in structure['main']]:
        src.extend(_sample_at(grid, chain, xz))
    src = np.asarray([v for v in src if v > 1e-6], np.float64)
    ref_floor = float(np.median(base[zone])) if zone.any() else float(np.median(base))
    # Reserve the broad body's existing height before adding a narrow crest. Calibrating both
    # to the same summit ceiling produced large saturated tables in the first real group window.
    pedestal_samples = []
    for xz in [e_['xz_m'] for e_ in structure['main']]:
        pedestal_samples.extend(_sample_at(grid, base + generic, xz))
    pedestal = float(np.percentile(pedestal_samples, 95.0)) if pedestal_samples else ref_floor
    peak_target = max(min(float(p['peak_relief_m']), 0.80 * (cap - pedestal)), 300.0)
    chain_gain = 1.0
    if src.size >= 4:
        chain_gain = float(np.clip(peak_target / max(float(np.percentile(src, 99.0)), 1e-6),
                                   *[float(v) for v in p['chain_cal_gain_range']]))
    chain_m = chain * chain_gain                      # metres, calibrated on the main lines themselves
    # --- 4a. foothill skirt in metres, exactly 0 outside its own R (the field is 0 there)
    skirt_m = float(p['group_skirt_amp_m']) * skirt_f
    # --- 4b. trunk valley: continuous entry (no hard switch at 25 km), finite width, bed stays positive
    dmain = np.asarray(fields['dist_main_m'], np.float64)
    half = float(p['group_valley_half_km'][0]) * 1000.0
    outer = float(p['group_valley_half_km'][1]) * 1000.0
    inner = half * 0.5
    ramp = _smoothstep(np.clip((dmain - inner) / max(inner, 1.0), 0.0, 1.0))
    vw = _smoothstep(np.clip(1.0 - dmain / max(outer, 1.0), 0.0, 1.0)) * ramp
    vw = np.where(np.isfinite(dmain), vw, 0.0)
    valley_m = float(p['group_valley_depth_m']) * float(p['group_valley_share']) * vw
    total = base + generic + chain_m - valley_m
    cap_soft = max(float(p['peak_soft_share']) * cap, 1.0)
    total = _soft_cap(total, cap, cap_soft)
    total = np.where(dry, np.maximum(total, float(p['min_land_m'])), base)
    # the two metre layers are returned so a caller (and the tests) can measure the real shoulder width and the real
    # mean slope instead of trusting a scalar. ``slope_target`` is the configured band member; ``slope_realised`` is
    # the ratio the surface actually got - different numbers, different names, never conflated.
    shoulder_m = shoulder_amp * shoulder * body_gain
    skirt_m_arr = float(p['group_skirt_amp_m']) * skirt_f * body_gain
    realised = float(dH_in * body_gain / max(R, 1e-9))
    report = dict(shoulder_half_m=float(R), shoulder_amp_m=float(shoulder_amp),
                  group_relief_m=float(dH_tgt), group_relief_realised_m=float(dH_in * body_gain),
                  slope_target=float(s_tgt), slope_realised=float(realised),
                  chain_gain=float(chain_gain), chain_peak_m=float(chain_m.max()),
                  body_gain=float(body_gain), keep_excess=[lo_k, hi_k],
                  slope_range=[s_lo, s_hi], relief_range_m=[dH_lo, dH_hi],
                  note='slope_target is the configured band member (not a law of nature); slope_realised is the '
                       'ratio the built metres actually have; relief is in metres above the group floor')
    if log:
        log(dict(stage='mountain_group', **{k: v for k, v in report.items()
                                            if isinstance(v, (int, float))}))
    return total, None, None, cap, report, dict(shoulder_m=shoulder_m, skirt_m=skirt_m_arr)


def _coast_guard(before_m, wet, cells):
    """Weight 0 on the coastal ring, rising to 1 further inland: the land/sea edge keeps its old value."""
    from scipy import ndimage
    n = int(cells)
    if n <= 0:
        return np.ones(np.shape(before_m), np.float64)
    # distance in cells from the nearest wet / below-sea cell: the first land ring (d = 1) gets exactly 0
    d = ndimage.distance_transform_edt(~np.asarray(wet, bool))
    return _smoothstep(np.clip((d - 1.0) / float(n), 0.0, 1.0)).astype(np.float64)


def _safe_domain(fields, dom, before, fixed, p):
    """Union of the selected corridor support and the saved belt wide band, on dry land only, with a coastal guard.

    This is a *permission* mask: everything inside may be lowered or raised, including the old platform floors.
    """
    sup = np.asarray(fields['support'], np.float64)
    if dom is not None and dom.get('has_belt'):
        sup = np.maximum(sup, np.asarray(dom['belt_band'], np.float64))
    dry = (~np.asarray(fixed, bool)) & (np.asarray(before, np.float64) > 0.0)
    guard = _coast_guard(before, np.asarray(fixed, bool) | ~dry, p['coast_guard_cells'])
    sup = np.where(dry, sup * guard, 0.0)
    return np.clip(sup, 0.0, 1.0).astype(np.float64)


def apply_window(win, structure, grid, *, world_seed=0, params=None, erosion=False, log=None):
    """Sculpt one window: rebuilt massif (base + piedmont + chain) or the v1 corridor replay, real metres.

    ``structure_policy='platform-rebuild'`` (v2, default) separates the **safe domain** (where change is allowed:
    the selected belt's wide band plus an outward buffer, dry land only) from the **mountain outline** (rebuilt from
    the network: a widened/varying crest envelope cut back by low-frequency fields). Inside the domain the old
    platform is replaced by a low base, so its edge may retreat; the main chain keeps its direction and peak level.
    ``structure_policy='corridor'`` reproduces v1 (narrow corridor support, old-surface box-mean floor).

    Returns the result dict used by ``write_candidate``. Ocean / closed sea / lakes / below-sea bed, a coastal ring
    and the outermost halo ring keep the old value bit for bit; everything outside the support is untouched.
    """
    p = _params(params)
    seeds = seeds_for(world_seed)
    schema, algorithm = identity_tags(p)
    v2 = str(p['structure_policy']) in ('platform-rebuild', 'mountain-group')   # both rebuild the domain
    group = str(p['structure_policy']) == 'mountain-group'
    before = np.asarray(win['before_m'], np.float64)
    ocean = np.asarray(win['ocean'], bool)
    fixed = np.asarray(win['fixed'], bool)
    nz, nx = before.shape
    if tuple(grid['shape']) != (nz, nx):
        raise ValueError('grid shape %s differs from the window %s' % (grid['shape'], (nz, nx)))
    wx, wz = _window_warp(grid, p, world_seed)
    dom = belt_domain(structure, grid, wx, wz, p, world_seed=world_seed) if v2 else None
    fields = corridor_fields(structure, grid, wx, wz, p, log=log,
                             width_mod=(dom['width_mod'] if dom is not None else None))
    support = _safe_domain(fields, dom, before, fixed, p) if v2 else np.asarray(fields['support'], np.float64)
    fields['support'] = support.astype(np.float32)
    halo = _halo((nz, nx), int(p['halo_cells'])).astype(np.float64)
    # v2: a wide (metres-based) taper from the window border, so the kept old surface at the border is met along a
    # 80-200 km ramp instead of a straight wall at the 6-cell halo
    taper = _edge_taper(grid, min(float(p['edge_taper_km']), float(p['edge_taper_max_share'])
                                  * min(nz, nx) * float(grid['spacing_m']) / 1000.0)) if v2 \
        else np.ones((nz, nx), np.float64)
    if v2:
        # the low base is the local reference of the rebuilt surface *inside* the safe domain; outside it (or on the
        # border ramp, or on fixed water) the old surface stays its own base, so ``floor_m`` never claims a valley
        # where nothing was rebuilt
        w_base = np.clip(support * halo * taper, 0.0, 1.0)
        w_base = np.where(fixed | ~((~fixed) & (before > 0.0)), 0.0, w_base)
        base_m = before + w_base * (rebuilt_base(grid, before, fixed, p, world_seed=world_seed) - before)
    else:
        base_m = None
    fl = floor_and_basins(grid, before, fixed, fields, p, world_seed=world_seed, log=log, base_m=base_m)
    if log and dom is not None:
        log(dict(stage='safe_domain', belt_band_cells=int((dom['belt_band'] > 0).sum()),
                 domain_cells=int((support > 0).sum()), belt_band=bool(dom['has_belt']),
                 width_var=float(p['width_var']), fringe_cut=float(p['fringe_cut'])))
    crest = crest_factor(grid, wx, wz, p, seeds['mountain-sculpt/crest'])
    if v2:
        # box mean (never a Gaussian): neighbouring cells of the crest multiplier are shared, so a chain reads as a
        # continuous ridge line instead of a string of one-cell spikes
        crest = _smooth_field(crest, int(p['crest_smooth_cells'])).astype(np.float32)
    passes = add_passes(structure, p, world_seed=world_seed)
    passf = pass_factor(passes, grid, wx, wz, p)
    if log:
        log(dict(stage='passes', count=len(passes), network=sum(1 for q in passes if q.get('source') == 'network')))
    env = np.maximum(np.maximum(np.asarray(fields['envelope_main'], np.float64),
                                np.asarray(fields['envelope_branch'], np.float64)),
                     np.asarray(fields['envelope_spur'], np.float64))
    dry = ~fixed & (before > 0.0)
    floor_m = np.asarray(fl['floor_m'], np.float64)
    # v2 normalises on the FINAL chain inside ``_rebuilt_excess`` (after cut / along-chain / mass modulation), so the
    # v1 window-level scale is not applied twice - a pre-cut normalisation is exactly what made the cut delete the
    # main chain on the real belt.
    scale = 1.0 if v2 else _peak_scale(env, crest, passf, floor_m, before, support, dry, p)
    ridge_m = scale * env * np.asarray(crest, np.float64) * np.asarray(passf, np.float64)
    group_report = None
    group_layers = None
    if group:
        sculpt, fringe_f, pied_m, cap_m, group_report, group_layers = _group_surface(
            grid, structure, before, dry, support, env, ridge_m, crest, passf, floor_m, fields, dom, p,
            log=log, wx=wx, wz=wz, world_seed=world_seed)
    elif v2:
        sculpt, fringe_f, pied_m, cap_m = _rebuilt_excess(grid, structure, before, dry, support, env, ridge_m,
                                                          floor_m, fields, dom, p, log=log)
    else:
        sculpt, fringe_f, pied_m, cap_m = floor_m + ridge_m, None, None, None
    # the band that is the flat valley floor (part of the old platform lowered) - finite width, not global
    dmain = np.asarray(fields['dist_main_m'], np.float64)
    band = np.isfinite(dmain) & (dmain > float(p['floor_start_km']) * 1000.0) \
        & (dmain < float(p['floor_radius_km']) * 1000.0) & (np.asarray(fields['support'], np.float64) > 0.0)
    valley = (_smoothstep((dmain - float(p['floor_start_km']) * 1000.0) / (0.25 * float(p['floor_radius_km']) * 1000.0))
              * (1.0 - _smoothstep((dmain - 0.8 * float(p['floor_radius_km']) * 1000.0)
                                  / (0.3 * float(p['floor_radius_km']) * 1000.0))))
    valley = np.where(band, valley, 0.0).astype(np.float32)
    # basins: finite-width flat bottom, lowered from the local valley floor (inside the support only)
    bm = np.asarray(fl['basin_mask'], np.float64) * np.clip(support, 0.0, 1.0)
    bfloor = np.asarray(fl['basin_floor_m'], np.float64)
    if group:
        # Bound the target depth, not the replacement coverage: weakening coverage filled every
        # basin back with its mountain body. A basin may remain shallow but must still have a floor.
        max_depth = float(p['group_valley_depth_m']) * float(p['group_valley_share'])
        bfloor = np.maximum(bfloor, floor_m - max_depth)
    sculpt = np.where(bm > 0, sculpt * (1.0 - bm) + bfloor * bm, sculpt)
    if v2:
        # a basin bed may not go below sea level: the land/sea split of the window is never changed by the sculpt
        sculpt = np.where(dry, np.maximum(sculpt, float(p['min_land_m'])), sculpt)
    # the safe domain is a permission mask: at its outer edge the new surface meets the old one through the
    # smoothstep of the domain itself (no residual old platform inside, no cliff at the edge)
    blend = np.clip(support * halo * taper, 0.0, 1.0)
    blend = np.where(fixed | ~dry, 0.0, blend)
    after = before + blend * (sculpt - before)
    # ``changed_mask`` is every cell whose value moved at all; ``significant`` is the separate >= min_rise_m report.
    # Inside the blend the new surface is never reverted to the old one: that would keep an old platform crest while
    # its flanks are lowered (a discontinuous spike).
    # the masks describe where the change actually landed (support x halo x threshold)
    valley = (np.asarray(valley) * blend).astype(np.float32)
    bm = (bm * blend).astype(np.float32)
    assert np.array_equal(after[fixed], before[fixed]), 'fixed water cells were changed'
    assert np.array_equal(after[0, :], before[0, :]) and np.array_equal(after[-1, :], before[-1, :])
    assert np.array_equal(after[:, 0], before[:, 0]) and np.array_equal(after[:, -1], before[:, -1])
    erosion_report = None
    if erosion:
        e = _erode_window(after, fixed, ocean, grid, p, world_seed=world_seed, log=log)
        # the eroded surface only replaces the sculpted part, tapered by the same blend: a hard switch at blend > 0
        # would leave a step on the halo ramp, so the eroded surface is mixed in through the blend weight itself.
        e = np.where(fixed | ~dry, before, after + blend * (e - after))
        e[0, :], e[-1, :], e[:, 0], e[:, -1] = before[0, :], before[-1, :], before[:, 0], before[:, -1]
        erosion_report = dict(applied=True, iterations=int(p['erosion_iterations']),
                              mean_change_m=float((e - after)[~fixed].mean()),
                              note='coarse irregular-graph stream power, window border = finite exit; no hydrology rebuilt')
        after = e
    after = np.where(fixed, before, after)
    changed = np.asarray(after) != before
    significant = np.abs(np.asarray(after, np.float64) - before) > float(p['min_rise_m'])
    meta = dict(schema=schema, algorithm=algorithm, structure_policy=str(p['structure_policy']),
                world_seed=int(world_seed), params=p, seeds=seeds,
                domain=dict(policy=str(p['structure_policy']),
                            safe_cells=int((support > 0).sum()),
                            belt_band_cells=int((dom['belt_band'] > 0).sum()) if dom is not None else 0,
                            corridor_support_cells=int((np.asarray(fields['support'], np.float64) > 0).sum()),
                            belt_support_scale=float(p['belt_support_scale']),
                            belt_support_extra_km=float(p['belt_support_extra_km']),
                            coast_guard_cells=int(p['coast_guard_cells']),
                            base=('rebuilt low base (ridge_network.lowland_base ramp)' if v2
                                  else 'box mean of the old dry surface clipped to the floor range'),
                            outline=('network tent envelope, width varied by %.2f and fringes cut by a low-frequency '
                                     'field (cut %.2f, incise %.0f m)' % (float(p['width_var']), float(p['fringe_cut']),
                                                                            float(p['fringe_incise_m'])) if v2 else
                                     'network tent envelope on the unmodulated width'))
                             if True else None,
                peak_soft_cap_m=(float(cap_m) if cap_m is not None else None),
                source=win.get('source'),
                support_cells=int((support > 0).sum()), support_land_fraction=float((support[~fixed] > 0).mean()),
                changed_cells=int(changed.sum()), changed_land_fraction=float(changed[~fixed].mean()),
                significant_change_cells=int(significant.sum()),
                significant_change_threshold_m=float(p['min_rise_m']),
                valley_cells=int((valley > 0.5).sum()), basin_cells=int((bm > 0.5).sum()),
                basins=fl['basins'], smooth_cells=int(fl['smooth_cells']), peak_scale=float(scale),
                main_half_width_median_m=float(np.median([v for e in structure['main']
                                                          for v in e['half_width_wide_m']])) if structure['main'] else None,
                main_width_scale=float(p['main_width_scale']),
                peak_target_m=float(np.percentile(before[dry & (support > 0.05)], 99.0))
                if (dry & (support > 0.05)).any() else float(before.max()),
                floor_range_m=[float(floor_m.min()), float(floor_m.max())],
                volume_change_m3=float(((after - before)[~fixed] * float(grid['spacing_m']) ** 2).sum()),
                volume_note='artistic mountain generation, not a mass-conserving geological process',
                group_report=group_report,
                erosion=erosion_report or dict(applied=False, note='erosion not requested'),
                hydrology=dict(computed=False, note='no river/lake was routed or drawn; basins are terrain flats'),
                cross_section='asymmetric tent amp * clip(1 - d/w, 0, 1)**profile_exp, wide/steep flanks from '\
                              'vertex_side; no Gaussian profile, no Gaussian blur, no global noise on the platform',
                boundary='old value kept bitwise on ocean, closed below-sea bed, kept lakes, a coastal ring and the '
                         'outermost halo ring; safe-domain x halo smoothstep blend inside' + ('' if v2 else ''),
                excess=('rebuilt: base(lowland ramp) + kept %.0f%% of the old excess (direction modulated) + low-freq '
                        'piedmont + chain(all belt level-1 segments, narrowed, calibrated on the final chain, '
                        'soft-capped at %.0f m)' % (100.0 * float(p['keep_old_excess']), float(cap_m))
                        if v2 else 'v1: floor + scale*envelope*crest*passes'),
                edge_taper_km=(float(p['edge_taper_km']) if v2 else None),
                reused=dict(files=list(REUSED), sha256={f: _file_sha(f) for f in REUSED}),
                structure=structure)
    result = dict(before_m=before.astype(np.float64), after_m=np.asarray(after, np.float64),
                  changed_mask=changed, significant_mask=significant, blend_weight=blend, halo_weight=halo,
                  support=support.astype(np.float32),
                  valley_mask=np.asarray(valley, np.float32), basin_mask=np.asarray(bm, np.float32),
                  ocean=ocean, lake=np.asarray(win['lake'], bool), closed=np.asarray(win['closed'], bool),
                  before_status=np.asarray(win['status']), floor_m=floor_m.astype(np.float32),
                  envelope=env.astype(np.float32), crest=crest, pass_factor=np.asarray(passf, np.float32),
                  dist_main_m=np.asarray(fields['dist_main_m'], np.float32),
                  # group-only metre layers (None for the other policies): the built shoulder and foothill skirt, so
                  # their real width and slope can be measured instead of inferred from a scalar
                  shoulder_m=(np.asarray(group_layers['shoulder_m'], np.float32)
                              if group_layers else None),
                  skirt_m=(np.asarray(group_layers['skirt_m'], np.float32) if group_layers else None),
                  first_xz_m=tuple(float(v) for v in grid['first_xz_m']), spacing_m=float(grid['spacing_m']),
                  shape=(int(nz), int(nx)), rect_m=tuple(float(v) for v in grid['rect_m']),
                  index=tuple(int(v) for v in grid['index']), structure=structure, passes=passes, meta=meta)
    result['identity'] = identity_of(result)
    return result


def _file_sha(rel):
    root = Path(__file__).resolve().parents[2] / rel
    return fr.file_sha(root) if root.exists() else None


def identity_of(result):
    """Deterministic identity of the generated arrays plus the grid (independent of the run's wall clock)."""
    h = hashlib.sha256()
    for k in ('before_m', 'after_m', 'support', 'blend_weight', 'valley_mask', 'basin_mask'):
        a = np.ascontiguousarray(np.asarray(result[k]))
        h.update(k.encode()); h.update(str(a.dtype).encode()); h.update(str(a.shape).encode()); h.update(a.tobytes())
    h.update(canonical([list(result['first_xz_m']), result['spacing_m'], list(result['shape'])]).encode())
    return h.hexdigest()


# ------------------------------------------------------------------ writing the candidate
def _structure_vectors(result):
    st = result['structure']
    out = dict(main=[], branch=[], spur=[], passes=[], basins=[], connectors=[])
    for kind, key in (('main', 'main'), ('branch', 'branches'), ('spur', 'spurs')):
        for e in st[key]:
            out[kind].append(dict(line=e['line'], level=e['level'], parent=e['parent'], belt=e['belt'],
                                  kind=e['kind'], length_km=e['length_m'] / 1e3, samples=e['samples'],
                                  xz_m=e['xz_m'], half_width_wide_m=e['half_width_wide_m'],
                                  half_width_steep_m=e['half_width_steep_m'], side=e['side'], amp=e['amp']))
    for q in result['passes']:
        out['passes'].append(dict(xz_m=q['xz_m'], depth=float(q['depth']),
                                  half_m=q.get('half_m'), line=q.get('line'), source=q.get('source')))
    for b in result['meta']['basins']:
        out['basins'].append(dict(xz_m=b['xz_m'], radius_km=b.get('radius_km'), target_m=b.get('target_m'),
                                  floor_m=b.get('floor_m'), env=b.get('env')))
        if b.get('connector_xz_m'):
            out['connectors'].append(dict(basin_xz_m=b['xz_m'], xz_m=b['connector_xz_m']))
    return out


def write_candidate(out_dir, result, *, note=None):
    """Write arrays.npz + structure.json + a draft README.md. Never a world-map product manifest."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    # before/after are stored at full precision: storing them as float32 changes the last bit of some cells, so a
    # reader recomputing ``after != before`` gets a different cell count than the reported ``changed_mask``.
    arrays = dict(before_m=np.asarray(result['before_m'], np.float64),
                  after_m=np.asarray(result['after_m'], np.float64),
                  changed_mask=np.asarray(result['changed_mask'], bool),
                  significant_mask=np.asarray(result['significant_mask'], bool),
                  blend_weight=np.asarray(result['blend_weight'], np.float32),
                  halo_weight=np.asarray(result['halo_weight'], np.float32),
                  support=np.asarray(result['support'], np.float32),
                  valley_mask=np.asarray(result['valley_mask'], np.float32),
                  basin_mask=np.asarray(result['basin_mask'], np.float32),
                  ocean=np.asarray(result['ocean'], bool), lake=np.asarray(result['lake'], bool),
                  closed=np.asarray(result['closed'], bool), before_status=np.asarray(result['before_status']),
                  floor_m=np.asarray(result['floor_m'], np.float32),
                  envelope=np.asarray(result['envelope'], np.float32),
                  crest=np.asarray(result['crest'], np.float32),
                  pass_factor=np.asarray(result['pass_factor'], np.float32),
                  dist_main_m=np.asarray(result['dist_main_m'], np.float32),
                  first_xz_m=np.asarray(result['first_xz_m'], np.float64),
                  spacing_m=np.asarray([result['spacing_m']], np.float64),
                  shape=np.asarray(result['shape'], np.int64),
                  rect_m=np.asarray(result['rect_m'], np.float64),
                  window_index=np.asarray(result['index'], np.int64))
    np.savez_compressed(out / 'arrays.npz', **arrays)
    structure = _structure_vectors(result)
    doc = dict(schema=result['meta'].get('schema') or SCHEMA,
               algorithm=result['meta'].get('algorithm') or ALGORITHM,
               identity=result['identity'], grid=dict(
        first_xz_m=list(result['first_xz_m']), spacing_m=result['spacing_m'], shape_zx=list(result['shape']),
        rect_m=list(result['rect_m']), window_index=list(result['index']), axes='arrays [z, x]; X east, Z south; metres'),
        structure=structure, structure_meta=result['structure']['meta'], meta={k: v for k, v in result['meta'].items()
                                                                             if k != 'structure'}, note=note)
    (out / 'structure.json').write_text(json.dumps(doc, ensure_ascii=False, indent=1, allow_nan=False), encoding='utf-8')
    (out / 'README.md').write_text(_readme(result, note), encoding='utf-8')
    return dict(dir=str(out), arrays='arrays.npz', structure='structure.json', readme='README.md',
                identity=result['identity'])


def _readme(result, note):
    m = result['meta']
    meta = result['structure']['meta']
    dom = m.get('domain') or {}
    head = ('# 山域结构局部原型候选（%s）\n\n' % (m.get('schema') or SCHEMA)
            + '本目录**不是**正式游戏世界产品，不带世界 manifest，不是默认世界层的接线；仅用于对照这一窗口的结构化结果。\n\n')
    body = ('## 位置\n\n- 窗口：X %.0f..%.0f km，Z %.0f..%.0f km（%d×%d 格，%g m）\n- 产品格索引：ix0=%d, iz0=%d\n'
            '- 选中 belt：%s；主脊线：%s；主方向 (%.2f, %.2f)，走向一致性 %.2f\n\n'
            '## 做了什么\n\n'
            '- 策略 `%s`：安全域（允许改变的范围）与山体高程包络分开；安全域 = 所选 belt 宽带 ×%.2f 向外 %.0f km '
            '缓冲（仅陆地，带海岸保护环 %d 格），不是一条窄走廊。\n'
            '- 域内旧宽平台的高程被重建：低基底（`ridge_network.lowland_base` 斜面）+ 山麓低频起伏 + 网络山脊，'
            '旧平台边缘因此可向内退。\n'
            '- 山脊包络宽度按低频场变宽/变窄，外缘被低频场切退并下切：轮廓凹入/断开，不再是一圈平滑偏移。\n'
            '- 谷底为重建低基底（%.0f 到 %.0f m），保留 %d 个有限宽山间盆地（底 %s m）。\n'
            '- 峰高量级保留：新脊峰软上限按原窗口干地 99 分位 %.0f m（scale %.1f），不削成平顶。\n'
            '- 体积改变 %.3e m³（艺术生成，不冒充守恒地质过程）。\n\n'
            '## 边界与水文\n\n- 海、封闭负地形、原湖面、海岸环与最外 halo 环逐位保持原值；改变只在安全域内。\n'
            '- **未算水文**：不新绘河湖，也不把旧河线画到新面上；盆地是地形低平底，不是水面。\n'
            '- 侵蚀：%s\n\n'
            '## 文件\n\n- `arrays.npz`：before_m/after_m/changed_mask/blend_weight/support/valley_mask/basin_mask/'
            'ocean/lake/closed/floor_m/envelope/crest/pass_factor/dist_main_m + 网格字段\n'
            '- `structure.json`：全网实际结构矢量（主脊/支脉/子脊/山口/盆地/连接谷）与 meta\n\n'
            '%s\n'
            % (result['rect_m'][0] / 1e3, result['rect_m'][2] / 1e3, result['rect_m'][1] / 1e3,
               result['rect_m'][3] / 1e3, result['shape'][1], result['shape'][0], result['spacing_m'],
               result['index'][0], result['index'][1], meta['belt'], meta['main_lines'],
               meta['main_direction'][0], meta['main_direction'][1], meta['main_coherence'],
               dom.get('policy', 'platform-rebuild'), dom.get('belt_support_scale', 0.0),
               dom.get('belt_support_extra_km', 0.0), dom.get('coast_guard_cells', 0),
               m['floor_range_m'][0], m['floor_range_m'][1], len(m['basins']),
               [round(b.get('target_m', 0.0)) for b in m['basins']], m['peak_target_m'], m['peak_scale'],
               m['volume_change_m3'], m['erosion'].get('note', ''), note or ''))
    return head + body
