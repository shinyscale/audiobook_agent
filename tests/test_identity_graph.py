"""
Unit tests for Identity Graph resolution system.

Tests:
1. Basic graph construction and edge addition
2. Connected component detection
3. Hard constraint splitting (different titles)
4. Soft constraint evaluation (merge weight vs constraint strength)
5. Canonical name selection
6. John Donaldson father/son test (the key use case)
7. Evidence collectors (title variant, within-cast, cross-cast, synonyms)
8. Full pipeline integration test
"""

import pytest
from dataclasses import dataclass, field
from typing import Optional


# Mock Character class for testing without importing the full model
@dataclass
class MockCharacter:
    id: str
    canonical_name: str
    aliases: list = field(default_factory=list)
    mention_count: int = 0
    role: Optional[str] = None
    is_narrator: bool = False
    descriptions: list = field(default_factory=list)
    mentions: list = field(default_factory=list)
    narrative_role: Optional[str] = None
    confidence: str = "medium"

    @property
    def description(self):
        return self.descriptions[0] if self.descriptions else ""


@dataclass
class MockDescription:
    text: str
    source_position: int = 0


@dataclass
class MockNarratorInfo:
    pov: str = "third-person"
    narrator_name: Optional[str] = None
    narrator_character_id: Optional[str] = None
    nested_narrators: list = field(default_factory=list)


# Import the modules under test
from src.pipeline.character_extraction_v2.identity_graph import (
    IdentityGraph,
    EdgeType,
    ConstraintType,
    MergeEdge,
    ConstraintEdge,
    resolve_identities,
    execute_merges,
    compare_results,
    _find_connected_components,
    _split_by_hard_constraints,
    _select_canonical,
)
from src.pipeline.character_extraction_v2.evidence_collectors import (
    collect_title_variant_evidence,
    collect_within_cast_evidence,
    collect_cross_cast_evidence,
    collect_synonym_evidence,
    collect_narrator_evidence,
    collect_constraint_evidence,
    collect_cooccurrence_evidence,
    collect_surname_family_evidence,
    collect_all_evidence,
    _are_different_titled_people,
    _name_contains_other,
    _strip_title,
    _normalize_descriptor,
    _is_nickname_match,
)


# ---------------------------------------------------------------------------
# Graph construction tests
# ---------------------------------------------------------------------------

class TestGraphConstruction:
    def test_add_character(self):
        graph = IdentityGraph()
        char = MockCharacter(id="c1", canonical_name="Jay Gatsby", mention_count=100)
        graph.add_character(char, is_main_cast=True)
        assert "c1" in graph.nodes
        assert graph.nodes["c1"].canonical_name == "Jay Gatsby"
        assert graph.nodes["c1"].is_main_cast is True

    def test_add_characters_both_casts(self):
        graph = IdentityGraph()
        main = [MockCharacter(id="m1", canonical_name="Gatsby")]
        supporting = [MockCharacter(id="s1", canonical_name="Wolfsheim")]
        graph.add_characters(main, supporting)
        assert len(graph.nodes) == 2
        assert graph.nodes["m1"].is_main_cast is True
        assert graph.nodes["s1"].is_main_cast is False

    def test_add_merge_edge(self):
        graph = IdentityGraph()
        graph.add_character(MockCharacter(id="c1", canonical_name="A"), is_main_cast=True)
        graph.add_character(MockCharacter(id="c2", canonical_name="B"), is_main_cast=True)
        graph.add_merge_edge("c1", "c2", EdgeType.SPELLING_VARIANT, "test reason")
        assert len(graph.merge_edges) == 1
        assert graph.merge_edges[0].weight == 0.65  # default weight

    def test_add_constraint_edge(self):
        graph = IdentityGraph()
        graph.add_character(MockCharacter(id="c1", canonical_name="A"), is_main_cast=True)
        graph.add_character(MockCharacter(id="c2", canonical_name="B"), is_main_cast=True)
        graph.add_constraint_edge("c1", "c2", ConstraintType.DIFFERENT_TITLES, "test")
        assert len(graph.constraint_edges) == 1
        assert graph.constraint_edges[0].strength == 1.0  # hard block

    def test_self_edge_ignored(self):
        graph = IdentityGraph()
        graph.add_character(MockCharacter(id="c1", canonical_name="A"), is_main_cast=True)
        graph.add_merge_edge("c1", "c1", EdgeType.SPELLING_VARIANT, "self")
        assert len(graph.merge_edges) == 0

    def test_missing_node_edge_ignored(self):
        graph = IdentityGraph()
        graph.add_character(MockCharacter(id="c1", canonical_name="A"), is_main_cast=True)
        graph.add_merge_edge("c1", "nonexistent", EdgeType.SPELLING_VARIANT, "missing")
        assert len(graph.merge_edges) == 0


