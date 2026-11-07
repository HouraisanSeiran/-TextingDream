"""V2 declared morphology: curved broad belts and multiscale drainage divides."""
import numpy as np
from scipy import ndimage
from .source import spatial_noise, subseed

PURPOSES = ('v2-warp-x-96km','v2-warp-z-96km','v2-warp-x-32km','v2-warp-z-32km') + tuple(f'v2-relief-{km}km' for km in (64,32,16,8,4,2))
PARAMETERS = dict(skeleton_smoothing_sigma_m=14000,uplift_smoothing_sigma_m=16000,warp_wavelengths_m=[96000,32000],warp_amplitudes_m=[22000,6500],relief_wavelengths_m=[64000,32000,16000,8000,4000,2000],mountain_amplitudes_m=[700,550,450,320,200,100],plain_amplitudes_m=[120,85,55,32,18,9],coastal_fade_m=16000)

def initial_surface(base,uplift,thickness,ocean,first,spacing,seed=20260903):
    shape=base.shape
    seeds={purpose:subseed(seed,purpose) for purpose in PURPOSES}
    dx=np.zeros(shape);dz=np.zeros(shape)
    for km,amplitude in ((96,22000),(32,6500)):
        dx += amplitude*spatial_noise(shape,first,spacing,seeds[f'v2-warp-x-{km}km'],km*1000)
        dz += amplitude*spatial_noise(shape,first,spacing,seeds[f'v2-warp-z-{km}km'],km*1000)
    distance=ndimage.distance_transform_edt(~ocean,sampling=spacing)
    fade=np.clip(distance/16000,0,1)
    fade=fade*fade*(3-2*fade)
    z,x=np.indices(shape,dtype=float)
    coords=[z+dz*fade/spacing,x+dx*fade/spacing]
    def warped(a):
        return ndimage.map_coordinates(a,coords,order=3,mode='nearest')
    smooth=ndimage.gaussian_filter(base,PARAMETERS['skeleton_smoothing_sigma_m']/spacing,mode='nearest')
    curved=warped(smooth)
    # Coastal heights retain their zero contour; warped morphology is inland only.
    surface=base*(1-fade)+curved*fade
    broad=ndimage.gaussian_filter(uplift,16000/spacing,mode='nearest')
    belt=np.maximum(warped(broad),0)
    mountain=np.clip((curved-1000)/3500,0,1)
    mountain=np.maximum(mountain,np.clip(belt/.5,0,1))
    # Thickness can preserve broad plateaux, but does not force peak-filled interiors.
    local_relief=ndimage.maximum_filter(smooth,size=max(3,int(40000/spacing)))-ndimage.minimum_filter(smooth,size=max(3,int(40000/spacing)))
    mountain*=np.clip(local_relief/1200,.2,1)
    detail=np.zeros(shape)
    for km,ma,pa in zip((64,32,16,8,4,2),PARAMETERS['mountain_amplitudes_m'],PARAMETERS['plain_amplitudes_m']):
        noise=spatial_noise(shape,first,spacing,seeds[f'v2-relief-{km}km'],km*1000)
        detail += warped(noise)*(pa+(ma-pa)*mountain)
    # Always preserve known marine beds. Avoid generating negative coastal land
    # during this declared uplift stage; genuinely negative inland basins survive.
    result=surface+fade*(detail+belt*1900)
    positive=(base>=0)&~ocean
    result[positive]=np.maximum(result[positive],np.minimum(base[positive],2))
    result[ocean]=base[ocean]
    return result,belt*.0004,seeds,dict(PARAMETERS)
