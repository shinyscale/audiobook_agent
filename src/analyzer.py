"""
Main analyzer orchestrator.
Coordinates ingestion and analysis pipeline.
"""

from pathlib import Path
from typing import Optional, Callable
import json
import time
from datetime import datetime
import logging

from .models import (
    AnalysisResult,
    BookMetadata,
    StructuralElement,
    StructureType,
    Character,
    CharacterDescription,
    PronunciationEntry,
    PronunciationFlag as ModelPronunciationFlag,
    ConfidenceLevel,
)
from .ingestion import get_ingester, ExtractedDocument
from .ingestion.refine import refine_extracted_document, to_canonical_markdown

# Import new pipeline
from .pipeline import (
    ChapterDetectionPipeline,
    ChapterMap,
)
from .pipeline.character_extraction import (
    CharacterExtractionPipeline,
    CharacterMap as PipelineCharacterMap,
)
from .pipeline.chapter_summary import (
    ChapterSummaryPipeline,
    ChapterSummaryMap,
)
from .pipeline.pronunciation_guide import (
    PronunciationGuidePipeline,
    PronunciationMap,
    PronunciationFlag as PipelinePronunciationFlag,
)
from .pipeline.llm import LLMClient, LLMConfig
from .pipeline.metrics import MetricsCollector, ProfilingReport

# Agent imports
from .agents import StructureAgent, AgentContext, AgentConfig

# LLM prompts config (keep for compatibility)
try:
    from .llm.prompts import PromptConfig
    HAS_PROMPTS = True
except ImportError:
    HAS_PROMPTS = False
    PromptConfig = None  # type: ignore

logger = logging.getLogger(__name__)


