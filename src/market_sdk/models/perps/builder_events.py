"""Experimental builder receipts; may change in any release, including patches."""

from datetime import datetime
from typing import Literal

from pydantic import field_validator

from market_sdk.models.base import BaseModel
from market_sdk.models.perps._validators import _require_epoch_ms
from market_sdk.models.perps.builders import PerpsBuilderEarning


class PerpsBuilderFillEvent(BaseModel):
    """Experimental: a batch of builder receipts; sequence numbers may skip values."""

    type: Literal["builder_fill"] = "builder_fill"
    channel: Literal["builderFills"] = "builderFills"
    timestamp: datetime
    sequence: int
    payload: tuple[PerpsBuilderEarning, ...]

    @field_validator("timestamp", mode="before")
    @classmethod
    def _timestamp(cls, value: object) -> object:
        return _require_epoch_ms(value)
