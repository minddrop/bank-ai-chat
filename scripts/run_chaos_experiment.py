#!/usr/bin/env python3
"""
CLI Tool: Japanese Major Bank AI Assistant - Chaos Engineering & Resilience Drill Runner
Compliant with FISC Safety Standards (第9版 コンティンジェンシープラン策定基準).

Usage:
  python3 scripts/run_chaos_experiment.py --list
  python3 scripts/run_chaos_experiment.py --scenario CORE_BANKING_TIMEOUT
  python3 scripts/run_chaos_experiment.py --scenario all
  python3 scripts/run_chaos_experiment.py --reset
"""

import argparse
import json
import os
import sys
import time
import requests

# Add src to python path
sys.path.append(os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "src")))

from chaos.scenarios import SCENARIO_CATALOG, ChaosScenario

DEFAULT_ENDPOINT = os.environ.get("BANK_API_ENDPOINT", "http://localhost:8000")


def print_banner():
    print("=" * 78)
    print(" 🏛️  MEGABANK JAPAN AI ASSISTANT - CHAOS ENGINEERING DRILL RUNNER")
    print("    FISC Safety Standards 第9版 & APPI Compliance Invariant Validator")
    print("=" * 78)


def list_scenarios():
    print_banner()
    print(f"\nCataloged Chaos Scenarios ({len(SCENARIO_CATALOG)} available):\n")
    print(f"{'Scenario ID':<26} | {'Strategy':<16} | {'FISC Reference'}")
    print("-" * 78)
    for s_enum, defn in SCENARIO_CATALOG.items():
        print(f"{defn.scenario_id:<26} | {defn.strategy.value:<16} | {defn.fisc_reference[:32]}")
    print()


def reset_faults(endpoint: str):
    url = f"{endpoint}/api/chaos/reset"
    try:
        res = requests.post(url, timeout=5)
        print(f"✅ Reset response from {url}: HTTP {res.status_code} - {res.json()}")
    except Exception as e:
        print(f"❌ Failed to reach {url}: {e}")


def run_experiment(scenario_name: str, endpoint: str) -> dict:
    url = f"{endpoint}/api/chaos/simulate"
    payload = {
        "scenario": scenario_name,
        "customer_id": "CUST-1001",
        "message": "現在の普通預金の残高および直近の取引明細を教えてください"
    }

    start = time.time()
    try:
        res = requests.post(url, json=payload, timeout=10)
        elapsed_ms = round((time.time() - start) * 1000, 2)
        if res.status_code == 200:
            data = res.json()
            data["http_status"] = res.status_code
            data["cli_elapsed_ms"] = elapsed_ms
            return data
        else:
            return {
                "scenario": scenario_name,
                "status": "FAILED",
                "http_status": res.status_code,
                "error_message": res.text,
                "cli_elapsed_ms": elapsed_ms
            }
    except Exception as e:
        return {
            "scenario": scenario_name,
            "status": "CONNECTION_ERROR",
            "error_message": str(e),
            "cli_elapsed_ms": round((time.time() - start) * 1000, 2)
        }


def print_result_table(results: list):
    print("\n" + "=" * 78)
    print(f"{'Scenario':<26} | {'Status':<8} | {'Latency':<9} | {'Degraded?':<9} | {'FISC Invariant'}")
    print("-" * 78)
    for r in results:
        scenario = r.get("scenario", "UNKNOWN")
        status = r.get("status", "UNKNOWN")
        lat = f"{r.get('chaos_latency_ms', r.get('cli_elapsed_ms', 0))}ms"
        degraded = "YES" if r.get("degradation_observed") else "NO"
        report = r.get("steady_state_report")
        if report:
            fisc_stat = "PASSED" if report.get("is_healthy") else "VIOLATION"
        else:
            fisc_stat = "N/A"

        status_color = "\033[92m" if status == "PASSED" else "\033[91m"
        reset_color = "\033[0m"

        print(f"{scenario:<26} | {status_color}{status:<8}{reset_color} | {lat:<9} | {degraded:<9} | {fisc_stat}")
    print("=" * 78 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Japanese Major Bank AI Chaos Engineering CLI")
    parser.add_argument("--list", action="store_true", help="List all available chaos scenarios")
    parser.add_argument("--scenario", type=str, help="Scenario to execute (or 'all')")
    parser.add_argument("--endpoint", type=str, default=DEFAULT_ENDPOINT, help="Bank API Base URL")
    parser.add_argument("--reset", action="store_true", help="Reset all active chaos faults")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")

    args = parser.parse_args()

    if args.list:
        list_scenarios()
        return

    if args.reset:
        reset_faults(args.endpoint)
        return

    if not args.scenario:
        parser.print_help()
        return

    print_banner()
    print(f"Connecting to Bank AI Assistant: {args.endpoint}\n")

    targets = []
    if args.scenario.lower() == "all":
        targets = [
            "CORE_BANKING_TIMEOUT",
            "CORE_BANKING_DB_CRASH",
            "BEDROCK_429_THROTTLING",
            "BEDROCK_OUTAGE_500",
            "RAG_INDEX_CORRUPT",
            "AUDIT_STORAGE_FAILURE"
        ]
    else:
        targets = [args.scenario.upper()]

    results = []
    for sc in targets:
        print(f"🚀 Injecting chaos scenario: {sc} ...", end="", flush=True)
        res = run_experiment(sc, args.endpoint)
        print(f" Done ({res.get('status')})")
        results.append(res)
        time.sleep(0.5)

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print_result_table(results)


if __name__ == "__main__":
    main()
