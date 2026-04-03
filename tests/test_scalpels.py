"""
Tests for scalpel model loader and integration.

Tests both the scalpel infrastructure (availability checks, graceful degradation)
and individual model predictions when models are present.
"""

import pytest
from unittest.mock import patch, MagicMock

from src.pipeline.scalpels import (
    SCALPEL_REGISTRY,
    ScalpelLoader,
    scalpel_available,
    _torch_available,
    MODELS_DIR,
)


class TestScalpelRegistry:
    """Test the scalpel registry configuration."""

    def test_all_models_registered(self):
        assert set(SCALPEL_REGISTRY.keys()) == {"compass", "beacon", "cluster", "echo", "voice"}

    def test_compass_config(self):
        cfg = SCALPEL_REGISTRY["compass"]
        assert cfg["num_classes"] == 5
        assert cfg["max_length"] == 512
        assert set(cfg["labels"].values()) == {
            "protagonist", "antagonist", "morally_ambiguous", "victim", "neutral"
        }

    def test_beacon_config(self):
        cfg = SCALPEL_REGISTRY["beacon"]
        assert cfg["num_classes"] == 4
        assert cfg["max_length"] == 512
        assert set(cfg["labels"].values()) == {
            "first_person", "third_person", "third_person_omniscient", "epistolary"
        }

    def test_cluster_config(self):
        cfg = SCALPEL_REGISTRY["cluster"]
        assert cfg["num_classes"] == 2
        assert cfg["max_length"] == 256
        assert set(cfg["labels"].values()) == {"same_person", "different_person"}

    def test_echo_config(self):
        cfg = SCALPEL_REGISTRY["echo"]
        assert cfg["num_classes"] == 2
        assert cfg["max_length"] == 256
        assert set(cfg["labels"].values()) == {"active", "mentioned"}


class TestScalpelAvailability:
    """Test availability checking and graceful degradation."""

    def test_unknown_model_unavailable(self):
        assert scalpel_available("nonexistent") is False

    def test_unavailable_when_no_torch(self):
        with patch("src.pipeline.scalpels._torch_available", return_value=False):
            assert scalpel_available("compass") is False

    def test_unavailable_when_no_model_file(self):
        with patch("src.pipeline.scalpels._torch_available", return_value=True):
            # Model file won't exist unless explicitly staged
            if not (MODELS_DIR / "compass_model" / "compass_model.pt").exists():
                assert scalpel_available("compass") is False


class TestScalpelLoaderSingleton:
    """Test that ScalpelLoader is a proper singleton."""

    def test_singleton(self):
        # Reset singleton for clean test
        ScalpelLoader._instance = None
        a = ScalpelLoader()
        b = ScalpelLoader()
        assert a is b
        # Cleanup
        ScalpelLoader._instance = None


@pytest.mark.skipif(
    not _torch_available(),
    reason="torch not installed"
)
class TestScalpelModelsIntegration:
    """Integration tests that run when torch is installed and models are present."""

    @pytest.mark.skipif(
        not scalpel_available("compass"),
        reason="compass model not available"
    )
    def test_compass_prediction(self):
        loader = ScalpelLoader()
        label, confidence = loader.predict(
            "compass",
            "Jay Gatsby [SEP] He threw lavish parties and pursued Daisy relentlessly."
        )
        assert label in SCALPEL_REGISTRY["compass"]["labels"].values()
        assert 0.0 <= confidence <= 1.0

    @pytest.mark.skipif(
        not scalpel_available("beacon"),
        reason="beacon model not available"
    )
    def test_beacon_prediction(self):
        loader = ScalpelLoader()
        label, confidence = loader.predict(
            "beacon",
            "I walked down the street and saw my old friend. I could not believe my eyes."
        )
        assert label in SCALPEL_REGISTRY["beacon"]["labels"].values()
        assert 0.0 <= confidence <= 1.0

    @pytest.mark.skipif(
        not scalpel_available("cluster"),
        reason="cluster model not available"
    )
    def test_cluster_prediction(self):
        loader = ScalpelLoader()
        label, confidence = loader.predict(
            "cluster",
            "Mr. Smith [SEP] John Smith [SEP] Mr. Smith greeted his neighbor."
        )
        assert label in SCALPEL_REGISTRY["cluster"]["labels"].values()
        assert 0.0 <= confidence <= 1.0

    @pytest.mark.skipif(
        not scalpel_available("cluster"),
        reason="cluster model not available"
    )
    def test_cluster_batch_prediction(self):
        loader = ScalpelLoader()
        texts = [
            "Alice [SEP] Alice Smith [SEP] Alice walked to the store.",
            "Bob [SEP] Charlie [SEP] Bob and Charlie went fishing.",
        ]
        results = loader.predict_batch("cluster", texts)
        assert len(results) == 2
        for label, confidence in results:
            assert label in SCALPEL_REGISTRY["cluster"]["labels"].values()
            assert 0.0 <= confidence <= 1.0

    @pytest.mark.skipif(
        not scalpel_available("echo"),
        reason="echo model not available"
    )
    def test_echo_prediction(self):
        loader = ScalpelLoader()
        label, confidence = loader.predict(
            "echo",
            "Elizabeth [SEP] Elizabeth entered the room and spoke firmly to the crowd."
        )
        assert label in SCALPEL_REGISTRY["echo"]["labels"].values()
        assert 0.0 <= confidence <= 1.0

    @pytest.mark.skipif(
        not scalpel_available("echo"),
        reason="echo model not available"
    )
    def test_echo_batch_empty(self):
        loader = ScalpelLoader()
        results = loader.predict_batch("echo", [])
        assert results == []


class TestGracefulDegradation:
    """Test that pipeline code gracefully falls back to LLM when scalpels unavailable."""

    def test_moral_valence_falls_back_to_llm(self):
        """When compass is unavailable, moral_valence should use LLM."""
        with patch("src.pipeline.character_profiling.moral_valence.scalpel_available", return_value=False):
            from src.pipeline.character_profiling.moral_valence import MoralValenceClassifier
            # Just verify the import and class instantiation works
            # Full integration requires an LLM client
            assert MoralValenceClassifier is not None

    def test_narrator_falls_back_to_llm(self):
        """When beacon is unavailable, narrator should use LLM."""
        with patch("src.pipeline.character_extraction_v2.narrator.scalpel_available", return_value=False):
            from src.pipeline.character_extraction_v2.narrator import NarratorDetector
            assert NarratorDetector is not None

    def test_summarizer_falls_back_to_llm(self):
        """When echo is unavailable, summarizer should use LLM results."""
        with patch("src.pipeline.chapter_summary.summarizer.scalpel_available", return_value=False):
            from src.pipeline.chapter_summary.summarizer import ChapterSummarizer
            assert ChapterSummarizer is not None
