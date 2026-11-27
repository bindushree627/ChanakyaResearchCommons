"""
Keyword Retrieval Engine using Normalized TF-IDF and Inverted Token Scoring.
Provides exact term, acronym, author token, and Boolean-weighted lexical search.
"""

import math
import re
from collections import defaultdict
from app.models.db import query_db

def tokenize(text):
    """Lowercases and extracts alphanumeric word tokens."""
    if not text:
        return []
    return re.findall(r"\b[a-zA-Z0-9]{2,}\b", text.lower())

class BM25KeywordSearcher:
    def __init__(self, k1=1.5, b=0.75):
        self.k1 = k1
        self.b = b
        self.doc_len = {}
        self.avg_doc_len = 0.0
        self.doc_freq = defaultdict(int)
        self.inverted_index = defaultdict(list)
        self.corpus_size = 0
        self._build_index()

    def _build_index(self):
        """Build in-memory BM25 index over all papers in database."""
        papers = query_db("SELECT id, title, abstract FROM papers")
        self.corpus_size = len(papers)
        if self.corpus_size == 0:
            return

        total_len = 0
        for p in papers:
            doc_id = p["id"]
            # Weight title 2x in keyword index
            tokens = tokenize(p["title"]) * 2 + tokenize(p["abstract"] or "")
            self.doc_len[doc_id] = len(tokens)
            total_len += len(tokens)

            tf = defaultdict(int)
            for t in tokens:
                tf[t] += 1

            for term, count in tf.items():
                self.doc_freq[term] += 1
                self.inverted_index[term].append((doc_id, count))

        self.avg_doc_len = total_len / self.corpus_size if self.corpus_size > 0 else 1.0

    def search(self, query_text, top_k=50):
        """
        Calculate Okapi BM25 score for query terms.
        Returns list of (doc_id, score) sorted descending.
        """
        tokens = tokenize(query_text)
        if not tokens or self.corpus_size == 0:
            return []

        scores = defaultdict(float)
        for term in tokens:
            if term not in self.doc_freq:
                continue
            df = self.doc_freq[term]
            # Standard Lucene/BM25 IDF
            idf = math.log((self.corpus_size - df + 0.5) / (df + 0.5) + 1.0)

            for doc_id, tf in self.inverted_index[term]:
                dl = self.doc_len[doc_id]
                numerator = tf * (self.k1 + 1.0)
                denominator = tf + self.k1 * (1.0 - self.b + self.b * (dl / self.avg_doc_len))
                scores[doc_id] += idf * (numerator / denominator)

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]

# Cached singleton index
_KEYWORD_SEARCHER = None

def get_keyword_searcher():
    global _KEYWORD_SEARCHER
    if _KEYWORD_SEARCHER is None:
        _KEYWORD_SEARCHER = BM25KeywordSearcher()
    return _KEYWORD_SEARCHER

def search_papers_keyword(query_text, top_k=50):
    searcher = get_keyword_searcher()
    return searcher.search(query_text, top_k=top_k)
