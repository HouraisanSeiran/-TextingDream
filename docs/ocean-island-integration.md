# 可选冻结海洋岛链消费

岛屿生成、形态和采样算法位于 Terragenesis。织梦只通过 `app/world_gen/ocean_island_adapter.py` 导入公共接口，读取已经准备的岛屿产品；不会在查询或世界层命令里隐式准备岛链。原骨架 NPZ 与已有世界不回写。

世界层实际入口：

```powershell
python tools/build_fast_relief.py --skeleton <原骨架.npz> --expected-identity <骨架身份> --out <新输出目录> --relief orogen --island-product-path <islands.npz> --expected-island-identity <岛产品身份> --skeleton-run <同骨架的skeleton-run.json>
```

世界层先完成原有地形和海岸清斑，再以相同绝对米制坐标直接采冻结岛要素；保存初次岛体目标与连续保护权重，在侵蚀后恢复受保护差值，避免重复合成。水文之前按最终发布的 float32 床面重算有限外海连通。登记潟湖作为局部水文终点，排除普通淡水湖与外海。状态3为外海、4为闭合负高程床面/潟湖、5为非负陆地；状态4不算陆地面积。

侵蚀的固定床面掩码包含合成后全部初始负高程格，因而保护岛外原有闭合负盆地，不会把它们按陆地最低高度夹到正值。这个掩码仅用于侵蚀；水文的外海掩码仍是边界连通海洋，潟湖仍是独立局部终点。禁用岛产品的闭合盆地反例同时检查原始负高程逐值保持、状态4以及与旧路径相同的海陆分类。

输出新增 `ocean-island-binding.json`、矢量清册、冻结岛源面积分数与保护附层。矢量身份独立于格心海陆；小岛没有落在格心仍可保留ID和有限面积估计，不扩成整格陆地。`frozen_island_*_fraction` 明确表示冻结岛源的面积估计，不冒称经过外部地表合成后的精确面积。

绑定严格检查原骨架和岛产品身份、消耗数组、真实源种子/坐标，以及两文件SHA。`--skeleton-run` 可选，但一旦传入就必须通过其自身身份与source SHA/plate/config identity验证；只采用其中已有海洋目标和容差。缺目标或容差写未知，不自动补默认值，不调整海平面，也不承诺精确配额。

局部TD实际入口：

```powershell
python tools/prepare_local30.py --config <引用同骨架的world.json> --tile <ix> <iz> --reason <登记理由> --out-root <新世界根目录> --world-layer-identity <世界层身份> --island-product-path <同一islands.npz> --expected-island-identity <同一岛身份> --skeleton-run <同一skeleton-run.json>
```

该命令默认会执行原有 GPU/内存门槛并启动模型；纯接线验证应使用 Python 的 `td_resident.periodic_factory(...).sample_raw(...)` 或 `local30.prepare_tile(..., generator=<CPU注入器>)`。`--dry-run` 不启动生成。测试中的CPU注入器输出只是调用证据，不是TD地貌成果。

TD条件工厂沿原有模型索引→世界米制坐标→可选scale的顺序，以同一冻结岛产品求条件高程，再执行气温/降水随高程订正。按既有有限边缘政策明确重复该有限产品，不生成新外域岛；周期接缝和真实TD模型响应不由接线测试保证。默认7680m条件格仍可能漏采小岛或窄环礁，世界层与局部岸线偏差须如实报告。

局部产品lineage额外保存 `island_identity` 和 `island_condition_policy`。同一plate但换岛、移除岛或变条件政策均拒绝复用旧tile，须显式重新准备；没有岛参数时原默认路径保持。只读 `request_local/tile_state` 不触发生成。

现有 `world_cells_from_pages` 仍用于960m TD页比较；本接线没有把2km fast产品伪装成960m。可显式提供 `world_layer_identity` 绑定真正消费的世界层，实际粗细岸线/高程比较另做。生成器/产品来源与运行统计分别记录。

CPU回归入口：

```powershell
python -m pytest tests/test_ocean_island_integration.py tests/test_fast_relief.py tests/test_world_gen_tiles.py
```

旧 `test_world_gen_pipeline.py` 的新骨架生成fixture仍调用重构前 `tectonic_evolution/tectonic_product`，属于已知上游导入断链，本集成没有改骨架求解器，也不将该套件记录为通过。世界层所需 `graph_hydro` 已仅迁移到重构后的公开 `terrain_pipeline.drainage`，数值算法保持原样。

2026-11-06 本地回归为30项通过（集成8、原fast14、tiles8，1项既有插件警告）。另完成真实1600km、800²、2km全域CPU运行，42.35秒、采样RSS峰值464,023,552字节；真实TD raw条件进入同一岛产品，但未启动模型推理。原v2真实产物身份 `fae4a40cb1d9aa3a1a4f226b978c446275f06e37da3e44edf0d0063d75b49f4a` 保留为中间版本：事后发现旧侵蚀夹高使2218个岛保护域外负床变陆，共8872km²；这不是岛链新增陆地面积。该产物没有被修复后的源码覆盖，不能作最终通过。修复仅经小CPU反例/回归及加强的只读审计验证；下一次真实全域运行与核心v3产品一起执行。

该v2独立岛产品46个要素的谷线激活均为0，不能把外部世界自带山系/侵蚀当作岛算法生成的谷地。保存高程图明确区分冻结岛产品与外部组合世界层；配色表示床面高程，没有植被或TD推理含义。
