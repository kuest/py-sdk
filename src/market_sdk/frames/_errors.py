"""Errors raised by :mod:`market_sdk.frames`."""

from __future__ import annotations


class MissingOptionalDependencyError(ImportError):
    """An optional dependency required by a frames operation is not installed."""


__all__ = ["MissingOptionalDependencyError"]
