from __future__ import annotations

from market_sdk.clients._transport import AsyncTransport, SyncTransport
from market_sdk.errors import UserInputError
from market_sdk.models.clob.relayer import RelayerExecuteParams, RelayerTransactionType


async def fetch_execute_params(
    relayer: AsyncTransport,
    *,
    address: str,
    type: RelayerTransactionType,
) -> RelayerExecuteParams:
    if type != RelayerTransactionType.WALLET:
        raise UserInputError("SDK relayer nonce requests require WALLET.")
    data = await relayer.get_json(
        "/nonce",
        params={"address": address, "type": type.value},
    )
    return RelayerExecuteParams.parse_response({"address": address, "nonce": data["nonce"]})


def fetch_execute_params_sync(
    relayer: SyncTransport,
    *,
    address: str,
    type: RelayerTransactionType,
) -> RelayerExecuteParams:
    if type != RelayerTransactionType.WALLET:
        raise UserInputError("SDK relayer nonce requests require WALLET.")
    data = relayer.get_json(
        "/nonce",
        params={"address": address, "type": type.value},
    )
    return RelayerExecuteParams.parse_response({"address": address, "nonce": data["nonce"]})


async def fetch_relay_payload(
    relayer: AsyncTransport,
    *,
    address: str,
    type: RelayerTransactionType,
) -> RelayerExecuteParams:
    data = await relayer.get_json(
        "/relay-payload",
        params={"address": address, "type": type.value},
    )
    return RelayerExecuteParams.parse_response(data)


def fetch_relay_payload_sync(
    relayer: SyncTransport,
    *,
    address: str,
    type: RelayerTransactionType,
) -> RelayerExecuteParams:
    data = relayer.get_json(
        "/relay-payload",
        params={"address": address, "type": type.value},
    )
    return RelayerExecuteParams.parse_response(data)


__all__ = [
    "fetch_execute_params",
    "fetch_execute_params_sync",
    "fetch_relay_payload",
    "fetch_relay_payload_sync",
]
