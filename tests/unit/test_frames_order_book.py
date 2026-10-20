"""Tests for the OrderBook flatten override."""

# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownParameterType=false

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pyarrow as pa

from market_sdk.frames import to_arrow, to_pandas, to_polars
from market_sdk.models import OrderBook
from market_sdk.pagination import Page


def _make_book(
    bids: tuple[tuple[str, str], ...] = (("0.49", "100"), ("0.48", "50")),
    asks: tuple[tuple[str, str], ...] = (("0.51", "80"),),
    *,
    market: str = "0xfoo",
    asset_id: str = "42",
    timestamp_ms: int | None = None,
    book_hash: str = "abc",
) -> OrderBook:
    return OrderBook.model_validate(
        {
            "market": market,
            "asset_id": asset_id,
            "timestamp": str(timestamp_ms) if timestamp_ms is not None else None,
            "bids": [{"price": p, "size": s} for p, s in bids],
            "asks": [{"price": p, "size": s} for p, s in asks],
            "min_order_size": "5",
            "tick_size": "0.01",
            "neg_risk": True,
            "last_trade_price": "0.50",
            "hash": book_hash,
        }
    )


def test_free_function_to_arrow_uses_flat_shape() -> None:
    table = to_arrow(_make_book())
    assert table.column_names == ["side", "level", "price", "size"]
    assert table.num_rows == 3


def test_free_function_to_pandas_uses_flat_shape() -> None:
    df = to_pandas(_make_book())
    assert list(df.columns) == ["side", "level", "price", "size"]
    assert len(df) == 3


def test_free_function_to_polars_uses_flat_shape() -> None:
    df = to_polars(_make_book())
    assert df.columns == ["side", "level", "price", "size"]
    assert df.shape == (3, 4)


def test_method_to_arrow_matches_free_function() -> None:
    book = _make_book()
    assert book.to_arrow().to_pylist() == to_arrow(book).to_pylist()


def test_method_to_pandas_matches_free_function() -> None:
    book = _make_book()
    method_df = book.to_pandas()
    func_df = to_pandas(book)
    assert list(method_df.columns) == list(func_df.columns)
    assert len(method_df) == len(func_df)


def test_method_to_polars_matches_free_function() -> None:
    book = _make_book()
    assert book.to_polars().to_dict(as_series=False) == to_polars(book).to_dict(as_series=False)


def test_bids_appear_first_then_asks_with_correct_level_indexing() -> None:
    rows = _make_book().to_arrow().to_pylist()
    bids = [r for r in rows if r["side"] == "bid"]
    asks = [r for r in rows if r["side"] == "ask"]
    assert [r["level"] for r in bids] == [0, 1]
    assert [r["level"] for r in asks] == [0]


def test_decimal_columns_use_decimal128_38_18() -> None:
    schema = _make_book().to_arrow().schema
    assert pa.types.is_decimal(schema.field("price").type)
    assert pa.types.is_decimal(schema.field("size").type)


def test_pandas_default_decimal_mode_preserves_precision() -> None:
    book = OrderBook.model_validate(
        {
            "market": "0xfoo",
            "asset_id": "42",
            "timestamp": None,
            "bids": [{"price": "0.123456789012345678", "size": "1"}],
            "asks": [],
            "min_order_size": "5",
            "tick_size": "0.01",
            "neg_risk": True,
            "last_trade_price": None,
            "hash": "x",
        }
    )
    df = book.to_pandas()
    assert df["price"][0] == Decimal("0.123456789012345678")


def test_empty_bids_or_asks_still_produces_table() -> None:
    book_no_asks = _make_book(asks=())
    df = book_no_asks.to_pandas()
    assert all(df["side"] == "bid")
    assert len(df) == 2


def test_completely_empty_book_yields_empty_table() -> None:
    book = _make_book(bids=(), asks=())
    table = book.to_arrow()
    assert table.num_rows == 0


_SEQ_COLS = ["market", "token_id", "timestamp", "hash", "side", "level", "price", "size"]


def test_sequence_of_books_includes_identity_columns() -> None:
    b1 = _make_book(market="0xaaa", asset_id="1", book_hash="h1")
    b2 = _make_book(market="0xbbb", asset_id="2", asks=(("0.55", "40"),), book_hash="h2")
    table = to_arrow((b1, b2))
    assert table.column_names == _SEQ_COLS
    assert table.num_rows == 6
    markets = table["market"].to_pylist()
    assert markets.count("0xaaa") == 3
    assert markets.count("0xbbb") == 3


def test_repeated_snapshots_of_same_token_stay_distinguishable() -> None:
    """Same market/token across two snapshots — timestamp + hash disambiguate rows."""
    s1 = _make_book(market="0xaaa", asset_id="1", timestamp_ms=1_700_000_000_000, book_hash="h1")
    s2 = _make_book(market="0xaaa", asset_id="1", timestamp_ms=1_700_000_060_000, book_hash="h2")
    df = to_pandas((s1, s2))
    assert set(df["hash"]) == {"h1", "h2"}
    assert df["timestamp"].nunique() == 2


def test_sequence_timestamp_can_be_null() -> None:
    b = _make_book(market="0xaaa", asset_id="1", timestamp_ms=None)
    df = to_pandas((b,))
    assert bool(df["timestamp"].isna().all())


def test_sequence_timestamp_arrow_type_is_utc_timestamp() -> None:
    b = _make_book(market="0xaaa", asset_id="1", timestamp_ms=1_700_000_000_000)
    schema = to_arrow((b,)).schema
    ts_type = schema.field("timestamp").type
    assert pa.types.is_timestamp(ts_type)
    assert str(ts_type.tz) == "UTC"
    assert to_arrow((b,))["timestamp"][0].as_py() == datetime(2023, 11, 14, 22, 13, 20, tzinfo=UTC)


def test_single_book_in_list_still_includes_identity_columns() -> None:
    df = to_pandas((_make_book(market="0xaaa", asset_id="1"),))
    assert list(df.columns) == _SEQ_COLS
    assert (df["market"] == "0xaaa").all()


def test_page_of_books_uses_sequence_shape() -> None:
    page: Page[OrderBook] = Page(
        items=(
            _make_book(market="0xaaa", asset_id="1"),
            _make_book(market="0xbbb", asset_id="2"),
        ),
        has_more=False,
    )
    df = page.to_pandas()
    assert list(df.columns) == _SEQ_COLS
    assert set(df["market"]) == {"0xaaa", "0xbbb"}


def test_polars_sequence_of_books() -> None:
    b1 = _make_book(market="0xaaa", asset_id="1")
    b2 = _make_book(market="0xbbb", asset_id="2")
    df = to_polars((b1, b2))
    assert df.columns == _SEQ_COLS
    assert df.shape == (6, 8)


def test_single_book_scalar_call_keeps_compact_shape() -> None:
    table = _make_book().to_arrow()
    assert table.column_names == ["side", "level", "price", "size"]
