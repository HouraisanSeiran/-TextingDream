"""Two live authoring probes, saved only in an isolated temporary library."""
import asyncio,json,re,sys,tempfile
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.service import Service
from app.storage import Store
from app.world_generator import GenerateWorldRequest

async def main():
    keys=set(re.findall(r'sk-[A-Za-z0-9_-]{16,}',Path('C:/Users/Huang/Desktop/api用后即删.txt').read_text(encoding='utf-8-sig')))
    if len(keys)!=1:raise ValueError('需要唯一测试密钥')
    out=ROOT/'artifacts'/('world_workshop_'+datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir(parents=True)
    rows=[]
    with tempfile.TemporaryDirectory() as tmp:
        svc=Service(Store(Path(tmp)/'live.sqlite3'),ROOT)
        svc.provider.configure({'api_key':keys.pop(),'model':'deepseek-flash','offline':False,'max_tokens':8000})
        for kind,instruction in [('expand','保留玄陆全部原设定。只新增2个知识点，细化西行关城的水站供水与商队维护义务；新增2个公开地点标记，绑定western_pass并各关联一个新增知识点，勿添加秘密或虚构已完成事件。不要复用已有ID。'),
                                 ('complete','创建两座沿河的低魔城市，水源与贸易互补，文化与政权范围不同。四个世界观知识点即可，文字简明；所有城市的气候、资源、文化、信仰、经济字段均填写。主角为旅人。')]:
            if '--complete-only' in sys.argv and kind!='complete':continue
            try:
                d=await svc.world_generator.generate(GenerateWorldRequest(kind=kind,title='两河城邦验证',instruction=instruction,city_count=2,output_tokens=8000))
                saved=svc.world_generator.save(d['id'])
                atlas=svc.world_generator.preview_atlas(d['id'])
                rows.append({'kind':kind,'status':'success','data':d['data'],'usage':d['usage'],'map_features':len(atlas['features']),'saved':saved['folder']})
            except ValueError as e:rows.append({'kind':kind,'status':'error','error':str(e)})
            print(json.dumps({k:v for k,v in rows[-1].items() if k!='data'},ensure_ascii=False),flush=True)
        (out/'results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
        (out/'traces.json').write_text(json.dumps(svc.store.all('trace'),ensure_ascii=False,indent=2),encoding='utf-8')
    print('Artifacts:',out,flush=True)
if __name__=='__main__':asyncio.run(main())
