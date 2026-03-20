"""Circuit breaker for Nitter instance health."""

import threading
import time
from enum import Enum
from typing import Optional


class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


class CircuitBreaker:
    """
    Thread-safe circuit breaker that trips after consecutive failures.

    Use as a decorator or context manager around Nitter fetch calls.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 3,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = threading.RLock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if self._last_failure_time:
                    elapsed = time.time() - self._last_failure_time
                    if elapsed >= self.recovery_timeout:
                        self._state = CircuitState.HALF_OPEN
                        self._half_open_calls = 0
                        self._failure_count = 0  # Reset for clean half-open probe
            return self._state

    def can_execute(self) -> bool:
        """Check if a request is allowed."""
        with self._lock:
            s = self.state
            if s == CircuitState.CLOSED:
                return True
            if s == CircuitState.HALF_OPEN:
                return self._half_open_calls < self.half_open_max_calls
            return False  # OPEN

    def record_success(self) -> None:
        """Record a successful request."""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.half_open_max_calls:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0

    def record_failure(self) -> None:
        """Record a failed request."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._success_count = 0
            elif self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN

    def get_open_message(self) -> str:
        """Return user-friendly message when circuit is open."""
        elapsed = 0.0
        with self._lock:
            if self._last_failure_time:
                elapsed = time.time() - self._last_failure_time
        retry_in = max(0, self.recovery_timeout - elapsed)
        return (
            f"Circuit breaker is open. "
            f"Too many failures. Retry in {retry_in:.0f}s. "
            f"Run 'xpert status' for details."
        )


# Global circuit breaker instance
nitter_circuit = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=30.0,
    half_open_max_calls=3,
)
