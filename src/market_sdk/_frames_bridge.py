"""Lazy, type-erased lookup of :mod:`market_sdk.frames` functions for non-frames modules."""

from __future__ import annotations

from typing import Any, Literal


def frames_func(name: Literal["to_arrow", "to_pandas", "to_polars"]) -> Any:
    from market_sdk import frames

    return getattr(frames, name)


__all__ = ["frames_func"]
