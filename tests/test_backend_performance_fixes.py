import asyncio
import time
from pathlib import Path
from unittest.mock import patch

from app.service import Service
from app.storage import Store
from app.web import create_app, MapSampleRequest
from app import civ_atlas_snapshot


def test_polish_releases_lock_and_rejects_stale_session(tmp_path):
    async def run():
        svc = Service(Store(tmp_path / 'test.sqlite3'), Path.cwd())
        svc.store.save_session({'id': 's', 'archives': [{'id': 'a', 'title': 'a', 'turns': [{'reply': 'text'}]}], 'facts': [], 'beliefs': [], 'heard': []})
        entered, release = asyncio.Event(), asyncio.Event()
        async def complete(*args, **kwargs):
            entered.set(); await release.wait(); return 'polished', {}
        with patch.object(svc.provider, 'config', return_value={**svc.provider.config(), 'offline': False}), patch.object(svc.provider, 'complete', side_effect=complete):
            task = asyncio.create_task(svc.polish('s'))
            await asyncio.wait_for(entered.wait(), 2)
            try:
                async with asyncio.timeout(0.1):
                    async with svc.lock:
                        s = svc.store.session('s'); s['title'] = 'changed'; svc.store.save_session(s)
            finally:
                release.set()
            try:
                await task
            except ValueError:
                pass
            else:
                raise AssertionError('stale polish accepted')
            assert svc.store.session('s')['title'] == 'changed'
    asyncio.run(run())


def test_sampling_does_not_block_event_loop(tmp_path):
    async def run():
        app = create_app(tmp_path / 'test.sqlite3')
        app.state.service.store.put('map_import', 'sn_aabbccddeeff', {'id': 'sn_aabbccddeeff', 'format': civ_atlas_snapshot.FORMAT})
        endpoint = next(r.endpoint for r in app.routes if getattr(r, 'path', '') == '/api/inner/map-imports/{import_id}/sample')
        def load(*args):
            time.sleep(.2); return object()
        with patch('app.web.civ_atlas_snapshot.load_world', side_effect=load), patch('app.web.civ_atlas_snapshot.sample_region', return_value={}):
            task = asyncio.create_task(endpoint('sn_aabbccddeeff', MapSampleRequest(lon=0, lat=0)))
            await asyncio.sleep(.02)
            assert not task.done()
            await task
    asyncio.run(run())




def test_pipeline_rejects_concurrent_edit_while_model_waits(tmp_path):
    from types import SimpleNamespace
    from app.world_pipeline import WorldPipeline

    async def run():
        store = Store(tmp_path / 'pipeline.sqlite3')
        entered, release = asyncio.Event(), asyncio.Event()
        async def complete(*args, **kwargs):
            entered.set(); await release.wait(); return {'result': 'generated'}, {}
        provider = SimpleNamespace(config=lambda: {'offline': False}, complete=complete)
        service = SimpleNamespace(store=store, lock=asyncio.Lock(), provider=provider)
        pipeline = WorldPipeline(service)
        initial = {'id': 'p', 'stages': [], 'request': {'regions': 2, 'output_tokens': 1500}, 'status': 'draft'}
        store.put('world_pipeline', 'p', initial)
        with patch.object(pipeline, 'example', return_value={}), patch.object(pipeline, 'validate', return_value={'result': 'generated'}):
            task = asyncio.create_task(pipeline.advance('p'))
            await asyncio.wait_for(entered.wait(), 2)
            async with asyncio.timeout(.2):
                async with service.lock:
                    changed = store.get('world_pipeline', 'p'); changed['status'] = 'edited'; store.put('world_pipeline', 'p', changed)
            release.set()
            try:
                await task
            except ValueError:
                pass
            else:
                raise AssertionError('concurrent pipeline edit was overwritten')
            assert store.get('world_pipeline', 'p')['status'] == 'edited'
    asyncio.run(run())


def test_development_rejects_stale_snapshot(tmp_path):
    from types import SimpleNamespace
    from app.development import Development

    async def run():
        svc = Service(Store(tmp_path / 'development.sqlite3'), Path.cwd())
        svc.store.save_session({'id': 's', 'facts': [], 'beliefs': [], 'heard': []})
        entered, release = asyncio.Event(), asyncio.Event()
        async def complete(*args, **kwargs):
            entered.set(); await release.wait(); return {}, {}
        development = Development(svc)
        request = SimpleNamespace(character_id='c', instruction='test')
        with patch.object(development, 'context', return_value={}), patch.object(svc.provider, 'config', return_value={**svc.provider.config(), 'offline': False}), patch.object(svc.provider, 'complete', side_effect=complete):
            task = asyncio.create_task(development.propose('s', request))
            await asyncio.wait_for(entered.wait(), 2)
            async with asyncio.timeout(.2):
                async with svc.lock:
                    s = svc.store.session('s'); s['title'] = 'changed'; svc.store.save_session(s)
            release.set()
            try:
                await task
            except ValueError:
                pass
            else:
                raise AssertionError('stale development proposal accepted')
            assert not svc.store.all('development_draft')
    asyncio.run(run())


def test_generator_releases_global_lock(tmp_path):
    from app.world_generator import GenerateWorldRequest

    async def run():
        svc = Service(Store(tmp_path / 'generator.sqlite3'), Path.cwd())
        entered, release = asyncio.Event(), asyncio.Event()
        async def complete(*args, **kwargs):
            entered.set(); await release.wait(); return {}, {}
        with patch.object(svc.elements, 'pin_manifest', return_value=(None, [])), patch.object(svc.provider, 'config', return_value={**svc.provider.config(), 'offline': False}), patch.object(svc.provider, 'complete', side_effect=complete), patch.object(svc.world_generator, 'validate', return_value={}):
            task = asyncio.create_task(svc.world_generator.generate(GenerateWorldRequest(kind='worldview', title='test', instruction='test')))
            await asyncio.wait_for(entered.wait(), 2)
            async with asyncio.timeout(.2):
                async with svc.lock:
                    pass
            release.set()
            draft = await task
            assert svc.store.get('world_generation', draft['id']) == draft
    asyncio.run(run())


def test_town_input_sampling_does_not_block_event_loop(tmp_path):
    from types import SimpleNamespace
    from app.web import MapTownInputRequest

    async def run():
        app = create_app(tmp_path / 'town.sqlite3')
        svc = app.state.service
        svc.store.put('map_import', 'sn_aabbccddeeff', {'id': 'sn_aabbccddeeff', 'format': civ_atlas_snapshot.FORMAT})
        endpoint = next(r.endpoint for r in app.routes if getattr(r, 'path', '') == '/api/inner/map-imports/{import_id}/town-input')
        def load(*args):
            time.sleep(.2); return object()
        built = {'input': SimpleNamespace(model_dump=lambda **kwargs: {}), 'provenance': {}, 'warnings': []}
        with patch('app.web.civ_atlas_snapshot.load_world', side_effect=load), patch('app.web.civ_atlas_snapshot.sample_region', return_value={}), patch('app.web.map_import.build_town_input', return_value=built), patch.object(svc.runtime, 'package', return_value={'id': 'p'}):
            task = asyncio.create_task(endpoint('sn_aabbccddeeff', MapTownInputRequest(lon=0, lat=0, author={'name': 'test'})))
            await asyncio.sleep(.02)
            assert not task.done()
            await task
    asyncio.run(run())
