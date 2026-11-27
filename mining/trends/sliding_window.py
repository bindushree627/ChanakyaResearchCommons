"""
Sliding-Window Trend Analysis and Topic Spike Detection.
Uses dynamic time windows (baseline vs current window) to compute Z-score velocities
and identify statistically significant research interest surges.
"""

from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from app.models.db import query_db

def compute_sliding_window_trends(window_days=14, baseline_days=45, z_threshold=2.0):
    """
    Computes activity velocity per topic:
    v_current = events in last `window_days`
    v_baseline = average events per window in preceding `baseline_days`
    Z = (v_current - mean_baseline) / std_baseline
    """
    # Query events mapped to topics
    events = query_db("""
        SELECT
            e.created_at,
            COALESCE(p.primary_topic_id, post.primary_topic_id) as topic_id,
            t.name as topic_name
        FROM activity_events e
        LEFT JOIN papers p ON (e.target_type = 'paper' AND e.target_id = p.id)
        LEFT JOIN posts post ON (e.target_type = 'post' AND e.target_id = post.id)
        JOIN topics t ON t.id = COALESCE(p.primary_topic_id, post.primary_topic_id)
        WHERE e.created_at IS NOT NULL
    """)

    if not events:
        return []

    df = pd.DataFrame(events)
    df["created_at"] = pd.to_datetime(df["created_at"])
    max_date = df["created_at"].max()

    curr_start = max_date - timedelta(days=window_days)
    base_start = curr_start - timedelta(days=baseline_days)

    df_recent = df[df["created_at"] >= base_start].copy()
    if df_recent.empty:
        return []

    # Assign 7-day sub-windows for baseline statistics
    df_recent["sub_window"] = ((max_date - df_recent["created_at"]).dt.days // 7)

    topics_summary = []
    num_curr_weeks = max(window_days / 7.0, 1.0)
    for topic_id, group in df_recent.groupby("topic_id"):
        topic_name = group["topic_name"].iloc[0]
        
        # Current window total and weekly velocity
        curr_total = len(group[group["sub_window"] < int(num_curr_weeks)])
        curr_weekly_rate = curr_total / num_curr_weeks
        
        # Historical sub-windows (each sub-window is 1 week)
        hist_group = group[group["sub_window"] >= int(num_curr_weeks)]
        hist_counts = hist_group.groupby("sub_window").size().values
        
        if len(hist_counts) < 2:
            hist_mean = curr_weekly_rate
            hist_std = max(hist_mean * 0.25, 1.0)
        else:
            hist_mean = float(np.mean(hist_counts))
            hist_std = float(np.std(hist_counts)) if np.std(hist_counts) > 0 else 1.0

        # Calculate Z-score based on weekly rate vs historical weekly mean
        z_score = (curr_weekly_rate - hist_mean) / hist_std
        growth_rate = ((curr_weekly_rate - hist_mean) / max(hist_mean, 1.0)) * 100.0

        # Statistically significant surge alert: surge growth rate > 100% and z_score >= threshold, or extreme growth >= 180%
        is_spike = (growth_rate >= 100.0 and z_score >= z_threshold) or (growth_rate >= 180.0)
        
        # Explanation
        if is_spike:
            status = "Spike Detected"
            reason = f"Sudden surge: weekly velocity is {z_score:.1f} standard deviations above historical baseline (+{growth_rate:.0f}%)."
        elif z_score > 1.0:
            status = "Rising Trend"
            reason = f"Steady upward momentum: +{growth_rate:.0f}% increase over historical baseline."
        else:
            status = "Stable"
            reason = "Consistent activity in line with seasonal baseline."

        topics_summary.append({
            "topic_id": int(topic_id),
            "topic_name": topic_name,
            "current_events": int(curr_total),
            "current_weekly_velocity": round(curr_weekly_rate, 1),
            "baseline_mean": round(hist_mean, 1),
            "z_score": round(float(z_score), 2),
            "growth_rate_pct": round(growth_rate, 1),
            "is_spike": bool(is_spike),
            "status": status,
            "explanation": reason
        })

    topics_summary.sort(key=lambda x: x["z_score"], reverse=True)
    return topics_summary

def get_trending_tags(top_n=10):
    """Computes top trending discussion tags."""
    tags = query_db("""
        SELECT pt.tag_name, COUNT(*) as usage_count
        FROM post_tags pt
        JOIN posts p ON pt.post_id = p.id
        GROUP BY pt.tag_name
        ORDER BY usage_count DESC
        LIMIT ?
    """, (top_n,))
    return tags
