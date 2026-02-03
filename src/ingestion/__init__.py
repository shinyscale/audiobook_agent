"""
Document ingestion module.
Supports PDF, DOCX, EPUB, and TXT formats.
"""

from .base import DocumentIngester, ExtractedDocument, get_ingester
from .docx import DOCXIngester
from .epub import EPUBIngester
from .glossary import GlossaryEntry, GlossaryExtractionResult, extract_glossary
from .ocr_repair import repair_ocr_errors
from .pdf import PDFIngester
from .refine import refine_extracted_document, to_canonical_markdown
from .txt import TXTIngester

__all__ = [
    "DocumentIngester",
    "ExtractedDocument",
    "get_ingester",
    "PDFIngester",
    "DOCXIngester",
    "EPUBIngester",
    "TXTIngester",
    "refine_extracted_document",
    "to_canonical_markdown",
    "extract_glossary",
    "GlossaryExtractionResult",
    "GlossaryEntry",
    "repair_ocr_errors",
]
