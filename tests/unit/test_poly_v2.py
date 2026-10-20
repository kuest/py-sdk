import pytest

from market_sdk._internal.actions.clob import build_midpoint_request
from market_sdk._internal.actions.orders.context import resolve_order_exchange_address
from market_sdk._internal.actions.relayer.positions import derive_combo_outcome_position_ids
from market_sdk._internal.environment import PRODUCTION_CONFIG
from market_sdk._internal.protocol import decode_v2_outcome_position_id, is_v2_position_id
from market_sdk.errors import UserInputError
from market_sdk.models.gamma import Market
from market_sdk.models.types import PositionId

_BINARY_CONDITION_ID = "0x01" + "00" * 30
_YES_POSITION_ID = PositionId(str(int(_BINARY_CONDITION_ID + "00", 16)))


def test_protocol_v2_position_ids_use_reserved_bit_namespace() -> None:
    assert is_v2_position_id(_YES_POSITION_ID)
    assert is_v2_position_id(bin(int(_YES_POSITION_ID)))
    assert is_v2_position_id(oct(int(_YES_POSITION_ID)))
    assert not is_v2_position_id(str(1 << 40))
    assert not is_v2_position_id("not-an-id")
    assert not is_v2_position_id("1_0")


def test_protocol_v2_position_decoder_supports_all_v2_modules() -> None:
    for module_id in (1, 2, 3):
        condition_id = f"0x{module_id:02x}" + "ab" * 30
        position_id = PositionId(str(int(condition_id + "01", 16)))
        decoded = decode_v2_outcome_position_id(position_id)
        assert decoded.condition_id == condition_id
        assert decoded.outcome_index == 1


def test_v2_outcome_derivation_rejects_bytes32_condition_id() -> None:
    with pytest.raises(UserInputError, match="31-byte"):
        derive_combo_outcome_position_ids("0x" + "ab" * 32)


def test_gamma_market_exposes_position_id_per_outcome() -> None:
    market = Market.parse_response(
        {
            "id": "1",
            "conditionId": _BINARY_CONDITION_ID,
            "outcomes": ["Yes", "No"],
            "outcomePrices": ["0.6", "0.4"],
            "clobTokenIds": [],
            "positionIds": ["11", "12"],
        }
    )
    assert market.outcomes.yes.position_id == "11"
    assert market.outcomes.no.position_id == "12"
    assert market.outcomes.yes.token_id is None


def test_clob_read_accepts_asset_id_and_preserves_wire_parameter() -> None:
    assert build_midpoint_request(asset_id="123") == ("/midpoint", {"token_id": "123"})
    try:
        build_midpoint_request(asset_id="123", token_id="456")
    except UserInputError as error:
        assert "mutually exclusive" in str(error)
    else:
        raise AssertionError("expected mutually exclusive identifier error")


def test_v2_order_is_rejected_before_signing() -> None:
    with pytest.raises(UserInputError, match="Position-backed V3 orders"):
        resolve_order_exchange_address(PRODUCTION_CONFIG, asset_id=_YES_POSITION_ID, neg_risk=False)
