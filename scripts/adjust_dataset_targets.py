#!/usr/bin/env python3
"""
Safe Non-Destructive Dataset Size Adjustment Script for Chanakya Research Commons.

Adjusts synthetic dataset counts to manageable university-scale targets while preserving
all genuine user-created records, administrator accounts, and foreign-key integrity:
  - Research papers: ~1,100 (target 1,000-1,200)
  - Student accounts: ~750 (target 700-800)
  - Faculty accounts: ~76 (realistic smaller group)
  - Researcher accounts: ~100 (realistic smaller group)
  - Administrator accounts: preserved (3)
"""

import random
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from werkzeug.security import generate_password_hash

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "chanakya_commons.db"
SEED = 42

FIRST_NAMES = [
    "Aarav", "Aditi", "Akhil", "Akshara", "Amrita", "Ananya", "Anirudh", "Anjali", "Arjun", "Aryan",
    "Bhavya", "Chetan", "Chinmay", "Darshan", "Deepika", "Dev", "Divya", "Esha", "Gaurav", "Harish",
    "Ishaan", "Jhanvi", "Karthik", "Kavya", "Keerthi", "Kiran", "Lakshmi", "Madhav", "Meera", "Nikhil",
    "Nisha", "Pranav", "Priya", "Rahul", "Rajesh", "Rhea", "Rohan", "Sahana", "Sanjay", "Shreya",
    "Siddharth", "Sneha", "Suhas", "Tanvi", "Varun", "Vidya", "Vikram", "Yash", "Zoya", "Nandini"
]

LAST_NAMES = [
    "Deshpande", "Joshi", "Nair", "Rao", "Shetty", "Upadhyay", "Banerjee", "Bhat", "Kulkarni", "Sharma",
    "Patil", "Hegde", "Menon", "Iyer", "Reddy", "Verma", "Gupta", "Mehta", "Kapoor", "Chatterjee",
    "Subramanian", "Krishnamurthy", "Kamath", "Pai", "Murthy", "Agarwal", "Malhotra", "Srinivasan", "Das", "Bose"
]


def get_counts(conn):
    roles = dict(conn.execute("SELECT role, COUNT(*) FROM users GROUP BY role").fetchall())
    return {
        "papers": conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0],
        "users": conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        "Student": roles.get("Student", 0),
        "Faculty": roles.get("Faculty", 0),
        "Researcher": roles.get("Researcher", 0),
        "Admin": roles.get("Admin", 0),
        "posts": conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0],
        "comments": conn.execute("SELECT COUNT(*) FROM post_comments WHERE parent_comment_id IS NULL").fetchone()[0],
        "replies": conn.execute("SELECT COUNT(*) FROM post_comments WHERE parent_comment_id IS NOT NULL").fetchone()[0],
        "library_saves": conn.execute("SELECT COUNT(*) FROM library_saves").fetchone()[0],
        "activity_events": conn.execute("SELECT COUNT(*) FROM activity_events").fetchone()[0],
        "user_followers": conn.execute("SELECT COUNT(*) FROM user_followers").fetchone()[0],
        "collections": conn.execute("SELECT COUNT(*) FROM collections").fetchone()[0],
    }


