"""
Character proposal validator.

Validates character proposals and identifies potential aliases.
"""

import re
import time
from typing import Optional
import logging

from .models import CharacterProposal, CharacterValidationResult
from .constants import NICKNAME_MAP
from ..llm import LLMClient

logger = logging.getLogger(__name__)


# Known non-person entities that might be detected as characters
PLACE_NAMES = {
    'london', 'paris', 'new york', 'england', 'america', 'france', 'germany',
    'broadway', 'manhattan',
}

# Common food/beverage names that NER might misidentify as characters
FOOD_BEVERAGE_NAMES = {
    'amontillado', 'sherry', 'wine', 'champagne', 'brandy', 'whiskey', 'bourbon',
    'tea', 'coffee', 'water', 'milk', 'beer', 'ale', 'porter', 'rum', 'gin',
    'bread', 'cheese', 'meat', 'fish', 'cake', 'pie', 'soup', 'stew',
}

TITLE_ONLY_PATTERN = re.compile(
    r'^(mr|mrs|ms|miss|dr|sir|lady|lord|captain|colonel|general|'
    r'professor|doctor|king|queen|prince|princess|duke|duchess)\.?$',
    re.IGNORECASE
)

# Words that indicate character context
CHARACTER_VERBS = {
    'said', 'asked', 'replied', 'whispered', 'shouted', 'muttered',
    'thought', 'wondered', 'felt', 'looked', 'smiled', 'laughed',
    'walked', 'ran', 'stood', 'sat', 'turned', 'nodded',
}


VALIDATION_SYSTEM_PROMPT = """You are a literary analyst validating character names.

Your task is to determine if a proposed name refers to a real character (person) in the story,
and identify other names that might refer to the same person.

Consider:
- Is this a person's name (not a place, title alone, object, food/drink, or abstract concept)?
- Does the context suggest this is a character who acts, speaks, or is spoken about?
- What other names/titles might refer to the same person?

CRITICAL: Reject names that refer to:
- Objects, items, or things (e.g., wine, books, weapons, artifacts)
- Food or beverages
- Places or locations
- Abstract concepts or ideas
- Titles without names"""


VALIDATION_PROMPT_TEMPLATE = """Validate this character proposal from a novel:

PROPOSED NAME: {name}
STRATEGY: {strategy}
MENTION COUNT: {mention_count}

SAMPLE CONTEXTS (where this name appears):
{contexts}

Analyze the contexts carefully. Ask yourself:
1. Is "{name}" a PERSON's name, or is it an object/item/place/concept?
2. If people are talking ABOUT "{name}" (e.g., "the Amontillado", "some Amontillado"), is it something they're discussing rather than someone they're addressing?
3. Do the contexts show "{name}" performing human actions (speaking, thinking, moving) or being acted upon as an object?

Please return JSON with:
- "is_person": true/false - Is this a real person/character name (NOT an object, food, drink, place, or concept)?
- "is_person_reasoning": Brief explanation of why this is or isn't a person
- "context_supports": 0.0-1.0 - How strongly does the context support this being a character?
- "alias_candidates": List of other names that might refer to the same person (e.g., "Elizabeth" -> ["Lizzy", "Miss Bennet"])
- "overall_valid": true/false - Should we include this as a character?

Return ONLY valid JSON."""


