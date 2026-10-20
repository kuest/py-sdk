import pytest
from eth_account import Account
from eth_account.signers.local import LocalAccount

from market_sdk._internal.actions.relayer.calls import (
    erc20_approval_call,
)
from market_sdk._internal.actions.relayer.signing.deposit_wallet import (
    build_deposit_wallet_typed_data,
    sign_deposit_wallet_batch,
)
from market_sdk._internal.actions.relayer.signing.proxy import (
    build_proxy_transaction_hash,
    sign_proxy_message,
)
from market_sdk._internal.actions.relayer.signing.safe import (
    build_safe_typed_data,
    pack_safe_signature,
    sign_safe_transaction,
)
from market_sdk.errors import SigningError
from market_sdk.types import EvmAddress, HexString

_PK = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
_SIGNER: LocalAccount = Account.from_key(_PK)
_TOKEN = EvmAddress("0xDDeeAa11220000000000000000000000000000aA")
_SPENDER = EvmAddress("0x000000000000000000000000000000000000dEaD")
_WALLET = EvmAddress("0x0000000000000000000000000000000000001234")
_RELAY_HUB = EvmAddress("0xD216153c06E857cD7f72665E0aF1d7D82172F494")
_ZERO = EvmAddress("0x0000000000000000000000000000000000000000")
_CHAIN_ID = 137


def test_deposit_wallet_typed_data_shape() -> None:
    call = erc20_approval_call(token_address=_TOKEN, spender=_SPENDER, amount=10)
    typed = build_deposit_wallet_typed_data(
        wallet=_WALLET,
        calls=[call],
        nonce="3",
        deadline="1000000",
        chain_id=_CHAIN_ID,
    )
    assert typed["primaryType"] == "Batch"
    assert typed["domain"]["name"] == "DepositWallet"
    assert typed["domain"]["version"] == "1"
    assert typed["domain"]["chainId"] == _CHAIN_ID
    assert typed["domain"]["verifyingContract"] == str(_WALLET)
    assert typed["message"]["wallet"] == str(_WALLET)
    assert typed["message"]["nonce"] == 3
    assert typed["message"]["deadline"] == 1000000


def test_deposit_wallet_signature_is_65_byte_hex() -> None:
    call = erc20_approval_call(token_address=_TOKEN, spender=_SPENDER, amount=10)
    sig = sign_deposit_wallet_batch(
        _SIGNER, wallet=_WALLET, calls=[call], nonce="3", deadline="1000000", chain_id=_CHAIN_ID
    )
    assert sig.startswith("0x")
    assert len(sig) == 2 + 130


def test_deposit_wallet_signature_changes_with_nonce() -> None:
    call = erc20_approval_call(token_address=_TOKEN, spender=_SPENDER, amount=10)
    a = sign_deposit_wallet_batch(
        _SIGNER, wallet=_WALLET, calls=[call], nonce="3", deadline="1000000", chain_id=_CHAIN_ID
    )
    b = sign_deposit_wallet_batch(
        _SIGNER, wallet=_WALLET, calls=[call], nonce="4", deadline="1000000", chain_id=_CHAIN_ID
    )
    assert a != b


def test_proxy_hash_is_32_bytes_and_deterministic() -> None:
    data = HexString("0xdeadbeef")
    a = build_proxy_transaction_hash(
        from_address=EvmAddress(_SIGNER.address),
        to=_TOKEN,
        data=data,
        relayer_fee="0",
        gas_price="0",
        gas_limit="10000000",
        nonce="0",
        relay_hub=_RELAY_HUB,
        relay=_ZERO,
    )
    b = build_proxy_transaction_hash(
        from_address=EvmAddress(_SIGNER.address),
        to=_TOKEN,
        data=data,
        relayer_fee="0",
        gas_price="0",
        gas_limit="10000000",
        nonce="0",
        relay_hub=_RELAY_HUB,
        relay=_ZERO,
    )
    assert a == b
    assert a.startswith("0x")
    assert len(a) == 2 + 64


