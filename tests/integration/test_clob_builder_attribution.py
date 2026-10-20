import contextlib
from decimal import Decimal

import pytest

from market_sdk import AsyncSecureClient, Market
from market_sdk.models.clob.order_response import AcceptedOrder

pytestmark = pytest.mark.anyio


def _yes_token_id(market: Market) -> str:
    token_id = market.outcomes.yes.token_id
    assert token_id is not None
    return token_id


def _minimum_order_size(market: Market) -> Decimal:
    size = market.trading.minimum_order_size
    assert size is not None
    return size


def _minimum_tick_size(market: Market) -> Decimal:
    tick_size = market.trading.minimum_tick_size
    assert tick_size is not None
    return tick_size


@pytest.mark.integration
@pytest.mark.metered
async def test_get_builder_fee_rates_against_live_clob(
    builder_code: str,
    deposit_wallet_client: AsyncSecureClient,
) -> None:
    rates = await deposit_wallet_client.get_builder_fee_rates(builder_code)
    maker, taker = rates.maker, rates.taker
    assert maker >= Decimal(0)
    assert taker >= Decimal(0)
    assert maker < Decimal(1)
    assert taker < Decimal(1)


@pytest.mark.integration
@pytest.mark.metered
async def test_place_limit_order_with_builder_code_round_trips(
    builder_code: str,
    deposit_wallet_client: AsyncSecureClient,
    tradable_market: Market,
) -> None:
    token_id = _yes_token_id(tradable_market)
    price = _minimum_tick_size(tradable_market)
    size = _minimum_order_size(tradable_market)

    placed_id: str | None = None
    try:
        placed = await deposit_wallet_client.place_limit_order(
            token_id=token_id,
            price=price,
            size=size,
            side="BUY",
            builder_code=builder_code,
        )
        assert isinstance(placed, AcceptedOrder)
        placed_id = placed.order_id
    finally:
        if placed_id is not None:
            with contextlib.suppress(Exception):
                await deposit_wallet_client.cancel_order(order_id=placed_id)
