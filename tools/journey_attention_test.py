"""Real sequential travel through HTTP routes, plus paired full-history probes.

Persists an isolated test library, save, all requests/responses and checkpoints.
No production preferences, story documents or saves are modified.
"""
import asyncio
import copy
import json
import re
import sys
from datetime import datetime
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.web import create_app

STOPS=[('tianchao_capital','天朝都城','pack'),('western_pass','西行关城','translate'),
       ('crescent_oasis','新月沃土商驿','listen'),('western_port','西方海港','ask'),
       ('test_alpine_pass','西方山口商镇','road_record'),('test_europe_city','西方河城·抵达欧洲','arrival')]
CODE='苇灯四七'
MEAL='麦饼偏硬，豆汤太淡'
ONCE='灰鹭八二'


def write(path,data):
    text=json.dumps(data,ensure_ascii=False,indent=2)
    temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(text,encoding='utf-8');temp.replace(path)


def fixture(svc):
    p=copy.deepcopy(svc.runtime.package())
    story,chars=p['story'],p['characters']
    next(e for e in story['events'] if e['id']=='port_contact')['next_events']=['test_alpine_event']
    next(l for l in story['locations'] if l['id']=='western_port')['neighbors'].append('test_alpine_pass')
    for i,(loc,name,action) in enumerate(STOPS[4:]):
        prior='western_port' if i==0 else 'test_alpine_pass'
        event='test_alpine_event' if i==0 else 'test_europe_event'
        npc='test_mountain_guide' if i==0 else 'test_city_scribe'
        story['locations'].append({'id':loc,'name':name,'description':
            '测试路线工作稿：山地商路在此换用驮运，商镇连接海岸与西方河谷。' if i==0 else
            '测试路线工作稿：西方河城位于河流渡口，集市、工匠与文书事务在此交汇。对应欧洲内陆的架空终点，不是现实历史城市。',
            'neighbors':[prior]+(['test_europe_city'] if i==0 else []),'scenes':[event],
            'coordinates':[15.5,46.5] if i==0 else [7.5,48.5]})
        story['major_scenes'].append({'id':loc+'_chapter','title':name+' · 行旅','kind':'city','location_ids':[loc],'expected_turns':18})
        fact='山口道路需要按季节和驮运条件核实，当前没有收到封路公告。' if i==0 else '我已抵达西方河城；此行的各项传闻仍需分别核实。'
        story['events'].append({'id':event,'title':'山口的通行条件' if i==0 else '河城的旅途复盘','location_id':loc,
            'major_scene_id':loc+'_chapter','participants':['protagonist',npc], 'player_enters':True,
            'player_goal':'核实山路补给，不擅自交易' if i==0 else '回顾旅行，区分事实、私下想法和传闻',
            'hidden_goal':'测试专用节点，不包含预定反转','entry_flags':{},'exit_flag':event+'_done','max_turns':20,
            'next_events':['test_europe_event'] if i==0 else [],
            'actions':[{'id':action,'label':'记下已确认的情况，结束会面','effects':[{'op':'fact','text':fact,'visible':True}],
                        'ends_event':True,'success_text':fact}]})
        chars['characters'].append({'id':npc,'name':'山口向导' if i==0 else '河城书记','public_name':'山口向导' if i==0 else '河城书记',
            'role':'次要角色','occupation':'旅人' if i==0 else '学者','traits':['务实'] if i==0 else ['求真'],
            'personality':{'谨慎':0.7,'社交':0.4} if i==0 else {'求真':0.8,'责任':0.6},'state':{},'location_id':loc,'power_level':1,
            'dialogue_profile':{'rhythm':'简短直接' if i==0 else '先问来源，再区分说法','diction':'道路、补给的日常词' if i==0 else '具体原话和条件',
             'tactic':'只就现有材料说明通行条件' if i==0 else '询问证据，允许暂不下结论','public_intent':'帮助核实可行条件','avoid':['重复格言'],'keywords':['务实' if i==0 else '严谨']}})
    svc.runtime.commit_package(story,chars,'仅测试副本：延伸西方海港到欧洲内陆，两站各18轮')


