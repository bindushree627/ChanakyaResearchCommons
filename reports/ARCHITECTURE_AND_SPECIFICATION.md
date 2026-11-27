# CHANAKYA RESEARCH COMMONS — SYSTEM ARCHITECTURE & TECHNICAL SPECIFICATION
**Course**: V Semester B.Tech Data Mining & Warehousing (2026–27)  
**Institution**: Chanakya University, Bangalore  
**Submission Deadline**: 28 November 2026  
**Author**: Engineering Team (Senior Full-Stack & Data Mining Architect)

---

## 1. System Architecture Overview

Chanakya Research Commons is designed using a multi-tier, data-centric architecture separating transactional processing (OLTP), data ingestion & preprocessing (ETL/ELT), intelligent mining & retrieval services, and institutional analytical processing (OLAP).

```
+----------------------------------------------------------------------------------------+
|                                    PRESENTATION TIER                                   |
|   Responsive Academic UI (HTML5, CSS3, Bootstrap 5, Vanilla JS, Chart.js, Feather/FontAwesome)|
|   Unified Navigation: Home | Explore | Library | Community | Recommendations | Assistant | Analytics |
+-------------------------------------------+--------------------------------------------+
                                            | REST / JSON / Server-Rendered Views
+-------------------------------------------v--------------------------------------------+
|                                  APPLICATION BACKEND                                    |
|   Python Flask Application Factory, Blueprint Routers & Session-based RBAC Security     |
|   - auth_routes: Register, Login, Profile, Role-based auth (Student/Faculty/Researcher/Admin)
|   - posts_routes: Research feeds, topic posts, paper attachments, comments, upvotes    |
|   - library_routes: Personal collections, university repository, DOI/arXiv imports, notes |
|   - search_routes: 4-Panel Unified Hybrid Search & entity disambiguation              |
|   - rec_routes: Content, Collaborative & Association Rule Recommendations              |
|   - assistant_routes: RAG Assistant with passage retrieval, citations & extractive fallbacks|
|   - analytics_routes: Institutional Admin Analytics & Dimensional Drill-downs          |
+---------------------+-------------------------------+----------------------------------+
                      |                               |
+---------------------v-------+       +---------------v---------------+
|    MINING & RETRIEVAL       |       |       INGESTION PIPELINE       |
|  - Hybrid Search Engine     |       |  - OpenAlex REST Ingestor      |
|    (BM25 + Dense Cosine)    |       |  - arXiv API XML Ingestor      |
|  - Entity Resolution        |       |  - Incremental Raw JSON Storage|
|    (Jaro-Winkler/Cosine)    |       |  - Deduplication & Normalizer  |
|  - Recommendation Engine    |       +---------------+---------------+
|    (TF-IDF, SVD CF, FP-Grow)|                       |
|  - Sliding-Window Trend Det.|                       |
|  - Isolation Forest/Z-Score |                       |
|    Abnormal/Spam Detection  |                       |
|  - RAG Retrieval & Ranker   |                       |
+---------------------+-------+                       |
                      |                               |
+---------------------v-------------------------------v----------------------------------+
|                                   DATA STORAGE LAYERS                                  |
|                                                                                        |
|  1. OLTP Database (PostgreSQL + pgvector / Dual SQLite-DuckDB Engine for Local Portability)
|     - Normalized 3NF tables: users, departments, papers, library_saves, posts, events  |
|     - 384-dimensional dense semantic vectors (all-MiniLM-L6-v2)                        |
|                                                                                        |
|  2. Raw Storage (data/raw/)                                                            |
|     - Immutable raw API JSON payloads from OpenAlex & arXiv                            |
|                                                                                        |
|  3. Processed Layer (data/processed/)                                                  |
|     - Cleaned, deduplicated, standardized research corpora & evaluation ground truth   |
|                                                                                        |
|  4. Data Warehouse (DuckDB + Parquet: data/warehouse/)                                 |
|     - Star Schema: Fact_Research_Activity, Dim_User, Dim_Department, Dim_Paper, Dim_Time|
|     - Columnar storage for sub-second analytical aggregations and drill-downs          |
+----------------------------------------------------------------------------------------+
```

---

## 2. Technology Justification

