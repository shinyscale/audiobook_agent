"""
EPUB document ingestion using ebooklib.
EPUBs are essentially structured XHTML, so we get good chapter info.
"""

from pathlib import Path
from typing import Optional
import re

try:
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup
except ImportError:
    ebooklib = None
    BeautifulSoup = None

from .base import DocumentIngester, ExtractedDocument


class EPUBIngester(DocumentIngester):
    """Ingester for EPUB documents."""
    
    SUPPORTED_EXTENSIONS = ['.epub']
    
    def __init__(self, normalize_whitespace: bool = True):
        super().__init__(normalize_whitespace)
        
        if ebooklib is None:
            raise ImportError("ebooklib is required for EPUB ingestion. Install with: pip install ebooklib beautifulsoup4")
    
    def extract(self, path: Path) -> ExtractedDocument:
        """Extract text and structure from an EPUB document."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"EPUB file not found: {path}")
        
        warnings = []
        book = epub.read_epub(str(path), options={'ignore_ncx': False})
        
        # Extract metadata
        title = None
        author = None
        
        title_meta = book.get_metadata('DC', 'title')
        if title_meta:
            title = title_meta[0][0]
        if not title:
            title = self._clean_extracted_title(path.stem)
        
        author_meta = book.get_metadata('DC', 'creator')
        if author_meta:
            author = author_meta[0][0]
        
        # Extract content from spine items
        all_text = []
        chapters = []
        has_images = False
        
        # Get items in reading order
        spine_items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
        
        # Try to get TOC for chapter info
        toc = book.toc
        toc_map = self._build_toc_map(toc)
        
        current_position = 0
        
        for item in spine_items:
            content = item.get_content()
            soup = BeautifulSoup(content, 'lxml')
            
            # Check for images
            if soup.find_all('img'):
                has_images = True
            
            # Extract text
            # Remove script and style elements
            for element in soup(['script', 'style', 'nav']):
                element.decompose()
            
            # Get text with some structure preservation
            item_text = self._extract_text_from_soup(soup)
            
            if item_text.strip():
                # Check if this item corresponds to a TOC entry
                item_href = item.get_name()
                if item_href in toc_map:
                    chapters.append({
                        'title': toc_map[item_href],
                        'start_pos': current_position,
                        'end_pos': None,
                    })
                
                all_text.append(item_text)
                current_position += len(item_text) + 2  # +2 for \n\n separator
        
        # Fill in chapter end positions
        for i in range(len(chapters) - 1):
            chapters[i]['end_pos'] = chapters[i + 1]['start_pos']
        if chapters:
            chapters[-1]['end_pos'] = current_position
        
        # Join all content
        full_text = '\n\n'.join(all_text)
        
        # Normalize if requested
        if self.normalize_whitespace:
            full_text = self._normalize_text(full_text)
        
        if has_images:
            warnings.append("EPUB contains images that won't be included in text extraction")
        
        return ExtractedDocument(
            text=full_text,
            source_path=path,
            source_format='epub',
            title=title,
            author=author,
            chapters=chapters if chapters else None,
            page_count=None,
            has_images=has_images,
            extraction_warnings=warnings,
        )
    
    def _build_toc_map(self, toc, result: dict = None) -> dict:
        """Build a map of href -> title from TOC."""
        if result is None:
            result = {}
        
        for item in toc:
            if isinstance(item, tuple):
                # It's a section with nested items
                section, children = item
                if hasattr(section, 'href') and hasattr(section, 'title'):
                    # Remove fragment identifier from href
                    href = section.href.split('#')[0]
                    result[href] = section.title
                self._build_toc_map(children, result)
            elif hasattr(item, 'href') and hasattr(item, 'title'):
                href = item.href.split('#')[0]
                result[href] = item.title
        
        return result
    
    def _extract_text_from_soup(self, soup: BeautifulSoup) -> str:
        """Extract text from BeautifulSoup, preserving some structure."""
        lines = []
        
        # Find the body
        body = soup.find('body')
        if not body:
            body = soup
        
        for element in body.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div', 'blockquote']):
            text = element.get_text(separator=' ', strip=True)
            if text:
                # Add extra spacing for headers
                if element.name in ('h1', 'h2', 'h3'):
                    lines.append('')
                lines.append(text)
                if element.name in ('h1', 'h2', 'h3'):
                    lines.append('')
        
        return '\n'.join(lines)
