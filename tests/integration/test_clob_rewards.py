import asyncio
import os
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import pytest

from market_sdk import (
    ApiKeyCreds,
    AsyncPublicClient,
    AsyncSecureClient,
    CurrentReward,
    MarketReward,
    RewardsPercentages,
    TotalUserEarning,
    UserEarning,
    UserRewardsEarning,
)


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


def _yesterday_iso() -> str:
    return (datetime.now(tz=UTC) - timedelta(days=1)).strftime("%Y-%m-%d")


@pytest.mark.integration
def test_list_current_rewards_returns_reward_models() -> None:
    async def run() -> tuple[CurrentReward, ...]:
        async with AsyncPublicClient() as client:
            page = await client.list_current_rewards().first_page()
            return page.items

    items = asyncio.run(run())
    for item in items:
        assert isinstance(item, CurrentReward)


@pytest.mark.integration
def test_list_market_rewards_for_first_active_reward_market() -> None:
    async def run() -> tuple[MarketReward, ...]:
        async with AsyncPublicClient() as client:
            current = await client.list_current_rewards().first_page()
            if not current.items:
                pytest.skip("no active reward markets to query")
            condition_id = current.items[0].condition_id
            page = await client.list_market_rewards(condition_id=condition_id).first_page()
            return page.items

    items = asyncio.run(run())
    for item in items:
        assert isinstance(item, MarketReward)


@pytest.mark.integration
@pytest.mark.metered
def test_get_order_scoring_returns_bool_for_arbitrary_order_id(
    require_env: Callable[[str], str],
) -> None:
    async def run() -> bool:
        async with _secure_client(require_env) as client:
            return await client.get_order_scoring(
                order_id="0x0000000000000000000000000000000000000000000000000000000000000001"
            )

    result = asyncio.run(run())
    assert isinstance(result, bool)


@pytest.mark.integration
@pytest.mark.metered
def test_get_orders_scoring_returns_dict(
    require_env: Callable[[str], str],
) -> None:
    async def run() -> dict[str, bool]:
        async with _secure_client(require_env) as client:
            return await client.get_orders_scoring(
                order_ids=[
                    "0x0000000000000000000000000000000000000000000000000000000000000001",
                    "0x0000000000000000000000000000000000000000000000000000000000000002",
                ]
            )

    result = asyncio.run(run())
    assert isinstance(result, dict)
    for key, value in result.items():
        assert isinstance(key, str)
        assert isinstance(value, bool)


@pytest.mark.integration
@pytest.mark.metered
def test_list_user_earnings_for_day_returns_paginator_models(
    require_env: Callable[[str], str],
) -> None:
    async def run() -> tuple[UserEarning, ...]:
        async with _secure_client(require_env) as client:
            page = await client.list_user_earnings_for_day(date=_yesterday_iso()).first_page()
            return page.items

    items = asyncio.run(run())
    for item in items:
        assert isinstance(item, UserEarning)


@pytest.mark.integration
@pytest.mark.metered
def test_get_total_earnings_for_user_for_day_returns_tuple(
    require_env: Callable[[str], str],
) -> None:
    async def run() -> tuple[TotalUserEarning, ...]:
        async with _secure_client(require_env) as client:
            return await client.get_total_earnings_for_user_for_day(date=_yesterday_iso())

    items = asyncio.run(run())
    assert isinstance(items, tuple)
    for item in items:
        assert isinstance(item, TotalUserEarning)


@pytest.mark.integration
@pytest.mark.metered
def test_list_user_earnings_and_markets_config_returns_models(
    require_env: Callable[[str], str],
) -> None:
    async def run() -> tuple[UserRewardsEarning, ...]:
        async with _secure_client(require_env) as client:
            page = await client.list_user_earnings_and_markets_config(
                date=_yesterday_iso()
            ).first_page()
            return page.items

    items = asyncio.run(run())
    for item in items:
        assert isinstance(item, UserRewardsEarning)


@pytest.mark.integration
@pytest.mark.metered
def test_get_reward_percentages_returns_dict_of_floats(
    require_env: Callable[[str], str],
) -> None:
    async def run() -> RewardsPercentages:
        async with _secure_client(require_env) as client:
            return await client.get_reward_percentages()

    result = asyncio.run(run())
    assert isinstance(result, dict)
    for key, value in result.items():
        assert isinstance(key, str)
        assert isinstance(value, float)
