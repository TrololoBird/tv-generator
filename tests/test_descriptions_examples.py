"""
Tests for description and example functionality in OpenAPI schema generation.
"""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from tv_generator.core import OpenAPIPipeline


class TestDescriptionsAndExamples:
    """Test description and example handling in field schemas."""

    @pytest.fixture
    def temp_dirs(self, tmp_path):
        """Create temporary directories for testing."""
        data_dir = tmp_path / "data"
        specs_dir = tmp_path / "specs"
        data_dir.mkdir()
        specs_dir.mkdir()

        # Create minimal markets.json
        (data_dir / "markets.json").write_text('["test_market"]')

        # Create minimal column_display_names.json
        (data_dir / "column_display_names.json").write_text('{"test_market": "Test Market"}')

        # Create metainfo directory and file
        metainfo_dir = data_dir / "metainfo"
        metainfo_dir.mkdir()

        yield {"data_dir": data_dir, "specs_dir": specs_dir, "temp_path": tmp_path}

    @pytest.fixture
    def sample_metainfo(self):
        """Sample metainfo with descriptions and examples."""
        return [
            {"n": "price", "t": "number", "d": "Current stock price in USD", "e": 123.45},
            {"n": "volume", "t": "integer", "d": "Trading volume for the day", "e": 1000000},
            {"n": "symbol", "t": "string", "d": "Stock symbol", "e": "AAPL"},
            {"n": "is_active", "t": "bool", "d": "Whether the stock is currently active", "e": True},
            {"n": "no_description", "t": "string", "e": "example_value"},
            {"n": "no_example", "t": "number", "d": "Field without example"},
            {"n": "bad_example_type", "t": "number", "d": "Field with wrong example type", "e": "not_a_number"},
            {
                "n": "multiline_description",
                "t": "string",
                "d": "This is a description\nwith multiple lines\nand extra   spaces",
                "e": "test",
            },
            {"n": "long_description", "t": "string", "d": "A" * 600, "e": "test"},  # Very long description
        ]

    def test_field_with_valid_description_and_example(self, temp_dirs, sample_metainfo):
        """Test field with valid description and example."""
        # Write metainfo
        metainfo_file = temp_dirs["data_dir"] / "metainfo" / "test_market.json"
        metainfo_file.write_text(json.dumps(sample_metainfo))

        # Create pipeline
        pipeline = OpenAPIPipeline(data_dir=temp_dirs["data_dir"], specs_dir=temp_dirs["specs_dir"], no_examples=False)

        # Generate spec
        spec = pipeline.generate_openapi_spec("test_market")

        # Check that price field has description and example
        price_field = spec["components"]["schemas"]["Field"]["properties"]["price"]
        assert "description" in price_field
        assert price_field["description"] == "Current stock price in USD"
        assert "example" in price_field
        assert price_field["example"] == 123.45

    def test_field_with_invalid_example_type(self, temp_dirs, sample_metainfo):
        """Test field with example that doesn't match field type."""
        # Write metainfo
        metainfo_file = temp_dirs["data_dir"] / "metainfo" / "test_market.json"
        metainfo_file.write_text(json.dumps(sample_metainfo))

        # Create pipeline
        pipeline = OpenAPIPipeline(data_dir=temp_dirs["data_dir"], specs_dir=temp_dirs["specs_dir"], no_examples=False)

        # Generate spec
        spec = pipeline.generate_openapi_spec("test_market")

        # Check that bad_example_type field has description but no example
        bad_field = spec["components"]["schemas"]["Field"]["properties"]["bad_example_type"]
        assert "description" in bad_field
        assert bad_field["description"] == "Field with wrong example type"
        assert "example" not in bad_field  # Should be dropped due to type mismatch

    def test_field_without_description(self, temp_dirs, sample_metainfo):
        """Test field without description but with example."""
        # Write metainfo
        metainfo_file = temp_dirs["data_dir"] / "metainfo" / "test_market.json"
        metainfo_file.write_text(json.dumps(sample_metainfo))

        # Create pipeline
        pipeline = OpenAPIPipeline(data_dir=temp_dirs["data_dir"], specs_dir=temp_dirs["specs_dir"], no_examples=False)

        # Generate spec
        spec = pipeline.generate_openapi_spec("test_market")

        # Check that no_description field has example but no description
        no_desc_field = spec["components"]["schemas"]["Field"]["properties"]["no_description"]
        assert "description" not in no_desc_field
        assert "example" in no_desc_field
        assert no_desc_field["example"] == "example_value"

    def test_field_without_example(self, temp_dirs, sample_metainfo):
        """Test field with description but without example."""
        # Write metainfo
        metainfo_file = temp_dirs["data_dir"] / "metainfo" / "test_market.json"
        metainfo_file.write_text(json.dumps(sample_metainfo))

        # Create pipeline
        pipeline = OpenAPIPipeline(data_dir=temp_dirs["data_dir"], specs_dir=temp_dirs["specs_dir"], no_examples=False)

        # Generate spec
        spec = pipeline.generate_openapi_spec("test_market")

        # Check that no_example field has description but generated example
        no_example_field = spec["components"]["schemas"]["Field"]["properties"]["no_example"]
        assert "description" in no_example_field
        assert no_example_field["description"] == "Field without example"
        assert "example" in no_example_field  # Should have generated example

    def test_no_examples_flag(self, temp_dirs, sample_metainfo):
        """Test behavior with --no-examples flag enabled."""
        # Write metainfo
        metainfo_file = temp_dirs["data_dir"] / "metainfo" / "test_market.json"
        metainfo_file.write_text(json.dumps(sample_metainfo))

        # Create pipeline with no_examples=True
        pipeline = OpenAPIPipeline(data_dir=temp_dirs["data_dir"], specs_dir=temp_dirs["specs_dir"], no_examples=True)

        # Generate spec
        spec = pipeline.generate_openapi_spec("test_market")

        # Check that no fields have examples
        for field_name, field_schema in spec["components"]["schemas"]["Field"]["properties"].items():
            assert "example" not in field_schema, f"Field {field_name} should not have example when no_examples=True"

        # But descriptions should still be present
        price_field = spec["components"]["schemas"]["Field"]["properties"]["price"]
        assert "description" in price_field
        assert price_field["description"] == "Current stock price in USD"

    def test_description_normalization(self, temp_dirs, sample_metainfo):
        """Test that descriptions are normalized (newlines removed, whitespace trimmed)."""
        # Write metainfo
        metainfo_file = temp_dirs["data_dir"] / "metainfo" / "test_market.json"
        metainfo_file.write_text(json.dumps(sample_metainfo))

        # Create pipeline
        pipeline = OpenAPIPipeline(data_dir=temp_dirs["data_dir"], specs_dir=temp_dirs["specs_dir"], no_examples=False)

        # Generate spec
        spec = pipeline.generate_openapi_spec("test_market")

        # Check that multiline description is normalized
        multiline_field = spec["components"]["schemas"]["Field"]["properties"]["multiline_description"]
        assert "description" in multiline_field
        expected_desc = "This is a description with multiple lines and extra spaces"
        assert multiline_field["description"] == expected_desc

    def test_description_truncation(self, temp_dirs, sample_metainfo):
        """Test that very long descriptions are truncated."""
        # Write metainfo
        metainfo_file = temp_dirs["data_dir"] / "metainfo" / "test_market.json"
        metainfo_file.write_text(json.dumps(sample_metainfo))

        # Create pipeline
        pipeline = OpenAPIPipeline(data_dir=temp_dirs["data_dir"], specs_dir=temp_dirs["specs_dir"], no_examples=False)

        # Generate spec
        spec = pipeline.generate_openapi_spec("test_market")

        # Check that long description is truncated
        long_field = spec["components"]["schemas"]["Field"]["properties"]["long_description"]
        assert "description" in long_field
        assert len(long_field["description"]) <= 500
        assert long_field["description"].endswith("...")

    def test_example_type_validation(self, temp_dirs):
        """Test example type validation for different field types."""
        metainfo = [
            {"n": "string_field", "t": "string", "e": "valid_string"},
            {"n": "number_field", "t": "number", "e": 123.45},
            {"n": "integer_field", "t": "integer", "e": 42},
            {"n": "bool_field", "t": "bool", "e": True},
            {"n": "array_field", "t": "set", "e": ["a", "b"]},
            {"n": "object_field", "t": "map", "e": {"key": "value"}},
            # Invalid examples
            {"n": "string_with_number", "t": "string", "e": 123},
            {"n": "number_with_string", "t": "number", "e": "not_a_number"},
            {"n": "bool_with_string", "t": "bool", "e": "not_a_bool"},
        ]

        # Write metainfo
        metainfo_file = temp_dirs["data_dir"] / "metainfo" / "test_market.json"
        metainfo_file.write_text(json.dumps(metainfo))

        # Create pipeline
        pipeline = OpenAPIPipeline(data_dir=temp_dirs["data_dir"], specs_dir=temp_dirs["specs_dir"], no_examples=False)

        # Generate spec
        spec = pipeline.generate_openapi_spec("test_market")

        # Check valid examples are included
        valid_fields = ["string_field", "number_field", "integer_field", "bool_field", "array_field", "object_field"]
        for field_name in valid_fields:
            field = spec["components"]["schemas"]["Field"]["properties"][field_name]
            assert "example" in field, f"Field {field_name} should have example"

        # Check invalid examples are dropped
        invalid_fields = ["string_with_number", "number_with_string", "bool_with_string"]
        for field_name in invalid_fields:
            field = spec["components"]["schemas"]["Field"]["properties"][field_name]
            assert "example" not in field, f"Field {field_name} should not have example due to type mismatch"

    def test_statistics_logging(self, temp_dirs, sample_metainfo, caplog):
        """Test that statistics are logged correctly."""
        import logging

        from loguru import logger as loguru_logger

        # Forward loguru logs to standard logging for pytest caplog
        class PropagateHandler(logging.Handler):
            def emit(self, record):
                logging.getLogger(record.name).handle(record)

        propagate_handler = PropagateHandler()
        logging.getLogger().addHandler(propagate_handler)
        loguru_logger.add(propagate_handler, format="{message}")

        # Write metainfo
        metainfo_file = temp_dirs["data_dir"] / "metainfo" / "test_market.json"
        metainfo_file.write_text(json.dumps(sample_metainfo))

        # Create pipeline
        pipeline = OpenAPIPipeline(data_dir=temp_dirs["data_dir"], specs_dir=temp_dirs["specs_dir"], no_examples=False)

        # Generate spec
        spec = pipeline.generate_openapi_spec("test_market")

        # Check that statistics are logged
        log_messages = [record.message for record in caplog.records]

        # Should have description and example statistics
        desc_logs = [msg for msg in log_messages if "fields with descriptions" in msg]
        example_logs = [msg for msg in log_messages if "fields with examples" in msg]

        assert len(desc_logs) > 0, "Should log description statistics"
        assert len(example_logs) > 0, "Should log example statistics"

        # Check that the counts are reasonable
        total_fields = len(spec["components"]["schemas"]["Field"]["properties"])
        assert total_fields > 0, "Should have fields in spec"

        # Remove handler after test
        loguru_logger.remove()
        logging.getLogger().removeHandler(propagate_handler)
