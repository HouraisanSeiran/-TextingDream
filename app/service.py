import asyncio
import json
from .contracts import Element, Preferences
from .provider import Provider
from .runtime import Runtime, uid, now
from .prompts import surface_prefix, author_prefix, template
from .knowledge import retrieve, extract_notes, notebook
from . import attributes
from . import scene_judgment


# Offline narration is deterministic and player-visible: a structured behaviour
# decision turned into one short action. It never prints the internal cue instruction,
# never claims to understand the player's input, and never shows personality weights.
OFFLINE_PHRASES = {
    '直接回应': '{name}直接答了一句，没有绕弯。',
    '提出明确请求': '{name}把要求说清楚，等一个准话。',
    '解释立场': '{name}先说明自己的立场，再看对方怎么接。',
    '接话反问': '{name}顺着话头接了一句，反问回来。',
    '温和转折': '{name}语气放缓，把话往别处引了引。',
    '试探需求': '{name}先探了探这边的打算。',
    '调侃缓和': '{name}笑了一声，把话说得轻些。',
    '协商交换': '{name}提了个交换条件，没有把话说死。',
    '委婉拒绝': '{name}没有答应，只留了个余地。',
}
OFFLINE_DEFAULT = '{name}听着，没有马上接话。'
OFFLINE_STILL = '{name}的注意力落在这边，神色未变。'
OFFLINE_EMOTION = {'警惕': '神色收着', '愉快': '神情松了些', '悲伤': '情绪低落',
                   '愤怒': '语气发硬', '恐惧': '有些犹疑'}


def offline_surface(session, result, request):
    """Build a player-visible offline reply from structured decisions only.

    The input channel decides what may be narrated as contact. A thought or a note is
    not spoken aloud, so nothing may be rendered as the NPC "answering" it; only a
    speech turn (or an executed action) can produce a conversational performance.
    """
    observer = (session.get('mode') == 'observer')
    if request.action_id:
        lines = [result['outcome']]
    elif observer:
        lines = ['我看着眼前这一幕。']
    elif request.channel == 'speech':
        lines = ['我把话说出口，等着回应。']
    elif request.channel == 'thought':
        lines = ['我在心里过了一遍这件事，没有出声。']
    elif request.channel == 'note':
        lines = ['我写下几行字，没有让旁人看见。']
    else:
        lines = ['我停下动作，等着眼前的人给出反应。']
    speaking = bool(request.action_id) or (request.channel == 'speech' and not observer)
    for item in result.get('performances', []):
        name = item['public_name']
        if not speaking:
            # Unspoken input: only something observable in the scene, never a reply.
            lines.append(OFFLINE_STILL.format(name=name))
            continue
        line = OFFLINE_PHRASES.get(item['action'], OFFLINE_DEFAULT).format(name=name)
        if item.get('emotion'):
            line += '（' + OFFLINE_EMOTION.get(item['emotion'], '神色有些变化') + '）'
        if item.get('stance') == 'guarded':
            line += '随后往后收了半步。'
        if item.get('unverified_claim'):
            line += '话里的说法我没有当成已证实。'
        lines.append(line)
    if result.get('special_dialogue'):
        lines.append(result['special_dialogue'])
    # Only public reward lines ever reach narration: labels and balances the engine
    # already disclosed. Absent config means no key, so old text is unchanged.
    if result.get('rewards'):
        lines.append('（' + '；'.join(result['rewards']) + '）')
    return '\n\n'.join(x for x in lines if x)


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
        from .towns_store import TownService
        self.towns = TownService(self)
        from .spatial_draft import SpatialDraftService
        self.spatial = SpatialDraftService(self)
        from .element_assembly import ElementAssembly
        self.elements = ElementAssembly(self)
        # 历史采纳（作者侧）。只读自己的三重文档；不碰 runtime 与 story 包，
        # 采纳写包时走 runtime.commit_package（与 towns 同一路）。
        from .world_history_store import WorldHistoryService
        self.history = WorldHistoryService(self.runtime)
        # 启动时恢复被中断的提交预留（包事务日志已由 Runtime 初始化先处理）。
        self.elements.recover_on_startup()

    def preferences(self):
        return {**Preferences().model_dump(), **self.store.get('settings', 'preferences', {}),
                'surface_thinking': self.provider.config()['thinking_mode'] == 'enabled'}

    async def _local_action(self, s, request):
        """没有事件时的本地行动：结算一次，保存一次（CAS）。

        ``Runtime.local_action`` 只在候选副本上执行、不写库；这里在**同一个**短锁内
        把候选写回并 ``save_session`` 一次，所以不存在双重保存或双版 ``state_version``。
        它不追加 ``active['turns']``（没有事件就没有对话轮），也不调用 ``finish_turn``。
        持久化失败时异常向上抛，``state_version`` 不递增，调用方不会以为已执行。
        """
        result, work = self.runtime.local_action(
            s, request.action_id, getattr(request, 'confirm', None))
        self.store.save_session(work)
        self.runtime.session_files(work).save_notes(
            '旅程', work['id'], notebook(work))
        surface = self.runtime.surface(work)
        # 无事件时没有模型叙述。只附上**服务端已确认**的最小回执（时长与资源前后），
        # 不写进 turns/archives、不冒充模型回复；持久化已由上面一次 save_session 完成。
        surface['local_result'] = result.get('local_result')
        return surface

    async def turn(self, session_id, request):
        # Prepare against one saved version, then release the lock while waiting for
        # the model. The final save uses Store's compare-and-swap version check.
        async with self.lock:
            s = self.store.session(session_id)
            expected_version = s.get('state_version', 0)
            # 没有进行中的事件时，带 action_id 的请求是**本地行动**（如休息）：它不产生
            # 对话轮，只在候选副本上结算一次，然后在下方的 CAS 保存里提交。
            # 无 action_id 的普通输入仍走原路（没有事件就没有可叙事的现场）。
            if request.action_id and not s.get('active'):
                return await self._local_action(s, request)
            scene_story = self.runtime.package(s['revision'])['story']
            scene_enabled = scene_judgment.enabled(scene_story)
            scene_node = self.runtime.node(s) if s.get('active') else {}
            scene_action = next((a for a in scene_node.get('actions', [])
                                 if a['id'] == request.action_id), None)
            result = self.runtime.prepare_turn(s, request)
            context = self.runtime.context(s, 'player', request.message, self.preferences())
            # Only the narrator-visible part of the resolved action reaches the model;
            # author-side reward audits stay out of every prompt.
            context['resolved_action'] = self.runtime.resolved_rewards(result)
            corpus = self.store.get('corpus', 'general')['text']
            system = surface_prefix(self.runtime.package(s['revision']), corpus)
            offline = self.provider.config()['offline']
            budget = self.preferences()['context_chars']
        if scene_enabled:
            reply, usage = await scene_judgment.narrate(self, s, request, result, scene_action)
        elif offline:
            reply = offline_surface(s, result, request)
            usage = {'mode': 'offline', 'calls': 0}
            self.provider.offline_trace('surface', {'system': system, 'tail': context}, reply)
        else:
            if len(system) + len(json.dumps(context, ensure_ascii=False)) > budget:
                raise ValueError('上下文超过预算，请减少语料或提高预算')
            reply, usage = await self.provider.complete(system, context, scope='surface')
            usage['calls'] = 1
        async with self.lock:
            latest = self.store.session(session_id)
            if latest.get('state_version', 0) != expected_version:
                raise ValueError('旅程已被其他操作更新，请刷新后重试')
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
