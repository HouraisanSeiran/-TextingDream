"""Fast latent-only Terragenesis world generation (large windows, batched UNet, optional half precision).

Same maths as td_resident (plan C periodic conditioning, latent channel 4, 4x4 mean -> 960 m) but the
resident worker asks the upstream InfiniteTensor for one big block of cells instead of one 32x32-cell
page at a time. Upstream stays read-only: only constructor arguments and instance-level wrappers are used.
"""
from __future__ import annotations

import json
import multiprocessing as mp
from pathlib import Path
import queue
import threading
import time

import numpy as np

from .td_pages import add_upstream, block_mean, file_sha, latent_lowfreq, write_json
from .td_resident import periodic_factory

ALGORITHM = 'dream-td-fast-latent-1'
LATENT_PER_CELL = 4      # 960 m cell / 240 m latent pixel
NATIVE_PER_CELL = 32     # 960 m cell / 30 m native pixel
PRECISIONS = ('fp32', 'fp16', 'autocast')
# onestep: skip the second latent refinement pass (upstream onestep_latent); coarse_steps: coarse sampler steps (upstream 20);
# warm_coarse: compute the whole region's coarse tiles once before the first block; slice_channels: read only latent
# channels 4 and weight (5) from the upstream tensor instead of all six.
DEFAULT_OPTIONS = dict(precision='fp32', batch=8, cache_mib=512, threads=2, cudnn_benchmark=True, profile=False,
                       onestep=False, coarse_steps=20, warm_coarse=False, slice_channels=False, scale=1,
                       cuda_graph=False, noise_cache=False, channels_last=False, writer_thread=False)
# Round 3 (software only, values unchanged): cuda_graph replays the UNet batch as one CUDA graph (removes kernel-launch gaps),
# noise_cache reuses the 64x64 tile normals shared by overlapping windows (same PCG64 stream, bit-identical), channels_last
# switches the UNet to NHWC and writer_thread moves low-frequency/block-mean/save/hash to a background thread (the parent
# then keeps one extra request queued). noise_cache also prefetches the next block's noise tiles during the current block.
# scale k: one model metre stands for k plate metres (conditioning coordinates x k about the region origin); the output
# grid spacing becomes 960*k m, so a block of N cells covers k*k times the plate area.
NUMERIC_KEYS = ('precision', 'onestep', 'coarse_steps', 'scale')   # options that can change values; part of the resume identity


def scale_origin(spec):
    """Model-space metres of the region's first cell: the fixed point of the conditioning scaling."""
    fx, fz = (int(v) for v in spec['first_sample_xz_m'])
    z0, _, x0, _ = (int(v) for v in spec['region'])
    return [fx + x0 * 960, fz + z0 * 960]


# ---------------------------------------------------------------- planning (CPU only)

def plan_blocks(region, block_cells, weight=None):
    """Tile region=(z0,z1,x0,x1) (half-open, 960 m cell indices) with block_cells squares.

    Blocks tile the region exactly (ragged at the far edges). When weight is given, blocks whose cells all
    have weight<=0 are dropped, so every weight>0 cell is covered exactly once.
    """
    z0, z1, x0, x1 = (int(v) for v in region)
    block_cells = int(block_cells)
    if z1 <= z0 or x1 <= x0 or block_cells < 1:
        raise ValueError('empty region or invalid block size')
    if weight is not None and (z0 < 0 or x0 < 0 or z1 > weight.shape[0] or x1 > weight.shape[1]):
        raise ValueError('region outside weight grid')
    blocks = []
    for z in range(z0, z1, block_cells):
        for x in range(x0, x1, block_cells):
            ze, xe = min(z + block_cells, z1), min(x + block_cells, x1)
            if weight is not None and not np.any(weight[z:ze, x:xe] > 0):
                continue
            blocks.append(dict(id=f'bz{z:05d}-bx{x:05d}', cell_zx=[z, x], cells_zx=[ze - z, xe - x]))
    return blocks


