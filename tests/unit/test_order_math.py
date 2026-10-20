from decimal import Decimal

import pytest

from market_sdk._internal.actions.orders.math import (
    decimal_places,
    parse_amount,
    round_down,
    round_normal,
    round_up,
)


def test_parse_amount_scales_to_six_decimals() -> None:
    assert parse_amount(Decimal("1")) == 1_000_000
    assert parse_amount(Decimal("0.5")) == 500_000
    assert parse_amount(Decimal("10.123456")) == 10_123_456


def test_parse_amount_rounds_half_even_on_extra_precision() -> None:
    assert parse_amount(Decimal("1.0000005")) == 1_000_000
    assert parse_amount(Decimal("1.0000015")) == 1_000_002


def test_round_down_truncates_toward_zero() -> None:
    assert round_down(Decimal("0.1234"), 2) == Decimal("0.12")
    assert round_down(Decimal("0.999"), 2) == Decimal("0.99")
    assert round_down(Decimal("1"), 4) == Decimal("1")


def test_round_up_always_rounds_away_from_zero() -> None:
    assert round_up(Decimal("0.1201"), 2) == Decimal("0.13")
    assert round_up(Decimal("0.999"), 2) == Decimal("1.00")
    assert round_up(Decimal("1"), 4) == Decimal("1")


def test_round_normal_uses_banker_rounding() -> None:
    assert round_normal(Decimal("0.125"), 2) == Decimal("0.12")
    assert round_normal(Decimal("0.135"), 2) == Decimal("0.14")


def test_decimal_places_strips_trailing_zeros() -> None:
    assert decimal_places(Decimal("1.0")) == 0
    assert decimal_places(Decimal("1.10")) == 1
    assert decimal_places(Decimal("0.0015")) == 4
    assert decimal_places(Decimal("1")) == 0


def test_decimal_places_integer_inputs() -> None:
    assert decimal_places(Decimal(123)) == 0


def test_round_down_no_op_when_already_within_precision() -> None:
    assert round_down(Decimal("0.12"), 4) == Decimal("0.12")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("0.000001"), 1),
        (Decimal("0.0000001"), 0),
        (Decimal("0.00001"), 10),
    ],
)
def test_parse_amount_handles_six_decimal_boundary(value: Decimal, expected: int) -> None:
    assert parse_amount(value) == expected