TOPICS=[
 ['都城街坊怎样与粮食转运联系','旅行之前怎样区分凭信、许可与自述','万言机能做什么，不能替我证明什么','在不拿取物品的情况下观察出行准备','河谷水源与城市腹地的关系','如何问清作保条件而不承诺付款','对离乡的不安，只写我的内心','不同语言怎样造成礼节误解','没有原文的传闻该怎样保留判断','若对方含糊，友善追问一个细节','回顾今天尚未核实的事项','这座城有哪些可观察的生活差异'],
 ['询问守卫首先需要核对哪一项','把翻译与文书核验分开','请守卫说明不知道的部分','山前水站为何影响队伍规模','不用凭空报价，问清驮运条件','礼貌质疑一项含糊的手续要求','我默想风险，不向守卫透露私事','没有得到许可之前保持等待','解释自己的提问不等于替商队担保','讨论道路、驿站与水源之间的关系','请求一句具体的下一步建议','短暂沉默，描述可观察的态度'],
 ['与商人讨论渠水和市集的关系','询问消息究竟出自哪里','区分亲眼见闻与沿途转述','不要立即买东西，先问交易惯例','渠道维修如何影响粮食供应','用友善但不轻信的语气追问','私下想想是否应该相信商人','解释我听懂了但没有承诺同行','问干旱地区为何仍有灌溉农业','询问商人尚不知道的道路细节','对照价格传闻与实际物品持有','保持对未证实消息的保留态度'],
 ['向学者说明我刚从沃土来','海港与都城的称谓有什么差异','询问万言机译出的概念是否等义','请学者区分港口规则和个人建议','航路存在是否等于已经买到船票','海陆转运受到什么实际限制','我在心中回顾陌生感，不让学者读心','温和反问学者哪里还需要证据','不要替我签契约，先解释见证人的用途','区分学者的推断与公开记录','询问继续向西的路线应核对什么','不替我决定明天行程，只结束这个问题'],
 ['向向导说明只想了解山口情况','为什么平原大车未必适合山路','雨雪与补给分别怎样影响旅程','询问道路是否真的已有封闭公告','不承诺雇用，先问需要准备哪些资料','请向导说明哪些经验不是确定事实','我私下想念故乡，不把想法说出口','友善反问是否存在其他已知办法','讨论过桥、驮畜和水站的不同限制','请不要替我获得新的装备','观察向导回答的方式，不编造他的秘密','为继续走向河谷保留未解问题'],
 ['向书记说明我已经来到河城','为何不同城市会使用不同契约术语','渡口市集与港口有哪些生活差异','用一项具体问题核对过去听说的规则','不把旅途经历变成自己已获得的官职','请书记只依据他知道的事情回应','我私下比较出发时的心情和现在','询问如何保留原话的说话者与出处','面对口径不同的人先保留哪类证据','让书记直接回答，不轮流复述我的话','说明我暂时不决定下一段远行','停下来回想这段路，避免编造遗漏情节']]


def player_turn(stage,local):
    channel='speech' if stage else 'action'
    expected=None
    if local==0 and stage==0:
        text=f'我在心里给这次西行取一个只有自己知道的暗号：{CODE}。我没有把暗号说出口。'
        channel='thought'
    elif local==1 and stage==0:
        text=f'我回想昨晚那顿饭，记得自己的评价是“{MEAL}”。这只是我现在的回忆，不意味着行囊里还有食物。'
        channel='thought'
    elif local==2 and stage==0:
        text=f'我在心里记下一句不向任何人透露的临时记忆标记：{ONCE}。这只是我自己随意取的记号，不对应任何物品或势力。'
        channel='thought'
    elif local==14:
        text='请用我自己的内心回忆：在天朝出发前，我给这次西行取的私下暗号是什么？不知道就说记不清，不补编来历。'
        channel='thought';expected=CODE
    elif local==15:
        text='我回忆出发前那次晚饭，当时对麦饼和豆汤各作了什么评价？只引用我原来的说法。'
        channel='thought';expected=MEAL
    elif local==16:
        text='我先确认此刻游戏第几天、几点、实际在哪，以及已确认持有什么。章节标题不能代替现在的位置。只写依据当前状态知道的。'
        channel='thought'
    elif local==17:
        text='我执行本轮选中的事件行动，只描述本地裁定的后果；不额外接受条件、取得物品或瞬间抵达下一城。'
        channel='action'
    else:
        topic=TOPICS[stage][local if local<12 else local-12]
        text=('我想'+topic+'。')
        if local==6:channel='thought'
    return text+' 请自然写两三段，约180—300字，直接回应本轮，不重复盘点景物。',channel,expected


