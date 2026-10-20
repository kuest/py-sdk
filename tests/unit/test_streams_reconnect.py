import asyncio

from market_sdk._internal.streams.reconnect import ReconnectScheduler


def test_schedule_runs_reconnect_after_backoff() -> None:
    calls: list[int] = []

    async def reconnect() -> None:
        calls.append(1)

    async def run() -> None:
        scheduler = ReconnectScheduler(base_s=0.01, max_s=0.05)
        scheduler.schedule(reconnect=reconnect, should_reconnect=lambda: True)
        await asyncio.sleep(0.2)

    asyncio.run(run())
    assert calls == [1]


def test_schedule_skips_when_should_reconnect_is_false() -> None:
    calls: list[int] = []

    async def reconnect() -> None:
        calls.append(1)

    async def run() -> None:
        scheduler = ReconnectScheduler(base_s=0.01, max_s=0.05)
        scheduler.schedule(reconnect=reconnect, should_reconnect=lambda: False)
        await asyncio.sleep(0.1)

    asyncio.run(run())
    assert calls == []


def test_stop_cancels_pending_reconnect() -> None:
    calls: list[int] = []

    async def reconnect() -> None:
        calls.append(1)

    async def run() -> None:
        scheduler = ReconnectScheduler(base_s=0.5, max_s=1.0)
        scheduler.schedule(reconnect=reconnect, should_reconnect=lambda: True)
        scheduler.stop()
        await asyncio.sleep(0.6)

    asyncio.run(run())
    assert calls == []


def test_double_schedule_does_not_stack() -> None:
    calls: list[int] = []

    async def reconnect() -> None:
        calls.append(1)

    async def run() -> None:
        scheduler = ReconnectScheduler(base_s=0.01, max_s=0.05)
        scheduler.schedule(reconnect=reconnect, should_reconnect=lambda: True)
        scheduler.schedule(reconnect=reconnect, should_reconnect=lambda: True)
        await asyncio.sleep(0.2)

    asyncio.run(run())
    assert calls == [1]


def test_callback_can_reschedule_itself_after_failure() -> None:
    attempts: list[int] = []

    async def run() -> int:
        scheduler = ReconnectScheduler(base_s=0.01, max_s=0.05)

        async def reconnect() -> None:
            attempts.append(1)
            if len(attempts) < 3:
                scheduler.schedule(reconnect=reconnect, should_reconnect=lambda: True)

        scheduler.schedule(reconnect=reconnect, should_reconnect=lambda: True)
        await asyncio.sleep(0.5)
        return len(attempts)

    assert asyncio.run(run()) == 3


def test_inner_schedule_during_callback_preserves_new_timer_reference() -> None:
    """When the callback calls schedule() before returning, the new timer
    must remain trackable for cancel/await — the outer task's finally clause
    must not clobber it.
    """

    async def run() -> bool:
        scheduler = ReconnectScheduler(base_s=10.0, max_s=10.0)
        observed: list[asyncio.Task[None] | None] = []

        async def reconnect() -> None:
            scheduler.schedule(reconnect=reconnect, should_reconnect=lambda: True)
            observed.append(scheduler._timer)  # pyright: ignore[reportPrivateUsage]

        # Make first attempt fire immediately, second one wait 10s.
        scheduler._timer = None  # pyright: ignore[reportPrivateUsage]
        await reconnect()
        return observed[0] is not None and scheduler.is_pending

    assert asyncio.run(run()) is True


def test_aclose_awaits_cancelled_timer_task() -> None:
    async def run() -> bool:
        scheduler = ReconnectScheduler(base_s=10.0, max_s=10.0)

        async def reconnect() -> None:
            return None

        scheduler.schedule(reconnect=reconnect, should_reconnect=lambda: True)
        timer = scheduler._timer  # pyright: ignore[reportPrivateUsage]
        assert timer is not None
        await scheduler.aclose()
        return timer.done()

    assert asyncio.run(run()) is True


def test_attempt_increments_then_resets() -> None:
    async def reconnect() -> None:
        return None

    async def run() -> tuple[int, int]:
        scheduler = ReconnectScheduler(base_s=0.01, max_s=0.05)
        scheduler.schedule(reconnect=reconnect, should_reconnect=lambda: True)
        await asyncio.sleep(0.15)
        attempt_before_reset = scheduler.attempt
        scheduler.reset()
        return attempt_before_reset, scheduler.attempt

    before, after = asyncio.run(run())
    assert before >= 1
    assert after == 0
