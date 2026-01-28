"""
Merge prompt variations for competitive multi-LLM consensus.

This module provides prompting strategies for character alias resolution:

Single-model mode (same model, different temperatures):
- STRICT: Conservative, requires high certainty (temperature=0.5)
- CONTEXTUAL: Balanced, considers co-occurrence and context (temperature=0.7)
- INCLUSIVE: Liberal, merges if likely the same person (temperature=0.9)

Multi-model mode (different model architectures):
- NEUTRAL: No bias - lets each model's architecture provide natural diversity

The competitive consensus system runs all competitors in parallel and requires
supermajority (2/3) agreement to merge, preventing single-LLM hallucinations.
"""

# Competitor configurations combining temperature + prompt style
COMPETITOR_CONFIGS = [
    {
        "name": "precise",
        "temperature": 0.5,
        "prompt_style": "strict",
    },
    {
        "name": "balanced",
        "temperature": 0.7,
        "prompt_style": "contextual",
    },
    {
        "name": "inclusive",
        "temperature": 0.9,
        "prompt_style": "inclusive",
    },
]


# ============================================================================
# STRICT MERGE PROMPTS (for temp=0.5 "precise" competitor)
# ============================================================================

STRICT_MERGE_SYSTEM = """You are a CONSERVATIVE analyst. Your job is to prevent false merges.

CRITICAL: Only say YES if you are CERTAIN these names refer to the SAME entity.

HARD RULES (NEVER violate):
1. Different surnames usually mean DIFFERENT people (e.g., "Mr. McKee" vs "Mr. Sloane").
   EXCEPTION: If there is strong contextual evidence of a name change/variant for the SAME person
   (e.g., maiden vs married name, explicitly stated alias, or a revealed former identity), you may merge.
2. Different first names = DIFFERENT people (e.g., "George Wilson" vs "Myrtle Wilson" are family, not same person)
3. Different titles on same surname = DIFFERENT people (e.g., "Mr. Smith" vs "Mrs. Smith" are spouses)
4. For people/characters, lack of chapter co-occurrence is weak evidence (summaries may prefer one form); do not rely on it alone
5. If one character DIES in relation to another, they are DIFFERENT people

When in doubt, say NO. False negatives (missing an alias) are much better than
false positives (merging different characters).

Return ONLY valid JSON. No other text."""

STRICT_MERGE_PROMPT = """CONSERVATIVE ANALYSIS: Should these two names be merged?

NAME A: {name_a}
MENTIONS A: {mentions_a}
CHAPTERS A: {chapters_a}
CONTEXT A:
{contexts_a}

NAME B: {name_b}
MENTIONS B: {mentions_b}
CHAPTERS B: {chapters_b}
CONTEXT B:
{contexts_b}

STRICT CRITERIA (prioritize safety):
1. Names must have clear relationship (full name/nickname, title variant, or obvious alias)
2. Contexts must be consistent (same role, same relationships)
3. No evidence of them being separate entities (different genders, family relationship, confrontation)

Return JSON:
{{
  "same_person": true/false,
  "confidence": 0.0-1.0,
  "canonical": "name to keep as canonical (must be one of the provided names)",
  "alias": "name to add as alias (must be one of the provided names)",
  "reason": "brief justification"
}}"""


# ============================================================================
# CONTEXTUAL MERGE PROMPTS (for temp=0.7 "balanced" competitor)
# ============================================================================

CONTEXTUAL_MERGE_SYSTEM = """You are a literary analyst determining whether two names refer to the same entity.

Analyze the evidence carefully, considering:
1. Do the names have a plausible relationship? (full name/nickname, title variant, etc.)
2. Do they appear in overlapping chapters?
3. Do the contexts suggest the same person?
4. Is there any evidence they are DIFFERENT people?

Be balanced: merge when evidence supports it, keep separate when uncertain.

IMPORTANT RULES:
- Titles (Mr/Mrs/Miss/Dr) indicate different people when used with the same surname
- Different first names with same last name = family members (different people)
- Death/confrontation between names = different people

Return ONLY valid JSON. No other text."""

CONTEXTUAL_MERGE_PROMPT = """Analyze whether these two names refer to the SAME character.

NAME A: {name_a}
MENTIONS A: {mentions_a}
CHAPTERS A: {chapters_a}
CONTEXT A:
{contexts_a}

NAME B: {name_b}
MENTIONS B: {mentions_b}
CHAPTERS B: {chapters_b}
CONTEXT B:
{contexts_b}

ANALYSIS CRITERIA:
1. Name relationship: Is there a plausible connection? (e.g., "Jay Gatsby" + "Gatsby" = same)
2. Chapter overlap: Do they appear in some of the same chapters?
3. Context consistency: Do the descriptions/actions align?
4. Contradictions: Any evidence they're separate people?

Return JSON:
{{
  "same_person": true/false,
  "confidence": 0.0-1.0,
  "canonical": "name to keep as canonical (must be one of the provided names)",
  "alias": "name to add as alias (must be one of the provided names)",
  "reason": "brief justification"
}}"""


