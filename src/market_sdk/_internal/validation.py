from market_sdk.errors import UserInputError
from market_sdk.types import HexString


def require_nonempty(name: str, value: object) -> str:
    if not isinstance(value, str):
        raise UserInputError(f"{name} must be a string, got {type(value).__name__}.")
    if not value:
        raise UserInputError(f"{name} is required")
    return value


def validate_builder_code(value: object) -> HexString:
    if not isinstance(value, str):
        raise UserInputError(
            f"builder_code must be an address or 32-byte hex string, got {type(value).__name__}."
        )
    if not value.startswith(("0x", "0X")):
        raise UserInputError("builder_code must be 0x-prefixed.")
    hex_value = value[2:]
    if len(hex_value) not in (40, 64):
        raise UserInputError("builder_code must be an address or 32-byte hex string.")
    if not all(char in "0123456789abcdefABCDEF" for char in hex_value):
        raise UserInputError("builder_code must be an address or 32-byte hex string.")
    return HexString("0x" + hex_value.lower().rjust(64, "0"))


__all__ = ["require_nonempty", "validate_builder_code"]
