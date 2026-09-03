"""
Middleware: input sanitization and per-client rate limiting.
"""

from __future__ import annotations

import logging
import re
import time
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)

# Patterns that signal malicious input
_BLOCKED: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"<\s*script",
        r"javascript\s*:",
        r"DROP\s+TABLE",
        r"SELECT\s+\*\s+FROM",
        r"INSERT\s+INTO",
        r"DELETE\s+FROM",
        r";\s*DROP",
        r"UNION\s+SELECT",
        r"exec\s*\(",
        r"system\s*\(",
        r"__import__",
        r"os\.system",
        r"subprocess",
        r"ignore previous instructions",
        r"disregard.*instructions",
    ]
]


def sanitize_input(query: str, max_length: int = 2000) -> str:
    """
    Validate and sanitize the query string.

    Raises:
        ValueError: on length violation or malicious pattern
    Returns:
        Stripped, safe query string
    """
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")

    if len(query) > max_length:
        raise ValueError(f"Query too long ({len(query)} chars, max {max_length})")

    for pattern in _BLOCKED:
        if pattern.search(query):
            logger.warning(f"Blocked query matching pattern: {pattern.pattern[:40]}")
            raise ValueError("Query contains disallowed content")

    return query.strip()


class RateLimiter:
    """
    In-memory sliding-window rate limiter.
    Tracks requests per client_id within a 60-second window.
    """

    def __init__(self, max_per_minute: int = 10) -> None:
        self.max_per_minute = max_per_minute
        self._timestamps: dict[str, list[float]] = defaultdict(list)

    def check(self, client_id: str) -> bool:
        """
        Returns True if request is allowed, False if rate limit exceeded.
        Side effect: records this request timestamp.
        """
        now = time.monotonic()
        window = 60.0
        history = self._timestamps[client_id]

        # Evict old entries
        self._timestamps[client_id] = [t for t in history if now - t < window]

        if len(self._timestamps[client_id]) >= self.max_per_minute:
            logger.warning(f"Rate limit exceeded for client={client_id}")
            return False

        self._timestamps[client_id].append(now)
        return True

    def remaining(self, client_id: str) -> int:
        """How many requests remain in current window."""
        now = time.monotonic()
        valid = [t for t in self._timestamps[client_id] if now - t < 60.0]
        return max(0, self.max_per_minute - len(valid))
