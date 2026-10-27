"""Operator creator scope from the generated site"s wallet manifest."""

from __future__ import annotations

from typing import cast

import httpx
import pytest

from market_sdk import site_creators
from market_sdk._internal.actions import gamma as gamma_actions
from market_sdk._internal.context import SyncClientContext
from market_sdk._internal.request import KeysetPaginatedSpec
from market_sdk.errors import UnexpectedResponseError, UserInputError
from market_sdk.pagination import Page, Paginator
from market_sdk.site_config import SITE_CONFIG

ONE = "0x" + "11" * 20
TWO = "0x" + "22" * 20
THREE = "0x" + "33" * 20


def _response(url: str, wallets: list[str]) -> httpx.Response:
    return httpx.Response(200, json={"wallets": wallets}, request=httpx.Request("GET", url))


def test_operator_wallets_are_isolated_cached_and_refreshed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    site_creators._cache.clear()  # pyright: ignore[reportPrivateUsage]
    calls: list[str] = []

    def fake_get(url: str, *, timeout: int) -> httpx.Response:
        calls.append(url)
        return _response(url, [TWO, ONE, ONE] if "first.example" in url else [THREE])

    monkeypatch.setattr(site_creators.httpx, "get", fake_get)
    monkeypatch.setitem(SITE_CONFIG, "site_url", "first.example")
    assert site_creators.resolve_sync_creator(None) == f"{ONE},{TWO}"
    assert site_creators.resolve_sync_creator(None) == f"{ONE},{TWO}"
    monkeypatch.setitem(SITE_CONFIG, "site_url", "https://second.example/path")
    assert site_creators.resolve_sync_creator(None) == THREE
    assert calls == [
        "https://first.example/api/allowed-market-creators",
        "https://second.example/api/allowed-market-creators",
    ]

    monkeypatch.setattr(site_creators.time, "monotonic", lambda: float("inf"))
    monkeypatch.setitem(SITE_CONFIG, "site_url", "first.example")
    assert site_creators.resolve_sync_creator(None) == f"{ONE},{TWO}"
    assert len(calls) == 3


def test_unconfigured_sdk_and_manifest_failure_do_not_leak_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    site_creators._cache.clear()  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setitem(SITE_CONFIG, "site_url", "")
    assert site_creators.resolve_sync_creator(None) is None
    assert site_creators.resolve_sync_creator([ONE, TWO]) == [ONE, TWO]

    monkeypatch.setitem(SITE_CONFIG, "site_url", "empty.example")

    def empty_get(url: str, *, timeout: int) -> httpx.Response:
        return _response(url, [])

    monkeypatch.setattr(site_creators.httpx, "get", empty_get)
    with pytest.raises(UnexpectedResponseError, match="no valid wallets"):
        site_creators.resolve_sync_creator(None)
    with pytest.raises(UserInputError, match="cannot override"):
        site_creators.resolve_sync_creator(ONE)


def test_scoped_keyset_uses_manifest_query_without_resolving_at_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(SITE_CONFIG, "site_url", "operator.example")

    def creator_query(site: str) -> str:
        return f"{ONE},{TWO}"

    monkeypatch.setattr(site_creators, "get_site_creator_query", creator_query)
    captured: list[object] = []

    def fake_paginate(ctx: object, spec: object, *, page_size: int) -> Paginator[object]:
        captured.append(spec)
        return Paginator(lambda cursor: Page(items=(), has_more=False))

    monkeypatch.setattr(site_creators, "sync_paginate_keyset", fake_paginate)
    spec = gamma_actions.list_markets_spec()
    paginator = site_creators.scope_sync_keyset(cast(SyncClientContext, None), spec, page_size=20)
    assert captured == []
    assert paginator.first_page().items == ()
    scoped = cast(KeysetPaginatedSpec[object], captured[0])
    assert scoped.base_params is not None
    assert scoped.base_params["creator"] == f"{ONE},{TWO}"
