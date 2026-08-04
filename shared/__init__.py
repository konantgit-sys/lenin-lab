# Shared modules for all 10 products

from .lenin_core import (
    get_faiss, get_db, faiss_search, fts5_search,
    get_paragraph, get_stats, load_cache, random_quote
)
from .utils import (
    ttl_cache, load_json, save_json, format_quote, year_color
)
