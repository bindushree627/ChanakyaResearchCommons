"""
Spam and Abnormal Activity Detection Module.
Extracts user activity vectors (burst frequency, repetition ratio, keyword triggers)
and applies Scikit-Learn IsolationForest + Heuristic Scoring to detect anomalous bot accounts.
"""

import re
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from app.models.db import query_db, execute_db

SPAM_KEYWORDS = [
    r"\bcrypto\b", r"\bairdrop\b", r"\bbuy\b", r"\bguaranteed\b", r"\bwhatsapp\b",
    r"\bcheat\b", r"\bcheap\b", r"\baccept\b", r"\bclick\b", r"\bdiscount\b",
    r"\btelegram\b", r"\bcoupon\b", r"\bboost\b"
]

def extract_user_behavior_features():
    """
    Extracts numerical feature vectors for all registered users:
    - post_count
    - comment_count
    - save_count
    - spam_keyword_hits
    - burst_ratio (fraction of posts created within < 1 hour of another)
    - upvote_received_ratio
    """
    users = query_db("SELECT id, username, full_name, role, is_spam_flagged FROM users")
    features = []

    for u in users:
        uid = u["id"]
        posts = query_db("SELECT id, title, content, upvote_count, created_at FROM posts WHERE user_id = ? ORDER BY created_at ASC", (uid,))
        comments = query_db("SELECT id, created_at FROM post_comments WHERE user_id = ?", (uid,))
        saves = query_db("SELECT id FROM library_saves WHERE user_id = ?", (uid,))

        post_count = len(posts)
        comment_count = len(comments)
        save_count = len(saves)

        # Keyword hits
        keyword_hits = 0
        all_text = " ".join([p["title"] + " " + p["content"] for p in posts]).lower()
        for kw in SPAM_KEYWORDS:
            keyword_hits += len(re.findall(kw, all_text))

        # Burst velocity: posts within 2 hours of each other
        burst_count = 0
        if len(posts) > 1:
            for i in range(1, len(posts)):
                t1 = pd.to_datetime(posts[i-1]["created_at"])
                t2 = pd.to_datetime(posts[i]["created_at"])
                if abs((t2 - t1).total_seconds()) < 7200: # 2 hours
                    burst_count += 1
            burst_ratio = burst_count / len(posts)
        else:
            burst_ratio = 0.0

        # Upvote ratio: legitimate posts get upvotes, spam bot posts get 0
        total_upvotes = sum(p["upvote_count"] for p in posts)
        avg_upvotes = (total_upvotes / post_count) if post_count > 0 else 0.0

        features.append({
            "user_id": uid,
            "username": u["username"],
            "full_name": u["full_name"],
            "role": u["role"],
            "is_planted_spam": u["is_spam_flagged"],
            "post_count": post_count,
            "comment_count": comment_count,
            "save_count": save_count,
            "keyword_hits": keyword_hits,
            "burst_ratio": burst_ratio,
            "avg_upvotes": avg_upvotes
        })

    return pd.DataFrame(features)

def detect_spam_accounts(contamination=0.10):
    """
    Runs IsolationForest anomaly detection and heuristic rule checks.
    Returns list of flagged accounts with anomaly scores and diagnostic explanations.
    """
    df = extract_user_behavior_features()
    if df.empty or len(df) < 5:
        return []

    feature_cols = ["post_count", "comment_count", "save_count", "keyword_hits", "burst_ratio", "avg_upvotes"]
    X = df[feature_cols].values

    # Train Isolation Forest
    iso = IsolationForest(contamination=contamination, random_state=42)
    df["iso_pred"] = iso.fit_predict(X) # -1 for anomaly, 1 for normal
    df["anomaly_score"] = -iso.score_samples(X) # higher means more anomalous

    # Heuristic Rule: high keywords OR high burst with 0 saves/upvotes
    df["rule_flag"] = (df["keyword_hits"] >= 3) | ((df["burst_ratio"] > 0.40) & (df["save_count"] == 0) & (df["avg_upvotes"] <= 1.0))
    df["is_anomaly"] = (df["iso_pred"] == -1) | df["rule_flag"]

    flagged = []
    for _, row in df[df["is_anomaly"]].iterrows():
        reasons = []
        if row["keyword_hits"] >= 2:
            reasons.append(f"Contains promotional/commercial triggers ({int(row['keyword_hits'])} occurrences)")
        if row["burst_ratio"] > 0.30:
            reasons.append(f"Abnormal burst posting ({int(row['burst_ratio']*100)}% created in short intervals)")
        if row["save_count"] == 0:
            reasons.append("Zero legitimate library saves or research curation")
        if row["avg_upvotes"] <= 1.0:
            reasons.append("Low community trust / zero upvotes")

        explanation = "; ".join(reasons) if reasons else "Multi-dimensional activity outlier detected by Isolation Forest."

        flagged.append({
            "user_id": int(row["user_id"]),
            "username": row["username"],
            "full_name": row["full_name"],
            "role": row["role"],
            "anomaly_score": round(float(row["anomaly_score"]), 3),
            "keyword_hits": int(row["keyword_hits"]),
            "burst_ratio": round(float(row["burst_ratio"]), 2),
            "explanation": explanation,
            "is_planted_spam": bool(row["is_planted_spam"])
        })

    flagged.sort(key=lambda x: x["anomaly_score"], reverse=True)
    return flagged

def get_admin_monitoring_alerts():
    """Generates real-time security alerts for the institutional dashboard."""
    flagged = detect_spam_accounts()
    alerts = []
    for f in flagged:
        alerts.append({
            "severity": "CRITICAL" if f["keyword_hits"] >= 3 else "WARNING",
            "type": "SPAM_ANOMALY",
            "target": f"User: @{f['username']} ({f['full_name']})",
            "score": f["anomaly_score"],
            "details": f["explanation"],
            "user_id": f["user_id"]
        })
    return alerts
