"""Live integration test for the CLOB market WebSocket stream."""

import asyncio
from typing import Any, cast

import pytest

from market_sdk import AsyncPublicClient
from market_sdk.environments import PRODUCTION
from market_sdk.streams import MarketEvent, MarketSpec

_DISCOVERY_LIMIT = 25
_EVENT_TIMEOUT_S = 30.0


async def _discover_token_ids() -> tuple[str, str]:
    async with AsyncPublicClient(environment=PRODUCTION) as client:
        paginator = client.list_markets(
            closed=False,
            order="volume24hr",
            ascending=False,
            page_size=_DISCOVERY_LIMIT,
        )
        page = await paginator.first_page()
        for market in page.items:
            outcomes = cast(Any, market).outcomes
            yes_token = outcomes.yes.token_id if outcomes.yes else None
            no_token = outcomes.no.token_id if outcomes.no else None
            if yes_token and no_token:
                return str(yes_token), str(no_token)
    pytest.skip("no active market with token ids discoverable from gamma")


@pytest.mark.integration
def test_live_market_stream_delivers_an_event() -> None:
    async def run() -> MarketEvent:
        yes_token, no_token = await _discover_token_ids()
        client = AsyncPublicClient(environment=PRODUCTION)
        try:
            async with await client.subscribe(
                MarketSpec(token_ids=[yes_token, no_token])
            ) as stream:
                async for event in stream:
                    return event
        finally:
            await client.close()
        raise AssertionError("stream closed before any event arrived")

    event = asyncio.run(asyncio.wait_for(run(), timeout=_EVENT_TIMEOUT_S + 5.0))
    # The discriminated union enforces it's one of the known variants.
    assert hasattr(event, "type")
    assert event.type in {
        "book",
        "price_change",
        "last_trade_price",
        "tick_size_change",
    }


@pytest.mark.integration
def test_live_market_stream_clean_shutdown() -> None:
    async def run() -> None:
        yes_token, _no_token = await _discover_token_ids()
        client = AsyncPublicClient(environment=PRODUCTION)
        handle = await client.subscribe(MarketSpec(token_ids=[yes_token]))
        await asyncio.sleep(0.5)
        await handle.close()
        await client.close()

    asyncio.run(asyncio.wait_for(run(), timeout=15.0))
