"""
Evidence Collectors for Identity Graph

Each collector ports logic from an existing sequential merge function,
but instead of mutating character lists, it adds typed/weighted edges
to the identity graph.

Collectors:
1. collect_title_variant_evidence     ← _merge_title_variants
2. collect_within_cast_evidence       ← _merge_within_main_cast
3. collect_cooccurrence_evidence      ← wraps _compute_cooccurrence
4. collect_cross_cast_evidence        ← _merge_lastname_aliases + _merge_within_supporting_cast
5. collect_synonym_evidence           ← _merge_descriptive_synonyms_across_casts
6. collect_narrator_evidence          ← _merge_narrator_placeholder
7. collect_llm_evidence               ← wraps LLM Pass 2 results
8. collect_constraint_evidence        ← generates constraint edges
"""

import logging
import re
from typing import Optional

from .identity_graph import (
    ConstraintType,
    EdgeType,
    IdentityGraph,
)
from ...utils.similarity import names_similar, string_similarity

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper functions (shared across collectors)
# ---------------------------------------------------------------------------

# Honorific titles that indicate distinct individuals when different
_TITLE_PREFIXES = [
    r"^(Mr\.|Mrs\.|Miss|Ms\.|Dr\.|M\.)\s+",
]

# Common synonym groups for descriptive handles
SYNONYM_GROUPS = [
    # Supernatural/created beings
    {"creature", "monster", "fiend", "daemon", "wretch", "being", "thing"},
    # Authority figures
    {"stranger", "visitor", "guest", "traveler", "intruder"},
    # Generic descriptors
    {"man", "woman", "boy", "girl", "child", "person"},
]

# Common nickname mapping
COMMON_NICKNAMES = {
    "jim": ["james"],
    "jimmy": ["james"],
    "bill": ["william"],
    "billy": ["william"],
    "bob": ["robert"],
    "bobby": ["robert"],
    "dick": ["richard"],
    "rick": ["richard"],
    "ed": ["edward", "edmund"],
    "eddie": ["edward", "edmund"],
    "ted": ["theodore", "edward"],
    "teddy": ["theodore", "edward"],
    "will": ["william"],
    "tom": ["thomas"],
    "tommy": ["thomas"],
    "joe": ["joseph"],
    "joey": ["joseph"],
    "mike": ["michael"],
    "pat": ["patrick", "patricia"],
    "chris": ["christopher", "christine", "christina"],
    "alex": ["alexander", "alexandra", "alexis"],
    "sam": ["samuel", "samantha"],
    "ben": ["benjamin"],
    "matt": ["matthew"],
    "dan": ["daniel"],
    "dave": ["david"],
    "steve": ["stephen", "steven"],
    "milt": ["milton"],
}

# Placeholder patterns for narrator detection
NARRATOR_PLACEHOLDER_PATTERNS = [
    "the protagonist",
    "the narrator",
    "narrator",
    "protagonist",
    "main character",
    "the main character",
]


def _strip_title(name: str) -> str:
    """Strip honorific titles from a name."""
    for pattern in _TITLE_PREFIXES:
        name = re.sub(pattern, "", name, flags=re.IGNORECASE).strip()
    return name


def _name_contains_other(longer_name: str, shorter_name: str) -> bool:
    """Check if longer_name contains shorter_name as a complete word."""
    escaped = re.escape(shorter_name)
    pattern = r"(?:^|[\s\-\.])" + escaped + r"(?:$|[\s\-\.])"
    return bool(re.search(pattern, longer_name))


def _are_different_titled_people(name1: str, name2: str) -> bool:
    """Check if two names represent different people with different title prefixes."""
    title1 = None
    title2 = None
    stripped1 = name1
    stripped2 = name2

    for pattern in _TITLE_PREFIXES:
        match1 = re.match(pattern, name1, flags=re.IGNORECASE)
        if match1:
            title1 = match1.group(1).lower()
            stripped1 = re.sub(pattern, "", name1, flags=re.IGNORECASE).strip()
        match2 = re.match(pattern, name2, flags=re.IGNORECASE)
        if match2:
            title2 = match2.group(1).lower()
            stripped2 = re.sub(pattern, "", name2, flags=re.IGNORECASE).strip()

    if title1 and title2:
        if stripped1.lower() != stripped2.lower():
            return True
        if title1 != title2:
            return True

    return False


def _normalize_descriptor(raw_name: str) -> tuple[bool, str]:
    """
    Normalize a descriptive handle.
    Returns (is_the_form, descriptor).
    """
    name = (raw_name or "").lower().strip()
    is_the_form = name.startswith("the ")
    desc = name[4:].strip() if is_the_form else name
    if " (" in desc:
        desc = desc.split(" (", 1)[0].strip()
    desc = desc.strip(".,;:!?\"'""")
    return is_the_form, desc


def _is_nickname_match(name_a: str, name_b: str) -> bool:
    """Check if two names have a nickname relationship."""
    a_lower = name_a.lower()
    b_lower = name_b.lower()
    if a_lower in COMMON_NICKNAMES:
        if b_lower in COMMON_NICKNAMES[a_lower]:
            return True
    if b_lower in COMMON_NICKNAMES:
        if a_lower in COMMON_NICKNAMES[b_lower]:
            return True
    return False


