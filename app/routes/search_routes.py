"""
Unified 4-Panel Hybrid Search Routes (Subsystem F5).
Combines Okapi BM25 keyword matching with Dense Semantic Sentence Embeddings via Reciprocal Rank Fusion.
"""

from flask import Blueprint, render_template, request, session, jsonify
from app.models.db import query_db
from app.models.entities import ActivityLogger
from mining.search.hybrid_ranker import execute_unified_search

search_bp = Blueprint("search", __name__)

@search_bp.route("/explore")
def explore():
    query_text = request.args.get("q", "").strip()
    topic_id = request.args.get("topic_id")
    year = request.args.get("year")
    dept_id = request.args.get("dept_id")

    filters = {}
    if topic_id:
        filters["topic_id"] = int(topic_id)
    if year:
        filters["year"] = int(year)
    if dept_id:
        filters["department_id"] = int(dept_id)

    user_id = session.get("user_id")

    # If query present, execute search; otherwise default to recent research
    if query_text:
        results = execute_unified_search(
            query_text=query_text,
            filters=filters,
            top_k=25,
            current_user_id=user_id
        )
        if user_id:
            ActivityLogger.log(user_id, "search", "query", None, {"query": query_text})
    else:
        results = {
            "query": "",
            "panel_papers": [],
            "panel_library": [],
            "panel_members": [],
            "panel_posts": [],
            "total_matches": 0
        }

    topics = query_db("SELECT id, name FROM topics ORDER BY name ASC")
    departments = query_db("SELECT id, name, code FROM departments ORDER BY name ASC")
    years = [2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019]

    return render_template(
        "explore.html",
        results=results,
        query_text=query_text,
        topics=topics,
        departments=departments,
        years=years,
        selected_topic=topic_id,
        selected_year=year,
        selected_dept=dept_id
    )

@search_bp.route("/api/search")
def api_search():
    query_text = request.args.get("q", "").strip()
    topic_id = request.args.get("topic_id")
    year = request.args.get("year")
    user_id = session.get("user_id")

    filters = {}
    if topic_id:
        filters["topic_id"] = int(topic_id)
    if year:
        filters["year"] = int(year)

    results = execute_unified_search(
        query_text=query_text,
        filters=filters,
        top_k=20,
        current_user_id=user_id
    )
    return jsonify(results)
