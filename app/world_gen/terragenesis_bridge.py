"""Single seam for Terragenesis as the map-generation physics kernel.

织梦 owns jobs, product directories, ``map_source`` consumption and player basemaps.
Terragenesis owns tectonic / islands / mountains / drainage / world_processes / climate.
Heavy stages run under ``runtime/venv`` (see ``web_jobs.TG_PYTHON``); this module only
probes paths and records the public surface — it does not import numba-heavy modules at
import time.
"""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3] / '山川形意Terragenesis'
TG_PYTHON = ROOT / 'runtime' / 'venv' / 'Scripts' / 'python.exe'

# Author-chain modules 织梦 actually calls (import or freeze SHA).
PUBLIC_MODULES = (
    'terrain_pipeline/tectonic.py',
    'terrain_pipeline/ocean_islands.py',
    'terrain_pipeline/ocean_island_consumers.py',
    'terrain_pipeline/island_volcanoes.py',
    'terrain_pipeline/island_volcanoes_v4.py',
    'terrain_pipeline/island_mountains.py',
    'terrain_pipeline/drainage.py',
    'terrain_pipeline/world_processes.py',
    'terrain_pipeline/world_geology.py',
    'terrain_pipeline/world_climate.py',
    'terrain_pipeline/procedural_mountain_erosion.py',
    'terrain_pipeline/common_infra.py',
)

# Product schemas that cross the seam into 织梦.
PRODUCT_SCHEMAS = (
    'dream-world-skeleton-plate-v1',          # written by 织梦 skeleton from tectonic evolve
    'ocean-islands-frozen-v1',                # TG ocean_islands (algorithm v5 current)
    'island-mountain-plan-v3',               # TG island_mountains
    'terragenesis-fast-relief-v1',           # written by 织梦 fast_relief (uses TG drainage)
    'terragenesis-world-process-v1',         # TG world_processes nested under fast
    'terragenesis-local30-v1',               # 织梦 local30 / TG detail
    'terragenesis-regional-climate-v1',      # TG world_climate (opt-in query)
)

ISLAND_FILES = (
    'terrain_pipeline/ocean_islands.py',
    'terrain_pipeline/ocean_island_consumers.py',
    'terrain_pipeline/island_volcanoes.py',
    'terrain_pipeline/island_volcanoes_v4.py',
)


def tg_root() -> Path:
    return ROOT


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def module_sha_map(files=PUBLIC_MODULES) -> dict:
    out = {}
    for rel in files:
        path = ROOT / rel
        out[rel] = file_sha(path) if path.is_file() else None
    return out


def island_producer_stack() -> dict:
    """Live SHA map recorded on new ocean-island bindings."""
    return {rel: file_sha(ROOT / rel) for rel in ISLAND_FILES}


def probe(*, check_import: bool = False) -> dict:
    """Readiness report for author UI / options (no TG algorithm import into this process).

    ``check_import=True`` spawns TG_PYTHON once to verify public modules import; keep it off
    on hot options() paths — file presence is enough for the panel.
    """
    present = {rel: (ROOT / rel).is_file() for rel in PUBLIC_MODULES}
    missing = [rel for rel, ok in present.items() if not ok]
    py = TG_PYTHON
    import_ok = None
    import_error = None
    if check_import and py.is_file():
        code = (
            'import importlib\n'
            'mods=["terrain_pipeline.tectonic","terrain_pipeline.ocean_islands",'
            '"terrain_pipeline.drainage","terrain_pipeline.island_mountains",'
            '"terrain_pipeline.world_processes","terrain_pipeline.world_climate"]\n'
            'bad=[]\n'
            'for m in mods:\n'
            '  try: importlib.import_module(m)\n'
            '  except Exception as e: bad.append(f\"{m}:{type(e).__name__}\")\n'
            'print("ok" if not bad else "fail:"+",".join(bad))\n'
        )
        import subprocess
        try:
            out = subprocess.run([str(py), '-c', code], capture_output=True, text=True, timeout=60,
                                 cwd=str(ROOT), creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            line = (out.stdout or '').strip().splitlines()[-1] if out.stdout else ''
            import_ok = line == 'ok'
            if not import_ok:
                import_error = line or (out.stderr or '')[:300]
        except Exception as exc:
            import_ok = False
            import_error = f'{type(exc).__name__}: {exc}'
    return dict(
        root=str(ROOT), root_present=ROOT.is_dir(),
        tg_python=str(py), tg_python_present=py.is_file(),
        modules_present=present, modules_missing=missing,
        import_ok=import_ok, import_error=import_error,
        product_schemas=list(PRODUCT_SCHEMAS),
        notes=[
            '作者链：骨架/岛/岛山/fast/details 子进程用 TG_PYTHON；地图读取走 map_source',
            '气候产品为可选侧车，经 map_source kind terragenesis-regional-climate 或 SavedClimateMap 查询',
            '玩家地图默认 world_map_product；civ-atlas 需 TEXTILE_CIV_ATLAS=1',
        ],
    )


def ensure_path():
    """Append TG repo to sys.path for read-only imports (caller must use TG venv for numba)."""
    import sys
    root = str(ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    return ROOT
