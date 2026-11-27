"""
Hybrid Search Ranker using Reciprocal Rank Fusion (RRF) and Normalized Score Blending.
Orchestrates 4-panel unified search results across:
1. External & Repository Scholarly Papers
2. University Library Saved Papers
3. University Members & Faculty
4. Community Research Posts & Discussions
"""

from collections import defaultdict
from app.models.db import query_db
from app.models.entities import PaperModel, UserModel
from mining.search.keyword_search import search_papers_keyword
from mining.search.semantic_search import search_papers_semantic

RRF_K = 60
WEIGHT_KEYWORD = 0.45
WEIGHT_SEMANTIC = 0.55

def reciprocal_rank_fusion(bm25_ranks, semantic_ranks, k=RRF_K):
    """
    RRF Formula: Score(d) = SUM( 1 / (k + rank_m(d)) )
    Measurable, scale-invariant ranking combining lexical precision with semantic recall.
    """
    rrf_scores = defaultdict(float)
    paper_ids = set(bm25_ranks.keys()) | set(semantic_ranks.keys())

    for pid in paper_ids:
        score = 0.0
        if pid in bm25_ranks:
            score += 1.0 / (k + bm25_ranks[pid])
        if pid in semantic_ranks:
            score += 1.0 / (k + semantic_ranks[pid])
        rrf_scores[pid] = score

    return sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

def execute_unified_search(query_text, filters=None, top_k=25, current_user_id=None):
    """
    Executes 4-panel search across all repository entities.
    filters: {'topic_id': int, 'year': int, 'department_id': int, 'content_type': str}
    """
    if not query_text or not query_text.strip():
        return {
            "query": query_text,
            "panel_papers": [],
            "panel_library": [],
            "panel_members": [],
            "panel_posts": [],
            "total_matches": 0
        }

    filters = filters or {}
    q = query_text.strip()

    # 1. Hybrid Paper Retrieval
    kw_results = search_papers_keyword(q, top_k=60)
    sem_results = search_papers_semantic(q, top_k=60)

    bm25_ranks = {doc_id: rank for rank, (doc_id, _) in enumerate(kw_results, start=1)}
    semantic_ranks = {doc_id: rank for rank, (doc_id, _) in enumerate(sem_results, start=1)}

    fused_ranking = reciprocal_rank_fusion(bm25_ranks, semantic_ranks)

    # Hydrate Paper Details
    ranked_paper_ids = [pid for pid, _ in fused_ranking]
    papers_list = []
    library_list = []

    for pid in ranked_paper_ids[:top_k * 2]:
        p = PaperModel.get_by_id(pid)
        if not p:
            continue

        # Apply Filters
        if filters.get("topic_id") and p.get("primary_topic_id") != int(filters["topic_id"]):
            continue
        if filters.get("year") and p.get("publication_year") != int(filters["year"]):
            continue

        # Check if saved in user's library
        is_saved = PaperModel.is_saved_by_user(current_user_id, pid) if current_user_id else False
        p["is_saved"] = is_saved

        # Calculate normalized display relevance (0 - 100%)
        rrf_val = dict(fused_ranking).get(pid, 0.0)
        p["relevance_score"] = min(round(rrf_val * 3100, 1), 99.8)

        # Panel 1: General scholarly papers
        papers_list.append(p)

        # Panel 2: Papers with library saves
        if p.get("save_count", 0) > 0 or is_saved:
            library_list.append(p)

    # 2. Panel 3: University Members Working in Related Areas
    # Matches user full_name, bio, department, or research interests
    from app.models.db import sql_group_concat
    interests_agg = sql_group_concat("topic_name", ", ")
    member_matches = query_db(
        f"""
        SELECT DISTINCT u.id, u.username, u.full_name, u.role, u.bio,
               d.name as department_name, d.code as department_code,
               (SELECT {interests_agg} FROM user_interests WHERE user_id = u.id) as interests
        FROM users u
        LEFT JOIN departments d ON u.department_id = d.id
        LEFT JOIN user_interests ui ON u.id = ui.user_id
        WHERE u.is_spam_flagged = 0 AND (
            LOWER(u.full_name) LIKE LOWER(?) OR
            LOWER(u.bio) LIKE LOWER(?) OR
            LOWER(ui.topic_name) LIKE LOWER(?) OR
            LOWER(d.name) LIKE LOWER(?)
        )
        LIMIT 10
        """,
        (f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%")
    )
    for m in member_matches:
        if current_user_id:
            m["is_following"] = UserModel.is_following(current_user_id, m["id"])
        else:
            m["is_following"] = False

    # 3. Panel 4: Research Posts and Community Discussions
    post_matches = query_db(
        """
        SELECT p.id, p.title, p.content, p.upvote_count, p.comment_count, p.created_at,
               u.full_name as author_name, u.username, t.name as topic_name
        FROM posts p
        JOIN users u ON p.user_id = u.id
        LEFT JOIN topics t ON p.primary_topic_id = t.id
        LEFT JOIN post_tags pt ON p.id = pt.post_id
        WHERE u.is_spam_flagged = 0 AND (
            LOWER(p.title) LIKE LOWER(?) OR
            LOWER(p.content) LIKE LOWER(?) OR
            LOWER(pt.tag_name) LIKE LOWER(?)
        )
        GROUP BY p.id
        ORDER BY p.upvote_count DESC, p.created_at DESC
        LIMIT 12
        """,
        (f"%{q}%", f"%{q}%", f"%{q}%")
    )

    return {
        "query": query_text,
        "panel_papers": papers_list[:top_k],
        "panel_library": library_list[:top_k],
        "panel_members": member_matches,
        "panel_posts": post_matches,
        "total_matches": len(papers_list) + len(member_matches) + len(post_matches)
    }
