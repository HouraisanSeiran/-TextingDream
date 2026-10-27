"""Two-stage world creation. Compact AI blueprints compile to executable packages."""
import copy
import json
from typing import Literal
from pydantic import Field, model_validator
from .contracts import Strict
from .knowledge import PackageFiles, atomic_text, retrieve, validate_points, read_point
from .prompts import stable_json, template
from .runtime import uid, now
from .atlas import Atlas, TerrainKind, city_atlas, project_atlas
from .geography import Environment, Calendar, environment_features
from . import attributes
from . import element_assembly


class KnowledgePoint(Strict):
    id: str = Field(pattern=r'^[A-Za-z0-9_-]+$', max_length=80)
    title: str = Field(min_length=1, max_length=100)
    category: str = Field(min_length=1, max_length=60)
    keywords: list[str] = Field(min_length=1, max_length=12)
    content: str = Field(min_length=1, max_length=3000)
    visibility: Literal['public', 'author'] = 'author'
    status: str = '生成草案，待作者审核'


class WorldviewBlueprint(Strict):
    title: str = Field(min_length=1, max_length=80)
    overview: str = Field(min_length=20, max_length=2500)
    knowledge: list[KnowledgePoint] = Field(min_length=4, max_length=24)


class City(Strict):
    environment: Environment = Field(default_factory=Environment)
    name: str = Field(min_length=1, max_length=80)
    region: str = Field(min_length=1, max_length=80)
    terrain: str = Field(min_length=1, max_length=300)
    terrain_kind: TerrainKind = 'unspecified'
    terrain_boundary: list[tuple[float, float]] = Field(default_factory=list, max_length=60)
    description: str = Field(min_length=1, max_length=800)
    faction: str = Field(min_length=1, max_length=80)
    faction_description: str = Field(min_length=1, max_length=800)
    coordinates: tuple[float, float]
    event_title: str = Field(min_length=1, max_length=80)
    goal: str = Field(min_length=1, max_length=300)
    discovery: str = Field(min_length=1, max_length=800)
    secret: str = Field(min_length=1, max_length=800)
    climate: str = Field(default='', max_length=400)
    resources: str = Field(default='', max_length=500)
    culture: str = Field(default='', max_length=600)
    faith: str = Field(default='', max_length=400)
    economy: str = Field(default='', max_length=600)

    @model_validator(mode='after')
    def coordinate_bounds(self):
        if not (-180 <= self.coordinates[0] <= 180 and -90 <= self.coordinates[1] <= 90):
            raise ValueError('示意坐标必须位于经度±180、纬度±90内')
        if self.terrain_boundary and (len(self.terrain_boundary)<3 or any(not -180<=x<=180 or not -90<=y<=90 for x,y in self.terrain_boundary)):
            raise ValueError('地形范围需要至少三个合法坐标')
        return self


class Person(Strict):
    attributes: dict[str,float] = Field(default_factory=lambda:{k:50 for k in attributes.AXES},
        json_schema_extra={'type':'object','required':list(attributes.AXES),'additionalProperties':False,
            'properties':{k:{'type':'number','minimum':0,'maximum':100,'description':attributes.NAMES[k]} for k in attributes.AXES}})
    name: str = Field(min_length=1, max_length=80)
    appearance: str = Field(min_length=1, max_length=300)
    occupation: str = Field(min_length=1, max_length=80)
    personality: dict[str, float] = Field(min_length=1, max_length=8)
    secret: str = Field(min_length=1, max_length=500)

    @model_validator(mode='after')
    def weights(self):
        attributes.values(self.attributes)
        if any(not 0 <= n <= 1 for n in self.personality.values()):
            raise ValueError('性格权重须在0到1之间')
        return self


class WorldBlueprint(Strict):
    cities: list[City] = Field(min_length=2, max_length=5)
    hero: Person
    guide: Person
    item_name: str = Field(min_length=1, max_length=80)
    item_description: str = Field(min_length=1, max_length=400)


class ExpansionBlueprint(Strict):
    knowledge: list[KnowledgePoint] = Field(min_length=1, max_length=24)
    atlas: Atlas


class CompleteBlueprint(WorldBlueprint):
    worldview: WorldviewBlueprint


