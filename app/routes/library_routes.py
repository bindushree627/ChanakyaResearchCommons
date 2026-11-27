"""
Shared Research Library & Collections Routes (Subsystem F3).
Handles saving scholarly papers, personal collections, private notes, ratings,
and 'Members who saved this also saved' association-rule recommendations.
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app.models.db import query_db, execute_db
from app.models.entities import PaperModel, LibraryModel, ActivityLogger
from app.routes.auth_routes import login_required
from mining.recommendations.association_rules import get_also_saved_recommendations
from ingestion.normalizer import extract_doi, extract_arxiv_id, normalize_title
from mining.embeddings import generate_embedding
import json

library_bp = Blueprint("library", __name__)

@library_bp.route("/library")
def library_index():
    user_id = session.get("user_id")
    view_mode = request.args.get("view", "university") # 'university' or 'personal'
    topic_id = request.args.get("topic_id")
    year = request.args.get("year")
    collection_id = request.args.get("collection_id")
    page = max(1, request.args.get("page", 1, type=int))
    per_page = 40

    topics = query_db("SELECT id, name FROM topics ORDER BY name ASC")
    years = [2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019]
    total_papers = query_db("SELECT COUNT(*) as c FROM papers", one=True)["c"]
    personal_count = query_db("SELECT COUNT(*) as c FROM library_saves WHERE user_id = ?", (user_id,), one=True)["c"] if user_id else 0

    if view_mode == "personal" and user_id:
        user_saves = LibraryModel.get_user_library(user_id, collection_id=int(collection_id) if collection_id else None)
        collections = LibraryModel.get_user_collections(user_id)
        return render_template(
            "library.html",
            view_mode="personal",
            papers=user_saves,
            collections=collections,
            topics=topics,
            years=years,
            selected_collection=collection_id,
            total_papers=total_papers,
            personal_count=personal_count
        )
    else:
        # University Shared Library (dynamic filtered count + pagination)
        where_clauses = ["1=1"]
        count_params = []
        if topic_id:
            where_clauses.append("primary_topic_id = ?")
            count_params.append(int(topic_id))
        if year:
            where_clauses.append("publication_year = ?")
            count_params.append(int(year))
        filtered_count = query_db(
            f"SELECT COUNT(*) as c FROM papers WHERE {' AND '.join(where_clauses)}",
            count_params,
            one=True
        )["c"]
        total_pages = max(1, (filtered_count + per_page - 1) // per_page)
        page = min(page, total_pages)
        offset = (page - 1) * per_page

        papers = PaperModel.get_all(
            limit=per_page,
            offset=offset,
            topic_id=int(topic_id) if topic_id else None,
            year=int(year) if year else None
        )
        collections = LibraryModel.get_user_collections(user_id) if user_id else []
        return render_template(
            "library.html",
            view_mode="university",
            papers=papers,
            collections=collections,
            topics=topics,
            years=years,
            selected_topic=topic_id,
            selected_year=year,
            total_papers=total_papers,
            filtered_count=filtered_count,
            personal_count=personal_count,
            page=page,
            total_pages=total_pages,
            per_page=per_page
        )

@library_bp.route("/papers/<int:paper_id>")
def paper_detail(paper_id):
    user_id = session.get("user_id")
    paper = PaperModel.get_by_id(paper_id)
    if not paper:
        flash("Research paper not found.", "warning")
        return redirect(url_for("library.library_index"))

    is_saved = PaperModel.is_saved_by_user(user_id, paper_id) if user_id else False
    user_save_info = None
    if is_saved:
        user_save_info = query_db(
            "SELECT * FROM library_saves WHERE user_id = ? AND paper_id = ?",
            (user_id, paper_id),
            one=True
        )

    # Log view event
    if user_id:
        ActivityLogger.log(user_id, "view_paper", "paper", paper_id)

    # FP-Growth "Members who saved this also saved" recommendations
    co_saved_papers = get_also_saved_recommendations(paper_id, top_n=4)

    collections = LibraryModel.get_user_collections(user_id) if user_id else []

    return render_template(
        "paper_detail.html",
        paper=paper,
        is_saved=is_saved,
        user_save_info=user_save_info,
        co_saved_papers=co_saved_papers,
        collections=collections
    )

@library_bp.route("/papers/save", methods=["POST"])
@login_required
def save_paper():
    user_id = session["user_id"]
    paper_id = request.form.get("paper_id")
    collection_id = request.form.get("collection_id")
    private_notes = request.form.get("private_notes", "").strip()
    rating = request.form.get("rating")

    if not paper_id:
        flash("Invalid paper identifier.", "danger")
        return redirect(request.referrer or url_for("library.library_index"))

    LibraryModel.save_paper(
        user_id=user_id,
        paper_id=int(paper_id),
        collection_id=int(collection_id) if collection_id else None,
        private_notes=private_notes,
        rating=int(rating) if rating else None
    )

    ActivityLogger.log(user_id, "save_paper", "paper", int(paper_id), {"collection_id": collection_id})
    flash("Paper saved to your personal research library.", "success")
    return redirect(request.referrer or url_for("library.paper_detail", paper_id=paper_id))

@library_bp.route("/papers/<int:paper_id>/unsave", methods=["POST"])
@login_required
def unsave_paper(paper_id):
    user_id = session["user_id"]
    LibraryModel.remove_save(user_id, paper_id)
    flash("Paper removed from your personal library.", "info")
    return redirect(request.referrer or url_for("library.library_index"))

@library_bp.route("/collections/create", methods=["POST"])
@login_required
def create_collection():
    user_id = session["user_id"]
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    if title:
        LibraryModel.create_collection(user_id, title, description)
        flash(f"Collection '{title}' created successfully.", "success")
    return redirect(request.referrer or url_for("library.library_index", view="personal"))

@library_bp.route("/papers/import", methods=["POST"])
@login_required
def import_paper():
    user_id = session["user_id"]
    identifier = request.form.get("identifier", "").strip()
    title = request.form.get("title", "").strip()
    abstract = request.form.get("abstract", "").strip()
    year = request.form.get("year", 2026)
    venue = request.form.get("venue", "University Preprint Repository")

    if not title:
        flash("Title is mandatory for cataloguing.", "danger")
        return redirect(url_for("library.library_index"))

    doi = extract_doi(identifier)
    arxiv_id = extract_arxiv_id(identifier)
    clean_title = normalize_title(title)

    # Check duplicate
    existing = None
    if doi:
        existing = query_db("SELECT id FROM papers WHERE doi = ?", (doi,), one=True)
    if not existing:
        existing = query_db("SELECT id FROM papers WHERE clean_title = ?", (clean_title,), one=True)

    if existing:
        paper_id = existing["id"]
        flash("Paper is already indexed in the Chanakya repository. Opening record.", "info")
    else:
        emb = generate_embedding(f"{title}. {abstract}")
        emb_json = json.dumps(emb)
        paper_id = execute_db(
            """
            INSERT INTO papers (title, clean_title, abstract, publication_year, doi, arxiv_id, venue, embedding_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (title, clean_title, abstract, int(year), doi, arxiv_id, venue, emb_json)
        )
        execute_db(
            "INSERT INTO paper_sources (paper_id, source_name, external_id, landing_url) VALUES (?, 'ManualEntry', ?, ?)",
            (paper_id, identifier or f"ID_{paper_id}", f"https://doi.org/{doi}" if doi else "")
        )
        flash("Paper successfully catalogued into Chanakya Research Commons.", "success")

    # Automatically save to user's library
    LibraryModel.save_paper(user_id, paper_id)
    return redirect(url_for("library.paper_detail", paper_id=paper_id))
