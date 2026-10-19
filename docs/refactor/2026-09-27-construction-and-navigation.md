# 2026-09-27 施工与资源导航

## 已迁移

- 新增 `ConstructionExecutor`，负责在材料、权限、碰撞和目标检查通过后放置单个方块。
- `WorkManager` 保留工单调度、材料需求、进度和完成判定，不再直接执行世界放置细节。
- `VillageEconomy.canWork` 的进食流程改为可恢复状态：到仓库后确认实际消耗食物；导航暂时受阻不会永久覆盖采集/施工工单。
- `NavigationService` 增加资源区远程推进策略，按高度图和碰撞检查逐步接近目标，复杂地形回退到候选站位寻路。

## 验证

- `compileJava`、`compileClientJava` 成功。
- `verifyCore`：927 项断言通过。
- 第 15、16、17、18、19 轮真实村庄测试确认工人不再长期停留在 `daily_routine`，会进入 `quarrying/logging`。

## 第 20 轮结果

- 采石工单：`completed`，`collected=16`、`gatherSuccesses=16`、`warehouseTrips=1`。
- 伐木工单：`completed`，`collected=16`、`gatherSuccesses=16`、`warehouseTrips=1`。
- 建筑工已实际放置 7 个方块并继续进入 `building/returning`。
- 延长观察后，首栋工单在 `placed=7/436` 处再次等待 `daily_routine/前往仓库用餐`，其余工单等待 cobblestone；这说明采集闭环已通，但施工供料节奏和日常进食仍需继续调度优化。

## 未完成

第 15–19 轮曾出现 `collected=0`，第 20 轮通过专用远程资源导航后已完成采集和返仓。整村仍未完成：建筑计划尚有多个住宅、农田、工作区和道路，后续需继续验证材料循环、农田交接、道路施工和跨日续作。

施工执行器虽已拆出，整村建设闭环仍必须以真实材料入库、建筑完成、农田和道路完成为准。