def main():
    random.seed(SEED)
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH), timeout=60.0)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")

    before = get_counts(conn)
    print("Before:", before)

    # 1. Trim excess SyntheticCorpus papers (target 1,100) that have no saves/posts/events
    target_papers = 1100
    if before["papers"] > target_papers:
        to_remove = before["papers"] - target_papers
        removable_paper_ids = [
            r[0]
            for r in conn.execute(
                """
                SELECT p.id
                FROM papers p
                JOIN paper_sources ps ON ps.paper_id = p.id
                WHERE ps.source_name = 'SyntheticCorpus'
                  AND p.id NOT IN (SELECT paper_id FROM library_saves)
                  AND p.id NOT IN (SELECT attached_paper_id FROM posts WHERE attached_paper_id IS NOT NULL)
                  AND p.id NOT IN (SELECT target_id FROM activity_events WHERE target_type = 'paper' AND target_id IS NOT NULL)
                ORDER BY p.id DESC
                LIMIT ?
                """,
                (to_remove,),
            ).fetchall()
        ]
        if removable_paper_ids:
            conn.executemany("DELETE FROM papers WHERE id = ?", [(pid,) for pid in removable_paper_ids])
            conn.commit()
        print(f"Removed {len(removable_paper_ids)} unreferenced SyntheticCorpus papers.")

    # 2. Trim excess synthetic Faculty (keep ~76) and Researcher (keep ~100) from id 62..1020
    #    Only remove synthetic accounts that have no posts, comments, saves, events, or searches.
    def remove_excess_synthetic_role(role_name, target_total):
        current_role = conn.execute("SELECT COUNT(*) FROM users WHERE role = ?", (role_name,)).fetchone()[0]
        if current_role <= target_total:
            return 0
        excess = current_role - target_total
        removable_ids = [
            r[0]
            for r in conn.execute(
                """
                SELECT u.id
                FROM users u
                WHERE u.role = ?
                  AND u.id BETWEEN 62 AND 1020
                  AND u.id NOT IN (SELECT user_id FROM posts)
                  AND u.id NOT IN (SELECT user_id FROM post_comments)
                  AND u.id NOT IN (SELECT user_id FROM library_saves)
                  AND u.id NOT IN (SELECT user_id FROM activity_events WHERE user_id IS NOT NULL)
                  AND u.id NOT IN (SELECT user_id FROM search_history WHERE user_id IS NOT NULL)
                ORDER BY u.id DESC
                LIMIT ?
                """,
                (role_name, excess),
            ).fetchall()
        ]
        if removable_ids:
            conn.executemany("DELETE FROM users WHERE id = ?", [(uid,) for uid in removable_ids])
            conn.commit()
        return len(removable_ids)

    removed_fac = remove_excess_synthetic_role("Faculty", 76)
    removed_res = remove_excess_synthetic_role("Researcher", 100)
    print(f"Removed {removed_fac} excess synthetic Faculty and {removed_res} excess synthetic Researcher accounts.")

    # 3. Ensure Student accounts are in 700-800 range (target 750)
    current_students = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'Student'").fetchone()[0]
    target_students = 750
    added_students = 0
    if current_students < target_students:
        needed_students = target_students - current_students
        dept_ids = [r[0] for r in conn.execute("SELECT id FROM departments ORDER BY id").fetchall()]
        topic_names = [r[0] for r in conn.execute("SELECT name FROM topics ORDER BY id").fetchall()]
        existing_usernames = {r[0].lower() for r in conn.execute("SELECT username FROM users").fetchall()}
        existing_emails = {r[0].lower() for r in conn.execute("SELECT email FROM users").fetchall()}
        pwd_hash = generate_password_hash("Chanakya@2026")
        base_time = datetime(2026, 6, 1, 9, 0, 0)
        idx = conn.execute("SELECT COALESCE(MAX(id), 1000) FROM users").fetchone()[0] + 1
        new_student_ids = []

        while added_students < needed_students:
            fn = random.choice(FIRST_NAMES)
            ln = random.choice(LAST_NAMES)
            uname = f"{fn.lower()}.{ln.lower()}{idx}"
            email = f"{uname}@chanakya.ac.in"
            idx += 1
            if uname in existing_usernames or email in existing_emails:
                continue
            existing_usernames.add(uname)
            existing_emails.add(email)

            dept_id = dept_ids[added_students % len(dept_ids)]
            full_name = f"{fn} {ln}"
            bio = "Student in Chanakya University researching applied computational methods and scholarly data analysis."
            created_at = (base_time + timedelta(days=random.randint(0, 150), hours=random.randint(8, 19))).strftime("%Y-%m-%d %H:%M:%S")
            cur = conn.execute(
                """
                INSERT INTO users (username, email, password_hash, full_name, role, department_id, bio, is_spam_flagged, created_at)
                VALUES (?, ?, ?, ?, 'Student', ?, ?, 0, ?)
                """,
                (uname, email, pwd_hash, full_name, dept_id, bio, created_at),
            )
            uid = cur.lastrowid
            new_student_ids.append(uid)
            for tname in random.sample(topic_names, k=min(3, len(topic_names))):
                conn.execute(
                    "INSERT OR IGNORE INTO user_interests (user_id, topic_name, weight) VALUES (?, ?, ?)",
                    (uid, tname, round(random.uniform(0.7, 1.0), 2)),
                )
            added_students += 1

        # Add realistic follow links for new students (2-3 each)
        existing_user_ids = [r[0] for r in conn.execute("SELECT id FROM users WHERE is_spam_flagged = 0").fetchall()]
        for uid in new_student_ids:
            targets = random.sample(existing_user_ids, k=min(3, len(existing_user_ids)))
            for tid in targets:
                if tid != uid:
                    conn.execute(
                        "INSERT OR IGNORE INTO user_followers (follower_id, following_id) VALUES (?, ?)",
                        (uid, tid),
                    )
        conn.commit()
    print(f"Added {added_students} synthetic Student accounts.")

    fk_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
    after = get_counts(conn)
    print("After:", after)
    print("PRAGMA foreign_key_check errors:", len(fk_errors))
    conn.close()


if __name__ == "__main__":
    main()
