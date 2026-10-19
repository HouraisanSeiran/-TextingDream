import asyncio
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.contracts import DraftRequest, Turn
from app.service import Service
from app.storage import Store
from app.web import create_app

ROOT = Path(__file__).resolve().parents[1]


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'test.sqlite3'
        self.service = Service(Store(self.path), ROOT)
        self.service.provider.configure({'base_url': 'https://api.deepseek.com', 'model':'deepseek-chat', 'offline':True, 'max_tokens':1200})
        self.rt = self.service.runtime
        self.s = self.rt.new_session('测试', 'protagonist')

    def tearDown(self):
        self.tmp.cleanup()

    def turn(self, action=None, message='继续'):
        asyncio.run(self.service.turn(self.s['id'], Turn(message=message, action_id=action)))
        self.s = self.service.store.session(self.s['id'])

    def test_full_chain_persistence_information_rollback(self):
        self.turn('pack')
        self.assertEqual(self.s['inventory'], ['translation_machine'])
        self.rt.move(self.s, 'western_pass')
        self.turn('translate')
        first_roll = copy.deepcopy(self.s['checks'])
        archive = self.s['archives'][-1]['id']
        self.s = self.rt.rollback(self.s, archive)
        self.assertEqual(self.s['location'], 'western_pass')
        self.assertEqual(self.s['inventory'], ['translation_machine'])
        self.assertEqual(self.s['checks'], [])
        self.turn('translate')
        self.assertEqual(first_roll, self.s['checks'])
        self.rt.move(self.s, 'crescent_oasis')
        self.turn('listen')
        self.assertIn('3天', self.s['facts'][-1]['text'])
        self.assertIn('9天', self.s['heard'][-1]['text'])
        self.assertEqual(self.s['heard'][-1]['source_fact'], self.s['facts'][-1]['id'])
        self.assertIsNotNone(self.s['decisions'][-1]['source_belief'])
        surface = json.dumps(self.rt.surface(self.s), ensure_ascii=False)
        self.assertNotIn('3天', surface)
        context = json.dumps(self.rt.context(self.s, 'player', '道路', self.service.preferences()), ensure_ascii=False)
        self.assertNotIn('3天', context)
        # Creating a fresh service loads the identical persisted state.
        restarted = Service(Store(self.path), ROOT)
        self.assertEqual(restarted.store.session(self.s['id']), self.s)
        self.rt.move(self.s, 'western_port')
        self.turn('ask')
        self.assertEqual(len(self.s['archives']), 4)

    def test_illegal_actions_and_provider_failure_are_atomic(self):
        before = self.service.store.session(self.s['id'])
        with self.assertRaises(ValueError):
            self.rt.move(self.s, 'western_port')
        with self.assertRaises(ValueError):
            self.turn('invented-action')
        self.assertEqual(before, self.service.store.session(self.s['id']))
        self.service.provider.configure({'base_url':'https://api.deepseek.com','model':'deepseek-chat','offline':False,'max_tokens':1200})
        async def fail(*args, **kwargs):
            raise ValueError('API failure')
        with patch.object(self.service.provider, 'complete', fail):
            with self.assertRaises(ValueError):
                self.turn('pack')
        self.assertEqual(before, self.service.store.session(self.s['id']))

    def test_draft_approval_version_pin_and_default_deny(self):
        d = asyncio.run(self.service.generate(DraftRequest(kind='item', instruction='测试物品')))
        revision = self.rt.approve(d)
        self.assertNotEqual(revision, self.s['revision'])
        new = self.rt.new_session('新版', 'protagonist')
        self.assertEqual(self.rt.project_elements(new, 'player'), [])
        self.assertEqual(len(self.rt.package(new['revision'])['story']['items']), 2)
        self.assertEqual(len(self.rt.package(self.s['revision'])['story']['items']), 1)
        with self.assertRaises(ValueError):
            self.rt.approve(d)

    def test_observer_cannot_take_items(self):
        self.s = self.rt.new_session('旁观', 'observer')
        with self.assertRaises(ValueError):
            self.turn('pack')
        self.turn(message='描写眼前的道路')
        self.assertEqual(self.s['inventory'], [])

    def test_api_projection_auth_and_config(self):
        with TestClient(create_app(self.path)) as client:
            b = client.get('/api/bootstrap').json()
            headers = {'X-TextileDream-Token': b['token']}
            self.assertEqual(client.get('/api/inner/package').status_code,403)
            self.assertEqual(client.post('/api/sessions', json={}).status_code,403)
            self.assertEqual(client.post('/api/sessions', json={}, headers={**headers, 'Origin':'https://evil.example'}).status_code,403)
            s = client.get('/api/sessions/'+self.s['id']).json()
            for key in ('facts','beliefs','checks','characters','seed','hidden_goal'):
                self.assertNotIn(key,s)
            self.assertEqual(client.get('/').status_code,200)
            self.assertEqual(client.get('/maps/world.svg').status_code,200)
            c=client.put('/api/settings/api',json={'api_key':'secret-test-key','offline':True},headers=headers)
            self.assertEqual(c.status_code,200)
            self.assertNotIn('secret-test-key',c.text)
            self.assertNotIn('secret-test-key',self.path.read_bytes().decode('utf-8',errors='ignore'))

    def test_provider_request_and_structured_draft(self):
        import httpx
        self.service.provider.configure({'base_url':'https://api.deepseek.com','model':'deepseek-chat','api_key':'test-only','offline':False,'max_tokens':1200})
        example = self.service.example('item', self.rt.package())
        requests = []
        def respond(request):
            data = json.loads(request.content)
            requests.append(data)
            return httpx.Response(200, json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(example)}}], 'usage':{'prompt_tokens':30,'completion_tokens':40}})
        original = httpx.AsyncClient
        with patch('app.provider.httpx.AsyncClient', side_effect=lambda **kw: original(transport=httpx.MockTransport(respond), **kw)):
            d = asyncio.run(self.service.generate(DraftRequest(kind='item', instruction='做一个匣子')))
        self.assertEqual(d['element']['kind'],'item')
        self.assertEqual(requests[0]['response_format'],{'type':'json_object'})
        self.assertEqual(d['usage']['calls'],1)

    def test_empty_projection_and_character_memory_isolation(self):
        p=copy.deepcopy(self.rt.package())
        p['story']['elements']=[{'kind':'fact','data':{'title':'可见外观','secret':'禁止泄露'},'public_fields':['title'],'location_id':self.s['location'],'known_by':['player'],'reveal_flag':'unlocked'}]
        self.rt.commit_package(p['story'],p['characters'],'测试投影')
        s=self.rt.new_session('投影','protagonist')
        self.assertEqual(self.rt.project_elements(s,'player'),[])
        s['flags']['unlocked']=True
        self.assertEqual(self.rt.project_elements(s,'player'),[{'title':'可见外观'}])
        s['active']['turns']=[{'input':'秘密','reply':'禁止泄露'}]
        context=self.rt.context(s,'pass_guard','',self.service.preferences())
        self.assertNotIn('禁止泄露',json.dumps(context,ensure_ascii=False))

    def test_major_scene_continuation_and_boundary(self):
        self.service.store.put('settings','preferences',{'conversation_mode':'scene'})
        self.turn('pack'); first=self.s['conversation']['id']
        self.rt.move(self.s,'western_pass'); self.assertNotEqual(first,self.s['conversation']['id'])
        self.turn('translate');self.rt.move(self.s,'crescent_oasis');self.turn('listen')
        self.rt.move(self.s,'western_port');self.turn('ask');self.rt.move(self.s,'south_lantern_port')
        conversation=self.s['conversation']['id'];self.turn('read_letter')
        self.assertEqual(self.s['active']['node'],'south_oath')
        self.assertEqual(conversation,self.s['conversation']['id'])
        self.turn('record_oath')
        self.assertEqual(len(self.rt.conversations(self.s)),5)
        self.assertEqual(len(self.rt.conversations(self.s)[-1]['turns']),2)
        self.assertEqual(len(self.s['archives']),6)

    def test_stable_prefix_and_trace_redaction(self):
        from app.prompts import surface_prefix, stable_json
        import httpx
        p=self.rt.package(); prefix=surface_prefix(p,'通用规则')
        q=copy.deepcopy(p);q['characters']['characters'].reverse()
        q['characters']['characters'][0]['state']={'疲劳':.9}
        self.assertEqual(prefix,surface_prefix(q,'通用规则'))
        self.assertEqual(stable_json({'b':2,'a':1}),stable_json({'a':1,'b':2}))
        self.service.provider.configure({'base_url':'https://api.deepseek.com','model':'deepseek-chat','api_key':'private-key-test','offline':False,'max_tokens':1200})
        original=httpx.AsyncClient
        def response(request):
            return httpx.Response(401,text='invalid private-key-test')
        with patch('app.provider.httpx.AsyncClient',side_effect=lambda **kw: original(transport=httpx.MockTransport(response),**kw)):
            with self.assertRaises(ValueError):asyncio.run(self.service.provider.complete(prefix,{'current_time':30},scope='surface'))
        trace=self.service.store.all('trace')[-1]
        self.assertEqual(trace['http_status'],401)
        self.assertEqual(trace['status'],'error')
        self.assertNotIn('private-key-test',json.dumps(trace))
        self.assertEqual(trace['request']['messages'][0]['content'],prefix)
        self.assertEqual(trace['request']['messages'][1]['content'],'{"current_time":30}')


if __name__ == '__main__':
    unittest.main()
