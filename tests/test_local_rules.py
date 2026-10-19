import asyncio
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from app import local_rules as local
from app.service import Service
from app.storage import Store
from app.contracts import Turn
from app.web import create_app

ROOT=Path(__file__).resolve().parents[1]


class LocalRulesTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.svc=Service(Store(Path(self.tmp.name)/'t.sqlite3'),ROOT)
        self.svc.provider.configure({'offline':True});self.rt=self.svc.runtime
        p=copy.deepcopy(self.rt.package())
        p['story'].setdefault('mechanics',{})['local']={
            'resources':[{'id':'coin','name':'测试钱','initial':10,'maximum':20},{'id':'food','name':'补给','initial':10,'maximum':20,'per_hour':-1}],
            'schedules':[{'id':'bell','title':'报时','at':10,'every':2,'public':True,'effects':[{'op':'flag','id':'bell','value':True},{'op':'notice','text':'报时声响起','visible':True}]},
                         {'id':'secret','title':'秘密调动','at':9,'effects':[{'op':'notice','text':'秘密ABC','visible':False}]}],
            'routines':[{'character':'pass_guard','start':10,'end':12,'location':'crescent_oasis','activity':'短暂休息'}]}
        action=p['story']['events'][0]['actions'][0]
        action['costs']={'coin':3};action['duration_hours']=2
        action.setdefault('effects',[]).append({'op':'resource','id':'coin','delta':1})
        self.rt.commit_package(p['story'],p['characters'],'测试本地规则');self.s=self.rt.new_session('本地','protagonist')
    def tearDown(self):self.tmp.cleanup()
    def test_cost_time_schedule_rollback_no_extra_calls(self):
        asyncio.run(self.svc.turn(self.s['id'],Turn(message='收拾',action_id='pack')))
        s=self.svc.store.session(self.s['id']);self.assertEqual(s['time'],10)
        self.assertEqual(s['local']['resources'],{'coin':8,'food':8})
        self.assertTrue(s['flags']['bell']);self.assertEqual(s['characters']['pass_guard']['location'],'crescent_oasis')
        projected=self.rt.surface(s)
        self.assertNotIn('秘密ABC',str(projected));self.assertNotIn('秘密调动',str(projected))
        p=self.rt.package(s['revision']);before=len(s['heard'])
        local.advance(s,p['story'],p['characters'],0);self.assertEqual(len(s['heard']),before)
        old=self.rt.rollback(s,s['archives'][-1]['id']);self.assertEqual(old['local']['resources']['coin'],10)
        self.assertEqual(old['time'],8);self.assertFalse(old['flags'].get('bell'))
    def test_insufficient_and_api_failure_do_not_commit(self):
        s=self.svc.store.session(self.s['id']);s['local']['resources']['coin']=1;self.svc.store.save_session(s)
        before=self.svc.store.session(s['id'])
        with self.assertRaises(ValueError):asyncio.run(self.svc.turn(s['id'],Turn(message='拿',action_id='pack')))
        self.assertEqual(before,self.svc.store.session(s['id']))
        s['local']['resources']['coin']=10;self.svc.store.save_session(s);before=self.svc.store.session(s['id'])
        self.svc.provider.configure({'offline':False})
        async def fail(*a,**k):raise ValueError('network')
        with patch.object(self.svc.provider,'complete',fail):
            with self.assertRaises(ValueError):asyncio.run(self.svc.turn(s['id'],Turn(message='拿',action_id='pack')))
        self.assertEqual(before,self.svc.store.session(s['id']))
    def test_thought_and_private_speech(self):
        p=self.rt.package();s=copy.deepcopy(self.s)
        node={'participants':['protagonist','pass_guard','oasis_merchant'],'player_enters':True}
        for cid in node['participants']:s['characters'][cid]['location']=s['location']
        self.assertEqual(local.communicate(s,node,Turn(message='秘密',channel='thought'),20),[])
        self.assertEqual(s['beliefs'],[])
        request=Turn(message='只是我的猜测',channel='speech',listeners=['pass_guard'])
        self.assertEqual(local.communicate(s,node,request,20),['pass_guard'])
        self.assertEqual(s['beliefs'][0]['character'],'pass_guard');self.assertEqual(s['facts'],[])
        local.communicate(s,node,request,20);self.assertEqual(len(s['beliefs']),1)
        with self.assertRaises(ValueError):local.communicate(s,node,Turn(message='说',channel='speech',listeners=['ghost']),20)
    def test_reject_overlap_and_unknown_resource(self):
        p=copy.deepcopy(self.rt.package());p['story']['mechanics']['local']['routines']*=2
        with self.assertRaises(ValueError):self.rt.validate_package(p['story'],p['characters'])
        p=copy.deepcopy(self.rt.package());p['story']['events'][0]['actions'][0]['costs']={'unknown':1}
        with self.assertRaises(ValueError):self.rt.validate_package(p['story'],p['characters'])
    def test_wait_endpoint_no_model_and_author_rules_guard(self):
        with TestClient(create_app(Path(self.tmp.name)/'web.sqlite3')) as c:
            b=c.get('/api/bootstrap').json();headers={'X-TextileDream-Token':b['token']}
            self.assertEqual(c.get('/api/inner/local-rules').status_code,403)
            rules=c.get('/api/inner/local-rules',headers=headers).json()['rules']
            self.assertEqual(c.put('/api/inner/local-rules',headers=headers,json=rules).status_code,200)
            s=c.post('/api/sessions',headers=headers,json={}).json();sid=s['id']
            self.assertEqual(c.post('/api/sessions/'+sid+'/wait',headers=headers,json={'hours':1}).status_code,400)
            after=c.post('/api/sessions/'+sid+'/chat',headers=headers,json={'message':'行装','action_id':'pack'}).json()
            trace_count=len(c.app.state.service.store.all('trace'))
            r=c.post('/api/sessions/'+sid+'/wait',headers=headers,json={'hours':2})
            self.assertEqual(r.status_code,200);self.assertEqual(r.json()['local_state']['clock']['elapsed_hours'],after['local_state']['clock']['elapsed_hours']+2)
            self.assertEqual(len(c.app.state.service.store.all('trace')),trace_count)
