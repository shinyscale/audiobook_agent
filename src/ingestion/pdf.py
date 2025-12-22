"""
PDF document ingestion using pdfplumber.
Handles both text-layer PDFs and scanned documents.
"""

from pathlib import Path
from typing import Optional
from collections import Counter
import re
import subprocess
import tempfile
import shutil

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

from .base import DocumentIngester, ExtractedDocument


# Minimum threshold for considering a page as having text
MIN_CHARS_FOR_TEXT_PAGE = 50

# Threshold for identifying repeating headers/footers (60% of pages)
HEADER_FOOTER_REPEAT_THRESHOLD = 0.6


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
        page_texts = []  # Raw text per page
        header_candidates = []  # First 2-3 lines of each page
        footer_candidates = []  # Last 2-3 lines of each page
        page_count = 0
        pages_with_text = 0
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
                    page_texts.append(page_text)

                    # Track pages with substantial text
                    if len(page_text.strip()) >= MIN_CHARS_FOR_TEXT_PAGE:
                        pages_with_text += 1

                    # Collect header/footer candidates
                    lines = [l.strip() for l in page_text.split('\n') if l.strip()]
                    if len(lines) >= 2:
                        # First 2 lines as header candidates
                        header_candidates.extend(lines[:2])
                        # Last 2 lines as footer candidates
                        footer_candidates.extend(lines[-2:])
                else:
                    # Page has no extractable text
                    page_texts.append('')
                    if page.images:
                        has_images = True
                        warnings.append(f"Page {i+1}: No text extracted (contains images, may need OCR)")
                    else:
                        warnings.append(f"Page {i+1}: No text extracted")

                # Check for images
                if page.images:
                    has_images = True

        # Check extraction quality and potentially trigger OCR
        extraction_ratio = pages_with_text / max(page_count, 1)
        if extraction_ratio < 0.3 and self.ocr_fallback:
            # Try OCR fallback
            ocr_result = self._try_ocr_extraction(path, warnings)
            if ocr_result:
                page_texts = [ocr_result]
                warnings.append(f"Used OCR fallback (only {extraction_ratio:.0%} of pages had extractable text)")
        elif extraction_ratio < 0.3:
            warnings.append(f"Low text extraction rate ({extraction_ratio:.0%}). Consider using --pdf-ocr for OCR fallback.")

        # Identify and remove repeating headers/footers
        removed_headers, removed_footers = self._identify_repeating_lines(
            header_candidates, footer_candidates, page_count
        )

        if removed_headers or removed_footers:
            page_texts = self._remove_header_footer_lines(
                page_texts, removed_headers, removed_footers
            )
            if removed_headers:
                for h in removed_headers:
                    warnings.append(f"Removed repeating header: {h[:50]}...")
            if removed_footers:
                for f in removed_footers:
                    warnings.append(f"Removed repeating footer: {f[:50]}...")

        # Join all pages
        full_text = '\n\n'.join(t for t in page_texts if t.strip())

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

    def _identify_repeating_lines(
        self,
        header_candidates: list[str],
        footer_candidates: list[str],
        page_count: int
    ) -> tuple[list[str], list[str]]:
        """
        Identify lines that repeat across many pages (likely headers/footers).

        Args:
            header_candidates: First 2-3 lines from each page
            footer_candidates: Last 2-3 lines from each page
            page_count: Total number of pages

        Returns:
            Tuple of (repeating headers, repeating footers) to remove
        """
        threshold = int(page_count * HEADER_FOOTER_REPEAT_THRESHOLD)

        # Count occurrences
        header_counts = Counter(header_candidates)
        footer_counts = Counter(footer_candidates)

        # Find lines that appear on most pages
        repeating_headers = [
            line for line, count in header_counts.items()
            if count >= threshold and len(line) > 3  # Skip very short lines
        ]
        repeating_footers = [
            line for line, count in footer_counts.items()
            if count >= threshold and len(line) > 3
        ]

        return repeating_headers, repeating_footers

    def _remove_header_footer_lines(
        self,
        page_texts: list[str],
        headers_to_remove: list[str],
        footers_to_remove: list[str]
    ) -> list[str]:
        """
        Remove identified header/footer lines from page texts.

        Args:
            page_texts: Text content of each page
            headers_to_remove: Lines to remove from beginning of pages
            footers_to_remove: Lines to remove from end of pages

        Returns:
            Cleaned page texts
        """
        cleaned = []
        for page_text in page_texts:
            if not page_text.strip():
                cleaned.append(page_text)
                continue

            lines = page_text.split('\n')

            # Remove header lines from the beginning
            while lines and lines[0].strip() in headers_to_remove:
                lines.pop(0)

            # Remove footer lines from the end
            while lines and lines[-1].strip() in footers_to_remove:
                lines.pop()

            cleaned.append('\n'.join(lines))

        return cleaned

    def _try_ocr_extraction(self, path: Path, warnings: list[str]) -> Optional[str]:
        """
        Attempt OCR extraction using available tools.

        Priority:
        1. ocrmypdf (best quality for PDFs)
        2. pytesseract + pdf2image

        Args:
            path: Path to the PDF file
            warnings: List to append warnings to

        Returns:
            Extracted text if successful, None otherwise
        """
        # Try ocrmypdf first (best quality)
        if shutil.which('ocrmypdf'):
            try:
                return self._ocr_with_ocrmypdf(path)
            except Exception as e:
                warnings.append(f"ocrmypdf failed: {e}")

        # Try pytesseract + pdf2image
        try:
            from pdf2image import convert_from_path
            import pytesseract
            return self._ocr_with_pytesseract(path, convert_from_path, pytesseract)
        except ImportError:
            pass
        except Exception as e:
            warnings.append(f"pytesseract OCR failed: {e}")

        warnings.append(
            "OCR fallback requested but no OCR tools available. "
            "Install ocrmypdf (recommended) or pytesseract + pdf2image."
        )
        return None

    def _ocr_with_ocrmypdf(self, path: Path) -> str:
        """
        Use ocrmypdf to add text layer, then extract.

        Args:
            path: Path to the PDF file

        Returns:
            Extracted text from OCR'd PDF
        """
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            # Run ocrmypdf to create searchable PDF
            subprocess.run(
                ['ocrmypdf', '--force-ocr', '--skip-text', str(path), str(tmp_path)],
                check=True,
                capture_output=True,
                timeout=600  # 10 minute timeout
            )

            # Extract text from the OCR'd PDF
            with pdfplumber.open(tmp_path) as pdf:
                texts = []
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        texts.append(self._clean_pdf_text(page_text))
                return '\n\n'.join(texts)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def _ocr_with_pytesseract(self, path: Path, convert_from_path, pytesseract) -> str:
        """
        Use pytesseract + pdf2image for OCR.

        Args:
            path: Path to the PDF file
            convert_from_path: pdf2image function
            pytesseract: pytesseract module

        Returns:
            Extracted text from OCR
        """
        # Convert PDF pages to images
        images = convert_from_path(str(path), dpi=300)

        texts = []
        for i, image in enumerate(images):
            text = pytesseract.image_to_string(image)
            if text.strip():
                texts.append(self._clean_pdf_text(text))

        return '\n\n'.join(texts)
