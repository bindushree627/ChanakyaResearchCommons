"""
Comprehensive Automated Test Suite for Chanakya Research Commons.
Validates all 9 functional subsystems, intelligent algorithms, and analytics warehouse.
"""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.models.db import query_db, execute_db
from app.models.entities import UserModel, PaperModel, LibraryModel, PostModel
from mining.search.hybrid_ranker import execute_unified_search
from mining.duplicate_detection.paper_dedup import are_papers_duplicate, detect_all_duplicates
from mining.recommendations.content_based import recommend_papers_content_based, get_cold_start_recommendations
from mining.recommendations.collaborative import recommend_papers_collaborative
from mining.recommendations.association_rules import get_also_saved_recommendations
from mining.trends.sliding_window import compute_sliding_window_trends
from mining.anomaly_detection.spam_detector import detect_spam_accounts
from mining.rag.generator import generate_rag_answer
from analytics.queries import get_overall_summary, drill_down_analytics
from ingestion.normalizer import extract_doi, extract_arxiv_id, normalize_title

class TestChanakyaCommons(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app("testing")
        cls.client = cls.app.test_client()

    # 1. Registration & Login (F1)
    def test_01_registration_and_authentication(self):
        import time
        ts = int(time.time() * 1000) % 100000
        username = f"test.evaluator_{ts}"
        email = f"test.evaluator_{ts}@chanakya.ac.in"
        user = UserModel.create(username, email, "Pass@12345", "Test Evaluator", role="Student")
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], username)

        # Authenticate
        auth_user = UserModel.authenticate(username, "Pass@12345")
        self.assertIsNotNone(auth_user)
        self.assertEqual(auth_user["id"], user["id"])

        # Bad password
        bad_user = UserModel.authenticate(username, "WrongPassword")
        self.assertIsNone(bad_user)

    # 2. User Permissions & RBAC (F1)
    def test_02_rbac_permissions(self):
        admin = query_db("SELECT id, role FROM users WHERE role = 'Admin' LIMIT 1", one=True)
        student = query_db("SELECT id, role FROM users WHERE role = 'Student' LIMIT 1", one=True)
        self.assertIsNotNone(admin)
        self.assertEqual(admin["role"], "Admin")
        self.assertEqual(student["role"], "Student")

    # 3. Posts & Discussions (F2)
    def test_03_creating_posts(self):
        user = query_db("SELECT id FROM users LIMIT 1", one=True)
        post_id = PostModel.create(
            user_id=user["id"],
            title="Automated Test Discussion on Distributed Systems",
            content="Testing discussion pipeline and attachment mechanism.",
            tags=["distributed", "testing"]
        )
        self.assertIsNotNone(post_id)
        post = PostModel.get_by_id(post_id)
        self.assertEqual(post["title"], "Automated Test Discussion on Distributed Systems")
        self.assertIn("distributed", post["tags"])

    # 4. Comments & Votes (F2)
    def test_04_comments_and_votes(self):
        user = query_db("SELECT id FROM users LIMIT 1", one=True)
        # Create dedicated post for voting test
        post_id = PostModel.create(
            user_id=user["id"],
            title="Post for Vote and Comment Testing",
            content="Testing upvote counting and comments."
        )

        # Vote
        new_votes = PostModel.vote(user["id"], post_id, 1)
        self.assertEqual(new_votes, 1)

        # Comment
        comment_id = PostModel.add_comment(user["id"], post_id, "Automated test comment reply.")
        self.assertIsNotNone(comment_id)
        post = PostModel.get_by_id(post_id)
        self.assertEqual(post["comment_count"], 1)

    # 5. Shared Research Library & Saves (F3)
    def test_05_saving_papers(self):
        user = query_db("SELECT id FROM users LIMIT 1", one=True)
        paper = query_db("SELECT id FROM papers LIMIT 1", one=True)

        save_id = LibraryModel.save_paper(
            user_id=user["id"],
            paper_id=paper["id"],
            private_notes="Key paper to review for capstone.",
            rating=5
        )
        self.assertIsNotNone(save_id)
        self.assertTrue(PaperModel.is_saved_by_user(user["id"], paper["id"]))

    # 6. External Normalizer & Ingestion Parsing (F4)
    def test_06_ingestion_normalizer(self):
        doi_raw = "https://doi.org/10.1145/3448016.3452841"
        self.assertEqual(extract_doi(doi_raw), "10.1145/3448016.3452841")

        arxiv_raw = "https://arxiv.org/abs/2401.12345v2"
        self.assertEqual(extract_arxiv_id(arxiv_raw), "2401.12345v2")

        title_raw = "Attention Mechanisms for Vision Transformers: An Overview!"
        self.assertEqual(normalize_title(title_raw), "attention mechanisms for vision transformers an overview")

    # 7. Unified 4-Panel Hybrid Search (F5)
    def test_07_unified_search(self):
        res = execute_unified_search("vision transformer attention", top_k=5)
        self.assertIn("panel_papers", res)
        self.assertIn("panel_library", res)
        self.assertIn("panel_members", res)
        self.assertIn("panel_posts", res)
        self.assertTrue(len(res["panel_papers"]) > 0)

    # 8. Duplicate Detection (F5)
    def test_08_duplicate_detection(self):
        p1 = {"title": "Attention Mechanisms for Deep Learning", "clean_title": "attention mechanisms for deep learning", "doi": "10.1145/test.1", "arxiv_id": "2401.1001"}
        p2 = {"title": "ATTENTION MECHANISMS FOR DEEP LEARNING", "clean_title": "attention mechanisms for deep learning", "doi": "10.1145/test.1", "arxiv_id": "2401.1001v2"}
        is_dup, conf, reason = are_papers_duplicate(p1, p2)
        self.assertTrue(is_dup)
        self.assertTrue(conf >= 0.90)

    # 9. Recommendation Systems (F6)
    def test_09_recommendations(self):
        user = query_db("SELECT id FROM users WHERE is_spam_flagged = 0 LIMIT 1", one=True)
        cb_recs = recommend_papers_content_based(user["id"], top_n=5)
        self.assertTrue(len(cb_recs) > 0)
        self.assertIn("score", cb_recs[0])

        cf_recs = recommend_papers_collaborative(user["id"], top_n=5)
        self.assertIsInstance(cf_recs, list)

        also_saved = get_also_saved_recommendations(1, top_n=3)
        self.assertIsInstance(also_saved, list)

    # 10. Sliding-Window Trend Detection (F7)
    def test_10_trend_detection(self):
        trends = compute_sliding_window_trends(window_days=14, baseline_days=45, z_threshold=1.4)
        self.assertTrue(len(trends) > 0)
        self.assertIn("z_score", trends[0])
        # Verify Quantum Machine Learning spike was detected
        qml_trend = next((t for t in trends if t["topic_name"] == "Quantum Machine Learning"), None)
        self.assertIsNotNone(qml_trend)
        self.assertTrue(qml_trend["is_spike"])

    # 11. Spam & Anomaly Detection (F7)
    def test_11_spam_detection(self):
        flagged = detect_spam_accounts()
        self.assertTrue(len(flagged) >= 5)
        # Verify planted bot account was caught
        bot = next((u for u in flagged if "promo99" in u["username"] or "sellpapers" in u["username"] or u["is_planted_spam"]), None)
        self.assertIsNotNone(bot)

    # 12. Research Assistant RAG Pipeline (F8)
    def test_12_rag_research_assistant(self):
        q = "How do attention mechanisms enhance vision transformers?"
        res = generate_rag_answer(q, top_passages=3)
        self.assertIsNotNone(res["answer"])
        self.assertTrue(len(res["citations"]) > 0)
        self.assertTrue(len(res["source_passages"]) > 0)
        self.assertEqual(res["groundedness_score"], 1.0)

    # 13. DuckDB Star Schema Analytics Queries (F9)
    def test_13_duckdb_analytics(self):
        summary = get_overall_summary()
        self.assertTrue(summary["total_events"] > 10000)
        self.assertTrue(summary["active_departments"] >= 6)

        drill = drill_down_analytics(department_code="CSE")
        self.assertEqual(drill["level"], "department")

if __name__ == "__main__":
    unittest.main()
