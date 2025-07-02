"""
Tests for OpenAPI $ref schema functionality.
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from tv_generator.core import OpenAPIPipeline


class TestOpenAPIRefSchemas:
    """Test OpenAPI $ref schema generation."""

    @pytest.fixture
    def pipeline(self):
        """Create a test pipeline instance."""
        return OpenAPIPipeline(
            data_dir=Path("tests/test_data"),
            specs_dir=Path("tests/test_specs"),
            inline_body=False,  # Use $ref by default
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
            {
                "n": "active",
                "t": "boolean",
                "d": "Active status",
                "e": True,
            },
        ]

    def test_generate_request_body_schema(self, pipeline):
        """Test request body schema generation."""
        fields = {"name": {"type": "string"}, "price": {"type": "number"}}
        filter_schemas = {
            "name": {"type": "object", "properties": {"query": {"type": "string"}}},
            "price": {"type": "object", "properties": {"left": {"type": "number"}, "right": {"type": "number"}}},
        }

        schema = pipeline._generate_request_body_schema(fields, filter_schemas)

        assert schema["type"] == "object"
        assert "symbols" in schema["properties"]
        assert "columns" in schema["properties"]
        assert "filters" in schema["properties"]
        assert "range" in schema["properties"]
        assert "options" in schema["properties"]
        assert "symbols" in schema["required"]
        assert "columns" in schema["required"]

    def test_generate_filter_expression_schema(self, pipeline):
        """Test filter expression schema generation."""
        metainfo = {
            "name": {"t": "string"},
            "price": {"t": "number"},
            "sector": {"t": "string", "r": [{"id": "tech"}]},
            "active": {"t": "boolean"},
        }

        schema = pipeline._generate_filter_expression_schema(metainfo, skip_enum_validation=False)

        assert schema["type"] == "object"
        assert "left" in schema["properties"]
        assert "operation" in schema["properties"]
        assert "right" in schema["properties"]
        assert "left" in schema["required"]
        assert "operation" in schema["required"]
        assert "right" in schema["required"]

        # Check operations enum
        operations = schema["properties"]["operation"]["enum"]
        assert "equal" in operations
        assert "not_equal" in operations
        assert "greater" in operations
        assert "less" in operations
        assert "and" in operations
        assert "or" in operations

    def test_generate_components_schemas(self, pipeline):
        """Test components schemas generation."""
        fields = {"name": {"type": "string"}}
        filter_schemas = {"name": {"type": "object"}}
        metainfo = {"name": {"t": "string"}}

        schemas = pipeline._generate_components_schemas(fields, filter_schemas, metainfo, skip_enum_validation=False)

        assert "Field" in schemas
        assert "Filter" in schemas
        assert "RequestBody" in schemas
        assert "FilterExpression" in schemas

        # Check Field schema
        assert schemas["Field"]["type"] == "object"
        assert "name" in schemas["Field"]["properties"]

        # Check Filter schema
        assert "oneOf" in schemas["Filter"]

        # Check RequestBody schema
        assert schemas["RequestBody"]["type"] == "object"
        assert "symbols" in schemas["RequestBody"]["properties"]

        # Check FilterExpression schema
        assert schemas["FilterExpression"]["type"] == "object"
        assert "left" in schemas["FilterExpression"]["properties"]

    @patch.object(OpenAPIPipeline, "_load_metainfo")
    def test_generate_openapi_spec_with_ref(self, mock_load_metainfo, pipeline, sample_metainfo):
        """Test OpenAPI spec generation with $ref references."""
        mock_load_metainfo.return_value = sample_metainfo
        pipeline.inline_body = False

        spec = pipeline.generate_openapi_spec("crypto")

        # Check that request body uses $ref
        request_body = spec["paths"]["/scan"]["post"]["requestBody"]
        schema = request_body["content"]["application/json"]["schema"]
        assert "$ref" in schema
        assert schema["$ref"] == "#/components/schemas/RequestBody"

        # Check that components.schemas contains RequestBody
        assert "RequestBody" in spec["components"]["schemas"]
        assert "FilterExpression" in spec["components"]["schemas"]

    @patch.object(OpenAPIPipeline, "_load_metainfo")
    def test_generate_openapi_spec_inline(self, mock_load_metainfo, pipeline, sample_metainfo):
        """Test OpenAPI spec generation with inline body."""
        mock_load_metainfo.return_value = sample_metainfo
        pipeline.inline_body = True

        spec = pipeline.generate_openapi_spec("crypto")

        # Check that request body is inline
        request_body = spec["paths"]["/scan"]["post"]["requestBody"]
        schema = request_body["content"]["application/json"]["schema"]
        assert "$ref" not in schema
        assert "type" in schema
        assert schema["type"] == "object"

        # Check that components.schemas still contains other schemas
        assert "RequestBody" in spec["components"]["schemas"]
        assert "FilterExpression" in spec["components"]["schemas"]

    def test_filter_operations_by_type(self, pipeline):
        """Test that filter operations are correctly determined by field type."""
        metainfo = {
            "string_field": {"t": "string"},
            "number_field": {"t": "number"},
            "boolean_field": {"t": "boolean"},
            "enum_field": {"t": "string", "r": [{"id": "value1"}]},
        }

        schema = pipeline._generate_filter_expression_schema(metainfo, skip_enum_validation=False)
        operations = schema["properties"]["operation"]["enum"]

        # String operations
        assert "equal" in operations
        assert "not_equal" in operations
        assert "contains" in operations
        assert "not_contains" in operations

        # Number operations
        assert "greater" in operations
        assert "less" in operations
        assert "in_range" in operations
        assert "not_in_range" in operations

        # Boolean operations
        assert "equal" in operations
        assert "not_equal" in operations

        # Logical operations
        assert "and" in operations
        assert "or" in operations
        assert "not" in operations

    def test_enum_operations_when_validation_skipped(self, pipeline):
        """Test enum operations when validation is skipped."""
        metainfo = {
            "enum_field": {"t": "string", "r": [{"id": "value1"}]},
        }

        # With validation
        schema_with_validation = pipeline._generate_filter_expression_schema(metainfo, skip_enum_validation=False)
        operations_with_validation = schema_with_validation["properties"]["operation"]["enum"]

        # Without validation
        schema_without_validation = pipeline._generate_filter_expression_schema(metainfo, skip_enum_validation=True)
        operations_without_validation = schema_without_validation["properties"]["operation"]["enum"]

        # Both should have enum operations (in/not_in for enum fields)
        assert "in" in operations_with_validation
        assert "not_in" in operations_with_validation
        # When validation is skipped, enum fields still get in/not_in operations
        assert "in" in operations_without_validation
        assert "not_in" in operations_without_validation

    def test_request_body_schema_structure(self, pipeline):
        """Test request body schema has correct structure."""
        fields = {"field1": {"type": "string"}}
        filter_schemas = {"field1": {"type": "object"}}

        schema = pipeline._generate_request_body_schema(fields, filter_schemas)

        # Check symbols structure
        symbols = schema["properties"]["symbols"]
        assert symbols["type"] == "object"
        assert "query" in symbols["properties"]
        assert "types" in symbols["properties"]["query"]["properties"]

        # Check columns structure
        columns = schema["properties"]["columns"]
        assert columns["type"] == "array"
        assert columns["items"]["type"] == "string"

        # Check filters structure
        filters = schema["properties"]["filters"]
        assert filters["type"] == "array"
        assert "oneOf" in filters["items"]

        # Check range structure
        range_prop = schema["properties"]["range"]
        assert range_prop["type"] == "array"
        assert range_prop["items"]["type"] == "integer"

        # Check options structure
        options = schema["properties"]["options"]
        assert options["type"] == "object"
        assert "lang" in options["properties"]

    def test_filter_expression_right_value_types(self, pipeline):
        """Test filter expression right value supports multiple types."""
        metainfo = {"field": {"t": "string"}}

        schema = pipeline._generate_filter_expression_schema(metainfo, skip_enum_validation=False)
        right_schema = schema["properties"]["right"]

        assert "oneOf" in right_schema
        types = [item["type"] for item in right_schema["oneOf"]]
        assert "string" in types
        assert "number" in types
        assert "boolean" in types
        assert "array" in types
        assert "object" in types

    def test_components_schemas_reusability(self, pipeline):
        """Test that components schemas can be reused."""
        fields = {"name": {"type": "string"}}
        filter_schemas = {"name": {"type": "object"}}
        metainfo = {"name": {"t": "string"}}

        schemas = pipeline._generate_components_schemas(fields, filter_schemas, metainfo, skip_enum_validation=False)

        # RequestBody should reference the same fields and filter_schemas
        request_body = schemas["RequestBody"]
        assert "columns" in request_body["properties"]
        assert "filters" in request_body["properties"]

        # Filter should reference the same filter_schemas
        filter_schema = schemas["Filter"]
        assert "oneOf" in filter_schema

    def test_cli_inline_body_flag(self):
        """Test CLI inline body flag behavior."""
        # Test default behavior (use $ref)
        pipeline_default = OpenAPIPipeline(inline_body=False)
        assert pipeline_default.inline_body is False

        # Test inline behavior
        pipeline_inline = OpenAPIPipeline(inline_body=True)
        assert pipeline_inline.inline_body is True

    def test_schema_validation_compatibility(self, pipeline):
        """Test that generated schemas are compatible with OpenAPI 3.1.0."""
        fields = {"name": {"type": "string"}}
        filter_schemas = {"name": {"type": "object"}}
        metainfo = {"name": {"t": "string"}}

        schemas = pipeline._generate_components_schemas(fields, filter_schemas, metainfo, skip_enum_validation=False)

        # Check that all schemas have required OpenAPI 3.1.0 properties
        for schema_name, schema in schemas.items():
            # Schemas can have type, $ref, oneOf, or other valid OpenAPI properties
            assert any(key in schema for key in ["type", "$ref", "oneOf", "allOf", "anyOf", "not"])

            if "properties" in schema:
                assert isinstance(schema["properties"], dict)

            if "required" in schema:
                assert isinstance(schema["required"], list)

    def test_ref_resolution_structure(self, pipeline):
        """Test that $ref references resolve correctly."""
        fields = {"name": {"type": "string"}}
        filter_schemas = {"name": {"type": "object"}}
        metainfo = {"name": {"t": "string"}}

        schemas = pipeline._generate_components_schemas(fields, filter_schemas, metainfo, skip_enum_validation=False)

        # RequestBody should be self-contained (not reference other schemas)
        request_body = schemas["RequestBody"]
        assert "$ref" not in str(request_body)  # No internal references

        # Filter should reference filter_schemas
        filter_schema = schemas["Filter"]
        assert "oneOf" in filter_schema
        assert len(filter_schema["oneOf"]) == len(filter_schemas)

    def test_english_only_schemas(self, pipeline):
        """Test that all schema descriptions are in English only."""
        fields = {"name": {"type": "string"}}
        filter_schemas = {"name": {"type": "object"}}
        metainfo = {"name": {"t": "string"}}

        schemas = pipeline._generate_components_schemas(fields, filter_schemas, metainfo, skip_enum_validation=False)

        # Check that all string values are ASCII (English)
        schema_json = json.dumps(schemas)
        for char in schema_json:
            if ord(char) >= 128:
                # Allow common punctuation and symbols
                if char not in '""{}[]:,':
                    assert False, f"Non-ASCII character found: {char} (ord: {ord(char)})"

    def test_deterministic_schema_generation(self, pipeline):
        """Test that schema generation is deterministic."""
        fields = {"name": {"type": "string"}}
        filter_schemas = {"name": {"type": "object"}}
        metainfo = {"name": {"t": "string"}}

        # Generate schemas multiple times
        results = []
        for _ in range(5):
            schemas = pipeline._generate_components_schemas(
                fields, filter_schemas, metainfo, skip_enum_validation=False
            )
            results.append(schemas)

        # All results should be identical
        for i in range(1, len(results)):
            assert results[i] == results[0], f"Schema generation not deterministic: {results[i]} != {results[0]}"

    @patch.object(OpenAPIPipeline, "_load_metainfo")
    def test_generate_openapi_spec_with_examples(self, mock_load_metainfo, pipeline, sample_metainfo):
        """Test OpenAPI spec generation with real scan examples."""
        mock_load_metainfo.return_value = sample_metainfo
        pipeline.include_examples = True
        scan_examples = [
            {"d": {"filter": ["f1"], "columns": ["c1"], "symbol": "BTCUSDT"}},
            {"d": {"filter": ["f2"], "columns": ["c2"], "symbol": "ETHUSDT"}},
            {"d": {"filter": ["f3"], "columns": ["c3"], "symbol": "BNBUSDT"}},
            {"d": {"filter": ["f4"], "columns": ["c4"], "symbol": "BTCUSDT"}},  # дубликат тикера
        ]
        spec = pipeline.generate_openapi_spec("crypto", include_examples=True, scan_examples=scan_examples)
        # Проверяем, что components.examples есть и не более 3 примеров
        assert "examples" in spec["components"]
        assert 1 <= len(spec["components"]["examples"]) <= 3
        # Проверяем, что примеры ссылаются из requestBody
        examples_ref = spec["paths"]["/scan"]["post"]["requestBody"]["content"]["application/json"]["examples"]
        for k in spec["components"]["examples"].keys():
            assert k in examples_ref
        # Проверяем, что тикеры уникальны
        tickers = [ex["summary"] for ex in spec["components"]["examples"].values()]
        assert len(tickers) == len(set(tickers))

    @patch.object(OpenAPIPipeline, "_load_metainfo")
    def test_generate_openapi_spec_no_examples(self, mock_load_metainfo, pipeline, sample_metainfo):
        """Test OpenAPI spec generation with examples disabled."""
        mock_load_metainfo.return_value = sample_metainfo
        pipeline.include_examples = False
        scan_examples = [
            {"d": {"filter": ["f1"], "columns": ["c1"], "symbol": "BTCUSDT"}},
        ]
        spec = pipeline.generate_openapi_spec("crypto", include_examples=False, scan_examples=scan_examples)
        # Не должно быть components.examples и ссылок
        assert "examples" not in spec["components"]
        assert "examples" not in spec["paths"]["/scan"]["post"]["requestBody"]["content"]["application/json"]

    @patch.object(OpenAPIPipeline, "_load_metainfo")
    def test_openapi_with_examples_is_valid_yaml(self, mock_load_metainfo, pipeline, sample_metainfo):
        """Test that OpenAPI spec with examples is valid YAML/JSON."""
        import yaml

        mock_load_metainfo.return_value = sample_metainfo
        pipeline.include_examples = True
        scan_examples = [
            {"d": {"filter": ["f1"], "columns": ["c1"], "symbol": "BTCUSDT"}},
        ]
        spec = pipeline.generate_openapi_spec("crypto", include_examples=True, scan_examples=scan_examples)
        # Проверяем, что можно сериализовать в YAML и JSON
        yaml_str = yaml.dump(spec)
        json_str = json.dumps(spec)
        assert "components" in yaml_str
        assert "examples" in yaml_str
        assert "BTCUSDT" in yaml_str or "BTCUSDT" in json_str

    @patch.object(OpenAPIPipeline, "_load_metainfo")
    def test_require_examples_success(self, mock_load_metainfo, pipeline, sample_metainfo):
        """Test that spec is generated if >=80% fields have examples and require_examples is True."""
        mock_load_metainfo.return_value = sample_metainfo
        pipeline.include_examples = True
        scan_examples = [
            {
                "d": {
                    "filter": ["f1"],
                    "columns": ["c1"],
                    "symbol": "BTCUSDT",
                    "name": "Apple Inc.",
                    "price": 150.25,
                    "sector": "technology",
                    "active": True,
                }
            },
        ]
        # Проставим примеры вручную для 4 из 5 полей (80%)
        fields = {
            "name": {"type": "string", "example": "Apple Inc."},
            "price": {"type": "number", "example": 150.25},
            "sector": {"type": "string", "example": "technology"},
            "active": {"type": "boolean", "example": True},
            "missing": {"type": "string"},
        }
        # monkeypatch _generate_field_schemas
        pipeline._generate_field_schemas = lambda *a, **kw: fields
        spec = pipeline.generate_openapi_spec(
            "crypto", include_examples=True, scan_examples=scan_examples, require_examples=True
        )
        assert "components" in spec
        assert "examples" in spec["components"]

    @patch.object(OpenAPIPipeline, "_load_metainfo")
    def test_require_examples_fail(self, mock_load_metainfo, pipeline, sample_metainfo):
        """Test that spec generation fails if <80% fields have examples and require_examples is True."""
        mock_load_metainfo.return_value = sample_metainfo
        pipeline.include_examples = True
        scan_examples = [
            {"d": {"filter": ["f1"], "columns": ["c1"], "symbol": "BTCUSDT", "name": "Apple Inc."}},
        ]
        # Только 1 из 5 полей с примером (20%)
        fields = {
            "name": {"type": "string", "example": "Apple Inc."},
            "price": {"type": "number"},
            "sector": {"type": "string"},
            "active": {"type": "boolean"},
            "missing": {"type": "string"},
        }
        pipeline._generate_field_schemas = lambda *a, **kw: fields
        with pytest.raises(Exception) as excinfo:
            pipeline.generate_openapi_spec(
                "crypto", include_examples=True, scan_examples=scan_examples, require_examples=True
            )
        assert "coverage" in str(excinfo.value) or "80%" in str(excinfo.value)

    @patch.object(OpenAPIPipeline, "_load_metainfo")
    def test_debug_trace_fields(self, mock_load_metainfo, pipeline, sample_metainfo):
        """Test that x-tradingview-id and x-tradingview-type are present in field schemas when debug_trace is enabled."""
        mock_load_metainfo.return_value = sample_metainfo
        pipeline.debug_trace = True
        spec = pipeline.generate_openapi_spec("crypto", debug_trace=True)
        field_props = spec["components"]["schemas"]["Field"]["properties"]
        for field in sample_metainfo:
            name = field["n"]
            assert "x-tradingview-id" in field_props[name]
            assert field_props[name]["x-tradingview-id"] == field["n"]
            assert "x-tradingview-type" in field_props[name]
            assert field_props[name]["x-tradingview-type"] == field["t"]

    def test_generate_field_schema_invalid():
        from src.tv_generator.core.schema_generator import SchemaGenerator

        sg = SchemaGenerator()
        # Некорректное поле (нет ключей)
        result = sg.generate_field_schema({}, market=None)
        assert result["type"] == "string"
        assert "Error" in result["description"]

    def test_generate_field_schema_partial():
        from src.tv_generator.core.schema_generator import SchemaGenerator

        sg = SchemaGenerator()
        # Частично заполненное поле
        result = sg.generate_field_schema({"n": "test"}, market=None)
        assert result["type"] == "string"
        assert "Field: test" in result["description"]

    def test_generate_filter_schema_invalid():
        from src.tv_generator.core.schema_generator import SchemaGenerator

        sg = SchemaGenerator()
        # Некорректный metainfo (нет filters)
        result = sg.generate_filter_schema({})
        assert result["type"] == "object"
        assert result["properties"] == {}
        # Некорректный фильтр (битый dict)
        result = sg.generate_filter_schema({"filters": {"bad": {"broken": True}}})
        assert result["type"] == "object"
        assert "bad" in result["properties"] or result["properties"] == {}
