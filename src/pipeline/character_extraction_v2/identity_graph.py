"""
Identity Graph for Character Resolution

Replaces sequential merge passes with a declarative graph-based approach:
- Nodes = character entries (main cast + supporting cast)
- Positive edges = evidence two nodes are the same person (typed, weighted)
- Constraint edges = evidence two nodes are NOT the same person (hard/soft blocks)
- Resolution = connected components → constraint checking → atomic merge

This solves the fundamental problem with sequential merges: they can't express
"these two characters share a name but are DIFFERENT people" (e.g., father/son
John Donaldson in american_sir).
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ...utils.similarity import names_similar, string_similarity

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EdgeType(Enum):
    """Types of positive merge evidence."""
    TITLE_VARIANT = "title_variant"               # Mr. Smith ↔ Smith
    LASTNAME_MATCH = "lastname_match"              # shared surname
    FIRSTNAME_MATCH = "firstname_match"            # shared first name
    SPELLING_VARIANT = "spelling_variant"          # Catherine ↔ Katherine
    MIDDLE_INITIAL = "middle_initial"              # J. Smith ↔ John Smith
    DESCRIPTIVE_SYNONYM = "descriptive_synonym"    # the monster ↔ the creature
    NARRATOR_PLACEHOLDER = "narrator_placeholder"  # The Narrator ↔ detected name
    COOCCURRENCE = "cooccurrence"                  # high Jaccard similarity
    LLM_IDENTIFIED = "llm_identified"              # LLM said same person
    NICKNAME = "nickname"                          # Jim ↔ James
    THE_VARIANT = "the_variant"                    # "owl-eyed man" ↔ "the owl-eyed man"
    PERIOD_ABBREVIATION = "period_abbreviation"    # "John G." ↔ "John"
    NAME_CONTAINMENT = "name_containment"          # "Sergeant-Major Morris" contains "Morris"
    FULL_NAME_FUZZY = "full_name_fuzzy"            # full name fuzzy match across casts
    SURNAME_FAMILY = "surname_family"              # bare surname into family descriptive


class ConstraintType(Enum):
    """Types of negative constraint evidence."""
    DIFFERENT_TITLES = "different_titles"           # Mr. X vs Mrs. X
    DIFFERENT_FIRST_NAMES = "different_first_names" # John Smith vs Jane Smith
    ROLE_CONFLICT = "role_conflict"                 # father vs son, even if same name
    SAME_SCENE_DISTINCT = "same_scene_distinct"     # appear together as distinct actors
    AMBIGUOUS_SURNAME = "ambiguous_surname"         # shared surname, different first names


# ---------------------------------------------------------------------------
# Edge weight defaults
# ---------------------------------------------------------------------------

DEFAULT_WEIGHTS: dict[EdgeType, float] = {
    EdgeType.TITLE_VARIANT: 0.85,
    EdgeType.LASTNAME_MATCH: 0.40,
    EdgeType.FIRSTNAME_MATCH: 0.35,
    EdgeType.SPELLING_VARIANT: 0.65,
    EdgeType.MIDDLE_INITIAL: 0.95,
    EdgeType.DESCRIPTIVE_SYNONYM: 0.60,
    EdgeType.NARRATOR_PLACEHOLDER: 0.90,
    EdgeType.COOCCURRENCE: 0.70,
    EdgeType.LLM_IDENTIFIED: 0.80,
    EdgeType.NICKNAME: 0.75,
    EdgeType.THE_VARIANT: 0.85,
    EdgeType.PERIOD_ABBREVIATION: 0.80,
    EdgeType.NAME_CONTAINMENT: 0.85,
    EdgeType.FULL_NAME_FUZZY: 0.70,
    EdgeType.SURNAME_FAMILY: 0.55,
}

DEFAULT_STRENGTHS: dict[ConstraintType, float] = {
    ConstraintType.DIFFERENT_TITLES: 1.0,       # hard block
    ConstraintType.DIFFERENT_FIRST_NAMES: 0.9,
    ConstraintType.ROLE_CONFLICT: 0.9,
    ConstraintType.SAME_SCENE_DISTINCT: 0.8,
    ConstraintType.AMBIGUOUS_SURNAME: 0.7,
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class MergeEdge:
    """Positive evidence that two characters are the same person."""
    source: str          # character id
    target: str          # character id
    edge_type: EdgeType
    weight: float
    reason: str

    def __repr__(self) -> str:
        return f"MergeEdge({self.source}→{self.target}, {self.edge_type.value}, w={self.weight:.2f}, {self.reason})"


@dataclass
class ConstraintEdge:
    """Negative evidence that two characters are NOT the same person."""
    source: str              # character id
    target: str              # character id
    constraint_type: ConstraintType
    strength: float
    reason: str

    def __repr__(self) -> str:
        return f"ConstraintEdge({self.source}↔{self.target}, {self.constraint_type.value}, s={self.strength:.2f}, {self.reason})"


@dataclass
class CharacterNode:
    """A node in the identity graph representing a single character entry."""
    char_id: str
    canonical_name: str
    aliases: list[str]
    mention_count: int
    role: Optional[str]
    is_narrator: bool
    is_main_cast: bool       # True = main cast, False = supporting
    descriptions: list[str]  # Description texts for relationship detection


@dataclass
class MergeGroup:
    """A resolved group of character nodes that should be merged."""
    canonical_node_id: str   # The node chosen as canonical
    canonical_name: str      # The chosen canonical name
    member_ids: list[str]    # All node IDs in this group
    aliases: list[str]       # All collected aliases
    evidence: list[MergeEdge]      # Evidence supporting this merge
    constraints_overridden: list[ConstraintEdge]  # Soft constraints that were overridden


class IdentityGraph:
    """
    Graph-based identity resolution for characters.

    Usage:
        graph = IdentityGraph()
        graph.add_characters(main_cast, supporting_cast)

        # Collect evidence (replaces sequential merge passes)
        collect_title_variant_evidence(graph, ...)
        collect_within_cast_evidence(graph, ...)
        ...

        # Resolve
        merge_groups = resolve_identities(graph)
        final_main, final_supporting = execute_merges(merge_groups, main_cast, supporting_cast)
    """

    def __init__(self) -> None:
        self.nodes: dict[str, CharacterNode] = {}
        self.merge_edges: list[MergeEdge] = []
        self.constraint_edges: list[ConstraintEdge] = []

    def add_character(self, char, *, is_main_cast: bool) -> None:
        """Add a character as a node in the graph."""
        descriptions = []
        if hasattr(char, 'descriptions') and char.descriptions:
            descriptions = [d.text if hasattr(d, 'text') else str(d) for d in char.descriptions]
        if hasattr(char, 'description') and char.description:
            descriptions.append(char.description if isinstance(char.description, str) else str(char.description))

        self.nodes[char.id] = CharacterNode(
            char_id=char.id,
            canonical_name=char.canonical_name,
            aliases=list(char.aliases),
            mention_count=char.mention_count,
            role=getattr(char, 'role', None),
            is_narrator=getattr(char, 'is_narrator', False),
            is_main_cast=is_main_cast,
            descriptions=descriptions,
        )

    def add_characters(self, main_cast: list, supporting_cast: list) -> None:
        """Add all characters from both casts."""
        for char in main_cast:
            self.add_character(char, is_main_cast=True)
        for char in supporting_cast:
            self.add_character(char, is_main_cast=False)

    def add_merge_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: EdgeType,
        reason: str,
        weight: Optional[float] = None,
    ) -> None:
        """Add positive merge evidence between two characters."""
        if source_id == target_id:
            return
        if source_id not in self.nodes or target_id not in self.nodes:
            logger.warning(
                f"Skipping merge edge: node not found ({source_id} or {target_id})"
            )
            return

        w = weight if weight is not None else DEFAULT_WEIGHTS.get(edge_type, 0.5)
        edge = MergeEdge(
            source=source_id,
            target=target_id,
            edge_type=edge_type,
            weight=w,
            reason=reason,
        )
        self.merge_edges.append(edge)
        logger.debug(f"Added {edge}")

    def add_constraint_edge(
        self,
        source_id: str,
        target_id: str,
        constraint_type: ConstraintType,
        reason: str,
        strength: Optional[float] = None,
    ) -> None:
        """Add negative constraint evidence between two characters."""
        if source_id == target_id:
            return
        if source_id not in self.nodes or target_id not in self.nodes:
            return

        s = strength if strength is not None else DEFAULT_STRENGTHS.get(constraint_type, 0.5)
        edge = ConstraintEdge(
            source=source_id,
            target=target_id,
            constraint_type=constraint_type,
            strength=s,
            reason=reason,
        )
        self.constraint_edges.append(edge)
        logger.debug(f"Added {edge}")

    def get_merge_edges_for(self, char_id: str) -> list[MergeEdge]:
        """Get all merge edges involving a character."""
        return [
            e for e in self.merge_edges
            if e.source == char_id or e.target == char_id
        ]

    def get_constraint_edges_for(self, char_id: str) -> list[ConstraintEdge]:
        """Get all constraint edges involving a character."""
        return [
            e for e in self.constraint_edges
            if e.source == char_id or e.target == char_id
        ]

    def get_constraints_between(self, id_a: str, id_b: str) -> list[ConstraintEdge]:
        """Get all constraint edges between two specific characters."""
        return [
            e for e in self.constraint_edges
            if (e.source == id_a and e.target == id_b)
            or (e.source == id_b and e.target == id_a)
        ]

    def get_merge_evidence_between(self, id_a: str, id_b: str) -> list[MergeEdge]:
        """Get all merge edges between two specific characters."""
        return [
            e for e in self.merge_edges
            if (e.source == id_a and e.target == id_b)
            or (e.source == id_b and e.target == id_a)
        ]

    def summary(self) -> str:
        """Return a human-readable summary of the graph."""
        return (
            f"IdentityGraph: {len(self.nodes)} nodes, "
            f"{len(self.merge_edges)} merge edges, "
            f"{len(self.constraint_edges)} constraint edges"
        )


# ---------------------------------------------------------------------------
# Resolution algorithm
# ---------------------------------------------------------------------------

def _build_adjacency(
    nodes: dict[str, CharacterNode],
    edges: list[MergeEdge],
    min_weight: float = 0.0,
) -> dict[str, set[str]]:
    """Build adjacency list from merge edges above min_weight threshold."""
    adj: dict[str, set[str]] = {nid: set() for nid in nodes}
    for e in edges:
        if e.weight > min_weight and e.source in adj and e.target in adj:
            adj[e.source].add(e.target)
            adj[e.target].add(e.source)
    return adj


def _find_connected_components(adj: dict[str, set[str]]) -> list[set[str]]:
    """Find connected components using BFS."""
    visited: set[str] = set()
    components: list[set[str]] = []

    for node in adj:
        if node in visited:
            continue
        # BFS
        component: set[str] = set()
        queue = [node]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            component.add(current)
            for neighbor in adj.get(current, set()):
                if neighbor not in visited:
                    queue.append(neighbor)
        if component:
            components.append(component)

    return components


def _split_by_hard_constraints(
    component: set[str],
    constraint_edges: list[ConstraintEdge],
) -> list[set[str]]:
    """
    Split a component by hard constraints (strength == 1.0).

    If A and B are in the same component but have a hard constraint,
    remove the weaker merge path and split into sub-components.
    """
    # Find hard constraints within this component
    hard_constraints = [
        e for e in constraint_edges
        if e.strength >= 1.0
        and e.source in component
        and e.target in component
    ]

    if not hard_constraints:
        return [component]

    # Build a "must not merge" set of pairs
    blocked_pairs: set[tuple[str, str]] = set()
    for c in hard_constraints:
        pair = tuple(sorted([c.source, c.target]))
        blocked_pairs.add(pair)

    # Greedy splitting: assign each node to a sub-component,
    # ensuring no blocked pairs end up together
    sub_components: list[set[str]] = []
    assigned: dict[str, int] = {}  # node_id -> sub_component index

    for node in component:
        placed = False
        for idx, sc in enumerate(sub_components):
            # Check if placing this node violates any hard constraint
            violates = False
            for existing in sc:
                pair = tuple(sorted([node, existing]))
                if pair in blocked_pairs:
                    violates = True
                    break
            if not violates:
                sc.add(node)
                assigned[node] = idx
                placed = True
                break

        if not placed:
            # Create new sub-component
            assigned[node] = len(sub_components)
            sub_components.append({node})

    return sub_components


def _evaluate_soft_constraints(
    component: set[str],
    merge_edges: list[MergeEdge],
    constraint_edges: list[ConstraintEdge],
) -> list[set[str]]:
    """
    Evaluate soft constraints within a component.

    For each pair with soft constraints, compare:
    - sum of merge evidence weights
    - sum of constraint strengths

    If constraints outweigh evidence, split the pair apart.
    """
    # Find soft constraints within this component
    soft_constraints = [
        e for e in constraint_edges
        if e.strength < 1.0
        and e.source in component
        and e.target in component
    ]

    if not soft_constraints:
        return [component]

    # For each constrained pair, check if merge evidence outweighs constraints
    pairs_to_split: set[tuple[str, str]] = set()

    for constraint in soft_constraints:
        pair = tuple(sorted([constraint.source, constraint.target]))
        if pair in pairs_to_split:
            continue

        # Sum merge evidence between these two nodes
        merge_weight = sum(
            e.weight for e in merge_edges
            if (e.source == constraint.source and e.target == constraint.target)
            or (e.source == constraint.target and e.target == constraint.source)
        )

        # Sum constraint strength between these two nodes
        constraint_strength = sum(
            e.strength for e in constraint_edges
            if (e.source == constraint.source and e.target == constraint.target)
            or (e.source == constraint.target and e.target == constraint.source)
        )

        if constraint_strength > merge_weight:
            pairs_to_split.add(pair)
            logger.info(
                f"Soft constraint wins: splitting {pair} "
                f"(merge_weight={merge_weight:.2f}, constraint={constraint_strength:.2f})"
            )

    if not pairs_to_split:
        return [component]

    # Greedy splitting (same approach as hard constraints)
    sub_components: list[set[str]] = []
    for node in component:
        placed = False
        for idx, sc in enumerate(sub_components):
            violates = False
            for existing in sc:
                pair = tuple(sorted([node, existing]))
                if pair in pairs_to_split:
                    violates = True
                    break
            if not violates:
                sc.add(node)
                placed = True
                break
        if not placed:
            sub_components.append({node})

    return sub_components


def _select_canonical(
    component: set[str],
    nodes: dict[str, CharacterNode],
) -> tuple[str, str]:
    """
    Select the canonical node and name for a merge group.

    Preference order:
    1. Main cast over supporting cast
    2. Full name (multi-word) over single-word
    3. Proper name over descriptive handle ("the X")
    4. Higher mention count
    5. Longer name (more specific)
    """
    members = [nodes[nid] for nid in component if nid in nodes]
    if not members:
        nid = next(iter(component))
        return nid, nid

    def sort_key(node: CharacterNode):
        name = node.canonical_name
        is_main = 1 if node.is_main_cast else 0
        is_multi_word = 1 if " " in name else 0
        is_proper = 0 if name.lower().startswith("the ") else 1
        mention_count = node.mention_count
        name_len = len(name)
        return (is_main, is_proper, is_multi_word, mention_count, name_len)

    members.sort(key=sort_key, reverse=True)
    best = members[0]
    return best.char_id, best.canonical_name


def _collect_aliases_for_group(
    component: set[str],
    canonical_id: str,
    canonical_name: str,
    nodes: dict[str, CharacterNode],
) -> list[str]:
    """Collect all aliases for a merge group, deduplicating."""
    aliases_set: set[str] = set()

    for nid in component:
        node = nodes.get(nid)
        if not node:
            continue

        # Add canonical name of non-canonical nodes as aliases
        if nid != canonical_id and node.canonical_name != canonical_name:
            aliases_set.add(node.canonical_name)

        # Add all existing aliases
        for alias in node.aliases:
            if alias != canonical_name:
                aliases_set.add(alias)

    return sorted(aliases_set)


def resolve_identities(
    graph: IdentityGraph,
    min_edge_weight: float = 0.0,
) -> list[MergeGroup]:
    """
    Resolve the identity graph into merge groups.

    Algorithm:
    1. Build adjacency from merge edges
    2. Find connected components
    3. For each component:
       a. Split by hard constraints (strength >= 1.0)
       b. Evaluate soft constraints (compare weights vs strengths)
    4. For each final sub-component:
       a. Select canonical name
       b. Collect aliases
    5. Return merge groups

    Args:
        graph: The populated identity graph
        min_edge_weight: Minimum edge weight to consider (default 0.0 = all edges)

    Returns:
        List of MergeGroup objects describing how to merge characters
    """
    logger.info(f"Resolving identity graph: {graph.summary()}")

    # Step 1: Build adjacency
    adj = _build_adjacency(graph.nodes, graph.merge_edges, min_edge_weight)

    # Step 2: Find connected components
    components = _find_connected_components(adj)
    logger.info(f"Found {len(components)} connected components")

    # Step 3 & 4: Process each component
    merge_groups: list[MergeGroup] = []

    for component in components:
        if len(component) <= 1:
            # Single node — no merge needed, but still create a group for consistency
            nid = next(iter(component))
            node = graph.nodes.get(nid)
            if node:
                merge_groups.append(MergeGroup(
                    canonical_node_id=nid,
                    canonical_name=node.canonical_name,
                    member_ids=[nid],
                    aliases=list(node.aliases),
                    evidence=[],
                    constraints_overridden=[],
                ))
            continue

        # Step 3a: Split by hard constraints
        sub_components = _split_by_hard_constraints(component, graph.constraint_edges)

        # Step 3b: Evaluate soft constraints on each sub-component
        final_components: list[set[str]] = []
        for sc in sub_components:
            if len(sc) <= 1:
                final_components.append(sc)
            else:
                split_result = _evaluate_soft_constraints(
                    sc, graph.merge_edges, graph.constraint_edges,
                )
                final_components.extend(split_result)

        # Step 4: Build merge groups from final components
        for fc in final_components:
            canonical_id, canonical_name = _select_canonical(fc, graph.nodes)
            aliases = _collect_aliases_for_group(fc, canonical_id, canonical_name, graph.nodes)

            # Collect evidence for this group
            evidence = [
                e for e in graph.merge_edges
                if e.source in fc and e.target in fc
            ]

            # Note any overridden soft constraints
            overridden = [
                e for e in graph.constraint_edges
                if e.source in fc and e.target in fc and e.strength < 1.0
            ]

            merge_groups.append(MergeGroup(
                canonical_node_id=canonical_id,
                canonical_name=canonical_name,
                member_ids=sorted(fc),
                aliases=aliases,
                evidence=evidence,
                constraints_overridden=overridden,
            ))

            if len(fc) > 1:
                member_names = [graph.nodes[nid].canonical_name for nid in fc if nid in graph.nodes]
                logger.info(
                    f"Merge group: {canonical_name} ← {member_names} "
                    f"({len(evidence)} evidence, {len(overridden)} overridden constraints)"
                )

    logger.info(
        f"Resolution complete: {len(merge_groups)} groups "
        f"({sum(1 for g in merge_groups if len(g.member_ids) > 1)} with merges)"
    )

    return merge_groups


# ---------------------------------------------------------------------------
# Merge execution
# ---------------------------------------------------------------------------

def execute_merges(
    merge_groups: list[MergeGroup],
    main_cast: list,
    supporting_cast: list,
    is_valid_alias_fn=None,
) -> tuple[list, list]:
    """
    Execute merge groups atomically against the character lists.

    For each merge group with >1 member:
    - Keep the canonical character
    - Transfer aliases, mentions, descriptions from absorbed characters
    - Remove absorbed characters from their respective lists

    Args:
        merge_groups: Resolved merge groups from resolve_identities()
        main_cast: List of main cast Character objects
        supporting_cast: List of supporting cast Character objects
        is_valid_alias_fn: Optional function(alias, canonical_name) -> bool

    Returns:
        Tuple of (updated_main_cast, updated_supporting_cast)
    """
    # Build lookup maps
    main_by_id = {c.id: c for c in main_cast}
    supporting_by_id = {c.id: c for c in supporting_cast}
    all_by_id = {**main_by_id, **supporting_by_id}

    # Track which characters to remove
    ids_to_remove: set[str] = set()

    for group in merge_groups:
        if len(group.member_ids) <= 1:
            continue

        canonical_char = all_by_id.get(group.canonical_node_id)
        if not canonical_char:
            logger.warning(f"Canonical character not found: {group.canonical_node_id}")
            continue

        # Update canonical name if resolution chose a different one
        if canonical_char.canonical_name != group.canonical_name:
            old_name = canonical_char.canonical_name
            # Add old canonical name as alias
            if old_name not in canonical_char.aliases:
                canonical_char.aliases.append(old_name)
            canonical_char.canonical_name = group.canonical_name

        # Add all aliases from the merge group
        for alias in group.aliases:
            if alias not in canonical_char.aliases and alias != canonical_char.canonical_name:
                if is_valid_alias_fn is None or is_valid_alias_fn(alias, canonical_char.canonical_name):
                    canonical_char.aliases.append(alias)

        # Transfer data from absorbed characters
        for member_id in group.member_ids:
            if member_id == group.canonical_node_id:
                continue

            absorbed = all_by_id.get(member_id)
            if not absorbed:
                continue

            # Transfer mention count
            canonical_char.mention_count += absorbed.mention_count

            # Transfer mentions list
            if hasattr(absorbed, 'mentions') and absorbed.mentions:
                if not canonical_char.mentions:
                    canonical_char.mentions = []
                canonical_char.mentions.extend(absorbed.mentions)

            # Transfer descriptions
            if hasattr(absorbed, 'descriptions') and absorbed.descriptions:
                if not canonical_char.descriptions:
                    canonical_char.descriptions = []
                for desc in absorbed.descriptions:
                    if desc not in canonical_char.descriptions:
                        canonical_char.descriptions.append(desc)

            # Transfer narrator flag
            if getattr(absorbed, 'is_narrator', False):
                canonical_char.is_narrator = True
                if not canonical_char.narrative_role and hasattr(absorbed, 'narrative_role'):
                    canonical_char.narrative_role = absorbed.narrative_role

            # Mark for removal
            ids_to_remove.add(member_id)

            logger.info(
                f"Merged '{absorbed.canonical_name}' into '{canonical_char.canonical_name}'"
            )

    # Remove absorbed characters
    updated_main = [c for c in main_cast if c.id not in ids_to_remove]
    updated_supporting = [c for c in supporting_cast if c.id not in ids_to_remove]

    logger.info(
        f"Merge execution: removed {len(ids_to_remove)} characters "
        f"(main: {len(main_cast)}→{len(updated_main)}, "
        f"supporting: {len(supporting_cast)}→{len(updated_supporting)})"
    )

    return updated_main, updated_supporting


# ---------------------------------------------------------------------------
# Shadow mode comparison
# ---------------------------------------------------------------------------

def compare_results(
    graph_main: list,
    graph_supporting: list,
    sequential_main: list,
    sequential_supporting: list,
) -> dict:
    """
    Compare graph resolution results against sequential merge results.

    Returns a dict with:
    - matches: characters present in both with same aliases
    - graph_only_merges: merges that graph did but sequential didn't
    - sequential_only_merges: merges that sequential did but graph didn't
    - alias_differences: characters where alias sets differ
    """
    def _char_signature(char) -> tuple[str, frozenset]:
        return (char.canonical_name, frozenset(char.aliases))

    # Build name→character maps
    graph_chars = {c.canonical_name: c for c in graph_main + graph_supporting}
    seq_chars = {c.canonical_name: c for c in sequential_main + sequential_supporting}

    # Find common canonical names
    graph_names = set(graph_chars.keys())
    seq_names = set(seq_chars.keys())

    matches = []
    alias_differences = []

    for name in graph_names & seq_names:
        g_aliases = set(graph_chars[name].aliases)
        s_aliases = set(seq_chars[name].aliases)
        if g_aliases == s_aliases:
            matches.append(name)
        else:
            alias_differences.append({
                "name": name,
                "graph_only_aliases": sorted(g_aliases - s_aliases),
                "sequential_only_aliases": sorted(s_aliases - g_aliases),
            })

    graph_only = sorted(graph_names - seq_names)
    sequential_only = sorted(seq_names - graph_names)

    result = {
        "matches": len(matches),
        "graph_only_characters": graph_only,
        "sequential_only_characters": sequential_only,
        "alias_differences": alias_differences,
        "total_graph": len(graph_chars),
        "total_sequential": len(seq_chars),
    }

    # Log summary
    logger.info(
        f"Shadow mode comparison: {result['matches']} matches, "
        f"{len(graph_only)} graph-only, {len(sequential_only)} sequential-only, "
        f"{len(alias_differences)} alias differences"
    )

    if alias_differences:
        for diff in alias_differences:
            logger.info(
                f"  Alias diff for '{diff['name']}': "
                f"graph-only={diff['graph_only_aliases']}, "
                f"seq-only={diff['sequential_only_aliases']}"
            )

    return result
