"""Authored short adventures. Export sources or install through the running API."""
import argparse
import json
from pathlib import Path
import urllib.request
import urllib.parse

from app import attributes

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/playable-scenes'


def flag(key, value=True):
    return {'op': 'flag', 'id': key, 'value': value}


def money(amount):
    return {'op': 'resource', 'id': 'pence', 'delta': amount}


def info(text):
    return {'op': 'information', 'text': text, 'known_by': ['player'], 'confirmed': True}


def action(id, label, text, *, effects=(), requires=None, cost=0, end=False,
           check=None, failure='', success=(), fail=(), risk='', social=None, hours=0, aliases=()):
    row = {'id': id, 'label': label, 'success_text': text,
           'effects': list(effects), 'requires': requires or {}, 'ends_event': end,
           'duration_hours': hours, 'intent_aliases': list(aliases)}
    if cost:
        row['costs'] = {'pence': cost}
    if check:
        row.update(check={'attribute': check[0], 'difficulty': check[1]},
                   failure_text=failure, success=list(success), failure=list(fail))
    if risk:
        row.update(requires_confirmation=True, risk_notice=risk)
    if social:
        row['social'] = social
    return row


def event(id, title, place, people, actions, next_id=None, goal=''):
    return {'id': id, 'title': title, 'location_id': place, 'participants': ['player'] + people,
            'player_enters': True, 'player_goal': goal or title, 'next_events': [next_id] if next_id else [],
            'entry_flags': {}, 'exit_flag': 'finished_' + id, 'max_turns': 40, 'actions': actions}


def person(id, name, place, personality, role='次要角色'):
    return {'id': id, 'name': name, 'public_name': name, 'role': role, 'location_id': place,
            'personality': personality, 'state': {}, 'attributes': {k: 55 for k in attributes.AXES}}


def choice(line, trust=0, **flags):
    return {'line': line, 'trust_delta': trust, 'flags': flags}


def base(key, title, premise, places, people, actors, law, events, endings, route, alternative):
    for index, row in enumerate(endings):
        row['priority'] = len(endings) - index
        row['condition']['not_flags'] = [other['id'] for other in endings if other is not row]
    story = {'id': 'short_' + key, 'title': title, 'premise': premise,
             'worldview': {'premise': premise + ' 架空西幻港郡；1镑=20先令=240便士，1先令=12便士。'
                           '价格为游戏设计值。允许恶作剧，但人物有自己的底线。'},
             'character_package_id': 'short_' + key + '_cast',
             'locations': places, 'events': events, 'items': [],
             'knowledge': [{'id': 'currency', 'title': '港郡钱币与行情', 'visibility': 'public',
                            'keywords': ['钱', '便士', '先令', '镑', '物价'],
                            'content': '以便士记账。12便士=1先令，20先令=1镑。麦酒2便士，渡船12便士，'
                                       '半日短工约6至12便士。这里只是游戏行情，不是历史价格考证。', 'requires': []}],
             'mechanics': {
                 'attributes': attributes.specification(),
                 'local': {'turn_hours': 0, 'travel_hours': 1, 'resources': [
                     {'id': 'pence', 'name': '旅费（12便士=1先令）', 'unit': '便士', 'initial': 18, 'maximum': 10000}]},
                 'scene_judgment': {'version': 1, 'law': law, 'actors': actors},
                 'endings': {'version': 1, 'endings': endings},
                 'start_profiles': {'version': 1, 'default_profile': 'traveller', 'profiles': [{
                     'id': 'traveller', 'title': title, 'summary': premise[:190], 'identity': '手头不宽裕的外乡旅人',
                     'location': places[0]['id'], 'goal': events[0]['player_goal'], 'entry_event': events[0]['id'],
                     'relations': {p['id']: {'trust': .5, 'note': '初次相识'} for p in people},
                     'known': [{'id': 'opening', 'text': premise[:450]}]}]}}}
    characters = {'id': story['character_package_id'], 'title': title + '·人物',
                  'characters': [person('player', '我', places[0]['id'], {}, '主角')] + people}
    return {'story': story, 'characters': characters,
            'playtest': {'target_minutes': [15, 20], 'measured_minutes': None,
                         'route': route, 'alternative': alternative,
                         'pacing': '约12–18次行动，穿插6–10轮追问、阅读与权衡；快速点击会更短。'}}


def place(id, name, description, neighbors):
    return {'id': id, 'name': name, 'description': description, 'neighbors': neighbors, 'scenes': []}


def ending(id, title, summary, kind='saved'):
    return {'id': id, 'title': title, 'summary': summary, 'kind': kind,
            'condition': {'all_flags': {id: True}}}


