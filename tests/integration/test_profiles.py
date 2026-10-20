import asyncio

import pytest

from market_sdk import AsyncPublicClient, PublicClient, PublicProfile

PROFILE_ADDRESS = "0x0000000000000000000000000000000000000000"


@pytest.mark.integration
def test_get_public_profile_returns_profile() -> None:
    with PublicClient() as client:
        profile = client.get_public_profile(PROFILE_ADDRESS)

        assert isinstance(profile, PublicProfile)
        assert profile.wallet == PROFILE_ADDRESS
        assert profile.wallet is not None and profile.wallet.startswith("0x")


@pytest.mark.integration
def test_async_get_public_profile_returns_profile() -> None:
    async def run() -> None:
        async with AsyncPublicClient() as client:
            profile = await client.get_public_profile(PROFILE_ADDRESS)

            assert isinstance(profile, PublicProfile)
            assert profile.wallet == PROFILE_ADDRESS

    asyncio.run(run())
