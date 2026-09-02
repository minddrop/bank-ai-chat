"""
FastAPI Middleware for Chaos Engineering Injection
Inspects HTTP request headers (X-Chaos-Scenario) and context parameters
to bind request-scoped faults during automated integration tests and GameDays.
"""

from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .fault_injector import (
    set_request_chaos_scenario,
    get_request_chaos_scenario,
    is_chaos_enabled
)
from .scenarios import SCENARIO_CATALOG, ChaosScenario


class ChaosMiddleware(BaseHTTPMiddleware):
    """
    Middleware intercepting requests to inject simulated chaos on a per-request basis.
    Activated when:
    - X-Chaos-Scenario header is present (e.g. X-Chaos-Scenario: CORE_BANKING_TIMEOUT)
    - CHAOS_ENGINEERING_ENABLED is true or running in non-production
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        chaos_header = request.headers.get("x-chaos-scenario") or request.query_params.get("chaos_scenario")

        if chaos_header and is_chaos_enabled():
            scenario_name = chaos_header.strip().upper()
            # Set request context
            set_request_chaos_scenario(scenario_name)
            try:
                response = await call_next(request)
                response.headers["X-Chaos-Injected"] = scenario_name
                return response
            finally:
                set_request_chaos_scenario(None)
        else:
            return await call_next(request)