def check_coverage(blocks, region, weight=None):
    """Raise when a needed cell is uncovered or any cell is covered twice."""
    z0, z1, x0, x1 = (int(v) for v in region)
    count = np.zeros((z1 - z0, x1 - x0), dtype=np.int16)
    for b in blocks:
        z, x = b['cell_zx']
        h, w = b['cells_zx']
        if z < z0 or x < x0 or z + h > z1 or x + w > x1:
            raise ValueError('block outside region ' + b['id'])
        count[z - z0:z - z0 + h, x - x0:x - x0 + w] += 1
    if (count > 1).any():
        raise ValueError('overlapping blocks')
    needed = np.ones_like(count, dtype=bool) if weight is None else weight[z0:z1, x0:x1] > 0
    if (needed & (count == 0)).any():
        raise ValueError('uncovered cells: %d' % int((needed & (count == 0)).sum()))
    return int(needed.sum()), int((count > 0).sum())


def block_geometry(first_sample_xz_m, block):
    """Native-pixel origin and latent slice of a block; mirrors td_resident.world_plan page origins."""
    fx, fz = (int(v) for v in first_sample_xz_m)
    if (fx - 465) % 960 or (fz - 465) % 960:
        raise ValueError('first sample must sit on the 960 m model block grid')
    bx, bz = (fx - 465) // 30, (fz - 465) // 30
    z, x = block['cell_zx']
    h, w = block['cells_zx']
    ox, oz = bx + x * NATIVE_PER_CELL, bz + z * NATIVE_PER_CELL
    if ox % 8 or oz % 8:
        raise ValueError('origin not aligned to latent pixels')
    return dict(origin_native_xz=[ox, oz],
                latent_slice=[[oz // 8, oz // 8 + h * LATENT_PER_CELL], [ox // 8, ox // 8 + w * LATENT_PER_CELL]])


def staging_bytes(block, cache_bytes, legacy_side=1024):
    """Host staging for one block: tiles alive during the access + cache + result copies; never below the page rule."""
    lh, lw = (c * LATENT_PER_CELL for c in block['cells_zx'])
    tiles = 2 * 6 * 4 * 4 * (lh + 160) * (lw + 160)   # init + step stage, 4x tile overlap, float32
    copies = 3 * 6 * 4 * lh * lw
    working = 300_000_000 + int(cache_bytes) + tiles + copies
    legacy = 300_000_000 + legacy_side * legacy_side * 160
    return int(max(working, legacy))


def block_headroom(available_bytes, worker_rss_mib, worker_budget_mib, staging):
    required = staging + 1024 * 2 ** 20
    if worker_rss_mib > worker_budget_mib:
        raise RuntimeError(f'resident RSS budget exceeded: {worker_rss_mib} > {worker_budget_mib} MiB')
    if available_bytes < required:
        raise RuntimeError(f'resident available host memory insufficient: {available_bytes} < {required} bytes')
    return dict(available_host_bytes=int(available_bytes), required_host_bytes=int(required), staging_bytes=int(staging),
                safety_margin_bytes=1024 * 2 ** 20, worker_rss_mib=worker_rss_mib, worker_budget_mib=worker_budget_mib,
                rule='block: staging + 1024MiB headroom; resident RSS checked separately, not counted twice')


def preflight_fast(root, staging):
    """Start-up check: full RSS budget + staging must be available, and the full GPU budget must be free."""
    add_upstream(root)
    import subprocess
    import psutil
    from diffusion.world_layout_backend import BUDGETS, BudgetExceeded
    available = psutil.virtual_memory().available
    required = BUDGETS['host_rss_mib'] * 2 ** 20 + staging
    if available < required:
        raise BudgetExceeded('available_host_memory', available, f'required bytes {required}')
    query = subprocess.run(['nvidia-smi', '--query-gpu=memory.free', '--format=csv,noheader,nounits'],
                           check=True, capture_output=True, text=True, timeout=5)
    free = int(query.stdout.splitlines()[0].strip())
    if free < BUDGETS['gpu_peak_mib']:
        raise BudgetExceeded('gpu_free', free, 'full upstream GPU budget must be free')
    return dict(available_host_bytes=available, required_host_bytes=required, gpu_free_mib=free,
                staging_bytes=staging, budgets=dict(BUDGETS))


def check_block(dest, expected, block):
    """Return a verified receipt for a finished block, None when absent; raise on mismatch or corruption."""
    dest = Path(dest)
    receipt = dest / 'receipt.json'
    if not receipt.exists():
        return None
    data = json.loads(receipt.read_text(encoding='utf-8'))
    if any(data.get(k) != v for k, v in expected.items()) \
            or data.get('cell_zx') != block['cell_zx'] or data.get('cells_zx') != block['cells_zx']:
        raise ValueError('resume mismatch')
    path = dest / 'elevation_960m.npy'
    if not path.exists() or file_sha(path) != data['files']['elevation_960m.npy']:
        raise ValueError('resume file corrupted')
    a = np.load(path, mmap_mode='r')
    if tuple(a.shape) != tuple(block['cells_zx']) or not np.isfinite(a).all():
        raise ValueError('resume file invalid')
    return data


def assemble(directory, blocks, region, fill=np.nan):
    """Read finished blocks into one float32 array over region."""
    z0, z1, x0, x1 = (int(v) for v in region)
    canvas = np.full((z1 - z0, x1 - x0), fill, dtype=np.float32)
    for b in blocks:
        a = np.load(Path(directory) / b['id'] / 'elevation_960m.npy')
        z, x = b['cell_zx']
        canvas[z - z0:z - z0 + a.shape[0], x - x0:x - x0 + a.shape[1]] = a
    return canvas


# ---------------------------------------------------------------- monitoring

class GpuMonitor:
    """Polls nvidia-smi; keeps (time, utilisation %, memory MiB) samples."""

    def __init__(self, interval=0.5):
        self.interval, self.samples, self._stop, self._thread = interval, [], threading.Event(), None

    def _run(self):
        import subprocess
        while not self._stop.is_set():
            try:
                out = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu,memory.used', '--format=csv,noheader,nounits'],
                                     capture_output=True, text=True, timeout=5).stdout.splitlines()[0]
                u, m = (float(v) for v in out.split(','))
                self.samples.append((time.time(), u, m))
            except Exception:
                pass
            self._stop.wait(self.interval)

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def stop(self, since=None):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=10)
        return self.summary(since)

    def summary(self, since=None):
        s = [v for v in self.samples if since is None or v[0] >= since]
        if not s:
            return dict(samples=0)
        u = np.array([v[1] for v in s])
        m = np.array([v[2] for v in s])
        return dict(samples=len(s), util_mean_pct=float(u.mean()), util_median_pct=float(np.median(u)),
                    util_max_pct=float(u.max()), mem_used_max_mib=float(m.max()), mem_used_mean_mib=float(m.mean()))


# ---------------------------------------------------------------- round 3 helpers (values unchanged)

class NoiseTileCache:
    """Bit-identical cache of upstream gaussian_noise_patch tiles.

    Overlapping 64x64 latent windows (stride 32) re-draw the same 64x64 normal tiles up to nine times. The tiles come
    from the same PCG64 + Marsaglia polar stream (the upstream numba kernel recompiled with nogil=True so a prefetch thread
    can fill the cache while the GPU works); a cached tile is read-only and every patch is a fresh copy.
    """

    def __init__(self, wp, max_tiles=768):
        import collections
        import numba
        import terrain_diffusion.inference.portable_rng as rng
        self.tile_seed = wp._tile_seed
        self.fill = numba.njit(nogil=True)(rng._fill_standard_normal_impl.py_func)
        self.max_tiles = int(max_tiles)
        self.tiles = collections.OrderedDict()
        self.lock = threading.Lock()
        self.hits = self.misses = 0

    def tile(self, base_seed, ty, tx, channels, th, tw, dtype):
        key = (int(base_seed), int(ty), int(tx), int(channels), int(th), int(tw), np.dtype(dtype).str)
        with self.lock:
            t = self.tiles.get(key)
            if t is not None:
                self.tiles.move_to_end(key)
                self.hits += 1
                return t
        t = np.empty((channels, th, tw), dtype=dtype)
        self.fill(np.uint64(int(self.tile_seed(base_seed, ty, tx)) & 0xFFFFFFFFFFFFFFFF), t.ravel())
        t.flags.writeable = False
        with self.lock:
            self.misses += 1
            self.tiles[key] = t
            while len(self.tiles) > self.max_tiles:
                self.tiles.popitem(last=False)
        return t

    def patch(self, base_seed, y0, x0, h, w, channels=1, tile_h=256, tile_w=256, dtype=np.float32):
        """Same contract and tiling as upstream gaussian_noise_patch."""
        out = np.empty((channels, h, w), dtype=dtype)
        for ty in range(y0 // tile_h, (y0 + h - 1) // tile_h + 1):
            for tx in range(x0 // tile_w, (x0 + w - 1) // tile_w + 1):
                tile = self.tile(base_seed, ty, tx, channels, tile_h, tile_w, dtype)
                ty0, tx0 = ty * tile_h, tx * tile_w
                oy0, oy1 = max(y0, ty0), min(y0 + h, ty0 + tile_h)
                ox0, ox1 = max(x0, tx0), min(x0 + w, tx0 + tile_w)
                out[:, oy0 - y0:oy1 - y0, ox0 - x0:ox1 - x0] = tile[:, oy0 - ty0:oy1 - ty0, ox0 - tx0:ox1 - tx0]
        return out

    def prefetch(self, base_seed, y0, y1, x0, x1, channels=5, tile=64):
        """Fill every tile touched by pixel window [y0,y1)x[x0,x1) on a background thread."""
        def run():
            for ty in range(y0 // tile, (y1 - 1) // tile + 1):
                for tx in range(x0 // tile, (x1 - 1) // tile + 1):
                    self.tile(base_seed, ty, tx, channels, tile, tile, np.float32)
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        return thread


def cached_noise_patch(cache):
    return cache.patch


def graphed_forward(torch, base_forward, precision, stats, compute_embeddings):
    """UNet forward replayed as one CUDA graph per input-shape signature (falls back to eager when capture fails)."""
    import contextlib
    graphs = {}
    pool = torch.cuda.graph_pool_handle()
    constants = {}
    real_tensor = torch.tensor

    def cached_tensor(data, *a, **k):
        # upstream mp_sum/mp_concat/attention build tiny constant tensors host->device on every call; that is illegal inside a
        # graph capture. Constants are built once (eager warm-up) and reused, so values are identical.
        dev = k.get('device')
        if a or dev is None or torch.device(dev).type != 'cuda' or isinstance(data, torch.Tensor):
            return real_tensor(data, *a, **k)
        try:
            key = (repr(data), str(k.get('dtype')), str(dev))
        except Exception:
            return real_tensor(data, *a, **k)
        t = constants.get(key)
        if t is None:
            t = constants[key] = real_tensor(data, *a, **k)
        return t

    @contextlib.contextmanager
    def constants_cached():
        torch.tensor = cached_tensor
        try:
            yield
        finally:
            torch.tensor = real_tensor

    def eager(x, *a, **k):
        if precision == 'autocast':
            with torch.autocast('cuda', dtype=torch.float16, cache_enabled=False):   # the weight-cast cache cannot live inside a graph capture
                return base_forward(x, *a, **k).float()
        return base_forward(x, *a, **k)

    def embed(labels, cond):
        # mp_sum builds a host->device weight tensor, which cannot happen inside a capture: embeddings stay eager, the rest is graphed
        if precision == 'autocast':
            with torch.autocast('cuda', dtype=torch.float16, cache_enabled=False):
                return compute_embeddings(labels, cond)
        return compute_embeddings(labels, cond)

    def body(x, labels, cond, emb):
        if precision == 'autocast':
            with torch.autocast('cuda', dtype=torch.float16, cache_enabled=False):
                return base_forward(x, noise_labels=labels, conditional_inputs=cond, precomputed_embeds=emb).float()
        return base_forward(x, noise_labels=labels, conditional_inputs=cond, precomputed_embeds=emb)

    def run(x, *a, **k):
        stats['unet_calls'] += 1
        stats['unet_samples'] += int(x.shape[0])
        labels, cond = k.get('noise_labels'), k.get('conditional_inputs')
        if a or set(k) != {'noise_labels', 'conditional_inputs'} or not x.is_cuda or not cond:
            return eager(x, *a, **k)
        key = (tuple(x.shape), str(x.dtype), tuple(labels.shape), tuple(tuple(c.shape) for c in cond))
        entry = graphs.get(key)
        if entry is None:
            try:
                sx, sl, sc = x.clone(), labels.clone(), [c.clone() for c in cond]
                se = embed(sl, sc).clone()
                side = torch.cuda.Stream()
                side.wait_stream(torch.cuda.current_stream())
                with constants_cached():
                    with torch.cuda.stream(side):
                        for _ in range(2):
                            body(sx, sl, sc, se)
                    torch.cuda.current_stream().wait_stream(side)
                    graph = torch.cuda.CUDAGraph()
                    with torch.cuda.graph(graph, pool=pool):
                        so = body(sx, sl, sc, se)
                entry = (graph, sx, se, so)
                stats['graphs_captured'] += 1
            except Exception:
                import traceback
                traceback.print_exc()
                entry = False
                stats['graph_capture_failed'] += 1
            graphs[key] = entry
        if not entry:
            return eager(x, *a, **k)
        graph, sx, se, so = entry
        sx.copy_(x)
        se.copy_(embed(labels, cond))
        graph.replay()
        return so.clone()

    return run


# ---------------------------------------------------------------- resident worker (GPU)

def _worker(root, source, options, requests, responses):
    try:
        root = add_upstream(root)
        import collections
        import torch
        from diffusion.physical_config import PhysicalGenerationConfig
        from diffusion.world_layout_backend import BUDGETS
        import terrain_diffusion.inference.world_pipeline as wp
        config = PhysicalGenerationConfig()
        factory, manifest = periodic_factory(source, config, scale=int(options['scale']),
                                             origin_xz=tuple(options.get('scale_origin_xz') or (0, 0)))
        seed = int(manifest['config']['world_seed'])

        class PlatePipeline(wp.WorldPipeline):
            def _init_conditioning(self):
                self.synthetic_map_factory = factory

        precision = options['precision']
        torch.set_num_threads(int(options['threads']))
        torch.cuda.set_per_process_memory_fraction(BUDGETS['gpu_peak_mib'] * 2 ** 20 / torch.cuda.get_device_properties(0).total_memory)
        torch.backends.cudnn.benchmark = bool(options['cudnn_benchmark'])
        loading = time.perf_counter()
        pipeline = PlatePipeline.from_pretrained(
            str(Path(root) / 'models/terrain-diffusion-30m'), seed=seed, latents_batch_size=int(options['batch']),
            torch_compile=False, dtype='fp16' if precision == 'fp16' else None, caching_strategy='direct',
            onestep_latent=bool(options['onestep']),
            cache_limit=int(options['cache_mib']) * 2 ** 20, cond_snr=list(config.cond_snr), log_mode='info')
        stats = collections.defaultdict(float)

        def timed(name, fn, sync=False):
            def wrapper(*a, **k):
                if sync:
                    torch.cuda.synchronize()
                t = time.perf_counter()
                out = fn(*a, **k)
                if sync:
                    torch.cuda.synchronize()
                stats[name + '_s'] += time.perf_counter() - t
                stats[name + '_calls'] += 1
                return out
            return wrapper

        try:
            pipeline.to('cuda')
            pipeline.bind()
            if options.get('channels_last'):
                pipeline.base_model.to(memory_format=torch.channels_last)
                plain_forward = pipeline.base_model.forward
                base_forward = lambda x, *a, **k: plain_forward(x.contiguous(memory_format=torch.channels_last), *a, **k)
            else:
                base_forward = pipeline.base_model.forward

            def counted_forward(x, *a, **k):
                stats['unet_calls'] += 1
                stats['unet_samples'] += int(x.shape[0])
                if precision == 'autocast':
                    with torch.autocast('cuda', dtype=torch.float16):
                        return base_forward(x, *a, **k).float()
                return base_forward(x, *a, **k)

            if options.get('cuda_graph'):
                counted_forward = graphed_forward(torch, base_forward, precision, stats, pipeline.base_model.compute_embeddings)
            pipeline.base_model.forward = counted_forward
            noise_cache = None
            if options.get('noise_cache'):
                noise_cache = NoiseTileCache(wp)
                wp.gaussian_noise_patch = cached_noise_patch(noise_cache)
            if options.get('profile'):
                pipeline.base_model.forward = timed('unet', counted_forward, sync=True)
                wp.gaussian_noise_patch = timed('noise', wp.gaussian_noise_patch)
                pipeline._process_latent_conditioning = timed('latent_cond', pipeline._process_latent_conditioning)
                pipeline._latent_inference = timed('latent_total', pipeline._latent_inference)
            coarse_steps = int(options['coarse_steps'])
            base_coarse = pipeline._coarse_inference

            def coarse_wrapper(ctx, scheduler, *a, **k):
                if coarse_steps != 20 and not getattr(scheduler, '_dream_steps', False):
                    original = scheduler.set_timesteps
                    scheduler.set_timesteps = lambda n, *aa, **kk: original(coarse_steps, *aa, **kk)
                    scheduler._dream_steps = True
                return base_coarse(ctx, scheduler, *a, **k)

            pipeline._coarse_inference = timed('coarse', coarse_wrapper, sync=True)
            torch.cuda.synchronize()
            responses.put(dict(event='ready', model_loading_seconds=time.perf_counter() - loading))
            writer = None
            if options.get('writer_thread'):
                import concurrent.futures
                writer = concurrent.futures.ThreadPoolExecutor(max_workers=1)

            def finish(request, plane, elapsed, snap):
                h = latent_lowfreq(plane)
                result = block_mean(h, LATENT_PER_CELL)
                dest = Path(request['destination'])
                dest.mkdir(parents=True, exist_ok=True)
                temporary = dest / 'elevation_960m.tmp.npy'
                np.save(temporary, result, allow_pickle=False)
                temporary.replace(dest / 'elevation_960m.npy')
                responses.put(dict(event='block', id=request['id'], inference_seconds=elapsed,
                                   allocated_peak_mib=snap[0], reserved_peak_mib=snap[1],
                                   worker_stats=snap[2], files={'elevation_960m.npy': file_sha(dest / 'elevation_960m.npy')}))

            while True:
                request = requests.get()
                if request is None:
                    break
                (a0, a1), (b0, b1) = request['latent_slice']
                stats.clear()
                torch.cuda.reset_peak_memory_stats()
                started = time.perf_counter()
                with torch.inference_mode():
                    if request.get('warm'):
                        # coarse pixel range covering every latent window of the region (coarse cell = 32 latent px)
                        c0, c1 = a0 // 32 - 3, (a1 - 1) // 32 + 4
                        d0, d1 = b0 // 32 - 3, (b1 - 1) // 32 + 4
                        pipeline.coarse[:, c0:c1, d0:d1]
                        torch.cuda.synchronize()
                        responses.put(dict(event='warm', id=request['id'], seconds=time.perf_counter() - started,
                                           worker_stats={k: float(v) for k, v in stats.items()}))
                        continue
                    if options['slice_channels']:
                        latent = pipeline.latents[4:6, a0:a1, b0:b1]
                        plane = (latent[0] / latent[1]).cpu().numpy()
                    else:
                        latent = pipeline.latents[:, a0:a1, b0:b1]
                        plane = (latent[4] / latent[-1]).cpu().numpy()
                    if writer is None:
                        result = block_mean(latent_lowfreq(plane), LATENT_PER_CELL)
                torch.cuda.synchronize()
                elapsed = time.perf_counter() - started
                if writer is not None:
                    snap = (torch.cuda.max_memory_allocated() / 2 ** 20, torch.cuda.max_memory_reserved() / 2 ** 20,
                            {k: float(v) for k, v in stats.items()})
                    writer.submit(finish, request, plane, elapsed, snap)
                    continue
                dest = Path(request['destination'])
                dest.mkdir(parents=True, exist_ok=True)
                temporary = dest / 'elevation_960m.tmp.npy'
                np.save(temporary, result, allow_pickle=False)
                temporary.replace(dest / 'elevation_960m.npy')
                responses.put(dict(event='block', id=request['id'], inference_seconds=elapsed,
                                   allocated_peak_mib=torch.cuda.max_memory_allocated() / 2 ** 20,
                                   reserved_peak_mib=torch.cuda.max_memory_reserved() / 2 ** 20,
                                   worker_stats={k: float(v) for k, v in stats.items()},
                                   files={'elevation_960m.npy': file_sha(dest / 'elevation_960m.npy')}))
        finally:
            if writer is not None:
                writer.shutdown(wait=True)
            pipeline.close()
    except BaseException as exc:
        import traceback
        responses.put(dict(event='error', error=str(exc), traceback=traceback.format_exc()))


def generate_blocks(root, source, spec, blocks, directory, *, purpose, options=None, deadline_s=None, monitor=None):
    """Parent enforces unchanged RSS/GPU budgets, per-block memory headroom and a deadline per block."""
    options = {**DEFAULT_OPTIONS, **(options or {})}
    if options['precision'] not in PRECISIONS:
        raise ValueError('precision must be one of %s' % (PRECISIONS,))
    if int(options['scale']) < 1:
        raise ValueError('scale must be a positive integer')
    options['scale'] = int(options['scale'])
    if options['scale'] != 1:
        options['scale_origin_xz'] = scale_origin(spec)
    root = add_upstream(root)
    from diffusion.world_layout_backend import BUDGETS, BudgetExceeded, _child_rss_mib
    import psutil
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    expected = dict(algorithm=ALGORITHM, plan_identity=spec['plan_identity'], plate_identity=spec['plate_identity'],
                    world_seed=spec['world_seed'], **{k: options[k] for k in NUMERIC_KEYS})
    cache_bytes = int(options['cache_mib']) * 2 ** 20
    pending, completed = [], []
    for b in blocks:
        data = check_block(directory / b['id'], expected, b)
        (completed if data else pending).append(data or b)
    if not pending:
        return completed
    deadline = float(deadline_s or BUDGETS['wall_clock_s'])
    flight = preflight_fast(root, max(staging_bytes(b, cache_bytes) for b in pending))
    ctx = mp.get_context('spawn')
    requests, responses = ctx.Queue(), ctx.Queue()
    proc = ctx.Process(target=_worker, args=(str(root), str(source), options, requests, responses))
    proc.start()
    peak = 0.0
    min_available = float(psutil.virtual_memory().available)

    def receive():
        nonlocal peak
        start = time.perf_counter()
        while True:
            rss = _child_rss_mib(proc.pid)
            peak = max(peak, rss)
            if rss > BUDGETS['host_rss_mib']:
                raise BudgetExceeded('host_rss_mib', rss, 'resident worker exceeded original RSS cap')
            if time.perf_counter() - start > deadline:
                raise BudgetExceeded('wall_clock_s', time.perf_counter() - start, 'resident load/block deadline')
            try:
                result = responses.get(timeout=BUDGETS['poll_interval_s'])
            except queue.Empty:
                if not proc.is_alive():
                    raise RuntimeError('resident worker exited without result')
                continue
            if result['event'] == 'error':
                raise RuntimeError(result['error'] + '\n' + result['traceback'])
            return result

    try:
        ready = receive()
        if ready['event'] != 'ready':
            raise RuntimeError('worker did not become ready')
        write_json(directory / 'session.json', dict(**expected, purpose=purpose, options=options, initial_preflight=flight, **ready))
        if options['warm_coarse']:
            rows = [b['cell_zx'][0] for b in pending] + [b['cell_zx'][0] + b['cells_zx'][0] for b in pending]
            cols = [b['cell_zx'][1] for b in pending] + [b['cell_zx'][1] + b['cells_zx'][1] for b in pending]
            span = dict(id='warm', cell_zx=[min(rows), min(cols)], cells_zx=[max(rows) - min(rows), max(cols) - min(cols)])
            requests.put(dict(**span, **block_geometry(spec['first_sample_xz_m'], span), warm=True, destination=''))
            warm = receive()
            print(f'WARM coarse {warm["seconds"]:.2f}s {warm["worker_stats"]}', flush=True)
            write_json(directory / 'warm.json', warm)
        if monitor:
            monitor.start()
        depth = 2 if options.get('writer_thread') else 1   # requests kept in flight; the extra one lets the GPU start while the writer finishes
        sent = {}

        def submit(block):
            nonlocal min_available
            geometry = block_geometry(spec['first_sample_xz_m'], block)
            available = psutil.virtual_memory().available
            min_available = min(min_available, available)
            current = block_headroom(available, _child_rss_mib(proc.pid), BUDGETS['host_rss_mib'], staging_bytes(block, cache_bytes))
            dest = directory / block['id']
            sent[block['id']] = (geometry, current, time.perf_counter(), dest)
            requests.put(dict(**block, **geometry, destination=str(dest)))

        for index, block in enumerate(pending):
            for ahead in pending[index:index + depth]:
                if ahead['id'] not in sent:
                    submit(ahead)
            geometry, current, started, dest = sent.pop(block['id'])
            result = receive()
            if result['event'] != 'block' or result['id'] != block['id']:
                raise RuntimeError('worker block identity mismatch')
            if result['reserved_peak_mib'] > BUDGETS['gpu_peak_mib']:
                raise BudgetExceeded('gpu_peak_mib', result['reserved_peak_mib'], 'allocator cap exceeded')
            a = np.load(dest / 'elevation_960m.npy', mmap_mode='r')
            if tuple(a.shape) != tuple(block['cells_zx']) or not np.isfinite(a).all():
                raise ValueError('invalid block')
            min_available = min(min_available, psutil.virtual_memory().available)
            record = {**expected, **block, **geometry, **result, 'purpose': purpose, 'options': options,
                      'peak_child_rss_mib': peak, 'block_wall_seconds': time.perf_counter() - started, 'preflight': current,
                      'cells': block['cells_zx'][0] * block['cells_zx'][1],
                      'gpu_scope': 'PyTorch allocator only; driver and non-PyTorch allocations excluded'}
            write_json(dest / 'receipt.json', record)
            completed.append(record)
            write_json(directory / 'progress.json', dict(**expected, completed=len(completed), total=len(blocks),
                                                         last_block=block['id'], peak_child_rss_mib=peak))
            print(f'BLOCK {len(completed)}/{len(blocks)} {block["id"]} {result["inference_seconds"]:.2f}s '
                  f'{record["cells"] * 0.9216 / max(result["inference_seconds"], 1e-9):.1f} km2/s RSS {peak:.0f}MiB', flush=True)
        requests.put(None)
        proc.join(timeout=5)
        completed_summary = dict(peak_child_rss_mib=peak, min_available_host_bytes=min_available)
        write_json(directory / 'run-summary.json', dict(**expected, options=options, blocks=len(completed), **completed_summary,
                                                        gpu=monitor.stop() if monitor else None))
        return completed
    except BaseException as exc:
        write_json(directory / 'blocked.json', dict(**expected, error=str(exc), completed=len(completed), total=len(blocks),
                                                    peak_child_rss_mib=peak))
        raise
    finally:
        if proc.is_alive():
            proc.terminate()
        proc.join(timeout=5)
        if proc.is_alive():
            proc.kill()
            proc.join()
        requests.close()
        responses.close()
