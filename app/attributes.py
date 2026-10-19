"""Six stable axes; deterministic rules and a rebuildable SQLite keyword vector index."""
import copy
import hashlib
import json
import math

AXES = ('talent', 'strength', 'agility', 'wisdom', 'social', 'resilience')
NAMES = dict(zip(AXES, ('天赋', '力量', '敏捷', '智慧', '社交', '韧性')))
ALIASES = {**{v:k for k,v in NAMES.items()}, '灵力亲合度':'talent', '理解':'wisdom'}
WORDS = {
    'talent': [('感应迟缓','按步骤练习','谨慎引导'),('感知灵力','稳定引导','熟练需训练'),('灵力敏感','精细引导','易察能量变化')],
    'strength': [('借助工具','节省力气','避免硬扛'),('稳妥发力','常规负重','调整支点'),('有力支撑','重物搬运','控制力道')],
    'agility': [('提前避让','缓步试探','留足距离'),('及时闪避','协调动作','保持平衡'),('迅速变向','精细动作','快速撤步')],
    'wisdom': [('先问清楚','单步判断','需要明确线索'),('比较线索','识别明显危险','选择应变'),('识别矛盾','多步预判','察觉陷阱线索')],
    'social': [('直述需要','简短回应','少用言外之意'),('接住话题','解释立场','适度转折'),('调整措辞','试探需求','协商让步')],
    'resilience': [('及时休息','承认疲惫','规避消耗'),('保持节奏','承受压力','恢复呼吸'),('耐受消耗','逆境坚持','缓慢释放紧张')],
}
TRIGGERS = {'talent':['灵力','修炼','法术','感应','天赋'], 'strength':['力量','搬','推','负重','攀爬'],
            'agility':['闪避','躲','敏捷','平衡','陷阱'], 'wisdom':['应变','陷阱','判断','翻译','线索'],
            'social':['交谈','对话','说','协商','说服'], 'resilience':['血量','伤','疲劳','坚持','韧性']}


def specification():
    return {'version':1, 'scale':[0,100], 'axes':[{'id':k,'name':NAMES[k],
        'keywords':{'low':list(WORDS[k][0]), 'medium':list(WORDS[k][1]), 'high':list(WORDS[k][2])}} for k in AXES],
        'hp':{'base':50,'per_resilience':2},
        'note':'天赋仅为原灵力亲合度的显示改名。属性约束能力，不等于性格、道德或已知秘密。'}


def values(raw=None, legacy=False):
    raw=raw or {}
    if legacy:
        result={k:50 for k in AXES}
        for key,value in raw.items():
            axis=ALIASES.get(key,key)
            if axis in AXES:
                result[axis]=value*100 if key not in AXES and isinstance(value,(int,float)) and 0<=value<=1 else value
        raw=result
    if set(raw)!=set(AXES):raise ValueError('角色必须包含天赋、力量、敏捷、智慧、社交、韧性六项属性（内部ID不变）')
    if any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=100 for v in raw.values()):
        raise ValueError('六项属性必须是0至100的有限数值，不能使用布尔值')
    return {k:raw[k] for k in AXES}


def upgrade(story, characters, legacy=False):
    story,characters=copy.deepcopy(story),copy.deepcopy(characters)
    old='attributes' not in story.get('mechanics',{})
    story.setdefault('mechanics',{}).setdefault('attributes',specification())
    for c in characters['characters']:
        c['attributes']=values(c.get('attributes'),legacy=old or legacy)
    for e in story['events']:
        for a in e.get('actions',[]):
            if a.get('check'):
                a['check']['attribute']=ALIASES.get(a['check']['attribute'],a['check']['attribute'])
    return story,characters


