"""SDK environment configuration for the local SDK adaptation."""

from dataclasses import dataclass, field, replace


@dataclass(frozen=True, slots=True, kw_only=True)
class _WalletDerivation:
    proxy_factory: str
    proxy_implementation: str
    safe_factory: str
    safe_init_code_hash: str
    deposit_wallet_factory: str
    deposit_wallet_implementation: str
    deposit_wallet_beacon: str


@dataclass(frozen=True, slots=True, kw_only=True)
class _EnvironmentConfig:
    chain_id: int
    wallet_derivation: _WalletDerivation
    collateral_token: str
    conditional_tokens: str
    neg_risk_adapter: str
    collateral_adapter: str
    neg_risk_collateral_adapter: str
    standard_exchange: str
    neg_risk_exchange: str
    auto_redeem_operator: str
    safe_multisend: str
    relay_hub: str
    clob_url: str
    clob_market_ws_url: str
    clob_user_ws_url: str
    relayer_url: str
    gamma_url: str
    data_url: str
    rfq_url: str
    rtds_ws_url: str
    sports_ws_url: str
    rpc_url: str
    exchange_v3: str = "0xe3333700cA9d93003F00f0F71f8515005F6c00Aa"
    protocol_v2_router: str = "0x12121212006e4CD160D18e3f00711DA5c3372600"
    binary_module: str = "0x1000008dD9001B968442c1000017eaE6E0dA00Ba"
    neg_risk_module: str = "0x200000900045e3B6259600682756002200028933"
    combinatorial_module: str = "0x30000034706c7d8e12009dab006be20000c031a8"
    position_manager: str = "0x006F54F7f9A22e0000CC2AB60031000000ae9fEF"
    rfq_quoter_ws_url: str = "wss://unconfigured.invalid/ws/rfq"
    rfq_quoter_ws_headers: dict[str, str] | None = None
    builder_gateway_url: str = "https://unconfigured.invalid"
    collateral_return_url: str = "https://unconfigured.invalid"
    perps_url: str = "https://unconfigured.invalid"
    perps_ws_url: str = "wss://unconfigured.invalid/v1/ws"
    realtime_ws_url: str = "wss://unconfigured.invalid/ws"
    realtime_ws_headers: dict[str, str] | None = None
    perps_deposit_contract: str = "0xDCa4af75705dbB50f62437045afF9921947917d2"
    relayer_max_polls: int = 100
    relayer_poll_frequency_ms: int = 2000


@dataclass(frozen=True, slots=True, init=False)
class Environment:
    """An SDK environment identified by its public name."""

    name: str
    _config: _EnvironmentConfig = field(repr=False)

    def __init__(self) -> None:
        raise TypeError("Environment instances are provided by the SDK")


def _create_environment(*, name: str, config: _EnvironmentConfig) -> Environment:
    environment = object.__new__(Environment)
    object.__setattr__(environment, "name", name)
    object.__setattr__(environment, "_config", config)
    return environment


PRODUCTION = _create_environment(
    name="production",
    config=_EnvironmentConfig(
        chain_id=137,
        wallet_derivation=_WalletDerivation(
            proxy_factory="0xaB45c5A4B0c941a2F231C04C3f49182e1A254052",
            proxy_implementation="0x44e999d5c2F66Ef0861317f9A4805AC2e90aEB4f",
            safe_factory="0xaacFeEa03eb1561C4e67d661e40682Bd20E3541b",
            safe_init_code_hash="0x2bce2127ff07fb632d16c8347c4ebf501f4841168bed00d9e6ef715ddb6fcecf",
            deposit_wallet_factory="0x2CcdC6C5dDcd895aFcCD259F291de9b618A5cA6c",
            deposit_wallet_implementation="0x65507Fa36589B3b2ceD54E77999909e843691e44",
            deposit_wallet_beacon="0x74a618eBdd62Ff8579A8FE94f5B888d7623b9C35",
        ),
        collateral_token="0x3c499c542cef5e3811e1192ce70d8cc03d5c3359",
        conditional_tokens="0x4682048725865bf17067bd85fF518527A262A9C7",
        neg_risk_adapter="0xd9416E904e1ab925ad72F03F6D6ce0Aa80fd2dC5",
        collateral_adapter="0xAdA100Db00Ca00073811820692005400218FcE1f",
        neg_risk_collateral_adapter="0xadA2005600Dec949baf300f4C6120000bDB6eAab",
        standard_exchange="0xaa1b8dE834E16eC69C044F5300041673C968c9eF",
        neg_risk_exchange="0xe7FA09cA716FDf498d74AFF618d32AFeacc310aB",
        auto_redeem_operator="0xa1200000d0002264C9a1698e001292D00E1b00af",
        safe_multisend="0xA238CBeb142c10Ef7Ad8442C6D1f9E89e07e7761",
        relay_hub="0xE2a6dC9a931538adB7efFA2E1D9eC60a65735117",
        clob_url="https://unconfigured.invalid",
        clob_market_ws_url="wss://unconfigured.invalid/ws/market",
        clob_user_ws_url="wss://unconfigured.invalid/ws/user",
        relayer_url="https://unconfigured.invalid",
        gamma_url="https://unconfigured.invalid",
        data_url="https://unconfigured.invalid",
        rfq_url="https://unconfigured.invalid",
        rtds_ws_url="wss://unconfigured.invalid",
        sports_ws_url="wss://unconfigured.invalid/ws",
        rpc_url="https://unconfigured.invalid",
    ),
)


def configured_environment(
    *,
    clob_url: str,
    clob_ws_url: str,
    relayer_url: str,
    gamma_url: str,
    data_url: str,
    rpc_url: str,
) -> Environment:
    """Use integrator-approved SDK endpoints with the local contract configuration."""
    rest_urls = (clob_url, relayer_url, gamma_url, data_url, rpc_url)
    if any(not url.startswith("https://") for url in rest_urls):
        raise ValueError("SDK REST endpoints must use HTTPS")
    if not clob_ws_url.startswith("wss://"):
        raise ValueError("SDK CLOB WebSocket endpoint must use WSS")
    base_ws = clob_ws_url.rstrip("/")
    config = replace(
        PRODUCTION._config,  # pyright: ignore[reportPrivateUsage]
        clob_url=clob_url,
        clob_market_ws_url=f"{base_ws}/ws/market",
        clob_user_ws_url=f"{base_ws}/ws/user",
        relayer_url=relayer_url,
        gamma_url=gamma_url,
        data_url=data_url,
        rpc_url=rpc_url,
    )
    return _create_environment(name="configured", config=config)


__all__ = ["Environment", "PRODUCTION", "configured_environment"]
