"""
Pytest configuration for Lenin-Book.

Auto-skips tests that require the corpus database when it is not available
(e.g. in CI runners). Local runs with a real DB execute the full suite.
"""

import os

import pytest

_DB_MARKERS = ("lenin.db", "LENIN_DB", "sqlite3")


def _requires_db(item) -> bool:
    path = item.fspath.strpath
    if not path.endswith(".py"):
        return False
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
