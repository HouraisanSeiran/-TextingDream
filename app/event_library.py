# -*- coding: utf-8 -*-
"""事件池第一轮内容（civ 世界）：纯函数，返回 ``mechanics.events`` / ``quests`` / ``rewards`` 配置。

不改引擎。civ 世界的城镇 id 因存档而异，所以内容按“角色”挂城：
``origin``（玩家起点城）与按路程排序的其余城镇 ``ranked``。同一函数对同一张图永远给同一份配置。

``native_starts`` 在新 civ 开局默认调用 ``attach``（开局请求 ``random_events`` 可关）；
按开局种子确定性地抽一部分事件，见 ``pick_event_ids``。事件“中/大”不预先标死，
由引擎按最终传播范围定级；``max_towns`` 与传播率只决定“大致多大”。

遏制：每个事件至少有一条 ``contain_on``（flag / quest_done）或 ``fade_after``。
flag 是给后续玩法（行动、任务、战斗）接线的开关，本轮只有两条真任务可走通：
``fever_relief``（遏制疫病）与 ``hero_hunt``（讨伐怪物）。
"""
from __future__ import annotations

import copy
import hashlib

from . import events as events_pool

PICK_MIN = 5          # 每个开局抽取的事件数下限 / 上限（含）
PICK_MAX = 8


def _ev(event_id, label, origin, nature, *, starts, contagion, half, towns, fade=None, recede=None,
        contain=(), heard, notice, on_level=None, road_factor=None):
    spec = {'id': event_id, 'label': label, 'origin': origin, 'starts_at': starts,
            'contagion': contagion, 'hours_half': half, 'max_towns': towns,
            'contain_on': list(contain), 'heard': heard, 'notice': notice,
            'on_level': on_level or {}}
    if fade:
        spec['fade_after'] = fade
    if recede:
        spec['recede_per_check'] = recede
    if road_factor:
        spec['road_factor'] = road_factor
    spec['_nature'] = nature          # 仅供作者/测试读；attach 时剥掉
    return spec


def _flag(flag_id, value=True):
    return {'op': 'flag', 'id': flag_id, 'value': value}