def tavern():
    actors = {
        'bess': {'values': '勤恳、看重尊严；帮助可以挣得信任，拿贴身衣物公开羞辱会触到底线。',
                 'choices': {
                     'thanks': choice('贝丝记下了你的帮助，愿意替你作一次介绍。', .15, tavern_friend=True),
                     'warn': choice('贝丝严肃警告你停止拿她的私人物品开玩笑。', -.15, warned=True),
                     'ban': choice('贝丝要求你归还衣物，并明确拒绝继续招待你。', -.3, tavern_banned=True),
                     'report': choice('贝丝决定去报官；此刻卫兵尚未接报，也没有罚款落账。', -.3, report_planned=True),
                     'accept': choice('贝丝接受了归还与赔礼，但说明信任需要慢慢修复。', .1, amends=True),
                     'reserve': choice('贝丝收回衣物，保留戒心，没有立即原谅。', 0, amends=True)}},
        'ferryman': {'values': '务实，守约，愿意用有偿劳动帮助手头紧的旅人。',
                     'choices': {'respect': choice('船工承认你按约办事，替你留好一个座位。', .1)}}}
    places = [place('hall', '铜杯酒馆', '贝丝把空账夹放上柜台。码头的船傍晚出发，她愿付8便士找回丢在后院的运货单。麦酒每杯2便士。', ['yard', 'quay']),
              place('yard', '酒馆后院', '运货木箱靠着墙。贝丝在另一头清点空桶；近处晾衣绳上有她的贴身衬裤，伸手可及，但不是无主物。', ['hall']),
              place('quay', '旧码头', '船工正收绳，船票12便士，也可先替他搬一批绳箱挣6便士。', ['hall'])]
    events = [event('welcome', '一杯酒与一份委托', 'hall', ['bess'], [
        action('read_prices', '看看价目与船期', '我确认了麦酒2便士、船票12便士。', effects=[flag('prices'), info('酒馆找单报酬8便士；渡船票12便士。')]),
        action('buy_ale', '买一杯麦酒（2便士）', '我付了2便士，喝下一杯麦酒。', cost=2, requires={'tavern_banned': False}, aliases=['喝酒', '买酒']),
        action('ask_job', '问清运货单与报酬', '贝丝指向后院木箱：单据印有蓝色船锚。找到后她支付8便士。', effects=[flag('job_known'), info('寻找蓝色船锚印的运货单，不需要拿走别人的衣物。')]),
        action('go_search', '接下委托，准备去后院', '我答应找单，走到后门。接下来可前往后院。', requires={'job_known': True}, end=True),
    ], 'yard_search', '挣到船费，决定怎样对待酒馆里的人。'),
    event('yard_search', '木箱与晾衣绳', 'yard', ['bess'], [
        action('inspect_crates', '仔细查看木箱', '我在木箱缝里发现了蓝色印章。', check=('wisdom', .45),
               success=[flag('invoice'), info('蓝色船锚运货单夹在木箱底部。')],
               failure='我没能一眼找到单据，可以花时间逐只搬开木箱。', effects=[flag('searched')]),
        action('search_slowly', '花一小时逐箱检查', '我逐箱查看，终于找到了运货单。', requires={'invoice': False}, hours=1,
               effects=[flag('invoice'), flag('searched'), info('运货单已经找到。')]),
        action('steal_linen', '尝试偷走晾衣绳上的衬裤', '我取下了衬裤。贝丝没有看见这次取物；我还没有展示它。',
               requires={'linen_held': False}, check=('agility', .6), aliases=['偷内裤', '偷衬裤'],
               success=[flag('linen_held'), {'op': 'resource', 'id': 'linen', 'delta': 1}],
               failure='我伸手时碰响了衣夹，贝丝看见了这次未遂偷取。',
               social={'failure': {'bess': ['warn', 'report']}},
               risk='这是偷取有主私物；失败可能被发现。成功也不等于可以公开炫耀。'),
        action('show_linen', '向贝丝炫耀偷来的衬裤', '我举起衬裤炫耀。贝丝亲眼看见，偷取已暴露。', requires={'linen_held': True},
               effects=[flag('exposed')], social={'success': {'bess': ['ban', 'report']}},
               risk='会让贝丝知道你拿了衣物，可能损害关系、被拒绝招待或被报官。'),
        action('return_linen', '归还衬裤并赔礼', '我归还了衬裤，并为拿取私物赔礼。', requires={'linen_held': True},
               effects=[flag('linen_held', False), {'op': 'resource', 'id': 'linen', 'delta': -1}],
               social={'success': {'bess': ['reserve', 'accept']}}),
        action('finish_yard', '带着运货单回到柜台', '我收好运货单，准备回酒馆交付。', requires={'invoice': True}, end=True),
    ], 'settle'),
    event('settle', '报酬与关系', 'hall', ['bess'], [
        action('deliver_invoice', '交付运货单，领取8便士', '我交出运货单。贝丝按约付了8便士；这笔报酬不是原谅的证明。',
               effects=[money(8), flag('paid')]),
        action('help_barrels', '替贝丝把空桶归位', '我帮贝丝归拢空桶，不另索报酬。', hours=1,
               requires={'tavern_banned': False, 'report_planned': False}, social={'success': {'bess': ['thanks']}}),
        action('leave_for_quay', '结束交谈，去码头', '我把余下的话留在酒馆，准备前往码头。', requires={'paid': True}, end=True),
    ], 'departure'),
    event('departure', '傍晚的渡船', 'quay', ['ferryman'], [
        action('dock_work', '搬一批绳箱，挣6便士', '我花一小时搬好绳箱，船工支付6便士。', hours=1, effects=[money(6)],
               social={'success': {'ferryman': ['respect']}}),
        action('sail', '买船票离开（12便士）', '我付清船票，登上渡船。酒馆里的关系与这次选择一起留在存档中。', cost=12,
               effects=[flag('sail')], end=True),
        action('stay', '留在港口，改日再走', '我留下旅费，决定明天再走。今天建立或破坏的关系不会因此消失。', effects=[flag('stay')], end=True),
    ])]
    data = base('tavern', '铜杯酒馆：一条衬裤的风波', '你有18便士，想赶上傍晚渡船。酒保贝丝丢了运货单，愿付8便士寻回。你可以认真帮忙，也可以惹出一场需要收拾的恶作剧。',
                places, [person('bess', '贝丝', 'hall', {'责任': .8, '谨慎': .6}), person('ferryman', '船工托马', 'quay', {'责任': .7})], actors,
                '港郡禁止盗取私物。受害者可要求归还、拒绝服务或报官；报官意愿不等于卫兵已知或罚款已执行。', events,
                [ending('sail', '带着后果出发', '你付清船票离港。钱账结清，但在人心里留下了什么，取决于你如何对待贝丝。'), ending('stay', '留下的旅人', '你留在港口，保留旅费与尚待修复的关系。', 'negotiated')],
                ['read_prices', 'buy_ale', 'ask_job', 'go_search', '@yard', 'inspect_crates', '?search_slowly', 'finish_yard', '@hall', 'deliver_invoice', 'help_barrels', 'leave_for_quay', '@quay', 'dock_work', 'sail'],
                ['ask_job', 'go_search', '@yard', 'search_slowly', 'steal_linen', '?show_linen', '?return_linen', 'finish_yard', '@hall', 'deliver_invoice', 'leave_for_quay', '@quay', 'stay'])
    # During the yard event Bess is physically present; the routine follows game hours.
    # Both hall and yard observations are authored; movement of the scene cast is explicit below.
    data['story']['mechanics']['local']['resources'].append({'id': 'linen', 'name': '暂持的贝丝衬裤', 'unit': '件', 'initial': 0, 'maximum': 1})
    data['story']['mechanics']['scene_judgment']['scene_cast'] = {'welcome': {'bess': 'hall'}, 'yard_search': {'bess': 'yard'}, 'settle': {'bess': 'hall'}}
    return data


