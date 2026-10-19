"""Evidence-backed proposals. Author approval changes only a pinned journey."""
import copy
import hashlib
from .contracts import DevelopmentProposal
from .prompts import stable_json, template
from .runtime import uid, now


def fingerprint(session):
    # Includes rollback-restored state. Other session changes invalidate review.
    return hashlib.sha256(stable_json(session).encode('utf-8')).hexdigest()


class Development:
    def __init__(self, service):
        self.service = service

    def context(self, session, character_id):
        rt = self.service.runtime
        p = rt.package(session['revision'])
        c = next((x for x in p['characters']['characters'] if x['id'] == character_id), None)
        if not c:
            raise ValueError('角色不存在')
        evidence=[]
        nodes={e['id']:e for e in p['story']['events']}
        for event in session['archives']+([session['active']] if session['active'] else []):
            if character_id not in nodes[event['node']]['participants']:
                continue
            for i,t in enumerate(event['turns']):
                if t.get('channel') != 'speech' or character_id not in t.get('listeners',[]):
                    continue
                # Input is evidence of a statement. Generated narration is not
                # promoted into an objective witnessed event.
                if session['mode']=='observer' or (session['mode']=='mixed' and not nodes[event['node']].get('player_enters',False)):
                    continue
                evidence.append({'id':f"{event['id']}:{i}:statement", 'event':event['id'],
                                 'kind':'statement','text':t['input'],'speaker':session['hero']})
            sources={event['node']+':'+a for a in event.get('actions_done',[])}
            for fact in session['heard']:
                if fact.get('distortion')==0 and fact.get('source') in sources:
                    evidence.append({'id':'observed:'+fact['id'],'event':event['id'],
                                     'kind':'confirmed','text':fact['text']})
        for i,b in enumerate(session['beliefs']):
            if b.get('character')==character_id and b.get('kind')!='statement':
                evidence.append({'id':f"belief:{i}",'event':b.get('source','belief'),
                                 'kind':'belief','text':b['text']})
        d=session.get('development',{}).get(character_id,{})
        personality={**c.get('personality',{}),**d.get('personality',{})}
        emotion=d.get('emotion',{}) if d.get('emotion_expires_after_turn',-1)>session['turn_index'] else {}
        return {'character':{'id':character_id,'name':c['name'],'traits':c.get('traits',[]),
                             'personality':personality,'emotion':emotion,
                             'relationships':d.get('relationships',{})},
                'allowed_keys':{'emotion':['警惕','愉快','悲伤','愤怒','恐惧'], 'personality':list(personality)},
                'other_characters':[{'id':x['id'],'name':x.get('public_name',x['name'])} for x in p['characters']['characters']
                                    if x['id']!=character_id and (x['id']==session['hero'] or any(b.get('speaker')==x['id'] for b in evidence))],
                'evidence':evidence[-24:]}

    def validate(self, data, context):
        proposal=DevelopmentProposal.model_validate(data)
        if proposal.character_id!=context['character']['id']:
            raise ValueError('不能修改其他角色')
        evidence={x['id']:x for x in context['evidence']}
        targets={x['id'] for x in context['other_characters']}
        seen=set()
        for change in proposal.changes:
            if not set(change.evidence_ids)<=evidence.keys():
                raise ValueError('变化引用了不存在或该角色不可见的证据')
            identity=(change.category,change.key,change.target_id)
            if identity in seen:
                raise ValueError('同一属性不能重复变更')
            seen.add(identity)
            if change.category=='relationship':
                if change.key!='trust' or change.target_id not in targets:
                    raise ValueError('关系目标或属性无效')
                if not any(evidence[x].get('speaker')==change.target_id for x in change.evidence_ids):
                    raise ValueError('关系变化缺少与目标互动的证据')
                old=context['character']['relationships'].get(change.target_id,{}).get('trust',0.5)
            else:
                if change.target_id is not None or change.key not in context['allowed_keys'][change.category]:
                    raise ValueError('变化属性不在允许范围')
                old=context['character'][change.category].get(change.key,0.5)
            if abs(change.value-old)>0.15000001:
                raise ValueError('单次变化超过0.15，请拆分经历或重新评估')
            if change.category=='personality' and len({evidence[x]['event'] for x in change.evidence_ids})<2:
                raise ValueError('稳定人格变化需要至少两个不同事件的证据')
        return proposal.model_dump()

    async def propose(self, session_id, request):
        svc=self.service
        async with svc.lock:
            s=svc.store.session(session_id)
            context=self.context(s,request.character_id)
            payload={**context,'request':request.instruction,'schema':DevelopmentProposal.model_json_schema()}
            if len(template('development'))+len(stable_json(payload))>svc.preferences()['context_chars']:
                raise ValueError('发展证据超过上下文预算，请调整设置')
            if svc.provider.config()['offline']:
                data={'character_id':request.character_id,'assessment':'离线模式不推断角色成长，保持不变。','changes':[]}
                usage={'calls':0,'mode':'offline'}
                svc.provider.offline_trace('development',payload,data)
            else:
                data,usage=await svc.provider.complete(template('development'),payload,json_mode=True,scope='development')
            data=self.validate(data,context)
            draft={'id':uid(),'session_id':session_id,'base_fingerprint':fingerprint(s),'created':now(),
                   'context':context,'proposal':data,'usage':usage,'status':'pending',
                   'validation':'结构、证据引用、变化幅度通过；因果合理性待作者审核'}
            svc.store.put('development_draft',draft['id'],draft)
            return draft

    async def review(self, identity, approve):
        svc=self.service
        async with svc.lock:
            draft=svc.store.get('development_draft',identity)
            if not draft or draft['status']!='pending':
                raise ValueError('候选不存在或已处理')
            if not approve:
                draft['status']='rejected';svc.store.put('development_draft',identity,draft);return draft
            s=svc.store.session(draft['session_id'])
            if fingerprint(s)!=draft['base_fingerprint']:
                raise ValueError('旅程已变化，候选过期，请重新评估')
            proposal=self.validate(draft['proposal'],self.context(s,draft['proposal']['character_id']))
            d=s.setdefault('development',{}).setdefault(proposal['character_id'],{})
            for change in proposal['changes']:
                category,key=change['category'],change['key']
                if category=='relationship':
                    d.setdefault('relationships',{}).setdefault(change['target_id'],{})[key]=change['value']
                else:
                    d.setdefault(category,{})[key]=change['value']
                    if category=='emotion':d['emotion_expires_after_turn']=s['turn_index']+1
            s.setdefault('development_log',[]).append({'id':identity,'proposal':copy.deepcopy(proposal),'time':s['time']})
            # Draft status is a convenience index; session log is the atomic source
            # of applied changes and participates in event snapshots/rollback.
            draft['status']='approved'
            svc.store.save_session(s, [('development_draft',identity,draft)])
            return draft
