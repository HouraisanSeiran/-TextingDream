# -*- coding: utf-8 -*-
"""产地词表（game_fields_v1 的 terrains）基于高度图 / DEM 的判定规则。

用途：后续地图玩法（物产分布、集市货源、采集点）按地块判断“这里算什么产地”，与元素库
``game.terrains`` 对上。地图基础统一用 civ-atlas；本模块只读它导出的数值，不改上游。

能从高度图可靠得到的只有一部分，其余必须如实标“缺数据”，不猜：

* **DEM 直接判定**：ocean（海面像素）、coast（陆地且邻近海）、mountain（起伏大或坡陡）、
  plateau（海拔高且顶面平缓）。
* **气候群落**：14 个群落按 civ-atlas ``classifyBiome``（年均温 × 年降水）判定，阈值逐字照抄
  ``external/civ-atlas/src/gen/biomes.ts``。高度图没有降水：不给降水时只返回与温度相容的
  **候选**，不定论。温度可以给实测；不给时按“纬度海平面温度 + 6.5 ℃/km 递减率”估算，
  并在 ``assumed`` 里写明是估算。
* **需要专门图层**：lake（16 位高度图把湖记成湖面高度的陆地）、river、wetland 需要
  civ-atlas 存档的水域 / 河网 / 湿地层，单靠高度图不判。
* **生产用地**：farmland / orchard / pasture / mine 只给“适宜”判断（坡度、海拔、温度），
  不等于那里已经有田、有矿；workshop / import 不是地理属性，不参与判定。

所有阈值是本项目的设计口径（米、度、℃、毫米），不是地理学标准分类。
"""
from __future__ import annotations

import math

# --------------------------------------------------------------------------- 阈值
LAPSE_RATE_C_PER_KM = 6.5          # 标准大气递减率
MOUNTAIN_RELIEF_M = 600.0          # 取样窗内最高与最低陆地之差
MOUNTAIN_SLOPE_DEG = 15.0          # 区域坡度（像素中心相距数十公里，不是建筑坡度）
MOUNTAIN_MIN_ELEV_M = 500.0
PLATEAU_MIN_ELEV_M = 1500.0
PLATEAU_MAX_RELIEF_M = 600.0
PLATEAU_MAX_SLOPE_DEG = 8.0
COAST_MAX_KM = 25.0                # 距海多近算海岸

FARMLAND_MAX_SLOPE_DEG = 6.0
FARMLAND_MAX_ELEV_M = 3000.0
FARMLAND_MIN_TEMP_C = 5.0
FARMLAND_MIN_PRECIP_MM = 300.0     # 有河流灌溉时可放宽
ORCHARD_MAX_SLOPE_DEG = 12.0
ORCHARD_TEMP_RANGE_C = (8.0, 26.0)
PASTURE_MAX_SLOPE_DEG = 20.0
PASTURE_MIN_TEMP_C = -2.0
MINE_MIN_RELIEF_M = 300.0

# 每个产地取值靠什么判定。键必须与 tools/game_fields.TERRAINS 一致（测试保证）。
RULES = {
    'ocean': 'dem',
    'coast': 'dem',
    'mountain': 'dem',
    'plateau': 'dem',
    'tundra': 'climate', 'taiga': 'climate', 'cold_desert': 'climate',
    'temperate_desert': 'climate', 'steppe': 'climate', 'temperate_forest': 'climate',
    'temperate_rainforest': 'climate', 'hot_desert': 'climate', 'savanna': 'climate',
    'tropical_dry_forest': 'climate', 'rainforest': 'climate',
    'lake': 'needs_layer', 'river': 'needs_layer', 'wetland': 'needs_layer',
    'farmland': 'suitability', 'orchard': 'suitability', 'pasture': 'suitability',
    'mine': 'suitability',
    'workshop': 'non_geographic', 'import': 'non_geographic',
}
LAYER_NEEDED = {
    'lake': '水域层（16 位高度图把湖记作湖面高度的陆地）',
    'river': '河网层',
    'wetland': '湿地层（civ-atlas 湿地不由 classifyBiome 产生）',
}


def sea_level_temp_c(lat_deg):
    """纬度 → 海平面年均温的粗估：赤道约 28 ℃，两极约 −12 ℃。是估算，不是气候模型。"""
    s = math.sin(math.radians(lat_deg))
    return 28.0 - 40.0 * s * s


def estimate_temp_c(lat_deg, elev_m):
    return sea_level_temp_c(lat_deg) - LAPSE_RATE_C_PER_KM * max(0.0, elev_m) / 1000.0


def classify_biome(t, p):
    """照抄 civ-atlas classifyBiome 的陆地分支（不含水域）。返回群落键；冰原返回 None。"""
    if t < -9:
        return None                                  # Ice：产地词表里没有冰原
    if t < -2:
        return 'cold_desert' if p < 150 else 'tundra'
    if t < 5:
        return 'cold_desert' if p < 280 else 'taiga'
    if t < 18:
        if p < 250:
            return 'temperate_desert'
        if p < 600:
            return 'steppe'
        if p < 2300:
            return 'temperate_forest'
        return 'temperate_rainforest'
    if p < 320:
        return 'hot_desert'
    if p < 950:
        return 'savanna'
    if p < 1800:
        return 'tropical_dry_forest'
    return 'rainforest'


