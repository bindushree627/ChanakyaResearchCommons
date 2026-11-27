"""
Research Assistant RAG Routes (Subsystem F8).
Provides an interactive AI academic research dialogue powered by passage retrieval,
grounded extractive synthesis, citations, and optional local Ollama integration.
"""

from flask import Blueprint, render_template, request, jsonify, session
from app.models.entities import ActivityLogger
from mining.rag.generator import generate_rag_answer

assistant_bp = Blueprint("assistant", __name__)

@assistant_bp.route("/assistant")
def assistant_page():
    # Preset sample questions
    sample_queries = [
        "How do attention mechanisms enhance vision transformers?",
        "What methods mitigate hallucinations in large language models?",
        "How does the FP-Growth algorithm optimize frequent itemset discovery?",
        "What are the advantages of compute-in-memory architectures in VLSI?",
        "What is the role of pangenome graphs in genomic variant calling?"
    ]
    return render_template("assistant.html", sample_queries=sample_queries)

@assistant_bp.route("/api/assistant/ask", methods=["POST"])
def api_ask():
    data = request.get_json() or {}
    question = data.get("question", "").strip()

    if not question:
        return jsonify({
            "error": "Question cannot be empty."
        }), 400

    user_id = session.get("user_id")
    if user_id:
        ActivityLogger.log(user_id, "ask_assistant", "query", None, {"question": question})

    result = generate_rag_answer(question)
    return jsonify(result)
