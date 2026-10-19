"""Save dated primary-source excerpts; failures remain explicit."""
import asyncio
import json
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[1]
SOURCES={
    'openai_eval':'https://platform.openai.com/docs/guides/evaluation-best-practices',
    'openai_structured':'https://platform.openai.com/docs/guides/structured-outputs',
    'anthropic_workflows':'https://www.anthropic.com/engineering/building-effective-agents',
    'anthropic_context':'https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents',
    'generative_agents':'https://arxiv.org/abs/2304.03442',
    'lost_middle':'https://arxiv.org/abs/2307.03172',
    'self_correction':'https://arxiv.org/abs/2310.01798',
    'rolellm':'https://arxiv.org/abs/2310.00746',
    'deepseek_json':'https://api-docs.deepseek.com/guides/json_mode',
    'openai_eval_alternate':'https://developers.openai.com/api/docs/guides/evaluation-best-practices',
    'openai_structured_alternate':'https://developers.openai.com/api/docs/guides/structured-outputs',
    'generative_agents_full':'https://arxiv.org/html/2304.03442v2',
    'self_correction_full':'https://arxiv.org/html/2310.01798v2',
}
class Text(HTMLParser):
    def __init__(self):
        super().__init__();self.parts=[];self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style','svg'):self.skip+=1
    def handle_endtag(self,tag):
        if tag in ('script','style','svg'):self.skip=max(0,self.skip-1)
    def handle_data(self,data):
        if not self.skip and data.strip():self.parts.append(data.strip())

async def main():
    out=ROOT/'artifacts/prompt_research';out.mkdir(parents=True,exist_ok=True)
    async with httpx.AsyncClient(timeout=35,follow_redirects=True) as client:
        async def fetch(name,url):
            existing=out/(name+'.txt')
            if existing.exists():
                return {'name':name,'url':url,'cached':True,'characters':len(existing.read_text(encoding='utf-8'))}
            row={'name':name,'url':url,'retrieved_utc':datetime.now(timezone.utc).isoformat()}
            try:
                r=await client.get(url);row.update(status=r.status_code,final_url=str(r.url));r.raise_for_status()
                p=Text();p.feed(r.text);body='\n'.join(p.parts)
                (out/(name+'.txt')).write_text(url+'\n'+body,encoding='utf-8')
                row['characters']=len(body)
                terms=('abstract','ablation','mistake','schema','criteria','human','evaluation','workflow','reflection','memory','correct','role-playing','role playing','middle','json')
                lines=[s for s in p.parts if len(s)>65 and any(w in s.lower() for w in terms)]
                print(name+'\n'+'\n'.join(lines[:12])[:8500],flush=True)
            except Exception as e:
                row['error']=type(e).__name__;print(name+' '+row['error'],flush=True)
            return row
        rows=await asyncio.gather(*(fetch(k,v) for k,v in SOURCES.items()))
    (out/'sources.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':asyncio.run(main())
