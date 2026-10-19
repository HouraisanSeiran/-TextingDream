"""Authored geographic inputs and reproducible worldbuilding estimates (not survey data)."""
import math
from typing import Literal
from pydantic import Field, model_validator
from .contracts import Strict


class Deposit(Strict):
    kind: Literal['iron','coal','copper','tin','gold','rare_metals']
    abundance: float = Field(ge=0,le=1,allow_inf_nan=False)
    accessibility: float = Field(default=.5,ge=0,le=1,allow_inf_nan=False)
    technology: float = Field(default=.5,ge=0,le=1,allow_inf_nan=False)
    surveyed: bool = False


class Environment(Strict):
    elevation_m: float = Field(default=200,ge=-500,le=9000,allow_inf_nan=False)
    slope_deg: float = Field(default=5,ge=0,le=90,allow_inf_nan=False)
    precipitation_mm: float = Field(default=650,ge=0,le=12000,allow_inf_nan=False)
    temperature_c: float = Field(default=15,ge=-60,le=60,allow_inf_nan=False)
    freshwater: float = Field(default=.5,ge=0,le=1,allow_inf_nan=False)
    soil_fertility: float = Field(default=.5,ge=0,le=1,allow_inf_nan=False)
    flood_risk: float = Field(default=.2,ge=0,le=1,allow_inf_nan=False)
    irrigation: float = Field(default=.2,ge=0,le=1,allow_inf_nan=False)
    transport: float = Field(default=.4,ge=0,le=1,allow_inf_nan=False)
    governance: float = Field(default=.5,ge=0,le=1,allow_inf_nan=False)
    area_km2: float = Field(default=1000,gt=0,le=10000000,allow_inf_nan=False)
    basin: str = Field(default='',max_length=100)
    river_path: list[tuple[float,float]] = Field(default_factory=list,max_length=60)
    river_elevations_m: list[float] = Field(default_factory=list,max_length=60)
    deposits: list[Deposit] = Field(default_factory=list,max_length=6)
    source: str = Field(default='架空设计参数，非现实测绘',max_length=200)

    @model_validator(mode='after')
    def river(self):
        if len({d.kind for d in self.deposits})!=len(self.deposits):raise ValueError('同一区域矿产类型不可重复')
        if self.river_path:
            if len(self.river_path)<2 or len(self.river_path)!=len(self.river_elevations_m):raise ValueError('河流至少两点，并逐点提供海拔')
            if not self.basin:raise ValueError('河流必须标明流域')
            if any(not math.isfinite(x) or not math.isfinite(y) or not -180<=x<=180 or not -90<=y<=90 for x,y in self.river_path):raise ValueError('河流经纬度无效')
            if any(not math.isfinite(x) or not -500<=x<=9000 for x in self.river_elevations_m):raise ValueError('河道海拔无效')
            if any(a<b for a,b in zip(self.river_elevations_m,self.river_elevations_m[1:])):raise ValueError('河流必须从高处流向低处，不允许逆坡')
        elif self.river_elevations_m:raise ValueError('河道海拔需要坐标')
        return self


class Calendar(Strict):
    start_day_of_year: int = Field(default=80,ge=1,le=365,strict=True)
    utc_offset: float = Field(default=0,ge=-12,le=14,allow_inf_nan=False)
    axial_tilt_deg: float = Field(default=23.44,ge=0,le=45,allow_inf_nan=False)
    enabled: bool = True


RESOURCE_NAMES={'iron':'铁','coal':'煤','copper':'铜','tin':'锡','gold':'金','rare_metals':'稀有金属'}


def estimate(raw):
    e=Environment.model_validate(raw)
    water=min(1,e.precipitation_mm/800)*.45+e.freshwater*.35+e.irrigation*.2
    temperature=max(0,1-abs(e.temperature_c-18)/30)
    slope=max(.02,1-e.slope_deg/35)
    altitude=math.exp(-max(0,e.elevation_m-500)/2200)
    fertile=max(0,min(1,e.soil_fertility*(.25+.75*min(1,e.precipitation_mm/800)*.5+.375*e.freshwater)*temperature*slope))
    farmland=max(0,min(.9,e.soil_fertility*water*temperature*slope*(1-.65*e.flood_risk)))
    density=120*farmland*altitude*(.3+.7*e.transport)*(.3+.7*e.governance)
    mining=sum(d.abundance*d.accessibility*d.technology for d in e.deposits)
    density+=min(8,mining*4)*e.freshwater*(.2+.8*e.transport)*altitude
    dependencies=[]
    if farmland<.15:dependencies.append('粮食输入依赖')
    if e.freshwater<.35:dependencies.append('水源与灌溉通道依赖')
    if e.transport<.35:dependencies.append('运输瓶颈')
    if e.flood_risk>.5:dependencies.append('堤防维护压力')
    if mining>.2:dependencies.append('矿产外运与冶炼燃料需求')
    return {'fertile_soil_fraction':round(fertile,3),'fertile_soil_km2':round(e.area_km2*fertile,1),
        'arable_fraction':round(farmland,3),'arable_km2':round(e.area_km2*farmland,1),
        'population_density_per_km2':round(density,2),'population_capacity':round(density*e.area_km2),
        'dependencies':dependencies,'resource_potential':{RESOURCE_NAMES[d.kind]:round(d.abundance*d.accessibility*d.technology,3) for d in e.deposits},
        'basis':'区域承载估计，不是实际人口普查；资源存在不等于已勘探或能开采；不自动决定国界、战争和政权。'}


