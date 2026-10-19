import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import httpx
from app.service import Service
from app.storage import Store
from app.contracts import Turn
from app.prompts import surface_prefix

ROOT=Path(__file__).resolve().parents[1]

class EfficiencyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.svc=Service(Store(Path(self.tmp.name)/'test.sqlite3'),ROOT)
        self.rt=self.svc.runtime
        self.svc.provider.configure({'base_url':'https://api.deepseek.com','model':'deepseek-v4-pro','offline':True,'max_tokens':8000})
        self.s=self.rt.new_session('连续旅程','protagonist')
    def tearDown(self):
        self.tmp.cleanup()
    def turn(self,action):
        asyncio.run(self.svc.turn(self.s['id'],Turn(message='继续',action_id=action)))
        self.s=self.svc.store.session(self.s['id'])
    def test_default_merges_scenes_keeps_event_continuation_and_rollback(self):
        self.turn('pack'); first=self.s['conversation']['id']
        self.rt.move(self.s,'western_pass');self.turn('translate')
        self.rt.move(self.s,'crescent_oasis');self.turn('listen')
        self.rt.move(self.s,'western_port');self.turn('ask')
        self.rt.move(self.s,'south_lantern_port');self.turn('read_letter')
        self.assertEqual(self.s['active']['node'],'south_oath')
        self.assertEqual(self.s['conversation']['id'],first)
        context=self.rt.context(self.s,'player','书信',self.svc.preferences())
        self.assertIn('南岸',context['scene'])
        self.assertNotIn('3天',json.dumps(context,ensure_ascii=False))
        self.turn('record_oath')
        self.assertEqual(len(self.rt.conversations(self.s)),1)
        self.assertEqual(len(self.s['archives']),6)
        rollback=self.rt.rollback(self.s,self.s['archives'][1]['id'])
        self.assertEqual(rollback['location'],'western_pass')
        self.assertEqual(rollback['conversation']['id'],first)
    def test_threshold_only_splits_at_scene_transition(self):
        self.svc.store.put('settings','preferences',{'chapter_turns':12})
        for _ in range(11):
            self.turn(None)
        first=self.s['conversation']['id']
        self.turn('pack')
        self.assertEqual(self.s['conversation']['id'],first)
        self.rt.move(self.s,'western_pass')
        self.assertNotEqual(self.s['conversation']['id'],first)
    def test_recent_reply_not_repeated_as_knowledge(self):
        self.s['active']['turns']=[{'input':'问路','reply':'商人说道路关闭九天，但这只是传闻，还未证实。'}]
        ctx=self.rt.context(self.s,'player','商人道路传闻',self.svc.preferences())
        self.assertEqual(ctx['dialogue_knowledge'],[])
        self.assertIn('未证实',ctx['history'][0]['reply'])
    def test_custom_corpus_preserved_empty_default(self):
        self.assertEqual(self.svc.store.get('corpus','general')['text'],'')
        custom='请保持诗意节奏。'
        self.svc.store.put('corpus','general',{'text':custom})
        again=Service(self.svc.store,ROOT)
        self.assertEqual(again.store.get('corpus','general')['text'],custom)
        self.assertIn(custom,surface_prefix(self.rt.package(),custom))
    def test_thinking_only_official_surface_and_toggle(self):
        self.svc.provider.configure({'base_url':'https://api.deepseek.com','model':'deepseek-v4-pro','offline':False,'max_tokens':8000,'api_key':'test-only'})
        requests=[]
        def reply(req):
            requests.append(json.loads(req.content))
            return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':'正文'}}],'usage':{}})
        original=httpx.AsyncClient
        with patch('app.provider.httpx.AsyncClient',side_effect=lambda **kw:original(transport=httpx.MockTransport(reply),**kw)):
            asyncio.run(self.svc.provider.complete('规则',{},scope='surface'))
            asyncio.run(self.svc.provider.complete('规则',{},scope='inner'))
            self.svc.provider.configure({'thinking_mode':'disabled'})
            asyncio.run(self.svc.provider.complete('规则',{},scope='surface'))
        self.assertEqual(requests[0]['thinking'],{'type':'enabled'})
        self.assertEqual(requests[1]['thinking'],{'type':'enabled'})
        self.assertEqual(requests[2]['thinking'],{'type':'disabled'})

    def test_current_state_overrides_old_scene_and_invented_inventory(self):
        self.turn('pack')
        self.rt.move(self.s,'western_pass')
        ctx=self.rt.context(self.s,'player','查看背包和周围',self.svc.preferences())
        self.assertEqual(ctx['location'],'西行关城')
        self.assertEqual(ctx['current_inventory'],['万言机'])
        self.assertEqual(ctx['current_event']['title'],self.rt.node(self.s)['title'])
        self.assertIn(ctx['current_daytime'],('白昼','夜间'))
