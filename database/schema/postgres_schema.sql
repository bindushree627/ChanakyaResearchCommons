-- ==============================================================================
-- CHANAKYA RESEARCH COMMONS: PostgreSQL DDL Schema
-- Course: V Sem B.Tech Data Mining & Warehousing, Chanakya University, Bangalore
-- ==============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Departments
CREATE TABLE IF NOT EXISTS departments (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    faculty_count INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Users (Role-based access: Student, Faculty, Researcher, Admin)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('Student', 'Faculty', 'Researcher', 'Admin')),
    department_id INT REFERENCES departments(id) ON DELETE SET NULL,
    bio TEXT,
    website_url VARCHAR(500),
    scholar_url VARCHAR(500),
    is_spam_flagged SMALLINT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. User Research Interests
CREATE TABLE IF NOT EXISTS user_interests (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    topic_name VARCHAR(100) NOT NULL,
    weight NUMERIC(3, 2) DEFAULT 1.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_interest UNIQUE (user_id, topic_name)
);

-- 4. User Follow Relationships
CREATE TABLE IF NOT EXISTS user_followers (
    id SERIAL PRIMARY KEY,
    follower_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    following_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_follow UNIQUE (follower_id, following_id),
    CONSTRAINT chk_no_self_follow CHECK (follower_id <> following_id)
);

-- 5. Topics
CREATE TABLE IF NOT EXISTS topics (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) UNIQUE NOT NULL,
    slug VARCHAR(150) UNIQUE NOT NULL,
    domain VARCHAR(100) NOT NULL,
    description TEXT,
    follower_count INT DEFAULT 0,
    post_count INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. Topic Followers
CREATE TABLE IF NOT EXISTS topic_followers (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    topic_id INT NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_topic UNIQUE (user_id, topic_id)
);

-- 7. Papers (Scholarly repository)
CREATE TABLE IF NOT EXISTS papers (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    clean_title TEXT NOT NULL,
    abstract TEXT,
    publication_year INT,
    doi VARCHAR(255) UNIQUE,
    arxiv_id VARCHAR(100) UNIQUE,
    venue VARCHAR(255),
    citation_count INT DEFAULT 0,
    primary_topic_id INT REFERENCES topics(id) ON DELETE SET NULL,
    embedding_json TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 8. Paper Authors
CREATE TABLE IF NOT EXISTS paper_authors (
    id SERIAL PRIMARY KEY,
    paper_id INT NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    author_name VARCHAR(255) NOT NULL,
    normalized_name VARCHAR(255) NOT NULL,
    affiliation VARCHAR(255),
    author_order INT DEFAULT 1
);

-- 9. Paper Sources (Unified multi-source ingestion)
CREATE TABLE IF NOT EXISTS paper_sources (
    id SERIAL PRIMARY KEY,
    paper_id INT NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    source_name VARCHAR(50) NOT NULL, -- 'OpenAlex', 'arXiv', 'Manual'
    external_id VARCHAR(255),
    landing_url TEXT,
    pdf_url TEXT,
    raw_payload_path TEXT,
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_paper_source UNIQUE (paper_id, source_name, external_id)
);

-- 10. Collections (Personal paper folders)
CREATE TABLE IF NOT EXISTS collections (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    is_public SMALLINT DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 11. Library Saves (User personal library entries)
CREATE TABLE IF NOT EXISTS library_saves (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    paper_id INT NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    collection_id INT REFERENCES collections(id) ON DELETE SET NULL,
    private_notes TEXT,
    rating INT CHECK (rating >= 1 AND rating <= 5),
    saved_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_paper_save UNIQUE (user_id, paper_id)
);

-- 12. Research Posts (Community discussions)
CREATE TABLE IF NOT EXISTS posts (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(300) NOT NULL,
    content TEXT NOT NULL,
    attached_paper_id INT REFERENCES papers(id) ON DELETE SET NULL,
    primary_topic_id INT REFERENCES topics(id) ON DELETE SET NULL,
    upvote_count INT DEFAULT 0,
    comment_count INT DEFAULT 0,
    is_pinned SMALLINT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 13. Post Tags
CREATE TABLE IF NOT EXISTS post_tags (
    id SERIAL PRIMARY KEY,
    post_id INT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    tag_name VARCHAR(50) NOT NULL
);

-- 14. Post Comments (Threaded discussions)
CREATE TABLE IF NOT EXISTS post_comments (
    id SERIAL PRIMARY KEY,
    post_id INT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    parent_comment_id INT REFERENCES post_comments(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 15. Post Votes
CREATE TABLE IF NOT EXISTS post_votes (
    id SERIAL PRIMARY KEY,
    post_id INT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    vote_value INT NOT NULL CHECK (vote_value IN (-1, 1)),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_post_vote UNIQUE (post_id, user_id)
);

-- 16. Activity Events (OLTP logging for audit & ETL into DuckDB Warehouse)
CREATE TABLE IF NOT EXISTS activity_events (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE SET NULL,
    event_type VARCHAR(50) NOT NULL, -- 'view_paper', 'save_paper', 'search', 'post', 'comment', 'upvote'
    target_type VARCHAR(50),        -- 'paper', 'post', 'user', 'query'
    target_id INT,
    metadata_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 17. Search History
CREATE TABLE IF NOT EXISTS search_history (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    query_text VARCHAR(500) NOT NULL,
    result_count INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 18. Precomputed Recommendations Cache
CREATE TABLE IF NOT EXISTS recommendations_cache (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rec_type VARCHAR(50) NOT NULL, -- 'paper_content', 'paper_collaborative', 'researcher', 'paper_association'
    item_id INT NOT NULL,
    score NUMERIC(6, 4) NOT NULL,
    explanation TEXT,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
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
