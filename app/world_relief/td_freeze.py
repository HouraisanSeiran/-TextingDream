"""Freeze complete latent pages, then coarse diagnostic drainage; never erodes terrain."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from scipy import ndimage
from .td_pages import file_sha,stats,write_json
from .source import identity
from . import drainage


def assemble(directory,return_td=False):
    directory=Path(directory)
    plan=json.loads((directory/'world-plan.json').read_text())
    if identity({k:v for k,v in plan.items() if k!='plan_identity'})!=plan['plan_identity']:
        raise ValueError('plan identity mismatch')
    h=np.load(directory/'world-skeleton-960m.npy').copy()
    weight=np.load(directory/'world-td-weight.npy')
    if plan['algorithm']!='test-only':
        from .td_resident import world_plan
        source=Path(__file__).resolve().parents[2].parent/'山川形意Terragenesis/.scratch/plate-formation-coast-20261101/shaped-run-v4/product.npz'
        verified,skeleton,verified_weight=world_plan(source,plan['coast_buffer_m'])
        if verified!=plan or not np.array_equal(h,skeleton) or not np.array_equal(weight,verified_weight):
            raise ValueError('plan or CPU blend inputs differ from verified frozen plate')
        del skeleton,verified_weight
    if h.shape!=tuple(plan['shape_zx']) or weight.shape!=h.shape or not np.isfinite(h).all() or not np.isfinite(weight).all():
        raise ValueError('invalid CPU blend grids')
    skeleton_field=h.copy();td_field=np.full(h.shape,np.nan,np.float32)
    covered=np.zeros(h.shape,bool);records=[];seams=[]
    page_by_grid={tuple(p['grid_zx']):p for p in plan['pages']}
    for page in plan['pages']:
        dest=directory/'world-pages'/page['id']
        receipt=json.loads((dest/'receipt.json').read_text())
        expected={key:plan[key] for key in ('algorithm','plate_identity','world_seed','plan_identity')}
        expected.update({key:page[key] for key in ('id','origin_native_xz','grid_zx','side_native')})
        if any(receipt.get(key)!=value for key,value in expected.items()):
            raise ValueError('page request/plan/source mismatch')
        path=dest/'elevation_960m.npy'
        if file_sha(path)!=receipt['files'][path.name]:
            raise ValueError('page corrupt')
        a=np.load(path,allow_pickle=False)
        if a.shape!=(32,32) or not np.isfinite(a).all():
            raise ValueError('invalid page')
        z,x=page['grid_zx'];nz=min(30,h.shape[0]-z);nx=min(30,h.shape[1]-x)
        w=weight[z:z+nz,x:x+nx]
        h[z:z+nz,x:x+nx]=(a[:nz,:nx]*w+h[z:z+nz,x:x+nx]*(1-w)).astype(np.float32)
        td_field[z:z+nz,x:x+nx]=a[:nz,:nx]
        covered[z:z+nz,x:x+nx]=True
        records.append(receipt)
        for neighbor,axis in (((z,x+30),1),((z+30,x),0)):
            if neighbor not in page_by_grid:
                continue
            other=np.load(directory/'world-pages'/page_by_grid[neighbor]['id']/'elevation_960m.npy')
            s=stats(a[:,-2:] if axis else a[-2:,:],other[:,:2] if axis else other[:2,:])
            seams.append(dict(page=page['id'],neighbor=page_by_grid[neighbor]['id'],axis=axis,**s))
    if not np.all(covered[weight>0]) or not np.isfinite(h).all():
        raise ValueError('incomplete world coverage')
    max_seam=max(s['max_abs_m'] for s in seams) if seams else 0
    if max_seam>.01:
        raise ValueError(f'world overlap mismatch {max_seam}m')
    metrics=dict(pages=len(records),overlap_pairs=len(seams),overlap_max_abs_m=max_seam,
                 overlap_mae_m=float(np.mean([s['mae_m'] for s in seams])) if seams else 0,
                 sum_inference_seconds=sum(r['inference_seconds'] for r in records),
                 peak_child_rss_mib=max(r['peak_child_rss_mib'] for r in records),
                 allocated_peak_mib=max(r['allocated_peak_mib'] for r in records),
                 reserved_peak_mib=max(r['reserved_peak_mib'] for r in records),
                 minimum_resident_available_bytes=min(r['preflight']['available_host_bytes'] for r in records))
    write_json(directory/'world-seams.json',dict(metrics=metrics,pairs=seams))
    if return_td:
        return h,plan,metrics,skeleton_field,weight,td_field
    return h,plan,metrics


def _rings(mask):
    """Trace directed exposed pixel edges; four-neighbour components keep diagonal lakes apart."""
    nz,nx=mask.shape;edges={}
    def edge(a,b):
        edges.setdefault(a,[]).append(b)
    for z,x in np.argwhere(mask):
        z=int(z);x=int(x)
        if z==0 or not mask[z-1,x]:edge((x,z),(x+1,z))
        if x==nx-1 or not mask[z,x+1]:edge((x+1,z),(x+1,z+1))
        if z==nz-1 or not mask[z+1,x]:edge((x+1,z+1),(x,z+1))
        if x==0 or not mask[z,x-1]:edge((x,z+1),(x,z))
    rings=[]
    while edges:
        start=min(edges);current=start;previous=(start[0]-1,start[1]);ring=[start]
        while True:
            candidates=edges[current]
            incoming=(current[0]-previous[0],current[1]-previous[1])
            def priority(p):
                v=(p[0]-current[0],p[1]-current[1])
                cross=incoming[0]*v[1]-incoming[1]*v[0]
                dot=incoming[0]*v[0]+incoming[1]*v[1]
                return (2 if cross>0 else 1 if dot>0 else 0 if cross<0 else -1,p)
            nxt=max(candidates,key=priority)
            candidates.remove(nxt)
            if not candidates:del edges[current]
            previous,current=current,nxt;ring.append(current)
            if current==start:break
            if len(ring)>4*mask.size+1:raise ValueError('lake outline did not close')
        rings.append(ring)
    return rings


def lake_vectors(wet,filled,first,spacing):
    labels,n=ndimage.label(wet,structure=ndimage.generate_binary_structure(2,1))
    lakes=[]
    for label,bounds in enumerate(ndimage.find_objects(labels),1):
        if bounds is None:continue
        mask=labels[bounds]==label
        rings=_rings(mask)
        def signed_area(r):
            return sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(r,r[1:]))/2
        outer=[r for r in rings if signed_area(r)>0]
        holes=[r for r in rings if signed_area(r)<0]
        start_id=int(np.flatnonzero(mask)[0]);row,col=divmod(start_id,mask.shape[1])
        def coordinates(r):
            return [[float(first[0]+(x+bounds[1].start-.5)*spacing),
                     float(first[1]+(z+bounds[0].start-.5)*spacing)] for x,z in r]
        surfaces=filled[bounds][mask]
        for k,r in enumerate(outer):
            stable=hashlib.sha256(f'{first}:{spacing}:{bounds[0].start+row}:{bounds[1].start+col}:{k}'.encode()).hexdigest()[:20]
            lakes.append(dict(id='lake-'+stable,ring_xz_m=coordinates(r),holes_xz_m=[coordinates(h) for h in holes],
                surface_m=float(surfaces.max()),surface_range_m=[float(surfaces.min()),float(surfaces.max())],
                area_m2=int(mask.sum())*spacing**2,
                meaning='potential priority-flood inundation, not permanent water or balanced lake'))
    return sorted(lakes,key=lambda v:v['id'])


def standard_rivers(lines,ocean,closed,wet,first,spacing):
    nz,nx=ocean.shape;result=[]
    for line in lines:
        x,z=line['coordinates_xz_m'][-1]
        ix=int(round((x-first[0])/spacing));iz=int(round((z-first[1])/spacing))
        outlet='ocean' if ocean[iz,ix] else 'edge' if ix in (0,nx-1) or iz in (0,nz-1) else 'lake' if wet[iz,ix] else 'closed'
        result.append(dict(id=line['id'],points_xz_m=line['coordinates_xz_m'],downstream_id=line['downstream_id'],
            upstream_ids=line['upstream_ids'],drainage_area_m2=line['outlet_area_km2']*1e6,
            head_drainage_area_m2=line['head_area_km2']*1e6,outlet=outlet))
    by_id={v['id']:v for v in result}
    for item in result:
        current=item;seen=set()
        while current['downstream_id'] is not None:
            if current['id'] in seen:raise ValueError('cyclic river')
            seen.add(current['id']);current=by_id[current['downstream_id']]
        item['outlet']=current['outlet']
    return result


def freeze(directory):
    directory=Path(directory);started=time.perf_counter()
    h,plan,metrics=assemble(directory)
    product=directory/'world-960m';product.mkdir(parents=True,exist_ok=True)
    ocean=drainage.ocean_mask(h);closed=(h<0)&~ocean
    flow_start=time.perf_counter()
    flow=drainage.route(h,ocean,960,area_mode='mfd')
    flow_seconds=time.perf_counter()-flow_start
    filled=flow['filled_m'].astype(np.float32);wet=(filled-h>1e-5)&~ocean
    water=np.where(wet,filled,np.nan).astype(np.float32)
    status=np.where(ocean,3,np.where(closed,4,5)).astype(np.uint8)
    raw_lines=drainage.river_lines(flow,ocean,plan['first_sample_xz_m'],960)
    rivers=standard_rivers(raw_lines,ocean,closed,wet,plan['first_sample_xz_m'],960)
    lakes=lake_vectors(wet,filled,plan['first_sample_xz_m'],960)
    arrays=dict(elevation_m=h,status=status,ocean_mask=ocean,inland_depression_mask=closed,
        lake_surface_m=filled,water_surface_m=water,drainage_area_m2=flow['area_m2'].reshape(h.shape).astype(np.float32),
        receiver=flow['receiver'].reshape(h.shape).astype(np.int32))
    for name,a in arrays.items():np.save(product/(name+'.npy'),a,allow_pickle=False)
    write_json(product/'rivers.json',dict(schema='coordinate-river-segments-v1',lines=raw_lines))
    (product/'vectors').mkdir(exist_ok=True)
    write_json(product/'vectors/rivers.json',dict(schema='rivers-v1',lines=rivers))
    write_json(product/'vectors/lakes.json',dict(schema='lakes-v1',lakes=lakes))
    layers={}
    for name,unit,meaning in (('elevation_m','m','terrain low-frequency surface/bed, not water surface'),
        ('status','1','3 ocean; 4 closed below sea; 5 land'),('water_surface_m','m','potential priority-flood water surface; NaN dry'),
        ('drainage_area_m2','m2','MFD contributing area, NOT discharge')):
        path=product/(name+'.npy')
        layers[name]=dict(file=path.name,sha256=file_sha(path),dtype=str(arrays[name].dtype),unit=unit,meaning=meaning,nodata=None)
    vectors={kind:dict(file=f'vectors/{kind}.json',sha256=file_sha(product/f'vectors/{kind}.json'),schema=kind+'-v1') for kind in ('rivers','lakes')}
    generation=json.loads((directory/'generation-summary.json').read_text())
    upstream_root=Path(__file__).resolve().parents[2].parent/'山川形意Terragenesis'
    model_root=upstream_root/'models/terrain-diffusion-30m'
    td_source=dict(test_fixture=True) if plan['algorithm']=='test-only' else dict(model_manifest=json.loads((model_root/'manifest.json').read_text(encoding='utf-8')),
        model_config=json.loads((model_root/'config.json').read_text(encoding='utf-8')),
        model_config_sha256=file_sha(model_root/'config.json'),
        upstream=json.loads((upstream_root/'runtime/upstream.json').read_text(encoding='utf-8')),
        conditioning_spacing_m=7680,cond_snr=[.65,.1,1.,.1,1.],dtype='fp32',latents_batch_size=1,
        provenance_capture='at CPU freeze after generation; this run did not bind model/config/code signatures into per-page receipts',
        local_code_sha256={name:file_sha(Path(__file__).with_name(name)) for name in ('td_resident.py','td_pages.py','td_freeze.py','drainage.py')})
    manifest=dict(schema='td-world-960m-v1',producer='Terragenesis',algorithm_version=plan['algorithm'],
        lineage=[plan['plate_identity']],source_identity=plan['plate_identity'],world_seed=plan['world_seed'],
        subseed_method='No stochastic postprocessing; TD seed read from plate manifest',subseeds={},ready=True,
        grid=dict(first_sample_xz_m=plan['first_sample_xz_m'],spacing_m=960,shape_zx=plan['shape_zx'],semantics='cell-centre',
            axes='X east, Z south; arrays [z,x]',length_unit='m',sea_level_m=0),
        shape_zx=plan['shape_zx'],first_sample_xz_m=plan['first_sample_xz_m'],spacing_m=960,
        axes='arrays [z,x]; X east; Z south; metres; cell centres; sea=0',boundary='finite; no wrap',
        requested_domain_bounds_m=plan['extent_bounds_m'],plan_identity=plan['plan_identity'],layers=layers,vectors=vectors,
        declared_generated=['TD fifth latent channel low-frequency elevation at ~240m, inverse signed square then 4x4 metre-space mean to960m; NO30m decoder',
            'Plate conditioning samples periodically outside skeleton; finite output grid does not repeat continents',
            'Physical baseline climate used only as TD conditioning, rebased to plate; not a generated climate product',
            'Land plus80km Euclidean coastal buffer. Full TD to40km offshore, cubic smoothstep taper40..80km to periodic bilinear plate deep-ocean bed',
            'Four-neighbour negative ocean connected to finite domain rim; disconnected negative cells remain inland',
            'Priority-flood routing surface, MFD slope^1.1 contributing area, single receiver river lines at300km2 threshold; terrain NOT eroded or filled',
            'Potential lake pixel-edge polygons with holes; priority-flood diagnostic, no water balance'],
        limitations=['World low-frequency approximation is not exact30m decoder average; coastline/valley depth may differ',
            '960m D8 receiver direction bias, MFD area is not discharge; no real precipitation-runoff simulation',
            'Lake surface/inundation is potential flood level, not permanent water. Boundary-crossing basins drain through finite rim',
            'Physical climate rebase inherits clipping and is approximate; no climate/biome layer exposed',
            'Native block-centre alignment leaves a sub-cell finite rim margin; no extrapolation of output queries'],
        resource_policy=dict(cold_launch='available >=4096MiB worker + staging',resident_page='available >=staging+1024MiB safety; worker RSS <=4096MiB independently',
            staging_bytes=467772160,cold_required_bytes=4762739456,resident_required_bytes=1541513984,
            gpu_cap_mib=4096,worker_rss_cap_mib=4096,per_page_deadline_s=120,gpu_scope='PyTorch allocator only',rss_scope='sampled every0.25s'),
        statistics=dict(**metrics,routing_seconds=flow_seconds,postprocessing_seconds=time.perf_counter()-started,
            river_segments=len(rivers),potential_lakes=len(lakes),ocean_cells=int(ocean.sum()),closed_below_sea_cells=int(closed.sum()),
            elevation_min_m=float(h.min()),elevation_max_m=float(h.max())),generation=generation,td_source=td_source,
        files={p.name:file_sha(p) for p in product.glob('*.npy')})
    manifest['files']['rivers.json']=file_sha(product/'rivers.json')
    manifest['identity']=identity(manifest)
    write_json(product/'manifest.json',manifest)
    print('FROZEN '+manifest['identity']+' routing_seconds='+str(flow_seconds),flush=True)
    return product,manifest
