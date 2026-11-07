# -*- coding: utf-8 -*-
"""世界设定：校验、越档判断、推荐分组、提示词摘要。推荐用假元素库，不依赖真实百科库。"""
import unittest

from app import world_setting as ws


class FakeElements:
    def __init__(self, items):
        self.items = items

    def search(self, tags_any=(), limit=200, **_):
        hit = [i for i in self.items if set(i['tags']) & set(tags_any)]
        return {'items': hit[:limit]}


def item(eid, name, *tags):
    return {'namespace': 'lib', 'element_id': eid, 'name': name, 'summary': '', 'tags': list(tags)}


SETTING = {'genres': [{'tag': 'western_fantasy', 'weight': 3}, {'tag': 'steampunk', 'weight': 1}],
           'tech': 'steam', 'magic': 'rare',
           'polities': [{'id': 'ardel', 'name': '阿尔德王国', 'summary': '靠煤矿起家的王国',
                         'tags': ['polity:monarchy', '自定义标签']}]}


class NormalizeTests(unittest.TestCase):
    def test_none_is_valid(self):
        self.assertIsNone(ws.normalize(None))
        ws.validate({'worldview': {}})

    def test_author_written_entries_and_free_tags(self):
        out = ws.normalize(SETTING)
        self.assertEqual(out['polities'][0]['tags'], ['polity:monarchy', '自定义标签'])
        self.assertEqual(out['races'], [])
        self.assertIsNone(out['polities'][0]['element_ref'])

    def test_rejects_bad_values(self):
        for bad in ({'tech': 'nuclear'}, {'magic': 'godlike'},
                    {'genres': [{'tag': 'cyberpunk', 'weight': 1}]},
                    {'genres': [{'tag': 'xianxia', 'weight': 5}]},
                    {'polities': [{'id': 'Bad ID', 'name': 'x'}]},
                    {'polities': [{'id': 'a', 'name': ''}]},
                    {'races': [{'id': 'a', 'name': 'x', 'tags': ['有 空格']}]},
                    {'factions': [{'id': 'a', 'name': 'x', 'element_ref': 'no-slash'}]}):
            with self.assertRaises(ws.SettingError, msg=bad):
                ws.normalize(bad)


class TierTests(unittest.TestCase):
    def test_conflicts(self):
        s = ws.normalize(SETTING)
        self.assertEqual(ws.conflicts(['tech:medieval', 'magic:rare'], s), [])
        self.assertEqual(len(ws.conflicts(['tech:early_modern'], s)), 1)
        self.assertEqual(len(ws.conflicts(['magic:abundant'], s)), 1)
        self.assertEqual(ws.conflicts(['kind:herb'], s), [])
        self.assertEqual(ws.conflicts(['tech:early_modern'], {'genres': []}), [])


class RecommendTests(unittest.TestCase):
    def test_groups_scoring_and_tier_filter(self):
        lib = FakeElements([
            item('elf', '精灵', 'kind:race', 'genre:western_fantasy'),
            item('fox', '狐仙', 'kind:race', 'genre:xianxia'),
            item('engine', '蒸汽机', 'tech:steam', 'genre:steampunk'),
            item('radio', '无线电', 'tech:early_modern', 'genre:steampunk'),
            item('kingdom', '封建王国', 'kind:polity', 'genre:western_fantasy', 'genre:steampunk'),
        ])
        out = ws.recommend(lib, SETTING, adopted=['lib/elf'])
        groups = {g['id']: g for g in out['groups']}
        self.assertEqual([r['element_id'] for r in groups['races']['items']], ['elf'])
        self.assertTrue(groups['races']['items'][0]['adopted'])
        self.assertEqual([r['element_id'] for r in groups['tech']['items']], ['engine'])
        self.assertEqual(groups['tech']['skipped_by_tier'], 1)
        self.assertEqual(groups['polities']['items'][0]['score'], 4)

    def test_polity_with_tech_tag_only_in_polity_group(self):
        lib = FakeElements([item('parl', '议会君主国', 'kind:polity', 'tech:steam',
                                 'category:institution', 'genre:western_fantasy')])
        groups = {g['id']: g for g in ws.recommend(lib, SETTING)['groups']}
        self.assertEqual(len(groups['polities']['items']), 1)
        self.assertEqual(groups['tech']['items'], [])
        self.assertEqual(groups['factions']['items'], [])