# ---------------------------------------------------------------------------
# Collector 1: Title variant evidence
# Ports logic from _merge_title_variants (lines 1191-1278)
# ---------------------------------------------------------------------------

def collect_title_variant_evidence(graph: IdentityGraph) -> None:
    """
    Add merge edges for title variant relationships.

    Detects: "Sergeant-Major Morris" contains "Morris" → merge evidence.
    Also adds DIFFERENT_TITLES constraints when applicable.

    Handles ambiguity: if a short name (e.g., "White") is contained in
    multiple longer names that are different people (e.g., "Mr. White",
    "Mrs. White", "Herbert White"), it does NOT add merge edges for the
    short name — those are deferred to cross-cast/within-cast collectors
    which handle ambiguity resolution.
    """
    node_ids = list(graph.nodes.keys())

    # First pass: build containment map for each node
    # shorter_id → list of (longer_id, direction) that contain it
    containment_map: dict[str, list[str]] = {nid: [] for nid in node_ids}

    for i, id_a in enumerate(node_ids):
        node_a = graph.nodes[id_a]
        for id_b in node_ids[i + 1:]:
            node_b = graph.nodes[id_b]

            name_a = node_a.canonical_name
            name_b = node_b.canonical_name
            name_a_lower = name_a.lower()
            name_b_lower = name_b.lower()

            a_contains_b = _name_contains_other(name_a_lower, name_b_lower)
            b_contains_a = _name_contains_other(name_b_lower, name_a_lower)

            if a_contains_b:
                containment_map[id_b].append(id_a)  # b is shorter, a contains it
            if b_contains_a:
                containment_map[id_a].append(id_b)  # a is shorter, b contains it

    # Second pass: add edges, but skip ambiguous short names
    processed_pairs: set[tuple[str, str]] = set()

    for shorter_id, longer_ids in containment_map.items():
        if not longer_ids:
            continue

        shorter_node = graph.nodes[shorter_id]

        # Check for different-titled constraint between each pair
        for longer_id in longer_ids:
            pair = tuple(sorted([shorter_id, longer_id]))
            if pair in processed_pairs:
                continue
            processed_pairs.add(pair)

            longer_node = graph.nodes[longer_id]

            if _are_different_titled_people(shorter_node.canonical_name, longer_node.canonical_name):
                graph.add_constraint_edge(
                    shorter_id, longer_id,
                    ConstraintType.DIFFERENT_TITLES,
                    f"Different titles: '{shorter_node.canonical_name}' vs '{longer_node.canonical_name}'",
                )
                continue

            # If this short name matches MULTIPLE longer names, check if those
            # longer names are different people. If so, skip merge edges for
            # the short name (ambiguous — let cross-cast handle it).
            if len(longer_ids) > 1:
                # Check if the longer names are distinct people
                distinct_people = False
                for i, lid_a in enumerate(longer_ids):
                    for lid_b in longer_ids[i + 1:]:
                        na = graph.nodes[lid_a].canonical_name
                        nb = graph.nodes[lid_b].canonical_name
                        if _are_different_titled_people(na, nb):
                            distinct_people = True
                            break
                        # Check different first names
                        pa = na.split()
                        pb = nb.split()
                        if len(pa) >= 2 and len(pb) >= 2:
                            fa = pa[0].strip(".,;:").lower()
                            fb = pb[0].strip(".,;:").lower()
                            la = pa[-1].strip(".,;:").lower()
                            lb = pb[-1].strip(".,;:").lower()
                            if la == lb and fa != fb:
                                distinct_people = True
                                break
                    if distinct_people:
                        break

                if distinct_people:
                    # Ambiguous — don't add merge edge, add constraint instead
                    graph.add_constraint_edge(
                        shorter_id, longer_id,
                        ConstraintType.AMBIGUOUS_SURNAME,
                        f"Ambiguous containment: '{shorter_node.canonical_name}' matches multiple distinct names",
                    )
                    continue

            # Unambiguous containment — add merge edge
            graph.add_merge_edge(
                shorter_id, longer_id,
                EdgeType.NAME_CONTAINMENT,
                f"Name containment: '{shorter_node.canonical_name}' ↔ '{longer_node.canonical_name}'",
            )


# ---------------------------------------------------------------------------
# Collector 2: Within-cast evidence
# Ports logic from _merge_within_main_cast (lines 1536-1900)
# ---------------------------------------------------------------------------

def collect_within_cast_evidence(graph: IdentityGraph) -> None:
    """
    Add merge edges for within-cast relationships.

    Detects:
    - Middle initial variants: "George B. Wilson" ↔ "George Wilson"
    - Last-name-only → Full name: "Wilson" ↔ "George B. Wilson"
    - Spelling variants: "Wolfsheim" ↔ "Wolfshiem"
    - First-name-only → Full name: "George" ↔ "George Wilson"
    - Descriptive synonyms: "the creature" ↔ "the monster"
    - Period abbreviations: "John G." ↔ "John"
    """
    # Process separately for main cast and supporting cast
    main_ids = [nid for nid, n in graph.nodes.items() if n.is_main_cast]
    supporting_ids = [nid for nid, n in graph.nodes.items() if not n.is_main_cast]

    for cast_ids in [main_ids, supporting_ids]:
        _collect_within_cast_for_group(graph, cast_ids)


