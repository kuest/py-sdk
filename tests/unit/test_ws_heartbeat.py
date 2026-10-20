import asyncio

from market_sdk._internal.ws.heartbeat import Heartbeat, NoopHeartbeat


def test_noop_heartbeat_satisfies_protocol() -> None:
    heartbeat: Heartbeat = NoopHeartbeat()
    assert isinstance(heartbeat, Heartbeat)


def test_noop_heartbeat_never_consumes_messages() -> None:
    heartbeat = NoopHeartbeat()
    assert heartbeat.handle("PONG") is False
    assert heartbeat.handle("anything") is False
    assert heartbeat.handle("") is False


def test_noop_heartbeat_never_reports_stale() -> None:
    heartbeat = NoopHeartbeat()
    assert heartbeat.is_stale(0.0) is False
    assert heartbeat.is_stale(1e18) is False


def test_noop_heartbeat_start_and_stop_are_safe() -> None:
    heartbeat = NoopHeartbeat()

    async def noop_send(_: str) -> bool:
        return True

    async def run() -> None:
        await heartbeat.start(noop_send)
        await heartbeat.stop()
        await heartbeat.stop()

    asyncio.run(run())
