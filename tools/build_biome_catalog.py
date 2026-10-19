import csv, json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
out=root/'artifacts/map-design'
rows=list(csv.DictReader((out/'biome-styles.tsv').open(encoding='utf-8'),delimiter='\t'))
names=json.loads((out/'biome-names.json').read_text(encoding='utf-8'))
vanilla=json.loads((out/'vanilla-biomes.json').read_text(encoding='utf-8'))
assert len(rows)==len(vanilla)==len(set(r['id'] for r in rows))==67
assert set(r['id'] for r in rows)==set(vanilla)
for r in rows:
    r['name']=names[r['id']];r['density']=int(r['density'])
    r['ground']='#'+r['ground'];r['accent']='#'+r['accent']
catalog={'version':'26.3','biomes':rows}
(out/'biome-catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
resource=root/'artifacts/village-complete/src/main/resources/assets/minecraftzombiearmy/map/biomes.json'
resource.parent.mkdir(parents=True,exist_ok=True)
resource.write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['# 67 个群系的地图设计','', 'Minecraft 26.3 JAR 群系注册数据逐项对照；中文名称来自同版本 zh_cn。色彩为 TextingDream 制图设计色，不声称等同游戏纹理 RGB。','', '|群系|ID|底色 / 特征色|纹理与辨识特征|','|---|---|---|---|']
lines += [f"|{r['name']}|{r['id']}|{r['ground']} / {r['accent']}|{r['note']}（{r['motif']}）|" for r in rows]
(out/'逐群系设计.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('Catalog verified: 67/67, resource and per-biome design written')