class AudiobookAnalyzer:
    """
    Main analyzer class that orchestrates the full analysis pipeline.

    Uses the new multi-agent pipeline for:
    - Chapter detection
    - Character extraction
    - Chapter summaries
    - Pronunciation guide
    """

    def __init__(
        self,
        words_per_minute: int = 150,
        min_character_mentions: int = 2,
        llm_refine: bool = True,
        llm_model: Optional[str] = None,
        llm_base_url: Optional[str] = None,
        llm_provider: str = "ollama",
        llm_api_key: Optional[str] = None,
        llm_context_length: int = 32768,
        llm_prompts: Optional["PromptConfig"] = None,
        ocr_fallback: bool = False,
        write_canonical_md: bool = False,
        output_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ):
        self.words_per_minute = words_per_minute
        self.min_character_mentions = min_character_mentions
        self.llm_refine = llm_refine
        self.llm_model = llm_model
        self.llm_base_url = llm_base_url or "http://localhost:11434"
        self.llm_provider = llm_provider
        self.llm_api_key = llm_api_key
        self.llm_context_length = llm_context_length
        self.llm_prompts = llm_prompts
        self.ocr_fallback = ocr_fallback
        self.write_canonical_md = write_canonical_md
        self.output_dir = Path(output_dir) if output_dir else None
        self.progress_callback = progress_callback

        # LLM client (created on first use)
        self._llm_client: Optional[LLMClient] = None

        # Analysis timing (set after each analyze() call)
        self._last_analysis_duration: Optional[float] = None

        # Metrics collector for profiling
        self._metrics = MetricsCollector()
        self._last_profiling_report: Optional[ProfilingReport] = None

    def _get_llm_client(self) -> Optional[LLMClient]:
        """Get or create LLM client."""
        if not self.llm_refine:
            return None

        if self._llm_client is not None:
            return self._llm_client

        try:
            if self.llm_provider == "ollama":
                config = LLMConfig.ollama(
                    model=self.llm_model or "llama3.2",
                    base_url=self.llm_base_url,
                )
            elif self.llm_provider == "openai":
                config = LLMConfig.openai(
                    model=self.llm_model or "gpt-4o-mini",
                    api_key=self.llm_api_key,
                )
            elif self.llm_provider == "anthropic":
                config = LLMConfig.anthropic(
                    model=self.llm_model or "claude-3-5-sonnet-20241022",
                    api_key=self.llm_api_key,
                )
            elif self.llm_provider == "lm_studio":
                # LM Studio uses OpenAI-compatible API
                config = LLMConfig(
                    provider="openai",
                    model=self.llm_model or "local-model",
                    base_url=self.llm_base_url,
                    api_key="not-needed",
                )
            else:
                logger.warning(f"Unknown LLM provider: {self.llm_provider}")
                return None

            self._llm_client = LLMClient(config)

            # Test connection
            ok, msg = self._llm_client.test_connection()
            if ok:
                logger.info(f"LLM connected: {msg}")
            else:
                # Raise exception so caller knows LLM is unavailable
                raise RuntimeError(f"LLM connection failed: {msg}")

        except RuntimeError:
            # Re-raise connection failures
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to create LLM client: {e}")

        return self._llm_client

    def analyze(self, file_path: str | Path) -> AnalysisResult:
        """
        Analyze a book file and return structured results.

        Args:
            file_path: Path to PDF, DOCX, EPUB, or TXT file

        Returns:
            AnalysisResult with all extracted information
        """
        file_path = Path(file_path)
        warnings = []
        start_time = time.time()

        # Start metrics collection
        self._metrics.start_analysis()

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
            warnings.extend(doc.extraction_warnings)

        # Optionally write canonical markdown artifact
        if self.write_canonical_md:
            output_dir = self.output_dir or Path('output')
            output_dir.mkdir(exist_ok=True)
            md_path = output_dir / f"{file_path.stem}.canonical.md"
            canonical_md = to_canonical_markdown(doc)
            md_path.write_text(canonical_md, encoding='utf-8')
            print(f"   📝 Wrote canonical markdown: {md_path}")

        # Get LLM client
        llm = self._get_llm_client()

        # Step 2: Chapter Detection (using StructureAgent)
        print("📑 Detecting chapters...")
        with self._metrics.stage("Chapter Detection") as ctx:
            # Create agent and context
            structure_agent = StructureAgent(
                llm_client=llm,
                config=AgentConfig(enable_verification=True),
            )
            agent_context = AgentContext(
                text=doc.text,
                source_file=str(file_path),
            )

            # Run with self-verification
            structure_result = structure_agent.run_with_refinement(agent_context)
            chapter_map = structure_result.data

            # Record metrics from agent result
            ctx.record_items(
                total=structure_result.total_items,
                high_confidence=structure_result.high_confidence_count,
                medium_confidence=structure_result.medium_confidence_count,
                low_confidence=structure_result.low_confidence_count,
            )

            # Log any issues found during verification
            if structure_result.issues:
                for issue in structure_result.issues:
                    logger.info(f"Structure issue: {issue}")

        print(f"   Found {len(chapter_map.chapters)} chapters")

        # Step 3: Character Extraction
        print("👥 Extracting characters...")
        with self._metrics.stage("Character Extraction") as ctx:
            character_pipeline = CharacterExtractionPipeline(
                llm_client=llm,
                progress_callback=self._wrap_progress("characters"),
            )
            pipeline_char_map, _ = character_pipeline.run(
                doc.text, chapter_map, source_file=str(file_path)
            )

            # Record confidence metrics
            high = sum(1 for c in pipeline_char_map.characters if c.confidence >= 0.7)
            medium = sum(1 for c in pipeline_char_map.characters if 0.4 <= c.confidence < 0.7)
            low = sum(1 for c in pipeline_char_map.characters if c.confidence < 0.4) + len(pipeline_char_map.low_confidence_characters)
            ctx.record_items(total=len(pipeline_char_map.characters), high_confidence=high, medium_confidence=medium, low_confidence=low)

        print(f"   Found {len(pipeline_char_map.characters)} characters")

        # Step 3.5: Generate Character Profiles
        MIN_MENTIONS_FOR_PROFILE = 5
        if llm:
            print("📋 Generating character profiles...")
            with self._metrics.stage("Character Profiles") as ctx:
                # Generate profiles for all characters with sufficient mentions
                eligible_chars = [
                    c for c in pipeline_char_map.characters
                    if c.mention_count >= MIN_MENTIONS_FOR_PROFILE
                ]
                logger.info(f"Generating profiles for {len(eligible_chars)} characters (5+ mentions)")
                profile_count = 0
                for i, char in enumerate(eligible_chars):
                    logger.debug(f"Profile {i+1}/{len(eligible_chars)}: {char.canonical_name}")
                    profile = self._generate_character_profile(llm, char, doc.text)
                    if profile:
                        char.description = profile
                        profile_count += 1

                # Record metrics - all generated profiles are high confidence
                ctx.record_items(total=len(eligible_chars), high_confidence=profile_count, medium_confidence=0, low_confidence=len(eligible_chars) - profile_count)

            print(f"   Generated {profile_count} profiles for {len(eligible_chars)} eligible characters")

        # Step 4: Chapter Summaries
        print("📝 Generating chapter summaries...")
        if llm:
            with self._metrics.stage("Chapter Summaries") as ctx:
                summary_pipeline = ChapterSummaryPipeline(
                    llm_client=llm,
                    progress_callback=self._wrap_progress("summaries"),
                )
                summary_map, _ = summary_pipeline.run(
                    doc.text, chapter_map, pipeline_char_map, source_file=str(file_path)
                )

                # Record metrics - summaries don't have confidence scores, so count all as high
                ctx.record_items(total=len(summary_map.summaries), high_confidence=len(summary_map.summaries), medium_confidence=0, low_confidence=0)

            print(f"   Generated {len(summary_map.summaries)} summaries")
        else:
            summary_map = None
            print("   ⚠️  Skipped (no LLM)")

        # Step 5: Pronunciation Guide
        print("🗣️  Generating pronunciation guide...")
        with self._metrics.stage("Pronunciation Guide") as ctx:
            pronunciation_pipeline = PronunciationGuidePipeline(
                llm_client=llm,
                progress_callback=self._wrap_progress("pronunciation"),
            )
            pron_map, _ = pronunciation_pipeline.run(
                doc.text, chapter_map, pipeline_char_map, source_file=str(file_path)
            )

            # Record confidence metrics
            high = sum(1 for p in pron_map.entries if p.confidence >= 0.7)
            medium = sum(1 for p in pron_map.entries if 0.4 <= p.confidence < 0.7)
            low = sum(1 for p in pron_map.entries if p.confidence < 0.4) + len(pron_map.low_confidence_entries)
            ctx.record_items(total=len(pron_map.entries), high_confidence=high, medium_confidence=medium, low_confidence=low)

        print(f"   Flagged {len(pron_map.entries)} words")

        # Step 6: Convert to AnalysisResult
        print("📦 Building analysis result...")

        # Convert chapters to StructuralElements
        structure = self._convert_chapters(chapter_map, summary_map, self.words_per_minute)

        # Convert characters
        characters = self._convert_characters(pipeline_char_map)

        # Convert pronunciations
        pronunciations = self._convert_pronunciations(pron_map)

        # Calculate totals
        total_duration = sum(s.estimated_duration_minutes for s in structure)

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

        # Identify low-confidence items
        low_confidence = []
        for elem in structure:
            if elem.confidence == ConfidenceLevel.LOW:
                low_confidence.append(f"Structure: {elem.type.value} at position {elem.start_position}")
        for char in characters:
            if char.confidence == ConfidenceLevel.LOW:
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

        # Track analysis duration
        self._last_analysis_duration = time.time() - start_time
        duration_str = self._format_duration(self._last_analysis_duration)

        # Generate and store profiling report
        self._last_profiling_report = self._metrics.get_report()

        print(f"✅ Analysis complete in {duration_str}!")

        # Display profiling report
        print("")
        print(self._last_profiling_report.format_table())

        return result

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable form (e.g., '2m 34s')."""
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        if mins > 0:
            return f"{mins}m {secs}s"
        return f"{secs}s"

    def _wrap_progress(self, stage: str) -> Optional[Callable[[str, int, int], None]]:
        """Wrap progress callback with stage prefix."""
        if not self.progress_callback:
            return None

        def wrapped(substage: str, current: int, total: int):
            self.progress_callback(f"{stage}:{substage}", current, total)

        return wrapped

    def _generate_character_profile(
        self,
        llm: "LLMClient",
        character,
        full_text: str,
    ) -> str:
        """Generate prose profile for a character using LLM."""
        # Gather context snippets from character mentions
        contexts = []
        for mention in character.mentions[:5]:  # First 5 mentions for context
            start = max(0, mention.position - 100)
            end = min(len(full_text), mention.position + 100)
            snippet = full_text[start:end].strip()
            # Clean up partial words at boundaries
            if start > 0:
                snippet = "..." + snippet.split(" ", 1)[-1] if " " in snippet else snippet
            if end < len(full_text):
                snippet = snippet.rsplit(" ", 1)[0] + "..." if " " in snippet else snippet
            contexts.append(f"- {snippet}")

        context_text = "\n".join(contexts[:5]) if contexts else "No context available."

        prompt = f"""Write a brief character profile (2-3 sentences) for "{character.canonical_name}".

