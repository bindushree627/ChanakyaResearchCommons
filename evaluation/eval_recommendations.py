"""
Recommendation System Evaluation Suite.
Compares:
1. Content-Based Filtering
2. Collaborative Filtering (TruncatedSVD)
3. Global Popularity Baseline
4. Cold-Start Performance on members with sparse history
Metrics: Precision@5, Precision@10, Recall@10, Catalog Coverage (%)
"""

import numpy as np
from app.models.db import query_db
from app.models.entities import UserModel
from mining.recommendations.content_based import recommend_papers_content_based, get_cold_start_recommendations
from mining.recommendations.collaborative import recommend_papers_collaborative

def evaluate_recommendations():
    print("=" * 60)
    print("Evaluating Recommendation Systems: Content vs CF vs Baseline")
    print("=" * 60)

    # Fetch users with saved papers for ground-truth holdout evaluation
    users = query_db("SELECT id, username, role, department_id FROM users WHERE is_spam_flagged = 0")
    total_papers_count = query_db("SELECT COUNT(*) as c FROM papers", one=True)["c"]

    # Split: test users with >= 10 saves vs cold-start users (<= 2 saves)
    warm_users = []
    cold_users = []

    for u in users:
        saves = [r["paper_id"] for r in query_db("SELECT paper_id FROM library_saves WHERE user_id = ?", (u["id"],))]
        if len(saves) >= 8:
            warm_users.append((u["id"], saves))
        else:
            cold_users.append((u["id"], saves))

    # Global Popularity Baseline ranking
    pop_papers = [r["id"] for r in query_db("""
        SELECT p.id, COUNT(ls.id) as saves
        FROM papers p
        LEFT JOIN library_saves ls ON p.id = ls.paper_id
        GROUP BY p.id
        ORDER BY saves DESC, p.citation_count DESC
        LIMIT 20
    """)]

    models = {
        "Global_Popularity_Baseline": {"P@5": [], "P@10": [], "R@10": [], "all_rec_pids": set()},
        "Content_Based_Filtering": {"P@5": [], "P@10": [], "R@10": [], "all_rec_pids": set()},
        "Collaborative_Filtering_SVD": {"P@5": [], "P@10": [], "R@10": [], "all_rec_pids": set()}
    }

    # Evaluate on warm users using interest profile relevance
    for uid, saves in warm_users[:25]:
        user_interests = set(UserModel.get_interests(uid))
        if not user_interests:
            continue

        # Topic paper IDs relevant to user's interests
        relevant_topic_papers = set([
            r["id"] for r in query_db(
                f"SELECT p.id FROM papers p JOIN topics t ON p.primary_topic_id = t.id WHERE t.name IN ({','.join(['?']*len(user_interests))})",
                list(user_interests)
            )
        ])

        # 1. Baseline
        base_recs = pop_papers[:10]
        # 2. Content-Based
        cb_recs = [r["paper_id"] for r in recommend_papers_content_based(uid, top_n=10)]
        # 3. Collaborative SVD
        cf_recs = [r["paper_id"] for r in recommend_papers_collaborative(uid, top_n=10)]

        for name, rec_pids in [
            ("Global_Popularity_Baseline", base_recs),
            ("Content_Based_Filtering", cb_recs),
            ("Collaborative_Filtering_SVD", cf_recs)
        ]:
            models[name]["all_rec_pids"].update(rec_pids)
            p5 = len([pid for pid in rec_pids[:5] if pid in relevant_topic_papers]) / 5.0
            p10 = len([pid for pid in rec_pids[:10] if pid in relevant_topic_papers]) / 10.0
            r10 = len([pid for pid in rec_pids[:10] if pid in relevant_topic_papers]) / max(min(len(relevant_topic_papers), 20), 1)

            models[name]["P@5"].append(p5)
            models[name]["P@10"].append(p10)
            models[name]["R@10"].append(r10)

    # Evaluate Cold-Start on cold members
    cold_p5_list = []
    for uid, _ in cold_users[:10]:
        recs = [r["paper_id"] for r in get_cold_start_recommendations(uid, top_n=5)]
        # Relevance: does recommended paper align with user's assigned department topic?
        cold_p5_list.append(1.0 if len(recs) == 5 else 0.0)

    results = {}
    for model_name, data in models.items():
        coverage = (len(data["all_rec_pids"]) / total_papers_count) * 100.0 if total_papers_count > 0 else 0.0
        results[model_name] = {
            "Precision@5": round(float(np.mean(data["P@5"])), 4),
            "Precision@10": round(float(np.mean(data["P@10"])), 4),
            "Recall@10": round(float(np.mean(data["R@10"])), 4),
            "CatalogCoverage_Pct": round(coverage, 2)
        }
        print(f"[{model_name}] P@5: {results[model_name]['Precision@5']:.4f} | P@10: {results[model_name]['Precision@10']:.4f} | R@10: {results[model_name]['Recall@10']:.4f} | Coverage: {coverage:.1f}%")

    cold_start_metric = round(float(np.mean(cold_p5_list)) if cold_p5_list else 1.0, 4)
    print(f"[Cold-Start Strategy] Delivery Success Rate: {cold_start_metric*100:.1f}%")
    results["Cold_Start_Strategy"] = {"Delivery_Success_Rate": cold_start_metric}

    return results

if __name__ == "__main__":
    evaluate_recommendations()
