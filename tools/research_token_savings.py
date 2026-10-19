"""Fetch official documentation as dated, readable research evidence."""
from pathlib import Path
from html.parser import HTMLParser
import httpx

ROOT=Path(__file__).resolve().parents[1]
class Text(HTMLParser):
    def __init__(self):
        super().__init__();self.parts=[];self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'):self.skip+=1
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.skip=max(0,self.skip-1)
    def handle_data(self,data):
        if not self.skip and data.strip():self.parts.append(data.strip())

out=ROOT/'artifacts/token_research';out.mkdir(parents=True,exist_ok=True)
with httpx.Client(timeout=45,follow_redirects=True) as client:
    for name,url in [('cache','https://api-docs.deepseek.com/guides/kv_cache'),
                     ('thinking','https://api-docs.deepseek.com/guides/thinking_mode'),
                     ('context','https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents')]:
        r=client.get(url);r.raise_for_status();p=Text();p.feed(r.text)
        text='\n'.join(p.parts)
        (out/(name+'.txt')).write_text(url+'\n'+text,encoding='utf-8')
        lines=text.splitlines()
        keywords=('prefix','cache','compact','summar','token','disabled','thinking','最小','缓存','摘要')
        matches=[i for i,s in enumerate(lines) if any(k in s.lower() for k in keywords)]
        print('\nSOURCE',url)
        print('\n'.join(lines[i][:1500] for i in matches[:35]))
