"""
Fault Injector Module for Banking Chaos Engineering
Provides thread-safe and context-scoped failure injection mechanisms
including latency injection, exception throwing, data corruption, and resource exhaustion.
"""

import contextvars
import os
import random
import time
from typing import Dict, Any, Optional, Callable, List

# Context variable to hold per-request active chaos scenarios (e.g. from HTTP headers)
_request_chaos_scenario: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "request_chaos_scenario", default=None
)

# Global chaos state for full-system GameDay simulations
_global_active_scenarios: Dict[str, Dict[str, Any]] = {}


def is_chaos_enabled() -> bool:
    """Check if chaos engineering is enabled in the current environment."""
    env_val = os.environ.get("CHAOS_ENGINEERING_ENABLED", "").lower()
    # Default to true in non-production, test, or when explicitly enabled
    if env_val in ["1", "true", "yes", "enabled"]:
        return True
    if os.environ.get("ENV", "development").lower() in ["development", "test", "staging"]:
        return True
    return False


def set_request_chaos_scenario(scenario_name: Optional[str]):
    """Set the chaos scenario for the current asynchronous request context."""
    _request_chaos_scenario.set(scenario_name)


def get_request_chaos_scenario() -> Optional[str]:
    """Retrieve the chaos scenario active in the current asynchronous request context."""
    return _request_chaos_scenario.get()


class FaultInjector:
    """Thread-safe and context-aware fault injector for Japanese Banking Chaos Engineering."""

    @classmethod
    def enable_global_scenario(cls, scenario_name: str, config: Optional[Dict[str, Any]] = None):
        """Enable a global chaos scenario across all threads/requests."""
        if not is_chaos_enabled():
            return
        _global_active_scenarios[scenario_name] = config or {}

    @classmethod
    def disable_global_scenario(cls, scenario_name: str):
        """Disable a global chaos scenario."""
        _global_active_scenarios.pop(scenario_name, None)

    @classmethod
    def reset_all_faults(cls):
        """Reset all active global and request-scoped chaos faults."""
        _global_active_scenarios.clear()
        _request_chaos_scenario.set(None)

    @classmethod
    def is_scenario_active(cls, scenario_name: str) -> bool:
        """Check if a specific scenario is active globally or in the current request context."""
        if not is_chaos_enabled():
            return False
        # 1. Check request-scoped header context
        req_scenario = get_request_chaos_scenario()
        if req_scenario and req_scenario.upper() == scenario_name.upper():
            return True
        # 2. Check global registry
        return scenario_name.upper() in [k.upper() for k in _global_active_scenarios.keys()]

    @classmethod
    def get_scenario_config(cls, scenario_name: str) -> Dict[str, Any]:
        """Get configuration parameters for an active scenario."""
        for k, v in _global_active_scenarios.items():
            if k.upper() == scenario_name.upper():
                return v
        return {}

    @classmethod
    def inject_latency(cls, scenario_name: str, duration_seconds: float, jitter: float = 0.0):
        """Inject an artificial sleep/latency if the scenario is active."""
        if cls.is_scenario_active(scenario_name):
            effective_delay = duration_seconds
            if jitter > 0:
                effective_delay += random.uniform(-jitter, jitter)
            effective_delay = max(0.0, effective_delay)
            time.sleep(effective_delay)
            return True
        return False

    @classmethod
    def inject_exception(cls, scenario_name: str, exception_to_raise: Exception):
        """Raise an exception immediately if the scenario is active."""
        if cls.is_scenario_active(scenario_name):
            raise exception_to_raise

    @classmethod
    def maybe_corrupt_data(cls, scenario_name: str, original_data: Any, corruptor: Callable[[Any], Any]) -> Any:
        """Apply a data corruptor function if the scenario is active."""
        if cls.is_scenario_active(scenario_name):
            return corruptor(original_data)
        return original_data
