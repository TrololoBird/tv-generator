from unittest import mock

from src.generator.yaml_generator import _supported_timeframes


def test_supported_timeframes_parsed() -> None:
    text = (
        "Timeframe codes map to minutes unless otherwise noted:\n"
        "```\n"
        "1, 5 -> minutes\n"
        "1D -> 1 day\n"
        "1W -> 1 week\n"
        "```"
    )
    with mock.patch("pathlib.Path.read_text", return_value=text):
        assert _supported_timeframes() == ["1", "5", "1D", "1W"]


def test_supported_timeframes_default() -> None:
    with mock.patch("pathlib.Path.read_text", return_value="no block"):
        frames = _supported_timeframes()
    assert frames == ["1", "5", "15", "30", "60", "120", "240", "1D", "1W"]
