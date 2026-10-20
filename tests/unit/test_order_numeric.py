from decimal import Decimal

import pytest

from market_sdk._internal.actions.orders._numeric import coerce_positive_decimal
from market_sdk.errors import UserInputError


def test_coerce_positive_decimal_passes_through_decimal() -> None:
    assert coerce_positive_decimal("price", Decimal("0.5")) == Decimal("0.5")


def test_coerce_positive_decimal_accepts_int() -> None:
    assert coerce_positive_decimal("size", 10) == Decimal(10)


def test_coerce_positive_decimal_accepts_string() -> None:
    assert coerce_positive_decimal("size", "10.5") == Decimal("10.5")


def test_coerce_positive_decimal_routes_float_through_str_to_preserve_literal() -> None:
    # Decimal(0.1) leaks IEEE-754 noise: Decimal('0.10000000000000000555...')
    # Decimal(str(0.1)) preserves the literal: Decimal('0.1')
    result = coerce_positive_decimal("price", 0.1)
    assert result == Decimal("0.1")
    assert str(result) == "0.1"


def test_coerce_positive_decimal_rejects_bool() -> None:
    with pytest.raises(UserInputError, match="positive number"):
        coerce_positive_decimal("amount", True)


def test_coerce_positive_decimal_rejects_zero() -> None:
    with pytest.raises(UserInputError, match="positive number"):
        coerce_positive_decimal("amount", 0)


def test_coerce_positive_decimal_rejects_negative() -> None:
    with pytest.raises(UserInputError, match="positive number"):
        coerce_positive_decimal("amount", -1)


def test_coerce_positive_decimal_rejects_non_numeric_string() -> None:
    with pytest.raises(UserInputError, match="decimal number"):
        coerce_positive_decimal("amount", "not-a-number")


def test_coerce_positive_decimal_rejects_non_numeric_type() -> None:
    with pytest.raises(UserInputError, match="must be a number"):
        coerce_positive_decimal("amount", [10])  # type: ignore[arg-type]


def test_coerce_positive_decimal_rejects_nan() -> None:
    with pytest.raises(UserInputError, match="positive number"):
        coerce_positive_decimal("amount", float("nan"))


def test_coerce_positive_decimal_rejects_infinity() -> None:
    with pytest.raises(UserInputError, match="positive number"):
        coerce_positive_decimal("amount", float("inf"))
