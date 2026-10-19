# TextingDream 重构资料库

本目录记录 Minecraft Java 单 JAR 工程的重构边界、迁移顺序、接口约束和验收证据。每次拆分都必须保持存档格式、命令接口和服务端权威规则兼容。

## 当前模块边界

| 模块 | 当前职责 | 目标职责 |
|---|---|---|
| `WorkManager` | 聚落、蓝图、工单生命周期、存档协调 | 工单门面与协调器 |
| `NavigationService` | 原先内嵌在 `WorkManager` 的站位、路径、重试 | 所有居民/工单共享的导航策略 |
| `WarehouseService` | 待拆出 | 仓库库存、交接、工具借还和交接诊断 |
| `GatherExecutor` | 待拆出 | 伐木、采石、采集成功判定和产物入背包 |
| `ConstructionExecutor` | 待拆出 | 蓝图施工、材料消耗和完成判定 |
| `VillageEconomy` | 招募、居民状态、农业、调度 | 居民调度门面；农业和招募继续拆分 |
| `CognitiveManager` | T2 认知协议和提案确认 | 保持独立，通过事件读取工作/社会事实 |

## 迁移规则

1. 先抽取无持久化状态的服务，再移动有状态执行器。
2. `work.json` schema、命令 JSON 和客户端字段保持兼容；需要变化时增加 schema 迁移。
3. 服务只通过明确方法访问订单和仓库，禁止跨模块直接修改内部集合。
4. 每次迁移都先跑核心验证，再跑最小真实场景；实机未通过不得标记功能完成。
5. 采集、施工、农业和身份事件必须能独立记录诊断，避免再次形成不可定位的大循环。

## 当前阶段

- [x] 抽出 `NavigationService` 与 `NavigationState`。
- [x] `WorkManager` 通过导航门面调用路径策略。
- [x] 抽出 `WarehouseService`，集中物资交接和工具归还。
- [x] 为 `WorkOrder` 增加采集尝试、成功数量、返仓次数和最后目标诊断字段。
- [x] 抽出 `GatherExecutor`，将单次方块采集、工具检查、背包增量和失败原因独立出来。
- [ ] 抽出 `ConstructionExecutor`。
- [ ] 将工单字符串阶段迁移为枚举并提供旧存档映射。
- [ ] 将 `VillageEconomy` 拆为居民调度、农业、招募三个模块。
- [ ] 建立身份事件模块，与工作事件解耦。
