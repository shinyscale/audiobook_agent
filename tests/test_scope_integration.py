"""
Tests for Scope scalpel integration in NarratorDetector.

Verifies lazy gating, graceful degradation, length mismatch handling,
is_nested promotion, and backward compatibility with existing code paths.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.pipeline.character_extraction_v2.narrator import NarratorDetector, NarratorInfo


def _mock_llm_response(
    pov: str = "first-person",
    narrator_name: str = "Narrator",
    is_nested: bool = False,
):
    """Build a mock LLM response tuple (result, response)."""
    result = {
        "pov": pov,
        "narrator_name": narrator_name,
        "is_nested": is_nested,
        "nested_narrators": [],
    }
    response = MagicMock()
    response.success = True
    response.error = None
    return (result, response)


def _mock_main_cast():
    """Build a minimal main cast for tests."""
    char = MagicMock()
    char.canonical_name = "Narrator"
    char.aliases = []
    char.id = "char_1"
    char.description = "Test character"
    char.role = "protagonist"
    return [char]


class TestNarratorInfoFields:
    """Verify the new scope fields exist and have sensible defaults."""

    def test_default_empty_lists(self):
        ni = NarratorInfo(pov="first-person")
        assert ni.chapter_narrator_types == []
        assert ni.chapter_narrator_confidences == []

    def test_custom_lists_respected(self):
        ni = NarratorInfo(
            pov="epistolary",
            chapter_narrator_types=["frame_narrator", "inner_narrator"],
            chapter_narrator_confidences=[0.8, 0.7],
        )
        assert len(ni.chapter_narrator_types) == 2
        assert ni.chapter_narrator_types[0] == "frame_narrator"
        assert ni.chapter_narrator_confidences[1] == 0.7


class TestScopeGating:
    """Scope should only run when nested narrative is suspected."""

    def test_scope_not_run_without_opening_texts(self):
        """When chapter_opening_texts=None, scope never runs."""
        llm = MagicMock()
        llm.query_json.return_value = _mock_llm_response()
        detector = NarratorDetector(llm)

        with patch(
            "src.pipeline.character_extraction_v2.narrator.scalpel_available"
        ) as mock_avail:
            mock_avail.return_value = True
            result = detector.detect(
                chapter_summaries=["chapter 1", "chapter 2"],
                main_cast=_mock_main_cast(),
                chapter_opening_texts=None,
            )

        assert result.chapter_narrator_types == []
        assert result.chapter_narrator_confidences == []

    def test_scope_not_run_when_scalpel_unavailable(self):
        """When scope model not available, lists stay empty."""
        llm = MagicMock()
        llm.query_json.return_value = _mock_llm_response(is_nested=True)
        detector = NarratorDetector(llm)

        def _fake_avail(name):
            return name == "beacon"  # beacon ok, scope not

        with patch(
            "src.pipeline.character_extraction_v2.narrator.scalpel_available",
            side_effect=_fake_avail,
        ):
            result = detector.detect(
                chapter_summaries=["c1", "c2"],
                main_cast=_mock_main_cast(),
                chapter_opening_texts=["text1", "text2"],
            )

        assert result.chapter_narrator_types == []

    def test_scope_runs_for_is_nested_llm_signal(self):
        """When LLM reports is_nested=True, scope runs."""
        llm = MagicMock()
        llm.query_json.return_value = _mock_llm_response(
            pov="first-person", is_nested=True
        )
        detector = NarratorDetector(llm)

        mock_loader = MagicMock()
        mock_loader.predict_batch.return_value = [
            ("frame_narrator", 0.85),
            ("inner_narrator", 0.72),
        ]

        def _fake_avail(name):
            return True

        with patch(
            "src.pipeline.character_extraction_v2.narrator.scalpel_available",
            side_effect=_fake_avail,
        ), patch(
            "src.pipeline.character_extraction_v2.narrator.ScalpelLoader",
            return_value=mock_loader,
        ):
            # Beacon predict needs to return something sensible
            mock_loader.predict.return_value = ("first_person", 0.7)
            result = detector.detect(
                chapter_summaries=["c1", "c2"],
                main_cast=_mock_main_cast(),
                chapter_opening_texts=["text1", "text2"],
            )

        assert result.chapter_narrator_types == ["frame_narrator", "inner_narrator"]
        assert result.chapter_narrator_confidences == [0.85, 0.72]

    def test_scope_runs_for_long_first_person(self):
        """Long first-person book (>= 20 chapters) triggers lazy gate."""
        llm = MagicMock()
        llm.query_json.return_value = _mock_llm_response(
            pov="first-person", is_nested=False
        )
        detector = NarratorDetector(llm)

        n = 22
        mock_loader = MagicMock()
        mock_loader.predict_batch.return_value = [("single_narrator", 0.9)] * n
        mock_loader.predict.return_value = ("first_person", 0.7)

        with patch(
            "src.pipeline.character_extraction_v2.narrator.scalpel_available",
            return_value=True,
        ), patch(
            "src.pipeline.character_extraction_v2.narrator.ScalpelLoader",
            return_value=mock_loader,
        ):
            result = detector.detect(
                chapter_summaries=[f"ch {i}" for i in range(n)],
                main_cast=_mock_main_cast(),
                chapter_opening_texts=[f"text {i}" for i in range(n)],
            )

        assert len(result.chapter_narrator_types) == n
        assert all(t == "single_narrator" for t in result.chapter_narrator_types)

    def test_scope_skipped_for_short_first_person(self):
        """Short first-person book (< 20 chapters) without is_nested skips scope."""
        llm = MagicMock()
        llm.query_json.return_value = _mock_llm_response(
            pov="first-person", is_nested=False
        )
        detector = NarratorDetector(llm)

        mock_loader = MagicMock()
        mock_loader.predict.return_value = ("first_person", 0.7)
        mock_loader.predict_batch.return_value = [("single_narrator", 0.9)] * 5

        with patch(
            "src.pipeline.character_extraction_v2.narrator.scalpel_available",
            return_value=True,
        ), patch(
            "src.pipeline.character_extraction_v2.narrator.ScalpelLoader",
            return_value=mock_loader,
        ):
            result = detector.detect(
                chapter_summaries=["c1", "c2", "c3", "c4", "c5"],
                main_cast=_mock_main_cast(),
                chapter_opening_texts=["t1", "t2", "t3", "t4", "t5"],
            )

        # Lazy gate: short first-person + not nested = scope skipped
        assert result.chapter_narrator_types == []
        assert mock_loader.predict_batch.call_count == 0


class TestScopeGracefulDegradation:
    """Scope failures should never break narrator detection."""

    def test_scope_exception_handled(self):
        """Exception during scope prediction leaves lists empty, detect still returns."""
        llm = MagicMock()
        llm.query_json.return_value = _mock_llm_response(
            pov="epistolary", is_nested=True
        )
        detector = NarratorDetector(llm)

        mock_loader = MagicMock()
        mock_loader.predict_batch.side_effect = RuntimeError("Model load failed")
        mock_loader.predict.return_value = ("epistolary", 0.9)

        with patch(
            "src.pipeline.character_extraction_v2.narrator.scalpel_available",
            return_value=True,
        ), patch(
            "src.pipeline.character_extraction_v2.narrator.ScalpelLoader",
            return_value=mock_loader,
        ):
            result = detector.detect(
                chapter_summaries=["c1", "c2"],
                main_cast=_mock_main_cast(),
                chapter_opening_texts=["t1", "t2"],
            )

        assert result.chapter_narrator_types == []
        assert result.chapter_narrator_confidences == []
        # detect() still returns a valid NarratorInfo
        assert result.pov == "epistolary"

    def test_scope_length_mismatch_skipped(self):
        """Mismatched list lengths trigger warning and skip scope."""
        llm = MagicMock()
        llm.query_json.return_value = _mock_llm_response(
            pov="epistolary", is_nested=True
        )
        detector = NarratorDetector(llm)

        mock_loader = MagicMock()
        mock_loader.predict.return_value = ("epistolary", 0.9)

        with patch(
            "src.pipeline.character_extraction_v2.narrator.scalpel_available",
            return_value=True,
        ), patch(
            "src.pipeline.character_extraction_v2.narrator.ScalpelLoader",
            return_value=mock_loader,
        ):
            result = detector.detect(
                chapter_summaries=["c1", "c2", "c3"],
                main_cast=_mock_main_cast(),
                chapter_opening_texts=["t1", "t2"],  # length mismatch
            )

        assert result.chapter_narrator_types == []
        assert mock_loader.predict_batch.call_count == 0


class TestScopePromotesIsNested:
    """Scope should promote is_nested=True when non-single chapters detected."""

    def test_promotes_is_nested_on_frame_detection(self):
        """If LLM says is_nested=False but scope finds frame_narrator, is_nested promoted."""
        llm = MagicMock()
        llm.query_json.return_value = _mock_llm_response(
            pov="first-person", is_nested=False
        )
        detector = NarratorDetector(llm)

        n = 22  # long enough to trigger lazy gate
        mock_loader = MagicMock()
        # Mix: 2 frame, 20 single
        predictions = [("frame_narrator", 0.75), ("frame_narrator", 0.70)]
        predictions += [("single_narrator", 0.9)] * 20
        mock_loader.predict_batch.return_value = predictions
        mock_loader.predict.return_value = ("first_person", 0.7)

        with patch(
            "src.pipeline.character_extraction_v2.narrator.scalpel_available",
            return_value=True,
        ), patch(
            "src.pipeline.character_extraction_v2.narrator.ScalpelLoader",
            return_value=mock_loader,
        ):
            result = detector.detect(
                chapter_summaries=[f"ch {i}" for i in range(n)],
                main_cast=_mock_main_cast(),
                chapter_opening_texts=[f"text {i}" for i in range(n)],
            )

        assert result.is_nested is True  # Promoted from False
        assert "frame_narrator" in result.chapter_narrator_types

    def test_is_nested_unchanged_when_all_single(self):
        """All single_narrator chapters leave is_nested at LLM's value."""
        llm = MagicMock()
        llm.query_json.return_value = _mock_llm_response(
            pov="first-person", is_nested=False
        )
        detector = NarratorDetector(llm)

        n = 22
        mock_loader = MagicMock()
        mock_loader.predict_batch.return_value = [("single_narrator", 0.9)] * n
        mock_loader.predict.return_value = ("first_person", 0.7)

        with patch(
            "src.pipeline.character_extraction_v2.narrator.scalpel_available",
            return_value=True,
        ), patch(
            "src.pipeline.character_extraction_v2.narrator.ScalpelLoader",
            return_value=mock_loader,
        ):
            result = detector.detect(
                chapter_summaries=[f"ch {i}" for i in range(n)],
                main_cast=_mock_main_cast(),
                chapter_opening_texts=[f"text {i}" for i in range(n)],
            )

        assert result.is_nested is False  # Not promoted


class TestBackwardCompatibility:
    """Existing callers should still work without passing chapter_opening_texts."""

    def test_detect_without_new_param(self):
        """Calling detect() without chapter_opening_texts works as before."""
        llm = MagicMock()
        llm.query_json.return_value = _mock_llm_response()
        detector = NarratorDetector(llm)

        with patch(
            "src.pipeline.character_extraction_v2.narrator.scalpel_available",
            return_value=False,
        ):
            result = detector.detect(
                chapter_summaries=["c1", "c2"],
                main_cast=_mock_main_cast(),
            )

        # Works without exception, scope fields default empty
        assert result.chapter_narrator_types == []
        assert result.pov == "first-person"
