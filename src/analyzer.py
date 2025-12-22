"""
Main analyzer orchestrator.
Coordinates ingestion and analysis steps.
"""

from pathlib import Path
from typing import Optional
import json
from datetime import datetime

from .models import (
    AnalysisResult,
    BookMetadata,
)
from .ingestion import get_ingester, ExtractedDocument
from .ingestion.refine import refine_extracted_document, to_canonical_markdown
from .analysis import (
    analyze_structure,
    extract_characters,
    flag_pronunciations,
)

# LLM refinement is optional - gracefully handle if not available
try:
    from .llm import LLMRefiner, refine_analysis
    from .llm.prompts import PromptConfig
    HAS_LLM = True
except ImportError:
    HAS_LLM = False
    PromptConfig = None  # type: ignore


class AudiobookAnalyzer:
    """
    Main analyzer class that orchestrates the full analysis pipeline.
    """

    def __init__(
        self,
        words_per_minute: int = 150,
        min_character_mentions: int = 2,
        llm_refine: bool = True,
        llm_model: Optional[str] = None,
        llm_base_url: Optional[str] = None,
        llm_provider: str = "lm_studio",
        llm_api_key: Optional[str] = None,
        llm_context_length: int = 32768,
        llm_prompts: Optional["PromptConfig"] = None,
        ocr_fallback: bool = False,
        write_canonical_md: bool = False,
        output_dir: Optional[Path] = None,
    ):
        self.words_per_minute = words_per_minute
        self.min_character_mentions = min_character_mentions
        self.llm_refine = llm_refine and HAS_LLM
        self.llm_model = llm_model
        self.llm_base_url = llm_base_url or "http://localhost:1234/v1"
        self.llm_provider = llm_provider
        self.llm_api_key = llm_api_key
        self.llm_context_length = llm_context_length
        self.llm_prompts = llm_prompts
        self.ocr_fallback = ocr_fallback
        self.write_canonical_md = write_canonical_md
        self.output_dir = Path(output_dir) if output_dir else None
    
    def analyze(self, file_path: str | Path) -> AnalysisResult:
        """
        Analyze a book file and return structured results.
        
        Args:
            file_path: Path to PDF, DOCX, EPUB, or TXT file
            
        Returns:
            AnalysisResult with all extracted information
        """
        file_path = Path(file_path)

        # Step 1: Ingest document
        print(f"📖 Ingesting: {file_path.name}")
        ingester = get_ingester(file_path, ocr_fallback=self.ocr_fallback)
        doc = ingester.extract(file_path)

        print(f"   Extracted {doc.word_count:,} words")

        # Step 1.5: Refine extracted text (deterministic)
        print("🔧 Refining text...")
        doc = refine_extracted_document(doc)

        if doc.extraction_warnings:
            for warning in doc.extraction_warnings:
                print(f"   ⚠️  {warning}")

        # Optionally write canonical markdown artifact
        if self.write_canonical_md:
            output_dir = self.output_dir or Path('output')
            output_dir.mkdir(exist_ok=True)
            md_path = output_dir / f"{file_path.stem}.canonical.md"
            canonical_md = to_canonical_markdown(doc)
            md_path.write_text(canonical_md, encoding='utf-8')
            print(f"   📝 Wrote canonical markdown: {md_path}")

        # Step 2: Analyze structure
        print("📑 Analyzing structure...")
        structure = analyze_structure(doc, words_per_minute=self.words_per_minute)
        
        chapter_count = sum(1 for s in structure if s.type.value == 'chapter')
        print(f"   Found {chapter_count} chapters, {len(structure)} total structural elements")
        
        # Step 3: Extract characters
        print("👥 Extracting characters...")
        characters = extract_characters(
            doc.text,
            structure=structure,
            min_mentions=self.min_character_mentions,
        )
        print(f"   Found {len(characters)} characters")
        
        # Step 4: Flag pronunciations
        print("🗣️  Flagging pronunciations...")
        pronunciations = flag_pronunciations(doc.text, characters=characters)
        print(f"   Flagged {len(pronunciations)} words for pronunciation review")
        
        # Step 5: Build result
        total_duration = sum(s.estimated_duration_minutes for s in structure if s.type.value == 'chapter')
        
        metadata = BookMetadata(
            title=doc.title,
            author=doc.author,
            source_file=str(file_path),
            source_format=doc.source_format,
            total_word_count=doc.word_count,
            total_character_count=doc.character_count,
            estimated_total_duration_minutes=total_duration,
            words_per_minute=self.words_per_minute,
        )
        
        # Collect warnings
        warnings = list(doc.extraction_warnings) if doc.extraction_warnings else []
        
        # Identify low-confidence items
        low_confidence = []
        for elem in structure:
            if elem.confidence.value == 'low':
                low_confidence.append(f"Structure: {elem.type.value} at position {elem.start_position}")
        for char in characters:
            if char.confidence.value == 'low':
                low_confidence.append(f"Character: {char.canonical_name}")
        
        result = AnalysisResult(
            metadata=metadata,
            structure=structure,
            characters=characters,
            pronunciations=pronunciations,
            raw_text=doc.text,
            warnings=warnings,
            low_confidence_items=low_confidence,
        )

        # Step 6: LLM refinement (optional)
        if self.llm_refine:
            print("🤖 Running LLM refinement...")
            try:
                refiner = LLMRefiner(
                    model=self.llm_model,
                    base_url=self.llm_base_url,
                    provider=self.llm_provider,
                    api_key=self.llm_api_key,
                    context_length=self.llm_context_length,
                    custom_prompts=self.llm_prompts,
                )
                stats = refine_analysis(
                    result, doc.text,
                    refiner=refiner,
                    words_per_minute=self.words_per_minute,
                    verbose=True
                )
            except Exception as e:
                print(f"   ⚠️  LLM refinement failed: {e}")
                warnings.append(f"LLM refinement failed: {e}")

        return result
    
    def analyze_to_json(
        self,
        file_path: str | Path,
        output_path: Optional[str | Path] = None,
    ) -> str:
        """
        Analyze a book and save results as JSON.
        
        Args:
            file_path: Path to book file
            output_path: Optional output path (defaults to same name with .json)
            
        Returns:
            Path to output JSON file
        """
        result = self.analyze(file_path)
        
        if output_path is None:
            file_path = Path(file_path)
            output_path = file_path.with_suffix('.analysis.json')
        
        output_path = Path(output_path)
        
        # Convert to dict, excluding raw_text to save space
        result_dict = result.model_dump(exclude={'raw_text'})
        
        # Add analysis metadata
        result_dict['_analysis_metadata'] = {
            'analyzed_at': datetime.now().isoformat(),
            'analyzer_version': '0.1.0',
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result_dict, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Analysis saved to: {output_path}")
        return str(output_path)


def analyze_book(file_path: str | Path) -> AnalysisResult:
    """
    Convenience function to analyze a book.
    
    Args:
        file_path: Path to PDF, DOCX, EPUB, or TXT file
        
    Returns:
        AnalysisResult with all extracted information
    """
    analyzer = AudiobookAnalyzer()
    return analyzer.analyze(file_path)
