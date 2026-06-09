"""
LLM Provider abstraction layer.
Supports OpenAI, Anthropic, Google Gemini, and custom providers.
"""

import json
import urllib.request
import urllib.error
import ssl
from typing import Dict, List, Any, Optional, Iterator, Callable
from dataclasses import dataclass, field
from enum import Enum
import time


class ProviderStatus(Enum):
    """Provider health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ProviderMetrics:
    """Runtime metrics for a provider."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_latency_ms: float = 0.0
    last_request_time: Optional[float] = None
    last_error: Optional[str] = None
    status: ProviderStatus = ProviderStatus.UNKNOWN

    @property
    def average_latency_ms(self) -> float:
        if self.successful_requests == 0:
            return 0.0
        return self.total_latency_ms / self.successful_requests

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests


@dataclass
class ProviderConfig:
    """Configuration for an LLM provider."""
    name: str
    api_base: str
    api_key: str
    models: List[str] = field(default_factory=list)
    timeout: int = 60
    weight: int = 1
    enabled: bool = True
    custom_headers: Dict[str, str] = field(default_factory=dict)
    # Provider-specific settings
    supports_streaming: bool = True
    supports_tools: bool = True
    max_tokens_limit: int = 4096
    request_format: str = "openai"  # openai, anthropic, google


