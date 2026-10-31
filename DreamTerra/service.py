"""Persistence, author API and fog projection for the finite map adapter."""
import io
import json
import re
import shutil
import tempfile
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from fastapi import Body
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from .generation import Parameters, generate

PALETTE = np.array([[123,160,155],[143,180,173],[224,216,179],[190,190,145],[159,157,133],
                    [196,185,151],[136,164,127],[224,199,150],[122,157,133],[184,191,146]], dtype=np.uint8)


def directory(store, identifier):
    if not re.fullmatch(r'dt_[0-9a-f]{24}', identifier):
        raise ValueError('DreamTerra 世界编号无效')
    return Path(store.path).resolve().parent / 'dreamterra' / identifier


def read(store, identifier):
    if not store.get('dreamterra', identifier):
        raise ValueError('DreamTerra 世界不存在')
    folder = directory(store, identifier)
    world = json.loads((folder/'world.json').read_text(encoding='utf8'))
    with np.load(folder/'terrain.npz', allow_pickle=False) as source:
        arrays = {name:source[name] for name in source.files}
    return world, arrays


def create(store, params):
    started=time.perf_counter()
    world, arrays=generate(params)
    folder=directory(store,world['id'])
    folder.parent.mkdir(parents=True,exist_ok=True)
    temporary=Path(tempfile.mkdtemp(prefix='generating-',dir=folder.parent))
    try:
        (temporary/'world.json').write_text(json.dumps(world,ensure_ascii=False,allow_nan=False),encoding='utf8')
        np.savez_compressed(temporary/'terrain.npz',**arrays)
        if not folder.exists():
            temporary.rename(folder)
        record={'id':world['id'],'parameters':params.model_dump(),'stats':world['stats'],
                'generator':world['provenance']['generator'],'generation_seconds':round(time.perf_counter()-started,3)}
        store.put('dreamterra',world['id'],record)
        return record
    finally:
        if temporary.exists():shutil.rmtree(temporary)


def image(world,arrays,mask=None,vectors=True):
    elevation=arrays['elevation']
    dz,dx=np.gradient(elevation,1000)
    shade=np.clip((dx*.6+dz*.8)*.7,-.22,.17)
    rgb=np.clip(PALETTE[arrays['biome']].astype(float)*(1+shade[:,:,None]),0,255).astype('uint8')
    result=Image.fromarray(rgb)
    draw=ImageDraw.Draw(result)
    for river in world['rivers'] if vectors else []:
        draw.line([tuple(p) for p in river['points']],fill=(70,120,125),width=1 if river['level']<3 else 2)
    for road in world['roads'] if vectors else []:
        draw.line([tuple(p) for p in road['points']],fill=(129,110,81),width=1)
    if mask is not None:
        rgb=np.array(result);rgb[~mask]=(33,57,50);result=Image.fromarray(rgb)
    stream=io.BytesIO();result.save(stream,format='PNG');return stream.getvalue()


def compile_story(world):
    # Terrain coordinates remain km. The old player canvas receives a display-only
    # linear frame at 111 map-km/unit; travel never uses its geographic distance.
    towns=world['towns'];roads=world['roads']
    connected={v for r in roads for v in (r['origin'],r['destination'])}
    start=next((t for t in towns if t['id'] in connected),None)
    if start is None:raise ValueError('世界中没有可旅行的连接')
    locations=[{'id':t['id'],'name':t['name'],'coordinates':[t['point'][0]/111,-t['point'][1]/111],
                'dreamterra_point':t['point'],'description':f"{t['name']}，人口 {t['population']}。",'neighbors':[], 'scenes':[]} for t in towns]
    by_id={t['id']:t for t in locations}
    routes=[]
    for r in roads:
        for a,b in [(r['origin'],r['destination']),(r['destination'],r['origin'])]:
            by_id[a]['neighbors'].append(b)
            routes.append({'origin':a,'destination':b,'kind':'road','hours':r['hours']})
    identifier=world['id']
    story={'id':identifier,'title':'山川行记 · '+str(world['provenance']['parameters']['seed']),
           'premise':'沿真实山川和道路探索这个世界。','character_package_id':identifier+'_cast',
           'locations':locations,'events':[],'items':[],
           'mechanics':{'dreamterra':{'id':identifier,'generator':world['provenance']['generator']},
                        'adventure':{'version':1,'routes':routes}}}
    characters={'id':identifier+'_cast','title':'旅人','characters':[{'id':'player','name':'旅人','role':'主角',
                 'location_id':start['id'],'state':{},'personality':{}}]}
    return story,characters


