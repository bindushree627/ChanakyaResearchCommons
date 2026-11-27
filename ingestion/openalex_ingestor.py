"""
OpenAlex Scholarly Ingestion Service.
Fetches academic works, stores raw immutable JSON, normalizes schema, and updates database.
"""

import json
import time
from datetime import datetime
from pathlib import Path
import requests

from app.config import Config
from app.models.db import query_db, execute_db
from ingestion.normalizer import clean_text, normalize_title, extract_doi
from mining.embeddings import generate_embedding

RAW_DIR = Config.RAW_DATA_DIR / "openalex"
RAW_DIR.mkdir(parents=True, exist_ok=True)

def fetch_openalex_works(query="data mining", per_page=15, mailto="research@chanakya.ac.in"):
    """
    Fetch works from OpenAlex API and archive raw response.
    Returns parsed list of normalized paper dictionaries.
    """
    endpoint = f"{Config.OPENALEX_API_URL}/works"
    params = {
        "search": query,
        "per-page": per_page,
        "mailto": mailto,
        "filter": "has_abstract:true"
    }

    timestamp = int(time.time())
    raw_file = RAW_DIR / f"openalex_{query.replace(' ', '_')}_{timestamp}.json"

    try:
        response = requests.get(endpoint, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        # Archive raw immutable payload
        with open(raw_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        results = data.get("results", [])
        parsed_papers = []

        for item in results:
            title = clean_text(item.get("display_name", ""))
            if not title:
                continue

            # Reconstruct abstract from inverted index
            abstract = ""
            inv_idx = item.get("abstract_inverted_index")
            if inv_idx:
                word_positions = []
                for word, positions in inv_idx.items():
                    for pos in positions:
                        word_positions.append((pos, word))
                word_positions.sort(key=lambda x: x[0])
                abstract = " ".join([w[1] for w in word_positions])

            doi = extract_doi(item.get("doi"))
            pub_year = item.get("publication_year")
            venue_obj = item.get("primary_location", {}).get("source") or {}
            venue = venue_obj.get("display_name", "Academic Conference / Journal")
            citations = item.get("cited_by_count", 0)
            openalex_id = item.get("id", "")

            # Authors
            authors = []
            for authorship in item.get("authorships", []):
                author_name = authorship.get("author", {}).get("display_name", "")
                affils = authorship.get("institutions", [])
                affil_name = affils[0].get("display_name", "") if affils else ""
                if author_name:
                    authors.append({
                        "name": author_name,
                        "affiliation": affil_name
                    })

            parsed_papers.append({
                "title": title,
                "clean_title": normalize_title(title),
                "abstract": abstract,
                "publication_year": pub_year,
                "doi": doi,
                "arxiv_id": None,
                "venue": venue,
                "citation_count": citations,
                "source_name": "OpenAlex",
                "external_id": openalex_id,
                "landing_url": item.get("primary_location", {}).get("landing_page_url") or f"https://openalex.org/{openalex_id}",
                "pdf_url": item.get("primary_location", {}).get("pdf_url"),
                "raw_file": str(raw_file),
                "authors": authors
            })

        return parsed_papers

    except Exception as e:
        print(f"[WARN] OpenAlex Ingestion Exception: {e}")
        return []

def ingest_openalex_papers(query="data mining", per_page=15):
    """Fetch, deduplicate, generate embeddings, and persist OpenAlex papers."""
    papers = fetch_openalex_works(query=query, per_page=per_page)
    inserted_count = 0
    updated_count = 0

    for p in papers:
        # Deduplication check: 1. By DOI, 2. By clean_title
        existing = None
        if p["doi"]:
            existing = query_db("SELECT id FROM papers WHERE doi = ?", (p["doi"],), one=True)
        if not existing:
            existing = query_db("SELECT id FROM papers WHERE clean_title = ?", (p["clean_title"],), one=True)

        if existing:
            paper_id = existing["id"]
            # Add new source link if not present
            execute_db(
                "INSERT INTO paper_sources (paper_id, source_name, external_id, landing_url, pdf_url, raw_payload_path) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (paper_id, source_name, external_id) DO NOTHING",
                (paper_id, p["source_name"], p["external_id"], p["landing_url"], p["pdf_url"], p["raw_file"])
            )
            updated_count += 1
        else:
            # Generate semantic vector
            full_text = f"{p['title']}. {p['abstract']}"
            emb = generate_embedding(full_text)
            emb_json = json.dumps(emb)

            paper_id = execute_db(
                """
                INSERT INTO papers (title, clean_title, abstract, publication_year, doi, venue, citation_count, embedding_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (p["title"], p["clean_title"], p["abstract"], p["publication_year"], p["doi"], p["venue"], p["citation_count"], emb_json)
            )

            # Authors
            for idx, a in enumerate(p["authors"], start=1):
                execute_db(
                    "INSERT INTO paper_authors (paper_id, author_name, normalized_name, affiliation, author_order) VALUES (?, ?, ?, ?, ?)",
                    (paper_id, a["name"], a["name"], a["affiliation"], idx)
                )

            # Sources
            execute_db(
                "INSERT INTO paper_sources (paper_id, source_name, external_id, landing_url, pdf_url, raw_payload_path) VALUES (?, ?, ?, ?, ?, ?)",
                (paper_id, p["source_name"], p["external_id"], p["landing_url"], p["pdf_url"], p["raw_file"])
            )
            inserted_count += 1

    return {"fetched": len(papers), "inserted": inserted_count, "merged_duplicates": updated_count}
