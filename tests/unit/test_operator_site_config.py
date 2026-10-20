"""Offline contract checks for the legacy .sdk operator overlay."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from market_sdk import site_config, site_scope
from market_sdk.errors import UserInputError
from market_sdk.models.gamma.market import Market
from market_sdk.pagination import AsyncPaginator, Page, Paginator

CONDITION = "0x" + "ab" * 32
OTHER_CONDITION = "0x" + "cd" * 32


def test_extracted_zip_reads_overlay_from_working_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    overlay = tmp_path / ".sdk" / "site-config.json"
    overlay.parent.mkdir()
    overlay.write_text(json.dumps({"site_url": "https://operator.example"}))
    monkeypatch.chdir(tmp_path)
    assert site_config._config_path() == overlay  # pyright: ignore[reportPrivateUsage]
    assert site_config._load_site_config()["site_url"] == "https://operator.example"  # pyright: ignore[reportPrivateUsage]


def test_overlay_uses_existing_schema_and_direct_checkout_defaults(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path = tmp_path / ".sdk" / "site-config.json"
    monkeypatch.setattr(site_config, "_config_path", lambda: path)
    assert site_config._load_site_config() == site_config.DEFAULT_SITE_CONFIG  # pyright: ignore[reportPrivateUsage]

    path.parent.mkdir()
    path.write_text(
        json.dumps(
            {
                "site_url": "https://operator.example",
                "builder_mode": True,
                "geoblock": True,
                "builder_code": "0x" + "11" * 32,
                "order_metadata": "0x" + "22" * 32,
            }
        )
    )
    parsed = site_config._load_site_config()  # pyright: ignore[reportPrivateUsage]
    assert parsed["builder_code"] == "0x" + "11" * 32
    assert parsed["order_metadata"] == "0x" + "22" * 32
    monkeypatch.setitem(site_config.SITE_CONFIG, "builder_mode", True)
    monkeypatch.setitem(site_config.SITE_CONFIG, "builder_code", parsed["builder_code"])
    assert site_config.get_site_order_context()["builder_code"] == parsed["builder_code"]


def test_zero_builder_code_preserves_inherited_override_when_builder_mode_is_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(site_config.SITE_CONFIG, "builder_mode", False)
    monkeypatch.setitem(site_config.SITE_CONFIG, "builder_code", site_config.ZERO_BYTES32)
    assert site_config.get_site_order_context()["builder_code"] == site_config.ZERO_BYTES32
    monkeypatch.setitem(site_config.SITE_CONFIG, "builder_mode", True)
    with pytest.raises(ValueError, match="requires a non-zero builder_code"):
        site_config.get_site_order_context()


def test_geoblock_uses_operator_site_and_rejects_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(site_config.SITE_CONFIG, "site_url", "https://operator.example")
    observed: dict[str, object] = {}

    def fake_get(url: str, *, params: dict[str, str], timeout: int) -> httpx.Response:
        observed.update({"url": url, "params": params, "timeout": timeout})
        return httpx.Response(
            200,
            json={"blocked": True, "country": "US", "region": "NY"},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(site_config.httpx, "get", fake_get)
    status = site_config.fetch_geoblock_status()
    assert observed["params"] == {"url": "https://operator.example"}
    with pytest.raises(UserInputError, match="trading blocked"):
        site_config.ensure_geoblock_allowed(status)


def _market(condition_id: str, token_id: str) -> Market:
    return Market.parse_response(
        {
            "id": token_id,
            "conditionId": condition_id,
            "outcomes": ["Yes", "No"],
            "clobTokenIds": [token_id, "999"],
        }
    )


def test_site_market_scope_filters_and_skips_empty_pages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(site_config.SITE_CONFIG, "site_url", "https://operator.example/path")
    monkeypatch.setattr(site_scope, "_site_scope_cache", None)
    calls: list[str] = []

    def fake_get(url: str, *, timeout: int) -> httpx.Response:
        calls.append(url)
        return httpx.Response(
            200, json=[{"markets": [{"conditionId": CONDITION}]}], request=httpx.Request("GET", url)
        )

    monkeypatch.setattr(site_scope.httpx, "get", fake_get)
    excluded = _market(OTHER_CONDITION, "111")
    allowed = _market(CONDITION, "222")

    def fetch(cursor: str | None) -> Page[Market]:
        if cursor is None:
            return Page((excluded,), True, "second")
        return Page((allowed, excluded), False)

    page = site_scope.scope_market_paginator(Paginator(fetch)).first_page()
    assert page.items == (allowed,)
    assert len(calls) == 1
    assert calls[0].startswith("https://operator.example/api/events?")


def test_no_site_config_preserves_unfiltered_paginator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(site_config.SITE_CONFIG, "site_url", "")
    original: Paginator[Market] = Paginator(lambda _: Page((), False))
    assert site_scope.scope_market_paginator(original) is original


def test_async_site_scope_keeps_only_operator_market(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(site_config.SITE_CONFIG, "site_url", "https://operator.example")

    async def fake_scope() -> site_scope.SiteMarketScope:
        return site_scope.SiteMarketScope({CONDITION}, set())

    monkeypatch.setattr(site_scope, "async_get_site_market_scope", fake_scope)

    async def fetch(cursor: str | None) -> Page[Market]:
        return Page((_market(CONDITION, "222"), _market(OTHER_CONDITION, "111")), False)

    paginator = site_scope.scope_async_market_paginator(AsyncPaginator(fetch))
    page = asyncio.run(paginator.first_page())
    assert [market.condition_id for market in page.items] == [CONDITION]
