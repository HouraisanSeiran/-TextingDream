"""Declarative local resources, schedules and witnessed information.

No arbitrary code or model calls. State belongs to the journey snapshot.
"""
import hashlib
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid')


class Resource(Strict):
    id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,60}$')
    name: str = Field(min_length=1,max_length=60)
    unit: str = Field(default='',max_length=20)
    initial: int = Field(default=0,ge=0,le=1000000000,strict=True)
    maximum: int = Field(default=1000000000,ge=0,le=1000000000,strict=True)
    per_hour: int = Field(default=0,ge=-100000,le=100000,strict=True)


class TimedEffect(Strict):
    op: Literal['flag','resource','notice']
    id: str = Field(default='',max_length=120)
    value: bool = True
    delta: int = Field(default=0,ge=-1000000000,le=1000000000,strict=True)
    text: str = Field(default='',max_length=600)
    visible: bool = False


class Timer(Strict):
    id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,60}$')
    title: str = Field(min_length=1,max_length=100)
    at: int = Field(ge=0,le=10000000,strict=True)
    every: int | None = Field(default=None,ge=1,le=100000,strict=True)
    public: bool = False
    effects: list[TimedEffect] = Field(default_factory=list,max_length=12)


class Routine(Strict):
    character: str
    start: int = Field(ge=0,le=23,strict=True)
    end: int = Field(ge=1,le=24,strict=True)
    location: str
    activity: str = Field(default='',max_length=80)


class LocalRules(Strict):
    resources: list[Resource] = Field(default_factory=list,max_length=40)
    schedules: list[Timer] = Field(default_factory=list,max_length=100)
    routines: list[Routine] = Field(default_factory=list,max_length=200)
    turn_hours: int = Field(default=1,ge=0,le=24,strict=True)
    travel_hours: int = Field(default=4,ge=1,le=168,strict=True)
    memory_limit: int = Field(default=200,ge=20,le=2000,strict=True)


def rules(story):
    return LocalRules.model_validate(story.get('mechanics',{}).get('local',{}))


def validate(story,characters):
    cfg=rules(story)
    ids={x.id for x in cfg.resources}
    if len(ids)!=len(cfg.resources) or len({x.id for x in cfg.schedules})!=len(cfg.schedules):
        raise ValueError('资源或日程ID重复')
    if any(x.initial>x.maximum for x in cfg.resources):raise ValueError('资源初始值超过上限')
    chars={x['id'] for x in characters['characters']};places={x['id'] for x in story['locations']}
    hero=next(c['id'] for c in characters['characters'] if c['role']=='主角')
    used=set()
    for r in cfg.routines:
        if r.character not in chars or r.character==hero or r.location not in places or r.start>=r.end:
            raise ValueError('NPC日程角色、地点或时段无效；跨午夜请拆为两段')
        for hour in range(r.start,r.end):
            if (r.character,hour) in used:raise ValueError('同一NPC日程时段重叠')
            used.add((r.character,hour))
    for timer in cfg.schedules:
        for effect in timer.effects:
            if effect.op=='resource' and effect.id not in ids:raise ValueError('日程引用未知资源')
            if effect.op=='flag' and not effect.id:raise ValueError('日程标记需要ID')
            if effect.op=='notice' and not effect.text.strip():raise ValueError('日程消息不能为空')
    for e in story['events']:
        for a in e.get('actions',[]):
            for rid,amount in a.get('costs',{}).items():
                if rid not in ids or type(amount) is not int or amount<0:raise ValueError('行动费用必须引用资源且为非负整数')
            if 'duration_hours' in a and (type(a['duration_hours']) is not int or not 0<=a['duration_hours']<=168):raise ValueError('行动时长必须是0到168小时整数')
            for branch in ('effects','success','failure'):
                for effect in a.get(branch,[]):
                    if effect.get('op')=='resource' and (effect.get('id') not in ids or type(effect.get('delta')) is not int):raise ValueError('资源效果需要已定义资源和整数delta')
                    if effect.get('op')=='information':
                        targets=set(effect.get('known_by',[]))
                        if not targets or targets-(chars|{'player'}) or not isinstance(effect.get('text'),str) or not 0<len(effect['text'])<=1000:
                            raise ValueError('信息效果需要文本及有效知情对象')


def ensure(s,story):
    cfg=rules(story)
    if 'local' not in s:
        s['local']={'resources':{r.id:r.initial for r in cfg.resources},'ledger':[],
                    'applied':{},'notices':[],'initialized_at':s['time']}
        # One-shot deadlines predating this save do not fire retroactively.
        for t in cfg.schedules:
            if t.at<s['time']:s['local']['applied'][t.id]=s['time']-1
    return cfg


def change_resource(s,cfg,rid,delta,source,clamp=False):
    spec=next((r for r in cfg.resources if r.id==rid),None)
    if spec is None or type(delta) is not int:raise ValueError('资源ID或变化数量无效')
    old=s['local']['resources'][rid];new=old+delta
    if not clamp and not 0<=new<=spec.maximum:raise ValueError(f'{spec.name}不足或超过容量上限')
    new=max(0,min(spec.maximum,new))
    s['local']['resources'][rid]=new
    if new!=old:
        s['local']['ledger'].append({'time':s['time'],'resource':rid,'before':old,'delta':new-old,'after':new,'source':source})