def event_specs(origin, ranked):
    """11 个事件：2 个小种子（疫病、斗殴）+ 6 个多半停在中等规模 + 3 个大范围。

    ``ranked``：除起点外的城镇 id，按离起点的路程从近到远。城镇少于 5 座时循环取用。
    """
    if not ranked:
        raise ValueError('事件内容至少需要两座可达城镇')

    def at(i):
        return ranked[i % len(ranked)]

    return [
        # ------------------------------------------------ 小种子（开局 1 城、传染性高、可遏制）
        _ev('first_fever_cases', '零星高热病例', origin, '坏', starts=2, contagion=0.3, half=800, towns=5,
            fade=2, recede=2, contain=[{'quest_done': 'fever_relief'}],
            heard={'small': '听说城里的码头区有几个人烧得说胡话，郎中说是着了凉；已经有人把自家的门闩上了。',
                   'medium': '听说高热病不止一座城里有，药铺的艾草和醋一天比一天贵。',
                   'large': '听说那场高热已经跟着商船过了边境，几个国家的港口都在盘查来客。',
                   'ended': '听说高热病终于退了，药铺门口排队的人少了。'},
            notice={'small': '码头区出现零星高热病例。', 'medium': '高热病蔓延到邻近城镇。',
                    'large': '高热病越过国境。', 'ended': '高热病平息。'},
            on_level={'medium': [{'op': 'signal', 'id': 'fever_alarm'}],
                      'ended': [_flag('ev_fever_active', False)],
                      'small': [_flag('ev_fever_active')]}),
        _ev('tavern_brawl_feud', '酒馆斗殴结成仇', at(1), '坏', starts=3, contagion=0.2, half=300, towns=5,
            fade=4, recede=2, contain=[{'quest_done': 'feud_mediation'}],
            heard={'small': '听说有两帮脚夫在酒馆里动了刀，各自都说是对方先动的手，官差只抓走了两个醉汉。',
                   'medium': '听说那两帮脚夫的仇已经传到邻城，两边都有人被堵在巷子里。',
                   'large': '听说两帮人的仇杀闹到了别国的码头，有人说背后有大商号撑腰。',
                   'ended': '听说有德高望重的人出面调停，两帮人当众喝了和解酒。'},
            notice={'small': '酒馆斗殴，两帮脚夫结怨。', 'medium': '帮派冲突波及邻城。',
                    'large': '帮派冲突波及他国。', 'ended': '帮派冲突平息。'},
            on_level={'small': [{'op': 'signal', 'id': 'feud_brewing'}],
                      'medium': [_flag('ev_feud_widening')], 'ended': [_flag('ev_feud_widening', False)]}),
        # ------------------------------------------------ 多半中等规模
        _ev('monster_call_heroes', '征集勇者讨伐怪物', at(1), '福祸相依', starts=2, contagion=0.5, half=400, towns=3,
            fade=3, recede=2, contain=[{'quest_done': 'hero_hunt'}],
            heard={'small': '听说城外的林地里有东西夜里叼走了牲口，猎户说脚印比牛还大。',
                   'medium': '听说官府在几座城贴了告示，出钱招人去讨伐林子里的怪物。',
                   'large': '听说连邻国都派人来问那头怪物的事，说它沿着山路往这边来了。',
                   'ended': '听说怪物被打死了，皮子挂在城门口，围观的人比赏金还多。'},
            notice={'small': '近郊有野兽伤畜。', 'medium': '官府张贴告示征集勇者。',
                    'large': '怪物之事惊动邻国。', 'ended': '怪物已被讨平。'},
            on_level={'medium': [{'op': 'signal', 'id': 'heroes_called'}]}),
        _ev('highway_bandits', '商路出了劫匪', at(2), '坏', starts=4, contagion=0.5, half=400, towns=3,
            fade=4, recede=2, contain=[{'quest_done': 'road_patrol'}],
            heard={'small': '听说一支商队在城外的岔路口被劫了，车夫只记得对方蒙着脸，很熟悉路。',
                   'medium': '听说几座城之间的路都不太平，商人宁可多花钱雇护卫。',
                   'large': '听说劫匪的买卖做到了边境两边，货主都在抱怨关税之外又多了一笔买路钱。',
                   'ended': '听说官军清了几处窝点，商队又敢走夜路了。'},
            notice={'small': '城外商队遇劫。', 'medium': '数城之间商路不靖。',
                    'large': '商路劫匪横跨边境。', 'ended': '商路恢复通行。'},
            on_level={'small': [{'op': 'signal', 'id': 'caravan_raided'}],
                      'medium': [_flag('ev_roads_unsafe')], 'ended': [_flag('ev_roads_unsafe', False)]}),
        _ev('grain_price_rise', '粮价上涨', at(1), '坏', starts=1, contagion=0.45, half=400, towns=4,
            fade=3, recede=2,
            heard={'small': '听说城里的粮价一夜涨了三成，粮铺的伙计说是新麦还没上市，也有人说是大户在囤。',
                   'medium': '听说周边几座城的粮价都在涨，船老大说运粮的船不够。',
                   'large': '听说粮价涨过了国境，好几个国家的官府都在商量要不要限价。',
                   'ended': '听说新粮运到了，粮价慢慢落了回来。'},
            notice={'small': '本地粮价上涨。', 'medium': '邻近城镇粮价同涨。',
                    'large': '粮价上涨波及多国。', 'ended': '粮价回落。'},
            on_level={'medium': [_flag('ev_grain_dear')], 'ended': [_flag('ev_grain_dear', False)]}),
        _ev('border_levy', '边境征兵', at(3), '坏', starts=5, contagion=0.5, half=400, towns=3,
            fade=3, recede=2,
            heard={'small': '听说边上的城开始点兵，里正挨家挨户登名，每户要出一个壮丁。',
                   'medium': '听说征兵令传到了几座城，铁匠铺的活排到了月底。',
                   'large': '听说邻国也在边境集兵，两边都说是防着对方。',
                   'ended': '听说征兵令撤了，一些人被放回了家。'},
            notice={'small': '边境城镇征兵。', 'medium': '征兵令扩大到数城。',
                    'large': '边境两侧同时集兵。', 'ended': '征兵令撤销。'},
            on_level={'medium': [_flag('ev_levy_on')], 'ended': [_flag('ev_levy_on', False)]}),
        _ev('harvest_fair', '丰年大集', at(0), '好', starts=3, contagion=0.5, half=300, towns=3,
            fade=3, recede=2,
            heard={'small': '听说今年的收成好，城里要办一场大集，摊位费减半，外乡人也能摆摊。',
                   'medium': '听说附近几座城都在办集，货郎们挑着担子一个城接一个城地赶。',
                   'large': '听说大集办到了别国，两边的商人换着卖货，连关卡都放松了些。',
                   'ended': '听说集市散了，摊棚拆得干干净净，只剩满地的菜叶。'},
            notice={'small': '本地举办大集。', 'medium': '邻近城镇接着办集。',
                    'large': '大集办到邻国。', 'ended': '大集散场。'},
            on_level={'medium': [_flag('ev_fair_on')], 'ended': [_flag('ev_fair_on', False)]}),
        _ev('pilgrim_wave', '朝圣潮', at(4), '福祸相依', starts=4, contagion=0.4, half=400, towns=4,
            fade=4, recede=2,
            heard={'small': '听说有座老庙传出神迹，朝圣的人络绎不绝，客栈的床位早就订满了。',
                   'medium': '听说朝圣的人沿着路一路走过好几座城，有的施粥，也有的趁乱偷东西。',
                   'large': '听说朝圣的队伍越过了边境，两国的官府都派人维持秩序。',
                   'ended': '听说朝圣的人渐渐少了，客栈老板在算这个月到底赚了多少。'},
            notice={'small': '老庙吸引朝圣者。', 'medium': '朝圣者沿路涌入数城。',
                    'large': '朝圣队伍跨国而行。', 'ended': '朝圣潮退去。'},
            on_level={'medium': [_flag('ev_pilgrims')], 'ended': [_flag('ev_pilgrims', False)]}),
        # ------------------------------------------------ 多半大范围
        _ev('great_drought', '大旱', at(1), '坏', starts=4, contagion=0.3, half=700, towns=5,
            fade=4, recede=3, contain=[{'quest_done': 'rain_ritual'}],
            heard={'small': '听说那边已经三个月没下透雨了，河床露出了底，老人说这样的年景不多见。',
                   'medium': '听说旱情从一座城蔓延到了另一座，井水都发苦了。',
                   'large': '听说旱情连成了片，几个国家的粮仓都在盘点存粮。',
                   'ended': '听说终于下了场透雨，田里的人跪在泥里笑。'},
            notice={'small': '一地旱情严重。', 'medium': '旱情扩大到邻近城镇。',
                    'large': '旱情连成多国大旱。', 'ended': '旱情缓解。'},
            on_level={'small': [{'op': 'signal', 'id': 'drought_warning'}],
                      'large': [_flag('ev_great_drought')], 'ended': [_flag('ev_great_drought', False)]}),
        _ev('sea_trade_boom', '海贸兴旺', origin, '好', starts=3, contagion=0.25, half=700, towns=5,
            fade=4, recede=2,
            heard={'small': '听说有支大船队在港口卸货，码头上的脚夫抢着接活，酒馆的生意也好了许多。',
                   'medium': '听说船队又去了邻近的港口，那边的货价也跟着活了起来。',
                   'large': '听说海贸的风吹到了好几个国家，连内陆小城也在谈着要不要修栈桥。',
                   'ended': '听说船队走远了，码头安静下来，脚夫们开始盼着下一拨。'},
            notice={'small': '港口迎来大船队。', 'medium': '海贸扩及邻港。',
                    'large': '海贸繁荣跨国。', 'ended': '海贸高峰过去。'},
            on_level={'large': [_flag('ev_trade_boom')], 'ended': [_flag('ev_trade_boom', False)]}),
        _ev('border_crisis', '边境对峙', at(3), '坏', starts=6, contagion=0.5, half=600, towns=5,
            fade=4, recede=2, contain=[{'quest_done': 'border_parley'}],
            heard={'small': '听说边境的关口两边各站了一队兵，互不让路，已经有商人被扣了一夜。',
                   'medium': '听说对峙的消息传开，几座城的关口都加了岗。',
                   'large': '听说好几国都派了使者去谈，谁也不肯先松口，谈判桌摆了三回。',
                   'ended': '听说使者们终于握了手，关口恢复了往来。'},
            notice={'small': '边境关口出现对峙。', 'medium': '关口戒严扩大。',
                    'large': '数国卷入边境对峙。', 'ended': '边境对峙缓和。'},
            on_level={'small': [{'op': 'signal', 'id': 'border_standoff'}],
                      'large': [_flag('ev_border_crisis')], 'ended': [_flag('ev_border_crisis', False)]}),
    ]


