import copy
import json
import unittest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch
import httpx
from app.provider import Provider
from app.storage import Store
from app.prompts import context_json, stable_json


class PromptCacheTests(unittest.TestCase):
    def test_current_fields_do_not_break_scene_history_prefix(self):
        a = {'scene':'城内','location':'都城','description':'公开描述','characters':[],
             'last_summary':'上一场景已知见闻','history':[{'input':'你好','reply':'早安'}],
             'current_time':9,'current_state':'平静','knowledge':[], 'input':'第一问'}
        b = copy.deepcopy(a)
        b.update(current_time=10,current_state='疲倦',input='第二问',knowledge=[{'id':'new','content':'新检索'}])
        left,right = context_json(a,'surface'),context_json(b,'surface')
        self.assertEqual(left.split(',"knowledge":')[0],right.split(',"knowledge":')[0])
        self.assertEqual(json.loads(left),a)
        self.assertEqual(json.loads(right),b)
        self.assertTrue(right.endswith('"input":"第二问"}'))

    def test_order_is_deterministic_and_does_not_add_information(self):
        context={'input':'q','history':[{'reply':'b','input':'a'},{'reply':'d','input':'c'}],
                 'characters':[{'id':'z','name':'Z'},{'id':'a','name':'A'}],'future_extension':{'z':1,'a':2}}
        first=context_json(context,'surface')
        self.assertEqual(first,context_json(dict(reversed(list(context.items()))),'surface'))
        decoded=json.loads(first)
        self.assertEqual(decoded['history'],context['history'])
        self.assertEqual(set(decoded),set(context))
        self.assertEqual(json.loads(context_json(context,'inner')),json.loads(stable_json(context)))

    def test_provider_sends_ordered_context_without_changing_values(self):
        with tempfile.TemporaryDirectory() as directory:
            provider=Provider(Store(Path(directory)/'test.sqlite3'))
            provider.configure({'base_url':'https://api.deepseek.com','model':'deepseek-v4-pro',
                                'offline':False,'max_tokens':8000,'api_key':'test-not-real'})
            context={'current_time':19,'history':[{'input':'问','reply':'答'}],'scene':'城','input':'继续'}
            requests=[]
            def respond(request):
                requests.append(json.loads(request.content))
                return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':'正文'}}],'usage':{}})
            original=httpx.AsyncClient
            with patch('app.provider.httpx.AsyncClient',side_effect=lambda **kw: original(transport=httpx.MockTransport(respond),**kw)):
                asyncio.run(provider.complete('固定规则',context,scope='surface'))
            sent=requests[0]['messages'][1]['content']
            self.assertEqual(json.loads(sent),context)
            self.assertLess(sent.index('"history"'),sent.index('"current_time"'))
