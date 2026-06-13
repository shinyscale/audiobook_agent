"""Tests for the output linter (universal invariant gate)."""

from src.models import (
    AnalysisResult,
    BookMetadata,
    Character,
    ConfidenceLevel,
    PronunciationEntry,
    PronunciationFlag,
)
from src.pipeline.output_linter import apply_lint, lint_analysis_result

TEXT = (
    "Sergeant Marsh briefed the platoon while Calder watched. "
    "Marsh and Calder walked to the ridge. Toby Quill laughed. "
    "The word Xanthe appeared once here."
)


def _char(name, **kw):
    defaults = dict(
        id=name.lower().replace(" ", "_"),
        canonical_name=name,
        aliases=[],
        confidence=ConfidenceLevel.MEDIUM,
        mention_count=3,
    )
    defaults.update(kw)
    return Character(**defaults)


def _result(characters, pronunciations=()):
    return AnalysisResult(
        metadata=BookMetadata(source_file="t.txt", source_format="txt"),
        structure=[],
        characters=list(characters),
        pronunciations=list(pronunciations),
        warnings=[],
    )


class TestCharacterInvariants:
    def test_clean_result_passes(self):
        result = _result([
            _char("Marsh", aliases=["Sergeant Marsh"]),
            _char("Calder", relationships={"Marsh": "colleague"}),
        ])
        assert lint_analysis_result(result, TEXT) == []

    def test_ungrounded_alias_flagged(self):
        result = _result([_char("Marsh", aliases=["Dudley Marsh"])])
        violations = lint_analysis_result(result, TEXT)
        assert any(v.startswith("C4") and "Dudley" in v for v in violations)

    def test_ungrounded_canonical_flagged(self):
        result = _result([_char("Zebulon Pike")])
        violations = lint_analysis_result(result, TEXT)
        assert any(v.startswith("C3") for v in violations)

    def test_group_and_bare_title_canonicals_flagged(self):
        result = _result([_char("Ridge personnel"), _char("Sgt")])
        violations = lint_analysis_result(result, TEXT)
        assert any(v.startswith("C2 group") for v in violations)
        assert any(v.startswith("C2 bare-title") for v in violations)

    def test_orphan_and_self_relationships_flagged(self):
        result = _result([
            _char("Marsh", relationships={"Marsh": "self", "Nobody Special": "friend"}),
        ])
        violations = lint_analysis_result(result, TEXT)
        assert any(v.startswith("C5 self") for v in violations)
        assert any(v.startswith("C5 orphan") for v in violations)

    def test_duplicate_canonical_flagged(self):
        result = _result([_char("Marsh"), _char("Marsh")])
        violations = lint_analysis_result(result, TEXT)
        assert any(v.startswith("C1") for v in violations)

    def test_zero_mention_flagged_but_symbolic_exempt(self):
        result = _result([
            _char("Calder", mention_count=0),
            _char("the storm", mention_count=0, is_symbolic=True),
        ])
        violations = lint_analysis_result(result, TEXT)
        assert any(v.startswith("C6") and "Calder" in v for v in violations)
        assert not any("storm" in v for v in violations)


class TestPronunciationInvariants:
    def test_ungrounded_word_and_bad_ipa(self):
        prons = [
            PronunciationEntry(
                word="Quetzal",  # not in TEXT
                flag_reason=PronunciationFlag.PROPER_NOUN,
                first_position=0,
            ),
            PronunciationEntry(
                word="Xanthe",
                flag_reason=PronunciationFlag.PROPER_NOUN,
                first_position=0,
                ipa="/ザンシ/",  # CJK garbage
            ),
        ]
        result = _result([], prons)
        violations = lint_analysis_result(result, TEXT)
        assert any(v.startswith("P1") and "Quetzal" in v for v in violations)
        assert any(v.startswith("P2") and "Xanthe" in v for v in violations)


class TestApplyLint:
    def test_appends_warnings_and_never_raises(self):
        result = _result([_char("Marsh", aliases=["Dudley Marsh"])])
        violations = apply_lint(result, TEXT)
        assert violations
        assert any("Output lint" in w for w in result.warnings)

    def test_clean_run_adds_no_warnings(self):
        result = _result([_char("Calder")])
        assert apply_lint(result, TEXT) == []
        assert result.warnings == []
