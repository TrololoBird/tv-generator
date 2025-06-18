import pytest
import click
from src.utils.fs import load_yaml


def test_load_yaml_invalid(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(": bad")
    with pytest.raises(click.ClickException) as exc:
        load_yaml(bad)
    assert "Invalid YAML" in str(exc.value)
