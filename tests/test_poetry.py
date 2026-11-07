# -*- coding: utf-8 -*-
"""诗歌创作：体裁列表、上下文拼装（范例挑选）、模型输出检查。用假元素库，不依赖真实库。"""
import unittest

from app import poetry as po


class FakeElements:
    def __init__(self, items):
        self.items = items

    def search(self, tags_any=(), limit=200, include_payload=False, **_):
        return {'items': [i for i in self.items if set(i['tags']) & set(tags_any)][:limit]}


def form(eid, name, spec):
    return {'namespace': 'poetry-forms', 'element_id': eid, 'name': name, 'summary': '',
            'tags': ['kind:poetry_form'], 'payload': {'poetry_form': spec}}


def poem(eid, title, form_ref, text):
    return {'namespace': 'poems', 'element_id': eid, 'name': title, 'summary': '', 'tags': ['kind:poem'],
            'payload': {'poem': {'title': title, 'author': 'x', 'era': 'y', 'form_ref': form_ref,
                                 'text': text, 'excerpt': False}}}


JUEJU = {'tradition': 'chinese', 'language': 'classical_chinese', 'lines': 4,
         'line_pattern': '每句五字', 'rhyme_scheme': '二四句押平声韵', 'constraints': ['四句', '每句五字'],
         'example_ref': 'poem_jingyesi'}
SONNET = {'tradition': 'western', 'language': 'english', 'lines': 14,
          'meter': 'iambic pentameter', 'rhyme_scheme': 'ABAB CDCD EFEF GG', 'constraints': ['14 行']}
LIB = FakeElements([
    form('form_wujue', '五言绝句', JUEJU),
    form('form_sonnet', '莎士比亚体十四行诗', SONNET),
    form('form_broken', '坏条目', 'not a dict'),
    poem('poem_jingyesi', '静夜思', 'form_wujue', '床前明月光，\n疑是地上霜。\n举头望明月，\n低头思故乡。'),
    poem('poem_other', '登鹳雀楼', 'poetry-forms/form_wujue', '白日依山尽……'),
    poem('poem_s18', 'Sonnet 18', 'form_sonnet', 'Shall I compare thee…'),
])


class FormsTests(unittest.TestCase):
    def test_list_skips_broken(self):
        ids = [f['id'] for f in po.forms(LIB)]
        self.assertEqual(sorted(ids), ['form_sonnet', 'form_wujue'])

    def test_context_prefers_example_ref(self):
        ctx, spec = po.build_context(LIB, 'form_wujue', '秋夜思乡', speaker='酒馆里的吟游诗人',
                                     setting={'tech': '中世纪'})
        self.assertEqual([e['title'] for e in ctx['examples']], ['静夜思', '登鹳雀楼'])
        self.assertEqual(ctx['speaker'], '酒馆里的吟游诗人')
        self.assertEqual(ctx['setting'], {'tech': '中世纪'})
        self.assertEqual(ctx['constraints'], ['四句', '每句五字'])

    def test_bad_input(self):
        with self.assertRaises(po.PoetryError):
            po.build_context(LIB, 'form_none', '主题')
        with self.assertRaises(po.PoetryError):
            po.build_context(LIB, 'form_wujue', '  ')
        with self.assertRaises(po.PoetryError):
            po.build_context(LIB, 'form_wujue', 'x' * 201)


class CheckTests(unittest.TestCase):
    def test_good_jueju(self):
        r = po.check({'title': '秋思', 'lines': ['孤灯照客窗，', '霜叶落空江。', '一曲琴声远，', '归心向故邦。']}, JUEJU)
        self.assertTrue(r['ok'], r['issues'])
        self.assertIn('每行字数', r['checked'])
        self.assertIn('平仄 / 格律', r['not_checked'])

    def test_wrong_lines_and_length(self):
        r = po.check({'lines': '孤灯照客窗\n霜叶落空江江\n一曲琴声远'}, JUEJU)
        self.assertFalse(r['ok'])
        self.assertTrue(any('行数' in x for x in r['issues']))
        self.assertTrue(any('第 2 行' in x for x in r['issues']))

    def test_sonnet_only_counts_lines(self):
        r = po.check({'lines': ['line'] * 14}, SONNET)
        self.assertTrue(r['ok'])
        self.assertEqual(r['checked'], ['行数'])

    def test_bad_output(self):
        for raw in (None, {}, {'lines': ['', '  ']}):
            with self.assertRaises(po.PoetryError):
                po.check(raw, JUEJU)


if __name__ == '__main__':
    unittest.main()