class CategoryTests(unittest.TestCase):
    LIB = FakeElements([
        item('elf', '精灵', 'kind:race', 'genre:western_fantasy'),
        item('mage', '法师学院', 'category:institution', 'genre:western_fantasy', 'magic:common'),
        item('fox', '狐仙', 'kind:race', 'genre:xianxia'),
        item('loco', '蒸汽机车', 'tech:steam', 'genre:steampunk'),
        item('radio', '无线电', 'tech:early_modern', 'genre:western_fantasy'),
        item('kingdom', '议会君主国', 'kind:polity', 'tech:steam', 'genre:western_fantasy'),
    ])

    def test_unknown_category_rejected(self):
        with self.assertRaises(ws.SettingError):
            ws.normalize({'categories': ['cyberpunk']})

    def test_category_selects_elements_and_tech_is_separate(self):
        out = ws.category_elements(self.LIB, {'categories': ['western_fantasy'], 'tech': 'steam', 'magic': 'rare'})
        groups = {g['id']: g for g in out['groups']}
        # 国家模板带 tech:steam 也仍属大类，不算技术元素
        self.assertEqual([r['element_id'] for r in groups['western_fantasy']['items']], ['elf', 'kingdom'])
        self.assertEqual(groups['western_fantasy']['skipped_by_tier'], 1)  # 法师学院需要魔法常见
        # 技术不跟大类走：无线电虽带西幻标签也不进大类组，只按科技档位判断（越档被排除）
        self.assertEqual([r['element_id'] for r in groups['technology']['items']], ['loco'])
        self.assertEqual(groups['technology']['skipped_by_tier'], 1)

    def test_no_tech_tier_means_no_tech_elements(self):
        out = ws.category_elements(self.LIB, {'categories': ['western_fantasy']})
        self.assertEqual({g['id']: g for g in out['groups']}['technology']['items'], [])


class AgentTests(unittest.TestCase):
    def test_author_entries_kept_and_fake_refs_dropped(self):
        from app import worldview_agent as wa
        setting = ws.normalize(SETTING)
        raw = {'premise': '煤烟与魔法并存的王国', 'laws': ['魔法稀少'], 'polities': [],
               'used_elements': ['lib/elf', 'lib/fake']}
        result, warnings = wa.validate_result(raw, setting, {'lib/elf'})
        self.assertEqual(result['polities'][0]['name'], '阿尔德王国')
        self.assertEqual(result['used_elements'], ['lib/elf'])
        self.assertEqual(len(warnings), 2)
        with self.assertRaises(wa.AgentError):
            wa.validate_result({'laws': []}, setting, set())

    def test_context_round_robin(self):
        from app import worldview_agent as wa
        setting = {'categories': ['western_fantasy'], 'tech': 'steam', 'magic': 'rare'}
        resolved = ws.category_elements(CategoryTests.LIB, setting)
        ctx = wa.build_context(setting, resolved)
        self.assertEqual({r['ref'] for r in ctx['available_elements']}, {'lib/elf', 'lib/kingdom', 'lib/loco'})
        self.assertEqual(ctx['tech']['label'], '蒸汽')


class PromptTests(unittest.TestCase):
    def test_block(self):
        self.assertIsNone(ws.prompt_block({'worldview': {}}))
        block = ws.prompt_block({'worldview': {'setting': SETTING}})
        self.assertIn('西幻（主体）', block['genres'])
        self.assertTrue(block['tech'].startswith('蒸汽'))
        self.assertTrue(block['magic'].startswith('稀少'))
        self.assertEqual(block['polities'], ['阿尔德王国：靠煤矿起家的王国'])

    def test_options_have_descriptions(self):
        opts = ws.options()
        self.assertEqual([m['label'] for m in opts['magic']], ['无魔', '稀少', '常见', '丰富'])
        self.assertTrue(all(t['description'] for t in opts['tech']))


class FiveTierTests(unittest.TestCase):
    def test_order_and_ids(self):
        self.assertEqual(ws.TECH, ('classical', 'medieval', 'renaissance', 'steam', 'early_modern'))

    def test_renaissance_is_beyond_medieval_but_before_steam(self):
        med = ws.normalize({'tech': 'medieval'})
        ren = ws.normalize({'tech': 'renaissance'})
        self.assertEqual(len(ws.conflicts(['tech:renaissance'], med)), 1)
        self.assertEqual(ws.conflicts(['tech:medieval'], ren), [])
        self.assertEqual(len(ws.conflicts(['tech:steam'], ren)), 1)

    def test_every_tier_has_markers_in_options(self):
        tech = ws.options()['tech']
        self.assertEqual([t['id'] for t in tech], list(ws.TECH))
        for t in tech:
            self.assertTrue(2 <= len(t['markers']) <= 3, t['id'])

    def test_tier_from_markers(self):
        m = {t: ws.TECH_INFO[t][2] for t in ws.TECH}
        self.assertIsNone(ws.tier_from_markers([]))
        self.assertEqual(ws.tier_from_markers(m['classical']), 'classical')
        self.assertEqual(ws.tier_from_markers(m['classical'] + m['medieval']), 'medieval')
        # 缺一项中世纪代表科技：停在古典，哪怕更高档的齐了
        partial = m['classical'] + m['medieval'][:2] + m['renaissance']
        self.assertEqual(ws.tier_from_markers(partial), 'classical')
        everything = [x for t in ws.TECH for x in m[t]]
        self.assertEqual(ws.tier_from_markers(everything), 'early_modern')
        self.assertEqual(ws.tier_from_markers(['不存在的科技']), None)

    def test_tech_markers_validation(self):
        out = ws.normalize({'tech': 'medieval', 'tech_markers': ['铁器冶炼', '铁器冶炼']})
        self.assertEqual(out['tech_markers'], ['铁器冶炼'])
        self.assertNotIn('tech_markers', ws.normalize({'tech': 'medieval'}))
        with self.assertRaises(ws.SettingError):
            ws.normalize({'tech_markers': ['瞎编的科技']})
        with self.assertRaises(ws.SettingError):
            ws.normalize({'tech_markers': '铁器冶炼'})


if __name__ == '__main__':
    unittest.main()