def bridge():
    actors = {
        'guard': {'values': '守规矩，担心桥塌后担责；会听证据，但讨厌当众被指作贼。', 'choices': {
            'listen': choice('桥吏奥伦承认你提供了实际证据，愿意听一个替代方案。', .15, guard_listens=True),
            'stern': choice('奥伦要求你收回无证据的指控，谈判气氛明显变差。', -.2, guard_offended=True),
            'explain': choice('奥伦压住怒气，再次说明通行费的用途，没有追加罚款。', -.05),
            'respect': choice('奥伦认可你的修桥劳动，按公开约定免去本次通行费。', .15, toll_waived=True)}},
        'mara': {'values': '急着送药，不愿看到别人为她送命；喜欢实际帮助。', 'choices': {
            'grateful': choice('药师玛拉感谢你探清路况，愿意支付约定的护送费。', .15)}}}
    places = [place('bridge_gate', '雾桥岗亭', '木牌写着通行8便士，参与修桥者免本次费用。桥吏奥伦守着栏杆，药师玛拉的药箱等着过河。', ['riverbank', 'far_bank']),
              place('riverbank', '桥下河岸', '一处旧渡口露出泥地，断裂的横梁能从这里看清。河水并不适合临时游过去。', ['bridge_gate']),
              place('far_bank', '对岸药棚', '送药的人在棚下等候，能听见河对面的敲钉声。', ['bridge_gate'])]
    events = [event('gate', '谁有权收这笔钱', 'bridge_gate', ['guard', 'mara'], [
        action('read_toll', '读清收费与免票条件', '木牌明示：通行8便士，修桥劳动可抵本次费用。', effects=[flag('terms'), info('桥费8便士；修桥劳动可免票。')]),
        action('hear_mara', '问玛拉为什么赶路', '玛拉要把药箱送到对岸，愿付你12便士护送费，不要求你冒险下水。', effects=[flag('escort'), info('护送药箱抵达可得12便士。')]),
        action('accuse', '当众指责桥吏借机敛财', '我当众指责奥伦敛财，但手头还没有贪污证据。',
               risk='公开指控可能破坏谈判关系；不是已经查明犯罪。', social={'success': {'guard': ['stern', 'explain']}}),
        action('inspect_route', '先去桥下核实路况', '我决定先看实物，再讨论费用。接下来前往桥下河岸。', requires={'terms': True, 'escort': True}, end=True),
    ], 'bank'),
    event('bank', '横梁上的裂口', 'riverbank', [], [
        action('read_damage', '辨认横梁裂口', '我辨认出受潮开裂的横梁，收费至少有实际维修对象。', check=('wisdom', .45),
               success=[flag('evidence'), info('桥下横梁受潮开裂，需要加固。')], failure='雾气遮住了裂口，我需要靠近慢慢观察。'),
        action('slow_inspection', '沿岸慢慢查看一小时', '我沿岸绕到能看清的位置，确认横梁确实损坏。', hours=1, requires={'evidence': False},
               effects=[flag('evidence'), info('横梁确实损坏；河上没有可用的免费渡船。')]),
        action('find_timber', '找出堆放的修桥木料', '我找到岗亭公开堆放的备用木料，没有拿走它们。', effects=[flag('timber')]),
        action('return_gate', '带着证据返回岗亭', '我准备回岗亭提出具体方案。', requires={'evidence': True, 'timber': True}, end=True),
    ], 'bargain'),
    event('bargain', '钱、劳动与面子', 'bridge_gate', ['guard', 'mara'], [
        action('show_evidence', '说明裂梁与木料的位置', '我说明了实际看到的损坏，没有把猜测当事实。', effects=[flag('explained')],
               social={'success': {'guard': ['listen'], 'mara': ['grateful']}}),
        action('repair_bridge', '尝试帮忙加固横梁', '我按桥吏指示固定好横梁，得到本次免票。', check=('strength', .5), hours=1,
               requires={'explained': True}, success=[flag('pass')], failure='我没能稳住重木，没有完成修复；可以改付通行费。',
               social={'success': {'guard': ['respect']}}),
        action('pay_toll', '支付8便士通行费', '我支付了8便士，拿到通行许可。', cost=8, requires={'pass': False}, effects=[flag('pass')]),
        action('cross', '与玛拉一起过桥', '我护着药箱走向桥面。接下来前往对岸药棚。', requires={'pass': True}, end=True),
    ], 'delivery'),
    event('delivery', '药箱落地之后', 'far_bank', ['mara'], [
        action('deliver_medicine', '交付药箱并领取12便士', '药箱完整交付，我收到约定的12便士。', effects=[money(12), flag('delivered')]),
        action('donate', '拿出4便士添置药棚灯油', '我把4便士交给药棚作为灯油钱。', requires={'delivered': True}, cost=4, effects=[flag('donated')]),
        action('finish_bridge', '记录这次通行，继续上路', '我记下今天用钱、劳动与证据换来的路。', requires={'delivered': True}, effects=[flag('delivered_end')], end=True),
        action('remain_helper', '留在药棚帮忙整理', '我决定留下帮忙，暂缓自己的旅程。', requires={'delivered': True}, effects=[flag('helper_end')], end=True),
    ])]
    data = base('bridge', '雾桥：八便士的路', '你护送药师玛拉的药箱过河。桥费8便士，护送报酬12便士；你可以支付、查证后以劳动换票，也可以先把关系弄僵。',
                places, [person('guard', '桥吏奥伦', 'bridge_gate', {'责任': .9, '谨慎': .8}), person('mara', '药师玛拉', 'bridge_gate', {'责任': .8})], actors,
                '桥费公开为8便士，修桥可免一次。未经证实的贪污指控不是事实；桥吏无权临时增设罚款。', events,
                [ending('delivered_end', '药箱与通行证', '药箱送达，你得到了报酬，也看到了规则背后的实际需要。'), ending('helper_end', '多留一盏灯', '药箱已送达，你留在药棚帮忙。', 'negotiated')],
                ['read_toll', 'hear_mara', 'inspect_route', '@riverbank', 'read_damage', '?slow_inspection', 'find_timber', 'return_gate', '@bridge_gate', 'show_evidence', 'repair_bridge', '?pay_toll', 'cross', '@far_bank', 'deliver_medicine', 'donate', 'finish_bridge'],
                ['read_toll', 'hear_mara', 'accuse', 'inspect_route', '@riverbank', 'slow_inspection', 'find_timber', 'return_gate', '@bridge_gate', 'show_evidence', 'pay_toll', 'cross', '@far_bank', 'deliver_medicine', 'remain_helper'])
    data['story']['mechanics']['scene_judgment']['scene_cast'] = {'delivery': {'mara': 'far_bank'}}
    return data


