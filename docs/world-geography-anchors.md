# 作者地理软锚点（织梦 × Terragenesis）

## 目的与参考

参考 [dreamulator 中文 README](https://github.com/fyabc/dreamulator/blob/main/README.zh-CN.md) 的结构化输入、确定性管线，以及其 [地理锚定设计 §4.4](https://github.com/fyabc/dreamulator/blob/main/docs/design/pipelines/geological-pipeline.md)：让作者表达大陆与海域的大致位置，再计算地形，而不是让模型编造已生成地图。

本次在线读取了 README；地形设计依据本地 2026-11-08 上游快照，不声称已核验上游最新实现。仅借鉴输入约束设计，不复制其源码、不引入球面 CVT、天文系统、投影或另一套气候引擎。

## 生成链与复用边界

`geography_features → 既有 land_field 的有限域偏置 → TG initialize / CrustState / evolve → 原骨架与山脊 → 原岛链与不规则图水文 → 原地图读取`

- TG 算法只 import，不修改其源文件；新生成产物另目录保存。
- 锚点为初始大陆地壳分配的**软意图**，不是最终海岸硬约束。海陆配额与板块演化可能改变结果；必须查看实际诊断。
- 正 strength 增强大陆倾向，负值增强海域倾向；不直接写最终高程，不造新河流或按图画海峡。
- X 东、Z 南，单位米，有限域不环绕。骨架内部既有板块周期计算仍保持，不代表锚点在对边复制。
- 省略或空列表保持旧路径；非空锚点进入配置与产品身份。已有骨架不能追加锚点冒充重新生成。
- 暂不实现上游的 overlay 局部后编辑、构造后重锚定或高程钉扎。修改本输入意味着重新生成骨架及依赖产物，不能直接覆盖冻结世界。

## 输入示例

作者生成 API `POST /api/inner/worldgen/jobs` 增加可选字段，旧字段照常：

```json
{
  "world_type": "two-continents",
  "size_km": 1600,
  "seed": 20260903,
  "use_gpu": false,
  "geography_features": [
    {"id": "western-continent", "center_x_m": -350000, "center_z_m": 0, "radius_m": 240000, "strength": 2, "aspect": 1.5, "bearing_deg": 0},
    {"id": "central-sea", "center_x_m": 0, "center_z_m": 0, "radius_m": 100000, "strength": -2, "aspect": 2, "bearing_deg": 0}
  ]
}
```

`radius_m` 为半短轴，`aspect` 为长短轴比，`bearing_deg` 从北顺时针（0 沿南北轴、90 沿东西轴）；范围外平滑核为零。最多32项，id唯一，中心必须在世界范围内，半径不小于骨架格距；数值需有限，布尔值不能充当数字。详尽可接受范围以实现校验为准。

配置文件通过顶层 `geography_features` 指定，仍走 `tools/generate_world_skeleton.py --config <文件>`。预设 CLI 可用 `--geography-json '<JSON数组>'`；不能和 `--config` 同时提供，避免参数被静默忽略。Web API仅接受结构化数组，不接收任意文件路径。现有前端未增加锚点编辑器。

## 验收与限制

检查相同输入确定性、无锚点旧路径、正负偏置、有限支持无对边复制、配置身份变化、错误输入拒绝、Web到CLI传递及小规模真实TG生成。生成记录应保留输入、锚点算法身份及最终中心海陆/高程结果，不能把输入愿望当已实现地理。

小规模测试不能替代世界级自然度、最终海峡连通性或所有锚点满足率认证。本改动不重新标定现有极干气候，不重跑万公里世界，不切换玩家默认，不修改存档或已有冻结产品。

### 本轮验证记录

- 织梦解释器：`tests/test_worldgen_geography.py`，23通过、2跳过（缺少psutil，真实生成由TG解释器覆盖）。
- TG解释器：`tests/test_worldgen_geography.py tests/test_world_gen_pipeline.py`，32通过、1跳过（TG环境缺pydantic，Web项已由织梦解释器覆盖）。真实小域生成检查输入/最终高程记录、旧空列表回放身份一致以及原TD plate reader兼容。
- 执行代理入口相关回归：114通过、1跳过、1已有失败；失败为 `test_skeleton_cell_by_size[10000-25]` 仍预期25km，而当前实现与现行文档为40km，本次未修改该无关断言。不称全库通过。
- 主审阅与目标 `git diff --check` 完成。未运行完整大世界/全域成图或浏览器视觉验收，未新增锚点编辑UI。
