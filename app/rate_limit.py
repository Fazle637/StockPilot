"""A small in-memory rate limiter for failed login attempts."""

import time
from collections import defaultdict, deque
from threading import Lock


class LoginRateLimiter:
    """Counts failed logins per client key inside a sliding time window.

    State lives in memory only: it resets when the server restarts and is
    not shared between server processes.
    """

    def __init__(self):
        self._failures = defaultdict(deque)
        self._lock = Lock()

    def _recent(self, key, window):
        """Drop expired failures for a key and return how many remain."""
        attempts = self._failures[key]
        cutoff = time.monotonic() - window

        while attempts and attempts[0] <= cutoff:
            attempts.popleft()

        if not attempts:
            del self._failures[key]
            return 0

        return len(attempts)

    def is_blocked(self, key, max_attempts, window):
        with self._lock:
            return self._recent(key, window) >= max_attempts

    def record_failure(self, key, window):
        with self._lock:
            self._recent(key, window)
            self._failures[key].append(time.monotonic())

    def reset(self, key):
        with self._lock:
            self._failures.pop(key, None)