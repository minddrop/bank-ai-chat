"""
Core Banking API Client & Resilience Gateway Module
Compliant with REQ-FUN-004, REQ-IF-016, ADR-0008, and FISC Contingency Guidelines.
Provides read-only access with in-memory caching (60s TTL), 1.5s call timeout,
and an automated 3-state Circuit Breaker (CLOSED / OPEN / HALF_OPEN).
"""

import enum
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Dict, Any, Optional, Callable, List, Tuple

from core_banking.service import CoreBankingService


class CircuitState(enum.Enum):
    CLOSED = "CLOSED"        # Normal operational state
    OPEN = "OPEN"            # Tripped: Reject requests immediately to protect core banking
    HALF_OPEN = "HALF_OPEN"  # Testing recovery with single probe request


class CoreBankingTimeoutException(Exception):
    """Raised when Core Banking API response exceeds the 1.5s FISC latency threshold."""
    pass


class CoreBankingCircuitBreakerOpenException(Exception):
    """Raised when Circuit Breaker is OPEN due to elevated error rates or consecutive timeouts."""
    pass


class CircuitBreaker:
    """
    Automated FISC-compliant Circuit Breaker.
    - Threshold: 50% failure rate over a 10-request sliding window OR 3 consecutive failures
    - Open Duration: 30 seconds
    - Recovery: Single probe request in HALF_OPEN transitions back to CLOSED on success
    """

    def __init__(
        self,
        failure_threshold: float = 0.50,
        consecutive_limit: int = 3,
        open_wait_seconds: float = 30.0,
        window_size: int = 10,
        call_timeout_seconds: float = 1.5
    ):
        self.failure_threshold = failure_threshold
        self.consecutive_limit = consecutive_limit
        self.open_wait_seconds = open_wait_seconds
        self.window_size = window_size
        self.call_timeout_seconds = call_timeout_seconds

        self.state: CircuitState = CircuitState.CLOSED
        self.consecutive_failures: int = 0
        self.recent_calls: List[bool] = []  # True = success, False = failure
        self.last_state_change: float = time.time()

    def can_execute(self) -> bool:
        """Evaluate whether a request should be allowed through."""
        now = time.time()
        if self.state == CircuitState.OPEN:
            if now - self.last_state_change >= self.open_wait_seconds:
                self.state = CircuitState.HALF_OPEN
                self.last_state_change = now
                return True
            return False
        return True

    def record_success(self):
        """Record successful invocation."""
        self.consecutive_failures = 0
        self.recent_calls.append(True)
        if len(self.recent_calls) > self.window_size:
            self.recent_calls.pop(0)

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.last_state_change = time.time()

    def record_failure(self):
        """Record failed invocation and trip to OPEN if threshold exceeded."""
        self.consecutive_failures += 1
        self.recent_calls.append(False)
        if len(self.recent_calls) > self.window_size:
            self.recent_calls.pop(0)

        failure_count = self.recent_calls.count(False)
        failure_rate = failure_count / len(self.recent_calls)

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()
        elif (
            self.consecutive_failures >= self.consecutive_limit
            or (len(self.recent_calls) >= 4 and failure_rate >= self.failure_threshold)
        ):
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()

    def trip_open_manually(self):
        """Manually trip the circuit breaker for maintenance or testing."""
        self.state = CircuitState.OPEN
        self.last_state_change = time.time()

    def reset(self):
        """Reset the circuit breaker to clean CLOSED state."""
        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.recent_calls.clear()
        self.last_state_change = time.time()


class CoreBankingClient:
    """
    Decoupled client wrapper providing resilient, cached extraction APIs for the AI Chat System.
    Grounded in REQ-FUN-004, REQ-IF-016, and ADR-0008.
    """

    DEGRADED_MESSAGE = (
        "ただいま口座照会システムがメンテナンス中のため、残高のご案内ができません。"
        "一般的なお手続きや手数料については引き続きご案内可能です。"
    )

    def __init__(
        self,
        service: Optional[CoreBankingService] = None,
        cache_ttl_seconds: float = 60.0,
        call_timeout_seconds: float = 1.5,
        circuit_breaker: Optional[CircuitBreaker] = None
    ):
        self.service = service or CoreBankingService()
        self.cache_ttl = cache_ttl_seconds
        self.call_timeout = call_timeout_seconds
        self.circuit_breaker = circuit_breaker or CircuitBreaker(call_timeout_seconds=call_timeout_seconds)
        self.cache: Dict[str, Tuple[float, Any]] = {}
        self.executor = ThreadPoolExecutor(max_workers=4)

    def _execute_with_resilience(self, cache_key: str, func: Callable, *args, **kwargs) -> Any:
        """Execute call through Cache, Circuit Breaker, and 1.5s Timeout guard."""
        now = time.time()

        # Step 1: Check in-memory Cache (TTL 60s)
        if cache_key in self.cache:
            cached_time, cached_val = self.cache[cache_key]
            if now - cached_time < self.cache_ttl:
                return cached_val

        # Step 2: Check Circuit Breaker State
        if not self.circuit_breaker.can_execute():
            raise CoreBankingCircuitBreakerOpenException(
                f"Core Banking Circuit Breaker is OPEN (state: {self.circuit_breaker.state.value})"
            )

        # Step 3: Execute with 1.5s Timeout
        future = self.executor.submit(func, *args, **kwargs)
        try:
            result = future.result(timeout=self.call_timeout)
            self.circuit_breaker.record_success()
            if result is not None:
                self.cache[cache_key] = (now, result)
            return result
        except FuturesTimeoutError:
            self.circuit_breaker.record_failure()
            raise CoreBankingTimeoutException(
                f"Core Banking request timed out after {self.call_timeout}s"
            )
        except Exception:
            self.circuit_breaker.record_failure()
            raise

    def get_customer_summary(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Fetch customer profile, balances, and recent transaction history with fallback."""
        cache_key = f"profile:{customer_id}"
        try:
            return self._execute_with_resilience(
                cache_key,
                self.service.get_customer_profile,
                customer_id
            )
        except (CoreBankingCircuitBreakerOpenException, CoreBankingTimeoutException, Exception):
            return None

    def extract_account_info(self, customer_id: str) -> Dict[str, Any]:
        """
        Extract structured account info for AI context assembly.
        If Core Banking is unavailable or times out, returns graceful degradation payload (REQ-IF-016).
        """
        cache_key = f"extract:{customer_id}"
        try:
            return self._execute_with_resilience(
                cache_key,
                self.service.extract_account_info_for_ai,
                customer_id
            )
        except (CoreBankingCircuitBreakerOpenException, CoreBankingTimeoutException, Exception) as err:
            return {
                "status": "DEGRADED",
                "customer_id": customer_id,
                "circuit_breaker_state": self.circuit_breaker.state.value,
                "degradation_message": self.DEGRADED_MESSAGE,
                "is_degraded": True,
                "reason": str(err),
                "primary_savings_balance": None,
                "accounts_summary": "【勘定系メンテナンス中】残高照会サービスを一時停止しております。",
                "recent_transactions": []
            }

    def clear_cache(self):
        """Clear all in-memory cached entries."""
        self.cache.clear()
