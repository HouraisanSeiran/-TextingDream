from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=root/'app/static/app.js'
s=p.read_text(encoding='utf-8')
edits=[
 ('function prefs(p){', 'function prefs(p){fillStageSettings(p);'),
 ("{recall_enabled:$('recall-enabled').checked", "{...stageSettings(),recall_enabled:$('recall-enabled').checked"),
 ("$('trace-list').replaceChildren(...filtered.map", "showCacheSummary(filtered);$('trace-list').replaceChildren(...filtered.map"),
 ("usage:traceRecord.usage,http_status:", "usage:traceRecord.usage,cache:traceRecord.cache,context_stats:traceRecord.context_stats,http_status:"),
 ("t.elapsed_ms+'ms'", "t.elapsed_ms+'ms'+(t.cache?.reported?' · 命中 '+(100*(t.cache.hit_rate||0)).toFixed(1)+'% · 未命中 '+t.cache.miss_tokens:' · 缓存用量未知')")
]
for old,new in edits:
    if new in s:continue
    if old not in s:raise ValueError('UI anchor missing')
    s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
