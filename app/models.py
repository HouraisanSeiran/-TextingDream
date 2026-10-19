from typing import Literal
from pydantic import BaseModel, Field, ConfigDict
from .drama import DialogueProfile

class Worldview(BaseModel):
    """故事包的最高语义层级；下级内容都受它约束。"""
    model_config = ConfigDict(extra='allow')
    premise: str = ''
    laws: list[str] = Field(default_factory=list)
    chronology: list[dict] = Field(default_factory=list)
    geography: dict = Field(default_factory=dict)
    cultures: list[dict] = Field(default_factory=list)
    information_rules: list[str] = Field(default_factory=list)

class Character(BaseModel):
    id: str
    name: str
    role: Literal['主角', '次要角色']
    traits: list[str] = Field(default_factory=list)
    personality: dict[str, float] = Field(default_factory=dict)
    state: dict[str, float] = Field(default_factory=dict)
    memories: list[str] = Field(default_factory=list)
    beliefs: list[dict] = Field(default_factory=list)
    location_id: str | None = None
    dialogue_profile: DialogueProfile | None = None
    attributes: dict[str,float] = Field(default_factory=dict)

class CharacterPackage(BaseModel):
    """可跨故事复用的角色集合；实体内容不写入故事包。"""
    id: str
    title: str
    description: str = ''
    characters: list[Character] = Field(default_factory=list)
    generation_constraints: dict = Field(default_factory=dict)

class Location(BaseModel):
    id: str
    name: str
    description: str = ''
    neighbors: list[str] = Field(default_factory=list)
    scenes: list[str] = Field(default_factory=list)

class StoryPackage(BaseModel):
    id: str
    title: str
    premise: str
    character_package_id: str
    worldview: Worldview | None = None
    locations: list[Location] = Field(default_factory=list)
    events: list['StoryEvent'] = Field(default_factory=list)
    items: list[dict] = Field(default_factory=list)
    mechanics: dict = Field(default_factory=dict)

class StoryAssembly(BaseModel):
    """一个运行实例由一个故事包和一个角色包装配而成。"""
    story: StoryPackage
    characters: CharacterPackage

class VisibilityRule(BaseModel):
    audience: Literal['player', 'character', 'inner']
    condition: dict = Field(default_factory=dict)
    fields: list[str] = Field(default_factory=list)

class GeneratedElement(BaseModel):
    """里层生成的完整元素；surface_view 是经过可见性判定后的表层投影。"""
    id: str
    kind: Literal['character', 'item', 'place', 'fact', 'rumor', 'event']
    canonical: dict = Field(default_factory=dict)
    beliefs: dict[str, dict] = Field(default_factory=dict)
    player_heard: dict = Field(default_factory=dict)
    visibility_rules: list[VisibilityRule] = Field(default_factory=list)
    surface_view: dict = Field(default_factory=dict)

class StoryEvent(BaseModel):
    id: str
    title: str
    location_id: str
    scene_id: str | None = None
    premise: str = ''
    participants: list[str] = Field(default_factory=list)
    player_goal: str = ''
    hidden_goal: str = ''
    interactive_elements: list[str] = Field(default_factory=list)
    entry_flags: dict[str, bool] = Field(default_factory=dict)
    exit_flag: str = ''
    next_events: list[str] = Field(default_factory=list)

class WorldState(BaseModel):
    story_id: str
    current_location: str
    time: int = 8
    explored_locations: list[str] = Field(default_factory=list)
    flags: dict[str, bool] = Field(default_factory=dict)
    inventory: list[str] = Field(default_factory=list)
    memories: list[dict] = Field(default_factory=list)
    objective_facts: list[dict] = Field(default_factory=list)
    character_beliefs: dict[str, list[dict]] = Field(default_factory=dict)
    player_heard: list[dict] = Field(default_factory=list)
    current_event: str | None = None

class EventRecord(BaseModel):
    id: int
    player_input: str
    reply: str
    location: str
    time: int
    event_id: str | None = None

class StateSnapshot(BaseModel):
    sequence: int
    state: WorldState

class EventArchive(BaseModel):
    """一个事件对应一个可读、可回滚的存档单位。"""
    event_id: str
    title: str
    interactions: list[EventRecord] = Field(default_factory=list)
    before: WorldState
    after: WorldState
    summary: str = ''

class ChatRequest(BaseModel):
    message: str = Field(min_length=1)

class MoveRequest(BaseModel):
    location_id: str

class InnerRequest(BaseModel):
    instruction: str = Field(min_length=1)

class VisibilityRequest(BaseModel):
    element_id: str
    fields: list[str] = Field(default_factory=list)