class LLMProvider:
    """Base class for LLM providers."""

    def __init__(self, config: ProviderConfig):
        self.config = config
        self.metrics = ProviderMetrics()
        self._ssl_context = ssl.create_default_context()

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Send a chat completion request."""
        raise NotImplementedError

    def stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Iterator[str]:
        """Stream chat completion response."""
        raise NotImplementedError

    def health_check(self) -> bool:
        """Check if provider is healthy."""
        return True

    def _make_request(
        self,
        url: str,
        data: Dict[str, Any],
        headers: Dict[str, str],
        timeout: int = 60
    ) -> Dict[str, Any]:
        """Make HTTP POST request."""
        start_time = time.time()
        self.metrics.total_requests += 1
        self.metrics.last_request_time = start_time

        try:
            json_data = json.dumps(data).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=json_data,
                headers={"Content-Type": "application/json", **headers},
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=timeout, context=self._ssl_context) as resp:
                response_data = json.loads(resp.read().decode("utf-8"))
                latency = (time.time() - start_time) * 1000
                self.metrics.successful_requests += 1
                self.metrics.total_latency_ms += latency
                self.metrics.status = ProviderStatus.HEALTHY
                return response_data

        except urllib.error.HTTPError as e:
            self.metrics.failed_requests += 1
            self.metrics.last_error = f"HTTP {e.code}: {e.reason}"
            self.metrics.status = ProviderStatus.DEGRADED
            try:
                error_body = json.loads(e.read().decode("utf-8"))
                raise ProviderError(f"Provider error: {error_body.get('error', {}).get('message', str(e))}", status_code=e.code)
            except (json.JSONDecodeError, AttributeError):
                raise ProviderError(f"HTTP error {e.code}: {e.reason}", status_code=e.code)

        except Exception as e:
            self.metrics.failed_requests += 1
            self.metrics.last_error = str(e)
            self.metrics.status = ProviderStatus.UNHEALTHY
            raise ProviderError(f"Request failed: {str(e)}")

    def _make_stream_request(
        self,
        url: str,
        data: Dict[str, Any],
        headers: Dict[str, str],
        timeout: int = 60
    ) -> Iterator[str]:
        """Make HTTP POST request with streaming response."""
        start_time = time.time()
        self.metrics.total_requests += 1
        self.metrics.last_request_time = start_time

        try:
            json_data = json.dumps(data).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=json_data,
                headers={"Content-Type": "application/json", **headers},
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=timeout, context=self._ssl_context) as resp:
                latency = (time.time() - start_time) * 1000
                self.metrics.successful_requests += 1
                self.metrics.total_latency_ms += latency
                self.metrics.status = ProviderStatus.HEALTHY

                for line in resp:
                    line = line.decode("utf-8").strip()
                    if line.startswith("data: "):
                        chunk = line[6:]
                        if chunk == "[DONE]":
                            break
                        yield chunk

        except Exception as e:
            self.metrics.failed_requests += 1
            self.metrics.last_error = str(e)
            self.metrics.status = ProviderStatus.UNHEALTHY
            raise ProviderError(f"Stream request failed: {str(e)}")


class OpenAIProvider(LLMProvider):
    """OpenAI-compatible provider (OpenAI, Azure, Groq, etc.)."""

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        url = f"{self.config.api_base.rstrip('/')}/chat/completions"
        payload = {
            "model": model or (self.config.models[0] if self.config.models else "gpt-4o"),
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if tools:
            payload["tools"] = tools
        payload.update(kwargs)

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            **self.config.custom_headers
        }

        if stream:
            # Return streaming format
            chunks = []
            for chunk in self._make_stream_request(url, payload, headers, self.config.timeout):
                try:
                    data = json.loads(chunk)
                    chunks.append(data)
                except json.JSONDecodeError:
                    continue
            return {"stream_chunks": chunks}

        return self._make_request(url, payload, headers, self.config.timeout)

    def stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Iterator[str]:
        url = f"{self.config.api_base.rstrip('/')}/chat/completions"
        payload = {
            "model": model or (self.config.models[0] if self.config.models else "gpt-4o"),
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        payload.update(kwargs)

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            **self.config.custom_headers
        }

        for chunk in self._make_stream_request(url, payload, headers, self.config.timeout):
            yield chunk

    def health_check(self) -> bool:
        """Check provider health via models endpoint."""
        try:
            url = f"{self.config.api_base.rstrip('/')}/models"
            req = urllib.request.Request(
                url,
                headers={"Authorization": f"Bearer {self.config.api_key}"},
                method="GET"
            )
            with urllib.request.urlopen(req, timeout=10, context=self._ssl_context) as resp:
                return resp.status == 200
        except Exception:
            return False


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider with OpenAI-compatible adapter."""

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        url = "https://api.anthropic.com/v1/messages"

        # Convert OpenAI messages to Anthropic format
        system_msg = ""
        anthropic_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system_msg = msg.get("content", "")
            else:
                anthropic_messages.append(msg)

        payload = {
            "model": model or (self.config.models[0] if self.config.models else "claude-3-sonnet-20240229"),
            "messages": anthropic_messages,
            "max_tokens": max_tokens or 4096,
            "temperature": temperature,
            "stream": stream,
        }
        if system_msg:
            payload["system"] = system_msg
        if tools:
            payload["tools"] = tools

        headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
            **self.config.custom_headers
        }

        if stream:
            chunks = []
            for chunk in self._make_stream_request(url, payload, headers, self.config.timeout):
                try:
                    data = json.loads(chunk)
                    chunks.append(data)
                except json.JSONDecodeError:
                    continue
            return {"stream_chunks": chunks}

        response = self._make_request(url, payload, headers, self.config.timeout)
        # Convert Anthropic response to OpenAI format
        return self._to_openai_format(response)

    def stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Iterator[str]:
        url = "https://api.anthropic.com/v1/messages"
        system_msg = ""
        anthropic_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system_msg = msg.get("content", "")
            else:
                anthropic_messages.append(msg)

        payload = {
            "model": model or (self.config.models[0] if self.config.models else "claude-3-sonnet-20240229"),
            "messages": anthropic_messages,
            "max_tokens": max_tokens or 4096,
            "temperature": temperature,
            "stream": True,
        }
        if system_msg:
            payload["system"] = system_msg

        headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        for chunk in self._make_stream_request(url, payload, headers, self.config.timeout):
            yield chunk

    def _to_openai_format(self, anthropic_response: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Anthropic response to OpenAI format."""
        content = ""
        if "content" in anthropic_response:
            for block in anthropic_response["content"]:
                if block.get("type") == "text":
                    content += block.get("text", "")

        return {
            "id": anthropic_response.get("id", ""),
            "object": "chat.completion",
            "created": int(time.time()),
            "model": anthropic_response.get("model", ""),
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                },
                "finish_reason": anthropic_response.get("stop_reason", "stop"),
            }],
            "usage": {
                "prompt_tokens": anthropic_response.get("usage", {}).get("input_tokens", 0),
                "completion_tokens": anthropic_response.get("usage", {}).get("output_tokens", 0),
                "total_tokens": (
                    anthropic_response.get("usage", {}).get("input_tokens", 0) +
                    anthropic_response.get("usage", {}).get("output_tokens", 0)
                ),
            },
        }

    def health_check(self) -> bool:
        try:
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/models",
                headers={"x-api-key": self.config.api_key, "anthropic-version": "2023-06-01"},
                method="GET"
            )
            with urllib.request.urlopen(req, timeout=10, context=self._ssl_context) as resp:
                return resp.status == 200
        except Exception:
            return False


class GoogleProvider(LLMProvider):
    """Google Gemini provider with OpenAI-compatible adapter."""

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        model_name = model or (self.config.models[0] if self.config.models else "gemini-1.5-pro")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.config.api_key}"

        # Convert to Gemini format
        contents = []
        system_instruction = None
        for msg in messages:
            if msg.get("role") == "system":
                system_instruction = {"parts": [{"text": msg.get("content", "")}]}
            else:
                role = "user" if msg.get("role") == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg.get("content", "")}]
                })

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
            },
        }
        if max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        headers = {"Content-Type": "application/json"}

        response = self._make_request(url, payload, headers, self.config.timeout)
        return self._to_openai_format(response, model_name)

    def _to_openai_format(self, gemini_response: Dict[str, Any], model: str) -> Dict[str, Any]:
        """Convert Gemini response to OpenAI format."""
        content = ""
        candidates = gemini_response.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            for part in parts:
                content += part.get("text", "")

        usage = gemini_response.get("usageMetadata", {})
        return {
            "id": gemini_response.get("id", ""),
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                },
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens": usage.get("promptTokenCount", 0),
                "completion_tokens": usage.get("candidatesTokenCount", 0),
                "total_tokens": usage.get("totalTokenCount", 0),
            },
        }

    def health_check(self) -> bool:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.config.api_key}"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=10, context=self._ssl_context) as resp:
                return resp.status == 200
        except Exception:
            return False


class ProviderError(Exception):
    """Provider-specific error."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code


def create_provider(config: ProviderConfig) -> LLMProvider:
    """Factory function to create appropriate provider instance."""
    if config.request_format == "anthropic":
        return AnthropicProvider(config)
    elif config.request_format == "google":
        return GoogleProvider(config)
    else:
        return OpenAIProvider(config)