def solar(latitude,longitude,day,calendar):
    cfg=Calendar.model_validate(calendar)
    if not cfg.enabled:return None
    doy=(cfg.start_day_of_year+day-2)%365+1
    phi=math.radians(latitude)
    decl=math.radians(cfg.axial_tilt_deg)*math.sin(2*math.pi*(284+doy)/365)
    b=2*math.pi*(doy-81)/364
    equation=9.87*math.sin(2*b)-7.53*math.cos(b)-1.5*math.sin(b)
    noon=12+cfg.utc_offset-longitude/15-equation/60
    denominator=math.cos(phi)*math.cos(decl)
    numerator=math.sin(math.radians(-.833))-math.sin(phi)*math.sin(decl)
    ratio=numerator/denominator if abs(denominator)>1e-12 else (float('inf') if numerator>0 else -float('inf'))
    if ratio>=1:duration=0;polar='polar_night'
    elif ratio<=-1:duration=24;polar='polar_day'
    else:duration=2*math.degrees(math.acos(ratio))/15;polar=None
    def clock(h):
        minutes=round(h*60);return {'time':f'{minutes%1440//60:02d}:{minutes%60:02d}','day_offset':minutes//1440}
    return {'day_of_year':doy,'utc_offset':cfg.utc_offset,'sunrise':None if polar else clock(noon-duration/2),
        'sunset':None if polar else clock(noon+duration/2),'daylight_hours':round(duration,2),'polar':polar,
        'basis':'类地365日历近似太阳模型；统一游戏时区，含经度与均时差，不含山体遮挡、天气和夏令时'}


def local_environment(story,session):
    place=next(l for l in story['locations'] if l['id']==session['location'])
    result={'coordinates':place.get('coordinates'),'coordinate_order':'经度、纬度'}
    if place.get('environment'):
        e=Environment.model_validate(place['environment']).model_dump(mode='json')
        e['deposits']=[d for d in e['deposits'] if d['surveyed']]
        result.update(environment=e,estimates=estimate(e))
    if place.get('coordinates') and story.get('mechanics',{}).get('calendar'):
        lon,lat=place['coordinates'];result['sun']=solar(lat,lon,session['time']//24+1,story['mechanics']['calendar'])
    return result


def is_daylight(story,session):
    place=next(l for l in story['locations'] if l['id']==session['location'])
    calendar=story.get('mechanics',{}).get('calendar')
    if not calendar or not place.get('coordinates'):return 6<=session['time']%24<18
    lon,lat=place['coordinates'];sun=solar(lat,lon,session['time']//24+1,calendar)
    if sun is None:return 6<=session['time']%24<18
    if sun['polar']:return sun['polar']=='polar_day'
    def minutes(x):h,m=map(int,x['time'].split(':'));return h*60+m
    start=minutes(sun['sunrise']);end=minutes(sun['sunset']);now=session['time']%24*60
    return start<=now<end if start<end else now>=start or now<end


def environment_features(place):
    if not place.get('environment'):return []
    e=Environment.model_validate(place['environment']).model_dump(mode='json');stats=estimate(e)
    common={'coordinates':[place['coordinates']],'geometry':'point','location_ids':[place['id']],
            'environment':e,'description':e['source']+'；'+stats['basis']}
    features=[]
    for layer,label in [('elevation','海拔'),('fertile_soil','沃土'),('population','人口承载'),('resources','资源')]:
        if layer=='resources' and not e['deposits']:continue
        features.append({**common,'id':layer+'_'+place['id'],'name':place['name']+' · '+label,'layer':layer})
    if e['river_path']:
        features.append({**common,'id':'basin_'+place['id'],'name':e['basin'],'layer':'water','geometry':'line',
            'coordinates':e['river_path'],'description':'流域河道工作稿，按逐点海拔下降；不是现实河流测绘。'})
    return features
