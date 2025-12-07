"""Tests for agents."""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from app.agents.jd_context_agent import JDContextAgent
from app.agents.resume_analysis_agent import ResumeAnalysisAgent
from app.agents.ranking_agent import RankingAgent
from app.models.job_context import JobContext
from app.models.candidate import Candidate
from app.models.score_report import ScoreReport


class TestJDContextAgent:
    """Tests for JDContextAgent."""
    
    @pytest.fixture
    def mock_llm(self):
        llm = Mock()
        llm.generate_structured = AsyncMock()
        return llm
    
    @pytest.fixture
    def mock_chroma(self):
        chroma = Mock()
        chroma.add_job = Mock()
        return chroma
    
    @pytest.fixture
    def agent(self, mock_llm, mock_chroma):
        return JDContextAgent(mock_llm, mock_chroma)
    
    @pytest.mark.asyncio
    async def test_extract_context(self, agent, mock_llm):
        """Test JD context extraction."""
        mock_job_context = {
            "title": "Python Developer",
            "company": "Tech Corp",
            "required_skills": ["Python", "FastAPI"],
            "preferred_skills": ["Docker"],
            "experience_years": 3,
            "education_requirement": "Bachelor's",
            "responsibilities": ["Build APIs"],
            "summary": "Test summary"
        }
        mock_llm.generate_structured.return_value = mock_job_context
        
        result = await agent.extract_context("Test JD")
        
        assert result is not None
        mock_llm.generate_structured.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_store_job(self, agent, mock_chroma, mock_llm):
        """Test storing job in vector DB."""
        mock_llm.generate_structured.return_value = {
            "title": "Python Developer",
            "company": "Tech Corp",
            "required_skills": ["Python"],
            "preferred_skills": [],
            "experience_years": 3,
            "education_requirement": "Bachelor's",
            "responsibilities": ["Build APIs"],
            "summary": "Test summary"
        }
        
        job_context = await agent.extract_context("Test JD")
        agent.store_job("job_1", job_context, "Test JD")
        
        mock_chroma.add_job.assert_called_once()


class TestResumeAnalysisAgent:
    """Tests for ResumeAnalysisAgent."""
    
    @pytest.fixture
    def mock_llm(self):
        llm = Mock()
        llm.generate_structured = AsyncMock()
        return llm
    
    @pytest.fixture
    def mock_extractor(self):
        return Mock()
    
    @pytest.fixture
    def agent(self, mock_llm, mock_extractor):
        return ResumeAnalysisAgent(mock_llm, mock_extractor)
    
    @pytest.mark.asyncio
    async def test_analyze_resume(self, agent, mock_llm):
        """Test resume analysis."""
        mock_candidate = {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "123-456-7890",
            "skills": ["Python", "FastAPI"],
            "experience": [],
            "education": [],
            "projects": [],
            "certifications": [],
            "summary": "Experienced developer"
        }
        mock_llm.generate_structured.return_value = mock_candidate
        
        result = await agent.analyze("Sample resume text")
        
        assert result is not None
        mock_llm.generate_structured.assert_called_once()


class TestRankingAgent:
    """Tests for RankingAgent."""
    
    @pytest.fixture
    def mock_llm(self):
        llm = Mock()
        llm.generate_structured = AsyncMock()
        return llm
    
    @pytest.fixture
    def mock_scoring(self):
        scoring = Mock()
        scoring.calculate_weighted_score = Mock(return_value=85.0)
        return scoring
    
    @pytest.fixture
    def agent(self, mock_llm, mock_scoring):
        return RankingAgent(mock_llm, mock_scoring)
    
    @pytest.mark.asyncio
    async def test_evaluate_candidate(self, agent, mock_llm):
        """Test candidate evaluation."""
        mock_evaluation = {
            "candidate_id": "c1",
            "job_id": "j1",
            "overall_score": 85.0,
            "skills_match_score": 90.0,
            "experience_score": 80.0,
            "education_score": 85.0,
            "culture_fit_score": 80.0,
            "matched_skills": ["Python", "FastAPI"],
            "missing_skills": ["Docker"],
            "strengths": ["Strong Python"],
            "weaknesses": ["No Docker experience"],
            "recommendation": "Strong candidate",
            "rank": 1
        }
        mock_llm.generate_structured.return_value = mock_evaluation
        
        job_context = JobContext(
            title="Python Developer",
            company="Tech Corp",
            required_skills=["Python", "FastAPI"],
            preferred_skills=["Docker"],
            experience_years=3,
            education_requirement="Bachelor's",
            responsibilities=["Build APIs"],
            summary="Test job"
        )
        
        candidate = Candidate(
            name="John Doe",
            email="john@example.com",
            skills=["Python", "FastAPI"],
            experience=[],
            education=[],
            projects=[],
            certifications=[],
            summary="Developer"
        )
        
        result = await agent.evaluate(candidate, job_context, "c1", "j1")
        
        assert result is not None
        mock_llm.generate_structured.assert_called_once()
