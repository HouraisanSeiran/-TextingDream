"""Implicit n=1 stream power and explicit stable hillslope diffusion."""
import numpy as np
from scipy import ndimage,sparse
from scipy.sparse.linalg import spsolve_triangular
from .drainage import route

def evolve(initial,ocean,uplift,spacing,steps=12,dt_years=100000,k=2e-6,diffusivity=.03,progress=None,area_mode='d8'):
    h = initial.astype(float).copy()
    for step in range(steps):
        flow = route(h,ocean,spacing,area_mode)
        order,parent = flow['order'],flow['parent']
        active = ~ocean.ravel()[order] & ~flow['closed_mask'].ravel()[order] & (parent != np.arange(h.size))
        length = np.maximum(flow['distance_m'][order],spacing)
        coefficient = k*np.sqrt(flow['area_m2'].ravel()[order])*dt_years/length
        coefficient *= active
        rhs = h.ravel()[order]+uplift.ravel()[order]*dt_years*(~ocean.ravel()[order])
        # Rivers terminate at sea surface, never erode toward the abyssal bed.
        water = flow['closed_mask'].ravel()[order]
        preserved = rhs[water].copy()
        rhs[water] = flow['filled_m'].ravel()[order][water]
        rhs[ocean.ravel()[order]] = 0
        diagonal = 1+coefficient
        matrix = sparse.diags(diagonal,format='csr')-sparse.diags(coefficient,format='csr')@flow['transfer']
        solved = spsolve_triangular(matrix,rhs,lower=True)
        solved[water] = preserved
        h.ravel()[order] = solved
        # No sediment removal by sink filling: closed depressions remain stored beds.
        alpha = diffusivity*dt_years/(spacing*spacing)
        substeps = max(1,int(np.ceil(alpha/.2)))
        for _ in range(substeps):
            lap = ndimage.laplace(h,mode='nearest')
            h[~ocean] += (alpha/substeps)*lap[~ocean]
        h[ocean] = initial[ocean]
        if progress:
            progress(step+1,h)
    return h,route(h,ocean,spacing,area_mode)
