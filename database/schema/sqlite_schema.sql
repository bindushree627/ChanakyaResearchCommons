-- ==============================================================================
-- CHANAKYA RESEARCH COMMONS: Universal SQLite DDL Schema
-- Course: V Sem B.Tech Data Mining & Warehousing, Chanakya University, Bangalore
-- ==============================================================================

PRAGMA foreign_keys = ON;

-- 1. Departments
CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    faculty_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Users (Role-based access: Student, Faculty, Researcher, Admin)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('Student', 'Faculty', 'Researcher', 'Admin')),
    department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL,
    bio TEXT,
    website_url TEXT,
    scholar_url TEXT,
    is_spam_flagged INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. User Research Interests
CREATE TABLE IF NOT EXISTS user_interests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    topic_name TEXT NOT NULL,
    weight REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, topic_name)
);

-- 4. User Follow Relationships
CREATE TABLE IF NOT EXISTS user_followers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    follower_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    following_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (follower_id, following_id)
);

-- 5. Topics
CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    domain TEXT NOT NULL,
    description TEXT,
    follower_count INTEGER DEFAULT 0,
    post_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Topic Followers
CREATE TABLE IF NOT EXISTS topic_followers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, topic_id)
);

-- 7. Papers (Scholarly repository)
CREATE TABLE IF NOT EXISTS papers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    clean_title TEXT NOT NULL,
    abstract TEXT,
    publication_year INTEGER,
    doi TEXT UNIQUE,
    arxiv_id TEXT UNIQUE,
    venue TEXT,
    citation_count INTEGER DEFAULT 0,
    primary_topic_id INTEGER REFERENCES topics(id) ON DELETE SET NULL,
    embedding_json TEXT, -- JSON-encoded 384-dimensional dense vector
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. Paper Authors
CREATE TABLE IF NOT EXISTS paper_authors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    author_name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    affiliation TEXT,
    author_order INTEGER DEFAULT 1
);

-- 9. Paper Sources (Unified multi-source ingestion)
CREATE TABLE IF NOT EXISTS paper_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    source_name TEXT NOT NULL, -- 'OpenAlex', 'arXiv', 'Manual'
    external_id TEXT,
    landing_url TEXT,
    pdf_url TEXT,
    raw_payload_path TEXT,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (paper_id, source_name, external_id)
);

-- 10. Collections (Personal paper folders)
CREATE TABLE IF NOT EXISTS collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    is_public INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 11. Library Saves (User personal library entries)
CREATE TABLE IF NOT EXISTS library_saves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    collection_id INTEGER REFERENCES collections(id) ON DELETE SET NULL,
    private_notes TEXT,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, paper_id)
);

-- 12. Research Posts (Community discussions)
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    attached_paper_id INTEGER REFERENCES papers(id) ON DELETE SET NULL,
    primary_topic_id INTEGER REFERENCES topics(id) ON DELETE SET NULL,
    upvote_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    is_pinned INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 13. Post Tags
CREATE TABLE IF NOT EXISTS post_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    tag_name TEXT NOT NULL
);

-- 14. Post Comments (Threaded discussions)
CREATE TABLE IF NOT EXISTS post_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    parent_comment_id INTEGER REFERENCES post_comments(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 15. Post Votes
CREATE TABLE IF NOT EXISTS post_votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    vote_value INTEGER NOT NULL CHECK (vote_value IN (-1, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (post_id, user_id)
);

-- 16. Activity Events (OLTP logging for audit & ETL into DuckDB Warehouse)
CREATE TABLE IF NOT EXISTS activity_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    target_type TEXT,
    target_id INTEGER,
    metadata_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 17. Search History
CREATE TABLE IF NOT EXISTS search_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    query_text TEXT NOT NULL,
    result_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 18. Precomputed Recommendations Cache
CREATE TABLE IF NOT EXISTS recommendations_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rec_type TEXT NOT NULL,
    item_id INTEGER NOT NULL,
    score REAL NOT NULL,
    explanation TEXT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_papers_clean_title ON papers(clean_title);
CREATE INDEX IF NOT EXISTS idx_papers_pub_year ON papers(publication_year);
CREATE INDEX IF NOT EXISTS idx_papers_doi ON papers(doi);
CREATE INDEX IF NOT EXISTS idx_papers_arxiv ON papers(arxiv_id);
CREATE INDEX IF NOT EXISTS idx_papers_topic ON papers(primary_topic_id);
CREATE INDEX IF NOT EXISTS idx_library_saves_user ON library_saves(user_id);
CREATE INDEX IF NOT EXISTS idx_library_saves_paper ON library_saves(paper_id);
CREATE INDEX IF NOT EXISTS idx_posts_user ON posts(user_id);
CREATE INDEX IF NOT EXISTS idx_posts_topic ON posts(primary_topic_id);
CREATE INDEX IF NOT EXISTS idx_events_user_type ON activity_events(user_id, event_type);
CREATE INDEX IF NOT EXISTS idx_events_target ON activity_events(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_events_created ON activity_events(created_at);
