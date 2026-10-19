"""Deterministic append-only history stages, derived from committed turns.

No extra model calls, no hidden durable state: rollback derives the old stage.
"""
import json


def stage_history(turns, preferences):
    if preferences.get('history_strategy', 'staged') == 'sliding':
        return turns[-preferences['history_turns']:], '', {'strategy':'sliding','start':max(0,len(turns)-preferences['history_turns'])}
    limit=preferences.get('stage_turns',16)
    char_limit=min(preferences.get('stage_chars',6000), max(1200,preferences['context_chars']//3))
    start=0; chars=0
    for i,turn in enumerate(turns):
        size=len(json.dumps(turn,ensure_ascii=False,separators=(',',':')))
        if i>start and (i-start>=limit or chars+size>char_limit):
            start=i;chars=0
        chars+=size
    # Fixed, explicitly historical excerpt, not an inferred objective summary.
    # Keep complete short exchanges only; never cut off a negation mid-sentence.
    summary=[]
    for turn in reversed(turns[max(0,start-2):start]):
        if len(json.dumps(summary+[turn],ensure_ascii=False))<=1000:summary.insert(0,turn)
    text=('上一阶段原文摘录（可能含误解，不覆盖当前状态）：'+json.dumps(summary,ensure_ascii=False,separators=(',',':'))) if summary else ''
    return turns[start:],text,{'strategy':'staged','start':start,'char_limit':char_limit,'turn_limit':limit}
