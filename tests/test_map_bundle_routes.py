"""Real create_app guard and isolated synthetic frozen product endpoints."""
import pytest
from fastapi.testclient import TestClient

from app import map_bundle as mb
from app.web import create_app
from tests.test_map_bundle import registered

BASE='/api/inner/map-bundles'


@pytest.fixture
def client(registered,tmp_path):
    root,record=registered
    app=create_app(tmp_path/'test.sqlite')
    registry=mb.BundleRegistry(root)
    # install captured the state registry; replace its data source, not auth/routes.
    app.state.map_bundles.get=registry.get
    app.state.map_bundles.list=registry.list
    c=TestClient(app)
    assert c.get(BASE).status_code==403
    c.headers['x-textiledream-token']=c.get('/api/bootstrap').json()['token']
    return c,root,record


def test_routes_shapes_and_preview_token(client):
    c,root,record=client;path=BASE+'/'+record['id']
    assert c.get(BASE).json()['bundles'][0]['id']==record['id']
    detail=c.get(path);assert detail.status_code==200,detail.text
    assert set(detail.json()['groups'])==set(mb.GROUPS)
    image=c.get(path+'/preview/atlas');assert image.status_code==200 and image.content.startswith(b'\x89PNG')
    assert 'no-store' in image.headers['cache-control']
    assert 'blob:' in image.headers['content-security-policy']
    point=c.post(path+'/point',json=dict(x_m=-20000.,z_m=-20000.,month=7))
    assert point.status_code==200,point.text
    assert point.json()['groups']['climate']['values']['monthly_temperature_c']==6.
    assert point.json()['groups']['environment']['values']['year_end_ice_swe_mm'] is None
    query=c.post(path+'/query',json=dict(fields=['climate.monthly_temperature_c'],window=[0,0,1,1],months=[7,1]))
    assert query.status_code==200 and query.json()['arrays']['climate.monthly_temperature_c']==[[[6.]],[[0.]]]
    lakes=c.get(path+'/vectors/lakes?limit=1').json()
    assert lakes['status']=='potential/unvalidated' and lakes['items'][0]['permanent'] is False
    c.headers.pop('x-textiledream-token')
    assert c.get(path+'/preview/atlas').status_code==403


@pytest.mark.parametrize('body',[dict(x_m=0,z_m=0,month=0),dict(x_m=0,z_m=0,month=13),
    dict(x_m=True,z_m=0,month=1),dict(x_m=0,z_m=0,month='7'),dict(x_m=0,z_m=0,path='world')])
def test_point_strict_validation(client,body):
    c,_,r=client
    assert c.post(BASE+'/'+r['id']+'/point',json=body).status_code==422


def test_bounds_missing_paths_fields_and_origin(client):
    c,root,r=client;p=BASE+'/'+r['id']
    assert c.post(p+'/point',json=dict(x_m=1e9,z_m=0,month=1)).status_code==422
    assert c.get(BASE+'/unknown').status_code==404
    assert c.get(p+'/preview/manifest.json').status_code==404
    assert c.get(p+'/vectors/rivers?limit=501').status_code==422
    assert c.post(p+'/query',json=dict(fields=['status'],window=[0,0,1,1])).status_code==422
    assert c.post(p+'/query',json=dict(fields=['terrain.status'],window=[0,0,9,9])).status_code==422
    assert c.get(p,headers={'origin':'http://evil.test'}).status_code==403
    assert c.get('http://evil.test'+p).status_code==403
    assert c.get('/api/bootstrap').status_code==200  # old entry unchanged
    (root/'ocean/routes.json').unlink()
    assert c.get(p).status_code==404
