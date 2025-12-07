"""
FastAPI dependency injection.
Provides shared instances of services, agents, and workflows.
"""
from functools import lru_cache
from typing import Generator

from app.config import get_settings, Settings
from app.services.gemini_llm import GeminiLLM
from app.services.chroma_db import ChromaStore
from app.services.pdf_parser import PDFParser
from app.services.resume_extractor import ResumeExtractor
from app.services.scoring_utils import ScoringUtils
from app.database.store import DatabaseStore
from app.agents.jd_context_agent import JDContextAgent
from app.agents.resume_analysis_agent import ResumeAnalysisAgent
from app.agents.ranking_agent import RankingAgent
from app.agents.email_ingest_agent import EmailIngestAgent
from app.workflows.job_context_workflow import JobContextWorkflow
from app.workflows.resume_ingestion_workflow import ResumeIngestionWorkflow
from app.workflows.assessment_workflow import AssessmentWorkflow
from app.workflows.ranking_workflow import RankingWorkflow


# ============ Services ============

@lru_cache()
def get_llm() -> GeminiLLM:
    """Get singleton LLM instance."""
    settings = get_settings()
    return GeminiLLM(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
        embedding_model=settings.gemini_embedding_model
    )


@lru_cache()
def get_chroma_store() -> ChromaStore:
    """Get singleton ChromaDB instance."""
    settings = get_settings()
    return ChromaStore(persist_dir=settings.chroma_persist_dir)


@lru_cache()
def get_database() -> DatabaseStore:
    """Get singleton database instance."""
    settings = get_settings()
    return DatabaseStore(db_path=settings.database_path)


def get_pdf_parser() -> PDFParser:
    """Get PDF parser instance."""
    return PDFParser()


def get_resume_extractor() -> ResumeExtractor:
    """Get resume extractor instance."""
    return ResumeExtractor(llm=get_llm())


def get_scoring_utils() -> ScoringUtils:
    """Get scoring utilities instance."""
    settings = get_settings()
    return ScoringUtils(
        llm=get_llm(),
        weights={
            "semantic_similarity": settings.weight_semantic_similarity,
            "skill_match": settings.weight_skill_match,
            "experience_match": settings.weight_experience_match
        }
    )


# ============ Agents ============

def get_jd_context_agent() -> JDContextAgent:
    """Get JD Context Agent instance."""
    return JDContextAgent(llm=get_llm())


def get_resume_analysis_agent() -> ResumeAnalysisAgent:
    """Get Resume Analysis Agent instance."""
    return ResumeAnalysisAgent(llm=get_llm())


def get_ranking_agent() -> RankingAgent:
    """Get Ranking Agent instance."""
    return RankingAgent(
        llm=get_llm(),
        scoring_utils=get_scoring_utils()
    )


def get_email_ingest_agent() -> EmailIngestAgent:
    """Get Email Ingest Agent instance."""
    settings = get_settings()
    return EmailIngestAgent(
        imap_server=settings.email_imap_server,
        email_address=settings.email_address,
        email_password=settings.email_password,
        folder=settings.email_folder,
        subject_pattern=settings.email_subject_pattern
    )


# ============ Workflows ============

def get_job_context_workflow() -> JobContextWorkflow:
    """Get Job Context Workflow instance."""
    return JobContextWorkflow(
        agent=get_jd_context_agent(),
        chroma_store=get_chroma_store(),
        database=get_database(),
        llm=get_llm()
    )


def get_resume_ingestion_workflow() -> ResumeIngestionWorkflow:
    """Get Resume Ingestion Workflow instance."""
    return ResumeIngestionWorkflow(
        pdf_parser=get_pdf_parser(),
        resume_agent=get_resume_analysis_agent(),
        chroma_store=get_chroma_store(),
        database=get_database(),
        llm=get_llm()
    )


def get_assessment_workflow() -> AssessmentWorkflow:
    """Get Assessment Workflow instance."""
    return AssessmentWorkflow(
        ranking_agent=get_ranking_agent(),
        chroma_store=get_chroma_store(),
        database=get_database()
    )


def get_ranking_workflow() -> RankingWorkflow:
    """Get Ranking Workflow instance."""
    return RankingWorkflow(
        assessment_workflow=get_assessment_workflow(),
        ranking_agent=get_ranking_agent(),
        chroma_store=get_chroma_store(),
        database=get_database()
    )