# ---------------------------------------------------------------------------
# Resolution algorithm tests
# ---------------------------------------------------------------------------

class TestResolution:
    def _make_graph(self, chars, edges=None, constraints=None):
        """Helper to build a graph quickly."""
        graph = IdentityGraph()
        for cid, name, is_main, mentions in chars:
            graph.add_character(
                MockCharacter(id=cid, canonical_name=name, mention_count=mentions),
                is_main_cast=is_main,
            )
        for src, tgt, etype, reason in (edges or []):
            graph.add_merge_edge(src, tgt, etype, reason)
        for src, tgt, ctype, reason in (constraints or []):
            graph.add_constraint_edge(src, tgt, ctype, reason)
        return graph

    def test_single_node_no_merge(self):
        graph = self._make_graph([("c1", "Gatsby", True, 100)])
        groups = resolve_identities(graph)
        assert len(groups) == 1
        assert groups[0].canonical_name == "Gatsby"
        assert len(groups[0].member_ids) == 1

    def test_simple_merge(self):
        graph = self._make_graph(
            [("c1", "Jay Gatsby", True, 100), ("c2", "Gatsby", True, 50)],
            [("c1", "c2", EdgeType.LASTNAME_MATCH, "lastname match")],
        )
        groups = resolve_identities(graph)
        # Should merge into one group
        merged = [g for g in groups if len(g.member_ids) > 1]
        assert len(merged) == 1
        assert "c1" in merged[0].member_ids
        assert "c2" in merged[0].member_ids
        # Canonical should be "Jay Gatsby" (multi-word, higher mentions)
        assert merged[0].canonical_name == "Jay Gatsby"

    def test_hard_constraint_splits_component(self):
        """Mr. White and Mrs. White should NOT be merged even with a name match."""
        graph = self._make_graph(
            [("c1", "Mr. White", True, 80), ("c2", "Mrs. White", True, 60)],
            [("c1", "c2", EdgeType.LASTNAME_MATCH, "shared surname")],
            [("c1", "c2", ConstraintType.DIFFERENT_TITLES, "Mr. vs Mrs.")],
        )
        groups = resolve_identities(graph)
        # Should be two separate groups
        merged = [g for g in groups if len(g.member_ids) > 1]
        assert len(merged) == 0
        assert len(groups) == 2

    def test_soft_constraint_merge_wins(self):
        """If merge evidence outweighs soft constraint, merge proceeds."""
        graph = self._make_graph(
            [("c1", "George Wilson", True, 100), ("c2", "Wilson", True, 60)],
            [
                ("c1", "c2", EdgeType.LASTNAME_MATCH, "lastname", ),
                ("c1", "c2", EdgeType.COOCCURRENCE, "high co-occurrence"),
            ],
            [("c1", "c2", ConstraintType.AMBIGUOUS_SURNAME, "ambiguous")],
        )
        groups = resolve_identities(graph)
        # Total merge weight: 0.40 + 0.70 = 1.10
        # Constraint strength: 0.70
        # Merge wins
        merged = [g for g in groups if len(g.member_ids) > 1]
        assert len(merged) == 1

    def test_soft_constraint_split_wins(self):
        """If soft constraint outweighs merge evidence, split occurs."""
        graph = self._make_graph(
            [("c1", "Character A", True, 100), ("c2", "Character B", True, 60)],
            [("c1", "c2", EdgeType.FIRSTNAME_MATCH, "weak match")],
            [
                ("c1", "c2", ConstraintType.DIFFERENT_FIRST_NAMES, "different first names"),
                ("c1", "c2", ConstraintType.ROLE_CONFLICT, "parent/child"),
            ],
        )
        groups = resolve_identities(graph)
        # Total merge weight: 0.35
        # Constraint strength: 0.9 + 0.9 = 1.8
        # Constraint wins
        merged = [g for g in groups if len(g.member_ids) > 1]
        assert len(merged) == 0

    def test_transitive_merge(self):
        """A-B and B-C should result in A,B,C merged."""
        graph = self._make_graph(
            [
                ("c1", "Sergeant-Major Morris", True, 80),
                ("c2", "Morris", True, 30),
                ("c3", "Sgt. Morris", True, 10),
            ],
            [
                ("c1", "c2", EdgeType.NAME_CONTAINMENT, "containment"),
                ("c2", "c3", EdgeType.SPELLING_VARIANT, "spelling"),
            ],
        )
        groups = resolve_identities(graph)
        merged = [g for g in groups if len(g.member_ids) > 1]
        assert len(merged) == 1
        assert len(merged[0].member_ids) == 3

    def test_canonical_prefers_main_cast(self):
        """Main cast node should be preferred as canonical over supporting."""
        graph = self._make_graph(
            [
                ("s1", "Meyer Wolfsheim", False, 20),
                ("m1", "Wolfsheim", True, 50),
            ],
            [("m1", "s1", EdgeType.LASTNAME_MATCH, "lastname")],
        )
        groups = resolve_identities(graph)
        merged = [g for g in groups if len(g.member_ids) > 1]
        assert len(merged) == 1
        # "Meyer Wolfsheim" is more specific (multi-word) but from supporting cast
        # However, main cast preference + higher mentions should favor "Wolfsheim"
        # Wait — actually _select_canonical prefers main_cast first, then proper name,
        # then multi-word, then mentions. Main-cast single-word beats supporting multi-word.
        # Let me check: m1 is main (1), proper (1), single-word (0), mentions=50
        #               s1 is supporting (0), so main wins regardless
        assert merged[0].canonical_node_id == "m1"


