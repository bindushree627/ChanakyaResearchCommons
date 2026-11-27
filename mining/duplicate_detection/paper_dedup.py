"""
Scholarly Paper Deduplication Engine.
Combines exact identifier matching (DOI, arXiv) with fuzzy title Jaccard & Levenshtein metrics.
"""

import re
from app.models.db import query_db
from ingestion.normalizer import normalize_title

def jaccard_similarity(tokens_a, tokens_b):
    """Compute Jaccard token similarity: |A ∩ B| / |A ∪ B|."""
    set_a = set(tokens_a)
    set_b = set(tokens_b)
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)

def levenshtein_ratio(s1, s2):
    """Normalized edit distance similarity ratio [0.0 - 1.0]."""
    if s1 == s2:
        return 1.0
    if not s1 or not s2:
        return 0.0

    len1, len2 = len(s1), len(s2)
    # Optimized 2-row DP for memory efficiency
    prev_row = list(range(len2 + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1] * (len2 + 1)
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row[j + 1] = min(insertions, deletions, substitutions)
        prev_row = curr_row

    dist = prev_row[len2]
    max_len = max(len1, len2)
    return 1.0 - (dist / max_len)

def are_papers_duplicate(paper_a, paper_b, jaccard_threshold=0.85, levenshtein_threshold=0.88):
    """
    Evaluates whether two paper records represent the same academic work.
    Returns (is_duplicate: bool, confidence: float, match_reason: str).
    """
    # 1. Exact DOI match (or version suffix like _v2 / .ext)
    if paper_a.get("doi") and paper_b.get("doi"):
        clean_doi_a = paper_a["doi"].lower().strip()
        clean_doi_b = paper_b["doi"].lower().strip()
        base_doi_a = clean_doi_a.split("_")[0].split(".ext")[0]
        base_doi_b = clean_doi_b.split("_")[0].split(".ext")[0]
        if clean_doi_a == clean_doi_b:
            return True, 1.0, "Exact DOI Match"
        if base_doi_a == base_doi_b and (len(clean_doi_a) > len(base_doi_a) or len(clean_doi_b) > len(base_doi_b)):
            return True, 0.98, "Versioned DOI Match"

    # 2. Exact arXiv ID match (handling v1/v2/.rev)
    if paper_a.get("arxiv_id") and paper_b.get("arxiv_id"):
        clean_arx_a = paper_a["arxiv_id"].lower().strip()
        clean_arx_b = paper_b["arxiv_id"].lower().strip()
        base_a = clean_arx_a.split("v")[0].split(".rev")[0]
        base_b = clean_arx_b.split("v")[0].split(".rev")[0]
        if clean_arx_a == clean_arx_b:
            return True, 0.99, "Exact arXiv Match"
        if base_a == base_b and (len(clean_arx_a) > len(base_a) or len(clean_arx_b) > len(base_b)):
            return True, 0.98, "Versioned arXiv Match"

    # 3. Clean Title Exact Match
    title_a = normalize_title(paper_a.get("title", ""))
    title_b = normalize_title(paper_b.get("title", ""))
    if title_a and title_a == title_b:
        return True, 0.99, "Exact Title Match"

    # 4. Check for distinct series/phase/part numbers
    nums_a = set(re.findall(r"\b\d+\b", title_a))
    nums_b = set(re.findall(r"\b\d+\b", title_b))
    if nums_a != nums_b:
        return False, 0.0, "Distinct Volume/Phase Number"

    # 5. Fuzzy Token Jaccard + Levenshtein for variations (e.g. 'and' vs '&', extra subtitle)
    toks_a = title_a.split()
    toks_b = title_b.split()
    jaccard = jaccard_similarity(toks_a, toks_b)

    if jaccard >= 0.90:
        lev = levenshtein_ratio(title_a, title_b)
        if lev >= 0.92:
            conf = round((jaccard * 0.5) + (lev * 0.5), 3)
            return True, conf, f"Fuzzy Title Match (Jaccard: {jaccard:.2f}, Lev: {lev:.2f})"

    return False, 0.0, "Distinct Papers"

def detect_all_duplicates(threshold=0.85):
    """
    Scans entire paper repository to identify all duplicate clusters.
    Returns list of duplicate pairs with match evidence.
    """
    papers = query_db("SELECT id, title, clean_title, doi, arxiv_id, publication_year FROM papers")
    duplicates_found = []

    # Partition by publication year or length to avoid O(N^2) explosion
    for i in range(len(papers)):
        for j in range(i + 1, len(papers)):
            p1 = papers[i]
            p2 = papers[j]

            # Fast length filter
            len1, len2 = len(p1["clean_title"]), len(p2["clean_title"])
            if max(len1, len2) > 0 and min(len1, len2) / max(len1, len2) < 0.60:
                continue

            is_dup, conf, reason = are_papers_duplicate(p1, p2, jaccard_threshold=threshold)
            if is_dup:
                duplicates_found.append({
                    "paper_a_id": p1["id"],
                    "paper_a_title": p1["title"],
                    "paper_b_id": p2["id"],
                    "paper_b_title": p2["title"],
                    "confidence": conf,
                    "reason": reason
                })

    return duplicates_found
