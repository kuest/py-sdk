"""Perps delegated credentials lifecycle tests against a mocked transport."""

import asyncio
import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from eth_account import Account

from market_sdk._internal.actions.perps import credentials as perps_credentials
from market_sdk._internal.actions.perps.signing import (
    build_perps_create_proxy_typed_data,
    build_perps_op_typed_data,
)
from market_sdk.clients._transport import AsyncTransport
from market_sdk.errors import (
    RequestRejectedError,
    UnexpectedResponseError,
    UserInputError,
)
from market_sdk.models.perps.credentials import PerpsCredentials

_BASE_URL = "https://perps.test"
_OWNER_KEY = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
_OWNER = Account.from_key(_OWNER_KEY)


def _transport(handler: Callable[[httpx.Request], httpx.Response]) -> AsyncTransport:
    return AsyncTransport(
        base_url=_BASE_URL,
        client=httpx.AsyncClient(base_url=_BASE_URL, transport=httpx.MockTransport(handler)),
    )


def _credentials_response(proxy: str, *, expiry_ms: int) -> dict[str, Any]:
    return {
        "address": _OWNER.address,
        "keys": [{"proxy": proxy, "expiry": expiry_ms}],
    }


def test_create_credentials_signs_create_proxy_and_validates() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        if request.url.path == "/v1/account/proxy":
            return httpx.Response(200, json={"secret": "new-secret"})
        assert request.url.path == "/v1/account/credentials"
        body = json.loads(captured[0].content)
        expiry = body["op"]["args"]["expiry"]
        return httpx.Response(
            200, json=_credentials_response(body["op"]["args"]["proxy"], expiry_ms=expiry)
        )

    async def run() -> PerpsCredentials:
        transport = _transport(handler)
        try:
            return await perps_credentials.create_credentials(
                transport,
                signer=_OWNER,
                chain_id=137,
                expires_in=timedelta(days=7),
                label="bot",
            )
        finally:
            await transport.close()

    credentials = asyncio.run(run())
    assert credentials.secret == "new-secret"
    assert Account.from_key(credentials.private_key).address == credentials.proxy

    create_request = captured[0]
    body = json.loads(create_request.content)
    assert body["label"] == "bot"
    assert body["op"]["type"] == "createProxy"
    assert body["op"]["args"]["owner"] == _OWNER.address
    # The signature must recover to the owner for the CreateProxy payload.
    payload = build_perps_create_proxy_typed_data(
        chain_id=137,
        proxy=body["op"]["args"]["proxy"],
        expires_at_ms=body["op"]["args"]["expiry"],
        salt=body["salt"],
        timestamp_ms=body["ts"],
    )
    from eth_account.messages import encode_typed_data

    recovered = Account.recover_message(
        encode_typed_data(full_message=payload), signature=body["sig"]
    )
    assert recovered == _OWNER.address

    validate_request = captured[1]
    assert validate_request.headers["POLYMARKET-PROXY"] == credentials.proxy
    assert validate_request.headers["POLYMARKET-SECRET"] == "new-secret"


def test_resume_rejects_mismatched_private_key() -> None:
    async def run() -> None:
        transport = _transport(lambda request: httpx.Response(200, json={}))
        try:
            with pytest.raises(UserInputError, match="does not match"):
                await perps_credentials.resume_credentials(
                    transport,
                    signer_address=_OWNER.address,
                    credentials=PerpsCredentials(
                        proxy="0x9965507D1a55bcC2695C58ba16FB37d819B0A4dc",
                        private_key=_OWNER_KEY,  # derives a different address
                        secret="secret",
                        expires_at=datetime.now(tz=UTC),
                    ),
                )
        finally:
            await transport.close()

    asyncio.run(run())


def test_validate_rejects_expired_and_missing_keys() -> None:
    proxy_account = Account.create()
    credentials = PerpsCredentials(
        proxy=proxy_account.address,
        private_key="0x" + proxy_account.key.hex().removeprefix("0x"),
        secret="secret",
        expires_at=datetime.now(tz=UTC),
    )

    def expired_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_credentials_response(credentials.proxy, expiry_ms=1_000))

    def missing_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"address": _OWNER.address, "keys": []})

    async def run() -> None:
        expired = _transport(expired_handler)
        missing = _transport(missing_handler)
        try:
            with pytest.raises(UnexpectedResponseError, match="expired"):
                await perps_credentials.validate_credentials(
                    expired, signer_address=_OWNER.address, credentials=credentials
                )
            with pytest.raises(UnexpectedResponseError, match="not returned"):
                await perps_credentials.validate_credentials(
                    missing, signer_address=_OWNER.address, credentials=credentials
                )
        finally:
            await expired.close()
            await missing.close()

    asyncio.run(run())


def test_validate_normalizes_nanosecond_expiries() -> None:
    proxy_account = Account.create()
    credentials = PerpsCredentials(
        proxy=proxy_account.address,
        private_key="0x" + proxy_account.key.hex().removeprefix("0x"),
        secret="secret",
        expires_at=datetime.now(tz=UTC),
    )
    expiry_ms = int((datetime.now(tz=UTC) + timedelta(days=1)).timestamp() * 1000)

    def handler(request: httpx.Request) -> httpx.Response:
        # The credentials endpoint currently reports expiries in nanoseconds.
        return httpx.Response(
            200,
            json=_credentials_response(credentials.proxy, expiry_ms=expiry_ms * 1_000_000),
        )

    async def run() -> PerpsCredentials:
        transport = _transport(handler)
        try:
            return await perps_credentials.validate_credentials(
                transport, signer_address=_OWNER.address, credentials=credentials
            )
        finally:
            await transport.close()

    validated = asyncio.run(run())
    assert int(validated.expires_at.timestamp() * 1000) == expiry_ms


def test_revoke_sends_signed_delete_op_and_maps_err_status() -> None:
    captured: list[httpx.Request] = []
    proxy = "0x9965507D1a55bcC2695C58ba16FB37d819B0A4dc"

    def ok_handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"status": "ok"})

    def err_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "err", "error": "unknown proxy"})

    async def run() -> None:
        ok = _transport(ok_handler)
        err = _transport(err_handler)
        try:
            await perps_credentials.revoke_credentials(ok, signer=_OWNER, chain_id=137, proxy=proxy)
            with pytest.raises(RequestRejectedError, match="unknown proxy"):
                await perps_credentials.revoke_credentials(
                    err, signer=_OWNER, chain_id=137, proxy=proxy
                )
        finally:
            await ok.close()
            await err.close()

    asyncio.run(run())
    body = json.loads(captured[0].content)
    assert body["op"] == {"type": "deleteProxy", "args": {"proxy": proxy}}
    from eth_account.messages import encode_typed_data

    payload = build_perps_op_typed_data(
        chain_id=137, op=["deleteProxy", [proxy]], salt=body["salt"], timestamp_ms=body["ts"]
    )
    recovered = Account.recover_message(
        encode_typed_data(full_message=payload), signature=body["sig"]
    )
    assert recovered == _OWNER.address
