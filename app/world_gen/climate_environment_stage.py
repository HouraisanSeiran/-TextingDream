"""Publish a NEW frozen world-map environment from exact saved climate/hydrology.

No recomputation, default selection, terrain evolution or river-vector guessing.
The independent hydrology sidecar remains independently queryable, not a climate.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

import numpy as np

from app.map_source import load_source
from app.world_gen import climate_world_stage as cs
from app.world_gen.world_climate_adapter import SavedClimateMap

SCHEMA = 'dream-climate-environment-publication-1'


def _file(root, relative, digest):
    path = (root/relative).resolve()
    if not path.is_relative_to(root) or cs._sha(path) != digest:
        raise ValueError('Saved sidecar/source path or hash differs')
    return path


class SavedClimateHydrology:
    """Verify sidecar files/binding once; selected month/window reads use memmaps."""
    def __init__(self, source_map, climate_product, hydrology_product, *,
                 expected_source_identity, expected_climate_identity, expected_hydrology_identity=None):
        if not expected_source_identity or not expected_climate_identity:
            raise ValueError('Explicit source and climate identities required')
        self.climate = SavedClimateMap(source_map,climate_product,
            expected_source_identity=expected_source_identity,expected_climate_identity=expected_climate_identity)
        self.source = cs.climate_source_from_map(source_map,expected_identity=expected_source_identity)
        self.root = Path(hydrology_product).resolve()
        self.manifest = json.loads((self.root/'manifest.json').read_text(encoding='utf-8'))
        m = self.manifest
        from terrain_pipeline.common_infra import identity,array_sha256
        if (m.get('schema') != 'dream-climate-hydrology-year-1' or m.get('status') != 'complete'
                or m.get('identity') != identity({}, {k:v for k,v in m.items() if k != 'identity'})
                or (expected_hydrology_identity is not None and m['identity'] != expected_hydrology_identity)):
            raise ValueError('Hydrology identity/schema/completion differs')
        shape = self.source['elevation_m'].shape
        b = m['binding']; s = self.source
        if (b['source_identity'] != expected_source_identity or b['climate_identity'] != expected_climate_identity
                or b['climate_manifest_identity'] != self.climate.manifest_identity
                or b['world_seed'] != s['world_seed']
                or b['grid'] != dict(first_xz_m=s['first_xz_m'],spacing_m=s['spacing_m'],shape_zx=list(shape))
                or b['receiver_sha256'] != array_sha256(np.asarray(s['receiver'],np.int64).ravel())
                or b['order_sha256'] != array_sha256(s['order'])
                or m.get('calendar') != 'noleap365' or m.get('year') != 1
                or m.get('month_days') != self.climate.metadata['month_days']):
            raise ValueError('Hydrology source/climate/grid/receiver/calendar binding differs')
        if not m.get('files') or not m.get('fields'):
            raise ValueError('Missing hydrology file/field descriptors')
        for relative,digest in m['files'].items():
            _file(self.root,relative,digest)
        required = {'monthly_routed_volume_m3','final_soil_water_mm','final_snow_swe_mm',
                    'final_ice_swe_mm','dynamic_glacier_mask','receiver','order'}
        if not required <= set(m['fields']):
            raise ValueError('Missing hydrology publication fields')
        for name,spec in m['fields'].items():
            if m['files'].get(spec['file']) != spec['sha256']:
                raise ValueError('Hydrology field/file binding differs')
            value = np.load(self.root/spec['file'],mmap_mode='r',allow_pickle=False)
            expected_shape = (12,*shape) if name.startswith('monthly_') else ((int(np.prod(shape)),) if name=='order' else shape)
            if (list(value.shape) != spec['shape'] or str(value.dtype) != spec['dtype']
                    or value.shape != expected_shape):
                raise ValueError('Hydrology field descriptor/grid differs')
            value._mmap.close()
        for name,expected in [('receiver',s['receiver']),('order',s['order'])]:
            if not np.array_equal(self.query([name])['arrays'][name],expected):
                raise ValueError('Saved hydrology receiver/order differs')
        if m['fields']['monthly_routed_volume_m3']['units'] != 'm3/month':
            raise ValueError('Hydrology routed volume must be m3/month')
        for name in ('final_soil_water_mm','final_snow_swe_mm','final_ice_swe_mm'):
            if m['fields'][name]['units'] != 'mm':
                raise ValueError('Hydrology terminal stock must be mm water')
        if 'regions.json' not in m['files']:
            raise ValueError('Hydrology region record not hash bound')
        self.regions = json.loads((self.root/'regions.json').read_text(encoding='utf-8'))
        if [r['binding'] for r in self.regions] != b['regions']:
            raise ValueError('Hydrology region record binding differs')
        parent = json.loads((Path(source_map)/'manifest.json').read_text(encoding='utf-8'))
        mask = np.zeros(shape,bool)
        for r in self.regions:
            rb = r['binding']; win = rb['window_zx']
            if (len(win) != 4 or any(type(i) is not int for i in win)
                    or not (0 <= win[0] < win[2] <= shape[0] and 0 <= win[1] < win[3] <= shape[1])):
                raise ValueError('Hydrology region grid differs')
            sl = np.s_[win[0]:win[2],win[1]:win[3]]
            if (mask[sl].any() or not any(v['identity'] == rb['old_identity'] and v['window_zx'] == win
                    for v in parent.get('glacier_regions',[]))
                    or rb['source_identity'] != expected_source_identity
                    or rb['new_climate_identity'] != expected_climate_identity
                    or r['metadata'].get('completed') is not True
                    or r['metadata'].get('completed_years') != 1
                    or r['ledger'].get('boundary_ice_out_m3') != 0):
                raise ValueError('Hydrology selected region source/completion differs')
            mask[sl] = True
        actual_mask = self.query(['dynamic_glacier_mask'])['arrays']['dynamic_glacier_mask']
        if actual_mask.dtype != np.dtype('bool') or not np.array_equal(mask,actual_mask):
            raise ValueError('Hydrology dynamic region support differs')

    def query(self,fields,*,months=None,window=None):
        names = [fields] if isinstance(fields,str) else list(fields)
        specs = self.manifest['fields']
        if any(name not in specs for name in names):
            raise ValueError('Hydrology field unavailable')
        if months is not None and (not len(months) or any(type(i) is not int or not 1 <= i <= 12 for i in months)):
            raise ValueError('Months must be 1..12')
        nz,nx = self.source['elevation_m'].shape
        if window is not None and (len(window) != 4 or any(type(i) is not int for i in window)
                or not (0 <= window[0] < window[2] <= nz and 0 <= window[1] < window[3] <= nx)):
            raise ValueError('Window outside hydrology parent')
        arrays = {}
        for name in names:
            path = _file(self.root,specs[name]['file'],specs[name]['sha256'])
            a = np.load(path,mmap_mode='r',allow_pickle=False)
            if window is not None:
                if a.ndim < 2:
                    raise ValueError('Topology permutation has no window semantics')
                z0,x0,z1,x1 = window
                a = a[...,z0:z1,x0:x1]
            if months is not None and a.ndim == 3:
                a = a[np.asarray(months)-1]
            a.flags.writeable = False
            arrays[name] = a
        grid = deepcopy(self.manifest['binding']['grid'])
        if window is not None:
            z0,x0,z1,x1 = window
            grid['first_xz_m'] = [grid['first_xz_m'][0]+x0*grid['spacing_m'],grid['first_xz_m'][1]+z0*grid['spacing_m']]
            grid['shape_zx'] = [z1-z0,x1-x0]
        selected_specs = {n:deepcopy(specs[n]) for n in names}
        for n in names:
            selected_specs[n]['source_shape'] = selected_specs[n]['shape']
            selected_specs[n]['shape'] = list(arrays[n].shape)
        return dict(arrays=arrays,fields=selected_specs,
                    hydrology_identity=self.manifest['identity'],grid=grid)


def plan(source_map,climate_product,hydrology_product=None,*,expected_source_identity,
         expected_climate_identity,expected_hydrology_identity=None):
    view = SavedClimateMap(source_map,climate_product,expected_source_identity=expected_source_identity,
        expected_climate_identity=expected_climate_identity)
    hydrology = None
    if hydrology_product is not None:
        hydrology = SavedClimateHydrology(source_map,climate_product,hydrology_product,
            expected_source_identity=expected_source_identity,expected_climate_identity=expected_climate_identity,
            expected_hydrology_identity=expected_hydrology_identity)
    cells = int(np.prod(view.metadata['shape_zx']))
    return dict(schema=SCHEMA,status='ready' if hydrology else 'pending-input',
        missing=[] if hydrology else ['completed-same-source-climate-hydrology-sidecar'],
        source_identity=expected_source_identity,climate_identity=expected_climate_identity,
        hydrology_identity=hydrology.manifest['identity'] if hydrology else None,
        shape_zx=view.metadata['shape_zx'],estimated_increment_bytes=128*2**20+cells*8*20,
        derived_raster_bytes_estimate=cells*8*14,terrain_evolution=False,river_topology='byte-preserved',
        default_story_publication=False)


def publish(source_map,climate_product,hydrology_product,out_dir,*,expected_source_identity,
            expected_climate_identity,expected_hydrology_identity=None):
    saved = SavedClimateHydrology(source_map,climate_product,hydrology_product,
        expected_source_identity=expected_source_identity,expected_climate_identity=expected_climate_identity,
        expected_hydrology_identity=expected_hydrology_identity)
    source_root = Path(source_map).resolve(); out = Path(out_dir).resolve()
    for parent in (source_root,Path(climate_product).resolve(),Path(hydrology_product).resolve()):
        if out == parent or out.is_relative_to(parent):
            raise ValueError('New environment output must not be inside an immutable parent')
    if out.exists():
        raise FileExistsError('New environment directory required')
    parent = json.loads((source_root/'manifest.json').read_text(encoding='utf-8'))
    climate = saved.climate
    annual = climate.query(['temperature_c','precipitation_mm_yr','biome_id'])['arrays']
    terminal = saved.query(['final_soil_water_mm','final_snow_swe_mm','final_ice_swe_mm','dynamic_glacier_mask'])['arrays']
    shape = saved.source['elevation_m'].shape
    q = np.zeros(shape)
    # Integrated monthly volumes, NOT unweighted mean of monthly mean discharge.
    for month in range(1,13):
        q += saved.query(['monthly_routed_volume_m3'],months=[month])['arrays']['monthly_routed_volume_m3'][0]
    q /= 365.*86400.
    mask = terminal['dynamic_glacier_mask']
    h = np.full(shape,np.nan)
    for r in saved.regions:
        z0,x0,z1,x1 = r['binding']['window_zx']; sl = np.s_[z0:z1,x0:x1]
        rho = r['metadata']['parameters']['ice_density_kg_m3']
        if not np.isfinite(rho) or rho <= 0:
            raise ValueError('Dynamic ice density invalid')
        h[sl] = terminal['final_ice_swe_mm'][sl]/rho
    arrays = dict(temperature_c=annual['temperature_c'],precipitation_mm_yr=annual['precipitation_mm_yr'],
        biome=annual['biome_id'],discharge_m3_s=q,soil_water_mm=terminal['final_soil_water_mm'],
        snow_swe_mm=terminal['final_snow_swe_mm'],year_end_ice_swe_mm=terminal['final_ice_swe_mm'],
        glacier_simulated_fraction=mask.astype(np.float64),glacier_ice_thickness_m=h,
        glacier_ice_surface_m=saved.source['elevation_m']+h,
        glacier_ice_volume_m3=h*saved.source['spacing_m']**2,
        glacier_coverage_fraction=np.where(mask,h>0,np.nan).astype(float))
    for name,value in arrays.items():
        used = value[mask] if name.startswith('glacier_') and name != 'glacier_simulated_fraction' else value
        if not np.isfinite(used).all() or (name not in ('temperature_c','glacier_ice_surface_m') and np.any(used<0)):
            raise ValueError('Invalid environment annual/terminal fields')
    ids = climate.metadata['classification']['stable_biome_ids']
    if arrays['biome'].dtype.kind not in 'iu' or not set(np.unique(arrays['biome'])).issubset({int(k) for k in ids}):
        raise ValueError('Climate biome ids not covered by stable name table')
    out.parent.mkdir(parents=True,exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='.climate-environment-',dir=out.parent))
    try:
        layers={}; vectors=deepcopy(parent['vectors']); files={}
        for name,spec in parent['layers'].items():
            if name.startswith('glacier_') or name in arrays:
                continue
            source = _file(source_root,spec['file'],spec['sha256'])
            relative = source.relative_to(source_root).as_posix()
            target = work/'frozen-source'/relative; target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,target)
            layers[name]=deepcopy(spec); layers[name]['file']='frozen-source/'+relative
            files[layers[name]['file']]=spec['sha256']
        for name,spec in vectors.items():
            source = _file(source_root,spec['file'],spec['sha256'])
            relative = source.relative_to(source_root).as_posix()
            target=work/'frozen-source'/relative;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,target)
            spec['file']='frozen-source/'+relative; files[spec['file']]=spec['sha256']
        from app.map_source import STANDARD_LAYERS
        for name,a in arrays.items():
            np.save(work/(name+'.npy'),a,allow_pickle=False)
            spec=dict(file=name+'.npy',sha256=cs._sha(work/(name+'.npy')),dtype=str(a.dtype),
                unit=STANDARD_LAYERS.get(name,'mm'),nodata=None,
                meaning=('Selected dynamic regions new climate-year-end ice; NaN outside dynamic support'
                    if name.startswith('glacier_') else 'Saved climate annual or new hydrology terminal field'))
            if name in ('temperature_c','precipitation_mm_yr','biome'):
                spec.update(source=expected_climate_identity,approximation='bounded saved monthly climate diagnostic; native classification ids unchanged')
            if name=='discharge_m3_s':
                spec['scenario']='new finite noleap365 snow/ice-liquid soil year; sum(monthly routed volume)/(365*86400)'
            if name=='glacier_simulated_fraction':
                spec['meaning']='1 selected dynamic new-year region, 0 not dynamically modelled; 0 does NOT mean ice-free'
            if name=='year_end_ice_swe_mm':
                spec['meaning']='Year-end mm water ice stock: dynamic selected regions and cell-local non-dynamic diagnostic elsewhere; NOT global 2-D glacier H'
            layers[name]=spec;files[spec['file']]=spec['sha256']
        manifest=dict(schema='world-map-product-v1',producer='Terragenesis',algorithm_version=SCHEMA,
            ready=True,source_identity=expected_source_identity,
            lineage=list(dict.fromkeys([expected_source_identity,expected_climate_identity,saved.manifest['identity'],*parent.get('lineage',[])])),
            world_seed=parent['world_seed'],subseeds=deepcopy(parent['subseeds']),subseed_method=parent['subseed_method'],
            grid=deepcopy(parent['grid']),boundary=parent.get('boundary','finite; no wrap'),layers=layers,vectors=vectors,files=files,
            stable_biome_ids=ids,climate_environment=dict(schema=SCHEMA,source_identity=expected_source_identity,
                climate_identity=expected_climate_identity,hydrology_identity=saved.manifest['identity'],year=1,calendar='noleap365',
                dynamic_regions=[r['binding'] for r in saved.regions],topology='original receiver/lake/rivers byte-preserved; no vector Q inferred',
                routing_surface='Inherited frozen routing/hydro surfaces remain original parent geometry, not new-year ice surface'),
            declared_generated=['saved annual T/P and native biome ids','new-year soil/snow/ice terminal fields and integrated annual raster discharge'],
            limitations=['Finite diagnostic climate/year, not calibrated GCM or coupled climate convergence',
                'Dynamic H only inside selected regions; global ice SWE elsewhere is cell-local non-dynamic stock',
                'Original topology and potential lake geometry retained; no lake storage/delay, channel evolution or vector discharge attribution',
                'Not selected as default story world; source/old glacier inventories remain immutable'])
        if 'status_codes' in parent:
            manifest['status_codes']=deepcopy(parent['status_codes'])
        from app.terrain_source import _canon
        manifest['identity']=hashlib.sha256(_canon(manifest).encode()).hexdigest()
        cs._write_json(work/'manifest.json',manifest)
        load_source('world-map-product',work,expected_identity=manifest['identity'])
        work.rename(out)
        return manifest
    finally:
        if work.exists():shutil.rmtree(work)
