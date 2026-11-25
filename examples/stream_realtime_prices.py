"""Stream public reference prices from explicitly configured operator endpoints."""

import asyncio
import os

from market_sdk import AsyncPublicClient, configured_environment
from market_sdk.streams import CryptoPriceSpec


async def main() -> None:
    environment = configured_environment(
        clob_url=os.environ["SDK_CLOB_URL"],
        clob_ws_url=os.environ["SDK_CLOB_WS_URL"],
        relayer_url=os.environ["SDK_RELAYER_URL"],
        gamma_url=os.environ["SDK_GAMMA_URL"],
        data_url=os.environ["SDK_DATA_URL"],
        rpc_url=os.environ["SDK_RPC_URL"],
        realtime_ws_url=os.environ["SDK_LIVE_DATA_WS_URL"],
    )
    async with (
        AsyncPublicClient(environment=environment) as client,
        await client.subscribe(CryptoPriceSpec(symbols=["btcusd"])) as prices,
    ):
        async for event in prices:
            print(event)


if __name__ == "__main__":
    asyncio.run(main())
