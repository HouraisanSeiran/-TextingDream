import json, re, zipfile
from pathlib import Path
from html import unescape

root = Path(__file__).resolve().parents[1]
out = root / 'artifacts/map-design'
out.mkdir(exist_ok=True)
jar = Path('D:/codexwork/MinecraftZombieArmy/.gradle-user/caches/fabric-loom/26.3/minecraft-common.jar')
with zipfile.ZipFile(jar) as z:
    names = sorted(n for n in z.namelist() if n.startswith('data/minecraft/worldgen/biome/') and n.endswith('.json'))
    data = {Path(n).stem: json.loads(z.read(n)) for n in names}
    templates = [n for n in z.namelist() if '/structure/village/' in n and '/houses/' in n and n.endswith('.nbt')]
    (out / 'vanilla-biomes.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    (out / 'vanilla-buildings.txt').write_text('\n'.join(templates), encoding='utf-8')
    print('Biomes:', len(names), ', '.join(data))
    print('Village templates:', len(templates))
assets = Path('D:/codexwork/MinecraftZombieArmy/client-assets')
index = json.loads((assets / 'indexes/34.json').read_text())
lang = index['objects'].get('minecraft/lang/zh_cn.json')
if lang:
    h = lang['hash']
    p = assets / 'objects' / h[:2] / h
    if p.exists():
        translations = json.loads(p.read_text(encoding='utf-8'))
        (out / 'biome-names.json').write_text(json.dumps({k: translations.get('biome.minecraft.'+k, k) for k in data}, ensure_ascii=False, indent=2), encoding='utf-8')
        print('Chinese names extracted')
for name in ['dual-grid', 'biome', 'village', 'villager']:
    path = root / f'artifacts/{name}-reference.html'
    if not path.exists(): continue
    html = path.read_text(encoding='utf-8', errors='replace')
    html = re.sub(r'<(script|style)\b[^>]*>.*?</\1>', '', html, flags=re.S)
    text = unescape(re.sub('<[^>]+>', ' ', html))
    text = re.sub(r'[ \t]+', ' ', text)
    (out / f'{name}-reference.txt').write_text(text, encoding='utf-8')
    print(name, text[:550])
