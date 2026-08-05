"""Shadow routes — Product #11."""
import sys, json, time as _time
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse

SITE_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SITE_ROOT))

from shared.lenin_core import logger

router = APIRouter(tags=["Shadow"])

# Shadow cache
_shadow_cache = {"data": None, "time": 0, "ttl": 300}

@router.get("/shadow")
@router.get("/shadow/")
async def shadow_index():
    return FileResponse(str(SITE_ROOT / "products" / "11_shadow" / "index.html"))

@router.get("/api/shadow")
def shadow():
    """Shadow structure — word frequency drift. CACHED (5 min TTL)."""
    now = _time.time()
    if _shadow_cache["data"] is not None and (now - _shadow_cache["time"]) < _shadow_cache["ttl"]:
        return _shadow_cache["data"]

    try:
        from phase_c_engine import get_shadow_json
        result = get_shadow_json()
        resp = {"terms": result}
        _shadow_cache["data"] = resp
        _shadow_cache["time"] = now
        return resp
    except Exception as e:
        if _shadow_cache["data"] is not None:
            _shadow_cache["data"]["stale"] = True
            _shadow_cache["data"]["warning"] = f"Cache stale, refresh failed: {e}"
            return _shadow_cache["data"]
        logger.error(f"[shadow] {e}")
        return {"error": "internal error", "terms": []}
