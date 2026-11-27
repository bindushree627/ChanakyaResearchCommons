"""
DuckDB OLAP Analytics Service.
Executes high-performance analytical queries and dimensional drill-downs
across the Fact_Research_Activity star schema.
"""

from pathlib import Path
import threading
import duckdb
from app.config import Config

DUCKDB_PATH = Config.DUCKDB_PATH
_ETL_LOCK = threading.Lock()

def ensure_warehouse_ready():
    """Build DuckDB analytics warehouse automatically if missing (e.g. fresh production deploy)."""
    if not Path(DUCKDB_PATH).exists():
        with _ETL_LOCK:
            if not Path(DUCKDB_PATH).exists():
                from analytics.etl_warehouse import run_etl
                run_etl()

def get_duckdb_con():
    """Get read-only DuckDB connection, initializing warehouse if needed."""
    ensure_warehouse_ready()
    return duckdb.connect(str(DUCKDB_PATH), read_only=True)

def get_overall_summary():
    """High-level university KPI metrics."""
    con = get_duckdb_con()
    try:
        summary = con.execute("""
            SELECT
                COUNT(*) as total_events,
                COUNT(DISTINCT user_key) as active_members,
                COUNT(DISTINCT department_key) as active_departments,
                COUNT(DISTINCT paper_key) as papers_interacted,
                SUM(CASE WHEN event_type = 'save_paper' THEN 1 ELSE 0 END) as total_saves,
                SUM(CASE WHEN event_type = 'post' THEN 1 ELSE 0 END) as total_posts,
                SUM(CASE WHEN event_type = 'comment' THEN 1 ELSE 0 END) as total_comments,
                SUM(CASE WHEN event_type = 'search' THEN 1 ELSE 0 END) as total_searches
            FROM fact_research_activity
            WHERE user_key > 0
        """).df().to_dict(orient="records")[0]
        return summary
    finally:
        con.close()

def get_activity_trends_over_time(granularity="month"):
    """
    Time-series trend aggregation.
    granularity: 'month' or 'week'
    """
    con = get_duckdb_con()
    try:
        if granularity == "week":
            df = con.execute("""
                SELECT
                    t.year,
                    t.week_of_year,
                    COUNT(*) as event_count,
                    SUM(f.event_weight) as weighted_score
                FROM fact_research_activity f
                JOIN dim_time t ON f.date_key = t.date_key
                GROUP BY t.year, t.week_of_year
                ORDER BY t.year ASC, t.week_of_year ASC
            """).df()
            labels = [f"W{int(r.week_of_year)} ({int(r.year)})" for _, r in df.iterrows()]
        else:
            df = con.execute("""
                SELECT
                    t.year,
                    t.month,
                    t.month_name,
                    COUNT(*) as event_count,
                    SUM(f.event_weight) as weighted_score
                FROM fact_research_activity f
                JOIN dim_time t ON f.date_key = t.date_key
                GROUP BY t.year, t.month, t.month_name
                ORDER BY t.year ASC, t.month ASC
            """).df()
            labels = [f"{r.month_name[:3]} {int(r.year)}" for _, r in df.iterrows()]

        return {
            "labels": labels,
            "counts": df["event_count"].tolist(),
            "scores": [round(s, 1) for s in df["weighted_score"].tolist()]
        }
    finally:
        con.close()

def get_department_engagement():
    """Department activity distribution."""
    con = get_duckdb_con()
    try:
        df = con.execute("""
            SELECT
                d.department_code,
                d.department_name,
                COUNT(f.activity_key) as total_activity,
                SUM(CASE WHEN f.event_type = 'save_paper' THEN 1 ELSE 0 END) as paper_saves,
                SUM(CASE WHEN f.event_type = 'post' THEN 1 ELSE 0 END) as posts_count,
                COUNT(DISTINCT f.user_key) as active_researchers
            FROM fact_research_activity f
            JOIN dim_department d ON f.department_key = d.department_key
            GROUP BY d.department_code, d.department_name
            ORDER BY total_activity DESC
        """).df()
        return df.to_dict(orient="records")
    finally:
        con.close()

def get_most_active_topics(top_n=10):
    """Most active research areas."""
    con = get_duckdb_con()
    try:
        df = con.execute(f"""
            SELECT
                t.topic_name,
                t.topic_domain,
                COUNT(f.activity_key) as interaction_count,
                COUNT(DISTINCT f.user_key) as distinct_researchers
            FROM fact_research_activity f
            JOIN dim_topic t ON f.topic_key = t.topic_key
            WHERE f.topic_key > 0
            GROUP BY t.topic_name, t.topic_domain
            ORDER BY interaction_count DESC
            LIMIT {top_n}
        """).df()
        return df.to_dict(orient="records")
    finally:
        con.close()

