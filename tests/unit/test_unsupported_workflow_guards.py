"""Unsupported upstream mutation paths must fail before any network request."""

import pytest
from _relayer_helpers import SPENDER, TOKEN, make_sync_deposit_client, make_sync_proxy_client

from market_sdk.errors import UserInputError


def test_combo_quote_fails_before_network() -> None:
    with (
        make_sync_deposit_client() as client,
        pytest.raises(UserInputError, match="combo RFQ and position-backed V3"),
    ):
        client.request_combo_quote(leg_position_ids=["1", "2"], direction="BUY", amount="1")


def test_combo_acceptance_fails_before_signing() -> None:
    with (
        make_sync_deposit_client() as client,
        pytest.raises(UserInputError, match="combo RFQ and position-backed V3"),
    ):
        client.accept_combo_quote({})


def test_collateral_return_fails_before_network() -> None:
    with (
        make_sync_deposit_client() as client,
        pytest.raises(UserInputError, match="collateral return and protocol V2"),
    ):
        client.plan_collateral_return()


def test_session_key_management_fails_before_network() -> None:
    with make_sync_deposit_client() as client:
        with pytest.raises(UserInputError, match="Session-key management is not supported"):
            client.fetch_session_keys()
        with pytest.raises(UserInputError, match="Session-key management is not supported"):
            client.authorize_session_key(address=SPENDER)
        with pytest.raises(UserInputError, match="Session-key management is not supported"):
            client.revoke_session_key(address=SPENDER)


def test_proxy_relayer_submission_fails_before_network() -> None:
    with (
        make_sync_proxy_client() as client,
        pytest.raises(UserInputError, match="Deposit Wallet only"),
    ):
        client.approve_erc20(token_address=TOKEN, spender_address=SPENDER, amount=1)
