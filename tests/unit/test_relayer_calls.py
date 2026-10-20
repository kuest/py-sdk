import pytest

from market_sdk._internal.actions.relayer.calls import (
    MAX_UINT256,
    TransactionCall,
    encode_proxy_call,
    encode_safe_multisend_call,
    erc20_approval_call,
)
from market_sdk.errors import UserInputError
from market_sdk.types import EvmAddress, HexString

_TOKEN = EvmAddress("0xDDeeAa11220000000000000000000000000000aA")
_SPENDER = EvmAddress("0x000000000000000000000000000000000000dEaD")


def test_erc20_approval_call_emits_approve_selector() -> None:
    call = erc20_approval_call(token_address=_TOKEN, spender=_SPENDER, amount=10)
    assert call.to == _TOKEN
    assert call.value == 0
    assert call.data.startswith("0x095ea7b3")


def test_erc20_approval_max_amount() -> None:
    call = erc20_approval_call(token_address=_TOKEN, spender=_SPENDER, amount=MAX_UINT256)
    assert call.data.lower().endswith("f" * 64)


def test_erc20_approval_rejects_negative_amount() -> None:
    with pytest.raises(UserInputError, match="non-negative"):
        erc20_approval_call(token_address=_TOKEN, spender=_SPENDER, amount=-1)


def test_erc20_approval_rejects_above_uint256() -> None:
    with pytest.raises(UserInputError, match="uint256"):
        erc20_approval_call(token_address=_TOKEN, spender=_SPENDER, amount=MAX_UINT256 + 1)


def test_erc20_approval_rejects_bool() -> None:
    with pytest.raises(UserInputError, match="int"):
        erc20_approval_call(
            token_address=_TOKEN,
            spender=_SPENDER,
            amount=True,  # type: ignore[arg-type]
        )


def test_encode_proxy_call_wraps_calls() -> None:
    call = erc20_approval_call(token_address=_TOKEN, spender=_SPENDER, amount=1)
    encoded = encode_proxy_call([call])
    from eth_utils.crypto import keccak

    expected_selector = keccak(b"proxy((uint8,address,uint256,bytes)[])")[:4]
    assert encoded.startswith("0x" + expected_selector.hex())


def test_encode_proxy_call_rejects_empty() -> None:
    with pytest.raises(UserInputError, match="at least one call"):
        encode_proxy_call([])


def test_encode_safe_multisend_rejects_empty() -> None:
    with pytest.raises(UserInputError, match="at least one call"):
        encode_safe_multisend_call([])


def test_encode_safe_multisend_single_call_packed_format() -> None:
    call = TransactionCall(to=_TOKEN, data=HexString("0xdeadbeef"), value=0)
    encoded = encode_safe_multisend_call([call])
    assert encoded.startswith("0x8d80ff0a")
    raw = bytes.fromhex(encoded[2:])
    inner_offset = 4 + 32 + 32
    inner_len = int.from_bytes(raw[4 + 32 : 4 + 64], "big")
    assert inner_len == 1 + 20 + 32 + 32 + 4
    inner = raw[inner_offset : inner_offset + inner_len]
    assert inner[0] == 0
    assert inner[1:21].hex() == str(_TOKEN)[2:].lower()
    assert int.from_bytes(inner[21:53], "big") == 0
    assert int.from_bytes(inner[53:85], "big") == 4
    assert inner[85:89].hex() == "deadbeef"


def test_encode_safe_multisend_two_calls_concatenated() -> None:
    calls = [
        TransactionCall(to=_TOKEN, data=HexString("0xdeadbeef"), value=0),
        TransactionCall(to=_SPENDER, data=HexString("0x0011223344556677"), value=123),
    ]
    encoded = encode_safe_multisend_call(calls)
    raw = bytes.fromhex(encoded[2:])
    inner_offset = 4 + 32 + 32
    inner_len = int.from_bytes(raw[4 + 32 : 4 + 64], "big")
    expected_len = (1 + 20 + 32 + 32 + 4) + (1 + 20 + 32 + 32 + 8)
    assert inner_len == expected_len

    inner = raw[inner_offset : inner_offset + inner_len]
    second = inner[89:]
    assert second[0] == 0
    assert second[1:21].hex() == str(_SPENDER)[2:].lower()
    assert int.from_bytes(second[21:53], "big") == 123
    assert int.from_bytes(second[53:85], "big") == 8
    assert second[85:93].hex() == "0011223344556677"
