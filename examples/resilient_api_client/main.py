"""
Resilient API Client — Circuit Breaker Pattern Example
=======================================================
Demonstrates the three-state circuit breaker (CLOSED → OPEN → HALF_OPEN → CLOSED).

Run:
    python3 examples/resilient_api_client/main.py

No external dependencies required.
"""

import time
import random
from enum import Enum


# ── State machine ──────────────────────────────────────────────────────────────

class State(Enum):
    CLOSED    = "CLOSED"      # Normal — requests flow through
    OPEN      = "OPEN"        # Tripped — requests blocked, fallback returned
    HALF_OPEN = "HALF_OPEN"   # Probing — one request allowed to test recovery


class CircuitBreaker:
    """
    Wraps any callable and tracks its failure rate.

    Parameters
    ----------
    failure_threshold : int   – consecutive failures before opening
    recovery_timeout  : float – seconds to wait before probing in HALF_OPEN
    probe_successes   : int   – successes needed in HALF_OPEN before closing
    """

    def __init__(self, name: str, failure_threshold=3,
                 recovery_timeout=5.0, probe_successes=1):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout  = recovery_timeout
        self.probe_successes   = probe_successes

        self._state            = State.CLOSED
        self._consecutive_fail = 0
        self._probe_ok         = 0
        self._opened_at        = None

    # ── Public ─────────────────────────────────────────────────────────────────

    @property
    def state(self) -> State:
        # Auto-transition OPEN → HALF_OPEN after timeout
        if self._state == State.OPEN:
            elapsed = time.time() - self._opened_at
            if elapsed >= self.recovery_timeout:
                self._transition(State.HALF_OPEN)
        return self._state

    def call(self, fn, *args, **kwargs):
        """Execute fn through the breaker. Raises CircuitOpenError if blocked."""
        s = self.state

        if s == State.OPEN:
            raise CircuitOpenError(f"[{self.name}] Circuit is OPEN — call blocked")

        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure()
            raise

    # ── Internal ───────────────────────────────────────────────────────────────

    def _on_success(self):
        if self._state == State.HALF_OPEN:
            self._probe_ok += 1
            if self._probe_ok >= self.probe_successes:
                self._transition(State.CLOSED)
        else:
            # Reset failure counter on every success in CLOSED state
            self._consecutive_fail = 0

    def _on_failure(self):
        self._consecutive_fail += 1
        if self._state == State.HALF_OPEN:
            # Probe failed — reopen immediately
            self._transition(State.OPEN)
        elif self._consecutive_fail >= self.failure_threshold:
            self._transition(State.OPEN)

    def _transition(self, new_state: State):
        print(f"  [breaker:{self.name}] {self._state.value} → {new_state.value}")
        self._state = new_state
        if new_state == State.OPEN:
            self._opened_at = time.time()
        if new_state == State.CLOSED:
            self._consecutive_fail = 0
            self._probe_ok         = 0


class CircuitOpenError(Exception):
    pass


# ── Fake HTTP client ───────────────────────────────────────────────────────────

def fake_http_get(url: str, fail_probability: float = 0.0) -> dict:
    """Simulates an HTTP GET that randomly raises on failure."""
    if random.random() < fail_probability:
        raise ConnectionError(f"HTTP timeout on {url}")
    return {"status": 200, "url": url, "data": "ok"}


# ── Demo harness ───────────────────────────────────────────────────────────────

def demo():
    random.seed(42)
    breaker = CircuitBreaker("payments-api", failure_threshold=3, recovery_timeout=3.0)

    print("=" * 60)
    print("Phase 1: Healthy traffic (fail_probability=0.1)")
    print("=" * 60)
    for i in range(5):
        try:
            result = breaker.call(fake_http_get, "https://api.example.com/pay", fail_probability=0.1)
            print(f"  req {i+1}: OK  — state={breaker.state.value}")
        except CircuitOpenError as e:
            print(f"  req {i+1}: BLOCKED — {e}")
        except ConnectionError as e:
            print(f"  req {i+1}: FAIL   — {e}  (failures={breaker._consecutive_fail})")

    print()
    print("=" * 60)
    print("Phase 2: Degraded service (fail_probability=1.0) — breaker trips")
    print("=" * 60)
    for i in range(6):
        try:
            breaker.call(fake_http_get, "https://api.example.com/pay", fail_probability=1.0)
        except CircuitOpenError as e:
            print(f"  req {i+1}: BLOCKED — circuit is OPEN, fast-fail returned")
        except ConnectionError as e:
            print(f"  req {i+1}: FAIL   — {e}  (failures={breaker._consecutive_fail})")

    print()
    print("=" * 60)
    print(f"Phase 3: Waiting {breaker.recovery_timeout}s for HALF_OPEN probe window...")
    print("=" * 60)
    time.sleep(breaker.recovery_timeout + 0.1)

    print("Phase 4: Service recovered — single probe succeeds")
    try:
        result = breaker.call(fake_http_get, "https://api.example.com/pay", fail_probability=0.0)
        print(f"  probe: OK — state={breaker.state.value}")
    except Exception as e:
        print(f"  probe: {e}")

    print()
    print("Phase 5: Normal traffic resumes")
    for i in range(3):
        try:
            breaker.call(fake_http_get, "https://api.example.com/pay", fail_probability=0.0)
            print(f"  req {i+1}: OK  — state={breaker.state.value}")
        except Exception as e:
            print(f"  req {i+1}: {e}")

    print()
    print("Done. Circuit breaker prevented downstream overload during outage.")


if __name__ == "__main__":
    demo()