def _collect_within_cast_for_group(graph: IdentityGraph, cast_ids: list[str]) -> None:
    """Collect within-cast evidence for a specific group of character IDs."""

    # --- Pass 0: Middle initial variants ---
    middle_initial_pattern = re.compile(r"^(\w+)\s+([A-Z]\.)\s+(.+)$")

    for id_a in cast_ids:
        node_a = graph.nodes[id_a]
        name_a = node_a.canonical_name.strip()

        if not name_a or " " not in name_a:
            continue

        match = middle_initial_pattern.match(name_a)
        if not match:
            continue

        firstname = match.group(1)
        lastname = match.group(3)
        name_without_middle = f"{firstname} {lastname}"

        for id_b in cast_ids:
            if id_b == id_a:
                continue
            node_b = graph.nodes[id_b]
            if node_b.canonical_name.strip().lower() == name_without_middle.lower():
                graph.add_merge_edge(
                    id_a, id_b,
                    EdgeType.MIDDLE_INITIAL,
                    f"Middle initial: '{name_a}' ↔ '{node_b.canonical_name}'",
                )

    # --- Pass 1: Single-word name matching (last name, first name, title-stripped) ---
    for id_a in cast_ids:
        node_a = graph.nodes[id_a]
        name_a = node_a.canonical_name.strip()

        if not name_a or " " in name_a:
            continue  # Only single-word names

        matches = []
        for id_b in cast_ids:
            if id_b == id_a:
                continue
            node_b = graph.nodes[id_b]
            name_b = node_b.canonical_name.strip()

            if not name_b or " " not in name_b:
                continue  # Only match against multi-word

            # Title-stripped exact match
            title_stripped = _strip_title(name_b)
            if name_a.lower() == title_stripped.lower():
                matches.append((id_b, "exact_title_stripped"))
                continue

            # Last name exact match
            parts = name_b.split()
            lastname = parts[-1].strip(".,;:")
            if name_a.lower() == lastname.lower():
                matches.append((id_b, "exact_lastname"))
                continue

            # Fuzzy last name match
            if names_similar(name_a, lastname):
                matches.append((id_b, "fuzzy_lastname"))
                continue

            # First name exact match
            if len(parts) >= 2:
                firstname = parts[0].strip(".,;:")
                if name_a.lower() == firstname.lower():
                    matches.append((id_b, "exact_firstname"))

        # Only add edge if exactly ONE match (avoids ambiguity)
        if len(matches) == 1:
            id_b, match_type = matches[0]
            if "lastname" in match_type or "title_stripped" in match_type:
                graph.add_merge_edge(
                    id_a, id_b,
                    EdgeType.LASTNAME_MATCH,
                    f"Single-word match ({match_type}): '{name_a}' ↔ '{graph.nodes[id_b].canonical_name}'",
                    weight=0.60,  # Boost from default 0.40 since unambiguous
                )
            else:
                graph.add_merge_edge(
                    id_a, id_b,
                    EdgeType.FIRSTNAME_MATCH,
                    f"First name match ({match_type}): '{name_a}' ↔ '{graph.nodes[id_b].canonical_name}'",
                )
        elif len(matches) > 1:
            # Ambiguous - add constraint between all matched pairs
            for id_b, _ in matches:
                graph.add_constraint_edge(
                    id_a, id_b,
                    ConstraintType.AMBIGUOUS_SURNAME,
                    f"Ambiguous single-word '{name_a}' matches multiple: {[graph.nodes[m[0]].canonical_name for m in matches]}",
                )

    # --- Pass 2: Spelling variants (multi-word) ---
    processed_pairs: set[tuple[str, str]] = set()
    for id_a in cast_ids:
        node_a = graph.nodes[id_a]
        name_a = node_a.canonical_name.strip()
        if not name_a:
            continue

        for id_b in cast_ids:
            if id_b <= id_a:
                continue  # Only check each pair once

            pair = tuple(sorted([id_a, id_b]))
            if pair in processed_pairs:
                continue
            processed_pairs.add(pair)

            node_b = graph.nodes[id_b]
            name_b = node_b.canonical_name.strip()
            if not name_b:
                continue

            # For within-supporting, use string_similarity directly (not names_similar)
            # to prevent false merges like "John" + "John Donaldson"
            if not node_a.is_main_cast and not node_b.is_main_cast:
                similarity = string_similarity(name_a, name_b)
                if similarity >= 0.85:
                    if _are_different_titled_people(name_a, name_b):
                        graph.add_constraint_edge(
                            id_a, id_b,
                            ConstraintType.DIFFERENT_TITLES,
                            f"Different titles: '{name_a}' vs '{name_b}'",
                        )
                    else:
                        graph.add_merge_edge(
                            id_a, id_b,
                            EdgeType.SPELLING_VARIANT,
                            f"Spelling variant: '{name_a}' ↔ '{name_b}' (sim={similarity:.2f})",
                        )
            else:
                # For main cast, use names_similar (includes subset matching)
                if names_similar(name_a, name_b):
                    if _are_different_titled_people(name_a, name_b):
                        graph.add_constraint_edge(
                            id_a, id_b,
                            ConstraintType.DIFFERENT_TITLES,
                            f"Different titles: '{name_a}' vs '{name_b}'",
                        )
                    else:
                        similarity = string_similarity(name_a, name_b)
                        graph.add_merge_edge(
                            id_a, id_b,
                            EdgeType.SPELLING_VARIANT,
                            f"Spelling variant: '{name_a}' ↔ '{name_b}' (sim={similarity:.2f})",
                        )

    # --- Pass 3: Descriptive synonyms (the creature ↔ the monster) ---
    for id_a in cast_ids:
        node_a = graph.nodes[id_a]
        is_the_a, desc_a = _normalize_descriptor(node_a.canonical_name)

        for group in SYNONYM_GROUPS:
            allow_bare = "creature" in group
            if desc_a not in group:
                continue
            if not is_the_a and not allow_bare:
                continue

            for id_b in cast_ids:
                if id_b <= id_a:
                    continue

                node_b = graph.nodes[id_b]
                is_the_b, desc_b = _normalize_descriptor(node_b.canonical_name)

                if desc_b in group and (is_the_b or allow_bare):
                    graph.add_merge_edge(
                        id_a, id_b,
                        EdgeType.DESCRIPTIVE_SYNONYM,
                        f"Synonym group {group}: '{node_a.canonical_name}' ↔ '{node_b.canonical_name}'",
                    )

    # --- Pass 4: Period-terminated abbreviations ("John G." ↔ "John") ---
    for id_a in cast_ids:
        node_a = graph.nodes[id_a]
        name_a = node_a.canonical_name.strip()
        if not name_a or "." not in name_a:
            continue

        # Normalize: strip trailing "X." initials
        normalized_a = re.sub(r'\s+[A-Z]\.$', '', name_a).lower().strip()
        if not normalized_a:
            continue

        for id_b in cast_ids:
            if id_b == id_a:
                continue

            node_b = graph.nodes[id_b]
            name_b = node_b.canonical_name.strip()
            if not name_b:
                continue

            normalized_b = re.sub(r'\s+[A-Z]\.$', '', name_b).lower().strip()
            if normalized_a == normalized_b and normalized_a:
                graph.add_merge_edge(
                    id_a, id_b,
                    EdgeType.PERIOD_ABBREVIATION,
                    f"Period abbreviation: '{name_a}' ↔ '{name_b}'",
                )


