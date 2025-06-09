from src.utils.infer import infer_type


def test_infer_type_number():
    assert infer_type(1) == "number"
    assert infer_type("10") == "number"


def test_infer_type_string():
    assert infer_type("abc") == "string"
