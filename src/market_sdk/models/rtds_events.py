from datetime import datetime
from typing import Any, Literal, cast

from pydantic import Field, TypeAdapter, field_validator

from market_sdk.models.base import BaseModel
from market_sdk.models.clob._validators import (
    _parse_epoch_ms_or_iso_timestamp,  # pyright: ignore[reportPrivateUsage]
)
from market_sdk.models.gamma.comment import (
    Comment,
    CommentMedia,
    CommentProfile,
    Reaction,
)
from market_sdk.models.gamma.common import parse_optional_datetime

_WIRE_TO_API_TOPIC = {"comments": "comments"}
_API_TO_WIRE_TOPIC = {"comments": "comments"}


def wire_topic_to_api(wire: str) -> str | None:
    return _WIRE_TO_API_TOPIC.get(wire)


def api_topic_to_wire(api: str) -> str:
    return _API_TO_WIRE_TOPIC[api]


class CommentRemovedPayload(BaseModel):
    id: str
    body: str | None = None
    parent_entity_type: Literal["Event", "Market"] | None = Field(
        default=None, validation_alias="parentEntityType"
    )
    parent_entity_id: int | None = Field(default=None, validation_alias="parentEntityID")
    parent_comment_id: str | None = Field(default=None, validation_alias="parentCommentID")
    user_address: str | None = Field(default=None, validation_alias="userAddress")
    reply_address: str | None = Field(default=None, validation_alias="replyAddress")
    created_at: datetime | None = Field(default=None, validation_alias="createdAt")
    updated_at: datetime | None = Field(default=None, validation_alias="updatedAt")
    media: tuple[CommentMedia, ...] | None = None
    profile: CommentProfile | None = None
    reactions: tuple[Reaction, ...] | None = None
    report_count: int | None = Field(default=None, validation_alias="reportCount")
    reaction_count: int | None = Field(default=None, validation_alias="reactionCount")
    trade_asset: str | None = Field(default=None, validation_alias="tradeAsset")

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _parse_datetime(cls, value: object) -> datetime | None:
        return parse_optional_datetime(value)


class CommentCreatedEvent(BaseModel):
    topic: Literal["comments"] = "comments"
    type: Literal["comment_created"]
    timestamp: datetime | None
    payload: Comment

    @field_validator("timestamp", mode="before")
    @classmethod
    def _parse_timestamp(cls, value: object) -> object:
        return _parse_epoch_ms_or_iso_timestamp(value)


class CommentRemovedEvent(BaseModel):
    topic: Literal["comments"] = "comments"
    type: Literal["comment_removed"]
    timestamp: datetime | None
    payload: CommentRemovedPayload

    @field_validator("timestamp", mode="before")
    @classmethod
    def _parse_timestamp(cls, value: object) -> object:
        return _parse_epoch_ms_or_iso_timestamp(value)


class ReactionCreatedEvent(BaseModel):
    topic: Literal["comments"] = "comments"
    type: Literal["reaction_created"]
    timestamp: datetime | None
    payload: Reaction

    @field_validator("timestamp", mode="before")
    @classmethod
    def _parse_timestamp(cls, value: object) -> object:
        return _parse_epoch_ms_or_iso_timestamp(value)


class ReactionRemovedEvent(BaseModel):
    topic: Literal["comments"] = "comments"
    type: Literal["reaction_removed"]
    timestamp: datetime | None
    payload: Reaction

    @field_validator("timestamp", mode="before")
    @classmethod
    def _parse_timestamp(cls, value: object) -> object:
        return _parse_epoch_ms_or_iso_timestamp(value)


CommentsEvent = (
    CommentCreatedEvent | CommentRemovedEvent | ReactionCreatedEvent | ReactionRemovedEvent
)


RtdsEvent = CommentsEvent


_RTDS_VARIANTS: dict[tuple[str, str], type[BaseModel]] = {
    ("comments", "comment_created"): CommentCreatedEvent,
    ("comments", "comment_removed"): CommentRemovedEvent,
    ("comments", "reaction_created"): ReactionCreatedEvent,
    ("comments", "reaction_removed"): ReactionRemovedEvent,
}

_TYPE_ADAPTERS: dict[tuple[str, str], TypeAdapter[Any]] = {
    key: TypeAdapter(model) for key, model in _RTDS_VARIANTS.items()
}


def parse_rtds_event(raw: object) -> RtdsEvent:
    if not isinstance(raw, dict):
        msg = f"expected dict, got {type(raw).__name__}"
        raise ValueError(msg)
    wire = cast(dict[str, Any], raw)
    topic_raw = wire.get("topic")
    type_raw = wire.get("type")
    if not isinstance(topic_raw, str) or not isinstance(type_raw, str):
        msg = "RTDS event missing topic/type"
        raise ValueError(msg)
    api_topic = wire_topic_to_api(topic_raw)
    if api_topic is None:
        msg = f"unknown RTDS wire topic: {topic_raw!r}"
        raise ValueError(msg)
    key = (api_topic, type_raw)
    adapter = _TYPE_ADAPTERS.get(key)
    if adapter is None:
        msg = f"unknown RTDS event: topic={api_topic!r}, type={type_raw!r}"
        raise ValueError(msg)
    normalized = {**wire, "topic": api_topic}
    return cast(RtdsEvent, adapter.validate_python(normalized))


__all__ = [
    "Comment",
    "CommentCreatedEvent",
    "CommentMedia",
    "CommentProfile",
    "CommentRemovedEvent",
    "CommentRemovedPayload",
    "CommentsEvent",
    "Reaction",
    "ReactionCreatedEvent",
    "ReactionRemovedEvent",
    "RtdsEvent",
    "api_topic_to_wire",
    "parse_rtds_event",
    "wire_topic_to_api",
]
