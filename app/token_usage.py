"""Observed model token usage, with explicit unknowns for providers without telemetry."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import mean

from .cache_metrics import cache_usage


def _time(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def _number(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _rates(rows, hours):
    seconds = hours * 3600 if hours is not None and hours > 0 else None
    offline = sum(row['status'] == 'offline' for row in rows)
    blocked = sum(row['status'] == 'blocked' for row in rows)
    rows = [row for row in rows if row['status'] not in ('offline', 'blocked')]
    observed = [row for row in rows if row["input_tokens"] is not None or row["output_tokens"] is not None]
    input_values = [row["input_tokens"] for row in rows if row["input_tokens"] is not None]
    output_values = [row["output_tokens"] for row in rows if row["output_tokens"] is not None]
    hit_values = [row["hit_tokens"] for row in rows if row["hit_tokens"] is not None]
    miss_values = [row["miss_tokens"] for row in rows if row["miss_tokens"] is not None]
    total_in = sum(input_values) if input_values else None
    total_out = sum(output_values) if output_values else None
    # Cache fields can be absent on a request even when prompt_tokens is present;
    # report the rate over the requests that actually reported cache accounting.
    total_hit = sum(hit_values) if hit_values else None
    total_miss = sum(miss_values) if miss_values else None
    total = total_in + total_out if rows and len(input_values) == len(rows) and len(output_values) == len(rows) else None
    return {
        "calls": len(rows), "telemetry_calls": len(observed),
        "offline_traces": offline, "blocked_traces": blocked,
        "input_usage_calls": len(input_values), "output_usage_calls": len(output_values),
        "unknown_usage_calls": len(rows) - len(observed),
        "input_tokens": total_in, "output_tokens": total_out, "total_tokens": total,
        "avg_input_tokens": round(mean(input_values), 1) if input_values else None,
        "avg_output_tokens": round(mean(output_values), 1) if output_values else None,
        "input_tokens_per_hour": round(total_in / (seconds / 3600), 1) if total_in is not None and seconds else None,
        "output_tokens_per_hour": round(total_out / (seconds / 3600), 1) if total_out is not None and seconds else None,
        "total_tokens_per_hour": round(total / (seconds / 3600), 1) if total is not None and seconds else None,
        "calls_per_hour": round(len(rows) / (seconds / 3600), 2) if seconds else None,
        "cache_hit_tokens": total_hit,
        "cache_miss_tokens": total_miss,
        "cache_hit_rate": round(total_hit / (total_hit + total_miss), 4) if total_hit is not None and total_miss is not None and total_hit + total_miss else None,
        "window_seconds": round(seconds, 1) if seconds else None,
    }


def summarize(traces, hours=None, now=None):
    """Aggregate stored traces. Missing provider usage remains unknown, never zero."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=hours) if hours is not None else None
    rows = []
    for trace in traces or []:
        created = _time(trace.get("created"))
        if cutoff and (created is None or created < cutoff or created > now):
            continue
        usage = trace.get("usage") or {}
        cache = cache_usage(usage)
        rows.append({"scope": trace.get("scope", "unknown"), "status": trace.get("status"),
                     "created": created, "input_tokens": _number(usage.get("prompt_tokens")),
                     "output_tokens": _number(usage.get("completion_tokens")),
                     "hit_tokens": cache["hit_tokens"], "miss_tokens": cache["miss_tokens"]})
    rows.sort(key=lambda row: row["created"] or datetime.min.replace(tzinfo=timezone.utc))
    first = next((row["created"] for row in rows if row["created"]), None)
    last = next((row["created"] for row in reversed(rows) if row["created"]), None)
    by_scope = {}
    for scope in sorted({row["scope"] for row in rows}):
        subset = [row for row in rows if row["scope"] == scope]
        by_scope[scope] = _rates(subset, hours)
    return {"window_hours": hours, "from": first.isoformat() if first else None,
            "to": last.isoformat() if last else None,
            "overall": _rates(rows, hours), "by_scope": by_scope,
            "note": "每小时为已报告用量除以所选窗口时长；覆盖不完整时仅反映已知用量。无明确窗口时速率未知。离线和未发送的记录不计入调用。"}
