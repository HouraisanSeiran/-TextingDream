# -*- coding: utf-8 -*-
"""交易结算：买、卖、以物易物、讨价还价（引擎动作，候选 → 确认 → 结算）。

规格见 docs/economy-design.md。本模块的分工：

* 价格与规则来自 ``app/economy.py``（纯函数，整数便士，无随机）。
* 讨价还价只调用 ``app/checks.py`` 的公开接口 ``plan`` / ``resolve``（纯函数，不写 session），
  不改判定模块内部。种子由 session 种子 + 商人 + 商品 + 已谈次数派生，回滚后同一步结果不变。
* 钱走 ``session['rewards']``：玩家钱包 ``wallet``，商人付款账户 ``accounts``（玩家不可见）。
  商人收购时从他的账户付钱，余额不足就收不了。
* 可数货物存在 ``session['trade']['bag']``；作者声明的唯一物品（Good.item）走 ``session['inventory']``。
* 所有写入只发生在 ``settle`` 里，且调用方（``Runtime``）传入的是候选副本：任何一步失败都在
  写入前抛错，不留半截；成功后由 ``Service`` 一次性保存，随存档保存与回滚。
* 模型说「你买到了」不改变任何状态，只有这里的结算会改。
* 故事包没有声明商人时，本模块什么也不做：不写任何 session 键，surface 也不出现 ``trade``。

动作 id：``trade:buy:<商人>:<商品>[:<数量>]``、``trade:sell:...``、``trade:haggle:<商人>:<商品>``、
``trade:barter:<商人>:<换到的商品>:<付出的商品>``。
"""
from __future__ import annotations

import copy

from . import economy

PREFIX = 'trade:'
MODES = ('buy', 'sell', 'barter', 'haggle')
MAX_QTY = 20
MAX_LOG = 40
MAX_BARTER_ROWS = 8

# 讨价还价：各判定档能拿到「开价 → 底价」差额的百分之几（100 = 压到底价）。
# 不在表里的档（failure / setback / disaster）没有成交。
TIER_SHARE = {'critical': 100, 'success': 50, 'partial': 25}
TIER_LABEL = {'critical': '大成功', 'success': '成功', 'partial': '成功但有代价',
              'failure': '失败', 'setback': '失败（有代价）', 'disaster': '大失败'}
# 大失败：商人当天不再卖这件货给你；其余失败：当天不再谈价，仍可按开价买。
REFUSE_TIERS = ('disaster',)


def blank():
    return {'version': 1, 'bag': {}, 'sold': {}, 'bargain': {}, 'haggles': {}, 'log': []}


# ------------------------------------------------------------------ 解析与上下文


def parse(action_id):
    """交易动作 id → 结构化参数；不是交易动作或格式不对返回 None。"""
    if not isinstance(action_id, str) or not action_id.startswith(PREFIX):
        return None
    p = action_id.split(':')
    if len(p) < 4 or p[1] not in MODES:
        return None
    mode = p[1]
    if mode == 'barter':
        if len(p) != 5:
            return None
        return {'mode': mode, 'merchant': p[2], 'good': p[3], 'give': p[4], 'qty': 1}
    if len(p) not in (4, 5):
        return None
    qty = 1
    if len(p) == 5:
        if not (p[4].isascii() and p[4].isdigit()):
            return None
        qty = int(p[4])
    if not 1 <= qty <= MAX_QTY or (mode == 'haggle' and qty != 1):
        return None
    return {'mode': mode, 'merchant': p[2], 'good': p[3], 'give': '', 'qty': qty}


def declared(story):
    """故事包是否声明了商人（决定本模块是否参与；配置非法由 validate 在提交时挡住）。"""
    raw = economy.config(story)
    return bool(isinstance(raw, dict) and raw.get('merchants'))


def _regime(story):
    return economy.regime_of(story) or 'feudal'


