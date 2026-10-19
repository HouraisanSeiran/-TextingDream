import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / 'world_packages/玄陆_世界包.json'
story = json.loads(path.read_text(encoding='utf-8'))
for loc, xy in zip(story['locations'], [[108.9,34.3],[94.7,40.1],[44.4,33.3],[28.9,41.0]]):
    loc['coordinates'] = xy
story['items'][0]['location_id'] = 'tianchao_capital'
story['events'][0]['actions'] = [{'id':'pack','label':'整理行装，带上万言机','effects':[{'op':'take','id':'translation_machine'}],'ends_event':True,'success_text':'我将万言机收进行囊，踏上西行的路。'}]
story['events'][1]['actions'] = [{'id':'translate','label':'尝试翻译通关文书','check':{'attribute':'理解','difficulty':0.55},'success':[{'op':'flag','id':'translated','value':True}],'failure':[{'op':'flag','id':'needs_help','value':True}],'ends_event':True,'success_text':'我认出了文书的关键语句，守卫让开道路。','failure_text':'译文中仍有歧义。守卫指向商驿：那里或许有人能教我。'}]
story['events'][2]['actions'] = [{'id':'listen','label':'听商人讲述道路上的消息','effects':[{'op':'rumor','truth':'西行道路封闭3天；东侧便道仍然开放','character':'oasis_merchant','transform':'number_scale','factor':3,'source':'驿站转述时夸大数字'}],'ends_event':True,'success_text':'我听见商人说：“西行道路封闭9天，东侧便道仍然开放。”这只是他的说法。'}]
story['events'][3]['actions'] = [{'id':'ask','label':'向学者询问下一段旅程','effects':[{'op':'fact','text':'港口提供继续西行的航路。','visible':True}],'ends_event':True,'success_text':'我在学者指引下记下航路。旅程尚未结束，陌生的海岸正在前方。'}]
for event in story['events']:
    event.update(max_turns=8, exit_flag='completed_'+event['id'], player_enters=True)
path.write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding='utf-8')
path = root / 'character_packages/xuanlu_初始角色包.json'
chars = json.loads(path.read_text(encoding='utf-8'))
chars['characters'][0]['attributes'] = {'理解':0.6}
path.write_text(json.dumps(chars, ensure_ascii=False, indent=2), encoding='utf-8')
geo = json.loads((root / 'assets/maps/natural-earth-land.geojson').read_text(encoding='utf-8'))
paths = []
for feature in geo['features']:
    geometry = feature['geometry']
    polygons = geometry['coordinates'] if geometry['type'] == 'MultiPolygon' else [geometry['coordinates']]
    for polygon in polygons:
        parts = ['M' + ' L'.join(f'{(x+180)*4:.2f},{(90-y)*4:.2f}' for x,y in ring) + ' Z' for ring in polygon]
        paths.append('<path d="' + ' '.join(parts) + '"/>')
svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1440 720"><rect width="1440" height="720" fill="#151f29"/><g fill="#748674" stroke="#bac7a3" stroke-width="0.5" fill-rule="evenodd">' + ''.join(paths) + '</g></svg>'
(root / 'assets/maps/world.svg').write_text(svg, encoding='utf-8')
print('Demo actions and map prepared')
