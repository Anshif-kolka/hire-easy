from .routes_job import router as job_router
from .routes_resume import router as resume_router
from .routes_ranking import router as ranking_router

__all__ = ["job_router", "resume_router", "ranking_router"]