class GenerateWorldRequest(Strict):
    kind: Literal['worldview', 'world', 'complete', 'expand']
    title: str = Field(default='未命名世界', min_length=1, max_length=80)
    instruction: str = Field(min_length=1, max_length=4000)
    historical_reference: str = Field(default='', max_length=500)
    worldview_draft_id: str | None = None
    city_count: int = Field(default=3, ge=2, le=5)
    output_tokens: int = Field(default=4000, ge=1500, le=8000)
    # Locked element refs ("namespace/element_id" or ".../id@3"). Empty = pin the CURRENT
    # package manifest. Either way nothing is taken straight from the library: an explicit
    # list must be a subset of the manifest that already exists, and candidates are never
    # auto-confirmed here.
    elements: list[str] = Field(default_factory=list, max_length=16)


class GeneratorEdit(Strict):
    data: dict


def worldview_example(title, reference=''):
    subjects = [('时代与文明','时代,文明','多个城邦在旧帝国解体后沿商路合作。'),
                ('力量与代价','力量,法术','术法需要材料与休息，不能替代生产和契约。'),
                ('信仰与社会','信仰,社会','各地信仰内部有不同解释，不以教派决定个人善恶。'),
                ('经济与消息','贸易,传闻','贸易连接各城，旅人应区分见闻与已核实的事实。')]
    return {'title':title, 'overview':f'{title}是一处由河谷、山路与海港连接的架空世界。旅人从故乡出发，通过行动认识不同共同体。力量有代价，角色所闻不等于真相。此为离线模板，未按自由指令完成AI创作。',
            'knowledge':[{'id':f'foundation_{i}', 'title':name, 'category':'世界基础', 'keywords':words.split(','),
                          'content':body + (f' 作者指定历史参考：{reference}；尚未进行历史考证。' if reference else ''),
                          'visibility':'public', 'status':'离线模板，待编辑'} for i,(name,words,body) in enumerate(subjects)]}


def world_example(count):
    names = ['河灯城','雾岭驿','潮门港','苇泽城','北星堡']
    return {'cities':[{'name':names[i],'region':['河谷','山地','海岸'][i%3], 'terrain':'商道经过水源与有人维护的道路。',
                       'terrain_kind':['plain','mountain','plain'][i%3],
                       'environment':Environment(elevation_m=[180,1800,25][i%3],slope_deg=[3,24,4][i%3],
                           freshwater=[.85,.4,.7][i%3],soil_fertility=[.8,.3,.6][i%3],transport=[.7,.3,.9][i%3],
                           basin=names[i]+'集水区',deposits=[{'kind':'iron' if i%2 else 'coal','abundance':.5,'surveyed':True}] if i%3==1 else [],
                           source='离线示例设计参数，待作者修改').model_dump(mode='json'),
                       'description':f'{names[i]}的旅店与市集迎接过路旅人。', 'faction':names[i]+'议事会',
                       'faction_description':'由工匠、商人和居民推举代表，负责道路维护与争议调解。',
                       'coordinates':[35+i*12,25+i*3], 'event_title':names[i]+'的通行约定',
                       'goal':'了解此地的规则并寻找下一段旅途的线索。',
                       'discovery':f'我在{names[i]}读到公告：过境旅人可以向驿馆申请路线说明。',
                       'secret':'议事会尚未公开一场关于维修费用的内部争执。'} for i in range(count)],
            'hero':{'name':'行旅者','appearance':'带着旧行囊的旅人。','occupation':'旅人','personality':{'好奇':0.7,'谨慎':0.5},'secret':'尚未向别人提起自己的出行缘由。'},
            'guide':{'name':'引路人','appearance':'随身携带路线册的本地向导。','occupation':'向导','personality':{'谨慎':0.8},'secret':'曾为议事会递送过未公开的信件。'},
            'item_name':'行路册','item_description':'记录已公开驿站与道路的纸册，不揭示未探索地区的秘密。'}


