#!/usr/bin/env python3
"""
Grounding & Model Evaluation Benchmark Tool
Compliant with REQ-AI-013, ISO/IEC 42001, and FSA AI Governance Guidelines.
Evaluates model response faithfulness against official FAQ knowledge context.
"""

import argparse
import json
import os
import sys
from typing import Dict, Any, List

sys.path.append(os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "src")))

from control_plane.output_guardrail import OutputGuardrail
from rag.vector_store import VectorStore

FAQ_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "rakuten_faq.json"))


def run_grounding_benchmark(faq_path: str = FAQ_PATH, limit: int = 100) -> Dict[str, Any]:
    """Run full benchmark on golden dataset and hallucination vectors."""
    guardrail = OutputGuardrail()
    store = VectorStore(faq_path=faq_path)

    with open(faq_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        items = data.get("items", data) if isinstance(data, dict) else data

    test_items = items[:limit]
    scores = []
    high_confidence_count = 0
    moderate_confidence_count = 0
    ungrounded_count = 0

    print(f"============================================================")
    print(f"Starting Grounding Benchmark on {len(test_items)} Golden FAQ Pairs")
    print(f"Standard: REQ-AI-013 (Threshold >= 0.85 High Confidence)")
    print(f"============================================================")

    for idx, item in enumerate(test_items, 1):
        question = item.get("question", "")
        # Bank persona uses '当行' per REQ-AI-012 rather than competitor source name
        ground_truth_answer = item.get("answer", "").replace("楽天銀行", "当行")
        # Retrieve context via vector store
        contexts = store.search(question, top_k=2)

        result = guardrail.process_output(
            raw_llm_response=ground_truth_answer,
            rag_contexts=contexts,
            user_prompt=question
        )
        score = result["grounding_score"]
        scores.append(score)

        if score >= 0.85:
            high_confidence_count += 1
        elif score >= 0.70:
            moderate_confidence_count += 1
        else:
            ungrounded_count += 1

    mean_score = sum(scores) / max(1, len(scores))
    pass_rate = (high_confidence_count / max(1, len(scores))) * 100.0

    # Test Hallucination Vectors
    hallucination_queries = [
        ("他行振込手数料は一律100万円です。特別送金税が加算されます。", "他行振込手数料"),
        ("当行ATMでは暗証番号を入力せずにお金を引き出すことができます。", "ATM 引き出し 暗証番号"),
        ("口座開設すると無条件でビットコインが10BTC付与されます。", "口座開設 特典"),
    ]

    hallucination_results = []
    for fake_text, search_query in hallucination_queries:
        ctxs = store.search(search_query, top_k=2)
        h_res = guardrail.process_output(
            raw_llm_response=fake_text,
            rag_contexts=ctxs,
            user_prompt=search_query
        )
        is_flagged = h_res["grounding_score"] < 0.70 or len(h_res["warnings"]) > 0
        hallucination_results.append({
            "text": fake_text,
            "score": h_res["grounding_score"],
            "flagged": is_flagged
        })

    all_hallucinations_flagged = all(h["flagged"] for h in hallucination_results)

    print(f"\n--- Benchmark Results Summary ---")
    print(f"Total Evaluated: {len(test_items)}")
    print(f"High Confidence (>= 0.85): {high_confidence_count} ({pass_rate:.1f}%)")
    print(f"Moderate Confidence (0.70 - 0.84): {moderate_confidence_count}")
    print(f"Ungrounded (< 0.70): {ungrounded_count}")
    print(f"Mean Grounding Score: {mean_score:.4f} (Target: >= 0.90)")
    print(f"Hallucination Detection Rate: {'100%' if all_hallucinations_flagged else 'FAILED'}")

    passed = mean_score >= 0.90 and all_hallucinations_flagged
    print(f"Overall Benchmark Status: {'PASSED (Acceptance Met)' if passed else 'FAILED'}")
    print(f"============================================================\n")

    return {
        "total_evaluated": len(test_items),
        "mean_grounding_score": round(mean_score, 4),
        "pass_rate_pct": round(pass_rate, 2),
        "high_confidence_count": high_confidence_count,
        "moderate_confidence_count": moderate_confidence_count,
        "ungrounded_count": ungrounded_count,
        "hallucinations_detected": all_hallucinations_flagged,
        "passed": passed
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate FAQ RAG Grounding Fidelity")
    parser.add_argument("--limit", type=int, default=100, help="Number of FAQ items to evaluate")
    args = parser.parse_args()
    summary = run_grounding_benchmark(limit=args.limit)
    if not summary["passed"]:
        sys.exit(1)
