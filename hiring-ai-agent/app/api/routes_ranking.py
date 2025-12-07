"""
Ranking API Routes - Endpoints for candidate ranking and assessment.
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional

from app.models.score_report import ScoreReport, RankingReport
from app.workflows.ranking_workflow import RankingWorkflow
from app.workflows.assessment_workflow import AssessmentWorkflow
from app.dependencies import get_ranking_workflow, get_assessment_workflow
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/ranking", tags=["Rankings"])


class AssessRequest(BaseModel):
    """Request for single candidate assessment."""
    candidate_id: str
    job_id: str
    force_refresh: bool = False


class CompareRequest(BaseModel):
    """Request for comparing multiple candidates."""
    candidate_ids: List[str]
    job_id: str


class ScoreReportResponse(BaseModel):
    """API response for score report."""
    id: Optional[str]
    candidate_id: str
    job_id: str
    candidate_name: Optional[str]
    overall_score: float
    skill_match_score: float
    experience_match_score: float
    semantic_similarity_score: float
    matched_skills: List[str]
    missing_skills: List[str]
    strengths: List[str]
    weaknesses: List[str]
    reasoning: Optional[str]
    recommendation: Optional[str]


class RankingReportResponse(BaseModel):
    """API response for full ranking report."""
    job_id: str
    job_title: str
    total_candidates: int
    rankings: List[ScoreReportResponse]
    top_candidates_summary: Optional[str]


@router.get("/{job_id}", response_model=RankingReportResponse)
async def get_rankings_for_job(
    job_id: str,
    top_k: Optional[int] = None,
    force_refresh: bool = False,
    workflow: RankingWorkflow = Depends(get_ranking_workflow)
):
    """
    Get ranked list of candidates for a job.
    
    Runs the full ranking pipeline:
    1. Finds all relevant candidates
    2. Scores each against job requirements
    3. Generates LLM analysis (strengths/weaknesses)
    4. Returns sorted results
    
    Set force_refresh=true to regenerate all scores.
    """
    try:
        report = workflow.rank_all_candidates(
            job_id=job_id,
            top_k=top_k,
            force_refresh=force_refresh
        )
        
        return RankingReportResponse(
            job_id=report.job_id,
            job_title=report.job_title,
            total_candidates=report.total_candidates,
            rankings=[
                ScoreReportResponse(
                    id=r.id,
                    candidate_id=r.candidate_id,
                    job_id=r.job_id,
                    candidate_name=r.candidate_name,
                    overall_score=r.overall_score,
                    skill_match_score=r.skill_match_score,
                    experience_match_score=r.experience_match_score,
                    semantic_similarity_score=r.semantic_similarity_score,
                    matched_skills=r.matched_skills,
                    missing_skills=r.missing_skills,
                    strengths=r.strengths,
                    weaknesses=r.weaknesses,
                    reasoning=r.reasoning,
                    recommendation=r.recommendation
                )
                for r in report.rankings
            ],
            top_candidates_summary=report.top_candidates_summary
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Ranking failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/{job_id}/refresh")
async def refresh_rankings_for_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    workflow: RankingWorkflow = Depends(get_ranking_workflow)
):
    """
    Trigger ranking computation for a job in the background.

    This starts the full ranking pipeline asynchronously and returns immediately.
    Use this when you want to precompute scores (e.g., after bulk upload) and
    avoid recomputing on each frontend view.
    """
    try:
        # Schedule the ranking to run in background
        background_tasks.add_task(workflow.rank_all_candidates, job_id, None, True)
        return {"status": "started", "job_id": job_id}
    except Exception as e:
        logger.error(f"Failed to start background ranking for {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}/top/{limit}", response_model=List[ScoreReportResponse])
async def get_top_candidates(
    job_id: str,
    limit: int = 5,
    workflow: RankingWorkflow = Depends(get_ranking_workflow)
):
    """
    Get top N candidates for a job.
    
    Returns the highest-scoring candidates based on existing rankings.
    """
    reports = workflow.get_top_candidates(job_id, limit)
    
    return [
        ScoreReportResponse(
            id=r.id,
            candidate_id=r.candidate_id,
            job_id=r.job_id,
            candidate_name=r.candidate_name,
            overall_score=r.overall_score,
            skill_match_score=r.skill_match_score,
            experience_match_score=r.experience_match_score,
            semantic_similarity_score=r.semantic_similarity_score,
            matched_skills=r.matched_skills,
            missing_skills=r.missing_skills,
            strengths=r.strengths,
            weaknesses=r.weaknesses,
            reasoning=r.reasoning,
            recommendation=r.recommendation
        )
        for r in reports
    ]


@router.get("/{job_id}/{candidate_id}", response_model=ScoreReportResponse)
async def get_candidate_score(
    job_id: str,
    candidate_id: str,
    workflow: AssessmentWorkflow = Depends(get_assessment_workflow)
):
    """
    Get individual score report for a candidate-job pair.
    
    If not already scored, generates a new assessment.
    """
    try:
        report = workflow.assess_candidate(
            candidate_id=candidate_id,
            job_id=job_id,
            force_refresh=False
        )
        
        return ScoreReportResponse(
            id=report.id,
            candidate_id=report.candidate_id,
            job_id=report.job_id,
            candidate_name=report.candidate_name,
            overall_score=report.overall_score,
            skill_match_score=report.skill_match_score,
            experience_match_score=report.experience_match_score,
            semantic_similarity_score=report.semantic_similarity_score,
            matched_skills=report.matched_skills,
            missing_skills=report.missing_skills,
            strengths=report.strengths,
            weaknesses=report.weaknesses,
            reasoning=report.reasoning,
            recommendation=report.recommendation
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Assessment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/assess", response_model=ScoreReportResponse)
async def assess_candidate(
    request: AssessRequest,
    workflow: AssessmentWorkflow = Depends(get_assessment_workflow)
):
    """
    Assess a specific candidate for a job.
    
    Generates or retrieves a score report with:
    - Overall score
    - Skill match breakdown
    - Experience alignment
    - LLM-generated strengths and weaknesses
    - Recommendation (Interview/Maybe/Reject)
    """
    try:
        report = workflow.assess_candidate(
            candidate_id=request.candidate_id,
            job_id=request.job_id,
            force_refresh=request.force_refresh
        )
        
        return ScoreReportResponse(
            id=report.id,
            candidate_id=report.candidate_id,
            job_id=report.job_id,
            candidate_name=report.candidate_name,
            overall_score=report.overall_score,
            skill_match_score=report.skill_match_score,
            experience_match_score=report.experience_match_score,
            semantic_similarity_score=report.semantic_similarity_score,
            matched_skills=report.matched_skills,
            missing_skills=report.missing_skills,
            strengths=report.strengths,
            weaknesses=report.weaknesses,
            reasoning=report.reasoning,
            recommendation=report.recommendation
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Assessment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare")
async def compare_candidates(
    request: CompareRequest,
    workflow: RankingWorkflow = Depends(get_ranking_workflow)
):
    """
    Compare specific candidates for a job.
    
    Scores and ranks the specified candidates, returning
    a comparison with the best candidate highlighted.
    """
    try:
        result = workflow.compare_candidates(
            candidate_ids=request.candidate_ids,
            job_id=request.job_id
        )
        
        return {
            "job_id": result["job_id"],
            "job_title": result["job_title"],
            "candidates_compared": result["candidates_compared"],
            "rankings": [
                ScoreReportResponse(
                    id=r.id,
                    candidate_id=r.candidate_id,
                    job_id=r.job_id,
                    candidate_name=r.candidate_name,
                    overall_score=r.overall_score,
                    skill_match_score=r.skill_match_score,
                    experience_match_score=r.experience_match_score,
                    semantic_similarity_score=r.semantic_similarity_score,
                    matched_skills=r.matched_skills,
                    missing_skills=r.missing_skills,
                    strengths=r.strengths,
                    weaknesses=r.weaknesses,
                    reasoning=r.reasoning,
                    recommendation=r.recommendation
                ).model_dump()
                for r in result["rankings"]
            ],
            "best_candidate": result["best_candidate"].candidate_name if result["best_candidate"] else None,
            "summary": result["summary"]
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Comparison failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
