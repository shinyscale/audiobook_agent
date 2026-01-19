"""
Main analyzer orchestrator.
Coordinates ingestion and analysis pipeline.
"""

from pathlib import Path
from typing import Optional, Callable, Tuple
from concurrent.futures import ThreadPoolExecutor
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
    GlossaryEntry as ModelGlossaryEntry,
    GlossaryMap,
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
from .pipeline.overview import OverviewGenerator

# Character profiling pipeline components (F1-F5)
from .pipeline.character_profiling import (
    # F1: Summary-driven character merge detection
    SummaryMerger,
    SummaryMergeResult,
    find_summary_merges,
    apply_summary_merges,
    # F2: Summary evidence extraction
    SummaryEvidenceExtractor,
    CharacterSummaryEvidence,
    # F3: Moral valence classification
    MoralValence,
    MoralValenceClassifier,
    MoralValenceResult,
    MORAL_VALENCE_CONSTRAINTS,
    # F5: Tag identity propagation
    TagIdentityExtractor,
    extract_tag_identities,
)

# Agent imports
from .agents import (
    StructureAgent,
    CharacterAgent,
    SummaryAgent,
    PronunciationAgent,
    AgentContext,
    AgentConfig,
    OrchestratorConfig,
)
from .agents.validation import (
    PipelineHaltReport,
    UpstreamValidationResult,
    get_recommendations_for_issue,
)
from .export.quality_report import generate_quality_report, QualityReport
from .ingestion.regions import RegionType

# LLM prompts config (keep for compatibility)
try:
    from .llm.prompts import PromptConfig
    HAS_PROMPTS = True
except ImportError:
    HAS_PROMPTS = False
    PromptConfig = None  # type: ignore

logger = logging.getLogger(__name__)