| Component | Selected Technology | Technical Justification |
| :--- | :--- | :--- |
| **Backend Framework** | Python 3.13 + Flask 3.1 | Lightweight, modular blueprint architecture; native interoperability with scientific Python libraries (`numpy`, `scipy`, `scikit-learn`, `duckdb`). |
| **Transactional DB** | PostgreSQL + pgvector (with dual-engine local adapter) | ACID compliance for academic users, collections, and library saves; pgvector provides fast $HNSW$ and IVFFlat vector indexing for 384-dim semantic embeddings. |
| **Data Warehouse** | DuckDB + Parquet | In-process vectorized OLAP engine ideal for analytical drill-downs across millions of events; zero network overhead; high compression with Apache Parquet. |
| **Semantic Embedding**| Sentence-Transformers (`all-MiniLM-L6-v2`) | Compact 384-dimensional dense vectors with state-of-the-art semantic sentence clustering; ultra-fast inference on Apple Silicon / CPU. |
| **Data Mining Stack** | Scikit-Learn, MLxtend, NetworkX | Industry-standard implementations of TF-IDF, TruncatedSVD (Collaborative Filtering), FP-Growth (association rules), and graph centrality algorithms for institutional co-authorship. |
| **Frontend Stack** | Bootstrap 5, Modern Vanilla JS, Chart.js | Zero heavyweight node build dependencies; runs reliably anywhere; accessible, responsive academic styling with interactive visualizations. |
| **External Sources** | OpenAlex & arXiv REST APIs | 100% open, high-quality scholarly APIs with zero licensing or subscription cost. |

---

## 3. Database Schema Design (OLTP)

The application relational database contains 18 normalized tables:

1. **`departments`**: `id, code, name, description, faculty_count, created_at`
2. **`users`**: `id, username, email, password_hash, full_name, role (Student/Faculty/Researcher/Admin), department_id, bio, website_url, scholar_url, is_spam_flagged, created_at`
3. **`user_interests`**: `id, user_id, topic_name, weight, created_at`
4. **`user_followers`**: `id, follower_id, following_id, created_at`
5. **`topics`**: `id, name, slug, domain, description, follower_count, post_count, created_at`
6. **`topic_followers`**: `id, user_id, topic_id, created_at`
7. **`papers`**: `id, title, clean_title, abstract, publication_year, doi, arxiv_id, venue, citation_count, primary_topic_id, embedding (384-dim), created_at`
8. **`paper_authors`**: `id, paper_id, author_name, normalized_name, affiliation, author_order`
9. **`paper_sources`**: `id, paper_id, source_name (OpenAlex/arXiv/UserUpload), external_id, landing_url, pdf_url, ingested_at`
10. **`collections`**: `id, user_id, title, description, is_public, created_at`
11. **`library_saves`**: `id, user_id, paper_id, collection_id, private_notes, rating, saved_at`
12. **`posts`**: `id, user_id, title, content, attached_paper_id, primary_topic_id, upvote_count, comment_count, is_pinned, created_at`
13. **`post_tags`**: `id, post_id, tag_name`
14. **`post_comments`**: `id, post_id, user_id, parent_comment_id (threaded), content, created_at`
15. **`post_votes`**: `id, post_id, user_id, vote_value (+1/-1), created_at`
16. **`activity_events`**: `id, user_id, event_type (view_paper, save_paper, search, post, comment, upvote), target_type, target_id, metadata_json, created_at`
17. **`search_history`**: `id, user_id, query_text, result_count, created_at`
18. **`recommendations_cache`**: `id, user_id, rec_type (paper/researcher/item_assoc), item_id, score, explanation, generated_at`

---

## 4. Data Warehouse Dimensional Model (Star Schema)

Stored in DuckDB (`data/warehouse/analytics.duckdb`) and backed by columnar Parquet files (`data/warehouse/*.parquet`):

### Fact Tables:
- **`fact_research_activity`**:
  `activity_key, date_key, user_key, department_key, paper_key, topic_key, event_type_key, duration_seconds, count_event, weight_score`

### Dimension Tables:
- **`dim_time`**:
  `date_key, full_date, day_of_week, day_name, week_of_year, month, month_name, quarter, year, is_academic_session`
- **`dim_user`**:
  `user_key, user_id, username, full_name, role, department_name, seniority_level`
- **`dim_department`**:
  `department_key, department_id, department_code, department_name, faculty_count`
- **`dim_paper`**:
  `paper_key, paper_id, title, publication_year, venue, primary_domain, citation_tier`
