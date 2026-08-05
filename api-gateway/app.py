"""Lenin-Book API Gateway v1.1
Transparent proxy to internal API (port 9770) with auth + rate limiting.
"""
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx, sqlite3, hashlib, secrets, time, os

app = FastAPI(title="Lenin-Book API Gateway", version="1.1")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DB = os.path.expanduser('~/data/sites/api-lenin/keys.db')
UPSTREAM = 'http://localhost:9770'

TIERS = {'free': {'daily': 100, 'name': 'Free'}, 'basic': {'daily': 1000, 'name': 'Basic'}, 'pro': {'daily': 999999, 'name': 'Pro'}}

def get_conn():
    conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row; return conn

def init_db():
    conn = get_conn()
    conn.execute('''CREATE TABLE IF NOT EXISTS api_keys (
        key_hash TEXT PRIMARY KEY, key_prefix TEXT, tier TEXT DEFAULT 'free',
        created_at TEXT DEFAULT (datetime('now')), owner TEXT DEFAULT '', active INTEGER DEFAULT 1)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS usage_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, key_prefix TEXT, endpoint TEXT,
        timestamp TEXT DEFAULT (datetime('now')) )''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_usage_ts ON usage_log(key_prefix, timestamp)')
    if conn.execute('SELECT COUNT(*) FROM api_keys').fetchone()[0] == 0:
        key = 'lb-' + secrets.token_hex(16)
        kh = hashlib.sha256(key.encode()).hexdigest()
        conn.execute('INSERT INTO api_keys (key_hash, key_prefix, tier, owner) VALUES (?,?,?,?)', (kh, key[:8], 'free', 'default'))
        conn.commit()
        print(f'SEED_KEY={key}')
    conn.commit(); conn.close()

init_db()

async def check_auth(request: Request):
    path = request.url.path
    if path in ('/', '/health', '/docs', '/openapi.json', '/favicon.ico') or path.startswith('/keys'):
        return None
    api_key = request.headers.get('X-API-Key', '')
    if not api_key:
        raise HTTPException(401, detail='Missing X-API-Key header. Get key: POST /keys/generate')
    kh = hashlib.sha256(api_key.encode()).hexdigest()
    conn = get_conn()
    row = conn.execute('SELECT * FROM api_keys WHERE key_hash=? AND active=1', (kh,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(403, detail='Invalid API key')
    today = time.strftime('%Y-%m-%d')
    count = conn.execute("SELECT COUNT(*) FROM usage_log WHERE key_prefix=? AND timestamp LIKE ?", (row['key_prefix'], today + '%')).fetchone()[0]
    limit = TIERS.get(row['tier'], {}).get('daily', 100)
    if count >= limit:
        conn.close()
        raise HTTPException(429, detail=f'Rate limit exceeded: {limit}/day. Tier: {row["tier"]}')
    if path.startswith('/api'):
        conn.execute('INSERT INTO usage_log (key_prefix, endpoint) VALUES (?,?)', (row['key_prefix'], path))
        conn.commit()
    conn.close()
    return None

# ═══ PUBLIC ROUTES (before catch-all) ═══

@app.get("/")
async def root(request: Request):
    accept = request.headers.get('accept', '')
    if 'text/html' in accept:
        return FileResponse("/home/agent/data/sites/api-lenin/pricing.html", media_type="text/html")
    return {"service": "Lenin-Book API Gateway", "version": "1.1",
            "docs": "/docs", "pricing": "/pricing",
            "endpoints": {"generate_key": "POST /keys/generate?owner=name&tier=free",
            "list_keys": "GET /keys/list", "usage": "GET /keys/usage/{prefix}",
            "api_dashboard": "GET /api/dashboard", "api_oracle": "GET /api/oracle?q=",
            "api_comparator": "GET /api/comparator/topics", "api_shadow": "GET /api/shadow?word=",
            "api_passport": "GET /api/passport", "api_quotes": "GET /api/quotes"}}

@app.get("/health")
async def health():
    conn = get_conn()
    keys = conn.execute('SELECT COUNT(*) FROM api_keys WHERE active=1').fetchone()[0]
    today = time.strftime('%Y-%m-%d')
    usage = conn.execute("SELECT COUNT(*) FROM usage_log WHERE timestamp LIKE ?", (today+'%',)).fetchone()[0]
    conn.close()
    return {"status": "ok", "active_keys": keys, "usage_today": usage, "upstream": UPSTREAM}

@app.post("/keys/generate")
async def generate_key(owner: str = '', tier: str = 'free'):
    if tier not in TIERS:
        raise HTTPException(400, detail=f'Invalid tier: {list(TIERS.keys())}')
    key = 'lb-' + secrets.token_hex(16)
    kh = hashlib.sha256(key.encode()).hexdigest()
    conn = get_conn()
    conn.execute('INSERT INTO api_keys (key_hash, key_prefix, tier, owner) VALUES (?,?,?,?)', (kh, key[:8], tier, owner))
    conn.commit(); conn.close()
    return {"api_key": key, "prefix": key[:8], "tier": tier, "daily_limit": TIERS[tier]['daily']}

@app.get("/keys/list")
async def list_keys():
    conn = get_conn()
    rows = conn.execute('SELECT key_prefix, tier, owner, created_at, active FROM api_keys ORDER BY created_at DESC').fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.delete("/keys/revoke/{prefix}")
async def revoke_key(prefix: str):
    conn = get_conn()
    conn.execute('UPDATE api_keys SET active=0 WHERE key_prefix=?', (prefix,))
    changed = conn.total_changes
    conn.commit(); conn.close()
    if changed == 0: raise HTTPException(404, 'Key not found')
    return {"revoked": prefix}

@app.get("/keys/usage/{prefix}")
async def key_usage(prefix: str, days: int = 7):
    conn = get_conn()
    rows = conn.execute('''SELECT date(timestamp) as day, COUNT(*) as count
        FROM usage_log WHERE key_prefix=? AND timestamp >= date('now', ?)
        GROUP BY day ORDER BY day DESC''', (prefix, f'-{days} days')).fetchall()
    tier_row = conn.execute('SELECT tier FROM api_keys WHERE key_prefix=?', (prefix,)).fetchone()
    limit = TIERS.get(tier_row['tier'], {}).get('daily', 0) if tier_row else 0
    conn.close()
    return {"prefix": prefix, "tier": tier_row['tier'] if tier_row else '?',
            "daily_limit": limit, "usage": [dict(r) for r in rows]}


@app.get("/pricing")
async def pricing():
    return FileResponse("/home/agent/data/sites/api-lenin/pricing.html", media_type="text/html")

# ═══ CATCH-ALL PROXY (must be LAST) ═══

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"])
async def proxy(request: Request, path: str):
    # Auth check
    await check_auth(request)

    # Build upstream URL
    url = f"{UPSTREAM}/{path}"
    if request.url.query:
        url += f"?{request.url.query}"

    headers = dict(request.headers)
    headers.pop('host', None); headers.pop('x-api-key', None)
    body = await request.body() if request.method in ('POST', 'PUT', 'PATCH') else None

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            upstream_resp = await client.request(request.method, url, headers=headers, content=body)
            content = upstream_resp.content
            resp_headers = dict(upstream_resp.headers)
            resp_headers.pop('content-encoding', None)
            resp_headers.pop('transfer-encoding', None)
            return StreamingResponse(iter([content]), status_code=upstream_resp.status_code,
                                     headers=resp_headers, media_type=resp_headers.get('content-type', 'application/json'))
        except httpx.ConnectError:
            return JSONResponse({"error": "Upstream API is down"}, 502)
        except httpx.TimeoutException:
            return JSONResponse({"error": "Upstream timeout"}, 504)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=9880)