# ---------------------------------------------------------------------------
# Collector 3: Co-occurrence evidence
# Wraps _compute_cooccurrence results
# ---------------------------------------------------------------------------

def collect_cooccurrence_evidence(
    graph: IdentityGraph,
    cooccurrence: dict[tuple[str, str], float],
    positive_threshold: float = 0.5,
) -> None:
    """
    Add co-occurrence based evidence to the graph.

    High co-occurrence (>0.5) adds merge evidence.
    Does not add negative evidence — co-occurrence absence is not proof of
    being different people (a character might use different names in different chapters).
    """
    seen_pairs: set[tuple[str, str]] = set()

    for (id_a, id_b), score in cooccurrence.items():
        pair = tuple(sorted([id_a, id_b]))
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)

        if id_a not in graph.nodes or id_b not in graph.nodes:
            continue

        if score >= positive_threshold:
            graph.add_merge_edge(
                id_a, id_b,
                EdgeType.COOCCURRENCE,
                f"High co-occurrence: score={score:.2f}",
                weight=min(score, 0.90),  # Cap at 0.90
            )


# ---------------------------------------------------------------------------
# Collector 4: Cross-cast evidence
# Ports logic from _merge_lastname_aliases and _merge_within_supporting_cast
# ---------------------------------------------------------------------------

