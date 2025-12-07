"""
Text Cleaner - Utilities for cleaning and normalizing text.
"""
import re
from typing import List


class TextCleaner:
    """
    Clean and normalize text from resumes and job descriptions.
    """
    
    def __init__(self):
        pass
    
    def clean_resume_text(self, text: str) -> str:
        """
        Clean resume text for better LLM processing.
        
        Args:
            text: Raw resume text
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = self._normalize_whitespace(text)
        
        # Remove common PDF artifacts
        text = self._remove_pdf_artifacts(text)
        
        # Fix common encoding issues
        text = self._fix_encoding_issues(text)
        
        # Remove page numbers and headers/footers patterns
        text = self._remove_page_markers(text)
        
        return text.strip()
    
    def clean_jd_text(self, text: str) -> str:
        """
        Clean job description text.
        
        Args:
            text: Raw JD text
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Similar cleaning to resume
        text = self._normalize_whitespace(text)
        text = self._fix_encoding_issues(text)
        
        # Remove common JD boilerplate patterns
        text = self._remove_jd_boilerplate(text)
        
        return text.strip()
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace and line breaks."""
        # Replace multiple spaces with single space
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Replace 3+ newlines with 2 newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove trailing whitespace from lines
        text = re.sub(r' +\n', '\n', text)
        
        return text
    
    def _remove_pdf_artifacts(self, text: str) -> str:
        """Remove common PDF extraction artifacts."""
        # Remove bullet point artifacts
        text = re.sub(r'[•●○◦■□▪▫►▻]', '- ', text)
        
        # Remove form feed characters
        text = text.replace('\f', '\n')
        
        # Remove non-printable characters (except newlines and tabs)
        text = re.sub(r'[^\x20-\x7E\n\t\r]', '', text)
        
        return text
    
    def _fix_encoding_issues(self, text: str) -> str:
        """Fix common encoding issues."""
        # Fix common mojibake patterns
        replacements = {
            'â€™': "'",
            'â€"': "-",
            'â€"': "—",
            'â€œ': '"',
            'â€': '"',
            'Ã©': 'é',
            'Ã¨': 'è',
            'Ã ': 'à',
            '\u200b': '',  # Zero-width space
            '\u00a0': ' ',  # Non-breaking space
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        return text
    
    def _remove_page_markers(self, text: str) -> str:
        """Remove page numbers and common headers/footers."""
        # Remove standalone page numbers
        text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
        
        # Remove "Page X of Y" patterns
        text = re.sub(r'[Pp]age\s+\d+\s+of\s+\d+', '', text)
        
        return text
    
    def _remove_jd_boilerplate(self, text: str) -> str:
        """Remove common JD boilerplate text."""
        # Patterns to remove (case insensitive)
        boilerplate_patterns = [
            r'equal opportunity employer.*?(?=\n\n|\Z)',
            r'we are an equal.*?(?=\n\n|\Z)',
            r'this position is.*?visa sponsorship',
            r'salary:?\s*\$?[\d,]+\s*-?\s*\$?[\d,]*\s*(?:per|\/)\s*(?:year|annum|month)',
        ]
        
        for pattern in boilerplate_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
        
        return text
    
    def extract_sections(self, text: str) -> dict:
        """
        Try to identify common resume sections.
        
        Args:
            text: Resume text
            
        Returns:
            Dict of section_name -> text
        """
        sections = {}
        
        # Common section headers
        section_patterns = [
            (r'(?:professional\s+)?summary|profile|objective', 'summary'),
            (r'(?:work\s+)?experience|employment(?:\s+history)?', 'experience'),
            (r'education|academic|qualifications', 'education'),
            (r'skills|technical\s+skills|competencies', 'skills'),
            (r'projects|portfolio', 'projects'),
            (r'certifications?|licenses?', 'certifications'),
            (r'awards?|achievements?|honors?', 'awards'),
        ]
        
        lines = text.split('\n')
        current_section = 'header'
        current_content = []
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Check if this line is a section header
            found_section = None
            for pattern, section_name in section_patterns:
                if re.match(f'^{pattern}$', line_lower) or re.match(f'^{pattern}:?$', line_lower):
                    found_section = section_name
                    break
            
            if found_section:
                # Save previous section
                if current_content:
                    sections[current_section] = '\n'.join(current_content).strip()
                current_section = found_section
                current_content = []
            else:
                current_content.append(line)
        
        # Save last section
        if current_content:
            sections[current_section] = '\n'.join(current_content).strip()
        
        return sections
    
    def normalize_skill(self, skill: str) -> str:
        """
        Normalize a single skill name.
        
        Args:
            skill: Skill string
            
        Returns:
            Normalized skill name
        """
        skill = skill.strip()
        
        # Common normalizations
        normalizations = {
            'js': 'JavaScript',
            'ts': 'TypeScript',
            'py': 'Python',
            'c++': 'C++',
            'c#': 'C#',
            'node': 'Node.js',
            'react': 'React',
            'vue': 'Vue.js',
            'angular': 'Angular',
            'aws': 'AWS',
            'gcp': 'Google Cloud',
            'azure': 'Azure',
            'k8s': 'Kubernetes',
            'docker': 'Docker',
            'sql': 'SQL',
            'nosql': 'NoSQL',
            'ml': 'Machine Learning',
            'dl': 'Deep Learning',
            'ai': 'Artificial Intelligence',
            'nlp': 'NLP',
            'cv': 'Computer Vision',
        }
        
        skill_lower = skill.lower()
        if skill_lower in normalizations:
            return normalizations[skill_lower]
        
        return skill
