"""
Ranking Agent - Score and rank candidates against job requirements.
"""
from typing import List, Optional
from pydantic import BaseModel

from app.models.job_context import JobContext
from app.models.candidate import Candidate
from app.models.score_report import ScoreReport
from app.services.scoring_utils import ScoringUtils
from app.utils.logger import get_logger

logger = get_logger(__name__)


class LLMEvaluation(BaseModel):
    """LLM-generated evaluation output."""
    strengths: List[str] = []
    weaknesses: List[str] = []
    reasoning: str = ""
    recommendation: str = ""  # Strong Interview, Interview, Maybe, Reject


class RankingAgent:
    """
    Agent that evaluates candidates and generates rankings with detailed analysis.
    """
    
    def __init__(self, llm, scoring_utils: ScoringUtils):
        """
        Initialize Ranking Agent.
        
        Args:
            llm: GeminiLLM instance
            scoring_utils: ScoringUtils instance
        """
        self.llm = llm
        self.scoring_utils = scoring_utils
    
    def generate_candidate_rank(
        self,
        candidate: Candidate,
        job: JobContext,
        candidate_embedding: Optional[List[float]] = None,
        job_embedding: Optional[List[float]] = None
    ) -> ScoreReport:
        """
        Generate a complete ranking report for a candidate.
        
        Args:
            candidate: Candidate model
            job: JobContext model
            candidate_embedding: Pre-computed candidate embedding
            job_embedding: Pre-computed job embedding
            
        Returns:
            ScoreReport with scores and analysis
        """
        logger.info(f"Ranking candidate {candidate.name} for {job.job_title}")
        
        # Calculate numerical scores
        scores = self.scoring_utils.score_candidate(
            candidate=candidate,
            job=job,
            candidate_embedding=candidate_embedding,
            job_embedding=job_embedding
        )
        
        # Get LLM evaluation (strengths, weaknesses, reasoning)
        evaluation = self._get_llm_evaluation(candidate, job, scores)
        
        # Build score report
        skill_result = scores["skill_match"]
        
        report = ScoreReport(
            candidate_id=candidate.id or "unknown",
            job_id=job.id or "unknown",
            candidate_name=candidate.name,
            overall_score=scores["overall_score"],
            skill_match_score=skill_result["score"],
            experience_match_score=scores["experience_match"]["score"],
            semantic_similarity_score=scores["semantic_similarity"],
            matched_skills=skill_result["matched_required"] + skill_result["matched_preferred"],
            missing_skills=skill_result["missing_required"],
            extra_skills=skill_result["extra_skills"][:10],  # Limit extras
            strengths=evaluation.strengths,
            weaknesses=evaluation.weaknesses,
            reasoning=evaluation.reasoning,
            recommendation=evaluation.recommendation
        )
        
        logger.info(
            f"Ranked {candidate.name}: {report.overall_score:.1f} - {report.recommendation}"
        )
        
        return report
    
    def _get_llm_evaluation(
        self,
        candidate: Candidate,
        job: JobContext,
        scores: dict
    ) -> LLMEvaluation:
        """
        Get LLM-generated evaluation of candidate.
        
        Args:
            candidate: Candidate model
            job: JobContext model
            scores: Calculated scores dict
            
        Returns:
            LLMEvaluation with strengths, weaknesses, reasoning
        """
        skill_result = scores["skill_match"]
        exp_result = scores["experience_match"]
        
        prompt = f"""Evaluate this candidate for the job role.

JOB REQUIREMENTS:
- Title: {job.job_title}
- Seniority: {job.seniority or 'Not specified'}
- Required Skills: {', '.join(job.required_skills)}
- Preferred Skills: {', '.join(job.preferred_skills)}
- Experience: {job.experience_required or 'Not specified'}
- Domain: {job.domain or 'Not specified'}

CANDIDATE PROFILE:
- Name: {candidate.name}
- Headline: {candidate.headline or 'Not specified'}
- Experience: {candidate.total_experience_years or 'Unknown'} years
- Skills: {', '.join(candidate.skills[:20])}
- Summary: {candidate.summary or 'Not available'}

SCORING RESULTS:
- Overall Score: {scores['overall_score']:.1f}/100
- Skill Match: {skill_result['score']:.1f}/100
  - Matched Required: {skill_result['matched_required']}
  - Missing Required: {skill_result['missing_required']}
- Experience Match: {exp_result['score']:.1f}/100 ({exp_result['status']})

Based on this analysis, provide:

1. **Strengths** (3-5 bullet points): What makes this candidate a good fit?

2. **Weaknesses** (2-4 bullet points): What gaps or concerns exist?

3. **Reasoning**: A 2-3 sentence explanation of the overall assessment.

4. **Recommendation**: One of:
   - "Strong Interview" (score 85+, excellent fit)
   - "Interview" (score 70-84, good potential)
   - "Maybe" (score 55-69, some concerns)
   - "Reject" (score <55, significant gaps)

Be objective and specific. Reference actual skills and experience."""

        try:
            evaluation = self.llm.generate_structured(
                prompt=prompt,
                output_model=LLMEvaluation,
                temperature=0.3
            )
            return evaluation
            
        except Exception as e:
            logger.error(f"LLM evaluation failed: {e}")
            # Return default evaluation based on score
            score = scores["overall_score"]
            if score >= 85:
                rec = "Strong Interview"
            elif score >= 70:
                rec = "Interview"
            elif score >= 55:
                rec = "Maybe"
            else:
                rec = "Reject"
            
            return LLMEvaluation(
                strengths=["Analysis unavailable"],
                weaknesses=["Analysis unavailable"],
                reasoning=f"Score-based recommendation: {score:.1f}/100",
                recommendation=rec
            )
    
    def rank_candidates(
        self,
        candidates: List[Candidate],
        job: JobContext,
        candidate_embeddings: Optional[dict] = None,
        job_embedding: Optional[List[float]] = None
    ) -> List[ScoreReport]:
        """
        Rank multiple candidates for a job.
        
        Args:
            candidates: List of candidates
            job: Job context
            candidate_embeddings: Dict of candidate_id -> embedding
            job_embedding: Job embedding
            
        Returns:
            List of ScoreReports sorted by score (descending)
        """
        candidate_embeddings = candidate_embeddings or {}
        
        reports = []
        for candidate in candidates:
            cand_embedding = candidate_embeddings.get(candidate.id)
            report = self.generate_candidate_rank(
                candidate=candidate,
                job=job,
                candidate_embedding=cand_embedding,
                job_embedding=job_embedding
            )
            reports.append(report)
        
        # Sort by overall score (descending)
        reports.sort(key=lambda r: r.overall_score, reverse=True)
        
        return reports
    
    def generate_ranking_summary(
        self,
        reports: List[ScoreReport],
        job: JobContext
    ) -> str:
        """
        Generate a summary of the top candidates.
        
        Args:
            reports: Sorted list of score reports
            job: Job context
            
        Returns:
            Summary text
        """
        if not reports:
            return "No candidates to summarize."
        
        top_3 = reports[:3]
        
        candidates_text = "\n".join([
            f"{i+1}. {r.candidate_name}: {r.overall_score:.1f}/100 - {r.recommendation}"
            for i, r in enumerate(top_3)
        ])
        
        prompt = f"""Summarize the top candidates for this {job.job_title} position.

TOP CANDIDATES:
{candidates_text}

Top Candidate Strengths: {top_3[0].strengths if top_3 else []}
Top Candidate Weaknesses: {top_3[0].weaknesses if top_3 else []}

Write a 3-4 sentence executive summary highlighting:
1. The best candidate and why
2. Overall quality of the candidate pool
3. Any notable patterns or concerns"""

        try:
            summary = self.llm.generate_text(
                prompt=prompt,
                temperature=0.4,
                max_tokens=250
            )
            return summary.strip()
        except Exception as e:
            logger.warning(f"Failed to generate ranking summary: {e}")
            if top_3:
                return f"Top candidate: {top_3[0].candidate_name} with score {top_3[0].overall_score:.1f}/100"
            return "Unable to generate summary."
