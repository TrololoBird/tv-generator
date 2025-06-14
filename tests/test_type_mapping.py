from src.utils.type_mapping import tv2ref, TV_TYPE_TO_REF
import pytest


@pytest.mark.parametrize("tv_type,ref", TV_TYPE_TO_REF.items())
def test_tv2ref_known_types(tv_type: str, ref: str) -> None:
    assert tv2ref(tv_type) == ref


def test_tv2ref_unknown_type() -> None:
    ref = tv2ref("unknown")
    assert ref == "#/components/schemas/Str"


def test_tv2ref_new_types() -> None:
    assert tv2ref("duration") == "#/components/schemas/Num"
    assert tv2ref("percentage") == "#/components/schemas/Num"
