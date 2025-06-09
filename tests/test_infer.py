# flake8: noqa
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))  # noqa: E402

from utils.infer import infer_type


def test_infer_type_number():
    assert infer_type(1) == "number"
    assert infer_type("10") == "number"


def test_infer_type_string():
    assert infer_type("abc") == "string"
