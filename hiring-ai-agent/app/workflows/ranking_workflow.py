"""
Ranking Workflow - Full ranking pipeline for all candidates for a job.
"""
from typing import List, Optional

from app.models.job_context import JobContext
from app.models.candidate import Candidate
from app.models.score_report import ScoreReport, RankingReport
from app.agents.ranking_agent import RankingAgent
from app.workflows.assessment_workflow import AssessmentWorkflow
from app.services.chroma_db import ChromaStore
from app.database.store import DatabaseStore
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RankingWorkflow:
    """
    Workflow for ranking all candidates for a job:
    1. Load job context and embeddings
    2. Find relevant candidates using vector similarity
    3. Run assessment workflow for each candidate
    4. Sort and generate final ranking report
    """
    
    def __init__(
        self,
        assessment_workflow: AssessmentWorkflow,
        ranking_agent: RankingAgent,
        chroma_store: ChromaStore,
        database: DatabaseStore
    ):
        """
        Initialize Ranking Workflow.
        
        Args:
            assessment_workflow: AssessmentWorkflow instance
            ranking_agent: RankingAgent instance
            chroma_store: ChromaStore instance
            database: DatabaseStore instance
        """
        self.assessment = assessment_workflow
        self.ranking_agent = ranking_agent
        self.chroma = chroma_store
        self.db = database
        self.settings = get_settings()
    
    def rank_all_candidates(
        self,
        job_id: str,
        top_k: Optional[int] = None,
        force_refresh: bool = False
    ) -> RankingReport:
        """
        Generate rankings for all candidates for a job.
        
        Args:
            job_id: Job ID
            top_k: Optional limit on number of candidates
            force_refresh: Whether to regenerate all scores
            
        Returns:
            RankingReport with sorted candidates
        """
        logger.info(f"Starting ranking workflow for job {job_id}")
        
        # Load job
        job = self.db.get_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        # Get job embedding
        job_embedding = self._get_job_embedding(job_id)
        
        # Find candidate IDs
        candidate_ids = self._find_candidates_for_job(job_id, job_embedding, top_k)
        
        if not candidate_ids:
            logger.info("No candidates found for ranking")
            return RankingReport(
                job_id=job_id,
                job_title=job.job_title,
                total_candidates=0,
                rankings=[],
                top_candidates_summary="No candidates available for this position."
            )
        
        # Assess each candidate
        reports = []
        for cand_id in candidate_ids:
            try:
                report = self.assessment.assess_candidate(
                    candidate_id=cand_id,
                    job_id=job_id,
                    force_refresh=force_refresh
                )
                reports.append(report)
            except Exception as e:
                logger.error(f"Failed to assess candidate {cand_id}: {e}")
        
        # Sort by score
        reports.sort(key=lambda r: r.overall_score, reverse=True)
        
        # Generate summary
        summary = self.ranking_agent.generate_ranking_summary(reports, job)
        
        # Build ranking report
        ranking_report = RankingReport(
            job_id=job_id,
            job_title=job.job_title,
            total_candidates=len(reports),
            rankings=reports,
            top_candidates_summary=summary
        )
        
        logger.info(f"Ranking complete: {len(reports)} candidates ranked")
        return ranking_report
    
    def _get_job_embedding(self, job_id: str) -> Optional[list]:
        """Get job embedding from vector store."""
        result = self.chroma.get_by_id(
            collection_name=self.settings.chroma_collection_jobs,
            id=job_id,
            include=["embeddings"]
        )
        
        if result and result.get('embedding'):
            return result['embedding']
        return None
    
    def _find_candidates_for_job(
        self,
        job_id: str,
        job_embedding: Optional[list],
        top_k: Optional[int] = None
    ) -> List[str]:
        """
        Find candidates relevant to a job.
        
        Strategy:
        1. First get candidates who applied directly for this job
        2. Then use vector similarity to find additional matches
        """
        candidate_ids = set()
        
        # Get candidates who applied for this job directly
        direct_candidates = self.db.list_candidates(job_id=job_id)
        for cand in direct_candidates:
            candidate_ids.add(cand.id)
        
        # If we have a job embedding, find similar candidates
        if job_embedding:
            limit = top_k or 50
            
            similar = self.chroma.query_similar(
                collection_name=self.settings.chroma_collection_candidates,
                query_embedding=job_embedding,
                top_k=limit
            )
            
            if similar and similar.get('ids'):
                for cand_id in similar['ids'][0]:
                    candidate_ids.add(cand_id)
        
        # If still no candidates, get all candidates
        if not candidate_ids:
            all_candidates = self.db.list_candidates(limit=top_k or 100)
            candidate_ids = {c.id for c in all_candidates}
        
        result = list(candidate_ids)
        if top_k:
            result = result[:top_k]
        
        logger.info(f"Found {len(result)} candidates for ranking")
        return result
    
    def get_rankings(self, job_id: str) -> List[ScoreReport]:
        """
        Get existing rankings for a job.
        
        Args:
            job_id: Job ID
            
        Returns:
            List of ScoreReports sorted by score
        """
        return self.db.get_rankings_for_job(job_id)
    
    def get_top_candidates(
        self,
        job_id: str,
        limit: int = 5
    ) -> List[ScoreReport]:
        """
        Get top N candidates for a job.
        
        Args:
            job_id: Job ID
            limit: Number of candidates
            
        Returns:
            List of top ScoreReports
        """
        all_rankings = self.get_rankings(job_id)
        return all_rankings[:limit]
    
    def compare_candidates(
        self,
        candidate_ids: List[str],
        job_id: str
    ) -> dict:
        """
        Compare specific candidates for a job.
        
        Args:
            candidate_ids: List of candidate IDs to compare
            job_id: Job ID
            
        Returns:
            Comparison dict with rankings and analysis
        """
        reports = []
        for cand_id in candidate_ids:
            report = self.assessment.assess_candidate(cand_id, job_id)
            reports.append(report)
        
        # Sort by score
        reports.sort(key=lambda r: r.overall_score, reverse=True)
        
        # Get job for summary
        job = self.db.get_job(job_id)
        
        return {
            "job_id": job_id,
            "job_title": job.job_title if job else "Unknown",
            "candidates_compared": len(reports),
            "rankings": reports,
            "best_candidate": reports[0] if reports else None,
            "summary": self.ranking_agent.generate_ranking_summary(reports, job) if job else ""
        }