def market():
    actors = {
        'seller': {'values': '精打细算，想保住生意名声；能接受有证据的议价，不接受无端称其下毒。', 'choices': {
            'respect': choice('粮商艾达认可你先查证再议价，愿意继续与你交易。', .15),
            'resent': choice('艾达要求你澄清没有证据的下毒指控，信任受到损害。', -.2, seller_offended=True),
            'defend': choice('艾达拿出登记簿为自己辩解，没有凭你的指控承认下毒。', -.1)}},
        'baker': {'values': '关心能否开炉和雇工生计，不愿让潮粮混进好粮。', 'choices': {
            'trust': choice('面包师诺尔认可你把品质和价格讲清楚，下次愿意再托你办事。', .15, baker_friend=True)}}}
    places = [place('market', '雨后的粮市', '最后一袋干麦标价12便士，旁边还有一袋受潮麦。粮商艾达看着人群；诺尔的面包铺等着开炉。', ['storehouse', 'bakery']),
              place('storehouse', '粮仓门廊', '门廊挂着这一批货的登记簿，检验盘里分别放着干麦和受潮麦样本。', ['market']),
              place('bakery', '未开炉的面包铺', '炉火尚未点起。诺尔承诺干麦送达支付16便士，若只有潮麦则宁可停炉。', ['market'])]
    events = [event('request', '最后一袋麦子', 'market', ['seller'], [
        action('read_offer', '核对两袋麦子的价格', '干麦12便士，受潮麦便宜但不适合这次烘焙委托。', effects=[flag('offer')]),
        action('read_order', '读诺尔留下的委托条', '诺尔只收干麦，送到面包铺支付16便士。', effects=[flag('order'), info('面包铺只收干麦，送达报酬16便士；不接受混入潮粮。')]),
        action('poison_accusation', '喊艾达在麦子里下毒', '我喊出下毒指控，但当前没有任何毒物证据。',
               risk='可能损害艾达名誉及你们的关系；受潮不等于下毒。', social={'success': {'seller': ['resent', 'defend']}}),
        action('go_storehouse', '先去门廊核对登记与样本', '我准备查看公开样本与登记簿，再决定购买。', requires={'offer': True, 'order': True}, end=True),
    ], 'inspection'),
    event('inspection', '账册与麦粒', 'storehouse', [], [
        action('inspect_grain', '比较干麦与潮麦', '我认出受潮痕迹，确认干麦可以区分出来。', check=('wisdom', .4),
               success=[flag('quality'), info('潮麦有结块和受潮气味，不是毒物证据。')], failure='我暂时拿不准，需要对照标注样本慢慢看。'),
        action('compare_samples', '花一小时对照标注样本', '我反复对照，终于能区分两袋麦子的状态。', hours=1, requires={'quality': False}, effects=[flag('quality')]),
        action('read_ledger', '查看登记簿中的进货日期', '账册记录昨夜搬运受雨，卖方没有证据表明下毒；干麦挂牌12便士。', effects=[flag('ledger'), info('账册记录受雨搬运；没有查到毒物证据。')]),
        action('return_market', '带着核对结果返回粮市', '我准备回去按事实谈价格。', requires={'quality': True, 'ledger': True}, end=True),
    ], 'purchase'),
    event('purchase', '怎样成交', 'market', ['seller'], [
        action('explain_quality', '只谈品质，不作无证据指控', '我说明干麦与潮麦的区别，没有把受潮说成下毒。', effects=[flag('explained')], social={'success': {'seller': ['respect']}}),
        action('bargain', '尝试把干麦谈到10便士', '艾达同意以10便士出售这袋干麦。尚未付款，也尚未取得麦子。', requires={'explained': True}, check=('social', .5),
               success=[flag('discount')], failure='艾达没有接受降价，仍按12便士出售。'),
        action('buy_discount', '按议定价买干麦（10便士）', '我付了10便士，取得一袋干麦。', requires={'discount': True, 'grain': False}, cost=10,
               effects=[flag('grain'), {'op': 'resource', 'id': 'wheat', 'delta': 1}]),
        action('buy_full', '按挂牌价买干麦（12便士）', '我付了12便士，取得一袋干麦。', requires={'grain': False, 'discount': False}, cost=12,
               effects=[flag('grain'), {'op': 'resource', 'id': 'wheat', 'delta': 1}]),
        action('carry_grain', '带干麦去面包铺', '我收好干麦，准备去面包铺交付。', requires={'grain': True}, end=True),
    ], 'baking'),
    event('baking', '开炉之前', 'bakery', ['baker'], [
        action('deliver_grain', '交付干麦，领取16便士', '我交付一袋干麦，诺尔支付16便士，麦子不再由我持有。',
               effects=[money(16), {'op': 'resource', 'id': 'wheat', 'delta': -1}, flag('grain', False), flag('delivered')],
               social={'success': {'baker': ['trust']}}),
        action('buy_bread', '花2便士预订一份面包', '我付了2便士预订面包；面包尚未烤好。', cost=2, requires={'delivered': True}, effects=[flag('bread_reserved')]),
        action('keep_profit', '结清账目，留下利润', '我结清这趟交易，把余钱留作下一段旅费。', requires={'delivered': True}, effects=[flag('profit_end')], end=True),
        action('share_profit', '捐出4便士给铺里的学徒', '我从这趟收入中拿出4便士给学徒添饭。', requires={'delivered': True}, cost=4, effects=[flag('shared_end')], end=True),
    ])]
    data = base('market', '雨后粮市：最后一袋麦子', '你带着18便士替面包师采购干麦。成本、品质与名声都在这笔小交易里：诺尔收货支付16便士，你要先辨认哪袋值得买。',
                places, [person('seller', '粮商艾达', 'market', {'贪婪': .6, '谨慎': .7}), person('baker', '面包师诺尔', 'bakery', {'责任': .8})], actors,
                '不得以潮粮冒充干粮；未经证实不得把受潮说成下毒。议价自愿，成交前不能直接拿走商品。', events,
                [ending('profit_end', '一笔干净的小生意', '你按实物品质完成交易，获得利润与合作机会。', 'traded'), ending('shared_end', '分出去的四便士', '你完成交易，并把一部分收入留给学徒。', 'negotiated')],
                ['read_offer', 'read_order', 'go_storehouse', '@storehouse', 'inspect_grain', '?compare_samples', 'read_ledger', 'return_market', '@market', 'explain_quality', 'bargain', '?buy_discount', '?buy_full', 'carry_grain', '@bakery', 'deliver_grain', 'buy_bread', 'keep_profit'],
                ['read_offer', 'read_order', 'poison_accusation', 'go_storehouse', '@storehouse', 'compare_samples', 'read_ledger', 'return_market', '@market', 'explain_quality', 'buy_full', 'carry_grain', '@bakery', 'deliver_grain', 'share_profit'])
    data['story']['mechanics']['local']['resources'].append({'id': 'wheat', 'name': '干麦', 'unit': '袋', 'initial': 0, 'maximum': 1})
    return data


