"""Search events, tags, and profiles.

    uv run python -m examples.search

No credentials required.
"""

from __future__ import annotations

from examples.lib.tables import print_rows_table
from market_sdk import PublicClient


def main() -> None:
    with PublicClient() as client:
        page = client.search(
            q="ethereum",
            search_tags=True,
            search_profiles=True,
            page_size=3,
        ).first_page()
        # Search returns a single results payload (events/tags/profiles) per page.
        if not page.items:
            raise SystemExit("No search results returned.")
        results = page.items[0]

        print("Events")
        print_rows_table(
            [
                {"id": event.id, "title": event.title or event.slug or "Untitled event"}
                for event in results.events
            ]
        )

        print("\nTags")
        print_rows_table(
            [
                {"id": tag.id, "label": tag.label or tag.slug or "Untitled tag"}
                for tag in results.tags
            ]
        )

        print("\nProfiles")
        print_rows_table(
            [
                {
                    "id": profile.id or "profile",
                    "name": profile.name or profile.wallet or "Unnamed profile",
                }
                for profile in results.profiles
            ]
        )


if __name__ == "__main__":
    main()
