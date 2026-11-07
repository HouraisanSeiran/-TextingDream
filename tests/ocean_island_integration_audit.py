"""Read-only CPU audit of a published fast world and its frozen island sidecar."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
TG=ROOT.parent/'山川形意Terragenesis'
sys.path.insert(0,str(TG))
from app.world_gen import fast_relief as fr, ocean_island_adapter as bridge
from app.world_relief import td_resident as td
from terrain_pipeline.ocean_island_consumers import connected_ocean, sample_td_condition
from diffusion.physical_config import PhysicalGenerationConfig


def audit(world,source,islands,expected_identity,skeleton_run):
    world=Path(world)
    manifest=json.loads((world/'manifest.json').read_text(encoding='utf-8'))
    assert fr.identity_of(manifest)==manifest['identity']
    binding=bridge.load_binding(source,islands,expected_identity,skeleton_run)
    assert manifest['lineage']==[binding.product.source.identity,expected_identity]
    published=manifest['ocean_islands']['binding']
    sidecar=manifest['ocean_islands']['binding_file']
    assert bridge.file_sha(world/sidecar['file'])==sidecar['sha256']
    saved_binding=json.loads((world/sidecar['file']).read_text(encoding='utf-8'))
    assert saved_binding==published
    for key in ('plate_identity','source_file_sha256','island_identity','island_file_sha256','condition_policy'):
        assert published[key]==binding.record[key],key
    for name,digest in manifest['files'].items():
        assert bridge.file_sha(world/name)==digest,name
    for name,record in manifest['vectors'].items():
        assert bridge.file_sha(world/record['file'])==record['sha256'],name
    for rel,digest in published['imported_sha256'].items():
        assert bridge.file_sha(TG/rel)==digest,rel
    for rel,digest in manifest['reused_code']['terragenesis_sha256'].items():
        assert bridge.file_sha(TG/rel)==digest,rel
    for name,digest in manifest['reused_code']['local_sha256'].items():
        assert bridge.file_sha(ROOT/'app/world_gen'/name)==digest,name
    h=np.load(world/'elevation_m.npy');status=np.load(world/'status.npy');lagoon=np.load(world/'registered_lagoon.npy')
    assert h.dtype==np.float32 and np.isfinite(h).all()
    assert np.all(status[h>=0]==5) and np.all(h[status==3]<0)
    assert np.all(status[lagoon]==4) and np.all(h[lagoon]<0)
    assert np.isnan(np.load(world/'water_surface_m.npy')[lagoon]).all()
    expected_ocean=connected_ocean(h,lagoon)
    np.testing.assert_array_equal(status==3,expected_ocean)
    np.testing.assert_array_equal(status==4,(h<0)&~expected_ocean)
    assert manifest['statistics']['land_fraction']==float((h>=0).mean())
    first=manifest['grid']['first_sample_xz_m'];spacing=manifest['grid']['spacing_m']
    x=first[0]+np.arange(h.shape[1])*spacing;z=first[1]+np.arange(h.shape[0])*spacing
    sk=fr.load_skeleton(source,binding.product.source.identity)
    terrain_builder={fr.ALGORITHM:fr.build_terrain,fr.ALGORITHM_V2:fr.build_terrain_v2,
                     fr.ALGORITHM_V3:fr.build_terrain_v3}[manifest['algorithm_version']]
    original=terrain_builder(sk,manifest['parameters'])['elevation']
    full_protection_cells=0;protected_max_error=0.;lagoon_mismatch=0
    unprotected_negative_cells=0;unprotected_negative_max_error=0.
    for start in range(0,len(z),64):
        q=binding.product.query(x[None,:],z[start:start+64,None])
        full=q['protection_weight']==1
        full_protection_cells+=int(full.sum())
        if full.any():
            error=np.abs(h[start:start+64][full]-q['elevation_m'].astype(np.float32)[full])
            protected_max_error=max(protected_max_error,float(error.max()))
        lagoon_mismatch+=int(np.count_nonzero(lagoon[start:start+64]!=(q['lagoon']&(h[start:start+64]<0))))
        original_block=original[start:start+64]
        fixed=(original_block<0)&(q['protection_weight']==0)
        unprotected_negative_cells+=int(fixed.sum())
        if fixed.any():
            unprotected_negative_max_error=max(unprotected_negative_max_error,
                float(np.max(abs(h[start:start+64][fixed]-original_block[fixed]))))
    assert protected_max_error==0,protected_max_error
    assert lagoon_mismatch==0,lagoon_mismatch
    assert unprotected_negative_max_error==0,unprotected_negative_max_error
    vectors=json.loads((world/'vectors/ocean-islands.json').read_text(encoding='utf-8'))
    assert {row['feature_id'] for row in vectors['features']}=={f.feature_id for f in binding.product.features}
    assert vectors['island_identity']==expected_identity
    for name in ('frozen_island_land_fraction','protected_fraction','frozen_island_lagoon_fraction'):
        fraction=np.load(world/(name+'.npy'))
        assert fraction.shape==h.shape and ((fraction>=0)&(fraction<=1)).all()
    config=PhysicalGenerationConfig()
    factory,_=td.periodic_factory(source,config,island_product_path=islands,expected_island_identity=expected_identity,skeleton_run_path=skeleton_run)
    bounds=binding.product.source.bounds_m
    ix0=int(np.floor(bounds[0]/config.conditioning_spacing_m));iz0=int(np.floor(bounds[1]/config.conditioning_spacing_m))
    ix1=int(np.ceil(bounds[2]/config.conditioning_spacing_m));iz1=int(np.ceil(bounds[3]/config.conditioning_spacing_m))
    raw=factory.sample_raw(ix0,iz0,ix1,iz1)
    cx=np.arange(ix0,ix1)[None,:]*config.conditioning_spacing_m
    cz=np.arange(iz0,iz1)[:,None]*config.conditioning_spacing_m
    with np.load(source,allow_pickle=False) as archive:
        source_manifest=json.loads(str(archive['manifest_json']))
        baseline=td.sample_periodic(archive['final/elevation_m'],source_manifest['config'],cx,cz)
    expected=sample_td_condition(binding.product,cx,cz,baseline,periodic=True)['elevation_m']
    condition_error=float(np.max(abs(raw[0]-expected)))
    assert condition_error<=.001,condition_error
    assert np.max(abs(raw[0]-baseline))>100
    quota=manifest['ocean_islands']['quota']
    assert quota['final_fraction']==float((h<0).mean())
    return dict(world_identity=manifest['identity'],plate_identity=binding.product.source.identity,island_identity=expected_identity,
                world_shape_zx=list(h.shape),world_spacing_m=spacing,all_final_field_files_sha_verified=True,
                full_protection_cells=full_protection_cells,protected_float32_max_error_m=protected_max_error,
                registered_lagoon_cells=int(lagoon.sum()),lagoon_mismatch_cells=lagoon_mismatch,
                unprotected_original_negative_cells=unprotected_negative_cells,
                unprotected_original_negative_max_error_m=unprotected_negative_max_error,
                status_counts={str(int(k)):int(v) for k,v in zip(*np.unique(status,return_counts=True))},
                frozen_vector_features=len(vectors['features']),ocean_quota=quota,
                td_condition=dict(shape_zx=list(raw[0].shape),spacing_m=config.conditioning_spacing_m,model_generation=False,
                                  direct_public_sampler_max_abs_error_m=condition_error,
                                  max_island_effect_m=float(np.max(abs(raw[0]-baseline))),
                                  new_land_condition_nodes=int(((raw[0]>=0)&(baseline<0)).sum()),
                                  policy=factory.island_binding['condition_policy'],
                                  limitation='Actual raw condition wiring verified; tiny islands may fall between 7680m nodes. TD model/coastline response not measured.'),
                source_and_import_hashes=binding.record)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('world','source','islands','expected-identity','skeleton-run','out'):
        parser.add_argument('--'+name,required=True)
    args=parser.parse_args()
    output=Path(args.out)
    if output.exists():
        raise FileExistsError(output)
    result=audit(args.world,args.source,args.islands,args.expected_identity,args.skeleton_run)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2,allow_nan=False))