- **`dim_topic`**:
  `topic_key, topic_id, topic_name, domain_category`

---

## 5. Directory Structure

```
ChanakyaResearchCommons/
├── app/
│   ├── __init__.py               # Flask app factory, DB initialization, template filters
│   ├── config.py                 # Configuration classes (Dev, Test, Prod)
│   ├── models/                   # Database models & schema definitions
│   │   ├── __init__.py
│   │   ├── entities.py           # User, Paper, Post, Library models
│   │   └── db.py                 # Database connection & dual-engine session adapter
│   ├── routes/                   # HTTP Blueprint controllers
│   │   ├── __init__.py
│   │   ├── auth_routes.py        # F1: Authentication & Profiles
│   │   ├── posts_routes.py       # F2: Posts & Discussions
│   │   ├── library_routes.py     # F3: Shared Research Library
│   │   ├── ingestion_routes.py   # F4: Trigger & monitor ingestion
│   │   ├── search_routes.py      # F5: 4-Panel Unified Search
│   │   ├── rec_routes.py         # F6: Recommendation Engine
│   │   ├── trends_routes.py      # F7: Trends & Anomaly Monitoring
│   │   ├── assistant_routes.py   # F8: Research Assistant RAG
│   │   └── analytics_routes.py   # F9: Institutional Analytics Dashboard
│   ├── services/                 # Core business & data services
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── library_service.py
│   │   ├── feed_service.py
│   │   └── event_service.py
│   ├── static/                   # Static assets
│   │   ├── css/                  # Custom theme, typography & responsive styles
│   │   │   └── chanakya.css
│   │   ├── js/                   # Dynamic search, assistant & chart scripts
│   │   │   ├── main.js
│   │   │   ├── search.js
│   │   │   ├── assistant.js
│   │   │   └── analytics_charts.js
│   │   └── img/                  # Brand logos, icons
│   └── templates/                # Jinja2 HTML templates
│       ├── base.html             # Unified master layout & navigation
│       ├── home.html             # Landing portal & quick stats
│       ├── explore.html          # F5: Unified 4-panel search UI
│       ├── library.html          # F3: Shared research library
│       ├── paper_detail.html     # Single paper detail, sources & notes
│       ├── community.html        # F2: Discussion feed & post creation
│       ├── post_detail.html      # Post threaded comments & discussion
│       ├── recommendations.html  # F6: Personalized recommendation panels
│       ├── assistant.html        # F8: RAG Assistant interactive chat
│       ├── analytics.html        # F9: Institutional Admin Analytics
│       ├── profile.html          # F1: Member profile, interests & collections
│       ├── settings.html         # User preferences & tag management
│       ├── login.html            # Sign-in
│       ├── register.html         # Sign-up
│       └── evaluation.html       # Evaluation results & benchmark dashboard
├── data/
│   ├── raw/                      # Raw immutable API payloads
│   ├── processed/                # Normalized JSON & CSV data
│   ├── warehouse/                # DuckDB database & Parquet star schema
│   └── synthetic/                # Synthetic generator outputs & ground truths
├── ingestion/                    # External ETL pipelines (F4)
│   ├── __init__.py
│   ├── openalex_ingestor.py     # OpenAlex API client & parser
│   ├── arxiv_ingestor.py         # arXiv API XML client & parser
│   ├── normalizer.py             # Schema normalization & deduplication
│   └── pipeline.py               # Orchestrator for scheduled/incremental ingestion
├── mining/                       # Intelligent Algorithms (F5 - F8)
│   ├── __init__.py
│   ├── embeddings.py             # SentenceTransformers embedding generator & cosine cache
│   ├── search/                   # F5: Unified Hybrid Search
│   │   ├── __init__.py
│   │   ├── keyword_search.py     # BM25 / TF-IDF ranker
│   │   ├── semantic_search.py    # Vector similarity search
│   │   └── hybrid_ranker.py      # Reciprocal Rank Fusion & score normalization
│   ├── duplicate_detection/      # Paper deduplication & entity resolution
│   │   ├── __init__.py
│   │   ├── paper_dedup.py        # Title Jaccard + Levenshtein + DOI/arXiv matcher
│   │   └── author_resolution.py  # Author name normalization & Jaro-Winkler clustering
│   ├── recommendations/          # F6: Recommendation Engine
│   │   ├── __init__.py
│   │   ├── content_based.py      # User interest vs Paper cosine similarity
│   │   ├── collaborative.py      # TruncatedSVD Matrix Factorization & item-item CF
│   │   └── association_rules.py  # FP-Growth algorithm (MLxtend) for co-save patterns
│   ├── trends/                   # F7: Topic & Activity Monitoring
│   │   ├── __init__.py
│   │   ├── sliding_window.py     # Z-Score & velocity anomaly detection on topics
│   │   └── spike_detector.py     # Poisson / Moving-average spike alerts
│   ├── anomaly_detection/        # F7: Anti-Spam & Abuse Detection
│   │   ├── __init__.py
│   │   └── spam_detector.py      # Heuristic + Isolation Forest user activity classifier
│   └── rag/                      # F8: Research Assistant RAG
│       ├── __init__.py
│       ├── retriever.py          # Paper abstract & passage chunk retriever
│       ├── ranker.py             # Passage re-ranking by query relevance
│       └── generator.py          # Extractive high-groundedness summarizer + Ollama hook
├── analytics/                    # F9: Institutional Analytics Warehouse
│   ├── __init__.py
│   ├── etl_warehouse.py          # Populates DuckDB star schema from OLTP
│   └── queries.py                # OLAP drill-downs: University -> Dept -> Topic -> Member
├── evaluation/                   # Scientific Algorithm Evaluation (Section 5)
│   ├── __init__.py
│   ├── eval_search.py            # P@5, P@10, R@10, nDCG@10 (Keyword vs Hybrid)
│   ├── eval_duplicate.py         # Precision, Recall, F1 against planted ground truth
│   ├── eval_recommendations.py   # P@K, R@K, Coverage vs Popularity baseline & Cold-start
│   ├── eval_trends.py            # Precision, Recall, F1, Detection delay on planted spikes
│   ├── eval_spam.py              # Confusion matrix, Precision, Recall, F1
│   ├── eval_rag.py               # Retrieval P@K, R@K, Citation Coverage & Groundedness
│   └── run_all_evaluations.py    # Master runner generating JSON/CSV benchmarks
├── database/
│   ├── schema/
│   │   ├── postgres_schema.sql   # PostgreSQL + pgvector DDL schema
│   │   └── sqlite_schema.sql     # Portable local SQLite DDL schema
│   └── seeds/
│       └── initial_departments.json
├── scripts/
│   ├── generate_synthetic_data.py# Reproducible dataset generator (seed=42)
│   ├── init_db.py                # Database initializer & migrator
│   └── run_full_pipeline.sh      # End-to-end setup, ingestion, ETL & benchmark script
├── tests/                        # Automated unit and integration tests
│   ├── test_auth.py
│   ├── test_library.py
│   ├── test_search.py
│   ├── test_recommendations.py
│   ├── test_trends_and_spam.py
│   ├── test_rag.py
│   └── test_analytics.py
├── reports/                      # Evaluation benchmarks, architecture diagrams & final report
│   ├── benchmarks_summary.json
│   ├── evaluation_metrics.csv
│   └── final_project_report.md
├── docker-compose.yml            # Containerized PostgreSQL + pgvector + Flask service
├── Dockerfile                    # Production Docker container
├── requirements.txt              # Pinned Python package dependencies
├── .env.example                  # Environment configuration template
└── README.md                     # Comprehensive academic project documentation
```