class CharacterValidator:
    """
    Validates character proposals using heuristics and LLM.

    Uses fast heuristics for clear cases, LLM for ambiguous ones.
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        min_confidence: float = 0.5,
        use_llm_validation: bool = True,
    ):
        """
        Args:
            llm_client: LLM client for ambiguous cases
            min_confidence: Minimum score to consider valid
            use_llm_validation: Whether to use LLM for validation
        """
        self.llm = llm_client
        self.min_confidence = min_confidence
        self.use_llm_validation = use_llm_validation and llm_client is not None

    def validate(self, proposal: CharacterProposal) -> CharacterValidationResult:
        """Validate a single character proposal."""
        # Quick heuristic checks
        heuristic_result = self._heuristic_validation(proposal)

        if heuristic_result is not None:
            return heuristic_result

        # Use LLM for ambiguous cases
        if self.use_llm_validation:
            return self._llm_validation(proposal)

        # No LLM validation available - fail fast instead of using fallback confidence
        error_msg = f"LLM validation is required but not enabled for proposal '{proposal.name}'"
        logger.error(error_msg)
        raise ValueError(error_msg)

    def validate_batch(
        self,
        proposals: list[CharacterProposal],
    ) -> list[CharacterValidationResult]:
        """Validate multiple proposals."""
        return [self.validate(p) for p in proposals]

    def _heuristic_validation(
        self,
        proposal: CharacterProposal,
    ) -> Optional[CharacterValidationResult]:
        """
        Apply fast heuristic checks.

        Returns ValidationResult if we can determine validity,
        None if LLM validation is needed.
        """
        name = proposal.name
        name_lower = name.lower()

        # Reject: known places
        if name_lower in PLACE_NAMES:
            return CharacterValidationResult(
                proposal=proposal,
                is_person_score=0.0,
                context_score=0.0,
                alias_candidates=[],
                overall_score=0.0,
                is_valid=False,
                reasoning=f"'{name}' is a known place name",
            )

        # Reject: known food/beverage names
        if name_lower in FOOD_BEVERAGE_NAMES:
            return CharacterValidationResult(
                proposal=proposal,
                is_person_score=0.0,
                context_score=0.0,
                alias_candidates=[],
                overall_score=0.0,
                is_valid=False,
                reasoning=f"'{name}' is a food or beverage, not a character",
            )

        # Check for plural family names (e.g., "the Montresors" referring to the family)
        # These appear in contexts like "the Xs" or "of the Xs" where X is a surname
        if self._is_plural_family_reference(name, proposal.mentions):
            return CharacterValidationResult(
                proposal=proposal,
                is_person_score=0.0,
                context_score=0.0,
                alias_candidates=[],
                overall_score=0.0,
                is_valid=False,
                reasoning=f"'{name}' appears to be a plural family reference, not an individual",
            )

        # Reject: title only (no actual name)
        if TITLE_ONLY_PATTERN.match(name):
            return CharacterValidationResult(
                proposal=proposal,
                is_person_score=0.0,
                context_score=0.0,
                alias_candidates=[],
                overall_score=0.0,
                is_valid=False,
                reasoning=f"'{name}' is a title without a name",
            )

        # Removed overly aggressive heuristic - high mention count alone doesn't guarantee character
        # Objects, food, drinks can also be mentioned frequently in dialogue
        # Let LLM validation handle these ambiguous cases

        dialogue_mentions = sum(1 for m in proposal.mentions if m.in_dialogue)

        # Accept: appears in dialogue tags (said X, asked X)
        dialogue_tag_count = self._count_dialogue_tags(proposal)
        if dialogue_tag_count >= 2:
            alias_candidates = self._find_obvious_aliases(proposal)
            return CharacterValidationResult(
                proposal=proposal,
                is_person_score=0.9,
                context_score=0.85,
                alias_candidates=alias_candidates,
                overall_score=0.87,
                is_valid=True,
                reasoning=f"Appears in {dialogue_tag_count} dialogue tags (said/asked/replied)",
            )

        # Accept: titled name (Mr. Smith, Mrs. Jones)
        if re.match(r'^(Mr|Mrs|Ms|Miss|Dr|Sir|Lady|Lord)\.?\s+\w+', name):
            alias_candidates = self._find_obvious_aliases(proposal)
            return CharacterValidationResult(
                proposal=proposal,
                is_person_score=0.85,
                context_score=0.8,
                alias_candidates=alias_candidates,
                overall_score=0.82,
                is_valid=True,
                reasoning=f"Titled name pattern suggests person",
            )

        # Reject: single mention, no dialogue
        if proposal.mention_count == 1 and dialogue_mentions == 0:
            # Check context for character verbs
            context = proposal.mentions[0].context.lower() if proposal.mentions else ""
            has_character_verb = any(verb in context for verb in CHARACTER_VERBS)

            if not has_character_verb:
                return CharacterValidationResult(
                    proposal=proposal,
                    is_person_score=0.3,
                    context_score=0.2,
                    alias_candidates=[],
                    overall_score=0.25,
                    is_valid=False,
                    reasoning="Single mention without dialogue or character verbs",
                )

        # Ambiguous: need LLM validation
        return None

    def _llm_validation(self, proposal: CharacterProposal) -> CharacterValidationResult:
        """Use LLM to validate ambiguous cases."""
        # Prepare sample contexts
        contexts = []
        for mention in proposal.mentions[:5]:  # Up to 5 examples
            context_preview = mention.context[:200] if len(mention.context) > 200 else mention.context
            dialogue_marker = "[in dialogue]" if mention.in_dialogue else "[narrative]"
            contexts.append(f"  {dialogue_marker} ...{context_preview}...")

        contexts_str = "\n".join(contexts)

        prompt = VALIDATION_PROMPT_TEMPLATE.format(
            name=proposal.name,
            strategy=proposal.strategy,
            mention_count=proposal.mention_count,
            contexts=contexts_str,
        )

        # Retry logic with exponential backoff
        max_retries = 2
        last_error = None

        for attempt in range(max_retries + 1):
            result, response = self.llm.query_json(prompt, system=VALIDATION_SYSTEM_PROMPT)

            if not response.success:
                last_error = f"LLM query failed: {response.error}"
                logger.warning(f"LLM validation attempt {attempt + 1} for '{proposal.name}' failed: {last_error}")
                if attempt < max_retries:
                    time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
                    continue
                else:
                    raise ValueError(f"LLM validation failed for '{proposal.name}' after {max_retries + 1} attempts: {last_error}")

            if result is None or not isinstance(result, dict):
                error_detail = f"got {type(result).__name__}" if result is not None else "failed to parse JSON"

                # If LLM returned a list, log the actual content for debugging
                if isinstance(result, list):
                    logger.warning(f"LLM validation for '{proposal.name}' returned a list instead of object. List content: {result[:3] if len(result) > 3 else result}")

                last_error = f"Invalid JSON: {error_detail}"
                logger.warning(f"LLM validation attempt {attempt + 1} for '{proposal.name}' returned invalid JSON: {error_detail}")
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    raise ValueError(f"LLM validation returned invalid JSON for '{proposal.name}' after {max_retries + 1} attempts: {last_error}")

            # Success - parse LLM response
            break

        # Parse LLM response
        is_person = result.get("is_person", True)
        is_person_score = 0.9 if is_person else 0.1
        # F14: Warn when LLM doesn't return context_supports score
        context_supports_raw = result.get("context_supports")
        if context_supports_raw is None:
            logger.warning(
                f"LLM validation for '{proposal.name}' did not return context_supports - "
                "using neutral default 0.5"
            )
            context_score = 0.5
        else:
            context_score = float(context_supports_raw)
        alias_candidates = result.get("alias_candidates", [])
        overall_valid = result.get("overall_valid", is_person)
        reasoning = result.get("is_person_reasoning", "LLM validation")

        # F16: Include mention count in overall_score calculation
        # High-mention characters should get higher confidence scores
        base_score = (is_person_score + context_score) / 2

        # Mention count boost: characters with many mentions are more likely real
        mention_count = proposal.mention_count
        if mention_count >= 100:
            mention_boost = 0.15
        elif mention_count >= 50:
            mention_boost = 0.10
        elif mention_count >= 20:
            mention_boost = 0.05
        elif mention_count >= 10:
            mention_boost = 0.02
        else:
            mention_boost = 0.0

        overall_score = min(1.0, base_score + mention_boost)

        logger.debug(
            f"Validation score for '{proposal.name}': base={base_score:.2f}, "
            f"mention_boost={mention_boost:.2f} ({mention_count} mentions), "
            f"final={overall_score:.2f}"
        )

        return CharacterValidationResult(
            proposal=proposal,
            is_person_score=is_person_score,
            context_score=context_score,
            alias_candidates=alias_candidates,
            overall_score=overall_score,
            is_valid=overall_valid and overall_score >= self.min_confidence,
            reasoning=reasoning,
        )

    def _count_dialogue_tags(self, proposal: CharacterProposal) -> int:
        """Count how often the name appears in dialogue tags."""
        count = 0
        name_pattern = re.escape(proposal.name)

        # Patterns like: said Nick, asked Gatsby, replied Jordan
        tag_patterns = [
            rf'said\s+{name_pattern}',
            rf'asked\s+{name_pattern}',
            rf'replied\s+{name_pattern}',
            rf'whispered\s+{name_pattern}',
            rf'shouted\s+{name_pattern}',
            rf'{name_pattern}\s+said',
            rf'{name_pattern}\s+asked',
            rf'{name_pattern}\s+replied',
        ]

        for mention in proposal.mentions:
            context = mention.context
            for pattern in tag_patterns:
                if re.search(pattern, context, re.IGNORECASE):
                    count += 1
                    break  # Count each mention only once

        return count

    def _find_obvious_aliases(self, proposal: CharacterProposal) -> list[str]:
        """Find obvious alias candidates based on the name."""
        aliases = []
        name = proposal.name

        # Extract first and last name
        parts = name.split()

        if len(parts) >= 2:
            first_name = parts[0]
            last_name = parts[-1]

            # Handle titles
            if first_name.lower().rstrip('.') in {'mr', 'mrs', 'ms', 'miss', 'dr', 'sir', 'lady', 'lord'}:
                if len(parts) >= 3:
                    first_name = parts[1]
                    last_name = parts[-1]
                else:
                    first_name = None
                    last_name = parts[-1]

            if first_name:
                aliases.append(first_name)

            # NOTE: We do NOT generate phantom titled versions here (e.g., "Mr. LastName")
            # because they may not exist in the text. The consensus stage, which has access
            # to all character names, will handle alias detection with the LLM's help.
            # Generating phantom aliases pollutes the system and wastes LLM tokens.

        # Use shared nickname map from constants module
        name_lower = name.lower()
        for full_name, nicknames in NICKNAME_MAP.items():
            if full_name in name_lower:
                aliases.extend([n.title() for n in nicknames])
            elif any(nick in name_lower for nick in nicknames):
                aliases.append(full_name.title())

        return list(set(aliases))

    def _is_plural_family_reference(self, name: str, mentions: list) -> bool:
        """
        Detect if a name is likely a plural family reference (e.g., "the Montresors").

        Checks if:
        1. Name ends in 's' (possible plural)
        2. Contexts show patterns like "the Xs", "of the Xs", "X family"
        3. Not a common name ending in 's' (Charles, James, etc.)
        """
        # Must end in 's' to be a potential plural
        if not name.endswith('s') or len(name) < 4:
            return False

        # Common names that legitimately end in 's'
        # (these are NOT plural family references)
        common_s_endings = {
            'james', 'charles', 'thomas', 'lucas', 'nicholas', 'jonas',
            'francis', 'silas', 'julius', 'marcus', 'atticus', 'rufus',
            'jesus', 'moses', 'agnes', 'frances', 'gladys', 'doris',
        }

        if name.lower() in common_s_endings:
            return False

        # Check contexts for plural family patterns
        family_pattern_count = 0
        total_mentions = len(mentions)

        for mention in mentions:
            context = mention.context.lower()
            name_lower = name.lower()

            # Patterns indicating family reference:
            # "the Montresors", "of the Montresors", "Montresors were", "Montresors had"
            family_patterns = [
                f'the {name_lower}',
                f'of the {name_lower}',
                f'{name_lower} were',
                f'{name_lower} had been',
                f'{name_lower} family',
            ]

            if any(pattern in context for pattern in family_patterns):
                family_pattern_count += 1

        # If >50% of mentions show family patterns, likely a plural reference
        if total_mentions > 0 and family_pattern_count / total_mentions > 0.5:
            return True

        return False
