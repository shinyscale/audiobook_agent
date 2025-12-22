"""
Document ingestion module.
Supports PDF, DOCX, EPUB, and TXT formats.
"""

from .base import DocumentIngester, ExtractedDocument, get_ingester
from .pdf import PDFIngester
from .docx import DOCXIngester
from .epub import EPUBIngester
from .txt import TXTIngester
from .refine import refine_extracted_document, to_canonical_markdown

__all__ = [
    'DocumentIngester',
    'ExtractedDocument',
    'get_ingester',
    'PDFIngester',
    'DOCXIngester',
    'EPUBIngester',
    'TXTIngester',
    'refine_extracted_document',
    'to_canonical_markdown',
]
