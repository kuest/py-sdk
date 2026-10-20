# pyright: reportPrivateUsage=false
import inspect
from datetime import UTC, date, datetime

import pytest

from market_sdk._internal.actions.gamma import (
    _coerce_date_filter,
    _coerce_timestamp_filter,
    list_events_spec,
    list_markets_spec,
)
from market_sdk.clients.async_public import AsyncPublicClient
from market_sdk.clients.public import PublicClient
from market_sdk.errors import UserInputError

# Partition per TS source of truth:
#   ts-sdk/packages/client/src/actions/events.ts + markets.ts
# event_date is the only IsoCalendarDateStringSchema filter.
# Every other date/time filter is IsoDateTimeStringSchema.
_TIMESTAMP_PARAMS_LIST_EVENTS = (
    "end_date_max",
    "end_date_min",
    "start_date_max",
    "start_date_min",
    "start_time_max",
    "start_time_min",
)
_TIMESTAMP_PARAMS_LIST_MARKETS = (
    "end_date_max",
    "end_date_min",
    "start_date_max",
    "start_date_min",
)
_DATE_PARAMS_LIST_EVENTS = ("event_date",)


class TestCoerceDateFilter:
    def test_none_returns_none(self) -> None:
        assert _coerce_date_filter(None) is None

    def test_string_passes_through(self) -> None:
        assert _coerce_date_filter("2026-05-31") == "2026-05-31"

    def test_date_serializes_to_iso(self) -> None:
        assert _coerce_date_filter(date(2026, 5, 31)) == "2026-05-31"

    def test_rejects_datetime_with_helpful_message(self) -> None:
        with pytest.raises(UserInputError, match="datetime"):
            _coerce_date_filter(datetime(2026, 5, 31, 12, 0, tzinfo=UTC))  # type: ignore[arg-type]

    def test_rejects_int(self) -> None:
        with pytest.raises(UserInputError, match="expected str or date"):
            _coerce_date_filter(42)  # type: ignore[arg-type]

    def test_rejects_arbitrary_object(self) -> None:
        with pytest.raises(UserInputError):
            _coerce_date_filter(object())  # type: ignore[arg-type]


class TestCoerceTimestampFilter:
    def test_none_returns_none(self) -> None:
        assert _coerce_timestamp_filter(None) is None

    def test_string_passes_through(self) -> None:
        assert _coerce_timestamp_filter("2026-05-31T12:00:00Z") == "2026-05-31T12:00:00Z"

    def test_datetime_aware_serializes_to_iso(self) -> None:
        assert (
            _coerce_timestamp_filter(datetime(2026, 5, 31, 12, 0, tzinfo=UTC))
            == "2026-05-31T12:00:00+00:00"
        )

    def test_datetime_naive_serializes_without_tz(self) -> None:
        assert _coerce_timestamp_filter(datetime(2026, 5, 31, 12, 0)) == "2026-05-31T12:00:00"

    def test_rejects_date(self) -> None:
        with pytest.raises(UserInputError, match="expected str or datetime"):
            _coerce_timestamp_filter(date(2026, 5, 31))  # type: ignore[arg-type]

    def test_rejects_int(self) -> None:
        with pytest.raises(UserInputError):
            _coerce_timestamp_filter(42)  # type: ignore[arg-type]


class TestListEventsSpecTimestampFilters:
    def test_string_lands_in_params(self) -> None:
        spec = list_events_spec(end_date_max="2026-05-31T00:00:00Z")
        assert spec.base_params is not None
        assert spec.base_params["end_date_max"] == "2026-05-31T00:00:00Z"

    def test_datetime_serializes_to_iso(self) -> None:
        spec = list_events_spec(end_date_max=datetime(2026, 5, 31, 12, 0, tzinfo=UTC))
        assert spec.base_params is not None
        assert spec.base_params["end_date_max"] == "2026-05-31T12:00:00+00:00"

    def test_rejects_date_at_runtime(self) -> None:
        with pytest.raises(UserInputError, match="expected str or datetime"):
            list_events_spec(end_date_max=date(2026, 5, 31))  # type: ignore[arg-type]

    def test_all_six_timestamp_params_accept_datetime(self) -> None:
        kwargs: dict[str, datetime] = {
            name: datetime(2026, 1, n + 1, tzinfo=UTC)
            for n, name in enumerate(_TIMESTAMP_PARAMS_LIST_EVENTS)
        }
        spec = list_events_spec(**kwargs)  # type: ignore[arg-type]
        assert spec.base_params is not None
        for name in _TIMESTAMP_PARAMS_LIST_EVENTS:
            assert spec.base_params[name].endswith("+00:00")  # type: ignore[union-attr]


