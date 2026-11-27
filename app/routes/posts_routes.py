"""
Community Discussions & Research Feed Routes (Subsystem F2).
Handles research posts, paper attachments, threaded replies, and upvotes.
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app.models.db import query_db, execute_db
from app.models.entities import PostModel, ActivityLogger, UserModel
from app.routes.auth_routes import login_required

posts_bp = Blueprint("posts", __name__)

@posts_bp.route("/community")
def community_feed():
    user_id = session.get("user_id")
    feed_type = request.args.get("feed", "all") # 'all' or 'following'
    posts = PostModel.get_feed(current_user_id=user_id, feed_type=feed_type, limit=40)
    topics = query_db("SELECT id, name FROM topics ORDER BY name ASC")
    
    # User's saved papers for easy attachment in new post modal
    saved_papers = []
    if user_id:
        saved_papers = query_db("""
            SELECT p.id, p.title
            FROM library_saves ls
            JOIN papers p ON ls.paper_id = p.id
            WHERE ls.user_id = ?
            ORDER BY ls.saved_at DESC LIMIT 15
        """, (user_id,))

    return render_template(
        "community.html",
        posts=posts,
        feed_type=feed_type,
        topics=topics,
        saved_papers=saved_papers
    )

@posts_bp.route("/posts/create", methods=["POST"])
@login_required
def create_post():
    user_id = session["user_id"]
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    topic_id = request.form.get("topic_id")
    attached_paper_id = request.form.get("attached_paper_id")
    tags_raw = request.form.get("tags", "").strip()

    if not title or not content:
        flash("Title and discussion content are mandatory.", "danger")
        return redirect(url_for("posts.community_feed"))

    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

    post_id = PostModel.create(
        user_id=user_id,
        title=title,
        content=content,
        attached_paper_id=int(attached_paper_id) if attached_paper_id else None,
        primary_topic_id=int(topic_id) if topic_id else None,
        tags=tags
    )

    ActivityLogger.log(user_id, "post", "post", post_id)
    flash("Research discussion post published.", "success")
    return redirect(url_for("posts.post_detail", post_id=post_id))

@posts_bp.route("/posts/<int:post_id>")
def post_detail(post_id):
    user_id = session.get("user_id")
    post = PostModel.get_by_id(post_id, current_user_id=user_id)
    if not post:
        flash("Discussion post not found.", "warning")
        return redirect(url_for("posts.community_feed"))

    return render_template("post_detail.html", post=post)

@posts_bp.route("/posts/<int:post_id>/comment", methods=["POST"])
@login_required
def add_comment(post_id):
    user_id = session["user_id"]
    content = request.form.get("content", "").strip()
    parent_comment_id = request.form.get("parent_comment_id")

    if content:
        PostModel.add_comment(
            user_id=user_id,
            post_id=post_id,
            content=content,
            parent_comment_id=int(parent_comment_id) if parent_comment_id else None
        )
        ActivityLogger.log(user_id, "comment", "post", post_id)
        flash("Comment added to discussion.", "success")
    return redirect(url_for("posts.post_detail", post_id=post_id))

@posts_bp.route("/posts/<int:post_id>/vote", methods=["POST"])
@login_required
def vote_post(post_id):
    user_id = session["user_id"]
    vote_val = int(request.form.get("vote", 1))
    new_count = PostModel.vote(user_id, post_id, vote_val)
    ActivityLogger.log(user_id, "upvote", "post", post_id)
    if request.is_json:
        return jsonify({"upvote_count": new_count})
    return redirect(request.referrer or url_for("posts.post_detail", post_id=post_id))

@posts_bp.route("/posts/<int:post_id>/delete", methods=["POST"])
@login_required
def delete_post(post_id):
    user_id = session["user_id"]
    post = PostModel.get_by_id(post_id)
    user = UserModel.get_by_id(user_id)
    if post and (post["user_id"] == user_id or user.get("role") == "Admin"):
        execute_db("DELETE FROM posts WHERE id = ?", (post_id,))
        flash("Post deleted.", "info")
    return redirect(url_for("posts.community_feed"))
