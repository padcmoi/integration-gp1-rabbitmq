"""Shared Django bootstrap for consumers that read the application's data."""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

_ready = False


def setup_django():
    global _ready
    if _ready:
        from django.db import close_old_connections

        # The bus lives outside Django's request cycle, so nothing recycles a
        # connection MySQL has dropped during an idle spell; without this, the
        # first query after that idle dies with InterfaceError (0, '').
        close_old_connections()
        return
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from dotenv import load_dotenv

    # The application's own .env, loaded explicitly: the bus runs from
    # rabbit_bus/ and a bare load_dotenv() would find the bus one instead.
    load_dotenv(REPO_ROOT / ".env")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    import django

    django.setup()
    _ready = True


def json_safe(row):
    return {key: value if isinstance(value, (str, int, float, bool)) or value is None else str(value) for key, value in row.items()}
