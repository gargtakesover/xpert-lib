"""Rate limiter with sliding window and exponential backoff.

Instead of a global semaphore (which doesn't prevent Twitter rate limits from Nitter's side),
we track request timestamps and add delays between calls. When a 429 is detected,
we enter exponential backoff until the rate limit window passes.
"""

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field

from xpert.config import MAX_CONCURRENT_REQUESTS

logger = logging.getLogger(__name__)


@dataclass
class RateLimitState:
    """Per-instance rate limit state."""
    # Sliding window of request timestamps
    request_times: deque = field(default_factory=deque)
    # Sliding window for 429 detection (separate from general requests)
    rate_limit_times: deque = field(default_factory=deque)
    # Current backoff multiplier (doubles on each 429)
    backoff_multiplier: float = 1.0
    # Timestamp when current backoff ends (0 if not in backoff)
    backoff_until: float = 0.0
    # Lock for thread-safe access
    lock: threading.Lock = field(default_factory=threading.Lock)

    def is_in_backoff(self) -> bool:
        return time.time() < self.backoff_until

    def record_request(self) -> None:
        """Record a request timestamp in the sliding window."""
        now = time.time()
        with self.lock:
            self.request_times.append(now)
            # Expire entries older than 60 seconds
            while self.request_times and self.request_times[0] < now - 60:
                self.request_times.popleft()

    def record_429(self) -> None:
        """Record a 429 response and increase backoff."""
        now = time.time()
        with self.lock:
            self.rate_limit_times.append(now)
            # Expire entries older than 5 minutes
            while self.rate_limit_times and self.rate_limit_times[0] < now - 300:
                self.rate_limit_times.popleft()
            # Double backoff on each 429, up to 5 minutes
            self.backoff_multiplier = min(self.backoff_multiplier * 2, 16.0)
            # Backoff duration: 15s * multiplier
            backoff_duration = 15 * self.backoff_multiplier
            self.backoff_until = now + backoff_duration
            logger.warning("Rate limit detected (429). Backing off for %.1fs", backoff_duration)

    def record_success(self) -> None:
        """Called on successful request — gradually reduce backoff."""
        with self.lock:
            if self.backoff_multiplier > 1.0:
                self.backoff_multiplier = max(self.backoff_multiplier * 0.5, 1.0)
            # Also reset backoff if we had one and it's been a while
            now = time.time()
            if self.backoff_until and now > self.backoff_until:
                self.backoff_until = 0.0

    def should_throttle(self) -> bool:
        """Check if we should throttle to avoid hitting rate limits.

        Uses sliding window: if we've made more than MAX_CONCURRENT_REQUESTS
        requests in the last 60 seconds, throttle.
        When MAX_CONCURRENT_REQUESTS is None (unlimited), returns False.
        """
        if MAX_CONCURRENT_REQUESTS is None:
            return False  # Unlimited: never throttle based on slot count
        now = time.time()
        with self.lock:
            # Expire old entries first
            while self.request_times and self.request_times[0] < now - 60:
                self.request_times.popleft()
            return len(self.request_times) >= MAX_CONCURRENT_REQUESTS

    def wait_if_needed(self) -> None:
        """Block until a request can be made without hitting rate limits."""
        # First check if we're in backoff from a 429
        while self.is_in_backoff():
            remaining = self.backoff_until - time.time()
            if remaining > 0:
                time.sleep(min(remaining, 2.0))  # Sleep in small chunks

        # Then check if we need to throttle based on request frequency
        if self.should_throttle():
            with self.lock:
                if self.request_times:
                    # Wait until the oldest request falls out of the window
                    oldest = self.request_times[0]
                    wait_time = max(oldest + 60 - time.time(), 0.1)
                    logger.debug("Throttling: waiting %.1fs", wait_time)
                    time.sleep(wait_time)


# Global rate limit state — one per process
_rate_limit_state = RateLimitState()


def rate_limit_and_wait() -> None:
    """Call before making a request to Nitter.

    This will block if:
    1. We're in exponential backoff from a recent 429
    2. We've made too many requests in the sliding window
    """
    _rate_limit_state.wait_if_needed()


def record_request() -> None:
    """Record that a request was made. Call after each Nitter request."""
    _rate_limit_state.record_request()


def record_429() -> None:
    """Record a 429 response. Triggers exponential backoff."""
    _rate_limit_state.record_429()


def record_success() -> None:
    """Record a successful request. Gradually reduces backoff."""
    _rate_limit_state.record_success()


def get_state() -> RateLimitState:
    """Get the global rate limit state for inspection."""
    return _rate_limit_state
