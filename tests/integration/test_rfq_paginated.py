import asyncio

import pytest

from market_sdk import AsyncPublicClient, ComboMarket, PublicClient


@pytest.mark.integration
def test_list_combo_markets_returns_paginator() -> None:
    with PublicClient() as client:
        paginator = client.list_combo_markets(page_size=1)
        first = paginator.first_page()

        assert first.items
        assert all(isinstance(market, ComboMarket) for market in first.items)
        market = first.items[0]
        assert market.outcomes.yes.position_id
        assert market.outcomes.no.position_id


@pytest.mark.integration
def test_async_list_combo_markets_returns_paginator() -> None:
    async def run() -> None:
        async with AsyncPublicClient() as client:
            paginator = client.list_combo_markets(page_size=1)
            first = await paginator.first_page()

            assert first.items
            assert all(isinstance(market, ComboMarket) for market in first.items)
            market = first.items[0]
            assert market.outcomes.yes.position_id
            assert market.outcomes.no.position_id

    asyncio.run(run())
