"""
Institutional Analytics & Administrator Dashboard Routes (Subsystems F7 & F9).
Restricted to Administrators. Combines DuckDB Star Schema OLAP analytics
with live operational statistics and privacy-preserving record inspection.
"""

from flask import Blueprint, render_template, request, jsonify
from app.routes.auth_routes import admin_required
from app.models.db import query_db
from analytics.queries import (
    get_overall_summary,
    get_activity_trends_over_time,
    get_department_engagement,
    get_most_active_topics,
    get_most_saved_papers,
    get_cross_department_collaboration_network,
    drill_down_analytics
)
from analytics.admin_service import get_admin_overview_stats, inspect_records
from mining.trends.sliding_window import compute_sliding_window_trends
from mining.anomaly_detection.spam_detector import detect_spam_accounts, get_admin_monitoring_alerts

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/analytics")
@admin_required
def analytics_dashboard():
    filters = {
        "start_date": request.args.get("start_date", "").strip(),
        "end_date": request.args.get("end_date", "").strip(),
        "department_id": request.args.get("department_id", "").strip(),
        "role": request.args.get("role", "").strip(),
        "topic_id": request.args.get("topic_id", "").strip(),
        "event_type": request.args.get("event_type", "").strip(),
    }
    granularity = request.args.get("granularity", "month")

    # 1. Live operational statistics (respecting filters)
    admin_stats = get_admin_overview_stats(filters)

    # 2. DuckDB Star Schema OLAP metrics
    summary = get_overall_summary()
    trend_data = get_activity_trends_over_time(granularity="week" if granularity == "week" else "month")
    dept_stats = get_department_engagement()
    top_topics = get_most_active_topics(top_n=8)
    top_papers = get_most_saved_papers(top_n=6)
    collaboration_matrix = get_cross_department_collaboration_network()

    # 3. Sliding-window topic spike alerts & spam monitoring (F7)
    topic_spikes = compute_sliding_window_trends(window_days=14, baseline_days=45, z_threshold=1.5)
    spam_alerts = get_admin_monitoring_alerts()
    flagged_accounts = detect_spam_accounts()

    # Selectors for filters & drill-down
    departments = query_db("SELECT id, code, name FROM departments ORDER BY name ASC")
    all_topics = query_db("SELECT id, name FROM topics ORDER BY name ASC")

    return render_template(
        "analytics.html",
        admin_stats=admin_stats,
        filters=filters,
        granularity=granularity,
        summary=summary,
        trend_data=trend_data,
        dept_stats=dept_stats,
        top_topics=top_topics,
        top_papers=top_papers,
        collaboration_matrix=collaboration_matrix,
        topic_spikes=topic_spikes,
        spam_alerts=spam_alerts,
        flagged_accounts=flagged_accounts,
        departments=departments,
        all_topics=all_topics
    )


@analytics_bp.route("/analytics/records/<record_type>")
@admin_required
def admin_records_view(record_type):
    if record_type not in ("papers", "members", "posts", "comments", "replies", "saves"):
        record_type = "papers"

    q = request.args.get("q", "").strip()
    department_id = request.args.get("department_id", "").strip()
    role = request.args.get("role", "").strip()
    topic_id = request.args.get("topic_id", "").strip()
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()
    sort = request.args.get("sort", "id")
    order = request.args.get("order", "desc")
    page = request.args.get("page", 1, type=int)

    result = inspect_records(
        record_type=record_type,
        q=q,
        department_id=department_id or None,
        role=role or None,
        topic_id=topic_id or None,
        start_date=start_date or None,
        end_date=end_date or None,
        sort=sort,
        order=order,
        page=page,
        per_page=25
    )

    departments = query_db("SELECT id, code, name FROM departments ORDER BY name ASC")
    all_topics = query_db("SELECT id, name FROM topics ORDER BY name ASC")

    return render_template(
        "admin_records.html",
        result=result,
        record_type=record_type,
        q=q,
        department_id=department_id,
        role=role,
        topic_id=topic_id,
        start_date=start_date,
        end_date=end_date,
        sort=sort,
        order=order,
        departments=departments,
        all_topics=all_topics
    )


@analytics_bp.route("/api/analytics/records")
@admin_required
def api_admin_records():
    record_type = request.args.get("type", "papers")
    result = inspect_records(
        record_type=record_type,
        q=request.args.get("q", ""),
        department_id=request.args.get("department_id") or None,
        role=request.args.get("role") or None,
        topic_id=request.args.get("topic_id") or None,
        start_date=request.args.get("start_date") or None,
        end_date=request.args.get("end_date") or None,
        sort=request.args.get("sort", "id"),
        order=request.args.get("order", "desc"),
        page=request.args.get("page", 1, type=int),
        per_page=request.args.get("per_page", 25, type=int)
    )
    return jsonify(result)


@analytics_bp.route("/api/analytics/drilldown")
@admin_required
def api_drilldown():
    dept_code = request.args.get("department_code")
    topic_id = request.args.get("topic_id")
    user_id = request.args.get("user_id")

    res = drill_down_analytics(
        department_code=dept_code if dept_code else None,
        topic_id=int(topic_id) if topic_id else None,
        user_id=int(user_id) if user_id else None
    )
    return jsonify(res)
