"""Tests for the pandas adapter."""

# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownParameterType=false

from __future__ import annotations

from decimal import Decimal

import pandas as pd
import pyarrow as pa
import pytest
from pydantic import BaseModel

from market_sdk.frames import to_pandas


class _Trade(BaseModel):
    id: str
    price: Decimal
    size: Decimal


class _WithList(BaseModel):
    id: str
    children: tuple[dict[str, Decimal], ...] = ()


def test_default_decimal_mode_preserves_precision() -> None:
    trades = (
        _Trade(id="t1", price=Decimal("0.123456789012345678"), size=Decimal("1")),
        _Trade(id="t2", price=Decimal("0.987654321098765432"), size=Decimal("2")),
    )
    df = to_pandas(trades)
    assert isinstance(df["price"].dtype, pd.ArrowDtype)
    assert pa.types.is_decimal(df["price"].dtype.pyarrow_dtype)
    assert df["price"][0] == Decimal("0.123456789012345678")
    assert df["price"][1] == Decimal("0.987654321098765432")


def test_float_decimal_mode_casts_to_float64() -> None:
    trades = (_Trade(id="t1", price=Decimal("0.5"), size=Decimal("100")),)
    df = to_pandas(trades, decimal="float")
    assert df["price"].dtype == "float64"
    assert df["size"].dtype == "float64"
    assert df["price"][0] == pytest.approx(0.5)


def test_float_mode_loses_precision_predictably() -> None:
    """float64 holds ~15-17 sig digits, so opt-in precision loss is the whole point."""
    high_precision = Decimal("0.123456789012345678")
    trade = _Trade(id="t", price=high_precision, size=Decimal("1"))
    df = to_pandas(trade, decimal="float")
    assert df["price"][0] != float(high_precision) or float(high_precision) != float(
        str(high_precision)
    )


def test_invalid_decimal_mode_raises_typeerror() -> None:
    with pytest.raises(TypeError, match="decimal must be"):
        to_pandas(_Trade(id="t", price=Decimal("1"), size=Decimal("1")), decimal="wrong")  # type: ignore[arg-type]


def test_single_model_yields_one_row() -> None:
    m = _Trade(id="t", price=Decimal("0.5"), size=Decimal("100"))
    df = to_pandas(m)
    assert len(df) == 1
    assert list(df.columns) == ["id", "price", "size"]


def test_empty_tuple_yields_empty_dataframe() -> None:
    df = to_pandas(())
    assert len(df) == 0


def test_explode_row_multiplies_list_columns() -> None:
    items = (
        _WithList(
            id="parent",
            children=({"v": Decimal("1")}, {"v": Decimal("2")}, {"v": Decimal("3")}),
        ),
    )
    df = to_pandas(items, explode=["children"])
    assert len(df) == 3
    assert all(df["id"] == "parent")


def test_explode_unknown_column_raises_keyerror() -> None:
    df_input = (_Trade(id="t", price=Decimal("0.5"), size=Decimal("100")),)
    with pytest.raises(KeyError):
        to_pandas(df_input, explode=["does_not_exist"])
