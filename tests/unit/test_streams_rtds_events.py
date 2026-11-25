from datetime import UTC, datetime
from typing import Any

import pytest

from market_sdk.models.rtds_events import (
    CommentCreatedEvent,
    CommentRemovedEvent,
    ReactionCreatedEvent,
    parse_rtds_event,
)

_COMMENT_CREATED: dict[str, Any] = {
    "topic": "comments",
    "type": "comment_created",
    "timestamp": "1710000000000",
    "payload": {
        "id": "42",
        "body": "hi",
        "parentEntityType": "Event",
        "parentEntityID": 123,
        "userAddress": "0xabc",
        "createdAt": "2024-03-09T00:00:00Z",
    },
}

_REACTION_CREATED: dict[str, Any] = {
    "topic": "comments",
    "type": "reaction_created",
    "timestamp": "1710000000000",
    "payload": {
        "id": "7",
        "commentID": 42,
        "reactionType": "like",
        "userAddress": "0xdef",
    },
}


def test_comment_created_parses_with_camelcase_aliases() -> None:
    event = parse_rtds_event(_COMMENT_CREATED)
    assert isinstance(event, CommentCreatedEvent)
    assert event.topic == "comments"
    assert event.type == "comment_created"
    assert event.payload.id == "42"
    assert event.payload.parent_entity_type == "Event"
    assert event.payload.parent_entity_id == "123"
    assert event.payload.user_address == "0xabc"


def test_comment_removed_parses_full_payload_mirroring_ts() -> None:
    event = parse_rtds_event(
        {
            "topic": "comments",
            "type": "comment_removed",
            "timestamp": "1710000000000",
            "payload": {
                "id": "99",
                "body": "deleted body",
                "parentEntityType": "Event",
                "parentEntityID": 7,
                "parentCommentID": "pc-1",
                "userAddress": "0xabc",
                "replyAddress": "0xdef",
                "createdAt": "2024-03-09T00:00:00Z",
                "updatedAt": "2024-03-10T00:00:00Z",
                "reportCount": 2,
                "reactionCount": 5,
                "tradeAsset": "asset-1",
            },
        }
    )
    assert isinstance(event, CommentRemovedEvent)
    p = event.payload
    assert p.id == "99"
    assert p.body == "deleted body"
    assert p.parent_entity_type == "Event"
    assert p.parent_entity_id == 7  # noqa: PLR2004
    assert p.parent_comment_id == "pc-1"
    assert p.user_address == "0xabc"
    assert p.reply_address == "0xdef"
    assert p.created_at == datetime(2024, 3, 9, tzinfo=UTC)
    assert p.updated_at == datetime(2024, 3, 10, tzinfo=UTC)
    assert p.report_count == 2  # noqa: PLR2004
    assert p.reaction_count == 5  # noqa: PLR2004
    assert p.trade_asset == "asset-1"


def test_reaction_created_parses() -> None:
    event = parse_rtds_event(_REACTION_CREATED)
    assert isinstance(event, ReactionCreatedEvent)
    assert event.payload.comment_id == 42
    assert event.payload.reaction_type == "like"


@pytest.mark.parametrize(
    ("timestamp", "expected"),
    [
        (1710000000000, datetime.fromtimestamp(1710000000, tz=UTC)),
        ("1710000000000", datetime.fromtimestamp(1710000000, tz=UTC)),
        ("2024-03-09T12:00:00+00:00", datetime(2024, 3, 9, 12, tzinfo=UTC)),
        (None, None),
        ("", None),
    ],
)
def test_rtds_timestamp_preserves_accepted_inputs(
    timestamp: object, expected: datetime | None
) -> None:
    event = parse_rtds_event({**_COMMENT_CREATED, "timestamp": timestamp})

    assert event.timestamp == expected


@pytest.mark.parametrize("timestamp", [True, 1710000000000.0, b"1710000000000", "+1", "-1"])
def test_rtds_timestamp_preserves_rejected_inputs(timestamp: object) -> None:
    with pytest.raises(ValueError):
        parse_rtds_event({**_COMMENT_CREATED, "timestamp": timestamp})


def test_unknown_wire_topic_raises() -> None:
    with pytest.raises(ValueError, match="unknown RTDS wire topic"):
        parse_rtds_event({"topic": "made_up", "type": "update", "timestamp": "1", "payload": {}})


def test_unknown_event_type_raises() -> None:
    with pytest.raises(ValueError, match="unknown RTDS event"):
        parse_rtds_event({"topic": "comments", "type": "made_up", "timestamp": "1", "payload": {}})


def test_missing_topic_raises() -> None:
    with pytest.raises(ValueError, match="missing topic"):
        parse_rtds_event({"type": "update", "payload": {}})


def test_non_dict_raises() -> None:
    with pytest.raises(ValueError, match="expected dict"):
        parse_rtds_event("not a dict")
