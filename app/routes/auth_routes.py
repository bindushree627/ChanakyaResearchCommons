"""
Authentication & Member Profile Routes (Subsystem F1).
Handles registration, login, role-based authorization, user profiles,
research interests, and member follow relationships.
"""

from functools import wraps
from urllib.parse import urlparse
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app.models.db import query_db, execute_db
from app.models.entities import UserModel, ActivityLogger

auth_bp = Blueprint("auth", __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to access this feature.", "warning")
            return redirect(url_for("auth.login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in as Administrator.", "warning")
            return redirect(url_for("auth.login", next=request.url))
        user = UserModel.get_by_id(session["user_id"])
        if not user or user.get("role") != "Admin":
            flash("Administrator privileges required to access institutional analytics.", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    departments = query_db("SELECT id, name, code FROM departments ORDER BY name ASC")
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        full_name = request.form.get("full_name", "").strip()
        role = request.form.get("role", "Student")
        if role not in ("Student", "Faculty", "Researcher"):
            role = "Student"
        dept_id = request.form.get("department_id")
        bio = request.form.get("bio", "").strip()
        interests_raw = request.form.get("interests", "").strip()

        if not username or not email or not password or not full_name:
            flash("All mandatory fields must be completed.", "danger")
            return render_template("register.html", departments=departments)

        if UserModel.get_by_username(username):
            flash("Username already registered. Please choose another.", "danger")
            return render_template("register.html", departments=departments)

        if UserModel.get_by_email(email):
            flash("Email already registered. Please sign in.", "danger")
            return render_template("register.html", departments=departments)

        user = UserModel.create(
            username=username,
            email=email,
            password=password,
            full_name=full_name,
            role=role,
            department_id=int(dept_id) if dept_id else None,
            bio=bio
        )

        if user and interests_raw:
            topics = [t.strip() for t in interests_raw.split(",") if t.strip()]
            UserModel.set_interests(user["id"], topics)

        flash("Registration successful! You may now sign in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html", departments=departments)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")

        user = UserModel.authenticate(identifier, password)
        if user:
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            ActivityLogger.log(user["id"], "login", "user", user["id"])
            flash(f"Welcome back, {user['full_name']}!", "success")
            next_page = request.args.get("next")
            if (
                not next_page
                or urlparse(next_page).netloc != ""
                or next_page in (url_for("auth.login"), url_for("auth.register"), url_for("index"))
            ):
                next_page = url_for("home")
            return redirect(next_page)
        else:
            flash("Invalid credentials. Please verify your username/email and password.", "danger")

    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been securely signed out.", "info")
    return redirect(url_for("auth.login"))

@auth_bp.route("/profile")
@login_required
def my_profile():
    return redirect(url_for("auth.user_profile", user_id=session["user_id"]))

@auth_bp.route("/profile/<int:user_id>")
@login_required
def user_profile(user_id):
    user = UserModel.get_by_id(user_id)
    if not user:
        flash("Member profile not found.", "warning")
        return redirect(url_for("index"))

    stats = UserModel.get_stats(user_id)
    interests = UserModel.get_interests(user_id)
    collections = query_db("SELECT * FROM collections WHERE user_id = ?", (user_id,))
    recent_saves = query_db("""
        SELECT p.id as paper_id, p.title, p.publication_year, p.venue, ls.saved_at
        FROM library_saves ls
        JOIN papers p ON ls.paper_id = p.id
        WHERE ls.user_id = ?
        ORDER BY ls.saved_at DESC LIMIT 6
    """, (user_id,))
    recent_posts = query_db("""
        SELECT id, title, upvote_count, comment_count, created_at
        FROM posts
        WHERE user_id = ?
        ORDER BY created_at DESC LIMIT 5
    """, (user_id,))

    is_following = False
    is_self = (session.get("user_id") == user_id)
    current_uid = session.get("user_id")
    if not is_self and current_uid:
        is_following = UserModel.is_following(current_uid, user_id)

    followers_list = UserModel.get_followers(user_id)
    following_list = UserModel.get_following(user_id)
    current_following_ids = set(UserModel.get_following_ids(current_uid)) if current_uid else set()
    for f in followers_list:
        f["is_followed_by_me"] = f["id"] in current_following_ids
    for f in following_list:
        f["is_followed_by_me"] = f["id"] in current_following_ids

    return render_template(
        "profile.html",
        profile_user=user,
        stats=stats,
        interests=interests,
        collections=collections,
        recent_saves=recent_saves,
        recent_posts=recent_posts,
        followers_list=followers_list,
        following_list=following_list,
        is_following=is_following,
        is_self=is_self
    )

@auth_bp.route("/follow/<int:target_id>", methods=["POST"])
@login_required
def follow_user(target_id):
    success = UserModel.follow(session["user_id"], target_id)
    ActivityLogger.log(session["user_id"], "follow_user", "user", target_id)
    if request.is_json:
        return jsonify({"success": success})
    flash("You are now following this researcher.", "success")
    return redirect(request.referrer or url_for("auth.user_profile", user_id=target_id))

@auth_bp.route("/unfollow/<int:target_id>", methods=["POST"])
@login_required
def unfollow_user(target_id):
    UserModel.unfollow(session["user_id"], target_id)
    if request.is_json:
        return jsonify({"success": True})
    flash("Unfollowed successfully.", "info")
    return redirect(request.referrer or url_for("auth.user_profile", user_id=target_id))

@auth_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    user = UserModel.get_by_id(session["user_id"])
    departments = query_db("SELECT id, name, code FROM departments ORDER BY name ASC")
    current_interests = UserModel.get_interests(session["user_id"])
    all_topics = query_db("SELECT name FROM topics ORDER BY name ASC")

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        bio = request.form.get("bio", "").strip()
        website_url = request.form.get("website_url", "").strip()
        scholar_url = request.form.get("scholar_url", "").strip()
        dept_id = request.form.get("department_id")
        selected_topics = request.form.getlist("topics")

        execute_db("""
            UPDATE users
            SET full_name = ?, bio = ?, website_url = ?, scholar_url = ?, department_id = ?
            WHERE id = ?
        """, (full_name, bio, website_url, scholar_url, int(dept_id) if dept_id else None, session["user_id"]))

        UserModel.set_interests(session["user_id"], selected_topics)
        flash("Profile settings and research interests updated.", "success")
        return redirect(url_for("auth.settings"))

    return render_template(
        "settings.html",
        user=user,
        departments=departments,
        current_interests=current_interests,
        all_topics=all_topics
    )
