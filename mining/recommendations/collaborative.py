"""
Collaborative Filtering Recommendation Engine using TruncatedSVD Matrix Factorization.
Discovers latent community research interests across sparse user-paper save matrices.
"""

import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from app.models.db import query_db

class MatrixFactorizationCF:
    def __init__(self, n_components=12):
        self.n_components = n_components
        self.user_ids = []
        self.paper_ids = []
        self.user_idx_map = {}
        self.paper_idx_map = {}
        self.predicted_matrix = None
        self._fit()

    def _fit(self):
        """Fit TruncatedSVD on the User x Paper sparse interaction matrix."""
        saves = query_db("SELECT user_id, paper_id, rating FROM library_saves")
        if not saves:
            return

        df = pd.DataFrame(saves)
        # Implicit feedback rating: rating if present else 1.0
        df["score"] = df["rating"].fillna(1.0).astype(float)

        self.user_ids = sorted(df["user_id"].unique().tolist())
        self.paper_ids = sorted(df["paper_id"].unique().tolist())

        self.user_idx_map = {uid: i for i, uid in enumerate(self.user_ids)}
        self.paper_idx_map = {pid: j for j, pid in enumerate(self.paper_ids)}

        num_users = len(self.user_ids)
        num_papers = len(self.paper_ids)

        # Build dense/sparse interaction matrix
        R = np.zeros((num_users, num_papers), dtype=np.float32)
        for _, row in df.iterrows():
            u_idx = self.user_idx_map[row["user_id"]]
            p_idx = self.paper_idx_map[row["paper_id"]]
            R[u_idx, p_idx] = row["score"]

        # Decompose using TruncatedSVD
        k = min(self.n_components, min(num_users, num_papers) - 1)
        if k < 2:
            self.predicted_matrix = R
            return

        svd = TruncatedSVD(n_components=k, random_state=42)
        U_sigma = svd.fit_transform(R)
        Vt = svd.components_
        self.predicted_matrix = np.dot(U_sigma, Vt)

    def recommend(self, user_id, top_n=10):
        """Recommend unsaved papers with highest collaborative latent affinity."""
        if self.predicted_matrix is None or user_id not in self.user_idx_map:
            return []

        u_idx = self.user_idx_map[user_id]
        user_scores = self.predicted_matrix[u_idx]

        # Get user's already saved paper IDs
        saved_papers = {r["paper_id"] for r in query_db("SELECT paper_id FROM library_saves WHERE user_id = ?", (user_id,))}

        candidates = []
        for pid in self.paper_ids:
            if pid in saved_papers:
                continue
            p_idx = self.paper_idx_map[pid]
            score = float(user_scores[p_idx])
            if score > 0.05:
                candidates.append((pid, score))

        candidates.sort(key=lambda x: x[1], reverse=True)
        top_candidates = candidates[:top_n]

        results = []
        for pid, score in top_candidates:
            p = query_db("SELECT id as paper_id, title, publication_year, venue FROM papers WHERE id = ?", (pid,), one=True)
            if p:
                results.append({
                    "paper_id": p["paper_id"],
                    "title": p["title"],
                    "publication_year": p["publication_year"],
                    "venue": p["venue"],
                    "score": round(min(score, 1.0), 3),
                    "explanation": "Collaborative filtering: Researchers with reading habits similar to yours frequently saved this."
                })

        return results

_CF_RECOMMENDER = None

def get_cf_recommender():
    global _CF_RECOMMENDER
    if _CF_RECOMMENDER is None:
        _CF_RECOMMENDER = MatrixFactorizationCF()
    return _CF_RECOMMENDER

def recommend_papers_collaborative(user_id, top_n=10):
    recommender = get_cf_recommender()
    return recommender.recommend(user_id, top_n=top_n)