PROBE_SYSTEM='''你是对话记录核对器。仅根据给定context和history回答JSON。引擎current_anchor优先于旧文；人物发言/回忆不等于客观事实。
字段：code（出发前主角在心中取的暗号，缺失null）；meal（当时对麦饼和豆汤的原评价，缺失null）；location（当前地点名称）；game_day（游戏日整数）；local_time（HH:MM）；inventory（当前已确认物品名称数组）；rumor_days（商驿商人声称西行封路几天，未出现null）；rumor_verified（该说法是否已客观证实，布尔）；guard_knows_code（是否有证据守卫听到暗号，布尔）。不从常识补全。'''
PROBE_SYSTEM+='另一个字段 once_marker：主角在都城心中记下的临时记忆标记；它不同于西行暗号，缺失时null。'


async def main():
    out=ROOT/'artifacts'/('journey_attention_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
    out.mkdir(parents=True);(out/'calls').mkdir()
    app=create_app(out/'test.sqlite3');svc=app.state.service;rt=svc.runtime
    keys=set(re.findall(r'sk-[A-Za-z0-9_-]{16,}',Path('C:/Users/Huang/Desktop/api用后即删.txt').read_text(encoding='utf-8-sig')))
    if len(keys)!=1:raise ValueError('需要唯一测试密钥')
    # Preserve actual production provider settings, except explicitly using online Flash.
    import sqlite3
    with sqlite3.connect('file:'+str(ROOT/'data/textiledream.sqlite3')+'?mode=ro',uri=True) as db:
        row=db.execute("SELECT body FROM documents WHERE kind='settings' AND id='api'").fetchone()
    cfg=json.loads(row[0]) if row else {}
    cfg.update(api_key=keys.pop(),offline=False,model='deepseek-flash',dialogue_model='deepseek-flash',max_tokens=8192)
    svc.provider.configure(cfg)
    fixture(svc)
    # Main route tests shipped defaults; no privileged all-history setting.
    report={'status':'running','route':[x[1] for x in STOPS],'planned_turns':108,'preferences':svc.preferences(),
            'api':svc.provider.public_config(),'rows':[],'probes':[],'errors':[],'moves':[],
            'fixture_note':'原四站+两站测试专用欧洲内陆节点；游戏移动仍用默认4小时，不能当作真实跨洲行程。'}
    write(out/'manifest.json',report)
    counter=0
    original_complete=svc.provider.complete
    pending_label={}
    async def capture(system,context,**kwargs):
        nonlocal counter
        counter+=1
        label=copy.deepcopy(pending_label)
        before={t['id'] for t in svc.store.all('trace')}
        try:return await original_complete(system,context,**kwargs)
        finally:
            traces=[t for t in svc.store.all('trace') if t['id'] not in before]
            for t in traces:write(out/'calls'/f'{counter:03}.json',{'label':label,'trace':t})
    svc.provider.complete=capture
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://testserver',timeout=240) as client:
        b=(await client.get('/api/bootstrap')).json();client.headers['X-TextileDream-Token']=b['token']
        async def post(path,data):
            r=await client.post('/api'+path,json=data)
            if r.status_code!=200:raise ValueError(r.text[:1000])
            return r.json()
        surface=await post('/sessions',{'title':'天朝到欧洲 · 108轮真实API旅行测试','mode':'protagonist'})
        sid=surface['id'];report['session_id']=sid
        full=[]
        async def checkpoint(n):
            state=svc.store.session(sid)
            base=rt.context(state,'player','核对出发暗号、临时记忆标记、麦饼豆汤、商驿封路传闻及当前状态',svc.preferences())
            anchor=base['current_anchor']
            expected={'code':CODE,'meal':MEAL,'location':anchor['location'],'game_day':anchor['clock']['game_day'],
                'local_time':anchor['clock']['local_time'],'inventory':anchor['inventory'],
                'rumor_days':9 if n>=54 else None,'rumor_verified':False,'guard_knows_code':False,'once_marker':ONCE}
            contexts=[('runtime',base)]
            if n in (18,54,108):
                long=copy.deepcopy(base);long['history']=copy.deepcopy(full);long['last_summary']='';long['recalled_dialogue']=[]
                contexts.append(('full_history',long))
                # Same nine-field task, explicit minimal sourced evidence; ceiling control.
                short={'current_anchor':copy.deepcopy(anchor),'history':full[:3],
                    'evidence':'商驿商人声称西行封路9天，未经证实。' if n>=54 else '尚未听到商驿封路传闻。'}
                contexts.append(('short_control',short))
            for arm,context in contexts:
                pending_label.clear();pending_label.update(kind='probe',round=n,arm=arm)
                probe={'round':n,'arm':arm,'expected':expected,'context_chars':len(json.dumps(context,ensure_ascii=False)),
                    'evidence_present':{'code':CODE in json.dumps(context,ensure_ascii=False),'meal':MEAL in json.dumps(context,ensure_ascii=False),'once_marker':ONCE in json.dumps(context,ensure_ascii=False)}}
                try:
                    answer,usage=await svc.provider.complete(PROBE_SYSTEM,context,json_mode=True,scope='surface')
                    scores={k:answer.get(k)==v for k,v in expected.items()} if isinstance(answer,dict) else {k:False for k in expected}
                    probe.update(status='success',answer=answer,usage=usage,exact_scores=scores)
                except ValueError as e:probe.update(status='error',error=str(e))
                report['probes'].append(probe);write(out/'manifest.json',report)
                print(json.dumps({'probe':arm,'round':n,'status':probe['status'],'scores':probe.get('exact_scores')},ensure_ascii=False),flush=True)
        try:
            for stage,(loc,name,action) in enumerate(STOPS):
                if stage:
                    surface=await post('/sessions/'+sid+'/move',{'location_id':loc})
                    report['moves'].append({'after_round':len(full),'location':loc,'clock':surface['local_state']['clock']})
                for local in range(18):
                    n=stage*18+local+1
                    message,channel,expected=player_turn(stage,local)
                    req={'message':message,'channel':channel,'action_id':action if local==17 else None}
                    pending_label.clear();pending_label.update(kind='journey',round=n,stage=name)
                    for attempt in range(2):
                        try:
                            surface=await post('/sessions/'+sid+'/chat',req)
                            break
                        except ValueError as e:
                            report['errors'].append({'round':n,'attempt':attempt+1,'error':str(e)})
                            write(out/'manifest.json',report)
                            if attempt==1:raise
                    state=svc.store.session(sid)
                    event=state['active'] if state['active'] and state['active']['turns'] else state['archives'][-1]
                    turn=event['turns'][-1]
                    full.append({**copy.deepcopy(turn),'location':name,'event':event['title']})
                    t=json.loads((out/'calls'/f'{counter:03}.json').read_text(encoding='utf-8'))['trace']
                    context=json.loads(t['request']['messages'][1]['content'])
                    row={'round':n,'stage':name,'conversation_id':surface['conversation_id'],'message':message,'channel':channel,'action_id':req['action_id'],
                         'reply':turn['reply'],'usage':t.get('usage',{}),'elapsed_ms':t['elapsed_ms'],
                         'history_turns':len(context['history']),'history_chars':len(json.dumps(context['history'],ensure_ascii=False)),
                         'retrieved_records':len(context.get('recalled_dialogue',[])), 'clock':surface['local_state']['clock'],
                         'expected_recall':expected,'literal_recall_in_reply':expected in turn['reply'] if expected else None,
                         'evidence_in_request':expected in json.dumps(context,ensure_ascii=False) if expected else None,
                         'anchor':context['current_anchor'],'trace_file':f'calls/{counter:03}.json'}
                    report['rows'].append(row)
                    write(out/'manifest.json',report);write(out/'history.json',full)
                    print(json.dumps({'round':n,'place':name,'input':row['usage'].get('prompt_tokens'),'output':row['usage'].get('completion_tokens'),
                        'history':row['history_turns'],'recall':row['literal_recall_in_reply'],'evidence':row['evidence_in_request']},ensure_ascii=False),flush=True)
                await checkpoint(len(full))
            report['status']='complete'
        except Exception as e:
            report['status']='incomplete';report['fatal']=str(e);print('STOP:',str(e),flush=True)
        finally:
            write(out/'manifest.json',report)
            text=['# 天朝到欧洲 · 真实生成原文','',report['fixture_note'],'']
            for r in report['rows']:text.extend([f'## {r["round"]}. {r["stage"]}',f'玩家（{r["channel"]}）：'+r['message'],'',r['reply'],''])
            (out/'旅行对话全文.md').write_text('\n'.join(text),encoding='utf-8')
            print('ARTIFACT:',out,flush=True)

if __name__=='__main__':asyncio.run(main())
