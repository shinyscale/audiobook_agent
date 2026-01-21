"""
CharacterAgentV2 - Summary-Driven Character Extraction

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

from .base import (
    Agent,
    AgentContext,
    AgentResult,
    VerificationResult,
    VerificationIssue,
    VerificationLevel,
)
from .config import AgentConfig
from ..pipeline.character_extraction.models import CharacterMap, Character as PipelineCharacter
from ..pipeline.character_extraction_v2 import (
    MainCastExtractor,
    MentionSearcher,
    GroundingGate,
    NarratorDetector,
    SupportingCastExtractor,
)
from ..models import Character, StructuralElement, StructureType
from ..llm.client import LLMClient

logger = logging.getLogger(__name__)


class CharacterAgentV2(Agent):
    """
    V2 Character Agent using summary-driven extraction.

    Pipeline order: summaries → main_cast → mentions → grounding → narrator → supporting
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        config: Optional[AgentConfig] = None,
        min_grounding_mentions: int = 3,
    ):
        self.llm = llm_client
        self.config = config or AgentConfig()
        self.min_grounding_mentions = min_grounding_mentions

    @property
    def name(self) -> str:
        return "characters_v2"

    @property
    def depends_on(self) -> list[str]:
        """V2 requires summaries (from SummaryAgent) before running."""
        return ["structure", "summaries"]

    @property
    def recommended_models(self) -> list[str]:
        return [
            "qwen2.5:72b",  # Strong local model for character understanding
            "llama3.2",     # Good local alternative
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
        main_cast_extractor = MainCastExtractor(self.llm)
        profiles = main_cast_extractor.extract(chapter_summaries, plot_summary)

        if not profiles:
            issues.append("No main cast profiles extracted from summaries")

        # Convert profiles to Character objects
        characters = main_cast_extractor.profiles_to_characters(profiles)
        logger.info(f"V2 Step 1 complete: {len(characters)} main cast candidates")

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

        # STEP 3.5: Merge within main cast (last-name-only, spelling variants, first-name-only)
        logger.info("V2 Step 3.5: Merging within main cast")
        main_cast, within_main_aliases_added = self._merge_within_main_cast(main_cast)

        # Re-search mentions for characters that gained new aliases
        if within_main_aliases_added:
            logger.info(f"Re-searching mentions for {len(within_main_aliases_added)} characters with new aliases")
            for char_id in within_main_aliases_added:
                char = next((c for c in main_cast if c.id == char_id), None)
                if char:
                    result = searcher.search_character(char)
                    char.mention_count = result.total_mentions
                    if result.chapter_distribution:
                        chapters = sorted(result.chapter_distribution.keys())
                        char.first_appearance_chapter = chapters[0]

        logger.info(f"V2 Step 3.5 complete: {len(main_cast)} main cast after within-cast merge")

        # STEP 4: Detect narrator (F4)
        logger.info("V2 Step 4: Detecting narrator")
        narrator_detector = NarratorDetector(self.llm)
        narrator_info = narrator_detector.detect(
            chapter_summaries, main_cast, plot_summary
        )
        main_cast = narrator_detector.update_characters_with_narrator(
            main_cast, narrator_info
        )

        logger.info(
            f"V2 Step 4 complete: POV={narrator_info.pov}, "
            f"narrator={narrator_info.narrator_name}"
        )

        # STEP 5: Extract supporting cast (F3)
        logger.info("V2 Step 5: Extracting supporting cast via NER")
        main_cast_names = self._collect_all_names(main_cast)
        supporting_extractor = SupportingCastExtractor(
            context.text,
            min_mentions=3,
        )
        supporting_cast = supporting_extractor.extract(main_cast_names)

        logger.info(f"V2 Step 5 complete: {len(supporting_cast)} supporting characters")

        # STEP 5.5: Merge last-name-only supporting characters as aliases
        main_cast, supporting_cast, aliases_added = self._merge_lastname_aliases(
            main_cast, supporting_cast
        )

        # Re-search mentions for characters that gained new aliases
        if aliases_added:
            logger.info(f"Re-searching mentions for {len(aliases_added)} characters with new aliases")
            for char_id in aliases_added:
                char = next((c for c in main_cast if c.id == char_id), None)
                if char:
                    result = searcher.search_character(char)
                    char.mention_count = result.total_mentions
                    if result.chapter_distribution:
                        chapters = sorted(result.chapter_distribution.keys())
                        char.first_appearance_chapter = chapters[0]

        logger.info(
            f"V2 Step 5.5 complete: {len(main_cast)} main cast, "
            f"{len(supporting_cast)} supporting after last-name merge"
        )

        # STEP 5.6: Merge within supporting cast (last-name-only, spelling variants)
        supporting_cast, supp_aliases_added = self._merge_within_supporting_cast(
            supporting_cast
        )

        # Re-search mentions for supporting characters that gained new aliases
        if supp_aliases_added:
            logger.info(f"Re-searching mentions for {len(supp_aliases_added)} supporting chars with new aliases")
            for char_id in supp_aliases_added:
                char = next((c for c in supporting_cast if c.id == char_id), None)
                if char:
                    result = searcher.search_character(char)
                    char.mention_count = result.total_mentions
                    if result.chapter_distribution:
                        chapters = sorted(result.chapter_distribution.keys())
                        char.first_appearance_chapter = chapters[0]

        logger.info(
            f"V2 Step 5.6 complete: {len(supporting_cast)} supporting after within-supporting merge"
        )

        # Build final CharacterMap
        all_characters = self._convert_to_pipeline_characters(
            main_cast, supporting_cast
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
            issues.append(VerificationIssue(
                description=f"Only {main_count} main cast characters - may be incomplete",
                severity="warning",
            ))
        elif main_count > 20:
            issues.append(VerificationIssue(
                description=f"{main_count} main cast characters - may have over-extraction",
                severity="warning",
            ))

        # Check 2: Grounding worked
        ungrounded = character_map.pipeline_metadata.get("ungrounded_count", 0)
        if ungrounded > main_count:
            issues.append(VerificationIssue(
                description=f"More ungrounded ({ungrounded}) than grounded ({main_count}) characters",
                severity="warning",
            ))

        # Check 3: Low confidence items
        if result.low_confidence_count > 0:
            issues.append(VerificationIssue(
                description=f"{result.low_confidence_count} characters have low confidence",
                severity="info",
            ))

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
        if summaries_result:
            # SummaryAgent returns a list of ChapterSummary objects or similar
            if hasattr(summaries_result, "summaries"):
                return [s.summary for s in summaries_result.summaries if s.summary]
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
                    summaries.append(ch.summary)
            if summaries:
                return summaries

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
                    # Merge char2 into char1
                    logger.info(
                        f"Merging title variant: '{char2.canonical_name}' → "
                        f"'{char1.canonical_name}' (as alias)"
                    )

                    # Add char2's canonical name as an alias of char1
                    if char2.canonical_name not in char1.aliases:
                        char1.aliases.append(char2.canonical_name)

                    # Add char2's aliases to char1
                    for alias in char2.aliases:
                        if alias not in char1.aliases and alias != char1.canonical_name:
                            char1.aliases.append(alias)

                    skip_indices.add(j)

                elif self._name_contains_other(name2_lower, name1_lower):
                    # Merge char1 into char2
                    logger.info(
                        f"Merging title variant: '{char1.canonical_name}' → "
                        f"'{char2.canonical_name}' (as alias)"
                    )

                    # Add char1's canonical name as an alias of char2
                    if char1.canonical_name not in char2.aliases:
                        char2.aliases.append(char1.canonical_name)

                    # Add char1's aliases to char2
                    for alias in char1.aliases:
                        if alias not in char2.aliases and alias != char2.canonical_name:
                            char2.aliases.append(alias)

                    skip_indices.add(i)
                    break  # Don't process this character further

            if i not in skip_indices:
                merged.append(char1)

        return merged

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
        pattern = r'(?:^|[\s\-\.])'  + escaped + r'(?:$|[\s\-\.])'
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
            r"\bLord\b",
            r"\bLady\b",
            r"\bSir\b",
        ]

        # Remove any leading title
        for title in titles:
            name = re.sub(f"^{title}\\s+", "", name, flags=re.IGNORECASE)

        return name.strip()

    def _merge_within_main_cast(
        self,
        main_cast: list[Character],
    ) -> tuple[list[Character], set[str]]:
        """
        Merge characters within main cast that are variants of each other.

        Handles three patterns:
        1. Last-name-only → Full name: "Wilson" (65 mentions) → alias of "George B. Wilson"
        2. Spelling variants: "Wolfsheim" ↔ "Wolfshiem" (85% fuzzy match)
        3. First-name-only → Full name: "George" → alias of "George B. Wilson"

        Returns:
            Tuple of (updated_main_cast, char_ids_with_new_aliases)
        """
        from difflib import SequenceMatcher

        chars_to_remove = set()
        chars_with_new_aliases = set()

        # Pass 1: Merge last-name-only characters
        for idx, char in enumerate(main_cast):
            if idx in chars_to_remove:
                continue

            char_name = char.canonical_name.strip()
            if not char_name or ' ' in char_name:
                continue  # Skip empty or multi-word names

            # This is a single-word name (potential last name or first name)
            # Check if it matches the last word of any OTHER main cast character

            matches = []
            for other_idx, other_char in enumerate(main_cast):
                if other_idx == idx or other_idx in chars_to_remove:
                    continue

                other_name = other_char.canonical_name.strip()
                if not other_name or ' ' not in other_name:
                    continue  # Only match against multi-word names

                # Check last name match
                other_parts = other_name.split()
                other_lastname = other_parts[-1].strip('.,;:')

                # Exact last name match
                if char_name.lower() == other_lastname.lower():
                    matches.append((other_idx, "exact_lastname"))
                    continue

                # Fuzzy last name match (handles Wolfsheim/Wolfshiem)
                similarity = SequenceMatcher(
                    None,
                    char_name.lower(),
                    other_lastname.lower()
                ).ratio()

                if similarity >= 0.85:
                    matches.append((other_idx, "fuzzy_lastname"))
                    continue

                # Check first name match (if other_name has multiple parts)
                if len(other_parts) >= 2:
                    other_firstname = other_parts[0].strip('.,;:')
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
                similarity = SequenceMatcher(
                    None,
                    char_name.lower(),
                    other_name.lower()
                ).ratio()

                if similarity >= 0.85:  # 85% similar
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
            char for idx, char in enumerate(main_cast)
            if idx not in chars_to_remove
        ]

        # Pass 3: Re-run last-name matching after spelling variants are merged
        # This handles cases like "Wolfshiem" which initially had ambiguous matches,
        # but after Pass 2 merging has only one match remaining
        chars_to_remove_pass3 = set()

        for idx, char in enumerate(updated_main_cast):
            char_name = char.canonical_name.strip()
            if not char_name or ' ' in char_name:
                continue  # Skip empty or multi-word names

            # Check if this single-word name now has exactly ONE match
            matches = []
            for other_idx, other_char in enumerate(updated_main_cast):
                if other_idx == idx:
                    continue

                other_name = other_char.canonical_name.strip()
                if not other_name or ' ' not in other_name:
                    continue

                other_parts = other_name.split()
                other_lastname = other_parts[-1].strip('.,;:')

                # Exact or fuzzy last name match
                if char_name.lower() == other_lastname.lower():
                    matches.append((other_idx, "exact_lastname"))
                else:
                    similarity = SequenceMatcher(
                        None,
                        char_name.lower(),
                        other_lastname.lower()
                    ).ratio()
                    if similarity >= 0.85:
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
            char for idx, char in enumerate(updated_main_cast)
            if idx not in chars_to_remove_pass3
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

        Returns:
            Tuple of (updated_main_cast, updated_supporting_cast, char_ids_with_new_aliases)
        """
        import re
        from difflib import SequenceMatcher

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

            # Only process single-word names (potential last names)
            if ' ' in supp_name:
                continue

            # Check if this could be a last name of any main cast character
            matches = []

            for main_idx, main_char in enumerate(main_cast):
                # Extract last name from main character's canonical name
                main_name_parts = main_char.canonical_name.strip().split()

                if not main_name_parts:
                    continue

                # Get last word as potential surname
                main_lastname = main_name_parts[-1].strip('.,;:')

                # Check for exact match (case-insensitive)
                if supp_name.lower() == main_lastname.lower():
                    matches.append((main_idx, "exact"))
                    continue

                # Check for fuzzy match (handles Wolfsheim/Wolfshiem)
                similarity = SequenceMatcher(
                    None,
                    supp_name.lower(),
                    main_lastname.lower()
                ).ratio()

                if similarity >= 0.85:  # 85% similar
                    matches.append((main_idx, "fuzzy_lastname"))
                    continue

                # Check first name match (if main_name has multiple parts)
                if len(main_name_parts) >= 2:
                    main_firstname = main_name_parts[0].strip('.,;:')
                    if supp_name.lower() == main_firstname.lower():
                        matches.append((main_idx, "exact_firstname"))

            # Only merge if there's exactly ONE match
            # (avoids merging when multiple characters share a surname)
            if len(matches) == 1:
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

        # Remove merged characters from supporting cast
        updated_supporting = [
            char for idx, char in enumerate(supporting_cast)
            if idx not in supporting_to_remove
        ]

        return main_cast, updated_supporting, chars_with_new_aliases

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
        from difflib import SequenceMatcher

        chars_to_remove = set()
        chars_with_new_aliases = set()

        # Pass 1: Merge last-name-only characters
        for idx, char in enumerate(supporting_cast):
            if idx in chars_to_remove:
                continue

            char_name = char.canonical_name.strip()
            if not char_name or ' ' in char_name:
                continue  # Skip empty or multi-word names

            # This is a single-word name (potential last name)
            # Check if it matches the last word of any OTHER supporting character

            matches = []
            for other_idx, other_char in enumerate(supporting_cast):
                if other_idx == idx or other_idx in chars_to_remove:
                    continue

                other_name = other_char.canonical_name.strip()
                if not other_name or ' ' not in other_name:
                    continue  # Only match against multi-word names

                # Check last name match
                other_parts = other_name.split()
                other_lastname = other_parts[-1].strip('.,;:')

                # Exact last name match
                if char_name.lower() == other_lastname.lower():
                    matches.append((other_idx, "exact_lastname"))
                    continue

                # Fuzzy last name match (handles Wolfsheim/Wolfshiem)
                similarity = SequenceMatcher(
                    None,
                    char_name.lower(),
                    other_lastname.lower()
                ).ratio()

                if similarity >= 0.85:
                    matches.append((other_idx, "fuzzy_lastname"))

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

                # Check if names are very similar (spelling variants)
                similarity = SequenceMatcher(
                    None,
                    char_name.lower(),
                    other_name.lower()
                ).ratio()

                if similarity >= 0.85:  # 85% similar
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

        # Remove merged characters
        updated_supporting = [
            char for idx, char in enumerate(supporting_cast)
            if idx not in chars_to_remove
        ]

        return updated_supporting, chars_with_new_aliases

    def _convert_to_pipeline_characters(
        self,
        main_cast: list[Character],
        supporting_cast: list[Character],
    ) -> list[PipelineCharacter]:
        """Convert model Characters to pipeline Characters for output compatibility."""
        result = []

        for char in main_cast:
            # Convert model.Character to pipeline Character
            pc = PipelineCharacter(
                id=char.id,
                canonical_name=char.canonical_name,
                aliases=char.aliases,
                mentions=[],  # Mentions are tracked separately in v2
                first_appearance_chapter=char.first_appearance_chapter or 0,
                mention_count=char.mention_count,
                chapters_present=[],  # Filled from mention search
                confidence=0.85 if char.confidence.value == "high" else 0.6,
                supporting_strategies=["v2_summary_extraction"],
                description=self._get_description_text(char),
                is_narrator=char.is_narrator,
                narrative_role=char.narrative_role,
                role=char.role or "main",
            )
            result.append(pc)

        for char in supporting_cast:
            pc = PipelineCharacter(
                id=char.id,
                canonical_name=char.canonical_name,
                aliases=char.aliases,
                mentions=[],
                first_appearance_chapter=char.first_appearance_chapter or 0,
                mention_count=char.mention_count,
                chapters_present=[],
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
