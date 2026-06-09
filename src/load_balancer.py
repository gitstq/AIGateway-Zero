"""
Load balancing strategies for routing requests across providers.
Supports round-robin, least-latency, weighted, and adaptive strategies.
"""

import random
import time
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from providers import LLMProvider, ProviderStatus


class LoadBalanceStrategy(Enum):
    """Available load balancing strategies."""
    ROUND_ROBIN = "round_robin"
    LEAST_LATENCY = "least_latency"
    WEIGHTED = "weighted"
    ADAPTIVE = "adaptive"
    RANDOM = "random"


@dataclass
class ProviderScore:
    """Score for provider selection."""
    provider: LLMProvider
    score: float
    reason: str


class LoadBalancer:
    """Intelligent load balancer for LLM providers."""

    def __init__(self, strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN):
        self.strategy = strategy
        self._round_robin_index = 0
        self._provider_scores: Dict[str, List[float]] = {}
        self._score_window_size = 10

    def select_provider(
        self,
        providers: List[LLMProvider],
        model: Optional[str] = None
    ) -> Optional[LLMProvider]:
        """Select the best provider based on strategy."""
        healthy = self._filter_healthy(providers, model)
        if not healthy:
            return None

        if self.strategy == LoadBalanceStrategy.ROUND_ROBIN:
            return self._round_robin(healthy)
        elif self.strategy == LoadBalanceStrategy.LEAST_LATENCY:
            return self._least_latency(healthy)
        elif self.strategy == LoadBalanceStrategy.WEIGHTED:
            return self._weighted(healthy)
        elif self.strategy == LoadBalanceStrategy.ADAPTIVE:
            return self._adaptive(healthy)
        elif self.strategy == LoadBalanceStrategy.RANDOM:
            return self._random(healthy)
        else:
            return self._round_robin(healthy)

    def _filter_healthy(
        self,
        providers: List[LLMProvider],
        model: Optional[str] = None
    ) -> List[LLMProvider]:
        """Filter to healthy providers that support the requested model."""
        healthy = []
        for p in providers:
            if not p.config.enabled:
                continue
            if p.metrics.status in (ProviderStatus.UNHEALTHY,):
                continue
            if model and p.config.models and model not in p.config.models:
                continue
            healthy.append(p)
        return healthy

    def _round_robin(self, providers: List[LLMProvider]) -> LLMProvider:
        """Simple round-robin selection."""
        if not providers:
            raise ValueError("No providers available")
        idx = self._round_robin_index % len(providers)
        self._round_robin_index = (self._round_robin_index + 1) % len(providers)
        return providers[idx]

    def _least_latency(self, providers: List[LLMProvider]) -> LLMProvider:
        """Select provider with lowest average latency."""
        if not providers:
            raise ValueError("No providers available")

        best = providers[0]
        best_latency = best.metrics.average_latency_ms or float("inf")

        for p in providers[1:]:
            latency = p.metrics.average_latency_ms
            if latency == 0:  # No data yet, prefer this
                return p
            if latency < best_latency:
                best = p
                best_latency = latency

        return best

    def _weighted(self, providers: List[LLMProvider]) -> LLMProvider:
        """Weighted random selection based on provider weights."""
        if not providers:
            raise ValueError("No providers available")

        total_weight = sum(p.config.weight for p in providers)
        if total_weight == 0:
            return self._random(providers)

        pick = random.uniform(0, total_weight)
        current = 0
        for p in providers:
            current += p.config.weight
            if pick <= current:
                return p

        return providers[-1]

    def _adaptive(self, providers: List[LLMProvider]) -> LLMProvider:
        """
        Adaptive selection based on success rate and latency.
        Combines multiple factors into a composite score.
        """
        if not providers:
            raise ValueError("No providers available")

        scores = []
        for p in providers:
            score = self._calculate_adaptive_score(p)
            scores.append((p, score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[0][0]

    def _calculate_adaptive_score(self, provider: LLMProvider) -> float:
        """Calculate composite score for adaptive selection."""
        m = provider.metrics

        # Success rate factor (0-1)
        success_score = m.success_rate

        # Latency factor (lower is better, normalize to 0-1)
        latency = m.average_latency_ms
        if latency == 0:
            latency_score = 1.0
        else:
            latency_score = max(0, 1.0 - (latency / 5000.0))

        # Recency factor (prefer recently successful providers)
        recency_score = 1.0
        if m.last_request_time:
            time_since_last = time.time() - m.last_request_time
            if time_since_last > 300:  # 5 minutes
                recency_score = 0.5

        # Weight factor
        weight_score = min(1.0, provider.config.weight / 10.0)

        # Composite score with weights
        composite = (
            success_score * 0.4 +
            latency_score * 0.3 +
            recency_score * 0.2 +
            weight_score * 0.1
        )

        return composite

    def _random(self, providers: List[LLMProvider]) -> LLMProvider:
        """Random selection."""
        if not providers:
            raise ValueError("No providers available")
        return random.choice(providers)

    def update_score(self, provider_name: str, latency_ms: float, success: bool):
        """Update provider score after request."""
        if provider_name not in self._provider_scores:
            self._provider_scores[provider_name] = []

        scores = self._provider_scores[provider_name]
        score = 1.0 if success else 0.0
        scores.append(score)

        # Keep only recent scores
        if len(scores) > self._score_window_size:
            scores.pop(0)

    def get_provider_rankings(self, providers: List[LLMProvider]) -> List[Dict[str, Any]]:
        """Get ranked list of providers with scores."""
        rankings = []
        for p in providers:
            rankings.append({
                "name": p.config.name,
                "status": p.metrics.status.value,
                "success_rate": round(p.metrics.success_rate, 3),
                "avg_latency_ms": round(p.metrics.average_latency_ms, 2),
                "total_requests": p.metrics.total_requests,
                "weight": p.config.weight,
                "adaptive_score": round(self._calculate_adaptive_score(p), 3) if self.strategy == LoadBalanceStrategy.ADAPTIVE else None,
            })

        if self.strategy == LoadBalanceStrategy.ADAPTIVE:
            rankings.sort(key=lambda x: x["adaptive_score"] or 0, reverse=True)
        elif self.strategy == LoadBalanceStrategy.LEAST_LATENCY:
            rankings.sort(key=lambda x: x["avg_latency_ms"] if x["avg_latency_ms"] > 0 else float("inf"))

        return rankings
