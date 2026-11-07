"""Resource-site mini maps (about 10 x 8 cells), see docs/town-art-spec.md 14 and 16.

site_layout() lays one main site building, its matching props and special ground
on a small grid with a dirt road leading off the map. Art is picked by the meta
``resource`` / ``subtype`` fields; nothing outside metadata is read.
"""
from .building_economy import profile_for
from .town_layout_art import (CELL, DUAL_RE, cell_hash, dual_tiles, footprint_cells,
                              normalize_catalog, place_cells, rng_for)

SITE_SIZE = (10, 8)
BASE = {'west': 'west-common-ground-grass-', 'east': 'east-common-ground-earth-'}


def _variants(meta, prefix):
    return sorted(i for i in meta if i.startswith(prefix) and i[len(prefix):].isdigit())


def _pick(rows, style, resource, subtype, category):
    rows = [m for m in rows if m.get('category') == category and m.get('resource') == resource
            and m.get('style') == style]
    exact = [m for m in rows if subtype and m.get('subtype') == subtype]
    loose = [m for m in rows if not m.get('subtype')]
    return sorted(exact or loose or rows, key=lambda m: m['id'])


def site_layout(site_meta_or_resource, style='west', subtype=None, seed=None, catalog=None):
    """Return a JSON-compatible mini map for one resource site.

    site_meta_or_resource: a site meta dict (its style/resource/subtype win) or a
    resource name such as 'timber'. Styles without site art (arab) fall back to
    west and say so in ``missing``.
    """
    from .town_layout import load_catalog
    rows, meta = normalize_catalog(catalog, load_catalog)
    missing = []
    if isinstance(site_meta_or_resource, dict):
        given = site_meta_or_resource
        resource = given.get('resource')
        style = given.get('style', style)
        subtype = given.get('subtype', subtype)
    else:
        given, resource = None, site_meta_or_resource
    if style not in ('west', 'east', 'arab'):
        raise ValueError('unsupported style')
    art_style = style
    if not _pick(rows, art_style, resource, subtype, 'site'):
        other = [s for s in ('west', 'east') if s != style and _pick(rows, s, resource, subtype, 'site')]
        if other:
            missing.append({'facility': None, 'id': f'{style}-site-{resource}', 'reason': 'style_fallback',
                            'note': f'{style} 无 {resource} 资源点素材，回落 {other[0]}'})
            art_style = other[0]
    rng = rng_for('site', resource, subtype, art_style, seed)
    sites = _pick(rows, art_style, resource, subtype, 'site')
    if given and given.get('id') in meta:
        main = meta[given['id']]
    elif sites:
        main = sites[rng.randrange(len(sites))]
    else:
        main = None
        missing.append({'facility': None, 'id': f'{style}-site-{resource}', 'reason': 'asset'})
    if subtype and main and main.get('subtype') != subtype:
        missing.append({'facility': None, 'id': main['id'], 'reason': 'subtype_fallback',
                        'note': f'无 subtype={subtype} 的主体，改用 {main["id"]}'})
    fw, fd = main['footprint'] if main else (2, 2)
    w, h = max(SITE_SIZE[0], fw + 4), max(SITE_SIZE[1], fd + 4)
    x0 = (w - fw) // 2 + rng.randint(-1, 1)
    y0 = rng.randint(1, max(1, h - fd - 4))
    body = footprint_cells(x0, y0, fw, fd)
    # Dirt road: from the entrance south to the road row, then off one map edge.
    ex, ey = x0 + fw // 2, y0 + fd
    row = min(h - 2, ey + rng.randint(1, 2))
    roads = {(ex, y) for y in range(ey, row + 1)}
    if rng.random() < .5:
        roads |= {(x, row) for x in range(0, ex + 1)}
    else:
        roads |= {(x, row) for x in range(ex, w)}
    if rng.random() < .4:
        roads |= {(ex, y) for y in range(row, h)}
    # Ground: special resource ground around the site, the style's base texture elsewhere.
    special = _pick(rows, art_style, resource, subtype, 'ground')
    special = [m for m in special if not DUAL_RE.search(m['id'])]
    base = _variants(meta, BASE.get(art_style, BASE['west']))
    near = footprint_cells(x0 - 2, y0 - 2, fw + 4, fd + 4)
    underlay = []
    for y in range(h):
        for x in range(w):
            k = cell_hash(seed, x, y)
            if special and (x, y) in near and k % 5:
                ident = special[k % len(special)]['id']
            elif base:
                ident = base[0] if k % 2 == 0 or len(base) == 1 else base[1 + (k >> 1) % (len(base) - 1)]
            else:
                continue
            it = place_cells(meta[ident], x, y)
            it['layer'] = 'base' if ident in base else 'site_ground'
            underlay.append(it)
    if not special:
        missing.append({'facility': None, 'id': f'{art_style}-ground-{resource}', 'reason': 'ground_asset'})
    ground, lost = dual_tiles(roads, f'{art_style}-common-road-dirt-', meta)
    missing += [{'facility': None, 'id': i, 'reason': 'tile_asset'} for i in lost]
    items, buildings, props = [], [], []
    if main:
        items.append(place_cells(main, x0, y0))
        profile = profile_for(main)
        buildings.append({'id': main['id'], 'facility': main.get('facility'), 'cell': [x0, y0],
                          'footprint': [fw, fd], 'resource': main.get('resource'),
                          'subtype': main.get('subtype'),
                          'economy': profile.id if profile else None})
    prop_pool = [m for m in _pick(rows, art_style, resource, subtype, 'prop')
                 if list(m.get('footprint', [1, 1])) == [1, 1]]
    blocked = body | roads | {(ex, ey)}
    free = [(x, y) for y in range(h) for x in range(w) if (x, y) not in blocked
            and 0 < x < w - 1 and 0 < y < h - 1]
    free.sort(key=lambda p: (max(abs(p[0] - (x0 + fw / 2)), abs(p[1] - (y0 + fd / 2))), rng.random()))
    last = {}
    for q in free[:18]:
        if not prop_pool or len(props) >= rng.randint(5, 8):
            break
        if rng.random() < .35:
            continue
        m = prop_pool[rng.randrange(len(prop_pool))]
        if any(last.get(n) == m['id'] for n in ((q[0] - 1, q[1]), (q[0] + 1, q[1]),
                                                 (q[0], q[1] - 1), (q[0], q[1] + 1))):
            continue
        last[q] = m['id']
        items.append(place_cells(m, *q))
        props.append({'id': m['id'], 'cell': list(q)})
    if not prop_pool:
        missing.append({'facility': None, 'id': f'{art_style}-prop-{resource}', 'reason': 'prop_asset'})
    items.sort(key=lambda it: (it['key'], it['x']))
    return {'grid': {'w': w, 'h': h, 'cell': CELL, 'roads': sorted(map(list, roads)),
                     'walls': [], 'gates': [], 'water': [], 'walled': False},
            'underlay': underlay, 'ground': ground, 'items': items, 'buildings': buildings,
            'props': props, 'missing': missing, 'style': art_style, 'race': 'common',
            'resource': resource, 'subtype': subtype, 'kind': 'site'}
