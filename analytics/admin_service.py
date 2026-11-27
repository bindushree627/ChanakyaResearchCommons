"""
Administrator Dashboard & Live Record Inspection Service (Subsystem F9).
Provides dynamically computed institutional statistics, filtered analytics,
and privacy-preserving operational record inspection for authorized Administrators.
"""

from app.models.db import query_db, sql_date_cast, sql_date_format, sql_group_concat


def _build_activity_filter(filters):
    """Build SQL WHERE clauses and params for filtered activity_events queries."""
    clauses = ["1=1"]
    params = []
    ae_date = sql_date_cast("ae.created_at")
    if filters.get("start_date"):
        clauses.append(f"{ae_date} >= ?")
        params.append(filters["start_date"])
    if filters.get("end_date"):
        clauses.append(f"{ae_date} <= ?")
        params.append(filters["end_date"])
    if filters.get("department_id"):
        clauses.append("u.department_id = ?")
        params.append(int(filters["department_id"]))
    if filters.get("role"):
        clauses.append("u.role = ?")
        params.append(filters["role"])
    if filters.get("event_type"):
        clauses.append("ae.event_type = ?")
        params.append(filters["event_type"])
    if filters.get("topic_id"):
        tid = int(filters["topic_id"])
        clauses.append("""(
            (ae.target_type = 'paper' AND ae.target_id IN (SELECT id FROM papers WHERE primary_topic_id = ?))
            OR (ae.target_type = 'post' AND ae.target_id IN (SELECT id FROM posts WHERE primary_topic_id = ?))
        )""")
        params.extend([tid, tid])
    return " AND ".join(clauses), params


