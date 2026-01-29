import pytest

from src.pipeline.character_profiling.perspective_filter import (
    should_exclude_narrator_perspective_for_non_narrator,
)
from src.pipeline.character_profiling.summary_evidence import SummaryEvidenceExtractor
from src.pipeline.chapter_summary.models import ChapterSummary, ChapterSummaryMap


def test_should_exclude_narrator_perspective_object_mention():
    # Narrator is subject; character is only mentioned as object/possessive.
    assert should_exclude_narrator_perspective_for_non_narrator(
        "I repaid John's debts and never spoke of it again.",
        "John",
    )


def test_should_not_exclude_co_subject():
    # Co-subject: includes the character as actor with the narrator.
    assert not should_exclude_narrator_perspective_for_non_narrator(
        "John and I drove the ambulance through the night.",
        "John",
    )


def test_should_not_exclude_appositive_relation():
    # Appositive/introducing relation: narrator is describing who John is.
    assert not should_exclude_narrator_perspective_for_non_narrator(
        "My nephew John was only a boy when the war began.",
        "John",
    )


def test_summary_evidence_filters_first_person_contamination_for_non_narrator():
    extractor = SummaryEvidenceExtractor(llm_client=None, all_character_names=["John"])

    summary = ChapterSummary(
        chapter_index=1,
        chapter_title="Ch 1",
        summary="I repaid John's debts. John drove the ambulance.",
        key_events=[],
        primary_tone="dramatic",
        secondary_tones=[],
        dialogue_density="low",
        active_characters=["John"],
        mentioned_characters=[],
        pov_character=None,
        word_count=100,
        estimated_duration_minutes=1.0,
        confidence=0.9,
    )
    summary_map = ChapterSummaryMap(
        summaries=[summary],
        total_chapters=1,
        total_word_count=100,
        total_duration_minutes=1.0,
        overall_tones={"dramatic": 1},
        character_appearances={"John": [1]},
        pipeline_metadata={},
    )

    evidence = extractor.extract_evidence(
        character_name="John",
        aliases=[],
        summary_map=summary_map,
        is_narrator=False,
        narrative_style="first-person",
    )

    statements = [e.statement for e in evidence.evidence]
    assert any("drove the ambulance" in s.lower() for s in statements)
    assert not any("repaid" in s.lower() for s in statements)

