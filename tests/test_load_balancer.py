"""
Unit tests for load balancer.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from load_balancer import LoadBalancer, LoadBalanceStrategy
from providers import LLMProvider, ProviderConfig, ProviderStatus


class MockProvider(LLMProvider):
    """Mock provider for testing."""

    def __init__(self, name: str, weight: int = 1, enabled: bool = True):
        config = ProviderConfig(
            name=name,
            api_base="http://test",
            api_key="test",
            weight=weight,
            enabled=enabled,
        )
        super().__init__(config)

    def chat_completion(self, **kwargs):
        return {}

    def stream_chat_completion(self, **kwargs):
        yield ""

    def health_check(self):
        return True


class TestLoadBalancer(unittest.TestCase):
    """Test load balancing strategies."""

    def setUp(self):
        self.providers = [
            MockProvider("provider_a", weight=3),
            MockProvider("provider_b", weight=2),
            MockProvider("provider_c", weight=1),
        ]

    def test_round_robin(self):
        """Test round-robin selection."""
        lb = LoadBalancer(LoadBalanceStrategy.ROUND_ROBIN)
        selected = [lb.select_provider(self.providers) for _ in range(6)]
        names = [p.config.name for p in selected]
        # Should cycle through all providers
        self.assertEqual(names[:3], ["provider_a", "provider_b", "provider_c"])
        self.assertEqual(names[3:6], ["provider_a", "provider_b", "provider_c"])

    def test_weighted_selection(self):
        """Test weighted random selection."""
        lb = LoadBalancer(LoadBalanceStrategy.WEIGHTED)
        counts = {"provider_a": 0, "provider_b": 0, "provider_c": 0}

        for _ in range(1000):
            p = lb.select_provider(self.providers)
            counts[p.config.name] += 1

        # Provider A (weight 3) should be selected most often
        self.assertGreater(counts["provider_a"], counts["provider_c"])

    def test_least_latency(self):
        """Test least-latency selection."""
        lb = LoadBalancer(LoadBalanceStrategy.LEAST_LATENCY)

        # Set different latencies
        self.providers[0].metrics.total_latency_ms = 500
        self.providers[0].metrics.successful_requests = 10
        self.providers[1].metrics.total_latency_ms = 100
        self.providers[1].metrics.successful_requests = 10
        self.providers[2].metrics.total_latency_ms = 300
        self.providers[2].metrics.successful_requests = 10

        selected = lb.select_provider(self.providers)
        # Should select provider_b with lowest latency
        self.assertEqual(selected.config.name, "provider_b")

    def test_adaptive_selection(self):
        """Test adaptive selection."""
        lb = LoadBalancer(LoadBalanceStrategy.ADAPTIVE)

        # Provider with best metrics should be selected
        self.providers[0].metrics.successful_requests = 10
        self.providers[0].metrics.total_requests = 10
        self.providers[1].metrics.successful_requests = 5
        self.providers[1].metrics.total_requests = 10

        selected = lb.select_provider(self.providers)
        # Provider A has better success rate
        self.assertEqual(selected.config.name, "provider_a")

    def test_filter_unhealthy(self):
        """Test filtering unhealthy providers."""
        lb = LoadBalancer(LoadBalanceStrategy.ROUND_ROBIN)
        self.providers[0].metrics.status = ProviderStatus.UNHEALTHY

        for _ in range(10):
            selected = lb.select_provider(self.providers)
            self.assertNotEqual(selected.config.name, "provider_a")

    def test_filter_disabled(self):
        """Test filtering disabled providers."""
        lb = LoadBalancer(LoadBalanceStrategy.ROUND_ROBIN)
        self.providers[1].config.enabled = False

        for _ in range(10):
            selected = lb.select_provider(self.providers)
            self.assertNotEqual(selected.config.name, "provider_b")

    def test_no_providers(self):
        """Test with no providers."""
        lb = LoadBalancer()
        result = lb.select_provider([])
        self.assertIsNone(result)

    def test_provider_rankings(self):
        """Test provider rankings."""
        lb = LoadBalancer(LoadBalanceStrategy.ADAPTIVE)
        rankings = lb.get_provider_rankings(self.providers)

        self.assertEqual(len(rankings), 3)
        self.assertIn("name", rankings[0])
        self.assertIn("success_rate", rankings[0])


if __name__ == "__main__":
    unittest.main()
