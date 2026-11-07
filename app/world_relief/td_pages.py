"""CPU helpers and budget-supervised, read-only upstream TD integration."""
from __future__ import annotations

import hashlib
import json
import multiprocessing as mp
from pathlib import Path
import sys
import time

import numpy as np

WORLD_SEED = 20261020
PLATE_IDENTITY = 'b4c8bbdba29111b8c3ba3270e2f0d3a4fed3544655249fa07c506654b8ae6af9'
UPSTREAM_DIR = 'terrain-diffusion-e8dcb4b1a834ab2f6b1a6f5256ed7c9f2f3e8230'


def block_mean(a, factor):
    a = np.asarray(a)
    if a.ndim != 2 or factor < 1 or any(s % factor for s in a.shape):
        raise ValueError('two-dimensional, exactly divisible block grid required')
    if not np.isfinite(a).all():
        raise ValueError('nonfinite terrain')
    return a.reshape(a.shape[0]//factor, factor, a.shape[1]//factor, factor).mean(axis=(1, 3), dtype=np.float64).astype(np.float32)


def latent_lowfreq(normalized_fifth_channel):
    sqrt_m = np.asarray(normalized_fifth_channel, dtype=np.float32) * 38.6 - 31.4
    return np.sign(sqrt_m) * np.square(sqrt_m)


def stats(a, b):
    if a.shape != b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('finite aligned grids required')
    d = a.astype(float)-b
    return dict(cells=int(d.size), bias_m=float(d.mean()), mae_m=float(np.abs(d).mean()),
                rmse_m=float(np.sqrt(np.square(d).mean())), max_abs_m=float(np.abs(d).max()),
                abs_m_quantiles=dict(zip(('p50','p90','p99'), np.quantile(np.abs(d), [.5,.9,.99]).tolist())),
                sign_agreement=float(np.mean((a >= 0) == (b >= 0))))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')
    temp.replace(path)


def file_sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def add_upstream(root):
    root = Path(root).resolve()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    vendor = root / 'vendor' / UPSTREAM_DIR
    if str(vendor) not in sys.path:
        sys.path.insert(0, str(vendor))
    return root


def preflight(root, side=1024):
    add_upstream(root)
    import psutil
    import subprocess
    from diffusion.world_layout_backend import BUDGETS, BudgetExceeded
    staging = 300_000_000 + side*side*160
    available = psutil.virtual_memory().available
    required = BUDGETS['host_rss_mib']*2**20 + staging
    if available < required:
        raise BudgetExceeded('available_host_memory', available, f'required bytes {required}')
    query = subprocess.run(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],
                           check=True, capture_output=True, text=True, timeout=5)
    free = int(query.stdout.splitlines()[0].strip())
    if free < BUDGETS['gpu_peak_mib']:
        raise BudgetExceeded('gpu_free', free, 'full upstream GPU budget must be free')
    return dict(available_host_bytes=available, required_host_bytes=required, gpu_free_mib=free,
                staging_bytes=staging, budgets=dict(BUDGETS))


