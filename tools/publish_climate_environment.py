"""Explicit environment plan/publication; no default climate or story selection."""
import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from app.world_gen import climate_environment_stage as stage


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=('plan','publish'),default='plan')
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--climate',type=Path,required=True)
    p.add_argument('--hydrology',type=Path)
    p.add_argument('--out',type=Path)
    p.add_argument('--expected-source-identity',required=True)
    p.add_argument('--expected-climate-identity',required=True)
    p.add_argument('--expected-hydrology-identity')
    a=p.parse_args(argv)
    options=dict(expected_source_identity=a.expected_source_identity,
        expected_climate_identity=a.expected_climate_identity,expected_hydrology_identity=a.expected_hydrology_identity)
    if a.mode=='publish':
        if a.hydrology is None or a.out is None:p.error('--hydrology and --out required to publish')
        result=stage.publish(a.source,a.climate,a.hydrology,a.out,**options)
    else:result=stage.plan(a.source,a.climate,a.hydrology,**options)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