def get_most_saved_papers(top_n=10):
    """Most saved research papers."""
    con = get_duckdb_con()
    try:
        df = con.execute(f"""
            SELECT
                p.paper_id,
                p.title,
                p.publication_year,
                p.venue,
                p.citation_tier,
                COUNT(f.activity_key) as save_count
            FROM fact_research_activity f
            JOIN dim_paper p ON f.paper_key = p.paper_key
            WHERE f.event_type = 'save_paper' AND f.paper_key > 0
            GROUP BY p.paper_id, p.title, p.publication_year, p.venue, p.citation_tier
            ORDER BY save_count DESC
            LIMIT {top_n}
        """).df()
        return df.to_dict(orient="records")
    finally:
        con.close()

def get_cross_department_collaboration_network():
    """
    Computes cross-department interaction matrix for NetworkX / heatmaps.
    Identifies multidisciplinary intersections.
    """
    con = get_duckdb_con()
    try:
        # Cross-department co-saving patterns on same papers
        df = con.execute("""
            WITH PaperDepts AS (
                SELECT DISTINCT f.paper_key, d.department_code
                FROM fact_research_activity f
                JOIN dim_department d ON f.department_key = d.department_key
                WHERE f.paper_key > 0 AND f.event_type = 'save_paper'
            )
            SELECT
                p1.department_code as dept_a,
                p2.department_code as dept_b,
                COUNT(DISTINCT p1.paper_key) as shared_papers
            FROM PaperDepts p1
            JOIN PaperDepts p2 ON p1.paper_key = p2.paper_key AND p1.department_code < p2.department_code
            GROUP BY p1.department_code, p2.department_code
            ORDER BY shared_papers DESC
        """).df()
        return df.to_dict(orient="records")
    finally:
        con.close()

def drill_down_analytics(department_code=None, topic_id=None, user_id=None):
    """
    Dimensional drill-down:
    University -> Department -> Topic -> Member.
    """
    con = get_duckdb_con()
    try:
        if user_id:
            # Member level details
            res = con.execute(f"""
                SELECT
                    u.username,
                    u.full_name,
                    u.role,
                    d.department_name,
                    COUNT(f.activity_key) as member_events,
                    SUM(CASE WHEN f.event_type = 'save_paper' THEN 1 ELSE 0 END) as saves,
                    SUM(CASE WHEN f.event_type = 'post' THEN 1 ELSE 0 END) as posts
                FROM fact_research_activity f
                JOIN dim_user u ON f.user_key = u.user_key
                JOIN dim_department d ON f.department_key = d.department_key
                WHERE u.user_id = {int(user_id)}
                GROUP BY u.username, u.full_name, u.role, d.department_name
            """).df().to_dict(orient="records")
            return {"level": "member", "data": res[0] if res else None}

        elif topic_id:
            # Topic level details
            res = con.execute(f"""
                SELECT
                    t.topic_name,
                    u.username,
                    u.full_name,
                    d.department_code,
                    COUNT(f.activity_key) as interactions
                FROM fact_research_activity f
                JOIN dim_topic t ON f.topic_key = t.topic_key
                JOIN dim_user u ON f.user_key = u.user_key
                JOIN dim_department d ON f.department_key = d.department_key
                WHERE t.topic_id = {int(topic_id)}
                GROUP BY t.topic_name, u.username, u.full_name, d.department_code
                ORDER BY interactions DESC
                LIMIT 15
            """).df().to_dict(orient="records")
            return {"level": "topic", "data": res}

        elif department_code:
            # Department level details
            res = con.execute(f"""
                SELECT
                    d.department_name,
                    t.topic_id,
                    t.topic_name,
                    COUNT(f.activity_key) as topic_activity
                FROM fact_research_activity f
                JOIN dim_department d ON f.department_key = d.department_key
                JOIN dim_topic t ON f.topic_key = t.topic_key
                WHERE d.department_code = '{department_code}' AND f.topic_key > 0
                GROUP BY d.department_name, t.topic_id, t.topic_name
                ORDER BY topic_activity DESC
                LIMIT 10
            """).df().to_dict(orient="records")
            return {"level": "department", "data": res}

        else:
            # University Level
            return {"level": "university", "data": get_overall_summary()}
    finally:
        con.close()
