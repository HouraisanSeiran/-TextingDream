"""Normal relative velocity defines convergence; dilation defines mountain belts."""
import numpy as np
from scipy import ndimage

def boundary_fields(plate, velocities, spacing, width_m=24000):
    convergence = np.zeros(plate.shape)
    divergence = np.zeros(plate.shape)
    transform = np.zeros(plate.shape)
    for axis in (0,1):
        a = [slice(None),slice(None)]; b = list(a)
        a[axis] = slice(None,-1); b[axis] = slice(1,None)
        a,b = tuple(a),tuple(b)
        pa,pb = plate[a],plate[b]
        dv = velocities[pb]-velocities[pa]
        component = 1 if axis == 0 else 0
        normal = -dv[...,component]
        changed = pa != pb
        for target, strength in ((convergence,np.maximum(normal,0)),(divergence,np.maximum(-normal,0)),(transform,np.abs(dv[...,1-component]))):
            strength = strength*changed
            target[a] = np.maximum(target[a],strength)
            target[b] = np.maximum(target[b],strength)
    if np.any(convergence):
        distance, indices = ndimage.distance_transform_edt(convergence == 0, sampling=spacing, return_indices=True)
        belt = convergence[tuple(indices)] / 4000 * np.exp(-.5*(distance/width_m)**2)
    else:
        belt = np.zeros(plate.shape)
    return belt, dict(convergence=convergence, divergence=divergence, transform=transform)

def uplift_field(plate, velocities, thickness, continental, spacing):
    belt, classes = boundary_fields(plate,velocities,spacing)
    # Thickness modulates convergent belts, but cannot turn rifts/transforms into mountains.
    strength = np.clip((thickness-7000)/35000,.15,1.8)
    return belt*strength*np.clip(continental*2,0,1), classes
