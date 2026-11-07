# 事件池契约（`mechanics.events`）

实现：`app/events.py`。只有故事包声明 `mechanics.events` 才生效；旧包不加任何 session 键、不加 surface 键，行为不变。

## 分级（按最终传播范围）

| 等级 | 条件（默认值，包内可配） |
|---|---|
| 小 | 只波及 1 座城镇 |
| 中 | 波及 ≥ `medium_towns`（默认 2）座城镇，但国家数 < `large_countries` |
| 大 | 波及城镇分属 ≥ `large_countries`（默认 2）个不同国家 |

等级每次检查重新计算，可升可降。国家缺失（无人地、作者没声明）的城镇不计入国家数，所以没有国家数据的世界最高只出中事件。

按影响人数分级本轮不做：civ-atlas 没有可靠的人口数据。后续可选算法：给城镇加作者声明的 `population`，按受影响人口比例分级，并把它和范围分级取较大者。

## 检查与传播

- 每 `interval_hours`（默认 24，即每游戏日；`offset_hours` 可错开日界）检查一次。`pressure.advance` 是唯一的时间入口，推进结束后 `events.tick` 把跨过的边界逐个处理，一次跨多日就逐日检查。
- 每次检查：新事件满足 `starts_at`、`start_on`、`max_active`、`radius_hours`（起点离玩家不超过该小时数）才开始；已波及城镇对每个相邻未波及城镇各掷一次骰。
- 概率：`contagion * road_factor[kind] / (1 + hours / hours_half)`。`road_factor` 默认 road 1.0、trail 0.6、sea 0.8、town_lane/street 1.0，事件可覆盖。
- 种子：`sha256("{session.seed}:event:{id}:day:{n}:{a}>{b}")`，只由种子、事件、检查序号、边决定。状态在 `session['event_pool']`，随快照回滚，读档/回滚结果不变。
- 收缩：`contain_on`（`flag` / `signal` / `quest_done`，任一成立）或 `fade_after`（开始后第 n 次检查）使事件每次检查退出 `recede_per_check` 座城镇（离起点最远的先退，起点最后退）；退完则 `ended`。
- `max_towns` 限制单个事件的波及城镇数；`max_active`（默认 3）限制同时活跃事件数。

## 传播图（中立接口）

`events.PlaceGraph`：节点=城镇/地点 id，边=相邻 + 路程小时 + 道路类型，节点可带国家。模块不 import civ 快照或 play_map，不新建路网。`graph` 取 `story_locations` 或 `exploration`，缺省时有 `mechanics.exploration` 就用后者。

| 适配器 | 读取字段 |
|---|---|
| `story_graph` | `story.locations[*].id/name/neighbors/town_id/polity`；`mechanics.adventure.routes[*].origin/destination/hours/kind`（缺路由时 1 小时、`path`） |
| `exploration_graph` | `mechanics.exploration.towns[*].id/name/polity`；`mechanics.exploration.roads[*]` 中 `source == 'civ_routes'` 的 `origin/destination/kind/hours`（途中驿站并成一条城到城的边，小时相加，类型用 `/` 合并）；`story.locations[*].town_id` 映射玩家位置 |

国家来源：`mechanics.events.polities[地点 id]`，或地点上的 `polity` 字段。civ 世界由 `civ_exploration.town_polities(civ, towns, year)` 生成（只读，不改 `compile_region`），建包时写入 `polities`。

## civ-atlas 城镇 → 国家

`settlement.region` → `civ_atlas_history._replay_block(civ, year)['polity'][region]`。年份须不早于第一个检查点（否则回放状态为 UNKNOWN，全部给 None，不编造）。`-1`、越界一律是“无人地”，不计入国家。映射以一个固定年份为准，运行中国家不随游戏时间变。

## 玩家与作者投影

玩家：

- `session['heard']` 追加未确认 information：`source="局势"`，`distortion=1`，文本只含 `heard` 文案，不含事件 id。`hear_delay_hours > 0` 时按离玩家的最短路程小时延迟若干检查。不写 `facts`。
- `surface['event_notices']`：`[{kind, label, text}]`。`kind ∈ start / rise / fall / end`，只在变化发生的那一步响应里出现一次（复用 `_notice_slot` 机制）。不含事件 id、等级、波及城镇。
- 玩家 surface 不含 `event_pool`。

作者：`GET /api/inner/sessions/{id}/events`（`events.authority_view`）。字段：`interval_hours`、`offset_hours`、`last_check`、`next_check`、`next_check_at_hours`、`thresholds`、`max_active`、`radius_hours`、`graph{source,nodes,edges,polity_missing,note}`、`news`，以及每个事件的 `id、label、status、level、origin、started_check、towns[{id,name,polity,since_check}]、countries、polity_missing_towns、country_missing、fading、contained、contagion、pending_hearing、history[{check,at_hours,kind,from,to,towns,countries}]`。

## 后果

`on_level.{small,medium,large,ended}` 只允许 `flag / resource / information / clock / signal`；`information` 不能 `confirmed`。校验沿用 `checks._validate_effects`：signal 必须被钟或任务订阅（例如中事件发信号开启“征集勇者”任务的 `enabled_on`）。所有效果经 `Runtime.effects` 应用。

## 配置字段

`version, interval_hours(1–168), offset_hours, graph, polities, medium_towns, large_countries, max_active(1–8), radius_hours, hear_delay_hours, events[≤16]`。事件：`id, label, origin, starts_at, start_on, start_chance(0–1，默认 1=条件满足就开始；<1 时每次检查按 sha256(seed:event:id:start:check) 掷一次，没掷中下次检查再掷), contagion, hours_half, road_factor, max_towns, contain_on, fade_after, recede_per_check, heard{small,medium,large,ended}, notice{…}, on_level{…}`。所有模型 `extra=forbid`。
