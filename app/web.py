import functools
import secrets
from pathlib import Path
from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from .contracts import ApiSettings, Corpus, DraftRequest, BatchDraftRequest, Element, IntentRequest, Move, NewSession, PackageEdit, Preferences, Turn, DevelopmentRequest, WaitRequest
from .recall import dialogue_records
from .cache_metrics import cache_usage
from . import token_usage
from . import local_rules
import copy
from .service import Service
from .storage import Store
from .knowledge import notebook
from .world_generator import GenerateWorldRequest, GeneratorEdit
from .reply_direction import ReplyDirectionRequest, DIRECTIONS, draft_reply
from .world_pipeline import WorldPipeline, PipelineRequest, StageEdit
from . import civ_atlas_snapshot, map_import, towns, play_map
from . import spatial_draft
from . import native_worlds
from . import native_starts
from . import npc_cards

from .town_schema import (AdoptRequest, AdvanceRequest, PresetRequest, PublishRequest,
                          StageEditRequest, STAGE_NAMES,
                          DraftRequest as TownDraftRequest)

ROOT = Path(__file__).resolve().parents[1]


# ------------------------------------------------------- civ-atlas import requests
# Every field is bounded and typed. An unknown key is refused rather than ignored, so a
# typo cannot silently become "use the default", and a bool or a string can never stand in
# for a number (the sampler would otherwise coerce it).
class _Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class MapImportDeclared(_Strict):
    """Query flags for the import POST. The payload itself is the raw request body."""
    note: str = Field(default='', max_length=map_import.MAX_NOTE_CHARS)
    commit: str = Field(default='', max_length=40, pattern=r'^([0-9a-f]{7,40})?$')
    generator_version: int | None = Field(default=None, ge=1, le=1_000_000, strict=True)


class MapSampleRequest(_Strict):
    lon: float = Field(ge=-180.0, le=180.0, strict=True, allow_inf_nan=False)
    lat: float = Field(ge=-90.0, le=90.0, strict=True, allow_inf_nan=False)
    window_px: int = Field(default=3, ge=3, le=15, strict=True)
    radius_km: float = Field(default=map_import.DEFAULT_RADIUS_KM, ge=1000.0, le=20000.0,
                             strict=True, allow_inf_nan=False)


class MapTownInputRequest(MapSampleRequest):
    author: dict = Field(min_length=1, max_length=64)


class SpatialDraftBody(_Strict):
    """One spatial draft, exactly as ``spatial_draft.parse_request`` reads it.

    The geometry schema has one home (the service) and is not restated here: this model only
    says "there is a body", so the strict validation of unknown keys, NaN/bool numbers and
    the vertex budget stays in one place instead of drifting into two.
    """
    draft: dict = Field(min_length=1, max_length=64)


class NativeStartBody(_Strict):
    """一份开局候选。形状由 ``native_starts.build_body`` 一处校验。"""
    draft: dict = Field(min_length=1, max_length=64)


class NativeStartConfirm(_Strict):
    expected_revision: int = Field(ge=0, strict=True)


class HistoryPreviewRequest(_Strict):
    """Start a replay. The **import id** is the only source reference accepted.

    There is deliberately no record, file path, URL or client-supplied civ payload here:
    the server looks the record up itself, and its own pin decides what may be replayed.
    """
    import_id: str = Field(min_length=3, max_length=64,
                           pattern=r'^(?:sn|mi)_[0-9a-f]{6,32}$')
    base_year: float = Field(strict=True, allow_inf_nan=False)
    branch: str | None = Field(default=None, max_length=120)
    window: list[int] | None = Field(default=None, min_length=2, max_length=2)
    max_events: int | None = Field(default=None, ge=1, le=4000, strict=True)
    max_entities: int | None = Field(default=None, ge=1, le=4000, strict=True)


