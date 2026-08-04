#!/usr/bin/env python3
"""
Lenin Book — Test Pipeline Runner v2.7
Reads test_config.yaml, runs all phases, produces report.
"""
import json, re, requests, sys, time, os, subprocess
from datetime import datetime

BASE = "https://lenin-book.v2.site"
PASS, FAIL, WARN = 0, 0, 0

def green(s): return f"\033[92m{s}\033[0m"
def red(s): return f"\033[91m{s}\033[0m"
def yellow(s): return f"\033[93m{s}\033[0m"
def bold(s): return f"\033[1m{s}\033[0m"

def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        print(f"  {green('✅')} {name}{' — ' + detail if detail else ''}")
        PASS += 1
    else:
        print(f"  {red('❌')} {name}{' — ' + detail if detail else ''}")
        FAIL += 1

def check_warn(name, ok, detail=""):
    global PASS, WARN
    if ok:
        print(f"  {green('✅')} {name}{' — ' + detail if detail else ''}")
        PASS += 1
    else:
        print(f"  {yellow('⚠️ ')} {name}{' — ' + detail if detail else ''}")
        WARN += 1

def api_get(path, timeout=15):
    url = BASE + path
    try:
        r = requests.get(url, timeout=timeout)
        return r.status_code, r.json() if r.headers.get('content-type','').startswith('application/json') else r.text
    except Exception as e:
        return 0, str(e)

