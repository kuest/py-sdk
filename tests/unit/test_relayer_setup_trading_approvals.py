# pyright: reportPrivateUsage=false
import asyncio
from urllib.parse import urlparse

import httpx
import pytest
from _relayer_helpers import (
    install_relayer_routes,
    install_rpc_handler,
    make_deposit_client,
    make_safe_client,
    request_json,
    trading_approval_rpc_handler,
)
from eth_utils.crypto import keccak

from market_sdk._internal.environment import PRODUCTION_CONFIG
from market_sdk.errors import UserInputError


def _selector(sig: str) -> str:
    return "0x" + keccak(sig.encode("ascii"))[:4].hex()


def test_setup_trading_approvals_bundles_required_calls_for_deposit_wallet() -> None:
    captured: list[httpx.Request] = []

    async def run() -> None:
        client = await make_deposit_client()
        install_relayer_routes(
            client,
            captured,
            {
                "/v1/account/transactions/params": {
                    "address": client._ctx.signer.address,
                    "nonce": "0",
                },
                "/submit": {
                    "state": "STATE_NEW",
                    "transactionHash": None,
                    "transactionID": "tx-setup",
                },
                "/transaction": [
                    {
                        "state": "STATE_CONFIRMED",
                        "transactionHash": "0x" + "ab" * 32,
                        "transactionID": "tx-setup",
                    }
                ],
            },
        )
        install_rpc_handler(client, trading_approval_rpc_handler())
        try:
            await client.setup_trading_approvals()
        finally:
            await client.close()

    asyncio.run(run())
    submit_calls = [r for r in captured if urlparse(str(r.url)).path == "/submit"]
    assert len(submit_calls) == 1
    body = request_json(submit_calls[0])
    assert body["type"] == "WALLET"
    inner = body["depositWalletParams"]["calls"]
    assert len(inner) == 4

    erc20_sel = _selector("approve(address,uint256)")
    erc1155_sel = _selector("setApprovalForAll(address,bool)")
    # ERC20 approvals: the two supported exchange spenders.
    for index, spender in enumerate(
        [
            PRODUCTION_CONFIG.standard_exchange,
            PRODUCTION_CONFIG.neg_risk_exchange,
        ]
    ):
        assert inner[index]["target"].lower() == PRODUCTION_CONFIG.collateral_token.lower()
        assert inner[index]["data"].startswith(erc20_sel)
        assert spender[2:].lower() in inner[index]["data"].lower()
    # ERC1155 conditional-token approvals: the same two exchanges.
    for offset, operator in enumerate(
        [
            PRODUCTION_CONFIG.standard_exchange,
            PRODUCTION_CONFIG.neg_risk_exchange,
        ]
    ):
        index = 2 + offset
        assert inner[index]["target"].lower() == PRODUCTION_CONFIG.conditional_tokens.lower()
        assert inner[index]["data"].startswith(erc1155_sel)
        assert operator[2:].lower() in inner[index]["data"].lower()

    assert body["metadata"] == "Trading setup approvals"


def test_setup_trading_approvals_skips_submit_when_already_approved() -> None:
    captured: list[httpx.Request] = []

    async def run() -> None:
        client = await make_deposit_client()
        install_relayer_routes(client, captured, {})
        install_rpc_handler(
            client,
            trading_approval_rpc_handler(allowance=(1 << 256) - 1, approved=True),
        )
        try:
            handle = await client.setup_trading_approvals()
            await handle.wait()
        finally:
            await client.close()

    asyncio.run(run())
    submit_calls = [r for r in captured if urlparse(str(r.url)).path == "/submit"]
    assert submit_calls == []


def test_setup_trading_approvals_rejects_unsupported_safe_wallet() -> None:
    captured: list[httpx.Request] = []

    async def run() -> None:
        client = await make_safe_client()
        install_relayer_routes(
            client,
            captured,
            {
                "/v1/account/transactions/params": {
                    "address": client._ctx.signer.address,
                    "nonce": "0",
                },
                "/submit": {
                    "state": "STATE_NEW",
                    "transactionHash": None,
                    "transactionID": "tx-setup-safe",
                },
                "/v1/account/transactions/tx-setup-safe": {
                    "state": "STATE_CONFIRMED",
                    "transaction_hash": "0x" + "cd" * 32,
                    "transaction_id": "tx-setup-safe",
                },
            },
        )
        install_rpc_handler(client, trading_approval_rpc_handler())
        try:
            with pytest.raises(UserInputError, match="Deposit Wallet only"):
                await client.setup_trading_approvals()
        finally:
            await client.close()

    asyncio.run(run())
    submit_calls = [r for r in captured if urlparse(str(r.url)).path == "/submit"]
    assert submit_calls == []
