"""Environment helpers for the examples.

The SDK does not load `.env` at runtime, so examples read credentials straight
from the environment. Export them in your shell (or `source` a `.env`).
"""

from __future__ import annotations

import os


def require_env(name: str) -> str:
    """Return the environment variable, or exit with a clear message if unset."""
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"{name} is required — set it in your environment to run this example.")
    return value
