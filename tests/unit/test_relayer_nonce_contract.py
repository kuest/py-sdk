import asyncio

import httpx
import pytest

from market_sdk._internal.actions.relayer.nonce import fetch_execute_params
from market_sdk.clients._transport import AsyncTransport
from market_sdk.errors import UserInputError
from market_sdk.models.clob.relayer import RelayerTransactionType


def test_wallet_nonce_uses_nonce_endpoint_and_query() -> None:
    observed: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        observed.append(request)
        return httpx.Response(200, json={"nonce": "7"}, request=request)

    async def run():
        relayer = AsyncTransport(
            base_url="https://relayer.test",
            client=httpx.AsyncClient(
                base_url="https://relayer.test", transport=httpx.MockTransport(handler)
            ),
        )
        try:
            return await fetch_execute_params(
                relayer,
                address="0x0000000000000000000000000000000000000001",
                type=RelayerTransactionType.WALLET,
            )
        finally:
            await relayer.close()

    params = asyncio.run(run())
    assert params.nonce == "7"
    assert observed[0].url.path == "/nonce"
    assert observed[0].url.params["address"] == "0x0000000000000000000000000000000000000001"
    assert observed[0].url.params["type"] == "WALLET"


def test_nonce_rejects_unsupported_relayer_type_before_network() -> None:
    async def run():
        relayer = AsyncTransport(base_url="https://relayer.test")
        try:
            await fetch_execute_params(
                relayer,
                address="0x0000000000000000000000000000000000000001",
                type=RelayerTransactionType.SAFE,
            )
        finally:
            await relayer.close()

    with pytest.raises(UserInputError, match="WALLET"):
        asyncio.run(run())
