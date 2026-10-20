"""Offline contract fixtures from clob/routes/auth.rs and relayer/routes/auth.rs."""

# pyright: reportPrivateUsage=false

import dataclasses
from urllib.parse import urlparse

import httpx
import pytest
from _relayer_helpers import FAKE_CREDS, PK_DEPLOY_WALLET, install_sync_relayer_handler
from eth_account import Account

from market_sdk import RelayerApiKey, SecureClient, UserInputError


def test_builder_credentials_use_relayer_l1_then_l2_and_builder_headers() -> None:
    # relayer/src/routes/auth.rs:45-76, 70-76, 201-205, 232-286 at 35b335a.
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        if request.method == "POST":
            payload: object = {"apiKey": "builder-key", "secret": "dGVzdA==", "passphrase": "p"}
        elif request.method == "GET":
            payload = ["builder-key"]
        else:
            payload = {"revoked": True}
        return httpx.Response(200, json=payload, request=request)

    signer = Account.from_key(PK_DEPLOY_WALLET)
    with SecureClient._create(
        private_key=PK_DEPLOY_WALLET,
        wallet=signer.address,
        credentials=FAKE_CREDS,
        validate_credentials=False,
    ) as client:
        install_sync_relayer_handler(client, handler)
        builder = client.create_builder_api_key()
        assert builder.key == "builder-key"
        assert tuple(key.key for key in client.fetch_builder_api_keys()) == ("builder-key",)
        client._ctx = dataclasses.replace(client._ctx, api_key=builder)
        client.revoke_builder_api_key()

    assert [(r.method, urlparse(str(r.url)).path) for r in captured] == [
        ("POST", "/auth/builder-api-key"),
        ("GET", "/auth/builder-api-key"),
        ("DELETE", "/auth/builder-api-key"),
    ]
    assert captured[0].headers.get("KUEST_NONCE") == "0"
    assert captured[0].headers.get("KUEST_SIGNATURE")
    assert captured[1].headers.get("KUEST_API_KEY") == FAKE_CREDS.key
    assert captured[1].headers.get("KUEST_SIGNATURE")
    assert captured[2].headers.get("KUEST_BUILDER_API_KEY") == "builder-key"


def test_builder_key_list_rejects_relayer_api_key_mode_before_transport() -> None:
    signer = Account.from_key(PK_DEPLOY_WALLET)
    with SecureClient._create(
        private_key=PK_DEPLOY_WALLET,
        wallet=signer.address,
        credentials=FAKE_CREDS,
        validate_credentials=False,
    ) as client:
        client._ctx = dataclasses.replace(
            client._ctx, api_key=RelayerApiKey(key="offline", address=signer.address)
        )
        with pytest.raises(UserInputError, match="Listing builder keys"):
            client.fetch_builder_api_keys()
