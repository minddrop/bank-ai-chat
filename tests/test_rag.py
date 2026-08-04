"""
Unit Tests for Rakuten Bank FAQ RAG Vector Store
Verifies search accuracy, cosine relevance scoring, and document indexing.
"""

import os
import sys
import unittest

sys.path.append(os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "src")))

from rag.vector_store import VectorStore

class TestVectorStore(unittest.TestCase):

    def test_vector_store_search(self):
        store = VectorStore()
        results = store.search("他行への振込手数料はいくらですか？", top_k=3)
        
        self.assertGreater(len(results), 0)
        top_match = results[0]
        self.assertTrue("振込" in top_match["question"] or "手数料" in top_match["question"])
        self.assertGreater(top_match["relevance_score"], 0)

if __name__ == "__main__":
    unittest.main()
