import copy
import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from app import attributes
from app.geography import Environment, estimate, solar, local_environment
from app.service import Service
from app.storage import Store
from app.recall import Recall
from app.atlas import project_atlas
from app.contracts import Turn

ROOT=Path(__file__).resolve().parents[1]


class WorldSystemsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=Store(Path(self.tmp.name)/'test.sqlite3')
        self.svc=Service(self.store,ROOT);self.rt=self.svc.runtime
    def tearDown(self):self.tmp.cleanup()

    def test_six_axes_required_and_legacy_rename(self):
        p=copy.deepcopy(self.rt.package())
        self.assertEqual(p['story']['mechanics']['attributes']['axes'][0]['name'],'天赋')
        self.assertEqual(attributes.values({'灵力亲合度':.8,'理解':.6},legacy=True)['talent'],80)
        for raw in ({'strength':80},{**dict.fromkeys(attributes.AXES,50),'social':True},
                    {**dict.fromkeys(attributes.AXES,50),'wisdom':float('nan')}):
            with self.assertRaises(ValueError):attributes.values(raw)
        del p['characters']['characters'][0]['attributes']['talent']
        with self.assertRaises(ValueError):self.rt.commit_package(p['story'],p['characters'],'bad')

    def test_vector_gate_namespace_and_expression(self):
        spec=attributes.specification();vals=dict.fromkeys(attributes.AXES,20)
        low=self.rt.attribute_vectors.search(spec,vals,'交谈说服',6)
        self.assertTrue(all(x['band']=='low' for x in low))
        vals['social']=90;high=self.rt.attribute_vectors.search(spec,vals,'交谈说服',1)
        self.assertEqual(high[0]['attribute'],'social');self.assertEqual(high[0]['band'],'high')
        edited=copy.deepcopy(spec);edited['axes'][4]['keywords']['high']=['测试新关键词']
        self.assertEqual(self.rt.attribute_vectors.search(edited,vals,'社交说服',1)[0]['keywords'],['测试新关键词'])
        self.assertNotIn('测试新关键词',str(self.rt.attribute_vectors.search(spec,vals,'社交说服',1)))
        self.assertNotEqual(attributes.performance({'attributes':vals})['social_actions'],
                            attributes.performance({'attributes':dict.fromkeys(attributes.AXES,20)})['social_actions'])

    def test_health_effect_and_context_rules(self):
        s=self.rt.new_session('属性','protagonist')
        before=self.rt.surface(s)['abilities']['health']
        self.rt.effects(s,[{'op':'health','delta':-20}],'trap')
        self.assertEqual(self.rt.surface(s)['abilities']['health']['current'],before['current']-20)
        self.rt.effects(s,[{'op':'health','delta':1000}],'heal')
        self.assertEqual(self.rt.surface(s)['abilities']['health']['current'],before['maximum'])
        ctx=self.rt.context(s,'player','踩到陷阱如何应变',self.svc.preferences())
        self.assertTrue(ctx['player_abilities']['keywords'])
        npc=self.rt.context(s,'pass_guard','陷阱',self.svc.preferences())
        self.assertNotIn('player_abilities',npc)

    def test_original_evidence_beats_failed_recollections(self):
        records=[{'source_id':'0','input':'我给西行取了暗号：苇灯四七。没有说出口。','reply':'我把它记在心里。'},
                 {'source_id':'1','input':'昨晚的麦饼偏硬，豆汤太淡。这只是回忆。','reply':'我记下这两句。'}]
        for i in range(2,12):records.append({'source_id':str(i),'input':'出发前的暗号是什么？麦饼豆汤如何？','reply':'记不清了。'})
        recall=Recall(self.store)
        for query,expected in [('出发前给西行取的暗号是什么？请自然写两三段，约180—300字。','0'),
                               ('最初对麦饼和豆汤各作了什么评价？只引用我原来的说法。','1')]:
            hits=recall.search('s',query,records)
            self.assertEqual(hits[0]['source_id'],expected)
        self.assertEqual(recall.search('s','修理马车轮毂',records),[])
        recall.search('s','暗号',records[:1])
        with self.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM recall_vectors WHERE session=?',('s',)).fetchone()[0],1)

    def test_environment_population_and_river_constraints(self):
        low=Environment(elevation_m=100).model_dump();high={**low,'elevation_m':3500}
        self.assertGreater(estimate(low)['population_capacity'],estimate(high)['population_capacity'])
        desert={**low,'precipitation_mm':10,'freshwater':0,'irrigation':0,'temperature_c':35}
        self.assertGreater(estimate(high)['population_capacity'],estimate(desert)['population_capacity'])
        civilization={**low,'irrigation':1,'transport':1,'governance':1}
        self.assertEqual(estimate(low)['fertile_soil_km2'],estimate(civilization)['fertile_soil_km2'])
        with self.assertRaises(ValueError):Environment(basin='河',river_path=[(0,0),(1,1)],river_elevations_m=[100,200])
        with self.assertRaises(ValueError):Environment(elevation_m=float('nan'))

    def test_solar_seasons_longitude_and_poles(self):
        spring=solar(0,0,1,{'start_day_of_year':80})
        self.assertAlmostEqual(spring['daylight_hours'],12,delta=.3)
        self.assertEqual(solar(90,0,1,{'start_day_of_year':172})['polar'],'polar_day')
        self.assertEqual(solar(90,0,1,{'start_day_of_year':355})['polar'],'polar_night')
        west=solar(35,0,1,{'start_day_of_year':172});east=solar(35,30,1,{'start_day_of_year':172})
        def hour(s):h,m=map(int,s['sunrise']['time'].split(':'));return h+m/60
        self.assertAlmostEqual(hour(west)-hour(east),2,delta=.02)

    def test_unsurveyed_deposits_never_reach_player(self):
        s=self.rt.new_session('隐矿','protagonist');p=copy.deepcopy(self.rt.package())
        e=Environment(deposits=[{'kind':'rare_metals','abundance':.8,'surveyed':False}]).model_dump(mode='json')
        p['story']['locations'][0]['environment']=e
        p['story']['atlas']['features']=[{'id':'secret_ore','name':'矿点','layer':'resources',
            'coordinates':[[108,34]],'environment':e}]
        self.assertEqual(project_atlas(p['story'],s)['features'],[])
        self.assertNotIn('rare_metals',str(local_environment(p['story'],s)))
        self.assertIn('rare_metals',str(project_atlas(p['story'])))

    def test_pipeline_stages_invalidation_and_playable_save(self):
        from app.world_pipeline import WorldPipeline,PipelineRequest,StageEdit
        self.svc.provider.configure({'offline':True});pipeline=WorldPipeline(self.svc)
        p=pipeline.start(PipelineRequest(title='阶段测试',instruction='先自然资源后文明',regions=2))
        for i in range(4):
            p=asyncio.run(pipeline.advance(p['id']))
            self.assertEqual(len(p['stages']),i+1)
        data=copy.deepcopy(p['stages'][1]['data']);data['regions'][0]['environment']['elevation_m']=550
        p=pipeline.edit(p['id'],StageEdit(index=1,data=data));self.assertEqual(len(p['stages']),2)
        p=asyncio.run(pipeline.advance(p['id']));p=asyncio.run(pipeline.advance(p['id']))
        self.assertEqual(p['stages'][3]['data']['cities'][0]['environment']['elevation_m'],550)
        atlas=pipeline.atlas(p);self.assertIn('fertile_soil',{f['layer'] for f in atlas['features']})
        saved=pipeline.save(p['id']);self.rt.activate_package(saved['folder'])
        s=self.rt.new_session('可玩','protagonist');self.assertTrue(self.rt.surface(s)['actions'])
        self.assertTrue((self.rt.library/saved['folder']/'生成阶段.json').exists())
        with self.assertRaises(ValueError):pipeline.edit(p['id'],StageEdit(index=1,data=data))

if __name__=='__main__':unittest.main()
