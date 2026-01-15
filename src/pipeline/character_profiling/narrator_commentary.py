"""
Narrator commentary detection (Feature F4).

Detects narrator commentary patterns that provide explicit judgments about
characters, which can inform profile generation.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from ..llm import LLMClient


logger = logging.getLogger(__name__)


# Pre-filter regex patterns for potential narrator commentary
# These patterns identify sentences that MAY contain authorial voice
NARRATOR_PATTERNS = [
    # Direct authorial asides
    r'\bI believe\b',
    r'\bthe reader\b',
    r'\bone must\b',
    r'\bin truth\b',
    r'\bit must be said\b',
    r'\bit should be said\b',
    r'\blet it be said\b',
    # Judgment patterns
    r'\bthere are .* born\b',
    r'\bthere was .* about\b',
    r'\bsuch .* are\b',
    r'\bsuch .* was\b',
    # Foreshadowing patterns
    r'\blittle did .* know\b',
    r'\bwhat .* did not know\b',
    r'\bif .* had known\b',
    r'\bas we shall see\b',
    r'\bas .* would discover\b',
    # Omniscient observations
    r'\bin all .* life\b',
    r'\bno one knew\b',
    r'\bno one could\b',
    r'\bnever .* had\b',
    r'\bperhaps .* was\b',
    # Direct characterization
    r'\bwas the sort of\b',
    r'\bwas not the kind\b',
    r'\bhad always been\b',
    r'\bwould always be\b',
]

# Compile patterns for efficiency
COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in NARRATOR_PATTERNS]


@dataclass
class NarratorComment:
    """A narrator commentary about a character."""
    quote: str
    character_name: str
    chapter_index: int
    position: int  # Character position in text
    comment_type: str  # 'judgment', 'aside', 'foreshadowing', 'observation'
    sentiment: str  # 'positive', 'negative', 'neutral', 'ambiguous'

    def to_dict(self) -> dict:
        return {
            "quote": self.quote,
            "character_name": self.character_name,
            "chapter_index": self.chapter_index,
            "position": self.position,
            "comment_type": self.comment_type,
            "sentiment": self.sentiment,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NarratorComment":
        return cls(
            quote=data["quote"],
            character_name=data.get("character_name", ""),
            chapter_index=data.get("chapter_index", 0),
            position=data.get("position", 0),
            comment_type=data.get("comment_type", "observation"),
            sentiment=data.get("sentiment", "neutral"),
        )


@dataclass
class NarratorCommentaryResult:
    """Result of narrator commentary detection."""
    comments: list[NarratorComment] = field(default_factory=list)
    has_significant_commentary: bool = False
    narrative_voice_notes: str = ""
    comments_by_character: dict[str, list[NarratorComment]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "comments": [c.to_dict() for c in self.comments],
            "has_significant_commentary": self.has_significant_commentary,
            "narrative_voice_notes": self.narrative_voice_notes,
            "comments_by_character": {
                name: [c.to_dict() for c in comments]
                for name, comments in self.comments_by_character.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NarratorCommentaryResult":
        comments = [NarratorComment.from_dict(c) for c in data.get("comments", [])]
        return cls(
            comments=comments,
            has_significant_commentary=data.get("has_significant_commentary", False),
            narrative_voice_notes=data.get("narrative_voice_notes", ""),
            comments_by_character={
                name: [NarratorComment.from_dict(c) for c in cmts]
                for name, cmts in data.get("comments_by_character", {}).items()
            },
        )


NARRATOR_COMMENTARY_SYSTEM = """You are a literary analyst identifying NARRATOR COMMENTARY in fiction.

Narrator commentary is when the narrator steps back from the story to:
- Make a judgment about a character ("She was evil incarnate")
- Provide an authorial aside to the reader
- Foreshadow events ("Little did he know...")
- Give omniscient observations about a character's nature

IMPORTANT: Only flag EXPLICIT narrator commentary, not:
- Simple narration ("She walked to the door")
- Character descriptions ("She had blue eyes")
- Action descriptions ("He picked up the gun")

