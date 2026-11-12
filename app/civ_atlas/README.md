# civ-atlas 后端隔离包

默认**关闭**。开启：环境变量 `TEXTILE_CIV_ATLAS=1`。

| 模块 | 职责 |
|---|---|
| `snapshot` | `.civsnap` 容器解析与地块采样 |
| `history` | civ 部分解码与政区回放 |
| `exploration` | 原件道路 → 旅途城镇编译 |
| `world_source` | 世界包流水线适配器 |
| `native_worlds` / `native_starts` | 原生宿主只读桥与从 civ 开局 |

上游前端：`external/civ-atlas`（不入本包）。玩家默认地图：`world_map_product`（Terragenesis），见 `app.map_policy`。
