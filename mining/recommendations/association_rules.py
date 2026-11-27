"""
Association Rule Mining for Academic Co-Saving Patterns using FP-Growth (MLxtend).
Powers: "Members who saved this paper also saved..."
"""

import pandas as pd
from app.models.db import query_db

class FPGrowthCoSaveRecommender:
    def __init__(self, min_support=0.04, min_confidence=0.35):
        self.min_support = min_support
        self.min_confidence = min_confidence
        self.rules = None
        self._mine_rules()

    def _mine_rules(self):
        """Mines association rules from user save baskets using MLxtend FP-Growth."""
        try:
            from mlxtend.frequent_patterns import fpgrowth, association_rules
            from mlxtend.preprocessing import TransactionEncoder

            saves = query_db("SELECT user_id, paper_id FROM library_saves ORDER BY user_id")
            if not saves:
                return

            # Group papers by user into baskets
            baskets = {}
            for r in saves:
                uid = r["user_id"]
                pid = r["paper_id"]
                if uid not in baskets:
                    baskets[uid] = []
                baskets[uid].append(str(pid))

            transactions = list(baskets.values())
            if len(transactions) < 5:
                return

            # One-hot encode transactions
            te = TransactionEncoder()
            te_ary = te.fit(transactions).transform(transactions)
            df = pd.DataFrame(te_ary, columns=te.columns_)

            # Mine pairwise frequent itemsets with FP-Growth (max_len=2 for fast pairwise rules)
            frequent_itemsets = fpgrowth(df, min_support=self.min_support, max_len=2, use_colnames=True)
            if frequent_itemsets.empty:
                return

            # Generate association rules
            rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=self.min_confidence)
            if not rules.empty:
                rules["antecedent_len"] = rules["antecedents"].apply(lambda x: len(x))
                # Focus on 1-to-1 rules for item-to-item recommendations
                self.rules = rules[rules["antecedent_len"] == 1].copy()
                self.rules["antecedent_id"] = self.rules["antecedents"].apply(lambda x: int(list(x)[0]))
                self.rules["consequent_id"] = self.rules["consequents"].apply(lambda x: int(list(x)[0]))
                self.rules.sort_values(by=["confidence", "lift"], ascending=False, inplace=True)
        except Exception as e:
            print(f"[WARN] Error in FP-Growth mining: {e}")
            self.rules = None

    def get_related_papers(self, paper_id, top_n=5):
        """
        Return papers co-saved with paper_id based on mined association rules.
        """
        if self.rules is None or self.rules.empty:
            return self._heuristic_fallback(paper_id, top_n)

        matches = self.rules[self.rules["antecedent_id"] == int(paper_id)]
        if matches.empty:
            return self._heuristic_fallback(paper_id, top_n)

        results = []
        for _, r in matches.head(top_n).iterrows():
            target_pid = int(r["consequent_id"])
            p = query_db("SELECT id as paper_id, title, publication_year, venue FROM papers WHERE id = ?", (target_pid,), one=True)
            if p:
                conf = float(r["confidence"])
                lift = float(r["lift"])
                results.append({
                    "paper_id": p["paper_id"],
                    "title": p["title"],
                    "publication_year": p["publication_year"],
                    "venue": p["venue"],
                    "confidence": round(conf, 3),
                    "lift": round(lift, 2),
                    "explanation": f"FP-Growth Rule: {int(conf*100)}% of researchers who saved this also saved this paper (Lift: {lift:.1f}x)."
                })

        return results if results else self._heuristic_fallback(paper_id, top_n)

    def _heuristic_fallback(self, paper_id, top_n=5):
        """Co-occurrence fallback when support threshold is sparse."""
        rows = query_db(
            """
            SELECT s2.paper_id, p.title, p.publication_year, p.venue, COUNT(*) as co_saves
            FROM library_saves s1
            JOIN library_saves s2 ON s1.user_id = s2.user_id AND s1.paper_id != s2.paper_id
            JOIN papers p ON s2.paper_id = p.id
            WHERE s1.paper_id = ?
            GROUP BY s2.paper_id, p.title, p.publication_year, p.venue
            ORDER BY co_saves DESC
            LIMIT ?
            """,
            (paper_id, top_n)
        )
        results = []
        for r in rows:
            results.append({
                "paper_id": r["paper_id"],
                "title": r["title"],
                "publication_year": r["publication_year"],
                "venue": r["venue"],
                "confidence": round(min(r["co_saves"] * 0.12, 0.95), 2),
                "lift": round(1.2 + r["co_saves"] * 0.1, 1),
                "explanation": f"Members who saved this also saved this work (Co-saved by {r['co_saves']} colleagues)."
            })
        return results

_FP_GROWTH_ENGINE = None

def get_fp_growth_engine():
    global _FP_GROWTH_ENGINE
    if _FP_GROWTH_ENGINE is None:
        _FP_GROWTH_ENGINE = FPGrowthCoSaveRecommender()
    return _FP_GROWTH_ENGINE

def get_also_saved_recommendations(paper_id, top_n=5):
    engine = get_fp_growth_engine()
    return engine.get_related_papers(paper_id, top_n=top_n)
