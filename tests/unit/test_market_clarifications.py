import asyncio
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
import respx
from eth_account import Account

from market_sdk import (
    ApiKeyCreds,
    AsyncPublicClient,
    AsyncSecureClient,
    MarketClarification,
    MarketClarificationState,
    Page,
    PublicClient,
    SecureClient,
    configured_environment,
)
from market_sdk.errors import UnexpectedResponseError, UserInputError
from market_sdk.site_config import SITE_CONFIG

_ENV = configured_environment(
    clob_url="https://clob.test",
    clob_ws_url="wss://clob-ws.test",
    relayer_url="https://relayer.test",
    gamma_url="https://gamma.test",
    data_url="https://data.test",
    rpc_url="https://rpc.test",
)
_CONDITION_ID = "0x" + "12" * 32
_QUESTION_ID = "0x" + "34" * 32
_TX_HASH = "0x" + "56" * 32
_CREATOR = "0x" + "a1" * 20
_TEST_SIGNER = "0x" + "ab" * 32
_TEST_WALLET = Account.from_key(_TEST_SIGNER).address
_TEST_CREDENTIALS = ApiKeyCreds(key="test-key", passphrase="test-passphrase", secret="dGVzdA==")


def note(note_id: int, **overrides: object) -> dict[str, object]:
    return {
        "id": note_id,
        "marketId": 42,
        "eventId": 7,
        "questionId": _QUESTION_ID,
        "content": "Use the official published results.",
        "state": "success",
        "showInFrontend": True,
        "clearBook": True,
        "source": "polymarket",
        "sourceMarketId": 31,
        "txHash": _TX_HASH,
        "txTimestamp": "2026-11-24T19:30:00Z",
        **overrides,
    }


@pytest.mark.parametrize("mode", ["sync", "async"])
@pytest.mark.parametrize("secure", [False, True])
def test_client_filters_and_paginates_market_clarifications(mode: str, secure: bool) -> None:
    responses = iter(
        (
            httpx.Response(
                200, json=[note(10), note(11, marketId=None, conditionId=_CONDITION_ID)]
            ),
            httpx.Response(200, json=[note(12, clearBook=None, txTimestamp=None)]),
        )
    )
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return next(responses)

    filters: dict[str, Any] = {
        "market_ids": [42, _CONDITION_ID],
        "event_ids": [7, "8"],
        "question_ids": [_QUESTION_ID],
        "tx_hash": [_TX_HASH],
        "state": MarketClarificationState.SUCCESS,
        "show_in_frontend": True,
        "creator": _CREATOR,
        "order": "id,tx_timestamp",
        "ascending": True,
        "page_size": 2,
    }
    with respx.mock as router:
        if secure:
            router.get("https://clob.test/auth/api-keys").respond(json=[_TEST_CREDENTIALS.key])
        route = router.get("https://gamma.test/market-clarifications")
        route.side_effect = respond

        if mode == "sync":
            with (
                SecureClient.create(
                    private_key=_TEST_SIGNER,
                    wallet=_TEST_WALLET,
                    credentials=_TEST_CREDENTIALS,
                    environment=_ENV,
                )
                if secure
                else PublicClient(environment=_ENV)
            ) as client:
                pages = list(client.list_market_clarifications(**filters))
        else:

            async def collect() -> list[Page[MarketClarification]]:
                client = (
                    await AsyncSecureClient.create(
                        private_key=_TEST_SIGNER,
                        wallet=_TEST_WALLET,
                        credentials=_TEST_CREDENTIALS,
                        environment=_ENV,
                    )
                    if secure
                    else AsyncPublicClient(environment=_ENV)
                )
                async with client:
                    return [page async for page in client.list_market_clarifications(**filters)]

            pages = asyncio.run(collect())

    assert [[entry.id for entry in page.items] for page in pages] == [[10, 11], [12]]
    assert pages[0].has_more
    assert not pages[1].has_more
    published, native_id_only = pages[0].items
    assert isinstance(published, MarketClarification)
    assert published.market_id == "42"
    assert published.event_id == "7"
    assert published.source_market_id == "31"
    assert published.content == "Use the official published results."
    assert published.state is MarketClarificationState.SUCCESS
    assert published.clear_book is True
    assert published.tx_timestamp == datetime(2026, 11, 24, 19, 30, tzinfo=UTC)
    assert native_id_only.market_id is None
    assert native_id_only.condition_id == _CONDITION_ID
    assert all("authorization" not in request.headers for request in requests)
    for offset, request in zip((0, 2), requests, strict=True):
        params = request.url.params
        assert params.get_list("market_id") == ["42", _CONDITION_ID]
        assert params.get_list("event_id") == ["7", "8"]
        assert params.get_list("question_id") == [_QUESTION_ID]
        assert params.get_list("tx_hash") == [_TX_HASH]
        assert params.get_list("state") == ["success"]
        assert params["show_in_frontend"] == "true"
        assert params["creator"] == _CREATOR
        assert params["order"] == "id,tx_timestamp"
        assert params["ascending"] == "true"
        assert params["limit"] == "2"
        assert params["offset"] == str(offset)


@pytest.mark.parametrize("mode", ["sync", "async"])
def test_configured_operator_scopes_the_lazy_paginator(
    mode: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    site = f"https://clarifications-{mode}-operator.test"
    monkeypatch.setitem(SITE_CONFIG, "site_url", site)
    with respx.mock as router:
        manifest = router.get(f"{site}/api/allowed-market-creators").respond(
            json={"wallets": [_CREATOR]}
        )
        listing = router.get("https://gamma.test/market-clarifications").respond(json=[])

        if mode == "sync":
            with PublicClient(environment=_ENV) as client:
                result = client.list_market_clarifications(market_ids=42)
                assert not manifest.called
                with pytest.raises(UserInputError, match="cannot override"):
                    client.list_market_clarifications(creator=_CREATOR)
                with pytest.raises(UserInputError, match="100"):
                    client.list_market_clarifications(page_size=101)
                assert not listing.called
                assert result.first_page().items == ()
        else:

            async def collect() -> None:
                async with AsyncPublicClient(environment=_ENV) as client:
                    result = client.list_market_clarifications(market_ids=42)
                    assert not manifest.called
                    with pytest.raises(UserInputError, match="cannot override"):
                        client.list_market_clarifications(creator=_CREATOR)
                    with pytest.raises(UserInputError, match="100"):
                        client.list_market_clarifications(page_size=101)
                    assert not listing.called
                    assert (await result.first_page()).items == ()

            asyncio.run(collect())

        assert manifest.call_count == 1
        assert listing.calls.last.request.url.params["creator"] == _CREATOR
        assert listing.calls.last.request.url.params["market_id"] == "42"


def test_invalid_response_is_reported_without_yielding_invalid_notes() -> None:
    with respx.mock as router, PublicClient(environment=_ENV) as client:
        router.get("https://gamma.test/market-clarifications").respond(
            json=[note(2, state="invalid")]
        )
        with pytest.raises(UnexpectedResponseError, match="MarketClarification"):
            client.list_market_clarifications().first_page()


def test_rejects_filters_larger_than_the_endpoint_limit() -> None:
    with (
        PublicClient(environment=_ENV) as client,
        pytest.raises(UserInputError, match="market_id accepts at most 100"),
    ):
        client.list_market_clarifications(market_ids=list(range(101)))
