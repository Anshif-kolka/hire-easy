"""
Resume API Routes - Endpoints for resume upload and management.
"""
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional

from app.models.candidate import Candidate, CandidateResponse
from app.workflows.resume_ingestion_workflow import ResumeIngestionWorkflow
from app.workflows.job_context_workflow import JobContextWorkflow
from app.agents.email_ingest_agent import EmailIngestAgent
from app.dependencies import (
    get_resume_ingestion_workflow,
    get_job_context_workflow,
    get_email_ingest_agent
)
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/resume", tags=["Resumes"])


class EmailIngestResponse(BaseModel):
    """Response for email ingestion."""
    message: str
    processed_count: int


@router.post("/upload", response_model=CandidateResponse)
async def upload_resume(
    file: UploadFile = File(...),
    job_id: Optional[str] = None,
    workflow: ResumeIngestionWorkflow = Depends(get_resume_ingestion_workflow)
):
    """
    Upload a resume PDF for processing.
    
    Extracts candidate information, generates embeddings, and stores the profile.
    Optionally associates with a job ID.
    """
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        )
    
    # Check file size
    settings = get_settings()
    max_size = settings.max_file_size_mb * 1024 * 1024
    
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {settings.max_file_size_mb}MB"
        )
    
    try:
        candidate = workflow.process_resume_bytes(
            pdf_bytes=content,
            source="upload",
            job_id=job_id,
            filename=file.filename
        )
        
        return CandidateResponse(
            id=candidate.id,
            name=candidate.name,
            email=candidate.email,
            headline=candidate.headline,
            skills=candidate.skills,
            total_experience_years=candidate.total_experience_years,
            summary=candidate.summary,
            source=candidate.source,
            job_id=candidate.job_id,
            created_at=candidate.created_at
        )
    except Exception as e:
        logger.error(f"Failed to process resume: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(
    candidate_id: str,
    workflow: ResumeIngestionWorkflow = Depends(get_resume_ingestion_workflow)
):
    """
    Get a candidate by ID.
    
    Returns the full candidate profile with extracted information.
    """
    candidate = workflow.get_candidate(candidate_id)
    
    if not candidate:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found")
    
    return CandidateResponse(
        id=candidate.id,
        name=candidate.name,
        email=candidate.email,
        headline=candidate.headline,
        skills=candidate.skills,
        total_experience_years=candidate.total_experience_years,
        summary=candidate.summary,
        source=candidate.source,
        job_id=candidate.job_id,
        created_at=candidate.created_at
    )


@router.get("/", response_model=List[CandidateResponse])
async def list_candidates(
    job_id: Optional[str] = None,
    limit: int = 100,
    workflow: ResumeIngestionWorkflow = Depends(get_resume_ingestion_workflow)
):
    """
    List candidates, optionally filtered by job.
    
    Returns a list of candidate profiles.
    """
    candidates = workflow.list_candidates(job_id=job_id, limit=limit)
    
    return [
        CandidateResponse(
            id=c.id,
            name=c.name,
            email=c.email,
            headline=c.headline,
            skills=c.skills,
            total_experience_years=c.total_experience_years,
            summary=c.summary,
            source=c.source,
            job_id=c.job_id,
            created_at=c.created_at
        )
        for c in candidates
    ]


@router.post("/email-ingest", response_model=EmailIngestResponse)
async def ingest_from_email(
    background_tasks: BackgroundTasks,
    resume_workflow: ResumeIngestionWorkflow = Depends(get_resume_ingestion_workflow),
    job_workflow: JobContextWorkflow = Depends(get_job_context_workflow),
    email_agent: EmailIngestAgent = Depends(get_email_ingest_agent)
):
    """
    Trigger email ingestion to fetch resumes from inbox.
    
    Checks for new emails matching pattern "JOB - {Title} - APPLICATION"
    and processes PDF attachments.
    """
    if not email_agent.is_configured():
        raise HTTPException(
            status_code=400,
            detail="Email ingestion not configured. Set EMAIL_* environment variables."
        )
    
    processed_count = 0
    
    def process_email_resume(
        job_title: str,
        pdf_bytes: bytes,
        filename: str,
        sender: str,
        message_id: str
    ):
        nonlocal processed_count
        
        try:
            # Get or create job
            job = job_workflow.get_or_create_job(job_title)
            
            # Process resume
            candidate = resume_workflow.process_resume_bytes(
                pdf_bytes=pdf_bytes,
                source="email",
                job_id=job.id,
                filename=filename
            )
            
            logger.info(f"Processed email resume: {candidate.name} for {job_title}")
            processed_count += 1
            
        except Exception as e:
            logger.error(f"Failed to process email resume from {sender}: {e}")
    
    # Run email polling
    email_agent.poll_and_process(process_email_resume)
    
    return EmailIngestResponse(
        message="Email ingestion complete",
        processed_count=processed_count
    )


