"""Series models."""

from __future__ import annotations

from market_sdk.models.gamma.common import (
    CollectionReference,
    SeriesReference,
)
from market_sdk.models.gamma.event import Event
from market_sdk.models.gamma.tag import Tag


class Series(SeriesReference):
    events: tuple[Event, ...] | None = None
    collections: tuple[CollectionReference, ...] | None = None
    tags: tuple[Tag, ...] | None = None


__all__ = ["Series"]
