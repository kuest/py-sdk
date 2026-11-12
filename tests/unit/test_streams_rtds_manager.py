import asyncio
import json
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

import pytest
from websockets.asyncio.server import ServerConnection, serve

from market_sdk._internal.streams.rtds.manager import RtdsStreamManager
from market_sdk.models.rtds_events import CommentRemovedEvent
from market_sdk.streams import CommentsSpec

Handler = Callable[[ServerConnection], Awaitable[None]]


@asynccontextmanager
async def ws_server(handler: Handler) -> AsyncGenerator[str, None]:
    server = await serve(handler, host="127.0.0.1", port=0)
    try:
        port = next(iter(server.sockets)).getsockname()[1]
        yield f"ws://127.0.0.1:{port}"
    finally:
        server.close()
        await server.wait_closed()


def _comment_frame() -> dict[str, Any]:
    return {
        "topic": "comments",
        "type": "comment_removed",
        "timestamp": 1710000000000,
        "payload": {"id": "comment-1", "parentEntityID": 1, "parentEntityType": "Event"},
    }


def test_initial_subscribe_frame_sent_on_connect() -> None:
    received: list[dict[str, Any]] = []

    async def handler(ws: ServerConnection) -> None:
        async for raw in ws:
            if raw == "PING":
                continue
            received.append(json.loads(raw))

    async def run() -> None:
        async with ws_server(handler) as url:
            mgr = RtdsStreamManager(url=url)
            try:
                handle = await mgr.subscribe(CommentsSpec(types=["comment_removed"]))
                await asyncio.sleep(0.1)
                await handle.close()
            finally:
                await mgr.close()

    asyncio.run(run())
    assert received[0] == {
        "action": "subscribe",
        "subscriptions": [{"topic": "comments", "type": "comment_removed"}],
    }


def test_overlapping_specs_dedup_one_subscribe_frame() -> None:
    received: list[dict[str, Any]] = []

    async def handler(ws: ServerConnection) -> None:
        async for raw in ws:
            if raw == "PING":
                continue
            received.append(json.loads(raw))

    async def run() -> None:
        async with ws_server(handler) as url:
            mgr = RtdsStreamManager(url=url)
            try:
                h1 = await mgr.subscribe(
                    CommentsSpec(types=["comment_removed"], parent_entity_id=1)
                )
                h2 = await mgr.subscribe(
                    CommentsSpec(types=["comment_removed"], parent_entity_id=2)
                )
                await asyncio.sleep(0.1)
                await h1.close()
                await h2.close()
            finally:
                await mgr.close()

    asyncio.run(run())
    subscribes = [f for f in received if f["action"] == "subscribe"]
    assert len(subscribes) == 1


def test_unsubscribe_only_after_last_user_drops_a_topic_type() -> None:
    received: list[dict[str, Any]] = []

    async def handler(ws: ServerConnection) -> None:
        async for raw in ws:
            if raw == "PING":
                continue
            received.append(json.loads(raw))

    async def run() -> None:
        async with ws_server(handler) as url:
            mgr = RtdsStreamManager(url=url)
            try:
                h1 = await mgr.subscribe(
                    CommentsSpec(types=["comment_removed"], parent_entity_id=1)
                )
                h2 = await mgr.subscribe(
                    CommentsSpec(types=["comment_removed"], parent_entity_id=2)
                )
                await asyncio.sleep(0.05)
                await h1.close()
                await asyncio.sleep(0.05)
                unsubscribes_so_far = [f for f in received if f["action"] == "unsubscribe"]
                assert unsubscribes_so_far == []
                await h2.close()
                await asyncio.sleep(0.05)
            finally:
                await mgr.close()

    asyncio.run(run())


def test_comment_event_reaches_registered_handle() -> None:
    async def handler(ws: ServerConnection) -> None:
        await ws.recv()  # initial subscribe
        await ws.send(json.dumps(_comment_frame()))
        async for _ in ws:
            pass

    async def run() -> str:
        async with ws_server(handler) as url:
            mgr = RtdsStreamManager(url=url)
            try:
                handle = await mgr.subscribe(CommentsSpec(types=["comment_removed"]))
                event = await asyncio.wait_for(handle.__aiter__().__anext__(), timeout=2.0)
                assert isinstance(event, CommentRemovedEvent)
                topic = event.topic
                await handle.close()
                return topic
            finally:
                await mgr.close()

    assert asyncio.run(run()) == "comments"


