"""
Pytest configuration for Lenin-Book.

Auto-skips tests that require the full corpus database when it is not
available (e.g. CI runners). Local runs with a real DB execute the full suite
(100/100 tests).

Which tests are skipped without the corpus:
  - engines that open sqlite directly (test_01/03/04/07/08/09)
  - engine_05 (timemachine) — requires DB, no cache fallback
  - API contract tests (test_10/11) — assert corpus-level invariants
    (169,067 paragraphs, quotes, timeline) that only hold with the real DB.
"""

import os

import pytest

_DB_MARKERS = ("lenin.db", "LENIN_DB", "sqlite3")
_DB_ONLY_FILES = (
    "test_05_timemachine.py",
    "test_10_master.py",
    "test_11_api_v1.py",
)


def _requires_db(item) -> bool:
    path = item.fspath.strpath
    if not path.endswith(".py"):
        return False
    if path.rsplit("/", 1)[-1] in _DB_ONLY_FILES:
        return True
    try:
        with open(path, encoding="utf-8") as fh:
            source = fh.read()
    except OSError:
        return False
    return any(m in source for m in _DB_MARKERS)


def pytest_collection_modifyitems(config, items):  # noqa: ARG001
    db_path = os.environ.get("LENIN_DB", "data/lenin.db")
    if os.path.exists(db_path):
        return  # full corpus available — run everything
    for item in items:
        if _requires_db(item):
            item.add_marker(
                pytest.mark.skip(reason="corpus DB not available in this environment")
            )
