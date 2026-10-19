from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Turn(Strict):
    message: str = Field(min_length=1, max_length=3000)
    action_id: str | None = None
    channel: Literal['speech','thought','action','note'] = 'action'
    listeners: list[str] | None = Field(default=None,max_length=20)


class WaitRequest(Strict):
    hours: int = Field(ge=1,le=24,strict=True)


class DraftRequest(Strict):
    instruction: str = Field(min_length=1, max_length=4000)
    kind: Literal['character', 'item', 'place', 'event', 'fact', 'worldview']


class Element(Strict):
    kind: Literal['character', 'item', 'place', 'event', 'fact', 'worldview']
    data: dict
    public_fields: list[str] = Field(default_factory=list)
    location_id: str | None = None
    known_by: list[str] = Field(default_factory=list)
    reveal_flag: str | None = None


class ApiSettings(Strict):
    base_url: str = 'https://api.deepseek.com'
    model: str = Field(default='deepseek-flash', min_length=1, max_length=120)
    dialogue_model: str = Field(default='', max_length=120)
    author_model: str = Field(default='', max_length=120)
    thinking_mode: Literal['enabled', 'disabled'] = 'enabled'
    reasoning_effort: Literal['low', 'high', 'max'] = 'high'
    temperature: float = Field(default=0.7, ge=0, le=2)
    timeout_seconds: int = Field(default=180, ge=15, le=600)
    max_concurrency: int = Field(default=2, ge=1, le=8)
    api_key: str = Field(default='', max_length=600)
    clear_key: bool = False
    offline: bool = True
    max_tokens: int = Field(default=8192, ge=200, le=65536)


class BatchDraftRequest(Strict):
    tasks: list[DraftRequest] = Field(min_length=1, max_length=6)


class Preferences(Strict):
    conversation_mode: Literal['chapter', 'scene'] = 'chapter'
    chapter_turns: int = Field(default=40, ge=12, le=200)
    surface_thinking: bool = True
    recall_enabled: bool = True
    recall_threshold: float = Field(default=0.12, ge=0.05, le=0.9)
    memory_k: int = Field(default=5, ge=1, le=12)
    history_turns: int = Field(default=6, ge=1, le=12)
    history_strategy: Literal['staged', 'sliding'] = 'staged'
    stage_turns: int = Field(default=16, ge=6, le=40)
    stage_chars: int = Field(default=6000, ge=1200, le=16000)
    context_chars: int = Field(default=18000, ge=6000, le=40000)
    font_size: int = Field(default=17, ge=14, le=24)
    theme: Literal['dark', 'light'] = 'dark'


class NewSession(Strict):
    title: str = Field(default='新的旅程', min_length=1, max_length=80)
    mode: Literal['protagonist', 'observer', 'mixed'] = 'protagonist'


class Move(Strict):
    location_id: str


class Corpus(Strict):
    text: str = Field(default='', max_length=6000)


class PackageEdit(Strict):
    story: dict
    characters: dict


class DevelopmentRequest(Strict):
    character_id: str = Field(min_length=1, max_length=120)
    instruction: str = Field(default='根据实际经历判断是否需要变化；允许保持不变。', min_length=1, max_length=2000)


class CharacterChange(Strict):
    category: Literal['emotion', 'relationship', 'personality']
    key: str = Field(min_length=1, max_length=60)
    target_id: str | None = None
    value: float = Field(ge=0, le=1)
    evidence_ids: list[str] = Field(min_length=1, max_length=8)
    rationale: str = Field(min_length=1, max_length=800)


class DevelopmentProposal(Strict):
    character_id: str
    assessment: str = Field(min_length=1, max_length=1500)
    changes: list[CharacterChange] = Field(default_factory=list, max_length=6)
