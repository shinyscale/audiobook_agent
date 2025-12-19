"""
Plain text document ingestion.
Simple but needs heuristic chapter detection.
"""

from pathlib import Path
from typing import Optional
import re

from .base import DocumentIngester, ExtractedDocument


class TXTIngester(DocumentIngester):
    """Ingester for plain text documents."""
    
    SUPPORTED_EXTENSIONS = ['.txt', '.text', '.md', '.markdown']
    
    def __init__(
        self,
        normalize_whitespace: bool = True,
        encoding: str = 'utf-8',
        fallback_encodings: list[str] = None,
    ):
        super().__init__(normalize_whitespace)
        self.encoding = encoding
        self.fallback_encodings = fallback_encodings or ['latin-1', 'cp1252', 'utf-16']
    
    def extract(self, path: Path) -> ExtractedDocument:
        """Extract text from a plain text document."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Text file not found: {path}")
        
        warnings = []
        
        # Try to read with specified encoding, fall back to others
        text = None
        used_encoding = self.encoding
        
        encodings_to_try = [self.encoding] + self.fallback_encodings
        
        for enc in encodings_to_try:
            try:
                text = path.read_text(encoding=enc)
                used_encoding = enc
                break
            except UnicodeDecodeError:
                continue
        
        if text is None:
            raise ValueError(f"Could not decode file with any of: {encodings_to_try}")
        
        if used_encoding != self.encoding:
            warnings.append(f"File decoded using {used_encoding} (not {self.encoding})")
        
        # Try to extract title from filename
        title = self._clean_extracted_title(path.stem)
        
        # Try to detect title from first lines
        detected_title = self._detect_title(text)
        if detected_title:
            title = detected_title
        
        # Normalize if requested
        if self.normalize_whitespace:
            text = self._normalize_text(text)
        
        # Detect chapters
        chapters = self._detect_chapters(text)
        
        # Try to detect author (common in Project Gutenberg texts)
        author = self._detect_author(text)
        
        return ExtractedDocument(
            text=text,
            source_path=path,
            source_format='txt',
            title=title,
            author=author,
            chapters=chapters,
            page_count=None,
            has_images=False,
            extraction_warnings=warnings,
        )
    
    def _detect_title(self, text: str) -> Optional[str]:
        """Try to detect book title from text content."""
        lines = text.split('\n')[:20]  # Check first 20 lines
        
        for line in lines:
            line = line.strip()
            # Skip empty lines
            if not line:
                continue
            # Skip Project Gutenberg headers
            if 'project gutenberg' in line.lower():
                continue
            if line.startswith('***'):
                continue
            
            # Title is often all caps or the first substantial line
            if line.isupper() and len(line) > 3 and len(line) < 100:
                return line.title()  # Convert to title case
            
            # Or it might be prefixed with "Title:"
            if line.lower().startswith('title:'):
                return line[6:].strip()
        
        return None
    
    def _detect_author(self, text: str) -> Optional[str]:
        """Try to detect author from text content."""
        lines = text.split('\n')[:30]  # Check first 30 lines
        
        for line in lines:
            line = line.strip()
            
            # Common patterns
            patterns = [
                r'^(?:by|author:?)\s+(.+)$',
                r'^written by\s+(.+)$',
            ]
            
            for pattern in patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    author = match.group(1).strip()
                    # Clean up
                    author = re.sub(r'\s+', ' ', author)
                    return author
        
        return None
    
    def _detect_chapters(self, text: str) -> Optional[list[dict]]:
        """Detect chapter boundaries using various patterns."""
        chapters = []
        
        # Common chapter patterns (ordered by specificity)
        patterns = [
            # "Chapter 1: Title" or "Chapter One - The Beginning"
            r'^(?P<title>Chapter\s+(?:\d+|[IVXLC]+|One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten|Eleven|Twelve|Thirteen|Fourteen|Fifteen|Sixteen|Seventeen|Eighteen|Nineteen|Twenty)(?:\s*[:\-–—]\s*[^\n]+)?)',
            # "CHAPTER 1" (all caps)
            r'^(?P<title>CHAPTER\s+(?:\d+|[IVXLC]+)(?:\s*[:\-–—]\s*[^\n]+)?)',
            # Numbered sections: "1." at start of line
            r'^(?P<title>\d+\.\s+[A-Z][^\n]*)',
            # Roman numerals with significant leading whitespace (centered chapter headers)
            # Requires 10+ spaces before the numeral to avoid matching TOC entries
            r'^(?P<title>\s{10,}[IVXLC]+)\s*$',
            # Part headers
            r'^(?P<title>(?:PART|Part)\s+(?:\d+|[IVXLC]+|One|Two|Three|Four|Five)(?:\s*[:\-–—]\s*[^\n]+)?)',
            # Scene breaks that might indicate structure
            r'^(?P<title>\*\s*\*\s*\*)',
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.MULTILINE):
                title = match.group('title').strip()
                # Skip scene breaks as chapters unless that's all we have
                if title == '* * *' and chapters:
                    continue
                    
                chapters.append({
                    'title': title,
                    'start_pos': match.start(),
                    'end_pos': None,
                })
        
        if not chapters:
            return None
        
        # Remove duplicates (same position)
        seen_positions = set()
        unique_chapters = []
        for ch in chapters:
            if ch['start_pos'] not in seen_positions:
                seen_positions.add(ch['start_pos'])
                unique_chapters.append(ch)
        chapters = unique_chapters
        
        # Sort by position and fill in end positions
        chapters.sort(key=lambda c: c['start_pos'])
        for i in range(len(chapters) - 1):
            chapters[i]['end_pos'] = chapters[i + 1]['start_pos']
        chapters[-1]['end_pos'] = len(text)
        
        return chapters