def town_day():
    """One town, one wallet, and explicitly authored consequences between scenes."""
    actors = {
        'bess': {'values': '看重尊严，也看重把收入分给学徒的实际行动。', 'choices': {
            'trust': choice('贝丝听完诺尔的收据，认可你分享利润，写了船工介绍信。', .2, introduced=True),
            'warn': choice('贝丝要求你把衣物放下；赔礼不代表她立刻信任你。', -.2)}},
        'guard': {'values': '传闻不是定罪证据，但赊账是他自行承担的信用风险。', 'choices': {
            'respect': choice('奥伦确认你完成修桥劳动，提醒你须在截止前登记免票。', .1)}},
    }
    places = [
        place('town_hall', '铜杯酒馆', '早晨八点。贝丝的柜台旁挂着待收的衣物。粮市往返各一小时，雾桥也需一小时。', ['town_market', 'town_bridge']),
        place('town_market', '雨后粮市', '艾达卖最后一袋干麦，12便士；诺尔在同一市场的烤炉边收货，支付16便士。', ['town_hall', 'town_bridge']),
        place('town_bridge', '雾桥', '奥伦守着8便士的桥口。桥另一头的傍晚船免费载客；必须在傍晚六点前办好通行。', ['town_hall', 'town_market']),
    ]
    opening = event('town_open', '八点的铜杯', 'town_hall', ['bess'], [
        action('day_terms', '读清今天的委托、桥费与船期', '干麦成本12便士，送达收16便士。桥费8便士；傍晚六点（开局后10小时）截止，错过可留下做工等明天。', effects=[flag('day_terms'), info('今天傍晚六点前办好通行；酒馆到粮市、粮市到酒馆、酒馆到雾桥均一小时。')]),
        action('day_breakfast', '付清食宿欠账（6便士）', '我支付昨夜食宿6便士，剩12便士用于采购。', cost=6, effects=[flag('breakfast_paid')]),
        action('day_prank', '当着贝丝把衬裤套在头上再归还', '贝丝亲眼看见我擅拿衣物又放回。去桥口送桶的跑腿听见争执，将转述此事；奥伦只能听到传闻，不是目击者。', risk='会破坏信用；桥吏可能拒绝赊账，谈价更难。衣物归还不抹去冒犯。', effects=[flag('day_prank')], social={'success': {'bess': ['warn']}}),
        action('day_to_market', '接下诺尔的采购委托，去粮市', '我带着采购钱离开柜台。', requires={'day_terms': True, 'breakfast_paid': True}, end=True),
    ], 'town_trade', '在傍晚六点前办好雾桥通行，赶上傍晚船。')
    trade = event('town_trade', '同一笔钱的两种用途', 'town_market', ['seller', 'baker'], [
        action('day_inspect', '辨认哪一袋是干麦', '我认出了干麦的松散颗粒。', check=('wisdom', .4), hours=1, success=[flag('day_quality')], failure='我看不准；诺尔愿意用一小时带我对照标注样本。', fail=[flag('day_inspect_failed'), info('诺尔可带你对照样本，不需要再掷骰。')]),
        action('day_compare', '请诺尔带着对照样本（一小时）', '诺尔带我逐粒对照，确认了干麦。', requires={'day_quality': False}, hours=1, effects=[flag('day_quality')]),
        action('day_buy', '买下干麦（12便士）', '我支付12便士，手头现金用尽，取得干麦；现在不能再用这笔钱付桥费。', cost=12, requires={'day_quality': True}, effects=[flag('day_grain'), {'op': 'resource', 'id': 'wheat', 'delta': 1}]),
        action('day_deliver', '把干麦送到市场烤炉，收16便士', '诺尔验收干麦支付16便士；其中12便士归还采购本钱，4便士是利润。', hours=1, requires={'day_grain': True}, effects=[money(16), flag('day_grain', False), flag('day_delivered'), {'op': 'resource', 'id': 'wheat', 'delta': -1}]),
        action('day_share', '把4便士利润分给学徒，请诺尔写收据', '我拿出4便士给学徒添饭，诺尔写下署名收据，可带回给贝丝看。', cost=4, requires={'day_delivered': True}, effects=[flag('day_shared'), info('诺尔的收据：旅人把4便士采购利润分给了学徒。')]),
        action('day_lamp', '再捐4便士给市场灯油', '我又捐出4便士；若已分享利润，现在只余8便士，刚好够原价桥费。', cost=4, requires={'day_shared': True}, effects=[flag('day_lamp')]),
        action('day_return', '结清交易，带收据回酒馆', '我离开市场，回铜杯酒馆取行李。', requires={'day_delivered': True}, end=True),
    ], 'town_return')
    rumor = '跑腿转述：酒馆里有人把贝丝的衬裤套在头上，据说就是这位旅人；奥伦没有亲眼见到。'
    rumor_effect = {'op': 'information', 'text': rumor, 'known_by': ['player', 'guard'], 'confirmed': False}
    home = event('town_return', '带回来的不只是钱', 'town_hall', ['bess'], [
        action('day_introduction', '出示分享利润的收据，请贝丝介绍船工', '贝丝核对收据，愿意为这次善意作介绍；奥伦接受船工介绍信可免本次桥费。', requires={'day_shared': True, 'day_prank': False}, social={'success': {'bess': ['trust']}}),
        action('day_amends', '赔付洗衣与停工损失（8便士）', '贝丝接受8便士的损失赔付；已经传出去的故事不会因此收回。', cost=8, requires={'day_prank': True}, effects=[flag('day_amends')]),
        action('day_to_bridge', '取好行李，前往雾桥', '我离开酒馆，去办通行。', requires={'day_prank': False}, end=True),
        action('day_rumor_to_bridge', '跟送桶跑腿一起去雾桥', '跑腿先走一步，把酒馆争执转述给奥伦；贝丝告诉我这消息已经传开。奥伦只听到传闻，不是目击者。', requires={'day_prank': True}, effects=[flag('rumor_arrived'), rumor_effect], end=True),
    ], 'town_depart')
    depart = event('town_depart', '传闻、信用与八便士', 'town_bridge', ['guard'], [
        action('day_hear_rumor', '听奥伦转述跑腿的传闻', '奥伦明确说自己只是听说，没有据此罚款；但不愿承担你的赊账风险。', requires={'rumor_arrived': True}, effects=[flag('day_rumor_heard')]),
        action('day_credit', '请求记下8便士桥费，明日偿还', '奥伦同意本次赊账8便士。欠款留在旅程，不是免费免除。', requires={'day_prank': False, 'secured': False, 'day_missed': False}, effects=[flag('secured'), flag('day_debt'), {'op': 'resource', 'id': 'toll_debt', 'delta': 8}, info('欠奥伦8便士桥费，约定明日偿还。')]),
        action('day_bargain', '尝试以修桥换票', '我按指示修好栏杆，可在截止前登记免票通行。', requires={'day_prank': False, 'secured': False, 'day_missed': False}, check=('strength', .45), hours=1, success=[flag('day_repair_done')], failure='我没能稳住木料；可以改付8便士，或请求赊账。', fail=[flag('day_repair_failed')], social={'success': {'guard': ['respect']}}),
        action('day_hard_bargain', '在传闻影响下尝试以修桥换票', '虽然奥伦谨慎，我仍完成了要求更严的修补，可在截止前登记通行。', requires={'rumor_arrived': True, 'secured': False, 'day_missed': False}, check=('strength', .7), hours=1, success=[flag('day_repair_done')], failure='奥伦不接受这次修补，也不肯赊账；仍可付公开的8便士，或者搬木料两小时抵票。', fail=[flag('day_repair_failed')]),
        action('day_carry', '修补失败后搬两小时木料抵桥费', '我按公开劳动约定搬完木料，可在截止前登记通行；这不修复酒馆信用。', hours=2, requires={'day_repair_failed': True, 'secured': False, 'day_missed': False}, effects=[flag('day_repair_done')]),
        action('day_register_work', '在截止前登记已完成的修桥劳动', '奥伦核对完成的劳动，登记免票通行。', requires={'day_repair_done': True, 'secured': False, 'day_missed': False}, effects=[flag('secured')]),
        action('day_wait', '在桥口等五小时再决定', '五小时过去了；船期不会因为我犹豫而推迟。', hours=5, requires={'secured': False}, risk='等待可能超过傍晚六点的通行期限，错过后可留下做工。'),
        action('day_pay', '按公开价格付8便士桥费', '我付8便士取得通行；没有传闻罚款。', cost=8, requires={'secured': False, 'day_missed': False}, effects=[flag('secured')]),
        action('day_letter', '出示贝丝的船工介绍信', '奥伦核对介绍信，按船工预留名额免去本次桥费。', requires={'introduced': True, 'secured': False, 'day_missed': False}, effects=[flag('secured'), flag('day_letter_used')]),
        action('day_sail', '过桥登船，保留今天的账目', '我办妥通行后登船，离开铜杯镇。', requires={'secured': True, 'day_prank': False, 'day_letter_used': False, 'day_missed': False}, effects=[flag('day_normal')], end=True),
        action('day_friend_sail', '带着介绍信过桥登船', '我带着学徒的谢意与贝丝的信任登船。', requires={'secured': True, 'day_letter_used': True, 'day_missed': False}, effects=[flag('day_friend')], end=True),
        action('day_prank_sail', '带着信用损失过桥登船', '我可以离镇，但赔付、传闻与被拒绝的赊账都留在记录里。', requires={'secured': True, 'rumor_arrived': True, 'day_missed': False}, effects=[flag('day_chaos')], end=True),
        action('day_stay', '自愿错过今天的船，明天再走', '我决定留镇，明天凭劳动重新挣旅费。', effects=[flag('day_missed')], end=True),
    ])
    aftermath = event('town_tomorrow', '错过之后还有明天', 'town_bridge', ['guard'], [
        action('day_next_work', '帮奥伦整理木料，挣明日旅费8便士', '船已离开；我做两小时工挣8便士，明天仍能重新出发。', hours=2, effects=[money(8), flag('day_rebuilt')]),
        action('day_next_close', '记下明日计划，结束今天', '今天错过了船，明天的路仍然开着。', end=True),
    ])
    aftermath['entry_flags'] = {'day_missed': True}
    ends = [ending('day_normal', '一笔生意，一张通行证', '你完成采购、付清或约定桥费后离镇。', 'traded'),
            ending('day_friend', '收据换来的介绍信', '分享利润得到实际信任，省下桥费。', 'negotiated'),
            ending('day_chaos', '胡闹也要付账', '你离开了镇子，但传闻、赔付与信用损失并未被抹掉。'),
            ending('day_missed', '船走了，明天还在', '你错过今天的船，可以留下做工挣明日旅费。', 'lost')]
    ends[-1]['continue_event'] = 'town_tomorrow'
    normal = ['day_terms', 'day_breakfast', 'day_to_market', '@town_market', 'day_inspect', '?day_compare', 'day_buy', 'day_deliver', 'day_return', '@town_hall', 'day_to_bridge', '@town_bridge', 'day_pay', 'day_sail']
    alternative = ['day_terms', 'day_breakfast', 'day_to_market', '@town_market', 'day_inspect', '?day_compare', 'day_buy', 'day_deliver', 'day_share', 'day_lamp', 'day_return', '@town_hall', 'day_introduction', 'day_to_bridge', '@town_bridge', 'day_letter', 'day_friend_sail']
    data = base('town_day', '铜杯镇的一天', '早晨八点，你有18便士，其中6便士要付昨夜食宿。诺尔的干麦委托要垫12便士，收货付16便士。傍晚六点前办好雾桥通行，赶傍晚船；桥费8便士。', places,
                [person('bess', '贝丝', 'town_hall', {'责任': .8}), person('seller', '粮商艾达', 'town_market', {'谨慎': .7}), person('baker', '面包师诺尔', 'town_market', {'责任': .8}), person('guard', '桥吏奥伦', 'town_bridge', {'责任': .9})], actors,
                '衣物有主，不得擅拿。传闻不是目击事实，不触发罚款；8便士桥费公开，介绍信或约定劳动可免票。',
                [opening, trade, home, depart, aftermath], ends, normal, alternative)
    mechanics = data['story']['mechanics']
    mechanics['local']['resources'].append({'id': 'wheat', 'name': '干麦', 'unit': '袋', 'initial': 0, 'maximum': 1})
    mechanics['local']['resources'].append({'id': 'toll_debt', 'name': '欠奥伦的桥费', 'unit': '便士', 'initial': 0, 'maximum': 8})
    mechanics['adventure'] = {'version': 1, 'routes': [
        {'origin': a, 'destination': b, 'hours': 1, 'kind': 'town_lane'}
        for a, b in [('town_hall', 'town_market'), ('town_market', 'town_hall'), ('town_hall', 'town_bridge'), ('town_bridge', 'town_hall'), ('town_market', 'town_bridge'), ('town_bridge', 'town_market')]]}
    mechanics['pressure'] = {'version': 1, 'pressures': [{'id': 'day_boat', 'title': '傍晚六点截止的通行', 'stages': [
        {'id': 'warning', 'kind': 'warning', 'at_hours': 0, 'known_by': ['player'], 'public_text': '早晨八点；开局后10小时即傍晚六点，须在此之前办妥通行。', 'effects': []},
        {'id': 'escalation', 'kind': 'escalation', 'at_hours': 15, 'when': {'not_flags': ['secured']}, 'known_by': ['player'], 'public_text': '下午三点，离通行截止还剩三小时。', 'effects': [flag('day_last_call')]},
        {'id': 'missed', 'kind': 'trigger', 'at_hours': 18, 'when': {'not_flags': ['secured']}, 'known_by': ['player'], 'public_text': '傍晚六点，船工停止接收通行名单。今天错过了，但可留镇做工。', 'effects': [flag('day_missed')]},
        {'id': 'reserved', 'kind': 'lift', 'at_hours': 0, 'when': {'all_flags': {'secured': True}, 'not_flags': ['day_missed']}, 'known_by': ['player'], 'public_text': '通行已登记，船工留好座位；不用再赶这道期限。', 'effects': []},
        {'id': 'guard_private', 'kind': 'warning', 'at_hours': 0, 'known_by': ['guard'], 'public_text': '奥伦私记：收班后要清点备用铁钉。', 'effects': []},
    ]}]}
    mechanics['adventure']['fallback'] = {
        'enabled': True, 'duration_hours': 1, 'hints': [
            {'id': 'hall_prices', 'target': {'kind': 'place', 'id': 'town_hall'}, 'kinds': ['observe', 'ask'], 'text': '柜台账单写着昨夜食宿6便士；付清后还剩12便士采购本钱。'},
            {'id': 'hall_receipt', 'target': {'kind': 'place', 'id': 'town_hall'}, 'kinds': ['observe', 'ask'], 'text': '贝丝说她肯看诺尔署名的收据，不会只凭自夸作介绍。'},
            {'id': 'market_samples', 'target': {'kind': 'place', 'id': 'town_market'}, 'kinds': ['observe', 'ask'], 'text': '诺尔指着标注样本：拿不准可以请他一起对照，不必押运气。'},
            {'id': 'market_profit', 'target': {'kind': 'place', 'id': 'town_market'}, 'kinds': ['observe', 'ask'], 'text': '12便士成本、16便士收货款，中间4便士才是这笔生意的利润。'},
            {'id': 'bridge_labor', 'target': {'kind': 'place', 'id': 'town_bridge'}, 'kinds': ['observe', 'ask'], 'text': '桥牌写着修桥失败后可搬木料抵票，但劳动完成还须在六点前登记。'},
            {'id': 'bridge_tomorrow', 'target': {'kind': 'place', 'id': 'town_bridge'}, 'kinds': ['observe', 'ask'], 'text': '错过今天的船，桥口仍有明日短工；这不等于今天能免费登船。'},
        ]}
    data['playtest']['chaos'] = ['day_terms', 'day_breakfast', 'day_prank', 'day_to_market', '@town_market', 'day_compare', 'day_buy', 'day_deliver', 'day_return', '@town_hall', 'day_amends', 'day_rumor_to_bridge', '@town_bridge', 'day_hear_rumor', 'day_pay', 'day_prank_sail']
    _town_day_checks(mechanics, data['story'])
    return data


