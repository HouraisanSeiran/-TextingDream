# -*- coding: utf-8 -*-
"""导入的世界/故事包：中文标题、简介必须原样保存；已被降成问号的请求必须拒绝。

根因（见 app/native_starts._readable 的注释）：Windows PowerShell 5.1 的
``Invoke-RestMethod -Body <字符串>`` 在 Content-Type 不带 charset 时按 ISO-8859-1 编码，
中文在到达服务器前就变成 ASCII ``?``。服务器收到的是合法 JSON，原文无法恢复。
"""
import json
import unittest

from app import native_starts
from tests import test_native_starts as base


class ImportEncodingTests(unittest.TestCase):
    # 复用 test_native_starts 的 fixture，但不继承它的用例（避免重复运行）。
    setUp = base.NativeStartTests.setUp
    tearDown = base.NativeStartTests.tearDown
    register = base.NativeStartTests.register
    draft = base.NativeStartTests.draft

    def _post_raw(self, payload, content_type='application/json; charset=utf-8'):
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        headers = dict(self.headers)
        headers['Content-Type'] = content_type
        return self.client.post('/api/inner/native-starts', headers=headers, content=body)

    def test_chinese_title_and_premise_survive_utf8_bytes(self):
        res = self._post_raw(self.draft(title='塞瓦雷拉周边探索', premise='港口结了冰，粮价在涨。'))
        self.assertEqual(res.status_code, 200, res.text)
        saved = res.json()['draft']
        self.assertEqual(saved['title'], '塞瓦雷拉周边探索')
        self.assertEqual(saved['premise'], '港口结了冰，粮价在涨。')
        stored = self.service.store.get(native_starts.KIND, saved['id'])
        self.assertEqual(stored['title'], '塞瓦雷拉周边探索')

    def test_confirmed_package_keeps_title_note_and_files(self):
        draft = self._post_raw(self.draft(title='塞瓦雷拉周边探索')).json()['draft']
        res = self.client.post('/api/inner/native-starts/%s/confirm' % draft['id'],
                               headers=self.headers, json={'expected_revision': 0})
        self.assertEqual(res.status_code, 200, res.text)
        packages = self.service.store.all('package')
        self.assertEqual(len(packages), 1)
        self.assertEqual(packages[0]['story']['title'], '塞瓦雷拉周边探索')
        self.assertEqual(packages[0]['note'], '从 civ 开局：塞瓦雷拉周边探索')
        story_files = list(self.service.runtime.files.root.rglob('story.json')) \
            if hasattr(self.service.runtime.files, 'root') else []
        for path in story_files:
            self.assertNotIn('????', path.read_text(encoding='utf-8'))

    def test_question_marked_title_is_refused(self):
        # PowerShell 5.1 默认编码会发来的样子：12 个汉字 → 12 个 '?'。
        res = self._post_raw(self.draft(title='?' * 12))
        self.assertEqual(res.status_code, 400, res.text)
        self.assertIn('UTF-8', res.json()['detail'])
        self.assertEqual(self.service.store.all(native_starts.KIND), [])

    def test_question_marked_premise_is_refused(self):
        res = self._post_raw(self.draft(premise='？？？？？？？？'))
        self.assertEqual(res.status_code, 400, res.text)

    def test_charset_less_latin1_body_does_not_reach_the_store(self):
        # 复现 PowerShell 5.1：不带 charset 的字符串 body 按 ISO-8859-1 编码，
        # 无法表示的字符变成 0x3F。
        payload = json.dumps(self.draft(title='塞瓦雷拉周边探索'), ensure_ascii=False)
        body = payload.encode('latin-1', errors='replace')
        self.assertNotIn('塞'.encode('utf-8'), body)
        headers = dict(self.headers)
        headers['Content-Type'] = 'application/json'
        res = self.client.post('/api/inner/native-starts', headers=headers, content=body)
        self.assertEqual(res.status_code, 400, res.text)
        self.assertEqual(self.service.store.all(native_starts.KIND), [])

    def test_ordinary_question_marks_are_allowed(self):
        res = self._post_raw(self.draft(title='谁偷了麦子？', premise='真的是他吗?'))
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()['draft']['title'], '谁偷了麦子？')


if __name__ == '__main__':
    unittest.main()