def test_malformed_event_dropped_and_counter_increments() -> None:
    async def handler(ws: ServerConnection) -> None:
        await ws.recv()
        await ws.send(json.dumps({"topic": "bogus", "type": "x"}))
        await ws.send(json.dumps(_comment_frame()))
        async for _ in ws:
            pass

    async def run() -> tuple[str, int]:
        async with ws_server(handler) as url:
            mgr = RtdsStreamManager(url=url)
            try:
                handle = await mgr.subscribe(CommentsSpec(types=["comment_removed"]))
                event = await asyncio.wait_for(handle.__aiter__().__anext__(), timeout=2.0)
                assert isinstance(event, CommentRemovedEvent)
                symbol = event.payload.id
                await asyncio.sleep(0.05)
                dropped = mgr.dropped_events
                await handle.close()
                return symbol, dropped
            finally:
                await mgr.close()

    symbol, dropped = asyncio.run(run())
    assert symbol == "comment-1"
    assert dropped == 1


def test_reconnect_resends_full_state() -> None:
    received_per_connection: list[list[dict[str, Any]]] = []
    connect_count = 0

    async def handler(ws: ServerConnection) -> None:
        nonlocal connect_count
        connect_count += 1
        frames: list[dict[str, Any]] = []
        received_per_connection.append(frames)
        if connect_count == 1:
            raw = await ws.recv()
            if isinstance(raw, str) and raw != "PING":
                frames.append(json.loads(raw))
            await ws.close()
            return
        async for raw in ws:
            if raw == "PING":
                continue
            frames.append(json.loads(raw))

    async def run() -> None:
        async with ws_server(handler) as url:
            mgr = RtdsStreamManager(url=url)
            try:
                handle = await mgr.subscribe(CommentsSpec(types=["comment_removed"]))
                await asyncio.sleep(1.5)
                await handle.close()
            finally:
                await mgr.close()

    asyncio.run(run())
    assert connect_count >= 2
    assert received_per_connection[0][0]["subscriptions"] == [
        {"topic": "comments", "type": "comment_removed"}
    ]
    assert received_per_connection[1][0]["subscriptions"] == [
        {"topic": "comments", "type": "comment_removed"}
    ]


def test_last_handle_close_drops_socket() -> None:
    async def handler(ws: ServerConnection) -> None:
        async for _ in ws:
            pass

    async def run() -> bool:
        async with ws_server(handler) as url:
            mgr = RtdsStreamManager(url=url)
            try:
                handle = await mgr.subscribe(CommentsSpec(types=["comment_removed"]))
                await asyncio.sleep(0.05)
                await handle.close()
                await asyncio.sleep(0.1)
                return mgr.is_open
            finally:
                await mgr.close()

    assert asyncio.run(run()) is False


def test_subscribe_after_close_raises() -> None:
    async def run() -> None:
        mgr = RtdsStreamManager(url="ws://127.0.0.1:1")
        await mgr.close()
        with pytest.raises(RuntimeError, match="closed"):
            await mgr.subscribe(CommentsSpec(types=["comment_removed"]))

    asyncio.run(run())


def test_unsubscribe_removes_only_unused_comment_type() -> None:
    received: list[dict[str, Any]] = []

    async def handler(ws: ServerConnection) -> None:
        async for raw in ws:
            if raw != "PING":
                received.append(json.loads(raw))

    async def run() -> None:
        async with ws_server(handler) as url:
            mgr = RtdsStreamManager(url=url)
            try:
                removed = await mgr.subscribe(CommentsSpec(types=["comment_removed"]))
                created = await mgr.subscribe(CommentsSpec(types=["comment_created"]))
                await removed.close()
                await asyncio.sleep(0.05)
                assert mgr.is_open
                assert {
                    "action": "unsubscribe",
                    "subscriptions": [{"topic": "comments", "type": "comment_removed"}],
                } in received
                assert received[1] == {
                    "action": "subscribe",
                    "subscriptions": [{"topic": "comments", "type": "comment_created"}],
                }
                await created.close()
            finally:
                await mgr.close()

    asyncio.run(run())
