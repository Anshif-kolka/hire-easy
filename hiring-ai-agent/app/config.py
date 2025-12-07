"""
Application configuration settings.
Loads environment variables and provides centralized config access.
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # App settings
    app_name: str = "Hiring AI Agent"
    debug: bool = False
    
    # Gemini API
    gemini_api_key: str = Field(..., env="GEMINI_API_KEY")
    gemini_model: str = "gemini-flash-latest"
    gemini_embedding_model: str = "models/text-embedding-004"
    
    # Database
    database_path: str = "data/hiring_agent.db"
    
    # ChromaDB
    chroma_persist_dir: str = "data/chroma_db"
    chroma_collection_jobs: str = "job_contexts"
    chroma_collection_candidates: str = "candidates"
    
    # Email settings (for IMAP polling)
    email_enabled: bool = False
    email_imap_server: str = "imap.gmail.com"
    email_address: Optional[str] = None
    email_password: Optional[str] = None  # Gmail App Password
    email_folder: str = "INBOX"
    email_subject_pattern: str = r"^JOB\s*-\s*(.+?)\s*-\s*APPLICATION$"
    email_poll_interval_minutes: int = 5
    
    # File storage
    # Base data directory (used for resumes, uploads, chroma, etc.)
    data_dir: str = "data"
    upload_dir: str = "data/uploads"
    max_file_size_mb: int = 10
    
    # Scoring weights
    weight_semantic_similarity: float = 0.4
    weight_skill_match: float = 0.35
    weight_experience_match: float = 0.25
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the application settings."""
    return settings


def ensure_directories():
    """Ensure required directories exist."""
    dirs = [
        settings.chroma_persist_dir,
        settings.upload_dir,
        Path(settings.database_path).parent,
        Path(settings.data_dir) / "resumes",
        Path(settings.data_dir) / "uploads"
    ]
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
