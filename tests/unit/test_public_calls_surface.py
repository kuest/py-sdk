def test_public_calls_module_re_exports() -> None:
    from market_sdk import calls

    assert hasattr(calls, "TransactionCall")
    assert hasattr(calls, "MAX_UINT256")
    assert hasattr(calls, "erc20_approval_call")
    assert hasattr(calls, "erc20_transfer_call")
    assert hasattr(calls, "erc1155_set_approval_for_all_call")
    assert hasattr(calls, "split_position_call")
    assert hasattr(calls, "merge_positions_call")
    assert hasattr(calls, "ctf_redeem_positions_call")
    assert hasattr(calls, "encode_proxy_call")
    assert hasattr(calls, "encode_safe_multisend_call")


def test_transaction_call_re_exported_at_top_level() -> None:
    from market_sdk import TransactionCall

    assert TransactionCall is not None


def test_public_calls_can_construct_transaction_call() -> None:
    from market_sdk.calls import (
        MAX_UINT256,
        TransactionCall,
        erc20_approval_call,
    )
    from market_sdk.types import EvmAddress

    call = erc20_approval_call(
        token_address=EvmAddress("0xDDeeAa11220000000000000000000000000000aA"),
        spender=EvmAddress("0x000000000000000000000000000000000000dEaD"),
        amount=MAX_UINT256,
    )
    assert isinstance(call, TransactionCall)
    assert call.data.lower().endswith("f" * 64)