def context(store,runtime,session_id):
    session=store.session(session_id)
    story=runtime.package(session['revision'])['story']
    link=story.get('mechanics',{}).get('dreamterra')
    if not link:return None
    world,arrays=read(store,link['id'])
    from app.play_map import visible_places
    places=visible_places(session,story)
    selected={p['id']:p for p in places}
    n=world['size_km'];z,x=np.ogrid[:n,:n];mask=np.zeros((n,n),bool)
    for town in world['towns']:
        if town['id'] in selected:
            radius=14 if selected[town['id']]['state'] in ('current','explored') else 7
            px,pz=town['point'];mask|=(x+.5-px)**2+(z+.5-pz)**2<=radius**2
    visible_roads=[]
    for road in world['roads']:
        if road['origin'] in selected and road['destination'] in selected:
            # Known connections reveal their actual corridor, not the surrounding world.
            for c in road['cells']:
                zz,xx=divmod(c,n);mask[max(0,zz-1):zz+2,max(0,xx-1):xx+2]=True
            visible_roads.append({k:road[k] for k in ('id','origin','destination','kind','hours','distance_km','points','crossings')})
    return session,story,world,arrays,places,mask,visible_roads


def player_projection(ctx,session_id):
    session,story,world,arrays,places,mask,roads=ctx
    current=next((p for p in places if p['state']=='current'),None)
    n=world['size_km']/111
    return {'status':'ok','session':{'id':session_id,'revision':session['revision']},
            'source':{'map':'dreamterra','world':story['title'],'note':'已知山川 · 服务器遮罩'},
            'projection':{'scheme':'finite_planar','note':'有限米制世界；显示单位仅作线性定位，旅行按原始公里路程计算'},
            'player':({'location_id':current['id'],'name':current['name'],'lon':current['lon'],'lat':current['lat']} if current else None),
            'places':places,'roads':roads,'fog':{'masked_by':'server','reveal_radius_km':14,'known_radius_km':7},
            'basemap':{'available':True,'url':f'/api/sessions/{session_id}/play-map/basemap.png',
                       'bbox':[0,n,-n,0],'clipped_at_dateline':False,'note':'只含已探索地点及已知道路走廊'},'notes':[]}


def install(app,service,root):
    app.mount('/dreamterra',StaticFiles(directory=Path(__file__).parent/'static'),name='dreamterra')

    @app.get('/api/inner/dreamterra')
    def listing():return service.store.all('dreamterra')

    @app.post('/api/inner/dreamterra')
    def new(params:Parameters):return create(service.store,params)

    @app.get('/api/inner/dreamterra/{identifier}')
    def detail(identifier:str):
        world,arrays=read(service.store,identifier)
        # Quantized heights are a display copy; calculations retain float32 originals.
        return {**world,'terrain':{'elevation':np.rint(arrays['elevation']).astype(int).ravel().tolist(),
                                   'biome':arrays['biome'].ravel().tolist()}}

    @app.get('/api/inner/dreamterra/{identifier}/terrain.png')
    def terrain(identifier:str):
        world,arrays=read(service.store,identifier)
        return Response(image(world,arrays,vectors=False),media_type='image/png')

    @app.post('/api/inner/dreamterra/{identifier}/start')
    def start(identifier:str, request:dict=Body(default={})): 
        world,_=read(service.store,identifier)
        story,characters=compile_story(world)
        service.runtime.commit_package(story,characters,'DreamTerra')
        session=service.runtime.new_session('山川旅程','protagonist')
        return {'session_id':session['id']}
