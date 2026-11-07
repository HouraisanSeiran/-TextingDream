"""Synchronise shared weather tables into the JS mirror; --check makes no writes."""
import argparse
import json
import re
from pathlib import Path

from app import weather


NAMES = ('NATURAL', 'FANTASY', 'KINDS', 'SEASONS', 'PRECIP_TYPES', 'PTYPE', 'PTYPES_OF', 'WET_TYPES',
         'GROUND_NAMES', 'CLIMATES', 'DEFAULT_INTENSITY', 'BIOMES', 'BIOME_CLIMATE', 'CLOUD_BAND', 'RELATED',
         'OVERRIDE_FIELDS', 'OVERRIDE_NESTED', 'KIND_RANGE', 'CLOUD_OF', 'FOG_OF', 'WIND_FLOOR', 'RATE', 'VCOST',
         'FANTASY_SHARE', 'MAGIC_OF', 'MAGIC_HUE', 'MAGIC_PULSE', 'GROUND_KEYS', 'EXTRA', 'AEROSOL_OF',
         'DUST_KINDS', 'HEAT_KINDS', 'RAINBOW_KINDS', 'LIQUID_KINDS', 'FOGGY', 'CYC_SLOT_H', 'AEROSOL_TYPES',
         'CYCLONE_PHASES', 'MAX_CONTEXTS', 'MAX_MEMO')


def sync(source):
    additions = []
    for name in NAMES:
        value = getattr(weather, name)
        if name == 'OVERRIDE_FIELDS':
            value = {k: v for k, v in value.items() if k != 'kind'}
        declaration = 'var ' + name + ' = ' + json.dumps(value, ensure_ascii=False, separators=(',', ':')) + ';'
        pattern = r'var ' + name + r' = .*?;'
        if re.search(pattern, source, flags=re.S):
            source = re.sub(pattern, lambda _: declaration, source, count=1, flags=re.S)
        else:
            additions.append('  ' + declaration)
    marker = '  // Shared extension tables (tools/weather_mirror_tables.py).\n'
    # New table declarations are inserted once; subsequent runs update them above.
    if additions:
        source = source.replace("  'use strict';\n", "  'use strict';\n" + marker + '\n'.join(additions) + '\n', 1)
    return source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    path = Path(__file__).resolve().parents[1] / 'app/static/weather-fx/weather-gen.js'
    source = path.read_text(encoding='utf-8')
    result = sync(source)
    if args.check:
        if result != source:
            raise SystemExit('Weather mirror tables differ; run python -m tools.weather_mirror_tables')
    else:
        path.write_text(result, encoding='utf-8')


if __name__ == '__main__':
    main()
