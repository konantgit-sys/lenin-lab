"""
Test helper: loads cache files used by the API.
This bypasses heavy computation and tests what the API actually serves.
"""

import json
from pathlib import Path

SITE_DIR = Path(__file__).parent.parent
DATA_DIR = SITE_DIR


def load_concept_cache() -> dict:
    """Load concept graph cache (what /api/v1/concepts returns)."""
    path = DATA_DIR / "concept_cache.json"
    if not path.exists():
        raise FileNotFoundError(f"Cache not found: {path}")
    return json.loads(path.read_text())


def load_rhetoric_cache() -> dict:
    """Load rhetoric cache (what /api/v1/rhetoric returns)."""
    path = DATA_DIR / "rhetoric_data.json"
    if not path.exists():
        raise FileNotFoundError(f"Cache not found: {path}")
    return json.loads(path.read_text())


def load_entropy_cache() -> dict:
    """Load entropy cache."""
    path = DATA_DIR / "entropy_data.json"
    return json.loads(path.read_text()) if path.exists() else {}


def load_phantoms_cache() -> dict:
    """Load phantom opponents cache."""
    path = DATA_DIR / "phantom_opponents.json"
    return json.loads(path.read_text()) if path.exists() else {}


def load_tomography_cache() -> dict:
    """Load tomography cache."""
    path = DATA_DIR / "tomography_data.json"
    return json.loads(path.read_text()) if path.exists() else {}
