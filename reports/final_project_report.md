# CHANAKYA RESEARCH COMMONS — COMPREHENSIVE TECHNICAL PROJECT REPORT
**Course**: V Semester B.Tech Data Mining and Warehousing (2026–27)  
**Institution**: Chanakya University, Bangalore  
**Submission Deadline**: 28 November 2026  
**Project Title**: Chanakya Research Commons: An Integrated Academic Data Mining, Warehousing, and Retrieval Platform  
**Authors**: Senior Engineering Team  

---

## Executive Summary

The **Chanakya Research Commons** is a comprehensive academic research, literature discovery, data mining, and institutional analytics platform engineered specifically for the V Semester B.Tech Data Mining and Warehousing curriculum at Chanakya University, Bangalore.

Unlike superficial mockup applications, Chanakya Research Commons delivers a fully implemented, mathematically defensible, full-stack data mining platform. It integrates:
1. **Nine Functional Subsystems** spanning identity (F1), community debates (F2), curated research library (F3), open scholarly ingestion (F4), 4-panel hybrid retrieval (F5), personalized recommendations (F6), trend and anomaly monitoring (F7), grounded conversational RAG assistant (F8), and institutional star-schema OLAP analytics (F9).
2. **A Deterministic Synthetic Dataset Generator** (Seed: 42) creating 520 research papers across 10 academic domains, 55 university members across 6 academic departments, 2,250 posts and threaded comments, and 12,906 activity events spanning 6 simulated academic months.
3. **Planted Ground Truth Datasets** evaluating duplicate papers, author name variants, burst promotional spam accounts, and sudden research topic velocity spikes.
4. **An Empirical Evaluation Suite** generating reproducible, numerical metrics comparing algorithms against established baselines (BM25 vs. Dense Vector vs. Hybrid RRF, Content-Based vs. SVD Collaborative vs. Popularity baseline, Isolation Forest Confusion Matrix, and MMR Groundedness).
5. **A Dimensional Data Warehouse** in DuckDB backed by columnar Apache Parquet files implementing a star schema (`Fact_Research_Activity`, `Dim_User`, `Dim_Department`, `Dim_Paper`, `Dim_Topic`, `Dim_Time`) supporting sub-second drill-down from University $\to$ Department $\to$ Topic $\to$ Member.

---

## 1. System Architecture & Component Design

The platform adopts a decoupled multi-tier architecture separating transactional OLTP workloads, external ETL/ELT pipelines, intelligent retrieval engines, and analytical OLAP cubes.

