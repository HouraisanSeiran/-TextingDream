"""铜杯酒馆元素试点：清单里的元素必须真在本地百科库里，价格与锚点协调，购买动作扣钱正确。

库不存在时测试失败（不 skip），并提示构库命令。
"""
import asyncio
import copy
import tempfile
import unittest
from pathlib import Path

from app import encyclopedia, free_actions
from app.contracts import Turn
from app.service import Service
from app.storage import Store
from tools import game_fields, playable_scenes
from tools.playable_scenes import ROOT

DB = ROOT / 'artifacts/human-encyclopedia/encyclopedia.sqlite3'
BUILD = ('.venv\\Scripts\\python.exe -X utf8 -m tools.encyclopedia_build --with-traits --with-cuisine '
         '--with-attributes --with-culture --with-fantasy-biology --with-alchemy --with-reality-herbs '
         '--with-formulae --with-cuisine-western --with-world-setting --with-cuisine-world --with-shops')
ANCHORS = {'ale': 2, 'ferry': 12, 'dock_work': 6, 'job': 8}


def require_library(test):
    test.assertTrue(DB.exists(), '百科库不存在：%s。请先运行：%s' % (DB.relative_to(ROOT).as_posix(), BUILD))


class PilotListTests(unittest.TestCase):
    def setUp(self):
        require_library(self)
        self.pilot = playable_scenes.pilot()
        self.rows = self.pilot['entries']

    def test_size_and_uses(self):
        self.assertTrue(20 <= len(self.rows) <= 30, len(self.rows))
        uses = {r['use'] for r in self.rows}
        self.assertEqual(uses, {'menu', 'shelf', 'shop'})
        shops = [r for r in self.rows if r['use'] == 'shop']
        self.assertTrue(2 <= len(shops) <= 4)
        self.assertEqual(len({(r['namespace'], r['element_id']) for r in self.rows}), len(self.rows))

    def test_every_element_exists_with_locked_version(self):
        for r in self.rows:
            with self.subTest(element=r['element_id']):
                d = encyclopedia.get(DB, r['element_id'], namespace=r['namespace'], version=r['version'])
                self.assertEqual(d['version'], r['version'])
                self.assertEqual(d['current_version'], r['version'], '库内已有新版本，请复核清单')
                self.assertEqual(d['payload'].get('primary'), r['primary'])

    def test_goods_have_game_and_are_for_sale(self):
        for r in self.rows:
            if r['use'] == 'shop':
                continue
            with self.subTest(element=r['element_id']):
                d = encyclopedia.get(DB, r['element_id'], namespace=r['namespace'], version=r['version'])
                game = d['payload'].get('game')
                self.assertIsInstance(game, dict, '缺 game 字段')
                # 即使世界禁掉全部限售原因，这些货品也必须可买：清单里不放限售品。
                self.assertTrue(game_fields.is_for_sale(game, set(game_fields.RESTRICTIONS)),
                                '带限售原因或不可买')
                self.assertIsNone(game.get('restriction'))
                price = game['price']
                self.assertEqual({'min': price['min'], 'max': price['max']},
                                 {'min': r['library_price']['min'], 'max': r['library_price']['max']})
                self.assertIn(r['supplied_by'], game['sold_by'])
                self.assertTrue(price['min'] <= r['scene_price'] <= price['max'],
                                '场景价 %s 不在库内区间 %s-%s' % (r['scene_price'], price['min'], price['max']))

    def test_shops_exist_and_match_keys(self):
        shop_keys = set()
        for r in self.rows:
            if r['use'] != 'shop':
                continue
            with self.subTest(element=r['element_id']):
                d = encyclopedia.get(DB, r['element_id'], namespace=r['namespace'], version=r['version'])
                self.assertEqual(r['namespace'], 'shops')
                self.assertEqual(d['payload']['shop']['key'], r['supplied_by'])
                shop_keys.add(r['supplied_by'])
        # 货品的 supplied_by 必须是清单里已选的店铺，场景里才有出售它的地方。
        for r in self.rows:
            if r['use'] != 'shop':
                self.assertIn(r['supplied_by'], shop_keys, r['element_id'])

    def test_prices_do_not_conflict_with_anchors(self):
        by_id = {r['element_id']: r for r in self.rows}
        self.assertEqual(by_id['flavors_beer']['scene_price'], ANCHORS['ale'])
        a = self.pilot['anchors']
        self.assertEqual((a['ale_pence'], a['ferry_ticket_pence'], a['dock_work_pence'], a['job_reward_pence']),
                         (2, 12, 6, 8))
        for r in self.rows:
            price = r.get('scene_price')
            if price is None:
                continue
            # 单份货品不应贵过一次短工报酬，也不能让船票买不起之外的“主线”被一份饭吃掉。
            self.assertLess(price, ANCHORS['dock_work'] + 1, r['element_id'])
            if r['kind'] == 'dish':
                self.assertTrue(3 <= price <= 6 or price <= 2, r['element_id'])
        # 同一杯酒不能有两个价；蜂蜜酒比麦酒贵。
        self.assertGreater(by_id['flavors_mead']['scene_price'], by_id['flavors_beer']['scene_price'])


