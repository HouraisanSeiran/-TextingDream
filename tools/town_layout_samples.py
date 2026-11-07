"""Export offline fixtures. Run: .venv/Scripts/python tools/town_layout_samples.py.

These are layout-only fixtures, not invented full TownSnapshot records. No world,
DB, civ-atlas location or game service is read or modified.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.town_layout import FACILITY_DISTRICTS, layout, load_catalog  # noqa: E402

COMBINATIONS = [('west', r) for r in ('common', 'elf', 'dwarf', 'orc')] + [('east', 'common')]
SAMPLES = [
    ('village', 'Village', 'village', 'village', ['well', 'inn', 'temple', 'mill', 'granary']),
    ('town', 'Town', 'town', 'market_town', ['town_hall', 'market_hall', 'forge', 'inn',
                                         'granary', 'stable', 'infirmary', 'cemetery']),
    ('city', 'City', 'city', 'city', ['city_wall', 'gate', 'town_hall', 'lord_hall',
                                   'market_hall', 'temple', 'academy', 'barracks',
                                   'warehouse', 'smelter', 'tannery', 'kiln', 'cistern']),
    ('port', 'Port', 'town', 'port', ['town_hall', 'market_hall', 'dock', 'bridge',
                                   'warehouse', 'inn', 'well', 'stable']),
    ('fortress', 'Fortress', 'small_town', 'border_fortress', ['city_wall', 'gate',
                  'lord_hall', 'barracks', 'watchtower', 'forge', 'stable', 'granary', 'well']),
]


def export():
    catalog = load_catalog()
    output = []
    for ident, name, scale, town_type, facilities in SAMPLES:
        districts = sorted(set(FACILITY_DISTRICTS.get(k, 'residential') for k in facilities)
                           | {'residential'})
        town = {'town_id': ident, 'skeleton': {'scale': scale, 'town_type': town_type,
                                             'water': {'source': 'river' if ident == 'port' else 'well_field'}},
                'built': {'districts': [{'id': d, 'kind': d, 'roof': 'gable_tile'} for d in districts],
                          'facilities': [{'id': f'{k}_{i}', 'kind': k,
                                          'district': FACILITY_DISTRICTS.get(k, 'residential')}
                                         for i, k in enumerate(facilities)]}}
        for style, race in COMBINATIONS:
            for seed in (1, 7, 42):
                output.append({'sample': ident, 'name': name, 'style': style, 'race': race,
                               'seed': seed, 'layout': layout(town, style, race, seed, catalog)})
    target = ROOT / 'app/static/map-art/town/layout-samples.js'
    target.write_text('window.TOWN_LAYOUT_SAMPLES = ' + json.dumps(output, separators=(',', ':')) + ';\n',
                      encoding='utf-8')
    missing = sorted({m['facility'] for s in output for m in s['layout']['missing'] if m.get('facility')})
    print(f'Exported {len(output)} layouts to {target}')
    print('Missing facilities:', ', '.join(missing) or '(none)')


if __name__ == '__main__':
    export()