def collect_cross_cast_evidence(graph: IdentityGraph) -> None:
    """
    Add merge edges for cross-cast relationships (supporting → main).

    Detects:
    - Title variants: "Mr. Gatsby" (supporting) ↔ "Jay Gatsby" (main)
    - "the X" variants: "owl-eyed man" ↔ "the owl-eyed man"
    - Fuzzy full-name matches: "Meyer Wolfsheim" ↔ "Meyer Wolfshiem"
    - Last-name matches: "Wilson" (supporting) ↔ "George Wilson" (main)
    - First-name matches: "George" (supporting) ↔ "George Wilson" (main)
    - Nickname matches: "Jim" ↔ "James Dillingham Young"
    - Reverse matches: single-word main ↔ full-name supporting
    """
    main_ids = [nid for nid, n in graph.nodes.items() if n.is_main_cast]
    supporting_ids = [nid for nid, n in graph.nodes.items() if not n.is_main_cast]

    for supp_id in supporting_ids:
        supp_node = graph.nodes[supp_id]
        supp_name = supp_node.canonical_name.strip()
        if not supp_name:
            continue

        # --- Title variant check ---
        title_stripped = _strip_title(supp_name)
        if title_stripped != supp_name:
            for main_id in main_ids:
                main_node = graph.nodes[main_id]
                # Check canonical name
                if title_stripped.lower() == main_node.canonical_name.lower():
                    graph.add_merge_edge(
                        supp_id, main_id,
                        EdgeType.TITLE_VARIANT,
                        f"Title variant: '{supp_name}' ↔ '{main_node.canonical_name}'",
                    )
                    break
                # Check aliases
                for alias in main_node.aliases:
                    if title_stripped.lower() == alias.lower():
                        graph.add_merge_edge(
                            supp_id, main_id,
                            EdgeType.TITLE_VARIANT,
                            f"Title variant: '{supp_name}' ↔ '{main_node.canonical_name}' (via alias '{alias}')",
                        )
                        break

        # --- "the X" normalization ---
        supp_normalized = re.sub(r"^the\s+", "", supp_name, flags=re.IGNORECASE).strip()
        for main_id in main_ids:
            main_node = graph.nodes[main_id]
            main_normalized = re.sub(
                r"^the\s+", "", main_node.canonical_name, flags=re.IGNORECASE
            ).strip()

            if (
                supp_normalized.lower() == main_normalized.lower()
                or supp_name.lower() == main_node.canonical_name.lower()
            ) and supp_name.lower() != main_node.canonical_name.lower():
                graph.add_merge_edge(
                    supp_id, main_id,
                    EdgeType.THE_VARIANT,
                    f"'the' variant: '{supp_name}' ↔ '{main_node.canonical_name}'",
                )
                break

            # Check aliases
            for alias in main_node.aliases:
                alias_normalized = re.sub(r"^the\s+", "", alias, flags=re.IGNORECASE).strip()
                if (
                    supp_normalized.lower() == alias_normalized.lower()
                    or supp_name.lower() == alias.lower()
                ) and supp_name.lower() != alias.lower():
                    graph.add_merge_edge(
                        supp_id, main_id,
                        EdgeType.THE_VARIANT,
                        f"'the' variant: '{supp_name}' ↔ '{main_node.canonical_name}' (via alias '{alias}')",
                    )
                    break

        # --- Fuzzy full-name match (multi-word supporting) ---
        if " " in supp_name:
            for main_id in main_ids:
                main_node = graph.nodes[main_id]
                if names_similar(supp_name, main_node.canonical_name):
                    graph.add_merge_edge(
                        supp_id, main_id,
                        EdgeType.FULL_NAME_FUZZY,
                        f"Fuzzy full-name: '{supp_name}' ↔ '{main_node.canonical_name}'",
                    )
                    break
            continue  # Multi-word names don't need single-word processing

        # --- Single-word supporting → multi-word main (last/first name match) ---
        matches = []
        for main_id in main_ids:
            main_node = graph.nodes[main_id]
            main_name = main_node.canonical_name.strip()
            main_parts = main_name.split()
            if not main_parts:
                continue

            # Last name match
            main_lastname = main_parts[-1].strip(".,;:")
            if supp_name.lower() == main_lastname.lower():
                matches.append((main_id, "exact_lastname"))
                continue
            if names_similar(supp_name, main_lastname):
                matches.append((main_id, "fuzzy_lastname"))
                continue

            # First name match
            if len(main_parts) >= 2:
                main_firstname = main_parts[0].strip(".,;:")
                if supp_name.lower() == main_firstname.lower():
                    matches.append((main_id, "exact_firstname"))
                    continue

                # Nickname match
                if _is_nickname_match(supp_name, main_firstname):
                    matches.append((main_id, "nickname"))

        if len(matches) == 1:
            main_id, match_type = matches[0]
            if "lastname" in match_type:
                graph.add_merge_edge(
                    supp_id, main_id,
                    EdgeType.LASTNAME_MATCH,
                    f"Cross-cast lastname ({match_type}): '{supp_name}' ↔ '{graph.nodes[main_id].canonical_name}'",
                    weight=0.60,  # Boosted since unambiguous
                )
            elif "firstname" in match_type:
                graph.add_merge_edge(
                    supp_id, main_id,
                    EdgeType.FIRSTNAME_MATCH,
                    f"Cross-cast firstname ({match_type}): '{supp_name}' ↔ '{graph.nodes[main_id].canonical_name}'",
                )
            elif "nickname" in match_type:
                graph.add_merge_edge(
                    supp_id, main_id,
                    EdgeType.NICKNAME,
                    f"Cross-cast nickname: '{supp_name}' ↔ '{graph.nodes[main_id].canonical_name}'",
                )
        elif len(matches) > 1:
            # Ambiguous surname - add constraints but still add weak evidence
            for main_id, match_type in matches:
                graph.add_constraint_edge(
                    supp_id, main_id,
                    ConstraintType.AMBIGUOUS_SURNAME,
                    f"Ambiguous cross-cast: '{supp_name}' matches {[graph.nodes[m[0]].canonical_name for m in matches]}",
                )

    # --- Reverse pass: single-word main ↔ multi-word supporting ---
    for main_id in main_ids:
        main_node = graph.nodes[main_id]
        main_name = main_node.canonical_name.strip()

        if not main_name or " " in main_name:
            continue  # Only single-word main cast

        matches = []
        for supp_id in supporting_ids:
            supp_node = graph.nodes[supp_id]
            supp_name = supp_node.canonical_name.strip()

            if not supp_name or " " not in supp_name:
                continue

            supp_parts = supp_name.split()
            supp_lastname = supp_parts[-1].strip(".,;:")
            supp_firstname = supp_parts[0].strip(".,;:")

            # Last name match
            if main_name.lower() == supp_lastname.lower():
                matches.append((supp_id, "exact_lastname"))
                continue
            if names_similar(main_name, supp_lastname):
                matches.append((supp_id, "fuzzy_lastname"))
                continue

            # First name match
            if main_name.lower() == supp_firstname.lower():
                matches.append((supp_id, "exact_firstname"))
                continue
            if names_similar(main_name, supp_firstname):
                matches.append((supp_id, "fuzzy_firstname"))
                continue

            # Nickname match
            if _is_nickname_match(main_name, supp_firstname):
                matches.append((supp_id, "nickname"))

        if len(matches) == 1:
            supp_id, match_type = matches[0]
            if "lastname" in match_type:
                graph.add_merge_edge(
                    main_id, supp_id,
                    EdgeType.LASTNAME_MATCH,
                    f"Reverse cross-cast ({match_type}): '{main_name}' ↔ '{graph.nodes[supp_id].canonical_name}'",
                    weight=0.60,
                )
            elif "firstname" in match_type:
                graph.add_merge_edge(
                    main_id, supp_id,
                    EdgeType.FIRSTNAME_MATCH,
                    f"Reverse cross-cast ({match_type}): '{main_name}' ↔ '{graph.nodes[supp_id].canonical_name}'",
                )
            elif "nickname" in match_type:
                graph.add_merge_edge(
                    main_id, supp_id,
                    EdgeType.NICKNAME,
                    f"Reverse cross-cast nickname: '{main_name}' ↔ '{graph.nodes[supp_id].canonical_name}'",
                )


