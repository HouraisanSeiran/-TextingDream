"""Register the existing 2026-11-11 whole source group; never generate or modify it.

Run: .venv/Scripts/python.exe tools/register_map_bundle.py
Only config/map-bundles.json is written. Source files are read and verified.
Registration is an explicit author action, not an HTTP endpoint or startup task.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from app.map_bundle import MapBundle, WARNINGS, digest, read_json, relative_file, _extent, _grid


TERRAIN = 'artifacts/mountain-glacier-hydrology-20261111/world'
BASE = 'artifacts/world-climate-integration-20261111'
OCEAN = 'artifacts/ocean-current-overlay-20261111'


def build_record(root, *, surface_water=None, surface_previews=None):
    root = Path(root)
    paths = dict(terrain=TERRAIN, environment=BASE+'/environment-world',
                 climate=BASE+'/climate-dry-continuous-year', hydrology=BASE+'/hydrology-dry-continuous-year', ocean=OCEAN)
    manifests = {g: read_json(root/p/'manifest.json') for g, p in paths.items()}
    sources = {g: dict(path=p, identity=manifests[g].get('identity'), manifest_sha256=digest(root/p/'manifest.json'))
               for g, p in paths.items()}
    sources['ocean']['forcing_identity'] = manifests['ocean']['source_ids']['ocean_forcing']
    sources['ocean']['status'] = manifests['ocean']['status']
    sources['ocean']['fields'] = {}
    for name in manifests['ocean']['arrays']:
        p = root/OCEAN/(name+'.npy')
        a = np.load(p, mmap_mode='r', allow_pickle=False)
        unit = 'degC' if name.endswith('_c') else 'm/s' if name.endswith('_m_s') else '1'
        sources['ocean']['fields'][name] = dict(file=p.name, sha256=digest(p), shape=list(a.shape),
            dtype=str(a.dtype), unit=unit, nodata=None,
            meaning='Saved independent ocean support / monthly upper-layer diagnostic; warm/cold uses SST anomaly, not absolute temperature')
        a._mmap.close()
    sources['ocean']['routes'] = dict(path=OCEAN+'/routes.json', sha256=digest(root/OCEAN/'routes.json'))
    atlas_path = BASE+'/atlas-final/atlas-source.json'
    atlas = read_json(root/atlas_path)
    summary = atlas['files']['simple-atlas.png']['summary']
    if atlas['product']['identity'] != sources['environment']['identity']:
        raise ValueError('Atlas environment identity differs')
    width, height = summary['map_px']; margin = summary['margin_px']
    rect = dict(x=margin, y=margin, width=width, height=height)
    extent = _extent(_grid(manifests['environment']['grid']))
    frame = manifests['ocean']['render']['frame']
    if frame['origin_px'] != [margin, margin] or frame['map_px'] != [width, height]:
        raise ValueError('Ocean and atlas frames differ')
    previews = []
    def add(key, title, files, georeferenced):
        specs = {month: dict(path=p, sha256=digest(root/p)) for month, p in files.items()}
        sizes = []
        for p in files.values():
            with Image.open(root/p) as im:
                sizes.append(list(im.size))
        if any(s != sizes[0] for s in sizes):
            raise ValueError('Preview monthly image dimensions differ')
        previews.append(dict(key=key, title=title, months=[] if 'static' in files else [int(m) for m in files],
            georeferenced=georeferenced, image_size=sizes[0], map_rect=rect if georeferenced else None,
            world_extent_m=extent if georeferenced else None, files=specs,
            coordinate_note='Only map_rect has coordinate meaning; exclude margins/decorations' if georeferenced else 'Diagnostic panel; clicking cannot query a world coordinate'))
    add('atlas', 'Year-1 environment atlas', {'static':BASE+'/atlas-final/simple-atlas.png'}, True)
    add('relief', 'Relief only', {'static':BASE+'/atlas-final/relief-only.png'}, True)
    for key, title, name in [('climate-topics','Climate diagnostic panels','climate-topics.png'),
                              ('water-snow-topics','Water and snow diagnostic panels','water-snow-topics.png'),
                              ('glacier-year-comparison','Old H20 / current H1 comparison (history only)','glacier-year-comparison.png')]:
        add(key, title, {'static':BASE+'/topics/'+name}, False)
    for key, name in [('ocean-overlay','overlay'), ('ocean-composite','natural-map'), ('ocean-theme','ocean-theme')]:
        add(key, key, {str(m):f'{OCEAN}/{name}-month-{m:02d}.png' for m in (1, 7)}, True)
    history = [dict(kind='glacier-H20', status='history-reference-only', source_identity=sources['terrain']['identity'],
        regions=manifests['terrain'].get('glacier_regions', []),
        warning='Old H20 and cumulative melt do not supply year-1 melt/water; original routing geometry retained')]
    for path in sorted((root/BASE).glob('*/manifest.json')):
        if path.parent.name in ('environment-world', 'climate-dry-continuous-year', 'hydrology-dry-continuous-year'):
            continue
        m = read_json(path)
        history.append(dict(path=path.parent.relative_to(root).as_posix(), identity=m.get('identity'),
            status='history-reference-only', source_status=m.get('status'), selectable=False))
    record = dict(id='terragenesis-world-20261111', title='Terragenesis · 2026-11-11 同源世界地图',
        status='current-registered-finite-year', sources=sources, previews=previews,
        preview_metadata=[dict(path=atlas_path, sha256=digest(root/atlas_path))],
        warnings=deepcopy(WARNINGS), history=history, producer='Terragenesis', default_story_publication=False)
    if surface_water is not None:
        attach_surface_water(root, record, surface_water, surface_previews)
    elif surface_previews is not None:
        raise ValueError('surface previews require explicit surface-water sidecar')
    return record


def attach_surface_water(root, record, surface_water, preview_metadata=None):
    """Explicit optional sixth group; builds a record, never writes the registry."""
    root = Path(root).resolve(); path = relative_file(root, surface_water)
    m = read_json(path/'manifest.json')
    record['sources']['surface_water'] = dict(path=surface_water, identity=m['identity'],
        manifest_sha256=digest(path/'manifest.json'))
    for preview in record['previews']:
        if preview['key'] in ('atlas','ocean-composite','water-snow-topics'):
            preview['status'] = 'history-reference-only'
            preview['title'] += ' · 历史潜在湖 / 无湖水账'
            record['history'].append(dict(kind='preview', key=preview['key'], status='history-reference-only'))
            if preview['key'] == 'atlas': preview['key'] = 'atlas-history'
    record['warnings'] += ['Current surface_water is one finite empty-stock year. Hillslope Q excludes lake interior; spill routes are net schematic transfers, not full hydraulic Q.',
                           'Old terrain lakes/rivers, hydrology Q and ocean-composite retain historical potential/no-lake geometry; old environment identity is unchanged.']
    if preview_metadata is not None:
        mp = relative_file(root, preview_metadata); renders = read_json(mp)
        files = {}; frame = None
        for render in renders:
            if (render.get('surface_water_identity') != m['identity']
                    or render.get('environment_parent_identity') != record['sources']['environment']['identity']
                    or render.get('physical_source_identity') != record['sources']['terrain']['identity']):
                raise ValueError('Surface preview provenance source differs')
            month = render.get('month')
            if type(month) is not int or month not in (1,7,12) or str(month) in files or not render.get('image'):
                raise ValueError('Explicit unique saved surface previews 1/7/12 required')
            image = relative_file(mp.parent, render['image'])
            if digest(image) != render.get('image_sha256'):
                raise ValueError('Surface preview image hash differs')
            current = {k: render[k] for k in ('image_size','map_rect','world_extent_m')}
            if frame is not None and current != frame:
                raise ValueError('Surface monthly preview coordinate frames differ')
            frame = current
            with Image.open(image) as im:
                if list(im.size) != frame['image_size'] or im.format != 'PNG':
                    raise ValueError('Surface preview dimensions/format differ')
            files[str(month)] = dict(path=image.relative_to(root).as_posix(), sha256=digest(image))
        if not files:
            raise ValueError('No saved surface preview images')
        record['previews'].insert(0, dict(key='atlas', title='实际月湖河 · 有限首年', months=[int(v) for v in files],
            georeferenced=True, files=files, **frame, surface_water_identity=m['identity'],
            coordinate_note='Only renderer-provenance map_rect maps to metric world coordinates'))
        record.setdefault('preview_metadata', []).append(dict(path=preview_metadata, sha256=digest(mp)))
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--surface-water', help='Explicit root-relative sixth sidecar; absent preserves old five groups')
    parser.add_argument('--surface-previews', help='Explicit root-relative renderer surface-water-source.json')
    args = parser.parse_args()
    root = args.root.resolve()
    record = build_record(root, surface_water=args.surface_water, surface_previews=args.surface_previews)
    # Whole same-source binding validated before registry write; never field-mix.
    MapBundle(root, record).detail()
    path = root/'config/map-bundles.json'
    data = read_json(path) if path.is_file() else dict(schema='dream-map-bundles-1', bundles=[])
    if data['schema'] != 'dream-map-bundles-1':
        raise ValueError('Unsupported registry')
    data['bundles'] = [r for r in data['bundles'] if r['id'] != record['id']] + [record]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('Registered existing whole source group:', record['id'], '->', path)


if __name__ == '__main__':
    main()
