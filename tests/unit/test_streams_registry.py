# pyright: reportPrivateUsage=false
import asyncio
from collections.abc import Iterable
from dataclasses import dataclass

from market_sdk._internal.streams.handle import AsyncSubscriptionHandle
from market_sdk._internal.streams.registry import SubscriptionRegistry


@dataclass(frozen=True)
class _Sub:
    label: str


@dataclass(frozen=True)
class _Event:
    label: str


@dataclass(frozen=True)
class _State:
    labels: tuple[str, ...]


def _derive(subs: Iterable[_Sub]) -> _State:
    return _State(labels=tuple(sorted(s.label for s in subs)))


def _make_handle() -> AsyncSubscriptionHandle[_Event]:
    return AsyncSubscriptionHandle(queue_size=16)


def test_registry_starts_empty() -> None:
    reg: SubscriptionRegistry[_Sub, _Event, _State] = SubscriptionRegistry(derive_state=_derive)
    assert reg.is_empty is True
    assert reg.server_state() == _State(labels=())


def test_add_and_remove_handle_updates_server_state() -> None:
    reg: SubscriptionRegistry[_Sub, _Event, _State] = SubscriptionRegistry(derive_state=_derive)
    h1 = _make_handle()
    h2 = _make_handle()
    reg.add(sub=_Sub("a"), matcher=lambda _e: True, handle=h1)
    reg.add(sub=_Sub("b"), matcher=lambda _e: True, handle=h2)
    assert reg.server_state() == _State(labels=("a", "b"))
    assert reg.remove_handle(h1) is True
    assert reg.server_state() == _State(labels=("b",))
    assert reg.remove_handle(h1) is False


def test_dispatch_routes_via_matcher() -> None:
    reg: SubscriptionRegistry[_Sub, _Event, _State] = SubscriptionRegistry(derive_state=_derive)
    h_match = _make_handle()
    h_skip = _make_handle()
    reg.add(sub=_Sub("a"), matcher=lambda e: e.label == "yes", handle=h_match)
    reg.add(sub=_Sub("b"), matcher=lambda _e: False, handle=h_skip)
    reg.dispatch(_Event("yes"))
    reg.dispatch(_Event("no"))

    async def collect(h: AsyncSubscriptionHandle[_Event]) -> list[_Event]:
        h._end()
        items: list[_Event] = []
        async for e in h:
            items.append(e)
        return items

    assert asyncio.run(collect(h_match)) == [_Event("yes")]
    assert asyncio.run(collect(h_skip)) == []


def test_dispatch_swallows_matcher_exception_and_continues() -> None:
    reg: SubscriptionRegistry[_Sub, _Event, _State] = SubscriptionRegistry(derive_state=_derive)
    h_bad = _make_handle()
    h_ok = _make_handle()

    def bad_matcher(_e: _Event) -> bool:
        raise RuntimeError("boom")

    reg.add(sub=_Sub("a"), matcher=bad_matcher, handle=h_bad)
    reg.add(sub=_Sub("b"), matcher=lambda _e: True, handle=h_ok)
    reg.dispatch(_Event("x"))

    async def collect(h: AsyncSubscriptionHandle[_Event]) -> list[_Event]:
        h._end()
        items: list[_Event] = []
        async for e in h:
            items.append(e)
        return items

    assert asyncio.run(collect(h_ok)) == [_Event("x")]


def test_end_all_clears_entries() -> None:
    reg: SubscriptionRegistry[_Sub, _Event, _State] = SubscriptionRegistry(derive_state=_derive)
    h = _make_handle()
    reg.add(sub=_Sub("a"), matcher=lambda _e: True, handle=h)
    reg.end_all()
    assert reg.is_empty is True
