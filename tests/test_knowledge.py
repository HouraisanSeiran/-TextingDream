import asyncio
import copy
import json
import tempfile
import unittest
from pathlib import Path
from app.service import Service
from app.storage import Store
from app.contracts import Turn, DraftRequest
from app.knowledge import retrieve, notebook, extract_notes
from app.prompts import surface_prefix, author_prefix, stable_json

ROOT = Path(__file__).resolve().parents[1]


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.service = Service(Store(Path(self.temp.name) / 'test.sqlite3'), ROOT)
        self.rt = self.service.runtime
        self.s = self.rt.new_session('知识测试', 'protagonist')

    def tearDown(self):
        self.temp.cleanup()

    def test_document_is_source_and_existing_journey_pinned(self):
        folder = self.rt.files.directory
        file = next((folder / '知识点').rglob('xuanlu_001.md'))
        text = file.read_text(encoding='utf-8')
        file.write_text(text + '\n文档变更唯一标记。', encoding='utf-8')
        new = self.rt.new_session('新版', 'protagonist')
        self.assertNotEqual(new['revision'], self.s['revision'])
        self.assertIn('文档变更唯一标记', json.dumps(self.rt.package(new['revision']), ensure_ascii=False))
        self.assertNotIn('文档变更唯一标记', json.dumps(self.rt.package(self.s['revision']), ensure_ascii=False))
        revision = new['revision']
        file.write_text('bad metadata', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.rt.reload_documents()
        self.assertEqual(self.rt.package()['id'], revision)

    def test_retrieval_visibility_stability_and_budget(self):
        points = [dict(id='secret', title='隐藏', keywords=['商队'], visibility='author', content='秘密标记'),
                  dict(id='closed', title='未解锁', keywords=['商队'], visibility='public', reveal_flag='open', content='未解锁标记'),
                  dict(id='public', title='商队供水', keywords=['商队','水源'], visibility='public', content='商队需要水源。')]
        story = {'knowledge': points}
        selected = retrieve(story, '商队水源')
        self.assertEqual([p['id'] for p in selected], ['public'])
        self.assertEqual(selected, retrieve({'knowledge': list(reversed(points))}, '商队水源'))
        self.assertEqual(retrieve(story, '完全不相关'), [])
        self.assertEqual(retrieve(story, '商队水源', budget=5), [])
        self.assertIn('secret', [p['id'] for p in retrieve(story, '商队', 'author')])
        points[2]['requires'] = ['secret']
        self.assertEqual(retrieve(story, '水源'), [])

    def test_only_displayed_replies_can_become_notebook_and_rollback(self):
        s = self.s
        s['facts'].append({'id':'hidden','text':'后台真相封路3天'})
        request = Turn(message='我的愿望是获得黄金一百箱')
        result = self.rt.prepare_turn(s, request)
        reply = '商人说道路封闭9天。这个说法尚未核实。\n\n我没有拿走柜台上的铜匣。'
        self.rt.finish_turn(s, request, reply, result, {})
        notes = notebook(s)
        output = json.dumps(notes, ensure_ascii=False)
        self.assertNotIn('3天', output)
        self.assertNotIn('黄金', output)
        self.assertIn('没有拿走', output)
        for n in notes:
            self.assertIn(n['content'], reply)
            self.assertIn(n['summary'], reply)
        persisted = self.rt.files.directory / '生成记录/旅程' / (s['id'] + '.md')
        self.assertIn('9天', persisted.read_text(encoding='utf-8'))
        other = self.rt.new_session('另一旅程', 'protagonist')
        self.assertEqual(notebook(other), [])
        self.rt.close_event(s)
        restored = self.rt.rollback(s, s['archives'][-1]['id'])
        self.assertEqual(notebook(restored), [])
        self.assertNotIn('9天', persisted.read_text(encoding='utf-8'))

    def test_overview_only_prefix_and_inner_example(self):
        p = self.rt.package()
        token = '测试整包泄露标记'
        p['story']['knowledge'].append(dict(id='sentinel',title=token,content=token,visibility='author',keywords=[token]))
        self.assertNotIn(token, surface_prefix(p, ''))
        self.assertNotIn(token, author_prefix(p, ''))
        self.assertNotIn(token, stable_json(self.service.example('worldview', p)))
        context = self.rt.context(self.s, 'player', '万言机翻译方言', self.service.preferences())
        self.assertTrue(context['knowledge'])
        self.assertLessEqual(len(stable_json(context['knowledge'])), 3600)
        self.assertLess(len(context['knowledge']), len(p['story']['knowledge']))

    def test_inner_generation_saved_but_not_disclosed(self):
        draft = asyncio.run(self.service.generate(DraftRequest(kind='item', instruction='铜匣秘密')))
        path = self.rt.files.directory / '生成记录/里层草稿' / (draft['id'] + '.md')
        self.assertTrue(path.exists())
        self.assertIn('匣底', path.read_text(encoding='utf-8'))
        self.assertEqual(notebook(self.s), [])

    def test_document_roundtrip_and_character_separation(self):
        source = self.rt.files.read()
        self.assertNotIn('characters', source)
        self.assertEqual(set(source['worldview']), {'premise'})
        self.rt.files.write(source)
        self.assertEqual(source, self.rt.files.read())

    def test_qualification_after_two_sentences_is_retained(self):
        text = '商人称王位已经更替。城里正在庆祝。可是这个说法尚未得到证实。'
        notes = extract_notes(text, {'id':'source','scope':'surface'})
        self.assertEqual(notes[0]['summary'], text)
