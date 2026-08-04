"""
Shared utilities for all 10 products.
"""

import json, time, os
from functools import wraps

CACHE_DIR = None

def set_cache_dir(d: str):
    global CACHE_DIR
    CACHE_DIR = d

def ttl_cache(seconds: int = 300):
    """Simple TTL cache decorator."""
    def decorator(fn):
        cache = {}
        @wraps(fn)
        def wrapper(*args, **kwargs):
            key = f"{fn.__name__}:{args}:{kwargs}"
            if key in cache and time.time() - cache[key]['ts'] < seconds:
                return cache[key]['val']
            result = fn(*args, **kwargs)
            cache[key] = {'val': result, 'ts': time.time()}
            return result
        return wrapper
    return decorator

def load_json(path: str) -> dict:
    with open(path) as f:
        return json.load(f)

def save_json(path: str, data: dict):
    with open(path, 'w') as f:
        json.dump(data, f, ensure_ascii=False)

def format_quote(text: str, max_len: int = 250) -> str:
    """Truncate quote with ellipsis."""
    if len(text) <= max_len:
        return text
    # Try to break at sentence end
    for sep in ['. ', '! ', '? ']:
        idx = text.rfind(sep, 0, max_len)
        if idx > max_len * 0.6:
            return text[:idx + 1] + '...'
    return text[:max_len] + '...'

def year_color(year: int, years: list = None) -> str:
    """Color gradient from blue (early) to red (late)."""
    if years is None:
        years = [1893, 1895, 1898, 1899, 1901, 1902, 1903, 1905, 1906, 1907,
                 1908, 1909, 1910, 1911, 1912, 1913, 1914, 1915, 1916, 1917,
                 1918, 1919, 1920, 1921, 1922]
    if year not in years:
        return '#555'
    t = years.index(year) / (len(years) - 1)
    r, g, b = int(40 + t*200), int(80 + (1-abs(t-0.5)*2)*150), int(200 - t*180)
    return f"rgb({r},{g},{b})"
