"""
Semantic Vector Search Engine using Dense Embeddings and Cosine Similarity.
Captures conceptual intent and semantic relevance even when lexical overlap is low.
"""

import json
import numpy as np
from app.models.db import query_db, is_postgres
from mining.embeddings import generate_embedding, cosine_similarity

class SemanticVectorSearcher:
    def __init__(self):
        self.doc_ids = []
        self.embedding_matrix = None
        self._load_embeddings()

    def _load_embeddings(self):
        """Pre-load paper embeddings into in-memory normalized matrix for fast dot-product."""
        rows = query_db("SELECT id, embedding_json FROM papers WHERE embedding_json IS NOT NULL")
        self.doc_ids = []
        vecs = []

        for r in rows:
            try:
                emb = json.loads(r["embedding_json"])
                if len(emb) == 384:
                    self.doc_ids.append(r["id"])
                    vecs.append(emb)
            except Exception:
                continue

        if vecs:
            mat = np.array(vecs, dtype=np.float32)
            # Normalize row vectors to unit length
            norms = np.linalg.norm(mat, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            self.embedding_matrix = mat / norms
        else:
            self.embedding_matrix = np.empty((0, 384), dtype=np.float32)

    def search(self, query_text, top_k=50):
        """
        Embed query string and compute cosine similarity against paper matrix.
        Returns list of (doc_id, score) sorted descending.
        """
        if self.embedding_matrix is None or len(self.doc_ids) == 0:
            self._load_embeddings()

        if len(self.doc_ids) == 0:
            return []

        q_vec = generate_embedding(query_text)
        q_arr = np.array(q_vec, dtype=np.float32)
        q_norm = np.linalg.norm(q_arr)
        if q_norm > 0:
            q_arr = q_arr / q_norm
        else:
            return []

        # Vectorized cosine similarity via matrix dot-product
        sims = np.dot(self.embedding_matrix, q_arr)
        
        # Top-K indices
        top_indices = np.argsort(-sims)[:top_k]
        results = []
        for idx in top_indices:
            score = float(sims[idx])
            if score > 0.10: # threshold noise
                results.append((self.doc_ids[idx], score))

        return results

_SEMANTIC_SEARCHER = None

def get_semantic_searcher():
    global _SEMANTIC_SEARCHER
    if _SEMANTIC_SEARCHER is None:
        _SEMANTIC_SEARCHER = SemanticVectorSearcher()
    return _SEMANTIC_SEARCHER

def search_papers_semantic(query_text, top_k=50):
    searcher = get_semantic_searcher()
    return searcher.search(query_text, top_k=top_k)
