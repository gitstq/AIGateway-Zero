"""
Content guardrails for input/output validation.
Supports keyword filtering, length limits, and model allowlisting.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class GuardrailResult:
    """Result of guardrail check."""
    allowed: bool
    reason: Optional[str] = None
    action: str = "block"  # block, warn, log


class Guardrails:
    """Content safety guardrails."""

    def __init__(
        self,
        enabled: bool = False,
        max_input_length: int = 32000,
        max_output_length: int = 16000,
        blocked_keywords: Optional[List[str]] = None,
        allowed_models: Optional[List[str]] = None,
    ):
        self.enabled = enabled
        self.max_input_length = max_input_length
        self.max_output_length = max_output_length
        self.blocked_keywords = blocked_keywords or []
        self.allowed_models = allowed_models or []
        self._compiled_patterns = []
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile keyword patterns for efficient matching."""
        self._compiled_patterns = []
        for keyword in self.blocked_keywords:
            try:
                pattern = re.compile(keyword, re.IGNORECASE)
                self._compiled_patterns.append(pattern)
            except re.error:
                # Treat as literal string if regex invalid
                pattern = re.compile(re.escape(keyword), re.IGNORECASE)
                self._compiled_patterns.append(pattern)

    def check_input(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None
    ) -> GuardrailResult:
        """Validate input messages."""
        if not self.enabled:
            return GuardrailResult(allowed=True)

        # Check model allowlist
        if self.allowed_models and model and model not in self.allowed_models:
            return GuardrailResult(
                allowed=False,
                reason=f"Model '{model}' is not in the allowed models list",
                action="block"
            )

        # Check input length
        total_length = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total_length += len(content)

        if total_length > self.max_input_length:
            return GuardrailResult(
                allowed=False,
                reason=f"Input length ({total_length}) exceeds maximum ({self.max_input_length})",
                action="block"
            )

        # Check blocked keywords
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                for pattern in self._compiled_patterns:
                    if pattern.search(content):
                        return GuardrailResult(
                            allowed=False,
                            reason="Content contains blocked keywords",
                            action="block"
                        )

        return GuardrailResult(allowed=True)

    def check_output(self, content: str) -> GuardrailResult:
        """Validate output content."""
        if not self.enabled:
            return GuardrailResult(allowed=True)

        # Check output length
        if len(content) > self.max_output_length:
            return GuardrailResult(
                allowed=False,
                reason=f"Output length ({len(content)}) exceeds maximum ({self.max_output_length})",
                action="block"
            )

        # Check blocked keywords
        for pattern in self._compiled_patterns:
            if pattern.search(content):
                return GuardrailResult(
                    allowed=False,
                    reason="Output contains blocked keywords",
                    action="block"
                )

        return GuardrailResult(allowed=True)

    def check_request_body(self, body: Dict[str, Any]) -> GuardrailResult:
        """Validate full request body."""
        if not self.enabled:
            return GuardrailResult(allowed=True)

        messages = body.get("messages", [])
        model = body.get("model")
        return self.check_input(messages, model)

    def to_dict(self) -> Dict[str, Any]:
        """Export guardrails configuration."""
        return {
            "enabled": self.enabled,
            "max_input_length": self.max_input_length,
            "max_output_length": self.max_output_length,
            "blocked_keywords_count": len(self.blocked_keywords),
            "allowed_models": self.allowed_models,
        }