def test_proxy_hash_changes_with_nonce() -> None:
    data = HexString("0xdeadbeef")
    a = build_proxy_transaction_hash(
        from_address=EvmAddress(_SIGNER.address),
        to=_TOKEN,
        data=data,
        relayer_fee="0",
        gas_price="0",
        gas_limit="10000000",
        nonce="0",
        relay_hub=_RELAY_HUB,
        relay=_ZERO,
    )
    b = build_proxy_transaction_hash(
        from_address=EvmAddress(_SIGNER.address),
        to=_TOKEN,
        data=data,
        relayer_fee="0",
        gas_price="0",
        gas_limit="10000000",
        nonce="1",
        relay_hub=_RELAY_HUB,
        relay=_ZERO,
    )
    assert a != b


def test_proxy_signature_is_65_byte_hex() -> None:
    h = build_proxy_transaction_hash(
        from_address=EvmAddress(_SIGNER.address),
        to=_TOKEN,
        data=HexString("0xdeadbeef"),
        relayer_fee="0",
        gas_price="0",
        gas_limit="10000000",
        nonce="0",
        relay_hub=_RELAY_HUB,
        relay=_ZERO,
    )
    sig = sign_proxy_message(_SIGNER, h)
    assert sig.startswith("0x")
    assert len(sig) == 2 + 130


def test_safe_typed_data_shape() -> None:
    typed = build_safe_typed_data(
        safe_address=_WALLET,
        to=_TOKEN,
        data=HexString("0xdeadbeef"),
        value=0,
        operation=0,
        nonce="0",
        chain_id=_CHAIN_ID,
    )
    assert typed["primaryType"] == "SafeTx"
    assert "name" not in typed["domain"]
    assert "version" not in typed["domain"]
    assert typed["domain"]["chainId"] == _CHAIN_ID
    assert typed["domain"]["verifyingContract"] == str(_WALLET)


def test_safe_signature_is_packed_after_signing() -> None:
    sig = sign_safe_transaction(
        _SIGNER,
        safe_address=_WALLET,
        to=_TOKEN,
        data=HexString("0xdeadbeef"),
        value=0,
        operation=0,
        nonce="0",
        chain_id=_CHAIN_ID,
    )
    assert sig.startswith("0x")
    assert len(sig) == 2 + 130
    v = int(sig[-2:], 16)
    assert v in (31, 32)


def test_pack_safe_signature_v_zero_becomes_thirty_one() -> None:
    raw = HexString("0x" + "11" * 64 + "00")
    packed = pack_safe_signature(raw)
    assert packed[-2:] == "1f"


def test_pack_safe_signature_v_one_becomes_thirty_two() -> None:
    raw = HexString("0x" + "11" * 64 + "01")
    packed = pack_safe_signature(raw)
    assert packed[-2:] == "20"


def test_pack_safe_signature_v_27_becomes_31() -> None:
    raw = HexString("0x" + "11" * 64 + "1b")
    packed = pack_safe_signature(raw)
    assert packed[-2:] == "1f"


def test_pack_safe_signature_v_28_becomes_32() -> None:
    raw = HexString("0x" + "11" * 64 + "1c")
    packed = pack_safe_signature(raw)
    assert packed[-2:] == "20"


def test_pack_safe_signature_rejects_wrong_length() -> None:
    raw = HexString("0x" + "11" * 32)
    with pytest.raises(SigningError, match="65-byte"):
        pack_safe_signature(raw)


def test_safe_signature_changes_with_nonce() -> None:
    a = sign_safe_transaction(
        _SIGNER,
        safe_address=_WALLET,
        to=_TOKEN,
        data=HexString("0xdeadbeef"),
        value=0,
        operation=0,
        nonce="0",
        chain_id=_CHAIN_ID,
    )
    b = sign_safe_transaction(
        _SIGNER,
        safe_address=_WALLET,
        to=_TOKEN,
        data=HexString("0xdeadbeef"),
        value=0,
        operation=0,
        nonce="1",
        chain_id=_CHAIN_ID,
    )
    assert a != b