def compile_package(view, world, identity, manifest=None):
    # Imported foundations may be larger than a freshly generated blueprint.
    view = copy.deepcopy(view)
    validate_points(view['knowledge'])
    world = WorldBlueprint.model_validate(world).model_dump(mode='json')
    story_id, chars_id = 'world_' + identity, 'characters_' + identity
    points = copy.deepcopy(view['knowledge'])
    story = {'id':story_id,'title':view['title'],'premise':view['overview'], 'worldview':{'premise':view['overview']},
             'character_package_id':chars_id,'knowledge':points,'locations':[],'events':[],'items':[],
             'major_scenes':[], 'mechanics':{'narrative_person':'first','visibility_pipeline':'inner_complete_then_surface_projection'},
             'generator':{'schema':1,'map':'坐标为示意，不代表现实地理或历史疆域'}}
    count = len(world['cities'])
    for i, city in enumerate(world['cities']):
        loc, scene, event = f'place_{i}', f'scene_{i}', f'event_{i}'
        story['locations'].append({'id':loc,'name':city['name'],'description':city['description'],
                                   'neighbors':([f'place_{i-1}'] if i else [])+([f'place_{i+1}'] if i+1<count else []),
                                   'scenes':[event],'coordinates':city['coordinates']})
        story['major_scenes'].append({'id':scene,'title':city['name']+' · 旅途见闻','kind':'city','location_ids':[loc],'expected_turns':16})
        story['events'].append({'id':event,'title':city['event_title'],'location_id':loc,'major_scene_id':scene,
                                'participants':['hero','guide'] if i==0 else ['hero'], 'player_goal':city['goal'],
                                'hidden_goal':city['secret'], 'next_events':[f'event_{i+1}'] if i+1<count else [],
                                'entry_flags':{},'exit_flag':f'completed_{i}','max_turns':16,'player_enters':True,
                                'actions':[{'id':'investigate','label':'了解当地情况并结束本次会面','ends_event':True,
                                            'effects':[], 'success_text':city['discovery']}]})
        points.extend([{'id':f'gen_{identity}_geography_{i}','title':city['name']+'地理','category':'地区与城市','keywords':[city['name'],city['region']],
                        'visibility':'public','locations':[loc],'status':'生成草案，作者已保存','content':city['terrain']+'\n'+city['description']},
                       {'id':f'gen_{identity}_faction_{i}','title':city['faction'],'category':'势力与社会','keywords':[city['name'],city['faction']],
                        'visibility':'public','locations':[loc],'status':'生成草案，作者已保存','content':city['faction_description']},
                       {'id':f'gen_{identity}_secret_{i}','title':city['name']+'幕后','category':'作者秘密','keywords':[city['name']],
                        'visibility':'author','status':'生成草案，作者已保存','content':city['secret']}])
        for field, label in [('climate','气候水文'),('resources','资源供应'),('culture','文化语言'),('faith','信仰习俗'),('economy','生计贸易')]:
            if city.get(field):
                points.append({'id':f'gen_{identity}_{field}_{i}', 'title':city['name']+' · '+label,
                    'category':label,'keywords':[city['name'],label], 'visibility':'public', 'locations':[loc],
                    'status':'生成草案，作者已保存','content':city[field]})
    story['items'] = [{'id':'travel_book','name':world['item_name'],'description':world['item_description'],'location_id':'place_0'}]
    story['events'][0]['actions'].insert(0, {'id':'collect','label':'领取'+world['item_name'],'ends_event':False,
                                          'effects':[{'op':'take','id':'travel_book'}],'success_text':'我收好'+world['item_name']+'，准备继续旅程。'})
    characters = {'id':chars_id,'title':view['title']+' · 独立角色包','characters':[],'generation_constraints':{'max_power_level':100}}
    for key, role in [('hero','主角'),('guide','次要角色')]:
        characters['characters'].append({**world[key],'id':key,'role':role,'public_name':world[key]['name'],
                                         'location_id':'place_0','traits':list(world[key]['personality']), 'state':{},'power_level':1})
    validate_points(points)
    story['atlas'] = city_atlas(story, world['cities'])
    for place,city in zip(story['locations'],world['cities']):
        place['environment']=city['environment']
        story['atlas']['features'].extend(environment_features(place))
    story['mechanics']['calendar']=Calendar().model_dump()
    if manifest is not None:
        # A copied manifest may name places or characters from ANOTHER world. Those
        # references are cleared (nobody can see the element) instead of being carried
        # over or widened; the author re-specifies the public scope afterwards.
        rebound, _notes = element_assembly.rebind_manifest(manifest, story, characters)
        story['mechanics'][element_assembly.MECHANICS_KEY] = rebound
    return attributes.upgrade(story,characters)


