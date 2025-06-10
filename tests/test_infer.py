from src.utils.infer import infer_type


def test_infer_type_number():
    assert infer_type(1) == "integer"
    assert infer_type("10") == "integer"
    assert infer_type(1.5) == "number"


def test_infer_type_string():
    assert infer_type("abc") == "string"


def test_infer_type_nan():
    assert infer_type(None) == "string"


def test_infer_type_date():
    assert infer_type("2023-01-01") == "string"
    assert infer_type("2023-01-01T00:00:00Z") == "string"


def test_infer_type_boolean():
    assert infer_type(True) == "boolean"
    assert infer_type(False) == "boolean"
    assert infer_type("true") == "boolean"
    assert infer_type("False") == "boolean"
