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
}

FAMILY_TERMS = (
    "cousin", "brother", "sister", "uncle", "aunt", "nephew", "niece",
    "father", "mother", "son", "daughter", "husband", "wife",
    "grandfather", "grandmother", "grandson", "granddaughter",
)

PHYS_DESCRIPTOR_WORDS = {
    "man", "woman", "person", "elderly", "old", "young", "tall",
    "short", "thin", "small", "lean", "stout", "fat", "grizzled",
    "bald", "gray", "grey", "large",
}

MALE_INDICATORS = {"man", " he ", " his ", "himself", "boy", "gentleman", "mr."}
FEMALE_INDICATORS = {"woman", " she ", " her ", "herself", "girl", "lady", "mrs.", "miss"}
FEMALE_ONLY_RELS = {"mother", "sister", "wife", "daughter", "grandmother", "granddaughter", "aunt", "niece"}
MALE_ONLY_RELS = {"father", "brother", "husband", "son", "grandfather", "grandson", "uncle", "nephew"}

SAME_PERSON_PHRASES = ("same person", "same character", "identical to", "the same as", "same individual")

NO_DESC_PHRASES = (
    "unknown", "does not provide", "no physical description",
    "not described", "no direct physical", "no description",
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

# Death phrase pattern
_death_phrase_re = re.compile(r'\s+in\s+death(?=[.,;!?]|$)', re.IGNORECASE)

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
                if cleaned:
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

    def infer_bidirectional_relationships(self, characters) -> None:
        """Infer reverse family relationships.

        If character A -> B is "father", infer B -> A is "son" (if not
        already set). Parent/child, sibling, and spouse relationships
        are always bidirectional with a known reverse.
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
                    rel_words = set(rel_lower.split())
                    for key in sorted(RELATIONSHIP_REVERSES, key=len, reverse=True):
                        if key in rel_words:
                            reverse_rel = RELATIONSHIP_REVERSES[key]
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

    def run_all(self, characters, source_text: str) -> None:
        """Run all Phase B corrections in order. Mutates characters in place."""
        self.inject_narrator_appearance_final(characters, source_text)
        self.extract_deterministic_age(characters, source_text)
        self.clean_unknown_appearance(characters)
        self.clean_plot_summary_personality(characters, source_text)
        self.propagate_physical_description(characters)
        self.clean_orphaned_relationships(characters)
        self.fix_same_person_relationships(characters)
        self.verify_relationships_from_text(characters, source_text)
        self.enforce_gender_consistency(characters)

    def propagate_physical_description(self, characters) -> None:
        """Copy appearance.summary to physical_description when the latter is absent.

        Falls back to joining distinguishing_features when summary is null.
        Provides a flat top-level field for narrator convenience without duplicating
        structured appearance data.  Skips placeholder values like 'unknown'.
        """
        _skip = {"", "unknown", "not described", "no physical description available in text."}
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

    def inject_narrator_appearance_final(self, characters, source_text: str) -> None:
        """Final narrator appearance injection (guaranteed-last pass).

        Runs AFTER _convert_characters so no subsequent step can overwrite it.
        Any first-person narrator who physically self-describes in text gets
        that description injected regardless of what the LLM generated.
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
            if cleaned:
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
        for char in characters:
            app = getattr(char, 'appearance', None)
            if not app:
                continue
            for key in ("summary", "age_indication", "distinguishing_features"):
                val = app.get(key)
                if isinstance(val, str) and val.strip().lower() in _placeholder:
                    app[key] = None
                    logger.info(
                        f"Cleared placeholder appearance.{key}='{val}' for '{char.canonical_name}'"
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
                    for rm in _rel_phrase_re.finditer(win):
                        term = rm.group(1).lower()
                        found[term] = found.get(term, 0) + 1

                if found:
                    best = max(found, key=found.get)
                    if best not in cur_lower:
                        logger.info(
                            f"Text-based rel override: '{char.canonical_name}' → '{other_key}': "
                            f"'{cur}' → '{best}' (evidence: {found})"
                        )
                        char.relationships[other_key] = best
                elif is_family and comention_count == 0:
                    logger.info(
                        f"Hallucinated family rel downgraded: "
                        f"'{char.canonical_name}' → '{other_key}': '{cur}' → 'acquaintance'"
                    )
                    char.relationships[other_key] = "acquaintance"

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
                new_summary = ' '.join(subject_sentences)
                if len(new_summary) > 250:
                    new_summary = new_summary[:250].rsplit(' ', 1)[0] + '…'
                personality['summary'] = new_summary
                logger.info(
                    f"Plot-synopsis personality replaced for '{char.canonical_name}': "
                    f"extracted {len(subject_sentences)} subject sentence(s) from source text "
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

        If a character is clearly male (from descriptions), they cannot be
        "mother", "sister", etc. Similarly for female characters.
        """
        for char in characters:
            desc_text = " ".join(
                d.text.lower() for d in (getattr(char, 'descriptions', None) or []) if d.text
            )
            is_male = any(ind in f" {desc_text} " for ind in MALE_INDICATORS)
            is_female = any(ind in f" {desc_text} " for ind in FEMALE_INDICATORS)

            if not char.relationships:
                continue
            for other_key, rel_val in list(char.relationships.items()):
                if not rel_val:
                    continue
                rel_lower = rel_val.strip().lower()
                if is_male and not is_female and rel_lower in FEMALE_ONLY_RELS:
                    logger.info(
                        f"Gender consistency: '{char.canonical_name}' (male) cannot be "
                        f"'{rel_val}' to '{other_key}' — correcting to 'unknown'"
                    )
                    char.relationships[other_key] = "unknown"
                elif is_female and not is_male and rel_lower in MALE_ONLY_RELS:
                    logger.info(
                        f"Gender consistency: '{char.canonical_name}' (female) cannot be "
                        f"'{rel_val}' to '{other_key}' — correcting to 'unknown'"
                    )
                    char.relationships[other_key] = "unknown"
