"""
Summary Verification Gate (SVG) — Anti-Hallucination for Chapter Summaries

Catches common LLM hallucination patterns in chapter summary character lists:
1. Literary/historical allusions extracted as real characters (Berenice failure mode)
2. Narrator confusion from nested narratives (Frankenstein failure mode)
3. Descriptive phrases treated as character names
4. Cross-chapter consistency anomalies

Designed by local LLM fleet (qwen3-coder-next), refined and integrated by Claude.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from .models import ChapterSummary

logger = logging.getLogger(__name__)

__all__ = [
    "SummaryVerificationGate",
    "SVGResult",
    "FlaggedCharacter",
    "CharacterClassification",
    "LLM_VERIFICATION_PROMPT_TEMPLATE",
]


class CharacterClassification:
    """Classification categories for flagged characters."""
    REAL_CHARACTER = "REAL_CHARACTER"
    LITERARY_REFERENCE = "LITERARY_REFERENCE"
    NARRATOR_ARTIFACT = "NARRATOR_ARTIFACT"
    DESCRIPTION_NOT_NAME = "DESCRIPTION_NOT_NAME"
    NAME_FRAGMENT = "NAME_FRAGMENT"
    UNCERTAIN = "UNCERTAIN"


@dataclass
class FlaggedCharacter:
    """A character flagged by the verification gate."""
    name: str
    reason: str
    source: str  # "regex" or "cross_chapter"
    chapter_indices: list[int] = field(default_factory=list)
    suggested_classification: str = ""


@dataclass
class SVGResult:
    """Result from the Summary Verification Gate."""
    flagged_characters: list[FlaggedCharacter] = field(default_factory=list)
    llm_prompt: str = ""

    @property
    def has_flags(self) -> bool:
        return len(self.flagged_characters) > 0


# Compiled regex patterns for detecting hallucination artifacts

_HONORIFIC_ONLY = re.compile(
    r'^(?:Monsieur|Madame|Mademoiselle|Mad\'selle|Miss|Mrs\.?|Mr\.?|Ms\.?|Dr\.?|'
    r'Sir|Lady|Lord|Dame|The\s+(?:Doctor|Professor|Captain|General|Colonel|Major|'
    r'Reverend|Father|Mother|Sister|Brother))$',
    re.IGNORECASE,
)

_DESCRIPTIVE_PHRASE = re.compile(
    r'^(?:an?|the)\s+'
    r'(?:old|young|tall|short|pale|dark|rich|poor|wise|foolish|mad|gentle|noble|'
    r'mysterious|strange|beautiful|ugly|blind|deaf|dying|dead|wounded|sick|unnamed|'
    r'unknown|ancient|former|foreign)\s+'
    r'(?:man|woman|boy|girl|child|person|figure|stranger|servant|master|lord|lady|'
    r'priest|monk|nun|soldier|sailor|doctor|beggar|merchant|king|queen|prince|'
    r'princess|knight|peasant|noble|citizen|traveler|pilgrim|narrator)$',
    re.IGNORECASE,
)

_LITERARY_HISTORICAL = re.compile(
    r'(?:the\s+(?:poet|philosopher|dancer|historian|scientist|writer|author|composer|'
    r'painter|artist|playwright|orator|statesman|emperor|general))|'
    r'(?:\b\d{4}\s*[-\u2013\u2014]\s*\d{4}\b)|'
    r'(?:\bca?\.?\s*\d{4}\b)|'
    r'(?:\b\d+(?:st|nd|rd|th)\s+century\b)',
    re.IGNORECASE,
)

_NARRATOR_ARTIFACT = re.compile(
    r'^(?:The\s+Narrator|Narrator|The\s+Speaker|Speaker|The\s+Author|'
    r'First[\s-]Person\s+Narrator|I)$',
    re.IGNORECASE,
)

_GENERIC_ROLE = re.compile(
    r'^(?:The\s+)?(?:Protagonist|Antagonist|Hero|Heroine|Villain|'
    r'Main\s+Character|Love\s+Interest|Sidekick|Mentor|Guide)$',
    re.IGNORECASE,
)

# Group descriptors: "The sailors", "the people of the inn", "the townspeople"
_GROUP_DESCRIPTOR = re.compile(
    r'^(?:The|A\s+group\s+of|Some|Several|Many|Various)\s+'
    r'(?:sailors|soldiers|servants|guards|townspeople|villagers|people|'
    r'citizens|monks|nuns|priests|students|workers|passengers|crew|'
    r'children|men|women|guests|crowd|mob|audience|family|relatives)',
    re.IGNORECASE,
)


LLM_VERIFICATION_PROMPT_TEMPLATE = """You are an expert literary analyst verifying character extraction from book chapter summaries.