def _town_day_checks(mechanics, story):
    # 开启判定 v2（d20）的试点内容，并把三个既有检定接上钟与社交画像。
    #
    # 这是**内容试点**，不是新规则：判定、档位、钟全在 app/checks.py。
    #
    # * 三个检定（认麦 / 修桥 / 传闻下的修桥）改走 d20 四档（差值判定），difficulty 仍照旧换算成 DC；
    # * 认麦成功推进「干麦生意」进度钟，修桥失败/恶化推进「桥吏的疑虑」危险钟；
    # * 桥吏与贝丝的底线/诉求是**作者声明**的结构（不从自然语言猜），不进任何玩家投影；
    # * 重试用 refuse：同样的做法刚失败过就换办法，而不是反复押同一杆。
    #
    # 时钟仍只有一个：钟的进度按**行动**推进，不推游戏时间，也不另开第二套时间。
    mechanics['checks'] = {
        'version': 2, 'tier_mode': 'margin_four', 'die': 'd20', 'display': 'transparent',
        'default_position': 'risky', 'default_effect': 'standard',
        'factors': [
            # 「读过今天的委托与期限」只让已经读过的局面轻松一点：没读过就没有这 +1。
            {'id': 'terms_read', 'label': '你读过今天的委托与期限', 'mod': 1,
             'when': {'kind': 'flag', 'id': 'day_terms', 'value': True}},
            # 胡闹传出去以后，当面的交涉更难；这条对玩家可见（信用是公开的）。
            {'id': 'prank_credit', 'label': '酒馆里的信用已经受损', 'mod': -2,
             'when': {'kind': 'flag', 'id': 'day_prank', 'value': True}},
            # 拿着署名收据：这笔生意的凭据，对交涉有利。
            {'id': 'receipt', 'label': '你手里有诺尔署名的收据', 'mod': 2,
             'when': {'kind': 'flag', 'id': 'day_shared', 'value': True}},
        ],
        'push': [
            {'id': 'extra_look', 'label': '再仔细看一遍', 'fatigue': 0.1, 'bonus': 2},
            {'id': 'strain', 'label': '咬牙硬撑', 'fatigue': 0.2, 'advantage': True},
        ],
        'clocks': [
            {'id': 'grain_deal', 'label': '干麦生意', 'segments': 4, 'kind': 'progress',
             'known_by': ['player'], 'on_full': [flag('day_deal_clean')]},
            {'id': 'guard_doubt', 'label': '桥吏的疑虑', 'segments': 4, 'kind': 'danger',
             'known_by': ['player']},
            # 奥伦自己的笔记：只有他能看到这个钟。
            {'id': 'guard_note', 'label': '奥伦私下的笔记', 'segments': 3, 'kind': 'progress',
             'known_by': ['guard']},
        ],
        'social': {
            'guard': {'interests': ['public_price', 'labor'], 'boundaries': ['theft'],
                      'trust_weight': 10,
                      'refusal_text': '奥伦不肯为传闻里的失礼作担保。',
                      'absent_text': '奥伦此刻不在桥口。'},
            'bess': {'interests': ['honest_receipt'], 'boundaries': ['theft', 'family'],
                     'trust_weight': 10,
                     'refusal_text': '贝丝不愿再谈这件衣物。'},
        },
        # 成功但有代价时，引擎从这一组按声明顺序取第一条可执行的代价（多花一小时）。
        'default_costs': [{'kind': 'time', 'hours': 1}],
        'retry': {'same_approach': 'refuse'},
    }
    by_id = {entry['id']: entry
             for event in story['events'] for entry in event.get('actions') or []}
    # 认麦：成功推进「干麦生意」；失败只给下一步提示（不软锁）。
    by_id['day_inspect']['check']['clock'] = {'id': 'grain_deal'}
    # 修桥：失败/恶化让桥吏更起疑（数字可省，默认 1/2）；付公开价的活不推这个钟。
    for name in ('day_bargain', 'day_hard_bargain'):
        by_id[name]['check']['danger_clock'] = {'id': 'guard_doubt', 'failure': 1,
                                                'disaster': 2}
    # 传闻下的修桥只剩「硬撑」：这时候塞钱不是对话的一部分。
    by_id['day_hard_bargain']['check']['push_allowed'] = ['strain']
    # chaos 路线的孤注一掷只提高效果，不改变四档差值边界。
    by_id['day_hard_bargain']['check']['position'] = 'desperate'
    # 与桥吏当面交涉：诉求来自他公开的定价与劳动，底线是财物（作者声明，不是模型猜）。
    by_id['day_bargain']['check']['social'] = {'target': 'guard',
                                               'appeals': ['public_price', 'labor'],
                                               'violates': []}
    return mechanics['checks']


