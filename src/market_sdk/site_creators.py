"""Resolve creator wallets for a configured operator site."""

from __future__ import annotations

import asyncio
import re
import time
from collections.abc import Sequence
from dataclasses import dataclass, replace
from threading import Lock
from typing import TypeVar, cast
from urllib.parse import urlparse

import httpx

from market_sdk._internal.context import AsyncClientContext, SyncClientContext
from market_sdk._internal.dispatch import async_paginate_keyset, sync_paginate_keyset
from market_sdk._internal.request import KeysetPaginatedSpec
from market_sdk.errors import TransportError, UnexpectedResponseError, UserInputError
from market_sdk.pagination import AsyncPaginator, Page, Paginator
from market_sdk.site_config import SITE_CONFIG

_CACHE_TTL_SECONDS = 30 * 60
_WALLET = re.compile(r"^0x[0-9a-fA-F]{40}$")
_T = TypeVar("_T")


@dataclass(frozen=True)
class _CacheEntry:
    query: str
    expires_at: float


_cache: dict[str, _CacheEntry] = {}
_cache_lock = Lock()
_async_pending: dict[tuple[asyncio.AbstractEventLoop, str], asyncio.Task[str]] = {}


def _site_origin(site_url: str) -> str:
    raw = site_url.strip()
    candidate = raw if raw.startswith(("http://", "https://")) else f"https://{raw}"
    parsed = urlparse(candidate)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise UserInputError("invalid site_url for creator filtering")
    return f"{parsed.scheme}://{parsed.netloc}"


def _parse_manifest(payload: object) -> str:
    if not isinstance(payload, dict):
        raise UnexpectedResponseError("creator manifest must contain wallets")
    wallets = cast(dict[str, object], payload).get("wallets")
    if not isinstance(wallets, list):
        raise UnexpectedResponseError("creator manifest must contain wallets")
    wallets = cast(list[object], wallets)
    normalized = sorted(
        {
            wallet.strip().lower()
            for wallet in wallets
            if isinstance(wallet, str) and _WALLET.fullmatch(wallet.strip())
        }
    )
    if not normalized:
        raise UnexpectedResponseError("creator manifest has no valid wallets")
    return ",".join(normalized)


def _cached(origin: str) -> str | None:
    entry = _cache.get(origin)
    return entry.query if entry and entry.expires_at > time.monotonic() else None


def get_site_creator_query(site_url: str) -> str:
    origin = _site_origin(site_url)
    with _cache_lock:
        cached = _cached(origin)
        if cached is not None:
            return cached
        endpoint = f"{origin}/api/allowed-market-creators"
        try:
            response = httpx.get(endpoint, timeout=12)
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise TransportError(f"creator manifest request failed: {error}") from error
        try:
            query = _parse_manifest(response.json())
        except ValueError as error:
            raise UnexpectedResponseError("invalid creator manifest JSON") from error
        _cache[origin] = _CacheEntry(query, time.monotonic() + _CACHE_TTL_SECONDS)
        return query


async def async_get_site_creator_query(site_url: str) -> str:
    origin = _site_origin(site_url)
    cached = _cached(origin)
    if cached is not None:
        return cached
    key = (asyncio.get_running_loop(), origin)
    pending = _async_pending.get(key)
    if pending is None:

        async def fetch_query() -> str:
            endpoint = f"{origin}/api/allowed-market-creators"
            try:
                async with httpx.AsyncClient(timeout=12) as client:
                    response = await client.get(endpoint)
                    response.raise_for_status()
            except httpx.HTTPError as error:
                raise TransportError(f"creator manifest request failed: {error}") from error
            try:
                query = _parse_manifest(response.json())
            except ValueError as error:
                raise UnexpectedResponseError("invalid creator manifest JSON") from error
            _cache[origin] = _CacheEntry(query, time.monotonic() + _CACHE_TTL_SECONDS)
            return query

        pending = asyncio.create_task(fetch_query())
        _async_pending[key] = pending
        pending.add_done_callback(
            lambda done: _async_pending.pop(key, None) if _async_pending.get(key) is done else None
        )
    return await asyncio.shield(pending)


def resolve_sync_creator(creator: str | Sequence[str] | None) -> str | Sequence[str] | None:
    site_url = SITE_CONFIG["site_url"].strip()
    if not site_url:
        return creator
    if creator is not None:
        raise UserInputError("creator cannot override a configured operator site")
    return get_site_creator_query(site_url)


async def resolve_async_creator(creator: str | Sequence[str] | None) -> str | Sequence[str] | None:
    site_url = SITE_CONFIG["site_url"].strip()
    if not site_url:
        return creator
    if creator is not None:
        raise UserInputError("creator cannot override a configured operator site")
    return await async_get_site_creator_query(site_url)


def scope_sync_keyset(
    ctx: SyncClientContext, spec: KeysetPaginatedSpec[_T], *, page_size: int
) -> Paginator[_T]:
    site_url = SITE_CONFIG["site_url"].strip()
    if not site_url:
        return sync_paginate_keyset(ctx, spec, page_size=page_size)
    if spec.base_params and "creator" in spec.base_params:
        raise UserInputError("creator cannot override a configured operator site")

    def fetch(cursor: str | None) -> Page[_T]:
        query = get_site_creator_query(site_url)
        scoped = replace(spec, base_params={**(spec.base_params or {}), "creator": query})
        paginator = sync_paginate_keyset(ctx, scoped, page_size=page_size)
        return (paginator if cursor is None else paginator.from_cursor(cursor)).first_page()

    return Paginator(fetch)


def scope_async_keyset(
    ctx: AsyncClientContext, spec: KeysetPaginatedSpec[_T], *, page_size: int
) -> AsyncPaginator[_T]:
    site_url = SITE_CONFIG["site_url"].strip()
    if not site_url:
        return async_paginate_keyset(ctx, spec, page_size=page_size)
    if spec.base_params and "creator" in spec.base_params:
        raise UserInputError("creator cannot override a configured operator site")

    async def fetch(cursor: str | None) -> Page[_T]:
        query = await async_get_site_creator_query(site_url)
        scoped = replace(spec, base_params={**(spec.base_params or {}), "creator": query})
        paginator = async_paginate_keyset(ctx, scoped, page_size=page_size)
        return await (paginator if cursor is None else paginator.from_cursor(cursor)).first_page()

    return AsyncPaginator(fetch)