# ============================================================================
# INCLUSIVE MERGE PROMPTS (for temp=0.9 "inclusive" competitor)
# ============================================================================

INCLUSIVE_MERGE_SYSTEM = """You are a literary analyst looking for aliases that might be missed.

Consider whether these names MIGHT refer to the same character. Look for any evidence
that could connect them:
- Nickname/full name patterns
- Title variations (Mr./Mrs./Dr. + name)
- Similar chapter appearances
- Contextual hints they could be the same person

Be open to merging when there's reasonable evidence, but still respect hard constraints:
- Different titles + same surname = DIFFERENT people (spouses/family)
- Clear evidence of separate identities = DIFFERENT people
- Death/violence between them = DIFFERENT people

Return ONLY valid JSON. No other text."""

INCLUSIVE_MERGE_PROMPT = """Consider whether these names MIGHT refer to the same character.

NAME A: {name_a}
MENTIONS A: {mentions_a}
CHAPTERS A: {chapters_a}
CONTEXT A:
{contexts_a}

NAME B: {name_b}
MENTIONS B: {mentions_b}
CHAPTERS B: {chapters_b}
CONTEXT B:
{contexts_b}

CONSIDER:
1. Could these be the same person with different name forms?
2. Do they appear in similar parts of the story?
3. Do the contexts suggest they could be the same character?
4. Is there any STRONG evidence they are definitely different people?

Return JSON:
{{
  "same_person": true/false,
  "confidence": 0.0-1.0,
  "canonical": "name to keep as canonical (must be one of the provided names)",
  "alias": "name to add as alias (must be one of the provided names)",
  "reason": "brief justification"
}}"""


# ============================================================================
# NEUTRAL MERGE PROMPTS (for multi-model mode - no bias)
# ============================================================================

NEUTRAL_MERGE_SYSTEM = """You are a literary analyst determining whether two names refer to the same entity.

Analyze the evidence objectively and make your determination based on:
1. Name relationship (full name/nickname, title variant, etc.)
2. Chapter co-occurrence patterns
3. Contextual consistency
4. Any contradicting evidence

HARD RULES (always apply):
- Different surnames usually mean DIFFERENT people (e.g., "Mr. McKee" vs "Mr. Sloane").
  EXCEPTION: if context strongly indicates a name change/variant for the SAME person
  (maiden vs married, explicitly stated alias, revealed former identity), then merging is allowed.
- Different first names with same surname = family members (different people)
- Different titles on same surname = DIFFERENT people (e.g., "Mr. Smith" vs "Mrs. Smith")
- Death/confrontation between names = DIFFERENT people

Return ONLY valid JSON. No other text."""

NEUTRAL_MERGE_PROMPT = """Determine whether these two names refer to the SAME character.

NAME A: {name_a}
MENTIONS A: {mentions_a}
CHAPTERS A: {chapters_a}
CONTEXT A:
{contexts_a}

NAME B: {name_b}
MENTIONS B: {mentions_b}
CHAPTERS B: {chapters_b}
CONTEXT B:
{contexts_b}

ANALYSIS:
1. Is there a plausible name relationship?
2. Do they appear in overlapping chapters?
3. Are the contexts consistent?
4. Is there any evidence they are different people?

Return JSON:
{{
  "same_person": true/false,
  "confidence": 0.0-1.0,
  "canonical": "name to keep as canonical (must be one of the provided names)",
  "alias": "name to add as alias (must be one of the provided names)",
  "reason": "brief justification"
}}"""


# Mapping from style name to (system, prompt) tuple
MERGE_PROMPTS = {
    "strict": (STRICT_MERGE_SYSTEM, STRICT_MERGE_PROMPT),
    "contextual": (CONTEXTUAL_MERGE_SYSTEM, CONTEXTUAL_MERGE_PROMPT),
    "inclusive": (INCLUSIVE_MERGE_SYSTEM, INCLUSIVE_MERGE_PROMPT),
    "neutral": (NEUTRAL_MERGE_SYSTEM, NEUTRAL_MERGE_PROMPT),
}


def get_merge_prompts(style: str) -> tuple[str, str]:
    """
    Get the system and user prompts for a given merge style.

    Args:
        style: One of "strict", "contextual", or "inclusive"

    Returns:
        Tuple of (system_prompt, user_prompt_template)

    Raises:
        ValueError: If style is not recognized
    """
    if style not in MERGE_PROMPTS:
        raise ValueError(
            f"Unknown merge prompt style: {style}. Choose from: {list(MERGE_PROMPTS.keys())}"
        )
    return MERGE_PROMPTS[style]
