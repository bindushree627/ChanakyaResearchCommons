"""
Database abstraction layer for Chanakya Research Commons.
Supports PostgreSQL (with pgvector) and universal SQLite (for portable local execution).
"""

import os
import json
import sqlite3
from pathlib import Path
from flask import g, current_app

def get_db_path():
    """Returns local SQLite database path."""
    if current_app:
        return Path(current_app.config.get("SQLITE_PATH", "data/chanakya_commons.db"))
    return Path("data/chanakya_commons.db")

def is_postgres():
    """Detect if PostgreSQL is configured."""
    if current_app:
        db_url = current_app.config.get("DATABASE_URL", "")
    else:
        db_url = os.getenv("DATABASE_URL", "")
    return db_url.startswith("postgresql://") or db_url.startswith("postgres://")


def _normalized_pg_url():
    db_url = current_app.config.get("DATABASE_URL") if current_app else os.getenv("DATABASE_URL", "")
    if db_url.startswith("postgres://"):
        return "postgresql://" + db_url[len("postgres://"):]
    return db_url


def sql_group_concat(expr, separator=", ", distinct=False):
    """Return dialect-compatible string aggregation SQL expression."""
    if is_postgres():
        dist = "DISTINCT " if distinct else ""
        return f"STRING_AGG({dist}CAST({expr} AS TEXT), '{separator}')"
    if distinct:
        return f"GROUP_CONCAT(DISTINCT {expr})"
    return f"GROUP_CONCAT({expr}, '{separator}')"


def sql_date_format(col, granularity="month"):
    """Return dialect-compatible date truncation/formatting SQL expression."""
    if is_postgres():
        fmt_map = {
            "day": "YYYY-MM-DD",
            "week": 'IYYY-"W"IW',
            "month": "YYYY-MM",
        }
        return f"TO_CHAR({col}, '{fmt_map.get(granularity, 'YYYY-MM')}')"
    fmt_map = {
        "day": "%Y-%m-%d",
        "week": "%Y-W%W",
        "month": "%Y-%m",
    }
    return f"strftime('{fmt_map.get(granularity, '%Y-%m')}', {col})"


def sql_date_cast(col):
    """Return dialect-compatible DATE cast expression."""
    if is_postgres():
        return f"({col})::date"
    return f"DATE({col})"


def get_connection():
    """Get active database connection for the current request context or CLI session."""
    if is_postgres():
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(_normalized_pg_url())
        conn.autocommit = False
        return conn
    else:
        # SQLite mode
        db_path = get_db_path()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

def get_db():
    """Flask request-context cached connection."""
    if "db" not in g:
        g.db = get_connection()
    return g.db

def close_db(e=None):
    """Close connection at end of request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    """Execute read query and return list of dictionaries."""
    conn = get_db() if current_app else get_connection()
    try:
        if is_postgres():
            import psycopg2.extras
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # Convert SQLite ? placeholders to %s for postgres if needed
                pg_query = query.replace("?", "%s")
                cur.execute(pg_query, args)
                rv = cur.fetchall()
                result = [dict(r) for r in rv]
                return (result[0] if result else None) if one else result
        else:
            cur = conn.cursor()
            cur.execute(query, args)
            rv = cur.fetchall()
            cur.close()
            result = [dict(r) for r in rv]
            return (result[0] if result else None) if one else result
    finally:
        if not current_app:
            conn.close()

def execute_db(query, args=(), commit=True):
    """Execute INSERT/UPDATE/DELETE query and return lastrowid / affected rows."""
    conn = get_db() if current_app else get_connection()
    try:
        if is_postgres():
            with conn.cursor() as cur:
                pg_query = query.replace("?", "%s")
                is_insert = pg_query.lstrip().upper().startswith("INSERT")
                if is_insert and "RETURNING" not in pg_query.upper():
                    pg_query_exec = pg_query.rstrip().rstrip(";") + " RETURNING id"
                else:
                    pg_query_exec = pg_query
                cur.execute(pg_query_exec, args)
                row_id = None
                if cur.description is not None:
                    fetched = cur.fetchone()
                    if fetched:
                        row_id = fetched[0]
                if commit:
                    conn.commit()
                return row_id if row_id is not None else cur.rowcount
        else:
            cur = conn.cursor()
            cur.execute(query, args)
            last_id = cur.lastrowid
            row_count = cur.rowcount
            if commit:
                conn.commit()
            cur.close()
            return last_id if last_id else row_count
    finally:
        if not current_app:
            conn.close()

def execute_script(script_text):
    """Execute raw SQL DDL script."""
    conn = get_db() if current_app else get_connection()
    try:
        if is_postgres():
            with conn.cursor() as cur:
                cur.execute(script_text)
            conn.commit()
        else:
            conn.executescript(script_text)
            conn.commit()
    finally:
        if not current_app:
            conn.close()