# ---------------------------------------------------------------------------
# Collector 5: Synonym evidence (cross-cast descriptive synonyms)
# Ports logic from _merge_descriptive_synonyms_across_casts
# ---------------------------------------------------------------------------

def collect_synonym_evidence(graph: IdentityGraph) -> None:
    """
    Add merge edges for descriptive synonym relationships across casts.

    Detects: "the creature" (main) ↔ "the monster" (supporting) → same synonym group.
    """
    main_ids = [nid for nid, n in graph.nodes.items() if n.is_main_cast]
    supporting_ids = [nid for nid, n in graph.nodes.items() if not n.is_main_cast]

    for main_id in main_ids:
        main_node = graph.nodes[main_id]
        main_name_lower = main_node.canonical_name.lower().strip()

        if not main_name_lower.startswith("the "):
            continue

        # Normalize descriptor
        main_desc = main_name_lower[4:].strip()
        if " (" in main_desc:
            main_desc = main_desc.split(" (")[0].strip()
        main_desc = main_desc.strip(".,;:!?\"'""")

        for group in SYNONYM_GROUPS:
            if main_desc not in group:
                continue

            # Found a match - check supporting cast
            for supp_id in supporting_ids:
                supp_node = graph.nodes[supp_id]
                supp_name_lower = supp_node.canonical_name.lower().strip()

                if not supp_name_lower.startswith("the "):
                    continue

                supp_desc = supp_name_lower[4:].strip()
                if " (" in supp_desc:
                    supp_desc = supp_desc.split(" (")[0].strip()
                supp_desc = supp_desc.strip(".,;:!?\"'""")

                if supp_desc in group:
                    graph.add_merge_edge(
                        main_id, supp_id,
                        EdgeType.DESCRIPTIVE_SYNONYM,
                        f"Cross-cast synonym: '{main_node.canonical_name}' ↔ '{supp_node.canonical_name}' (group: {group})",
                    )


# ---------------------------------------------------------------------------
# Collector 6: Narrator evidence
# Ports logic from _merge_narrator_placeholder
# ---------------------------------------------------------------------------

def collect_narrator_evidence(
    graph: IdentityGraph,
    narrator_info,
) -> None:
    """
    Add merge edges for narrator placeholder resolution.

    Detects: narrator placeholder ("the protagonist") → actual named character.
    """
    if not narrator_info or narrator_info.pov != "first-person":
        return
    if not narrator_info.narrator_character_id:
        return

    narrator_id = narrator_info.narrator_character_id
    narrator_node = graph.nodes.get(narrator_id)
    if not narrator_node:
        return

    # Check if narrator is a placeholder
    narrator_lower = narrator_node.canonical_name.lower()
    is_placeholder = any(
        pattern in narrator_lower for pattern in NARRATOR_PLACEHOLDER_PATTERNS
    )

    if not is_placeholder:
        return

    logger.info(
        f"Narrator placeholder detected: '{narrator_node.canonical_name}' — scanning for match"
    )

    # PRIORITY 1: Match narrator_info.narrator_name to other characters
    if narrator_info.narrator_name:
        narrator_name_lower = narrator_info.narrator_name.lower()
        for nid, node in graph.nodes.items():
            if nid == narrator_id:
                continue

            candidate_lower = node.canonical_name.lower()

            # Skip other placeholders and generic descriptors
            if any(p in candidate_lower for p in NARRATOR_PLACEHOLDER_PATTERNS):
                continue
            if candidate_lower.startswith("the ") and len(node.canonical_name.split()) <= 3:
                continue

            # Name match
            if (
                narrator_name_lower == candidate_lower
                or narrator_name_lower in candidate_lower
                or candidate_lower in narrator_name_lower
            ):
                graph.add_merge_edge(
                    narrator_id, nid,
                    EdgeType.NARRATOR_PLACEHOLDER,
                    f"Narrator placeholder '{narrator_node.canonical_name}' → '{node.canonical_name}' (name match via narrator_info)",
                )
                return  # Only match one

    # PRIORITY 2: Highest-mention candidate
    best_id = None
    best_mentions = 0
    for nid, node in graph.nodes.items():
        if nid == narrator_id:
            continue
        candidate_lower = node.canonical_name.lower()
        if any(p in candidate_lower for p in NARRATOR_PLACEHOLDER_PATTERNS):
            continue
        if candidate_lower.startswith("the ") and len(node.canonical_name.split()) <= 3:
            continue
        if not node.canonical_name[0].isupper():
            continue
        if node.mention_count > best_mentions:
            best_mentions = node.mention_count
            best_id = nid

    if best_id:
        graph.add_merge_edge(
            narrator_id, best_id,
            EdgeType.NARRATOR_PLACEHOLDER,
            f"Narrator placeholder '{narrator_node.canonical_name}' → '{graph.nodes[best_id].canonical_name}' (highest mentions: {best_mentions})",
            weight=0.70,  # Lower weight for heuristic match
        )


