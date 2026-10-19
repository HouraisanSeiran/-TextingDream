"""Local sparse TF-IDF vectors. Index is derived from the current save only.

No embedding service or token cost. This is lexical retrieval with a small
explicit synonym vocabulary, not a neural semantic embedding model.
"""
import hashlib
import json
import math
import re
from collections import Counter

ALIASES = {
    '做饭': ('做饭', '下厨', '饭菜', '炒肉', '白粥', '肉片', '米粥'),
    '初次': ('第一次', '第1次', '头一次', '初次'),
    '口味': ('好吃', '味道', '口味', '咸淡'),
    '暗号': ('暗号',),
    '餐食': ('麦饼', '豆汤'),
    '记忆标记': ('临时记忆标记', '临时标记'),
}
STOP = ('之前', '有没有', '请问', '根据', '对话', '回答', '不要', '自己',
        '可以', '什么', '现在', '一个', '我们', '这个', '继续', '然后', '一下')

def subject_query(text):
    # Strip presentation instructions, never rewrite the source evidence.
    text=re.split(r'请自然写|请用.{0,8}字|约\d+[—到～-]?\d*字',text)[0]
    return re.sub(r'请用我自己的内心回忆[：:]|只引用我原来的说法|不知道就说记不清.*|不补编来历', '', text)


def is_question(text):
    return any(w in text for w in ('什么','如何','怎样','是否','好不好','？','?','记不清'))


def vector(text):
    text = text.lower()
    concepts = ['@' + name for name, words in ALIASES.items() if any(w in text for w in words)]
    for word in STOP:
        text = text.replace(word, ' ')
    terms = re.findall(r'[a-z0-9_]{2,}', text)
    for run in re.findall(r'[\u4e00-\u9fff]+', text):
        terms.extend(run[i:i+2] for i in range(len(run)-1))
    counts = Counter(terms)
    counts.update({term: 3 for term in concepts})
    return dict(counts)


def dialogue_records(session, package):
    records = []
    places = {x['id']: x['name'] for x in package['story']['locations']}
    nodes = {x['id']: x for x in package['story']['events']}
    for event in session['archives'] + ([session['active']] if session['active'] else []):
        for i, turn in enumerate(event['turns']):
            records.append({
                'source_id': event['id'] + ':' + str(i), 'event_id': event['id'],
                'conversation_id': event.get('conversation', {}).get('id', event['id']),
                'event': event['title'], 'location': places.get(event.get('before', {}).get('location'), '未记录'),
                'scene_participants': nodes.get(event['node'], {}).get('participants', []),
                'audience': 'player', 'npc_knowledge': '参与名单不证明听见私语或内心活动；NPC知情需独立证据',
                'input': turn['input'], 'reply': turn['reply'],
                'channel': turn.get('channel','unknown'), 'listeners':turn.get('listeners',[]),
                'turn_index':len(records), 'source_priority':'原始玩家输入优先；生成正文不可覆盖原始陈述',
                'evidence_type': '历史对话原文，不代表已证实事实',
            })
    return records


class Recall:
    def __init__(self, store):
        self.store = store
        with store.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS recall_vectors(session TEXT, source TEXT, signature TEXT, body TEXT, vector TEXT, PRIMARY KEY(session,source))')

    def sync(self, session_id, records):
        # Reconcile deletions as well: a rollback must remove future memories.
        with self.store.connect() as db:
            old = {r[0]: r[1] for r in db.execute('SELECT source,signature FROM recall_vectors WHERE session=?', (session_id,))}
            live = set()
            for r in records:
                source = r['source_id']; live.add(source)
                body = json.dumps(r, ensure_ascii=False, sort_keys=True)
                signature = hashlib.sha256(body.encode('utf-8')).hexdigest()
                if old.get(source) != signature:
                    v = vector(r['input'] + '\n' + r['reply'])
                    db.execute('INSERT OR REPLACE INTO recall_vectors VALUES(?,?,?,?,?)',
                               (session_id, source, signature, body, json.dumps(v, ensure_ascii=False)))
            db.executemany('DELETE FROM recall_vectors WHERE session=? AND source=?',
                           [(session_id, source) for source in old.keys() - live])

    def search(self, session_id, query, records, exclude=(), k=3, threshold=0.12):
        query=subject_query(query)
        q = vector(query)
        if not q:
            return []
        self.sync(session_id, records)
        with self.store.connect() as db:
            rows = db.execute('SELECT source,body,vector FROM recall_vectors WHERE session=? ORDER BY rowid', (session_id,)).fetchall()
        corpus = [(source, json.loads(body), json.loads(v)) for source, body, v in rows]
        df = Counter(term for _, _, v in corpus for term in v)
        def weights(v):
            return {t: (1+math.log(n)) * (1+math.log((1+len(corpus))/(1+df[t]))) for t, n in v.items()}
        qw = weights(q); qnorm = math.sqrt(sum(v*v for v in qw.values()))
        ranked = []
        excluded = set(exclude)
        for pos, (source, record, v) in enumerate(corpus):
            if source in excluded:
                continue
            shared = q.keys() & v.keys()
            # An ordinal alone is not evidence of a shared subject.
            if not (shared - {'@初次', '第一', '一次'}):
                continue
            w = weights(v)
            score = sum(qw[t]*w[t] for t in shared) / max(1e-12, qnorm*math.sqrt(sum(x*x for x in w.values())))
            iv=weights(vector(subject_query(record['input'])))
            input_score=sum(qw[t]*iv[t] for t in q.keys() & iv.keys())/max(1e-12,qnorm*math.sqrt(sum(x*x for x in iv.values())))
            original=not is_question(record['input'])
            score=max(score,input_score*1.4) if original else score*.45
            # Evidence fallback is gated to a substantive original statement.
            lexical=len((q.keys() & iv.keys())-{'回忆','出发','之前','当时','评价'})
            topic_match=(q.keys() & iv.keys()) & {'@暗号','@餐食','@记忆标记'}
            if score >= threshold or original and (input_score>=.07 and lexical>=2 or topic_match):
                ranked.append((score+(.2 if original else 0), pos, record))
        ranked.sort(key=lambda x: (-x[0], -x[1]))
        # "First time" asks for chronology within relevant evidence, not recency.
        if '@初次' in q and ranked:
            explicit = [r for r in ranked if '@初次' in vector(r[2]['input']+' '+r[2]['reply'])]
            ranked = sorted(explicit or ranked, key=lambda x: x[1])
        elif any(t in query for t in ('出发前','最初','原来','临时记忆标记')):
            ranked.sort(key=lambda x:(is_question(x[2]['input']),-x[0],x[1]))
        return [{**r, 'score': round(score, 4), 'retrieval': 'local_sparse_tfidf_original_v2'} for score, _, r in ranked[:k]]
