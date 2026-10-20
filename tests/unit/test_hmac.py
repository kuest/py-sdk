import base64
import hashlib
import hmac

from market_sdk._internal.hmac import build_hmac_signature

_SECRET = "dGVzdC1zZWNyZXQ="
_RAW_SECRET = base64.urlsafe_b64decode(_SECRET)


def test_build_hmac_signature_matches_manual_hmac_for_get_request() -> None:
    timestamp = 1700000000
    method = "GET"
    path = "/auth/api-keys"

    signature = build_hmac_signature(
        secret=_SECRET,
        timestamp=timestamp,
        method=method,
        path=path,
    )

    expected_message = f"{timestamp}{method}{path}".encode()
    expected = base64.urlsafe_b64encode(
        hmac.new(_RAW_SECRET, expected_message, hashlib.sha256).digest()
    ).decode("ascii")
    assert signature == expected


def test_build_hmac_signature_includes_body_when_provided() -> None:
    timestamp = 1700000000
    method = "POST"
    path = "/orders"
    body = '{"a":1}'

    signature = build_hmac_signature(
        secret=_SECRET,
        timestamp=timestamp,
        method=method,
        path=path,
        body=body,
    )

    expected_message = f"{timestamp}{method}{path}{body}".encode()
    expected = base64.urlsafe_b64encode(
        hmac.new(_RAW_SECRET, expected_message, hashlib.sha256).digest()
    ).decode("ascii")
    assert signature == expected


def test_build_hmac_signature_is_deterministic_for_same_inputs() -> None:
    sig_a = build_hmac_signature(secret=_SECRET, timestamp=1700000000, method="GET", path="/foo")
    sig_b = build_hmac_signature(secret=_SECRET, timestamp=1700000000, method="GET", path="/foo")

    assert sig_a == sig_b


def test_build_hmac_signature_differs_with_body_versus_without() -> None:
    no_body = build_hmac_signature(secret=_SECRET, timestamp=1700000000, method="POST", path="/x")
    with_body = build_hmac_signature(
        secret=_SECRET, timestamp=1700000000, method="POST", path="/x", body="{}"
    )

    assert no_body != with_body


def test_build_hmac_signature_accepts_secret_without_padding() -> None:
    secret_no_pad = "dGVzdC1zZWNyZXQ"

    sig_padded = build_hmac_signature(secret=_SECRET, timestamp=1, method="GET", path="/x")
    sig_unpadded = build_hmac_signature(secret=secret_no_pad, timestamp=1, method="GET", path="/x")

    assert sig_padded == sig_unpadded


def test_build_hmac_signature_wraps_bad_base64_secret_as_signing_error() -> None:
    import pytest

    from market_sdk.errors import SigningError

    with pytest.raises(SigningError, match="HMAC"):
        build_hmac_signature(secret="!!!not-base64!!!", timestamp=1, method="GET", path="/x")
