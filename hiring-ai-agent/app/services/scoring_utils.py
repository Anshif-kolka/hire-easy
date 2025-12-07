"""
Scoring Utilities - Match scoring and similarity functions.
"""
from typing import Dict, List, Optional, Set
import math

from app.models.job_context import JobContext
from app.models.candidate import Candidate
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ScoringUtils:
    """
    Compute candidate scores based on skill match, experience, and semantic similarity.
    """
    
    DEFAULT_WEIGHTS = {
        "semantic_similarity": 0.4,
        "skill_match": 0.35,
        "experience_match": 0.25
    }
    
    def __init__(self, llm, weights: Optional[Dict[str, float]] = None):
        """
        Initialize scoring utilities.
        
        Args:
            llm: GeminiLLM instance for embeddings
            weights: Custom scoring weights
        """
        self.llm = llm
        self.weights = weights or self.DEFAULT_WEIGHTS
    
    def calculate_skill_match(
        self,
        candidate_skills: List[str],
        required_skills: List[str],
        preferred_skills: List[str]
    ) -> Dict[str, any]:
        """
        Calculate skill match score.
        
        Args:
            candidate_skills: Candidate's skills
            required_skills: Must-have skills from JD
            preferred_skills: Nice-to-have skills from JD
            
        Returns:
            Dict with score, matched, missing, extra skills
        """
        # Normalize all skills to lowercase for comparison
        candidate_set = {s.lower() for s in candidate_skills}
        required_set = {s.lower() for s in required_skills}
        preferred_set = {s.lower() for s in preferred_skills}
        all_jd_skills = required_set | preferred_set
        
        # Find matches
        matched_required = candidate_set & required_set
        matched_preferred = candidate_set & preferred_set
        missing_required = required_set - candidate_set
        missing_preferred = preferred_set - candidate_set
        extra_skills = candidate_set - all_jd_skills
        
        # Calculate score
        # Required skills are worth more
        required_score = 0
        if required_set:
            required_score = (len(matched_required) / len(required_set)) * 70  # 70% weight
        
        preferred_score = 0
        if preferred_set:
            preferred_score = (len(matched_preferred) / len(preferred_set)) * 30  # 30% weight
        
        total_score = required_score + preferred_score
        
        # Map back to original case
        def get_original(skill_set: Set[str], original_list: List[str]) -> List[str]:
            original_map = {s.lower(): s for s in original_list}
            return [original_map.get(s, s) for s in skill_set]
        
        return {
            "score": round(total_score, 2),
            "matched_required": get_original(matched_required, required_skills),
            "matched_preferred": get_original(matched_preferred, preferred_skills),
            "missing_required": get_original(missing_required, required_skills),
            "missing_preferred": get_original(missing_preferred, preferred_skills),
            "extra_skills": list(extra_skills),
            "match_percentage": round(
                (len(matched_required) + len(matched_preferred)) / 
                max(len(all_jd_skills), 1) * 100, 2
            )
        }
    
    def calculate_experience_match(
        self,
        candidate_years: Optional[float],
        required_min: Optional[float],
        required_max: Optional[float]
    ) -> Dict[str, any]:
        """
        Calculate experience match score.
        
        Args:
            candidate_years: Candidate's years of experience
            required_min: Minimum required years
            required_max: Maximum required years (or None)
            
        Returns:
            Dict with score and analysis
        """
        if candidate_years is None:
            return {
                "score": 50.0,  # Neutral score when unknown
                "status": "unknown",
                "message": "Experience not specified in resume"
            }
        
        if required_min is None:
            return {
                "score": 75.0,  # Decent score when JD doesn't specify
                "status": "not_specified",
                "message": "Experience requirement not specified in job"
            }
        
        # Calculate score based on range
        if required_max is None:
            required_max = required_min + 5  # Assume 5 year range
        
        if candidate_years >= required_min and candidate_years <= required_max:
            # Perfect match - in range
            score = 100.0
            status = "match"
            message = f"Experience ({candidate_years} years) is within required range ({required_min}-{required_max} years)"
        elif candidate_years < required_min:
            # Under-qualified
            gap = required_min - candidate_years
            score = max(0, 100 - (gap * 15))  # Lose 15 points per year under
            status = "under"
            message = f"Experience ({candidate_years} years) is {gap:.1f} years below minimum ({required_min} years)"
        else:
            # Over-qualified (slight penalty, might be overqualified)
            excess = candidate_years - required_max
            score = max(70, 100 - (excess * 5))  # Slight penalty for overqualified
            status = "over"
            message = f"Experience ({candidate_years} years) exceeds range by {excess:.1f} years"
        
        return {
            "score": round(score, 2),
            "status": status,
            "message": message,
            "candidate_years": candidate_years,
            "required_range": f"{required_min}-{required_max} years"
        }
    
    def calculate_semantic_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Similarity score (0-100)
        """
        if not embedding1 or not embedding2:
            return 50.0  # Neutral if embeddings missing
        
        # Cosine similarity
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        norm1 = math.sqrt(sum(a * a for a in embedding1))
        norm2 = math.sqrt(sum(b * b for b in embedding2))
        
        if norm1 == 0 or norm2 == 0:
            return 50.0
        
        similarity = dot_product / (norm1 * norm2)
        
        # Convert to 0-100 scale (cosine sim is -1 to 1, but usually 0-1 for text)
        score = (similarity + 1) * 50  # Map -1,1 to 0,100
        
        return round(min(100, max(0, score)), 2)
    
    def calculate_final_score(
        self,
        skill_score: float,
        experience_score: float,
        semantic_score: float,
        weights: Optional[Dict[str, float]] = None
    ) -> float:
        """
        Calculate weighted final score.
        
        Args:
            skill_score: Skill match score (0-100)
            experience_score: Experience match score (0-100)
            semantic_score: Semantic similarity score (0-100)
            weights: Custom weights (optional)
            
        Returns:
            Final weighted score (0-100)
        """
        w = weights or self.weights
        
        final = (
            skill_score * w["skill_match"] +
            experience_score * w["experience_match"] +
            semantic_score * w["semantic_similarity"]
        )
        
        return round(final, 2)
    
    def score_candidate(
        self,
        candidate: Candidate,
        job: JobContext,
        candidate_embedding: Optional[List[float]] = None,
        job_embedding: Optional[List[float]] = None
    ) -> Dict[str, any]:
        """
        Full scoring of a candidate against a job.
        
        Args:
            candidate: Candidate model
            job: JobContext model
            candidate_embedding: Pre-computed candidate embedding
            job_embedding: Pre-computed job embedding
            
        Returns:
            Complete scoring breakdown
        """
        # Skill match
        skill_result = self.calculate_skill_match(
            candidate_skills=candidate.skills,
            required_skills=job.required_skills,
            preferred_skills=job.preferred_skills
        )
        
        # Experience match
        experience_result = self.calculate_experience_match(
            candidate_years=candidate.total_experience_years,
            required_min=job.experience_min_years,
            required_max=job.experience_max_years
        )
        
        # Semantic similarity
        semantic_score = 50.0  # Default
        if candidate_embedding and job_embedding:
            semantic_score = self.calculate_semantic_similarity(
                candidate_embedding,
                job_embedding
            )
        
        # Final score
        final_score = self.calculate_final_score(
            skill_score=skill_result["score"],
            experience_score=experience_result["score"],
            semantic_score=semantic_score
        )
        
        return {
            "overall_score": final_score,
            "skill_match": skill_result,
            "experience_match": experience_result,
            "semantic_similarity": semantic_score,
            "weights_used": self.weights
        }
