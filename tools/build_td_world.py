"""TD world experiments. CPU S0; upstream CUDA interpreter S1. No implicit generation."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from scipy import ndimage
from app.world_relief.td_pages import block_mean, stats, write_json, run_page, add_upstream, PLATE_IDENTITY


def comparison(path, arrays, titles, spacing=960):
    from PIL import Image, ImageDraw
    panel=620; header=60; footer=30
    canvas=Image.new('RGB',(panel*len(arrays),header+panel+footer),'white')
    draw=ImageDraw.Draw(canvas)
    stops=np.array([-6000,-2000,-1,0,300,1000,2500,5000,10000],float)
    colours=np.array([[22,45,82],[42,88,132],[111,174,195],[91,143,100],[145,170,104],
                      [186,178,129],[161,145,127],[211,208,200],[250,250,248]],float)
    # Fixed physical colour stops and fixed illumination for every panel.
    for k,(a,title) in enumerate(zip(arrays,titles)):
        rgb=np.stack([np.interp(a,stops,colours[:,i]) for i in range(3)],axis=-1)
        gz,gx=np.gradient(a.astype(float),spacing)
        light=np.clip((1-.6*gx-.6*gz)/np.sqrt(1+gx*gx+gz*gz),0,1)
        rgb=np.clip(rgb*(.45+.55*light[:,:,None]),0,255).astype('uint8')
        image=Image.fromarray(rgb).resize((panel,panel),resample=Image.Resampling.NEAREST)
        canvas.paste(image,(k*panel,header))
        draw.text((k*panel+12,12),title,fill='black')
        draw.text((k*panel+12,34),f'{a.shape[1]*spacing/1000:.2f} x {a.shape[0]*spacing/1000:.2f} km; 960m grid',fill='black')
        draw.text((k*panel+12,header+panel+8),f'elevation {a.min():.1f} .. {a.max():.1f} m; X east / Z south',fill='black')
    canvas.save(path)


def s0(args):
    t=time.perf_counter()
    fixture=Path(args.terra)/'.scratch/river-upgrade-20261101/terrain-v3'
    manifest=json.loads((fixture/'manifest.json').read_text())
    native=np.load(fixture/'raw_td_m.npy',mmap_mode='r')
    td=block_mean(native,32)
    first=np.array(manifest['origin_native_xz'])*30+465
    pilot=ROOT/'artifacts/world-relief-pilot-v2'
    pm=json.loads((pilot/'manifest.json').read_text())
    v2=np.load(pilot/'elevation_m.npy',mmap_mode='r')
    zz,xx=np.meshgrid(first[1]+np.arange(td.shape[0])*960,first[0]+np.arange(td.shape[1])*960,indexing='ij')
    old=ndimage.map_coordinates(v2,[(zz-pm['first_sample_xz_m'][1])/pm['spacing_m'],(xx-pm['first_sample_xz_m'][0])/pm['spacing_m']],order=1,mode='nearest')
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    comparison(output/'s0-compare.png',[old,td],['v2 noise + erosion (same window)','Frozen TD 30m -> 960m block mean'])
    np.save(output/'s0-td-960m.npy',td,allow_pickle=False)
    write_json(output/'s0-comparison.json',dict(purpose='test',source_identity=manifest['identity'],v2_identity=pm['identity'],
        shape_zx=list(td.shape),first_sample_xz_m=first.tolist(),spacing_m=960,block_factor=32,
        comparison=stats(td,old),td_range_m=[float(td.min()),float(td.max())],v2_range_m=[float(old.min()),float(old.max())],
        elapsed_seconds=time.perf_counter()-t,limitations=['v2 interpolated from 1000m at identical TD block centres; descriptive difference, not accuracy',
        'shared colour scale and illumination; no independently verified ground truth']))
    print(json.dumps(json.loads((output/'s0-comparison.json').read_text()),indent=2),flush=True)


def select_origin(terra,source,side):
    add_upstream(terra)
    from diffusion.plate_td_conditioning import conditioning_footprint
    from app.world_relief.source import load_source
    fields,_=load_source(source)
    a=fields['elevation_m']; candidates=[]
    for z,x in np.argwhere(a>1000):
        xm=-800000+(int(x)+.5)*10000
        zm=-640000+(int(z)+.5)*10000
        origin=(int(np.floor(xm/960))*32,int(np.floor(zm/960))*32)
        # 2x2 pages each overlap by 64 native samples.
        footprints=[conditioning_footprint((origin[0]+dx*(side-64),origin[1]+dz*(side-64)),side) for dz in range(2) for dx in range(2)]
        if all(f[0]*7680>=-795000 and (f[2]-1)*7680<=795000 and f[1]*7680>=-635000 and (f[3]-1)*7680<=635000 for f in footprints):
            candidates.append((float(a[z,x]),origin,footprints))
    if not candidates:
        raise ValueError('No mountain test site has full finite conditioning support')
    value,origin,footprints=max(candidates)
    return origin,dict(skeleton_elevation_m=value,origin_native_xz=list(origin),footprints=footprints)


def estimate(args,source,benchmark):
    from app.world_relief.source import load_source
    fields,_=load_source(source)
    a=fields['elevation_m']
    mask=ndimage.binary_dilation(a>=0,iterations=8)
    core=960; width=core*30
    nz=int(np.ceil(1280000/width));nx=int(np.ceil(1600000/width))
    count=valid=0
    from diffusion.plate_td_conditioning import conditioning_footprint
    for z in range(nz):
        for x in range(nx):
            x0=-800000+x*width;z0=-640000+z*width
            sx=slice(max(0,int((x0+800000)//10000)),min(160,int(np.ceil((x0+width+800000)/10000))))
            sz=slice(max(0,int((z0+640000)//10000)),min(128,int(np.ceil((z0+width+640000)/10000))))
            if not mask[sz,sx].any():
                continue
            count+=1
            origin=(int(np.floor(x0/960))*32,int(np.floor(z0/960))*32)
            f=conditioning_footprint(origin,1024)
            valid+=int(f[0]*7680>=-795000 and (f[2]-1)*7680<=795000 and f[1]*7680>=-635000 and (f[3]-1)*7680<=635000)
    times=[r['wall_seconds'] for r in benchmark.get('pages',[]) if r['mode']=='latent']
    result=dict(page_side_native=1024,core_side_native=core,coastal_buffer_m=80000,
        coverage='skeleton elevation >=0 plus 8 four-neighbour 10km dilation steps; page bounding boxes',
        required_pages=count,finite_conditioning_pages=valid,unsupported_conditioning_pages=count-valid,
        estimated_seconds=count*max(times) if times else None,
        estimated_best_observed_seconds=count*min(times) if times else None,
        estimated_inference_only_seconds=count*min([r['inference_seconds'] for r in benchmark.get('pages',[]) if r['mode']=='latent']) if times else None,
        estimate_status='partial S1: two latent pages and one decoded page; not a completed benchmark',
        estimation='conservative per-page wall including cold model loading; only if latent accepted',
        world_shape_zx=[1333,1666],world_spacing_m=960,world_full_layers_estimated_bytes=1333*1666*38,
        blockers=['Upstream factory rejects conditioning outside finite skeleton. No edge extrapolation is authorized.'] if valid<count else [])
    write_json(Path(args.output)/'s2-estimate.json',result)
    return result


def s1(args):
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    source=Path(args.terra)/'.scratch/plate-formation-coast-20261101/shaped-run-v4/product.npz'
    origin,site=select_origin(args.terra,source,args.side)
    report=dict(schema='dream-td-benchmark-1',purpose='test',world_seed=20261020,plate_identity=PLATE_IDENTITY,
        site=site,pages=[],status='running',limitations=['No local 30m production layer; test exemption only',
        'Low-frequency latent is not the exact average of full decoder output'])
    write_json(output/'s1-benchmark.json',report)
    print('SITE '+json.dumps(site),flush=True)
    try:
        for dz,dx in ((0,0),(0,1),(1,0),(1,1)):
            pos=(origin[0]+dx*(args.side-64),origin[1]+dz*(args.side-64))
            tag=f'p{dz}{dx}'
            for mode in ('latent','decoded'):
                dest=output/'test-pages'/tag/mode
                record=run_page(args.terra,source,pos,dest,side=args.side,mode=mode)
                report['pages'].append(dict(page=tag,**record))
                write_json(output/'s1-benchmark.json',report)
                print(f'PAGE {tag} {mode}: '+json.dumps(record),flush=True)
            latent=np.load(output/'test-pages'/tag/'latent/elevation_960m.npy')
            decoded=np.load(output/'test-pages'/tag/'decoded/elevation_960m.npy')
            report.setdefault('latent_vs_decoded',{})[tag]=stats(latent,decoded)
            comparison(output/(tag+'-latent-vs-decoded.png'),[latent,decoded],['TD latent low-frequency -> 960m','TD full 30m decoder -> 960m'])
            write_json(output/'s1-benchmark.json',report)
        seams=[]
        for mode in ('latent','decoded'):
            layer='elevation_30m.npy' if mode=='decoded' else 'elevation_960m.npy'
            overlap=64 if mode=='decoded' else 2
            pages={tag:np.load(output/'test-pages'/tag/mode/layer) for tag in ('p00','p01','p10','p11')}
            for a,b,axis in (('p00','p01',1),('p10','p11',1),('p00','p10',0),('p01','p11',0)):
                left=pages[a][:,-overlap:] if axis else pages[a][-overlap:,:]
                right=pages[b][:,:overlap] if axis else pages[b][:overlap,:]
                seams.append(dict(mode=mode,pages=[a,b],axis=axis,**stats(left,right)))
            n=pages['p00'].shape[0]-overlap
            mosaic=np.block([[pages['p00'][:n,:n],pages['p01'][:n,:n]],
                             [pages['p10'][:n,:n],pages['p11'][:n,:n]]])
            if mode=='decoded':
                mosaic=block_mean(mosaic,32)
            np.save(output/(mode+'-mosaic-960m.npy'),mosaic,allow_pickle=False)
        report['seams']=seams
        comparison(output/'s1-seams.png',[np.load(output/'latent-mosaic-960m.npy'),np.load(output/'decoded-mosaic-960m.npy')],
                   ['Latent 2x2 test pages','Decoded 2x2 test pages'])
        report['status']='completed'
        report['s2_estimate']=estimate(args,source,report)
    except BaseException as exc:
        report['status']='blocked';report['error']=str(exc)
        try:
            report['s2_estimate']=estimate(args,source,report)
        except Exception as estimate_error:
            report['estimate_error']=str(estimate_error)
        raise
    finally:
        write_json(output/'s1-benchmark.json',report)


def partial_analysis(output):
    """Summarize only completed test pages, without triggering GPU generation."""
    output=Path(output)
    report=json.loads((output/'s1-benchmark.json').read_text())
    a=np.load(output/'test-pages/p00/latent/elevation_960m.npy')
    b=np.load(output/'test-pages/p01/latent/elevation_960m.npy')
    report['partial_seams']=[dict(mode='latent',pages=['p00','p01'],axis=1,
        overlap_native_points=64,**stats(a[:,-2:],b[:,:2]))]
    mosaic=np.concatenate([a[:,:-2],b],axis=1)
    # Preserve actual aspect ratio with a separate compact image of the seam.
    from PIL import Image,ImageDraw
    q=np.clip((mosaic-2500)/5500*255,0,255).astype('uint8')
    im=Image.fromarray(q).convert('RGB').resize((1240,640),Image.Resampling.NEAREST)
    draw=ImageDraw.Draw(im)
    line=int(30/62*1240)
    draw.line((line,0,line,640),fill='red',width=1)
    im.save(output/'s1-partial-latent-seam.png')
    report['visual_review']={
        's0':'TD has more irregular coastline and small slope/valley structure than v2; nearest-pixel 960m display is stair-stepped. Does not establish seam absence.',
        'p00':'Low-frequency latent follows the broad ridge and valley pattern of decoded terrain but is smoother and suppresses valley depth. One all-positive mountain window cannot validate coastal sign agreement.',
        'status':'Partial benchmark only. No completed 2x2 decoded seam or world imagery.'}
    class Args:
        pass
    args=Args();args.output=str(output)
    source=ROOT.parent/'山川形意Terragenesis/.scratch/plate-formation-coast-20261101/shaped-run-v4/product.npz'
    report['s2_estimate']=estimate(args,source,report)
    write_json(output/'s1-benchmark.json',report)
    print(json.dumps(dict(partial_seams=report['partial_seams'],estimate=report['s2_estimate']),indent=2))


def supplemental_report(output):
    """CPU-only coverage and hypothetical throughput; never invokes a worker."""
    output=Path(output)
    from app.world_relief.source import load_source
    from diffusion.plate_td_conditioning import conditioning_footprint
    from PIL import Image,ImageDraw
    report=json.loads((output/'s1-benchmark.json').read_text())
    a=np.load(output/'test-pages/p00/latent/elevation_960m.npy')
    b=np.load(output/'test-pages/p00/decoded/elevation_960m.npy')
    comparison(output/'s1-latent-vs-decoded.png',[a,b],['Latent low frequency -> 960m','30m decoded -> 960m'])
    existing=Image.open(output/'s1-latent-vs-decoded.png').convert('RGB')
    result=Image.new('RGB',(1860,710),'white');result.paste(existing,(0,0))
    d=a-b;limit=max(1,float(np.abs(d).max()));v=np.clip(d/limit,-1,1)
    rgb=np.empty(d.shape+(3,),dtype='uint8')
    rgb[:,:,0]=255-np.maximum(-v,0)*220;rgb[:,:,1]=255-np.abs(v)*220;rgb[:,:,2]=255-np.maximum(v,0)*220
    result.paste(Image.fromarray(rgb).resize((620,620),Image.Resampling.NEAREST),(1240,60))
    draw=ImageDraw.Draw(result);draw.text((1252,12),'Difference: latent - decoded (m)',fill='black')
    draw.text((1252,34),f'Blue negative / white zero / red positive; +/-{limit:.1f}m',fill='black')
    draw.text((1252,688),f'MAE {np.abs(d).mean():.2f}m; RMSE {np.sqrt((d*d).mean()):.2f}m',fill='black')
    result.save(output/'s1-latent-vs-decoded.png')
    source=ROOT.parent/'山川形意Terragenesis/.scratch/plate-formation-coast-20261101/shaped-run-v4/product.npz'
    fields,_=load_source(source);h=fields['elevation_m'];land=h>=0
    mask=ndimage.binary_dilation(land,iterations=8)
    nx=int(np.ceil(1600000/28800));nz=int(np.ceil(1280000/28800))
    grid=np.zeros((nz,nx),np.uint8);coasts=[];valid_centres=[]
    # A coastal page core contains both signs in the bilinearly sampled skeleton.
    local=(np.arange(30)+.5)*960
    for z in range(nz):
        for x in range(nx):
            x0=-800000+x*28800;z0=-640000+z*28800
            sx=slice(max(0,int((x0+800000)//10000)),min(160,int(np.ceil((x0+28800+800000)/10000))))
            sz=slice(max(0,int((z0+640000)//10000)),min(128,int(np.ceil((z0+28800+640000)/10000))))
            if not mask[sz,sx].any():
                continue
            origin=(int(np.floor(x0/960))*32,int(np.floor(z0/960))*32)
            f=conditioning_footprint(origin,1024)
            valid=f[0]*7680>=-795000 and (f[2]-1)*7680<=795000 and f[1]*7680>=-635000 and (f[3]-1)*7680<=635000
            grid[z,x]=1
            if valid:
                zz,xx=np.meshgrid((z0+local+640000)/10000-.5,(x0+local+800000)/10000-.5,indexing='ij')
                sample=ndimage.map_coordinates(h,[zz,xx],order=1,mode='nearest')
                coastal=bool((sample<0).any() and (sample>=0).any())
                grid[z,x]=3 if coastal else 2
                coasts.append(coastal);valid_centres.append([x0+14400,z0+14400])
    colors=np.array([[224,232,237],[207,130,116],[87,151,108],[239,195,60]],dtype='uint8')
    im=Image.fromarray(colors[grid]).resize((896,720),Image.Resampling.NEAREST)
    canvas=Image.new('RGB',(920,820),'white');canvas.paste(im,(12,60))
    draw=ImageDraw.Draw(canvas)
    draw.text((12,10),'S2 candidate pages: finite conditioning coverage (X east, Z south)',fill='black')
    draw.text((12,30),'Grey deep ocean skipped; red unsupported; green supported; yellow supported coast',fill='black')
    draw.text((12,788),'Extent: X -800..800 km; Z -640..640 km. Each cell: nominal 28.8km page core.',fill='black')
    canvas.save(output/'s2-page-coverage.png')
    centres=np.array(valid_centres)
    n=int((grid>0).sum())
    latent=[r for r in report['pages'] if r['mode']=='latent'];decoded=[r for r in report['pages'] if r['mode']=='decoded']
    lt=float(np.mean([r['inference_seconds'] for r in latent]));dt=float(np.mean([r['inference_seconds'] for r in decoded]))
    load=max(r['model_loading_seconds'] for r in report['pages'])
    extra=dict(
        resident_worker_estimates=dict(required_pages=n,assumed_fixed_overhead_seconds_per_page=2,
            overhead_assumption='CPU averaging/output/checkpoint/IPC estimate, not measured; model import startup excluded; per-page preflight still required',
            latent=dict(mean_inference_seconds=lt,total_seconds=load+n*(lt+2),hours=(load+n*(lt+2))/3600),
            decoded=dict(mean_inference_seconds=dt,total_seconds=load+n*(dt+2),hours=(load+n*(dt+2))/3600),
            once_model_load_seconds=load,limitation='Hypothetical persistent worker, not implemented or benchmarked. Unmodified per-page 120s/RSS/GPU budgets remain requirements.'),
        coverage=dict(required_pages=n,supported_pages=int((grid>=2).sum()),supported_coastal_pages=int(np.sum(coasts)),
            coastal_definition='page core has both negative and nonnegative bilinearly sampled skeleton elevations, sampled at 960m; not TD shoreline',
            supported_page_centres_x_range_m=[float(centres[:,0].min()),float(centres[:,0].max())],
            supported_page_centres_z_range_m=[float(centres[:,1].min()),float(centres[:,1].max())],
            hypothetical_wrap_supported_pages=n,
            wrap_caveat='Count only: periodic outside sampling would accept all finite queries. No wrap code change or terrain generation performed. Current product contract remains finite/no wrap; periodic continuity not verified.'))
    report['supplemental']=extra
    write_json(output/'s1-benchmark.json',report)
    write_json(output/'s2-supplemental.json',extra)
    print(json.dumps(extra,indent=2))


def main():
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('stage',choices=['s0','s1'])
    p.add_argument('--terra',default=str(ROOT.parent/'山川形意Terragenesis'))
    p.add_argument('--output',default=str(ROOT/'artifacts/td-world'))
    p.add_argument('--side',type=int,default=1024)
    args=p.parse_args()
    if args.side !=1024:
        p.error('This benchmark uses a fixed 1024-native-point page and 64-point overlap')
    (s0 if args.stage=='s0' else s1)(args)


if __name__=='__main__':
    main()
