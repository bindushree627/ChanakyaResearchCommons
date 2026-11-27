#!/usr/bin/env python3
"""
Safe Local Database Setup Script for Chanakya Research Commons.

Designed for teammates cloning the repository onto a new computer:
  1. Applies the SQLite schema (CREATE TABLE IF NOT EXISTS) and seeds departments.
  2. Checks if the database already contains users or papers.
     - If data already exists: preserves ALL existing records without resetting or overwriting.
     - If the database is fresh/empty: populates the synthetic academic dataset,
       sets real password hashes, and builds the DuckDB analytics warehouse.
  3. Ensures data/warehouse/analytics.duckdb is ready.

Usage:
    python3 scripts/setup_local_db.py
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.models.db import query_db
from scripts.init_db import init_database
from analytics.queries import ensure_warehouse_ready


def run_step(script_rel_path):
    script_path = PROJECT_ROOT / script_rel_path
    print(f"\n>>> Running {script_rel_path} ...")
    subprocess.run([sys.executable, str(script_path)], cwd=str(PROJECT_ROOT), check=True)


def main():
    print("=" * 70)
    print("CHANAKYA RESEARCH COMMONS — SAFE LOCAL DATABASE SETUP")
    print("=" * 70)

    # 1. Ensure schema and initial departments exist (non-destructive)
    init_database()

    # 2. Check whether the local database already has data
    user_count = query_db("SELECT COUNT(*) as c FROM users", one=True)["c"]
    paper_count = query_db("SELECT COUNT(*) as c FROM papers", one=True)["c"]

    if user_count > 0 or paper_count > 0:
        print(
            f"\n[SAFEGUARD] Existing local database detected ({user_count} users, {paper_count} papers)."
        )
        print("Skipping synthetic data generation to preserve all existing records.")
    else:
        print("\nFresh database detected. Populating synthetic academic dataset...")
        run_step("scripts/generate_synthetic_data.py")
        run_step("scripts/augment_missing_data.py")
        run_step("scripts/adjust_dataset_targets.py")
        run_step("analytics/etl_warehouse.py")

    # 3. Ensure DuckDB warehouse exists
    ensure_warehouse_ready()

    print("\n" + "=" * 70)
    print("LOCAL DATABASE SETUP COMPLETE.")
    print("Start the application locally with:")
    print("  python3 -m flask --app app:create_app run --host=127.0.0.1 --port=5000")
    print("=" * 70)


if __name__ == "__main__":
    main()
