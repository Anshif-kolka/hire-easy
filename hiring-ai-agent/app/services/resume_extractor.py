"""
Resume Extractor - Clean and structure resume text using LLM.
"""
import re
from typing import Dict, List, Optional
from pydantic import BaseModel

from app.models.candidate import Candidate, Experience, Education, Project
from app.utils.logger import get_logger
from app.utils.text_cleaner import TextCleaner

logger = get_logger(__name__)


class ExtractedResumeData(BaseModel):
    """Intermediate model for LLM extraction."""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    headline: Optional[str] = None
    summary: Optional[str] = None
    skills: List[str] = []
    experience: List[Dict] = []
    education: List[Dict] = []
    projects: List[Dict] = []
    certifications: List[str] = []
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    total_experience_years: Optional[float] = None


class ResumeExtractor:
    """
    Extract structured information from resume text using LLM + heuristics.
    """
    
    def __init__(self, llm):
        """
        Initialize resume extractor.
        
        Args:
            llm: GeminiLLM instance
        """
        self.llm = llm
        self.text_cleaner = TextCleaner()
    
    def extract(self, raw_text: str, is_linkedin: bool = False) -> Candidate:
        """
        Extract structured candidate data from resume text.
        
        Args:
            raw_text: Raw text from PDF
            is_linkedin: Whether this is a LinkedIn PDF export
            
        Returns:
            Candidate model with extracted data
        """
        # Clean the text first
        cleaned_text = self.text_cleaner.clean_resume_text(raw_text)
        
        # Extract using LLM
        extracted = self._extract_with_llm(cleaned_text, is_linkedin)
        
        # Extract URLs using regex (more reliable)
        urls = self._extract_urls(raw_text)
        
        # Build Candidate model
        candidate = Candidate(
            name=extracted.name,
            email=extracted.email or self._extract_email(raw_text),
            phone=extracted.phone or self._extract_phone(raw_text),
            location=extracted.location,
            headline=extracted.headline,
            summary=extracted.summary,
            skills=self._normalize_skills(extracted.skills),
            experience=[Experience(**exp) for exp in extracted.experience],
            education=[Education(**edu) for edu in extracted.education],
            projects=[Project(**proj) for proj in extracted.projects],
            certifications=extracted.certifications,
            github_url=extracted.github_url or urls.get('github'),
            linkedin_url=extracted.linkedin_url or urls.get('linkedin'),
            portfolio_url=extracted.portfolio_url or urls.get('portfolio'),
            total_experience_years=extracted.total_experience_years,
            is_linkedin_pdf=is_linkedin,
            raw_text=raw_text
        )
        
        logger.info(f"Extracted candidate: {candidate.name}, {len(candidate.skills)} skills")
        
        return candidate
    
    def _extract_with_llm(self, text: str, is_linkedin: bool) -> ExtractedResumeData:
        """
        Use LLM to extract structured data from resume text.
        """
        source_hint = "LinkedIn PDF export" if is_linkedin else "resume/CV"
        
        prompt = f"""Analyze this {source_hint} and extract structured information.

RESUME TEXT:
{text}

Extract the following information:
1. Personal details (name, email, phone, location)
2. Professional headline/title
3. A brief professional summary
4. All technical and soft skills (as a list)
5. Work experience (company, role, duration, description, skills used)
6. Education (institution, degree, field, year)
7. Notable projects (name, description, technologies)
8. Certifications
9. URLs (GitHub, LinkedIn, portfolio)
10. Total years of professional experience (estimate if not explicit)

For experience duration, try to calculate duration_months.
Normalize skill names (e.g., "JS" -> "JavaScript", "ML" -> "Machine Learning").
If information is not found, use null.

Return the data as JSON matching the required schema."""

        try:
            extracted = self.llm.generate_structured(
                prompt=prompt,
                output_model=ExtractedResumeData,
                temperature=0.2
            )
            return extracted
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            # Return empty extraction on failure
            return ExtractedResumeData()
    
    def _extract_email(self, text: str) -> Optional[str]:
        """Extract email using regex."""
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        match = re.search(pattern, text)
        return match.group(0) if match else None
    
    def _extract_phone(self, text: str) -> Optional[str]:
        """Extract phone number using regex."""
        patterns = [
            r'\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}',  # US
            r'\+91[-.\s]?[0-9]{10}',  # India
            r'\+?[0-9]{10,14}',  # Generic international
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        return None
    
    def _extract_urls(self, text: str) -> Dict[str, str]:
        """Extract URLs from text."""
        urls = {}
        
        # GitHub
        github_pattern = r'(?:https?://)?(?:www\.)?github\.com/[\w-]+'
        match = re.search(github_pattern, text, re.IGNORECASE)
        if match:
            url = match.group(0)
            if not url.startswith('http'):
                url = 'https://' + url
            urls['github'] = url
        
        # LinkedIn
        linkedin_pattern = r'(?:https?://)?(?:www\.)?linkedin\.com/in/[\w-]+'
        match = re.search(linkedin_pattern, text, re.IGNORECASE)
        if match:
            url = match.group(0)
            if not url.startswith('http'):
                url = 'https://' + url
            urls['linkedin'] = url
        
        # Generic portfolio (common patterns)
        portfolio_patterns = [
            r'(?:https?://)?(?:www\.)?[\w-]+\.(?:dev|io|com|me)/?\S*',
        ]
        for pattern in portfolio_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                url = match.group(0)
                # Exclude common non-portfolio domains
                if not any(domain in url.lower() for domain in ['github.com', 'linkedin.com', 'gmail.com', 'email']):
                    if not url.startswith('http'):
                        url = 'https://' + url
                    urls['portfolio'] = url
                    break
        
        return urls
    
    def _normalize_skills(self, skills: List[str]) -> List[str]:
        """Normalize skill names for consistency."""
        # Common normalizations
        normalizations = {
            'js': 'JavaScript',
            'ts': 'TypeScript',
            'py': 'Python',
            'ml': 'Machine Learning',
            'dl': 'Deep Learning',
            'ai': 'Artificial Intelligence',
            'nlp': 'Natural Language Processing',
            'cv': 'Computer Vision',
            'aws': 'AWS',
            'gcp': 'Google Cloud',
            'k8s': 'Kubernetes',
            'postgres': 'PostgreSQL',
            'mongo': 'MongoDB',
            'react.js': 'React',
            'reactjs': 'React',
            'node.js': 'Node.js',
            'nodejs': 'Node.js',
            'vue.js': 'Vue.js',
            'vuejs': 'Vue.js',
        }
        
        normalized = []
        seen = set()
        
        for skill in skills:
            # Normalize
            skill_lower = skill.lower().strip()
            if skill_lower in normalizations:
                skill = normalizations[skill_lower]
            else:
                # Title case for consistency, but preserve known acronyms
                if skill_lower not in ['aws', 'gcp', 'api', 'sql', 'css', 'html', 'ci/cd']:
                    skill = skill.title()
            
            # Deduplicate (case-insensitive)
            if skill.lower() not in seen:
                seen.add(skill.lower())
                normalized.append(skill)
        
        return normalized
