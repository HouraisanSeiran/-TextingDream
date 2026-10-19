import asyncio,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app.service import Service
from app.storage import Store
from app.world_pipeline import WorldPipeline,PipelineRequest

async def main():
    out=ROOT/'artifacts/world_pipeline_online';out.mkdir(exist_ok=True)
    svc=Service(Store(out/'test.sqlite3'),ROOT)
    keys=set(re.findall(r'sk-[A-Za-z0-9_-]{16,}',Path('C:/Users/Huang/Desktop/api用后即删.txt').read_text(encoding='utf-8-sig')))
    if len(keys)!=1:raise ValueError('Need unique key')
    svc.provider.configure({'api_key':keys.pop(),'offline':False,'model':'deepseek-flash','author_model':'deepseek-flash','max_tokens':8192})
    g=WorldPipeline(svc)
    if '--resume' in sys.argv:
        report=json.loads((out/'result.json').read_text(encoding='utf-8'));p=g.get(report['pipeline_id'])
        report['previous_error']=report.pop('error',None)
    else:
        p=g.start(PipelineRequest(title='沃土与山岭测试',regions=2,instruction='两块相邻自然区域：河谷与山岭。先生成自然地理，再生成沃土与铁矿，最后形成依靠贸易交换粮食与矿产的两个前工业共同体。非真实历史，保持简短，每阶段只填写必要内容。'))
        report={'pipeline_id':p['id'],'stages':[]}
    try:
        for i in range(len(p['stages']),4):
            p=await g.advance(p['id']);report['stages'].append({'name':p['stages'][-1]['name'],'usage':p['stages'][-1]['usage']})
            (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(report['stages'][-1],ensure_ascii=False),flush=True)
        saved=g.save(p['id']);report['folder']=saved['folder'];report['status']='complete'
        svc.runtime.activate_package(saved['folder']);s=svc.runtime.new_session('生成验证','protagonist')
        assert svc.runtime.surface(s)['actions']
    except Exception as e:report.update(status='failed',error=str(e));print(type(e).__name__,str(e),flush=True)
    finally:
        (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        (out/'traces.json').write_text(json.dumps(svc.store.all('trace'),ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':asyncio.run(main())
