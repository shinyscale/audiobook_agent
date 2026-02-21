"""
Moral valence classification for characters (Feature F2).

Provides action-focused moral classification before profile generation,
ensuring moral assessment is based on deeds not descriptions.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum

from ..llm import LLMClient

logger = logging.getLogger(__name__)


class MoralValence(str, Enum):
    """Moral classification based on character actions."""

    PROTAGONIST = "protagonist"  # Primarily beneficial actions
    ANTAGONIST = "antagonist"  # Primarily harmful actions
    MORALLY_AMBIGUOUS = "morally_ambiguous"  # Significant harmful AND beneficial
    NEUTRAL = "neutral"  # Primarily neutral actions
    VICTIM = "victim"  # Primarily recipient of harmful actions
    UNCERTAIN = "uncertain"  # Insufficient evidence


# Constraints for profile generation based on moral valence.
# These are HARD CONSTRAINTS that the profile generator must respect.
MORAL_VALENCE_CONSTRAINTS: dict[MoralValence, str] = {
    MoralValence.PROTAGONIST: (
        "This character performs primarily BENEFICIAL actions. "
        "Profile should reflect their positive qualities while noting any flaws. "
        "Avoid overly negative characterization that contradicts their helpful actions."
    ),
    MoralValence.ANTAGONIST: (
        "This character performs primarily harmful actions. "
        "Acknowledge clearly evidenced harmful behaviors, but remain balanced and avoid attributing "
        "negative motives without direct textual support. Describe from a narrator's practical perspective."
    ),
    MoralValence.MORALLY_AMBIGUOUS: (
        "This character performs BOTH significant harmful AND beneficial actions. "
        "Profile should present a balanced view acknowledging both aspects. "
        "Avoid simplifying them as purely good or purely evil."
    ),
    MoralValence.NEUTRAL: (
        "This character primarily performs neutral actions (daily life, observation, work). "
        "Profile should focus on their role in the narrative without moral judgment."
    ),
    MoralValence.VICTIM: (
        "This character is primarily a RECIPIENT of harmful actions from others. "
        "Profile should acknowledge their suffering and any resilience or growth shown."
    ),
    MoralValence.UNCERTAIN: (
        "Insufficient evidence to classify this character's moral role. "
        "Profile should be factual and avoid making moral judgments."
    ),
}


@dataclass
class MoralValenceResult:
    """Result of moral valence classification."""

    character_name: str
    valence: MoralValence
    confidence: float
    key_actions: list[dict] = field(
        default_factory=list
    )  # [{action, category, victim/beneficiary}]
    evidence_quotes: list[str] = field(default_factory=list)
    reasoning: str = ""

    def to_dict(self) -> dict:
        return {
            "character_name": self.character_name,
            "valence": self.valence.value,
            "confidence": self.confidence,
            "key_actions": self.key_actions,
            "evidence_quotes": self.evidence_quotes,
            "reasoning": self.reasoning,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MoralValenceResult":
        return cls(
            character_name=data["character_name"],
            valence=MoralValence(data.get("valence", "uncertain")),
            confidence=data.get("confidence", 0.5),
            key_actions=data.get("key_actions", []),
            evidence_quotes=data.get("evidence_quotes", []),
            reasoning=data.get("reasoning", ""),
        )


MORAL_VALENCE_SYSTEM = """You are a literary analyst classifying characters by MORAL ROLE based on ACTIONS.

CRITICAL: Base classification ENTIRELY on what characters DO, not how they are described.
Physical appearance and descriptions are IRRELEVANT to moral classification.

ACTION CATEGORIES:
- HARMFUL: murder, assault, manipulation, deception, cruelty, abuse, betrayal, theft, exploitation
- BENEFICIAL: helping others, sacrifice, protection, honesty, kindness, healing, generosity
- NEUTRAL: daily activities, travel, work, observation, conversation

CLASSIFICATION RULES:
1. Primarily HARMFUL actions -> ANTAGONIST
2. Primarily BENEFICIAL actions -> PROTAGONIST
3. Both significant HARMFUL and BENEFICIAL actions -> MORALLY_AMBIGUOUS
4. Primarily NEUTRAL actions or few actions -> NEUTRAL
5. Primarily receives harm from others -> VICTIM
6. Insufficient information -> UNCERTAIN

IMPORTANT:
- A beautiful character can be a monster (ANTAGONIST)
- A physically ugly character can be heroic (PROTAGONIST)
- "Charming" descriptions do NOT make someone good
- Backstory explains but does NOT excuse harmful actions

