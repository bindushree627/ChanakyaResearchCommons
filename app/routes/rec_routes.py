"""
Personalized Research Recommendations Routes (Subsystem F6).
Integrates Content-Based Profile Matching, Collaborative Filtering (TruncatedSVD),
and Graph-Based Researcher Synergy.
"""

from flask import Blueprint, render_template, session, jsonify
from app.models.db import query_db
from app.models.entities import UserModel
from app.routes.auth_routes import login_required
from mining.recommendations.content_based import (
    recommend_papers_content_based,
    recommend_researchers,
    get_cold_start_recommendations
)
from mining.recommendations.collaborative import recommend_papers_collaborative

rec_bp = Blueprint("recommendations", __name__)

@rec_bp.route("/recommendations")
def recommendations_page():
    user_id = session.get("user_id")

    if user_id:
        user = UserModel.get_by_id(user_id)
        # 1. Content-based papers
        content_recs = recommend_papers_content_based(user_id, top_n=8)
        # 2. Collaborative filtering papers
        cf_recs = recommend_papers_collaborative(user_id, top_n=6)
        # 3. Recommended researchers
        researcher_recs = recommend_researchers(user_id, top_n=6)
        is_cold_start = len(UserModel.get_interests(user_id)) == 0 and UserModel.get_stats(user_id)["saves_count"] < 2
    else:
        # Default cold start / anonymous visitor
        user = None
        content_recs = get_cold_start_recommendations(None, top_n=8)
        cf_recs = []
        researcher_recs = []
        is_cold_start = True

    return render_template(
        "recommendations.html",
        content_recs=content_recs,
        cf_recs=cf_recs,
        researcher_recs=researcher_recs,
        is_cold_start=is_cold_start,
        user=user
    )

@rec_bp.route("/api/recommendations")
def api_recommendations():
    user_id = session.get("user_id")
    if not user_id:
        recs = get_cold_start_recommendations(None, top_n=10)
        return jsonify({"mode": "cold_start", "recommendations": recs})

    content_recs = recommend_papers_content_based(user_id, top_n=10)
    cf_recs = recommend_papers_collaborative(user_id, top_n=5)
    researchers = recommend_researchers(user_id, top_n=5)

    return jsonify({
        "mode": "personalized",
        "content_based": content_recs,
        "collaborative": cf_recs,
        "researchers": researchers
    })
