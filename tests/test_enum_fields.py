"""
Tests for enum field handling in OpenAPIPipeline.
"""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from loguru import logger

from tv_generator.core import OpenAPIPipeline


class TestEnumFieldHandling:
    """Test enum field processing in OpenAPI schema generation."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            data_dir = temp_path / "data"
            specs_dir = temp_path / "specs"
            results_dir = temp_path / "results"

            # Create directory structure
            data_dir.mkdir()
            specs_dir.mkdir()
            results_dir.mkdir()
            (data_dir / "metainfo").mkdir()
            (data_dir / "markets.json").write_text('["test_market"]')
            (data_dir / "column_display_names.json").write_text('{"signal_type": "Signal Type"}')

            yield {"data_dir": data_dir, "specs_dir": specs_dir, "results_dir": results_dir, "temp_path": temp_path}

    @pytest.fixture
    def valid_enum_metainfo(self) -> list[dict[str, Any]]:
        """Valid enum field metadata."""
        return [
            {
                "n": "signal_type",
                "t": "string",
                "r": [{"id": "BUY", "name": "Buy"}, {"id": "SELL", "name": "Sell"}, {"id": "HOLD", "name": "Hold"}],
            },
            {"n": "price", "t": "number", "r": []},  # Empty enum
            {
                "n": "volume",
                "t": "integer",
                "r": [{"id": 1, "name": "Low"}, {"id": 2, "name": "Medium"}, {"id": 3, "name": "High"}],
            },
        ]

    @pytest.fixture
    def malformed_enum_metainfo(self) -> list[dict[str, Any]]:
        """Malformed enum field metadata."""
        return [
            {
                "n": "broken_enum",
                "t": "string",
                "r": [{"id": 123, "name": "One"}, {"id": "ABC", "name": "Two"}],  # Integer in string field
            },
            {
                "n": "mixed_types",
                "t": "integer",
                "r": [{"id": 1, "name": "One"}, {"id": "two", "name": "Two"}],  # String in integer field
            },
            {"n": "not_list", "t": "string", "r": "not a list"},  # Not a list
            {"n": "empty_list", "t": "string", "r": []},  # Empty list
        ]

    def test_valid_enum_field(self, temp_dirs, valid_enum_metainfo):
        """Test that valid enum fields are correctly processed."""
        # Setup
        data_dir = temp_dirs["data_dir"]
        specs_dir = temp_dirs["specs_dir"]

        # Write metainfo
        metainfo_file = data_dir / "metainfo" / "test_market.json"
        metainfo_file.write_text(json.dumps({"fields": valid_enum_metainfo}))

        # Create pipeline
        pipeline = OpenAPIPipeline(data_dir=data_dir, specs_dir=specs_dir, skip_enum_validation=False)

        # Generate spec
        spec = pipeline.generate_openapi_spec("test_market")

        # Assertions
        market_data_schema = spec["components"]["schemas"]["MarketData"]
        properties = market_data_schema["properties"]

        # Check signal_type enum
        signal_type = properties["signal_type"]
        assert signal_type["type"] == "string"
        assert "enum" in signal_type
        assert signal_type["enum"] == ["BUY", "SELL", "HOLD"]

        # Check volume enum (integer)
        volume = properties["volume"]
        assert volume["type"] == "integer"
        assert "enum" in volume
        assert volume["enum"] == [1, 2, 3]

        # Check price (no enum due to empty r)
        price = properties["price"]
        assert price["type"] == "number"
        assert "enum" not in price

    def test_malformed_enum_field(self, temp_dirs, malformed_enum_metainfo, caplog):
        """Test that malformed enum fields are handled correctly with warnings."""
        # Setup
        data_dir = temp_dirs["data_dir"]
        specs_dir = temp_dirs["specs_dir"]

        # Write metainfo
        metainfo_file = data_dir / "metainfo" / "test_market.json"
        metainfo_file.write_text(json.dumps({"fields": malformed_enum_metainfo}))

        # Create pipeline
        pipeline = OpenAPIPipeline(data_dir=data_dir, specs_dir=specs_dir, skip_enum_validation=False)

        # Generate spec
        spec = pipeline.generate_openapi_spec("test_market")

        # Assertions
        market_data_schema = spec["components"]["schemas"]["MarketData"]
        properties = market_data_schema["properties"]

        # Check broken_enum (should not have enum due to type mismatch)
        broken_enum = properties["broken_enum"]
        assert broken_enum["type"] == "string"
        assert "enum" not in broken_enum

        # Check mixed_types (should not have enum due to type mismatch)
        mixed_types = properties["mixed_types"]
        assert mixed_types["type"] == "integer"
        assert "enum" not in mixed_types

        # Check not_list (should not have enum due to malformed r)
        not_list = properties["not_list"]
        assert not_list["type"] == "string"
        assert "enum" not in not_list

        # Check empty_list (should not have enum due to empty r)
        empty_list = properties["empty_list"]
        assert empty_list["type"] == "string"
        assert "enum" not in empty_list

        # Check warnings were logged
        log_records = [record.message for record in caplog.records]
        assert any("[enum/type]" in msg for msg in log_records)
        assert any("[enum/malformed]" in msg for msg in log_records)
        assert any("[enum/empty]" in msg for msg in log_records)

    def test_skip_enum_validation_flag(self, temp_dirs, malformed_enum_metainfo, caplog):
        """Test that skip_enum_validation flag bypasses validation."""
        # Setup
        data_dir = temp_dirs["data_dir"]
        specs_dir = temp_dirs["specs_dir"]

        # Write metainfo
        metainfo_file = data_dir / "metainfo" / "test_market.json"
        metainfo_file.write_text(json.dumps({"fields": malformed_enum_metainfo}))

        # Create pipeline with skip_enum_validation=True
        pipeline = OpenAPIPipeline(data_dir=data_dir, specs_dir=specs_dir, skip_enum_validation=True)

        # Generate spec
        spec = pipeline.generate_openapi_spec("test_market")

        # Assertions
        market_data_schema = spec["components"]["schemas"]["MarketData"]
        properties = market_data_schema["properties"]

        # Check broken_enum (should have enum despite type mismatch)
        broken_enum = properties["broken_enum"]
        assert broken_enum["type"] == "string"
        assert "enum" in broken_enum
        assert broken_enum["enum"] == [123, "ABC"]  # Mixed types passed through

        # Check mixed_types (should have enum despite type mismatch)
        mixed_types = properties["mixed_types"]
        assert mixed_types["type"] == "integer"
        assert "enum" in mixed_types
        assert mixed_types["enum"] == [1, "two"]  # Mixed types passed through

        # Check not_list (should have enum despite malformed r)
        not_list = properties["not_list"]
        assert not_list["type"] == "string"
        assert "enum" in not_list
        assert not_list["enum"] == ["not a list"]  # Non-list passed through

        # Check empty_list (should have enum despite empty r)
        empty_list = properties["empty_list"]
        assert empty_list["type"] == "string"
        assert "enum" in empty_list
        assert empty_list["enum"] == []  # Empty list passed through

        # Check unsafe mode warning was logged
        log_records = [record.message for record in caplog.records]
        assert any("[enum/unsafe]" in msg for msg in log_records)

    def test_enum_validation_parameter_override(self, temp_dirs, malformed_enum_metainfo, caplog):
        """Test that skip_enum_validation parameter can override instance setting."""
        # Setup
        data_dir = temp_dirs["data_dir"]
        specs_dir = temp_dirs["specs_dir"]

        # Write metainfo
        metainfo_file = data_dir / "metainfo" / "test_market.json"
        metainfo_file.write_text(json.dumps({"fields": malformed_enum_metainfo}))

        # Create pipeline with skip_enum_validation=False (default)
        pipeline = OpenAPIPipeline(data_dir=data_dir, specs_dir=specs_dir, skip_enum_validation=False)

        # Generate spec with skip_enum_validation=True (override)
        spec = pipeline.generate_openapi_spec("test_market", skip_enum_validation=True)

        # Assertions - should behave like skip_enum_validation=True
        market_data_schema = spec["components"]["schemas"]["MarketData"]
        properties = market_data_schema["properties"]

        broken_enum = properties["broken_enum"]
        assert "enum" in broken_enum
        assert broken_enum["enum"] == [123, "ABC"]

        # Check unsafe mode warning was logged
        log_records = [record.message for record in caplog.records]
        assert any("[enum/unsafe]" in msg for msg in log_records)

    def test_enum_with_verified_fields(self, temp_dirs, valid_enum_metainfo):
        """Test enum handling when using verified fields filter."""
        # Setup
        data_dir = temp_dirs["data_dir"]
        specs_dir = temp_dirs["specs_dir"]

        # Write metainfo
        metainfo_file = data_dir / "metainfo" / "test_market.json"
        metainfo_file.write_text(json.dumps({"fields": valid_enum_metainfo}))

        # Create pipeline
        pipeline = OpenAPIPipeline(data_dir=data_dir, specs_dir=specs_dir, skip_enum_validation=False)

        # Generate spec with only signal_type as verified field
        verified_fields = ["signal_type"]
        spec = pipeline.generate_openapi_spec("test_market", verified_fields=verified_fields)

        # Assertions
        market_data_schema = spec["components"]["schemas"]["MarketData"]
        properties = market_data_schema["properties"]

        # Should only have signal_type
        assert len(properties) == 1
        assert "signal_type" in properties

        # Check enum is preserved
        signal_type = properties["signal_type"]
        assert signal_type["type"] == "string"
        assert "enum" in signal_type
        assert signal_type["enum"] == ["BUY", "SELL", "HOLD"]

    def test_enum_field_example_generation(self, temp_dirs):
        """Test that enum field examples use the first enum value."""
        # Setup
        data_dir = temp_dirs["data_dir"]
        specs_dir = temp_dirs["specs_dir"]

        metainfo = [
            {
                "n": "test_enum",
                "t": "string",
                "r": [{"id": "FIRST", "name": "First Value"}, {"id": "SECOND", "name": "Second Value"}],
            }
        ]

        metainfo_file = data_dir / "metainfo" / "test_market.json"
        metainfo_file.write_text(json.dumps({"fields": metainfo}))

        # Create pipeline
        pipeline = OpenAPIPipeline(data_dir=data_dir, specs_dir=specs_dir, skip_enum_validation=False)

        # Generate spec
        spec = pipeline.generate_openapi_spec("test_market")

        # Assertions
        market_data_schema = spec["components"]["schemas"]["MarketData"]
        properties = market_data_schema["properties"]

        test_enum = properties["test_enum"]
        assert test_enum["example"] == "FIRST"  # Should use first enum value

    def test_enum_with_direct_values(self, temp_dirs):
        """Test enum handling when r contains direct values instead of objects."""
        # Setup
        data_dir = temp_dirs["data_dir"]
        specs_dir = temp_dirs["specs_dir"]

        metainfo = [
            {"n": "direct_enum", "t": "string", "r": ["A", "B", "C"]},  # Direct string values
            {"n": "direct_int_enum", "t": "integer", "r": [1, 2, 3]},  # Direct integer values
        ]

        metainfo_file = data_dir / "metainfo" / "test_market.json"
        metainfo_file.write_text(json.dumps({"fields": metainfo}))

        # Create pipeline
        pipeline = OpenAPIPipeline(data_dir=data_dir, specs_dir=specs_dir, skip_enum_validation=False)

        # Generate spec
        spec = pipeline.generate_openapi_spec("test_market")

        # Assertions
        market_data_schema = spec["components"]["schemas"]["MarketData"]
        properties = market_data_schema["properties"]

        direct_enum = properties["direct_enum"]
        assert direct_enum["type"] == "string"
        assert "enum" in direct_enum
        assert direct_enum["enum"] == ["A", "B", "C"]

        direct_int_enum = properties["direct_int_enum"]
        assert direct_int_enum["type"] == "integer"
        assert "enum" in direct_int_enum
        assert direct_int_enum["enum"] == [1, 2, 3]