def biome_candidates(t):
    """不知道降水时，与该温度相容的全部群落（按 classify_biome 的温度带）。"""
    if t < -9:
        return []
    if t < -2:
        return ['cold_desert', 'tundra']
    if t < 5:
        return ['cold_desert', 'taiga']
    if t < 18:
        return ['temperate_desert', 'steppe', 'temperate_forest', 'temperate_rainforest']
    return ['hot_desert', 'savanna', 'tropical_dry_forest', 'rainforest']


def _need(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('%s 必须是有限数值' % name)
    return float(value)


def classify_cell(*, is_sea, elev_m, lat_deg, slope_deg=None, relief_m=None,
                  dist_to_sea_km=None, temp_c=None, precip_mm=None, layers=None):
    """判定一个地块属于哪些产地。

    参数都是从 civ-atlas 高度图取样得到的数值（见 ``app/map_import.sample_region``）；
    ``layers`` 是可选的专门图层结果，如 ``{'river': True, 'lake': False}``。

    返回 ``{'terrains', 'candidates', 'suitable', 'assumed', 'missing'}``：

    * terrains —— 确定成立的产地；
    * candidates —— 因缺降水而无法定论的群落候选；
    * suitable —— 生产用地的适宜判断（不是现状）；
    * assumed —— 用了估算的项；missing —— 缺什么数据导致哪项没判。
    """
    elev_m = _need(elev_m, '海拔')
    lat_deg = _need(lat_deg, '纬度')
    if not -90.0 <= lat_deg <= 90.0:
        raise ValueError('纬度必须在 −90…90 之间')
    layers = dict(layers or {})
    terrains, candidates, suitable, assumed, missing = [], [], [], [], []

    if is_sea:
        return {'terrains': ['ocean'], 'candidates': [], 'suitable': [],
                'assumed': [], 'missing': []}

    slope = None if slope_deg is None else _need(slope_deg, '坡度')
    relief = None if relief_m is None else _need(relief_m, '起伏')

    # ---- DEM 直接判定
    if dist_to_sea_km is None:
        missing.append('coast：缺距海距离')
    elif _need(dist_to_sea_km, '距海距离') <= COAST_MAX_KM:
        terrains.append('coast')

    if slope is None and relief is None:
        missing.append('mountain/plateau：缺坡度与起伏')
    else:
        steep = (relief is not None and relief >= MOUNTAIN_RELIEF_M) or \
                (slope is not None and slope >= MOUNTAIN_SLOPE_DEG)
        if steep and elev_m >= MOUNTAIN_MIN_ELEV_M:
            terrains.append('mountain')
        flat = (relief is None or relief < PLATEAU_MAX_RELIEF_M) and \
               (slope is None or slope < PLATEAU_MAX_SLOPE_DEG)
        if elev_m >= PLATEAU_MIN_ELEV_M and flat and not steep:
            terrains.append('plateau')

    # ---- 气候群落
    if temp_c is None:
        t = estimate_temp_c(lat_deg, elev_m)
        assumed.append('温度：按纬度与 %.1f ℃/km 递减率估算为 %.1f ℃' % (LAPSE_RATE_C_PER_KM, t))
    else:
        t = _need(temp_c, '温度')
    p = None if precip_mm is None else _need(precip_mm, '降水')
    if p is None:
        candidates = biome_candidates(t)
        missing.append('群落：缺年降水，只给候选')
    else:
        biome = classify_biome(t, p)
        if biome is None:
            missing.append('群落：冰原，无对应产地')
        else:
            terrains.append(biome)

    # ---- 专门图层
    for key, desc in LAYER_NEEDED.items():
        if key in layers:
            if layers[key]:
                terrains.append(key)
        else:
            missing.append('%s：需要%s' % (key, desc))

    # ---- 生产用地适宜性
    if slope is None:
        missing.append('适宜性：缺坡度')
    else:
        river = bool(layers.get('river'))
        wet_enough = (p is not None and p >= FARMLAND_MIN_PRECIP_MM) or river
        if slope <= FARMLAND_MAX_SLOPE_DEG and elev_m <= FARMLAND_MAX_ELEV_M \
                and t >= FARMLAND_MIN_TEMP_C:
            if wet_enough:
                suitable.append('farmland')
            elif p is None:
                missing.append('farmland：缺降水或河流，无法确认水源')
        if slope <= ORCHARD_MAX_SLOPE_DEG and ORCHARD_TEMP_RANGE_C[0] <= t <= ORCHARD_TEMP_RANGE_C[1]:
            suitable.append('orchard')
        if slope <= PASTURE_MAX_SLOPE_DEG and t >= PASTURE_MIN_TEMP_C:
            suitable.append('pasture')
    if relief is not None and relief >= MINE_MIN_RELIEF_M:
        suitable.append('mine')      # 只说明地形有出露可能，有没有矿要看资源层

    return {'terrains': terrains, 'candidates': candidates, 'suitable': suitable,
            'assumed': assumed, 'missing': missing}


def matches_element(cell, element_terrains):
    """地块是否能产出某元素：元素的产地与地块的 terrains / suitable 有交集即可。

    ``import`` / ``workshop`` 不看地理，永远返回 False（远途输入要看商路，作坊产品看原料）。
    候选群落不算命中，避免缺降水时把每个温带地块都当成森林物产地。
    """
    have = set(cell['terrains']) | set(cell['suitable'])
    return any(key in have for key in element_terrains
               if RULES.get(key) != 'non_geographic')
