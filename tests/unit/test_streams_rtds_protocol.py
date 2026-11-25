from market_sdk._internal.streams.rtds.protocol import (
    derive_state,
    matcher_for,
    server_subscriptions_for,
)
from market_sdk.models.rtds_events import RtdsEvent, parse_rtds_event
from market_sdk.streams._specs import (
    CommentsSpec,
)


def test_comments_defaults_to_comment_created_only_when_unspecified() -> None:
    srvs = server_subscriptions_for(CommentsSpec())
    assert {s.type for s in srvs} == {"comment_created"}
    assert all(s.topic == "comments" for s in srvs)


def test_comments_expands_only_requested_types() -> None:
    srvs = server_subscriptions_for(CommentsSpec(types=["comment_created", "reaction_created"]))
    assert {s.type for s in srvs} == {"comment_created", "reaction_created"}


def test_comments_all_four_types_when_explicitly_requested() -> None:
    srvs = server_subscriptions_for(
        CommentsSpec(
            types=["comment_created", "comment_removed", "reaction_created", "reaction_removed"]
        )
    )
    assert {s.type for s in srvs} == {
        "comment_created",
        "comment_removed",
        "reaction_created",
        "reaction_removed",
    }


def test_dedup_keeps_distinct_comment_types() -> None:
    state = derive_state(
        [
            CommentsSpec(types=["comment_created"]),
            CommentsSpec(types=["reaction_created"]),
        ]
    )
    assert set(state.keys()) == {"comments:comment_created", "comments:reaction_created"}


def _comment_created(parent_entity_id: int = 1, parent_entity_type: str = "Event") -> RtdsEvent:
    return parse_rtds_event(
        {
            "topic": "comments",
            "type": "comment_created",
            "timestamp": "1710000000000",
            "payload": {
                "id": "1",
                "body": "hi",
                "parentEntityType": parent_entity_type,
                "parentEntityID": parent_entity_id,
            },
        }
    )


def _reaction_created() -> RtdsEvent:
    return parse_rtds_event(
        {
            "topic": "comments",
            "type": "reaction_created",
            "timestamp": "1710000000000",
            "payload": {"id": "1", "commentID": 99},
        }
    )


def test_comments_matcher_filters_by_type() -> None:
    matches = matcher_for(CommentsSpec(types=["comment_created"]))
    assert matches(_comment_created()) is True
    assert matches(_reaction_created()) is False


def test_default_commentsspec_matcher_drops_non_default_types() -> None:
    matches = matcher_for(CommentsSpec())
    assert matches(_comment_created()) is True
    assert matches(_reaction_created()) is False


def _comment_removed(parent_entity_id: int = 1, parent_entity_type: str = "Event") -> RtdsEvent:
    return parse_rtds_event(
        {
            "topic": "comments",
            "type": "comment_removed",
            "timestamp": "1710000000000",
            "payload": {
                "id": "99",
                "parentEntityType": parent_entity_type,
                "parentEntityID": parent_entity_id,
            },
        }
    )


def test_comments_parent_filter_matches_removed_event_with_int_parent_id() -> None:
    matches = matcher_for(CommentsSpec(types=["comment_removed"], parent_entity_id=1))
    assert matches(_comment_removed(parent_entity_id=1)) is True
    assert matches(_comment_removed(parent_entity_id=2)) is False


def test_comments_parent_filter_drops_reactions_without_parent_context() -> None:
    matches = matcher_for(CommentsSpec(parent_entity_id=1, parent_entity_type="Event"))
    assert matches(_comment_created(parent_entity_id=1, parent_entity_type="Event")) is True
    assert matches(_reaction_created()) is False


def test_comments_parent_filter_rejects_non_matching_parent() -> None:
    matches = matcher_for(CommentsSpec(parent_entity_id=1))
    assert matches(_comment_created(parent_entity_id=2)) is False