---

## 6. Feature-to-Algorithm Mapping

| Subsystem | Core Feature | Algorithm / Mathematical Technique | Justification |
| :--- | :--- | :--- | :--- |
| **F4: Ingestion** | Entity Deduplication | DOI/arXiv Exact Match + Jaccard Normalized Title Similarity ($J(A,B) \ge 0.88$) | Prevents redundant paper ingestion across heterogeneous scholarly APIs. |
| **F5: Search** | Keyword Retrieval | Okapi BM25 / Normalized TF-IDF Term Frequency Inverted Index | Exact terminology, acronyms, and author token retrieval. |
| **F5: Search** | Semantic Retrieval | Dense Vector Cosine Similarity: $\cos(\mathbf{q}, \mathbf{d}) = \frac{\mathbf{q} \cdot \mathbf{d}}{\|\mathbf{q}\|\|\mathbf{d}\|}$ | Captures conceptual semantic relevance even without keyword overlap. |
| **F5: Search** | Hybrid Ranking | Reciprocal Rank Fusion (RRF): $\text{RRF}(d) = \sum_{m \in \{BM25, Dense\}} \frac{1}{60 + \text{rank}_m(d)}$ | Measurable, rank-invariant fusion outperforming raw score summation. |
| **F5: Search** | Author Entity Resolution | Jaro-Winkler Distance ($d_{jw} \ge 0.90$) + Department Affiliation Clustering | Unifies variations like "A. Sharma", "Anand Sharma", "Sharma, A.". |
| **F6: Recommendations** | Personalized Papers | Content-Based Filtering: Cosine similarity between User Interest Profile Vector $\mathbf{u}_i$ and Paper Embedding $\mathbf{p}_j$ | Robust for user-specific research alignment without sparse interaction data. |
| **F6: Recommendations** | Collaborative Papers | TruncatedSVD Matrix Factorization on User-Paper Save Interaction Matrix | Discovers latent research interest communities. |
| **F6: Recommendations** | Co-save Recommendations | FP-Growth Frequent Itemset Mining (MLxtend) to generate Association Rules with $\text{Confidence} \ge 0.40, \text{Lift} > 1.2$ | "Members who saved this also saved..." based on association rule mining. |
| **F6: Recommendations** | Cold-Start Strategy | Departmental Popularity + Primary Topic Heuristic | Guarantees non-empty, high-quality recommendations for day-one members. |
| **F7: Trends** | Topic Spike Detection | Sliding-Window Z-Score Velocity: $Z_t = \frac{v_t - \mu_{w}}{\sigma_{w}}$, alert if $Z_t > 2.5$ | Detects sudden emerging research topics while adjusting for historical variance. |
| **F7: Monitoring** | Spam & Anomaly Detection | Isolation Forest + Activity Rate Outlier Rules (burst posts/comments/saves) | Unsupervised anomaly identification with high recall on planted bot behavior. |
| **F8: Research Assistant**| Context Retrieval & RAG | Top-$K$ Dense Bi-Encoder Retrieval + Maximal Marginal Relevance (MMR) + Extractive Sentence Grounding | Prevents hallucination; guarantees 100% verifiable citations directly to paper abstracts. |
| **F9: Analytics** | Dimensional OLAP | Star Schema aggregation via DuckDB Columnar Vector Execution | Instantaneous roll-ups and drill-downs: University $\to$ Department $\to$ Topic $\to$ Member. |

