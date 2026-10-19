"""Local adjudication and compact public performance cues; no model calls."""
import hashlib
import math
from .attributes import performance
from pydantic import BaseModel, ConfigDict, Field


class DialogueProfile(BaseModel):
    """Author-approved public performance information, never private biography."""
    model_config = ConfigDict(extra='forbid')
    rhythm: str = Field(default='长短句自然交替', max_length=60)
    diction: str = Field(default='朴素具体，少用抽象总结', max_length=80)
    tactic: str = Field(default='先回应问题，再提出自己的疑问', max_length=100)
    public_intent: str = Field(default='', max_length=100)
    avoid: list[str] = Field(default_factory=list, max_length=3)
    keywords: list[str] = Field(default_factory=list,max_length=6)


class OutcomeCues(BaseModel):
    model_config = ConfigDict(extra='forbid')
    success: list[str] = Field(default_factory=list, max_length=5)
    failure: list[str] = Field(default_factory=list, max_length=5)


def validate_cues(raw):
    cues=OutcomeCues.model_validate(raw).model_dump()
    if any(not isinstance(x,str) or not x.strip() or len(x)>40 for values in cues.values() for x in values):
        raise ValueError('结果关键词应为1到40字的非空文本，每个分支最多5个')
    return cues


def resolve_check(seed, attribute, ability, difficulty, fatigue):
    """Retains existing game formula and repeatable roll on retries/rollback."""
    for name,value in [('能力',ability),('难度',difficulty),('疲劳',fatigue)]:
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<=value<=1:
            raise ValueError(name+'必须是0到1的有限数值')
    probability=max(.05,min(.95,.5+ability-difficulty-fatigue*.2))
    roll=int(hashlib.sha256(seed.encode()).hexdigest()[:8],16)/0xffffffff
    success=roll<probability
    return {'seed':seed,'attribute':attribute,'ability':ability,'difficulty':difficulty,'fatigue':fatigue,
            'probability':probability,'roll':roll,'success':success,'margin':probability-roll,
            'rules_version':'attribute_v1'}


def outcome_cues(action, success, checked):
    branch='success' if success else 'failure'
    supplied=validate_cues(action.get('narrative_cues',{}))[branch]
    default=['回应结果','保留下一步选择'] if success else ['尝试受阻','保留尊严','询问替代办法']
    return {'result':'success' if success else 'failure','checked':checked,
            'keywords':supplied or default,
            'boundary':'只影响表达；不能新授物品、通行、知识或关系。后果以outcome和当前状态为准。'}


def public_voice(character):
    if character.get('dialogue_profile') is not None:
        profile=DialogueProfile.model_validate(character['dialogue_profile']).model_dump()
        if any(not x.strip() or len(x)>60 for x in profile['avoid']):
            raise ValueError('表达禁用项应为1到60字的非空文本')
        if any(not x.strip() or len(x)>20 for x in profile['keywords']):raise ValueError('表达关键词应为1到20字')
        return profile
    # A small reusable behavior vocabulary, not a serialized personality sheet.
    weights=character.get('personality',{})
    tendency=max(weights,key=weights.get) if weights else ''
    styles={
        '谨慎':('短句，问题明确','具体条件，不说空泛大道理','先核实一项条件，不替人做担保'),
        '责任':('简短平稳','步骤和责任，少修饰','指出责任归属，再说下一步'),
        '社交':('轻快，先接话再转折','生活用语，少术语','探问需求，讨价还价须有现有依据'),
        '贪婪':('简练，条件句较多','利弊与代价','询问交换条件，不捏造价格'),
        '求真':('先限定，再给理由','区分观察、推断与传闻','指出一个具体疑点，允许暂不下结论'),
        '好奇':('发问简短，感受具体','少总结，多问缘由','追问一个细节，不替玩家决定'),
    }
    rhythm,diction,tactic=styles.get(tendency,('长短句自然交替','朴素具体','直接回应，允许沉默'))
    return {'rhythm':rhythm,'diction':diction,'tactic':tactic,'public_intent':'',
            'avoid':['每轮复述性格标签','固定口头禅']}


def cast_projection(package, session, participants, audience='player'):
    cast=[]
    for c in package['characters']['characters']:
        if c['id'] not in participants or c['id']==session['hero'] or session['characters'][c['id']]['location']!=session['location']:
            continue
        if audience!='player' and c['id']!=audience:
            continue
        profile=public_voice(c)
        profile['ability_expression']=performance(c)
        growth=session.get('development',{}).get(c['id'],{})
        weights={**c.get('personality',{}),**growth.get('personality',{})}
        traits=sorted(weights,key=lambda k:(-weights[k],k))[:2]
        emotion=growth.get('emotion',{}) if growth.get('emotion_expires_after_turn',-1)>=session.get('turn_index',0) else {}
        feelings=sorted(emotion,key=lambda k:(-emotion[k],k))[:1]
        profile['keywords']=list(dict.fromkeys(profile.get('keywords',[])+traits+feelings))[:6]
        activity=session['characters'][c['id']].get('activity','')
        if activity:profile['activity']=activity
        cast.append({'id':c['id'],'name':c.get('public_name',c['name']), **profile})
    return sorted(cast,key=lambda c:c['id'])