def scenes():
    return [tavern(), bridge(), market(), town_day()]


def export():
    OUT.mkdir(parents=True, exist_ok=True)
    for data in scenes():
        path = OUT / (data['story']['id'] + '.json')
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Exported', len(scenes()), 'short scenes to', OUT)


def install(url):
    def api(path, body=None, method=None):
        request = urllib.request.Request(url.rstrip('/') + path,
            data=None if body is None else json.dumps(body, ensure_ascii=False).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'x-textiledream-token': token}, method=method)
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response)
    token = ''
    boot = api('/api/bootstrap')
    token = boot['token']
    original = api('/api/inner/package') if boot.get('world') else None
    sessions = []
    for data in scenes():
        api('/api/inner/package', {'story': data['story'], 'characters': data['characters']}, 'PUT')
        session = api('/api/sessions', {'title': data['story']['title'], 'mode': 'protagonist', 'profile': 'traveller'})
        sessions.append({'title': data['story']['title'], 'id': session['id']})
    if original:
        api('/api/inner/packages/' + urllib.parse.quote(original['folder']) + '/activate', {}, 'POST')
    print(json.dumps(sessions, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install', help='Install and create four fresh journeys through this local API URL')
    args = parser.parse_args()
    export()
    if args.install:
        install(args.install)
