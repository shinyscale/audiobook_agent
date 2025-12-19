"""
Base class for document ingestion.
All format-specific parsers inherit from this.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import re


@dataclass
class ExtractedDocument:
    """Raw extracted content from a document."""
    text: str
    source_path: Path
    source_format: str
    
    # Optional structured info if the format provides it
    title: Optional[str] = None
    author: Optional[str] = None
    chapters: Optional[list[dict]] = None  # [{title, start_pos, end_pos}, ...]
    
    # Metadata
    page_count: Optional[int] = None
    has_images: bool = False
    extraction_warnings: list[str] = None
    
    def __post_init__(self):
        if self.extraction_warnings is None:
            self.extraction_warnings = []
    
    @property
    def word_count(self) -> int:
        """Approximate word count."""
        return len(self.text.split())
    
    @property
    def character_count(self) -> int:
        """Character count."""
        return len(self.text)


class DocumentIngester(ABC):
    """Abstract base class for document ingesters."""
    
    SUPPORTED_EXTENSIONS: list[str] = []
    
    def __init__(self, normalize_whitespace: bool = True):
        self.normalize_whitespace = normalize_whitespace
    
    @abstractmethod
    def extract(self, path: Path) -> ExtractedDocument:
        """Extract text and metadata from the document."""
        pass
    
    @classmethod
    def can_handle(cls, path: Path) -> bool:
        """Check if this ingester can handle the given file."""
        return path.suffix.lower() in cls.SUPPORTED_EXTENSIONS
    
    def _normalize_text(self, text: str) -> str:
        """Clean up extracted text."""
        if not self.normalize_whitespace:
            return text
        
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Collapse multiple blank lines into two (preserving paragraph breaks)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Normalize spaces (but preserve newlines)
        lines = text.split('\n')
        lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in lines]
        text = '\n'.join(lines)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def _clean_extracted_title(self, title: Optional[str]) -> Optional[str]:
        """Clean up an extracted title."""
        if not title:
            return None
        
        # Remove common suffixes
        title = re.sub(r'\.(pdf|docx|epub|txt)$', '', title, flags=re.IGNORECASE)
        
        # Clean whitespace
        title = ' '.join(title.split())
        
        return title if title else None


def get_ingester(path: Path) -> DocumentIngester:
    """Factory function to get the appropriate ingester for a file."""
    from .pdf import PDFIngester
    from .docx import DOCXIngester
    from .epub import EPUBIngester
    from .txt import TXTIngester
    
    ingesters = [PDFIngester, DOCXIngester, EPUBIngester, TXTIngester]
    
    for ingester_class in ingesters:
        if ingester_class.can_handle(path):
            return ingester_class()
    
    raise ValueError(f"No ingester available for file type: {path.suffix}")
