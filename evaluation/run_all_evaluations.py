#!/usr/bin/env python3
"""
Master Scientific Evaluation Runner for Chanakya Research Commons.
Executes all 6 subsystem evaluations:
A. Unified Search (BM25 vs Semantic vs Hybrid)
B. Duplicate Detection (Planted pairs)
C. Recommendations (Content vs Collaborative vs Baseline vs Cold-Start)
D. Trend Detection (Planted topic spikes)
E. Spam & Anomaly Detection (Isolation Forest)
F. Research Assistant (RAG Groundedness & Retrieval)

Outputs:
- reports/benchmarks_summary.json
- reports/evaluation_metrics.csv
"""

import sys
import json
import csv
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.eval_search import evaluate_search
from evaluation.eval_duplicate import evaluate_duplicates
from evaluation.eval_recommendations import evaluate_recommendations
from evaluation.eval_trends import evaluate_trend_detection
from evaluation.eval_spam import evaluate_spam_detection
from evaluation.eval_rag import evaluate_rag

REPORTS_DIR = PROJECT_ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

def run_all():
    print("=" * 80)
    print("CHANAKYA RESEARCH COMMONS — COMPREHENSIVE ALGORITHM EVALUATION SUITE")
    print(f"Timestamp: {datetime.now().isoformat()} | Course: V Sem B.Tech Data Mining")
    print("=" * 80)

    # 1. Unified Search
    search_metrics = evaluate_search()

    # 2. Duplicate Detection
    dup_metrics = evaluate_duplicates()

    # 3. Recommendations
    rec_metrics = evaluate_recommendations()

    # 4. Trends
    trend_metrics = evaluate_trend_detection()

    # 5. Spam Detection
    spam_metrics = evaluate_spam_detection()

    # 6. RAG Assistant
    rag_metrics = evaluate_rag()

    benchmarks_summary = {
        "timestamp": datetime.now().isoformat(),
        "subsystem_evaluations": {
            "search": search_metrics,
            "duplicate_detection": dup_metrics,
            "recommendations": rec_metrics,
            "trend_detection": trend_metrics,
            "spam_detection": spam_metrics,
            "research_assistant_rag": rag_metrics
        }
    }

    # Save to JSON
    json_path = REPORTS_DIR / "benchmarks_summary.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(benchmarks_summary, f, indent=2)
    print(f"\nSaved JSON Summary -> {json_path}")

    # Save to CSV
    csv_path = REPORTS_DIR / "evaluation_metrics.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Subsystem", "Algorithm_Variant", "Metric", "Value"])

        # Search
        for model, mdict in search_metrics.items():
            for mname, mval in mdict.items():
                writer.writerow(["Search", model, mname, mval])

        # Duplicate
        for mname, mval in dup_metrics.items():
            if isinstance(mval, (int, float)):
                writer.writerow(["DuplicateDetection", "TitleJaccard_Levenshtein", mname, mval])

        # Recs
        for model, mdict in rec_metrics.items():
            for mname, mval in mdict.items():
                writer.writerow(["Recommendations", model, mname, mval])

        # Trends
        for mname, mval in trend_metrics.items():
            if isinstance(mval, (int, float)):
                writer.writerow(["Trends", "SlidingWindow_ZScore", mname, mval])

        # Spam
        for mname, mval in spam_metrics.items():
            if isinstance(mval, (int, float)):
                writer.writerow(["SpamDetection", "IsolationForest_Rules", mname, mval])

        # RAG
        for mname, mval in rag_metrics.items():
            writer.writerow(["ResearchAssistant", "DenseMMR_GroundedExtractive", mname, mval])

    print(f"Saved CSV Metrics -> {csv_path}")
    print("=" * 80)
    print("All scientific evaluations completed successfully with numerical proofs.")
    print("=" * 80)

if __name__ == "__main__":
    run_all()
