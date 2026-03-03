"""
Post-processing corrections for character profiling.

Extracted from analyzer.py's inline correction blocks. Each method fixes a
specific LLM failure mode (hallucinated relationships, same-name contamination,
gender-inconsistent labels, etc.). All corrections are book-agnostic.

Two classes split by the type boundary:
- PipelineCharacterCorrector: operates on pipeline Character objects during profiling
- OutputCharacterCorrector: operates on output Character (Pydantic) after conversion
"""

import json
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

RELATIONSHIP_REVERSES = {
    "father": "son",
    "mother": "daughter",
    "son": "father",
    "daughter": "mother",
    "brother": "brother",
    "sister": "sister",
    "grandfather": "grandson",
    "grandmother": "granddaughter",
    "grandson": "grandfather",
    "granddaughter": "grandmother",
    "uncle": "nephew",
    "aunt": "niece",
    "nephew": "uncle",
    "niece": "aunt",
    "cousin": "cousin",
    "husband": "wife",
    "wife": "husband",
    "spouse": "spouse",
    "partner": "partner",
    "guardian": "ward",
    "ward": "guardian",
    # Parent/child (generic forms)
    "parent": "child",
    "child": "parent",
    # Employment
    "employer": "employee",
    "employee": "employer",
    # Mentor/apprentice
    "mentor": "protégé",
    "protégé": "mentor",
}

# Relationships that are symmetric: A→B implies B→A with the same label.
# These are VALID when bidirectional — both sides having the same label is correct.
# Only asymmetric labels (father, creator, mentor, etc.) are contradictory when bidirectional.
_SYMMETRIC_RELATIONSHIPS = frozenset({
    "acquaintance", "associate", "associated", "business partner",
    "close friend", "colleague", "friend",
    "ally", "neighbor", "rival", "enemy",
    "romantic interest", "love interest",
    "sibling", "twin", "brother", "sister", "cousin",
    "co-conspirator", "conspirator", "partner", "spouse",
})

FAMILY_TERMS = (
    "cousin", "brother", "sister", "uncle", "aunt", "nephew", "niece",
    "father", "mother", "son", "daughter", "husband", "wife",
    "grandfather", "grandmother", "grandson", "granddaughter",
    # Generic forms — LLMs use "parent"/"child" when direction is uncertain.
    # Including them here enables verify_relationships_from_text to upgrade
    # them to directional labels (e.g., "father"/"son") when text evidence
    # is available, and reject_unfounded_familial_labels to downgrade them
    # when no shared surname or text evidence supports the claim.
    "parent", "child",
)

PHYS_DESCRIPTOR_WORDS = {
    "man", "woman", "person", "elderly", "old", "young", "tall",
    "short", "thin", "small", "lean", "stout", "fat", "grizzled",
    "bald", "gray", "grey", "large",
    # Extended physical appearance descriptors
    "face", "eyes", "eye", "hair", "mouth", "lips", "chin", "brow",
    "complexion", "build", "figure", "slim", "slender", "dark", "fair",
    "skin", "handsome", "beautiful", "pale", "flushed", "broad", "muscular",
    "athletic", "stocky", "lanky", "wiry", "gaunt", "plump", "heavyset",
}

MALE_INDICATORS = {"man", " he ", " his ", "himself", "boy", "gentleman", "mr."}
FEMALE_INDICATORS = {"woman", " she ", " her ", "herself", "girl", "lady", "mrs.", "miss"}
FEMALE_ONLY_RELS = {"mother", "sister", "wife", "daughter", "grandmother", "granddaughter", "aunt", "niece"}
MALE_ONLY_RELS = {"father", "brother", "husband", "son", "grandfather", "grandson", "uncle", "nephew"}

SAME_PERSON_PHRASES = ("same person", "same character", "identical to", "the same as", "same individual")

NO_DESC_PHRASES = (
    "unknown", "does not provide", "no physical description",
    "not described", "not directly described", "not physically described",
    "no direct physical", "no description",
    "not provide a direct",
)

# ---------------------------------------------------------------------------
# Compiled regex patterns
# ---------------------------------------------------------------------------

_phys_joined = '|'.join(sorted(PHYS_DESCRIPTOR_WORDS, key=len, reverse=True))

# Pattern A: direct self-description  ("I am an old man", "I was a lean person")
_narrator_desc_pattern_a = re.compile(
    r'\bI[\s.…]{0,20}(?:am|was)\b[^\n]{0,200}?\b(?:' + _phys_joined + r')\b',
    re.IGNORECASE,
)

# Pattern B: indirect self-description ("as I stood, an elderly, grizzled man")
_narrator_desc_pattern_b = re.compile(
    r'\bI\b.{0,80}?\ban?\s+(?:' + _phys_joined + r')\b.{0,150}?\b(?:man|woman|person)\b',
    re.IGNORECASE | re.DOTALL,
)

# Family relationship phrase pattern
_rel_phrase_re = re.compile(
    r'\b(?:a|an|(?:his|her|my|our|their|your)\s+(?:late\s+|dear\s+)?)\s*('
    + '|'.join(FAMILY_TERMS) + r')\b',
    re.IGNORECASE,
)

# Non-family relationship terms for extended relationship detection.
# These are universal words that appear in any novel to describe relationships.
# Used by verify_relationships_from_text() to upgrade "associated" labels.
_NONFAMILY_REL_TERMS = (
    "friend",
    "companion",
    "confidant",
    "betrothed",
    "fiancée",
    "fiancee",
    "fiancé",
    "beloved",
    "lover",
    "rival",
    "enemy",
    "foe",
    "mentor",
    "protégé",
    "employer",
    "servant",
    "guardian",
    "ward",
    "colleague",
    "creator",
    "creation",
)

# Combined family + non-family terms for verify_relationships_from_text.
# Extended prefix handles "my best friend", "my old friend", "my dearest friend", etc.
_all_rel_terms = list(FAMILY_TERMS) + list(_NONFAMILY_REL_TERMS)
_all_rel_phrase_re = re.compile(
    r'\b(?:a|an|(?:his|her|my|our|their|your)\s+'
    r'(?:late\s+|dear\s+|dearest\s+|best\s+|close\s+|old\s+|trusted\s+)?)\s*('
    + '|'.join(sorted(_all_rel_terms, key=len, reverse=True)) + r')\b',
    re.IGNORECASE,
)

# Death phrase pattern
_death_phrase_re = re.compile(r'\s+in\s+death(?=[.,;!?]|$)', re.IGNORECASE)

# Attribution phrase pattern — detects clauses like "(as described by X)" that indicate
# a physical feature was sourced from another character's description, not this character's.
_attribution_re = re.compile(r'\(as described by\b', re.IGNORECASE)


def _strip_attribution_clauses(text: str, other_canonical_names: set) -> str:
    """Remove semicolon-separated clauses that attribute a description to another character.

    When an appearance summary contains a clause like 'has red hair (as described by
    Catherine)', that feature belongs to Catherine, not the subject. This is a universal
    invariant: cross-character attribution signals contamination of the description.
    Only removes clauses where the attribution refers to an actual cast member.
    """
    if not _attribution_re.search(text):
        return text  # fast path: no attribution in text
    parts = re.split(r';\s*', text)
    kept = []
    for part in parts:
        if _attribution_re.search(part):
            # Check whether the attribution refers to a known cast member
            part_lower = part.lower()
            if any(
                name.lower() in part_lower or name.split()[-1].lower() in part_lower
                for name in other_canonical_names
            ):
                logger.debug(f"Stripping attribution clause: {part!r}")
                continue  # skip contaminated clause
        kept.append(part)
    return '; '.join(kept)

# Age extraction patterns
_written_num_pat = (
    r"(?:twenty(?:[\s-](?:one|two|three|four|five|six|seven|eight|nine))?|"
    r"thirty(?:[\s-](?:one|two|three|four|five|six|seven|eight|nine))?|"
    r"forty(?:[\s-](?:one|two|three|four|five|six|seven|eight|nine))?|"
    r"fifty(?:[\s-](?:one|two|three|four|five|six|seven|eight|nine))?|"
    r"sixty(?:[\s-](?:one|two|three|four|five|six|seven|eight|nine))?|"
    r"seventy(?:[\s-](?:one|two|three|four|five|six|seven|eight|nine))?|"
    r"eighty(?:[\s-](?:one|two|three|four|five|six|seven|eight|nine))?|"
    r"ninety(?:[\s-](?:one|two|three|four|five|six|seven|eight|nine))?|"
    r"(?:one|two|three|four|five|six|seven|eight|nine)(?:teen)?)"
)

_age_extract_pat = re.compile(
    r"(?:\d+[\s-]+years?[\s-]+old|\d+[\s-]+year[\s-]+old|"
    r"aged?\s+\d+|age\s+of\s+\d+|"
    r"(?:" + _written_num_pat + r")[\s-]+years?[\s-]+old)",  # written nums MUST have "old"
    re.IGNORECASE,
)