# ---------------------------------------------------------------------------
# Collector 7: LLM evidence
# Wraps LLM Pass 2 alias consolidation results
# ---------------------------------------------------------------------------

def collect_llm_evidence(
    graph: IdentityGraph,
    llm_pass2_results: Optional[dict] = None,
) -> None:
    """
    Add merge edges from LLM Pass 2 alias consolidation results.

    llm_pass2_results format (if provided):
    {
        "char_id_a": ["alias1", "alias2"],  # LLM identified these as aliases
        ...
    }

    Since LLM Pass 2 results are already incorporated into character aliases
    by the main cast extractor, this collector checks for cross-character
    alias overlaps that the LLM identified.
    """
    if not llm_pass2_results:
        return

    # Build reverse map: alias → character IDs that claim it
    alias_to_ids: dict[str, list[str]] = {}

    for char_id, aliases in llm_pass2_results.items():
        if char_id not in graph.nodes:
            continue
        for alias in aliases:
            alias_lower = alias.lower()
            if alias_lower not in alias_to_ids:
                alias_to_ids[alias_lower] = []
            alias_to_ids[alias_lower].append(char_id)

    # If multiple characters share an alias, add merge evidence
    for alias, char_ids in alias_to_ids.items():
        if len(char_ids) < 2:
            continue
        for i, id_a in enumerate(char_ids):
            for id_b in char_ids[i + 1:]:
                graph.add_merge_edge(
                    id_a, id_b,
                    EdgeType.LLM_IDENTIFIED,
                    f"LLM identified shared alias '{alias}'",
                )


# ---------------------------------------------------------------------------
# Collector 8: Constraint evidence (generates constraint edges)
# This is new — the sequential approach had implicit constraints baked in
# ---------------------------------------------------------------------------

def collect_constraint_evidence(graph: IdentityGraph) -> None:
    """
    Generate constraint edges from character metadata.

    Detects:
    - Different titled people: "Mr. White" vs "Mrs. White"
    - Different first names with same surname: "George Wilson" vs "Myrtle Wilson"
    - Role conflicts: father vs son with same name
    """
    node_ids = list(graph.nodes.keys())

    for i, id_a in enumerate(node_ids):
        node_a = graph.nodes[id_a]
        name_a = node_a.canonical_name.strip()

        for id_b in node_ids[i + 1:]:
            node_b = graph.nodes[id_b]
            name_b = node_b.canonical_name.strip()

            # --- Different titled people ---
            if _are_different_titled_people(name_a, name_b):
                graph.add_constraint_edge(
                    id_a, id_b,
                    ConstraintType.DIFFERENT_TITLES,
                    f"Different titles: '{name_a}' vs '{name_b}'",
                )

            # --- Different first names with shared surname ---
            parts_a = name_a.split()
            parts_b = name_b.split()

            if len(parts_a) >= 2 and len(parts_b) >= 2:
                lastname_a = parts_a[-1].strip(".,;:").lower()
                lastname_b = parts_b[-1].strip(".,;:").lower()
                firstname_a = parts_a[0].strip(".,;:").lower()
                firstname_b = parts_b[0].strip(".,;:").lower()

                # Same surname, different first names
                if (
                    lastname_a == lastname_b
                    and firstname_a != firstname_b
                    and not _is_nickname_match(firstname_a, firstname_b)
                ):
                    graph.add_constraint_edge(
                        id_a, id_b,
                        ConstraintType.DIFFERENT_FIRST_NAMES,
                        f"Same surname, different first names: '{name_a}' vs '{name_b}'",
                    )

            # --- Role conflict detection (from descriptions) ---
            desc_a = " ".join(node_a.descriptions).lower()
            desc_b = " ".join(node_b.descriptions).lower()

            # Check for explicit generational relationships
            gen_terms_a = {"father", "mother", "parent", "grandfather", "grandmother", "elder"}
            gen_terms_b = {"son", "daughter", "child", "grandson", "granddaughter", "younger"}

            a_is_parent = bool(gen_terms_a & set(desc_a.split()))
            a_is_child = bool(gen_terms_b & set(desc_a.split()))
            b_is_parent = bool(gen_terms_a & set(desc_b.split()))
            b_is_child = bool(gen_terms_b & set(desc_b.split()))

            if (a_is_parent and b_is_child) or (a_is_child and b_is_parent):
                # Check if they share a name component
                name_overlap = bool(
                    set(name_a.lower().split()) & set(name_b.lower().split())
                )
                if name_overlap:
                    graph.add_constraint_edge(
                        id_a, id_b,
                        ConstraintType.ROLE_CONFLICT,
                        f"Generational conflict: '{name_a}' ({desc_a[:80]}) vs '{name_b}' ({desc_b[:80]})",
                    )


