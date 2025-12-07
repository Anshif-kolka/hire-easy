"""
PDF Parser - Extract text and metadata from PDF files.
"""
import io
from pathlib import Path
from typing import Dict, List, Optional, Union
import PyPDF2

from app.utils.logger import get_logger

logger = get_logger(__name__)


class PDFParser:
    """
    Extract text and metadata from PDF files (resumes, LinkedIn exports).
    """
    
    # Patterns to detect LinkedIn PDF exports
    LINKEDIN_PATTERNS = [
        "linkedin.com",
        "LinkedIn",
        "Profile",
        "Experience",
        "Education", 
        "Skills",
        "Contact",
        "www.linkedin.com"
    ]
    
    def __init__(self):
        """Initialize PDF parser."""
        pass
    
    def extract_text(self, file_path: Union[str, Path]) -> Dict[str, any]:
        """
        Extract text from a PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dict with raw_text, pages, metadata, and source detection
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        
        if not file_path.suffix.lower() == '.pdf':
            raise ValueError(f"Not a PDF file: {file_path}")
        
        try:
            with open(file_path, 'rb') as f:
                return self._extract_from_file_object(f)
        except Exception as e:
            logger.error(f"Error extracting PDF {file_path}: {e}")
            raise
    
    def extract_text_from_bytes(self, pdf_bytes: bytes) -> Dict[str, any]:
        """
        Extract text from PDF bytes (for uploaded files).
        
        Args:
            pdf_bytes: PDF file content as bytes
            
        Returns:
            Dict with raw_text, pages, metadata, and source detection
        """
        try:
            file_obj = io.BytesIO(pdf_bytes)
            return self._extract_from_file_object(file_obj)
        except Exception as e:
            logger.error(f"Error extracting PDF from bytes: {e}")
            raise
    
    def _extract_from_file_object(self, file_obj) -> Dict[str, any]:
        """
        Internal method to extract text from a file object.
        
        Args:
            file_obj: File-like object
            
        Returns:
            Extraction result dict
        """
        reader = PyPDF2.PdfReader(file_obj)
        
        # Extract metadata
        metadata = {}
        if reader.metadata:
            metadata = {
                'title': reader.metadata.get('/Title', ''),
                'author': reader.metadata.get('/Author', ''),
                'creator': reader.metadata.get('/Creator', ''),
                'producer': reader.metadata.get('/Producer', ''),
                'creation_date': str(reader.metadata.get('/CreationDate', '')),
            }
        
        # Extract text page by page
        pages = []
        full_text_parts = []
        
        for page_num, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text() or ""
                pages.append(page_text)
                full_text_parts.append(page_text)
            except Exception as e:
                logger.warning(f"Error extracting page {page_num}: {e}")
                pages.append("")
        
        raw_text = "\n\n".join(full_text_parts)
        
        # Detect if this is a LinkedIn PDF export
        is_linkedin = self._detect_linkedin_pdf(raw_text)
        
        # Detect if document appears to be scanned (very little text)
        is_scanned = len(raw_text.strip()) < 100 and len(reader.pages) > 0
        
        result = {
            "raw_text": raw_text,
            "pages": pages,
            "page_count": len(reader.pages),
            "metadata": metadata,
            "is_linkedin_pdf": is_linkedin,
            "is_scanned": is_scanned,
            "char_count": len(raw_text),
            "word_count": len(raw_text.split())
        }
        
        logger.info(
            f"Extracted PDF: {result['page_count']} pages, "
            f"{result['word_count']} words, "
            f"linkedin={is_linkedin}"
        )
        
        return result
    
    def _detect_linkedin_pdf(self, text: str) -> bool:
        """
        Detect if the PDF is a LinkedIn export.
        
        Args:
            text: Extracted text content
            
        Returns:
            True if likely a LinkedIn PDF
        """
        text_lower = text.lower()
        
        # Count how many LinkedIn patterns are found
        pattern_count = sum(
            1 for pattern in self.LINKEDIN_PATTERNS 
            if pattern.lower() in text_lower
        )
        
        # If multiple patterns found, likely LinkedIn
        return pattern_count >= 3
    
    def validate_pdf(self, file_path: Union[str, Path]) -> Dict[str, any]:
        """
        Validate a PDF file without full extraction.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Validation result with is_valid, page_count, error
        """
        file_path = Path(file_path)
        
        result = {
            "is_valid": False,
            "page_count": 0,
            "file_size_bytes": 0,
            "error": None
        }
        
        if not file_path.exists():
            result["error"] = "File not found"
            return result
        
        if not file_path.suffix.lower() == '.pdf':
            result["error"] = "Not a PDF file"
            return result
        
        result["file_size_bytes"] = file_path.stat().st_size
        
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                result["page_count"] = len(reader.pages)
                result["is_valid"] = True
        except Exception as e:
            result["error"] = str(e)
        
        return result
