"""Tests for CMUProposer merged-word (missing-space) artifact detection.

Guards the precision fix where PDF de-spacing failures ("Beckmanstated",
"dosomething") leaked into the pronunciation guide, without dropping real
names/loanwords ("Silkowski", "bandoleer", "Pinkville").
"""

import pytest

from src.pipeline.pronunciation_guide.proposers.cmu_proposer import CMUProposer

# Genuine missing-space artifacts observed in see_the_light output.
MERGED_ARTIFACTS = [
    "dosomething",       # do + something  (function-word prefix)
    "ofkitchen",         # of + kitchen
    "upthere",           # up + there
    "ananimal",          # an + animal
    "bygrunts",          # by + grunts
    "upbehind",          # up + behind
    "Calleyand",         # name + and      (common-word suffix)
    "Beckmanstated",     # name + stated
    "Bacawas",           # name + was
    "Mahoneypointed",    # name + pointed
    "Kowalskiadmirably",  # name + admirably
    "Montagnardsworked",  # name + worked
]

# Legitimate names / loanwords that a naive segmenter would wrongly split.
REAL_WORDS = [
    "Silkowski",
    "Rouskie",
    "bandoleer",
    "Capiche",
    "Marlantes",
    "Pinkville",
    "mamasan",
    "Brooklynese",
]


@pytest.fixture(scope="module")
def proposer():
    p = CMUProposer()
    if p._wordsegment is None:
        pytest.skip("wordsegment not installed")
    return p


@pytest.mark.parametrize("word", MERGED_ARTIFACTS)
def test_merged_artifacts_detected(proposer, word):
    assert proposer._is_ocr_artifact(word) is True


@pytest.mark.parametrize("word", REAL_WORDS)
def test_real_words_preserved(proposer, word):
    assert proposer._is_ocr_artifact(word) is False


def test_artifact_absent_from_proposals_via_index():
    """End-to-end through the WordIndex path (is_unknown): the artifact is
    filtered while a co-occurring real name survives."""
    from src.pipeline.pronunciation_guide.word_index import WordIndex

    p = CMUProposer()
    if p._wordsegment is None:
        pytest.skip("wordsegment not installed")
    text = (
        "The squad moved out. Beckmanstated the order clearly. "
        "Silkowski checked the map and nodded. " * 3
    )
    boundaries = [(0, 0, len(text))]
    wi = WordIndex(text, boundaries)
    proposals = p.propose(text, boundaries, word_index=wi)
    words = {pr.word.lower() for pr in proposals}
    assert "beckmanstated" not in words
    assert "silkowski" in words