class PilotSceneTests(unittest.TestCase):
    def setUp(self):
        require_library(self)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.service = Service(Store(Path(self.tmp.name) / 'test.sqlite3'), Path(self.tmp.name))
        self.service.provider.configure({'offline': True})
        self.rt = self.service.runtime
        self.data = playable_scenes.tavern()
        self.pilot = playable_scenes.pilot()

    def start(self):
        self.rt.commit_package(self.data['story'], self.data['characters'], 'pilot test')
        return self.rt.new_session('test', 'protagonist')

    def do(self, s, action_id):
        action = free_actions.describe(s, self.rt.package(s['revision'])['story'], self.rt.node(s), action_id)
        asyncio.run(self.service.turn(s['id'], Turn(message=action['label'], action_id=action_id,
                                                    confirm=action['confirm'])))
        return self.service.store.session(s['id'])

    def actions(self):
        return {a['id']: a for ev in self.data['story']['events'] for a in ev['actions']}

    def test_buy_actions_cost_matches_pilot_price(self):
        buys = [r for r in self.pilot['entries'] if r.get('action')]
        self.assertGreaterEqual(len(buys), 3)
        acts = self.actions()
        for r in buys:
            with self.subTest(action=r['action']['id']):
                self.assertEqual(acts[r['action']['id']]['costs'], {'pence': r['scene_price']})
                self.assertIn('%d便士' % r['scene_price'], acts[r['action']['id']]['label'])
        self.assertEqual(acts['buy_ale']['costs'], {'pence': 2})

    def at_place(self, place):
        """按 playtest 主路线走到 place 的起始事件（不含该地点内的任何动作）。"""
        s = self.start()
        if place == 'hall':
            return s  # 酒馆货品在开局的 welcome 事件里出售
        for step in self.data['playtest']['route']:
            if step == '@' + place:
                break
            if step.startswith('@'):
                self.rt.move(s, step[1:])
                s = self.service.store.session(s['id'])
            elif step.startswith('?'):
                if step[1:] in {row['id'] for row in self.rt.surface(s)['actions']}:
                    s = self.do(s, step[1:])
            else:
                s = self.do(s, step)
        if place != 'hall':
            self.rt.move(s, place)
            s = self.service.store.session(s['id'])
        return s

    def test_buying_deducts_pence_exactly(self):
        for r in [r for r in self.pilot['entries'] if r.get('action')]:
            with self.subTest(action=r['action']['id']):
                s = self.at_place(r['sold_at'])
                before = s['local']['resources']['pence']
                self.assertGreaterEqual(before, r['scene_price'])
                s = self.do(s, r['action']['id'])
                self.assertEqual(s['local']['resources']['pence'], before - r['scene_price'])

    def test_purchase_belongs_to_the_right_shop_and_seller(self):
        events = {a['id']: ev for ev in self.data['story']['events'] for a in ev['actions']}
        tavern_menu = {'buy_ale', 'buy_mead', 'buy_rarebit', 'buy_stew', 'buy_pie'}
        owner = {'baker': {'buy_bread', 'buy_brioche'}, 'fishmonger': {'buy_kippers', 'buy_herring'}}
        npcs = {c['id'] for c in self.data['characters']['characters']}
        shops = {r['supplied_by']: r for r in self.pilot['entries'] if r['use'] == 'shop'}
        for r in self.pilot['entries']:
            if r['use'] == 'shop' or not r.get('action'):
                continue
            with self.subTest(action=r['action']['id']):
                ev = events[r['action']['id']]
                self.assertEqual(ev['location_id'], r['sold_at'])
                self.assertEqual(r['sold_at'], shops[r['supplied_by']]['sold_at'])
                seller = shops[r['supplied_by']].get('npc')
                self.assertIn(seller, npcs)
                self.assertIn(seller, ev['participants'])
                self.assertEqual(r.get('npc'), seller)
                if r['supplied_by'] == 'tavern':
                    self.assertIn(r['action']['id'], tavern_menu)
                    self.assertEqual(seller, 'bess')
                else:
                    self.assertIn(r['action']['id'], owner[r['supplied_by']])
        for key, ids in owner.items():
            self.assertEqual({r['action']['id'] for r in self.pilot['entries']
                              if r.get('action') and r['supplied_by'] == key}, ids)
        # 贝丝的菜单里没有面包与鱼货。
        self.assertNotIn('面包', playable_scenes.pilot_menu_text())
        self.assertNotIn('鲱', playable_scenes.pilot_menu_text())

    def test_stall_npcs_have_valid_private_cards(self):
        from app import npc_cards
        npc_cards.validate(self.data['story'], self.data['characters'])
        rows = {c['id']: c for c in self.data['characters']['characters']}
        for cid in ('baker', 'fishmonger'):
            with self.subTest(npc=cid):
                self.assertEqual(rows[cid]['role'], '次要角色')
                self.assertEqual(rows[cid]['location_id'], 'quay')
                card = rows[cid]['npc_card']
                self.assertTrue(card['values']['text'])
                self.assertTrue(any(k['visibility'] == 'private' for k in card['knowledge']))
        self.assertIsNone(rows['player'].get('npc_card'))

    def test_public_descriptions_are_present_and_harmless(self):
        from app import element_assembly
        banned = ['治', '疗', '止', '消炎', '退烧', '安神', '镇痛', '药效', '功效', '煎服', '每日',
                  '剂量', '服用', '内服', '外敷', '泡茶', '入药', '主治']
        for sel in playable_scenes.pilot_selections():
            d = sel['disclosure']
            with self.subTest(element=sel['element_id']):
                text = d['public_description']
                self.assertTrue(text.strip())
                self.assertLessEqual(len(text), element_assembly.MAX_PUBLIC_DESCRIPTION)
                self.assertEqual(d['public_fields'], [])
                self.assertEqual(d['known_by'], ['player'])
        for r in self.pilot['entries']:
            if r['use'] == 'shelf' and r['kind'] == 'herb':
                for word in banned:
                    self.assertNotIn(word, r['public_description'], (r['element_id'], word))
            self.assertIn(r['sold_at'], {p['id'] for p in self.data['story']['locations']})

    def run_route(self, name):
        s = self.start()
        flow = []
        for step in self.data['playtest'][name]:
            if step.startswith('@'):
                self.rt.move(s, step[1:])
                s = self.service.store.session(s['id'])
                continue
            if step.startswith('?'):
                step = step[1:]
                if step not in {row['id'] for row in self.rt.surface(s)['actions']}:
                    continue
            before = s['local']['resources']['pence']
            s = self.do(s, step)
            flow.append((step, s['local']['resources']['pence'] - before))
        return s, [(k, v) for k, v in flow if v]

    def test_main_route_buys_and_balance_is_exact(self):
        s, flow = self.run_route('route')
        self.assertEqual(flow, [('buy_ale', -2), ('deliver_invoice', 8), ('buy_bread', -2),
                                ('dock_work', 6), ('sail', -12)])
        self.assertEqual(s['local']['resources']['pence'], 18 - 2 + 8 - 2 + 6 - 12)
        self.assertTrue(s['flags'].get('sail'))

    def test_alternative_route_buys_and_balance_is_exact(self):
        s, flow = self.run_route('alternative')
        self.assertEqual(flow, [('deliver_invoice', 8), ('buy_kippers', -3)])
        self.assertEqual(s['local']['resources']['pence'], 18 + 8 - 3)
        self.assertTrue(s['flags'].get('stay'))

    def test_inquiry_is_free_and_gives_prices(self):
        acts = self.actions()
        self.assertNotIn('costs', acts['ask_apothecary'])
        self.assertNotIn('costs', acts['read_menu'])
        shelf = [r for r in self.pilot['entries'] if r.get('inquiry')]
        self.assertGreaterEqual(len(shelf), 1)
        text = acts['ask_apothecary']['effects'][0]['text']
        for r in shelf:
            self.assertIn(r['menu_name'], text)

    def test_read_menu_costs_nothing_in_session(self):
        s = self.start()
        before = s['local']['resources']['pence']
        s = self.do(s, 'read_menu')
        self.assertEqual(s['local']['resources']['pence'], before)

    def test_manifest_assembly_locks_pilot_into_story(self):
        self.service.elements.configure(DB, allowed_roots=[ROOT / 'artifacts'])
        data = copy.deepcopy(self.data)
        manifest, _warnings = playable_scenes.attach_pilot_manifest(data, self.service.elements)
        self.assertEqual(manifest['count'], len(self.pilot['entries']))
        locked = {e['ref']: e['version'] for e in manifest['elements']}
        for r in self.pilot['entries']:
            self.assertEqual(locked['%s/%s' % (r['namespace'], r['element_id'])], r['version'])
        self.rt.commit_package(data['story'], data['characters'], 'pilot manifest')
        s = self.rt.new_session('test', 'protagonist')
        self.assertEqual(s['local']['resources']['pence'], 18)


if __name__ == '__main__':
    unittest.main()
