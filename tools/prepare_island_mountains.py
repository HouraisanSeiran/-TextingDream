"""Explicit eligible-island TD task. Empty/dry plans never start a model."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.world_gen.island_mountains import prepare_mountains


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('skeleton','island-product-path','expected-island-identity','plan','expected-plan-identity','out-root','reason'):
        parser.add_argument('--'+name,required=True)
    parser.add_argument('--skeleton-run')
    parser.add_argument('--raw-root',help='Explicit existing raw cache root; identity/SHA checked; no raw overwrites')
    parser.add_argument('--tile',nargs=2,type=int,action='append',metavar=('IX','IZ'))
    parser.add_argument('--dry-run',action='store_true')
    parser.add_argument('--report',help='New report file; existing reports are never overwritten')
    args=parser.parse_args(argv)
    if args.report and Path(args.report).exists():
        raise FileExistsError(args.report)
    result=prepare_mountains(source=args.skeleton,product_path=args.island_product_path,
        island_identity=args.expected_island_identity,plan_path=args.plan,plan_identity=args.expected_plan_identity,
        out_root=args.out_root,reason=args.reason,skeleton_run=args.skeleton_run,dry_run=args.dry_run,tile_indices=args.tile,raw_root_override=args.raw_root)
    rendered=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    if args.report:
        path=Path(args.report);path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('x',encoding='utf-8') as stream:
            stream.write(rendered)
    print(rendered)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
