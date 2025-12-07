"""
Job Context Workflow - Orchestrates JD ingestion, extraction, embedding, and storage.
"""
from typing import Optional

from app.models.job_context import JobContext
from app.agents.jd_context_agent import JDContextAgent
from app.services.chroma_db import ChromaStore
from app.database.store import DatabaseStore
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class JobContextWorkflow:
    """
    Workflow for processing job descriptions:
    1. Extract structured job context using JD Agent
    2. Generate embeddings
    3. Store in both vector DB and regular DB
    """
    
    def __init__(
        self,
        agent: JDContextAgent,
        chroma_store: ChromaStore,
        database: DatabaseStore,
        llm
    ):
        """
        Initialize Job Context Workflow.
        
        Args:
            agent: JDContextAgent instance
            chroma_store: ChromaStore instance
            database: DatabaseStore instance
            llm: GeminiLLM instance for embeddings
        """
        self.agent = agent
        self.chroma = chroma_store
        self.db = database
        self.llm = llm
        self.settings = get_settings()
    
    def process_job_description(
        self,
        raw_text: str,
        title_hint: Optional[str] = None
    ) -> JobContext:
        """
        Process a job description through the full workflow.
        
        Args:
            raw_text: Raw job description text or conversation
            title_hint: Optional job title hint
            
        Returns:
            Processed and stored JobContext
        """
        logger.info("Starting job context workflow")
        
        # Step 1: Extract structured job context
        job_context = self.agent.extract_job_context(raw_text, title_hint)
        
        # Step 2: Generate embedding
        embedding_text = self._build_embedding_text(job_context)
        embedding = self.llm.embed_text(embedding_text)
        job_context.embedding_vector = embedding
        
        # Step 3: Store in database
        job_id = self.db.create_job(job_context)
        job_context.id = job_id
        
        # Step 4: Store embedding in vector store
        self._store_embedding(job_context)
        
        logger.info(f"Job context workflow complete: {job_id}")
        return job_context
    
    def _build_embedding_text(self, job: JobContext) -> str:
        """Build text for embedding generation."""
        parts = [
            f"Job Title: {job.job_title}",
            f"Required Skills: {', '.join(job.required_skills)}",
            f"Preferred Skills: {', '.join(job.preferred_skills)}",
            f"Experience: {job.experience_required or 'Not specified'}",
            f"Domain: {job.domain or 'Not specified'}",
            f"Summary: {job.job_summary or ''}"
        ]
        return "\n".join(parts)
    
    def _store_embedding(self, job: JobContext):
        """Store job embedding in ChromaDB."""
        if not job.embedding_vector or not job.id:
            return
        
        metadata = {
            "job_title": job.job_title,
            "seniority": job.seniority or "",
            "domain": job.domain or "",
            "required_skills": ",".join(job.required_skills[:10]),
            "type": "job"
        }
        
        self.chroma.add_embedding(
            collection_name=self.settings.chroma_collection_jobs,
            id=job.id,
            embedding=job.embedding_vector,
            metadata=metadata,
            document=job.job_summary or job.job_title
        )
    
    def get_job(self, job_id: str) -> Optional[JobContext]:
        """
        Get a job by ID with embedding.
        
        Args:
            job_id: Job ID
            
        Returns:
            JobContext or None
        """
        job = self.db.get_job(job_id)
        
        if job:
            # Fetch embedding from vector store
            result = self.chroma.get_by_id(
                collection_name=self.settings.chroma_collection_jobs,
                id=job_id
            )
            if result and result.get('embedding'):
                job.embedding_vector = result['embedding']
        
        return job
    
    def find_job_by_title(self, title: str) -> Optional[JobContext]:
        """
        Find a job by title.
        
        Args:
            title: Job title to search
            
        Returns:
            JobContext or None
        """
        return self.db.get_job_by_title(title)
    
    def get_or_create_job(
        self,
        title: str,
        raw_text: Optional[str] = None
    ) -> JobContext:
        """
        Get existing job or create a new one.
        
        Args:
            title: Job title
            raw_text: Raw JD text if creating new
            
        Returns:
            JobContext
        """
        # Try to find existing
        existing = self.db.get_job_by_title(title)
        if existing:
            logger.info(f"Found existing job: {existing.id}")
            return self.get_job(existing.id)
        
        # Create new if we have text
        if raw_text:
            return self.process_job_description(raw_text, title_hint=title)
        
        # Create minimal placeholder
        job = JobContext(
            job_title=title,
            required_skills=[],
            preferred_skills=[],
            job_summary=f"Job position for {title}"
        )
        job_id = self.db.create_job(job)
        job.id = job_id
        
        logger.info(f"Created placeholder job: {job_id}")
        return job
    
    def list_jobs(self, limit: int = 100):
        """List all jobs."""
        return self.db.list_jobs(limit)
    
    def update_job(
        self,
        job_id: str,
        additional_info: str
    ) -> Optional[JobContext]:
        """
        Update a job with additional information.
        
        Args:
            job_id: Job ID to update
            additional_info: New information to add
            
        Returns:
            Updated JobContext or None
        """
        job = self.get_job(job_id)
        if not job:
            return None
        
        # Refine with agent
        updated_job = self.agent.refine_job_context(job, additional_info)
        updated_job.id = job_id
        
        # Regenerate embedding
        embedding_text = self._build_embedding_text(updated_job)
        embedding = self.llm.embed_text(embedding_text)
        updated_job.embedding_vector = embedding
        
        # Update in vector store
        self._store_embedding(updated_job)
        
        # Note: Full DB update would require additional method
        logger.info(f"Updated job: {job_id}")
        
        return updated_job