# ═══════════════════════════════════════
print(bold("=" * 55))
print(bold("  LENIN BOOK — TEST PIPELINE v2.7"))
print(bold(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
print(bold("=" * 55))

# ═══════ PHASE 1: BACKEND ═══════
print(f"\n{bold('🔧 PHASE 1: BACKEND HEALTH')}")
try:
    out = subprocess.check_output(['pgrep', '-f', 'api_v2.*9770'], text=True).strip()
    pids = [p for p in out.split('\n') if p]
    check("Process running", len(pids) > 0, f"PID(s): {', '.join(pids[:3])}")
except:
    check("Process running", False, "api_v2.py not found")

try:
    health = subprocess.check_output(
        ['curl', '-s', '--max-time', '3', 'http://localhost:9770/api/health'],
        text=True)
    ok = '"status":"ok"' in health
    check("Port 9770 listening", ok, "local health check")
except:
    check("Port 9770 listening", False, "could not check local")

check("start.sh exists", os.path.exists('/home/agent/data/sites/lenin-book/start.sh'))

# ═══════ PHASE 2: API ═══════
print(f"\n{bold('🔌 PHASE 2: API ENDPOINTS')}")

api_tests = {
    "core": [
        ("health", "/api/health", lambda r: r[0]==200 and r[1].get("status")=="ok"),
        ("stats", "/api/stats", lambda r: r[0]==200 and r[1].get("total_engines")==9),
        ("summary", "/api/summary", lambda r: r[0]==200 and "engines" in r[1]),
        ("search", "/api/search?q=%D1%80%D0%B5%D0%B2%D0%BE%D0%BB%D1%8E%D1%86%D0%B8%D1%8F",
         lambda r: r[0]==200 and r[1].get("engines_hit",0)>0),
        ("timeline", "/api/timeline?year=1917",
         lambda r: r[0]==200 and ("events" in r[1] or "paragraphs" in r[1])),
        ("rhetoric", "/api/rhetoric", lambda r: r[0]==200 and r[1] is not None),
        ("concepts", "/api/concepts", lambda r: r[0]==200 and "nodes" in r[1]),
        ("opponents", "/api/opponents", lambda r: r[0]==200 and ("opponents" in r[1] or "total" in r[1])),
        ("entropy", "/api/entropy", lambda r: r[0]==200 and len(r[1].get("years",{}))>0),
        ("phantoms", "/api/phantoms", lambda r: r[0]==200 and r[1].get("total",0)>0),
        ("tomography", "/api/tomography", lambda r: r[0]==200 and r[1] is not None),
        ("legend", "/api/legend", lambda r: r[0]==200 and r[1] is not None),
        ("quote", "/api/quote", lambda r: r[0]==200 and r[1] is not None),
        ("dashboard", "/api/dashboard", lambda r: r[0]==200 and r[1].get("engines_count")==9),
    ],
    "oracle": [
        ("oracle/stats", "/api/oracle/stats", lambda r: r[0]==200 and "total_paragraphs" in r[1]),
        ("oracle/search", "/api/oracle/search?q=imperialism", lambda r: r[0]==200 and r[1] is not None),
        ("oracle/random", "/api/oracle/random", lambda r: r[0]==200 and ("text" in r[1] or "quote" in r[1])),
    ],
    "products": [
        ("papers/concepts", "/api/papers/concepts", lambda r: r[0]==200 and r[1] is not None),
        ("comparator/topics", "/api/comparator/topics", lambda r: r[0]==200 and isinstance(r[1], list)),
        ("comparator/compare", "/api/comparator/compare?topic=%D0%B8%D0%BC%D0%BF%D0%B5%D1%80%D0%B8%D0%B0%D0%BB%D0%B8%D0%B7%D0%BC",
         lambda r: r[0]==200 and r[1] is not None),
        ("contradictions", "/api/contradictions", lambda r: r[0]==200 and r[1] is not None),
        ("shadow", "/api/shadow", lambda r: r[0]==200 and r[1] is not None),
        ("twin", "/api/twin", lambda r: r[0]==200 and r[1] is not None),
        ("style/tones", "/api/style/tones", lambda r: r[0]==200 and r[1] is not None),
        ("passport", "/api/passport", lambda r: r[0]==200 and (isinstance(r[1], dict) and "stats" in r[1])),
    ],
    "legacy": [
        ("v1/health", "/api/v1/health", lambda r: r[0]==200 and r[1].get("status")=="ok"),
        ("v1/stats", "/api/v1/stats", lambda r: r[0]==200 and r[1] is not None),
    ],
}

for group, tests in api_tests.items():
    print(f"\n  {bold(group.upper())}:")
    for name, path, fn in tests:
        result = api_get(path)
        ok = fn(result)
        code = result[0]
        size = len(json.dumps(result[1])) if isinstance(result[1], (dict,list)) else len(str(result[1]))
        check(name, ok, f"HTTP {code}, {size:,} bytes")

# ═══════ PHASE 3: PAGES ═══════
print(f"\n{bold('📄 PHASE 3: STATIC PAGES')}")

pages = [
    ("Главная", "/"),
    ("Dashboard Pro", "/dashboard/"),
    ("Oracle", "/oracle/"),
    ("Digital Twin", "/twin/"),
    ("White Papers", "/papers/"),
    ("Contradictions", "/contradictions/"),
    ("Shadow", "/shadow/"),
    ("Knowledge Graph", "/graph/"),
    ("Comparator", "/comparator/"),
    ("Style Mimic", "/style/"),
    ("Obsidian", "/obsidian/"),
]

for name, path in pages:
    try:
        r = requests.get(BASE + path, timeout=10)
        html_ok = "<!doctype html>" in r.text[:200].lower()
        size = len(r.content)
        ct = r.headers.get('content-type','')
        check(name, r.status_code==200 and html_ok, f"{size:,} bytes, {ct}")
    except Exception as e:
        check(name, False, str(e)[:60])

# ═══════ PHASE 4: FRONTEND ═══════
print(f"\n{bold('🎨 PHASE 4: FRONTEND FEATURES')}")

try:
    r = requests.get(BASE + "/", timeout=10)
    r.encoding = 'utf-8'  # Force UTF-8 — server doesn't send charset header
    html = r.text
except:
    html = ""

frontend_checks = [
    ("Tab panels (≥20)", len(re.findall(r'id="panel-\d+"', html)) >= 20,
     "found " + str(len(re.findall(r'id="panel-\d+"', html)))),
    ("SVG icons (≥25)", len(re.findall(r'<svg[^>]*>', html)) >= 25,
     f"found {len(re.findall(r'<svg[^>]*>', html))}"),
    ("i18n keys (≥60)", len(re.findall(r'data-i18n=', html)) >= 60,
     f"found {len(re.findall(r'data-i18n=', html))}"),
    ("CSS classes", '.c-muted' in html or '.c-accent' in html, ""),
    ("ARIA labels", 'aria-label=' in html, ""),
    ("Skip link", 'skip-link' in html, ""),
    ("Language toggle", 'lang-toggle' in html, ""),
    ("Theme toggle", 'toggleTheme' in html or 'theme-toggle' in html, ""),
    ("Search input", 'search-input' in html, ""),
    ("Tab system JS", 'switchTab' in html, ""),
    ("Canvas FX", '<canvas' in html, ""),
    ("OG meta tags", 'og:' in html.lower(), ""),
    ("Favicon SVG", 'favicon' in html.lower(), ""),
    ("Footer", '<footer' in html, ""),
    ("Counter/visits", 'counter' in html.lower() or 'visits' in html.lower(), ""),
    ("Instruction panel", 'Инструкция' in html or 'instruction' in html.lower(), ""),
    ("About page", 'О проекте' in html, ""),
]

for name, ok, detail in frontend_checks:
    check(name, ok, detail)

# Mobile breakpoints
print(f"\n  {bold('Mobile:')}")
for bp in ['1024', '768', '480']:
    ok = bool(re.search(rf'@media[^{{]*{bp}', html))
    check(f"Breakpoint {bp}px", ok)

# ═══════ PHASE 5: OPS ═══════
print(f"\n{bold('⚡ PHASE 5: PERFORMANCE & SECURITY')}")

try:
    # TTFB via curl
    out = subprocess.check_output(
        ['curl', '-so', '/dev/null', '-w', '%{time_starttransfer}', BASE + '/'],
        text=True, timeout=10)
    ttfb = float(out.strip()) * 1000
    check_warn("TTFB < 500ms", ttfb < 500, f"{ttfb:.0f} ms")
except:
    check("TTFB", False, "could not measure")

try:
    r = requests.get(BASE + "/", timeout=10)
    size_kb = len(r.content) / 1024
    check_warn("Page size < 150KB", size_kb < 150, f"{size_kb:.0f} KB")
    check("gzip enabled", r.headers.get('content-encoding') == 'gzip', "")
    check("X-Frame-Options", r.headers.get('x-frame-options') == 'SAMEORIGIN',
          r.headers.get('x-frame-options','?'))
    check("X-Content-Type-Options", 'nosniff' in r.headers.get('x-content-type-options',''), "")
    check("Referrer-Policy", bool(r.headers.get('referrer-policy')),
          r.headers.get('referrer-policy','?'))
except:
    check("Headers check", False, "request failed")

# TLS
try:
    out = subprocess.check_output(
        "curl -svI https://lenin-book.v2.site/ 2>&1 | grep -E 'TLS|expire'",
        shell=True, text=True, timeout=10)
    tls_ok = 'TLSv1.3' in out
    check("TLS 1.3", tls_ok)
    for line in out.split('\n'):
        if 'expire' in line.lower():
            print(f"    ↳ {line.strip()}")
except:
    check("TLS check", False, "could not check")

# ═══════ SUMMARY ═══════
print(f"\n{bold('=' * 55)}")
total = PASS + FAIL + WARN
pct = (PASS / total * 100) if total else 0
print(f"  TOTAL: {total} checks")
print(f"  {green(f'PASS: {PASS}')}  {red(f'FAIL: {FAIL}')}  {yellow(f'WARN: {WARN}')}")
print(f"  Score: {pct:.0f}%")
if FAIL == 0 and WARN == 0:
    print(f"  {green('✅ ALL CHECKS PASSED')}")
elif FAIL == 0:
    print(f"  {yellow('⚠️  ALL CRITICAL OK — warnings only')}")
else:
    print(f"  {red('❌ FAILURES DETECTED — fix required')}")
print(bold("=" * 55))

# Save report
report = {
    "timestamp": datetime.now().isoformat(),
    "total": total,
    "pass": PASS,
    "fail": FAIL,
    "warn": WARN,
    "score_pct": round(pct, 1),
}
report_path = '/home/agent/data/sites/lenin-book/test_report.json'
with open(report_path, 'w') as f:
    json.dump(report, f, indent=2)
print(f"\n  Report saved: {report_path}")