Look for the narrator's VOICE commenting on characters, not just describing events.

Always respond with valid JSON. No other text."""


NARRATOR_COMMENTARY_PROMPT = """Analyze these potential narrator commentary passages.

For each passage, determine:
1. Is this NARRATOR COMMENTARY (authorial voice commenting on character) or just NARRATION?
2. Which character is being discussed?
3. What type of comment is it? (judgment, aside, foreshadowing, observation)
4. What is the sentiment? (positive, negative, neutral, ambiguous)

PASSAGES TO ANALYZE:
{passages}

CHARACTER NAMES IN THE BOOK:
{character_names}

Return JSON in this exact format:
```json
{{
  "commentary": [
    {{
      "passage_index": 0,
      "is_commentary": true,
      "character_name": "Character Name",
      "comment_type": "judgment/aside/foreshadowing/observation",
      "sentiment": "positive/negative/neutral/ambiguous",
      "reasoning": "Why this is narrator commentary"
    }}
  ]
}}
```

Rules:
- Only mark as is_commentary=true if the narrator is EXPLICITLY commenting
- Simple descriptions ("She was tall") are NOT commentary
- Look for narrator's opinions, not just facts
- Match character_name to the provided list when possible

Return ONLY valid JSON. No other text."""


class NarratorCommentaryDetector:
    """Detects narrator commentary about characters in text."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Args:
            llm_client: Optional LLM client for commentary classification
        """
        self.llm = llm_client

    def detect(
        self,
        text: str,
        character_names: list[str],
        chapter_boundaries: Optional[list[tuple[int, int]]] = None,
    ) -> NarratorCommentaryResult:
        """
        Detect narrator commentary in text.

        Args:
            text: Full document text
            character_names: List of character names to look for
            chapter_boundaries: Optional list of (start, end) positions for chapters

        Returns:
            NarratorCommentaryResult with detected comments
        """
        # Step 1: Pre-filter with regex patterns
        candidates = self._find_candidates(text, chapter_boundaries)

        if not candidates:
            return NarratorCommentaryResult(
                has_significant_commentary=False,
                narrative_voice_notes="No narrator commentary patterns detected",
            )

        # Step 2: If we have an LLM, classify the candidates
        if self.llm:
            comments = self._classify_with_llm(candidates, character_names)
        else:
            # Fallback: use simple pattern-based classification
            comments = self._classify_simple(candidates, character_names)

        # Build result
        comments_by_character: dict[str, list[NarratorComment]] = {}
        for comment in comments:
            if comment.character_name:
                if comment.character_name not in comments_by_character:
                    comments_by_character[comment.character_name] = []
                comments_by_character[comment.character_name].append(comment)

        has_significant = len(comments) >= 3 or any(
            c.comment_type == "judgment" for c in comments
        )

        voice_notes = self._generate_voice_notes(comments)

        return NarratorCommentaryResult(
            comments=comments,
            has_significant_commentary=has_significant,
            narrative_voice_notes=voice_notes,
            comments_by_character=comments_by_character,
        )

    def _find_candidates(
        self,
        text: str,
        chapter_boundaries: Optional[list[tuple[int, int]]] = None,
    ) -> list[dict]:
        """Find candidate passages using regex patterns."""
        candidates = []
        seen_positions = set()

        for pattern in COMPILED_PATTERNS:
            for match in pattern.finditer(text):
                pos = match.start()

                # Skip if we've already found a candidate nearby
                if any(abs(pos - p) < 100 for p in seen_positions):
                    continue
                seen_positions.add(pos)

                # Extract surrounding context (sentence/paragraph)
                start = max(0, text.rfind('.', max(0, pos - 200), pos) + 1)
                end = text.find('.', pos, pos + 300)
                if end == -1:
                    end = min(len(text), pos + 300)
                else:
                    end += 1

                passage = text[start:end].strip()

                # Determine chapter index
                chapter_idx = 0
                if chapter_boundaries:
                    for idx, (ch_start, ch_end) in enumerate(chapter_boundaries):
                        if ch_start <= pos <= ch_end:
                            chapter_idx = idx + 1
                            break

                candidates.append({
                    "text": passage,
                    "position": pos,
                    "chapter_index": chapter_idx,
                    "pattern": pattern.pattern,
                })

        return candidates[:20]  # Limit to 20 candidates

    def _classify_with_llm(
        self,
        candidates: list[dict],
        character_names: list[str],
    ) -> list[NarratorComment]:
        """Classify candidates using LLM."""
        passages_text = "\n\n".join(
            f"[Passage {i}]\n{c['text']}" for i, c in enumerate(candidates)
        )
        names_text = ", ".join(character_names[:20])  # Limit names

        prompt = NARRATOR_COMMENTARY_PROMPT.format(
            passages=passages_text,
            character_names=names_text,
        )

        result, response = self.llm.query_json(prompt, system=NARRATOR_COMMENTARY_SYSTEM)

        if not response.success or result is None:
            logger.warning(f"LLM commentary classification failed: {response.error}")
            return self._classify_simple(candidates, character_names)

        comments = []
        for item in result.get("commentary", []):
            if not item.get("is_commentary", False):
                continue

            idx = item.get("passage_index", 0)
            if idx >= len(candidates):
                continue

            candidate = candidates[idx]
            comments.append(NarratorComment(
                quote=candidate["text"],
                character_name=item.get("character_name", ""),
                chapter_index=candidate["chapter_index"],
                position=candidate["position"],
                comment_type=item.get("comment_type", "observation"),
                sentiment=item.get("sentiment", "neutral"),
            ))

        return comments

    def _classify_simple(
        self,
        candidates: list[dict],
        character_names: list[str],
    ) -> list[NarratorComment]:
        """Simple pattern-based classification without LLM."""
        comments = []

        for candidate in candidates:
            text = candidate["text"].lower()

            # Determine comment type based on pattern
            if "believe" in text or "must be said" in text or "in truth" in text:
                comment_type = "judgment"
            elif "little did" in text or "would discover" in text or "did not know" in text:
                comment_type = "foreshadowing"
            elif "reader" in text:
                comment_type = "aside"
            else:
                comment_type = "observation"

            # Find associated character
            associated_char = ""
            for name in character_names:
                if name.lower() in candidate["text"].lower():
                    associated_char = name
                    break

            # Simple sentiment detection
            negative_words = ["evil", "monster", "cruel", "terrible", "wicked", "dark", "sinister"]
            positive_words = ["good", "kind", "noble", "gentle", "warm", "loving", "brave"]
            sentiment = "neutral"
            for word in negative_words:
                if word in text:
                    sentiment = "negative"
                    break
            for word in positive_words:
                if word in text:
                    sentiment = "positive"
                    break

            comments.append(NarratorComment(
                quote=candidate["text"],
                character_name=associated_char,
                chapter_index=candidate["chapter_index"],
                position=candidate["position"],
                comment_type=comment_type,
                sentiment=sentiment,
            ))

        return comments

    def _generate_voice_notes(self, comments: list[NarratorComment]) -> str:
        """Generate narrative voice notes from detected comments."""
        if not comments:
            return "No significant narrator commentary detected"

        judgment_count = sum(1 for c in comments if c.comment_type == "judgment")
        foreshadowing_count = sum(1 for c in comments if c.comment_type == "foreshadowing")
        aside_count = sum(1 for c in comments if c.comment_type == "aside")

        notes = []
        if judgment_count > 0:
            notes.append(f"Strong authorial judgments ({judgment_count} instances)")
        if foreshadowing_count > 0:
            notes.append(f"Narrative foreshadowing ({foreshadowing_count} instances)")
        if aside_count > 0:
            notes.append(f"Direct reader asides ({aside_count} instances)")

        if notes:
            return "Narrative voice characteristics: " + "; ".join(notes)
        return f"Moderate narrator commentary ({len(comments)} observations)"
