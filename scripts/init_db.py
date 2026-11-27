#!/usr/bin/env python3
"""
Database initialization script for Chanakya Research Commons.
Initializes tables, indexes, and loads initial department seed data.
"""

import sys
import json
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import Config
from app.models.db import is_postgres, execute_script, execute_db, query_db, get_connection

def init_database(drop_existing=False):
    """Initialize database tables and initial seed data."""
    print("=" * 60)
    print("Chanakya Research Commons - Database Initializer")
    print("=" * 60)

    is_pg = is_postgres()
    print(f"Target Database Engine: {'PostgreSQL + pgvector' if is_pg else 'Universal SQLite'}")

    schema_file = (
        PROJECT_ROOT / "database" / "schema" / ("postgres_schema.sql" if is_pg else "sqlite_schema.sql")
    )

    if not schema_file.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_file}")

    print(f"Applying schema from: {schema_file.name}")
    with open(schema_file, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    execute_script(schema_sql)
    print("Schema applied successfully.")

    # Seed initial departments
    departments_file = PROJECT_ROOT / "database" / "seeds" / "initial_departments.json"
    if departments_file.exists():
        with open(departments_file, "r", encoding="utf-8") as f:
            departments = json.load(f)

        existing_depts = query_db("SELECT code FROM departments")
        existing_codes = {d["code"] for d in existing_depts}

        inserted_count = 0
        for dept in departments:
            if dept["code"] not in existing_codes:
                execute_db(
                    """
                    INSERT INTO departments (code, name, description, faculty_count)
                    VALUES (?, ?, ?, ?)
                    """,
                    (dept["code"], dept["name"], dept["description"], dept.get("faculty_count", 0)),
                )
                inserted_count += 1

        print(f"Seeded {inserted_count} departments (Total: {len(existing_codes) + inserted_count}).")

    # Verify tables
    if is_pg:
        tables = query_db(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )
        table_names = [t["table_name"] for t in tables]
    else:
        tables = query_db("SELECT name FROM sqlite_master WHERE type='table'")
        table_names = [t["name"] for t in tables]

    print(f"Verified {len(table_names)} tables in database:")
    print(", ".join(sorted(table_names)))
    print("=" * 60)
    print("Database initialization complete.")
    print("=" * 60)

if __name__ == "__main__":
    init_database()
