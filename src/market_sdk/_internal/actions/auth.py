from typing import cast

from pydantic import TypeAdapter, ValidationError

from market_sdk._internal.actions.relayer.auth import build_builder_key_headers
from market_sdk._internal.l1_auth import ApiKeyAuthSignature
from market_sdk.auth import BuilderApiKey
from market_sdk.clients._transport import AsyncTransport, SyncTransport
from market_sdk.errors import RequestRejectedError, UnexpectedResponseError
from market_sdk.models.clob import ApiKeyCreds, BuilderApiKeyInfo

_BUILDER_API_KEY_PATH = "/auth/builder-api-key"

_ApiKeysListAdapter = TypeAdapter(tuple[str, ...])
_BuilderApiKeyInfoListAdapter = TypeAdapter(tuple[BuilderApiKeyInfo, ...])


def build_l1_auth_headers(signature: ApiKeyAuthSignature) -> dict[str, str]:
    return {
        "KUEST_ADDRESS": signature.address,
        "KUEST_NONCE": str(signature.nonce),
        "KUEST_SIGNATURE": signature.signature,
        "KUEST_TIMESTAMP": str(signature.timestamp),
    }


def parse_api_key_creds(data: object) -> ApiKeyCreds:
    return ApiKeyCreds.parse_response(data)


def parse_api_keys_response(data: object) -> tuple[str, ...]:
    try:
        return _ApiKeysListAdapter.validate_python(data)
    except ValidationError as error:
        raise UnexpectedResponseError("api keys response did not match expected shape") from error


def parse_builder_api_key_creds(data: object) -> BuilderApiKey:
    if not isinstance(data, dict):
        raise UnexpectedResponseError("builder api key response did not match expected shape")
    fields = cast(dict[str, object], data)
    key = fields.get("apiKey")
    secret = fields.get("secret")
    passphrase = fields.get("passphrase")
    if not (isinstance(key, str) and isinstance(secret, str) and isinstance(passphrase, str)):
        raise UnexpectedResponseError("builder api key response did not match expected shape")
    return BuilderApiKey(key=key, secret=secret, passphrase=passphrase)


def parse_builder_api_keys_response(data: object) -> tuple[BuilderApiKeyInfo, ...]:
    if not isinstance(data, list):
        raise UnexpectedResponseError("builder api keys response did not match expected shape")
    normalized = [
        {"key": item} if isinstance(item, str) else item for item in cast(list[object], data)
    ]
    try:
        return _BuilderApiKeyInfoListAdapter.validate_python(normalized)
    except ValidationError as error:
        raise UnexpectedResponseError(
            "builder api keys response did not match expected shape"
        ) from error


async def create_api_key(clob: AsyncTransport, signature: ApiKeyAuthSignature) -> ApiKeyCreds:
    payload = await clob.post_json("/auth/api-key", headers=build_l1_auth_headers(signature))
    return parse_api_key_creds(payload)


async def derive_api_key(clob: AsyncTransport, signature: ApiKeyAuthSignature) -> ApiKeyCreds:
    payload = await clob.get_json("/auth/derive-api-key", headers=build_l1_auth_headers(signature))
    return parse_api_key_creds(payload)


async def create_or_derive_api_key(
    clob: AsyncTransport, signature: ApiKeyAuthSignature
) -> ApiKeyCreds:
    try:
        return await create_api_key(clob, signature)
    except RequestRejectedError as error:
        if error.status != 400:
            raise
    return await derive_api_key(clob, signature)


async def fetch_api_keys(secure_clob: AsyncTransport) -> tuple[str, ...]:
    payload = await secure_clob.get_json("/auth/api-keys")
    return parse_api_keys_response(payload)


async def delete_api_key(secure_clob: AsyncTransport) -> None:
    payload = await secure_clob.delete_json("/auth/api-key")
    if payload != {"revoked": True}:
        raise UnexpectedResponseError(
            f"delete api key response did not match expected shape: {payload!r}"
        )


async def create_builder_api_key(
    relayer: AsyncTransport, signature: ApiKeyAuthSignature
) -> BuilderApiKey:
    payload = await relayer.post_json(
        _BUILDER_API_KEY_PATH, headers=build_l1_auth_headers(signature)
    )
    return parse_builder_api_key_creds(payload)


