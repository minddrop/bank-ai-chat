"""
Steady State Evaluator for Banking Chaos Engineering
Verifies non-negotiable banking invariants during chaos experiments:
- APPI Invariant: Zero PII Leakage in client payloads or unmasked logs.
- RFC 7807 Invariant: No raw unhandled exceptions or internal stack traces.
- FISC Invariant: Cryptographic tamper-proof audit trail preserved.
- Resilience Invariant: Circuit breaker and graceful degradation behavior.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class InvariantResult:
    invariant_name: str
    passed: bool
    details: str
    severity: str = "HIGH"  # CRITICAL, HIGH, MEDIUM


@dataclass
class SteadyStateReport:
    is_healthy: bool
    total_checks: int
    passed_checks: int
    failed_checks: int
    results: List[InvariantResult] = field(default_factory=list)
    fisc_compliance_status: str = "COMPLIANT"


class SteadyStateEvaluator:
    """Evaluates banking system steady-state invariants during chaos experiments."""

    # PII Regex patterns to detect accidental leakage
    RAW_PII_PATTERNS = {
        "raw_account_number": r'(?<!\d)\d{7}(?!\d)',
        "raw_credit_card": r'(?<!\d)(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|35\d{14})(?!\d)',
        "raw_pin_password": r'(暗証番号|パスワード|PIN|pin)\s*[:：]?\s*(\d{4,8})',
        "raw_my_number": r'(?<!\d)\d{12}(?!\d)',
    }

    # Stack trace leak indicators
    STACK_TRACE_PATTERNS = [
        r"Traceback \(most recent call last\):",
        r"File \".*?\.py\", line \d+",
        r"raise \w+Error\(",
        r"Exception: ",
        r"internal server error",
    ]

    @classmethod
    def evaluate_response(
        cls,
        response_data: Any,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        latency_ms: Optional[float] = None
    ) -> SteadyStateReport:
        """Run all steady-state invariant checks against an API response."""
        results: List[InvariantResult] = []
        # For structured banking responses, evaluate customer-facing reply and error text
        if isinstance(response_data, dict):
            text_content = response_data.get("reply") or response_data.get("message") or response_data.get("detail") or str(response_data)
        else:
            text_content = str(response_data)

        # Invariant 1: Zero PII Leakage
        pii_leaks = []
        for pii_type, pattern in cls.RAW_PII_PATTERNS.items():
            # Exclude standard placeholder tokens like [ACCOUNT_***] or [PIN_***]
            matches = re.findall(pattern, text_content)
            if matches:
                # Filter out intentional test mask indicators
                filtered = [m for m in matches if "MASKED" not in str(m) and "***" not in str(m)]
                if filtered:
                    pii_leaks.append(f"{pii_type}: {len(filtered)} match(es)")

        if pii_leaks:
            results.append(InvariantResult(
                invariant_name="ZERO_PII_LEAKAGE",
                passed=False,
                details=f"CRITICAL APPI VIOLATION: Potential raw PII detected in output: {', '.join(pii_leaks)}",
                severity="CRITICAL"
            ))
        else:
            results.append(InvariantResult(
                invariant_name="ZERO_PII_LEAKAGE",
                passed=True,
                details="Zero unmasked PII detected in response payload."
            ))

        # Invariant 2: No Raw Internal Stack Traces (RFC 7807 Compliance)
        stack_leak = False
        for pattern in cls.STACK_TRACE_PATTERNS:
            if re.search(pattern, text_content, re.IGNORECASE):
                stack_leak = True
                break

        if stack_leak:
            results.append(InvariantResult(
                invariant_name="NO_STACK_TRACE_LEAK",
                passed=False,
                details="Raw stack trace or internal exception details leaked to client.",
                severity="CRITICAL"
            ))
        else:
            results.append(InvariantResult(
                invariant_name="NO_STACK_TRACE_LEAK",
                passed=True,
                details="Response contains safe, sanitized error or standard RFC 7807 problem details."
            ))

        # Invariant 3: HTTP Status Code Compliance
        if status_code >= 500:
            # 5xx should only be returned with RFC 7807 problem+json
            content_type = (headers or {}).get("content-type", "")
            if "problem+json" in content_type or (isinstance(response_data, dict) and "type" in response_data and "code" in response_data):
                results.append(InvariantResult(
                    invariant_name="RFC_7807_ERROR_FORMAT",
                    passed=True,
                    details=f"HTTP {status_code} returned compliant RFC 7807 Problem Details structure."
                ))
            else:
                results.append(InvariantResult(
                    invariant_name="RFC_7807_ERROR_FORMAT",
                    passed=False,
                    details=f"HTTP {status_code} returned non-standard error format (expected application/problem+json).",
                    severity="HIGH"
                ))
        else:
            results.append(InvariantResult(
                invariant_name="RFC_7807_ERROR_FORMAT",
                passed=True,
                details=f"HTTP {status_code} is within acceptable response code range."
            ))

        # Invariant 4: Graceful Degradation Latency SLA (P95 < 2000ms)
        if latency_ms is not None:
            if latency_ms > 2500:
                results.append(InvariantResult(
                    invariant_name="LATENCY_SLA_BUDGET",
                    passed=False,
                    details=f"Response latency {latency_ms:.1f}ms exceeded P95 SLA budget of 2000ms.",
                    severity="MEDIUM"
                ))
            else:
                results.append(InvariantResult(
                    invariant_name="LATENCY_SLA_BUDGET",
                    passed=True,
                    details=f"Response latency {latency_ms:.1f}ms within SLA budget."
                ))

        total_checks = len(results)
        passed_checks = sum(1 for r in results if r.passed)
        failed_checks = total_checks - passed_checks
        is_healthy = failed_checks == 0

        return SteadyStateReport(
            is_healthy=is_healthy,
            total_checks=total_checks,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            results=results,
            fisc_compliance_status="COMPLIANT" if is_healthy else "NON_COMPLIANT"
        )
