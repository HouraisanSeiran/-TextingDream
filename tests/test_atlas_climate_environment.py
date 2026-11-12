"""Saved environment atlas consumption; tiny synthetic source, no world generation."""
from dataclasses import replace
import hashlib
import json

import numpy as np
import pytest

from app.map_render import load_styles
from app.world_relief import atlas
from app.terrain_source import _canon
from tests.test_atlas_glacier_surface import Source


def environment(tmp_path,identifier=None):
    src=Source(ice=True)
    shape=src.arrays['status'].shape
    ids=np.resize(np.array(list(atlas.SAVED_BIOMES),np.uint16),shape) if identifier is None else np.full(shape,identifier,np.uint16)
    src.arrays.update(biome=ids,temperature_c=np.full(shape,12.),precipitation_mm_yr=np.full(shape,.5),
        discharge_m3_s=np.full(shape,2.),snow_swe_mm=np.zeros(shape))
    # New-year dynamic support, not old Source fixture's all-20m ice.
    src.arrays['glacier_ice_thickness_m'][:]=0
    src.arrays['glacier_ice_surface_m'][:]=src.arrays['elevation_m']
    src.arrays['glacier_coverage_fraction'][:]=0
    src.info.layers=tuple(src.arrays)
    doc=dict(schema='world-map-product-v1',climate_environment=dict(schema='dream-climate-environment-publication-1',
        source_identity='terrain-id',climate_identity='dry-continuous-id',hydrology_identity='hydrology-id',
        year=1,calendar='noleap365'),stable_biome_ids={str(k):v[0] for k,v in atlas.SAVED_BIOMES.items()})
    src.info.identity=hashlib.sha256(_canon(doc).encode()).hexdigest()
    doc['identity']=src.info.identity
    (tmp_path/'manifest.json').write_text(json.dumps(doc),encoding='utf-8')
    return src,atlas.product_from_source(src,tmp_path,rows=5)


def test_actual_saved_ids_palette_no_north_noise_reclassification(tmp_path):
    src,p=environment(tmp_path)
    params=replace(atlas.AtlasParams(width_px=80),biome_smooth_m=0.)
    a=atlas.analyse(p,params)
    np.testing.assert_array_equal(a['biome'],src.arrays['biome'])
    for identifier,(_,_,colour) in atlas.SAVED_BIOMES.items():
        mask=p.saved_biome==identifier
        np.testing.assert_allclose(a['biome_rgb'][mask],np.broadcast_to(atlas.hex_rgb(colour),(mask.sum(),3)))
    assert not a['forest'][np.isin(p.saved_biome,[0,4,5,11,12,65535])].any()
    assert np.all(a['natural_type'][p.saved_biome==1]==3)
    assert np.all(a['natural_type'][p.saved_biome==10]==2)
    # T/P remain actual saved fields; altering display proxy thresholds cannot reclassify them.
    b=atlas.analyse(p,replace(params,forest_threshold=-100,biome_lapse_m=1,forest_coast_km=.1))
    np.testing.assert_array_equal(a['biome'],b['biome'])
    np.testing.assert_array_equal(a['forest'],b['forest'])
    view=atlas.full_view(p,83)
    d=atlas.display_fields(p,a,view,params)
    assert set(np.unique(d['biome_id']))<=set(np.unique(p.saved_biome))
    assert not d['forest'][np.isin(d['biome_id'],[0,4,5,11,12,65535])].any()


def test_saved_species_weights_ignore_latitude_and_coast():
    names=['oak','spruce','teak','acacia']
    f=dict(h=np.array([500.,500.,500.,500.]),saved_biome=np.array([7,10,1,3]))
    w=atlas._tree_weights(names,f,atlas.AtlasParams(),1.)
    assert np.argmax(w,axis=1).tolist()==[0,1,2,3]
    assert np.array_equal(w,atlas._tree_weights(names,dict(f,north=np.ones(4),dsea=np.zeros(4)),atlas.AtlasParams(),1.))


def test_snow_is_year_end_stock_not_elevation_proxy_and_new_ice(tmp_path):
    src,p=environment(tmp_path,4)
    p.elevation[:]=4500
    p.saved_snow_swe[8:12,12:18]=50
    params=atlas.AtlasParams(width_px=80)
    view=atlas.full_view(p,80)
    a=atlas.analyse(p,params);df=atlas.display_fields(p,a,view,params)
    assert df['saved_snow_alpha'].max()>0 and df['glacier_mask'].sum()==0
    style=load_styles()['styles']['simple']
    one=atlas.paint_map(p,df,view,params,style)
    two=atlas.paint_map(p,df,view,replace(params,snow_base_m=-10000,snow_aspect_m=9999,snow_noise_m=9999),style)
    np.testing.assert_array_equal(one,two)
    assert np.count_nonzero(df['saved_snow_alpha'])<df['saved_snow_alpha'].size


def test_legacy_without_saved_layers_keeps_proxy_and_metadata_rejects_wrong_ids(tmp_path):
    src=Source(ice=False)
    p=atlas.product_from_source(src)
    assert p.saved_biome is None and p.environment_metadata is None
    a=atlas.analyse(p,atlas.AtlasParams())
    assert set(np.unique(a['biome']))<=set(range(10))
    src,p=environment(tmp_path)
    doc=json.loads((tmp_path/'manifest.json').read_text());doc['stable_biome_ids']['10']='legacy-id-10'
    doc.pop('identity');src.info.identity=hashlib.sha256(_canon(doc).encode()).hexdigest();doc['identity']=src.info.identity
    (tmp_path/'manifest.json').write_text(json.dumps(doc))
    with pytest.raises(ValueError,match='id/name'):atlas.product_from_source(src,tmp_path)


def test_small_saved_render_summary_provenance_and_no_proxy_legend(tmp_path):
    _,p=environment(tmp_path,4)
    params=replace(atlas.AtlasParams(width_px=80),tree_keep=0.,tree_keep_edge=0.)
    L=atlas.build_atlas(p,params,deco_kind='none')
    summary=atlas.summarize(L)
    assert summary['climate_environment']['climate_identity']=='dry-continuous-id'
    prov=atlas.provenance(p,L,params,{})
    assert prov['climate_environment']['hydrology_identity']=='hydrology-id'
    assert '极干旱' in ' '.join(prov['layers']['approximate'])
    assert '北冷' not in ' '.join(prov['layers']['approximate'])
    assert 'not realized' in prov['vegetation_display']['scope']
    assert '保存气候' in ''.join(atlas._natural_legend_footer(L))
    assert '保存气候' in str(atlas.legend_rows(L))
    assert not any(s['kind']=='tree' for s in L.symbols)
