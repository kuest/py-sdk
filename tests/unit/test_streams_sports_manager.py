import asyncio
import json
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

import pytest
from websockets.asyncio.server import ServerConnection, serve

from market_sdk._internal.streams.sports.manager import SportsStreamManager
from market_sdk.models.sports_events import SportsResultEvent

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


def _game_frame(game_id: int = 1) -> dict[str, Any]:
    return {
        "gameId": game_id,
        "leagueAbbreviation": "NBA",
        "status": "live",
        "live": True,
        "ended": False,
        "score": "0-0",
    }


def test_no_client_frame_sent_on_connect() -> None:
    received: list[str] = []

    async def handler(ws: ServerConnection) -> None:
        async for raw in ws:
            received.append(str(raw))

    async def run() -> None:
        async with ws_server(handler) as url:
            mgr = SportsStreamManager(url=url)
            try:
                handle = await mgr.subscribe()
                await asyncio.sleep(0.1)
                await handle.close()
            finally:
                await mgr.close()

    asyncio.run(run())
    # Sports never sends a subscribe frame; we also never pinged so no pong.
    assert received == []


def test_server_ping_triggers_pong_response() -> None:
    received: list[str] = []

    async def handler(ws: ServerConnection) -> None:
        await ws.send("ping")
        async for raw in ws:
            received.append(str(raw))

    async def run() -> None:
        async with ws_server(handler) as url:
            mgr = SportsStreamManager(url=url)
            try:
                handle = await mgr.subscribe()
                deadline = asyncio.get_event_loop().time() + 2.0
                while not received:
                    if asyncio.get_event_loop().time() > deadline:
                        raise AssertionError("pong not observed")
                    await asyncio.sleep(0.02)
                await handle.close()
            finally:
                await mgr.close()

    asyncio.run(run())
    assert received == ["pong"]


def test_event_broadcast_to_all_subscribers() -> None:
    async def handler(ws: ServerConnection) -> None:
        # Stream events on a loop so subscribers registered after the first
        # event still see one within the test window.
        try:
            for _ in range(50):
                await ws.send(json.dumps(_game_frame(42)))
                await asyncio.sleep(0.02)
        except Exception:
            return

    async def run() -> tuple[int, int]:
        async with ws_server(handler) as url:
            mgr = SportsStreamManager(url=url)
            try:
                h1 = await mgr.subscribe()
                h2 = await mgr.subscribe()
                e1 = await asyncio.wait_for(h1.__aiter__().__anext__(), timeout=2.0)
                e2 = await asyncio.wait_for(h2.__aiter__().__anext__(), timeout=2.0)
                assert isinstance(e1, SportsResultEvent)
                assert isinstance(e2, SportsResultEvent)
                game1 = e1.payload.game_id
                game2 = e2.payload.game_id
                await h1.close()
                await h2.close()
                return game1, game2
            finally:
                await mgr.close()

    g1, g2 = asyncio.run(run())
    assert g1 == 42
    assert g2 == 42


def test_malformed_event_dropped_and_counter_increments() -> None:
    async def handler(ws: ServerConnection) -> None:
        await ws.send(json.dumps({"this": "is not a sport result"}))
        await ws.send(json.dumps(_game_frame(7)))
        async for _ in ws:
            pass

    async def run() -> tuple[int, int]:
        async with ws_server(handler) as url:
            mgr = SportsStreamManager(url=url)
            try:
                handle = await mgr.subscribe()
                event = await asyncio.wait_for(handle.__aiter__().__anext__(), timeout=2.0)
                assert isinstance(event, SportsResultEvent)
                game_id = event.payload.game_id
                await asyncio.sleep(0.05)
                dropped = mgr.dropped_events
                await handle.close()
                return game_id, dropped
            finally:
                await mgr.close()

    game_id, dropped = asyncio.run(run())
    assert game_id == 7
    assert dropped == 1


def test_last_handle_close_drops_socket() -> None:
    async def handler(ws: ServerConnection) -> None:
        async for _ in ws:
            pass

    async def run() -> bool:
        async with ws_server(handler) as url:
            mgr = SportsStreamManager(url=url)
            try:
                handle = await mgr.subscribe()
                await asyncio.sleep(0.05)
                await handle.close()
                await asyncio.sleep(0.1)
                return mgr.is_open
            finally:
                await mgr.close()

    assert asyncio.run(run()) is False


def test_manager_remains_usable_after_last_handle_drops_socket() -> None:
    accepts = 0

    async def handler(ws: ServerConnection) -> None:
        nonlocal accepts
        accepts += 1
        async for _ in ws:
            pass

    async def run() -> int:
        async with ws_server(handler) as url:
            mgr = SportsStreamManager(url=url)
            try:
                h1 = await mgr.subscribe()
                await asyncio.sleep(0.05)
                await h1.close()
                await asyncio.sleep(0.1)
                h2 = await mgr.subscribe()
                await asyncio.sleep(0.05)
                await h2.close()
                return accepts
            finally:
                await mgr.close()

    assert asyncio.run(run()) == 2


def test_reconnect_does_not_send_any_frame() -> None:
    received_per_connection: list[list[str]] = []
    connect_count = 0

    async def handler(ws: ServerConnection) -> None:
        nonlocal connect_count
        connect_count += 1
        my_received: list[str] = []
        received_per_connection.append(my_received)
        if connect_count == 1:
            # Close immediately so the manager schedules a reconnect.
            await ws.close()
            return
        async for raw in ws:
            my_received.append(str(raw))

    async def run() -> None:
        async with ws_server(handler) as url:
            mgr = SportsStreamManager(url=url)
            try:
                handle = await mgr.subscribe()
                await asyncio.sleep(1.5)
                await handle.close()
            finally:
                await mgr.close()

    asyncio.run(run())
    assert connect_count >= 2
    # Neither connection received a client-sent subscribe frame.
    for frames in received_per_connection:
        assert frames == []


def test_handle_close_idempotent_and_manager_close_ends_handles() -> None:
    async def handler(ws: ServerConnection) -> None:
        async for _ in ws:
            pass

    async def run() -> None:
        async with ws_server(handler) as url:
            mgr = SportsStreamManager(url=url)
            handle = await mgr.subscribe()
            await asyncio.gather(handle.close(), handle.close())
            handle2 = await mgr.subscribe()
            await mgr.close()
            with pytest.raises(StopAsyncIteration):
                await handle2.__aiter__().__anext__()

    asyncio.run(run())


def test_subscribe_after_manager_close_raises() -> None:
    async def run() -> None:
        mgr = SportsStreamManager(url="ws://127.0.0.1:1")
        await mgr.close()
        with pytest.raises(RuntimeError, match="closed"):
            await mgr.subscribe()

    asyncio.run(run())
