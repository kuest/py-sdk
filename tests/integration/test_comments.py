import asyncio

import pytest

from market_sdk import AsyncPublicClient, Comment, PublicClient

COMMENT_ID = "1000"


@pytest.mark.integration
def test_get_comment_thread_returns_comments() -> None:
    with PublicClient() as client:
        comments = client.get_comment_thread(COMMENT_ID)

        assert comments
        assert all(isinstance(comment, Comment) for comment in comments)
        root = comments[0]
        assert root.user_address is not None
        assert root.user_address.startswith("0x")


@pytest.mark.integration
def test_async_get_comment_thread_returns_comments() -> None:
    async def run() -> None:
        async with AsyncPublicClient() as client:
            comments = await client.get_comment_thread(COMMENT_ID)

            assert comments
            assert all(isinstance(comment, Comment) for comment in comments)

    asyncio.run(run())