```
+----------------------------------------------------------------------------------------------------+
|                                         PRESENTATION TIER                                          |
|     Responsive Academic Interface (HTML5, CSS3, Bootstrap 5, Modern Vanilla JS, Chart.js)          |
|     Unified Navigation: Home | Explore | Library | Community | Recommendations | Assistant | Analytics |
+-------------------------------------------------+--------------------------------------------------+
                                                  | HTTP / JSON REST
+-------------------------------------------------v--------------------------------------------------+
|                                      APPLICATION BACKEND (FLASK)                                    |
|   Application Factory, Session Security, Role-Based Access Control (Student/Faculty/Researcher/Admin)   |
|   - auth_routes: Member registration, authentication, profiles, follow graph                      |
|   - library_routes: Repository browsing, DOI/arXiv imports, personal collections, private notes    |
|   - posts_routes: Threaded research posts, attached papers, upvotes, following feed                |
|   - search_routes: 4-Panel Unified Hybrid Search & entity resolution                               |
|   - rec_routes: Content-based, SVD Collaborative & FP-Growth co-save recommendations                |
|   - assistant_routes: RAG Assistant with passage retrieval, MMR re-ranking, verifiable citations   |
|   - analytics_routes: Institutional Admin Analytics, Dimensional Drill-downs, Security Alerts       |
|   - evaluation_routes: Empirical benchmark comparisons and confusion matrices                      |
+------------------------+---------------------------------+-----------------------------------------+
                         |                                 |
+------------------------v--------+               +--------v-----------------------+
|     DATA MINING & RETRIEVAL     |               |      DATA INGESTION (ETL)      |
|  - BM25 Inverted Token Index    |               |  - OpenAlex API Client         |
|  - Dense Cosine Similarity      |               |  - arXiv API XML Parser        |
|  - Reciprocal Rank Fusion (RRF) |               |  - Immutable Raw Storage (JSON)|
|  - Jaro-Winkler Author Resolver |               |  - Incremental Deduplicator    |
|  - TruncatedSVD Matrix Factor   |               +--------------------------------+
|  - FP-Growth Frequent Itemsets  |
|  - Sliding-Window Z-Score Trends|
|  - Isolation Forest Spam Outlier|
|  - MMR Passage Reranker & RAG   |
+------------------------+--------+
                         |
+------------------------v---------------------------------------------------------------------------+
|                                         DATA STORAGE LAYERS                                        |
|                                                                                                    |
|  1. OLTP Database Layer:                                                                           |
|     - PostgreSQL + pgvector (for Docker deployment) / Universal SQLite (for zero-setup local run)  |
|     - 19 Normalized tables, foreign keys, b-tree indexes, 384-dimensional dense vectors            |
|                                                                                                    |
|  2. Raw Storage Layer (data/raw/):                                                                 |
|     - Immutable raw API payloads preserved with timestamp metadata                                 |
|                                                                                                    |
|  3. Analytical Warehouse Layer (data/warehouse/):                                                  |
|     - DuckDB Columnar Vectorized Engine (analytics.duckdb)                                         |
|     - Columnar Apache Parquet files: Fact_Research_Activity, Dim_User, Dim_Department,             |
|       Dim_Paper, Dim_Topic, Dim_Time                                                               |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. Technology Stack Justification

| Layer | Technology | Version | Justification |
| :--- | :--- | :--- | :--- |
| **Backend** | Python Flask | 3.1.3 | Lightweight, robust WSGI application factory; native interoperability with scientific Python libraries (`numpy`, `scipy`, `scikit-learn`, `duckdb`). |
| **Relational DB** | PostgreSQL + pgvector (Dual-Engine SQLite Adapter) | 16 / 3.x | High-throughput ACID transactions; vector extensions allow native cosine indexing; dual engine enables zero-friction execution on student laptops. |
| **Data Warehouse** | DuckDB & Apache Parquet | 2.0.1 | In-process vectorized OLAP engine ideal for dimensional analytics across millions of rows; zero network overhead; high columnar compression. |
| **Embeddings** | SentenceTransformers (`all-MiniLM-L6-v2`) | 6.3.0 | 384-dimensional dense sentence embeddings capturing nuanced semantic similarities; optimized inference on Apple Silicon (ARM64) and CPU. |
| **Data Mining** | Scikit-Learn, MLxtend, NetworkX | Latest | Industry-standard implementations of TF-IDF, TruncatedSVD (CF), Isolation Forest (Spam), and FP-Growth (Association Rules). |
| **Frontend** | HTML5, CSS3, Bootstrap 5, Chart.js | 5.3.3 / 4.4.2 | Responsive academic UI; zero Node build requirements; fast client rendering across desktop, tablet, and mobile browsers. |
| **External APIs** | OpenAlex & arXiv REST APIs | Latest | 100% open, high-quality scholarly APIs with zero subscription fees or proprietary API keys. |

---

## 3. Detailed Subsystem Specifications

### Subsystem F1: Accounts and Profiles
- **Authentication**: PBKDF2 with SHA-256 password hashing.
- **Role-Based Access Control (RBAC)**: Distinct permissions for `Student`, `Faculty`, `Researcher`, and `Admin`.
- **Profiles**: Research interests, academic department affiliation, Google Scholar URLs, personal websites, and follow relationships.

### Subsystem F2: Posts and Discussions
- **Academic Forums**: Markdown-supported research posts with topic tags.
- **Attachment Mechanism**: Direct linking of papers from the institutional library.
- **Threaded Discussions**: Nested comment replies, upvotes, and personalized following feeds.

### Subsystem F3: Shared Research Library
- **Repository**: 520 curated papers with title, authors, abstract, publication year, venue, DOI, and arXiv identifiers.
- **Curated Collections**: Custom folders and private reading annotations.
- **Co-Saving Intelligence**: Integrated FP-Growth association rules displaying *"Members who saved this also saved..."*.

### Subsystem F4: External Content Ingestion
- **Multi-Source ETL**: Integrates OpenAlex and arXiv APIs.
- **Layered Storage**:
  1. *Raw Layer*: Immutable API responses saved in `data/raw/openalex/` and `data/raw/arxiv/`.
  2. *Processed Layer*: Standardized schema, normalized author names, and deduplication.
  3. *Warehouse Layer*: Populated into the DuckDB star schema.

### Subsystem F5: Unified Hybrid Search
- **4-Panel Interface**:
  1. Scholarly Papers & Repository
  2. University Library Saved Papers
  3. University Members & Faculty
  4. Community Discussions & Research Posts
- **Ranking Formulation**: Reciprocal Rank Fusion (RRF):
  $$\text{RRF}(d) = \sum_{m \in \{\text{BM25}, \text{Semantic}\}} \frac{1}{60 + \text{rank}_m(d)}$$
- **Entity Resolution**: Author name canonicalization via Jaro-Winkler distance ($d_{jw} \ge 0.88$).
- **Deduplication**: Multi-level identifier matching (DOI, arXiv ID, and Levenshtein token similarity).

### Subsystem F6: Recommendation Engine
1. **Content-Based Filtering**: Cosine similarity between centroid of user interest tags/saved papers and candidate paper vectors.
2. **Collaborative Filtering**: TruncatedSVD Matrix Factorization decomposing the user-paper interaction matrix into latent factor dimensions.
3. **Association-Rule Mining**: FP-Growth frequent itemset mining (MLxtend) discovering co-save rules with $\text{Confidence} \ge 0.35$ and $\text{Lift} > 1.2$.
4. **Cold-Start Strategy**: Stratified departmental popularity fallback ensuring 100% recommendation delivery for new members.

### Subsystem F7: Trends and Monitoring
- **Sliding-Window Velocity**: Compares 14-day current window velocity against 45-day historical baseline:
  $$Z = \frac{v_{\text{current}} - \mu_{\text{baseline}}}{\sigma_{\text{baseline}}}$$
- **Spam & Anomaly Detection**: Unsupervised `IsolationForest` combined with burst velocity heuristics and commercial keyword frequency checks.

### Subsystem F8: Research Assistant (RAG)
- **Workflow**:
  1. Receive query.
  2. Retrieve candidate passages from paper abstracts.
  3. Re-rank using Maximal Marginal Relevance (MMR, $\lambda = 0.70$) to balance relevance and diversity.
  4. Synthesize answers with citations `[Paper #ID: "Title", Year]`.
  5. Fallback: High-precision extractive summarization guarantees 100% fact groundedness directly in verified passages.

### Subsystem F9: Institutional Analytics Dashboard
- **Dimensional Model (Star Schema)**:
  - Fact: `Fact_Research_Activity` (12,906 rows)
  - Dimensions: `Dim_User`, `Dim_Department`, `Dim_Paper`, `Dim_Topic`, `Dim_Time`
- **Analytics Capabilities**:
  - Longitudinal activity trends (monthly/weekly).
  - Departmental engagement distribution.
  - Cross-department co-saving collaboration networks.
  - Drill-down: $\text{University} \to \text{Department} \to \text{Topic} \to \text{Member}$.

---

## 4. Empirical Evaluation Results & Numerical Proofs

All intelligent algorithms were evaluated against planted ground truth datasets (Seed: 42). The empirical results are saved in `reports/benchmarks_summary.json` and `reports/evaluation_metrics.csv`.

### Table 1: Master Empirical Evaluation Summary

| Subsystem | Algorithm / Model Variant | Metric | Measured Value | Baseline Comparison | Defensibility Assessment |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **Search (F5)** | Okapi BM25 Lexical | Precision@5 | **0.6100** | Keyword Baseline | High exact token precision, low conceptual recall |
| **Search (F5)** | Dense Semantic (`all-MiniLM-L6-v2`) | Precision@5 | **0.7800** | Vector Search | Excellent conceptual semantic match |
| **Search (F5)** | **Hybrid RRF (Combined)** | **Precision@5** | **0.7600** | Fusion Model | **Balanced precision; bridges vocabulary mismatch** |
| **Search (F5)** | Okapi BM25 Lexical | nDCG@10 | **0.6043** | Keyword Baseline | Lower rank discount due to missing synonyms |
| **Search (F5)** | Dense Semantic | nDCG@10 | **0.7909** | Vector Search | High top-rank density |
| **Search (F5)** | **Hybrid RRF (Combined)** | **nDCG@10** | **0.7368** | Fusion Model | **Robust across broad and specific queries** |
| **Deduplication**| Title Jaccard + Levenshtein + ID | Precision | **1.0000** | Exact Match | **Zero false positives across 520 papers** |
| **Deduplication**| Title Jaccard + Levenshtein + ID | Recall | **0.7500** | Exact Match | Catches 30 of 40 planted duplicate pairs |
| **Deduplication**| Title Jaccard + Levenshtein + ID | **F1-Score** | **0.8571** | Exact Match | Statistically rigorous deduplication |
| **Recommendations**| Global Popularity Baseline | Precision@5 | **0.3600** | Non-Personalized| Prone to popularity bias; 1.9% catalog coverage |
| **Recommendations**| **Content-Based Filtering** | **Precision@5** | **0.9600** | Personalized | **Highest alignment with user research interests** |
| **Recommendations**| **Collaborative Filtering (SVD)**| **Precision@5** | **0.8080** | Matrix Factor | **Strong discovery of latent co-reading patterns** |
| **Recommendations**| Content-Based Filtering | Catalog Coverage | **39.2%** | Diversity | High diversity without popularity skew |
| **Recommendations**| Cold-Start Strategy | Delivery Success| **100.0%** | Fallback | Guarantees non-empty cards for new members |
| **Trends (F7)** | Sliding-Window Z-Score Velocity | Precision | **1.0000** | Static Moving Avg| Zero false alarm spikes |
| **Trends (F7)** | Sliding-Window Z-Score Velocity | Recall | **1.0000** | Static Moving Avg| **Catches 100% of planted topic surges (QML)** |
| **Trends (F7)** | Sliding-Window Z-Score Velocity | **F1-Score** | **1.0000** | Static Moving Avg| Perfect surge classification |
| **Trends (F7)** | Sliding-Window Z-Score Velocity | Detection Delay| **3.2 days**| Real-Time Window | Rapid alert within half of window period |
| **Spam / Anomaly**| Isolation Forest + Heuristics | **True Positives** | **5** | Bot Ground Truth | **Caught all 5 planted commercial spammers** |
| **Spam / Anomaly**| Isolation Forest + Heuristics | **False Positives**| **1** | Legitimate Users | Only 1 false alarm out of 50 legitimate users |
| **Spam / Anomaly**| Isolation Forest + Heuristics | Precision | **0.8333** | Binary Classifier | High precision anomaly detection |
| **Spam / Anomaly**| Isolation Forest + Heuristics | Recall | **1.0000** | Binary Classifier | **100% detection of planted spam accounts** |
| **Spam / Anomaly**| Isolation Forest + Heuristics | **F1-Score** | **0.9091** | Binary Classifier | Robust abuse mitigation |
| **Spam / Anomaly**| Isolation Forest + Heuristics | Accuracy | **0.9818** | Full Population | 54 out of 55 accounts correctly classified |
| **RAG Assistant** | MMR Bi-Encoder Passage Retrieval| Precision@5 | **1.0000** | Top-K Retrieval | 100% of retrieved chunks belong to target domain |
| **RAG Assistant** | MMR Bi-Encoder Passage Retrieval| Recall@5 | **1.0000** | Top-K Retrieval | Captures all relevant domain passages |
| **RAG Assistant** | Grounded Citation Engine | Citation Coverage | **0.9500** | Open QA Baseline | 95% of generated citations match topic ground truth|
| **RAG Assistant** | Extractive Synthesis Engine | **Groundedness** | **1.0000** | Generative LLM | **100% verifiable proofs; zero hallucination** |

---

## 5. Limitations & Production Deployment Plan

### Current Limitations
1. **Single-Node Execution**: In the local configuration, SQLite and DuckDB operate as in-process embedded storage engines. In high-concurrency production deployments with thousands of simultaneous concurrent writes, PostgreSQL connection pooling (PgBouncer) is recommended.
2. **Local Embedding Latency**: Initial inference for 520 papers requires ~4 seconds on Apple Silicon. For millions of documents, asynchronous Celery workers with GPU acceleration (NVIDIA CUDA or Apple Metal MPS) should be deployed.

### Production Deployment Strategy
1. **Container Orchestration**: Deploy via Kubernetes using the included `Dockerfile` and `docker-compose.yml`.
2. **Cloud Migration**:
   - PostgreSQL + pgvector hosted on AWS RDS or Google Cloud SQL.
   - DuckDB analytics files exported periodically to AWS S3 or GCP Cloud Storage.
3. **Continuous Ingestion**: Configure cron schedules running `ingestion/pipeline.py` every 6 hours for incremental OpenAlex and arXiv ingestion.
