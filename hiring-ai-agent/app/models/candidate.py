"""
Candidate model - structured representation of a candidate's resume.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class Experience(BaseModel):
    """Structured work experience entry."""
    company: Optional[str] = None
    role: Optional[str] = None
    duration: Optional[str] = None  # e.g., "Jan 2020 - Dec 2022"
    duration_months: Optional[int] = None
    description: Optional[str] = None
    skills_used: List[str] = Field(default_factory=list)


class Education(BaseModel):
    """Structured education entry."""
    institution: Optional[str] = None
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    year: Optional[str] = None
    gpa: Optional[str] = None


class Project(BaseModel):
    """Structured project entry."""
    name: Optional[str] = None
    description: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)
    url: Optional[str] = None


class Candidate(BaseModel):
    """Structured candidate profile extracted from resume."""
    
    id: Optional[str] = Field(default=None, description="Unique candidate ID")
    
    # Personal info
    name: Optional[str] = Field(default=None, description="Candidate's full name")
    email: Optional[str] = Field(default=None, description="Email address")
    phone: Optional[str] = Field(default=None, description="Phone number")
    location: Optional[str] = Field(default=None, description="City/Country")
    headline: Optional[str] = Field(default=None, description="Professional headline/title")
    
    # Core data
    skills: List[str] = Field(default_factory=list, description="Technical and soft skills")
    experience: List[Experience] = Field(default_factory=list, description="Work experience entries")
    education: List[Education] = Field(default_factory=list, description="Education entries")
    projects: List[Project] = Field(default_factory=list, description="Notable projects")
    certifications: List[str] = Field(default_factory=list, description="Certifications")
    finish_message: Optional[str] = None  # Add this line

    # Computed fields
    total_experience_years: Optional[float] = Field(default=None, description="Total years of experience")
    summary: Optional[str] = Field(default=None, description="LLM-generated candidate summary")
    
    # URLs
    github_url: Optional[str] = Field(default=None, description="GitHub profile URL")
    linkedin_url: Optional[str] = Field(default=None, description="LinkedIn URL")
    portfolio_url: Optional[str] = Field(default=None, description="Portfolio/website URL")
    
    # Source tracking
    source: Optional[str] = Field(default="upload", description="How resume was received (upload, email)")
    is_linkedin_pdf: bool = Field(default=False, description="If resume came from LinkedIn PDF export")
    raw_text: Optional[str] = Field(default=None, description="Original resume text")
    resume_file_path: Optional[str] = Field(default=None, description="Path to stored resume PDF file")
    
    # Vector embedding
    embedding_vector: Optional[List[float]] = Field(default=None, description="Vector embedding")
    
    # Metadata
    job_id: Optional[str] = Field(default=None, description="Associated job ID (if applied via email)")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "CAND-001",
                "name": "Rahul Nair",
                "email": "rahul@example.com",
                "phone": "+91-9876543210",
                "headline": "AI Engineer | LLM Specialist",
                "skills": ["Python", "FastAPI", "LangChain", "Docker", "PostgreSQL"],
                "experience": [
                    {
                        "company": "TechCorp",
                        "role": "ML Engineer",
                        "duration": "Jan 2022 - Present",
                        "duration_months": 24,
                        "description": "Built LLM pipelines for document processing"
                    }
                ],
                "education": [
                    {
                        "institution": "IIT Delhi",
                        "degree": "B.Tech",
                        "field_of_study": "Computer Science",
                        "year": "2021"
                    }
                ],
                "projects": [
                    {
                        "name": "RAG FAQ Bot",
                        "description": "Built a retrieval-augmented generation chatbot",
                        "technologies": ["Python", "LangChain", "ChromaDB"]
                    }
                ],
                "total_experience_years": 2.5,
                "github_url": "https://github.com/rahulnair",
                "source": "email"
            }
        }


class CandidateResponse(BaseModel):
    """API response model for candidate."""
    id: str
    name: Optional[str]
    email: Optional[str]
    headline: Optional[str]
    skills: List[str]
    total_experience_years: Optional[float]
    summary: Optional[str]
    source: str
    job_id: Optional[str]
    created_at: datetime
