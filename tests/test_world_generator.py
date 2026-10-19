import asyncio
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.service import Service
from app.storage import Store
from app.web import create_app
from app.contracts import Turn
from app.world_generator import GenerateWorldRequest, world_example

ROOT = Path(__file__).resolve().parents[1]


class WorldGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / 'test.sqlite3'
        self.service = Service(Store(self.db), ROOT)
        self.service.provider.configure({'base_url':'https://api.deepseek.com','model':'deepseek-chat','offline':True,'max_tokens':1200})
        self.rt = self.service.runtime
        self.gen = self.service.world_generator

    def tearDown(self):
        self.temp.cleanup()

    def generate(self, kind, **kwargs):
        return asyncio.run(self.gen.generate(GenerateWorldRequest(kind=kind,title='星河诸城',instruction='生成可探索的城市与社会规则',**kwargs)))

    def test_end_to_end_files_activation_play_and_restart(self):
        self.service.store.put('settings','preferences',{'conversation_mode':'scene'})
        old = self.rt.new_session('旧旅程','protagonist')
        original = (self.rt.files.directory/'总概.md').read_bytes()
        foundation = self.generate('worldview')
        f = self.gen.save(foundation['id'])
        self.assertTrue((self.rt.library/f['folder']/'总概.md').exists())
        overview_file = self.rt.library/f['folder']/'总概.md'
        overview_file.write_text(overview_file.read_text(encoding='utf-8')+'\n所有城市都维护公共渡口。',encoding='utf-8')
        world = self.generate('world',worldview_draft_id=foundation['id'],city_count=3)
        self.assertIn('公共渡口',world['worldview']['overview'])
        saved = self.gen.save(world['id'])
        self.assertEqual(saved, self.gen.save(world['id']))
        self.assertEqual(original,(self.rt.library/'玄陆/总概.md').read_bytes())
        revision = self.rt.activate_package(saved['folder'])
        p = self.rt.package()
        self.assertEqual(revision,p['id'])
        self.assertEqual(len(p['story']['locations']),3)
        self.assertTrue((self.rt.character_directory/(p['characters']['id']+'.json')).exists())
        self.assertNotIn('characters',json.loads((self.rt.files.directory/'story.json').read_text(encoding='utf-8')))
        new = self.rt.new_session('新旅程','protagonist')
        for i in range(3):
            result = asyncio.run(self.service.turn(new['id'],Turn(message='了解当地',action_id='investigate')))
            self.assertNotIn('内部争执',json.dumps(result,ensure_ascii=False))
            new = self.service.store.session(new['id'])
            if i<2:
                self.rt.move(new,f'place_{i+1}')
        self.assertEqual(len(new['archives']),3)
        self.assertEqual(len(self.rt.conversations(new)),3)
        restart = Service(Store(self.db),ROOT)
        self.assertEqual(restart.runtime.files.directory.name,saved['folder'])
        self.assertEqual(restart.runtime.surface(old)['world'],'玄陆：万国灵潮')
        self.assertTrue((self.rt.library/'玄陆/生成记录/旅程'/ (old['id']+'.md')).exists())
        self.rt.activate_package('玄陆')
        self.assertEqual(original,(self.rt.files.directory/'总概.md').read_bytes())

    def test_current_large_worldview_and_invalid_generated_output(self):
        d = self.generate('world')
        self.assertEqual(len(d['worldview']['knowledge']),len(self.rt.package()['story']['knowledge']))
        self.gen.save(d['id'])
        bad = copy.deepcopy(d['data'])
        bad['cities'][0]['coordinates']=[900,50]
        with self.assertRaises(ValueError):
            self.gen.edit(d['id'],bad)
        with self.assertRaises(ValueError):
            self.rt.activate_package('../escape')

    def test_failed_remote_generation_does_not_save_or_activate(self):
        old_revision = self.rt.package()['id']
        self.service.provider.configure({'base_url':'https://api.deepseek.com','model':'deepseek-chat','offline':False,'max_tokens':1200})
        async def invalid(*args,**kwargs):
            return {'cities':[]}, {'prompt_tokens':10}
        with patch.object(self.service.provider,'complete',invalid):
            with self.assertRaises(ValueError):
                self.generate('world')
        self.assertEqual(self.service.store.all('world_generation'),[])
        self.assertEqual(old_revision,self.rt.package()['id'])

    def test_mock_api_budget_scope_and_prompt(self):
        self.service.provider.configure({'base_url':'https://api.deepseek.com','model':'deepseek-chat','offline':False,'max_tokens':1200})
        requests=[]
        async def respond(system,context,**kwargs):
            requests.append((context,kwargs))
            return world_example(2),{'prompt_tokens':50,'completion_tokens':100}
        with patch.object(self.service.provider,'complete',respond):
            d=self.generate('world',city_count=2,output_tokens=3500)
        self.assertEqual(requests[0][1]['scope'],'generator_world')
        self.assertEqual(requests[0][1]['max_tokens'],3500)
        self.assertLessEqual(len(requests[0][0]['knowledge']),6)
        self.assertEqual(d['usage']['calls'],1)

    def test_api_author_guard_and_validation(self):
        with TestClient(create_app(self.db)) as client:
            self.assertEqual(client.get('/api/inner/generators').status_code,403)
            token=client.get('/api/bootstrap').json()['token']
            headers={'X-TextileDream-Token':token}
            result=client.post('/api/inner/generators',headers=headers,json={'kind':'worldview','instruction':'生成一个世界观','title':'测试'})
            self.assertEqual(result.status_code,200,result.text)
            identity=result.json()['id']
            invalid=client.put('/api/inner/generators/'+identity,headers=headers,json={'data':{'title':'坏数据'}})
            self.assertIn(invalid.status_code,(400,422))
            self.assertEqual(client.post('/api/inner/generators/'+identity+'/save',headers=headers).status_code,200)
