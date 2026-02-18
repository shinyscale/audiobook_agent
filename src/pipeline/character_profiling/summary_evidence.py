"""
Summary-derived evidence extractor for character profiling.

Extracts character-specific statements from chapter summaries to use as
PRIMARY evidence in profile generation. This ranks above raw text mentions
because summaries capture the LLM's understanding of significant events.

Feature F2: Summary-Derived Profile Evidence
"""

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from ..chapter_summary.models import ChapterSummary, ChapterSummaryMap
from ..llm import LLMClient
from .perspective_filter import should_exclude_narrator_perspective_for_non_narrator

if TYPE_CHECKING:
    from .name_disambiguator import ContextDisambiguator

logger = logging.getLogger(__name__)


@dataclass
class SummaryEvidence:
    """Evidence about a character extracted from a chapter summary."""

    character_name: str
    statement: str  # The relevant statement about the character
    chapter_index: int
    source_type: str  # "summary", "key_event", or "character_present"
    relevance_score: float = 0.8  # How relevant this evidence is (0-1)

    def to_dict(self) -> dict:
        return {
            "character_name": self.character_name,
            "statement": self.statement,
            "chapter_index": self.chapter_index,
            "source_type": self.source_type,
            "relevance_score": self.relevance_score,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SummaryEvidence":
        return cls(
            character_name=data["character_name"],
            statement=data["statement"],
            chapter_index=data["chapter_index"],
            source_type=data["source_type"],
            relevance_score=data.get("relevance_score", 0.8),
        )


@dataclass
class CharacterSummaryEvidence:
    """All summary-derived evidence for a single character."""

    character_name: str
    aliases: list[str] = field(default_factory=list)
    evidence: list[SummaryEvidence] = field(default_factory=list)

    # Derived from evidence
    key_actions: list[str] = field(default_factory=list)  # Actions mentioned in summaries
    key_relationships: list[str] = field(default_factory=list)  # Relationships noted
    key_traits: list[str] = field(default_factory=list)  # Character traits mentioned

    def to_dict(self) -> dict:
        return {
            "character_name": self.character_name,
            "aliases": self.aliases,
            "evidence": [e.to_dict() for e in self.evidence],
            "key_actions": self.key_actions,
            "key_relationships": self.key_relationships,
            "key_traits": self.key_traits,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CharacterSummaryEvidence":
        return cls(
            character_name=data["character_name"],
            aliases=data.get("aliases", []),
            evidence=[SummaryEvidence.from_dict(e) for e in data.get("evidence", [])],
            key_actions=data.get("key_actions", []),
            key_relationships=data.get("key_relationships", []),
            key_traits=data.get("key_traits", []),
        )

    def format_for_prompt(self) -> str:
        """Format evidence for inclusion in profile generation prompt."""
        if not self.evidence:
            return ""

        lines = [f"=== SUMMARY EVIDENCE FOR {self.character_name} (HIGH PRIORITY) ==="]
        lines.append(
            "These statements come from chapter summaries and represent confirmed plot events:"
        )
        lines.append("")

        # Group by chapter
        by_chapter: dict[int, list[SummaryEvidence]] = {}
        for ev in self.evidence:
            by_chapter.setdefault(ev.chapter_index, []).append(ev)

        for chapter_idx in sorted(by_chapter.keys()):
            chapter_evidence = by_chapter[chapter_idx]
            lines.append(f"Chapter {chapter_idx}:")
            for ev in chapter_evidence:
                lines.append(f"  - {ev.statement}")

        if self.key_actions:
            lines.append("")
            lines.append("KEY ACTIONS from summaries:")
            for action in self.key_actions:
                lines.append(f"  * {action}")

        lines.append("")
        return "\n".join(lines)


EVIDENCE_EXTRACTION_SYSTEM = """You are extracting character evidence from chapter summaries.

Your job is to identify statements that directly describe a character's:
1. ACTIONS - What they DO (highest importance)
2. RELATIONSHIPS - How they relate to other characters
3. TRAITS - Personality characteristics revealed
4. EVENTS - Significant events they're involved in

Extract only statements that are DIRECTLY relevant to the specified character.
Be specific and preserve important details from the summaries.

Respond with valid JSON only."""


EVIDENCE_EXTRACTION_PROMPT = """Extract evidence about "{character_name}" from these chapter summaries.

CHARACTER: {character_name}
ALIASES: {aliases}
{disambiguation_context}
CHAPTER SUMMARIES:
{summaries}

Extract statements about this character that describe:
- Actions they take (especially morally significant ones)
- Their relationships to other characters
- Their personality or behavior patterns
- Significant events they cause or are involved in

Return JSON:
```json
{{
  "relevant_statements": [
    {{
      "chapter_index": 1,
      "statement": "Character does X to Y",
      "category": "action/relationship/trait/event"
    }}
  ],
  "key_actions": ["action 1", "action 2"],
  "key_relationships": ["relationship to Person A"],
  "key_traits": ["trait 1", "trait 2"]
}}
```

Only include statements that DIRECTLY mention or involve {character_name}.
Do not infer or assume - extract only what is explicitly stated."""


class SummaryEvidenceExtractor:
    """
    Extracts character-relevant evidence from chapter summaries.

    This evidence is ranked ABOVE raw text mentions because summaries
    represent the LLM's distillation of significant plot events.
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        all_character_names: Optional[list[str]] = None,
        disambiguator: Optional["ContextDisambiguator"] = None,
    ):
        """
        Args:
            llm_client: Optional LLM for enhanced extraction. If None, uses pattern-based extraction.
            all_character_names: List of all character names for collision detection.
            disambiguator: Optional ContextDisambiguator for same-name character handling.
        """
        self.llm = llm_client
        self.surname_collisions = self._build_surname_collisions(all_character_names or [])
        self.disambiguator = disambiguator
        # Statistics for disambiguation
        self._disambiguation_stats = {
            "checked": 0,
            "skipped_different_character": 0,
            "kept_same_character": 0,
            "kept_not_ambiguous": 0,
        }

    def _build_surname_collisions(self, names: list[str]) -> dict[str, list[str]]:
        """
        Build a map of name_part -> list of full names containing that part.

        This helps detect when extracting evidence for a short name but
        the sentence is actually about a longer name containing that part.

        Examples:
        - "Ames" (parents) vs "Cathy Ames" (daughter) - surname collision
        - "John" (nephew) vs "John Donaldson" (father) - first name collision

        Args:
            names: List of all character names

        Returns:
            Dict mapping short name or name part to list of longer names containing it
        """
        collisions: dict[str, list[str]] = {}

        # First pass: Build collisions for each name part (first, middle, last)
        for name in names:
            name_lower = name.lower().strip()
            parts = name_lower.split()

            # Extract all parts (first name, middle name, surname)
            for part in parts:
                # Find all names that contain this part
                for other_name in names:
                    other_lower = other_name.lower().strip()
                    if other_lower == name_lower:
                        continue

                    other_parts = other_lower.split()
                    if part in other_parts:
                        # This part appears in another name
                        if part not in collisions:
                            collisions[part] = []
                        if name not in collisions[part]:
                            collisions[part].append(name)
                        if other_name not in collisions[part]:
                            collisions[part].append(other_name)

        # Second pass: Single-word names need special handling
        # Map single-word name to all longer names containing it
        for name in names:
            name_lower = name.lower().strip()
            parts = name_lower.split()

            if len(parts) == 1:
                # This is a single-word name (e.g., "John")
                # Find all longer names that contain this word
                for other_name in names:
                    other_lower = other_name.lower().strip()
                    other_parts = other_lower.split()

                    # Skip if same name or other is also single-word
                    if other_lower == name_lower or len(other_parts) == 1:
                        continue

                    # Check if our single word appears in the other name
                    if name_lower in other_parts:
                        if name_lower not in collisions:
                            collisions[name_lower] = []
                        if name not in collisions[name_lower]:
                            collisions[name_lower].append(name)
                        if other_name not in collisions[name_lower]:
                            collisions[name_lower].append(other_name)

        return collisions

    def _is_collision_sentence(
        self,
        target_name: str,
        sentence: str,
        all_names: list[str],
    ) -> bool:
        """
        Check if a sentence is primarily about a different character.

        When extracting evidence for "Ames" and the sentence contains
        "Cathy Ames did X", return True because the sentence is about
        Cathy, not about "Ames" (the parents).

        Args:
            target_name: The name we're extracting evidence for
            sentence: The sentence to check
            all_names: All name variants for the target character

        Returns:
            True if the sentence is primarily about a different character
        """
        target_lower = target_name.lower().strip()
        # Note: sentence lowercasing not needed - _name_in_text() uses case-insensitive matching

        # Check if target is a short name (single word or surname only)
        target_parts = target_lower.split()

        # For single-word targets (like "Ames"), check for longer variants
        if len(target_parts) == 1:
            # Look for any full name containing this word
            for collision_key, collision_names in self.surname_collisions.items():
                if collision_key == target_lower or target_lower in collision_key:
                    # Check if any longer name is in the sentence
                    for full_name in collision_names:
                        full_lower = full_name.lower()
                        # Skip if this IS our target
                        if full_lower == target_lower or full_lower in [
                            n.lower() for n in all_names
                        ]:
                            continue
                        # Check if the longer name appears in the sentence
                        if self._name_in_text(full_name, sentence):
                            logger.debug(
                                f"Collision detected: extracting for '{target_name}' "
                                f"but sentence contains '{full_name}'"
                            )
                            return True

        # For multi-word targets, check if a longer variant is present
        # e.g., "Mr. Ames" but sentence has "Cathy Ames"
        if len(target_parts) >= 2:
            surname = target_parts[-1]
            if surname in self.surname_collisions:
                for full_name in self.surname_collisions[surname]:
                    full_lower = full_name.lower()
                    # Skip if this is our target
                    if full_lower == target_lower or full_lower in [n.lower() for n in all_names]:
                        continue
                    # Check if sentence contains the other full name
                    if self._name_in_text(full_name, sentence):
                        # Verify the other name is truly different
                        # (not just a variant like "Mr. Ames" vs "Mrs. Ames")
                        other_parts = full_lower.split()
                        # If first names are different, it's a collision
                        if len(other_parts) >= 2 and other_parts[0] != target_parts[0]:
                            logger.debug(
                                f"Collision detected: extracting for '{target_name}' "
                                f"but sentence contains '{full_name}'"
                            )
                            return True

        return False

    def extract_evidence(
        self,
        character_name: str,
        aliases: list[str],
        summary_map: ChapterSummaryMap,
        is_narrator: bool = False,
        narrative_style: str = "unknown",
    ) -> CharacterSummaryEvidence:
        """
        Extract all summary evidence for a character.

        Args:
            character_name: The character's canonical name
            aliases: Alternative names/forms for the character
            summary_map: All chapter summaries
            is_narrator: Whether this character is the narrator
            narrative_style: Narrative style ("first-person", "third-person", "mixed", "unknown")

        Returns:
            CharacterSummaryEvidence with all extracted evidence
        """
        all_names = [character_name] + aliases
        evidence_result = CharacterSummaryEvidence(
            character_name=character_name,
            aliases=aliases,
        )

        # Pattern-based extraction (always run)
        pattern_evidence = self._extract_pattern_based(
            all_names,
            summary_map,
            is_narrator=is_narrator,
            narrative_style=narrative_style,
        )
        evidence_result.evidence.extend(pattern_evidence)

        # First-person evidence extraction for narrators
        if is_narrator and narrative_style == "first-person":
            for summary in summary_map.summaries:
                fp_evidence = self._extract_first_person_evidence(summary, character_name)
                for ev in fp_evidence:
                    if not self._is_duplicate(ev.statement, evidence_result.evidence):
                        evidence_result.evidence.append(ev)
            logger.info(f"Extracted first-person evidence for narrator {character_name}")

        # LLM-based extraction for deeper analysis (if available)
        if self.llm and len(pattern_evidence) > 0:
            llm_evidence = self._extract_llm_based(character_name, aliases, summary_map)
            if llm_evidence:
                evidence_result.key_actions = llm_evidence.get("key_actions", [])
                evidence_result.key_relationships = llm_evidence.get("key_relationships", [])
                evidence_result.key_traits = llm_evidence.get("key_traits", [])

                # Add any new statements not captured by pattern matching
                for stmt in llm_evidence.get("relevant_statements", []):
                    if not self._is_duplicate(stmt["statement"], evidence_result.evidence):
                        evidence_result.evidence.append(
                            SummaryEvidence(
                                character_name=character_name,
                                statement=stmt["statement"],
                                chapter_index=stmt.get("chapter_index", 0),
                                source_type="summary",
                                relevance_score=0.9,  # LLM-identified is high relevance
                            )
                        )

        # Log extraction results including disambiguation stats
        if self.disambiguator and self._disambiguation_stats["checked"] > 0:
            stats = self._disambiguation_stats
            logger.info(
                f"Extracted {len(evidence_result.evidence)} summary evidence items "
                f"for {character_name} (disambiguation: {stats['checked']} checked, "
                f"{stats['skipped_different_character']} skipped as different character)"
            )
        else:
            logger.info(
                f"Extracted {len(evidence_result.evidence)} summary evidence items "
                f"for {character_name}"
            )

        return evidence_result

    def _extract_first_person_evidence(
        self,
        summary: ChapterSummary,
        narrator_name: str,
    ) -> list[SummaryEvidence]:
        """
        Extract evidence from first-person statements for the narrator.

        First-person pronouns ("I", "my", etc.) in summaries should be
        attributed to the narrator.

        Args:
            summary: A chapter summary
            narrator_name: The narrator's name

        Returns:
            List of SummaryEvidence items from first-person statements
        """
        evidence = []

        first_person_patterns = [
            r"\bI\b",
            r"\bmy\b",
            r"\bme\b",
            r"\bmyself\b",
            r"\bI'm\b",
            r"\bI've\b",
            r"\bI'd\b",
            r"\bI'll\b",
        ]

        sentences = re.split(r"(?<=[.!?])\s+", summary.summary)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            has_first_person = any(
                re.search(pattern, sentence, re.IGNORECASE) for pattern in first_person_patterns
            )

            if has_first_person:
                score = self._score_statement(sentence)
                evidence.append(
                    SummaryEvidence(
                        character_name=narrator_name,
                        statement=sentence,
                        chapter_index=summary.chapter_index,
                        source_type="first_person_narration",
                        relevance_score=score,
                    )
                )

        return evidence

    def _extract_pattern_based(
        self,
        names: list[str],
        summary_map: ChapterSummaryMap,
        is_narrator: bool = False,
        narrative_style: str = "unknown",
    ) -> list[SummaryEvidence]:
        """Extract evidence using pattern matching on summaries."""
        evidence = []

        for summary in summary_map.summaries:
            # Check if character is in this chapter
            chapter_chars = [c.lower() for c in summary.characters_present]
            name_in_chapter = any(
                name.lower() in chapter_chars or any(name.lower() in c for c in chapter_chars)
                for name in names
            )

            if not name_in_chapter:
                continue

            # Extract from summary text - pass chapter_summary for disambiguation
            summary_statements = self._extract_statements_mentioning(
                summary.summary, names, summary.chapter_index, "summary",
                chapter_summary=summary,
                is_narrator=is_narrator,
                narrative_style=narrative_style,
            )
            evidence.extend(summary_statements)

            # Extract from key events - pass chapter_summary for disambiguation
            for event in summary.key_events:
                event_statements = self._extract_statements_mentioning(
                    event, names, summary.chapter_index, "key_event",
                    chapter_summary=summary,
                    is_narrator=is_narrator,
                    narrative_style=narrative_style,
                )
                evidence.extend(event_statements)

            # ALSO extract relationship-focused sentences even without explicit names
            # This captures pronominal relationships like "his father", "her son"
            #
            # In first-person narratives, relationship phrases are often narrator-centric
            # ("my father", "my son") and can contaminate non-narrator characters.
            if not (narrative_style == "first-person" and not is_narrator):
                relationship_statements = self._extract_relationship_statements(
                    summary.summary, names, summary.chapter_index, "summary"
                )
                evidence.extend(relationship_statements)

        return evidence

    def _extract_statements_mentioning(
        self,
        text: str,
        names: list[str],
        chapter_index: int,
        source_type: str,
        chapter_summary: Optional[ChapterSummary] = None,
        is_narrator: bool = False,
        narrative_style: str = "unknown",
    ) -> list[SummaryEvidence]:
        """Extract sentences that mention any of the character names."""
        evidence = []

        # Split into sentences
        sentences = re.split(r"(?<=[.!?])\s+", text)

        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence:
                continue

            # Check if any name variant is mentioned
            for name in names:
                if self._name_in_text(name, sentence):
                    # Filter narrator-centric first-person sentences for NON-narrator characters.
                    # Example: "I repaid John's debts" primarily describes the narrator.
                    if (
                        narrative_style == "first-person"
                        and not is_narrator
                        and should_exclude_narrator_perspective_for_non_narrator(sentence, name)
                    ):
                        continue

                    # Check for surname collision before adding
                    # (e.g., sentence about "Cathy Ames" when extracting for "Ames")
                    if self._is_collision_sentence(name, sentence, names):
                        logger.debug(
                            f"Skipping collision sentence for '{name}': {sentence[:50]}..."
                        )
                        continue

                    # Check disambiguation for same-name characters
                    if self.disambiguator and self.disambiguator.is_ambiguous(name):
                        self._disambiguation_stats["checked"] += 1

                        # Get surrounding sentences for expanded context
                        # This helps detect temporal markers like "Years ago..." in prior sentences
                        start_idx = max(0, i - 2)
                        end_idx = min(len(sentences), i)  # Sentences BEFORE current
                        surrounding_context = " ".join(sentences[start_idx:end_idx]) if start_idx < end_idx else None

                        result = self.disambiguator.disambiguate(
                            name=name,
                            sentence=sentence,
                            chapter_summary=chapter_summary,
                            chapter_index=chapter_index,
                            target_character_names=names,
                            surrounding_context=surrounding_context,
                        )

                        # Check if disambiguation resolved to a different character
                        resolved_lower = result.resolved_character.lower()
                        names_lower = [n.lower() for n in names]

                        # If resolved to a character NOT in our target names, skip
                        if resolved_lower not in names_lower and not any(
                            resolved_lower in n or n in resolved_lower
                            for n in names_lower
                        ):
                            self._disambiguation_stats["skipped_different_character"] += 1
                            logger.debug(
                                f"Disambiguation: '{name}' -> '{result.resolved_character}' "
                                f"(not in {names}), skipping. Method: {result.method}"
                            )
                            continue
                        else:
                            self._disambiguation_stats["kept_same_character"] += 1
                    else:
                        self._disambiguation_stats["kept_not_ambiguous"] += 1

                    # Score based on content indicators
                    score = self._score_statement(sentence)

                    evidence.append(
                        SummaryEvidence(
                            character_name=names[0],  # Use canonical name
                            statement=sentence,
                            chapter_index=chapter_index,
                            source_type=source_type,
                            relevance_score=score,
                        )
                    )
                    break  # Only add once per sentence

        return evidence

    def _name_in_text(self, name: str, text: str) -> bool:
        """Check if a name appears in text (word boundary aware)."""
        # Handle multi-word names and single names
        pattern = r"\b" + re.escape(name) + r"\b"
        return bool(re.search(pattern, text, re.IGNORECASE))

    def _extract_relationship_statements(
        self,
        text: str,
        names: list[str],
        chapter_index: int,
        source_type: str,
    ) -> list[SummaryEvidence]:
        """
        Extract sentences with strong relationship keywords even without explicit character names.

        This captures pronominal relationships like "his father", "her son", "the nephew"
        that are critical for understanding character connections but don't use explicit names.

        Only extracts if the character is confirmed to be in this chapter
        (via characters_present check done by caller).
        """
        evidence = []

        # Strong relationship keywords that indicate family/close connections
        # These are UNIVERSAL relationship terms, not book-specific vocabulary
        relationship_keywords = [
            # Family relationships (direct)
            "father", "mother", "parent",
            "son", "daughter", "child", "children",
            "brother", "sister", "sibling",
            "husband", "wife", "spouse",
            "uncle", "aunt", "nephew", "niece",
            "cousin", "grandfather", "grandmother", "grandchild",
            # Family relationships (in-law)
            "father-in-law", "mother-in-law", "brother-in-law", "sister-in-law",
            # Close relationships
            "lover", "mistress", "friend", "companion", "partner",
            # Descriptive phrases
            "married to", "son of", "daughter of", "brother of", "sister of",
        ]

        # Split into sentences
        sentences = re.split(r"(?<=[.!?])\s+", text)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_lower = sentence.lower()

            # Check if sentence contains any strong relationship keyword
            has_relationship = any(keyword in sentence_lower for keyword in relationship_keywords)

            if has_relationship:
                # Avoid duplicates - check if we already extracted this sentence
                already_added = any(
                    ev.statement == sentence and ev.chapter_index == chapter_index
                    for ev in evidence
                )
                if already_added:
                    continue

                # Score higher since relationship info is critical
                score = 0.85  # High base score for relationship statements

                evidence.append(
                    SummaryEvidence(
                        character_name=names[0],  # Use canonical name
                        statement=sentence,
                        chapter_index=chapter_index,
                        source_type=source_type,
                        relevance_score=score,
                    )
                )

        return evidence

    def _score_statement(self, statement: str) -> float:
        """Score a statement's relevance based on content indicators."""
        score = 0.7  # Base score

        statement_lower = statement.lower()

        # Action verbs increase score
        action_indicators = [
            "kills",
            "murders",
            "attacks",
            "saves",
            "helps",
            "betrays",
            "reveals",
            "discovers",
            "confronts",
            "escapes",
            "fights",
            "poisons",
            "manipulates",
            "deceives",
            "protects",
            "threatens",
        ]
        if any(ind in statement_lower for ind in action_indicators):
            score += 0.15

        # Relationship indicators
        relationship_indicators = [
            "husband",
            "wife",
            "lover",
            "mistress",
            "friend",
            "enemy",
            "brother",
            "sister",
            "mother",
            "father",
            "daughter",
            "son",
            "marries",
            "loves",
            "hates",
            "trusts",
        ]
        if any(ind in statement_lower for ind in relationship_indicators):
            score += 0.1

        # Character trait indicators
        trait_indicators = [
            "cruel",
            "kind",
            "evil",
            "good",
            "monster",
            "hero",
            "manipulative",
            "honest",
            "deceptive",
            "brave",
            "cowardly",
        ]
        if any(ind in statement_lower for ind in trait_indicators):
            score += 0.1

        return min(score, 1.0)

    def _build_disambiguation_context(self, character_name: str, aliases: list[str]) -> str:
        """Build disambiguation context for the LLM evidence extraction prompt.

        When multiple characters share name components (e.g. father/son with same
        surname), this provides explicit guidance so the LLM attributes evidence
        to the correct character.
        """
        if not self.disambiguator:
            return ""

        # Check if any of this character's names are ambiguous
        all_names = [character_name] + (aliases or [])
        ambiguous_names = []
        other_characters = []

        for name in all_names:
            # Check if this name appears in the disambiguator's ambiguity map
            name_lower = name.lower()
            for part in name_lower.split():
                if hasattr(self.disambiguator, 'ambiguity_map'):
                    amb_map = self.disambiguator.ambiguity_map
                    if hasattr(amb_map, 'ambiguous_names') and part in getattr(amb_map, 'ambiguous_names', {}):
                        ambiguous_names.append(part)
                        candidates = getattr(amb_map, 'ambiguous_names', {}).get(part, [])
                        for c in candidates:
                            if c.lower() != character_name.lower():
                                other_characters.append(c)

        # Also check surname collisions
        for name in all_names:
            for part in name.lower().split():
                if part in self.surname_collisions:
                    for other in self.surname_collisions[part]:
                        if other.lower() != character_name.lower() and other not in other_characters:
                            other_characters.append(other)

        if not other_characters:
            return ""

        context_lines = [
            f"DISAMBIGUATION WARNING: This character shares name components with other characters.",
            f"Be careful to attribute evidence ONLY to {character_name}, NOT to:",
        ]
        for other in other_characters[:5]:
            context_lines.append(f"  - {other}")
        context_lines.append(
            f"When a shared name (e.g. a surname) appears, use surrounding context "
            f"(age, role, relationships) to determine which character is being described."
        )

        return "\n".join(context_lines) + "\n"

    def _extract_llm_based(
        self,
        character_name: str,
        aliases: list[str],
        summary_map: ChapterSummaryMap,
    ) -> Optional[dict]:
        """Use LLM for deeper evidence extraction."""
        if not self.llm:
            return None

        # Format summaries for prompt
        summaries_text = []
        for summary in summary_map.summaries:
            summaries_text.append(
                f"Chapter {summary.chapter_index} ({summary.chapter_title or 'untitled'}):\n"
                f"Summary: {summary.summary}\n"
                f"Key Events: {', '.join(summary.key_events)}\n"
                f"Characters: {', '.join(summary.characters_present)}\n"
            )

        # Build disambiguation context for same-name characters
        disambiguation_context = self._build_disambiguation_context(character_name, aliases)

        prompt = EVIDENCE_EXTRACTION_PROMPT.format(
            character_name=character_name,
            aliases=", ".join(aliases) if aliases else "None",
            disambiguation_context=disambiguation_context,
            summaries="\n".join(summaries_text),
        )

        result, response = self.llm.query_json(prompt, system=EVIDENCE_EXTRACTION_SYSTEM)

        if not response.success or result is None:
            logger.warning(f"LLM evidence extraction failed for {character_name}")
            return None

        return result

    def _is_duplicate(self, statement: str, existing: list[SummaryEvidence]) -> bool:
        """Check if a statement is a duplicate of existing evidence."""
        statement_lower = statement.lower().strip()
        for ev in existing:
            if ev.statement.lower().strip() == statement_lower:
                return True
            # Also check for high similarity (substring)
            if len(statement_lower) > 20:
                if (
                    statement_lower in ev.statement.lower()
                    or ev.statement.lower() in statement_lower
                ):
                    return True
        return False


def extract_character_summary_evidence(
    character_name: str,
    aliases: list[str],
    summary_map: ChapterSummaryMap,
    llm_client: Optional[LLMClient] = None,
    is_narrator: bool = False,
    narrative_style: str = "unknown",
    all_character_names: Optional[list[str]] = None,
    disambiguator: Optional["ContextDisambiguator"] = None,
) -> CharacterSummaryEvidence:
    """
    Convenience function to extract summary evidence for a character.

    Args:
        character_name: The character's canonical name
        aliases: Alternative names for the character
        summary_map: All chapter summaries
        llm_client: Optional LLM for enhanced extraction
        is_narrator: Whether this character is the narrator
        narrative_style: Narrative style ("first-person", "third-person", "mixed", "unknown")
        all_character_names: List of all character names for collision detection
        disambiguator: Optional ContextDisambiguator for same-name character handling

    Returns:
        CharacterSummaryEvidence with all extracted evidence
    """
    extractor = SummaryEvidenceExtractor(
        llm_client, all_character_names, disambiguator=disambiguator
    )
    return extractor.extract_evidence(
        character_name,
        aliases,
        summary_map,
        is_narrator=is_narrator,
        narrative_style=narrative_style,
    )
