from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from market_sdk.models.rtds_events import (
    ReactionCreatedEvent,
    ReactionRemovedEvent,
    RtdsEvent,
)
from market_sdk.streams._specs import (
    CommentsSpec,
    RtdsSpec,
)

_DEFAULT_COMMENT_TYPES: tuple[str, ...] = ("comment_created",)


@dataclass(frozen=True, slots=True)
class RtdsServerSubscription:
    topic: str
    type: str

    @property
    def key(self) -> str:
        return f"{self.topic}:{self.type}"


def server_subscriptions_for(spec: RtdsSpec) -> tuple[RtdsServerSubscription, ...]:
    types = spec.types if spec.types else _DEFAULT_COMMENT_TYPES
    return tuple(RtdsServerSubscription(topic="comments", type=t) for t in types)


def derive_state(subs: Iterable[RtdsSpec]) -> dict[str, RtdsServerSubscription]:
    state: dict[str, RtdsServerSubscription] = {}
    for sub in subs:
        for srv in server_subscriptions_for(sub):
            state.setdefault(srv.key, srv)
    return state


def build_subscribe_frame(subscriptions: Iterable[RtdsServerSubscription]) -> dict[str, Any]:
    return {
        "action": "subscribe",
        "subscriptions": [{"topic": s.topic, "type": s.type} for s in subscriptions],
    }


def build_unsubscribe_frame(subscriptions: Iterable[RtdsServerSubscription]) -> dict[str, Any]:
    return {
        "action": "unsubscribe",
        "subscriptions": [{"topic": s.topic, "type": s.type} for s in subscriptions],
    }


def diff_state_frames(
    before: dict[str, RtdsServerSubscription],
    after: dict[str, RtdsServerSubscription],
) -> list[dict[str, Any]]:
    added = [s for k, s in after.items() if k not in before]
    removed = [s for k, s in before.items() if k not in after]
    frames: list[dict[str, Any]] = []
    if added:
        frames.append(build_subscribe_frame(added))
    if removed:
        frames.append(build_unsubscribe_frame(removed))
    return frames


def matcher_for(spec: RtdsSpec) -> Callable[[RtdsEvent], bool]:
    return _comments_matcher(spec)


def _comments_matcher(spec: CommentsSpec) -> Callable[[RtdsEvent], bool]:
    allowed_types = frozenset(spec.types or _DEFAULT_COMMENT_TYPES)
    parent_id = spec.parent_entity_id
    parent_id_str = str(parent_id) if parent_id is not None else None
    parent_type = spec.parent_entity_type
    needs_parent_check = parent_id is not None or parent_type is not None

    def matches(event: RtdsEvent) -> bool:
        if event.type not in allowed_types:
            return False
        if not needs_parent_check:
            return True
        if isinstance(event, ReactionCreatedEvent | ReactionRemovedEvent):
            return False
        payload = event.payload
        if parent_id_str is not None:
            payload_parent = payload.parent_entity_id
            if payload_parent is None or str(payload_parent) != parent_id_str:
                return False
        return not (parent_type is not None and payload.parent_entity_type != parent_type)

    return matches