# ---------------------------------------------------------------------------
# John Donaldson test (the key use case)
# ---------------------------------------------------------------------------

class TestJohnDonaldson:
    """
    Test the father/son "John Donaldson" disambiguation.

    In american_sir:
    - John Donaldson Sr (father) - "father of the current knight"
    - John Donaldson Jr (son) - "the current Sir"

    Both share the same name. The ROLE_CONFLICT constraint should prevent merging.
    """

    def test_father_son_same_name_not_merged(self):
        graph = IdentityGraph()

        father = MockCharacter(
            id="father",
            canonical_name="John Donaldson",
            mention_count=15,
            descriptions=[MockDescription("father of the current knight, elder Donaldson")],
        )
        son = MockCharacter(
            id="son",
            canonical_name="John Donaldson",
            mention_count=45,
            descriptions=[MockDescription("the current Sir, son of the elder John")],
        )

        graph.add_character(father, is_main_cast=True)
        graph.add_character(son, is_main_cast=True)

        # The within-cast collector will find identical names and add merge evidence
        # But the constraint collector should detect the parent/child role conflict
        collect_within_cast_evidence(graph)
        collect_constraint_evidence(graph)

        # Verify constraint was generated
        constraints = graph.get_constraints_between("father", "son")
        assert len(constraints) > 0, "Should have generated role conflict constraint"
        assert any(
            c.constraint_type == ConstraintType.ROLE_CONFLICT for c in constraints
        ), "Should have ROLE_CONFLICT constraint"

        # Resolve and verify they stay separate
        groups = resolve_identities(graph)
        father_group = next(g for g in groups if "father" in g.member_ids)
        son_group = next(g for g in groups if "son" in g.member_ids)

        assert father_group != son_group or len(father_group.member_ids) == 1, \
            "Father and son should NOT be merged"

    def test_father_son_with_different_titles(self):
        """Even if both are "Sir John", different descriptions should prevent merge."""
        graph = IdentityGraph()

        father = MockCharacter(
            id="father",
            canonical_name="Sir John Donaldson",
            mention_count=15,
            descriptions=[MockDescription("the elder Sir John, father of the current knight")],
        )
        son = MockCharacter(
            id="son",
            canonical_name="Sir John Donaldson",
            mention_count=45,
            descriptions=[MockDescription("the younger Sir John, son of the late baronet")],
        )

        graph.add_character(father, is_main_cast=True)
        graph.add_character(son, is_main_cast=True)

        collect_within_cast_evidence(graph)
        collect_constraint_evidence(graph)

        groups = resolve_identities(graph)
        # They should remain separate
        assert len(groups) == 2, "Father and son with same title should stay separate"