def _merchant_present(session, m):
    """商人在场：地点相同；声明了人物时，人物此刻也在这个地点（没有位置记录视为在场）。"""
    if m.location != session.get('location'):
        return False
    if m.npc:
        seat = ((session.get('characters') or {}).get(m.npc) or {}).get('location')
        return seat in (None, session.get('location'))
    return True


def _good(rows, good_id):
    return next((g for g in rows if g.id == good_id), None)


def _currency(story, cfg):
    from . import rewards
    rcfg = rewards.rules(story)
    cur = next((c for c in rcfg.currencies if c.id == cfg.currency), None)
    return rcfg, cur


def _unit_name(cur):
    return (cur.unit or cur.name) if cur else '铜币'


def _state(session):
    return session.get('trade') or {}


def has(session, good):
    """玩家持有这件货的数量：唯一物品最多 1；可数货物看货物袋。"""
    if good.item:
        return 1 if good.item in (session.get('inventory') or []) else 0
    return int((_state(session).get('bag') or {}).get(good.id, 0))


def stock_left(session, m, g):
    if g.stock is None:
        return None
    row = (_state(session).get('sold') or {}).get(m.id + ':' + g.id) or {}
    used = row.get('n', 0) if row.get('day') == economy.day_of(session) else 0
    return max(0, g.stock - used)


def _bargain_state(session, m, g):
    """今天对这件货的谈价状态：'' / 'failed' / 'refused'（不是今天的记录一律作废）。"""
    row = (_state(session).get('bargain') or {}).get(m.id + ':' + g.id) or {}
    return row.get('state', '') if row.get('day') == economy.day_of(session) else ''


def _closed_text(cfg, regime, m, session):
    if regime == 'feudal':
        days = economy.days_to_market(cfg, session)
        return '%s今天不开市，下个集市日在 %d 天后' % (m.name, days)
    return '%s今天不营业' % m.name


def _haggle_action(m, g):
    """讨价还价用的判定动作：社交判定，难度取商人配置；声明了人物就以他为社交目标。"""
    check = {'attribute': 'social', 'difficulty': m.haggle_difficulty}
    if m.npc:
        check['social'] = {'target': m.npc, 'appeals': [], 'violates': []}
    return check


def _node(m):
    return {'id': 'trade:' + m.id, 'participants': [m.npc] if m.npc else []}


def action_for(session, story, characters, action_id):
    """按 id 重建交易动作（供 ``free_actions.resolve_action`` 与确认凭据使用）。

    只回答「这个 id 属于谁」，能不能用由 ``preview`` / ``settle`` 判；未知商人 / 商品返回 None。
    """
    parsed = parse(action_id)
    if parsed is None or not declared(story):
        return None
    cfg = economy.model(story)
    m = next((x for x in cfg.merchants if x.id == parsed['merchant']), None)
    if m is None:
        return None
    mode, qty = parsed['mode'], parsed['qty']
    if mode == 'sell':
        g = _good(m.buys, parsed['good'])
    else:
        g = _good(m.sells, parsed['good'])
    if g is None:
        return None
    action = {'id': action_id, 'costs': {}, 'duration_hours': 0, 'trade': True}
    if mode == 'buy':
        action['label'] = '向%s买 %d%s%s' % (m.name, qty, g.unit, g.name)
    elif mode == 'sell':
        action['label'] = '卖给%s %d%s%s' % (m.name, qty, g.unit, g.name)
    elif mode == 'haggle':
        action['label'] = '向%s讨价还价买%s' % (m.name, g.name)
        action['check'] = _haggle_action(m, g)
    else:
        give = _good(m.buys, parsed['give'])
        if give is None:
            return None
        action['label'] = '用%s向%s换%s' % (give.name, m.name, g.name)
    return action


# ------------------------------------------------------------------ 准备（预览与结算共用）


