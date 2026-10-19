import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.web import create_app
from app.service import Service
from app.storage import Store
from app.reply_direction import ReplyDirectionRequest,draft_reply

ROOT=Path(__file__).resolve().parents[1]

class ReplyDirectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.svc=Service(Store(Path(self.tmp.name)/'t.sqlite3'),ROOT)
        self.svc.provider.configure({'offline':True});self.s=self.svc.runtime.new_session('方向','protagonist')
    def tearDown(self):self.tmp.cleanup()
    def test_draft_does_not_change_game_or_memories(self):
        before=self.svc.store.session(self.s['id'])
        r=asyncio.run(draft_reply(self.svc,self.s['id'],ReplyDirectionRequest(directions=['friendly','clarify'])))
        self.assertIn('谢谢',r['text']);self.assertEqual(before,self.svc.store.session(self.s['id']))
        self.assertEqual(r['usage']['calls'],0)
    def test_remote_scoped_context_routing_and_staleness(self):
        self.svc.provider.configure({'offline':False,'dialogue_model':'test-dialogue','author_model':'test-author'})
        self.assertEqual(self.svc.provider.model_for('player_reply'),'test-dialogue')
        async def respond(system,context,**kwargs):
            self.assertEqual(kwargs['scope'],'player_reply');self.assertNotIn('atlas',context['player_context'])
            self.assertNotIn('secret',context['player_context'])
            s=self.svc.store.session(self.s['id']);s['time']+=1;self.svc.store.save_session(s)
            return '请说清楚。',{}
        with patch.object(self.svc.provider,'complete',respond):
            with self.assertRaisesRegex(ValueError,'旅程已变化'):
                asyncio.run(draft_reply(self.svc,self.s['id'],ReplyDirectionRequest(instruction='问清条件')))
    def test_validation_and_observer_guard(self):
        for data in ({},{'directions':['bad']},{'directions':['clarify','clarify']}):
            with self.assertRaises(ValueError):ReplyDirectionRequest(**data)
        s=self.svc.runtime.new_session('旁观','observer')
        with self.assertRaises(ValueError):asyncio.run(draft_reply(self.svc,s['id'],ReplyDirectionRequest(directions=['friendly'])))
    def test_api_guard(self):
        with TestClient(create_app(Path(self.tmp.name)/'web.sqlite3')) as c:
            b=c.get('/api/bootstrap').json();h={'X-TextileDream-Token':b['token']}
            self.assertEqual(len(c.get('/api/reply-directions').json()),6)
            c.app.state.service.provider.configure({'offline':True})
            s=c.post('/api/sessions',headers=h,json={}).json()
            url='/api/sessions/'+s['id']+'/reply-draft'
            self.assertEqual(c.post(url,json={'directions':['clarify']}).status_code,403)
            r=c.post(url,headers=h,json={'directions':['clarify']})
            self.assertEqual(r.status_code,200);self.assertIn('text',r.json())
