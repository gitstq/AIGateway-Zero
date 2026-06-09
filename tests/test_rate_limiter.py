"""
Unit tests for rate limiter.
"""

import sys
import os
import unittest
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from rate_limiter import RateLimiter


class TestRateLimiter(unittest.TestCase):
    """Test rate limiting functionality."""

    def test_basic_rate_limit(self):
        """Test basic rate limiting."""
        rl = RateLimiter(requests_per_window=3, window_seconds=60, enabled=True)

        # First 3 requests should be allowed
        for i in range(3):
            allowed, meta = rl.is_allowed("client_1")
            self.assertTrue(allowed, f"Request {i+1} should be allowed")

        # 4th request should be blocked
        allowed, meta = rl.is_allowed("client_1")
        self.assertFalse(allowed)
        self.assertEqual(meta["remaining"], 0)

    def test_different_clients(self):
        """Test rate limiting per client."""
        rl = RateLimiter(requests_per_window=5, window_seconds=60, enabled=True)

        # Client 1 uses some requests
        rl.is_allowed("client_1")
        rl.is_allowed("client_1")
        rl.is_allowed("client_1")

        # Client 2 should still be allowed (independent per-client limit)
        allowed, _ = rl.is_allowed("client_2")
        self.assertTrue(allowed)

        # Client 2 should be able to use its own quota
        rl.is_allowed("client_2")
        rl.is_allowed("client_2")
        allowed, _ = rl.is_allowed("client_2")
        self.assertTrue(allowed)

        # Client 1 should be blocked after exceeding its limit
        rl.is_allowed("client_1")
        rl.is_allowed("client_1")
        allowed, _ = rl.is_allowed("client_1")
        self.assertFalse(allowed)

    def test_disabled_rate_limiter(self):
        """Test disabled rate limiter allows all requests."""
        rl = RateLimiter(requests_per_window=1, window_seconds=60, enabled=False)

        for _ in range(100):
            allowed, _ = rl.is_allowed("client")
            self.assertTrue(allowed)

    def test_window_reset(self):
        """Test that window resets after time."""
        rl = RateLimiter(requests_per_window=1, window_seconds=1, enabled=True)

        # Use the one request
        rl.is_allowed("client")
        allowed, _ = rl.is_allowed("client")
        self.assertFalse(allowed)

        # Wait for window to reset
        time.sleep(1.1)
        allowed, _ = rl.is_allowed("client")
        self.assertTrue(allowed)

    def test_rate_limit_headers(self):
        """Test rate limit metadata."""
        rl = RateLimiter(requests_per_window=5, window_seconds=60, enabled=True)

        allowed, meta = rl.is_allowed("client")
        self.assertTrue(allowed)
        self.assertEqual(meta["limit"], 5)
        self.assertEqual(meta["remaining"], 4)
        self.assertIn("reset", meta)

    def test_stats(self):
        """Test rate limit statistics."""
        rl = RateLimiter(requests_per_window=10, window_seconds=60, enabled=True)

        for _ in range(3):
            rl.is_allowed("client")

        stats = rl.get_stats("client")
        self.assertEqual(stats["current_requests"], 3)
        self.assertEqual(stats["remaining"], 7)


if __name__ == "__main__":
    unittest.main()
