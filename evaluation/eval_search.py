"""
Unified Search Evaluation Suite: Keyword (BM25) vs Semantic vs Hybrid (RRF).
Computes: Precision@5, Precision@10, Recall@10, and nDCG@10 across standard test queries.
"""

import math
import json
from pathlib import Path
import numpy as np

from app.config import Config
from app.models.db import query_db
from mining.search.keyword_search import search_papers_keyword
from mining.search.semantic_search import search_papers_semantic
from mining.search.hybrid_ranker import reciprocal_rank_fusion

BENCHMARK_FILE = Config.SYNTHETIC_DATA_DIR / "ground_truth_search_queries.json"

def dcg_at_k(relevance_scores, k=10):
    """Discounted Cumulative Gain at rank K."""
    dcg = 0.0
    for i, rel in enumerate(relevance_scores[:k], start=1):
        dcg += (2**rel - 1) / math.log2(i + 1)
    return dcg

def ndcg_at_k(retrieved_pids, relevant_pids, k=10):
    """Normalized Discounted Cumulative Gain at rank K."""
    rel_scores = [1 if pid in relevant_pids else 0 for pid in retrieved_pids[:k]]
    actual_dcg = dcg_at_k(rel_scores, k=k)
    
    # Ideal DCG (all 1s up to min(k, len(relevant_pids)))
    ideal_scores = [1] * min(k, len(relevant_pids)) + [0] * max(0, k - len(relevant_pids))
    idcg = dcg_at_k(ideal_scores, k=k)
    return (actual_dcg / idcg) if idcg > 0 else 0.0

def evaluate_search():
    print("=" * 60)
    print("Evaluating Unified Search: BM25 vs Semantic vs Hybrid (RRF)")
    print("=" * 60)

    if not BENCHMARK_FILE.exists():
        raise FileNotFoundError(f"Search benchmark query file not found: {BENCHMARK_FILE}")

    with open(BENCHMARK_FILE, "r", encoding="utf-8") as f:
        test_queries = json.load(f)

    # Pre-map topic names to paper IDs for ground-truth relevance
    topic_paper_map = {}
    for q in test_queries:
        topic_name = q["relevant_topic"]
        if topic_name not in topic_paper_map:
            pids = [r["id"] for r in query_db(
                "SELECT p.id FROM papers p JOIN topics t ON p.primary_topic_id = t.id WHERE t.name = ?",
                (topic_name,)
            )]
            topic_paper_map[topic_name] = set(pids)

    metrics = {
        "BM25_Keyword": {"P@5": [], "P@10": [], "R@10": [], "nDCG@10": []},
        "Semantic_Dense": {"P@5": [], "P@10": [], "R@10": [], "nDCG@10": []},
        "Hybrid_RRF": {"P@5": [], "P@10": [], "R@10": [], "nDCG@10": []}
    }

    for item in test_queries:
        q_text = item["query"]
        relevant_pids = topic_paper_map[item["relevant_topic"]]
        if not relevant_pids:
            continue

        # 1. BM25 Keyword
        kw_ranked = [doc_id for doc_id, _ in search_papers_keyword(q_text, top_k=20)]
        # 2. Semantic
        sem_ranked = [doc_id for doc_id, _ in search_papers_semantic(q_text, top_k=20)]
        # 3. Hybrid
        kw_ranks = {pid: r for r, pid in enumerate(kw_ranked, 1)}
        sem_ranks = {pid: r for r, pid in enumerate(sem_ranked, 1)}
        hybrid_ranked = [pid for pid, _ in reciprocal_rank_fusion(kw_ranks, sem_ranks, k=60)]

        for model_name, retrieved in [("BM25_Keyword", kw_ranked), ("Semantic_Dense", sem_ranked), ("Hybrid_RRF", hybrid_ranked)]:
            p5 = len([pid for pid in retrieved[:5] if pid in relevant_pids]) / 5.0
            p10 = len([pid for pid in retrieved[:10] if pid in relevant_pids]) / 10.0
            r10 = len([pid for pid in retrieved[:10] if pid in relevant_pids]) / max(len(relevant_pids), 1)
            ndcg = ndcg_at_k(retrieved, relevant_pids, k=10)

            metrics[model_name]["P@5"].append(p5)
            metrics[model_name]["P@10"].append(p10)
            metrics[model_name]["R@10"].append(r10)
            metrics[model_name]["nDCG@10"].append(ndcg)

    results = {}
    for model, vals in metrics.items():
        results[model] = {
            "Precision@5": round(float(np.mean(vals["P@5"])), 4),
            "Precision@10": round(float(np.mean(vals["P@10"])), 4),
            "Recall@10": round(float(np.mean(vals["R@10"])), 4),
            "nDCG@10": round(float(np.mean(vals["nDCG@10"])), 4)
        }
        print(f"[{model}] P@5: {results[model]['Precision@5']:.4f} | P@10: {results[model]['Precision@10']:.4f} | R@10: {results[model]['Recall@10']:.4f} | nDCG@10: {results[model]['nDCG@10']:.4f}")

    return results

if __name__ == "__main__":
    evaluate_search()
