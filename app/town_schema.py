"""Strict bounded schemas for the V1 town generator.

Every model here forbids extra fields and closes its enums. Numbers are validated
with ``strict=True`` plus explicit bounds, so a bool, a NaN, a float where an int is
declared (or the reverse) is rejected instead of silently coerced.

Nothing in this module calls a language model. The generator in ``app/towns.py``
turns these authored inputs into four reviewable stages with fixed rules; a model
adapter may be added later, but it would only ever propose candidates that the same
validator has to accept.
"""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

ID = r'^[A-Za-z0-9_-]{1,60}$'


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


def ratio(default=0.0, lo=0.0, hi=1.0):
    return Field(default=default, ge=lo, le=hi, strict=True, allow_inf_nan=False)


def count(lo, hi, default=0):
    return Field(default=default, ge=lo, le=hi, strict=True)


# ---------------------------------------------------------------- closed vocabularies
TownType = Literal['hamlet', 'village', 'market_town', 'town', 'city', 'port', 'pass_fortress',
                   'mining_town', 'farm_town', 'caravan_stop', 'religious_center',
                   'border_fortress', 'academy_town', 'industrial_town', 'abandoned',
                   'quarantine']
Scale = Literal['hamlet', 'village', 'small_town', 'town', 'city']
WaterSource = Literal['river', 'lake', 'spring', 'well_field', 'aqueduct', 'rain_cistern', 'none']
StorageKind = Literal['none', 'cistern', 'tank', 'reservoir']
RoadKind = Literal['road', 'trail', 'river', 'sea', 'pass']
RoadGrade = Literal['none', 'track', 'paved', 'highway']
SitingReason = Literal['water', 'crossroad', 'ore', 'farmland', 'defense', 'religious',
                       'trade', 'refuge', 'fishing', 'salt']
MaterialId = Literal['timber', 'stone', 'cut_stone', 'clay_brick', 'fired_tile', 'mud_brick',
                     'rammed_earth', 'thatch', 'reed', 'slate', 'iron', 'bronze', 'glass',
                     'hide', 'felt', 'lime_plaster']
TechId = Literal['masonry', 'timber_frame', 'kiln', 'forge', 'water_wheel', 'windmill',
                 'mine_shaft', 'aqueduct', 'cistern', 'printing', 'snow_load_engineering',
                 'steam_boiler', 'arcane_ward']
EnergyId = Literal['human', 'animal', 'water', 'wind', 'fuel', 'none']
RoofId = Literal['flat_mud', 'gable_thatch', 'gable_tile', 'steep_slate', 'hip_tile',
                 'monopitch', 'none']
DrainId = Literal['open_gutter', 'stone_channel', 'covered_sewer', 'soak_pit', 'none']
DistrictKind = Literal['market', 'craft', 'residential', 'administration', 'temple',
                       'foreign_quarter', 'poor', 'industrial', 'harbor', 'cemetery',
                       'military', 'academy', 'storage', 'outskirts']
FacilityKind = Literal['town_hall', 'lord_hall', 'market_hall', 'granary', 'cistern', 'well',
                       'mill', 'forge', 'smelter', 'kiln', 'tannery', 'barracks', 'watchtower',
                       'city_wall', 'gate', 'temple', 'academy', 'infirmary', 'inn',
                       'caravanserai', 'stable', 'dock', 'warehouse', 'mine_head',
                       'boiler_house', 'ward_tower', 'cemetery', 'bridge']
SiteKind = Literal['ruin', 'old_mine', 'shrine', 'abandoned_workshop', 'old_manor',
                   'battlefield', 'hidden_workshop', 'quarantine_camp', 'cave_mouth',
                   'stone_circle', 'customs_post']
Access = Literal['public', 'restricted', 'secret']
# Knowledge is deliberately separate from physical access and from a site's passage state:
# `visibility` says whether people know of it at all; `access`/`status` say whether one may go.
Visibility = Literal['public', 'author']
GroupRole = Literal['majority', 'minority', 'migrant', 'seasonal', 'transient']
GovernanceForm = Literal['council', 'lord', 'guild_board', 'temple_authority', 'assembly',
                         'elder_council', 'military_governor', 'company_board', 'none']
