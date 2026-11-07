"""Periodic plate conditioning and persistent latent-only generation; upstream is read-only."""
from __future__ import annotations
import json
import multiprocessing as mp
from pathlib import Path
import queue
import time

import numpy as np
from scipy import ndimage
from .td_pages import add_upstream, block_mean, file_sha, latent_lowfreq, preflight, write_json
from .source import identity

ALGORITHM = 'dream-td-periodic-latent-1'


def read_plate(path):
    with np.load(path,allow_pickle=False) as archive:
        manifest=json.loads(archive['manifest_json'].item())
        actual=identity({k:v for k,v in manifest.items() if k!='identity'})
        if actual!=manifest['identity']:
            raise ValueError('plate identity mismatch')
        a=archive['final/elevation_m'].copy()
        import hashlib
        if hashlib.sha256(a.tobytes()).hexdigest()!=manifest['arrays']['final/elevation_m']['sha256']:
            raise ValueError('plate array mismatch')
    return a,manifest


def sample_periodic(a,config,x,z):
    zz,xx=np.broadcast_arrays((np.asarray(z)-config['origin_z_m'])/config['cell_size_m']-.5,
                             (np.asarray(x)-config['origin_x_m'])/config['cell_size_m']-.5)
    return ndimage.map_coordinates(a,[zz,xx],order=1,mode='grid-wrap')


def periodic_factory(source,config,scale=1,origin_xz=(0,0), *, island_product_path=None,
                     expected_island_identity=None,skeleton_run_path=None):
    """scale k>1: one model metre stands for k plate metres about origin_xz (skeleton conditioning coordinates x k)."""
    from diffusion.geography_physical import make_physical_map_factory
    elevation,manifest=read_plate(source)
    binding=None
    if island_product_path is not None:
        from app.world_gen import ocean_island_adapter as islands
        binding=islands.load_binding(source,island_product_path,expected_island_identity,skeleton_run_path)
    elif expected_island_identity is not None or skeleton_run_path is not None:
        raise ValueError('island identity/run binding requires island_product_path')
    seed=int(manifest['config']['world_seed'])
    physical=make_physical_map_factory(seed,config)
    def raw(x1,z1,x2,z2):
        values=physical.sample_raw(x1,z1,x2,z2)
        x=np.arange(x1,x2,dtype=float)[None,:]*config.conditioning_spacing_m
        z=np.arange(z1,z2,dtype=float)[:,None]*config.conditioning_spacing_m
        if scale!=1:
            x=origin_xz[0]+(x-origin_xz[0])*scale
            z=origin_xz[1]+(z-origin_xz[1])*scale
        h=sample_periodic(elevation,manifest['config'],x,z)
        if binding is not None:
            h=islands.condition_height(binding,x,z,h)
        old=values[0].copy()
        values[1]=np.clip(values[1]+.0065*(np.maximum(old,0)-np.maximum(h,0)),-35,38)
        values[3]=np.clip(values[3]+.08*(np.maximum(old-1800,0)-np.maximum(h-1800,0)),100,3200)
        values[0]=h
        return values
    def full(x1,z1,x2,z2):
        import torch
        values=physical.finalize(raw(x1,z1,x2,z2))
        values[0]=np.sign(values[0])*np.sqrt(np.abs(values[0]))
        return torch.from_numpy(values)
    full.sample_raw=raw;full.finalize=physical.finalize
    if binding is not None:
        full.island_binding=binding.record
    return full,manifest


