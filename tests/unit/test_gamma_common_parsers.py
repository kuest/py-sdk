from decimal import Decimal

import pytest

from market_sdk.models.gamma.common import (
    coerce_string_id,
    parse_decimal,
    parse_optional_decimal,
    parse_string_sequence,
)


def test_parse_string_sequence_accepts_strings() -> None:
    assert parse_string_sequence(["a", "b"]) == ("a", "b")


def test_parse_string_sequence_accepts_empty() -> None:
    assert parse_string_sequence([]) == ()
    assert parse_string_sequence(None) == ()


def test_parse_string_sequence_rejects_integers() -> None:
    with pytest.raises(ValueError, match="expected a string"):
        parse_string_sequence([1, 2])


def test_parse_string_sequence_rejects_none_items() -> None:
    with pytest.raises(ValueError, match="expected a string"):
        parse_string_sequence(["a", None])


def test_parse_string_sequence_rejects_dicts() -> None:
    with pytest.raises(ValueError, match="expected a string"):
        parse_string_sequence([{"x": 1}])


def test_parse_optional_decimal_accepts_string() -> None:
    assert parse_optional_decimal("1.5") == Decimal("1.5")


def test_parse_optional_decimal_accepts_number() -> None:
    assert parse_optional_decimal(2) == Decimal("2")


def test_parse_optional_decimal_returns_none_for_empty() -> None:
    assert parse_optional_decimal(None) is None
    assert parse_optional_decimal("") is None


def test_parse_optional_decimal_raises_value_error_on_garbage() -> None:
    with pytest.raises(ValueError, match="invalid decimal"):
        parse_optional_decimal("not-a-number")


def test_parse_decimal_raises_value_error_on_garbage() -> None:
    with pytest.raises(ValueError, match="invalid decimal"):
        parse_decimal("nope")


def test_coerce_string_id_passes_strings_through() -> None:
    assert coerce_string_id("abc") == "abc"


def test_coerce_string_id_converts_int_to_str() -> None:
    assert coerce_string_id(123) == "123"


def test_coerce_string_id_passes_bools_through() -> None:
    assert coerce_string_id(True) is True


def test_coerce_string_id_passes_none_through() -> None:
    assert coerce_string_id(None) is None
