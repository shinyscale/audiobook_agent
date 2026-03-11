"""
Main analyzer orchestrator.
Coordinates ingestion and analysis pipeline.
"""

import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, Tuple

# Agent imports
from .agents import (
    AgentConfig,
    AgentContext,
    CharacterAgent,
    OrchestratorConfig,
    StructureAgent,
    SummaryAgent,
)
from .agents.validation import (
    PipelineHaltReport,
    get_recommendations_for_issue,
)
from .export.quality_report import QualityReport, generate_quality_report
from .ingestion import ExtractedDocument, get_ingester
from .ingestion.refine import refine_extracted_document, to_canonical_markdown
from .ingestion.regions import RegionType
from .models import (
    AnalysisResult,
    BookMetadata,
    CharacterDescription,
    ConfidenceLevel,
    GlossaryMap,
    PronunciationEntry,
    StructuralElement,
    StructureType,
)
from .models import (
    Character as OutputCharacter,
)
from .models import (
    GlossaryEntry as ModelGlossaryEntry,
)
from .models import (
    PronunciationFlag as ModelPronunciationFlag,
)

# Import new pipeline
from .pipeline import (
    ChapterMap,
)
from .pipeline.chapter_summary import (
    ChapterSummaryMap,
    ChapterSummaryPipeline,
)
from .pipeline.character_extraction import (
    CharacterMap as PipelineCharacterMap,
)
from .utils.debug_log import append_debug_event
from .pipeline.character_extraction.models import (
    Character,
    CharacterType,
)

