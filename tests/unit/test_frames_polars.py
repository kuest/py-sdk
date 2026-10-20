"""Tests for the polars adapter."""

# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownParameterType=false

from __future__ import annotations

from decimal import Decimal

import polars as pl
import pytest
from pydantic import BaseModel

from market_sdk.frames import to_polars


class _Trade(BaseModel):
    id: str
    price: Decimal
    size: Decimal


class _WithList(BaseModel):
    id: str
    children: tuple[dict[str, Decimal], ...] = ()


def test_single_model_yields_one_row() -> None:
    m = _Trade(id="t", price=Decimal("0.5"), size=Decimal("100"))
    df = to_polars(m)
    assert df.shape == (1, 3)
    assert df.columns == ["id", "price", "size"]


def test_native_decimal_dtype_preserves_precision() -> None:
    high_precision = Decimal("0.123456789012345678")
    trades = (
        _Trade(id="t1", price=high_precision, size=Decimal("1")),
        _Trade(id="t2", price=Decimal("0.987654321098765432"), size=Decimal("2")),
    )
    df = to_polars(trades)
    assert isinstance(df["price"].dtype, pl.Decimal)
    assert df["price"][0] == high_precision


def test_tuple_of_models_yields_n_rows() -> None:
    trades = tuple(_Trade(id=f"t{i}", price=Decimal(f"0.{i}"), size=Decimal("1")) for i in range(5))
    df = to_polars(trades)
    assert df.shape == (5, 3)


def test_empty_tuple_yields_empty_dataframe() -> None:
    df = to_polars(())
    assert df.shape == (0, 0)


def test_explode_row_multiplies_list_columns() -> None:
    items = (
        _WithList(
            id="parent",
            children=({"v": Decimal("1")}, {"v": Decimal("2")}),
        ),
    )
    df = to_polars(items, explode=["children"])
    assert df.shape == (2, 2)


def test_explode_unknown_column_raises() -> None:
    df_input = (_Trade(id="t", price=Decimal("0.5"), size=Decimal("100")),)
    with pytest.raises(pl.exceptions.ColumnNotFoundError):
        to_polars(df_input, explode=["nope"])


def test_decimal256_column_raises_clean_error_not_rust_panic() -> None:
    """Regression: ``pl.from_arrow`` panics in Rust on decimal256; the SDK should TypeError."""
    from pydantic import BaseModel

    class _Big(BaseModel):
        v: Decimal

    big = Decimal("123456789012345678901234567890123456789")
    with pytest.raises(TypeError, match=r"decimal256"):
        to_polars((_Big(v=big),))


def test_decimal256_nested_in_struct_also_caught() -> None:
    from pydantic import BaseModel

    class _Inner(BaseModel):
        v: Decimal

    class _Outer(BaseModel):
        id: str
        inner: _Inner

    big = Decimal("123456789012345678901234567890123456789")
    with pytest.raises(TypeError, match=r"decimal256"):
        to_polars((_Outer(id="x", inner=_Inner(v=big)),))
