"""Explicit saved-climate snow/ice water sidecar; defaults to plan, never picks a candidate."""
import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from app.world_gen import climate_hydrology_stage as stage


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=('plan','prepare'),default='plan')
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--climate',type=Path,required=True)
    p.add_argument('--expected-source-identity',required=True)
    p.add_argument('--expected-climate-identity',required=True)
    p.add_argument('--regions-json',type=Path,required=True,help='Explicit list of {window_zx,old_identity}; [] means no dynamic regions')
    p.add_argument('--out',type=Path)
    p.add_argument('--parameters-json',type=Path,help='prepare kwargs: diagnostic_snow_parameters, glacier_snow_config, glacier_config, max_memory_bytes')
    a=p.parse_args(argv)
    regions=json.loads(a.regions_json.read_text(encoding='utf-8'))
    options=dict(expected_source_identity=a.expected_source_identity,expected_climate_identity=a.expected_climate_identity)
    if a.mode=='plan':
        if a.parameters_json:
            p.error('plan is source sizing only; no parameters-json accepted')
        result=stage.plan(a.source,a.climate,regions,**options)
    else:
        if a.out is None:
            p.error('--out required for prepare')
        extra=json.loads(a.parameters_json.read_text(encoding='utf-8')) if a.parameters_json else {}
        if set(extra)-{'diagnostic_snow_parameters','glacier_snow_config','glacier_config','max_memory_bytes'}:
            p.error('Unsupported sidecar configuration')
        result=stage.prepare(a.source,a.climate,regions,a.out,**options,**extra)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
