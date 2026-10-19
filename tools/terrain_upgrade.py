"""Explicit fictional terrain categories; no inferred elevation or contour lines."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.knowledge import PackageFiles
from app.atlas import validate_atlas

def main():
    source=(ROOT/'assets/maps/world-detailed.svg').read_text(encoding='utf-8')
    for a,b in [('#172f3c','#b0d4df'),('#3c514a','#e4e1cb'),('#234858','#91bfd1'),('#60766a','#9eab94'),('#568797','#6a9daf')]:source=source.replace(a,b)
    (ROOT/'assets/maps/world-terrain.svg').write_text(source,encoding='utf-8')
    files=PackageFiles(ROOT/'StoryPackage/玄陆');story=files.read();features=story['atlas']['features']
    updates={'atlas_xuanlu_eastern_range':'mountain','atlas_xuanlu_central_range':'mountain','atlas_xuanlu_dry_basin':'desert'}
    for f in features:
        if f['id'] in updates:f['terrain_kind']=updates[f['id']]
    regions=[
      ('plateau','中段高原','plateau',[[72,30],[78,28],[86,30],[91,34],[84,36],[76,35]],'basins','高地风寒、坡道与补水点限制通行，低地粮食需经山口输入；未指定海拔。'),
      ('east_plain','澄京河谷平原','plain',[[106,33],[111,32.7],[114,34.5],[110,35.5],[107,35]],'eastern_basin','河谷适宜耕作与转运，渡口和堤防形成交通瓶颈；雨季泥泞不能由地图自动判为已发生。'),
      ('foothills','东陆山前丘陵','hill',[[103,30],[108,29],[112,31],[109,33],[105,32]],'basins','聚落沿谷地分布，坡耕地与林地交错；车队可能需要绕行或换用驮运。'),
      ('forest','东南山麓林地','forest',[[110,25],[115,24],[119,27],[117,30],[112,29]],'resource_flows','候选林地覆盖区，与丘陵并存；提供木材药材，采伐和运输受道路、季节及当地权利约束。'),
      ('alluvial','沃土冲积平原','plain',[[42,32],[45,30.5],[48,31],[46,34],[43,35]],'oasis_hydrology','灌溉、排盐与渠桥关系决定聚落生计，平坦不代表处处可通行。'),
      ('delta','南岸河口湿地','wetland',[[29,30.3],[31,30],[32,31.1],[30.5,31.7],[29,31.3]],'coastal_winds','河汊、浅滩和湿地交错，小舟与引水人重要；洪水、虫害与失踪消息需另有事件证据。'),
      ('dry_south','南岸内陆荒漠','desert',[[24,25],[31,24],[30,29.5],[25,30]],'pass_water','沿河与绿洲外为干旱区域工作稿，旅行依赖补水与向导；不能凭一片黄色推出完全无人居住。')]
    ids={f['id'] for f in features}
    for key,name,kind,coords,article,body in regions:
        fid='terrain_xuanlu_'+key
        if fid in ids:continue
        pid=fid+'_lore'
        story['knowledge'].append({'id':pid,'title':name+' · 旅行与生计','category':'地图补充_地形与叙事','keywords':[name,{'plateau':'高原','plain':'平原','hill':'丘陵','forest':'森林','wetland':'湿地','desert':'荒漠'}[kind],'地形'],
            'content':'架空地形工作稿：'+body+' 区域边界为示意，可由作者调整；不是实际测绘。','visibility':'public','status':'可调整架空工作稿'})
        features.append({'id':fid,'name':name,'layer':'terrain','geometry':'polygon','coordinates':coords,'terrain_kind':kind,
            'description':body,'knowledge_ids':[pid,'atlas_xuanlu_'+article],'visibility':'public','location_ids':[]})
    story['atlas']['note']='玄陆地形分区工作稿：颜色与符号表示地貌或地表覆盖，不代表测绘海拔；未设定区域不推断地形。参考底图不用于计算旅行时间。'
    validate_atlas(story);files.write(story)
    print('Terrain base and 7 authored terrain regions ready; existing edits preserved on repeat.')

if __name__=='__main__':main()
