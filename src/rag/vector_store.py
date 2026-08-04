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
        """Load FAQ items from JSON file."""
        if os.path.exists(self.faq_path):
            with open(self.faq_path, 'r', encoding='utf-8') as f:
                self.documents = json.load(f)

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
        if not self.documents:
            self.load_data()

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return self.documents[:top_k]

        scored_docs = []
        for doc in self.documents:
            doc_text = f"{doc.get('category', '')} {doc.get('question', '')} {doc.get('answer', '')}"
            doc_tokens = self._tokenize(doc_text)
            
            # Count term frequency overlap
            doc_token_counts = {}
            for t in doc_tokens:
                doc_token_counts[t] = doc_token_counts.get(t, 0) + 1
                
            score = 0
            for qt in query_tokens:
                if qt in doc_token_counts:
                    score += doc_token_counts[qt]

            # Normalize by document length
            norm_score = score / max(1, math.sqrt(len(doc_tokens)))
            
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