## Book Context
{chapter_contexts}

## Characters to Verify

Analyze each character name below. Classify as one of:
- REAL_CHARACTER: A genuine character who participates in story events
- LITERARY_REFERENCE: A literary/historical figure mentioned for context, not a story participant
- NARRATOR_ARTIFACT: A narrative device ("The Narrator", "I") that shouldn't be a character entry
- DESCRIPTION_NOT_NAME: A descriptive phrase incorrectly used as a character name
- UNCERTAIN: Insufficient context to determine

## Characters
{character_list}

For each, respond in this exact format (one per line):
CHARACTER_NAME: CLASSIFICATION - Brief explanation"""


class SummaryVerificationGate:
    """
    Verification gate for chapter summary character lists.

    Catches common LLM hallucination patterns through regex pre-filters
    and cross-chapter consistency analysis. Optionally generates an LLM
    prompt for ambiguous cases.
    """

    def __init__(
        self,
        low_confidence_threshold: float = 0.7,
        mention_threshold: int = 2,
    ):
        self.low_confidence_threshold = low_confidence_threshold
        self.mention_threshold = mention_threshold

    def verify(
        self,
        summaries: list[ChapterSummary],
        full_character_list: Optional[list[str]] = None,
    ) -> SVGResult:
        """
        Run all verification checks on chapter summaries.

        Returns SVGResult with flagged characters and optional LLM prompt.
        """
        flagged = []

        for summary in summaries:
            flagged.extend(self._regex_pre_filter(summary))

        flagged.extend(self._cross_chapter_checks(summaries))

        llm_prompt = ""
        if flagged:
            unique_names = list({f.name for f in flagged})
            llm_prompt = self._build_llm_prompt(summaries, unique_names)

        logger.info(
            f"SVG: {len(flagged)} characters flagged "
            f"({sum(1 for f in flagged if f.source == 'regex')} regex, "
            f"{sum(1 for f in flagged if f.source == 'cross_chapter')} cross-chapter)"
        )

        return SVGResult(flagged_characters=flagged, llm_prompt=llm_prompt)

    def _regex_pre_filter(self, summary: ChapterSummary) -> list[FlaggedCharacter]:
        """Apply regex filters to a single chapter's character lists."""
        flags = []
        chapter_idx = summary.chapter_index

        for char_name in summary.active_characters + summary.mentioned_characters:
            stripped = char_name.strip()
            if not stripped:
                continue

            if _HONORIFIC_ONLY.match(stripped):
                flags.append(FlaggedCharacter(
                    name=stripped,
                    reason="Honorific-only name with no actual character name",
                    source="regex",
                    chapter_indices=[chapter_idx],
                    suggested_classification=CharacterClassification.DESCRIPTION_NOT_NAME,
                ))
                continue

            if _DESCRIPTIVE_PHRASE.match(stripped):
                flags.append(FlaggedCharacter(
                    name=stripped,
                    reason="Descriptive phrase used as character name",
                    source="regex",
                    chapter_indices=[chapter_idx],
                    suggested_classification=CharacterClassification.DESCRIPTION_NOT_NAME,
                ))
                continue

            if _LITERARY_HISTORICAL.search(stripped):
                flags.append(FlaggedCharacter(
                    name=stripped,
                    reason="Contains literary/historical figure markers",
                    source="regex",
                    chapter_indices=[chapter_idx],
                    suggested_classification=CharacterClassification.LITERARY_REFERENCE,
                ))
                continue

            if summary.pov_character and _NARRATOR_ARTIFACT.match(stripped):
                flags.append(FlaggedCharacter(
                    name=stripped,
                    reason=f"Narrator artifact — POV character '{summary.pov_character}' already identified",
                    source="regex",
                    chapter_indices=[chapter_idx],
                    suggested_classification=CharacterClassification.NARRATOR_ARTIFACT,
                ))
                continue

            if _GENERIC_ROLE.match(stripped):
                flags.append(FlaggedCharacter(
                    name=stripped,
                    reason="Generic role description, not a specific character name",
                    source="regex",
                    chapter_indices=[chapter_idx],
                    suggested_classification=CharacterClassification.DESCRIPTION_NOT_NAME,
                ))
                continue

            # Check group descriptors
            if _GROUP_DESCRIPTOR.match(stripped):
                flags.append(FlaggedCharacter(
                    name=stripped,
                    reason="Group descriptor, not an individual character",
                    source="regex",
                    chapter_indices=[chapter_idx],
                    suggested_classification=CharacterClassification.DESCRIPTION_NOT_NAME,
                ))
                continue

        return flags

    def _cross_chapter_checks(self, summaries: list[ChapterSummary]) -> list[FlaggedCharacter]:
        """Analyze character patterns across all chapters."""
        flags = []

        active_chapters: dict[str, set[int]] = {}
        mention_chapters: dict[str, set[int]] = {}
        all_chars: set[str] = set()

        for summary in summaries:
            for char in summary.active_characters:
                active_chapters.setdefault(char, set()).add(summary.chapter_index)
                all_chars.add(char)
            for char in summary.mentioned_characters:
                mention_chapters.setdefault(char, set()).add(summary.chapter_index)
                all_chars.add(char)

        confidence_by_chapter = {s.chapter_index: s.confidence for s in summaries}

        # Single-appearance characters in low-confidence chapters
        for char, chapters in active_chapters.items():
            if len(chapters) == 1:
                ch_idx = next(iter(chapters))
                conf = confidence_by_chapter.get(ch_idx, 1.0)
                if conf < self.low_confidence_threshold:
                    flags.append(FlaggedCharacter(
                        name=char,
                        reason=f"Appears in only 1 chapter (ch.{ch_idx}) with low confidence ({conf:.2f})",
                        source="cross_chapter",
                        chapter_indices=[ch_idx],
                        suggested_classification=CharacterClassification.UNCERTAIN,
                    ))

        # Name substring fragmentation
        char_list = sorted(all_chars)
        seen_pairs: set[tuple[str, str]] = set()
        for i, char1 in enumerate(char_list):
            for j, char2 in enumerate(char_list):
                if i == j:
                    continue
                if len(char1) < len(char2) and char1.lower() in char2.lower():
                    pair_key = (min(char1, char2), max(char1, char2))
                    if pair_key not in seen_pairs:
                        seen_pairs.add(pair_key)
                        flags.append(FlaggedCharacter(
                            name=char1,
                            reason=f"Name '{char1}' is a substring of '{char2}' — possible name fragmentation",
                            source="cross_chapter",
                            chapter_indices=sorted(
                                active_chapters.get(char1, set()) | mention_chapters.get(char1, set())
                            ),
                            suggested_classification=CharacterClassification.NAME_FRAGMENT,
                        ))

        # Frequently mentioned but never active
        for char in mention_chapters:
            mention_count = len(mention_chapters[char])
            active_count = len(active_chapters.get(char, set()))
            if mention_count >= self.mention_threshold and active_count == 0:
                flags.append(FlaggedCharacter(
                    name=char,
                    reason=f"Mentioned in {mention_count} chapters but never active — possible literary/historical reference",
                    source="cross_chapter",
                    chapter_indices=sorted(mention_chapters[char]),
                    suggested_classification=CharacterClassification.LITERARY_REFERENCE,
                ))

        return flags

    def _build_llm_prompt(self, summaries: list[ChapterSummary], suspicious_names: list[str]) -> str:
        """Build an LLM verification prompt for suspicious characters."""
        chapter_contexts = []
        for s in summaries:
            title = f" '{s.chapter_title}'" if s.chapter_title else ""
            excerpt = s.summary[:300].replace("\n", " ")
            chars = ", ".join(s.active_characters[:5])
            chapter_contexts.append(
                f"Chapter {s.chapter_index}{title}: {excerpt}...\n"
                f"  Active characters: {chars}"
            )

        return LLM_VERIFICATION_PROMPT_TEMPLATE.format(
            chapter_contexts="\n\n".join(chapter_contexts),
            character_list="\n".join(f"- {name}" for name in suspicious_names),
        )
