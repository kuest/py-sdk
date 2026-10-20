import asyncio

import pytest

from market_sdk import AsyncPublicClient, Event, PublicClient, TagReference
from market_sdk.models.gamma import EventState

EVENT_ID = "902661"


@pytest.mark.integration
def test_get_event_returns_event() -> None:
    with PublicClient() as client:
        event = client.get_event(id=EVENT_ID)

        assert isinstance(event, Event)
        assert event.id == EVENT_ID
        assert event.slug == "did-israeli-intelligence-have-advanced-knowledge-of-the-attack"
        assert event.markets
        assert isinstance(event.state, EventState)
        first_market = event.markets[0]
        assert first_market.outcomes.yes.label
        assert first_market.outcomes.no.label


@pytest.mark.integration
def test_get_event_tags_returns_tags() -> None:
    with PublicClient() as client:
        tags = client.get_event_tags(EVENT_ID)

        assert tags
        assert all(isinstance(tag, TagReference) for tag in tags)


@pytest.mark.integration
def test_async_get_event_returns_event() -> None:
    async def run() -> None:
        async with AsyncPublicClient() as client:
            event = await client.get_event(id=EVENT_ID)

            assert isinstance(event, Event)
            assert event.id == EVENT_ID

    asyncio.run(run())


@pytest.mark.integration
def test_async_get_event_tags_returns_tags() -> None:
    async def run() -> None:
        async with AsyncPublicClient() as client:
            tags = await client.get_event_tags(EVENT_ID)

            assert tags
            assert all(isinstance(tag, TagReference) for tag in tags)

    asyncio.run(run())