Always respond with valid JSON. No other text."""


MORAL_VALENCE_PROMPT = """Classify this character's MORAL ROLE based on their ACTIONS.

CHARACTER: {name}
ROLE IN STORY: {role}

TEXT PASSAGES ABOUT THIS CHARACTER:
{passages}

Analyze the character's actions and classify their moral role.

Return JSON in this exact format:
```json
{{
  "valence": "protagonist/antagonist/morally_ambiguous/neutral/victim/uncertain",
  "confidence": 0.0-1.0,
  "key_actions": [
    {{"action": "specific action", "category": "harmful/beneficial/neutral", "target": "who was affected"}}
  ],
  "evidence_quotes": ["direct quote from text"],
  "reasoning": "Explanation of why this classification was chosen based on actions"
}}
```

CRITICAL RULES:
- List SPECIFIC ACTIONS the character takes (not descriptions of them)
- Ignore physical appearance and charm - focus only on DEEDS
- If a character commits murder, manipulation, or cruelty, they are likely ANTAGONIST
- If a character helps, protects, or sacrifices, they are likely PROTAGONIST
- If both, they are MORALLY_AMBIGUOUS

Return ONLY valid JSON. No other text."""


class MoralValenceClassifier:
    """Classifies characters by moral role based on their actions."""

    def __init__(self, llm_client: LLMClient):
        """
        Args:
            llm_client: LLM client for classification
        """
        self.llm = llm_client

    def classify_character(
        self,
        character_name: str,
        role: str,
        passages: list[str],
    ) -> MoralValenceResult:
        """
        Classify a character's moral role based on text passages.

        Args:
            character_name: Name of the character
            role: Character's role (protagonist, antagonist, supporting, minor)
            passages: Text passages mentioning this character

        Returns:
            MoralValenceResult with classification
        """
        if not passages:
            logger.warning(f"No passages provided for {character_name}, returning UNCERTAIN")
            return MoralValenceResult(
                character_name=character_name,
                valence=MoralValence.UNCERTAIN,
                confidence=0.0,
                reasoning="No text passages available for classification",
            )

        # Format passages for prompt
        passages_text = "\n\n".join(
            f"[Passage {i+1}]\n{p}" for i, p in enumerate(passages[:10])  # Limit to 10 passages
        )

        prompt = MORAL_VALENCE_PROMPT.format(
            name=character_name,
            role=role,
            passages=passages_text,
        )

        result, response = self.llm.query_json(prompt, system=MORAL_VALENCE_SYSTEM)

        if not response.success or result is None:
            logger.warning(
                f"Moral valence classification failed for {character_name}: {response.error}"
            )
            return MoralValenceResult(
                character_name=character_name,
                valence=MoralValence.UNCERTAIN,
                confidence=0.0,
                reasoning=f"Classification failed: {response.error}",
            )

        # Parse result
        try:
            valence_str = result.get("valence", "uncertain").lower()
            valence = MoralValence(valence_str)
        except ValueError:
            valence = MoralValence.UNCERTAIN

        # F14: Warn when confidence is missing from LLM response
        confidence_raw = result.get("confidence")
        if confidence_raw is None:
            logger.warning(
                f"Moral valence classification for '{character_name}' did not return confidence - "
                "using default 0.5"
            )
            confidence = 0.5
        else:
            confidence = float(confidence_raw)

        return MoralValenceResult(
            character_name=character_name,
            valence=valence,
            confidence=confidence,
            key_actions=result.get("key_actions", []),
            evidence_quotes=result.get("evidence_quotes", []),
            reasoning=result.get("reasoning", ""),
        )

    def classify_characters(
        self,
        characters: list[dict],
        passages_by_character: dict[str, list[str]],
    ) -> dict[str, MoralValenceResult]:
        """
        Classify multiple characters.

        Args:
            characters: List of character dicts with 'canonical_name' and 'role'
            passages_by_character: Dict mapping character names to their passages

        Returns:
            Dict mapping character names to MoralValenceResult
        """
        results = {}
        for char in characters:
            name = char.get("canonical_name", char.get("name", "Unknown"))
            role = char.get("role", "supporting")
            passages = passages_by_character.get(name, [])

            logger.info(f"Classifying moral valence for {name}")
            results[name] = self.classify_character(name, role, passages)

        return results
