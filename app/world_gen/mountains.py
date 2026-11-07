"""Mountain reinforcement for the world skeleton (CPU only; Terragenesis is imported read-only).

The tectonic evolution (Terragenesis `evolve`) only produces thin crustal-thickening ridges. This module
re-derives the mountains from the final plate geometry:

1. `boundary_convergence`: for every pair of touching plates the boundary normal is estimated from a smoothed
   plate indicator (not from the staircase of grid faces) and the relative plate velocity is projected on it.
   Only convergent boundaries (approach rate above `TRANSFORM_RATIO` of the relative speed) carry mountains;
   divergent (rift) and transform (slip) boundaries get none. Sign convention equals
   `tectonic_evolution._boundaries` (A moving towards B along the A->B normal = convergent).
2. `build_belt_shape`: curved ribbons are placed along the convergent boundary. The orientation of each ribbon is
   the principal axis of the local boundary cloud (so the grid staircase never reaches the ridge line), the
   centre line is moved to the continental side, and the ribbon profile is Terragenesis'
   `skeleton_mountains._ribbon` (asymmetric profile: wide landward slope, steep seaward slope). Ribbons are merged with the
   same zero-preserving soft union (sum u^9 / sum u^8) that `skeleton_mountains._source_uplift` uses.
3. `enhance_mountains`: the land base is smoothed and saturated below the mountain proxy, a small plains
   relief is added, and the belt uplift is scaled (bisection) so that the share of land cells above the
   proxy elevation hits the target. Only land cells (elevation > 0) change; ocean cells are untouched and no land
   cell can drop to <= 0, so the land/sea split is exactly preserved (asserted).

All randomness uses `derive_subseed(world_seed, <purpose>)`.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

import numpy as np
from scipy import ndimage

from .config import derive_subseed

PROFILE = 'asymmetric'                 # Terragenesis PROFILES key: (left .155, right .040, ...) half widths
TRANSFORM_RATIO = 0.3                  # |approach rate| <= ratio * |relative speed| -> transform boundary
BASE_SOFT_START_M = 900.0              # land base saturates smoothly towards BASE_SOFT_LIMIT_M (< mountain proxy)
BASE_SOFT_LIMIT_M = 1200.0
PLAINS_RELIEF_M = 60.0
SEED_PURPOSES = ('mountain-bend', 'mountain-modulation', 'mountain-rugged', 'plains-relief-broad', 'plains-relief-fine')
REUSED = (
    ('terrain_pipeline/tectonic.py', ('TectonicConfig', 'initialize', 'evolve', 'surface_fields', 'CrustState'),
     'plate evolution; plate_id / velocities and the convergence sign convention of _boundaries'),
    ('terrain_pipeline/tectonic.py', ('plan', 'connected_ocean'), 'resource pre-check; connected ocean flag'),
    ('terrain_pipeline/skeleton_mountains.py', ('_ribbon', 'PROFILES'),
     'curved asymmetric ridge ribbon profile along a bent centre line (private function imported read-only); '
     'soft-union rule copied from _source_uplift'),
)


def _tg():
    from .skeleton import _terragenesis
    _terragenesis()                       # puts the Terragenesis root on sys.path
    from terrain_pipeline import skeleton_mountains as sm
    return sm._ribbon, sm.PROFILES


def reuse_record(terragenesis_root):
    out = []
    for rel, funcs, role in REUSED:
        p = Path(terragenesis_root) / rel
        out.append(dict(file=rel, sha256=hashlib.sha256(p.read_bytes()).hexdigest(), functions=list(funcs), role=role))
    return out


def _nb4(mask):
    return np.roll(mask, 1, 0) | np.roll(mask, -1, 0) | np.roll(mask, 1, 1) | np.roll(mask, -1, 1)


def boundary_convergence(plate_id, velocities, sigma=2.0, transform_ratio=TRANSFORM_RATIO):
    """Per boundary cell: convergent / divergent / transform class and convergence strength in [0, 1]."""
    pid = np.asarray(plate_id).astype(np.int64)
    vel = np.asarray(velocities, dtype=np.float64)
    pairs = []
    for axis in (0, 1):
        nb = np.roll(pid, -1, axis=axis)
        m = pid != nb
        pairs.append(np.stack([np.minimum(pid[m], nb[m]), np.maximum(pid[m], nb[m])], axis=1))
    pairs = np.unique(np.concatenate(pairs), axis=0) if pairs else np.zeros((0, 2), int)
    rate = np.full(pid.shape, -np.inf)
    relmag = np.zeros(pid.shape)
    has = np.zeros(pid.shape, bool)
    for a, b in pairs:
        ia, ib = pid == a, pid == b
        band = (ia & _nb4(ib)) | (ib & _nb4(ia))
        s = ndimage.gaussian_filter(ib.astype(np.float64) - ia.astype(np.float64), sigma, mode='wrap')
        gx = (np.roll(s, -1, 1) - np.roll(s, 1, 1)) * 0.5
        gz = (np.roll(s, -1, 0) - np.roll(s, 1, 0)) * 0.5
        norm = np.hypot(gx, gz)
        ok = band & (norm > 1e-9)
        vrel = vel[a] - vel[b]
        r = (vrel[0] * gx + vrel[1] * gz) / np.maximum(norm, 1e-12)
        take = ok & (r > rate)
        rate[take] = r[take]
        relmag[take] = float(np.hypot(*vrel))
        has |= ok
    rate = np.where(has, rate, 0.0)
    conv = has & (rate > transform_ratio * relmag)
    div = has & (rate < -transform_ratio * relmag)
    trn = has & ~conv & ~div
    ref = float(np.percentile(rate[conv], 90)) if conv.any() else 1.0
    strength = np.clip(rate / max(ref, 1e-9), 0, 1) * conv
    return dict(strength=strength, convergent=conv, divergent=div, transform=trn,
                cells=dict(boundary=int(has.sum()), convergent=int(conv.sum()), divergent=int(div.sum()),
                           transform=int(trn.sum())),
                pairs=int(len(pairs)))


def build_belt_shape(strength, land_f, width_cells, cell_m, bend_seed, *, bucket=2, radius=4, length_cells=None,
                     offset_frac=0.15):
    """Union of curved ribbons along the convergent boundary; values in [0, 1] (1 = full crest)."""
    ribbon, profiles = _tg()
    left, right = profiles[PROFILE][:2]
    scale_m = width_cells / (left + right) * cell_m
    length = length_cells or max(8.0, 0.7 * width_cells)
    nz, nx = strength.shape
    weights = np.zeros((nz, nx))
    weighted = np.zeros((nz, nx))
    cand = np.argwhere(strength > 0)
    info = dict(width_cells=float(width_cells), length_cells=float(length), segments=0, candidates=int(len(cand)))
    if not len(cand):
        return weights, info
    order = np.argsort(-strength[cand[:, 0], cand[:, 1]], kind='stable')
    key = (cand[order, 0] // bucket) * (nx // bucket + 2) + cand[order, 1] // bucket
    _, first = np.unique(key, return_index=True)
    sel = cand[order[first]]
    sel = sel[np.lexsort((sel[:, 1], sel[:, 0]))]
    reach = int(math.ceil(0.5 * width_cells + 0.5 * length))
    local_land = ndimage.uniform_filter(land_f, size=min(2 * reach + 1, nz, nx), mode='wrap')
    sel = sel[local_land[sel[:, 0], sel[:, 1]] > 0.03]
    d = np.arange(-radius, radius + 1)
    DX, DZ = np.meshgrid(d, d)
    gauss = np.exp(-(DX ** 2 + DZ ** 2) / (2 * (radius / 1.5) ** 2))
    half = min(int(math.ceil(max(0.6 * length, width_cells))) + 2, (min(nz, nx) - 1) // 2)
    dw = np.arange(-half, half + 1)
    WX, WZ = np.meshgrid(dw, dw)
    X, Z = WX * cell_m, WZ * cell_m
    rng = np.random.default_rng(bend_seed)
    probe = max(2.0, 0.5 * width_cells)
    offset = offset_frac * width_cells
    for z0, x0 in sel:
        wm = (strength[np.ix_((z0 + d) % nz, (x0 + d) % nx)] > 0) * gauss
        sw = wm.sum()
        if sw <= 0:
            continue
        mx, mz = (wm * DX).sum() / sw, (wm * DZ).sum() / sw
        cxx, czz = (wm * (DX - mx) ** 2).sum() / sw, (wm * (DZ - mz) ** 2).sum() / sw
        cxz = (wm * (DX - mx) * (DZ - mz)).sum() / sw
        theta = 0.5 * math.atan2(2 * cxz, cxx - czz)
        nxl, nzl = -math.sin(theta), math.cos(theta)          # left normal of the ribbon (wide slope side)
        px, pz = x0 + mx, z0 + mz

        def land_side(sign):
            return sum(land_f[int(round(pz + sign * nzl * probe * k)) % nz, int(round(px + sign * nxl * probe * k)) % nx]
                       for k in (0.5, 1.0, 1.5))
        if land_side(-1) > land_side(1):
            theta += math.pi
            nxl, nzl = -nxl, -nzl
        cx, cz = px + nxl * offset, pz + nzl * offset
        xc, zc = int(round(cx)), int(round(cz))
        curve = dict(start_x_m=(cx - xc - math.cos(theta) * 0.4 * length) * cell_m,
                     start_z_m=(cz - zc - math.sin(theta) * 0.4 * length) * cell_m,
                     angle_rad=theta, length_m=length * cell_m, bend_m=length * cell_m * 0.10 * rng.uniform(-1, 1),
                     width_factor=1.0, level=1, attach_t=0.0)
        s = float(strength[z0, x0])
        u = ribbon(X, Z, curve, PROFILE, scale_m) * (0.55 + 0.45 * s)
        idx = ((zc + WZ) % nz, (xc + WX) % nx)
        np.add.at(weights, idx, u ** 8)
        np.add.at(weighted, idx, u ** 9)
        info['segments'] += 1
    return np.divide(weighted, weights, out=np.zeros_like(weights), where=weights > 1e-300), info


def _smooth_compress(e, land, sigma=1.5):
    num = ndimage.gaussian_filter(np.where(land, e, 0.0), sigma, mode='wrap')
    den = ndimage.gaussian_filter(land.astype(np.float64), sigma, mode='wrap')
    sm = np.where(land, num / np.maximum(den, 1e-9), e)
    span = BASE_SOFT_LIMIT_M - BASE_SOFT_START_M
    sat = BASE_SOFT_START_M + span * (1 - np.exp(-np.maximum(sm - BASE_SOFT_START_M, 0) / span))
    return np.where(land, np.where(sm > BASE_SOFT_START_M, sat, sm), e)


def _plains_relief(land, world_seed, amplitude=PLAINS_RELIEF_M):
    from .skeleton import periodic_noise
    pad = 8
    dist = ndimage.distance_transform_edt(np.pad(land, pad, mode='wrap'))[pad:-pad, pad:-pad] if not land.all() \
        else np.full(land.shape, 99.0)
    ramp = np.clip((dist - 1) / 4.0, 0, 1)
    noise = (0.65 * periodic_noise(land.shape, derive_subseed(world_seed, 'plains-relief-broad'), exponent=2.6)
             + 0.35 * periodic_noise(land.shape, derive_subseed(world_seed, 'plains-relief-fine'), exponent=1.2))
    return amplitude * noise * ramp


def belt_width_cells(mask):
    """Approximate belt thickness in cells: 2*EDT-1 on medial-axis cells (EDT local maxima)."""
    if not mask.any():
        return dict(median=0.0, mean=0.0)
    pad = 6
    edt = ndimage.distance_transform_edt(np.pad(mask, pad, mode='wrap'))[pad:-pad, pad:-pad]
    medial = mask & (edt >= ndimage.maximum_filter(edt, size=3, mode='wrap') - 1e-9)
    w = 2 * edt[medial] - 1
    return dict(median=float(np.median(w)), mean=float(w.mean()))


def enhance_mountains(elev, plate_id, velocities, *, cell_m, world_seed, target_fraction, proxy_m=1500.0,
                      width_candidates=(7, 9, 11, 14, 18, 24), pref_amp_m=5200.0, cap_amp_m=7500.0, min_width_cells=3.5):
    from .skeleton import periodic_noise
    e = np.asarray(elev, dtype=np.float64)
    land = e > 0
    seeds = {p: derive_subseed(world_seed, p) for p in SEED_PURPOSES}
    meta = dict(method='plate-boundary ribbons (convergent only) + smoothed saturated base + plains relief',
                subseeds=seeds, target_land_fraction=float(target_fraction), proxy_m=float(proxy_m))
    if not land.any() or target_fraction <= 0:
        meta['applied'] = False
        return e.copy(), meta
    conv = boundary_convergence(plate_id, velocities)
    meta['boundary_cells'] = conv['cells']
    meta['plate_pairs'] = conv['pairs']
    base = _smooth_compress(e, land)
    relief = _plains_relief(land, world_seed)
    low = np.where(land, np.maximum(base + relief, 1.0), e)
    mod = np.clip(1 + 0.22 * periodic_noise(e.shape, seeds['mountain-modulation'], exponent=3.0), 0.55, 1.35)
    rug = np.clip(periodic_noise(e.shape, seeds['mountain-rugged'], exponent=1.4), -1.5, 1.5)
    land_f = land.astype(np.float64)

    def fraction(shape, amp):
        return float(((low + amp * shape) > proxy_m)[land].mean())

    def solve(shape, hi):
        if fraction(shape, hi) < target_fraction:
            return hi
        lo = 0.0
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            lo, hi = (mid, hi) if fraction(shape, mid) < target_fraction else (lo, mid)
        return hi

    trials, chosen = [], None
    for width in width_candidates:
        belt, info = build_belt_shape(conv['strength'], land_f, width, cell_m, seeds['mountain-bend'])
        shape = belt * mod * (1 + 0.15 * rug)
        amp = solve(shape, cap_amp_m)
        frac = fraction(shape, amp)
        bw = belt_width_cells(((low + amp * shape) > proxy_m) & land)
        trial = dict(info, amp_m=float(amp), land_fraction=frac, belt_width_median_cells=bw['median'],
                     belt_width_mean_cells=bw['mean'], reached=bool(abs(frac - target_fraction) <= 0.0015))
        trials.append(trial)
        if chosen is None and trial['reached'] and amp <= pref_amp_m and bw['median'] >= min_width_cells:
            chosen = (trial, shape, amp)
            break
        trial['_shape'] = shape
    if chosen is None:                    # nothing met every preference: smallest deviation, then thicker belt
        pick = min(trials, key=lambda t: (round(abs(t['land_fraction'] - target_fraction), 4), -t['belt_width_median_cells']))
        chosen = (pick, pick['_shape'], pick['amp_m'])
    trial, shape, amp = chosen
    for t in trials:
        t.pop('_shape', None)
    out = np.where(land, np.maximum(low + amp * shape, 1.0), e)
    assert ((out > 0) == land).all(), 'mountain enhancement changed the land/sea split'
    assert (out[~land] == e[~land]).all()
    meta.update(applied=True, chosen_width_cells=trial['width_cells'], amp_m=float(amp), width_trials=trials,
                segments=trial['segments'], land_fraction_after=float(((out > proxy_m)[land]).mean()),
                belt_width_median_cells=trial['belt_width_median_cells'], plains_relief_m=PLAINS_RELIEF_M,
                base_saturation_m=[BASE_SOFT_START_M, BASE_SOFT_LIMIT_M])
    return out, meta