def _prepare(session, story, characters, action_id):
    """核对这次交易此刻能不能做，并算出价格。任何不满足都抛 ValueError，**不写任何状态**。"""
    from . import checks
    parsed = parse(action_id)
    action = action_for(session, story, characters, action_id)
    if parsed is None or action is None:
        raise ValueError('没有这个交易：' + str(action_id))
    cfg = economy.model(story)
    regime = _regime(story)
    m = next(x for x in cfg.merchants if x.id == parsed['merchant'])
    if not _merchant_present(session, m):
        raise ValueError('%s不在这里' % m.name)
    rcfg, cur = _currency(story, cfg)
    from . import rewards
    st = rewards.state(session, rcfg)
    wallet = st['wallet'].get(cfg.currency, 0)
    account = st['accounts'].get(m.account, 0)
    mode, qty = parsed['mode'], parsed['qty']
    ctx = {'parsed': parsed, 'action': action, 'cfg': cfg, 'regime': regime, 'm': m, 'rcfg': rcfg,
           'cur': cur, 'wallet': wallet, 'account': account, 'mode': mode, 'qty': qty,
           'label': action['label']}

    if mode in ('buy', 'haggle'):
        g = _good(m.sells, parsed['good'])
        if not economy.good_available(cfg, regime, m, g, session):
            raise ValueError(_closed_text(cfg, regime, m, session))
        if _bargain_state(session, m, g) == 'refused':
            raise ValueError('%s今天不肯再把%s卖给你了' % (m.name, g.name))
        left = stock_left(session, m, g)
        if left is not None and left < qty:
            raise ValueError('%s今天的%s只剩 %d%s' % (m.name, g.name, left, g.unit))
        if g.item and has(session, g):
            raise ValueError('你已经有%s了' % g.name)
        row = economy.price_for(story, session, m, g, cfg, regime)
        total = row['ask'] * qty
        if wallet < total:
            raise ValueError('钱不够：这笔要 %d %s' % (total, _unit_name(cur)))
        ctx.update(g=g, row=row, unit_price=row['ask'], total=total)
        if mode == 'haggle':
            if not m.haggle:
                raise ValueError('%s不接受讨价还价' % m.name)
            if not checks.enabled(story):
                raise ValueError('这个故事包没有开启判定，不能讨价还价')
            if _bargain_state(session, m, g) == 'failed':
                raise ValueError('%s今天不肯再谈%s的价钱了' % (m.name, g.name))
            planned = checks.plan(session, story, characters, _node(m), action, None)
            if planned.get('refused'):
                raise ValueError(str(planned['refused']))
            if planned.get('blocked'):
                raise ValueError('现在不能讨价还价：' + str(planned['blocked']))
            ctx['planned'] = planned
    elif mode == 'sell':
        g = _good(m.buys, parsed['good'])
        if not economy.good_available(cfg, regime, m, g, session):
            raise ValueError(_closed_text(cfg, regime, m, session))
        if g.item and qty != 1:
            raise ValueError('唯一物品一次只能卖一件')
        if has(session, g) < qty:
            raise ValueError('你手上没有那么多%s' % g.name)
        row = economy.price_for(story, session, m, g, cfg, regime)
        total = row['bid'] * qty
        if total <= 0:
            raise ValueError('%s不收这件货' % m.name)
        if account < total:
            raise ValueError('%s手头的钱不够，今天收不了这笔货' % m.name)
        if cur is not None and wallet + total > cur.maximum:
            raise ValueError('钱袋装不下这么多钱')
        ctx.update(g=g, row=row, unit_price=row['bid'], total=total)
    else:
        allowed = m.barter if m.barter is not None else economy.REGIME_INFO[regime]['barter']
        if not allowed:
            raise ValueError('%s只收钱，不做以物易物' % m.name)
        want = _good(m.sells, parsed['good'])
        give = _good(m.buys, parsed['give'])
        for good in (want, give):
            if not economy.good_available(cfg, regime, m, good, session):
                raise ValueError(_closed_text(cfg, regime, m, session))
        left = stock_left(session, m, want)
        if left is not None and left < 1:
            raise ValueError('%s今天的%s卖完了' % (m.name, want.name))
        if want.item and has(session, want):
            raise ValueError('你已经有%s了' % want.name)
        want_row = economy.price_for(story, session, m, want, cfg, regime)
        give_row = economy.price_for(story, session, m, give, cfg, regime)
        if give_row['bid'] <= 0:
            raise ValueError('%s不收%s' % (m.name, give.name))
        need = -(-want_row['ask'] // give_row['bid'])      # 向上取整：不找零，多出的算商人的
        if give.item and need != 1:
            raise ValueError('一件%s抵不了%s' % (give.name, want.name))
        if need > MAX_QTY:
            raise ValueError('这笔换算太悬殊，换不成')
        if has(session, give) < need:
            raise ValueError('你的%s不够：要 %d%s' % (give.name, need, give.unit))
        ctx.update(g=want, give=give, need=need, row=want_row, give_row=give_row,
                   total=0, unit_price=want_row['ask'])
        ctx['label'] = action['label']
    return ctx


def _public(ctx, extra=None):
    """玩家可见的交易摘要（不含底价与商人账户）。"""
    g, cur = ctx['g'], ctx['cur']
    out = {'mode': ctx['mode'], 'merchant': ctx['m'].name, 'good': g.name, 'qty': ctx['qty'],
           'unit': g.unit, 'unit_price': ctx['unit_price'], 'total': ctx['total'],
           'currency': _unit_name(cur), 'notes': list(ctx['row'].get('notes') or [])}
    if ctx['mode'] == 'barter':
        out['give'] = {'good': ctx['give'].name, 'qty': ctx['need'], 'unit': ctx['give'].unit}
    if ctx['mode'] == 'haggle':
        out['note'] = '成交价在开价以内；谈得好可以便宜，谈砸了商人可能不再让价'
    if extra:
        out.update(extra)
    return out


def preview(session, story, characters, action_id):
    """确认预览里的交易部分；此刻做不了就抛 ValueError（说明缺什么）。只读。"""
    return _public(_prepare(session, story, characters, action_id))


# ------------------------------------------------------------------ 结算


def _give_goods(work, state, g, qty):
    if g.item:
        work.setdefault('inventory', []).append(g.item)
    else:
        state['bag'][g.id] = state['bag'].get(g.id, 0) + qty


def _take_goods(work, state, g, qty):
    if g.item:
        work['inventory'].remove(g.item)
    else:
        left = state['bag'].get(g.id, 0) - qty
        if left > 0:
            state['bag'][g.id] = left
        else:
            state['bag'].pop(g.id, None)


def _count_sold(state, m, g, qty, day):
    key = m.id + ':' + g.id
    row = state['sold'].get(key)
    if not row or row.get('day') != day:
        row = {'day': day, 'n': 0}
    row['n'] += qty
    state['sold'][key] = row


def settle(work, story, characters, action_id):
    """在候选副本 ``work`` 上结算一次交易，返回与 ``Runtime.local_action`` 同形的结果。

    先 ``_prepare`` 全部核对（不写），再一次性改钱包 / 账户 / 货物 / 记录，所以失败不留半截。
    """
    from . import rewards
    ctx = _prepare(work, story, characters, action_id)
    rewards.ensure(work, story)
    state = work.get('trade')
    if state is None:
        state = work['trade'] = blank()
    for key, value in blank().items():
        state.setdefault(key, copy.deepcopy(value))
    m, g, qty, cfg = ctx['m'], ctx['g'], ctx['qty'], ctx['cfg']
    wallet = work['rewards']['wallet']
    accounts = work['rewards']['accounts']
    day = economy.day_of(work)
    unit = _unit_name(ctx['cur'])
    extra = {}
    deal = True

    if ctx['mode'] == 'haggle':
        deal, extra, outcome = _haggle(work, story, characters, ctx, state)
        if deal:
            ctx['unit_price'] = extra['unit_price']
            ctx['total'] = extra['unit_price']
    if ctx['mode'] in ('buy', 'haggle') and deal:
        total = ctx['total']
        wallet[cfg.currency] = wallet.get(cfg.currency, 0) - total
        accounts[m.account] = accounts.get(m.account, 0) + total
        _give_goods(work, state, g, qty)
        _count_sold(state, m, g, qty, day)
        if ctx['mode'] == 'buy':
            outcome = '你以 %d %s买下了 %d%s%s' % (total, unit, qty, g.unit, g.name)
        else:
            outcome = '%s；你以 %d %s买下了%s（开价 %d）' % (outcome, total, unit, g.name, ctx['row']['ask'])
    elif ctx['mode'] == 'sell':
        total = ctx['total']
        accounts[m.account] = accounts.get(m.account, 0) - total
        wallet[cfg.currency] = wallet.get(cfg.currency, 0) + total
        _take_goods(work, state, g, qty)
        outcome = '你把 %d%s%s卖了 %d %s' % (qty, g.unit, g.name, total, unit)
    elif ctx['mode'] == 'barter':
        give, need = ctx['give'], ctx['need']
        _take_goods(work, state, give, need)
        _give_goods(work, state, g, 1)
        _count_sold(state, m, g, 1, day)
        outcome = '你用 %d%s%s换到了 1%s%s' % (need, give.unit, give.name, g.unit, g.name)

    row = {'at': work.get('time', 0), 'day': day, 'mode': ctx['mode'], 'merchant': m.id,
           'good': g.id, 'qty': qty, 'total': ctx['total'] if deal else 0, 'deal': deal}
    if ctx['mode'] == 'barter':
        row['give'] = ctx['give'].id
        row['give_qty'] = ctx['need']
    state['log'] = (state['log'] + [row])[-MAX_LOG:]

    public = _public(ctx, extra)
    public['deal'] = deal
    public['outcome'] = outcome
    return {'outcome': outcome, 'kind': 'trade', 'duration_hours': 0, 'ends': False,
            'listeners': [],
            'local_result': {'action_id': action_id, 'kind': 'trade', 'hours': 0,
                             'label': ctx['label'], 'resources': [], 'trade': public}}


def _haggle(work, state_story, characters, ctx, state):
    """讨价还价：调用 checks 的公开接口，把成交价落在开价与底价之间。

    返回 (是否成交, 公开补充字段, 说明文字)。失败不成交，只记录今天的谈价状态。
    """
    from . import checks
    m, g = ctx['m'], ctx['g']
    key = m.id + ':' + g.id
    n = state['haggles'].get(key, 0)
    seed = '%s:haggle:%s:%s:%d' % (work.get('seed', ''), m.id, g.id, n)
    state['haggles'][key] = n + 1
    resolved = checks.resolve(work, state_story, characters, _node(m), ctx['action'], None, seed,
                              planned=ctx['planned'])
    tier = resolved.get('tier')
    label = TIER_LABEL.get(tier, str(tier))
    ask, floor = ctx['row']['ask'], ctx['row']['floor']
    extra = {'tier': tier, 'tier_label': label, 'dc': resolved.get('dc'),
             'margin': resolved.get('margin'), 'rolled': resolved.get('kept')}
    share = TIER_SHARE.get(tier)
    if share is not None:
        price = ask - (ask - floor) * share // 100
        extra['unit_price'] = price
        return True, extra, '讨价还价：' + label
    day = economy.day_of(work)
    refused = tier in REFUSE_TIERS
    state['bargain'][key] = {'day': day, 'state': 'refused' if refused else 'failed'}
    extra['unit_price'] = ask
    if refused:
        outcome = '讨价还价：%s，%s不肯再把%s卖给你了（今天）' % (label, m.name, g.name)
    else:
        outcome = '讨价还价：%s，%s不肯再让价了（今天），按开价还是可以买' % (label, m.name)
    return False, extra, outcome


# ------------------------------------------------------------------ 玩家侧投影


def surface(session, story, characters):
    """信息栏交易卡的数据（只读，纯函数）；没声明商人返回 None，旧包 payload 不变。

    不含底价与商人账户余额；每个入口带上动作 id，点击后走既有的「确认 → 结算」流程。
    """
    if not declared(story):
        return None
    from . import checks, rewards
    cfg = economy.model(story)
    regime = _regime(story)
    rcfg, cur = _currency(story, cfg)
    st = rewards.state(session, rcfg)
    info = economy.REGIME_INFO[regime]
    names = {}
    for m in cfg.merchants:
        for g in list(m.sells) + list(m.buys):
            names[g.id] = g
    bag = [{'good': gid, 'name': names[gid].name if gid in names else gid, 'qty': n,
            'unit': names[gid].unit if gid in names else ''}
           for gid, n in sorted((_state(session).get('bag') or {}).items())]
    out = {'regime': info['label'], 'season': economy.SEASON_LABEL[economy.season_of(story, session)],
           'day': economy.day_of(session), 'market_day_today': economy.is_market_day(cfg, session),
           'next_market_in': economy.days_to_market(cfg, session),
           'currency': _unit_name(cur), 'wallet': st['wallet'].get(cfg.currency, 0),
           'busy': bool(session.get('active')), 'bag': bag, 'merchants': []}
    can_haggle = checks.enabled(story)
    for m in cfg.merchants:
        if not _merchant_present(session, m):
            continue
        barter_ok = m.barter if m.barter is not None else info['barter']
        row = {'id': m.id, 'name': m.name, 'sells': [], 'buys': [], 'barter': [],
               'open_today': economy.merchant_open(cfg, regime, m, session)}
        for g in m.sells:
            p = economy.price_for(story, session, m, g, cfg, regime)
            ok = economy.good_available(cfg, regime, m, g, session)
            left = stock_left(session, m, g)
            lock = _bargain_state(session, m, g)
            line = {'good': g.id, 'name': g.name, 'unit': g.unit, 'ask': p['ask'],
                    'notes': p['notes'], 'imported': p['imported'], 'available': ok,
                    'stock_left': left}
            if not ok:
                line['reason'] = '今天不开市'
            elif left == 0:
                line['reason'] = '今天卖完了'
            elif lock == 'refused':
                line['reason'] = '商人今天不肯再卖给你'
            elif g.item and has(session, g):
                line['reason'] = '已拥有'
            else:
                line['buy_action'] = '%sbuy:%s:%s' % (PREFIX, m.id, g.id)
                if m.haggle and can_haggle and lock != 'failed':
                    line['haggle_action'] = '%shaggle:%s:%s' % (PREFIX, m.id, g.id)
            row['sells'].append(line)
        for g in m.buys:
            p = economy.price_for(story, session, m, g, cfg, regime)
            have = has(session, g)
            ok = economy.good_available(cfg, regime, m, g, session)
            line = {'good': g.id, 'name': g.name, 'unit': g.unit, 'bid': p['bid'], 'have': have,
                    'notes': p['notes'], 'available': ok}
            if have and ok and p['bid'] > 0 and st['accounts'].get(m.account, 0) >= p['bid']:
                line['sell_action'] = '%ssell:%s:%s' % (PREFIX, m.id, g.id)
            row['buys'].append(line)
        if barter_ok:
            for want in m.sells:
                for give in m.buys:
                    if len(row['barter']) >= MAX_BARTER_ROWS or not has(session, give):
                        continue
                    if not (economy.good_available(cfg, regime, m, want, session)
                            and economy.good_available(cfg, regime, m, give, session)):
                        continue
                    ask = economy.price_for(story, session, m, want, cfg, regime)['ask']
                    bid = economy.price_for(story, session, m, give, cfg, regime)['bid']
                    if bid <= 0:
                        continue
                    need = -(-ask // bid)
                    row['barter'].append({
                        'get': want.name, 'give': give.name, 'need': need, 'have': has(session, give),
                        'unit': give.unit,
                        'action': '%sbarter:%s:%s:%s' % (PREFIX, m.id, want.id, give.id)
                        if has(session, give) >= need and (not give.item or need == 1) else None})
        out['merchants'].append(row)
    return out
