"""Tests for the golden-corpus scorer."""

from src.pipeline.golden_score import normalize_name, score_against_truth

TRUTH = {
    "book": "T",
    "narrator": "Mira Voss",
    "characters": [
        {"canonical_name": "Mira Voss", "aliases": ["Mira"], "role": "protagonist"},
        {"canonical_name": "Sgt. Calder", "aliases": ["Calder"], "role": "main"},
        {"canonical_name": "Old Pete", "aliases": [], "role": "supporting", "required": False},
    ],
    "forbidden": ["Elvis Presley"],
}


def _analysis(chars, narrator_id=None):
    return {"characters": chars, "narrator_character_id": narrator_id}


def _char(cid, name, aliases=(), role="main", mentions=10):
    return {
        "id": cid,
        "canonical_name": name,
        "aliases": list(aliases),
        "role": role,
        "mention_count": mentions,
    }


class TestNormalize:
    def test_strips_titles_possessives_initials(self):
        assert normalize_name("Sgt. Calder's") == "calder"
        assert normalize_name("George B. Wilson") == "george wilson"
        assert normalize_name("the old man") == "man"


class TestScoring:
    def test_perfect_match(self):
        s = score_against_truth(
            _analysis(
                [
                    _char("1", "Mira Voss", ["Mira"], "protagonist"),
                    _char("2", "Calder", ["Sgt. Calder"], "main"),
                ],
                narrator_id="1",
            ),
            TRUTH,
        )
        assert s["character_recall"] == 1.0
        assert s["main_cast_precision"] == 1.0
        assert s["narrator_correct"] is True
        assert s["forbidden_hits"] == []

    def test_missing_required_lowers_recall(self):
        s = score_against_truth(
            _analysis([_char("1", "Mira Voss", [], "protagonist")]), TRUTH
        )
        assert s["character_recall"] == 0.5
        assert "Sgt. Calder" in s["missing_required"]

    def test_spurious_main_cast_lowers_precision(self):
        s = score_against_truth(
            _analysis(
                [
                    _char("1", "Mira Voss", [], "protagonist"),
                    _char("2", "Calder", [], "main"),
                    _char("3", "The Ridge", [], "protagonist"),  # location leak
                ]
            ),
            TRUTH,
        )
        assert s["main_cast_precision"] < 1.0
        assert "The Ridge" in s["spurious_main_cast"]

    def test_forbidden_hit_detected(self):
        s = score_against_truth(
            _analysis([_char("1", "Elvis Presley", [], "minor")]), TRUTH
        )
        assert s["forbidden_hits"] == ["Elvis Presley"]

    def test_alias_fragments_of_canonical_accepted(self):
        s = score_against_truth(
            _analysis([_char("1", "Mira Voss", ["Voss"], "protagonist")]), TRUTH
        )
        assert s["alias_precision"] == 1.0

    def test_invented_alias_is_false_positive(self):
        s = score_against_truth(
            _analysis([_char("1", "Mira Voss", ["Tabitha Voss"], "protagonist")]),
            TRUTH,
        )
        assert s["alias_precision"] == 0.0
        assert s["alias_false_positives"]

    def test_third_person_narrator(self):
        truth = dict(TRUTH, narrator=None)
        s = score_against_truth(_analysis([_char("1", "Mira Voss")]), truth)
        assert s["narrator_correct"] is True  # no narrator predicted, none expected

    def test_role_free_outputs_use_mention_fallback(self):
        s = score_against_truth(
            _analysis(
                [
                    _char("1", "Mira Voss", [], "", mentions=50),
                    _char("2", "Calder", [], "", mentions=40),
                ]
            ),
            TRUTH,
        )
        assert s["main_cast_precision"] == 1.0
