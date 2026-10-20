import asyncio

import pytest

from market_sdk import AsyncPublicClient, PublicClient, RelatedTag, Tag

TAG_ID = "100215"


@pytest.mark.integration
def test_get_tag_returns_tag() -> None:
    with PublicClient() as client:
        tag = client.get_tag(id=TAG_ID)

        assert isinstance(tag, Tag)
        assert tag.id == TAG_ID
        assert tag.slug == "all"
        assert tag.label is not None


@pytest.mark.integration
def test_get_related_tags_returns_relationships() -> None:
    with PublicClient() as client:
        related_tags = client.get_related_tags(id=TAG_ID, omit_empty=True)

        assert related_tags
        assert all(isinstance(tag, RelatedTag) for tag in related_tags)


@pytest.mark.integration
def test_get_related_tag_resources_returns_tags() -> None:
    with PublicClient() as client:
        tags = client.get_related_tag_resources(id=TAG_ID, omit_empty=True)

        assert tags
        assert all(isinstance(tag, Tag) for tag in tags)


@pytest.mark.integration
def test_async_get_tag_returns_tag() -> None:
    async def run() -> None:
        async with AsyncPublicClient() as client:
            tag = await client.get_tag(id=TAG_ID)

            assert isinstance(tag, Tag)
            assert tag.id == TAG_ID
            assert tag.slug == "all"

    asyncio.run(run())


@pytest.mark.integration
def test_async_get_related_tags_returns_relationships() -> None:
    async def run() -> None:
        async with AsyncPublicClient() as client:
            related_tags = await client.get_related_tags(id=TAG_ID, omit_empty=True)

            assert related_tags
            assert all(isinstance(tag, RelatedTag) for tag in related_tags)

    asyncio.run(run())


@pytest.mark.integration
def test_async_get_related_tag_resources_returns_tags() -> None:
    async def run() -> None:
        async with AsyncPublicClient() as client:
            tags = await client.get_related_tag_resources(id=TAG_ID, omit_empty=True)

            assert tags
            assert all(isinstance(tag, Tag) for tag in tags)

    asyncio.run(run())
