"""
Resume Ingestion Workflow - Orchestrates resume parsing, embedding, and storage.
"""
from pathlib import Path
from typing import Optional, Union

from app.models.candidate import Candidate
from app.services.pdf_parser import PDFParser
from app.agents.resume_analysis_agent import ResumeAnalysisAgent
from app.services.chroma_db import ChromaStore
from app.database.store import DatabaseStore
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ResumeIngestionWorkflow:
    """
    Workflow for processing resumes:
    1. Parse PDF to extract text
    2. Use Resume Agent to extract structured data
    3. Generate embeddings
    4. Store in both vector DB and regular DB
    """
    
    def __init__(
        self,
        pdf_parser: PDFParser,
        resume_agent: ResumeAnalysisAgent,
        chroma_store: ChromaStore,
        database: DatabaseStore,
        llm
    ):
        """
        Initialize Resume Ingestion Workflow.
        
        Args:
            pdf_parser: PDFParser instance
            resume_agent: ResumeAnalysisAgent instance
            chroma_store: ChromaStore instance
            database: DatabaseStore instance
            llm: GeminiLLM instance for embeddings
        """
        self.pdf_parser = pdf_parser
        self.resume_agent = resume_agent
        self.chroma = chroma_store
        self.db = database
        self.llm = llm
        self.settings = get_settings()
    
    def process_resume_file(
        self,
        file_path: Union[str, Path],
        source: str = "upload",
        job_id: Optional[str] = None
    ) -> Candidate:
        """
        Process a resume PDF file.
        
        Args:
            file_path: Path to PDF file
            source: How resume was received (upload, email)
            job_id: Associated job ID (if applicable)
            
        Returns:
            Processed Candidate
        """
        logger.info(f"Processing resume file: {file_path}")
        
        # Step 1: Extract text from PDF
        pdf_result = self.pdf_parser.extract_text(file_path)
        
        return self._process_resume_content(
            raw_text=pdf_result["raw_text"],
            is_linkedin=pdf_result["is_linkedin_pdf"],
            source=source,
            job_id=job_id
        )
    
    def process_resume_bytes(
        self,
        pdf_bytes: bytes,
        source: str = "upload",
        job_id: Optional[str] = None,
        filename: Optional[str] = None
    ) -> Candidate:
        """
        Process resume from bytes (for uploaded files).
        
        Args:
            pdf_bytes: PDF file content as bytes
            source: How resume was received
            job_id: Associated job ID
            filename: Original filename
            
        Returns:
            Processed Candidate
        """
        logger.info(f"Processing resume bytes (filename={filename})")
        
        # Step 1: Extract text from PDF bytes
        pdf_result = self.pdf_parser.extract_text_from_bytes(pdf_bytes)
        
        return self._process_resume_content(
            raw_text=pdf_result["raw_text"],
            is_linkedin=pdf_result["is_linkedin_pdf"],
            source=source,
            job_id=job_id,
            pdf_bytes=pdf_bytes
        )
    
    def _process_resume_content(
        self,
        raw_text: str,
        is_linkedin: bool,
        source: str,
        job_id: Optional[str],
        enrich_github: bool = True,
        pdf_bytes: Optional[bytes] = None
    ) -> Candidate:
        """
        Process extracted resume content.
        
        Args:
            raw_text: Extracted text
            is_linkedin: Whether from LinkedIn PDF
            source: Resume source
            job_id: Associated job ID
            enrich_github: Whether to enrich with GitHub data
            pdf_bytes: Original PDF bytes to store
            
        Returns:
            Processed Candidate
        """
        # Step 2: Check for duplicate by email (if we can extract it quickly)
        # This is a basic dedup - could be enhanced
        
        # Step 3: Extract structured data using Resume Agent (with GitHub enrichment)
        candidate = self.resume_agent.parse_resume_with_github(
            raw_text=raw_text,
            is_linkedin=is_linkedin,
            source=source,
            job_id=job_id,
            enrich_github=enrich_github
        )
        
        # Check for existing candidate with same email
        if candidate.email:
            existing = self.db.get_candidate_by_email(candidate.email)
            if existing:
                logger.info(f"Found existing candidate with email {candidate.email}")
                # Update job_id if this is a new application
                if job_id and job_id != existing.job_id:
                    # For now, we'll create a new record for the new application
                    # In a production system, you might want to track multiple applications
                    pass
                else:
                    return existing
        
        # Step 4: Generate embedding
        embedding_text = self._build_embedding_text(candidate)
        embedding = self.llm.embed_text(embedding_text)
        candidate.embedding_vector = embedding
        
        # Step 5: Store in database
        candidate_id = self.db.create_candidate(candidate)
        candidate.id = candidate_id
        
        # Step 5.5: Save original PDF file
        if pdf_bytes:
            resume_path = self._save_resume_file(candidate_id, pdf_bytes)
            candidate.resume_file_path = resume_path
            self.db.update_candidate(candidate)
        
        # Step 6: Store embedding in vector store
        self._store_embedding(candidate)
        
        logger.info(f"Resume ingestion complete: {candidate_id} ({candidate.name})")
        return candidate
    
    def _save_resume_file(self, candidate_id: str, pdf_bytes: bytes) -> str:
        """
        Save the original resume PDF to disk.
        
        Args:
            candidate_id: Candidate ID
            pdf_bytes: PDF file content
            
        Returns:
            Path to saved file
        """
        # Ensure directory exists
        resumes_dir = Path(self.settings.data_dir) / "resumes"
        resumes_dir.mkdir(parents=True, exist_ok=True)
        
        # Save file
        file_path = resumes_dir / f"{candidate_id}.pdf"
        with open(file_path, 'wb') as f:
            f.write(pdf_bytes)
        
        logger.info(f"Saved resume file: {file_path}")
        return str(file_path)
    
    def _build_embedding_text(self, candidate: Candidate) -> str:
        """Build text for embedding generation."""
        parts = [
            f"Name: {candidate.name or 'Unknown'}",
            f"Headline: {candidate.headline or ''}",
            f"Skills: {', '.join(candidate.skills)}",
            f"Experience: {candidate.total_experience_years or 'Unknown'} years",
            f"Summary: {candidate.summary or ''}"
        ]
        
        # Add project info
        for project in candidate.projects[:3]:
            if project.name:
                parts.append(f"Project: {project.name} - {project.description or ''}")
        
        return "\n".join(parts)
    
    def _store_embedding(self, candidate: Candidate):
        """Store candidate embedding in ChromaDB."""
        if not candidate.embedding_vector or not candidate.id:
            return
        
        metadata = {
            "name": candidate.name or "",
            "email": candidate.email or "",
            "skills": ",".join(candidate.skills[:15]),
            "experience_years": str(candidate.total_experience_years or 0),
            "job_id": candidate.job_id or "",
            "source": candidate.source,
            "type": "candidate"
        }
        
        self.chroma.add_embedding(
            collection_name=self.settings.chroma_collection_candidates,
            id=candidate.id,
            embedding=candidate.embedding_vector,
            metadata=metadata,
            document=candidate.summary or candidate.name or "Unknown"
        )
    
    def get_candidate(self, candidate_id: str) -> Optional[Candidate]:
        """
        Get a candidate by ID with embedding.
        
        Args:
            candidate_id: Candidate ID
            
        Returns:
            Candidate or None
        """
        candidate = self.db.get_candidate(candidate_id)
        
        if candidate:
            # Fetch embedding from vector store
            result = self.chroma.get_by_id(
                collection_name=self.settings.chroma_collection_candidates,
                id=candidate_id
            )
            if result and result.get('embedding'):
                candidate.embedding_vector = result['embedding']
        
        return candidate
    
    def list_candidates(
        self,
        job_id: Optional[str] = None,
        limit: int = 100
    ):
        """List candidates, optionally filtered by job."""
        return self.db.list_candidates(job_id=job_id, limit=limit)
    
    def find_similar_candidates(
        self,
        job_embedding: list,
        top_k: int = 10,
        job_id: Optional[str] = None
    ):
        """
        Find candidates similar to a job description.
        
        Args:
            job_embedding: Job embedding vector
            top_k: Number of results
            job_id: Optional job ID filter
            
        Returns:
            List of candidate IDs with scores
        """
        where_filter = None
        if job_id:
            where_filter = {"job_id": job_id}
        
        results = self.chroma.query_similar(
            collection_name=self.settings.chroma_collection_candidates,
            query_embedding=job_embedding,
            top_k=top_k,
            where=where_filter
        )
        
        # Format results
        candidates = []
        if results and results.get('ids'):
            for i, cand_id in enumerate(results['ids'][0]):
                candidates.append({
                    'candidate_id': cand_id,
                    'distance': results['distances'][0][i] if results.get('distances') else None,
                    'metadata': results['metadatas'][0][i] if results.get('metadatas') else {}
                })
        
        return candidates
