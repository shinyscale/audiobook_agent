"""
Character proposal validator.

Validates character proposals and identifies potential aliases.
"""

import re
from typing import Optional
import logging

from .models import CharacterProposal, CharacterValidationResult
from ..llm import LLMClient

logger = logging.getLogger(__name__)


# Known non-person entities that might be detected as characters
PLACE_NAMES = {
    'london', 'paris', 'new york', 'england', 'america', 'france', 'germany',
    'broadway', 'manhattan',
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
- Is this a person's name (not a place, title alone, or abstract concept)?
- Does the context suggest this is a character who acts, speaks, or is spoken about?
- What other names/titles might refer to the same person?"""


VALIDATION_PROMPT_TEMPLATE = """Validate this character proposal from a novel:

PROPOSED NAME: {name}
STRATEGY: {strategy}
MENTION COUNT: {mention_count}

SAMPLE CONTEXTS (where this name appears):
{contexts}

Please analyze and return JSON with:
- "is_person": true/false - Is this a real person/character name (not a place, title, or concept)?
- "is_person_reasoning": Brief explanation
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

        # Accept: high mention count with dialogue
        dialogue_mentions = sum(1 for m in proposal.mentions if m.in_dialogue)
        if proposal.mention_count >= 10 and dialogue_mentions >= 3:
            # Strong signal: mentioned often and speaks
            alias_candidates = self._find_obvious_aliases(proposal)
            return CharacterValidationResult(
                proposal=proposal,
                is_person_score=0.95,
                context_score=0.9,
                alias_candidates=alias_candidates,
                overall_score=0.92,
                is_valid=True,
                reasoning=f"High mention count ({proposal.mention_count}) with dialogue ({dialogue_mentions} in speech)",
            )

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

        result, response = self.llm.query_json(prompt, system=VALIDATION_SYSTEM_PROMPT)

        if not response.success:
            # HTTP error or connection failure - fail fast instead of masking with fallback
            error_msg = f"LLM validation failed for '{proposal.name}': {response.error}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        if result is None or not isinstance(result, dict):
            # JSON parsing failure or wrong type - fail fast instead of masking with fallback
            error_detail = f"got {type(result).__name__}" if result is not None else "failed to parse JSON"
            error_msg = f"LLM validation returned invalid JSON for '{proposal.name}': {error_detail}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Parse LLM response
        is_person = result.get("is_person", True)
        is_person_score = 0.9 if is_person else 0.1
        context_score = float(result.get("context_supports", 0.5))
        alias_candidates = result.get("alias_candidates", [])
        overall_valid = result.get("overall_valid", is_person)
        reasoning = result.get("is_person_reasoning", "LLM validation")

        overall_score = (is_person_score + context_score) / 2

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

        # Common nickname patterns
        nickname_map = {
            'elizabeth': ['lizzy', 'liz', 'beth', 'eliza'],
            'william': ['will', 'bill', 'billy', 'willy'],
            'robert': ['rob', 'bob', 'bobby', 'robbie'],
            'richard': ['rick', 'dick', 'ricky'],
            'james': ['jim', 'jimmy', 'jamie'],
            'katherine': ['kate', 'kathy', 'katie', 'kitty'],
            'margaret': ['maggie', 'meg', 'peggy', 'marge'],
            'nicholas': ['nick', 'nicky'],
        }

        name_lower = name.lower()
        for full_name, nicknames in nickname_map.items():
            if full_name in name_lower:
                aliases.extend([n.title() for n in nicknames])
            elif any(nick in name_lower for nick in nicknames):
                aliases.append(full_name.title())

        return list(set(aliases))