FactionKind = Literal['lord', 'council', 'guild', 'temple', 'merchant_house', 'garrison',
                      'academy', 'company', 'secret_society', 'clan', 'customs']
PowerSource = Literal['land', 'capital', 'arms', 'faith', 'knowledge', 'trade_route',
                      'appointment', 'custom']
FlowUnit = Literal['t', 'kg', 'm3', 'count']
FlowPeriod = Literal['day', 'week', 'month', 'year']
HeatingKind = Literal['open_hearth', 'stove', 'underfloor', 'none']
HouseholdKind = Literal['nuclear', 'extended', 'communal']
Condition = Literal['good', 'fair', 'poor', 'ruined']
SiteStatus = Literal['active', 'dormant', 'sealed', 'ruined', 'claimed']
SocialMode = Literal['realistic_reference', 'artistic_extrapolation']
EvidenceLevel = Literal['primary_sources', 'secondary_survey', 'regional_analogue',
                        'comparative_guess']
EventKind = Literal['social', 'economic', 'hazard', 'discovery', 'conflict', 'ritual']

# Chinese labels are display only: every identifier above stays stable in storage.
LABELS = {
    'hamlet': '小型聚落', 'village': '村落', 'market_town': '集镇', 'town': '乡镇',
    'city': '城市', 'port': '港口', 'pass_fortress': '山口关城', 'mining_town': '矿业镇',
    'farm_town': '农业镇', 'caravan_stop': '商路驿站', 'religious_center': '宗教中心',
    'border_fortress': '边境要塞', 'academy_town': '学院城', 'industrial_town': '工业镇',
    'abandoned': '废弃聚落', 'quarantine': '隔离区',
    'small_town': '小镇', 'river': '河流', 'lake': '湖泊', 'spring': '泉水',
    'well_field': '井群', 'aqueduct': '引水渠', 'rain_cistern': '雨窖', 'none': '无',
    'track': '土路', 'paved': '铺石路', 'highway': '干道',
    'realistic_reference': '现实参考档', 'artistic_extrapolation': '艺术夸张档',
}


# ------------------------------------------------------------------------ inputs
class MapInput(Strict):
    """Recorded verbatim. The V1 rules never parse the scale string.

    An external terrain generator is not integrated yet, so `coordinate_system` and
    `scale` are stored as authored text and only carried through to storage and the
    UI. Nothing here assumes a future tool's format.
    """
    input_version: str = Field(min_length=1, max_length=40)
    coordinate_system: str = Field(min_length=1, max_length=120)
    scale: str = Field(min_length=1, max_length=120)
    source: Literal['manual_sample', 'site_selection', 'external_adapter'] = 'manual_sample'


class TerrainSample(Strict):
    elevation_m: float = Field(ge=-500, le=9000, strict=True, allow_inf_nan=False)
    slope_deg: float = Field(ge=0, le=60, strict=True, allow_inf_nan=False)
    precipitation_mm: float = Field(ge=0, le=6000, strict=True, allow_inf_nan=False)
    temperature_c: float = Field(ge=-55, le=55, strict=True, allow_inf_nan=False)
    freshwater: float = ratio(0.5)
    soil_fertility: float = ratio(0.5)
    flood_risk: float = ratio(0.2)
    area_km2: float = Field(ge=0.5, le=20000, strict=True, allow_inf_nan=False)
    coordinates: tuple[float, float] | None = None

    @model_validator(mode='after')
    def coordinate_bounds(self):
        if self.coordinates is not None:
            x, y = self.coordinates
            if not (-180 <= x <= 180 and -90 <= y <= 90):
                raise ValueError('示意坐标须在经度±180、纬度±90内')
        return self


class WaterSupply(Strict):
    source: WaterSource
    reliability: float = ratio(0.7)
    daily_capacity_l: int = count(0, 100000000)
    storage: StorageKind = 'none'
    distance_km: float = Field(default=1, ge=0, le=200, strict=True, allow_inf_nan=False)

    @model_validator(mode='after')
    def capacity(self):
        if self.source == 'none' and self.daily_capacity_l:
            raise ValueError('没有水源时不能声明日供水量')
        if self.source != 'none' and self.daily_capacity_l <= 0:
            raise ValueError('水源需要给出日供水量（升/日）')
        return self


