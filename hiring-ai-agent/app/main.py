"""
Hiring AI Agent - Main FastAPI Application

A multi-agent system for automated resume screening and candidate ranking.
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import get_settings, ensure_directories
from app.api.routes_job import router as job_router
from app.api.routes_resume import router as resume_router
from app.api.routes_ranking import router as ranking_router
from app.utils.error_handler import AppException, app_exception_handler
from app.utils.logger import setup_logger, get_logger
from app.dependencies import (
    get_email_ingest_agent,
    get_resume_ingestion_workflow,
    get_job_context_workflow
)

# Initialize logger
setup_logger("hiring_agent")
logger = get_logger(__name__)

# Scheduler for email polling
scheduler = AsyncIOScheduler()


async def poll_email_inbox():
    """Background task to poll email inbox for new applications."""
    settings = get_settings()
    
    if not settings.email_enabled:
        return
    
    logger.info("Polling email inbox for new applications...")
    
    try:
        email_agent = get_email_ingest_agent()
        resume_workflow = get_resume_ingestion_workflow()
        job_workflow = get_job_context_workflow()
        
        if not email_agent.is_configured():
            return
        
        def process_email_resume(
            job_title: str,
            pdf_bytes: bytes,
            filename: str,
            sender: str,
            message_id: str
        ):
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
                
            except Exception as e:
                logger.error(f"Failed to process email resume from {sender}: {e}")
        
        count = email_agent.poll_and_process(process_email_resume)
        logger.info(f"Email poll complete: {count} resumes processed")
        
    except Exception as e:
        logger.error(f"Email polling failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Hiring AI Agent...")
    
    # Ensure data directories exist
    ensure_directories()
    
    # Start email polling scheduler if enabled
    settings = get_settings()
    if settings.email_enabled:
        scheduler.add_job(
            poll_email_inbox,
            'interval',
            minutes=settings.email_poll_interval_minutes,
            id='email_poll'
        )
        scheduler.start()
        logger.info(f"Email polling enabled (every {settings.email_poll_interval_minutes} minutes)")
    
    logger.info("Hiring AI Agent started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Hiring AI Agent...")
    if scheduler.running:
        scheduler.shutdown()
    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Hiring AI Agent",
    description="""
    An AI-powered hiring assistant that automates resume screening and candidate ranking.
    
    ## Features
    
    * **Job Context Extraction**: Parse job descriptions into structured requirements
    * **Resume Analysis**: Extract candidate information from PDF resumes
    * **Automated Ranking**: Score and rank candidates using AI
    * **Email Ingestion**: Automatically process resumes from email
    
    ## Workflow
    
    1. Create a job context with POST /job/create
    2. Upload resumes with POST /resume/upload
    3. Get rankings with GET /ranking/{job_id}
    """,
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add exception handler
app.add_exception_handler(AppException, app_exception_handler)

# Include routers
app.include_router(job_router)
app.include_router(resume_router)
app.include_router(ranking_router)


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - API information."""
    return {
        "name": "Hiring AI Agent",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    settings = get_settings()
    
    return {
        "status": "healthy",
        "email_enabled": settings.email_enabled,
        "gemini_configured": bool(settings.gemini_api_key),
    }


@app.post("/email/trigger", tags=["Email"])
async def trigger_email_poll():
    """Manually trigger email inbox polling."""
    settings = get_settings()
    
    if not settings.email_enabled:
        return {
            "status": "disabled",
            "message": "Email ingestion is not enabled"
        }
    
    # Run poll in background
    asyncio.create_task(poll_email_inbox())
    
    return {
        "status": "triggered",
        "message": "Email polling started in background"
    }


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