def get_admin_overview_stats(filters=None):
    """Compute all live institutional statistics from the active database."""
    filters = filters or {}
    ae_where, ae_params = _build_activity_filter(filters)

    # 1. Research Data
    total_papers = query_db("SELECT COUNT(*) as c FROM papers", one=True)["c"]
    papers_by_source = query_db("""
        SELECT COALESCE(ps.source_name, 'Unspecified') as source_name,
               COUNT(DISTINCT p.id) as paper_count
        FROM papers p
        LEFT JOIN paper_sources ps ON p.id = ps.paper_id
        GROUP BY COALESCE(ps.source_name, 'Unspecified')
        ORDER BY paper_count DESC
    """)
    papers_by_topic = query_db("""
        SELECT COALESCE(t.name, 'Uncategorized') as topic_name, COUNT(p.id) as paper_count
        FROM papers p
        LEFT JOIN topics t ON p.primary_topic_id = t.id
        GROUP BY t.id, t.name
        ORDER BY paper_count DESC
        LIMIT 12
    """)
    papers_month = sql_date_format("created_at", "month")
    papers_over_time = query_db(f"""
        SELECT {papers_month} as period, COUNT(*) as count
        FROM papers
        WHERE created_at IS NOT NULL
        GROUP BY period
        ORDER BY period ASC
    """)
    papers_by_department = query_db("""
        SELECT d.code as department_code, d.name as department_name,
               COUNT(DISTINCT ls.paper_id) as saved_paper_count
        FROM departments d
        LEFT JOIN users u ON u.department_id = d.id
        LEFT JOIN library_saves ls ON ls.user_id = u.id
        GROUP BY d.id, d.code, d.name
        ORDER BY saved_paper_count DESC
    """)

    # 2. Members
    role_rows = query_db("SELECT role, COUNT(*) as c FROM users GROUP BY role")
    role_counts = {r["role"]: r["c"] for r in role_rows}
    total_members = sum(role_counts.values())
    members_by_department = query_db("""
        SELECT d.code as department_code, d.name as department_name,
               COUNT(u.id) as total_members,
               SUM(CASE WHEN u.role = 'Student' THEN 1 ELSE 0 END) as students,
               SUM(CASE WHEN u.role = 'Faculty' THEN 1 ELSE 0 END) as faculty,
               SUM(CASE WHEN u.role = 'Researcher' THEN 1 ELSE 0 END) as researchers,
               SUM(CASE WHEN u.role = 'Admin' THEN 1 ELSE 0 END) as admins
        FROM departments d
        LEFT JOIN users u ON u.department_id = d.id
        GROUP BY d.id, d.code, d.name
        ORDER BY total_members DESC
    """)
    reg_month = sql_date_format("created_at", "month")
    registrations_over_time = query_db(f"""
        SELECT {reg_month} as period, COUNT(*) as count
        FROM users
        WHERE created_at IS NOT NULL
        GROUP BY period
        ORDER BY period ASC
    """)

    # 3. Community Activity
    total_posts = query_db("SELECT COUNT(*) as c FROM posts", one=True)["c"]
    total_comments = query_db("SELECT COUNT(*) as c FROM post_comments WHERE parent_comment_id IS NULL", one=True)["c"]
    total_replies = query_db("SELECT COUNT(*) as c FROM post_comments WHERE parent_comment_id IS NOT NULL", one=True)["c"]
    posts_by_department = query_db("""
        SELECT COALESCE(d.code, 'N/A') as department_code,
               COALESCE(d.name, 'Unassigned') as department_name,
               COUNT(p.id) as post_count
        FROM posts p
        JOIN users u ON p.user_id = u.id
        LEFT JOIN departments d ON u.department_id = d.id
        GROUP BY d.id, d.code, d.name
        ORDER BY post_count DESC
    """)
    most_discussed_posts = query_db("""
        SELECT p.id, p.title, p.comment_count, p.upvote_count, p.created_at,
               u.full_name, u.username, d.code as department_code
        FROM posts p
        JOIN users u ON p.user_id = u.id
        LEFT JOIN departments d ON u.department_id = d.id
        ORDER BY p.comment_count DESC, p.upvote_count DESC
        LIMIT 8
    """)
    recent_posts = query_db("""
        SELECT p.id, p.title, p.comment_count, p.upvote_count, p.created_at,
               u.full_name, u.username, d.code as department_code
        FROM posts p
        JOIN users u ON p.user_id = u.id
        LEFT JOIN departments d ON u.department_id = d.id
        ORDER BY p.created_at DESC
        LIMIT 8
    """)

    # 4. Research Library
    total_saves = query_db("SELECT COUNT(*) as c FROM library_saves", one=True)["c"]
    total_collections = query_db("SELECT COUNT(*) as c FROM collections", one=True)["c"]
    saves_by_department = query_db("""
        SELECT COALESCE(d.code, 'N/A') as department_code,
               COALESCE(d.name, 'Unassigned') as department_name,
               COUNT(ls.id) as save_count
        FROM library_saves ls
        JOIN users u ON ls.user_id = u.id
        LEFT JOIN departments d ON u.department_id = d.id
        GROUP BY d.id, d.code, d.name
        ORDER BY save_count DESC
    """)
    most_saved_papers_live = query_db("""
        SELECT p.id as paper_id, p.title, p.publication_year, p.venue,
               COUNT(ls.id) as save_count
        FROM library_saves ls
        JOIN papers p ON ls.paper_id = p.id
        GROUP BY p.id, p.title, p.publication_year, p.venue
        ORDER BY save_count DESC
        LIMIT 8
    """)
    saves_month = sql_date_format("saved_at", "month")
    saves_over_time = query_db(f"""
        SELECT {saves_month} as period, COUNT(*) as count
        FROM library_saves
        WHERE saved_at IS NOT NULL
        GROUP BY period
        ORDER BY period ASC
    """)

    # 5. Filtered Platform Activity
    activity_totals = query_db(f"""
        SELECT
            COUNT(*) as total_events,
            SUM(CASE WHEN ae.event_type = 'search' THEN 1 ELSE 0 END) as total_searches,
            SUM(CASE WHEN ae.event_type = 'view_paper' THEN 1 ELSE 0 END) as total_views,
            SUM(CASE WHEN ae.event_type = 'save_paper' THEN 1 ELSE 0 END) as total_save_events,
            COUNT(DISTINCT ae.user_id) as active_members
        FROM activity_events ae
        LEFT JOIN users u ON ae.user_id = u.id
        WHERE {ae_where}
    """, ae_params, one=True)

    ae_day = sql_date_format("ae.created_at", "day")
    ae_week = sql_date_format("ae.created_at", "week")
    ae_month = sql_date_format("ae.created_at", "month")

    activity_by_day = query_db(f"""
        SELECT {ae_day} as period, COUNT(*) as count
        FROM activity_events ae
        LEFT JOIN users u ON ae.user_id = u.id
        WHERE {ae_where} AND ae.created_at IS NOT NULL
        GROUP BY period
        ORDER BY period DESC
        LIMIT 30
    """, ae_params)
    activity_by_day.reverse()

    activity_by_week = query_db(f"""
        SELECT {ae_week} as period, COUNT(*) as count
        FROM activity_events ae
        LEFT JOIN users u ON ae.user_id = u.id
        WHERE {ae_where} AND ae.created_at IS NOT NULL
        GROUP BY period
        ORDER BY period ASC
    """, ae_params)

    activity_by_month = query_db(f"""
        SELECT {ae_month} as period,
               COUNT(*) as count,
               COUNT(DISTINCT ae.user_id) as active_members
        FROM activity_events ae
        LEFT JOIN users u ON ae.user_id = u.id
        WHERE {ae_where} AND ae.created_at IS NOT NULL
        GROUP BY period
        ORDER BY period ASC
    """, ae_params)

    return {
        "research": {
            "total_papers": total_papers,
            "by_source": papers_by_source,
            "by_topic": papers_by_topic,
            "over_time": papers_over_time,
            "by_department": papers_by_department,
        },
        "members": {
            "total_members": total_members,
            "students": role_counts.get("Student", 0),
            "faculty": role_counts.get("Faculty", 0),
            "researchers": role_counts.get("Researcher", 0),
            "admins": role_counts.get("Admin", 0),
            "by_department": members_by_department,
            "registrations_over_time": registrations_over_time,
        },
        "community": {
            "total_posts": total_posts,
            "total_comments": total_comments,
            "total_replies": total_replies,
            "total_discussion_activity": total_posts + total_comments + total_replies,
            "posts_by_department": posts_by_department,
            "most_discussed_posts": most_discussed_posts,
            "recent_posts": recent_posts,
        },
        "library": {
            "total_saves": total_saves,
            "total_collections": total_collections,
            "saves_by_department": saves_by_department,
            "most_saved_papers": most_saved_papers_live,
            "saves_over_time": saves_over_time,
        },
        "activity": {
            "total_events": activity_totals["total_events"] or 0,
            "total_searches": activity_totals["total_searches"] or 0,
            "total_views": activity_totals["total_views"] or 0,
            "total_save_events": activity_totals["total_save_events"] or 0,
            "active_members": activity_totals["active_members"] or 0,
            "by_day": activity_by_day,
            "by_week": activity_by_week,
            "by_month": activity_by_month,
        },
    }


