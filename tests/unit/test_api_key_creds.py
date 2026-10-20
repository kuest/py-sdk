from market_sdk import ApiKeyCreds


def test_api_key_creds_repr_does_not_leak_any_field() -> None:
    creds = ApiKeyCreds(key="visible-key", passphrase="sneaky-passphrase", secret="sneaky-secret")

    rendered = repr(creds)

    assert "visible-key" not in rendered
    assert "sneaky-passphrase" not in rendered
    assert "sneaky-secret" not in rendered
    assert "redacted" in rendered


def test_api_key_creds_str_does_not_leak_any_field() -> None:
    creds = ApiKeyCreds(key="visible-key", passphrase="sneaky-passphrase", secret="sneaky-secret")

    rendered = str(creds)

    assert "visible-key" not in rendered
    assert "sneaky-passphrase" not in rendered
    assert "sneaky-secret" not in rendered


def test_api_key_creds_attributes_still_accessible() -> None:
    creds = ApiKeyCreds(key="k", passphrase="p", secret="s")

    assert creds.key == "k"
    assert creds.passphrase == "p"
    assert creds.secret == "s"