class TransportLink(Strict):
    road: RoadGrade = 'track'
    water_route: bool = False
    portage: bool = False
    seasonal_closed_days: int = count(0, 365)
    nearest_market_days: int = count(0, 60, 1)


class ResourceCandidate(Strict):
    """A candidate is a *potential*. Output is only generated when it is surveyed,
    extractable, allowed by the declared technology and has a declared fuel/energy."""
    id: str = Field(pattern=ID)
    kind: Literal['grain', 'timber', 'stone', 'clay', 'iron', 'copper', 'tin', 'coal', 'salt',
                  'livestock', 'fish', 'herb', 'wool', 'gold', 'rare_metals', 'reed']
    abundance: float = ratio(0.5)
    accessibility: float = ratio(0.5)
    surveyed: bool = False
    extractable: bool = True
    requires_technology: list[TechId] = Field(default_factory=list, max_length=3)
    fuel: Literal['none', 'timber', 'coal', 'charcoal', 'animal'] = 'none'


class ImportDependency(Strict):
    id: str = Field(pattern=ID)
    name: str = Field(min_length=1, max_length=60)
    kind: Literal['grain', 'timber', 'stone', 'clay', 'iron', 'copper', 'tin', 'coal', 'salt',
                  'livestock', 'fish', 'herb', 'wool', 'gold', 'rare_metals', 'reed', 'water',
                  'fuel']
    amount_per_period: int = count(1, 1000000, 1)
    unit: FlowUnit = 't'
    period: FlowPeriod = 'year'
    via: Literal['road', 'river', 'sea', 'porter', 'none'] = 'road'
    note: str = Field(default='', max_length=300)


class CultureTemplate(Strict):
    """Built-in bounded template. It may shape roofs, heating and household size.

    It deliberately has no field for occupation, morality or intelligence: a culture
    is never a fixed profession or a fixed character verdict.
    """
    id: str = Field(pattern=ID)
    name: str = Field(min_length=1, max_length=60)
    roof: RoofId = 'gable_tile'
    heating: HeatingKind = 'open_hearth'
    household: HouseholdKind = 'nuclear'
    note: str = Field(default='', max_length=300)


class PeopleTemplate(Strict):
    """Body size and dwelling needs only. No temperament, no caste, no skill table."""
    id: str = Field(pattern=ID)
    name: str = Field(min_length=1, max_length=60)
    average_height_cm: int = count(90, 260, 170)
    min_ceiling_m: float = Field(default=2.4, ge=1.6, le=4.5, strict=True, allow_inf_nan=False)
    space_factor: float = Field(default=1.0, ge=0.6, le=2.5, strict=True, allow_inf_nan=False)
    need_note: str = Field(default='', max_length=200)


class ElementBinding(Strict):
    """Explicit in-request ID + version + bounded snapshot.

    The generator never reads a dynamic external candidate library: an element only
    exists for this town because the request named it, pinned a version and carried a
    short snapshot.
    """
    id: str = Field(pattern=ID)
    kind: Literal['element', 'rule_template', 'culture', 'people', 'material']
    version: str = Field(min_length=1, max_length=40)
    summary: str = Field(min_length=1, max_length=600)
    # V1：只有故事包清单里标为 existing 的元素才能充当已启用的条件；potential 只
    # 作为作者预绑定记录（未来研究、尚未出现的资源）。绑定本身不解锁任何东西。
    state: Literal['existing', 'potential'] = 'existing'
    use: str = Field(default='', max_length=200)


class RealisticReference(Strict):
    region: str = Field(min_length=1, max_length=120)
    period: str = Field(min_length=1, max_length=80)
    polity_scope: str = Field(min_length=1, max_length=200)
    evidence_level: EvidenceLevel
    uncertainty: str = Field(min_length=1, max_length=600)
    adaptation: str = Field(default='', max_length=600)


class ArtisticReference(Strict):
    prototypes: list[str] = Field(min_length=1, max_length=6)
    inventions: list[str] = Field(min_length=1, max_length=6)
    design_goal: str = Field(min_length=1, max_length=400)
    counterexamples: str = Field(default='', max_length=400)