class TestListEventsSpecDateFilter:
    def test_event_date_accepts_string(self) -> None:
        spec = list_events_spec(event_date="2026-05-31")
        assert spec.base_params is not None
        assert spec.base_params["event_date"] == "2026-05-31"

    def test_event_date_accepts_date(self) -> None:
        spec = list_events_spec(event_date=date(2026, 5, 31))
        assert spec.base_params is not None
        assert spec.base_params["event_date"] == "2026-05-31"

    def test_event_date_rejects_datetime_at_runtime(self) -> None:
        with pytest.raises(UserInputError, match="datetime"):
            list_events_spec(event_date=datetime(2026, 5, 31, tzinfo=UTC))  # type: ignore[arg-type]


class TestListMarketsSpecTimestampFilters:
    def test_string_lands_in_params(self) -> None:
        spec = list_markets_spec(end_date_max="2026-05-31T00:00:00Z")
        assert spec.base_params is not None
        assert spec.base_params["end_date_max"] == "2026-05-31T00:00:00Z"

    def test_datetime_serializes_to_iso(self) -> None:
        spec = list_markets_spec(start_date_min=datetime(2026, 1, 1, tzinfo=UTC))
        assert spec.base_params is not None
        assert spec.base_params["start_date_min"] == "2026-01-01T00:00:00+00:00"

    def test_rejects_date_at_runtime(self) -> None:
        with pytest.raises(UserInputError, match="expected str or datetime"):
            list_markets_spec(end_date_max=date(2026, 5, 31))  # type: ignore[arg-type]

    def test_all_four_timestamp_params_accept_datetime(self) -> None:
        kwargs: dict[str, datetime] = {
            name: datetime(2026, 1, n + 1, tzinfo=UTC)
            for n, name in enumerate(_TIMESTAMP_PARAMS_LIST_MARKETS)
        }
        spec = list_markets_spec(**kwargs)  # type: ignore[arg-type]
        assert spec.base_params is not None
        for name in _TIMESTAMP_PARAMS_LIST_MARKETS:
            assert spec.base_params[name].endswith("+00:00")  # type: ignore[union-attr]


def _annotation_args(annotation: object) -> tuple[type, ...]:
    args = getattr(annotation, "__args__", ())
    return tuple(a for a in args if isinstance(a, type))


class TestClientMethodSignaturesMatchTsContract:
    def test_async_public_list_events_timestamp_params_accept_datetime(self) -> None:
        sig = inspect.signature(AsyncPublicClient.list_events)
        for name in _TIMESTAMP_PARAMS_LIST_EVENTS:
            args = _annotation_args(sig.parameters[name].annotation)
            assert str in args, f"{name} should accept str: got {args}"
            assert datetime in args, f"{name} should accept datetime: got {args}"
            assert date not in {a for a in args if a is not datetime}, (
                f"{name} should not advertise bare date: {args}"
            )

    def test_async_public_list_events_event_date_is_date_only(self) -> None:
        sig = inspect.signature(AsyncPublicClient.list_events)
        args = _annotation_args(sig.parameters["event_date"].annotation)
        assert str in args, f"event_date should accept str: got {args}"
        assert date in args, f"event_date should accept date: got {args}"
        assert datetime not in args, f"event_date should NOT accept datetime: {args}"

    def test_sync_public_list_markets_timestamp_params_accept_datetime(self) -> None:
        sig = inspect.signature(PublicClient.list_markets)
        for name in _TIMESTAMP_PARAMS_LIST_MARKETS:
            args = _annotation_args(sig.parameters[name].annotation)
            assert str in args, f"{name} should accept str: got {args}"
            assert datetime in args, f"{name} should accept datetime: got {args}"
            assert date not in {a for a in args if a is not datetime}, (
                f"{name} should not advertise bare date: {args}"
            )
