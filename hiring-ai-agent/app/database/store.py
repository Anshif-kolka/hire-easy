"""
Database Store - SQLite operations for persistent storage.
"""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from app.models.job_context import JobContext
from app.models.candidate import Candidate
from app.models.score_report import ScoreReport
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseStore:
    """
    SQLite database operations for jobs, candidates, and scores.
    """
    
    def __init__(self, db_path: str = "data/hiring_agent.db"):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        
        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize schema
        self._init_schema()
        
        logger.info(f"Initialized database at: {db_path}")
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_schema(self):
        """Initialize database schema."""
        schema_path = Path(__file__).parent / "schemas.sql"
        
        if schema_path.exists():
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
        else:
            # Inline schema if file doesn't exist
            schema_sql = self._get_inline_schema()
        
        with self._get_connection() as conn:
            conn.executescript(schema_sql)
    
    def _get_inline_schema(self) -> str:
        """Get inline schema definition."""
        return """
        -- Jobs table
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            job_title TEXT NOT NULL,
            seniority TEXT,
            required_skills TEXT,
            preferred_skills TEXT,
            experience_required TEXT,
            experience_min_years REAL,
            experience_max_years REAL,
            responsibilities TEXT,
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
            skills TEXT,
            experience TEXT,
            education TEXT,
            projects TEXT,
            certifications TEXT,
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
            matched_skills TEXT,
            missing_skills TEXT,
            extra_skills TEXT,
            strengths TEXT,
            weaknesses TEXT,
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
        
        -- Indexes
        CREATE INDEX IF NOT EXISTS idx_candidates_job_id ON candidates(job_id);
        CREATE INDEX IF NOT EXISTS idx_candidates_email ON candidates(email);
        CREATE INDEX IF NOT EXISTS idx_score_reports_job_id ON score_reports(job_id);
        CREATE INDEX IF NOT EXISTS idx_score_reports_candidate_id ON score_reports(candidate_id);
        CREATE INDEX IF NOT EXISTS idx_jobs_title ON jobs(job_title);
        """
    
    # ============ Job Operations ============
    
    def create_job(self, job: JobContext) -> str:
        """
        Create a new job.
        
        Args:
            job: JobContext model
            
        Returns:
            Job ID
        """
        job_id = job.id or f"JOB-{uuid.uuid4().hex[:8].upper()}"
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO jobs (
                    id, job_title, seniority, required_skills, preferred_skills,
                    experience_required, experience_min_years, experience_max_years,
                    responsibilities, domain, job_summary, raw_text, location, remote_policy
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                job.job_title,
                job.seniority,
                json.dumps(job.required_skills),
                json.dumps(job.preferred_skills),
                job.experience_required,
                job.experience_min_years,
                job.experience_max_years,
                json.dumps(job.responsibilities),
                job.domain,
                job.job_summary,
                job.raw_text,
                job.location,
                job.remote_policy
            ))
        
        logger.info(f"Created job: {job_id}")
        return job_id
    
    def get_job(self, job_id: str) -> Optional[JobContext]:
        """
        Get a job by ID.
        
        Args:
            job_id: Job ID
            
        Returns:
            JobContext or None
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE id = ?", (job_id,)
            ).fetchone()
        
        if not row:
            return None
        
        return self._row_to_job(row)
    
    def get_job_by_title(self, title: str) -> Optional[JobContext]:
        """
        Get a job by title (case-insensitive).
        
        Args:
            title: Job title
            
        Returns:
            JobContext or None
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE LOWER(job_title) = LOWER(?) ORDER BY created_at DESC LIMIT 1",
                (title,)
            ).fetchone()
        
        if not row:
            return None
        
        return self._row_to_job(row)
    
    def list_jobs(self, limit: int = 100) -> List[JobContext]:
        """List all jobs."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        
        return [self._row_to_job(row) for row in rows]
    
    def _row_to_job(self, row: sqlite3.Row) -> JobContext:
        """Convert database row to JobContext."""
        return JobContext(
            id=row['id'],
            job_title=row['job_title'],
            seniority=row['seniority'],
            required_skills=json.loads(row['required_skills'] or '[]'),
            preferred_skills=json.loads(row['preferred_skills'] or '[]'),
            experience_required=row['experience_required'],
            experience_min_years=row['experience_min_years'],
            experience_max_years=row['experience_max_years'],
            responsibilities=json.loads(row['responsibilities'] or '[]'),
            domain=row['domain'],
            job_summary=row['job_summary'],
            raw_text=row['raw_text'],
            location=row['location'],
            remote_policy=row['remote_policy'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
    
    # ============ Candidate Operations ============
    
    def create_candidate(self, candidate: Candidate) -> str:
        """
        Create a new candidate.
        
        Args:
            candidate: Candidate model
            
        Returns:
            Candidate ID
        """
        candidate_id = candidate.id or f"CAND-{uuid.uuid4().hex[:8].upper()}"
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO candidates (
                    id, name, email, phone, location, headline, skills,
                    experience, education, projects, certifications,
                    total_experience_years, summary, github_url, linkedin_url,
                    portfolio_url, source, is_linkedin_pdf, raw_text, resume_file_path, job_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                candidate_id,
                candidate.name,
                candidate.email,
                candidate.phone,
                candidate.location,
                candidate.headline,
                json.dumps(candidate.skills),
                json.dumps([exp.model_dump() for exp in candidate.experience]),
                json.dumps([edu.model_dump() for edu in candidate.education]),
                json.dumps([proj.model_dump() for proj in candidate.projects]),
                json.dumps(candidate.certifications),
                candidate.total_experience_years,
                candidate.summary,
                candidate.github_url,
                candidate.linkedin_url,
                candidate.portfolio_url,
                candidate.source,
                1 if candidate.is_linkedin_pdf else 0,
                candidate.raw_text,
                candidate.resume_file_path,
                candidate.job_id
            ))
        
        logger.info(f"Created candidate: {candidate_id}")
        return candidate_id
    
    def get_candidate(self, candidate_id: str) -> Optional[Candidate]:
        """Get a candidate by ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM candidates WHERE id = ?", (candidate_id,)
            ).fetchone()
        
        if not row:
            return None
        
        return self._row_to_candidate(row)
    
    def get_candidate_by_email(self, email: str) -> Optional[Candidate]:
        """Get a candidate by email."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM candidates WHERE email = ?", (email,)
            ).fetchone()
        
        if not row:
            return None
        
        return self._row_to_candidate(row)
    
    def list_candidates(self, job_id: Optional[str] = None, limit: int = 100) -> List[Candidate]:
        """List candidates, optionally filtered by job."""
        with self._get_connection() as conn:
            if job_id:
                rows = conn.execute(
                    "SELECT * FROM candidates WHERE job_id = ? ORDER BY created_at DESC LIMIT ?",
                    (job_id, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM candidates ORDER BY created_at DESC LIMIT ?", (limit,)
                ).fetchall()
        
        return [self._row_to_candidate(row) for row in rows]
    
    def _row_to_candidate(self, row: sqlite3.Row) -> Candidate:
        """Convert database row to Candidate."""
        from app.models.candidate import Experience, Education, Project
        
        # Handle missing resume_file_path column for older databases
        resume_file_path = None
        try:
            resume_file_path = row['resume_file_path']
        except (IndexError, KeyError):
            pass
        
        return Candidate(
            id=row['id'],
            name=row['name'],
            email=row['email'],
            phone=row['phone'],
            location=row['location'],
            headline=row['headline'],
            skills=json.loads(row['skills'] or '[]'),
            experience=[Experience(**e) for e in json.loads(row['experience'] or '[]')],
            education=[Education(**e) for e in json.loads(row['education'] or '[]')],
            projects=[Project(**p) for p in json.loads(row['projects'] or '[]')],
            certifications=json.loads(row['certifications'] or '[]'),
            total_experience_years=row['total_experience_years'],
            summary=row['summary'],
            github_url=row['github_url'],
            linkedin_url=row['linkedin_url'],
            portfolio_url=row['portfolio_url'],
            source=row['source'],
            is_linkedin_pdf=bool(row['is_linkedin_pdf']),
            raw_text=row['raw_text'],
            resume_file_path=resume_file_path,
            job_id=row['job_id'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )

    # ============ Deletion / Cleanup Operations ============

    def delete_candidate(self, candidate_id: str) -> Optional[str]:
        """
        Delete a single candidate and related score reports.

        Returns the resume_file_path (if any) so callers can remove the file from disk.
        """
        with self._get_connection() as conn:
            # Fetch resume path if present
            row = conn.execute(
                "SELECT resume_file_path FROM candidates WHERE id = ?",
                (candidate_id,)
            ).fetchone()

            resume_path = row['resume_file_path'] if row and row['resume_file_path'] else None

            # Delete score reports for this candidate
            conn.execute("DELETE FROM score_reports WHERE candidate_id = ?", (candidate_id,))

            # Delete candidate row
            conn.execute("DELETE FROM candidates WHERE id = ?", (candidate_id,))

        logger.info(f"Deleted candidate and reports: {candidate_id}")
        return resume_path

    def delete_candidates_by_job(self, job_id: str) -> Dict[str, Any]:
        """
        Delete all candidates (and their score reports) associated with a job.

        Returns a dict with deleted candidate ids and resume_file_paths for cleanup.
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT id, resume_file_path FROM candidates WHERE job_id = ?",
                (job_id,)
            ).fetchall()

            candidate_ids = [r['id'] for r in rows]
            resume_paths = [r['resume_file_path'] for r in rows if r['resume_file_path']]

            if candidate_ids:
                # Delete score reports for these candidates
                placeholders = ','.join(['?'] * len(candidate_ids))
                conn.execute(f"DELETE FROM score_reports WHERE candidate_id IN ({placeholders})", tuple(candidate_ids))
                conn.execute(f"DELETE FROM candidates WHERE id IN ({placeholders})", tuple(candidate_ids))

            # Also delete any score reports directly tied to the job
            conn.execute("DELETE FROM score_reports WHERE job_id = ?", (job_id,))

        logger.info(f"Deleted {len(candidate_ids)} candidates for job: {job_id}")
        return {"deleted_candidate_ids": candidate_ids, "resume_paths": resume_paths}

    def delete_job(self, job_id: str) -> bool:
        """
        Delete a job row. Does not remove embeddings from vector store (caller should handle that).
        Returns True if a row was deleted.
        """
        with self._get_connection() as conn:
            cur = conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            deleted = cur.rowcount

        logger.info(f"Deleted job {job_id}, rows removed: {deleted}")
        return deleted > 0
    
    def update_candidate(self, candidate: Candidate) -> bool:
        """
        Update an existing candidate.
        
        Args:
            candidate: Candidate model with updated data
            
        Returns:
            True if updated successfully
        """
        if not candidate.id:
            logger.warning("Cannot update candidate without ID")
            return False
        
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE candidates SET
                    name = ?,
                    email = ?,
                    phone = ?,
                    location = ?,
                    headline = ?,
                    skills = ?,
                    experience = ?,
                    education = ?,
                    projects = ?,
                    certifications = ?,
                    total_experience_years = ?,
                    summary = ?,
                    github_url = ?,
                    linkedin_url = ?,
                    portfolio_url = ?,
                    source = ?,
                    is_linkedin_pdf = ?,
                    raw_text = ?,
                    resume_file_path = ?,
                    job_id = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                candidate.name,
                candidate.email,
                candidate.phone,
                candidate.location,
                candidate.headline,
                json.dumps(candidate.skills),
                json.dumps([exp.model_dump() for exp in candidate.experience]),
                json.dumps([edu.model_dump() for edu in candidate.education]),
                json.dumps([proj.model_dump() for proj in candidate.projects]),
                json.dumps(candidate.certifications),
                candidate.total_experience_years,
                candidate.summary,
                candidate.github_url,
                candidate.linkedin_url,
                candidate.portfolio_url,
                candidate.source,
                1 if candidate.is_linkedin_pdf else 0,
                candidate.raw_text,
                candidate.resume_file_path,
                candidate.job_id,
                candidate.id
            ))
        
        logger.info(f"Updated candidate: {candidate.id}")
        return True
    
    # ============ Score Report Operations ============
    
    def create_score_report(self, report: ScoreReport) -> str:
        """Create a new score report."""
        report_id = report.id or f"SCORE-{uuid.uuid4().hex[:8].upper()}"
        with self._get_connection() as conn:
            # Ensure only one score report exists per candidate-job pair.
            # Delete any existing report for this candidate+job before inserting the new one.
            try:
                conn.execute(
                    "DELETE FROM score_reports WHERE candidate_id = ? AND job_id = ?",
                    (report.candidate_id, report.job_id)
                )
            except Exception:
                # If table schema is older and column missing, ignore and continue to insert
                pass

            conn.execute("""
                INSERT INTO score_reports (
                    id, candidate_id, job_id, candidate_name, overall_score,
                    skill_match_score, experience_match_score, semantic_similarity_score,
                    matched_skills, missing_skills, extra_skills,
                    strengths, weaknesses, reasoning, recommendation
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report_id,
                report.candidate_id,
                report.job_id,
                report.candidate_name,
                report.overall_score,
                report.skill_match_score,
                report.experience_match_score,
                report.semantic_similarity_score,
                json.dumps(report.matched_skills),
                json.dumps(report.missing_skills),
                json.dumps(report.extra_skills),
                json.dumps(report.strengths),
                json.dumps(report.weaknesses),
                report.reasoning,
                report.recommendation
            ))
        
        logger.info(f"Created score report: {report_id}")
        return report_id
    
    def get_score_report(self, candidate_id: str, job_id: str) -> Optional[ScoreReport]:
        """Get score report for a candidate-job pair."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM score_reports WHERE candidate_id = ? AND job_id = ?",
                (candidate_id, job_id)
            ).fetchone()
        
        if not row:
            return None
        
        return self._row_to_score_report(row)
    
    def get_rankings_for_job(self, job_id: str) -> List[ScoreReport]:
        """Get all rankings for a job, sorted by score."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM score_reports WHERE job_id = ? ORDER BY overall_score DESC",
                (job_id,)
            ).fetchall()
        
        return [self._row_to_score_report(row) for row in rows]
    
    def _row_to_score_report(self, row: sqlite3.Row) -> ScoreReport:
        """Convert database row to ScoreReport."""
        return ScoreReport(
            id=row['id'],
            candidate_id=row['candidate_id'],
            job_id=row['job_id'],
            candidate_name=row['candidate_name'],
            overall_score=row['overall_score'],
            skill_match_score=row['skill_match_score'],
            experience_match_score=row['experience_match_score'],
            semantic_similarity_score=row['semantic_similarity_score'],
            matched_skills=json.loads(row['matched_skills'] or '[]'),
            missing_skills=json.loads(row['missing_skills'] or '[]'),
            extra_skills=json.loads(row['extra_skills'] or '[]'),
            strengths=json.loads(row['strengths'] or '[]'),
            weaknesses=json.loads(row['weaknesses'] or '[]'),
            reasoning=row['reasoning'],
            recommendation=row['recommendation'],
            created_at=row['created_at']
        )
    
    # ============ Email Log Operations ============
    
    def log_email(
        self,
        message_id: str,
        subject: str,
        sender: str,
        status: str,
        job_id: Optional[str] = None,
        candidate_id: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> str:
        """Log an email processing event."""
        log_id = f"EMAIL-{uuid.uuid4().hex[:8].upper()}"
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO email_log (
                    id, message_id, subject, sender, status, job_id, candidate_id, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (log_id, message_id, subject, sender, status, job_id, candidate_id, error_message))
        
        return log_id
    
    def is_email_processed(self, message_id: str) -> bool:
        """Check if an email has already been processed."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM email_log WHERE message_id = ?", (message_id,)
            ).fetchone()
        
        return row is not None
