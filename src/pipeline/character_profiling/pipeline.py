"""
Character profiling pipeline orchestrator.

Coordinates the summary-driven character identification and profiling workflow.

Feature F2: Summary-Derived Profile Evidence
The pipeline now passes summary_map to the generator for evidence extraction.

Feature F3: Moral Valence Propagation to Profiles
The pipeline now computes moral valence and passes it as a HARD CONSTRAINT.
"""

import logging
from typing import Optional, Callable
from datetime import datetime

from .models import (
    IdentifiedCharacter,
    CharacterProfile,
    CharacterProfileMap,
)
from .identifier import SummaryDrivenCharacterIdentifier
from .generator import CharacterProfileGenerator
from .moral_valence import MoralValenceClassifier
from .passage_gatherer import CharacterPassageGatherer
from .summary_evidence import SummaryEvidenceExtractor
from .handoff_detector import HandoffDetector, HandoffCandidate
from ..chapter_summary.models import ChapterSummary, ChapterSummaryMap
from ..chapter_detection.models import ChapterMap
from ..llm import LLMClient

logger = logging.getLogger(__name__)


class CharacterProfilingPipeline:
    """
    Orchestrates the character profiling workflow.

    Stages:
    1. Identification: Extract characters from chapter summaries
    2. Profiling: Generate rich profiles for each character (future)
    3. Reconciliation: Final duplicate check (future)
    """

    def __init__(
        self,
        llm_client: LLMClient,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
        generate_rich_profiles: bool = True,
    ):
        """
        Args:
            llm_client: LLM client for character identification and profiling
            progress_callback: Callback(stage, current, total) for progress updates
            generate_rich_profiles: Whether to generate rich profiles (requires LLM calls per character)
        """
        self.llm = llm_client
        self.progress_callback = progress_callback
        self.generate_rich_profiles = generate_rich_profiles

    def run(
        self,
        full_text: str,
        chapter_map: ChapterMap,
        summary_map: ChapterSummaryMap,
        plot_summary: Optional[str] = None,
        source_file: str = "unknown",
    ) -> CharacterProfileMap:
        """
        Run the character profiling pipeline.

        Args:
            full_text: Complete document text
            chapter_map: Chapter boundaries from chapter detection
            summary_map: Chapter summaries from summary pipeline
            plot_summary: Optional plot summary for better identification
            source_file: Source file name for metadata

        Returns:
            CharacterProfileMap with all character profiles
        """
        logger.info("Starting character profiling pipeline")
        self._report_progress("identification", 0, 3)

        # Stage 1: Character Identification from Summaries
        logger.info("Stage 1: Identifying characters from summaries")
        identifier = SummaryDrivenCharacterIdentifier(self.llm)

        characters, narrator_name, narrative_style = identifier.identify_characters(
            chapter_summaries=summary_map.summaries,
            plot_summary=plot_summary or "",
        )
        self._report_progress("identification", 1, 3)

        logger.info(f"Identified {len(characters)} characters")
        if narrator_name:
            logger.info(f"Narrator: {narrator_name}")

            # Double-check that narrator is marked (case-insensitive match)
            narrator_found = False
            for char in characters:
                if char.canonical_name.lower() == narrator_name.lower():
                    if not char.is_narrator:
                        logger.warning(f"Narrator {narrator_name} not marked - fixing")
                        char.is_narrator = True
                        char.narrative_role = "First-person narrator" if "first" in narrative_style.lower() else "Narrator"
                    narrator_found = True
                    break
                # Also check aliases
                if any(alias.lower() == narrator_name.lower() for alias in char.aliases):
                    if not char.is_narrator:
                        logger.warning(f"Narrator {narrator_name} (alias) not marked - fixing")
                        char.is_narrator = True
                        char.narrative_role = "First-person narrator" if "first" in narrative_style.lower() else "Narrator"
                    narrator_found = True
                    break

            if not narrator_found:
                logger.warning(f"Narrator {narrator_name} not in character list - may need addition")

        # Stage 1.5: Handoff Detection and Auto-Merge
        logger.info("Stage 1.5: Detecting character handoffs")
        self._report_progress("identification", 2, 3)

        handoff_detector = HandoffDetector(gap_tolerance=2, min_confidence=0.5)
        handoff_candidates = handoff_detector.detect_handoffs(characters, summary_map)

        # Apply high-confidence merges automatically (>0.85)
        high_confidence_merges = [c for c in handoff_candidates if c.confidence >= 0.85]
        if high_confidence_merges:
            logger.info(f"Auto-merging {len(high_confidence_merges)} high-confidence handoffs")
            characters = self._apply_handoff_merges(characters, high_confidence_merges)
            logger.info(f"After merge: {len(characters)} characters")

        self._report_progress("identification", 3, 3)

        # Build list of all character names for collision filtering
        all_character_names = []
        for char in characters:
            all_character_names.append(char.canonical_name)
            all_character_names.extend(char.aliases)

        # Stage 2: Profile Generation
        logger.info("Stage 2: Generating character profiles")
        self._report_progress("profiling", 0, len(characters))

        profiles = []
        if self.generate_rich_profiles:
            # Generate rich profiles with appearance, personality, voice guidance
            # Feature F2: Pass summary_map to generator for summary evidence extraction
            generator = CharacterProfileGenerator(self.llm, summary_map=summary_map)
            passage_gatherer = CharacterPassageGatherer()
            # Pass all character names for collision filtering
            summary_extractor = SummaryEvidenceExtractor(self.llm, all_character_names)
            # Feature F3: Moral valence classifier for hard constraints
            valence_classifier = MoralValenceClassifier(self.llm)

            for i, char in enumerate(characters):
                logger.info(f"Profiling character {i + 1}/{len(characters)}: {char.canonical_name}")

                # Gather passages for this character
                passages = passage_gatherer.gather_passages(char, full_text, chapter_map)

                # Extract summary evidence (Feature F2)
                # Check if this character is the narrator
                is_char_narrator = (
                    narrator_name and
                    char.canonical_name.lower() == narrator_name.lower()
                )
                summary_evidence = summary_extractor.extract_evidence(
                    char.canonical_name,
                    char.aliases,
                    summary_map,
                    is_narrator=is_char_narrator,
                    narrative_style=narrative_style,
                )

                # Classify moral valence (Feature F3)
                passage_texts = [p.text for p in passages]
                moral_valence = valence_classifier.classify_character(
                    char.canonical_name,
                    char.role,
                    passage_texts,
                )
                logger.info(
                    f"Moral valence for {char.canonical_name}: {moral_valence.valence.value} "
                    f"(confidence={moral_valence.confidence:.2f})"
                )

                # Generate rich profile with summary evidence and moral valence constraint
                profile = generator.generate_profile(
                    character=char,
                    full_text=full_text,
                    chapter_map=chapter_map,
                    passages=passages,
                    summary_evidence=summary_evidence,
                    moral_valence=moral_valence,
                    narrative_style=narrative_style,
                )
                profiles.append(profile)
                self._report_progress("profiling", i + 1, len(characters))
        else:
            # Basic profile without LLM generation
            for i, char in enumerate(characters):
                profile = CharacterProfile.from_identified(char)
                profiles.append(profile)
                self._report_progress("profiling", i + 1, len(characters))

        # Stage 3: Build result
        logger.info("Stage 3: Building profile map")
        self._report_progress("finalization", 1, 1)

        profile_map = CharacterProfileMap(
            profiles=profiles,
            narrator_name=narrator_name,
            narrative_style=narrative_style,
            total_characters=len(profiles),
            pipeline_metadata={
                "source_file": source_file,
                "generated_at": datetime.now().isoformat(),
                "chapter_count": len(summary_map.summaries),
            },
        )

        logger.info(f"Character profiling complete: {len(profiles)} profiles")

        return profile_map

    def identify_only(
        self,
        summary_map: ChapterSummaryMap,
        plot_summary: Optional[str] = None,
    ) -> tuple[list[IdentifiedCharacter], Optional[str], str]:
        """
        Run only the identification stage (for testing or separate workflows).

        Args:
            summary_map: Chapter summaries from summary pipeline
            plot_summary: Optional plot summary for better identification

        Returns:
            Tuple of (characters, narrator_name, narrative_style)
        """
        identifier = SummaryDrivenCharacterIdentifier(self.llm)
        return identifier.identify_characters(
            chapter_summaries=summary_map.summaries,
            plot_summary=plot_summary or "",
        )

    def _apply_handoff_merges(
        self,
        characters: list[IdentifiedCharacter],
        merges: list[HandoffCandidate],
    ) -> list[IdentifiedCharacter]:
        """
        Apply handoff merges to the character list.

        Merges name_b into name_a (name_a is kept as canonical).

        Args:
            characters: List of identified characters
            merges: List of high-confidence handoff candidates to merge

        Returns:
            Updated list with merges applied
        """
        # Build name -> character lookup
        char_by_name: dict[str, IdentifiedCharacter] = {}
        for char in characters:
            char_by_name[char.canonical_name.lower()] = char
            for alias in char.aliases:
                char_by_name[alias.lower()] = char

        chars_to_remove = set()

        for merge in merges:
            name_a = merge.name_a.lower()
            name_b = merge.name_b.lower()

            char_a = char_by_name.get(name_a)
            char_b = char_by_name.get(name_b)

            if not char_a or not char_b or char_a == char_b:
                continue

            logger.info(
                f"Merging '{merge.name_b}' into '{merge.name_a}' "
                f"(confidence={merge.confidence:.2f}): {merge.reason}"
            )

            # Merge B into A
            # Add B's canonical name and aliases to A
            if merge.name_b not in char_a.aliases:
                char_a.aliases.append(merge.name_b)
            for alias in char_b.aliases:
                if alias not in char_a.aliases and alias.lower() != char_a.canonical_name.lower():
                    char_a.aliases.append(alias)

            # Merge chapters
            char_a.chapters_present = sorted(set(char_a.chapters_present + char_b.chapters_present))

            # Update first appearance
            if char_b.first_appearance_chapter < char_a.first_appearance_chapter:
                char_a.first_appearance_chapter = char_b.first_appearance_chapter

            # Mark B for removal
            chars_to_remove.add(id(char_b))

        # Return filtered list
        return [c for c in characters if id(c) not in chars_to_remove]

    def _report_progress(self, stage: str, current: int, total: int) -> None:
        """Report progress if callback is configured."""
        if self.progress_callback:
            self.progress_callback(stage, current, total)


def profile_characters(
    full_text: str,
    chapter_map: ChapterMap,
    summary_map: ChapterSummaryMap,
    llm_client: LLMClient,
    plot_summary: Optional[str] = None,
    source_file: str = "unknown",
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
) -> CharacterProfileMap:
    """
    Convenience function for character profiling.

    Args:
        full_text: Complete document text
        chapter_map: Chapter boundaries from chapter detection
        summary_map: Chapter summaries from summary pipeline
        llm_client: LLM client
        plot_summary: Optional plot summary
        source_file: Source file name
        progress_callback: Optional progress callback

    Returns:
        CharacterProfileMap with all character profiles
    """
    pipeline = CharacterProfilingPipeline(
        llm_client=llm_client,
        progress_callback=progress_callback,
    )

    return pipeline.run(
        full_text=full_text,
        chapter_map=chapter_map,
        summary_map=summary_map,
        plot_summary=plot_summary,
        source_file=source_file,
    )
