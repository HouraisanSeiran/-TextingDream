"""Opt-in map queries over a saved regional climate and its exact terrain parent.

This Python adapter does not choose a default product or prepare missing data.
Existing ``map_source`` terrain sampling stays available as ``terrain``.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

import numpy as np

from app.map_source import load_source


def _climate_module():
    # Follow the existing sibling-project arrangement without importing the
    # generation adapter (which imports numerical hydrology at module load).
    root = Path(__file__).resolve().parents[3] / '山川形意Terragenesis'
    if str(root) not in sys.path:
        sys.path.append(str(root))
    from terrain_pipeline import world_climate
    return world_climate


def _saved_array(root, descriptor, climate):
    root = Path(root).resolve()
    path = (root / descriptor['file']).resolve()
    if not path.is_relative_to(root) or climate._digest(path) != descriptor['sha256']:
        raise ValueError('Saved climate parent array path/hash differs')
    return np.load(path, mmap_mode='r', allow_pickle=False)


def _validate_diagnostic_parent(product, source_root, source, info, meta, loaded, climate):
    """Validate only static parent fields; never open a monthly climate array."""
    from app.world_gen.climate_world_stage import SCHEMA, topological_order
    from terrain_pipeline.common_infra import array_sha256, identity

    convergence = meta.get('convergence', {})
    cfg = meta.get('config', {})
    if (meta.get('algorithm') != climate.DIAGNOSTIC_VERSION
            or cfg.get('atmosphere_backend') != 'game-diagnostic'
            or cfg.get('snow_ice', {}).get('enabled', False)
            or convergence.get('converged') is not False
            or convergence.get('not_applicable') is not True
            or convergence.get('joint_iteration') is not False
            or meta.get('capability_flags', {}).get('snow_ice') is not False
            or meta.get('plate_identity') is not None
            or meta.get('source_process_identity') is not None):
        raise ValueError('Unsupported diagnostic climate completion/source semantics')
    checkpoint = product/'source-binding.json'
    if not checkpoint.is_file():
        raise ValueError('Diagnostic climate requires its source-binding checkpoint')
    binding = json.loads(checkpoint.read_text(encoding='utf-8'))
    bed = _saved_array(source_root, source['layers']['elevation_m'], climate)
    status = _saved_array(source_root, source['layers']['status'], climate)
    receiver_spec = source['layers']['receiver']
    receiver = _saved_array(source_root, receiver_spec, climate)
    if (info.grid_semantics != 'cell-centre'
            or bed.dtype != np.dtype('float64') or bed.shape != tuple(info.shape_zx)
            or not np.isfinite(bed).all() or status.shape != bed.shape
            or not np.isin(status, [3, 4, 5]).all()
            or receiver_spec.get('unit') != '1' or receiver.dtype.kind not in 'iu'
            or receiver.shape != bed.shape or str(receiver.dtype) != receiver_spec['dtype']
            or source.get('files', {}).get(receiver_spec['file'], receiver_spec['sha256']) != receiver_spec['sha256']):
        raise ValueError('Diagnostic climate parent terrain/receiver descriptor differs')
    ocean = status == 3
    if np.any(ocean & (bed >= 0)):
        raise ValueError('Diagnostic ocean requires actual below-sea terrain bed')
    rec = np.asarray(receiver, np.int64).ravel()
    order = topological_order(receiver)
    expected = dict(schema=SCHEMA, source_identity=info.identity, world_seed=info.world_seed,
        first_xz_m=list(info.first_sample_xz_m), spacing_m=float(info.spacing_m),
        shape_zx=list(info.shape_zx), terrain_sha256=array_sha256(bed),
        ocean_sha256=array_sha256(ocean), receiver_sha256=array_sha256(rec),
        order_sha256=array_sha256(order), config=cfg, reference_identity=meta['reference_identity'])
    if binding != expected:
        raise ValueError('Diagnostic climate source-binding differs from actual parent')
    if (meta['source_identity'] != info.identity or meta['world_seed'] != info.world_seed
            or meta['terrain_sha256'] != expected['terrain_sha256']
            or meta['first_xz_m'] != expected['first_xz_m']
            or meta['spacing_m'] != expected['spacing_m'] or meta['shape_zx'] != expected['shape_zx']
            or meta['routing']['receiver_sha256'] != expected['receiver_sha256']
            or meta['routing']['order_sha256'] != expected['order_sha256']
            or loaded['arrays']['ocean_mask'].dtype != np.dtype('bool')
            or not np.array_equal(loaded['arrays']['ocean_mask'], ocean)):
        raise ValueError('Prepared diagnostic climate differs from source terrain/receiver/grid/seed')
    expected_native_binding = identity(dict(bed_m=bed, ocean_mask=ocean, receiver=rec, order=order), dict(
        source_identity=info.identity, world_seed=info.world_seed, first_xz_m=expected['first_xz_m'],
        spacing_m=expected['spacing_m'], config=cfg, reference_identity=meta['reference_identity'],
        algorithm=climate.DIAGNOSTIC_VERSION))
    if meta.get('binding') != expected_native_binding:
        raise ValueError('Native diagnostic climate binding differs from actual parent')
    published = climate.query_climate(product, fields=['receiver'])
    if (published['manifest_identity'] != loaded['manifest_identity']
            or published['arrays']['receiver'].shape != bed.shape
            or published['arrays']['receiver'].dtype != np.dtype('int64')
            or not np.array_equal(published['arrays']['receiver'].ravel(), rec)):
        raise ValueError('Published diagnostic receiver differs from actual parent')


class SavedClimateMap:
    """Read selected saved fields/months/windows, plus exact nearest-cell curves.

    Coupled products require a converged ``world_processes`` parent as before.
    A complete game-diagnostic liquid year instead requires the explicit stage
    source-binding and exact map bed/ocean/receiver/order. Neither branch infers
    missing climate fields or promotes potential vegetation to realized ecology.
    """

    def __init__(self, source_map, climate_product, *, expected_source_identity=None,
                 expected_climate_identity=None):
        climate = _climate_module()
        self.product = Path(climate_product).resolve()
        loaded = climate.query_climate(self.product, fields=['ocean_mask'])
        self.metadata = deepcopy(loaded['metadata'])
        self.manifest_identity = loaded['manifest_identity']
        if expected_climate_identity is not None and self.metadata['identity'] != expected_climate_identity:
            raise ValueError('Climate identity differs from explicitly selected product')
        manifest = json.loads((self.product / 'manifest.json').read_text(encoding='utf-8'))
        if manifest['manifest_identity'] != self.manifest_identity:
            raise ValueError('Climate manifest changed during load')
        if (self.metadata['status'] != 'complete'
                or self.metadata['identity'] != manifest['identity']):
            raise ValueError('Climate completion/identity metadata differs')
        self._climate_fields = deepcopy(manifest['fields'])
        source_root = Path(source_map).resolve()
        self.terrain = load_source('world-map-product', source_root,
                                   expected_identity=expected_source_identity)
        source = json.loads((source_root / 'manifest.json').read_text(encoding='utf-8'))
        if source['identity'] != self.terrain.info.identity:
            raise ValueError('Source manifest changed during load')
        if self.metadata.get('algorithm') == climate.DIAGNOSTIC_VERSION:
            _validate_diagnostic_parent(self.product, source_root, source, self.terrain.info,
                                        self.metadata, loaded, climate)
            self.process_identity = None
            self._environment_fields = {}
            return
        # This gate remains mandatory for every pre-existing coupled product.
        if not self.metadata['convergence']['converged']:
            raise ValueError('Climate completion/identity metadata differs')
        process_record = source.get('world_processes')
        if process_record is None:
            raise ValueError('Saved climate map requires its authoritative physical parent')
        process_path = (source_root / process_record['file']).resolve()
        # load_source has verified this file, its metadata and map binding.
        process = json.loads(process_path.read_text(encoding='utf-8'))
        physical = process['arrays']
        bed = _saved_array(process_path.parent, physical['elevation_m'], climate)
        ocean = _saved_array(process_path.parent, physical['ocean_mask'], climate)
        mapped_bed = _saved_array(source_root, source['layers']['elevation_m'], climate)
        mapped_status = _saved_array(source_root, source['layers']['status'], climate)
        info, meta = self.terrain.info, self.metadata
        from terrain_pipeline.common_infra import array_sha256
        if (bed.dtype != np.dtype('float64') or bed.shape != tuple(info.shape_zx)
                or ocean.dtype != np.dtype('bool') or ocean.shape != bed.shape
                or not np.isfinite(bed).all()
                or not np.array_equal(mapped_bed, bed.astype(mapped_bed.dtype))
                or not np.array_equal(mapped_status == 3, ocean)
                or not np.isin(mapped_status, [3, 4, 5]).all()):
            raise ValueError('Map differs from the known authoritative physical terrain')
        if (meta['source_identity'] != info.identity
                or meta['terrain_sha256'] != array_sha256(bed)
                or meta['shape_zx'] != list(info.shape_zx)
                or meta['first_xz_m'] != list(info.first_sample_xz_m)
                or meta['spacing_m'] != info.spacing_m
                or not np.array_equal(loaded['arrays']['ocean_mask'], ocean)):
            raise ValueError('Prepared climate differs from source terrain/grid')
        if (meta['world_seed'] != info.world_seed or not meta.get('plate_identity')
                or meta['plate_identity'] != process['metadata'].get('plate_identity')):
            raise ValueError('Prepared climate seed/plate differs from source')
        self.process_identity = process['identity']
        # Only published environment layers already tied to this process count
        # as realized fields. Climate-derived potential biomes stay separate.
        self._environment_fields = {
            name: deepcopy(info.layer_metadata[name]) for name in info.layers
            if name not in self._climate_fields
            and info.layer_metadata[name].get('process_identity') == self.process_identity
        }

    @property
    def fields(self):
        """Descriptors only; this does not materialize all monthly arrays."""
        result = deepcopy(self._climate_fields)
        for name, descriptor in self._environment_fields.items():
            descriptor['units'] = descriptor['unit']
            descriptor['role'] = 'realized-environment-at-saved-process-time'
            result[name] = descriptor
        return result

    def query(self, fields=('monthly_temperature_c', 'monthly_precipitation_mm', 'koppen_geiger_id'),
              *, months=None, window=None):
        """Read [z,x] or selected [month,z,x]; month indices are 1..12.

        Static environment fields refer to the saved process time, and are
        unaffected by the selected climate months. No interpolation or time
        advancement occurs. The returned grid is shifted to the crop origin.
        """
        names = [fields] if isinstance(fields, str) else list(fields)
        descriptors = self.fields
        if any(name not in descriptors for name in names):
            raise ValueError('Requested saved climate/environment field is unavailable')
        climate_names = [name for name in names if name in self._climate_fields]
        loaded = _climate_module().query_climate(self.product, climate_names, months=months, window=window)
        if loaded['manifest_identity'] != self.manifest_identity:
            raise ValueError('Selected climate product changed after load')
        arrays = loaded['arrays']
        nz, nx = self.metadata['shape_zx']
        z0, x0, z1, x1 = [0, 0, nz, nx] if window is None else window
        first = self.metadata['first_xz_m']
        spacing = self.metadata['spacing_m']
        environment_names = [name for name in names if name in self._environment_fields]
        if environment_names:
            x, z = np.meshgrid(first[0] + np.arange(x0, x1) * spacing,
                               first[1] + np.arange(z0, z1) * spacing)
            sampled = self.terrain.sample(x, z, environment_names)
            arrays.update({name: sampled[name] for name in environment_names})
        for array in arrays.values():
            array.flags.writeable = False
        selected_descriptors = {}
        for name in names:
            descriptor = descriptors[name]
            descriptor['source_shape'] = descriptor.get('shape', self.metadata['shape_zx'])
            descriptor['source_dtype'] = descriptor['dtype']
            descriptor['shape'] = list(arrays[name].shape)
            descriptor['dtype'] = str(arrays[name].dtype)
            selected_descriptors[name] = descriptor
        return dict(arrays=arrays, fields=selected_descriptors,
                    months=list(range(1, 13)) if months is None else list(months),
                    grid=dict(first_xz_m=[first[0] + x0 * spacing, first[1] + z0 * spacing],
                              spacing_m=spacing, shape_zx=[z1-z0, x1-x0],
                              axes='X east/Z south, arrays[z,x]', semantics='cell-centre'),
                    metadata=deepcopy(self.metadata), source_identity=self.terrain.info.identity,
                    climate_identity=self.metadata['identity'], process_identity=self.process_identity,
                    environment_time=('finite diagnostic liquid year; no physical-process time or snow/ice claim'
                         if self.process_identity is None else
                         'saved physical process time; independent of climate month selection'))

    def point(self, x_m, z_m, fields=('monthly_temperature_c', 'monthly_precipitation_mm'), *, months=None):
        """Return the nearest saved cell and its monthly curve, without resampling."""
        if (isinstance(x_m, bool) or isinstance(z_m, bool)
                or not np.isfinite([x_m, z_m]).all()):
            raise ValueError('Finite metric point coordinates required')
        first = self.metadata['first_xz_m']
        spacing = self.metadata['spacing_m']
        column = (x_m-first[0]) / spacing
        row = (z_m-first[1]) / spacing
        nz, nx = self.metadata['shape_zx']
        if not (0 <= row <= nz-1 and 0 <= column <= nx-1):
            raise ValueError('Point outside prepared climate cell-centre support')
        iz, ix = int(np.rint(row)), int(np.rint(column))
        result = self.query(fields, months=months, window=[iz, ix, iz+1, ix+1])
        result['arrays'] = {name: value[..., 0, 0] for name, value in result['arrays'].items()}
        for name, value in result['arrays'].items():
            result['fields'][name]['shape'] = list(np.shape(value))
        result['cell_zx'] = [iz, ix]
        result['cell_xz_m'] = [first[0]+ix*spacing, first[1]+iz*spacing]
        result['sampling'] = 'nearest saved cell centre; no new terrain correction'
        return result
