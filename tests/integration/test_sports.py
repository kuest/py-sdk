import asyncio

import pytest

from market_sdk import AsyncPublicClient, PublicClient, SportsMarketTypes, SportsMetadata


@pytest.mark.integration
def test_get_sports_returns_sports_metadata() -> None:
    with PublicClient() as client:
        sports = client.get_sports()

        assert sports
        assert all(isinstance(sport, SportsMetadata) for sport in sports)
        first = sports[0]
        assert first.sport
        assert isinstance(first.id, int)


@pytest.mark.integration
def test_get_sports_market_types_returns_market_types() -> None:
    with PublicClient() as client:
        market_types = client.get_sports_market_types()

        assert isinstance(market_types, SportsMarketTypes)
        assert market_types.market_types


@pytest.mark.integration
def test_async_get_sports_returns_sports_metadata() -> None:
    async def run() -> None:
        async with AsyncPublicClient() as client:
            sports = await client.get_sports()

            assert sports
            assert all(isinstance(sport, SportsMetadata) for sport in sports)

    asyncio.run(run())


@pytest.mark.integration
def test_async_get_sports_market_types_returns_market_types() -> None:
    async def run() -> None:
        async with AsyncPublicClient() as client:
            market_types = await client.get_sports_market_types()

            assert isinstance(market_types, SportsMarketTypes)
            assert market_types.market_types

    asyncio.run(run())
