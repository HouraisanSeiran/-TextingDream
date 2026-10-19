import asyncio
import copy
import tempfile
import unittest
from pathlib import Path
from app.service import Service
from app.storage import Store
from app.world_generator import GenerateWorldRequest
from app.atlas import validate_atlas, project_atlas
from app.knowledge import PackageFiles

ROOT=Path(__file__).resolve().parents[1]


class AtlasTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.svc=Service(Store(Path(self.tmp.name)/'t.sqlite3'),ROOT)
        self.svc.provider.configure({'offline':True})
        self.rt=self.svc.runtime
    def tearDown(self):self.tmp.cleanup()
    def generate(self,kind):
        return asyncio.run(self.svc.world_generator.generate(GenerateWorldRequest(kind=kind,title='地图测试',instruction='补充水源、商路、文化与聚落',city_count=2)))
    def test_complete_save_reload_and_playable_map(self):
        d=self.generate('complete');g=self.svc.world_generator
        self.assertTrue(g.preview_atlas(d['id'])['features'])
        saved=g.save(d['id']);self.rt.activate_package(saved['folder'])
        story=self.rt.package()['story'];self.assertEqual(len(story['locations']),2)
        self.assertTrue((self.rt.files.directory/'atlas.json').exists())
        self.assertEqual(story['atlas'],self.rt.files.read()['atlas'])
        s=self.rt.new_session('新图','protagonist')
        self.assertTrue(self.rt.surface(s)['atlas']['features'])
    def test_expansion_preserves_source_and_actor_event_identity(self):
        before=copy.deepcopy(self.rt.package());d=self.generate('expand');g=self.svc.world_generator
        story,chars=g.assembled(d)
        self.assertEqual(story['events'],before['story']['events'])
        self.assertEqual(story['locations'],before['story']['locations'])
        self.assertEqual(chars,before['characters'])
        saved=g.save(d['id']);self.assertEqual(before,self.rt.package())
        expanded=PackageFiles(self.rt.library/saved['folder']).read()
        self.assertNotEqual(expanded['id'],before['story']['id'])
        self.assertEqual(expanded['events'],before['story']['events'])
        self.assertGreater(len(expanded['knowledge']),len(before['story']['knowledge']))
        bad=copy.deepcopy(d['data']);bad['knowledge'][0]['id']=before['story']['knowledge'][0]['id']
        with self.assertRaises(ValueError):g.validate(d,bad)
    def test_secret_location_and_knowledge_filters(self):
        story=copy.deepcopy(self.rt.package()['story'])
        story['knowledge'].extend([{'id':'testsecret','title':'秘密','keywords':['秘密'],'visibility':'author','content':'SECRET_VALUE'},
            {'id':'locked','title':'锁定','keywords':['锁定'],'visibility':'public','reveal_flag':'unlock','content':'LOCKED_VALUE'}])
        base={'id':'test_marker','name':'内部地点','layer':'markers','geometry':'point','coordinates':[[0,0]],'location_ids':[], 'knowledge_ids':['testsecret'],'visibility':'public'}
        story['atlas']={'features':[base]}
        with self.assertRaises(ValueError):validate_atlas(story)
        base['visibility']='author'
        story['atlas']['features'].append({**base,'id':'public_marker','visibility':'public','knowledge_ids':['locked']})
        s=self.rt.new_session('玩家','protagonist')
        view=project_atlas(story,s)
        self.assertNotIn('SECRET_VALUE',str(view));self.assertNotIn('LOCKED_VALUE',str(view));self.assertNotIn('testsecret',str(view))
        s['flags']['unlock']=True
        self.assertIn('LOCKED_VALUE',str(project_atlas(story,s)))
        story['atlas']['features'][1]['location_ids']=['south_lantern_port']
        self.assertEqual(project_atlas(story,s)['features'],[])
    def test_invalid_geometry_and_map_not_in_ai_context(self):
        story=copy.deepcopy(self.rt.package()['story'])
        story['atlas']={'features':[{'id':'bad','name':'bad','layer':'routes','geometry':'line','coordinates':[[0,0]]}]}
        with self.assertRaises(ValueError):validate_atlas(story)
        story['atlas']['features'][0]['coordinates']=[[0,0],[float('nan'),2]]
        with self.assertRaises(ValueError):validate_atlas(story)
        s=self.rt.new_session('范围','protagonist')
        self.assertNotIn('atlas',self.rt.context(s,'player','你好',self.svc.preferences()))

    def test_terrain_boundaries_compile_and_roundtrip(self):
        from app.world_generator import world_example,worldview_example,compile_package
        w=world_example(2)
        w['cities'][0].update(terrain_kind='wetland',terrain_boundary=[[34,24],[36,24],[35,26]])
        story,chars=compile_package(worldview_example('地形'),w,'terrain_test')
        self.rt.validate_package(story,chars)
        terrain=next(f for f in story['atlas']['features'] if f['id']=='terrain_place_0')
        self.assertEqual(terrain['geometry'],'polygon');self.assertEqual(terrain['terrain_kind'],'wetland')
        self.assertTrue(terrain['knowledge_ids'])
        w['cities'][0]['terrain_boundary']=[[34,24],[36,24]]
        with self.assertRaises(ValueError):compile_package(worldview_example('地形'),w,'bad')
