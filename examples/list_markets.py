"""List the first page of markets.

    uv run python -m examples.list_markets

No credentials required.
"""

from __future__ import annotations

from market_sdk import PublicClient


def main() -> None:
    with PublicClient() as client:
        # List methods return a Paginator; `.first_page()` fetches just the first page.
        page = client.list_markets(page_size=5).first_page()
        for market in page.items:
            print(f"{market.id}: {market.question or market.slug or 'Untitled market'}")


if __name__ == "__main__":
    main()
