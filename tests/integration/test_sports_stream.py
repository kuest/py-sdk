"""Live integration test for the Sports WebSocket stream."""

import asyncio

import pytest

from market_sdk import AsyncPublicClient
from market_sdk.environments import PRODUCTION
from market_sdk.streams import SportsSpec

# The server stale threshold is 30s; if pings/pongs aren't flowing both ways
# the watchdog force-closes inside this window. Sleeping past it proves the
# heartbeat is live without needing to inspect wire traffic.
_HEARTBEAT_OBSERVATION_S = 35.0


@pytest.mark.integration
def test_live_sports_stream_clean_shutdown() -> None:
    async def run() -> None:
        client = AsyncPublicClient(environment=PRODUCTION)
        try:
            async with await client.subscribe(SportsSpec()):
                await asyncio.sleep(0.5)
        finally:
            await client.close()

    asyncio.run(asyncio.wait_for(run(), timeout=15.0))


@pytest.mark.integration
def test_live_sports_stream_survives_past_heartbeat_stale_window() -> None:
    async def run() -> bool:
        client = AsyncPublicClient(environment=PRODUCTION)
        try:
            async with await client.subscribe(SportsSpec()):
                await asyncio.sleep(_HEARTBEAT_OBSERVATION_S)
                manager = client._sports_manager  # pyright: ignore[reportPrivateUsage]
                assert manager is not None
                return manager.is_open
        finally:
            await client.close()

    assert asyncio.run(asyncio.wait_for(run(), timeout=_HEARTBEAT_OBSERVATION_S + 10.0)) is True
