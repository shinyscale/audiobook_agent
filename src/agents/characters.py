"""
CharacterAgent - Summary-Driven Character Extraction

This agent implements the profile-first approach:
1. Extract main cast profiles from chapter summaries (F1)
2. Search for mentions deterministically (F2)
3. Apply grounding gate to reject hallucinations (F2b)
4. Detect narrator from summaries (F4)
5. Extract supporting cast via NER (F3)
6. Graph-based identity resolution (merge via declarative evidence graph)

Identity resolution uses a graph-based approach (identity_graph.py + evidence_collectors.py)
that replaces 7 sequential merge passes with a single declarative resolution:
- Nodes = character entries, edges = typed/weighted merge evidence
- Constraint edges prevent false merges (e.g., father/son same name)
- Resolution: connected components → constraint splitting → atomic merge
"""

import logging
import time
from typing import Optional

from ..llm.client import LLMClient
from ..models import Character, MergeDecision, StructuralElement, StructureType
from ..pipeline.character_extraction.models import Character as PipelineCharacter
from ..pipeline.character_extraction.models import CharacterMap
from ..pipeline.character_extraction_v2 import (
    GroundingGate,
    MainCastExtractor,
    MentionSearcher,
    NarratorDetector,
    SupportingCastExtractor,
    adaptive_min_mentions,
)
from .base import (
    Agent,
    AgentContext,
    AgentResult,
    VerificationIssue,
    VerificationLevel,
    VerificationResult,
)
from .config import AgentConfig, CompetitiveConfig

logger = logging.getLogger(__name__)


