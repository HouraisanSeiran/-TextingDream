# -*- coding: utf-8 -*-
"""Schema names shared by the civilisation simulator.

The simulator is original Python. It uses the same *ideas* as a chronicle
(year, polity, event kind) but does not copy upstream source.
"""

ALGORITHM = "zhimeng-civ-sim-2"
HABITAT_SCHEMA = "zhimeng-civ-habitat-v1"
CHRONICLE_SCHEMA = "zhimeng-civ-chronicle-v1"
RUN_SCHEMA = "zhimeng-civ-sim-run-v1"
CANDIDATE_KIND = "zhimeng_civ_sim_history_candidate"

ANNAL_KINDS = (
    "found", "expand", "war", "peace", "fall",
    "dynasty", "succession", "appoint", "faith_adopt", "convert",
)

#: Whole-grid cell cap. 400×400 fast products are far under this; a 30 m bed is not.
MAX_CELLS = 2_000_000

LICENSE_NOTE = (
    "织梦自有模拟器，不是 civ-atlas 移植。上游 https://github.com/guaner-334/civ-atlas "
    "为 AGPL-3.0-only；此处只借鉴「地图与文明种子分离、编年史按年/政体/事件种类」的数据语义，"
    "没有复制、翻译或改写其源码，也没有把它作为依赖引入。"
)
