"""Observed provider usage, never equate missing telemetry with zero misses."""
def cache_usage(usage):
    usage=usage or {}
    total=usage.get('prompt_tokens')
    hit=usage.get('prompt_cache_hit_tokens', (usage.get('prompt_tokens_details') or {}).get('cached_tokens'))
    miss=usage.get('prompt_cache_miss_tokens')
    if miss is None and isinstance(total,int) and isinstance(hit,int):
        miss=max(0,total-hit)
    valid=all(isinstance(x,int) and not isinstance(x,bool) and x>=0 for x in (total,hit,miss)) and total==hit+miss
    return {'input_tokens':total,'hit_tokens':hit if valid else None,'miss_tokens':miss if valid else None,
            'output_tokens':usage.get('completion_tokens'),
            'hit_rate':hit/total if valid and total else None,'reported':valid}


def context_stats(context):
    if not isinstance(context,dict):return {}
    import json
    history=context.get('history',[])
    return {'history_turns':len(history),'history_chars':len(json.dumps(history,ensure_ascii=False)),
            'has_stage_excerpt':bool(context.get('last_summary')),
            'recalled_turns':len(context.get('recalled_dialogue',[])),
            'context_chars':len(json.dumps(context,ensure_ascii=False))}
