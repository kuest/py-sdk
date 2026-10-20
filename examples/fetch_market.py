"""Fetch a single market by slug and id.

    uv run python -m examples.fetch_market

No credentials required. Discovers a few live markets, then re-fetches them.
"""

from __future__ import annotations

from market_sdk import PublicClient


def main() -> None:
    with PublicClient() as client:
        items = client.list_markets(page_size=3).first_page().items
        if len(items) < 2:
            raise SystemExit("Not enough live markets to demo lookups.")

        slug0 = items[0].slug
        if slug0 is None:
            raise SystemExit("Discovered markets are missing slugs; try again.")

        by_slug = client.get_market(slug=slug0)
        by_id = client.get_market(id=str(items[1].id))

        print(f"Slug lookup: {by_slug.question or by_slug.id}")
        print(f"ID lookup:   {by_id.question or by_id.id}")


if __name__ == "__main__":
    main()
