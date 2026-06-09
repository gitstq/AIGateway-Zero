"""
Unit tests for guardrails.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from guardrails import Guardrails


class TestGuardrails(unittest.TestCase):
    """Test content guardrails."""

    def test_disabled_guardrails(self):
        """Test that disabled guardrails allow everything."""
        gr = Guardrails(enabled=False)
        result = gr.check_input([{"role": "user", "content": "anything"}])
        self.assertTrue(result.allowed)

    def test_input_length_limit(self):
        """Test input length limiting."""
        gr = Guardrails(enabled=True, max_input_length=10)
        result = gr.check_input([{"role": "user", "content": "short"}])
        self.assertTrue(result.allowed)

        result = gr.check_input([{"role": "user", "content": "this is way too long"}])
        self.assertFalse(result.allowed)
        self.assertIn("length", result.reason.lower())

    def test_blocked_keywords(self):
        """Test keyword blocking."""
        gr = Guardrails(
            enabled=True,
            blocked_keywords=["badword", "evil"]
        )

        result = gr.check_input([{"role": "user", "content": "hello world"}])
        self.assertTrue(result.allowed)

        result = gr.check_input([{"role": "user", "content": "this contains badword"}])
        self.assertFalse(result.allowed)

    def test_allowed_models(self):
        """Test model allowlisting."""
        gr = Guardrails(
            enabled=True,
            allowed_models=["gpt-4", "claude-3"]
        )

        result = gr.check_input([{"role": "user", "content": "hello"}], model="gpt-4")
        self.assertTrue(result.allowed)

        result = gr.check_input([{"role": "user", "content": "hello"}], model="unknown-model")
        self.assertFalse(result.allowed)

    def test_output_length(self):
        """Test output length limiting."""
        gr = Guardrails(enabled=True, max_output_length=10)

        result = gr.check_output("short")
        self.assertTrue(result.allowed)

        result = gr.check_output("this is way too long for the limit")
        self.assertFalse(result.allowed)

    def test_request_body_check(self):
        """Test full request body validation."""
        gr = Guardrails(enabled=True, max_input_length=100)

        body = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "hello"}]
        }
        result = gr.check_request_body(body)
        self.assertTrue(result.allowed)


if __name__ == "__main__":
    unittest.main()