# Character profiling pipeline components (F1-F5)
from .pipeline.character_profiling import (
    MORAL_VALENCE_CONSTRAINTS,
    CharacterSummaryEvidence,
    # F3: Moral valence classification
    MoralValenceClassifier,
    MoralValenceResult,
    # F2: Summary evidence extraction
    SummaryEvidenceExtractor,
    # F1: Summary-driven character merge detection
    SummaryMerger,
    SummaryMergeResult,
    # F5: Tag identity propagation
    TagIdentityExtractor,
    apply_summary_merges,
)
from .pipeline.llm import LLMClient, LLMConfig
from .pipeline.metrics import MetricsCollector, ProfilingReport
from .pipeline.overview import OverviewGenerator
from .pipeline.pronunciation_guide import (
    PronunciationFlag as PipelinePronunciationFlag,
)
from .pipeline.pronunciation_guide import (
    PronunciationGuidePipeline,
    PronunciationMap,
)

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
        # Set output dir for heartbeat file (used by oracle-monitor)
        if self.output_dir:
            self._metrics.set_output_dir(str(self.output_dir))
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
            # Determine default model: prioritize llm_model, then orchestrator_config.default_model, then provider default
            default_model = self.llm_model or (
                self.orchestrator_config.default_model if self.orchestrator_config else None
            )
            if self.llm_provider == "ollama":
                config = LLMConfig.ollama(
                    model=default_model or "llama3.2",
                    base_url=self.llm_base_url,
                )
            elif self.llm_provider == "openai":
                config = LLMConfig.openai(
                    model=default_model or "gpt-4o-mini",
                    api_key=self.llm_api_key,
                )
            elif self.llm_provider == "anthropic":
                config = LLMConfig.anthropic(
                    model=default_model or "claude-3-5-sonnet-20241022",
                    api_key=self.llm_api_key,
                )
            elif self.llm_provider == "lm_studio":
                # LM Studio uses OpenAI-compatible API
                config = LLMConfig(
                    provider="openai",
                    model=default_model or "local-model",
                    base_url=self.llm_base_url,
                    api_key="not-needed",
                )
            else:
                logger.warning(f"Unknown LLM provider: {self.llm_provider}")
                return None

            # Disable thinking mode by default (thinking models like qwen3.5 return empty
            # content when think=None; agents override this as needed via their own configs)
            config.think = False
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
                    config.max_tokens = agent_config.max_tokens
                    config.think = agent_config.think_mode
                    config.context_length = (
                        agent_config.context_length or self.orchestrator_config.context_length
                    )

                    # Sampling parameters (Qwen3 recommended: top_p=0.8, top_k=20)
                    if agent_config.top_p is not None:
                        config.top_p = agent_config.top_p
                    if agent_config.top_k is not None:
                        config.top_k = agent_config.top_k
                    if agent_config.presence_penalty is not None:
                        config.presence_penalty = agent_config.presence_penalty

                    client = LLMClient(config, metrics=self._metrics)
                    self._agent_llm_clients[agent_name] = client
                    logger.info(
                        f"Created agent-specific LLM client for {agent_name}: {agent_config.model}"
                    )
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
            max_tokens = agent_config.max_tokens
            think_mode = agent_config.think_mode
            context_length = agent_config.context_length or self.orchestrator_config.context_length
            # Sampling parameters (Qwen3 recommended: top_p=0.8, top_k=20)
            top_p = agent_config.top_p
            top_k = agent_config.top_k
            presence_penalty = agent_config.presence_penalty
        else:
            provider = self.llm_provider
            base_url = self.llm_base_url
            model = self.llm_model
            temperature = 0.7  # Model-recommended default
            max_tokens = 8192  # Default for agents when no config
            think_mode = False
            context_length = self.llm_context_length
            top_p = None
            top_k = None
            presence_penalty = None

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
            config.max_tokens = max_tokens
            config.think = think_mode
            config.context_length = context_length

            # Sampling parameters (Qwen3 recommended: top_p=0.8, top_k=20)
            if top_p is not None:
                config.top_p = top_p
            if top_k is not None:
                config.top_k = top_k
            if presence_penalty is not None:
                config.presence_penalty = presence_penalty

            return LLMClient(config, metrics=self._metrics)
        except Exception as e:
            logger.warning(f"Failed to create LLM client for {agent_name}: {e}")
            return None

    def _are_quality_gates_enabled(self) -> bool:
        """Check if quality gates are enabled in orchestrator config."""
        return (
            self.orchestrator_config is not None and self.orchestrator_config.enable_quality_gates
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
            halted_reason=(
                validation.issues[0].description if validation.issues else "Validation failed"
            ),
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
        report_path.write_text(halt_report.to_markdown(), encoding="utf-8")

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
                low_confidence.append(
                    f"Structure: {elem.type.value} at position {elem.start_position}"
                )
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

                    # Use V2 character agent (V1 has been removed)
                    competitive_config = (
                        self.orchestrator_config.competitive if self.orchestrator_config else None
                    )
                    character_agent = CharacterAgent(
                        llm_client=char_llm,
                        config=char_config,
                        competitive_config=competitive_config,
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
                    self._get_agent_config("pronunciation")

                    # Set model info from LLM client config (before running pipeline)
                    if pron_llm and pron_llm.config:
                        ctx.set_model(pron_llm.config.model, pron_llm.config.provider)

                    pronunciation_pipeline = PronunciationGuidePipeline(
                        llm_client=pron_llm,
                        progress_callback=self._wrap_progress("Pronunciation Guide"),
                    )
                    pron_map, _ = pronunciation_pipeline.run(
                        doc.text, chapter_map, None, source_file=str(file_path)
                    )

                    # Record confidence metrics
                    high = sum(1 for p in pron_map.entries if p.confidence >= 0.7)
                    medium = sum(1 for p in pron_map.entries if 0.4 <= p.confidence < 0.7)
                    low = sum(1 for p in pron_map.entries if p.confidence < 0.4) + len(
                        pron_map.low_confidence_entries
                    )
                    ctx.record_items(
                        total=len(pron_map.entries),
                        high_confidence=high,
                        medium_confidence=medium,
                        low_confidence=low,
                    )

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

        # Reset consensus collector for this analysis
        from .pipeline.consensus_collector import consensus_collector
        consensus_collector.reset()
        if self.orchestrator_config and self.orchestrator_config.competitive:
            cc = self.orchestrator_config.competitive
            consensus_collector.configure(
                enabled=cc.enabled,
                mode="multi" if cc.competitor_models else ("single" if cc.enabled else "none"),
                models=[m.model.split(":")[0] for m in (cc.competitor_models or [])],
                stages=[
                    s for s, enabled in [
                        ("characters", cc.competitive_consensus),
                        ("structure", cc.competitive_structure),
                        ("summaries", cc.competitive_summaries),
                    ] if enabled
                ],
            )

        # Clear debug logs for this run (avoid cumulative logs across runs)
        log_dir = Path.home() / ".audiobook-prep"
        llm_log = log_dir / "llm.log"
        pipeline_log = log_dir / "pipeline.log"
        if llm_log.exists():
            llm_log.unlink()  # Delete the file, logger will recreate it on first write
        if pipeline_log.exists():
            pipeline_log.unlink()  # Delete the file, logger will recreate it on first write

        # Step 1: Ingest document
        print(f"📖 Ingesting: {file_path.name}")
        ingester = get_ingester(file_path, ocr_fallback=self.ocr_fallback)
        doc = ingester.extract(file_path)

        print(f"   Extracted {doc.word_count:,} words")

        # region agent log (chapter-v-bug) - hypothesis A/C
        try:
            import re as _re

            append_debug_event(
                {
                    "sessionId": "debug-session",
                    "runId": "chapter-v-bug-pre",
                    "hypothesisId": "C",
                    "location": "src/analyzer.py:analyze:post_ingest",
                    "message": "Doc text marker presence right after ingestion",
                    "data": {
                        "source_format": getattr(doc, "source_format", None),
                        "text_len": len(doc.text),
                        "centered_V_lines": len(_re.findall(r"(?m)^[ \t]{10,}V[ \t]*$", doc.text)),
                        "standalone_V_lines": len(_re.findall(r"(?m)^[ \t]*V[ \t]*$", doc.text)),
                        "centered_I_lines": len(_re.findall(r"(?m)^[ \t]{10,}I[ \t]*$", doc.text)),
                        "standalone_I_lines": len(_re.findall(r"(?m)^[ \t]*I[ \t]*$", doc.text)),
                    },
                    "timestamp": int(time.time() * 1000),
                }
            )
        except Exception:
            pass
        # endregion

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
            output_dir = self.output_dir or Path("output")
            output_dir.mkdir(exist_ok=True)
            md_path = output_dir / f"{file_path.stem}.canonical.md"
            canonical_md = to_canonical_markdown(doc)
            md_path.write_text(canonical_md, encoding="utf-8")
            print(f"   📝 Wrote canonical markdown: {md_path}")

        # Get default LLM client (for pipelines that don't have agents yet)
        llm = self._get_llm_client()

        # Step 2: Chapter Detection (using StructureAgent)
        print("📑 Detecting chapters...")
        self._write_progress(
            "Chapter Detection",
            (
                self._get_agent_config("structure").model
                if self._get_agent_config("structure")
                else None
            ),
        )
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
                competitive_config=(
                    self.orchestrator_config.competitive
                    if self.orchestrator_config and self.orchestrator_config.competitive
                    else None
                ),
            )
            agent_context = AgentContext(
                text=doc.text,
                source_file=str(file_path),
            )

            # region agent log (chapter-v-bug) - hypothesis A/C
            try:
                import re as _re

                append_debug_event(
                    {
                        "sessionId": "debug-session",
                        "runId": "chapter-v-bug-pre",
                        "hypothesisId": "C",
                        "location": "src/analyzer.py:analyze:pre_structure_agent",
                        "message": "Text marker presence passed into StructureAgent",
                        "data": {
                            "text_len": len(agent_context.text),
                            "centered_V_lines": len(
                                _re.findall(r"(?m)^[ \t]{10,}V[ \t]*$", agent_context.text)
                            ),
                            "standalone_V_lines": len(
                                _re.findall(r"(?m)^[ \t]*V[ \t]*$", agent_context.text)
                            ),
                            "centered_I_lines": len(
                                _re.findall(r"(?m)^[ \t]{10,}I[ \t]*$", agent_context.text)
                            ),
                            "standalone_I_lines": len(
                                _re.findall(r"(?m)^[ \t]*I[ \t]*$", agent_context.text)
                            ),
                        },
                        "timestamp": int(time.time() * 1000),
                    }
                )
            except Exception:
                pass
            # endregion

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
        # NOTE: Parallel character+pronunciation is currently DISABLED because V2 character extraction
        # requires summaries to be generated first. The parallel path needs to be redesigned.
        use_parallel = False  # Force disable until parallel path is fixed for V2
        # use_parallel = (
        #     self.orchestrator_config
        #     and self.orchestrator_config.parallel_execution
        # )

        if use_parallel:
            # Step 3+5 PARALLEL: Run CharacterAgent and PronunciationAgent in parallel
            # TODO: Fix this path to work with V2 (needs summaries first)
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
            # Step 3 SEQUENTIAL: Character Extraction (deferred)
            # V2 requires summaries first, so we defer character extraction until after Step 4
            pipeline_char_map = None
            print("👥 Character extraction: will run after summaries...")

            # pron_map will be set in Step 5 below (sequential mode)
            pron_map = None

        # Step 3.5: Detect Narrator (before profile generation)
        # DISABLED: The pronoun density heuristic is unreliable - it counts first-person
        # pronouns AROUND character mentions, not who is SPEAKING them. This causes
        # false positives (e.g., "I looked at Berenice" makes Berenice look like narrator).
        # Instead, rely on summary-based narrator detection in Step 6.5, which is more accurate.
        narrator_detected = None

        # NOTE: Character profiles are now generated AFTER summaries (Step 4.5)
        # This allows us to use summary-derived features (F1, F2, F3, F5)

        # Step 4: Chapter Summaries
        print("📝 Generating chapter summaries...")
        self._write_progress(
            "Chapter Summaries",
            (
                self._get_agent_config("summaries").model
                if self._get_agent_config("summaries")
                else None
            ),
        )

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
                    self.orchestrator_config.max_parallel_workers if self.orchestrator_config else 4
                )

                # Factory to create fresh LLM clients for parallel execution
                def summary_llm_factory():
                    return self._create_llm_client_for_agent("summaries")

                summary_pipeline = ChapterSummaryPipeline(
                    llm_client=summary_llm,
                    progress_callback=self._wrap_progress("Chapter Summaries"),
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
                    competitive_config=(
                        self.orchestrator_config.competitive
                        if self.orchestrator_config and self.orchestrator_config.competitive
                        else None
                    ),
                )
                summary_map, _ = summary_pipeline.run(
                    doc.text, chapter_map, pipeline_char_map, source_file=str(file_path)
                )

                # Record metrics - summaries don't have confidence scores, so count all as high
                ctx.record_items(
                    total=len(summary_map.summaries),
                    high_confidence=len(summary_map.summaries),
                    medium_confidence=0,
                    low_confidence=0,
                )

            print(f"   Generated {len(summary_map.summaries)} summaries")
        else:
            summary_map = None
            print("   ⚠️  Skipped (no LLM)")

        # Step 4.1: Character Extraction (summary-driven)
        # Uses summaries as the source of truth for main cast extraction
        if pipeline_char_map is None:
            if summary_map and len(summary_map.summaries) > 0:
                print("👥 Extracting characters (summary-driven)...")
                self._write_progress(
                    "Character Extraction",
                    (
                        self._get_agent_config("characters").model
                        if self._get_agent_config("characters")
                        else None
                    ),
                )
                with self._metrics.stage("Character Extraction") as ctx:
                    char_llm = self._get_agent_llm_client("characters")
                    char_config = self._get_agent_config("characters")

                    if char_llm and char_llm.config:
                        ctx.set_model(char_llm.config.model, char_llm.config.provider)

                    # Create V2 agent
                    competitive_config = (
                        self.orchestrator_config.competitive if self.orchestrator_config else None
                    )
                    character_agent_v2 = CharacterAgent(
                        llm_client=char_llm,
                        config=char_config,
                        competitive_config=competitive_config,
                    )

                    # Build context with summaries
                    # Store summaries result so v2 agent can access it
                    char_agent_context = AgentContext(
                        text=doc.text,
                        source_file=str(file_path),
                        chapter_map=chapter_map,
                        previous_results={"summaries": summary_map},
                    )

                    # Run V2 agent
                    character_result = character_agent_v2.run(char_agent_context)
                    pipeline_char_map = character_result.data

                    # Extract narrator info from V2 pipeline result.
                    # characters.py Step 4/5.8 already ran narrator detection with the
                    # fully-resolved main_cast — use this result directly rather than
                    # waiting for the duplicate early detection (Step 4.5) later.
                    _v2_narrator_name = pipeline_char_map.pipeline_metadata.get("narrator_name")
                    _v2_narrator_pov = pipeline_char_map.pipeline_metadata.get("narrator_pov", "")
                    if _v2_narrator_name and _v2_narrator_pov in ("first-person", "epistolary"):
                        narrator_detected = _v2_narrator_name
                        logger.info(
                            f"V2 narrator extracted from pipeline result: "
                            f"'{narrator_detected}' (pov={_v2_narrator_pov})"
                        )
                        print(f"   Narrator (from V2 pipeline): {narrator_detected}")

                    ctx.record_items(
                        total=character_result.total_items,
                        high_confidence=character_result.high_confidence_count,
                        medium_confidence=character_result.medium_confidence_count,
                        low_confidence=character_result.low_confidence_count,
                    )

                    if character_result.issues:
                        for issue in character_result.issues:
                            logger.info(f"Character extraction issue: {issue}")

                print(f"   Found {len(pipeline_char_map.characters)} characters")
            else:
                # No summaries available - fall back to empty character map
                print("   ⚠️  Character extraction skipped (no summaries)")
                pipeline_char_map = PipelineCharacterMap(characters=[], source_file=str(file_path))

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
                combined_summary = "\n\n".join(
                    [f"Chapter {s.chapter_index}: {s.summary}" for s in summary_map.summaries]
                )
                merge_result = summary_merger.find_identity_statements(
                    combined_summary, use_llm=True
                )

                if merge_result.merge_pairs:
                    logger.info(
                        f"F1: Found {len(merge_result.merge_pairs)} identity statements from summaries"
                    )
                    for stmt in merge_result.statements:
                        logger.info(
                            f"  - '{stmt.name_a}' = '{stmt.name_b}' (pattern: {stmt.pattern_matched})"
                        )

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
                        logger.info(
                            f"  - '{match.name1}/{match.name2}' in chapter {match.chapter_index}"
                        )

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

        # F6: Reconcile characters from chapter summaries (moved outside llm check)
        # This must run whenever summaries exist, regardless of whether there's a default LLM client
        # Add any characters from summary.active_characters that are missing from the character list
        # This addresses the issue where self-referential narrators (e.g., "My name is X") are missed by NER
        # but correctly identified in chapter summaries
        #
        # IMPORTANT: We ONLY use active_characters (characters who appear "on stage"), NOT mentioned_characters.
        # mentioned_characters are people referenced but not present (historical figures, guest lists, etc.)
        # Adding mentioned_characters would cause character count explosion (e.g., party guests in Gatsby Ch.4)
        if summary_map:
            print("🔍 Reconciling characters from chapter summaries...")
            try:
                # Collect all unique character names from chapter summaries
                # Use active_characters (new format) with fallback to characters_present (old format via property)
                summary_character_names = set()
                for summary in summary_map.summaries:
                    # active_characters = characters who appear and act in the chapter
                    # The property characters_present returns active_characters for backward compatibility
                    active_chars = (
                        getattr(summary, "active_characters", None)
                        or summary.characters_present
                        or []
                    )
                    for name in active_chars:
                        # Normalize name (strip whitespace, handle case)
                        normalized_name = name.strip()
                        if normalized_name:
                            summary_character_names.add(normalized_name)

                def _normalize_name_for_matching(name: str) -> str:
                    """Normalize name for existence checking - strip articles, titles, and initials."""
                    normalized = name.strip().lower()

                    # Strip leading articles (the, a, an)
                    # This prevents false duplicates like "masked figure" vs "the masked figure"
                    for article in ["the ", "a ", "an "]:
                        if normalized.startswith(article):
                            normalized = normalized[len(article):].strip()
                            break  # Only strip one article

                    # Strip common titles/honorifics
                    TITLES = [
                        "professor",
                        "prof.",
                        "dr.",
                        "mr.",
                        "mrs.",
                        "ms.",
                        "miss",
                        "sir",
                        "lady",
                        "lord",
                    ]
                    for title in TITLES:
                        # Handle "Professor X" or "Professor X Y"
                        if normalized.startswith(title + " "):
                            normalized = normalized[len(title) :].strip()
                        # Handle "X, Professor" or "X, Dr."
                        if normalized.endswith(", " + title):
                            normalized = normalized[: -(len(title) + 2)].strip()

                    # Strip LEADING first-name initials only (e.g., "m. waldman" → "waldman").
                    # This handles "M. Waldman" vs "Professor Waldman" without falsely
                    # collapsing middle initials: "George B. Wilson" must NOT normalize to
                    # "george wilson" (they are different names — one has a middle initial).
                    # Only strip if the FIRST word is a single letter+period.
                    import re
                    normalized = re.sub(r'^[a-z]\.\s+', '', normalized).strip()

                    return normalized

                # Find which names from summaries are missing from character list
                existing_names = set()
                for char in pipeline_char_map.characters:
                    existing_names.add(char.canonical_name.lower())
                    existing_names.add(_normalize_name_for_matching(char.canonical_name))
                    for alias in char.aliases:
                        existing_names.add(alias.lower())
                        existing_names.add(_normalize_name_for_matching(alias))

                def _is_generic_descriptor(name: str) -> bool:
                    """Check if name is a generic descriptor that shouldn't be a separate character."""
                    name_lower = name.lower().strip()

                    # Exact match for simple generic epithets
                    SIMPLE_EPITHETS = {
                        "the old man",
                        "the old woman",
                        "the young man",
                        "the young woman",
                        "old man",  # Bare form (common in narrative shift)
                        "old woman",  # Bare form (common in narrative shift)
                        "young man",
                        "young woman",
                        "the boy",
                        "the girl",
                        "the child",
                        "the stranger",
                        "the husband",
                        "the wife",
                        "the father",
                        "the mother",
                        "the son",
                        "the daughter",
                        "the brother",
                        "the sister",
                        "the gentleman",
                        "the lady",
                        "an old man",
                        "an old woman",
                        "a young man",
                        "a young woman",
                        "a stranger",
                        "father",
                        "mother",
                        # Narrator meta-references (should not be separate characters)
                        "narrator",
                        "the narrator",
                        "our narrator",
                        "the storyteller",
                        # Protagonist meta-references
                        "protagonist",
                        "the protagonist",
                        # Bare profession words (without "the")
                        "magistrate",
                        "nurse",
                        "fishermen",
                        "sailors",
                        "innkeepers",
                        "confessor",
                        "lieutenant",
                    }

                    if name_lower in SIMPLE_EPITHETS:
                        return True

                    # Pattern matching for qualified descriptors
                    # Examples: "the young girl", "the blind father", "Victor's father", "his father"
                    GENERIC_PATTERNS = [
                        # Possessive descriptors: "X's father", "his father", "her mother"
                        r"^(?:his|her|their|the narrator's|victor's|elizabeth's|\w+'s)\s+(?:father|mother|brother|sister|son|daughter|husband|wife)$",
                        # Qualified kinship: "the blind father", "the young girl", "the old woman"
                        r"^the\s+(?:young|old|blind|deaf|poor|rich|wise|cruel|kind|gentle)\s+(?:man|woman|boy|girl|father|mother|child|gentleman|lady)$",
                        # Generic professional descriptors with articles: "the servant", "the magistrate", "the philosopher"
                        r"^the\s+(?:servant|magistrate|priest|judge|doctor|lawyer|soldier|guard|innkeeper|merchant|clerk|officer|philosopher|nurse|confessor|lieutenant|master|mariner)$",
                        # Generic descriptors with articles: "the creature", "a stranger"
                        r"^(?:the|a|an)\s+(?:creature|stranger|visitor|guest|traveler|messenger|guide|companion)$",
                        # Qualified professional: "the village priest", "the natural philosopher"
                        r"^the\s+(?:village|town|local|old|young|blind|natural)\s+(?:priest|philosopher|doctor|magistrate|servant|guard)$",
                        # Compound descriptors: "the master mariner", "the ship's master", "the peasant man/woman"
                        r"^the\s+(?:master|ship's|peasant|young)\s+(?:mariner|master|man|woman)$",
                        # Turkish/generic merchant patterns: "the Turkish merchant", "the [nationality] [profession]"
                        r"^the\s+(?:turkish|french|italian|german|spanish|english)\s+(?:merchant|sailor|soldier|officer)$",
                        # "Woman/man of the house" patterns
                        r"^the\s+(?:woman|man)\s+of\s+the\s+(?:house|inn|cottage)$",
                        # Qualified descriptors: "the young woman in the barn"
                        r"^the\s+(?:young|old)\s+(?:woman|man|boy|girl)\s+(?:in|at|from)\s+the\s+\w+$",
                    ]

                    import re

                    for pattern in GENERIC_PATTERNS:
                        if re.match(pattern, name_lower):
                            return True

                    return False

                # Synonym groups for checking if a name is a synonym of an existing character
                # (Same as in characters.py cross-cast merge)
                SYNONYM_GROUPS = [
                    # Supernatural/created beings
                    {"creature", "monster", "fiend", "daemon", "wretch", "being", "thing"},
                    # Authority figures
                    {"stranger", "visitor", "guest", "traveler", "intruder"},
                    # Generic descriptors
                    {"man", "woman", "boy", "girl", "child", "person"},
                ]

                def _normalize_descriptor(name: str) -> str:
                    """Extract base descriptor from 'the X' pattern."""
                    name_lower = name.lower().strip()

                    # Normalize Unicode ligatures to ASCII for synonym matching
                    # (e.g., 'dæmon' → 'daemon', 'œuvre' → 'oeuvre')
                    name_lower = name_lower.replace("æ", "ae").replace("œ", "oe")

                    # Strip "the ", "a ", "an " prefixes
                    for prefix in ["the ", "a ", "an "]:
                        if name_lower.startswith(prefix):
                            name_lower = name_lower[len(prefix):].strip()
                            break

                    # Strip parentheticals
                    if " (" in name_lower:
                        name_lower = name_lower.split(" (")[0].strip()

                    return name_lower.strip(".,;:!?\"'" "")

                def _is_synonym_of_existing(name: str) -> bool:
                    """Check if name is a synonym of an existing character."""
                    name_desc = _normalize_descriptor(name)

                    # Check each existing character
                    for char in pipeline_char_map.characters:
                        char_desc = _normalize_descriptor(char.canonical_name)

                        # Check if both belong to same synonym group
                        for group in SYNONYM_GROUPS:
                            if name_desc in group and char_desc in group:
                                logger.info(
                                    f"F6: '{name}' is synonym of existing character '{char.canonical_name}' "
                                    f"(both in group: {group})"
                                )
                                return True
                    return False

                def _is_likely_alias_of_existing(name: str) -> bool:
                    """
                    Check if name is likely an alias/variant of an existing character.
                    Handles common patterns like:
                    - "Herbert White" → "Herbert" (full name vs first name)
                    - "Sergeant-Major Morris" → "Morris" (title + name vs name)
                    - "Herbert (mentioned)" → "Herbert" (annotation stripping)
                    - "Narrator (Victor)" → matches "Victor" or "Victor Frankenstein" (parenthetical matching)
                    """
                    import re

                    # Diagnostic logging for Wilson-family debugging (Bug B)
                    if "wilson" in name.lower():
                        logger.warning(
                            f"DIAG-WILSON: _is_likely_alias_of_existing called with '{name}', "
                            f"num characters in pipeline: {len(pipeline_char_map.characters)}, "
                            f"canonical names: {[c.canonical_name for c in pipeline_char_map.characters]}"
                        )

                    # Strip parenthetical annotations first (e.g., "Herbert (mentioned)" → "Herbert")
                    clean_name = name
                    parenthetical_content = None
                    if "(" in clean_name:
                        # Extract both the cleaned name and the parenthetical content
                        parts = clean_name.split("(", 1)
                        clean_name = parts[0].strip()
                        if len(parts) > 1 and ")" in parts[1]:
                            parenthetical_content = parts[1].split(")")[0].strip()

                    # Normalize for comparison
                    clean_lower = clean_name.lower().strip()

                    # If parenthetical content exists, check if it matches an existing character
                    # Example: "Narrator (Victor)" should match "Victor Frankenstein"
                    if parenthetical_content:
                        parenthetical_lower = parenthetical_content.lower().strip()
                        for char in pipeline_char_map.characters:
                            char_canonical = char.canonical_name.lower().strip()

                            # Check exact match with canonical name
                            if parenthetical_lower == char_canonical:
                                logger.info(
                                    f"F6: '{name}' matches existing '{char.canonical_name}' via parenthetical content"
                                )
                                return True

                            # Check if parenthetical content matches first or last name
                            char_name_parts = char_canonical.split()
                            if parenthetical_lower in char_name_parts:
                                logger.info(
                                    f"F6: '{name}' matches existing '{char.canonical_name}' (parenthetical is name component)"
                                )
                                return True

                            # Check aliases
                            for alias in char.aliases:
                                if parenthetical_lower == alias.lower().strip():
                                    logger.info(
                                        f"F6: '{name}' matches alias '{alias}' of '{char.canonical_name}' via parenthetical"
                                    )
                                    return True

                    for char in pipeline_char_map.characters:
                        char_canonical = char.canonical_name.lower().strip()

                        # Check exact match after cleaning
                        if clean_lower == char_canonical:
                            if "wilson" in name.lower():
                                logger.warning(f"DIAG-WILSON: blocked by exact match against '{char.canonical_name}'")
                            logger.debug(
                                f"F6: '{name}' matches existing '{char.canonical_name}' after cleaning"
                            )
                            return True

                        # Check if summary name is "FirstName LastName" and existing char is "FirstName"
                        # e.g., "Herbert White" should match "Herbert"
                        name_parts = clean_lower.split()
                        if len(name_parts) >= 2:
                            first_name = name_parts[0]
                            last_name = name_parts[-1]

                            # Does first name match existing character?
                            # Exception: if the existing character is a single-word name (e.g.
                            # "George"), do NOT block multi-word candidates like "George Wilson".
                            # The single-word entry is a first-name fragment; Step 4.5.9
                            # word-subset dedup will absorb it into the full-name character
                            # after F6 adds the correct entity. Blocking here would prevent
                            # "George Wilson" from ever entering the pipeline when a bare
                            # "George" supporting character already exists.
                            if first_name == char_canonical and len(char_canonical.split()) > 1:
                                if "wilson" in name.lower():
                                    logger.warning(f"DIAG-WILSON: blocked by first-name match against '{char.canonical_name}'")
                                logger.info(
                                    f"F6: '{name}' is likely full name variant of '{char.canonical_name}' (first name match)"
                                )
                                return True

                            # Does last name match existing character?
                            # Exception: if the existing character is a single-word name (e.g.
                            # "Wilson") and the candidate is multi-word (e.g. "George Wilson"),
                            # do NOT block.  The single-word entry is a surname-only fragment;
                            # Step 4.5.9 word-subset dedup will absorb it into the full-name
                            # character after F6 adds the correct entity.  Blocking here would
                            # prevent "George Wilson" from ever entering the pipeline when a
                            # bare "Wilson" supporting character already exists.
                            if last_name == char_canonical and len(char_canonical.split()) > 1:
                                if "wilson" in name.lower():
                                    logger.warning(f"DIAG-WILSON: blocked by last-name match against '{char.canonical_name}'")
                                logger.info(
                                    f"F6: '{name}' is likely full name variant of '{char.canonical_name}' (last name match)"
                                )
                                return True

                            # Does first name match the first name of an existing multi-word character?
                            # e.g., "Daisy Fay" (maiden name) → matches "Daisy Buchanan" (married name)
                            # Only match when candidate has a different last name (not just a full-name variant)
                            char_name_parts = char_canonical.split()
                            if (
                                len(char_name_parts) >= 2
                                and first_name == char_name_parts[0]
                                and last_name != char_name_parts[-1]
                            ):
                                if "wilson" in name.lower():
                                    logger.warning(f"DIAG-WILSON: blocked by alternate-surname match against '{char.canonical_name}'")
                                logger.info(
                                    f"F6: '{name}' shares first name with '{char.canonical_name}' "
                                    f"(likely alternate-surname variant, e.g. maiden name)"
                                )
                                return True

                        # Check if summary name has title prefix (e.g., "Sergeant-Major Morris" → "Morris")
                        # Strip common military/professional titles
                        TITLE_PATTERNS = [
                            r"^(?:sergeant-major|sergeant|captain|major|colonel|general|lieutenant|admiral|commander)\s+(.+)$",
                            r"^(?:doctor|dr\.|professor|prof\.|reverend|rev\.|father|sister)\s+(.+)$",
                        ]

                        for pattern in TITLE_PATTERNS:
                            match = re.match(pattern, clean_lower, re.IGNORECASE)
                            if match:
                                name_without_title = match.group(1).strip()
                                if name_without_title == char_canonical:
                                    logger.info(
                                        f"F6: '{name}' matches '{char.canonical_name}' after stripping title"
                                    )
                                    return True

                                # Check if the part after title is the LAST NAME of a
                                # multi-word character (e.g., "Captain Walton" → "Walton"
                                # matches last name of "Robert Walton").
                                char_parts = char_canonical.split()
                                if len(char_parts) >= 2 and name_without_title == char_parts[-1]:
                                    logger.info(
                                        f"F6: '{name}' matches '{char.canonical_name}' "
                                        f"(title + surname '{name_without_title}')"
                                    )
                                    return True

                                # Also check if the part after title matches an alias
                                for alias in char.aliases:
                                    if name_without_title == alias.lower().strip():
                                        logger.info(
                                            f"F6: '{name}' matches alias '{alias}' of '{char.canonical_name}' after stripping title"
                                        )
                                        return True

                    # Check if single-word candidate is a name component of a multi-word character.
                    # Universal invariant: if summaries say "Tom" and "Tom Buchanan" already exists,
                    # "Tom" is just a first-name reference — do NOT add a second character.
                    # NOTE: This block needs its own for-char loop because it was previously
                    # outside the main for-char loop (Bug A indentation fix).
                    name_parts = clean_lower.split()
                    for char in pipeline_char_map.characters:
                        char_canonical = char.canonical_name.lower().strip()
                        if len(name_parts) == 1:
                            _f6_cand_word = name_parts[0]
                            _f6_char_parts = char_canonical.split()
                            if len(_f6_char_parts) >= 2 and _f6_cand_word in _f6_char_parts:
                                if "wilson" in name.lower():
                                    logger.warning(f"DIAG-WILSON: blocked by single-word match against '{char.canonical_name}'")
                                logger.info(
                                    f"F6: '{name}' matches '{char.canonical_name}' "
                                    f"(single-word name component '{_f6_cand_word}')"
                                )
                                return True
                            for alias in char.aliases:
                                _f6_alias_parts = alias.lower().strip().split()
                                if len(_f6_alias_parts) >= 2 and _f6_cand_word in _f6_alias_parts:
                                    if "wilson" in name.lower():
                                        logger.warning(f"DIAG-WILSON: blocked by single-word alias match against '{alias}' of '{char.canonical_name}'")
                                    logger.info(
                                        f"F6: '{name}' matches alias '{alias}' of '{char.canonical_name}' "
                                        f"(single-word name component '{_f6_cand_word}')"
                                    )
                                    return True

                    # Check for partial alias matches (e.g., "the masked figure" vs alias "the figure")
                    # This handles cases where the summary uses a more descriptive variant of an existing alias
                    # Extract significant words (nouns) from the summary name
                    clean_words = set(clean_lower.split())
                    # Remove common articles and qualifiers to get core nouns
                    stopwords = {"the", "a", "an", "this", "that", "these", "those", "my", "your", "his", "her", "their", "our"}
                    adjectives = {"old", "young", "mysterious", "masked", "red", "black", "white", "great", "little", "big", "small"}
                    core_words = clean_words - stopwords - adjectives

                    # Check against all aliases of all characters
                    # NOTE: This block needs its own for-char loop (Bug A indentation fix).
                    for char in pipeline_char_map.characters:
                        for alias in char.aliases:
                            alias_lower = alias.lower().strip()
                            alias_words = set(alias_lower.split())
                            alias_core = alias_words - stopwords - adjectives

                            # If the summary name contains all core words from an existing alias,
                            # it's likely a more descriptive variant (e.g., "the masked figure" contains "figure")
                            if alias_core and alias_core.issubset(core_words):
                                # Guard: single-word alias vs multi-word candidate = surname collision
                                # e.g., alias "Wilson" should not block "George Wilson"
                                if len(alias_core) == 1 and len(core_words) >= 2:
                                    continue
                                if "wilson" in name.lower():
                                    logger.warning(f"DIAG-WILSON: blocked by partial alias core-word match against '{alias}' of '{char.canonical_name}'")
                                logger.info(
                                    f"F6: '{name}' is likely variant of '{char.canonical_name}' (contains alias '{alias}' core words: {alias_core})"
                                )
                                return True

                    # Check if summary name appears in character's description
                    # This handles cases where the LLM proposed an alias but grounding filtered it out
                    # Example: "the masked figure" appears in description of "the Red Death"
                    # IMPORTANT: Only check DESCRIPTIVE phrases (all-lowercase), NOT proper names.
                    # A proper name like "George Wilson" appearing in Michaelis's description means
                    # George Wilson is referenced by Michaelis, NOT that George Wilson IS Michaelis.
                    # Universal invariant: description-phrase alias matching only applies to
                    # lowercase descriptors (epithets, roles), never to capitalized proper names.
                    _name_words_orig = [w for w in name.split() if w]
                    _name_has_proper_noun = any(w[0].isupper() for w in _name_words_orig if w)
                    # NOTE: This block needs its own for-char loop (Bug A indentation fix).
                    for char in pipeline_char_map.characters:
                        if char.description and not _name_has_proper_noun:
                            desc_lower = char.description.lower()

                            # Build the cleaned phrase (strip articles but keep adjectives and nouns)
                            # Example: "the masked figure" → "masked figure"
                            name_without_articles = clean_lower
                            for article in ["the ", "a ", "an "]:
                                if name_without_articles.startswith(article):
                                    name_without_articles = name_without_articles[len(article):].strip()
                                    break

                            # Check if the phrase appears verbatim in the description
                            # Example: "masked figure" in "manifests as a masked figure"
                            if len(name_without_articles.split()) >= 2 and name_without_articles in desc_lower:
                                if "wilson" in name.lower():
                                    logger.warning(f"DIAG-WILSON: blocked by description phrase match in '{char.canonical_name}'")
                                logger.info(
                                    f"F6: '{name}' matches '{char.canonical_name}' (phrase '{name_without_articles}' found in description)"
                                )
                                return True

                    # Check if name is an initials abbreviation (e.g., "R.W." → "Robert Walton").
                    # Pattern: one or more "X." segments where each X is a single uppercase letter.
                    initials_match = re.match(r'^([A-Z]\.)+$', clean_name)
                    if initials_match:
                        initials = [c for c in clean_name if c.isupper()]
                        for char in pipeline_char_map.characters:
                            char_words = [
                                w for w in char.canonical_name.split()
                                if w and w[0].isupper()
                            ]
                            if len(char_words) >= len(initials) >= 2:
                                if [w[0] for w in char_words[:len(initials)]] == initials:
                                    logger.info(
                                        f"F6: '{name}' matches '{char.canonical_name}' via initials"
                                    )
                                    return True

                    return False

                # Common English pronouns and single-character strings that should never
                # be treated as character names.  A first-person narrator uses "I" heavily,
                # and the summariser may include it in active_characters by mistake.
                _F6_PRONOUN_FILTER = {
                    "i", "he", "she", "they", "we", "it",
                    "him", "her", "them", "us",
                    "his", "hers", "theirs", "its", "ours",
                }

                missing_names = []
                f6_seen_normalized = set()  # Track normalized names already added in this F6 pass
                for name in summary_character_names:
                    # Skip single-character strings (pronouns like "I", OCR noise, etc.)
                    if len(name.strip()) <= 1:
                        logger.debug(f"F6: Skipping '{name}' (single character — not a valid name)")
                        continue

                    # Skip common pronouns that are never character names
                    if name.strip().lower() in _F6_PRONOUN_FILTER:
                        logger.debug(f"F6: Skipping '{name}' (common pronoun — not a character name)")
                        continue

                    # Skip generic descriptors - these are likely aliases of existing characters
                    if _is_generic_descriptor(name):
                        logger.debug(
                            f"F6: Skipping generic descriptor '{name}' (likely alias of existing character)"
                        )
                        continue

                    # Skip if name already exists as canonical or alias (check both raw and normalized)
                    if (
                        name.lower() in existing_names
                        or _normalize_name_for_matching(name) in existing_names
                    ):
                        logger.debug(f"F6: Skipping '{name}' (already exists in character list)")
                        continue

                    # Skip if name is a synonym of an existing character
                    if _is_synonym_of_existing(name):
                        logger.debug(f"F6: Skipping '{name}' (synonym of existing character)")
                        continue

                    # Skip if name is likely an alias/variant of an existing character
                    if _is_likely_alias_of_existing(name):
                        logger.debug(f"F6: Skipping '{name}' (likely alias of existing character)")
                        continue

                    # Skip if a case variant of this name was already added in this F6 pass
                    # (e.g., "the butler" and "The butler" from different chapter summaries)
                    normalized_for_f6 = _normalize_name_for_matching(name)
                    if normalized_for_f6 in f6_seen_normalized:
                        logger.debug(
                            f"F6: Skipping '{name}' (case/article variant of already-added name in this pass)"
                        )
                        continue
                    f6_seen_normalized.add(normalized_for_f6)

                    # Skip plural group nouns (e.g., "the courtiers", "the musicians").
                    # A plural agent/role noun denotes a group, never an individual character.
                    # Universal linguistic invariant: article + plural_noun = group reference.
                    # Uses the same suffix patterns as _is_valid_alias() in characters.py.
                    _F6_PLURAL_SUFFIXES = (
                        "ers", "ors", "ians", "ists", "ants", "ents", "iers", "ees", "smen", "ies", "stra"
                    )
                    _f6_article_words = {"the", "a", "an", "of", "in", "from", "at", "by", "with"}
                    _f6_tokens = [
                        w.strip(".,;:'\"()")
                        for w in name.lower().split()
                        if w.strip(".,;:'\"()") and w.strip(".,;:'\"()") not in _f6_article_words
                    ]
                    if _f6_tokens:
                        _f6_head = _f6_tokens[-1]
                        _is_plural_group_f6 = any(
                            _f6_head.endswith(sfx) and len(_f6_head) > len(sfx) + 1
                            for sfx in _F6_PLURAL_SUFFIXES
                        )
                        if _is_plural_group_f6:
                            # Also check that ALL content words are lowercase (proper nouns are ok to create)
                            _f6_content = [
                                w.strip(".,;:'\"()")
                                for w in name.split()
                                if w.strip(".,;:'\"()").lower() not in _f6_article_words
                            ]
                            _all_lower_f6 = all(w and w[0].islower() for w in _f6_content if w)
                            if _all_lower_f6:
                                logger.info(
                                    f"F6: Skipping '{name}' — plural group noun (head: '{_f6_head}'); "
                                    f"group references are never individual characters"
                                )
                                continue

                    # Universal invariant: named characters always contain at least one proper noun
                    # (a capitalized non-article word). Pure lowercase descriptors like "butler",
                    # "gardener", "the war veteran" are occupational roles, not named characters.
                    _f6_name_words = name.split()
                    _f6_articles_set = {"the", "a", "an", "of", "in", "from", "at", "by", "with"}
                    _f6_content_words = [
                        w.strip(".,;:'\"()")
                        for w in _f6_name_words
                        if w.strip(".,;:'\"()").lower() not in _f6_articles_set
                    ]
                    _f6_has_proper_noun = any(
                        w and w[0].isupper() for w in _f6_content_words if w
                    )
                    if not _f6_has_proper_noun:
                        logger.info(
                            f"F6: Skipping '{name}' — no proper noun; "
                            f"likely an occupational role or generic descriptor"
                        )
                        continue

                    # Name is truly missing - add it
                    missing_names.append(name)

                # Helper used by F6 and F6c safety-net
                import hashlib as _hashlib_f6
                import re as _re_f6

                def _f6_add_character(name: str, chapters_present: list, confidence: float = 0.75) -> bool:
                    """Add a character from F6 reconciliation. Returns True if added."""
                    char_id = _hashlib_f6.md5(name.encode()).hexdigest()[:12]
                    new_character = Character(
                        id=char_id,
                        canonical_name=name,
                        aliases=[],
                        mentions=[],
                        first_appearance_chapter=(
                            min(chapters_present) if chapters_present else 0
                        ),
                        mention_count=len(chapters_present),
                        chapters_present=chapters_present,
                        confidence=confidence,
                        supporting_strategies=["chapter_summary_reconciliation"],
                        description="",
                        character_type=CharacterType.STORY,
                    )
                    # Count actual text mentions via regex
                    name_pattern = rf"\b{_re_f6.escape(name)}(?:'?s)?\b"
                    actual_mentions = len(_re_f6.findall(name_pattern, doc.text, _re_f6.IGNORECASE))
                    if actual_mentions > 0:
                        new_character.mention_count = actual_mentions
                        logger.info(
                            f"F6: '{name}' actual text mentions: {actual_mentions} "
                            f"(was {len(chapters_present)} from chapter count)"
                        )
                    pipeline_char_map.characters.append(new_character)
                    return True

                if missing_names:
                    logger.info(
                        f"F6: Found {len(missing_names)} character(s) in summaries but not in character list: {missing_names}"
                    )

                    for name in missing_names:
                        chapters_present = []
                        for summary in summary_map.summaries:
                            active_chars = (
                                getattr(summary, "active_characters", None)
                                or summary.characters_present
                                or []
                            )
                            if name in active_chars:
                                chapters_present.append(summary.chapter_index)
                        _f6_add_character(name, chapters_present, confidence=0.75)

                    print(f"   Added {len(missing_names)} character(s) from chapter summaries")
                    logger.info(f"F6: Added characters: {', '.join(missing_names)}")
                else:
                    logger.info("F6: All characters from summaries already in character list")

                # F6c: Safety-net for characters appearing as active in 2+ distinct chapters.
                # If a character appears in multiple chapters' active_characters but was NOT
                # added by F6 (possibly due to an alias/similarity filter false-positive),
                # force-add them. Universal invariant: appearing as active in 2+ chapters is
                # strong evidence of a real, plot-relevant character.
                try:
                    _f6c_name_chapters: dict = {}
                    for _f6c_summary in summary_map.summaries:
                        _f6c_active = (
                            getattr(_f6c_summary, "active_characters", None)
                            or _f6c_summary.characters_present
                            or []
                        )
                        for _f6c_name in _f6c_active:
                            _f6c_name = _f6c_name.strip()
                            if _f6c_name:
                                _f6c_name_chapters.setdefault(_f6c_name, []).append(
                                    _f6c_summary.chapter_index
                                )

                    # Build lookup sets from current character list (includes F6 additions)
                    _f6c_existing_canonical = set()
                    _f6c_existing_aliases = set()
                    _f6c_canonical_words: set = set()  # individual words from canonical names
                    for _f6c_char in pipeline_char_map.characters:
                        _cn = _f6c_char.canonical_name.lower().strip()
                        _f6c_existing_canonical.add(_cn)
                        # Track individual words (len > 3) so we can detect name components
                        # Example: "gatsby" is a word of canonical "Gatsby" → block "Jay Gatsby"
                        for _w in _cn.split():
                            _w = _w.strip(".,;:'\"()")
                            if len(_w) > 3:
                                _f6c_canonical_words.add(_w)
                        for _alias in getattr(_f6c_char, "aliases", []):
                            _f6c_existing_aliases.add(_alias.lower().strip())

                    _f6c_added = []
                    _f6c_articles = {"the", "a", "an", "of", "in", "from", "at", "by", "with"}
                    for _f6c_name, _f6c_chapters in _f6c_name_chapters.items():
                        # Must appear in 2+ distinct chapters
                        if len(set(_f6c_chapters)) < 2:
                            continue
                        _f6c_lower = _f6c_name.lower().strip()
                        # Skip if already a canonical character
                        if _f6c_lower in _f6c_existing_canonical:
                            continue
                        # Skip if already a known alias (e.g., "Myrtle Wilson" is Myrtle's alias)
                        if _f6c_lower in _f6c_existing_aliases:
                            continue
                        # Skip if any substantive word of this name appears as a canonical name word.
                        # Universal invariant: a name variant/fragment of an existing character
                        # (e.g., "Daisy" from "Daisy Buchanan", "Jay Gatsby" from "Gatsby") is
                        # not a new character — it's the same entity referred to differently.
                        _f6c_cand_words = {
                            w.strip(".,;:'\"()").lower()
                            for w in _f6c_name.split()
                            if len(w.strip(".,;:'\"()")) > 3
                        }
                        if _f6c_cand_words & _f6c_canonical_words:
                            continue
                        # Skip generic descriptors
                        if _is_generic_descriptor(_f6c_name):
                            continue
                        # Must have at least one proper noun
                        _f6c_content = [
                            w.strip(".,;:'\"()")
                            for w in _f6c_name.split()
                            if w.strip(".,;:'\"()").lower() not in _f6c_articles
                        ]
                        if not any(w and w[0].isupper() for w in _f6c_content if w):
                            continue
                        # Skip pronouns
                        if _f6c_lower in _F6_PRONOUN_FILTER:
                            continue
                        # Require at least 2 actual text mentions
                        _f6c_pattern = rf"\b{_re_f6.escape(_f6c_name)}(?:'?s)?\b"
                        _f6c_mentions = len(
                            _re_f6.findall(_f6c_pattern, doc.text, _re_f6.IGNORECASE)
                        )
                        if _f6c_mentions < 2:
                            continue
                        # Force-add the character
                        _f6_add_character(_f6c_name, list(set(_f6c_chapters)), confidence=0.75)
                        _f6c_existing_canonical.add(_f6c_lower)
                        _f6c_added.append(_f6c_name)
                        logger.info(
                            f"F6c: Force-added '{_f6c_name}' "
                            f"({len(set(_f6c_chapters))} chapters, {_f6c_mentions} text mentions)"
                        )

                    if _f6c_added:
                        print(f"   F6c safety-net added {len(_f6c_added)} character(s): {_f6c_added}")
                        logger.info(f"F6c: Safety-net characters: {', '.join(_f6c_added)}")
                except Exception as _f6c_err:
                    logger.warning(f"F6c safety-net failed: {_f6c_err}")

                # F6b: Also scan mentioned_characters (referenced but not physically present).
                # Characters only referenced in dialogue often land in mentioned_characters but
                # are still important (e.g., a figure invoked as a manipulation tool, a suspect
                # discussed by witnesses). We include them when they have ≥ N actual text mentions
                # (adaptive threshold to prevent guest-list explosion in long books).
                #
                # Threshold: short texts (< 10K words) → 2 mentions; long texts → 3 mentions.
                # This filters incidental name-drops (Gatsby's party guests: 1–2 mentions each)
                # while capturing recurring referenced characters (≥ 2–3 mentions = plot-relevant).
                try:
                    import re as _re_f6b
                    import hashlib as _hashlib_f6b

                    _f6b_word_count = len(doc.text.split()) if doc.text else 0
                    _f6b_mention_threshold = 2 if _f6b_word_count < 10_000 else 3

                    # Collect mentioned_characters across all summaries
                    mentioned_names: set[str] = set()
                    for summary in summary_map.summaries:
                        mentioned = getattr(summary, "mentioned_characters", None) or []
                        for name in mentioned:
                            stripped = name.strip()
                            if stripped:
                                mentioned_names.add(stripped)

                    # Only consider names NOT already covered by active_characters pass (F6)
                    mentioned_only = mentioned_names - summary_character_names

                    f6b_added = []
                    for name in mentioned_only:
                        # Apply the same skip filters as F6 active_characters
                        if len(name.strip()) <= 1:
                            continue
                        if name.strip().lower() in _F6_PRONOUN_FILTER:
                            continue
                        if _is_generic_descriptor(name):
                            continue
                        if (
                            name.lower() in existing_names
                            or _normalize_name_for_matching(name) in existing_names
                        ):
                            continue
                        if _is_synonym_of_existing(name):
                            continue
                        if _is_likely_alias_of_existing(name):
                            continue

                        # Universal invariant: named characters have at least one proper noun
                        _f6b_articles = {"the", "a", "an", "of", "in", "from", "at", "by", "with"}
                        _f6b_content = [
                            w.strip(".,;:'\"()")
                            for w in name.split()
                            if w.strip(".,;:'\"()").lower() not in _f6b_articles
                        ]
                        if _f6b_content and not any(w and w[0].isupper() for w in _f6b_content if w):
                            continue

                        # Require actual text mentions above threshold
                        name_pattern = rf"\b{_re_f6b.escape(name)}(?:'?s)?\b"
                        actual_mentions = len(_re_f6b.findall(name_pattern, doc.text, _re_f6b.IGNORECASE))
                        if actual_mentions < _f6b_mention_threshold:
                            continue

                        # Add to character list
                        chapters_present = []
                        for summary in summary_map.summaries:
                            mentioned = getattr(summary, "mentioned_characters", None) or []
                            if name in mentioned:
                                chapters_present.append(summary.chapter_index)

                        char_id = _hashlib_f6b.md5(name.encode()).hexdigest()[:12]
                        new_character = Character(
                            id=char_id,
                            canonical_name=name,
                            aliases=[],
                            mentions=[],
                            first_appearance_chapter=(
                                min(chapters_present) if chapters_present else 0
                            ),
                            mention_count=actual_mentions,
                            chapters_present=chapters_present,
                            confidence=0.6,  # Lower confidence — referenced but not physically present
                            supporting_strategies=["mentioned_character_reconciliation"],
                            description="",
                            character_type=CharacterType.STORY,
                        )
                        pipeline_char_map.characters.append(new_character)

                        # Update existing_names so later iterations don't double-add
                        existing_names.add(name.lower())
                        existing_names.add(_normalize_name_for_matching(name))
                        f6b_added.append(name)

                    if f6b_added:
                        print(f"   Added {len(f6b_added)} referenced character(s) from summaries: {f6b_added}")
                        logger.info(f"F6b: Added mentioned-only characters: {', '.join(f6b_added)}")
                    else:
                        logger.info("F6b: No additional mentioned-only characters to add")
                except Exception as e:
                    logger.warning(f"F6b mentioned_characters reconciliation failed: {e}")
            except Exception as e:
                logger.warning(f"F6 character reconciliation failed: {e}")

        # Step 4.5: Early Narrator Detection (before profile generation)
        # Use summary-based narrator detection to mark narrators early, ensuring they
        # receive profile enrichment even if they have few explicit name mentions
        if summary_map and llm and pipeline_char_map.characters:
            print("🎭 Detecting narrator from summaries...")
            try:
                from .pipeline.character_extraction_v2.narrator import NarratorDetector

                narrator_detector = NarratorDetector(llm)

                # Extract chapter summaries
                chapter_summaries = [s.summary for s in summary_map.summaries if s.summary]

                narrator_info = narrator_detector.detect(
                    chapter_summaries=chapter_summaries,
                    main_cast=pipeline_char_map.characters,
                    plot_summary=None,  # Not available yet
                )

                if narrator_info.narrator_name and narrator_info.confidence >= 0.7:
                    # Adapt V2 NarratorInfo to work with _mark_narrator_in_character_map
                    # which expects narrative_style and narrator_role attributes
                    from .pipeline.character_profiling.narrator import NarratorInfo as OldNarratorInfo

                    adapted_info = OldNarratorInfo(
                        narrative_style=narrator_info.pov,  # Map 'pov' to 'narrative_style'
                        narrator_name=narrator_info.narrator_name,
                        narrator_role="narrator",  # Generic role for now
                        confidence=narrator_info.confidence,
                    )

                    # Mark narrator in character list
                    self._mark_narrator_in_character_map(
                        pipeline_char_map.characters, adapted_info
                    )

                    # Update narrator_detected for use in profile generation.
                    # Only update if V2 pipeline didn't already identify a narrator —
                    # V2 ran detection with full context (raw text + summaries + cast),
                    # so its result is more reliable than re-detecting from summaries alone.
                    if narrator_detected is None:
                        narrator_detected = narrator_info.narrator_name
                        print(f"   Detected narrator: {narrator_info.narrator_name} ({narrator_info.pov})")
                    else:
                        print(f"   Narrator already identified by V2 pipeline: {narrator_detected} (skipping re-detection)")
                    logger.info(
                        f"Early narrator detection: {narrator_info.narrator_name} "
                        f"(confidence={narrator_info.confidence:.2f})"
                    )

                    # For first-person narratives, replace "the narrator" references in
                    # chapter summaries with the narrator's actual name. The summaries are
                    # generated before narrator detection, so they may use "the narrator"
                    # as a stand-in for the protagonist. Using the real name improves
                    # summary specificity for any first-person narrative.
                    if narrator_info.pov == "first-person" and summary_map:
                        _nn = narrator_info.narrator_name
                        _replaced = 0
                        for _sum in summary_map.summaries:
                            if _sum.summary and "narrator" in _sum.summary.lower():
                                _new_sum = re.sub(
                                    r'\bthe narrator\b', _nn,
                                    _sum.summary, flags=re.IGNORECASE,
                                )
                                if _new_sum != _sum.summary:
                                    _sum.summary = _new_sum
                                    _replaced += 1
                        if _replaced:
                            logger.info(
                                f"Replaced 'the narrator' with '{_nn}' in {_replaced} summaries"
                            )
                else:
                    print("   No definitive narrator identified yet")
                    logger.info("Early narrator detection: No narrator identified")
            except Exception as e:
                logger.warning(f"Early narrator detection failed: {e}")
                print(f"   Narrator detection skipped (error: {e})")

        # Safety net: enforce role correctness by mention count before profiling.
        # Universal invariant: a character's role must reflect narrative significance.
        # This catches cases where the extraction pipeline assigned "minor" to a
        # high-mention character (e.g., when the protagonist was only found by NER,
        # not by LLM extraction from summaries, and promotion logic didn't fire).
        if pipeline_char_map and pipeline_char_map.characters:
            _sn_word_count = len(doc.text.split()) if doc and doc.text else 100_000
            if _sn_word_count >= 20_000:
                _sn_protagonist_threshold = 200
                _sn_main_threshold = 100
            else:
                _sn_scale = 100_000 / max(_sn_word_count, 1000)
                _sn_protagonist_threshold = max(10, int(200 / _sn_scale))
                _sn_main_threshold = max(5, int(100 / _sn_scale))
            for _sn_char in pipeline_char_map.characters:
                if getattr(_sn_char, "is_narrator", False):
                    continue
                _sn_role = getattr(_sn_char, "role", None) or "minor"
                _sn_mentions = getattr(_sn_char, "mention_count", 0) or 0
                if _sn_role in ("minor", "supporting") and _sn_mentions >= _sn_protagonist_threshold:
                    logger.info(
                        f"Role safety net: '{_sn_char.canonical_name}' upgraded from "
                        f"'{_sn_role}' to 'protagonist' ({_sn_mentions} mentions)"
                    )
                    _sn_char.role = "protagonist"
                elif _sn_role == "minor" and _sn_mentions >= _sn_main_threshold:
                    logger.info(
                        f"Role safety net: '{_sn_char.canonical_name}' upgraded from "
                        f"'minor' to 'main' ({_sn_mentions} mentions)"
                    )
                    _sn_char.role = "main"

        # Step 4.5.5: Canonical name normalization — prefer most-used name over legal/birth name.
        # Universal invariant: the name a character is primarily called in the text should be
        # the canonical name. If a character's canonical appears < 10 times in text but an
        # alias appears 20+ times, the alias is the "real" name for narrator purposes.
        # This catches cases like "James Gatz" (4 text uses) whose alias "Jay Gatsby" appears
        # ~175 times — "Jay Gatsby" is the correct canonical for narrator prep.
        if pipeline_char_map and pipeline_char_map.characters and doc and doc.text:
            import re as _sn_re
            def _count_in_text(name: str, text: str) -> int:
                return len(_sn_re.findall(
                    rf"(?<![A-Za-z0-9]){_sn_re.escape(name)}(?![A-Za-z0-9])",
                    text, _sn_re.IGNORECASE
                ))
            for _sn55_char in pipeline_char_map.characters:
                if getattr(_sn55_char, "is_narrator", False):
                    continue
                _sn55_aliases = getattr(_sn55_char, "aliases", None) or []
                if not _sn55_aliases:
                    continue
                _sn55_canonical_count = _count_in_text(_sn55_char.canonical_name, doc.text)
                if _sn55_canonical_count >= 10:
                    continue  # Canonical is well-used; no need to rename
                # Find the alias with the highest text count
                _sn55_best_alias = None
                _sn55_best_count = 0
                for _sn55_alias in _sn55_aliases:
                    _sn55_ac = _count_in_text(_sn55_alias, doc.text)
                    # Alias must appear > 20 times AND > 3x more than canonical
                    if _sn55_ac >= 20 and _sn55_ac > _sn55_canonical_count * 3:
                        if _sn55_best_alias is None:
                            _sn55_best_alias = _sn55_alias
                            _sn55_best_count = _sn55_ac
                        elif len(_sn55_alias.split()) > 1 and len(_sn55_best_alias.split()) == 1:
                            _sn55_best_alias = _sn55_alias  # Prefer multi-word (fuller name)
                            _sn55_best_count = _sn55_ac
                        elif _sn55_ac > _sn55_best_count and len(_sn55_alias.split()) >= len(_sn55_best_alias.split()):
                            _sn55_best_alias = _sn55_alias
                            _sn55_best_count = _sn55_ac
                if _sn55_best_alias:
                    _sn55_old = _sn55_char.canonical_name
                    _sn55_char.aliases = [a for a in _sn55_aliases if a.lower() != _sn55_best_alias.lower()]
                    if _sn55_old.lower() not in {a.lower() for a in _sn55_char.aliases}:
                        _sn55_char.aliases.append(_sn55_old)
                    _sn55_char.canonical_name = _sn55_best_alias
                    logger.info(
                        f"Step 4.5.5: Renamed '{_sn55_old}' → '{_sn55_best_alias}' "
                        f"({_sn55_best_count} text uses vs {_sn55_canonical_count} for old canonical)"
                    )

        # Step 4.5.9: Post-extraction word-subset dedup.
        # Universal invariant: if a character's canonical name words are a strict subset of
        # another character's canonical or alias words, they are partial references to the same
        # entity. Merge the shorter-named character into the longer-named one.
        # This runs AFTER Step 4.5.5 so all aliases are fully enriched, and catches cases where
        # the V2 pipeline's internal dedup (STEP 5.12) could not match due to alias ordering.
        if pipeline_char_map and pipeline_char_map.characters:
            try:
                _459_to_remove: set[str] = set()
                _459_chars = list(pipeline_char_map.characters)
                for _459_i, _459_a in enumerate(_459_chars):
                    if _459_a.id in _459_to_remove:
                        continue
                    _459_a_words = set(_459_a.canonical_name.lower().split())
                    if not _459_a_words:
                        continue
                    for _459_j, _459_b in enumerate(_459_chars):
                        if _459_i == _459_j or _459_b.id in _459_to_remove:
                            continue
                        # Check if _459_a canonical words are strict subset of _459_b canonical words
                        _459_b_words = set(_459_b.canonical_name.lower().split())
                        if _459_a_words < _459_b_words:
                            _459_b.mention_count = max(_459_b.mention_count, _459_a.mention_count)
                            # Transfer F6 protection: if the absorbed character was added by F6
                            # (chapter_summary_reconciliation), carry that strategy onto the survivor
                            # so the survivor is not discarded by the evidence filter in _convert_characters.
                            _F6_STRATEGY = "chapter_summary_reconciliation"
                            if _F6_STRATEGY in (_459_a.supporting_strategies or []) and \
                                    _F6_STRATEGY not in (_459_b.supporting_strategies or []):
                                _459_b.supporting_strategies = list(_459_b.supporting_strategies or []) + [_F6_STRATEGY]
                            _459_to_remove.add(_459_a.id)
                            logger.info(
                                f"Step 4.5.9: '{_459_a.canonical_name}' merged into "
                                f"'{_459_b.canonical_name}' (word-subset of canonical)"
                            )
                            break
                        # Check if _459_a canonical words are strict subset of any _459_b alias words
                        for _459_alias in (_459_b.aliases or []):
                            _459_alias_words = set(_459_alias.lower().split())
                            if _459_a_words <= _459_alias_words and len(_459_a_words) < len(_459_alias_words):
                                _459_b.mention_count = max(_459_b.mention_count, _459_a.mention_count)
                                # Transfer F6 protection when merging via alias match too
                                _F6_STRATEGY = "chapter_summary_reconciliation"
                                if _F6_STRATEGY in (_459_a.supporting_strategies or []) and \
                                        _F6_STRATEGY not in (_459_b.supporting_strategies or []):
                                    _459_b.supporting_strategies = list(_459_b.supporting_strategies or []) + [_F6_STRATEGY]
                                _459_to_remove.add(_459_a.id)
                                logger.info(
                                    f"Step 4.5.9: '{_459_a.canonical_name}' merged into "
                                    f"'{_459_b.canonical_name}' (word-subset of alias '{_459_alias}')"
                                )
                                break
                        if _459_a.id in _459_to_remove:
                            break
                if _459_to_remove:
                    pipeline_char_map.characters = [
                        c for c in _459_chars if c.id not in _459_to_remove
                    ]
                    logger.info(f"Step 4.5.9: Removed {len(_459_to_remove)} word-subset duplicate(s)")
            except Exception as _459_e:
                logger.warning(f"Step 4.5.9 post-extraction dedup failed: {_459_e}")

        # Post-4.5.9 F6 re-check: characters that were blocked during F6 may now be
        # unblocked after 4.5.9 merged/removed the blocker (e.g., a bare "Wilson" that
        # blocked "George Wilson" was absorbed into "Myrtle Wilson" by 4.5.9).
        # Re-scan summary characters and add any that now pass all checks.
        if summary_map and pipeline_char_map and pipeline_char_map.characters:
            try:
                import hashlib as _hashlib_post459

                # Rebuild lookup sets from current (post-4.5.9) character list
                _post459_existing = set()
                for _c in pipeline_char_map.characters:
                    _post459_existing.add(_c.canonical_name.lower().strip())
                    for _a in getattr(_c, 'aliases', []):
                        _post459_existing.add(_a.lower().strip())

                _post459_added = []
                _post459_name_chapters = {}
                for _s in summary_map.summaries:
                    _active = getattr(_s, 'active_characters', None) or _s.characters_present or []
                    for _n in _active:
                        _n = _n.strip()
                        if _n:
                            _post459_name_chapters.setdefault(_n, []).append(_s.chapter_index)

                for _name, _chapters in _post459_name_chapters.items():
                    if len(set(_chapters)) < 2:
                        continue
                    _lower = _name.lower().strip()
                    if _lower in _post459_existing:
                        continue
                    # Must have proper noun
                    _content = [w for w in _name.split() if w.strip(".,;:'\"()")]
                    if not any(w[0].isupper() for w in _content if w):
                        continue
                    # Must have 2+ text mentions
                    _pattern = rf"\b{re.escape(_name)}(?:'?s)?\b"
                    _mentions = len(re.findall(_pattern, doc.text, re.IGNORECASE))
                    if _mentions < 2:
                        continue
                    # Create the character inline (since _f6_add_character is out of scope)
                    _char_id = _hashlib_post459.md5(_name.encode()).hexdigest()[:12]
                    _new_char = Character(
                        id=_char_id,
                        canonical_name=_name,
                        aliases=[],
                        mentions=[],
                        first_appearance_chapter=(min(set(_chapters)) if _chapters else 0),
                        mention_count=_mentions,
                        chapters_present=list(set(_chapters)),
                        confidence=0.70,
                        supporting_strategies=["chapter_summary_reconciliation"],
                        description="",
                        character_type=CharacterType.STORY,
                    )
                    pipeline_char_map.characters.append(_new_char)
                    _post459_existing.add(_lower)
                    _post459_added.append(_name)
                    logger.info(f"Post-4.5.9 F6 re-check: Added '{_name}' ({len(set(_chapters))} chapters, {_mentions} mentions)")

                if _post459_added:
                    print(f"   Post-4.5.9 re-check added {len(_post459_added)} character(s): {_post459_added}")
            except Exception as _e:
                logger.warning(f"Post-4.5.9 F6 re-check failed: {_e}")

        # Step 4.6: Generate Character Profiles with Summary Evidence and Moral Valence (F2, F3)
        # Adaptive threshold based on text length
        # For short texts (< 5000 words), use a lower threshold
        # For normal texts (5000-50000 words), use standard threshold
        # For long texts (> 50000 words), maintain standard threshold
        word_count = len(doc.text.split())
        if word_count < 5000:
            # Short story: profile characters with 2+ mentions
            MIN_MENTIONS_FOR_PROFILE = 2
            logger.info(
                f"Short text detected ({word_count} words) - using MIN_MENTIONS_FOR_PROFILE = 2"
            )
        else:
            # Standard threshold for longer texts
            MIN_MENTIONS_FOR_PROFILE = 5

        # Use characters-specific LLM client for profiles (same model as character extraction)
        profile_llm = self._get_agent_llm_client("characters") or llm
        if profile_llm:
            print("📋 Generating character profiles...")
            self._write_progress(
                "Character Profiles",
                profile_llm.config.model if profile_llm and profile_llm.config else None,
            )
            with self._metrics.stage("Character Profiles") as ctx:
                # Set model info from LLM client config (before running)
                if profile_llm and profile_llm.config:
                    ctx.set_model(profile_llm.config.model, profile_llm.config.provider)

                # F3: Initialize moral valence classifier
                moral_valence_classifier = MoralValenceClassifier(profile_llm)
                logger.info("F3: Moral valence classification enabled")

                # Generate profiles for all characters with sufficient mentions
                # SPECIAL CASE: Include narrators even if they have few explicit mentions
                # (first-person narrators may use "I" throughout without saying their name)
                eligible_chars = [
                    c
                    for c in pipeline_char_map.characters
                    if c.mention_count >= MIN_MENTIONS_FOR_PROFILE
                    or getattr(c, "is_narrator", False)
                ]
                logger.info(
                    f"Generating profiles for {len(eligible_chars)} eligible characters ({MIN_MENTIONS_FOR_PROFILE}+ mentions or narrator)"
                )
                profile_count = 0
                high_conf_count = 0
                medium_conf_count = 0
                low_conf_count = 0

                # Build character name list for collision detection and relationship extraction
                # This helps avoid assigning evidence to the wrong character when names overlap
                # (e.g., "John" vs "John Donaldson", "Mary" vs "Mary Smith")
                all_character_names = [c.canonical_name for c in pipeline_char_map.characters]

                # Build character descriptions map for same-name disambiguation.
                # When two characters share a name prefix (e.g., "John" and "John Donaldson"),
                # passing the other character's extracted description helps the LLM distinguish
                # which passages belong to which character.
                character_descriptions_map: dict[str, str] = {}
                for _c in pipeline_char_map.characters:
                    descs = getattr(_c, "descriptions", []) or []
                    if descs:
                        # Use first description text (from V2 extraction)
                        first_desc = descs[0]
                        desc_text = (
                            first_desc.get("text", "") if isinstance(first_desc, dict)
                            else getattr(first_desc, "text", "")
                        )
                        if desc_text:
                            character_descriptions_map[_c.canonical_name] = desc_text

                # F2: Initialize summary evidence extractor with character names for collision detection
                summary_evidence_extractor = None
                if summary_map:
                    summary_evidence_extractor = SummaryEvidenceExtractor(
                        profile_llm,
                        all_character_names  # Required for detecting name substring collisions
                    )
                    logger.info("F2: Summary evidence extraction enabled with collision detection")

                # Store summary evidence per character for post-profile correction pass
                _char_summary_evidence_store: dict[str, object] = {}

                for i, char in enumerate(eligible_chars):
                    logger.debug(f"Profile {i+1}/{len(eligible_chars)}: {char.canonical_name}")

                    # F2: Extract summary evidence for this character
                    summary_evidence = None
                    if summary_evidence_extractor and summary_map:
                        try:
                            # Check if this character is the narrator
                            is_char_narrator = (
                                narrator_detected and char.canonical_name == narrator_detected
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
                            # Store for post-profile correction pass
                            _char_summary_evidence_store[char.canonical_name] = summary_evidence
                        except Exception as e:
                            logger.warning(
                                f"F2: Summary evidence extraction failed for {char.canonical_name}: {e}"
                            )

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
                        logger.warning(
                            f"F3: Moral valence classification failed for {char.canonical_name}: {e}"
                        )

                    # Generate profile with enhanced context
                    profile, evidence, confidence, appearance, personality, voice_guidance, relationships = (
                        self._generate_character_profile(
                            profile_llm,
                            char,
                            doc.text,
                            chapter_map=chapter_map,
                            summary_evidence=summary_evidence,
                            moral_valence=moral_valence,
                            all_character_names=all_character_names,
                            character_descriptions=character_descriptions_map,
                            narrator_name=narrator_detected if not getattr(char, "is_narrator", False) else None,
                        )
                    )

                    # Validate appearance.summary: if it contains no physical descriptor words,
                    # it's likely narrative text or a misextraction — reset to "unknown".
                    # This is a universal invariant: physical descriptions must contain physical terms.
                    if appearance and isinstance(appearance, dict):
                        _summary = appearance.get("summary", "")
                        if _summary and _summary.lower() != "unknown" and len(_summary) > 80:
                            _phys_terms = {
                                "tall", "short", "thin", "slim", "fat", "stout", "heavy",
                                "build", "built", "hair", "eye", "brow", "face", "chin",
                                "cheek", "skin", "complexion", "young", "old", "aged",
                                "blonde", "dark", "fair", "lean", "broad", "lanky",
                                "muscular", "athletic", "handsome", "beautiful", "plain",
                                "pale", "tan", "tanned", "wrinkle", "figure", "slender",
                                "stocky", "portly", "wiry", "gaunt", "robust", "frail",
                            }
                            _summary_lower = _summary.lower()
                            if not any(term in _summary_lower for term in _phys_terms):
                                logger.info(
                                    f"Appearance summary for {char.canonical_name} contains no "
                                    f"physical terms — resetting to unknown"
                                )
                                appearance["summary"] = "unknown"

                    # Store structured profile fields FIRST (F8: Simplified Character Output)
                    # These should be saved even if the profile description is empty,
                    # since the LLM may have extracted relationships/appearance/etc.
                    # but failed to generate the prose description.
                    char.appearance = appearance
                    char.personality = personality
                    char.voice_guidance = voice_guidance
                    # Always assign relationships, even if None (will use model default {})
                    # This ensures we don't silently skip assignment when LLM provides data
                    if relationships is not None:
                        # Remove self-references and vague fallback labels.
                        # Use substring containment for "colleague" and "acquaintance" because
                        # LLMs often output compound forms like "business colleague" or "social
                        # acquaintance" that don't start with the vague word but are equally vague.
                        char_name_lower = char.canonical_name.lower()
                        _VAGUE_CONTAINS = {"colleague", "acquaintance"}
                        _VAGUE_EXACT = {"associated", "associate", "unknown", "unrelated"}
                        relationships = {
                            k: v for k, v in relationships.items()
                            if k.lower() != char_name_lower
                            and isinstance(v, str)
                            and not any(vague in v.lower() for vague in _VAGUE_CONTAINS)
                            and v.lower() not in _VAGUE_EXACT
                        }
                        char.relationships = relationships
                        logger.info(f"Assigned relationships for {char.canonical_name}: {relationships}")

                    if profile:
                        char.description = profile
                        profile_count += 1

                        # Store evidence in character
                        char.profile_evidence = evidence
                        char.profile_confidence = confidence

                        # Track confidence distribution
                        if confidence >= 0.7:
                            high_conf_count += 1
                        elif confidence >= 0.4:
                            medium_conf_count += 1
                        else:
                            low_conf_count += 1
                            logger.warning(
                                f"Low confidence profile for {char.canonical_name}: {confidence:.2f}"
                            )
                    else:
                        char.profile_confidence = None
                        low_conf_count += 1

                    # Update real-time progress
                    self._metrics.update_stage_progress(
                        items_processed=i + 1,
                        high=high_conf_count,
                        medium=medium_conf_count,
                        low=low_conf_count,
                    )

                # Record metrics with confidence breakdown
                ctx.record_items(
                    total=len(eligible_chars),
                    high_confidence=high_conf_count,
                    medium_confidence=medium_conf_count,
                    low_confidence=low_conf_count,
                )

            print(
                f"   Generated {profile_count} profiles for {len(eligible_chars)} eligible characters"
            )


            # Post-processing corrections on pipeline characters (Phase A).
            # Extracts: narrator appearance injection, bidirectional relationships,
            # same-name contamination fix, death claim removal, description relationship correction.
            from .pipeline.character_profiling.post_corrections import PipelineCharacterCorrector
            corrector = PipelineCharacterCorrector(
                llm_client=profile_llm,
                evidence_store=_char_summary_evidence_store,
            )
            corrector.run_all(pipeline_char_map.characters, doc.text)

            # Post-profile role correction: if a non-narrator "protagonist" character's
            # outgoing relationships are predominantly adversarial, relabel as "antagonist".
            # Universal invariant: characters described as having victims/captives are antagonists.
            # IMPORTANT: Only count labels where THIS character IS the aggressor (target is victim/
            # prisoner/prey). Do NOT count victim-of-others labels like "tormentor" or "captor" —
            # outgoing "tormentor" means "my target torments me", making me the VICTIM not aggressor.
            _OUTGOING_AGGRESSOR_LABELS_EARLY = {
                "victim", "prisoner", "captive", "subordinate", "prey",
                "servant", "slave", "subject", "hostage", "pawn",
            }
            _INCOMING_AGGRESSOR_LABELS_EARLY = {
                "tormentor", "captor", "oppressor", "persecutor", "jailer", "warden",
                "abuser", "enslaver", "tyrant", "predator", "antagonist", "villain",
            }
            for _rchar in pipeline_char_map.characters:
                if _rchar.role != "protagonist" or _rchar.is_narrator:
                    continue
                _rels = _rchar.relationships or {}
                # Check outgoing aggressor labels only (labels where the TARGET is the victim)
                _adversarial_count = sum(
                    1 for v in _rels.values()
                    if isinstance(v, str) and any(adv in v.lower() for adv in _OUTGOING_AGGRESSOR_LABELS_EARLY)
                )
                if _adversarial_count > 0 and _adversarial_count >= len(_rels) / 2:
                    _rchar.role = "antagonist"
                    logger.info(
                        f"Role corrected: '{_rchar.canonical_name}' protagonist→antagonist "
                        f"({_adversarial_count}/{len(_rels)} outgoing adversarial labels)"
                    )
                    continue
                # Check incoming adversarial labels: if OTHER characters label this character
                # adversarially, it is likely the antagonist even if its own outgoing labels
                # are mislabeled (e.g., LLM defaults to "colleague" for a captor→victim bond).
                # Universal invariant: a true antagonist will show adversarial signals in BOTH
                # directions — at least 1 outgoing adversarial label (they see some as adversaries)
                # AND at least 1 incoming adversarial label (others label them as tormentor/captor).
                _rchar_name_lower = _rchar.canonical_name.lower()
                _incoming_adversarial = 0
                for _other in pipeline_char_map.characters:
                    if _other.id == _rchar.id:
                        continue
                    for _rel_key, _rel_val in (_other.relationships or {}).items():
                        if _rel_key.lower() == _rchar_name_lower and isinstance(_rel_val, str):
                            if any(adv in _rel_val.lower() for adv in _INCOMING_AGGRESSOR_LABELS_EARLY):
                                _incoming_adversarial += 1
                if _incoming_adversarial >= 1 and _adversarial_count >= 1:
                    _rchar.role = "antagonist"
                    logger.info(
                        f"Role corrected: '{_rchar.canonical_name}' protagonist→antagonist "
                        f"({_adversarial_count} outgoing + {_incoming_adversarial} incoming adversarial labels)"
                    )

            # Direction-aware aggressor detection:
            # Relationship convention: relationships[target] = "what target is to me"
            # So outgoing "tormentor" means "my target is my tormentor" (I am the VICTIM).
            # Outgoing "victim" means "my target is my victim" (I am the AGGRESSOR).
            #
            # _OUTGOING_AGGRESSOR_LABELS: labels a character applies to their TARGETS that
            # reveal the character is the aggressor (the target is beneath/harmed by them).
            _OUTGOING_AGGRESSOR_LABELS = {
                "victim", "prisoner", "captive", "subordinate", "prey",
                "servant", "slave", "subject", "hostage", "pawn",
            }
            # _INCOMING_AGGRESSOR_LABELS: labels OTHER characters apply to describe THIS
            # character as an aggressor (others call them a tormentor, captor, etc.).
            _INCOMING_AGGRESSOR_LABELS = {
                "tormentor", "captor", "oppressor", "persecutor", "jailer", "warden",
                "abuser", "enslaver", "tyrant", "predator", "antagonist", "villain",
            }

            # False antagonist correction: if a character is labeled "antagonist" but has
            # zero direction-aware adversarial evidence, the LLM misclassified them.
            # Universal invariant: a true antagonist must have aggressor evidence from
            # at least one direction (outgoing labels showing they have victims, OR
            # incoming labels showing others call them the aggressor).
            for _rchar in pipeline_char_map.characters:
                if _rchar.role != "antagonist":
                    continue
                # Outgoing: does this character label any target as "victim", "prisoner", etc.?
                _own_adv = sum(
                    1 for v in (_rchar.relationships or {}).values()
                    if isinstance(v, str) and any(adv in v.lower() for adv in _OUTGOING_AGGRESSOR_LABELS)
                )
                _rchar_name_lower = _rchar.canonical_name.lower()
                # Incoming: do other characters label this character as "tormentor", "captor", etc.?
                _in_adv = sum(
                    1
                    for _other in pipeline_char_map.characters
                    if _other.id != _rchar.id
                    for _k, _v in (_other.relationships or {}).items()
                    if _k.lower() == _rchar_name_lower and isinstance(_v, str)
                    and any(adv in _v.lower() for adv in _INCOMING_AGGRESSOR_LABELS)
                )
                if _own_adv <= 1 and _in_adv == 0:
                    _rchar.role = "protagonist"
                    logger.info(
                        f"Role corrected: '{_rchar.canonical_name}' antagonist→protagonist "
                        f"(insufficient direction-aware adversarial evidence: outgoing={_own_adv}, incoming={_in_adv})"
                    )

            # Relationship consistency enforcement: if a confirmed antagonist has outgoing
            # "colleague" labels to protagonists but also has active adversarial labels to
            # other protagonists, the "colleague" labels are LLM fallbacks — replace them
            # with the dominant active adversarial label.
            # Also enforce the inverse: if a confirmed protagonist labels a confirmed
            # antagonist as "colleague" but other protagonists use an adversarial label for
            # the antagonist, replace "colleague" with the majority label.
            # Universal invariant: consistent power dynamics within a cast.
            _all_antagonists = [c for c in pipeline_char_map.characters if c.role == "antagonist"]
            # Include both "protagonist" and "main" roles — main-cast characters are
            # significant story participants and should have consistent adversarial labels
            # relative to antagonists, regardless of the exact role label.
            _all_protagonists = [
                c for c in pipeline_char_map.characters
                if c.role in ("protagonist", "main")
            ]
            for _ant in _all_antagonists:
                _ant_rels = _ant.relationships or {}
                # Collect antagonist's outgoing labels to protagonists
                _prot_names = {p.canonical_name.lower() for p in _all_protagonists}
                _ant_to_prot = {
                    k: v for k, v in _ant_rels.items()
                    if k.lower() in _prot_names and isinstance(v, str)
                }
                if not _ant_to_prot:
                    continue
                # Count outgoing aggressor labels vs "colleague" labels to protagonists.
                # Check both label sets: LLMs don't always follow direction conventions,
                # so an antagonist may use "tormentor" (normally incoming) for a protagonist.
                _all_adversarial = _OUTGOING_AGGRESSOR_LABELS | _INCOMING_AGGRESSOR_LABELS
                _active_labels = [
                    v for v in _ant_to_prot.values()
                    if any(a in v.lower() for a in _all_adversarial)
                ]
                _colleague_keys = [
                    k for k, v in _ant_to_prot.items()
                    if isinstance(v, str) and "colleague" in v.lower()
                    and not any(a in v.lower() for a in _OUTGOING_AGGRESSOR_LABELS)
                ]
                if len(_active_labels) >= 1 and _colleague_keys:
                    # Find the most common active adversarial label
                    from collections import Counter
                    _dominant = Counter(_active_labels).most_common(1)[0][0]
                    for _ck in _colleague_keys:
                        _ant.relationships[_ck] = _dominant
                        logger.info(
                            f"Relationship corrected: '{_ant.canonical_name}'→'{_ck}' "
                            f"'colleague'→'{_dominant}' (consistency with dominant active label)"
                        )

            # Inverse: protagonist→antagonist "colleague" corrected to majority label.
            for _ant in _all_antagonists:
                _ant_name_lower = _ant.canonical_name.lower()
                # Collect all protagonist outgoing labels toward this antagonist as (prot, label) pairs
                _prot_label_pairs = []
                for _prot in _all_protagonists:
                    for _k, _v in (_prot.relationships or {}).items():
                        if _k.lower() == _ant_name_lower and isinstance(_v, str):
                            _prot_label_pairs.append((_prot, _v))
                if not _prot_label_pairs:
                    continue
                # Protagonists' outgoing labels toward antagonist: "tormentor", "captor" etc.
                # = incoming aggressor evidence (protagonist calls antagonist the aggressor)
                _active_prot_labels = [
                    v for _, v in _prot_label_pairs
                    if any(a in v.lower() for a in _INCOMING_AGGRESSOR_LABELS)
                ]
                _colleague_prots = [
                    p for p, v in _prot_label_pairs
                    if "colleague" in v.lower() and not any(a in v.lower() for a in _INCOMING_AGGRESSOR_LABELS)
                ]
                if len(_active_prot_labels) >= 1 and _colleague_prots:
                    from collections import Counter
                    _dominant_inv = Counter(_active_prot_labels).most_common(1)[0][0]
                    for _cp in _colleague_prots:
                        for _k in list((_cp.relationships or {}).keys()):
                            if _k.lower() == _ant_name_lower:
                                _cp.relationships[_k] = _dominant_inv
                                logger.info(
                                    f"Relationship corrected: '{_cp.canonical_name}'→'{_k}' "
                                    f"'colleague'→'{_dominant_inv}' (consistency with majority protagonist label)"
                                )

        # Post-profile self-relationship filter: remove any relationship where the key
        # matches the character's own canonical name (artifact of duplicate characters
        # being profiled together).
        for _schar in pipeline_char_map.characters:
            if not _schar.relationships:
                continue
            _self_keys = [
                k for k in _schar.relationships
                if k.lower() == _schar.canonical_name.lower()
            ]
            for _sk in _self_keys:
                del _schar.relationships[_sk]
                logger.info(
                    f"Removed self-relationship '{_sk}' from '{_schar.canonical_name}'"
                )

        # Step 5: Pronunciation Guide (skip if already done in parallel mode)
        if pron_map is None:
            print("🗣️  Generating pronunciation guide...")
            self._write_progress(
                "Pronunciation Guide",
                (
                    self._get_agent_config("pronunciation").model
                    if self._get_agent_config("pronunciation")
                    else None
                ),
            )
            # Use agent-specific LLM client for pronunciation
            pron_llm = self._get_agent_llm_client("pronunciation")
            with self._metrics.stage("Pronunciation Guide") as ctx:
                # Set model info from LLM client config (before running)
                if pron_llm and pron_llm.config:
                    ctx.set_model(pron_llm.config.model, pron_llm.config.provider)

                pronunciation_pipeline = PronunciationGuidePipeline(
                    llm_client=pron_llm,
                    progress_callback=self._wrap_progress("Pronunciation Guide"),
                )
                pron_map, _ = pronunciation_pipeline.run(
                    doc.text, chapter_map, pipeline_char_map, source_file=str(file_path)
                )

                # Filter out front/back matter entries
                pron_map = self._filter_pronunciation_by_body(pron_map, doc)

                # Record confidence metrics
                high = sum(1 for p in pron_map.entries if p.confidence >= 0.7)
                medium = sum(1 for p in pron_map.entries if 0.4 <= p.confidence < 0.7)
                low = sum(1 for p in pron_map.entries if p.confidence < 0.4) + len(
                    pron_map.low_confidence_entries
                )
                ctx.record_items(
                    total=len(pron_map.entries),
                    high_confidence=high,
                    medium_confidence=medium,
                    low_confidence=low,
                )

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
            print("   Overview generated successfully")

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
                    print(
                        f"   Confirmed narrator: {narrator_info.narrator_name} ({narrator_info.narrative_style})"
                    )
                else:
                    print("   No definitive narrator identified from plot summary")
        else:
            print("   Skipped (no plot summary or LLM)")

        # Step 6.6: Narrator fallback — use overview's narrative_style as authoritative signal.
        # When all LLM-based narrator detection fails (summaries are written in 3rd person so
        # the LLM keeps returning "third-person" pov), the overview generator may have already
        # correctly identified the narrative style (e.g., "first-person retrospective").
        # Universal invariant: if the overview says "first-person" and no narrator has been
        # detected, pick the least-name-mentioned character who appears in the plot summary —
        # first-person narrators use "I" instead of their name, so they have anomalously few
        # direct name mentions compared to characters they narrate about.
        if not any(getattr(c, "is_narrator", False) for c in pipeline_char_map.characters):
            _ov_ps = overview.get("plot_summary") if overview else None
            if isinstance(_ov_ps, dict):
                _ov_style = _ov_ps.get("narrative_style", "")
                _ov_text = _ov_ps.get("plot_summary", "")
                if "first-person" in _ov_style.lower() and _ov_text and pipeline_char_map.characters:
                    _plot_lower_66 = _ov_text.lower()
                    _narrator_candidates_66 = [
                        c for c in pipeline_char_map.characters
                        if c.canonical_name.lower() in _plot_lower_66
                        and (getattr(c, "mention_count", 0) or 0) >= 20
                    ]
                    if _narrator_candidates_66:
                        _narrator_pick_66 = min(
                            _narrator_candidates_66,
                            key=lambda c: getattr(c, "mention_count", 0) or 0,
                        )
                        _narrator_pick_66.is_narrator = True
                        _narrator_pick_66.narrative_role = "First-Person Narrator"
                        if getattr(_narrator_pick_66, "role", None) in ("supporting", "minor"):
                            _narrator_pick_66.role = "protagonist"
                        narrator_detected = _narrator_pick_66.canonical_name
                        logger.info(
                            f"Step 6.6: Narrator fallback via overview narrative_style "
                            f"'{_ov_style}' → '{_narrator_pick_66.canonical_name}' "
                            f"(mention_count={getattr(_narrator_pick_66, 'mention_count', 0)})"
                        )
                        print(
                            f"   Narrator identified from overview style: "
                            f"{_narrator_pick_66.canonical_name}"
                        )

        # Step 6.9: Comprehensive "the narrator" → narrator name substitution.
        # First-person narrators are often referred to as "the narrator" in LLM-generated text
        # (chapter summaries, active_characters, plot summary, personality profiles).
        # Now that narrator_detected is finalized, replace all such references with the
        # narrator's actual name for consistency across all output fields.
        if narrator_detected:
            # Bug A fix: find the actual narrator character's canonical_name instead of using
            # narrator_detected which may be the generic placeholder "the narrator".
            _nn_final = narrator_detected
            for _nc in pipeline_char_map.characters:
                if getattr(_nc, 'is_narrator', False) and _nc.canonical_name:
                    _nn_final = _nc.canonical_name
                    break
            # Only substitute if we have a real name (not just "the narrator")
            _nn_pat = re.compile(r'\bthe (?:\S+ )?narrator\b', re.IGNORECASE)
            _do_sub = _nn_final.lower() not in ('the narrator', 'narrator', '')

            if _do_sub:
                # 1. Chapter summary texts (already partly done earlier, but may have missed some)
                # 2. active_characters lists in chapter summaries
                if summary_map:
                    for _sum in summary_map.summaries:
                        if _sum.summary and 'narrator' in _sum.summary.lower():
                            _sum.summary = _nn_pat.sub(_nn_final, _sum.summary)
                        if hasattr(_sum, 'active_characters'):
                            if _sum.active_characters:
                                _sum.active_characters = [
                                    _nn_final if re.match(r'^the narrator$', ac, re.IGNORECASE) else ac
                                    for ac in _sum.active_characters
                                ]
                            # Also inject narrator into active_characters if absent
                            _ac_lower = [ac.lower() for ac in (_sum.active_characters or [])]
                            if _nn_final.lower() not in _ac_lower:
                                _sum.active_characters = list(_sum.active_characters or []) + [_nn_final]

                # 3. Plot summary text in overview
                # Bug B fix: plot_summary may be a nested dict {"plot_summary": "...", "themes": [...], ...}
                if overview:
                    _ps_obj = overview.get('plot_summary')
                    if isinstance(_ps_obj, dict):
                        _ps_inner = _ps_obj.get('plot_summary')
                        if isinstance(_ps_inner, str) and 'narrator' in _ps_inner.lower():
                            _ps_obj['plot_summary'] = _nn_pat.sub(_nn_final, _ps_inner)
                    elif isinstance(_ps_obj, str) and 'narrator' in _ps_obj.lower():
                        overview['plot_summary'] = _nn_pat.sub(_nn_final, _ps_obj)

                # 4. All characters' personality summary, evidence, and descriptions
                # (Gorrister/Benny descriptions also reference "the narrator" and need substitution)
                for _char in pipeline_char_map.characters:
                    if isinstance(getattr(_char, 'personality', None), dict):
                        _psumm = _char.personality.get('summary', '')
                        if _psumm and 'narrator' in _psumm.lower():
                            _char.personality['summary'] = _nn_pat.sub(_nn_final, _psumm)
                    if hasattr(_char, 'profile_evidence') and _char.profile_evidence:
                        for _i, _ev in enumerate(_char.profile_evidence):
                            if isinstance(_ev, str) and 'narrator' in _ev.lower():
                                _char.profile_evidence[_i] = _nn_pat.sub(_nn_final, _ev)
                            elif isinstance(_ev, dict) and 'statement' in _ev:
                                if 'narrator' in _ev['statement'].lower():
                                    _ev['statement'] = _nn_pat.sub(_nn_final, _ev['statement'])
                    if hasattr(_char, 'description') and _char.description:
                        if 'narrator' in _char.description.lower():
                            _char.description = _nn_pat.sub(_nn_final, _char.description)

        # Step 7: Convert to AnalysisResult
        print("📦 Building analysis result...")

        # Convert chapters to StructuralElements
        structure = self._convert_chapters(chapter_map, summary_map, self.words_per_minute)

        # Convert characters
        characters = self._convert_characters(pipeline_char_map)


        # Plot-summary safety net: add characters mentioned in plot_summary but missed
        # by the extraction pipeline. Handles all-caps acronym names (e.g. "AM", "HAL")
        # that spaCy NER and the LLM extraction pipeline routinely fail to capture.
        # Must run BEFORE OutputCharacterCorrector so safety-net characters are included.
        if overview:
            safety_net_chars = self._plot_summary_safety_net(characters, overview, doc.text)

            # LLM-profile safety-net characters so they get real personality/appearance
            # fields instead of empty stubs.  The safety net only handles *detection*;
            # profiling is the LLM's job.
            if safety_net_chars:
                profile_llm = self._get_agent_llm_client("characters") or llm
                if profile_llm:
                    all_char_names = [c.canonical_name for c in characters]
                    for new_char in safety_net_chars:
                        print(f"   Profiling safety-net character: {new_char.canonical_name}")
                        profile, evidence, confidence, appearance, personality, voice_guidance, relationships = (
                            self._generate_character_profile(
                                profile_llm, new_char, doc.text,
                                all_character_names=all_char_names,
                                narrator_name=narrator_detected if not getattr(new_char, "is_narrator", False) else None,
                            )
                        )
                        if personality:
                            new_char.personality = personality
                        if appearance:
                            new_char.appearance = appearance
                        if voice_guidance:
                            new_char.voice_guidance = voice_guidance
                        if relationships:
                            new_char_name_lower = new_char.canonical_name.lower()
                            relationships = {
                                k: v for k, v in relationships.items()
                                if k.lower() != new_char_name_lower
                            }
                            new_char.relationships = relationships
                        if profile:
                            new_char.descriptions.append(
                                CharacterDescription(
                                    text=profile,
                                    source_position=0,
                                    confidence=ConfidenceLevel.LLM_REFINED,
                                )
                            )

        # Post-processing corrections on output characters (Phase B).
        # Extracts: final narrator appearance injection, deterministic age extraction,
        # same-person relationship fix, text-based relationship verification, gender consistency.
        # Runs AFTER safety net so all characters (including safety-net additions) are corrected.
        from .pipeline.character_profiling.post_corrections import OutputCharacterCorrector
        profile_llm = self._get_agent_llm_client("characters") or llm
        _phase_b_summaries = (
            [s.summary for s in summary_map.summaries if s and s.summary]
            if summary_map else []
        )
        OutputCharacterCorrector(llm_client=profile_llm).run_all(
            characters, doc.text, chapter_summaries=_phase_b_summaries
        )

        # Post-Phase-B role validation: re-apply false-antagonist check and colleague
        # replacement using final (Phase-B-corrected) relationships. Phase B may refine
        # relationship labels in ways that would have changed the pipeline-level role
        # corrections. Running again on output characters ensures the final JSON reflects
        # accurate roles based on the most complete relationship data available.
        # Universal invariant: a true antagonist has outgoing aggressor labels (labels
        # their targets as victims/prisoners) OR incoming aggressor labels (others call
        # them tormentor/captor). A character with neither should be protagonist.
        _PHSB_OUTGOING = {"victim", "prisoner", "captive", "subordinate", "prey",
                          "servant", "slave", "subject", "hostage", "pawn"}
        _PHSB_INCOMING = {"tormentor", "captor", "oppressor", "persecutor", "jailer",
                          "warden", "abuser", "enslaver", "tyrant", "predator",
                          "antagonist", "villain"}
        for _fc in characters:
            if _fc.role != "antagonist" or getattr(_fc, "is_narrator", False):
                continue
            _fc_own = sum(
                1 for v in (_fc.relationships or {}).values()
                if isinstance(v, str) and any(a in v.lower() for a in _PHSB_OUTGOING)
                and "fellow" not in v.lower()  # "fellow victim/prisoner" = co-victim, not aggressor
            )
            _fc_name = _fc.canonical_name.lower()
            _fc_inc = sum(
                1 for oc in characters
                if oc.id != _fc.id
                for k, v in (oc.relationships or {}).items()
                if k.lower() == _fc_name and isinstance(v, str)
                and any(a in v.lower() for a in _PHSB_INCOMING)
            )
            if _fc_own <= 2 and _fc_inc == 0:
                _fc.role = "protagonist"
                logger.info(
                    f"Post-Phase-B role corrected: '{_fc.canonical_name}' "
                    f"antagonist→protagonist (outgoing={_fc_own}, incoming={_fc_inc})"
                )

        # Colleague replacement on output characters: build antagonist/protagonist lists
        # AFTER the role fix above so corrected roles are used.
        _phsb_antagonists = [c for c in characters if c.role == "antagonist"]
        _phsb_protagonists = [c for c in characters if c.role in ("protagonist", "main")]
        _phsb_all_adv = _PHSB_OUTGOING | _PHSB_INCOMING
        for _bant in _phsb_antagonists:
            _bprot_names = {p.canonical_name.lower() for p in _phsb_protagonists}
            _bant_to_prot = {
                k: v for k, v in (_bant.relationships or {}).items()
                if k.lower() in _bprot_names and isinstance(v, str)
            }
            if not _bant_to_prot:
                continue
            _bactive = [
                v for v in _bant_to_prot.values()
                if any(a in v.lower() for a in _phsb_all_adv) and "colleague" not in v.lower()
            ]
            _bcols = [k for k, v in _bant_to_prot.items() if "colleague" in v.lower()]
            if _bactive and _bcols:
                from collections import Counter
                _bdom = Counter(_bactive).most_common(1)[0][0]
                for _bck in _bcols:
                    _bant.relationships[_bck] = _bdom
                    logger.info(
                        f"Post-Phase-B: '{_bant.canonical_name}'→'{_bck}' "
                        f"'colleague'→'{_bdom}'"
                    )
        # Inverse: protagonist→antagonist "colleague" corrected using majority label.
        for _bant in _phsb_antagonists:
            _bant_name = _bant.canonical_name.lower()
            _bprot_pairs = [
                (p, v)
                for p in _phsb_protagonists
                for k, v in (p.relationships or {}).items()
                if k.lower() == _bant_name and isinstance(v, str)
            ]
            _bactive_inv = [
                v for _, v in _bprot_pairs
                if any(a in v.lower() for a in _PHSB_INCOMING)
            ]
            _bcol_prots = [p for p, v in _bprot_pairs if "colleague" in v.lower()]
            if _bactive_inv and _bcol_prots:
                from collections import Counter
                _bdom_inv = Counter(_bactive_inv).most_common(1)[0][0]
                for _bcp in _bcol_prots:
                    for _bk in list((_bcp.relationships or {}).keys()):
                        if _bk.lower() == _bant_name:
                            _bcp.relationships[_bk] = _bdom_inv
                            logger.info(
                                f"Post-Phase-B: '{_bcp.canonical_name}'→'{_bk}' "
                                f"'colleague'→'{_bdom_inv}'"
                            )

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
                low_confidence.append(
                    f"Structure: {elem.type.value} at position {elem.start_position}"
                )
        for char in characters:
            if char.confidence == ConfidenceLevel.LOW:
                low_confidence.append(f"Character: {char.canonical_name}")

        # Convert glossary if present
        glossary_map = self._convert_glossary(doc)

        # Build consensus log from collected votes
        from .pipeline.consensus_collector import consensus_collector
        from .models import ConsensusLog
        consensus_log_data = consensus_collector.build_log()
        consensus_log = ConsensusLog(**consensus_log_data) if consensus_log_data.get("total_votes", 0) > 0 else None

        # Determine narrator_character_id from the converted output characters
        _narrator_char_id = None
        for _oc in characters:
            if getattr(_oc, 'is_narrator', False):
                _narrator_char_id = _oc.id
                break

        result = AnalysisResult(
            metadata=metadata,
            structure=structure,
            characters=characters,
            pronunciations=pronunciations,
            glossary=glossary_map,
            overview=overview,
            raw_text=doc.text,
            consensus_log=consensus_log,
            warnings=warnings,
            low_confidence_items=low_confidence,
            narrator_character_id=_narrator_char_id,
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
            if re.search(r"_\d{3}$", self.output_dir.name):
                # GUI-style: output/gatsby_001 - use directly
                run_dir = self.output_dir
            else:
                # CLI-style: output/ - create timestamped subdirectory
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                run_dir = self.output_dir / f"{file_path.stem}_{timestamp}"
            run_dir.mkdir(parents=True, exist_ok=True)

            # Save quality report
            quality_path = run_dir / "quality.md"
            quality_path.write_text(self._last_quality_report.to_markdown(), encoding="utf-8")

            # Copy log files to per-run directory for debugging
            import shutil

            log_dir = Path.home() / ".audiobook-prep"

            # Copy pipeline log if it exists
            pipeline_log = log_dir / "pipeline.log"
            if pipeline_log.exists():
                shutil.copy(pipeline_log, run_dir / "pipeline.log")

            # Copy LLM log if it exists
            llm_log = log_dir / "llm.log"
            if llm_log.exists():
                shutil.copy(llm_log, run_dir / "llm.log")

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
        output_dir = self.output_dir or Path("output")
        output_dir.mkdir(parents=True, exist_ok=True)
        progress_file = output_dir / "PROGRESS.json"
        try:
            import json
            from datetime import datetime

            # Get cumulative token counts from metrics
            input_tokens = 0
            output_tokens = 0
            llm_calls = 0
            items_processed = 0
            items_total = None
            avg_latency_ms = 0.0
            last_latency_ms = 0.0

            if self._metrics:
                # Sum completed stages
                for s in self._metrics._stages:
                    input_tokens += s.tokens_prompt
                    output_tokens += s.tokens_completion
                    llm_calls += s.llm_calls

                # Add current stage (if any)
                if self._metrics._current_context:
                    ctx_metrics = self._metrics._current_context._metrics
                    input_tokens += ctx_metrics.tokens_prompt
                    output_tokens += ctx_metrics.tokens_completion
                    llm_calls += ctx_metrics.llm_calls
                    items_processed = ctx_metrics.items_processed
                    items_total = ctx_metrics.items_total
                    last_latency_ms = ctx_metrics.last_latency_ms
                    avg_latency_ms = ctx_metrics.avg_latency_ms

                # Also check stage info for real-time items progress
                stage_info = self._metrics._current_stage_info
                if stage_info.get("items_processed"):
                    items_processed = stage_info["items_processed"]
                if stage_info.get("items_total"):
                    items_total = stage_info["items_total"]

            progress_data = {
                "stage": stage,
                "model": model,
                "timestamp": datetime.now().isoformat(),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "llm_calls": llm_calls,
                "items_processed": items_processed,
                "items_total": items_total,
                "avg_latency_ms": round(avg_latency_ms, 1),
                "last_latency_ms": round(last_latency_ms, 1),
            }
            with open(progress_file, "w") as f:
                json.dump(progress_data, f)
        except Exception:
            pass  # Non-critical, don't fail analysis if progress write fails

    def _wrap_progress(self, stage: str) -> Callable[[str, int, int], None]:
        """Wrap progress callback with stage prefix and metrics updates."""
        # Get model for this stage
        stage_model = None
        if self._metrics and self._metrics._current_context:
            stage_model = self._metrics._current_context._metrics.model_used

        def wrapped(substage: str, current: int, total: int):
            # Update metrics (always, for real-time progress tracking)
            self._metrics.update_stage_progress(items_processed=current, items_total=total)

            # Update PROGRESS.json for real-time monitoring
            self._write_progress(stage, stage_model)

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
        s = re.sub(r'^\s*\{?\s*"profile"\s*:\s*"?', "", s)

        # Remove trailing JSON: ", "evidence": [...] etc
        s = re.sub(r'"?\s*,?\s*"(evidence|confidence|limitations)"\s*:.*$', "", s, flags=re.DOTALL)

        # Unescape JSON string escapes
        s = s.replace('\\"', '"').replace("\\n", "\n").replace("\\t", " ")

        # Remove remaining JSON structural characters
        s = re.sub(r"[{}\[\]]", "", s)

        # Clean up whitespace
        s = " ".join(s.split())

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
        all_character_names: Optional[list[str]] = None,
        character_descriptions: Optional[dict[str, str]] = None,
        narrator_name: Optional[str] = None,
    ) -> tuple[str, list[dict], float, Optional[dict], Optional[dict], Optional[dict], Optional[dict]]:
        """Generate prose profile for a character using LLM with evidence grounding.

        Args:
            llm: LLM client for generation
            character: Character to profile
            full_text: Full document text
            chapter_map: Chapter boundaries (optional)
            summary_evidence: F2 - Evidence extracted from chapter summaries (optional)
            moral_valence: F3 - Moral valence classification result (optional)
            all_character_names: List of all character names in the story (for relationship extraction)

        Returns:
            tuple: (profile_text, evidence_list, confidence_score, appearance, personality, voice_guidance, relationships)
                evidence_list: List of dicts with 'statement', 'quote', 'position'
                confidence_score: 0.0-1.0 based on evidence quality
                appearance: Dict with appearance data or None
                personality: Dict with personality data or None
                voice_guidance: Dict with voice guidance data or None
                relationships: Dict with character relationships or None
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

            # Build set of ALL character names to filter substring matches
            # This prevents "John" from matching "John Donaldson"
            all_names_set = set()
            if all_character_names:
                for n in all_character_names:
                    if isinstance(n, str) and n.strip():
                        all_names_set.add(n.lower().strip())

            positions: set[int] = set()
            for name in names:
                # Allow flexible whitespace for multi-word names (e.g., "De Lacey")
                escaped = re.escape(name).replace(r"\ ", r"\s+")
                pattern = rf"\b{escaped}\b"
                for m in re.finditer(pattern, full_text, flags=re.IGNORECASE):
                    pos = m.start()

                    # Filter out matches that are part of a longer character name OR
                    # that refer to a different character with a similar name
                    # Extract surrounding context to check if this is a substring match
                    if all_names_set:
                        # Get broader context for disambiguation
                        context_start = max(0, pos - 200)
                        context_end = min(len(full_text), pos + len(name) + 200)
                        context = full_text[context_start:context_end]

                        # Check if this match is part of a longer name in our character list
                        is_substring_match = False
                        refers_to_other_character = False

                        for other_name in all_names_set:
                            if other_name != name.lower().strip():
                                # Check if the matched text is followed by more name parts
                                # that would make it match a longer character name
                                if other_name.startswith(name.lower().strip() + " "):
                                    # This is a potential substring (e.g., "John" in "John Donaldson")
                                    # Check if the text after the match contains the rest of the longer name
                                    remaining = other_name[len(name):].strip()
                                    text_after_match = full_text[pos + len(name):pos + len(name) + len(remaining) + 5]
                                    # Use flexible whitespace matching
                                    remaining_pattern = r"\s+" + re.escape(remaining)
                                    if re.match(remaining_pattern, text_after_match, re.IGNORECASE):
                                        is_substring_match = True
                                        break

                                # UNIVERSAL DISAMBIGUATION: Check if this match refers to the OTHER character
                                # This handles cases like father/son sharing a name
                                # If we're searching for "John" and "John Donaldson" also exists:
                                # - Check if context contains parts of the longer name (e.g., "Donaldson")
                                # - Check for relationship markers (e.g., "father", "his father", "the elder")
                                if other_name.startswith(name.lower().strip() + " "):
                                    # Extract the distinguishing part (e.g., "Donaldson" from "John Donaldson")
                                    distinguishing_parts = other_name[len(name):].strip().split()

                                    # Check if any distinguishing part appears in the context
                                    for part in distinguishing_parts:
                                        if len(part) >= 3:  # Avoid single-char matches
                                            # Check if the distinguishing part appears in the context
                                            # Use word boundaries to avoid false positives
                                            part_pattern = r"\b" + re.escape(part) + r"\b"
                                            if re.search(part_pattern, context, re.IGNORECASE):
                                                refers_to_other_character = True
                                                break

                                    # Check for family relationship markers that suggest this refers to the longer name
                                    # Universal markers: "father", "his father", "the elder", "senior", "Sr."
                                    family_markers = [
                                        r"\b(his|her|their)\s+(father|mother|parent)",
                                        r"\bfather\b",
                                        r"\bmother\b",
                                        r"\b(the\s+)?(elder|older)\b",
                                        r"\b(Sr\.|Senior)\b"
                                    ]
                                    for marker_pattern in family_markers:
                                        if re.search(marker_pattern, context, re.IGNORECASE):
                                            # If we find a family marker near a simple name match,
                                            # and a fuller name exists, this likely refers to the fuller name
                                            refers_to_other_character = True
                                            break

                        if not is_substring_match and not refers_to_other_character:
                            positions.add(pos)
                    else:
                        # No filtering data available, include all matches
                        positions.add(pos)

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

        # Special case: First-person narrators often have few name mentions but "speak" throughout
        # If this is a narrator with very few mentions, sample broadly across the text
        is_narrator = getattr(character, "is_narrator", False)
        if is_narrator and total_mentions < 3:
            logger.info(
                f"Narrator {character.canonical_name} has only {total_mentions} name mentions - sampling broadly across text"
            )
            # Sample 10 passages evenly distributed through the text
            text_len = len(full_text)
            num_samples = 10
            step = text_len // (num_samples + 1)

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
                    position=step * (i + 1),
                    chapter_index=_chapter_for_pos(step * (i + 1)),
                    context="",
                    in_dialogue=False,
                )
                for i in range(num_samples)
            ]
            total_mentions = len(all_mentions)
            logger.info(f"Generated {total_mentions} synthetic mentions for narrator profile")

        # For narrators with named mentions, ensure early text is captured.
        # First-person narrators often describe themselves near the start ("I am an elderly man..."),
        # but that passage may not be near any named mention of the narrator.
        # Search for actual first-person physical self-descriptions rather than using a fixed position.
        if is_narrator and all_mentions:
            def _chapter_for_pos_early(pos: int) -> int:
                if chapter_map is None:
                    return 0
                for ch in chapter_map.chapters:
                    if ch.start_position <= pos < ch.end_position:
                        return ch.index
                return 0

            # Search the first portion of the text for first-person physical self-descriptions.
            # This captures patterns like "I am an elderly, grizzled man" near the narrative start.
            # Universal: works for any first-person narrator who describes themselves physically.
            _self_desc_re = re.compile(
                r'\bI[\s.…]{0,20}(?:am|was)\b[^\n]{0,300}?\b(?:man|woman|person|elderly|old|young|tall|short|thin|small|lean|stout|fat|grizzled|bald|gray|grey|large)\b',
                re.IGNORECASE,
            )
            # Search in first 20% of text or 10000 chars, whichever is larger
            search_end = min(len(full_text), max(10000, len(full_text) // 5))
            narrator_desc_pos = 100  # Fallback position if no self-description found
            for _m in _self_desc_re.finditer(full_text[:search_end]):
                narrator_desc_pos = _m.start()
                logger.info(
                    f"Narrator '{character.canonical_name}': found first-person self-description "
                    f"at position {narrator_desc_pos}: {_m.group()[:120]!r}"
                )
                break  # Use first match only

            early_mention = CharacterMention(
                text=getattr(character, "canonical_name", "") or "",
                position=narrator_desc_pos,
                chapter_index=_chapter_for_pos_early(narrator_desc_pos),
                context="",
                in_dialogue=False,
            )
            all_mentions = [early_mention] + list(all_mentions)
            total_mentions = len(all_mentions)
            logger.info(
                f"Narrator '{character.canonical_name}': prepended synthetic mention at position "
                f"{narrator_desc_pos} to capture self-description"
            )

        # Sample up to 10 mentions, distributed across the narrative
        if total_mentions <= 10:
            sampled_mentions = all_mentions
        else:
            # ALWAYS include the first mention (where physical descriptions typically appear)
            first_mention = all_mentions[0]

            # Divide remaining mentions into thirds (early, middle, late) and sample from each
            remaining_mentions = all_mentions[1:]  # Exclude first mention
            third = len(remaining_mentions) // 3
            early = remaining_mentions[:third]
            middle = remaining_mentions[third : 2 * third]
            late = remaining_mentions[2 * third :]

            # Sample 3 from each third (9 total + 1 first mention = 10 total)
            import random

            sampled_mentions = [first_mention]  # Start with first mention
            sampled_mentions.extend(random.sample(early, min(3, len(early))))
            sampled_mentions.extend(random.sample(middle, min(3, len(middle))))
            sampled_mentions.extend(random.sample(late, min(3, len(late))))

            # Sort by position to maintain chronological order in context
            sampled_mentions.sort(key=lambda m: m.position)
            logger.info(
                f"Profile sampling for {character.canonical_name}: "
                f"Included first mention at position {first_mention.position}, "
                f"plus {len(sampled_mentions)-1} sampled mentions"
            )

        # Same-name disambiguation: filter mentions that refer to related characters.
        # When character A's name is a substring of character B's name (e.g., "John" ⊂ "John Donaldson"),
        # mentions of A where B's full name appears in nearby context likely refer to B, not A.
        # This prevents father/son or other same-name confusion in profile generation.
        _char_name_filter = getattr(character, "canonical_name", "")
        if _char_name_filter and all_character_names and sampled_mentions:
            _related_pats = [
                re.compile(r'\b' + re.escape(other) + r'\b', re.IGNORECASE)
                for other in all_character_names
                if (other != _char_name_filter
                    and _char_name_filter.lower() in other.lower()
                    and len(other) > len(_char_name_filter))
            ]
            if _related_pats:
                _filtered = [
                    m for m in sampled_mentions
                    if not any(
                        pat.search(
                            full_text[max(0, m.position - 500):min(len(full_text), m.position + 500)]
                        )
                        for pat in _related_pats
                    )
                ]
                if len(_filtered) >= 3:
                    logger.info(
                        f"Profile dedup for '{_char_name_filter}': filtered "
                        f"{len(sampled_mentions) - len(_filtered)} mention(s) referring to "
                        f"longer-named characters"
                    )
                    sampled_mentions = _filtered

        # Gather context snippets from sampled mentions
        contexts = []
        mention_positions = []
        for mention in sampled_mentions:
            start = max(0, mention.position - 400)  # Wide context to capture nearby descriptions
            end = min(len(full_text), mention.position + 400)
            snippet = full_text[start:end].strip()
            # Clean up partial words at boundaries
            if start > 0:
                snippet = "..." + snippet.split(" ", 1)[-1] if " " in snippet else snippet
            if end < len(full_text):
                snippet = snippet.rsplit(" ", 1)[0] + "..." if " " in snippet else snippet
            contexts.append(
                {"text": snippet, "position": mention.position, "chapter": mention.chapter_index}
            )
            mention_positions.append(mention.position)

        if not contexts:
            logger.warning(f"No context available for {character.canonical_name}")
            return "", [], 0.0, None, None, None, None

        context_text = "\n\n".join(
            [
                f"[Context {i+1}, Chapter {c['chapter']}, Position {c['position']}]:\n{c['text']}"
                for i, c in enumerate(contexts)
            ]
        )

        # Check if this character is the narrator
        narrator_note = ""
        is_narrator_char = hasattr(character, "is_narrator") and character.is_narrator
        if is_narrator_char:
            narrator_note = f"\n\nNOTE: This character is the NARRATOR of the story ({character.narrative_role or 'First-person narrator'}). IMPORTANT: Any first-person descriptions in the text (\"I am...\", \"I was...\", \"I look...\", \"I have...\") describe THIS character's appearance and traits. Look for self-descriptions where the narrator characterizes themselves physically or emotionally."
        elif narrator_name:
            # Non-narrator character in a first-person narrative.
            # The narrator uses "I" throughout — those descriptions belong to the narrator, not here.
            narrator_note = (
                f"\n\nNOTE: This is a first-person narrative. The narrator is \"{narrator_name}\"."
                f" All \"I\" descriptions in the text (\"I put on...\", \"I was wearing...\", \"I went...\")"
                f" belong to {narrator_name}, NOT to {character.canonical_name}."
                f" For {character.canonical_name}, only extract details explicitly attributed to them"
                f" using their name or third-person pronouns (\"He...\", \"She...\", \"{character.canonical_name}...\")."
            )

        # Build character disambiguation context for same-name characters
        # This helps when multiple characters share name components (e.g., "John" and "John Donaldson")
        disambiguation_note = ""
        char_canonical = getattr(character, "canonical_name", "")
        if char_canonical and all_character_names:
            # Check if there's another character whose name contains or is contained in this character's name
            related_names = []
            for other_name in all_character_names:
                if other_name != char_canonical:
                    # Check for name overlap (one is substring of the other)
                    if (char_canonical.lower() in other_name.lower() or
                        other_name.lower() in char_canonical.lower()):
                        related_names.append(other_name)

            if related_names:
                # Extract distinguishing information about the other characters from extraction data
                other_char_info = []
                for rname in related_names:
                    desc_for_other = ""
                    if character_descriptions and rname in character_descriptions:
                        desc_for_other = character_descriptions[rname]
                    if desc_for_other:
                        other_char_info.append(f'- "{rname}": {desc_for_other}')
                    else:
                        other_char_info.append(f'- "{rname}": (a different character)')

                related_list = ", ".join(f'"{name}"' for name in related_names)
                other_info_text = "\n".join(other_char_info)
                disambiguation_note = f"""

CHARACTER DISAMBIGUATION (CRITICAL):
This story has multiple characters with similar names: "{char_canonical}" and {related_list}.
You are analyzing "{char_canonical}" ONLY.

The other character(s) with similar names:
{other_info_text}

When attributing traits, events, or quotes:
1. Only use evidence that clearly describes "{char_canonical}", not the other character(s) above
2. If a passage matches traits listed for the other character(s), EXCLUDE it from your analysis of "{char_canonical}"
3. Passages mentioning the full name of another character refer to that other character, not "{char_canonical}"

IMPORTANT: If the available evidence is ambiguous, report only what is clearly specific to "{char_canonical}"."""

        # Build character names list for relationship extraction
        character_names_text = ""
        if all_character_names:
            names_list = ", ".join(f'"{name}"' for name in all_character_names if name != character.canonical_name)
            if names_list:
                character_names_text = f"""

CHARACTERS IN THIS STORY:
The following characters appear in this story: {names_list}
If you identify a relationship with any of these characters, use these exact names as keys in the relationships dict."""

        # F2: Build summary evidence section if available
        summary_evidence_text = ""
        if summary_evidence and summary_evidence.evidence:
            evidence_lines = []
            for ev in summary_evidence.evidence[:5]:  # Limit to top 5 items
                evidence_lines.append(f'- Chapter {ev.chapter_index}: "{ev.statement}"')
            if evidence_lines:
                summary_evidence_text = f"""

ADDITIONAL CONTEXT FROM CHAPTER SUMMARIES (Feature F2):
The following information about this character was extracted from chapter summaries:
{chr(10).join(evidence_lines)}

Use this summary evidence to enrich your profile, but prioritize direct text quotes as primary evidence.
When the summary evidence explicitly states a relationship (e.g., "X is Y's father", "X and Y are friends"), include it in relationships."""

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
Your analysis should reflect the character's full arc, not just their initial appearance.{narrator_note}{disambiguation_note}{character_names_text}{summary_evidence_text}{moral_valence_constraint}

Text Evidence:
{context_text}

CRITICAL REQUIREMENTS:
1. Make ONLY claims that are directly supported by the provided text
2. For each claim, provide the exact quote that supports it
3. Consider how the character develops or changes throughout the narrative (if evident from the samples)
4. If the text doesn't provide enough information about a trait or relationship, DO NOT invent it
5. Write from a narrator's practical perspective — balanced, actionable descriptions without literary criticism or moral judgments

Return a JSON response matching this example format exactly:

```json
{{
  "profile": "A brief 2-3 sentence overview based on provided evidence.",
  "appearance": {{
    "summary": "Physical description: height, build, coloring, age markers, facial features, clothing, bearing — any that appear in text",
    "age_indication": "exact age phrase from text if stated (e.g., '22 years old', 'thirty-five'), otherwise young/middle-aged/elderly/unknown",
    "distinguishing_features": ["specific feature from text", "another feature"]
  }},
  "personality": {{
    "summary": "Brief personality summary",
    "traits": ["trait1", "trait2"],
    "temperament": "calm/volatile/melancholic/cheerful/etc or unknown",
    "emotional_range": "Brief note on emotional expression",
    "speech_patterns": ["catchphrase or verbal tic if present", "dialect feature", "speech style"]
  }},
  "voice_guidance": {{
    "suggested_tone": "authoritative/gentle/aggressive/etc based on dialogue",
    "dialect_notes": "Any accent, regional speech, or class markers",
    "verbal_tics": ["repeated phrase", "speech pattern"],
    "formality_level": "formal/informal/moderate",
    "example_quotes": ["quote1", "quote2"]
  }},
  "relationships": {{
    "character_name_1": "relationship label (e.g., 'romantic interest', 'close friend', 'rival', 'mentor', 'employer', 'parent', 'child', 'sibling', 'cousin', 'spouse')"
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
- You MUST include ALL fields in your response: profile, appearance, personality, voice_guidance, relationships, evidence, confidence, limitations
- If information is not available in the text, use "unknown" or empty arrays [] for that field
- Do NOT omit any field - every field must be present even if the value is "unknown" or []
- Do NOT invent details - only use what's explicitly or clearly implied in the provided text
- For appearance: Search the text snippets carefully for physical descriptions (height, build, coloring, hair, eyes, age, clothing, bearing). If found, describe them. If truly absent, use {{"summary": "unknown", "age_indication": "unknown", "distinguishing_features": []}}
- For personality: Only include if you can infer from behavior, otherwise use {{"summary": "unknown", "traits": [], "temperament": "unknown", "emotional_range": "unknown", "speech_patterns": []}}
- For voice_guidance: Base on actual dialogue if present. For verbal_tics, copy any recurring phrases or speech patterns from the character's dialogue (e.g., a habitual greeting, distinctive pronunciation, pet phrase). If no dialogue is present, use {{"suggested_tone": "unknown", "dialect_notes": "unknown", "verbal_tics": [], "formality_level": "moderate", "example_quotes": []}}
- Return ONLY valid JSON matching the above structure. No other text.

RELATIONSHIPS EXTRACTION:
Include ONLY relationships where the provided text or summary evidence EXPLICITLY describes how these characters interact or relate to each other.
Use familial labels (parent, child, sibling, cousin, spouse, brother, sister) only when the text explicitly uses these words.
Use other labels ("close friend", "rival", "mentor", "employer", "enemy", "creator", "creation", "captor", "prisoner", "tormentor", "victim") only with direct textual support.
If two characters merely appear in the same context without explicit relationship words, OMIT them from the relationships dict entirely.
Do NOT use "acquaintance", "associated", "colleague", or "unknown" — omit instead."""

        # Helper to parse JSON from LLM response
        def _parse_json_blob(s: str):
            try:
                return json.loads(s)
            except json.JSONDecodeError:
                # Try to extract JSON object from text with better heuristics
                # Look for first { and last } at the same nesting level
                brace_count = 0
                start_idx = -1
                end_idx = -1

                for i, char in enumerate(s):
                    if char == '{':
                        if brace_count == 0:
                            start_idx = i
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0 and start_idx != -1:
                            end_idx = i
                            # Found a complete JSON object, try to parse it
                            try:
                                return json.loads(s[start_idx : end_idx + 1])
                            except json.JSONDecodeError:
                                # Continue searching for another potential JSON object
                                start_idx = -1

                # Fallback to simple extraction if balanced parsing failed
                start = s.find("{")
                end = s.rfind("}")
                if start != -1 and end != -1 and end > start:
                    try:
                        return json.loads(s[start : end + 1])
                    except json.JSONDecodeError:
                        return None
                return None

        # Retry loop: try up to 3 times on LLM errors (increased for profile generation robustness)
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                # Character profiles are consumed as JSON; enforce JSON mode at the provider level when possible
                # (e.g., Ollama `format: "json"`) to reduce malformed output and truncation artifacts.
                response = llm.query(prompt, system=CHARACTER_PROFILE_SYSTEM, json_mode=True)
                if response.success:
                    # Clean up any thinking tags or extra formatting
                    content = response.content.strip()

                    # Strip thinking tags (common in reasoning models like DeepSeek-R1, QwQ, Qwen3)
                    # These can appear as <think>...</think> or <thinking>...</thinking>
                    import re as re_module
                    content = re_module.sub(r'<think>.*?</think>', '', content, flags=re_module.DOTALL)
                    content = re_module.sub(r'<thinking>.*?</thinking>', '', content, flags=re_module.DOTALL)

                    # Try to extract JSON if wrapped in markdown code blocks
                    # Handle multiple code blocks by taking the largest one (likely the JSON)
                    if "```json" in content:
                        # Extract all ```json blocks and take the longest one
                        json_blocks = []
                        remaining = content
                        while "```json" in remaining:
                            parts = remaining.split("```json", 1)
                            if len(parts) > 1 and "```" in parts[1]:
                                block = parts[1].split("```", 1)[0].strip()
                                json_blocks.append(block)
                                remaining = parts[1].split("```", 1)[1] if len(parts[1].split("```", 1)) > 1 else ""
                            else:
                                break
                        if json_blocks:
                            content = max(json_blocks, key=len)  # Take the longest JSON block
                    elif "```" in content:
                        # Try generic code blocks
                        code_blocks = []
                        parts = content.split("```")
                        for i in range(1, len(parts), 2):  # Odd indices are inside code blocks
                            code_blocks.append(parts[i].strip())
                        if code_blocks:
                            # Take the longest block that looks like JSON (starts with {)
                            json_like_blocks = [b for b in code_blocks if b.startswith("{")]
                            if json_like_blocks:
                                content = max(json_like_blocks, key=len)
                            else:
                                content = max(code_blocks, key=len)

                    try:
                        result = _parse_json_blob(content)
                        if result is None:
                            raise json.JSONDecodeError("Could not parse JSON", content, 0)

                        # DEBUG: Log the complete parsed result to diagnose relationship extraction
                        logger.info(f"RAW LLM response for {character.canonical_name}: {json.dumps(result, indent=2)[:500]}...")

                        # Check if "profile" field itself contains JSON (double-encoded or malformed)
                        profile = result.get("profile", "")
                        if profile:
                            # Case 1: Profile starts with JSON structure
                            if profile.startswith("{") or profile.startswith("["):
                                logger.warning(
                                    f"Character profile for {character.canonical_name} starts with JSON, attempting to parse"
                                )
                                try:
                                    nested = json.loads(profile)
                                    if isinstance(nested, dict) and "profile" in nested:
                                        # Double-encoded JSON
                                        profile = nested["profile"]
                                        logger.info(
                                            f"Successfully extracted profile from nested JSON for {character.canonical_name}"
                                        )
                                except json.JSONDecodeError:
                                    # Not valid JSON - try to extract readable text
                                    logger.warning(
                                        f"Nested JSON parse failed for {character.canonical_name}, extracting text"
                                    )
                                    profile = self._extract_text_from_malformed_json(profile)
                                    if not profile:
                                        logger.warning(
                                            f"Could not salvage text from malformed profile for {character.canonical_name}"
                                        )

                            # Case 2: Profile contains embedded JSON patterns (malformed response)
                            # Look for patterns like: `text", "appearance": {` or similar
                            elif (
                                '", "appearance":' in profile
                                or '", "personality":' in profile
                                or '", "voice_guidance":' in profile
                            ):
                                logger.warning(
                                    f"Character profile for {character.canonical_name} contains embedded JSON fields, attempting to extract"
                                )

                                # Try to extract the leading text as the profile description
                                import re

                                # Find where the JSON structure starts (first occurrence of structured field)
                                json_start_match = re.search(
                                    r'",\s*"(appearance|personality|voice_guidance)":', profile
                                )
                                if json_start_match:
                                    # Extract the text before the JSON structure
                                    text_part = profile[: json_start_match.start()]
                                    # Remove any leading/trailing JSON artifacts
                                    text_part = text_part.strip(" \"'{")

                                    # Try to reconstruct and parse the embedded JSON
                                    # The LLM returned malformed JSON like:
                                    #   "appearance": "summary": "unknown", "age": "unknown", "personality": ...
                                    # Should be:
                                    #   "appearance": {"summary": "unknown", "age": "unknown"}, "personality": ...
                                    json_part = profile[
                                        json_start_match.start() + 2 :
                                    ]  # Skip the leading quote+comma

                                    # Strategy: Insert { after main field names, and } before the next main field
                                    # Main fields are: appearance, personality, voice_guidance
                                    main_fields = ["appearance", "personality", "voice_guidance", "relationships"]

                                    # Step 1: Add opening brace after each main field name
                                    for field in main_fields:
                                        json_part = re.sub(
                                            rf'"{field}":\s*(?!\{{)',  # Match field name NOT followed by {
                                            f'"{field}": {{',
                                            json_part,
                                        )

                                    # Step 2: Add closing brace before each subsequent main field (and at end)
                                    # Work backwards to avoid index shifting
                                    for i, field in enumerate(main_fields):
                                        if i < len(main_fields) - 1:
                                            next_field = main_fields[i + 1]
                                            # Insert } before next_field if not already there
                                            json_part = re.sub(
                                                rf'(?<!\}})\s*,\s*("{next_field}":)',
                                                r"}, \1",
                                                json_part,
                                            )

                                    # Attempt to wrap it in braces to make valid JSON
                                    reconstructed = "{" + json_part

                                    # Close any unclosed braces at the end
                                    # Count opening and closing braces
                                    open_count = reconstructed.count("{")
                                    close_count = reconstructed.count("}")
                                    if open_count > close_count:
                                        reconstructed += "}" * (open_count - close_count)

                                    try:
                                        parsed_fields = json.loads(reconstructed)

                                        # If we successfully parsed structured fields, use them
                                        if parsed_fields.get("appearance") and not result.get(
                                            "appearance"
                                        ):
                                            result["appearance"] = parsed_fields["appearance"]
                                            logger.info(
                                                f"Extracted appearance from embedded JSON for {character.canonical_name}"
                                            )

                                        if parsed_fields.get("personality") and not result.get(
                                            "personality"
                                        ):
                                            result["personality"] = parsed_fields["personality"]
                                            logger.info(
                                                f"Extracted personality from embedded JSON for {character.canonical_name}"
                                            )

                                        if parsed_fields.get("voice_guidance") and not result.get(
                                            "voice_guidance"
                                        ):
                                            result["voice_guidance"] = parsed_fields[
                                                "voice_guidance"
                                            ]
                                            logger.info(
                                                f"Extracted voice_guidance from embedded JSON for {character.canonical_name}"
                                            )

                                        # Use the cleaned text as profile
                                        profile = text_part
                                        logger.info(
                                            f"Successfully extracted profile text and structured fields from malformed response for {character.canonical_name}"
                                        )

                                    except json.JSONDecodeError as e:
                                        # Reconstruction failed, fall back to text extraction
                                        logger.warning(
                                            f"Could not reconstruct JSON from embedded fields for {character.canonical_name}: {e}"
                                        )
                                        profile = self._extract_text_from_malformed_json(profile)
                                        if not profile:
                                            logger.warning(
                                                f"Could not salvage text from malformed profile for {character.canonical_name}"
                                            )
                                else:
                                    # Pattern detected but no clear boundary, fall back to text extraction
                                    profile = self._extract_text_from_malformed_json(profile)
                                    if not profile:
                                        logger.warning(
                                            f"Could not salvage text from malformed profile for {character.canonical_name}"
                                        )

                        evidence = result.get("evidence", [])
                        confidence = float(result.get("confidence", 0.5))

                        # Extract structured fields (F8: Simplified Character Output)
                        appearance = result.get("appearance")
                        personality = result.get("personality")
                        voice_guidance = result.get("voice_guidance")
                        relationships = result.get("relationships")

                        # Enforce the prompt's "omit instead" instruction for vague labels.
                        # The LLM sometimes ignores the prohibition and uses "associated"/
                        # "acquaintance"/"unknown" as fallbacks. Post-filter them here so
                        # the secondary call can replace with specific labels (or omit cleanly).
                        _VAGUE_CONTAINS_2 = {"colleague", "acquaintance"}
                        _VAGUE_EXACT_2 = {"associated", "associate", "unknown", "unrelated"}
                        if isinstance(relationships, dict):
                            relationships = {k: v for k, v in relationships.items()
                                             if isinstance(v, str)
                                             and not any(vague in v.lower() for vague in _VAGUE_CONTAINS_2)
                                             and v.lower() not in _VAGUE_EXACT_2}
                            # Empty dict (not None) — triggers secondary call below for specific labels

                        # Debug logging
                        logger.info(
                            f"Profile generation for {character.canonical_name}: "
                            f"keys={list(result.keys())}, "
                            f"appearance={'present' if appearance else 'missing'}, "
                            f"personality={'present' if personality else 'missing'}, "
                            f"voice_guidance={'present' if voice_guidance else 'missing'}, "
                            f"relationships={'present' if relationships else 'missing'}"
                        )

                        # DETAILED DEBUG: Log the actual structured field contents
                        if appearance:
                            logger.info(f"  appearance content: {json.dumps(appearance)}")
                        if personality:
                            logger.info(f"  personality content: {json.dumps(personality)}")
                        if voice_guidance:
                            logger.info(f"  voice_guidance content: {json.dumps(voice_guidance)}")
                        # ALWAYS log relationships, even if empty, to diagnose extraction issues
                        logger.info(f"  relationships RAW from LLM: {json.dumps(relationships)} (type: {type(relationships).__name__})")

                        # Preserve structured fields even if they contain "unknown" values
                        def _clean_dict(d):
                            if not isinstance(d, dict):
                                return None
                            # Return the dict as-is, even if empty
                            # Empty dict {} means "we looked but found nothing" (valid)
                            # None means "we didn't look" or "parsing failed"
                            # We keep "unknown" values and empty dicts because they indicate
                            # the LLM responded but found no evidence (which is valid information)
                            return d

                        appearance = _clean_dict(appearance)
                        personality = _clean_dict(personality)
                        voice_guidance = _clean_dict(voice_guidance)
                        # Don't clean relationships - preserve whatever LLM returned (even empty {})
                        # Empty dict {} is valid (means no relationships found in text)
                        # Non-dict values get converted to None for safety
                        if not isinstance(relationships, dict):
                            relationships = None

                        # DEBUG: Log after cleaning
                        logger.info(
                            f"After _clean_dict for {character.canonical_name}: "
                            f"appearance={'present' if appearance else 'NULL'}, "
                            f"personality={'present' if personality else 'NULL'}, "
                            f"voice_guidance={'present' if voice_guidance else 'NULL'}, "
                            f"relationships={json.dumps(relationships) if relationships else 'NULL (from _clean_dict)'}"
                        )

                        # Regex fallback: If ALL structured fields are None, try per-field regex
                        # extraction from raw LLM content as a last resort before the secondary LLM call
                        if appearance is None and personality is None and voice_guidance is None:
                            import re as _re_f4
                            raw_for_recovery = json.dumps(result) if result else ""
                            # Also check the profile text itself
                            if profile and len(profile) > len(raw_for_recovery):
                                raw_for_recovery = profile

                            for field_name in ["appearance", "personality", "voice_guidance", "relationships"]:
                                # Try to find a JSON object associated with this field name
                                pattern = rf'"{field_name}"\s*:\s*(\{{[^}}]*\}})'
                                match = _re_f4.search(pattern, raw_for_recovery, _re_f4.DOTALL)
                                if match:
                                    try:
                                        parsed = json.loads(match.group(1))
                                        if field_name == "appearance" and appearance is None:
                                            appearance = parsed
                                        elif field_name == "personality" and personality is None:
                                            personality = parsed
                                        elif field_name == "voice_guidance" and voice_guidance is None:
                                            voice_guidance = parsed
                                        elif field_name == "relationships" and relationships is None:
                                            relationships = parsed
                                        logger.info(
                                            f"Recovered {field_name} via regex fallback for {character.canonical_name}"
                                        )
                                    except json.JSONDecodeError:
                                        pass

                        # Fallback: If LLM didn't provide structured fields or they're mostly empty,
                        # OR the profile description is empty, attempt a secondary LLM call.
                        # When profile is empty, use the context_text from the book as source.
                        has_minimal_data = (
                            (not appearance or (isinstance(appearance, dict) and not any(v for v in appearance.values() if v and v != "unknown")))
                            and (not personality or (isinstance(personality, dict) and not any(v for v in personality.values() if v and v != "unknown")))
                            and (not voice_guidance or (isinstance(voice_guidance, dict) and not any(v for v in voice_guidance.values() if v and v != "unknown")))
                        )
                        needs_secondary_call = contexts and (has_minimal_data or not profile or not relationships)
                        if needs_secondary_call:
                            log_reason = "profile is empty" if not profile else ("relationships empty after filtering" if not relationships else "structured fields missing")
                            logger.warning(
                                f"Secondary LLM call for {character.canonical_name}: {log_reason}"
                            )
                            # When profile is empty, use the original text evidence as source.
                            # When profile exists but fields are unknown, structure the profile text.
                            use_context = not profile or len(profile) < 20
                            source_text = context_text if use_context else profile
                            source_label = "text evidence from the book" if use_context else "character profile"
                            structuring_prompt = f"""Extract character information for "{character.canonical_name}" from the following {source_label}.

{source_label.capitalize()}:
{source_text}

Return a JSON object with these fields:
{{
  "profile": "2-3 sentence overview of this character based only on the text above",
  "appearance": {{"summary": "Physical description if mentioned", "age_indication": "exact age phrase from text if stated, otherwise young/middle-aged/elderly/unknown", "distinguishing_features": []}},
  "personality": {{"summary": "Personality traits and behavior", "traits": ["trait1", "trait2"], "temperament": "overall temperament"}},
  "voice_guidance": {{"suggested_tone": "tone based on character's manner", "formality_level": "formal/informal/moderate"}},
  "relationships": {{"character_name": "relationship_type (e.g., friend, rival, mentor, spouse, parent, child, sibling, guardian, ward, employer, enemy)"}},
  "evidence": [{{"statement": "claim made about character", "quote": "supporting quote from text", "position": 0}}]
}}

Only use information explicitly present in the text above. If a category has no information, use "unknown", [], or {{}}.
Do NOT use "associated", "acquaintance", or "unknown" as relationship labels — omit those entries instead.
Return ONLY the JSON object."""

                            try:
                                struct_response = llm.query(
                                    structuring_prompt,
                                    system="You are a helpful assistant that structures character information.",
                                    json_mode=True,
                                )
                                if struct_response.success:
                                    struct_content = struct_response.content.strip()
                                    if "```json" in struct_content:
                                        struct_content = (
                                            struct_content.split("```json")[1]
                                            .split("```")[0]
                                            .strip()
                                        )
                                    elif "```" in struct_content:
                                        struct_content = (
                                            struct_content.split("```")[1].split("```")[0].strip()
                                        )

                                    struct_result = json.loads(struct_content)
                                    appearance = _clean_dict(struct_result.get("appearance"))
                                    personality = _clean_dict(struct_result.get("personality"))
                                    voice_guidance = _clean_dict(
                                        struct_result.get("voice_guidance")
                                    )
                                    # Only use secondary relationships if primary call produced none.
                                    # The secondary prompt has weaker context so it tends to produce
                                    # incorrect relationship labels when the primary already has data.
                                    secondary_relationships = _clean_dict(struct_result.get("relationships"))
                                    if isinstance(secondary_relationships, dict):
                                        _VAGUE_REL_LABELS = {"colleague", "acquaintance", "associated", "associate", "unknown", "unrelated"}
                                        secondary_relationships = {k: v for k, v in secondary_relationships.items()
                                                                    if isinstance(v, str) and not any(vague in v.lower() for vague in {"colleague", "acquaintance"}) and v.lower() not in _VAGUE_REL_LABELS}
                                    if secondary_relationships and not relationships:
                                        relationships = secondary_relationships
                                    # If primary profile was empty, use the one generated by secondary call
                                    if not profile and struct_result.get("profile"):
                                        profile = struct_result["profile"]
                                        logger.info(
                                            f"Generated profile description from secondary call for {character.canonical_name}"
                                        )
                                    # Extract evidence from secondary call if primary didn't provide it
                                    if not evidence:
                                        secondary_evidence = struct_result.get("evidence", [])
                                        if isinstance(secondary_evidence, list):
                                            evidence = secondary_evidence
                                            logger.info(
                                                f"Extracted {len(evidence)} evidence items from secondary call for {character.canonical_name}"
                                            )
                                    logger.warning(
                                        f"Successfully structured profile for {character.canonical_name}"
                                    )
                            except Exception as e:
                                logger.warning(
                                    f"Failed to structure profile for {character.canonical_name}: {e}"
                                )

                        # Validate evidence structure
                        validated_evidence = []
                        for ev in evidence:
                            if isinstance(ev, dict) and "statement" in ev and "quote" in ev:
                                validated_evidence.append(
                                    {
                                        "statement": ev["statement"],
                                        "quote": ev["quote"],
                                        "position": ev.get("position", 0),
                                        "confidence": (
                                            "high"
                                            if confidence >= 0.7
                                            else "medium" if confidence >= 0.4 else "low"
                                        ),
                                    }
                                )

                        # If no valid evidence but we got a profile, mark as low confidence
                        if profile and not validated_evidence:
                            logger.warning(f"Profile for {character.canonical_name} lacks evidence")
                            confidence = min(confidence, 0.3)

                        # F9: Focused relationship extraction (second LLM call if needed)
                        # If relationships dict is empty/None but we have evidence and other characters exist,
                        # make a focused LLM call to extract just relationships from the evidence
                        if (not relationships or not isinstance(relationships, dict) or len(relationships) == 0) and validated_evidence and all_character_names:
                            logger.info(f"Attempting focused relationship extraction for {character.canonical_name}")
                            relationships = self._extract_relationships_from_evidence(
                                llm,
                                character.canonical_name,
                                validated_evidence,
                                all_character_names
                            )
                            if relationships:
                                logger.info(f"Focused extraction found {len(relationships)} relationships for {character.canonical_name}")

                        return (
                            profile,
                            validated_evidence,
                            confidence,
                            appearance,
                            personality,
                            voice_guidance,
                            relationships,
                        )

                    except json.JSONDecodeError as e:
                        logger.error(
                            f"Failed to parse JSON response for {character.canonical_name}: {e}"
                        )
                        logger.debug(f"Raw content (first 500 chars): {content[:500]}")
                        # Try to extract readable text from malformed response
                        salvaged = self._extract_text_from_malformed_json(content)
                        if salvaged:
                            logger.info(f"Salvaged profile text for {character.canonical_name}")
                            return salvaged, [], 0.3, None, None, None, None
                        return "", [], 0.0, None, None, None, None
                else:
                    # LLM returned error response
                    error_msg = getattr(response, "error", None) or "unknown error"
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
                        return "", [], 0.0, None, None, None, None

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

        return "", [], 0.0, None, None, None, None

    def _extract_relationships_from_evidence(
        self,
        llm: "LLMClient",
        character_name: str,
        evidence: list[dict],
        all_character_names: list[str]
    ) -> Optional[dict[str, str]]:
        """Extract character relationships using a focused second LLM call.

        This method is called when the main profile generation didn't populate
        the relationships dict, but evidence exists that may contain relationship info.

        Args:
            llm: LLM client for generation
            character_name: The character whose relationships we're extracting
            evidence: List of evidence dicts with 'statement' and 'quote' fields
            all_character_names: List of all character names in the story

        Returns:
            dict mapping character names to relationship descriptions, or None if extraction fails
        """
        import json
        import re as _re

        # Filter out the current character from the list
        other_characters = [name for name in all_character_names if name != character_name]
        if not other_characters:
            return None

        # Build a case-insensitive lookup for validation
        other_characters_lower = {name.lower(): name for name in other_characters}

        # Pre-scan evidence to annotate which other characters are mentioned in each item.
        # This makes relationships visible to the LLM even when names appear only in quotes.
        evidence_lines = []
        # Also track which characters were found in ANY evidence item (for programmatic fallback)
        chars_in_evidence: dict = {name: [] for name in other_characters}

        for ev in evidence[:10]:  # Limit to first 10 evidence items
            statement = ev.get('statement', '')
            quote = ev.get('quote', '')
            combined = f"{statement} {quote}"

            # Find which other characters appear in this evidence item
            mentioned = []
            for other_name in other_characters:
                # Check all words in the name individually (handles multi-word names)
                name_parts = [p for p in other_name.split() if len(p) >= 3]
                if any(part.lower() in combined.lower() for part in name_parts):
                    mentioned.append(other_name)
                    chars_in_evidence[other_name].append(statement[:80])

            evidence_lines.append(f"- {statement}")
            if quote:
                evidence_lines.append(f'  Quote: "{quote}"')
            if mentioned:
                evidence_lines.append(f"  [References: {', '.join(mentioned)}]")

        evidence_text = "\n".join(evidence_lines)
        other_chars_text = ", ".join(f'"{name}"' for name in other_characters)

        # Build an explicit summary of which characters appear in evidence
        mention_summary_lines = []
        for name, stmts in chars_in_evidence.items():
            if stmts:
                mention_summary_lines.append(f'"{name}" is referenced in {len(stmts)} evidence item(s)')
        mention_summary = "\n".join(mention_summary_lines) if mention_summary_lines else "(none detected)"

        prompt = f"""Extract character relationships from the evidence below.

CHARACTER: \"{character_name}\"

OTHER CHARACTERS IN STORY: {other_chars_text}

EVIDENCE ABOUT {character_name}:
{evidence_text}

CHARACTER REFERENCES FOUND IN EVIDENCE:
{mention_summary}

Task: For each character listed in \"CHARACTER REFERENCES FOUND IN EVIDENCE\", describe the relationship between \"{character_name}\" and that character based on the evidence.

RULES:
- Use the EXACT character names from \"OTHER CHARACTERS IN STORY\" as JSON keys
- Relationship descriptions should be brief (2-5 words): "target of revenge", "rival", "victim", "enemy", "manipulation tool", etc.
- Base descriptions on statements and quotes in the evidence above

Return ONLY a JSON object:
{{
  "character_name_1": "relationship_description",
  "character_name_2": "relationship_description"
}}

Example: {{"Alice": "murder victim", "Bob": "rival connoisseur"}}
"""

        try:
            response = llm.query(
                prompt,
                system="You are a literary analyst extracting character relationships. Return only valid JSON.",
                json_mode=True,
                temperature=0.3,
                max_tokens=512
            )

            if not response or not response.content:
                logger.warning(f"F9: Empty response from relationship extraction for {character_name}")
            else:
                content = response.content.strip()
                # Strip markdown code fences if present
                if content.startswith("```json"):
                    content = content.split("```json", 1)[1].split("```")[0].strip()
                elif content.startswith("```"):
                    content = content.split("```", 1)[1].split("```")[0].strip()

                logger.info(f"F9 RAW LLM response for {character_name}: {content[:300]}")

                try:
                    relationships = json.loads(content)
                    if not isinstance(relationships, dict):
                        logger.warning(f"F9: Non-dict response for {character_name}: {type(relationships)}")
                    else:
                        # Validate with case-insensitive matching (LLM may vary case)
                        validated = {}
                        for char_name, rel_desc in relationships.items():
                            if char_name in other_characters:
                                validated[char_name] = rel_desc
                            elif char_name.lower() in other_characters_lower:
                                canonical = other_characters_lower[char_name.lower()]
                                validated[canonical] = rel_desc
                                logger.info(f"F9: Case-normalized '{char_name}' -> '{canonical}'")
                            else:
                                logger.debug(f"F9: Ignoring unknown key '{char_name}' for {character_name}")

                        logger.info(f"F9: validated relationships for {character_name}: {json.dumps(validated)}")
                        if validated:
                            return validated
                except json.JSONDecodeError as e:
                    logger.warning(f"F9: JSON parse error for {character_name}: {e}, content={content[:200]}")

        except Exception as e:
            logger.warning(f"F9: LLM call failed for {character_name}: {e}")

        # Programmatic fallback: if LLM failed, build relationships from evidence name mentions.
        # Deterministic and universal: any character mentioned in another's evidence
        # has a relationship with them (at minimum, they interact in the narrative).
        programmatic = {}
        for name, stmts in chars_in_evidence.items():
            if stmts:
                # Use the first statement that mentions this character as the relationship hint
                desc = stmts[0]
                # Strip the current character's name from the description to focus on the relationship
                desc = _re.sub(_re.escape(character_name), "", desc, flags=_re.IGNORECASE).strip()
                desc = desc.strip(" .,")
                if len(desc) > 50:
                    desc = desc[:47] + "..."
                programmatic[name] = desc if desc else "mentioned in narrative"
        if programmatic:
            logger.info(f"F9: Using programmatic fallback for {character_name}: {json.dumps(programmatic)}")
            return programmatic

        return None

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
            logger.info(
                f"First-person narrative detected ({first_person_count} pronouns in opening)"
            )

            # NEW: Calculate per-character first-person pronoun scores
            # Check which character's contexts contain first-person pronouns
            character_scores = []

            for char in characters:
                if not hasattr(char, "mentions") or not char.mentions:
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

                character_scores.append(
                    {
                        "character": char,
                        "pronoun_count": pronoun_count,
                        "density": density,
                        "mention_count": char.mention_count,
                    }
                )

                logger.debug(
                    f"Narrator scoring: {char.canonical_name} - "
                    f"{pronoun_count} pronouns in contexts, density={density:.2f}, "
                    f"mentions={char.mention_count}"
                )

            # Sort by pronoun density (primary) and mention count (tiebreaker)
            character_scores.sort(key=lambda x: (x["density"], x["mention_count"]), reverse=True)

            if character_scores and character_scores[0]["density"] > 5.0:
                # Narrator should have significant first-person pronoun usage in their contexts
                narrator = character_scores[0]["character"]
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

        # CRITICAL FIX: If V2 character extraction already set narrator flags, don't override them
        # V2 has more sophisticated narrator detection that runs during character extraction
        if any(char.is_narrator for char in characters):
            logger.info("Skipping V1 narrator re-detection - narrator already set by V2 pipeline")
            return

        narrator_lower = narrator_info.narrator_name.lower().strip()

        # CRITICAL: Clear narrator flag from ALL characters UNCONDITIONALLY
        # This ensures only one character is marked as narrator
        # Previous bug: only cleared if is_narrator was True, which left stale flags
        for char in characters:
            char.is_narrator = False
            logger.debug(f"Cleared narrator flag from {char.canonical_name}")

        # Now mark the correct narrator
        for char in characters:
            # Check canonical name (case-insensitive, whitespace-normalized)
            if char.canonical_name.lower().strip() == narrator_lower:
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

            # Check aliases (case-insensitive, whitespace-normalized)
            for alias in char.aliases:
                if alias.lower().strip() == narrator_lower:
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

                    logger.info(
                        f"Marked {char.canonical_name} as narrator (matched alias: {alias})"
                    )
                    return

        logger.warning(f"Narrator '{narrator_info.narrator_name}' not found in character list")

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
            (getattr(c, "mention_count", 0) for c in char_map.characters), default=10
        )

        # Find narrator and boost their effective importance
        for char in char_map.characters:
            if char.canonical_name.lower() == narrator_name.lower():
                # Store original for reference
                original_mentions = getattr(char, "mention_count", 0)

                # Set effective mention count to match most-mentioned character
                char.effective_mention_count = max(max_mentions, original_mentions)

                # Ensure role is protagonist (already done in mark_narrator_in_characters,
                # but double-check here)
                if hasattr(char, "role") and char.role in ("supporting", "minor", None):
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
                    original_mentions = getattr(char, "mention_count", 0)
                    char.effective_mention_count = max(max_mentions, original_mentions)

                    if hasattr(char, "role") and char.role in ("supporting", "minor", None):
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

            elements.append(
                StructuralElement(
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
                )
            )

        return elements

    def _convert_characters(
        self,
        char_map: PipelineCharacterMap,
    ) -> list[OutputCharacter]:
        """Convert pipeline CharacterMap to list of OutputCharacter models."""
        characters = []

        for pc in char_map.characters:
            # Post-profiling evidence filter: discard characters that were profiled but
            # produced zero evidence citations. A real character always yields at least
            # one supporting quote; zero evidence indicates a false positive (e.g. an
            # exclamation captured by NER as a PERSON entity). This is a universal
            # invariant — applies to any book, any genre.
            # Exception 1: characters with significant mention counts (>5) are real
            # regardless of whether profile JSON parsing succeeded — a failed parse
            # can produce empty evidence for a genuine character (e.g. Nimdok).
            # Exception 2: main_cast characters (LLM-extracted and grounding-vetted)
            # are never discarded on this basis — empty evidence reflects a profile
            # generation failure, not a false positive. NER false positives
            # (exclamations, place names) come from supporting cast, not main_cast.
            # Exception 3: F6 reconciliation characters were explicitly listed in
            # LLM-generated chapter summaries as active characters — they are
            # definitively real. NER false positives never reach F6 (they don't
            # appear in LLM summaries). Discarding them here is always wrong.
            _is_f6_character = "chapter_summary_reconciliation" in getattr(
                pc, "supporting_strategies", []
            )
            if (
                hasattr(pc, "profile_evidence")
                and not pc.profile_evidence
                and not getattr(pc, "is_narrator", False)
                and getattr(pc, "mention_count", 0) <= 5
                and not pc.id.startswith("main_cast_")
                and not _is_f6_character
            ):
                logger.info(
                    f"Discarding '{pc.canonical_name}' — profiled with 0 evidence (false positive)"
                )
                continue

            # Map confidence - use profile confidence if available
            profile_conf = getattr(pc, "profile_confidence", None)
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
                descriptions.append(
                    CharacterDescription(
                        text=pc.description,
                        source_position=pc.mentions[0].position if pc.mentions else 0,
                        confidence=ConfidenceLevel.LLM_REFINED,
                    )
                )

            # Extract evidence from pipeline character
            evidence = getattr(pc, "profile_evidence", [])

            characters.append(
                OutputCharacter(
                    id=pc.id,
                    canonical_name=pc.canonical_name,
                    aliases=pc.aliases,
                    descriptions=descriptions,
                    first_appearance_chapter=pc.first_appearance_chapter,
                    mention_count=pc.mention_count,
                    confidence=confidence,
                    evidence=evidence,
                    is_narrator=getattr(pc, "is_narrator", False),
                    narrative_role=getattr(pc, "narrative_role", None),
                    appearance=getattr(pc, "appearance", None),
                    personality=getattr(pc, "personality", None),
                    voice_guidance=getattr(pc, "voice_guidance", None),
                    role=getattr(pc, "role", None),
                    relationships=getattr(pc, "relationships", {}),
                )
            )

        # Also add low confidence characters (no profiles generated for these)
        for pc in char_map.low_confidence_characters:
            characters.append(
                OutputCharacter(
                    id=pc.id,
                    canonical_name=pc.canonical_name,
                    aliases=pc.aliases,
                    first_appearance_chapter=pc.first_appearance_chapter,
                    mention_count=pc.mention_count,
                    confidence=ConfidenceLevel.LOW,
                    role=getattr(pc, "role", None),
                )
            )

        return characters

    def _plot_summary_safety_net(
        self,
        characters: list,
        overview: dict,
        source_text: str,
    ) -> list:
        """Universal safety net: add characters present in the plot summary but missed
        by the extraction pipeline.

        Targets all-caps acronym names (AM, HAL, VIKI, etc.) that spaCy NER and LLM
        extraction routinely fail to identify.  Works for any book where the summarizer
        correctly names a character but the extraction pipeline does not.

        Algorithm:
        1. Find all-caps words (2–10 chars) that appear 3+ times in the plot summary.
        2. Skip any that are already in the character list.
        3. Require at least one case-sensitive occurrence in the raw source text
           (prevents adding terms invented by the summarizer).
        4. Infer role from surrounding plot-summary context.
        5. Append a minimal Character entry so downstream HTML/JSON includes it.

        Returns:
            List of newly added OutputCharacter objects (empty if none added).
        """
        # Extract plot summary text
        plot_summary_obj = overview.get("plot_summary")
        if not plot_summary_obj:
            return []
        if isinstance(plot_summary_obj, dict):
            plot_summary_text = plot_summary_obj.get("plot_summary", "")
        else:
            plot_summary_text = str(plot_summary_obj)
        if not plot_summary_text or len(plot_summary_text) < 50:
            return []

        # Build set of all known names (canonical + aliases), lower-cased
        from collections import Counter
        known_lower: set[str] = set()
        for char in characters:
            known_lower.add(char.canonical_name.lower())
            for alias in (char.aliases or []):
                known_lower.add(alias.lower())

        # Find all-caps 2–10 char words in the plot summary
        counts: Counter = Counter()
        for m in re.finditer(r'\b([A-Z]{2,10})\b', plot_summary_text):
            name = m.group(1)
            if name.lower() not in known_lower:
                counts[name] += 1

        added_chars: list = []
        for name, count in counts.most_common():
            if count < 3:
                break  # Counter.most_common() is sorted descending

            # Require case-sensitive occurrence in raw source text (grounding)
            text_count = len(re.findall(r'\b' + re.escape(name) + r'\b', source_text))
            if text_count == 0:
                logger.info(
                    f"Plot summary safety net: '{name}' not found case-sensitively in source text, skipping"
                )
                continue

            # Infer role from surrounding plot-summary context
            contexts_lower = []
            contexts_original = []
            for m in re.finditer(r'\b' + re.escape(name) + r'\b', plot_summary_text):
                start = max(0, m.start() - 200)
                end = min(len(plot_summary_text), m.end() + 200)
                contexts_lower.append(plot_summary_text[start:end].lower())
                contexts_original.append(plot_summary_text[start:end])
            context_text = " ".join(contexts_lower)

            role = "supporting"
            if any(w in context_text for w in (
                "antagonist", "villain", "malevolent", "adversary", "evil",
                "sadistic", "hateful", "cruel", "torturer", "torment",
            )):
                role = "antagonist"
            elif any(w in context_text for w in ("protagonist", "narrator", "hero")):
                role = "protagonist"

            # Personality is left to the LLM profiling step that runs after the
            # safety net returns.  The safety net only handles *detection*.

            # Build relationships: any existing character mentioned in context.
            # Use a role-appropriate label instead of a generic placeholder.
            if role == "antagonist":
                rel_label = "adversary"
            elif role == "protagonist":
                rel_label = "ally"
            else:
                rel_label = "associate"
            known_names = {c.canonical_name for c in characters}
            relationships: dict = {}
            for other_name in known_names:
                if other_name != name and re.search(
                    r'\b' + re.escape(other_name) + r'\b', context_text, re.IGNORECASE
                ):
                    relationships[other_name] = rel_label

            new_char = OutputCharacter(
                id=f"plot_summary_{name.lower()}",
                canonical_name=name,
                role=role,
                confidence=ConfidenceLevel.MEDIUM,
                mention_count=text_count,
                relationships=relationships,
            )
            characters.append(new_char)
            added_chars.append(new_char)
            print(f"   Plot summary safety net: added '{name}' (role={role}, text mentions={text_count})")
            logger.info(
                f"Plot summary safety net: added '{name}' "
                f"(summary mentions={count}, text mentions={text_count}, role={role})"
            )

        if not added_chars:
            logger.info("Plot summary safety net: no missing characters found")

        return added_chars

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

            entries.append(
                PronunciationEntry(
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
                )
            )

        # Also add low confidence entries
        for pe in pron_map.low_confidence_entries:
            flag = flag_mapping.get(pe.flag_reason, ModelPronunciationFlag.UNKNOWN)

            entries.append(
                PronunciationEntry(
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
                )
            )

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

            entries.append(
                ModelGlossaryEntry(
                    term=ge.term,
                    definition=ge.definition,
                    position=ge.position,
                    confidence=confidence,
                )
            )

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
        result_dict = result.model_dump(exclude={"raw_text"})

        # Add analysis metadata
        result_dict["_analysis_metadata"] = {
            "analyzed_at": datetime.now().isoformat(),
            "analyzer_version": "0.2.0",
            "pipeline": "multi-agent",
            "llm_model": self.llm_model or "none",
            "llm_provider": self.llm_provider if self.llm_refine else "none",
            "analysis_duration_seconds": (
                round(self._last_analysis_duration, 1) if self._last_analysis_duration else None
            ),
        }

        # Add profiling data if available
        if self._last_profiling_report:
            result_dict["_profiling"] = self._last_profiling_report.to_dict()

        # Add configuration data for oracle loop auditing
        result_dict["_config"] = self._build_config_dict()

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result_dict, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Analysis saved to: {output_path}")
        return str(output_path)

    def _build_config_dict(self) -> dict:
        """
        Build configuration dictionary for oracle loop auditing.

        Captures all configuration that affects analysis quality:
        - Orchestrator settings (default model, provider, parallelism)
        - Per-agent configs (model, temperature, context length)
        - Tuning parameters (chunk sizes, overlaps)
        """
        config_dict = {
            "orchestrator": {
                "default_model": (
                    self.orchestrator_config.default_model
                    if self.orchestrator_config and self.orchestrator_config.default_model
                    else self.llm_model or "none"
                ),
                "default_provider": (
                    self.orchestrator_config.default_provider
                    if self.orchestrator_config and self.orchestrator_config.default_provider
                    else self.llm_provider if self.llm_refine else "none"
                ),
                "parallel_execution": (
                    self.orchestrator_config.parallel_execution
                    if self.orchestrator_config
                    else False
                ),
                "context_length": (
                    self.orchestrator_config.context_length
                    if self.orchestrator_config
                    else self.llm_context_length
                ),
            },
            "agents": {},
            "tuning": {},
        }

        # Capture per-agent configurations
        agent_names = ["structure", "characters", "summaries", "pronunciation"]
        for agent_name in agent_names:
            if self.orchestrator_config:
                agent_config = self.orchestrator_config.get_agent_config(agent_name)
                config_dict["agents"][agent_name] = {
                    "model": agent_config.model or self.llm_model or "default",
                    "provider": agent_config.provider,
                    "temperature": agent_config.temperature,
                    "context_length": agent_config.context_length,
                    "max_tokens": agent_config.max_tokens,
                    "think_mode": agent_config.think_mode,
                }
            else:
                # No orchestrator config - using defaults
                config_dict["agents"][agent_name] = {
                    "model": self.llm_model or "default",
                    "provider": self.llm_provider,
                    "temperature": 0.7,
                    "context_length": self.llm_context_length,
                    "max_tokens": 4096,
                    "think_mode": False,
                }

        # Capture tuning parameters
        if self.orchestrator_config and self.orchestrator_config.tuning:
            tuning = self.orchestrator_config.tuning
            config_dict["tuning"] = {
                "chapter_marker_chunk_chars": tuning.chapter_marker_chunk_chars,
                "chapter_marker_chunk_overlap_chars": tuning.chapter_marker_chunk_overlap_chars,
                "chapter_narrative_chunk_chars": tuning.chapter_narrative_chunk_chars,
                "chapter_narrative_chunk_overlap_chars": tuning.chapter_narrative_chunk_overlap_chars,
                "character_llm_chunk_chars": tuning.character_llm_chunk_chars,
                "character_mention_context_chars": tuning.character_mention_context_chars,
                "summary_chunk_words": tuning.summary_chunk_words,
                "summary_chunk_overlap_words": tuning.summary_chunk_overlap_words,
            }
        else:
            # Use PipelineTuningConfig defaults
            from .agents.config import PipelineTuningConfig

            defaults = PipelineTuningConfig()
            config_dict["tuning"] = {
                "chapter_marker_chunk_chars": defaults.chapter_marker_chunk_chars,
                "chapter_marker_chunk_overlap_chars": defaults.chapter_marker_chunk_overlap_chars,
                "chapter_narrative_chunk_chars": defaults.chapter_narrative_chunk_chars,
                "chapter_narrative_chunk_overlap_chars": defaults.chapter_narrative_chunk_overlap_chars,
                "character_llm_chunk_chars": defaults.character_llm_chunk_chars,
                "character_mention_context_chars": defaults.character_mention_context_chars,
                "summary_chunk_words": defaults.summary_chunk_words,
                "summary_chunk_overlap_words": defaults.summary_chunk_overlap_words,
            }

        return config_dict

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
                output_path = file_path.with_suffix(".analysis.json")

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
