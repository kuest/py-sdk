import asyncio

import pytest

from market_sdk import AsyncPublicClient, PublicClient, Series

SERIES_ID = "39"


@pytest.mark.integration
def test_get_series_returns_series() -> None:
    with PublicClient() as client:
        series = client.get_series(SERIES_ID)

        assert isinstance(series, Series)
        assert series.id == SERIES_ID
        assert series.slug == "march-madness"
        assert series.title


@pytest.mark.integration
def test_async_get_series_returns_series() -> None:
    async def run() -> None:
        async with AsyncPublicClient() as client:
            series = await client.get_series(SERIES_ID)

            assert isinstance(series, Series)
            assert series.id == SERIES_ID
            assert series.slug == "march-madness"

    asyncio.run(run())
