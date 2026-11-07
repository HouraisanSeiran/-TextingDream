"""Authorized periodic-conditioning latent world build. No 30m decoder or game integration."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from app.world_relief.td_pages import add_upstream,stats,write_json
from app.world_relief.td_resident import generate_pages,world_plan,ALGORITHM
from app.world_relief.source import identity
from tools.build_td_world import comparison


def smoke(terra,source,output):
    pages=[dict(id=f'p{z}{x}',origin_native_xz=[-26880+x*960,-3200+z*960],side_native=1024) for z in range(2) for x in range(2)]
    spec=dict(algorithm=ALGORITHM,pages=pages,purpose='test-boundary-smoke')
    records=generate_pages(terra,source,pages,output/'smoke-periodic',purpose='test',plan_identity=identity(spec))
    arrays={p['id']:np.load(output/'smoke-periodic'/p['id']/'elevation_960m.npy') for p in pages}
    seams=[]
    for a,b,axis in (('p00','p01',1),('p10','p11',1),('p00','p10',0),('p01','p11',0)):
        left=arrays[a][:,-2:] if axis else arrays[a][-2:,:]
        right=arrays[b][:,:2] if axis else arrays[b][:2,:]
        seams.append(dict(pages=[a,b],axis=axis,**stats(left,right)))
    mosaic=np.block([[arrays['p00'][:30,:30],arrays['p01'][:30,:30]],
                     [arrays['p10'][:30,:30],arrays['p11'][:30,:30]]])
    edge=(np.abs(np.diff(mosaic,axis=1)))
    # Boundary at X=-800km falls between output sample columns 6 and 7.
    index=int(np.floor((-800000-(-26880*30+465))/960))
    boundary=edge[:,index]
    base=float(np.quantile(edge,.99))
    result=dict(schema='dream-td-periodic-smoke-v1',purpose='test',records=records,seams=seams,
        crosses_skeleton_x_m=-800000,first_sample_xz_m=[-26880*30+465,-3200*30+465],
        boundary_neighbor_max_m=float(boundary.max()),boundary_neighbor_p99_m=float(np.quantile(boundary,.99)),
        window_neighbor_p99_m=base,window_neighbor_max_m=float(edge.max()),
        limitations=['Boundary test checks local continuity, not equality of opposite output edges; final DEM remains finite',
        '960m latent low-frequency approximation, not decoded terrain'],
        ready=all(s['max_abs_m']<=.01 for s in seams) and float(boundary.max())<=max(200,base*5))
    write_json(output/'smoke-periodic/result.json',result)
    np.save(output/'smoke-periodic/mosaic_960m.npy',mosaic,allow_pickle=False)
    comparison(output/'boundary-smoke.png',[mosaic],['Periodic conditioning: 2x2 latent pages across X=-800km'])
    print('SMOKE '+json.dumps({k:v for k,v in result.items() if k!='records'}),flush=True)
    if not result['ready']:
        raise ValueError('Boundary smoke seam/continuity check failed')
    if max(r['inference_seconds'] for r in records)>60:
        raise ValueError('Smoke page inference >60s, unexpected throughput; stop before world')
    return result


def main():
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('stage',choices=['smoke','generate','all'])
    p.add_argument('--terra',default=str(ROOT.parent/'山川形意Terragenesis'))
    p.add_argument('--output',default=str(ROOT/'artifacts/td-world'))
    args=p.parse_args();terra=Path(args.terra);output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    add_upstream(terra)
    source=terra/'.scratch/plate-formation-coast-20261101/shaped-run-v4/product.npz'
    if args.stage in ('smoke','all'):
        smoke(terra,source,output)
    if args.stage in ('generate','all'):
        result=json.loads((output/'smoke-periodic/result.json').read_text())
        if not result['ready']:
            raise ValueError('Must pass periodic boundary smoke before generation')
        spec,skeleton,weight=world_plan(source)
        write_json(output/'world-plan.json',spec)
        np.save(output/'world-skeleton-960m.npy',skeleton,allow_pickle=False)
        np.save(output/'world-td-weight.npy',weight,allow_pickle=False)
        del skeleton,weight
        print(f'WORLD PLAN {len(spec["pages"])} pages; shape {spec["shape_zx"]}; identity {spec["plan_identity"]}',flush=True)
        started=time.perf_counter()
        records=generate_pages(terra,source,spec['pages'],output/'world-pages',purpose='world',plan_identity=spec['plan_identity'])
        write_json(output/'generation-summary.json',dict(algorithm=ALGORITHM,plan_identity=spec['plan_identity'],
            world_seed=spec['world_seed'],plate_identity=spec['plate_identity'],completed_pages=len(records),
            total_pages=len(spec['pages']),elapsed_seconds_this_invocation=time.perf_counter()-started,
            sum_page_inference_seconds=sum(r['inference_seconds'] for r in records),
            sum_page_wall_seconds=sum(r['page_wall_seconds'] for r in records),
            peak_child_rss_mib=max(r['peak_child_rss_mib'] for r in records),
            allocated_peak_mib=max(r['allocated_peak_mib'] for r in records),
            reserved_peak_mib=max(r['reserved_peak_mib'] for r in records)))
        print('WORLD GENERATION COMPLETE',flush=True)


if __name__=='__main__':
    main()
