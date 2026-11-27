"""
Author Entity Resolution & Disambiguation Module.
Standardizes academic author names using Jaro-Winkler distance and canonical normalization.
"""

import re
from app.models.db import query_db

def jaro_distance(s1, s2):
    """Calculates Jaro similarity metric [0.0 - 1.0]."""
    if s1 == s2:
        return 1.0
    len1, len2 = len(s1), len(s2)
    if len1 == 0 or len2 == 0:
        return 0.0

    match_bound = max(len1, len2) // 2 - 1
    matches1 = [False] * len1
    matches2 = [False] * len2

    matches = 0
    for i in range(len1):
        start = max(0, i - match_bound)
        end = min(i + match_bound + 1, len2)
        for j in range(start, end):
            if not matches2[j] and s1[i] == s2[j]:
                matches1[i] = True
                matches2[j] = True
                matches += 1
                break

    if matches == 0:
        return 0.0

    # Count transpositions
    transpositions = 0
    k = 0
    for i in range(len1):
        if matches1[i]:
            while not matches2[k]:
                k += 1
            if s1[i] != s2[k]:
                transpositions += 1
            k += 1

    transpositions = transpositions // 2
    return (matches / len1 + matches / len2 + (matches - transpositions) / matches) / 3.0

def jaro_winkler_similarity(s1, s2, prefix_scale=0.10):
    """Calculates Jaro-Winkler similarity with common prefix bonus."""
    jaro = jaro_distance(s1, s2)
    if jaro < 0.70:
        return jaro

    prefix = 0
    for i in range(min(len(s1), len(s2), 4)):
        if s1[i] == s2[i]:
            prefix += 1
        else:
            break

    return jaro + prefix * prefix_scale * (1.0 - jaro)

def are_authors_equivalent(name1, name2, threshold=0.88):
    """
    Evaluates whether two author string variants refer to the same researcher.
    Handles 'First Last', 'Last, First', and 'F. Last' initials.
    """
    n1 = name1.lower().replace(".", "").replace(",", "").strip()
    n2 = name2.lower().replace(".", "").replace(",", "").strip()

    if n1 == n2:
        return True, 1.0

    toks1 = n1.split()
    toks2 = n2.split()

    if not toks1 or not toks2:
        return False, 0.0

    # If last names match, and first name is initial or match
    last1, last2 = toks1[-1], toks2[-1]
    if last1 == last2:
        first1, first2 = toks1[0], toks2[0]
        if first1 == first2 or first1[0] == first2[0]:
            return True, 0.95

    # Check reversed order: 'sharma anand' vs 'anand sharma'
    rev1 = " ".join(reversed(toks1))
    if rev1 == n2:
        return True, 0.98

    jw = jaro_winkler_similarity(n1, n2)
    return (jw >= threshold), round(jw, 3)

def resolve_all_authors():
    """Groups all database paper authors into resolved canonical clusters."""
    authors = query_db("SELECT DISTINCT author_name, normalized_name, affiliation FROM paper_authors")
    clusters = []

    for a in authors:
        placed = False
        for c in clusters:
            equiv, score = are_authors_equivalent(a["author_name"], c["canonical_name"])
            if equiv:
                c["variants"].append(a["author_name"])
                placed = True
                break
        if not placed:
            clusters.append({
                "canonical_name": a["normalized_name"] or a["author_name"],
                "affiliation": a["affiliation"],
                "variants": [a["author_name"]]
            })

    return clusters
