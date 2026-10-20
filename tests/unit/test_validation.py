import pytest

from market_sdk._internal.validation import require_nonempty
from market_sdk.errors import UserInputError


def test_require_nonempty_returns_value() -> None:
    assert require_nonempty("user", "0xWALLET") == "0xWALLET"


def test_require_nonempty_rejects_empty_string() -> None:
    with pytest.raises(UserInputError, match="user is required"):
        require_nonempty("user", "")


def test_require_nonempty_uses_provided_name() -> None:
    with pytest.raises(UserInputError, match="market_id is required"):
        require_nonempty("market_id", "")
