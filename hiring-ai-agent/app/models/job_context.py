"""
Job Context model - structured representation of a job description.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class JobContext(BaseModel):
    """Structured job description extracted by JD Context Agent."""
    
    id: Optional[str] = Field(default=None, description="Unique job ID")
    job_title: str = Field(..., description="Job title/role name")
    seniority: Optional[str] = Field(default=None, description="Seniority level (Junior, Mid, Senior, Lead)")
    
    required_skills: List[str] = Field(default_factory=list, description="Must-have skills")
    preferred_skills: List[str] = Field(default_factory=list, description="Nice-to-have skills")
    
    experience_required: Optional[str] = Field(default=None, description="Required years of experience")
    experience_min_years: Optional[float] = Field(default=None, description="Minimum years as number")
    experience_max_years: Optional[float] = Field(default=None, description="Maximum years as number")
    
    responsibilities: List[str] = Field(default_factory=list, description="Key job responsibilities")
    domain: Optional[str] = Field(default=None, description="Industry/domain (e.g., Fintech, Healthcare, AI)")
    
    job_summary: Optional[str] = Field(default=None, description="LLM-generated job summary")
    raw_text: Optional[str] = Field(default=None, description="Original JD text")
    
    location: Optional[str] = Field(default=None, description="Job location")
    remote_policy: Optional[str] = Field(default=None, description="Remote/Hybrid/Onsite")
    
    embedding_vector: Optional[List[float]] = Field(default=None, description="Vector embedding for similarity search")
    
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "JOB-2024-001",
                "job_title": "AI Engineer",
                "seniority": "Mid",
                "required_skills": ["Python", "FastAPI", "LLMs", "LangChain"],
                "preferred_skills": ["Docker", "RAG systems", "AWS"],
                "experience_required": "3-5 years",
                "experience_min_years": 3.0,
                "experience_max_years": 5.0,
                "responsibilities": [
                    "Build LLM-powered applications",
                    "Design and implement AI workflows",
                    "Collaborate with product team"
                ],
                "domain": "Generative AI",
                "job_summary": "Looking for an engineer to build LLM-driven workflows...",
                "location": "Remote",
                "remote_policy": "Remote"
            }
        }


class JobContextCreate(BaseModel):
    """Input model for creating a job context."""
    raw_text: str = Field(..., description="Raw job description text or conversation transcript")
    job_title: Optional[str] = Field(default=None, description="Optional job title hint")


class JobContextResponse(BaseModel):
    """API response model for job context."""
    id: str
    job_title: str
    seniority: Optional[str]
    required_skills: List[str]
    preferred_skills: List[str]
    experience_required: Optional[str]
    responsibilities: List[str]
    domain: Optional[str]
    job_summary: Optional[str]
    created_at: datetime
