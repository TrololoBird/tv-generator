"""
Tests for OpenAPI metadata generation (tags, operationId, summary, description).
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from tv_generator.core import OpenAPIPipeline


class TestOpenAPIMetadata:
    """Test OpenAPI metadata generation."""

    @pytest.fixture
    def pipeline(self):
        """Create a test pipeline instance."""
        return OpenAPIPipeline(
            data_dir=Path("tests/test_data"),
            specs_dir=Path("tests/test_specs"),
            tag_format="default",
            include_metadata=True,
        )

    @pytest.fixture
    def sample_metainfo(self):
        """Sample metainfo for testing."""
        return [
            {
                "n": "name",
                "t": "string",
                "d": "Company name",
                "e": "Apple Inc.",
            },
            {
                "n": "price",
                "t": "number",
                "d": "Current stock price",
                "e": 150.25,
            },
            {
                "n": "sector",
                "t": "string",
                "d": "Business sector",
                "r": [{"id": "technology"}, {"id": "healthcare"}],
            },
        ]

    def test_generate_market_tag_default(self, pipeline):
        """Test tag generation in default format."""
        # Mock display names
        pipeline.display_names = {"crypto": "Cryptocurrency", "america": "US Stocks"}

        tag = pipeline._generate_market_tag("crypto")
        assert tag == "Cryptocurrency Screener"

        tag = pipeline._generate_market_tag("america")
        assert tag == "US Stocks Screener"

        # Test fallback to title case
        tag = pipeline._generate_market_tag("forex")
        assert tag == "Forex Screener"

    def test_generate_market_tag_technical(self, pipeline):
        """Test tag generation in technical format."""
        pipeline.tag_format = "technical"

        tag = pipeline._generate_market_tag("crypto")
        assert tag == "CRYPTO_SCREENER"

        tag = pipeline._generate_market_tag("us_stocks")
        assert tag == "US_STOCKS_SCREENER"

    def test_generate_market_tag_disabled(self, pipeline):
        """Test tag generation when metadata is disabled."""
        pipeline.include_metadata = False

        tag = pipeline._generate_market_tag("crypto")
        assert tag == ""

    def test_generate_operation_id(self, pipeline):
        """Test operationId generation."""
        operation_id = pipeline._generate_operation_id("crypto")
        assert operation_id == "scanCrypto"

        operation_id = pipeline._generate_operation_id("us_stocks")
        assert operation_id == "scanUsStocks"

        operation_id = pipeline._generate_operation_id("forex")
        assert operation_id == "scanForex"

    def test_generate_operation_id_disabled(self, pipeline):
        """Test operationId generation when metadata is disabled."""
        pipeline.include_metadata = False

        operation_id = pipeline._generate_operation_id("crypto")
        assert operation_id == ""

    def test_generate_summary(self, pipeline):
        """Test summary generation."""
        pipeline.display_names = {"crypto": "Cryptocurrency"}

        summary = pipeline._generate_summary("crypto")
        assert summary == "Run screener scan for Cryptocurrency"

        # Test fallback
        summary = pipeline._generate_summary("forex")
        assert summary == "Run screener scan for Forex"

    def test_generate_summary_disabled(self, pipeline):
        """Test summary generation when metadata is disabled."""
        pipeline.include_metadata = False

        summary = pipeline._generate_summary("crypto")
        assert summary == ""

    def test_generate_description(self, pipeline):
        """Test description generation."""
        pipeline.display_names = {"crypto": "Cryptocurrency"}

        description = pipeline._generate_description("crypto")
        assert (
            description
            == "Execute a TradingView screener query for the Cryptocurrency market. Returns indicator values for filtered tickers."
        )

        # Test fallback
        description = pipeline._generate_description("forex")
        assert (
            description
            == "Execute a TradingView screener query for the Forex market. Returns indicator values for filtered tickers."
        )

    def test_generate_description_disabled(self, pipeline):
        """Test description generation when metadata is disabled."""
        pipeline.include_metadata = False

        description = pipeline._generate_description("crypto")
        assert description == ""

    def test_operation_id_uniqueness(self, pipeline):
        """Test that operationIds are unique across markets."""
        markets = ["crypto", "forex", "us_stocks", "europe", "asia"]
        operation_ids = set()

        for market in markets:
            operation_id = pipeline._generate_operation_id(market)
            assert operation_id not in operation_ids, f"Duplicate operationId: {operation_id}"
            operation_ids.add(operation_id)

    @patch.object(OpenAPIPipeline, "_load_metainfo")
    def test_generate_openapi_spec_with_metadata(self, mock_load_metainfo, pipeline, sample_metainfo):
        """Test OpenAPI spec generation includes metadata."""
        mock_load_metainfo.return_value = sample_metainfo
        pipeline.display_names = {"crypto": "Cryptocurrency"}

        spec = pipeline.generate_openapi_spec("crypto")

        # Check that metadata is included
        post_operation = spec["paths"]["/scan"]["post"]
        assert post_operation["tags"] == ["Cryptocurrency Screener"]
        assert post_operation["operationId"] == "scanCrypto"
        assert post_operation["summary"] == "Run screener scan for Cryptocurrency"
        assert "Execute a TradingView screener query" in post_operation["description"]

    @patch.object(OpenAPIPipeline, "_load_metainfo")
    def test_generate_openapi_spec_without_metadata(self, mock_load_metainfo, pipeline, sample_metainfo):
        """Test OpenAPI spec generation without metadata."""
        mock_load_metainfo.return_value = sample_metainfo
        pipeline.include_metadata = False

        spec = pipeline.generate_openapi_spec("crypto")

        # Check that metadata is not included
        post_operation = spec["paths"]["/scan"]["post"]
        assert "tags" not in post_operation
        assert "operationId" not in post_operation
        # Summary and description should fall back to defaults
        assert "Scan" in post_operation["summary"]
        assert "market with filters" in post_operation["description"]

    @patch.object(OpenAPIPipeline, "_load_metainfo")
    def test_generate_openapi_spec_technical_tags(self, mock_load_metainfo, pipeline, sample_metainfo):
        """Test OpenAPI spec generation with technical tag format."""
        mock_load_metainfo.return_value = sample_metainfo
        pipeline.tag_format = "technical"

        spec = pipeline.generate_openapi_spec("crypto")

        # Check that technical tags are used
        post_operation = spec["paths"]["/scan"]["post"]
        assert post_operation["tags"] == ["CRYPTO_SCREENER"]

    def test_cli_tag_format_choices(self):
        """Test CLI tag format choices are valid."""
        # This test ensures the CLI choices match what the code supports
        valid_formats = ["default", "technical"]

        # Test that our pipeline accepts these formats
        for format_choice in valid_formats:
            pipeline = OpenAPIPipeline(tag_format=format_choice)
            assert pipeline.tag_format == format_choice

    def test_metadata_consistency(self, pipeline):
        """Test that metadata is consistent across different markets."""
        test_cases = [
            ("crypto", "Cryptocurrency"),
            ("forex", "Forex"),
            ("us_stocks", "US Stocks"),
        ]

        for market, expected_display in test_cases:
            pipeline.display_names[market] = expected_display

            tag = pipeline._generate_market_tag(market)
            summary = pipeline._generate_summary(market)
            description = pipeline._generate_description(market)

            # Check consistency
            assert expected_display in tag
            assert expected_display in summary
            assert expected_display in description

    def test_metadata_english_only(self, pipeline):
        """Test that all metadata is in English with no emojis."""
        markets = ["crypto", "forex", "us_stocks"]

        for market in markets:
            tag = pipeline._generate_market_tag(market)
            summary = pipeline._generate_summary(market)
            description = pipeline._generate_description(market)
            operation_id = pipeline._generate_operation_id(market)

            # Check for English characters only (basic check)
            assert all(ord(c) < 128 for c in tag + summary + description + operation_id)

            # Check no emojis
            assert not any(0x1F600 <= ord(c) <= 0x1F64F for c in tag + summary + description + operation_id)
            assert not any(0x1F300 <= ord(c) <= 0x1F5FF for c in tag + summary + description + operation_id)

    def test_metadata_deterministic(self, pipeline):
        """Test that metadata generation is deterministic."""
        market = "crypto"
        pipeline.display_names[market] = "Cryptocurrency"

        # Generate metadata multiple times
        results = []
        for _ in range(5):
            result = {
                "tag": pipeline._generate_market_tag(market),
                "operation_id": pipeline._generate_operation_id(market),
                "summary": pipeline._generate_summary(market),
                "description": pipeline._generate_description(market),
            }
            results.append(result)

        # All results should be identical
        for i in range(1, len(results)):
            assert results[i] == results[0], f"Metadata not deterministic: {results[i]} != {results[0]}"
