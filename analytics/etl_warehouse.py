"""
Data Warehouse ETL Pipeline: OLTP -> Dimensional Star Schema -> Parquet & DuckDB.
Creates Fact_Research_Activity and Dimension Tables for high-performance OLAP analytics.
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
import pandas as pd
import duckdb

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import Config
from app.models.db import query_db

WAREHOUSE_DIR = Config.WAREHOUSE_DIR
WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)
DUCKDB_PATH = Config.DUCKDB_PATH

def run_etl():
    print("=" * 60)
    print("Running Data Warehouse ETL Pipeline (OLTP -> Parquet -> DuckDB)")
    print("=" * 60)

    # 1. Extract OLTP Entities
    users = query_db("SELECT id as user_id, username, full_name, role, department_id, is_spam_flagged, created_at FROM users")
    departments = query_db("SELECT id as department_id, code as department_code, name as department_name, faculty_count FROM departments")
    topics = query_db("SELECT id as topic_id, name as topic_name, domain as topic_domain FROM topics")
    papers = query_db("SELECT id as paper_id, title, publication_year, venue, citation_count, primary_topic_id FROM papers")
    events = query_db("SELECT id as event_id, user_id, event_type, target_type, target_id, metadata_json, created_at FROM activity_events")

    df_users = pd.DataFrame(users)
    df_depts = pd.DataFrame(departments)
    df_topics = pd.DataFrame(topics)
    df_papers = pd.DataFrame(papers)
    df_events = pd.DataFrame(events)

    print(f"Extracted: {len(df_users)} users, {len(df_depts)} departments, {len(df_papers)} papers, {len(df_events)} events.")

    # 2. Build Dimensions
    # Dim_Department
    dim_department = df_depts.copy()
    dim_department["department_key"] = dim_department.index + 1

    # Dim_User
    dim_user = df_users.merge(df_depts[["department_id", "department_code", "department_name"]], on="department_id", how="left")
    dim_user["user_key"] = dim_user.index + 1
    dim_user["seniority_level"] = dim_user["role"].apply(lambda r: "Senior Academic" if r in ("Faculty", "Admin") else "Early Career")

    # Dim_Topic
    dim_topic = df_topics.copy()
    dim_topic["topic_key"] = dim_topic.index + 1

    # Dim_Paper
    dim_paper = df_papers.merge(df_topics[["topic_id", "topic_name", "topic_domain"]], left_on="primary_topic_id", right_on="topic_id", how="left")
    dim_paper["paper_key"] = dim_paper.index + 1
    dim_paper["citation_tier"] = pd.cut(
        dim_paper["citation_count"],
        bins=[-1, 5, 20, 50, 10000],
        labels=["Emerging (0-5)", "Established (6-20)", "Highly Cited (21-50)", "Seminal (>50)"]
    ).astype(str)

    # Dim_Time
    # Generate calendar dimension based on event dates
    df_events["created_at_dt"] = pd.to_datetime(df_events["created_at"])
    df_events["date_only"] = df_events["created_at_dt"].dt.date

    unique_dates = sorted(df_events["date_only"].unique())
    time_records = []
    for d in unique_dates:
        dt = pd.to_datetime(d)
        date_key = int(dt.strftime("%Y%m%d"))
        time_records.append({
            "date_key": date_key,
            "full_date": str(d),
            "day_of_week": dt.dayofweek,
            "day_name": dt.day_name(),
            "week_of_year": int(dt.isocalendar().week),
            "month": dt.month,
            "month_name": dt.month_name(),
            "quarter": dt.quarter,
            "year": dt.year,
            "is_academic_session": 1 if dt.month in (1, 2, 3, 4, 8, 9, 10, 11) else 0
        })
    dim_time = pd.DataFrame(time_records)

    # 3. Build Fact Table: Fact_Research_Activity
    df_events["date_key"] = df_events["created_at_dt"].dt.strftime("%Y%m%d").astype(int)
    
    # Map foreign keys
    fact = df_events.merge(dim_user[["user_id", "user_key", "department_id"]], on="user_id", how="left")
    fact = fact.merge(dim_department[["department_id", "department_key"]], on="department_id", how="left")
    
    # Map paper and topic keys
    # If target_type == 'paper', target_id is paper_id
    fact["paper_id"] = fact.apply(lambda row: row["target_id"] if row["target_type"] == "paper" else None, axis=1)
    fact = fact.merge(dim_paper[["paper_id", "paper_key", "primary_topic_id"]], on="paper_id", how="left")
    
    fact["topic_id"] = fact["primary_topic_id"]
    fact = fact.merge(dim_topic[["topic_id", "topic_key"]], on="topic_id", how="left")

    # Weights by event type
    event_weights = {
        "view_paper": 1.0,
        "search": 1.2,
        "upvote": 1.5,
        "comment": 3.0,
        "save_paper": 5.0,
        "post": 8.0
    }
    fact["event_weight"] = fact["event_type"].map(event_weights).fillna(1.0)
    fact["activity_key"] = fact.index + 1
    fact["count_event"] = 1

    fact_table = fact[[
        "activity_key", "date_key", "user_key", "department_key",
        "paper_key", "topic_key", "event_type", "count_event", "event_weight"
    ]].copy()

    # Fill NA keys with 0 (unknown dimension)
    fact_table["user_key"] = fact_table["user_key"].fillna(0).astype(int)
    fact_table["department_key"] = fact_table["department_key"].fillna(0).astype(int)
    fact_table["paper_key"] = fact_table["paper_key"].fillna(0).astype(int)
    fact_table["topic_key"] = fact_table["topic_key"].fillna(0).astype(int)

    # 4. Save to Parquet Columnar Storage
    print("Exporting dimensional tables to Apache Parquet...")
    dim_department.to_parquet(WAREHOUSE_DIR / "dim_department.parquet", index=False)
    dim_user.to_parquet(WAREHOUSE_DIR / "dim_user.parquet", index=False)
    dim_topic.to_parquet(WAREHOUSE_DIR / "dim_topic.parquet", index=False)
    dim_paper.to_parquet(WAREHOUSE_DIR / "dim_paper.parquet", index=False)
    dim_time.to_parquet(WAREHOUSE_DIR / "dim_time.parquet", index=False)
    fact_table.to_parquet(WAREHOUSE_DIR / "fact_research_activity.parquet", index=False)

    # 5. Populate DuckDB Database
    print(f"Connecting to DuckDB at {DUCKDB_PATH}...")
    con = duckdb.connect(str(DUCKDB_PATH))
    
    con.execute("DROP TABLE IF EXISTS fact_research_activity;")
    con.execute("DROP TABLE IF EXISTS dim_time;")
    con.execute("DROP TABLE IF EXISTS dim_paper;")
    con.execute("DROP TABLE IF EXISTS dim_topic;")
    con.execute("DROP TABLE IF EXISTS dim_user;")
    con.execute("DROP TABLE IF EXISTS dim_department;")

    con.execute(f"CREATE TABLE dim_department AS SELECT * FROM read_parquet('{WAREHOUSE_DIR}/dim_department.parquet');")
    con.execute(f"CREATE TABLE dim_user AS SELECT * FROM read_parquet('{WAREHOUSE_DIR}/dim_user.parquet');")
    con.execute(f"CREATE TABLE dim_topic AS SELECT * FROM read_parquet('{WAREHOUSE_DIR}/dim_topic.parquet');")
    con.execute(f"CREATE TABLE dim_paper AS SELECT * FROM read_parquet('{WAREHOUSE_DIR}/dim_paper.parquet');")
    con.execute(f"CREATE TABLE dim_time AS SELECT * FROM read_parquet('{WAREHOUSE_DIR}/dim_time.parquet');")
    con.execute(f"CREATE TABLE fact_research_activity AS SELECT * FROM read_parquet('{WAREHOUSE_DIR}/fact_research_activity.parquet');")

    # Verify counts in DuckDB
    res = con.execute("SELECT COUNT(*) FROM fact_research_activity").fetchone()[0]
    print(f"ETL Complete: DuckDB loaded {res} fact rows into Star Schema.")
    con.close()
    print("=" * 60)

if __name__ == "__main__":
    run_etl()
