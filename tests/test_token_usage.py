from datetime import datetime, timedelta, timezone

from app.token_usage import summarize


def test_usage_rate_keeps_unknowns_and_groups_scopes():
    now = datetime(2026, 10, 31, 12, tzinfo=timezone.utc)
    traces = [
        {'scope': 'surface', 'status': 'success', 'created': (now - timedelta(hours=2)).isoformat(),
         'usage': {'prompt_tokens': 1000, 'completion_tokens': 200, 'prompt_cache_hit_tokens': 700}},
        {'scope': 'surface', 'status': 'offline', 'created': (now - timedelta(hours=1)).isoformat(),
         'usage': {'calls': 0}},
        {'scope': 'inner', 'status': 'success', 'created': now.isoformat(),
         'usage': {'prompt_tokens': 500, 'completion_tokens': 100}},
    ]
    report = summarize(traces, hours=24, now=now)
    assert report['overall']['calls'] == 3
    assert report['overall']['telemetry_calls'] == 2
    assert report['overall']['unknown_usage_calls'] == 1
    assert report['overall']['input_tokens'] == 1500
    assert report['overall']['output_tokens'] == 300
    assert report['overall']['cache_hit_rate'] == 0.7
    assert report['by_scope']['surface']['unknown_usage_calls'] == 1


def test_empty_usage_does_not_claim_zero_consumption():
    report = summarize([{'scope': 'surface', 'created': '2026-10-31T12:00:00+00:00', 'usage': {}}], hours=24)
    assert report['overall']['input_tokens'] is None
    assert report['overall']['output_tokens'] is None
    assert report['overall']['total_tokens'] is None
