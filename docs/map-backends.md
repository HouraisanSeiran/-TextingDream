# 地图后端策略（玩家旅程）

更新日期：2026-11-09。

## 默认：Terragenesis `world_map_product`

- 策略模块：`app/map_policy.py`
- 故事包未声明 `mechanics.map` 时，玩家底图回退到
  `artifacts/fast-world/tg-speed-archipelago-1600-20261108`（可用
  `TEXTILE_DEFAULT_WORLD_MAP` / `TEXTILE_DEFAULT_WORLD_IDENTITY` 覆盖）。
- 投影：`planar_metres`（坐标槽位存米制 x/z）。

## 可选：civ-atlas（默认关闭）

```text
TEXTILE_CIV_ATLAS=1
```

关闭时：

- `/api/inner/map-imports*`、`/native-map`、`/api/inner/native-*`、`world-package` 返回 503
- `mechanics.map.kind=civ_atlas` 的旅程 resolve 为 `backend_disabled`
- 实现代码隔离在 `app/civ_atlas/`（旧 `app.civ_atlas_*` 路径为兼容 shim）

## 天气与道路

运行：`python -c "from app.tg_weather_roads import verify; import json; print(json.dumps(verify(), ensure_ascii=False, indent=2))"`

| 系统 | 结论 |
|---|---|
| 天气 | 可用 `mechanics.weather`；产品可提供 elevation。平面米制不可当 lon/lat。 |
| 道路 | 作者 `adventure.routes` / 地点邻居可用。TG 无道路层；`civ_routes` 属 civ-atlas。 |