# ---------------------------------------------------------------------------
# Collector 9: Surname into family descriptive evidence
# Ports logic from _merge_surname_into_family_descriptive
# ---------------------------------------------------------------------------

def collect_surname_family_evidence(graph: IdentityGraph) -> None:
    """
    Add merge edges for bare surnames matching family descriptive handles.

    Detects: "De Lacey" (supporting) → "the old man" (main, father of Felix/Agatha De Lacey).
    """
    main_ids = [nid for nid, n in graph.nodes.items() if n.is_main_cast]
    supporting_ids = [nid for nid, n in graph.nodes.items() if not n.is_main_cast]

    # Build surname → main cast family members map
    surname_to_chars: dict[str, list[str]] = {}
    for main_id in main_ids:
        node = graph.nodes[main_id]
        parts = node.canonical_name.split()
        if len(parts) >= 2:
            surname = parts[-1].lower()
            if surname not in surname_to_chars:
                surname_to_chars[surname] = []
            surname_to_chars[surname].append(main_id)

    for supp_id in supporting_ids:
        supp_node = graph.nodes[supp_id]
        supp_name = supp_node.canonical_name.strip()
        supp_lower = supp_name.lower()

        # Only process bare surnames (single word, capitalized)
        if " " in supp_name or not supp_name or not supp_name[0].isupper():
            continue
        if supp_lower.startswith("the "):
            continue

        if supp_lower not in surname_to_chars:
            continue

        family_ids = surname_to_chars[supp_lower]
        if len(family_ids) < 2:
            continue  # Need 2+ family members

        # Check if any descriptive main cast character is a family member
        for main_id in main_ids:
            main_node = graph.nodes[main_id]
            main_name_lower = main_node.canonical_name.lower().strip()

            if not main_name_lower.startswith("the "):
                continue

            # Already has this surname?
            if any(supp_lower in alias.lower() for alias in main_node.aliases):
                continue

            # Check family relationship via descriptions
            desc = " ".join(main_node.descriptions).lower()
            family_indicators = ["father", "mother", "parent", "patriarch", "matriarch"]
            is_family = any(ind in desc for ind in family_indicators)

            if not is_family:
                for fam_id in family_ids:
                    fam_node = graph.nodes[fam_id]
                    first_name = fam_node.canonical_name.split()[0].lower()
                    if first_name in desc:
                        is_family = True
                        break

            if is_family:
                graph.add_merge_edge(
                    supp_id, main_id,
                    EdgeType.SURNAME_FAMILY,
                    f"Surname '{supp_name}' → descriptive '{main_node.canonical_name}' (family relationship)",
                )


# ---------------------------------------------------------------------------
# Master collector: runs all collectors
# ---------------------------------------------------------------------------

def collect_all_evidence(
    graph: IdentityGraph,
    narrator_info=None,
    cooccurrence: Optional[dict] = None,
    llm_pass2_results: Optional[dict] = None,
) -> None:
    """
    Run all evidence collectors on the graph.

    This is the main entry point for Phase 1 shadow mode.

    Args:
        graph: Populated IdentityGraph with character nodes
        narrator_info: NarratorInfo from narrator detection
        cooccurrence: Pre-computed co-occurrence dict
        llm_pass2_results: Optional LLM alias consolidation results
    """
    logger.info("Collecting all identity evidence...")

    # 1. Constraint evidence (should run first to establish constraints)
    logger.info("  Collecting constraint evidence...")
    collect_constraint_evidence(graph)

    # 2. Title variant evidence
    logger.info("  Collecting title variant evidence...")
    collect_title_variant_evidence(graph)

    # 3. Within-cast evidence (both main and supporting)
    logger.info("  Collecting within-cast evidence...")
    collect_within_cast_evidence(graph)

    # 4. Co-occurrence evidence
    if cooccurrence:
        logger.info("  Collecting co-occurrence evidence...")
        collect_cooccurrence_evidence(graph, cooccurrence)

    # 5. Cross-cast evidence
    logger.info("  Collecting cross-cast evidence...")
    collect_cross_cast_evidence(graph)

    # 6. Synonym evidence
    logger.info("  Collecting synonym evidence...")
    collect_synonym_evidence(graph)

    # 7. Narrator evidence
    if narrator_info:
        logger.info("  Collecting narrator evidence...")
        collect_narrator_evidence(graph, narrator_info)

    # 8. LLM evidence
    if llm_pass2_results:
        logger.info("  Collecting LLM evidence...")
        collect_llm_evidence(graph, llm_pass2_results)

    # 9. Surname family evidence
    logger.info("  Collecting surname family evidence...")
    collect_surname_family_evidence(graph)

    logger.info(f"Evidence collection complete: {graph.summary()}")
