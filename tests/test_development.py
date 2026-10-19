import asyncio
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.service import Service
from app.storage import Store
from app.contracts import Turn, DevelopmentRequest
from app.web import create_app

ROOT=Path(__file__).resolve().parents[1]

class DevelopmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.svc=Service(Store(Path(self.tmp.name)/'t.sqlite3'),ROOT)
        self.svc.provider.configure({'base_url':'https://api.deepseek.com','model':'deepseek-v4-pro','offline':True,'max_tokens':8000})
        self.rt=self.svc.runtime;self.s=self.rt.new_session('成长测试','protagonist')
        asyncio.run(self.svc.turn(self.s['id'],Turn(message='带上万言机',action_id='pack')))
        self.rt.move(self.svc.store.session(self.s['id']),'western_pass')
        asyncio.run(self.svc.turn(self.s['id'],Turn(message='我愿意按规矩核验，但没有担保人。',channel='speech')))
    def tearDown(self):self.tmp.cleanup()
    def proposal(self):
        s=self.svc.store.session(self.s['id']);c=self.svc.development.context(s,'pass_guard')
        return c,{'character_id':'pass_guard','assessment':'愿意配合，可考虑小幅增加信任。','changes':[{'category':'relationship','key':'trust','target_id':'protagonist','value':0.6,'evidence_ids':[c['evidence'][0]['id']],'rationale':'玩家表达愿意核验；只证明态度，最终需作者评估。'}]}
    def make(self):
        c,data=self.proposal();self.svc.provider.configure({**self.svc.provider.config(),'offline':False})
        async def respond(*a,**k):return data,{'calls':1}
        with patch.object(self.svc.provider,'complete',respond):
            return asyncio.run(self.svc.development.propose(self.s['id'],DevelopmentRequest(character_id='pass_guard')))
    def test_validate_evidence_and_stable_personality(self):
        c,data=self.proposal();self.svc.development.validate(data,c)
        for edit in [dict(evidence_ids=['fake']),dict(value=0.99),dict(category='personality',key='谨慎',target_id=None,value=0.85)]:
            bad=copy.deepcopy(data);bad['changes'][0].update(edit)
            with self.assertRaises(ValueError):self.svc.development.validate(bad,c)
        self.svc.development.validate({**data,'changes':[]},c)
    def test_review_scoped_stale_and_rollback(self):
        original=copy.deepcopy(self.rt.package());d=self.make()
        self.assertNotIn('development',self.svc.store.session(self.s['id']))
        asyncio.run(self.svc.development.review(d['id'],True))
        self.assertEqual(self.rt.package(),original)
        self.assertEqual(self.svc.store.session(self.s['id'])['development']['pass_guard']['relationships']['protagonist']['trust'],0.6)
        with self.assertRaises(ValueError):asyncio.run(self.svc.development.review(d['id'],True))
        stale=self.make()
        self.svc.provider.configure({**self.svc.provider.config(),'offline':True})
        asyncio.run(self.svc.turn(self.s['id'],Turn(message='继续')))
        with self.assertRaises(ValueError):asyncio.run(self.svc.development.review(stale['id'],True))
        s=self.svc.store.session(self.s['id']);self.rt.close_event(s);self.svc.store.save_session(s)
        restored=self.rt.rollback(s,s['archives'][-1]['id'])
        self.assertFalse(restored.get('development'))
    def test_npc_projection_does_not_inherit_player_state(self):
        s=self.svc.store.session(self.s['id']);s['heard'].append({'text':'玩家私下获得暗号','time':s['time'],'distortion':0})
        ctx=self.rt.context(s,'oasis_merchant','',self.svc.preferences())
        self.assertEqual(ctx['location'],'新月沃土商驿')
        self.assertEqual(ctx['current_anchor']['confirmed_records'],[])
        self.assertEqual(ctx['current_inventory'],[])
        self.assertEqual(ctx['history'],[])
        evidence=self.svc.development.context(s,'oasis_merchant')['evidence']
        self.assertEqual(evidence,[])
    def test_routes_author_guard(self):
        with TestClient(create_app(Path(self.tmp.name)/'web.sqlite3')) as client:
            boot=client.get('/api/bootstrap').json();h={'X-TextileDream-Token':boot['token']}
            s=client.post('/api/sessions',headers=h,json={'title':'路由','mode':'protagonist'}).json()
            url='/api/inner/sessions/'+s['id']+'/development'
            self.assertEqual(client.get(url).status_code,403)
            d=client.post(url,headers=h,json={'character_id':'protagonist'}).json()
            self.assertEqual(d['proposal']['changes'],[])
            self.assertEqual(client.post('/api/inner/development/'+d['id']+'/approve',headers=h).status_code,200)
