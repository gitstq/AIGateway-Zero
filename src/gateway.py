"""
Core gateway logic: request routing, provider management, fallback, and metrics.
"""

import json
import time
import logging
import threading
from typing import Dict, List, Any, Optional, Iterator
from dataclasses import dataclass, field

from config import Config
from providers import (
    LLMProvider, ProviderConfig, ProviderStatus,
    create_provider, ProviderError
)
from load_balancer import LoadBalancer, LoadBalanceStrategy
from rate_limiter import RateLimiter
from guardrails import Guardrails
from server import Router, Request, Response


@dataclass
class GatewayMetrics:
    """Gateway-wide metrics."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens_prompt: int = 0
    total_tokens_completion: int = 0
    start_time: float = field(default_factory=time.time)

    @property
    def uptime_seconds(self) -> float:
        return time.time() - self.start_time


class AIGateway:
    """
    AI Gateway core: manages providers, routes requests,
    handles load balancing, fallback, and metrics.
    """

    def __init__(self, config: Config):
        self.config = config
        self.providers: Dict[str, LLMProvider] = {}
        self.load_balancer: LoadBalancer = self._create_load_balancer()
        self.rate_limiter = self._create_rate_limiter()
        self.guardrails = self._create_guardrails()
        self.metrics = GatewayMetrics()
        self.logger = self._setup_logging()
        self._health_check_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()

        self._init_providers()
        self._start_health_checks()

    def _setup_logging(self) -> logging.Logger:
        """Configure logging."""
        logger = logging.getLogger("AIGateway")
        level = getattr(logging, self.config.get("logging", "level", default="INFO"), logging.INFO)
        logger.setLevel(level)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                self.config.get("logging", "format", default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

            log_file = self.config.get("logging", "file")
            if log_file:
                file_handler = logging.FileHandler(log_file)
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)

        return logger

    def _create_load_balancer(self) -> LoadBalancer:
        """Create load balancer from config."""
        strategy_name = self.config.get("gateway", "load_balance_strategy", default="round_robin")
        try:
            strategy = LoadBalanceStrategy(strategy_name)
        except ValueError:
            strategy = LoadBalanceStrategy.ROUND_ROBIN
        return LoadBalancer(strategy)

    def _create_rate_limiter(self) -> RateLimiter:
        """Create rate limiter from config."""
        return RateLimiter(
            requests_per_window=self.config.get("gateway", "rate_limit_requests", default=100),
            window_seconds=self.config.get("gateway", "rate_limit_window", default=60),
            enabled=self.config.get("gateway", "rate_limit_enabled", default=True),
        )

    def _create_guardrails(self) -> Guardrails:
        """Create guardrails from config."""
        guard_config = self.config.get("guardrails", default={})
        return Guardrails(
            enabled=guard_config.get("enabled", False),
            max_input_length=guard_config.get("max_input_length", 32000),
            max_output_length=guard_config.get("max_output_length", 16000),
            blocked_keywords=guard_config.get("blocked_keywords", []),
            allowed_models=guard_config.get("allowed_models", []),
        )

    def _init_providers(self):
        """Initialize providers from configuration."""
        provider_configs = self.config.get("providers", default={})

        # Default demo providers if none configured
        if not provider_configs:
            self.logger.info("No providers configured. Gateway will start in demo mode.")
            return

        for name, cfg in provider_configs.items():
            if not isinstance(cfg, dict):
                continue

            try:
                pconfig = ProviderConfig(
                    name=name,
                    api_base=cfg.get("api_base", ""),
                    api_key=cfg.get("api_key", ""),
                    models=cfg.get("models", []),
                    timeout=cfg.get("timeout", 60),
                    weight=cfg.get("weight", 1),
                    enabled=cfg.get("enabled", True),
                    request_format=cfg.get("request_format", "openai"),
                    supports_streaming=cfg.get("supports_streaming", True),
                    supports_tools=cfg.get("supports_tools", True),
                )
                provider = create_provider(pconfig)
                self.providers[name] = provider
                self.logger.info(f"Provider '{name}' initialized ({pconfig.request_format})")
            except Exception as e:
                self.logger.error(f"Failed to initialize provider '{name}': {e}")

    def _start_health_checks(self):
        """Start background health check thread."""
        interval = self.config.get("gateway", "health_check_interval", default=30)

        def health_check_loop():
            while not self._shutdown_event.is_set():
                for name, provider in self.providers.items():
                    try:
                        healthy = provider.health_check()
                        if healthy:
                            if provider.metrics.status == ProviderStatus.UNHEALTHY:
                                provider.metrics.status = ProviderStatus.HEALTHY
                                self.logger.info(f"Provider '{name}' recovered")
                        else:
                            provider.metrics.status = ProviderStatus.UNHEALTHY
                            self.logger.warning(f"Provider '{name}' health check failed")
                    except Exception as e:
                        provider.metrics.status = ProviderStatus.UNHEALTHY
                        self.logger.warning(f"Provider '{name}' health check error: {e}")

                self._shutdown_event.wait(interval)

        self._health_check_thread = threading.Thread(target=health_check_loop, daemon=True)
        self._health_check_thread.start()

    def shutdown(self):
        """Gracefully shutdown the gateway."""
        self._shutdown_event.set()
        if self._health_check_thread:
            self._health_check_thread.join(timeout=5)
        self.logger.info("Gateway shutdown complete")

    def get_router(self) -> Router:
        """Create and configure HTTP router."""
        router = Router()

        # OpenAI-compatible endpoints
        router.post("/v1/chat/completions", self._handle_chat_completion)
        router.get("/v1/models", self._handle_list_models)
        router.get("/v1/models/{model}", self._handle_get_model)

        # Gateway management endpoints
        router.get("/gateway/status", self._handle_gateway_status)
        router.get("/gateway/providers", self._handle_list_providers)
        router.get("/gateway/metrics", self._handle_gateway_metrics)
        router.get("/gateway/health", self._handle_health_check)

        # Middleware
        router.add_middleware(self._logging_middleware)
        router.add_middleware(self._rate_limit_middleware)

        return router

    def _logging_middleware(self, request: Request, handler) -> Response:
        """Log incoming requests."""
        start = time.time()
        self.logger.info(f"{request.method} {request.path} from {request.get_client_ip()}")
        response = handler(request)
        duration = (time.time() - start) * 1000
        self.logger.info(f"{request.method} {request.path} -> {response.status_code} ({duration:.2f}ms)")
        return response

    def _rate_limit_middleware(self, request: Request, handler) -> Response:
        """Rate limit middleware."""
        client_ip = request.get_client_ip()
        allowed, meta = self.rate_limiter.is_allowed(client_ip)

        if not allowed:
            return Response().set_status(429).json({
                "error": {
                    "message": "Rate limit exceeded",
                    "type": "rate_limit_error",
                    "code": 429,
                    "retry_after": meta.get("retry_after", 60),
                }
            })

        response = handler(request)
        # Add rate limit headers
        response.set_header("X-RateLimit-Limit", str(meta.get("limit", "")))
        response.set_header("X-RateLimit-Remaining", str(meta.get("remaining", "")))
        response.set_header("X-RateLimit-Reset", str(meta.get("reset", "")))
        return response

    def _handle_chat_completion(self, request: Request) -> Response:
        """Handle chat completion requests."""
        body = request.get_json()
        if not body:
            return Response().error("Invalid JSON body", 400)

        # Guardrails check
        guard_result = self.guardrails.check_request_body(body)
        if not guard_result.allowed:
            return Response().error(guard_result.reason or "Guardrails blocked", 400)

        messages = body.get("messages", [])
        model = body.get("model") or self.config.get("gateway", "default_model", default="gpt-4o")
        temperature = body.get("temperature", 0.7)
        max_tokens = body.get("max_tokens")
        stream = body.get("stream", False)
        tools = body.get("tools")

        self.metrics.total_requests += 1

        # Select provider
        provider_list = list(self.providers.values())
        if not provider_list:
            return Response().error("No providers configured", 503)

        provider = self.load_balancer.select_provider(provider_list, model)
        if not provider:
            return Response().error("No healthy providers available for model", 503)

        # Try with fallback
        fallback_enabled = self.config.get("gateway", "fallback_enabled", default=True)
        retry_attempts = self.config.get("gateway", "retry_attempts", default=3)
        retry_delay = self.config.get("gateway", "retry_delay", default=1.0)

        last_error = None
        attempted_providers = [provider]

        for attempt in range(retry_attempts):
            try:
                if stream:
                    return self._handle_streaming(
                        provider, messages, model, temperature, max_tokens
                    )
                else:
                    response = provider.chat_completion(
                        messages=messages,
                        model=model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        stream=False,
                        tools=tools,
                    )
                    self.metrics.successful_requests += 1
                    usage = response.get("usage", {})
                    self.metrics.total_tokens_prompt += usage.get("prompt_tokens", 0)
                    self.metrics.total_tokens_completion += usage.get("completion_tokens", 0)
                    return Response().json(response)

            except ProviderError as e:
                last_error = e
                self.logger.warning(
                    f"Provider '{provider.config.name}' failed (attempt {attempt + 1}/{retry_attempts}): {e}"
                )

                if fallback_enabled and attempt < retry_attempts - 1:
                    # Try another provider
                    time.sleep(retry_delay)
                    remaining = [p for p in provider_list if p not in attempted_providers and p.config.enabled]
                    if remaining:
                        provider = self.load_balancer.select_provider(remaining, model)
                        if provider:
                            attempted_providers.append(provider)
                            continue

                break

        self.metrics.failed_requests += 1
        status_code = last_error.status_code if last_error else 500
        return Response().error(
            str(last_error) if last_error else "All providers failed",
            status_code
        )

    def _handle_streaming(
        self,
        provider: LLMProvider,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: Optional[int],
    ) -> Response:
        """Handle streaming chat completion."""
        response = Response()
        response.set_status(200)
        response.set_header("Content-Type", "text/event-stream")
        response.set_header("Cache-Control", "no-cache")
        response.set_header("Connection", "keep-alive")

        # For standard library server, we need to handle streaming differently
        # We'll collect and return as a single response for simplicity
        # In production, this would use proper SSE streaming
        chunks = []
        try:
            for chunk in provider.stream_chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            ):
                chunks.append(chunk)

            self.metrics.successful_requests += 1

            # Format as SSE
            sse_data = ""
            for chunk in chunks:
                sse_data += f"data: {chunk}\n\n"
            sse_data += "data: [DONE]\n\n"

            response.body = sse_data.encode("utf-8")
            return response

        except Exception as e:
            self.metrics.failed_requests += 1
            return Response().error(f"Streaming failed: {e}", 500)

    def _handle_list_models(self, request: Request) -> Response:
        """List available models."""
        models = []
        seen = set()

        for provider in self.providers.values():
            for model in provider.config.models:
                if model not in seen:
                    seen.add(model)
                    models.append({
                        "id": model,
                        "object": "model",
                        "created": int(time.time()),
                        "owned_by": provider.config.name,
                    })

        # Add default model if no providers configured
        if not models:
            default_model = self.config.get("gateway", "default_model", default="gpt-4o")
            models.append({
                "id": default_model,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "gateway",
            })

        return Response().json({
            "object": "list",
            "data": models,
        })

    def _handle_get_model(self, request: Request) -> Response:
        """Get specific model info."""
        model_id = request.path_params.get("model", "")

        for provider in self.providers.values():
            if model_id in provider.config.models:
                return Response().json({
                    "id": model_id,
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": provider.config.name,
                })

        return Response().error(f"Model '{model_id}' not found", 404)

    def _handle_gateway_status(self, request: Request) -> Response:
        """Get gateway status."""
        return Response().json({
            "status": "running",
            "version": "1.0.0",
            "uptime_seconds": round(self.metrics.uptime_seconds, 2),
            "providers": {
                "total": len(self.providers),
                "healthy": sum(1 for p in self.providers.values() if p.metrics.status == ProviderStatus.HEALTHY),
            },
            "requests": {
                "total": self.metrics.total_requests,
                "successful": self.metrics.successful_requests,
                "failed": self.metrics.failed_requests,
            },
            "tokens": {
                "prompt": self.metrics.total_tokens_prompt,
                "completion": self.metrics.total_tokens_completion,
            },
            "load_balance_strategy": self.load_balancer.strategy.value,
            "guardrails": self.guardrails.to_dict(),
        })

    def _handle_list_providers(self, request: Request) -> Response:
        """List all providers with metrics."""
        provider_data = []
        for name, provider in self.providers.items():
            provider_data.append({
                "name": name,
                "enabled": provider.config.enabled,
                "status": provider.metrics.status.value,
                "models": provider.config.models,
                "weight": provider.config.weight,
                "metrics": {
                    "total_requests": provider.metrics.total_requests,
                    "successful_requests": provider.metrics.successful_requests,
                    "failed_requests": provider.metrics.failed_requests,
                    "average_latency_ms": round(provider.metrics.average_latency_ms, 2),
                    "success_rate": round(provider.metrics.success_rate, 3),
                },
            })

        rankings = self.load_balancer.get_provider_rankings(list(self.providers.values()))

        return Response().json({
            "providers": provider_data,
            "rankings": rankings,
        })

    def _handle_gateway_metrics(self, request: Request) -> Response:
        """Get detailed gateway metrics."""
        return Response().json({
            "gateway": {
                "uptime_seconds": round(self.metrics.uptime_seconds, 2),
                "total_requests": self.metrics.total_requests,
                "successful_requests": self.metrics.successful_requests,
                "failed_requests": self.metrics.failed_requests,
                "success_rate": round(
                    self.metrics.successful_requests / max(1, self.metrics.total_requests), 3
                ),
                "total_tokens": {
                    "prompt": self.metrics.total_tokens_prompt,
                    "completion": self.metrics.total_tokens_completion,
                },
            },
            "rate_limiter": self.rate_limiter.get_stats(),
            "provider_rankings": self.load_balancer.get_provider_rankings(
                list(self.providers.values())
            ),
        })

    def _handle_health_check(self, request: Request) -> Response:
        """Simple health check endpoint."""
        healthy_count = sum(
            1 for p in self.providers.values()
            if p.metrics.status == ProviderStatus.HEALTHY
        )
        total = len(self.providers)

        if total == 0:
            # No providers configured, gateway itself is healthy
            return Response().json({"status": "healthy", "providers": 0})

        if healthy_count == 0:
            return Response().set_status(503).json({
                "status": "unhealthy",
                "providers": {"total": total, "healthy": 0},
            })

        return Response().json({
            "status": "healthy",
            "providers": {"total": total, "healthy": healthy_count},
        })
