import secrets
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from .contracts import ApiSettings, Corpus, DraftRequest, BatchDraftRequest, Element, Move, NewSession, PackageEdit, Preferences, Turn, DevelopmentRequest, WaitRequest
from .recall import dialogue_records
from .cache_metrics import cache_usage
from . import local_rules
import copy
from .service import Service
from .storage import Store
from .knowledge import notebook
from .world_generator import GenerateWorldRequest, GeneratorEdit
from .reply_direction import ReplyDirectionRequest, DIRECTIONS, draft_reply
from .world_pipeline import WorldPipeline, PipelineRequest, StageEdit
from . import towns
from .town_schema import (AdoptRequest, AdvanceRequest, PresetRequest, PublishRequest,
                          StageEditRequest, STAGE_NAMES,
                          DraftRequest as TownDraftRequest)

ROOT = Path(__file__).resolve().parents[1]


def create_app(db_path=None):
    app = FastAPI(title='TextingDream')
    service = Service(Store(db_path or ROOT / 'data/textiledream.sqlite3'), ROOT)
    app.state.service = service
    pipeline=WorldPipeline(service)
    token = secrets.token_urlsafe(32)
    app.mount('/static', StaticFiles(directory=ROOT / 'app/static'), name='static')
    app.mount('/maps', StaticFiles(directory=ROOT / 'assets/maps'), name='maps')

    @app.middleware('http')
    async def guard(request: Request, call_next):
        if request.url.path.startswith('/api/'):
            host = request.url.hostname
            if host not in ('127.0.0.1', 'localhost', 'testserver'):
                return JSONResponse({'detail': '仅允许本机访问'}, status_code=403)
            origin = request.headers.get('origin')
            if origin and origin != str(request.base_url).rstrip('/'):
                return JSONResponse({'detail': '拒绝跨站请求'}, status_code=403)
            if request.method != 'GET' or request.url.path.startswith('/api/inner') or request.url.path.startswith('/api/settings'):
                if request.headers.get('x-textiledream-token') != token:
                    return JSONResponse({'detail': '请刷新页面后重试'}, status_code=403)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
        return response

    @app.exception_handler(ValueError)
    async def value_error(request, error):
        return JSONResponse({'detail': str(error)}, status_code=400)

    @app.exception_handler(ValidationError)
    async def validation_error(request, error):
        return JSONResponse({'detail': '结构校验失败：' + str(error)}, status_code=422)

    @app.get('/')
    def index():
        return FileResponse(ROOT / 'app/static/index.html', media_type='text/html; charset=utf-8')

    @app.get('/api/bootstrap')
    def bootstrap():
        sessions = [{'id': s['id'], 'title': s['title']} for s in service.store.all('session')]
        return {'token': token, 'sessions': sessions, 'preferences': service.preferences(), 'api': service.provider.public_config()}

    @app.post('/api/sessions')
    async def new_session(req: NewSession):
        async with service.lock:
            return service.runtime.surface(service.runtime.new_session(req.title, req.mode))

    @app.get('/api/sessions/{id}')
    def surface(id: str):
        return service.runtime.surface(service.store.session(id))

    @app.get('/api/sessions/{id}/notebook')
    def knowledge_notebook(id: str):
        return notebook(service.store.session(id))

    @app.get('/api/sessions/{id}/towns')
    def journey_towns(id: str):
        # Player side, scoped twice over: the reading comes from the revision this
        # JOURNEY is bound to (so a later adoption cannot reach it), and then only the
        # places this journey stands in, has been to, or borders. A town the author
        # placed somewhere the player has never heard of is not returned at all.
        from .towns_store import story_towns
        s = service.store.session(id)
        story = service.runtime.package(s['revision'])['story']
        return {'revision': s['revision'],
                'location': s['location'],
                'towns': story_towns(story, s['revision'], s)}

    @app.get('/api/sessions/{id}/towns/{version_id}')
    def journey_town(id: str, version_id: str):
        # One town, still filtered by knowledge: guessing a version_id must not reach a
        # place the journey has never been near.
        from .towns_store import town_for_journey
        s = service.store.session(id)
        story = service.runtime.package(s['revision'])['story']
        return town_for_journey(story, s, version_id, s['revision'])

    @app.post('/api/inner/package/reload')
    async def reload_package():
        async with service.lock:
            return {'revision': service.runtime.reload_documents()}

    @app.get('/api/inner/local-rules')
    def get_local_rules():
        p=service.runtime.package()
        return {'revision':p['id'],'rules':local_rules.rules(p['story']).model_dump()}

    # ---- towns: author side (token protected). No model is called here. ----
    @app.get('/api/inner/towns/presets')
    def town_presets():
        return {'presets': [{'id': p, 'title': t} for p, t in
                            (('wet_valley', '湿润河谷农业'),
                             ('cold_mountain_mine', '寒冷山地矿业'),
                             ('arid_oasis_route', '干旱商路绿洲'))],
                'generator_version': towns.GENERATOR_VERSION,
                'stages': list(STAGE_NAMES),
                'note': 'V1 为固定规则生成；不调用语言模型，也不读外部地形工具'}

    @app.get('/api/inner/towns')
    def town_drafts():
        return [{'id': d['id'], 'revision': d['revision'], 'status': d['status'],
                 'created': d['created'], 'updated': d['updated'],
                 'base_story_revision': d['base_story_revision'],
                 'site': d['input']['site_name'], 'seed': d['seed'],
                 'stages': [{k: s.get(k) for k in ('name', 'title', 'hash', 'stale', 'source')}
                            for s in d['stages']],
                 'published': d.get('published', [])} for d in service.towns.list_drafts()]

    @app.post('/api/inner/towns')
    async def town_create(req: TownDraftRequest):
        async with service.lock:
            return service.towns.create(req)

    @app.post('/api/inner/towns/presets/{preset}')
    async def town_create_preset(preset: str, req: PresetRequest):
        async with service.lock:
            base = service.runtime.package()['id']
            entry = towns.preset_entry(preset, req.seed, req.site_name, base)
            return service.towns.create(TownDraftRequest(input=entry))

    @app.get('/api/inner/towns/{draft_id}')
    def town_draft(draft_id: str):
        draft = service.towns.get_draft(draft_id)
        return {**service.towns.authored(draft),
                'stages': draft['stages'], 'input': draft['input'],
                'revision': draft['revision'], 'status': draft['status'],
                'base_story_revision': draft['base_story_revision'],
                'published': draft.get('published', [])}

    @app.post('/api/inner/towns/{draft_id}/next')
    async def town_advance(draft_id: str, req: AdvanceRequest):
        async with service.lock:
            return service.towns.advance(draft_id, req.expected_revision)

    @app.put('/api/inner/towns/{draft_id}/stages')
    async def town_edit_stage(draft_id: str, req: StageEditRequest):
        async with service.lock:
            return service.towns.edit_stage(draft_id, req.stage, req.data,
                                            req.expected_revision)

    @app.get('/api/inner/towns/{draft_id}/preview')
    def town_preview(draft_id: str, audience: str = 'public'):
        draft = service.towns.get_draft(draft_id)
        snapshot = service.towns.snapshot(draft)
        if audience == 'author':
            return towns.author_view(snapshot)
        return towns.public_view(snapshot)

    @app.post('/api/inner/towns/{draft_id}/publish')
    async def town_publish(draft_id: str, req: PublishRequest):
        async with service.lock:
            return service.towns.publish(draft_id, req.expected_revision)

    @app.get('/api/inner/town-versions')
    def town_versions():
        return [{'id': v['id'], 'created': v['created'], 'town_id': v['town_id'],
                 'content_hash': v['content_hash'], 'seed': v['seed'],
                 'base_story_revision': v['base_story_revision'],
                 'generator_version': v['generator_version'],
                 'name': v['snapshot']['skeleton']['display_name'],
                 'bindings': [b['id'] for b in service.towns.list_bindings(v['id'])],
                 'warnings': v.get('warnings', [])[:5]}
                for v in service.towns.list_versions()]

    @app.get('/api/inner/town-versions/{version_id}')
    def town_version(version_id: str, audience: str = 'author'):
        version = service.towns.get_version(version_id)
        if audience == 'public':
            return towns.public_view(version['snapshot'])
        return {'id': version['id'], 'created': version['created'],
                'content_hash': version['content_hash'],
                'base_story_revision': version['base_story_revision'],
                'warnings': version.get('warnings', []),
                'snapshot': version['snapshot'],
                'bindings': service.towns.list_bindings(version_id)}

    @app.post('/api/inner/town-versions/{version_id}/adopt')
    async def town_adopt(version_id: str, req: AdoptRequest):
        async with service.lock:
            return service.towns.adopt(version_id, req.expected_story_revision,
                                       req.location_id, req.note)

    @app.get('/api/inner/town-bindings')
    def town_bindings(version: str = ''):
        return service.towns.list_bindings(version or None)

    @app.get('/api/inner/rewards')
    def get_rewards(session: str = ''):
        # Author-only, read-only. Without a session it reports the active package's
        # configuration and derivation rules. With one, everything — config, instances
        # and projections — comes from the revision that journey is bound to, because a
        # journey keeps its own package version and may predate a later reward config
        # (or the current package may have none at all).
        from . import rewards as rewards_rules
        if session:
            s=service.store.session(session)
            p=service.runtime.package(s['revision'])
            result={'revision':p['id'],'journey_revision':s['revision']}
        else:
            s=None
            p=service.runtime.package()
            result={'revision':p['id']}
        cfg=rewards_rules.rules(p['story'])
        if cfg is None:
            result['configured']=False
            if s is not None:
                # The journey may still hold reward state from an older revision; report
                # that instead of pretending it has none.
                result['journey']={'id':s['id'],'revision':s['revision'],
                                   'projection':None,'grants':[],'ledger':[],
                                   'instances':[],'note':'该旅程绑定的版本未配置奖励'}
            return result
        result.update(configured=True, derivation=rewards_rules.DERIVATION,
                      rules=cfg.model_dump())
        if s is not None:
            current=rewards_rules.state(s,cfg)
            result['journey']={'id':s['id'],'revision':s['revision'],
                               'projection':rewards_rules.public_state(s,p['story'],'author'),
                               'grants':current['grants'],'ledger':current['ledger'],
                               'instances':current['items']}
        return result

    @app.get('/api/inner/attribute-keywords')
    def attribute_keywords(character_id: str='', query: str=''):
        from . import attributes
        p=service.runtime.package()
        spec=p['story'].get('mechanics',{}).get('attributes',attributes.specification())
        c=next((c for c in p['characters']['characters'] if c['id']==character_id),None)
        if character_id and c is None:raise ValueError('角色不存在')
        return {'revision':p['id'],'specification':spec,'index':'SQLite六维属性向量；非神经语义嵌入',
                'matches':service.runtime.attribute_vectors.search(spec,attributes.values(c.get('attributes'),legacy=True),query,6) if c else []}

    @app.get('/api/inner/world-pipelines')
    def pipelines():return service.store.all('world_pipeline')

    @app.post('/api/inner/world-pipelines')
    async def start_pipeline(req:PipelineRequest):
        async with service.lock:return pipeline.start(req)

    @app.post('/api/inner/world-pipelines/{id}/next')
    async def advance_pipeline(id:str):
        async with service.lock:return await pipeline.advance(id)

    @app.put('/api/inner/world-pipelines/{id}')
    async def edit_pipeline(id:str,req:StageEdit):
        async with service.lock:return pipeline.edit(id,req)

    @app.get('/api/inner/world-pipelines/{id}/atlas')
    def pipeline_atlas(id:str):return pipeline.atlas(pipeline.get(id))

    @app.post('/api/inner/world-pipelines/{id}/save')
    async def save_pipeline(id:str):
        async with service.lock:return pipeline.save(id)

    @app.put('/api/inner/local-rules')
    async def put_local_rules(req: local_rules.LocalRules):
        async with service.lock:
            p=copy.deepcopy(service.runtime.package())
            p['story'].setdefault('mechanics',{})['local']=req.model_dump()
            revision=service.runtime.commit_package(p['story'],p['characters'],'修改本地资源与日程规则')
            return {'revision':revision,'rules':req.model_dump()}

    @app.get('/api/inner/package/document')
    def package_document():
        story = service.runtime.files.read()
        text = '# ' + story['title'] + '\n\n' + story['worldview']['premise']
        for p in story.get('knowledge', []):
            text += '\n\n## ' + p['title'] + '\n\n' + p['content']
        return {'text': text, 'directory': str(service.runtime.files.directory)}

    @app.post('/api/sessions/{id}/chat')
    async def chat(id: str, req: Turn):
        return await service.turn(id, req)

    @app.get('/api/reply-directions')
    def reply_directions():
        return [{'id':k,'title':v[0],'description':v[1]} for k,v in DIRECTIONS.items()]

    @app.post('/api/sessions/{id}/reply-draft')
    async def reply_draft(id: str, req: ReplyDirectionRequest):
        return await draft_reply(service,id,req)

    @app.post('/api/sessions/{id}/move')
    async def move(id: str, req: Move):
        async with service.lock:
            s = service.store.session(id)
            service.runtime.move(s, req.location_id)
            return service.runtime.surface(s)

    @app.post('/api/sessions/{id}/wait')
    async def wait_local(id: str, req: WaitRequest):
        async with service.lock:
            s=service.store.session(id)
            if s['active']:raise ValueError('请先结束当前事件，再等待时间推进')
            p=service.runtime.package(s['revision'])
            local_rules.advance(s,p['story'],p['characters'],req.hours)
            service.runtime.enter(s)
            service.store.save_session(s)
            return service.runtime.surface(s)

    @app.post('/api/sessions/{id}/close')
    async def close(id: str):
        async with service.lock:
            s = service.store.session(id)
            service.runtime.close_event(s)
            service.store.save_session(s)
            return service.runtime.surface(s)

    @app.post('/api/sessions/{id}/rollback/{archive}')
    async def rollback(id: str, archive: str):
        async with service.lock:
            return service.runtime.surface(service.runtime.rollback(service.store.session(id), archive))

    @app.get('/api/sessions/{id}/export')
    def export(id: str):
        s = service.runtime.surface(service.store.session(id))
        chapters = s.get('conversations', [])
        text = s['title'] + '\n\n' + '\n\n'.join(a['title'] + '\n\n' + '\n\n'.join(t['reply'] for t in a['turns']) for a in chapters if a['turns'])
        return Response(text, media_type='text/plain; charset=utf-8', headers={'Content-Disposition': 'attachment; filename="TextingDream.txt"'})

    @app.post('/api/sessions/{id}/polish')
    async def polish(id: str):
        return await service.polish(id)

    @app.get('/api/inner/package')
    def package(revision: str | None = None):
        return service.runtime.package(revision)

    @app.get('/api/inner/generators')
    def generator_drafts():
        return service.store.all('world_generation')

    @app.get('/api/inner/atlas')
    def author_atlas():
        from .atlas import project_atlas
        service.runtime.reload_documents()
        return project_atlas(service.runtime.package()['story'])

    @app.get('/api/inner/world-resources')
    def world_resources():
        return {'text':(ROOT / '资源使用说明.md').read_text(encoding='utf-8')}

    @app.get('/api/inner/generators/{id}/atlas')
    def generator_atlas(id: str):
        return service.world_generator.preview_atlas(id)

    @app.post('/api/inner/generators')
    async def generator_generate(req: GenerateWorldRequest):
        async with service.lock:
            return await service.world_generator.generate(req)

    @app.put('/api/inner/generators/{id}')
    async def generator_edit(id: str, req: GeneratorEdit):
        async with service.lock:
            return service.world_generator.edit(id, req.data)

    @app.post('/api/inner/generators/{id}/save')
    async def generator_save(id: str):
        async with service.lock:
            return service.world_generator.save(id)

    @app.get('/api/inner/packages')
    def packages():
        return service.runtime.list_packages()

    @app.post('/api/inner/packages/{folder}/activate')
    async def activate_package(folder: str):
        async with service.lock:
            return {'revision':service.runtime.activate_package(folder)}

    @app.get('/api/inner/traces')
    def traces():
        return [{**{k: v for k, v in t.items() if k not in ('request', 'response')},
                 'cache':cache_usage(t.get('usage'))} for t in reversed(service.store.all('trace'))]

    @app.get('/api/inner/traces/{id}')
    def trace(id: str):
        record = service.store.get('trace', id)
        if not record:
            raise ValueError('调用记录不存在或已过保留上限')
        return record

    @app.delete('/api/inner/traces')
    def clear_traces():
        service.store.clear_traces()
        return {'ok': True}

    @app.put('/api/inner/package')
    async def edit_package(req: PackageEdit):
        async with service.lock:
            revision = service.runtime.commit_package(req.story, req.characters, '作者编辑')
            return {'revision': revision}

    @app.get('/api/inner/versions')
    def versions():
        return [{'id': p['id'], 'note': p['note'], 'created': p['created']} for p in service.store.all('package')]

    @app.post('/api/inner/versions/{id}/restore')
    async def restore_version(id: str):
        async with service.lock:
            p = service.runtime.package(id)
            return {'revision': service.runtime.commit_package(p['story'], p['characters'], '恢复版本 ' + id)}

    @app.get('/api/inner/package/export')
    def package_export():
        return service.runtime.package()

    @app.get('/api/inner/drafts')
    def drafts():
        return service.store.all('draft')

    @app.post('/api/inner/generate')
    async def generate(req: DraftRequest):
        return await service.generate(req)

    @app.post('/api/inner/generate-batch')
    async def generate_batch(req: BatchDraftRequest):
        return await service.generate_batch(req.tasks)

    @app.get('/api/inner/sessions/{id}/recall')
    def recall(id: str, query: str = ''):
        if len(query) > 3000:
            raise ValueError('检索文本过长')
        s = service.store.session(id)
        prefs = service.preferences()
        return {'method': 'local_sparse_tfidf', 'results': service.runtime.recall.search(
            id, query, dialogue_records(s, service.runtime.package(s['revision'])),
            k=prefs['memory_k'], threshold=prefs['recall_threshold'])}

    @app.put('/api/inner/drafts/{id}')
    async def edit_draft(id: str, req: Element):
        async with service.lock:
            d = service.store.get('draft', id)
            if not d or d['status'] != 'draft':
                raise ValueError('只能编辑待审核候选')
            d['element'] = req.model_dump()
            service.store.put('draft', id, d)
            return d

    @app.post('/api/inner/drafts/{id}/{action}')
    async def process_draft(id: str, action: str):
        async with service.lock:
            draft = service.store.get('draft', id)
            if not draft:
                raise ValueError('候选不存在')
            if action == 'approve':
                return {'revision': service.runtime.approve(draft)}
            if action == 'reject' and draft['status'] == 'draft':
                draft['status'] = 'rejected'
                service.store.put('draft', id, draft)
                return draft
            raise ValueError('无效操作')

    @app.get('/api/inner/sessions/{id}')
    def inspect_session(id: str):
        return service.store.session(id)

    @app.get('/api/inner/sessions/{id}/development')
    def developments(id: str):
        s=service.store.session(id)
        return {'state':s.get('development',{}),'log':s.get('development_log',[]),
                'drafts':[d for d in service.store.all('development_draft') if d['session_id']==id]}

    @app.post('/api/inner/sessions/{id}/development')
    async def propose_development(id: str, req: DevelopmentRequest):
        return await service.development.propose(id,req)

    @app.post('/api/inner/development/{id}/{action}')
    async def review_development(id: str, action: str):
        if action not in ('approve','reject'):
            raise ValueError('无效审核操作')
        return await service.development.review(id,action=='approve')

    @app.get('/api/inner/sessions/{id}/context/{audience}')
    def inspect_context(id: str, audience: str):
        return service.runtime.context(service.store.session(id), audience, '', service.preferences())

    @app.get('/api/inner/corpus')
    def corpus():
        return service.store.get('corpus', 'general')

    @app.put('/api/inner/corpus')
    def set_corpus(req: Corpus):
        service.store.put('corpus', 'general', req.model_dump())
        return {'ok': True}

    # ---- element assembly: author side (token protected). Library is read-only. ----
    # No endpoint takes a filesystem path: the library is chosen by server config only.
    @app.get('/api/inner/elements/library')
    def element_library():
        return service.elements.status()

    @app.get('/api/inner/elements/search')
    def element_search(text: str = '', tag: str = '', all_tag: str = '', namespace: str = '',
                       limit: int = 20, offset: int = 0):
        return service.elements.search(
            text=text or None,
            tags_any=[item for item in tag.split(',') if item],
            tags_all=[item for item in all_tag.split(',') if item],
            namespace=namespace or None, limit=limit, offset=offset)

    @app.get('/api/inner/elements/tags')
    def element_tags(namespace: str = '', limit: int = 60):
        return service.elements.tags(namespace=namespace or None, limit=limit)

    @app.get('/api/inner/elements/item/{namespace}/{element_id}')
    def element_detail(namespace: str, element_id: str, version: int | None = None):
        return service.elements.get(namespace, element_id, version=version)

    @app.get('/api/inner/elements/item/{namespace}/{element_id}/versions')
    def element_versions(namespace: str, element_id: str):
        return service.elements.versions(namespace, element_id)

    @app.get('/api/inner/elements/drafts')
    def element_drafts():
        return [{'id': d['id'], 'created': d['created'], 'updated': d['updated'],
                 'revision': d['revision'], 'status': d['status'],
                 'count': len(d.get('elements', [])),
                 'committed_revision': d.get('committed_revision'),
                 'note': d.get('note', '')} for d in service.elements.list_drafts()]

    @app.post('/api/inner/elements/drafts')
    async def element_draft_save(req: dict):
        async with service.lock:
            return service.elements.save_draft(
                req.get('elements') or [], req.get('rules') or [],
                draft_id=req.get('draft_id'), expected_revision=req.get('expected_revision'),
                note=req.get('note') or '')

    @app.get('/api/inner/elements/drafts/{draft_id}')
    def element_draft(draft_id: str):
        return service.elements.get_draft(draft_id)

    @app.post('/api/inner/elements/recover')
    async def element_recover():
        # 作者显式恢复：把上一进程崩溃留下的 committing 预留放回草稿（revision 不回退）。
        async with service.lock:
            return service.elements.recover_reservations()

    @app.post('/api/inner/elements/drafts/{draft_id}/preview')
    def element_preview(draft_id: str):
        draft = service.elements.get_draft(draft_id)
        return service.elements.preview(draft['elements'], draft['rules'])

    @app.post('/api/inner/elements/drafts/{draft_id}/commit')
    async def element_commit(draft_id: str, req: dict | None = None):
        body = req or {}
        async with service.lock:
            return service.elements.commit(
                draft_id,
                expected_draft_revision=body.get('expected_draft_revision'),
                expected_story_revision=body.get('expected_story_revision'),
                note=body.get('note') or '')

    @app.get('/api/inner/elements/manifest')
    def element_manifest(revision: str = '', audience: str = 'author', session: str = ''):
        if audience == 'author':
            return service.elements.author_view(revision or None)
        if not session:
            raise ValueError('公开/角色投影需要指定旅程（session）')
        snapshot = service.store.session(session)
        return {'audience': audience,
                'elements': service.elements.player_view(revision or None, audience, snapshot)}

    @app.get('/api/settings/api')
    def api_config():
        return service.provider.public_config()

    @app.put('/api/settings/api')
    def set_api(req: ApiSettings):
        service.provider.configure(req.model_dump())
        return service.provider.public_config()

    @app.post('/api/settings/api/test')
    async def test_api():
        if service.provider.config()['offline']:
            service.provider.offline_trace('connection_test', {}, '离线模式可用')
            return {'message': '离线模式可用；未访问远程 API'}
        text, usage = await service.provider.complete('回复连接成功。', {'test': True}, scope='connection_test')
        return {'message': text, 'usage': usage}

    @app.put('/api/settings/preferences')
    def preferences(req: Preferences):
        service.store.put('settings', 'preferences', req.model_dump())
        service.provider.configure({'thinking_mode': 'enabled' if req.surface_thinking else 'disabled'})
        return req

    return app
