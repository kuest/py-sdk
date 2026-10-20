"""Restrict Gamma market discovery to markets offered by a configured site."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import cast
from urllib.parse import urlencode, urlparse, urlunparse

import httpx

from market_sdk.models.gamma.market import Market
from market_sdk.pagination import AsyncPaginator, Page, Paginator
from market_sdk.site_config import SITE_CONFIG

SITE_SCOPE_TTL_SECONDS = 5 * 60
SITE_EVENTS_LIMIT = 100
SITE_EVENTS_MAX_PAGES = 50
CONDITION_ID_PATTERN = re.compile(r"^0x[0-9a-fA-F]{64}$")
TOKEN_ID_PATTERN = re.compile(r"^(0x[0-9a-fA-F]+|\d+)$")


@dataclass(frozen=True)
class SiteMarketScope:
    condition_ids: set[str]
    token_ids: set[str]


@dataclass(frozen=True)
class SiteScopeCacheEntry:
    scope: SiteMarketScope
    expires_at: float


_site_scope_cache: SiteScopeCacheEntry | None = None


def has_configured_site_scope() -> bool:
    return bool(SITE_CONFIG["site_url"].strip())


def normalize_condition_id(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    return normalized if CONDITION_ID_PATTERN.fullmatch(normalized) else None


def normalize_token_id(value: object) -> str | None:
    if not isinstance(value, (str, int)):
        return None
    normalized = str(value).strip().lower()
    return normalized if TOKEN_ID_PATTERN.fullmatch(normalized) else None


def _site_api_url(path: str, params: dict[str, str]) -> str:
    raw = SITE_CONFIG["site_url"].strip()
    if not raw:
        raise RuntimeError("site_url must be configured for site-scoped market discovery")
    candidate = raw if raw.startswith(("http://", "https://")) else f"https://{raw}"
    parsed = urlparse(candidate)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise RuntimeError("invalid site_url for site-scoped market discovery")
    origin = urlunparse((parsed.scheme, parsed.netloc, "", "", "", "")).rstrip("/")
    return f"{origin}{path}?{urlencode(params)}"


def _empty_scope() -> SiteMarketScope:
    return SiteMarketScope(condition_ids=set(), token_ids=set())


def _add_token(scope: SiteMarketScope, value: object) -> None:
    token_id = normalize_token_id(value)
    if token_id:
        scope.token_ids.add(token_id)


def _collect_token_list(value: object, scope: SiteMarketScope) -> None:
    if isinstance(value, list):
        for item in cast(list[object], value):
            _collect_token_list(item, scope)
    elif isinstance(value, dict):
        _collect_market_scope(cast(dict[str, object], value), scope)
    else:
        _add_token(scope, value)


def _collect_market_scope(value: object, scope: SiteMarketScope) -> None:
    if isinstance(value, list):
        for item in cast(list[object], value):
            _collect_market_scope(item, scope)
        return
    if not isinstance(value, dict):
        return
    record = cast(dict[str, object], value)
    for key in ("condition_id", "conditionId", "conditionID", "c"):
        condition_id = normalize_condition_id(record.get(key))
        if condition_id:
            scope.condition_ids.add(condition_id)
    for key in ("token_id", "tokenId", "asset_id", "assetId", "t"):
        _add_token(scope, record.get(key))
    for key in ("markets", "outcomes", "tokens"):
        _collect_market_scope(record.get(key), scope)
    for key in ("clob_token_ids", "clobTokenIds", "outcome_assets", "outcomeAssets"):
        _collect_token_list(record.get(key), scope)


def _events_url(page: int) -> str:
    return _site_api_url(
        "/api/events",
        {
            "status": "active",
            "includeBookmarkState": "false",
            "limit": str(SITE_EVENTS_LIMIT),
            "offset": str(page * SITE_EVENTS_LIMIT),
        },
    )


def _add_events(response: httpx.Response, scope: SiteMarketScope) -> bool:
    response.raise_for_status()
    events: object = response.json()
    if not isinstance(events, list):
        raise RuntimeError("site-scoped market discovery expected /api/events to return an array")
    _collect_market_scope(cast(list[object], events), scope)
    return len(cast(list[object], events)) < SITE_EVENTS_LIMIT


def get_site_market_scope() -> SiteMarketScope:
    global _site_scope_cache
    if not has_configured_site_scope():
        return _empty_scope()
    now = time.monotonic()
    if _site_scope_cache and _site_scope_cache.expires_at > now:
        return _site_scope_cache.scope
    scope = _empty_scope()
    for page in range(SITE_EVENTS_MAX_PAGES):
        if _add_events(httpx.get(_events_url(page), timeout=10), scope):
            break
    _site_scope_cache = SiteScopeCacheEntry(scope, now + SITE_SCOPE_TTL_SECONDS)
    return scope


async def async_get_site_market_scope() -> SiteMarketScope:
    global _site_scope_cache
    if not has_configured_site_scope():
        return _empty_scope()
    now = time.monotonic()
    if _site_scope_cache and _site_scope_cache.expires_at > now:
        return _site_scope_cache.scope
    scope = _empty_scope()
    async with httpx.AsyncClient(timeout=10) as client:
        for page in range(SITE_EVENTS_MAX_PAGES):
            if _add_events(await client.get(_events_url(page)), scope):
                break
    _site_scope_cache = SiteScopeCacheEntry(scope, now + SITE_SCOPE_TTL_SECONDS)
    return scope


def _filter_markets(markets: tuple[Market, ...], scope: SiteMarketScope) -> tuple[Market, ...]:
    return tuple(
        market
        for market in markets
        if normalize_condition_id(market.condition_id) in scope.condition_ids
        or any(
            normalize_token_id(outcome.token_id) in scope.token_ids
            for outcome in (market.outcomes.yes, market.outcomes.no)
        )
    )


def scope_market_paginator(paginator: Paginator[Market]) -> Paginator[Market]:
    """Match the old CLOB client's active-event filter, including empty pages."""
    if not has_configured_site_scope():
        return paginator

    def fetch(cursor: str | None) -> Page[Market]:
        scope = get_site_market_scope()
        while True:
            page = (paginator if cursor is None else paginator.from_cursor(cursor)).first_page()
            filtered = _filter_markets(page.items, scope)
            if (
                filtered
                or page.limit_reached
                or not page.has_more
                or page.next_cursor in (None, cursor)
            ):
                return Page(
                    filtered,
                    page.has_more,
                    page.next_cursor,
                    page.total_count,
                    page.limit_reached,
                )
            cursor = page.next_cursor

    return Paginator(fetch)


def scope_async_market_paginator(paginator: AsyncPaginator[Market]) -> AsyncPaginator[Market]:
    if not has_configured_site_scope():
        return paginator

    async def fetch(cursor: str | None) -> Page[Market]:
        scope = await async_get_site_market_scope()
        while True:
            current = paginator if cursor is None else paginator.from_cursor(cursor)
            page = await current.first_page()
            filtered = _filter_markets(page.items, scope)
            if (
                filtered
                or page.limit_reached
                or not page.has_more
                or page.next_cursor in (None, cursor)
            ):
                return Page(
                    filtered,
                    page.has_more,
                    page.next_cursor,
                    page.total_count,
                    page.limit_reached,
                )
            cursor = page.next_cursor

    return AsyncPaginator(fetch)
