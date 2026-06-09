"""
Rate limiting with sliding window algorithm.
Supports per-IP and global rate limits.
"""

import time
import threading
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque


@dataclass
class RateLimitEntry:
    """Entry for tracking requests in time window."""
    timestamps: deque = field(default_factory=lambda: deque(maxlen=10000))
    lock: threading.Lock = field(default_factory=threading.Lock)


class RateLimiter:
    """Sliding window rate limiter."""

    def __init__(
        self,
        requests_per_window: int = 100,
        window_seconds: int = 60,
        enabled: bool = True
    ):
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.enabled = enabled
        self._entries: Dict[str, RateLimitEntry] = {}
        self._global_entry = RateLimitEntry()
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()
        self._lock = threading.Lock()

    def is_allowed(self, key: str) -> Tuple[bool, Dict[str, any]]:
        """
        Check if request is allowed.
        Returns (allowed, metadata).
        """
        if not self.enabled:
            return True, {"limit": -1, "remaining": -1, "reset": -1}

        now = time.time()
        self._cleanup_if_needed(now)

        # Check per-key limit
        with self._lock:
            if key not in self._entries:
                self._entries[key] = RateLimitEntry()
            entry = self._entries[key]

        allowed, meta = self._check_entry(entry, now)
        return allowed, meta

    def _check_entry(self, entry: RateLimitEntry, now: float) -> Tuple[bool, Dict[str, any]]:
        """Check if entry is within rate limit."""
        with entry.lock:
            # Remove timestamps outside window
            cutoff = now - self.window_seconds
            while entry.timestamps and entry.timestamps[0] < cutoff:
                entry.timestamps.popleft()

            current_count = len(entry.timestamps)
            remaining = max(0, self.requests_per_window - current_count)
            reset_time = int(now + self.window_seconds)

            if current_count >= self.requests_per_window:
                return False, {
                    "limit": self.requests_per_window,
                    "remaining": 0,
                    "reset": reset_time,
                    "retry_after": int(self.window_seconds - (now - entry.timestamps[0])) if entry.timestamps else self.window_seconds,
                }

            entry.timestamps.append(now)
            return True, {
                "limit": self.requests_per_window,
                "remaining": remaining - 1,
                "reset": reset_time,
            }

    def _cleanup_if_needed(self, now: float):
        """Clean up old entries periodically."""
        if now - self._last_cleanup < self._cleanup_interval:
            return

        with self._lock:
            cutoff = now - self.window_seconds * 2
            keys_to_remove = []
            for key, entry in self._entries.items():
                with entry.lock:
                    while entry.timestamps and entry.timestamps[0] < cutoff:
                        entry.timestamps.popleft()
                    if not entry.timestamps:
                        keys_to_remove.append(key)

            for key in keys_to_remove:
                del self._entries[key]

            self._last_cleanup = now

    def get_stats(self, key: Optional[str] = None) -> Dict[str, any]:
        """Get rate limit statistics."""
        now = time.time()
        cutoff = now - self.window_seconds

        stats = {
            "enabled": self.enabled,
            "limit": self.requests_per_window,
            "window_seconds": self.window_seconds,
        }

        if key and key in self._entries:
            entry = self._entries[key]
            with entry.lock:
                count = sum(1 for t in entry.timestamps if t > cutoff)
                stats["current_requests"] = count
                stats["remaining"] = max(0, self.requests_per_window - count)
        else:
            with self._global_entry.lock:
                count = sum(1 for t in self._global_entry.timestamps if t > cutoff)
                stats["current_requests"] = count
                stats["remaining"] = max(0, self.requests_per_window - count)

        return stats