def validate(story,characters):
    spec=story.get('mechanics',{}).get('attributes')
    if spec is None:return  # legacy import is upgraded before commit
    if spec.get('version')!=1 or spec.get('scale')!=[0,100] or [a.get('id') for a in spec.get('axes',[])]!=list(AXES):
        raise ValueError('故事包六项属性定义缺失、乱序或量程错误')
    if spec.get('hp')!={'base':50,'per_resilience':2}:raise ValueError('血量公式需为50+2×韧性（版本1）')
    for a in spec['axes']:
        if a.get('name')!=NAMES[a['id']]:raise ValueError('属性显示名称需与当前版本一致')
        if set(a.get('keywords',{}))!={'low','medium','high'}:raise ValueError('每项属性需要低中高三档关键词')
        for ws in a['keywords'].values():
            if not isinstance(ws,list) or not 1<=len(ws)<=6 or any(not isinstance(w,str) or not w.strip() or len(w)>30 for w in ws):
                raise ValueError('每档需要1至6个短关键词')
    for c in characters['characters']:values(c.get('attributes'))
    for e in story['events']:
        for a in e.get('actions',[]):
            if a.get('check') and ALIASES.get(a['check']['attribute'],a['check']['attribute']) not in AXES:
                raise ValueError('判定必须引用六项属性之一')


def band(value):return 'low' if value<35 else 'high' if value>=70 else 'medium'


class KeywordVectors:
    """Explicit six-dimensional game vectors, not semantic neural embeddings."""
    def __init__(self,store):
        self.store=store
        with store.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS attribute_vectors(namespace TEXT,id TEXT,body TEXT,vector TEXT,PRIMARY KEY(namespace,id))')

    def search(self,spec,attrs,query='',limit=6):
        vals=values(attrs)
        namespace=hashlib.sha256(json.dumps(spec,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        with self.store.connect() as db:
            if not db.execute('SELECT 1 FROM attribute_vectors WHERE namespace=? LIMIT 1',(namespace,)).fetchone():
                for i,a in enumerate(spec['axes']):
                    for level,keywords in a['keywords'].items():
                        v=[0]*6;v[i]={'low':-1,'medium':0.25,'high':1}[level]
                        body={'attribute':a['id'],'name':a['name'],'band':level,'keywords':keywords}
                        db.execute('INSERT OR REPLACE INTO attribute_vectors VALUES(?,?,?,?)',
                            (namespace,a['id']+':'+level,json.dumps(body,ensure_ascii=False),json.dumps(v)))
            rows=db.execute('SELECT body,vector FROM attribute_vectors WHERE namespace=? ORDER BY id',(namespace,)).fetchall()
        q=[(vals[k]-50)/50 for k in AXES];norm=math.sqrt(sum(x*x for x in q)) or 1
        ranked=[]
        for body,vec in rows:
            b=json.loads(body);v=json.loads(vec)
            if b['band']!=band(vals[b['attribute']]):continue # hard gate before similarity
            cosine=sum(x*y for x,y in zip(q,v))/(norm*math.sqrt(sum(x*x for x in v)))
            score=cosine+sum(w in query for w in TRIGGERS[b['attribute']])
            ranked.append({**b,'score':round(score,4)})
        return sorted(ranked,key=lambda b:(-b['score'],b['attribute']))[:limit]


def performance(character):
    vals=values(character.get('attributes'),legacy=set(character.get('attributes',{}))!=set(AXES))
    social=band(vals['social']);wise=band(vals['wisdom'])
    return {'ability_bands':{NAMES[k]:band(v) for k,v in vals.items()},
        'social_actions':{'low':['直接回应','提出明确请求'],'medium':['解释立场','接话反问','温和转折'],
                          'high':['试探需求','调侃缓和','协商交换','委婉拒绝']}[social],
        'reasoning_scope':{'low':'依赖明确线索，不无依据多步预判','medium':'比较可见线索，允许判断错误',
                           'high':'可多步预判，但不可知道未被感知的事实'}[wise],
        'boundary':'行动成败、血量与能力档位由本地决定；表达措辞不能反向修改数值。高能力不强制礼貌或善良。'}


def health(character,status):
    vals=values(character.get('attributes'),legacy=set(character.get('attributes',{}))!=set(AXES))
    maximum=round(50+2*vals['resilience'])
    damage=status.get('damage',0)
    return {'maximum':maximum,'current':max(0,maximum-damage),'formula':'50+2×韧性'}
