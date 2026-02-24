"""
CharacterAgent - Summary-Driven Character Extraction

This agent implements the profile-first approach:
1. Extract main cast profiles from chapter summaries (F1)
2. Search for mentions deterministically (F2)
3. Apply grounding gate to reject hallucinations (F2b)
4. Detect narrator from summaries (F4)
5. Extract supporting cast via NER (F3)

Key improvements over v1:
- No complex merge heuristics
- Summaries provide identity context upfront
- Grounding prevents hallucinated characters
- Dramatically simpler code (<500 lines vs 2500+)
"""

import logging
import time
from typing import Optional

from ..llm.client import LLMClient
from ..models import Character, StructuralElement, StructureType
from ..pipeline.character_extraction.models import Character as PipelineCharacter
from ..pipeline.character_extraction.models import CharacterMap
from ..pipeline.character_extraction_v2 import (
    GroundingGate,
    MainCastExtractor,
    MentionSearcher,
    NarratorDetector,
    NarratorInfo,
    SupportingCastExtractor,
)
from ..utils.similarity import names_similar, string_similarity
from ..utils.debug_log import append_debug_event
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

# Standard English diminutive forms mapped to their canonical long-form equivalents.
# Used to merge nickname variants extracted by NER (e.g., "Johnny" → alias of "John").
# Only unambiguous one-to-one mappings are included; standalone names like "Ted" or "Bob"
# are intentionally excluded to avoid merging genuinely different characters.
STANDARD_DIMINUTIVES: dict[str, str] = {
    "johnny": "john",
    "johnnie": "john",
    "jimmy": "james",
    "jimmie": "james",
    "charlie": "charles",
    "tommy": "thomas",
    "bobby": "robert",
    "robbie": "robert",
    "billy": "william",
    "willie": "william",
    "freddie": "frederick",
    "freddy": "frederick",
}


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
    ):
        self.llm = llm_client
        self.config = config or AgentConfig()
        self.min_grounding_mentions = min_grounding_mentions
        self.competitive_config = competitive_config

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
        main_cast_extractor = MainCastExtractor(self.llm, self.competitive_config)
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

        # STEP 1.5: Merge title-variant characters (deterministic post-processing)
        characters = self._merge_title_variants(characters)
        logger.info(f"V2 Step 1.5 complete: {len(characters)} after title-variant merge")

        # STEP 2: Search for mentions (F2)
        logger.info("V2 Step 2: Searching for character mentions")
        searcher = MentionSearcher(context.text, chapters)
        mention_results = searcher.search_all(characters)
        characters = searcher.update_characters_with_mentions(characters, mention_results)

        # STEP 3: Apply grounding gate (F2b)
        logger.info("V2 Step 3: Applying grounding gate")
        grounding_gate = GroundingGate(
            min_mentions=self.min_grounding_mentions,
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

        # STEP 3.1: Fallback — when main_cast extraction returned 0 grounded characters,
        # retry with a simpler prompt on just the plot_summary text.
        # The main_cast LLM may fail on long/complex chapter summaries while succeeding
        # on a shorter, more focused summary. This is a universal safety net.
        if not main_cast and plot_summary:
            logger.warning(
                "V2 Step 3.1 FALLBACK: main_cast empty after grounding. "
                "Retrying with simpler prompt on plot_summary."
            )
            fallback_prompt = (
                "List every named character or sentient entity in this story. "
                "Include humans, non-human beings, AI, and any named force that acts with agency. "
                "Return JSON array only.\n\n"
                "STORY SUMMARY:\n{summary}\n\n"
                "Return a JSON array:\n"
                '[{{"canonical_name": "Name", "role": "protagonist|antagonist|supporting", '
                '"description": "brief description", "is_symbolic": false}}]'
            ).format(summary=plot_summary[:3000])

            fallback_result, fallback_response = self.llm.query_json(fallback_prompt)
            logger.info(
                f"V2 Step 3.1 fallback LLM: success={fallback_response.success}, "
                f"result_type={type(fallback_result).__name__ if fallback_result is not None else 'None'}"
            )
            if fallback_response.success and fallback_result is not None:
                fallback_profiles = main_cast_extractor._parse_pass1_results(fallback_result)
                logger.info(f"V2 Step 3.1 fallback parsed {len(fallback_profiles)} profiles")
                if fallback_profiles:
                    fallback_chars = main_cast_extractor.profiles_to_characters(fallback_profiles)
                    fallback_mentions = searcher.search_all(fallback_chars)
                    fallback_chars = searcher.update_characters_with_mentions(
                        fallback_chars, fallback_mentions
                    )
                    mention_results.update(fallback_mentions)
                    # Fallback characters come from the LLM-generated plot_summary, which is
                    # itself a distillation of the text. They are implicitly grounded and do
                    # NOT need the grounding gate — which would incorrectly reject short names
                    # like "AM" (2-letter abbreviation with ambiguous lowercase matches).
                    main_cast = fallback_chars
                    logger.info(
                        f"V2 Step 3.1 fallback: {len(fallback_profiles)} profiles → "
                        f"{len(main_cast)} characters (grounding skipped for plot_summary fallback)"
                    )
            else:
                logger.warning(
                    f"V2 Step 3.1 fallback LLM failed: {fallback_response.error}"
                )

        # STEP 3.4: Pre-merge same-firstname variants (handles Daisy Buchanan + Daisy Fay case)
        # This must run BEFORE the main merge to avoid the ambiguity problem where
        # "Daisy" matches multiple full names and gets skipped
        logger.info("V2 Step 3.4: Pre-merging same-firstname variants")
        main_cast = self._merge_same_firstname_variants(main_cast)
        logger.info(f"V2 Step 3.4 complete: {len(main_cast)} after same-firstname merge")

        # STEP 3.5: Merge within main cast (last-name-only, spelling variants, first-name-only)
        logger.info("V2 Step 3.5: Merging within main cast")
        main_cast, within_main_aliases_added = self._merge_within_main_cast(main_cast)

        # STEP 3.6: Deduplicate alias-canonical conflicts
        # Handles cases like "Myrtle Wilson" (canonical) + "Mrs. Wilson" (canonical with alias "Myrtle Wilson")
        logger.info("V2 Step 3.6: Deduplicating alias-canonical conflicts")
        main_cast, alias_dedupe_aliases_added = self._deduplicate_alias_canonical_conflicts(
            main_cast
        )
        if alias_dedupe_aliases_added:
            within_main_aliases_added.update(alias_dedupe_aliases_added)

        # Re-search mentions for characters that gained new aliases
        if within_main_aliases_added:
            logger.info(
                f"Re-searching mentions for {len(within_main_aliases_added)} characters with new aliases"
            )
            for char_id in within_main_aliases_added:
                char = next((c for c in main_cast if c.id == char_id), None)
                if char:
                    result = searcher.search_character(char)
                    char.mention_count = result.total_mentions
                    # Transfer actual mentions for profile generation
                    char.mentions = result.mentions
                    # CRITICAL FIX: Update mention_results dict so profile generation has full mention list
                    mention_results[char.id] = result
                    if result.chapter_distribution:
                        chapters = sorted(result.chapter_distribution.keys())
                        char.first_appearance_chapter = chapters[0]

        logger.info(f"V2 Step 3.5 complete: {len(main_cast)} main cast after within-cast merge")

        # STEP 3.7: Defensive split for wrongly-merged titled characters
        # Handles LLM hallucinations where "M. Waldman" gets "M. Krempe" as an alias
        # despite explicit prompt instructions
        logger.info("V2 Step 3.7: Splitting wrongly-merged titled characters")
        main_cast, split_count = self._split_wrongly_merged_titled_characters(main_cast)
        if split_count > 0:
            logger.warning(
                f"V2 Step 3.7: Split {split_count} wrongly-merged titled character pairs "
                f"(LLM ignored prompt instructions)"
            )

        # STEP 3.8: Defensive split for semantic conflicts
        # Handles LLM hallucinations where semantically incompatible terms get merged
        # (e.g., "the creature" as alias of "the old man")
        logger.info("V2 Step 3.8: Splitting semantically conflicting aliases")

        # region agent log
        try:
            focus = []
            for c in main_cast:
                blob = (c.canonical_name + " " + " ".join(c.aliases)).lower()
                if any(
                    k in blob
                    for k in (
                        "creature",
                        "monster",
                        "fiend",
                        "daemon",
                        "wretch",
                        "being",
                        "lacey",
                        "old man",
                    )
                ):
                    focus.append(
                        {
                            "id": c.id,
                            "canonical": c.canonical_name,
                            "aliases": list(c.aliases),
                            "mentions": c.mention_count,
                        }
                    )
            append_debug_event(
                {
                    "sessionId": "debug-session",
                    "runId": "frankenstein-pre",
                    "hypothesisId": "H2",
                    "location": "src/agents/characters.py:step3.8",
                    "message": "Pre semantic-split focused main_cast snapshot",
                    "data": {"focus": focus},
                    "timestamp": int(time.time() * 1000),
                }
            )
        except Exception:
            pass
        # endregion

        main_cast, semantic_split_count = self._split_semantic_conflicts(main_cast)
        if semantic_split_count > 0:
            logger.warning(
                f"V2 Step 3.8: Split {semantic_split_count} semantically conflicting alias pairs "
                f"(LLM merged incompatible entity types)"
            )

        # region agent log
        try:
            split_focus = []
            for c in main_cast:
                if not isinstance(c.id, str) or not c.id.startswith("split_"):
                    continue
                blob = (c.canonical_name + " " + " ".join(c.aliases)).lower()
                if any(
                    k in blob
                    for k in (
                        "creature",
                        "monster",
                        "fiend",
                        "daemon",
                        "wretch",
                        "being",
                        "lacey",
                        "old man",
                    )
                ):
                    split_focus.append(
                        {
                            "id": c.id,
                            "canonical": c.canonical_name,
                            "aliases": list(c.aliases),
                            "mentions": c.mention_count,
                        }
                    )

            append_debug_event(
                {
                    "sessionId": "debug-session",
                    "runId": "frankenstein-pre",
                    "hypothesisId": "H2",
                    "location": "src/agents/characters.py:step3.8",
                    "message": "Post semantic-split created split_* characters (focused subset)",
                    "data": {
                        "semantic_split_count": semantic_split_count,
                        "split_focus": split_focus,
                    },
                    "timestamp": int(time.time() * 1000),
                }
            )
        except Exception:
            pass
        # endregion

        # STEP 3.9: Post-split repair pass
        # Splitting creates new split_* character stubs with mention_count=0.
        # We must ground them and then re-run within-main merges so they can be absorbed
        # into existing descriptive clusters (e.g., creature/monster variants).
        split_stubs = [c for c in main_cast if isinstance(c.id, str) and c.id.startswith("split_")]
        if split_stubs:
            logger.info(f"V2 Step 3.9: Grounding {len(split_stubs)} split_* character stub(s)")
            for char in split_stubs:
                result = searcher.search_character(char)
                char.mention_count = result.total_mentions
                # Transfer actual mentions for profile generation
                char.mentions = result.mentions
                # Keep mention_results updated for downstream profile generation
                mention_results[char.id] = result
                if result.chapter_distribution:
                    chapters = sorted(result.chapter_distribution.keys())
                    char.first_appearance_chapter = chapters[0]

            logger.info("V2 Step 3.9: Re-running within-main merges after split repair")
            main_cast, post_split_aliases_added = self._merge_within_main_cast(main_cast)
            main_cast, post_split_dedupe_added = self._deduplicate_alias_canonical_conflicts(
                main_cast
            )
            if post_split_dedupe_added:
                post_split_aliases_added.update(post_split_dedupe_added)

            # Re-search mentions for characters that gained new aliases during post-split merges
            if post_split_aliases_added:
                logger.info(
                    f"V2 Step 3.9: Re-searching mentions for {len(post_split_aliases_added)} post-split merged character(s)"
                )
                for char_id in post_split_aliases_added:
                    char = next((c for c in main_cast if c.id == char_id), None)
                    if char:
                        result = searcher.search_character(char)
                        char.mention_count = result.total_mentions
                        char.mentions = result.mentions
                        mention_results[char.id] = result
                        if result.chapter_distribution:
                            chapters = sorted(result.chapter_distribution.keys())
                            char.first_appearance_chapter = chapters[0]

            # region agent log
            try:
                focus = []
                for c in main_cast:
                    blob = (c.canonical_name + " " + " ".join(c.aliases)).lower()
                    if any(
                        k in blob
                        for k in (
                            "creature",
                            "monster",
                            "fiend",
                            "daemon",
                            "wretch",
                            "being",
                            "lacey",
                            "old man",
                        )
                    ):
                        focus.append(
                            {
                                "id": c.id,
                                "canonical": c.canonical_name,
                                "aliases": list(c.aliases),
                                "mentions": c.mention_count,
                                "is_narrator": getattr(c, "is_narrator", None),
                            }
                        )

                append_debug_event(
                    {
                        "sessionId": "debug-session",
                        "runId": "frankenstein-postfix",
                        "hypothesisId": "H4",
                        "location": "src/agents/characters.py:step3.9",
                        "message": "Post-split repair focus snapshot (main_cast)",
                        "data": {"focus": focus},
                        "timestamp": int(time.time() * 1000),
                    }
                )
            except Exception:
                pass
            # endregion

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
        # Adaptive threshold: short texts (< 10K words) need a lower threshold since
        # characters with only 2 text mentions may still be significant
        text_word_count = len(context.text.split())
        supporting_min_mentions = 2 if text_word_count < 10000 else 3
        logger.info(
            f"V2 Step 5: text_word_count={text_word_count}, "
            f"supporting_min_mentions={supporting_min_mentions}"
        )
        supporting_extractor = SupportingCastExtractor(
            context.text,
            min_mentions=supporting_min_mentions,
        )
        supporting_cast = supporting_extractor.extract(main_cast_names)

        logger.info(f"V2 Step 5 complete: {len(supporting_cast)} supporting characters")

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

        # STEP 5.3: Merge narrator placeholders with their actual named character
        # If the narrator is "the protagonist", "the narrator", etc., find their real name
        main_cast, supporting_cast, narrator_info, narrator_merged_ids = (
            self._merge_narrator_placeholder(
                main_cast, supporting_cast, narrator_info, context.text
            )
        )
        logger.info("V2 Step 5.3 complete: narrator placeholder merge check done")

        # STEP 5.4: Re-search mentions for narrator-merged characters
        # The merge added the placeholder name as an alias, so we need to re-search
        # to capture all mentions (both the original name and the placeholder)
        if narrator_merged_ids:
            logger.info(
                f"Re-searching mentions for {len(narrator_merged_ids)} narrator-merged characters"
            )
            for char_id in narrator_merged_ids:
                char = next((c for c in main_cast if c.id == char_id), None)
                if char:
                    result = searcher.search_character(char)
                    char.mention_count = result.total_mentions
                    # Transfer actual mentions for profile generation
                    char.mentions = result.mentions
                    # CRITICAL FIX: Update mention_results dict so profile generation has full mention list
                    mention_results[char.id] = result
                    if result.chapter_distribution:
                        chapters = sorted(result.chapter_distribution.keys())
                        char.first_appearance_chapter = chapters[0]
                    logger.info(
                        f"Narrator-merged character '{char.canonical_name}' now has "
                        f"{char.mention_count} total mentions (including placeholder)"
                    )

        # STEP 5.5: Merge last-name-only supporting characters as aliases
        main_cast, supporting_cast, aliases_added = self._merge_lastname_aliases(
            main_cast, supporting_cast
        )

        # Re-search mentions for characters that gained new aliases
        if aliases_added:
            logger.info(
                f"Re-searching mentions for {len(aliases_added)} characters with new aliases"
            )
            for char_id in aliases_added:
                char = next((c for c in main_cast if c.id == char_id), None)
                if char:
                    result = searcher.search_character(char)
                    char.mention_count = result.total_mentions
                    # Transfer actual mentions for profile generation
                    char.mentions = result.mentions
                    # CRITICAL FIX: Update mention_results dict so profile generation has full mention list
                    mention_results[char.id] = result
                    if result.chapter_distribution:
                        chapters = sorted(result.chapter_distribution.keys())
                        char.first_appearance_chapter = chapters[0]

        logger.info(
            f"V2 Step 5.5 complete: {len(main_cast)} main cast, "
            f"{len(supporting_cast)} supporting after last-name merge"
        )

        # STEP 5.6: Merge within supporting cast (last-name-only, spelling variants)
        supporting_cast, supp_aliases_added = self._merge_within_supporting_cast(supporting_cast)

        # Re-search mentions for supporting characters that gained new aliases
        if supp_aliases_added:
            logger.info(
                f"Re-searching mentions for {len(supp_aliases_added)} supporting chars with new aliases"
            )
            for char_id in supp_aliases_added:
                char = next((c for c in supporting_cast if c.id == char_id), None)
                if char:
                    result = searcher.search_character(char)
                    char.mention_count = result.total_mentions
                    # Transfer actual mentions for profile generation
                    char.mentions = result.mentions
                    # CRITICAL FIX: Update mention_results dict so profile generation has full mention list
                    mention_results[char.id] = result
                    if result.chapter_distribution:
                        chapters = sorted(result.chapter_distribution.keys())
                        char.first_appearance_chapter = chapters[0]

        logger.info(
            f"V2 Step 5.6 complete: {len(supporting_cast)} supporting after within-supporting merge"
        )

        # STEP 5.6.5: Merge descriptive synonyms from supporting into main cast
        # Handles "the creature" (main) + "the monster" (supporting) → merge monster into creature
        logger.info("V2 Step 5.6.5: Merging descriptive synonyms across main/supporting casts")
        supporting_cast, cross_cast_aliases_added = self._merge_descriptive_synonyms_across_casts(
            main_cast, supporting_cast
        )

        # Re-search mentions for main cast characters that gained new aliases
        if cross_cast_aliases_added:
            logger.info(
                f"Re-searching mentions for {len(cross_cast_aliases_added)} main cast chars with new aliases"
            )
            for char_id in cross_cast_aliases_added:
                char = next((c for c in main_cast if c.id == char_id), None)
                if char:
                    result = searcher.search_character(char)
                    char.mention_count = result.total_mentions
                    # Transfer actual mentions for profile generation
                    char.mentions = result.mentions
                    # CRITICAL FIX: Update mention_results dict so profile generation has full mention list
                    mention_results[char.id] = result
                    if result.chapter_distribution:
                        chapters = sorted(result.chapter_distribution.keys())
                        char.first_appearance_chapter = chapters[0]

        logger.info(
            f"V2 Step 5.6.5 complete: {len(main_cast)} main cast, {len(supporting_cast)} supporting "
            f"after cross-cast synonym merge"
        )

        # STEP 5.6.6: Merge bare surnames into family descriptive handles
        # Handles "De Lacey" (supporting) + "the old man" (main, father of Felix/Agatha De Lacey)
        logger.info("V2 Step 5.6.6: Merging bare surnames into family descriptive handles")
        supporting_cast, surname_aliases_added = self._merge_surname_into_family_descriptive(
            main_cast, supporting_cast
        )

        # Re-search mentions for main cast characters that gained new aliases
        if surname_aliases_added:
            logger.info(
                f"Re-searching mentions for {len(surname_aliases_added)} main cast chars with new surname aliases"
            )
            for char_id in surname_aliases_added:
                char = next((c for c in main_cast if c.id == char_id), None)
                if char:
                    result = searcher.search_character(char)
                    char.mention_count = result.total_mentions
                    char.mentions = result.mentions
                    mention_results[char.id] = result
                    if result.chapter_distribution:
                        chapters = sorted(result.chapter_distribution.keys())
                        char.first_appearance_chapter = chapters[0]

        logger.info(
            f"V2 Step 5.6.6 complete: {len(main_cast)} main cast, {len(supporting_cast)} supporting "
            f"after surname-family merge"
        )

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

        # STEP 5.7.5: Update mention counts for supporting cast BEFORE promotion
        # Supporting cast NER counts may undercount actual text occurrences (spaCy misses some
        # entity detections). Running deterministic mention search here ensures that STEP 5.8
        # promotion decisions are based on accurate counts, not NER approximations.
        if supporting_cast:
            logger.info(
                f"V2 Step 5.7.5: Pre-promotion mention search for {len(supporting_cast)} supporting characters"
            )
            try:
                pre_promotion_results = searcher.search_all(supporting_cast)
                supporting_cast = searcher.update_characters_with_mentions(
                    supporting_cast, pre_promotion_results
                )
                mention_results.update(pre_promotion_results)
                for char in supporting_cast:
                    r = pre_promotion_results.get(char.id)
                    if r and r.chapter_distribution:
                        chapter_indices = sorted(r.chapter_distribution.keys())
                        char.first_appearance_chapter = chapter_indices[0]
            except Exception as e:
                logger.warning(f"Pre-promotion mention search failed: {e}")

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

        # Scale thresholds for short texts where absolute counts are misleading
        # e.g., 14 mentions in a 2,354-word story = ~595 per 100K words (very significant)
        word_count = len(context.text.split()) if context.text else 100_000
        if word_count < 20_000:
            scale = 100_000 / max(word_count, 1000)
            effective_protagonist = max(10, int(PROTAGONIST_THRESHOLD / scale))
            effective_main = max(5, int(MAIN_THRESHOLD / scale))
            effective_promotion = max(3, int(PROMOTION_THRESHOLD / scale))
            logger.info(
                f"V2 Step 5.8: Short text ({word_count} words), scaled thresholds: "
                f"protagonist={effective_protagonist}, main={effective_main}, promotion={effective_promotion}"
            )
        else:
            effective_protagonist = PROTAGONIST_THRESHOLD
            effective_main = MAIN_THRESHOLD
            effective_promotion = PROMOTION_THRESHOLD

        promoted_chars = []
        remaining_supporting = []

        for char in supporting_cast:
            if char.mention_count >= effective_promotion:
                # Promote to main cast with role based on mention count
                if char.mention_count >= effective_protagonist:
                    char.role = "protagonist"
                elif char.mention_count >= effective_main:
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

        # STEP 5.8.5: Re-run narrator detection if narrator was not identified in STEP 4
        # This handles the case where main_cast was empty during STEP 4 (LLM extraction failed
        # or all candidates were filtered by grounding), but promotion in STEP 5.8 has now
        # added characters to main_cast. With actual characters available, narrator detection
        # has better context to match the narrator name to a known character.
        # Also re-runs when narrator was named but could not be matched (narrator_character_id is None),
        # e.g. when STEP 4 identified "Ted" as narrator but main_cast was empty so no match was possible.
        if (
            narrator_info.pov in ("unknown", "")
            or narrator_info.narrator_name is None
            or narrator_info.narrator_character_id is None
        ) and main_cast:
            logger.info(
                f"V2 Step 5.8.5: Re-running narrator detection with {len(main_cast)} characters "
                f"(initial detection returned pov='{narrator_info.pov}')"
            )
            try:
                narrator_info = narrator_detector.detect(
                    chapter_summaries, main_cast, plot_summary
                )
                main_cast = narrator_detector.update_characters_with_narrator(
                    main_cast, narrator_info
                )
                logger.info(
                    f"V2 Step 5.8.5 complete: pov={narrator_info.pov}, "
                    f"narrator={narrator_info.narrator_name}"
                )
            except Exception as e:
                logger.warning(f"Narrator re-detection failed: {e}")

        # STEP 5.8.5b: Search supporting_cast for narrator name fragments.
        # When narrator_name was identified (e.g., "Nick Carraway") but not matched
        # to any main_cast character, the narrator may exist in supporting_cast as
        # fragments (e.g., "Nick" + "Carraway") that individually fell below the
        # promotion threshold.  Merge any matches and promote to main_cast BEFORE
        # the heuristic fallback, which would otherwise pick the wrong character.
        if (
            narrator_info.narrator_name is not None
            and narrator_info.narrator_character_id is None
            and supporting_cast
        ):
            result = self._find_narrator_in_supporting(
                narrator_info.narrator_name, supporting_cast
            )
            if result is not None:
                merged_narrator, supporting_cast = result
                main_cast.append(merged_narrator)
                narrator_info = NarratorInfo(
                    pov=narrator_info.pov or "first-person",
                    narrator_name=merged_narrator.canonical_name,
                    narrator_character_id=merged_narrator.id,
                    confidence=max(narrator_info.confidence, 0.75),
                )
                logger.info(
                    f"V2 Step 5.8.5b: Narrator '{merged_narrator.canonical_name}' "
                    f"found in supporting cast, promoted to main cast "
                    f"(mention_count={merged_narrator.mention_count})"
                )

        # STEP 5.8.6: Heuristic narrator fallback for confirmed first-person narratives.
        # When LLM narrator detection has failed (narrator_character_id is still None)
        # but the summaries metadata confirms first-person POV, use a universal heuristic:
        # in first-person narratives the narrator tends to have the lowest name-mention count
        # (they use "I" instead of their own name), so the least-mentioned character who
        # appears in the plot_summary is the most likely narrator.
        narrative_style = self._get_narrative_style(context)
        if (
            narrative_style
            and "first-person" in narrative_style.lower()
            and narrator_info.narrator_character_id is None
            and main_cast
        ):
            narrator_candidate = self._heuristic_narrator_from_mention_count(
                main_cast, plot_summary
            )
            if narrator_candidate:
                narrator_candidate.is_narrator = True
                narrator_candidate.narrative_role = "First-Person Narrator"
                if narrator_candidate.role not in ("protagonist",):
                    narrator_candidate.role = "protagonist"
                narrator_info = NarratorInfo(
                    pov="first-person",
                    narrator_name=narrator_candidate.canonical_name,
                    narrator_character_id=narrator_candidate.id,
                    confidence=0.6,
                )
                logger.info(
                    f"V2 Step 5.8.6: Heuristic narrator fallback identified "
                    f"'{narrator_candidate.canonical_name}' "
                    f"(mention_count={narrator_candidate.mention_count}, "
                    f"narrative_style='{narrative_style}')"
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
                        chapter_indices = sorted(r.chapter_distribution.keys())
                        char.first_appearance_chapter = chapter_indices[0]
            except Exception as e:
                logger.warning(f"Supporting cast mention search failed: {e}")

        # Build final CharacterMap
        all_characters = self._convert_to_pipeline_characters(
            main_cast, supporting_cast, mention_results
        )

        # Calculate confidence breakdown
        high = sum(1 for c in all_characters if c.confidence >= 0.7)
        medium = sum(1 for c in all_characters if 0.4 <= c.confidence < 0.7)
        low = sum(1 for c in all_characters if c.confidence < 0.4)

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
        """Extract chapter summaries from context."""
        # Try getting from previous_results (SummaryAgent output)
        summaries_result = context.get_result("summaries")
        logger.info(
            f"[DIAG] _get_chapter_summaries: summaries_result type={type(summaries_result).__name__ if summaries_result else 'None'}, "
            f"has_summaries={hasattr(summaries_result, 'summaries') if summaries_result else False}"
        )
        if summaries_result:
            # SummaryAgent returns a list of ChapterSummary objects or similar
            if hasattr(summaries_result, "summaries"):
                result = []
                for s in summaries_result.summaries:
                    if not s.summary:
                        continue
                    text = s.summary
                    # Prepend structured character list when available.
                    # CHARACTER_IDENTIFICATION_PROMPT references `characters_present` lists
                    # but they were never actually included in the text — this fixes that gap.
                    chars = getattr(s, "characters_present", None) or []
                    if chars:
                        text = f"[Characters present: {', '.join(chars)}]\n{text}"
                    result.append(text)
                logger.info(f"[DIAG] _get_chapter_summaries: found {len(result)} summaries via .summaries attribute, total_chars={sum(len(s) for s in result)}")
                return result
            elif isinstance(summaries_result, list):
                result = [
                    s.get("summary") if isinstance(s, dict) else str(s)
                    for s in summaries_result
                    if s
                ]
                logger.info(f"[DIAG] _get_chapter_summaries: found {len(result)} summaries via list path")
                return result

        # Try getting from chapter_map (summaries may be stored on chapters)
        if context.chapter_map:
            summaries = []
            chapters = getattr(context.chapter_map, "chapters", [])
            for ch in chapters:
                if hasattr(ch, "summary") and ch.summary:
                    summaries.append(ch.summary)
            if summaries:
                logger.info(f"[DIAG] _get_chapter_summaries: found {len(summaries)} summaries via chapter_map.chapters")
                return summaries

        logger.warning("[DIAG] _get_chapter_summaries: no summaries found from any source")
        return []

    def _get_chapters(self, context: AgentContext) -> list[StructuralElement]:
        """Get chapter structural elements from context."""
        if context.chapter_map:
            chapters = getattr(context.chapter_map, "chapters", [])
            # Convert to StructuralElement if needed
            result = []
            for ch in chapters:
                if isinstance(ch, StructuralElement):
                    result.append(ch)
                elif hasattr(ch, "start_position"):
                    # Create StructuralElement from chapter data
                    elem = StructuralElement(
                        type=StructureType.CHAPTER,
                        index=getattr(ch, "index", 0),
                        start_position=ch.start_position,
                        end_position=getattr(ch, "end_position", ch.start_position + 1000),
                    )
                    result.append(elem)
            return result
        return []

    def _get_plot_summary(self, context: AgentContext) -> Optional[str]:
        """Get overall plot summary if available.

        ChapterSummaryMap does not have a .plot_summary attribute, so we construct
        a combined summary from the available chapter summaries. This combined text
        gives narrator detection and main cast extraction a holistic view of the story.
        """
        summaries_result = context.get_result("summaries")
        if summaries_result:
            # Primary: ChapterSummaryMap.plot_summary (if it exists in some variant)
            if hasattr(summaries_result, "plot_summary"):
                ps = summaries_result.plot_summary
                # Handle nested dict structure (e.g., {"plot_summary": "...", "narrative_style": "..."})
                if isinstance(ps, dict):
                    ps = ps.get("plot_summary") or ps.get("summary") or ps.get("text")
                if isinstance(ps, str) and ps.strip():
                    return ps
            # Fallback: dict-type result
            if isinstance(summaries_result, dict):
                ps = summaries_result.get("plot_summary")
                if isinstance(ps, dict):
                    ps = ps.get("plot_summary") or ps.get("summary") or ps.get("text")
                if isinstance(ps, str) and ps.strip():
                    return ps
            # Construct from chapter summaries when no dedicated plot_summary exists
            # (ChapterSummaryMap has .summaries but no .plot_summary)
            if hasattr(summaries_result, "summaries") and summaries_result.summaries:
                parts = [s.summary for s in summaries_result.summaries if s.summary]
                if parts:
                    combined = "\n\n".join(parts)
                    logger.info(
                        f"[DIAG] _get_plot_summary: constructed from {len(parts)} chapter summaries, "
                        f"total_chars={len(combined)}"
                    )
                    return combined
        return None

    def _collect_all_names(self, characters: list[Character]) -> set[str]:
        """Collect all names and aliases from characters."""
        names = set()
        for char in characters:
            names.add(char.canonical_name)
            names.update(char.aliases)
        return names

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

    def _merge_narrator_placeholder(
        self,
        main_cast: list[Character],
        supporting_cast: list[Character],
        narrator_info,
        text: str,
    ) -> tuple[list[Character], list[Character], any, set[str]]:
        """
        Merge narrator placeholders (e.g., 'the protagonist', 'the narrator') with their actual named character.

        In first-person narratives, the LLM may extract a placeholder like "the protagonist"
        from summaries, when the character has an actual name mentioned in the text.
        This method attempts to identify and merge such cases.

        Args:
            main_cast: List of main cast characters
            supporting_cast: List of supporting characters
            narrator_info: NarratorInfo object from narrator detection
            text: Full text for searching

        Returns:
            Tuple of (updated_main_cast, updated_supporting_cast, updated_narrator_info, merged_char_ids)
        """
        # Only process for first-person narrators with placeholder names
        if narrator_info.pov != "first-person" or not narrator_info.narrator_character_id:
            return main_cast, supporting_cast, narrator_info, set()

        # Find the narrator character
        narrator_char = None
        narrator_in_main = True
        for char in main_cast:
            if char.id == narrator_info.narrator_character_id:
                narrator_char = char
                break

        if not narrator_char:
            # Check supporting cast
            for char in supporting_cast:
                if char.id == narrator_info.narrator_character_id:
                    narrator_char = char
                    narrator_in_main = False
                    break

        if not narrator_char:
            return main_cast, supporting_cast, narrator_info, set()

        # Check if narrator is a placeholder (unnamed or generic descriptor)
        narrator_name_lower = narrator_char.canonical_name.lower()
        placeholder_patterns = [
            "the protagonist",
            "the narrator",
            "narrator",
            "protagonist",
            "main character",
            "the main character",
        ]

        is_placeholder = any(pattern in narrator_name_lower for pattern in placeholder_patterns)

        if not is_placeholder:
            return main_cast, supporting_cast, narrator_info, set()

        logger.info(
            f"Narrator placeholder detected: '{narrator_char.canonical_name}' "
            f"- attempting to find actual character name"
        )

        # Search for the narrator's actual name in all characters
        # Look for a character that:
        # 1. Has a proper name (not another placeholder)
        # 2. Has relatively high mentions in supporting cast OR is in main cast
        # 3. Is addressed by name in first-person context

        all_characters = main_cast + supporting_cast
        candidates = []

        for char in all_characters:
            if char.id == narrator_char.id:
                continue

            char_name_lower = char.canonical_name.lower()

            # Skip other placeholders
            is_other_placeholder = any(
                pattern in char_name_lower for pattern in placeholder_patterns
            )
            if is_other_placeholder:
                continue

            # Skip generic descriptors
            if char_name_lower.startswith("the ") and len(char.canonical_name.split()) <= 3:
                continue

            # Proper name candidate (has capital letters indicating a name)
            if len(char.canonical_name) > 1 and char.canonical_name[0].isupper():
                # Simple heuristic: characters with mentions close to narrator's placeholder mentions
                # are likely the same person (the placeholder captured most first-person references)
                candidates.append(char)

        if not candidates:
            logger.info("No named character candidates found for narrator placeholder")
            return main_cast, supporting_cast, narrator_info, set()

        # PRIORITY 1: Match narrator_info.narrator_name to candidates
        # The narrator detector may have identified the narrator by name even if
        # it couldn't match to main_cast (e.g., "Uncle Bill" identified from summaries)
        merge_target = None
        if narrator_info.narrator_name:
            narrator_name_lower = narrator_info.narrator_name.lower()
            for candidate in candidates:
                candidate_name_lower = candidate.canonical_name.lower()
                # Exact match or partial match (first/last name)
                if (
                    narrator_name_lower == candidate_name_lower
                    or narrator_name_lower in candidate_name_lower
                    or candidate_name_lower in narrator_name_lower
                ):
                    merge_target = candidate
                    logger.info(
                        f"Matched narrator '{narrator_info.narrator_name}' to candidate "
                        f"'{candidate.canonical_name}' by name"
                    )
                    break

        # PRIORITY 2 (FALLBACK): Use mention count heuristic
        # For true placeholders like "the protagonist" where narrator detection
        # couldn't determine a name
        if not merge_target:
            logger.info(
                "No name match found, using mention count heuristic to identify narrator"
            )
            # Sort by mention count (higher is more likely to be the narrator)
            candidates.sort(key=lambda c: c.mention_count, reverse=True)
            # Take the top candidate
            merge_target = candidates[0]

        logger.info(
            f"Merging narrator placeholder '{narrator_char.canonical_name}' "
            f"({narrator_char.mention_count} mentions) "
            f"into '{merge_target.canonical_name}' "
            f"({merge_target.mention_count} mentions)"
        )

        # Merge the placeholder into the target character
        # Transfer mention count (will be recalculated with re-search, but keep for safety)
        merge_target.mention_count += narrator_char.mention_count

        # CRITICAL FIX: Transfer the mentions list for profile generation
        # Combine both characters' mentions into the target
        if narrator_char.mentions:
            if not merge_target.mentions:
                merge_target.mentions = []
            merge_target.mentions.extend(narrator_char.mentions)

        # Transfer narrator flag
        merge_target.is_narrator = True
        merge_target.narrative_role = narrator_char.narrative_role

        # Boost confidence for narrator (they're a key character)
        from ...models import ConfidenceLevel

        merge_target.confidence = ConfidenceLevel.HIGH

        # Add placeholder as an alias (for historical record)
        if narrator_char.canonical_name not in merge_target.aliases:
            merge_target.aliases.append(narrator_char.canonical_name)

        # Transfer any description if target doesn't have one
        if not merge_target.descriptions and narrator_char.descriptions:
            merge_target.descriptions = narrator_char.descriptions

        # Remove the placeholder from main_cast or supporting_cast
        if narrator_in_main:
            main_cast = [c for c in main_cast if c.id != narrator_char.id]
        else:
            supporting_cast = [c for c in supporting_cast if c.id != narrator_char.id]

        # Update narrator_info to point to the merged character
        narrator_info.narrator_character_id = merge_target.id
        narrator_info.narrator_name = merge_target.canonical_name

        logger.info(
            f"Narrator placeholder merge complete: narrator is now '{merge_target.canonical_name}'"
        )

        # Return the ID of the merged character so mention search can be re-run
        return main_cast, supporting_cast, narrator_info, {merge_target.id}

    def _merge_title_variants(self, characters: list[Character]) -> list[Character]:
        """
        Merge characters where one canonical name contains another.

        Example: "Sergeant-Major Morris" contains "Morris" → merge as aliases

        This is a deterministic post-processing step to handle LLM variance
        where titles/ranks are inconsistently included.
        """
        if len(characters) <= 1:
            return characters

        merged = []
        skip_indices = set()

        for i, char1 in enumerate(characters):
            if i in skip_indices:
                continue

            # Check if any other character's name is contained in this one
            for j, char2 in enumerate(characters):
                if i == j or j in skip_indices:
                    continue

                name1_lower = char1.canonical_name.lower()
                name2_lower = char2.canonical_name.lower()

                # Check if one name fully contains the other as a word
                # "Sergeant-Major Morris" contains "Morris"
                if self._name_contains_other(name1_lower, name2_lower):
                    # SAFETY CHECK: Don't merge if both have different title prefixes
                    # (e.g., "Mr. White" and "Mrs. White" are DIFFERENT people)
                    if self._are_different_titled_people(
                        char1.canonical_name, char2.canonical_name
                    ):
                        continue  # Skip this merge - they're different people

                    # Merge char2 into char1
                    logger.info(
                        f"Merging title variant: '{char2.canonical_name}' → "
                        f"'{char1.canonical_name}' (as alias)"
                    )

                    # Add char2's canonical name as an alias of char1
                    if char2.canonical_name not in char1.aliases:
                        if self._is_valid_alias(char2.canonical_name, char1.canonical_name):
                            char1.aliases.append(char2.canonical_name)

                    # Add char2's aliases to char1
                    for alias in char2.aliases:
                        if alias not in char1.aliases and alias != char1.canonical_name:
                            if self._is_valid_alias(alias, char1.canonical_name):
                                char1.aliases.append(alias)

                    skip_indices.add(j)

                elif self._name_contains_other(name2_lower, name1_lower):
                    # SAFETY CHECK: Don't merge if both have different title prefixes
                    if self._are_different_titled_people(
                        char1.canonical_name, char2.canonical_name
                    ):
                        continue  # Skip this merge - they're different people

                    # Merge char1 into char2
                    logger.info(
                        f"Merging title variant: '{char1.canonical_name}' → "
                        f"'{char2.canonical_name}' (as alias)"
                    )

                    # Add char1's canonical name as an alias of char2
                    if char1.canonical_name not in char2.aliases:
                        if self._is_valid_alias(char1.canonical_name, char2.canonical_name):
                            char2.aliases.append(char1.canonical_name)

                    # Add char1's aliases to char2
                    for alias in char1.aliases:
                        if alias not in char2.aliases and alias != char2.canonical_name:
                            if self._is_valid_alias(alias, char2.canonical_name):
                                char2.aliases.append(alias)

                    skip_indices.add(i)
                    break  # Don't process this character further

            if i not in skip_indices:
                merged.append(char1)

        return merged

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

    def _name_contains_other(self, longer_name: str, shorter_name: str) -> bool:
        """
        Check if longer_name contains shorter_name as a complete word.

        Examples:
        - "sergeant-major morris" contains "morris" → True
        - "mr. white" contains "white" → True
        - "whitehouse" contains "white" → False (not word boundary)
        """
        import re

        # Escape special regex characters in shorter_name
        escaped = re.escape(shorter_name)

        # Match as a complete word (with word boundaries or punctuation)
        pattern = r"(?:^|[\s\-\.])" + escaped + r"(?:$|[\s\-\.])"
        return bool(re.search(pattern, longer_name))

    def _strip_title(self, name: str) -> str:
        """
        Strip honorific titles from a name.

        Examples:
        - "Mr. Gatsby" → "Gatsby"
        - "Mrs. Wilson" → "Wilson"
        - "Dr. Jekyll" → "Jekyll"
        """
        import re

        # List of common titles
        titles = [
            r"\bMr\.",
            r"\bMrs\.",
            r"\bMs\.",
            r"\bMiss\b",
            r"\bDr\.",
            r"\bDoctor\b",
            r"\bProf\.",
            r"\bProfessor\b",
            r"\bLord\b",
            r"\bLady\b",
            r"\bSir\b",
            r"\bReverend\b",
            r"\bRev\.",
        ]

        # Remove any leading title
        for title in titles:
            name = re.sub(f"^{title}\\s+", "", name, flags=re.IGNORECASE)

        return name.strip()

    def _are_different_titled_people(self, name1: str, name2: str) -> bool:
        """
        Check if two names represent different people with different title prefixes.

        This prevents merging "Mr. White" with "Mrs. White" (husband and wife),
        while still allowing "Sergeant-Major Morris" to merge with "Morris".

        Rules:
        - If both names start with DIFFERENT honorific titles (Mr./Mrs./Miss/Ms./Dr.)
          AND the stripped names are identical → they are DIFFERENT people
        - Otherwise, allow the merge

        Examples:
        - "Mr. White" + "Mrs. White" → True (different people)
        - "Mr. Smith" + "Dr. Smith" → True (different people)
        - "Sergeant-Major Morris" + "Morris" → False (same person)
        - "Mr. White" + "White" → False (same person)

        Returns:
            True if they're different titled people (DON'T merge)
            False if they're the same person or safe to merge
        """
        import re

        # Honorific titles that indicate distinct individuals when different
        honorific_prefixes = [
            r"^(Mr\.|Mrs\.|Miss|Ms\.|Dr\.|M\.)\s+",  # Added M. for French Monsieur
        ]

        # Extract titles and stripped names
        title1 = None
        title2 = None
        stripped1 = name1
        stripped2 = name2

        for pattern in honorific_prefixes:
            match1 = re.match(pattern, name1, flags=re.IGNORECASE)
            if match1:
                title1 = match1.group(1).lower()
                stripped1 = re.sub(pattern, "", name1, flags=re.IGNORECASE).strip()

            match2 = re.match(pattern, name2, flags=re.IGNORECASE)
            if match2:
                title2 = match2.group(1).lower()
                stripped2 = re.sub(pattern, "", name2, flags=re.IGNORECASE).strip()

        # If both have honorific titles, check for different people scenarios
        if title1 and title2:
            # Case 1: Different surnames with any title = different people
            # "M. Waldman" vs "M. Krempe" are different people (same title, different surnames)
            # "Mr. Sloane" vs "Mr. McKee" are different people
            if stripped1.lower() != stripped2.lower():
                return True  # Different titled people - DON'T merge

            # Case 2: Same surname, different title = different people (spouses)
            # "Mr. White" vs "Mrs. White" are different people (same surname, different titles)
            if title1 != title2:
                return True  # Different titled people - DON'T merge

        # Otherwise, safe to merge
        return False

    def _merge_same_firstname_variants(
        self,
        main_cast: list[Character],
    ) -> list[Character]:
        """
        Pre-merge characters that share the same first name but have different last names.

        This handles cases like:
        - "Daisy" + "Daisy Buchanan" + "Daisy Fay" → all same person (maiden/married name)

        Unlike the Wilson case (George Wilson vs Myrtle Wilson = different people with
        different first names), same-first-name variants are likely the same person.

        The key insight: When multiple matches share the SAME first name, they're
        probably the same person. When matches have DIFFERENT first names (like
        George Wilson vs Myrtle Wilson), they're different people.

        Returns:
            Updated list with same-firstname variants merged
        """
        if len(main_cast) <= 1:
            return main_cast

        # Group multi-word names by their first name (lowercase)
        firstname_to_fullnames: dict[str, list[int]] = {}
        single_word_names: dict[str, int] = {}  # first_name_lower -> index

        for idx, char in enumerate(main_cast):
            name = char.canonical_name.strip()
            if not name:
                continue

            parts = name.split()
            first_name = parts[0].lower()

            if len(parts) == 1:
                # Single-word name (potential first-name-only reference)
                single_word_names[first_name] = idx
            else:
                # Multi-word name (full name)
                if first_name not in firstname_to_fullnames:
                    firstname_to_fullnames[first_name] = []
                firstname_to_fullnames[first_name].append(idx)

        chars_to_remove = set()

        # For each first name that has multiple full-name variants, merge them
        for first_name, indices in firstname_to_fullnames.items():
            if len(indices) < 2:
                continue

            # Multiple full names share the same first name (e.g., "Daisy Buchanan", "Daisy Fay")
            # These are likely the same person with maiden/married names
            [(idx, main_cast[idx]) for idx in indices]

            # Find the canonical entry: prefer the one with most mentions
            canonical_idx = max(indices, key=lambda i: main_cast[i].mention_count)
            canonical_char = main_cast[canonical_idx]

            logger.info(
                f"Same-firstname merge: '{first_name}' has {len(indices)} variants, "
                f"using '{canonical_char.canonical_name}' as canonical"
            )

            # Merge others into canonical
            for idx in indices:
                if idx == canonical_idx:
                    continue
                other = main_cast[idx]

                # Add other's canonical name as alias
                if other.canonical_name not in canonical_char.aliases:
                    logger.info(
                        f"  Merging '{other.canonical_name}' → '{canonical_char.canonical_name}' as alias"
                    )
                    canonical_char.aliases.append(other.canonical_name)

                # Merge other's aliases too
                for alias in other.aliases:
                    if (
                        alias not in canonical_char.aliases
                        and alias != canonical_char.canonical_name
                    ):
                        canonical_char.aliases.append(alias)

                # Accumulate mention count
                canonical_char.mention_count += other.mention_count

                chars_to_remove.add(idx)

            # If there's a single-word name matching this first name, merge it too
            if first_name in single_word_names:
                single_idx = single_word_names[first_name]
                if single_idx not in chars_to_remove:
                    single_char = main_cast[single_idx]
                    if single_char.canonical_name not in canonical_char.aliases:
                        logger.info(
                            f"  Also merging first-name-only '{single_char.canonical_name}' → "
                            f"'{canonical_char.canonical_name}' as alias"
                        )
                        canonical_char.aliases.append(single_char.canonical_name)
                    canonical_char.mention_count += single_char.mention_count
                    chars_to_remove.add(single_idx)

        # Build result list
        result = [c for i, c in enumerate(main_cast) if i not in chars_to_remove]

        if chars_to_remove:
            logger.info(f"Same-firstname merge: removed {len(chars_to_remove)} duplicate entries")

        return result

    def _deduplicate_alias_canonical_conflicts(
        self,
        main_cast: list[Character],
    ) -> tuple[list[Character], set[str]]:
        """
        Deduplicate characters where one character's alias matches another's canonical name.

        Example: "Myrtle Wilson" (canonical) + "Mrs. Wilson" (canonical, alias="Myrtle Wilson")
        → These are the SAME person, merge them

        This handles cases where the LLM extracted both a character and a variant reference
        as separate characters, but correctly noted one as an alias of the other.

        Returns:
            Tuple of (updated_main_cast, char_ids_with_new_aliases)
        """
        if len(main_cast) <= 1:
            return main_cast, set()

        chars_to_remove = set()
        chars_with_new_aliases = set()

        # Build a map of canonical_name -> character index
        canonical_map = {char.canonical_name.lower(): idx for idx, char in enumerate(main_cast)}

        for idx, char in enumerate(main_cast):
            if idx in chars_to_remove:
                continue

            # Check if any of this character's aliases match another character's canonical name
            for alias in char.aliases:
                alias_lower = alias.lower()

                # Does this alias match another character's canonical name?
                if alias_lower in canonical_map:
                    other_idx = canonical_map[alias_lower]

                    # Skip if it's the same character (alias matches own canonical name)
                    if other_idx == idx:
                        continue

                    # Skip if already marked for removal
                    if other_idx in chars_to_remove:
                        continue

                    other_char = main_cast[other_idx]

                    # MERGE: The character whose canonical name appears as an alias
                    # should be merged INTO the character that has it as an alias
                    #
                    # Example: "Mrs. Wilson" has alias "Myrtle Wilson"
                    # → Merge "Myrtle Wilson" INTO "Mrs. Wilson"
                    #
                    # BUT: We want to keep the one with MORE mentions as canonical
                    if char.mention_count >= other_char.mention_count:
                        # Keep current char, merge other into it
                        logger.info(
                            f"Alias-canonical conflict: merging '{other_char.canonical_name}' "
                            f"({other_char.mention_count} mentions) → '{char.canonical_name}' "
                            f"({char.mention_count} mentions) - alias match"
                        )

                        # Add other's canonical name as alias (if not already there)
                        if other_char.canonical_name not in char.aliases:
                            char.aliases.append(other_char.canonical_name)

                        # Merge other's aliases too
                        for other_alias in other_char.aliases:
                            if (
                                other_alias not in char.aliases
                                and other_alias.lower() != char.canonical_name.lower()
                            ):
                                char.aliases.append(other_alias)

                        chars_with_new_aliases.add(char.id)
                        chars_to_remove.add(other_idx)
                    else:
                        # Keep other char, merge current into it
                        logger.info(
                            f"Alias-canonical conflict: merging '{char.canonical_name}' "
                            f"({char.mention_count} mentions) → '{other_char.canonical_name}' "
                            f"({other_char.mention_count} mentions) - alias match"
                        )

                        # Add current's canonical name as alias (if not already there)
                        if char.canonical_name not in other_char.aliases:
                            other_char.aliases.append(char.canonical_name)

                        # Merge current's aliases too
                        for curr_alias in char.aliases:
                            if (
                                curr_alias not in other_char.aliases
                                and curr_alias.lower() != other_char.canonical_name.lower()
                            ):
                                other_char.aliases.append(curr_alias)

                        chars_with_new_aliases.add(other_char.id)
                        chars_to_remove.add(idx)
                        break  # Don't process this char anymore

        # Remove merged characters
        updated_main_cast = [
            char for idx, char in enumerate(main_cast) if idx not in chars_to_remove
        ]

        if chars_to_remove:
            logger.info(
                f"Alias-canonical deduplication: removed {len(chars_to_remove)} duplicate entries"
            )

        return updated_main_cast, chars_with_new_aliases

    def _split_wrongly_merged_titled_characters(
        self,
        main_cast: list[Character],
    ) -> tuple[list[Character], int]:
        """
        Defensive fix: Split characters that have aliases with different title+surname combinations.

        This handles LLM hallucinations where "M. Waldman" incorrectly gets "M. Krempe" as an alias,
        despite explicit prompt instructions forbidding this.

        Examples of splits:
        - "M. Waldman" with alias "M. Krempe" → split into two separate characters
        - "Mr. Sloane" with alias "Mr. McKee" → split into two separate characters

        Returns:
            Tuple of (updated_main_cast, number_of_splits)
        """
        import re

        title_pattern = r"^(Mr\.|Mrs\.|Miss|Ms\.|Dr\.|M\.)\s+(.+)$"
        split_count = 0
        new_characters = []

        for char in main_cast:
            # Check if canonical name has a title
            canonical_match = re.match(title_pattern, char.canonical_name, flags=re.IGNORECASE)
            if not canonical_match:
                # No title in canonical name - nothing to split
                new_characters.append(char)
                continue

            canonical_title = canonical_match.group(1).lower()
            canonical_surname = canonical_match.group(2).strip().lower()

            # Check each alias for different title+surname combinations
            aliases_to_split = []
            valid_aliases = []

            for alias in char.aliases:
                alias_match = re.match(title_pattern, alias, flags=re.IGNORECASE)
                if not alias_match:
                    # Alias doesn't have a title
                    # Check if this is a bare surname of a different person
                    # (e.g., canonical="M. Waldman", alias="Krempe" - should split)
                    # vs. (e.g., canonical="M. Waldman", alias="Professor" - should keep)
                    alias_lower = alias.strip().lower()
                    # If the alias is a single capitalized word that doesn't match the canonical surname,
                    # it's likely a different person's surname
                    if (
                        len(alias.split()) == 1  # Single word
                        and alias[0].isupper()  # Capitalized (likely a name)
                        and alias_lower != canonical_surname  # Different from canonical surname
                        and alias_lower not in canonical_surname
                    ):  # Not a substring of canonical surname
                        logger.warning(
                            f"SPLIT: '{alias}' cannot be alias of '{char.canonical_name}' "
                            f"(untitled surname doesn't match canonical surname '{canonical_surname}')"
                        )
                        aliases_to_split.append(alias)
                        split_count += 1
                    else:
                        # Keep as valid alias (could be a title, descriptor, etc.)
                        valid_aliases.append(alias)
                    continue

                alias_title = alias_match.group(1).lower()
                alias_surname = alias_match.group(2).strip().lower()

                # Check if this is a different titled person
                # Different surnames = different people (even if same title)
                # Different titles with same surname = different people (spouses)
                if alias_surname != canonical_surname:
                    logger.warning(
                        f"SPLIT: '{alias}' cannot be alias of '{char.canonical_name}' "
                        f"(different surnames: '{alias_surname}' vs '{canonical_surname}')"
                    )
                    aliases_to_split.append(alias)
                    split_count += 1
                elif alias_title != canonical_title:
                    logger.warning(
                        f"SPLIT: '{alias}' cannot be alias of '{char.canonical_name}' "
                        f"(same surname but different titles: '{alias_title}' vs '{canonical_title}')"
                    )
                    aliases_to_split.append(alias)
                    split_count += 1
                else:
                    # Same title and surname - valid alias
                    valid_aliases.append(alias)

            # Update character with only valid aliases
            char.aliases = valid_aliases
            new_characters.append(char)

            # Create new character entries for the split aliases
            # These will be minimal stubs that may get fleshed out in later processing
            for split_alias in aliases_to_split:
                new_char = Character(
                    id=f"split_{split_alias.lower().replace(' ', '_').replace('.', '')}",
                    canonical_name=split_alias,
                    aliases=[],
                    role="supporting",
                    mention_count=0,  # Will be updated by mention search
                    confidence="medium",
                )
                new_characters.append(new_char)
                logger.info(f"Created new character from split alias: '{split_alias}'")

        return new_characters, split_count

    def _split_semantic_conflicts(
        self,
        main_cast: list[Character],
    ) -> tuple[list[Character], int]:
        """
        Defensive fix: Split characters that have semantically conflicting aliases.

        This handles LLM hallucinations where descriptive terms from conflicting semantic
        categories get merged as aliases (e.g., "the creature" as alias of "the old man").

        Semantic conflict rules:
        - Creature-related terms (creature, monster, fiend, daemon, wretch) should NEVER
          be aliases of human descriptors (man, woman, boy, girl, old man, etc.)
        - These are fundamentally different types of entities

        Examples of splits:
        - "the old man (De Lacey)" with alias "the creature" → split into two separate characters
        - "the woman" with alias "the monster" → split into two separate characters

        Returns:
            Tuple of (updated_main_cast, number_of_splits)
        """

        # Define semantic conflict groups
        # Group 1: Supernatural/created beings
        creature_terms = {"creature", "monster", "fiend", "daemon", "wretch", "being"}

        # Group 2: Human descriptors (when used in "the X" pattern)
        # These should NOT merge with creature terms
        human_descriptors = {
            "man",
            "woman",
            "boy",
            "girl",
            "child",
            "person",
            "old man",
            "young man",
            "old woman",
            "young woman",
            "gentleman",
            "lady",
            "peasant",
            "sailor",
            "cottager",
        }

        split_count = 0
        new_characters = []

        for char in main_cast:
            canonical_lower = char.canonical_name.lower().strip()

            # Extract descriptor from "the X" or "X (surname)" patterns
            canonical_descriptor = None
            if canonical_lower.startswith("the "):
                # "the creature", "the old man", etc.
                canonical_descriptor = canonical_lower[4:].strip()
                # Handle patterns like "the old man (De Lacey)" - extract just "old man"
                if " (" in canonical_descriptor:
                    canonical_descriptor = canonical_descriptor.split(" (")[0].strip()

            # Determine canonical's semantic group
            canonical_is_creature = canonical_descriptor and any(
                term in canonical_descriptor for term in creature_terms
            )
            canonical_is_human = canonical_descriptor and any(
                canonical_descriptor == desc or canonical_descriptor.endswith(" " + desc)
                for desc in human_descriptors
            )

            # Check each alias for semantic conflicts
            aliases_to_split = []
            valid_aliases = []

            for alias in char.aliases:
                alias_lower = alias.lower().strip()

                # Extract descriptor from alias
                alias_descriptor = None
                if alias_lower.startswith("the "):
                    alias_descriptor = alias_lower[4:].strip()
                    if " (" in alias_descriptor:
                        alias_descriptor = alias_descriptor.split(" (")[0].strip()

                # Determine alias's semantic group
                alias_is_creature = alias_descriptor and any(
                    term in alias_descriptor for term in creature_terms
                )
                alias_is_human = alias_descriptor and any(
                    alias_descriptor == desc or alias_descriptor.endswith(" " + desc)
                    for desc in human_descriptors
                )

                # Check for semantic conflict
                conflict = False
                if canonical_is_creature and alias_is_human:
                    conflict = True
                    logger.warning(
                        f"SEMANTIC CONFLICT: '{alias}' (human descriptor) cannot be alias of "
                        f"'{char.canonical_name}' (creature-related term)"
                    )
                elif canonical_is_human and alias_is_creature:
                    conflict = True
                    logger.warning(
                        f"SEMANTIC CONFLICT: '{alias}' (creature-related term) cannot be alias of "
                        f"'{char.canonical_name}' (human descriptor)"
                    )

                if conflict:
                    # region agent log
                    try:
                        append_debug_event(
                            {
                                "sessionId": "debug-session",
                                "runId": "frankenstein-pre",
                                "hypothesisId": "H2",
                                "location": "src/agents/characters.py:_split_semantic_conflicts",
                                "message": "Semantic conflict detected; alias will be split into new character",
                                "data": {
                                    "char_id": char.id,
                                    "canonical": char.canonical_name,
                                    "canonical_descriptor": canonical_descriptor,
                                    "canonical_is_creature": canonical_is_creature,
                                    "canonical_is_human": canonical_is_human,
                                    "alias": alias,
                                    "alias_descriptor": alias_descriptor,
                                    "alias_is_creature": alias_is_creature,
                                    "alias_is_human": alias_is_human,
                                },
                                "timestamp": int(time.time() * 1000),
                            }
                        )
                    except Exception:
                        pass
                    # endregion

                    aliases_to_split.append(alias)
                    split_count += 1
                else:
                    valid_aliases.append(alias)

            # Update character with only valid aliases
            char.aliases = valid_aliases
            new_characters.append(char)

            # Create new character entries for the semantically conflicting aliases
            for split_alias in aliases_to_split:
                new_char = Character(
                    id=f"split_{split_alias.lower().replace(' ', '_').replace('.', '').replace('(', '').replace(')', '')}",
                    canonical_name=split_alias,
                    aliases=[],
                    role="supporting",
                    mention_count=0,  # Will be updated by mention search
                    confidence="medium",
                )
                new_characters.append(new_char)
                logger.info(
                    f"Created new character from semantically conflicting alias: '{split_alias}'"
                )

                # region agent log
                try:
                    append_debug_event(
                        {
                            "sessionId": "debug-session",
                            "runId": "frankenstein-pre",
                            "hypothesisId": "H3",
                            "location": "src/agents/characters.py:_split_semantic_conflicts",
                            "message": "Created split character stub (note mention_count=0 here)",
                            "data": {
                                "new_id": new_char.id,
                                "canonical": new_char.canonical_name,
                                "mentions": new_char.mention_count,
                            },
                            "timestamp": int(time.time() * 1000),
                        }
                    )
                except Exception:
                    pass
                # endregion

        return new_characters, split_count

    def _merge_within_main_cast(
        self,
        main_cast: list[Character],
    ) -> tuple[list[Character], set[str]]:
        """
        Merge characters within main cast that are variants of each other.

        Handles four patterns:
        1. Middle initial variants: "George B. Wilson" → alias of "George Wilson"
        2. Last-name-only → Full name: "Wilson" (65 mentions) → alias of "George B. Wilson"
        3. Spelling variants: "Wolfsheim" ↔ "Wolfshiem" (85% fuzzy match)
        4. First-name-only → Full name: "George" → alias of "George B. Wilson"

        Returns:
            Tuple of (updated_main_cast, char_ids_with_new_aliases)
        """
        import re

        chars_to_remove = set()
        chars_with_new_aliases = set()

        # Pass 0: Merge middle initial variants
        # "George B. Wilson" (1 mention) → alias of "George Wilson" (91 mentions)
        for idx, char in enumerate(main_cast):
            if idx in chars_to_remove:
                continue

            char_name = char.canonical_name.strip()
            if not char_name or " " not in char_name:
                continue  # Skip empty or single-word names

            # Check if this name has a middle initial pattern: "FirstName I. LastName"
            # Middle initial pattern: single letter followed by period
            middle_initial_pattern = r"^(\w+)\s+([A-Z]\.)\s+(.+)$"
            match = re.match(middle_initial_pattern, char_name)
            if not match:
                continue  # Not a middle initial pattern

            firstname = match.group(1)
            match.group(2)
            lastname = match.group(3)

            # Construct the name without middle initial
            name_without_middle = f"{firstname} {lastname}"

            # Check if this matches any other character
            for other_idx, other_char in enumerate(main_cast):
                if other_idx == idx or other_idx in chars_to_remove:
                    continue

                other_name = other_char.canonical_name.strip()
                if other_name.lower() == name_without_middle.lower():
                    # Found a match! Merge the one with FEWER mentions into the one with MORE
                    if char.mention_count <= other_char.mention_count:
                        # Current char (with middle initial) has fewer mentions → make it alias
                        if char_name not in other_char.aliases:
                            logger.info(
                                f"Merging middle initial variant: '{char_name}' ({char.mention_count} mentions) "
                                f"→ '{other_char.canonical_name}' ({other_char.mention_count} mentions) as alias"
                            )
                            other_char.aliases.append(char_name)
                            # Also transfer char's aliases
                            for alias in char.aliases:
                                if alias not in other_char.aliases:
                                    other_char.aliases.append(alias)
                            chars_with_new_aliases.add(other_char.id)
                        chars_to_remove.add(idx)
                    else:
                        # Other char (without middle initial) has fewer mentions → make it alias
                        if other_name not in char.aliases:
                            logger.info(
                                f"Merging middle initial variant: '{other_char.canonical_name}' ({other_char.mention_count} mentions) "
                                f"→ '{char_name}' ({char.mention_count} mentions) as alias"
                            )
                            char.aliases.append(other_name)
                            # Also transfer other's aliases
                            for alias in other_char.aliases:
                                if alias not in char.aliases:
                                    char.aliases.append(alias)
                            chars_with_new_aliases.add(char.id)
                        chars_to_remove.add(other_idx)
                    break  # Only merge with first match

        # Pass 1: Merge last-name-only and title-variant characters
        for idx, char in enumerate(main_cast):
            if idx in chars_to_remove:
                continue

            char_name = char.canonical_name.strip()
            if not char_name or " " in char_name:
                continue  # Skip empty or multi-word names

            # This is a single-word name (potential last name or first name)
            # Check if it matches the last word OR title-stripped version of any OTHER main cast character

            matches = []
            for other_idx, other_char in enumerate(main_cast):
                if other_idx == idx or other_idx in chars_to_remove:
                    continue

                other_name = other_char.canonical_name.strip()
                if not other_name or " " not in other_name:
                    continue  # Only match against multi-word names

                # First check: exact match with title-stripped version
                # E.g., "Sloane" matches "Mr. Sloane" after stripping "Mr."
                other_title_stripped = self._strip_title(other_name)
                if char_name.lower() == other_title_stripped.lower():
                    matches.append((other_idx, "exact_title_stripped"))
                    continue

                # Second check: last name match
                other_parts = other_name.split()
                other_lastname = other_parts[-1].strip(".,;:")

                # Exact last name match
                if char_name.lower() == other_lastname.lower():
                    matches.append((other_idx, "exact_lastname"))
                    continue

                # Fuzzy last name match (handles Wolfsheim/Wolfshiem)
                if names_similar(char_name, other_lastname):
                    matches.append((other_idx, "fuzzy_lastname"))
                    continue

                # Check first name match (if other_name has multiple parts)
                if len(other_parts) >= 2:
                    other_firstname = other_parts[0].strip(".,;:")
                    if char_name.lower() == other_firstname.lower():
                        matches.append((other_idx, "exact_firstname"))

            # Merge if exactly ONE match (avoids ambiguity like "Wilson" matching both George and Myrtle)
            if len(matches) == 1:
                other_idx, match_type = matches[0]
                other_char = main_cast[other_idx]

                # Add single-word name as alias to the full name character
                if char_name not in other_char.aliases:
                    logger.info(
                        f"Merging within main cast: '{char_name}' ({char.mention_count} mentions) "
                        f"→ '{other_char.canonical_name}' as alias ({match_type})"
                    )
                    other_char.aliases.append(char_name)
                    chars_with_new_aliases.add(other_char.id)

                # Mark single-word character for removal
                chars_to_remove.add(idx)

        # Pass 2: Merge spelling variants (e.g., "Meyer Wolfsheim" ↔ "Meyer Wolfshiem")
        for idx, char in enumerate(main_cast):
            if idx in chars_to_remove:
                continue

            char_name = char.canonical_name.strip()
            if not char_name:
                continue

            for other_idx, other_char in enumerate(main_cast):
                if other_idx <= idx or other_idx in chars_to_remove:
                    continue  # Only check each pair once

                other_name = other_char.canonical_name.strip()
                if not other_name:
                    continue

                # Check if names are very similar (spelling variants)
                if names_similar(char_name, other_name):  # 85% similar
                    # SAFETY CHECK: Don't merge if both have different title prefixes
                    # (e.g., "Mr. White" vs "Mrs. White" are different people)
                    if self._are_different_titled_people(char_name, other_name):
                        continue  # Skip - they're different people

                    # Calculate similarity for logging
                    similarity = string_similarity(char_name, other_name)

                    # Merge the one with FEWER mentions into the one with MORE mentions
                    if char.mention_count >= other_char.mention_count:
                        # Merge other → char
                        if other_name not in char.aliases:
                            logger.info(
                                f"Merging spelling variant within main cast: '{other_name}' "
                                f"({other_char.mention_count} mentions) → '{char_name}' "
                                f"({char.mention_count} mentions) as alias (similarity={similarity:.2f})"
                            )
                            char.aliases.append(other_name)
                            # Also merge other's existing aliases
                            for alias in other_char.aliases:
                                if alias not in char.aliases:
                                    char.aliases.append(alias)
                            chars_with_new_aliases.add(char.id)
                        chars_to_remove.add(other_idx)
                    else:
                        # Merge char → other
                        if char_name not in other_char.aliases:
                            logger.info(
                                f"Merging spelling variant within main cast: '{char_name}' "
                                f"({char.mention_count} mentions) → '{other_name}' "
                                f"({other_char.mention_count} mentions) as alias (similarity={similarity:.2f})"
                            )
                            other_char.aliases.append(char_name)
                            # Also merge char's existing aliases
                            for alias in char.aliases:
                                if alias not in other_char.aliases:
                                    other_char.aliases.append(alias)
                            chars_with_new_aliases.add(other_char.id)
                        chars_to_remove.add(idx)
                        break  # Don't process this char anymore

        # Remove merged characters from Pass 2
        updated_main_cast = [
            char for idx, char in enumerate(main_cast) if idx not in chars_to_remove
        ]

        # Pass 3: Re-run last-name matching after spelling variants are merged
        # This handles cases like "Wolfshiem" which initially had ambiguous matches,
        # but after Pass 2 merging has only one match remaining
        chars_to_remove_pass3 = set()

        for idx, char in enumerate(updated_main_cast):
            char_name = char.canonical_name.strip()
            if not char_name or " " in char_name:
                continue  # Skip empty or multi-word names

            # Check if this single-word name now has exactly ONE match
            matches = []
            for other_idx, other_char in enumerate(updated_main_cast):
                if other_idx == idx:
                    continue

                other_name = other_char.canonical_name.strip()
                if not other_name or " " not in other_name:
                    continue

                other_parts = other_name.split()
                other_lastname = other_parts[-1].strip(".,;:")

                # Exact or fuzzy last name match
                if char_name.lower() == other_lastname.lower():
                    matches.append((other_idx, "exact_lastname"))
                else:
                    if names_similar(char_name, other_lastname):
                        matches.append((other_idx, "fuzzy_lastname"))

            # Merge if exactly ONE match
            if len(matches) == 1:
                other_idx, match_type = matches[0]
                other_char = updated_main_cast[other_idx]

                if char_name not in other_char.aliases:
                    logger.info(
                        f"Merging within main cast (Pass 3): '{char_name}' ({char.mention_count} mentions) "
                        f"→ '{other_char.canonical_name}' as alias ({match_type})"
                    )
                    other_char.aliases.append(char_name)
                    chars_with_new_aliases.add(other_char.id)

                chars_to_remove_pass3.add(idx)

        # Remove Pass 3 merged characters
        final_main_cast = [
            char for idx, char in enumerate(updated_main_cast) if idx not in chars_to_remove_pass3
        ]

        # Pass 4: Merge descriptive synonyms within main cast
        # Handles cases like "the creature", "the monster", "the fiend" referring to same entity
        chars_to_remove_pass4 = set()

        # Synonym groups for unnamed characters (same as in supporting.py)
        synonym_groups = [
            # Supernatural/created beings
            {"creature", "monster", "fiend", "daemon", "wretch", "being", "thing"},
            # Authority figures
            {"stranger", "visitor", "guest", "traveler", "intruder"},
            # Generic descriptors
            {"man", "woman", "boy", "girl", "child", "person"},
        ]

        def _normalize_descriptor(raw_name: str) -> tuple[bool, str]:
            """
            Normalize a descriptive handle into a synonym-group descriptor.

            Examples:
            - "the creature" -> (True, "creature")
            - "the creature (implied)" -> (True, "creature")
            - "creature" -> (False, "creature")   # bare form (special-cased for creature group)
            """
            name = (raw_name or "").lower().strip()
            is_the_form = name.startswith("the ")
            desc = name[4:].strip() if is_the_form else name
            if " (" in desc:
                desc = desc.split(" (", 1)[0].strip()
            desc = desc.strip(".,;:!?\"'“”")
            return is_the_form, desc

        for idx, char in enumerate(final_main_cast):
            if idx in chars_to_remove_pass4:
                continue

            char_name = char.canonical_name.lower().strip()

            char_is_the_form, descriptor = _normalize_descriptor(char.canonical_name)

            # Check if descriptor matches any synonym group (creature group also allows bare "creature"/"monster"/etc.)
            for group in synonym_groups:
                allow_bare = "creature" in group  # only the creature/supernatural group
                if descriptor not in group:
                    continue
                if not char_is_the_form and not allow_bare:
                    continue

                # Found a match! Check if any other characters use terms from the same group
                for other_idx, other_char in enumerate(final_main_cast):
                    if other_idx <= idx or other_idx in chars_to_remove_pass4:
                        continue  # Only check each pair once

                    other_name = other_char.canonical_name.lower().strip()
                    other_is_the_form, other_descriptor = _normalize_descriptor(
                        other_char.canonical_name
                    )

                    # If both descriptors are in the same synonym group, merge them
                    if other_descriptor in group:
                        if not other_is_the_form and not allow_bare:
                            continue
                        # Merge the one with FEWER mentions into the one with MORE mentions
                        if char.mention_count >= other_char.mention_count:
                            # Merge other → char
                            if other_char.canonical_name not in char.aliases:
                                logger.info(
                                    f"Merging descriptive synonym within main cast: '{other_char.canonical_name}' "
                                    f"({other_char.mention_count} mentions) → '{char.canonical_name}' "
                                    f"({char.mention_count} mentions) as alias (synonym group: {group})"
                                )
                                char.aliases.append(other_char.canonical_name)
                                # Also merge other's existing aliases
                                for alias in other_char.aliases:
                                    if alias not in char.aliases:
                                        char.aliases.append(alias)
                                chars_with_new_aliases.add(char.id)
                            chars_to_remove_pass4.add(other_idx)
                        else:
                            # Merge char → other
                            if char.canonical_name not in other_char.aliases:
                                logger.info(
                                    f"Merging descriptive synonym within main cast: '{char.canonical_name}' "
                                    f"({char.mention_count} mentions) → '{other_char.canonical_name}' "
                                    f"({other_char.mention_count} mentions) as alias (synonym group: {group})"
                                )
                                other_char.aliases.append(char.canonical_name)
                                # Also merge char's existing aliases
                                for alias in char.aliases:
                                    if alias not in other_char.aliases:
                                        other_char.aliases.append(alias)
                                chars_with_new_aliases.add(other_char.id)
                            chars_to_remove_pass4.add(idx)
                            break  # Don't process this char anymore

                if idx in chars_to_remove_pass4:
                    break  # This char was merged, stop checking other synonym groups

        # Remove Pass 4 merged characters
        final_main_cast = [
            char for idx, char in enumerate(final_main_cast) if idx not in chars_to_remove_pass4
        ]

        return final_main_cast, chars_with_new_aliases

    def _merge_lastname_aliases(
        self,
        main_cast: list[Character],
        supporting_cast: list[Character],
    ) -> tuple[list[Character], list[Character], set[str]]:
        """
        Merge last-name-only supporting characters as aliases of main cast.

        Common pattern: "Wilson" (65 mentions) should be an alias of "George B. Wilson"
        when there's only one Wilson in the main cast.

        Also handles title variants like "Mr. Gatsby" → alias of "Jay Gatsby"

        NEW: Also handles reverse case where main_cast has single-word name and
        supporting_cast has full name (e.g., "Wolfshiem" in main, "Meyer Wolfshiem" in supporting)

        Returns:
            Tuple of (updated_main_cast, updated_supporting_cast, char_ids_with_new_aliases)
        """
        import re

        if not supporting_cast:
            return main_cast, supporting_cast, set()

        supporting_to_remove = set()
        chars_with_new_aliases = set()

        for supp_idx, supp_char in enumerate(supporting_cast):
            supp_name = supp_char.canonical_name.strip()

            # Skip if empty
            if not supp_name:
                continue

            # Check for title + name pattern (e.g., "Mr. Gatsby")
            title_stripped = self._strip_title(supp_name)
            if title_stripped != supp_name:
                # This is a title + name - check if it matches any main cast canonical or alias
                for main_idx, main_char in enumerate(main_cast):
                    # Check canonical name
                    if title_stripped.lower() == main_char.canonical_name.lower():
                        if supp_name not in main_char.aliases:
                            logger.info(
                                f"Merging title variant '{supp_name}' → "
                                f"'{main_char.canonical_name}' as alias"
                            )
                            main_char.aliases.append(supp_name)
                            chars_with_new_aliases.add(main_char.id)
                        supporting_to_remove.add(supp_idx)
                        break

                    # Check aliases
                    for alias in main_char.aliases:
                        if title_stripped.lower() == alias.lower():
                            if supp_name not in main_char.aliases:
                                logger.info(
                                    f"Merging title variant '{supp_name}' → "
                                    f"'{main_char.canonical_name}' (matches alias '{alias}')"
                                )
                                main_char.aliases.append(supp_name)
                                chars_with_new_aliases.add(main_char.id)
                            supporting_to_remove.add(supp_idx)
                            break

                # If we processed this as a title variant, skip last-name processing
                if supp_idx in supporting_to_remove:
                    continue

            # Check reverse: MAIN cast has title, SUPPORTING cast does not.
            # e.g., main = "Doctor T. J. Eckleburg", supporting = "T. J. Eckleburg"
            if supp_idx not in supporting_to_remove:
                for main_idx, main_char in enumerate(main_cast):
                    main_title_stripped = self._strip_title(main_char.canonical_name)
                    if (
                        main_title_stripped != main_char.canonical_name
                        and main_title_stripped.lower() == supp_name.lower()
                    ):
                        if supp_name not in main_char.aliases:
                            logger.info(
                                f"Merging title-free variant '{supp_name}' → "
                                f"'{main_char.canonical_name}' as alias (main has title)"
                            )
                            main_char.aliases.append(supp_name)
                            chars_with_new_aliases.add(main_char.id)
                        supporting_to_remove.add(supp_idx)
                        break

            if supp_idx in supporting_to_remove:
                continue

            # Check for "the X" → "X" normalization (e.g., "Owl-eyed man" vs "the owl-eyed man")
            # Strip leading "the " for comparison
            supp_name_normalized = re.sub(r"^the\s+", "", supp_name, flags=re.IGNORECASE).strip()

            # Check against main cast canonical names and aliases
            for main_idx, main_char in enumerate(main_cast):
                # Normalize main canonical name
                main_canonical_normalized = re.sub(
                    r"^the\s+", "", main_char.canonical_name, flags=re.IGNORECASE
                ).strip()

                # Check canonical name (with and without "the")
                if (
                    supp_name_normalized.lower() == main_canonical_normalized.lower()
                    or supp_name.lower() == main_char.canonical_name.lower()
                ):
                    if supp_name not in main_char.aliases:
                        logger.info(
                            f"Merging 'the' variant '{supp_name}' → "
                            f"'{main_char.canonical_name}' as alias"
                        )
                        main_char.aliases.append(supp_name)
                        chars_with_new_aliases.add(main_char.id)
                    supporting_to_remove.add(supp_idx)
                    break

                # Check aliases
                for alias in main_char.aliases:
                    alias_normalized = re.sub(r"^the\s+", "", alias, flags=re.IGNORECASE).strip()
                    if (
                        supp_name_normalized.lower() == alias_normalized.lower()
                        or supp_name.lower() == alias.lower()
                    ):
                        if supp_name not in main_char.aliases:
                            logger.info(
                                f"Merging 'the' variant '{supp_name}' → "
                                f"'{main_char.canonical_name}' (matches alias '{alias}')"
                            )
                            main_char.aliases.append(supp_name)
                            chars_with_new_aliases.add(main_char.id)
                        supporting_to_remove.add(supp_idx)
                        break

                if supp_idx in supporting_to_remove:
                    break

            # Only process single-word names (potential last names)
            if " " in supp_name:
                continue

            # Check if this could be a last name of any main cast character
            matches = []

            for main_idx, main_char in enumerate(main_cast):
                # Extract last name from main character's canonical name
                main_name_parts = main_char.canonical_name.strip().split()

                if not main_name_parts:
                    continue

                # Get last word as potential surname
                main_lastname = main_name_parts[-1].strip(".,;:")

                # Check for exact match (case-insensitive)
                if supp_name.lower() == main_lastname.lower():
                    matches.append((main_idx, "exact"))
                    continue

                # Check for fuzzy match (handles Wolfsheim/Wolfshiem)
                if names_similar(supp_name, main_lastname):  # 85% similar
                    matches.append((main_idx, "fuzzy_lastname"))
                    continue

                # Check first name match (if main_name has multiple parts)
                if len(main_name_parts) >= 2:
                    main_firstname = main_name_parts[0].strip(".,;:")
                    if supp_name.lower() == main_firstname.lower():
                        matches.append((main_idx, "exact_firstname"))

            # Handle merging based on match count
            if len(matches) == 1:
                # Exactly one match - straightforward merge
                main_idx, match_type = matches[0]
                main_char = main_cast[main_idx]

                # Check if already an alias
                if supp_name not in main_char.aliases:
                    logger.info(
                        f"Merging last-name-only '{supp_name}' ({supp_char.mention_count} mentions) "
                        f"→ '{main_char.canonical_name}' as alias ({match_type} match)"
                    )
                    main_char.aliases.append(supp_name)
                    chars_with_new_aliases.add(main_char.id)

                # Mark for removal from supporting cast
                supporting_to_remove.add(supp_idx)

            elif len(matches) > 1:
                # Multiple characters share this surname
                # Use title-based disambiguation: if one character has "Mrs. [LastName]" as alias,
                # merge bare last name with a character that does NOT have that female title
                # (This handles cases like George Wilson vs Myrtle Wilson in Gatsby)

                # Find which characters have gendered title variants
                matches_with_mrs = []
                matches_without_mrs = []

                for main_idx, match_type in matches:
                    main_char = main_cast[main_idx]

                    # Check if this character has "Mrs. [LastName]" as alias
                    has_mrs_variant = any(
                        alias.lower().startswith("mrs.") and supp_name.lower() in alias.lower()
                        for alias in main_char.aliases
                    )

                    if has_mrs_variant:
                        matches_with_mrs.append((main_idx, match_type))
                    else:
                        matches_without_mrs.append((main_idx, match_type))

                # If we have exactly ONE match WITHOUT the Mrs. title, merge with that one
                # (This means bare "Wilson" → "George Wilson", not "Myrtle Wilson" who has "Mrs. Wilson")
                if len(matches_without_mrs) == 1:
                    main_idx, match_type = matches_without_mrs[0]
                    main_char = main_cast[main_idx]

                    if supp_name not in main_char.aliases:
                        logger.info(
                            f"Merging last-name-only '{supp_name}' ({supp_char.mention_count} mentions) "
                            f"→ '{main_char.canonical_name}' as alias (title-disambiguated {match_type} match, "
                            f"{len(matches)} total surname matches)"
                        )
                        main_char.aliases.append(supp_name)
                        chars_with_new_aliases.add(main_char.id)

                    supporting_to_remove.add(supp_idx)
                else:
                    # Can't disambiguate - merge to ALL matching characters
                    # (This means bare "Wilson" becomes alias for both George and Myrtle)
                    # Rationale: If we can't tell which character a bare surname refers to,
                    # both family members should get credit for those mentions
                    logger.info(
                        f"Merging last-name-only '{supp_name}' ({supp_char.mention_count} mentions) "
                        f"→ ALL {len(matches)} characters with this surname (disambiguation failed)"
                    )
                    for main_idx, match_type in matches:
                        main_char = main_cast[main_idx]
                        if supp_name not in main_char.aliases:
                            main_char.aliases.append(supp_name)
                            chars_with_new_aliases.add(main_char.id)
                            logger.debug(
                                f"  Added '{supp_name}' as alias to '{main_char.canonical_name}'"
                            )

                    supporting_to_remove.add(supp_idx)

        # Remove merged characters from supporting cast
        updated_supporting = [
            char for idx, char in enumerate(supporting_cast) if idx not in supporting_to_remove
        ]

        # REVERSE PASS: Check if any MULTI-WORD supporting characters should merge
        # with SINGLE-WORD main cast characters (e.g., "Wolfshiem" main + "Meyer Wolfshiem" supporting)
        # This handles cases where NER extracted the full name but summaries only mentioned last name
        reverse_supporting_to_remove = set()

        for main_idx, main_char in enumerate(main_cast):
            main_name = main_char.canonical_name.strip()

            # Only process single-word main cast names
            if not main_name or " " in main_name:
                continue

            # Check if this matches any multi-word supporting character's last name
            matches = []

            for supp_idx, supp_char in enumerate(updated_supporting):
                if supp_idx in reverse_supporting_to_remove:
                    continue

                supp_name = supp_char.canonical_name.strip()

                # Only match against multi-word names
                if not supp_name or " " not in supp_name:
                    continue

                # Extract last name from supporting character
                supp_parts = supp_name.split()
                supp_lastname = supp_parts[-1].strip(".,;:")

                # Check for exact match
                if main_name.lower() == supp_lastname.lower():
                    matches.append((supp_idx, supp_name, "exact"))
                    continue

                # Check for fuzzy match (handles spelling variants)
                if names_similar(main_name, supp_lastname):
                    matches.append((supp_idx, supp_name, "fuzzy"))

            # Merge if exactly ONE match
            if len(matches) == 1:
                supp_idx, supp_name, match_type = matches[0]
                supp_char = updated_supporting[supp_idx]

                # Add supporting full name as alias to main cast character
                if supp_name not in main_char.aliases:
                    logger.info(
                        f"Merging full-name supporting char '{supp_name}' ({supp_char.mention_count} mentions) "
                        f"→ '{main_char.canonical_name}' ({main_char.mention_count} mentions) as alias ({match_type} match)"
                    )
                    main_char.aliases.append(supp_name)
                    chars_with_new_aliases.add(main_char.id)

                # Mark for removal from supporting cast
                reverse_supporting_to_remove.add(supp_idx)

        # Remove reverse-merged characters
        final_supporting = [
            char
            for idx, char in enumerate(updated_supporting)
            if idx not in reverse_supporting_to_remove
        ]

        return main_cast, final_supporting, chars_with_new_aliases

    def _merge_within_supporting_cast(
        self,
        supporting_cast: list[Character],
    ) -> tuple[list[Character], set[str]]:
        """
        Merge characters within supporting cast that are variants of each other.

        Handles two patterns:
        1. Last-name-only → Full name: "Wolfshiem" (20 mentions) → alias of "Meyer Wolfshiem"
        2. Spelling variants: "Wolfsheim" ↔ "Wolfshiem" (85% fuzzy match)

        This is similar to _merge_within_main_cast but for supporting characters.

        Returns:
            Tuple of (updated_supporting_cast, char_ids_with_new_aliases)
        """
        chars_to_remove = set()
        chars_with_new_aliases = set()

        # Pass 1: Merge last-name-only characters
        for idx, char in enumerate(supporting_cast):
            if idx in chars_to_remove:
                continue

            char_name = char.canonical_name.strip()
            if not char_name or " " in char_name:
                continue  # Skip empty or multi-word names

            # This is a single-word name (potential last name)
            # Check if it matches the last word of any OTHER supporting character

            matches = []
            for other_idx, other_char in enumerate(supporting_cast):
                if other_idx == idx or other_idx in chars_to_remove:
                    continue

                other_name = other_char.canonical_name.strip()
                if not other_name or " " not in other_name:
                    continue  # Only match against multi-word names

                # Check last name match
                other_parts = other_name.split()
                other_lastname = other_parts[-1].strip(".,;:")

                # Exact last name match
                if char_name.lower() == other_lastname.lower():
                    matches.append((other_idx, "exact_lastname"))
                    continue

                # Fuzzy last name match (handles Wolfsheim/Wolfshiem)
                if names_similar(char_name, other_lastname):
                    matches.append((other_idx, "fuzzy_lastname"))
                    continue  # Skip first-name check for this other_char

                # First-name match for two cases:
                # Case A: "FirstName LastInitial." pattern (e.g., "John" → "John G.")
                #   When a full name uses a single-letter last initial, a reference to
                #   just the first name is always the same person. Universal: any book
                #   with initial-style names (military, formal, period fiction) benefits.
                # Case B: Rare full-name characters (e.g., "Ted" → "Ted Frith").
                #   Universal pattern: character introduced by full name, then referenced
                #   by first name only. The ≤3 guard prevents false merges with
                #   frequently-mentioned characters.
                other_firstname = other_parts[0].strip(".,;:")
                if char_name.lower() == other_firstname.lower():
                    remaining_parts = other_parts[1:]
                    all_initials = bool(remaining_parts) and all(
                        len(p.strip(".,;:")) == 1 and p.strip(".,;:").isalpha()
                        for p in remaining_parts
                    )
                    if all_initials:
                        matches.append((other_idx, "firstname_of_initial_name"))
                    elif other_char.mention_count <= 3:
                        matches.append((other_idx, "exact_firstname_of_rare_fullname"))

            # Merge if exactly ONE match
            if len(matches) == 1:
                other_idx, match_type = matches[0]
                other_char = supporting_cast[other_idx]

                # Add single-word name as alias to the full name character
                if char_name not in other_char.aliases:
                    logger.info(
                        f"Merging within supporting cast: '{char_name}' ({char.mention_count} mentions) "
                        f"→ '{other_char.canonical_name}' as alias ({match_type})"
                    )
                    other_char.aliases.append(char_name)
                    chars_with_new_aliases.add(other_char.id)

                # Mark single-word character for removal
                chars_to_remove.add(idx)

        # Pass 2: Merge spelling variants (e.g., "Meyer Wolfsheim" ↔ "Meyer Wolfshiem")
        for idx, char in enumerate(supporting_cast):
            if idx in chars_to_remove:
                continue

            char_name = char.canonical_name.strip()
            if not char_name:
                continue

            for other_idx, other_char in enumerate(supporting_cast):
                if other_idx <= idx or other_idx in chars_to_remove:
                    continue  # Only check each pair once

                other_name = other_char.canonical_name.strip()
                if not other_name:
                    continue

                # Calculate similarity for spelling variant detection
                # Use direct string similarity (NOT names_similar which has subset matching)
                # This prevents false merges like "John" + "John Donaldson" (father/son with same first name)
                # while still catching spelling variants like "Wolfsheim"/"Wolfshiem" (89% similar)
                # Note: Pass 1 handles legitimate last-name-only merges ("Wilson" → "George Wilson")
                similarity = string_similarity(char_name, other_name)

                # Check if names are very similar (spelling variants only, threshold 85%)
                if similarity >= 0.85:
                    # SAFETY CHECK: Don't merge if both have different title prefixes
                    # (e.g., "Mr. White" vs "Mrs. White" are different people)
                    if self._are_different_titled_people(char_name, other_name):
                        continue  # Skip - they're different people

                    # Merge the one with FEWER mentions into the one with MORE mentions
                    if char.mention_count >= other_char.mention_count:
                        # Merge other → char
                        if other_name not in char.aliases:
                            logger.info(
                                f"Merging spelling variant within supporting cast: '{other_name}' "
                                f"({other_char.mention_count} mentions) → '{char_name}' "
                                f"({char.mention_count} mentions) as alias (similarity={similarity:.2f})"
                            )
                            char.aliases.append(other_name)
                            # Also merge other's existing aliases
                            for alias in other_char.aliases:
                                if alias not in char.aliases:
                                    char.aliases.append(alias)
                            chars_with_new_aliases.add(char.id)
                        chars_to_remove.add(other_idx)
                    else:
                        # Merge char → other
                        if char_name not in other_char.aliases:
                            logger.info(
                                f"Merging spelling variant within supporting cast: '{char_name}' "
                                f"({char.mention_count} mentions) → '{other_name}' "
                                f"({other_char.mention_count} mentions) as alias (similarity={similarity:.2f})"
                            )
                            other_char.aliases.append(char_name)
                            # Also merge char's existing aliases
                            for alias in char.aliases:
                                if alias not in other_char.aliases:
                                    other_char.aliases.append(alias)
                            chars_with_new_aliases.add(other_char.id)
                        chars_to_remove.add(idx)
                        break  # Don't process this char anymore

        # Pass 3: Merge standard English diminutives as aliases.
        # Handles cases where NER extracts a nickname form separately from the canonical name.
        # Example: "Johnny" (2 mentions) → alias of "John" (16 mentions).
        # Uses the module-level STANDARD_DIMINUTIVES mapping.
        for idx, char in enumerate(supporting_cast):
            if idx in chars_to_remove:
                continue

            char_name = char.canonical_name.strip()
            if not char_name or " " in char_name:
                continue  # Only single-word names

            canonical_form = STANDARD_DIMINUTIVES.get(char_name.lower())
            if not canonical_form:
                continue  # Not a known diminutive

            # Find exactly one supporting character whose canonical name is the long form
            dim_matches = []
            for other_idx, other_char in enumerate(supporting_cast):
                if other_idx == idx or other_idx in chars_to_remove:
                    continue
                if other_char.canonical_name.lower() == canonical_form:
                    dim_matches.append(other_idx)

            # Merge if exactly ONE match (avoid ambiguity when multiple same-name characters)
            if len(dim_matches) == 1:
                other_idx = dim_matches[0]
                other_char = supporting_cast[other_idx]

                if char_name not in other_char.aliases:
                    logger.info(
                        f"Merging diminutive '{char_name}' ({char.mention_count} mentions) "
                        f"→ '{other_char.canonical_name}' as alias (standard English diminutive)"
                    )
                    other_char.aliases.append(char_name)
                    chars_with_new_aliases.add(other_char.id)

                chars_to_remove.add(idx)

        # Remove merged characters
        updated_supporting = [
            char for idx, char in enumerate(supporting_cast) if idx not in chars_to_remove
        ]

        return updated_supporting, chars_with_new_aliases

    def _merge_descriptive_synonyms_across_casts(
        self,
        main_cast: list[Character],
        supporting_cast: list[Character],
    ) -> tuple[list[Character], set[str]]:
        """
        Merge descriptive synonym characters from supporting cast into main cast.

        Handles cases like:
        - "the creature" (main cast, antagonist) + "the monster" (supporting) → merge monster into creature
        - "the stranger" (main cast) + "the visitor" (supporting) → merge visitor into stranger

        This only merges supporting→main when both use "the X" pattern from same synonym group.

        Returns:
            Tuple of (updated_supporting_cast, char_ids_with_new_aliases_in_main_cast)
        """
        chars_to_remove = set()
        chars_with_new_aliases = set()

        # Synonym groups (same as in _merge_within_main_cast Pass 4)
        synonym_groups = [
            # Supernatural/created beings
            {"creature", "monster", "fiend", "daemon", "wretch", "being", "thing"},
            # Authority figures
            {"stranger", "visitor", "guest", "traveler", "intruder"},
            # Generic descriptors
            {"man", "woman", "boy", "girl", "child", "person"},
        ]

        # Helper function to normalize descriptors (strip parentheticals)
        def _normalize_cross_cast_descriptor(name: str) -> str:
            """
            Normalize a descriptive name by stripping parentheticals.

            Examples:
            - "the creature (implied presence)" → "creature"
            - "the monster" → "monster"
            - "the old man (De Lacey)" → "old man"
            """
            if not name.startswith("the "):
                return name

            desc = name[4:].strip().lower()

            # Strip parentheticals: "creature (implied)" → "creature"
            if " (" in desc:
                desc = desc.split(" (")[0].strip()

            # Strip trailing punctuation
            desc = desc.strip(".,;:!?\"'" "")

            return desc

        # Loop through main cast characters looking for "the X" patterns
        for main_char in main_cast:
            main_name = main_char.canonical_name.lower().strip()

            # Only check descriptive patterns like "the X"
            if not main_name.startswith("the "):
                continue

            # Extract and normalize descriptor
            main_descriptor = _normalize_cross_cast_descriptor(main_name)

            # DEBUG: Log creature/monster specifically
            if "creature" in main_descriptor or "monster" in main_descriptor:
                logger.warning(
                    f"DEBUG cross-cast merge: Main cast has '{main_char.canonical_name}' "
                    f"(normalized descriptor: '{main_descriptor}')"
                )

            # Check if descriptor matches any synonym group
            # Group elements are already lowercase strings
            for group in synonym_groups:
                if main_descriptor not in group:
                    continue

                # Found a match! Check supporting cast for synonyms from same group
                logger.info(
                    f"Main cast '{main_char.canonical_name}' (descriptor: '{main_descriptor}') "
                    f"matches synonym group: {group}. Checking supporting cast..."
                )

                for supp_idx, supp_char in enumerate(supporting_cast):
                    if supp_idx in chars_to_remove:
                        continue

                    supp_name = supp_char.canonical_name.lower().strip()
                    if not supp_name.startswith("the "):
                        continue

                    # Extract and normalize descriptor (strips parentheticals)
                    supp_descriptor = _normalize_cross_cast_descriptor(supp_name)

                    # DEBUG: Log all "the X" supporting characters when main is creature/monster
                    if "creature" in main_descriptor or "monster" in main_descriptor:
                        logger.warning(
                            f"DEBUG cross-cast merge: Checking supporting '{supp_char.canonical_name}' "
                            f"(normalized descriptor: '{supp_descriptor}') against main '{main_char.canonical_name}'"
                        )

                    # If supporting character uses synonym from same group, merge it
                    # Group elements are already lowercase strings
                    if supp_descriptor in group:
                        logger.info(
                            f"Merging descriptive synonym across casts: '{supp_char.canonical_name}' "
                            f"({supp_char.mention_count} mentions, supporting) → "
                            f"'{main_char.canonical_name}' ({main_char.mention_count} mentions, main cast) "
                            f"as alias (synonym group: {group})"
                        )

                        # Add supporting character's name as alias to main character
                        if supp_char.canonical_name not in main_char.aliases:
                            main_char.aliases.append(supp_char.canonical_name)

                        # Also merge supporting character's existing aliases
                        for alias in supp_char.aliases:
                            if alias not in main_char.aliases:
                                main_char.aliases.append(alias)

                        chars_with_new_aliases.add(main_char.id)
                        chars_to_remove.add(supp_idx)

                # Found synonym group match, no need to check other groups for this main character
                break

        # Remove merged supporting characters
        updated_supporting = [
            char for idx, char in enumerate(supporting_cast) if idx not in chars_to_remove
        ]

        return updated_supporting, chars_with_new_aliases

    def _merge_surname_into_family_descriptive(
        self,
        main_cast: list[Character],
        supporting_cast: list[Character],
    ) -> tuple[list[Character], set[str]]:
        """
        Merge bare surname from supporting cast into descriptive handles when
        they share family relationships.

        Example:
        - Supporting: "De Lacey" (bare surname)
        - Main cast: "Felix De Lacey", "Agatha De Lacey" (share surname)
        - Main cast: "the old man" (descriptive, described as father of Felix/Agatha)
        → Merge "De Lacey" into "the old man" as alias

        Returns:
            Tuple of (updated_supporting_cast, char_ids_with_new_aliases_in_main_cast)
        """
        chars_to_remove = set()
        chars_with_new_aliases = set()

        # Step 1: Build map of surnames → main cast characters
        surname_to_chars: dict[str, list[Character]] = {}
        for char in main_cast:
            parts = char.canonical_name.split()
            if len(parts) >= 2:
                surname = parts[-1].lower()
                if surname not in surname_to_chars:
                    surname_to_chars[surname] = []
                surname_to_chars[surname].append(char)

        logger.debug(
            f"_merge_surname_into_family_descriptive: Found surname families: "
            f"{[(s, [c.canonical_name for c in chars]) for s, chars in surname_to_chars.items() if len(chars) >= 2]}"
        )

        # Step 2: Find bare surnames in supporting cast
        for supp_idx, supp_char in enumerate(supporting_cast):
            supp_name = supp_char.canonical_name.strip()
            supp_lower = supp_name.lower()

            # Skip if not a bare surname (single word, title-case)
            if " " in supp_name:
                continue
            if not supp_name or not supp_name[0].isupper():
                continue

            # Skip if already a descriptive handle
            if supp_lower.startswith("the "):
                continue

            # Check if this surname matches main cast family members
            if supp_lower not in surname_to_chars:
                continue

            family_members = surname_to_chars[supp_lower]
            if len(family_members) < 2:
                continue  # Need at least 2 family members to infer relationship

            logger.info(
                f"Found bare surname '{supp_name}' matching {len(family_members)} "
                f"main cast family members: {[c.canonical_name for c in family_members]}"
            )

            # Step 3: Find descriptive handles that could be this family member
            for main_char in main_cast:
                main_name = main_char.canonical_name.lower().strip()

                # Only check descriptive patterns
                if not main_name.startswith("the "):
                    continue

                # Skip if already has this surname as alias
                if any(supp_lower in alias.lower() for alias in main_char.aliases):
                    logger.debug(
                        f"Skipping '{main_char.canonical_name}' - already has '{supp_name}' as alias"
                    )
                    continue

                # Check for family relationship indicators in description
                description = (main_char.description or "").lower()
                family_indicators = ["father", "mother", "parent", "patriarch", "matriarch"]

                # Check if main_char is described as family member of surname-holders
                is_family = any(ind in description for ind in family_indicators)
                if not is_family:
                    # Also check if any family member's name appears in description
                    for fm in family_members:
                        first_name = fm.canonical_name.split()[0].lower()
                        if first_name in description:
                            is_family = True
                            logger.debug(
                                f"Family relationship detected via description: "
                                f"'{main_char.canonical_name}' mentions '{first_name}'"
                            )
                            break

                if is_family:
                    logger.info(
                        f"Merging surname '{supp_name}' into descriptive handle "
                        f"'{main_char.canonical_name}' (family relationship detected)"
                    )

                    # Merge
                    if supp_char.canonical_name not in main_char.aliases:
                        main_char.aliases.append(supp_char.canonical_name)
                    for alias in supp_char.aliases:
                        if alias not in main_char.aliases:
                            main_char.aliases.append(alias)

                    main_char.mention_count += supp_char.mention_count
                    chars_to_remove.add(supp_idx)
                    chars_with_new_aliases.add(main_char.id)
                    break  # Only merge into one descriptive handle

        # Remove merged characters
        updated_supporting = [
            c for i, c in enumerate(supporting_cast) if i not in chars_to_remove
        ]

        return updated_supporting, chars_with_new_aliases

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

    def _get_narrative_style(self, context: AgentContext) -> Optional[str]:
        """Extract narrative_style from summaries result metadata or chapter POV heuristics."""
        summaries_result = context.get_result("summaries")
        if not summaries_result:
            return None

        # Check pipeline_metadata first (if populated upstream)
        if hasattr(summaries_result, "pipeline_metadata"):
            style = summaries_result.pipeline_metadata.get("narrative_style")
            if style:
                return style

        # Heuristic: check pov_character across chapter summaries
        if hasattr(summaries_result, "summaries"):
            pov_chars = [
                s.pov_character for s in summaries_result.summaries
                if s.pov_character
            ]
            if pov_chars:
                from collections import Counter
                most_common = Counter(pov_chars).most_common(1)[0]
                if most_common[1] >= len(summaries_result.summaries) * 0.5:
                    return "first-person"

        # Fallback: check summary text for first-person indicators
        if hasattr(summaries_result, "summaries") and summaries_result.summaries:
            first_summary = summaries_result.summaries[0].summary.lower()
            first_person_markers = [" i ", " my ", " me ", "narrator", "first-person", "first person"]
            if sum(1 for m in first_person_markers if m in first_summary) >= 2:
                return "first-person"

        return None

    def _find_narrator_in_supporting(
        self,
        narrator_name: str,
        supporting_cast: list[Character],
    ) -> Optional[tuple[Character, list[Character]]]:
        """
        Search supporting_cast for name fragment(s) matching the narrator name.

        Handles split identities where e.g. "Nick Carraway" was extracted as
        separate supporting entries "Nick" (24 mentions) and "Carraway" (10 mentions),
        neither of which crossed the promotion threshold.  All fragments whose
        canonical name or alias is a contiguous word-sequence within narrator_name
        are merged into a single promoted character.

        Returns (merged_character, remaining_supporting) or None if no match found.
        """
        if not narrator_name or not supporting_cast:
            return None

        narrator_words = narrator_name.strip().lower().split()
        if not narrator_words:
            return None

        matches: list[Character] = []
        for char in supporting_cast:
            all_forms = [char.canonical_name] + list(char.aliases or [])
            for form in all_forms:
                form_lower = form.strip().lower()
                if not form_lower or len(form_lower) < 3:
                    continue
                form_words = form_lower.split()
                # Accept only if form_words is a contiguous sub-sequence of narrator_words
                n = len(narrator_words)
                k = len(form_words)
                found = any(
                    narrator_words[i:i + k] == form_words
                    for i in range(n - k + 1)
                )
                if found:
                    matches.append(char)
                    break

        if not matches:
            return None

        base = max(matches, key=lambda c: c.mention_count)
        merged_count = sum(c.mention_count for c in matches)

        all_aliases: list[str] = list(base.aliases or [])
        for char in matches:
            if char is base:
                continue
            if char.canonical_name != narrator_name and char.canonical_name not in all_aliases:
                all_aliases.append(char.canonical_name)
            for a in char.aliases or []:
                if a != narrator_name and a not in all_aliases:
                    all_aliases.append(a)

        first_chap = min(
            (c.first_appearance_chapter for c in matches if c.first_appearance_chapter is not None),
            default=None,
        )

        merged = Character(
            id=base.id,
            canonical_name=narrator_name,
            aliases=all_aliases,
            role="protagonist",
            mention_count=merged_count,
            is_narrator=True,
            narrative_role="First-Person Narrator",
            confidence=base.confidence,
            first_appearance_chapter=first_chap,
        )

        matched_ids = {c.id for c in matches}
        remaining = [c for c in supporting_cast if c.id not in matched_ids]

        logger.info(
            f"_find_narrator_in_supporting: merged "
            f"{[c.canonical_name for c in matches]} → '{narrator_name}' "
            f"(total mentions: {merged_count})"
        )
        return merged, remaining

    def _heuristic_narrator_from_mention_count(
        self,
        main_cast: list[Character],
        plot_summary: Optional[str],
    ) -> Optional[Character]:
        """
        Heuristic narrator identification for confirmed first-person narratives.

        In first-person narratives the narrator typically has the lowest direct
        name-mention count (they say "I" instead of their own name). Among main cast
        characters who appear in the plot_summary, the one with the fewest text
        mentions is the most likely narrator.

        This is a universal invariant across first-person fiction: the protagonist-
        narrator uses "I" far more than their own name, so their name-mention count
        is anomalously low compared to other named characters.
        """
        if not main_cast:
            return None

        # Prefer candidates who are explicitly named in the plot_summary
        # (confirms they are plot-central, not a minor character with few mentions)
        candidates = []
        if plot_summary:
            plot_lower = plot_summary.lower()
            for char in main_cast:
                if char.canonical_name.lower() in plot_lower:
                    candidates.append(char)

        if not candidates:
            candidates = list(main_cast)

        # The narrator has the lowest mention count (uses "I" not their name)
        return min(candidates, key=lambda c: c.mention_count, default=None)
