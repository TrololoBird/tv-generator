from src.utils.type_mapping import tv2ref, TV_TYPE_TO_REF
import pytest


@pytest.mark.parametrize("tv_type,ref", TV_TYPE_TO_REF.items())
def test_tv2ref_known_types(tv_type: str, ref: str) -> None:
    assert tv2ref(tv_type) == ref


def test_tv2ref_unknown_type() -> None:
    with pytest.raises(KeyError):
        tv2ref("unknown")