def world_plan(source,buffer_m=80000):
    a,manifest=read_plate(source)
    c=manifest['config'];spacing=960
    # Native model block centres are 465m modulo 960. Keep all centres in finite domain.
    first=[int(np.ceil((c['origin_x_m']-465)/960))*960+465,
           int(np.ceil((c['origin_z_m']-465)/960))*960+465]
    shape=[int(np.floor((c['origin_z_m']+a.shape[0]*c['cell_size_m']-first[1])/960))+1,
           int(np.floor((c['origin_x_m']+a.shape[1]*c['cell_size_m']-first[0])/960))+1]
    zz,xx=np.meshgrid(first[1]+np.arange(shape[0])*spacing,first[0]+np.arange(shape[1])*spacing,indexing='ij')
    skeleton=sample_periodic(a,c,xx,zz).astype(np.float32)
    distance=ndimage.distance_transform_edt(skeleton<0)*spacing
    # Full TD to 40km offshore, smooth taper to skeleton at 80km offshore.
    t=np.clip((distance-buffer_m/2)/(buffer_m/2),0,1)
    weight=(1-t*t*(3-2*t)).astype(np.float32)
    pages=[];core=30;side=1024
    for z in range(0,shape[0],core):
        for x in range(0,shape[1],core):
            if not np.any(weight[z:z+core,x:x+core]>0):
                continue
            pages.append(dict(id=f'z{z:04d}-x{x:04d}',grid_zx=[z,x],
                origin_native_xz=[int((first[0]-465)//30+x*32),int((first[1]-465)//30+z*32)],side_native=side))
    spec=dict(algorithm=ALGORITHM,plate_identity=manifest['identity'],world_seed=c['world_seed'],
              first_sample_xz_m=first,shape_zx=shape,spacing_m=spacing,core_cells=core,page_side_native=side,
              coast_buffer_m=buffer_m,extent_bounds_m=[c['origin_x_m'],c['origin_z_m'],
              c['origin_x_m']+a.shape[1]*c['cell_size_m'],c['origin_z_m']+a.shape[0]*c['cell_size_m']],pages=pages)
    spec['plan_identity']=identity(spec)
    return spec,skeleton,weight


def _resident(root,source,requests,responses):
    try:
        root=add_upstream(root)
        import torch
        from diffusion.physical_config import PhysicalGenerationConfig
        from diffusion.world_layout_backend import BUDGETS
        from terrain_diffusion.inference.world_pipeline import WorldPipeline
        factory,manifest=periodic_factory(source,PhysicalGenerationConfig())
        seed=int(manifest['config']['world_seed'])
        class PlatePipeline(WorldPipeline):
            def _init_conditioning(self):
                self.synthetic_map_factory=factory
        torch.set_num_threads(2)
        torch.cuda.set_per_process_memory_fraction(BUDGETS['gpu_peak_mib']*2**20/torch.cuda.get_device_properties(0).total_memory)
        loading=time.perf_counter()
        pipeline=PlatePipeline.from_pretrained(str(root/'models/terrain-diffusion-30m'),seed=seed,
            latents_batch_size=1,torch_compile=False,dtype=None,caching_strategy='direct',cache_limit=64*1024*1024,
            cond_snr=list(PhysicalGenerationConfig().cond_snr),log_mode='info')
        try:
            pipeline.to('cuda');pipeline.bind();torch.cuda.synchronize()
            model_seconds=time.perf_counter()-loading
            responses.put(dict(event='ready',model_loading_seconds=model_seconds))
            while True:
                request=requests.get()
                if request is None:
                    break
                x,z=request['origin_native_xz'];side=request['side_native']
                torch.cuda.reset_peak_memory_stats()
                started=time.perf_counter()
                with torch.inference_mode():
                    latent=pipeline.latents[:,z//8:(z+side)//8,x//8:(x+side)//8]
                    h=latent_lowfreq((latent[4]/latent[-1]).cpu().numpy())
                    result=block_mean(h,4)
                torch.cuda.synchronize()
                elapsed=time.perf_counter()-started
                dest=Path(request['destination']);dest.mkdir(parents=True,exist_ok=True)
                temporary=dest/'elevation_960m.tmp.npy'
                np.save(temporary,result,allow_pickle=False)
                temporary.replace(dest/'elevation_960m.npy')
                responses.put(dict(event='page',id=request['id'],inference_seconds=elapsed,
                    model_loading_seconds=model_seconds,
                    allocated_peak_mib=torch.cuda.max_memory_allocated()/2**20,
                    reserved_peak_mib=torch.cuda.max_memory_reserved()/2**20,
                    files={'elevation_960m.npy':file_sha(dest/'elevation_960m.npy')}))
        finally:
            pipeline.close()
    except BaseException as exc:
        import traceback
        responses.put(dict(event='error',error=str(exc),traceback=traceback.format_exc()))


def resident_headroom(available_bytes,worker_rss_mib,worker_budget_mib,side=1024):
    staging=300_000_000+side*side*160
    required=staging+1024*2**20
    if worker_rss_mib>worker_budget_mib:
        raise RuntimeError(f'resident RSS budget exceeded: {worker_rss_mib} > {worker_budget_mib} MiB')
    if available_bytes<required:
        raise RuntimeError(f'resident available host memory insufficient: {available_bytes} < {required} bytes')
    return dict(available_host_bytes=int(available_bytes),required_host_bytes=required,
                staging_bytes=staging,safety_margin_bytes=1024*2**20,
                worker_rss_mib=worker_rss_mib,worker_budget_mib=worker_budget_mib,
                rule='resident page: staging + 1024MiB headroom; resident RSS checked separately, not counted twice')


def generate_pages(root,source,pages,directory,*,purpose,plan_identity):
    """Parent enforces unchanged RSS/GPU budgets and a fresh 120s deadline per page."""
    root=add_upstream(root)
    from diffusion.world_layout_backend import BUDGETS,BudgetExceeded,_child_rss_mib
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    plate,manifest=read_plate(source)
    expected=dict(algorithm=ALGORITHM,plan_identity=plan_identity,plate_identity=manifest['identity'],world_seed=manifest['config']['world_seed'])
    pending=[];completed=[]
    for page in pages:
        dest=directory/page['id'];receipt=dest/'receipt.json'
        if receipt.exists():
            data=json.loads(receipt.read_text())
            if any(data.get(k)!=v for k,v in expected.items()) or data['origin_native_xz']!=page['origin_native_xz']:
                raise ValueError('resume mismatch')
            if file_sha(dest/'elevation_960m.npy')!=data['files']['elevation_960m.npy']:
                raise ValueError('resume file corrupted')
            completed.append(data)
        else:
            pending.append(page)
    if not pending:
        return completed
    flight=preflight(root,1024)
    ctx=mp.get_context('spawn');requests=ctx.Queue();responses=ctx.Queue()
    proc=ctx.Process(target=_resident,args=(str(root),str(source),requests,responses))
    proc.start();peak=0.0
    def receive():
        nonlocal peak
        start=time.perf_counter()
        while True:
            rss=_child_rss_mib(proc.pid);peak=max(peak,rss)
            if rss>BUDGETS['host_rss_mib']:
                raise BudgetExceeded('host_rss_mib',rss,'resident worker exceeded original RSS cap')
            if time.perf_counter()-start>BUDGETS['wall_clock_s']:
                raise BudgetExceeded('wall_clock_s',time.perf_counter()-start,'resident load/page deadline')
            try:
                result=responses.get(timeout=BUDGETS['poll_interval_s'])
            except queue.Empty:
                if not proc.is_alive():
                    raise RuntimeError('resident worker exited without result')
                continue
            if result['event']=='error':
                raise RuntimeError(result['error']+'\n'+result['traceback'])
            return result
    try:
        ready=receive()
        if ready['event']!='ready':
            raise RuntimeError('worker did not become ready')
        write_json(directory/'session.json',dict(**expected,purpose=purpose,initial_preflight=flight,**ready))
        for page in pending:
            import psutil
            current=resident_headroom(psutil.virtual_memory().available,_child_rss_mib(proc.pid),BUDGETS['host_rss_mib'])
            started=time.perf_counter();dest=directory/page['id']
            requests.put(dict(**page,destination=str(dest)))
            result=receive()
            if result['event']!='page' or result['id']!=page['id']:
                raise RuntimeError('worker page identity mismatch')
            if result['reserved_peak_mib']>BUDGETS['gpu_peak_mib']:
                raise BudgetExceeded('gpu_peak_mib',result['reserved_peak_mib'],'allocator cap exceeded')
            a=np.load(dest/'elevation_960m.npy',mmap_mode='r')
            if a.shape!=(32,32) or not np.isfinite(a).all():
                raise ValueError('invalid page')
            record={**expected,**page,**result,'purpose':purpose,'peak_child_rss_mib':peak,
                    'page_wall_seconds':time.perf_counter()-started,'preflight':current,
                    'gpu_scope':'PyTorch allocator only; driver and non-PyTorch allocations excluded'}
            write_json(dest/'receipt.json',record);completed.append(record)
            write_json(directory/'progress.json',dict(**expected,completed=len(completed),total=len(pages),last_page=page['id'],peak_child_rss_mib=peak))
            print(f'PAGE {len(completed)}/{len(pages)} {page["id"]} {result["inference_seconds"]:.3f}s RSS {peak:.1f}MiB',flush=True)
        requests.put(None);proc.join(timeout=5)
        return completed
    except BaseException as exc:
        write_json(directory/'blocked.json',dict(**expected,error=str(exc),completed=len(completed),total=len(pages),peak_child_rss_mib=peak))
        raise
    finally:
        if proc.is_alive():
            proc.terminate()
        proc.join(timeout=5)
        if proc.is_alive():
            proc.kill();proc.join()
        requests.close();responses.close()
