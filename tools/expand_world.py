"""Publish an additive worldbook revision, preserving author edits and old saves."""
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.runtime import Runtime
from app.storage import Store


def expand(package):
    package = copy.deepcopy(package)
    story = package['story']
    world = story['worldview']
    world.setdefault('source_notes', []).append({
        'id': 'world-docx-v1', 'source': '世界观.docx',
        'confirmed': ['唐朝前后地缘格局作参考，不照搬现实历史', '东方天朝、中东新月沃土王朝、西方诸国',
                      '主角自东方出发，持有可学习翻译语言的魔法机器', '灵气与气为同一能量，东方五行与西方四元素为不同理论',
                      '炼气/筑基/金丹/元婴与魔法学徒/魔法使/大魔法使/圣者大体对应', '强者可延寿，最高层次可摧山开海',
                      '信息先有真实来源，再发生片段缺失或数字夸缩', '奇幻史诗、第一人称见闻，不唯战力论'],
        'provisional': ['玄陆、万言机等专名沿用测试稿', '圣辉议庭、灯火会、澄京等名称为本次补充草案',
                        '贸易、翻译代价与法术约束为可改补充，不视为用户已经确定的硬设定'],
        'open_questions': ['世界是否放大及尺度', '寿命年限、强者人口比例、能量恢复速度', '各国疆域与年代', '主角姓名、身世和境界']})
    world['geopolitics'] = [
        {'id':'east','name':'天朝','region':'东方大陆','government':'王朝官署、地方城邑与修行传承共同维持秩序','tension':'边地通行、长寿家族与新兴商路之间的利益分配','status':'框架来自原文，社会细节为补充草案'},
        {'id':'crescent','name':'新月沃土王朝','region':'半岛、河谷与绿洲商路','government':'统一王朝，驿站与商队串联地方城市','tension':'水源、道路税、继位消息的传播','status':'框架来自原文，行政细节为补充草案'},
        {'id':'west','name':'西方诸国与圣辉议庭','region':'西方大陆','government':'多个世俗国家与跨国宗教议庭并存，议庭不是整个西方的唯一政权','tension':'港口自治、地方王权与学术传承','status':'名称与结构为补充草案'},
        {'id':'south','name':'南岸港邦','region':'南方大陆北岸','government':'沿海城邦与腹地商路的联盟','tension':'海路季节、粮食与内陆商队安全','status':'为亚欧非旅行测试添加的架空草案'}]
    world['belief_systems'] = [
        {'id':'sacred','name':'圣教','description':'强调誓约与共同体的架空信仰，不引用现实教义与现实宗教评价'},
        {'id':'crescent','name':'新月教','description':'架空王朝的重要信仰传统，各地实践允许差异'},
        {'id':'shi','name':'释教','description':'强调自省、行旅与记忆的架空宗派，仅沿用用户指定名称'},
        {'id':'dao','name':'道教','description':'东方修行传统之一，不代表全部天朝文化'},
        {'id':'flame','name':'灯火会','description':'崇尚守灯、见证与旅人契约的架空信仰；替代尚未定稿的神道教名称，待作者确认'}]
    world['energy_system'] = {
        'common_origin':'同一可利用的超自然能量，东方称灵气，西方称气；灵力与魔力是运用方式与称谓差异。',
        'schools':[{'id':'five','name':'五行学说','elements':['金','木','水','火','土']}, {'id':'four','name':'四元素学说','elements':['土','水','气','火']}],
        'translation_rule':'两套分类是不同文明的解释模型，不强行逐项等同；同名的气可能是总能量或元素，需结合语境。',
        'tiers':[{'id':'1','east':'炼气','west':'魔法学徒'}, {'id':'2','east':'筑基','west':'魔法使'}, {'id':'3','east':'金丹','west':'大魔法使'}, {'id':'4','east':'元婴','west':'圣者'}],
        'ceiling':'顶尖者可摧山开海，但不是日常行动尺度。',
        'provisional_limits':['大型施术需要准备、耗能与恢复，不能无代价持续使用', '无默认读心、复活或时间旅行；若要加入必须由作者定义', '境界不自动赋予外交合法性、语言知识、财富或可信度'],
        'longevity':'修行可延寿并改变继承与王朝延续；不据此保证王朝永不衰亡，具体年限待定。'}
    world['travel_and_language'] = {
        'trade':'国家间已有商旅和使节往来；玩家未知不等于当地社会从未交流。',
        'translation_machine':'万言机需要接触语料学习语言。礼仪、隐喻、谎言和缺失语境无法仅靠逐字翻译解决。学习速度与能源代价待定。',
        'map_scale':'暂用现实轮廓作为示意底图，未设定架空世界倍率；时间消耗为测试游戏单位，不等于真实洲际旅行小时。',
        'fog':'地理迷雾代表主角掌握的信息层级，可知道地区存在而未掌握当地道路。'}
    world['information_protocol'] = {'source':'客观记录拥有来源 ID 与时间，传播链引用它',
        'transforms':['截取部分内容','数字夸大或缩小'], 'epistemic_rule':'翻译输出、NPC 转述与玩家所闻都不自动成为客观事实',
        'examples':['国王继位消息可能只传到庆典而缺失争议背景','村庄道路封闭3日可能被转述成9日']}
    story['public_lore'] = {'premise':'第一人称奇幻史诗：我从东方天朝出发，沿商路和海路认识不同文明。',
        'energy':'东方灵气与西方气源自同一种力量；五行与四元素是不同解释体系。',
        'realms':'炼气、筑基、金丹、元婴；魔法学徒、魔法使、大魔法使、圣者。不同文明的同阶大体相当，手段与属性仍然重要。',
        'society':'长寿修行者影响王朝、贸易与知识；这个世界不唯战力论。',
        'language':'我携带可学习语言的万言机，但它无法替我判断信息真假。',
        'known_regions':['天朝','新月沃土王朝','西方诸国'],
        'style':'以见闻而非全知视角呈现；宗教与政治实体采用架空设定。'}
    scenes = [
        {'id':'capital_chapter','title':'天朝都城 · 离乡前夜','kind':'city','location_ids':['tianchao_capital'],'expected_turns':20,'information_scope':['出行准备','文化常识','语言机器']},
        {'id':'road_chapter','title':'西行商路 · 关城见闻','kind':'journey','location_ids':['western_pass'],'expected_turns':16,'information_scope':['通关','方言','商路规则']},
        {'id':'oasis_chapter','title':'新月商驿 · 流言与交易','kind':'city','location_ids':['crescent_oasis'],'expected_turns':24,'information_scope':['王朝商贸','消息来源','真假传闻']},
        {'id':'port_chapter','title':'西方海港 · 异文明初见','kind':'city','location_ids':['western_port'],'expected_turns':24,'information_scope':['诸国关系','航线','四元素学说']},
        {'id':'south_chapter','title':'南岸灯港 · 潮汐与书信','kind':'city','location_ids':['south_lantern_port'],'expected_turns':24,'information_scope':['南方海路','信件转述','港口契约']}
    ]
    existing = {x['id']: x for x in story.setdefault('major_scenes', [])}
    for scene in scenes: existing.setdefault(scene['id'], scene)
    story['major_scenes'] = list(existing.values())
    associations = dict(zip(['departure','pass_translation','oasis_rumor','port_contact'],[x['id'] for x in scenes]))
    for event in story['events']:
        if event['id'] in associations:
            event.setdefault('major_scene_id', associations[event['id']])
            event['max_turns'] = max(event.get('max_turns',8),20)
    if not any(l['id']=='south_lantern_port' for l in story['locations']):
        story['locations'].append({'id':'south_lantern_port','name':'南岸灯港','description':'海风吹过灯塔与译信铺，旅人在此等待航期。','neighbors':['western_port'],'scenes':['letters','harbor_oath'],'coordinates':[29.9,31.2]})
    port = next(l for l in story['locations'] if l['id']=='western_port')
    if 'south_lantern_port' not in port['neighbors']: port['neighbors'].append('south_lantern_port')
    first = {'id':'south_letters','title':'译信铺的两种说法','major_scene_id':'south_chapter','location_id':'south_lantern_port','participants':[],
             'player_goal':'对照书信与转述，区分遗漏与谎言','hidden_goal':'演示同一城市场景中的连续事件','entry_flags':{},'next_events':['south_oath'],'max_turns':20,'player_enters':True,
             'actions':[{'id':'read_letter','label':'对照书信中的措辞','effects':[{'op':'fact','text':'船队延航的正式理由是季风，书信没有提到战争。','visible':True}],'ends_event':True,'success_text':'我读到书信只说季风延误。它没有证明所有街头传闻都是假的，却足以让我暂缓判断。'}]}
    second = {'id':'south_oath','title':'灯塔下的旅人契约','major_scene_id':'south_chapter','location_id':'south_lantern_port','participants':[],
              'player_goal':'了解出海契约，决定今后的旅行方向','hidden_goal':'同一主要场景沿用上一段对话','entry_flags':{},'next_events':[],'max_turns':20,'player_enters':True,
              'actions':[{'id':'record_oath','label':'记下港口的契约规则','effects':[{'op':'fact','text':'港口契约要求写明货物、见证人和失约责任。','visible':True}],'ends_event':True,'success_text':'我把见证人与失约责任记在册页上。力量能越过高墙，却不能替代一句经人见证的承诺。'}]}
    for event in (first,second):
        if not any(e['id']==event['id'] for e in story['events']): story['events'].append(event)
    port_event = next(e for e in story['events'] if e['id']=='port_contact')
    if 'south_letters' not in port_event['next_events']: port_event['next_events'].append('south_letters')
    story['authoring_status'] = {'source':'世界观.docx','revision_label':'世界观扩充与主要场景 v0.2','unconfirmed':'source_notes 中的补充草案与待定项可继续修改'}
    return package


if __name__ == '__main__':
    store = Store(ROOT / 'data/textiledream.sqlite3')
    runtime = Runtime(store, ROOT)
    original = runtime.package()
    if original['story'].get('authoring_status', {}).get('revision_label') == '世界观扩充与主要场景 v0.2':
        updated = original
    else:
        updated = expand(original)
        revision = runtime.commit_package(updated['story'], updated['characters'], '依据世界观.docx补充文明、能量、信仰、旅途与主要场景 v0.2')
        updated = runtime.package(revision)
    (ROOT / 'world_packages/玄陆_世界包.json').write_text(json.dumps(updated['story'],ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT / 'world_packages/玄陆_完整组合包_v0.2.json').write_text(json.dumps({'story':updated['story'],'characters':updated['characters']},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Published revision:', updated['id'], 'major scenes:',len(updated['story']['major_scenes']))