# Character profile system prompt for evidence-based generation
CHARACTER_PROFILE_SYSTEM = """You are a literary analyst creating evidence-based character profiles for audiobook narration.

CRITICAL: Base your analysis ONLY on the text provided below.
Do NOT use any prior knowledge about this book, author, or characters.
If you recognize this as a famous work, IGNORE what you know about it.
Analyze only what is explicitly written in the provided text.

Your profiles help narrators understand:
- Character traits supported by textual evidence
- Relationships between characters
- What we confidently know vs. what is uncertain

Always respond with valid JSON. No other text."""


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
        orchestrator_config: Optional[OrchestratorConfig] = None,
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
        self.orchestrator_config = orchestrator_config

        # LLM client (created on first use)
        self._llm_client: Optional[LLMClient] = None
        # Agent-specific LLM clients cache
        self._agent_llm_clients: dict[str, LLMClient] = {}

        # Analysis timing (set after each analyze() call)
        self._last_analysis_duration: Optional[float] = None

        # Metrics collector for profiling
        self._metrics = MetricsCollector()
        self._last_profiling_report: Optional[ProfilingReport] = None

        # Halt report (set if pipeline halted due to validation failure)
        self._last_halt_report: Optional[PipelineHaltReport] = None

        # Quality report and per-run output directory
        self._last_quality_report: Optional[QualityReport] = None
        self._last_run_dir: Optional[Path] = None

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

            self._llm_client = LLMClient(config, metrics=self._metrics)

            # Run health check to detect broken models (empty responses, etc.)
            ok, msg = self._llm_client.health_check()
            if ok:
                logger.info(f"LLM health check passed: {msg}")
            else:
                # Raise exception so caller knows LLM is unavailable/broken
                logger.warning(f"LLM health check failed: {msg}")
                raise RuntimeError(f"LLM health check failed: {msg}")

        except RuntimeError:
            # Re-raise connection failures
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to create LLM client: {e}")

        return self._llm_client

    def _get_agent_llm_client(self, agent_name: str) -> Optional[LLMClient]:
        """
        Get LLM client configured for a specific agent.

        If orchestrator_config specifies a model for this agent, creates
        an agent-specific client. Otherwise falls back to default client.
        """
        if not self.llm_refine:
            return None

        # Check if we have an orchestrator config with agent-specific settings
        if self.orchestrator_config:
            agent_config = self.orchestrator_config.get_agent_config(agent_name)
            if agent_config.model and agent_config.model != self.llm_model:
                # Need agent-specific client
                if agent_name in self._agent_llm_clients:
                    return self._agent_llm_clients[agent_name]

                try:
                    # Create client based on agent config
                    provider = agent_config.provider or self.llm_provider
                    base_url = agent_config.base_url or self.llm_base_url

                    if provider == "ollama":
                        config = LLMConfig.ollama(
                            model=agent_config.model,
                            base_url=base_url,
                        )
                    elif provider == "openai":
                        config = LLMConfig.openai(
                            model=agent_config.model,
                            api_key=agent_config.get_api_key() or self.llm_api_key,
                        )
                    elif provider in ("lm_studio", "openai_compatible"):
                        config = LLMConfig(
                            provider="openai",
                            model=agent_config.model,
                            base_url=base_url,
                            api_key="not-needed",
                        )
                    else:
                        # Fall back to default
                        return self._get_llm_client()

                    # Apply agent-specific settings
                    config.temperature = agent_config.temperature
                    config.think = agent_config.think_mode
                    config.context_length = agent_config.context_length or self.orchestrator_config.context_length

                    client = LLMClient(config, metrics=self._metrics)
                    self._agent_llm_clients[agent_name] = client
                    logger.info(f"Created agent-specific LLM client for {agent_name}: {agent_config.model}")
                    return client

                except Exception as e:
                    logger.warning(f"Failed to create agent-specific client for {agent_name}: {e}")
                    # Fall back to default

        # Fall back to default client
        return self._get_llm_client()

    def _get_agent_config(self, agent_name: str) -> Optional[AgentConfig]:
        """Get configuration for a specific agent."""
        if self.orchestrator_config:
            return self.orchestrator_config.get_agent_config(agent_name)
        return AgentConfig()

    def _create_llm_client_for_agent(self, agent_name: str) -> Optional[LLMClient]:
        """
        Create a NEW LLM client for an agent (for parallel execution).

        Unlike _get_agent_llm_client, this always creates a fresh client
        to avoid thread contention issues in parallel execution.
        """
        if not self.llm_refine:
            return None

        # Get agent-specific configuration
        agent_config = None
        if self.orchestrator_config:
            agent_config = self.orchestrator_config.get_agent_config(agent_name)
            provider = agent_config.provider or self.llm_provider
            base_url = agent_config.base_url or self.llm_base_url
            model = agent_config.model or self.llm_model
            temperature = agent_config.temperature
            think_mode = agent_config.think_mode
            context_length = agent_config.context_length or self.orchestrator_config.context_length
        else:
            provider = self.llm_provider
            base_url = self.llm_base_url
            model = self.llm_model
            temperature = 0.3
            think_mode = False
            context_length = self.llm_context_length

        try:
            if provider == "ollama":
                config = LLMConfig.ollama(model=model, base_url=base_url)
            elif provider == "openai":
                config = LLMConfig.openai(model=model, api_key=self.llm_api_key)
            elif provider in ("lm_studio", "openai_compatible"):
                config = LLMConfig(
                    provider="openai",
                    model=model,
                    base_url=base_url,
                    api_key="not-needed",
                )
            else:
                config = LLMConfig.ollama(model=model, base_url=base_url)

            # Apply agent-specific settings
            config.temperature = temperature
            config.think = think_mode
            config.context_length = context_length

            return LLMClient(config, metrics=self._metrics)
        except Exception as e:
            logger.warning(f"Failed to create LLM client for {agent_name}: {e}")
            return None

    def _are_quality_gates_enabled(self) -> bool:
        """Check if quality gates are enabled in orchestrator config."""
        return (
            self.orchestrator_config is not None
            and self.orchestrator_config.enable_quality_gates
        )

    def _filter_pronunciation_by_body(
        self,
        pron_map: PronunciationMap,
        doc: ExtractedDocument,
    ) -> PronunciationMap:
        """
        Filter pronunciation entries to only include those in the body region.

        Args:
            pron_map: Pronunciation map to filter
            doc: Document with region information

        Returns:
            Filtered pronunciation map (or original if no regions)
        """
        if not doc.regions:
            return pron_map

        # Find body region boundaries
        body_regions = [r for r in doc.regions if r.region_type == RegionType.BODY]
        if not body_regions:
            return pron_map

        # Use the first body region (should only be one)
        body_start = body_regions[0].start_position
        body_end = body_regions[0].end_position

        return pron_map.filter_by_body_region(body_start, body_end)

    def _validate_for_agent(
        self,
        agent,
        context: AgentContext,
        partial_results: dict,
    ) -> Tuple[bool, Optional[PipelineHaltReport]]:
        """
        Validate upstream data before running an agent.

        Args:
            agent: The agent to validate for
            context: Agent context with upstream results
            partial_results: Results completed so far

        Returns:
            Tuple of (can_proceed, halt_report)
            - If can_proceed is True, halt_report is None
            - If can_proceed is False, halt_report contains the diagnostic
        """
        if not self._are_quality_gates_enabled():
            return True, None

        validation = agent.validate_upstream(context)

        # Log warnings even if we can proceed
        for issue in validation.issues:
            if issue.severity.value == "warning":
                logger.warning(f"{agent.name}: {issue.description}")

        if validation.can_proceed:
            return True, None

        # Generate halt report
        recommendations = []
        for issue in validation.issues:
            recommendations.extend(get_recommendations_for_issue(issue))

        # Deduplicate recommendations
        recommendations = list(dict.fromkeys(recommendations))

        halt_report = PipelineHaltReport(
            halted_at=agent.name,
            halted_reason=validation.issues[0].description if validation.issues else "Validation failed",
            upstream_issues=validation.issues,
            partial_results=partial_results,
            recommendations=recommendations[:5],  # Limit to top 5
        )

        return False, halt_report

    def _save_halt_report(self, halt_report: PipelineHaltReport, file_path: Path) -> Optional[Path]:
        """
        Save a halt report to disk.

        Args:
            halt_report: The halt report to save
            file_path: Original input file path (for naming)

        Returns:
            Path to saved report, or None if output_dir not set
        """
        if not self.output_dir:
            return None

        self.output_dir.mkdir(parents=True, exist_ok=True)
        report_path = self.output_dir / f"{file_path.stem}.halt-report.md"
        report_path.write_text(halt_report.to_markdown(), encoding='utf-8')

        return report_path

    def _build_partial_result(
        self,
        doc: ExtractedDocument,
        file_path: Path,
        chapter_map: ChapterMap,
        character_map: Optional[PipelineCharacterMap],
        pron_map: Optional[PronunciationMap],
        summary_map: Optional[ChapterSummaryMap],
        warnings: list[str],
        start_time: float,
    ) -> AnalysisResult:
        """
        Build an AnalysisResult from partial pipeline results.

        Used when pipeline halts due to validation failure.
        """
        # Convert chapters to StructuralElements
        structure = self._convert_chapters(chapter_map, summary_map, self.words_per_minute)

        # Convert characters (if available)
        characters = []
        if character_map:
            characters = self._convert_characters(character_map)

        # Convert pronunciations (if available)
        pronunciations = []
        if pron_map:
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

        # Convert glossary if present
        glossary_map = self._convert_glossary(doc)

        result = AnalysisResult(
            metadata=metadata,
            structure=structure,
            characters=characters,
            pronunciations=pronunciations,
            glossary=glossary_map,
            overview=None,  # No overview for partial results
            raw_text=doc.text,
            warnings=warnings,
            low_confidence_items=low_confidence,
        )

        # Track analysis duration
        self._last_analysis_duration = time.time() - start_time

        # Generate profiling report
        self._last_profiling_report = self._metrics.get_report()

        return result

    def _run_agents_parallel(
        self,
        doc: ExtractedDocument,
        file_path: Path,
        chapter_map: ChapterMap,
    ) -> Tuple:
        """
        Run CharacterAgent and PronunciationAgent in parallel.

        Both agents depend only on StructureAgent, so they can run concurrently.
        This significantly reduces total analysis time.

        Returns:
            Tuple of (character_result, pronunciation_result)
        """
        max_workers = 2
        if self.orchestrator_config:
            max_workers = min(2, self.orchestrator_config.max_parallel_workers)

        character_result = None
        pronunciation_result = None
        character_error = None
        pronunciation_error = None

        def run_character_agent():
            """Run CharacterAgent in a thread."""
            nonlocal character_error
            try:
                with self._metrics.stage("Character Extraction") as ctx:
                    # Create fresh LLM client for this thread
                    char_llm = self._create_llm_client_for_agent("characters")
                    char_config = self._get_agent_config("characters")
                    char_config.enable_verification = True

                    # Set model info from LLM client config (before running agent)
                    if char_llm and char_llm.config:
                        ctx.set_model(char_llm.config.model, char_llm.config.provider)

                    character_agent = CharacterAgent(
                        llm_client=char_llm,
                        config=char_config,
                        tuning=(self.orchestrator_config.tuning if self.orchestrator_config else None),
                    )
                    char_agent_context = AgentContext(
                        text=doc.text,
                        source_file=str(file_path),
                        chapter_map=chapter_map,
                    )

                    result = character_agent.run_with_refinement(char_agent_context)

                    ctx.record_items(
                        total=result.total_items,
                        high_confidence=result.high_confidence_count,
                        medium_confidence=result.medium_confidence_count,
                        low_confidence=result.low_confidence_count,
                    )

                    if result.issues:
                        for issue in result.issues:
                            logger.info(f"Character issue: {issue}")

                    return result
            except Exception as e:
                character_error = e
                logger.error(f"CharacterAgent failed: {e}")
                return None

        def run_pronunciation_agent():
            """Run PronunciationAgent in a thread."""
            nonlocal pronunciation_error
            try:
                with self._metrics.stage("Pronunciation Guide") as ctx:
                    # Create fresh LLM client for this thread
                    pron_llm = self._create_llm_client_for_agent("pronunciation")
                    pron_config = self._get_agent_config("pronunciation")

                    # Set model info from LLM client config (before running pipeline)
                    if pron_llm and pron_llm.config:
                        ctx.set_model(pron_llm.config.model, pron_llm.config.provider)

                    pronunciation_pipeline = PronunciationGuidePipeline(
                        llm_client=pron_llm,
                        progress_callback=self._wrap_progress("pronunciation"),
                    )
                    pron_map, _ = pronunciation_pipeline.run(
                        doc.text, chapter_map, None, source_file=str(file_path)
                    )

                    # Record confidence metrics
                    high = sum(1 for p in pron_map.entries if p.confidence >= 0.7)
                    medium = sum(1 for p in pron_map.entries if 0.4 <= p.confidence < 0.7)
                    low = sum(1 for p in pron_map.entries if p.confidence < 0.4) + len(pron_map.low_confidence_entries)
                    ctx.record_items(total=len(pron_map.entries), high_confidence=high, medium_confidence=medium, low_confidence=low)

                    return pron_map
            except Exception as e:
                pronunciation_error = e
                logger.error(f"PronunciationAgent failed: {e}")
                return None

        # Run in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            char_future = executor.submit(run_character_agent)
            pron_future = executor.submit(run_pronunciation_agent)

            character_result = char_future.result()
            pronunciation_result = pron_future.result()

        return character_result, pronunciation_result

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

        # Reset halt report
        self._last_halt_report = None

        # Start metrics collection
        self._metrics.start_analysis()

        # Clear debug logs for this run (avoid cumulative logs across runs)
        log_dir = Path.home() / '.audiobook-prep'
        llm_log = log_dir / 'llm.log'
        pipeline_log = log_dir / 'pipeline.log'
        if llm_log.exists():
            llm_log.unlink()  # Delete the file, logger will recreate it on first write
        if pipeline_log.exists():
            pipeline_log.unlink()  # Delete the file, logger will recreate it on first write

        # Step 1: Ingest document
        print(f"📖 Ingesting: {file_path.name}")
        ingester = get_ingester(file_path, ocr_fallback=self.ocr_fallback)
        doc = ingester.extract(file_path)

        print(f"   Extracted {doc.word_count:,} words")

        # Step 1.5: Refine extracted text (deterministic)
        # Note: On first run, this may download word segmentation data (~25MB, takes 10-30s)
        print("🔧 Refining text (may download word data on first run)...")
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

        # Get default LLM client (for pipelines that don't have agents yet)
        llm = self._get_llm_client()

        # Step 2: Chapter Detection (using StructureAgent)
        print("📑 Detecting chapters...")
        self._write_progress("Chapter Detection", self._get_agent_config("structure").model if self._get_agent_config("structure") else None)
        with self._metrics.stage("Chapter Detection") as ctx:
            # Create agent with agent-specific LLM client
            structure_llm = self._get_agent_llm_client("structure")
            structure_config = self._get_agent_config("structure")
            structure_config.enable_verification = True

            # Set model info from LLM client config (before running agent)
            if structure_llm and structure_llm.config:
                ctx.set_model(structure_llm.config.model, structure_llm.config.provider)

            structure_agent = StructureAgent(
                llm_client=structure_llm,
                config=structure_config,
                tuning=(self.orchestrator_config.tuning if self.orchestrator_config else None),
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

        # Check if parallel execution is enabled
        use_parallel = (
            self.orchestrator_config
            and self.orchestrator_config.parallel_execution
        )

        if use_parallel:
            # Step 3+5 PARALLEL: Run CharacterAgent and PronunciationAgent in parallel
            print("🔀 Running character extraction and pronunciation in parallel...")
            character_result, pron_map = self._run_agents_parallel(doc, file_path, chapter_map)

            if character_result:
                pipeline_char_map = character_result.data
                print(f"   Found {len(pipeline_char_map.characters)} characters")
            else:
                # Fallback to empty character map if agent failed
                pipeline_char_map = PipelineCharacterMap(characters=[], source_file=str(file_path))
                print("   ⚠️  Character extraction failed, continuing with empty character map")

            if pron_map:
                # Filter out front/back matter entries
                pron_map = self._filter_pronunciation_by_body(pron_map, doc)
                print(f"   Flagged {len(pron_map.entries)} pronunciation words")
            else:
                # Fallback to empty pronunciation map
                pron_map = PronunciationMap(entries=[], source_file=str(file_path))
                print("   ⚠️  Pronunciation guide failed, continuing with empty map")

        else:
            # Step 3 SEQUENTIAL: Character Extraction (using CharacterAgent)
            print("👥 Extracting characters...")
            self._write_progress("Character Extraction", self._get_agent_config("characters").model if self._get_agent_config("characters") else None)
            with self._metrics.stage("Character Extraction") as ctx:
                # Create agent with agent-specific LLM client
                # Note: CharacterAgent uses "characters" config key for backwards compat
                char_llm = self._get_agent_llm_client("characters")
                char_config = self._get_agent_config("characters")
                char_config.enable_verification = True

                # Set model info from LLM client config (before running agent)
                if char_llm and char_llm.config:
                    ctx.set_model(char_llm.config.model, char_llm.config.provider)

                character_agent = CharacterAgent(
                    llm_client=char_llm,
                    config=char_config,
                    tuning=(self.orchestrator_config.tuning if self.orchestrator_config else None),
                )
                char_agent_context = AgentContext(
                    text=doc.text,
                    source_file=str(file_path),
                    chapter_map=chapter_map,
                )

                # Run with self-verification
                character_result = character_agent.run_with_refinement(char_agent_context)
                pipeline_char_map = character_result.data

                # Record metrics from agent result
                ctx.record_items(
                    total=character_result.total_items,
                    high_confidence=character_result.high_confidence_count,
                    medium_confidence=character_result.medium_confidence_count,
                    low_confidence=character_result.low_confidence_count,
                )

                # Log any issues found during verification
                if character_result.issues:
                    for issue in character_result.issues:
                        logger.info(f"Character issue: {issue}")

            print(f"   Found {len(pipeline_char_map.characters)} characters")

            # pron_map will be set in Step 5 below (sequential mode)
            pron_map = None

        # Step 3.5: Detect Narrator (before profile generation)
        # Check if this is a first-person narrative and identify the narrator
        narrator_detected = self._detect_narrator(doc.text, pipeline_char_map.characters)
        if narrator_detected:
            print(f"📖 Detected narrator: {narrator_detected}")

            # Boost confidence for detected narrator
            # Narrator should have at least "high" confidence (≥ 0.8)
            for char in pipeline_char_map.characters:
                if char.canonical_name == narrator_detected:
                    if char.confidence < 0.8:
                        logger.info(
                            f"Boosting narrator confidence: {char.canonical_name} "
                            f"{char.confidence:.2f} → 0.85"
                        )
                        char.confidence = 0.85
                    break

        # NOTE: Character profiles are now generated AFTER summaries (Step 4.5)
        # This allows us to use summary-derived features (F1, F2, F3, F5)

        # Step 4: Chapter Summaries
        print("📝 Generating chapter summaries...")
        self._write_progress("Chapter Summaries", self._get_agent_config("summaries").model if self._get_agent_config("summaries") else None)

        # Validate chapter_map before summarization (if quality gates enabled)
        if self._are_quality_gates_enabled():
            summary_agent_for_validation = SummaryAgent(
                tuning=(self.orchestrator_config.tuning if self.orchestrator_config else None),
            )
            validation_context = AgentContext(
                text=doc.text,
                source_file=str(file_path),
                chapter_map=chapter_map,
                character_map=pipeline_char_map,
            )
            partial_results = {
                "structure": chapter_map,
                "characters": pipeline_char_map,
                "pronunciation": pron_map,
            }

            can_proceed, halt_report = self._validate_for_agent(
                summary_agent_for_validation,
                validation_context,
                partial_results,
            )

            if not can_proceed:
                self._last_halt_report = halt_report
                report_path = self._save_halt_report(halt_report, file_path)

                print(f"\n PIPELINE HALTED: {halt_report.halted_reason}")
                if report_path:
                    print(f"   Halt report saved to: {report_path}")
                print("   Recommendations:")
                for rec in halt_report.recommendations[:3]:
                    print(f"   - {rec}")

                # Return partial result with warnings
                return self._build_partial_result(
                    doc=doc,
                    file_path=file_path,
                    chapter_map=chapter_map,
                    character_map=pipeline_char_map,
                    pron_map=pron_map,
                    summary_map=None,
                    warnings=warnings + [f"Pipeline halted: {halt_report.halted_reason}"],
                    start_time=start_time,
                )

        # Use agent-specific LLM client for summaries
        summary_llm = self._get_agent_llm_client("summaries")
        if summary_llm:
            with self._metrics.stage("Chapter Summaries") as ctx:
                # Set model info from LLM client config (before running)
                if summary_llm and summary_llm.config:
                    ctx.set_model(summary_llm.config.model, summary_llm.config.provider)

                # Check if parallel chapter summaries are enabled
                parallel_summaries = (
                    use_parallel
                    and self.orchestrator_config
                    and self.orchestrator_config.parallel_chapter_summaries
                )
                max_workers = (
                    self.orchestrator_config.max_parallel_workers
                    if self.orchestrator_config
                    else 4
                )

                # Factory to create fresh LLM clients for parallel execution
                def summary_llm_factory():
                    return self._create_llm_client_for_agent("summaries")

                summary_pipeline = ChapterSummaryPipeline(
                    llm_client=summary_llm,
                    progress_callback=self._wrap_progress("summaries"),
                    parallel_chapters=parallel_summaries,
                    max_workers=max_workers,
                    llm_client_factory=summary_llm_factory if parallel_summaries else None,
                    summarizer_chunk_size_words=(
                        self.orchestrator_config.tuning.summary_chunk_words
                        if self.orchestrator_config
                        else 2500
                    ),
                    summarizer_chunk_overlap_words=(
                        self.orchestrator_config.tuning.summary_chunk_overlap_words
                        if self.orchestrator_config
                        else 200
                    ),
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

        # Step 4.5: Summary-Driven Character Merges and Profile Generation (F1, F2, F3, F5)
        # Now that summaries are available, we can apply summary-based character merges
        # and generate enriched profiles with moral valence constraints.
        if summary_map and llm:
            # F1: Summary-Driven Character Merge Detection
            # Detects explicit identity statements like "Cathy Ames—later revealed to be Kate"
            print("🔗 Applying summary-driven character merges (F1)...")
            try:
                summary_merger = SummaryMerger(llm_client=llm)
                # Combine all chapter summaries into a plot summary
                combined_summary = "\n\n".join([
                    f"Chapter {s.chapter_index}: {s.summary}"
                    for s in summary_map.summaries
                ])
                merge_result = summary_merger.find_identity_statements(combined_summary, use_llm=True)

                if merge_result.merge_pairs:
                    logger.info(f"F1: Found {len(merge_result.merge_pairs)} identity statements from summaries")
                    for stmt in merge_result.statements:
                        logger.info(f"  - '{stmt.name_a}' = '{stmt.name_b}' (pattern: {stmt.pattern_matched})")

                    # Apply merges to character list
                    original_count = len(pipeline_char_map.characters)
                    pipeline_char_map.characters = apply_summary_merges(
                        pipeline_char_map.characters,
                        merge_result,
                    )
                    merged_count = original_count - len(pipeline_char_map.characters)
                    if merged_count > 0:
                        print(f"   Merged {merged_count} character(s) based on identity statements")
                else:
                    logger.info("F1: No explicit identity statements found in summaries")
            except Exception as e:
                logger.warning(f"F1 summary merger failed: {e}")

            # F5: Tag Identity Propagation
            # Detects compound character tags like "Cathy/Kate" in chapter summaries
            print("🏷️  Extracting tag identities (F5)...")
            try:
                tag_extractor = TagIdentityExtractor()
                tag_result = tag_extractor.extract(summary_map)

                if tag_result.matches:
                    logger.info(f"F5: Found {len(tag_result.matches)} compound name tags")
                    for match in tag_result.matches:
                        logger.info(f"  - '{match.name1}/{match.name2}' in chapter {match.chapter_index}")

                    # Convert tag identity matches to merge format and apply
                    tag_merge_pairs = [(m.name1, m.name2) for m in tag_result.matches]
                    tag_merge_result = SummaryMergeResult(
                        merge_pairs=tag_merge_pairs,
                        statements=[],  # Not statement-based
                        raw_summary="",
                    )
                    original_count = len(pipeline_char_map.characters)
                    pipeline_char_map.characters = apply_summary_merges(
                        pipeline_char_map.characters,
                        tag_merge_result,
                    )
                    merged_count = original_count - len(pipeline_char_map.characters)
                    if merged_count > 0:
                        print(f"   Merged {merged_count} character(s) based on compound tags")
                else:
                    logger.info("F5: No compound name tags found")
            except Exception as e:
                logger.warning(f"F5 tag identity extraction failed: {e}")

        # Step 4.6: Generate Character Profiles with Summary Evidence and Moral Valence (F2, F3)
        # Adaptive threshold based on text length
        # For short texts (< 5000 words), use a lower threshold
        # For normal texts (5000-50000 words), use standard threshold
        # For long texts (> 50000 words), maintain standard threshold
        word_count = len(doc.text.split())
        if word_count < 5000:
            # Short story: profile characters with 2+ mentions
            MIN_MENTIONS_FOR_PROFILE = 2
            logger.info(f"Short text detected ({word_count} words) - using MIN_MENTIONS_FOR_PROFILE = 2")
        else:
            # Standard threshold for longer texts
            MIN_MENTIONS_FOR_PROFILE = 5

        if llm:
            print("📋 Generating character profiles...")
            self._write_progress("Character Profiles", llm.config.model if llm and llm.config else None)
            with self._metrics.stage("Character Profiles") as ctx:
                # Set model info from LLM client config (before running)
                if llm and llm.config:
                    ctx.set_model(llm.config.model, llm.config.provider)

                # F2: Initialize summary evidence extractor (if summaries available)
                summary_evidence_extractor = None
                if summary_map:
                    summary_evidence_extractor = SummaryEvidenceExtractor(llm)
                    logger.info("F2: Summary evidence extraction enabled")

                # F3: Initialize moral valence classifier
                moral_valence_classifier = MoralValenceClassifier(llm)
                logger.info("F3: Moral valence classification enabled")

                # Generate profiles for all characters with sufficient mentions
                # SPECIAL CASE: Include narrators even if they have few explicit mentions
                # (first-person narrators may use "I" throughout without saying their name)
                eligible_chars = [
                    c for c in pipeline_char_map.characters
                    if c.mention_count >= MIN_MENTIONS_FOR_PROFILE or getattr(c, 'is_narrator', False)
                ]
                logger.info(f"Generating profiles for {len(eligible_chars)} eligible characters ({MIN_MENTIONS_FOR_PROFILE}+ mentions or narrator)")
                profile_count = 0
                high_conf_count = 0
                medium_conf_count = 0
                low_conf_count = 0

                for i, char in enumerate(eligible_chars):
                    logger.debug(f"Profile {i+1}/{len(eligible_chars)}: {char.canonical_name}")

                    # F2: Extract summary evidence for this character
                    summary_evidence = None
                    if summary_evidence_extractor and summary_map:
                        try:
                            # Check if this character is the narrator
                            is_char_narrator = (
                                narrator_detected and
                                char.canonical_name == narrator_detected
                            )
                            narrative_style = "first-person" if narrator_detected else "unknown"

                            summary_evidence = summary_evidence_extractor.extract_evidence(
                                char.canonical_name,
                                char.aliases,
                                summary_map,
                                is_narrator=is_char_narrator,
                                narrative_style=narrative_style,
                            )
                            if summary_evidence.evidence:
                                logger.debug(
                                    f"F2: Found {len(summary_evidence.evidence)} summary evidence items "
                                    f"for {char.canonical_name}"
                                )
                        except Exception as e:
                            logger.warning(f"F2: Summary evidence extraction failed for {char.canonical_name}: {e}")

                    # F3: Classify moral valence to constrain profile generation
                    moral_valence = None
                    try:
                        # Get character role from extraction (if available)
                        role = "supporting"  # Default
                        # Gather some context passages for valence classification
                        char_contexts = []
                        for mention in char.mentions[:10]:  # Sample up to 10 mentions
                            start = max(0, mention.position - 200)
                            end = min(len(doc.text), mention.position + 200)
                            char_contexts.append(doc.text[start:end])

                        moral_valence = moral_valence_classifier.classify_character(
                            char.canonical_name,
                            role,
                            char_contexts,
                        )
                        if moral_valence:
                            logger.debug(
                                f"F3: Moral valence for {char.canonical_name}: "
                                f"{moral_valence.valence.value} (confidence={moral_valence.confidence:.2f})"
                            )
                    except Exception as e:
                        logger.warning(f"F3: Moral valence classification failed for {char.canonical_name}: {e}")

                    # Generate profile with enhanced context
                    profile, evidence, confidence, appearance, personality, voice_guidance = self._generate_character_profile(
                        llm, char, doc.text,
                        chapter_map=chapter_map,
                        summary_evidence=summary_evidence,
                        moral_valence=moral_valence,
                    )

                    if profile:
                        char.description = profile
                        profile_count += 1

                        # Store evidence in character
                        char.profile_evidence = evidence
                        char.profile_confidence = confidence

                        # Store structured profile fields (F8: Simplified Character Output)
                        char.appearance = appearance
                        char.personality = personality
                        char.voice_guidance = voice_guidance

                        # Track confidence distribution
                        if confidence >= 0.7:
                            high_conf_count += 1
                        elif confidence >= 0.4:
                            medium_conf_count += 1
                        else:
                            low_conf_count += 1
                            logger.warning(f"Low confidence profile for {char.canonical_name}: {confidence:.2f}")
                    else:
                        char.profile_confidence = None
                        low_conf_count += 1

                    # Update real-time progress
                    self._metrics.update_stage_progress(
                        items_processed=i+1,
                        high=high_conf_count,
                        medium=medium_conf_count,
                        low=low_conf_count
                    )

                # Record metrics with confidence breakdown
                ctx.record_items(
                    total=len(eligible_chars),
                    high_confidence=high_conf_count,
                    medium_confidence=medium_conf_count,
                    low_confidence=low_conf_count
                )

            print(f"   Generated {profile_count} profiles for {len(eligible_chars)} eligible characters")

        # Step 5: Pronunciation Guide (skip if already done in parallel mode)
        if pron_map is None:
            print("🗣️  Generating pronunciation guide...")
            self._write_progress("Pronunciation Guide", self._get_agent_config("pronunciation").model if self._get_agent_config("pronunciation") else None)
            # Use agent-specific LLM client for pronunciation
            pron_llm = self._get_agent_llm_client("pronunciation")
            with self._metrics.stage("Pronunciation Guide") as ctx:
                # Set model info from LLM client config (before running)
                if pron_llm and pron_llm.config:
                    ctx.set_model(pron_llm.config.model, pron_llm.config.provider)

                pronunciation_pipeline = PronunciationGuidePipeline(
                    llm_client=pron_llm,
                    progress_callback=self._wrap_progress("pronunciation"),
                )
                pron_map, _ = pronunciation_pipeline.run(
                    doc.text, chapter_map, pipeline_char_map, source_file=str(file_path)
                )

                # Filter out front/back matter entries
                pron_map = self._filter_pronunciation_by_body(pron_map, doc)

                # Record confidence metrics
                high = sum(1 for p in pron_map.entries if p.confidence >= 0.7)
                medium = sum(1 for p in pron_map.entries if 0.4 <= p.confidence < 0.7)
                low = sum(1 for p in pron_map.entries if p.confidence < 0.4) + len(pron_map.low_confidence_entries)
                ctx.record_items(total=len(pron_map.entries), high_confidence=high, medium_confidence=medium, low_confidence=low)

            print(f"   Flagged {len(pron_map.entries)} words")

        # Step 6: Generate Overview
        print("📊 Generating overview...")
        overview = None
        if llm:
            # Build a partial AnalysisResult for overview generation
            temp_structure = self._convert_chapters(chapter_map, summary_map, self.words_per_minute)
            temp_metadata = BookMetadata(
                title=doc.title,
                author=doc.author,
                source_file=str(file_path),
                source_format=doc.source_format,
                total_word_count=doc.word_count,
                words_per_minute=self.words_per_minute,
            )
            temp_result = AnalysisResult(
                metadata=temp_metadata,
                structure=temp_structure,
            )

            # Generate profiling report for timing
            profiling_report = self._metrics.get_report()

            # Extract model usage from profiling stages
            model_usage = {}
            for stage in profiling_report.stages:
                if stage.model_used:
                    model_usage[stage.stage_name] = {
                        "model": stage.model_used,
                        "provider": stage.provider_used or "unknown",
                    }

            # Generate overview with narrator context
            overview_gen = OverviewGenerator(llm_client=llm)
            overview = overview_gen.generate_overview(
                analysis_result=temp_result,
                profiling_data=profiling_report.to_dict(),
                model_usage=model_usage,
                narrator_name=narrator_detected,
                narrative_style="first-person" if narrator_detected else None,
            )
            print(f"   Overview generated successfully")

        # Step 6.5: Re-run narrator detection with plot_summary (more accurate)
        # The plot_summary often correctly identifies the narrator even when
        # pronoun heuristics fail (e.g., first-person narrators who use "I" not their name)
        print("🎭 Finalizing narrator detection...")
        if overview and overview.get("plot_summary") and llm:
            plot_summary_obj = overview["plot_summary"]
            plot_summary_text = (
                plot_summary_obj.get("plot_summary", "")
                if isinstance(plot_summary_obj, dict)
                else str(plot_summary_obj)
            )

            if plot_summary_text:
                from .pipeline.character_profiling.narrator import NarratorDetector

                narrator_detector = NarratorDetector(llm)
                narrator_info = narrator_detector.detect_narrator(
                    plot_summary=plot_summary_text,
                    characters=pipeline_char_map.characters,
                )

                if narrator_info.narrator_name and narrator_info.confidence >= 0.7:
                    # Mark narrator in character list
                    self._mark_narrator_in_character_map(
                        pipeline_char_map.characters, narrator_info
                    )

                    # Apply narrator role injection for first-person
                    if narrator_info.narrative_style == "first-person":
                        self._apply_narrator_role_injection(
                            pipeline_char_map, narrator_info.narrator_name
                        )

                    # Update narrator_detected for consistency
                    narrator_detected = narrator_info.narrator_name
                    print(f"   Confirmed narrator: {narrator_info.narrator_name} ({narrator_info.narrative_style})")
                else:
                    print(f"   No definitive narrator identified from plot summary")
        else:
            print(f"   Skipped (no plot summary or LLM)")

        # Step 7: Convert to AnalysisResult
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

        # Convert glossary if present
        glossary_map = self._convert_glossary(doc)

        result = AnalysisResult(
            metadata=metadata,
            structure=structure,
            characters=characters,
            pronunciations=pronunciations,
            glossary=glossary_map,
            overview=overview,
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

        # Generate and save quality report (if output_dir is set)
        if self.output_dir:
            self._last_quality_report = generate_quality_report(
                result=result,
                profiling_report=self._last_profiling_report,
                llm_model=self.llm_model or "none",
                llm_provider=self.llm_provider if self.llm_refine else "none",
                duration_seconds=self._last_analysis_duration,
                halted=False,
            )

            # Determine run directory
            # If output_dir looks like a per-run path (ends with _NNN pattern), use it directly
            # Otherwise, create a timestamped subdirectory (backward compat with CLI)
            import re
            if re.search(r'_\d{3}$', self.output_dir.name):
                # GUI-style: output/gatsby_001 - use directly
                run_dir = self.output_dir
            else:
                # CLI-style: output/ - create timestamped subdirectory
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                run_dir = self.output_dir / f"{file_path.stem}_{timestamp}"
            run_dir.mkdir(parents=True, exist_ok=True)

            # Save quality report
            quality_path = run_dir / "quality.md"
            quality_path.write_text(self._last_quality_report.to_markdown(), encoding='utf-8')

            # Copy log files to per-run directory for debugging
            import shutil
            log_dir = Path.home() / '.audiobook-prep'

            # Copy pipeline log if it exists
            pipeline_log = log_dir / 'pipeline.log'
            if pipeline_log.exists():
                shutil.copy(pipeline_log, run_dir / 'pipeline.log')

            # Copy LLM log if it exists
            llm_log = log_dir / 'llm.log'
            if llm_log.exists():
                shutil.copy(llm_log, run_dir / 'llm.log')

            # Store run_dir for save_to_json to use
            self._last_run_dir = run_dir

            print(f"\n📊 Quality report: {quality_path}")
            print(f"📁 Output directory: {run_dir}")

        return result

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable form (e.g., '2m 34s')."""
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        if mins > 0:
            return f"{mins}m {secs}s"
        return f"{secs}s"

    def _write_progress(self, stage: str, model: str = None) -> None:
        """Write a progress file for external monitoring (e.g., oracle-monitor)."""
        output_dir = self.output_dir or Path('output')
        output_dir.mkdir(parents=True, exist_ok=True)
        progress_file = output_dir / "PROGRESS.json"
        try:
            import json
            from datetime import datetime
            progress_data = {
                "stage": stage,
                "model": model,
                "timestamp": datetime.now().isoformat(),
            }
            with open(progress_file, 'w') as f:
                json.dump(progress_data, f)
        except Exception:
            pass  # Non-critical, don't fail analysis if progress write fails

    def _wrap_progress(self, stage: str) -> Callable[[str, int, int], None]:
        """Wrap progress callback with stage prefix and metrics updates."""
        def wrapped(substage: str, current: int, total: int):
            # Update metrics (always, for real-time progress tracking)
            self._metrics.update_stage_progress(items_processed=current)

            # Call external progress callback if configured
            if self.progress_callback:
                self.progress_callback(f"{stage}:{substage}", current, total)

        return wrapped

    def _extract_text_from_malformed_json(self, s: str) -> str:
        """Extract readable text from a malformed JSON string.

        When LLM returns nested JSON or broken formatting, try to salvage
        the actual profile text by stripping JSON artifacts.

        Args:
            s: Raw string that may contain embedded JSON structure

        Returns:
            Cleaned text string, or empty string if unsalvageable
        """
        import re

        # Remove leading JSON structure: {"profile": " or similar
        s = re.sub(r'^\s*\{?\s*"profile"\s*:\s*"?', '', s)

        # Remove trailing JSON: ", "evidence": [...] etc
        s = re.sub(r'"?\s*,?\s*"(evidence|confidence|limitations)"\s*:.*$', '', s, flags=re.DOTALL)

        # Unescape JSON string escapes
        s = s.replace('\\"', '"').replace('\\n', '\n').replace('\\t', ' ')

        # Remove remaining JSON structural characters
        s = re.sub(r'[{}\[\]]', '', s)

        # Clean up whitespace
        s = ' '.join(s.split())

        # Only return if we have substantial text
        return s.strip() if len(s.strip()) > 30 else ""

    def _generate_character_profile(
        self,
        llm: "LLMClient",
        character,
        full_text: str,
        chapter_map: Optional["ChapterMap"] = None,
        summary_evidence: Optional["CharacterSummaryEvidence"] = None,
        moral_valence: Optional["MoralValenceResult"] = None,
    ) -> tuple[str, list[dict], float, Optional[dict], Optional[dict], Optional[dict]]:
        """Generate prose profile for a character using LLM with evidence grounding.

        Args:
            llm: LLM client for generation
            character: Character to profile
            full_text: Full document text
            chapter_map: Chapter boundaries (optional)
            summary_evidence: F2 - Evidence extracted from chapter summaries (optional)
            moral_valence: F3 - Moral valence classification result (optional)

        Returns:
            tuple: (profile_text, evidence_list, confidence_score, appearance, personality, voice_guidance)
                evidence_list: List of dicts with 'statement', 'quote', 'position'
                confidence_score: 0.0-1.0 based on evidence quality
                appearance: Dict with appearance data or None
                personality: Dict with personality data or None
                voice_guidance: Dict with voice guidance data or None
        """
        import json
        import re
        from .pipeline.character_extraction.models import CharacterMention

        # Sample mentions from throughout the book (early, middle, late)
        # to ensure character proof reflects the entire narrative
        all_mentions = getattr(character, "mentions", []) or []
        total_mentions = len(all_mentions)

        # Fallback: if mention objects are unexpectedly missing (but the character exists),
        # rebuild a small set of mention positions via regex so we can still generate a profile.
        #
        # This prevents "No detailed profile available" for major characters when upstream
        # mention tracking is incomplete.
        if total_mentions == 0 and getattr(character, "canonical_name", ""):
            names = [getattr(character, "canonical_name", "")]
            names.extend(getattr(character, "aliases", []) or [])
            names = [n for n in names if isinstance(n, str) and n.strip()]

            positions: set[int] = set()
            for name in names:
                # Allow flexible whitespace for multi-word names (e.g., "De Lacey")
                escaped = re.escape(name).replace(r"\ ", r"\s+")
                pattern = rf"\b{escaped}\b"
                for m in re.finditer(pattern, full_text, flags=re.IGNORECASE):
                    positions.add(m.start())

            pos_list = sorted(positions)

            # Sample up to 10 positions spread across the text
            if len(pos_list) > 10:
                idxs = [int(i * (len(pos_list) - 1) / 9) for i in range(10)]
                pos_list = [pos_list[i] for i in idxs]

            def _chapter_for_pos(pos: int) -> int:
                if chapter_map is None:
                    return 0
                for ch in chapter_map.chapters:
                    if ch.start_position <= pos < ch.end_position:
                        return ch.index
                return 0

            all_mentions = [
                CharacterMention(
                    text=getattr(character, "canonical_name", "") or "",
                    position=pos,
                    chapter_index=_chapter_for_pos(pos),
                    context="",
                    in_dialogue=False,
                )
                for pos in pos_list
            ]
            total_mentions = len(all_mentions)

        # Sample up to 10 mentions, distributed across the narrative
        if total_mentions <= 10:
            sampled_mentions = all_mentions
        else:
            # Divide mentions into thirds (early, middle, late) and sample from each
            third = total_mentions // 3
            early = all_mentions[:third]
            middle = all_mentions[third:2*third]
            late = all_mentions[2*third:]

            # Sample 3-4 from each third
            import random
            sampled_mentions = []
            sampled_mentions.extend(random.sample(early, min(3, len(early))))
            sampled_mentions.extend(random.sample(middle, min(3, len(middle))))
            sampled_mentions.extend(random.sample(late, min(4, len(late))))

            # Sort by position to maintain chronological order in context
            sampled_mentions.sort(key=lambda m: m.position)

        # Gather context snippets from sampled mentions
        contexts = []
        mention_positions = []
        for mention in sampled_mentions:
            start = max(0, mention.position - 200)  # Increased context window
            end = min(len(full_text), mention.position + 200)
            snippet = full_text[start:end].strip()
            # Clean up partial words at boundaries
            if start > 0:
                snippet = "..." + snippet.split(" ", 1)[-1] if " " in snippet else snippet
            if end < len(full_text):
                snippet = snippet.rsplit(" ", 1)[0] + "..." if " " in snippet else snippet
            contexts.append({
                "text": snippet,
                "position": mention.position,
                "chapter": mention.chapter_index
            })
            mention_positions.append(mention.position)

        if not contexts:
            logger.warning(f"No context available for {character.canonical_name}")
            return "", [], 0.0, None, None, None

        context_text = "\n\n".join([
            f"[Context {i+1}, Chapter {c['chapter']}, Position {c['position']}]:\n{c['text']}"
            for i, c in enumerate(contexts)
        ])

        # Check if this character is the narrator
        narrator_note = ""
        if hasattr(character, 'is_narrator') and character.is_narrator:
            narrator_note = f"\n\nNOTE: This character is the NARRATOR of the story ({character.narrative_role or 'First-person narrator'}). Your description should mention their role as the narrator/storyteller."

        # F2: Build summary evidence section if available
        summary_evidence_text = ""
        if summary_evidence and summary_evidence.evidence:
            evidence_lines = []
            for ev in summary_evidence.evidence[:5]:  # Limit to top 5 items
                evidence_lines.append(f"- Chapter {ev.chapter_index}: \"{ev.statement}\"")
            if evidence_lines:
                summary_evidence_text = f"""

ADDITIONAL CONTEXT FROM CHAPTER SUMMARIES (Feature F2):
The following information about this character was extracted from chapter summaries:
{chr(10).join(evidence_lines)}

Use this summary evidence to enrich your profile, but prioritize direct text quotes as primary evidence."""

        # F3: Build moral valence constraint if available
        moral_valence_constraint = ""
        if moral_valence and moral_valence.valence:
            constraint = MORAL_VALENCE_CONSTRAINTS.get(moral_valence.valence, "")
            if constraint:
                moral_valence_constraint = f"""

MORAL VALENCE CONSTRAINT (Feature F3):
This character has been classified as {moral_valence.valence.value} (confidence: {moral_valence.confidence:.0%}).
{constraint}

This is a HARD CONSTRAINT - your profile MUST respect this classification."""

        prompt = f"""Analyze the character "{character.canonical_name}" using ONLY the provided text evidence.

The evidence below is sampled from throughout the entire narrative (early, middle, and late chapters).
Your analysis should reflect the character's full arc, not just their initial appearance.{narrator_note}{summary_evidence_text}{moral_valence_constraint}

Text Evidence:
{context_text}

CRITICAL REQUIREMENTS:
1. Make ONLY claims that are directly supported by the provided text
2. For each claim, provide the exact quote that supports it
3. Consider how the character develops or changes throughout the narrative (if evident from the samples)
4. If the text doesn't provide enough information about a trait or relationship, DO NOT invent it
5. Distinguish between what the text explicitly states vs. what might be inferred

Return a JSON response matching this example format exactly:

```json
{{
  "profile": "A brief 2-3 sentence overview based on provided evidence.",
  "appearance": {{
    "summary": "Brief physical description if available from text",
    "age_indication": "young/middle-aged/elderly/unknown",
    "distinguishing_features": ["feature1", "feature2"]
  }},
  "personality": {{
    "summary": "Brief personality summary",
    "traits": ["trait1", "trait2"],
    "temperament": "calm/volatile/melancholic/cheerful/etc or unknown",
    "emotional_range": "Brief note on emotional expression"
  }},
  "voice_guidance": {{
    "suggested_tone": "authoritative/gentle/aggressive/etc based on dialogue",
    "dialect_notes": "Any accent, regional speech, or class markers",
    "verbal_tics": ["repeated phrase", "speech pattern"],
    "formality_level": "formal/informal/moderate",
    "example_quotes": ["quote1", "quote2"]
  }},
  "evidence": [
    {{"statement": "Character is newly relocated", "quote": "I had just arrived in the city that spring", "position": 1234}},
    {{"statement": "Has family in the area", "quote": "My cousin lived just across the bay", "position": 2456}}
  ],
  "confidence": 0.85,
  "limitations": "What the text doesn't reveal"
}}
```

CRITICAL INSTRUCTIONS:
- You MUST include ALL fields in your response: profile, appearance, personality, voice_guidance, evidence, confidence, limitations
- If information is not available in the text, use "unknown" or empty arrays [] for that field
- Do NOT omit any field - every field must be present even if the value is "unknown" or []
- Do NOT invent details - only use what's explicitly or clearly implied in the provided text
- For appearance: Only include if text mentions physical traits, otherwise use {{"summary": "unknown", "age_indication": "unknown", "distinguishing_features": []}}
- For personality: Only include if you can infer from behavior, otherwise use {{"summary": "unknown", "traits": [], "temperament": "unknown", "emotional_range": "unknown"}}
- For voice_guidance: Base on actual dialogue if present; otherwise use {{"suggested_tone": "unknown", "dialect_notes": "unknown", "verbal_tics": [], "formality_level": "moderate", "example_quotes": []}}
- Return ONLY valid JSON matching the above structure. No other text."""

        # Helper to parse JSON from LLM response
        def _parse_json_blob(s: str):
            try:
                return json.loads(s)
            except json.JSONDecodeError:
                start = s.find("{")
                end = s.rfind("}")
                if start != -1 and end != -1 and end > start:
                    try:
                        return json.loads(s[start:end + 1])
                    except json.JSONDecodeError:
                        return None
                return None

        # Retry loop: try up to 2 times on LLM errors
        max_attempts = 2
        for attempt in range(max_attempts):
            try:
                response = llm.query(prompt, system=CHARACTER_PROFILE_SYSTEM)
                if response.success:
                    # Clean up any thinking tags or extra formatting
                    content = response.content.strip()

                    # Try to extract JSON if wrapped in markdown code blocks
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0].strip()
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0].strip()

                    try:
                        result = _parse_json_blob(content)
                        if result is None:
                            raise json.JSONDecodeError("Could not parse JSON", content, 0)

                        # Check if "profile" field itself contains JSON (double-encoded)
                        profile = result.get("profile", "")
                        if profile and (profile.startswith("{") or profile.startswith("[")):
                            # LLM returned nested JSON - try to parse it
                            logger.warning(
                                f"Character profile for {character.canonical_name} contains nested JSON, attempting to parse"
                            )
                            try:
                                nested = json.loads(profile)
                                if isinstance(nested, dict) and "profile" in nested:
                                    # Double-encoded JSON
                                    profile = nested["profile"]
                                    logger.info(f"Successfully extracted profile from nested JSON for {character.canonical_name}")
                            except json.JSONDecodeError:
                                # Not valid JSON - try to extract readable text
                                logger.warning(f"Nested JSON parse failed for {character.canonical_name}, extracting text")
                                profile = self._extract_text_from_malformed_json(profile)
                                if not profile:
                                    logger.warning(f"Could not salvage text from malformed profile for {character.canonical_name}")

                        evidence = result.get("evidence", [])
                        confidence = float(result.get("confidence", 0.5))

                        # Extract structured fields (F8: Simplified Character Output)
                        appearance = result.get("appearance")
                        personality = result.get("personality")
                        voice_guidance = result.get("voice_guidance")

                        # Debug logging
                        logger.info(
                            f"Profile generation for {character.canonical_name}: "
                            f"keys={list(result.keys())}, "
                            f"appearance={'present' if appearance else 'missing'}, "
                            f"personality={'present' if personality else 'missing'}, "
                            f"voice_guidance={'present' if voice_guidance else 'missing'}"
                        )

                        # DETAILED DEBUG: Log the actual structured field contents
                        if appearance:
                            logger.info(f"  appearance content: {json.dumps(appearance)}")
                        if personality:
                            logger.info(f"  personality content: {json.dumps(personality)}")
                        if voice_guidance:
                            logger.info(f"  voice_guidance content: {json.dumps(voice_guidance)}")

                        # Preserve structured fields even if they contain "unknown" values
                        def _clean_dict(d):
                            if not isinstance(d, dict):
                                return None
                            # Return the dict as-is if it has any content
                            # We keep "unknown" values because they indicate the LLM responded
                            # but found no evidence in the text (which is valid information)
                            return d if d else None

                        appearance = _clean_dict(appearance)
                        personality = _clean_dict(personality)
                        voice_guidance = _clean_dict(voice_guidance)

                        # DEBUG: Log after cleaning
                        logger.info(
                            f"After _clean_dict for {character.canonical_name}: "
                            f"appearance={'present' if appearance else 'NULL'}, "
                            f"personality={'present' if personality else 'NULL'}, "
                            f"voice_guidance={'present' if voice_guidance else 'NULL'}"
                        )

                        # Fallback: If LLM didn't provide structured fields, attempt to structure the profile text
                        if not appearance and not personality and not voice_guidance and profile:
                            logger.warning(
                                f"Structured fields missing for {character.canonical_name}, "
                                f"attempting to structure profile text via secondary LLM call"
                            )
                            # Use LLM to structure the existing profile text
                            structuring_prompt = f"""The following character profile needs to be organized into structured fields.
Extract information into the specified categories. Only use information explicitly present in the profile.

Profile text:
{profile}

Return a JSON object with these fields:
{{
  "appearance": {{"summary": "Physical description if mentioned", "age_indication": "age if mentioned", "distinguishing_features": []}},
  "personality": {{"summary": "Personality traits and behavior", "traits": ["trait1", "trait2"], "temperament": "overall temperament"}},
  "voice_guidance": {{"suggested_tone": "tone based on character's manner", "formality_level": "formal/informal/moderate"}}
}}

If a category has no information in the profile, use "unknown" or [] for that field.
Return ONLY the JSON object."""

                            try:
                                struct_response = llm.query(structuring_prompt, system="You are a helpful assistant that structures character information.")
                                if struct_response.success:
                                    struct_content = struct_response.content.strip()
                                    if "```json" in struct_content:
                                        struct_content = struct_content.split("```json")[1].split("```")[0].strip()
                                    elif "```" in struct_content:
                                        struct_content = struct_content.split("```")[1].split("```")[0].strip()

                                    struct_result = json.loads(struct_content)
                                    appearance = _clean_dict(struct_result.get("appearance"))
                                    personality = _clean_dict(struct_result.get("personality"))
                                    voice_guidance = _clean_dict(struct_result.get("voice_guidance"))
                                    logger.warning(f"Successfully structured profile for {character.canonical_name}")
                            except Exception as e:
                                logger.warning(f"Failed to structure profile for {character.canonical_name}: {e}")

                        # Validate evidence structure
                        validated_evidence = []
                        for ev in evidence:
                            if isinstance(ev, dict) and "statement" in ev and "quote" in ev:
                                validated_evidence.append({
                                    "statement": ev["statement"],
                                    "quote": ev["quote"],
                                    "position": ev.get("position", 0),
                                    "confidence": "high" if confidence >= 0.7 else "medium" if confidence >= 0.4 else "low"
                                })

                        # If no valid evidence but we got a profile, mark as low confidence
                        if profile and not validated_evidence:
                            logger.warning(f"Profile for {character.canonical_name} lacks evidence")
                            confidence = min(confidence, 0.3)

                        return profile, validated_evidence, confidence, appearance, personality, voice_guidance

                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON response for {character.canonical_name}: {e}")
                        logger.debug(f"Raw content (first 500 chars): {content[:500]}")
                        # Try to extract readable text from malformed response
                        salvaged = self._extract_text_from_malformed_json(content)
                        if salvaged:
                            logger.info(f"Salvaged profile text for {character.canonical_name}")
                            return salvaged, [], 0.3, None, None, None
                        return "", [], 0.0, None, None, None
                else:
                    # LLM returned error response
                    error_msg = getattr(response, 'error', None) or 'unknown error'
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"LLM error for '{character.canonical_name}' (attempt {attempt + 1}/{max_attempts}): "
                            f"{error_msg}, retrying..."
                        )
                        continue  # Retry
                    else:
                        logger.error(
                            f"Profile generation failed for '{character.canonical_name}' after {max_attempts} attempts: "
                            f"{error_msg}"
                        )
                        return "", [], 0.0, None, None, None

            except Exception as e:
                if attempt < max_attempts - 1:
                    logger.warning(
                        f"Exception generating profile for '{character.canonical_name}' (attempt {attempt + 1}/{max_attempts}): "
                        f"{e}, retrying..."
                    )
                    continue  # Retry
                else:
                    logger.error(
                        f"Profile generation failed for '{character.canonical_name}' after {max_attempts} attempts: {e}"
                    )

        return "", [], 0.0, None, None, None

    def _detect_narrator(self, full_text: str, characters: list) -> Optional[str]:
        """
        Detect if this is a first-person narrative and identify the narrator.

        Uses per-character pronoun density scoring to identify which character
        is actually speaking in first person, not just mention count.

        Returns:
            Name of narrator character if detected, None otherwise
        """
        # Sample text from beginning (first 5000 chars)
        sample_text = full_text[:5000]

        # Count first-person pronouns in opening
        first_person_count = 0
        pronouns = ["I ", " I ", "I'm", "I've", "my ", " my ", "me ", " me "]
        for pronoun in pronouns:
            first_person_count += sample_text.count(pronoun)

        # If high first-person usage, this is likely a first-person narrative
        if first_person_count > 15:  # Threshold for first-person narrative
            logger.info(f"First-person narrative detected ({first_person_count} pronouns in opening)")

            # NEW: Calculate per-character first-person pronoun scores
            # Check which character's contexts contain first-person pronouns
            character_scores = []

            for char in characters:
                if not hasattr(char, 'mentions') or not char.mentions:
                    continue

                # Sample up to 10 mentions per character
                sampled_mentions = char.mentions[:10]

                # Count first-person pronouns in context around each mention
                pronoun_count = 0
                total_context_length = 0

                for mention in sampled_mentions:
                    # Get context window around mention (±200 chars)
                    start = max(0, mention.position - 200)
                    end = min(len(full_text), mention.position + 200)
                    context = full_text[start:end]

                    # Count pronouns in this context
                    for pronoun in pronouns:
                        pronoun_count += context.count(pronoun)

                    total_context_length += len(context)

                # Calculate pronoun density (pronouns per 1000 chars)
                if total_context_length > 0:
                    density = (pronoun_count / total_context_length) * 1000
                else:
                    density = 0.0

                character_scores.append({
                    'character': char,
                    'pronoun_count': pronoun_count,
                    'density': density,
                    'mention_count': char.mention_count
                })

                logger.debug(
                    f"Narrator scoring: {char.canonical_name} - "
                    f"{pronoun_count} pronouns in contexts, density={density:.2f}, "
                    f"mentions={char.mention_count}"
                )

            # Sort by pronoun density (primary) and mention count (tiebreaker)
            character_scores.sort(key=lambda x: (x['density'], x['mention_count']), reverse=True)

            if character_scores and character_scores[0]['density'] > 5.0:
                # Narrator should have significant first-person pronoun usage in their contexts
                narrator = character_scores[0]['character']
                narrator.is_narrator = True
                narrator.narrative_role = "First-person narrator"

                logger.info(
                    f"Detected first-person narrator: {narrator.canonical_name} "
                    f"(density={character_scores[0]['density']:.2f}, {narrator.mention_count} mentions)"
                )
                return narrator.canonical_name
            else:
                logger.warning(
                    f"First-person narrative detected but no character has strong pronoun association. "
                    f"Top character: {character_scores[0]['character'].canonical_name if character_scores else 'none'}"
                )

        return None

    def _mark_narrator_in_character_map(
        self,
        characters: list,
        narrator_info,
    ) -> None:
        """
        Mark the narrator character in the character list.

        Similar to NarratorDetector.mark_narrator_in_characters but works with
        Character objects from character_extraction (not IdentifiedCharacter).

        Args:
            characters: List of Character objects (modified in-place)
            narrator_info: NarratorInfo with detected narrator details
        """
        if not narrator_info.narrator_name:
            return

        narrator_lower = narrator_info.narrator_name.lower()

        for char in characters:
            # Check canonical name
            if char.canonical_name.lower() == narrator_lower:
                char.is_narrator = True
                char.narrative_role = narrator_info.narrator_role

                # Elevate role - first-person narrators should not be supporting/minor
                if char.role in ("supporting", "minor"):
                    old_role = char.role
                    if narrator_info.narrative_style == "first-person":
                        char.role = "protagonist"
                        logger.info(
                            f"Elevated first-person narrator {char.canonical_name} "
                            f"from '{old_role}' to 'protagonist'"
                        )

                logger.info(f"Marked {char.canonical_name} as narrator")
                return

            # Check aliases
            for alias in char.aliases:
                if alias.lower() == narrator_lower:
                    char.is_narrator = True
                    char.narrative_role = narrator_info.narrator_role

                    # Elevate role
                    if char.role in ("supporting", "minor"):
                        old_role = char.role
                        if narrator_info.narrative_style == "first-person":
                            char.role = "protagonist"
                            logger.info(
                                f"Elevated first-person narrator {char.canonical_name} "
                                f"from '{old_role}' to 'protagonist'"
                            )

                    logger.info(f"Marked {char.canonical_name} as narrator (matched alias: {alias})")
                    return

        logger.warning(
            f"Narrator '{narrator_info.narrator_name}' not found in character list"
        )

    def _apply_narrator_role_injection(
        self,
        char_map,
        narrator_name: str,
    ) -> None:
        """
        Boost narrator importance for first-person narratives.

        First-person narrators have low explicit mention counts because they
        use "I" instead of their name. This ensures the narrator is treated
        as a main character by setting their effective_mention_count to match
        the most-mentioned character.

        Args:
            char_map: CharacterMap containing characters
            narrator_name: Name of the narrator to boost
        """
        # Find max mention count among all characters
        max_mentions = max(
            (getattr(c, 'mention_count', 0) for c in char_map.characters),
            default=10
        )

        # Find narrator and boost their effective importance
        for char in char_map.characters:
            if char.canonical_name.lower() == narrator_name.lower():
                # Store original for reference
                original_mentions = getattr(char, 'mention_count', 0)

                # Set effective mention count to match most-mentioned character
                char.effective_mention_count = max(max_mentions, original_mentions)

                # Ensure role is protagonist (already done in mark_narrator_in_characters,
                # but double-check here)
                if hasattr(char, 'role') and char.role in ("supporting", "minor", None):
                    char.role = "protagonist"

                logger.info(
                    f"Narrator role injection: {char.canonical_name} - "
                    f"mentions {original_mentions} → effective {char.effective_mention_count}, "
                    f"role={char.role}"
                )
                return

        # Also check aliases
        for char in char_map.characters:
            for alias in char.aliases:
                if alias.lower() == narrator_name.lower():
                    original_mentions = getattr(char, 'mention_count', 0)
                    char.effective_mention_count = max(max_mentions, original_mentions)

                    if hasattr(char, 'role') and char.role in ("supporting", "minor", None):
                        char.role = "protagonist"

                    logger.info(
                        f"Narrator role injection: {char.canonical_name} (via alias {alias}) - "
                        f"mentions {original_mentions} → effective {char.effective_mention_count}, "
                        f"role={char.role}"
                    )
                    return

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
            # Map confidence - use profile confidence if available
            profile_conf = getattr(pc, 'profile_confidence', None)
            if profile_conf is not None:
                # Use profile confidence if it exists
                if profile_conf >= 0.7:
                    confidence = ConfidenceLevel.HIGH
                elif profile_conf >= 0.4:
                    confidence = ConfidenceLevel.MEDIUM
                else:
                    confidence = ConfidenceLevel.LOW
            else:
                # Fall back to extraction confidence
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

            # Extract evidence from pipeline character
            evidence = getattr(pc, 'profile_evidence', [])

            characters.append(Character(
                id=pc.id,
                canonical_name=pc.canonical_name,
                aliases=pc.aliases,
                descriptions=descriptions,
                first_appearance_chapter=pc.first_appearance_chapter,
                mention_count=pc.mention_count,
                confidence=confidence,
                evidence=evidence,
                is_narrator=getattr(pc, 'is_narrator', False),
                narrative_role=getattr(pc, 'narrative_role', None),
                appearance=getattr(pc, 'appearance', None),
                personality=getattr(pc, 'personality', None),
                voice_guidance=getattr(pc, 'voice_guidance', None),
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

    def _convert_glossary(
        self,
        doc: ExtractedDocument,
    ) -> Optional[GlossaryMap]:
        """Convert ingestion glossary to GlossaryMap model."""
        if not doc.glossary:
            return None

        entries = []
        for ge in doc.glossary.entries:
            # Map confidence
            if ge.confidence >= 0.8:
                confidence = ConfidenceLevel.HIGH
            elif ge.confidence >= 0.5:
                confidence = ConfidenceLevel.MEDIUM
            else:
                confidence = ConfidenceLevel.LOW

            entries.append(ModelGlossaryEntry(
                term=ge.term,
                definition=ge.definition,
                position=ge.position,
                confidence=confidence,
            ))

        return GlossaryMap(
            entries=entries,
            source_region_start=doc.glossary.region_start,
            source_region_end=doc.glossary.region_end,
        )

    def save_to_json(
        self,
        result: AnalysisResult,
        output_path: str | Path,
    ) -> str:
        """
        Save an analysis result to JSON.

        Args:
            result: AnalysisResult to save
            output_path: Path for output JSON file

        Returns:
            Path to output JSON file
        """
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

    def analyze_to_json(
        self,
        file_path: str | Path,
        output_path: Optional[str | Path] = None,
    ) -> str:
        """
        Analyze a book and save results as JSON.

        Args:
            file_path: Path to book file
            output_path: Optional output path (defaults to per-run dir or same name)

        Returns:
            Path to output JSON file
        """
        result = self.analyze(file_path)

        if output_path is None:
            # Use per-run directory if available
            if self._last_run_dir:
                output_path = self._last_run_dir / "analysis.json"
            else:
                file_path = Path(file_path)
                output_path = file_path.with_suffix('.analysis.json')

        return self.save_to_json(result, output_path)


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