def quests_block(origin, ranked):
    """六个由事件信号开启的任务；完成证据一律是“到过某城”（``visited``，玩家走到就算）。

    奖励引用 ``rewards_block`` 里已声明的条目（见 quests-contract §3.1）。任务完成即遏制对应事件
    （事件的 ``contain_on.quest_done``）。
    """
    def at(i):
        return ranked[i % len(ranked)]

    def quest(qid, giver, title, summary, secret, signal, goal, place, reward):
        return {'id': qid, 'giver': giver, 'location': '', 'title': title, 'public_summary': summary,
                'secret_objective': secret, 'known_by': ['player'], 'enabled_on': {'signal': signal},
                'objectives': [goal], 'evidence': [{'kind': 'visited', 'id': place}],
                'rewards': reward, 'effects': [{'op': 'flag', 'id': qid + '_done', 'value': True}]}

    rel = lambda text: [{'kind': 'relationship', 'text': text}]
    return {'version': 1, 'quests': [
        quest('hero_hunt', 'levy_office', '讨伐近郊怪物', '官府出钱招人，去城外林地讨伐伤畜的怪物。',
              '（作者侧）怪物只是一头发疯的老熊，赏金够付，但不够雇一队人。',
              'heroes_called', '赶到出事的城镇，找到并驱走怪物', at(1), [{'kind': 'currency', 'id': 'hero_bounty'}]),
        quest('fever_relief', 'physicians', '给疫区送药', '郎中们缺艾草和干净的水，想请人把药材送进疫区。',
              '（作者侧）送药只能减缓，真正的遏制是隔开病人。',
              'fever_alarm', '把药材送到邻近的疫区城镇', at(0),
              rel('城里的郎中记下了你的名字，以后求药会容易些。')),
        quest('feud_mediation', 'dock_elders', '为两帮脚夫说和', '码头上有头脸的老人想请个外人去给两帮脚夫做中人。',
              '（作者侧）两帮人真正争的是一条渡口的抽成，不是那一刀。',
              'feud_brewing', '赶到结仇的城镇，当面说和', at(1),
              rel('脚夫们认得你了，在码头上遇到麻烦时有人愿意搭把手。')),
        quest('road_patrol', 'caravan_guild', '护送商队巡路', '商队行会想雇人沿商路走一趟，让劫匪知道有人盯着。',
              '（作者侧）劫匪里有一个是行会自己的押车人。',
              'caravan_raided', '沿商路走到出事的城镇', at(2),
              rel('行会记下了你的名字，以后过路能少交一份买路钱。')),
        quest('rain_ritual', 'temple_keepers', '主持祈雨', '庙祝说旱得太久，需要有人去旱情最重的城里主持一场祈雨。',
              '（作者侧）祈雨不一定真的下雨，但能稳住人心，让人不再逃荒。',
              'drought_warning', '赶到旱情最重的城镇', at(1),
              rel('庙祝记下了你的名字，以后求神签、借庙宇歇脚都方便。')),
        quest('border_parley', 'border_wardens', '到关口做个见证', '边关守将想请一个不属于任何一方的外人去关口做调停见证。',
              '（作者侧）两边其实都不想先动手，缺的是一个能下台的台阶。',
              'border_standoff', '赶到对峙的关口城镇', at(3),
              rel('守将记下了你的名字，以后过关少些盘问。')),
    ]}