class CharacterAgent(Agent):
    """
    V2 Character Agent using summary-driven extraction.

    Pipeline order: summaries → main_cast → mentions → grounding → narrator → supporting
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        config: Optional[AgentConfig] = None,
        min_grounding_mentions: int = 3,
        competitive_config: Optional[CompetitiveConfig] = None,
        json_llm_client: Optional[LLMClient] = None,
    ):
        self.llm = llm_client
        self.config = config or AgentConfig()
        self.min_grounding_mentions = min_grounding_mentions
        self.competitive_config = competitive_config
        # JSON-capable LLM client for fallback when primary model fails JSON parsing
        self.json_llm = json_llm_client
        # Track merge decisions for TUI review (co-occurrence validation)
        self._merge_decisions: list[MergeDecision] = []
        # Store co-occurrence scores computed once after grounding
        self._cooccurrence: dict[tuple[str, str], float] = {}

    @property
    def name(self) -> str:
        return "characters"

    @property
    def depends_on(self) -> list[str]:
        """V2 requires summaries (from SummaryAgent) before running."""
        return ["structure", "summaries"]

    @property
    def recommended_models(self) -> list[str]:
        return [
            "qwen2.5:72b",  # Strong local model for character understanding
            "llama3.2",  # Good local alternative
            "gpt-4o-mini",  # Cloud fallback
        ]

    def run(self, context: AgentContext) -> AgentResult[CharacterMap]:
        """
        Run the v2 character extraction pipeline.

        Order:
        1. Extract main cast from summaries (F1)
        2. Search for mentions (F2)
        3. Apply grounding gate (F2b)
        4. Detect narrator (F4)
        5. Extract supporting cast (F3)
        """
        start_time = time.perf_counter()
        issues = []

        # Validate required inputs
        if not self.llm:
            return self._error_result("No LLM client configured", start_time)

        # Get chapter summaries from context
        chapter_summaries = self._get_chapter_summaries(context)
        if not chapter_summaries:
            return self._error_result(
                "No chapter summaries available - SummaryAgent must run first",
                start_time,
            )

        # Get chapters for mention position mapping
        chapters = self._get_chapters(context)

        # Get plot summary if available
        plot_summary = self._get_plot_summary(context)

        # STEP 1: Extract main cast from summaries (F1)
        logger.info("V2 Step 1: Extracting main cast from summaries")
        main_cast_extractor = MainCastExtractor(
            self.llm,
            self.competitive_config,
            json_llm=self.json_llm,
        )
        profiles = main_cast_extractor.extract(chapter_summaries, plot_summary)

        if not profiles:
            issues.append("No main cast profiles extracted from summaries")

        # Convert profiles to Character objects
        characters = main_cast_extractor.profiles_to_characters(profiles)
        logger.info(f"V2 Step 1 complete: {len(characters)} main cast candidates")

        # STEP 1.4: Filter non-character entities (locations, objects, concepts)
        # Some LLMs may extract setting elements with roles like "setting/plot device"
        non_character_roles = ["setting", "location", "place", "object", "concept", "device"]
        before_filter = len(characters)
        characters = [
            c
            for c in characters
            if (
                # Keep plot-central symbolic entities explicitly marked as such
                bool(getattr(c, "is_symbolic", False))
                or not any(non_char_role in (c.role or "").lower() for non_char_role in non_character_roles)
            )
        ]
        if len(characters) < before_filter:
            filtered_count = before_filter - len(characters)
            logger.info(f"V2 Step 1.4: Filtered {filtered_count} non-character entity/entities")

        # STEP 2: Search for mentions (F2)
        logger.info("V2 Step 2: Searching for character mentions")
        searcher = MentionSearcher(context.text, chapters)
        mention_results = searcher.search_all(characters)
        characters = searcher.update_characters_with_mentions(characters, mention_results)

        # STEP 3: Apply grounding gate (F2b)
        word_count = len(context.text.split())
        effective_min_mentions = adaptive_min_mentions(
            word_count, default=self.min_grounding_mentions
        )
        logger.info(
            f"V2 Step 3: Applying grounding gate "
            f"(~{word_count:,} words, threshold={effective_min_mentions})"
        )
        grounding_gate = GroundingGate(
            min_mentions=effective_min_mentions,
            remove_ungrounded_aliases=True,
        )
        grounding_report = grounding_gate.apply(characters, mention_results)
        grounding_gate.log_report(grounding_report)

        # Use grounded characters as main cast
        main_cast = grounding_report.grounded_characters
        ungrounded = grounding_report.ungrounded_characters

        if ungrounded:
            issues.append(
                f"{len(ungrounded)} characters excluded by grounding gate "
                f"(insufficient text evidence)"
            )

        logger.info(f"V2 Step 3 complete: {len(main_cast)} grounded characters")

        # STEP 3.3.5: Compute co-occurrence matrix (main cast only, re-computed with supporting later)
        logger.info("V2 Step 3.3.5: Computing co-occurrence matrix for merge validation")
        self._merge_decisions = []  # Reset for this run
        self._cooccurrence = self._compute_cooccurrence(main_cast, context.text)
        logger.info(
            f"V2 Step 3.3.5 complete: computed {len(self._cooccurrence)} pairwise scores"
        )

        # STEP 4: Detect narrator (F4)
        logger.info("V2 Step 4: Detecting narrator")
        narrator_detector = NarratorDetector(self.llm)
        narrator_info = narrator_detector.detect(chapter_summaries, main_cast, plot_summary)
        main_cast = narrator_detector.update_characters_with_narrator(main_cast, narrator_info)

        logger.info(
            f"V2 Step 4 complete: POV={narrator_info.pov}, "
            f"narrator={narrator_info.narrator_name}"
        )

        # STEP 5: Extract supporting cast (F3)
        logger.info("V2 Step 5: Extracting supporting cast via NER")
        main_cast_names = self._collect_all_names(main_cast)
        supporting_extractor = SupportingCastExtractor(
            context.text,
            min_mentions=effective_min_mentions,
        )
        supporting_cast = supporting_extractor.extract(main_cast_names)

        logger.info(f"V2 Step 5 complete: {len(supporting_cast)} supporting characters")

        # STEP 5.0.5: Re-run narrator detection with combined cast
        # This catches frame narrators (like Walton in Frankenstein) who appear infrequently by name
        # and get extracted into supporting_cast rather than main_cast.
        # Previous Step 4 only checked main_cast, so we re-check with full character list.
        if supporting_cast and narrator_info.narrator_name:
            # If narrator was identified by name but not matched to a character,
            # try matching against supporting cast as well
            combined_cast = main_cast + supporting_cast
            logger.info(
                f"Re-checking narrator '{narrator_info.narrator_name}' against combined cast "
                f"({len(main_cast)} main + {len(supporting_cast)} supporting)"
            )
            narrator_info_combined = narrator_detector.detect(
                chapter_summaries, combined_cast, plot_summary
            )

            # If the combined detection found a match (and Step 4 didn't), update narrator info
            if narrator_info_combined.narrator_character_id and not narrator_info.narrator_character_id:
                logger.info(
                    f"Found narrator '{narrator_info_combined.narrator_name}' in supporting cast: "
                    f"{narrator_info_combined.narrator_character_id}"
                )
                narrator_info = narrator_info_combined
                # Update the character in whichever list they belong to
                for i, char in enumerate(supporting_cast):
                    if char.id == narrator_info.narrator_character_id:
                        supporting_cast[i] = narrator_detector.update_characters_with_narrator(
                            [char], narrator_info
                        )[0]
                        logger.info(f"Marked {char.canonical_name} as narrator in supporting cast")
                        break
                for i, char in enumerate(main_cast):
                    if char.id == narrator_info.narrator_character_id:
                        main_cast[i] = narrator_detector.update_characters_with_narrator(
                            [char], narrator_info
                        )[0]
                        logger.info(f"Marked {char.canonical_name} as narrator in main cast")
                        break

            # Handle nested narrators in supporting cast as well
            if narrator_info_combined.nested_narrators:
                for narrator_id in narrator_info_combined.nested_narrators:
                    if narrator_id not in narrator_info.nested_narrators:
                        # Found a nested narrator in supporting cast that wasn't in main cast
                        for i, char in enumerate(supporting_cast):
                            if char.id == narrator_id:
                                supporting_cast[i].is_narrator = True
                                logger.info(
                                    f"Marked {char.canonical_name} as nested narrator in supporting cast"
                                )
                                break

        # STEP 5.1: Filter narrator-related entries from supporting cast
        # Handles cases where NER picks up "narrator", "the narrator", etc.
        supporting_cast = self._filter_narrator_variants(
            supporting_cast, narrator_info.narrator_name
        )
        logger.info(
            f"V2 Step 5.1 complete: {len(supporting_cast)} supporting after narrator filter"
        )

        # STEP 5.2: Also filter narrator variants from main cast (defensive)
        # In case the LLM extracted "Narrator" as a main character
        original_main_count = len(main_cast)
        main_cast = self._filter_narrator_variants(main_cast, narrator_info.narrator_name)
        if len(main_cast) < original_main_count:
            logger.info(
                f"V2 Step 5.2: Filtered {original_main_count - len(main_cast)} narrator "
                f"variant(s) from main cast"
            )

        # STEP 5.3: Recompute co-occurrence for ALL characters before graph resolution
        # The initial co-occurrence (step 3.3.5) only covered main_cast.
        # Now we need scores for supporting→main merges too.
        all_characters_for_cooccurrence = main_cast + supporting_cast
        logger.info(
            f"V2 Step 5.3: Recomputing co-occurrence for {len(all_characters_for_cooccurrence)} "
            f"characters (main + supporting) before identity resolution"
        )
        self._cooccurrence = self._compute_cooccurrence(all_characters_for_cooccurrence, context.text)
        logger.info(
            f"V2 Step 5.3 complete: {len(self._cooccurrence)} pairwise scores computed"
        )

        # STEP 5.5: Graph-based identity resolution
        # Replaces 7 sequential merge passes with a single declarative graph:
        #   - Nodes = characters, edges = typed/weighted merge evidence
        #   - Constraint edges prevent false merges (e.g., father/son same name)
        #   - Resolution: connected components → constraint splitting → atomic merge
        from ..pipeline.character_extraction_v2.identity_graph import (
            IdentityGraph,
            resolve_identities,
            execute_merges as graph_execute_merges,
            merge_groups_to_dict,
        )
        from ..pipeline.character_extraction_v2.evidence_collectors import (
            collect_all_evidence,
        )

        logger.info("V2 Step 5.5: Running graph-based identity resolution")

        # Track original alias sets to detect which characters gained new aliases
        pre_merge_aliases = {}
        for c in main_cast + supporting_cast:
            pre_merge_aliases[c.id] = set(c.aliases)

        # Build identity graph from current character lists
        ig = IdentityGraph()
        ig.add_characters(main_cast, supporting_cast)

        # Collect all evidence (title variants, within-cast, cross-cast,
        # synonyms, narrator, surname families, co-occurrence corroboration,
        # and summary-based disambiguation)
        collect_all_evidence(
            ig,
            narrator_info=narrator_info,
            cooccurrence=self._cooccurrence,
            chapter_summaries=chapters,  # Pass StructuralElements with characters_present
        )

        # Resolve identities and execute merges atomically
        merge_groups = resolve_identities(ig)
        main_cast, supporting_cast = graph_execute_merges(
            merge_groups,
            main_cast,
            supporting_cast,
            is_valid_alias_fn=self._is_valid_alias,
        )

        # Apply disambiguation labels to same-name characters kept separate by constraints
        logger.info("V2 Step 5.6: Applying disambiguation labels to same-name characters")
        main_cast, supporting_cast = self._apply_disambiguation_labels(
            main_cast, supporting_cast, merge_groups, ig
        )

        # Post-merge: update narrator_info if narrator placeholder was merged
        if narrator_info.narrator_character_id:
            # Check if the narrator's character was absorbed into another
            narrator_still_exists = any(
                c.id == narrator_info.narrator_character_id
                for c in main_cast + supporting_cast
            )
            if not narrator_still_exists:
                # Narrator was merged — find the canonical character that absorbed it
                for group in merge_groups:
                    if (narrator_info.narrator_character_id in group.member_ids
                            and len(group.member_ids) > 1):
                        canonical = next(
                            (c for c in main_cast + supporting_cast
                             if c.id == group.canonical_node_id),
                            None,
                        )
                        if canonical:
                            narrator_info.narrator_character_id = canonical.id
                            narrator_info.narrator_name = canonical.canonical_name
                            logger.info(
                                f"Updated narrator reference to merged character: "
                                f"'{canonical.canonical_name}'"
                            )
                        break

        # Re-search mentions for characters that gained new aliases from graph merges
        chars_with_new_aliases = []
        for c in main_cast + supporting_cast:
            old_aliases = pre_merge_aliases.get(c.id, set())
            if set(c.aliases) != old_aliases:
                chars_with_new_aliases.append(c)

        if chars_with_new_aliases:
            logger.info(
                f"Re-searching mentions for {len(chars_with_new_aliases)} characters "
                f"with new aliases from graph resolution"
            )
            for char in chars_with_new_aliases:
                result = searcher.search_character(char)
                char.mention_count = result.total_mentions
                char.mentions = result.mentions
                mention_results[char.id] = result
                if result.chapter_distribution:
                    chapters_sorted = sorted(result.chapter_distribution.keys())
                    char.first_appearance_chapter = chapters_sorted[0]

        groups_with_merges = sum(1 for g in merge_groups if len(g.member_ids) > 1)
        logger.info(
            f"V2 Step 5.5 complete: {len(main_cast)} main cast, "
            f"{len(supporting_cast)} supporting after graph resolution "
            f"({groups_with_merges} merge groups applied)"
        )

        # Serialize identity graph for visualization/debugging
        identity_graph_data = {
            "graph": ig.to_dict(),
            "merge_groups": merge_groups_to_dict(merge_groups),
            "stats": {
                "nodes": len(ig.nodes),
                "merge_edges": len(ig.merge_edges),
                "constraint_edges": len(ig.constraint_edges),
                "groups_with_merges": groups_with_merges,
            },
        }

        # STEP 5.7: Final defensive narrator filter (after all merges)
        # This catches any narrator entries that might have been introduced during merging
        logger.info("V2 Step 5.7: Final narrator filter pass")
        main_cast = self._filter_narrator_variants(main_cast, narrator_info.narrator_name)
        supporting_cast = self._filter_narrator_variants(
            supporting_cast, narrator_info.narrator_name
        )
        logger.info(
            f"V2 Step 5.7 complete: {len(main_cast)} main cast, {len(supporting_cast)} supporting "
            f"after final narrator filter"
        )

        # STEP 5.8: Post-processing - Promote high-mention supporting characters to main cast
        # This addresses cases where the LLM fails to extract key characters in main_cast
        # but they get picked up by NER-based supporting_cast extraction
        logger.info("V2 Step 5.8: Promoting high-mention supporting characters to main cast")

        # Characters with high mention counts should have protagonist/main roles
        # Thresholds based on narrative significance:
        # - 200+ mentions: Protagonist level (title character, narrator, central character)
        # - 100+ mentions: Main character level (key supporting roles, love interests)
        # - 50+ mentions: Supporting character level (recurring named characters)
        PROTAGONIST_THRESHOLD = 200
        MAIN_THRESHOLD = 100
        PROMOTION_THRESHOLD = 50
        promoted_chars = []
        remaining_supporting = []

        for char in supporting_cast:
            if char.mention_count >= PROMOTION_THRESHOLD:
                # Promote to main cast with role based on mention count
                if char.mention_count >= PROTAGONIST_THRESHOLD:
                    char.role = "protagonist"
                elif char.mention_count >= MAIN_THRESHOLD:
                    char.role = "main"
                else:
                    char.role = "supporting"
                promoted_chars.append(char)
                logger.info(
                    f"Promoted '{char.canonical_name}' to main cast ({char.mention_count} mentions, "
                    f"role: {char.role})"
                )
            else:
                remaining_supporting.append(char)

        if promoted_chars:
            main_cast.extend(promoted_chars)
            supporting_cast = remaining_supporting
            logger.info(f"Promoted {len(promoted_chars)} character(s) from supporting to main cast")

        logger.info(
            f"V2 Step 5.8 complete: {len(main_cast)} main cast, {len(supporting_cast)} supporting "
            f"after promotion"
        )

        # STEP 5.9: REMOVED - Non-sentient object filter
        # Symbolic objects/forces can be valid "characters" for narrator preparation
        # Examples: "the monkey's paw" (title antagonist), "the eyes of Doctor T. J. Eckleburg" (symbolic presence)
        # Trust plot importance over categorization - if something drives the narrative, extract it
        logger.info("V2 Step 5.9: Skipped (object filter removed - trusting plot importance)")

        logger.info(
            f"V2 Step 5.9 complete: {len(main_cast)} main cast, {len(supporting_cast)} supporting"
        )

        # STEP 5.10: Final alias validation
        # Clean up any invalid aliases that may have been added during merge operations
        # This ensures aliases like "the ebony clock" (object) don't appear on non-object characters
        logger.info("V2 Step 5.10: Validating aliases before final output")
        self._clean_invalid_aliases(main_cast)
        self._clean_invalid_aliases(supporting_cast)

        # STEP 5.10.5: Search for mentions for supporting cast too (chapter distributions)
        #
        # Supporting cast is initially extracted via NER and may not have deterministic
        # mention search results. However, downstream components (and debugging) benefit
        # from having grounded mentions + chapter_distribution for supporting characters,
        # especially for same-name disambiguation and chapter-range priors.
        if supporting_cast:
            logger.info(
                f"V2 Step 5.10.5: Searching mentions for {len(supporting_cast)} supporting characters"
            )
            try:
                supporting_results = searcher.search_all(supporting_cast)
                supporting_cast = searcher.update_characters_with_mentions(
                    supporting_cast, supporting_results
                )
                # Merge into global mention_results so downstream conversion can use chapter_distribution
                mention_results.update(supporting_results)

                # Populate first appearance chapter when possible
                for char in supporting_cast:
                    r = supporting_results.get(char.id)
                    if r and r.chapter_distribution:
                        chapters = sorted(r.chapter_distribution.keys())
                        char.first_appearance_chapter = chapters[0]
            except Exception as e:
                logger.warning(f"Supporting cast mention search failed: {e}")

        # STEP 5.10.6: Filter out name fragments (middle names, partial names)
        # If supporting cast has standalone names that are word fragments of main cast full names,
        # filter them out (e.g., "Dillingham" when "James Dillingham Young" exists in main cast)
        logger.info("V2 Step 5.10.6: Filtering name fragments from supporting cast")
        supporting_cast = self._filter_name_fragments(main_cast, supporting_cast)
        logger.info(
            f"V2 Step 5.10.6 complete: {len(supporting_cast)} supporting after fragment filter"
        )

        # Build final CharacterMap
        all_characters = self._convert_to_pipeline_characters(
            main_cast, supporting_cast, mention_results
        )

        # Calculate confidence breakdown
        high = sum(1 for c in all_characters if c.confidence >= 0.7)
        medium = sum(1 for c in all_characters if 0.4 <= c.confidence < 0.7)
        low = sum(1 for c in all_characters if c.confidence < 0.4)

        # Summarize merge decisions for pipeline metadata
        pending_reviews = [d for d in self._merge_decisions if d.needs_review]
        merge_summary = {
            "total_merges": len(self._merge_decisions),
            "high_confidence": sum(1 for d in self._merge_decisions if d.confidence == "high"),
            "medium_confidence": sum(1 for d in self._merge_decisions if d.confidence == "medium"),
            "low_confidence_pending_review": len(pending_reviews),
        }

        character_map = CharacterMap(
            characters=all_characters,
            low_confidence_characters=[c for c in all_characters if c.confidence < 0.4],
            total_mentions=sum(c.mention_count for c in all_characters),
            total_chapters=len(chapters) if chapters else 1,
            pipeline_metadata={
                "version": "v2",
                "main_cast_count": len(main_cast),
                "supporting_cast_count": len(supporting_cast),
                "grounded_count": grounding_report.total_grounded,
                "ungrounded_count": grounding_report.total_ungrounded,
                "narrator_pov": narrator_info.pov,
                "narrator_name": narrator_info.narrator_name,
                "merge_decisions": merge_summary,
                "pending_reviews": [d.model_dump() for d in pending_reviews],
                "identity_graph": identity_graph_data,
            },
        )

        elapsed = time.perf_counter() - start_time

        return AgentResult(
            data=character_map,
            confidence_scores=[c.confidence for c in all_characters],
            high_confidence_count=high,
            medium_confidence_count=medium,
            low_confidence_count=low,
            issues=issues,
            processing_time_seconds=elapsed,
            model_used=self.llm.config.model if self.llm else None,
            provider_used=self.llm.config.provider if self.llm else None,
        )

    def verify(
        self,
        result: AgentResult[CharacterMap],
        level: VerificationLevel = VerificationLevel.SELF_CHECK,
        context: Optional[AgentContext] = None,
    ) -> VerificationResult:
        """
        Verify V2 character extraction quality.

        Simpler than V1 - most validation is handled by grounding gate.
        """
        issues = []
        character_map = result.data

        if not character_map.characters:
            return VerificationResult(passed=True, issues=[], suggestions=[])

        # Check 1: Main cast count is reasonable
        main_count = character_map.pipeline_metadata.get("main_cast_count", 0)
        if main_count < 3:
            issues.append(
                VerificationIssue(
                    description=f"Only {main_count} main cast characters - may be incomplete",
                    severity="warning",
                )
            )
        elif main_count > 20:
            issues.append(
                VerificationIssue(
                    description=f"{main_count} main cast characters - may have over-extraction",
                    severity="warning",
                )
            )

        # Check 2: Grounding worked
        ungrounded = character_map.pipeline_metadata.get("ungrounded_count", 0)
        if ungrounded > main_count:
            issues.append(
                VerificationIssue(
                    description=f"More ungrounded ({ungrounded}) than grounded ({main_count}) characters",
                    severity="warning",
                )
            )

        # Check 3: Low confidence items
        if result.low_confidence_count > 0:
            issues.append(
                VerificationIssue(
                    description=f"{result.low_confidence_count} characters have low confidence",
                    severity="info",
                )
            )

        return VerificationResult(
            passed=len([i for i in issues if i.severity == "error"]) == 0,
            issues=issues,
            suggestions=[],
        )

    def _error_result(
        self,
        error_msg: str,
        start_time: float,
    ) -> AgentResult[CharacterMap]:
        """Create an error result."""
        elapsed = time.perf_counter() - start_time
        return AgentResult(
            data=CharacterMap(
                characters=[],
                low_confidence_characters=[],
                total_mentions=0,
                total_chapters=0,
                pipeline_metadata={"error": error_msg, "version": "v2"},
            ),
            high_confidence_count=0,
            medium_confidence_count=0,
            low_confidence_count=0,
            issues=[error_msg],
            processing_time_seconds=elapsed,
            model_used=self.llm.config.model if self.llm else None,
            provider_used=self.llm.config.provider if self.llm else None,
        )

    def _get_chapter_summaries(self, context: AgentContext) -> list[str]:
        """Extract chapter summaries from context, including characters_present."""
        # Try getting from previous_results (SummaryAgent output)
        summaries_result = context.get_result("summaries")
        if summaries_result:
            # SummaryAgent returns a list of ChapterSummary objects or similar
            if hasattr(summaries_result, "summaries"):
                return [
                    self._format_summary_with_characters(s)
                    for s in summaries_result.summaries
                    if s.summary
                ]
            elif isinstance(summaries_result, list):
                return [
                    s.get("summary") if isinstance(s, dict) else str(s)
                    for s in summaries_result
                    if s
                ]

        # Try getting from chapter_map (summaries may be stored on chapters)
        if context.chapter_map:
            summaries = []
            chapters = getattr(context.chapter_map, "chapters", [])
            for ch in chapters:
                if hasattr(ch, "summary") and ch.summary:
                    summaries.append(self._format_summary_with_characters(ch))
            if summaries:
                return summaries

        return []

    def _format_summary_with_characters(self, summary_obj) -> str:
        """Format a summary object to include characters_present list."""
        summary_text = summary_obj.summary

        # Check for characters_present or active_characters field
        characters = None
        if hasattr(summary_obj, "characters_present"):
            characters = summary_obj.characters_present
        elif hasattr(summary_obj, "active_characters"):
            characters = summary_obj.active_characters

        # If characters list exists and is non-empty, prepend it to the summary
        if characters:
            char_list = ", ".join(characters)
            return f"[Characters: {char_list}]\n{summary_text}"

        return summary_text

    def _get_chapters(self, context: AgentContext) -> list[StructuralElement]:
        """Get chapter structural elements from context, with characters_present from summaries."""
        if context.chapter_map:
            chapters = getattr(context.chapter_map, "chapters", [])

            # Get summary data to populate characters_present
            summaries_by_index = {}
            summaries_result = context.get_result("summaries")
            if summaries_result:
                if hasattr(summaries_result, "summaries"):
                    for s in summaries_result.summaries:
                        summaries_by_index[s.chapter_index] = s
                elif isinstance(summaries_result, list):
                    for idx, s in enumerate(summaries_result):
                        summaries_by_index[idx] = s

            # Convert to StructuralElement if needed
            result = []
            for ch in chapters:
                if isinstance(ch, StructuralElement):
                    # Populate characters_present if missing
                    if not ch.characters_present and ch.index in summaries_by_index:
                        summary_obj = summaries_by_index[ch.index]
                        if hasattr(summary_obj, "characters_present"):
                            ch.characters_present = summary_obj.characters_present
                        elif hasattr(summary_obj, "active_characters"):
                            ch.characters_present = summary_obj.active_characters
                    result.append(ch)
                elif hasattr(ch, "start_position"):
                    # Get characters_present from summary
                    characters_present = []
                    ch_index = getattr(ch, "index", len(result))
                    if ch_index in summaries_by_index:
                        summary_obj = summaries_by_index[ch_index]
                        if hasattr(summary_obj, "characters_present"):
                            characters_present = summary_obj.characters_present
                        elif hasattr(summary_obj, "active_characters"):
                            characters_present = summary_obj.active_characters

                    # Create StructuralElement from chapter data
                    elem = StructuralElement(
                        type=StructureType.CHAPTER,
                        index=ch_index,
                        start_position=ch.start_position,
                        end_position=getattr(ch, "end_position", ch.start_position + 1000),
                        characters_present=characters_present,
                    )
                    result.append(elem)
            return result
        return []

    def _get_plot_summary(self, context: AgentContext) -> Optional[str]:
        """Get overall plot summary if available."""
        summaries_result = context.get_result("summaries")
        if summaries_result:
            if hasattr(summaries_result, "plot_summary"):
                return summaries_result.plot_summary
            elif isinstance(summaries_result, dict):
                return summaries_result.get("plot_summary")
        return None

    def _collect_all_names(self, characters: list[Character]) -> set[str]:
        """Collect all names and aliases from characters."""
        names = set()
        for char in characters:
            names.add(char.canonical_name)
            names.update(char.aliases)
        return names

    def _compute_cooccurrence(
        self,
        characters: list[Character],
        text: str,
        chunk_size: int = 2000,  # ~1 page
    ) -> dict[tuple[str, str], float]:
        """
        Compute co-occurrence scores for all character pairs.

        Co-occurrence is measured by Jaccard similarity of chunk presence:
        How often do two characters appear in the same text chunks?

        This provides a structural signal independent of LLM reasoning:
        - High overlap (>0.5): Strong evidence they're the same person
        - Medium overlap (0.2-0.5): Possible same person, moderate confidence
        - Low overlap (<0.2): Weak evidence, flag for human review

        Args:
            characters: List of characters to analyze
            text: Full text to search for mentions
            chunk_size: Size of text chunks to use (default ~1 page)

        Returns:
            Dict mapping (char_a_id, char_b_id) -> overlap_score (0.0-1.0)
        """
        if not characters or not text:
            return {}

        # Split text into chunks
        chunks = [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]

        # For each character, find which chunks they appear in
        char_chunks: dict[str, set[int]] = {}
        for char in characters:
            names = [char.canonical_name] + list(char.aliases)
            char_chunks[char.id] = set()
            for i, chunk in enumerate(chunks):
                chunk_lower = chunk.lower()
                if any(name.lower() in chunk_lower for name in names):
                    char_chunks[char.id].add(i)

        # Compute pairwise overlap (Jaccard similarity)
        cooccurrence: dict[tuple[str, str], float] = {}
        for i, char_a in enumerate(characters):
            for char_b in characters[i + 1 :]:
                a_chunks = char_chunks.get(char_a.id, set())
                b_chunks = char_chunks.get(char_b.id, set())
                if a_chunks and b_chunks:
                    # Jaccard similarity: intersection / union
                    overlap = len(a_chunks & b_chunks) / len(a_chunks | b_chunks)
                else:
                    overlap = 0.0
                cooccurrence[(char_a.id, char_b.id)] = overlap
                cooccurrence[(char_b.id, char_a.id)] = overlap  # Symmetric

        return cooccurrence

    def _filter_narrator_variants(
        self,
        supporting_cast: list[Character],
        narrator_name: str | None,
    ) -> list[Character]:
        """
        Filter out narrator-related entries from supporting cast.

        Removes entries like:
        - "Narrator"
        - "the narrator"
        - "The Narrator"
        - "Nick Carraway (narrator)"

        These are descriptive references that should not be separate characters.

        Args:
            supporting_cast: List of supporting characters
            narrator_name: The identified narrator's name (if any)

        Returns:
            Filtered list with narrator variants removed
        """
        if not supporting_cast:
            return supporting_cast

        filtered = []
        removed_count = 0

        for char in supporting_cast:
            canonical_lower = char.canonical_name.lower()

            # Check if canonical name contains "narrator" (case-insensitive)
            if "narrator" in canonical_lower:
                logger.info(
                    f"Filtering narrator variant '{char.canonical_name}' "
                    f"({char.mention_count} mentions) from supporting cast"
                )
                removed_count += 1
                continue

            filtered.append(char)

        if removed_count > 0:
            logger.info(f"Removed {removed_count} narrator variant(s) from supporting cast")

        return filtered

    def _apply_disambiguation_labels(
        self,
        main_cast: list,
        supporting_cast: list,
        merge_groups: list,
        identity_graph,
    ) -> tuple[list, list]:
        """
        Apply disambiguation labels to characters with identical canonical names
        that were kept separate by role_conflict constraint edges.

        When two characters share the same canonical name (e.g., "John Donaldson" for
        both father and son), but were kept separate by a constraint edge, this extracts
        the disambiguation labels from the constraint edge reason and appends them to
        the canonical names.

        Args:
            main_cast: List of main cast characters
            supporting_cast: List of supporting cast characters
            merge_groups: Merge groups from identity resolution
            identity_graph: The identity graph with constraint edges

        Returns:
            Tuple of (updated_main_cast, updated_supporting_cast)
        """
        import re

        all_chars = main_cast + supporting_cast

        # Group characters by canonical_name (case-insensitive)
        name_groups = {}
        for char in all_chars:
            name_lower = char.canonical_name.lower()
            if name_lower not in name_groups:
                name_groups[name_lower] = []
            name_groups[name_lower].append(char)

        # Find groups with duplicates (same canonical name, multiple characters)
        for name_lower, chars in name_groups.items():
            if len(chars) < 2:
                continue  # No duplicates

            logger.info(
                f"Found {len(chars)} characters with name '{chars[0].canonical_name}': "
                f"{[c.id for c in chars]}"
            )

            # Find the merge groups for these characters
            char_ids = {c.id for c in chars}
            relevant_groups = [g for g in merge_groups if g.canonical_node_id in char_ids]

            if len(relevant_groups) < 2:
                logger.warning(
                    f"Expected {len(chars)} merge groups for '{chars[0].canonical_name}', "
                    f"found {len(relevant_groups)}"
                )
                continue

            # Find constraint edges between these groups
            # Look for role_conflict edges between any pair of these character IDs
            constraint_edges = []
            for i, char_a in enumerate(chars):
                for char_b in chars[i + 1:]:
                    edges = [
                        e for e in identity_graph.constraint_edges
                        if ((e.source == char_a.id and e.target == char_b.id) or
                            (e.source == char_b.id and e.target == char_a.id))
                        and e.constraint_type.value == "role_conflict"
                    ]
                    constraint_edges.extend(edges)

            if not constraint_edges:
                logger.warning(
                    f"No role_conflict constraint edges found between characters "
                    f"named '{chars[0].canonical_name}'"
                )
                continue

            # Extract labels from the first constraint edge
            # Format: "Summary disambiguates 'Name': N distinct people with labels ['label1', 'label2']"
            edge = constraint_edges[0]
            logger.info(f"Constraint edge reason: {edge.reason}")

            # Parse labels from the reason string
            match = re.search(r"labels \[(.*?)\]", edge.reason)
            if not match:
                logger.warning(f"Could not parse labels from constraint reason: {edge.reason}")
                continue

            # Extract individual labels
            labels_str = match.group(1)
            labels = [
                label.strip().strip("'\"")
                for label in labels_str.split(",")
            ]

            logger.info(f"Extracted {len(labels)} disambiguation labels: {labels}")

            if len(labels) != len(chars):
                logger.warning(
                    f"Label count mismatch: {len(labels)} labels for {len(chars)} characters"
                )
                # Use what we have
                labels = labels[:len(chars)]
                while len(labels) < len(chars):
                    labels.append(f"variant {len(labels) + 1}")

            # Sort characters by mention count (descending) to assign labels consistently
            # The character with more mentions gets the first label
            chars_sorted = sorted(chars, key=lambda c: c.mention_count, reverse=True)

            # Apply labels to canonical names
            for char, label in zip(chars_sorted, labels):
                old_name = char.canonical_name
                # Append label in parentheses
                char.canonical_name = f"{old_name} ({label})"
                logger.info(
                    f"Applied disambiguation label: '{old_name}' → '{char.canonical_name}' "
                    f"({char.mention_count} mentions)"
                )

        return main_cast, supporting_cast

    def _is_valid_alias(self, alias: str, canonical_name: str) -> bool:
        """
        Check if an alias is valid for the given canonical name.

        Blocks:
        - Inanimate objects (clock, door, etc.) unless canonical also has object keyword
        - Meta-references (narrator, reader, etc.)

        This prevents merge operations from adding invalid aliases that bypass
        MainCastExtractor.verify_aliases().

        Args:
            alias: The proposed alias to validate
            canonical_name: The canonical character name

        Returns:
            True if alias is valid, False if it should be blocked
        """
        alias_lower = alias.lower().strip()
        canonical_lower = canonical_name.lower().strip()

        # Block meta-references
        meta_references = {"narrator", "the narrator", "reader", "the reader", "audience", "the audience"}
        if alias_lower in meta_references:
            logger.warning(
                f"BLOCKED alias during merge: '{alias}' is a meta-reference, "
                f"not valid for '{canonical_name}'"
            )
            return False

        # Block inanimate objects (unless canonical also has object keyword)
        object_keywords = {
            "clock", "bell", "door", "window", "mirror", "portrait", "painting",
            "statue", "coffin", "casket", "sword", "dagger", "knife", "weapon",
            "chair", "table", "bed", "chest", "book", "letter", "ring", "crown",
            "chandelier", "candle", "torch", "lamp"
        }

        # Extract core words (after removing articles)
        alias_words = set(alias_lower.replace("the ", "").replace("a ", "").replace("an ", "").split())
        canonical_words = set(canonical_lower.replace("the ", "").replace("a ", "").replace("an ", "").split())

        alias_has_object = bool(alias_words & object_keywords)
        canonical_has_object = bool(canonical_words & object_keywords)

        if alias_has_object and not canonical_has_object:
            logger.warning(
                f"BLOCKED alias during merge: '{alias}' contains object keyword "
                f"({alias_words & object_keywords}), not valid for '{canonical_name}'"
            )
            return False

        return True

    def _clean_invalid_aliases(self, characters: list[Character]) -> None:
        """
        Remove invalid aliases from character list.

        This is a final cleanup pass applied after all merge operations to catch
        any invalid aliases that slipped through. Modifies characters in-place.

        Args:
            characters: List of Character objects to clean
        """
        for char in characters:
            original_count = len(char.aliases)
            # Filter out invalid aliases
            char.aliases = [
                alias for alias in char.aliases
                if self._is_valid_alias(alias, char.canonical_name)
            ]
            removed_count = original_count - len(char.aliases)
            if removed_count > 0:
                logger.info(
                    f"Cleaned {removed_count} invalid alias(es) from '{char.canonical_name}': "
                    f"final aliases = {char.aliases}"
                )

    def _filter_name_fragments(
        self,
        main_cast: list[Character],
        supporting_cast: list[Character],
    ) -> list[Character]:
        """
        Filter out supporting characters that are word fragments of main cast names.

        Common pattern: "Dillingham" (6 mentions) is a middle name in "James Dillingham Young".
        The text discusses "the 'Dillingham' had been flung to the breeze" - the name itself
        as a subject, not a person reference.

        This filters out:
        - Single-word supporting names that are middle names in main cast full names
        - Single-word supporting names that are last names in main cast full names
          (if not already merged by previous steps)

        Args:
            main_cast: List of main cast characters (already merged)
            supporting_cast: List of supporting cast characters

        Returns:
            Filtered supporting cast list
        """
        # Collect all full names from main cast (canonical + aliases)
        main_cast_full_names = []
        for main_char in main_cast:
            # Add canonical name
            main_cast_full_names.append(main_char.canonical_name)
            # Add all aliases
            main_cast_full_names.extend(main_char.aliases)

        # Filter supporting cast
        filtered_supporting = []
        for supp_char in supporting_cast:
            supp_name = supp_char.canonical_name.strip()

            # Only filter single-word names
            if " " in supp_name:
                filtered_supporting.append(supp_char)
                continue

            # Check if this single-word name is a word fragment of any main cast full name
            is_fragment = False
            for full_name in main_cast_full_names:
                # Skip single-word main cast names (no fragments possible)
                if " " not in full_name:
                    continue

                # Split full name into words
                full_name_words = full_name.split()

                # Check if supp_name is a middle or last name (but NOT first name)
                # We allow first-name-only matches (handled by reverse pass merge)
                # We filter out middle/last name fragments
                if len(full_name_words) >= 3:
                    # 3+ word name - check if supp_name is a middle name (not first or last)
                    middle_names = full_name_words[1:-1]
                    if any(supp_name.lower() == word.strip(".,;:").lower() for word in middle_names):
                        logger.info(
                            f"Filtering name fragment '{supp_name}' (middle name of '{full_name}')"
                        )
                        is_fragment = True
                        break

            if not is_fragment:
                filtered_supporting.append(supp_char)

        return filtered_supporting

    def _convert_to_pipeline_characters(
        self,
        main_cast: list[Character],
        supporting_cast: list[Character],
        mention_results: dict = None,
    ) -> list[PipelineCharacter]:
        """Convert model Characters to pipeline Characters for output compatibility."""
        result = []
        mention_results = mention_results or {}

        for char in main_cast:
            # Get mention data if available
            mention_info = mention_results.get(char.id)

            # Convert mentions from models.CharacterMention to pipeline.CharacterMention
            mentions_list = []
            if mention_info:
                from ..pipeline.character_extraction.models import (
                    CharacterMention as PipelineMention,
                )

                for m in mention_info.mentions:
                    pipeline_mention = PipelineMention(
                        text=m.name_form,
                        position=m.position,
                        chapter_index=m.chapter_index or 0,
                        context=m.context,
                        in_dialogue=False,  # V2 doesn't track this
                        is_agentive=False,  # V2 doesn't track this
                    )
                    mentions_list.append(pipeline_mention)

            chapters_present = (
                list(mention_info.chapter_distribution.keys())
                if mention_info and mention_info.chapter_distribution
                else []
            )

            # Convert model.Character to pipeline Character
            pc = PipelineCharacter(
                id=char.id,
                canonical_name=char.canonical_name,
                aliases=char.aliases,
                mentions=mentions_list,  # Use actual mentions from search
                first_appearance_chapter=char.first_appearance_chapter or 0,
                mention_count=char.mention_count,
                chapters_present=chapters_present,
                confidence=0.85 if char.confidence.value == "high" else 0.6,
                supporting_strategies=["v2_summary_extraction"],
                description=self._get_description_text(char),
                is_narrator=char.is_narrator,
                narrative_role=char.narrative_role,
                role=char.role or "main",
            )
            result.append(pc)

        for char in supporting_cast:
            # Supporting cast doesn't have mention search results (uses NER counts)
            # So mentions list remains empty for them
            mention_info = mention_results.get(char.id) if mention_results else None

            mentions_list = []
            if mention_info:
                from ..pipeline.character_extraction.models import (
                    CharacterMention as PipelineMention,
                )

                for m in mention_info.mentions:
                    pipeline_mention = PipelineMention(
                        text=m.name_form,
                        position=m.position,
                        chapter_index=m.chapter_index or 0,
                        context=m.context,
                        in_dialogue=False,  # V2 doesn't track this
                        is_agentive=False,  # V2 doesn't track this
                    )
                    mentions_list.append(pipeline_mention)

            chapters_present = (
                list(mention_info.chapter_distribution.keys())
                if mention_info and mention_info.chapter_distribution
                else []
            )

            pc = PipelineCharacter(
                id=char.id,
                canonical_name=char.canonical_name,
                aliases=char.aliases,
                mentions=mentions_list,
                first_appearance_chapter=char.first_appearance_chapter or 0,
                mention_count=char.mention_count,
                chapters_present=chapters_present,
                confidence=0.4,  # Lower confidence for NER extraction
                supporting_strategies=["v2_ner_extraction"],
                description="",
                is_narrator=False,
                narrative_role=None,
                role="minor",
            )
            result.append(pc)

        return result

    def _get_description_text(self, char: Character) -> str:
        """Get description text from a Character."""
        if char.descriptions:
            return char.descriptions[0].text
        return ""
