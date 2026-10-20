import asyncio
import os
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager

import pytest

from market_sdk import ApiKeyCreds, AsyncSecureClient
from market_sdk.streams import UserSpec


def _existing_credentials() -> ApiKeyCreds | None:
    key = os.environ.get("POLYMARKET_TEST_API_KEY")
    secret = os.environ.get("POLYMARKET_TEST_API_SECRET")
    passphrase = os.environ.get("POLYMARKET_TEST_API_PASSPHRASE")
    if key and secret and passphrase:
        return ApiKeyCreds(key=key, secret=secret, passphrase=passphrase)
    return None


@asynccontextmanager
async def _secure_client(
    require_env: Callable[[str], str],
) -> AsyncGenerator[AsyncSecureClient, None]:
    private_key = require_env("POLYMARKET_PRIVATE_KEY")
    wallet = require_env("POLYMARKET_DEPOSIT_WALLET")
    client = await AsyncSecureClient.create(
        private_key=private_key,
        wallet=wallet,
        credentials=_existing_credentials(),
    )
    try:
        yield client
    finally:
        await client.close()


@pytest.mark.integration
@pytest.mark.metered
def test_live_user_clean_shutdown(require_env: Callable[[str], str]) -> None:
    async def run() -> None:
        async with _secure_client(require_env) as client:
            handle = await client.subscribe(UserSpec())
            async with handle:
                await asyncio.sleep(0.5)

    asyncio.run(asyncio.wait_for(run(), timeout=20.0))


@pytest.mark.integration
@pytest.mark.metered
def test_live_user_specific_markets_clean_shutdown(
    require_env: Callable[[str], str],
) -> None:
    async def run() -> None:
        async with _secure_client(require_env) as client:
            handle = await client.subscribe(UserSpec(markets=["0xnonexistent-market"]))
            async with handle:
                await asyncio.sleep(0.5)

    asyncio.run(asyncio.wait_for(run(), timeout=20.0))
