"""
Configuration management for AIGateway-Zero.
Supports YAML, JSON, and environment variable configuration.
"""

import os
import json
import re
from typing import Dict, List, Any, Optional


DEFAULT_CONFIG = {
    "server": {
        "host": "0.0.0.0",
        "port": 8080,
        "workers": 4,
        "timeout": 60,
        "keep_alive": 120,
    },
    "gateway": {
        "default_model": "gpt-4o",
        "fallback_enabled": True,
        "retry_attempts": 3,
        "retry_delay": 1.0,
        "load_balance_strategy": "round_robin",
        "health_check_interval": 30,
        "request_timeout": 60,
        "max_request_size": 10485760,
        "rate_limit_enabled": True,
        "rate_limit_requests": 100,
        "rate_limit_window": 60,
    },
    "providers": {},
    "guardrails": {
        "enabled": False,
        "max_input_length": 32000,
        "max_output_length": 16000,
        "blocked_keywords": [],
        "allowed_models": [],
    },
    "logging": {
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "file": None,
    },
    "metrics": {
        "enabled": True,
        "retention_seconds": 86400,
    },
}


class Config:
    """Configuration manager with merge support."""

    def __init__(self, config_path: Optional[str] = None):
        self._config = self._deep_copy(DEFAULT_CONFIG)
        if config_path and os.path.exists(config_path):
            self.load_from_file(config_path)
        self._load_from_env()

    def _deep_copy(self, obj: Any) -> Any:
        """Deep copy a nested structure."""
        if isinstance(obj, dict):
            return {k: self._deep_copy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_copy(item) for item in obj]
        return obj

    def _load_from_env(self):
        """Override config with environment variables."""
        env_mappings = {
            "AIGATEWAY_HOST": ("server", "host"),
            "AIGATEWAY_PORT": ("server", "port", int),
            "AIGATEWAY_WORKERS": ("server", "workers", int),
            "AIGATEWAY_TIMEOUT": ("server", "timeout", int),
            "AIGATEWAY_DEFAULT_MODEL": ("gateway", "default_model"),
            "AIGATEWAY_RETRY_ATTEMPTS": ("gateway", "retry_attempts", int),
            "AIGATEWAY_RETRY_DELAY": ("gateway", "retry_delay", float),
            "AIGATEWAY_LOAD_BALANCE": ("gateway", "load_balance_strategy"),
            "AIGATEWAY_RATE_LIMIT_ENABLED": ("gateway", "rate_limit_enabled", self._str_to_bool),
            "AIGATEWAY_RATE_LIMIT_REQUESTS": ("gateway", "rate_limit_requests", int),
            "AIGATEWAY_RATE_LIMIT_WINDOW": ("gateway", "rate_limit_window", int),
            "AIGATEWAY_LOG_LEVEL": ("logging", "level"),
            "AIGATEWAY_METRICS_ENABLED": ("metrics", "enabled", self._str_to_bool),
        }

        for env_var, mapping in env_mappings.items():
            value = os.environ.get(env_var)
            if value is not None:
                section, key = mapping[0], mapping[1]
                converter = mapping[2] if len(mapping) > 2 else str
                try:
                    self._config[section][key] = converter(value)
                except (ValueError, TypeError):
                    pass

        # Load provider configs from env
        provider_pattern = re.compile(r"AIGATEWAY_PROVIDER_(\w+)_(\w+)")
        for key, value in os.environ.items():
            match = provider_pattern.match(key)
            if match:
                provider_name = match.group(1).lower()
                field = match.group(2).lower()
                if provider_name not in self._config["providers"]:
                    self._config["providers"][provider_name] = {}
                self._config["providers"][provider_name][field] = value

    @staticmethod
    def _str_to_bool(value: str) -> bool:
        """Convert string to boolean."""
        return value.lower() in ("true", "1", "yes", "on")

    def load_from_file(self, path: str):
        """Load configuration from YAML or JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        if path.endswith(".json"):
            data = json.loads(content)
        else:
            # Simple YAML parser for basic structures
            data = self._parse_yaml(content)

        self._merge_config(self._config, data)

    def _parse_yaml(self, content: str) -> Dict[str, Any]:
        """Parse simple YAML (no anchors, basic types only)."""
        result: Dict[str, Any] = {}
        lines = content.split("\n")
        i = 0
        n = len(lines)

        def parse_block(start_idx: int, base_indent: int) -> tuple:
            """Parse a block of key-value pairs at given indent level."""
            data: Dict[str, Any] = {}
            j = start_idx
            while j < n:
                line = lines[j]
                stripped = line.lstrip()
                if not stripped or stripped.startswith("#"):
                    j += 1
                    continue

                indent = len(line) - len(stripped)
                if indent < base_indent:
                    break
                if indent > base_indent:
                    j += 1
                    continue

                if ":" in stripped:
                    key, _, value = stripped.partition(":")
                    key = key.strip()
                    value = value.strip()

                    # Check next lines for nested content
                    next_indent = base_indent + 2
                    has_nested = False
                    k = j + 1
                    while k < n:
                        next_line = lines[k]
                        next_stripped = next_line.lstrip()
                        if not next_stripped or next_stripped.startswith("#"):
                            k += 1
                            continue
                        ni = len(next_line) - len(next_stripped)
                        if ni <= base_indent:
                            break
                        if ni >= next_indent and ":" in next_stripped:
                            has_nested = True
                            break
                        k += 1

                    if has_nested:
                        nested, j = parse_block(j + 1, next_indent)
                        data[key] = nested
                    else:
                        if value:
                            data[key] = self._convert_value(value)
                        else:
                            data[key] = {}
                        j += 1
                else:
                    j += 1
            return data, j

        while i < n:
            line = lines[i]
            stripped = line.lstrip()
            if not stripped or stripped.startswith("#"):
                i += 1
                continue

            indent = len(line) - len(stripped)
            if indent > 0:
                i += 1
                continue

            if ":" in stripped:
                key, _, value = stripped.partition(":")
                key = key.strip()
                value = value.strip()

                # Check for nested content
                has_nested = False
                k = i + 1
                while k < n:
                    next_line = lines[k]
                    next_stripped = next_line.lstrip()
                    if not next_stripped or next_stripped.startswith("#"):
                        k += 1
                        continue
                    ni = len(next_line) - len(next_stripped)
                    if ni <= 0:
                        break
                    if ni >= 2 and ":" in next_stripped:
                        has_nested = True
                        break
                    k += 1

                if has_nested:
                    nested, i = parse_block(i + 1, 2)
                    result[key] = nested
                else:
                    if value:
                        result[key] = self._convert_value(value)
                    else:
                        result[key] = {}
                    i += 1
            else:
                i += 1

        return result

    def _convert_value(self, value: str) -> Any:
        """Convert string value to appropriate type."""
        value = value.strip()
        if not value or value.lower() in ("null", "~"):
            return None
        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            return value[1:-1]
        if value.startswith("[") and value.endswith("]"):
            items = value[1:-1].split(",")
            return [self._convert_value(item) for item in items if item.strip()]
        return value

    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]):
        """Recursively merge override into base."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = self._deep_copy(value)

    def get(self, *keys: str, default: Any = None) -> Any:
        """Get nested config value."""
        current = self._config
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    def set(self, *keys: str, value: Any):
        """Set nested config value."""
        current = self._config
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

    @property
    def raw(self) -> Dict[str, Any]:
        """Return raw config dict."""
        return self._deep_copy(self._config)

    def to_json(self) -> str:
        """Export config as JSON string."""
        return json.dumps(self._config, indent=2, ensure_ascii=False)