class TownInput(Strict):
    story_revision: str = Field(min_length=8, max_length=64)
    seed: str = Field(pattern=r'^[A-Za-z0-9_-]{4,64}$')
    site: Literal['manual_sample', 'selected_location'] = 'manual_sample'
    site_name: str = Field(min_length=1, max_length=80)
    site_location_id: str | None = Field(default=None, max_length=60)
    region: str = Field(min_length=1, max_length=80)
    founded_period: str = Field(default='未定（作者未提供时期）', max_length=120)
    map: MapInput
    terrain: TerrainSample
    water: WaterSupply
    transport: TransportLink = Field(default_factory=TransportLink)
    resources: list[ResourceCandidate] = Field(default_factory=list, max_length=8)
    materials: list[MaterialId] = Field(min_length=1, max_length=16)
    technology: list[TechId] = Field(default_factory=list, max_length=14)
    cultures: list[CultureTemplate] = Field(min_length=1, max_length=3)
    peoples: list[PeopleTemplate] = Field(min_length=1, max_length=3)
    social_mode: SocialMode
    realistic: RealisticReference | None = None
    artistic: ArtisticReference | None = None
    imports: list[ImportDependency] = Field(default_factory=list, max_length=6)
    bindings: list[ElementBinding] = Field(default_factory=list, max_length=12)
    notes: str = Field(default='', max_length=600)

    @model_validator(mode='after')
    def consistent(self):
        for name, rows in (('资源候选', self.resources), ('文化模板', self.cultures),
                           ('体型模板', self.peoples), ('进口依赖', self.imports),
                           ('元素绑定', self.bindings)):
            if len({r.id for r in rows}) != len(rows):
                raise ValueError(name + 'ID重复')
        if len(set(self.materials)) != len(self.materials):
            raise ValueError('允许材料重复')
        if len(set(self.technology)) != len(self.technology):
            raise ValueError('允许技术重复')
        if self.social_mode == 'realistic_reference':
            if self.realistic is None:
                raise ValueError('现实参考档必须给出地域/时期参考与不确定性说明')
            if self.artistic is not None:
                raise ValueError('现实参考档不能同时提交艺术夸张档的设计归纳')
        else:
            if self.artistic is None:
                raise ValueError('艺术夸张档必须说明使用的现实原型与创作归纳')
            if self.realistic is not None:
                raise ValueError('艺术夸张档不伪造历史来源；请移除现实参考档字段')
        if self.site == 'selected_location' and not self.site_location_id:
            raise ValueError('按已选地点生成时必须给出地点ID')
        # A declared fuel must exist locally (as an allowed material, a fuel resource
        # candidate) or arrive as an import. A workshop cannot burn what nobody has.
        local_fuel = {m for m in self.materials if m in ('timber', 'reed', 'coal')}
        local_fuel |= {r.kind for r in self.resources if r.kind in ('timber', 'coal', 'reed')}
        fuel_import = any(i.kind == 'fuel' for i in self.imports)
        for r in self.resources:
            if r.fuel != 'none' and r.fuel not in local_fuel and not fuel_import:
                raise ValueError('资源处理所需燃料既未在本地材料/资源候选中声明，也没有进口来源')
            if set(r.requires_technology) - set(self.technology):
                # Only a surveyed candidate claims it could be worked now. An unsurveyed
                # one may name the technology it would need, and is never produced.
                if r.surveyed:
                    raise ValueError('资源候选要求的开采/加工技术未在允许技术中声明')
        return self


class PresetRequest(Strict):
    preset: Literal['wet_valley', 'cold_mountain_mine', 'arid_oasis_route']
    seed: str = Field(min_length=4, max_length=64)
    site_name: str = Field(default='', max_length=80)


# ----------------------------------------------------------------------- stages 1
class Causal(Strict):
    claim: str = Field(min_length=1, max_length=300)
    because: list[str] = Field(min_length=1, max_length=6)


