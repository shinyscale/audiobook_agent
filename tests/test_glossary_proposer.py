"""Tests for GlossaryProposer: every cleaned glossary term becomes a
pronunciation entry (even CMU-dict words), with definition-line junk rejected.
"""

from dataclasses import dataclass

from src.pipeline.pronunciation_guide.proposers.glossary_proposer import GlossaryProposer


@dataclass
class _GE:
    term: str
    definition: str = "A defined term used in the text."
    position: int = 0


class TestCleanTerm:
    def setup_method(self):
        self.gp = GlossaryProposer()

    def test_strips_trailing_parenthetical(self):
        assert self.gp._clean_term("Artillery (arty for short)") == "Artillery"
        assert self.gp._clean_term("Tactical Operations Center (TOC)") == "Tactical Operations Center"

    def test_rejects_sentence_fragment(self):
        assert self.gp._clean_term("in Vietnam. [Note this was common]") is None

    def test_rejects_long_phrase(self):
        assert self.gp._clean_term("YOU CANNOT AND MUST NOT do this") is None

    def test_rejects_url(self):
        assert self.gp._clean_term("Americal4ofthe3.com") is None

    def test_keeps_normal_term(self):
        assert self.gp._clean_term("ARVN") == "ARVN"
        assert self.gp._clean_term("Chieu Hoi") == "Chieu Hoi"


class TestSplitAliases:
    def test_splits_short_comma_list(self):
        assert GlossaryProposer._split_aliases("1-oh, 2-oh, 3-oh") == ["1-oh", "2-oh", "3-oh"]

    def test_does_not_split_definitionlike(self):
        # A comma-list where parts are long phrases is left intact.
        out = GlossaryProposer._split_aliases("a long phrase here, another long phrase there")
        assert out == ["a long phrase here, another long phrase there"]


class TestPropose:
    def test_cmu_dict_term_is_still_proposed(self):
        # "radio" is in the CMU dictionary; routing via the glossary strategy must
        # bypass the CMU skip so author-flagged terms always appear.
        text = "The radio crackled. He keyed the radio again. " * 3
        gp = GlossaryProposer(glossary_entries=[_GE("radio")])
        props = gp.propose(text, [(1, 0, len(text))])
        assert any(p.word == "radio" for p in props)
        assert props[0].strategy == "glossary"

    def test_glossary_only_term_gets_synthetic_mention(self):
        # A term not present verbatim in the body still yields an entry anchored
        # at the glossary position.
        text = "Body text with no occurrence of the acronym spelled out. " * 3
        gp = GlossaryProposer(
            glossary_entries=[_GE("DEROS", definition="Date Eligible for Return.", position=500)]
        )
        props = gp.propose(text, [(1, 0, len(text))])
        deros = [p for p in props if p.word == "DEROS"]
        assert len(deros) == 1
        assert len(deros[0].mentions) >= 1

    def test_empty_glossary_returns_nothing(self):
        assert GlossaryProposer(glossary_entries=None).propose("text", [(1, 0, 4)]) == []


class TestBodyFilterExemption:
    """A glossary-sourced entry whose first_position is in back matter must
    survive filter_by_body_region (the glossary itself lives in back matter)."""

    def _entry(self, strategies, position):
        from src.pipeline.pronunciation_guide.models import (
            PronunciationEntry,
            PronunciationFlag,
        )

        return PronunciationEntry(
            id="e1",
            word="DEROS",
            flag_reason=PronunciationFlag.PROPER_NOUN,
            occurrence_count=1,
            first_position=position,
            chapters_present=[1],
            context_examples=[],
            supporting_strategies=strategies,
        )

    def test_glossary_entry_survives_back_matter_filter(self):
        from src.pipeline.pronunciation_guide.models import PronunciationMap

        gloss_entry = self._entry(["glossary"], position=9000)  # in back matter
        plain_entry = self._entry(["cmu"], position=9000)
        plain_entry.id = "e2"
        pm = PronunciationMap(
            entries=[gloss_entry, plain_entry],
            low_confidence_entries=[],
            total_flagged_words=2,
            total_occurrences=2,
            by_category={},
            character_names=[],
        )
        filtered = pm.filter_by_body_region(body_start=0, body_end=5000)
        words = {(e.word, tuple(e.supporting_strategies)) for e in filtered.entries}
        assert ("DEROS", ("glossary",)) in words  # glossary kept
        assert ("DEROS", ("cmu",)) not in words   # non-glossary back-matter dropped