def affordable(s,story,action):
    cfg=rules(story)
    balances=s.get('local',{}).get('resources',{r.id:r.initial for r in cfg.resources})
    return all(balances.get(k,0)>=v for k,v in action.get('costs',{}).items())


def charge(s,story,action,source):
    cfg=ensure(s,story)
    if not affordable(s,story,action):raise ValueError('资源不足，无法执行该行动')
    for rid,amount in sorted(action.get('costs',{}).items()):change_resource(s,cfg,rid,-amount,source)


def apply_routines(s,cfg,characters):
    hour=s['time']%24
    for cid in {r.character for r in cfg.routines}:
        current=next((r for r in cfg.routines if r.character==cid and r.start<=hour<r.end),None)
        base=next(c['location_id'] for c in characters['characters'] if c['id']==cid)
        s['characters'][cid]['location']=current.location if current else base
        s['characters'][cid]['activity']=current.activity if current else ''


def advance(s,story,characters,hours):
    if type(hours) is not int or not 0<=hours<=168:raise ValueError('推进时长必须为0到168小时')
    cfg=ensure(s,story);end=s['time']+hours;start=s['time']
    # Tick bounded integer game hours; no real-time/background API work.
    for moment in range(start,end+1):
        s['time']=moment
        if moment>start:
            for r in cfg.resources:
                if r.per_hour:change_resource(s,cfg,r.id,r.per_hour,'time',clamp=True)
        for timer in cfg.schedules:
            due=moment>=timer.at and (moment==timer.at or timer.every and (moment-timer.at)%timer.every==0)
            if not due or s['local']['applied'].get(timer.id,-1)>=moment:continue
            for effect in timer.effects:
                if effect.op=='flag':s['flags'][effect.id]=effect.value
                elif effect.op=='resource':change_resource(s,cfg,effect.id,effect.delta,'schedule:'+timer.id,clamp=True)
                elif effect.op=='notice':
                    record={'id':f'schedule:{timer.id}:{moment}','text':effect.text,'time':moment,'source':'schedule:'+timer.id,'distortion':0,'intensity':.5}
                    if effect.visible:
                        s['heard'].append(record)
                        s['local']['notices'].append({'time':moment,'text':effect.text})
                    else:s['facts'].append(record)
            s['local']['applied'][timer.id]=moment
        apply_routines(s,cfg,characters)


def view(s,story):
    cfg=rules(story);local=s.get('local',{})
    values=local.get('resources',{r.id:r.initial for r in cfg.resources})
    upcoming=[]
    for t in cfg.schedules:
        if not t.public:continue
        last=max(s['time'],local.get('applied',{}).get(t.id,-1)+1)
        at=t.at
        if at<last:
            if not t.every:continue
            at+=((last-at+t.every-1)//t.every)*t.every
        upcoming.append({'title':t.title,'at':at,'in_hours':at-s['time']})
    return {'clock':{'day':s['time']//24+1,'hour':s['time']%24,'elapsed_hours':s['time']},
            'resources':[{'id':r.id,'name':r.name,'amount':values[r.id],'unit':r.unit,'maximum':r.maximum} for r in cfg.resources],
            'upcoming':sorted(upcoming,key=lambda t:(t['at'],t['title']))[:8],
            'notices':local.get('notices',[])[-8:]}


def communicate(s,node,request,limit):
    """Only explicit speech becomes witnessed statement evidence; never truth."""
    if request.channel!='speech' or s['mode']=='observer' or s['mode']=='mixed' and not node.get('player_enters',False):return []
    present=[cid for cid in node['participants'] if cid!=s['hero'] and s['characters'][cid]['location']==s['location']]
    if request.listeners is not None:
        if set(request.listeners)-set(present):raise ValueError('私语对象必须是当前现场参与者')
        present=[cid for cid in present if cid in request.listeners]
    source=f"{s['active']['id']}:{len(s['active']['turns'])}:statement"
    for cid in present:
        # Stable id and explicit type prevent speech from becoming objective fact.
        record={'id':hashlib.sha256((source+':'+cid).encode()).hexdigest()[:16],
                'character':cid,'speaker':s['hero'],'text':request.message,'source':source,
                'time':s['time'],'distortion':1,'certainty':'仅确认听见，不确认内容为真',
                'kind':'statement','intensity':.4}
        if not any(b.get('id')==record['id'] for b in s['beliefs']):s['beliefs'].append(record)
    # Bound per-NPC derived speech memory, preserving world facts/beliefs and full chat.
    for cid in present:
        old=[b for b in s['beliefs'] if b.get('character')==cid and b.get('kind')=='statement']
        remove={b['id'] for b in old[:-limit]}
        s['beliefs'][:]=[b for b in s['beliefs'] if b.get('id') not in remove]
    return present
