-- Hiring AI Agent Database Schema
-- SQLite

-- Jobs table
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    job_title TEXT NOT NULL,
    seniority TEXT,
    required_skills TEXT,  -- JSON array
    preferred_skills TEXT,  -- JSON array
    experience_required TEXT,
    experience_min_years REAL,
    experience_max_years REAL,
    responsibilities TEXT,  -- JSON array
    domain TEXT,
    job_summary TEXT,
    raw_text TEXT,
    location TEXT,
    remote_policy TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Candidates table
CREATE TABLE IF NOT EXISTS candidates (
    id TEXT PRIMARY KEY,
    name TEXT,
    email TEXT,
    phone TEXT,
    location TEXT,
    headline TEXT,
    skills TEXT,  -- JSON array
    experience TEXT,  -- JSON array of Experience objects
    education TEXT,  -- JSON array of Education objects
    projects TEXT,  -- JSON array of Project objects
    certifications TEXT,  -- JSON array
    total_experience_years REAL,
    summary TEXT,
    github_url TEXT,
    linkedin_url TEXT,
    portfolio_url TEXT,
    source TEXT DEFAULT 'upload',
    is_linkedin_pdf INTEGER DEFAULT 0,
    raw_text TEXT,
    resume_file_path TEXT,
    job_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);

-- Score reports table
CREATE TABLE IF NOT EXISTS score_reports (
    id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL,
    job_id TEXT NOT NULL,
    candidate_name TEXT,
    overall_score REAL NOT NULL,
    skill_match_score REAL,
    experience_match_score REAL,
    semantic_similarity_score REAL,
    matched_skills TEXT,  -- JSON array
    missing_skills TEXT,  -- JSON array
    extra_skills TEXT,  -- JSON array
    strengths TEXT,  -- JSON array
    weaknesses TEXT,  -- JSON array
    reasoning TEXT,
    recommendation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id),
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);

-- Email processing log
CREATE TABLE IF NOT EXISTS email_log (
    id TEXT PRIMARY KEY,
    message_id TEXT UNIQUE,
    subject TEXT,
    sender TEXT,
    received_at TIMESTAMP,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT,
    job_id TEXT,
    candidate_id TEXT,
    error_message TEXT
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_candidates_job_id ON candidates(job_id);
CREATE INDEX IF NOT EXISTS idx_candidates_email ON candidates(email);
CREATE INDEX IF NOT EXISTS idx_score_reports_job_id ON score_reports(job_id);
CREATE INDEX IF NOT EXISTS idx_score_reports_candidate_id ON score_reports(candidate_id);
CREATE INDEX IF NOT EXISTS idx_score_reports_score ON score_reports(overall_score DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_title ON jobs(job_title);
CREATE INDEX IF NOT EXISTS idx_email_log_message_id ON email_log(message_id);
