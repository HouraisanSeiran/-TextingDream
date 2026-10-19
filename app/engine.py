import json, os
from pathlib import Path
import httpx
from .models import CharacterPackage, StoryAssembly, StoryPackage, WorldState, EventRecord

ROOT = Path(__file__).resolve().parents[1]

def load_assembly() -> StoryAssembly:
    story_path = ROOT / 'world_packages' / '玄陆_世界包.json'
    character_path = ROOT / 'character_packages' / 'xuanlu_初始角色包.json'
    story_data = json.loads(story_path.read_text(encoding='utf-8'))
    character_data = json.loads(character_path.read_text(encoding='utf-8'))
    story = StoryPackage.model_validate(story_data)
    characters = CharacterPackage.model_validate(character_data)
    if story.character_package_id != characters.id:
        raise ValueError(f'故事包需要角色包 {story.character_package_id}，实际加载的是 {characters.id}')
    assembly = StoryAssembly(story=story, characters=characters)
    validate_story(assembly)
    return assembly

def load_story() -> StoryPackage:
    """兼容旧调用；新代码应使用 load_assembly。"""
    return load_assembly().story

def validate_story(assembly: StoryAssembly) -> None:
    """在启动时拒绝会造成状态漂移的故事包引用。"""
    card = assembly.story
    characters = assembly.characters.characters
    location_ids = {x.id for x in card.locations}
    character_ids = {x.id for x in characters}
    event_ids = {x.id for x in card.events}
    if len(location_ids) != len(card.locations):
        raise ValueError('故事包包含重复地点 ID')
    if len(character_ids) != len(characters):
        raise ValueError('角色包包含重复角色 ID')
    if len(event_ids) != len(card.events):
        raise ValueError('故事包包含重复事件 ID')
    for location in card.locations:
        unknown = set(location.neighbors) - location_ids
        if unknown:
            raise ValueError(f'地点 {location.id} 引用了不存在的邻接地点: {sorted(unknown)}')
    for event in card.events:
        if event.location_id not in location_ids:
            raise ValueError(f'事件 {event.id} 的地点不存在: {event.location_id}')
        unknown_characters = set(event.participants) - character_ids
        if unknown_characters:
            raise ValueError(f'事件 {event.id} 引用了不存在的角色: {sorted(unknown_characters)}')
        unknown_events = set(event.next_events) - event_ids
        if unknown_events:
            raise ValueError(f'事件 {event.id} 引用了不存在的后继事件: {sorted(unknown_events)}')

def initial_state(assembly: StoryAssembly) -> WorldState:
    card = assembly.story
    start = card.locations[0].id
    return WorldState(story_id=card.id, current_location=start,
                      explored_locations=[start],
                      character_beliefs={x.id: list(x.beliefs) for x in assembly.characters.characters})

def move(card: StoryPackage, state: WorldState, destination: str) -> tuple[bool, str]:
    target = next((x for x in card.locations if x.id == destination), None)
    current = next(x for x in card.locations if x.id == state.current_location)
    if not target or destination not in current.neighbors:
        return False, '这条路目前无法通行。'
    state.current_location = destination
    state.explored_locations = sorted(set(state.explored_locations + [destination]))
    state.time += 1
    return True, f'你来到了{target.name}。'

async def generate_reply(card: StoryPackage, state: WorldState, message: str, events: list[EventRecord]) -> str:
    key = os.getenv('DEEPSEEK_API_KEY')
    if not key:
        reply = f'（本地模拟）你在{next(x.name for x in card.locations if x.id == state.current_location)}说：“{message}”\n\n风声停了一瞬，故事等待你的下一步。'
        events.append(EventRecord(id=len(events)+1, player_input=message, reply=reply, location=state.current_location, time=state.time))
        return reply
    loc = next(x for x in card.locations if x.id == state.current_location)
    recent = '\n'.join(f'玩家：{e.player_input}\n叙述：{e.reply}' for e in events[-3:])
    prompt = f'''你是“{card.title}”的叙事引擎。只用第一人称，简短回应（150字以内）。不要输出数值、规则或系统提示。\n世界观：{card.premise}\n当前地点：{loc.name}：{loc.description}\n游戏时间：{state.time}\n近期事件：{recent}\n玩家输入：{message}'''
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(os.getenv('DEEPSEEK_BASE_URL','https://api.deepseek.com') + '/chat/completions',
            headers={'Authorization': f'Bearer {key}'},
            json={'model': os.getenv('DEEPSEEK_MODEL','deepseek-chat'), 'messages':[{'role':'user','content':prompt}], 'temperature':0.8})
        response.raise_for_status()
        reply = response.json()['choices'][0]['message']['content']
        events.append(EventRecord(id=len(events)+1, player_input=message, reply=reply, location=state.current_location, time=state.time))
        return reply
