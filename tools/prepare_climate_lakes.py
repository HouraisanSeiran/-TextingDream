"""Independent saved-liquid surface-water diagnostic; defaults to read-only plan."""
import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from app.world_gen import climate_lake_stage as stage


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode', choices=('plan', 'prepare'), default='plan')
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--climate', type=Path, required=True)
    p.add_argument('--hydrology', type=Path, required=True)
    p.add_argument('--expected-source-identity', required=True)
    p.add_argument('--expected-climate-identity', required=True)
    p.add_argument('--expected-hydrology-identity', required=True)
    p.add_argument('--out', type=Path)
    p.add_argument('--max-cells', type=int, default=1024)
    p.add_argument('--max-memory-bytes', type=int, default=512 * 2**20)
    p.add_argument('--max-spill-path-nodes', type=int, default=2000000)
    p.add_argument('--closed-rim', action='store_true', help='Do not register finite-domain rim outlets')
    a = p.parse_args(argv)
    options = dict(expected_source_identity=a.expected_source_identity,
                   expected_climate_identity=a.expected_climate_identity,
                   expected_hydrology_identity=a.expected_hydrology_identity,
                   finite_boundary=not a.closed_rim, max_cells=a.max_cells,
                   max_memory_bytes=a.max_memory_bytes)
    if a.mode == 'plan':
        result = stage.plan(a.source, a.climate, a.hydrology, **options)
    else:
        if a.out is None:
            p.error('--out required for prepare')
        result = stage.prepare(a.source, a.climate, a.hydrology, a.out,
                               max_spill_path_nodes=a.max_spill_path_nodes, **options)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
