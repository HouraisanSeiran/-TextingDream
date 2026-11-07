"""Pure geometry and cost model for the 30 m local tile lattice. No heavy imports.

Lattice: native sample n sits at X = 30*n metres (native-sample semantics, no half cell).
A tile (ix, iz) has origin_native = (512*ix, 512*iz) and 513 x 513 samples. The last row and
column duplicate the neighbour tile's first row and column, so the covered extent is closed and
neighbouring tiles leave no 30 m gap. 512 native samples = 16 world cells of 960 m, so every
tile is aligned with the world-layer grid (world cell origins are multiples of 32 native).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

NATIVE_M = 30
TILE_NATIVE = 512
TILE_SAMPLES = TILE_NATIVE + 1
WORLD_CELL_NATIVE = 32            # one 960 m world cell = 32 native samples
WORLD_CELL_M = 960
MAX_WINDOW_NATIVE = 1024          # largest decoded window measured upstream (s1-benchmark decoded)
MAX_TILES_PER_REQUEST = 16        # 4 x 4 tiles = about 61 km square

DEFAULT_BENCHMARK = Path(__file__).resolve().parents[2] / 'artifacts' / 'td-world' / 's1-benchmark.json'
# Used only when the benchmark file is absent; flagged as fallback in every estimate.
FALLBACK_DECODED = dict(inference_seconds=28.65, side_native=1024, model_loading_seconds=4.19,
                        cold_model_loading_seconds=33.84, reserved_peak_mib=3136.0, allocated_peak_mib=2181.0)


def tile_id(ix, iz):
    return f'x{ix:+04d}z{iz:+04d}'


def tile_window(ix, iz):
    ox, oz = ix * TILE_NATIVE, iz * TILE_NATIVE
    x0, z0 = NATIVE_M * ox, NATIVE_M * oz
    return dict(id=tile_id(ix, iz), ix=ix, iz=iz, origin_native_xz=[ox, oz], side_native=TILE_SAMPLES,
                first_sample_xz_m=[x0, z0], spacing_m=NATIVE_M,
                extent_m=[x0, z0, x0 + NATIVE_M * TILE_NATIVE, z0 + NATIVE_M * TILE_NATIVE])


def box_from_center(center_x_m, center_z_m, size_m):
    half = float(size_m) / 2
    return (center_x_m - half, center_z_m - half, center_x_m + half, center_z_m + half)


def tiles_for_box(x0, z0, x1, z1):
    """Tiles needed so every sample position in the closed box is covered. Deterministic order (z, x)."""
    if not all(math.isfinite(v) for v in (x0, z0, x1, z1)):
        raise ValueError('non-finite box')
    if x1 < x0 or z1 < z0:
        raise ValueError('empty box')
    span = NATIVE_M * TILE_NATIVE
    def rng(lo, hi):
        a = math.floor(lo / span)
        b = max(a, math.ceil(hi / span) - 1)
        return range(a, b + 1)
    return [tile_window(ix, iz) for iz in rng(z0, z1) for ix in rng(x0, x1)]


def decoded_rate(benchmark_path=None):
    """Per-native-pixel decoded cost from the measured benchmark (mean over ok decoded pages)."""
    path = Path(benchmark_path) if benchmark_path else DEFAULT_BENCHMARK
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        rows = [p for p in data['pages'] if p.get('mode') == 'decoded' and p.get('ok')]
        loads = [p['model_loading_seconds'] for p in data['pages'] if p.get('ok')]
        if not rows:
            raise ValueError('no decoded rows')
        sec = sum(p['inference_seconds'] / p['side_native'] ** 2 for p in rows) / len(rows)
        return dict(seconds_per_native_px=sec, model_loading_seconds=min(p['model_loading_seconds'] for p in rows),
                    cold_model_loading_seconds=max(loads),
                    reserved_peak_mib=max(p['reserved_peak_mib'] for p in rows),
                    allocated_peak_mib=max(p['allocated_peak_mib'] for p in rows),
                    basis=f'{path.name}: {len(rows)} measured decoded page(s), inference seconds / side^2 (linear in area assumed)',
                    fallback=False)
    except (OSError, KeyError, ValueError, TypeError):
        f = FALLBACK_DECODED
        return dict(seconds_per_native_px=f['inference_seconds'] / f['side_native'] ** 2,
                    model_loading_seconds=f['model_loading_seconds'], cold_model_loading_seconds=f['cold_model_loading_seconds'],
                    reserved_peak_mib=f['reserved_peak_mib'], allocated_peak_mib=f['allocated_peak_mib'],
                    basis='FALLBACK constants copied from s1-benchmark decoded page (benchmark file unreadable)', fallback=True)


def tile_cost(rate, tiles=1):
    return dict(tiles=tiles, inference_seconds=tiles * TILE_SAMPLES ** 2 * rate['seconds_per_native_px'],
                disk_bytes=tiles * (TILE_SAMPLES ** 2 * 5 + 4096))