---

## 7. Evaluation Strategy & Benchmark Metrics

All algorithms are evaluated against planted ground truth labels generated deterministically (Random Seed: 42):

1. **Unified Search Benchmark**:
   - Test queries: 25 representative research queries spanning AI, Data Mining, Networks, Robotics, VLSI, Bioinformatics.
   - Metrics: Precision@5, Precision@10, Recall@10, nDCG@10.
   - Baseline Comparison: Pure Keyword Search (BM25) vs. Pure Semantic Search vs. Hybrid RRF.
2. **Duplicate Detection Benchmark**:
   - Planted: 30 paper duplicate pairs with perturbed titles, alternate casing, and missing DOIs.
   - Metrics: Precision, Recall, F1-Score.
3. **Recommendation Benchmark**:
   - Metrics: Precision@5, Precision@10, Recall@10, Catalog Coverage (%).
   - Comparison: Content-Based Filtering vs. Collaborative Filtering (SVD) vs. FP-Growth vs. Global Popularity Baseline.
   - Cold-Start: Evaluated on test users with $\le 2$ interactions.
4. **Trend Detection Benchmark**:
   - Planted: 4 synthetic topic volume spikes at distinct simulated calendar dates.
   - Metrics: Precision, Recall, F1-Score, Mean Detection Delay (in days).
5. **Spam & Anomaly Detection Benchmark**:
   - Planted: 5 synthetic spam/bot profiles with repetitive content and abnormal posting rates.
   - Metrics: Confusion Matrix (TP, FP, TN, FN), Precision, Recall, F1-Score.
6. **Research Assistant Benchmark**:
   - Ground Truth: 20 academic question-answer pairs with exact source paper passages.
   - Metrics: Retrieval Precision@K, Retrieval Recall@K, Citation Accuracy, Groundedness Score (fraction of extracted facts verifiable in cited abstracts).
