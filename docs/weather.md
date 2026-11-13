# 天气生成与素材说明

更新：2026-11-08。后端入口 `app/weather.py`，浏览器镜像 `app/static/weather-fx/weather-gen.js`，字段规范见 [weather-spec.md](weather-spec.md)。**已接入**旅程只读投影：`GET /api/sessions/{id}/weather?hours=0..72`；**未接入**玩家前端、正式地图天气层、Canvas 特效合成、旅程资源/结算（2026-11-08 按用户要求本轮不改前端）。天气不推进时间、不写存档、不改 `state_version`。

## 已有美术素材

目录 `app/static/weather-fx/`，素材为 Canvas 效果代码，均有独立预览。总预览入口：[index.html](../app/static/weather-fx/index.html)，可直接用浏览器打开。

| 模块 | 文件 | 已有内容 |
|---|---|---|
| 雨与风暴 | `rain/rain.js` | 雨、雷暴、冰雹 |
| 雪 | `snow/snow.js` | 雪、暴风雪、雨夹雪的雪部分 |
| 雾 | `snow/fog.js` | 雾 |
| 沙暴 | `snow/sand.js` | 沙暴 |
| 昼夜 | `daylight/daylight.js` | 昼夜调色、灯光、星月与水面倒影 |
| 奇幻 | `fantasy/fantasy.js` 及四个子文件 | 魔力风暴、灵雾、瘴气、灰烬雨 |
| 极光 | `aurora/aurora.js` | 极光帘幕 |
| 冰冻 | `ice/ice.js` | 冻雨、霰、霜、雾凇 |
| 强风 | `wind/wind.js` | 台风、龙卷风，雨与 rain 模块组合 |
| 天色 | `sky/sky.js` | 霾、浮尘、扬沙、热浪、太阳雨、彩虹 |

共有 10 个模块。已做 Edge 无头运行检查：10 模块就绪，28 种手动天气、16 个预设、生成器模式及风眼参数联动无脚本异常。此次查看了生成器冬夜积雪截图；其他效果尚不能视为完成逐项视觉验收。DPR2、移动端性能和 reduced-motion 仍待后续验收。

用户后续验收发现 HTTP + DPR1.5 下的部分覆盖和模块加载错误，现已修复：总合成器为每层按 DPR 绘制，可选模块按 CSP 允许的同源脚本加载。新增 HTTP 浏览器回归覆盖 DPR1/1.5/2 和画布四角真实像素变化；此项是坐标与运行回归，不等于 DPR2 视觉/性能已验收。美术待办见 [weather-art-review-2026-11-06.md](archive/handoffs/weather-art-review-2026-11-06.md)。

## Python 接口

从项目根目录调用：

```python
from app.weather import weather_at, forecast, region_weather, validate_state

opts = dict(lon=116.4, lat=39.9, elevation=50,
            calendar={"start_day_of_year": 80, "utc_offset": 8})
state = weather_at(42, day=12, hour=7.5, climate="temperate", **opts)
validate_state(state)
next_24 = forecast(42, 12, 7.5, 24, "temperate", **opts)

coastal = weather_at(4, 12, 15, "tropical", season="summer", coast_distance_km=20)
frozen = weather_at(42, 12, 5, "continental",
                    overrides={"kind": "freezing_rain", "intensity": .7})
eye = weather_at(42, 12, 5, "tropical", overrides={
    "kind": "typhoon", "cyclone": {"category": 3, "phase": "eye"}})
cells = [{"id": "port", "lon": 120, "lat": 25,
          "climate": "subtropical_monsoon", "elevation": 10, "coast_distance_km": 5}]
region = region_weather(42, cells, 180, 15, season="summer")
```

`day` 从 1 开始，支持有限的负日期；`hour` 为 `[0,24)`，可带小数。`forecast` 的 `hours` 表示返回样本数，最多 1440，`step` 为每个样本间隔的游戏小时（默认 1，上限 24）。`region_weather` 最多 4096 格，返回顺序与 cells 一致，`id` 只负责输入去重，不添加到输出状态。

9 种气候：`temperate`、`continental`、`maritime`、`mediterranean`、`subtropical_monsoon`、`tropical`、`arid`、`highland`、`polar`。不指定 `season` 时按年内日期平滑插值，南半球错开半年；显式季节主要用于调试。传经纬度用于空间锋面，同时传 `calendar` 才启用地理日出日落；否则日出/日落为 6/18 点。

自然天气有 24 种，另有 4 种奇幻天气：`mana_storm/spirit_mist/miasma/ashfall`，默认不进随机池，用 `fantasy=("spirit_mist",)` 开启允许项。`overrides.kind` 可以强制任意已支持类型用于预览。