Context where this character appears:
{context_text}

Focus on: their role in the story, notable traits, and key relationships.
Return ONLY the prose description, no headers, labels, or formatting."""

        try:
            response = llm.query(prompt)
            if response.success:
                # Clean up any thinking tags or extra formatting
                text = response.content.strip()
                # Remove common LLM artifacts
                if text.startswith('"') and text.endswith('"'):
                    text = text[1:-1]
                return text
        except Exception as e:
            logger.warning(f"Failed to generate profile for {character.canonical_name}: {e}")

        return ""

    def _convert_chapters(
        self,
        chapter_map: ChapterMap,
        summary_map: Optional[ChapterSummaryMap],
        wpm: int,
    ) -> list[StructuralElement]:
        """Convert pipeline ChapterMap to list of StructuralElements."""
        elements = []

        # Build summary lookup
        summaries = {}
        if summary_map:
            for s in summary_map.summaries:
                summaries[s.chapter_index] = s

        for chapter in chapter_map.chapters:
            # Calculate duration
            duration = chapter.word_count / wpm

            # Get summary if available
            summary_text = None
            characters_present = []
            if chapter.index in summaries:
                summary_obj = summaries[chapter.index]
                summary_text = summary_obj.summary
                characters_present = summary_obj.characters_present

            # Map confidence
            if chapter.confidence >= 0.8:
                confidence = ConfidenceLevel.HIGH
            elif chapter.confidence >= 0.5:
                confidence = ConfidenceLevel.MEDIUM
            else:
                confidence = ConfidenceLevel.LOW

            elements.append(StructuralElement(
                type=StructureType.CHAPTER,
                title=chapter.title,
                index=chapter.index,
                start_position=chapter.start_position,
                end_position=chapter.end_position,
                word_count=chapter.word_count,
                estimated_duration_minutes=duration,
                confidence=confidence,
                summary=summary_text,
                characters_present=characters_present,
            ))

        return elements

    def _convert_characters(
        self,
        char_map: PipelineCharacterMap,
    ) -> list[Character]:
        """Convert pipeline CharacterMap to list of Character models."""
        characters = []

        for pc in char_map.characters:
            # Map confidence
            if pc.confidence >= 0.8:
                confidence = ConfidenceLevel.HIGH
            elif pc.confidence >= 0.5:
                confidence = ConfidenceLevel.MEDIUM
            else:
                confidence = ConfidenceLevel.LOW

            # Build descriptions list if profile was generated
            descriptions = []
            if pc.description:
                descriptions.append(CharacterDescription(
                    text=pc.description,
                    source_position=pc.mentions[0].position if pc.mentions else 0,
                    confidence=ConfidenceLevel.LLM_REFINED,
                ))

            characters.append(Character(
                id=pc.id,
                canonical_name=pc.canonical_name,
                aliases=pc.aliases,
                descriptions=descriptions,
                first_appearance_chapter=pc.first_appearance_chapter,
                mention_count=pc.mention_count,
                confidence=confidence,
            ))

        # Also add low confidence characters (no profiles generated for these)
        for pc in char_map.low_confidence_characters:
            characters.append(Character(
                id=pc.id,
                canonical_name=pc.canonical_name,
                aliases=pc.aliases,
                first_appearance_chapter=pc.first_appearance_chapter,
                mention_count=pc.mention_count,
                confidence=ConfidenceLevel.LOW,
            ))

        return characters

    def _convert_pronunciations(
        self,
        pron_map: PronunciationMap,
    ) -> list[PronunciationEntry]:
        """Convert pipeline PronunciationMap to list of PronunciationEntry models."""
        entries = []

        # Map flag reasons
        flag_mapping = {
            PipelinePronunciationFlag.PROPER_NOUN: ModelPronunciationFlag.PROPER_NOUN,
            PipelinePronunciationFlag.FOREIGN: ModelPronunciationFlag.FOREIGN,
            PipelinePronunciationFlag.HOMOGRAPH: ModelPronunciationFlag.HOMOGRAPH,
            PipelinePronunciationFlag.UNKNOWN: ModelPronunciationFlag.UNKNOWN,
            PipelinePronunciationFlag.CHARACTER: ModelPronunciationFlag.PROPER_NOUN,  # Map CHARACTER to PROPER_NOUN
        }

        for pe in pron_map.entries:
            # Map confidence
            if pe.confidence >= 0.8:
                confidence = ConfidenceLevel.HIGH
            elif pe.confidence >= 0.5:
                confidence = ConfidenceLevel.MEDIUM
            else:
                confidence = ConfidenceLevel.LOW

            # Map flag reason
            flag = flag_mapping.get(pe.flag_reason, ModelPronunciationFlag.UNKNOWN)

            entries.append(PronunciationEntry(
                word=pe.word,
                flag_reason=flag,
                occurrences=pe.occurrence_count,
                first_position=pe.first_position,
                chapter_indices=pe.chapters_present,
                context_examples=pe.context_examples[:3],
                confidence=confidence,
                ipa=pe.ipa,
                phonetic_spelling=pe.phonetic_spelling,
                notes=pe.notes,
            ))

        # Also add low confidence entries
        for pe in pron_map.low_confidence_entries:
            flag = flag_mapping.get(pe.flag_reason, ModelPronunciationFlag.UNKNOWN)

            entries.append(PronunciationEntry(
                word=pe.word,
                flag_reason=flag,
                occurrences=pe.occurrence_count,
                first_position=pe.first_position,
                chapter_indices=pe.chapters_present,
                context_examples=pe.context_examples[:3],
                confidence=ConfidenceLevel.LOW,
                ipa=pe.ipa,
                phonetic_spelling=pe.phonetic_spelling,
                notes=pe.notes,
            ))

        return entries

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
            'analyzer_version': '0.2.0',
            'pipeline': 'multi-agent',
            'llm_model': self.llm_model or 'none',
            'llm_provider': self.llm_provider if self.llm_refine else 'none',
            'analysis_duration_seconds': round(self._last_analysis_duration, 1) if self._last_analysis_duration else None,
        }

        # Add profiling data if available
        if self._last_profiling_report:
            result_dict['_profiling'] = self._last_profiling_report.to_dict()

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
