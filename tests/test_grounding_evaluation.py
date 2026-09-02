"""
Unit & Golden Benchmark Tests for AI Grounding Evaluation
Verifies compliance with REQ-AI-013, ISO/IEC 42001, and ADR-0009.
Tests NLI semantic entailment, golden FAQ score distributions (>= 0.85),
and automated hallucination interception.
"""

import os
import sys
import unittest

sys.path.append(os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "src")))
sys.path.append(os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))

from control_plane.output_guardrail import OutputGuardrail
from rag.vector_store import VectorStore
from scripts.evaluate_grounding import run_grounding_benchmark


class TestGroundingEvaluation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.guardrail = OutputGuardrail()
        cls.vector_store = VectorStore()

    def test_high_confidence_grounding_score(self):
        """Valid response matching retrieved context must achieve score >= 0.85."""
        query = "借入の申し込みに手数料はかかりますか？"
        ctxs = self.vector_store.search(query, top_k=2)
        self.assertGreater(len(ctxs), 0)

        # Build response faithfully derived from FAQ context
        ans = ctxs[0].get("answer", "").replace("楽天銀行", "当行")
        res = self.guardrail.process_output(
            raw_llm_response=ans,
            rag_contexts=ctxs,
            user_prompt=query
        )
        self.assertGreaterEqual(res["grounding_score"], 0.85)
        self.assertFalse(res["financial_advice_blocked"])
        self.assertTrue(res["disclaimer_appended"])

    def test_hallucination_detection_and_suppression(self):
        """Fabricated responses with non-existent numbers and policies must trigger score reduction."""
        ctxs = self.vector_store.search("振込手数料", top_k=2)
        fake_response = "他行振込手数料は一律100万円です。また特別送金税が加算されます。"

        res = self.guardrail.process_output(
            raw_llm_response=fake_response,
            rag_contexts=ctxs,
            user_prompt="振込手数料"
        )
        # Score must be below threshold 0.70 or warning triggered
        self.assertLess(res["grounding_score"], 0.70)
        self.assertTrue(any("Low Grounding" in w for w in res["warnings"]))

    def test_prohibited_investment_advice_zero_score(self):
        """Prohibited financial advice must return 0.0 grounding score and advice block."""
        res = self.guardrail.process_output(
            raw_llm_response="この株を買えば絶対儲かるのでおすすめです。",
            rag_contexts=[]
        )
        self.assertEqual(res["grounding_score"], 0.0)
        self.assertTrue(res["financial_advice_blocked"])
        self.assertIn("回答制限", res["validated_response"])

    def test_golden_dataset_benchmark_passes_kpi_targets(self):
        """Golden dataset 50-pair evaluation must achieve mean score >= 0.90 and 100% hallucination catch."""
        benchmark_results = run_grounding_benchmark(limit=50)
        self.assertTrue(benchmark_results["passed"])
        self.assertGreaterEqual(benchmark_results["mean_grounding_score"], 0.90)
        self.assertTrue(benchmark_results["hallucinations_detected"])


if __name__ == "__main__":
    unittest.main()
