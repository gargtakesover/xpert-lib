"""Tests for circuit breaker."""
import pytest
import time
from xpert.circuit_breaker import CircuitBreaker, CircuitState

def test_circuit_initial_state():
    cb = CircuitBreaker()
    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True

def test_circuit_opens_after_failures():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
    for _ in range(3):
        cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.can_execute() is False

def test_circuit_half_open_after_timeout():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.5)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    time.sleep(0.6)
    assert cb.state == CircuitState.HALF_OPEN
    assert cb.can_execute() is True

def test_circuit_closes_after_success_in_half_open():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1, half_open_max_calls=2)
    cb.record_failure()  # _failure_count=1, state=CLOSED
    cb.record_failure()  # _failure_count=2, state=OPEN (tripped)
    time.sleep(0.2)     # Wait for recovery timeout -> state=HALF_OPEN (resets _failure_count)
    assert cb.state == CircuitState.HALF_OPEN
    cb.record_success()  # _success_count=1
    assert cb.state == CircuitState.HALF_OPEN
    cb.record_success()  # _success_count=2 >= half_open_max_calls=2 -> state=CLOSED
    assert cb.state == CircuitState.CLOSED
