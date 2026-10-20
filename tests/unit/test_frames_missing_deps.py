"""Tests for graceful failure when optional dependencies are missing."""

# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownParameterType=false

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import BaseModel

from market_sdk.frames import (
    MissingOptionalDependencyError,
    to_arrow,
    to_pandas,
    to_polars,
)


class _Tiny(BaseModel):
    n: int
    v: Decimal


def _raise_missing(name: str):  # noqa: ANN202
    def go(*_args: object, **_kwargs: object) -> object:
        raise MissingOptionalDependencyError(f"market_sdk.frames test stub: {name} unavailable")

    return go


def test_error_class_is_importerror_subclass() -> None:
    """Existing ``except ImportError:`` clauses must still catch it."""
    assert issubclass(MissingOptionalDependencyError, ImportError)


def test_to_arrow_raises_when_pyarrow_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "market_sdk.frames._arrow._require_pyarrow",
        _raise_missing("pyarrow"),
    )
    with pytest.raises(MissingOptionalDependencyError, match="pyarrow"):
        to_arrow(_Tiny(n=1, v=Decimal("1")))


def test_to_pandas_raises_when_pandas_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "market_sdk.frames._pandas._require_pandas_stack",
        _raise_missing("pandas"),
    )
    with pytest.raises(MissingOptionalDependencyError, match="pandas"):
        to_pandas(_Tiny(n=1, v=Decimal("1")))


def test_to_polars_raises_when_polars_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "market_sdk.frames._polars._require_polars",
        _raise_missing("polars"),
    )
    with pytest.raises(MissingOptionalDependencyError, match="polars"):
        to_polars(_Tiny(n=1, v=Decimal("1")))


def test_error_message_includes_install_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "market_sdk.frames._pandas._require_pandas_stack",
        lambda: (_ for _ in ()).throw(
            MissingOptionalDependencyError(
                "market_sdk.frames.to_pandas() requires pandas. Install via "
                "`pip install kuest-sdk[pandas]`."
            )
        ),
    )
    with pytest.raises(MissingOptionalDependencyError, match=r"kuest-sdk\[pandas\]"):
        to_pandas(_Tiny(n=1, v=Decimal("1")))


def test_module_imports_without_any_extras_installed() -> None:
    """``from market_sdk.frames import to_pandas`` must succeed with no extras installed."""
    import market_sdk.frames as f

    assert hasattr(f, "to_arrow")
    assert hasattr(f, "to_pandas")
    assert hasattr(f, "to_polars")
    assert hasattr(f, "MissingOptionalDependencyError")
