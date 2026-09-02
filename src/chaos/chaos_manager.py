"""
Chaos Experiment Manager & Orchestrator
Coordinates chaos experiment execution, active scenarios, blast radius controls,
and generates FISC-compliant resilience verification reports.
"""

import datetime
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable

from .scenarios import ChaosScenario, SCENARIO_CATALOG, ChaosScenarioDefinition
from .fault_injector import FaultInjector
from .steady_state import SteadyStateEvaluator, SteadyStateReport


@dataclass
class ExperimentExecutionRecord:
    experiment_id: str
    scenario: str
    scenario_name_ja: str
    target_component: str
    started_at: str
    ended_at: Optional[str] = None
    duration_seconds: float = 0.0
    status: str = "RUNNING"  # RUNNING, PASSED, FAILED, STOPPED
    baseline_latency_ms: float = 0.0
    chaos_latency_ms: float = 0.0
    degradation_observed: bool = False
    steady_state_report: Optional[Dict[str, Any]] = None
    fisc_reference: str = ""
    error_message: Optional[str] = None


class ChaosManager:
    """Enterprise Chaos Engineering Orchestrator for Japanese Banking Systems."""

    def __init__(self):
        self.active_experiments: Dict[str, ExperimentExecutionRecord] = {}
        self.history: List[ExperimentExecutionRecord] = []

    def list_available_scenarios(self) -> List[Dict[str, Any]]:
        """List all cataloged chaos scenarios with metadata."""
        return [
            {
                "scenario_id": defn.scenario_id,
                "name_ja": defn.name_ja,
                "name_en": defn.name_en,
                "category": defn.category.value,
                "target_component": defn.target_component,
                "strategy": defn.strategy.value,
                "description": defn.description,
                "fisc_reference": defn.fisc_reference,
            }
            for defn in SCENARIO_CATALOG.values()
        ]

    def get_scenario_definition(self, scenario: ChaosScenario) -> Optional[ChaosScenarioDefinition]:
        """Get the specification for a scenario."""
        return SCENARIO_CATALOG.get(scenario)

    def start_experiment(
        self,
        scenario: ChaosScenario,
        config: Optional[Dict[str, Any]] = None
    ) -> ExperimentExecutionRecord:
        """Start a chaos experiment globally."""
        defn = SCENARIO_CATALOG.get(scenario)
        if not defn:
            raise ValueError(f"Unknown chaos scenario: {scenario}")

        exp_id = f"CHAOS-{int(time.time())}-{uuid.uuid4().hex[:6]}"
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

        record = ExperimentExecutionRecord(
            experiment_id=exp_id,
            scenario=defn.scenario_id,
            scenario_name_ja=defn.name_ja,
            target_component=defn.target_component,
            started_at=now_str,
            fisc_reference=defn.fisc_reference
        )

        FaultInjector.enable_global_scenario(defn.scenario_id, config or {})
        self.active_experiments[exp_id] = record
        return record

    def stop_experiment(self, experiment_id: str) -> Optional[ExperimentExecutionRecord]:
        """Stop an active chaos experiment and restore normal operations."""
        record = self.active_experiments.pop(experiment_id, None)
        if record:
            record.ended_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
            record.status = "STOPPED"
            FaultInjector.disable_global_scenario(record.scenario)
            self.history.append(record)
        return record

    def stop_all_experiments(self):
        """Emergency stop of all chaos experiments."""
        for exp_id in list(self.active_experiments.keys()):
            self.stop_experiment(exp_id)
        FaultInjector.reset_all_faults()

    def run_single_experiment(
        self,
        scenario: ChaosScenario,
        test_callable: Callable[[], Any],
        scenario_config: Optional[Dict[str, Any]] = None
    ) -> ExperimentExecutionRecord:
        """
        Execute a targeted chaos experiment with automated steady-state evaluation.
        1. Measure Baseline
        2. Inject Fault
        3. Execute test callable
        4. Validate Invariants
        5. Restore Normalcy
        """
        defn = SCENARIO_CATALOG.get(scenario)
        if not defn:
            raise ValueError(f"Unknown scenario: {scenario}")

        exp_id = f"CHAOS-RUN-{int(time.time())}-{uuid.uuid4().hex[:4]}"
        start_time = time.time()
        start_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

        record = ExperimentExecutionRecord(
            experiment_id=exp_id,
            scenario=defn.scenario_id,
            scenario_name_ja=defn.name_ja,
            target_component=defn.target_component,
            started_at=start_str,
            fisc_reference=defn.fisc_reference
        )

        # 1. Measure baseline
        try:
            b_start = time.time()
            _ = test_callable()
            record.baseline_latency_ms = round((time.time() - b_start) * 1000, 2)
        except Exception:
            record.baseline_latency_ms = 0.0

        # 2. Inject fault and execute
        FaultInjector.enable_global_scenario(defn.scenario_id, scenario_config or {})
        try:
            c_start = time.time()
            chaos_result = test_callable()
            record.chaos_latency_ms = round((time.time() - c_start) * 1000, 2)

            # 3. Evaluate steady-state invariants
            report = SteadyStateEvaluator.evaluate_response(
                response_data=chaos_result,
                latency_ms=record.chaos_latency_ms
            )
            record.steady_state_report = {
                "is_healthy": report.is_healthy,
                "passed_checks": report.passed_checks,
                "failed_checks": report.failed_checks,
                "results": [
                    {
                        "invariant": r.invariant_name,
                        "passed": r.passed,
                        "details": r.details,
                        "severity": r.severity
                    }
                    for r in report.results
                ]
            }

            # Check if degradation occurred as expected
            if defn.strategy.value == "GRACEFUL_DEGRADE":
                res_str = str(chaos_result)
                record.degradation_observed = any(
                    w in res_str for w in ["メンテナンス中", "DEGRADED", "縮退", "混雑", "一時停止"]
                )

            record.status = "PASSED" if report.is_healthy else "FAILED"

        except Exception as err:
            record.error_message = str(err)
            # If scenario expected fail-closed, check whether it raised appropriately
            if defn.strategy.value == "FAIL_CLOSED":
                record.status = "PASSED"
                record.degradation_observed = True
            else:
                record.status = "FAILED"

        finally:
            # 4. Clean up
            FaultInjector.disable_global_scenario(defn.scenario_id)
            record.ended_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
            record.duration_seconds = round(time.time() - start_time, 3)
            self.history.append(record)

        return record


# Global singleton instance
chaos_manager = ChaosManager()
