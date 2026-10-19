import asyncio
import copy
import json
from .contracts import Element, Preferences
from .provider import Provider
from .runtime import Runtime, uid, now
from .prompts import surface_prefix, author_prefix, template
from .knowledge import retrieve, extract_notes
from . import attributes


class Service:
    def __init__(self, store, root):
        self.store = store
        self.runtime = Runtime(store, root)
        self.provider = Provider(store)
        self.lock = asyncio.Lock()
        from .world_generator import WorldGenerator
        self.world_generator = WorldGenerator(self)
        from .development import Development
        self.development = Development(self)

    def preferences(self):
        return {**Preferences().model_dump(), **self.store.get('settings', 'preferences', {}),
                'surface_thinking': self.provider.config()['thinking_mode'] == 'enabled'}

    async def turn(self, session_id, request):
        async with self.lock:
            s = self.store.session(session_id)
            result = self.runtime.prepare_turn(s, request)
            context = self.runtime.context(s, 'player', request.message, self.preferences())
            context['resolved_action'] = result
            corpus = self.store.get('corpus', 'general')['text']
            system = surface_prefix(self.runtime.package(s['revision']), corpus)
            if self.provider.config()['offline']:
                reply = result['outcome'] if request.action_id else '我停下脚步，斟酌着接下来要说的话。'
                reply += '\n\n' + result.get('reaction', '') + result['voice'] + result.get('special_dialogue', '')
                usage = {'mode': 'offline', 'calls': 0}
                self.provider.offline_trace('surface', {'system': system, 'tail': context}, reply)
            else:
                if len(system) + len(json.dumps(context, ensure_ascii=False)) > self.preferences()['context_chars']:
                    raise ValueError('上下文超过预算，请减少语料或提高预算')
                reply, usage = await self.provider.complete(system, context, scope='surface')
                usage['calls'] = 1
            # Failure above never persists the candidate state.
            self.runtime.finish_turn(s, request, reply, result, usage)
            return self.runtime.surface(s)

    def example(self, kind, package, stable=False):
        place = package['story']['locations'][0]['id']
        id = 'generated_' + ('example' if stable else uid())
        data = {
            'character': {'id': id, 'name': '待命名旅人', 'public_name': '陌生旅人', 'role': '次要角色', 'occupation': '旅人', 'power_level': 1, 'traits': ['谨慎'], 'personality': {'谨慎': 0.7}, 'attributes':{k:50 for k in attributes.AXES}, 'state': {}, 'location_id': place, 'secret': '尚未向玩家披露的来历'},
            'item': {'id': id, 'name': '旧铜匣', 'description': '表面刻着模糊的纹路。', 'location_id': place, 'secret': '匣底藏着未被发现的纸条'},
            'place': {'id': id, 'name': '商路驿站', 'description': '可供旅人休息的驿站。', 'neighbors': [place], 'scenes': [], 'coordinates': [80, 35]},
            'event': {'id': id, 'title': '驿站短谈', 'location_id': place, 'participants': [], 'player_goal': '了解当地消息', 'hidden_goal': '发现传闻中的矛盾', 'next_events': [], 'entry_flags': {}, 'exit_flag': 'done_' + id, 'max_turns': 6, 'actions': [{'id': 'listen', 'label': '听完这段见闻', 'ends_event': True, 'effects': [], 'success_text': '我将这段见闻记在心里，暂且保留判断。'}]},
            'fact': {'id': id, 'name': '道路消息', 'truth': '道路正在维修，工期尚未确定。', 'rumor': '有人说道路会很快开放。'},
            'worldview': {'premise': package['story']['worldview']['premise']}
        }[kind]
        # Offline examples are explicitly labelled and do not pretend to answer the instruction.
        return {'kind': kind, 'data': data, 'public_fields': [], 'location_id': place, 'known_by': [], 'reveal_flag': None}

    async def generate(self, request):
        self.runtime.reload_documents()
        package = self.runtime.package()
        files = self.runtime.files
        example = self.example(request.kind, package, stable=not self.provider.config()['offline'])
        if self.provider.config()['offline']:
            element, usage = example, {'mode': 'offline', 'calls': 0}
            self.provider.offline_trace('inner', {'instruction': request.instruction, 'kind': request.kind}, element)
        else:
            instruction = author_prefix(package, self.store.get('corpus', 'general')['text'])
            # Bounded authoring context: laws, IDs and requested type, not the whole history.
            context = {'request': request.instruction, 'example': example, 'schema': Element.model_json_schema(),
                       'local_rules':package['story'].get('mechanics',{}).get('local',{}),
                       'attribute_rules':package['story'].get('mechanics',{}).get('attributes',attributes.specification()),
                       'knowledge': retrieve(package['story'], request.instruction, 'author'),
                       'locations': [{'id': l['id'], 'name': l['name']} for l in package['story']['locations']],
                       'characters': [{'id': c['id'], 'name': c['name']} for c in package['characters']['characters']],
                       'items': [{'id': i['id'], 'name': i['name']} for i in package['story']['items']],
                       'events': [{'id': e['id'], 'title': e['title']} for e in package['story']['events']]}
            if len(instruction) + len(json.dumps(context, ensure_ascii=False)) > self.preferences()['context_chars']:
                raise ValueError('创作上下文超过预算，请提高预算或精简设定')
            element, usage = await self.provider.complete(instruction, context, json_mode=True, scope='inner')
            usage['calls'] = 1
        validated = Element.model_validate(element)
        if validated.data.get('id') == 'generated_example':
            new_id = 'generated_' + uid()
            def replace_placeholder(value):
                if isinstance(value, dict):return {k:replace_placeholder(v) for k,v in value.items()}
                if isinstance(value, list):return [replace_placeholder(v) for v in value]
                if value == 'generated_example':return new_id
                if value == 'done_generated_example':return 'done_' + new_id
                return value
            validated = Element.model_validate(replace_placeholder(validated.model_dump()))
        if validated.kind != request.kind:
            raise ValueError('模型返回了不同类型的元素')
        draft = {'id': uid(), 'created': now(), 'instruction': request.instruction, 'base_revision': package['id'],
                 'element': validated.model_dump(), 'status': 'draft', 'usage': usage}
        self.store.put('draft', draft['id'], draft)
        source = {'id': draft['id'], 'scope': 'inner', 'revision': package['id']}
        files.save_notes('里层草稿', draft['id'], extract_notes(json.dumps(validated.model_dump(), ensure_ascii=False, indent=2), source))
        return draft

    async def generate_batch(self, requests):
        async def one(request):
            try:
                return {'kind': request.kind, 'draft': await self.generate(request)}
            except (ValueError, OSError) as error:
                return {'kind': request.kind, 'error': str(error)}
        return {'results': await asyncio.gather(*(one(r) for r in requests))}

    async def polish(self, session_id):
        async with self.lock:
            s = self.store.session(session_id)
            text = '\n\n'.join('## ' + a['title'] + '\n\n' + '\n\n'.join(t['reply'] for t in a['turns']) for a in s['archives'])
            if not text:
                raise ValueError('请先完成至少一个事件')
            if len(text) > self.preferences()['context_chars'] - 2000:
                raise ValueError('归档超出单次润色预算，请提高预算；原始小说仍可导出')
            if self.provider.config()['offline']:
                result, usage = text, {'mode':'offline', 'calls':0}
                self.provider.offline_trace('polish', {'text': text}, result)
            else:
                result, usage = await self.provider.complete(template('polish'), {'text':text}, scope='polish')
                usage['calls'] = 1
            s['polished'] = {'text': result, 'archive_ids': [a['id'] for a in s['archives']], 'usage': usage}
            self.store.save_session(s)
            return {'text': result, 'usage': usage}