def rewards_block():
    return {
        'version': 1,
        'currencies': [{'id': 'coin', 'name': '铜币', 'unit': '文'}],
        'accounts': [{'id': 'levy_office', 'name': '官府征募处', 'currency': 'coin', 'initial': 300}],
        'materials': [], 'shapes': [], 'qualities': [], 'enchantments': [], 'abilities': [],
        'templates': [], 'tables': [],
        'rewards': [{'id': 'hero_bounty', 'kind': 'currency', 'currency': 'coin',
                     'amount_min': 20, 'amount_max': 30, 'payer': 'levy_office'}],
    }


def _digest(seed, label):
    return int(hashlib.sha256(('%s:civ-events:%s' % (seed, label)).encode('utf-8')).hexdigest(), 16)


def pick_event_ids(seed, count=None):
    """按种子确定性地抽事件 id（不依赖 Python 的 random 实现，跨版本稳定）。

    数量：``PICK_MIN``..``PICK_MAX`` 里按种子取一个（也可显式给 ``count``）；每个事件的得分是
    ``sha256(seed:id)``，取得分最小的前 N 个。返回值按事件库里的原顺序排列。
    """
    ids = [spec['id'] for spec in event_specs('o', ['a'])]
    if count is None:
        count = PICK_MIN + _digest(seed, 'count') % (PICK_MAX - PICK_MIN + 1)
    if type(count) is not int or not 1 <= count <= len(ids):
        raise ValueError('抽取数量必须在 1..%d 之间' % len(ids))
    chosen = set(sorted(ids, key=lambda i: (_digest(seed, 'pick:' + i), i))[:count])
    return [i for i in ids if i in chosen]


