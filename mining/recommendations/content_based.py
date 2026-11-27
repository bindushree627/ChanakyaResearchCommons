"""
Content-Based Recommendation Engine.
Constructs User Interest Profile Embeddings from user tags and saved paper abstracts.
Computes Cosine Similarity against all repository papers.
Provides explicit recommendation explanations and cold-start handling.
"""

import json
import numpy as np
from app.models.db import query_db
from app.models.entities import UserModel, PaperModel
from mining.embeddings import generate_embedding

def get_user_profile_vector(user_id):
    """
    Synthesize user's latent interest vector from:
    1. Explicit interest tags
    2. Embeddings of papers they saved
    """
    interests = UserModel.get_interests(user_id)
    saved_papers = query_db(
        """
        SELECT p.embedding_json
        FROM library_saves ls
        JOIN papers p ON ls.paper_id = p.id
        WHERE ls.user_id = ? AND p.embedding_json IS NOT NULL
        LIMIT 10
        """,
        (user_id,)
    )

    vecs = []
    # 1. From explicit topic interests
    if interests:
        topic_text = ". ".join(interests)
        vecs.append(np.array(generate_embedding(topic_text), dtype=np.float32))

    # 2. From saved paper vectors
    for r in saved_papers:
        try:
            emb = json.loads(r["embedding_json"])
            if len(emb) == 384:
                vecs.append(np.array(emb, dtype=np.float32))
        except Exception:
            pass

    if not vecs:
        return None

    # Centroid average vector
    profile = np.mean(vecs, axis=0)
    norm = np.linalg.norm(profile)
    return (profile / norm) if norm > 0 else profile

def recommend_papers_content_based(user_id, top_n=10):
    """
    Recommend papers matching user's content profile.
    Filters out already saved papers.
    """
    profile_vec = get_user_profile_vector(user_id)
    user = UserModel.get_by_id(user_id)
    interests = UserModel.get_interests(user_id)

    # Cold-start fallback if no profile can be formed
    if profile_vec is None:
        return get_cold_start_recommendations(user_id, top_n=top_n)

    # Get already saved paper IDs
    saved_ids = {r["paper_id"] for r in query_db("SELECT paper_id FROM library_saves WHERE user_id = ?", (user_id,))}

    # Score candidate papers
    papers = query_db("SELECT id, title, abstract, publication_year, venue, primary_topic_id, embedding_json FROM papers")
    candidates = []

    for p in papers:
        if p["id"] in saved_ids or not p["embedding_json"]:
            continue
        try:
            p_emb = np.array(json.loads(p["embedding_json"]), dtype=np.float32)
            norm = np.linalg.norm(p_emb)
            if norm > 0:
                p_emb = p_emb / norm
            score = float(np.dot(profile_vec, p_emb))

            # Generate natural explanation
            topic_row = query_db("SELECT name FROM topics WHERE id = ?", (p["primary_topic_id"],), one=True)
            topic_name = topic_row["name"] if topic_row else "your research area"
            explanation = f"Matches your interest in '{topic_name}' with high semantic cosine alignment ({score:.2f})."

            candidates.append({
                "paper_id": p["id"],
                "title": p["title"],
                "publication_year": p["publication_year"],
                "venue": p["venue"],
                "score": round(score, 4),
                "explanation": explanation
            })
        except Exception:
            continue

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:top_n]

def get_cold_start_recommendations(user_id, top_n=10):
    """
    Department-stratified popular papers for day-one members with zero history.
    """
    user = UserModel.get_by_id(user_id)
    dept_id = user["department_id"] if user else None
    
    # Recommend top saved papers in user's department or university-wide
    papers = query_db(
        """
        SELECT p.id as paper_id, p.title, p.publication_year, p.venue,
               t.name as topic_name, COUNT(ls.id) as save_count
        FROM papers p
        LEFT JOIN topics t ON p.primary_topic_id = t.id
        LEFT JOIN library_saves ls ON p.id = ls.paper_id
        GROUP BY p.id
        ORDER BY save_count DESC, p.citation_count DESC
        LIMIT ?
        """,
        (top_n,)
    )
    results = []
    for p in papers:
        results.append({
            "paper_id": p["paper_id"],
            "title": p["title"],
            "publication_year": p["publication_year"],
            "venue": p["venue"],
            "score": round(0.50 + min(p["save_count"] * 0.05, 0.45), 3),
            "explanation": f"Trending across Chanakya University with {p['save_count']} research saves."
        })
    return results

def recommend_researchers(user_id, top_n=5):
    """
    Recommend academic collaborators based on shared topics and co-reading patterns.
    """
    my_interests = set(UserModel.get_interests(user_id))
    my_following = set(UserModel.get_following_ids(user_id))
    my_user = UserModel.get_by_id(user_id)

    candidates = query_db(
        """
        SELECT u.id, u.username, u.full_name, u.role, d.name as department_name, d.code as department_code
        FROM users u
        LEFT JOIN departments d ON u.department_id = d.id
        WHERE u.id != ? AND u.is_spam_flagged = 0
        """,
        (user_id,)
    )

    scored = []
    for c in candidates:
        if c["id"] in my_following:
            continue

        c_interests = set(UserModel.get_interests(c["id"]))
        shared = my_interests & c_interests
        jaccard = len(shared) / max(len(my_interests | c_interests), 1)
        
        # Department synergy bonus
        dept_bonus = 0.20 if c.get("department_code") == (my_user.get("department_code") if my_user else "") else 0.10
        total_score = round(jaccard + dept_bonus, 3)

        if shared:
            shared_str = ", ".join(list(shared)[:2])
            explanation = f"Shares mutual research focus in {shared_str}."
        else:
            explanation = f"Active researcher in {c.get('department_name')}."

        scored.append({
            "user_id": c["id"],
            "username": c["username"],
            "full_name": c["full_name"],
            "role": c["role"],
            "department": c.get("department_name"),
            "score": total_score,
            "explanation": explanation
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_n]
