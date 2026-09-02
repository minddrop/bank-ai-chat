"""
RAG Vector Store & FAQ Retrieval Module
Performs Japanese TF-IDF / Cosine Similarity Vector Search over Rakuten Bank FAQ knowledge base.
"""

import json
import math
import os
import re
from typing import Dict, Any, List

FAQ_FILE = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "rakuten_faq.json"))

class VectorStore:
    """In-memory Vector Search Store for Rakuten Bank FAQ dataset."""

    def __init__(self, faq_path: str = FAQ_FILE):
        self.faq_path = faq_path
        self.documents = []
        self.load_data()

    def load_data(self):
        """Load FAQ items from JSON file with metadata support and precompute token index."""
        if os.path.exists(self.faq_path):
            with open(self.faq_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict) and "items" in data:
                    self.documents = data["items"]
                    self.metadata = data.get("metadata", {})
                else:
                    self.documents = data
                    self.metadata = {}

        # Precompute token frequency index for fast retrieval
        self._doc_index = []
        for doc in self.documents:
            q_counts = {}
            for t in self._tokenize(doc.get('question', '')):
                q_counts[t] = q_counts.get(t, 0) + 1
            cat_counts = {}
            for t in self._tokenize(doc.get('category', '')):
                cat_counts[t] = cat_counts.get(t, 0) + 1
            ans_counts = {}
            for t in self._tokenize(doc.get('answer', '')):
                ans_counts[t] = ans_counts.get(t, 0) + 1

            total_tokens = len(q_counts) * 4 + len(cat_counts) * 2 + len(ans_counts) * 0.5
            norm_denom = max(1.0, math.sqrt(total_tokens))
            self._doc_index.append((doc, q_counts, cat_counts, ans_counts, norm_denom))

    def _tokenize(self, text: str) -> List[str]:
        """Simple Japanese character & word n-gram tokenizer."""
        clean = re.sub(r'[^\w\s]', '', text.lower())
        tokens = list(clean)
        # Add 2-gram / 3-gram tokens
        for i in range(len(clean) - 1):
            tokens.append(clean[i:i+2])
        for i in range(len(clean) - 2):
            tokens.append(clean[i:i+3])
        return tokens

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Search top K relevant FAQ entries using cosine TF-IDF similarity."""
        # Chaos Injection Hook
        try:
            from chaos.fault_injector import FaultInjector
            FaultInjector.inject_latency("RAG_OPENSEARCH_TIMEOUT", duration_seconds=1.5)
            if FaultInjector.is_scenario_active("RAG_INDEX_CORRUPT"):
                return []
        except ImportError:
            pass

        if not self.documents:
            self.load_data()

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return self.documents[:top_k]

        scored_docs = []
        for doc, q_counts, cat_counts, ans_counts, norm_denom in self._doc_index:
            score = 0
            for qt in query_tokens:
                if qt in q_counts:
                    score += q_counts[qt] * 4.0
                if qt in cat_counts:
                    score += cat_counts[qt] * 2.0
                if qt in ans_counts:
                    score += ans_counts[qt] * 0.5

            norm_score = score / norm_denom
            scored_docs.append((norm_score, doc))


        # Sort descending by similarity score
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        
        results = []
        for score, doc in scored_docs[:top_k]:
            results.append({
                **doc,
                "relevance_score": round(float(score), 4)
            })
            
        return results
