"""Market clarification models."""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import Field, field_validator

from market_sdk.models.base import BaseModel
from market_sdk.models.gamma.common import parse_optional_datetime
from market_sdk.models.types import ConditionId, EventId, MarketId, QuestionId, ResolutionRequestId
from market_sdk.types import EvmAddress, TransactionHash


class MarketClarificationState(StrEnum):
    """Publication state of a market clarification."""

    PENDING = "pending"
    QUEUED = "queued"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MarketClarification(BaseModel):
    """Published note explaining how a market settles."""

    id: int
    market_id: MarketId | None = Field(validation_alias="marketId")
    condition_id: ConditionId | None = Field(default=None, validation_alias="conditionId")
    event_id: EventId = Field(validation_alias="eventId")
    question_id: QuestionId | None = Field(validation_alias="questionId")
    content: str
    state: MarketClarificationState
    show_in_frontend: bool = Field(validation_alias="showInFrontend")
    clear_book: bool | None = Field(
        default=None,
        validation_alias="clearBook",
        description="Whether the source cleared its open orders; does not cancel orders.",
    )
    source: Literal["kuest", "polymarket"] | None = None
    source_market_id: MarketId | None = Field(default=None, validation_alias="sourceMarketId")
    source_event_id: EventId | None = Field(default=None, validation_alias="sourceEventId")
    source_question_id: QuestionId | None = Field(default=None, validation_alias="sourceQuestionId")
    notify_discord: bool | None = Field(default=None, validation_alias="notifyDiscord")
    adapter_address: EvmAddress | None = Field(default=None, validation_alias="adapterAddress")
    neg_risk_request_id: ResolutionRequestId | None = Field(
        default=None, validation_alias="negRiskRequestId"
    )
    tx_hash: TransactionHash | None = Field(default=None, validation_alias="txHash")
    tx_timestamp: datetime | None = Field(default=None, validation_alias="txTimestamp")
    created_at: datetime | None = Field(default=None, validation_alias="createdAt")
    queued_at: datetime | None = Field(default=None, validation_alias="queuedAt")
    scheduled_for: datetime | None = Field(default=None, validation_alias="scheduledFor")

    @field_validator("market_id", "event_id", "source_market_id", "source_event_id", mode="before")
    @classmethod
    def _coerce_ids(cls, value: object) -> object:
        return str(value) if type(value) is int else value

    @field_validator("tx_timestamp", "created_at", "queued_at", "scheduled_for", mode="before")
    @classmethod
    def _parse_datetime(cls, value: object) -> datetime | None:
        return parse_optional_datetime(value)
