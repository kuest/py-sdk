# pyright: reportPrivateUsage=false
import asyncio
import contextlib
import dataclasses
from typing import Any
from urllib.parse import urlparse

import httpx
import pytest

from market_sdk import ApiKeyCreds, AsyncPublicClient, AsyncSecureClient
from market_sdk.clients._transport import AsyncTransport
from market_sdk.errors import RequestRejectedError

PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
SIGNER_ADDRESS = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
FAKE_CREDS = ApiKeyCreds(key="test-key", passphrase="test-passphrase", secret="dGVzdA==")


def _capture(captured: list[httpx.Request], status: int, payload: Any) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(status, json=payload, request=request)

    return httpx.MockTransport(handler)


def _install_secure_clob(client: AsyncSecureClient, handler: httpx.MockTransport) -> None:
    transport = AsyncTransport(
        base_url="https://clob.test",
        client=httpx.AsyncClient(base_url="https://clob.test", transport=handler),
        header_resolver=client._ctx.secure_clob._header_resolver,
    )
    client._ctx = dataclasses.replace(client._ctx, secure_clob=transport)


async def _build_client() -> AsyncSecureClient:
    return await AsyncSecureClient._create(
        private_key=PRIVATE_KEY,
        wallet=SIGNER_ADDRESS,
        credentials=FAKE_CREDS,
        validate_credentials=False,
    )


def test_end_authentication_calls_delete_and_returns_async_public_client() -> None:
    captured: list[httpx.Request] = []

    async def run() -> AsyncPublicClient:
        client = await _build_client()
        _install_secure_clob(client, _capture(captured, 200, {"revoked": True}))
        public = await client.end_authentication()
        return public

    public = asyncio.run(run())

    assert isinstance(public, AsyncPublicClient)
    assert captured[0].method == "DELETE"
    assert urlparse(str(captured[0].url)).path == "/auth/api-key"


def test_end_authentication_returned_public_client_has_same_environment() -> None:
    async def run() -> AsyncPublicClient:
        client = await _build_client()
        _install_secure_clob(client, _capture([], 200, {"revoked": True}))
        return await client.end_authentication()

    public = asyncio.run(run())

    assert public.environment.name == "production"


def test_end_authentication_blocks_subsequent_method_calls() -> None:
    async def run() -> None:
        client = await _build_client()
        _install_secure_clob(client, _capture([], 200, {"revoked": True}))
        await client.end_authentication()
        await client.fetch_api_keys()

    with pytest.raises(RuntimeError, match="ended authentication"):
        asyncio.run(run())


def test_end_authentication_blocks_property_access_after_end() -> None:
    async def run() -> str:
        client = await _build_client()
        _install_secure_clob(client, _capture([], 200, {"revoked": True}))
        await client.end_authentication()
        return client.wallet

    with pytest.raises(RuntimeError, match="ended authentication"):
        asyncio.run(run())


def test_end_authentication_tolerates_401_on_delete() -> None:
    async def run() -> AsyncPublicClient:
        client = await _build_client()
        _install_secure_clob(client, _capture([], 401, {"error": "invalid"}))
        return await client.end_authentication()

    public = asyncio.run(run())

    assert isinstance(public, AsyncPublicClient)


def test_end_authentication_tolerates_404_on_delete() -> None:
    async def run() -> AsyncPublicClient:
        client = await _build_client()
        _install_secure_clob(client, _capture([], 404, {"error": "not found"}))
        return await client.end_authentication()

    public = asyncio.run(run())

    assert isinstance(public, AsyncPublicClient)


def test_end_authentication_propagates_unexpected_errors_from_delete() -> None:
    async def run() -> None:
        client = await _build_client()
        _install_secure_clob(client, _capture([], 500, {"error": "boom"}))
        await client.end_authentication()

    with pytest.raises(RequestRejectedError) as info:
        asyncio.run(run())
    assert info.value.status == 500


def test_end_authentication_marks_client_ended_even_when_delete_fails() -> None:
    async def run() -> AsyncSecureClient:
        client = await _build_client()
        _install_secure_clob(client, _capture([], 500, {"error": "boom"}))
        with contextlib.suppress(RequestRejectedError):
            await client.end_authentication()
        return client

    client = asyncio.run(run())

    assert client._ended is True


def test_close_after_end_authentication_does_not_raise() -> None:
    async def run() -> None:
        client = await _build_client()
        _install_secure_clob(client, _capture([], 200, {"revoked": True}))
        await client.end_authentication()
        await client.close()

    asyncio.run(run())