# ---------------------------------------------------------------------------
# Evidence collector tests
# ---------------------------------------------------------------------------

class TestEvidenceCollectors:
    def test_title_variant_detection(self):
        graph = IdentityGraph()
        graph.add_character(
            MockCharacter(id="c1", canonical_name="Sergeant-Major Morris", mention_count=50),
            is_main_cast=True,
        )
        graph.add_character(
            MockCharacter(id="c2", canonical_name="Morris", mention_count=30),
            is_main_cast=True,
        )
        collect_title_variant_evidence(graph)
        edges = graph.get_merge_evidence_between("c1", "c2")
        assert len(edges) >= 1
        assert any(e.edge_type == EdgeType.NAME_CONTAINMENT for e in edges)

    def test_different_titled_people_constraint(self):
        """Mr. White and Mrs. White get DIFFERENT_TITLES constraint from constraint collector."""
        graph = IdentityGraph()
        graph.add_character(
            MockCharacter(id="c1", canonical_name="Mr. White", mention_count=80),
            is_main_cast=True,
        )
        graph.add_character(
            MockCharacter(id="c2", canonical_name="Mrs. White", mention_count=60),
            is_main_cast=True,
        )
        # The constraint comes from collect_constraint_evidence, not title_variant
        collect_constraint_evidence(graph)
        constraints = graph.get_constraints_between("c1", "c2")
        assert len(constraints) >= 1
        assert any(c.constraint_type == ConstraintType.DIFFERENT_TITLES for c in constraints)

    def test_spelling_variant_detection(self):
        graph = IdentityGraph()
        graph.add_character(
            MockCharacter(id="c1", canonical_name="Meyer Wolfsheim", mention_count=40),
            is_main_cast=True,
        )
        graph.add_character(
            MockCharacter(id="c2", canonical_name="Meyer Wolfshiem", mention_count=20),
            is_main_cast=True,
        )
        collect_within_cast_evidence(graph)
        edges = graph.get_merge_evidence_between("c1", "c2")
        assert len(edges) >= 1

    def test_middle_initial_detection(self):
        graph = IdentityGraph()
        graph.add_character(
            MockCharacter(id="c1", canonical_name="George B. Wilson", mention_count=5),
            is_main_cast=True,
        )
        graph.add_character(
            MockCharacter(id="c2", canonical_name="George Wilson", mention_count=91),
            is_main_cast=True,
        )
        collect_within_cast_evidence(graph)
        edges = graph.get_merge_evidence_between("c1", "c2")
        assert len(edges) >= 1
        assert any(e.edge_type == EdgeType.MIDDLE_INITIAL for e in edges)

    def test_cross_cast_lastname_match(self):
        graph = IdentityGraph()
        graph.add_character(
            MockCharacter(id="m1", canonical_name="Jay Gatsby", mention_count=200),
            is_main_cast=True,
        )
        graph.add_character(
            MockCharacter(id="s1", canonical_name="Gatsby", mention_count=50),
            is_main_cast=False,
        )
        collect_cross_cast_evidence(graph)
        edges = graph.get_merge_evidence_between("m1", "s1")
        assert len(edges) >= 1

    def test_descriptive_synonym_cross_cast(self):
        graph = IdentityGraph()
        graph.add_character(
            MockCharacter(id="m1", canonical_name="the creature", mention_count=100),
            is_main_cast=True,
        )
        graph.add_character(
            MockCharacter(id="s1", canonical_name="the monster", mention_count=30),
            is_main_cast=False,
        )
        collect_synonym_evidence(graph)
        edges = graph.get_merge_evidence_between("m1", "s1")
        assert len(edges) >= 1
        assert any(e.edge_type == EdgeType.DESCRIPTIVE_SYNONYM for e in edges)

    def test_narrator_placeholder_detection(self):
        graph = IdentityGraph()
        graph.add_character(
            MockCharacter(id="narrator", canonical_name="the protagonist", mention_count=0, is_narrator=True),
            is_main_cast=True,
        )
        graph.add_character(
            MockCharacter(id="nick", canonical_name="Nick Carraway", mention_count=150),
            is_main_cast=True,
        )
        narrator_info = MockNarratorInfo(
            pov="first-person",
            narrator_name="Nick Carraway",
            narrator_character_id="narrator",
        )
        collect_narrator_evidence(graph, narrator_info)
        edges = graph.get_merge_evidence_between("narrator", "nick")
        assert len(edges) >= 1
        assert any(e.edge_type == EdgeType.NARRATOR_PLACEHOLDER for e in edges)

    def test_cooccurrence_evidence_corroborates(self):
        """Co-occurrence only adds evidence when there's already a name-based edge."""
        graph = IdentityGraph()
        graph.add_character(
            MockCharacter(id="c1", canonical_name="Jay Gatsby", mention_count=200),
            is_main_cast=True,
        )
        graph.add_character(
            MockCharacter(id="c2", canonical_name="Gatsby", mention_count=50),
            is_main_cast=True,
        )
        # Add a name-based edge first
        graph.add_merge_edge("c1", "c2", EdgeType.LASTNAME_MATCH, "lastname match")

        cooccurrence = {("c1", "c2"): 0.75, ("c2", "c1"): 0.75}
        collect_cooccurrence_evidence(graph, cooccurrence)
        edges = graph.get_merge_evidence_between("c1", "c2")
        cooccurrence_edges = [e for e in edges if e.edge_type == EdgeType.COOCCURRENCE]
        assert len(cooccurrence_edges) >= 1, "Co-occurrence should corroborate existing evidence"

    def test_cooccurrence_no_standalone_evidence(self):
        """Co-occurrence should NOT add evidence when there's no prior name-based edge."""
        graph = IdentityGraph()
        graph.add_character(
            MockCharacter(id="c1", canonical_name="Prince Prospero", mention_count=50),
            is_main_cast=True,
        )
        graph.add_character(
            MockCharacter(id="c2", canonical_name="the Red Death", mention_count=30),
            is_main_cast=True,
        )
        cooccurrence = {("c1", "c2"): 0.80, ("c2", "c1"): 0.80}
        collect_cooccurrence_evidence(graph, cooccurrence)
        edges = graph.get_merge_evidence_between("c1", "c2")
        assert len(edges) == 0, "Co-occurrence should NOT create standalone merge evidence"

    def test_nickname_detection(self):
        assert _is_nickname_match("Jim", "James") is True
        assert _is_nickname_match("Bob", "Robert") is True
        assert _is_nickname_match("Milt", "Milton") is True
        assert _is_nickname_match("John", "James") is False

    def test_different_first_names_constraint(self):
        graph = IdentityGraph()
        graph.add_character(
            MockCharacter(id="c1", canonical_name="George Wilson", mention_count=80),
            is_main_cast=True,
        )
        graph.add_character(
            MockCharacter(id="c2", canonical_name="Myrtle Wilson", mention_count=60),
            is_main_cast=True,
        )
        collect_constraint_evidence(graph)
        constraints = graph.get_constraints_between("c1", "c2")
        assert len(constraints) >= 1
        assert any(c.constraint_type == ConstraintType.DIFFERENT_FIRST_NAMES for c in constraints)


