"""Idempotent authored default-world migration, retaining a reviewable backup."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app import attributes
from app.geography import Environment, Calendar, environment_features
from app.knowledge import PackageFiles, atomic_text
from app.runtime import Runtime


def main():
    folder=ROOT/'StoryPackage'/'玄陆';files=PackageFiles(folder);story=files.read()
    charfile=ROOT/'character_packages'/'xuanlu_初始角色包.json'
    chars=json.loads(charfile.read_text(encoding='utf-8'))
    backup=ROOT/'artifacts'/'before_attributes_geography'
    if not backup.exists():
        backup.mkdir(parents=True)
        for name,data in [('story.json',story),('characters.json',chars)]:atomic_text(backup/name,json.dumps(data,ensure_ascii=False,indent=2))
    story,chars=attributes.upgrade(story,chars,legacy='attributes' not in story.get('mechanics',{}))
    presets={'protagonist':[60,45,55,60,50,55], 'pass_guard':[35,75,55,55,35,75],
             'oasis_merchant':[40,40,55,65,85,50], 'port_scholar':[70,35,45,85,65,40]}
    for c in chars['characters']:
        if c['id'] in presets:c['attributes']=dict(zip(attributes.AXES,presets[c['id']]))
    envs=[dict(elevation_m=420,slope_deg=3,precipitation_mm=650,temperature_c=14,freshwater=.85,soil_fertility=.85,irrigation=.65,transport=.8,basin='东部大河中游',river_path=[[107.5,35.2],[108.9,34.3],[110,34]],river_elevations_m=[750,420,260],deposits=[dict(kind='iron',abundance=.65,accessibility=.7,technology=.6,surveyed=True),dict(kind='coal',abundance=.6,accessibility=.6,technology=.3,surveyed=True)]),
          dict(elevation_m=1450,slope_deg=8,precipitation_mm=110,temperature_c=9,freshwater=.4,soil_fertility=.4,irrigation=.7,transport=.35,basin='西关内流绿洲',river_path=[[95.5,39.1],[94.7,40.1],[94.2,40.5]],river_elevations_m=[3200,1450,1200],deposits=[dict(kind='copper',abundance=.5,accessibility=.35,technology=.6,surveyed=True),dict(kind='rare_metals',abundance=.6,accessibility=.2,technology=.05,surveyed=False)]),
          dict(elevation_m=45,slope_deg=2,precipitation_mm=180,temperature_c=23,freshwater=.85,soil_fertility=.8,flood_risk=.5,irrigation=.8,transport=.75,basin='新月两河灌溉区',river_path=[[43.5,35],[44.4,33.3],[46,31]],river_elevations_m=[400,45,10],deposits=[]),
          dict(elevation_m=40,slope_deg=6,precipitation_mm=760,temperature_c=15,freshwater=.65,soil_fertility=.6,transport=.9,basin='海峡沿岸集水区',deposits=[dict(kind='iron',abundance=.35,accessibility=.6,technology=.5,surveyed=True)]),
          dict(elevation_m=8,slope_deg=1,precipitation_mm=180,temperature_c=21,freshwater=.9,soil_fertility=.9,flood_risk=.65,irrigation=.75,transport=.85,basin='南岸大河三角洲',river_path=[[30,29],[30,30],[29.9,31.2]],river_elevations_m=[80,35,8],deposits=[])]
    features=story.setdefault('atlas',{}).setdefault('features',[])
    for place,env in zip(story['locations'],envs):
        place['environment']=Environment(**env,area_km2=2500,source='玄陆架空地理设计v1；参考类似地貌规律，非现实矿床/人口测绘').model_dump(mode='json')
        additions=environment_features(place);ids={f['id'] for f in additions}
        features[:]=[f for f in features if f['id'] not in ids];features.extend(additions)
    story['mechanics']['calendar']=Calendar(utc_offset=8,start_day_of_year=100).model_dump()
    Runtime.validate_package(None,story,chars)
    files.write(story)
    for path in (charfile,ROOT/'character_packages'/(chars['id']+'.json')):atomic_text(path,json.dumps(chars,ensure_ascii=False,indent=2))
    # Stable UI extension and prompt append without rewriting existing source instructions.
    index=ROOT/'app/static/index.html';text=index.read_text(encoding='utf-8')
    if 'world-systems.js' not in text:text=text.replace('</body>','<script src="/static/world-systems.js"></script>\n</body>')
    atomic_text(index,text)
    atlas=ROOT/'app/static/atlas.js';text=atlas.read_text(encoding='utf-8')
    text=text.replace("['terrain','states','cultures','water','routes','markers']","['terrain','elevation','farmland','states','cultures','water','routes','resources','population','markers']")
    text=text.replace("color=f.layer==='terrain'?style[1]:colors[f.layer]", "color=f.layer==='elevation'?(f.environment?.elevation_m>=2500?'#aa8065':f.environment?.elevation_m>=1000?'#ceb27c':f.environment?.elevation_m>=300?'#b7c68a':'#78b58b'):f.layer==='terrain'?style[1]:colors[f.layer]")
    atomic_text(atlas,text)
    additions={
      'surface':'\n能力表达约束v1：player_abilities与cast.ability_expression是本地计算的硬档位；仅在相关行动体现，不朗读属性和规则。智慧决定危险线索识别和应变判定，敏捷决定动作执行；高智慧不等于预知陷阱。社交决定可用表达策略，不代表善良。保留每个人的意图、词汇和节奏，不把所有人写成核实文书的守门人。geography只含当前地区公开资料；solar是日出日落近似计算，不能再从整点臆测；无太阳数据时不推断。矿藏潜力、承载人口不等于已开采产量或实际人口。',
      'generator':'\n世界要素生成v1：每个城市生成environment：海拔、坡度、降雨、温度、水源、土壤、洪灾风险、灌溉、运输、治理、腹地面积和流域；填写架空设计来源。河道提供river_path与等长river_elevations_m，顺流海拔不得上升，不无理由跨分水岭。deposits区分iron/coal/copper/tin/gold/rare_metals，分开丰度、可达性、技术和surveyed已知状态；不是每城都产矿。河流沃土须兼顾洪水、盐渍化与灌溉，不把海拔当唯一人口因素。只有确定边界才绘polygon，否则使用point。人口承载和适耕比例交本地计算，不编实际普查。hero和guide的attributes必须填写talent/strength/agility/wisdom/social/resilience六项0到100数值；talent中文名天赋，仅替代灵力亲合度。kind=expand可用elevation/resources/farmland/population图层及environment生成这些元素。以粮食、水、矿、燃料和通道解释贸易依赖，不直接推断国家必然征服。',
      'author':'\n属性约束v1：人物attributes必须包含talent天赋、strength力量、agility敏捷、wisdom智慧、social社交、resilience韧性六项0到100数值。天赋仅为灵力亲合度改名。不要用属性推断道德；性格与表达意图独立填写。事件check引用稳定英文ID，difficulty仍用0到1，成功失败由本地裁定。'}
    for name,addition in additions.items():
        path=ROOT/'app/prompt_templates'/(name+'.txt');text=path.read_text(encoding='utf-8')
        if addition.strip() not in text:atomic_text(path,text+addition+'\n')
    print('Updated default package, four character profiles, geographic layers, prompts and UI include; backup:',backup)

if __name__=='__main__':main()
