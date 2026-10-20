import asyncio

import pytest

from market_sdk import AsyncPublicClient, Market, PublicClient, TagReference
from market_sdk.errors import UnexpectedResponseError

MARKET_ID = "540816"
MARKET_SLUG = "russia-ukraine-ceasefire-before-gta-vi-554"
LEGACY_MULTI_OUTCOME_MARKET_SLUG = "who-will-the-world-s-richest-person-be-on-february-27-2021"


@pytest.mark.integration
def test_get_market_returns_canonical_market() -> None:
    with PublicClient() as client:
        market = client.get_market(id=MARKET_ID)

        assert isinstance(market, Market)
        assert market.id == MARKET_ID
        assert market.outcomes.yes.label
        assert market.outcomes.no.label
        assert market.outcomes.yes.token_id is not None
        assert market.outcomes.no.token_id is not None
        assert market.state.active is not None or market.state.closed is not None


@pytest.mark.integration
def test_get_market_by_slug_returns_canonical_market() -> None:
    with PublicClient() as client:
        market = client.get_market(slug=MARKET_SLUG)

        assert isinstance(market, Market)
        assert market.id == MARKET_ID
        assert market.outcomes.yes.label
        assert market.outcomes.no.label


@pytest.mark.integration
def test_get_market_by_url_returns_canonical_market() -> None:
    with PublicClient() as client:
        market = client.get_market(url=f"https://polymarket.com/market/{MARKET_SLUG}")

        assert isinstance(market, Market)
        assert market.id == MARKET_ID
        assert market.outcomes.yes.label
        assert market.outcomes.no.label


@pytest.mark.integration
def test_get_market_rejects_legacy_multi_outcome_market_with_typed_error() -> None:
    with PublicClient() as client, pytest.raises(UnexpectedResponseError):
        client.get_market(slug=LEGACY_MULTI_OUTCOME_MARKET_SLUG)


@pytest.mark.integration
def test_get_market_tags_returns_tags() -> None:
    with PublicClient() as client:
        tags = client.get_market_tags(MARKET_ID)

        assert tags
        assert all(isinstance(tag, TagReference) for tag in tags)
        assert any(tag.slug == "politics" for tag in tags)


@pytest.mark.integration
def test_async_get_market_returns_canonical_market() -> None:
    async def run() -> None:
        async with AsyncPublicClient() as client:
            market = await client.get_market(id=MARKET_ID)

            assert isinstance(market, Market)
            assert market.id == MARKET_ID
            assert market.outcomes.yes.label
            assert market.outcomes.no.label

    asyncio.run(run())
