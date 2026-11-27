"""
Passage Re-Ranker using Maximal Marginal Relevance (MMR).
Balances query relevance with information diversity to eliminate redundant passages.
"""

import numpy as np
from mining.embeddings import generate_embedding

def mmr_rerank_passages(query_text, candidate_passages, top_n=5, lambda_param=0.70):
    """
    Applies Maximal Marginal Relevance (MMR) to select top-N diverse passages.
    lambda_param: 1.0 = pure relevance, 0.0 = pure diversity. Standard = 0.70.
    """
    if not candidate_passages:
        return []

    if len(candidate_passages) <= top_n:
        return candidate_passages

    # Compute query vector
    q_vec = np.array(generate_embedding(query_text), dtype=np.float32)
    q_norm = np.linalg.norm(q_vec)
    if q_norm > 0:
        q_vec = q_vec / q_norm

    # Compute passage vectors
    p_vecs = []
    for c in candidate_passages:
        v = np.array(generate_embedding(c["passage_text"]), dtype=np.float32)
        v_norm = np.linalg.norm(v)
        p_vecs.append((v / v_norm) if v_norm > 0 else v)

    selected_indices = []
    candidate_indices = list(range(len(candidate_passages)))

    # Select first best match
    best_first = int(np.argmax([c["similarity"] for c in candidate_passages]))
    selected_indices.append(best_first)
    candidate_indices.remove(best_first)

    # Greedily pick remaining
    while len(selected_indices) < top_n and candidate_indices:
        best_idx = None
        best_score = -float("inf")

        for c_idx in candidate_indices:
            # Relevance to query
            sim_to_query = candidate_passages[c_idx]["similarity"]

            # Max similarity to already selected passages
            sim_to_selected = max([
                float(np.dot(p_vecs[c_idx], p_vecs[s_idx]))
                for s_idx in selected_indices
            ])

            # MMR Equation
            mmr_score = lambda_param * sim_to_query - (1.0 - lambda_param) * sim_to_selected
            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = c_idx

        if best_idx is not None:
            selected_indices.append(best_idx)
            candidate_indices.remove(best_idx)
        else:
            break

    ranked_results = [candidate_passages[i] for i in selected_indices]
    return ranked_results
