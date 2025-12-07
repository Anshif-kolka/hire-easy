"""
Score Report model - candidate evaluation results.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ScoreReport(BaseModel):
    """Individual candidate evaluation against a job."""
    
    id: Optional[str] = Field(default=None, description="Unique score report ID")
    candidate_id: str = Field(..., description="Candidate ID")
    job_id: str = Field(..., description="Job ID")
    candidate_name: Optional[str] = Field(default=None, description="Candidate name for display")
    
    # Scores (0-100)
    overall_score: float = Field(..., ge=0, le=100, description="Final weighted score")
    skill_match_score: float = Field(default=0, ge=0, le=100, description="Skill overlap score")
    experience_match_score: float = Field(default=0, ge=0, le=100, description="Experience alignment score")
    semantic_similarity_score: float = Field(default=0, ge=0, le=100, description="Semantic similarity score")
    
    # Skill breakdown
    matched_skills: List[str] = Field(default_factory=list, description="Skills that match JD")
    missing_skills: List[str] = Field(default_factory=list, description="Required skills candidate lacks")
    extra_skills: List[str] = Field(default_factory=list, description="Additional skills not in JD")
    
    # LLM-generated analysis
    strengths: List[str] = Field(default_factory=list, description="Candidate strengths")
    weaknesses: List[str] = Field(default_factory=list, description="Candidate weaknesses/gaps")
    reasoning: Optional[str] = Field(default=None, description="LLM reasoning for the score")
    recommendation: Optional[str] = Field(default=None, description="Hire/Interview/Reject recommendation")
    
    # Metadata
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "SCORE-001",
                "candidate_id": "CAND-001",
                "job_id": "JOB-2024-001",
                "candidate_name": "Rahul Nair",
                "overall_score": 82.5,
                "skill_match_score": 85.0,
                "experience_match_score": 78.0,
                "semantic_similarity_score": 84.0,
                "matched_skills": ["Python", "FastAPI", "LLMs"],
                "missing_skills": ["AWS", "Kubernetes"],
                "extra_skills": ["Docker", "PostgreSQL"],
                "strengths": [
                    "Strong Python background",
                    "Hands-on LLM experience",
                    "Relevant project portfolio"
                ],
                "weaknesses": [
                    "Limited cloud infrastructure experience",
                    "No system design experience mentioned"
                ],
                "reasoning": "Strong technical match for AI Engineer role with solid LLM experience...",
                "recommendation": "Interview"
            }
        }


class RankingReport(BaseModel):
    """Full ranking report for all candidates for a job."""
    
    job_id: str
    job_title: str
    total_candidates: int
    
    rankings: List[ScoreReport] = Field(default_factory=list, description="Sorted list of candidate scores")
    
    top_candidates_summary: Optional[str] = Field(
        default=None, 
        description="LLM summary of top candidates"
    )
    
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "JOB-2024-001",
                "job_title": "AI Engineer",
                "total_candidates": 15,
                "rankings": [
                    {
                        "candidate_id": "CAND-001",
                        "candidate_name": "Rahul Nair",
                        "overall_score": 92,
                        "recommendation": "Strong Interview"
                    },
                    {
                        "candidate_id": "CAND-002", 
                        "candidate_name": "Priya Sharma",
                        "overall_score": 85,
                        "recommendation": "Interview"
                    }
                ],
                "top_candidates_summary": "Top candidate Rahul Nair shows exceptional fit..."
            }
        }
