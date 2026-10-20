import pytest

from market_sdk.models import to_combo_condition_id, to_ctf_condition_id

COMBO_CONDITION_ID = "0x032def24bfb0c5c57fb236fac08b94236a0000000000000000000000000000"
CTF_CONDITION_ID = "0x5c19f205507ce03ff5f3be08a8090a5969ea6870cc07b902a4ca2e61dfe48fdd"


def test_to_ctf_condition_id_accepts_31_and_32_byte_hex_strings() -> None:
    assert to_ctf_condition_id(COMBO_CONDITION_ID) == COMBO_CONDITION_ID
    assert to_ctf_condition_id(CTF_CONDITION_ID) == CTF_CONDITION_ID


def test_to_ctf_condition_id_rejects_malformed_values() -> None:
    with pytest.raises(TypeError, match="31-byte or 32-byte hex string"):
        to_ctf_condition_id("0x1234")
    with pytest.raises(TypeError, match="31-byte or 32-byte hex string"):
        to_ctf_condition_id("0xZZ" + "11" * 30)


def test_to_combo_condition_id_normalizes_supported_wire_forms() -> None:
    assert to_combo_condition_id(COMBO_CONDITION_ID) == COMBO_CONDITION_ID
    assert to_combo_condition_id(f"{COMBO_CONDITION_ID}00") == COMBO_CONDITION_ID
    assert to_combo_condition_id(f"{COMBO_CONDITION_ID}01") == COMBO_CONDITION_ID


def test_to_combo_condition_id_rejects_non_combo_and_non_binary_wire_forms() -> None:
    with pytest.raises(TypeError, match="combo condition ID"):
        to_combo_condition_id("0x022def24bfb0c5c57fb236fac08b94236a0000000000000000000000000000")
    with pytest.raises(TypeError, match="combo condition ID"):
        to_combo_condition_id(f"{COMBO_CONDITION_ID}02")
