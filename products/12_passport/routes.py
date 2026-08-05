"""Passport routes — Product #12."""
import sys, json
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse

SITE_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SITE_ROOT))

from shared.lenin_core import logger

router = APIRouter(tags=["Passport"])

# Cached passport data
_PASSPORT_CACHE = None

def _load_passport_cache():
    global _PASSPORT_CACHE
    if _PASSPORT_CACHE is None:
        cache_path = SITE_ROOT / "passport_cache.json"
        if cache_path.exists():
            _PASSPORT_CACHE = json.loads(cache_path.read_text())
        else:
            _PASSPORT_CACHE = []
    return _PASSPORT_CACHE

@router.get("/passport")
@router.get("/passport/")
async def passport_page():
    return FileResponse(str(SITE_ROOT / "products" / "12_passport" / "index.html"))

@router.get("/api/passport")
def passport():
    """Stylometric passport — text DNA by year. Served from cache."""
    return {"stats": _load_passport_cache()}
