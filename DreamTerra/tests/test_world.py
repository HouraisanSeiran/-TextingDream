import io
import json
import platform
import tempfile
import time
from pathlib import Path

import numpy as np
from PIL import Image
from fastapi.testclient import TestClient

from DreamTerra.generation import Parameters, generate
from DreamTerra.service import create, read
from app.web import create_app


def test_same_recipe_density_and_geography():
    started=time.perf_counter()
    world,a=generate(Parameters())
    again,b=generate(Parameters.model_validate_json(Parameters().model_dump_json()))
    assert world==again
    for name in a:np.testing.assert_array_equal(a[name],b[name])
    sparse,c=generate(Parameters(river_density=.5))
    assert len(sparse['rivers'])<len(world['rivers'])
    np.testing.assert_array_equal(a['elevation'],c['elevation'])
    np.testing.assert_array_equal(a['receiver'],c['receiver'])
    assert world['stats']['wetland_cells']>0 and world['stats']['floodplain_cells']>0
    assert sum(t['tier']=='village' for t in world['towns'])>sum(t['tier']=='city' for t in world['towns'])
    rec=a['receiver'].ravel();water=a['water'].ravel();n=world['size_km']
    for river in world['rivers']:
        for u,v in zip(river['cells'],river['cells'][1:]):assert rec[u]==v
        assert river['outlet'] in ('river','lake','ocean','external')
    by_id={t['id']:t for t in world['towns']}
    crossings=0
    for road in world['roads']:
        assert road['cells'][0]==by_id[road['origin']]['cell']
        assert road['cells'][-1]==by_id[road['destination']]['cell']
        for u,v in zip(road['cells'],road['cells'][1:]):
            assert water[u]==water[v]==0
            assert max(abs(u//n-v//n),abs(u%n-v%n))==1
        for crossing in road['crossings']:
            assert crossing['cell'] in road['cells']
            assert crossing['discharge_m3_s']>=world['river_threshold_m3_s']
            crossings+=1
    assert crossings>0
    evidence={'platform':platform.platform(),'processor':platform.processor(),'python':platform.python_version(),
              'world_id':world['id'],'parameters':world['provenance']['parameters'],'stats':world['stats'],
              'sparse_river_segments':len(sparse['rivers']),'crossings':crossings,'three_generations_seconds':time.perf_counter()-started,
              'checks':['identical arrays and world data','density changes channels, not elevation or drainage','wetland entry','downstream chains','road adjacency and crossings']}
    Path('DreamTerra/artifacts/generation.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf8')


def test_persistence_player_travel_and_isolation():
    with tempfile.TemporaryDirectory() as folder:
        app=create_app(Path(folder)/'world.sqlite3');svc=app.state.service
        svc.runtime.library=Path(folder)/'stories';svc.runtime.library.mkdir()
        svc.provider.configure({'offline':True})
        with TestClient(app) as client:
            headers={'X-TextileDream-Token':client.get('/api/bootstrap').json()['token']}
            assert client.get('/api/inner/dreamterra').status_code==403
            bad=client.post('/api/inner/dreamterra',headers=headers,json={'river_density':0})
            assert bad.status_code==422 and not svc.store.all('dreamterra')
            record=create(svc.store,Parameters(size_km=128,settlements=12))
            world,arrays=read(svc.store,record['id'])
            started=client.post('/api/inner/dreamterra/'+record['id']+'/start',headers=headers,json={})
            assert started.status_code==200,started.text
            sid=started.json()['session_id'];url='/api/sessions/'+sid
            before=client.get(url).json();stored=svc.store.session(sid)
            road=next(r for r in world['roads'] if stored['location'] in (r['origin'],r['destination']))
            target=road['destination'] if stored['location']==road['origin'] else road['origin']
            elapsed=before['local_state']['clock']['elapsed_hours']
            move=client.post(url+'/move',headers=headers,json={'location_id':target,'expected_version':stored['state_version']})
            assert move.status_code==200,move.text
            assert move.json()['local_state']['clock']['elapsed_hours']==elapsed+road['hours']
            assert svc.store.session(sid)['location']==target
            assert client.get(url).json()['local_state']['clock']['elapsed_hours']==elapsed+road['hours']
            payload=client.get(url+'/play-map').json()
            assert payload['status']=='ok' and payload['fog']['masked_by']=='server'
            assert 'terrain' not in payload and 'provenance' not in payload
            assert len(payload['places'])<len(world['towns'])
            known={p['id'] for p in payload['places']}
            assert all(r['origin'] in known and r['destination'] in known for r in payload['roads'])
            raw=client.get(payload['basemap']['url']);assert raw.headers['x-play-map']=='fog-masked'
            pixels=np.array(Image.open(io.BytesIO(raw.content)))
            assert np.count_nonzero(np.all(pixels==[33,57,50],axis=2))>pixels.shape[0]*pixels.shape[1]*.5
            restored,restored_arrays=read(svc.store,record['id'])
            assert restored==world
            np.testing.assert_array_equal(arrays['receiver'],restored_arrays['receiver'])
            Path('DreamTerra/artifacts/travel.json').write_text(json.dumps({'origin':stored['location'],'destination':target,
              'distance_km':road['distance_km'],'hours':road['hours'],'clock_before':elapsed,'clock_after':elapsed+road['hours'],
              'persisted':True,'player_places':len(payload['places']),'world_towns':len(world['towns']),'server_masked':True},indent=2),encoding='utf8')
