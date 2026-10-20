from market_sdk._internal.data_params import build_data_params


def test_build_data_params_drops_none_values() -> None:
    assert build_data_params({"a": "x", "b": None, "c": 1}) == {"a": "x", "c": 1}


def test_build_data_params_joins_sequences_with_commas() -> None:
    assert build_data_params({"market": ["0xabc", "0xdef"]}) == {"market": "0xabc,0xdef"}


def test_build_data_params_drops_empty_sequences() -> None:
    assert build_data_params({"market": [], "limit": 5}) == {"limit": 5}


def test_build_data_params_preserves_scalars() -> None:
    assert build_data_params({"limit": 5, "verified": True, "rate": 1.5}) == {
        "limit": 5,
        "verified": True,
        "rate": 1.5,
    }


def test_build_data_params_handles_int_sequence() -> None:
    assert build_data_params({"ids": [1, 2, 3]}) == {"ids": "1,2,3"}