class Road(Strict):
    id: str = Field(pattern=ID)
    name: str = Field(min_length=1, max_length=80)
    kind: RoadKind
    destination: str = Field(min_length=1, max_length=80)
    travel_days: int = count(0, 120, 1)
    seasonal_closed_days: int = count(0, 365)


class WaterPlan(Strict):
    source: WaterSource
    storage: StorageKind
    daily_capacity_l: int = count(0, 100000000)
    reliability: float = ratio(0.7)
    note: str = Field(default='', max_length=300)


class Capacity(Strict):
    water_cap: int = count(0, 100000000)
    local_food_cap: int = count(0, 100000000)
    import_food_cap: int = count(0, 100000000)
    transport_cap: int = count(0, 100000000)
    population: int = count(0, 100000000)
    basis: list[str] = Field(min_length=1, max_length=8)


class Skeleton(Strict):
    town_type: TownType
    scale: Scale
    display_name: str = Field(min_length=1, max_length=80)
    name_candidates: list[str] = Field(min_length=1, max_length=4)
    region: str = Field(min_length=1, max_length=80)
    founded_reason: str = Field(min_length=1, max_length=400)
    founded_period: str = Field(min_length=1, max_length=120)
    coordinates: tuple[float, float]
    siting_reasons: list[SitingReason] = Field(min_length=1, max_length=6)
    water: WaterPlan
    roads: list[Road] = Field(min_length=1, max_length=6)
    capacity: Capacity
    explanations: list[Causal] = Field(default_factory=list, max_length=8)
    warnings: list[str] = Field(default_factory=list, max_length=12)

    @model_validator(mode='after')
    def coordinate_bounds(self):
        x, y = self.coordinates
        if not (-180 <= x <= 180 and -90 <= y <= 90):
            raise ValueError('示意坐标须在经度±180、纬度±90内')
        return self


# ----------------------------------------------------------------------- stages 2
class PopulationGroup(Strict):
    id: str = Field(pattern=ID)
    label: str = Field(min_length=1, max_length=60)
    role: GroupRole
    share_permille: int = count(0, 1000)
    note: str = Field(default='', max_length=300)


class Population(Strict):
    total: int = count(0, 100000000)
    groups: list[PopulationGroup] = Field(min_length=1, max_length=8)
    basis: str = Field(min_length=1, max_length=600)
    uncertainty: str = Field(min_length=1, max_length=400)

    @model_validator(mode='after')
    def shares(self):
        if sum(g.share_permille for g in self.groups) != 1000:
            raise ValueError('人口组群占比之和必须为1000‰')
        if self.total and not any(g.share_permille for g in self.groups):
            raise ValueError('人口组群不能全部为零')
        return self


class Governance(Strict):
    form: GovernanceForm
    authority: str = Field(min_length=1, max_length=200)
    legitimacy: str = Field(min_length=1, max_length=300)
    tax_basis: list[str] = Field(default_factory=list, max_length=5)
    obligations: list[str] = Field(default_factory=list, max_length=5)


class Relation(Strict):
    faction: str = Field(pattern=ID)
    stance: Literal['ally', 'rival', 'client', 'patron', 'neutral', 'tense']
    over: str = Field(min_length=1, max_length=200)


class Faction(Strict):
    id: str = Field(pattern=ID)
    name: str = Field(min_length=1, max_length=80)
    kind: FactionKind
    public_goal: str = Field(min_length=1, max_length=300)
    power_source: PowerSource
    resources: list[str] = Field(min_length=1, max_length=6)
    obligations: list[str] = Field(default_factory=list, max_length=4)
    constraints: list[str] = Field(default_factory=list, max_length=4)
    relations: list[Relation] = Field(default_factory=list, max_length=6)
    evidence: list[str] = Field(min_length=1, max_length=4)
    hidden_goal: str = Field(default='', max_length=400)


class ChainFlow(Strict):
    resource: str = Field(pattern=ID)
    name: str = Field(min_length=1, max_length=60)
    amount: int = count(0, 100000000)
    unit: FlowUnit
    period: FlowPeriod


