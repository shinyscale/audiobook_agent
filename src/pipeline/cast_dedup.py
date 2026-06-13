"""
Final-stage cast cleanup, all deterministic and text-grounded:

  1. reground_canonical_names — a canonical name must appear in the text. When a
     multi-word canonical's given+surname never co-occur in the source (a
     hallucinated/wrong given name attached to a real surname, e.g. "Mary
     Wilson" / "Audie Murphy"), rename it to a grounded form (a grounded alias
     or the bare surname).
  2. merge_fragment_duplicates — merge a less-specific name into a more-specific
     one ONLY when their mention_counts are identical (the searcher matched the
     same occurrences ⇒ provably the same entity). This avoids namesake
     collisions across DIFFERENT counts (soldier "Murphy" 3 vs "Audie Murphy"
     36; "Captain Turner" 4 vs warship "USS Turner Joy" 8).
  3. reject_implausible_narrator — a narrator is a dominant presence; drop the
     flag if it sits far below the lead's mention count.

Operates on any object exposing canonical_name, aliases, mention_count, role,
is_narrator, id, evidence, descriptions (pipeline or output Characters).
Conservative by design — the project's history is littered with over-merge
regressions, so every action requires a high-confidence, text-anchored signal.
"""

import logging
import re

logger = logging.getLogger(__name__)


# Generic role-nicknames that are shared by multiple distinct characters
# ("Doc", "Sarge", "Chief"). A name built only on one of these has no identifying
# core, so it must never absorb a specifically-named character.
_ROLE_NICKNAMES = frozenset({"doc", "sarge", "chief", "top", "padre", "preacher", "gunny"})


def _core_tokens(name: str):
    from .character_extraction_v2.main_cast import MainCastExtractor

    toks = MainCastExtractor._name_core_tokens(name)
    return [t for t in toks if t not in _ROLE_NICKNAMES]


def _given_name_conflict(a: str, b: str) -> bool:
    from .character_extraction_v2.main_cast import MainCastExtractor

    gnc = MainCastExtractor.__new__(MainCastExtractor)
    return gnc._given_name_conflict(a, b)


def _grounded(token_seq, text_lower: str) -> bool:
    """Do these core tokens appear as an adjacent unit in the text?

    Strict adjacency: the given name must sit immediately before the surname
    ("mike mitchell"). A loose gap would falsely ground "Mary Wilson" off an
    unrelated "Mary, and Wilson" elsewhere in a long text. A real middle name
    ("Mary Anne Wilson") that fails this just regrounds to the surname, which
    is safe.
    """
    if not token_seq:
        return False
    if len(token_seq) == 1:
        return bool(re.search(rf"\b{re.escape(token_seq[0])}\b", text_lower))
    first, last = token_seq[0], token_seq[-1]
    return bool(re.search(rf"\b{re.escape(first)}\s+{re.escape(last)}\b", text_lower))


def reground_canonical_names(characters: list, source_text: str) -> None:
    """Rename canonicals whose full name never appears in the text. Mutates in place."""
    if not source_text:
        return
    tl = source_text.lower()
    for c in characters:
        core = _core_tokens(c.canonical_name)
        if len(core) < 2:
            continue  # bare surname / single token — already minimal
        if _grounded(core, tl) or c.canonical_name.lower() in tl:
            continue  # full name is attested — keep it
        surname = core[-1]
        if len(surname) < 3:
            continue
        # Prefer a grounded single-token alias ending in the surname.
        new_name = None
        for a in list(getattr(c, "aliases", []) or []):
            ac = _core_tokens(a)
            if (
                ac
                and ac[-1] == surname
                and len(ac) == 1
                and re.search(rf"\b{re.escape(surname)}\b", tl)
            ):
                new_name = a
                break
        if new_name is None and re.search(rf"\b{re.escape(surname)}\b", tl):
            new_name = surname.capitalize()
        if not new_name or new_name.lower() == c.canonical_name.lower():
            continue
        old = c.canonical_name
        c.canonical_name = new_name
        # Drop the ungrounded old name; keep only aliases that ARE in the text.
        c.aliases = [
            x
            for x in (getattr(c, "aliases", []) or [])
            if x.lower() != new_name.lower() and x.lower() in tl
        ]
        logger.info(
            f"Regrounded canonical '{old}' -> '{new_name}' "
            f"(original name absent from text)"
        )


def _bigram_count(name: str, text_lower: str) -> int:
    core = _core_tokens(name)
    if len(core) < 2:
        return 0
    return len(
        re.findall(rf"\b{re.escape(core[0])}\s+{re.escape(core[-1])}\b", text_lower)
    )


