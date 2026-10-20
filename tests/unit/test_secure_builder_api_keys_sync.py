# pyright: reportPrivateUsage=false
import dataclasses
from typing import Any
from urllib.parse import urlparse

import httpx
import pytest

from market_sdk import ApiKeyCreds, BuilderApiKey, SecureClient
from market_sdk.clients._transport import SyncTransport
from market_sdk.errors import UnexpectedResponseError, UserInputError

PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
SIGNER_ADDRESS = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
FAKE_CREDS = ApiKeyCreds(key="test-key", passphrase="test-passphrase", secret="dGVzdA==")
BUILDER = BuilderApiKey(key="bk", secret="dGVzdA==", passphrase="bp")


def _capture(captured: list[httpx.Request], status: int, payload: Any) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(status, json=payload, request=request)

    return httpx.MockTransport(handler)


def _install_relayer(client: SecureClient, handler: httpx.MockTransport) -> None:
    transport = SyncTransport(
        base_url="https://relayer.test",
        client=httpx.Client(base_url="https://relayer.test", transport=handler),
        header_resolver=client._ctx.relayer._header_resolver,
    )
    client._ctx = dataclasses.replace(client._ctx, relayer=transport)


def _make_client(*, with_builder_key: bool = False) -> SecureClient:
    return SecureClient._create(
        private_key=PRIVATE_KEY,
        wallet=SIGNER_ADDRESS,
        credentials=FAKE_CREDS,
        api_key=BUILDER if with_builder_key else None,
        validate_credentials=False,
    )


def test_create_builder_api_key_sends_l1_to_relayer_and_returns_credential() -> None:
    captured: list[httpx.Request] = []
    payload = {"apiKey": "new-bk", "secret": "new-secret", "passphrase": "new-pass"}

    with _make_client() as client:
        _install_relayer(client, _capture(captured, 200, payload))
        result = client.create_builder_api_key()

    assert isinstance(result, BuilderApiKey)
    assert (result.key, result.secret, result.passphrase) == ("new-bk", "new-secret", "new-pass")
    request = captured[0]
    assert request.method == "POST"
    assert urlparse(str(request.url)).path == "/auth/builder-api-key"
    # The relayer's issuance route verifies signed L1 ClobAuth headers.
    assert request.headers.get("KUEST_NONCE") == "0"
    assert request.headers.get("KUEST_SIGNATURE")
    assert request.headers.get("KUEST_API_KEY") is None
    assert request.headers.get("KUEST_BUILDER_API_KEY") is None


def test_fetch_builder_api_keys_returns_records_via_l2() -> None:
    captured: list[httpx.Request] = []
    payload = ["bk"]

    with _make_client() as client:
        _install_relayer(client, _capture(captured, 200, payload))
        keys = client.fetch_builder_api_keys()

    assert len(keys) == 1
    assert keys[0].key == "bk"
    assert keys[0].created_at is None
    assert keys[0].revoked_at is None
    request = captured[0]
    assert request.method == "GET"
    assert urlparse(str(request.url)).path == "/auth/builder-api-key"
    assert request.headers.get("KUEST_API_KEY") == FAKE_CREDS.key


def test_fetch_builder_api_keys_normalizes_bare_string_elements() -> None:
    with _make_client() as client:
        _install_relayer(client, _capture([], 200, ["bk1", {"key": "bk2"}]))
        keys = client.fetch_builder_api_keys()

    assert [k.key for k in keys] == ["bk1", "bk2"]


def test_revoke_builder_api_key_authenticates_with_builder_key_not_l2() -> None:
    captured: list[httpx.Request] = []

    with _make_client(with_builder_key=True) as client:
        _install_relayer(client, _capture(captured, 200, {"revoked": True}))
        client.revoke_builder_api_key()

    request = captured[0]
    assert request.method == "DELETE"
    assert urlparse(str(request.url)).path == "/auth/builder-api-key"
    # The load-bearing guardrail (ts-sdk#68): revoke is signed by the builder key's own HMAC,
    # NOT the account L2 credential.
    assert request.headers.get("KUEST_BUILDER_API_KEY") == BUILDER.key
    assert request.headers.get("KUEST_BUILDER_PASSPHRASE") == BUILDER.passphrase
    assert request.headers.get("KUEST_BUILDER_SIGNATURE")
    assert request.headers.get("KUEST_BUILDER_TIMESTAMP")
    assert request.headers.get("KUEST_API_KEY") is None


def test_revoke_builder_api_key_requires_a_builder_key() -> None:
    with pytest.raises(UserInputError), _make_client() as client:
        client.revoke_builder_api_key()


def test_revoke_builder_api_key_raises_on_non_ok_payload() -> None:
    with pytest.raises(UnexpectedResponseError), _make_client(with_builder_key=True) as client:
        _install_relayer(client, _capture([], 200, "FAIL"))
        client.revoke_builder_api_key()
