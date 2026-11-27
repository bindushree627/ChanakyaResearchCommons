"""
RAG Passage Retriever for Research Assistant.
Splits research paper abstracts into granular sentence passages and performs
dense vector retrieval to find the most relevant academic passages for any query.
"""

import re
import json
import numpy as np
from app.models.db import query_db
from mining.embeddings import generate_embedding, cosine_similarity

def split_into_passages(text, max_sentences=2):
    """Splits an abstract into 2-sentence coherent academic passages."""
    if not text:
        return []
    # Split by period followed by space
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 15]
    passages = []
    for i in range(0, len(sentences), max_sentences):
        chunk = " ".join(sentences[i:i+max_sentences])
        if len(chunk) > 30:
            passages.append(chunk)
    return passages

def retrieve_candidate_passages(query_text, top_k=15):
    """
    Retrieves top-K candidate paper passages for a user query.
    Returns list of dicts with passage text, paper metadata, and similarity score.
    """
    if not query_text or not query_text.strip():
        return []

    q_vec = generate_embedding(query_text)
    q_arr = np.array(q_vec, dtype=np.float32)
    q_norm = np.linalg.norm(q_arr)
    if q_norm > 0:
        q_arr = q_arr / q_norm

    # 1. Fast semantic retrieval of top candidate papers (sub-millisecond dot-product)
    from mining.search.semantic_search import search_papers_semantic
    top_papers = search_papers_semantic(query_text, top_k=20)
    top_paper_ids = [pid for pid, _ in top_papers]

    if not top_paper_ids:
        return []

    from app.models.db import sql_group_concat
    authors_agg = sql_group_concat("author_name", ", ")
    placeholders = ",".join("?" for _ in top_paper_ids)
    papers = query_db(f"""
        SELECT p.id, p.title, p.abstract, p.publication_year, p.venue, p.doi, p.arxiv_id,
               t.name as topic_name,
               (SELECT {authors_agg} FROM paper_authors WHERE paper_id = p.id) as authors
        FROM papers p
        LEFT JOIN topics t ON p.primary_topic_id = t.id
        WHERE p.id IN ({placeholders}) AND p.abstract IS NOT NULL AND length(p.abstract) > 30
    """, top_paper_ids)

    candidates = []
    # Score passages of top candidate papers
    for p in papers:
        passages = split_into_passages(p["abstract"])
        for idx, pass_text in enumerate(passages):
            pass_vec = generate_embedding(pass_text)
            pass_arr = np.array(pass_vec, dtype=np.float32)
            p_norm = np.linalg.norm(pass_arr)
            if p_norm > 0:
                pass_arr = pass_arr / p_norm
            
            sim = float(np.dot(q_arr, pass_arr))
            candidates.append({
                "paper_id": p["id"],
                "paper_title": p["title"],
                "authors": p["authors"] or "Chanakya Researchers",
                "year": p["publication_year"],
                "venue": p["venue"],
                "topic": p["topic_name"],
                "passage_idx": idx,
                "passage_text": pass_text,
                "similarity": round(sim, 4)
            })

    candidates.sort(key=lambda x: x["similarity"], reverse=True)
    return candidates[:top_k]
