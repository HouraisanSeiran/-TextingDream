import copy
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app import civ_exploration, native_starts
from app.civ_atlas_snapshot import World
from app.web import create_app


def fixture():
    world = World(cells=6, lon=[0, .1, .2, .3, .4, 1], lat=[0]*6,
                  elevation=[100]*6, water=[0]*6)
    civ = {'settlements': [{'id':i, 'cell':c, 'name':'城镇%d'%i, 'founded':0, 'port':i==0}
                           for i,c in enumerate([0,2,4,5])],
           'routes':[{'kind':'road','cells':[0,1,2,3,4],'built':10},
                     {'kind':'sea','cells':[4,5],'built':200}]}
    doc = {'start_cell':0,'city_id':'settlement:0','source_sha256':'a'*64,
           'import_id':'sn_aaaaaaaaaaaa','base_year':100}
    story = {'id':'exploration_test','title':'探索测试','premise':'沿路旅行',
             'character_package_id':'exploration_cast','locations':[],'events':[],'items':[],
             'mechanics':{'map':{'kind':'civ_atlas','import_id':doc['import_id']}}}
    characters={'id':'exploration_cast','title':'角色','characters':[
        {'id':'player','name':'我','role':'主角','location_id':'city_0','state':{},'personality':{}}]}
    return world,civ,doc,story,characters


class CivExplorationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.app=create_app(Path(self.tmp.name)/'test.sqlite3')
        self.svc=self.app.state.service
        self.svc.provider.configure({'offline':True})
        self.client=TestClient(self.app)
        self.addCleanup(self.client.close)
        self.headers={'X-TextileDream-Token':self.client.get('/api/bootstrap').json()['token']}

    def build(self, data=None):
        world,civ,doc,story,characters=data or fixture()
        return civ_exploration.compile_region(story,characters,civ,world,doc,
                                              native_starts.settlements_at(civ,doc['base_year']))

    def test_deterministic_layout_and_real_road_chain(self):
        story,chars=self.build()
        self.assertEqual((story,chars),self.build())
        cfg=story['mechanics']['exploration']
        self.assertEqual(len(cfg['towns']),3)  # future sea route does not connect the island
        roads=[r for r in cfg['roads'] if r['source']=='civ_routes']
        self.assertEqual(len(roads),2)
        self.assertEqual(roads[0]['points'],[[0,0],[.1,0],[.2,0]])
        self.assertNotIn('city_2',next(p for p in story['locations'] if p['id']=='city_0')['neighbors'])
        self.assertEqual(cfg['towns'][0]['nodes'][-1]['kind'],'dock')

    def test_future_abandoned_and_era_routes(self):
        world,civ,doc,story,chars=fixture()
        civ['routes'][0]['abandoned']=50
        self.assertEqual(civ_exploration.road_graph(civ,world,100),{})
        civ['eras']=[{'until':60,'routes':[{'kind':'trail','cells':[0,1,2],'built':0}]}]
        self.assertIn(1,civ_exploration.road_graph(civ,world,40)[0])
        self.assertEqual(civ_exploration.road_graph(civ,world,100),{})

    def test_invalid_cell_rejected(self):
        data=fixture();data[1]['routes'][0]['cells'].append(999)
        with self.assertRaisesRegex(ValueError,'越界'):
            self.build(data)

    def test_streets_travel_persist_time_and_reject_teleport(self):
        story,chars=self.build()
        self.svc.runtime.commit_package(story,chars,'test')
        session=self.svc.runtime.new_session('test','protagonist')
        url='/api/sessions/'+session['id']
        start=self.client.get(url).json()
        state=start['exploration']
        self.assertNotIn('city_2',str(state))
        clock=start['local_state']['clock']['elapsed_hours']
        move=lambda dest,version:self.client.post(url+'/move',headers=self.headers,
            json={'location_id':dest,'expected_version':version})
        bad=move('city_2',state['state_version'])
        self.assertEqual(bad.status_code,400)
        result=move('city_0_market',state['state_version'])
        self.assertEqual(result.status_code,200,result.text)
        arrived=result.json()
        self.assertEqual(arrived['exploration']['location_id'],'city_0_market')
        self.assertEqual(arrived['local_state']['clock']['elapsed_hours'],clock+1)
        self.assertEqual(move('city_0',state['state_version']).status_code,400)
        gate=move('city_0',arrived['exploration']['state_version']).json()
        destination=next(d for d in gate['exploration']['destinations'] if d['id']=='city_1')
        other=move('city_1',gate['exploration']['state_version']).json()
        self.assertEqual(other['exploration']['town']['id'],'city_1')
        self.assertEqual(other['local_state']['clock']['elapsed_hours'],clock+2+destination['hours'])
        self.assertEqual(self.client.get(url).json()['exploration']['location_id'],'city_1')
        stored=self.svc.store.session(session['id'])
        self.assertEqual(stored['characters']['player']['location'],'city_1')
        self.assertIn('city_1',stored['explored'])

    def test_long_trip_split_at_actual_cells(self):
        data=fixture();world,civ,doc,story,chars=data
        world.lon=[0,5,10,15,20,25]
        civ['settlements']=[civ['settlements'][0],civ['settlements'][2]]
        generated,_=self.build(data)
        roads=[r for r in generated['mechanics']['exploration']['roads'] if r['source']=='civ_routes']
        self.assertGreater(len(roads),1)
        self.assertTrue(all(0<r['hours']<=168 for r in roads))
        for road in roads:
            self.assertTrue(all(p[0] in world.lon for p in road['points']))


if __name__=='__main__':
    unittest.main()
