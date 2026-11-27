# Chanakya Research Commons
### V Semester B.Tech Data Mining & Warehousing Capstone Project (2026–27)
**Chanakya University, Bangalore**  
**Submission Deadline**: 28 November 2026  

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1.3-green.svg)](https://flask.palletsprojects.com/)
[![DuckDB](https://img.shields.io/badge/DuckDB-OLAP-yellow.svg)](https://duckdb.org/)
[![SentenceTransformers](https://img.shields.io/badge/SentenceTransformers-all--MiniLM--L6--v2-orange.svg)](https://www.sbert.net/)
[![Docker](https://img.shields.io/badge/Docker-Postgres%20%2B%20pgvector-blue.svg)](https://www.docker.com/)

---

## 1. Project Overview

**Chanakya Research Commons** is a university research collaboration platform that enables students, faculty, and researchers to discover academic papers, share research ideas, collaborate through discussions, save research resources, explore research trends, and receive AI-powered research recommendations and assistance. Built for the V Semester B.Tech Data Mining & Warehousing course, the application implements all nine subsystems with reproducible numerical evaluation results.

> **Complete Technical Documentation:** See [`CHANAKYA_RESEARCH_COMMONS_COMPLETE_DOCUMENTATION.md`](CHANAKYA_RESEARCH_COMMONS_COMPLETE_DOCUMENTATION.md) for the full 17-chapter architectural, database, data mining, mathematical, and viva-preparation reference.

### Key Highlights
- **Nine Functional Subsystems**:
  - `F1`: Accounts, Profiles, and Role-Based Access Control (Student, Faculty, Researcher, Admin).
  - `F2`: Posts, Discussions, Threaded Comments, Upvotes, and Following-Based Personalized Feeds.
  - `F3`: Shared Research Library, Collections, Private Notes, and "Members who saved this also saved" co-save intelligence.
  - `F4`: External Scholarly Ingestion (OpenAlex & arXiv APIs, raw/processed/warehouse layered architecture).
  - `F5`: Unified 4-Panel Hybrid Search (Okapi BM25 Lexical + 384-dim Dense Sentence Embeddings via Reciprocal Rank Fusion).
  - `F6`: Multi-Model Recommendation Engine (Content-Based Profile Centroid, TruncatedSVD Collaborative Filtering, MLxtend FP-Growth Association Rules, and Cold-Start Handling).
  - `F7`: Trends & Monitoring (Sliding-Window Z-Score Velocity Spike Detection and Isolation Forest Spam Anomaly Detection).
  - `F8`: Research Assistant RAG (Passage retrieval, MMR re-ranking, verifiable citations, extractive high-precision fallback, and optional local Ollama integration).
  - `F9`: Institutional Analytics Dashboard (DuckDB Star Schema and Apache Parquet columnar storage with University $\to$ Department $\to$ Topic $\to$ Member drill-down).
- **Synthetic Academic Dataset**: 520 research papers across 10 academic disciplines, 60 university members across 6 departments, 20,220 posts and comments (5,020 posts + 15,200 comments), 10,525 paper-save relationships, 20,500 views, 10,200 searches, 569 follow links, and 66,945 total activity events simulated over 6 academic months (184 days, 27 weeks).
- **Planted Ground Truth Anomaly Sets**: Duplicate papers (40 pairs), author name variants, commercial bot spammers (5 accounts), and sudden topic velocity spikes (Quantum Machine Learning).
- **Automated Verification Suite**: Direct SQL database audit asserting all mandatory minimums and project targets (`python scripts/verify_dataset.py`).
- **Empirical Evaluations**: Reproducible numerical benchmarks with output files saved in JSON and CSV format.

---

## 2. Directory Structure

```
ChanakyaResearchCommons/
├── app/
│   ├── __init__.py               # Flask app factory, DB hooks, Jinja filters
│   ├── config.py                 # Configuration classes (Dev, Test, Prod)
│   ├── models/                   # Relational DB models & dual-engine adapter
│   │   ├── db.py                 # PostgreSQL / SQLite connection abstraction
│   │   └── entities.py           # User, Paper, Library, Post domain models
│   ├── routes/                   # HTTP Blueprint Controllers (F1 - F9)
│   │   ├── auth_routes.py        # F1: Authentication & Profiles
│   │   ├── library_routes.py     # F3: Research Library & Saves
│   │   ├── posts_routes.py       # F2: Discussions & Feeds
│   │   ├── search_routes.py      # F5: 4-Panel Unified Hybrid Search
│   │   ├── rec_routes.py         # F6: Recommendation Engine
│   │   ├── assistant_routes.py   # F8: Research Assistant RAG
│   │   ├── analytics_routes.py   # F9: Institutional Analytics (Admin)
│   │   └── evaluation_routes.py  # Benchmark Comparison Dashboard
│   ├── static/                   # Static CSS & JS Assets
│   │   ├── css/chanakya.css      # Professional academic stylesheet
│   │   └── js/main.js            # AJAX votes, follow buttons, RAG chat
│   └── templates/                # Responsive Jinja2 HTML Templates
├── data/
│   ├── raw/                      # Raw immutable API payloads (OpenAlex & arXiv)
│   ├── warehouse/                # DuckDB database (analytics.duckdb) & Parquet files
│   └── synthetic/                # Ground truth JSON files (duplicates, spikes, spam)
├── ingestion/                    # External Content ETL (F4)
│   ├── openalex_ingestor.py     # OpenAlex API works harvester
│   ├── normalizer.py             # Schema normalization & deduplication
├── mining/                       # Intelligent Algorithms (F5 - F8)
│   ├── embeddings.py             # SentenceTransformers (all-MiniLM-L6-v2)
│   ├── search/                   # BM25, Semantic, and Hybrid RRF rankers
│   ├── duplicate_detection/      # Paper deduplication & Jaro-Winkler author resolver
│   ├── recommendations/          # Content-based, SVD Collaborative, FP-Growth
│   ├── trends/                   # Sliding-window Z-score velocity trend detector
│   ├── anomaly_detection/        # Isolation Forest spam & abuse classifier
│   └── rag/                      # Passage chunking, MMR re-ranking, Grounded RAG
├── analytics/                    # Star Schema OLAP (F9)
│   ├── etl_warehouse.py          # Populates DuckDB star schema from OLTP
│   └── queries.py                # Fast OLAP drill-down queries
├── evaluation/                   # Scientific Algorithm Evaluations
│   ├── eval_search.py            # P@5, P@10, R@10, nDCG@10 (BM25 vs Dense vs Hybrid)
│   ├── eval_duplicate.py         # Precision, Recall, F1 against planted ground truth
│   ├── eval_recommendations.py   # Precision, Recall, Coverage vs Baseline
│   ├── eval_trends.py            # Precision, Recall, F1, Detection delay on surges
│   ├── eval_spam.py              # Confusion matrix, Precision, Recall, F1
│   ├── eval_rag.py               # Retrieval P@K, R@K, Citation Coverage & Groundedness
│   └── run_all_evaluations.py    # Master runner generating JSON/CSV benchmarks
├── database/
│   ├── schema/
│   │   ├── postgres_schema.sql   # PostgreSQL + pgvector DDL schema
│   │   └── sqlite_schema.sql     # Universal local SQLite DDL schema
│   └── seeds/
│       └── initial_departments.json
├── scripts/
│   ├── init_db.py                # Database initializer & department seeder
│   ├── generate_synthetic_data.py# Reproducible dataset generator (Seed=42)
│   └── run_full_pipeline.sh      # Master setup & benchmark orchestrator
├── reports/
│   ├── benchmarks_summary.json   # Machine-readable evaluation outputs
│   ├── evaluation_metrics.csv    # Metric comparison table
│   ├── ARCHITECTURE_AND_SPECIFICATION.md
│   └── final_project_report.md   # Complete academic technical project report
├── tests/
│   └── test_all_subsystems.py    # Automated test suite (13 test cases)
├── docker-compose.yml            # Containerized PostgreSQL + pgvector service
├── Dockerfile                    # Multi-platform container configuration
├── requirements.txt              # Pinned Python package dependencies
├── .env.example                  # Environment configuration template
└── README.md
```

---

## 3. Running Chanakya Research Commons Locally

Follow these step-by-step instructions to run Chanakya Research Commons on your own computer. No cloud services or paid accounts are required.

### 1. Install Git and Python
- **Git:** Download and install from [git-scm.com](https://git-scm.com/downloads) (on macOS, you can also run `xcode-select --install`).
- **Python 3.10+ (3.13 recommended):** Download and install from [python.org](https://www.python.org/downloads/). On Windows, make sure to check **"Add python.exe to PATH"** during installation.

### 2. Clone the Private GitHub Repository
Make sure you have accepted your GitHub repository invitation first, then run:
```bash
git clone https://github.com/JhansiCMohitha1587/ChanakyaResearchCommons.git
```

### 3. Enter the Project Directory
```bash
cd ChanakyaResearchCommons
```

### 4. Create a Python Virtual Environment
- **macOS / Linux:**
  ```bash
  python3 -m venv .venv
  ```
- **Windows (Command Prompt or PowerShell):**
  ```powershell
  python -m venv .venv
  ```

### 5. Activate the Virtual Environment
- **macOS / Linux:**
  ```bash
  source .venv/bin/activate
  ```
- **Windows (PowerShell):**
  ```powershell
  .venv\Scripts\Activate.ps1
  ```
- **Windows (Command Prompt):**
  ```cmd
  .venv\Scripts\activate.bat
  ```
*(You should see `(.venv)` appear at the beginning of your terminal prompt.)*

### 6. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 7. Create Local Environment Configuration
Copy the example environment file to `.env`:
- **macOS / Linux:**
  ```bash
  cp .env.example .env
  ```
- **Windows:**
  ```powershell
  copy .env.example .env
  ```
*(By default, `.env.example` uses local SQLite at `data/chanakya_commons.db`—no external database is needed.)*

### 8. Initialize a Fresh Local Database
Run the safe local database setup script (it creates all tables, seeds departments, generates the synthetic academic dataset if your database is empty, and builds the local DuckDB analytics warehouse—without overwriting any existing data):
```bash
python3 scripts/setup_local_db.py
```
*(On Windows, use `python scripts/setup_local_db.py`.)*

### 9. Start the Flask Application
```bash
python3 -m flask --app app:create_app run --host=127.0.0.1 --port=5000
```
*(On Windows, use `python -m flask --app app:create_app run --host=127.0.0.1 --port=5000`.)*

### 10. Open the Website in a Browser
Open your browser and go to:
**http://127.0.0.1:5000**

You can register a new Student, Faculty, or Researcher account on the Register page, or sign in with an existing account.

### 11. Troubleshooting Common Errors
- **`python3: command not found` (Windows):** Use `python` instead of `python3`.
- **PowerShell activation blocked (`running scripts is disabled`):** Run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` in PowerShell, then activate again.
- **`ModuleNotFoundError` (e.g. `No module named 'flask'`):** Make sure your virtual environment is activated (`(.venv)` in your prompt) and re-run `pip install -r requirements.txt`.
- **Port 5000 already in use (macOS AirPlay Receiver):** Either turn off AirPlay Receiver in macOS System Settings or run with `--port=5001` and open `http://127.0.0.1:5001`.
- **First-run delay on search/assistant:** On the first run on a new computer, `sentence-transformers` downloads `all-MiniLM-L6-v2` (~90 MB) once and caches it locally.

---

### Alternative: Step-by-Step Manual Setup

#### 1. Database Initialization
```bash
python3 scripts/init_db.py
```
*Creates all 19 normalized tables, indexes, and seeds the 6 university academic departments.*

#### 2. Synthetic Dataset Generation (Fixed Seed: 42)
```bash
python3 scripts/generate_synthetic_data.py --reset
```
*Generates 520 research papers with dense embeddings, 60 university members across 6 departments, 5,020 posts, 15,200 comments, 10,525 library paper-save relationships, 20,500 views, 10,200 searches, 569 follow relationships, and 66,945 total activity events across 6 academic months (184 days, 27 calendar weeks).*

#### 3. Automated Dataset Verification & Audit
```bash
python3 scripts/verify_dataset.py
```
*Queries the database directly using SQL and asserts that all mandatory minimums and larger project targets are satisfied. Exits with code 0 on complete pass, code 1 on failure.*

#### 4. Data Warehouse ETL (DuckDB & Parquet Star Schema)
```bash
python3 analytics/etl_warehouse.py
```
*Extracts OLTP events, builds dimensional tables (`Dim_User`, `Dim_Department`, `Dim_Paper`, `Dim_Topic`, `Dim_Time`, `Fact_Research_Activity`), exports Parquet files, and loads 66,945 fact rows into the DuckDB OLAP cube.*

#### 5. Run Scientific Algorithm Evaluations
```bash
python3 evaluation/run_all_evaluations.py
```
*Executes all empirical benchmark suites against ground truth anomaly files and generates `reports/benchmarks_summary.json` and `reports/evaluation_metrics.csv`.*

#### 6. Run Automated Tests
```bash
python3 tests/test_all_subsystems.py
```
*Runs all 13 test suites validating registration, authentication, RBAC, posts, comments, saves, search, deduplication, recommendations, trends, spam, RAG, and analytics.*

#### 7. Start Web Application
```bash
python3 -m flask --app app:create_app run --host=127.0.0.1 --port=5000
```

---

### Option C: Containerized Deployment (Docker Compose)
To run with containerized PostgreSQL and pgvector:
```bash
docker-compose up --build
```
Access the application at **http://localhost:5000**.

---

## 4. Database Configuration & Admin Recovery

### Database Configuration
- Copy `.env.example` to `.env` and set `SECRET_KEY` (and optionally `DATABASE_URL` for PostgreSQL).
- By default, the application uses local SQLite at `data/chanakya_commons.db` alongside the DuckDB/Parquet analytics warehouse in `data/warehouse/`.
- Local `.db` and `.env` files are excluded from Git via `.gitignore`. Teammates should run `python3 scripts/init_db.py`, `python3 scripts/generate_synthetic_data.py --reset`, and `python3 analytics/etl_warehouse.py` after cloning to initialize their local databases.

### Admin Recovery Instructions
All accounts use `werkzeug.security` password hashing (`generate_password_hash` / `check_password_hash`). Public registration is restricted to `Student`, `Faculty`, and `Researcher` roles.

If an authorized administrator needs to reset or recover an admin password locally:
```bash
.venv/bin/python -c "
import sqlite3
from werkzeug.security import generate_password_hash
conn = sqlite3.connect('data/chanakya_commons.db')
conn.execute('UPDATE users SET password_hash = ? WHERE username = ? AND role = \"Admin\"',
             (generate_password_hash('<NEW_STRONG_PASSWORD>'), '<admin_username>'))
conn.commit()
"
```

---

## 5. Summary of Empirical Algorithm Results

All evaluations were executed against planted ground truth datasets (Seed: 42):

```
+--------------------------------------------------------------------------------------------------+
| SUBSYSTEM                 | ALGORITHM / VARIANT           | KEY METRICS                          |
+---------------------------+-------------------------------+--------------------------------------+
| F5: Unified Search        | Okapi BM25 Lexical            | P@5: 0.6100 | P@10: 0.6050 | nDCG: 0.6043|
| F5: Unified Search        | Dense Semantic (MiniLM)       | P@5: 0.7800 | P@10: 0.7900 | nDCG: 0.7909|
| F5: Unified Search        | Hybrid RRF (Combined)         | P@5: 0.7600 | P@10: 0.7200 | nDCG: 0.7368|
+---------------------------+-------------------------------+--------------------------------------+
| F5: Duplicate Detection   | Jaccard + Levenshtein + ID    | Precision: 1.0000 | Recall: 0.7500   |
|                           |                               | F1-Score: 0.8571 (30 TP, 0 FP)       |
+---------------------------+-------------------------------+--------------------------------------+
| F6: Recommendations       | Global Popularity Baseline    | P@5: 0.3600 | Catalog Coverage: 1.9% |
| F6: Recommendations       | Content-Based Profile         | P@5: 0.9600 | Catalog Coverage: 39.2%|
| F6: Recommendations       | Collaborative Filtering (SVD) | P@5: 0.8080 | Catalog Coverage: 31.7%|
| F6: Recommendations       | Cold-Start Strategy           | Delivery Success Rate: 100.0%        |
+---------------------------+-------------------------------+--------------------------------------+
| F7: Trend Spike Detection | Sliding-Window Z-Score        | Precision: 1.0000 | Recall: 1.0000   |
|                           |                               | F1-Score: 1.0000 | Mean Delay: 3.2d  |
+---------------------------+-------------------------------+--------------------------------------+
| F7: Spam Detection        | Isolation Forest + Heuristics | Precision: 0.8333 | Recall: 1.0000   |
|                           |                               | F1: 0.9091 | Accuracy: 0.9818        |
|                           |                               | Confusion Matrix: TP=5, FP=1, FN=0   |
+---------------------------+-------------------------------+--------------------------------------+
| F8: Research Assistant    | Dense MMR Bi-Encoder RAG      | Retrieval P@5: 1.0000 | R@5: 1.0000  |
|                           |                               | Citation Coverage: 0.9500            |
|                           |                               | Groundedness Score: 1.0000 (100%)    |
+--------------------------------------------------------------------------------------------------+
```

---

## 6. Accessing Platform Interfaces

Once the application is running at `http://127.0.0.1:5000`:
- **Home**: `http://127.0.0.1:5000/`
- **Explore Research (F5 Search)**: `http://127.0.0.1:5000/explore`
- **Research Library (F3)**: `http://127.0.0.1:5000/library`
- **Community Discussions (F2)**: `http://127.0.0.1:5000/community`
- **Recommendations (F6)**: `http://127.0.0.1:5000/recommendations`
- **Research Assistant (F8 RAG)**: `http://127.0.0.1:5000/assistant`
- **Institutional Analytics (F9, Admin)**: `http://127.0.0.1:5000/analytics`
- **Algorithm Benchmark Dashboard**: `http://127.0.0.1:5000/evaluation`
- **Account Settings**: `http://127.0.0.1:5000/settings`

---

## 7. Faculty & Evaluation Checklist

- [x] **Subsystem F1**: Accounts, authentication, password hashing, 4 roles, profiles, department tags, follow graph.
- [x] **Subsystem F2**: Research posts, topic tags, attached library papers, threaded comments, upvotes, personalized feed.
- [x] **Subsystem F3**: Research library, collections, private notes, ratings, DOI/arXiv imports, co-save recommendations.
- [x] **Subsystem F4**: OpenAlex and arXiv ingestion pipelines, immutable raw JSON storage, clean processed schema.
- [x] **Subsystem F5**: 4-panel unified search (papers, library, members, posts), Okapi BM25 + dense sentence embeddings, RRF ranker, author entity resolution.
- [x] **Subsystem F6**: Content-based centroid recommendations, TruncatedSVD collaborative filtering, FP-Growth association rules, cold-start handling.
- [x] **Subsystem F7**: Sliding-window Z-score velocity trend surge detection, Isolation Forest spam outlier detection, admin security alerts.
- [x] **Subsystem F8**: RAG research assistant, passage chunking, MMR re-ranking, 100% grounded citations and source verification proofs.
- [x] **Subsystem F9**: Admin analytics dashboard, DuckDB star schema, Parquet columnar storage, dimensional drill-down (University $\to$ Dept $\to$ Topic $\to$ Member).
- [x] **Synthetic Dataset (Audited)**: 520 papers, 60 members across 6 departments, 4 roles, 5,020 posts, 15,200 comments (20,220 combined discussions), 10,525 paper saves, 20,500 views, 10,200 searches, 569 follow links, 66,945 activity events over 184 days (27 weeks) with fixed seed (42). Verified by `python scripts/verify_dataset.py`.
- [x] **Algorithm Benchmarks**: Empirical precision, recall, nDCG, F1, and confusion matrix outputs saved in CSV and JSON.
- [x] **Testing**: 13 automated unit and integration tests passing (`13/13 OK`).
- [x] **Packaging**: Dockerfile, docker-compose.yml, .env.example, requirements.txt, comprehensive technical report.

---

## 8. Synthetic Activity Dataset Audit & Target Verification Table

All metrics below are calculated directly from active database rows via `python scripts/verify_dataset.py`:

| Verification Metric | Mandatory Minimum | Project Target | Database Verified Count | Audit Status |
| :--- | :--- | :--- | :--- | :--- |
| **University Members** | $\ge 50$ members | 50+ members | **60 members** | `PASS` |
| **Academic Departments** | $\ge 6$ departments | 6 departments | **6 departments** (`CSE`, `DSAI`, `ECE`, `ISE`, `BTBI`, `MDS`) | `PASS` |
| **Member Roles** | 4 roles | 4 roles | **4 roles** (31 Student, 15 Researcher, 11 Faculty, 3 Admin) | `PASS` |
| **Research Posts** | $\ge 1,000$ posts | 5,000+ posts | **5,020 posts** (64.9% with attached library papers) | `PASS` |
| **Threaded Comments** | $\ge 1,000$ comments | 15,000+ comments | **15,200 comments** (3,747 threaded child replies) | `PASS` |
| **Combined Discussions** | $\ge 2,000$ combined | 20,000+ combined | **20,220 discussions** | `PASS` |
| **Paper-Save Relationships** | $\ge 2,000$ saves | 10,000+ saves | **10,525 saves** (`library_saves` table) | `PASS` |
| **Paper Views** | $\ge 5,000$ views | 20,000+ views | **20,500 views** (`activity_events`, `event_type='view_paper'`) | `PASS` |
| **Search Queries** | $\ge 3,000$ searches | 10,000+ searches | **10,200 searches** (`search_history` & `activity_events`) | `PASS` |
| **Total Activity Events** | $\ge 10,000$ events | 50,000+ events | **66,945 events** (`activity_events` table) | `PASS` |
| **Academic Follow Graph** | $\ge 100$ links | 300+ links | **569 follow links** (`user_followers` table) | `PASS` |
| **Temporal Coverage (Span)** | $\ge 180$ days (6 months) | 6 months | **184 days** (2026-05-28 to 2026-11-28, 6.1 months) | `PASS` |
| **Active Calendar Weeks** | $\ge 26$ weeks | 26+ weeks | **27 active weeks** | `PASS` |
| **Planted Anomaly Ground Truth** | Required | Planted sets | **Duplicates (40), Spam (5), QML Surge (1)** | `PASS` |

---

## 9. Team Collaboration & Git Workflow

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/JhansiCMohitha1587/ChanakyaResearchCommons.git
   cd ChanakyaResearchCommons
   ```
2. **Get the Latest Changes Before Working:**
   ```bash
   git pull origin main
   ```
   *(Your local `data/chanakya_commons.db` and `.env` are ignored by Git, so pulling code updates will never overwrite your local database.)*
3. **Create a Feature Branch** (recommended for individual contributions):
   ```bash
   git checkout -b feature/<your-feature-name>
   ```
4. **Commit & Push Changes:**
   ```bash
   git add <files>
   git commit -m "Describe your change clearly"
   git push -u origin feature/<your-feature-name>
   ```
5. **Open a Pull Request:**
   On GitHub, open a Pull Request from `feature/<your-feature-name>` into `main` for review before merging.