def merge_fragment_duplicates(characters: list, source_text: str = "") -> list:
    """Merge identical-mention-count name fragments into their fuller form.

    When the fuller name is only weakly attested as a unit (its given+surname
    bigram occurs <2× and it is not a lead-role character), the canonical is set
    to the bare surname instead. This prevents a real-world name-drop that
    shares a surname with a soldier ("Mary Wilson", "Audie Murphy") from
    becoming the displayed name of that soldier — a residual of the upstream
    bug where a bare-surname alias is attributed to the wrong entity.
    """
    tl = (source_text or "").lower()
    chars = list(characters)
    cores = {id(c): set(_core_tokens(c.canonical_name)) for c in chars}
    mc = {id(c): (getattr(c, "mention_count", 0) or 0) for c in chars}
    removed: set[int] = set()

    # Shortest core first so the least-specific name folds into the fuller one.
    order = sorted(chars, key=lambda c: (len(cores[id(c)]), -mc[id(c)]))
    for b in order:
        if id(b) in removed:
            continue
        b_core = cores[id(b)]
        if not b_core:
            continue  # title-only / empty core ("Doc") — never a merge source
        containers = []
        for a in chars:
            if a is b or id(a) in removed:
                continue
            a_core = cores[id(a)]
            if not a_core or not (b_core <= a_core):
                continue  # A must contain B's core tokens
            if a_core == b_core:
                # Same core (title-only variants, "Pfc. Perkins"/"Perkins", or
                # exact duplicates). Pick a deterministic survivor so the pair
                # merges once: the longer name string, breaking ties by id.
                a_wins = (len(a.canonical_name) > len(b.canonical_name)) or (
                    len(a.canonical_name) == len(b.canonical_name)
                    and str(getattr(a, "id", "")) < str(getattr(b, "id", ""))
                )
                if not a_wins:
                    continue
            if mc[id(a)] != mc[id(b)]:
                continue  # identical occurrences ⇒ same entity; else skip
            if _given_name_conflict(a.canonical_name, b.canonical_name):
                continue
            containers.append(a)
        if len(containers) != 1:
            continue  # zero or ambiguous → leave b alone
        a = containers[0]

        # Decide the surviving canonical. Keep A's fuller name only if it
        # genuinely recurs as a unit or A is a lead; otherwise the bare-surname
        # fragment B is the safer displayed name (avoids labelling a soldier
        # with a name-drop's given name).
        keep_full = (
            not tl
            or _bigram_count(a.canonical_name, tl) >= 2
            or getattr(a, "role", None) in ("protagonist", "main")
            or getattr(a, "is_narrator", False)
        )
        if keep_full:
            survivor_name, demoted_name = a.canonical_name, b.canonical_name
        else:
            survivor_name, demoted_name = b.canonical_name, a.canonical_name

        new_aliases = list(getattr(a, "aliases", []) or [])
        for nm in [a.canonical_name, b.canonical_name] + list(
            getattr(b, "aliases", []) or []
        ):
            if nm and nm.lower() != survivor_name.lower() and nm not in new_aliases:
                new_aliases.append(nm)
        a.canonical_name = survivor_name
        a.aliases = new_aliases
        if not getattr(a, "evidence", None) and getattr(b, "evidence", None):
            a.evidence = b.evidence
        if not getattr(a, "descriptions", None) and getattr(b, "descriptions", None):
            a.descriptions = b.descriptions
        if getattr(b, "is_narrator", False):
            a.is_narrator = True
        removed.add(id(b))
        logger.info(
            f"Cast dedup: merged fragment '{b.canonical_name}' (mc={mc[id(b)]}) "
            f"into '{a.canonical_name}'"
        )
    return [c for c in chars if id(c) not in removed]


def reject_implausible_narrator(
    characters: list, narrator_id, *, min_ratio: float = 0.10, abs_floor: int = 25
):
    """Drop a narrator assignment that is implausibly minor.

    A first-person narrator is often UNDER-named (they say "I"), so a low
    mention ratio alone is not disqualifying — Nick Carraway has ~14% of
    Gatsby's mentions yet is the narrator. We reject ONLY when the narrator is
    both a tiny fraction of the lead AND has few absolute mentions, the
    signature of a minor character wrongly crowned by a fallback heuristic
    (e.g. a 20-mention captain beside a 1149-mention lead).
    """
    if not narrator_id or not characters:
        return narrator_id
    by_id = {getattr(c, "id", None): c for c in characters}
    narr = by_id.get(narrator_id)
    if narr is None:
        return narrator_id
    top = max((getattr(c, "mention_count", 0) or 0) for c in characters)
    narr_mc = getattr(narr, "mention_count", 0) or 0
    if top > 0 and narr_mc < min_ratio * top and narr_mc < abs_floor:
        logger.warning(
            f"Rejecting narrator '{getattr(narr, 'canonical_name', '?')}' "
            f"(mentions={narr_mc}) — below {min_ratio:.0%} of lead's {top}; "
            f"treating as third-person/omniscient"
        )
        if hasattr(narr, "is_narrator"):
            narr.is_narrator = False
        if getattr(narr, "role", None) == "protagonist":
            narr.role = "supporting"
        return None
    return narrator_id
