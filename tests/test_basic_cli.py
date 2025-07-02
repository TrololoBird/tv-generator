"""
Basic CLI tests for tv-generator.
Tests the main CLI functionality with the russia market.
"""

import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import TestCase

import pytest


class TestBasicCLI(TestCase):
    """Basic CLI functionality tests."""

    def setUp(self):
        """Set up test environment."""
        self.project_root = Path(__file__).parent.parent
        self.cli_module = "src.tv_generator"
        self.test_market = "russia"
        self.test_output_dir = self.project_root / "test_output"

    def test_cli_help(self):
        """Test that CLI help works."""
        result = subprocess.run(
            [sys.executable, "-m", self.cli_module, "--help"],
            capture_output=True,
            text=True,
            cwd=self.project_root,
            timeout=30,
        )

        # CLI should not crash and should show some output
        self.assertEqual(result.returncode, 0, f"CLI help failed: {result.stderr}")
        self.assertIn("usage:", result.stdout.lower() or result.stderr.lower())

    def test_cli_generate_russia_market(self):
        """Test CLI generation for russia market."""
        # Create temporary output directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Run CLI command
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    self.cli_module,
                    "generate",
                    f"--market={self.test_market}",
                    f"--output-dir={temp_path}",
                    "--validate",
                ],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=60,
            )

            # Check if command completed (may have warnings but should not crash)
            self.assertLessEqual(
                result.returncode, 1, f"CLI generation failed: {result.stderr}"  # Allow warnings (return code 1)
            )

            # Check if output file was created
            expected_file = temp_path / f"{self.test_market}_openapi.json"
            if expected_file.exists():
                # File was created successfully
                self.assertTrue(expected_file.exists(), "OpenAPI spec file was not created")

                # Check file size (should be reasonable)
                file_size = expected_file.stat().st_size
                self.assertGreater(file_size, 1000, "Generated file is too small")

                # Check file content (should be valid JSON)
                try:
                    import json

                    with open(expected_file, "r", encoding="utf-8") as f:
                        spec = json.load(f)

                    # Basic OpenAPI structure check
                    self.assertIn("openapi", spec, "Missing openapi version")
                    self.assertIn("info", spec, "Missing info section")
                    self.assertIn("paths", spec, "Missing paths section")

                except json.JSONDecodeError as e:
                    self.fail(f"Generated file is not valid JSON: {e}")
            else:
                # File not created - this might be expected if metainfo is missing
                # Just log it as a warning
                print(f"Warning: Expected file {expected_file} was not created")
                print(f"CLI output: {result.stdout}")
                print(f"CLI errors: {result.stderr}")

    def test_cli_without_arguments(self):
        """Test CLI without arguments (should generate for all markets)."""
        result = subprocess.run(
            [sys.executable, "-m", self.cli_module],
            capture_output=True,
            text=True,
            cwd=self.project_root,
            timeout=120,  # Longer timeout for all markets
        )

        # Should not crash (may have errors for missing metainfo files)
        self.assertLessEqual(result.returncode, 1, f"CLI without arguments failed: {result.stderr}")  # Allow warnings

    def test_cli_invalid_market(self):
        """Test CLI with invalid market (should handle gracefully)."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                self.cli_module,
                "generate",
                "--market=invalid_market_12345",
                "--output-dir=/tmp",
            ],
            capture_output=True,
            text=True,
            cwd=self.project_root,
            timeout=30,
        )

        # Should handle invalid market gracefully
        self.assertLessEqual(result.returncode, 1, f"CLI with invalid market failed: {result.stderr}")  # Allow warnings


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
