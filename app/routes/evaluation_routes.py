"""
Scientific Evaluation Benchmark Dashboard Routes (Section 5).
Displays empirical performance metrics, baseline comparisons, and confusion matrices.
"""

import json
from pathlib import Path
from flask import Blueprint, render_template
from app.config import Config

evaluation_bp = Blueprint("evaluation", __name__)
BENCHMARKS_FILE = Config.REPORTS_DIR / "benchmarks_summary.json"

@evaluation_bp.route("/evaluation")
def evaluation_dashboard():
    benchmarks = {}
    if BENCHMARKS_FILE.exists():
        with open(BENCHMARKS_FILE, "r", encoding="utf-8") as f:
            benchmarks = json.load(f)

    subs = benchmarks.get("subsystem_evaluations", {})
    return render_template(
        "evaluation.html",
        benchmarks=benchmarks,
        search_eval=subs.get("search", {}),
        dup_eval=subs.get("duplicate_detection", {}),
        rec_eval=subs.get("recommendations", {}),
        trend_eval=subs.get("trend_detection", {}),
        spam_eval=subs.get("spam_detection", {}),
        rag_eval=subs.get("research_assistant_rag", {})
    )