async def fetch_builder_api_keys(
    relayer: AsyncTransport, *, headers: dict[str, str] | None = None
) -> tuple[BuilderApiKeyInfo, ...]:
    payload = await relayer.get_json(_BUILDER_API_KEY_PATH, headers=headers)
    return parse_builder_api_keys_response(payload)


async def revoke_builder_api_key(relayer: AsyncTransport, builder_key: BuilderApiKey) -> None:
    headers = build_builder_key_headers(
        creds=builder_key, method="DELETE", path=_BUILDER_API_KEY_PATH
    )
    payload = await relayer.delete_json(_BUILDER_API_KEY_PATH, headers=headers)
    if payload != {"revoked": True}:
        raise UnexpectedResponseError(
            f"revoke builder api key response did not match expected shape: {payload!r}"
        )


def create_api_key_sync(clob: SyncTransport, signature: ApiKeyAuthSignature) -> ApiKeyCreds:
    payload = clob.post_json("/auth/api-key", headers=build_l1_auth_headers(signature))
    return parse_api_key_creds(payload)


def derive_api_key_sync(clob: SyncTransport, signature: ApiKeyAuthSignature) -> ApiKeyCreds:
    payload = clob.get_json("/auth/derive-api-key", headers=build_l1_auth_headers(signature))
    return parse_api_key_creds(payload)


def create_or_derive_api_key_sync(
    clob: SyncTransport, signature: ApiKeyAuthSignature
) -> ApiKeyCreds:
    try:
        return create_api_key_sync(clob, signature)
    except RequestRejectedError as error:
        if error.status != 400:
            raise
    return derive_api_key_sync(clob, signature)


def fetch_api_keys_sync(secure_clob: SyncTransport) -> tuple[str, ...]:
    payload = secure_clob.get_json("/auth/api-keys")
    return parse_api_keys_response(payload)


def delete_api_key_sync(secure_clob: SyncTransport) -> None:
    payload = secure_clob.delete_json("/auth/api-key")
    if payload != {"revoked": True}:
        raise UnexpectedResponseError(
            f"delete api key response did not match expected shape: {payload!r}"
        )


def create_builder_api_key_sync(
    relayer: SyncTransport, signature: ApiKeyAuthSignature
) -> BuilderApiKey:
    payload = relayer.post_json(_BUILDER_API_KEY_PATH, headers=build_l1_auth_headers(signature))
    return parse_builder_api_key_creds(payload)


def fetch_builder_api_keys_sync(
    relayer: SyncTransport, *, headers: dict[str, str] | None = None
) -> tuple[BuilderApiKeyInfo, ...]:
    payload = relayer.get_json(_BUILDER_API_KEY_PATH, headers=headers)
    return parse_builder_api_keys_response(payload)


def revoke_builder_api_key_sync(relayer: SyncTransport, builder_key: BuilderApiKey) -> None:
    headers = build_builder_key_headers(
        creds=builder_key, method="DELETE", path=_BUILDER_API_KEY_PATH
    )
    payload = relayer.delete_json(_BUILDER_API_KEY_PATH, headers=headers)
    if payload != {"revoked": True}:
        raise UnexpectedResponseError(
            f"revoke builder api key response did not match expected shape: {payload!r}"
        )


__all__ = [
    "build_l1_auth_headers",
    "create_api_key",
    "create_api_key_sync",
    "create_builder_api_key",
    "create_builder_api_key_sync",
    "create_or_derive_api_key",
    "create_or_derive_api_key_sync",
    "delete_api_key",
    "delete_api_key_sync",
    "derive_api_key",
    "derive_api_key_sync",
    "fetch_api_keys",
    "fetch_api_keys_sync",
    "fetch_builder_api_keys",
    "fetch_builder_api_keys_sync",
    "parse_api_key_creds",
    "parse_api_keys_response",
    "parse_builder_api_key_creds",
    "parse_builder_api_keys_response",
    "revoke_builder_api_key",
    "revoke_builder_api_key_sync",
]
