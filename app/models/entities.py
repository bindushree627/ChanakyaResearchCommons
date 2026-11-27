"""
Domain Entity Models and Data Access Helpers for Chanakya Research Commons.
"""

import json
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app.models.db import query_db, execute_db

class UserModel:
    @staticmethod
    def create(username, email, password, full_name, role='Student', department_id=None, bio="", website_url="", scholar_url=""):
        pwd_hash = generate_password_hash(password)
        user_id = execute_db(
            """
            INSERT INTO users (username, email, password_hash, full_name, role, department_id, bio, website_url, scholar_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (username.lower().strip(), email.lower().strip(), pwd_hash, full_name.strip(), role, department_id, bio, website_url, scholar_url)
        )
        return UserModel.get_by_id(user_id)

    @staticmethod
    def get_by_id(user_id):
        return query_db(
            """
            SELECT u.*, d.name as department_name, d.code as department_code
            FROM users u
            LEFT JOIN departments d ON u.department_id = d.id
            WHERE u.id = ?
            """,
            (user_id,),
            one=True
        )

    @staticmethod
    def get_by_username(username):
        return query_db(
            """
            SELECT u.*, d.name as department_name, d.code as department_code
            FROM users u
            LEFT JOIN departments d ON u.department_id = d.id
            WHERE LOWER(u.username) = LOWER(?)
            """,
            (username.strip(),),
            one=True
        )

    @staticmethod
    def get_by_email(email):
        return query_db(
            """
            SELECT u.*, d.name as department_name, d.code as department_code
            FROM users u
            LEFT JOIN departments d ON u.department_id = d.id
            WHERE LOWER(u.email) = LOWER(?)
            """,
            (email.strip(),),
            one=True
        )

    @staticmethod
    def authenticate(identifier, password):
        user = query_db(
            """
            SELECT * FROM users
            WHERE LOWER(username) = LOWER(?) OR LOWER(email) = LOWER(?)
            """,
            (identifier.strip(), identifier.strip()),
            one=True
        )
        if not user:
            return None
        try:
            if check_password_hash(user["password_hash"], password):
                return user
        except Exception:
            pass
        return None

    @staticmethod
    def get_interests(user_id):
        rows = query_db(
            "SELECT topic_name, weight FROM user_interests WHERE user_id = ? ORDER BY weight DESC",
            (user_id,)
        )
        return [r["topic_name"] for r in rows]

    @staticmethod
    def set_interests(user_id, topic_list):
        execute_db("DELETE FROM user_interests WHERE user_id = ?", (user_id,))
        for topic in topic_list:
            if topic.strip():
                execute_db(
                    "INSERT INTO user_interests (user_id, topic_name, weight) VALUES (?, ?, 1.0)",
                    (user_id, topic.strip())
                )

    @staticmethod
    def is_following(follower_id, following_id):
        row = query_db(
            "SELECT 1 FROM user_followers WHERE follower_id = ? AND following_id = ?",
            (follower_id, following_id),
            one=True
        )
        return bool(row)

    @staticmethod
    def follow(follower_id, following_id):
        if follower_id == following_id:
            return False
        if not UserModel.is_following(follower_id, following_id):
            execute_db(
                "INSERT INTO user_followers (follower_id, following_id) VALUES (?, ?)",
                (follower_id, following_id)
            )
        return True

    @staticmethod
    def unfollow(follower_id, following_id):
        execute_db(
            "DELETE FROM user_followers WHERE follower_id = ? AND following_id = ?",
            (follower_id, following_id)
        )
        return True

    @staticmethod
    def get_following_ids(user_id):
        rows = query_db("SELECT following_id FROM user_followers WHERE follower_id = ?", (user_id,))
        return [r["following_id"] for r in rows]

    @staticmethod
    def get_followers(user_id):
        return query_db(
            """
            SELECT u.id, u.username, u.full_name, u.role, d.code as department_code, d.name as department_name
            FROM user_followers uf
            JOIN users u ON uf.follower_id = u.id
            LEFT JOIN departments d ON u.department_id = d.id
            WHERE uf.following_id = ?
            ORDER BY u.full_name ASC
            """,
            (user_id,)
        )

    @staticmethod
    def get_following(user_id):
        return query_db(
            """
            SELECT u.id, u.username, u.full_name, u.role, d.code as department_code, d.name as department_name
            FROM user_followers uf
            JOIN users u ON uf.following_id = u.id
            LEFT JOIN departments d ON u.department_id = d.id
            WHERE uf.follower_id = ?
            ORDER BY u.full_name ASC
            """,
            (user_id,)
        )

    @staticmethod
    def get_stats(user_id):
        saves_count = query_db("SELECT COUNT(*) as c FROM library_saves WHERE user_id = ?", (user_id,), one=True)["c"]
        posts_count = query_db("SELECT COUNT(*) as c FROM posts WHERE user_id = ?", (user_id,), one=True)["c"]
        followers_count = query_db("SELECT COUNT(*) as c FROM user_followers WHERE following_id = ?", (user_id,), one=True)["c"]
        following_count = query_db("SELECT COUNT(*) as c FROM user_followers WHERE follower_id = ?", (user_id,), one=True)["c"]
        return {
            "saves_count": saves_count,
            "posts_count": posts_count,
            "followers_count": followers_count,
            "following_count": following_count
        }


class PaperModel:
    @staticmethod
    def get_by_id(paper_id):
        paper = query_db(
            """
            SELECT p.*, t.name as topic_name, t.domain as topic_domain,
                   (SELECT COUNT(*) FROM library_saves WHERE paper_id = p.id) as save_count
            FROM papers p
            LEFT JOIN topics t ON p.primary_topic_id = t.id
            WHERE p.id = ?
            """,
            (paper_id,),
            one=True
        )
        if not paper:
            return None
        paper["authors"] = query_db(
            "SELECT author_name, normalized_name, affiliation FROM paper_authors WHERE paper_id = ? ORDER BY author_order ASC",
            (paper_id,)
        )
        paper["sources"] = query_db(
            "SELECT source_name, external_id, landing_url, pdf_url FROM paper_sources WHERE paper_id = ?",
            (paper_id,)
        )
        return paper

    @staticmethod
    def get_all(limit=100, offset=0, topic_id=None, year=None):
        where_clauses = ["1=1"]
        params = []
        if topic_id:
            where_clauses.append("p.primary_topic_id = ?")
            params.append(topic_id)
        if year:
            where_clauses.append("p.publication_year = ?")
            params.append(year)
        
        where_sql = " AND ".join(where_clauses)
        params.extend([limit, offset])

        query = f"""
            SELECT p.*, t.name as topic_name,
                   (SELECT COUNT(*) FROM library_saves WHERE paper_id = p.id) as save_count
            FROM papers p
            LEFT JOIN topics t ON p.primary_topic_id = t.id
            WHERE {where_sql}
            ORDER BY save_count DESC, p.citation_count DESC
            LIMIT ? OFFSET ?
        """
        papers = query_db(query, params)
        for p in papers:
            p["authors"] = query_db(
                "SELECT author_name FROM paper_authors WHERE paper_id = ? ORDER BY author_order ASC LIMIT 3",
                (p["id"],)
            )
            p["sources"] = query_db(
                "SELECT source_name FROM paper_sources WHERE paper_id = ?",
                (p["id"],)
            )
        return papers

    @staticmethod
    def is_saved_by_user(user_id, paper_id):
        row = query_db(
            "SELECT 1 FROM library_saves WHERE user_id = ? AND paper_id = ?",
            (user_id, paper_id),
            one=True
        )
        return bool(row)


class LibraryModel:
    @staticmethod
    def save_paper(user_id, paper_id, collection_id=None, private_notes="", rating=None):
        existing = query_db(
            "SELECT id FROM library_saves WHERE user_id = ? AND paper_id = ?",
            (user_id, paper_id),
            one=True
        )
        if existing:
            execute_db(
                """
                UPDATE library_saves
                SET collection_id = ?, private_notes = ?, rating = ?, saved_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (collection_id, private_notes, rating, existing["id"])
            )
            return existing["id"]
        else:
            save_id = execute_db(
                """
                INSERT INTO library_saves (user_id, paper_id, collection_id, private_notes, rating)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, paper_id, collection_id, private_notes, rating)
            )
            return save_id

    @staticmethod
    def remove_save(user_id, paper_id):
        execute_db(
            "DELETE FROM library_saves WHERE user_id = ? AND paper_id = ?",
            (user_id, paper_id)
        )

    @staticmethod
    def get_user_library(user_id, collection_id=None):
        where_clause = "ls.user_id = ?"
        params = [user_id]
        if collection_id:
            where_clause += " AND ls.collection_id = ?"
            params.append(collection_id)

        rows = query_db(
            f"""
            SELECT ls.id as save_id, ls.saved_at, ls.private_notes, ls.rating,
                   p.id as paper_id, p.title, p.abstract, p.publication_year, p.doi, p.arxiv_id, p.venue,
                   p.citation_count, t.name as topic_name, c.title as collection_title,
                   (SELECT COUNT(*) FROM library_saves WHERE paper_id = p.id) as total_saves
            FROM library_saves ls
            JOIN papers p ON ls.paper_id = p.id
            LEFT JOIN topics t ON p.primary_topic_id = t.id
            LEFT JOIN collections c ON ls.collection_id = c.id
            WHERE {where_clause}
            ORDER BY ls.saved_at DESC
            """,
            params
        )
        for r in rows:
            r["authors"] = query_db(
                "SELECT author_name FROM paper_authors WHERE paper_id = ? ORDER BY author_order ASC",
                (r["paper_id"],)
            )
        return rows

    @staticmethod
    def get_user_collections(user_id):
        return query_db(
            """
            SELECT c.*, COUNT(ls.id) as item_count
            FROM collections c
            LEFT JOIN library_saves ls ON c.id = ls.collection_id
            WHERE c.user_id = ?
            GROUP BY c.id
            ORDER BY c.created_at ASC
            """,
            (user_id,)
        )

    @staticmethod
    def create_collection(user_id, title, description="", is_public=1):
        return execute_db(
            "INSERT INTO collections (user_id, title, description, is_public) VALUES (?, ?, ?, ?)",
            (user_id, title.strip(), description.strip(), 1 if is_public else 0)
        )


class PostModel:
    @staticmethod
    def create(user_id, title, content, attached_paper_id=None, primary_topic_id=None, tags=None):
        post_id = execute_db(
            """
            INSERT INTO posts (user_id, title, content, attached_paper_id, primary_topic_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, title.strip(), content.strip(), attached_paper_id, primary_topic_id)
        )
        if tags:
            for tag in tags:
                clean_tag = tag.strip().lstrip("#")
                if clean_tag:
                    execute_db(
                        "INSERT INTO post_tags (post_id, tag_name) VALUES (?, ?)",
                        (post_id, clean_tag)
                    )
        return post_id

    @staticmethod
    def get_by_id(post_id, current_user_id=None):
        post = query_db(
            """
            SELECT p.*, u.username, u.full_name, u.role as user_role, d.code as department_code,
                   paper.title as attached_paper_title, paper.publication_year as attached_paper_year,
                   t.name as topic_name
            FROM posts p
            JOIN users u ON p.user_id = u.id
            LEFT JOIN departments d ON u.department_id = d.id
            LEFT JOIN papers paper ON p.attached_paper_id = paper.id
            LEFT JOIN topics t ON p.primary_topic_id = t.id
            WHERE p.id = ?
            """,
            (post_id,),
            one=True
        )
        if not post:
            return None
        post["tags"] = [r["tag_name"] for r in query_db("SELECT tag_name FROM post_tags WHERE post_id = ?", (post_id,))]
        
        # User vote
        if current_user_id:
            user_vote = query_db(
                "SELECT vote_value FROM post_votes WHERE post_id = ? AND user_id = ?",
                (post_id, current_user_id),
                one=True
            )
            post["user_vote"] = user_vote["vote_value"] if user_vote else 0
        else:
            post["user_vote"] = 0

        # Comments
        comments = query_db(
            """
            SELECT c.*, u.username, u.full_name, u.role as user_role
            FROM post_comments c
            JOIN users u ON c.user_id = u.id
            WHERE c.post_id = ?
            ORDER BY c.created_at ASC
            """,
            (post_id,)
        )
        # Nest threaded comments
        comment_dict = {}
        top_level = []
        for c in comments:
            c["replies"] = []
            comment_dict[c["id"]] = c
            if c["parent_comment_id"] is None or c["parent_comment_id"] not in comment_dict:
                top_level.append(c)
            else:
                comment_dict[c["parent_comment_id"]]["replies"].append(c)
        post["comments"] = top_level
        return post

    @staticmethod
    def get_feed(current_user_id=None, feed_type="all", limit=30, offset=0):
        where_sql = "1=1"
        params = []

        if feed_type == "following" and current_user_id:
            following_ids = UserModel.get_following_ids(current_user_id)
            if not following_ids:
                return []
            placeholders = ",".join("?" for _ in following_ids)
            where_sql = f"p.user_id IN ({placeholders})"
            params.extend(following_ids)

        params.extend([limit, offset])
        posts = query_db(
            f"""
            SELECT p.*, u.username, u.full_name, u.role as user_role, d.code as department_code,
                   paper.title as attached_paper_title, t.name as topic_name
            FROM posts p
            JOIN users u ON p.user_id = u.id
            LEFT JOIN departments d ON u.department_id = d.id
            LEFT JOIN papers paper ON p.attached_paper_id = paper.id
            LEFT JOIN topics t ON p.primary_topic_id = t.id
            WHERE {where_sql}
            ORDER BY p.is_pinned DESC, p.created_at DESC
            LIMIT ? OFFSET ?
            """,
            params
        )
        for post in posts:
            post["tags"] = [r["tag_name"] for r in query_db("SELECT tag_name FROM post_tags WHERE post_id = ?", (post["id"],))]
            if current_user_id:
                uv = query_db("SELECT vote_value FROM post_votes WHERE post_id = ? AND user_id = ?", (post["id"], current_user_id), one=True)
                post["user_vote"] = uv["vote_value"] if uv else 0
            else:
                post["user_vote"] = 0
        return posts

    @staticmethod
    def vote(user_id, post_id, vote_value):
        # vote_value: 1 or -1
        existing = query_db("SELECT id, vote_value FROM post_votes WHERE post_id = ? AND user_id = ?", (post_id, user_id), one=True)
        if existing:
            if existing["vote_value"] == vote_value:
                # toggle off
                execute_db("DELETE FROM post_votes WHERE id = ?", (existing["id"],))
                diff = -vote_value
            else:
                execute_db("UPDATE post_votes SET vote_value = ? WHERE id = ?", (vote_value, existing["id"]))
                diff = 2 * vote_value
        else:
            execute_db("INSERT INTO post_votes (post_id, user_id, vote_value) VALUES (?, ?, ?)", (post_id, user_id, vote_value))
            diff = vote_value
        
        execute_db("UPDATE posts SET upvote_count = upvote_count + ? WHERE id = ?", (diff, post_id))
        return query_db("SELECT upvote_count FROM posts WHERE id = ?", (post_id,), one=True)["upvote_count"]

    @staticmethod
    def add_comment(user_id, post_id, content, parent_comment_id=None):
        comment_id = execute_db(
            """
            INSERT INTO post_comments (post_id, user_id, parent_comment_id, content)
            VALUES (?, ?, ?, ?)
            """,
            (post_id, user_id, parent_comment_id, content.strip())
        )
        execute_db("UPDATE posts SET comment_count = comment_count + 1 WHERE id = ?", (post_id,))
        return comment_id


class ActivityLogger:
    @staticmethod
    def log(user_id, event_type, target_type=None, target_id=None, metadata=None):
        meta_str = json.dumps(metadata) if metadata else None
        execute_db(
            """
            INSERT INTO activity_events (user_id, event_type, target_type, target_id, metadata_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, event_type, target_type, target_id, meta_str)
        )