class ProductionChain(Strict):
    id: str = Field(pattern=ID)
    name: str = Field(min_length=1, max_length=80)
    inputs: list[ChainFlow] = Field(default_factory=list, max_length=4)
    output: ChainFlow
    workers: int = count(0, 1000000)
    energy: EnergyId
    requires_technology: list[TechId] = Field(default_factory=list, max_length=4)
    stores: str = Field(min_length=1, max_length=200)
    ships_via: list[str] = Field(default_factory=list, max_length=4)
    consumers: str = Field(min_length=1, max_length=200)
    note: str = Field(default='', max_length=400)


class TradeFlow(Strict):
    id: str = Field(pattern=ID)
    direction: Literal['import', 'export']
    resource: str = Field(pattern=ID)
    kind: Literal['grain', 'timber', 'stone', 'clay', 'iron', 'copper', 'tin', 'coal', 'salt',
                  'livestock', 'fish', 'herb', 'wool', 'gold', 'rare_metals', 'reed', 'water',
                  'fuel', 'other'] = 'other'
    name: str = Field(min_length=1, max_length=60)
    amount: int = count(0, 100000000)
    unit: FlowUnit
    period: FlowPeriod
    via: str = Field(min_length=1, max_length=80)
    requirement: str = Field(min_length=1, max_length=300)


class Labor(Strict):
    available_workers: int = count(0, 100000000)
    assigned_workers: int = count(0, 100000000)
    note: str = Field(min_length=1, max_length=400)


class Socioeconomy(Strict):
    population: Population
    governance: Governance
    factions: list[Faction] = Field(min_length=1, max_length=6)
    chains: list[ProductionChain] = Field(min_length=1, max_length=8)
    trade: list[TradeFlow] = Field(default_factory=list, max_length=8)
    labor: Labor
    staple: ChainFlow
    staple_need: ChainFlow
    tensions: list[str] = Field(default_factory=list, max_length=8)
    explanations: list[Causal] = Field(default_factory=list, max_length=8)
    warnings: list[str] = Field(default_factory=list, max_length=12)
    reference_note: str = Field(default='', max_length=600)


# ----------------------------------------------------------------------- stages 3
class District(Strict):
    id: str = Field(pattern=ID)
    name: str = Field(min_length=1, max_length=80)
    kind: DistrictKind
    population_share_permille: int = count(0, 1000)
    materials: list[MaterialId] = Field(min_length=1, max_length=6)
    roof: RoofId
    drainage: DrainId
    storeys: int = count(1, 8, 1)
    access: Access = 'public'
    visibility: Visibility = 'public'
    reach_via: list[str] = Field(default_factory=list, max_length=4)
    note: str = Field(default='', max_length=300)


class Facility(Strict):
    id: str = Field(pattern=ID)
    name: str = Field(min_length=1, max_length=80)
    kind: FacilityKind
    district: str = Field(pattern=ID)
    materials: list[MaterialId] = Field(min_length=1, max_length=6)
    condition: Condition = 'good'
    requires_technology: list[TechId] = Field(default_factory=list, max_length=4)
    public_note: str = Field(min_length=1, max_length=400)
    secret_note: str = Field(default='', max_length=400)
    visibility: Visibility = 'public'


class HousingRow(Strict):
    material: MaterialId
    roof: RoofId
    houses: int = count(0, 1000000)
    household_size: float = Field(ge=1, le=40, strict=True, allow_inf_nan=False)
    note: str = Field(default='', max_length=300)


class Housing(Strict):
    total_houses: int = count(0, 1000000)
    rows: list[HousingRow] = Field(default_factory=list, max_length=6)
    basis: str = Field(min_length=1, max_length=500)


class SpecialSite(Strict):
    """A special site is not forced to be residential and carries no population or
    administrative fields: ruins, mines and shrines must not be given inhabitants."""
    id: str = Field(pattern=ID)
    name: str = Field(min_length=1, max_length=80)
    kind: SiteKind
    is_residential: bool = False
    in_district: str | None = Field(default=None, pattern=ID)
    reach_via: list[str] = Field(default_factory=list, max_length=4)
    origin: str = Field(min_length=1, max_length=400)
    public_description: str = Field(min_length=1, max_length=600)
    secret: str = Field(default='', max_length=600)
    status: SiteStatus = 'active'
    visibility: Visibility = 'public'
    risks: list[str] = Field(default_factory=list, max_length=4)
    related_factions: list[str] = Field(default_factory=list, max_length=4)
    entry_conditions: list[str] = Field(default_factory=list, max_length=4)


