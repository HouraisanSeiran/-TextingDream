"""Author-side soft land/crust intent; TG still owns tectonic evolution.

Inspired by dreamulator's geography input, implemented for finite metric grids.
No post-evolution pinning, sea-level edits, periodic copies or terrain generation.
"""
from __future__ import annotations

import numpy as np

ALGORITHM = 'dream-geography-soft-crust-1'


def bias_land_field(field, cfg):
    """Add compact C2 kernels at cell centres; absent intent is an exact no-op."""
    features = cfg.get('geography_features', [])
    if not features:
        return field
    cell = cfg['skeleton']['cell_size_km'] * 1000
    ox, oz = np.asarray(cfg['world']['origin_km']) * 1000
    z, x = np.meshgrid(oz + (np.arange(field.shape[0]) + .5) * cell,
                       ox + (np.arange(field.shape[1]) + .5) * cell, indexing='ij')
    out = field.copy()
    for f in features:
        # Bearing clockwise from north, with Z positive south. Radius is the minor semiaxis.
        angle = np.deg2rad(f['bearing_deg'])
        dx, dz = x - f['center_x_m'], z - f['center_z_m']
        along = dx * np.sin(angle) - dz * np.cos(angle)
        across = dx * np.cos(angle) + dz * np.sin(angle)
        r = np.sqrt((along / (f['radius_m'] * f['aspect'])) ** 2 + (across / f['radius_m']) ** 2)
        q = np.clip(1 - r, 0, 1)
        out += f['strength'] * q ** 4 * (1 + 4 * np.minimum(r, 1))
    return out


def result_record(cfg, elevation_m):
    """Report sampled final outcome, not a claim that soft intent is a constraint."""
    cell = cfg['skeleton']['cell_size_km'] * 1000
    ox, oz = np.asarray(cfg['world']['origin_km']) * 1000
    outcomes = []
    for f in cfg['geography_features']:
        ix = min(elevation_m.shape[1] - 1, int((f['center_x_m'] - ox) // cell))
        iz = min(elevation_m.shape[0] - 1, int((f['center_z_m'] - oz) // cell))
        height = float(elevation_m[iz, ix])
        land = height > 0
        outcomes.append(dict(id=f['id'], cell_zx=[iz, ix],
            sampled_center_xz_m=[float(ox + (ix + .5) * cell), float(oz + (iz + .5) * cell)],
            final_elevation_m=height, final_is_land=land,
            soft_intent_met=(land if f['strength'] > 0 else not land) if f['strength'] else None))
    return dict(algorithm=ALGORITHM, features=cfg['geography_features'], outcomes=outcomes,
        semantics='initial crust bias only; global ocean tuning and periodic TG advection can affect distant cells; final geometry not pinned')
