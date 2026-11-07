"""Descriptive grid-anisotropy metrics, not a claim of natural drainage."""
import numpy as np
from scipy import ndimage


def mountain_directions(h,receiver,area,spacing):
    nz,nx=h.shape;ids=np.arange(h.size);rec=receiver.ravel()
    dz=rec//nx-ids//nx;dx=rec%nx-ids%nx
    gy,gx=np.gradient(h,spacing)
    mountain=(h>1500)&(ndimage.maximum_filter(np.hypot(gx,gy),size=7)>.02)
    channel=mountain.ravel()&(area.ravel()>=50e6)&(rec!=ids)
    angle=np.mod(np.degrees(np.arctan2(dz,dx)),180)
    values,counts=np.unique(angle[channel],return_counts=True)
    step_distribution={str(round(float(a),3)):float(n/max(1,channel.sum())) for a,n in zip(values,counts)}
    # Ten-cell reach displacement measures macroscopic turning; individual D8
    # steps are necessarily in multiples of 45 degrees (100%, by definition).
    end=ids.copy()
    for _ in range(10):
        end=rec[end]
    reach_angle=np.mod(np.degrees(np.arctan2(end//nx-ids//nx,end%nx-ids%nx)),180)
    reach_angle=reach_angle[channel]
    grid_distance=np.abs((reach_angle+22.5)%45-22.5)
    near_axis=float(np.mean(grid_distance<=5)) if len(reach_angle) else None
    orientation=np.full(h.size,-1,np.int8)
    orientation[channel]=np.rint(angle[channel]/45).astype(np.int8)%4
    orientation=orientation.reshape(h.shape)
    # Perpendicular offsets compare distinct similarly oriented channel traces,
    # rather than measuring spacing along one receiver chain.
    nearest=np.full(h.shape,np.inf)
    for code,(oz,ox) in enumerate(((1,0),(1,-1),(0,1),(1,1))):
        for sign in (-1,1):
            for k in range(2,max(3,int(20000/spacing))+1):
                zz,xx=oz*k*sign,ox*k*sign
                a=(slice(max(0,-zz),min(nz,nz-zz)),slice(max(0,-xx),min(nx,nx-xx)))
                b=(slice(max(0,zz),min(nz,nz+zz)),slice(max(0,xx),min(nx,nx+xx)))
                pair=(orientation[a]==code)&(orientation[b]==code)
                nearest[a][pair]=np.minimum(nearest[a][pair],k*spacing*np.hypot(oz,ox))
    distances=nearest[np.isfinite(nearest)]/1000
    return dict(mountain_channel_area_threshold_km2=50,mountain_definition='h>1500m and max local slope within 7 cells >0.02',mountain_channel_cells=int(channel.sum()),single_step_orientation_mod180_fraction=step_distribution,single_step_grid_angles_fraction=1.0,ten_cell_reach_within_5deg_of_grid_angles_fraction=near_axis,parallel_neighbor_definition='same D8 orientation at perpendicular offsets 2..20 km; local trace estimate, not distinct named rivers',parallel_neighbor_distance_km_quantiles=dict(zip(('p10','p50','p90'),np.percentile(distances,[10,50,90]).tolist())) if len(distances) else {},parallel_neighbor_fraction=float(len(distances)/max(1,channel.sum())))