class HistoryReviewRequest(_Strict):
    entries: list[dict] = Field(min_length=1, max_length=2000)
    disclosure: dict | None = Field(default=None, max_length=8)
    local_links: dict | None = Field(default=None, max_length=512)
    # The revision the author read; without it a second tab could overwrite the first.
    expected_revision: int = Field(ge=0, strict=True)


class HistoryCommitRequest(_Strict):
    expected_revision: int = Field(ge=0, strict=True)
    what_changed: str = Field(default='', max_length=400)


class HistoryAdoptRequest(_Strict):
    # The revision the author reviewed against. Never taken from "whatever is current now".
    expected_story_revision: str = Field(min_length=1, max_length=64)
    note: str = Field(default='', max_length=400)


class HistoryMapLinkRequest(_Strict):
    """Author's explicit "this import is the map my package starts on".

    Separate from adopting history: adopting history never writes ``mechanics.map``, so the
    author has to say this on purpose.
    """
    import_id: str = Field(min_length=3, max_length=64,
                           pattern=r'^(?:sn|mi)_[0-9a-f]{6,32}$')
    expected_story_revision: str = Field(min_length=1, max_length=64)
    fog_radius_km: float = Field(default=300.0, ge=10.0, le=2000.0, strict=True,
                                 allow_inf_nan=False)
    note: str = Field(default='', max_length=400)


class SpatialDraftUpdateRequest(SpatialDraftBody):
    # 乐观并发凭据在 API 层就是必填：没有它就不允许改一份已存的草稿。
    expected_revision: int = Field(ge=0, strict=True)


class SpatialDraftConvertRequest(_Strict):
    """Author declarations for a conversion.

    There is deliberately **no** ``sample`` field: a client-supplied sample is not part of
    this contract at all, so ``extra='forbid'`` refuses it with a 422 before any code runs.
    The sample is recomputed here from the draft's own saved point, in a worker thread.
    """
    expected_revision: int = Field(ge=0, strict=True)
    author: dict = Field(min_length=1, max_length=64)