@router.get("/{candidate_id}/full")
async def get_candidate_full(
    candidate_id: str,
    workflow: ResumeIngestionWorkflow = Depends(get_resume_ingestion_workflow)
):
    """
    Get full candidate details including experience, education, and projects.
    """
    candidate = workflow.get_candidate(candidate_id)
    
    if not candidate:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found")
    
    return {
        "id": candidate.id,
        "name": candidate.name,
        "email": candidate.email,
        "phone": candidate.phone,
        "location": candidate.location,
        "headline": candidate.headline,
        "summary": candidate.summary,
        "skills": candidate.skills,
        "total_experience_years": candidate.total_experience_years,
        "experience": [exp.model_dump() for exp in candidate.experience],
        "education": [edu.model_dump() for edu in candidate.education],
        "projects": [proj.model_dump() for proj in candidate.projects],
        "certifications": candidate.certifications,
        "github_url": candidate.github_url,
        "linkedin_url": candidate.linkedin_url,
        "portfolio_url": candidate.portfolio_url,
        "source": candidate.source,
        "is_linkedin_pdf": candidate.is_linkedin_pdf,
        "resume_file_path": candidate.resume_file_path,
        "job_id": candidate.job_id,
        "created_at": candidate.created_at
    }


@router.get("/{candidate_id}/download")
async def download_resume(
    candidate_id: str,
    workflow: ResumeIngestionWorkflow = Depends(get_resume_ingestion_workflow)
):
    """
    Download the original resume PDF for a candidate.
    
    Returns the PDF file if available.
    """
    candidate = workflow.get_candidate(candidate_id)
    
    if not candidate:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found")
    
    if not candidate.resume_file_path:
        raise HTTPException(
            status_code=404,
            detail="Resume file not available for this candidate"
        )
    
    file_path = Path(candidate.resume_file_path)
    
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Resume file not found on disk"
        )
    
    # Create a safe filename
    safe_name = (candidate.name or "resume").replace(" ", "_")
    filename = f"{safe_name}_{candidate_id}.pdf"
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/pdf"
    )


@router.delete("/{candidate_id}")
async def delete_candidate(
    candidate_id: str,
    workflow: ResumeIngestionWorkflow = Depends(get_resume_ingestion_workflow)
):
    """
    Delete a candidate, their score reports, associated resume file, and remove embedding from Chroma.
    """
    # Ensure candidate exists
    candidate = workflow.get_candidate(candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found")

    # Remove embedding from chroma
    try:
        workflow.chroma.delete(
            collection_name=workflow.settings.chroma_collection_candidates,
            ids=[candidate_id]
        )
    except Exception as e:
        logger.warning(f"Chroma deletion warning for candidate {candidate_id}: {e}")

    # Delete DB rows and get resume path
    resume_path = workflow.db.delete_candidate(candidate_id)

    # Delete file if present
    deleted_file = False
    if resume_path:
        p = Path(resume_path)
        if p.exists():
            try:
                p.unlink()
                deleted_file = True
            except Exception as e:
                logger.warning(f"Failed to delete resume file {resume_path}: {e}")

    return {"deleted": True, "deleted_file": deleted_file}


@router.post("/{candidate_id}/enrich-github")
async def enrich_candidate_github(
    candidate_id: str,
    github_url: Optional[str] = None,
    workflow: ResumeIngestionWorkflow = Depends(get_resume_ingestion_workflow)
):
    """
    Manually enrich a candidate with GitHub profile analysis.
    
    If github_url is not provided, will try to extract it from the resume text.
    
    Returns:
        GitHub analysis data and updated candidate skills
    """
    candidate = workflow.get_candidate(candidate_id)
    
    if not candidate:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found")
    
    # Set GitHub URL if provided
    if github_url:
        candidate.github_url = github_url
    
    # Get the resume agent from workflow
    resume_agent = workflow.resume_agent
    
    # If no GitHub URL, try to extract from raw text
    if not candidate.github_url and candidate.raw_text:
        candidate.github_url = resume_agent.extract_github_url(candidate.raw_text)
    
    if not candidate.github_url:
        raise HTTPException(
            status_code=400,
            detail="No GitHub URL found in resume. Please provide github_url parameter."
        )
    
    # Analyze GitHub profile
    analysis = resume_agent.analyze_github_profile(candidate.github_url)
    
    if 'error' in analysis:
        raise HTTPException(status_code=400, detail=analysis['error'])
    
    # Enrich candidate
    enriched = resume_agent.enrich_candidate_with_github(candidate)
    
    # Update in database
    workflow.db.update_candidate(enriched)
    
    return {
        "message": "GitHub enrichment complete",
        "candidate_id": candidate_id,
        "github_analysis": analysis,
        "new_skills_added": len(enriched.skills) - len(candidate.skills),
        "projects_added": len(enriched.projects) - len(candidate.projects),
        "updated_summary": enriched.summary
    }


@router.get("/{candidate_id}/github-analysis")
async def get_github_analysis(
    candidate_id: str,
    workflow: ResumeIngestionWorkflow = Depends(get_resume_ingestion_workflow)
):
    """
    Get GitHub profile analysis for a candidate.
    
    Fetches fresh data from GitHub API.
    """
    candidate = workflow.get_candidate(candidate_id)
    
    if not candidate:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found")
    
    if not candidate.github_url:
        raise HTTPException(
            status_code=400,
            detail="No GitHub URL associated with this candidate"
        )
    
    resume_agent = workflow.resume_agent
    analysis = resume_agent.analyze_github_profile(candidate.github_url)
    
    if 'error' in analysis:
        raise HTTPException(status_code=400, detail=analysis['error'])
    
    # Generate summary
    summary = resume_agent.generate_github_summary(analysis)
    analysis['ai_summary'] = summary
    
    return analysis
