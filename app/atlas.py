"""Layered atlas data and visibility projection, independent of rendering."""
import math
from typing import Literal
from pydantic import Field, model_validator
from .contracts import Strict
from .geography import Environment, estimate

TerrainKind = Literal['unspecified', 'mountain', 'plateau', 'hill', 'plain', 'desert', 'forest', 'wetland']


class MapFeature(Strict):
    id: str = Field(pattern=r'^[A-Za-z0-9_-]+$', max_length=100)
    name: str = Field(min_length=1, max_length=100)
    layer: Literal['terrain', 'water', 'states', 'cultures', 'routes', 'markers', 'elevation', 'resources', 'fertile_soil', 'farmland', 'population']
    geometry: Literal['point', 'line', 'polygon'] = 'point'
    coordinates: list[tuple[float, float]] = Field(min_length=1, max_length=200)
    description: str = Field(default='', max_length=1600)
    knowledge_ids: list[str] = Field(default_factory=list, max_length=20)
    location_ids: list[str] = Field(default_factory=list, max_length=30)
    visibility: Literal['public', 'author'] = 'public'
    reveal_flag: str | None = None
    terrain_kind: TerrainKind = 'unspecified'
    environment: Environment | None = None

    @model_validator(mode='after')
    def shape(self):
        minimum = {'point': 1, 'line': 2, 'polygon': 3}[self.geometry]
        if len(self.coordinates) < minimum or (self.geometry == 'point' and len(self.coordinates) != 1):
            raise ValueError('地图图形的坐标数量不正确')
        if any(not math.isfinite(x) or not math.isfinite(y) or not -180 <= x <= 180 or not -90 <= y <= 90 for x,y in self.coordinates):
            raise ValueError('地图坐标必须是有限的经纬示意坐标')
        return self


class Atlas(Strict):
    version: Literal[1] = 1
    title: str = Field(default='世界图册', max_length=100)
    note: str = Field(default='架空地理工作稿；底图仅为位置参考，范围不代表精确疆界，比例不用于计算行程。', max_length=800)
    features: list[MapFeature] = Field(default_factory=list, max_length=500)


def validate_atlas(story):
    atlas = Atlas.model_validate(story.get('atlas', {})).model_dump(mode='json')
    ids = [f['id'] for f in atlas['features']]
    if len(ids) != len(set(ids)):
        raise ValueError('地图标记 ID 重复')
    places = {p['id'] for p in story['locations']}
    points = {p['id']: p for p in story.get('knowledge', [])}
    for f in atlas['features']:
        if set(f['location_ids']) - places or set(f['knowledge_ids']) - points.keys():
            raise ValueError('地图引用了不存在的地点或知识点')
        if f['visibility'] == 'public' and any(points[k]['visibility'] != 'public' for k in f['knowledge_ids']):
            raise ValueError('公开地图不能关联作者秘密；请改为作者可见标记')
    return atlas


def project_atlas(story, session=None):
    atlas = validate_atlas(story)
    points = {p['id']: p for p in story.get('knowledge', [])}
    visible = None
    if session is not None:
        here = next(p for p in story['locations'] if p['id'] == session['location'])
        visible = set(session['explored']) | set(here['neighbors'])
    projected = []
    for f in atlas['features']:
        if session is not None:
            if f['visibility'] != 'public' or (f['reveal_flag'] and not session['flags'].get(f['reveal_flag'])):
                continue
            if f['location_ids'] and not set(f['location_ids']) <= visible:
                continue
        articles = []
        for pid in f['knowledge_ids']:
            p = points[pid]
            if session is not None and (p['visibility'] != 'public' or
                (p.get('known_by') and 'player' not in p['known_by']) or
                (p.get('reveal_flag') and not session['flags'].get(p['reveal_flag'])) or
                (p.get('locations') and session['location'] not in p['locations'])):
                continue
            articles.append({k: p[k] for k in ('id','title','content','status') if k in p})
        if f.get('environment'):
            if session is not None:
                f={**f,'environment':{**f['environment'],'deposits':[d for d in f['environment']['deposits'] if d['surveyed']]}}
                if f['layer']=='resources' and not f['environment']['deposits']:continue
            f={**f,'estimates':estimate(f['environment'])}
        projected.append({**f, 'knowledge_ids': [p['id'] for p in articles], 'articles': articles})
    return {**atlas, 'features': projected}


def city_atlas(story, cities):
    """Compile authored regional facts to linked map features, without inventing terrain."""
    features = []
    for i, (place, city) in enumerate(zip(story['locations'], cities)):
        loc = place['id']
        features.append({'id':'city_'+loc,'name':place['name'],'layer':'markers','geometry':'point',
            'coordinates':[place['coordinates']], 'description':city['description'],
            'location_ids':[loc], 'knowledge_ids':[p['id'] for p in story['knowledge'] if p.get('locations') == [loc] and p['visibility']=='public'][:20]})
        for layer, field in [('terrain','terrain'),('states','faction_description'),('cultures','culture')]:
            if city.get(field):
                features.append({'id':layer+'_'+loc,'name':city.get('faction',place['name']) if layer=='states' else place['name']+' · '+{'terrain':'地貌','cultures':'文化'}[layer],
                    'layer':layer,'coordinates':(city.get('terrain_boundary') or [place['coordinates']]) if layer=='terrain' else [place['coordinates']],
                    'geometry':'polygon' if layer=='terrain' and city.get('terrain_boundary') else 'point',
                    'terrain_kind':city.get('terrain_kind','unspecified') if layer=='terrain' else 'unspecified',
                    'description':city[field], 'location_ids':[loc],
                    'knowledge_ids':[p['id'] for p in story['knowledge'] if p.get('locations')==[loc] and p['visibility']=='public' and p['category'] in ('地区与城市','气候水文','资源供应')] if layer=='terrain' else []})
    by_id = {p['id']:p for p in story['locations']}
    visited = set()
    for place in story['locations']:
        for neighbor in place['neighbors']:
            pair = tuple(sorted((place['id'],neighbor)))
            if pair in visited:
                continue
            visited.add(pair)
            features.append({'id':'route_'+str(len(visited)), 'name':place['name']+'—'+by_id[neighbor]['name'],
                'layer':'routes','geometry':'line','coordinates':[place['coordinates'],by_id[neighbor]['coordinates']],
                'description':'已有可通行关系的示意连线，不是实际道路测绘，不据此计算旅行小时。','location_ids':list(pair)})
    return Atlas(title=story['title']+' · 图册', features=features).model_dump(mode='json')
