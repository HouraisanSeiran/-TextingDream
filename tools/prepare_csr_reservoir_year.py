"""Read-only plan by default; explicit bounded TG CSR saved-liquid year."""
import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.world_gen import csr_reservoir_year as stage


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode', choices=('plan','prepare','finalize'), default='plan')
    for name in ('source','climate','hydrology'):
        p.add_argument('--'+name, type=Path)
        p.add_argument('--expected-'+name+'-identity')
    p.add_argument('--out', type=Path)
    p.add_argument('--checkpoint', type=Path)
    p.add_argument('--min-display-area-m2',type=float,default=0.)
    p.add_argument('--dry-valley-min-area-m2',type=float,default=1e10)
    p.add_argument('--display-policy')
    p.add_argument('--max-cells', type=int, default=1024)
    p.add_argument('--max-memory-bytes', type=int, default=3*2**30)
    p.add_argument('--max-owners', type=int, default=10000)
    p.add_argument('--max-steps', type=int, default=4096)
    p.add_argument('--wall-seconds', type=float, default=1200.)
    p.add_argument('--face-conductance-m-s', type=float, default=.6)
    p.add_argument('--closed-rim', action='store_true')
    a = p.parse_args(argv)
    options = dict(expected_source_identity=a.expected_source_identity, expected_climate_identity=a.expected_climate_identity,
        expected_hydrology_identity=a.expected_hydrology_identity, finite_boundary=not a.closed_rim,
        max_cells=a.max_cells, max_memory_bytes=a.max_memory_bytes, max_owners=a.max_owners,
        max_steps=a.max_steps, wall_seconds=a.wall_seconds, face_conductance_m_s=a.face_conductance_m_s)
    display=dict(min_display_area_m2=a.min_display_area_m2,dry_valley_min_area_m2=a.dry_valley_min_area_m2,
                 display_policy=a.display_policy)
    if a.mode in ('prepare','finalize') and a.out is None:
        p.error('--out required for prepare/finalize')
    if a.mode == 'finalize':
        if a.checkpoint is None:
            p.error('--checkpoint required for display-only finalize')
        result=stage.finalize_checkpoint(a.checkpoint,a.out,**display)
    else:
        if not all((a.source,a.climate,a.hydrology,a.expected_source_identity,a.expected_climate_identity,a.expected_hydrology_identity)):
            p.error('source/climate/hydrology paths and identities required for plan/prepare')
        result = (stage.plan(a.source,a.climate,a.hydrology,**options) if a.mode == 'plan' else
                  stage.prepare(a.source,a.climate,a.hydrology,a.out,checkpoint_dir=a.checkpoint,**display,**options))
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)


if __name__ == '__main__':
    main()
