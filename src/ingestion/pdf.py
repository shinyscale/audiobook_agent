"""
PDF document ingestion using pdfplumber.
Handles both text-layer PDFs and scanned documents.
"""

from pathlib import Path
from typing import Optional
import re

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

from .base import DocumentIngester, ExtractedDocument


class PDFIngester(DocumentIngester):
    """Ingester for PDF documents."""
    
    SUPPORTED_EXTENSIONS = ['.pdf']
    
    def __init__(
        self,
        normalize_whitespace: bool = True,
        extract_images: bool = False,
        ocr_fallback: bool = False,  # Future: integrate with OCR
    ):
        super().__init__(normalize_whitespace)
        self.extract_images = extract_images
        self.ocr_fallback = ocr_fallback
        
        if pdfplumber is None:
            raise ImportError("pdfplumber is required for PDF ingestion. Install with: pip install pdfplumber")
    
    def extract(self, path: Path) -> ExtractedDocument:
        """Extract text from a PDF document."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {path}")
        
        warnings = []
        all_text = []
        page_count = 0
        has_images = False
        
        # Try to extract title from filename as fallback
        title = self._clean_extracted_title(path.stem)
        author = None
        
        with pdfplumber.open(path) as pdf:
            page_count = len(pdf.pages)
            
            # Try to get metadata
            if pdf.metadata:
                if pdf.metadata.get('Title'):
                    title = pdf.metadata['Title']
                if pdf.metadata.get('Author'):
                    author = pdf.metadata['Author']
            
            for i, page in enumerate(pdf.pages):
                # Extract text
                page_text = page.extract_text()
                
                if page_text:
                    # Clean up common PDF artifacts
                    page_text = self._clean_pdf_text(page_text)
                    all_text.append(page_text)
                else:
                    # Page has no extractable text
                    if page.images:
                        has_images = True
                        warnings.append(f"Page {i+1}: No text extracted (contains images, may need OCR)")
                    else:
                        warnings.append(f"Page {i+1}: No text extracted")
                
                # Check for images
                if page.images:
                    has_images = True
        
        # Join all pages
        full_text = '\n\n'.join(all_text)
        
        # Normalize if requested
        if self.normalize_whitespace:
            full_text = self._normalize_text(full_text)
        
        # Try to detect chapter structure from the text
        chapters = self._detect_chapters(full_text)
        
        return ExtractedDocument(
            text=full_text,
            source_path=path,
            source_format='pdf',
            title=title,
            author=author,
            chapters=chapters,
            page_count=page_count,
            has_images=has_images,
            extraction_warnings=warnings,
        )
    
    def _clean_pdf_text(self, text: str) -> str:
        """Clean common PDF extraction artifacts."""
        # Fix ligatures that may not extract properly
        ligatures = {
            'ﬁ': 'fi',
            'ﬂ': 'fl',
            'ﬀ': 'ff',
            'ﬃ': 'ffi',
            'ﬄ': 'ffl',
        }
        for lig, replacement in ligatures.items():
            text = text.replace(lig, replacement)
        
        # Remove page numbers that appear alone on lines
        # (This is a heuristic - might need tuning)
        text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
        
        # Remove headers/footers that repeat (basic heuristic)
        # More sophisticated detection would track repeated patterns across pages
        
        return text
    
    def _detect_chapters(self, text: str) -> Optional[list[dict]]:
        """
        Attempt to detect chapter boundaries in extracted text.
        Returns list of {title, start_pos, end_pos} dicts.
        """
        chapters = []
        
        # Common chapter patterns
        patterns = [
            # "Chapter 1", "Chapter One", "Chapter I"
            r'^(?P<title>Chapter\s+(?:\d+|[IVXLC]+|One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten|Eleven|Twelve|Thirteen|Fourteen|Fifteen|Sixteen|Seventeen|Eighteen|Nineteen|Twenty)[^\n]*)',
            # "CHAPTER 1" (all caps)
            r'^(?P<title>CHAPTER\s+(?:\d+|[IVXLC]+)[^\n]*)',
            # "1." or "I." at start of line (numbered chapters)
            r'^(?P<title>(?:\d+|[IVXLC]+)\.\s*[^\n]*)',
            # Part headers
            r'^(?P<title>(?:PART|Part)\s+(?:\d+|[IVXLC]+|One|Two|Three|Four|Five)[^\n]*)',
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE):
                chapters.append({
                    'title': match.group('title').strip(),
                    'start_pos': match.start(),
                    'end_pos': None,  # Will be filled in below
                })
        
        if not chapters:
            return None
        
        # Sort by position and fill in end positions
        chapters.sort(key=lambda c: c['start_pos'])
        for i in range(len(chapters) - 1):
            chapters[i]['end_pos'] = chapters[i + 1]['start_pos']
        chapters[-1]['end_pos'] = len(text)
        
        return chapters
