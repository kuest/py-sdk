from __future__ import annotations

from dataclasses import InitVar, dataclass, field

from eth_account.signers.local import LocalAccount

from market_sdk._internal.actions.orders.cache import (
    AsyncOrderMetadataCache,
    SyncOrderMetadataCache,
)
from market_sdk._internal.environment import EnvironmentConfig, get_environment_config
from market_sdk._internal.eoa.rpc import JsonRpcClient, SyncJsonRpcClient
from market_sdk._internal.wallet import SignerType, WalletType
from market_sdk.auth import ApiKey
from market_sdk.clients._transport import AsyncTransport, SyncTransport
from market_sdk.environments import Environment
from market_sdk.models.clob import ApiKeyCreds
from market_sdk.types import EvmAddress


@dataclass(frozen=True, slots=True, kw_only=True)
class SyncClientContext:
    environment: Environment
    environment_config: EnvironmentConfig = field(init=False, repr=False)
    gamma: SyncTransport
    data: SyncTransport
    rfq: SyncTransport
    clob: SyncTransport
    _resolved_environment_config: InitVar[EnvironmentConfig | None] = None

    def __post_init__(self, _resolved_environment_config: EnvironmentConfig | None) -> None:
        config = _resolved_environment_config or get_environment_config(self.environment)
        object.__setattr__(self, "environment_config", config)


@dataclass(frozen=True, slots=True, kw_only=True)
class SyncSecureClientContext(SyncClientContext):
    signer: LocalAccount
    credentials: ApiKeyCreds
    secure_clob: SyncTransport
    wallet: EvmAddress
    wallet_type: WalletType
    signer_type: SignerType
    relayer: SyncTransport
    combos: SyncTransport
    builder_gateway: SyncTransport
    api_key: ApiKey | None
    rpc: SyncJsonRpcClient
    order_metadata: SyncOrderMetadataCache


@dataclass(frozen=True, slots=True, kw_only=True)
class AsyncClientContext:
    environment: Environment
    environment_config: EnvironmentConfig = field(init=False, repr=False)
    gamma: AsyncTransport
    data: AsyncTransport
    rfq: AsyncTransport
    clob: AsyncTransport
    perps: AsyncTransport
    _resolved_environment_config: InitVar[EnvironmentConfig | None] = None

    def __post_init__(self, _resolved_environment_config: EnvironmentConfig | None) -> None:
        config = _resolved_environment_config or get_environment_config(self.environment)
        object.__setattr__(self, "environment_config", config)


@dataclass(frozen=True, slots=True, kw_only=True)
class AsyncSecureClientContext(AsyncClientContext):
    signer: LocalAccount
    credentials: ApiKeyCreds
    secure_clob: AsyncTransport
    wallet: EvmAddress
    wallet_type: WalletType
    signer_type: SignerType
    relayer: AsyncTransport
    combos: AsyncTransport
    builder_gateway: AsyncTransport
    api_key: ApiKey | None
    rpc: JsonRpcClient
    order_metadata: AsyncOrderMetadataCache


__all__ = [
    "AsyncClientContext",
    "AsyncSecureClientContext",
    "SyncClientContext",
    "SyncSecureClientContext",
]