class WorldGenerator:
    def __init__(self, service):
        self.service = service

    def get(self, identity):
        draft = self.service.store.get('world_generation', identity)
        if not draft:
            raise ValueError('生成草稿不存在')
        return draft

    def validate(self, draft, data):
        if draft['kind'] == 'expand':
            result = ExpansionBlueprint.model_validate(data).model_dump(mode='json')
            p = self.service.runtime.package(draft['base_revision'])
            story = self.expanded_story(p['story'],result)
            self.service.runtime.validate_package(story,p['characters'])
            return result
        if draft['kind'] == 'complete':
            result = CompleteBlueprint.model_validate(data).model_dump(mode='json')
            if len(result['cities']) != draft['request']['city_count']:
                raise ValueError('生成城市数与指定数量不一致')
            view = result['worldview']
            story, chars = compile_package(view,{k:v for k,v in result.items() if k!='worldview'},draft['id'],manifest=draft.get('element_manifest'))
            self.service.runtime.validate_package(story,chars)
            return result
        if draft['kind'] == 'worldview':
            result = WorldviewBlueprint.model_validate(data).model_dump()
            validate_points(result['knowledge'])
            return result
        result = WorldBlueprint.model_validate(data).model_dump(mode='json')
        if len(result['cities']) != draft['request']['city_count']:
            raise ValueError('生成城市数与指定数量不一致')
        story, chars = compile_package(draft['worldview'], result, draft['id'],manifest=draft.get('element_manifest'))
        self.service.runtime.validate_package(story, chars)
        return result

    @staticmethod
    def expanded_story(source, additions):
        story = copy.deepcopy(source)
        old = {k['id'] for k in story.get('knowledge',[])}
        if old & {k['id'] for k in additions['knowledge']}:
            raise ValueError('补充知识点不能覆盖已有 ID，请使用新的 ID')
        story.setdefault('knowledge',[]).extend(additions['knowledge'])
        atlas = Atlas.model_validate(story.get('atlas',{})).model_dump(mode='json')
        if {f['id'] for f in atlas['features']} & {f['id'] for f in additions['atlas']['features']}:
            raise ValueError('补充地图不能覆盖已有标记 ID')
        atlas['features'].extend(additions['atlas']['features'])
        story['atlas'] = atlas
        return story

    def assembled(self, draft):
        if draft['kind']=='expand':
            p=self.service.runtime.package(draft['base_revision'])
            return self.expanded_story(p['story'],draft['data']),copy.deepcopy(p['characters'])
        if draft['kind']=='complete':
            data=draft['data']
            return compile_package(data['worldview'],{k:v for k,v in data.items() if k!='worldview'},draft['id'],manifest=draft.get('element_manifest'))
        return compile_package(draft['worldview'],draft['data'],draft['id'],manifest=draft.get('element_manifest'))

    def preview_atlas(self, identity):
        draft=self.get(identity)
        if draft['kind']=='worldview':
            return Atlas().model_dump(mode='json')
        story,_=self.assembled(draft)
        return project_atlas(story)

    async def generate(self, request):
        svc = self.service
        draft = {'id':uid(),'kind':request.kind,'created':now(),'status':'draft','request':request.model_dump()}
        # 元素清单在**创建草稿时**就固定：缺省是本包当前快照，显式引用只能是它的子集。
        # 生成器不会自己去库里挑新条目，也不替作者确认候选状态。
        manifest, element_notes = None, []
        if request.kind != 'expand':
            manifest, element_notes = svc.elements.pin_manifest(request.elements or None)
        draft['element_manifest'] = manifest
        draft['element_warnings'] = element_notes
        if request.kind == 'expand':
            svc.runtime.reload_documents()
            p=svc.runtime.package()
            draft['base_revision']=p['id']
            draft['worldview']={'title':p['story']['title'],'overview':p['story']['worldview']['premise']}
            example={'knowledge':[{'id':'expansion_example','title':'商路维护','category':'交通与社会',
                'keywords':['道路','维护'],'content':'离线示例：各地维护义务、资金与通行季节待作者补充。','visibility':'author','status':'离线模板'}],
                'atlas':Atlas().model_dump(mode='json')}
            context={'request':request.model_dump(),'overview':p['story']['worldview']['premise'],
                'knowledge':retrieve(p['story'],request.instruction,'author'),
                'existing_knowledge_ids':[k['id'] for k in p['story'].get('knowledge',[])],
                'existing_map_ids':[f['id'] for f in p['story'].get('atlas',{}).get('features',[])],
                'locations':[{k:l[k] for k in ('id','name','coordinates','neighbors') if k in l} for l in p['story']['locations']],
                'schema':ExpansionBlueprint.model_json_schema(),'example':example,
                'elements':element_assembly.author_context(element_assembly.package_manifest(p['story']))}
        elif request.kind == 'complete':
            example={**world_example(request.city_count),'worldview':worldview_example(request.title,request.historical_reference)}
            context={'request':request.model_dump(),'schema':CompleteBlueprint.model_json_schema(),'example':example,
                     'elements':element_assembly.author_context(manifest)}
        elif request.kind == 'worldview':
            example = worldview_example(request.title, request.historical_reference)
            schema = WorldviewBlueprint.model_json_schema()
            context = {'request':request.model_dump(), 'example':example, 'schema':schema,
                       'elements':element_assembly.author_context(manifest)}
        else:
            if request.worldview_draft_id:
                foundation = self.get(request.worldview_draft_id)
                if foundation['kind'] != 'worldview':
                    raise ValueError('请选择世界观草稿作为基础')
                view = copy.deepcopy(foundation['data'])
                if foundation['status'] == 'saved':
                    folder = svc.runtime.package_directory(foundation['folder'])
                    view['overview'] = (folder/'总概.md').read_text(encoding='utf-8-sig').strip()
                    view['knowledge'] = [read_point(p) for p in sorted((folder/'知识点').rglob('*.md'))]
                    view = WorldviewBlueprint.model_validate(view).model_dump()
                    validate_points(view['knowledge'])
            else:
                svc.runtime.reload_documents()
                source = svc.runtime.package()['story']
                # Keep the whole foundation on disk, but retrieve only relevant points for AI.
                view = {'title':request.title,'overview':source['worldview']['premise'],
                        'knowledge':copy.deepcopy(source.get('knowledge', []))}
                # Existing packages can have more than the creation form's 24 points.
            draft['worldview'] = view
            example = world_example(request.city_count)
            context = {'request':request.model_dump(), 'overview':view['overview'],
                       'knowledge':retrieve({'knowledge':view['knowledge']}, request.instruction, 'author'),
                       'example':example,'schema':WorldBlueprint.model_json_schema(),
                       'elements':element_assembly.author_context(manifest)}
        system = template('generator')
        if len(system) + len(stable_json(context)) > svc.preferences()['context_chars']:
            raise ValueError('生成上下文超过预算，请缩短要求或提高设置中的上下文预算')
        if svc.provider.config()['offline']:
            data, usage = example, {'mode':'offline','calls':0}
            svc.provider.offline_trace('generator_'+request.kind, context, data)
        else:
            data, usage = await svc.provider.complete(system, context, json_mode=True,
                                                       scope='generator_'+request.kind, max_tokens=request.output_tokens)
            usage['calls'] = 1
        draft['data'] = self.validate(draft, data)
        draft['usage'] = usage
        svc.store.put('world_generation', draft['id'], draft)
        return draft

    def edit(self, identity, data):
        draft = self.get(identity)
        if draft['status'] != 'draft':
            raise ValueError('已保存的生成结果不能覆盖，请重新生成')
        draft['data'] = self.validate(draft, data)
        self.service.store.put('world_generation', identity, draft)
        return draft

    def save(self, identity):
        draft = self.get(identity)
        if draft['status'] == 'saved':
            return draft
        rt = self.service.runtime
        draft['data'] = self.validate(draft, draft['data'])
        folder = ('世界观_' if draft['kind']=='worldview' else '世界_') + identity
        target = rt.library / folder
        if target.exists():
            raise ValueError('目标目录已存在，未覆盖；请检查上次保存结果')
        stage = rt.library / ('.pending_' + identity)
        if stage.exists():
            raise ValueError('上次保存未完成，请检查临时目录后重试')
        if draft['kind'] == 'worldview':
            data = draft['data']
            atomic_text(stage / '总概.md', data['overview']+'\n')
            from .knowledge import point_document
            for point in data['knowledge']:
                atomic_text(stage / '知识点' / (point['id']+'.md'), point_document(point))
            atomic_text(stage / 'worldview.json', json.dumps(data, ensure_ascii=False, indent=2))
        else:
            story, chars = self.assembled(draft)
            if draft['kind']=='expand':
                # Expansion is a reviewable new package; source and pinned journeys survive.
                story['id']='world_'+identity
                chars['id']='characters_'+identity
                story['character_package_id']=chars['id']
                story['title'] += ' · 地理补充'
            rt.validate_package(story, chars)
            PackageFiles(stage).write(story)
            atomic_text(rt.character_directory / (chars['id']+'.json'), json.dumps(chars, ensure_ascii=False, indent=2))
            atomic_text(stage / '使用说明.md', '# '+story['title']+'\n\n此目录是正式故事包来源。角色包独立保存为 character_packages/'+chars['id']+'.json。\n在世界创作的故事包列表中点击“启用”，再到表层对话新建旅程。已有旅程保留原版本。atlas.json 保存分层地图，知识点目录保存关联资料。坐标与范围为架空示意，不据此计算实际行程。\n')
        atomic_text(stage / '生成说明.json', json.dumps({'request':draft['request'],'usage':draft['usage'],'created':draft['created']}, ensure_ascii=False, indent=2))
        stage.rename(target)
        draft.update(status='saved',folder=folder)
        self.service.store.put('world_generation', identity, draft)
        return draft
