"""Tests for EntityProposer (multi-word foreign place-name detection).

Recall on real Vietnamese city names (Chu Lai, Da Nang, Saigon, Hue, …) is
verified against the full book; spaCy's labels on toy text are context-dependent,
so the integration assertions here cover only the deterministic behavior:
all-English places and known characters are never proposed.
"""

import pytest

from src.pipeline.pronunciation_guide.proposers.entity_proposer import EntityProposer


@pytest.fixture(scope="module")
def proposer():
    return EntityProposer()


class TestHelpers:
    def test_all_english_skips_ordinary_places(self, proposer):
        assert proposer._is_all_english("New York") is True
        assert proposer._is_all_english("River Road") is True

    def test_all_english_keeps_foreign_places(self, proposer):
        # These tokens are in CMU but NOT the common-word whitelist — must be kept.
        assert proposer._is_all_english("Chu Lai") is False
        assert proposer._is_all_english("Da Nang") is False
        assert proposer._is_all_english("Hue") is False
        assert proposer._is_all_english("Saigon") is False

    def test_acronym_detection(self, proposer):
        for a in ("ARVN", "VC", "CP", "ROTC", "U.S."):
            assert proposer._is_acronym(a) is True
        assert proposer._is_acronym("Chu Lai") is False
        assert proposer._is_acronym("Saigon") is False

    def test_title_case_filter(self, proposer):
        assert proposer._tokens_title_case("Chu Lai") is True
        assert proposer._tokens_title_case("mi chica") is False
        assert proposer._tokens_title_case("villes") is False


def _spacy_available():
    try:
        import spacy  # noqa: F401

        EntityProposer()._get_nlp()
        return EntityProposer()._get_nlp() is not None
    except Exception:
        return False


@pytest.mark.skipif(not _spacy_available(), reason="spaCy model not installed")
class TestIntegration:
    def test_excludes_all_english_places_and_characters(self):
        ep = EntityProposer()
        text = (
            "The company flew into Chu Lai and later moved to Da Nang. "
            "Sergeant Mitchell had grown up in New York before the war. "
            "They patrolled near Hue for weeks. "
        ) * 4
        props = ep.propose(text, [(1, 0, len(text))], character_names=["Mitchell"])
        words = {p.word.lower() for p in props}
        # All-English place and the known character are never proposed.
        assert "new york" not in words
        assert "mitchell" not in words
        # Every proposal carries the FOREIGN flag and at least one mention.
        for p in props:
            assert p.flag_reason.value == "foreign"
            assert len(p.mentions) >= 1