自然台风要求热带/亚热带季风的适宜季节和显式海岸距离不超过 200 公里，未提供距离时不猜沿海。台风事件约 48–72 小时，风眼默认无雨、弱风、少云；少量雨可手动覆盖。模型不包含真实台风路径求解。

## 输出与累积

每次返回全字段状态，含时间、kind、强度、降水、风、云雾、温湿度、能见度、极光、魔力、气溶胶、彩虹、热浪、台风阶段和龙卷强度。无台风时为 `cyclone={"category":0,"phase":"none"}`。温度限制在 −80～60℃，效果和累积强度为 0～1。

地面 11 项：`wetness/puddles/snow_cover/hail_cover/ash_cover/mana_residue/glaze/frost/rime/dust_cover/graupel`。按历史天气逐小时积分，包含冻雨结冰、积霰、夜间生霜、冷雾生雾凇、沙尘沉积及日照/升温/雨水消退；冰壳融化会补充地面湿度。`ground.graupel` 已是正式字段，ice 模块缺字段时的强度近似只为兼容旧预览。

有限历史约 216–240 小时，未持久保存沉积。影响地面的 `overrides` 视为整个窗口持续；强制霜等仍受日照物理条件影响。用 `overrides.ground` 可直接设预览覆盖量。数值区间、枚举和天气组合统一校验，矛盾参数抛出 `ValueError`，不自动吞掉或更改指定字段。

## 前端镜像与性能

JS 对应接口为 `WeatherGen.weatherAt/forecast/regionWeather/validateState`，可选参数通过最后一个 opts 对象传入；字段名与 Python 相同。Node 使用 `require()`。修改算法须同步两端；共享表由 `python -m tools.weather_mirror_tables` 同步，`--check` 可只读检查。

经度使用周期空间噪声，跨日界线连续；低纬和极地向西，中纬向东，过渡平滑。缓存上限 128 个地点上下文，每上下文自然状态 2048、太阳信息 128、地面前缀 32，缓存不影响确定性。Python `clear_cache/cache_info` 与 JS `clearCache/cacheInfo` 提供调试观测。

本机单次实测（非服务承诺）：

| 查询 | 首次 | 重复 | 下一小时 |
|---|---:|---:|---:|
| 单点 | 67.42 ms | 0.075 ms（20 次中位数） | 0.51 ms |
| 16 格 | 1048.78 ms | 1.54 ms | 7.51 ms |
| 64 格 | 4409.18 ms | 5.50 ms | 24.61 ms |

缓存覆盖后相邻小时重用历史。首次新地点仍需历史回放，超过上下文容量的批量循环可能反复重算；不能据此宣称全世界地图已可实时刷新。接地图时需进一步安排可见区域、采样与预计算。没有上层温度、污染源、雨影或气压场，冻雨、霾、龙卷寿命等均为游戏近似。

## 接入旅程（2026-11-08）

- 适配层：`app/weather_view.py`。它把 `session.time`（小时数，从 0 开始）、当前地点坐标/海拔、
  `story.mechanics.calendar` 与可选的 `story.mechanics.weather` 转成生成器参数。
- 路由：`GET /api/sessions/{id}/weather?hours=0..72`。只读；不推进时间、不写存档、不改版本。
- 前端：本轮未改。玩家手记标题、天气效果合成均未接；接口先供后续前端/外部客户端使用。
- 配置（全部可选）：`mechanics.weather.seed`、`climate`、`season`、`fantasy`、
  `locations.<id>.climate`、`locations.<id>.coast_distance_km`。缺省时由地点纬度/群系推导气候，
  再缺省为 `temperate`；不猜海岸距离，因此不会自然生成台风。
- 回归：`tests/test_weather_integration.py`（纯函数 + HTTP + 版本不变）。

## 验证

```powershell
.venv\Scripts\python.exe -X utf8 -m pytest tests/test_weather.py tests/test_weather_backend.py -q --tb=short -o addopts=''
.venv\Scripts\python.exe -m ruff check app/weather.py tests/test_weather_backend.py tools/weather_mirror_tables.py
.venv\Scripts\python.exe -m tools.weather_mirror_tables --check
node --check app/static/weather-fx/weather-gen.js
node --check app/static/weather-fx/index.js
```

最新天气专项：**84 passed，31.78 秒**。原有测试保留，新增自然天气出现、地面消退、风眼、非法覆盖、海岸输入、极端高程、日界线、风带、缓存复用及 Python/JS 全字段比对。它不是工程全量回归结果。运行记录和截图在 `artifacts/weather-backend/`。
