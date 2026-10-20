"""Walk multiple pages of a list endpoint.

    uv run python -m examples.pagination

No credentials required. Iterating a Paginator yields whole pages; iterating
`.iter_items()` would yield individual items across pages.
"""

from __future__ import annotations

from market_sdk import PublicClient


def main() -> None:
    with PublicClient() as client:
        markets = client.list_markets(page_size=5)

        for page_count, page in enumerate(markets, start=1):  # iterating yields pages
            print(f"Page {page_count}")
            for market in page.items:
                print(f"  {market.id}: {market.question or 'Untitled market'}")
            if page_count == 3:
                break


if __name__ == "__main__":
    main()
