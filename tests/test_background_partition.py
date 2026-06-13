"""Regression tests for the cast / background_references partition.

Guards against the 2026-06-12 regression where a has_dialogue-only gate
relegated heavily-mentioned real cast (e.g. a soldier with 111 mentions and
profiler evidence) into background_references, collapsing recall.
"""

from src.analyzer import is_background_reference


class _Ch:
    def __init__(self, **kw):
        self.id = kw.get("id", "supporting_1")
        self.role = kw.get("role", "supporting")
        self.mention_count = kw.get("mention_count", 0)
        self.has_dialogue = kw.get("has_dialogue", False)
        self.is_narrator = kw.get("is_narrator", False)
        self.evidence = kw.get("evidence", [])
        self.descriptions = kw.get("descriptions", [])


class TestKeptInCast:
    def test_high_mention_supporting_kept(self):
        # The exact regression: 111-mention soldier, no dialogue flag.
        assert not is_background_reference(_Ch(role="supporting", mention_count=111))

    def test_profiler_substance_kept_even_if_low_mentions(self):
        assert not is_background_reference(
            _Ch(role="supporting", mention_count=3, evidence=[{"quote": "x"}])
        )

    def test_main_and_lead_roles_kept(self):
        for role in ("protagonist", "antagonist", "main"):
            assert not is_background_reference(_Ch(role=role, mention_count=1))

    def test_narrator_kept(self):
        assert not is_background_reference(_Ch(is_narrator=True, mention_count=1))

    def test_dialogue_flag_kept(self):
        assert not is_background_reference(_Ch(has_dialogue=True, mention_count=1))

    def test_main_cast_id_kept(self):
        assert not is_background_reference(_Ch(id="main_cast_4", mention_count=1))


class TestRelegatedToBackground:
    def test_pure_namedrop_relegated(self):
        # One-off historical name-drop: no presence signal whatsoever.
        assert is_background_reference(
            _Ch(role="minor", mention_count=1, evidence=[], descriptions=[])
        )

    def test_low_mention_supporting_namedrop_relegated(self):
        assert is_background_reference(_Ch(role="supporting", mention_count=2))
