# -*- coding: utf-8 -*-
"""兼容包装：事件库内容已移到 ``app/event_library.py``（产品代码不得 import tools/）。

``artifacts/event-content/stats.py`` 与旧测试仍可 ``from tools import event_library``。
"""
from app.event_library import *  # noqa: F401,F403
from app.event_library import (  # noqa: F401
    PICK_MAX, PICK_MIN, attach, event_specs, events_block, natures, pick_event_ids,
    quests_block, rewards_block,
)
