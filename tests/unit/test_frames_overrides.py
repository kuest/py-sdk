"""Tests for the override registry."""

# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownParameterType=false

from __future__ import annotations

from typing import Any

import pyarrow as pa
import pytest

from market_sdk.frames._overrides import (
    clear_overrides,
    lookup_override,
    register_override,
    registered_types,
)
from market_sdk.models import OrderBook


@pytest.fixture(autouse=True)
def _restore_default_overrides():  # pyright: ignore[reportUnusedFunction] # noqa: ANN202
    """The OrderBook built-in override is registered at import time; restore it after each test."""
    import market_sdk.frames._builtin_overrides  # noqa: F401  # pyright: ignore[reportUnusedImport]

    yield

    clear_overrides()
    import importlib

    import market_sdk.frames._builtin_overrides as bo

    importlib.reload(bo)


def test_register_and_lookup() -> None:
    class _Custom:
        pass

    @register_override(_Custom)
    def _convert(value: Any) -> pa.Table:
        return pa.table({"marker": ["custom"]})

    assert lookup_override(_Custom) is _convert
    assert _Custom in registered_types()


def test_lookup_walks_mro_so_subclasses_inherit() -> None:
    class _Base:
        pass

    class _Sub(_Base):
        pass

    @register_override(_Base)
    def _convert(value: Any) -> pa.Table:
        return pa.table({"x": [1]})

    assert lookup_override(_Sub) is _convert


def test_lookup_returns_none_for_unregistered_type() -> None:
    class _NotRegistered:
        pass

    assert lookup_override(_NotRegistered) is None


def test_clear_overrides_removes_all() -> None:
    class _Tmp:
        pass

    @register_override(_Tmp)
    def _convert(value: Any) -> pa.Table:
        return pa.table({})

    assert lookup_override(_Tmp) is _convert
    clear_overrides()
    assert lookup_override(_Tmp) is None


def test_orderbook_override_is_registered_by_default() -> None:
    import market_sdk.frames  # noqa: F401  # pyright: ignore[reportUnusedImport]

    assert lookup_override(OrderBook) is not None
