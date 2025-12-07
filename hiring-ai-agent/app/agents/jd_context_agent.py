"""
JD Context Agent - Extract structured job context from job descriptions.
"""
from typing import Optional
from pydantic import BaseModel, Field
from typing import List

from app.models.job_context import JobContext
from app.utils.logger import get_logger
from app.utils.text_cleaner import TextCleaner

logger = get_logger(__name__)


class ExtractedJobData(BaseModel):
    """Intermediate model for LLM extraction."""
    job_title: str
    seniority: Optional[str] = None
    required_skills: List[str] = []
    preferred_skills: List[str] = []
    experience_required: Optional[str] = None
    experience_min_years: Optional[float] = None
    experience_max_years: Optional[float] = None
    responsibilities: List[str] = []
    domain: Optional[str] = None
    job_summary: Optional[str] = None
    location: Optional[str] = None
    remote_policy: Optional[str] = None


class JDContextAgent:
    """
    Agent that extracts structured job context from messy job descriptions
    or hiring manager conversations.
    """
    
    def __init__(self, llm):
        """
        Initialize JD Context Agent.
        
        Args:
            llm: GeminiLLM instance
        """
        self.llm = llm
        self.text_cleaner = TextCleaner()
    
    def extract_job_context(self, raw_text: str, title_hint: Optional[str] = None) -> JobContext:
        """
        Extract structured job context from raw JD text.
        
        Args:
            raw_text: Raw job description text or conversation transcript
            title_hint: Optional hint for job title
            
        Returns:
            Structured JobContext model
        """
        # Clean the input text
        cleaned_text = self.text_cleaner.clean_jd_text(raw_text)
        
        # Build prompt
        prompt = self._build_extraction_prompt(cleaned_text, title_hint)
        
        # Extract using LLM
        try:
            extracted = self.llm.generate_structured(
                prompt=prompt,
                output_model=ExtractedJobData,
                temperature=0.2,
                system_instruction=self._get_system_instruction()
            )
            
            # Convert to JobContext
            job_context = JobContext(
                job_title=extracted.job_title,
                seniority=extracted.seniority,
                required_skills=self._normalize_skills(extracted.required_skills),
                preferred_skills=self._normalize_skills(extracted.preferred_skills),
                experience_required=extracted.experience_required,
                experience_min_years=extracted.experience_min_years,
                experience_max_years=extracted.experience_max_years,
                responsibilities=extracted.responsibilities,
                domain=extracted.domain,
                job_summary=extracted.job_summary,
                location=extracted.location,
                remote_policy=extracted.remote_policy,
                raw_text=raw_text
            )
            
            logger.info(f"Extracted job context: {job_context.job_title}")
            return job_context
            
        except Exception as e:
            logger.error(f"Failed to extract job context: {e}")
            raise
    
    def _build_extraction_prompt(self, text: str, title_hint: Optional[str] = None) -> str:
        """Build the extraction prompt."""
        hint_section = ""
        if title_hint:
            hint_section = f"\nNote: The job title is likely '{title_hint}'.\n"
        
        return f"""Analyze this job description and extract structured information.
{hint_section}
JOB DESCRIPTION TEXT:
{text}

Extract the following information:

1. **Job Title**: The exact role name (e.g., "Senior AI Engineer", "Backend Developer")

2. **Seniority Level**: One of: Junior, Mid, Senior, Lead, Principal, Staff, or null if unclear

3. **Required Skills** (must-have): Technical skills explicitly marked as required or mandatory.
   - Normalize skill names (e.g., "JS" -> "JavaScript")
   - Include both technical and soft skills if marked as required

4. **Preferred Skills** (nice-to-have): Skills mentioned as preferred, bonus, or plus

5. **Experience Required**: The stated experience requirement as text (e.g., "3-5 years")
   - Also extract as numbers: experience_min_years and experience_max_years

6. **Responsibilities**: Key job duties and responsibilities as a list

7. **Domain**: The industry or technical domain (e.g., "Fintech", "Healthcare AI", "E-commerce")

8. **Job Summary**: Write a 2-3 sentence summary of the role

9. **Location**: Job location if mentioned

10. **Remote Policy**: One of: Remote, Hybrid, Onsite, or null if not mentioned

Be thorough but accurate. Only include information that is clearly stated or strongly implied.
If something is not mentioned, use null instead of guessing."""

    def _get_system_instruction(self) -> str:
        """Get the system instruction for the LLM."""
        return """You are an expert HR analyst specializing in technical job descriptions.
Your task is to extract structured information from job descriptions accurately.

Guidelines:
- Be precise with skill names - normalize common abbreviations
- Distinguish clearly between required and preferred skills
- If experience is mentioned as "X+ years", set min to X and max to X+3
- For seniority, infer from title and experience requirements if not explicit
- Keep responsibilities concise and actionable
- Domain should be the business/technical domain, not generic terms"""

    def _normalize_skills(self, skills: List[str]) -> List[str]:
        """Normalize skill names for consistency."""
        normalized = []
        seen = set()
        
        for skill in skills:
            # Use text cleaner's normalize function
            norm_skill = self.text_cleaner.normalize_skill(skill.strip())
            
            # Deduplicate
            if norm_skill.lower() not in seen:
                seen.add(norm_skill.lower())
                normalized.append(norm_skill)
        
        return normalized
    
    def refine_job_context(
        self,
        job_context: JobContext,
        additional_info: str
    ) -> JobContext:
        """
        Refine an existing job context with additional information.
        
        Args:
            job_context: Existing JobContext
            additional_info: New information to incorporate
            
        Returns:
            Updated JobContext
        """
        prompt = f"""You have an existing job context and need to update it with new information.

EXISTING JOB CONTEXT:
- Title: {job_context.job_title}
- Required Skills: {job_context.required_skills}
- Preferred Skills: {job_context.preferred_skills}
- Experience: {job_context.experience_required}
- Domain: {job_context.domain}

NEW INFORMATION TO INCORPORATE:
{additional_info}

Update the job context by:
1. Adding any new skills mentioned
2. Updating experience requirements if changed
3. Adding responsibilities if mentioned
4. Keeping existing information unless explicitly changed

Return the complete updated job context."""

        try:
            extracted = self.llm.generate_structured(
                prompt=prompt,
                output_model=ExtractedJobData,
                temperature=0.2
            )
            
            # Merge with existing
            updated = JobContext(
                id=job_context.id,
                job_title=extracted.job_title or job_context.job_title,
                seniority=extracted.seniority or job_context.seniority,
                required_skills=self._normalize_skills(
                    list(set(job_context.required_skills + extracted.required_skills))
                ),
                preferred_skills=self._normalize_skills(
                    list(set(job_context.preferred_skills + extracted.preferred_skills))
                ),
                experience_required=extracted.experience_required or job_context.experience_required,
                experience_min_years=extracted.experience_min_years or job_context.experience_min_years,
                experience_max_years=extracted.experience_max_years or job_context.experience_max_years,
                responsibilities=list(set(job_context.responsibilities + extracted.responsibilities)),
                domain=extracted.domain or job_context.domain,
                job_summary=extracted.job_summary or job_context.job_summary,
                location=extracted.location or job_context.location,
                remote_policy=extracted.remote_policy or job_context.remote_policy,
                raw_text=job_context.raw_text
            )
            
            return updated
            
        except Exception as e:
            logger.error(f"Failed to refine job context: {e}")
            return job_context  # Return original on failure