def inspect_records(record_type, q="", department_id=None, role=None, topic_id=None,
                    start_date=None, end_date=None, sort="id", order="desc", page=1, per_page=25):
    """
    Paginated, searchable, privacy-preserving inspection of underlying records.
    Excludes password_hash, tokens, private_notes, and private collection contents.
    """
    page = max(1, int(page or 1))
    per_page = min(100, max(5, int(per_page or 25)))
    offset = (page - 1) * per_page
    order_dir = "ASC" if str(order).lower() == "asc" else "DESC"
    q_like = f"%{q.strip()}%" if q and q.strip() else None

    clauses = ["1=1"]
    params = []

    if record_type == "papers":
        if q_like:
            clauses.append("(p.title LIKE ? OR p.venue LIKE ?)")
            params.extend([q_like, q_like])
        if topic_id:
            clauses.append("p.primary_topic_id = ?")
            params.append(int(topic_id))
        if start_date:
            clauses.append(f"{sql_date_cast('p.created_at')} >= ?")
            params.append(start_date)
        if end_date:
            clauses.append(f"{sql_date_cast('p.created_at')} <= ?")
            params.append(end_date)
        where_sql = " AND ".join(clauses)
        sort_col = {"id": "p.id", "title": "p.title", "year": "p.publication_year", "created_at": "p.created_at"}.get(sort, "p.id")

        sources_agg = sql_group_concat("ps.source_name", ",", distinct=True)
        authors_agg = sql_group_concat("pa.author_name", ", ")
        total = query_db(f"SELECT COUNT(*) as c FROM papers p WHERE {where_sql}", params, one=True)["c"]
        rows = query_db(f"""
            SELECT p.id, p.title, p.publication_year, p.venue, p.created_at,
                   COALESCE(t.name, 'Uncategorized') as topic_name,
                   (SELECT {sources_agg} FROM paper_sources ps WHERE ps.paper_id = p.id) as sources,
                   (SELECT {authors_agg} FROM (SELECT author_name FROM paper_authors WHERE paper_id = p.id ORDER BY author_order ASC LIMIT 3) pa) as authors,
                   (SELECT COUNT(*) FROM library_saves ls WHERE ls.paper_id = p.id) as save_count
            FROM papers p
            LEFT JOIN topics t ON p.primary_topic_id = t.id
            WHERE {where_sql}
            ORDER BY {sort_col} {order_dir}
            LIMIT ? OFFSET ?
        """, params + [per_page, offset])

    elif record_type == "members":
        if q_like:
            clauses.append("(u.username LIKE ? OR u.full_name LIKE ? OR u.email LIKE ?)")
            params.extend([q_like, q_like, q_like])
        if department_id:
            clauses.append("u.department_id = ?")
            params.append(int(department_id))
        if role:
            clauses.append("u.role = ?")
            params.append(role)
        if start_date:
            clauses.append(f"{sql_date_cast('u.created_at')} >= ?")
            params.append(start_date)
        if end_date:
            clauses.append(f"{sql_date_cast('u.created_at')} <= ?")
            params.append(end_date)
        where_sql = " AND ".join(clauses)
        sort_col = {"id": "u.id", "username": "u.username", "full_name": "u.full_name", "role": "u.role", "created_at": "u.created_at"}.get(sort, "u.id")

        total = query_db(f"SELECT COUNT(*) as c FROM users u WHERE {where_sql}", params, one=True)["c"]
        # Explicitly exclude password_hash and sensitive fields
        rows = query_db(f"""
            SELECT u.id, u.username, u.full_name, u.email, u.role, u.is_spam_flagged, u.created_at,
                   COALESCE(d.code, 'N/A') as department_code, COALESCE(d.name, 'Unassigned') as department_name
            FROM users u
            LEFT JOIN departments d ON u.department_id = d.id
            WHERE {where_sql}
            ORDER BY {sort_col} {order_dir}
            LIMIT ? OFFSET ?
        """, params + [per_page, offset])

    elif record_type == "posts":
        if q_like:
            clauses.append("(p.title LIKE ? OR p.content LIKE ? OR u.full_name LIKE ?)")
            params.extend([q_like, q_like, q_like])
        if department_id:
            clauses.append("u.department_id = ?")
            params.append(int(department_id))
        if role:
            clauses.append("u.role = ?")
            params.append(role)
        if topic_id:
            clauses.append("p.primary_topic_id = ?")
            params.append(int(topic_id))
        if start_date:
            clauses.append(f"{sql_date_cast('p.created_at')} >= ?")
            params.append(start_date)
        if end_date:
            clauses.append(f"{sql_date_cast('p.created_at')} <= ?")
            params.append(end_date)
        where_sql = " AND ".join(clauses)
        sort_col = {"id": "p.id", "title": "p.title", "comment_count": "p.comment_count", "created_at": "p.created_at"}.get(sort, "p.id")

        total = query_db(f"""
            SELECT COUNT(*) as c FROM posts p JOIN users u ON p.user_id = u.id WHERE {where_sql}
        """, params, one=True)["c"]
        rows = query_db(f"""
            SELECT p.id, p.title, p.comment_count, p.upvote_count, p.created_at,
                   u.username, u.full_name, u.role, COALESCE(d.code, 'N/A') as department_code,
                   COALESCE(t.name, 'General') as topic_name
            FROM posts p
            JOIN users u ON p.user_id = u.id
            LEFT JOIN departments d ON u.department_id = d.id
            LEFT JOIN topics t ON p.primary_topic_id = t.id
            WHERE {where_sql}
            ORDER BY {sort_col} {order_dir}
            LIMIT ? OFFSET ?
        """, params + [per_page, offset])

    elif record_type in ("comments", "replies"):
        if record_type == "comments":
            clauses.append("c.parent_comment_id IS NULL")
        else:
            clauses.append("c.parent_comment_id IS NOT NULL")
        if q_like:
            clauses.append("(c.content LIKE ? OR p.title LIKE ? OR u.full_name LIKE ?)")
            params.extend([q_like, q_like, q_like])
        if department_id:
            clauses.append("u.department_id = ?")
            params.append(int(department_id))
        if role:
            clauses.append("u.role = ?")
            params.append(role)
        if start_date:
            clauses.append(f"{sql_date_cast('c.created_at')} >= ?")
            params.append(start_date)
        if end_date:
            clauses.append(f"{sql_date_cast('c.created_at')} <= ?")
            params.append(end_date)
        where_sql = " AND ".join(clauses)
        sort_col = {"id": "c.id", "created_at": "c.created_at"}.get(sort, "c.id")

        total = query_db(f"""
            SELECT COUNT(*) as c
            FROM post_comments c
            JOIN posts p ON c.post_id = p.id
            JOIN users u ON c.user_id = u.id
            WHERE {where_sql}
        """, params, one=True)["c"]
        rows = query_db(f"""
            SELECT c.id, c.post_id, c.parent_comment_id, c.content, c.created_at,
                   p.title as post_title, u.username, u.full_name, u.role,
                   COALESCE(d.code, 'N/A') as department_code
            FROM post_comments c
            JOIN posts p ON c.post_id = p.id
            JOIN users u ON c.user_id = u.id
            LEFT JOIN departments d ON u.department_id = d.id
            WHERE {where_sql}
            ORDER BY {sort_col} {order_dir}
            LIMIT ? OFFSET ?
        """, params + [per_page, offset])

    elif record_type == "saves":
        if q_like:
            clauses.append("(p.title LIKE ? OR u.full_name LIKE ? OR u.username LIKE ?)")
            params.extend([q_like, q_like, q_like])
        if department_id:
            clauses.append("u.department_id = ?")
            params.append(int(department_id))
        if role:
            clauses.append("u.role = ?")
            params.append(role)
        if topic_id:
            clauses.append("p.primary_topic_id = ?")
            params.append(int(topic_id))
        if start_date:
            clauses.append(f"{sql_date_cast('ls.saved_at')} >= ?")
            params.append(start_date)
        if end_date:
            clauses.append(f"{sql_date_cast('ls.saved_at')} <= ?")
            params.append(end_date)
        where_sql = " AND ".join(clauses)
        sort_col = {"id": "ls.id", "saved_at": "ls.saved_at"}.get(sort, "ls.id")

        total = query_db(f"""
            SELECT COUNT(*) as c
            FROM library_saves ls
            JOIN papers p ON ls.paper_id = p.id
            JOIN users u ON ls.user_id = u.id
            WHERE {where_sql}
        """, params, one=True)["c"]
        # Explicitly exclude private_notes and private collection details
        rows = query_db(f"""
            SELECT ls.id, ls.paper_id, ls.saved_at,
                   p.title as paper_title, p.publication_year,
                   u.username, u.full_name, u.role,
                   COALESCE(d.code, 'N/A') as department_code
            FROM library_saves ls
            JOIN papers p ON ls.paper_id = p.id
            JOIN users u ON ls.user_id = u.id
            LEFT JOIN departments d ON u.department_id = d.id
            WHERE {where_sql}
            ORDER BY {sort_col} {order_dir}
            LIMIT ? OFFSET ?
        """, params + [per_page, offset])
    else:
        return {"record_type": record_type, "total": 0, "page": 1, "per_page": per_page, "total_pages": 1, "rows": []}

    total_pages = max(1, (total + per_page - 1) // per_page)
    return {
        "record_type": record_type,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "rows": rows,
    }
