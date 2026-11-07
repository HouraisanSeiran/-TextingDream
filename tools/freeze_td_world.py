"""CPU-only freeze, self-check previews and contract verification after GPU page completion."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from scipy import ndimage
from PIL import Image,ImageDraw
from app.world_relief.td_freeze import freeze
from app.world_relief.td_pages import write_json,file_sha
from app.map_source import load_source
from tools.build_td_world import comparison


def preview(path,h,first,spacing,lines=(),wet=None,max_width=1800,title='Terragenesis latent world 960m'):
    stops=np.array([-6000,-2000,-1,0,300,1000,2500,5000,10000],float)
    colours=np.array([[22,45,82],[42,88,132],[111,174,195],[91,143,100],[145,170,104],
                      [186,178,129],[161,145,127],[211,208,200],[250,250,248]],float)
    rgb=np.stack([np.interp(h,stops,colours[:,i]) for i in range(3)],axis=-1)
    gz,gx=np.gradient(h.astype(float),spacing)
    light=np.clip((1-.6*gx-.6*gz)/np.sqrt(1+gx*gx+gz*gz),0,1)
    rgb=np.clip(rgb*(.45+.55*light[:,:,None]),0,255).astype('uint8')
    if wet is not None:rgb[wet]=[70,138,180]
    scale=min(1,max_width/h.shape[1])
    width=int(round(h.shape[1]*scale));height=int(round(h.shape[0]*scale))
    image=Image.fromarray(rgb).resize((width,height),Image.Resampling.LANCZOS)
    draw=ImageDraw.Draw(image)
    for line in lines:
        pts=[((x-first[0])/spacing*scale,(z-first[1])/spacing*scale) for x,z in line['coordinates_xz_m']]
        draw.line(pts,fill=(45,113,174),width=1)
    canvas=Image.new('RGB',(width,height+56),'white');canvas.paste(image,(0,56));draw=ImageDraw.Draw(canvas)
    draw.text((12,10),title,fill='black')
    draw.text((12,30),f'{h.shape[1]} x {h.shape[0]} samples; {spacing}m; X east / Z south; sea0m; area is NOT discharge',fill='black')
    canvas.save(path)


def deliver(directory):
    started=time.perf_counter();directory=Path(directory)
    product,manifest=freeze(directory)
    h=np.load(product/'elevation_m.npy',mmap_mode='r')
    ocean=np.load(product/'ocean_mask.npy',mmap_mode='r')
    water=np.load(product/'water_surface_m.npy',mmap_mode='r')
    first=manifest['first_sample_xz_m']
    lines=json.loads((product/'rivers.json').read_text())['lines']
    preview(directory/'overview.png',h,first,960,lines,np.isfinite(water))
    v2=ROOT/'artifacts/world-relief-pilot-v2'
    pm=json.loads((v2/'manifest.json').read_text())
    old=np.load(v2/'elevation_m.npy',mmap_mode='r')
    z0,x0=pm['zoom']['first_sample_xz_m'][1],pm['zoom']['first_sample_xz_m'][0]
    zz,xx=np.meshgrid(z0+np.arange(300)*960,x0+np.arange(300)*960,indexing='ij')
    coords=[(zz-first[1])/960,(xx-first[0])/960]
    new=ndimage.map_coordinates(h,coords,order=1,mode='nearest')
    old_crop=ndimage.map_coordinates(old,[(zz-pm['first_sample_xz_m'][1])/1000,(xx-pm['first_sample_xz_m'][0])/1000],order=1,mode='nearest')
    comparison(directory/'v2-same-window.png',[old_crop,new],['v2 noise + erosion (same288km window)','TD latent low-frequency 960m (same window)'])
    score=ndimage.maximum_filter(h,size=31)-ndimage.minimum_filter(h,size=31)
    score=np.where((h>1500)&~ocean,score,-np.inf)
    z,x=np.unravel_index(np.argmax(score),h.shape)
    z=max(0,min(h.shape[0]-300,z-150));x=max(0,min(h.shape[1]-300,x-150))
    zoom=h[z:z+300,x:x+300]
    preview(directory/'mountain-zoom.png',zoom,[first[0]+x*960,first[1]+z*960],960,lines=(),max_width=1000,title='Mountain/valley self-check (288km window; no erosion)')
    smoke=np.load(directory/'smoke-periodic/mosaic_960m.npy')
    mn=float(smoke.min());mx=float(smoke.max());gray=((smoke-mn)/max(1,mx-mn)*255).astype('uint8')
    im=Image.fromarray(gray).convert('RGB').resize((900,900),Image.Resampling.NEAREST)
    draw=ImageDraw.Draw(im)
    edge=(-800000-(-26880*30+465))/960
    xx=int(round(edge/60*900));draw.line((xx,0,xx,900),fill=(250,140,40),width=2)
    draw.line((450,0,450,900),fill=(210,30,60),width=1);draw.line((0,450,900,450),fill=(210,30,60),width=1)
    canvas=Image.new('RGB',(900,950),'white');canvas.paste(im,(0,50));draw=ImageDraw.Draw(canvas)
    draw.text((12,10),'Cross-boundary latent smoke: local elevation contrast; orange X=-800km; red page joins',fill='black')
    draw.text((12,30),f'Local linear greyscale {mn:.1f}..{mx:.1f}m, not overview colour scale',fill='black')
    canvas.save(directory/'boundary-seam-check.png')
    loaded=load_source('world-map-product',product,expected_identity=manifest['identity'],expected_world_seed=manifest['world_seed'])
    s=loaded.sample(np.array([first[0],first[0]+960,first[0]-1]),first[1])
    if not np.allclose(s['elevation_m'][:2],h[0,:2]) or s['status'][2]!=1:
        raise ValueError('real-product contract coordinates/bounds failed')
    if s['elevation_m'].flags.writeable:
        raise ValueError('query buffers unexpectedly writable')
    from app.world_relief.drainage import ocean_mask
    if not np.array_equal(ocean_mask(h),ocean):raise ValueError('ocean classification mismatch')
    river_ids=[v['id'] for v in loaded.vectors('rivers')]
    lake_ids=[v['id'] for v in loaded.vectors('lakes')]
    if len(set(river_ids))!=len(river_ids) or len(set(lake_ids))!=len(lake_ids):raise ValueError('duplicate vector ids')
    validation=dict(identity=manifest['identity'],schema=manifest['schema'],coordinate_checks=True,finite_bounds=True,
        read_only_sample=True,ocean_four_neighbour=True,river_ids_unique=True,lake_ids_unique=True,
        river_count=len(river_ids),lake_count=len(lake_ids),preview_seconds=time.perf_counter()-started,
        artifact_files={p.name:dict(bytes=p.stat().st_size,sha256=file_sha(p)) for p in directory.glob('*.png')})
    write_json(directory/'validation.json',validation)
    stats=manifest['statistics'];g=manifest['generation']
    readme=f'''# Terragenesis world960m: generated, frozen and read-only validated

Product: world-960m/manifest.json\n\nIdentity: {manifest['identity']}\n\nActual TD seed: {manifest['world_seed']}; source plate: {manifest['source_identity']}.

TD fifth latent channel low-frequency ~240m, inverse signed square then4x4 metre-space average to960m. NO30m decoder. This is not the exact block mean of decoded30m.

Finite domain bounds: {manifest['requested_domain_bounds_m']}. Shape[z,x]: {manifest['shape_zx']}; first sample X,Z: {first}; grid960m. Conditions wrap on the skeleton's periodic plane outside its bounds; output query domain does NOT wrap. Native block alignment leaves less than one grid spacing at finite rim.

Pages: {stats['pages']}. Sum inference: {stats['sum_inference_seconds']:.3f}s; generation invocation: {g['elapsed_seconds_this_invocation']:.3f}s; sum page wall: {g['sum_page_wall_seconds']:.3f}s. RSS peak {stats['peak_child_rss_mib']:.1f}MiB, GPU allocated/reserved peaks {stats['allocated_peak_mib']:.1f}/{stats['reserved_peak_mib']:.1f}MiB. RSS sampled; GPU figures exclude driver/non-PyTorch memory.

Resource policy: cold launch requires4096MiB worker+467772160-byte staging =4762739456 bytes. Resident page requires staging+1024MiB safety =1541513984 bytes; resident RSS independently <=4096MiB. Per-page120s deadline, GPU allocator cap4096MiB. Both checks and actual readings are recorded in page receipts; already resident RSS is not double counted.

Land and nearshore use TD. Full TD extends40km offshore; smoothstep40..80km blends to bilinear plate deep ocean. Final coastline is zero-elevation contour; four-neighbour negatives reaching domain rim are ocean; disconnected negative basins remain inland. Positive lakes do not change status to closed-below-sea.

Coarse hydrology reused unchanged MFD/flood-parent/single-receiver algorithm, at960m, river threshold300km2. Routing time {stats['routing_seconds']:.3f}s. Bed elevation remains unmodified. {stats['river_segments']} river segments; {stats['potential_lakes']} potential lake polygons. Contributing area is NOT discharge. Filled surface and lake polygons are potential flood inundation, not permanent water or a water-balance simulation. D8 direction bias remains.

Overlap pairs {stats['overlap_pairs']}; maximum overlap discrepancy {stats['overlap_max_abs_m']:.6f}m. Cross-boundary2x2 smoke is in smoke-periodic/result.json and is a deep-sea test, not coastal validation. All world overlaps additionally checked before freeze.

Previews: overview.png (simple colour/shade + rivers/potential water); mountain-zoom.png; v2-same-window.png; boundary-seam-check.png (local contrast and joins). These are diagnostics, not a styled game map.

Adapter: kind world-map-product, schema td-world-960m-v1. Same strict generic contract as world-map-product-v1. Layers elevation/status/water_surface/drainage_area. Rivers/lakes standardized under vectors/. Root arrays and coordinate rivers.json retained for v2-like tooling. Validation: validation.json. Querying never generates terrain.

Reproduce GPU phase with upstream runtime/venv/Scripts/python.exe -u tools/build_td_resident_world.py all (resumes verified pages). CPU freeze/preview: .venv/Scripts/python.exe tools/freeze_td_world.py. Tests: .venv/Scripts/python.exe -m pytest tests/test_td_world.py tests/test_map_source_contract.py -o addopts='' -q -p no:cacheprovider.

No game integration. No Terragenesis file modifications. No git commit.
'''
    (directory/'README.md').write_text(readme,encoding='utf-8')
    print('VALIDATED '+manifest['identity'],flush=True)


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--output',default=str(ROOT/'artifacts/td-world'))
    args=parser.parse_args();deliver(args.output)


if __name__=='__main__':main()