class Style(Strict):
    materials: list[MaterialId] = Field(min_length=1, max_length=8)
    roof: RoofId
    drainage: DrainId
    wall_note: str = Field(min_length=1, max_length=300)
    explanations: list[Causal] = Field(min_length=1, max_length=10)


class Built(Strict):
    districts: list[District] = Field(min_length=1, max_length=10)
    facilities: list[Facility] = Field(default_factory=list, max_length=20)
    housing: Housing
    special_sites: list[SpecialSite] = Field(min_length=1, max_length=8)
    style: Style
    warnings: list[str] = Field(default_factory=list, max_length=12)


# ----------------------------------------------------------------------- stages 4
class EventCandidate(Strict):
    id: str = Field(pattern=ID)
    title: str = Field(min_length=1, max_length=80)
    kind: EventKind
    site: str | None = Field(default=None, pattern=ID)
    districts: list[str] = Field(default_factory=list, max_length=4)
    factions: list[str] = Field(default_factory=list, max_length=4)
    trigger_conditions: list[str] = Field(min_length=1, max_length=5)
    consequences: list[str] = Field(min_length=1, max_length=5)
    # V1 stops at a clearly labelled candidate: nothing here becomes an executable
    # task or a reward claim until an author writes it into a validated story event.
    status: Literal['candidate_awaiting_author'] = 'candidate_awaiting_author'
    executable: Literal[False] = False


class Clue(Strict):
    id: str = Field(pattern=ID)
    text: str = Field(min_length=1, max_length=400)
    site: str | None = Field(default=None, pattern=ID)
    holder: str = Field(default='', max_length=120)


class Secret(Strict):
    id: str = Field(pattern=ID)
    text: str = Field(min_length=1, max_length=600)
    holders: list[str] = Field(default_factory=list, max_length=4)


class StoryInterface(Strict):
    events: list[EventCandidate] = Field(default_factory=list, max_length=10)
    clues: list[Clue] = Field(default_factory=list, max_length=10)
    secrets: list[Secret] = Field(default_factory=list, max_length=8)
    open_questions: list[str] = Field(default_factory=list, max_length=8)
    warnings: list[str] = Field(default_factory=list, max_length=12)


STAGE_NAMES = ('skeleton', 'socioeconomy', 'built', 'story')
STAGE_TITLES = {'skeleton': '聚落骨架', 'socioeconomy': '社会经济', 'built': '建筑与特殊地点',
                'story': '故事候选'}
STAGE_MODELS = {'skeleton': Skeleton, 'socioeconomy': Socioeconomy, 'built': Built,
                'story': StoryInterface}


class TownSnapshot(Strict):
    """The complete bounded town that a story package carries.

    Author and public layers live together (a story package already stores author
    knowledge); projections decide what a player may read.
    """
    generator_version: Literal['town_v1'] = 'town_v1'
    # Derived from the input (seed/site/revision/terrain/water/mode), never random.
    town_id: str = Field(default='', max_length=60)
    seed: str = Field(pattern=r'^[A-Za-z0-9_-]{4,64}$')
    input: TownInput
    skeleton: Skeleton
    socioeconomy: Socioeconomy
    built: Built
    story: StoryInterface
    warnings: list[str] = Field(default_factory=list, max_length=40)


class StageEditRequest(Strict):
    stage: Literal['skeleton', 'socioeconomy', 'built', 'story']
    expected_revision: int = Field(ge=0, strict=True)
    data: dict


class AdvanceRequest(Strict):
    expected_revision: int = Field(ge=0, strict=True)


class DraftRequest(Strict):
    input: TownInput


class PublishRequest(Strict):
    expected_revision: int = Field(ge=0, strict=True)


class AdoptRequest(Strict):
    version_id: str = Field(pattern=ID)
    expected_story_revision: str = Field(min_length=8, max_length=64)
    location_id: str | None = Field(default=None, max_length=60)
    note: str = Field(default='', max_length=300)