def _wanted_quests(specs):
    return {gate['quest_done'] for spec in specs for gate in spec['contain_on'] if 'quest_done' in gate}


def events_block(origin, ranked, polities, *, radius_hours=None, max_active=5, only=None):
    specs = []
    for spec in event_specs(origin, ranked):
        if only is not None and spec['id'] not in only:
            continue
        spec = copy.deepcopy(spec)
        spec.pop('_nature')
        specs.append(spec)
    return {'version': 1, 'radius_hours': radius_hours, 'max_active': max_active,
            'polities': {k: v for k, v in polities.items() if v is not None},
            'events': specs}


def natures():
    return {spec['id']: spec['_nature'] for spec in event_specs('o', ['a'])}


def attach(story, origin, polities, *, only=None):
    """把内容挂到已编译的 civ 故事包上（原地修改并返回）。

    需要 ``mechanics.exploration``。步骤：用临时事件块建传播图，按离 ``origin`` 的路程排出其余城镇，
    再写入 ``mechanics.events`` / ``quests`` / ``rewards``。

    ``only``：事件 id 集合，只挂这些事件；任务只留被它们的 ``contain_on.quest_done`` 引用的，
    奖励声明只在仍有任务引用时才写，所以抽取后不会留下悬空任务/奖励。``None`` = 全部。
    """
    if only is not None:
        only = set(only)
        unknown = only - {spec['id'] for spec in event_specs('o', ['a'])}
        if unknown or not only:
            raise ValueError('事件库里没有这些事件：%s' % ('、'.join(sorted(unknown)) or '（空集）'))
    mech = story.setdefault('mechanics', {})
    probe = {'version': 1, 'polities': {}, 'events': []}
    mech['events'] = probe
    cfg = events_pool.config(story)
    graph = events_pool.build_graph(story, cfg)
    hours = graph.hours_from(origin)
    ranked = [t for t, _ in sorted(((t, h) for t, h in hours.items() if t != origin),
                                   key=lambda row: (row[1], row[0]))]
    mech['events'] = events_block(origin, ranked, polities, only=only)
    quests = quests_block(origin, ranked)
    if only is not None:
        wanted = _wanted_quests([s for s in event_specs(origin, ranked) if s['id'] in only])
        quests['quests'] = [q for q in quests['quests'] if q['id'] in wanted]
    rewards = rewards_block()
    used = {r['id'] for q in quests['quests'] for r in q['rewards'] if r.get('kind') == 'currency'}
    if quests['quests']:
        mech['quests'] = quests
    else:
        mech.pop('quests', None)
    if used or only is None:
        mech['rewards'] = rewards
    else:
        mech.pop('rewards', None)
    return story
