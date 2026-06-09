"""
Unit tests for configuration management.
"""

import sys
import os
import unittest
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from config import Config


class TestConfig(unittest.TestCase):
    """Test configuration management."""

    def test_default_config(self):
        """Test default configuration values."""
        config = Config()
        self.assertEqual(config.get("server", "host"), "0.0.0.0")
        self.assertEqual(config.get("server", "port"), 8080)
        self.assertEqual(config.get("gateway", "default_model"), "gpt-4o")
        self.assertEqual(config.get("gateway", "load_balance_strategy"), "round_robin")

    def test_json_config_file(self):
        """Test loading JSON config file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"server": {"port": 9090}, "gateway": {"default_model": "gpt-3.5"}}')
            path = f.name

        try:
            config = Config(path)
            self.assertEqual(config.get("server", "port"), 9090)
            self.assertEqual(config.get("gateway", "default_model"), "gpt-3.5")
            self.assertEqual(config.get("server", "host"), "0.0.0.0")  # Default preserved
        finally:
            os.unlink(path)

    def test_yaml_config_file(self):
        """Test loading YAML config file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
server:
  port: 7070
  host: 127.0.0.1
gateway:
  default_model: claude-3
""")
            path = f.name

        try:
            config = Config(path)
            self.assertEqual(config.get("server", "port"), 7070)
            self.assertEqual(config.get("server", "host"), "127.0.0.1")
            self.assertEqual(config.get("gateway", "default_model"), "claude-3")
        finally:
            os.unlink(path)

    def test_nested_get(self):
        """Test nested key access."""
        config = Config()
        self.assertIsNotNone(config.get("server"))
        self.assertIsNone(config.get("nonexistent", "key"))
        self.assertEqual(config.get("nonexistent", "key", default="default"), "default")

    def test_config_to_json(self):
        """Test JSON export."""
        config = Config()
        json_str = config.to_json()
        self.assertIn("server", json_str)
        self.assertIn("gateway", json_str)


if __name__ == "__main__":
    unittest.main()
