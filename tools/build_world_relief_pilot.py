"""Build the finite world-relief experiment; run --help for parameters."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.world_relief.product import build

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',type=Path,default=ROOT.parent/'山川形意Terragenesis/.scratch/plate-formation-coast-20261101/shaped-run-v4/product.npz')
    ap.add_argument('--out',type=Path,default=ROOT/'artifacts/world-relief-pilot')
    ap.add_argument('--spacing',type=int,default=1000)
    ap.add_argument('--steps',type=int,default=12)
    ap.add_argument('--variant',choices=['v1','v2'],default='v1')
    args=ap.parse_args()
    if args.variant=='v2' and args.out==ROOT/'artifacts/world-relief-pilot':
        args.out=ROOT/'artifacts/world-relief-pilot-v2'
    build(args.source,args.out,args.spacing,args.steps,args.variant)

if __name__=='__main__':
    main()
