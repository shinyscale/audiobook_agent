"""
Output linter: universal invariant checks on a finished AnalysisResult.

Every rule here must hold for ANY novel — past, present, or future — and may
only use evidence internal to the book's own text (no real-world name
knowledge, no genre assumptions). Violations indicate pipeline bugs, not
unusual books; they are reported as warnings, never auto-fixed.
"""

import logging
import re

logger = logging.getLogger(__name__)

# Cap how many violation strings are appended to result.warnings (all are logged)
MAX_REPORTED_VIOLATIONS = 25


def _title_stop_group_sets():
    """Borrow the canonical token sets from the extraction pipeline."""
    from .character_extraction_v2.main_cast import MainCastExtractor

    return (
        MainCastExtractor._TITLE_TOKENS,
        MainCastExtractor._NAME_STOP_TOKENS,
        MainCastExtractor._GROUP_NOUNS,
    )


def _is_valid_ipa(ipa: str) -> bool:
    from .pronunciation_guide.enricher import _is_valid_ipa as _check

    return _check(ipa)


def lint_analysis_result(result, full_text: str) -> list[str]:
    """
    Check a finished AnalysisResult against universal invariants.

    Args:
        result: AnalysisResult (characters, pronunciations, structure populated)
        full_text: The book's full text (post-refinement)

    Returns:
        List of human-readable violation strings (empty = clean).
    """
    violations: list[str] = []
    text_lower = full_text.lower() if full_text else ""
    title_tokens, stop_tokens, group_nouns = _title_stop_group_sets()

    characters = list(getattr(result, "characters", None) or [])

    # --- Character invariants -------------------------------------------------

    # Cast name index for relationship checks: exact names plus a word-level
    # index so partial keys ("Mitchell" for cast member "Mike Mitchell")
    # resolve when unambiguous.
    cast_names_lower: set[str] = set()
    cast_word_index: dict[str, set[str]] = {}
    for c in characters:
        names = [c.canonical_name] + list(getattr(c, "aliases", None) or [])
        for n in names:
            cast_names_lower.add(n.lower())
            for w in n.split():
                tok = w.strip(",.()'\"").lower()
                if len(tok) >= 3 and tok not in title_tokens and tok not in stop_tokens:
                    cast_word_index.setdefault(tok, set()).add(c.canonical_name.lower())

    def _resolves_to_cast(target: str) -> bool:
        t = target.lower()
        if t in cast_names_lower:
            return True
        core_toks = [
            w.strip(",.()'\"").lower()
            for w in target.split()
            if w.strip(",.()'\"").lower() not in title_tokens
            and w.strip(",.()'\"").lower() not in stop_tokens
        ]
        core_toks = [w for w in core_toks if len(w) >= 3]
        if not core_toks:
            return False
        # Resolvable if the last core token (surname) maps to exactly one cast member
        return len(cast_word_index.get(core_toks[-1], set())) == 1

    seen_canonicals: dict[str, str] = {}
    for c in characters:
        name = c.canonical_name
        name_lower = name.lower()

        # C1: duplicate canonical names
        if name_lower in seen_canonicals:
            violations.append(
                f"C1 duplicate canonical: '{name}' appears more than once in the cast"
            )
        seen_canonicals[name_lower] = name

        # C2: canonical is a bare title or group descriptor
        words = [w.strip(",.()'\"").lower() for w in name.split()]
        core = [w for w in words if w and w not in title_tokens and w not in stop_tokens]
        if not core:
            violations.append(
                f"C2 bare-title canonical: '{name}' has no name content beyond titles"
            )
        elif core[-1] in group_nouns:
            violations.append(
                f"C2 group canonical: '{name}' denotes a group, not an individual"
            )

        # C3: canonical name must appear in the text (unnamed/descriptive
        # handles and symbolic entities are exempt — they're paraphrases)
        if (
            text_lower
            and not getattr(c, "is_symbolic", False)
            and name_lower not in text_lower
        ):
            core_found = any(
                re.search(rf"\b{re.escape(t)}\b", text_lower) for t in core if len(t) >= 3
            )
            if not core_found:
                violations.append(
                    f"C3 ungrounded canonical: '{name}' never appears in the text"
                )

        # C4: alias token grounding — every substantive alias token must occur
        # somewhere in the full text
        canonical_tokens = {w.strip(",.()'\"").lower() for w in name.split()}
        for alias in getattr(c, "aliases", None) or []:
            if not text_lower:
                break
            for raw in alias.split():
                tok = raw.strip(",.()'\"").lower()
                if (
                    not tok
                    or len(tok) < 3
                    or tok in canonical_tokens
                    or tok in title_tokens
                    or tok in stop_tokens
                ):
                    continue
                parts = [p for p in tok.split("-") if p] or [tok]
                if not any(
                    re.search(rf"\b{re.escape(p)}\b", text_lower) for p in parts
                ):
                    violations.append(
                        f"C4 ungrounded alias: '{alias}' of '{name}' — token "
                        f"'{raw}' never appears in the text"
                    )
                    break

        # C5: relationships must reference cast members, never self
        rels = getattr(c, "relationships", None) or {}
        for target in rels:
            target_lower = target.lower()
            if target_lower == name_lower:
                violations.append(f"C5 self-relationship: '{name}' → '{target}'")
            elif not _resolves_to_cast(target):
                violations.append(
                    f"C5 orphan relationship: '{name}' → '{target}' "
                    f"(target is not a cast member)"
                )

        # C6: mention accounting — a kept character should have evidence of
        # existing (mentions, dialogue, or symbolic status)
        mention_count = getattr(c, "mention_count", 0) or 0
        if mention_count == 0 and not getattr(c, "is_symbolic", False):
            violations.append(
                f"C6 zero-mention character: '{name}' was kept with no text mentions"
            )

    # C7: has_dialogue cross-check against exported CRF attributions — only
    # meaningful when attribution data exists at all
    structure = list(getattr(result, "structure", None) or [])
    attributed_speakers = {
        (d.get("speaker") or "").lower()
        for el in structure
        for d in (getattr(el, "dialogue_speakers", None) or [])
        if isinstance(d, dict)
    }
    attributed_speakers.discard("")
    if attributed_speakers:
        for c in characters:
            if not getattr(c, "has_dialogue", False):
                continue
            char_names = {c.canonical_name.lower()} | {
                a.lower() for a in (getattr(c, "aliases", None) or [])
            }
            if not (char_names & attributed_speakers):
                violations.append(
                    f"C7 unattributed dialogue flag: '{c.canonical_name}' has "
                    f"has_dialogue=true but no CRF-attributed lines"
                )

    # --- Pronunciation invariants ----------------------------------------------

    for p in getattr(result, "pronunciations", None) or []:
        word = getattr(p, "word", "") or ""
        # P1: flagged word must occur in the text
        if text_lower and word and word.lower() not in text_lower:
            violations.append(
                f"P1 ungrounded pronunciation: '{word}' never appears in the text"
            )
        # P2: IPA must be well-formed when present
        ipa = getattr(p, "ipa", None)
        if ipa and not _is_valid_ipa(ipa):
            violations.append(
                f"P2 malformed IPA for '{word}': {ipa!r} contains non-IPA codepoints"
            )

    return violations


def apply_lint(result, full_text: str) -> list[str]:
    """
    Run the linter, log every violation, and append a capped summary to
    result.warnings. Returns the full violation list.
    """
    try:
        violations = lint_analysis_result(result, full_text)
    except Exception as e:  # linter must never break an analysis
        logger.warning(f"Output linter failed: {e}")
        return []

    if not violations:
        logger.info("Output lint: clean (0 invariant violations)")
        return []

    logger.warning(f"Output lint: {len(violations)} invariant violation(s)")
    for v in violations:
        logger.warning(f"  LINT: {v}")

    warnings_list = getattr(result, "warnings", None)
    if warnings_list is not None:
        warnings_list.append(
            f"Output lint: {len(violations)} invariant violation(s) — "
            f"likely pipeline bugs, see log for full list"
        )
        warnings_list.extend(violations[:MAX_REPORTED_VIOLATIONS])
        if len(violations) > MAX_REPORTED_VIOLATIONS:
            warnings_list.append(
                f"Output lint: ... {len(violations) - MAX_REPORTED_VIOLATIONS} more "
                f"violation(s) suppressed (see log)"
            )
    return violations
