import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import httpx
from app.storage import Store
from app.provider import Provider
from app.service import Service
from app.contracts import DraftRequest
from app.recall import Recall

ROOT = Path(__file__).resolve().parents[1]


class WorkerRecallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name)/'test.sqlite3')
    def tearDown(self):
        self.tmp.cleanup()

    def test_recall_first_meal_unrelated_isolation_and_rollback(self):
        recall = Recall(self.store)
        rows = [
            {'source_id':'e:0','input':'我第一次给你做了炒肉和白粥。','reply':'肉有点咸，粥很好喝。'},
            {'source_id':'e:1','input':'今天又做了炒肉和白粥。','reply':'这次咸淡正好。'},
            {'source_id':'e:2','input':'我们去城外骑马。','reply':'沿着山道往北走。'},
        ]
        for query in ('我第1次给你做的炒肉和白粥好不好吃？','头一次下厨的米粥味道如何？'):
            hits = recall.search('s1', query, rows)
            self.assertEqual(hits[0]['source_id'],'e:0')
            self.assertIn('有点咸', hits[0]['reply'])
        self.assertEqual(recall.search('s1','继续',rows),[])
        self.assertEqual(recall.search('s1','检查城门通行证',rows),[])
        self.assertEqual(recall.search('s2','炒肉和白粥',[]),[])
        self.assertEqual(recall.search('s1','炒肉和白粥',rows,exclude=['e:0','e:1']),[])
        self.assertEqual(recall.search('s1','炒肉和白粥',rows[2:]),[])
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM recall_vectors WHERE session=?',('s1',)).fetchone()[0],1)

    def test_payload_routing_concurrency_and_key_preservation(self):
        provider = Provider(self.store)
        self.store.put('settings','api',{'model':'deepseek-flash','offline':False,'max_tokens':8000})
        self.assertEqual(provider.config()['max_concurrency'],2)
        provider.configure({'api_key':'test-private-key','dialogue_model':'deepseek-flash','author_model':'deepseek-v4-pro'})
        provider.configure({'api_key':''})
        self.assertEqual(provider.key,'test-private-key')
        self.assertNotIn('api_key',self.store.get('settings','api'))
        requests=[]; active=0; peak=0
        async def reply(req):
            nonlocal active, peak
            active+=1;peak=max(peak,active)
            requests.append(json.loads(req.content))
            await asyncio.sleep(.03)
            active-=1
            return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':'正文'}}],'usage':{}})
        original=httpx.AsyncClient
        async def run():
            with patch('app.provider.httpx.AsyncClient',side_effect=lambda **kw:original(transport=httpx.MockTransport(reply),**kw)):
                await asyncio.gather(*(provider.complete('规则',{},scope=s) for s in ['surface','inner','surface','inner']))
                provider.configure({'thinking_mode':'disabled','temperature':0.4})
                await provider.complete('规则',{},scope='surface')
        asyncio.run(run())
        self.assertEqual(peak,2)
        self.assertEqual(requests[0]['model'],'deepseek-flash')
        self.assertEqual(requests[1]['model'],'deepseek-v4-pro')
        self.assertNotIn('temperature',requests[0])
        self.assertEqual(requests[0]['reasoning_effort'],'high')
        self.assertEqual(requests[-1]['temperature'],0.4)
        self.assertEqual(provider._active,0)

    def test_failed_batch_preserves_sibling_and_surface_can_overlap(self):
        svc=Service(self.store,ROOT)
        svc.provider.configure({'offline':False})
        active=0;peak=0
        async def complete(system,context,**kwargs):
            nonlocal active,peak
            active+=1;peak=max(peak,active)
            await asyncio.sleep(.03)
            active-=1
            if context['example']['kind']=='fact':raise ValueError('测试失败')
            return context['example'],{}
        with patch.object(svc.provider,'complete',complete):
            result=asyncio.run(svc.generate_batch([DraftRequest(kind='fact',instruction='背景'),DraftRequest(kind='item',instruction='物品')]))
        self.assertEqual(peak,2)
        self.assertIn('error',result['results'][0])
        self.assertEqual(result['results'][1]['draft']['status'],'draft')
        self.assertEqual(len(self.store.all('draft')),1)

    def test_npc_cannot_retrieve_player_private_chat(self):
        svc=Service(self.store,ROOT)
        s=svc.runtime.new_session('隔离测试','protagonist')
        s['active']['turns']=[{'input':'第一次做炒肉白粥','reply':'秘密配方桂花'}]*20
        prefs=svc.preferences()
        player=svc.runtime.context(s,'player','炒肉白粥',prefs)
        self.assertTrue(player['recalled_dialogue'])
        npc=svc.runtime.context(s,'oasis_merchant','炒肉白粥',prefs)
        self.assertEqual(npc['recalled_dialogue'],[])
        disabled=svc.runtime.context(s,'player','炒肉白粥',{**prefs,'recall_enabled':False})
        self.assertEqual(disabled['recalled_dialogue'],[])
