#!/usr/bin/env python3
"""
Synthetic University Activity Dataset Verification Suite.
Course: V Sem B.Tech Data Mining and Warehousing, Chanakya University, Bangalore.

Calculates actual counts directly from the database and runs automated checks
enforcing all mandatory minimums and larger project targets:
- Members >= 50 across >= 6 departments
- Member roles (Student, Faculty, Researcher, Admin)
- Posts >= 5,000 and Comments >= 15,000 (Combined >= 20,000)
- Paper Saves >= 10,000
- Views >= 20,000
- Searches >= 10,000
- Total Activity Events >= 50,000
- Follow Relationships >= 100
- Minimum 6-month time span (>= 180 days, >= 26 active weeks)

Exits with code 0 on complete pass, code 1 on any failure.
"""

import sys
import pandas as pd
from datetime import datetime
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.models.db import query_db, get_connection

def verify_dataset():
    print("=" * 78)
    print("CHANAKYA RESEARCH COMMONS — DATASET VERIFICATION & AUDIT REPORT")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Target: Universal SQLite / PostgreSQL")
    print("=" * 78)

    failures = []
    
    # 1. Members and Departments
    total_members = query_db("SELECT COUNT(*) as c FROM users", one=True)["c"]
    depts = query_db("""
        SELECT d.code, d.name, COUNT(u.id) as member_count
        FROM departments d
        LEFT JOIN users u ON u.department_id = d.id
        GROUP BY d.code, d.name
        ORDER BY d.code
    """)
    active_depts = [d for d in depts if d["member_count"] > 0]
    
    print("\n[1] UNIVERSITY MEMBERS & DEPARTMENTS")
    print(f"  • Total University Members : {total_members:,}")
    print("  • Departmental Breakdown   :")
    for d in depts:
        print(f"    - [{d['code']}] {d['name'][:42]:<42} : {d['member_count']} members")

    # Member count by role
    roles = query_db("""
        SELECT role, COUNT(*) as c
        FROM users
        GROUP BY role
        ORDER BY c DESC
    """)
    print("  • Member Roles Breakdown   :")
    role_dict = {r["role"]: r["c"] for r in roles}
    for r in roles:
        print(f"    - {r['role']:<15} : {r['c']} members")

    # Checks
    if total_members < 50:
        failures.append(f"Total members ({total_members}) < 50 minimum")
    if len(active_depts) < 6:
        failures.append(f"Active departments ({len(active_depts)}) < 6 minimum")
    for req_role in ["Student", "Faculty", "Researcher", "Admin"]:
        if req_role not in role_dict or role_dict[req_role] == 0:
            failures.append(f"Missing required role: {req_role}")

    # 2. Posts and Comments
    post_count = query_db("SELECT COUNT(*) as c FROM posts", one=True)["c"]
    comment_count = query_db("SELECT COUNT(*) as c FROM post_comments", one=True)["c"]
    combined_discussions = post_count + comment_count
    attached_papers = query_db("SELECT COUNT(*) as c FROM posts WHERE attached_paper_id IS NOT NULL", one=True)["c"]
    threaded_comments = query_db("SELECT COUNT(*) as c FROM post_comments WHERE parent_comment_id IS NOT NULL", one=True)["c"]

    print("\n[2] RESEARCH POSTS & COMMENTS (DISCUSSIONS)")
    print(f"  • Total Research Posts     : {post_count:,}")
    print(f"  • Posts with Attached Paper: {attached_papers:,} ({attached_papers/max(post_count,1)*100:.1f}%)")
    print(f"  • Total Comments           : {comment_count:,}")
    print(f"  • Threaded Replies         : {threaded_comments:,} ({threaded_comments/max(comment_count,1)*100:.1f}%)")
    print(f"  • Combined Discussions     : {combined_discussions:,}")

    if post_count < 5000:
        failures.append(f"Posts count ({post_count}) < 5,000 project target")
    if comment_count < 15000:
        failures.append(f"Comments count ({comment_count}) < 15,000 project target")
    if combined_discussions < 20000:
        failures.append(f"Combined posts & comments ({combined_discussions}) < 20,000 project target")

    # 3. Save, View and Search Events
    paper_saves = query_db("SELECT COUNT(*) as c FROM library_saves", one=True)["c"]
    views = query_db("SELECT COUNT(*) as c FROM activity_events WHERE event_type = 'view_paper'", one=True)["c"]
    searches = query_db("SELECT COUNT(*) as c FROM activity_events WHERE event_type = 'search'", one=True)["c"]
    search_history_count = query_db("SELECT COUNT(*) as c FROM search_history", one=True)["c"]
    total_events = query_db("SELECT COUNT(*) as c FROM activity_events", one=True)["c"]
    
    event_breakdown = query_db("""
        SELECT event_type, COUNT(*) as c
        FROM activity_events
        GROUP BY event_type
        ORDER BY c DESC
    """)

    print("\n[3] SAVE, VIEW, AND SEARCH ACTIVITY EVENTS")
    print(f"  • Total Paper-Save Relationships (library_saves) : {paper_saves:,}")
    print(f"  • Total Paper Views (event_type='view_paper')   : {views:,}")
    print(f"  • Total Search Events (event_type='search')     : {searches:,}")
    print(f"  • Total Logged Queries (search_history)         : {search_history_count:,}")
    print(f"  • Total Activity Events (activity_events table) : {total_events:,}")
    print("  • Activity Events Breakdown by Type             :")
    for eb in event_breakdown:
        print(f"    - {eb['event_type']:<15} : {eb['c']:,} records")

    if paper_saves < 10000:
        failures.append(f"Paper saves ({paper_saves}) < 10,000 project target")
    if views < 20000:
        failures.append(f"Views ({views}) < 20,000 project target")
    if searches < 10000:
        failures.append(f"Searches ({searches}) < 10,000 project target")
    if total_events < 50000:
        failures.append(f"Total activity events ({total_events}) < 50,000 project target")

    # 4. Follow Relationships
    follow_count = query_db("SELECT COUNT(*) as c FROM user_followers", one=True)["c"]
    print("\n[4] ACADEMIC FOLLOW GRAPH")
    print(f"  • Total Follow Relationships (user_followers)  : {follow_count:,}")
    if follow_count < 100:
        failures.append(f"Follow relationships ({follow_count}) < 100 minimum")

    # 5. Temporal Coverage: Time Span & Active Weeks
    time_stats = query_db("""
        SELECT
            MIN(created_at) as earliest_event,
            MAX(created_at) as latest_event,
            COUNT(DISTINCT strftime('%Y-%W', created_at)) as active_weeks
        FROM activity_events
    """, one=True)
    
    earliest = time_stats["earliest_event"]
    latest = time_stats["latest_event"]
    active_weeks = time_stats["active_weeks"]

    dt_early = datetime.strptime(earliest, "%Y-%m-%d %H:%M:%S")
    dt_late = datetime.strptime(latest, "%Y-%m-%d %H:%M:%S")
    span_days = (dt_late - dt_early).days

    print("\n[5] TEMPORAL COVERAGE & DURATION")
    print(f"  • Earliest Activity Timestamp : {earliest}")
    print(f"  • Latest Activity Timestamp   : {latest}")
    print(f"  • Total Calendar Span         : {span_days} days ({span_days / 30.4:.1f} months)")
    print(f"  • Active Calendar Weeks       : {active_weeks} weeks")

    if span_days < 180:
        failures.append(f"Time span ({span_days} days) < 180 days (6 months) minimum")
    if active_weeks < 26:
        failures.append(f"Active weeks ({active_weeks}) < 26 weeks minimum")

    # 6. Library Papers & Ground Truth Verification
    papers_count = query_db("SELECT COUNT(*) as c FROM papers", one=True)["c"]
    sources_count = query_db("SELECT COUNT(*) as c FROM paper_sources", one=True)["c"]
    authors_count = query_db("SELECT COUNT(*) as c FROM paper_authors", one=True)["c"]
    collections_count = query_db("SELECT COUNT(*) as c FROM collections", one=True)["c"]
    topics_count = query_db("SELECT COUNT(*) as c FROM topics", one=True)["c"]

    print("\n[6] SCHOLARLY PAPERS, COLLECTIONS, TOPICS & GROUND TRUTH")
    print(f"  • Total Research Papers       : {papers_count:,}")
    print(f"  • Paper Source Linkages       : {sources_count:,}")
    print(f"  • Author Records Ingested     : {authors_count:,}")
    print(f"  • Total Collections           : {collections_count:,}")
    print(f"  • Total Research Topics       : {topics_count:,}")

    gt_dup = PROJECT_ROOT / "data" / "synthetic" / "ground_truth_duplicates.json"
    gt_spam = PROJECT_ROOT / "data" / "synthetic" / "ground_truth_spam_users.json"
    gt_spikes = PROJECT_ROOT / "data" / "synthetic" / "ground_truth_topic_spikes.json"
    
    print(f"  • Ground Truth Duplicates     : {'PRESENT (' + str(len(pd.read_json(gt_dup))) + ' pairs)' if gt_dup.exists() else 'MISSING'}")
    print(f"  • Ground Truth Spam Bots      : {'PRESENT (' + str(len(pd.read_json(gt_spam))) + ' accounts)' if gt_spam.exists() else 'MISSING'}")
    print(f"  • Ground Truth Topic Spikes   : {'PRESENT (' + str(len(pd.read_json(gt_spikes))) + ' spikes)' if gt_spikes.exists() else 'MISSING'}")

    # Final Audit Summary
    print("\n" + "=" * 78)
    print("AUTOMATED VERIFICATION AUDIT SUMMARY")
    print("=" * 78)

    checks = [
        ("Members >= 1,000", total_members >= 1000, f"{total_members:,} members"),
        ("Departments >= 8", len(active_depts) >= 8, f"{len(active_depts)} departments"),
        ("Roles coverage (Student, Faculty, Researcher, Admin)", all(r in role_dict for r in ["Student", "Faculty", "Researcher", "Admin"]), f"{len(role_dict)} roles"),
        ("Research Papers >= 2,000", papers_count >= 2000, f"{papers_count:,} papers"),
        ("Research Topics >= 100", topics_count >= 100, f"{topics_count:,} topics"),
        ("Collections >= 1,000", collections_count >= 1000, f"{collections_count:,} collections"),
        ("Posts >= 5,000", post_count >= 5000, f"{post_count:,} posts"),
        ("Comments & Replies >= 15,000", comment_count >= 15000, f"{comment_count:,} comments/replies"),
        ("Combined Posts + Comments >= 20,000", combined_discussions >= 20000, f"{combined_discussions:,} discussions"),
        ("Paper-Save Relationships >= 10,000", paper_saves >= 10000, f"{paper_saves:,} saves"),
        ("Paper Views >= 20,000", views >= 20000, f"{views:,} views"),
        ("Searches >= 10,000", searches >= 10000, f"{searches:,} searches"),
        ("Total Activity Events >= 50,000", total_events >= 50000, f"{total_events:,} events"),
        ("Follow Relationships >= 3,000", follow_count >= 3000, f"{follow_count:,} links"),
        ("Temporal Span >= 6 Months (>= 180 Days)", span_days >= 180, f"{span_days} days"),
        ("Active Weeks >= 26 Weeks", active_weeks >= 26, f"{active_weeks} weeks")
    ]

    all_passed = True
    for name, passed, val_str in checks:
        status_str = "PASS" if passed else "FAIL"
        if not passed:
            all_passed = False
        print(f"  [{status_str:4s}] {name:<48} : {val_str}")

    print("=" * 78)
    if all_passed:
        print("ALL MANDATORY REQUIREMENTS & PROJECT TARGETS ARE FULLY SATISFIED.")
        print("Verified directly against database records.")
        print("=" * 78)
        return 0
    else:
        print("VERIFICATION FAILED: The following requirements were not satisfied:")
        for f in failures:
            print(f"  [X] {f}")
        print("=" * 78)
        return 1

if __name__ == "__main__":
    exit_code = verify_dataset()
    sys.exit(exit_code)
