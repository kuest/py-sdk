# pyright: reportPrivateUsage=false

from typing import NoReturn

import pytest

from market_sdk import PRODUCTION, Environment, PublicClient, configured_environment
from market_sdk._internal import context as context_module
from market_sdk._internal.environment import PRODUCTION_CONFIG


def test_environment_only_exposes_its_name() -> None:
    assert PRODUCTION.name == "production"
    assert {name for name in dir(PRODUCTION) if not name.startswith("_")} == {"name"}
    assert repr(PRODUCTION) == "Environment(name='production')"


def test_environment_cannot_be_constructed_directly() -> None:
    with pytest.raises(TypeError, match="provided by the SDK"):
        Environment()


def test_client_context_reuses_ingested_environment_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_lookup(_environment: Environment) -> NoReturn:
        raise AssertionError("context should reuse the config resolved by the client")

    monkeypatch.setattr(context_module, "get_environment_config", unexpected_lookup)

    with PublicClient() as client:
        assert client._ctx.environment_config is PRODUCTION_CONFIG


def test_configured_environment_requires_explicit_secure_endpoints() -> None:
    config = configured_environment(
        clob_url="https://clob.example.test",
        clob_ws_url="wss://ws.example.test",
        relayer_url="https://relay.example.test",
        gamma_url="https://gamma.example.test",
        data_url="https://data.example.test",
        rpc_url="https://rpc.example.test",
    )._config
    assert config.clob_url == "https://clob.example.test"
    assert config.clob_market_ws_url == "wss://ws.example.test/ws/market"
    assert config.rpc_url == "https://rpc.example.test"

    with pytest.raises(ValueError, match="HTTPS"):
        configured_environment(
            clob_url="https://clob.example.test",
            clob_ws_url="wss://ws.example.test",
            relayer_url="https://relay.example.test",
            gamma_url="https://gamma.example.test",
            data_url="https://data.example.test",
            rpc_url="http://rpc.example.test",
        )