# ---------------------------------------------------------------------------
# Execute merges tests
# ---------------------------------------------------------------------------

class TestExecuteMerges:
    def test_basic_merge_execution(self):
        from src.pipeline.character_extraction_v2.identity_graph import MergeGroup

        main = [
            MockCharacter(id="c1", canonical_name="Jay Gatsby", mention_count=200),
            MockCharacter(id="c2", canonical_name="Gatsby", mention_count=50),
        ]
        supporting = []

        groups = [
            MergeGroup(
                canonical_node_id="c1",
                canonical_name="Jay Gatsby",
                member_ids=["c1", "c2"],
                aliases=["Gatsby"],
                evidence=[],
                constraints_overridden=[],
            )
        ]

        new_main, new_supp = execute_merges(groups, main, supporting)
        assert len(new_main) == 1
        assert new_main[0].canonical_name == "Jay Gatsby"
        assert "Gatsby" in new_main[0].aliases
        assert new_main[0].mention_count == 250

    def test_cross_cast_merge(self):
        from src.pipeline.character_extraction_v2.identity_graph import MergeGroup

        main = [MockCharacter(id="m1", canonical_name="Jay Gatsby", mention_count=200)]
        supporting = [MockCharacter(id="s1", canonical_name="Mr. Gatsby", mention_count=10)]

        groups = [
            MergeGroup(
                canonical_node_id="m1",
                canonical_name="Jay Gatsby",
                member_ids=["m1", "s1"],
                aliases=["Mr. Gatsby"],
                evidence=[],
                constraints_overridden=[],
            )
        ]

        new_main, new_supp = execute_merges(groups, main, supporting)
        assert len(new_main) == 1
        assert len(new_supp) == 0
        assert "Mr. Gatsby" in new_main[0].aliases

    def test_no_merge_for_single_member_groups(self):
        from src.pipeline.character_extraction_v2.identity_graph import MergeGroup

        main = [
            MockCharacter(id="c1", canonical_name="A", mention_count=10),
            MockCharacter(id="c2", canonical_name="B", mention_count=20),
        ]
        groups = [
            MergeGroup(canonical_node_id="c1", canonical_name="A", member_ids=["c1"], aliases=[], evidence=[], constraints_overridden=[]),
            MergeGroup(canonical_node_id="c2", canonical_name="B", member_ids=["c2"], aliases=[], evidence=[], constraints_overridden=[]),
        ]

        new_main, _ = execute_merges(groups, main, [])
        assert len(new_main) == 2


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_are_different_titled_people(self):
        assert _are_different_titled_people("Mr. White", "Mrs. White") is True
        assert _are_different_titled_people("Mr. White", "White") is False
        assert _are_different_titled_people("Mr. Sloane", "Mr. McKee") is True
        assert _are_different_titled_people("Morris", "Sergeant-Major Morris") is False

    def test_name_contains_other(self):
        assert _name_contains_other("sergeant-major morris", "morris") is True
        assert _name_contains_other("mr. white", "white") is True
        assert _name_contains_other("whitehouse", "white") is False

    def test_strip_title(self):
        assert _strip_title("Mr. Gatsby") == "Gatsby"
        assert _strip_title("Mrs. Wilson") == "Wilson"
        assert _strip_title("Dr. Jekyll") == "Jekyll"
        assert _strip_title("Jay Gatsby") == "Jay Gatsby"

    def test_normalize_descriptor(self):
        is_the, desc = _normalize_descriptor("the creature")
        assert is_the is True
        assert desc == "creature"

        is_the, desc = _normalize_descriptor("the creature (implied)")
        assert is_the is True
        assert desc == "creature"

        is_the, desc = _normalize_descriptor("monster")
        assert is_the is False
        assert desc == "monster"


