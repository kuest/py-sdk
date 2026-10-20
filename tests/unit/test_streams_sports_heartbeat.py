# pyright: reportPrivateUsage=false
import asyncio

import pytest

from market_sdk._internal.streams.sports.heartbeat import SportsWebSocketHeartbeat


def test_lowercase_ping_consumed_and_triggers_pong_send() -> None:
    sent: list[str] = []

    async def fake_send(msg: str) -> bool:
        sent.append(msg)
        return True

    async def run() -> tuple[bool, list[str]]:
        hb = SportsWebSocketHeartbeat()
        await hb.start(fake_send)
        consumed = hb.handle("ping")
        await asyncio.sleep(0)  # let the pong task run
        await hb.stop()
        return consumed, sent

    consumed, sent = asyncio.run(run())
    assert consumed is True
    assert sent == ["pong"]


def test_uppercase_PING_is_not_a_heartbeat() -> None:
    sent: list[str] = []

    async def fake_send(msg: str) -> bool:
        sent.append(msg)
        return True

    async def run() -> tuple[bool, list[str]]:
        hb = SportsWebSocketHeartbeat()
        await hb.start(fake_send)
        consumed = hb.handle("PING")
        await asyncio.sleep(0)
        await hb.stop()
        return consumed, sent

    consumed, sent = asyncio.run(run())
    assert consumed is False
    assert sent == []


def test_arbitrary_text_is_not_a_heartbeat() -> None:
    async def fake_send(_msg: str) -> bool:
        return True

    async def run() -> bool:
        hb = SportsWebSocketHeartbeat()
        await hb.start(fake_send)
        consumed = hb.handle("hello")
        await hb.stop()
        return consumed

    assert asyncio.run(run()) is False


def test_is_stale_before_any_ping_received_after_start() -> None:
    async def run() -> bool:
        hb = SportsWebSocketHeartbeat(stale_s=0.01)
        await hb.start(_unused_send)
        await asyncio.sleep(0.05)
        result = hb.is_stale(_now())
        await hb.stop()
        return result

    assert asyncio.run(run()) is True


def test_is_stale_resets_on_ping() -> None:
    async def fake_send(_msg: str) -> bool:
        return True

    async def run() -> tuple[bool, bool]:
        hb = SportsWebSocketHeartbeat(stale_s=0.05)
        await hb.start(fake_send)
        await asyncio.sleep(0.1)
        before = hb.is_stale(_now())
        hb.handle("ping")
        after = hb.is_stale(_now())
        await asyncio.sleep(0)
        await hb.stop()
        return before, after

    before, after = asyncio.run(run())
    assert before is True
    assert after is False


def test_stop_does_not_hang_when_pong_send_is_stuck() -> None:
    """A pong send that never returns (stuck socket) must not block stop().
    stop() is awaited before the socket itself is closed, so blocking here
    would deadlock client.close()."""

    started = asyncio.Event()
    never_release = asyncio.Event()

    async def stuck_send(_msg: str) -> bool:
        started.set()
        await never_release.wait()
        return True

    async def run() -> None:
        hb = SportsWebSocketHeartbeat()
        await hb.start(stuck_send)
        hb.handle("ping")
        await started.wait()
        # Should return promptly via cancellation, not hang on the stuck send.
        await asyncio.wait_for(hb.stop(), timeout=1.0)

    asyncio.run(run())


def test_stop_awaits_pending_pong_tasks() -> None:
    started = asyncio.Event()
    release = asyncio.Event()
    completed: list[bool] = []

    async def slow_send(_msg: str) -> bool:
        started.set()
        await release.wait()
        completed.append(True)
        return True

    async def run() -> bool:
        hb = SportsWebSocketHeartbeat()
        await hb.start(slow_send)
        hb.handle("ping")
        await started.wait()
        release.set()
        await hb.stop()
        return all(completed)

    assert asyncio.run(run()) is True


def test_pong_send_errors_are_swallowed() -> None:
    async def failing_send(_msg: str) -> bool:
        raise RuntimeError("socket dead")

    async def run() -> None:
        hb = SportsWebSocketHeartbeat()
        await hb.start(failing_send)
        hb.handle("ping")
        await asyncio.sleep(0)
        await hb.stop()

    asyncio.run(run())  # must not raise


async def _unused_send(_msg: str) -> bool:
    return True


def _now() -> float:
    import time

    return time.monotonic()


@pytest.mark.parametrize("stale_s", [0, -1.0])
def test_invalid_stale_raises(stale_s: float) -> None:
    with pytest.raises(ValueError, match="stale_s"):
        SportsWebSocketHeartbeat(stale_s=stale_s)