def _worker(root, source, origin, side, mode, destination):
    destination = Path(destination)
    start = time.perf_counter()
    try:
        root = add_upstream(root)
        import torch
        from diffusion.physical_config import PhysicalGenerationConfig
        from diffusion.plate_td_conditioning import make_plate_factory
        from diffusion.world_layout_backend import BUDGETS
        from terrain_diffusion.inference.world_pipeline import WorldPipeline
        config = PhysicalGenerationConfig()
        factory = make_plate_factory(source, PLATE_IDENTITY, WORLD_SEED, config)
        class PlatePipeline(WorldPipeline):
            def _init_conditioning(self):
                self.synthetic_map_factory = factory
        torch.set_num_threads(2)
        torch.cuda.set_per_process_memory_fraction(BUDGETS['gpu_peak_mib']*2**20 / torch.cuda.get_device_properties(0).total_memory)
        torch.cuda.reset_peak_memory_stats()
        loading = time.perf_counter()
        pipeline = PlatePipeline.from_pretrained(str(root/config.model_dir), seed=WORLD_SEED,
            latents_batch_size=1, torch_compile=False, dtype=None, caching_strategy='direct',
            cache_limit=64*1024*1024, cond_snr=list(config.cond_snr), log_mode='info')
        try:
            pipeline.to('cuda')
            pipeline.bind()
            torch.cuda.synchronize()
            load_seconds = time.perf_counter()-loading
            x,z = origin
            started = time.perf_counter()
            with torch.inference_mode():
                if mode == 'latent':
                    a = pipeline.latents[:,z//8:(z+side)//8,x//8:(x+side)//8]
                    h = latent_lowfreq((a[4]/a[-1]).cpu().numpy())
                    result = {'elevation_960m': block_mean(h,4)}
                elif mode == 'decoded':
                    h = pipeline.get(z,x,z+side,x+side,with_climate=False)['elev'].cpu().numpy()
                    result = {'elevation_30m':h.astype(np.float32), 'elevation_960m':block_mean(h,32)}
                else:
                    raise ValueError('unknown TD mode')
            torch.cuda.synchronize()
            inference_seconds = time.perf_counter()-started
            for name,a in result.items():
                if not np.isfinite(a).all():
                    raise ValueError('nonfinite output')
                np.save(destination/(name+'.npy'),a,allow_pickle=False)
            metadata = dict(ok=True, purpose='test', mode=mode, world_seed=WORLD_SEED,
                plate_identity=PLATE_IDENTITY, origin_native_xz=list(origin),side_native=side,
                first_sample_960m_xz_m=[30*x+465,30*z+465],spacing_m=960,
                model_loading_seconds=load_seconds,inference_seconds=inference_seconds,
                worker_seconds=time.perf_counter()-start,
                allocated_peak_mib=torch.cuda.max_memory_allocated()/2**20,
                reserved_peak_mib=torch.cuda.max_memory_reserved()/2**20,
                files={n+'.npy':file_sha(destination/(n+'.npy')) for n in result})
        finally:
            pipeline.close()
        write_json(destination/'worker.json',metadata)
    except BaseException as exc:
        import traceback
        write_json(destination/'worker.json',dict(ok=False,error=str(exc),traceback=traceback.format_exc()))


def run_page(root, source, origin, destination, *, side=1024, mode='decoded'):
    """Each page uses unmodified upstream host/GPU/time ceilings; resumes verified output."""
    if side < 32 or side > 1337 or side % 32 or any(type(v) is not int or v % 32 for v in origin):
        raise ValueError('32-aligned native window up to upstream 1337 limit required')
    destination = Path(destination)
    destination.mkdir(parents=True,exist_ok=True)
    receipt = destination/'receipt.json'
    if receipt.exists():
        old = json.loads(receipt.read_text())
        if (old['mode'] != mode or old['origin_native_xz'] != list(origin) or old['side_native'] != side
                or old['world_seed'] != WORLD_SEED or old['plate_identity'] != PLATE_IDENTITY):
            raise ValueError('resume request differs from completed page')
        for name, digest in old['files'].items():
            if file_sha(destination/name) != digest:
                raise ValueError('completed page corrupted')
        return old
    flight = preflight(root,side)
    add_upstream(root)
    from diffusion.plate_td_conditioning import make_plate_factory,conditioning_footprint
    from diffusion.physical_config import PhysicalGenerationConfig
    from diffusion.world_layout_backend import BUDGETS, BudgetExceeded, _child_rss_mib
    factory = make_plate_factory(source,PLATE_IDENTITY,WORLD_SEED,PhysicalGenerationConfig())
    footprint = conditioning_footprint(origin,side)
    factory.sample_raw(*footprint)
    proc = mp.get_context('spawn').Process(target=_worker,args=(str(root),str(source),origin,side,mode,str(destination)))
    start = time.perf_counter()
    proc.start()
    rss = 0
    try:
        while proc.is_alive():
            rss = max(rss,_child_rss_mib(proc.pid))
            if rss > BUDGETS['host_rss_mib']:
                raise BudgetExceeded('host_rss_mib',rss,'worker RSS ceiling exceeded')
            elapsed = time.perf_counter()-start
            if elapsed > BUDGETS['wall_clock_s']:
                raise BudgetExceeded('wall_clock_s',elapsed,'upstream deadline exceeded')
            proc.join(timeout=BUDGETS['poll_interval_s'])
        proc.join()
        if proc.exitcode != 0:
            raise RuntimeError(f'TD worker exit {proc.exitcode}')
        data = json.loads((destination/'worker.json').read_text())
        if not data['ok']:
            raise RuntimeError(data['error']+'\n'+data['traceback'])
        if data['reserved_peak_mib'] > BUDGETS['gpu_peak_mib']:
            raise BudgetExceeded('gpu_peak_mib',data['reserved_peak_mib'],'allocator ceiling exceeded')
        data.update(wall_seconds=time.perf_counter()-start,peak_child_rss_mib=rss,preflight=flight,
                    gpu_scope='PyTorch allocator only; excludes driver and non-PyTorch allocations',
                    conditioning_footprint_xzxz=footprint)
        write_json(receipt,data)
        return data
    except BaseException as exc:
        write_json(destination/'failure.json',dict(ok=False,error=str(exc),elapsed_seconds=time.perf_counter()-start,
                   peak_child_rss_mib=rss,preflight=flight))
        raise
    finally:
        if proc.is_alive():
            proc.terminate()
        proc.join(timeout=5)
        if proc.is_alive():
            proc.kill()
            proc.join()