def create_app(db_path=None):
    app = FastAPI(title='TextingDream')
    service = Service(Store(db_path or ROOT / 'data/textiledream.sqlite3'), ROOT)
    app.state.service = service
    pipeline=WorldPipeline(service)
    token = secrets.token_urlsafe(32)
    app.mount('/static', StaticFiles(directory=ROOT / 'app/static'), name='static')
    app.mount('/maps', StaticFiles(directory=ROOT / 'assets/maps'), name='maps')
    from DreamTerra import service as dreamterra
    dreamterra.install(app, service, ROOT)

    # ---- 原生宿主（civ-atlas）前端产物 ---------------------------------
    # 独立前缀 /native-map：绝对不能挂到 /static 下面，那里已经被上面的旧壳抢占了。
    # 产物是本地构建的 external/civ-atlas/dist-dream（不入源码仓）。缺构建不是启动崩溃，
    # 而是一个可操作的 503；这里不装依赖、不启 Vite。
    native_map_dir = ROOT / 'external' / 'civ-atlas' / 'dist-dream'

    def _native_map_missing():
        return JSONResponse({'detail': '原生地图前端还没有构建：请在 external/civ-atlas '
                                       '运行前端构建，产出 dist-dream/ 后再访问；'
                                       '服务不会自动安装依赖或启动构建进程'},
                            status_code=503)

    if (native_map_dir / 'dream-host.js').is_file():
        app.mount('/native-map', StaticFiles(directory=native_map_dir, html=True),
                  name='native-map')
    else:
        # 只注册入口路径，让缺构建的情况给出明确说明（而不是 404/启动失败）。
        @app.get('/native-map/dream-host.js')
        @app.get('/native-map/dream-host.css')
        @app.get('/native-map')
        @app.get('/native-map/')
        def native_map_unbuilt():
            return _native_map_missing()

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
        # img-src 必须允许 blob:：作者侧受保护路由（带 token 头）取回的预览图是
        # ObjectURL，不是 data: 也不是同源文件，否则地图一像素都画不出来。
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; frame-ancestors 'none'"
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
        sessions = [{'id': s['id'], 'title': s['title']} for s in service.store.all('session')
                    if service.store.get('package', s.get('revision'))]
        # 没有世界时给**明确的空态**：world 为 null、can_start 为 false，而不是造一个假故事。
        # 设置、语料、百科与地图导入都独立于世界，仍照常返回。
        empty = service.runtime.empty_state()
        return {'token': token, 'sessions': sessions,
                'preferences': service.preferences(),
                'api': service.provider.public_config(),
                'world': empty['world'], 'packages': empty['packages'],
                'can_start': empty['can_start'], 'world_reason': empty['reason']}

    @app.post('/api/sessions')
    async def new_session(req: NewSession):
        async with service.lock:
            return service.runtime.surface(
                service.runtime.new_session(req.title, req.mode, profile_id=req.profile))

    @app.get('/api/start-profiles')
    def start_profiles():
        # Player-facing: only what a new journey may choose between. A package with no
        # start profiles returns an empty list and the UI hides the section entirely.
        from . import start_profiles as start_rules
        story = service.runtime.package()['story']
        cfg = start_rules.config(story)
        if cfg is None:
            return {'configured': False, 'profiles': []}
        return {'configured': True, 'default': cfg.default_profile,
                'profiles': [{'id': p.id, 'title': p.title, 'summary': p.summary,
                              'identity': p.identity, 'goal': p.goal,
                              'location': p.location,
                              'items': list(p.items), 'wallet': dict(p.wallet),
                              'known': [k.text for k in p.known if k.public]}
                             for p in cfg.profiles],
                'note': '起点由引擎一次性写入；不会通过正文补发物品或钱'}

    @app.get('/api/sessions/{id}/opening')
    def journey_opening(id: str):
        from . import start_profiles as start_rules
        s = service.store.session(id)
        return {'opening': start_rules.surface(s, service.runtime.package(s['revision'])['story'])}

    @app.get('/api/sessions/{id}/traits')
    def journey_traits(id: str):
        # Player projection only: public references, never hidden ones, never the payload.
        from . import traits as traits_rules
        s = service.store.session(id)
        p = service.runtime.package(s['revision'])
        hero = next(c for c in p['characters']['characters'] if c['id'] == s['hero'])
        if s.get('hero_traits'):
            hero = {**hero, 'trait_refs': s['hero_traits']}
        rows = traits_rules.projections(p['story'], hero, 'player')
        authored = traits_rules.projections(p['story'], hero, s['hero'])
        return {'traits': rows,
                'count': len(rows),
                'note': '只列玩家能观察到的特质；隐藏特质与模板全文不在玩家接口返回',
                'author_count': len(authored)}

    @app.get('/api/sessions/{id}/pressure')
    def journey_pressure(id: str):
        # Player-facing: only warnings this viewpoint already knows. Never stage counts,
        # never thresholds, never results that have not happened.
        from . import pressure as pressure_rules
        s = service.store.session(id)
        story = service.runtime.package(s['revision'])['story']
        return {'known': pressure_rules.known(s, story, 'player')}

    @app.post('/api/sessions/{id}/intent')
    async def journey_intent(id: str, req: IntentRequest):
        # Read-only: turns an intention into bounded candidates. Saves nothing, so a
        # GET-style exploration can never advance state.
        from . import free_actions
        s = service.store.session(id)
        p = service.runtime.package(s['revision'])
        # 没有进行中的事件时，本地行动（如休息）仍然有候选——只是不能有事件动作。
        node = service.runtime.node(s) if s['active'] else None
        from . import scene_judgment
        if scene_judgment.enabled(p['story']):
            return await scene_judgment.intent(service, s, p['story'], node, req.text)
        result = free_actions.suggest(s, p['story'], node, req.text)
        if node is None and not result['matched']:
            result['note'] = ('当前没有进行中的事件；只有本地行动（休息等）可作为候选，'
                              '其余输入只会作为对话或描述')
        return result

    @app.get('/api/sessions/{id}/confirm/{action_id}')
    def journey_confirm(id: str, action_id: str):
        from . import free_actions
        s = service.store.session(id)
        p = service.runtime.package(s['revision'])
        # 没有进行中的事件时只有本地行动（node=None）；事件动作仍只在活动中可用。
        node = service.runtime.node(s) if s['active'] else None
        return free_actions.describe(s, p['story'], node, action_id)

    @app.get('/api/sessions/{id}')
    def surface(id: str):
        return service.runtime.surface(service.store.session(id))

    # ---- player map: read-only projection + fog-masked basemap ----
    # The map comes from the revision this journey is bound to. Neither route takes an
    # import id, a coordinate, a layer or a size from the client, and neither writes a
    # session: polling the map or reloading the page cannot move state_version.
    def _play_map_context(session_id):
        s = service.store.session(session_id)
        story = service.runtime.package(s['revision'])['story']
        status, context = play_map.resolve(service.store, _import_root(), story)
        return s, story, status, context

    @app.get('/api/sessions/{id}/play-map')
    def play_map_projection(id: str):
        terrain_context = dreamterra.context(service.store, service.runtime, id)
        if terrain_context:
            return dreamterra.player_projection(terrain_context, id)
        s, story, status, context = _play_map_context(id)
        return play_map.projection(s, story, status=status, context=context, session_id=id)

    @app.get('/api/sessions/{id}/play-map/basemap.png')
    def play_map_basemap(id: str):
        terrain_context = dreamterra.context(service.store, service.runtime, id)
        if terrain_context:
            _, _, world, arrays, _, mask, _ = terrain_context
            return Response(dreamterra.image(world, arrays, mask), media_type='image/png',
                            headers={'X-Play-Map': 'fog-masked'})
        s, story, status, context = _play_map_context(id)
        if status != play_map.STATUS_OK:
            # No fallback image and no unrelated basemap: the JSON says why.
            return JSONResponse({'detail': context.get('reason') or '地图不可用'},
                                status_code=404)
        places = play_map.visible_places(s, story)
        png = play_map.basemap_png(context, places, context.get('link'))
        if png is None:
            return JSONResponse({'detail': '还没有带经纬度的已知位置，没有底图可画'},
                                status_code=404)
        response = Response(content=png, media_type='image/png')
        response.headers['X-Play-Map'] = 'fog-masked'
        return response

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

    # ---- history adoption: author side (token protected). No model is called here. ----
    # Every state-changing call needs the token, and so does reading a preview: a preview is
    # an author-side draft (unpublished history), never public.
    def _import_record(import_id):
        record = service.store.get('map_import', import_id)
        if not record:
            raise ValueError('找不到这个导入记录（%s）；请先导入地图' % import_id)
        if not record.get('sha256'):
            raise ValueError('该导入记录没有服务端算出的内容哈希，不能回放历史')
        return record

    @app.get('/api/inner/history/imports')
    def history_imports():
        """Imports that can be replayed, plus what each actually carries."""
        rows = []
        for record in service.store.all('map_import'):
            rows.append({'import_id': record.get('id'), 'sha256': record.get('sha256'),
                         'bytes': record.get('bytes'),
                         'world_id': (record.get('source') or {}).get('world_id'),
                         'parts': [part.get('name') for part in record.get('parts') or []],
                         'file': record.get('file')})
        # 世界还没建时这两个字段就是 null：地图导入与历史预览本身不依赖已有世界。
        world = None
        if service.runtime.has_world():
            package = service.runtime.package()
            world = {'story_revision': package['id'],
                     'story_id': package['story'].get('id')}
        return {'imports': rows, 'story_revision': (world or {}).get('story_revision'),
                'story_id': (world or {}).get('story_id')}

    @app.post('/api/inner/history/previews')
    async def history_preview(req: HistoryPreviewRequest):
        record = _import_record(req.import_id)
        # Decoding a 4.6 MB part is CPU-bound: keep it off the event loop and out from under
        # the turn lock (nothing here writes a package).
        return await run_in_threadpool(
            service.history.preview, record, base_year=req.base_year, branch=req.branch,
            window=tuple(req.window) if req.window else None,
            max_events=req.max_events, max_entities=req.max_entities)

    @app.get('/api/inner/history/previews/{preview_id}')
    def history_preview_get(preview_id: str):
        return service.history.get_preview(preview_id)

    @app.get('/api/inner/history/previews/{preview_id}/page')
    def history_preview_page(preview_id: str, category: str, page: int = 0, size: int = 25):
        return service.history.page(preview_id, category, page=page, size=size)

    @app.post('/api/inner/history/previews/{preview_id}/review')
    def history_review(preview_id: str, req: HistoryReviewRequest):
        return service.history.review(preview_id, entries=req.entries,
                                     disclosure=req.disclosure,
                                     local_links=req.local_links,
                                     expected_revision=req.expected_revision)

    @app.post('/api/inner/history/previews/{preview_id}/commit')
    def history_commit(preview_id: str, req: HistoryCommitRequest):
        return service.history.commit(preview_id, what_changed=req.what_changed,
                                     expected_revision=req.expected_revision)

    @app.get('/api/inner/history/snapshots/{snapshot_id}')
    def history_snapshot(snapshot_id: str):
        return service.history.authored(snapshot_id)

    @app.post('/api/inner/history/snapshots/{snapshot_id}/adopt')
    async def history_adopt(snapshot_id: str, req: HistoryAdoptRequest):
        async with service.lock:
            return service.history.adopt(snapshot_id, req.expected_story_revision,
                                        req.note)

    @app.post('/api/inner/history/map-link')
    async def history_map_link(req: HistoryMapLinkRequest):
        """Explicit author action: bind this import as the package's starting map.

        Kept apart from history adoption on purpose — adopting history never touches
        ``mechanics.map``, and this never adopts history.
        """
        async with service.lock:
            return await run_in_threadpool(
                service.history.link_start_map, req.import_id,
                req.expected_story_revision, fog_radius_km=req.fog_radius_km,
                note=req.note)

    # ---- civ-atlas data imports: author side (token protected). No model is called. ----
    # Two accepted shapes, both exported by the author themselves: a 16-bit heightmap PNG
    # (elevation + sea/land only) and a .civsnap written by tools/civ_atlas_export.js
    # (per-cell elevation / water / temperature / precipitation / biome). A save-file JSON
    # is refused by the adapter with the reason. Nothing here writes a story package or
    # moves the active pointer: an import only becomes a town through the ordinary draft
    # endpoints the author already reviews.
    def _sample_record(record, lon, lat, window_px, radius_km):
        # Same data root as the import that produced this record: a store built on a
        # temporary database must read its payloads from beside that database, not from
        # the repository's data/ directory.
        root = _import_root()
        if record.get('format') == civ_atlas_snapshot.FORMAT:
            world = civ_atlas_snapshot.load_world(root, record)
            return civ_atlas_snapshot.sample_region(world, lon, lat, window_px, radius_km)
        heightmap = map_import.load_heightmap(root, record)
        return map_import.sample_region(heightmap, lon, lat, window_px, radius_km)

    @app.get('/api/inner/map-imports')
    def map_import_list():
        return [map_import.summary(row) for row in map_import.list_imports(service.store)]

    # ---- 原生宿主数据桥：只读，只给作者填 -----------------------------
    # 三个路由都靠同一个作者 token；**没有**客户端参数能把玩家升级成读原件。
    # 字节路径与哈希校验都在 ``native_worlds`` 里，web 只负责权限与响应头。
    @app.get('/api/inner/native-worlds')
    def native_world_list():
        return native_worlds.listing(service.store)

    @app.get('/api/inner/native-worlds/{import_id}')
    def native_world_detail(import_id: str):
        return native_worlds.detail(service.store, service.runtime, import_id)

    @app.get('/api/inner/native-worlds/{import_id}/snapshot')
    def native_world_snapshot(import_id: str):
        data, record = native_worlds.snapshot_bytes(
            service.store, Path(service.store.path).resolve().parent, import_id)
        # 只给原件字节；文件名来自服务端生成的内容哈希，不接客户端任何输入。
        return Response(content=data, media_type=native_worlds.SNAPSHOT_MEDIA_TYPE,
                        headers={'Content-Disposition':
                                 'attachment; filename="%s"' % record['file']})

    # ---- 从 civ 开局：预览 → 候选 → 作者确认 ---------------------------------
    # 候选阶段不建 package / pointer / session；只有显式 confirm 才走既有事务建包。
    @app.get('/api/inner/native-starts/{import_id}/preview')
    def native_start_preview(import_id: str, base_year: float, branch: str = 'main'):
        return native_starts.preview(service.store, import_id, base_year=base_year,
                                     branch=branch)

    @app.get('/api/inner/native-starts')
    def native_start_list():
        return native_starts.list_all(service.store)

    @app.get('/api/inner/native-starts/{draft_id}')
    def native_start_detail(draft_id: str):
        return native_starts.get(service.store, draft_id)

    @app.post('/api/inner/native-starts')
    def native_start_create(req: NativeStartBody):
        return native_starts.save(service.store, req.draft)

    @app.post('/api/inner/native-starts/{draft_id}/confirm')
    def native_start_confirm(draft_id: str, req: NativeStartConfirm):
        return native_starts.confirm(service.runtime, service.store, draft_id,
                                     expected_revision=req.expected_revision)

    # Imported map payloads live beside the database they belong to, never at a fixed
    # ROOT path: a service built on a temporary store (tests, a sandboxed playthrough)
    # must not drop files into the real project's data/ directory.
    def _import_root():
        return Path(service.store.path).resolve().parent

    @app.post('/api/inner/map-imports')
    async def map_import_create(request: Request, body: MapImportDeclared = Depends()):
        limit = civ_atlas_snapshot.MAX_CONTAINER_BYTES
        declared = request.headers.get('content-length')
        if declared and declared.isdigit() and int(declared) > limit:
            raise ValueError('文件超过 %d MB 上限' % (limit // (1024 * 1024)))
        # Bounded streaming read: a missing or forged Content-Length must not let the
        # process buffer an unbounded body before the size check can run.
        chunks, total = [], 0
        async for chunk in request.stream():
            if not chunk:
                continue
            total += len(chunk)
            if total > limit:
                raise ValueError('文件超过 %d MB 上限' % (limit // (1024 * 1024)))
            chunks.append(chunk)
        data = b''.join(chunks)
        extra = {'commit': body.commit or None, 'generator_version': body.generator_version}
        import_root = _import_root()
        # Decoding a 96 MB container and validating every array is pure CPU with no await
        # inside. Running it inline in an async endpoint would block the event loop for the
        # whole parse — every other request (other journeys' GETs, this UI's own polls)
        # would wait, and taking the lock off would not help at all. So the parse goes to a
        # worker thread; only the short registration below is serialised by the lock.
        if data[:8] == civ_atlas_snapshot.CONTAINER_MAGIC:
            parse = functools.partial(civ_atlas_snapshot.create_import,
                                      service.store, import_root, data, extra)
        elif data[:8] == b'\x89PNG\r\n\x1a\n':
            parse = functools.partial(map_import.create_import,
                                      service.store, import_root, data, body.note, extra)
        else:
            raise ValueError('认不出这个文件：请给 civ-atlas 导出的 16 位高度图 PNG，'
                             '或 tools/civ_atlas_export.js 导出的 .civsnap'
                             '（存档 JSON 只记种子与修改，不含地形，无法导入）')
        record = await run_in_threadpool(parse)
        async with service.lock:
            # Both adapters are idempotent on content hash: a concurrent duplicate already
            # exists as the same row, so re-registering would only rewrite identical bytes.
            existing = service.store.get('map_import', record['id'])
            if existing:
                return map_import.summary(existing)
            if not record.get('created'):
                from datetime import datetime, timezone
                record = {**record,
                          'created': datetime.now(timezone.utc).isoformat(timespec='seconds')}
            service.store.put('map_import', record['id'], record)
        return map_import.summary(record)

    @app.get('/api/inner/map-imports/{import_id}')
    def map_import_detail(import_id: str):
        return map_import.get_import(service.store, import_id)

    @app.get('/api/inner/map-imports/{import_id}/preview.png')
    def map_import_preview(import_id: str, layer: str = 'elevation'):
        record = map_import.get_import(service.store, import_id)
        import_root = _import_root()
        if record.get('format') == civ_atlas_snapshot.FORMAT:
            world = civ_atlas_snapshot.load_world(import_root, record)
            grid = civ_atlas_snapshot.preview_grid(world, max_side=360)
            body = map_import.encode_rgb_preview(
                civ_atlas_snapshot.preview_rgb(grid, layer), grid['width'], grid['height'])
        else:
            # A heightmap carries elevation and a sea/land mask only, so those are the
            # only two layers it can honestly answer; anything else is refused.
            if layer not in ('elevation', 'water'):
                raise ValueError('这份导入只有高程与海陆，没有「%s」图层' % layer)
            grey, info = map_import.preview_png(map_import.load_heightmap(import_root, record))
            body = grey
        response = Response(content=body, media_type='image/png')
        response.headers['X-Map-Layer'] = layer
        return response

    @app.post('/api/inner/map-imports/{import_id}/sample')
    async def map_import_sample(import_id: str, payload: MapSampleRequest):
        record = map_import.get_import(service.store, import_id)
        return _sample_record(record, payload.lon, payload.lat, payload.window_px,
                              payload.radius_km)

    @app.post('/api/inner/map-imports/{import_id}/town-input')
    async def map_import_town_input(import_id: str, payload: MapTownInputRequest):
        record = map_import.get_import(service.store, import_id)
        author = payload.author
        # The sample is always recomputed here: a client-sent sample is never trusted.
        sample = _sample_record(record, payload.lon, payload.lat, payload.window_px,
                                payload.radius_km)
        built = map_import.build_town_input(record, sample, author,
                                            service.runtime.package()['id'])
        return {'sample': sample,
                'input': built['input'].model_dump(mode='json'),
                'provenance': built['provenance'],
                'warnings': built['warnings']}

    # ---- spatial drafts: author-drawn geometry, before any economy exists. ----
    # Token protected like every other /api/inner route. Nothing here publishes a town, moves
    # the story pointer, writes a story package or touches a journey: a draft is stored
    # geometry, and a conversion only hands back a TownInput for the ordinary towns flow.
    @app.get('/api/inner/spatial-drafts')
    def spatial_draft_list():
        return [spatial_draft.summary(row) for row in service.spatial.list()]

    @app.get('/api/inner/spatial-drafts/{draft_id}')
    def spatial_draft_detail(draft_id: str):
        draft = service.spatial.get(draft_id)
        return {**spatial_draft.summary(draft),
                'footprint': draft.get('footprint'),
                'land_use': draft.get('land_use'),
                'conversion': service.spatial.prepare(draft_id)}

    @app.post('/api/inner/spatial-drafts')
    def spatial_draft_create(req: SpatialDraftBody):
        return service.spatial.save(req.draft)

    @app.put('/api/inner/spatial-drafts/{draft_id}')
    def spatial_draft_update(draft_id: str, req: SpatialDraftUpdateRequest):
        return service.spatial.update(draft_id, req.draft, req.expected_revision)

    @app.get('/api/inner/spatial-drafts/{draft_id}/conversion')
    def spatial_draft_conversion(draft_id: str):
        # Pure read: what a conversion would need, and what the author still has to draw.
        return service.spatial.prepare(draft_id)

    @app.post('/api/inner/spatial-drafts/{draft_id}/town-input')
    async def spatial_draft_town_input(draft_id: str, req: SpatialDraftConvertRequest):
        # Sampling re-reads the payload and re-hashes it, which is CPU work: a worker thread,
        # so the event loop keeps answering. No service.lock is held — the only database work
        # is the short read/compare inside spatial_draft itself.
        built = await run_in_threadpool(
            functools.partial(service.spatial.to_town_input, draft_id,
                              author=req.author, expected_revision=req.expected_revision))
        return {**built,
                'note': ('这是空间草稿转换出的 TownInput；没有发布城镇、没有移动故事包指针。'
                         '下一步请用现有城镇草稿流程（四阶段、发布、绑定）。')}

    @app.get('/api/inner/civ-atlas/export-tool')
    def civ_atlas_export_tool():
        path = ROOT / 'tools' / 'civ_atlas_export.js'
        if not path.exists():
            raise ValueError('导出工具文件不在：tools/civ_atlas_export.js')
        return {'source': path.read_text(encoding='utf-8'),
                'path': 'tools/civ_atlas_export.js',
                'note': ('在生成过该世界的 civ-atlas 页面控制台整段粘贴运行；只读 IndexedDB ',
                         '的 results/heads，不联网、不写库、不碰 localStorage')}

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
            if req.expected_version is not None and req.expected_version != s.get('state_version', 0):
                raise ValueError('位置或旅程已更新，请重新选择目的地')
            service.runtime.move(s, req.location_id)
            return service.runtime.surface(s)

    @app.post('/api/sessions/{id}/wait')
    async def wait_local(id: str, req: WaitRequest):
        async with service.lock:
            s=service.store.session(id)
            if s['active']:raise ValueError('请先结束当前事件，再等待时间推进')
            p=service.runtime.package(s['revision'])
            from . import pressure as pressure_rules
            # Same single entry point as turns and travel: local resources, schedules and
            # story pressure all advance against one clock.
            pressure_rules.advance(s,p['story'],p['characters'],req.hours,
                                   effects=service.runtime.effects)
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

    @app.get('/api/inner/token-usage')
    def token_usage_summary(hours: float = 24):
        if not 0.25 <= hours <= 720:
            raise ValueError('统计窗口必须在 0.25 到 720 小时之间')
        return token_usage.summarize(service.store.all('trace'), hours=hours)

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

    @app.get('/api/inner/npc-cards')
    def npc_card_list(session_id: str | None = None):
        session = service.store.session(session_id) if session_id else {}
        if not session_id and not service.store.get('pointer', 'package'):
            return {'revision': None, 'characters': []}
        package = service.runtime.package(session.get('revision'))
        return {'revision': package['id'], 'characters': [
            {'id': c['id'], 'name': c['name'], 'traits': c.get('traits', []),
             'attributes': c.get('attributes', {}),
             'card': npc_cards.NPCCard.model_validate(c.get('npc_card') or {}).model_dump(),
             'configured': c.get('npc_card') is not None,
             'state': npc_cards.project(c, session, 'author')}
            for c in package['characters']['characters'] if c['role'] != '主角']}

    @app.put('/api/inner/npc-cards/{character_id}')
    async def npc_card_save(character_id: str, req: npc_cards.CardEdit):
        async with service.lock:
            package = service.runtime.package()
            if package['id'] != req.revision:
                raise ValueError('故事包已更新，请重新读取角色卡后再保存')
            characters = copy.deepcopy(package['characters'])
            actor = next((c for c in characters['characters'] if c['id'] == character_id), None)
            if actor is None or actor['role'] == '主角':
                raise ValueError('请选择有效的 NPC')
            actor['npc_card'] = req.card.model_dump()
            revision = service.runtime.commit_package(package['story'], characters, '更新 NPC 角色卡：' + actor['name'])
            return {'revision': revision}

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
