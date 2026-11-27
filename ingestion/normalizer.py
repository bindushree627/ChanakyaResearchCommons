"""
Data Normalization, Cleaning and Deduplication for External Ingestion Pipeline.
Handles field standardization, author resolution, and missing metadata attribution.
"""

import re
from datetime import datetime

def clean_text(text):
    """Normalize whitespace and strip HTML/XML tags."""
    if not text:
        return ""
    # Strip HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text

def normalize_title(title):
    """Normalize paper title for exact and fuzzy matching."""
    if not title:
        return ""
    clean = clean_text(title)
    # Remove punctuation for matching
    clean = re.sub(r"[^\w\s]", "", clean).lower()
    return re.sub(r"\s+", " ", clean).strip()

def normalize_author_name(name):
    """
    Standardize author names:
    'Anand Sharma' -> 'Sharma, Anand'
    'A. Sharma' -> 'Sharma, A.'
    """
    if not name:
        return ""
    clean = clean_text(name)
    parts = clean.split()
    if len(parts) > 1:
        # e.g. Anand Sharma -> canonical: Anand Sharma, inverted: Sharma, Anand
        return f"{parts[-1]}, {' '.join(parts[:-1])}"
    return clean

def extract_arxiv_id(raw_id_or_url):
    """Extract clean arXiv identifier from URL or raw string."""
    if not raw_id_or_url:
        return None
    match = re.search(r"(\d{4}\.\d{4,5}(?:v\d+)?)", raw_id_or_url)
    if match:
        return match.group(1)
    return raw_id_or_url.strip()

def extract_doi(raw_doi_or_url):
    """Extract clean DOI string."""
    if not raw_doi_or_url:
        return None
    match = re.search(r"(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)", raw_doi_or_url)
    if match:
        return match.group(1)
    return raw_doi_or_url.strip()
