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
    assert report['overall']['calls'] == 2
    assert report['overall']['telemetry_calls'] == 2
    assert report['overall']['unknown_usage_calls'] == 0
    assert report['overall']['input_tokens'] == 1500
    assert report['overall']['output_tokens'] == 300
    assert report['overall']['cache_hit_rate'] == 0.7
    assert report['by_scope']['surface']['offline_traces'] == 1


def test_empty_usage_does_not_claim_zero_consumption():
    report = summarize([{'scope': 'surface', 'created': '2026-10-31T12:00:00+00:00', 'usage': {}}], hours=24)
    assert report['overall']['input_tokens'] is None
    assert report['overall']['output_tokens'] is None
    assert report['overall']['total_tokens'] is None


def test_window_rate_excludes_offline_and_reports_partial_coverage():
    now = datetime(2026, 11, 1, tzinfo=timezone.utc)
    rows = [
        {'created': now.isoformat(), 'status': 'success', 'usage': {'prompt_tokens': 1000}},
        {'created': now.isoformat(), 'status': 'success', 'usage': {'completion_tokens': 100}},
        {'created': now.isoformat(), 'status': 'offline', 'usage': {'calls': 0}},
        {'created': now.isoformat(), 'status': 'blocked', 'usage': {}},
    ]
    result = summarize(rows, hours=24, now=now)['overall']
    assert result['calls'] == 2
    assert result['input_tokens_per_hour'] == 41.7
    assert result['output_tokens_per_hour'] == 4.2
    assert result['input_usage_calls'] == result['output_usage_calls'] == 1
    assert result['offline_traces'] == result['blocked_traces'] == 1
    assert result['total_tokens'] is None


def test_single_call_rate_and_unspecified_window():
    now = datetime(2026, 11, 1, tzinfo=timezone.utc)
    trace = {'created': now.isoformat(), 'status': 'success', 'usage': {'prompt_tokens': 1000, 'completion_tokens': 100}}
    report = summarize([trace], hours=24, now=now)['overall']
    assert report['total_tokens_per_hour'] == 45.8
    assert report['calls_per_hour'] == 0.04
    assert summarize([trace], now=now)['overall']['calls_per_hour'] is None
