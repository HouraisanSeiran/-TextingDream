"""Read and verify only explicitly consumed frozen arrays."""
import hashlib
import json
import numpy as np
from scipy import ndimage

EXPECTED = 'b4c8bbdba29111b8c3ba3270e2f0d3a4fed3544655249fa07c506654b8ae6af9'
KEYS = ('elevation_m', 'plate_id', 'continental_fraction', 'crust_thickness_m', 'velocities_m_per_step', 'ocean_connected')

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)

def identity(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def load_source(path, expected=EXPECTED):
    with np.load(path, allow_pickle=False) as archive:
        raw = archive['manifest_json']
        if raw.shape != () or raw.dtype.kind != 'U':
            raise ValueError('Invalid manifest_json')
        manifest = json.loads(raw.item())
        actual = identity({k:v for k,v in manifest.items() if k != 'identity'})
        if actual != expected or manifest['identity'] != actual:
            raise ValueError('Source identity mismatch')
        fields = {}
        for name in KEYS:
            key = 'final/' + name
            a = archive[key]
            if hashlib.sha256(a.tobytes(order='C')).hexdigest() != manifest['arrays'][key]['sha256']:
                raise ValueError('Source array hash mismatch: ' + key)
            fields[name] = a
    return fields, manifest

def sample(a, shape, source_spacing, spacing):
    z = (np.arange(shape[0]) + .5) * spacing / source_spacing - .5
    x = (np.arange(shape[1]) + .5) * spacing / source_spacing - .5
    zz, xx = np.meshgrid(z, x, indexing='ij')
    return ndimage.map_coordinates(a.astype(float), [zz, xx], order=1, mode='nearest')

def subseed(seed, purpose):
    return int.from_bytes(hashlib.sha256(f'{seed}:{purpose}'.encode('utf-8')).digest()[:8], 'big')

def spatial_noise(shape, first, spacing, seed, wavelength):
    """Coordinate-addressed lattice noise; no stateful RNG or query-order dependence."""
    z = (first[1] + np.arange(shape[0]) * spacing) / wavelength
    x = (first[0] + np.arange(shape[1]) * spacing) / wavelength
    zz, xx = np.meshgrid(z, x, indexing='ij')
    iz, ix = np.floor(zz).astype(np.int64), np.floor(xx).astype(np.int64)
    def lattice(a,b):
        with np.errstate(over='ignore'):
            q = a.astype(np.uint64)*np.uint64(0x9e3779b185ebca87) ^ b.astype(np.uint64)*np.uint64(0xc2b2ae3d27d4eb4f) ^ np.uint64(seed)
            q = (q ^ (q >> 30))*np.uint64(0xbf58476d1ce4e5b9)
            q = (q ^ (q >> 27))*np.uint64(0x94d049bb133111eb)
            q ^= q >> 31
        return (q >> 11).astype(float) / 2**53 * 2 - 1
    fx, fz = xx-ix, zz-iz
    fx, fz = fx*fx*(3-2*fx), fz*fz*(3-2*fz)
    return ((1-fz)*((1-fx)*lattice(ix,iz)+fx*lattice(ix+1,iz)) + fz*((1-fx)*lattice(ix,iz+1)+fx*lattice(ix+1,iz+1)))
