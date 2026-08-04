"""
Lenin-Book Analytics Engine
Parses api_access.log and returns visitor analytics.
No external dependencies — pure Python stdlib.
"""
import re
import json
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime, timedelta

LOG_PATH = Path("/home/agent/data/sites/lenin-book/api_access.log")

def parse_log(days: int = 30):
    """Parse access log, return structured data."""
    if not LOG_PATH.exists():
        return {"error": "No access log yet"}

    cutoff = datetime.now() - timedelta(days=days)
    entries = []

    with open(LOG_PATH) as f:
        for line in f:
            # Format: 2026-08-04 19:34:46,946 [TAG] IP METHOD path ...
            m = re.match(r'(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}),\d+ \[(\w+-\w+|\w+)\] (\S+) (\S+) (.+)', line)
            if not m:
                continue
            date_str, time_str, tag, ip, method, rest = m.groups()
            try:
                dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue

            if dt < cutoff:
                continue

            path = method  # rest may contain just path or 'GET /path'
            if ' ' in rest:
                parts = rest.split()
                if len(parts) >= 1:
                    path = parts[0] if parts[0] in ('GET','POST','PUT','DELETE') else method
                    path = f"{path} {parts[1]}" if len(parts) >= 2 else rest

            entries.append({
                "date": date_str,
                "time": time_str,
                "tag": tag,
                "ip": ip,
                "path": rest.split()[0] if rest and ' ' in rest else rest[:60]
            })

    return _compute_stats(entries, days)

def _compute_stats(entries: list, days: int):
    """Compute analytics from parsed entries."""
    if not entries:
        return {"error": "No entries in date range"}

    # Unique IPs
    all_ips = set(e["ip"] for e in entries)
    api_ips = set(e["ip"] for e in entries if "[API]" in e.get("tag", ""))
    public_ips = set(e["ip"] for e in entries if "[PUBLIC]" in e.get("tag", ""))

    # Daily breakdown
    daily = defaultdict(lambda: {"total": 0, "api": 0, "public": 0, "ips": set()})
    for e in entries:
        day = e["date"]
        daily[day]["total"] += 1
        daily[day]["ips"].add(e["ip"])
        if "[API]" in e.get("tag", ""):
            daily[day]["api"] += 1
        else:
            daily[day]["public"] += 1

    daily_json = {}
    for day in sorted(daily.keys()):
        daily_json[day] = {
            "total": daily[day]["total"],
            "api": daily[day]["api"],
            "public": daily[day]["public"],
            "unique_ips": len(daily[day]["ips"])
        }

    # Top paths
    path_counter = Counter()
    for e in entries:
        p = e["path"]
        if p.startswith("/api/"):
            path_counter[p] += 1

    top_paths = [{"path": p, "hits": c} for p, c in path_counter.most_common(20)]

    # Top API keys (masked)
    key_counter = Counter()
    for e in entries:
        if "key=..." in e.get("tag", ""):
            rest = e.get("tag", "")
            m = re.search(r'key=\.\.\.(\w+)', rest)
            if m:
                key_counter[f"...{m.group(1)}"] += 1

    top_keys = [{"key_mask": k, "requests": c} for k, c in key_counter.most_common(10)]

    # Auth failures
    auth_fails = sum(1 for e in entries if "AUTH-REJECT" in e.get("tag", ""))
    rate_limits = sum(1 for e in entries if "RATE-LIMIT" in e.get("tag", ""))

    return {
        "period_days": days,
        "total_requests": len(entries),
        "unique_ips": len(all_ips),
        "unique_api_users": len(api_ips),
        "unique_public_visitors": len(public_ips),
        "auth_failures": auth_fails,
        "rate_limits_hit": rate_limits,
        "daily": daily_json,
        "top_api_paths": top_paths,
        "top_api_keys": top_keys,
        "generated_at": datetime.now().isoformat()
    }


def get_summary():
    """Quick summary for dashboard widget."""
    if not LOG_PATH.exists():
        return {"total": 0, "today": 0, "unique_today": 0}

    today = datetime.now().strftime("%Y-%m-%d")
    total_lines = 0
    today_lines = 0
    today_ips = set()

    with open(LOG_PATH) as f:
        for line in f:
            total_lines += 1
            if line.startswith(today):
                today_lines += 1
                m = re.match(r'\S+ \S+ \S+ (\S+)', line)
                if m:
                    today_ips.add(m.group(1))

    return {
        "total_requests_all_time": total_lines,
        "today_requests": today_lines,
        "today_unique_ips": len(today_ips)
    }


if __name__ == "__main__":
    import sys
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    print(json.dumps(parse_log(days), indent=2, ensure_ascii=False))
