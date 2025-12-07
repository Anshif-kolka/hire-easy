"""
Assessment Workflow - Compare a candidate against a job and generate scores.
"""
from typing import Optional

from app.models.job_context import JobContext
from app.models.candidate import Candidate
from app.models.score_report import ScoreReport
from app.agents.ranking_agent import RankingAgent
from app.services.chroma_db import ChromaStore
from app.database.store import DatabaseStore
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AssessmentWorkflow:
    """
    Workflow for assessing a single candidate against a job:
    1. Load job and candidate data
    2. Fetch embeddings
    3. Run ranking agent to generate score report
    4. Store score report
    """
    
    def __init__(
        self,
        ranking_agent: RankingAgent,
        chroma_store: ChromaStore,
        database: DatabaseStore
    ):
        """
        Initialize Assessment Workflow.
        
        Args:
            ranking_agent: RankingAgent instance
            chroma_store: ChromaStore instance
            database: DatabaseStore instance
        """
        self.ranking_agent = ranking_agent
        self.chroma = chroma_store
        self.db = database
        self.settings = get_settings()
    
    def assess_candidate(
        self,
        candidate_id: str,
        job_id: str,
        force_refresh: bool = False
    ) -> ScoreReport:
        """
        Assess a candidate for a job.
        
        Args:
            candidate_id: Candidate ID
            job_id: Job ID
            force_refresh: Whether to regenerate even if exists
            
        Returns:
            ScoreReport with assessment results
        """
        logger.info(f"Assessing candidate {candidate_id} for job {job_id}")
        
        # Check for existing score report
        if not force_refresh:
            existing = self.db.get_score_report(candidate_id, job_id)
            if existing:
                logger.info("Returning existing score report")
                return existing
        
        # Load candidate
        candidate = self.db.get_candidate(candidate_id)
        if not candidate:
            raise ValueError(f"Candidate {candidate_id} not found")
        
        # Load job
        job = self.db.get_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        # Fetch embeddings
        candidate_embedding = self._get_embedding(
            self.settings.chroma_collection_candidates,
            candidate_id
        )
        job_embedding = self._get_embedding(
            self.settings.chroma_collection_jobs,
            job_id
        )
        
        # Generate score report using ranking agent
        report = self.ranking_agent.generate_candidate_rank(
            candidate=candidate,
            job=job,
            candidate_embedding=candidate_embedding,
            job_embedding=job_embedding
        )
        
        # Update IDs
        report.candidate_id = candidate_id
        report.job_id = job_id
        
        # Store score report
        report_id = self.db.create_score_report(report)
        report.id = report_id
        
        logger.info(f"Assessment complete: {report.overall_score:.1f}")
        return report
    
    def _get_embedding(self, collection: str, id: str) -> Optional[list]:
        """Get embedding from vector store."""
        result = self.chroma.get_by_id(
            collection_name=collection,
            id=id,
            include=["embeddings"]
        )
        
        if result and result.get('embedding'):
            return result['embedding']
        return None
    
    def assess_candidate_direct(
        self,
        candidate: Candidate,
        job: JobContext
    ) -> ScoreReport:
        """
        Assess a candidate directly (without DB lookup).
        
        Args:
            candidate: Candidate model
            job: JobContext model
            
        Returns:
            ScoreReport
        """
        logger.info(f"Direct assessment: {candidate.name} for {job.job_title}")
        
        return self.ranking_agent.generate_candidate_rank(
            candidate=candidate,
            job=job,
            candidate_embedding=candidate.embedding_vector,
            job_embedding=job.embedding_vector
        )
    
    def get_assessment(
        self,
        candidate_id: str,
        job_id: str
    ) -> Optional[ScoreReport]:
        """
        Get existing assessment if available.
        
        Args:
            candidate_id: Candidate ID
            job_id: Job ID
            
        Returns:
            ScoreReport or None
        """
        return self.db.get_score_report(candidate_id, job_id)
    
    def batch_assess(
        self,
        candidate_ids: list,
        job_id: str,
        force_refresh: bool = False
    ) -> list:
        """
        Assess multiple candidates for a job.
        
        Args:
            candidate_ids: List of candidate IDs
            job_id: Job ID
            force_refresh: Whether to regenerate
            
        Returns:
            List of ScoreReports
        """
        reports = []
        
        for candidate_id in candidate_ids:
            try:
                report = self.assess_candidate(
                    candidate_id=candidate_id,
                    job_id=job_id,
                    force_refresh=force_refresh
                )
                reports.append(report)
            except Exception as e:
                logger.error(f"Failed to assess {candidate_id}: {e}")
        
        return reports
