from typing import cast

from eth_account import Account
from eth_account.signers.local import LocalAccount

from market_sdk._internal.l1_auth import (
    build_api_key_auth_typed_data,
    sign_api_key_auth,
)

PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
SIGNER_ADDRESS = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"


def test_build_api_key_auth_typed_data_has_clob_auth_primary_type() -> None:
    payload = build_api_key_auth_typed_data(
        address=SIGNER_ADDRESS, chain_id=137, timestamp=1700000000
    )

    assert payload["primaryType"] == "ClobAuth"


def test_build_api_key_auth_typed_data_uses_polygon_chain_in_domain() -> None:
    payload = build_api_key_auth_typed_data(
        address=SIGNER_ADDRESS, chain_id=137, timestamp=1700000000
    )

    assert payload["domain"] == {
        "name": "ClobAuthDomain",
        "version": "1",
        "chainId": 137,
    }


def test_build_api_key_auth_typed_data_renders_canonical_message() -> None:
    payload = build_api_key_auth_typed_data(
        address=SIGNER_ADDRESS, chain_id=137, timestamp=1700000000, nonce=3
    )

    assert payload["message"] == {
        "address": SIGNER_ADDRESS,
        "timestamp": "1700000000",
        "nonce": 3,
        "message": "This message attests that I control the given wallet",
    }


def test_build_api_key_auth_typed_data_defaults_nonce_to_zero() -> None:
    payload = build_api_key_auth_typed_data(
        address=SIGNER_ADDRESS, chain_id=137, timestamp=1700000000
    )

    assert payload["message"]["nonce"] == 0


def test_sign_api_key_auth_returns_evm_signature_components() -> None:
    signer = cast(LocalAccount, Account.from_key(PRIVATE_KEY))

    result = sign_api_key_auth(signer, chain_id=137, timestamp=1700000000, nonce=0)

    assert result.address == SIGNER_ADDRESS
    assert result.nonce == 0
    assert result.timestamp == 1700000000
    assert result.signature.startswith("0x")
    assert len(result.signature) == 132  # 0x + 130 hex chars (65 bytes)


def test_sign_api_key_auth_is_deterministic_for_same_inputs() -> None:
    signer = cast(LocalAccount, Account.from_key(PRIVATE_KEY))

    sig_a = sign_api_key_auth(signer, chain_id=137, timestamp=1700000000)
    sig_b = sign_api_key_auth(signer, chain_id=137, timestamp=1700000000)

    assert sig_a.signature == sig_b.signature


def test_sign_api_key_auth_signature_changes_with_nonce() -> None:
    signer = cast(LocalAccount, Account.from_key(PRIVATE_KEY))

    sig_a = sign_api_key_auth(signer, chain_id=137, timestamp=1700000000, nonce=0)
    sig_b = sign_api_key_auth(signer, chain_id=137, timestamp=1700000000, nonce=1)

    assert sig_a.signature != sig_b.signature
