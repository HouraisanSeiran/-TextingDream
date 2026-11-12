# 显式大型岛 TD 山系任务

> **现行口径（2026-11-08 对齐 TG `docs/island-mountains-current.md`）**：默认实际露海连通岛面积严格 **>25 km²** 即可准备山系（`IslandMountainConfig.min_area_km2=25`）；无默认腹地宽度门槛。峰高曲线锚点仍约 **100 km²**（与资格门槛分开）：25–100 km² 岛 requested 峰高约 300 m±10%，更大岛沿 300–3000 m 面积曲线。整岛共用两遍高度标定，缺块保持 pending。已接入普通世界生成的 islands → island-mountains → fast。下文 2000 km² / 旧宽度门槛 /「不改默认世界生成」是首版历史。

资格分析、计划与混合算法归 Terragenesis 公共模块。织梦侧适配器是 `app/world_gen/island_mountains.py` 与 `tools/prepare_island_mountains.py`。原海峡/近岸/潟湖/环礁与特殊火山锥连通岛不套普通 TD 峰高。总台账见 [terrain-algorithm-map.md](terrain-algorithm-map.md)。

```powershell
python tools/prepare_island_mountains.py --skeleton <skeleton.npz> --island-product-path <islands.npz> --expected-island-identity <岛身份> --plan <plan.npz> --expected-plan-identity <计划身份> --out-root <新任务根> --reason <明确理由> --skeleton-run <同骨架run.json> --dry-run --report <新报告.json>
```

empty/dry-run在GPU、内存worker或模型检查之前返回。非空显式任务只调度固定选中内陆覆盖的tile，一个任务复用一个现有local30默认生成器；完全位于有限来源以外的tile跳过并记录。可以多次指定`--tile ix iz`选择计划集合子集。真实调用仍执行原资源门槛，无第二模型服务。

原始TD存在`raw/<island_identity>/local30/<tile>`，混合结果另存`derived/<plan_identity>/local30/<tile>`。raw不会被混合覆盖；派生产品绑定raw identity/高程SHA、plan/岛/源身份、基底政策、混合政策和公共模块SHA。组合为`base + w*(max(decoded,land_floor)-base)`，海岸和非选中域w=0严格保留解析岛基底；raw负值不改写。基底是冻结岛解析场，不是实测30m，也不是含额外山系/侵蚀的fast世界层。

`local30.tile_state/request_local` 可选接收`mountain_plan_identity/mountain_blend_policy`。换/移除计划、换政策均拒绝旧派生缓存；raw与计划分开，可在同岛不同计划间显式复用。同一任务不会把CPU注入raw当作真实TD结果。CPU测试只证明真实调度/组合路径；没有合格岛时不启动模型、不扩大原岛凑验收图。
