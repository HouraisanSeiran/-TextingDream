"""Finite D8 priority flood, acyclic receivers and sparse triangular accumulation."""
import heapq
from collections import deque
import hashlib
import numpy as np
from scipy import ndimage, sparse
from scipy.sparse.linalg import spsolve_triangular

NEIGHBORS = ((-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1))

def ocean_mask(elevation, candidate=None):
    wet = elevation < 0 if candidate is None else candidate
    seeds = np.zeros(wet.shape,bool)
    seeds[0] = wet[0]; seeds[-1] = wet[-1]; seeds[:,0] = wet[:,0]; seeds[:,-1] = wet[:,-1]
    return ndimage.binary_propagation(seeds,mask=wet,structure=ndimage.generate_binary_structure(2,1))

def route(elevation, ocean, spacing, area_mode='d8'):
    """Priority flood with FIFO depression interiors; outlets are ocean and domain rim.

    Receivers on filled flats follow the flood parent, hence have strictly lower
    flood rank. D8 steeper receivers may replace parents only at lower rank.
    Original bed is never filled: flood surface is routing/water level only.
    """
    nz,nx = elevation.shape; n = elevation.size
    filled = elevation.ravel().copy(); seen = ocean.copy()
    seen[0] = True; seen[-1] = True; seen[:,0] = True; seen[:,-1] = True
    outlets = seen.ravel().copy()
    receiver = np.arange(n,dtype=np.int32)
    ids = np.flatnonzero(seen.ravel())
    heap = [(float(filled[i]),int(i)) for i in ids]; heapq.heapify(heap)
    queue = deque(); order = np.empty(n,np.int32); count = 0
    visited = seen.ravel()
    while heap or queue:
        if queue:
            i = queue.popleft(); h = filled[i]
        else:
            h,i = heapq.heappop(heap)
        order[count] = i; count += 1
        z,x = divmod(i,nx)
        for dz,dx in NEIGHBORS:
            zz,xx = z+dz,x+dx
            if zz < 0 or zz >= nz or xx < 0 or xx >= nx:
                continue
            j = zz*nx+xx
            if visited[j]:
                continue
            visited[j] = True; receiver[j] = i
            if filled[j] <= h:
                filled[j] = h; queue.append(j)
            else:
                heapq.heappush(heap,(float(filled[j]),j))
    rank = np.empty(n,np.int32); rank[order] = np.arange(n,dtype=np.int32)
    f = filled.reshape(nz,nx); r = rank.reshape(nz,nx)
    best = np.zeros((nz,nx))
    rec = receiver.reshape(nz,nx)
    for dz,dx in NEIGHBORS:
        a = (slice(max(0,-dz),min(nz,nz-dz)),slice(max(0,-dx),min(nx,nx-dx)))
        b = (slice(max(0,dz),min(nz,nz+dz)),slice(max(0,dx),min(nx,nx+dx)))
        slope = (f[a]-f[b])/(spacing*np.hypot(dz,dx))
        take = (slope > best[a]) & (r[b] < r[a]) & ~outlets.reshape(nz,nx)[a]
        rz,rx = np.indices(slope.shape)
        neighbor = (rz+max(0,dz))*nx+rx+max(0,dx)
        rec[a][take] = neighbor[take]; best[a][take] = slope[take]
    parent = rank[receiver[order]]
    rows = np.arange(n); valid = parent != rows
    # Matrix in downstream-first flood order: each row points to an earlier receiver.
    transfer = sparse.csr_matrix((np.ones(valid.sum()),(rows[valid],parent[valid])),shape=(n,n))
    unit = sparse.eye(n,format='csr')
    area_sorted = spsolve_triangular((unit-transfer).T.tocsr(),np.full(n,spacing*spacing),lower=False,unit_diagonal=True)
    area = np.empty(n); area[order] = area_sorted
    if area_mode == 'mfd':
        area = mfd_area(f,rank.reshape(nz,nx),receiver,order,outlets,spacing)
    elif area_mode != 'd8':
        raise ValueError('Unknown accumulation mode')
    dist = np.hypot(receiver//nx-np.arange(n)//nx,receiver%nx-np.arange(n)%nx)*spacing
    return dict(area_mode=area_mode,receiver=receiver,order=order,parent=parent,transfer=transfer,area_m2=area.reshape(nz,nx),filled_m=f,closed_mask=(f-elevation>1e-5)&~ocean,distance_m=dist)

def mfd_area(filled,rank,receiver,order,outlets,spacing):
    """Slope^1.1 multiple-flow accumulation; flood-parent fallback on flats."""
    nz,nx=filled.shape;n=filled.size
    sources=[];targets=[];weights=[]
    for dz,dx in NEIGHBORS:
        a=(slice(max(0,-dz),min(nz,nz-dz)),slice(max(0,-dx),min(nx,nx-dx)))
        b=(slice(max(0,dz),min(nz,nz+dz)),slice(max(0,dx),min(nx,nx+dx)))
        slope=(filled[a]-filled[b])/(spacing*np.hypot(dz,dx))
        valid=(slope>1e-12)&(rank[b]<rank[a])&~outlets.reshape(nz,nx)[a]
        sources.append(rank[a][valid]);targets.append(rank[b][valid]);weights.append(slope[valid]**1.1)
    src=np.concatenate(sources);dst=np.concatenate(targets);w=np.concatenate(weights)
    total=np.bincount(src,weights=w,minlength=n)
    rows=np.arange(n);parent=rank.ravel()[receiver[order]]
    flat=(total==0)&(parent!=rows)
    src=np.concatenate((src,rows[flat]));dst=np.concatenate((dst,parent[flat]));w=np.concatenate((w,np.ones(flat.sum())))
    total[flat]=1;w/=total[src]
    transfer=sparse.csr_matrix((w,(src,dst)),shape=(n,n))
    matrix=(sparse.eye(n,format='csr')-transfer).T.tocsr()
    values=spsolve_triangular(matrix,np.full(n,spacing*spacing),lower=False,unit_diagonal=True)
    area=np.empty(n);area[order]=values
    return area


def river_lines(flow, ocean, first, spacing, threshold_m2=300e6):
    rec = flow['receiver']; area = flow['area_m2'].ravel(); nx = ocean.shape[1]
    active = (area >= threshold_m2) & ~ocean.ravel() & (rec != np.arange(rec.size))
    if flow.get('area_mode')=='mfd':
        order=flow['order'];n=rec.size
        matrix=(sparse.eye(n,format='csr')-flow['transfer']).T.tocsr()
        touched=spsolve_triangular(matrix,active[order].astype(float),lower=False,unit_diagonal=True)
        downstream=np.empty(n,bool);downstream[order]=touched>0
        active=downstream&~ocean.ravel()&(rec!=np.arange(n))
    indegree = np.bincount(rec[active],minlength=rec.size)
    starts = np.flatnonzero(active & (indegree != 1))
    def stable(i):
        x = first[0]+(int(i)%nx)*spacing; z = first[1]+(int(i)//nx)*spacing
        return 'r-'+hashlib.sha256(f'{x:.3f},{z:.3f}'.encode()).hexdigest()[:20]
    lines = []
    for start in starts:
        path = [int(start)]; end = int(rec[start]); path.append(end)
        while active[end] and indegree[end] == 1:
            end = int(rec[end]); path.append(end)
        coords = [[first[0]+(i%nx)*spacing,first[1]+(i//nx)*spacing] for i in path]
        lines.append(dict(id=stable(start),downstream_id=stable(end) if active[end] else None,coordinates_xz_m=coords,head_area_km2=float(area[start]/1e6),outlet_area_km2=float(area[end]/1e6)))
    upstream = {line['id']:[] for line in lines}
    for line in lines:
        if line['downstream_id'] in upstream:
            upstream[line['downstream_id']].append(line['id'])
    for line in lines:
        line['upstream_ids'] = sorted(upstream[line['id']])
    return sorted(lines,key=lambda line:line['id'])
