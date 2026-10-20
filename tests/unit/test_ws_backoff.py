import math
import random

import pytest

from market_sdk._internal.ws.backoff import jittered_backoff


def test_returns_zero_when_rng_draws_zero() -> None:
    class ZeroRng(random.Random):
        def random(self) -> float:
            return 0.0

    assert jittered_backoff(0, rng=ZeroRng()) == 0.0
    assert jittered_backoff(5, rng=ZeroRng()) == 0.0


def test_returns_near_cap_when_rng_draws_one() -> None:
    class OneRng(random.Random):
        def random(self) -> float:
            return 1.0 - 1e-12

    base = 0.25
    max_s = 30.0
    assert math.isclose(jittered_backoff(0, base_s=base, max_s=max_s, rng=OneRng()), base)
    assert math.isclose(jittered_backoff(3, base_s=base, max_s=max_s, rng=OneRng()), base * 8)
    assert math.isclose(jittered_backoff(100, base_s=base, max_s=max_s, rng=OneRng()), max_s)


def test_stays_within_bounds_across_many_draws() -> None:
    rng = random.Random(1234)
    for attempt in range(0, 12):
        cap = min(0.25 * (2**attempt), 30.0)
        for _ in range(50):
            value = jittered_backoff(attempt, rng=rng)
            assert 0.0 <= value <= cap


def test_rejects_negative_attempt() -> None:
    with pytest.raises(ValueError, match="attempt"):
        jittered_backoff(-1)


def test_rejects_non_positive_base() -> None:
    with pytest.raises(ValueError, match="base_s"):
        jittered_backoff(0, base_s=0)


def test_rejects_max_less_than_base() -> None:
    with pytest.raises(ValueError, match="max_s"):
        jittered_backoff(0, base_s=1.0, max_s=0.5)


def test_huge_attempt_does_not_overflow_and_returns_finite_value() -> None:
    class OneRng(random.Random):
        def random(self) -> float:
            return 1.0 - 1e-12

    value = jittered_backoff(10_000, base_s=0.25, max_s=30.0, rng=OneRng())
    assert math.isfinite(value)
    assert math.isclose(value, 30.0)
