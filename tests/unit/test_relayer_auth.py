import asyncio
from collections.abc import Mapping

import pytest

from market_sdk._internal.actions.relayer.auth import (
    RelayerHeaderResolver,
    make_relayer_header_resolver,
)
from market_sdk.auth import BuilderApiKey, RelayerApiKey
from market_sdk.errors import UserInputError


async def _call(
    resolve: RelayerHeaderResolver, method: str, path: str, body: str | None
) -> Mapping[str, str]:
    return await resolve(method, path, body)


def test_builder_api_key_resolver_emits_hmac_headers() -> None:
    auth = BuilderApiKey(key="my-key", secret="dGVzdA==", passphrase="my-pass")
    resolve = make_relayer_header_resolver(auth)
    headers = asyncio.run(_call(resolve, "POST", "/submit", '{"x":1}'))
    assert set(headers) == {
        "KUEST_BUILDER_API_KEY",
        "KUEST_BUILDER_PASSPHRASE",
        "KUEST_BUILDER_SIGNATURE",
        "KUEST_BUILDER_TIMESTAMP",
    }
    assert headers["KUEST_BUILDER_API_KEY"] == "my-key"
    assert headers["KUEST_BUILDER_PASSPHRASE"] == "my-pass"
    assert int(headers["KUEST_BUILDER_TIMESTAMP"]) > 0
    assert len(headers["KUEST_BUILDER_SIGNATURE"]) > 20


def test_builder_signature_differs_per_body() -> None:
    auth = BuilderApiKey(key="k", secret="dGVzdA==", passphrase="p")
    resolve = make_relayer_header_resolver(auth)
    a = asyncio.run(_call(resolve, "POST", "/submit", '{"a":1}'))
    b = asyncio.run(_call(resolve, "POST", "/submit", '{"a":2}'))
    assert a["KUEST_BUILDER_SIGNATURE"] != b["KUEST_BUILDER_SIGNATURE"]


def test_builder_resolver_handles_none_body() -> None:
    auth = BuilderApiKey(key="k", secret="dGVzdA==", passphrase="p")
    resolve = make_relayer_header_resolver(auth)
    headers = asyncio.run(_call(resolve, "GET", "/v1/account/transactions/params", None))
    assert "KUEST_BUILDER_SIGNATURE" in headers


def test_relayer_api_key_resolver_emits_plaintext_headers() -> None:
    auth = RelayerApiKey(
        key="r-key",
        address="0x0000000000000000000000000000000000000001",
    )
    resolve = make_relayer_header_resolver(auth)
    headers = asyncio.run(_call(resolve, "POST", "/submit", "{}"))
    assert headers == {
        "RELAYER_API_KEY": "r-key",
        "RELAYER_API_KEY_ADDRESS": "0x0000000000000000000000000000000000000001",
    }


def test_relayer_api_key_resolver_ignores_method_path_body() -> None:
    auth = RelayerApiKey(key="k", address="0x0000000000000000000000000000000000000001")
    resolve = make_relayer_header_resolver(auth)
    a = asyncio.run(_call(resolve, "GET", "/x", None))
    b = asyncio.run(_call(resolve, "POST", "/y", "body"))
    assert a == b


def test_relayer_api_key_normalizes_address() -> None:
    from eth_utils.address import to_checksum_address

    raw = "0xddeeaa11220000000000000000000000000000aa"
    auth = RelayerApiKey(key="k", address=raw)
    assert auth.address == to_checksum_address(raw)
    assert auth.address != raw


def test_relayer_api_key_rejects_invalid_address() -> None:
    with pytest.raises(UserInputError, match="Invalid relayer address"):
        RelayerApiKey(key="k", address="not-an-address")


def test_builder_api_key_repr_does_not_leak_secrets() -> None:
    auth = BuilderApiKey(key="super-secret-key", secret="dGVzdA==", passphrase="super-pass")
    r = repr(auth)
    s = str(auth)
    assert "super-secret-key" not in r and "super-secret-key" not in s
    assert "dGVzdA==" not in r and "dGVzdA==" not in s
    assert "super-pass" not in r and "super-pass" not in s
    assert "BuilderApiKey" in r and "redacted" in r


def test_relayer_api_key_repr_does_not_leak_key() -> None:
    addr = "0x0000000000000000000000000000000000000001"
    auth = RelayerApiKey(key="super-secret-relayer-key", address=addr)
    r = repr(auth)
    s = str(auth)
    assert "super-secret-relayer-key" not in r and "super-secret-relayer-key" not in s
    assert "RelayerApiKey" in r and "redacted" in r
    assert addr in r
