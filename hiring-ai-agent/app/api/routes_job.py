"""
Job API Routes - Endpoints for job context management.
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional

from app.models.job_context import JobContext, JobContextCreate, JobContextResponse
from app.workflows.job_context_workflow import JobContextWorkflow
from app.dependencies import get_job_context_workflow
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/job", tags=["Jobs"])


class JobCreateRequest(BaseModel):
    """Request body for creating a job."""
    description: str
  


class JobUpdateRequest(BaseModel):
    """Request body for updating a job."""
    additional_info: str


@router.post("/create", response_model=JobContextResponse)
async def create_job(
    request: JobCreateRequest,
    workflow: JobContextWorkflow = Depends(get_job_context_workflow)
):
    """
    Create a new job context from a job description.
    
    Takes raw JD text or hiring manager conversation and extracts
    structured job requirements, skills, and responsibilities.
    """
    try:
        job = workflow.process_job_description(
            raw_text=request.description,
            title_hint=None
        )
        
        return JobContextResponse(
            id=job.id,
            job_title=job.job_title,
            seniority=job.seniority,
            required_skills=job.required_skills,
            preferred_skills=job.preferred_skills,
            experience_required=job.experience_required,
            responsibilities=job.responsibilities,
            domain=job.domain,
            job_summary=job.job_summary,
            created_at=job.created_at
        )
    except Exception as e:
        logger.error(f"Failed to create job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}", response_model=JobContextResponse)
async def get_job(
    job_id: str,
    workflow: JobContextWorkflow = Depends(get_job_context_workflow)
):
    """
    Get a job by ID.
    
    Returns the structured job context with all extracted fields.
    """
    job = workflow.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    return JobContextResponse(
        id=job.id,
        job_title=job.job_title,
        seniority=job.seniority,
        required_skills=job.required_skills,
        preferred_skills=job.preferred_skills,
        experience_required=job.experience_required,
        responsibilities=job.responsibilities,
        domain=job.domain,
        job_summary=job.job_summary,
        created_at=job.created_at
    )


@router.get("/", response_model=List[JobContextResponse])
async def list_jobs(
    limit: int = 100,
    workflow: JobContextWorkflow = Depends(get_job_context_workflow)
):
    """
    List all jobs.
    
    Returns a list of job contexts, ordered by creation date.
    """
    jobs = workflow.list_jobs(limit=limit)
    
    return [
        JobContextResponse(
            id=job.id,
            job_title=job.job_title,
            seniority=job.seniority,
            required_skills=job.required_skills,
            preferred_skills=job.preferred_skills,
            experience_required=job.experience_required,
            responsibilities=job.responsibilities,
            domain=job.domain,
            job_summary=job.job_summary,
            created_at=job.created_at
        )
        for job in jobs
    ]


@router.get("/search/{title}")
async def search_job_by_title(
    title: str,
    workflow: JobContextWorkflow = Depends(get_job_context_workflow)
):
    """
    Search for a job by title.
    
    Returns the job context if found, or 404 if not found.
    """
    job = workflow.find_job_by_title(title)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job with title '{title}' not found")
    
    return JobContextResponse(
        id=job.id,
        job_title=job.job_title,
        seniority=job.seniority,
        required_skills=job.required_skills,
        preferred_skills=job.preferred_skills,
        experience_required=job.experience_required,
        responsibilities=job.responsibilities,
        domain=job.domain,
        job_summary=job.job_summary,
        created_at=job.created_at
    )


@router.post("/{job_id}/update", response_model=JobContextResponse)
async def update_job(
    job_id: str,
    request: JobUpdateRequest,
    workflow: JobContextWorkflow = Depends(get_job_context_workflow)
):
    """
    Update a job with additional information.
    
    Refines the existing job context by adding new requirements or details.
    """
    job = workflow.update_job(job_id, request.additional_info)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    return JobContextResponse(
        id=job.id,
        job_title=job.job_title,
        seniority=job.seniority,
        required_skills=job.required_skills,
        preferred_skills=job.preferred_skills,
        experience_required=job.experience_required,
        responsibilities=job.responsibilities,
        domain=job.domain,
        job_summary=job.job_summary,
        created_at=job.created_at
    )


@router.delete("/{job_id}")
async def delete_job(
    job_id: str,
    workflow: JobContextWorkflow = Depends(get_job_context_workflow)
):
    """
    Delete a job and its embedding from Chroma. By default this will not delete candidate rows;
    the client can call the cascade endpoint to remove candidates for the job as well.
    """
    job = workflow.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Attempt to remove embedding
    try:
        workflow.chroma.delete(
            collection_name=workflow.settings.chroma_collection_jobs,
            ids=[job_id]
        )
    except Exception as e:
        # Log but continue
        logger.warning(f"Chroma deletion warning for job {job_id}: {e}")

    removed = workflow.db.delete_job(job_id)

    return {"deleted": bool(removed)}


@router.delete("/{job_id}/candidates")
async def delete_candidates_for_job(
    job_id: str,
    workflow: JobContextWorkflow = Depends(get_job_context_workflow)
):
    """
    Delete all candidates associated with a job (and their embeddings and files).
    """
    job = workflow.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Collect and delete candidate embeddings from chroma
    deleted_info = workflow.db.delete_candidates_by_job(job_id)
    candidate_ids = deleted_info.get("deleted_candidate_ids", [])
    resume_paths = deleted_info.get("resume_paths", [])

    if candidate_ids:
        try:
            workflow.chroma.delete(
                collection_name=workflow.settings.chroma_collection_candidates,
                ids=candidate_ids
            )
        except Exception as e:
            logger.warning(f"Chroma deletion warning for candidates of job {job_id}: {e}")

    # Delete files
    deleted_files = 0
    from pathlib import Path
    for p in resume_paths:
        if not p:
            continue
        pp = Path(p)
        if pp.exists():
            try:
                pp.unlink()
                deleted_files += 1
            except Exception as e:
                logger.warning(f"Failed to delete resume file {p}: {e}")

    # Also remove any score reports directly tied to the job (already handled in DB method)

    return {"deleted_candidate_count": len(candidate_ids), "deleted_files": deleted_files}