# ---------------------------------------------------------------------------
# Compare results tests
# ---------------------------------------------------------------------------

class TestCompareResults:
    def test_identical_results(self):
        main = [MockCharacter(id="c1", canonical_name="Gatsby", aliases=["Jay Gatsby"])]
        result = compare_results(main, [], main, [])
        assert result["matches"] == 1
        assert len(result["alias_differences"]) == 0

    def test_different_aliases(self):
        graph_main = [MockCharacter(id="c1", canonical_name="Gatsby", aliases=["Jay Gatsby"])]
        seq_main = [MockCharacter(id="c1", canonical_name="Gatsby", aliases=["Jay Gatsby", "Old Sport"])]
        result = compare_results(graph_main, [], seq_main, [])
        assert len(result["alias_differences"]) == 1

    def test_different_characters(self):
        graph_main = [MockCharacter(id="c1", canonical_name="Gatsby")]
        seq_main = [MockCharacter(id="c2", canonical_name="Nick")]
        result = compare_results(graph_main, [], seq_main, [])
        assert len(result["graph_only_characters"]) == 1
        assert len(result["sequential_only_characters"]) == 1


# ---------------------------------------------------------------------------
# Integration test: full pipeline
# ---------------------------------------------------------------------------

class TestFullPipeline:
    def test_monkey_paw_scenario(self):
        """Simulate The Monkey's Paw character set."""
        graph = IdentityGraph()

        main = [
            MockCharacter(id="m1", canonical_name="Mr. White", mention_count=80),
            MockCharacter(id="m2", canonical_name="Mrs. White", mention_count=40),
            MockCharacter(id="m3", canonical_name="Herbert White", mention_count=30),
            MockCharacter(id="m4", canonical_name="Sergeant-Major Morris", mention_count=20),
        ]
        supporting = [
            MockCharacter(id="s1", canonical_name="Morris", mention_count=15),
            MockCharacter(id="s2", canonical_name="White", mention_count=25),
            MockCharacter(id="s3", canonical_name="Herbert", mention_count=10),
        ]

        graph.add_characters(main, supporting)
        collect_all_evidence(graph)
        groups = resolve_identities(graph)

        # Morris should merge with Sergeant-Major Morris
        morris_group = next(
            (g for g in groups if any(
                graph.nodes.get(mid, None) and graph.nodes[mid].canonical_name == "Sergeant-Major Morris"
                for mid in g.member_ids
            )),
            None,
        )
        assert morris_group is not None
        assert "s1" in morris_group.member_ids, "Morris should merge with Sergeant-Major Morris"

        # Herbert should merge with Herbert White
        herbert_group = next(
            (g for g in groups if any(
                graph.nodes.get(mid, None) and graph.nodes[mid].canonical_name == "Herbert White"
                for mid in g.member_ids
            )),
            None,
        )
        assert herbert_group is not None
        assert "s3" in herbert_group.member_ids, "Herbert should merge with Herbert White"

        # Mr. White and Mrs. White should NOT merge
        mr_group = next(g for g in groups if "m1" in g.member_ids)
        mrs_group = next(g for g in groups if "m2" in g.member_ids)
        assert mr_group != mrs_group or len(mr_group.member_ids) == 1, \
            "Mr. White and Mrs. White should stay separate"

    def test_frankenstein_descriptive_synonyms(self):
        """Simulate Frankenstein creature/monster scenario."""
        graph = IdentityGraph()

        main = [
            MockCharacter(id="m1", canonical_name="Victor Frankenstein", mention_count=200),
            MockCharacter(id="m2", canonical_name="the creature", mention_count=80),
        ]
        supporting = [
            MockCharacter(id="s1", canonical_name="the monster", mention_count=30),
            MockCharacter(id="s2", canonical_name="the fiend", mention_count=10),
            MockCharacter(id="s3", canonical_name="the wretch", mention_count=5),
        ]

        graph.add_characters(main, supporting)
        collect_all_evidence(graph)
        groups = resolve_identities(graph)

        # All creature synonyms should merge together
        creature_group = next(g for g in groups if "m2" in g.member_ids)
        assert "s1" in creature_group.member_ids, "the monster should merge with the creature"
        assert "s2" in creature_group.member_ids, "the fiend should merge with the creature"
        assert "s3" in creature_group.member_ids, "the wretch should merge with the creature"

        # Victor should NOT merge with any creature synonyms
        victor_group = next(g for g in groups if "m1" in g.member_ids)
        assert len(victor_group.member_ids) == 1, "Victor should be alone"
