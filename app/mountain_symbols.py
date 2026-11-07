"""Display-only mountain-belt approximation in a finite planar DEM.

Not a geological interpretation. Inputs are never modified.
"""
from __future__ import annotations
import math
import numpy as np
from scipy import ndimage as ndi
from app.terrain_source import LAND

PARAMETERS = dict(scales_km=[40, 100], relief_m=300, relative_m=100,
                  slope=0.006, minimum_component_cells=4, minimum_branch_cells=3,
                  icon_spacing_px=30, icon_width_px=24, icon_height_px=18)


def _thin(mask):
    """Zhang-Suen topology-preserving thinning; false outside finite domain."""
    a = np.pad(mask.astype(np.uint8), 1)
    changed = True
    while changed:
        changed = False
        for step in (0, 1):
            p = [a[:-2,1:-1], a[:-2,2:], a[1:-1,2:], a[2:,2:],
                 a[2:,1:-1], a[2:,:-2], a[1:-1,:-2], a[:-2,:-2]]
            n = sum(p)
            transitions = sum(((p[i] == 0) & (p[(i+1)%8] == 1)).astype(np.uint8) for i in range(8))
            if step == 0:
                c = (p[0]*p[2]*p[4] == 0) & (p[2]*p[4]*p[6] == 0)
            else:
                c = (p[0]*p[2]*p[6] == 0) & (p[0]*p[4]*p[6] == 0)
            remove = (a[1:-1,1:-1] == 1) & (n >= 2) & (n <= 6) & (transitions == 1) & c
            if remove.any():
                a[1:-1,1:-1][remove] = 0
                changed = True
    return a[1:-1,1:-1].astype(bool)


def _paths(skeleton, min_branch=3):
    nodes = set(map(tuple, np.argwhere(skeleton)))
    def neighbors(p):
        y,x = p
        return sorted((y+dy,x+dx) for dy in (-1,0,1) for dx in (-1,0,1)
                      if (dy or dx) and (y+dy,x+dx) in nodes)
    adj = {p: neighbors(p) for p in nodes}
    edges = set()
    paths = []
    starts = sorted(p for p in nodes if len(adj[p]) != 2)
    # Closed loops have no endpoint; start at a stable node.
    for start in starts + sorted(nodes):
        for nxt in adj[start]:
            edge = tuple(sorted((start,nxt)))
            if edge in edges:
                continue
            path = [start,nxt]; edges.add(edge)
            while len(adj[path[-1]]) == 2:
                q = next((n for n in adj[path[-1]] if n != path[-2]), None)
                if q is None or tuple(sorted((path[-1],q))) in edges:
                    break
                edges.add(tuple(sorted((path[-1],q)))); path.append(q)
            if len(path) >= min_branch:
                paths.append(path)
    return paths


def extract_mountains(elevation, status, spacing_m, first_xz_m=(0,0)):
    h = np.asarray(elevation, dtype=float)
    land = (np.asarray(status) == LAND) & np.isfinite(h)
    # Nearest valid land fills excluded cells for filters, never for classification.
    if not land.any():
        return dict(mask=np.zeros(h.shape,bool), skeleton=np.zeros(h.shape,bool), paths=[], score=np.zeros(h.shape))
    nearest = ndi.distance_transform_edt(~land, return_distances=False, return_indices=True)
    filled = h[tuple(nearest)]
    score = np.zeros(h.shape)
    for scale in (40000., 100000.):
        size = max(3, int(round(scale / spacing_m)) | 1)
        low = ndi.minimum_filter(filled, size=size, mode='nearest')
        high = ndi.maximum_filter(filled, size=size, mode='nearest')
        relative = filled - low
        relief = high - low
        score = np.maximum(score, np.minimum(relative / 100., relief / 300.))
    gz,gx = np.gradient(filled, spacing_m)
    slope = np.hypot(gx,gz)
    # A local gradient is essential: a flat elevated plateau interior is excluded.
    mask = land & (score >= 1) & (ndi.maximum_filter(slope, size=3) >= .006)
    labels,n = ndi.label(mask, structure=np.ones((3,3)))
    sizes = np.bincount(labels.ravel()); mask &= sizes[labels] >= 4
    skeleton = _thin(mask)
    paths = _paths(skeleton)
    return dict(mask=mask, skeleton=skeleton, paths=paths, score=score)


def place_icons(result, status, spacing_m, first_xz_m, pixels_per_cell, width_px=24, height_px=18, interval_px=30):
    """Return non-overlapping icons; every covered source cell must be land and mountain."""
    mask = result['mask']; status = np.asarray(status); nz,nx = mask.shape
    occupied = []; icons = []
    for path in result['paths']:
        distance = interval_px
        previous = None
        for y,x in path:
            if previous is not None:
                distance += math.hypot(y-previous[0],x-previous[1])*pixels_per_cell
            previous = (y,x)
            if distance < interval_px:
                continue
            px,py = (x+.5)*pixels_per_cell, (y+.5)*pixels_per_cell
            box = (px-width_px/2,py-height_px/2,px+width_px/2,py+height_px/2)
            x0,y0 = math.floor(box[0]/pixels_per_cell),math.floor(box[1]/pixels_per_cell)
            x1,y1 = math.ceil(box[2]/pixels_per_cell),math.ceil(box[3]/pixels_per_cell)
            if x0<0 or y0<0 or x1>nx or y1>nz or not np.all(status[y0:y1,x0:x1] == LAND) or not np.all(mask[y0:y1,x0:x1]):
                continue
            if any(box[0]<b[2] and box[2]>b[0] and box[1]<b[3] and box[3]>b[1] for b in occupied):
                continue
            occupied.append(box); distance = 0
            icons.append(dict(x_px=px,y_px=py,box_px=box,x_m=first_xz_m[0]+x*spacing_m,
                              z_m=first_xz_m[1]+y*spacing_m,kind='mountain'))
    return icons
