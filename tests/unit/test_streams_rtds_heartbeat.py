# pyright: reportPrivateUsage=false
import asyncio

import pytest

from market_sdk._internal.streams.rtds.heartbeat import RtdsWebSocketHeartbeat


def test_uppercase_PING_sent_on_interval() -> None:
    sent: list[str] = []

    async def fake_send(msg: str) -> bool:
        sent.append(msg)
        return True

    async def run() -> int:
        hb = RtdsWebSocketHeartbeat(interval_s=0.05)
        await hb.start(fake_send)
        await asyncio.sleep(0.2)
        await hb.stop()
        return len(sent)

    count = asyncio.run(run())
    assert count >= 2
    assert all(msg == "PING" for msg in sent)


def test_any_message_resets_stale_timer_and_handle_returns_false() -> None:
    async def fake_send(_msg: str) -> bool:
        return True

    async def run() -> tuple[bool, bool, bool]:
        hb = RtdsWebSocketHeartbeat(stale_s=0.05)
        await hb.start(fake_send)
        await asyncio.sleep(0.1)
        import time

        stale_before = hb.is_stale(time.monotonic())
        consumed = hb.handle('{"hello": "world"}')
        stale_after = hb.is_stale(time.monotonic())
        await hb.stop()
        return stale_before, stale_after, consumed

    before, after, consumed = asyncio.run(run())
    assert before is True
    assert after is False
    assert consumed is False


def test_handle_returns_false_for_all_messages() -> None:
    async def fake_send(_msg: str) -> bool:
        return True

    async def run() -> list[bool]:
        hb = RtdsWebSocketHeartbeat()
        await hb.start(fake_send)
        results = [hb.handle(msg) for msg in ["PING", "PONG", "ping", "{}", "anything"]]
        await hb.stop()
        return results

    assert asyncio.run(run()) == [False, False, False, False, False]


def test_stop_cancels_ticker_and_returns_promptly() -> None:
    sent: list[str] = []

    async def fake_send(msg: str) -> bool:
        sent.append(msg)
        return True

    async def run() -> int:
        hb = RtdsWebSocketHeartbeat(interval_s=0.05)
        await hb.start(fake_send)
        await asyncio.sleep(0.1)
        await asyncio.wait_for(hb.stop(), timeout=1.0)
        before = len(sent)
        await asyncio.sleep(0.15)
        return len(sent) - before

    assert asyncio.run(run()) == 0


@pytest.mark.parametrize("bad", [0, -1.0])
def test_invalid_interval_raises(bad: float) -> None:
    with pytest.raises(ValueError, match="interval_s"):
        RtdsWebSocketHeartbeat(interval_s=bad)


@pytest.mark.parametrize("bad", [0, -1.0])
def test_invalid_stale_raises(bad: float) -> None:
    with pytest.raises(ValueError, match="stale_s"):
        RtdsWebSocketHeartbeat(stale_s=bad)