# Strict age pattern for *validating* age_indication values:
# Written-number forms require "old" (rejects "five years" durations without "old").
# Numeric forms keep accepting with or without "old" since numbers are less ambiguous.
_strict_age_validate_pat = re.compile(
    r"(?:\d+[\s-]+years?(?:[\s-]+old)?|\d+[\s-]+year(?:[\s-]+old)?|"
    r"aged?\s+\d+|age\s+of\s+\d+|"
    r"(?:" + _written_num_pat + r")[\s-]+years?[\s-]+old)",  # written nums MUST have "old"
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _physical_descriptor_score(text: str) -> int:
    """Count unique physical descriptor words in text."""
    tl = text.lower()
    return sum(1 for w in PHYS_DESCRIPTOR_WORDS if re.search(r'\b' + w + r'\b', tl))


def _extract_narrator_description(match, source_text: str, is_pattern_b: bool) -> str:
    """Extract cleaned narrator description from a regex match."""
    if is_pattern_b:
        window = source_text[match.start():match.start() + 300]
        art = re.search(
            r'\ban?\s+(?:' + _phys_joined + r')\b(?:[^\n]|\n(?!\n)){0,200}',
            window, re.IGNORECASE,
        )
        if art:
            raw = art.group()
            raw = re.split(r'--|—', raw)[0]
            cleaned = re.sub(r'\s*\n\s*', ' ', raw).strip().rstrip('.,;- ')
        else:
            cleaned = re.sub(r'\s*\n\s*', ' ', match.group()).strip()[:200]
    else:
        cleaned = re.sub(
            r'^I[\s.…]*(?:am|was)\s*', '', match.group(), flags=re.IGNORECASE
        ).strip().rstrip('.,;')
    return cleaned


def _find_best_narrator_match(source_text: str):
    """Find best narrator self-description match in text.

    Returns (match, score, is_pattern_b) or (None, -1, False).
    """
    best_match = None
    best_score = -1
    best_is_pb = False

    for m in _narrator_desc_pattern_a.finditer(source_text):
        s = _physical_descriptor_score(m.group())
        if s > best_score:
            best_score, best_match, best_is_pb = s, m, False

    for m in _narrator_desc_pattern_b.finditer(source_text):
        if '\n\n' in m.group():
            continue
        s = _physical_descriptor_score(m.group())
        if s > best_score:
            best_score, best_match, best_is_pb = s, m, True

    return best_match, best_score, best_is_pb


def _is_compact_physical_description(text: str) -> bool:
    """Return True if the text looks like a concise physical description.

    Physical descriptions are dense with descriptor words relative to their length.
    Narrative prose (e.g., "a young man at the office suggested that we...") is long
    but sparse in physical descriptors. This filter rejects the latter.

    Universal invariant: a valid appearance.summary should be a brief description
    of physical attributes, not a plot excerpt that happens to mention a physical word.
    """
    score = _physical_descriptor_score(text)
    if score < 2:
        return False
    # Long text with low physical word density is narrative prose, not a description
    if len(text) > 60 and score / len(text) < 0.04:
        return False
    return True


def _build_name_patterns(characters) -> dict:
    """Build per-character name regex patterns (canonical + aliases)."""
    patterns = {}
    for c in characters:
        variants = {re.escape(c.canonical_name)}
        for alias in (getattr(c, 'aliases', None) or []):
            if len(alias) >= 3:
                variants.add(re.escape(alias))
        patterns[c.canonical_name] = re.compile(
            r'\b(?:' + '|'.join(sorted(variants, key=len, reverse=True)) + r')\b',
            re.IGNORECASE,
        )
    return patterns


# ---------------------------------------------------------------------------
# Phase A: Pipeline Character corrections
# ---------------------------------------------------------------------------

class PipelineCharacterCorrector:
    """Post-processing corrections on pipeline Character objects.

    Runs after profile generation, before conversion to output format.
    """

    def __init__(self, llm_client=None, evidence_store: Optional[dict] = None):
        self._llm = llm_client
        self._evidence_store = evidence_store or {}

    def run_all(self, characters, source_text: str) -> None:
        """Run all Phase A corrections in order. Mutates characters in place."""
        self.inject_narrator_appearance(characters, source_text)
        self.remove_contradictory_relationships(characters)
        self.infer_bidirectional_relationships(characters)
        self.fix_same_name_contamination(characters)
        self.remove_unsupported_death_claims(characters)
        self.correct_description_relationships(characters, source_text)

    def inject_narrator_appearance(self, characters, source_text: str) -> None:
        """Inject physical self-description for first-person narrators.

        First-person narrators who describe themselves physically (e.g.,
        "I am an elderly, grizzled man") often get "Unknown" appearance because
        the LLM does not connect "I am" to the narrator character. This pass
        directly injects the self-description when the narrator's appearance
        is still unknown and a first-person physical description is found.
        """
        for char in characters:
            if not getattr(char, 'is_narrator', False):
                continue
            if char.appearance is None:
                continue

            current_summary = (char.appearance.get("summary", "") or "").strip().lower()
            has_real_appearance = current_summary and not any(
                phrase in current_summary for phrase in NO_DESC_PHRASES
            )
            if has_real_appearance:
                continue

            best_match, best_score, is_pb = _find_best_narrator_match(source_text)

            if best_match is not None and best_score >= 2:
                cleaned = _extract_narrator_description(best_match, source_text, is_pb)
                if cleaned and _is_compact_physical_description(cleaned):
                    char.appearance["summary"] = cleaned
                    logger.info(
                        f"Post-profile narrator appearance injection for "
                        f"'{char.canonical_name}': {cleaned!r}"
                    )
                    desc_lower = best_match.group().lower()
                    current_age = (char.appearance.get("age_indication", "") or "").lower()
                    if current_age in ("", "unknown"):
                        if any(w in desc_lower for w in ("elderly", "old", "aged")):
                            char.appearance["age_indication"] = "elderly"
                        elif "young" in desc_lower:
                            char.appearance["age_indication"] = "young"
                elif cleaned:
                    logger.info(
                        f"Post-profile narrator injection skipped: sparse description "
                        f"for '{char.canonical_name}': {cleaned[:60]!r}"
                    )

    def remove_contradictory_relationships(self, characters) -> None:
        """Remove relationships where both A→B and B→A carry the same
        non-symmetric label (e.g., both "father"), which is logically impossible.

        This runs BEFORE bidirectional inference so that the inference step
        does not propagate wrong labels. For example, if the LLM erroneously
        labels Felix→Agatha='father' AND Agatha→Felix='father' (they are
        actually siblings), both are removed rather than one being silently
        flipped to 'son'/'daughter'.
        """
        char_by_name = {c.canonical_name: c for c in characters}
        to_remove: list[tuple[object, str]] = []  # (char_object, other_name) pairs to remove

        seen_pairs: set[frozenset] = set()
        for char_a in characters:
            rels_a = getattr(char_a, "relationships", None) or {}
            for other_name, rel_a in list(rels_a.items()):
                if not isinstance(rel_a, str):
                    continue
                rel_a_lower = rel_a.strip().lower()
                if rel_a_lower in _SYMMETRIC_RELATIONSHIPS:
                    continue  # symmetric labels are valid both ways

                pair = frozenset({char_a.canonical_name, other_name})
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)

                char_b = char_by_name.get(other_name)
                if not char_b:
                    continue
                rels_b = getattr(char_b, "relationships", None) or {}
                rel_b = rels_b.get(char_a.canonical_name, "")
                if not isinstance(rel_b, str):
                    continue
                rel_b_lower = rel_b.strip().lower()

                # Both sides carry the same asymmetric label → impossible
                if rel_a_lower == rel_b_lower and rel_a_lower not in _SYMMETRIC_RELATIONSHIPS:
                    logger.warning(
                        f"Removing contradictory relationship: "
                        f"'{char_a.canonical_name}'→'{other_name}'='{rel_a}' AND "
                        f"'{other_name}'→'{char_a.canonical_name}'='{rel_b}' "
                        f"(identical non-symmetric label is logically impossible)"
                    )
                    to_remove.append((rels_a, other_name))
                    to_remove.append((rels_b, char_a.canonical_name))

        for rel_dict, key in to_remove:
            rel_dict.pop(key, None)

    def infer_bidirectional_relationships(self, characters) -> None:
        """Infer reverse relationships.

        If character A -> B is "father", infer B -> A is "son" (if not
        already set). Family, employment, and symmetric social relationships
        are all bidirectional with known reverses.
        """
        char_by_name = {c.canonical_name: c for c in characters}

        for char_a in characters:
            rels_a = getattr(char_a, "relationships", None) or {}
            for other_name, rel_desc in list(rels_a.items()):
                if not isinstance(rel_desc, str):
                    continue
                rel_lower = rel_desc.strip().lower()
                reverse_rel = RELATIONSHIP_REVERSES.get(rel_lower)
                if not reverse_rel:
                    # Check symmetric relationships (A→B means B→A with same label)
                    if rel_lower in _SYMMETRIC_RELATIONSHIPS:
                        reverse_rel = rel_lower
                    else:
                        # Fall back to word-set lookup for multi-word relationship labels
                        rel_words = set(rel_lower.split())
                        for key in sorted(RELATIONSHIP_REVERSES, key=len, reverse=True):
                            if key in rel_words:
                                reverse_rel = RELATIONSHIP_REVERSES[key]
                                break
                        if not reverse_rel:
                            for sym in _SYMMETRIC_RELATIONSHIPS:
                                if sym in rel_lower:
                                    reverse_rel = sym
                                    break
                if reverse_rel and other_name in char_by_name:
                    char_b = char_by_name[other_name]
                    rels_b = getattr(char_b, "relationships", None)
                    if rels_b is None:
                        rels_b = {}
                        char_b.relationships = rels_b
                    existing = rels_b.get(char_a.canonical_name, "").strip().lower()
                    existing_words = set(existing.split())
                    if not existing or existing == "unknown" or reverse_rel not in existing_words:
                        rels_b[char_a.canonical_name] = reverse_rel
                        logger.info(
                            f"Bidirectional relationship inferred: "
                            f"{other_name} → {char_a.canonical_name} = '{reverse_rel}' "
                            f"(from {char_a.canonical_name} → {other_name} = '{rel_desc}')"
                        )

    def fix_same_name_contamination(self, characters) -> None:
        """Fix trait contamination for same-name character pairs.

        When two characters share a first name (e.g., "John" and "John
        Donaldson"), the shorter-named character may be profiled with traits
        that belong to the longer-named character. Uses LLM to detect and
        correct contamination.
        """
        if not self._llm or not self._evidence_store:
            return

        chars_with_profiles = [
            c for c in characters
            if c.personality is not None and c.personality.get("traits")
        ]

        for char_short in chars_with_profiles:
            name_short = char_short.canonical_name
            for char_long in chars_with_profiles:
                name_long = char_long.canonical_name
                if name_long == name_short:
                    continue
                if not name_long.lower().startswith(name_short.lower() + " "):
                    continue

                logger.info(
                    f"Post-profile correction: checking pair "
                    f"'{name_short}' (shorter) vs '{name_long}' (longer)"
                )

                ev_short = self._summarize_evidence(name_short)
                ev_long = self._summarize_evidence(name_long)

                traits_short = char_short.personality.get("traits", [])
                summary_short = char_short.personality.get("summary", "")
                traits_long = char_long.personality.get("traits", [])
                summary_long = char_long.personality.get("summary", "")
                age_short = (
                    (char_short.appearance or {}).get("age_indication", "unknown")
                    if char_short.appearance else "unknown"
                )
                desc_short = getattr(char_short, 'description', None) or ""
                app_short = (
                    (char_short.appearance or {}).get("summary", "")
                    if char_short.appearance else ""
                )

                correction_prompt = f"""Two characters share the same first name: "{name_short}" and "{name_long}".

Because their names overlap, the profiling system may have accidentally assigned "{name_long}"'s traits/descriptions to "{name_short}".

"{name_short}"'s story role (chapter summaries):
{ev_short}

"{name_long}"'s story role (chapter summaries):
{ev_long}

"{name_short}" was assigned:
- Personality traits: {traits_short}
- Personality summary: {summary_short}
- Age indication: {age_short}
- Description: {desc_short!r}
- Appearance summary: {app_short!r}

"{name_long}" was assigned:
- Personality traits: {traits_long}
- Personality summary: {summary_long}

Review traits, description, and appearance for "{name_short}". Remove only what clearly belongs to "{name_long}" instead. Keep traits if uncertain. Do NOT return empty traits.

Return JSON only:
{{
  "contamination_detected": true or false,
  "reason": "one sentence explanation",
  "corrected_personality": {{
    "summary": "...",
    "traits": ["keep if uncertain"],
    "temperament": "...",
    "emotional_range": "..."
  }},
  "corrected_age_indication": "young/middle-aged/elderly/unknown",
  "corrected_description": "description for {name_short} only — remove sentences about death or events that belong to {name_long}",
  "corrected_appearance_summary": "appearance for {name_short} only — remove attributes that belong to {name_long}"
}}
Only include fields if contamination_detected is true."""

                try:
                    response = self._llm.query(correction_prompt)
                    response_text = response.content if response.success else ""
                    corr_data = None
                    try:
                        corr_data = json.loads(response_text)
                    except json.JSONDecodeError:
                        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                        if json_match:
                            try:
                                corr_data = json.loads(json_match.group())
                            except json.JSONDecodeError:
                                pass

                    if corr_data and corr_data.get("contamination_detected"):
                        logger.info(
                            f"Post-profile correction: contamination detected for '{name_short}'. "
                            f"Reason: {corr_data.get('reason', '')}"
                        )
                        corr_personality = corr_data.get("corrected_personality")
                        if corr_personality and isinstance(corr_personality, dict):
                            char_short.personality = corr_personality
                            logger.info(
                                f"Post-profile correction: updated personality for '{name_short}': "
                                f"{corr_personality.get('traits', [])}"
                            )
                        corr_age = corr_data.get("corrected_age_indication")
                        if corr_age and char_short.appearance:
                            char_short.appearance["age_indication"] = corr_age
                            logger.info(
                                f"Post-profile correction: updated age for '{name_short}': {corr_age}"
                            )
                        corr_desc = corr_data.get("corrected_description")
                        if corr_desc and isinstance(corr_desc, str) and corr_desc.strip():
                            char_short.description = corr_desc.strip()
                            logger.info(
                                f"Post-profile correction: updated description for '{name_short}'"
                            )
                        corr_app_sum = corr_data.get("corrected_appearance_summary")
                        if (
                            corr_app_sum
                            and isinstance(corr_app_sum, str)
                            and corr_app_sum.strip()
                            and char_short.appearance
                        ):
                            char_short.appearance["summary"] = corr_app_sum.strip()
                            logger.info(
                                f"Post-profile correction: updated appearance for '{name_short}'"
                            )
                        print(
                            f"   Corrected profile for '{name_short}' "
                            f"(same-name contamination with '{name_long}')"
                        )
                    else:
                        logger.info(
                            f"Post-profile correction: no contamination detected for '{name_short}'"
                        )
                except Exception as e:
                    logger.warning(
                        f"Post-profile correction failed for '{name_short}': {e}"
                    )

    def remove_unsupported_death_claims(self, characters) -> None:
        """Remove 'in death' from descriptions when unsupported by evidence.

        If a character's description says the character died ("in death") but
        none of their profile evidence quotes reference dying/death, the claim
        is likely hallucinated.
        """
        for char in characters:
            desc = getattr(char, 'description', '') or ''
            if not _death_phrase_re.search(desc):
                continue
            evidence = getattr(char, 'profile_evidence', []) or []
            death_supported = any(
                any(
                    w in (
                        (e.get('quote', '') if isinstance(e, dict) else getattr(e, 'quote', '')) or ''
                    ).lower()
                    for w in ('death', 'died', 'dying', 'dead', 'killed', 'perished', 'fatal')
                )
                for e in evidence
            )
            if not death_supported:
                new_desc = _death_phrase_re.sub('', desc).strip()
                new_desc = re.sub(r'\s{2,}', ' ', new_desc)
                if new_desc != desc:
                    logger.info(
                        f"Evidence-based death removal for '{char.canonical_name}': "
                        f"'in death' not supported by profile evidence — removed"
                    )
                    char.description = new_desc

    def correct_description_relationships(self, characters, source_text: str) -> None:
        """Correct hallucinated relationship terms in descriptions.

        If a character's description prose uses a family relationship term
        (in possessive form) that does NOT appear in the raw text near that
        character's name mentions, replace it with the most-common relationship
        term found in the raw text near those mentions.
        """
        if not source_text:
            return

        name_patterns = _build_name_patterns(characters)
        near_window = 300

        for char in characters:
            desc = getattr(char, 'description', '') or ''
            if not desc:
                continue
            pat = name_patterns.get(char.canonical_name)
            if pat is None:
                continue

            desc_family_terms = [
                t for t in FAMILY_TERMS
                if re.search(r'\b' + re.escape(t) + r'\b', desc, re.IGNORECASE)
            ]
            if not desc_family_terms:
                continue

            nearby_rel_counts: dict = {}
            for match in pat.finditer(source_text):
                ws = max(0, match.start() - near_window)
                we = min(len(source_text), match.end() + near_window)
                window = source_text[ws:we]
                for rm in _rel_phrase_re.finditer(window):
                    term = rm.group(1).lower()
                    nearby_rel_counts[term] = nearby_rel_counts.get(term, 0) + 1
            if not nearby_rel_counts:
                continue

            modified = desc
            for dt in desc_family_terms:
                if not re.search(r'\b' + re.escape(dt) + r"'s\b", modified, re.IGNORECASE):
                    continue
                if dt in nearby_rel_counts:
                    continue
                best_raw_term = max(nearby_rel_counts, key=nearby_rel_counts.get)
                new_d = re.sub(
                    r'\b' + re.escape(dt) + r"'s\b",
                    best_raw_term + "'s",
                    modified,
                    flags=re.IGNORECASE,
                )
                if new_d != modified:
                    logger.info(
                        f"Desc text rel correction for '{char.canonical_name}': "
                        f"'{dt}\\'s' → '{best_raw_term}\\'s' "
                        f"(raw text counts near character: {nearby_rel_counts})"
                    )
                    modified = new_d
            if modified != desc:
                char.description = modified

    def _summarize_evidence(self, name: str) -> str:
        """Build summary context string from evidence store."""
        ev = self._evidence_store.get(name)
        if not ev or not getattr(ev, "evidence", None):
            return "(no summary evidence available)"
        lines = [
            f"- Chapter {e.chapter_index}: {e.statement}"
            for e in ev.evidence[:6]
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Phase B: Output Character corrections
# ---------------------------------------------------------------------------

class OutputCharacterCorrector:
    """Post-processing corrections on output Character objects (Pydantic).

    Runs after _convert_characters(), before building the final AnalysisResult.
    """

    def __init__(self, llm_client=None):
        self._llm = llm_client

    def run_all(self, characters, source_text: str, chapter_summaries: list = None) -> None:
        """Run all Phase B corrections in order. Mutates characters in place."""
        self.inject_narrator_appearance_final(characters, source_text)
        self.extract_deterministic_age(characters, source_text)
        self.clean_unknown_appearance(characters)
        self.clean_plot_summary_personality(characters, source_text)
        self.propagate_physical_description(characters, source_text)
        self.extract_relationships_from_evidence(characters)
        # Add "associated" for high-co-occurrence pairs that still lack any relationship.
        # Runs after evidence mining so only genuinely missing pairs are filled.
        # Runs before verify_relationships_from_text so text evidence can upgrade
        # "associated" to a more specific family term when available.
        if chapter_summaries:
            self.add_cooccurrence_relationships(characters, chapter_summaries)
        self.clean_orphaned_relationships(characters)
        self.fix_same_person_relationships(characters)
        self.verify_relationships_from_text(characters, source_text)
        self.reject_unfounded_familial_labels(characters, source_text)
        self.reject_unfounded_romantic_labels(characters, source_text)
        # fix_bidirectional_parent_labels must run AFTER verify_relationships_from_text,
        # which overrides relationships based on text evidence and can re-introduce
        # bidirectional parent labels (e.g., "father" found near co-mentioned siblings
        # refers to their shared parent, not their relationship to each other).
        self.fix_bidirectional_parent_labels(characters)
        self.enforce_gender_consistency(characters)
        # enforce_inverse_consistency runs after enforce_gender_consistency so that
        # gender corrections are applied before cross-pair validation.
        self.enforce_inverse_consistency(characters)
        self.clean_unknown_relationships(characters)
        # _propagate_missing_reverses must be LAST — it adds reverse labels derived
        # from confirmed relationships (e.g., Margaret→Walton 'sister' → Walton→Margaret
        # 'sister'). Running before enforce_gender_consistency causes the propagated
        # labels to be incorrectly flagged (e.g., male Walton can't be 'sister')
        # and removed by clean_unknown_relationships.
        self._propagate_missing_reverses(characters)

    def extract_relationships_from_evidence(self, characters) -> None:
        """Mine evidence statements to populate missing relationships.

        The profiling LLM often captures character relationships in the evidence
        field as statement text (e.g., "Has a romantic history with Jay Gatsby")
        but fails to surface them in the relationships dict. This method scans
        each character's evidence statements for co-mentions of other cast
        members and infers a relationship type from universal indicator words.

        Universal invariant: a character mentioned in another character's evidence
        statement is at minimum "associated" with that character.
        """
        _ROMANTIC_WORDS = frozenset({
            "romantic", "affair", "loves", "love", "passion", "longing", "intimate",
        })
        _RIVAL_WORDS = frozenset({
            "rival", "rivals", "rivalry", "opposes", "opposition",
        })
        _ENEMY_WORDS = frozenset({
            "enemy", "enemies", "hates", "hatred",
        })
        _NEIGHBOR_WORDS = frozenset({
            "neighbor", "next door", "next to", "lives near",
        })

        def _infer_rel(stmt: str) -> str:
            sl = stmt.lower()
            if any(w in sl for w in _ROMANTIC_WORDS):
                return "romantic interest"
            if any(w in sl for w in _RIVAL_WORDS):
                return "rival"
            if any(w in sl for w in _ENEMY_WORDS):
                return "enemy"
            if any(w in sl for w in _NEIGHBOR_WORDS):
                return "neighbor"
            # Check kinship/family terms (longest first to avoid "son" matching inside "grandson").
            # Allow optional -s/-es suffix to catch plural forms ("cousins", "brothers", etc.)
            for term in sorted(FAMILY_TERMS, key=len, reverse=True):
                if re.search(r'\b' + re.escape(term) + r'(?:s|es)?\b', sl):
                    return term
            return "associated"

        # Generic labels that evidence mining may upgrade to something more specific.
        _generic_rels = frozenset({"associated", "acquaintance", "associate", "unknown", ""})

        for char in characters:
            evidence = getattr(char, 'evidence', None) or []
            rels = getattr(char, 'relationships', None)
            if rels is None:
                rels = {}
            if not isinstance(rels, dict):
                continue

            changed = False
            for ev in evidence:
                if not isinstance(ev, dict):
                    continue
                stmt = ev.get('statement', '') or ''
                if not isinstance(stmt, str) or not stmt:
                    continue

                for other in characters:
                    if other is char:
                        continue
                    other_name = other.canonical_name
                    # Skip only if a specific (non-generic) relationship is already known.
                    cur_rel = (rels.get(other_name) or "").lower().strip()
                    if other_name in rels and cur_rel not in _generic_rels:
                        continue
                    # Check canonical name and aliases in the statement text
                    all_names = [other_name] + list(getattr(other, 'aliases', None) or [])
                    for n in all_names:
                        if n and len(n) >= 3 and re.search(
                            r'\b' + re.escape(n) + r'\b', stmt, re.IGNORECASE
                        ):
                            rel_type = _infer_rel(stmt)
                            rels[other_name] = rel_type
                            changed = True
                            logger.info(
                                f"Evidence-inferred relationship: "
                                f"'{char.canonical_name}' → '{other_name}' "
                                f"({rel_type!r}) from: {stmt[:80]!r}"
                            )
                            break

            if changed:
                char.relationships = rels

        # Apply symmetric bidirectional inference for newly added relationships.
        # Covers: "associated", "neighbor", "romantic interest", "rival", "enemy",
        # and other social labels where A→B implies B→A.
        symmetric = _SYMMETRIC_RELATIONSHIPS | frozenset({"associated", "romantic interest"})
        for char_a in characters:
            rels_a = getattr(char_a, 'relationships', None) or {}
            if not isinstance(rels_a, dict):
                continue
            for other_key, label in list(rels_a.items()):
                label_lower = (label or "").lower()
                if label_lower not in symmetric:
                    continue
                char_b = next(
                    (c for c in characters if c.canonical_name == other_key),
                    None,
                )
                if char_b is None:
                    continue
                rels_b = getattr(char_b, 'relationships', None)
                if rels_b is None:
                    rels_b = {}
                    char_b.relationships = rels_b
                if not isinstance(rels_b, dict):
                    continue
                existing = rels_b.get(char_a.canonical_name)
                # Add if missing, or upgrade from generic "associated" to a
                # more specific type inferred from the other side.
                if existing is None or (
                    existing.lower() == "associated" and label.lower() != "associated"
                ):
                    rels_b[char_a.canonical_name] = label
                    logger.info(
                        f"Symmetric inference: '{char_b.canonical_name}' → "
                        f"'{char_a.canonical_name}' ({label!r})"
                    )

    def add_cooccurrence_relationships(
        self, characters, chapter_summaries: list, min_shared: int = 3
    ) -> None:
        """Add 'associated' for character pairs that co-appear in many chapter summaries
        but currently have no relationship entry in either direction.

        Universal invariant: if A and B appear together in 3+ chapter summaries they
        genuinely share narrative space and at minimum "associated" is a factually safe
        label.  Only adds — never changes existing relationships.  verify_relationships_from_text
        (which runs after this) can upgrade "associated" to a more specific family term
        when the source text provides explicit evidence.

        Args:
            min_shared: Minimum number of shared chapter summaries to trigger enrichment.
        """
        if not chapter_summaries:
            return

        # Build name patterns for all characters
        name_patterns = _build_name_patterns(characters)

        # For each character, collect the set of summary indices where they appear
        char_summary_presence: dict[str, set[int]] = {}
        for char in characters:
            pat = name_patterns.get(char.canonical_name)
            if pat is None:
                char_summary_presence[char.canonical_name] = set()
                continue
            presence: set[int] = set()
            for idx, summary in enumerate(chapter_summaries):
                if summary and pat.search(summary):
                    presence.add(idx)
            char_summary_presence[char.canonical_name] = presence

        # Check all pairs
        for i, char_a in enumerate(characters):
            for j, char_b in enumerate(characters):
                if j <= i:
                    continue

                # Skip if relationship already exists in either direction.
                # Use 'or {}' only for the read-only existence check — an empty dict
                # is semantically equivalent to "no relationships" for skip purposes.
                rels_a_check = getattr(char_a, 'relationships', None) or {}
                rels_b_check = getattr(char_b, 'relationships', None) or {}
                if char_b.canonical_name in rels_a_check or char_a.canonical_name in rels_b_check:
                    continue

                # Count shared summaries
                shared = char_summary_presence.get(char_a.canonical_name, set()) & \
                         char_summary_presence.get(char_b.canonical_name, set())
                if len(shared) < min_shared:
                    continue

                # Add "associated" bidirectionally.
                # Write directly to char.relationships (not a temp 'or {}' copy) so that
                # characters with an empty relationships dict are correctly updated.
                if not isinstance(getattr(char_a, 'relationships', None), dict):
                    char_a.relationships = {}
                if not isinstance(getattr(char_b, 'relationships', None), dict):
                    char_b.relationships = {}
                char_a.relationships[char_b.canonical_name] = "associated"
                char_b.relationships[char_a.canonical_name] = "associated"
                logger.info(
                    f"Co-occurrence relationship: '{char_a.canonical_name}' ↔ "
                    f"'{char_b.canonical_name}': 'associated' ({len(shared)} shared summaries)"
                )

    def enrich_zero_relationships_from_summaries(self, characters, chapter_summaries: list) -> None:
        """Mine chapter summaries to populate relationships for zero-relationship characters.

        The LLM profile generator sometimes fails to produce relationship entries for
        characters even when those relationships are explicit in chapter summaries.
        This method scans summaries for character name co-mentions near family/social
        relationship terms and infers the relationship.

        Universal invariant: if character A and B co-appear in a chapter summary near
        a possessive relationship phrase ("his wife X", "her brother Y"), that
        relationship is real and should be recorded.
        """
        if not chapter_summaries:
            return

        zero_rel_chars = [c for c in characters if not getattr(c, 'relationships', None)]
        if not zero_rel_chars:
            return

        summary_text = "\n\n".join(s for s in chapter_summaries if s)
        if not summary_text:
            return

        name_patterns = _build_name_patterns(characters)
        char_by_name = {c.canonical_name: c for c in characters}
        co_window = 300

        for char in zero_rel_chars:
            pat_a = name_patterns.get(char.canonical_name)
            if pat_a is None:
                continue

            found: dict = {}  # other_canonical_name → {rel_term: count}

            for ma in pat_a.finditer(summary_text):
                ws = max(0, ma.start() - co_window)
                we = min(len(summary_text), ma.end() + co_window)
                win = summary_text[ws:we]

                for other in characters:
                    if other is char:
                        continue
                    pat_b = name_patterns.get(other.canonical_name)
                    if pat_b is None or not pat_b.search(win):
                        continue

                    for rm in _rel_phrase_re.finditer(win):
                        term = rm.group(1).lower()
                        key = other.canonical_name
                        if key not in found:
                            found[key] = {}
                        found[key][term] = found[key].get(term, 0) + 1

            if found:
                rels = {}
                for other_name, term_counts in found.items():
                    best_term = max(term_counts, key=term_counts.get)
                    rels[other_name] = best_term
                    logger.info(
                        f"Summary-inferred relationship: "
                        f"'{char.canonical_name}' → '{other_name}': '{best_term}'"
                    )
                char.relationships = rels

        # Propagate reverse relationships from newly enriched characters to others
        for char_a in zero_rel_chars:
            rels_a = getattr(char_a, 'relationships', None) or {}
            if not rels_a:
                continue
            for other_name, rel_label in list(rels_a.items()):
                rel_lower = (rel_label or "").lower()
                reverse_rel = RELATIONSHIP_REVERSES.get(rel_lower)
                if not reverse_rel and rel_lower in _SYMMETRIC_RELATIONSHIPS:
                    reverse_rel = rel_lower
                if not reverse_rel:
                    continue
                char_b = char_by_name.get(other_name)
                if char_b is None:
                    continue
                rels_b = getattr(char_b, 'relationships', None)
                if rels_b is None:
                    rels_b = {}
                    char_b.relationships = rels_b
                if isinstance(rels_b, dict) and char_a.canonical_name not in rels_b:
                    rels_b[char_a.canonical_name] = reverse_rel
                    logger.info(
                        f"Bidirectional inference from summary enrichment: "
                        f"'{other_name}' → '{char_a.canonical_name}' = '{reverse_rel}'"
                    )

    def fix_bidirectional_parent_labels(self, characters) -> None:
        """Correct bidirectional same-parent labels using a surname heuristic.

        If A→B = 'parent' AND B→A = 'parent' (or any identical parent term),
        they cannot both be each other's parent. The correction depends on
        whether they share a surname:
        - Shared surname → 'sibling' (same generation, same family)
        - No shared surname → 'associated' (direction unknown, neutral fallback)

        Universal invariant: bidirectional identical parent labels are logically
        impossible and indicate a LLM error. Text-evidence methods
        (verify_relationships_from_text) run before this and should already have
        upgraded correct directional labels where evidence exists.
        """
        _PARENT_LABELS = frozenset({"father", "mother", "parent"})
        _skip_titles = {"jr.", "sr.", "jr", "sr", "ii", "iii", "iv",
                        "md", "phd", "dr", "mr", "mrs", "ms", "miss"}
        char_by_name = {c.canonical_name: c for c in characters}

        def _surnames(name: str) -> set:
            parts = name.split()
            if len(parts) <= 1:
                return set()
            return {
                p.lower().strip("().,")
                for p in parts[1:]
                if len(p.strip("().,")) > 2 and p.lower().strip("().,") not in _skip_titles
            }

        seen_pairs: set = set()
        for char_a in characters:
            rels_a = getattr(char_a, 'relationships', None)
            if not rels_a:
                continue
            for other_name, rel_a in list(rels_a.items()):
                rel_a_lower = (rel_a or "").strip().lower()
                if rel_a_lower not in _PARENT_LABELS:
                    continue

                pair = frozenset({char_a.canonical_name, other_name})
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)

                char_b = char_by_name.get(other_name)
                if char_b is None:
                    continue
                rels_b = getattr(char_b, 'relationships', None)
                if not rels_b:
                    continue
                rel_b = rels_b.get(char_a.canonical_name, "")
                rel_b_lower = (rel_b or "").strip().lower()

                if rel_b_lower in _PARENT_LABELS:
                    # Determine correction: shared surname → siblings; otherwise → associated
                    surnames_a = _surnames(char_a.canonical_name)
                    surnames_b = _surnames(other_name)
                    if surnames_a and surnames_b and (surnames_a & surnames_b):
                        correction = "sibling"
                    else:
                        correction = "associated"
                    rels_a[other_name] = correction
                    rels_b[char_a.canonical_name] = correction
                    logger.info(
                        f"Bidirectional parent label corrected to '{correction}': "
                        f"'{char_a.canonical_name}' ↔ '{other_name}' "
                        f"(was '{rel_a}'/'{rel_b}')"
                    )

    def _propagate_missing_reverses(self, characters) -> None:
        """Propagate missing reverse relationships using RELATIONSHIP_REVERSES.

        After all verify/reject/fix passes, some relationships are one-directional
        (e.g., Margaret→Walton 'sister' but Walton→Margaret missing). This method
        adds the reverse label when:
        - A→B has a known label
        - RELATIONSHIP_REVERSES defines the reverse (or the label is symmetric)
        - B→A does not yet exist

        Universal invariant: if A's profile explicitly records a relationship to B,
        B's profile should record the reciprocal. Only adds — never overwrites.
        """
        char_by_name = {c.canonical_name: c for c in characters}
        for char_a in characters:
            rels_a = getattr(char_a, 'relationships', None) or {}
            for other_name, rel_label in list(rels_a.items()):
                if not isinstance(rel_label, str):
                    continue
                rel_lower = rel_label.strip().lower()
                reverse_rel = RELATIONSHIP_REVERSES.get(rel_lower)
                if not reverse_rel and rel_lower in _SYMMETRIC_RELATIONSHIPS:
                    reverse_rel = rel_lower
                if not reverse_rel:
                    continue
                char_b = char_by_name.get(other_name)
                if char_b is None:
                    continue
                rels_b = getattr(char_b, 'relationships', None)
                if rels_b is None:
                    rels_b = {}
                    char_b.relationships = rels_b
                if isinstance(rels_b, dict) and char_a.canonical_name not in rels_b:
                    rels_b[char_a.canonical_name] = reverse_rel
                    logger.info(
                        f"Propagated missing reverse: "
                        f"'{other_name}' → '{char_a.canonical_name}' = '{reverse_rel}'"
                    )

    def propagate_physical_description(self, characters, source_text: str = "") -> None:
        """Copy appearance.summary to physical_description when the latter is absent.

        Falls back to joining distinguishing_features when summary is null, and then
        to an LLM call focused on the character's first appearance in the source text
        for major characters (>50 mentions) that still have no description.

        Authors typically describe characters physically when they first appear on the
        page, so the first-appearance context is the most reliable source for physical
        descriptions and avoids cross-contamination from nearby characters introduced
        later in the same scene.
        """
        _skip = {"", "unknown", "not described", "no physical description available in text."}
        needs_llm: list = []
        for char in characters:
            if getattr(char, "physical_description", None):
                continue  # already set
            app = getattr(char, "appearance", None) or {}
            if not isinstance(app, dict):
                continue
            summary = (app.get("summary", "") or "").strip()
            if summary and summary.lower() not in _skip:
                char.physical_description = summary
                continue
            # Fall back: build from distinguishing_features when summary is absent
            features = app.get("distinguishing_features") or []
            if isinstance(features, list):
                valid = [f.strip() for f in features if isinstance(f, str) and f.strip()]
                if valid:
                    char.physical_description = "; ".join(valid).capitalize() + "."
                    continue
            # Collect major characters that still need a description
            if source_text and getattr(char, "mention_count", 0) > 50:
                needs_llm.append(char)

        # LLM fallback: extract physical descriptions from first-appearance context.
        if needs_llm and self._llm:
            all_names = [c.canonical_name for c in characters]
            for char in needs_llm:
                desc = self._llm_first_appearance_description(
                    char, source_text, all_names,
                )
                if desc:
                    char.physical_description = desc
                    # Also populate appearance.summary so downstream consumers see it
                    app = getattr(char, "appearance", None)
                    if isinstance(app, dict) and not app.get("summary"):
                        app["summary"] = desc
                    logger.info(
                        f"LLM first-appearance description for "
                        f"'{char.canonical_name}': {desc!r}"
                    )
        elif needs_llm:
            logger.info(
                f"No LLM client available for first-appearance description "
                f"fallback ({len(needs_llm)} characters need descriptions)"
            )

    def _llm_first_appearance_description(
        self, char, source_text: str, all_character_names: list[str],
    ) -> str:
        """Extract physical description from a character's first appearance.

        Finds the earliest mention of the character in the source text and sends
        the surrounding context to the LLM with a focused extraction prompt.
        Authors typically describe characters physically when they first appear,
        making this the most reliable source for accurate, uncontaminated descriptions.
        """
        names = [char.canonical_name]
        if hasattr(char, "aliases") and char.aliases:
            names.extend(a for a in char.aliases if isinstance(a, str) and a.strip())

        # Compute last-name tokens of other characters to filter ambiguous single-word aliases.
        # E.g., "Buchanan" is Daisy's alias but also Tom Buchanan's last name — using it as a
        # search anchor would find Tom's first appearance, not Daisy's.
        other_last_tokens: set[str] = set()
        for other_name in all_character_names:
            if other_name == char.canonical_name:
                continue
            parts = other_name.strip().split()
            if parts:
                other_last_tokens.add(parts[-1].lower())

        filtered_names = [
            n for n in names
            if len(n.split()) > 1  # multi-word names are never ambiguous
            or n.lower() not in other_last_tokens  # single-word name not shared with another char
        ]
        if not filtered_names:
            filtered_names = names  # safety fallback

        # Find the occurrence with the most physical-word context across unambiguous
        # name variants. Authors often introduce a character by name before describing
        # them physically, so the first mention may have no physical context while a
        # later one does. We score up to 5 occurrences per name by counting physical
        # descriptor words in the surrounding 800-char window, then use the best-
        # scoring position (tie-broken by earliest position for stability).
        best_pos = len(source_text)
        best_score = -1
        best_name = char.canonical_name
        for name in filtered_names:
            if not name or len(name) < 2:
                continue
            pat = re.compile(r"\b" + re.escape(name) + r"\b", re.IGNORECASE)
            for idx, m in enumerate(pat.finditer(source_text)):
                if idx >= 5:
                    break
                ctx_s = max(0, m.start() - 200)
                ctx_e = min(len(source_text), m.start() + 800)
                score = _physical_descriptor_score(source_text[ctx_s:ctx_e])
                if score > best_score or (score == best_score and m.start() < best_pos):
                    best_score = score
                    best_pos = m.start()
                    best_name = name

        if best_pos >= len(source_text):
            return ""

        # Extract a generous window around the best appearance.
        # Bias forward (more text after the name) since descriptions follow introductions.
        ctx_start = max(0, best_pos - 500)
        ctx_end = min(len(source_text), best_pos + 1500)
        context = source_text[ctx_start:ctx_end]

        # Clean up partial words at boundaries
        if ctx_start > 0:
            context = "..." + (context.split(" ", 1)[-1] if " " in context else context)
        if ctx_end < len(source_text):
            context = (context.rsplit(" ", 1)[0] if " " in context else context) + "..."

        # Build list of other characters for disambiguation
        others = [n for n in all_character_names if n != char.canonical_name]

        prompt = (
            f"Below is a passage from a novel surrounding the first appearance of "
            f'the character "{char.canonical_name}"'
        )
        if len(names) > 1:
            aliases = ", ".join(f'"{a}"' for a in names[1:])
            prompt += f" (also known as {aliases})"
        prompt += (
            f".\n\nOther characters in this story: {', '.join(others[:15])}\n\n"
            f"PASSAGE:\n{context}\n\n"
            f"Extract ONLY the physical description of \"{char.canonical_name}\" "
            f"from this passage. Include details like build, height, age, hair, "
            f"eyes, complexion, clothing, and any distinctive physical features.\n\n"
            f"RULES:\n"
            f"- Only describe \"{char.canonical_name}\", not any other character\n"
            f"- Use only details explicitly stated in the passage\n"
            f"- Write a concise 1-3 sentence description\n"
            f"- If the passage contains no physical description of this character, "
            f"respond with exactly: NONE"
        )

        try:
            response = self._llm.query(prompt, temperature=0.1, max_tokens=256)
            if not response.success:
                logger.warning(
                    f"LLM first-appearance query failed for "
                    f"'{char.canonical_name}': {response.error}"
                )
                return ""
            text = response.content.strip()
            if not text or text.upper() == "NONE" or "none" == text.lower():
                return ""
            # Filter out responses that are just negations
            if any(phrase in text.lower() for phrase in NO_DESC_PHRASES):
                return ""
            # Truncate overly long responses
            if len(text) > 400:
                text = text[:400].rsplit(" ", 1)[0] + "..."
            return text
        except Exception as e:
            logger.warning(
                f"LLM first-appearance extraction error for "
                f"'{char.canonical_name}': {e}"
            )
            return ""

    def inject_narrator_appearance_final(self, characters, source_text: str) -> None:
        """Final narrator appearance injection (guaranteed-last pass).

        Runs AFTER _convert_characters so no subsequent step can overwrite it.
        Any first-person narrator who physically self-describes in text gets
        that description injected regardless of what the LLM generated.
        Only injects when the extracted text is a compact physical description,
        not narrative prose that happens to mention a physical word.
        """
        for char in characters:
            if not getattr(char, 'is_narrator', False):
                continue
            app = getattr(char, 'appearance', None)
            if app is None:
                continue

            best_match, best_score, is_pb = _find_best_narrator_match(source_text)

            if best_match is None or best_score < 2:
                logger.info(
                    f"Final narrator injection: no strong physical description found for "
                    f"'{char.canonical_name}' (best score={best_score})"
                )
                continue

            cleaned = _extract_narrator_description(best_match, source_text, is_pb)
            if cleaned and _is_compact_physical_description(cleaned):
                char.appearance["summary"] = cleaned
                print(
                    f"   Final narrator appearance injection for "
                    f"'{char.canonical_name}': {cleaned!r}"
                )
                logger.info(
                    f"Final narrator appearance injection for "
                    f"'{char.canonical_name}': {cleaned!r}"
                )
                desc_lower = best_match.group().lower()
                if (app.get("age_indication", "") or "").lower() in ("", "unknown"):
                    if any(w in desc_lower for w in ("elderly", "old", "aged")):
                        char.appearance["age_indication"] = "elderly"
                    elif "young" in desc_lower:
                        char.appearance["age_indication"] = "young"
            elif cleaned:
                logger.info(
                    f"Final narrator injection skipped: sparse description "
                    f"for '{char.canonical_name}': {cleaned[:60]!r}"
                )

    # Valid age category words that do not require pattern matching
    _VALID_AGE_CATEGORIES = frozenset({
        "elderly", "old", "young", "middle-aged", "middle aged",
        "adult", "child", "teen", "adolescent", "infant", "baby",
        "toddler", "newborn",
    })

    def _is_valid_age_indication(self, age: str) -> bool:
        """Return True if age_indication is a recognizable age description.

        Rejects ambiguous values like "five years" or "nine years" (number-word +
        "years" without an explicit "old" qualifier) which are often hallucinated
        from context clues like "five survivors" rather than genuine age mentions.
        Written-number age forms must include "old" (e.g., "five years old"),
        while numeric forms are accepted with or without "old".
        """
        if not age:
            return False
        age_lower = age.strip().lower()
        if age_lower in ("", "unknown"):
            return False
        if age_lower in self._VALID_AGE_CATEGORIES:
            return True
        # Use strict pattern: written-number forms require "old" qualifier
        return bool(_strict_age_validate_pat.search(age))

    def extract_deterministic_age(self, characters, source_text: str) -> None:
        """Extract explicit age mentions from text near character names.

        For any character whose age_indication is still unknown or invalid, search
        the raw source text for explicit age mentions. Handles both numeric forms
        ("22 years old") and written-out forms ("twenty-two years old").

        Also resets hallucinated age values like "five years" (typically a count
        of survivors/objects, not a true age) so the deterministic search can
        supply a correct value.
        """
        for char in characters:
            app = getattr(char, 'appearance', None)
            if app is None:
                continue
            current_age = (app.get("age_indication", "") or "").strip()
            if self._is_valid_age_indication(current_age):
                continue
            if current_age and current_age.lower() not in ("", "unknown"):
                logger.info(
                    f"Resetting invalid age_indication '{current_age}' "
                    f"for '{char.canonical_name}' (not a recognizable age)"
                )
                app["age_indication"] = "unknown"

            names = [char.canonical_name] + list(char.aliases or [])
            age_found = None
            for name in names:
                if not name or len(name) < 2:
                    continue
                for nm in re.finditer(re.escape(name), source_text, re.IGNORECASE):
                    window = source_text[max(0, nm.start() - 50):min(len(source_text), nm.end() + 300)]
                    am = _age_extract_pat.search(window)
                    if am:
                        age_found = am.group().strip()
                        break
                if age_found:
                    break
            if age_found:
                char.appearance["age_indication"] = age_found
                logger.info(
                    f"Deterministic age extraction: '{char.canonical_name}' → '{age_found}'"
                )

    def clean_unknown_appearance(self, characters) -> None:
        """Clear appearance fields whose value is a placeholder like 'unknown'.

        When the LLM cannot describe a character it emits 'unknown', 'Unknown',
        'not described', etc.  These are noise — rendering "unknown" in the HTML
        provides no narrator guidance.  Clearing them lets the template skip the
        section entirely.  Universal invariant: absence of data is better than
        obviously-empty placeholder text.
        """
        _placeholder = frozenset({
            "", "unknown", "not described", "no physical description",
            "no description", "n/a", "none",
        })
        other_names_by_char = {
            c.canonical_name: {o.canonical_name for o in characters if o is not c}
            for c in characters
        }
        for char in characters:
            app = getattr(char, 'appearance', None)
            if not app:
                continue
            for key in ("summary", "age_indication", "distinguishing_features"):
                val = app.get(key)
                if not isinstance(val, str):
                    continue
                val_lower = val.strip().lower()
                if val_lower in _placeholder:
                    app[key] = None
                    logger.info(
                        f"Cleared placeholder appearance.{key}='{val}' for '{char.canonical_name}'"
                    )
                    continue
                # Also clear summary fields that explicitly state the character is not
                # described — the LLM sometimes wraps a long explanation around a denial
                # ("X is not directly described in the text; however her sister Y is...").
                # NO_DESC_PHRASES uses substring matching to catch these multi-sentence values.
                if key == "summary" and any(phrase in val_lower for phrase in NO_DESC_PHRASES):
                    app[key] = None
                    logger.info(
                        f"Cleared self-negating appearance.summary for '{char.canonical_name}': "
                        f"{val[:80]!r}"
                    )
                    continue
                # Remove cross-character attribution clauses: "(as described by X)" where X is
                # another cast member signals that the feature belongs to X, not this character.
                # Universal invariant: descriptions must describe THIS character only.
                if key == "summary":
                    others = other_names_by_char.get(char.canonical_name, set())
                    cleaned = _strip_attribution_clauses(val, others)
                    if cleaned != val:
                        new_val = cleaned.strip('; ').strip() or None
                        app[key] = new_val
                        logger.info(
                            f"Removed attribution clause from appearance.summary for "
                            f"'{char.canonical_name}': {val[:80]!r} → {str(new_val)[:80]!r}"
                        )

    def clean_orphaned_relationships(self, characters) -> None:
        """Remove relationship entries that reference characters not in the final list.

        When a character is removed from the output (e.g., filtered by the evidence
        gate, deduplication, or any post-processing step), references to that
        character in other characters' relationship dicts become orphaned. This
        method removes those orphaned entries.

        Universal: enforces the invariant that relationships only reference
        characters present in the final output.
        """
        canonical_names_lower = {c.canonical_name.lower() for c in characters}
        alias_to_canonical: dict = {}
        for c in characters:
            for alias in (getattr(c, 'aliases', None) or []):
                alias_to_canonical[alias.lower()] = c.canonical_name

        for char in characters:
            rels = getattr(char, 'relationships', None)
            if not rels:
                continue
            to_remove = [
                other_name
                for other_name in list(rels.keys())
                if other_name.lower() not in canonical_names_lower
                and other_name.lower() not in alias_to_canonical
            ]
            for name in to_remove:
                del rels[name]
                logger.info(
                    f"Cleaned orphaned relationship: '{char.canonical_name}' → '{name}' "
                    f"removed (character not in final list)"
                )

    def fix_same_person_relationships(self, characters) -> None:
        """Clear 'same person' relationships between distinct characters.

        Two distinct characters can never be "same person". If the LLM
        erroneously labels character A as the same person as character B,
        clear the relationship to "unknown".
        """
        names_lower = {c.canonical_name.lower() for c in characters}
        alias_to_canonical = {}
        for c in characters:
            for alias in (c.aliases or []):
                alias_to_canonical[alias.lower()] = c.canonical_name.lower()

        for char in characters:
            if not char.relationships:
                continue
            for other_name, rel_desc in list(char.relationships.items()):
                if not rel_desc:
                    continue
                rel_lower = rel_desc.lower()
                if not any(phrase in rel_lower for phrase in SAME_PERSON_PHRASES):
                    continue
                other_lower = other_name.lower()
                in_list = (
                    other_lower in names_lower
                    or other_lower in alias_to_canonical
                )
                if in_list:
                    char.relationships[other_name] = "unknown"
                    logger.info(
                        f"Corrected 'same person' relationship: "
                        f"'{char.canonical_name}' → '{other_name}' = '{rel_desc}' → 'unknown'"
                    )

    def verify_relationships_from_text(self, characters, source_text: str) -> None:
        """Override LLM relationships with text-evidenced terms.

        For each character pair, searches source text for explicit relationship
        phrases in windows where both characters co-appear. When the text
        explicitly states a relationship that differs from the LLM-generated
        one, the LLM value is overridden. When the LLM claims a family
        relationship but the characters never co-appear, it is downgraded
        to "acquaintance".
        """
        if not source_text:
            return

        family_set = set(FAMILY_TERMS)
        name_patterns = _build_name_patterns(characters)
        co_window = 500

        for char in characters:
            if not char.relationships:
                continue
            pat_a = name_patterns.get(char.canonical_name)
            if pat_a is None:
                continue

            for other_key in list(char.relationships.keys()):
                cur = char.relationships.get(other_key) or ""
                if not cur:
                    continue
                cur_lower = cur.lower()
                is_family = any(t in cur_lower for t in family_set)

                other_char = next(
                    (c for c in characters
                     if c.canonical_name == other_key
                     or c.canonical_name.lower() == other_key.lower()
                     or other_key in (c.aliases or [])
                     or other_key.lower() in [a.lower() for a in (c.aliases or [])]),
                    None,
                )
                if other_char is None:
                    continue
                pat_b = name_patterns.get(other_char.canonical_name)
                if pat_b is None:
                    continue

                found: dict = {}
                comention_count = 0
                for ma in pat_a.finditer(source_text):
                    ws = max(0, ma.start() - co_window)
                    we = min(len(source_text), ma.end() + co_window)
                    win = source_text[ws:we]
                    if not pat_b.search(win):
                        continue
                    comention_count += 1
                    for rm in _all_rel_phrase_re.finditer(win):
                        term = rm.group(1).lower()
                        found[term] = found.get(term, 0) + 1

                _generic_labels = {"associated", "acquaintance", "associate"}
                # Tier sets for cross-tier override guard (universal invariant).
                _PARENT_CHILD_TIER = {"parent", "child", "father", "mother", "son", "daughter"}
                _SPOUSAL_TIER = {"spouse", "husband", "wife"}
                if found:
                    best = max(found, key=found.get)
                    is_best_family = any(t in best for t in family_set)
                    if best not in cur_lower:
                        if is_best_family or cur_lower in _generic_labels:
                            # Universal invariant: never override a parent/child label with a
                            # spousal label based on co-mention window evidence. A "his wife"
                            # phrase in a parent-child co-mention window refers to the parent's
                            # marriage, not the parent-child relationship itself.
                            cur_is_pc = any(t in cur_lower for t in _PARENT_CHILD_TIER)
                            best_is_spousal = any(t in best for t in _SPOUSAL_TIER)
                            if cur_is_pc and best_is_spousal:
                                logger.debug(
                                    f"Cross-tier override blocked: "
                                    f"'{char.canonical_name}' → '{other_key}': "
                                    f"'{cur}' (parent/child) not replaced by "
                                    f"'{best}' (spousal) — co-mention window "
                                    f"evidence belongs to a different pair"
                                )
                            else:
                                # Family evidence: override any label (e.g., "brother" → "cousin"
                                # when text confirms "cousin"). Generic labels: upgrade to any term.
                                logger.info(
                                    f"Text-based rel override: '{char.canonical_name}' → '{other_key}': "
                                    f"'{cur}' → '{best}' (evidence: {found})"
                                )
                                char.relationships[other_key] = best
                        elif (
                            cur_lower not in _generic_labels
                            and not is_family
                            and found.get(cur_lower, 0) == 0
                            and comention_count <= 1
                        ):
                            # Specific non-family label with no corroborating text evidence AND
                            # very low co-occurrence: likely hallucinated.
                            # Universal invariant: if the specific label never appears in any
                            # co-mention window AND the characters barely share the text, the
                            # relationship was not established in this book.
                            logger.info(
                                f"Hallucinated specific rel downgraded (no evidence, co-occ={comention_count}): "
                                f"'{char.canonical_name}' → '{other_key}': '{cur}' → 'associated'"
                            )
                            char.relationships[other_key] = "associated"
                elif is_family and comention_count == 0:
                    # Skip downgrade when either character is a first-person narrator.
                    # Narrator names rarely appear in raw text (the narrator uses "I"),
                    # so co-occurrence analysis is unreliable for their relationships.
                    # This is a universal invariant: applies to any first-person narrative.
                    if getattr(char, 'is_narrator', False) or getattr(other_char, 'is_narrator', False):
                        logger.debug(
                            f"Family rel kept (narrator involved, co-mention unreliable): "
                            f"'{char.canonical_name}' → '{other_key}': '{cur}'"
                        )
                    else:
                        logger.info(
                            f"Hallucinated family rel downgraded: "
                            f"'{char.canonical_name}' → '{other_key}': '{cur}' → 'acquaintance'"
                        )
                        char.relationships[other_key] = "acquaintance"
                elif not is_family and comention_count == 0 and cur_lower not in _generic_labels:
                    # Specific non-family label between characters with zero raw-text co-occurrence.
                    logger.info(
                        f"Hallucinated specific rel downgraded (zero co-occurrence): "
                        f"'{char.canonical_name}' → '{other_key}': '{cur}' → 'associated'"
                    )
                    char.relationships[other_key] = "associated"

    def clean_plot_summary_personality(self, characters, source_text: str = "") -> None:
        """Replace personality.summary that narrates other characters' actions.

        Universal invariant: personality.summary must describe THIS character's
        traits and psychology, not what other characters are doing. When the
        summary mentions 3+ other cast members (strong signal) — or 2+ other
        cast members AND another character name leads the sentence (medium signal)
        — it is almost certainly a plot-synopsis copy, not a personality profile.

        Replacement: attempts to extract character-subject sentences from source
        text (sentences that START with the character's canonical name). Falls back
        to clearing the summary if no subject sentences are found in the text.
        Clearing (None) is always preferable to retaining a misleading plot dump.
        """
        canonical_names = {c.canonical_name for c in characters}

        # Pre-split source text into candidate sentences once for efficiency.
        # Use sentence-boundary heuristic: split on ". " or "! " or "? " followed
        # by an uppercase letter to avoid splitting mid-sentence abbreviations.
        source_sentences: list[str] = []
        if source_text:
            source_sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', source_text)

        for char in characters:
            personality = getattr(char, 'personality', None)
            if not isinstance(personality, dict):
                continue
            summary = personality.get('summary', '') or ''
            if not summary or len(summary) < 80:
                continue

            # Count other character canonical names mentioned in the summary.
            other_names_found = sum(
                1 for name in canonical_names
                if name != char.canonical_name
                and re.search(r'\b' + re.escape(name) + r'\b', summary, re.IGNORECASE)
            )

            # Strong signal: 3+ other cast member names → almost certainly a plot synopsis.
            # Medium signal: 2+ names AND another character's name leads the summary.
            is_plot_dump = False
            if other_names_found >= 3:
                is_plot_dump = True
            elif other_names_found >= 2:
                other_name_leads = any(
                    re.match(
                        r'^' + re.escape(other) + r'\b',
                        summary.strip(),
                        re.IGNORECASE,
                    )
                    for other in canonical_names
                    if other != char.canonical_name
                )
                if other_name_leads:
                    is_plot_dump = True

            if not is_plot_dump:
                continue

            # Allow through if the character's own name leads the summary
            # (subject-position sentence — already about this character).
            name_leads = bool(re.match(
                r'^' + re.escape(char.canonical_name) + r'\b',
                summary.strip(),
                re.IGNORECASE,
            ))
            if name_leads:
                continue

            # Attempt to replace with character-subject sentences from source text.
            # These sentences start with the character's own name (or possessive),
            # so they directly describe the character's actions/nature.
            name_re_str = r'^' + re.escape(char.canonical_name) + r"(\b|'s?\b)"
            subject_sentences: list[str] = []
            for sent in source_sentences:
                sent = sent.strip()
                if not sent:
                    continue
                if re.match(name_re_str, sent, re.IGNORECASE):
                    subject_sentences.append(sent)
                    if len(subject_sentences) >= 3:
                        break

            if subject_sentences:
                # Quality filter: discard bare-name sentences (e.g. "AM.") and
                # sentences that are clearly too short to be useful.
                name_only_re = re.compile(
                    r'^' + re.escape(char.canonical_name) + r'[.!?,;:\s]*$',
                    re.IGNORECASE,
                )
                quality_sentences = [
                    s for s in subject_sentences
                    if not name_only_re.match(s.strip()) and len(s.strip()) > 20
                ]
                total_len = sum(len(s) for s in quality_sentences)
                if quality_sentences and total_len >= 50:
                    new_summary = ' '.join(quality_sentences)
                    if len(new_summary) > 250:
                        new_summary = new_summary[:250].rsplit(' ', 1)[0] + '…'
                    personality['summary'] = new_summary
                    logger.info(
                        f"Plot-synopsis personality replaced for '{char.canonical_name}': "
                        f"extracted {len(quality_sentences)} subject sentence(s) from source text "
                        f"(was mentioning {other_names_found} other characters)"
                    )
                else:
                    personality['summary'] = None
                    logger.info(
                        f"Plot-synopsis personality cleared for '{char.canonical_name}': "
                        f"subject sentences too short or bare-name-only after quality filtering "
                        f"(was mentioning {other_names_found} other characters)"
                    )
            else:
                personality['summary'] = None
                logger.info(
                    f"Plot-synopsis personality cleared for '{char.canonical_name}': "
                    f"summary mentioned {other_names_found} other characters and no "
                    f"subject sentences found in source text"
                )

    def enforce_gender_consistency(self, characters) -> None:
        """Correct gender-inconsistent relationship labels.

        If a character is clearly male (from descriptions or title), they cannot be
        "mother", "sister", etc. Similarly for female characters.
        """
        # Gender-swap mapping: if a character has a gendered label that contradicts
        # their detected gender, convert to the gender-appropriate equivalent.
        # These mappings are universal in English literature.
        _MALE_TO_FEMALE = {
            "father": "mother",
            "son": "daughter",
            "husband": "wife",
            "brother": "sister",
            "grandfather": "grandmother",
            "grandson": "granddaughter",
            "uncle": "aunt",
            "nephew": "niece",
        }
        _FEMALE_TO_MALE = {v: k for k, v in _MALE_TO_FEMALE.items()}

        for char in characters:
            desc_text = " ".join(
                d.text.lower() for d in (getattr(char, 'descriptions', None) or []) if d.text
            )
            is_male = any(ind in f" {desc_text} " for ind in MALE_INDICATORS)
            is_female = any(ind in f" {desc_text} " for ind in FEMALE_INDICATORS)

            # Also check canonical name for title-based gender (universal convention):
            # "Mr." → male, "Mrs." / "Ms." / "Miss " → female
            name_lower = getattr(char, 'canonical_name', '').lower()
            if not is_male and "mr." in name_lower and "mrs." not in name_lower:
                is_male = True
            if not is_female and any(t in name_lower for t in ("mrs.", "ms.", "miss ")):
                is_female = True

            if not char.relationships:
                continue
            # Neutral kinship labels → gender-specific equivalents (male_form, female_form)
            _NEUTRAL_TO_GENDERED = {
                "parent": ("father", "mother"),
                "child": ("son", "daughter"),
                "sibling": ("brother", "sister"),
                "grandparent": ("grandfather", "grandmother"),
                "grandchild": ("grandson", "granddaughter"),
                "spouse": ("husband", "wife"),
            }
            for other_key, rel_val in list(char.relationships.items()):
                if not rel_val:
                    continue
                rel_lower = rel_val.strip().lower()
                if is_male and not is_female and rel_lower in FEMALE_ONLY_RELS:
                    corrected = _FEMALE_TO_MALE.get(rel_lower, "unknown")
                    logger.info(
                        f"Gender consistency: '{char.canonical_name}' (male) cannot be "
                        f"'{rel_val}' to '{other_key}' — correcting to '{corrected}'"
                    )
                    char.relationships[other_key] = corrected
                elif is_female and not is_male and rel_lower in MALE_ONLY_RELS:
                    corrected = _MALE_TO_FEMALE.get(rel_lower, "unknown")
                    logger.info(
                        f"Gender consistency: '{char.canonical_name}' (female) cannot be "
                        f"'{rel_val}' to '{other_key}' — correcting to '{corrected}'"
                    )
                    char.relationships[other_key] = corrected
                elif rel_lower in _NEUTRAL_TO_GENDERED:
                    male_form, female_form = _NEUTRAL_TO_GENDERED[rel_lower]
                    eff_male, eff_female = is_male, is_female
                    # Tiebreaker for ambiguous gender: check character's own gendered
                    # relationship labels (e.g., "son" → subject is male). This handles
                    # cases where descriptions mention other characters' titles that
                    # create false gender signals.
                    if eff_male and eff_female:
                        own_vals = [
                            v.strip().lower()
                            for v in char.relationships.values()
                            if v and v.strip().lower() != rel_lower
                        ]
                        if any(r in MALE_ONLY_RELS for r in own_vals):
                            eff_female = False
                        elif any(r in FEMALE_ONLY_RELS for r in own_vals):
                            eff_male = False
                    if eff_male and not eff_female:
                        logger.info(
                            f"Gender specialization: '{char.canonical_name}' (male) "
                            f"'{rel_val}' → '{male_form}'"
                        )
                        char.relationships[other_key] = male_form
                    elif eff_female and not eff_male:
                        logger.info(
                            f"Gender specialization: '{char.canonical_name}' (female) "
                            f"'{rel_val}' → '{female_form}'"
                        )
                        char.relationships[other_key] = female_form

    def enforce_inverse_consistency(self, characters) -> None:
        """Correct relationship labels that contradict their known inverse.

        Uses child-perspective labels ("son", "daughter") as the authoritative source
        since children reliably identify their parents.  When B→A exists but contradicts
        the inverse implied by A→B = "son"/"daughter", overwrite B→A with the correct
        gender-appropriate parent label.

        Corrections are collected in a single pass then applied in batch to avoid
        cascading from already-incorrect labels in the same iteration.

        Example: Herbert→Mrs. White = "son" implies Mrs. White→Herbert must be
        "mother" (she is female).  If B→A is "husband" or "wife", it gets corrected.
        """
        # Only child-perspective labels are reliable enough to drive corrections.
        _CHILD_LABELS = {"son", "daughter"}
        # Valid parent labels — if B→A is already a parent label, accept it as-is
        # (enforce_gender_consistency handles any remaining gendering errors).
        _PARENT_LABELS = {"father", "mother", "parent"}

        # Gender detection (mirrors enforce_gender_consistency logic)
        def _gender(char) -> str:
            desc_text = " ".join(
                d.text.lower() for d in (getattr(char, "descriptions", None) or []) if d.text
            )
            is_male = any(ind in f" {desc_text} " for ind in MALE_INDICATORS)
            is_female = any(ind in f" {desc_text} " for ind in FEMALE_INDICATORS)
            name_lower = getattr(char, "canonical_name", "").lower()
            if not is_male and "mr." in name_lower and "mrs." not in name_lower:
                is_male = True
            if not is_female and any(t in name_lower for t in ("mrs.", "ms.", "miss ")):
                is_female = True
            if is_female and not is_male:
                return "female"
            if is_male and not is_female:
                return "male"
            return "unknown"

        char_by_name = {c.canonical_name: c for c in characters}
        gender_cache = {c.canonical_name: _gender(c) for c in characters}

        # Phase 1: collect corrections without modifying relationships yet
        pending: dict = {}  # (parent_name, child_name) → required_parent_label

        for char_a in characters:
            rels_a = getattr(char_a, "relationships", None) or {}
            for other_name, rel_label in list(rels_a.items()):
                if not isinstance(rel_label, str):
                    continue
                rel_lower = rel_label.strip().lower()
                if rel_lower not in _CHILD_LABELS:
                    continue  # only trust child-perspective labels

                char_b = char_by_name.get(other_name)
                if char_b is None:
                    continue
                rels_b = getattr(char_b, "relationships", None) or {}
                current_b_to_a = rels_b.get(char_a.canonical_name)
                if not current_b_to_a:
                    continue  # missing reverse handled by _propagate_missing_reverses

                current_lower = current_b_to_a.strip().lower()
                if current_lower in _PARENT_LABELS:
                    continue  # already a parent label — gender consistency handles it
                if current_lower in _CHILD_LABELS:
                    # Both sides claim to be the child (e.g., A→B = "son", B→A = "son").
                    # fix_bidirectional_parent_labels only handles parent labels, not child labels,
                    # so we resolve direction here using formal title as a universal parent signal.
                    # A character with a formal adult title (Mr./Mrs.) is the parental generation.
                    _parent_titles = ("mr.", "mrs.", "ms.", "miss ", "dr.", "prof.")
                    a_has_title = any(t in char_a.canonical_name.lower() for t in _parent_titles)
                    b_has_title = any(t in other_name.lower() for t in _parent_titles)
                    if a_has_title and not b_has_title:
                        # char_a is the parent; their label toward char_b should be "father"/"mother"
                        a_gender = gender_cache.get(char_a.canonical_name, "unknown")
                        required_a = "mother" if a_gender == "female" else "father" if a_gender == "male" else "parent"
                        pending[(char_a.canonical_name, other_name)] = required_a
                    elif b_has_title and not a_has_title:
                        # char_b is the parent; their label toward char_a should be "father"/"mother"
                        b_gender = gender_cache.get(other_name, "unknown")
                        required_b = "mother" if b_gender == "female" else "father" if b_gender == "male" else "parent"
                        pending[(other_name, char_a.canonical_name)] = required_b
                    # If both or neither have titles, direction is ambiguous; leave unchanged.
                    continue

                # B→A is not a parent label; determine what it should be from B's gender
                b_gender = gender_cache.get(other_name, "unknown")
                if b_gender == "female":
                    required = "mother"
                elif b_gender == "male":
                    required = "father"
                else:
                    required = "parent"

                key = (other_name, char_a.canonical_name)  # (B_name, A_name)
                pending[key] = required

        # Phase 2: apply all collected corrections
        for (parent_name, child_name), new_label in pending.items():
            char_b = char_by_name.get(parent_name)
            if char_b is None:
                continue
            rels_b = getattr(char_b, "relationships", None) or {}
            current = rels_b.get(child_name, "").strip().lower()
            if current != new_label:
                logger.info(
                    f"Inverse consistency: '{parent_name}'→'{child_name}' "
                    f"was '{current}' but should be '{new_label}' "
                    f"('{child_name}' claims to be '{parent_name}'\\'s child)"
                )
                char_b.relationships[child_name] = new_label

    def reject_unfounded_familial_labels(self, characters, source_text: str) -> None:
        """Remove familial relationship labels unsupported by shared surname or text evidence.

        Universal invariant: a familial label (mother, father, husband, wife, etc.)
        is hallucinated if:
        1. The two characters share NO surname component, AND
        2. No tight text co-mention (within 100 chars) with a possessive/family phrase
           connects them.

        This runs AFTER verify_relationships_from_text, which can introduce incorrect
        family labels when nearby family phrases in 500-char windows belong to a
        different character pair (e.g., a possessive phrase like "her husband"
        referring to a third character found in a co-mention window).
        """
        if not source_text:
            return

        family_set = set(FAMILY_TERMS)
        name_patterns = _build_name_patterns(characters)
        _skip_titles = {"jr.", "sr.", "jr", "sr", "ii", "iii", "iv",
                        "md", "phd", "dr", "mr", "mrs", "ms", "miss"}
        tight_window = 100

        def _surnames(name: str) -> set:
            parts = name.split()
            if len(parts) <= 1:
                return set()
            return {
                p.lower().strip("().,")
                for p in parts[1:]
                if len(p.strip("().,")) > 2 and p.lower().strip("().,") not in _skip_titles
            }

        # Build lookup: lower name/alias → Character
        char_by_lower: dict = {}
        for c in characters:
            char_by_lower[c.canonical_name.lower()] = c
            for alias in (getattr(c, 'aliases', None) or []):
                char_by_lower[alias.lower()] = c

        for char in characters:
            if not char.relationships:
                continue
            char_surnames = _surnames(char.canonical_name)
            pat_a = name_patterns.get(char.canonical_name)

            for other_key in list(char.relationships.keys()):
                rel = char.relationships.get(other_key) or ""
                if not rel:
                    continue
                rel_lower = rel.strip().lower()
                if not any(t in rel_lower for t in family_set):
                    continue

                # Check 1: Shared surname → probably a real family relationship.
                other_char = char_by_lower.get(other_key.lower())
                other_surnames = _surnames(other_char.canonical_name) if other_char else set()
                if char_surnames & other_surnames:
                    continue

                # Option B: Only allow text evidence exception for sibling (sister/brother)
                # labels.  For all other non-surname-sharing family pairs, the label is
                # removed unconditionally — a universal invariant because almost all books
                # use shared surnames for spouses, parents, and children, and the 100-char
                # co-mention check for non-sibling terms causes too many false positives
                # (e.g., "her husband" in a scene window where two unrelated characters appear).
                sibling_terms = {"sister", "brother"}
                is_sibling = any(t in rel_lower for t in sibling_terms)
                if not is_sibling:
                    # Downgrade to "associated" rather than deleting entirely.
                    # Spouses and parent-child pairs frequently have different surnames
                    # (e.g., betrothed couples, adopted children) so shared-surname is
                    # not a reliable universal proxy for family relationships.
                    # "associated" is a factually safe fallback that preserves the
                    # information that these characters share narrative space.
                    char.relationships[other_key] = "associated"
                    logger.info(
                        f"Downgraded non-sibling familial label (no shared surname) to 'associated': "
                        f"'{char.canonical_name}' → '{other_key}': '{rel}'"
                    )
                    continue

                # For sibling labels: check text co-mention evidence.
                pat_b = name_patterns.get(other_char.canonical_name) if other_char else None
                has_evidence = False
                if pat_a and pat_b:
                    for match_a in pat_a.finditer(source_text):
                        ws = max(0, match_a.start() - tight_window)
                        we = min(len(source_text), match_a.end() + tight_window)
                        win = source_text[ws:we]
                        if pat_b.search(win) and _rel_phrase_re.search(win):
                            has_evidence = True
                            break

                if has_evidence:
                    continue

                # No sibling evidence: downgrade rather than delete.
                char.relationships[other_key] = "associated"
                logger.info(
                    f"Downgraded unfounded familial label to 'associated': "
                    f"'{char.canonical_name}' → '{other_key}': '{rel}'"
                )

    def reject_unfounded_romantic_labels(self, characters, source_text: str) -> None:
        """Downgrade 'romantic interest'/'love interest' labels unsupported by text evidence.

        Universal invariant: a romantic relationship label is hallucinated if the
        source text contains no explicit romantic language (love, kiss, marry, wed,
        betrothed, romance, courtship, fiancée) in any window where both characters
        co-appear.  Weak emotional words (longing, affection, dear) are deliberately
        excluded because they appear in non-romantic contexts in most narratives.

        When no strong evidence is found, the label is downgraded to "associated"
        rather than deleted — this preserves the co-occurrence signal while removing
        the misleading romantic claim.  Runs after reject_unfounded_familial_labels.
        """
        if not source_text:
            return

        _STRONG_ROMANTIC = frozenset({
            "love", "loves", "loved", "beloved",
            "kiss", "kisses", "kissed",
            "marry", "married", "marriage",
            "wed", "wedding", "wedded",
            "betrothed", "betrothal",
            "romance", "romantic",
            "courtship", "courting",
            "fiancée", "fiancé", "fiance",
        })
        romantic_labels = {"romantic interest", "love interest"}
        co_window = 500
        name_patterns = _build_name_patterns(characters)

        for char in characters:
            if not char.relationships:
                continue
            pat_a = name_patterns.get(char.canonical_name)
            if pat_a is None:
                continue

            for other_key in list(char.relationships.keys()):
                rel = char.relationships.get(other_key) or ""
                if rel.strip().lower() not in romantic_labels:
                    continue

                other_char = next(
                    (c for c in characters if c.canonical_name == other_key
                     or other_key in (c.aliases or [])),
                    None,
                )
                if other_char is None:
                    continue
                pat_b = name_patterns.get(other_char.canonical_name)
                if pat_b is None:
                    continue

                # Search for strong romantic evidence in co-mention windows.
                has_evidence = False
                for ma in pat_a.finditer(source_text):
                    ws = max(0, ma.start() - co_window)
                    we = min(len(source_text), ma.end() + co_window)
                    win = source_text[ws:we]
                    if not pat_b.search(win):
                        continue
                    win_lower = win.lower()
                    if any(w in win_lower for w in _STRONG_ROMANTIC):
                        has_evidence = True
                        break

                if not has_evidence:
                    char.relationships[other_key] = "associated"
                    logger.info(
                        f"Downgraded unfounded romantic label: "
                        f"'{char.canonical_name}' → '{other_key}': "
                        f"'{rel}' → 'associated' (no romantic text evidence)"
                    )

    def clean_unknown_relationships(self, characters) -> None:
        """Remove relationship entries labeled 'unknown' - they provide no information.

        'unknown' is a sentinel value meaning the relationship could not be determined.
        Better to omit the entry than show a meaningless label to the narrator.
        Runs last so all other corrections (verify_relationships, enforce_gender) have
        already run and may have resolved some entries.
        """
        for char in characters:
            if not char.relationships:
                continue
            to_remove = [
                k for k, v in char.relationships.items()
                if (v or "").strip().lower() == "unknown"
            ]
            for k in to_remove:
                del char.relationships[k]
                logger.info(
                    f"Removed uninformative relationship: "
                    f"'{char.canonical_name}' → '{k}': 'unknown'"
                )
