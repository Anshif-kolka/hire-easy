"""
Resume Analysis Agent - Parse and extract structured information from resumes.
Includes GitHub profile analysis.
"""
import re
import urllib.request
import json
from typing import Optional, Dict, List, Any

from app.models.candidate import Candidate
from app.services.resume_extractor import ResumeExtractor
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ResumeAnalysisAgent:
    """
    Agent that parses resumes and extracts structured candidate information.
    """
    
    def __init__(self, llm):
        """
        Initialize Resume Analysis Agent.
        
        Args:
            llm: GeminiLLM instance
        """
        self.llm = llm
        self.extractor = ResumeExtractor(llm)
    
    def parse_resume(
        self,
        raw_text: str,
        is_linkedin: bool = False,
        source: str = "upload",
        job_id: Optional[str] = None
    ) -> Candidate:
        """
        Parse resume text and extract structured candidate data.
        
        Args:
            raw_text: Raw text extracted from resume PDF
            is_linkedin: Whether this is a LinkedIn PDF export
            source: How the resume was received (upload, email)
            job_id: Associated job ID (if from email application)
            
        Returns:
            Structured Candidate model
        """
        logger.info(f"Parsing resume (source={source}, linkedin={is_linkedin})")
        
        # Use the extractor to get structured data
        candidate = self.extractor.extract(raw_text, is_linkedin)
        
        # Set additional metadata
        candidate.source = source
        candidate.job_id = job_id
        
        # Generate a summary if not already present
        if not candidate.summary:
            candidate.summary = self._generate_summary(candidate)
        
        logger.info(f"Parsed resume: {candidate.name}, {len(candidate.skills)} skills")
        return candidate
    
    def _generate_summary(self, candidate: Candidate) -> str:
        """
        Generate a professional summary for the candidate.
        
        Args:
            candidate: Partially parsed candidate
            
        Returns:
            Generated summary text
        """
        # Build context for summary generation
        skills_str = ", ".join(candidate.skills[:10]) if candidate.skills else "not specified"
        exp_str = f"{candidate.total_experience_years} years" if candidate.total_experience_years else "experience not specified"
        
        recent_roles = []
        for exp in candidate.experience[:2]:
            if exp.role and exp.company:
                recent_roles.append(f"{exp.role} at {exp.company}")
        roles_str = "; ".join(recent_roles) if recent_roles else "roles not specified"
        
        prompt = f"""Write a brief 2-3 sentence professional summary for this candidate:

Name: {candidate.name or 'Unknown'}
Headline: {candidate.headline or 'Not specified'}
Experience: {exp_str}
Recent Roles: {roles_str}
Key Skills: {skills_str}

Write in third person. Focus on their experience level, main skills, and career focus.
Be professional and concise."""

        try:
            summary = self.llm.generate_text(
                prompt=prompt,
                temperature=0.5,
                max_tokens=150
            )
            return summary.strip()
        except Exception as e:
            logger.warning(f"Failed to generate summary: {e}")
            return ""
    
    def analyze_fit(self, candidate: Candidate, job_title: str) -> str:
        """
        Generate a quick analysis of candidate fit for a role.
        
        Args:
            candidate: Candidate model
            job_title: Job title to analyze fit for
            
        Returns:
            Fit analysis text
        """
        skills_str = ", ".join(candidate.skills[:15]) if candidate.skills else "none listed"
        exp_str = f"{candidate.total_experience_years} years" if candidate.total_experience_years else "unknown"
        
        prompt = f"""Briefly analyze this candidate's fit for a {job_title} role:

Candidate: {candidate.name}
Experience: {exp_str}
Skills: {skills_str}
Background: {candidate.summary or 'Not available'}

Provide a 2-3 sentence assessment of their potential fit. Be objective."""

        try:
            analysis = self.llm.generate_text(
                prompt=prompt,
                temperature=0.4,
                max_tokens=200
            )
            return analysis.strip()
        except Exception as e:
            logger.warning(f"Failed to analyze fit: {e}")
            return "Unable to generate fit analysis."
    
    def enrich_candidate(self, candidate: Candidate, additional_info: str) -> Candidate:
        """
        Enrich candidate data with additional information.
        
        Args:
            candidate: Existing candidate data
            additional_info: Additional text to extract from
            
        Returns:
            Enriched candidate
        """
        prompt = f"""You have existing candidate data and need to enrich it with new information.

EXISTING CANDIDATE:
- Name: {candidate.name}
- Skills: {candidate.skills}
- Experience Years: {candidate.total_experience_years}

NEW INFORMATION:
{additional_info}

Extract any additional:
1. Skills not already listed
2. Projects or achievements
3. Certifications
4. URLs (GitHub, portfolio)

Return only the NEW information found, not duplicates."""

        try:
            response = self.llm.generate_text(
                prompt=prompt,
                temperature=0.3
            )
            
            # For now, just log. Full implementation would parse and merge.
            logger.info(f"Enrichment response for {candidate.name}: {response[:100]}...")
            
            return candidate
            
        except Exception as e:
            logger.warning(f"Failed to enrich candidate: {e}")
            return candidate

    # =========================================================================
    # GitHub Analysis Methods
    # =========================================================================
    
    def extract_github_url(self, text: str) -> Optional[str]:
        """
        Extract GitHub URL from resume text.
        
        Args:
            text: Resume text
            
        Returns:
            GitHub profile URL or None
        """
        # Match various GitHub URL formats
        patterns = [
            r'github\.com/([a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38})',
            r'https?://github\.com/([a-zA-Z0-9_-]+)',
            r'github:\s*@?([a-zA-Z0-9_-]+)',
            r'GitHub:\s*([a-zA-Z0-9_-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                username = match.group(1)
                # Clean up username
                username = username.strip('/')
                if username and len(username) > 0:
                    url = f"https://github.com/{username}"
                    logger.info(f"Found GitHub URL: {url}")
                    return url
        
        return None
    
    def extract_github_username(self, github_url: str) -> Optional[str]:
        """
        Extract username from GitHub URL.
        
        Args:
            github_url: Full GitHub URL
            
        Returns:
            Username string
        """
        match = re.search(r'github\.com/([a-zA-Z0-9_-]+)', github_url)
        if match:
            return match.group(1)
        return None
    
    def fetch_github_profile(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Fetch GitHub user profile via public API.
        
        Args:
            username: GitHub username
            
        Returns:
            User profile dict or None
        """
        try:
            url = f"https://api.github.com/users/{username}"
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'HiringAIAgent/1.0'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                logger.info(f"Fetched GitHub profile for {username}")
                return data
                
        except Exception as e:
            logger.warning(f"Failed to fetch GitHub profile for {username}: {e}")
            return None
    
    def fetch_github_repos(self, username: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch user's public repositories.
        
        Args:
            username: GitHub username
            limit: Max number of repos to fetch
            
        Returns:
            List of repository data
        """
        try:
            url = f"https://api.github.com/users/{username}/repos?sort=updated&per_page={limit}"
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'HiringAIAgent/1.0'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                repos = json.loads(response.read().decode())
                logger.info(f"Fetched {len(repos)} repos for {username}")
                return repos
                
        except Exception as e:
            logger.warning(f"Failed to fetch repos for {username}: {e}")
            return []
    
    def analyze_github_profile(self, github_url: str) -> Dict[str, Any]:
        """
        Analyze a GitHub profile and extract relevant information.
        
        Args:
            github_url: GitHub profile URL
            
        Returns:
            Analysis dict with skills, repos, stats
        """
        username = self.extract_github_username(github_url)
        if not username:
            logger.warning(f"Could not extract username from {github_url}")
            return {"error": "Invalid GitHub URL"}
        
        # Fetch profile and repos
        profile = self.fetch_github_profile(username)
        repos = self.fetch_github_repos(username, limit=15)
        
        if not profile:
            return {"error": "Could not fetch GitHub profile"}
        
        # Extract languages/skills from repos
        languages = {}
        repo_summaries = []
        total_stars = 0
        
        for repo in repos:
            if repo.get('fork', False):
                continue  # Skip forked repos
            
            lang = repo.get('language')
            if lang:
                languages[lang] = languages.get(lang, 0) + 1
            
            stars = repo.get('stargazers_count', 0)
            total_stars += stars
            
            repo_summaries.append({
                'name': repo.get('name'),
                'description': repo.get('description', '')[:100] if repo.get('description') else '',
                'language': lang,
                'stars': stars,
                'url': repo.get('html_url')
            })
        
        # Sort languages by frequency
        top_languages = sorted(languages.items(), key=lambda x: -x[1])[:8]
        
        analysis = {
            'username': username,
            'url': github_url,
            'name': profile.get('name'),
            'bio': profile.get('bio'),
            'company': profile.get('company'),
            'location': profile.get('location'),
            'public_repos': profile.get('public_repos', 0),
            'followers': profile.get('followers', 0),
            'following': profile.get('following', 0),
            'total_stars': total_stars,
            'top_languages': [lang for lang, _ in top_languages],
            'top_repos': repo_summaries[:5],
            'created_at': profile.get('created_at'),
        }
        
        logger.info(f"GitHub analysis for {username}: {len(top_languages)} languages, {total_stars} stars")
        return analysis
    
    def generate_github_summary(self, github_analysis: Dict[str, Any]) -> str:
        """
        Generate an LLM summary of GitHub profile.
        
        Args:
            github_analysis: Analysis dict from analyze_github_profile
            
        Returns:
            Summary string
        """
        if 'error' in github_analysis:
            return ""
        
        repos_text = "\n".join([
            f"- {r['name']}: {r['description']} ({r['language']}, {r['stars']} stars)"
            for r in github_analysis.get('top_repos', [])[:5]
        ])
        
        prompt = f"""Analyze this GitHub profile and provide a brief technical assessment:

Username: {github_analysis.get('username')}
Bio: {github_analysis.get('bio', 'Not provided')}
Public Repos: {github_analysis.get('public_repos', 0)}
Total Stars: {github_analysis.get('total_stars', 0)}
Followers: {github_analysis.get('followers', 0)}
Top Languages: {', '.join(github_analysis.get('top_languages', []))}

Notable Repositories:
{repos_text}

Provide a 2-3 sentence assessment of:
1. Their technical strengths based on languages/projects
2. Activity level and open source contribution
3. Overall GitHub presence quality

Be objective and concise."""

        try:
            summary = self.llm.generate_text(
                prompt=prompt,
                temperature=0.4,
                max_tokens=200
            )
            return summary.strip()
        except Exception as e:
            logger.warning(f"Failed to generate GitHub summary: {e}")
            return ""
    
    def enrich_candidate_with_github(self, candidate: Candidate) -> Candidate:
        """
        Enrich candidate with GitHub analysis if URL is available.
        
        Args:
            candidate: Candidate to enrich
            
        Returns:
            Enriched candidate
        """
        # Try to find GitHub URL from resume text or existing field
        github_url = candidate.github_url
        
        if not github_url and candidate.raw_text:
            github_url = self.extract_github_url(candidate.raw_text)
            if github_url:
                candidate.github_url = github_url
        
        if not github_url:
            logger.info(f"No GitHub URL found for {candidate.name}")
            return candidate
        
        logger.info(f"Enriching {candidate.name} with GitHub data from {github_url}")
        
        # Analyze GitHub profile
        analysis = self.analyze_github_profile(github_url)
        
        if 'error' in analysis:
            logger.warning(f"GitHub analysis failed: {analysis['error']}")
            return candidate
        
        # Add discovered languages to skills if not present
        github_languages = analysis.get('top_languages', [])
        current_skills_lower = [s.lower() for s in candidate.skills]
        
        new_skills = []
        for lang in github_languages:
            if lang.lower() not in current_skills_lower:
                new_skills.append(lang)
        
        if new_skills:
            candidate.skills.extend(new_skills)
            logger.info(f"Added {len(new_skills)} skills from GitHub: {new_skills}")
        
        # Add GitHub projects to candidate projects
        for repo in analysis.get('top_repos', [])[:3]:
            from app.models.candidate import Project
            project = Project(
                name=repo.get('name'),
                description=repo.get('description', ''),
                technologies=[repo.get('language')] if repo.get('language') else [],
                url=repo.get('url')
            )
            # Check if project already exists
            existing_names = [p.name.lower() for p in candidate.projects if p.name]
            if project.name and project.name.lower() not in existing_names:
                candidate.projects.append(project)
        
        # Generate and append GitHub summary to candidate summary
        github_summary = self.generate_github_summary(analysis)
        if github_summary:
            if candidate.summary:
                candidate.summary = f"{candidate.summary}\n\nGitHub Assessment: {github_summary}"
            else:
                candidate.summary = f"GitHub Assessment: {github_summary}"
        
        logger.info(f"GitHub enrichment complete for {candidate.name}")
        return candidate
    
    def parse_resume_with_github(
        self,
        raw_text: str,
        is_linkedin: bool = False,
        source: str = "upload",
        job_id: Optional[str] = None,
        enrich_github: bool = True
    ) -> Candidate:
        """
        Parse resume and optionally enrich with GitHub analysis.
        
        Args:
            raw_text: Raw text extracted from resume PDF
            is_linkedin: Whether this is a LinkedIn PDF export
            source: How the resume was received (upload, email)
            job_id: Associated job ID (if from email application)
            enrich_github: Whether to fetch and analyze GitHub profile
            
        Returns:
            Structured Candidate model with GitHub enrichment
        """
        # First parse the resume normally
        candidate = self.parse_resume(raw_text, is_linkedin, source, job_id)
        
        # Store raw text for GitHub URL extraction
        candidate.raw_text = raw_text
        
        # Enrich with GitHub if enabled
        if enrich_github:
            candidate = self.enrich_candidate_with_github(candidate)
        
        return candidate
