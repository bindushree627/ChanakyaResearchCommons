"""
Flask Application Factory for Chanakya Research Commons.
Configures session security, blueprints, database hooks, and Jinja filters.
"""

import os
import logging
from flask import Flask, session, g, request, redirect, url_for, flash, render_template, jsonify
from flask_wtf.csrf import CSRFProtect
from app.config import config_by_name, Config
from app.models.db import close_db, query_db
from app.models.entities import UserModel

csrf = CSRFProtect()

def create_app(config_name="default"):
    app = Flask(__name__)
    config_obj = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(config_obj)

    if config_name == "production":
        env_secret = os.getenv("SECRET_KEY", "").strip()
        if not env_secret or env_secret == Config.SECRET_KEY:
            raise RuntimeError("SECRET_KEY environment variable must be set to a secure value in production.")
        app.config["SECRET_KEY"] = env_secret
        logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s in %(module)s: %(message)s")

    csrf.init_app(app)

    # Ensure required runtime folders exist
    os.makedirs(app.config.get("DATA_DIR", "data"), exist_ok=True)
    os.makedirs(app.config.get("RAW_DATA_DIR", "data/raw"), exist_ok=True)
    os.makedirs(app.config.get("WAREHOUSE_DIR", "data/warehouse"), exist_ok=True)
    os.makedirs(app.config.get("SYNTHETIC_DATA_DIR", "data/synthetic"), exist_ok=True)

    # Teardown database request context
    app.teardown_appcontext(close_db)

    # Context processor: inject current_user and counts into all Jinja templates
    @app.context_processor
    def inject_global_vars():
        current_user = None
        user_id = session.get("user_id")
        if user_id:
            current_user = UserModel.get_by_id(user_id)
        
        # Navigation badges
        pending_alerts_count = 0
        if current_user and current_user.get("role") == "Admin":
            from mining.anomaly_detection.spam_detector import get_admin_monitoring_alerts
            try:
                pending_alerts_count = len(get_admin_monitoring_alerts())
            except Exception:
                pending_alerts_count = 0

        return {
            "current_user": current_user,
            "pending_alerts_count": pending_alerts_count,
            "app_name": "Chanakya Research Commons"
        }

    # Custom Jinja template filters
    @app.template_filter("truncate_chars")
    def truncate_chars(s, length=120):
        if not s:
            return ""
        return (s[:length] + "...") if len(s) > length else s

    @app.template_filter("format_date")
    def format_date(dt_str):
        if not dt_str:
            return ""
        try:
            return str(dt_str)[:10]
        except Exception:
            return str(dt_str)

    # Register Blueprints
    from app.routes.auth_routes import auth_bp
    from app.routes.library_routes import library_bp
    from app.routes.posts_routes import posts_bp
    from app.routes.search_routes import search_bp
    from app.routes.rec_routes import rec_bp
    from app.routes.assistant_routes import assistant_bp
    from app.routes.analytics_routes import analytics_bp
    from app.routes.evaluation_routes import evaluation_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(library_bp)
    app.register_blueprint(posts_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(rec_bp)
    app.register_blueprint(assistant_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(evaluation_bp)

    # Global Authentication Gate: Protect internal pages & APIs
    @app.before_request
    def enforce_authentication():
        # Allow static assets
        if request.path.startswith("/static"):
            return None

        # Allow public authentication endpoints
        public_endpoints = {"auth.login", "auth.register", "auth.logout", "static"}
        if request.endpoint in public_endpoints:
            # If already authenticated, redirect to Home dashboard
            if session.get("user_id") and request.endpoint in {"auth.login", "auth.register"}:
                return redirect(url_for("home"))
            return None

        # Check user session
        user_id = session.get("user_id")
        if not user_id:
            if request.path.startswith("/api/") or request.is_json:
                return jsonify({"error": "Authentication required"}), 401
            # Unauthenticated visitor: redirect to login
            if request.path in ("/", "/home"):
                return redirect(url_for("auth.login"))
            flash("Please sign in to access Chanakya Research Commons.", "warning")
            return redirect(url_for("auth.login", next=request.url))

        # Validate that the logged-in user exists
        user = UserModel.get_by_id(user_id)
        if not user:
            session.clear()
            if request.path.startswith("/api/") or request.is_json:
                return jsonify({"error": "Session expired"}), 401
            flash("Session expired. Please sign in again.", "info")
            return redirect(url_for("auth.login"))

    # Authenticated Home / Dashboard Route
    @app.route("/", endpoint="index")
    @app.route("/home", endpoint="home")
    def home_dashboard():
        # Popular / most-saved & most-cited scholarly papers
        top_papers = query_db("""
            SELECT p.*, t.name as topic_name,
                   (SELECT COUNT(*) FROM library_saves WHERE paper_id = p.id) as save_count
            FROM papers p
            LEFT JOIN topics t ON p.primary_topic_id = t.id
            ORDER BY save_count DESC, p.citation_count DESC
            LIMIT 6
        """)
        for p in top_papers:
            p["authors"] = query_db(
                "SELECT author_name FROM paper_authors WHERE paper_id = ? ORDER BY author_order ASC LIMIT 2",
                (p["id"],)
            )

        # Recent community discussions
        recent_posts = query_db("""
            SELECT p.id, p.title, p.content, p.comment_count, p.upvote_count, p.created_at,
                   u.full_name, d.code as department_code, t.name as topic_name
            FROM posts p
            JOIN users u ON p.user_id = u.id
            LEFT JOIN departments d ON u.department_id = d.id
            LEFT JOIN topics t ON p.primary_topic_id = t.id
            ORDER BY p.created_at DESC
            LIMIT 4
        """)

        # Trending research topics
        trending_topics = []
        try:
            from mining.trends.sliding_window import compute_sliding_window_trends
            raw_trends = compute_sliding_window_trends(window_days=14, baseline_days=45, z_threshold=1.4)
            trending_topics = [
                {"id": t.get("topic_id"), "name": t.get("topic_name"), "is_spike": t.get("is_spike", False)}
                for t in raw_trends[:6]
            ]
        except Exception:
            trending_topics = query_db("""
                SELECT t.id, t.name, 0 as is_spike
                FROM topics t
                ORDER BY t.id ASC
                LIMIT 6
            """)

        return render_template(
            "home.html",
            top_papers=top_papers,
            recent_posts=recent_posts,
            trending_topics=trending_topics
        )

    @app.errorhandler(404)
    def handle_404(err):
        if request.path.startswith("/api/") or request.is_json:
            return jsonify({"error": "Resource not found"}), 404
        flash("The requested page was not found.", "warning")
        if session.get("user_id"):
            return redirect(url_for("home"))
        return redirect(url_for("auth.login"))

    @app.errorhandler(500)
    def handle_500(err):
        app.logger.exception("Unhandled server error: %s", err)
        if request.path.startswith("/api/") or request.is_json:
            return jsonify({"error": "Internal server error"}), 500
        flash("An unexpected error occurred. Please try again.", "danger")
        if session.get("user_id"):
            return redirect(url_for("home"))
        return redirect(url_for("auth.login"))

    return app
